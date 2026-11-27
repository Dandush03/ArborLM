# ruff: noqa
"""Audit 4 (C1), step 2: draw items from every current C1 lineage (set of s1_set.py) with THROWAWAY seeds (not registered study seeds).

Seeds: my own stream = sha256("audit4c1|<seed>|<lineage>|<level>"); seed 41 (main draw), 43 (second draw used for CV checks if needed).
Registered study seeds (400004, 953702, ...) are not used. Writes one gzip JSONL per lineage: {"lid","lv","i","src","key","q","retries"}.
Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this> --per-level 400 --seed 41 --out <dir> --ids <s1_set_out.json>
"""
import argparse, gzip, hashlib, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())


def by_id():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2
    from studies.m0.lineages_c1_fix3 import load_fix3
    return {x.id: x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2(), *load_fix3()]}


def rng_for(seed, lid, lv):
    d = hashlib.sha256(f"audit4c1|{seed}|{lid}|{lv}".encode()).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def work(args):
    lid, seed, per_level, out = args
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    lin = by_id()[lid]
    rows = []
    for lv in range(7):
        r = rng_for(seed, lid, lv)
        for i in range(per_level):
            tries = 0
            while True:
                tries += 1
                if tries > 500:
                    raise RuntimeError(f"{lid} L{lv}: 500 retries")
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            src = render(b.structured["program"])
            rows.append({"lid": lid, "lv": lv, "i": i, "src": src, "key": b.answer, "q": b.question, "retries": tries - 1,
                         "atype": b.answer_type})
    with gzip.open(os.path.join(out, lid.replace("C1.", "") + ".jsonl.gz"), "wt") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return lid, len(rows), sum(r["retries"] for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=400)
    ap.add_argument("--seed", type=int, default=41)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = json.load(open(a.ids))["current"]
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump({"ids": ids, "seed": a.seed, "per_level": a.per_level, "python": sys.version}, f, indent=1)
    t = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, n, rt in ex.map(work, [(l, a.seed, a.per_level, a.out) for l in ids]):
            print(lid, n, "retries", rt, flush=True)
    print("secs", round(time.time() - t, 1))


if __name__ == "__main__":
    main()
