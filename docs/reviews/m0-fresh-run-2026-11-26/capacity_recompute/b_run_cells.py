"""Run a list of cells (lineage, level, target) with my own count, 16 processes; write one JSON line per cell.

usage: b_run_cells.py <cells.json> <out.jsonl> [--no-solver]
cells.json: [[lineage, level, target], ...]. Keys are written to work/keys/ (not delivered).
"""
import json
import multiprocessing as mp
import sys
import time

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

CHECK = "--no-solver" not in sys.argv


def work(cell):
    lid, lv, t = cell
    return rc.count_cell(lid, lv, t, check_solver=CHECK)


def main():
    cells = json.load(open(sys.argv[1]))
    # longest expected first: C1 slowest per attempt, then by target
    cells.sort(key=lambda c: (-(c[2] * (12 if c[0].startswith("C1") else 1)), c[0], c[1]))
    t0 = time.time()
    with open(sys.argv[2], "x") as fh, mp.get_context("spawn").Pool(16) as pool:
        for i, r in enumerate(pool.imap_unordered(work, cells)):
            fh.write(json.dumps(r, sort_keys=True) + "\n")
            fh.flush()
            if r["ended"] != "target" or r["solver_disagreements"]:
                print("NOTE", json.dumps(r), flush=True)
        print(f"done {i + 1} cells in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
