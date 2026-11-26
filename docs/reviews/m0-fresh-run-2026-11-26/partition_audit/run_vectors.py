"""Run partition_audit.py on vectors V1-V8 and compare with the drafter's printed results.

The V1-V8 input maps are COPIED from the drafter's partition_vector_rev4.py
(SHA-256 3b28dbbb1fc9748bb0ce77c7680df7fad1a8c12f509d2024e4d8fd61e176527f); nothing
else of that script is imported or used. Expected results are PARSED from its printed output
partition_vector_rev4.out.txt (c4fbae366257b5afe2ddf50e96588a1a06330d49f7456d24b5cc2909ced1ec8d),
sections 1, 2 and 3 (the decided option only).
Seed 400004 is used here as the text's test vectors use it: made-up identities only.
Usage: python run_vectors.py OUT_TXT_PATH
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partition_audit as pa  # noqa: E402


def _m(spec):
    return {t.rstrip("!"): not t.endswith("!") for t in spec.split()}


VECTORS = {
    "V1": (_m("R1.alpha R1.beta R1.gamma R1.delta! R1.epsilon R1.zeta R2.alpha R2.beta R2.gamma R2.delta R2.epsilon "
              "M1.alpha M1.beta M1.gamma M1.delta C1.alpha C1.beta C1.gamma C1.delta C1.epsilon!"),
           [("R1.alpha", "R1.beta"), ("C1.alpha", "R2.alpha"), ("C1.beta", "R2.beta"), ("M1.alpha", "R2.gamma"),
            ("C1.gamma", "M1.beta"), ("R1.gamma", "R1.delta"), ("C1.epsilon", "R1.epsilon")], []),
    "V2": (_m("R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c C1.a C1.b C1.c C1.d C1.e C1.f! C1.g!"),
           [("C1.a", "R2.a"), ("C1.b", "R2.b"), ("C1.c", "R2.c"), ("C1.d", "M1.a"), ("C1.e", "R1.a"), ("C1.f", "C1.g")], []),
    "V3": (_m("R1.e R2.e C1.e! R1.a M1.a C1.a C1.b C1.c C1.d"),
           [("R1.e", "R2.e"), ("C1.e", "R1.e"), ("R1.a", "M1.a")], []),
    "V4": (_m("R1.p R1.q R1.r R1.s R2.p! R2.q R2.r M1.p M1.q C1.p C1.q"),
           [("R1.p", "R2.p"), ("R1.q", "R2.p"), ("R2.q", "C1.p"), ("M1.p", "C1.q")], []),
    "V5": (_m("C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c R2.f R2.z0"),
           [("C1.a", "R2.a"), ("C1.b", "M1.b"), ("C1.c", "R2.c"), ("C1.d", "R1.d"), ("C1.e", "R1.e"), ("C1.f", "R2.f"),
            ("C1.g", "R1.g")], []),
    "V6": (_m("R1.a R1.b R1.c R1.d R1.e R1.f R1.g R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c M1.d "
              "C1.a C1.b C1.c C1.d C1.x!"),
           [("C1.a", "R2.a"), ("M1.a", "R2.b"), ("C1.b", "R2.c")],
           [("R1.a", "C1.x"), ("C1.x", "R1.b"), ("R1.b", "C1.a"), ("R1.c", "R1.d"), ("M1.b", "R2.b")]),
    "V7": (_m("R1.a R1.b R1.c R1.d C1.x!"), [], [("R1.a", "C1.x"), ("C1.x", "R1.b")]),
    "V8": (_m("R1.a R1.b R1.c R1.d R1.e R1.f"), [], [("R1.a", "R1.b"), ("R1.b", "R1.c")]),
}


def parse_expected(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    ints, exp = {}, {}
    sec = None
    cur = None
    for ln in lines:
        if ln.startswith("== "):
            sec = ln.split()[1]
            cur = None
            continue
        s = ln.strip()
        if sec == "1." and "->" in s:
            k, v = s.split("->")
            ints[ast.literal_eval(k.strip()).split("|")[-1]] = int(v)
        elif sec == "2." and s[:1] == "V":
            name = s.split(":")[0]
            a = ast.literal_eval(s.split("part A ")[1].split("; per evaluation")[0])
            rep = ast.literal_eval(s.split("per evaluation ")[1].split(": identical")[0])
            exp[name] = {"A": a, "report": rep}
        elif sec == "3." and s.startswith("-- "):
            cur = s[3:].strip()
            exp[cur] = {}
        elif sec == "3." and cur:
            for key, tag in (("cross", "cross-evaluation groups in shuffled order:"), ("A", "part A:"), ("B", "part B:"),
                             ("nopart", "no part (no candidate lineage):"),
                             ("report", "per evaluation (N_e, clusters in A, clusters in B):")):
                if s.startswith(tag):
                    exp[cur][key] = ast.literal_eval(s[len(tag):].strip())
    return ints, exp


def main():
    ints, exp = parse_expected(sys.argv[1])
    seed = 400004
    fails = 0
    for lab, v in ints.items():
        mine = pa.derived_int(seed, "cluster-partition", lab)
        ok = mine == v
        fails += not ok
        print(f"integer {lab}: mine {mine} printed {v} {'OK' if ok else 'DIFF'}")
    for name, (lin, links, bp) in VECTORS.items():
        le = {k: k.split(".", 1)[0] for k in lin}
        cands = [k for k, c in lin.items() if c]
        r = pa.partition(le, links, bp, cands, seed)
        A = sorted(c for c, p in r["cluster_part"].items() if p == "A")
        B = sorted(c for c, p in r["cluster_part"].items() if p == "B")
        rep = {e: (r["per_evaluation"][e]["N_e"], r["per_evaluation"][e]["A_clusters"], r["per_evaluation"][e]["B_clusters"])
               for e in pa.EVALS}
        nopart = sorted(r["noncandidate_cluster_group_part"])
        e = exp[name]
        checks = {"A": A == e["A"], "report": rep == e["report"]}
        if "B" in e:
            checks["B"] = B == e["B"]
            checks["cross"] = r["shuffled_orders"]["cross"] == e["cross"]
            checks["nopart"] = nopart == e["nopart"]
        bad = [k for k, ok in checks.items() if not ok]
        fails += bool(bad)
        print(f"{name}: A={A} B={B} report={rep} cross_order={r['shuffled_orders']['cross']} nopart={nopart} "
              f"groups>1={ {g: m for g, m in r['groups'].items() if len(m) > 1} } -> {'OK' if not bad else 'DIFF ' + str(bad)}")
    print("TOTAL DIFFERENCES:", fails)


if __name__ == "__main__":
    main()
