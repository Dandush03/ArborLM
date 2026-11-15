"""C1 - addressing capacity of unit-norm keys under ADR-0017 rev 1 settings (toy, pure math).

Auditor check, written independently of any arborlm code. No model, no data, no training.

Setting (best case for the memory): F facts, each with a fixed query code on the unit sphere in d
dimensions (this is exactly rung R1 when the codes are i.i.d. uniform). One key per fact is placed
exactly on its query (keys = codes). Retrieval is top-8 by cosine; weights are softmax(cos / 0.2)
over the 8 selected. Extra slots (N = 2F) are assumed parked where they are never selected.

Reported per (d, F):
  * cosines of the 1st and 7th nearest other code (median over facts);
  * self weight w_self of the fact's own key (median, 5th percentile);
  * share of facts with w_self > 0.5 (row diagonal dominance of the read matrix W);
  * naive accuracy: answers i.i.d. uniform over 32 symbols, each key's value is the one-hot of its
    own fact's answer, output = sum_j w_j onehot(answer_j); correct if the own answer has the
    strictly largest total weight (ties count wrong). This is the accuracy without any value
    co-adaptation;
  * the smallest singular value of the F x F read matrix W (F <= 8192), which bounds how well a
    linear value solve can undo the mixing (values can co-adapt; W invertible => exact solve exists).
Also: Hamming-1 neighbour rates for 4-symbol identifiers over a 32-symbol alphabet.
"""

import json
import math
import sys

import torch

TEMP, TOP, SYMBOLS = 0.2, 8, 32


def codes(f: int, d: int, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(f, d, generator=g, dtype=torch.float64)
    return x / x.norm(dim=1, keepdim=True)


def read_matrix(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Top-8 cosines, indices and softmax weights for each query against keys = q."""
    f = q.shape[0]
    cos_all, idx_all = [], []
    for start in range(0, f, 2048):
        s = q[start : start + 2048] @ q.T
        c, i = s.topk(TOP, dim=1)
        cos_all.append(c)
        idx_all.append(i)
    cos, idx = torch.cat(cos_all), torch.cat(idx_all)
    w = (cos / TEMP).softmax(dim=1)
    return cos, idx, w


def naive_accuracy(idx: torch.Tensor, w: torch.Tensor, seed: int) -> float:
    f = idx.shape[0]
    g = torch.Generator().manual_seed(seed + 7)
    ans = torch.randint(0, SYMBOLS, (f,), generator=g)
    mass = torch.zeros(f, SYMBOLS, dtype=torch.float64)
    mass.scatter_add_(1, ans[idx], w)
    own = mass.gather(1, ans[:, None]).squeeze(1)
    mass.scatter_(1, ans[:, None], -1.0)
    return float((own > mass.max(dim=1).values).double().mean())


def smallest_singular(idx: torch.Tensor, w: torch.Tensor) -> float:
    f = idx.shape[0]
    dense = torch.zeros(f, f, dtype=torch.float64)
    dense.scatter_(1, idx, w)
    return float(torch.linalg.svdvals(dense).min())


def main() -> None:
    torch.set_num_threads(4)
    out = []
    for d in (16, 32):
        for f in (2048, 8192, 32768):
            q = codes(f, d, seed=1000 * d + f)
            cos, idx, w = read_matrix(q)
            assert bool((idx[:, 0] == torch.arange(f)).all()), "self must rank first"
            wself = w[:, 0]
            row = {
                "d": d,
                "facts": f,
                "median_cos_1st_other": round(float(cos[:, 1].median()), 4),
                "median_cos_7th_other": round(float(cos[:, 7].median()), 4),
                "median_w_self": round(float(wself.median()), 4),
                "p05_w_self": round(float(wself.quantile(0.05)), 4),
                "share_w_self_gt_0.5": round(float((wself > 0.5).double().mean()), 4),
                "naive_accuracy_no_coadaptation": round(naive_accuracy(idx, w, f), 4),
            }
            if f <= 8192:
                row["sigma_min_W"] = round(smallest_singular(idx, w), 5)
            out.append(row)
            print(json.dumps(row), flush=True)
    # Upper bound on w_self for ANY arrangement: the 7 competitors cannot all be far away once F >> d.
    # If all 7 had cos c, w_self = 1 / (1 + 7 exp(-(1 - c)/TEMP)).
    for c in (0.0, 0.3, 0.5, 0.7):
        print(json.dumps({"w_self_if_7_competitors_at_cos": c,
                          "w_self": round(1 / (1 + 7 * math.exp(-(1 - c) / TEMP)), 4)}))
    # Hamming-1 neighbours among F identifiers drawn without replacement from 32^4.
    space = SYMBOLS**4
    for f in (2048, 8192, 32768):
        p = (f - 1) / (space - 1)
        one_pos = 1 - (1 - p) ** (SYMBOLS - 1)
        any_pos = 1 - (1 - p) ** (4 * (SYMBOLS - 1))
        print(json.dumps({"facts": f, "density": round(f / space, 6),
                          "P(twin differing only at a given position)": round(one_pos, 4),
                          "P(at least one Hamming-1 twin)": round(any_pos, 4),
                          "expected Hamming-1 twins per fact": round(4 * (SYMBOLS - 1) * p, 3)}))
    for length in (5, 6):
        space = SYMBOLS**length
        p = 32767 / (space - 1)
        print(json.dumps({"identifier_length": length, "facts": 32768,
                          "P(at least one Hamming-1 twin)": round(1 - (1 - p) ** (length * 31), 4)}))
    print(json.dumps({"python": sys.version.split()[0], "torch": torch.__version__}))


if __name__ == "__main__":
    main()
