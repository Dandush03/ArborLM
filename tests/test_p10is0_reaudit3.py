# ruff: noqa: E501
"""P10IS0: D1 (no per-task Stage R file in the public run directory) and D2 (a finished segment's record must be this run's own)."""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from studies.p9i.train import training_stream_for  # noqa: E402
from studies.p10is0 import adapter, core, drivers, items, sealed  # noqa: E402
from studies.p10is0.plan import IdentityMismatch  # noqa: E402
from studies.p10is0.profile import TEST  # noqa: E402

CFG = core.load_config()


def test_stage_r_task_files_are_sealed_and_the_public_directory_has_no_mid_wave_file(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    tasks = []
    for i, secs in enumerate((0.5, 2.5)):  # clearly different durations
        t = ctx.task("stage_r_a0_base_i0", f"t{i}", "stage-r-run", sealed_tasks=True)
        code = f"import pathlib, time; time.sleep({secs}); pathlib.Path({str(t.result_path)!r}).parent.mkdir(parents=True, exist_ok=True); pathlib.Path({str(t.result_path)!r}).write_text('{{}}')"
        tasks.append(type(t)(t.label, (sys.executable, "-c", code), t.result_path, t.failed_path, t.log_path))
        assert sealed.sealed_dir(tmp_path / "store") in t.result_path.parents and sealed.sealed_dir(tmp_path / "store") in t.log_path.parents  # D1
    start = time.time()
    m = drivers.run_stage(ctx, "stage_r_a0_base_i0", tasks, 60.0, workers=2, seal_task_stats=True)
    end = time.time()
    assert m["status"] == "COMPLETE"
    public = [f for f in (tmp_path / "run").rglob("*") if f.is_file()]
    assert public and not [f for f in public if "tasks" in f.relative_to(tmp_path / "run").parts]  # no per-task file at all
    mid = [f.name for f in public if start + 0.3 < f.stat().st_mtime < end - 0.3]
    assert mid == []  # nothing public was written between the start and the end of the wave except at its end (the old logs and results were)
    manifest = tmp_path / "run" / "stage_r_a0_base_i0" / "manifest.json"
    assert manifest.is_file() and manifest.stat().st_mtime >= end - 0.3
    sealed_tasks = [f for f in (sealed.sealed_dir(tmp_path / "store") / "tasks").rglob("*") if f.is_file()]
    assert len(sealed_tasks) >= 4  # the logs and results of both tasks are in the sealed directory


def _segment(tmp: Path, label_seed: int = 330098, arm: str = "A0", last: int = 4, **kw: object) -> tuple[adapter.Job, adapter.Segment]:
    env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    cell = core.Cell("TEST", "S", arm, 128, 512, 1, label_seed)
    job = adapter.Job(cell, data, training_stream_for(data, 128), env.backbone, tmp, data.seeds.r1_codes, last_update=last, snapshots=(last,), **kw)  # type: ignore[arg-type]
    return job, adapter.run_segment(job)


def rewrite(path: Path, **changes: object) -> None:
    rec = json.loads(path.read_text())
    rec.update(changes)
    path.write_text(json.dumps(rec))


def test_a_planted_foreign_train_record_is_an_identity_pause(tmp_path: Path) -> None:
    job, _ = _segment(tmp_path)
    rec = tmp_path / "train_00000000.json"
    assert adapter.run_segment(job).record["end_update"] == 4  # its own record is accepted
    for change in ({"label": "CAL-M-A6-8K-16K-d01-i330099"}, {"start_update": 3}, {"planned_last_update": 10**6, "end_update": 10**6}):
        original = rec.read_text()
        rewrite(rec, **change)
        with pytest.raises(IdentityMismatch, match="not this run's own"):
            adapter.run_segment(job)  # the old code accepted it and paused for ever on a missing snapshot
        rec.write_text(original)
    rewrite(rec, snapshot_sha256={"4": "0" * 64})
    with pytest.raises(IdentityMismatch, match="snapshot 4"):
        adapter.run_segment(job)


def test_run_cell_refuses_another_runs_train_record(tmp_path: Path) -> None:
    env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
    ct = core.cell_type_by_name("2K/512", CFG)
    cell = core.Cell("TEST", "S", "A0", 128, 512, 1, 330099)
    items.run_cell(cell, ct, 16, tmp_path, env, CFG, spec=core.test_set(4, CFG), diag=(4, 8, 8))
    out = items.cell_dir(tmp_path, cell.label)
    (out / "result.json").unlink()
    rewrite(out / "train_00000000.json", label="TEST-S-A6-2K-512-d01-i330099")
    with pytest.raises(IdentityMismatch, match="belongs to"):
        items.run_cell(cell, ct, 16, tmp_path, env, CFG, spec=core.test_set(4, CFG), diag=(4, 8, 8))
