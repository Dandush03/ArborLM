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
    study_level: list[str] = field(default_factory=list)  # sections other than cells (baseline, assembled, retrieval, routers, ensemble) with a difference beyond tolerance

    def to_json(self) -> dict[str, Any]:
        return {"complete": self.complete, "mode": self.mode, "differences": [d.to_json() for d in self.differences], "not_evaluated_cells": self.not_evaluated_cells, "missing": self.missing, "memory_exceeded": self.memory_exceeded, "study_level": self.study_level}


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


NON_VERDICT_KEYS = frozenset({"design", "recomputation", "cost_lines", "not_evaluated_reasons", "reasons", "oracle_line", "combined_line", "label_with_design", "by_construction"})
COUNT_ONLY_KEYS = frozenset({"engineering", "incomplete"})
KEEP_STRING_KEYS = frozenset({"control_failed", "cell", "replicate", "router_tasks"})  # strings that name a cell or a router: kept whole although they carry numerals


def verdict_view(obj: Any, key: str = "") -> Any:
    """What a verdict comparison reads: booleans, verdict words and their placement, and nothing numeric. Numbers are dropped (a difference within the recomputation's tolerance is a difference in a
    number, and it never changes a verdict by itself); strings that carry a numeral (formatted numbers, cell paths in free text) are dropped; the lists of engineering and incomplete reasons are compared
    by their length. GEN, CONTROL-FAILED, the gates, classes, annotations, composition and the label are all read through this view (the lead's ruling of 2026-11-15)."""
    if key in NON_VERDICT_KEYS:
        return None
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k in sorted(obj, key=str):
            v = verdict_view(obj[k], str(k))
            if v is not None:
                out[str(k)] = v
        return out
    if isinstance(obj, list | tuple):
        if key in COUNT_ONLY_KEYS:
            return len(obj)
        return [verdict_view(v, key) for v in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int | float):
        return None
    if isinstance(obj, str):
        return obj if key in KEEP_STRING_KEYS or not any(ch.isdecimal() for ch in obj) else None
    return None


def outcome_changes(registered_outcome: Mapping[str, Any], recomputed_outcome: Mapping[str, Any]) -> list[str]:
    """Every verdict of the outcome (gates, classes, annotations, composition, GEN, CONTROL-FAILED, label and the rest read through ``verdict_view``) compared between the registered scores and the
    recomputed ones; the paths that differ."""
    a, b = flatten(verdict_view(registered_outcome)), flatten(verdict_view(recomputed_outcome))
    return [path.lstrip("/") for path in sorted(set(a) | set(b)) if a.get(path, "<absent>") != b.get(path, "<absent>")]


# --- the whole study: every recomputed quantity ---------------------------------------------------------------------------------------------------
REP_SECTIONS = ("assembled", "retrieval", "routers", "ensemble")


def compare_study(registered: Mapping[str, Any], recomputed: Mapping[str, Any], mode: str, *, memory_exceeded: bool = False) -> RecomputeResult:
    """Compare every recomputed quantity: the cell scores and extras, the Stage 0 and teacher scores (``baseline``, every gap's denominator), and per replicate the assembled arms, the retrieval baselines,
    the router records (route accuracy decides ROUTER QUALIFIED) and the ensemble. A registered quantity the recomputation lacks makes it incomplete. A difference beyond the case's tolerance is listed;
    for a cell it makes the cell NOT_EVALUATED, for any other quantity it lists the section in ``study_level`` (the reported value is the recomputed one)."""
    if mode not in MODES:
        raise ValueError(f"unknown recomputation mode {mode!r}")
    tol = tolerance_of(mode)
    reg_reps, rec_reps = list(registered.get("replicates", [])), list(recomputed.get("replicates", []))
    reg_cells = {lab: rec for rep in reg_reps for lab, rec in rep.get("cells", {}).items()}
    rec_cells = {lab: rec for rep in rec_reps for lab, rec in rep.get("cells", {}).items()}
    res = compare_cells(reg_cells, rec_cells, mode, memory_exceeded=memory_exceeded)
    diffs, missing = list(res.differences), list(res.missing)
    study_level: list[str] = []

    def section(name: str, a: Any, b: Any) -> None:
        if a in (None, {}, []):
            return
        if b in (None, {}, []):
            missing.append(name)
            return
        fa, fb = flatten(a), flatten(b)
        found = False
        for path in sorted(set(fa) | set(fb)):
            if path not in fa or path not in fb:
                diffs.append(Difference(name, path, fa.get(path, "<absent>"), fb.get(path, "<absent>"), mode))
                found = True
            elif not _same(fa[path], fb[path], tol, mode == OWN):
                diffs.append(Difference(name, path, fa[path], fb[path], mode))
                found = True
        if found:
            study_level.append(name)

    section("baseline", registered.get("baseline"), recomputed.get("baseline"))
    for r, rep in enumerate(reg_reps):
        rr = rec_reps[r] if r < len(rec_reps) else {}
        for sec in REP_SECTIONS:
            section(f"r{r}/{sec}", rep.get(sec), rr.get(sec))
    ne = sorted({d.cell for d in diffs if d.cell in reg_cells})
    return RecomputeResult(complete=not missing and not memory_exceeded, mode=mode, differences=diffs, not_evaluated_cells=ne, missing=missing, memory_exceeded=memory_exceeded, study_level=sorted(set(study_level)))


