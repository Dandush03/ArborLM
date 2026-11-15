# ruff: noqa: E501
"""P9I pre-freeze audit fixes (docs/reviews/p9i-prefreeze-audit-2026-11-14/AUDIT.md): M1 (missing or failed
cells derive nothing), M2 (gates to interpretation), the registered-mode refusals, the calibration binding,
the template-pool check, snapshot hashes, report columns, rehearsal draw names and the loss warning. Tiny
sizes, test seeds, synthetic backbone. Self-check only: not independent review, not Astra validation, not
human approval."""

import sys
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import (
    controls,  # noqa: E402
    pool,  # noqa: E402
)
from studies.p9i import classes as c  # noqa: E402
from studies.p9i import core, evaluate, model, report, stages, train  # noqa: E402
from studies.p9i.classes import Key, Measure  # noqa: E402

ALL = core.SLOTS_BY_SIZE
PAIRS = [(s, p) for s in core.INIT_SEEDS for p in core.PANELS]
GOOD_GATES: dict[str, Any] = {"g1_passed": True, "g2_passed": True, "g4_passed": True, "g4_defects": []}


def full_table(bb: float = 0.9, a4: float = 0.3, w7: float = 0.3, bb0: float = 0.01) -> dict[Key, Measure]:
    t: dict[Key, Measure] = {}
    for s in ALL:
        for arm, acc in (("R1", 0.95), ("BB", bb), ("A4", a4), ("W7", w7), ("BB-0", bb0), ("D7", 0.3), ("BB-D", 0.3), ("E7", 0.01), ("A4E", 0.01), ("N", 0.01)):
            for seed, panel in PAIRS:
                t[(arm, s, core.PRIMARY_PARENT, seed, panel)] = Measure(acc, 0.05, True)
    return t


def assess(table: dict[Key, Measure], **kw: Any) -> dict[str, Any]:
    args: dict[str, Any] = {"table": table, "lm": {}, "size_status": {}, "sizes": ALL, "missing": [], "failed_tasks": [], "gates": dict(GOOD_GATES), "leakage": []}
    args.update(kw)
    return stages.assess(**args)


# --- M1 ---------------------------------------------------------------------------------------------------------------
def test_complete_and_clean_run_derives_classes_and_a_selection() -> None:
    out = assess(full_table(bb=0.9, bb0=0.01))
    assert out["status"] == "COMPLETE" and out["interpretable"] is True and out["gate_reasons"] == []
    assert out["analysis"]["selection"]["outcome"] == c.SELECTED_BB and out["analysis"]["classes"]["BB"]["16384"] == c.INTERFACE_WORKS


def test_a_missing_bb_0_cell_derives_nothing_instead_of_changing_model_stores_facts() -> None:
    full = full_table(bb=0.9, bb0=0.3)  # BB-0 above chance: the complete matrix gives MODEL_STORES_FACTS
    assert c.classify(full, "BB", 16384).cls == c.MODEL_STORES_FACTS
    broken = {k: v for k, v in full.items() if not (k[0] == "BB-0" and k[1] == 16384)}
    assert c.classify(broken, "BB", 16384).cls == c.INTERFACE_WORKS  # the silent change the audit found, in the class code
    label = "BB-0-n16384-b101-o301-s1801"
    out = assess(broken, missing=[label])
    assert out["status"] == "INCOMPLETE" and out["interpretable"] is False
    sel = out["analysis"]["selection"]
    assert sel["outcome"] == "NOT_INTERPRETED (INCOMPLETE)" and sel["missing"] == [label]
    assert out["analysis"]["classes"] == {} and out["analysis"]["annotations"] == {} and out["analysis"]["backbone_contrast"] == {} and out["analysis"]["details"] == {}


