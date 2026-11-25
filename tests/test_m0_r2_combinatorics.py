# ruff: noqa: E501
"""R2 batch 1, family combinatorics: mechanical checks and a test-local cross-check by listing (not the registered second solvers)."""

from __future__ import annotations

import itertools

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def test_family_checks() -> None:
    assert check_family_r2("combinatorics") == []


def test_dictionary_rank_by_listing_all_arrangements() -> None:
    for lv in ALL_LEVELS:
        r = stream(953810, "t", "dr", str(lv))
        for i in range(20):
            it = build_item(LIN["R2.dictionary_rank"], lv, r, "A", f"t/{lv}/{i}")
            s = it.structured
            words = ["".join(p) for p in itertools.permutations(s["letters"])]  # letters are sorted, so this is dictionary order
            assert words == sorted(words)
            if s["ask"] == "word":
                assert it.answer == words[s["k"] - 1]
            else:
                assert it.answer == str(words.index(s["word"]) + 1)
