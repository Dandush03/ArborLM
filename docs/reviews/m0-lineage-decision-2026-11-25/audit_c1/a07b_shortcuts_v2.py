# ruff: noqa
"""v2 of a07 (a07 kept as the failed attempt): a07's shape key canonicalised ONLY the print statement, so every printed
bare variable became '_0' and the shape (which variable is printed) was lost. v2 canonicalises the whole program and takes
the print statement from it. v2 also adds rules and a per-shape breakdown of every R.* rule (rate inside the shapes where
the rule is meant to apply), and the share of each shape.
Run: python a07b_shortcuts_v2.py gen1
"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a07_shortcuts as A
from a02_myeval import canonical, to_str
from a06_feats import facts, _find_print

_hz = Counter()
S = lambda v: to_str(v, _hz)


def shape_key_v2(p, f):
    cp = canonical(p)
    pr = _find_print(cp)
    return json.dumps(pr[1])


def R_insertion2(f, p):
    out = A.R_insertion(f, p)
    pr = f["print"]
    if pr[0] == "idx":
        out["R.original_element_at_index"] = S(f["flat"][0][pr[2][1]])
    return out


def R_turtle2(f, p):
    s = f["strs"][0]
    out = A.R_turtle(f, p)
    out["R.count_F_plus_B"] = S(s.count("F") + s.count("B"))
    return out


def R_shared2(f, p):
    # 'everything aliases' reading: every assignment d = <expr of s> makes d the SAME list as s (even copies/concats)
    return {}


A.SPECIFIC["C1.insertion_sort"] = R_insertion2
A.SPECIFIC["C1.turtle_walk"] = R_turtle2
A.shape_key = shape_key_v2


def per_shape(sub):
    d = os.path.join(HERE, sub)
    summ = json.load(open(os.path.join(d, "summary.json")))
    out = {}
    for lid in sorted(A.SPECIFIC):
        out[lid] = {}
        for lv in range(7):
            recs = [json.loads(l) for l in gzip.open(os.path.join(d, f"items_{lid}_L{lv}.jsonl.gz"), "rt")]
            fs = [facts(r["prog"]) for r in recs]
            tab = defaultdict(Counter)
            shapes = Counter()
            for f, r in zip(fs, recs):
                sh = shape_key_v2(r["prog"], f)
                shapes[sh] += 1
                gs = A.SPECIFIC[lid](f, r["prog"])
                for k, v in gs.items():
                    if v is not None:
                        tab[(k, sh)]["n"] += 1
                        tab[(k, sh)]["hit"] += v == r["ans"]
            rows = []
            for (k, sh), c in tab.items():
                if c["hit"] / max(1, shapes[sh]) >= 0.3:
                    rows.append((k, sh[:70], round(shapes[sh] / len(recs), 3), round(c["hit"] / shapes[sh], 3)))
            out[lid][lv] = sorted(rows, key=lambda x: -x[3])
    return out


if __name__ == "__main__":
    sub = sys.argv[1]
    summ, res = A.analyse(sub)
    json.dump(res, open(os.path.join(HERE, f"a07_shortcuts_{sub}_v2.json"), "w"), indent=1, sort_keys=True)
    ps = per_shape(sub)
    json.dump(ps, open(os.path.join(HERE, f"a07b_per_shape_{sub}.json"), "w"), indent=1, sort_keys=True)
    print("ok")
