# ruff: noqa: E501
"""M1 rev2, ruling R-4 (wording): every convention an answer depends on is stated in the item. Each test also shows the DEFECT on the batch-1 shape (the part that was red first)."""

from __future__ import annotations

import itertools
import math
import re

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_common import load_batch
from studies.m0.lineages_m1_rev2 import load_rev2

OLD = {x.id: x for x in load_batch()}
NEW = {x.id: x for x in load_rev2()}


def items(lin, per_level: int, tag: str):  # type: ignore[no-untyped-def]
    out = []
    for lv in ALL_LEVELS:
        rng = stream(953801, tag, lin.id, str(lv))
        out.extend(build_item(lin, lv, rng, "A", "t") for _ in range(per_level))
    return out


def test_slot_permutations_states_the_leading_zero_rule_and_the_key_follows_it() -> None:
    old_unstated = [it for it in items(OLD["M1.slot_permutations"], 60, "o") if 0 in it.structured["digits"] and "start with the digit 0" not in it.question]
    assert old_unstated, "batch 1 left the rule unstated for items containing the digit 0 (defect)"
    for it in items(NEW["M1.slot_permutations_r2"], 60, "n"):
        s = it.structured
        if 0 in s["digits"]:
            assert ("the first digit may not be 0" in it.question) == s["lead_nonzero"]
            assert ("the first digit may be 0" in it.question) != s["lead_nonzero"]
        assert f"the last digit must be {s['parity']}" in it.question
        if len(s["digits"]) ** s["length"] > 120_000:
            continue
        tuples = itertools.product(s["digits"], repeat=s["length"]) if s["repeat"] else itertools.permutations(s["digits"], s["length"])
        want = sum(1 for t in tuples if not (s["lead_nonzero"] and t[0] == 0) and (t[-1] % 2 == 0) == (s["parity"] == "even"))
        assert str(want) == it.answer  # independent brute force over the stated rules


def _literal_remainder(question: str) -> int:
    """Solve from the TEXT: every 'E factors (each) equal to B' is a product of E copies of B, multiplied out literally."""
    p = int(re.search(r"divided by (\d+)\?", question).group(1))  # type: ignore[union-attr]
    terms = [(int(e), int(b)) for e, b in re.findall(r"(\d+) factors,? (?:each )?equal to (\d+)", question)]
    vals = []
    for e, b in terms:
        v = 1
        for _ in range(e):
            v = v * b % p
        vals.append(v)
    if "Let X be the sum of" in question:
        return sum(vals) % p
    out = 1
    for v in vals:
        out = out * v % p
    return out


def test_power_remainder_wording_is_unambiguous_and_has_no_even_exponent_artefact() -> None:
    old = items(OLD["M1.last_digit_power"], 30, "o")
    assert all("multiplied by itself" in it.question for it in old), "batch 1 glossed the power as 'multiplied by itself E times' (E + 1 factors under the literal reading)"
    new = items(NEW["M1.power_remainder_r2"], 200, "n")
    for it in new:
        assert "multiplied by itself" not in it.question and "factors" in it.question
        assert _literal_remainder(it.question) == int(it.answer)
    # batch 1 forced an even exponent for every term whose base ends in 4 or 9; the revision has odd exponents for such bases
    old_terms = [(b, e) for it in items(OLD["M1.last_digit_power"], 200, "o2") for b, e in it.structured["terms"] if b % 10 in (4, 9)]
    new_terms = [(b, e) for it in new for b, e in it.structured["terms"] if b % 10 in (4, 9)]
    assert old_terms and all(e % 2 == 0 for _, e in old_terms)
    assert new_terms and any(e % 2 == 1 for _, e in new_terms) and any(e % 2 == 0 for _, e in new_terms)
    assert {it.structured["modulus"] for it in new} <= {17, 19, 23, 29}  # p - 1 is never a multiple of 5: the exponent's last digit says nothing


def _rev(n: int) -> int:
    return int(str(n)[::-1])  # a leading zero is dropped: 120 -> 021 -> 21 (what the revised item says)


def _holds(n: int, c: list) -> bool:  # type: ignore[type-arg]
    ds = [int(x) for x in str(n)]
    k = c[0]
    return {
        "digit_sum": lambda: sum(ds) == c[1],
        "digit_product": lambda: math.prod(ds) == c[1],
        "reverse_gap": lambda: _rev(n) - n == c[1],
        "multiple_of": lambda: n % c[1] == 0,
        "parity": lambda: (n % 2 == 0) == (c[1] == "even"),
        "first_gt_last": lambda: ds[0] > ds[-1],
        "digit_relation": lambda: ds[0] == c[1] * ds[-1],
        "contains_digit": lambda: c[1] in ds,
        "ends_differ_by": lambda: abs(ds[0] - ds[-1]) == c[1],
        "digits_distinct": lambda: len(set(ds)) == len(ds),
        "middle_is_mean": lambda: len(ds) == 3 and 2 * ds[1] == ds[0] + ds[2],
    }[k]()


def test_digit_puzzle_defines_the_reversal_and_the_key_is_unique_under_it() -> None:
    old = [it for it in items(OLD["M1.digit_puzzle"], 200, "o") if any(c[0] == "reverse_gap" for c in it.structured["clues"])]
    assert old and all("leading 0 is dropped" not in it.question for it in old)
    new = [it for it in items(NEW["M1.digit_puzzle_r2"], 200, "n")]
    with_rev = [it for it in new if any(c[0] == "reverse_gap" for c in it.structured["clues"])]
    assert with_rev and all("a leading 0 is dropped, so 120 turned round gives 21" in it.question for it in with_rev)
    for it in new[:400]:
        nd = it.structured["digits"]
        fits = [n for n in range(10 ** (nd - 1), 10**nd) if all(_holds(n, c) for c in it.structured["clues"])]
        assert fits == [int(it.answer)]


def test_every_revised_question_states_its_answer_format() -> None:
    for lid, lin in NEW.items():
        for it in items(lin, 5, "f"):
            assert "Answer with a" in it.question, lid
