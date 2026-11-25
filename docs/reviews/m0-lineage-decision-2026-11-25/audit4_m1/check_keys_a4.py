# ruff: noqa
"""Audit 4 of M1: key check (text-only solver vs the generator's key), alternative readings, stated answer format, determinism hash.
Usage: PYTHONHASHSEED=<h> PYTHONPATH=<impl worktree> uv run --locked --offline python check_keys_a4.py <per_level> <out.json>
Seed 11 (audit throwaway, not a registered study seed)."""
import hashlib
import json
import sys
import time
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a4 import ALL_LEVELS, current_set, items
from solve_text_a4 import solve

SEED = 11


def one(args):
    lid, per = args
    lin = current_set(True)[lid]
    out = {}
    for lv in ALL_LEVELS:
        t0 = time.time()
        its = items(lin, lv, per, SEED, "keys")
        h = hashlib.sha256()
        bad, errs, alt_diff, alt_n, fmt_missing = [], [], {}, {}, 0
        for it in its:
            h.update(json.dumps([it.question, it.answer, it.structured], sort_keys=True).encode())
            if "Answer with a" not in it.question:
                fmt_missing += 1
            try:
                key, alt = solve(lid, it.question)
                if key != it.answer:
                    bad.append([it.question, it.answer, key])
                for k, v in alt.items():
                    alt_n[k] = alt_n.get(k, 0) + 1
                    alt_diff.setdefault(k, 0)
                    if v != it.answer:
                        alt_diff[k] += 1
            except Exception as e:
                errs.append([it.question, it.answer, repr(e)])
        out[str(lv)] = {"n": per, "mismatch": len(bad), "solver_errors": len(errs), "examples_mismatch": bad[:3], "examples_errors": errs[:3],
                        "alt_applicable": alt_n, "alt_reading_key_changes": alt_diff, "no_stated_format": fmt_missing, "sha256": h.hexdigest(), "sec": round(time.time() - t0, 1)}
    return lid, out


if __name__ == "__main__":
    per, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    with get_context("spawn").Pool(10) as p:
        res = dict(p.map(one, [(i, per) for i in ids], chunksize=1))
    json.dump(res, open(path, "w"), indent=1, sort_keys=True)
    tm = te = 0
    for lid in ids:
        r = res[lid]
        tm += sum(r[str(l)]["mismatch"] for l in ALL_LEVELS)
        te += sum(r[str(l)]["solver_errors"] for l in ALL_LEVELS)
        alts = sorted({k for l in ALL_LEVELS for k in r[str(l)]["alt_reading_key_changes"]})
        print(lid, "mismatch", [r[str(l)]["mismatch"] for l in ALL_LEVELS], "err", [r[str(l)]["solver_errors"] for l in ALL_LEVELS],
              "alt(changed/applicable)", {k: [f"{r[str(l)]['alt_reading_key_changes'].get(k, 0)}/{r[str(l)]['alt_applicable'].get(k, 0)}" for l in ALL_LEVELS] for k in alts},
              "nofmt", sum(r[str(l)]["no_stated_format"] for l in ALL_LEVELS))
    print("TOTAL items", per * 7 * len(ids), "mismatch", tm, "solver_errors", te)
