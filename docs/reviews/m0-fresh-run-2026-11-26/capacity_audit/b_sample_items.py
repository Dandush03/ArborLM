"""Item 2 and item 5 sample: for each of the 67 candidates, 200 items per level (1,400 per lineage), built one after
another with core.build_item on stream(400002, "capacity-audit-names", e, id, str(level)) (audit label; NOT the label of
record). Each item is also given to the second solver (as capacity.py and the pair audit form it: deepcopy of the JSON
round trip); disagreements, errors and the slowest solver time are recorded. Writes work/sample_items.jsonl and
deliver/b_sample_solvers.json. Run from the implementation worktree root."""
import copy, json, os, sys, time
from multiprocessing import get_context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import SCR, candidates, load_lineages, load_solvers, my_stream

LABEL = "capacity-audit-names"
PER_LEVEL = 200


def one(lid):
    from studies.m0.core import build_item
    lins = load_lineages(); sol = load_solvers()[lid]; lin = lins[lid]
    rows, dis, slow = [], [], 0.0
    for lv in range(7):
        rng = my_stream(400002, LABEL, lin.eval, lid, str(lv))
        for i in range(PER_LEVEL):
            it = build_item(lin, lv, rng, "-", "x")
            st = json.loads(json.dumps(it.structured))
            t0 = time.perf_counter()
            try:
                got = sol(it.question, copy.deepcopy(st))
                bad = None if (isinstance(got, str) and got == it.answer) else f"mismatch {got!r:.80} vs {it.answer!r:.80}"
            except Exception as e:  # noqa
                bad = f"error {type(e).__name__}: {str(e)[:120]}"
            slow = max(slow, time.perf_counter() - t0)
            if bad:
                dis.append({"level": lv, "i": i, "what": bad})
            rows.append({"id": lid, "level": lv, "i": i, "question": it.question, "structured": st, "answer": it.answer})
    return lid, rows, dis, slow


if __name__ == "__main__":
    ids = [x for e in ("R1", "R2", "M1", "C1") for x in candidates()[e]]
    assert len(ids) == 67
    out = {}
    with open(f"{SCR}/work/sample_items.jsonl", "x") as fo:
        with get_context("fork").Pool(12) as pool:
            for lid, rows, dis, slow in pool.imap(one, ids):
                for r in rows:
                    fo.write(json.dumps(r) + "\n")
                out[lid] = {"items": len(rows), "solver_disagreements": dis, "slowest_solver_seconds": round(slow, 4)}
                print(lid, len(rows), len(dis), round(slow, 4), flush=True)
    with open(f"{SCR}/deliver/b_sample_solvers.json", "x") as f:
        json.dump(out, f, indent=1, sort_keys=True)
