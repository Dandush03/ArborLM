# ruff: noqa: E501
"""C1 batch 1, family minmax: mechanical checks (isolated runs twice, existing second solver, grammar)."""

from __future__ import annotations

from studies.m0.lineages_c1_common import check_family


def test_family_minmax_lineages_build_deterministic_and_agree_with_both_checkers() -> None:
    assert check_family("minmax") == []
