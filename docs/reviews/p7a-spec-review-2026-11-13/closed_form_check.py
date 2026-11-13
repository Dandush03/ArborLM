"""Auditor check of the ADR-0013 section 5 uniform analytical reference (standard library only).

k distinct rows are drawn uniformly without replacement from a candidate set of N rows.
The candidate set has m_j rows on page j (sum m_j = N). Then

    E[distinct pages] = sum_j [1 - C(N - m_j, k) / C(N, k)]

and when every page holds R candidate rows on P pages (N = P*R):

    E[distinct pages] = P * [1 - C(N - R, k) / C(N, k)].

Checked here against Monte Carlo on synthetic draws. No model, checkpoint or trace is used.
Run: python3 -I closed_form_check.py
"""

import random
from fractions import Fraction
from math import comb


def expected_pages(rows_per_page: list[int], k: int) -> Fraction:
    n = sum(rows_per_page)
    return sum((1 - Fraction(comb(n - m, k), comb(n, k)) for m in rows_per_page), Fraction(0))


def monte_carlo(rows_per_page: list[int], k: int, trials: int, rng: random.Random) -> float:
    page_of = [j for j, m in enumerate(rows_per_page) for _ in range(m)]
    total = 0
    for _ in range(trials):
        total += len({page_of[i] for i in rng.sample(range(len(page_of)), k)})
    return total / trials


def main() -> None:
    rng = random.Random(20261113)
    k, trials = 8, 200_000
    cases = []
    # Actual geometry: value row 128 B -> 32/128/512 rows per 4/16/64 KiB page.
    # Hypothetical geometry: value row 2048 B -> 2/8/32 rows per page.
    for geometry, row_bytes in (("actual", 128), ("hypothetical", 2048)):
        for block_kib in (4, 16, 64):
            r = block_kib * 1024 // row_bytes
            # Whole store (flat, L-ID or any layout under the uniform model).
            store_pages = 4096 // r
            cases.append((geometry, block_kib, "flat: whole store, 4096 rows", [r] * store_pages))
            # Two visited branches, L-ID contiguous, 512 rows.
            if r <= 256:
                # Branch = 256/r whole pages; two distinct branches never share a page.
                cases.append((geometry, block_kib, "tree: two branches (no shared page)", [r] * (512 // r)))
            else:
                # r = 512: one page holds branches 2b and 2b+1.
                cases.append((geometry, block_kib, "tree: two branches in the SAME 64 KiB page", [512]))
                cases.append((geometry, block_kib, "tree: two branches in DIFFERENT 64 KiB pages", [256, 256]))
    # Mixed occupancy example: candidate rows not page-aligned (general formula needed).
    cases.append(("synthetic", 4, "general form: 300 used rows spread 30,30,...,20,10", [30] * 9 + [20, 10]))
    lines = ["geometry\tblock_KiB\tcase\tclosed_form\tmonte_carlo(200k)\tabs_diff"]
    for geometry, block_kib, name, rows in cases:
        exact = expected_pages(rows, k)
        mc = monte_carlo(rows, k, trials, rng)
        lines.append(f"{geometry}\t{block_kib}\t{name}\t{float(exact):.6f}\t{mc:.6f}\t{abs(float(exact) - mc):.6f}")
    # Ratio relevant to PQ's 0.80 threshold.
    tree4 = float(expected_pages([32] * 16, k))
    flat4 = float(expected_pages([32] * 128, k))
    lines.append(f"ratio tree/flat at 4 KiB actual (uniform): {tree4 / flat4:.6f}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
