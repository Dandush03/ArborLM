# ruff: noqa: E501
"""P10IS0: the fixes of the implementation audit (blocking B1-B3, required R1-R17, the restructured Stage R). Each test fails on the behaviour the audit reported."""

import json
import os
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9i.train import training_stream_for  # noqa: E402
from studies.p10is0 import (  # noqa: E402
    accounting,
    adapter,
    core,
    drivers,
    gates,
    items,
    labels,
    ladder,
    report,
    runner,
    sealed,
)
from studies.p10is0.profile import TEST  # noqa: E402

torch.set_num_threads(1)
CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
LAD = [TEST.exp(int(e)) for e in CFG["ladder"]["base"]]  # 8 .. 256 tiny exposures


def tiny_env() -> items.Env:
    return items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)


def git_init(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)


# --- B1: the sealed directory ---------------------------------------------------------------------------------------------------------------------
def test_sealed_directory_is_refused_inside_a_working_tree_and_under_the_checkout(tmp_path: Path) -> None:
    repo = tmp_path / "wt"
    git_init(repo)
    assert any("working tree" in x for x in sealed.sealed_location_problems(repo / "sealed", repo))
    assert any("working tree" in x for x in sealed.sealed_location_problems(repo / "deep" / "er", repo))
    outside = tmp_path / "elsewhere" / "sealed"
    assert sealed.sealed_location_problems(outside, repo) == []
    link = tmp_path / "elsewhere" / "link"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(repo)  # symlinks are resolved
    assert sealed.sealed_location_problems(link / "inside", repo)
    assert any("under" in x for x in sealed.sealed_location_problems(REPO / "experiments" / "sealed_x", REPO))
    with pytest.raises(drivers.StageRefused, match="outside version control"):
        drivers.Ctx(REPO, tmp_path / "run", registered=False, sealed_dir=REPO / "experiments" / "_scratch" / "s")


def test_stage_r_writes_nothing_sensitive_outside_the_sealed_directory(tmp_path: Path) -> None:
    run_dir, sealed_base = tmp_path / "run", tmp_path / "store"
    ct = core.cell_type_by_name("2K/512", CFG)
    items.stage_r_cell_type(ct, sealed_base, tiny_env(), TH, CFG, ladder_values=LAD[:3], ceiling=LAD[2], diag=(4, 8, 8))
    run_dir.mkdir()
    sd = sealed.sealed_dir(sealed_base)
    assert list(sd.glob("cal/*/updates_*.jsonl")) and list(sd.glob("cal/*/diagnostics_*.jsonl")) and list(sd.glob("cal/*/snapshots/*/model.pt"))
    hashes = sealed.sealed_hashes(sealed_base)
    assert any(k.startswith("cal/") and k.endswith("updates_00000000.jsonl") for k in hashes) and any(k.endswith("model.pt") for k in hashes)  # hashed recursively
    for f in [*run_dir.rglob("*"), *tmp_path.glob("*.json")]:
        if f.is_file():
            assert "task_loss" not in f.read_text() and "distinct_top1" not in f.read_text()


# --- B2: a non-finite run does not silence the reference flags --------------------------------------------------------------------------------------
def test_nonfinite_run_lets_the_others_continue_to_the_base_ceiling_and_flags_are_computed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p9ii.train import Trainer

    real = Trainer.step

    def diverge(self: Trainer, batch: object) -> dict[str, object]:
        if self.arm == "A5-D" and self.job.cell.draw == 1 and self.update == 2:
            self.all_finite["loss"] = False
            raise ValueError("non-finite loss at update 3")
        return real(self, batch)  # type: ignore[arg-type]

    monkeypatch.setattr(Trainer, "step", diverge)
    ct = core.cell_type_by_name("2K/512", CFG)
    out = items.stage_r_cell_type(ct, tmp_path, tiny_env(), TH, CFG, diag=(4, 8, 8))
    d = out["decision"]
    base_t = TEST.exp(8192)
    assert d.status == ladder.STATUS_NONFINITE and d.t == base_t and d.label == labels.NON_FINITE_REHEARSAL
    cv = out["curves"]
    assert base_t in cv[("A5-D", 2)].points and base_t in cv[("A6", 1)].points and base_t in cv[("A6", 2)].points  # the other runs reached the base ceiling T
    assert out["computed"] is True and out["reference_flags"] is not None and out["reference_nonfinite"] is False
    entry = drivers.stage_r_entry({**drivers.res_of(items.read_state(ct, tmp_path, TH, CFG, TEST), ct, TH)}, extension="none", convergence=labels.NON_FINITE_REHEARSAL, t=base_t)
    assert entry["reference_flags_computed"] is True and labels.NON_FINITE_REHEARSAL in entry["labels"]


