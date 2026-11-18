# ruff: noqa: E501
"""P10IR (ADR-0029): frozen-checkpoint routing diagnosis, Stage A (A1 re-analysis of P10-S1's observed cells, A2 confirmation on fresh bridge cells).

New code lives here, beside ``studies/p9/`` and ``studies/p10s1/``, and imports them without changing them. Run from the repository root as
``uv run --locked python -m studies.p10ir.<module>``. Every threshold is in ``configs/p10ir_routing.toml``.

Every label of this study is a diagnosis of read-time reads over memories trained under the registered read; none is a positive or a negative result for ArborLM.
Self-checked implementation only: not independent review, not Astra validation, not human approval.
"""
