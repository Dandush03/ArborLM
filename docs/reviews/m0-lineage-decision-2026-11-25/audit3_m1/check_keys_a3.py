# ruff: noqa
"""Audit 3 of M1: key check (text-only solver vs the generator's key), alternative readings, stated answer format, and a determinism hash.
Usage: PYTHONHASHSEED=<h> PYTHONPATH=<impl worktree> uv run --locked --offline python check_keys_a3.py <per_level> <out.json>
Seed 3 (audit throwaway)."""
import hashlib
import json
import sys
import time
import traceback
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a3 import ALL_LEVELS, current_set, items
from solve_text_a3 import solve

SEED = 3


def one(args):
    lid, per = args
    lin = current_set(True)[lid]
    out = {}
    for lv in ALL_LEVELS:
        t0 = time.time()
        its = items(lin, lv, per, SEED, "keys")
        h = hashlib.sha256()
        bad, errs, alt_diff, fmt_missing = [], [], {}, 0
        for it in its:
            h.update(json.dumps([it.question, it.answer, it.structured], sort_keys=True).encode())
            if "Answer with a" not in it.question:
                fmt_missing += 1
            try:
                key, alt = solve(lid, it.question)
                if key != it.answer:
                    bad.append([it.question, it.answer, key])
                for k, v in alt.items():
                    alt_diff.setdefault(k, 0)
                    if v != it.answer:
                        alt_diff[k] += 1
            except Exception as e:
                errs.append([it.question, it.answer, repr(e)])
        out[str(lv)] = {"n": per, "mismatch": len(bad), "solver_errors": len(errs), "examples_mismatch": bad[:3], "examples_errors": errs[:3],
                        "alt_reading_key_changes": alt_diff, "no_stated_format": fmt_missing, "sha256": h.hexdigest(), "sec": round(time.time() - t0, 1)}
    return lid, out


if __name__ == "__main__":
    per, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    with get_context("spawn").Pool(8) as p:
        res = dict(p.map(one, [(i, per) for i in ids], chunksize=1))
    json.dump(res, open(path, "w"), indent=1, sort_keys=True)
    for lid in ids:
        r = res[lid]
        print(lid, "mismatch", [r[str(l)]["mismatch"] for l in ALL_LEVELS], "err", [r[str(l)]["solver_errors"] for l in ALL_LEVELS],
              "alt", {k: [r[str(l)]["alt_reading_key_changes"].get(k) for l in ALL_LEVELS] for k in r["3"]["alt_reading_key_changes"]},
              "nofmt", sum(r[str(l)]["no_stated_format"] for l in ALL_LEVELS))
