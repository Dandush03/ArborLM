# ruff: noqa: E501
"""P10S1: the audit's fixes and the lead's rulings (ADR-0021 section 22), one test per changed rule: M1 (Study B reads the I_use ratio), M2 (every label form is tagged and printable), M3
(the registered driver takes no override, registered mode only through the fixed path, the worker checks the frozen plan, the generation cap comes from the config), M4 (Decision 2 outside the
hashed specification), M5 (DENSE MATCHES only where the matched-compute reading is established; D-OQ far behind in an MC-SHORT pair never prints it), M6 (whole-update multiply-adds equal torch's
FLOP counter), M7 (the dense-rate tie rule), (g) DEP at every snapshot, (h) panel rules, (k) DENSE NOT READ and DENSE SPEED UNDECIDED, (n) both panels in the robustness readout, m13
(per-transition CAPACITY NOT TESTED), (b) lane L returning to the lead, m14 (the section 10.2 scenarios), m15 (identity drift), m4 (the generation cap is a config value). Synthetic records and
the unit-test seed sets only. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import canonical_json, file_sha256, sha256  # noqa: E402
from studies.p9 import pool  # noqa: E402
from studies.p10s1 import analysis, calibrate, core, stages  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLAN = core.Plan(seed_block_draws=(1,))
FRO = fz.Frozen.build(PLAN, fz.default_cpu_table())


def run(tmp: Path, scn: syn.Scenario, fro: fz.Frozen = FRO) -> tuple[dict[str, Any], Path]:
    d = tmp / "run"
    syn.write_run(d, fro, scn)
    result = analysis.analyze_study(analysis.load_study(d, fro), fro, gates=json.loads((d / "gates.json").read_text()))
    return result, d


# --- M1: Study B tests the ratio of I_use, not of i ----------------------------------------------------------------------------------
# --- M2: every label form is tagged and printable ------------------------------------------------------------------------------------
def test_every_adr_label_form_passes_the_tag_check() -> None:
    forms = (
        "BEATS DENSE (DENSE AT CHANCE AT 8K/64K)",
        "BEATS DENSE",
        "DENSE MATCHES",
        "FASTER",
        "FASTER IN UPDATES ONLY",
        "REACHED ONLY BY THE LARGER",
        "CAPACITY STEPs",
        "CAPACITY STEPS",
        "KNOWLEDGE SCALES WITH MEMORY",
    )
    for form in forms:
        if C.is_positive(form):
            assert C.untagged_positive_labels(form), form  # bare, it is caught
            tagged = f"{form} [{core.STORE_ONLY_TAG}]"
            assert C.untagged_positive_labels(tagged) == [], tagged
            assert C.emit(C.tag_positives(form))
    assert C.untagged_positive_labels("BEATS DENSE (DENSE AT CHANCE AT 8K/64K) [STORE ONLY; ORACLE-ADDRESSED; detail]") == []
    assert C.untagged_positive_labels("DENSE NOT FASTER and NOT FASTER and DENSE NOT ESTABLISHED AT MATCHED COMPUTE (MC-SHORT)") == []  # negations are not positive labels
    chance = C.dense_label([_cell(1.0, None, 0.03)])["label"]
    assert chance.startswith(C.BEATS_DENSE) and "DENSE AT CHANCE" in chance and C.printable(chance)  # printable() no longer raises on this form
    assert "BEATS DENSE (DENSE AT CHANCE AT" in C.printable(chance)


# --- M5 and (k): the dense reading ----------------------------------------------------------------------------------------------------
def _cell(d: float, r: float | None, dense_a: float = 0.4, status: str = "OK") -> C.DenseCell:
    rep = {"MU": dict.fromkeys(core.PANELS, (d, r, dense_a)), "MC": dict.fromkeys(core.PANELS, (d, r, dense_a)), "D-BEST": dict.fromkeys(core.PANELS, (d, r, dense_a))}
    return C.DenseCell("A1", [rep] * 5, mc_status=status)


def test_dense_matches_is_printed_only_where_the_matched_compute_reading_is_established() -> None:
    assert C.dense_label([_cell(1.0, 1.05)])["label"] == C.DENSE_MATCHES  # established (OK)
    for status in ("MC-SHORT", "MC-AMBIGUOUS"):
        got = C.dense_label([_cell(1.0, 1.05, status=status)])
        assert got["label"] != C.DENSE_MATCHES and C.dense_not_established(got["label"]) and status in got["label"]
        assert got["label"] == f"DENSE NOT ESTABLISHED AT MATCHED COMPUTE ({status})"
    far_behind = C.dense_label([_cell(1.0, 1.05, dense_a=0.05, status="MC-SHORT")])  # D-OQ far behind in an MC-SHORT pair: still not DENSE MATCHES
    assert far_behind["label"] != C.DENSE_MATCHES and "NOT ESTABLISHED" in far_behind["label"]
    assert far_behind["mu_text"]  # the matched-updates comparison is printed descriptively


def _rendered(d: Path, result: dict[str, Any]) -> str:
    from studies.p10s1 import report

    core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": result}))
    text = report.write_report(d, d / "results")[1].read_text()
    assert C.untagged_positive_labels(text) == [] and core.STORE_ONLY_TAG in text
    return text


def test_dense_ahead_either_panel_blocks_and_beats_dense_needs_both_panels() -> None:
    def cell(panel_a: tuple[float, float | None, float], panel_b: tuple[float, float | None, float]) -> C.DenseCell:
        rep = {k: {"A": panel_a, "B": panel_b} for k in ("MU", "MC", "D-BEST")}
        return C.DenseCell("A1", [rep] * 5)

    ahead_a = (-0.4, 0.8, 0.9)
    fine = (1.0, 1.2, 0.4)
    assert C.dense_label([cell(ahead_a, fine)])["label"] == C.DENSE_AHEAD  # a blocking label counts if either panel satisfies it
    assert C.dense_label([cell(fine, ahead_a)])["label"] == C.DENSE_AHEAD
    assert C.dense_label([cell(fine, fine)])["label"] == C.BEATS_DENSE
    assert C.dense_label([cell(fine, (1.0, 1.05, 0.4))])["label"] != C.BEATS_DENSE  # a store-favouring label needs both panels


def test_dense_not_read_and_dense_speed_undecided() -> None:
    c = {"cpu": 1.0, "madds": 1.0}
    exact = lambda v: [C.UT("exact", v, v)] * 2  # noqa: E731
    assert C.dense_faster([exact(2000.0)] * 5, [None] * 5, c, c) == C.DENSE_NOT_READ
    assert C.dense_faster([exact(2000.0)] * 5, [exact(1000.0)] * 5, c, c) == "DENSE FASTER"
    undecided = C.dense_faster([[C.UT("left", 0.0, 2000.0)] * 2] * 5, [exact(1000.0)] * 5, c, c)  # the arm's u_T is left-censored: not decided from the bounds
    assert undecided == C.DENSE_SPEED_UNDECIDED
    assert C.dense_faster([exact(2000.0)] * 5, [exact(1900.0)] * 5, c, c) == "DENSE NOT FASTER"
    out = C.efficiency_outcome({"F-OQ": "EFFICIENCY_SUPPORTED", "T-OQ": "EFFICIENCY_NOT_SUPPORTED"}, {"F-OQ": C.DENSE_SPEED_UNDECIDED}, engineering_failed=False, incomplete=False)
    assert out.label == C.EFFICIENCY_POSITIVE and C.DENSE_SPEED_UNDECIDED in out.printed  # neither blocks; the bracket carries the label
    out = C.efficiency_outcome({"F-OQ": "EFFICIENCY_SUPPORTED", "T-OQ": "EFFICIENCY_NOT_SUPPORTED"}, {}, engineering_failed=False, incomplete=False)
    assert out.label == C.EFFICIENCY_POSITIVE and C.DENSE_NOT_READ in out.printed


# --- (g): DEP at every snapshot ---------------------------------------------------------------------------------------------------------
def test_dep_is_read_at_every_snapshot_up_to_the_run_length() -> None:
    u_p, run_large = core.U_P, core.run_length("F-OQ", 16384)
    run_small = core.run_length("F-OQ", 4096)

    def obs(a: float, ok: bool = True) -> C.PanelObs:
        n, chance = 2048, 64
        useful = int(round(a * n))
        return C.PanelObs(n, useful, useful, chance if ok else n // 2, chance, chance, 2048, 64)

    sat = lambda a, u: a * (1.0 - math.exp(-u / 1500.0))  # noqa: E731
    small = C.View({u: obs(sat(0.35, u)) for u in core.snapshot_updates(u_p, run_small, (3 * u_p,))}, run_small, u_p)
    clean = C.View({u: obs(sat(0.99, u)) for u in core.snapshot_updates(u_p, run_large)}, run_large, u_p)
    mc = C.McEntry("OK", 3 * u_p, u_p, 3.0, "small")
    assert C.capacity_panel(small, clean, mc, ref_ok=True, leakage=False).verdict == C.CAPACITY
    odd = u_p // 4  # a snapshot that is neither U_P nor an MC readout
    assert odd in clean.updates and odd not in (u_p, mc.large_update, mc.small_update)
    broken = C.View({u: obs(sat(0.99, u), ok=u != odd) for u in clean.updates}, run_large, u_p)
    assert broken.dep(odd) is False
    assert C.capacity_panel(small, broken, mc, ref_ok=True, leakage=False).verdict == C.DEPENDENCE_FAILED


# --- m13: a transition directed to run with no loaded row is CAPACITY NOT TESTED, per transition ----------------------------------------
def test_directed_no_loaded_transition_prints_capacity_not_tested(tmp_path: Path) -> None:
    transition = next(iter(analysis.transitions_of(PLAN)))
    fro = fz.Frozen.build(PLAN, fz.default_cpu_table(), no_loaded_transitions=[transition])
    r, d = run(tmp_path, syn.Scenario(), fro)
    cap = r["outcome"]["capacity"]
    assert cap["label"] == C.CAPACITY_NOT_TESTED and transition in cap["printed"] and cap["label"] != C.CAPACITY_NEGATIVE
    assert all(a["class"] != C.CAPACITY_SUPPORTED for a in r["capacity"]["arms"].values())
    assert any(C.NOT_LOADED in a["effective_step_classes"].values() for a in r["capacity"]["arms"].values())
    _rendered(d, r)


# --- (n): robustness for both panels -----------------------------------------------------------------------------------------------------
def test_robustness_is_printed_for_both_panels(tmp_path: Path) -> None:
    r, d = run(tmp_path, syn.Scenario())
    rob = r["capacity"]["robustness"]["T-OQ"]
    for v in rob.values():
        assert "label" in v and "panel_B" in v and "label" in v["panel_B"]
    assert "panel B" in _rendered(d, r) or "panel_B" in json.dumps(rob)


# --- M6: whole-update multiply-adds against torch's FLOP counter ------------------------------------------------------------------
def test_madds_formula_is_in_the_config_and_equals_the_flop_counter() -> None:
    import torch
    from torch.utils.flop_counter import FlopCounterMode

    from studies.p9 import controls
    from studies.p9 import core as p9core
    from studies.p9 import data as data_mod
    from studies.p9i.train import alphabet_loss
    from studies.p10s1 import model as M
    from studies.p10s1 import train as T

    assert core.load_config()["cost"]["madds_formula"] == core.MADDS_FORMULA
    corpus = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
    seeds = core.test_seeds(1)
    data = data_mod.build_study_data(seeds, corpus, sizes=data_mod.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128))
    backbone = controls.synthetic_backbone(101, 301)
    tokens = T.training_stream_for(data, 128).batch(1).tokens
    lut = T.fact_lut_for(data, 128)
    for arm, slots in (("F-OQ", 4096), ("T-OQ", 4096), ("H8", 4096), ("R2", 4096), ("D-OQ", 4096), ("F-OQ", 16384)):
        model = M.build_model(arm, slots, 1, backbone, fact_lut=lut, r1_seed=seeds.r1_codes, hash_seed=5, seed_rng=False)
        model.train()
        params = [p for _, p in model.trainable()]
        with FlopCounterMode(display=False) as counter:
            logits, _ = model(tokens[:, :-1])
            loss = alphabet_loss(logits, tokens)
            torch.autograd.grad(loss, params, allow_unused=True)
        assert counter.get_total_flops() // 2 == fz.matmul_madds_per_update(arm, slots), (arm, slots)
    # the whole-update count adds the frozen backbone's forward and backward and 4 x trainable for AdamW
    assert fz.analytic_madds_per_update("F-OQ", 4096) == fz.matmul_madds_per_update("F-OQ", 4096) + fz.gather_madds("F-OQ", 4096) + 4 * fz.trainable_parameters("F-OQ", 4096)
    assert [fz.gather_madds(a, 4096) for a in ("F-OQ", "T-OQ", "H8", "R2", "D-OQ")] == [98_304, 98_304, 65_536, 8_192, 0]  # the gather-weighted sum (section 22.1; N4)
    assert fz.backbone_madds(16)["total"] == 32_901_120 + 24_643_584
    assert fz.analytic_madds_per_update("H8", 4096) > fz.backbone_madds(16)["total"]  # every arm pays the backbone: the cost never falls below it


# --- M7: the dense-rate tie rule ---------------------------------------------------------------------------------------------------------
def test_dense_rate_tie_rule_walks_the_doubling_grid_then_takes_the_smaller_rate() -> None:
    u = core.U_P
    acc = {0.001: 0.60, 0.003: 0.61, 0.01: 0.30}  # 0.001 and 0.003 are within 0.02; 0.01 is not a contender
    snaps = calibrate.tie_snapshots(u)
    assert snaps == (u // 2, u // 4, u // 8, u // 16)

    def traj(a: dict[int, float], b: dict[int, float]) -> dict[float, dict[int, float]]:
        return {0.001: a, 0.003: b}

    # decided at U_P/2: the faster learner is the higher a_use there
    got = calibrate.select_dense_rate(acc, traj({u // 2: 0.50, u // 4: 0.4, u // 8: 0.3, u // 16: 0.2}, {u // 2: 0.58, u // 4: 0.4, u // 8: 0.3, u // 16: 0.2}), u)
    assert got["rate"] == 0.003 and got["decided_by"] == f"faster learner: a_use at {u // 2}"
    # equal (within 0.02) at U_P/2 and U_P/4, decided at U_P/8
    got = calibrate.select_dense_rate(acc, traj({u // 2: 0.50, u // 4: 0.40, u // 8: 0.35, u // 16: 0.2}, {u // 2: 0.51, u // 4: 0.41, u // 8: 0.20, u // 16: 0.2}), u)
    assert got["rate"] == 0.001 and got["decided_by"] == f"faster learner: a_use at {u // 8}" and len(got["walk"]) == 3
    # no snapshot separates the rates: the smaller learning rate
    flat = {u // 2: 0.5, u // 4: 0.4, u // 8: 0.3, u // 16: 0.2}
    got = calibrate.select_dense_rate(acc, traj(flat, dict(flat)), u)
    assert got["rate"] == 0.001 and "smaller learning rate" in got["decided_by"]
    # a three-way tie: the walk keeps those within 0.02 of the best at the first separating snapshot
    three = {0.001: 0.60, 0.003: 0.61, 0.01: 0.605}
    t3 = {0.001: {u // 2: 0.30, u // 4: 0.2, u // 8: 0.1, u // 16: 0.1}, 0.003: {u // 2: 0.50, u // 4: 0.2, u // 8: 0.1, u // 16: 0.1}, 0.01: {u // 2: 0.495, u // 4: 0.3, u // 8: 0.1, u // 16: 0.1}}
    got = calibrate.select_dense_rate(three, t3, u)
    assert got["rate"] == 0.01 and got["decided_by"] == f"faster learner: a_use at {u // 4}"
    # a missing snapshot or a missing trajectory for a tie is returned to the lead, never guessed
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate(acc, traj({u // 2: 0.5}, {u // 2: 0.5}), u)
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate(acc)
    assert calibrate.select_dense_rate({0.001: 0.30, 0.003: 0.50, 0.01: 0.20})["rate"] == 0.003  # no tie: no trajectory needed


def test_dense_rate_cells_are_evaluated_on_the_doubling_snapshots() -> None:
    for cell in core.dense_rate_cells():
        snaps = calibrate.calibration_snapshots(cell)
        assert set(calibrate.tie_snapshots(cell.run_updates)) <= set(snaps) and cell.run_updates in snaps  # readout / 2, /4, /8, /16 and the readout itself


# --- (b), m12: lane L's status comes from S0's record, and a qualified interface returns to the lead -------------------------------
def test_lane_status_is_derived_from_s0_and_any_qualified_interface_returns_to_the_lead() -> None:
    assert fz.s0_status_and_lane(None) == (fz.S0_NOT_DECIDED, fz.LANE_OMITTED_NO_INTERFACE, False)
    assert fz.s0_status_and_lane({"outcome": "ADDRESSING-NOT-QUALIFIED"})[2] is False
    status, lane, returns = fz.s0_status_and_lane({"outcome": fz.LANE_QUALIFIED_BOTH, "candidate": "A5-C", "overload_qualified": True})
    assert returns is True and lane == fz.LANE_WOULD_RUN and status == f"S0 {fz.LANE_QUALIFIED_BOTH}"
    # lead's ruling P1: ANY qualified interface returns to the lead, whether or not the lane would run
    assert fz.s0_status_and_lane({"outcome": fz.LANE_QUALIFIED_BOTH, "candidate": "A1", "overload_qualified": True})[2] is True
    assert fz.s0_status_and_lane({"outcome": fz.LANE_QUALIFIED_BOTH, "candidate": "A5-C", "overload_qualified": False})[2] is True
    assert fz.s0_status_and_lane({"outcome": fz.LANE_QUALIFIED_4096})[2] is True


# --- M3: the registered driver ------------------------------------------------------------------------------------------------------------
OVERRIDES = (
    ("--stage-cap-seconds", "5"), ("--ledger-root", "/nonexistent"), ("--experiments-root", "/nonexistent"), ("--rss-worker-bytes", "1"), ("--rss-aggregate-bytes", "1"), ("--only", "x"),
    ("--repo", "/nonexistent"), ("--workers", "2"), ("--draw", "2"), ("--seed-block", "2"), ("--items", "load,row-up"), ("--finalize-items", "load,row-up"), ("--item-cap-seconds", "5"), ("--stage-start-epoch", "1"), ("--timing", "/nonexistent"), ("--calibration", "/nonexistent"),
    ("--freeze-plan", "/nonexistent"), ("--updates", "8"), ("--labels", "x"), ("--item", "x"), ("--restore-split", "4"), ("--results-dir", "/nonexistent"), ("--no-loaded-transitions", "x"),
    ("--s0-record", "/nonexistent"), ("--freeze-dir", "/nonexistent"), ("--projection", "/nonexistent"), ("--gates", "/nonexistent"), ("--synthetic", "/nonexistent"),
)  # fmt: skip


@pytest.mark.parametrize(("flag", "value"), OVERRIDES)
def test_registered_driver_refuses_every_override(flag: str, value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = stages.main(["registered", "train", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef", flag, value])
    err = capsys.readouterr().err
    assert code == 2 and "takes no override" in err and flag in err
    assert not list(tmp_path.rglob("*"))


def test_registered_driver_refusal_message_names_the_override(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["registered", "gates", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef", "--stage-cap-seconds", "999999"]) == 2
    err = capsys.readouterr().err
    assert "takes no override" in err and "--stage-cap-seconds" in err
    assert stages.main(["registered", "gates", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef", "--rss-worker-bytes", "1", "--only", "c"]) == 2
    err = capsys.readouterr().err
    assert "--rss-worker-bytes" in err and "--only" in err
    assert stages.main(["registered", "gates", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef", "--dry"]) == 2  # --dry never combines with registered


@pytest.mark.parametrize("command", ("train", "evaluate", "simulate", "analyze", "report", "gates", "timing", "calibrate", "rehearse", "freeze", "project", "synthetic"))
def test_registered_mode_is_reached_only_through_the_fixed_path(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main([command, "--mode", "registered", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef"]) == 2
    assert "only through" in capsys.readouterr().err and not list(tmp_path.rglob("*"))


def test_a_registered_worker_refuses_a_hand_made_plan_a_wrong_commit_and_a_missing_decision_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Re-check N1: a worker started by hand with a self-made plan and its digest, a commit that is not the freeze commit, or no Decision 2 is refused before it does anything."""
    base = ["work", "train", "--mode", "registered", "--run-dir", str(tmp_path / "run"), "--labels", "x"]
    assert stages.main(base) == 2  # no plan
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    assert stages.main([*base, "--freeze-plan", str(plan), "--freeze-plan-sha256", file_sha256(plan)]) == 2  # a typed plan with its own digest
    assert "not a typed plan" in capsys.readouterr().err
    repo = tmp_path / "repo"
    (repo / "studies" / "p10s1" / "freeze").mkdir(parents=True)
    real = repo / stages.FREEZE_PLAN
    real.write_text("{}")
    monkeypatch.setattr(core, "repo_root", lambda: repo)
    argv = [*base, "--freeze-plan", str(real), "--freeze-plan-sha256", file_sha256(real)]
    assert stages.main(argv) == 2 and "requires --freeze-commit" in capsys.readouterr().err  # the right file but no freeze commit
    assert stages.main([*argv, "--freeze-commit", "deadbeef"]) == 2 and "not a commit" in capsys.readouterr().err  # not a freeze commit
    assert stages.main([*argv[:-1], "0" * 64]) == 2 and "does not hash" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()
    # the guards run in order: preconditions, then verify_plan, then Decision 2
    calls: list[str] = []
    monkeypatch.setattr(stages, "check_preconditions", lambda *a, **k: calls.append("preconditions"))
    monkeypatch.setattr(stages, "load_plan", lambda r: {})
    monkeypatch.setattr(stages, "verify_plan", lambda *a, **k: calls.append("verify_plan"))
    monkeypatch.setattr(stages, "require_decision_2", lambda *a, **k: (_ for _ in ()).throw(pool.StageRefused("refused: no Decision 2")))
    assert stages.main([*argv, "--freeze-commit", "abc"]) == 2 and calls == ["preconditions", "verify_plan"] and "no Decision 2" in capsys.readouterr().err


