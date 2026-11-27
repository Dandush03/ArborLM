"""Independent audit implementation of the ADR-0033 addendum 1 cluster partition.

Written from the approved text (commit 2c944302, section 4 steps 1-5 and
section 4A stage 3) only, by the auditor, before reading any implementer,
drafter or reviewer partition code. Standard library only; CPython 3.12.

Rule implemented (decided option, section 13 items 5, 9, 17, 20):
  * global clusters = connected components of the lineage graph over `links`
    (all lineages, candidate or not); identity = min id (code-point order).
  * groups = connected components of the cluster graph whose edges are the
    borderline pairs between two different clusters; every cluster is a node
    (a cluster with no candidate lineage passes a group on, takes no part).
  * only groups with >=1 candidate cluster are placed; group identity = the
    smallest identity among its clusters that have a candidate lineage.
  * w(g) = # candidate clusters in g; w_e(g) = # clusters in g with a candidate
    lineage in e.  X = groups whose candidate lineages span >=2 evaluations,
    L_e = groups whose candidate lineages are all in e.
  * step 2: X sorted, shuffled with stream(seed,'cluster-partition','cross');
    walk from index 0; to B if B_so_far <= A_so_far (counted in w) else A.
  * step 3: for e in R1,R2,M1,C1: N_e = # clusters with candidate lineage in e;
    a_e = sum w_e(g) for g in X placed in A; L_e sorted, shuffled with
    stream(seed,'cluster-partition',e); walk; to A iff a_e+p+w_e(g) <= N_e//2
    (then p += w_e(g)), otherwise B and the walk continues.

CLI: --map MAP.json --candidates CANDS.json --seed INT --out OUT.json
The seed 400004 is refused unless --allow-registered-seed is given (the audit
never passes it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys

EVALS = ("R1", "R2", "M1", "C1")
LABEL = "cluster-partition"
REGISTERED_SEED = 400004


def derived_int(seed: int, *labels: str) -> int:
    text = "|".join([str(seed), *labels])
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def stream(seed: int, *labels: str) -> random.Random:
    return random.Random(derived_int(seed, *labels))


def shuffled(ids, seed: int, *labels: str) -> list[str]:
    lst = sorted(ids)
    rng = stream(seed, *labels)
    rng.shuffle(lst)
    # cross-check against an explicit Fisher-Yates using the same primitive
    lst2 = sorted(ids)
    rng2 = stream(seed, *labels)
    for i in range(len(lst2) - 1, 0, -1):
        j = rng2._randbelow(i + 1)
        lst2[i], lst2[j] = lst2[j], lst2[i]
    assert lst == lst2, "shuffle mismatch"
    return lst


class DSU:
    def __init__(self, items):
        self.p = {x: x for x in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if rb < ra:
                ra, rb = rb, ra
            self.p[rb] = ra


def components(nodes, edges):
    d = DSU(nodes)
    for a, b in edges:
        d.union(a, b)
    comp: dict[str, list[str]] = {}
    for n in nodes:
        comp.setdefault(d.find(n), []).append(n)
    return {min(v): sorted(v) for v in comp.values()}


def partition(lineage_eval: dict[str, str], links, borderline, candidates, seed: int):
    """lineage_eval: lineage id -> evaluation. candidates: iterable of lineage ids."""
    cands = set(candidates)
    for c in cands:
        if c not in lineage_eval:
            raise ValueError(f"candidate not in map: {c}")
    for a, b in list(links) + list(borderline):
        if a not in lineage_eval or b not in lineage_eval:
            raise ValueError(f"pair names unknown lineage: {a},{b}")
    clusters = components(list(lineage_eval), links)  # id -> members
    cl_of = {m: cid for cid, mem in clusters.items() for m in mem}
    cand_evals = {cid: sorted({lineage_eval[m] for m in mem if m in cands}) for cid, mem in clusters.items()}
    cand_clusters = sorted(cid for cid, ev in cand_evals.items() if ev)
    cedges = [(cl_of[a], cl_of[b]) for a, b in borderline if cl_of[a] != cl_of[b]]
    groups_all = components(list(clusters), cedges)  # keyed by min cluster id
    groups = {}
    group_of_cluster = {}
    for mem in groups_all.values():
        cmem = [c for c in mem if cand_evals[c]]
        if not cmem:
            for c in mem:
                group_of_cluster[c] = None
            continue
        gid = min(cmem)
        groups[gid] = mem
        for c in mem:
            group_of_cluster[c] = gid
    w = {g: sum(1 for c in mem if cand_evals[c]) for g, mem in groups.items()}
    we = {g: {e: sum(1 for c in mem if e in cand_evals[c]) for e in EVALS} for g, mem in groups.items()}
    gevals = {g: sorted({e for c in mem for e in cand_evals[c]}) for g, mem in groups.items()}
    X = [g for g in groups if len(gevals[g]) >= 2]
    L = {e: [g for g in groups if gevals[g] == [e]] for e in EVALS}
    for g in groups:
        assert len(gevals[g]) >= 1
        assert all(e in EVALS for e in gevals[g]), gevals[g]
    part: dict[str, str] = {}
    out_orders = {}
    xo = shuffled(X, seed, LABEL, "cross")
    out_orders["cross"] = xo
    a_cnt = b_cnt = 0
    for g in xo:
        if b_cnt <= a_cnt:
            part[g] = "B"
            b_cnt += w[g]
        else:
            part[g] = "A"
            a_cnt += w[g]
    per_eval = {}
    for e in EVALS:
        n_e = sum(1 for c in cand_clusters if e in cand_evals[c])
        half = n_e // 2
        a_e = sum(we[g][e] for g in X if part[g] == "A")
        lo = shuffled(L[e], seed, LABEL, e)
        out_orders[e] = lo
        p = 0
        for g in lo:
            if a_e + p + we[g][e] <= half:
                part[g] = "A"
                p += we[g][e]
            else:
                part[g] = "B"
        A_cl = sum(1 for c in cand_clusters if e in cand_evals[c] and part[group_of_cluster[c]] == "A")
        B_cl = n_e - A_cl
        A_gr = sum(1 for g in groups if we[g][e] > 0 and part[g] == "A")
        B_gr = sum(1 for g in groups if we[g][e] > 0 and part[g] == "B")
        per_eval[e] = {"N_e": n_e, "floor_half": half, "a_e": a_e, "p_e": p,
                       "A_clusters": A_cl, "B_clusters": B_cl, "A_groups": A_gr, "B_groups": B_gr,
                       "L_e_size": len(L[e])}
    cluster_part = {c: part[group_of_cluster[c]] for c in cand_clusters}
    noncand_group_part = {c: (part[group_of_cluster[c]] if group_of_cluster[c] else None)
                          for c in sorted(clusters) if not cand_evals[c]}
    # assertions of section 4 item 4
    for g, mem in groups.items():
        assert len({cluster_part[c] for c in mem if cand_evals[c]}) == 1
    return {
        "seed": seed,
        "derived_integers": {lab: derived_int(seed, LABEL, lab) for lab in ("cross", *EVALS)},
        "shuffled_orders": out_orders,
        "cluster_part": cluster_part,
        "group_part": {g: part[g] for g in sorted(groups)},
        "groups": {g: groups[g] for g in sorted(groups)},
        "group_w": {g: w[g] for g in sorted(groups)},
        "group_w_e": {g: we[g] for g in sorted(groups)},
        "cross_groups": sorted(X),
        "noncandidate_cluster_group_part": noncand_group_part,
        "per_evaluation": per_eval,
        "step2_counts": {"A": a_cnt, "B": b_cnt},
        "n_clusters_all": len(clusters),
        "n_candidate_clusters": len(cand_clusters),
        "clusters": clusters,
    }


def load_map(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    lineage_eval = {k: v["evaluation"] for k, v in d["lineages"].items()}
    return d, lineage_eval, [tuple(x) for x in d["links"]], [tuple(x) for x in d["borderline_pairs"]]


def load_candidates(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, list):
        return list(d)
    if isinstance(d, dict):
        if "candidates" in d:
            c = d["candidates"]
            if isinstance(c, list):
                return list(c)
            if isinstance(c, dict):
                return [x for e in EVALS for x in c.get(e, [])]
        if all(k in EVALS for k in d):
            return [x for e in EVALS for x in d.get(e, [])]
    raise ValueError("unrecognised candidate file format")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-registered-seed", action="store_true")
    a = ap.parse_args(argv)
    if a.seed == REGISTERED_SEED and not a.allow_registered_seed:
        sys.exit("refusing registered seed 400004")
    d, le, links, bp = load_map(a.map)
    cands = load_candidates(a.candidates)
    res = partition(le, links, bp, cands, a.seed)
    # consistency with the map's own clusters/groups fields
    if "clusters" in d:
        given = {c["cluster_id"]: sorted(c["members"]) for c in d["clusters"]}
        res["map_clusters_field_matches"] = given == res["clusters"]
    if "groups" in d:
        mine = sorted(sorted(v) for v in components(list(res["clusters"]),
                      [(x, y) for x, y in ((next(k for k, m in res["clusters"].items() if p in m),
                                            next(k for k, m in res["clusters"].items() if q in m)) for p, q in bp) if x != y]).values())
        res["map_groups_field_matches"] = sorted(sorted(g) for g in d["groups"]) == mine
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
