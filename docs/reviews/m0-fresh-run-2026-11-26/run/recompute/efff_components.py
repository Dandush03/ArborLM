"""Descriptive: which component carries EFF_F, per shape and fold, from the raw s4 records (C1a, C1c).
Re-implements the documented choice of s5_analyse_v2.py (2-fold CV by item parity; per shape the best of the shape's most
frequent key and every rule whose prefix is allowed, chosen on one fold, scored on the other) with the auditor's own code,
and checks that round(hits/n, 3) equals the EFF_S / EFF_SM / EFF_F written in s5.json. Decides nothing.
Usage: python efff_components.py OUT_JSON"""
import gzip, json, sys
from collections import Counter, defaultdict
from fractions import Fraction as F
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126"
CASES = {"C1.circle_elimination_r2": "circle_elimination_r2", "C1.cond_chain_f3": "cond_chain_f3", "C1.shared_lists_f3": "shared_lists_f3",
         "C1.union_find_links_f3": "union_find_links_f3", "C1.func_branch_f4": "func_branch", "C1.string_build_f3": "string_build_f3",
         "C1.run_length_scan": "run_length_scan", "C1.slices_f4": "slices", "C1.postfix_evaluation": "postfix_evaluation",
         "C1.merge_two_sorted_f3": "merge_two_sorted_f3"}
S5KEY = {"C1.func_branch_f4": "C1.func_branch", "C1.slices_f4": "C1.slices"}
def choose(items, allow):
    hit = 0; detail = []
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        by = defaultdict(list)
        for x in train:
            by[x["shape"]].append(x)
        choice = {}
        for sh, sub in by.items():
            sc = Counter()
            mf = Counter(x["key"] for x in sub).most_common(1)[0]
            sc[("MF", mf[0])] = mf[1]
            for x in sub:
                for r, v in x["R"].items():
                    if v is not None and r.split(".")[0] in allow and v == x["key"]:
                        sc[("R", r)] += 1
            choice[sh] = sorted(sc.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]
        th = Counter(); tn = Counter()
        for x in test:
            c = choice.get(x["shape"]); tn[x["shape"]] += 1
            if c is None:
                continue
            h = (x["key"] == c[1]) if c[0] == "MF" else (x["R"].get(c[1]) == x["key"])
            th[x["shape"]] += h; hit += h
        for sh in sorted(set(choice) | set(tn)):
            c = choice.get(sh)
            name = None if c is None else ("MF(shape most frequent)" if c[0] == "MF" else c[1])
            detail.append({"fold_train": f, "shape": sh, "chosen": name, "test_hits": th[sh], "test_items": tn[sh]})
    return hit, detail
out = {}
mismatch = []
for lid, draw in CASES.items():
    for unit in ("C1a", "C1c"):
        for s in "123":
            recs = [json.loads(l) for l in gzip.open(f"{RUN}/{unit}/seed{s}/rules/{draw}.jsonl.gz", "rt")]
            s5 = json.load(open(f"{RUN}/{unit}/seed{s}/s5.json"))[S5KEY.get(lid, lid)]
            for lv in range(7):
                its = [x for x in recs if x["lv"] == lv]
                n = len(its)
                res = {}
                for name, allow in (("EFF_S", ("S", "G")), ("EFF_SM", ("S", "G", "M")), ("EFF_F", ("S", "G", "M", "F"))):
                    h, det = choose(its, allow)
                    ok = round(h / max(1, n), 3) == s5[str(lv)][name]
                    if not ok:
                        mismatch.append([lid, unit, s, lv, name, h, n, s5[str(lv)][name]])
                    res[name] = {"hits": h, "n": n, "written": s5[str(lv)][name], "reproduced": ok, "detail": det}
                out.setdefault(lid, {}).setdefault(unit, {}).setdefault(s, {})[str(lv)] = res
json.dump({"mismatch": mismatch, "cases": out}, open(sys.argv[1], "w"), indent=1)
print("mismatches with s5.json:", len(mismatch), mismatch[:5])
# summary: per lineage/unit/level pooled over seeds, EFF_F hits by the class of the chosen component
for lid in CASES:
    print("\n##", lid)
    for unit in ("C1a", "C1c"):
        for lv in range(7):
            tot = Counter(); n = 0; names = Counter(); hS = hSM = hF = 0
            for s in "123":
                r = out[lid][unit][s][str(lv)]
                n += r["EFF_F"]["n"]; hF += r["EFF_F"]["hits"]; hSM += r["EFF_SM"]["hits"]; hS += r["EFF_S"]["hits"]
                for d in r["EFF_F"]["detail"]:
                    c = d["chosen"] or "none"
                    cls = "MF" if c.startswith("MF") else c.split(".")[0]
                    tot[cls] += d["test_hits"]; names[c] += d["test_hits"]
            top = ", ".join(f"{k}:{v}" for k, v in names.most_common(4))
            print(f"  {unit} L{lv}: EFF_F hits {hF}/{n}={float(F(hF, n)):.4f} (EFF_SM {hSM}, EFF_S {hS}) by class {dict(tot)} | top {top}")
