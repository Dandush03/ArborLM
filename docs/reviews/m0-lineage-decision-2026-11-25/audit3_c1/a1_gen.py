# ruff: noqa
"""Audit 3 (C1), step 1: draw items from every current and proposed C1 lineage with THROWAWAY seeds (not registered study seeds).

Seeds: my own stream = sha256("audit3c1|<seed>|<lineage>|<level>"), seed 7 (main draw).  Registered study seeds (400004.., 953702 ..) are not used.
Writes one gzip JSONL per lineage into OUT: {"lid","lv","i","src","key","q","retries"}.
Run from the audited worktree:  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this> --per-level 400 --seed 7 --out <dir>
"""
import argparse, gzip, hashlib, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())


def all_lineages():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2, SUPERSEDES, PROPOSED
    old = {x.id: x for x in lineages_of("C1")}
    b1 = {x.id: x for x in load_batch1()}
    r2 = {x.id: x for x in load_rev2()}
    superseded = set(SUPERSEDES.values())
    current = sorted([i for i in [*old, *b1] if i not in superseded] + [i for i in r2 if i not in PROPOSED])
    proposed = sorted(PROPOSED)
    allx = {**old, **b1, **r2}
    return current, proposed, allx


def rng_for(seed, lid, lv):
    d = hashlib.sha256(f"audit3c1|{seed}|{lid}|{lv}".encode()).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def work(args):
    lid, seed, per_level, out = args
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    _, _, allx = all_lineages()
    lin = allx[lid]
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
                         "atype": b.answer_type, "k": b.k})
    fn = os.path.join(out, lid.replace("C1.", "") + ".jsonl.gz")
    with gzip.open(fn, "wt") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return lid, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=14)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    current, proposed, _ = all_lineages()
    meta = {"current": current, "proposed": proposed, "seed": a.seed, "per_level": a.per_level, "python": sys.version}
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(len(current), "current;", len(proposed), "proposed")
    t = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, n in ex.map(work, [(l, a.seed, a.per_level, a.out) for l in current + proposed]):
            print(lid, n, flush=True)
    print("secs", round(time.time() - t, 1))


if __name__ == "__main__":
    main()