def reported_study(registered: Mapping[str, Any], recomputed: Mapping[str, Any], result: RecomputeResult) -> dict[str, Any]:
    """The study as reported: the recomputed CPU value replaces the registered one wherever the difference is beyond tolerance (cells with a difference, and any other section listed in
    ``study_level``). A difference within tolerance leaves the registered value, so it cannot change a verdict."""
    out = copy.deepcopy(dict(registered))
    rec_reps = list(recomputed.get("replicates", []))
    ne = set(result.not_evaluated_cells)
    for r, rep in enumerate(out.get("replicates", [])):
        rr = rec_reps[r] if r < len(rec_reps) else {}
        for lab in list(rep.get("cells", {})):
            if lab in ne:
                src = rr.get("cells", {}).get(lab, {})
                rep["cells"][lab] = {**rep["cells"][lab], "scores": copy.deepcopy(src.get("scores")), "extras": copy.deepcopy(src.get("extras")), "recomputed_replaced": True}
        for sec in REP_SECTIONS:
            if f"r{r}/{sec}" in result.study_level:
                rep[sec] = copy.deepcopy(rr.get(sec))
    if "baseline" in result.study_level:
        out["baseline"] = copy.deepcopy(recomputed.get("baseline"))
    return out


def outcome_under_recomputation(registered: Mapping[str, Any], recomputed: Mapping[str, Any] | None, mode: str, *, memory_exceeded: bool = False) -> dict[str, Any]:
    """The study outcome under the recomputation rule, over every recomputed quantity (audits B-M9 and C-M3): INCOMPLETE without a completed recomputation (no class is printed); ENGINEERING-FAILURE if
    any verdict (gate, class, annotation, composition, GEN, CONTROL-FAILED, label) differs between the registered study and the recomputed one; otherwise the cells and sections with a difference beyond
    tolerance carry the recomputed value, their mechanisms the class NOT_EVALUATED. The recomputed study is analyzed with its own recomputed baseline (it reuses nothing from the registered record)."""
    from . import analysis

    if recomputed is None:
        out = analysis.analyze({**registered, "incomplete": [*registered.get("incomplete", []), "the independent recomputation has not completed"]})
        out["recomputation"] = recomputation_status(None, [])
        return analysis.strip_classes_if_incomplete(out)
    res = compare_study(registered, recomputed, mode, memory_exceeded=memory_exceeded)
    if not res.complete:
        why = " within the memory limits" if memory_exceeded else ""
        out = analysis.analyze({**registered, "incomplete": [*registered.get("incomplete", []), f"the recomputation could not be completed{why}" + (f" (missing: {', '.join(res.missing[:5])})" if res.missing else "")]})
        out["recomputation"] = {**recomputation_status(res, []), "differences": [d.to_json() for d in res.differences], "missing": res.missing, "study_level": res.study_level}
        return analysis.strip_classes_if_incomplete(out)
    # the recomputed study is analyzed as recomputed (cells, baseline, assembled arms, retrieval, routers, ensemble); the records that were not recomputed (pre-freeze, gates, design) are the registered ones
    rec_for_verdicts = {**copy.deepcopy(dict(registered)), "baseline": copy.deepcopy(recomputed.get("baseline", {})), "replicates": copy.deepcopy(list(recomputed.get("replicates", [])))}
    changed = outcome_changes(analysis.analyze(registered), analysis.analyze(rec_for_verdicts))
    if changed:
        note = f"a recomputation difference changes {len(changed)} verdict entries ({', '.join(changed[:6])})"
        out = analysis.analyze({**registered, "engineering": [*registered.get("engineering", []), note]})
        out["recomputation"] = {**recomputation_status(res, changed), "differences": [d.to_json() for d in res.differences], "study_level": res.study_level}
        return out
    out = analysis.analyze(reported_study(registered, recomputed, res), set(res.not_evaluated_cells))
    out["recomputation"] = {**recomputation_status(res, []), "differences": [d.to_json() for d in res.differences], "study_level": res.study_level}
    return out


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