def test_a6_nonfinite_on_both_draws_is_recorded_not_silent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p9ii.train import Trainer

    real = Trainer.step

    def diverge(self: Trainer, batch: object) -> dict[str, object]:
        if self.arm == "A6" and self.update == 2:
            self.all_finite["gradients"] = False
            raise ValueError("non-finite gradient norm at update 3")
        return real(self, batch)  # type: ignore[arg-type]

    monkeypatch.setattr(Trainer, "step", diverge)
    ct = core.cell_type_by_name("2K/512", CFG)
    out = items.stage_r_cell_type(ct, tmp_path, tiny_env(), TH, CFG, diag=(4, 8, 8))
    assert out["computed"] is False and out["reference_nonfinite"] is True
    e = drivers.stage_r_entry(drivers.res_of(items.read_state(ct, tmp_path, TH, CFG, TEST), ct, TH), extension="none", convergence=labels.NON_FINITE_REHEARSAL)
    assert e["reference_flags_computed"] is False and "REFERENCE NON-FINITE IN REHEARSAL" in e["labels"] and e["removed"] is False  # stays in the plan, and says why no flag exists


# --- the restructured Stage R: runs as tasks, bit-identical to the sequential order ----------------------------------------------------------------
RUN_SCRIPT = """
import sys, torch
sys.path.insert(0, {repo!r})
torch.set_num_threads(1)
from pathlib import Path
from studies.p10is0 import adapter, core, items
from studies.p10is0.profile import TEST
cfg = core.load_config()
env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
ct = core.cell_type_by_name('2K/512', cfg)
lad = [TEST.exp(int(e)) for e in cfg['ladder']['base']]
items.stage_r_run(ct, {arm!r}, {draw}, {e}, Path({base!r}), env, cfg, attempt=0, diag=(4, 8, 8), lad=lad)
"""


def test_runs_as_parallel_tasks_are_bit_identical_to_the_sequential_order(tmp_path: Path) -> None:
    ct = core.cell_type_by_name("2K/512", CFG)
    seq, par = tmp_path / "seq", tmp_path / "par"
    items.stage_r_cell_type(ct, seq, tiny_env(), TH, CFG, ladder_values=LAD[:3], ceiling=LAD[2], diag=(4, 8, 8))
    for e in LAD[:3]:  # the driver's waves: every run of the round in its own process, at the same time
        procs = [subprocess.Popen([sys.executable, "-c", RUN_SCRIPT.format(repo=str(REPO), arm=a, draw=d, e=e, base=str(par))], stderr=subprocess.DEVNULL) for a, d in ladder.RUN_KEYS]
        assert [p.wait(timeout=300) for p in procs] == [0, 0, 0, 0]
    a, b = sealed.sealed_hashes(seq), sealed.sealed_hashes(par)
    pts = [k for k in a if k.endswith(".json") and "/" not in k]
    assert len(pts) == 12 and all(a[k] == b[k] for k in pts)  # every sealed point equal, byte for byte
    models = [k for k in a if k.endswith("model.pt")]
    assert models and all(a[k] == b[k] for k in models)  # and every snapshot (the state after each round)
    losses = [k for k in a if "updates_" in k]
    assert losses

    def arithmetic(base: Path, k: str) -> list[dict[str, object]]:  # every field of the per-update record except the two that measure the machine (wall seconds and resident memory)
        rows = [json.loads(x) for x in (sealed.sealed_dir(base) / k).read_text().splitlines()]
        return [{f: v for f, v in r.items() if f not in ("seconds", "rss_bytes")} for r in rows]

    assert all(arithmetic(seq, k) == arithmetic(par, k) for k in losses)  # and every per-update loss, gradient norm and parameter change


