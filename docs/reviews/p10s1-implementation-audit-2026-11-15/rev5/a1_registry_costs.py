"""Audit script a1 (Claude Opus 5.5 auditor, P10-S1 revision 5 implementation audit; not Astra review).

Rebuilds the revision-5 registry, run lengths, snapshots, calibration cells, seeds, counted work W and the
whole-update multiply-add counts from the ADR text (my own tables and formulas), and compares them with
studies.p10s1.core / frozen. Nothing is trained; no seed is generated; pure arithmetic.

Run from the worktree root:
  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root>
"""

import math
import sys
from collections import Counter

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)

from studies.p10s1 import core  # noqa: E402  (code under audit; compared, not reused for expectations)
from studies.p10s1 import frozen as fz  # noqa: E402

out = []
fails = []


def check(name, ok, detail=""):
    out.append(f"{'OK  ' if ok else 'FAIL'} {name}{(': ' + str(detail)) if detail else ''}")
    if not ok:
        fails.append(name)


# ---- 1. registry from ADR section 5.1 / 6.1 (my tables) ----
GRID = [(2048, 1024), (2048, 4096), (8192, 1024), (8192, 4096), (8192, 16384), (32768, 4096), (32768, 16384)]
EXP = {
    "F-OQ": GRID + [(2048, 256)],
    "T-OQ": GRID,
    "H8": GRID,
    "D-OQ": [(2048, 4096), (8192, 4096), (8192, 16384), (32768, 16384), (8192, 1024), (32768, 4096)],
    "R2": [(2048, 4096), (8192, 16384), (32768, 32768)],
}
per_rep = sum(len(v) for v in EXP.values())
check("configurations per replicate = 31", per_rep == 31, per_rep)
row_up = {2048: 8192, 8192: 8192, 32768: 16384}  # a plausible frozen row U_P (the lead's expectation), for run lengths
u_l = {(8192, 1024): 131072, (32768, 4096): 393216, (2048, 256): 98304}


def exp_run(arm, f, n):
    if (f, n) in u_l:
        return u_l[(f, n)]
    return row_up[f] * (1 if arm == "R2" else 6)


plan = core.Plan(seed_block_draws=(), row_u_p=(8192, 8192, 16384), u_l=(131072, 393216), u_l_256=98304)
cells = core.registered_cells(plan, dense_rates={"4096": 0.01, "16384": 0.03, "8K/1K": 0.003, "32K/4K": 0.001})
check("registered cells = 155", len(cells) == 155, len(cells))
got = Counter((c.arm, c.facts, c.slots) for c in cells)
exp = Counter((a, f, n) for a, v in EXP.items() for f, n in v for _ in range(5))
check("cells per arm equal ADR 6.1 x 5 replicates", got == exp, (got - exp, exp - got))
bad_runs = [(c.label, c.run_updates, exp_run(c.arm, c.facts, c.slots)) for c in cells if c.run_updates != exp_run(c.arm, c.facts, c.slots)]
check("run lengths (U_L at loaded cells and 2K/256 for every arm; 6 U_P of the row; R2 U_P)", not bad_runs, bad_runs[:3])
bad_up = [(c.label, c.u_p) for c in cells if c.u_p != row_up[c.facts]]
check("U_P of a cell is its row's (2K/256 uses the row of 2,048)", not bad_up, bad_up[:3])
seeds_ok = all(c.init_seed == 2100 + c.draw for c in cells)
check("initialization seed 2100 + r", seeds_ok)
dense_lr = {(c.facts, c.slots): c.lr for c in cells if c.arm == "D-OQ"}
exp_lr = {(2048, 4096): 0.01, (8192, 4096): 0.01, (8192, 16384): 0.03, (32768, 16384): 0.03, (8192, 1024): 0.003, (32768, 4096): 0.001}
check("D-OQ rate looked up by unit (4,096 / 16,384 / 8K/1K / 32K/4K)", dense_lr == exp_lr, dense_lr)
no256 = core.registered_cells(core.Plan(seed_block_draws=(), sat256=False))
check("without 2K/256: 150 cells", len(no256) == 150, len(no256))
sb1 = core.registered_cells(core.Plan(seed_block_draws=(1,)))
sb = [c for c in sb1 if c.kind == "SB"]
check("seed block draw 1: 14 cells, F-OQ x 7 grid cells x seeds 2111/2121", len(sb) == 14 and {c.init_seed for c in sb} == {2111, 2121} and {(c.facts, c.slots) for c in sb} == set(GRID), (len(sb), sorted({c.init_seed for c in sb})))
sb12 = [c for c in core.registered_cells(core.Plan(seed_block_draws=(1, 2))) if c.kind == "SB"]
check("seed block draws 1+2: 28 cells, seeds 2111/2121/2112/2122", len(sb12) == 28 and {c.init_seed for c in sb12} == {2111, 2121, 2112, 2122})