def test_a_missing_bb_seed_at_65536_does_not_move_the_selection_to_a4() -> None:
    full = full_table(bb=0.9, a4=0.9)
    assert assess(full)["analysis"]["selection"]["outcome"] == c.SELECTED_BB
    broken = {k: v for k, v in full.items() if not (k[0] == "BB" and k[1] == 65536 and k[3] == 1802)}
    assert c.analyze_classes(broken, {}, {}, sizes=ALL)["selection"]["outcome"] == c.SELECTED_A4  # what silently happened before
    out = assess(broken, missing=["BB-n65536-b101-o301-s1802"])
    assert out["analysis"]["selection"]["outcome"] == "NOT_INTERPRETED (INCOMPLETE)" and out["analysis"]["classes"] == {}
    assert out["analysis"]["selection"]["missing"] == ["BB-n65536-b101-o301-s1802"]


def test_a_failed_task_or_missing_gates_record_is_incomplete_too() -> None:
    out = assess(full_table(), failed_tasks=["train:W7-n4096-b101-o301-s1801"])
    assert out["status"] == "INCOMPLETE" and out["analysis"]["selection"]["missing"] == ["train:W7-n4096-b101-o301-s1801"]
    none = assess(full_table(), gates=None)
    assert none["status"] == "INCOMPLETE" and none["analysis"]["selection"]["missing"] == ["gates record"] and none["analysis"]["classes"] == {}


# --- M2 ---------------------------------------------------------------------------------------------------------------
def test_g2_failure_leakage_and_g1_failure_make_the_run_not_interpreted_without_engineering_fail() -> None:
    for gates, expect in (
        ({**GOOD_GATES, "g2_passed": False}, "G2 failed"),
        ({**GOOD_GATES, "g1_passed": False}, "G1 failed"),
        ({**GOOD_GATES, "g1_passed": None}, "G1 not recorded"),
    ):
        out = assess(full_table(), gates=gates)
        sel = out["analysis"]["selection"]
        assert sel["outcome"] == "NOT_INTERPRETED" and expect in sel["reasons"] and expect in sel["scope"][0]
        assert out["status"] == "COMPLETE" and out["interpretable"] is False  # not ENGINEERING_FAIL (section 8.6)
        assert out["analysis"]["classes"]["BB"]["16384"] == c.INTERFACE_WORKS  # still printed, marked not interpreted
    leak = assess(full_table(), leakage=["R1-n4096-b101-o301-s1801/A"])
    assert leak["analysis"]["selection"]["outcome"] == "NOT_INTERPRETED" and leak["gate_reasons"] == ["LEAKAGE: R1-n4096-b101-o301-s1801/A"]
    assert leak["status"] == "COMPLETE" and leak["analysis"]["classes"]


def test_g4_defects_are_the_only_engineering_fail_and_also_block_interpretation() -> None:
    out = assess(full_table(), gates={**GOOD_GATES, "g4_passed": False, "g4_defects": ["checkpoint restoration is not bit-identical for N"]})
    assert out["status"] == "ENGINEERING_FAIL" and out["analysis"]["selection"]["outcome"] == "NOT_INTERPRETED"
    assert any(r.startswith("G4 failed") for r in out["gate_reasons"])


def test_incomplete_outranks_gate_reasons_but_lists_them() -> None:
    out = assess(full_table(), missing=["x"], gates={**GOOD_GATES, "g2_passed": False})
    sel = out["analysis"]["selection"]
    assert sel["outcome"] == "NOT_INTERPRETED (INCOMPLETE)" and sel["reasons"] == ["G2 failed"] and out["analysis"]["classes"] == {}


def test_markdown_shows_not_interpreted_first() -> None:
    analysis = {"status": "COMPLETE", "updates": 8192, "g1_passed": True, "g2_passed": False, "g4_passed": True, "leakage": [], "missing_cells": [], "failed_tasks": [], "interpretable": False, "gate_reasons": ["G2 failed"], "analysis": assess(full_table(), gates={**GOOD_GATES, "g2_passed": False})["analysis"]}
    text = report.render_markdown(analysis, [], [], None)
    assert text.index("NOT INTERPRETED") < text.index("Study status") and "G2 failed" in text and "NOT_INTERPRETED" in text


