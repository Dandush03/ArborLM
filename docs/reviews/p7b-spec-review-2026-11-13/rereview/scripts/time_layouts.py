"""Time the complete rev-3 co-access layout set per checkpoint (calibration traces only).

Per checkpoint: A0, A8 (calibration) and A0 of the calibration null (for L-NCOAX); for each
R in {1, 2, 8, 32, 128, 512}: L-COAX, L-NCOAX, L-COAX8 (greedy + refinement; greedy-only is the
intermediate), and for trees L-BCOAX, L-BCOAX8; five L-PCOAX for every architecture.
Single process per checkpoint. Auditor's own implementation; an implementer's may be faster or slower.

Usage: .venv/bin/python -I .../rereview/scripts/time_layouts.py [--labels ...] [--jobs N]
"""

import argparse
import json
import sys
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True
HERE = __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE)
sys.path.insert(0, HERE.rsplit("/rereview", 1)[0] + "/scripts")
import calib_coaccess as old  # noqa: E402
import rev3_layouts as L  # noqa: E402

OUT = "docs/reviews/p7b-spec-review-2026-11-13/rereview/outputs"
RS = (1, 2, 8, 32, 128, 512)
SEEDS = (91601, 91602, 91603, 91604, 91605)


def work(args):
    label, kind, idx = args
    rec = json.load(open(f"{old.TREC}/{label}.json"))
    cs = rec["files"]["calibration"]["selected"]
    path = f"{old.RAW}/{rec['trace_dir']}/{cs['file']}"
    assert "eval_" not in path and old.sha256(path) == cs["sha256"]
    sel = old.read_i16(path)
    t = {}
    info = {}
    T0 = time.perf_counter()
    f = L.counts_of(sel)
    s = time.perf_counter()
    A0 = L.affinity0(sel, 32768)
    t["A0"] = time.perf_counter() - s
    s = time.perf_counter()
    A8 = L.affinity_w(sel, 512, 8)
    t["A8"] = time.perf_counter() - s
    s = time.perf_counter()
    nul = old.null_stream(f, idx)
    An = L.affinity0(nul, 32768)
    t["null+An0"] = time.perf_counter() - s
    parts = [L.partition_groups(x) for x in SEEDS]
    for R in RS:
        jobs = [("COAX", lambda: L.coax(R, f, A0)), ("NCOAX", lambda: L.coax(R, f, An)),
                ("COAX8", lambda: L.coax(R, f, A8))]
        if kind != "flat":
            jobs += [("BCOAX", lambda: L.group_coax(L.branch_groups(), R, f, A0)),
                     ("BCOAX8", lambda: L.group_coax(L.branch_groups(), R, f, A8))]
        for i, p in enumerate(parts):
            jobs.append((f"P{i + 1}", lambda p=p: L.group_coax(p, R, f, A0)))
        for name, fn in jobs:
            s = time.perf_counter()
            pages, inf = fn()
            t[f"{name}|R{R}"] = time.perf_counter() - s
            info[f"{name}|R{R}"] = inf
            assert sorted(x for pg in pages for x in pg) == list(range(L.SLOTS))
    return {"label": label, "kind": kind, "total": time.perf_counter() - T0, "t": t, "info": info,
            "files_read": [path]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    todo = old.registered()
    if a.labels:
        todo = [x for x in todo if x[0] in a.labels]
    t0 = time.perf_counter()
    with Pool(a.jobs) as pool:
        res = pool.map(work, todo, chunksize=1)
    wall = time.perf_counter() - t0
    json.dump({"wall": wall, "jobs": a.jobs, "per_checkpoint": res}, open(f"{OUT}/time_layouts.json", "w"), indent=1)
    for r in res:
        by = {}
        for k, v in r["t"].items():
            by.setdefault(k.split("|")[-1] if "|" in k else "affinity", []).append(v)
        print(r["label"], f"total {r['total']:.1f} s;", {k: round(sum(v), 2) for k, v in by.items()})
        mp = max((v["passes"] for v in r["info"].values() if v), default=0)
        nc = [k for k, v in r["info"].items() if v and not v["converged"]]
        print("   max passes", mp, "not converged:", nc)
    print("wall", round(wall, 1), "s with", a.jobs, "processes")


if __name__ == "__main__":
    main()