# refusals
for arm in ("T-OQ", "H8", "D-OQ"):
    try:
        core.make_cell("P", arm, 2048, 256, 1, 2101)
        check(f"{arm} refused at 256 slots", False)
    except ValueError:
        check(f"{arm} refused at 256 slots", True)
try:
    core.work_formula("F-OQ-IVF", 256, candidates=512)
    check("index read refused at 256 slots", False)
except ValueError:
    check("index read refused at 256 slots", True)
for arm in ("F-OQ", "T-OQ", "H8", "D-OQ", "R2"):
    try:
        core.make_cell("P", arm, 8192, 65536, 1, 2101)
        check(f"no 65,536-slot {arm} cell constructible", False)
    except ValueError:
        check(f"no 65,536-slot {arm} cell constructible", True)
try:
    core.parse_label("P_F-OQ_f32768_n65536_d1_i2101")
    check("65,536-slot label refused", False)
except ValueError:
    check("65,536-slot label refused", True)

# snapshots of a loaded cell (ADR 5.4): U_P x {1/16..4}, U_run/2, U_run, 32,768, 49,152, every candidate <= U_L and its half
c81 = next(c for c in cells if c.arm == "F-OQ" and (c.facts, c.slots) == (8192, 1024) and c.draw == 1)
snaps = set(core.cell_snapshot_updates(c81, 8192))
need = {512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 49152, 98304}
check("8K/1K F-OQ snapshots cover U_P grid, 32,768, 49,152, candidates <= U_L and halves", need <= snaps, sorted(need - snaps))
c324 = next(c for c in cells if c.arm == "D-OQ" and (c.facts, c.slots) == (32768, 4096) and c.draw == 1)
snaps = set(core.cell_snapshot_updates(c324, 8192))
need = {1024, 2048, 4096, 8192, 16384, 32768, 65536, 49152, 131072, 196608, 262144, 393216, 98304, 196608}
check("32K/4K D-OQ (U_L 393,216) snapshots: candidates and halves present", need <= snaps, sorted(need - snaps))
c256 = next(c for c in cells if (c.facts, c.slots) == (2048, 256) and c.draw == 1)
snaps = set(core.cell_snapshot_updates(c256, 8192))
check("2K/256 (U_L 98,304) snapshots", {65536, 98304, 32768, 49152} <= snaps, sorted(snaps))

# Plan: U_L can never be the first candidate under the two-consecutive rule; does Plan refuse it?
try:
    core.Plan(u_l=(65536, 131072))
    check("Plan refuses U_L equal to the first candidate (impossible under the rule) [placeholder detectable]", False, "accepted: the placeholder U_L is a valid-looking plan")
except ValueError:
    check("Plan refuses U_L equal to the first candidate", True)

# ---- 2. calibration (ADR 10.1) ----
cal = core.calibration_cells({2048: 8192, 8192: 8192, 32768: 16384})
check("calibration runs = 70", len(cal) == 70, len(cal))
by_item = Counter()
for c in cal:
    if c.arm == "D-OQ":
        by_item["dense"] += 1
    elif c.arm == "H8":
        by_item["h8"] += 1
    elif (c.facts, c.slots) in [(8192, 1024), (32768, 4096), (2048, 256)]:
        by_item["load"] += 1
    else:
        by_item["row"] += 1
