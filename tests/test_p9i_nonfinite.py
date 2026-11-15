# ruff: noqa: E501
"""P9I non-finite numbers (GATE_FIX_AUDIT X1 and X2): a ratio with a zero denominator is +infinity by rule and
must not crash analyze or report; a non-finite next-byte loss of a BB arm counts as a rise above 5%. A 57-cell
synthetic registry record set stands in for a run; no model is trained for it. Self-check only: not
independent review, not Astra validation, not human approval."""

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9i import classes as c  # noqa: E402
from studies.p9i import core, evaluate, model, stages  # noqa: E402

FACTS = core.FACTS_PROPORTIONAL
U = 8192


# --- helpers of the serialisation -----------------------------------------------------------------------------------------
def test_jsonable_and_number_round_trip_every_non_finite_value() -> None:
    value = {"a": math.inf, "b": [-math.inf, math.nan, 1.5], "c": {"d": (math.inf, 2)}, "e": "text", "f": None, "g": True}
    out = core.jsonable(value)
    assert out == {"a": "+inf", "b": ["-inf", "nan", 1.5], "c": {"d": ["+inf", 2]}, "e": "text", "f": None, "g": True}
    json.dumps(out, allow_nan=False)
    assert core.number("+inf") == math.inf and core.number("-inf") == -math.inf and math.isnan(core.number("nan"))
    assert core.number(2) == 2.0 and math.isnan(core.number(None))
    with pytest.raises(ValueError):
        core.number("infinity")
    assert core.jsonable({"x": 1e300}) == {"x": 1e300}  # finite numbers are untouched


def test_language_modelling_annotation_counts_a_non_finite_rise_as_degraded() -> None:
    for bad in (math.inf, -math.inf, math.nan):
        out = c.language_modelling_annotation({1801: 0.0, 1802: bad})
        assert out["degraded"] is True and out["label"] == c.LM_DEGRADED
        json.dumps(core.jsonable(out), allow_nan=False)
    assert c.language_modelling_annotation({1801: 0.05, 1802: 0.0})["degraded"] is False  # unchanged rule below the threshold


# --- X2 in the evaluation record ----------------------------------------------------------------------------------------
def test_language_modelling_keeps_a_non_finite_loss_as_a_string_and_flags_it(monkeypatch: pytest.MonkeyPatch) -> None:
    backbone = controls.synthetic_backbone()
    net = model.build_model("BB-0", 4096, 900061, backbone, seed_rng=False)
    rows = evaluate.corpus_rows(stages.SYNTHETIC_CORPUS)[:8]
    calls = iter([2.0, math.nan])
    monkeypatch.setattr(evaluate, "next_byte_loss", lambda bb, r: next(calls))
    out = evaluate.language_modelling(net, backbone, rows)
    assert out == {"before_nats": 2.0, "after_nats": "nan", "relative_rise": "nan", "degraded": True}
    calls = iter([2.0, math.inf])
    monkeypatch.setattr(evaluate, "next_byte_loss", lambda bb, r: next(calls))
    out = evaluate.language_modelling(net, backbone, rows)
    assert out == {"before_nats": 2.0, "after_nats": "+inf", "relative_rise": "+inf", "degraded": True}
    json.dumps(out, allow_nan=False)
    for after, degraded in ((21.0, False), (21.1, True)):  # a rise of exactly 5% (1 / 20) is not above 5%
        calls = iter([20.0, after])
        monkeypatch.setattr(evaluate, "next_byte_loss", lambda bb, r: next(calls))
        out = evaluate.language_modelling(net, backbone, rows)
        assert out["degraded"] is degraded and isinstance(out["relative_rise"], float)
    calls = iter([2.0, 2.0])
    monkeypatch.setattr(evaluate, "next_byte_loss", lambda bb, r: next(calls))
    assert evaluate.language_modelling(net, backbone, rows) == {"before_nats": 2.0, "after_nats": 2.0, "relative_rise": 0.0, "degraded": False}


