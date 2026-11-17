"""Audit script a6 (Claude Opus 5.5 auditor; P10-S1 revision 5 implementation audit; not Astra review).

The cap rule of ADR-0021 section 10.3 recomputed by me and compared with studies.p10s1.budget: C_need = charged + 2 x remaining,
cap = ceil(C_need) hours if C_need <= C_max = 36 h, the three cuts in their order, NOT STARTED: BUDGET after the last, c never
below 1.0, longest-first packing. Synthetic rates only (nothing measured).

  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root>
"""

import math
import sys

sys.path.insert(0, sys.argv[1])
from studies.p10s1 import budget, core  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

out, fails = [], []


def check(name, ok, detail=""):
    out.append(f"{'OK  ' if ok else 'FAIL'} {name}{(': ' + str(detail)) if detail != '' else ''}")
    if not ok:
        fails.append(name)


def my_lpt(jobs, k=6):
    loads = [0.0] * k
    for j in sorted(jobs, reverse=True):
        i = loads.index(min(loads))
        loads[i] += j
    return max(loads)


jobs = [7, 5, 4, 4, 3, 3, 2, 2, 2, 1, 1, 9, 6]
check("LPT makespan", budget.makespan(jobs) == my_lpt(jobs), (budget.makespan(jobs), my_lpt(jobs)))
c = budget.contention_ratio({("F-OQ", 4096): 0.009, ("T-OQ", 4096): 0.010}, {("F-OQ", 4096): 0.010, ("T-OQ", 4096): 0.011})
check("c never below 1.0 (all ratios < 1)", c["c"] == 1.0, c)
c = budget.contention_ratio({("F-OQ", 4096): 0.012, ("T-OQ", 4096): 0.010}, {("F-OQ", 4096): 0.010, ("T-OQ", 4096): 0.010})
check("c = the largest ratio", abs(c["c"] - 1.2) < 1e-12, c)
cm = 36 * 3600.0
for charged_h, rem_h in ((1.57, 10.0), (5.9, 15.0), (6.0, 15.0), (6.0, 15.0001), (0.0, 18.0)):
    h = budget.headroom_rule(charged_h * 3600, rem_h * 3600, cm)
    need = charged_h + 2 * rem_h
    exp_ok = need <= 36 + 1e-9
    check(f"headroom charged {charged_h} h + 2 x {rem_h} h = {need:.4f} h -> ok {exp_ok}, cap {math.ceil(need - 1e-12) if exp_ok else None}", h.ok == exp_ok and h.cap_hours == (math.ceil(need - 1e-9) if exp_ok else None), (h.ok, h.cap_hours))
seq = budget.cut_sequence(core.Plan())
check("cut order: none (draws 1+2) -> cut 1 -> cut 2 -> cut 3 (D-OQ 8K/16K)", [(p.seed_block_draws, p.dense_cut) for p, _ in seq] == [((1, 2), ()), ((1,), ()), ((), ()), ((), ("8K/16K",))])
check("the cuts never remove 2K/256, a replicate, H8 or another D-OQ cell", all(p.sat256 == core.Plan().sat256 for p, _ in seq) and all(len([c for c in core.registered_cells(p) if c.kind == "P"]) in (155, 150) for p, _ in seq[:3]) and len([c for c in core.registered_cells(seq[3][0]) if c.kind == "P"]) == 150)

# choose_plan on synthetic rates: scale every rate so that the need lands in each region
items = budget.rehearsal_items(core.Plan())
cpu = fz.default_cpu_table()
iso = {k: v for k, v in cpu.items()}


def plan_for(scale, charged_h=5.0):
    rates = {i: budget.Rate(cpu[(i[0], i[2])] * scale, 5.0 * scale, 1.0, 10**9) for i in items}
    return budget.choose_plan(rates, budget.Fixed(gates=600, timing=600, simulate=60, analysis=60, report=60, generate=300), cpu, charged_seconds=charged_h * 3600, cap_max_seconds=cm, base=core.Plan(), isolated={k: v * scale for k, v in iso.items()}, c=1.0)


results = []
for scale in (1, 3, 5, 6, 7, 8, 9, 10, 12, 20):
    r = plan_for(scale)
    tried = [(t["cuts"][-1] if t["cuts"] else "none", round(t["required_seconds"] / 3600, 2)) for t in r.tried]
    results.append((scale, r.ok, r.applied_cuts[-1] if r.applied_cuts else "none", r.returns_to_lead[:40] if r.returns_to_lead else None, tried))
    out.append(f"     rate scale {scale:>3}: ok={r.ok} cuts={r.applied_cuts[-1] if r.applied_cuts else 'none'} tried={tried} {'-> ' + r.returns_to_lead[:60] if r.returns_to_lead else ''}")
    for k in range(1, len(r.tried)):
        check(f"scale {scale}: a cut is tried only after the previous plan failed", not r.tried[k - 1]["ok"])
    if r.ok:
        check(f"scale {scale}: the plan chosen is the first that fits", r.tried[-1]["ok"] and r.tried[-1]["required_seconds"] <= cm)
    else:
        check(f"scale {scale}: NOT STARTED: BUDGET after the last cut", len(r.tried) == 4 and budget.NOT_STARTED_BUDGET in (r.returns_to_lead or ""))
regions = {x[2] for x in results if x[1]} | ({"NOT STARTED"} if any(not x[1] for x in results) else set())
check("every region reached on synthetic rates (none, cut 1, cut 2, cut 3, NOT STARTED)", {"none", "NOT STARTED"} <= regions, regions)

print("\n".join(out))
print(f"\n{len(fails)} FAIL: {fails}")
