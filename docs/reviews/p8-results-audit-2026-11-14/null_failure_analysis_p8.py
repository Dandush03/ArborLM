"""Why did the registered count-preserving null fail on five P8 cells? Auditor: Claude Opus 5.5.
Not Astra validation, not human approval. This is NOT an alternative null and produces no
registered quantity: it reads the panel traces, checks feasibility, and replays the registered
greedy (ADR-0013 section 14 item 8, as written in p7a_core._deal_and_repair's docstring, re-typed
here from that text with no arborlm import) with the registered seed, to see whether the recorded
failure (slot, row) is reproduced on Panel A, i.e. whether Panel A was the panel that failed.

Feasibility: a Q x 4096 0/1 matrix with every row sum 8 and column sums c exists iff
sum c = 8Q and max c <= Q (Gale-Ryser with uniform row sums: for k <= 8 the bound is Qk, implied
by max c <= Q; for k > 8 it is 8Q = total). The actual trace is itself such a matrix, so every
panel's histogram is feasible by construction.

Usage: python -I null_failure_analysis_p8.py --eval-run E --sim-run S --labels L ...
"""

import argparse
import json
import random
import struct
import sys
from collections import Counter
from pathlib import Path

SEEDS = {"A": (91331, 91332, 91333), "B": (91341, 91342, 91343)}
PARENTS = {101: 0, 102: 1, 103: 2}


def cell_index(lab: str) -> int:
    b, _, s, c = lab.split("-")
    return 20 * PARENTS[int(b[1:])] + 10 * (int(s[1:]) - 601) + int(c[1:]) - 1


def read_sel(path: Path) -> list[list[int]]:
    raw = path.read_bytes()
    v = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    return [list(v[i : i + 8]) for i in range(0, len(v), 8)]


def greedy(counts: list[int], gen: random.Random, queries: int, top: int = 8):
    occ = [s for s, c in enumerate(counts) for _ in range(c)]
    gen.shuffle(occ)
    rows = [occ[i * top : (i + 1) * top] for i in range(queries)]
    swaps = 0
    for q in range(queries):
        row = rows[q]
        while len(set(row)) < top:
            seen, pos = set(), -1
            for j, s in enumerate(row):
                if s in seen:
                    pos = j
                    break
                seen.add(s)
            x, mine = row[pos], set(row)
            for step in range(1, queries):
                other = rows[(q + step) % queries]
                if x in other:
                    continue
                k = next((k for k, s in enumerate(other) if s not in mine), -1)
                if k >= 0:
                    row[pos], other[k] = other[k], row[pos]
                    swaps += 1
                    break
            else:
                # describe the stuck state
                lacking_x = [r for r in range(queries) if x not in rows[r]]
                subset = [r for r in lacking_x if set(rows[r]) <= mine]
                unrepaired_dupe_rows = sum(1 for r in range(q, queries) if len(set(rows[r])) < top)
                return {"failed": True, "slot": x, "row": q, "row_contents": sorted(row),
                        "rows_lacking_x": len(lacking_x), "rows_lacking_x_all_subset_of_row_q": len(subset) == len(lacking_x),
                        "rows_lacking_x_indices_min": min(lacking_x) if lacking_x else None,
                        "rows_with_duplicates_from_q": unrepaired_dupe_rows, "swaps_before_failure": swaps}
    return {"failed": False, "swaps": swaps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-run", type=Path, required=True)
    ap.add_argument("--sim-run", type=Path, required=True)
    ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--replay", action="store_true", help="replay the registered greedy on Panel A, seeds in order until the first failure")
    a = ap.parse_args()
    out = {}
    for lab in a.labels:
        cdir = a.eval_run / "cells" / lab
        ev = json.loads((cdir / "eval.json").read_text())
        failed = (a.sim_run / "cells" / lab / "sim.failed.json").is_file()
        rec = {"sim_failed_record": failed, "cell_index": cell_index(lab), "panels": {}}
        for p in ("A", "B"):
            sel = read_sel(cdir / ev["traces"][p]["files"]["selected"]["file"])
            q = len(sel)
            cnt = Counter(s for r in sel for s in r)
            counts = [cnt.get(i, 0) for i in range(4096)]
            sets = Counter(tuple(sorted(r)) for r in sel)
            pr = {
                "queries": q, "distinct_slots": len(cnt), "max_count": max(counts),
                "min_nonzero_count": min(c for c in counts if c),
                "slots_with_count_equal_queries": sum(1 for c in counts if c == q),
                "distinct_query_sets": len(sets), "most_common_set_share": sets.most_common(1)[0][1] / q,
                "rows_with_distinct_slots": sum(1 for r in sel if len(set(r)) == 8),
                "feasible_gale_ryser": sum(counts) == 8 * q and max(counts) <= q,
                "top_counts": sorted(counts, reverse=True)[:12],
            }
            if a.replay and p == "A":
                pr["replay"] = []
                for rs in SEEDS[p]:  # registered order; the stage stops at the first failure
                    seed = rs * 1000 + rec["cell_index"]
                    r = greedy(counts, random.Random(seed), q)
                    pr["replay"].append({"generator_seed": seed, **r})
                    if r["failed"]:
                        break
            rec["panels"][p] = pr
        out[lab] = rec
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
