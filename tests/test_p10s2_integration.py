# ruff: noqa: E501
"""P10S2 integration of the three fix lanes (the lead's rulings of 2026-11-15): registered code refuses under pytest unless its root is a temporary directory; the cap is a computed rule; the larger-rate rule for
stand-in full-length cells; both teachers on every panel and E_open built and scored; the timing benchmark uses the stored 220908 items; the data-generation step is charged through the study ledger's
``measure`` and a guard; the bootstrap seed is drawn by the analysis stage only. Stand-in world and test seeds (229001-229999) only. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_budget import needed, rates, scale_for  # noqa: E402
from test_p10s2_classes import study  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import (  # noqa: E402
    budget,
    cells,
    core,
    recompute,
    rehearsal,
    stages,
    standins,
)
from studies.p10s2.evaluate import PanelData  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402
from studies.p10s2.prefreeze import TEACHER_PANELS  # noqa: E402
from studies.p10s2.worldio import RunConfig, build_world  # noqa: E402

CAPS = str(core.CAPS_FILE)


# --- registered code never touches the real repository, the real experiments directory or the real ledger under pytest -------------------------------------
def test_registered_code_refuses_under_pytest_unless_the_run_root_is_a_temporary_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "PYTEST_CURRENT_TEST" in __import__("os").environ
    for real in (core.REAL_ROOT, core.REAL_ROOT / "experiments", core.REAL_ROOT / "experiments" / "P10S2", core.REAL_ROOT / "studies" / "p10s2" / "freeze"):
        with pytest.raises(core.TestGuardRefused):
            core.refuse_under_pytest(real)
    core.refuse_under_pytest(tmp_path)  # a temporary directory is accepted
    assert core.is_temporary(tmp_path) and not core.is_temporary(core.REAL_ROOT)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    core.refuse_under_pytest(core.REAL_ROOT)  # the guard exists for tests only: outside pytest the real run is never blocked by it


def test_the_real_study_ledger_cannot_be_opened_or_written_by_a_test() -> None:
    real = core.REAL_ROOT / "experiments" / "P10S2" / "ledger.jsonl"
    before = real.read_bytes() if real.exists() else None
    with pytest.raises(core.TestGuardRefused):
        Ledger()  # core.ROOT is the real repository here
    with pytest.raises(core.TestGuardRefused):
        Ledger(core.REAL_ROOT / "experiments" / "P10S2" / "ledger.jsonl")
    assert (real.read_bytes() if real.exists() else None) == before  # nothing was written


@pytest.mark.parametrize("argv", [
    ["registered", "gates", "--run-dir", "RUN", "--freeze-commit", "abc", "--caps", CAPS],
    ["freeze", "--pre-run-dir", "RUN", "--run-dir", "RUN", "--data-dir", "data/x"],
    ["raise-cap", "--run-dir", "RUN"],
    ["calibrate", "--run-dir", "REAL", "--code-commit", "abc", "--stage-cap-seconds", "10", "--data-dir", "x"],
])
def test_every_stage_driver_refuses_the_real_repository_before_anything_is_started(argv: list[str], tmp_path: Path) -> None:
    real = core.REAL_ROOT / "experiments"
    existed = real.exists()
    args = [a.replace("RUN", str(tmp_path / "run")).replace("REAL", str(core.REAL_ROOT / "experiments" / "x")) for a in argv]
    with pytest.raises(core.TestGuardRefused):
        stages.main(args)
    assert not (tmp_path / "run").exists() and real.exists() == existed and not (core.REAL_ROOT / "experiments" / "P10S2").exists()  # no run directory, no ledger, no freeze file


def test_a_registered_stage_proceeds_to_its_ordinary_refusals_on_a_temporary_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(core, "ROOT", tmp_path)
    code = stages.main(["registered", "gates", "--run-dir", str(tmp_path / "run"), "--freeze-commit", "abc", "--caps", CAPS])
    assert code == 2 and "refused" in capsys.readouterr().err  # not the guard: the stage's own refusal (the code is not under the checked repository)


# --- the cap is a computed rule -------------------------------------------------------------------------------------------------------------------
def test_the_cap_is_36_else_the_smallest_whole_hour_up_to_72_else_72() -> None:
    p = 3.5
    assert budget.computed_cap(p, rates(scale_for(16.0, 4, 2000))) == 36.0
    k = scale_for(20.28, 4, 2000)
    assert budget.computed_cap(p, rates(k)) == float(math.ceil(needed(p, k))) and 36 < budget.computed_cap(p, rates(k)) <= 72
    assert budget.computed_cap(p, rates(scale_for(40.0, 4, 2000))) == 72.0  # rung 1 needs more than the ceiling: 72, with the rung order applied against 72
    huge = rates(scale_for(200.0, 4, 2000))
    assert budget.computed_cap(p, huge) == 72.0 and budget.rehearsal_rule(p, huge, 72.0).outcome == budget.NOT_STARTED_BUDGET  # no rung fits: NOT STARTED: BUDGET


def test_a_recorded_cap_other_than_the_computed_one_is_refused(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("rehearsal", 3.5 * 3600)
    r = rates(scale_for(20.28, 4, 2000))
    computed = budget.computed_cap(led.total_hours(), r)
    path = tmp_path / "cap_raise.json"
    led.append_cap_raise(computed - 1, {})  # a raise the rule did not compute
    path.write_text(json.dumps({"new_cap_hours": computed - 1}))
    with pytest.raises(budget.CapRefused, match="computed by the rule"):
        budget.verify_raise(path, led.total_hours(), r, led)
    base = Ledger(tmp_path / "base.jsonl")
    base.record("rehearsal", 3.5 * 3600)
    with pytest.raises(budget.CapRefused, match="computed by the rule"):
        budget.verify_raise(tmp_path / "none.json", base.total_hours(), r, base)  # the base cap where the rule requires a raise: a declined raise is not allowed


# --- the larger-rate rule for stand-in full-length cells --------------------------------------------------------------------------------------------
def test_a_stand_in_full_length_cell_uses_the_larger_of_its_rate_and_the_types_own_rate_and_the_record_says_so() -> None:
    short = {"ST1@L4": 0.2, "MAF@L4": 0.5, "MII@L4": 0.9, "MSEQ@L4": 0.1, "MAGOLD@L4": 0.3, "LORA1": 0.4, "LSEQ": 0.9, "LJOINT": 0.7}
    full = {"ST1": 0.3, "MII": 1.2, "LORA1": 0.6}
    used, rec = rehearsal.full_length_rates(short, full, 4)
    assert used["ST1@L4"] == 0.3 and used["MII@L4"] == 1.2 and used["LORA1"] == 0.6  # a cell stands in for its own type: its own rate
    assert used["MAF@L4"] == 0.5 and used["MSEQ@L4"] == 0.3 and used["MAGOLD@L4"] == 0.3  # the larger of the ST1 rate (0.3) and the type's own 200-update rate
    assert used["LSEQ"] == 0.9 and used["LJOINT"] == 0.7  # L-seq: the larger of the LoRA cell's 0.6 and its own 0.9; L-joint was not stood in for
    assert set(rec) == {"MAF@L4", "MSEQ@L4", "MAGOLD@L4", "LSEQ"} and rec["MAF@L4"]["full_length_cell"] == "ST1" and rec["LSEQ"]["full_length_cell"] == "LORA1" and rec["MSEQ@L4"]["used"] == 0.3 and rec["MAF@L4"]["own_short_run_rate"] == 0.5


# --- both teachers on every panel; E_open built and scored ----------------------------------------------------------------------------------------------
def test_both_teachers_generate_on_every_panel_section_6_1_names() -> None:
    world, _ = dry_world()
    assert TEACHER_PANELS == ("E_A", "E_B", "E_C", "E_open", "D_cal", "D_con")
    for c in core.TASKS:
        assert set(world.teacher_outputs[c]) == set(TEACHER_PANELS)
        for name in TEACHER_PANELS:
            assert len(world.teacher_outputs[c][name]) == len(world.partition.panels[name]), (c, name)


def with_open_panel(n: int = 3):  # type: ignore[no-untyped-def]
    """The stand-in bundle with a stand-in E_open (the synthetic corpus has no evaluation sentence with an out-of-vocabulary word at this size, so the first D_cal items fill it; the point is the mechanics of building and scoring it)."""
    bundle, _ = standins.build_synthetic_bundle(1)
    items = bundle.panels["D_cal"][:n]
    bundle.panels["E_open"] = list(items)
    for c in core.TASKS:
        bundle.teacher_outputs[c]["E_open"] = list(bundle.teacher_outputs[c]["D_cal"][:n])
    return bundle


def test_e_open_is_built_per_capability_scored_under_the_oracle_route_and_never_enters_a_gap_or_the_timing() -> None:
    bundle = with_open_panel()
    world = build_world(bundle, "test", 1, RunConfig.dry())
    names = list(world.ctx.panels)
    assert names[:2] == ["E_A", "E_B"] and {"E_open_A", "E_open_B"} <= set(names)
    for c in core.TASKS:
        p = world.ctx.panels["E_open_" + c]
        assert isinstance(p, PanelData) and p.task == c and len(p.examples) == len(p.refs) == len(p.source_index or ()) and all(p.refs)
    assert cells.gap_panels(world.ctx) == ["E_A", "E_B"]  # no gap, ablation, learned route or timing on E_open
    s0 = cells.stage0_scores(world, with_combined=False)
    assert {"E_open_A", "E_open_B"} <= set(s0["student"]) and "subsample" not in s0["student"]["E_open_A"]
    assert {"E_open_A", "E_open_B"} <= set(s0["teacher"]) and set(s0["teacher"]["E_A"]) >= {"mean", "subsample_mean"}  # each teacher is scored on E_open too, on the items that carry a reference in its language
    assert all(0.0 <= v <= 1.0 for v in s0["teacher"]["E_open_A"]["items"])
    from studies.p10s2 import gates

    assert not any(x.startswith("E_open") for x in gates.g2(world)["undefined_gaps"])  # G2 reads the gap panels only
    snap = cells.score_snapshot(world, 0, __import__("studies.p10s2.memory", fromlist=["NullArm"]).NullArm(), router=None, ablation_stages=None, ablation_tasks=(), gen=False)
    assert {"E_open_A", "E_open_B"} <= set(snap["panels"]) and "E_open_A" not in snap.get("learned_route", {})


def test_a_world_without_an_e_open_panel_builds_no_e_open_entry() -> None:
    world, _ = dry_world()
    assert not any(n.startswith("E_open") for n in world.ctx.panels)


# --- the timing benchmark uses the stored 220908 items --------------------------------------------------------------------------------------------------
def test_the_timing_benchmark_uses_the_stored_items_and_a_registered_world_without_them_is_refused() -> None:
    world, _ = dry_world()
    assert set(world.timing_items) == {"E_A", "E_B"}
    p = world.ctx.panels["E_A"]
    assert stages._timing_indices(world, "E_A", p, 10**6) == world.timing_items["E_A"]
    assert stages._timing_indices(world, "E_A", p, 2) == world.timing_items["E_A"][:2]
    import dataclasses

    with pytest.raises(stages.StageRefused, match="no entry for panel"):
        stages._timing_indices(dataclasses.replace(world, timing_items={"E_B": [0]}), "E_A", p, 5)
    with pytest.raises(stages.StageRefused, match="no stored timing items"):
        stages._timing_indices(dataclasses.replace(world, timing_items={}, mode="registered-run"), "E_A", p, 5)
    assert stages._timing_indices(dataclasses.replace(world, timing_items={}, mode="rehearsal"), "E_A", p, 3) == [0, 1, 2]  # the rehearsal times the first calibration items


# --- the bootstrap seed is drawn by the analysis stage only -----------------------------------------------------------------------------------------------
def test_intervals_and_the_bootstrap_seed_belong_to_the_analysis_stage_and_the_compared_analyses_draw_nothing() -> None:
    s = study()
    rs = copy.deepcopy(s)
    core.reset_seed_record()
    plain = recompute.outcome_under_recomputation(s, rs, recompute.FROZEN)
    assert plain["intervals_computed"] is False and core.seed_record() == []  # without a bootstrap mode no interval is computed and 220906 is not drawn, in the compared analyses either
    out = recompute.outcome_under_recomputation(s, rs, recompute.FROZEN, bootstrap_mode="test", bootstrap_resamples=20)
    drawn = core.seed_record()
    assert out["intervals_computed"] is True and drawn and {u.seed for u in drawn} == {core.partition_seeds("test")["bootstrap"]} and len(drawn) == sum(1 for e in out["intervals"] if e["lo"] is not None)  # one fresh generator per printed interval (a score with no per-item values has none and draws nothing), only in the printed analysis
    core.reset_seed_record()
    with pytest.raises(core.SeedRefused):
        core.bootstrap_generator("registered-data", "x")
    core.reset_seed_record()


def test_the_comparator_is_the_one_verdict_function() -> None:
    assert not hasattr(recompute, "verdict_view") and not hasattr(recompute, "outcome_changes") and not hasattr(__import__("studies.p10s2.analysis", fromlist=["x"]), "analyze_with_recomputation")
    assert not hasattr(__import__("studies.p10s2.gates", fromlist=["x"]), "record_code_seeds") and not hasattr(__import__("studies.p10s2.analysis", fromlist=["x"]), "bootstrap_generator")


def test_e_open_scores_are_printed_with_an_interval_and_change_no_gate_class_or_label() -> None:
    from test_p10s2_classes import cell, panel

    from studies.p10s2 import analysis, report

    s = study()
    base = analysis.analyze(s)
    s2 = copy.deepcopy(s)
    s2["baseline"]["student"]["E_open_A"] = {"panel": panel(0.3)}
    s2["baseline"]["teacher"]["E_open_A"] = panel(0.6)
    for r in range(len(s2["replicates"])):
        c = cell(s2, r, "ST1", "AB")
        c["scores"][c["label"]]["panels"]["E_open_A"] = panel(0.5)
    out = analysis.analyze(s2, bootstrap_mode="test", bootstrap_resamples=20)
    assert any("E_open_A" in e["name"] for e in out["intervals"]) and (out["label"], out["label_row"]) == (base["label"], base["label_row"])  # descriptive: no gate, class or label reads it
    assert analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts(s2)) == []
    assert "not scored in this record" not in report.render_report(out)
    core.reset_seed_record()
