# ruff: noqa: E501
"""R2 batch 1, family codes: mechanical checks and test-local cross-checks (not the registered second solvers)."""

from __future__ import annotations

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 30):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953809, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("codes") == []


def test_luhn_known_vectors_and_items() -> None:
    from studies.m0.lineages_r2_codes import luhn_total

    assert luhn_total([int(c) for c in "79927398713"]) % 10 == 0  # the standard worked example
    assert luhn_total([int(c) for c in "79927398710"]) % 10 != 0
    for it in items("R2.luhn_check", 20):
        d = it.structured["digits"]
        if it.structured["ask"] == "valid":
            assert it.answer == ("yes" if luhn_total(d) % 10 == 0 else "no")
        else:
            assert luhn_total([*d, int(it.answer)]) % 10 == 0 and 0 <= int(it.answer) <= 9


def test_hamming_flipped_position_by_trying_every_flip() -> None:
    from studies.m0.lineages_r2_codes import hamming_syndrome

    for it in items("R2.hamming_error_position", 12):
        bits, n = it.structured["bits"], it.structured["n"]
        assert len(bits) == n and n in (15, 31, 63)
        fixes = [p for p in range(1, n + 1) if hamming_syndrome([b ^ (i + 1 == p) for i, b in enumerate(bits)]) == 0]
        if hamming_syndrome(bits) == 0:
            assert it.answer == "0"
        else:
            assert fixes == [int(it.answer)]  # exactly one flip repairs the word
