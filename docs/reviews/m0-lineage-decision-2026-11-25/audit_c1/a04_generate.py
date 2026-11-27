# ruff: noqa
"""Audit steps 4b, 6 (data) and 7: draw items from every C1 lineage and level with the generators, then
(a) check every distinct drawn item's key with the auditor's own evaluator (a02_myeval), and the question/tree match;
(b) count distinct programs after canonical renaming of all identifiers (capacity);
(c) save the first N raw-distinct items per cell (tree + key) for the shortcut analysis (a06).

Uses only studies.m0.core.build_item/stream, the lineage builders and the registries. No solver, no analysis module.
Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this> <out_subdir> [--workers 14]
"""
import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, ".")

SEED = 20261125
CAP_TARGET = 2000
MAX_DRAWS = 30000
_WS = re.compile(r"\s+")


def norm(t):
    return _WS.sub(" ", unicodedata.normalize("NFKC", t).casefold()).strip()


def cell(args):
    lid, lv, keep_n, outdir = args
    from studies.m0.core import build_item, lineages_of, stream
    from studies.m0.lineages_c1_common import load_batch1
    from a02_myeval import EvalError, canonical, construct_problems, evaluate, tree_from_question

    lins = {x.id: x for x in lineages_of("C1")}
    lins.update({x.id: x for x in load_batch1()})
    lin = lins[lid]
    r = stream(SEED, "audit-gen", lid, str(lv))
    raw, canon = set(), set()
    kept = []
    draws = 0
    draws_at_cap = None
    new_in_last = []  # 1 if the draw gave a new canonical form
    problems = []
    hz = {}
    cons = {}
    t0 = time.time()
    max_steps = 0
    while draws < MAX_DRAWS and (len(kept) < keep_n or len(canon) < CAP_TARGET):
        draws += 1
        it = build_item(lin, lv, r, "A", f"{lid}/audit/L{lv}/{draws}")
        prog = it.structured["program"]
        c = json.dumps(canonical(prog), separators=(",", ":"))
        isnew = c not in canon
        canon.add(c)
        new_in_last.append(1 if isnew else 0)
        if draws_at_cap is None and len(canon) >= CAP_TARGET:
            draws_at_cap = draws
        h = norm(it.question)
        if h in raw:
            continue
        raw.add(h)
        if len(kept) < keep_n:
            # key check with own evaluator + render fidelity
            try:
                t = tree_from_question(it.question)
                if t != json.loads(json.dumps(prog)):
                    problems.append((it.id, "render-mismatch"))
                out, m = evaluate(prog)
                if out != it.answer:
                    problems.append((it.id, f"myeval {out!r} != key {it.answer!r}"))
                max_steps = max(max_steps, m.steps)
                for k in m.hz:
                    hz[k] = hz.get(k, 0) + 1
            except EvalError as ex:
                problems.append((it.id, "myeval error " + str(ex)))
            except Exception as ex:
                problems.append((it.id, "parse error " + repr(ex)))
            for p in construct_problems(prog):
                cons[p] = cons.get(p, 0) + 1
            kept.append({"lv": lv, "ans": it.answer, "prog": prog})
    tail = new_in_last[-2000:]
    rec = {"lineage": lid, "level": lv, "draws": draws, "raw_distinct": len(raw), "canon_distinct": len(canon),
           "draws_to_2000_canon": draws_at_cap, "new_rate_last_2000_draws": round(sum(tail) / max(1, len(tail)), 4),
           "kept": len(kept), "problems": problems[:20], "n_problems": len(problems), "hazards": hz, "solver_missing": cons,
           "max_steps": max_steps, "secs": round(time.time() - t0, 1)}
    fn = os.path.join(outdir, f"items_{lid}_L{lv}.jsonl.gz")
    with gzip.open(fn, "wt") as fh:
        for k in kept:
            fh.write(json.dumps(k, separators=(",", ":")) + "\n")
    return rec


def main():
    sub = sys.argv[1]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 14
    outdir = os.path.join(HERE, sub)
    os.makedirs(outdir, exist_ok=False)
    from studies.m0.core import ALL_LEVELS, lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    old = [x.id for x in lineages_of("C1")]
    new = [x.id for x in load_batch1()]
    tasks = [(lid, lv, 2000 if lid in new else 1000, outdir) for lid in old + new for lv in ALL_LEVELS]
    with Pool(workers) as p:
        recs = p.map(cell, tasks, chunksize=1)
    with open(os.path.join(outdir, "summary.json"), "w") as fh:
        json.dump({"seed": SEED, "cap_target": CAP_TARGET, "max_draws": MAX_DRAWS, "old": old, "new": new, "cells": recs}, fh, indent=1, sort_keys=True)
    bad = sum(r["n_problems"] for r in recs)
    print("cells", len(recs), "problems", bad)
    for r in recs:
        if r["n_problems"] or r["solver_missing"] or r["draws_to_2000_canon"] is None:
            print(r["lineage"], r["level"], "problems", r["n_problems"], r["problems"][:3], "missing", r["solver_missing"], "canon", r["canon_distinct"], "draws", r["draws"])


if __name__ == "__main__":
    main()
