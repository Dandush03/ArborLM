# ruff: noqa
"""cache_eviction 'present' items: author's heuristic (item among the last cap requests) split by policy and answer."""
from collections import Counter
from studies.m0.core import build_item, stream
from studies.m0.lineages_r2_common import load_batch1
lin = [l for l in load_batch1() if l.id == "R2.cache_eviction"][0]
for lv in (1, 3, 5):
    r = stream(2025112502, "cache-split", str(lv))
    c = Counter()
    for i in range(6000):
        it = build_item(lin, lv, r, "A", "x")
        s = it.structured
        if s["ask"] != "present":
            continue
        g = "yes" if s["item"] in s["seq"][-s["cap"]:] else "no"
        c[(s["policy"], it.answer, g == it.answer)] += 1
    for pol in ("lru", "fifo"):
        tot = sum(v for k, v in c.items() if k[0] == pol)
        hit = sum(v for k, v in c.items() if k[0] == pol and k[2])
        by = {a: (sum(v for k, v in c.items() if k[0] == pol and k[1] == a and k[2]), sum(v for k, v in c.items() if k[0] == pol and k[1] == a)) for a in ("yes", "no")}
        print(f"L{lv} {pol}: acc={hit/tot:.3f} n={tot}  per key (hits/n): {by}")
