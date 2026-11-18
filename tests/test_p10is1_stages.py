# ruff: noqa: E501
"""P10IS1 stages, plan, freeze and rehearsal (ADR-0024 sections 11, 14, 16, 17.1, 18): every registered entry point refuses today (nothing is frozen), the candidate plan is written once and superseded by rule, the
freeze refuses every missing precondition, every stage derives its items from the plan only (the throughput stage lists no cell the plan does not run), gate G9 passes with its extended copy of the registry's checker, the
R2 qualification table, and the tiny synthetic pipeline end to end (training in segments, the whole-cell ladder with no per-arm early stop, evaluation, baselines, timing, throughput) with test seeds only. Self-check only."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import read_json  # noqa: E402
from studies.p10is1 import (  # noqa: E402
    analysis,
    core,
    freeze,
    gates,
    items,
    rehearsal,
    stages,
    synthetic,
)
from studies.p10is1 import labels as L  # noqa: E402
from studies.p10is1 import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config()


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607


def mini_repo(tmp: Path) -> Path:
    """A throw-away repository with this study's own files copied in (no imported roots), clean and committed."""
    repo = tmp / "repo"
    for rel in ("studies/p10is1", "configs/p10is1_capacity.toml", "docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md", "uv.lock"):
        src, dst = ROOT / rel, repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "freeze"))
        else:
            shutil.copy(src, dst)
    git(repo, "init", "-q")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "x")
    return repo


# --- registered entry points refuse today ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("stage", planmod.REGISTERED_STAGES)
def test_every_registered_stage_refuses_today(stage: str, tmp_path: Path) -> None:
    run = tmp_path / "run"
    rc = stages.main(["registered", stage, "--run-dir", str(run), "--freeze-commit", "HEAD"])
    assert rc != 0 and not run.exists()  # nothing is frozen: no freeze plan, no freeze record, no Decision 2; and nothing is written


def test_each_precondition_refuses_by_itself(tmp_path: Path) -> None:
    repo = mini_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD").strip()
    assert planmod.check_preconditions(core.TEST, repo, None) is None  # rehearsal and test modes have no freeze identity
    with pytest.raises(core.StageRefused, match="requires --freeze-commit"):
        planmod.check_preconditions(core.REGISTERED, repo, None)
    with pytest.raises(core.StageRefused, match="not a commit"):
        planmod.check_preconditions(core.REGISTERED, repo, "deadbeef")
    (repo / "stray.txt").write_text("x")
    with pytest.raises(core.StageRefused, match="not clean"):
        planmod.check_preconditions(core.REGISTERED, repo, head)
    (repo / "stray.txt").unlink()
    with pytest.raises(core.StageRefused, match="no freeze plan"):
        planmod.load_registered_plan(repo)
    with pytest.raises(core.StageRefused, match="Decision 2 is recorded there before anything registered runs"):
        planmod.require_decision_2(repo, head)
    # Decision 2 must be COMMITTED, name the full freeze commit and hold DECISION: RUN
    d2 = repo / "results" / "p10is1-freeze-x" / "DECISION_2.md"
    d2.parent.mkdir(parents=True)
    d2.write_text(f"{head}\nDECISION: RUN\n")
    with pytest.raises(core.StageRefused):
        planmod.require_decision_2(repo, head)  # a working file is not a committed record
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "decision")
    assert planmod.require_decision_2(repo, head).endswith("DECISION_2.md")
    d2.write_text(f"{head}\nDECISION: RUN\nDECISION: DO NOT RUN\n")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "withdrawn")
    with pytest.raises(core.StageRefused):
        planmod.require_decision_2(repo, head)
    # the run directory inside the repository must be git-ignored, and so must the ledger
    with pytest.raises(core.StageRefused, match="not git-ignored"):
        planmod.require_ignored_run_dir(repo, repo / "runs" / "x")
    (repo / ".gitignore").write_text("runs/\nledger.json\n")
    planmod.require_ignored_run_dir(repo, repo / "runs" / "x")
    planmod.require_ignored_path(repo, repo / "ledger.json")
    with pytest.raises(core.StageRefused, match="would dirty the tree"):
        planmod.require_ignored_path(repo, repo / "notignored.json")
    planmod.require_ignored_run_dir(repo, tmp_path / "outside")  # outside the repository: cannot dirty it