def test_the_driver_makes_one_task_per_run_and_the_time_is_set_by_the_longest_runs() -> None:
    st = items.RState(ladder.Decision(ladder.STATUS_UNDECIDED), {k: ladder.Curve(*k) for k in ladder.RUN_KEYS}, {})
    needs = items.stage_r_needs(st, LAD, TEST, CFG)
    assert sorted(needs) == [("A5-D", 1, LAD[0]), ("A5-D", 2, LAD[0]), ("A6", 1, LAD[0]), ("A6", 2, LAD[0])]  # four tasks, not one
    cts = core.cell_types(CFG)
    flat = ladder.Rates({(a, ct.slots): 0.01 for ct in core.cell_types(CFG) for a in ct.arms}, {(a, ct.slots): 0.0 for ct in core.cell_types(CFG) for a in ct.arms})
    wall = ladder.stage_r_makespan_hours(cts, flat, 6, [512, 1024, 2048, 4096, 8192, 16384])
    sequential_sum = sum(0.01 * ct.updates(16384) for ct in cts for _ in range(4)) / 6 / 3600  # all work spread perfectly
    longest_run = max(0.01 * ct.updates(16384) for ct in cts) / 3600
    assert wall >= longest_run and wall >= sequential_sum
    per_type_sequential = max(0.01 * ct.updates(16384) * 4 for ct in cts) / 3600  # the old driver: four runs one after the other in one task
    assert wall < per_type_sequential * 0.95


def test_nothing_per_cell_type_is_a_task_result() -> None:
    names = ("CANDIDATE", "SHOWN", "NON_FINITE", "e_star")
    src = (REPO / "studies/p10is0/drivers.py").read_text()
    worker = src[src.index("def worker_main"):]
    assert not any(f'"{n}"' in worker for n in names)  # the worker returns only {"ok": True} for a Stage R run (B3)


# --- R1, R2, R3: projections and caps ---------------------------------------------------------------------------------------------------------------
def test_x8_extension_projection_is_charged_plus_its_remaining_only() -> None:
    ct = core.cell_type_by_name("8K/1K", CFG)
    r = ladder.Rates({(a, 1024): 0.01 for a in ct.arms}, {(a, 1024): 10.0 for a in ct.arms})
    rnd = 4 * (0.01 * ct.updates(16384) + 10.0)  # four runs from the base ceiling to twice it, one evaluation each
    task_cell = 3 * (0.01 * ct.updates(16384) + 30.0)  # a task is one (cell type, draw): its three arms
    longest_task = 0.01 * ct.updates(16384) + 10.0
    want = 20.0 + ((rnd + 10 * task_cell) / 6 + longest_task + task_cell) / 3600
    got = ladder.x8_extension_projection(ct, r, 20.0, 6, 16384, 16384)
    assert got == pytest.approx(want, rel=1e-9)
    # no double counting: the main grid and X8's base calibration are in the 20 charged hours and nowhere else
    assert ladder.x8_extension_projection(ct, r, 0.0, 6, 16384, 16384) == pytest.approx(want - 20.0, rel=1e-9)
    assert ladder.decide_x8_extension(ct, r, 20.0, CFG).projected_hours == pytest.approx(want, rel=1e-9)


def test_caps_x8_has_its_own_stage_and_total_includes_charged_hours() -> None:
    cts = core.cell_types(CFG)
    x8 = core.cell_type_by_name("8K/1K", CFG)
    r = ladder.Rates({(a, c.slots): 0.01 for c in core.cell_types(CFG, include_x8=True) for a in c.arms}, {(a, c.slots): 1.0 for c in core.cell_types(CFG, include_x8=True) for a in c.arms})
    _, stages = ladder.projected_hours(cts=cts, t_assumed={c.name: 1024 for c in cts}, granted_rounds=[], rates=r, charged_hours=0.0, other_hours=0.0, x8=x8, workers=6, ladder_top=0, x8_t=16384)
    names = [s.name for s in stages]
    assert names.count("main") == 1 and "x8" in names and any(n.startswith("calibration") for n in names)
    by = {s.name: s for s in stages}
    assert by["x8"].total_seconds != by["main"].total_seconds  # R2: the X8 cap is its own stage's, not the main grid's


