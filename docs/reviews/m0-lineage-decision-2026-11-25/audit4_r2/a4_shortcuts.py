# ruff: noqa
"""Audit 4 (R2): shortcut measurement, per lineage, level and shape, two-sided.
Batteries: mine (a4_heur.H), audit 3's (a3_heur.H, read from the review folder of the audited worktree, read-only), and the implementer's (studies.m0.r2_fix3_heuristics.OWN).
'most frequent answer' learned per shape on a separate training draw. Seeds: train random.Random(f"a4r2|{lid}|{lv}|5"), test random.Random(f"a4r2|{lid}|{lv}|6") (throwaway).
Effect: open answers -> accuracy (chance 0), with a rule's None counted as WRONG (acc_all) and, separately, accuracy among items where it applies (acc_app);
yes/no -> |acc_app - 0.5|. Names containing '(P)' are valid alternative procedures/full solves (reported, not counted as cues).
Usage (cwd = audited worktree): PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:<deliver> uv run --locked --offline python a4_shortcuts.py N OUT.json"""
import json
import random
import sys
from collections import Counter
from multiprocessing import Pool

N = int(sys.argv[1])
OUT = sys.argv[2]
A3 = "docs/reviews/m0-lineage-decision-2026-11-25/audit3_r2"


def shape(lid, s):
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            v = s[k]
            if lid.endswith("cache_eviction"):
                v = s["policy"] + "/" + v
            return v
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    if lid.endswith("sort_list"):
        return f"desc={s['desc']}"
    return "-"


def batteries(name):
    sys.path.append(A3)
    import a3_heur
    import a4_heur
    from studies.m0.r2_fix3_heuristics import OWN

    out = []
    for src, H in (("mine", a4_heur.H), ("a3", a3_heur.H), ("impl", OWN)):
        for hn, fn in H.get(name, []):
            out.append((f"[{src}] {hn}", fn))
    return out


def run(lid):
    from studies.m0.core import ALL_LEVELS, build_item
    from studies.m0.r2_fix3_set import fix3_set

    lin = fix3_set()[lid]
    name = lid.split(".", 1)[1]
    hs = batteries(name)
    res = {}
    for lv in ALL_LEVELS:
        rtr = random.Random(f"a4r2|{lid}|{lv}|5")
        rte = random.Random(f"a4r2|{lid}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(N)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(N)]
        gtr, gte = {}, {}
        for it in tr:
            gtr.setdefault(shape(lid, it.structured), []).append(it)
        for it in te:
            gte.setdefault(shape(lid, it.structured), []).append(it)
        rows = {}
        for sh, grp in gte.items():
            at = grp[0].answer_type
            ent = {"n": len(grp), "share": len(grp) / N, "answer_type": at, "rules": {}, "distinct_answers": len({it.answer for it in grp})}
            if at == "yn":
                ent["yes_share"] = sum(it.answer == "yes" for it in grp) / len(grp)
            mode = Counter(it.answer for it in gtr.get(sh, grp)).most_common(1)[0][0]
            k = sum(it.answer == mode for it in grp)
            ent["rules"]["most frequent answer (train draw)"] = {"k": k, "napp": len(grp), "nerr": 0}
            for hn, fn in hs:
                kk = napp = nerr = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:
                        nerr += 1
                        a = None
                    if a is None:
                        continue
                    napp += 1
                    kk += a == it.answer
                if napp:
                    ent["rules"][hn] = {"k": kk, "napp": napp, "nerr": nerr}
            for hn, v in ent["rules"].items():
                n = len(grp)
                v["acc_all"] = v["k"] / n
                v["acc_app"] = v["k"] / v["napp"]
                v["effect"] = abs(v["acc_app"] - 0.5) if at == "yn" else v["acc_all"]
                v["P"] = "(P)" in hn
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from studies.m0.r2_fix3_set import fix3_set

    ids = sorted(fix3_set())
    if len(sys.argv) > 3:
        ids = [i for i in ids if i.split(".")[1] in sys.argv[3].split(",")]
    with Pool(12) as p:
        out = dict(p.map(run, ids))
    json.dump({"N": N, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    print("wrote", OUT)
