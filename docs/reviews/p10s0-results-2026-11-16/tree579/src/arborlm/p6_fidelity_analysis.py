"""P6-Q registered descriptive flags and paired summaries (ADR-0011 section 4.4).

Reads only the compact per-checkpoint records written by ``p6_fidelity_study``. All means are
exact rational means of the recorded floating-point values and are compared with the registered
thresholds exactly (a value equal to a threshold passes a ">=" or "<=" clause). The flags are
descriptive conventions, not significance tests; the 27 cells share nine parents, three seeds
and one panel.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

from .p2_config import BACKBONES, ORDERS
from .p5_config import FIXED, LEARNED, SEEDS

KINDS = (FIXED, LEARNED)
FID_LEVEL = 0.95
LOSS_MARGIN = -0.005
PRIOR_MARGIN = 0.005
MIN_CELLS = 22
MIN_PARENTS = 8
MAX_LIST = 32
EXCLUDED = (
    "cell",
    "step",
    "integrity",
    "gates",
    "arrays",
    "resources",
    "checkpoint",
    "panel",
    "phase_seconds",
)

CellKey = tuple[int, int, int]
ParentKey = tuple[int, int]


def expected_cells() -> list[CellKey]:
    return [(b, o, s) for b, o, s in itertools.product(BACKBONES, ORDERS, SEEDS)]


def exact_mean(values: Sequence[float]) -> Fraction:
    if not values:
        raise ValueError("mean of no values")
    return sum((Fraction(v) for v in values), Fraction(0)) / len(values)


def parent_means(values: Mapping[CellKey, float]) -> dict[ParentKey, Fraction]:
    grouped: dict[ParentKey, list[float]] = {}
    for (b, o, _), value in sorted(values.items()):
        grouped.setdefault((b, o), []).append(value)
    return {parent: exact_mean(items) for parent, items in grouped.items()}


def _label(parent: ParentKey) -> str:
    return f"b{parent[0]}-o{parent[1]}"


def _flatten(prefix: str, value: Any, out: dict[str, float]) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int | float):
        out[prefix] = float(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), item, out)
    elif isinstance(value, list) and len(value) <= MAX_LIST:
        for index, item in enumerate(value):
            _flatten(f"{prefix}.{index}", item, out)


def scalar_metrics(record: Mapping[str, Any]) -> dict[str, float]:
    """Numeric scalars (and short vectors) of a record, keyed by dotted path."""
    out: dict[str, float] = {}
    for key, value in record.items():
        if key not in EXCLUDED:
            _flatten(key, value, out)
    return out


def _high_fidelity(values: Mapping[CellKey, float], level: float) -> dict[str, Any]:
    threshold = Fraction(level)
    mean = exact_mean(list(values.values()))
    parents = parent_means(values)
    cells_meeting = sum(1 for v in values.values() if Fraction(v) >= threshold)
    parents_meeting = sum(1 for v in parents.values() if v >= threshold)
    clauses = {
        "mean": bool(mean >= threshold),
        "cells": bool(cells_meeting >= MIN_CELLS),
        "parents": bool(parents_meeting >= MIN_PARENTS),
    }
    return {
        "threshold": level,
        "mean": float(mean),
        "cells_meeting": cells_meeting,
        "cells_required": MIN_CELLS,
        "cells_total": len(values),
        "parents_meeting": parents_meeting,
        "parents_required": MIN_PARENTS,
        "parents_total": len(parents),
        "clauses": clauses,
        "passed": all(clauses.values()),
        "parent_means": {_label(p): float(v) for p, v in sorted(parents.items())},
    }


def _loss(values: Mapping[CellKey, float], margin: float) -> dict[str, Any]:
    limit = Fraction(margin)
    mean = exact_mean(list(values.values()))
    parents = parent_means(values)
    cells_negative = sum(1 for v in values.values() if Fraction(v) < 0)
    parents_negative = sum(1 for v in parents.values() if v < 0)
    clauses = {
        "mean": bool(mean <= limit),
        "cells": bool(cells_negative >= MIN_CELLS),
        "parents": bool(parents_negative >= MIN_PARENTS),
    }
    return {
        "margin": margin,
        "mean": float(mean),
        "cells_negative": cells_negative,
        "cells_required": MIN_CELLS,
        "cells_total": len(values),
        "parents_negative": parents_negative,
        "parents_required": MIN_PARENTS,
        "parents_total": len(parents),
        "clauses": clauses,
        "passed": all(clauses.values()),
        "parent_means": {_label(p): float(v) for p, v in sorted(parents.items())},
    }


def _prior(values: Mapping[CellKey, float], margin: float) -> dict[str, Any]:
    limit = Fraction(margin)
    mean = exact_mean(list(values.values()))
    parents = parent_means(values)
    sign = (mean > 0) - (mean < 0)
    cells_same = sum(1 for v in values.values() if ((Fraction(v) > 0) - (Fraction(v) < 0)) == sign)
    parents_same = sum(1 for v in parents.values() if ((v > 0) - (v < 0)) == sign)
    clauses = {
        "magnitude": bool(abs(mean) >= limit),
        "cells": bool(sign != 0 and cells_same >= MIN_CELLS),
        "parents": bool(sign != 0 and parents_same >= MIN_PARENTS),
    }
    return {
        "margin": margin,
        "mean": float(mean),
        "sign": sign,
        "sign_meaning": "positive: removing the prior hurts; negative: the prior hurts",
        "cells_with_sign": cells_same,
        "cells_required": MIN_CELLS,
        "cells_total": len(values),
        "parents_with_sign": parents_same,
        "parents_required": MIN_PARENTS,
        "parents_total": len(parents),
        "clauses": clauses,
        "passed": all(clauses.values()),
        "parent_means": {_label(p): float(v) for p, v in sorted(parents.items())},
    }


def flags(records: Mapping[CellKey, Mapping[str, Any]]) -> dict[str, Any]:
    """FID_K, COS_K, LOSS_K and PRIOR_K for one tree kind (27 final records)."""
    recall_p = {k: float(r["recall"]["P"]["mean"]) for k, r in records.items()}
    recall_c = {k: float(r["recall"]["C"]["mean"]) for k, r in records.items()}
    restrict = {k: float(r["delta_nll"]["restrict"]) for k, r in records.items()}
    prior = {k: float(r["delta_nll"]["prior"]) for k, r in records.items()}
    return {
        "FID": _high_fidelity(recall_p, FID_LEVEL),
        "COS": _high_fidelity(recall_c, FID_LEVEL),
        "LOSS": _loss(restrict, LOSS_MARGIN),
        "PRIOR": _prior(prior, PRIOR_MARGIN),
    }


def paired_differences(
    fixed: Mapping[CellKey, Mapping[str, Any]], learned: Mapping[CellKey, Mapping[str, Any]]
) -> dict[str, Any]:
    """Learned minus fixed for every scalar metric, per parent/seed pair."""
    metrics = {key: scalar_metrics(rec) for key, rec in fixed.items()}
    other = {key: scalar_metrics(rec) for key, rec in learned.items()}
    names = sorted(set.intersection(*(set(m) for m in [*metrics.values(), *other.values()])))
    out: dict[str, Any] = {}
    for name in names:
        diffs = {key: other[key][name] - metrics[key][name] for key in sorted(metrics)}
        parents = parent_means(diffs)
        values = list(diffs.values())
        out[name] = {
            "mean_difference": float(exact_mean(values)),
            "positive": sum(1 for v in values if v > 0),
            "negative": sum(1 for v in values if v < 0),
            "zero": sum(1 for v in values if v == 0),
            "pairs": len(values),
            "parent_means": {_label(p): float(v) for p, v in sorted(parents.items())},
            "parents_positive": sum(1 for v in parents.values() if v > 0),
            "parents_negative": sum(1 for v in parents.values() if v < 0),
        }
    return out


def initial_tables(initial: Mapping[CellKey, Mapping[str, Any]]) -> dict[str, Any]:
    """Descriptive summaries of the completed shared initial checkpoints (any number, 0 to 27)."""
    note = "descriptive only; shared step-0 checkpoints (fixed and learned are identical)"
    metrics = {key: scalar_metrics(rec) for key, rec in initial.items()}
    if not metrics:
        return {"cells": {}, "summary": {}, "note": note}
    names = sorted(set.intersection(*(set(m) for m in metrics.values())))
    summary: dict[str, Any] = {}
    for name in names:
        values = {key: m[name] for key, m in metrics.items()}
        parents = parent_means(values)
        summary[name] = {
            "cells": len(values),
            "mean": float(exact_mean(list(values.values()))),
            "min": min(values.values()),
            "max": max(values.values()),
            "parent_means": {_label(p): float(v) for p, v in sorted(parents.items())},
        }
    return {
        "cells": {f"b{b}-o{o}-s{s}": metrics[(b, o, s)] for (b, o, s) in sorted(metrics)},
        "summary": summary,
        "note": note + "; summarized over completed records only",
    }


def final_label(kind: str, key: CellKey) -> str:
    """Folder and record label of a final checkpoint (equal to ``p6_fidelity_study.Item.label``)."""
    return f"b{key[0]}-o{key[1]}-{kind}-s{key[2]}-final"


def initial_label(key: CellKey) -> str:
    return f"b{key[0]}-o{key[1]}-shared_initial-s{key[2]}"


def _partition(
    records: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, dict[CellKey, Mapping[str, Any]]],
    dict[CellKey, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    """Completed finals, completed initials and every record that did not complete (by label)."""
    finals: dict[str, dict[CellKey, Mapping[str, Any]]] = {kind: {} for kind in KINDS}
    initial: dict[CellKey, Mapping[str, Any]] = {}
    not_completed: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if record.get("outcome") != "completed":
            label = str(record.get("label"))
            if label in not_completed:
                raise ValueError(f"duplicate non-completed record {label}")
            not_completed[label] = record
            continue
        cell = record["cell"]
        key = (int(cell["backbone"]), int(cell["order"]), int(cell["seed"]))
        if record["kind"] == "final":
            kind = cell["variant"]
            if kind not in KINDS or record["step"] != 512 or key in finals[kind]:
                raise ValueError(f"unexpected or duplicate final record {record.get('label')}")
            finals[kind][key] = record
        elif record["kind"] == "initial":
            if record["step"] != 0 or key in initial:
                raise ValueError(f"unexpected or duplicate initial record {record.get('label')}")
            initial[key] = record
        else:
            raise ValueError(f"unknown record kind {record['kind']!r}")
    return finals, initial, not_completed


def _reason(
    label: str,
    not_completed: Mapping[str, Mapping[str, Any]],
    statuses: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Why an expected checkpoint has no completed record (from its record and the suite log)."""
    entry: dict[str, Any] = {"label": label}
    row = statuses.get(label)
    if row is not None:
        entry["suite_status"] = row.get("status")
        entry["suite_reason"] = row.get("reason")
    record = not_completed.get(label)
    if record is not None:
        entry["record_outcome"] = record.get("outcome")
        for name in ("gate", "message", "error"):
            if name in record:
                entry[name] = record[name]
    if row is None and record is None:
        entry["suite_status"] = "no record and no suite status"
    return entry


