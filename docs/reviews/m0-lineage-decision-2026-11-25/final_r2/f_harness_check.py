# ruff: noqa
"""Final R2 audit: does my harness (f_rules.py) reproduce the implementer's counts when given the implementer's seeds?
Runs f_rules.run's logic with the seed tag 'a4r2' (the implementer's 'a4' set) at N = 2000 for every survivor except crt (compared with
bat_a4_2000_crt.json) and compares every (level, shape, rule) k and napp with bat_a4_2000.json. Rules the implementer omitted (napp = 0) are skipped.
Usage (cwd = audited worktree): PYTHONPATH=.:<deliver> PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> IMPL_DIR"""
import json, random, sys
from collections import Counter
from multiprocessing import Pool
IMPL = sys.argv[1]
sys.argv = [sys.argv[0], "2000", "/dev/null"]  # f_rules reads N and OUT at import; OUT unused here
import f_rules

SURV = f_rules.SURV


def run(nm):
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    lid = "R2." + nm
    lin = fix4_set()[lid]
    hs = f_rules.batteries(nm)
    res = {}
    for lv in range(7):
        rtr = random.Random(f"a4r2|{lid}|{lv}|5"); rte = random.Random(f"a4r2|{lid}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(2000)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(2000)]
        gtr, gte = {}, {}
        for it in tr:
            gtr.setdefault(f_rules.shape(lid, it.structured), []).append(it)
        for it in te:
            gte.setdefault(f_rules.shape(lid, it.structured), []).append(it)
        rows = {}
        for sh, grp in gte.items():
            mode = Counter(it.answer for it in gtr.get(sh, grp)).most_common(1)[0][0]
            r = {"most frequent answer (train draw)": (sum(it.answer == mode for it in grp), len(grp))}
            for hn, fn in hs:
                k = napp = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:
                        a = None
                    if a is None:
                        continue
                    napp += 1; k += a == it.answer
                r[hn] = (k, napp)
            rows[sh] = r
        res[str(lv)] = rows
    return lid, res


if __name__ == "__main__":
    a4 = json.load(open(f"{IMPL}/bat_a4_2000.json"))["lineages"]
    a4.update(json.load(open(f"{IMPL}/bat_a4_2000_crt.json"))["lineages"])
    with Pool(10) as p:
        got = dict(p.map(run, SURV, chunksize=1))
    nsame = ndiff = 0
    for lid, res in got.items():
        for lv, rows in res.items():
            for sh, r in rows.items():
                for hn, (k, napp) in r.items():
                    v = a4[lid][lv][sh]["rules"].get(hn)
                    if v is None:
                        if napp:
                            ndiff += 1; print("missing in implementer file:", lid, lv, sh, hn, k, napp)
                        continue
                    if (v["k"], v["napp"]) == (k, napp):
                        nsame += 1
                    else:
                        ndiff += 1; print("DIFF", lid, lv, sh, hn, (k, napp), (v["k"], v["napp"]))
    print(f"equal cells {nsame}, different {ndiff}")
