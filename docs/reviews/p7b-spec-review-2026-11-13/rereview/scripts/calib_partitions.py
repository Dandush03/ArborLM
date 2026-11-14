"""Re-review of ADR-0014 rev 3: partition control and adjusted ratio on the CALIBRATION stream only.

Auditor role (Claude Opus 5.5). Standard library only; no arborlm import; no implementer code.
Reads per checkpoint ONLY experiments/P7AT-.../traces/<label>/calib_selected.int16.bin (sha256
checked against the P7-A trace record). Never opens eval_selected / eval_branches. All layouts are
fitted on the calibration stream and scored in-sample on it (warm-up first 256 contexts, count last
256) or on a reviewer null of the calibration stream (seed 77001, one replicate). No registered
outcome on any evaluation stream is computed.

Usage (repo root):
  .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/calib_partitions.py --jobs 16
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True
HERE = __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE)
sys.path.insert(0, HERE.rsplit("/rereview", 1)[0] + "/scripts")
import calib_coaccess as old  # noqa: E402  (auditor's own revision-1 script: io, LRU, null)
import rev3_layouts as L  # noqa: E402

OUT = "docs/reviews/p7b-spec-review-2026-11-13/rereview/outputs"
Q = 32768
SETTINGS = ((2, 32), (8, 8))
REG_SEEDS = (91601, 91602, 91603, 91604, 91605)
EXTRA_SEEDS = tuple(range(91701, 91721))  # reviewer-only, operating characteristics (trees)
PROFILE_SEEDS = (91801, 91802, 91803, 91804, 91805)  # reviewer-only profile-matched partitions


def profile_partition(f, seed, binw=16):
    """Groups that keep each real branch's popularity profile (slots per 16-rank frequency bin)
    but scramble membership: inside each bin of 16 consecutive frequency ranks, branch labels are
    randomly permuted among the bin's slots."""
    order = L.layout_freq(f)
    g = random.Random(seed)
    label = [None] * L.SLOTS
    for i in range(0, L.SLOTS, binw):
        b = order[i:i + binw]
        labs = [s // L.PB for s in b]
        g.shuffle(labs)
        for s, lab in zip(b, labs):
            label[s] = lab
    groups = [[] for _ in range(L.NBR)]
    for s in range(L.SLOTS):
        groups[label[s]].append(s)
    assert all(len(x) == L.PB for x in groups)
    return groups


def sim(sel, pages, R, C):
    pos = L.positions(pages)
    pq = old.query_pages(sel, pos, R, range(Q))
    return {"asc": old.lru(pq, C, Q // 2), "desc": old.lru(pq, C, Q // 2, descending=True)}


def work(args):
    label, kind, idx = args
    t0 = time.perf_counter()
    rec = json.load(open(f"{old.TREC}/{label}.json"))
    d = f"{old.RAW}/{rec['trace_dir']}"
    cs = rec["files"]["calibration"]["selected"]
    path = f"{d}/{cs['file']}"
    assert "eval_" not in path and old.sha256(path) == cs["sha256"]
    sel = old.read_i16(path)
    f = L.counts_of(sel)
    A = L.affinity0(sel, Q)
    nul = old.null_stream(f, idx)
    out = {"label": label, "kind": kind, "files_read": [path], "eff_slots": old.eff_slots(f),
           "m": {}, "refine": {}}
    groups = {f"P{i + 1}": L.partition_groups(s) for i, s in enumerate(REG_SEEDS)}
    if kind != "flat":
        groups["B"] = L.branch_groups()
        groups.update({f"X{s}": L.partition_groups(s) for s in EXTRA_SEEDS})
        groups.update({f"M{s}": profile_partition(f, s) for s in PROFILE_SEEDS})
    for R, C in SETTINGS:
        key = f"R{R}C{C}"
        lay = {"FREQ": L.order_to_pages(L.layout_freq(f), R)}
        g0 = L.greedy_pages(list(range(L.SLOTS)), R, f, A)
        lay["COAXg"] = g0
        lay["COAX"], out["refine"][f"COAX|{key}"] = L.refine(g0, A, f)
        for name, gr in groups.items():
            lay[name], out["refine"][f"{name}|{key}"] = L.group_coax(gr, R, f, A)
        for name, pg in lay.items():
            out["m"][f"actual|{name}|{key}"] = sim(sel, pg, R, C)
            if name in ("FREQ", "COAX", "B") or name.startswith("P") or name.startswith("M"):
                out["m"][f"null|{name}|{key}"] = sim(nul, pg, R, C)
            out.setdefault("wpa", {})[f"{name}|{key}"] = L.within_page_affinity(pg, A)
    out["seconds"] = time.perf_counter() - t0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--out", default=f"{OUT}/calib_partitions.json")
    a = ap.parse_args()
    todo = old.registered()
    if a.labels:
        todo = [t for t in todo if t[0] in a.labels]
    t0 = time.perf_counter()
    with Pool(a.jobs) as pool:
        res = pool.map(work, todo, chunksize=1)
    files = sorted(x for r in res for x in r["files_read"])
    assert not any("eval_" in x for x in files)
    out = {"wall_seconds": time.perf_counter() - t0, "n": len(res), "files_read": files,
           "eval_files_read": [], "per_checkpoint": res}
    with open(a.out, "w") as fh:
        json.dump(out, fh, sort_keys=True)
    print("done", len(res), "in", round(out["wall_seconds"], 1), "s; files", len(files),
          "; evaluation files read: 0")


if __name__ == "__main__":
    main()
