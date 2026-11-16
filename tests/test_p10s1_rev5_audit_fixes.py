# ruff: noqa: E501
"""P10S1 revision 5, fixes of the independent audit (AUDIT_REV5.md) under the lead's rulings (ADR-0021 section 25.13): the item caps under the pool's dispatch order (B1), the finalize commands refusing
while their stage is incomplete (M1), the contention ratio from the rehearsal only (M2), the milestone reading and the saturation sub-labels (M3), the freeze and the evidence about P10-S0 (M4), the
placeholder plan (m1), a directed transition (m5) and H8 annotations (m7). The process list is injected in every test. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s1_model import job  # noqa: E402
from test_p10s1_rev5_calibration import write_cell  # noqa: E402
from test_p10s1_rev5_lines import FRO, run  # noqa: E402
from test_p10s1_stages import (  # noqa: E402, F401
    fake_projection,
    freeze_argv,
    no_other_study_running,
    run_dir_with_draws,
)

from studies.p10s1 import budget, calibrate, core, stages, train  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

# revision 4's measured wall seconds per update (training wall; the calibration of 2026-11-15) at the sizes it had, and the audit's assumption for the rest
WALL = {("F-OQ", 256): 0.004, ("F-OQ", 1024): 0.006, ("F-OQ", 4096): 0.0093, ("F-OQ", 16384): 0.0153, ("T-OQ", 1024): 0.006, ("T-OQ", 4096): 0.0093, ("T-OQ", 16384): 0.0153, ("H8", 1024): 0.005, ("H8", 4096): 0.0075,
        ("H8", 16384): 0.0101, ("D-OQ", 1024): 0.009, ("D-OQ", 4096): 0.0118, ("D-OQ", 16384): 0.0235, ("R2", 4096): 0.0091, ("R2", 16384): 0.0102, ("R2", 32768): 0.0188}  # fmt: skip


# --- B1: item caps under the dispatch order the pool will use -----------------------------------------------------------------------------------------
def test_item_caps_are_computed_from_the_pooled_dispatch_order_and_no_run_passes_its_deadline() -> None:
    ordered = budget.dispatch_order(("load", "row-up"))
    assert [i for i, _c in ordered][:12] == ["row-up"] * 12 and {i for i, _c in ordered[12:]} == {"load"}  # the 12 short runs come first
    loads = [c.run_updates for i, c in ordered if i == "load"]
    assert loads == sorted(loads, reverse=True)  # the longest load-search run first within its item
    for scale in (1.0, 2.0):  # assumed rates: as measured, and every rate doubled
        wall = {k: v * scale for k, v in WALL.items()}
        proj = budget.item_projection(wall)
        times = budget.simulate_dispatch([c.run_updates * wall[(c.arm, c.slots)] for _i, c in ordered])
        for (item, _c), (start, end) in zip(ordered, times, strict=True):
            assert end <= proj[item]["cap_seconds"] / 2.0 + 1e-6 and start < proj[item]["cap_seconds"] and end < proj[item]["cap_seconds"]  # no run starts or ends after its item's deadline
        assert proj["row-up"]["projected_wall_seconds"] < proj["load"]["projected_wall_seconds"]
    # what the audit found: the same runs in the order load-search first would start the row-U_P runs after the item-1 deadline
    wall = WALL
    bad = [("load", c) for c in core.load_search_cells()] + [("row-up", c) for c in core.row_u_p_cells()]
    t = budget.simulate_dispatch([c.run_updates * wall[(c.arm, c.slots)] for _i, c in bad])
    row_cap = budget.item_projection(wall)["row-up"]["cap_seconds"]
    assert any(start > row_cap for (item, _c), (start, _e) in zip(bad, t, strict=True) if item == "row-up")
    # items 2 and 3: h8 first, then dense; the caps cover the dispatch the same way
    ordered_b = budget.dispatch_order(("h8", "dense"), row_u_p={2048: 8192, 8192: 8192, 32768: 16384})
    pb = budget.item_projection(wall, row_u_p={2048: 8192, 8192: 8192, 32768: 16384})
    tb = budget.simulate_dispatch([c.run_updates * wall[(c.arm, c.slots)] for _i, c in ordered_b])
    assert all(end < pb[i]["cap_seconds"] for (i, _c), (_s, end) in zip(ordered_b, tb, strict=True))


def test_the_dispatch_simulation_is_list_order_on_the_first_free_worker() -> None:
    assert budget.simulate_dispatch([5.0, 5.0, 1.0], 2) == [(0.0, 5.0), (0.0, 5.0), (5.0, 6.0)]
    assert budget.simulate_dispatch([3.0, 1.0, 1.0, 1.0], 2) == [(0.0, 3.0), (0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]


def test_a_deadline_that_has_not_passed_stops_a_run_in_flight_and_a_distant_one_does_not(tmp_path: Path) -> None:
    far = job(tmp_path, "F-OQ", slots=1024, updates=4, snapshots=(4,), name="far")
    far.deadline_epoch = time.time() + 3600.0
    assert train.train_cell(far)["status"] == "completed"
    soon = job(tmp_path, "F-OQ", slots=1024, updates=100000, snapshots=(100000,), name="soon")
    soon.deadline_epoch = time.time() + 0.5  # not yet passed when the run starts
    with pytest.raises(train.ItemCapReached):
        train.train_cell(soon)
    rec = core.read_record(soon.out_dir / "train.json", "train")
    assert rec["status"] == "failed" and "ItemCapReached" in str(rec["reason"]) and "update 0 of" not in str(rec["reason"])  # stopped mid-run, not at update 0


# --- M1: finalize refuses while its stage is incomplete -------------------------------------------------------------------------------------------------
def test_finalize_refuses_without_the_stage_manifest_and_with_a_run_that_has_no_record(tmp_path: Path) -> None:
    unit = 16
    run_dir = tmp_path / "cal"
    cells = core.calibration_cells_of(("load", "row-up"), None, unit)
    for c in cells:
        write_cell(run_dir, c, lambda cell, u: 2.0)
    common = ["--dry", "--run-dir", str(run_dir), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    assert stages.main(["calibrate", "--finalize-items", "load,row-up", *common]) == 2  # no stage manifest: the runs may still be in progress
    assert not (run_dir / stages.ITEMS_FILE).exists()
    with pytest.raises(calibrate.NotComplete):
        calibrate.require_stage_complete(run_dir, "calibrate-load-row-up", cells)
    manifest = {**core.envelope("stage_manifest"), "tasks": [{"label": c.label, "status": "completed"} for c in cells]}
    core.write_record(run_dir / "calibrate-load-row-up" / "manifest.json", manifest)
    assert calibrate.require_stage_complete(run_dir, "calibrate-load-row-up", cells)["no_record"] == []
    missing = cells[0]
    (core.cell_dir(run_dir, missing.label) / "train.json").unlink()
    with pytest.raises(calibrate.NotComplete, match="no train record"):
        calibrate.require_stage_complete(run_dir, "calibrate-load-row-up", cells)  # a run without a record that the manifest does not list as not run
    manifest["tasks"][0]["status"] = "not_started"
    core.write_record(run_dir / "calibrate-load-row-up" / "manifest.json", manifest)
    assert calibrate.require_stage_complete(run_dir, "calibrate-load-row-up", cells)["no_record"] == [f"{missing.label}: not_started"]  # listed, and the finalize record carries it
    assert stages.main(["calibrate", "--finalize", *common]) == 2 and not (run_dir / "calibration.json").exists()  # items 0b and 1 not finalized yet


def test_a_dense_run_without_a_record_is_not_a_diverged_rate(tmp_path: Path) -> None:
    unit = 16
    rows = dict.fromkeys(core.ROW_FACTS, 16)
    run_dir = tmp_path / "cal"
    dense = core.dense_rate_cells(rows, unit)
    gone = next(c for c in dense if c.lr == 0.01 and c.slots == 1024 and c.draw == 2)
    for c in dense:
        if c.label != gone.label:
            write_cell(run_dir, c, lambda cell, u: 0.5 + cell.lr)
    rec = calibrate.finalize_h8_dense(run_dir, rows, unit=unit)
    unit_rec = rec["dense_rates"]["8K/1K"]
    assert unit_rec["action"] == calibrate.RETURN_TO_LEAD and "without a record" in unit_rec["reason"] and 0.01 not in unit_rec["diverged"]


# --- M2: c from the rehearsal only -----------------------------------------------------------------------------------------------------------------------
def test_c_is_the_rehearsals_and_the_calibrations_ratio_is_descriptive() -> None:
    iso = {("F-OQ", 4096): 0.010, ("D-OQ", 16384): 0.020}
    c, reh, cal = stages.contention_from({("F-OQ", 4096): 0.0105, ("D-OQ", 16384): 0.0200}, {("F-OQ", 4096): 0.0300}, iso)
    assert c == pytest.approx(1.05) and cal["c"] == pytest.approx(3.0) and reh["c"] == c  # a calibration that overlapped another study does not move c
    assert stages.contention_from({("F-OQ", 4096): 0.009}, {("F-OQ", 4096): 0.05}, iso)[0] == 1.0  # never below 1.0


# --- M3: the milestone reading reads only the capacity dense label ----------------------------------------------------------------------------------------
def test_the_saturation_sub_labels_refuse_nothing_in_both_directions() -> None:
    work = {"F-OQ": C.LINEAR_KEY_SCORING, "T-OQ": C.SUBLINEAR, "F-OQ-IVF": C.SUBLINEAR}

    def arms(dense: str, sub: list[str], ds: str = C.SAME_AT_SATURATION) -> dict[str, C.ArmCapacity]:
        return {a: C.ArmCapacity(a, C.CAPACITY_SUPPORTED, dense, sat_class=C.SAT_PROPORTIONAL_ALL_PAIRS, dense_sat=ds, dense_sat_sublabels=list(sub)) for a in core.LEARNED_KEY_ARMS}

    for sub in ([], [C.DENSE_NOT_ESTABLISHED], [C.DENSE_STILL_RISING], [C.DENSE_NOT_LEARNED]):
        a = arms(C.DENSE_MATCHES, sub)
        out = C.capacity_outcome(a, engineering_failed=False, incomplete=False)
        assert C.milestone_reading(out, a, work, C.TREE_AHEAD, "S0 X").startswith("Storage half supported")  # whatever the descriptive sub-label
    not_est = arms(f"{C.DENSE_NOT_ESTABLISHED} (MC-SHORT)", [])
    assert C.milestone_reading(C.capacity_outcome(not_est, engineering_failed=False, incomplete=False), not_est, work, C.TREE_AHEAD, "S0 X").startswith("Storage-half reading not available")  # the capacity dense label decides
    one_cond = C.dense_at_saturation([C.SatDenseCell("8K/1K", [dict.fromkeys(core.PANELS, (1.0, 1.5))] * 5, [dict.fromkeys(core.PANELS, C.PLATEAUED)] * 5, False), C.SatDenseCell("32K/4K", [dict.fromkeys(core.PANELS, (1.0, 1.5))] * 5, [dict.fromkeys(core.PANELS, C.PLATEAUED)] * 5, True)])
    assert one_cond["sublabels"] == [C.DENSE_NOT_ESTABLISHED]  # exactly one condition fails: the sub-label is printed, and descriptive
    two = C.dense_at_saturation([C.SatDenseCell("8K/1K", [dict.fromkeys(core.PANELS, (1.0, 1.5))] * 5, [dict.fromkeys(core.PANELS, C.RISING)] * 5, False)])
    assert two["sublabels"] == []  # two conditions fail: none


# --- M4: the freeze, P10-S0 and the evidence ------------------------------------------------------------------------------------------------------------------
def test_the_freeze_refuses_while_an_s0_or_s2_stage_is_alive_and_binds_the_evidence_by_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10s1 import timing

    paths = fake_projection(tmp_path)
    run = run_dir_with_draws(tmp_path)
    argv = freeze_argv(paths, run, tmp_path / "f")
    evidence = Path(argv[argv.index("--s0-training-manifest") + 1])
    monkeypatch.setattr(timing, "running_commands", lambda: ["python -m studies.p10s0.stages train --run-dir /x"])
    assert stages.main(argv) == 2 and not (tmp_path / "f").exists()  # a stage process is alive
    monkeypatch.setattr(timing, "running_commands", lambda: [])
    without = [a for i, a in enumerate(argv) if a not in ("--s0-training-manifest", str(evidence)) or i < 2]
    assert "--s0-training-manifest" not in without
    assert stages.main(without) == 2 and not (tmp_path / "f").exists()  # no evidence of S0's last training stage: the freeze does not state that it finished
    assert stages.main(argv) == 0
    rec = json.loads((tmp_path / "f" / "plan.json").read_text())
    assert rec["concurrency"]["checked"] and rec["concurrency"]["s0_training_manifest"]["sha256"] == core.file_sha256(evidence) and "evidence bound by hash" in rec["concurrency"]["statement"]
    refusal = tmp_path / "refusal.json"
    refusal.write_text("{}")
    assert stages.main([*freeze_argv(paths, run, tmp_path / "g"), "--s0-refusal-record", str(refusal)]) == 0
    assert json.loads((tmp_path / "g" / "plan.json").read_text())["concurrency"]["s0_refusal_record"]["sha256"] == core.file_sha256(refusal)
    assert stages.main([*freeze_argv(paths, run, tmp_path / "h"), "--s0-refusal-record", str(tmp_path / "nope.json")]) == 2


# --- m1: a placeholder plan -----------------------------------------------------------------------------------------------------------------------------------
def test_a_plan_with_default_u_l_is_a_placeholder_and_is_never_frozen(tmp_path: Path) -> None:
    assert core.Plan().placeholder and not core.Plan(u_l=(65536, 131072)).placeholder and core.Plan.from_json(core.Plan().as_json()).placeholder
    assert not core.Plan(u_l=(65536, 131072)).as_json()["placeholder"] and all(p.placeholder for p in core.plan_configurations())
    paths = fake_projection(tmp_path)
    rec = core.read_record(paths["projection"], "projection")
    rec["chosen"]["plan"] = core.Plan((1,), ("8K/16K",)).as_json()
    core.write_record(paths["projection"], rec)
    assert stages.main(freeze_argv(paths, run_dir_with_draws(tmp_path), tmp_path / "f")) == 2 and not (tmp_path / "f").exists()


# --- m5, m7 -----------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_directed_transition_fixes_the_pairs_that_use_its_loaded_cell_as_not_full(tmp_path: Path) -> None:
    fro = fz.Frozen.build(core.Plan(seed_block_draws=(1,)), fz.default_cpu_table(), no_loaded_transitions=["1K→4K"])
    r, _ = run(tmp_path, __import__("studies.p10s1.synthetic", fromlist=["x"]).Scenario(), fro)
    sat = r["saturation"]["arms"]
    assert sat["F-OQ"]["pairs"]["1024→4096"]["class"] == C.NOT_FULL and sat["F-OQ"]["pairs"]["256→1024"]["class"] == C.NOT_FULL and sat["T-OQ"]["class"] == C.SAT_NOT_MEASURED
    assert r["outcome"]["saturation"]["label"] == C.SAT_NOT_MEASURED_OUTCOME and FRO.no_loaded_transitions == []


def test_a_failed_or_missing_h8_run_leaves_the_cell_not_calibrated() -> None:
    acc = {(c, d, p): 0.95 for c in ("2K/4K", "8K/4K", "8K/16K") for d in (1, 2) for p in "AB"}
    for d in (1,):
        for p in "AB":
            acc[("32K/16K", d, p)] = 0.95  # draw 2 of 32K/16K failed
    rep = calibrate.h8_report(acc)
    assert rep["calibrated_cells"] == ["2K/4K", "8K/16K", "8K/4K"] and rep["annotations"]["32K/16K"] == "H8 NOT CALIBRATED AT 32K/16K" and "2K/4K" not in rep["annotations"]
