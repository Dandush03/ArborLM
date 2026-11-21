# ruff: noqa: E501
"""P10IS0: the remainders of the re-audit (N1: a kill during the evaluation; N3: per-task figures of a Stage R wave stay sealed)."""

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from studies.p10is0 import adapter, core, drivers, items, runner, sealed  # noqa: E402
from studies.p10is0.profile import TEST  # noqa: E402

CFG = core.load_config()

EVAL_CHILD = """
import sys, time, torch, pathlib
sys.path.insert(0, {repo!r})
torch.set_num_threads(1)
from pathlib import Path
from studies.p10is0 import adapter, core, items
from studies.p10is0.profile import TEST
mode, base, flag, hang = sys.argv[1:5]
cfg = core.load_config()
env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
ct = core.cell_type_by_name('2K/512', cfg)
if hang == '1':
    real = adapter.evaluate_snapshot
    def slow(*a, **k):
        pathlib.Path(flag).write_text('evaluating')
        time.sleep(120)
        return real(*a, **k)
    adapter.evaluate_snapshot = slow
if mode == 'stage_r':
    lad = [TEST.exp(int(e)) for e in cfg['ladder']['base']]
    print(items.stage_r_run(ct, 'A5-D', 1, lad[0], Path(base), env, cfg, attempt=0, diag=(4, 8, 8), lad=lad))
else:
    cell = core.Cell('TEST', 'S', 'A0', 128, 512, 1, 330099)
    print(items.run_cell(cell, ct, 16, Path(base), env, cfg, spec=core.test_set(4, cfg), diag=(4, 8, 8))['status'])
"""


def eval_child(mode: str, base: Path, flag: Path, hang: bool) -> "subprocess.Popen[bytes]":
    return subprocess.Popen([sys.executable, "-c", EVAL_CHILD.format(repo=str(REPO)), mode, str(base), str(flag), "1" if hang else "0"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def kill_in_evaluation(mode: str, base: Path, flag: Path) -> None:
    p = eval_child(mode, base, flag, True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline and not flag.is_file():
        time.sleep(0.05)
    assert flag.is_file(), "the child never reached the evaluation"
    p.kill()
    p.wait(timeout=30)
    flag.unlink()


def outputs(base: Path) -> dict[str, bytes]:
    return {str(f.relative_to(base)): f.read_bytes() for f in sorted(base.rglob("*")) if f.is_file() and (f.name == "result.json" or f.name == "model.pt" or (f.parent.name == "sealed" and f.suffix == ".json"))}


@pytest.mark.parametrize("mode,kills", [("stage_r", 1), ("cell", 2)])
def test_a_kill_during_evaluation_resumes_to_the_uninterrupted_result(tmp_path: Path, mode: str, kills: int) -> None:
    ref, out = tmp_path / "ref", tmp_path / "out"
    assert eval_child(mode, ref, tmp_path / "f0", False).wait(timeout=600) == 0
    for _ in range(kills):
        kill_in_evaluation(mode, out, tmp_path / "flag")  # the old code: FileExistsError on the next resume (Stage R after one kill, a main cell after two)
    assert eval_child(mode, out, tmp_path / "f1", False).wait(timeout=600) == 0
    a, b = outputs(ref), outputs(out)
    assert a and a.keys() == b.keys() and all(a[k] == b[k] for k in a)  # byte-identical points, results and snapshots
    assert not list(out.rglob("incomplete"))  # nothing was killed mid-training, so nothing was set aside


def test_a_zero_progress_segment_opens_no_log_and_a_finished_segment_returns_its_record(tmp_path: Path) -> None:
    from studies.p9i.train import training_stream_for

    env = items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=TEST)
    data = items.data_for(env, core.test_set(1), 2048, CFG)
    cell = core.Cell("TEST", "S", "A0", 128, 512, 1, 330098)

    def job(**kw: object) -> adapter.Job:
        return adapter.Job(cell, data, training_stream_for(data, 128), env.backbone, tmp_path, data.seeds.r1_codes, last_update=4, **kw)  # type: ignore[arg-type]

    first = adapter.run_segment(job(snapshots=(4,)))
    again = adapter.run_segment(job(snapshots=(), init_snapshot=tmp_path / "snapshots" / "u0000004"))
    assert again.record["end_update"] == 4 and not (tmp_path / "updates_00000004.jsonl").exists()
    cached = adapter.run_segment(job(snapshots=(4,)))
    assert cached.model is None and cached.record["snapshot_sha256"] == first.record["snapshot_sha256"]


def test_stage_r_wave_manifest_publishes_only_count_total_and_maximum(tmp_path: Path) -> None:
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    d = tmp_path / "run" / "tasks" / "w"
    tasks = []
    for i, mib in enumerate((20, 80)):
        res = d / f"t{i}.result.json"
        code = f"import pathlib, time; x = bytearray({mib} * 2**20); time.sleep({0.3 * (i + 1)}); pathlib.Path({str(res)!r}).parent.mkdir(parents=True, exist_ok=True); pathlib.Path({str(res)!r}).write_text('{{}}')"
        tasks.append(runner.Task(f"t{i}", (sys.executable, "-c", code), res, d / f"t{i}.failed.json", d / f"t{i}.log"))
    m = drivers.run_stage(ctx, "stage_r_a0_base_i0", tasks, 60.0, workers=2, seal_task_stats=True)
    assert m["status"] == "COMPLETE" and m["wave"]["tasks"] == 2 and m["wave"]["max_peak_rss_bytes"] > 0 and m["wave"]["total_seconds"] > 0
    for v in m["tasks"].values():
        assert v == {"status": "completed", "seconds": 0.0, "peak_rss_bytes": 0}  # nothing per task that could split the cell types
    stats = list(sealed.sealed_dir(tmp_path / "store").glob("taskstats-*.json"))
    assert len(stats) == 1
    outcomes = json.loads(stats[0].read_text())["outcomes"]
    assert set(outcomes) == {"t0", "t1"} and all(o["peak_rss_bytes"] > 0 for o in outcomes.values())  # the per-task figures are in the sealed directory
    assert "not which" in sealed.WAVE_LIMIT_SENTENCE and m["wave"]["limit"] == sealed.WAVE_LIMIT_SENTENCE
