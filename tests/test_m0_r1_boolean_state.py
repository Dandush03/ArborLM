# ruff: noqa: E501
"""R1 pilot, family boolean_state: mechanical checks of the new lineages (no independent solver exists yet; see studies/m0/NOTES_LINEAGE_REPAIR.md)."""

from __future__ import annotations

from studies.m0.lineage_gates import check_family


def test_family_boolean_state_lineages_build_in_grammar_deterministic_and_leak_free() -> None:
    assert check_family("boolean_state") == []