# --- registered-mode refusals ---------------------------------------------------------------------------------------------------
def _args(*argv: str) -> Any:
    return stages.build_parser().parse_args(["train", *argv])


def _calibration(path: Path, updates: int | None = 8192, failed: dict[str, list[str]] | None = None) -> Path:
    core.write_record(path, {**core.envelope("calibration"), "selected_updates": updates, "failed_sizes": failed or {}})
    return path


def test_train_refuses_unless_the_gates_record_exists_and_every_gate_passed(tmp_path: Path) -> None:
    run = tmp_path / "run"
    cal = _calibration(tmp_path / "cal.json")
    argv = ["--mode", "registered", "--run-dir", str(run), "--calibration", str(cal), "--stage-cap-seconds", "10", "--ledger", str(tmp_path / "l.json")]
    assert stages.main(["train", *argv]) == 2  # no gates record
    run.mkdir()
    for gates, name in (({**GOOD_GATES, "g2_passed": False}, "G2"), ({**GOOD_GATES, "g1_passed": None}, "G1"), ({**GOOD_GATES, "g4_passed": False}, "G4")):
        core.write_record(run / "gates.json", {**core.envelope("gates"), **gates})
        with pytest.raises(pool.StageRefused, match=name):
            stages.require_gates_passed(run)
        assert stages.main(["train", *argv]) == 2
        (run / "gates.json").unlink()
    assert not (run / "train").exists() and not (run / "cells").exists() and not (run / "updates.json").exists()  # nothing was trained or recorded
    core.write_record(run / "gates.json", {**core.envelope("gates"), **GOOD_GATES})
    assert stages.require_gates_passed(run)["g2_passed"] is True


def test_registered_mode_needs_the_calibration_record_and_refuses_updates(tmp_path: Path) -> None:
    with pytest.raises(pool.StageRefused, match="--calibration"):
        stages.updates_for(_args("--mode", "registered"))
    cal = _calibration(tmp_path / "cal.json")
    assert stages.updates_for(_args("--mode", "registered", "--calibration", str(cal))) == 8192
    with pytest.raises(pool.StageRefused, match="--updates"):
        stages.updates_for(_args("--mode", "registered", "--calibration", str(cal), "--updates", "8192"))
    none = _calibration(tmp_path / "none.json", updates=None)
    with pytest.raises(pool.StageRefused, match="no U"):
        stages.updates_for(_args("--mode", "registered", "--calibration", str(none)))
    assert stages.updates_for(_args("--mode", "rehearsal", "--updates", "64")) == 64  # other modes unchanged


def test_calibration_hash_is_checked_and_bound_across_stages(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    cal = _calibration(tmp_path / "cal.json")
    digest = stages.file_sha256(cal)
    ok = _args("--mode", "registered", "--calibration", str(cal), "--calibration-sha256", digest)
    assert stages.calibration_record_of(ok)["selected_updates"] == 8192
    with pytest.raises(pool.StageRefused, match="hash"):
        stages.calibration_record_of(_args("--mode", "registered", "--calibration", str(cal), "--calibration-sha256", "0" * 64))
    binding = stages.calibration_binding(ok)
    assert binding == {"calibration_sha256": digest, "calibration_selected_updates": 8192, "calibration_failed_sizes": {}}
    with pytest.raises(pool.StageRefused, match="train stage has not recorded"):
        stages.check_binding(ok, run)
    stages.write_json(run / "calibration_binding.json", binding)
    stages.check_binding(ok, run)
    other = _calibration(tmp_path / "other.json", updates=4096)  # another U
    with pytest.raises(pool.StageRefused, match="differs"):
        stages.check_binding(_args("--mode", "registered", "--calibration", str(other)), run)
    failed = _calibration(tmp_path / "failed.json", failed={"65536": ["TASK_CEILING_FAIL"]})  # same U, other failed sizes
    with pytest.raises(pool.StageRefused, match="differs"):
        stages.check_binding(_args("--mode", "registered", "--calibration", str(failed)), run)
    with pytest.raises(pool.StageRefused, match="--calibration"):
        stages.check_binding(_args("--mode", "registered"), run)
    stages.check_binding(_args("--mode", "calibration"), run)  # not registered: nothing to bind


def test_registered_evaluation_requires_the_data_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stages, "study_data", lambda args: SimpleNamespace(sha256s=lambda: {}))
    args = _args("--mode", "registered", "--run-dir", str(tmp_path), "--label", "N-n4096-b101-o301-s1801", "--calibration", str(_calibration(tmp_path / "cal.json")))
    with pytest.raises(stages.StageError, match="no data manifest"):
        stages.work_evaluate(args)
    with pytest.raises(stages.StageError, match="no data manifest"):
        stages.verified_data(args, require_manifest=True)
    assert stages.verified_data(_args("--mode", "calibration", "--run-dir", str(tmp_path)), require_manifest=False) is not None


