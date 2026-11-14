"""R4 (re-check of rev 2) - how hard is LOCALITY_POSITIVE (E ratio <= 0.80) on the planted stream? (toy)

Auditor toy, independent of arborlm code; same stream, LRU cache, cache rule and count-preserving null
as C6 (functions copied from c6_null_identifiability.py, which the auditor wrote for the rev 1 review).
N = 16,384, F = 8,192, clusters of 16, answer-site queries only, 8 slots per fact.

Cases:
  random            : 8 slots uniform over N (the expected dose-zero reference, C6 'S1').
  coherent_p        : with probability p a fact draws its 8 slots from its cluster's 32 slots, else random.
  packed_random     : each fact's 8 slots are one aligned 8-slot group chosen at random (4 facts per
                      group), i.e. perfect within-query co-access and no cluster structure.
'Own optimized layout' is approximated by the better of identity and the oracle cluster layout (the
P7-B co-access optimizer is not re-run). E = actual / mean of 3 nulls under the same layout.
The E ratio is case E / reference E (reference = 'random' under its best layout).
"""

import json
import random
from collections import OrderedDict

N, F, CL, TOPK = 16384, 8192, 16, 8


def selections(kind: str, p: float, rng: random.Random) -> list[list[int]]:
    ids = list(range(N))
    rng.shuffle(ids)
    out = []
    for f in range(F):
        if kind == "packed_random":
            g = rng.randrange(N // 8)
            out.append(list(range(g * 8, g * 8 + 8)))
        elif kind == "coherent" and rng.random() < p:
            pool = ids[(f // CL) * 32 : (f // CL) * 32 + 32]
            out.append(rng.sample(pool, TOPK))
        else:
            out.append(rng.sample(range(N), TOPK))
    return out


def stream(seed: int, epochs: int = 2) -> list[int]:
    rng = random.Random(seed)
    facts: list[int] = []
    for _ in range(epochs):
        order = list(range(F // CL))
        rng.shuffle(order)
        for c in order:
            members = list(range(c * CL, c * CL + CL))
            rng.shuffle(members)
            facts.extend(members)
    return facts


def null_stream(queries: list[list[int]], seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    occ = [s for q in queries for s in q]
    rng.shuffle(occ)
    rows = [occ[i * TOPK : (i + 1) * TOPK] for i in range(len(queries))]
    for row in rows:
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
    half = len(queries) // 2
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


def evaluate(sel: list[list[int]]) -> dict[str, float]:
    cal_f, ev_f = stream(101), stream(202)
    cal = [sel[f] for f in cal_f]
    ev = [sel[f] for f in ev_f]
    used = sorted({s for q in cal for s in q})
    w = len(used)
    votes: dict[int, dict[int, int]] = {}
    for f in cal_f:
        for s in sel[f]:
            votes.setdefault(s, {}).setdefault(f // CL, 0)
            votes[s][f // CL] += 1
    owner = {s: min(v.items(), key=lambda kv: (-kv[1], kv[0]))[0] for s, v in votes.items()}
    order = sorted(used, key=lambda s: (owner[s], s)) + [s for s in range(N) if s not in owner]
    layouts = {"id": {s: s for s in range(N)}, "cluster": {s: i for i, s in enumerate(order)}}
    nulls = [null_stream(ev, seed) for seed in (1, 2, 3)]
    out: dict[str, float] = {"W": w}
    for rpp, rho in ((8, 1 / 16), (8, 1 / 4), (32, 1 / 16), (32, 1 / 4)):
        pages = max(1, round(rho * w / rpp))
        best = None
        for pos in layouts.values():
            actual = misses(ev, pos, rpp, pages)
            null = sum(misses(nq, pos, rpp, pages) for nq in nulls) / 3
            e = actual / null if null > 0 else float("nan")
            best = e if best is None or e < best else best
        out[f"E_best_R{rpp}_rho{rho:.4f}"] = round(best, 3)
    return out


def main() -> None:
    cases = [("random", 0.0), ("coherent", 0.1), ("coherent", 0.2), ("coherent", 0.3), ("coherent", 0.5),
             ("coherent", 1.0), ("packed_random", 0.0)]
    ref = None
    for kind, p in cases:
        res = evaluate(selections(kind, p, random.Random(11)))
        if ref is None:
            ref = res
        ratios = {k.replace("E_best", "E_ratio"): round(v / ref[k], 3) for k, v in res.items() if k.startswith("E_best")}
        print(json.dumps({"case": kind, "p_coherent": p, **res, **ratios,
                          "all_four_ratios_le_0.80": all(v <= 0.80 for v in ratios.values())}), flush=True)


if __name__ == "__main__":
    main()
