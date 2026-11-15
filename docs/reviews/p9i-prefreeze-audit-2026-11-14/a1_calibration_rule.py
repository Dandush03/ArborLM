"""A1 (auditor, Opus 5.5): recompute the section I.6 rule from the per-cell calibration records.

Own code: reads cells/*/calibration_cell.json and cells/*/train.json of the calibration run, takes the
minimum over the two B101 seeds and both panels, applies the rule literally, and compares with the
run's calibration.json. Does not import studies.p9i (no core.select_updates).
"""
import json
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
CAND = (2048, 4096, 8192, 16384)
SIZES = (4096, 16384, 65536)
FACTS = {4096: 2048, 16384: 8192, 65536: 32768}

cells = sorted((RUN / "cells").iterdir())
labels = [c.name for c in cells]
expected = sorted(
    f"CAL-{arm}-n{s}-b{b}-o{o}-s{seed}"
    for arm in ("R1", "R2") for s in SIZES
    for (b, o, seed) in ((101, 301, 1791), (101, 301, 1792), (102, 302, 1791))
)
print("cell dirs == the 18 calibration cells:", labels == expected)

acc: dict[tuple, dict[int, dict[str, float]]] = {}
for c in cells:
    rec = json.loads((c / "calibration_cell.json").read_text())
    tr = json.loads((c / "train.json").read_text())
    key = (rec["arm"], rec["slots"], tuple(rec["parent"]), rec["seed"])
    acc[key] = {int(u): v for u, v in rec["accuracy"].items()}
    assert tr["arm"] == rec["arm"] and tr["mode"] == "calibration" and tr["status"] == "completed"
    assert tr["matched_updates"] == 16384 and tr["run_updates"] == 16384, tr["label"]
    assert tr["facts"] == FACTS[rec["slots"]] and tr["examples"] == 16 * 16384
    assert tr["init_seed"] == rec["seed"] and tr["trainable_backbone_parameters"] == 0
    assert tr["snapshots"] == [1024, 2048, 4096, 8192, 16384]
    # every fact exactly the same number of times: 16384 * 128 / F
    assert tr["exposure_per_fact_min"] == tr["exposure_per_fact_max"] == 16384 * 128 // tr["facts"]
    for u, v in acc[key].items():
        for p in ("A", "B"):
            k = round(v[p] * tr["facts"])
            assert abs(k / tr["facts"] - v[p]) < 1e-12  # accuracy is an integer count over F

mins: dict[str, dict[int, dict[int, float]]] = {"R1": {}, "R2": {}}
for arm in ("R1", "R2"):
    for s in SIZES:
        mins[arm][s] = {}
        for u in (1024, *CAND):
            mins[arm][s][u] = min(acc[(arm, s, (101, 301), seed)][u][p] for seed in (1791, 1792) for p in ("A", "B"))

print("\nminimum over B101 seeds 1791/1792 and panels A/B (count/F):")
for arm in ("R2", "R1"):
    for s in SIZES:
        row = "  ".join(f"{u}:{mins[arm][s][u]:.6f}({round(mins[arm][s][u] * FACTS[s])})" for u in (1024, *CAND))
        print(f"{arm} {s:>5}  {row}")

def ok(s: int, u: int) -> bool:
    return mins["R2"][s][u] >= 0.95 and mins["R1"][s][u] >= 0.90

failed = {}
for s in SIZES:
    r2_any = any(mins["R2"][s][u] >= 0.95 for u in CAND)
    r1_any = any(mins["R1"][s][u] >= 0.90 for u in CAND)
    if not any(ok(s, u) for u in CAND):
        failed[s] = [x for x, bad in (("TASK_CEILING_FAIL", not r2_any), ("ORACLE_QUERY_FAIL", not r1_any)) if bad] or ["NOT_JOINT"]
live = [s for s in SIZES if s not in failed]
U = next((u for u in CAND if all(ok(s, u) for s in live)), None)
print("\nauditor: U =", U, "failed sizes =", failed)
for u in CAND:
    bad = [(s, arm) for s in SIZES for arm, thr in (("R2", 0.95), ("R1", 0.90)) if mins[arm][s][u] < thr]
    print(f"  U={u}: below threshold -> {bad}")

cal = json.loads((RUN / "calibration.json").read_text())
same_mins = all(
    abs(cal[f"{arm.lower()}_min_accuracy"][str(s)][str(u)] - mins[arm][s][u]) == 0
    for arm in ("R1", "R2") for s in SIZES for u in (1024, *CAND)
)
print("run's calibration.json: U =", cal["selected_updates"], "failed =", cal["failed_sizes"], "| minima identical:", same_mins)
print("U agrees:", cal["selected_updates"] == U, "| failed agrees:", cal["failed_sizes"] == {str(k): v for k, v in failed.items()})

print("\nB102 replicate (reported only):")
for arm in ("R1", "R2"):
    for s in SIZES:
        v = acc[(arm, s, (102, 302), 1791)]
        print(f"  {arm} {s:>5} " + "  ".join(f"{u}:{min(v[u].values()):.4f}" for u in (1024, *CAND)))
print("\nper-seed / per-panel at the binding cell R1 65536:")
for seed in (1791, 1792):
    v = acc[("R1", 65536, (101, 301), seed)]
    print(f"  s{seed} " + "  ".join(f"{u}:A={v[u]['A']:.5f},B={v[u]['B']:.5f}" for u in (4096, 8192)))
