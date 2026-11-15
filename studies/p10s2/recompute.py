# ruff: noqa: E501
"""The recomputation rule (ADR-0022 section 13.3).

No result is reported before the recomputation completes. The recomputation is complete when every registered score has been recomputed on CPU from the snapshots and compared with the registered
score. If it uses the frozen scoring code, every score must be bit-identical; if it uses the auditor's own code, every greedy sequence must be identical and every item score must agree within 1e-6 (both
cases stand; each score is judged under the case of the code that recomputed it). Every difference is listed. A cell with a difference beyond its tolerance is NOT_EVALUATED, and the recomputed CPU value is
the one reported (the stricter reading; section 11.2 then gives its mechanism the class NOT_EVALUATED). If a listed difference changes a gate, class, annotation or label (if any of them differs between the
registered scores and the recomputed ones), the study label is ENGINEERING-FAILURE. If the recomputation cannot be completed within the memory limits (8 GiB per worker, 24 GiB aggregate), the label is
INCOMPLETE and no class is printed.
"""

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core

FROZEN = "frozen-code"
OWN = "own-code"
MODES = (FROZEN, OWN)


def _num(x: Any) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, int | float):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Leaves of a nested record by path; lists are kept whole when they are lists of ints (greedy sequences), otherwise indexed."""
    out: dict[str, Any] = {}
    if isinstance(obj, Mapping):
        for k in sorted(obj, key=str):
            out.update(flatten(obj[k], f"{prefix}/{k}"))
    elif isinstance(obj, list | tuple):
        if obj and all(isinstance(v, int) and not isinstance(v, bool) for v in obj):
            out[prefix] = tuple(obj)
        else:
            for i, v in enumerate(obj):
                out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _same(a: Any, b: Any, tolerance: float, sequence_case: bool) -> bool:
    if isinstance(a, tuple) or isinstance(b, tuple):
        return bool(a == b)  # greedy sequences are identical under both cases
    fa, fb = _num(a), _num(b)
    if fa is not None and fb is not None:
        if math.isnan(fa) and math.isnan(fb):
            return True
        if math.isinf(fa) or math.isinf(fb):
            return fa == fb
        return fa == fb if tolerance == 0.0 else abs(fa - fb) <= tolerance
    return bool(a == b)


@dataclass
class Difference:
    cell: str
    path: str
    registered: Any
    recomputed: Any
    mode: str

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = core.jsonable({"cell": self.cell, "path": self.path, "registered": self.registered, "recomputed": self.recomputed, "mode": self.mode})
        return out


@dataclass
class RecomputeResult:
    complete: bool
    mode: str
    differences: list[Difference] = field(default_factory=list)
    not_evaluated_cells: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    memory_exceeded: bool = False

    def to_json(self) -> dict[str, Any]:
        return {"complete": self.complete, "mode": self.mode, "differences": [d.to_json() for d in self.differences], "not_evaluated_cells": self.not_evaluated_cells, "missing": self.missing, "memory_exceeded": self.memory_exceeded}


def tolerance_of(mode: str) -> float:
    r = core.CFG["recompute"]
    return float(r["frozen_code_tolerance"] if mode == FROZEN else r["own_code_item_tolerance"])


def compare_cells(registered: Mapping[str, Mapping[str, Any]], recomputed: Mapping[str, Mapping[str, Any]], mode: str, *, memory_exceeded: bool = False) -> RecomputeResult:
    """Compare every registered cell's scores with its recomputed record. A cell missing from the recomputation makes it incomplete. A difference beyond the case's tolerance lists the cell."""
    if mode not in MODES:
        raise ValueError(f"unknown recomputation mode {mode!r}")
    tol = tolerance_of(mode)
    diffs: list[Difference] = []
    missing = [lab for lab, rec in registered.items() if rec.get("status") == "completed" and lab not in recomputed]
    for lab, rec in registered.items():
        if lab not in recomputed or rec.get("status") != "completed":
            continue
        a = flatten({k: rec.get(k) for k in ("scores", "extras")})
        b = flatten({k: recomputed[lab].get(k) for k in ("scores", "extras")})
        for path in sorted(set(a) | set(b)):
            if path not in a or path not in b:
                diffs.append(Difference(lab, path, a.get(path, "<absent>"), b.get(path, "<absent>"), mode))
            elif not _same(a[path], b[path], tol, mode == OWN):
                diffs.append(Difference(lab, path, a[path], b[path], mode))
    ne = sorted({d.cell for d in diffs})
    return RecomputeResult(complete=not missing and not memory_exceeded, mode=mode, differences=diffs, not_evaluated_cells=ne, missing=missing, memory_exceeded=memory_exceeded)


def reported_cells(registered: Mapping[str, Mapping[str, Any]], recomputed: Mapping[str, Mapping[str, Any]], result: RecomputeResult) -> dict[str, dict[str, Any]]:
    """The cells as reported: for a cell with a difference beyond tolerance the recomputed CPU value replaces the registered one (the stricter reading)."""
    out = {k: copy.deepcopy(dict(v)) for k, v in registered.items()}
    for lab in result.not_evaluated_cells:
        out[lab] = {**out[lab], "scores": copy.deepcopy(recomputed[lab].get("scores")), "extras": copy.deepcopy(recomputed[lab].get("extras")), "recomputed_replaced": True}
    return out


def outcome_changes(registered_outcome: Mapping[str, Any], recomputed_outcome: Mapping[str, Any]) -> list[str]:
    """Gates, classes, annotations and label compared between the registered scores and the recomputed ones; the paths that differ."""
    keys = ("gates", "classes", "annotations", "label")
    changed: list[str] = []
    for k in keys:
        a, b = flatten(registered_outcome.get(k)), flatten(recomputed_outcome.get(k))
        for path in sorted(set(a) | set(b)):
            if a.get(path) != b.get(path):
                changed.append(f"{k}{path}")
    return changed


def recomputation_status(result: RecomputeResult | None, changed: Sequence[str]) -> dict[str, Any]:
    """What the label rule reads: incomplete (no recomputation, or not completed within the memory limits), engineering failure (a listed difference changes a gate, class, annotation or label), or
    cells to mark NOT_EVALUATED."""
    if result is None:
        return {"state": "not_run", "incomplete": True, "engineering_failure": False, "not_evaluated_cells": []}
    return {
        "state": "complete" if result.complete else ("memory" if result.memory_exceeded else "incomplete"),
        "incomplete": not result.complete,
        "engineering_failure": bool(changed) and result.complete,
        "not_evaluated_cells": list(result.not_evaluated_cells),
        "changes": list(changed),
    }