# --- the candidate plan, the freeze --------------------------------------------------------------------------------------------------------------
CAL = {
    "complete": True, "rates": {u: 0.003 for u in core.units()}, "row_u_p": {"2048": 8192, "8192": 8192, "32768": 16384}, "u0": {"2K/256": 98304, "8K/1K": 131072, "32K/4K": 131072}, "sat256": True,
    "h8": {"undertrained_cells": [], "calibrated_cells": ["2K/4K"]},
}  # fmt: skip


def seed_manifests(run: Path) -> None:
    for d in range(1, 6):
        p = freeze.manifest_path(run, core.registered_seeds(d).name)
        core.write_record(p, {**core.envelope("snapshot"), "sha256s": {"x": str(d)}})


def candidate_args(repo: Path, run: Path, cal: Path, **kw: Any) -> Any:
    import argparse

    return argparse.Namespace(repo=str(repo), run_dir=str(run), calibration=str(cal), projection=kw.get("projection"), s1_run_dir=None, supersede=kw.get("supersede", False))


def test_candidate_plan_is_written_once_and_superseded_by_rule(tmp_path: Path) -> None:
    repo = mini_repo(tmp_path)
    run = tmp_path / "run"
    seed_manifests(run)
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(CAL))
    assert freeze.cmd_candidate_plan(candidate_args(repo, run, cal)) == 0
    plan_path = repo / core.PLAN
    first = plan_path.read_bytes()
    with pytest.raises(core.StageRefused, match="only with --supersede"):
        freeze.cmd_candidate_plan(candidate_args(repo, run, cal))
    assert plan_path.read_bytes() == first
    pl = planmod.Plan.load(plan_path)
    assert len(pl.data["cells"]) == 155 and pl.data["caps_provisional"] is True and pl.data["lane_l"] == core.LANE_L_NOT_LICENSED and pl.data["not_tested_x"] == core.NOT_TESTED_X
    assert pl.data["adr"]["note"].startswith("provenance only") and "docs/decisions" not in " ".join(pl.data["frozen_files"])  # the ADR text is outside the frozen set
    assert not any("ADR" in k for k in pl.data["frozen_files"]) and "configs/p10is1_capacity.toml" in pl.data["frozen_files"] and "uv.lock" in pl.data["frozen_files"]
    assert freeze.cmd_candidate_plan(candidate_args(repo, run, cal, supersede=True)) == 0
    moved = list((plan_path.parent / "superseded").glob("plan-*.json"))
    assert len(moved) == 1 and moved[0].read_bytes() == first  # the old file is moved aside, never deleted
    (repo / planmod.FREEZE_RECORD).write_text("{}")
    with pytest.raises(core.StageRefused, match="a frozen plan is not superseded"):
        freeze.cmd_candidate_plan(candidate_args(repo, run, cal, supersede=True))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({**CAL, "complete": False}))
    (repo / planmod.FREEZE_RECORD).unlink()
    (repo / core.PLAN).unlink()
    with pytest.raises(core.StageRefused, match="not complete"):
        freeze.cmd_candidate_plan(candidate_args(repo, run, bad))  # a return to the human lead is open: no plan is written
    assert not (repo / core.PLAN).exists()


