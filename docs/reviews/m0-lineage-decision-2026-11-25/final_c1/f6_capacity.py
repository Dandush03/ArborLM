# ruff: noqa
"""Final C1 audit (fix 4), step 6: capacity against studies.m0.core.generate_pool AS WRITTEN (R-22, R-28, R-30).

For every surviving lineage and level, ONE call of core.generate_pool(eval_id="C1", part="A", role=ROLE, seed=SEED, size=COUNT, level_mix={lv: 1.0},
taken=<counting set>, shortfalls=[]) is made. The only substitution (in this process; no file is edited): core.part_lineages is replaced by a function
returning [that lineage], because no fix-4 lineage is in core.REGISTRY, so the pool builder could not see it otherwise. Everything else (allocate, stream,
draw_items with its text de-duplication on core.normalise and its budget 40 * count + 1000 attempts, build_item with 500 retries) is the code as written.
The counting set records the attempt number (one membership test per attempt in draw_items) at which the k-th distinct item was added, so for a demand D
the result equals a call with count = D on the same stream: PASS iff D distinct items are reached within 40 * D + 1000 attempts.
Demands (R-30, G = clusters in the smaller part): 10 * (ceil(4000/G) + ceil(20000/G) + 100): G=9 27,680; G=8 31,000; G=7 35,300.
Each job also writes the 8-byte prefixes of the text hashes it took (for the cross-lineage / cross-level collision check, f6b).
Usage (cwd = the audited worktree): uv run --locked python <this> --seed S --count 35300 --out DIR [--workers K]
"""
import argparse, json, math, os, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f1_draw import SURVIVORS

ROLE = "final-c1-capacity"


def demand(G):
    return 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)


class CountingSet(set):
    def __init__(self):
        super().__init__()
        self.tests = 0
        self.reached = []  # attempt number when the k-th item was added
        self.added = []

    def __contains__(self, h):
        self.tests += 1
        return set.__contains__(self, h)

    def add(self, h):
        set.add(self, h)
        self.reached.append(self.tests)
        self.added.append(h)


def job(args):
    lid, lv, seed, count, out = args
    import studies.m0.core as core
    from studies.m0.lineages_c1_fix4 import all_written
    lin = all_written()[lid]
    core.part_lineages = lambda eval_id, part, partition_seed=400004: [lin]
    taken = CountingSet()
    short = []
    t = time.time()
    items = core.generate_pool("C1", "A", ROLE, seed, count, {lv: 1.0}, taken, shortfalls=short)
    secs = time.time() - t
    res = {"lid": lid, "lv": lv, "supplied": len(items), "attempts": taken.tests, "shortfalls": short, "secs": round(secs, 1)}
    for G in (7, 8, 9):
        D = demand(G)
        ok = len(taken.reached) >= D and taken.reached[D - 1] <= 40 * D + 1000
        res[f"G{G}"] = {"demand": D, "pass": ok, "attempt_at_demand": taken.reached[D - 1] if len(taken.reached) >= D else None, "budget": 40 * D + 1000}
    # sanity: every returned item's normalised text is distinct and its hash is in taken
    hs = [core.text_hash(it.question) for it in items]
    res["distinct_texts"] = len(set(hs))
    res["all_level"] = all(it.level == lv for it in items)
    with open(os.path.join(out, f"{lid.replace('C1.', '')}_L{lv}.bin"), "wb") as f:
        for h in taken.added:
            f.write(bytes.fromhex(h[:16]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--count", type=int, default=35300)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = a.ids.split(",") if a.ids else SURVIVORS
    jobs = [(l, lv, a.seed, a.count, a.out) for l in ids for lv in range(7)]
    t = time.time()
    res = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(job, jobs):
            res.append(r)
            print(r["lid"], r["lv"], r["supplied"], r["attempts"], r["G9"]["pass"], r["G8"]["pass"], r["G7"]["pass"], r["secs"], flush=True)
    json.dump({"seed": a.seed, "count": a.count, "role": ROLE, "python": sys.version, "secs": round(time.time() - t, 1), "jobs": res},
              open(os.path.join(a.out, "capacity.json"), "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
