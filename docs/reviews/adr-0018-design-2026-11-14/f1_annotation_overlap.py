"""F1 - pure math: can ADR-0018's BEATS DENSE WINDOW (I_acc >= 1.10 x D7's) and DENSE WINDOW SUFFICES
(D7 accuracy >= 0.90 x the arm's) both hold for the same pair? And what does eta >= 0.90 mean in Fano
bits per fact? I_acc per fact = 5 - h2(e) - e log2 31 (ADR-0017 6.1), set to 0 at or below chance.

Usage: uv run --locked python docs/reviews/adr-0018-design-2026-11-14/f1_annotation_overlap.py
"""

import json
import math


def bits(acc):
    e = 1 - acc
    if acc <= 1 / 32:
        return 0.0
    h2 = 0.0 if e in (0, 1) else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5 - h2 - e * math.log2(31)


def main():
    both = []
    for ia in range(500, 1001, 5):
        a = ia / 1000
        for idd in range(0, ia + 1, 5):
            d = idd / 1000
            if d >= 0.9 * a and bits(d) > 0 and bits(a) >= 1.10 * bits(d):
                both.append((a, d))
    print(json.dumps({"pairs_with_both_annotations": len(both),
                      "examples": [{"arm": a, "d7": d, "acc_ratio": round(d / a, 3), "I_ratio": round(bits(a) / bits(d), 3)}
                                   for a, d in both[:: max(1, len(both) // 8)]]}))
    for a in (0.5, 0.6, 0.75, 0.9, 0.95, 1.0):
        print(json.dumps({"accuracy": a, "fano_bits_per_fact": round(bits(a), 3),
                          "accuracy_at_eta_0.90_if_R1_is_this": round(0.9 * a, 3),
                          "bits_at_that_accuracy": round(bits(0.9 * a), 3)}))


if __name__ == "__main__":
    main()