def test_a_registered_generation_worker_refuses_a_provisional_cap_and_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Re-check N8: ``work generate --mode registered`` applies the refusals of ``generate``."""
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())  # provisional
    monkeypatch.setattr(core, "repo_root", lambda: repo)
    base = ["work", "generate", "--mode", "registered", "--run-dir", str(tmp_path / "run")]
    assert stages.main(base) == 2 and "provisional" in capsys.readouterr().err
    assert stages.main([*base, "--stage-cap-seconds", "5"]) == 2 and "takes no override" in capsys.readouterr().err
    assert stages.main([*base, "--rss-worker-bytes", "1"]) == 2 and "--rss-worker-bytes" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()


def test_no_in_process_work_command_leaks_process_state(tmp_path: Path) -> None:
    """Re-check N9: an in-process ``work`` call (which is refused here) changes no torch thread count, no deterministic flag, no default device and no RNG state."""
    import random

    import torch

    def state() -> tuple[Any, ...]:
        return (torch.get_num_threads(), torch.get_num_interop_threads(), torch.are_deterministic_algorithms_enabled(), str(torch.get_default_device()), torch.get_rng_state().tolist(), random.getstate())

    before = state()
    cell = core.make_cell("P", "F-OQ", 2048, 4096, 1, 2101, u_p=8192).label
    for argv in (["work", "calibrate-cell", "--mode", "calibration", "--labels", cell, "--run-dir", str(tmp_path)], ["work", "train", "--mode", "registered", "--run-dir", str(tmp_path), "--labels", "x"], ["work", "generate", "--mode", "registered", "--run-dir", str(tmp_path)]):
        stages.main(argv)
    assert state() == before


def test_worker_common_args_carry_the_plan_digest_and_the_freeze_commit(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    args = stages.build_parser().parse_args(["train", "--run-dir", str(tmp_path), "--freeze-plan", str(plan), "--freeze-commit", "abc123"])
    out = stages.common_args(args)
    assert "--freeze-plan-sha256" in out and out[out.index("--freeze-plan-sha256") + 1] == file_sha256(plan)
    assert out[out.index("--freeze-commit") + 1] == "abc123"


# --- m4: the generation cap is a config value the rehearsal sets; the registered generation takes no typed cap --------------------------------------
def test_registered_generation_refuses_a_provisional_cap_and_a_typed_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())
    assert core.generation_settings(repo / core.DEFAULT_CONFIG)["provisional"] is True
    monkeypatch.setattr(core, "repo_root", lambda: repo)
    argv = ["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp_path / "run"), "--i-understand-freeze-time"]
    assert stages.main(argv) == 2 and "provisional" in capsys.readouterr().err
    assert stages.main([*argv, "--stage-cap-seconds", "1800"]) == 2 and "takes no override" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()


def test_set_generation_cap_writes_the_config_from_a_measurement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    config = repo / core.DEFAULT_CONFIG
    config.write_text(core.render_config_toml())
    monkeypatch.setattr(core, "repo_root", lambda: repo)
    assert stages.main(["set-generation-cap"]) == 2  # no measurement and no explicit figure: nothing is invented
    assert core.generation_settings(config)["provisional"] is True
    rehearsal = tmp_path / "reh"
    manifest = rehearsal / "generate-p10s1-rehearsal" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    core.write_record(manifest, {**core.envelope("stage_manifest"), "tasks": [{"status": "completed", "seconds": 41.3}]})
    assert stages.main(["set-generation-cap", "--run-dir", str(rehearsal)]) == 0
    got = core.generation_settings(config)
    assert got["cap_seconds"] == 90.0 and got["provisional"] is False and got["table_facts"] == core.FACT_TABLE  # twice 41.3 s, rounded up to 10 s
    assert got["source"] == "measured" and got["measured_seconds"] == 41.3 and got["manifest_sha256"] == file_sha256(manifest)  # the record says where the figure came from (N6)
    assert stages.main(["set-generation-cap", "--generation-seconds", "600"]) == 0
    typed = core.generation_settings(config)
    assert typed["source"] == "typed" and typed["cap_seconds"] == 600.0 and typed["manifest_sha256"] == ""
    assert core.load_config(config)["resources"]["cap_hours"] == core.load_config(ROOT / core.DEFAULT_CONFIG)["resources"]["cap_hours"]
    assert stages.rehearsal_generate_seconds(rehearsal) == 41.3
    assert capsys.readouterr().out


def test_the_repository_config_is_the_canonical_rendering_with_a_provisional_generation_cap() -> None:
    assert (ROOT / core.DEFAULT_CONFIG).read_text() == core.render_config_toml(core.load_config()["resources"]["cap_hours"], core.generation_settings())
    assert core.generation_settings()["provisional"] is True  # set by `set-generation-cap` from the rehearsal; the freeze refuses while it is provisional


def test_the_projection_charges_five_generations() -> None:
    from studies.p10s1 import budget

    assert budget.Fixed(generate=100.0).total == 100.0 and budget.Fixed(1.0, 2.0, 3.0, 4.0, 5.0, 6.0).total == 21.0


# --- M4: Decision 2 outside the hashed specification ------------------------------------------------------------------------------------------
def test_decision_2_is_a_committed_file_with_the_run_line_and_the_freeze_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}

    def git(*argv: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True, check=True, env=env).stdout.strip()

    def commit(text: str, message: str) -> None:
        (folder / "DECISION_2.md").write_text(text)
        git("add", "-A")
        git("commit", "-q", "-m", message)

    git("init", "-q")
    (repo / "a.txt").write_text("x")
    git("add", "-A")
    git("commit", "-q", "-m", "freeze")
    freeze = git("rev-parse", "HEAD")
    with pytest.raises(pool.StageRefused, match="Decision 2"):
        stages.require_decision_2(repo, freeze)
    folder = repo / "results" / "p10s1-freeze-2026-11-16"
    folder.mkdir(parents=True)
    commit("Decision 2 for a different commit 0000\nDECISION: RUN\n", "decision 2")
    with pytest.raises(pool.StageRefused, match="full freeze commit"):
        stages.require_decision_2(repo, freeze)  # committed with the line, but it does not name this freeze commit
    commit(f"Decision 2. Freeze commit {freeze}\n", "no line")
    with pytest.raises(pool.StageRefused, match="DECISION: RUN"):
        stages.require_decision_2(repo, freeze)  # the commit is named but there is no DECISION: RUN line
    commit(f"Freeze commit {freeze}\nDECISION: DO NOT RUN\n", "do not run")
    with pytest.raises(pool.StageRefused):
        stages.require_decision_2(repo, freeze)
    commit(f"Freeze commit {freeze}\nDECISION: RUN and more\n", "not the exact line")
    with pytest.raises(pool.StageRefused):
        stages.require_decision_2(repo, freeze)  # the line must be exactly DECISION: RUN
    commit(f"Freeze commit {freeze}\nDECISION: DO NOT RUN\nDECISION: RUN\n", "contradictory")
    with pytest.raises(pool.StageRefused):
        stages.require_decision_2(repo, freeze)
    commit(f"Freeze commit {freeze}\nDECISION: RUN\n", "run")
    (folder / "DECISION_2.md").write_text(f"Freeze commit {freeze}\nDECISION: DO NOT RUN\n")
    assert stages.require_decision_2(repo, freeze).endswith("DECISION_2.md")  # the committed content decides, not a working-tree edit
    readme = (ROOT / "studies" / "p10s1" / "freeze" / "README.md").read_text()
    assert "DECISION_2.md" in readme and "outside the hashed" in readme and "DECISION: RUN" in readme


def test_freeze_refuses_a_provisional_generation_cap_and_a_qualified_interface(tmp_path: Path) -> None:
    from test_p10s1_stages import (  # the helpers of the freeze tests
        fake_projection,
        run_dir_with_draws,
    )

    paths = fake_projection(tmp_path)
    run_dir = run_dir_with_draws(tmp_path)
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())  # provisional
    base = ["freeze", "--run-dir", str(run_dir), "--projection", str(paths["projection"]), "--calibration", str(paths["calibration"]), "--timing", str(paths["timing"]), "--gates", str(paths["gates"]), "--repo", str(repo)]
    assert stages.main([*base, "--freeze-dir", str(tmp_path / "f1")]) == 2 and not (tmp_path / "f1").exists()  # the cap was never set by a rehearsal
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(generation={"cap_seconds": 600.0, "provisional": False, "table_facts": core.FACT_TABLE, "source": "typed"}))
    assert stages.main([*base, "--freeze-dir", str(tmp_path / "ft")]) == 2 and not (tmp_path / "ft").exists()  # a typed figure is refused (N6)
    measured = {"cap_seconds": 600.0, "provisional": False, "table_facts": core.FACT_TABLE, "source": "measured", "measured_seconds": 300.0, "manifest_sha256": "a" * 64}
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(generation=measured))
    s0 = tmp_path / "s0.json"
    for k, record in enumerate(({"outcome": fz.LANE_QUALIFIED_BOTH, "candidate": "A5-C", "overload_qualified": True}, {"outcome": fz.LANE_QUALIFIED_BOTH, "candidate": "A1", "overload_qualified": True}, {"outcome": fz.LANE_QUALIFIED_4096})):
        s0.write_text(json.dumps(record))
        assert stages.main([*base, "--freeze-dir", str(tmp_path / f"f2{k}"), "--s0-record", str(s0)]) == 2 and not (tmp_path / f"f2{k}").exists()  # any qualified interface returns to the lead (P1)
    assert stages.main([*base, "--freeze-dir", str(tmp_path / "f3")]) == 0
    plan = json.loads((tmp_path / "f3" / "plan.json").read_text())
    assert plan["generation"] == {**core.GENERATION_DEFAULT, **measured} and "identity_drift" in plan and "DECISION_2.md" in plan["decision_2"]["file_glob"]
    assert set(plan["identity_drift"]) == {"calibration", "projection", "timing", "rehearsal_gates"}


# --- m14: the section 10.2 scenarios and their never-negative rule ---------------------------------------------------------------------
def test_section_10_2_scenarios_never_give_a_negative(tmp_path: Path) -> None:
    scenarios = stages.section_10_2_scenarios()
    assert set(stages.NEVER_NEGATIVE) <= set(scenarios)
    for name, scn in scenarios.items():
        r, _ = run(tmp_path / name.replace(" ", "_").replace(",", ""), scn)
        label = r["outcome"]["capacity"]["label"]
        if name in stages.NEVER_NEGATIVE:
            assert label in (C.CAPACITY_INCONCLUSIVE, C.CAPACITY_NOT_TESTED, C.CAPACITY_POSITIVE) and label != C.CAPACITY_NEGATIVE, (name, label)
    dep = run(tmp_path / "dep", scenarios["dependence failed T-OQ, no other arm supported"])[0]["capacity"]["arms"]
    assert dep["T-OQ"]["class"] == C.DEPENDENCE_FAILED and dep["F-OQ"]["class"] != C.DEPENDENCE_FAILED
    assert stages.tiny_label_negative({"capacity": "CAPACITY-NEGATIVE (a)"}) and not stages.tiny_label_negative({"capacity": "CAPACITY-INCONCLUSIVE"})


# --- m6: stdout and results.json carry the tag ----------------------------------------------------------------------------------------------------
def test_results_json_and_printed_labels_carry_the_tag(tmp_path: Path) -> None:
    from studies.p10s1 import report

    r, d = run(tmp_path, syn.Scenario())
    core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": r}))
    report.write_report(d, d / "results")
    results = json.loads((d / "results" / "results.json").read_text())
    assert results["store_only_tag"] == core.STORE_ONLY_TAG and "tag_note" in results
    assert C.printable(C.CAPACITY_POSITIVE).endswith(f"[{core.STORE_ONLY_TAG}]")
    assert C.untagged_positive_labels("CAPACITY STEPs and CAPACITY STEPS and FASTER and REACHED ONLY BY THE LARGER") != []  # plurals and per-replicate labels are caught


# --- m2, m16: the seed block and the seed scan ------------------------------------------------------------------------------------------------------
def test_seed_block_is_the_seven_grid_cells_whatever_the_plan() -> None:
    for plan in (core.Plan(seed_block_draws=(1,)), core.Plan(seed_block_draws=(1,), sat256=False), core.Plan(seed_block_draws=(1,), row_u_p=(8192, 16384, 32768))):
        sb = [c for c in core.registered_cells(plan) if c.kind == "SB"]
        assert len(sb) == 14 and {(c.facts, c.slots) for c in sb} == set(core.GRID_CELLS) and all(c.arm == "F-OQ" for c in sb)


# --- the test-only switch -----------------------------------------------------------------------------------------------------------------------
def test_the_test_switch_changes_which_seed_sets_registered_mode_accepts(monkeypatch: pytest.MonkeyPatch) -> None:
    core.check_seed_set("registered", "p10s1-draw-1")
    with pytest.raises(ValueError):
        core.check_seed_set("registered", "p10s1-test-0")
    monkeypatch.setenv(core.TEST_SWITCH_ENV, "1")
    core.check_seed_set("registered", "p10s1-test-0")
    core.check_seed_set("registered", "p10s1-test-4")
    for bad in ("p10s1-draw-1", "p10s1-test-5", "p10s1-cal-1", "p10s1-rehearsal"):
        with pytest.raises(ValueError):
            core.check_seed_set("registered", bad)
    assert core.draw_names() == core.TEST_DRAW_NAMES and core.draw_seeds(1).name == "p10s1-test-0"
    args = stages.build_parser().parse_args(["train", "--mode", "registered", "--draw", "2"])
    assert stages.tiny(args) and stages.seeds_for(args).name == "p10s1-test-1"
    monkeypatch.delenv(core.TEST_SWITCH_ENV)
    assert core.draw_names() == core.DRAW_NAMES and not stages.tiny(args)
    assert stages.seeds_for(args).name == "p10s1-draw-2"


# --- m9: the README says registered stages run from a worktree pinned to the freeze commit ------------------------------------------------------
def test_readme_documents_the_pinned_worktree_and_the_generation_cap() -> None:
    readme = (ROOT / "studies" / "p10s1" / "freeze" / "README.md").read_text()
    assert "pinned to the freeze commit" in readme and "set-generation-cap" in readme and "--s0-record" in readme and "studies.p10s1.e2e" in readme
    assert "the ADR copy in this worktree still says 12" not in readme  # m10


# --- re-check N2: a registered freeze and driver refuse DRY records, a DRY-size plan and an open calibration -----------------------------------------
def _freeze_args(paths: dict[str, Path], run_dir: Path, out: Path, repo: Path) -> list[str]:
    return ["freeze", "--run-dir", str(run_dir), "--projection", str(paths["projection"]), "--calibration", str(paths["calibration"]), "--timing", str(paths["timing"]), "--gates", str(paths["gates"]), "--repo", str(repo), "--freeze-dir", str(out)]


def test_a_registered_freeze_refuses_dry_records_a_dry_plan_and_an_open_calibration(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from test_p10s1_stages import config_repo, fake_projection, run_dir_with_draws

    run_dir = run_dir_with_draws(tmp_path)
    repo = config_repo(tmp_path)
    cases = {
        "projection": {"dry": True},
        "calibration": {"cal_extra": {"dry": True}},
        "open calibration": {"cal_extra": {"returns_to_lead": ["the U_P check failed"]}},
        "unit": {"chosen": {"ok": True, "plan": core.Plan((1,), ("8K/16K",), False, 8).as_json(), "applied_cuts": [], "headroom": {"ok": True}}},
    }
    for name, over in cases.items():
        folder = tmp_path / name.replace(" ", "_")
        folder.mkdir()
        paths = fake_projection(folder, **over)
        assert stages.main(_freeze_args(paths, run_dir, folder / "out", repo)) == 2 and not (folder / "out").exists(), name
        err = capsys.readouterr().err
        assert {"projection": "DRY record", "calibration": "DRY record", "open calibration": "open returns", "unit": "unit"}[name] in err, (name, err)
    for rec_name, key in (("timing", "timing"), ("gates", "gates")):
        folder = tmp_path / f"dry_{rec_name}"
        folder.mkdir()
        paths = fake_projection(folder)
        core.write_record(paths[rec_name], {**core.read_record(paths[rec_name], key), "dry": True})
        # the bound hash now differs from the projection's: rebuild the projection around the DRY record
        folder2 = tmp_path / f"dry2_{rec_name}"
        folder2.mkdir()
        paths2 = fake_projection(folder2)
        rec = {**core.read_record(paths2[rec_name], key), "dry": True}
        core.write_record(paths2[rec_name], rec)
        proj = core.read_record(paths2["projection"], "projection")
        proj["timing" if rec_name == "timing" else "rehearsal_gates"]["sha256"] = file_sha256(paths2[rec_name])
        core.write_record(paths2["projection"], proj)
        assert stages.main(_freeze_args(paths2, run_dir, folder2 / "out", repo)) == 2 and "DRY record" in capsys.readouterr().err
    ok = tmp_path / "ok"
    ok.mkdir()
    assert stages.main(_freeze_args(fake_projection(ok), run_dir, ok / "out", repo)) == 0  # the same records, not DRY, at U_P, with no open return, freeze


def test_verify_plan_refuses_dry_records_and_a_dry_unit_outside_the_test_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_p10s1_stages import config_repo, fake_projection, run_dir_with_draws

    run_dir = run_dir_with_draws(tmp_path)
    paths = fake_projection(tmp_path)
    out = tmp_path / "out"
    assert stages.main(_freeze_args(paths, run_dir, out, config_repo(tmp_path))) == 0
    plan = json.loads((out / "plan.json").read_text())
    repo = tmp_path / "repo"
    (repo / "studies" / "p10s1" / "freeze").mkdir(parents=True)
    (repo / stages.CAPS_FILE).write_text((out / "stage_caps.json").read_text())
    plan["stage_caps_sha256"] = file_sha256(repo / stages.CAPS_FILE)
    # a DRY unit in the frozen plan
    dry_plan = json.loads(json.dumps(plan))
    dry_plan["frozen"]["plan"].update(unit=8, row_u_p=[8, 8, 16], u_l=[core.scaled(131072, 8), core.scaled(393216, 8)], u_l_256=core.scaled(98304, 8))
    dry_plan["frozen_sha256"] = sha256(canonical_json(dry_plan["frozen"]))
    with pytest.raises(pool.StageRefused, match="unit"):
        stages.verify_plan(dry_plan, repo, run_dir)
    # a DRY bound record
    core.write_record(paths["timing"], {**core.read_record(paths["timing"], "timing"), "dry": True})
    dry_rec = json.loads(json.dumps(plan))
    dry_rec["timing"]["sha256"] = file_sha256(paths["timing"])
    with pytest.raises(pool.StageRefused, match="DRY"):
        stages.verify_plan(dry_rec, repo, run_dir)
    monkeypatch.setenv(core.TEST_SWITCH_ENV, "1")  # under the switch the same plan passes these two guards and meets the next check instead
    with pytest.raises(pool.StageRefused) as caught:
        stages.verify_plan(dry_plan, repo, run_dir)
    assert "unit" not in str(caught.value) and "DRY" not in str(caught.value)


# --- re-check N3, N5, N7 ---------------------------------------------------------------------------------------------------------------------
def test_the_matched_updates_text_and_the_dense_matches_sentence_are_printed_beside_the_label(tmp_path: Path) -> None:
    from studies.p10s1 import report

    arms = {
        "F-OQ": {"class": C.CAPACITY_ONE_TRANSITION, "dense": "DENSE NOT ESTABLISHED AT MATCHED COMPUTE (MC-SHORT)", "dense_detail": {"mu_text": ["A1 matched updates (descriptive): d = +4.7 bits per fact, r = 27.2"]}, "work_label": None},
        "T-OQ": {"class": C.INTERMEDIATE, "dense": C.DENSE_MATCHES, "dense_detail": {}, "dense_matches_sentence": "A1: the sentence of section 8.5 | with a bar", "work_label": None},
    }
    steps = {a: {"A1": {"class": C.NO_GAIN, "verdicts": ["NULL"]}} for a in arms}
    text = "\n".join(report._capacity_table({"arms": arms, "steps": steps}))
    assert "MC-SHORT) — A1 matched updates (descriptive): d = +4.7 bits per fact, r = 27.2" in text
    assert "DENSE MATCHES — A1: the sentence of section 8.5 / with a bar" in text


def test_identity_drift_names_the_config_and_the_projection_carries_an_identity(tmp_path: Path) -> None:
    now = core.code_identity()
    changed = {**now, "config_sha256": "0" * 64}
    drift = stages.identity_drift(ROOT, {"calibration": {"identity": changed, "source_hashes": core.source_hashes()}, "projection": {"identity": now, "source_hashes": core.source_hashes()}, "timing": {}})
    assert drift["calibration"]["files_changed"] == [str(core.DEFAULT_CONFIG)] and drift["calibration"]["parts_differing"] == ["config_sha256"]
    assert drift["projection"] == {"equal": True, "parts_differing": [], "files_changed": []} and drift["timing"] == {"identity": "NOT RECORDED"}
    assert '"identity": core.code_identity(), "source_hashes": core.source_hashes()' in (ROOT / "studies" / "p10s1" / "stages.py").read_text()  # the projection record carries both
