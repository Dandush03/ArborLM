"""Seed-free shape facts of the real case, and every part size the rule can give.

Computes groups (with candidate clusters), w(g), w_e(g), X, L_e from the map of record and the
candidate list with partition_audit.py's structure code run on a dummy NON-registered seed (the
structure does not depend on the seed; only the orders do). Then enumerates EVERY permutation of
X and of each L_e (the shuffle can only pick a permutation) and applies steps 2 and 3, giving the
set of possible (A, B) cluster counts per evaluation and the fraction of permutations giving each
(the fraction is the probability only under a uniform shuffle; it is not a seed result).
Usage: python shape_facts.py MAP_JSON CANDIDATES_JSON OUT_JSON
"""
import itertools
import json
import os
import sys
from collections import Counter
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partition_audit as pa  # noqa: E402

DUMMY_SEED = 1  # not 400004; only the structure is read


def main():
    mp, cp, out = sys.argv[1:4]
    d, le, links, bp = pa.load_map(mp)
    cands = pa.load_candidates(cp)
    r = pa.partition(le, links, bp, cands, DUMMY_SEED)
    groups, w, we, X = r["groups"], r["group_w"], r["group_w_e"], r["cross_groups"]
    L = {e: sorted(g for g in groups if g not in X and we[g][e] > 0) for e in pa.EVALS}
    facts = {"n_clusters_all": r["n_clusters_all"], "n_candidate_clusters": r["n_candidate_clusters"],
             "n_groups_with_candidate": len(groups), "n_cross_groups": len(X), "per_eval": {},
             "cross_groups": {g: {"w": w[g], "w_e": we[g]} for g in X}}
    for e in pa.EVALS:
        pe = r["per_evaluation"][e]
        facts["per_eval"][e] = {
            "N_e": pe["N_e"], "floor_half": pe["floor_half"],
            "groups_with_candidate_cluster_in_e_sizes_w_e": sorted((we[g][e] for g in groups if we[g][e] > 0), reverse=True),
            "cross_groups_in_e": {g: we[g][e] for g in X if we[g][e] > 0},
            "local_groups_sizes": sorted((we[g][e] for g in L[e]), reverse=True),
        }
    # exhaustive enumeration
    tallies = {e: Counter() for e in pa.EVALS}
    joint = Counter()
    nx = 0
    for xo in itertools.permutations(X):
        nx += 1
        a = b = 0
        part = {}
        for g in xo:
            if b <= a:
                part[g] = "B"; b += w[g]
            else:
                part[g] = "A"; a += w[g]
        res = []
        for e in pa.EVALS:
            n, half = r["per_evaluation"][e]["N_e"], r["per_evaluation"][e]["floor_half"]
            a_e = sum(we[g][e] for g in X if part[g] == "A")
            c = Counter()
            perms = list(itertools.permutations(L[e])) if len(L[e]) <= 9 else None
            assert perms is not None
            for lo in perms:
                p = 0
                for g in lo:
                    if a_e + p + we[g][e] <= half:
                        p += we[g][e]
                c[a_e + p] += 1
            tot = sum(c.values())
            for k, v in c.items():
                tallies[e][(k, n - k)] += Fraction(v, tot)
            res.append(tuple(sorted(c)))
        joint[tuple((g, part[g]) for g in sorted(X))] += 1
    facts["n_permutations_of_X"] = nx
    facts["possible_A_B_per_eval"] = {e: {f"A{k[0]}/B{k[1]}": str(v / nx) for k, v in sorted(tallies[e].items())}
                                      for e in pa.EVALS}
    facts["distinct_step2_outcomes"] = len(joint)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(facts, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
