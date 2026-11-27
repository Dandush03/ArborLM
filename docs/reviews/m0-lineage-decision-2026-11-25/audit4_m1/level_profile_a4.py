# ruff: noqa
"""Audit 4 of M1: did the fix round change what the levels mean?
(1) Level no-op test: for each lineage and each pair of levels (L, L'), build 300 items from the SAME rng stream (label independent of the level). If every item is
    byte-identical, the builder ignores the level between L and L' (the two levels are the same distribution, exactly).
(2) Level profile before/after: per level, the mean count of numbers printed, mean log10(|answer|+1), mean question length in words; for the r3 shape and for the
    pre-fix shape it revises (core M1 16 + rev2 shapes + carried-over batch-1, as in audit 3).
Seed 13 (audit throwaway). Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python level_profile_a4.py <out.json>"""
import json
import math
import re
import sys
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from studies.m0.core import ALL_LEVELS, Retry, build_item, stream

SEED = 13


def after():
    from studies.m0.lineages_m1_fix3 import load_all
    return {x.id: x for x in load_all()}


def before():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_m1_rev2 import load_rev2
    d = {x.id: x for x in lineages_of("M1")}
    d.update({x.id: x for x in load_rev2()})
    return d


def stem(lid):
    s = lid.split(".", 1)[1].removesuffix("_r3").removesuffix("_r2")
    return "power_remainder" if s in ("last_digit_power",) else s


def old_for(new_id, old):
    st = stem(new_id)
    for k in (f"M1.{st}_r2", f"M1.{st}", f"M1.power_remainder_r2" if st == "power_remainder" else None):
        if k and k in old:
            return k
    return None


def nums(q):
    return [float(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q.replace("$", " "))]


def noop(lin, n=300):
    out = {}
    for a in ALL_LEVELS:
        for b in ALL_LEVELS:
            if b <= a:
                continue
            ra, rb = stream(SEED, "noop", lin.id), stream(SEED, "noop", lin.id)
            same = 0
            for i in range(n):
                try:
                    x = build_item(lin, a, ra, "A", "x")
                    y = build_item(lin, b, rb, "A", "x")
                except Exception:
                    break
                same += (x.question, x.answer) == (y.question, y.answer)
            out[f"{a}-{b}"] = same / n
    return out


def profile(lin, n=600):
    out = {}
    for lv in ALL_LEVELS:
        r = stream(SEED, "profile", lin.id, str(lv))
        its = [build_item(lin, lv, r, "A", "p") for _ in range(n)]
        out[str(lv)] = {"numbers": round(sum(len(nums(i.question)) for i in its) / n, 1), "log_ans": round(sum(math.log10(abs(float(i.answer)) + 1) for i in its) / n, 2),
                        "words": round(sum(len(i.question.split()) for i in its) / n, 1)}
    return out


def one(args):
    lid, which = args
    lin = (after() if which == "after" else before())[lid]
    res = {"profile": profile(lin)}
    if which == "after":
        res["noop"] = noop(lin)
    return which, lid, res


if __name__ == "__main__":
    A, B = after(), before()
    tasks = [(i, "after") for i in sorted(A) if "digit_puzzle" not in i]
    olds = sorted({old_for(i, B) for i in A if old_for(i, B)} - {"M1.digit_puzzle_r2"})
    tasks += [(o, "before") for o in olds]
    with get_context("spawn").Pool(12) as p:
        res = p.map(one, tasks, chunksize=1)
    out = {"after": {}, "before": {}, "pairs": {i: old_for(i, B) for i in A}}
    for which, lid, r in res:
        out[which][lid] = r
    json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
    for lid in sorted(out["after"]):
        r = out["after"][lid]
        same_adj = [f"{a}={a+1}" for a in range(6) if r["noop"][f"{a}-{a+1}"] == 1.0]
        o = out["pairs"].get(lid)
        po = out["before"].get(o, {}).get("profile") if o else None
        fmtp = lambda p: " ".join(f"{p[str(l)]['numbers']}/{p[str(l)]['log_ans']}" for l in ALL_LEVELS)
        print(f"{lid:34s} identical-levels {same_adj}")
        print(f"   after  nums/log10ans: {fmtp(r['profile'])}")
        if po:
            print(f"   before ({o}) : {fmtp(po)}")
