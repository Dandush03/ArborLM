# ruff: noqa
"""Arithmetic for ADR-0033 addendum 1, draft 3. Formulas only; nothing is read. Standard library only.

Run:  uv run --locked python -I -B docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev3_arithmetic.py

Part A  capacity demand per LINEAGE and level if the pool builder stays as written (it gives every lineage of a part an
        equal quota): D_w(L) = 10 x (ceil(4,000/L) + ceil(20,000/L) + 100), L = registered lineages of the evaluation
        in the part. A cluster of k lineages then carries k of the L shares.
Part B  the demand of the per-cluster builder at very small G, including G = 1 and 2 (the fixed point of section 4A
        can reach them): D(G) and D_lin(G, k).
Part C  share of a pool held by a cluster of k lineages under the builder as written, against 1/G.
"""

import math

DEV, POOL, TUNING = 4_000, 20_000, 100


def d_w(l: int) -> int:
    return 10 * (math.ceil(DEV / l) + math.ceil(POOL / l) + TUNING)


def d(g: int) -> int:
    return 10 * (math.ceil(DEV / g) + math.ceil(POOL / g) + TUNING)


def d_lin(g: int, k: int) -> int:
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUNING / k))


print("== A. builder as written: demand per lineage and level, D_w(L)")
print("  " + "  ".join(f"L={l}: {d_w(l):,}" for l in (3, 5, 8, 10, 12, 15, 20, 25, 30)))
print("== B. per-cluster builder: D(G) per cluster and level; D_lin(G, k) per lineage")
print("  " + "  ".join(f"G={g}: {d(g):,}" for g in (1, 2, 3, 4, 5)))
for g in (1, 2, 3, 4):
    print(f"  G={g}: " + "  ".join(f"k={k}: {d_lin(g, k):,}" for k in (1, 2, 3)))
print("== C. builder as written: share of a pool held by a cluster of k lineages in a part of L lineages and G clusters")
for g, l, k in ((7, 10, 3), (10, 15, 4), (5, 9, 4)):
    print(f"  G={g}, L={l}, k={k}: share {k / l:.3f} against 1/G = {1 / g:.3f}")