def test_a_really_non_finite_trained_attention_gives_nan_strings() -> None:
    backbone = controls.synthetic_backbone()
    net = model.build_model("BB-0", 4096, 900062, backbone, seed_rng=False)
    net.backbone.blocks[0].qkv.weight.data.fill_(float("nan"))
    out = evaluate.language_modelling(net, backbone, evaluate.corpus_rows(stages.SYNTHETIC_CORPUS)[:8])
    assert out["after_nats"] == "nan" and out["relative_rise"] == "nan" and out["degraded"] is True and isinstance(out["before_nats"], float)


# --- analyze -> report on a 57-cell synthetic registry record set ---------------------------------------------------------
def _panel(acc: float, facts: int) -> dict[str, Any]:
    low = {2048: (36, 96), 8192: (198, 318), 32768: (905, 1147)}[facts]
    return {"accuracy": acc, "facts": facts, "correct": round(acc * facts), "chance_interval": list(low), "memory_dependence_chance": True, "permuted_accuracy": 0.03, "disabled_accuracy": 0.03, "support": {"share_with_support": 0.9, "mean_length": 1.5, "useful_slots": 5}, "unseen_accuracy": 0.03, "leakage": False}


def _write_registry(run: Path, acc: dict[tuple[str, int], float], lm: dict[tuple[str, int], Any] | None = None) -> None:
    """Eval and train records for the 57 registered cells; ``acc[(arm, slots)]`` (default 0.01, R1 0.95)."""
    lm = lm or {}
    for cell in core.cells():
        a = acc.get((cell.arm, cell.slots), 0.95 if cell.arm == "R1" else 0.01)
        folder = core.cell_dir(run, cell.label)
        record: dict[str, Any] = {
            **core.envelope("eval"), "label": cell.label, "arm": cell.arm, "slots": cell.slots, "parent": list(cell.parent), "seed": cell.seed,
            "update": U, "facts": cell.facts, "panels": {p: _panel(a, cell.facts) for p in core.PANELS}, "secondary": {},
        }  # fmt: skip
        if cell.arm in core.BB_ARMS:
            record["language_modelling"] = {"before_nats": 2.3, "after_nats": 2.3, "relative_rise": lm.get((cell.arm, cell.slots), 0.0), "degraded": False}
        core.write_record(folder / "eval" / core.snapshot_stem(U) / "eval.json", record)
        core.write_record(
            folder / "train.json",
            {
                **core.envelope("train"), "label": cell.label, "arm": cell.arm, "slots": cell.slots, "facts": cell.facts, "parent": list(cell.parent), "seed": cell.seed,
                "matched_updates": U, "exposure_per_fact_mean": U * 128 / cell.facts, "exposure_per_fact_min": 1, "exposure_per_fact_max": 1,
                "trainable_parameters": 1, "trainable_backbone_parameters": 4224 if cell.arm in core.BB_ARMS else 0, "interface_extra_parameters": 0,
                "dense_hidden": 0, "stored_parameters": 2, "optimizer_state_bytes": 3, "wall_seconds": 1.0, "status": "completed",
            },
        )  # fmt: skip


def _run(tmp_path: Path, acc: dict[tuple[str, int], float], lm: dict[tuple[str, int], Any] | None = None) -> tuple[dict[str, Any], Path]:
    run = tmp_path / "run"
    _write_registry(run, acc, lm)
    core.write_record(run / "gates.json", {**core.envelope("gates"), "g1_passed": True, "g2_passed": True, "g4_passed": True, "g4_defects": []})
    cal = tmp_path / "cal.json"
    core.write_record(cal, {**core.envelope("calibration"), "selected_updates": U, "failed_sizes": {}})
    argv = ["--mode", "rehearsal", "--run-dir", str(run), "--calibration", str(cal)]
    parser = stages.build_parser()
    assert stages.work_analyze(parser.parse_args(["work", "analyze", *argv])) == 0
    analysis = json.loads((run / "analysis.json").read_text())  # strict JSON: no NaN or Infinity tokens
    assert stages.work_report(parser.parse_args(["work", "report", *argv])) == 0
    return analysis, run


WORKS = {("W7", s): 0.9 for s in core.SLOTS_BY_SIZE}


