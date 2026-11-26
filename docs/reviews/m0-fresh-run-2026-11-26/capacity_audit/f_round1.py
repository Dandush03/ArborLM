"""Item 7: round-1 targets from the inputs of record and the demand formulas only (no draw, no capacity).
Reads candidate_list.json, partition_of_record.json, map_of_record.json (implementation worktree)."""
import collections, hashlib, json, sys
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
P = {"cand": f"{W}/studies/m0/registration/candidate_list.json", "part": f"{W}/studies/m0/manifests/partition_of_record.json",
     "map": f"{W}/studies/m0/manifests/map_of_record.json"}
for k, p in P.items():
    print(k, hashlib.sha256(open(p, "rb").read()).hexdigest(), p)
cand = json.load(open(P["cand"]))["candidates"]
part = json.load(open(P["part"]))["cluster_part"]
mp = json.load(open(P["map"]))
cl_of = {x: c["cluster_id"] for c in mp["clusters"] for x in c["members"]}
cd = lambda a, b: -(-a // b)
D = lambda g: 10 * (cd(4000, g) + cd(20000, g) + 100)
DL = lambda g, k: 10 * (cd(cd(4000, g), k) + cd(cd(20000, g), k) + cd(100, k))
tot_cells = 0
tot_worst = 0
tot_reach = 0
rows = []
for e in ("R1", "R2", "M1", "C1"):
    for p in ("A", "B"):
        cls = collections.defaultdict(list)
        for x in cand[e]:
            if part[cl_of[x]] == p:
                cls[cl_of[x]].append(x)
        G = len(cls)
        ks = collections.Counter(len(v) for v in cls.values())
        nl = sum(len(v) for v in cls.values())
        line = f"{e}{p}: G={G} lineages={nl} D(G)={D(G) if G else '-'}"
        for k in sorted(ks):
            t = DL(G, k)
            line += f" | k={k} x{ks[k]} clusters: D_lin={t}, budget={40*t+1000}"
            tot_cells += 7 * k * ks[k]
            tot_worst += 7 * k * ks[k] * (40 * t + 1000)
            tot_reach += 7 * k * ks[k] * t
        print(line)
        rows.append({"part": e + p, "G": G, "D_G": D(G) if G else None, "k_counts": dict(ks),
                     "D_lin": {k: DL(G, k) for k in ks}, "clusters": {c: sorted(v) for c, v in sorted(cls.items())}})
print("round-1 cells", tot_cells, "| attempts if every cell reaches its target with no discard", tot_reach,
      "| attempts if every cell runs its whole budget", tot_worst)
print("largest possible target in any later round: D_lin(1,1) = D(1) =", DL(1, 1), "budget", 40 * DL(1, 1) + 1000)
json.dump(rows, open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_audit_20261126/deliver/f_round1.json", "x"), indent=1)
