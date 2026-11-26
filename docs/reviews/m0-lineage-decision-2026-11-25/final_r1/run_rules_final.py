# ruff: noqa
"""Final R1 audit: re-run (1) audit 4's battery (heuristics4.main, copied unchanged into a4copy/, run on the fix-4 survivors through the gen4 shim),
(2) the implementer's battery (studies.m0.r1_fix3_battery.measure, imported read-only, as audit 4's impl_battery_rerun4.py did) and
(3) audit 4's fitted count-feature lookups (feature_functions copied from feature_tells4.py / kept_tells4.py for the surviving shapes; fresh seeds)
on fresh throwaway seeds. One process per shape.
Adaptation (the only one): heuristics4.preds is wrapped so that an _r6 id is passed as _r5 (the audit-4 'NEW' rules for the shape's _r5 builder then
apply to the _r6 builder, whose wording is unchanged); audit 4 itself only ran NEW rules on ids ending _r5.
usage: python run_rules_final.py <n> <aud_seed> <aud_fit> <impl_seed> <impl_fit> <feat_fit> <feat_test> <n_feat> <out_dir> [ids...]"""
import json, os, re, sys
from collections import Counter, defaultdict
from multiprocessing import Pool

D = os.path.dirname(os.path.abspath(__file__))


def feat_defs():
    FEATS = {
        "R1.knights_knaves_r6": {
            "own statement kind": lambda b: b.structured["statements"][b.structured["who"]][0],
            "own kind + is self in args": lambda b: (b.structured["statements"][b.structured["who"]][0], b.structured["who"] in b.structured["statements"][b.structured["who"]][1]),
        },
        "R1.boolean_lights_r4": {"#presses of switches wired to ask, parity": lambda b: sum(1 for c in b.structured["presses"] if b.structured["ask"] in b.structured["switches"][c]) % 2},
        "R1.conditional_threshold_rule_r4": {"margin sign and |margin|//5": lambda b: (b.structured["margin"] > 0, abs(b.structured["margin"]) // 5),
                                              "#yes - #no votes": lambda b: sum(1 if v == "yes" else -1 if v == "no" else 0 for v in b.structured["votes"].values())},
        "R1.categories_default_exceptions_r4": {"#rules for verb, #true for verb": lambda b: (sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"]), sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"] and r[2])),
                                                 "chain length": lambda b: len(b.structured["chain"])},
    }
    return FEATS


def one(args):
    lid, n, aseed, afit, iseed, ifit, ffit, ftest, nf, out = args
    sys.path.insert(0, os.path.join(D, "a4copy"))
    sys.path.insert(0, D)
    import fgen
    import heuristics4 as H4
    from studies.m0 import r1_fix3_battery as B
    orig = H4.preds
    H4.preds = lambda l, b: orig(re.sub(r"_r6$", "_r5", l), b)
    argv = sys.argv
    sys.argv = ["heuristics4.py", str(n), str(aseed), str(afit), os.path.join(out, f"{lid}.aud.jsonl"), lid]
    H4.main()
    sys.argv = argv
    lin = fgen.lineages()[lid]
    rows = B.measure(lin, n, iseed, ifit)
    with open(os.path.join(out, f"{lid}.impl.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in ("lineage", "level", "heuristic", "fired", "acc_fired", "eff", "anti", "chance", "n")}) + "\n")
    with open(os.path.join(out, f"{lid}.feat.jsonl"), "w") as f:
        for name, fn in sorted(feat_defs().get(lid, {}).items()):
            for lv in range(7):
                fit = fgen.items(lin, lv, nf, ffit); test = fgen.items(lin, lv, nf, ftest)
                tab = defaultdict(Counter)
                for b in fit:
                    tab[fn(b)][b.answer] += 1
                glob = Counter(b.answer for b in fit).most_common(1)[0][0]
                acc = sum((tab[fn(b)].most_common(1)[0][0] if tab.get(fn(b)) else glob) == b.answer for b in test) / nf
                f.write(json.dumps({"lineage": lid, "level": lv, "heuristic": f"feat:{name}", "eff": round(acc - 1 / test[0].k, 4), "anti": None, "acc_fired": None, "fired": nf, "n": nf}) + "\n")
    return lid


if __name__ == "__main__":
    a = sys.argv[1:]
    n, aseed, afit, iseed, ifit, ffit, ftest, nf = (int(x) for x in a[:8])
    out = a[8]
    sys.path.insert(0, D)
    import fgen
    ids = a[9:] or sorted(fgen.lineages())
    os.makedirs(out, exist_ok=True)
    with Pool(min(12, len(ids))) as p:
        for lid in p.imap_unordered(one, [(i, n, aseed, afit, iseed, ifit, ffit, ftest, nf, out) for i in ids]):
            print(lid, "done", flush=True)
