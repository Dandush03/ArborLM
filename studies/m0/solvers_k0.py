"""Independent second solver for K0: the fact table gives the letter of the stated value."""

from __future__ import annotations

from typing import Any


def invented_fact(s: dict[str, Any]) -> str:
    value = s["options"][s["fact_index"]]
    return "ABCD"[list(s["options"]).index(value)]


SOLVERS = {"K0.invented_fact": invented_fact}
