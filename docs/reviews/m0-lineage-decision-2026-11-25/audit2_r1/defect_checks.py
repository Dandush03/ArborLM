# ruff: noqa
"""Checks that the ORIGINAL defects of each revised shape are gone, on the auditor's rendered items, plus new surface checks.
Usage: defect_checks.py ITEMSDIR"""
import gzip, json, os, re, sys
from collections import Counter, defaultdict

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
from studies.m0.vocab import COLOURS  # word list only

d = sys.argv[1]
L = lambda lid, mode="reg": [json.loads(x) for x in gzip.open(os.path.join(d, f"{lid}.{mode}.jsonl.gz"), "rt")]

rows = L("equivalence_classes_r2")
verb = sum(1 for r in rows if any({r["s"]["x"], r["s"]["y"]} == set(p) for p in r["s"]["same"] + r["s"]["different"]))
unm = sum(1 for r in rows if any(cnt == 0 for cnt in (r["q"].split(" Is ")[0].count(r["s"]["x"]), r["q"].split(" Is ")[0].count(r["s"]["y"]))))
print(f"equivalence_classes_r2: asked pair stated verbatim {verb}/{len(rows)}; asked entity never mentioned in the body {unm}/{len(rows)}; keys {Counter(r['a'] for r in rows)}")

rows = L("spatial_grid_walk_r2")
print(f"spatial_grid_walk_r2: column convention stated in {sum('(column 1 is the westernmost)' in r['q'] for r in rows)}/{len(rows)}")

rows = L("containers_stack_piles_r3")
bad = [r["id"] for r in rows if any(b in COLOURS for p in r["s"]["initial"].values() for b in p)]
print(f"containers_stack_piles_r3: items with a block named by a colour word {len(bad)}/{len(rows)}")

rows = L("boolean_lights_r2")
c = Counter("every other lamp is off" in r["q"] for r in rows)
c2 = Counter("the rest are off" in r["q"] for r in rows)
print(f"boolean_lights_r2: 'every other lamp is off' wording in {c[True]}/{len(rows)}; 'the rest are off' in {c2[True]}; asked lamp never toggled: {sum(1 for r in rows if not any(r['s']['ask'] in r['s']['switches'][x] for x in r['s']['presses']))}")
tog = defaultdict(Counter)
for r in rows:
    n = sum(1 for x in r["s"]["presses"] if r["s"]["ask"] in r["s"]["switches"][x])
    tog[r["level"]][min(n, 3)] += 1
print("   toggles of the asked lamp (3 = 3+), per level:", {lv: dict(sorted(v.items())) for lv, v in sorted(tog.items())})

rows = L("graph_shortest_route_r2")
import heapq
hops = defaultdict(Counter)
for r in rows:
    g = defaultdict(list)
    for a, b, w in r["s"]["roads"]:
        g[a].append((b, w)); g[b].append((a, w))
    S, T = r["s"]["start"], r["s"]["end"]
    # all shortest paths: min hops among shortest
    dist = {S: (0, 0)}
    h = [(0, 0, S)]
    while h:
        dd, hh, u = heapq.heappop(h)
        if (dd, hh) > dist[u]:
            continue
        for b, w in g[u]:
            nd = (dd + w, hh + 1)
            if b not in dist or nd < dist[b]:
                dist[b] = nd
                heapq.heappush(h, (nd[0], nd[1], b))
    hops[r["level"]][min(dist[T][1], 4)] += 1
print("graph_shortest_route_r2: roads on the shortest route (fewest among shortest; 4 = 4+), per level:", {lv: dict(sorted(v.items())) for lv, v in sorted(hops.items())})

rows = L("categories_follow_r2")
kk = defaultdict(Counter)
for r in rows:
    kk[r["s"]["kind"]][r["a"]] += 1
print("categories_follow_r2: key by question kind:", {k: dict(v) for k, v in kk.items()})

rows = L("instant_runoff_r2")
dup = sum(1 for r in rows if len({tuple(b[1]) for b in r["s"]["ballots"]}) < len(r["s"]["ballots"]))
print(f"instant_runoff_r2: items listing the same ranking in two or more separate groups {dup}/{len(rows)}")

rows = L("kinship_ancestor_r3")
print(f"kinship_ancestor_r3: answer is the parentless root {sum(1 for r in rows if r['a'] not in r['s']['parent'])}/{len(rows)}; answer is the asked person's parent {sum(1 for r in rows if r['s']['parent'][r['s']['child']] == r['a'])}")
rows = L("kinship_ancestor_r3", "unc")
print(f"   (unconditioned same) root {sum(1 for r in rows if r['a'] not in r['s']['parent'])}/{len(rows)}")

rows = L("categories_default_exceptions_r3")
c = Counter(len({x[2] for x in r["s"]["rules"] if x[1] == r["s"]["verb"]}) for r in rows)
print(f"categories_default_exceptions_r3: number of distinct signs among rules about the asked verb {dict(c)}")

rows = L("conditional_threshold_rule_r3")
print(f"conditional_threshold_rule_r3: keys {Counter(r['a'] for r in rows)}; items with any veto wording {sum('veto' in r['q'] for r in rows)}")

rows = L("elimination_bracket_r3")
print(f"elimination_bracket_r3: items mentioning a rating {sum('rating' in r['q'] for r in rows)}; ask types {Counter(r['s']['ask'][0] for r in rows)}")

rows = L("containers_queue_line_r2")
print(f"containers_queue_line_r2: asked position distribution {Counter(r['s']['ask'][1] for r in rows)}; items with a front-to-back op {sum(any(o[0]=='front_to_back' for o in r['s']['ops']) for r in rows)}/{len(rows)}")

rows = L("kinship_descendants_r3")
print(f"kinship_descendants_r3: root among options {sum(1 for r in rows if any(p not in r['s']['parent'] for p in r['s']['candidates']))}; ask types {Counter(r['s']['ask'] for r in rows)}")
