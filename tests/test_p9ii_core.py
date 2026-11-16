# ruff: noqa: E501
"""P9II core and budgets (ADR-0019 sections 5 to 7, 9, 10): the registry, schedules in exposures per fact, seeds and their disjointness, reserve substitution,
the calibration rule, config, identity, ledgers, projections and the 2x headroom rule, and the fixed launch scripts. Self-check only: not independent review,
not Astra validation, not human approval."""

import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.config import _validate  # noqa: E402
from studies.p9ii import budget, core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- registry ---------------------------------------------------------------------------------------------------------------------
def test_registry_counts() -> None:
    assert len(core.stage1_cells()) == 128 and len(core.calibration_cells()) == 22
    sizes = {tuple(a): len(core.stage2_cells(a)) for a in ([], ["A5-C"], ["A2"], ["A5-C", "A5-D"], ["A5-C", "A2"], ["A2", "A1"])}
    assert sizes == {(): 16, ("A5-C",): 24, ("A2",): 32, ("A5-C", "A5-D"): 32, ("A5-C", "A2"): 40, ("A2", "A1"): 40}
    assert len(core.stage3_cells("A0")) == 6 and len(core.stage3_cells("A5-D")) == 8
    s1 = core.stage1_cells()
    assert sum(1 for c in s1 if c.arm in core.LEARNED_ARMS) == 112 and sum(1 for c in s1 if c.arm in core.REFERENCE_ARMS) == 16
    assert {c.draw for c in s1} == set(range(1, 9)) and {c.slots for c in s1} == {4096}
    assert {c.draw for c in core.stage2_cells([])} == {9, 10, 11, 12} and {c.draw for c in core.stage3_cells("A0")} == {13, 14}
    assert all(c.seed_index == 0 for c in core.stage3_cells("A1")) and all(c.seed_index == 0 for c in s1 if c.arm in core.REFERENCE_ARMS)
    cal = core.calibration_cells()
    assert {c.draw for c in cal} == {3, 4} and all(c.slots == 4096 and c.seed_index == 0 for c in cal)
    assert sum(1 for c in cal if c.value is not None) == 16 and {c.arm for c in cal if c.value is None} == {"A0", "A6", "A7"}


def test_stage2_configuration_rules() -> None:
    assert core.stage2_arms(["A5-C", "A2"]) == ["A0", "A5-C", "A2", "A1-S"]  # A1-S runs with a supervised arm
    assert "A1-S" not in core.stage2_arms(["A5-C", "A4"])
    for bad in (["A0"], ["A1-S"], ["A5-C", "A5-C"], ["A5-C", "A5-D", "A4"]):
        with pytest.raises(ValueError):
            core.stage2_arms(bad)
    for bad_arm in ("A2", "A4", "A1-S", "A6", "A7"):
        with pytest.raises(ValueError):
            core.stage3_cells(bad_arm)


def test_labels_round_trip_and_test_labels() -> None:
    for c in [*core.stage1_cells(), *core.calibration_cells(), *core.stage2_cells(["A2", "A1"]), *core.stage3_cells("A1")]:
        assert core.parse_label(c.label) == c
    t = core.make_cell("A5-C", 16384, stage=2, draw=3, j=1)
    assert t.label.startswith("TEST-") and core.parse_label(t.label) == t
    cal = core.make_cell("A1", 4096, 0, 3, 0, 0.1)
    assert core.parse_label(cal.label) == cal
    for bad in ("nonsense", "S1-A9-n4096-d01-j0", "TEST-S1-A0-n1-d01-j0"):
        with pytest.raises(ValueError):
            core.parse_label(bad)


# --- schedules in exposures per fact ----------------------------------------------------------------------------------------------
def test_exposures_per_fact_at_each_size() -> None:
    f = core.FACTS_PROPORTIONAL
    assert core.exposures_per_fact(core.stage_updates(1), f[4096]) == 512
    assert core.exposures_per_fact(core.UPDATES, f[16384]) == 128 and core.exposures_per_fact(core.stage_updates(2), f[16384]) == 512  # U and 4U
    assert core.exposures_per_fact(core.stage_updates(3), f[65536]) == 32
    assert core.stage_readouts(2) == (8192, 32768) and core.stage_readouts(1) == core.stage_readouts(3) == (8192,) and core.decisive_readout(2) == 32768


