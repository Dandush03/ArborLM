# ruff: noqa
"""Audit 4 (R1): new tell hunt on the kept shapes. (1) fitted lookup tables of count features (fit seed base 8500 + level, test 8600 + level);
(2) kinship_ancestor_r4: "pick uniformly among the options in the asked child's own family tree" (credit = 1/#such options), eff = acc - 1/k.
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <n_fit> <n_test>"""
import os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen4
FEATS = {
    "R1.conditional_threshold_rule_r4": {"margin sign and |margin|//5": lambda b: (b.structured["margin"] > 0, abs(b.structured["margin"]) // 5),
                                          "#yes - #no votes": lambda b: sum(1 if v == "yes" else -1 if v == "no" else 0 for v in b.structured["votes"].values())},
    "R1.categories_default_exceptions_r4": {"#rules for verb, #true for verb": lambda b: (sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"]), sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"] and r[2])),
                                             "chain length": lambda b: len(b.structured["chain"])},
    "R1.containers_stack_piles_r4": {"asked pile size at start": lambda b: None},
}
nf, nt = int(sys.argv[1]), int(sys.argv[2])
L = gen4.lineages()
for lid, feats in FEATS.items():
    for name, f in feats.items():
        row = []
        for lv in range(7):
            fit = gen4.items(L[lid], lv, nf, 8500); test = gen4.items(L[lid], lv, nt, 8600)
            tab = defaultdict(Counter)
            for b in fit: tab[f(b)][b.answer] += 1
            glob = Counter(b.answer for b in fit).most_common(1)[0][0]
            acc = sum((tab[f(b)].most_common(1)[0][0] if tab.get(f(b)) else glob) == b.answer for b in test) / nt
            row.append(acc - 1 / test[0].k if test[0].k else acc)
        print(f"{lid:36s} {name:40s} " + " ".join(f"{x:+.3f}" for x in row), flush=True)
lin = L["R1.kinship_ancestor_r4"]
row = []
for lv in range(7):
    its = gen4.items(lin, lv, nt, 8600)
    acc = 0.0
    for b in its:
        par = b.structured["parent"]
        def root(p):
            while p in par: p = par[p]
            return p
        rc = root(b.structured["child"])
        same = [o for o in b.structured["options"] if root(o) == rc]
        acc += (b.answer in same) / len(same) if same else 1 / b.k
    row.append(acc / nt - sum(1 / b.k for b in its) / nt)
print(f"{'R1.kinship_ancestor_r4':36s} {'options in the child s family tree':40s} " + " ".join(f"{x:+.3f}" for x in row))
