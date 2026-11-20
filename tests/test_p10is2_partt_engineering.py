# ruff: noqa: E501
"""Part T engineering fixes after the first audit (docs/reviews/p10-i-s2-partt-audit-2026-11-20): B3 (merge at the end of the producing stages, the recomputation a stage, stage order), B4 (one projection function,
units from the plan, no zero caps, the charge before the freeze), R1 and R2 (one checked door to Part Q), R7, R8, R10, R11, R15. Each test fails on the behaviour the audit found. Self-check only."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2 import (  # noqa: E402
    partt_caps,
    partt_door,
    partt_plan,
    partt_real,
    partt_recompute,
    partt_stages,
    partt_tasks,
)
from studies.p10is2.common import core, procs  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config("T")
CALIB = {"U": 2000, "converged": True, "store_rate": 0.003, "lora_rate": 0.0003, "etable_rate": 0.003, "read_layer": 4, "pilot": {"passed": True}, "records": {}}


# --- R10 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_a_worker_whose_preconditions_fail_pauses_with_75_never_an_item_error(tmp_path: Path) -> None:
    rc = partt_stages.main(["task", "--stage", "train", "--task-id", "train|M1|AB|r0", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"])
    assert rc == partt_stages.EXIT_IDENTITY  # any precondition refusal (a dirty tree, a missing freeze, Decision 2) is a pause; it used to exit 2 and become a failed task
    assert not (tmp_path / "r" / "item_errors").exists()


# --- R15 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_a_run_directory_holds_one_mode_and_a_rehearsal_never_writes_the_plans_directory(tmp_path: Path) -> None:
    d = tmp_path / "rehearsal"
    partt_stages.claim_run_dir(d, "rehearsal")
    partt_stages.claim_run_dir(d, "rehearsal")  # idempotent
    for other in ("registered", "calibration"):
        with pytest.raises(core.StageRefused, match="one mode only"):
            partt_stages.claim_run_dir(d, other)
    reg = tmp_path / "registered"
    with pytest.raises(core.StageRefused, match="never writes there"):
        partt_stages.claim_run_dir(reg, "rehearsal", str(reg))
    with pytest.raises(core.StageRefused, match="never writes there"):
        partt_stages.claim_run_dir(reg, "calibration", str(reg))
    partt_stages.claim_run_dir(reg, "registered", str(reg))  # the registered run may use it
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / "x.json").write_text("{}")
    with pytest.raises(core.StageRefused, match="no run_mode.json"):
        partt_stages.claim_run_dir(stray, "registered")


# --- R11 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_process_rule_counts_its_own_launcher_as_family_on_the_real_process_tree(tmp_path: Path) -> None:
    script = tmp_path / "probe.py"
    script.write_text(f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\nfrom studies.p10is2.common import procs\nprint(json.dumps(procs.own_study_alive()))\n")
    # a launcher shell whose command line looks like a study process (as `uv run python -m studies.p10is2...` or a keep-awake watcher's does), starting the stage's python
    out = subprocess.run(["sh", "-c", f"{sys.executable} {script} studies.p10is2.partt_stages_launcher_marker; true"], capture_output=True, text=True, timeout=120, check=True).stdout  # noqa: S603, S607
    alive = json.loads(out.strip().splitlines()[-1])
    assert not [c for c in alive if "partt_stages_launcher_marker" in c]  # the launcher (parent) and the stage's own command line are excluded
    assert procs.ancestor_pids() and os.getppid() in procs.ancestor_pids()


# --- R8 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_every_recomputation_attempt_is_kept_and_a_failed_one_stands(tmp_path: Path) -> None:
    first = partt_recompute.write(tmp_path, {"ok": False, "differences": [{"key": "k"}]})
    second = partt_recompute.write(tmp_path, {"ok": True, "differences": []})
    assert first != second and first.is_file() and second.is_file() and len(partt_recompute.attempts(tmp_path)) == 2  # nothing overwritten
    with pytest.raises(core.StageRefused, match="ENGINEERING STOP — RECOMPUTATION"):
        partt_real.require_recomputation(tmp_path)  # a later pass does not erase the failure
    write_json(tmp_path / "recomputation_lead_record.json", {"cause": "recorded by the lead"})
    assert partt_real.require_recomputation(tmp_path)["ok"]


# --- B3 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_recomputation_is_a_registered_stage_before_the_analysis_and_the_order_is_enforced(tmp_path: Path) -> None:
    assert partt_plan.STAGES.index("recompute") == partt_plan.STAGES.index("analysis") - 1
    items = partt_plan.stage_items(CALIB)
    assert items["recompute"] and "recompute" not in partt_tasks.TASK_STAGES and "controls" not in partt_tasks.TASK_STAGES
    with pytest.raises(core.StageRefused, match="needs 'combined'"):
        partt_tasks.require_predecessor(tmp_path, "recompute", partt_plan.STAGES)
    for s in partt_plan.STAGES[:5]:
        partt_tasks.mark_complete(tmp_path, s)
    partt_tasks.require_predecessor(tmp_path, "recompute", partt_plan.STAGES)
    with pytest.raises(core.StageRefused, match="needs 'recompute'"):
        partt_tasks.require_predecessor(tmp_path, "analysis", partt_plan.STAGES)  # the analysis cannot start before the recomputation completed


def test_results_are_merged_at_the_end_of_the_producing_stage_once(tmp_path: Path) -> None:
    d = tmp_path / "tasks" / "evaluate"
    d.mkdir(parents=True)
    core.write_record(d / "evaluate__r0.result.json", {**core.envelope("cell_record", "T"), "records": {"M1|AB|0": {"s:E_A": 0.5}}, "side": {"r0/x": {"a": 1}}})
    assert partt_real.merge_evaluate(tmp_path) == {"records": 1}
    assert json.loads((tmp_path / "registry.json").read_text()) == {"M1|AB|0|s:E_A": 0.5}  # the recomputation can read it now
    assert partt_real.merge_evaluate(tmp_path) == {"records": 1}  # idempotent
    core.write_record(d / "evaluate__r1.result.json", {**core.envelope("cell_record", "T"), "records": {"M1|AB|1": {"s:E_A": 0.6}}, "side": {}})
    with pytest.raises(core.StageRefused, match="no record is overwritten"):
        partt_real.merge_evaluate(tmp_path)
    (tmp_path / "tasks" / "combined").mkdir()
    assert partt_real.merge_combined(tmp_path) == {"combined": 0} and (tmp_path / "combined.json").is_file()


# --- B4 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_units_of_the_caps_are_counted_from_the_plan_and_match_the_audits_count() -> None:
    basis = partt_caps.basis_of(CFG)
    per = partt_caps.replicate_units(basis["eval_panel"], basis["control_subsample"], basis["d_con_panel"])
    assert per["score:plain"] == 44_000 and per["score:route"] == 4_000 and per["score:control"] == 18_000 and per["score:dcon"] == 2_400 and per["score:icl"] == 4_000
    assert sum(v for k, v in per.items() if k.startswith("score:")) == 72_400
    items = partt_plan.stage_items(CALIB)
    units = partt_caps.task_units(items, basis)
    assert sum(sum(t["units"].get(k, 0) for k in ("score:plain", "score:route", "score:control", "score:dcon", "score:icl", "score:reference")) for t in units["evaluate"]) == 3 * 72_400 + 2_000  # about 219,000 greedy items per pass
    train_units = {k: sum(t["units"].get(k, 0) for t in units["train"]) for k in partt_caps.required_kinds(items, basis) if k.startswith("train:")}
    assert set(train_units) == {f"train:{a}" for a in partt_caps.TRAINED_TYPES}  # ALL ten trained types are kinds the measuring rehearsal must time
    assert len(units["train"]) == 54 and len(units["gates"]) == 1 and len(units["recompute"]) == 1


def test_projected_seconds_are_the_sum_of_units_times_rates_plus_tasks_times_the_process_overhead() -> None:
    basis = partt_caps.basis_of(CFG)
    items = partt_plan.stage_items(CALIB)
    kinds = partt_caps.required_kinds(items, basis)
    rates = {k: 0.01 for k in kinds}
    overhead = {s: 30.0 for s in partt_plan.STAGES}
    proj = partt_caps.project_stage_seconds(items, basis, rates, overhead)
    units = partt_caps.task_units(items, basis)
    assert proj["train"] == pytest.approx(sum(t["units"][k] for t in units["train"] for k in t["units"]) * 0.01 + 54 * 30.0)  # 54 task processes pay the overhead each
    assert proj["analysis"] == pytest.approx(0.01 + 30.0) and proj["gates"] == pytest.approx(0.01 + 30.0)
    with pytest.raises(core.StageRefused, match="no measured rate for kind"):
        partt_caps.project_stage_seconds(items, basis, {k: v for k, v in rates.items() if k != "train:M-ii"}, overhead)  # nothing is guessed
    with pytest.raises(core.StageRefused, match="no measured per-process overhead"):
        partt_caps.project_stage_seconds(items, basis, rates, {s: 1.0 for s in partt_plan.STAGES if s != "recompute"})


def test_the_caps_come_from_a_record_with_the_formula_and_a_zero_cap_is_refused() -> None:
    basis = partt_caps.basis_of(CFG)
    items = partt_plan.stage_items(CALIB)
    rec = {"caps_formula": partt_caps.CAPS_FORMULA, "rates_seconds_per_unit": {k: 0.01 for k in partt_caps.required_kinds(items, basis)}, "overhead_seconds": {s: 10.0 for s in partt_plan.STAGES}}
    caps = partt_caps.proposal_from_record(rec, items, basis, 3600.0)
    assert set(caps) == {f"{s}_hours" for s in (*partt_plan.STAGES, "total")} and all(v > 0 for v in caps.values())
    assert caps["total_hours"] >= 1.0 + 2 * sum(caps[f"{s}_hours"] / 2 for s in partt_plan.STAGES) - 0.1  # the charge before the freeze plus twice every stage
    with pytest.raises(core.StageRefused, match="caps_formula"):
        partt_caps.proposal_from_record({k: v for k, v in rec.items() if k != "caps_formula"}, items, basis, 0.0)
    assert partt_caps.zero_caps(CFG, partt_plan.STAGES) and "recompute" in partt_caps.zero_caps(CFG, partt_plan.STAGES)  # the unset config: every stage, the recomputation included, has no cap yet


def make_plan(cap_hours: dict[str, float], charge: float) -> planmod.Plan:
    caps = {f"{s}_hours": h for s, h in cap_hours.items()}
    return planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "stage_caps": caps, "charge_before_freeze": {"seconds": charge, "ledgers": {}}}, "T")


def test_the_cap_check_refuses_a_zero_cap_and_counts_the_charge_before_the_freeze(tmp_path: Path) -> None:
    led = core.Ledger(tmp_path / "charged_ledger.json", "T", 1e12)
    with pytest.raises(core.StageRefused, match="a cap of 0 is not 'uncapped'"):
        partt_tasks.stage_cap_for(make_plan({"train": 0.0, "total": 10.0}, 0.0), "train", led)
    plan = make_plan({"train": 5.0, "total": 10.0}, 4 * 3600.0)  # total 36,000 s, 14,400 s charged before the freeze
    assert partt_tasks.stage_cap_for(plan, "train", led) == pytest.approx(5 * 3600.0)
    led.charge_process("evaluate", "x", "w", 20_000.0)
    assert partt_tasks.stage_cap_for(plan, "train", led) == pytest.approx(36_000 - 14_400 - 20_000)  # what is left of the total once the pre-freeze charge and this run's charge are counted


# --- R1, R2 ------------------------------------------------------------------------------------------------------------------------------------------
def fake_part_q(tmp: Path) -> tuple[Path, dict]:  # type: ignore[type-arg]
    q = tmp / "partq"
    (q / "outputs/bundle").mkdir(parents=True)
    (q / "outputs/bundle/accepted.json").write_text('{"A": []}')
    (q / "outputs/gloss_bank.json").write_text("{}")
    (q / "generation").mkdir()
    (q / "generation/result.json").write_text('{"draws_label": "DISJOINT DRAWS"}')
    manifest = {"files": {"outputs/bundle/accepted.json": file_sha256(q / "outputs/bundle/accepted.json"), "outputs/gloss_bank.json": file_sha256(q / "outputs/gloss_bank.json")}}
    write_json(q / "manifest.json", manifest)
    qplan = tmp / "partq_plan.json"
    write_json(qplan, {"inputs": {"reuse": {"files": {"generation/result.json": file_sha256(q / "generation/result.json")}}}})
    return q, partt_stages.part_q_block(q, qplan)


def test_part_q_is_read_through_one_checked_door(tmp_path: Path) -> None:
    q, block = fake_part_q(tmp_path)
    door = partt_door.PartQDoor.from_plan(block)
    assert door.read_json("generation/result.json")["draws_label"] == "DISJOINT DRAWS"  # a file of a reused stage: by the reuse hashes
    assert door.verify_prefix("outputs/bundle") == 1
    (q / "outputs/gloss_bank.json").write_text('{"x": 1}')
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        door.verify("outputs/gloss_bank.json")
    with pytest.raises(core.StageRefused, match="not listed"):
        door.verify("generation/pools.json")  # not in the manifest or the reuse list: not read
    (q / "manifest.json").write_text('{"files": {}}')
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        partt_door.PartQDoor.from_plan(block)  # Part Q's manifest itself differs from the hash in the plan


# --- R7 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_plan_takes_the_calibration_from_its_own_record_by_hash(tmp_path: Path) -> None:
    rec = {**core.envelope("calibration", "T"), **{k: v for k, v in CALIB.items() if k != "records"}, "code_hashes": {"studies/p10is2/engine.py": "a" * 64}, "repetition": 0}
    path = tmp_path / "calibration_0.json"
    core.write_record(path, rec, overwrite=False)
    block = partt_stages.calibration_from_record(path)
    assert block["U"] == 2000 and block["record"]["sha256"] == file_sha256(path) and block["records"]["calibration_0"]["code_hashes"]
    assert partt_stages.calibration_from_record(path, file_sha256(path))["U"] == 2000
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        partt_stages.calibration_from_record(path, "0" * 64)  # a record edited after the plan
    core.write_record(tmp_path / "standin.json", {**rec, "stand_in": True}, overwrite=False)
    with pytest.raises(core.StageRefused, match="stand-in"):
        partt_stages.calibration_from_record(tmp_path / "standin.json")


def test_the_plan_records_part_q_the_charge_and_the_basis_of_its_units_and_rederives_like_with_like(tmp_path: Path) -> None:
    q, pq = fake_part_q(tmp_path)
    walk = {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}
    charge = {"seconds": 123.0, "ledgers": {}}
    rec = partt_plan.build_candidate(ROOT, tmp_path / "run", CFG, CALIB, walk=walk, charge_before_freeze=charge, part_q=pq)
    assert rec["part_q"] == pq and rec["charge_before_freeze"] == charge and rec["task_units_basis"] == partt_caps.basis_of(CFG)
    again = partt_plan.build_candidate(ROOT, tmp_path / "run", CFG, CALIB, walk=walk, charge_before_freeze=charge, part_q=pq)
    strip = {"adr", "platform"}
    assert partt_stages.differing_paths(json.loads(json.dumps(core.jsonable({k: v for k, v in rec.items() if k not in strip}))), json.loads(json.dumps(core.jsonable({k: v for k, v in again.items() if k not in strip})))) == []
    without = partt_plan.build_candidate(ROOT, tmp_path / "run", CFG, CALIB, walk=walk, part_q=pq)  # what a re-derivation without the recorded charge would be
    assert partt_stages.differing_paths(json.loads(json.dumps(core.jsonable(rec))), json.loads(json.dumps(core.jsonable(without)))) == [".charge_before_freeze"]


def test_the_ledger_charges_are_listed_and_a_relative_or_missing_ledger_is_refused(tmp_path: Path) -> None:
    led = tmp_path / "charged_ledger.json"
    core.Ledger(led, "T", 1e12).charge_process("calibration", "calibration", "main", 50.0)
    out = partt_stages.ledgers_charge([str(led)])
    assert out["seconds"] == pytest.approx(50.0) and out["ledgers"] == {str(led): pytest.approx(50.0)}
    for bad in ("relative.json", str(tmp_path / "absent.json")):
        with pytest.raises(core.StageRefused, match="absolute path of an existing"):
            partt_stages.ledgers_charge([bad])
    assert time.monotonic() > 0


# --- B2 and R3 ---------------------------------------------------------------------------------------------------------------------------------------
def test_a_rehearsal_and_a_calibration_never_score_an_evaluation_panel() -> None:
    from p10is2_engine_fixtures import world as tiny_world

    from studies.p10is2 import partt_run, scoring
    from studies.p10s2.memory import NullArm

    w = tiny_world(updates=2, n_reps=1)
    for mode in ("rehearsal", "calibration"):
        w.plan_mode = mode
        with pytest.raises(core.StageRefused, match="never scores E_A, E_B, E_C or E_open"):
            scoring.panel_means(w, NullArm())
        with pytest.raises(core.StageRefused, match="never scores"):
            partt_run.reference_task(w)
        with pytest.raises(core.StageRefused, match="never scores"):
            partt_run.combined_reference(w)
    w.plan_mode = "registered"


def test_gate_g1_runs_on_the_real_bundle_shape_without_a_q_check_panel() -> None:
    from p10is2_engine_fixtures import world as tiny_world

    from studies.p10is2 import partt_gates

    w = tiny_world(updates=2, n_reps=1)
    assert "Q_check" in w.partition.panels
    keys = sorted(i.key for i in w.partition.panels["Q_check"])[:5]
    import copy as _copy

    part = _copy.copy(w.partition)  # the fixture's bundle is shared: work on a copy
    part.panels = {k: v for k, v in part.panels.items() if k != "Q_check"}  # the real bundle holds D_cal, D_con, E_A, E_B, E_C, E_open and Q_fit only
    w.partition = part
    with pytest.raises(core.StageRefused, match="needs the Q_check panel"):
        partt_gates.g1(w)  # it used to crash with KeyError 'Q_check'; it never passes on a missing panel
    assert partt_gates.g1(w, q_check_keys=keys)["passed"] is True
    leak = next(iter(w.streams[0].t["A"])).key
    assert partt_gates.g1(w, q_check_keys=[*keys, leak])["passed"] is False  # a Q_check key that is also a training key is a failure


def test_q_check_keys_are_read_through_the_door_keys_only(tmp_path: Path) -> None:
    q = tmp_path / "partq"
    (q / "qcheck/teacher_A/block_000").mkdir(parents=True)
    f = q / "qcheck/teacher_A/block_000/batch_0000000.json"
    f.write_text(json.dumps({"index": 0, "keys": ["a b", "c d"], "scores": [-0.1, -0.2], "texts": ["x", "y"], "tokens": [[1], [2]]}))
    door = partt_door.PartQDoor(q, {"qcheck/teacher_A/block_000/batch_0000000.json": file_sha256(f)})
    assert door.q_check_keys() == ["a b", "c d"]
    f.write_text(json.dumps({"index": 0, "keys": ["changed"]}))
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        door.q_check_keys()


# --- R9 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_a_failed_gate_or_ensemble_check_makes_the_status_engineering_failure_and_stops_the_run(tmp_path: Path) -> None:
    from studies.p10is2 import labels as L
    from studies.p10is2.quantities import Registry, Thresholds

    assert partt_real.engineering_failures_of(tmp_path) == []
    write_json(tmp_path / "gates.json", {"status": "ENGINEERING-FAILURE", "failed": ["G1"]})
    write_json(tmp_path / "ensemble_check.json", {"ok": False})
    fails = partt_real.engineering_failures_of(tmp_path)
    assert len(fails) == 2 and "gates failed" in fails[0] and "ensemble" in fails[1]
    with pytest.raises(core.StageRefused, match="ENGINEERING-FAILURE recorded"):
        partt_real.require_gates_passed(tmp_path, "train")  # nothing further is trained or scored
    partt_real.require_gates_passed(tmp_path, "analysis")  # the analysis states the status
    res = partt_real.analyse(Registry({}), {}, None, {"U": 2000, "converged": True}, required=[], thresholds=Thresholds.from_config(CFG), engineering_failure=fails)
    assert res["status"]["status"] == L.STOP_ENGINEERING if hasattr(L, "STOP_ENGINEERING") else "ENGINEERING" in str(res["status"]["status"])
    assert "lines" not in res  # no line is derived under it


def test_the_config_cites_the_rulings_addendum_by_hash() -> None:
    assert CFG["rulings_addendum_sha256"] == file_sha256(ROOT / CFG["rulings_addendum"])  # the rulings the implementation follows, beside the ADR's reference


# --- R4 (G5(b)), R9 (the ensemble integrity check) -------------------------------------------------------------------------------------------------------
def test_g5b_a_store_with_every_gate_at_zero_adds_nothing_and_the_check_notices_a_changed_read() -> None:
    from p10is2_engine_fixtures import world as tiny_world

    from studies.p10is2 import engine, partt_gates

    w = tiny_world(updates=2, n_reps=1)
    spec = engine.CellSpec("M1", "AB", 0)
    arm, rows, opts = engine.build_cell_arm(w, spec, None)
    engine.train_cell(w, spec, arm, rows, opts, 2)
    assert partt_gates.g5b(arm.store, core.seeded_generator(934900, "probe", {934900}))["passed"] is True
    res = partt_gates.g5(w, arm)
    assert res["new_store_gate_zero_adds_nothing"]["passed"] is True and res["passed"] is True


def test_the_ensemble_integrity_check_passes_on_the_oracle_ensemble_and_fails_on_a_changed_score() -> None:
    import copy as _copy

    from p10is2_engine_fixtures import world as tiny_world

    from studies.p10is2 import partt_run

    w = tiny_world(updates=2, n_reps=1)
    rec = partt_run.combined_reference(w)["ensemble"]
    assert partt_run.ensemble_check(w, rec)["ok"] is True  # each ensemble answer is the stored output of its teacher: the score equals the teacher's own
    bad = _copy.deepcopy(rec)
    bad["C2"]["tested_by_language"]["A"] = float(bad["C2"]["tested_by_language"]["A"]) + 0.01
    out = partt_run.ensemble_check(w, bad)
    assert out["ok"] is False and out["differences"][0]["language"] == "A"


# --- ruling 2 ----------------------------------------------------------------------------------------------------------------------------------------
def test_the_calibration_record_states_the_overlap_with_the_registered_draws_by_code() -> None:
    from studies.p10s2.data import TrainItem

    def items(keys: list[str]) -> list[TrainItem]:
        return [TrainItem(k, k, "t", 0) for k in keys]

    reg = [{"A": items(["a", "b", "c"]), "B": items(["x"])}, {"A": items(["d", "e"]), "B": items(["y"])}]
    cal = [{"A": items(["a", "z", "d", "q"]), "B": items(["x", "w"])}]
    out = partt_real.draw_overlap(cal, reg)
    assert out["A"] == [{"draw": 0, "items": 4, "in_registered_draws": 2, "share": 0.5}] and out["B"][0]["in_registered_draws"] == 1 and out["B"][0]["share"] == 0.5


# --- B4: the caps are written by code; one Part T ledger ---------------------------------------------------------------------------------------------
def test_caps_config_writes_exactly_the_proposal_once() -> None:
    basis = partt_caps.basis_of(CFG)
    items = partt_plan.stage_items(CALIB)
    rec = {"caps_formula": partt_caps.CAPS_FORMULA, "rates_seconds_per_unit": {k: 0.01 for k in partt_caps.required_kinds(items, basis)}, "overhead_seconds": {s: 10.0 for s in partt_plan.STAGES}}
    proposal = partt_caps.proposal_from_record(rec, items, basis, 7200.0)
    text = (ROOT / core.CONFIG_T).read_text()
    import re
    import tomllib

    text = re.sub(r"(?m)^((?:gates|train|evaluate|controls|combined|recompute|analysis|report|total)_hours) = [0-9.]+", r"\1 = 0.0", text).replace("provisional = false", "provisional = true")  # start from the unset state
    new = partt_caps.apply_caps_text(text, proposal)
    cfg = tomllib.loads(new)
    assert cfg["caps"]["provisional"] is False and {k: cfg["stage_caps"][k] for k in proposal} == proposal and partt_caps.zero_caps(cfg, partt_plan.STAGES) == []
    with pytest.raises(core.StageRefused, match="already entered"):
        partt_caps.apply_caps_text(new, proposal)  # written once



# --- seed registry revision 5: the config equals the registry's rows, no seed literal in code ------------------------------------------------------------
def test_seeds_equal_the_registry_revision_5_rows() -> None:
    s = CFG["seeds"]
    assert s["init_test"] == [330281, 330289]
    got = sorted(v for i in (0, 1) for v in core.partt_replicate_values(CFG, "test", i)["init"].values())
    assert got == list(range(330281, 330297)) and not set(got) & {330301, 330302, 330303}  # P10-I-S3's registered initialisation seeds
    assert core.partt_replicate_values(CFG, "rehearsal", 0)["data"]["training_draw"] == 252002 and s["rehearsal_base"] == 252001
    pieces = [core.partt_replicate_values(CFG, "calibration", i)["route_pieces"] for i in range(4)] + [core.partt_replicate_values(CFG, "rehearsal", 0)["route_pieces"]]
    assert pieces == [251019, 251119, 251219, 251319, 252019]
    assert [core.partt_replicate_values(CFG, "test", i)["route_pieces"] for i in (0, 1)] == [934019, 934119]
    assert core.partt_replicate_values(CFG, "registered", 0)["route_pieces"] == 250918 == s["route_accuracy_pieces"]
    assert s["g5_probe"] == 250919 and core.g5_probe_seed(CFG, "registered") == 250919 and core.g5_probe_seed(CFG, "rehearsal") == s["g5_probe_test"]
    for m, n in (("calibration", 4), ("rehearsal", 1), ("test", 2)):
        for i in range(n):
            v = core.partt_replicate_values(CFG, m, i)
            assert v["route_pieces"] != v["data"]["router"]  # outside registered mode the pieces never reuse the router seed


def test_g9_names_every_derived_initialisation_value_and_cites_revision_5() -> None:
    import hashlib

    from studies.p10is2.common import gates

    named = gates.named_values("T", CFG)
    assert set(range(330281, 330297)) <= named["initialisation"] and 330298 not in named["initialisation"]
    assert 250919 in named["analysis and route accuracy (inside the partition-side row)"]
    assert CFG["seeds"]["registry_checker"].endswith("seed_registry_check_r5.py") and CFG["seeds"]["own_file_globs"] == ["configs/p10is2_*", "studies/p10is2/*", "tests/test_p10is2_*"]
    for k in ("registry_checker", "registry_addendum"):
        assert hashlib.sha256((ROOT / CFG["seeds"][k]).read_bytes()).hexdigest() == CFG["seeds"][k + "_sha256"]


def test_the_rehearsal_training_draw_uses_its_own_seed_and_is_recorded() -> None:
    from studies.p10s2.data import TrainItem

    pool = {c: [TrainItem(f"{c}{i}", f"{c}{i}", "t", i) for i in range(30)] for c in core.TASKS}
    before = len(core.recorded_seeds())
    d = partt_real.rehearsal_draws(pool, CFG, per=10)
    assert len(d) == 1 and all(len(d[0][c]) == 10 for c in core.TASKS)
    assert core.recorded_seeds()[before:] == [(252002, "rehearsal training draw")]


def test_no_part_t_module_holds_an_integer_literal_in_a_registered_or_test_seed_range() -> None:
    import ast

    files = [p for p in (ROOT / "studies/p10is2").rglob("*.py") if "partq" not in p.parts and "launch" not in p.parts]
    bad: list[str] = []
    for f in files:
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool) and (250001 <= n.value <= 259999 or 330201 <= n.value <= 330299 or 934001 <= n.value <= 934999) and not (f.name == "core.py" and n.value in (252901, 252915)):  # the only exception: Part Q's own rehearsal-range assertion (252901-252914)
                bad.append(f"{f.relative_to(ROOT)}:{n.lineno}: {n.value}")
    assert bad == [], bad


# --- rulings 16, 17, 19 (second addendum) --------------------------------------------------------------------------------------------------------------
def test_ruling_16_the_rehearsal_bundle_is_disjoint_from_every_e_set_and_q_check_and_refused_otherwise() -> None:
    import dataclasses

    from p10is2_engine_fixtures import bundle

    from studies.p10is2 import partt_rehearsal

    b = bundle()
    q_check = [i.key for i in b.panels["Q_check"]] if "Q_check" in b.panels else []
    rb = partt_rehearsal.rehearsal_bundle(b, CFG, q_check)
    forbidden = {i.key for n in ("E_A", "E_B", "E_C", "E_open", "Q_check") for i in b.panels.get(n, [])} | set(q_check)
    for n in ("E_A", "E_B", "E_C", "D_cal"):
        assert not ({i.key for i in rb.panels[n]} & forbidden), n
    leaky = dataclasses.replace(b, panels={**b.panels, "E_open": [b.panels["D_cal"][0]]})  # an evaluation set that holds a D_cal item: the rehearsal bundle must refuse
    with pytest.raises(core.StageRefused, match="ruling 16"):
        partt_rehearsal.rehearsal_bundle(leaky, CFG)
    with pytest.raises(core.StageRefused, match="ruling 16"):
        partt_rehearsal.rehearsal_bundle(b, CFG, [b.panels["D_cal"][1].key])  # a Q_check key that is a D_cal item


def test_ruling_17_the_counting_charge_is_read_from_its_ledger_and_the_registered_ledger_starts_from_plan_plus_counting(tmp_path: Path) -> None:
    led = tmp_path / "charged_ledger.json"
    core.Ledger(led, "T", 1e12).charge_process("train", "counting", "main", 123.0)
    rec = {"charged_ledgers": {str(led): 123.0}, "charged_seconds": 123.0}
    assert partt_stages.counting_charge_of(rec) == 123.0
    with pytest.raises(core.StageRefused, match="holds"):
        partt_stages.counting_charge_of({**rec, "charged_seconds": 5.0})  # the record disagrees with the ledger
    with pytest.raises(core.StageRefused, match="no ledger"):
        partt_stages.counting_charge_of({"charged_seconds": 1.0})
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    plan = planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "items": {}, "stage_caps": {}, "charge_before_freeze": {"seconds": 40.0}}, "T", freeze_dir / "partt_plan.json")
    assert partt_tasks.charge_before_freeze(plan) == 40.0
    (freeze_dir / "partt_freeze_record.json").write_text(json.dumps({"pre_freeze_charge": {"registered_ledger_starts_from_seconds": 163.0}}))
    assert partt_tasks.charge_before_freeze(plan) == 163.0


def test_ruling_19_the_report_states_the_q_check_limitation() -> None:
    from p10is2_partt_fixtures import quantities

    from studies.p10is2 import labels as L
    from studies.p10is2 import report

    q = quantities()
    text = report.render(L.study_status(q.reg, required=partt_plan.required_keys()), L.derive_all(q), {"U": 2000, "converged": True, "draws": "DISJOINT DRAWS", "shared_share": {}})
    assert "DISCLOSED LIMITATION (ruling 19)" in text and "by English key only" in text
