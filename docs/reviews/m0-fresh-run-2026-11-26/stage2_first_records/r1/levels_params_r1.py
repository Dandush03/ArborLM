# ruff: noqa
"""M0 stage 2, R1: the stated level parameters read from the builders' STRUCTURED output on the stage-2 fixtures
(same seed and streams as stage2_check_r1.py). Confirms the auditor's reading of the builder code; computes no rule.
usage (from the implementation worktree root): PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this>"""
import hashlib, json, os, random, sys
from collections import deque
W = os.getcwd(); sys.path.insert(0, W)
from studies.m0.core import Retry
from studies.m0.lineages_r1_fix4_clusters import registered_v4
SEED = int.from_bytes(hashlib.sha256(b"400002|stage2-check|R1").digest()[:8], "big")
assert SEED == 14961762383913329776
def sub(*l): return int.from_bytes(hashlib.sha256("|".join([str(SEED), *l]).encode()).digest()[:8], "big")
def draw(lin, lv, rng, n):
    out = []
    while len(out) < n:
        try: out.append(lin.build(lv, rng))
        except Retry: pass
    return out
def hops(edges, a, b):
    adj = {}
    for x, y in edges: adj.setdefault(x, []).append(y); adj.setdefault(y, []).append(x)
    d = {a: 0}; q = deque([a])
    while q:
        u = q.popleft()
        for v in adj.get(u, []):
            if v not in d: d[v] = d[u] + 1; q.append(v)
    return d.get(b)
def params(lid, s):
    if "boolean" in lid: return {"lamps": s["lamps"], "presses": len(s["presses"]), "switches": len(s["switches"])}
    if "categories" in lid: return {"chain": len(s["chain"]), "rules_on_asked_verb": sum(1 for g, v, ok in s["rules"] if v == s["verb"])}
    if "compass" in lid: return {"commands": len(s["seq"])}
    if "threshold" in lid: return {"members": len(s["members"])}
    if "exchange" in lid: return {"rates": len(s["rates"]), "hops_x_y": hops([(p[1], p[3]) for p in s["rates"]], s["x"], s["y"])}
    if "knights" in lid: return {"people": len(s["people"])}
    if "grid" in lid: return {"cells": len(s["grid"]) * len(s["grid"][0]), "moves": len(s["moves"])}
    if "swap" in lid: return {"people": len(s["hold"]), "ops": len(s["ops"])}
    if "weekday" in lid: return {"links": len(s["links"]), "hops_anchor_ask": hops([(l[0], l[1]) for l in s["links"]], s["anchor"][0], s["ask"])}
    if "venn" in lid: return {"groups": len(s["groups"]), "ask": s["ask"], "total": s["total"]}
    raise KeyError(lid)
surv = json.load(open(os.path.join(W, "studies/m0/manifests/survivor_list_of_record.json")))["evaluations"]["R1"]
L = {x.id: x for x in registered_v4()}
res = {}
for lid in sorted(surv):
    res[lid] = []
    for lv in range(7):
        ps = [params(lid, b.structured) for b in draw(L[lid], lv, random.Random(sub(lid, str(lv))), 50)]
        row = {}
        for k in ps[0]:
            vals = [p[k] for p in ps]
            row[k] = sorted(set(vals)) if isinstance(vals[0], str) else {"min": min(vals), "max": max(vals), "mean": round(sum(vals) / len(vals), 2)}
        res[lid].append(row)
    print(lid)
    for lv, row in enumerate(res[lid]):
        print("  L%d" % lv, json.dumps(row, sort_keys=True))
json.dump(res, open(sys.argv[1], "w"), sort_keys=True, indent=2)
