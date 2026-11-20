# ruff: noqa: E501
"""Independent recomputation from the stored per-item records (ADR-0025 section 8.6; audit R5; rulings 8 and 11).

The evaluate stage stores, for every registered score that has items, the per-item scores (chrF-norm per item), the exact-match flags and the greedy token sequences (``item_records.json``, keyed by the registry key
of the read) and snapshots the routers with their hashes. This module recomputes every reported figure that rests on items from those records ALONE, in plain Python (no model, no engine, no torch): the mean of the
stored per-item scores is the read, and the exact-match rate is the ``em:`` read. ``recompute_registry`` returns what the stored items reproduce; ``compare`` lists every registry key whose stored value differs.
Reads that rest on no item list (``gen:*`` and ``modification``, the learned-router diagnostics) are not reproduced here and are listed apart."""

import math
from collections.abc import Mapping, Sequence
from typing import Any

TOLERANCE = 1e-12  # the mean of floats summed in a fixed order: the stored items are the very numbers the mean was taken over


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs) if xs else float("nan")


def recompute_registry(items: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    """Registry key -> value, from the per-item records only. A record keyed ``arm|order|rep|s:E_A`` gives that key (mean of items) and ``arm|order|rep|em:E_A`` (mean of exact flags, 1.0 for true); every other record
    (``lr:``, ``dcon:``, ``sub:*``) gives its own key (mean of items)."""
    out: dict[str, float] = {}
    for k, rec in items.items():
        out[k] = _mean(rec["items"])
        if k.rsplit("|", 1)[1].startswith("s:") and "exact" in rec:
            out[k.rsplit("|", 1)[0] + "|em:" + k.rsplit("|", 1)[1][2:]] = _mean([1.0 if x else 0.0 for x in rec["exact"]])
    return out


def compare(registry: Mapping[str, float], items: Mapping[str, Mapping[str, Any]], tolerance: float = TOLERANCE) -> dict[str, Any]:
    """Every key the stored items reproduce, against the registry: the keys that differ, the keys the items reproduce that the registry lacks, and the registry keys no item record covers."""
    again = recompute_registry(items)
    differ = [{"key": k, "registry": registry[k], "from_items": v} for k, v in sorted(again.items()) if k in registry and abs(registry[k] - v) > tolerance]
    return {"checked": sum(1 for k in again if k in registry), "differ": differ, "not_in_registry": sorted(k for k in again if k not in registry), "not_covered_by_items": sorted(k for k in registry if k not in again)}


def compare_items(stored: Mapping[str, Mapping[str, Any]], again: Mapping[str, Mapping[str, Any]], tolerance: float = 0.0) -> list[dict[str, Any]]:
    """The stored per-item records against re-scored ones (the recomputation): any key present in both whose items, exact flags or greedy sequences differ."""
    out: list[dict[str, Any]] = []
    for k in sorted(set(stored) & set(again)):
        a, b = stored[k], again[k]
        bad = [f for f in ("items", "exact", "sequences", "texts") if f in a and f in b and (a[f] != b[f] if f != "items" else (len(a[f]) != len(b[f]) or any(abs(x - y) > tolerance for x, y in zip(a[f], b[f], strict=True))))]
        if bad:
            out.append({"key": k, "differs_in": bad, "why": "stored per-item record differs from the recomputation"})
    return out
