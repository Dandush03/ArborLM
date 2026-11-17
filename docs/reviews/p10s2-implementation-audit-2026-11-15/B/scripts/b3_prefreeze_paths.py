"""Audit B, check B3: pre-freeze paths on synthetic stand-ins and test seeds only.

B3a  rehearse.sh's argv (no --layer) through the real cmd_rehearse, in a throwaway clean git repo with a synthetic bundle (test seeds):
     does the driver reach the rehearsal, or fail on the missing layer?
B3b  calibration's 1,000-update snapshot when training runs on MPS: deep copy taken mid-training, then scored by the CPU context
     (the pattern of calibration.run_calibration), test-mode world.
B3c  index_put(accumulate=True) on CPU with deterministic algorithms off (evaluate) and on (recompute): bit-identical?
B3d  device 'auto' when MPS is reported unavailable: silent CPU?
Usage: python b3_prefreeze_paths.py <pin> <scratch-dir>
"""

import copy
import dataclasses
import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(PIN))
import torch  # noqa: E402

from studies.p10s2 import core, evaluate, stages, standins, train  # noqa: E402
from studies.p10s2.memory import MemoryArm, SparseStore  # noqa: E402
from studies.p10s2.worldio import write_bundle  # noqa: E402

res: dict[str, object] = {}
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a],
                          capture_output=True, text=True, check=True).stdout.strip()


# B3a -------------------------------------------------------------------------------------------------------------------------------------------
repo = OUT / "repo"
repo.mkdir()
(repo / "README").write_text("x\n")
(repo / ".gitignore").write_text("/run/\n")
git(repo, "init", "-q", "-b", "main")
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "c")
head = git(repo, "rev-parse", "HEAD")
core.reset_seed_record()
bundle, _pre = standins.build_synthetic_bundle(1)
write_bundle(bundle, repo / "run" / "data" / "bundle")
script_argv = (PIN / "studies/p10s2/launch/rehearse.sh").read_text().split("studies.p10s2.stages ", 1)[1].strip()
res["B3a_rehearse_sh_tail"] = script_argv
argv = ["rehearse", "--run-dir", str(repo / "run"), "--code-commit", head, "--stage-cap-seconds", "11520", "--data-dir", str(repo / "run" / "data" / "bundle"), "--updates", "200", "--full-updates", "2000", "--repo", str(repo)]
def _guard(*a, **k):  # never build a rehearsal-seed world in this audit (test seeds only)
    raise RuntimeError("AUDIT GUARD: build_world reached (the driver got past the layer argument); stopped before any rehearsal seed")


_bw = stages.build_world
stages.build_world = _guard  # type: ignore[assignment]
try:
    code = stages.main(argv)
    res["B3a_rehearse"] = {"exit": code}
except Exception as e:  # noqa: BLE001
    res["B3a_rehearse"] = {"exception": f"{type(e).__name__}: {e}", "where": traceback.format_exc().strip().splitlines()[-3:]}
stages.build_world = _bw  # type: ignore[assignment]
res["B3a_ledger_entries_written"] = (repo / "run" / "ledger.jsonl").exists()

# B3b -------------------------------------------------------------------------------------------------------------------------------------------
core.reset_seed_record()
world, _ = standins.build_synthetic_world(1, updates=4)
if torch.backends.mps.is_available():
    w = dataclasses.replace(world, device=torch.device("mps"))
    plan = w.plan(0)
    arm = MemoryArm(SparseStore.new(w.cfg.width, w.rows_per_stage, plan.gen(0, "stage-1 store (audit B3b)")), w.layer, w.codes(0))
    holder: dict[str, object] = {}

    def on_update(u: int) -> None:
        if u == 2:
            holder["snap"] = copy.deepcopy(arm)

    train.train_arm(w.student, arm, w.train_examples(0, "A"), 4, w.batch, w.store_lr, plan.gen(2, "batch order (audit B3b)"), w.marker_index, device=w.device, on_update=on_update)
    snap = holder["snap"]
    res["B3b_snapshot_device"] = str(snap.store.keys[0].device)  # type: ignore[attr-defined]
    res["B3b_final_arm_device"] = str(arm.store.keys[0].device)
    try:
        v = evaluate.score_panel(w.ctx, snap, w.d_cal["A"]).mean  # type: ignore[arg-type]
        res["B3b_score_snapshot"] = {"ok": True, "mean": v}
    except Exception as e:  # noqa: BLE001
        res["B3b_score_snapshot"] = {"ok": False, "exception": f"{type(e).__name__}: {str(e)[:300]}"}
else:
    res["B3b_score_snapshot"] = "MPS unavailable on this machine; not checked"

# B3c -------------------------------------------------------------------------------------------------------------------------------------------
g = torch.Generator().manual_seed(229777)
diffs = 0
for trial in range(200):
    vals = torch.randn(4000, 576, generator=g)
    bi = torch.randint(0, 8, (4000,), generator=g)
    pi = torch.randint(0, 20, (4000,), generator=g)
    torch.use_deterministic_algorithms(False)
    a = torch.zeros(8, 20, 576).index_put((bi, pi), vals, accumulate=True)
    torch.use_deterministic_algorithms(True)
    b = torch.zeros(8, 20, 576).index_put((bi, pi), vals, accumulate=True)
    torch.use_deterministic_algorithms(False)
    diffs += int(not torch.equal(a, b))
res["B3c_index_put_accumulate_cpu_det_off_vs_on_trials_differing"] = {"trials": 200, "differing": diffs, "threads": torch.get_num_threads()}
# thread count: same reduction at 1 and at the default threads
x = torch.randn(64, 4096, generator=g)
wmat = torch.randn(4096, 576, generator=g)
default_threads = torch.get_num_threads()
r_def = x @ wmat
torch.set_num_threads(1)
r_one = x @ wmat
torch.set_num_threads(default_threads)
res["B3c_matmul_bit_identical_1_thread_vs_default"] = {"default_threads": default_threads, "equal": bool(torch.equal(r_def, r_one)), "max_abs_diff": float((r_def - r_one).abs().max())}

# B3d -------------------------------------------------------------------------------------------------------------------------------------------
orig = torch.backends.mps.is_available
torch.backends.mps.is_available = lambda: False  # type: ignore[assignment]
try:
    res["B3d_auto_without_mps"] = str(train.select_device("auto"))
finally:
    torch.backends.mps.is_available = orig  # type: ignore[assignment]

print(json.dumps(core.jsonable(res), indent=1, default=str))
