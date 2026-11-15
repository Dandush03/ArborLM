"""R2 (auditor, Opus 5.5): summary of the per-update training logs (updates.jsonl) of every registered
cell of P9-I attempt 2, and of attempt 1's restoration-check logs. Reads JSON lines only; imports nothing
from the study code.

For each cell: number of lines and update indices; task loss (32-way alphabet CE at answer sites) averaged
over windows of updates; per-group gradient norms and parameter-change norms averaged over the same
windows; clip total norm. Usage: r2_training_logs.py RUN_DIR [ATTEMPT1_RUN_DIR]
"""
import json
import math
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
WINDOWS = [(1, 16), (17, 128), (129, 512), (513, 1024), (1025, 2048), (2049, 4096), (4097, 6144), (6145, 8192)]
GROUPS = ["keys_selected", "keys_candidate", "keys_untouched", "values", "projections", "interface", "dense", "backbone_attention"]


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def summarize(path: Path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    ups = [r["update"] for r in rows]
    ok_index = ups == list(range(1, len(rows) + 1))
    finite = all(math.isfinite(r["task_loss"]) for r in rows)
    out = {"lines": len(rows), "indices_1_to_n": ok_index, "finite_loss": finite, "windows": []}
    for lo, hi in WINDOWS:
        sel = [r for r in rows if lo <= r["update"] <= hi]
        if not sel:
            continue
        out["windows"].append({
            "updates": f"{lo}-{hi}",
            "task_loss": round(mean([r["task_loss"] for r in sel]), 4),
            "clip_total": round(mean([r["clip_total_norm"] for r in sel]), 5),
            "grad": {g: round(mean([r["grad_norm"][g] for r in sel]), 6) for g in GROUPS if any(r["grad_norm"][g] for r in sel)},
            "change": {g: round(mean([r["param_change_norm"][g] for r in sel]), 6) for g in GROUPS if any(r["param_change_norm"][g] for r in sel)},
        })
    out["min_window_loss"] = min(w["task_loss"] for w in out["windows"])
    out["clip_active_share"] = sum(1 for r in rows if r["clip_total_norm"] > 1.0) / len(rows)
    return out


print("ln 32 =", round(math.log(32), 4))
for d in sorted((RUN / "cells").iterdir()):
    s = summarize(d / "updates.jsonl")
    first, last = s["windows"][0], s["windows"][-1]
    print(f"{d.name:30s} lines={s['lines']} idx_ok={s['indices_1_to_n']} finite={s['finite_loss']} loss[1-16]={first['task_loss']:.4f} "
          f"loss[6145-8192]={last['task_loss']:.4f} min_window={s['min_window_loss']:.4f} clip>1 share={s['clip_active_share']:.4f}")
print()
print("=== per-window detail for the interface arms and references (seed 1801, B101 unless named) ===")
for label in ["W7-n4096-b101-o301-s1801", "W7-n16384-b101-o301-s1801", "W7-n65536-b101-o301-s1801", "E7-n16384-b101-o301-s1801",
              "A4-n16384-b101-o301-s1801", "A4E-n16384-b101-o301-s1801", "N-n16384-b101-o301-s1801", "R1-n16384-b101-o301-s1801",
              "BB-n4096-b101-o301-s1801", "BB-n16384-b101-o301-s1801", "BB-0-n4096-b101-o301-s1801", "D7-n16384-b101-o301-s1801"]:
    s = summarize(RUN / "cells" / label / "updates.jsonl")
    print(label)
    for w in s["windows"]:
        print("   ", json.dumps(w))

if len(sys.argv) > 2:
    print()
    print("=== attempt 1 restoration-check logs (read for the first time after the run) ===")
    a1 = Path(sys.argv[2])
    for p in sorted(a1.glob("g4_restore/**/updates.jsonl")):
        rows = [json.loads(line) for line in p.read_text().splitlines()]
        print(p.relative_to(a1), "lines", len(rows), "loss first/last", round(rows[0]["task_loss"], 4), round(rows[-1]["task_loss"], 4),
              "updates", rows[0]["update"], "..", rows[-1]["update"])
