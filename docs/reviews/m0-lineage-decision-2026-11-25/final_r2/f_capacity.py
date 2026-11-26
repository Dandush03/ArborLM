# ruff: noqa
"""Final R2 audit: capacity against studies.m0.core.generate_pool AS WRITTEN (R-22, R-28, R-30).
Demand per cluster and level D = 10 x (ceil(4000/G) + ceil(20000/G) + 100), G = number of clusters in ONE part (R-30).
For each lineage, in a worker process, core.part_lineages is replaced by a function returning [that lineage] (so the pool holds one lineage;
allocate, draw_items with its 40 x count + 1000 attempt limit, and the normalised-text de-duplication are core's own), then
core.generate_pool("R2", "A", "capacity-final-r2", 20261125, 7*D, uniform level mix over 0..6, taken=set(), shortfalls=[]) is called.
supplied = items returned per level. Cross-lineage collisions: the parent intersects the text-hash sets of all lineages (the real pool
shares one 'taken' set across the part's lineages).
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> G OUT.json"""
import json, math, sys, time
from multiprocessing import Pool

G = int(sys.argv[1]); OUT = sys.argv[2]
D = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]


def run(nm):
    from studies.m0 import core
    from studies.m0.r2_fix4_set import fix4_set
    lin = fix4_set()["R2." + nm]
    core.part_lineages = lambda eval_id, part, seed=400004: [lin]  # worker process only
    t0 = time.time()
    taken = set()
    short = []
    items = core.generate_pool("R2", "A", "capacity-final-r2", 20261125, 7 * D, {lv: 1.0 for lv in range(7)}, taken, shortfalls=short)
    per = {lv: 0 for lv in range(7)}
    for it in items:
        per[it.level] += 1
    hs = {int(core.text_hash(it.question)[:16], 16) for it in items}
    assert len(hs) == len(items)
    return "R2." + nm, {"supplied": [per[lv] for lv in range(7)], "shortfalls": short, "seconds": round(time.time() - t0, 1)}, hs


if __name__ == "__main__":
    with Pool(10) as p:
        got = p.map(run, SURV, chunksize=1)
    res = {lid: r for lid, r, _ in got}
    coll = {}
    for i in range(len(got)):
        for j in range(i + 1, len(got)):
            c = len(got[i][2] & got[j][2])
            if c:
                coll[f"{got[i][0]}|{got[j][0]}"] = c
    out = {"G": G, "demand_per_level": D, "lineages": res, "cross_lineage_shared_texts": coll}
    json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"G={G} D={D}")
    for lid, r in res.items():
        fail = [lv for lv in range(7) if r["supplied"][lv] < D]
        print(f"{lid:34s} {r['supplied']} {'PASS' if not fail else 'FAIL at levels ' + str(fail)} ({r['seconds']} s)")
    print("cross-lineage shared texts:", coll or "none")
