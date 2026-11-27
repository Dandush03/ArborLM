"""ADR-0033 addendum 1, draft 6: the numbers of the fresh shortcut run (section 4A, stage 1S).

Standard library only. Reads no file, no cluster map, no lineage, no run output; generates no item; runs no rule script.

Part A  the seed integers: derive_seed(400002, "fresh-shortcut", str(i)) for the seed indices, the dry-run base
        derive_seed(400002, "fresh-shortcut-dry-run"), and every per-unit, per-role integer derive_seed(base, unit, role).
        derive_seed is the derivation of section 4 (studies/m0/core.py, derive_seed): SHA-256 of the decimal seed and the
        labels joined by "|", first 8 bytes, big-endian.
Part B  the binomial standard error of a pooled rate at the bound (rate = chance + 0.15 and chance - 0.15), for the items
        per level of the plan and for 1 to 5 seeds, so that the count chosen (3) can be compared with its neighbours.
Part C  the two path patterns of the script listing, printed as the regular expressions the text gives.

Run: uv run --locked python -I -B addendum1_rev6_fresh_run.py > addendum1_rev6_fresh_run.out.txt
"""

from __future__ import annotations

import hashlib
import math
from fractions import Fraction

SEED = 400002
LABEL = "fresh-shortcut"
DRY_LABEL = "fresh-shortcut-dry-run"
N_SEEDS = 3
BOUND = Fraction(15, 100)

# unit -> (evaluation, items per level and seed, roles in the order of the unit's command line or of the literals replaced)
UNITS: dict[str, tuple[str, int, tuple[str, ...]]] = {
    "R1a": ("R1", 3000, ("aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat1_fit", "feat1_test", "feat2_fit", "feat2_test")),
    "R1b": ("R1", 3000, ("aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test")),
    "R1c": ("R1", 3000, ("fit", "test")),
    "R2a": ("R2", 4000, ("tag",)),
    "R2b": ("R2", 4000, ("tag",)),
    "M1a": ("M1", 4000, ("own", "a4", "a3")),
    "M1b": ("M1", 4000, ("seed",)),
    "M1c": ("M1", 4000, ("seed",)),
    "C1a": ("C1", 2000, ("seed",)),
    "C1b": ("C1", 2000, ("seed",)),
    "C1c": ("C1", 2000, ("seed",)),
}
DRY_ITEMS = 20


def derive_seed(seed: int, *labels: str) -> int:
    digest = hashlib.sha256("|".join([str(seed), *labels]).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def part_a() -> None:
    print("PART A. Seed integers")
    print("derivation: int.from_bytes(sha256('|'.join([str(seed), *labels])).digest()[:8], 'big')")
    bases: dict[str, int] = {}
    for i in range(1, N_SEEDS + 1):
        bases[str(i)] = derive_seed(SEED, LABEL, str(i))
        print(f"  base {i}: '{SEED}|{LABEL}|{i}' -> {bases[str(i)]}")
    dry = derive_seed(SEED, DRY_LABEL)
    print(f"  dry-run base: '{SEED}|{DRY_LABEL}' -> {dry}")
    assert dry not in bases.values()
    every: list[int] = [dry, *bases.values()]
    for name, base in [*bases.items(), ("dry", dry)]:
        print(f"  seed index {name} (base {base}):")
        for unit, (_ev, _n, roles) in UNITS.items():
            for role in roles:
                v = derive_seed(base, unit, role)
                every.append(v)
                print(f"    {unit:4s} {role:11s} '{base}|{unit}|{role}' -> {v}")
    assert len(set(every)) == len(every), "two derived integers coincide"
    print(f"  {len(every)} integers, all distinct; none equals {SEED} or the development label's integer {derive_seed(SEED, 'development')}")
    assert SEED not in every and derive_seed(SEED, "development") not in every
    # the labels withdrawn or used elsewhere in the addendum give other integers
    for other in ("capacity", "cheap-rule", "cluster-partition"):
        assert derive_seed(SEED, other) not in every
    print()


def se(p: Fraction, n: int) -> float:
    return math.sqrt(float(p * (1 - p)) / n)


def part_b() -> None:
    print("PART B. Binomial standard error of a pooled rate at the bound (one rule scored on every item of a lineage and level)")
    print("chance: 0 for an open answer, 1/k for k offered options. 'above': rate = chance + 0.15; 'below': rate = chance - 0.15 (none if negative)")
    chances = [("open", Fraction(0)), ("k=2", Fraction(1, 2)), ("k=3", Fraction(1, 3)), ("k=4", Fraction(1, 4)), ("k=5", Fraction(1, 5)), ("k=7", Fraction(1, 7))]
    for per_seed in (2000, 3000, 4000):
        evs = sorted({ev for ev, n, _ in UNITS.values() if n == per_seed})
        print(f"  items per level and seed: {per_seed}  ({', '.join(evs)})")
        for k in range(1, 6):
            n = k * per_seed
            cells = []
            for name, c in chances:
                up = se(c + BOUND, n)
                lo = c - BOUND
                cells.append(f"{name} {up:.4f}" + (f"/{se(lo, n):.4f}" if lo > 0 else "/-"))
            mark = "  <- plan" if k == N_SEEDS else ""
            print(f"    seeds {k}  n {n:6d}  worst case (rate 0.5) {se(Fraction(1, 2), n):.4f}   above/below: " + "  ".join(cells) + mark)
    print("  the figure is larger for a rule scored on part of the items (one shape, or the items where it applies): multiply by sqrt(n / items scored)")
    print(f"  dry run: {DRY_ITEMS} items per level, one seed; standard error at rate 0.15: {se(BOUND, DRY_ITEMS):.3f}; at rate 0.5: {se(Fraction(1, 2), DRY_ITEMS):.3f}")
    print()
    print("  rounding: a script that writes figures rounded to d decimals leaves an error of at most half a unit of the last decimal in each figure,")
    print("  and so in their item-weighted mean: 0.00005 at d = 4, 0.0005 at d = 3")
    print()


def part_c() -> None:
    print("PART C. The path patterns of the script listing (applied to the output of: git ls-tree -r --name-only b78e58b1)")
    print(r"  (a) ^studies/m0/(r1|r2|m1|c1)_fix4_(measure|battery|draw|a3_run)\.py$")
    print(r"  (b) ^docs/reviews/m0-lineage-decision-2026-11-25/final_(r1|r2|m1|c1)/[^/]*(rules|closed_forms|_draw|_a3_run|heur)[^/]*\.py$")
    print("  (c) by name: docs/reviews/m0-lineage-decision-2026-11-25/audit4_c1/s4_rules_v2.py, .../audit4_c1/s5_analyse_v2.py, .../audit3_c1/a3_shortcuts.py")
    print("  items per lineage and level over the run: " +", ".join(f"{u} {n * N_SEEDS}" for u, (_e, n, _r) in UNITS.items()))


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
