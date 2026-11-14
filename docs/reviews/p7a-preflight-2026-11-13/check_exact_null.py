"""Auditor check (stdlib only): feasibility of an EXACT count-preserving null for the 81 published P5
histograms. NOT part of the study; a proposal for the lead (PENDING LEAD REVIEW).

Procedure (deterministic given the seed):
  1. Expand the checkpoint's evaluation counts into the multiset of 262,144 slot occurrences, in
     ascending slot order; shuffle it with random.Random(seed).
  2. Deal it into 32,768 queries of 8 consecutive occurrences.
  3. Repair: for q = 0..Q-1, while query q holds a slot x twice (take the duplicate at the higher
     position j), scan r = q+1, q+2, ... (cyclically) for the first query r that does not contain x
     and has a position k (lowest first) whose slot is not in query q; swap q[j] and r[k]. Each swap
     keeps every slot's count, removes one duplicate and creates none.
Existence: a 0/1 slot-by-query incidence with row sums c_i and column sums 8 exists iff (Gale-Ryser,
uniform side 8) max_i c_i <= 32,768. The greedy repair is checked to succeed on every histogram.

Reports per kind: duplicates repaired, swaps, seconds; verifies exact marginals and 8 distinct slots per
query. Computes no page or cache metric.
Run: python3 docs/reviews/p7a-preflight-2026-11-13/check_exact_null.py
"""

import json
import random
import sys
import time
from pathlib import Path

P5 = Path("results/p5-2026-11-13")
Q, TOP = 32768, 8


def exact_null(counts: list[int], seed: int) -> tuple[list[list[int]], int]:
    occ = [slot for slot, c in enumerate(counts) for _ in range(c)]
    random.Random(seed).shuffle(occ)
    qs = [occ[i * TOP : (i + 1) * TOP] for i in range(Q)]
    swaps = 0
    for q in range(Q):
        while True:
            row = qs[q]
            seen: set[int] = set()
            dup_j = -1
            for j, s in enumerate(row):
                if s in seen:
                    dup_j = j
                    break
                seen.add(s)
            if dup_j < 0:
                break
            x = row[dup_j]
            mine = set(row)
            for step in range(1, Q):
                r = qs[(q + step) % Q]
                if x in r:
                    continue
                k = next((k for k, s in enumerate(r) if s not in mine), -1)
                if k >= 0:
                    row[dup_j], r[k] = r[k], row[dup_j]
                    swaps += 1
                    break
            else:
                raise RuntimeError("repair failed")
    return qs, swaps


def main() -> int:
    t_all = time.time()
    out = {}
    for path in sorted(P5.glob("b*-o*-*-s*/result.json")):
        label = path.parent.name
        kind = label.split("-")[2]
        if kind not in ("flat", "fixed_tree", "learned_tree"):
            continue
        counts = json.loads(path.read_text())["final"]["retrieval"]["selected_slot_counts"]
        t0 = time.time()
        qs, swaps = exact_null(counts, 91301)
        realized = [0] * len(counts)
        for row in qs:
            assert len(set(row)) == TOP
            for s in row:
                realized[s] += 1
        assert realized == counts, label
        out[label] = {"kind": kind, "swaps": swaps, "max_count": max(counts),
                      "seconds": time.time() - t0}
    for kind in ("flat", "fixed_tree", "learned_tree"):
        rows = [v for v in out.values() if v["kind"] == kind]
        print(f"{kind}: cells {len(rows)}  swaps mean {sum(r['swaps'] for r in rows)/len(rows):.0f} "
              f"max {max(r['swaps'] for r in rows)}  max count {max(r['max_count'] for r in rows)}"
              f"  seconds/cell {sum(r['seconds'] for r in rows)/len(rows):.2f}")
    print(f"all 81 exact (counts reproduced, 8 distinct per query); total {time.time()-t_all:.0f}s")
    Path(__file__).parent.joinpath("outputs", "exact_null.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