def test_registered_template_pool_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stages.p9core, "load_trained_corpus", lambda root: b"")
    monkeypatch.setattr(stages.data_mod, "build_study_data", lambda seeds, corpus, sizes=None: SimpleNamespace(pool=(1, 2, 3), seeds=seeds))
    with pytest.raises(stages.StageError, match="template pool"):
        stages.study_data(_args("--mode", "registered"))
    monkeypatch.setattr(stages.data_mod, "build_study_data", lambda seeds, corpus, sizes=None: SimpleNamespace(pool=stages.p9core.TEMPLATE_POOL, seeds=seeds))
    assert stages.study_data(_args("--mode", "registered")).pool == stages.p9core.TEMPLATE_POOL
    monkeypatch.setattr(stages.data_mod, "build_study_data", lambda seeds, corpus, sizes=None: SimpleNamespace(pool=(1, 2, 3), seeds=seeds))
    assert stages.study_data(_args("--mode", "rehearsal", "--draw", "2")).pool == (1, 2, 3)  # only the registered run checks it


# --- records carry the binding; snapshot hashes; loss warning -----------------------------------------------------------------
@pytest.fixture(scope="module")
def tiny() -> Any:
    args = _args("--dry", "--mode", "calibration")
    return SimpleNamespace(args=args, study=stages.study_data(args), backbone=controls.synthetic_backbone())


def test_train_and_eval_records_carry_the_calibration_binding_and_the_snapshot_hash_is_verified(tiny: Any, tmp_path: Path) -> None:
    cal = _calibration(tmp_path / "cal.json")
    args = _args("--dry", "--mode", "calibration", "--calibration", str(cal))
    cell = core.make_cell("N", 4096)
    out = tmp_path / "cell"
    job = stages.build_job(args, cell, tiny.study, out, 3)
    assert job.extra["calibration_sha256"] == stages.file_sha256(cal)
    record = train.train_cell(job)
    assert record["calibration_sha256"] == job.extra["calibration_sha256"] and record["calibration_selected_updates"] == 8192 and record["calibration_failed_sizes"] == {}
    assert record["seed_set"] == "p9i-test-0"
    written = evaluate.evaluate_cell(cell, tmp_path, tiny.study, job.backbone, facts=stages.DRY_FACTS[4096], updates=[3], init_seed=job.init_seed, r1_seed=job.r1_seed, extra=stages.calibration_binding(args), require_train_record=True, out_dir=out)
    assert core.read_record(written[0], "eval")["calibration_sha256"] == job.extra["calibration_sha256"]
    # a snapshot that no longer matches train.json is refused; so is a missing train record when one is required
    snap = out / "snapshots" / core.snapshot_stem(3) / "model.pt"
    snap.write_bytes(snap.read_bytes() + b"x")
    with pytest.raises(ValueError, match="hash"):
        evaluate.evaluate_cell(cell, tmp_path, tiny.study, job.backbone, facts=stages.DRY_FACTS[4096], updates=[3], init_seed=job.init_seed, r1_seed=job.r1_seed, out_dir=out)
    (out / "train.json").unlink()
    with pytest.raises(ValueError, match="no train record"):
        evaluate.evaluate_cell(cell, tmp_path, tiny.study, job.backbone, facts=stages.DRY_FACTS[4096], updates=[3], init_seed=job.init_seed, r1_seed=job.r1_seed, out_dir=out, require_train_record=True)


