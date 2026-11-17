"""Re-check B, R2: device, memory and snapshot paths, on synthetic stand-ins and test seeds only (no calibration, rehearsal or registered seed is drawn).

B1   calibration's mid-training snapshot when the arm trains on MPS: before (copy.deepcopy, the old code) and after (calibration.cpu_snapshot), scored by the CPU context;
     and run_calibration end to end on MPS on a test-mode stand-in world (the module's CAL patched IN THIS PROCESS ONLY to the stand-in student's layers [0, 1] and 4 updates, snapshot at 2).
M6   train.process_memory_bytes sees a 1 GiB MPS tensor; a StageGuard with a limit below the sampled memory stops the block (MemoryLimitExceeded).
M8   select_device: "auto" refused; MPS reported unavailable -> refused; PYTORCH_ENABLE_MPS_FALLBACK set -> refused. G4 with require_mps on a CPU world fails.
f    state leaks: threads and deterministic flags around scoring_environment, stage_timing and train_arm on MPS.
Usage: PYTHONPATH=<pin>/src python r2_device_memory.py <pin> <out.json>
"""

import copy
import dataclasses
import json
import os
import sys
import time
import traceback
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
import torch  # noqa: E402

from studies.p10s2 import calibration, core, evaluate, gates, stages, standins, train  # noqa: E402
from studies.p10s2.memory import MemoryArm, SparseStore  # noqa: E402

res: dict[str, object] = {"torch": torch.__version__, "mps_available": bool(torch.backends.mps.is_available())}
GIB = 2**30


def tb(e: BaseException) -> str:
    return f"{type(e).__name__}: {str(e)[:300]}"


core.reset_seed_record()
world, _ = standins.build_synthetic_world(1, updates=4)
mps = torch.backends.mps.is_available()

# --- B1 -------------------------------------------------------------------------------------------------------------------------------------------
if mps:
    w = dataclasses.replace(world, device=torch.device("mps"))
    plan = w.plan(0)
    for name, snapfn in (("before: copy.deepcopy", copy.deepcopy), ("after: calibration.cpu_snapshot", calibration.cpu_snapshot)):
        arm = MemoryArm(SparseStore.new(w.cfg.width, w.rows_per_stage, plan.gen(0, f"stage-1 store (recheck B1 {name})")), w.layer, w.codes(0))
        holder: dict[str, object] = {}

        def on_update(u: int, arm=arm, holder=holder, snapfn=snapfn) -> None:  # noqa: ANN001
            if u == 2:
                holder["snap"] = snapfn(arm)

        rec = train.train_arm(w.student, arm, w.train_examples(0, "A"), 4, w.batch, w.store_lr, plan.gen(2, f"batch order (recheck B1 {name})"), w.marker_index, device=w.device, on_update=on_update)
        snap = holder["snap"]
        out: dict[str, object] = {"train_status": rec.status, "train_device": rec.device, "snapshot_device": str(snap.store.keys[0].device)}  # type: ignore[attr-defined]
        try:
            out["score"] = evaluate.score_panel(w.ctx, snap, w.d_cal["A"]).mean  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            out["score_error"] = tb(e)
        res[f"B1 {name}"] = out
    # run_calibration end to end on MPS, stand-in layers patched in this process only
    cal_saved = calibration.CAL
    calibration.CAL = {**cal_saved, "read_layers": [0, 1], "updates": 4}
    try:
        t0 = time.perf_counter()
        rc = calibration.run_calibration(w, 0, updates=4, snapshot_updates=2)
        res["B1 run_calibration on MPS (stand-in, layers [0,1], 4 updates, snapshot 2)"] = {"ok": True, "device": rc["device"], "has_selection_at_snapshot": "selection_at_snapshot" in rc, "snapshot_scores_finite": all(v == v for v in rc["snapshot_scores"].values()), "seconds": time.perf_counter() - t0}
    except Exception as e:  # noqa: BLE001
        res["B1 run_calibration on MPS"] = {"ok": False, "error": tb(e), "where": traceback.format_exc().splitlines()[-4:]}
    finally:
        calibration.CAL = cal_saved
else:
    res["B1"] = "MPS unavailable: not checked"

