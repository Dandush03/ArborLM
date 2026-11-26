# ruff: noqa
"""Final C1 audit (fix 4), step 6d: capacity with ONE shared `taken` across the seven levels of a lineage, as core.generate_pool does within a pool
(f6_capacity.py drew each level alone; f6b found 12,700 texts drawn at two levels of the same lineage and none across lineages). For each surviving lineage
and each demand D (G = 9, 8, 7), one call core.generate_pool("C1", "A", ROLE, seed, 7 * D, {0..6: equal}, taken=set(), shortfalls=[]) with part_lineages
substituted to return the lineage (as in f6). allocate gives D per level. PASS iff no shortfall (every level supplied D within 40 * D + 1000 attempts).
Usage (cwd = worktree): uv run --locked python <this> --seed S --out OUT_JSON [--workers K]
"""
import argparse, json, math, os, sys, time
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f1_draw import SURVIVORS


def demand(G):
    return 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)


def job(args):
    lid, G, seed = args
    import studies.m0.core as core
    from studies.m0.lineages_c1_fix4 import all_written
    lin = all_written()[lid]
    core.part_lineages = lambda e, p, s=400004: [lin]
    D = demand(G)
    short = []
    taken = set()
    t = time.time()
    items = core.generate_pool("C1", "A", "final-c1-capacity-shared", seed, 7 * D, {lv: 1.0 for lv in range(7)}, taken, shortfalls=short)
    per = {lv: 0 for lv in range(7)}
    for it in items:
        per[it.level] += 1
    return {"lid": lid, "G": G, "demand": D, "per_level": per, "shortfalls": short, "pass": not short and all(v == D for v in per.values()),
            "distinct": len({core.text_hash(it.question) for it in items}) == len(items), "secs": round(time.time() - t, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    jobs = [(l, G, a.seed) for G in (9, 8, 7) for l in SURVIVORS]
    res = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(job, jobs):
            res.append(r)
            print(r["lid"], "G", r["G"], "pass", r["pass"], r["shortfalls"], r["secs"], flush=True)
    fails = {G: [r["lid"] for r in res if r["G"] == G and not r["pass"]] for G in (9, 8, 7)}
    json.dump({"seed": a.seed, "jobs": res, "fails": fails}, open(a.out, "w"), indent=1, sort_keys=True)
    print("fails:", fails)


if __name__ == "__main__":
    main()
