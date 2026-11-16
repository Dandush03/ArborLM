"""Recheck script r3 = a3 re-run against f1e8ebb (Claude Opus 5.5 auditor; P10-S1 rev-5 fix recheck; not Astra review).

Question 1 (B1): under the NEW dispatch order (budget.dispatch_order, which calibration_tasks now uses) and the NEW caps
(budget.item_projection: 2 x the item's projected completion from the stage start, training only), is any run stopped?
Question 2 (the open item 'caps bound training only'): with a start-up before training and evaluation after it (the worker
is busy for both; the deadline is a wall-clock instant counted from the stage start and only checked inside the training
loop), and with contention c on the training rate, can a run lose its U_L / row U_P / H8 value / dense rate to start-up?

The code is used only for: the dispatch order and the cap values (what is under audit). The schedule is my own simulator:
list order, first free worker (pool.py run_stage launches pending tasks in list order on free slots); task = start-up S,
then training (updates x rate x c), stopped at the deadline (ItemCapReached checked before every update), then evaluation
E seconds per snapshot only if training completed. Also the old order (load first) is shown to confirm B1's reproduction.

ASSUMED rates: revision 4's measured six-worker wall seconds per update as used in the implementer's own test (WALL), and
x2 of them. S and E from r0 (revision 4: start-up ~6-16 s per task, 2-51 s per snapshot, size dependent); E here is
taken per facts size: 8K and below 8 s, 32K 46 s (r0 medians), and a x2 variant. Projections, not measurements.

  UV_NO_SYNC=1 nice uv run --locked python -I r3_itemcap_schedule.py <worktree root>
"""
import sys
sys.path.insert(0, sys.argv[1])
from studies.p10s1 import budget, calibrate, core  # noqa: E402

WALL = {("F-OQ", 256): 0.004, ("F-OQ", 1024): 0.006, ("F-OQ", 4096): 0.0093, ("F-OQ", 16384): 0.0153, ("T-OQ", 1024): 0.006, ("T-OQ", 4096): 0.0093, ("T-OQ", 16384): 0.0153,
        ("H8", 1024): 0.005, ("H8", 4096): 0.0075, ("H8", 16384): 0.0101, ("D-OQ", 1024): 0.009, ("D-OQ", 4096): 0.0118, ("D-OQ", 16384): 0.0235,
        ("R2", 4096): 0.0091, ("R2", 16384): 0.0102, ("R2", 32768): 0.0188}
ROWS_MAX = {f: max(core.row_u_p_candidates()) for f in core.ROW_FACTS}
ROWS_MIN = {f: min(core.row_u_p_candidates()) for f in core.ROW_FACTS}


def eval_s(cell, e_scale):
    return e_scale * (46.0 if cell.facts >= 32768 else 8.0)


def simulate(ordered, rate, caps, startup, c, e_scale, workers=6):
    free = [0.0] * workers
    out = []
    for item, cell in ordered:
        k = free.index(min(free))
        s = free[k]
        t0 = s + startup
        train = cell.run_updates * rate[(cell.arm, cell.slots)] * c
        dl = caps[item]
        if t0 >= dl:
            end, status, slack = t0, "STOPPED AT UPDATE 0", dl - (t0 + train)
        elif t0 + train > dl:
            end, status, slack = dl, "STOPPED MID-RUN", dl - (t0 + train)
        else:
            end = t0 + train + eval_s(cell, e_scale) * len(calibrate.calibration_snapshots(cell))
            status, slack = "completed", dl - (t0 + train)
        free[k] = end
        out.append((item, cell.label, s, t0 + train, dl, status, slack))
    return out


print(__doc__.split("The code is used")[0].strip(), "\n")
worst = {}
slack = {}
for group, rows_proj, rows_run, tag in ((("load", "row-up"), None, None, "items 0b+1"),
                                         (("h8", "dense"), ROWS_MAX, ROWS_MAX, "items 2+3, rows at max candidate (caps and runs)"),
                                         (("h8", "dense"), ROWS_MIN, ROWS_MIN, "items 2+3, rows at min candidate (caps and runs)")):
    for scale in (1.0, 2.0):
        rate = {k: v * scale for k, v in WALL.items()}
        proj = budget.item_projection(rate, core.U_P, rows_proj)
        caps = {i: proj[i]["cap_seconds"] for i in group}
        for order_name in (("code", "old (load first)") if "load" in group else ("code",)):
            if order_name == "code":
                ordered = budget.dispatch_order(group, core.U_P, rows_run)
            else:
                ordered = [("load", x) for x in core.load_search_cells()] + [("row-up", x) for x in core.row_u_p_cells()]
            for startup in (0.0, 16.0, 30.0, 60.0):
                for c in (1.0, 1.25, 1.5):
                    for e_scale in (1.0, 2.0):
                        res = simulate(ordered, rate, caps, startup, c, e_scale)
                        stopped = {i: sum(1 for r in res if r[0] == i and r[5] != "completed") for i in group}
                        minslack = {i: round(min(r[6] for r in res if r[0] == i)) for i in group}
                        key = (tag, order_name, scale)
                        for i in group:
                            prev = slack.get((tag, order_name, i))
                            if prev is None or minslack[i] < prev[0]:
                                slack[(tag, order_name, i)] = (minslack[i], scale, startup, c, e_scale)
                        if any(stopped.values()) or startup in (0.0, 16.0) and c == 1.0 and e_scale == 1.0:
                            print(f"{tag:48s} order={order_name:16s} rates x{scale} start-up {startup:4.0f} s c {c:4.2f} eval x{e_scale}: caps {({k: round(v) for k, v in caps.items()})} stopped {stopped} min slack (s) {minslack}")
                        if any(stopped.values()):
                            worst.setdefault(key, []).append((startup, c, e_scale, stopped))
print("\nSUMMARY of settings with any stopped run (code order only matters for the verdict):")
for k, v in worst.items():
    print(" ", k, "->", len(v), "settings; first:", v[0])
print("\nWORST min slack (deadline minus training end, s) per item over all 48 settings (rates x1/x2, start-up 0/16/30/60 s, c 1/1.25/1.5, eval x1/x2):")
for k, v in slack.items():
    print(" ", k, "->", v[0], "s at rates x%s start-up %s c %s eval x%s" % v[1:])
