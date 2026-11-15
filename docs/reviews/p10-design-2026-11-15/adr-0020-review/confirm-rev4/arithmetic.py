"""Auditor's independent arithmetic for ADR-0020 rev4 (cells, budget, R2 reading A, bounds, P9-II rates).
Standard library only. Usage: python3 -I arithmetic.py <worktree>
"""
import csv
import math
import statistics as st
import sys
from pathlib import Path

wt = Path(sys.argv[1])
U = 8192
arms_core = ["A0", "A1", "A2", "A5-D"]
nL = len(arms_core)

# ---- cells -------------------------------------------------------------
c_2k4k = 20 * nL + 2 * 10          # learned 10 draws x 2 seeds; A6, A7 x 10 (seed 2001)
c_8k16k = 20 * nL + 2 * 10
c_8k4k = 10 * 2 + 10              # A0, A5-D x 10 (alternating seeds), A6 x 10
q1 = c_2k4k + c_8k16k + c_8k4k
wx, probe = 10 + 10, 3 * 2
cut3_8k16k = 10 * nL + 20
print(f"cells: 2K/4K {c_2k4k}, 8K/16K {c_8k16k}, 8K/4K {c_8k4k}; Q1 {q1}; with Q2 {q1 + wx + probe}; +3 check")
print(f"cut 3: 8K/16K {cut3_8k16k}, Q1 {c_2k4k + cut3_8k16k + c_8k4k}; three-arm Q1 {(20*3+20)*2 + 20}")

# ---- budget (ADR's P9-I rates, s/update; fastest / W7 / slowest) ---------
R = {4096: (0.008, 0.0098, 0.0112), 16384: (0.013, 0.0141, 0.0195), 65536: (0.035, 0.0531, 0.0619)}


def hours(blocks):
    return [sum(n * upd * R[s][i] for n, upd, s in blocks) / 3600 for i in range(3)]


Q1 = [(c_2k4k, U, 4096), (c_8k16k, 4 * U, 16384), (c_8k4k, 4 * U, 4096)]
Q1c3 = [(c_2k4k, U, 4096), (cut3_8k16k, 4 * U, 16384), (c_8k4k, 4 * U, 4096)]
Q1_3arm = [(80, U, 4096), (80, 4 * U, 16384), (20, 4 * U, 4096)]
WX = [(10, U, 4096), (10, 4 * U, 16384)]
PR = [(6, 16 * U, 65536)]
fmt = lambda v: " / ".join(f"{x:.2f}" for x in v)
q1h, wxh, prh, c3h, q13h = hours(Q1), hours(WX), hours(PR), hours(Q1c3), hours(Q1_3arm)
six = lambda v: [x / 6 for x in v]
pr6 = [x / 6 for x in prh]  # one round of six cells = per-cell time
print("summed CPU-h Q1", fmt(q1h), "| WX", fmt(wxh), "| probe", fmt(prh), "| Q1 cut3", fmt(c3h))
print("six-worker  Q1", fmt(six(q1h)), "| WX", fmt(six(wxh)), "| probe", fmt(pr6), "| Q1 cut3", fmt(six(c3h)))
OV = 0.8
whole = [six(q1h)[i] + six(wxh)[i] + pr6[i] + OV for i in range(3)]
whole3 = [six(q13h)[i] + six(wxh)[i] + pr6[i] + OV for i in range(3)]
print("whole plan", fmt(whole), "doubled", fmt([2 * x for x in whole]), f"left {16 - 2*whole[2]:.2f} h ({(16-2*whole[2])/16:.1%})")
print("three-arm whole", fmt(whole3))
s = 2  # slowest index
q, w, p, c = six(q1h)[s], six(wxh)[s], pr6[s], six(c3h)[s]
print("rev3-style multiples (16-1.6)/(2*block): uncut %.3f, no probe %.3f, Q1 %.3f, Q1 cut3 %.3f, 3-arm uncut %.3f" % (
    14.4 / (2 * (q + w + p)), 14.4 / (2 * (q + w)), 14.4 / (2 * q), 14.4 / (2 * c), 14.4 / (2 * (whole3[s] - OV))))
print(f"R2 bullets: pre-Q1 2*(0.8+Q1) = {2*(OV+q):.2f}; post-Q1 {OV+q:.2f} + 2*(WX+probe) = {OV+q+2*(w+p):.2f}; Q1 at cap {OV+2*q+2*(w+p):.2f}")

# Under reading A (rates = m x slowest): which m triggers which cut?
# pre-Q1: 2*(0.8 + Q1*m) <= 16 (drafter's convention: the 0.8 counted as still to run, doubled)
# post-Q1 (Q1 ran at projection): 0.8 + Q1*m + 2*(WX+probe)*m <= 16
m_q1 = (8 - OV) / q
m_c3 = (8 - OV) / c
m_full = (16 - OV) / (q + 2 * (w + p))
m_wx = (16 - OV) / (q + 2 * w)
print(f"reading A thresholds (x slowest): Q1 uncut up to {m_q1:.3f}; cut 3 up to {m_c3:.3f}; "
      f"probe kept up to {m_full:.3f}; WX kept up to {min(m_wx, m_q1):.3f} (limited by Q1 at {m_q1:.3f})")
m = 1.2
print(f"example m=1.2: post-Q1 total {OV + q*m + 2*(w+p)*m:.2f} h -> probe {'kept' if OV + q*m + 2*(w+p)*m <= 16 else 'cut'}")

# ---- Clopper-Pearson one-sided 95% lower bounds -----------------------------
def binom_sf(k, n, p):  # P(X >= k)
    return sum(math.comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))


def cp_lower(k, n, a=0.05):
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if binom_sf(k, n, mid) < a else (lo, mid)
    return lo


for k, n in [(10, 10), (9, 10), (9, 9), (8, 9), (8, 10), (3, 3), (16, 18), (12, 14), (18, 18), (17, 18), (14, 14), (13, 14)]:
    print(f"CP {k}/{n} = {cp_lower(k, n):.3f}")

# ---- P9-II measured wall seconds (informational, open point 13) -------------
rows = list(csv.DictReader(open(wt / "results/p9ii-run-2026-11-15/cells.csv")))
med = {}
for r in rows:
    med.setdefault((r["slots"], r["arm"]), []).append(float(r["wall_seconds"]))
med = {k: st.median(v) for k, v in med.items()}
rate = lambda slots, arm, upd: med[(slots, arm)] / upd
a2_16k = med[("16384", "A1")]  # A2 has no Stage 2 cell; A1 (L_addr throughout) as an upper stand-in
q1_p9ii = (20 * sum(med[("4096", a)] for a in arms_core) + 10 * (med[("4096", "A6")] + med[("4096", "A7")])
           + 20 * (med[("16384", "A0")] + med[("16384", "A1")] + a2_16k + med[("16384", "A5-D")])
           + 10 * (med[("16384", "A6")] + med[("16384", "A7")])
           + 10 * 4 * (med[("4096", "A0")] + med[("4096", "A5-D")] + med[("4096", "A6")]))
print(f"P9-II-rate Q1 (median wall s incl. evaluation): summed {q1_p9ii/3600:.2f} h, six workers {q1_p9ii/3600/6:.2f} h")
for (sl, arm, upd) in [("4096", "A5-D", U), ("4096", "A1", U), ("16384", "A5-D", 4 * U), ("16384", "A1", 4 * U), ("65536", "A0", U)]:
    print(f"  P9-II {arm}@{sl}: {rate(sl, arm, upd):.4f} s/update")
print(f"  probe at P9-II A0@65536 rate: one round {rate('65536','A0',U)*16*U/3600:.2f} h")
