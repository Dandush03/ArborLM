# ruff: noqa: E501
"""R2 batch 1, family strings: mechanical checks and a test-local brute-force cross-check (not the registered second solver)."""

from __future__ import annotations

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def test_family_checks() -> None:
    assert check_family_r2("strings") == []


def test_longest_palindromic_substring_by_all_substrings() -> None:
    for lv in ALL_LEVELS:
        r = stream(953812, "t", "lps", str(lv))
        for i in range(25):
            it = build_item(LIN["R2.longest_palindromic_substring"], lv, r, "A", f"t/{lv}/{i}")
            s = it.structured["s"]
            best = max(j - i2 for i2 in range(len(s)) for j in range(i2 + 1, len(s) + 1) if s[i2:j] == s[i2:j][::-1])
            assert it.answer == str(best)
