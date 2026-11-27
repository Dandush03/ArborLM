"""Checks on map_of_record.json (no rate, no part): (a) format rules; (b) within-evaluation merges made only through another
evaluation (section 3 item 2, transitive merging); (c) every id of the survivor list of record is a node (presence only; the
list is not used for any judgement). Usage: python e05_checks.py <deliver_dir> <survivor_list_json>"""
import json, sys, os
D, S = sys.argv[1], sys.argv[2]
raw = open(os.path.join(D, 'map_of_record.json'), encoding='utf-8').read()
m = json.loads(raw)
assert raw == json.dumps(m, sort_keys=True, indent=2, ensure_ascii=False) + "\n", "not canonical"
assert set(m) == {"lineages", "links", "borderline_pairs", "clusters", "groups"}
for p in m["links"] + m["borderline_pairs"]:
    assert len(p) == 2 and p[0] < p[1], p
assert m["links"] == sorted(m["links"]) and m["borderline_pairs"] == sorted(m["borderline_pairs"])
assert not set(map(tuple, m["links"])) & set(map(tuple, m["borderline_pairs"]))
ids = set(m["lineages"]); seen = []
for c in m["clusters"]:
    assert c["members"] == sorted(c["members"]) and c["cluster_id"] == c["members"][0]
    seen += c["members"]
assert sorted(seen) == sorted(ids) and len(seen) == len(set(seen))
assert all(g == sorted(g) for g in m["groups"]) and m["groups"] == sorted(m["groups"])
assert sorted(x for g in m["groups"] for x in g) == sorted(c["cluster_id"] for c in m["clusters"])
assert all(set(v) == {"evaluation"} for v in m["lineages"].values())
print("format checks: OK")
ev = {i: v["evaluation"] for i, v in m["lineages"].items()}
cl = {x: c["cluster_id"] for c in m["clusters"] for x in c["members"]}
for e in ("R1", "R2", "M1", "C1"):
    par = {i: i for i in ids if ev[i] == e}
    def f(x):
        while par[x] != x: x = par[x]
        return x
    for a, b in m["links"]:
        if ev[a] == e and ev[b] == e:
            ra, rb = f(a), f(b)
            if ra != rb: par[max(ra, rb)] = min(ra, rb)
    local = {}
    for i in par: local.setdefault(f(i), []).append(i)
    byglobal = {}
    for root, mem in local.items():
        byglobal.setdefault(cl[root], []).append(min(mem))
    joined = {g: sorted(v) for g, v in byglobal.items() if len(v) > 1}
    print(f"{e}: own-links components {len(local)}; global clusters holding {e} {len(byglobal)}; joined only through another evaluation: {joined if joined else 'none'}")
sv = json.load(open(S))["evaluations"]
miss = {e: sorted(set(v) - ids) for e, v in sv.items()}
print("survivor-list ids absent from the map:", miss, " (counts on the list:", {e: len(v) for e, v in sv.items()}, ")")