def test_analyze_and_report_survive_a_zero_accuracy_dense_arm(tmp_path: Path) -> None:
    acc = {**WORKS, **{("D7", s): 0.3 for s in core.SLOTS_BY_SIZE}, ("D7", 65536): 0.0}  # W7 works at 65,536 over a dense arm at 0
    analysis, run = _run(tmp_path, acc)
    assert analysis["status"] == "COMPLETE" and analysis["interpretable"] is True and len(analysis["cells_read"]) == 57
    dense = analysis["analysis"]["annotations"]["W7"]["65536"]["dense_comparison"]
    assert dense["label"] == c.BEATS_DENSE and dense["smallest"] == "+inf" and set(dense["ratios"].values()) == {"+inf"}
    assert analysis["analysis"]["annotations"]["W7"]["16384"]["dense_comparison"]["smallest"] == pytest.approx(3.0)  # finite ratios stay numbers
    out = run / "results"
    assert {p.name for p in out.iterdir()} == {"classes.csv", "cells.csv", "RESULTS.md", "results.json"}
    assert len(list(csv.DictReader((out / "cells.csv").open()))) == 57
    json.loads((out / "results.json").read_text())


def test_analyze_and_report_survive_a_zero_accuracy_state_arm(tmp_path: Path) -> None:
    acc = {("W7", 16384): 0.0, ("E7", 16384): 0.5}  # the state arm scores 0, the embedding arm is positive
    analysis, run = _run(tmp_path, acc)
    contrast = analysis["analysis"]["backbone_contrast"]["E7/W7"]
    assert contrast["label"] == c.BACKBONE_HURTS and set(contrast["ratios"].values()) == {"+inf"}
    assert analysis["analysis"]["classes"]["W7"]["16384"] == c.INTERFACE_FAILS and analysis["analysis"]["classes"]["E7"]["16384"] == c.INTERFACE_PARTIAL
    text = (run / "results" / "RESULTS.md").read_text()
    assert "BACKBONE HURTS ADDRESSING" in text and "Infinity" not in text


def test_both_zero_denominators_and_non_finite_language_modelling_in_one_run(tmp_path: Path) -> None:
    acc = {**WORKS, ("BB", 16384): 0.9, ("BB-D", 16384): 0.0, ("W7", 16384): 0.0, ("E7", 16384): 0.5}
    lm = {("BB", 16384): "+inf", ("BB-0", 16384): "nan", ("BB-D", 16384): None, ("BB", 4096): "nan"}  # X2: raw strings, and a legacy None
    analysis, run = _run(tmp_path, acc, lm)
    ann = analysis["analysis"]["annotations"]["BB"]
    assert ann["16384"]["language_modelling"]["label"] == c.LM_DEGRADED and ann["16384"]["language_modelling"]["degraded"] is True
    assert ann["16384"]["dense_comparison"]["smallest"] == "+inf"
    assert ann["4096"]["language_modelling"]["degraded"] is True  # "nan" on both seeds
    assert ann["65536"]["language_modelling"]["degraded"] is False
    assert "+inf" in set(analysis["analysis"]["backbone_contrast"]["E7/W7"]["ratios"].values())
    rows = list(csv.DictReader((run / "results" / "cells.csv").open()))
    bb = [r for r in rows if r["arm"] == "BB" and r["slots"] == "16384" and r["parent"] == "b101-o301"]
    assert bb and all(r["lm_relative_rise"] == "+inf" for r in bb)


def test_a_non_finite_language_modelling_does_not_block_selection(tmp_path: Path) -> None:
    acc = {("BB", s): 0.9 for s in core.SLOTS_BY_SIZE}
    lm = {("BB", s): "+inf" for s in core.SLOTS_BY_SIZE}
    analysis, _ = _run(tmp_path, acc, lm)
    assert analysis["analysis"]["selection"]["outcome"] == c.SELECTED_BB  # the annotation is carried, not a block (section I.8.2)
    assert all(a["language_modelling"]["degraded"] for a in analysis["analysis"]["annotations"]["BB"].values())

