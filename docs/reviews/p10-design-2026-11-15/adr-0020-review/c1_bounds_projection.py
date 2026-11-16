"""ADR-0020 review: one-sided Clopper-Pearson bounds, cell counts, projections, budgets, seed layout.

Independent arithmetic; no project code imported. Usage: python3 -I c1_bounds_projection.py
"""

from math import comb


def cp_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided (1 - alpha) Clopper-Pearson lower bound for k successes of n, by bisection on
    P(X >= k | p) = alpha."""
    if k == 0:
        return 0.0

    def tail(p: float) -> float:
        return sum(comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if tail(mid) < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


print("== per-draw one-sided 95% lower bounds")
for k, n, claim in [(6, 6, 0.61), (5, 6, 0.42), (4, 4, 0.47), (3, 3, 0.37), (10, 10, 0.74),
                    (14, 14, 0.81), (8, 8, 0.69), (7, 8, 0.53), (5, 5, None), (4, 5, None),
                    (2, 3, None), (9, 9, None), (13, 14, None), (9, 10, None), (15, 15, None)]:
    b = cp_lower(k, n)
    print(f"  {k:>2}/{n:<2} -> {b:.4f}  (draft {claim})" if claim else f"  {k:>2}/{n:<2} -> {b:.4f}")

print("\n== what RELIABLE guarantees at 2K/4K (12 cells, 6 draws x 2 seeds, at most one failed cell)")
print(f"  worst case: one draw with 1 of 2 failed -> 5 of 6 draws with both cells -> {cp_lower(5, 6):.4f}")
print(f"  if a draw counts as a success when at least one cell succeeds: 6 of 6 -> {cp_lower(6, 6):.4f}")

print("\n== cell counts (ADR-0020 §6.1)")
def q1(x2: bool, c_is_a0: bool, small: bool) -> int:
    learned_2k = (1 if c_is_a0 else 2) + 1 + (1 if x2 else 0)   # A0 (+C) + WX + X2
    learned_8k4k = (1 if c_is_a0 else 2) + (1 if x2 else 0)     # A0 (+C) + X2 (no WX)
    learned_8k16k = learned_2k
    n = learned_2k * 12 + 12 + learned_8k4k * 6 + 12
    if not small:
        n += learned_8k16k * 6 + 12
    return n
for x2 in (True, False):
    for a0 in (False, True):
        for small in (False, True):
            print(f"  X2={x2!s:5} C=A0={a0!s:5} SMALL={small!s:5} -> {q1(x2, a0, small)}")
print("  draft: 126 / 102 (no X2) / 102 / 78 (C=A0) / 90 / 72 (SMALL)")

print("\n== Q1 projection (summed CPU-hours; makespan = /6, perfect packing)")
rates = {"fastest (0.008/0.013)": (0.008, 0.013),
         "W7 registered (0.0098/0.0141)": (0.0098, 0.0141),
         "slowest (0.0112/0.0195)": (0.0112, 0.0195)}
for name, (r4, r16) in rates.items():
    s126 = 60 * 8192 * r4 + 30 * 32768 * r4 + 36 * 32768 * r16
    s102 = 48 * 8192 * r4 + 24 * 32768 * r4 + 30 * 32768 * r16
    print(f"  {name:32} 126 cells {s126/3600:5.2f} h, makespan {s126/3600/6:4.2f} h | 102 cells {s102/3600:5.2f} h, {s102/3600/6:4.2f} h")

print("\n== Q2 projection: 131,072 updates per cell at 65,536 slots")
for r in (0.035, 0.0531, 0.053, 0.0619):
    per = 131072 * r / 3600
    print(f"  rate {r:.4f} s -> {per:.3f} h per cell; 12 cells summed {12*per:5.2f} h; 2 rounds {2*per:4.2f} h;"
          f" 6 cells 1 round {per:4.2f} h")
print("  draft: 1.27 / 1.93 / 2.25 h per cell; 15.3 / 23.2 / 27.0; 2.5 / 3.9 / 4.5; cut 1 1.3 / 1.9 / 2.3")

print("\n== Q3 projection: 16 x 16,384 + 8 x 32,768 updates at 16,384 slots")
for r in (0.013, 0.0141, 0.0195):
    s = 16 * 16384 * r + 8 * 32768 * r
    # critical path: phase 1 (16,384) then SEQ-R (32,768) = 49,152 updates sequential per draw-arm
    crit = 49152 * r
    print(f"  rate {r}: summed {s/3600:4.2f} h; /6 {s/3600/6:4.2f} h; sequential critical path per (draw, arm) {crit/3600:4.2f} h")
print("  draft: 1.9 / 2.0 / 2.8 summed; 0.3 / 0.3 / 0.5 makespan")

print("\n== Budget B at the slowest rates: 2 x (Q3 + Q2)")
for r16, r64 in ((0.0141, 0.0531), (0.0195, 0.0619)):
    q3 = max((16 * 16384 + 8 * 32768) * r16 / 6, 49152 * r16) / 3600
    q2 = 2 * 131072 * r64 / 3600
    print(f"  rates {r16}/{r64}: Q3 makespan (max of /6 and critical path) {q3:4.2f} h; Q2 {q2:4.2f} h; 2x sum {2*(q3+q2):5.2f} h vs 10 h")

print("\n== A4 soft read over k slots at 65,536 if implemented by gather (values width 32, float32)")
for k in (65536, 8192, 8):
    b = 128 * k * 32 * 4
    print(f"  k={k:>6}: gathered value tensor [128, k, 32] = {b/2**30:.3f} GiB (forward only; autograd keeps it)")

print("\n== seed layout (ADR-0020 §7)")
bases = [200001 + 100 * (d - 1) for d in range(1, 14)] + [201301, 201401]
offs = list(range(0, 40)) + [40, 41, 50, 51, 70, 71]
used = sorted({b + o for b in bases for o in offs})
print(f"  registered+reserve: {len(bases)} sets, bases {bases[0]}..{bases[-1]}; used {used[0]}..{used[-1]}; within 200001-201499: {used[-1] <= 201499}")
print("  P9-II rev4 maximum: base 191501 + 60 + 1 =", 191501 + 61, "(A1-S stream seed, reserve 2, j=1) -> ADR-0021's 190001-190733 is wrong")
print("  P9-I test_seeds(offset) = 900001 + 100*offset (studies/p9i/core.py:351): offset 200 would reach", 900001 + 100 * 200)
print("  'P9-II tests 910001 upward' with the same convention reaches 920001 at offset", (920001 - 910001) // 100)
