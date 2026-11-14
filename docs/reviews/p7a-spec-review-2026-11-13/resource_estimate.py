"""Auditor resource estimate for ADR-0013 section 10 (standard library only, synthetic data).

1. Enumerates the simulation passes implied by the draft under the auditor's reading (stated
   below; the draft itself does not enumerate them) and counts page accesses (upper bounds).
2. Micro-benchmarks a plain OrderedDict LRU and a Fenwick-tree single-pass LRU stack-distance
   computation on a synthetic page stream, to convert access counts into seconds.

No model, checkpoint or real trace is used.
Run: python3 -I resource_estimate.py   (and: uv run --locked python -I resource_estimate.py)
"""

import platform
import random
import time
from collections import OrderedDict

Q = 32768  # queries per stream (512 contexts x 64 positions)
CELLS = {"flat": 27, "tree": 54}
VALUE_LAYOUTS = {"flat": 5, "tree": 6}  # L-ID, L-RAND x3, L-FREQ (+ L-BFREQ for trees)
GRANULARITIES = 6  # 3 blocks x 2 geometries
STREAMS = 3  # evaluation ordered, order-shuffled, context-shuffled
CAPS = 3
# Upper-bound distinct value pages per query (8 rows) and key pages per query (SSD-index),
# per block size 4/16/64 KiB. Keys are 64 B rows in both geometries.
FLAT_KEY_PAGES = {4: 64, 16: 16, 64: 4}
TREE_KEY_PAGES_LID = {4: 8, 16: 2, 64: 1}  # two branches; 64 KiB: 1-2
TREE_KEY_PAGES_LRAND = {4: 64, 16: 16, 64: 4}  # 512 rows scattered over all key pages (approx.)


def enumerate_work() -> list[str]:
    out = []
    ram_passes = sum(CELLS[a] * VALUE_LAYOUTS[a] * GRANULARITIES * STREAMS for a in CELLS)
    calib_passes = CELLS["tree"] * 3 * GRANULARITIES  # tree layout choice if re-chosen per granularity
    ram_accesses = (ram_passes + calib_passes) * Q * 8
    out.append(f"RAM-index value-only passes: {ram_passes} (+{calib_passes} calibration selection passes)")
    out.append(f"  accesses per pass <= {Q * 8:,}; total <= {ram_accesses:,} per capacity "
               f"(x{CAPS} = {ram_accesses * CAPS:,} if each capacity is a separate pass)")
    ssd = 0
    for arch in CELLS:
        for block in (4, 16, 64):
            for key_layout in ("LID", "LRAND"):
                if arch == "flat":
                    kp = FLAT_KEY_PAGES[block]
                else:
                    kp = (TREE_KEY_PAGES_LID if key_layout == "LID" else TREE_KEY_PAGES_LRAND)[block]
                # x2 geometries (value geometry changes, keys do not)
                ssd += CELLS[arch] * VALUE_LAYOUTS[arch] * 2 * STREAMS * Q * (kp + 8)
    out.append(f"SSD-index shared-cache accesses (value layouts x key layouts crossed): <= {ssd:,} "
               f"per capacity (x{CAPS} = {ssd * CAPS:,} if separate passes)")
    out.append(f"TOTAL upper bound, separate pass per capacity: {(ram_accesses + ssd) * CAPS:,}")
    out.append(f"TOTAL upper bound, one stack-distance pass for all capacities: {ram_accesses + ssd:,}")
    return out


def bench(n: int) -> list[str]:
    rng = random.Random(5)
    # Skewed synthetic page stream over 128 pages, 16-page cache.
    weights = [1 / (i + 1) for i in range(128)]
    stream = rng.choices(range(128), weights=weights, k=n)
    t0 = time.perf_counter()
    cache: OrderedDict[int, None] = OrderedDict()
    misses = 0
    for p in stream:
        if p in cache:
            cache.move_to_end(p)
        else:
            misses += 1
            cache[p] = None
            if len(cache) > 16:
                cache.popitem(last=False)
    t_lru = (time.perf_counter() - t0) / n
    # Fenwick-tree stack distance (Bennett-Kruskal style): one pass yields all capacities.
    t0 = time.perf_counter()
    size = n + 1
    tree = [0] * (size + 1)
    last: dict[int, int] = {}
    hist: dict[int, int] = {}

    def add(i: int, v: int) -> None:
        i += 1
        while i <= size:
            tree[i] += v
            i += i & -i

    def prefix(i: int) -> int:  # sum of [0, i)
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & -i
        return s

    for t, p in enumerate(stream):
        prev = last.get(p)
        if prev is None:
            d = -1
        else:
            d = prefix(t) - prefix(prev + 1)  # distinct pages touched since previous use
            add(prev, -1)
        hist[d] = hist.get(d, 0) + 1
        add(t, 1)
        last[p] = t
    t_sd = (time.perf_counter() - t0) / n
    misses_sd = sum(c for d, c in hist.items() if d == -1 or d >= 16)
    assert misses_sd == misses, (misses_sd, misses)
    return [
        f"python {platform.python_version()} on {platform.machine()}",
        f"OrderedDict LRU: {t_lru * 1e9:.0f} ns/access; Fenwick stack distance: {t_sd * 1e9:.0f} ns/access "
        f"(cross-check: identical miss count {misses} at 16 pages)",
    ], t_lru, t_sd


def main() -> None:
    lines = enumerate_work()
    blines, t_lru, t_sd = bench(2_000_000)
    lines += blines
    import re

    sep = int(re.sub(r"[^0-9]", "", lines[-4].split(":")[1]))
    one = int(re.sub(r"[^0-9]", "", lines[-3].split(":")[1]))
    lines.append(f"estimated seconds, separate LRU pass per capacity: {sep * t_lru:,.0f}")
    lines.append(f"estimated seconds, one stack-distance pass: {one * t_sd:,.0f}")
    lines.append("Budget in ADR-0013 section 10: simulation and analysis <= 3,600 s.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