def test_freeze_refuses_each_missing_precondition(tmp_path: Path) -> None:
    import argparse

    repo = mini_repo(tmp_path)
    run = tmp_path / "run"
    seed_manifests(run)
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(CAL))
    fargs = argparse.Namespace(repo=str(repo), rehearsal=str(tmp_path / "rehearsal.json"))
    with pytest.raises(core.StageRefused, match="no candidate plan"):
        freeze.cmd_freeze(fargs)
    freeze.cmd_candidate_plan(candidate_args(repo, run, cal))
    with pytest.raises(core.StageRefused, match="caps.provisional is true"):
        freeze.cmd_freeze(fargs)  # the measuring rehearsal cannot be frozen on: provisional caps
    # a plan above the budget is refused whatever else holds
    pl_path = repo / core.PLAN
    data = read_json(pl_path)
    data["base_plan_above_budget"] = True
    pl_path.write_text(json.dumps(data))
    with pytest.raises(core.StageRefused, match="BASE PLAN ABOVE BUDGET"):
        freeze.cmd_freeze(fargs)


def test_freeze_with_nonprovisional_caps_needs_the_counting_rehearsal_of_this_exact_file(tmp_path: Path) -> None:
    import argparse

    repo = mini_repo(tmp_path)
    cfgp = repo / core.CONFIG
    cfgp.write_text(cfgp.read_text().replace("provisional = true", "provisional = false"))  # the lead sets the caps and clears the flag after the measuring rehearsal
    run = tmp_path / "run"
    seed_manifests(run)
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(CAL))
    freeze.cmd_candidate_plan(candidate_args(repo, run, cal))
    plan_sha = planmod.Plan.load(repo / core.PLAN).data and __import__("arborlm.io", fromlist=["file_sha256"]).file_sha256(repo / core.PLAN)
    rehearsal_path = tmp_path / "rehearsal.json"
    fargs = argparse.Namespace(repo=str(repo), rehearsal=str(rehearsal_path))
    core.write_record(rehearsal_path, {**core.envelope("rehearsal"), "caps_provisional": True, "stages": {s: {"status": "COMPLETE"} for s in freeze.REHEARSAL_STAGES}, "candidate": {"status": "COMPLETE", "plan_file_sha256": plan_sha}})
    with pytest.raises(core.StageRefused, match="made on provisional caps"):
        freeze.cmd_freeze(fargs)
    core.write_record(rehearsal_path, {**core.envelope("rehearsal"), "caps_provisional": False, "stages": {s: {"status": "COMPLETE"} for s in freeze.REHEARSAL_STAGES[:-1]}, "candidate": {"status": "COMPLETE", "plan_file_sha256": plan_sha}}, overwrite=True)
    with pytest.raises(core.StageRefused, match="every stage COMPLETE"):
        freeze.cmd_freeze(fargs)  # a stage missing
    core.write_record(rehearsal_path, {**core.envelope("rehearsal"), "caps_provisional": False, "stages": {s: {"status": "COMPLETE"} for s in freeze.REHEARSAL_STAGES}, "candidate": {"status": "COMPLETE", "plan_file_sha256": "0" * 64}}, overwrite=True)
    with pytest.raises(core.StageRefused, match="every stage COMPLETE"):
        freeze.cmd_freeze(fargs)  # another plan file was rehearsed
    # the re-derivation catches a change of code after the plan was written
    (repo / "studies/p10is1/core.py").write_text((repo / "studies/p10is1/core.py").read_text() + "\n# changed after the plan\n")
    with pytest.raises(core.StageRefused, match="differs from a re-derivation"):
        freeze.cmd_freeze(fargs)


# --- items from the plan only ------------------------------------------------------------------------------------------------------------------------
def plan_of(params: core.PlanParams | None = None) -> planmod.Plan:
    p = params or core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, {u: 0.003 for u in core.units()}, synthetic.U0, synthetic.GRANTED)
    cells = core.planned_cells(p, core.REGISTERED)
    data = {**core.envelope("freeze_plan"), "mode": "registered", "cells": cells, "params": p.to_json(), "stage_caps": {"train_hours": 1.0}}
    return planmod.Plan(data)


