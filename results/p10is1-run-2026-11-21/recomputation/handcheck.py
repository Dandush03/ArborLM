# ruff: noqa
"""Hand checks of the registered labels that the regression of recompute.py never reached, computed DIRECTLY from the raw per-cell records
(evaluate/<label>/uXXXXXXXX.json) with an inline i formula and the ADR's printed chance bounds, not through recompute.py's functions.
Auditor: arbor-auditor (Opus 5.5), 2026-11-21. Usage: python3 -I handcheck.py <run dir> <frozen plan> <madds json> <timing.json>"""

import json
import math
import sys
from pathlib import Path

run, planp, maddsp, timingp = (Path(x) for x in sys.argv[1:5])
plan = json.loads(planp.read_text())
madds = json.loads(maddsp.read_text())
cpu = json.loads(timingp.read_text())["cpu"]
HI = {2048: 100, 8192: 325, 32768: 1159}  # ADR-0021 8.1 G2 upper chance bounds, as printed
by = {(c["arm"], c["facts"], c["slots"], c["draw"]): c for c in plan["cells"]}
stops = {json.loads(p.read_text())["cell_name"]: json.loads(p.read_text())["u_run"] for p in (run / "ladder").glob("*_*.json")}


def i_of(useful, n):
    if useful <= HI[n]:
        return 0.0
    e = 1 - useful / n
    if e <= 0:
        return 5.0
    return 5 - (-e * math.log2(e) - (1 - e) * math.log2(1 - e)) - e * math.log2(31)


def rec(arm, f, n, d, u, read="main"):
    c = by[(arm, f, n, d)]
    r = json.loads((run / "evaluate" / c["label"] / f"u{u:08d}.json").read_text())
    return r["reads"][read]["panels"]


def urun(c):
    if c["ladder_cell"]:
        nm = f"{c['facts'] // 1024}K/{c['slots'] // 1024 if c['slots'] >= 1024 else c['slots']}{'K' if c['slots'] >= 1024 else ''}"
        return stops[nm]
    return c["run"]


def series(arm, f, n, d, read="main"):
    c = by[(arm, f, n, d)]
    return {u: {p: i_of(v["useful"], v["n"]) for p, v in rec(arm, f, n, d, u, read).items()} for u in c["snapshots"] if u <= urun(c)}


out = {}
# 1. a_use at U_P at 32K/16K (arm class row 3: >= 0.80 in all 5, both panels)
out["a_use_32K16K_at_U_P"] = {}
for arm, read in (("F-OQ", "main"), ("F-OQ", "ivf"), ("T-OQ", "main"), ("H8", "main")):
    vals = [round(v["useful"] / v["n"], 4) for d in range(1, 6) for v in rec(arm, 32768, 16384, d, 8192, read).values()]
    out["a_use_32K16K_at_U_P"][f"{arm}/{read}"] = {"min": min(vals), "all_ge_0.80": min(vals) >= 0.80}
# 2. dense at 32K/16K and 8K/4K for F-OQ, T-OQ, H8: MU, D-BEST, and MC-A / MC-T (D-OQ costlier -> arm read at the smallest grid multiple >= ratio)
grid = [1, 1.25, 1.5, 2, 2.5, 3, 4, 6]
out["dense"] = {}
for arm in ("F-OQ", "T-OQ", "H8"):
    for f, n in ((32768, 16384), (8192, 4096), (8192, 16384), (2048, 4096)):
        row = {"MU": [], "D-BEST": [], "MC-A": [], "MC-T": []}
        for d in range(1, 6):
            sa, sd = series(arm, f, n, d), series("D-OQ", f, n, d)
            best = max(sd, key=lambda u: (sd[u]["A"], -u)), max(sd, key=lambda u: (sd[u]["B"], -u))
            row["MU"].append(min(sa[8192][p] - sd[8192][p] for p in "AB"))
            row["D-BEST"].append(min(sa[8192][p] - sd[best[k]][p] for k, p in enumerate("AB")))
            for k, (ca, cd) in (("MC-A", (madds[f"{arm}|{n}"], madds[f"D-OQ|{n}"])), ("MC-T", (cpu[f"{arm}|{n}"], cpu[f"D-OQ|{n}"]))):
                if cd >= ca:
                    m = next((g for g in grid if g >= cd / ca - 1e-12), None)
                    ua, ud = (int(m * 8192) if m else None), 8192
                else:
                    m = next((g for g in grid if g >= ca / cd - 1e-12), None)
                    ua, ud = 8192, (int(m * 8192) if m else None)
                row[k].append(None if (ua is None or ud is None or ua not in sa or ud not in sd) else min(sa[ua][p] - sd[ud][p] for p in "AB"))
        out["dense"][f"{arm} {f // 1024}K/{n // 1024}K"] = {k: {"min_d_per_rep": [None if v is None else round(v, 3) for v in vs], "reps_le_-0.25": sum(1 for v in vs if v is not None and v <= -0.25)} for k, vs in row.items()}
# 3. dense at saturation at the loaded cells: an upper bound for the arm (i* over all its snapshots up to U_run) against D-OQ's i* up to its U_run
out["dense_sat_upper_bound"] = {}
for arm, read in (("F-OQ", "main"), ("F-OQ", "ivf"), ("T-OQ", "main"), ("H8", "main")):
    for f, n in ((8192, 1024), (32768, 4096)):
        ds = []
        for d in range(1, 6):
            sa, sd = series(arm, f, n, d, read), series("D-OQ", f, n, d)
            ds.append(max(min(max(v[p] for v in sa.values()) - max(v[p] for v in sd.values()) for p in "AB"), -99))
        out["dense_sat_upper_bound"][f"{arm}/{read} {f // 1024}K/{n // 1024}K"] = {"max_over_panels_of_istar_arm_minus_istar_dense_per_rep": [round(x, 3) for x in ds]}
# 4. sparse: T-OQ / F-OQ-IVF i ratio at U_P at 8K/4K and 32K/16K
out["sparse_U_P"] = {}
for f, n in ((8192, 4096), (32768, 16384)):
    rs = []
    for d in range(1, 6):
        t, v = rec("T-OQ", f, n, d, 8192), rec("F-OQ", f, n, d, 8192, "ivf")
        rs.append(min(i_of(t[p]["useful"], t[p]["n"]) / i_of(v[p]["useful"], v[p]["n"]) for p in "AB"))
    out["sparse_U_P"][f"{f // 1024}K/{n // 1024}K"] = [round(x, 4) for x in rs]
# 5. efficiency: min-panel i at each snapshot of the N-step cells (u_T is where it first reaches 3.0)
out["efficiency_first_snapshot_i_ge_3"] = {}
for arm in ("F-OQ", "T-OQ"):
    for f, n in ((2048, 1024), (2048, 4096), (8192, 4096), (8192, 16384)):
        firsts = []
        for d in range(1, 6):
            s = series(arm, f, n, d)
            us = sorted(s)
            hit = next((u for u in us if min(s[u].values()) >= 3.0), None)
            firsts.append([us[0], hit])
        out["efficiency_first_snapshot_i_ge_3"][f"{arm} {f // 1024}K/{n // 1024}K"] = firsts
print(json.dumps(out, indent=1))