def test_stage_cap_is_cumulative_over_resumes(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False, total_hours=3.0 / 3600)  # total cap: 3 s
    d = tmp_path / "run" / "tasks" / "s"

    def tk(n: int) -> runner.Task:
        code = f"import time, pathlib; time.sleep(2); pathlib.Path({str(d / f't{n}.result.json')!r}).parent.mkdir(parents=True, exist_ok=True); pathlib.Path({str(d / f't{n}.result.json')!r}).write_text('{{}}')"
        return runner.Task(f"t{n}", (sys.executable, "-c", code), d / f"t{n}.result.json", d / f"t{n}.failed.json", d / f"t{n}.log")

    m1 = drivers.run_stage(ctx, "s1", [tk(1), tk(2)], cap_seconds=3.0, workers=1, group="g")
    assert m1["status"] == "PAUSED"  # the cap of 3 s stops the second 2-s task
    m2 = drivers.run_stage(ctx, "s1", [tk(1), tk(2)], cap_seconds=3.0, workers=1, group="g")
    assert ctx.ledger.charged() < 4.5  # a resume gets what was left, not a fresh cap (the old driver charged 4.2 s against a 3 s total)
    m3 = drivers.run_stage(ctx, "s1", [tk(1), tk(2)], cap_seconds=3.0, workers=1, group="g")
    assert m3["status"] == "PAUSED" and "spent" in str(m3.get("reason", "spent")) and m2["status"] in ("PAUSED", "COMPLETE")


# --- R4, R5: pauses and engineering stops ----------------------------------------------------------------------------------------------------------------
def test_worker_maps_conditions_to_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = ["generate", "--run-dir", str(tmp_path / "run"), "--repo", str(REPO), "--result", str(tmp_path / "r.json"), "--set", "p10is0-draw-1"]
    for exc, want in ((OSError(28, "no space"), runner.ENV_EXIT), (FileNotFoundError("x"), runner.ENV_EXIT), (drivers.CodeChanged("x"), runner.CODE_EXIT), (drivers.StageRefused("x"), drivers.IDENTITY_EXIT), (accounting.DiskPause("full"), runner.ENV_EXIT)):
        monkeypatch.setattr(drivers, "work_generate", lambda ctx, s, e=exc: (_ for _ in ()).throw(e))
        assert drivers.worker_main(args) == want
    assert not (tmp_path / "r.json").exists()


def test_exit_four_is_an_engineering_stop_without_a_failed_record(tmp_path: Path) -> None:
    d = tmp_path / "t"
    t = runner.Task("stop", (sys.executable, "-c", f"raise SystemExit({runner.CODE_EXIT})"), d / "a.result.json", d / "a.failed.json", d / "a.log")
    out, _ = runner.run_tasks([t], workers=1, cap_seconds=30, rss_worker_bytes=2**33, rss_aggregate_bytes=2**34, poll=0.05)
    assert out["stop"]["status"] == runner.ENGINEERING_STOP and not t.failed_path.exists() and runner.stage_status(out) == "ENGINEERING STOP"
    again, _ = runner.run_tasks([t], workers=1, cap_seconds=30, rss_worker_bytes=2**33, rss_aggregate_bytes=2**34, poll=0.05)
    assert again["stop"]["status"] == runner.ENGINEERING_STOP  # it can be re-run once the human lead rules (no failed record blocks it)


def test_disk_rule_pauses_between_tasks(tmp_path: Path) -> None:
    d = tmp_path / "t"
    tasks = [runner.Task(f"s{i}", (sys.executable, "-c", "import time; time.sleep(30)"), d / f"{i}.r.json", d / f"{i}.f.json", d / f"{i}.log") for i in range(2)]

    def full() -> None:
        raise accounting.DiskPause("run directory at 110 GiB")

    out, _ = runner.run_tasks(tasks, workers=1, cap_seconds=60, rss_worker_bytes=2**33, rss_aggregate_bytes=2**34, poll=0.05, disk_check=full)
    assert {o["status"] for o in out.values()} <= {runner.NOT_STARTED, runner.PAUSED_ENVIRONMENT} and not list(d.glob("*.f.json"))
    assert runner.stage_status(out) == "PAUSED"


