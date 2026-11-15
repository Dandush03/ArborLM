"""C1 (auditor, Opus 5.5) -- pure arithmetic for ADR-0019 draft sections 5 and 8.4. No data, no model.

1. One-sided 95% Clopper-Pearson lower bounds for k successes of n (the draft quotes 0.74 / 0.83 for 15/16, 16/16).
2. Probability that an arm with per-cell success probability p is classed RELIABLE (>= 15 of 16) or at
   least UNRELIABLE (>= 4 of 16), (a) if the 16 cells are independent, (b) if the outcome is a property of the
   draw (both seeds of a draw agree; the auditor's P9-I diagnostics: "within a draw the outcome hardly
   depends on the init seed; between draws it does"), so that 8 draws are the effective sample.
3. The 'every evaluated draw has at least one success' clause: is it implied by 15/16 and 7/8?
4. Probability that the A1-S negative control is flagged FAILED (>= 4 of 16) purely because the answer-only
   baseline itself escapes on a share of draws (if A1-S is no better than A0).
"""
import itertools
import math


def binom_cdf_ge(k, n, p):
    return sum(math.comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))


def cp_lower(k, n, alpha=0.05):
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        # lower bound L: P(X >= k | p = L) = alpha
        if binom_cdf_ge(k, n, mid) < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


print("== 1. one-sided 95% Clopper-Pearson lower bounds")
for k, n in [(16, 16), (15, 16), (14, 16), (8, 8), (7, 8), (4, 4), (3, 4), (2, 2)]:
    print(f"  {k}/{n}: {cp_lower(k, n):.4f}")

print("\n== 2. P(class) for per-cell success probability p")
print("  p     | indep: P(>=15/16) P(>=4/16) | draw-clustered (8 draws, both seeds agree): P(>=15/16)=P(8/8)  P(>=4/16)=P(>=2/8)")
for p in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98):
    ind_rel = binom_cdf_ge(15, 16, p)
    ind_unrel = binom_cdf_ge(4, 16, p)
    cl_rel = binom_cdf_ge(8, 8, p)  # 15 of 16 with paired seeds means all 8 draws
    cl_unrel = binom_cdf_ge(2, 8, p)
    print(f"  {p:.2f}  |   {ind_rel:.3f}            {ind_unrel:.3f}     |   {cl_rel:.3f}                                {cl_unrel:.3f}")
print("  Stage 2 (4 draws x 2 seeds, >= 7 of 8):")
for p in (0.8, 0.9, 0.95):
    print(f"  {p:.2f}  indep P(>=7/8) {binom_cdf_ge(7, 8, p):.3f}   clustered P(4/4) {binom_cdf_ge(4, 4, p):.3f}")

print("\n== 3. Is 'every evaluated draw has at least one success' implied?")
for draws, need in ((8, 15), (4, 7)):
    n = 2 * draws
    implied = True
    for fails in itertools.combinations(range(n), n - need):
        # a draw has zero successes iff both of its cells failed
        failed = set(fails)
        if any({2 * d, 2 * d + 1} <= failed for d in range(draws)):
            implied = False
            break
    print(f"  {draws} draws x 2 seeds, >= {need} of {n}: implied = {implied}")

print("\n== 4. NEGATIVE CONTROL FAILED from the baseline's own escape rate (A1-S no better than A0)")
print("  share of draws on which answer-only training escapes within U -> P(A1-S >= 4/16), draw-clustered")
for q in (0.2, 0.3, 0.5, 0.6, 0.8):
    print(f"  {q:.1f} -> {binom_cdf_ge(2, 8, q):.3f}")
print("  (P9-I diagnostics: W7 at 4,096 escaped and reached 0.94-0.98 on 3 of 5 non-registered draws, 9 of 11 runs.)")
