# ruff: noqa
"""Final M1 audit: what remains under core.generate_pool AS WRITTEN if every failing lineage is dropped, iterated to a fixed point
(dropping lineages changes the family set, so family_partition's shuffle, the part sizes and the per-lineage demand D(n_part) change; repeat until no lineage fails).
Reading: per-lineage demand D(lineages in its own part) and, separately, D(lineages in the smaller part). Keys text, struct, a4key from capacity_M30000_v2.json."""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cap_summary_a5 import A4_MAP, D, stem
from fm1_common import survivors
from studies.m0.core import stream


def parts(ids, fam):
    fams = sorted({fam[i] for i in ids})
    r = stream(400004, "family-partition", "M1")
    sh = fams[:]
    r.shuffle(sh)
    pf = {f: ("A" if k < len(sh) // 2 else "B") for k, f in enumerate(sh)}
    return {i: pf[fam[i]] for i in ids}


if __name__ == "__main__":
    cap = json.load(open(sys.argv[1]))["results"]
    reg = survivors()
    fam = {i: reg[i].family for i in reg}
    cl = {i: next(c for c, m in A4_MAP.items() if stem(i) in m) for i in reg}
    out = {}
    for key in ("text", "struct", "a4key"):
        for reading in ("own_part", "smaller_part"):
            ids = sorted(reg)
            rounds = []
            while True:
                pt = parts(ids, fam)
                n = {p: sum(1 for i in ids if pt[i] == p) for p in "AB"}
                dem = {i: D(min(n.values()) if reading == "smaller_part" else n[pt[i]]) for i in ids}
                bad = sorted(i for i in ids if any(cap[i][str(L)][key]["n_eff"] < dem[i] for L in range(7)))
                rounds.append({"lineages": len(ids), "per_part": n, "demand": sorted(set(dem.values())), "failing": [stem(i) for i in bad]})
                if not bad:
                    break
                ids = [i for i in ids if i not in bad]
            cls = sorted({cl[i] for i in ids})
            out[f"{key}/{reading}"] = {"rounds": rounds, "lineages_left": [stem(i) for i in ids], "clusters_left": cls, "cluster_count": len(cls)}
            print(f"[{key}/{reading}] rounds: " + " -> ".join(f"{r['lineages']} lin {r['per_part']} D{r['demand']} drop {r['failing']}" for r in rounds))
            print(f"    left: {len(ids)} lineages, {len(cls)} clusters; lost clusters {sorted(set(cl.values()) - set(cls))}")
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
