# ruff: noqa
"""Final R2 audit: the NEW rules of f_new_heur.py on the SAME fresh seeds as f_rules.py (finalr2|<lid>|<level>|5 train, |6 test).
Usage (cwd = audited worktree): PYTHONPATH=.:<deliver> PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> N OUT.json"""
import json, random, sys
from multiprocessing import Pool

N = int(sys.argv[1]); OUT = sys.argv[2]


def shape(lid, s):
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            return s[k]
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    if lid.endswith("sort_list"):
        return f"desc={s['desc']}"
    return "-"


def run(nm):
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    from f_new_heur import NEW
    lid = "R2." + nm
    lin = fix4_set()[lid]
    res = {}
    for lv in range(7):
        rte = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|6")
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(N)]
        g = {}
        for it in te:
            g.setdefault(shape(lid, it.structured), []).append(it)
        rows = {}
        for sh, grp in sorted(g.items()):
            ent = {"n": len(grp), "answer_type": grp[0].answer_type, "rules": {}}
            for hn, fn in NEW[nm]:
                kk = napp = nerr = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:
                        nerr += 1; a = None
                    if a is None:
                        continue
                    napp += 1; kk += a == it.answer
                ent["rules"]["[NEW] " + hn] = {"k": kk, "napp": napp, "nerr": nerr}
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res


if __name__ == "__main__":
    from f_new_heur import NEW
    with Pool(10) as p:
        out = dict(p.map(run, sorted(NEW), chunksize=1))
    json.dump({"n": N, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    for lid, r in out.items():
        for lv, rows in r.items():
            for sh, e in rows.items():
                for hn, v in e["rules"].items():
                    eff = abs(v["k"] / v["napp"] - 0.5) if e["answer_type"] == "yn" and v["napp"] else v["k"] / e["n"]
                    if eff > 0.05 or v["nerr"]:
                        print(f"{lid} L{lv} [{sh}] {eff:.3f} nerr={v['nerr']} {hn}")
