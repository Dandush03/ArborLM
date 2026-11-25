# ruff: noqa: E501
"""M1 batch 1, family algebra: mechanical checks of the new lineages (no independent solver exists yet; see studies/m0/manifests/m1_batch1_manifest.json)."""

from __future__ import annotations

from studies.m0.lineages_m1_common import check_family


def test_family_algebra_lineages_build_deterministic_in_grammar_and_state_their_format() -> None:
    assert check_family("algebra") == []
