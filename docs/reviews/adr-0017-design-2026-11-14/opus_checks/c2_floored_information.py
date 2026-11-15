"""C2 - is rev 1's retained information I = sum_f max(0, 5 + log2 p_f) a valid lower bound? (pure math)

Zero-knowledge predictors: their distribution over the 32 answer symbols is independent of the true
answer (answers i.i.d. uniform). For such a predictor every honest information measure is 0 in
expectation. We compute, per fact, the expectation of
  * floored  : max(0, 5 + log2 p_true)              (rev 1 section 6.1, primary)
  * unfloored: 5 + log2 p_true                       (rev 1, reported beside)
  * Fano     : 5 - h2(e) - e log2 31, e = 1 - accuracy  (lower bound on I(answer; argmax prediction)
                                                       for a uniform 32-ary answer; computed per panel)
and the step ratio I(4F) / I(F) that rev 1 section 8.2 tests against 3.0.
Predictors: logits = sigma * Gaussian noise over the 32 symbols (sigma = 0 is exact chance), and a
'confident random guess' predictor putting mass q on one random symbol.
"""

import json
import math

import torch

SYMBOLS = 32


def h2(x: float) -> float:
    return 0.0 if x <= 0 or x >= 1 else -(x * math.log2(x) + (1 - x) * math.log2(1 - x))


def fano_bits(acc: float) -> float:
    e = 1 - acc
    return max(0.0, 5 - h2(e) - e * math.log2(SYMBOLS - 1))


def zero_knowledge(sigma: float, facts: int, seed: int) -> dict[str, float]:
    g = torch.Generator().manual_seed(seed)
    logits = sigma * torch.randn(facts, SYMBOLS, generator=g, dtype=torch.float64)
    p = logits.softmax(1)
    truth = torch.randint(0, SYMBOLS, (facts,), generator=g)
    pt = p.gather(1, truth[:, None]).squeeze(1)
    bits = 5 + torch.log2(pt)
    acc = float((p.argmax(1) == truth).double().mean())
    return {"floored_bits_per_fact": float(bits.clamp_min(0).mean()),
            "unfloored_bits_per_fact": float(bits.mean()), "accuracy": acc,
            "fano_bits_per_fact": fano_bits(acc)}


def main() -> None:
    for sigma in (0.0, 0.1, 0.3, 1.0, 3.0):
        rows = {f: zero_knowledge(sigma, f, seed=int(sigma * 100) + f) for f in (2048, 8192, 32768)}
        i = {f: r["floored_bits_per_fact"] * f for f, r in rows.items()}
        print(json.dumps({"predictor": f"zero-knowledge, logit noise sd {sigma}",
                          "per_fact_32768": {k: round(v, 4) for k, v in rows[32768].items()},
                          "floored_I_bits": {f: round(v, 1) for f, v in i.items()},
                          "step_ratio_4K_to_16K": round(i[8192] / i[2048], 3) if i[2048] else None,
                          "step_ratio_16K_to_64K": round(i[32768] / i[8192], 3) if i[8192] else None}))
    for q in (0.2, 0.5, 0.9):
        rest = (1 - q) / (SYMBOLS - 1)
        floored = (1 / SYMBOLS) * max(0, 5 + math.log2(q)) + (31 / SYMBOLS) * max(0, 5 + math.log2(rest))
        unfloored = (1 / SYMBOLS) * (5 + math.log2(q)) + (31 / SYMBOLS) * (5 + math.log2(rest))
        print(json.dumps({"predictor": f"confident random guess, mass {q} on one random symbol",
                          "floored_bits_per_fact": round(floored, 4),
                          "unfloored_bits_per_fact": round(unfloored, 4),
                          "expected_accuracy": round(1 / SYMBOLS, 4),
                          "floored_I_at_4K_16K_64K": [round(floored * f, 1) for f in (2048, 8192, 32768)]}))
    # Fano bound at a few accuracies, bits per fact
    print(json.dumps({"fano_bits_per_fact_at_accuracy": {a: round(fano_bits(a), 4)
                                                         for a in (1 / 32, 0.05, 0.1, 0.25, 0.5, 0.9, 0.95, 1.0)}}))
    # The upper limit 5F is not reachable when probabilities are bounded: p_true = 0.5 gives 4 bits.
    print(json.dumps({"bits_per_fact_at_p_true": {p: round(5 + math.log2(p), 3) for p in (0.1, 0.25, 0.5, 0.9)}}))


if __name__ == "__main__":
    main()
