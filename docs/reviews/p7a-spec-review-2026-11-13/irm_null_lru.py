"""Auditor estimate: LRU warm misses under a frequency-matched independent-sampling null.

SYNTHETIC. For each published P5 cell, queries are generated independently: each query draws
8 distinct slots by successive weighted sampling from that cell's published evaluation-panel
selection histogram (results/p5-2026-11-13/<cell>/result.json, final.retrieval.
selected_slot_counts). This keeps (approximately) each architecture's marginal concentration and
destroys co-selection and temporal structure. It is NOT a prediction of ADR-0013's measured
values; it shows where the registered metric would sit if concentration alone mattered.

Layouts: FREQ-oracle (packed by the same histogram used to sample: a lower bound for L-FREQ)
and L-ID. Access model as written in ADR-0013 section 5: one LRU, pages of a query deduplicated
and touched in ascending page order; warm on the first half of queries, count on the second half.
A descending-order variant is also run at the 64 KiB actual block to test order dependence.

No model, checkpoint or real trace is used. Standard library only.
Run: python3 -I irm_null_lru.py <repo>/results/p5-2026-11-13 [queries]
"""

import bisect
import itertools
import json
import random
import statistics
import sys
import time
from collections import OrderedDict
from pathlib import Path

ARCHS = ("flat", "fixed_tree", "learned_tree")
SETTINGS = (
    # label, rows per page, capacities in pages (64/128/256 KiB-equivalent fractions)
    ("actual 4KiB", 32, (16, 32, 64)),
    ("actual 64KiB", 512, (1, 2, 4)),
    ("hyp 4KiB", 2, (256, 512, 1024)),
)


def draw_queries(counts: list[int], n: int, rng: random.Random) -> list[list[int]]:
    slots = [s for s, c in enumerate(counts) if c]
    cum = list(itertools.accumulate(counts[s] for s in slots))
    total = cum[-1]
    out = []
    for _ in range(n):
        chosen: set[int] = set()
        while len(chosen) < 8:
            chosen.add(slots[bisect.bisect_right(cum, rng.random() * total)])
        out.append(sorted(chosen))
    return out


def lru_warm_misses(page_lists: list[list[int]], capacity: int, descending: bool) -> float:
    cache: OrderedDict[int, None] = OrderedDict()
    half = len(page_lists) // 2
    misses = 0
    for qi, pages in enumerate(page_lists):
        for p in (reversed(pages) if descending else pages):
            if p in cache:
                cache.move_to_end(p)
            else:
                if qi >= half:
                    misses += 1
                cache[p] = None
                if len(cache) > capacity:
                    cache.popitem(last=False)
    return misses / (len(page_lists) - half)


def main() -> None:
    root = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8192
    rng = random.Random(91999)
    results: dict[str, dict[str, list[float]]] = {a: {} for a in ARCHS}
    accesses = 0
    t0 = time.perf_counter()
    for cell in sorted(root.iterdir()):
        parts = cell.name.split("-")
        if len(parts) != 4 or parts[2] not in ARCHS:
            continue
        counts = json.loads((cell / "result.json").read_text())["final"]["retrieval"][
            "selected_slot_counts"
        ]
        queries = draw_queries(counts, n, rng)
        order = sorted(range(4096), key=lambda s: (-counts[s], s))
        freq_pos = [0] * 4096
        for pos, s in enumerate(order):
            freq_pos[s] = pos
        for label, r, caps in SETTINGS:
            for layout, pos_of in (("FREQ", freq_pos), ("LID", list(range(4096)))):
                pls = [sorted({pos_of[s] // r for s in q}) for q in queries]
                key = f"{label} {layout} pages/query"
                results[parts[2]].setdefault(key, []).append(statistics.fmean(len(p) for p in pls))
                for cap in caps:
                    m = lru_warm_misses(pls, cap, False)
                    accesses += sum(len(p) for p in pls)
                    results[parts[2]].setdefault(f"{label} {layout} warm misses/query cap={cap}p asc", []).append(m)
                    if label == "actual 64KiB":
                        md = lru_warm_misses(pls, cap, True)
                        accesses += sum(len(p) for p in pls)
                        results[parts[2]].setdefault(f"{label} {layout} warm misses/query cap={cap}p DESC", []).append(md)
    elapsed = time.perf_counter() - t0
    lines = [f"synthetic queries per cell: {n} (warm {n // 2}, measured {n - n // 2}); rng seed 91999"]
    keys = list(results["flat"].keys())
    for key in keys:
        lines.append(key)
        for arch in ARCHS:
            v = results[arch][key]
            lines.append(
                f"   {arch:13s} mean {statistics.fmean(v):.6f}  min {min(v):.6f}  max {max(v):.6f}"
            )
        mf = statistics.fmean(results["flat"][key])
        for arch in ARCHS[1:]:
            mt = statistics.fmean(results[arch][key])
            lines.append(f"   ratio {arch}/flat of means: {mt / mf:.3f}" if mf > 0 else f"   ratio {arch}/flat: flat mean 0")
    lines.append(f"LRU page accesses simulated: {accesses}; wall time incl. sampling {elapsed:.1f} s; "
                 f"~{elapsed / accesses * 1e9:.0f} ns per access (upper bound, includes sampling)")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
