# ruff: noqa
"""Auditor's rate-selection check (ADR-0031 section 8, rulings 5 and G14), run AFTER the registered outcome was recomputed.
Reads ONLY <sealed_dir>/rehearsal_sealed.json (hash checked first) and the frozen rate_table.json. Imports nothing from the study.
Also recomputes the calibration convergence states (sealed 'states') from the curves, for the section 12.5 comparison.
Run: python3 -I check_rate_selection.py <sealed_json> <frozen_rate_table_json>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

SEALED, RT = Path(sys.argv[1]), Path(sys.argv[2])
HERE = Path(__file__).resolve().parent
raw = SEALED.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
EXPECT = "e85caefc82db263a5a233f7fd4bac120035408b682d03fa40a5a1860a47deda2"  # rehearsal_public.json sealed_sha256
assert sha == EXPECT, sha
d = json.loads(raw)
rt = json.loads(RT.read_text())
U = {-1: 8192, 0: 16384, 1: 32768, 2: 65536, 3: 131072, 4: 262144}
TIE = 0.0005
EPS = 0.001
res = {"sealed_sha256": sha, "arms": {}}
agree = True


def mean3(xs):
    s = 0.0
    for x in xs:
        s += x
    return s / len(xs)


for arm, by_rate in d["curves"].items():
    rates = sorted(by_rate, key=float)
    res["arms"][arm] = {}
    for k, u in U.items():
        # finite in all three cells through U_k (every snapshot <= U_k)
        fin = [r for r in rates if all(math.isfinite(by_rate[r][str(c)][str(uu)]) for c in range(3) for uu in U.values() if uu <= u)
               and all(str(c) in by_rate[r] for c in range(3))]
        means = {r: mean3([by_rate[r][str(c)][str(u)] for c in range(3)]) for r in fin}
        m = min(means.values())
        minimiser = min((r for r in fin if means[r] == m), key=float)  # exact tie -> smaller
        within = sorted((r for r in fin if means[r] - m <= TIE), key=float)
        sel = float(within[0])
        i = rates.index(minimiser)
        edge_low = i == 0
        edge_high = i == len(rates) - 1
        frozen = rt["rates"][arm][str(k)]
        ok = sel == frozen and not edge_low and not edge_high and rt["interior"][arm][str(k)] is True
        agree &= ok
        res["arms"][arm][k] = dict(selected=sel, frozen=frozen, match=ok, minimiser=float(minimiser), within_tolerance=[float(x) for x in within],
                                   gap_selected_minus_min=means[within[0]] - m, rates_finite=len(fin), rates_run=len(rates),
                                   minimiser_at_edge=edge_low or edge_high)
    # calibration envelope / run convergence states (sealed 'states')
    L = {k: mean3([by_rate[f"{res['arms'][arm][k]['selected']:g}"][str(c)][str(U[k])] for c in range(3)]) for k in U}
    st = {}
    for k in range(0, 5):
        r = f"{res['arms'][arm][k]['selected']:g}"
        dl = L[k - 1] - L[k]
        dr = mean3([by_rate[r][str(c)][str(U[k - 1])] for c in range(3)]) - L[k]
        st[k] = dict(delta=dl, delta_run=dr, state="CONVERGED" if (dl < EPS and dr < EPS) else "NOT CONVERGED",
                     sealed_state=d["states"][arm][str(k)]["state"],
                     sealed_delta_equal=dl == d["states"][arm][str(k)]["delta"], sealed_drun_equal=dr == d["states"][arm][str(k)]["delta_run"])
    res["arms"][arm]["calibration_states"] = st
res["agree"] = agree
(HERE / "rate_selection_out.json").write_text(json.dumps(res, indent=1, default=str))
print("sealed sha256", sha, "== rehearsal_public.json:", sha == EXPECT)
for arm, v in res["arms"].items():
    for k in U:
        x = v[k]
        print(arm, k, "selected", x["selected"], "frozen", x["frozen"], "match", x["match"], "minimiser", x["minimiser"],
              "within 0.0005:", x["within_tolerance"], f"gap {x['gap_selected_minus_min']:.6f}", "finite", x["rates_finite"], "/", x["rates_run"],
              "edge", x["minimiser_at_edge"])
    for k, s in v["calibration_states"].items():
        print("  cal state", arm, k, s["state"], "sealed", s["sealed_state"], "delta==sealed", s["sealed_delta_equal"], "drun==sealed", s["sealed_drun_equal"])
print("AGREE" if agree else "DISAGREE")
