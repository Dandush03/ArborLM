"""R2 (re-check of rev 2) - the Fano quantity of section 6.1 and edge cases of the section 8.2 rules.

Pure math, no model. I_acc per fact = 5 - h2(e) - e*log2(31), e = 1 - accuracy (rev 2 section 6.1).
1. curve, curvature at chance, behaviour below chance;
2. the G2 interval (exact binomial, central, level 1 - 0.001/16) at the panel sizes;
3. near-chance cells that satisfy 'step supported' (ratio >= 3 and accuracy above the G2 interval);
4. plateau rule 'gain from U/2 to U below 5% of I(U)' for power-law and at-chance curves.
"""

import json
import math


def h2(p: float) -> float:
    return 0.0 if p in (0.0, 1.0) else -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def fano(acc: float) -> float:
    e = 1 - acc
    return 5 - h2(e) - e * math.log2(31)


def binom_cdf(k: int, n: int, p: float) -> float:
    # log-space sum, exact enough for these n
    total, logp, logq = 0.0, math.log(p), math.log(1 - p)
    for i in range(0, k + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * logp + (n - i) * logq)
    return total


def central_interval(n: int, alpha: float, p: float = 1 / 32) -> tuple[int, int]:
    lo = 0
    while binom_cdf(lo, n, p) < alpha / 2:
        lo += 1
    hi = n
    # smallest hi with P(X > hi) <= alpha/2
    mean = int(n * p)
    hi = mean
    while 1 - binom_cdf(hi, n, p) > alpha / 2:
        hi += 1
    return lo, hi


def main() -> None:
    for acc in (0.0, 0.01, 0.02, 0.03, 1 / 32, 0.035, 0.04, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 0.9, 0.95, 1.0):
        print(json.dumps({"part": 1, "accuracy": round(acc, 5), "fano_bits_per_fact": round(fano(acc), 5)}))
    curv = (1 / math.log(2)) * (32 + 32 / 31) / 2
    print(json.dumps({"part": 1, "small_delta_approx": f"I ~ {curv:.2f} * (acc - 1/32)^2 bits per fact",
                      "below_chance_positive": fano(0.0) > 0, "fano_at_acc_0": round(fano(0.0), 4),
                      "note": "the formula is not monotone in accuracy below chance"}))
    for target in (0.25, 0.5, 1.0, 2.0):
        lo, hi = 1 / 32, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if fano(mid) < target else (lo, mid)
        print(json.dumps({"part": 1, "fano_bits_per_fact": target, "accuracy_needed": round(hi, 4)}))
    alpha = 0.001 / 16
    g2 = {}
    for n in (2048, 8192, 32768):
        lo, hi = central_interval(n, alpha)
        g2[n] = hi / n
        print(json.dumps({"part": 2, "facts": n, "alpha": alpha, "accept_count": [lo, hi],
                          "upper_accuracy": round(hi / n, 5)}))
    # 3. near-chance 'supported' steps
    for (n_small, f_small, f_large, a_small, a_large) in (
        ("4K->16K", 2048, 8192, 0.035, 0.040),
        ("4K->16K", 2048, 8192, 0.033, 0.042),
        ("16K->64K", 8192, 32768, 0.036, 0.0360),
        ("16K->64K", 8192, 32768, 0.034, 0.0358),
    ):
        i_s, i_l = f_small * fano(a_small), f_large * fano(a_large)
        print(json.dumps({"part": 3, "step": n_small, "acc_small": a_small, "acc_large": a_large,
                          "I_small_bits": round(i_s, 3), "I_large_bits": round(i_l, 3),
                          "ratio": round(i_l / i_s, 2) if i_s > 0 else None,
                          "large_above_G2_upper": a_large > g2[f_large],
                          "step_supported_by_rev2_rule": (i_s > 0 and i_l / i_s >= 3.0 and a_large > g2[f_large])}))
    # zero denominator: smaller cell exactly at chance or below
    print(json.dumps({"part": 3, "case": "acc_small = 1/32 exactly", "I_small": fano(1 / 32),
                      "ratio": "x/0 undefined in rev 2"}))
    print(json.dumps({"part": 3, "case": "acc_small = 0.028 (below chance, inside G2)", "I_small_bits_per_fact": round(fano(0.028), 6),
                      "comment": "positive bits from a below-chance noise draw"}))
    # 4. plateau rule
    for a in (0.05, 0.074, 0.1, 0.2, 0.3, 0.5):
        print(json.dumps({"part": 4, "curve": f"I ~ t^{a}", "gain_share_from_half_to_full": round(1 - 2 ** (-a), 4),
                          "plateaued_by_rev2_rule": 1 - 2 ** (-a) < 0.05}))
    print(json.dumps({"part": 4, "curve": "I(U/2) = I(U) = 0 (at chance)", "gain": 0, "threshold": 0,
                      "plateaued_by_rev2_rule('gain < 5% of I(U)')": 0 < 0,
                      "consequence": "never plateaued -> UNDERTRAINED, not NOT_SUPPORTED"}))


if __name__ == "__main__":
    main()