def test_free_space_check_in_the_training_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(accounting, "check_free", lambda path, cfg=None, free=None: (_ for _ in ()).throw(accounting.DiskPause("free space")))
    ct = core.cell_type_by_name("2K/512", CFG)
    cell = core.Cell("TEST", "S", "A0", 128, 512, 1, 330098)
    env = tiny_env()
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    with pytest.raises(accounting.DiskPause):
        adapter.run_segment(adapter.Job(cell, data, training_stream_for(data, 128), env.backbone, tmp_path / "o", data.seeds.r1_codes, last_update=1024))
    del ct


# --- R6: the memory rule ---------------------------------------------------------------------------------------------------------------------------------
def test_workers_follow_the_largest_measured_peak(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    gib = 2**30
    assert ctx.workers() == 6
    ctx.record_peak("stage_r_base", int(2.5 * gib))
    assert ctx.workers() == 3  # Stage R's 2T runs set it: floor(9 / 2.5)
    ctx.record_peak("a0_memory", 3 * gib)
    assert ctx.workers() == 3
    ctx.record_peak("a0_memory", 4 * gib)
    with pytest.raises(ladder.EngineeringStop):
        ctx.workers()


# --- R7: item errors of X8's calibration -----------------------------------------------------------------------------------------------------------------
def test_item_errors_of_x8_calibration_are_collected(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    bad = {"t": {"status": runner.FAILED, "seconds": 1.0, "peak_rss_bytes": 0}}
    runner.write_manifest(ctx.run_dir, "x8_cal_a0_base_i0", "test", bad, 1.0, identity={}, started="t", caps={})
    names = drivers.x8_stage_names(ctx)
    assert names == ["x8_cal_a0_base_i0"] and drivers.item_errors_of(ctx, ("main", "x8", *names)) == ["x8_cal_a0_base_i0:t"]


# --- R8: a code change voids Stage R; a repeat is a new attempt on the spare draws -----------------------------------------------------------------------
def test_repeat_attempts_use_the_spare_values_and_keep_the_voided_results(tmp_path: Path) -> None:
    ct = core.cell_type_by_name("2K/512", CFG)
    env = tiny_env()
    base = tmp_path / "s"
    items.stage_r_run(ct, "A6", 1, LAD[0], base, env, CFG, attempt=0, diag=(4, 8, 8), lad=LAD)
    items.stage_r_run(ct, "A6", 1, LAD[0], base, env, CFG, attempt=1, diag=(4, 8, 8), lad=LAD)
    a0, a1 = items.point_name(ct, "A6", 1, 0, LAD[0]), items.point_name(ct, "A6", 1, 1, LAD[0])
    assert a0 != a1 and (sealed.sealed_dir(base) / a0).is_file() and (sealed.sealed_dir(base) / a1).is_file()
    assert core.calibration_set(1, 1, CFG, "registered").base == 309401 and core.init_seed("CAL", "A6", 1, 1, CFG) == 330061 and core.init_seed("CAL", "A6", 2, 3, CFG) == 330066
    assert [i.label for i in (items.cal_cell(ct, "A6", 1, 0, CFG, TEST), items.cal_cell(ct, "A6", 1, 1, CFG, TEST))][0] != items.cal_cell(ct, "A6", 1, 1, CFG, TEST).label
    # the attempt's state never reads another attempt's points
    s0, s1 = items.read_state(ct, base, TH, CFG, TEST, attempt=0, lad=LAD, ceiling=LAD[-1]), items.read_state(ct, base, TH, CFG, TEST, attempt=2, lad=LAD, ceiling=LAD[-1])
    assert s0.obs_at and not s1.obs_at


def test_code_change_before_durations_starts_the_next_attempt_and_a_fourth_is_refused(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(REPO / "studies", repo / "studies", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "freeze"))
    shutil.copytree(REPO / "configs", repo / "configs")
    (repo / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cause = tmp_path / "results" / "cause.md"
    cause.parent.mkdir()
    cause.write_text("cause\n")
    assert drivers.record_code_identity(run_dir, repo)["attempt"] == 0 and drivers.current_attempt(run_dir) == 0
    for k in (1, 2, 3):
        f = repo / "studies/p10is0/core.py"
        f.write_text(f.read_text() + f"\n# change {k}\n")
        assert drivers.record_code_identity(run_dir, repo, cause_file=cause)["attempt"] == k
    f.write_text(f.read_text() + "\n# change 4\n")
    with pytest.raises(drivers.CodeChanged, match="fourth repeat"):
        drivers.record_code_identity(run_dir, repo, cause_file=cause)


# --- R9: the part (b) reference has its own forward --------------------------------------------------------------------------------------------------------
def test_part_b_reference_does_not_use_the_models_forward() -> None:
    cell = core.Cell("TEST", "S", "A5-D", 128, 512, 1, 330098)
    env = tiny_env()
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    stream = training_stream_for(data, 128)
    model = adapter.build_model(cell, env.backbone, data.seeds.r1_codes)

    def boom(*a: object, **k: object) -> None:
        raise AssertionError("the model's own forward was called")

    model.forward = boom  # type: ignore[method-assign]
    model.addition.forward = boom  # type: ignore[method-assign]
    model.train()
    out = gates.reference_update(model, stream.batch(1).tokens, "A5-D")
    assert out["answer_loss"] > 0 and out["diversity_loss"] is not None


# --- R10: the checker verifies the twelve spare values -------------------------------------------------------------------------------------------------------
def test_checker_copy_counts_the_twelve_named_values() -> None:
    from studies.p10is0 import seeds

    src = (REPO / CFG["seed_ranges"]["checker"]).read_text()
    copy = seeds.checker_copy(src, REPO)
    counts = {}
    for name, text in (("orig", src.replace("ROOT = Path(__file__).resolve().parents[3]", f"ROOT = Path({str(REPO)!r})")), ("copy", copy)):
        f = REPO / "experiments" / "_scratch" / f"checker_{name}.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        p = subprocess.run([sys.executable, str(f)], cwd=REPO, capture_output=True, text=True, timeout=900, check=False)
        counts[name] = [x for x in p.stdout.splitlines() if x.startswith(("named values checked", "RESULT"))]
        f.unlink()
    assert counts["copy"][-1] == "RESULT: PASS"
    import re

    o = [int(x) for x in re.findall(r"(\d+) initialization, (\d+) data", counts["orig"][0])[0]]
    c = [int(x) for x in re.findall(r"(\d+) initialization, (\d+) data", counts["copy"][0])[0]]
    assert c == [o[0] + 6, o[1] + 6]  # the checker itself now checks six more initialisation values and six more data sets


# --- R11, R12: labels --------------------------------------------------------------------------------------------------------------------------------------
def test_h23_g_is_read_at_step_two_and_the_seen_by_the_lead_label_prints() -> None:
    g_fail = labels.TypeState(labels.HOLDS, labels.FAILS, labels.FAILS, 7)
    ok = labels.TypeState(labels.HOLDS, labels.HOLDS, labels.HOLDS, 5)
    c = labels.Convergence(labels.CONFIRMED, (), {})
    loads = {0.5: [labels.SeriesAtLoad("M", g_fail, c, "m"), labels.SeriesAtLoad("S", ok, c, "s")], 1.0: [labels.SeriesAtLoad("M", ok, c, "m"), labels.SeriesAtLoad("S", ok, c, "s")]}
    h = labels.decide(loads=loads, th=TH)
    assert h.step == 2
    assert labels.hypotheses(h, {"M": g_fail}, None, labels.FAILS)["H23-G"] == "supported"  # the old code returned "not read" at step 2
    names = [c.name for c in core.cell_types(CFG)]
    assert sealed.disclosed_cell_types({"seal_broken": True}, names) == set(names)
    assert sealed.disclosed_cell_types({"disclosed_reads": ["8K-4K-A6-c1-r0-e8.json"]}, names) == {"8K/4K"}
    assert sealed.disclosed_cell_types(None, names) == set()


# --- R13 ------------------------------------------------------------------------------------------------------------------------------------------------------
def test_another_studys_process_is_seen_even_if_it_is_a_test_suite() -> None:
    marker = "studies.p10s1.fake_marker"
    subprocess.run(["sh", "-c", f"{sys.executable} -c 'import time; time.sleep(20)  # {marker} pytest' >/dev/null 2>&1 &"], check=True)
    deadline = time.monotonic() + 10
    found: list[dict[str, object]] = []
    while time.monotonic() < deadline and not found:
        found = [p for p in accounting.other_study_processes() if marker in str(p["command"])]
        time.sleep(0.2)
    for p in found:
        os.kill(int(str(p["pid"])), 9)
    assert found  # the old code skipped every command containing "pytest"
    assert accounting.other_study_processes(exclude_pids=[os.getpid()]) is not None


# --- R14: the memory test can fail ------------------------------------------------------------------------------------------------------------------------------
def _traced_peak(tmp: Path, updates: int, tag: str) -> int:
    cell = core.Cell("TEST", "S", "A0", 128, 512, 1, 330098)
    env = tiny_env()
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    stream = training_stream_for(data, 128)
    tracemalloc.start()
    try:
        adapter.run_segment(adapter.Job(cell, data, stream, env.backbone, tmp / tag, data.seeds.r1_codes, last_update=updates, diag_early=512, diag_late=512, diag_switch=512))
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_retained_memory_is_constant_and_the_test_detects_a_keeping_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    small, large = _traced_peak(tmp_path, 256, "a"), _traced_peak(tmp_path, 2048, "b")
    assert large - small < 0.5 * 2**20, (small, large)  # the streamed loop holds nothing per update
    kept: list[str] = []
    real = adapter.s0core.json_line
    monkeypatch.setattr(adapter.s0core, "json_line", lambda rec: kept.append(real(rec)) or kept[-1])  # the defect: records kept in memory, as P10-S0's loop does
    small_k, large_k = _traced_peak(tmp_path, 256, "c"), _traced_peak(tmp_path, 2048, "d")
    assert large_k - small_k >= 0.5 * 2**20, (small_k, large_k)  # the same bound fails on the keeping loop


# --- R15: the report prints what section 7 requires ---------------------------------------------------------------------------------------------------------
def test_report_prints_section_7(tmp_path: Path) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from test_p10is0_analysis import (  # type: ignore[import-not-found]
        durations,
        fails,
        obs,
        rec,
        registry,
        run,
    )

    bad = fails("8K/4K", "A5-D", range(1, 4), rec(obs(0.5)))
    out = run(registry(bad), durations(**{"8K_4K": {"reference_flags": {"cond4": True, "other": []}}}))
    text = report.render(out, h_ratio={"8K/4K": [0.81, 0.79]})
    for needle in ("which line fails at l1", "one-sided 95% per-draw bound", "at L_Q", "at l1", "REFERENCE NEAR CEILING", "CONVERGENCE CONFIRMED", "A6 H-ratio 0.810, 0.790 on calibration draws", "RATIO ABOVE 1 is this study's"):
        assert needle in text, needle
    assert "H-ratio x on" not in text and "LINE A" in text


# --- R16: the inputs of P --------------------------------------------------------------------------------------------------------------------------------------
def test_other_hours_count_generation_gates_and_the_report_allowance(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    ctx.ledger.charge("generate", "g", 3600.0)
    ctx.ledger.charge("gates", "x", 1800.0)
    ctx.ledger.charge("timing-quiet", "t", 7200.0)  # stage 3 is not one of P's added stages
    assert drivers.other_hours_of(ctx) == pytest.approx(1.5 + float(CFG["budget"]["analysis_report_hours"]))


# --- R17 -------------------------------------------------------------------------------------------------------------------------------------------------------
def test_data_manifests_are_frozen_inputs(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    ct = core.cell_type_by_name("2K/512", CFG)
    name = "p10is0-draw-1"
    path = drivers.draw_manifest_path(ctx.run_dir, name)
    core.write_record(path, {**core.envelope("data_manifest"), "seed_set": name, "sha256s": {"2048": {"x": "y"}}, "g1_passed": True})

    class D:
        def sha256s(self) -> dict[str, str]:
            return {"x": "y"}

    from arborlm.io import file_sha256

    drivers.verify_manifest(ctx, {"draw_manifests": {name: file_sha256(path)}}, name, ct, D())
    with pytest.raises(drivers.IdentityMismatch, match="SHA-256 the plan names"):
        drivers.verify_manifest(ctx, {"draw_manifests": {name: "0" * 64}}, name, ct, D())
    with pytest.raises(drivers.IdentityMismatch):
        drivers.verify_manifest(ctx, {"draw_manifests": {}}, name, ct, D())