def test_the_recorded_loss_is_unchanged_and_no_requires_grad_warning(tiny: Any) -> None:
    stream = train.training_stream_for(tiny.study, stages.DRY_FACTS[4096])
    tokens = stream.batch(1).tokens
    a = model.build_model("N", 4096, 7, tiny.backbone)
    b = model.build_model("N", 4096, 7, tiny.backbone)
    logits, _ = a(tokens[:, :-1])
    expected = float(train.alphabet_loss(logits, tokens).detach())
    trainer = train.Trainer(core.make_cell("N", 4096), b, train.build_optimizers(b))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        record = trainer.step(tokens)
    assert record["task_loss"] == expected  # bit for bit the same number
    assert not [w for w in caught if "requires_grad" in str(w.message)]


# --- report columns and the rehearsal draw name ---------------------------------------------------------------------------------
def test_report_cells_have_eta_dependence_support_and_next_byte_columns() -> None:
    def panel(acc: float) -> dict[str, Any]:
        return {"accuracy": acc, "permuted_accuracy": 0.03, "disabled_accuracy": 0.02, "support": {"share_with_support": 0.9, "mean_length": 1.5, "useful_slots": 7}}

    def ev(arm: str, acc: float, lm: bool) -> dict[str, Any]:
        rec: dict[str, Any] = {"arm": arm, "slots": 4096, "parent": [101, 301], "seed": 1801, "panels": {"A": panel(acc), "B": panel(acc)}}
        if lm:
            rec["language_modelling"] = {"before_nats": 2.0, "after_nats": 2.1, "relative_rise": 0.05}
        return rec

    def tr(arm: str) -> dict[str, Any]:
        return {"facts": 2048, "matched_updates": 8192, "arm": arm, "slots": 4096, "parent": [101, 301], "seed": 1801, "exposure_per_fact_mean": 512.0, "exposure_per_fact_min": 512, "exposure_per_fact_max": 512, "trainable_parameters": 1, "trainable_backbone_parameters": 0, "interface_extra_parameters": 0, "dense_hidden": 0, "stored_parameters": 2, "optimizer_state_bytes": 3, "wall_seconds": 1.0, "status": "completed"}

    trains = {"R1-a": tr("R1"), "BB-a": tr("BB"), "BB-0-a": tr("BB-0"), "BB-D-a": tr("BB-D")}
    evals = {"R1-a": ev("R1", 0.8, False), "BB-a": ev("BB", 0.4, True), "BB-0-a": ev("BB-0", 0.05, True), "BB-D-a": ev("BB-D", 0.3, True)}
    rows = {r["label"]: r for r in report._rows_cells(trains, evals)}
    bb = rows["BB-a"]
    assert bb["eta_A"] == pytest.approx(0.5) and bb["permuted_accuracy_A"] == 0.03 and bb["disabled_accuracy_B"] == 0.02
    assert bb["support_share_A"] == 0.9 and bb["support_mean_length_B"] == 1.5 and bb["useful_slots_A"] == 7
    for label in ("BB-a", "BB-0-a", "BB-D-a"):
        assert (rows[label]["lm_before_nats"], rows[label]["lm_after_nats"], rows[label]["lm_relative_rise"]) == (2.0, 2.1, 0.05)
    assert rows["R1-a"]["eta_A"] == pytest.approx(1.0)


def test_rehearsal_whitelist_accepts_a_draw_name_and_rejects_a_non_string() -> None:
    base = {"kind": "rehearsal", "schema": 1, "study": "P9I", "mode": "rehearsal", "seed_set": "rehearsal-2"}
    train.validate_rehearsal_record(base)
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**base, "seed_set": 2})
