"""Audit script a3 (Claude Opus 5.5 auditor; P10-S1 revision 5 implementation audit; not Astra review).

Question: when `stages calibrate --items load,row-up` runs items 0b and 1 together on six workers, does any run reach its
item's deadline because of the dispatch order rather than its own cost?

How the code behaves (read from studies/p10s1/stages.py cmd_calibrate / calibration_tasks and studies/p9/pool.py run_stage):
  * one task per calibration cell, listed load-search cells first (draw 1 then draw 2), then the 12 row-U_P cells;
  * the pool launches pending tasks in list order whenever one of the six workers is free;
  * every task of an item gets deadline = stage start + the item's cap, cap = 2 x the item's projected six-worker
    makespan computed for that item ALONE (budget.item_projection: training only, longest first, isolated wall rates);
  * the training loop raises ItemCapReached as soon as time >= deadline (also at update 1); the run then has no record
    usable by the rules (no U_L; no row U_P value).

This script takes the code's item caps (budget.item_projection, imported) and simulates the code's list-order dispatch with
my own scheduler. ASSUMED rates (no revision-5 rate exists: the timing preview has not run): ADR-0021 section 1 fact 17
(revision 4, six workers) used as the isolated rate; 1,024 and 256 slots at the 4,096-slot rate (the ADR's own assumption);
T-OQ at 1x or 2x F-OQ; evaluation seconds per snapshot 0 (lower bound) or 20 s; contention 1.0 or 1.25. Every number is a
projection under these assumptions, not a measurement.

  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root>
"""

import sys

sys.path.insert(0, sys.argv[1])
from studies.p10s1 import budget, calibrate, core  # noqa: E402


def rates(toq_factor):
    r = {}
    for n in (256, 1024, 4096):
        r[("F-OQ", n)] = 0.0093
    r[("F-OQ", 16384)] = 0.0153
    for n in (1024, 4096, 16384):
        r[("T-OQ", n)] = toq_factor * r[("F-OQ", n)]
        r[("H8", n)] = 0.0075 if n < 16384 else 0.0101
        r[("D-OQ", n)] = 0.0235 if n == 16384 else 0.0235 * (n / 16384) ** 0.5
    r[("R2", 4096)], r[("R2", 16384)], r[("R2", 32768)] = 0.0091, 0.0140, 0.0188
    return r


def simulate(items, toq, eval_s, contention, order="code"):
    rate = rates(toq)
    rows_up = {2048: 8192, 8192: 8192, 32768: 16384} if "h8" in items else None
    proj = budget.item_projection(rate, core.U_P, rows_up)
    caps = {i: proj[i]["cap_seconds"] for i in items}
    cells = [(i, c) for i in items for c in core.calibration_cells_of([i], None if "h8" not in items else {2048: 8192, 8192: 8192, 32768: 16384})]
    if order == "row-up first":
        cells = sorted(cells, key=lambda x: 0 if x[0] == "row-up" else 1)
    free = [0.0] * 6
    rows = []
    for item, c in cells:
        w = min(range(6), key=lambda k: free[k])
        start = free[w]
        train = c.run_updates * rate[(c.arm, c.slots)] * contention
        n_eval = len(calibrate.calibration_snapshots(c))
        deadline = caps[item]
        if start >= deadline:
            end, status = start, "STOPPED AT UPDATE 0 (started after its item's deadline)"
        elif start + train > deadline:
            end, status = deadline, "STOPPED AT ITS ITEM CAP"
        else:
            end, status = start + train + n_eval * eval_s, "completed"
        free[w] = end
        rows.append((item, c.label, round(start), round(train), round(deadline), status))
    return caps, rows


print(__doc__.split("How the code")[0].strip())
for items in (("load", "row-up"), ("h8", "dense")):
    for order in (("code", "row-up first") if "load" in items else ("code",)):
        for toq in (1.0, 2.0):
            for eval_s in (0.0, 20.0):
                for cont in (1.0, 1.25):
                    caps, rows = simulate(items, toq, eval_s, cont, order)
                    stopped = [r for r in rows if r[5] != "completed"]
                    by_item = {i: sum(1 for r in stopped if r[0] == i) for i in items}
                    print(f"\norder={order:13s} T-OQ x{toq} eval {eval_s:4.0f} s/snapshot contention {cont}: item caps (s) {({k: round(v) for k, v in caps.items()})}; runs stopped by their item cap: {by_item}")
                    if order == "code" and toq == 1.0 and eval_s == 0.0 and cont == 1.0 and "load" in items:
                        for r in rows:
                            print(f"   {r[0]:7s} {r[1]:42s} start {r[2]:6d} s  train {r[3]:6d} s  deadline {r[4]:6d} s  {r[5]}")
