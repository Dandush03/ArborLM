"""C5 - gate statistics in ADR-0017 rev 1 (pure math, exact binomial in log space).

G2 (section 8.1): no-memory and unseen-fact accuracy must lie in 'the exact binomial 99.9% interval
around 1/32'. Because answers are i.i.d. uniform and independent of everything the model sees, the
accuracy of ANY predictor on those sets is exactly Binomial(n, 1/32) (no leakage). So each G2 test is
a false-failure lottery with probability about 0.001; we compute the exact acceptance region
(central interval, each tail <= 0.0005) and the family-wise false-failure probability for plausible
test counts. Also: expected cell counts for the generator chi-square tests (section 4.5 item 2).
"""

import json
import math


def log_pmf(n: int, k: int, p: float) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def central_region(n: int, p: float, alpha: float = 0.001) -> tuple[int, int, float]:
    pmf = [math.exp(log_pmf(n, k, p)) for k in range(n + 1)]
    lo, acc = 0, 0.0
    while acc + pmf[lo] <= alpha / 2:
        acc += pmf[lo]
        lo += 1
    hi, acc_hi = n, 0.0
    while acc_hi + pmf[hi] <= alpha / 2:
        acc_hi += pmf[hi]
        hi -= 1
    return lo, hi, acc + acc_hi


def main() -> None:
    p = 1 / 32
    per_test = {}
    for n in (2048, 4096, 8192, 32768):
        lo, hi, false_fail = central_region(n, p)
        per_test[n] = false_fail
        print(json.dumps({"n_queries": n, "accept_correct_count_in": [lo, hi],
                          "accept_accuracy_in": [round(lo / n, 4), round(hi / n, 4)],
                          "exact_false_failure_probability": round(false_fail, 6)}))
    f = per_test[2048]
    # Rev 1 does not say on which cells G2 is evaluated. Two readings:
    for label, tests in (("per size and track, controls only: 4 tracks x 2 panels x 2 sets", 16),
                         ("every trained cell x 2 panels, unseen set only (108 cells)", 216),
                         ("every trained cell x 2 panels x {unseen, permuted, disabled}", 648)):
        print(json.dumps({"reading": label, "tests": tests,
                          "P(at least one false G2 failure)": round(1 - (1 - f) ** tests, 4)}))
    # Generator chi-square (answer vs identifier position): 32 x 32 table.
    for facts in (2048, 4096, 8192, 32768):
        print(json.dumps({"facts": facts, "answer_x_identifier_symbol_table": "32 x 32",
                          "expected_count_per_cell": round(facts / 1024, 2),
                          "chi_square_rule_of_thumb_(>=5)_met": facts / 1024 >= 5}))
    # Cluster test: 16 facts per cluster, answer x cluster table.
    for facts in (2048, 8192, 32768):
        print(json.dumps({"facts": facts, "answer_x_cluster_table": f"32 x {facts // 16}",
                          "expected_count_per_cell": round(16 / 32, 2)}))


if __name__ == "__main__":
    main()