def test_schedules_scale_with_exposures_and_are_undefined_at_stage_three() -> None:
    h = core.Hyper(u_pre=1024.0, k0_fraction=0.125)
    assert core.schedule_for("A2", 1, h, 4096) == core.Schedule(8192, 1024, None, None)
    assert core.schedule_for("A2", 2, h, 16384).u_pre == 4096  # U_pre x 4 in exposures per fact
    assert core.schedule_for("A4", 1, h, 4096) == core.Schedule(8192, None, 4096, 512)  # T_A = U/2, k_0 = N/8
    s2 = core.schedule_for("A4", 2, core.Hyper(k0_fraction=1.0), 16384)
    assert s2.t_anneal == 16384 and s2.k0 == 16384  # T_A = 2U at Stage 2
    assert core.schedule_for("A2", 1, h, 4096, updates=8).u_pre == 1  # DRY: U_pre scales with U / 8192
    for arm in ("A2", "A4"):
        with pytest.raises(ValueError):
            core.schedule_for(arm, 3, h, 65536)
    assert core.schedule_for("A0", 3, h, 65536).total == 8192


def test_k_schedule_formula() -> None:
    k0, ta = 512, 4096
    assert core.k_schedule(0, k0, ta) == 512 and core.k_schedule(ta, k0, ta) == 8 and core.k_schedule(ta + 100, k0, ta) == 8
    assert core.k_schedule(ta // 2, k0, ta) == round(512 * (8 / 512) ** 0.5) == 64
    ks = [core.k_schedule(t, k0, ta) for t in range(0, ta + 1, 128)]
    assert ks == sorted(ks, reverse=True) and min(ks) == 8
    with pytest.raises(ValueError):
        core.k_schedule(-1, k0, ta)


# --- seeds ---------------------------------------------------------------------------------------------------------------------------
def test_seed_layout_and_namespaces_are_disjoint() -> None:
    core.assert_namespaces_disjoint()
    s = core.registered_draw_seeds(1)
    assert s.facts == 190001 and s.null_seeds_a == (190015, 190016, 190017) and s.null_seeds_b == (190018, 190019, 190020)  # base + 14..16, base + 17..19
    assert [core.registered_draw_seeds(k).facts for k in (2, 14)] == [190101, 191301]
    assert [core.reserve_seeds(r).facts for r in (1, 2)] == [191401, 191501]
    assert core.calibration_seeds(3).facts == 179301 and core.calibration_seeds(4).facts == 179401 and core.rehearsal_seeds().facts == 179501
    assert core.test_seeds(0).facts == 910001
    assert core.target_seed(s, 1) == 190042 and core.stream_seed(s, 0) == 190061
    ns = core.seed_namespaces()
    reg = ns["registered"] | ns["reserve"]
    for other in ("p9_registered", "p9i_registered", "p9_rehearsal_other", "test", "calibration_data_3", "calibration_data_4", "rehearsal_data_5"):
        assert not reg & ns[other], other
    assert not any(200001 <= v <= 229999 or 920001 <= v <= 929999 or 900001 <= v <= 919999 for v in reg | ns["calibration_data_3"] | ns["calibration_data_4"] | ns["rehearsal_data_5"])
    assert all(910001 <= v <= 919999 for v in ns["test"]) and {1901, 1902, 1891, 1892} <= ns["init"] | ns["calibration_init"]
    for v in (1701, 1702, 1801, 1802, 1791, 1792, 170001, 182001):
        assert all(v not in ns[n] for n in ("registered", "reserve", "init", "calibration_init", "test"))


def test_disjointness_check_detects_overlaps_and_reserved_ranges() -> None:
    ns = core.seed_namespaces()
    with pytest.raises(ValueError, match="overlap"):
        core.assert_namespaces_disjoint({**ns, "p9i_registered": ns["p9i_registered"] | {190001}})
    with pytest.raises(ValueError, match="overlap"):
        core.assert_namespaces_disjoint({**ns, "rehearsal_data_5": ns["rehearsal_data_5"] | {179301}})
    with pytest.raises(ValueError, match="reserved range"):
        core.assert_namespaces_disjoint({**ns, "registered": ns["registered"] | {215000}})
    with pytest.raises(ValueError, match="reserved range"):
        core.assert_namespaces_disjoint({**ns, "reserve": ns["reserve"] | {925000}})
    with pytest.raises(ValueError, match="reserved range"):
        core.assert_namespaces_disjoint({**ns, "calibration_init": ns["calibration_init"] | {900500}})  # P9-I's test namespace
    with pytest.raises(ValueError):
        core.test_seeds(100)


def test_check_seed_set_per_mode() -> None:
    ok = [("registered", "p9ii-draw-3"), ("registered", "p9ii-reserve-2"), ("calibration", "rehearsal-3"), ("calibration", "rehearsal-4"), ("rehearsal", "rehearsal-5"), ("calibration", "p9ii-test-0"), ("rehearsal", "p9ii-test-1")]
    for mode, name in ok:
        core.check_seed_set(mode, name)
    bad = [("registered", "rehearsal-5"), ("registered", "p9i-registered"), ("registered", "p9ii-test-0"), ("calibration", "rehearsal-5"), ("calibration", "rehearsal-2"), ("calibration", "p9ii-draw-1"), ("rehearsal", "rehearsal-3"), ("rehearsal", "rehearsal-4"), ("rehearsal", "p9ii-draw-1"), ("rehearsal", "p9ii-reserve-1")]
    for mode, name in bad:
        with pytest.raises(ValueError):
            core.check_seed_set(mode, name)
    with pytest.raises(ValueError):
        core.check_seed_set("bogus", "p9ii-draw-1")
    with pytest.raises(ValueError):
        core.calibration_seeds(5)


# --- reserve substitution (9) -----------------------------------------------------------------------------------------------------------------
def test_plan_draws_substitution() -> None:
    allok = {n: True for n in (*core.DRAW_NAMES, *core.RESERVE_NAMES)}
    plan = core.plan_draws(allok)
    assert plan.ok and plan.replacements == {} and plan.seed_set_of[5] == "p9ii-draw-5"
    one = core.plan_draws({**allok, "p9ii-draw-5": False})
    assert one.ok and one.replacements == {5: "p9ii-reserve-1"} and one.seed_set_of[5] == "p9ii-reserve-1" and one.seed_set_of[6] == "p9ii-draw-6"  # takes the failed draw's place and stage
    two = core.plan_draws({**allok, "p9ii-draw-14": False, "p9ii-draw-2": False})
    assert two.replacements == {2: "p9ii-reserve-1", 14: "p9ii-reserve-2"}  # the next unused reserve, in the fixed order
    for bad in ({**allok, "p9ii-draw-1": False, "p9ii-draw-2": False, "p9ii-draw-3": False}, {**allok, "p9ii-draw-1": False, "p9ii-reserve-1": False}, {**allok, "p9ii-draw-1": False, "p9ii-draw-2": False, "p9ii-reserve-2": False}):
        p = core.plan_draws(bad)
        assert not p.ok and p.reason
    assert core.plan_draws({**allok, "p9ii-reserve-1": False}).ok  # a failed reserve that is not needed is harmless
    assert not core.plan_draws({n: True for n in core.DRAW_NAMES[:-1]}).ok  # a draw with no G1 result counts as failed and no reserve has one
    assert core.seeds_of_name("p9ii-reserve-2").facts == 191501 and core.seeds_of_name("p9ii-draw-14").facts == 191301
    with pytest.raises(ValueError):
        core.seeds_of_name("rehearsal-5")


# --- the calibration rule (6) -------------------------------------------------------------------------------------------------------------------
def test_select_value_rules_including_ties() -> None:
    v = (0.1, 1.0)
    assert core.select_value(v, {0.1: 0.5, 1.0: 0.9}, {0.1: 1.0, 1.0: 5.0}) == 1.0  # the higher minimum accuracy wins
    assert core.select_value(v, {0.1: 0.9, 1.0: 0.5}, {0.1: 5.0, 1.0: 1.0}) == 0.1
    assert core.select_value(v, {0.1: 0.50, 1.0: 0.519}, {0.1: 100.0, 1.0: 900.0}) == 0.1  # a difference below 0.02 goes to the secondary criterion
    assert core.select_value(v, {0.1: 0.50, 1.0: 0.52}, {0.1: 100.0, 1.0: 900.0}) == 1.0  # a difference of 0.02 does not
    assert core.select_value(v, {0.1: 0.9, 1.0: 0.9}, {0.1: 900.0, 1.0: 100.0}) == 1.0  # tie: the earlier median time to first success
    assert core.select_value(v, {0.1: 0.0, 1.0: 0.0}, {0.1: math.inf, 1.0: 300.0}) == 1.0  # a cell that never succeeds counts as later
    assert core.select_value(v, {0.1: 0.0, 1.0: 0.0}, {0.1: math.inf, 1.0: math.inf}) == 0.1  # also tied: the first value listed
    assert core.select_value(v, {0.1: 0.7, 1.0: 0.7}, {0.1: 64.0, 1.0: 64.0}) == 0.1
    assert core.median([1.0, math.inf]) == math.inf and core.median([2.0, 4.0]) == 3.0 and math.isnan(core.median([]))


# --- config, identity, records --------------------------------------------------------------------------------------------------------------------
def test_config_is_the_rendered_constants_and_validation_rejects_changes() -> None:
    assert (ROOT / core.DEFAULT_CONFIG).read_text() == core.render_config_toml()
    data = core.load_config()
    data["thresholds"]["paired_threshold"] = 3
    with pytest.raises(ValueError):
        core.validate_config(data)
    extra = core.load_config()
    extra["training"]["learning_rate"] = 0.01
    with pytest.raises(ValueError):
        _validate(extra, core.registered_config(), "x")
    cfg = core.registered_config()
    assert cfg["training"]["updates"] == 8192 and cfg["resources"]["budget_a_hours"] == 4.0 and cfg["resources"]["budget_b_hours"] == 3.0 and cfg["grid"]["A4"]["values"] == [0.125, 1.0]


def test_every_imported_study_module_is_hashed() -> None:
    hashed = core.source_hashes()
    pattern = re.compile(r"^\s*(?:from studies\.(p9i?)(?:\.(\w+))? import ([\w, ]+)|import studies\.(p9i?)\.(\w+))", re.M)
    for path in (ROOT / "studies" / "p9ii").glob("*.py"):
        for m in pattern.finditer(path.read_text()):
            study = m[1] or m[4]
            modules = [m[2]] if m[2] else [x.strip() for x in (m[3] or m[5]).split(",")]
            for name in modules:
                if name in ("core", "data", "evaluate", "model", "train", "stages", "classes", "report", "controls", "objective", "pool", "pilot_model") or (ROOT / "studies" / study / f"{name}.py").exists():
                    assert f"studies/{study}/{name}.py" in hashed, f"{path.name} imports studies.{study}.{name}, which is not hashed"
    assert "studies/p9ii/launch/stage1.sh" in hashed and "studies/p9ii/core.py" in hashed
    assert len(core.source_digest()) == 64 and set(core.code_identity()) == {"source_sha256", "spec_sha256", "config_sha256", "frozen_source_sha256"}


def test_environment_record_has_what_the_consolidation_review_asked_for() -> None:
    env = core.environment()
    for key in ("platform", "system", "machine", "processor", "python", "torch", "threads", "cpu_count"):
        assert key in env
    assert {"torch_num_threads", "torch_interop_threads", "deterministic_algorithms", "env"} <= set(env["threads"])


def test_run_names_records_and_non_finite_markers(tmp_path: Path) -> None:
    name = core.run_name("calibrate")
    assert name.startswith("P9IIC-") and core.parse_run_name(name)[0] == "calibrate"
    assert core.run_name("dry", unique="x").startswith("P9IID-")
    for bad in ("P9IC-20260101T000000Z-x", "P9IIZ-20260101T000000Z-x", "nonsense"):
        with pytest.raises(ValueError):
            core.parse_run_name(bad)
    with pytest.raises(ValueError):
        core.run_name("nope")
    core.write_record(tmp_path / "a.json", {**core.envelope("projection"), "x": 1})
    assert core.read_record(tmp_path / "a.json", "projection")["x"] == 1
    with pytest.raises(ValueError):
        core.read_record(tmp_path / "a.json", "train")
    with pytest.raises(ValueError):
        core.write_record(tmp_path / "b.json", {"study": "P9I", "schema": 1, "kind": "train"})
    assert core.jsonable({"a": math.inf, "b": [math.nan, 1.0], "c": -math.inf}) == {"a": "+inf", "b": ["nan", 1.0], "c": "-inf"} and core.number("+inf") == math.inf


# --- ledgers (10) ------------------------------------------------------------------------------------------------------------------------------------
def test_two_budgets_are_independent_and_refuse(tmp_path: Path) -> None:
    a, b = core.ledger_for_stage("stage1", tmp_path), core.ledger_for_stage("stage2", tmp_path)
    assert a.budget == "A" and b.budget == "B" and a.cap_seconds == 4 * 3600 and b.cap_seconds == 3 * 3600
    assert core.ledger_for_stage("calibrate", tmp_path).path == a.path and core.ledger_for_stage("stage3", tmp_path).path == b.path
    a.charge("calibrate", "r", 100.0)
    assert a.charged() == 100.0 and b.charged() == 0.0 and b.remaining() == 3 * 3600  # Budget A's unused time does not move to Budget B
    a.require_room("x", a.remaining())
    with pytest.raises(core.LedgerRefused):
        a.require_room("x", a.remaining() + 1)
    with pytest.raises(core.LedgerRefused):
        a.require_room("x", 0)
    b.charge("stage2", "r", 3 * 3600 - 10)
    with pytest.raises(core.LedgerRefused):
        b.require_room("stage3", 11.0)
    assert len(a.entries()) == 1
    with pytest.raises(ValueError):
        core.Ledger(tmp_path / "x.json", "C")
    with pytest.raises(ValueError):
        core.Ledger(a.path, "B").entries()  # a ledger file belongs to its budget


# --- projections and the headroom rule (10) ----------------------------------------------------------------------------------------------------------
def rates(per_update: float = 0.01, evaluation: float = 2.0, rss: int = 600 * 2**20) -> budget.Rates:
    return {i: budget.Rate(per_update, rss, rss, evaluation) for i in budget.rehearsal_items()}


def test_rehearsal_matrix_is_every_distinct_arm_size_phase() -> None:
    items = budget.rehearsal_items()
    assert len(items) == len(set(items)) == 30
    assert {(a, 65536) for a in budget.NEVER_AT_65536} & {(i[0], i[1]) for i in items} == set()  # A2, A4, A1-S are not rehearsed where they never run
    assert {i[2] for i in items if i[0] == "A2"} == {"pre", "post"} and {i[2] for i in items if i[0] == "A4"} == {"k0", "mid", "k8"}
    assert budget.missing_items(rates()) == [] and len(budget.missing_items({})) == 30
    partial = rates()
    partial.pop(("A4", 4096, "mid"))
    assert budget.missing_items(partial) == [("A4", 4096, "mid")]


def test_projection_arithmetic_rounds_of_six_and_phase_rates() -> None:
    assert budget.makespan([10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 1, 1]) == 10 + 4 + 1  # rounds of six, longest first
    r = rates()
    h = core.Hyper(u_pre=1024.0, k0_fraction=1.0)
    assert budget.cell_training_seconds("A0", 4096, 1, r, h) == pytest.approx(8192 * 0.01)
    r[("A2", 4096, "pre")] = budget.Rate(0.02, 0, 0, 1.0)
    assert budget.cell_training_seconds("A2", 4096, 1, r, h) == pytest.approx(1024 * 0.02 + 7168 * 0.01)
    r[("A4", 4096, "k0")], r[("A4", 4096, "mid")], r[("A4", 4096, "k8")] = budget.Rate(0.05, 0, 0, 1.0), budget.Rate(0.03, 0, 0, 1.0), budget.Rate(0.01, 0, 0, 1.0)
    assert budget.cell_training_seconds("A4", 4096, 1, r, h) == pytest.approx(4096 * 0.05 + 4096 * 0.01)  # the annealing phase at its most expensive measured rate
    assert budget.cell_evaluation_seconds("A0", 16384, 2, r) == 2 * 2.0  # two readouts at Stage 2
    p = budget.stage_projection(core.stage1_cells(), 1, rates(), h)
    assert p.cells == 128 and p.rounds == 22 and p.total_seconds == pytest.approx(p.training_seconds + p.evaluation_seconds)  # the registry's 22 rounds
    with pytest.raises(ValueError):
        budget.cell_training_seconds("A2", 65536, 3, r, h)


def test_stage2_table_has_every_configuration() -> None:
    table = budget.stage2_projection_table(rates(), core.Hyper())
    assert len(table) == 16 and table["A0-only"]["cells"] == 16 and max(v["cells"] for v in table.values()) == 40 and table["A5-C+A5-D"]["cells"] == 32
    assert {budget.config_key(c) for c in budget.stage2_configurations()} == set(table)
    assert table["A2+A1"]["total_seconds"] > table["A0-only"]["total_seconds"]
    t3 = budget.stage3_projection_table(rates(), core.Hyper())
    assert set(t3) == {"A0", "A1", "A5-C", "A5-D"} and t3["A0"]["cells"] == 6 and t3["A1"]["cells"] == 8


def test_budget_decision_two_times_headroom_and_not_run_status() -> None:
    d = budget.budget_decision(100.0, 200.0)
    assert d.run and d.status is None and d.required_seconds == 200.0 and d.stage_cap_seconds == 200.0  # equal is within
    d = budget.budget_decision(100.0, 199.9)
    assert not d.run and d.status == "NOT RUN — BUDGET"
    assert not budget.budget_decision(math.nan, 1e9).run and not budget.budget_decision(math.inf, 1e9).run
    table = {"A0-only": {"total_seconds": 2000.0}, "A2+A1": {"total_seconds": 6000.0}}
    assert budget.stage2_decision([], table, 4000.0).run and not budget.stage2_decision(["A2", "A1"], table, 11999.0).run
    assert budget.stage2_decision(["A2", "A1"], table, 12000.0).run
    # the ADR's own arithmetic: twice the largest Stage 2 (1.24 h + 0.04 h) against 3 h
    assert budget.budget_decision(1.28 * 3600, 3 * 3600).run and not budget.budget_decision(1.6 * 3600, 3 * 3600).run
    assert budget.stage3_decision("A0", {"A0": {"total_seconds": 600.0}}, 1199.0).status == "NOT RUN — BUDGET"


def test_memory_headroom_rule() -> None:
    assert budget.memory_headroom(rates(rss=1 * 2**30))["ok"]  # 2 x 1 GiB within 3 GiB, 6 x 2 within 24
    assert not budget.memory_headroom(rates(rss=int(1.6 * 2**30)))["per_worker_ok"]
    assert budget.memory_headroom({})["peak_rss_bytes"] == 0


def test_stage1_budget_reads_the_remainder() -> None:
    p, d = budget.stage1_budget(rates(), core.Hyper(), 4 * 3600.0)
    assert d.run and d.required_seconds == 2 * p.total_seconds
    _, d2 = budget.stage1_budget(rates(), core.Hyper(), p.total_seconds)
    assert not d2.run and d2.status == budget.NOT_RUN_BUDGET


# --- the fixed launch scripts (9) -----------------------------------------------------------------------------------------------------------------------
LAUNCH = ("gates", "stage1", "stage1_gate", "stage2", "stage3_gate", "stage3", "analysis", "report")


def test_launch_scripts_exist_and_call_the_driver_with_the_frozen_caps() -> None:
    for name in LAUNCH:
        path = ROOT / core.LAUNCH_DIR / f"{name}.sh"
        text = path.read_text()
        assert text.startswith("#!/bin/sh\n") and "set -eu" in text and 'if [ "$#" -ne 2 ]' in text  # POSIX sh, exactly two arguments
        assert "studies.p9ii.stages registered " + name in text
        assert "--caps studies/p9ii/freeze/stage_caps.json" in text and '--run-dir "$RUN_DIR"' in text and '--freeze-commit "$FREEZE_COMMIT"' in text
        assert re.findall(r"\$[A-Za-z0-9_@*#]+", text.split("exec ", 1)[1]) == ["$RUN_DIR", "$FREEZE_COMMIT"]  # nothing else expands on the command line
        assert "$@" not in text and "$*" not in text and "bash" not in text.splitlines()[0]
        assert subprocess.run(["sh", "-n", str(path)], check=False).returncode == 0
        refused = subprocess.run(["sh", str(path), "only-one"], capture_output=True, check=False)
        assert refused.returncode == 2 and b"usage" in refused.stderr
    assert {p.stem for p in (ROOT / core.LAUNCH_DIR).glob("*.sh")} == {*LAUNCH, "generate"}  # one per registered stage, plus the fixed generation script, no others
