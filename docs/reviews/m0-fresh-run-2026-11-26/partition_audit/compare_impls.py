"""Compare partition_audit.py (auditor) with the implementer's studies/m0/registration/partition.py.

Part 1: N random made-up maps of varied shape, random seeds (never 400004).
Part 2: the real map of record and the real candidate list, with 200 non-registered seeds.
Both implementations are called in-process on the same inputs; the implementer's module is loaded
from its file path. Compared per case: derived integers, shuffled order of X and of each L_e,
part of every candidate cluster, group membership of every candidate cluster, per-evaluation
N_e / floor / a_e / p / clusters A,B / groups A,B, step-2 cluster counts, the group part printed
beside every non-candidate cluster.
Usage: python compare_impls.py IMPL_PARTITION_PY MAP_JSON CANDIDATES_JSON N_RANDOM OUT_JSON
"""
import importlib.util
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partition_audit as pa  # noqa: E402

REG = 400004
EV = pa.EVALS


def load_impl(path):
    spec = importlib.util.spec_from_file_location("impl_partition_under_audit", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def facts_mine(r):
    return {
        "ints": r["derived_integers"],
        "orders": r["shuffled_orders"],
        "cluster_part": r["cluster_part"],
        "cluster_group": {c: g for g, mem in r["groups"].items() for c in mem if c in r["cluster_part"]},
        "per_eval": {e: (v["N_e"], v["floor_half"], v["a_e"], v["p_e"], v["A_clusters"], v["B_clusters"],
                         v["A_groups"], v["B_groups"]) for e, v in r["per_evaluation"].items()},
        "step2": (r["step2_counts"]["A"], r["step2_counts"]["B"]),
        "noncand": r["noncandidate_cluster_group_part"],
    }


def facts_impl(r):
    return {
        "ints": r["derived_integers"],
        "orders": {"cross": r["step2"]["order"], **{e: r["counts"][e]["step3"]["order"] for e in EV}},
        "cluster_part": r["cluster_part"],
        "cluster_group": r["cluster_groups"],
        "per_eval": {e: (v["N_e"], v["half_floor"], v["step3"]["a_e"], v["step3"]["p_placed_in_A"], v["clusters_A"],
                         v["clusters_B"], v["groups_A"], v["groups_B"]) for e, v in r["counts"].items()},
        "step2": (r["step2"]["clusters_in_A"], r["step2"]["clusters_in_B"]),
        "noncand": {c: v["group_part"] for c, v in r["clusters_without_candidate"].items()},
    }


ALPH = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"


def rand_map(rng):
    """A made-up map. Shape parameters are drawn per map so that regimes vary."""
    lineage_eval = {}
    for e in EV:
        n = rng.choice([0, 1, 1, 2, 2, 3, 4, 5, 6, 8, 10, 14, 20])
        while sum(1 for x in lineage_eval if x.startswith(e + ".")) < n:
            nm = "".join(rng.choice(ALPH) for _ in range(rng.randint(1, 4)))
            lineage_eval[f"{e}.{nm}"] = e
    ids = sorted(lineage_eval)
    rng.shuffle(ids)  # input order varies
    if len(ids) < 2:
        return lineage_eval, [], [], ids[:1] if ids and rng.random() < 0.8 else []
    p_cand = rng.choice([0.3, 0.6, 0.8, 0.95, 1.0])
    cands = [x for x in ids if rng.random() < p_cand]
    nl = int(len(ids) * rng.choice([0, 0.1, 0.3, 0.6, 1.0]))
    links = []
    for _ in range(nl):
        a, b = rng.sample(ids, 2)
        if rng.random() < 0.5 and a.split(".")[0] == b.split(".")[0]:
            pass
        links.append((a, b))
    nb = int(len(ids) * rng.choice([0, 0.2, 0.5, 1.0, 1.5]))
    bp = []
    noncand = [x for x in ids if x not in set(cands)]
    for _ in range(nb):
        if noncand and rng.random() < 0.3:  # chain through a non-candidate lineage
            m = rng.choice(noncand)
            a, b = rng.sample(ids, 2)
            bp.append((a, m))
            bp.append((m, b))
        else:
            a, b = rng.sample(ids, 2)
            bp.append((a, b))
    if rng.random() < 0.2 and links:  # duplicates and reversed pairs
        links.append(tuple(reversed(links[0])))
    if rng.random() < 0.2 and bp:
        bp.append(bp[0])
    rng.shuffle(links)
    rng.shuffle(bp)
    return lineage_eval, links, bp, cands


def shape_flags(r):
    f = set()
    for g, mem in r["groups"].items():
        if r["group_w"][g] > 1:
            f.add("group_w>1")
        if len(mem) > r["group_w"][g]:
            f.add("group_holds_noncandidate_cluster")
        ne = sum(1 for e in EV if r["group_w_e"][g][e] > 0)
        if ne >= 3:
            f.add("cross_group_3plus_evals")
        for e in EV:
            if r["group_w_e"][g][e] > r["per_evaluation"][e]["floor_half"] and r["group_w_e"][g][e] > 0:
                f.add("group_w_e_gt_floor_half")
    for e in EV:
        n = r["per_evaluation"][e]["N_e"]
        if n in (1, 2):
            f.add("eval_with_1_or_2_clusters")
        if r["per_evaluation"][e]["a_e"] > r["per_evaluation"][e]["floor_half"]:
            f.add("a_e_gt_floor_half")
        if r["per_evaluation"][e]["A_clusters"] > r["per_evaluation"][e]["floor_half"]:
            f.add("A_overfull")
    if r["step2_counts"]["B"] < r["step2_counts"]["A"]:
        f.add("step2_B_lt_A")
    if any(len(m) > 1 for m in r["clusters"].values()):
        f.add("multi_lineage_cluster")
    return f


def compare(impl, le, links, bp, cands, seed):
    rm = pa.partition(le, links, bp, cands, seed)
    ri = impl.partition(le, links, bp, cands, seed)
    fm, fi = facts_mine(rm), facts_impl(ri)
    diff = [k for k in fm if fm[k] != fi[k]]
    return rm, diff, fm, fi


def main():
    impl_path, map_path, cand_path, n_random, out = sys.argv[1:6]
    impl = load_impl(impl_path)
    gen = random.Random(20261126)
    report = {"random": {"cases": 0, "disagreements": 0, "examples": [], "flags": {}},
              "real": {"cases": 0, "disagreements": 0, "examples": [], "seeds": []}}
    for i in range(int(n_random)):
        le, links, bp, cands = rand_map(gen)
        seed = gen.choice([gen.randrange(0, 10**6), gen.randrange(0, 2**63), -gen.randrange(1, 10**9)])
        if seed == REG:
            seed += 1
        rm, diff, fm, fi = compare(impl, le, links, bp, cands, seed)
        report["random"]["cases"] += 1
        for fl in shape_flags(rm):
            report["random"]["flags"][fl] = report["random"]["flags"].get(fl, 0) + 1
        if diff:
            report["random"]["disagreements"] += 1
            if len(report["random"]["examples"]) < 5:
                report["random"]["examples"].append({"i": i, "seed": seed, "diff": diff,
                                                     "mine": {k: fm[k] for k in diff},
                                                     "impl": {k: fi[k] for k in diff}})
    d = json.load(open(map_path, encoding="utf-8"))
    le = {k: v["evaluation"] for k, v in d["lineages"].items()}
    links = [tuple(x) for x in d["links"]]
    bp = [tuple(x) for x in d["borderline_pairs"]]
    cands = pa.load_candidates(cand_path)
    sg = random.Random(7)
    seeds = []
    while len(seeds) < 200:
        s = sg.randrange(1, 10**7)
        if s != REG and s not in seeds:
            seeds.append(s)
    assert REG not in seeds
    report["real"]["seeds"] = seeds
    part_dist = {}
    for s in seeds:
        rm, diff, fm, fi = compare(impl, le, links, bp, cands, s)
        report["real"]["cases"] += 1
        for e in EV:
            k = f"{e}:A{fm['per_eval'][e][4]}/B{fm['per_eval'][e][5]}"
            part_dist[k] = part_dist.get(k, 0) + 1
        if diff:
            report["real"]["disagreements"] += 1
            if len(report["real"]["examples"]) < 5:
                report["real"]["examples"].append({"seed": s, "diff": diff})
    report["real"]["part_size_tally_over_non_registered_seeds"] = dict(sorted(part_dist.items()))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("seeds",)} for k, v in report.items()},
                     indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
