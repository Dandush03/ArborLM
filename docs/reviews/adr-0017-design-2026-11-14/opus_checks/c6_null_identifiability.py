"""C6 - planted clusters: is E = actual misses / count-preserving-null misses identifiable? (toy)

Auditor toy, independent of arborlm code (re-implements an LRU page cache and a count-preserving null
in the spirit of ADR-0013 item 8; it is NOT the registered generator). Answer-site queries only.

N = 16,384 slots, F = 8,192 facts in clusters of 16 (rev 1 section 4.3). A context = 8 distinct facts of
one cluster; every cluster gives two contexts per epoch; epochs in seeded cluster order. Calibration
and evaluation streams are 2 epochs each with different seeds. Each fact selects a fixed set of 8 slots:
  S1 random     : 8 slots uniform over N (slots shared across clusters, ~4 facts per slot);
  S2 coherent   : each cluster owns 32 slots (random IDs); each fact selects 8 of its cluster's 32;
  S3 collapsed  : every fact selects the same 8 slots (P8 C04/C05-like).
Layouts: 'id' (slot-ID order = random w.r.t. clusters), 'cluster' (slots grouped by the cluster that
accesses them most on calibration, ties by lowest cluster then slot ID: the rev 1 'oracle layout' needs
such a tie rule once slots are shared). Cache: C = max(1, round(rho W / R)) pages, LRU, W = distinct
slots on calibration (rev 1 section 8.4). Null: occurrences shuffled across queries, per-slot counts and
8-distinct-per-query preserved (simple swap repair), 3 seeds.
"""

import json
import random
from collections import OrderedDict

N, F, CL, TOPK = 16384, 8192, 16, 8


def selections(kind: str, rng: random.Random) -> list[list[int]]:
    if kind == "S1 random":
        return [rng.sample(range(N), TOPK) for _ in range(F)]
    if kind == "S2 coherent":
        ids = list(range(N))
        rng.shuffle(ids)
        out = []
        for f in range(F):
            pool = ids[(f // CL) * 32 : (f // CL) * 32 + 32]
            out.append(rng.sample(pool, TOPK))
        return out
    return [list(range(TOPK)) for _ in range(F)]


def stream(seed: int, epochs: int = 2) -> list[int]:
    rng = random.Random(seed)
    facts: list[int] = []
    for _ in range(epochs):
        order = list(range(F // CL))
        rng.shuffle(order)
        for c in order:
            members = list(range(c * CL, c * CL + CL))
            rng.shuffle(members)
            facts.extend(members)  # two contexts of 8 per cluster, back to back
    return facts


def null_stream(queries: list[list[int]], seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    occ = [s for q in queries for s in q]
    rng.shuffle(occ)
    rows = [occ[i * TOPK : (i + 1) * TOPK] for i in range(len(queries))]
    for i, row in enumerate(rows):
        tries = 0
        while len(set(row)) < TOPK and tries < 10_000:
            tries += 1
            seen, pos = set(), -1
            for j, s in enumerate(row):
                if s in seen:
                    pos = j
                    break
                seen.add(s)
            other = rows[rng.randrange(len(rows))]
            k = rng.randrange(TOPK)
            if other[k] not in row and row[pos] not in other:
                row[pos], other[k] = other[k], row[pos]
    return rows


def misses(queries: list[list[int]], position: dict[int, int], rows_per_page: int, cache_pages: int) -> float:
    cache: OrderedDict[int, None] = OrderedDict()
    total = 0
    half = len(queries) // 2  # first half warms the cache
    for t, q in enumerate(queries):
        for page in sorted({position[s] // rows_per_page for s in q}):
            if page in cache:
                cache.move_to_end(page)
            else:
                if t >= half:
                    total += 1
                cache[page] = None
                if len(cache) > cache_pages:
                    cache.popitem(last=False)
    return total / (len(queries) - half)


def main() -> None:
    for kind in ("S1 random", "S2 coherent", "S3 collapsed"):
        sel = selections(kind, random.Random(11))
        cal = [sel[f] for f in stream(101)]
        ev = [sel[f] for f in stream(202)]
        used = sorted({s for q in cal for s in q})
        w = len(used)
        votes: dict[int, dict[int, int]] = {}
        for f in stream(101):
            for s in sel[f]:
                votes.setdefault(s, {}).setdefault(f // CL, 0)
                votes[s][f // CL] += 1
        owner = {s: min(v.items(), key=lambda kv: (-kv[1], kv[0]))[0] for s, v in votes.items()}
        majority_share = sum(max(v.values()) for v in votes.values()) / sum(sum(v.values()) for v in votes.values())
        cluster_order = sorted(used, key=lambda s: (owner[s], s)) + [s for s in range(N) if s not in owner]
        layouts = {"id": {s: s for s in range(N)},
                   "cluster": {s: i for i, s in enumerate(cluster_order)}}
        nulls = [null_stream(ev, seed) for seed in (1, 2, 3)]
        for rows_per_page in (8, 32):
            for rho in (1 / 16, 1 / 4):
                pages = max(1, round(rho * w / rows_per_page))
                for name, pos in layouts.items():
                    actual = misses(ev, pos, rows_per_page, pages)
                    null = sum(misses(nq, pos, rows_per_page, pages) for nq in nulls) / 3
                    print(json.dumps({"case": kind, "distinct_slots_W": w,
                                      "slot_access_share_from_majority_cluster": round(majority_share, 3),
                                      "R": rows_per_page, "rho": rho, "cache_pages": pages, "layout": name,
                                      "actual_misses_per_query": round(actual, 3),
                                      "null_misses_per_query": round(null, 3),
                                      "E": round(actual / null, 3) if null > 0 else None,
                                      "degenerate_null_below_0.05": null < 0.05}), flush=True)


if __name__ == "__main__":
    main()
