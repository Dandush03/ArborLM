# ruff: noqa
"""Audit 4 (R1): fitted single/joint count-feature tells. For a shape, a feature function of the item (counts only); a lookup table
feature-value -> most frequent answer is fitted on one draw (seed base 8300 + level) and scored on another (8400 + level). Reports
accuracy - chance per level (closed answers).
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <n_fit> <n_test>"""
import os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen4

def kq(b):  # kind of the asked statement, from the text
    return re.search(r'Consider the statement: "(every|no|some)', b.question).group(1)

FEATS = {
    "R1.categories_follow_r5": {
        "kind+#No+#Some": lambda b: (kq(b), len(b.structured["none"]), len(b.structured["some"])),
        "kind+#groups": lambda b: (kq(b), len(b.structured["cats"])),
        "kind+#No+#Some+#All": lambda b: (kq(b), len(b.structured["none"]), len(b.structured["some"]), len(b.structured["all"])),
    },
    "R1.conditional_chain_r5": {
        "#rules with q-conclusion signs": lambda b: tuple(sorted(re.findall(r"then " + b.structured["query"] + r" is (true|false)", b.question))),
        "#facts+#rules": lambda b: (len(b.structured["facts"]), len(b.structured["rules"])),
    },
    "R1.knights_knaves_r5": {
        "own statement kind": lambda b: b.structured["statements"][b.structured["who"]][0],
        "own kind + is self in args": lambda b: (b.structured["statements"][b.structured["who"]][0], b.structured["who"] in b.structured["statements"][b.structured["who"]][1]),
    },
    "R1.equivalence_classes_r5": {
        "#same+#diff": lambda b: (len(b.structured["same"]), len(b.structured["different"])),
        "x,y degree (same/diff)": lambda b: tuple(sum(1 for e in b.structured[k] if v in e) for v in (b.structured["x"], b.structured["y"]) for k in ("same", "different")),
    },
    "R1.order_compare_r5": {"#facts": lambda b: len(b.structured["taller"]), "x,y in/out degree": lambda b: tuple(sum(1 for e in b.structured["taller"] if e[i] == v) for v in (b.structured["x"], b.structured["y"]) for i in (0, 1))},
    "R1.road_reachability_r5": {"#roads": lambda b: len(b.structured["roads"]), "x out, y in degree": lambda b: (sum(1 for e in b.structured["roads"] if e[0] == b.structured["x"]), sum(1 for e in b.structured["roads"] if e[1] == b.structured["y"]), sum(1 for e in b.structured["roads"] if e[1] == b.structured["x"]))},
    "R1.graph_bipartite_r5": {"#edges": lambda b: len(b.structured["rivals"]), "degree sequence top3": lambda b: tuple(sorted(Counter(p for e in b.structured["rivals"] for p in e).values(), reverse=True)[:3])},
    "R1.kinship_cousins_r5": {"x,y have parent / grandparent": lambda b: tuple((v in b.structured["parent"], b.structured["parent"].get(v) in b.structured["parent"]) for v in (b.structured["x"], b.structured["y"])),
                              "x,y #children": lambda b: tuple(sorted(sum(1 for c, p in b.structured["parent"].items() if p == v) for v in (b.structured["x"], b.structured["y"])))},
    "R1.temporal_interval_overlap_r5": {"earlier length bucket of 5": lambda b: None},
    "R1.nim_xor_r5": {"sum mod 8": lambda b: sum(b.structured["piles"]) % 8, "sum mod 16": lambda b: sum(b.structured["piles"]) % 16},
    "R1.boolean_lights_r4": {"#presses of switches wired to ask, parity": lambda b: sum(1 for c in b.structured["presses"] if b.structured["ask"] in b.structured["switches"][c]) % 2},
    "R1.one_culprit": {"true count": lambda b: b.structured["true_count"]},
}
nf, nt = int(sys.argv[1]), int(sys.argv[2])
L = gen4.lineages()
for lid, feats in FEATS.items():
    lin = L[lid]
    for name, f in feats.items():
        row = []
        for lv in range(7):
            fit = gen4.items(lin, lv, nf, 8300); test = gen4.items(lin, lv, nt, 8400)
            tab = defaultdict(Counter)
            for b in fit:
                tab[f(b)][b.answer] += 1
            glob = Counter(b.answer for b in fit).most_common(1)[0][0]
            acc = sum((tab[f(b)].most_common(1)[0][0] if tab.get(f(b)) else glob) == b.answer for b in test) / nt
            ch = 1 / test[0].k
            row.append(acc - ch)
        print(f"{lid:34s} {name:40s} " + " ".join(f"{x:+.3f}" for x in row), flush=True)