# --- M6 -------------------------------------------------------------------------------------------------------------------------------------------
if mps:
    before = train.process_memory_bytes()
    saved_flag = train.MPS_IN_USE
    train.MPS_IN_USE = True
    x = torch.empty(GIB // 4, dtype=torch.float32, device="mps").fill_(1.0)  # 1 GiB
    torch.mps.synchronize()
    after = train.process_memory_bytes()
    res["M6 process_memory_bytes with a 1 GiB MPS tensor"] = {"before": before, "after": after, "max_rose_gib": (after["max"] - before["max"]) / GIB, "rss_rose_gib": (after["rss_peak"] - before["rss_peak"]) / GIB}
    limit = int(after["max"] - GIB // 2)
    t0 = time.perf_counter()
    try:
        with stages.StageGuard("recheck-mem", memory_limit_bytes=limit, interval=0.1):
            while time.perf_counter() - t0 < 5.0:
                sum(range(1000))
        res["M6 guard below the sampled memory"] = {"stopped": False, "seconds": time.perf_counter() - t0}
    except stages.MemoryLimitExceeded as e:
        res["M6 guard below the sampled memory"] = {"stopped": True, "exception": tb(e), "seconds": time.perf_counter() - t0}
    del x
    torch.mps.empty_cache()
    train.MPS_IN_USE = saved_flag

# --- M8 -------------------------------------------------------------------------------------------------------------------------------------------
m8: dict[str, object] = {}
for name in ("auto", "cuda"):
    try:
        m8[f"select_device({name!r})"] = str(train.select_device(name))
    except Exception as e:  # noqa: BLE001
        m8[f"select_device({name!r})"] = tb(e)
orig = torch.backends.mps.is_available
torch.backends.mps.is_available = lambda: False  # type: ignore[assignment]
try:
    m8["select_device('mps') with MPS reported unavailable"] = str(train.select_device("mps"))
except Exception as e:  # noqa: BLE001
    m8["select_device('mps') with MPS reported unavailable"] = tb(e)
finally:
    torch.backends.mps.is_available = orig  # type: ignore[assignment]
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
try:
    m8["select_device('mps') with PYTORCH_ENABLE_MPS_FALLBACK=1"] = str(train.select_device("mps"))
except Exception as e:  # noqa: BLE001
    m8["select_device('mps') with PYTORCH_ENABLE_MPS_FALLBACK=1"] = tb(e)
finally:
    del os.environ["PYTORCH_ENABLE_MPS_FALLBACK"]
g = gates.g4(world, world.plan(0), 3, require_mps=True)
m8["G4 require_mps on a CPU world"] = {"ok": g["ok"], "mps_agreement": g["mps_agreement"]}
g = gates.g4(world, world.plan(0), 3, require_mps=True, cpu_by_freeze=True)
m8["G4 cpu_by_freeze on a CPU world"] = {"ok": g["ok"], "mps_agreement": g["mps_agreement"]}
res["M8"] = m8

# --- f: state leaks --------------------------------------------------------------------------------------------------------------------------------
def state() -> dict[str, object]:
    return {"threads": torch.get_num_threads(), "det": torch.are_deterministic_algorithms_enabled(), "warn_only": torch.is_deterministic_algorithms_warn_only_enabled(), "default_device": str(torch.empty(1).device), "default_dtype": str(torch.get_default_dtype())}


leaks: dict[str, object] = {}
torch.set_num_threads(3)
torch.use_deterministic_algorithms(True, warn_only=True)
s0 = state()
with stages.scoring_environment():
    inside = state()
s1 = state()
leaks["scoring_environment"] = {"before": s0, "inside": inside, "after": s1, "restored": s0 == s1}
if mps:
    w = dataclasses.replace(world, device=torch.device("mps"))
    plan = w.plan(0)
    arm = MemoryArm(SparseStore.new(w.cfg.width, w.rows_per_stage, plan.gen(0, "stage-1 store (recheck leak)")), w.layer, w.codes(0))
    train.train_arm(w.student, arm, w.train_examples(0, "A"), 2, w.batch, w.store_lr, plan.gen(2, "batch order (recheck leak)"), w.marker_index, device=w.device)
    s2 = state()
    leaks["train_arm on MPS with deterministic on, warn_only on"] = {"before": s1, "after": s2, "restored": s1 == s2}
torch.use_deterministic_algorithms(False)
torch.set_num_threads(3)
s3 = state()
tmp = Path(sys.argv[2]).parent / "r2-timing-run"
tmp.mkdir(parents=True, exist_ok=True)
stages.stage_timing(world, tmp, items=2) if not (tmp / "timing.json").exists() else None
s4 = state()
leaks["stage_timing"] = {"before": s3, "after": s4, "restored": s3 == s4}
res["f_state_leaks"] = leaks
res["seed_record_modes"] = sorted({u.mode for u in core.seed_record()})
res["seed_record_range"] = [min(u.seed for u in core.seed_record()), max(u.seed for u in core.seed_record())]
Path(sys.argv[2]).write_text(json.dumps(core.jsonable(res), indent=1, sort_keys=True, default=str))
print(json.dumps(core.jsonable(res), indent=1, sort_keys=True, default=str))
