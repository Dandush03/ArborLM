# ruff: noqa: E501
"""R2 batch 1, family numtheory: mechanical checks and test-local cross-checks (not the registered second solvers)."""

from __future__ import annotations

import math

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953802, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("numtheory") == []


def test_gcd_lcm_steps() -> None:
    for it in items("R2.gcd_euclid"):
        a, b, ask = it.structured["a"], it.structured["b"], it.structured["ask"]
        if ask == "gcd":
            assert it.answer == str(math.gcd(a, b))
        elif ask == "lcm":
            assert it.answer == str(math.lcm(a, b))
        else:
            n = 0
            while b:
                a, b = b, a % b
                n += 1
            assert it.answer == str(n)
    # known: (48, 18) -> (18, 12) -> (12, 6) -> (6, 0): 3 steps
    from studies.m0.lineages_r2_numtheory import euclid_steps

    assert euclid_steps(48, 18) == 3


def test_modular_power_against_loop() -> None:
    for it in items("R2.modular_power", 15):
        a, e, m = it.structured["a"], it.structured["e"], it.structured["m"]
        v = 1
        for _ in range(e):
            v = v * a % m
        assert it.answer == str(v)


def test_crt_smallest_by_search() -> None:
    for it in items("R2.crt_smallest", 15):
        cons = it.structured["congruences"]
        x = next(x for x in range(1, 10**7) if all(x % m == r for r, m in cons))
        assert it.answer == str(x)


def test_prime_factor_query_by_trial_division() -> None:
    for it in items("R2.prime_factor_query", 20):
        n, fs, d = it.structured["n"], [], 2
        while n > 1:
            while n % d == 0:
                fs.append(d)
                n //= d
            d += 1
        assert it.answer == (str(max(fs)) if it.structured["ask"] == "largest" else str(sum(fs)))
        assert max(fs) > 13
