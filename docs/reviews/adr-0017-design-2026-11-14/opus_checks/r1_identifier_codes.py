"""R1 (re-check of rev 2) - identifiers with a checksum symbol, template pool arithmetic.

Auditor toy, pure math / STYLIZED. No ArborLM code and no model is run.

Part 1 (exact counting on sampled fact sets): rev 2 section 4.1 identifiers = 4 uniform symbols plus
s5 = (s1+s2+s3+s4) mod 32. Share of facts with a neighbour at Hamming distance 1 and 2, and share whose
distance-2 neighbour agrees on s5 (the symbol adjacent to the binding byte, i.e. the two differences
sit in older positions). Compared with rev 1 (4 uniform symbols) and with 5 independent symbols.

Part 2 (stylized, as C1b): h = sum_k a_k M_k e(s_k) at the binding byte, recency weights
a_k proportional to r^(L-k) over the L identifier positions (same law for L = 4 and L = 5), keys at
the noise-free queries, query noise of relative size sigma. Reports own-key-first and naive accuracy.
The real attention profile of the frozen block is unknown; this only compares codes under one law.

Part 3: template pool arithmetic (rev 2 section 4.2).
"""

import itertools
import json

import torch

S = 32
TEMP, TOP, WIDTH, KEY = 0.2, 8, 32, 16


def draw(kind: str, f: int, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    if kind == "rev1_4sym":
        flat = torch.randperm(S**4, generator=g)[:f]
        return torch.stack([(flat // S**k) % S for k in (3, 2, 1, 0)], dim=1)
    if kind == "rev2_4+checksum":
        flat = torch.randperm(S**4, generator=g)[:f]
        ids = torch.stack([(flat // S**k) % S for k in (3, 2, 1, 0)], dim=1)
        return torch.cat([ids, ids.sum(1, keepdim=True) % S], dim=1)
    flat = torch.randperm(S**5, generator=g)[:f]
    return torch.stack([(flat // S**k) % S for k in (4, 3, 2, 1, 0)], dim=1)


def neighbour_shares(ids: torch.Tensor) -> dict[str, float]:
    rows = [tuple(int(x) for x in r) for r in ids]
    n, length = len(rows), len(rows[0])
    near: dict[int, set[int]] = {1: set(), 2: set()}
    d2_same_last: set[int] = set()
    for keep in itertools.combinations(range(length), length - 2):
        groups: dict[tuple[int, ...], list[int]] = {}
        for i, r in enumerate(rows):
            groups.setdefault(tuple(r[k] for k in keep), []).append(i)
        for members in groups.values():
            if len(members) < 2:
                continue
            for i, j in itertools.combinations(members, 2):
                d = sum(a != b for a, b in zip(rows[i], rows[j]))
                if d in near:
                    near[d].update((i, j))
                if d == 2 and rows[i][-1] == rows[j][-1]:
                    d2_same_last.update((i, j))
    return {"share_with_distance1_neighbour": round(len(near[1]) / n, 4),
            "share_with_distance2_neighbour": round(len(near[2]) / n, 4),
            "share_with_distance2_neighbour_same_last_symbol": round(len(d2_same_last) / n, 4)}


def stylized(ids: torch.Tensor, r: float, sigma: float, seed: int) -> dict[str, float]:
    g = torch.Generator().manual_seed(seed)
    f, length = ids.shape
    emb = torch.randn(S, WIDTH, generator=g, dtype=torch.float64) / WIDTH**0.5
    mix = [torch.linalg.qr(torch.randn(WIDTH, WIDTH, generator=g, dtype=torch.float64))[0] for _ in range(length)]
    proj = torch.randn(KEY, WIDTH, generator=g, dtype=torch.float64)
    a = torch.tensor([r ** (length - 1 - k) for k in range(length)], dtype=torch.float64)
    a = a / a.sum()
    h = sum(a[k] * emb[ids[:, k]] @ mix[k].T for k in range(length))
    noise = torch.randn(f, WIDTH, generator=g, dtype=torch.float64)
    noise = noise / noise.norm(dim=1, keepdim=True) * h.norm(dim=1, keepdim=True) * sigma
    keys = torch.nn.functional.normalize(h @ proj.T, dim=1)
    q = torch.nn.functional.normalize((h + noise) @ proj.T, dim=1)
    ans = torch.randint(0, S, (f,), generator=g)
    first = correct = 0
    for s in range(0, f, 2048):
        sc = q[s : s + 2048] @ keys.T
        c, i = sc.topk(TOP, dim=1)
        w = (c / TEMP).softmax(dim=1)
        rows = torch.arange(s, min(s + 2048, f))
        first += int((i[:, 0] == rows).sum())
        mass = torch.zeros(len(rows), S, dtype=torch.float64).scatter_add_(1, ans[i], w)
        own = mass.gather(1, ans[rows][:, None]).squeeze(1)
        mass.scatter_(1, ans[rows][:, None], -1.0)
        correct += int((own > mass.max(1).values).sum())
    return {"own_key_ranked_first": round(first / f, 4), "naive_accuracy": round(correct / f, 4)}


def main() -> None:
    torch.set_num_threads(4)
    kinds = ("rev1_4sym", "rev2_4+checksum", "5_independent")
    for f in (2048, 8192, 32768):
        for kind in kinds:
            ids = draw(kind, f, seed=f + 7)
            if kind == "rev2_4+checksum":
                assert bool(((ids[:, :4].sum(1) % S) == ids[:, 4]).all())
            print(json.dumps({"part": 1, "facts": f, "code": kind, **neighbour_shares(ids)}), flush=True)
    # analytic expected neighbour counts (density approximation)
    for f in (2048, 8192, 32768):
        print(json.dumps({"part": "1-analytic", "facts": f,
                          "checksum_expected_distance2_neighbours": round(10 * 31 * f / S**4, 3),
                          "of_which_same_checksum_share": round(6 * 31 / (10 * 31), 3),
                          "independent5_expected_distance1": round(5 * 31 * f / S**5, 3),
                          "independent5_expected_distance2": round(10 * 31**2 * f / S**5, 3)}))
    for f in (2048, 32768):
        for kind in kinds:
            ids = draw(kind, f, seed=f + 7)
            for r in (1.0, 0.6, 0.35):
                for sigma in (0.0, 0.1, 0.3):
                    out = stylized(ids, r, sigma, seed=1000 + f)
                    print(json.dumps({"part": 2, "facts": f, "code": kind, "recency_ratio_r": r,
                                      "context_noise": sigma, **out}), flush=True)
    pool, t_pairs, h_pairs = 48, 16, 8
    need_disjoint = 2 * (t_pairs + h_pairs + h_pairs)
    print(json.dumps({"part": 3, "pool_bytes": pool, "pairs_T_H1_H2": [t_pairs, h_pairs, h_pairs],
                      "bytes_needed_if_all_pairs_byte_disjoint": need_disjoint,
                      "well_defined_as_disjoint_pairs": need_disjoint <= pool,
                      "ordered_pairs_available_if_bytes_reused": pool * (pool - 1),
                      "example_disjoint_split": "T: 16 sep + 16 bind bytes (32); H1: 4 sep x 4 bind bytes, 8 of 16 combos;"
                                                " H2: same with the other 8 bytes; total 48, no byte in two panels"}))


if __name__ == "__main__":
    main()
