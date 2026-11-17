"""Re-check B, R9 (old M10): a failed cell does not lose its replicate's records. Stand-in world, test seeds, CPU, 2 updates per cell.
(a) an operation error inside the 5th cell's update loop (train.loss_of patched in this process to raise RuntimeError on its 5th call);
(b) an exception outside train_arm, in the middle of the replicate (cells.train_replicate wrapped to raise after the snapshots of the cells trained so far are written);
(c) a StageGuard wall-clock cap reached during the replicate (cap 1.5 s, many updates).
Usage: PYTHONPATH=<pin>/src python r9_failed_cells.py <pin> <work dir> <out.json>"""

import json
import shutil
import sys
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
W = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(PIN))
from studies.p10s2 import cells, core, stages, standins, train  # noqa: E402

if W.exists():
    shutil.rmtree(W)
W.mkdir(parents=True)
res: dict[str, object] = {}


def summary(run: Path) -> dict:
    p = run / "train" / "r0.json"
    if not p.exists():
        return {"r0.json": "absent"}
    d = json.loads(p.read_text())
    by: dict[str, int] = {}
    for v in d.values():
        by[v["status"]] = by.get(v["status"], 0) + 1
    failed = {k: (v.get("train") or [{}])[0].get("error", "")[:90] for k, v in d.items() if v["status"] != "completed"}
    return {"cells": len(d), "by_status": by, "not_completed": dict(list(failed.items())[:6]), "stopped.json": json.loads((run / "train" / "stopped.json").read_text()) if (run / "train" / "stopped.json").exists() else None}


# (a)
core.reset_seed_record()
world, _ = standins.build_synthetic_world(1, updates=2)
orig = train.loss_of
calls = {"n": 0}


def bad_loss(*a, **k):  # noqa: ANN001, ANN002, ANN003, ANN202
    calls["n"] += 1
    if calls["n"] == 9:  # inside the 5th cell (2 updates per cell)
        raise RuntimeError("injected: an unsupported operation on the device")
    return orig(*a, **k)


train.loss_of = bad_loss
try:
    stages.stage_train(world, W / "a")
    res["a_operation_error_in_a_cell"] = summary(W / "a")
except BaseException as e:  # noqa: BLE001
    res["a_operation_error_in_a_cell"] = {"escaped": f"{type(e).__name__}: {e}", **summary(W / "a")}
finally:
    train.loss_of = orig

# (b)
core.reset_seed_record()
world, _ = standins.build_synthetic_world(1, updates=2)
orig_tr = cells.train_replicate


def tr_then_fail(w, r, snap_dir):  # noqa: ANN001, ANN202
    calls2 = {"n": 0}
    o = train.train_arm

    def counting(*a, **k):  # noqa: ANN002, ANN003, ANN202
        calls2["n"] += 1
        if calls2["n"] == 6:
            raise MemoryError("injected outside a cell's update loop")
        return o(*a, **k)

    train.train_arm = counting
    cells.train_arm = counting  # cells imports the name
    try:
        return orig_tr(w, r, snap_dir)
    finally:
        train.train_arm = o
        cells.train_arm = o


had = hasattr(cells, "train_arm")
cells.train_replicate = tr_then_fail
try:
    stages.stage_train(world, W / "b")
    res["b_exception_outside_a_cell"] = summary(W / "b")
except BaseException as e:  # noqa: BLE001
    res["b_exception_outside_a_cell"] = {"escaped": f"{type(e).__name__}: {e}", **summary(W / "b")}
finally:
    cells.train_replicate = orig_tr
res["b_note"] = "cells.train_arm exists" if had else "cells does not import train_arm by name; the injection went through train.train_arm only"

# (c)
core.reset_seed_record()
world, _ = standins.build_synthetic_world(1, updates=400)
try:
    with stages.StageGuard("r9", cap_seconds=1.5, interval=0.05):
        out = stages.stage_train(world, W / "c")
    res["c_guard_cap_mid_replicate"] = {"returned": out, **summary(W / "c")}
except BaseException as e:  # noqa: BLE001
    res["c_guard_cap_mid_replicate"] = {"escaped": f"{type(e).__name__}: {e}", **summary(W / "c")}
res["seed_modes"] = sorted({u.mode for u in core.seed_record()})
Path(sys.argv[3]).write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))
