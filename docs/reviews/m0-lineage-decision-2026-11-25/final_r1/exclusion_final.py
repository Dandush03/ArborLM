# ruff: noqa
"""Final R1 audit: are the dropped shapes excluded wherever the fix-4 set is built? Checks registered_v4(), the cluster table, the partition,
the capacity manifest, the survivors manifest, the fixtures directory, and what core.generate_pool sees unpatched (core.lineages_of('R1')).
Also applies this audit's own extra drop (graph_shortest_route_r6, pooled R-32 excess) to show the resulting cluster set and partition.
usage: python exclusion_final.py"""
import json, os, sys
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
sys.path.insert(0, W)
from studies.m0 import core
from studies.m0 import lineages_r1_fix4_clusters as c4
from studies.m0.lineages_r1_fix3_clusters import registered_v3

reg = c4.registered_v4()
ids = {x.id for x in reg}
dropped = set(c4.AUDIT4_DROPS) | set(c4.SECOND_STAGE_DROPS) | set(c4.REPAIRED.values())
print("registered_v4:", len(ids), sorted(ids))
print("v3 ids:", len(registered_v3()), " stage-1 drops:", len(c4.AUDIT4_DROPS), " stage-2 drops:", len(c4.SECOND_STAGE_DROPS), " replaced by _r6:", len(c4.REPAIRED))
print("dropped or replaced ids inside registered_v4:", sorted(ids & dropped))
ct = c4.cluster_table_v4()
print("cluster table:", len(ct), {k: sorted(x.id for x in v) for k, v in sorted(ct.items())})
print("dropped ids inside cluster table:", sorted({x.id for v in ct.values() for x in v} & dropped))
pr = c4.partition_readings_v4()
print("partition ids == registered ids:", set(pr["cluster_keys"]) == ids)
man = json.load(open(os.path.join(W, "studies/m0/manifests/r1_fix4_survivors.json")))
mids = set(man["surviving_shapes"])
print("survivors manifest == registered_v4:", mids == ids, "; manifest cluster members ∩ dropped:", sorted({i for v in man["cluster_members"].values() for i in v} & dropped))
st = {s["name"]: s["status"] for s in man["shapes"]}
print("manifest statuses:", dict(sorted(__import__("collections").Counter(st.values()).items())), "; SURVIVES set == registered_v4:", {k for k, v in st.items() if v == "SURVIVES"} == ids)
cap = json.load(open(os.path.join(W, "studies/m0/manifests/r1_fix4_capacity.json")))
txt = json.dumps(cap)
print("capacity manifest mentions of dropped/replaced ids:", sorted(d for d in dropped if f'"{d}"' in txt))
lv = json.load(open(os.path.join(W, "studies/m0/manifests/r1_fix4_levels.json")))
ltxt = json.dumps(lv)
print("levels manifest mentions of stage-1 drops:", sorted(d for d in c4.AUDIT4_DROPS if f'"{d}"' in ltxt), " of stage-2 drops:", sorted(d for d in c4.SECOND_STAGE_DROPS if d in ltxt))
fx = os.path.join(W, "studies/m0/fixtures")
r1fx = sorted(d for d in os.listdir(fx) if d.startswith("r1"))
print("R1 fixture directories:", r1fx, "; any fix4 fixture dir:", any("fix4" in d for d in r1fx))
print("r1_fix3 fixtures naming a dropped id:", sorted(f for f in os.listdir(os.path.join(fx, "r1_fix3")) if f.rsplit(".", 1)[0] in dropped))
print("core.lineages_of('R1') (what generate_pool uses unpatched):", [x.id for x in core.lineages_of("R1")])
print("overlap of core registry with registered_v4:", sorted({x.id for x in core.lineages_of("R1")} & ids))
mine = [x for x in reg if x.id != "R1.graph_shortest_route_r6"]
ct2 = c4.cluster_table_v4(mine)
pm2 = c4.partition_readings_v4(mine)["cluster_keys"]
print("after this audit's drop:", len(mine), "shapes,", len(ct2), "clusters; parts", {p: sorted(k for k, v in ct2.items() if pm2[v[0].id] == p) for p in "AB"})