def test_every_stage_derives_its_items_from_the_plan_only() -> None:
    pl = plan_of()
    chk = rehearsal.check_plan_items(pl)
    assert chk["passed"], chk["problems"]
    c = chk["counts"]
    assert c["train"] == 155 and c["ladder"] == 3 and c["evaluate"] == 155 - 5 * (4 + 4 + 1) and c["baselines"] == 15 and c["timing"] == 16
    # train items: a ladder cell trains to U0, every other cell to its run length
    by = {i["cell"]: i for i in pl.items("train")}
    for cell in pl.data["cells"]:
        assert by[cell["label"]]["to"] == (cell["u0"] if cell["ladder_cell"] else cell["run"])
    assert {(i["arm"], i["slots"]) for i in pl.items("timing")} >= {("F-OQ", 256), ("R2", 4096), ("R2", 32768), ("D-OQ", 1024), ("H8", 16384)}  # 256 slots and R2's cells are in the timing stage
    # a plan that does not run 2K/256 has no timing item at 256 slots and no throughput item for it
    nosat = core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, {u: 0.003 for u in core.units()}, {"8K/1K": 131072, "32K/4K": 131072}, {"8K/1K": 262144, "32K/4K": 262144}, sat256=False)
    p2 = plan_of(nosat)
    assert len(p2.data["cells"]) == 150 and ("F-OQ", 256) not in {(i["arm"], i["slots"]) for i in p2.items("timing")}
    assert not [i for i in p2.items("throughput") if i["slots"] == 256] and [i for i in p2.items("throughput") if i["arm"] == "F-OQ-IVF"]
    assert all(i["slots"] != 256 for i in p2.items("throughput"))
    # the throughput stage lists only cells the plan runs (the failure of P10-S1's stage): drop a cell from the plan and its items vanish
    pl3 = plan_of()
    pl3.data["cells"] = [x for x in pl3.data["cells"] if not (x["arm"] == "D-OQ" and x["slots"] == 16384)]
    assert not [i for i in pl3.items("throughput") if i["arm"] == "D-OQ" and i["slots"] == 16384]
    assert all(i["cell"] in {x["label"] for x in pl3.data["cells"]} for i in pl3.items("throughput"))
    assert rehearsal.check_plan_items(pl3)["passed"]


def test_gate_g9_passes_with_the_extended_checker_copy_and_records_it() -> None:
    res = gates.seed_gate(CFG, root=ROOT)
    assert res["passed"] is True, res["problems"]
    ck = res["checker"]
    assert ck["result_line"] == "RESULT: PASS" and ck["missing_empty"] and ck["sha256"] == CFG["seed_ranges"]["checker_sha256"] and ck["allocation_rows"] >= 8 and len(ck["copy_sha256"]) == 64
    assert len(ck["substitutions"]) == 3 and res["declared_reuse_not_new"]["adapter_identity_gate_p10s1_draw_1"] > 30
    # the study's own values are checked separately: a config range outside the registry's row fails
    bad = json.loads(json.dumps(CFG))
    bad["seed_ranges"]["registered"] = [240001, 249999]
    rows = gates.allocation_rows((ROOT / CFG["seed_ranges"]["checker"]).read_text(), CFG["seed_ranges"]["checker_allocation_name"])
    assert any("registered range" in p for p in gates.allocation_problems(bad, rows))
    planned = gates.planned_seed_values(CFG)
    assert planned["initialisation"] == {330101, 330102, 330103, 330104, 330105, 330191, 330193, 330192, 330198, 330199}
    assert 240001 + 60 in planned["registered_sets"] and 249201 in planned["rehearsal_set"]


