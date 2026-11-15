# ruff: noqa: E501
"""P10S1 analysis and report on synthetic records of the whole registry (ADR-0021 section 10.2): on-disk records in the layout of a real run, covering both outcomes of section 8, a
missing cell, a failed cell, a non-finite cell, a failed task, each failed gate, an identity mismatch, leakage, a failed REF, a failed DEP, the overload row, the seed block, and the
censoring cases of section 8.8 at registry level. Every rendered report is checked for the STORE ONLY; ORACLE-ADDRESSED tag on every positive label. The accuracies are a declared
function of (arm, cell, replicate, update, panel): nothing here measures a model or a seed. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import analysis, core, report  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

PLAN = core.Plan(seed_block_draws=(1,))
FRO = fz.Frozen.build(PLAN, fz.default_cpu_table())


def run(tmp_path: Path, scn: syn.Scenario, fro: fz.Frozen = FRO, **kw: Any) -> tuple[dict[str, Any], Path]:
    d = tmp_path / "run"
    syn.write_run(d, fro, scn)
    gates = json.loads((d / "gates.json").read_text()) if (d / "gates.json").exists() else None
    study = analysis.load_study(d, fro)
    result = analysis.analyze_study(study, fro, gates=gates, **kw)
    core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": result}))
    return result, d


def rendered(d: Path, banner: str | None = None) -> str:
    paths = report.write_report(d, d / "results", banner=banner)
    text = paths[1].read_text()
    assert C.untagged_positive_labels(text) == [] and core.ORACLE_SENTENCE in text and core.STORE_ONLY_TAG in text and "Astra review: NOT_PERFORMED" in text
    return text


def a_max_all(v: float):
    def f(arm: str, facts: int, slots: int, rep: int) -> float:
        return 0.15 if arm == "D-OQ" else (1.0 if arm == "R2" else v)

    return f


def tau_by_slots(t4: float, t16: float, t64: float):
    def f(arm: str, facts: int, slots: int) -> float:
        return 200.0 if arm == "R2" else {4096: t4, 16384: t16, 65536: t64}[slots]

    return f


# --- the default scenario: both lines positive on paper, every positive label tagged ------------------------------------------------------------
def test_default_scenario_end_to_end(tmp_path: Path) -> None:
    r, d = run(tmp_path, syn.Scenario())
    assert r["assessment"]["status"] == "COMPLETE" and r["assessment"]["cells_read"] == 185
    steps, arms = r["capacity"]["steps"], r["capacity"]["arms"]
    assert {s: steps["F-OQ"][s]["class"] for s in ("A1", "A2", "B1", "B2")} == {"A1": C.CAPACITY_STEP, "A2": C.NOT_LOADED, "B1": C.GAIN_STEP, "B2": C.CAPACITY_STEP}
    assert steps["F-OQ"]["A2"]["verdicts"] == [C.CEILING] * 5 and steps["F-OQ"]["B1"]["verdicts"] == [C.GAIN_ONLY] * 5
    assert {a: arms[a]["class"] for a in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")} == dict.fromkeys(("F-OQ", "F-OQ-IVF", "T-OQ", "H8"), C.CAPACITY_SUPPORTED)
    assert arms["F-OQ"]["work_label"] == C.LINEAR_KEY_SCORING and arms["T-OQ"]["work_label"] == C.SUBLINEAR and arms["F-OQ-IVF"]["work_label"] == C.SUBLINEAR and arms["H8"]["work_label"] == C.SUBLINEAR
    out = r["outcome"]["capacity"]
    assert out["label"] == C.CAPACITY_POSITIVE and out["row"] == 3 and out["printed"].startswith("CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS;")
    assert "S0 NOT YET DECIDED" in out["printed"] and "learned-address lane: OMITTED" in out["printed"] and "hierarchy:" in out["printed"] and "active work:" in out["printed"] and core.ORACLE_SENTENCE in out["printed"]
    assert "H8" not in out["printed"].split("arm(s)")[1].split(";")[0]  # H8 alone cannot give the outcome: the label requires learned keys
    assert out["reading"].startswith("Storage-half reading not available: the dense comparison is not established at matched compute")  # every dense pair of the default cost table is MC-SHORT (section 22)
    assert "Storage half supported" not in out["reading"] and "DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE" in out["printed"]
    text = rendered(d)
    assert "CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED" in text and "EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED" in text and "What S1 cannot establish" in text
    assert "NOT_PERFORMED" in text and "Decision map" in text and "Row movement" in text and "Cost table" in text and "Seed block" in text and "Study B" in text
    # the two lines are reported separately and a positive on one implies nothing about the other
    eff = r["efficiency"]
    assert {a: eff["steps"][a]["A1"]["class"] for a in ("F-OQ", "T-OQ")} == {"F-OQ": "FASTER STEP", "T-OQ": "FASTER STEP"} and r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_POSITIVE
    assert all(v == C.REACHED_ONLY for v in eff["steps"]["F-OQ"]["A1"]["verdicts"])  # the smaller cell is loaded and never reaches 3.0 bits: right-censored
    sb = r["capacity"]["study_b"]
    assert sb["F-OQ"]["sublinear"] is False and sb["T-OQ"]["sublinear"] is True and sb["F-OQ"]["label"] == C.NOT_ESTABLISHED
    assert r["capacity"]["hierarchy"]["label"] in (C.TREE_AHEAD, C.TREE_COMPETITIVE, C.TREE_BEHIND) and r["capacity"]["key_learning_limited"] is False
    assert set(r["capacity"]["seed_block"]["cells"]) and all(v["dominates"] in ("init seed", "data draw") for v in r["capacity"]["seed_block"]["cells"].values())
    assert r["capacity"]["conventional"]["dict_dominates_on_this_task"] == "DICT DOMINATES ON THIS TASK" and r["decision_map"]
    assert any(m["flag"] == "MC-MISMATCH" for m in r["capacity"]["mc_mismatch"]) or r["capacity"]["mc_mismatch"] == []


def test_every_movement_ratio_is_printed_with_the_budget_and_efficiency_verdicts(tmp_path: Path) -> None:
    r, _ = run(tmp_path, syn.Scenario())
    for arm in ("F-OQ", "T-OQ", "H8"):
        for s in r["capacity"]["steps"][arm].values():
            for rep in s["replicates"]:
                assert rep["movement"]["ratios"]["total"] == pytest.approx(2.0) and "share_without" in rep["movement"]["ratios"]
    for arm in ("F-OQ", "T-OQ"):
        for s in r["efficiency"]["steps"][arm].values():
            for rep in s["replicates"]:
                assert rep["movement_at_U_P"]["ratios"]["total"] is not None and rep["movement_at_hit"]["ratios"] is not None and "optimizer_assisted" in rep


# --- outcomes of the capacity line -------------------------------------------------------------------------------------------------------
def test_not_loaded_is_not_tested_and_not_a_negative(tmp_path: Path) -> None:
    scn = syn.Scenario(a_max=a_max_all(1.0), tau=tau_by_slots(200.0, 200.0, 200.0))
    r, d = run(tmp_path, scn)
    steps = r["capacity"]["steps"]["F-OQ"]
    assert all(s["class"] == C.NOT_LOADED for s in steps.values()) and r["capacity"]["arms"]["F-OQ"]["class"] == C.NOT_TESTED_BY_LOAD
    assert r["outcome"]["capacity"]["label"] == C.CAPACITY_NOT_TESTED and r["outcome"]["capacity"]["row"] == 5 and r["outcome"]["capacity"]["label"] != C.CAPACITY_NEGATIVE
    assert r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_INCONCLUSIVE  # every cell reaches 3.0 bits at the first snapshot: left-censored both: NOT_ASSESSED
    assert "CAPACITY NOT TESTED" in rendered(d) and r["decision_map"][0].startswith("6.")


def test_no_gain_is_the_negative(tmp_path: Path) -> None:
    scn = syn.Scenario(a_max=a_max_all(0.6), tau=tau_by_slots(900.0, 900.0, 900.0))
    r, d = run(tmp_path, scn)
    assert all(s["class"] == C.NO_GAIN for s in r["capacity"]["steps"]["F-OQ"].values()) and r["capacity"]["arms"]["F-OQ"]["class"] == C.CAPACITY_NOT_SUPPORTED
    assert r["outcome"]["capacity"]["label"] == C.CAPACITY_NEGATIVE and r["outcome"]["capacity"]["printed"] == "CAPACITY-NEGATIVE (a)"
    assert r["outcome"]["capacity"]["reading"].startswith("Storage half not supported for this store, backbone, task and budget")
    assert r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_INCONCLUSIVE  # the level of 3.0 bits is never reached: both right-censored: NOT_ASSESSED
    assert "CAPACITY-NEGATIVE (a)" in rendered(d)


def test_dense_ahead_blocks_the_positive(tmp_path: Path) -> None:
    def a_max(arm: str, facts: int, slots: int, rep: int) -> float:
        return 1.0 if arm in ("D-OQ", "R2") else 0.85 * min(1.0, 0.7 * slots / facts)

    def tau(arm: str, facts: int, slots: int) -> float:
        return 200.0 if arm in ("R2", "D-OQ") else 1500.0

    r, d = run(tmp_path, syn.Scenario(a_max=a_max, tau=tau))
    arms = r["capacity"]["arms"]
    assert arms["F-OQ"]["class"] == C.CAPACITY_SUPPORTED and arms["F-OQ"]["dense"] == C.DENSE_AHEAD and arms["T-OQ"]["dense"] == C.DENSE_AHEAD
    assert r["outcome"]["capacity"]["label"] == C.CAPACITY_NEGATIVE and r["outcome"]["capacity"]["printed"].endswith("DENSE AHEAD)")
    assert "Storage half" not in r["outcome"]["capacity"]["reading"] or r["outcome"]["capacity"]["reading"].startswith("Storage half not supported")
    assert "DENSE AHEAD" in rendered(d)


def test_dense_dependence_and_ref_failures_are_not_negatives(tmp_path: Path) -> None:
    def broken(arm: str, facts: int, slots: int, rep: int) -> bool:
        return arm in ("F-OQ", "T-OQ") and rep in (1, 2)

    r, d = run(tmp_path, syn.Scenario(dep_fail=broken))
    s = r["capacity"]["steps"]["F-OQ"]
    assert s["A1"]["class"] == C.DEPENDENCE_FAILED and s["A1"]["verdicts"][:2] == [C.DEPENDENCE_FAILED] * 2 and r["capacity"]["arms"]["F-OQ"]["class"] == C.DEPENDENCE_FAILED
    assert r["outcome"]["capacity"]["label"] != C.CAPACITY_NEGATIVE
    rendered(d)

    def r2_low(arm: str, facts: int, slots: int, rep: int) -> float:
        return 0.5 if arm == "R2" and rep in (1, 2) else (0.15 if arm == "D-OQ" else (1.0 if arm == "R2" else min(1.0, 0.7 * slots / facts)))

    r2, d2 = run(tmp_path / "ref", syn.Scenario(a_max=r2_low))
    a1 = r2["capacity"]["steps"]["F-OQ"]["A1"]
    assert a1["verdicts"][:2] == [C.NOT_EVALUATED] * 2 and a1["class"] == C.NOT_EVALUATED and a1["replicates"][0]["ref_ok"] is False and a1["replicates"][2]["ref_ok"] is True
    assert r2["capacity"]["steps"]["F-OQ"]["B2"]["class"] == C.NOT_EVALUATED  # the 32,768-fact row's reference R2 (32K/64K) also failed in replicates 1 and 2
    assert r2["outcome"]["capacity"]["label"] != C.CAPACITY_NEGATIVE and r2["outcome"]["capacity"]["label"] != C.CAPACITY_POSITIVE
    rendered(d2)


def test_leakage_makes_a_replicate_not_evaluated(tmp_path: Path) -> None:
    label = next(c.label for c in core.registered_cells(PLAN) if (c.arm, c.facts, c.slots, c.draw) == ("F-OQ", 8192, 4096, 1))
    r, _ = run(tmp_path, syn.Scenario(leak_labels={label}))
    a1 = r["capacity"]["steps"]["F-OQ"]["A1"]["verdicts"]
    assert a1[0] == C.NOT_EVALUATED and a1[1:] == [C.CAPACITY] * 4 and r["capacity"]["steps"]["F-OQ"]["A1"]["class"] == C.MIXED


# --- incomplete and engineering failures ---------------------------------------------------------------------------------------------------
def test_a_missing_failed_or_non_finite_cell_makes_the_study_incomplete(tmp_path: Path) -> None:
    label = core.registered_cells(PLAN)[0].label
    for name, scn in (("missing", syn.Scenario(missing={label})), ("failed", syn.Scenario(fail={label})), ("nonfinite", syn.Scenario(nonfinite={label}))):
        r, d = run(tmp_path / name, scn)
        a = r["assessment"]
        assert a["status"] == C.S1_INCOMPLETE and (label in a["missing_cells"] or label in a["failed_cells"]) and r["capacity"] is None and r["efficiency"] is None
        assert r["outcome"]["capacity"]["label"] == C.S1_INCOMPLETE and r["outcome"]["efficiency"]["label"] == C.S1_INCOMPLETE  # no outcome on either line; the denominator is never reduced
        assert (name == "missing") == (label in a["missing_cells"]) and a["cells_read"] == 183 and label in a["reasons"]
        text = rendered(d)
        assert "S1-INCOMPLETE" in text and label in text and "CAPACITY-POSITIVE" not in text
    r, _ = run(tmp_path / "task", syn.Scenario(), failed_tasks=["train:P_F-OQ_f2048_n4096_d1_i2101"])
    assert r["assessment"]["status"] == C.S1_INCOMPLETE


@pytest.mark.parametrize("gate", ["g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9"])
def test_a_failed_engineering_gate_gives_no_scientific_label(tmp_path: Path, gate: str) -> None:
    r, d = run(tmp_path, syn.Scenario(gates_ok=False, failed_gate=gate))
    assert r["assessment"]["status"] == C.S1_ENGINEERING_FAILURE and f"gate {gate.upper()} failed" in r["assessment"]["engineering"]["reasons"]
    assert r["outcome"]["capacity"]["label"] == C.S1_ENGINEERING_FAILURE == r["outcome"]["efficiency"]["label"] and r["capacity"] is None
    text = rendered(d)
    assert "S1-ENGINEERING-FAILURE" in text and "CAPACITY-POSITIVE" not in text and "EFFICIENCY-POSITIVE" not in text


def test_missing_gates_and_identity_mismatch_are_engineering_failures(tmp_path: Path) -> None:
    d = tmp_path / "run"
    syn.write_run(d, FRO, syn.Scenario())
    study = analysis.load_study(d, FRO)
    assert analysis.analyze_study(study, FRO, gates=None)["assessment"]["status"] == C.S1_ENGINEERING_FAILURE
    ident = {"source_sha256": "synthetic", "spec_sha256": "synthetic", "config_sha256": "synthetic", "frozen_source_sha256": "synthetic"}
    assert analysis.analyze_study(study, FRO, gates=json.loads((d / "gates.json").read_text()), expected_identity=ident)["assessment"]["status"] == "COMPLETE"
    r = analysis.analyze_study(study, FRO, gates=json.loads((d / "gates.json").read_text()), expected_identity={**ident, "source_sha256": "other code"})
    assert r["assessment"]["status"] == C.S1_ENGINEERING_FAILURE and r["assessment"]["engineering"]["identity_mismatched_cells"]


def test_lane_l_cells_are_never_silently_dropped(tmp_path: Path) -> None:
    plan = core.Plan(seed_block_draws=(), lane_l=True)
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    d = tmp_path / "run"
    syn.write_run(d, fro, syn.Scenario())
    study = analysis.load_study(d, fro)
    assert len(study.missing) == 15 and all("lane L" in study.reasons[c] for c in study.missing)  # F-LA has no implementation here: the study is incomplete, not quietly smaller
    assert analysis.analyze_study(study, fro, gates=json.loads((d / "gates.json").read_text()))["assessment"]["status"] == C.S1_INCOMPLETE


# --- the efficiency line at registry level -----------------------------------------------------------------------------------------------
def test_efficiency_faster_slower_same_and_censoring_cases(tmp_path: Path) -> None:
    fast = syn.Scenario(a_max=a_max_all(1.0), tau=tau_by_slots(4000.0, 1000.0, 250.0))
    r, _ = run(tmp_path / "fast", fast)
    t = r["efficiency"]["steps"]["T-OQ"]["A1"]
    assert t["verdicts"] == [C.FASTER] * 5 and t["class"] == "FASTER STEP"  # T-OQ's cost per update is nearly flat in N: 0.8 of the compute holds in both measures
    f = r["efficiency"]["steps"]["F-OQ"]["A1"]
    assert f["verdicts"] == [C.FASTER_UPDATES_ONLY] * 5 and f["class"] == "UPDATES-ONLY STEP"  # F-OQ's cost per update rises 3.6x: fewer updates, not 0.8 of the compute
    slow = syn.Scenario(a_max=a_max_all(1.0), tau=tau_by_slots(250.0, 1000.0, 4000.0))
    r2, _ = run(tmp_path / "slow", slow)
    assert r2["efficiency"]["steps"]["T-OQ"]["A1"]["verdicts"] == [C.SLOWER] * 5 and r2["efficiency"]["steps"]["T-OQ"]["A1"]["class"] == "SLOWER STEP"
    assert r2["efficiency"]["arm_classes"]["T-OQ"] in ("EFFICIENCY_NOT_SUPPORTED", C.INTERMEDIATE)
    same = syn.Scenario(a_max=a_max_all(1.0), tau=tau_by_slots(1500.0, 1500.0, 1500.0))
    r3, _ = run(tmp_path / "same", same)
    assert r3["efficiency"]["steps"]["T-OQ"]["A1"]["verdicts"] == [C.SAME] * 5 and r3["efficiency"]["steps"]["T-OQ"]["A1"]["class"] == "NO DIFFERENCE"
    assert r3["efficiency"]["arm_classes"] == {"F-OQ": "EFFICIENCY_NOT_SUPPORTED", "T-OQ": "EFFICIENCY_NOT_SUPPORTED"} and r3["outcome"]["efficiency"]["label"] == C.EFFICIENCY_NEGATIVE
    # left-censored larger cell against a right-censored smaller one: REACHED ONLY BY THE LARGER (and the u_T interval is printed)
    def a_loaded(arm: str, facts: int, slots: int, rep: int) -> float:
        return 0.15 if arm == "D-OQ" else (1.0 if arm == "R2" else min(1.0, 0.7 * slots / facts))

    left = syn.Scenario(a_max=a_loaded, tau=tau_by_slots(1500.0, 40.0, 40.0))
    r4, _ = run(tmp_path / "left", left)
    v = r4["efficiency"]["steps"]["T-OQ"]["A1"]["replicates"][0]
    assert v["verdict"] == C.REACHED_ONLY and v["detail"]["u_t_large"][0] == "left" and v["detail"]["u_t_small"][0] == "right"
    assert r4["efficiency"]["steps"]["T-OQ"]["A1"]["class"] == "FASTER STEP"


def test_dense_faster_blocks_the_efficiency_positive(tmp_path: Path) -> None:
    def a_max(arm: str, facts: int, slots: int, rep: int) -> float:
        return 1.0 if arm in ("D-OQ", "R2") else min(1.0, 0.7 * slots / facts)

    def tau(arm: str, facts: int, slots: int) -> float:
        return 5.0 if arm == "D-OQ" else (200.0 if arm == "R2" else 1500.0)

    r, d = run(tmp_path, syn.Scenario(a_max=a_max, tau=tau))
    eff = r["efficiency"]
    assert eff["arm_classes"]["F-OQ"] == "EFFICIENCY_SUPPORTED" and eff["dense"]["F-OQ"] == "DENSE FASTER"  # D-OQ reaches the level in a tenth of the updates and a fraction of F-OQ's compute
    supported = [a for a in ("F-OQ", "T-OQ") if eff["arm_classes"][a] == "EFFICIENCY_SUPPORTED"]
    unblocked = [a for a in supported if eff["dense"].get(a) != "DENSE FASTER"]
    assert (r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_POSITIVE) == bool(unblocked) and "F-OQ" not in unblocked
    rendered(d)


# --- the overload row, seed block, cuts -------------------------------------------------------------------------------------------------------
def test_overload_row_changes_the_steps_and_the_reference(tmp_path: Path) -> None:
    plan = core.Plan(overload_u_p=8192, seed_block_draws=())
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    r, d = run(tmp_path, syn.Scenario(), fro)
    assert r["assessment"]["status"] == "COMPLETE" and r["assessment"]["cells_read"] == 190 + 45  # 150 + 40 trained cells; each of the 45 F-OQ cells is also read through the index
    steps = r["capacity"]["steps"]["F-OQ"]
    assert set(steps) == {"A1", "A2", "B1", "B3"} and steps["B3"]["transition"] == "16K→64K" and "B2" not in steps
    assert all(rep["ref_ok"] for rep in steps["B3"]["replicates"])  # R2 at 65,536 facts in 65,536 slots is the row's reference
    rendered(d)


def test_cut_configurations_are_analysed_with_the_cells_that_exist(tmp_path: Path) -> None:
    plan = core.Plan(seed_block_draws=(), dense_cut=("8K/64K", "32K/16K"))
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    r, d = run(tmp_path, syn.Scenario(), fro)
    assert r["assessment"]["status"] == "COMPLETE" and r["assessment"]["plan"]["dense_cut"] == ["8K/64K", "32K/16K"]
    foq = r["capacity"]["arms"]["F-OQ"]
    assert r["assessment"]["cells_read"] == 140 + 35 and foq["capacity_steps"] == ["A1", "B2"]  # B1 and A2 are not CAPACITY STEPs here, so the cut D-OQ cells are not read by any rule
    assert foq["dense_detail"]["missing"] == [] and foq["dense"] != C.DENSE_NOT_READ
    rendered(d)


def test_report_refuses_to_write_an_untagged_positive_and_never_overwrites(tmp_path: Path) -> None:
    r, d = run(tmp_path, syn.Scenario())
    broken = json.loads(json.dumps(r))
    broken["decision_map"].append("CAPACITY-POSITIVE without a tag is not tagged by the decision map's own text")
    text = report.render_markdown(broken)  # the report tags free text (tag_positives) before the final emit check
    assert C.untagged_positive_labels(text) == []
    broken["outcome"]["capacity"]["printed"] = "CAPACITY-POSITIVE"  # a printed outcome without the tag cannot be written
    with pytest.raises(C.UntaggedPositiveLabel):
        report.render_markdown(broken)
    paths = report.write_report(d, d / "results", banner=analysis_banner())
    assert [p.name for p in paths] == ["results.json", "RESULTS.md"] and "DRY" in paths[1].read_text()
    with pytest.raises(FileExistsError):
        report.write_report(d, d / "results")
    assert json.loads(paths[0].read_text())["analysis"]["assessment"]["status"] == "COMPLETE"


def analysis_banner() -> str:
    return "DRY: test banner"
