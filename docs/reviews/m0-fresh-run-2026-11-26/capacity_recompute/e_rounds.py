"""My own rounds and fixed point (section 4A stage 4), from my counts only; compare with the record.

usage: e_rounds.py <results.jsonl> [<results.jsonl> ...]
If a round needs a cell (lineage, level, target) that is not yet counted, the missing cells are written to
work/missing_cells_<n>.json and the script stops (exit 3) so they can be counted with b_run_cells.py.
"""
import json
import os
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

S = rc.SCR
res = {}
for f in sys.argv[1:]:
    for line in open(f):
        r = json.loads(line)
        res[(r["lineage"], r["level"], r["target"])] = r

parts = rc.round1_parts()
missing = []
outcome = {}
log = []
for (e, p), cls0 in sorted(parts.items()):
    Sset = {lid for v in cls0.values() for lid in v}
    member = {lid: c for c, v in cls0.items() for lid in v}
    rnd = 0
    rounds = []
    while True:
        rnd += 1
        cls = {}
        for lid in sorted(Sset):
            cls.setdefault(member[lid], []).append(lid)
        G = len(cls)
        if G == 0:
            break
        DG = rc.D(G)
        fail = {}
        info = {"round": rnd, "G": G, "D_G": DG, "clusters": {}}
        stop = False
        for c, lids in sorted(cls.items()):
            k = len(lids)
            T = rc.D_lin(G, k)
            ci = {"k": k, "D_lin": T, "lineages": {}}
            passed_i = []
            for lid in lids:
                bad = []
                for lv in rc.LEVELS:
                    r = res.get((lid, lv, T))
                    if r is None:
                        missing.append([lid, lv, T])
                        stop = True
                        continue
                    if r["count"] < T:
                        bad.append(("own_demand", lv, r["count"], T, r["ended"]))
                    if r["solver_disagreements"]:
                        bad.append(("solver", lv, r["solver_disagreements"]))
                ci["lineages"][lid] = bad
                if bad:
                    fail[lid] = bad
                elif not any(b[0] == "own_demand" for b in bad):
                    passed_i.append(lid)
            # (ii): only on a cluster all of whose lineages pass (i)
            own_ok = [lid for lid in lids if not any(b[0] == "own_demand" for b in ci["lineages"][lid])]
            if not stop and len(own_ok) == len(lids):
                unions = {}
                for lv in rc.LEVELS:
                    u = set()
                    for lid in lids:
                        u |= rc.read_keys(lid, lv, T)
                    unions[lv] = len(u)
                ci["union_by_level"] = unions
                ci["union_slack_by_level"] = {lv: unions[lv] - DG for lv in rc.LEVELS}
                if min(unions.values()) < DG:
                    for lid in lids:
                        fail.setdefault(lid, []).append(("union", min(unions, key=unions.get), min(unions.values()), DG))
            info["clusters"][c] = ci
        if stop:
            break
        info["removed"] = sorted(fail)
        info["reasons"] = {k: v for k, v in sorted(fail.items())}
        rounds.append(info)
        if not fail:
            break
        Sset -= set(fail)
    outcome[f"{e}{p}"] = {"rounds": rounds, "registered": sorted(Sset), "G_registered": len({member[x] for x in Sset}),
                          "complete": not missing}
if missing:
    n = 1
    while os.path.exists(f"{S}/work/missing_cells_{n}.json"):
        n += 1
    json.dump(sorted(missing), open(f"{S}/work/missing_cells_{n}.json", "x"))
    print(f"MISSING {len(missing)} cells -> work/missing_cells_{n}.json:", sorted({(m[0], m[2]) for m in missing}))
    sys.exit(3)

rec = rc.load_json("studies/m0/manifests/capacity_of_record.json")
summary = {}
for key, o in outcome.items():
    e, p = key[:2], key[2]
    rp = rec["parts"][e][p]
    rec_reg = sorted(x for v in rp["registered"].values() for x in v)
    rec_removed = sorted(x["lineage"] for x in rp["removed"])
    # round-by-round comparison: G, D_G, per cluster k, D_lin, union_by_level, removed
    rcmp = []
    for i, ro in enumerate(o["rounds"]):
        rr = rp["rounds"][i] if i < len(rp["rounds"]) else None
        if rr is None:
            rcmp.append({"round": i + 1, "record": "absent"})
            continue
        d = {"round": i + 1, "G": (rr["G"], ro["G"]), "D_G": (rr["D_G"], ro["D_G"])}
        cl_diff = []
        for c, ci in ro["clusters"].items():
            rc_ = rr["clusters"].get(c)
            if rc_ is None:
                cl_diff.append((c, "cluster absent in record round"))
                continue
            if (rc_["k"], rc_["D_lin"]) != (ci["k"], ci["D_lin"]):
                cl_diff.append((c, "k/D_lin", (rc_["k"], rc_["D_lin"]), (ci["k"], ci["D_lin"])))
            ru = {int(k): v for k, v in rc_.get("union_by_level", {}).items()} if rc_.get("union_evaluated") else None
            mu = ci.get("union_by_level")
            if ru != mu:
                cl_diff.append((c, "union", ru, mu))
            # per-cell
            for lid in ci["lineages"]:
                for lv in rc.LEVELS:
                    x = rc_["lineages"][lid][str(lv)]
                    m = res[(lid, lv, ci["D_lin"])]
                    for f in ("target", "count", "attempts", "ended", "solver_disagreements"):
                        if x[f] != m[f]:
                            cl_diff.append((c, lid, lv, f, x[f], m[f]))
        extra = sorted(set(rr["clusters"]) - set(ro["clusters"]))
        if extra:
            cl_diff.append(("clusters only in record", extra))
        d["cluster_diffs"] = cl_diff
        d["cells_compared"] = sum(7 * len(ci["lineages"]) for ci in ro["clusters"].values())
        rcmp.append(d)
    if len(rp["rounds"]) != len(o["rounds"]):
        rcmp.append({"n_rounds": (len(rp["rounds"]), len(o["rounds"]))})
    summary[key] = {"registered_mine": o["registered"], "registered_equal": rec_reg == o["registered"],
                    "removed_mine": sorted(set(x for v in parts[(e, p)].values() for x in v) - set(o["registered"])),
                    "removed_record": rec_removed, "G_registered": (rp["G_registered"], o["G_registered"]),
                    "n_rounds": (len(rp["rounds"]), len(o["rounds"])), "round_compare": rcmp}
json.dump({"outcome": outcome, "compare": summary}, open(f"{S}/deliver/e_rounds.json", "x"), indent=1, default=str)
for key, s in summary.items():
    print(key, "registered equal:", s["registered_equal"], "n registered:", len(s["registered_mine"]),
          "G (record, mine):", s["G_registered"], "rounds (record, mine):", s["n_rounds"], "removed mine:", s["removed_mine"],
          "removed record:", s["removed_record"])
    for d in s["round_compare"]:
        print("   ", json.dumps(d, default=str))
