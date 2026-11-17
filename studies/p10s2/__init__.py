# ruff: noqa: E501
"""P10-S2 (ADR-0022, revision 5): two-teacher sequential transfer into an expandable learned memory on a frozen student.

Implementation on synthetic stand-ins only (ADR-0022 section 18). New code lives here, beside ``studies/p9*``, and changes nothing outside it.
Run from the repository root as ``uv run --locked python -m studies.p10s2.<module>``. Self-check only: not independent review, not Astra validation,
not human approval.
"""
