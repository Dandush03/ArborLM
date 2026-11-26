# ruff: noqa
"""Final C1 audit (fix 4), step 8: set and cluster consistency (R-12, R-20, R-26): dropped lineages and shapes excluded wherever the fix-4 set is built.
Imports the implementer's MODULES only to read their declared sets (no analysis module, no summary script). Checks:
 - lineages_c1_fix4_clusters.check_consistency() (theirs) and my own recomputation: current set = every written C1 id minus superseded (rev2, fix3, fix4),
   minus rev2 PROPOSED, minus fix-3 NOT_REGISTERED, minus DROPPED_AUDIT4, minus DROPPED_AFTER_REMEASURE; equals MEMBERS; equals my 27 SURVIVORS;
 - the manifests' id lists (survivors, clusters, capacity_raw, exec, levels_final_set, rules_final_set) equal the 27;
 - no dropped id appears in any of them; the two variants sit alone in their own clusters;
 - shapes, from 3,000 fresh items per level (my draw gen9311, item TEXT): fast_power_f4 always prints the first-assigned name (res), with the squaring + c step;
   sieve_marking_f4 always prints the accumulator (never the flag list);
 - core.REGISTRY (registered lineages) holds no fix-4 id.
Usage (cwd = worktree): uv run --locked python <this> GEN_DIR OUT_JSON
"""
import ast, gzip, json, os, re, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f1_draw import SURVIVORS

PRE = "Here is a Python program.\n\n"
SUF = "\n\nWhat exactly does it print? It prints a single line."


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    import studies.m0.lineages_c1_fix4 as f4
    import studies.m0.lineages_c1_fix4_clusters as cl
    from studies.m0.lineages_c1_fix3 import NOT_REGISTERED as NR3, SUPERSEDES3
    from studies.m0.lineages_c1_rev2 import PROPOSED, SUPERSEDES as SUP2
    import studies.m0.core as core
    out = {}
    out["their_check_consistency"] = cl.check_consistency()
    written = f4.all_written()
    sup = set(SUP2.values()) | set(SUPERSEDES3.values()) | set(f4.SUPERSEDES4.values())
    nr = {k for k in NR3 if "[" not in k}
    mine = sorted(i for i in written if i not in sup and i not in PROPOSED and i not in nr and i not in f4.DROPPED_AUDIT4 and i not in f4.DROPPED_AFTER_REMEASURE)
    members = sorted(m for ms in cl.MEMBERS.values() for m in ms)
    out["my_current_set"] = mine
    out["my_current_equals_members"] = mine == members
    out["my_current_equals_27"] = mine == sorted(SURVIVORS)
    out["n_members"], out["n_clusters"], out["n_clusters_wo_variants"] = len(members), len(cl.MEMBERS), len([c for c in cl.MEMBERS if c not in cl.VARIANT_CLUSTERS])
    out["variant_clusters"] = {c: list(cl.MEMBERS[c]) for c in cl.VARIANT_CLUSTERS}
    dropped = set(f4.DROPPED_AUDIT4) | set(f4.DROPPED_AFTER_REMEASURE) | set(f4.SUPERSEDES4.values())
    man = {}
    mdir = "studies/m0/manifests"
    def ids_of(name, d):
        if name == "c1_fix4_survivors":
            return sorted(d["surviving_lineages"]["list"])
        if name == "c1_fix4_clusters":
            return sorted(m for ms in d["members"].values() for m in ms)
        if name == "c1_fix4_capacity_raw":
            return sorted({r["lineage"] if "lineage" in r else r.get("lid") for r in d["rows"]})
        if name == "c1_fix4_exec":
            return sorted(d["lineages"]) if isinstance(d["lineages"], (list, dict)) else None
        if name in ("c1_fix4_levels_final_set",):
            return sorted(k for k in d if k.startswith("C1.")) or sorted(d.get("lineages", {}))
        if name == "c1_fix4_rules_final_set":
            return sorted(d["lineages"])
    for name in ("c1_fix4_survivors", "c1_fix4_clusters", "c1_fix4_capacity_raw", "c1_fix4_exec", "c1_fix4_levels_final_set", "c1_fix4_rules_final_set"):
        d = json.load(open(os.path.join(mdir, name + ".json")))
        try:
            ids = ids_of(name, d)
        except Exception as ex:
            ids = f"could not read: {type(ex).__name__} {ex}"
        man[name] = {"n": len(ids) if isinstance(ids, list) else None, "equals_27": ids == sorted(SURVIVORS) if isinstance(ids, list) else None,
                     "dropped_present": sorted(set(ids) & dropped) if isinstance(ids, list) else None,
                     "extra": sorted(set(ids) - set(SURVIVORS)) if isinstance(ids, list) else None, "missing": sorted(set(SURVIVORS) - set(ids)) if isinstance(ids, list) else None}
    out["manifests"] = man
    reg = {x.id for x in core.lineages_of("C1")}
    out["registry_has_fix4"] = sorted(i for i in reg if i in set(SURVIVORS) and i.endswith("_f4"))
    out["registry_c1_ids_in_survivors"] = sorted(reg & set(SURVIVORS))
    # shapes from text
    sh = {}
    for fid, base in (("C1.fast_power_f4", "fast_power_f3"), ("C1.sieve_marking_f4", "sieve_marking_f3")):
        rows = [json.loads(l) for l in gzip.open(os.path.join(gen, base + ".jsonl.gz"), "rt")]
        bad = 0
        for r in rows:
            t = ast.parse(r["q"][len(PRE):-len(SUF)])
            pn = t.body[-1].value.args[0]
            first = t.body[0].targets[0].id
            if fid == "C1.fast_power_f4":
                ok = isinstance(pn, ast.Name) and pn.id == first and len([s for s in t.body if isinstance(s, ast.Assign)]) == 4
            else:
                ok = isinstance(pn, ast.Name) and pn.id != first  # the flag list is assigned first; the accumulator is printed
            bad += not ok
        sh[fid] = {"items": len(rows), "other_shape": bad}
    out["one_shape_check"] = sh
    json.dump(out, open(outp, "w"), indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in out.items() if k != "my_current_set"}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
