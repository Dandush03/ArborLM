# ruff: noqa: E501
"""P10IS5 (ADR-0028, engineering part): a device cost-model study of the human lead's internal SSD: what uncached reads cost as a function of request size and of the number of requests issued at once.

New code, beside ``studies/p10ir/``. Run from the repository root as ``uv run --locked python -m studies.p10is5.stages <command>``. Every threshold is in ``configs/p10is5_ssd.toml``.

The scientific part of the ADR (section 3.2) is NOT implemented: it is NOT EVALUABLE as capped, and only its registered label with its two reasons is printed. No label here is a result about ArborLM's memory, accuracy or the trained tree.
Self-checked implementation only: not independent review, not Astra validation, not human approval. Nothing is frozen and no registered run is approved.
"""
