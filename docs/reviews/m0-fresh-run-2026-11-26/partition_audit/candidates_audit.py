"""Rebuild the candidate list (section 4A stage 2) independently and compare with the implementer's.

candidate = on the survivor list of record AND every recorded stage-2 condition PASS (each condition's
own `result` read, not only `all_conditions`; the `map` condition checked as: lineage in the map of
record, its recorded cluster_id equals the cluster recomputed from the map's links, map hash equal)
AND not dropped by the fresh run (dropped.json: only the `lineage` and `evaluation` fields are read).
Usage: python candidates_audit.py SURVIVORS STAGE2 DROPPED MAP IMPL_CANDIDATES OUT_JSON
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partition_audit as pa  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    sp, s2p, dp, mp, ip, out = sys.argv[1:7]
    surv = json.load(open(sp, encoding="utf-8"))["evaluations"]
    s2 = json.load(open(s2p, encoding="utf-8"))
    dropped = json.load(open(dp, encoding="utf-8"))
    d, le, links, bp = pa.load_map(mp)
    clusters = pa.components(list(le), links)
    cl_of = {m: c for c, mem in clusters.items() for m in mem}
    map_sha = sha(mp)
    problems = []
    drop_ids = {}
    for row in dropped:
        drop_ids[row["lineage"]] = row["evaluation"]
    if len(drop_ids) != len(dropped):
        problems.append("duplicate in dropped")
    mine = {}
    for e in pa.EVALS:
        keep = []
        for x in surv[e]:
            if not x.startswith(e + "."):
                problems.append(f"survivor {x} under {e}")
            r = s2.get(x)
            if r is None:
                problems.append(f"no stage2 for {x}")
                continue
            ok = r["evaluation"] == e and r["all_conditions"] == "PASS"
            for k in ("levels_distinct", "pair_audited", "second_solver", "wording"):
                ok = ok and r[k]["result"] == "PASS"
            if x not in le:
                problems.append(f"{x} not in map"); ok = False
            elif r["map"]["cluster_id"] != cl_of[x] or r["map"]["map_sha256"] != map_sha:
                problems.append(f"{x} map condition mismatch"); ok = False
            if x in drop_ids:
                if drop_ids[x] != e:
                    problems.append(f"drop eval mismatch {x}")
                continue
            if ok:
                keep.append(x)
        mine[e] = sorted(keep)
    for x in drop_ids:
        if not any(x in surv[e] for e in pa.EVALS):
            problems.append(f"dropped {x} not a survivor")
    extra_s2 = sorted(set(s2) - {x for e in pa.EVALS for x in surv[e]})
    impl = json.load(open(ip, encoding="utf-8"))["candidates"]
    cmp = {e: {"mine": len(mine[e]), "impl": len(impl.get(e, [])), "equal": mine[e] == sorted(impl.get(e, [])),
               "only_mine": sorted(set(mine[e]) - set(impl.get(e, []))),
               "only_impl": sorted(set(impl.get(e, [])) - set(mine[e]))} for e in pa.EVALS}
    res = {"inputs_sha256": {"survivors": sha(sp), "stage2": s2p and sha(s2p), "dropped": sha(dp), "map": map_sha,
                             "impl_candidates": sha(ip)},
           "survivor_counts": {e: len(surv[e]) for e in pa.EVALS}, "n_dropped": len(drop_ids),
           "dropped_per_eval": {e: sorted(x for x, ee in drop_ids.items() if ee == e) for e in pa.EVALS},
           "stage2_entries_not_on_survivor_list": extra_s2, "problems": problems,
           "candidates": mine, "comparison": cmp,
           "candidate_clusters_per_eval": {e: len({cl_of[x] for x in mine[e]}) for e in pa.EVALS}}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, sort_keys=True); f.write("\n")
    print(json.dumps({k: v for k, v in res.items() if k != "candidates"}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
