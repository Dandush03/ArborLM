# ruff: noqa: E501
"""P9II pre-freeze fixes (audit 2026-11-15): one test or more for each of B1, M1 to M7 and the minors m3 to m15, on synthetic records of the full registry and on tiny
test-seed runs, plus the chunked evaluation at 4,096 and 16,384 slots on test seeds. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p9ii_classes import ALL, GATES_OK, NONE, obs, stage_data  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p9 import controls, pool  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9ii import analysis as A  # noqa: E402
from studies.p9ii import (  # noqa: E402
    budget,
    core,
    diagnostics,
    evaluate,
    gates,
    model,
    report,
    stages,
    train,
)
from studies.p9ii import classes as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SMALL = d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
HYPER = core.Hyper(lambda_=1.0, u_pre=4.0, k0_fraction=0.125, mu=0.1)
GIB = 2**30


def parse(*argv: str) -> Any:
    return stages.build_parser().parse_args(list(argv))


def corpus() -> bytes:
    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def small_draw() -> d.StudyData:
    return d.build_study_data(core.test_seeds(1), corpus(), sizes=SMALL)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def rates(per_update: float = 0.01, evaluation: float = 2.0, overhead: float = 2.0, train_rss: int = 600 * 2**20, eval_rss: int = 700 * 2**20, task_rss: int = 750 * 2**20) -> budget.Rates:
    return {i: budget.Rate(per_update, train_rss, train_rss, evaluation, overhead, eval_rss, task_rss) for i in budget.rehearsal_items()}


# --- B1: task-level times -----------------------------------------------------------------------------------------------------------------------
def test_task_overhead_is_measured_from_the_pool_task_and_enters_every_projection() -> None:
    train_rec = {"arm": "A0", "slots": 4096, "phase": "main", "label": "L", "seconds_per_update": 0.01, "peak_rss_bytes": 100, "sampled_rss_bytes": 120, "wall_seconds": 3.0}
    eval_rec = {"label": "L", "evaluation_wall_seconds": 2.0, "peak_rss_bytes": 900}
    r = budget.rates_from_records([train_rec], [eval_rec], {"REH-A0-n4096-main": {"seconds": 7.0, "peak_rss_bytes": 950}})[("A0", 4096, "main")]
    assert r.task_overhead_seconds == 2.0 and r.evaluation_peak_rss_bytes == 900 and r.task_peak_rss_bytes == 950  # 7 - 3 - 2
    assert budget.rates_from_records([train_rec], [eval_rec], {"REH-A0-n4096-main": {"seconds": 1.0, "peak_rss_bytes": 1}})[("A0", 4096, "main")].task_overhead_seconds == 0.0  # never negative
    assert budget.rates_from_records([train_rec], [eval_rec])[("A0", 4096, "main")].task_overhead_seconds == 0.0
    with_o, without = rates(overhead=2.0), rates(overhead=0.0)
    assert budget.cell_training_seconds("A0", 4096, 1, with_o, HYPER) == pytest.approx(8192 * 0.01 + 2.0)
    assert budget.cell_evaluation_seconds("A0", 4096, 1, with_o) == pytest.approx(2.0 + 2.0)  # one readout plus the process start-up
    assert budget.cell_evaluation_seconds("A0", 16384, 2, with_o) == pytest.approx(2 * 2.0 + 2.0)
    p, q = budget.stage_projection(core.stage1_cells(), 1, with_o, HYPER), budget.stage_projection(core.stage1_cells(), 1, without, HYPER)
    assert p.evaluation_seconds == pytest.approx(22 * 4.0) and q.evaluation_seconds == pytest.approx(22 * 2.0)  # the evaluation projection doubles: the cap has real margin


def test_the_dry_rehearsal_measures_task_overhead_and_records_memory_and_costs(dry_run: dict[str, Any]) -> None:
    proj = core.read_record(dry_run["root"] / "P9IIDRY-rehearsal" / "projection.json", "projection")
    assert all(v["task_overhead_seconds"] > 0 and v["evaluation_peak_rss_bytes"] > 0 and v["task_peak_rss_bytes"] > 0 for v in proj["rates"].values())
    assert set(proj["memory_by_stage"]) == {"stage1", "stage2", "stage3"} and proj["calibration_sha256"] is None and "cost_differences" in proj


# --- M1: the rehearsal runs at the calibrated values, and the projection is bound to them ------------------------------------------------------
def test_rehearse_refuses_without_the_calibration_record_outside_dry(tmp_path: Path) -> None:
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "r"), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path), "--stage-cap-seconds", "10"]) == 2
    assert not (tmp_path / "r").exists()


def frozen_repo(tmp: Path, *, caps: dict[str, Any] | None = None, projection_hyper: dict[str, float] | None = None, memory_ok: bool = True) -> dict[str, Any]:
    """A throw-away repository directory with a consistent freeze: calibration and projection records, cap table, draw plan and the sixteen data manifests."""
    repo, run = tmp / "repo", tmp / "run"
    (repo / "studies" / "p9ii" / "freeze").mkdir(parents=True)
    cal = tmp / "calibration.json"
    core.write_record(cal, {**core.envelope("calibration"), "hyper": core.Hyper(1.0, 2048.0, 0.125, 1.0).as_json()})
    table = caps if caps is not None else budget.caps_table(rates(), core.Hyper(1.0, 2048.0, 0.125, 1.0), gates_wall_seconds=8.0, analysis_wall_seconds=3.0, report_wall_seconds=3.0)
    caps_path = repo / stages.CAPS_FILE
    write_json(caps_path, core.jsonable(table))
    memory = {f"stage{n}": {"ok": memory_ok, "peak_rss_bytes": 1} for n in (1, 2, 3)}
    proj = tmp / "projection.json"
    core.write_record(proj, {**core.envelope("projection"), "hyper": projection_hyper or core.Hyper(1.0, 2048.0, 0.125, 1.0).as_json(), "calibration_sha256": file_sha256(cal), "memory_by_stage": memory, "rates": {budget.item_label(i): __import__("dataclasses").asdict(r) for i, r in rates().items()}})
    for name in (*core.DRAW_NAMES, *core.RESERVE_NAMES):
        core.write_record(stages.manifest_dir(run, name) / "data_manifest.json", {**core.envelope("data_manifest"), "seed_set": name, "g1_passed": True})
    assert stages.cmd_draw_plan(parse("draw-plan", "--run-dir", str(run))) == 0
    plan = {
        "calibration": {"path": str(cal), "sha256": file_sha256(cal)},
        "projection": {"path": str(proj), "sha256": file_sha256(proj)},
        "stage_caps_sha256": file_sha256(caps_path),
        "run_dir": str(run),
        "draw_plan": {"sha256": file_sha256(run / "draw_plan.json")},
        "data_manifests": {n: file_sha256(stages.manifest_dir(run, n) / "data_manifest.json") for n in (*core.DRAW_NAMES, *core.RESERVE_NAMES)},
    }
    write_json(repo / stages.FREEZE_PLAN, plan)
    return {"repo": repo, "run": run, "plan": plan, "cal": cal, "proj": proj, "caps": table}


def test_verify_plan_binds_every_identity(tmp_path: Path) -> None:
    f = frozen_repo(tmp_path)
    stages.verify_plan(f["plan"], f["repo"], f["run"])  # a consistent freeze passes
    for key in ("calibration", "projection"):
        bad = copy.deepcopy(f["plan"])
        bad[key]["sha256"] = "0" * 64
        with pytest.raises(pool.StageRefused, match=key):
            stages.verify_plan(bad, f["repo"], f["run"])
    for mutate, what in ((lambda p: p.update(stage_caps_sha256="1" * 64), "stage-cap"), (lambda p: p["draw_plan"].update(sha256="2" * 64), "draw plan"), (lambda p: p["data_manifests"].update({"p9ii-draw-7": "3" * 64}), "data manifest"), (lambda p: p.update(run_dir=str(tmp_path / "elsewhere")), "run directory")):
        bad = copy.deepcopy(f["plan"])
        mutate(bad)
        with pytest.raises(pool.StageRefused, match=what):
            stages.verify_plan(bad, f["repo"], f["run"])
    short = copy.deepcopy(f["plan"])
    del short["data_manifests"]["p9ii-reserve-2"]
    with pytest.raises(pool.StageRefused):
        stages.verify_plan(short, f["repo"], f["run"])


def test_projection_measured_at_other_values_than_the_calibrated_ones_is_refused(tmp_path: Path) -> None:
    f = frozen_repo(tmp_path, projection_hyper=core.Hyper().as_json())  # the worst-case grid values, as the first rehearsal had
    with pytest.raises(pool.StageRefused, match="calibrated values"):
        stages.verify_plan(f["plan"], f["repo"], f["run"])


# --- M2: memory, evaluation peaks and the chunked evaluation ------------------------------------------------------------------------------------
def test_memory_rule_covers_evaluation_and_task_peaks_per_stage() -> None:
    train_only = {i: budget.Rate(0.01, int(0.73 * GIB), int(0.73 * GIB), 1.0) for i in budget.rehearsal_items()}
    assert budget.memory_headroom(train_only)["ok"]  # the audit's finding: the training peaks alone looked fine
    r = rates(train_rss=int(0.73 * GIB), eval_rss=int(1.0 * GIB), task_rss=int(1.0 * GIB))
    r[("A0", 65536, "main")] = budget.Rate(0.05, int(0.73 * GIB), int(0.73 * GIB), 5.0, 2.0, int(1.529 * GIB), int(1.5 * GIB))  # the evaluation peak that fails 2 x in 3 GiB
    by = budget.memory_by_stage(r)
    assert by["stage1"]["ok"] and by["stage2"]["ok"]
    assert not by["stage3"]["ok"] and by["stage3"]["status"] == "NOT RUN — BUDGET (MEMORY)" and by["stage3"]["peak_rss_bytes"] == int(1.529 * GIB)
    assert not budget.memory_headroom(r)["ok"] and budget.memory_headroom(r)["slots"] is None
    only_task = rates(train_rss=1, eval_rss=1, task_rss=int(1.6 * GIB))
    assert not budget.memory_headroom(only_task)["per_worker_ok"]  # the pool task's peak counts too
    assert budget.memory_headroom(r, 4096)["ok"] and budget.NOT_RUN_MEMORY == "NOT RUN — BUDGET (MEMORY)"


def test_stage_gate_prints_not_run_memory_for_stage3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "run"
    s2 = stage_data(2, {"A5-C": ALL}, core.stage2_cells(["A5-C"]))
    monkeypatch.setattr(stages.analysis, "load_stage", lambda *a, **k: s2)
    core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "status": None, "advancing": ["A5-C"], "arms": ["A0", "A5-C"]})
    table = {"A0": {"total_seconds": 10.0}, "A5-C": {"total_seconds": 10.0}, "A1": {"total_seconds": 10.0}, "A5-D": {"total_seconds": 10.0}}
    proj = tmp_path / "projection.json"
    core.write_record(proj, {**core.envelope("projection"), "stage3_table": table, "stage2_table": {}, "memory_by_stage": {"stage3": {"ok": False, "peak_rss_bytes": 1, "status": budget.NOT_RUN_MEMORY}}})
    assert stages.main(["stagegate", "--run-dir", str(run), "--after", "2", "--projection", str(proj), "--ledger-root", str(tmp_path)]) == 0
    gate = core.read_record(run / "stage_gate_3.json", "stage_gate")
    assert gate["selected"] == "A5-C" and gate["run"] is False and gate["status"] == "NOT RUN — BUDGET (MEMORY)"


@pytest.fixture(scope="module")
def real_draw() -> d.StudyData:
    return d.build_study_data(core.test_seeds(4), corpus())  # the registered sizes


@pytest.mark.parametrize(("arm", "slots"), [("A0", 4096), ("A5-C", 4096), ("A0", 16384), ("A1", 16384)])
def test_chunked_evaluation_gives_the_same_record(real_draw: d.StudyData, backbone, arm: str, slots: int) -> None:  # type: ignore[no-untyped-def]
    facts = core.FACTS_PROPORTIONAL[slots]
    rows = evaluate.corpus_rows(corpus())
    m = model.build_model(arm, slots, 4, backbone, r1_seed=real_draw.seeds.r1_codes)
    cell = core.make_cell(arm, slots)
    kw: dict[str, Any] = {"frozen_backbone": backbone, "rows": rows, "target_seed": 9}
    plain = evaluate.evaluate_readout(cell, m, real_draw, facts, 8, chunked=False, **kw)
    chunked = evaluate.evaluate_readout(cell, m, real_draw, facts, 8, chunked=True, **kw)
    for record in (plain, chunked):
        record.pop("identity"), record.pop("environment")
    assert json.dumps(core.jsonable(plain), sort_keys=True) == json.dumps(core.jsonable(chunked), sort_keys=True)  # counts, probe, panel statistics, LM losses, G5: bit for bit
    assert plain["g5"]["passed"] and plain["panels"]["A"]["correct"] == chunked["panels"]["A"]["correct"]
    assert m.addition.chunk_elements == (1 << 24)  # restored after the evaluation


def test_eval_chunking_changes_and_restores_the_block_size_and_g5_chunks_agree(small_draw, backbone) -> None:  # type: ignore[no-untyped-def]
    m = model.build_model("A0", 4096, 1, backbone)
    with evaluate.eval_chunking(m):
        assert m.addition.chunk_elements == evaluate.EVAL_CHUNK_ELEMENTS
    assert m.addition.chunk_elements == 1 << 24
    a7 = model.build_model("A7", 4096, 1, backbone)
    with evaluate.eval_chunking(a7):
        pass  # the dense control has no block size: nothing to change
    rows = evaluate.corpus_rows(corpus())[:300, :64].contiguous()
    assert evaluate.g5_check_chunked(m, backbone, rows, rows=64) == model.g5_check(m, backbone, rows)
    with torch.no_grad():
        next(p for n, p in m.named_parameters() if n.startswith("backbone.")).add_(1e-3)
    bad = evaluate.g5_check_chunked(m, backbone, rows, rows=64)
    assert not bad["passed"] and bad["hash_mismatches"] == model.g5_check(m, backbone, rows)["hash_mismatches"]


# --- M3: the caps of Stages 2 and 3 are looked up by configuration ----------------------------------------------------------------------------
def test_cap_table_has_one_entry_per_configuration_each_twice_the_projection() -> None:
    r, h = rates(), core.Hyper(1.0, 2048.0, 0.125, 1.0)
    table = budget.caps_table(r, h, gates_wall_seconds=8.0, analysis_wall_seconds=30.0, report_wall_seconds=70.0)
    proj2, proj3 = budget.stage2_projection_table(r, h), budget.stage3_projection_table(r, h)
    assert len(table["stage2"]) == 16 and set(table["stage2"]) == {budget.config_key(c) for c in budget.stage2_configurations()} and set(table["stage3"]) == {"A0", "A1", "A5-C", "A5-D"}
    for key, entry in table["stage2"].items():
        assert entry["train"] == 2 * proj2[key]["training_seconds"] and entry["evaluate"] == 2 * proj2[key]["evaluation_seconds"]
    for key, entry in table["stage3"].items():
        assert entry["train"] == 2 * proj3[key]["training_seconds"] and entry["evaluate"] == 2 * proj3[key]["evaluation_seconds"]
    p1 = budget.stage_projection(core.stage1_cells(), 1, r, h)
    assert table["stage1"] == {"train": 2 * p1.training_seconds, "evaluate": 2 * p1.evaluation_seconds}
    assert table["gates"] == budget.CAP_FLOOR_SECONDS and table["analysis"] == budget.CAP_FLOOR_SECONDS and table["report"] == 140.0  # twice a measured time, with the stated floor
    assert table["stage2"]["A2+A1"]["train"] > table["stage2"]["A0-only"]["train"]  # a bigger configuration has a bigger cap


def test_every_stage2_configuration_finds_its_cap_and_a_missing_one_refuses(tmp_path: Path) -> None:
    f = frozen_repo(tmp_path)
    for advancing in budget.stage2_configurations():
        core.write_record(f["run"] / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": list(advancing)}) if not (f["run"] / "stage_gate_1.json").exists() else (f["run"] / "stage_gate_1.json").unlink()
        core.write_record(f["run"] / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": list(advancing)})
        assert stages.stage_caps_for("stage2", f["caps"], f["run"]) == f["caps"]["stage2"][budget.config_key(advancing)]
    for selected in ("A0", "A1", "A5-C", "A5-D"):
        core.write_record(f["run"] / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": selected}) if not (f["run"] / "stage_gate_3.json").exists() else None
        write_json(f["run"] / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": selected})
        assert stages.stage_caps_for("stage3", f["caps"], f["run"]) == f["caps"]["stage3"][selected]
    thin = {**f["caps"], "stage2": {k: v for k, v in f["caps"]["stage2"].items() if k != "A2+A1"}}
    write_json(f["run"] / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": ["A2", "A1"]})
    with pytest.raises(pool.StageRefused, match="A2\\+A1"):
        stages.stage_caps_for("stage2", thin, f["run"])
    with pytest.raises(pool.StageRefused):
        stages.stage_caps_for("stage9", f["caps"], f["run"])
    with pytest.raises(budget.CapMissing):
        budget.cap_for(f["caps"], "stage3", "A4")  # a scheduled arm never has a Stage 3 entry
    assert budget.cap_for(f["caps"], "gates") == f["caps"]["gates"]


def test_registered_driver_passes_the_cap_of_the_selected_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = frozen_repo(tmp_path)
    seen: dict[str, Any] = {}
    monkeypatch.setattr(stages, "check_preconditions", lambda *a, **k: {"commit": "x", "tree": "y"})
    monkeypatch.setattr(stages, "run_cells_stage", lambda args, stage, **kw: seen.update(stage=stage, **kw) or 0)
    base = ["--run-dir", str(f["run"]), "--repo", str(f["repo"]), "--freeze-commit", "x", "--caps", stages.CAPS_FILE]
    for advancing in (["A5-C", "A4"], ["A2", "A1"], []):
        write_json(f["run"] / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": advancing})
        seen.clear()
        assert stages.main(["registered", "stage2", *base]) == 0
        entry = f["caps"]["stage2"][budget.config_key(advancing)]
        assert seen == {"stage": 2, "cap_train": entry["train"], "cap_eval": entry["evaluate"]}
    write_json(f["run"] / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": ["A2", "A1"]})
    table = copy.deepcopy(f["caps"])
    del table["stage2"]["A2+A1"]
    write_json(f["repo"] / stages.CAPS_FILE, core.jsonable(table))
    plan = {**f["plan"], "stage_caps_sha256": file_sha256(f["repo"] / stages.CAPS_FILE)}
    write_json(f["repo"] / stages.FREEZE_PLAN, plan)
    assert stages.main(["registered", "stage2", *base]) == 2  # a configuration with no entry refuses
    assert stages.main(["registered", "stage2", "--run-dir", str(f["run"]), "--repo", str(f["repo"]), "--freeze-commit", "x", "--caps", "other.json"]) == 2  # the cap table is fixed


def test_registered_driver_refuses_stage3_on_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = frozen_repo(tmp_path, memory_ok=False)
    monkeypatch.setattr(stages, "check_preconditions", lambda *a, **k: {"commit": "x", "tree": "y"})
    monkeypatch.setattr(stages, "run_cells_stage", lambda *a, **k: pytest.fail("a stage that fails the memory rule must not run"))
    write_json(f["run"] / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": "A0"})
    assert stages.main(["registered", "stage3", "--run-dir", str(f["run"]), "--repo", str(f["repo"]), "--freeze-commit", "x", "--caps", stages.CAPS_FILE]) == 2


def test_caps_command_writes_the_table_once(tmp_path: Path) -> None:
    f = frozen_repo(tmp_path)
    out = tmp_path / "caps.json"
    argv = ["caps", "--projection", str(f["proj"]), "--out", str(out), "--gates-wall-seconds", "8", "--analysis-wall-seconds", "40", "--report-wall-seconds", "5"]
    assert stages.main(argv) == 0
    written = json.loads(out.read_text())
    assert written["analysis"] == 80.0 and written["gates"] == budget.CAP_FLOOR_SECONDS and len(written["stage2"]) == 16
    assert stages.main(argv) == 2  # never overwritten


# --- M4: the draw plan and G1 and G2 per draw are enforced ----------------------------------------------------------------------------------
def test_registered_data_commands_need_an_ok_plan_and_passed_g1(tmp_path: Path) -> None:
    args = parse("train", "--mode", "registered", "--run-dir", str(tmp_path), "--draw", "2")
    with pytest.raises(pool.StageRefused, match="no draw plan"):
        stages.seeds_named(args)
    f = frozen_repo(tmp_path / "ok")
    assert stages.seeds_named(parse("train", "--mode", "registered", "--run-dir", str(f["run"]), "--draw", "2")).facts == 190101
    manifest = stages.manifest_dir(f["run"], "p9ii-draw-5") / "data_manifest.json"
    core.write_record(manifest, {**core.envelope("data_manifest"), "seed_set": "p9ii-draw-5", "g1_passed": False})
    with pytest.raises(pool.StageRefused, match="draw 5"):
        stages.require_draw_plan(f["run"])  # a draw the plan uses did not pass G1
    bad = tmp_path / "bad"
    for name in (*core.DRAW_NAMES, *core.RESERVE_NAMES):
        core.write_record(stages.manifest_dir(bad, name) / "data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": name not in ("p9ii-draw-1", "p9ii-draw-2", "p9ii-draw-3")})
    assert stages.cmd_draw_plan(parse("draw-plan", "--run-dir", str(bad))) == 1
    with pytest.raises(pool.StageRefused, match="not ok"):
        stages.require_draw_plan(bad)  # more than two draws failed: nothing runs
    assert stages.main(["train", "--mode", "registered", "--run-dir", str(bad), "--stage", "1"]) == 2


def test_gates_compute_g2_for_every_registered_draw_at_its_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = frozen_repo(tmp_path)
    calls: list[tuple[str, list[int]]] = []

    def fake_controls(study: Any, backbones: Any, counts: list[int]) -> dict[str, Any]:
        calls.append((study.seeds.name, list(counts)))
        failing = study.seeds.name == "p9ii-draw-12"  # a later draw whose no-memory baseline is above chance
        return {"g2": {"passed": not failing}, "fact_counts": counts}

    monkeypatch.setattr(stages, "verified_data", lambda args, seeds, require_manifest: core_study(seeds))
    monkeypatch.setattr(stages.evaluate, "controls_record", fake_controls)
    monkeypatch.setattr(stages, "backbone_for", lambda args: None)
    monkeypatch.setattr(stages, "corpus_bytes", lambda args: stages.SYNTHETIC_CORPUS)
    monkeypatch.setattr(stages.gates, "run_g4_g5_g6", lambda *a, **k: {"g4_defects": [], "g4_passed": True, "g5": {}, "g5_passed": True, "g6": {}, "g6_passed": True, "checks": {}})
    assert stages.main(["work", "gates", "--mode", "registered", "--run-dir", str(f["run"]), "--draw", "1"]) == 0
    record = core.read_record(f["run"] / "gates.json", "gates")
    assert record["g2_passed"] is False and record["g2_by_draw"]["12"] is False and all(v for k, v in record["g2_by_draw"].items() if k != "12")
    assert set(record["g2_by_draw"]) == {str(k) for k in range(1, 15)} and record["g1_passed"] is True and set(record["g1_by_draw"]) == set(record["g2_by_draw"])
    per_draw = [c for c in calls if len(c[1]) == 1]
    assert [c[1][0] for c in per_draw] == [2048] * 8 + [8192] * 4 + [32768] * 2  # each draw at the size of its stage
    assert stages.draw_stage(9) == 2 and stages.draw_stage(14) == 3
    with pytest.raises(pool.StageRefused, match="G2"):
        stages.require_gates_passed(f["run"])  # a failed G2 on any draw stops training


class _Study:
    def __init__(self, seeds: Any) -> None:
        self.seeds = seeds


def core_study(seeds: Any) -> _Study:
    return _Study(seeds)


def test_analysis_makes_a_failed_g2_on_a_later_draw_not_interpreted() -> None:
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells())
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates={**GATES_OK, "g2_by_draw": {**dict.fromkeys(map(str, range(1, 15)), True), "13": False}})
    assert r["outcome"]["outcome"] == C.NOT_INTERPRETED and "G2 failed on draw 13" in r["outcome"]["label"] and r["outcome"]["descriptive_outcome"].startswith("ANSWER-ONLY RELIABLE")
    assert A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates={**GATES_OK, "g2_by_draw": dict.fromkeys(map(str, range(1, 15)), True)})["outcome"]["row"] == 3


# --- M5: a reserve substitution is not a failed cell --------------------------------------------------------------------------------------------
def write_run_for_analysis(tmp: Path, monkeypatch: pytest.MonkeyPatch, *, gate_run: bool | None = None, failed_generate: bool = True, plan_ok: bool = True) -> Path:
    run = tmp / "run"
    core.write_record(run / "gates.json", {**core.envelope("gates"), **GATES_OK, "g2_by_draw": {"1": True}})
    plan = core.plan_draws({n: True for n in (*core.DRAW_NAMES, *core.RESERVE_NAMES)} | {"p9ii-draw-4": False} | ({} if plan_ok else {"p9ii-draw-5": False, "p9ii-draw-6": False}))
    core.write_record(run / "draw_plan.json", {**core.envelope("draw_plan"), "ok": plan.ok, "seed_set_of": {str(k): v for k, v in plan.seed_set_of.items()}, "replacements": {str(k): v for k, v in plan.replacements.items()}, "reason": plan.reason})
    if failed_generate:
        core.write_record(run / "generate-p9ii-draw-4" / "manifest.json", {**core.envelope("stage_manifest"), "stage": "generate-p9ii-draw-4", "tasks": [{"label": "generate-p9ii-draw-4", "status": "failed", "seconds": 1.0}]})
    if gate_run is not None:
        core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": gate_run, "status": None if gate_run else C.NOT_RUN_BUDGET, "advancing": [], "arms": ["A0"]})
    monkeypatch.setattr(stages.analysis, "load_stage", lambda run_dir, stage, cells, unit=8192, failed=(): stage_data(stage, {"A0": ALL}, list(cells)))
    return run


def test_reserve_substitution_keeps_the_study_interpretable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = write_run_for_analysis(tmp_path, monkeypatch)
    assert stages.work_analyze(parse("analyze", "--run-dir", str(run))) == 0
    result = core.read_record(run / "analysis.json", "analysis")["result"]
    assert result["assessment"]["status"] == "COMPLETE" and result["assessment"]["interpretable"] and result["assessment"]["missing"] == []
    assert result["assessment"]["replaced_draws"] == {"4": "REPLACED BY RESERVE 1"} and result["outcome"]["row"] == 3
    plan = core.read_record(run / "draw_plan.json", "draw_plan")
    assert plan["replacements"] == {"4": "p9ii-reserve-1"}


def test_an_exhausted_reserve_list_makes_the_study_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = write_run_for_analysis(tmp_path, monkeypatch, plan_ok=False)
    stages.work_analyze(parse("analyze", "--run-dir", str(run)))
    result = core.read_record(run / "analysis.json", "analysis")["result"]
    assert result["assessment"]["status"] == "INCOMPLETE" and result["outcome"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and any("exhausted" in str(m) for m in result["outcome"]["missing"])


def test_a_failed_generation_of_a_replaced_draw_is_not_a_failed_task_but_a_failed_cell_task_is() -> None:
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells())
    assert A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK, failed_tasks=["generate-p9ii-draw-4:generate-p9ii-draw-4"])["assessment"]["status"] == "COMPLETE"
    assert A.analyze_study(s1, None, None, gates=GATES_OK, failed_tasks=["train1:S1-A0-n4096-d01-j0"])["assessment"]["status"] == "INCOMPLETE"


# --- M6 and m5/m6: hypotheses at 16,384 and the statuses ---------------------------------------------------------------------------------------
def harmed_stage1() -> A.StageData:
    return stage_data(1, {"A0": lambda d, j: (d, j) != (8, 1), "A1": NONE, "A4": NONE, "A5-C": NONE, "A5-D": NONE, "A2": NONE}, core.stage1_cells())


def test_row3_without_a_complete_stage2_does_not_read_the_hypotheses() -> None:
    for status, stage2, why in ((C.NOT_RUN_BUDGET, None, C.NOT_RUN_BUDGET), (C.INCOMPLETE, "incomplete", C.INCOMPLETE)):
        s2 = None
        if stage2:
            s2 = stage_data(2, {"A0": ALL}, core.stage2_cells([]), drop={"A0/d9/j0"})
        r = A.analyze_study(harmed_stage1(), s2, None, stage2_not_run=why if s2 is None else None, gates=GATES_OK)
        assert r["outcome"]["row"] == 3 and r["stage2"]["status"] == status
        for key in ("H19-B", "H19-C", "H19-D", "H19-F", "H19-G"):
            assert r["hypotheses"][key]["reading"] == "NOT TESTED AT 16,384" and r["hypotheses"][key]["stage2_status"] == status  # never CONTRADICTED
        assert r["hypotheses"]["H19-A"]["reading"] in ("supported", "not supported")
        assert r["carried_forward"]["arm"] is None
    assert "CONTRADICTED" not in json.dumps(r["hypotheses"])


def test_row3_with_a_complete_stage2_reads_at_16384_and_carries_forward() -> None:
    s1 = stage_data(1, {"A0": ALL, "A1": NONE}, core.stage1_cells())
    s2 = stage_data(2, {"A0": ALL, "A5-C": NONE}, core.stage2_cells(["A5-C"]))
    r = A.analyze_study(s1, s2, None, stage3_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert r["outcome"]["row"] == 3 and r["hypotheses"]["H19-F"]["reading"] in ("CONTRADICTED", "not supported") and r["carried_forward"]["arm"] == "A0"


def test_incomplete_stage2_carries_nothing_forward_in_any_row() -> None:
    s1 = stage_data(1, {"A5-C": ALL}, core.stage1_cells())
    s2 = stage_data(2, {"A5-C": ALL, "A0": NONE}, core.stage2_cells(["A5-C"]), drop={"A5-C/d9/j1"})
    r = A.analyze_study(s1, s2, None, stage3_not_run=C.INCOMPLETE, gates=GATES_OK)
    assert r["outcome"]["row"] == 6 and C.INCOMPLETE in r["outcome"]["label"] and r["carried_forward"]["arm"] is None


def test_stage3_inherits_a_budget_or_incomplete_reason_when_stage2_did_not_run() -> None:
    s1 = stage_data(1, {"A5-C": ALL}, core.stage1_cells())
    for reason in (C.NOT_RUN_BUDGET, C.INCOMPLETE):
        r = A.analyze_study(s1, None, None, stage2_not_run=reason, gates=GATES_OK)
        assert r["stage2"]["status"] == reason and r["stage3"]["status"] == reason and reason in r["outcome"]["label"]
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert r["stage3"]["status"] == C.NOT_RUN_NO_ARM
    r = A.analyze_study(s1, None, None, stage2_not_run=budget.NOT_RUN_MEMORY, gates=GATES_OK)
    assert r["stage2"]["status"] == budget.NOT_RUN_MEMORY


def test_stage_gate_status_strings_are_the_adr_s(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "run"
    thin = stage_data(1, {"A0": ALL}, core.stage1_cells(), drop={"A4/d3/j1"})
    monkeypatch.setattr(stages.analysis, "load_stage", lambda *a, **k: thin)
    assert stages.main(["stagegate", "--run-dir", str(run), "--after", "1", "--ledger-root", str(tmp_path)]) == 0
    assert core.read_record(run / "stage_gate_1.json", "stage_gate")["status"] == "INCOMPLETE"  # no invented "NOT RUN — STAGE NOT INTERPRETABLE"


def test_stage2_due_but_without_a_manifest_is_incomplete_not_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = write_run_for_analysis(tmp_path, monkeypatch, gate_run=True)
    stages.work_analyze(parse("analyze", "--run-dir", str(run)))
    result = core.read_record(run / "analysis.json", "analysis")["result"]
    assert result["stage2"]["status"] == C.INCOMPLETE and result["stage3"]["status"] == C.INCOMPLETE
    run2 = write_run_for_analysis(tmp_path / "b", monkeypatch, gate_run=False)
    stages.work_analyze(parse("analyze", "--run-dir", str(run2)))
    assert core.read_record(run2 / "analysis.json", "analysis")["result"]["stage2"]["status"] == C.NOT_RUN_BUDGET  # the gate's own recorded reason


# --- M7: generation script and freeze procedure -------------------------------------------------------------------------------------------------
def test_generate_script_and_freeze_readme() -> None:
    import subprocess

    path = ROOT / core.LAUNCH_DIR / "generate.sh"
    text = path.read_text()
    assert text.startswith("#!/bin/sh\n") and "set -eu" in text and 'if [ "$#" -ne 2 ]' in text and "--i-understand-freeze-time" in text and "draw-plan" in text
    assert text.count("--mode registered") == 2 and "for k in 1 2 3 4 5 6 7 8 9 10 11 12 13 14" in text and "for r in 1 2" in text
    assert "$@" not in text and "eval " not in text
    assert subprocess.run(["sh", "-n", str(path)], check=False).returncode == 0
    refused = subprocess.run(["sh", str(path), "only-one"], capture_output=True, check=False)
    assert refused.returncode == 2 and b"usage" in refused.stderr
    wrong = subprocess.run(["sh", str(path), str(ROOT / "x"), "0" * 40], capture_output=True, check=False)
    assert wrong.returncode != 0 and not (ROOT / "x").exists()  # a commit that is not HEAD refuses before anything is generated
    readme = (ROOT / "studies" / "p9ii" / "freeze" / "README.md").read_text()
    for needle in ("generate.sh", "--i-understand-freeze-time", "plan.json", "stage_caps.json", "draw_plan.json", "data_manifests", "calibration_sha256", "freeze commit", "two arguments", "REPLACED BY RESERVE", "(MEMORY)"):
        assert needle in readme
    assert readme.index("generate.sh") < readme.index("One freeze commit")  # generation, G1 and the draw plan run before the freeze commit
    # Before the freeze neither file exists; the freeze commit adds both together (never one alone).
    frozen = [(ROOT / "studies" / "p9ii" / "freeze" / name).exists() for name in ("plan.json", "stage_caps.json")]
    assert all(frozen) or not any(frozen)


# --- m3, m4, m8, m13, m15: training-side minors --------------------------------------------------------------------------------------------------
def tiny(arm: str, draw: d.StudyData, bb: Any, out: Path, updates: int = 8, **kw: Any) -> train.TrainJob:
    return gates.tiny_job(arm, draw, bb, 128, out / arm, hyper=kw.pop("hyper", HYPER), updates=updates, mode="calibration", init_seed=910041, **kw)


def test_no_batch_graph_is_kept_between_updates(small_draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run = train.run_job(tiny("A1", small_draw, backbone, tmp_path, updates=4))
    assert run.model.addition.last_query is None
    copy.deepcopy(run.model)  # blocked by the graph before the fix


def test_g6_after_training_replaces_the_injection_and_the_fact_table(small_draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    answer_before = small_draw.facts.answer.clone()
    tokens = small_draw.streams["panel_a"].tokens[:4, :63].contiguous()
    r = gates.g6_after_training(lambda arm, name, updates: tiny(arm, small_draw, backbone, tmp_path / name, updates=updates), tokens)
    assert r["passed"] and set(r["arms"]) == set(core.LEARNED_ARMS)
    assert all(v["unchanged_by_injection_and_fact_table"] and v["rebuilt_from_state_dict_identical"] and v["stray_tensor_attributes"] == [] for v in r["arms"].values())
    assert torch.equal(small_draw.facts.answer, answer_before)  # the shared draw is restored


def test_train_record_labels_a2_phases_and_records_cpu_seconds_and_analytical_cost(small_draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    a2 = train.train_cell(tiny("A2", small_draw, backbone, tmp_path, updates=8))
    assert a2["trainable_parameters"] == 201217 and a2["trainable_parameters_by_phase"] == {"1": 69120, "2": 201217}
    assert "phase 2" in a2["trainable_parameters_label"] and "phase 1" in a2["parameters_by_group_label"]
    assert a2["cpu_seconds"] > 0 and a2["cost"]["label"] == "analytical counts, not measurements" and "measured" in a2["cost"]["cpu_seconds_label"]
    assert a2["cost"]["key_scores_per_query_forward"] == 4096 and a2["cost"]["key_scores_per_query_address_loss"] == 4096 and a2["cost"]["value_rows_read_per_query"] == 8
    assert a2["cost"]["address_loss_flops_per_update"] == 3 * 2 * 128 * 4096 * 16
    a0 = train.train_cell(tiny("A0", small_draw, backbone, tmp_path, updates=4))
    assert a0["trainable_parameters"] == 201217 and a0["cost"]["address_loss_flops_per_update"] == 0 and a0["cost"]["diversity_loss_flops_per_update"] == 0
    a4 = train.train_cell(tiny("A4", small_draw, backbone, tmp_path, updates=8))
    assert a4["cost"]["value_rows_read_per_query"] > 8 and a4["cost"]["wide_read_flops_per_update"] > 0  # the mean k(t) over the run
    assert train.train_cell(tiny("A5-D", small_draw, backbone, tmp_path, updates=4))["cost"]["diversity_loss_flops_per_update"] == 3 * 2 * 128 * 128 * 16
    assert core.analytical_cost("A7", 4096, 10)["key_scores_per_query_forward"] == 0 and core.analytical_cost("A6", 4096, 10)["value_rows_read_per_query"] == 8


def test_cost_differences_are_rate_differences_by_mechanism() -> None:
    r = rates(per_update=0.01)
    r[("A1", 4096, "main")] = budget.Rate(0.013, 1, 1, 1.0)
    r[("A4", 4096, "k0")], r[("A4", 4096, "k8")] = budget.Rate(0.05, 1, 1, 1.0), budget.Rate(0.01, 1, 1, 1.0)
    diff = budget.cost_differences(r)
    assert diff["L_addr (A1 - A0)"]["4096"] == pytest.approx(0.003) and diff["A4 read at k_0 (k0 - k8)"]["4096"] == pytest.approx(0.04) and "16384" in diff["L_div (A5-D - A0)"]
    assert budget.cost_differences({}) == {}


def test_probe_excludes_unseen_control_facts_by_construction(small_draw, monkeypatch: pytest.MonkeyPatch) -> None:
    stream = d.restrict_stream(small_draw.streams["calibration"], small_draw.facts, 128)
    ids = stream.fact_ids.clone()
    ids[0] = torch.arange(600, 608)  # a context of unseen controls first
    ids[1, 0] = 700
    polluted = d.Stream(stream.name, stream.world, stream.template_set, stream.tokens, ids, stream.cluster, stream.template, stream.sha256)
    monkeypatch.setattr(diagnostics, "restrict_stream", lambda *a, **k: polluted)
    p = diagnostics.build_probe(small_draw, 128, n_facts=64)
    assert int(p.fact.max()) < 128 and p.probe_facts == 64 and int((p.fact >= 128).sum()) == 0


# --- m7, m9, m14 and the calibration under the corrected tie rule ----------------------------------------------------------------------------------
def test_supervision_dependent_denominator_excludes_not_evaluated_draws() -> None:
    flagged = C.TrainingSummary(C.Category(C.NEVER_SEPARATED, None, None, None, None), False, 0.5, 64, True, False, True)
    fine = C.TrainingSummary(C.Category(C.NEVER_SEPARATED, None, None, None, None), False, 0.5, 64, True, False, False)
    cells = {(draw, j): (flagged if draw <= 2 else fine) for draw in range(1, 9) for j in (0, 1)}
    assert C.supervision_dependent(cells)["label"] is None  # 4 of 16
    evaluated = {k for k in cells if k[0] <= 4}  # draws 5 to 8 NOT_EVALUATED
    assert C.supervision_dependent(cells, evaluated)["label"] is None and C.supervision_dependent(cells, evaluated)["of"] == 8
    evaluated = {k for k in cells if k[0] <= 3}
    assert C.supervision_dependent(cells, evaluated)["label"] == C.SUPERVISION_DEPENDENT and C.supervision_dependent(cells, evaluated)["of"] == 6  # 4 of 6 is more than half


def test_tie_rule_orders_finite_inf_between_finite_finite_and_inf_inf() -> None:
    fs = core.first_success_key
    assert fs([100.0, 200.0]) < fs([100.0, math.inf]) < fs([math.inf, math.inf])
    assert fs([300.0, math.inf]) < fs([math.inf, math.inf]) and fs([100.0, 300.0]) < fs([50.0, math.inf])
    v = (0.1, 1.0)
    tied = {0.1: 0.9, 1.0: 0.9}
    assert core.select_value(v, tied, {0.1: fs([math.inf, math.inf]), 1.0: fs([400.0, math.inf])}) == 1.0  # {finite, inf} beats {inf, inf}
    assert core.select_value(v, tied, {0.1: fs([400.0, math.inf]), 1.0: fs([400.0, 500.0])}) == 1.0  # and loses to {finite, finite}
    assert core.select_value(v, tied, {0.1: fs([math.inf, math.inf]), 1.0: fs([math.inf, math.inf])}) == 0.1  # all tied: the first value listed
    assert core.median([400.0, math.inf]) == math.inf  # the old plain median could not tell these apart


def test_calibration_selection_is_unchanged_under_the_corrected_tie_rule() -> None:
    record = json.loads((ROOT / "results" / "p9ii-calibration-2026-11-15" / "calibration.json").read_text())
    chosen = {}
    for arm, entry in record["table"].items():
        values = core.GRID[arm][1]
        minimum = {float(k): core.number(v) for k, v in entry["min_accuracy"].items()}
        keys = {float(k): (0 if math.isfinite(core.number(v)) else 2, core.number(v) if math.isfinite(core.number(v)) else 0.0) for k, v in entry["median_first_success"].items()}
        chosen[arm] = core.select_value(values, minimum, keys)
        assert chosen[arm] == entry["selected"]  # the recorded selection, recomputed
    assert chosen == {"A1": 1.0, "A2": 2048.0, "A4": 0.125, "A5-D": 1.0}
    assert record["hyper"] == {"k0_fraction": 0.125, "lambda": 1.0, "mu": 1.0, "u_pre": 2048.0}


def test_report_prints_every_label_the_adr_lists(tmp_path: Path) -> None:
    s1 = stage_data(1, {"A2": ALL, "A1": ALL, "A1-S": ALL, "A0": NONE, "A5-C": ALL}, core.stage1_cells())
    s2 = stage_data(2, {"A5-C": ALL, "A0": ALL, "A2": ALL, "A1-S": NONE}, core.stage2_cells(["A5-C", "A2"]))
    s3 = stage_data(3, {"A5-C": ALL}, core.stage3_cells("A5-C"))
    for sd in (s1, s2):
        for (arm, d_, j), cd in sd.cells.items():
            if arm == "A2" and cd.summary is not None:
                sd.cells[(arm, d_, j)] = A.CellData(cd.obs, C.TrainingSummary(cd.summary.category, False, 0.5, 64, True, False, True, True, 1.0, 8192, ((64, 1.0),), 4096))
    result = A.analyze_study(s1, s2, s3, stage3_selected="A5-C", gates=GATES_OK, draw_plan={"ok": True, "replacements": {"4": "p9ii-reserve-1"}, "labels": {"4": "REPLACED BY RESERVE 1"}})
    analysis = {"result": core.jsonable(result), "unit_updates": 8192}
    classes = report.class_rows(analysis["result"])
    text = report.render_markdown(analysis, classes, None)
    for label in (C.NEGATIVE_CONTROL_FAILED, C.SUPERVISION_DEPENDENT, C.ADDRESS_RECALL, C.ADDRESS_STABLE, C.ADDRESSES_REMAPPED, C.NEVER_SEPARATED, C.COLLAPSED_RECOVERED, C.COLLAPSED_NOT_RECOVERED, C.SCALE_POSITIVE, C.MID_SCHEDULE, C.ALSO_AT_MATCHED_UPDATES, "d(A2 against A1)", "A6 (oracle reference) relative next-byte loss rise", "REPLACED BY RESERVE 1", "(ADDRESS-SUPERVISED IN TRAINING)", "(LABEL-FREE)", "(escaped cells only)", "(censored at the readout)", "absolute rise"):
        assert label in text, label
    assert "median escape update |" not in text.replace("median escape update (", "")  # two medians, two names, none left under the old one
    assert {"median_escape_update_escaped_cells_only", "median_escape_update_censored_at_readout"} <= set(classes[0])
    assert result["stage1"]["arms"]["A0"]["median_escape_update_escaped_cells_only"] is not None


def test_the_replay_test_pins_the_calibration_code() -> None:
    import test_p9ii_replay as replay

    assert set(replay.EXPECTED) == {"A0", "A1", "A2"} and all(len(h) == 64 for pair in replay.EXPECTED.values() for h in pair)


@pytest.fixture(scope="module")
def dry_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("dry2")
    stages.main(["dry", "--out-root", str(root), "--workers", "6"])
    summary = json.loads((root / "DRY_SUMMARY.json").read_text())
    return {"root": root, "run": Path(summary["run_dir"]), "summary": summary}


def test_obs_helper_is_used() -> None:
    assert obs().distinct_top1 == 200