def analyze(
    records: Sequence[Mapping[str, Any]],
    statuses: Mapping[str, Mapping[str, Any]] | None = None,
    suite: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Registered flags from the 54 final records alone; step 0 is summarized over what exists.

    Flags and the paired learned-minus-fixed differences need all 54 completed final records. If
    any final is missing or did not complete the result says INCOMPLETE and lists each one with
    its recorded reason; it is never an exception. The step-0 checkpoints are descriptive: they
    are summarized over the completed records and every unexecuted or failed label is listed.
    ``statuses`` maps a checkpoint label to its row of the suite log (``cells.json``).
    """
    statuses = statuses or {}
    finals, initial, not_completed = _partition(records)
    expected = expected_cells()
    final_missing = [
        _reason(final_label(kind, key), not_completed, statuses)
        for kind in KINDS
        for key in expected
        if key not in finals[kind]
    ]
    initial_missing = [
        _reason(initial_label(key), not_completed, statuses)
        for key in expected
        if key not in initial
    ]
    known = {final_label(kind, key) for kind in KINDS for key in expected} | {
        initial_label(key) for key in expected
    }
    unrecognized = sorted(label for label in not_completed if label not in known)
    finals_complete = not final_missing
    result: dict[str, Any] = {
        "schema": "P6Q-analysis-v2",
        "label": "descriptive diagnostic on the P5 panel; not Astra validated",
        "suite": dict(suite) if suite is not None else None,
        "records": {"final": sum(len(v) for v in finals.values()), "initial": len(initial)},
        "expected": {"final": len(KINDS) * len(expected), "initial": len(expected)},
        "finals_missing_or_not_completed": final_missing,
        "step0_unexecuted_or_failed": initial_missing,
        "unrecognized_non_completed_records": unrecognized,
        "flags_status": "COMPUTED" if finals_complete else "INCOMPLETE",
    }
    if finals_complete:
        result["flags"] = {kind: flags(finals[kind]) for kind in KINDS}
        result["paired_learned_minus_fixed"] = paired_differences(finals[FIXED], finals[LEARNED])
    else:
        incomplete = {
            "status": "INCOMPLETE",
            "reason": "at least one of the 54 final records is missing or did not complete; "
            "no registered flag is computed and none is estimated",
        }
        result["flags"] = {kind: dict(incomplete) for kind in KINDS}
        result["paired_learned_minus_fixed"] = dict(incomplete)
    result["initial_checkpoints"] = {
        **initial_tables(initial),
        "completed": len(initial),
        "of": len(expected),
    }
    return result