def test_platform_record_and_worker_settings() -> None:
    rec = gates.platform_record()
    assert set(rec) >= {"system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"}
    assert gates.platform_problems(CFG, {**rec, "torch_num_threads": 4})[0].startswith("torch_num_threads")
    assert gates.platform_problems(CFG, {"system": "Darwin", "machine": "arm64", "torch": "2.8.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True}) == []
    assert any("machine" in p for p in gates.platform_problems(CFG, {"system": "Darwin", "machine": "x86_64", "torch": "2.8.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True}))


# --- the reference qualification ---------------------------------------------------------------------------------------------------------------------------
def test_qualification_table_removes_what_r2_fails_on_any_view() -> None:
    n = 2048
    ok = L.Obs(n, 870, 800, disabled=64, shuffled=64, baseline=64)
    fail_c = L.Obs(n, 1100, 800, disabled=64, shuffled=64, baseline=64)
    fail_a = L.Obs(n, 870, 800, disabled=300, shuffled=64, baseline=64)
    low = L.Obs(n, 1100, 300, disabled=500, shuffled=500, baseline=64)  # a_use below 0.25: DEP does not apply: nothing is disqualified
    r2 = {
        (2048, "rehearsal"): {4096: {"A": ok, "B": ok}, 8192: {"A": ok, "B": fail_c}, 512: {"A": low, "B": low}},
        (2048, "cal1"): {4096: {"A": fail_a, "B": ok}, 8192: {"A": ok, "B": ok}},
    }
    t = rehearsal.qualification_table(r2, {2048: 8192})
    assert t["2048"]["0.5"] == ["b", "c"]  # DEP-a fails at fraction 0.5 on the first calibration draw, panel A
    assert t["2048"]["1"] == ["a", "b"]  # DEP-c fails at fraction 1 on the rehearsal draw, panel B
    assert t["2048"]["0.0625"] == ["a", "b", "c"]  # under the a_use floor: stays qualified
    # the table drives the analysis: with 'c' unqualified at fraction 1 a DEP-c failure there is not applied
    reg = synthetic.build(qualification={"8192": {"1": ["a", "b"]}}, excess=lambda a, f, n, d, u, r, p: 300 if (a, f, n, d, u, r) == ("F-OQ", 8192, 4096, 3, 8192, "main") else 0)
    assert analysis.analyze(reg)["capacity"]["arms"]["F-OQ"]["class"] == "CAPACITY_SUPPORTED"
    reg2 = synthetic.build(excess=lambda a, f, n, d, u, r, p: 300 if (a, f, n, d, u, r) == ("F-OQ", 8192, 4096, 3, 8192, "main") else 0)
    assert analysis.analyze(reg2)["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["verdicts"][2] == "DEPENDENCE_FAILED"


# --- the counting rehearsal of a candidate plan file -------------------------------------------------------------------------------------------------------------
def test_run_candidate_runs_analysis_and_report_on_a_synthetic_registry_keyed_by_the_plans_labels(tmp_path: Path) -> None:
    pl = plan_of()
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(core.jsonable(pl.data)))
    rec = rehearsal.run_candidate(p, tmp_path / "run", repo=ROOT)
    assert rec["status"] == "COMPLETE" and len(rec["plan_file_sha256"]) == 64 and rec["analysis_lines"]["C-CAPACITY"] in ("CAPACITY-POSITIVE", "CAPACITY-NEGATIVE", "CAPACITY-INCONCLUSIVE")
    assert rec["item_counts"]["train"] == 155 and rec["report_chars"] > 1000 and not rec["item_problems"]


# --- the tiny synthetic pipeline, end to end --------------------------------------------------------------------------------------------------------------------
def test_the_synthetic_pipeline_runs_every_stage_and_the_whole_cell_stops_together(tmp_path: Path) -> None:
    rec = rehearsal.run_synthetic(tmp_path / "rehearsal", repo=ROOT)
    assert {k: v["status"] for k, v in rec["stages"].items()} == dict.fromkeys(("gates", "timing", "train", "ladder", "evaluate", "baselines", "throughput"), "COMPLETE")
    run = Path(rec["run_dir"])
    name = "128/1K"
    dec = core.read_record(stages.ladder_path(run, name), "decision")
    assert dec["u0"] == 48 and dec["granted"] == 192 and dec["u_run"] in (48, 64, 96, 128, 192) and dec["rounds"][0]["point"] == 48
    # no per-arm early stop: every arm and replicate of the ladder cell trained to the same ladder point, the cell's U_run
    pl = planmod.Plan.load(Path(rec["plan"]))
    ladder_cells = [c for c in pl.data["cells"] if c["ladder_cell"]]
    trained = {c["label"]: read_json(run / "train" / "cells" / c["label"] / "cell_train.json")["trained_to"] for c in ladder_cells}
    assert set(trained.values()) == {dec["u_run"]} and len(trained) == 8
    # items beyond the stop are NOT REACHED: no snapshot above U_run exists for a ladder cell
    for c in ladder_cells:
        snaps = sorted(int(d.name[1:]) for d in (run / "train" / "cells" / c["label"] / "snapshots").iterdir())
        assert max(snaps) == dec["u_run"] and all(s <= dec["u_run"] for s in snaps)
    # a decision stays final and a re-run of the stage recomputes nothing
    before = (stages.ladder_path(run, name)).read_bytes()
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=Path(rec["plan"]).parent / "tiny_config.toml")
    import argparse

    again = stages.execute_stage("ladder", pl, ctx, run, Path(rec["plan"]), argparse.Namespace(freeze_commit=None, synthetic=True), repo=ROOT, inline=True)
    assert again["status"] == "COMPLETE" and (stages.ladder_path(run, name)).read_bytes() == before
    # timing: every (arm, slots) of the plan, single-thread CPU seconds per update
    tj = core.read_record(run / "timing" / "timing.json", "timing")
    assert set(tj["cpu"]) == {f"{c['arm']}|{c['slots']}" for c in pl.data["cells"]} and all(v > 0 for v in tj["cpu"].values())
    tp = core.read_record(run / "throughput" / "throughput.json", "throughput")
    assert set(tp["results"]) == {f"{i['arm']}|{i['facts']}|{i['slots']}" for i in pl.items("throughput")}  # exactly the plan's throughput items
    # every evaluated snapshot has both panels' DEP counts, and the F-OQ cells have the index read
    ev = core.read_record(ctx.eval_path(ladder_cells[0]["label"], 48), "eval")
    assert ev["reads"]["main"]["panels"]["A"]["disabled_correct"] is not None
    f4096 = next(c for c in pl.data["cells"] if c["arm"] == "F-OQ" and c["slots"] == 4096)
    assert set(core.read_record(ctx.eval_path(f4096["label"], 48), "eval")["reads"]) == {"main", "ivf"}
    assert stages.item_errors(run) == [] and stages.failed_cells(run) == []
    assert quiet_state(run) == "MEASURED"


def quiet_state(run: Path) -> str:
    from studies.p10is1 import quiet

    return quiet.throughput_label(run)


def test_training_refuses_without_gates_and_without_a_settled_timing_stage(tmp_path: Path) -> None:
    import argparse

    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    with pytest.raises(core.StageRefused, match="no gates record"):
        stages.execute_stage("train", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    stages.execute_stage("gates", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    with pytest.raises(core.StageRefused, match="training does not start"):
        stages.execute_stage("train", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)  # the timing stage is PAUSED: no record, no decision
    with pytest.raises(core.StageRefused, match="ladder stage has not decided"):
        (run / "timing").mkdir(parents=True, exist_ok=True)
        (run / "timing" / "timing.json").write_text("{}")
        stages.execute_stage("evaluate", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    # a not-quiet machine pauses the timing stage and records the attempt; nothing else is written
    run2 = root / "run2"
    ctx2 = items.Ctx(core.TEST, run2, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    noisy = {"quiet": False, "load_average": 2.0, "other_study_processes": []}
    clock = {"t": 0.0}

    def sleep(s: float) -> None:
        clock["t"] += s

    rec = stages.execute_stage("timing", pl, ctx2, run2, pl.path, args, repo=ROOT, inline=True, quiet_reading=lambda: noisy, sleep=sleep, clock=lambda: clock["t"])
    assert rec["status"] == "PAUSED" and not (run2 / "timing" / "timing.json").exists() and (run2 / "timing" / "attempts" / "01.json").is_file()