check("10 / 12 / 8 / 40", dict(by_item) == {"load": 10, "row": 12, "h8": 8, "dense": 40}, dict(by_item))
check("calibration init seed 2191 on draw 1, 2193 on draw 2", all(c.init_seed == {1: 2191, 2: 2193}[c.draw] for c in cal))
ceil = {(8192, 1024): 262144, (2048, 256): 262144, (32768, 4096): 524288}
check("load search runs to its ceiling", all(c.run_updates == ceil[(c.facts, c.slots)] for c in cal if c.arm in ("F-OQ", "T-OQ") and (c.facts, c.slots) in ceil))
check("load search arms: F-OQ+T-OQ at 8K/1K, 32K/4K; F-OQ alone at 2K/256", Counter((c.arm, c.facts, c.slots) for c in cal if (c.facts, c.slots) in ceil and c.arm != "D-OQ") == Counter({("F-OQ", 8192, 1024): 2, ("T-OQ", 8192, 1024): 2, ("F-OQ", 32768, 4096): 2, ("T-OQ", 32768, 4096): 2, ("F-OQ", 2048, 256): 2}))
rowc = Counter((c.arm, c.facts, c.slots, c.run_updates) for c in cal if c.arm in ("F-OQ", "R2") and (c.facts, c.slots) not in ceil)
check("row U_P runs: F-OQ 2K/4K, 8K/4K, 32K/16K; R2 2K/4K, 8K/16K, 32K/32K, to 32,768", rowc == Counter({(a, f, n, 32768): 2 for a, f, n in [("F-OQ", 2048, 4096), ("F-OQ", 8192, 4096), ("F-OQ", 32768, 16384), ("R2", 2048, 4096), ("R2", 8192, 16384), ("R2", 32768, 32768)]}), rowc)
dense = [c for c in cal if c.arm == "D-OQ"]
unit_of = {(8192, 4096): ("4096", 8192), (32768, 16384): ("16384", 16384), (8192, 1024): ("8K/1K", 65536), (32768, 4096): ("32K/4K", 65536)}
check("dense: 4 units x 5 rates x 2 draws, run to row U_P or 65,536", Counter((c.facts, c.slots) for c in dense) == Counter({k: 10 for k in unit_of}) and all(c.run_updates == unit_of[(c.facts, c.slots)][1] for c in dense) and sorted({c.lr for c in dense}) == [0.001, 0.003, 0.01, 0.03, 0.1])
h8 = [c for c in cal if c.arm == "H8"]
check("H8 at 2K/4K, 8K/4K, 8K/16K, 32K/16K to its row's U_P", Counter((c.facts, c.slots, c.run_updates) for c in h8) == Counter({(2048, 4096, 8192): 2, (8192, 4096, 8192): 2, (8192, 16384, 8192): 2, (32768, 16384, 16384): 2}))

# ---- 3. G9 with 2193 and its derived seeds ----
ns = core.seed_namespaces()
check("2193 and 2193 + 1000 k declared", 2193 in ns["init"] and all(2193 + 1000 * k in ns["derived_init"] for k in range(1, 6)))
check("G9 passes on the declared namespaces", core.seed_check()["passed"], core.seed_check()["overlaps"][:3])

