# ruff: noqa: E501
"""P10IS0: the fixes of the re-audit (N1 resume after a kill, N2 Stage R hours in P, N3 opaque task labels, N4 disk cap over both directories, N5 the report reads nothing sealed and `disclose`, N6 the platform check)."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is0 import (  # noqa: E402
    accounting,
    adapter,
    core,
    drivers,
    items,
    ladder,
    report,
    runner,
    sealed,
)
from studies.p10is0.profile import TEST  # noqa: E402

CFG = core.load_config()

SEGMENT = """
import sys, torch
sys.path.insert(0, {repo!r})
torch.set_num_threads(1)
from pathlib import Path
from studies.p9i.train import training_stream_for
from studies.p10is0 import adapter, core, items
from studies.p10is0.profile import TEST
env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
data = items.data_for(env, core.test_set(1), 2048, core.load_config())
cell = core.Cell('TEST', 'S', 'A0', 128, 512, 1, 330098)
seg = adapter.run_segment(adapter.Job(cell, data, training_stream_for(data, 128), env.backbone, Path({out!r}), data.seeds.r1_codes, last_update={last}, snapshots=({last},), diag_early=64, diag_late=64, diag_switch=64))
"""


def run_script(out: Path, last: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen([sys.executable, "-c", SEGMENT.format(repo=str(REPO), out=str(out), last=last)], stderr=subprocess.DEVNULL)


def arithmetic(path: Path) -> list[dict[str, object]]:
    return [{k: v for k, v in json.loads(x).items() if k not in ("seconds", "rss_bytes")} for x in path.read_text().splitlines()]


# --- N1 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_a_killed_segment_resumes_and_matches_an_uninterrupted_run(tmp_path: Path) -> None:
    ref = tmp_path / "ref"
    assert run_script(ref, 1500).wait(timeout=600) == 0
    out = tmp_path / "out"
    p = run_script(out, 1500)
    log = out / "updates_00000000.jsonl"
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and not (log.is_file() and len(log.read_text().splitlines()) > 100):
        time.sleep(0.05)
    p.kill()  # mid-segment: the log exists, no train record, no snapshot yet
    p.wait(timeout=30)
    assert log.is_file() and not (out / "train_00000000.json").exists()
    assert run_script(out, 1500).wait(timeout=600) == 0  # the old code died here on FileExistsError, for ever
    moved = list((out / "incomplete").rglob("updates_00000000.jsonl"))
    assert len(moved) == 1 and moved[0].read_text()  # moved aside, never deleted
    assert arithmetic(log) == arithmetic(ref / "updates_00000000.jsonl")
    assert (out / "snapshots" / "u0001500" / "model.pt").read_bytes() == (ref / "snapshots" / "u0001500" / "model.pt").read_bytes() or file_sha256(out / "snapshots" / "u0001500" / "model.pt") == file_sha256(ref / "snapshots" / "u0001500" / "model.pt")


def test_a_completed_segment_is_not_set_aside(tmp_path: Path) -> None:
    (tmp_path / "train_00000000.json").write_text("{}")
    (tmp_path / "updates_00000000.jsonl").write_text("x")
    assert adapter.set_aside_incomplete(tmp_path, 0, [10]) == [] and (tmp_path / "updates_00000000.jsonl").exists()


# --- N2 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_extension_rule_counts_stage_rs_charged_hours(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    ctx.ledger.charge("stage_r_a0_base_i0", "r", 2.0 * 3600, group="stage_r_base_a0")  # what run_waves writes
    ctx.ledger.charge("stage_r_a1_base_i0", "r", 5.0 * 3600, group="stage_r_base_a1")
    assert drivers.stage_r_charged_hours(ctx, 0) == pytest.approx(2.0) and drivers.stage_r_charged_hours(ctx, 1) == pytest.approx(5.0)  # the old group name read 0.0
    cts = core.cell_types(CFG)
    r = ladder.Rates({(a, c.slots): 0.002 for c in core.cell_types(CFG, include_x8=True) for a in c.arms}, {(a, c.slots): 1.0 for c in core.cell_types(CFG, include_x8=True) for a in c.arms})
    cand = [core.cell_type_by_name("2K/4K", CFG)]
    kw = {"cts": cts, "t_known": {c.name: 2048 for c in cts if c not in cand}, "rates": r, "other_hours": 1.0, "x8": core.cell_type_by_name("8K/1K", CFG), "cfg": CFG}
    p0 = ladder.decide_extensions(cand, charged_hours=0.0, **kw)[0].projected_hours  # type: ignore[arg-type]
    p2 = ladder.decide_extensions(cand, charged_hours=drivers.stage_r_charged_hours(ctx, 0), **kw)[0].projected_hours  # type: ignore[arg-type]
    assert p2 - p0 == pytest.approx(2.0)  # P includes the two charged hours (hand-computed difference)


# --- N3 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_task_labels_are_opaque_and_the_map_is_sealed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    ct = core.cell_type_by_name("2K/512", CFG)
    seen: list[list[runner.Task]] = []

    def fake_run_stage(c: drivers.Ctx, stage: str, tasks: list[runner.Task], cap: float, **kw: object) -> dict[str, object]:
        seen.append(list(tasks))
        return {"status": "PAUSED"}

    monkeypatch.setattr(drivers, "run_stage", fake_run_stage)
    assert drivers.run_waves(ctx, [ct], phase="base", attempt=0, prefix="stage_r_a0", group="g", cap_seconds=1.0) == "PAUSED"
    names = [t.label for t in seen[0]]
    assert len(names) == 4 and len(set(names)) == 4
    for n in names:
        assert not any(w in n for w in ("2K", "512", "A5", "A6", "-c", "-e")) and n.startswith("t")
    for t in seen[0]:
        for f in (t.result_path, t.failed_path, t.log_path):
            assert not any(w in f.name for w in ("2K", "A6", "A5-D"))
    mp = sealed.sealed_dir(tmp_path / "store") / "taskmap-stage_r_a0_base_i0.json"
    rec = json.loads(mp.read_text())
    assert sorted(v[1] for v in rec["label_to_run"].values()) == ["A5-D", "A5-D", "A6", "A6"]
    assert drivers.opaque_label(tmp_path / "store", 0, ct.name, "A6", 1, 8) == drivers.opaque_label(tmp_path / "store", 0, ct.name, "A6", 1, 8)  # deterministic, so a resumed wave names its tasks the same
    assert not any(ct.name in p.read_text() for p in (tmp_path / "run").rglob("*.json"))  # nothing public carries the cell type


# --- N4 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_disk_cap_sums_the_run_directory_and_the_sealed_directory(tmp_path: Path) -> None:
    run, sd = tmp_path / "run", tmp_path / "sealed"
    run.mkdir()
    sd.mkdir()
    (run / "a").write_bytes(b"x" * 600)
    (sd / "b").write_bytes(b"x" * 600)
    cfg = {**CFG, "resources": {**CFG["resources"], "disk_cap_bytes": 1000, "disk_free_min_bytes": 1}}
    assert accounting.check_disk(run, cfg)["run_dir_bytes"] == 600  # the run directory alone is under the cap
    with pytest.raises(accounting.DiskPause):
        accounting.check_disk(run, cfg, also=[sd])  # together they are not


# --- N5 ----------------------------------------------------------------------------------------------------------------------------------------------
def make_repo(tmp: Path) -> Path:
    root = tmp / "repo"
    shutil.copytree(REPO / "configs", root / "configs")
    (root / core.DURATIONS).parent.mkdir(parents=True)
    write_json(root / core.DURATIONS, {"attempt": 0})
    return root


def test_report_reads_nothing_sealed_and_disclose_is_gated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_repo(tmp_path)
    ctx = drivers.Ctx(repo, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    types = {"8K/4K": {"labels": ["REFERENCE ALSO FAILS CONDITION 4 (A6 H-ratio {x} on calibration draws)"], "descriptive": {"convergence": {"status": "c", "tags": []}, "e512_readout": {"label": "l", "class": None}}}}
    a = {"headline": {"step": 3, "text": "t", "detail": {}}, "lines": {k: {"states": {"0.5": "HOLDS"}, "L": 0.5, "l1": None, "l1_state": None, "non_monotone": False} for k in "AGQ"}, "states_by_load_series": {}, "types": types,
         "annotations": {"penalty_vs_a0": {}, "hypotheses": {}, "licence_loads": []}, "x8": {"status": "s"}, "false_negative_table": []}
    monkeypatch.setattr(sealed, "read_sealed", lambda *x, **k: (_ for _ in ()).throw(AssertionError("the report read the sealed directory")))
    with pytest.raises(drivers.StageRefused, match="no analysis"):
        drivers.cmd_report(ctx)
    write_json(ctx.run_dir / "analysis.json", {**a, "status": "COMPLETE"})
    out = drivers.cmd_report(ctx)
    text = Path(out["report"]).read_text()
    assert "disclosed separately" in text and "{x}" not in text  # the label is printed; the value is not
    monkeypatch.undo()
    # disclose: refuses without a COMPLETE analysis record
    ctx2 = drivers.Ctx(repo, tmp_path / "run2", registered=False, sealed_dir=tmp_path / "store")
    with pytest.raises(drivers.StageRefused, match="no analysis record"):
        drivers.cmd_disclose(ctx2)
    write_json(ctx2.run_dir / "analysis.json", {**a, "status": "INCOMPLETE"})
    with pytest.raises(drivers.StageRefused, match="not COMPLETE"):
        drivers.cmd_disclose(ctx2)
    write_json(ctx2.run_dir / "analysis.json", {**a, "status": "COMPLETE"})
    monkeypatch.setattr(drivers, "load_plan_checked", lambda c: {"cell_types": {"8K/4K": {"t_exposures": 8}}})
    ct = core.cell_type_by_name("8K/4K", CFG)
    o = items.Obs((90, 100), (80, 100), (72, 100), (60, 100))
    sealed.write_sealed(tmp_path / "store", items.point_name(ct, "A6", 1, 0, 8), {"obs": items.obs_to_json(o), "exposures": 8})  # draw 2 has no point: A6 went non-finite
    res = drivers.cmd_disclose(ctx2)
    rec = json.loads((ctx2.run_dir / "disclosure.json").read_text())
    assert res["status"] == "COMPLETE" and rec["a6_h_ratio_x"]["8K/4K"]["calibration_draw_2"] == "missing"  # recorded as missing, not a crash
    assert rec["a6_h_ratio_x"]["8K/4K"]["calibration_draw_1"] == pytest.approx(0.60 / 0.90)  # condition 4's own (smallest per-panel) ratio
    assert "disclose-code" in (tmp_path / "store" / sealed.ACCESS_LOG).read_text()
    assert "A6 H-ratio 0.500 on calibration draws" in report.render({**a, "status": "COMPLETE"}, h_ratio={"8K/4K": [0.5]})  # the value reaches a report only from the post-outcome disclosure


# --- N6 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_platform_is_configured_before_it_is_checked_in_a_process_started_with_more_threads() -> None:
    env = {**os.environ, "OMP_NUM_THREADS": "8", "MKL_NUM_THREADS": "8", "VECLIB_MAXIMUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "8"}
    p = subprocess.run([sys.executable, "-m", "studies.p10is0.stages", "platform"], cwd=REPO, env=env, capture_output=True, text=True, timeout=120, check=False)
    assert p.returncode == 0, p.stderr[-300:]
    rec = json.loads(p.stdout.strip().splitlines()[-1])
    assert rec["torch_num_threads"] == 1 and rec["torch_interop_threads"] == 1 and rec["deterministic_algorithms"] is True and rec["system"] == "Darwin" and rec["machine"] == "arm64" and rec["torch"] == "2.8.0"


def test_registered_entry_configures_then_checks_then_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is0 import stages

    calls: list[str] = []
    monkeypatch.setattr(accounting, "configure_process", lambda: calls.append("configure"))
    monkeypatch.setattr(accounting, "check_platform", lambda cfg=None: calls.append("check") or {})
    args = stages.build_parser().parse_args(["registered", "main", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "0" * 40, "--repo", str(tmp_path)])
    shutil.copytree(REPO / "configs", tmp_path / "configs")
    assert stages.cmd_registered(args) == 2 and calls[:2] == ["configure", "check"]  # then the preconditions refuse (nothing is frozen)


def test_a_wrong_platform_is_refused_and_records_carry_the_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    accounting.configure_process()
    assert accounting.check_platform(CFG)["torch"] == "2.8.0"
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    with pytest.raises(accounting.PlatformMismatch, match="machine"):
        accounting.check_platform(CFG)
    monkeypatch.undo()
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False)
    d = tmp_path / "run" / "tasks" / "s"
    code = f"import pathlib; pathlib.Path({str(d / 't.result.json')!r}).parent.mkdir(parents=True, exist_ok=True); pathlib.Path({str(d / 't.result.json')!r}).write_text('{{}}')"
    t = runner.Task("t", (sys.executable, "-c", code), d / "t.result.json", d / "t.failed.json", d / "t.log")
    m = drivers.run_stage(ctx, "s", [t], 60.0, workers=1)
    assert m["identity"]["platform"]["torch_interop_threads"] == 1 and m["identity"]["platform"]["system"] == "Darwin"
    cell = core.Cell("TEST", "S", "A0", 128, 512, 1, 330098)
    env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    from studies.p9i.train import training_stream_for

    seg = adapter.run_segment(adapter.Job(cell, data, training_stream_for(data, 128), env.backbone, tmp_path / "o", data.seeds.r1_codes, last_update=2))
    assert seg.record["platform"]["deterministic_algorithms"] is True