# ---- 4. counted work W and D-OQ width (ADR 7.4, 5.3) ----
def W(arm, n):
    K = {"F-OQ": n, "T-OQ": n // 256 + 512, "H8": 0, "R2": 0}[arm]
    V = 1 if arm == "R2" else 8
    return 16 * K + 32 * V + 1024


exp_w = {("F-OQ", 256): 5376, ("F-OQ", 1024): 17664, ("F-OQ", 4096): 66816, ("F-OQ", 16384): 263424, ("T-OQ", 1024): 9536, ("T-OQ", 4096): 9728, ("T-OQ", 16384): 10496, ("H8", 1024): 1280, ("R2", 4096): 1056}
for (arm, n), v in exp_w.items():
    check(f"W {arm} {n} = {v} (ADR table; my formula {W(arm, n)})", core.work_formula(arm, n)["W"] == v == W(arm, n))
for n in (1024, 4096, 16384):
    p = 48 * n + 1025
    h = round((p - 1) / 49)
    check(f"D-OQ h at {n} = {h}, 49h+1 within 0.1% of {p}", core.doq_hidden(n) == h and abs(49 * h + 1 - p) / p <= 0.001, (core.doq_hidden(n), 49 * h + 1))
check("T-OQ at 1,024: 4 branches, 512 candidates", core.work_formula("T-OQ", 1024)["K"] == 4 + 512)

# whole-update multiply-adds (ADR 22 M6 and 22.1; formula from the config text, recomputed by me)
B, T, Q = 16, 63, 128
attn = 4 * T * T * 8
backbone = B * (2 * (T * 32 * 96 + attn + attn + T * 32 * 32 + 2 * T * 32 * 64) + T * 32 * 256) + B * (T * 32 * 96 + T * 32 * 32 + 2 * T * 32 * 64 + 4 * attn + T * 32 * 256)


def params(arm, n):
    if arm == "F-OQ":
        return 48 * n + 1025
    if arm == "T-OQ":
        return 48 * n + (n // 256) * 16 + 1025
    if arm in ("H8", "R2"):
        return 32 * n + 1025
    h = round((48 * n + 1024) / 49)
    return 49 * h + 1


def madds(arm, n):
    wo = 3 * Q * 32 * 32
    if arm == "F-OQ":
        m = 2 * Q * n * 16 + wo
        g = Q * 24 * 32
    elif arm == "T-OQ":
        m = 2 * Q * ((n // 256) * 16 + 512 * 16) + wo
        g = Q * 24 * 32
    elif arm == "H8":
        m, g = wo, Q * 16 * 32
    elif arm == "R2":
        m, g = wo, Q * 2 * 32
    else:
        h = round((48 * n + 1024) / 49)
        m, g = 2 * Q * 16 * h + 3 * Q * h * 32, 0
    return backbone + m + g + 4 * params(arm, n)


out.append(f"     backbone multiply-adds per update (mine) = {backbone:,}; code = {fz.backbone_madds()['total']:,}")
check("backbone madds equal", backbone == fz.backbone_madds()["total"])
for arm in ("F-OQ", "T-OQ", "H8", "R2", "D-OQ"):
    for n in core.arm_slot_counts()[arm]:
        mine, code = madds(arm, n), fz.analytic_madds_per_update(arm, n)
        check(f"madds {arm} {n}: {mine:,.0f}", abs(mine - code) < 0.5, code)
adr = {"F-OQ": (1.2, 1.7, 2.5), "T-OQ": (1.2, 2.0, 5.1), "H8": (1.3, 2.1, 5.4)}
for arm, vals in adr.items():
    got = tuple(madds("D-OQ", n) / madds(arm, n) for n in (1024, 4096, 16384))
    check(f"analytic multiplier D-OQ/{arm} at 1K/4K/16K = {', '.join(f'{x:.3f}' for x in got)} (ADR 25.7: {vals})", all(abs(round(g, 1) - v) < 0.051 for g, v in zip(got, vals, strict=True)))
    grid = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
    snaps = [next((x for x in grid if x >= g - 1e-12), None) for g in got]
    check(f"  MC grid snapshot for D-OQ/{arm} exists and <= 6 U_P on the analytic measure: {snaps}", all(s is not None and s <= 6 for s in snaps))
for arm in ("F-OQ", "T-OQ", "H8"):
    r = [madds(arm, 4 * n) / madds(arm, n) for n in (1024, 4096)]
    out.append(f"     analytic step cost ratio {arm} 1K->4K, 4K->16K: {r[0]:.4f}, {r[1]:.4f}")

print("\n".join(out))
print(f"\n{len(fails)} FAIL: {fails}")
