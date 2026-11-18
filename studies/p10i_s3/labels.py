# ruff: noqa: E501
"""P10IS3 labels (ADR-0026 sections 5.2, 6.1 to 6.6, 12): pure functions of plain numbers, no torch, no IO.

A per-cell list holds a float, or None for a value that is non-finite. A failed cell (section 6.1) is a None in the C list of its arm: then every mean condition of that arm in that regime is false and the cell counts
as failing every per-cell and per-parent count. A None under an intervention (P_used, X_mean) on a finite C fails D2 or D3 for that cell and makes the mean condition false.
Every comparison is >= or > exactly as written, with no rounding first.
"""

from collections.abc import Sequence
from typing import Any

from .core import Thresholds

Vals = Sequence[float | None]
NOT_EVALUABLE, INCONCLUSIVE = "NOT EVALUABLE", "INCONCLUSIVE"
DEPENDENT, CAP_NO_DEP, NO_CAPACITY = "DEPENDENT", "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE", "NO CAPACITY"
MEMORY_AHEAD, COMPETITIVE, NOT_COMPETITIVE = "MEMORY AHEAD", "COMPETITIVE", "NOT COMPETITIVE"
CONVERGED, NOT_CONVERGED, NOT_DETERMINED = "CONVERGED", "NOT CONVERGED", "NOT DETERMINED"


def _all_finite(v: Vals) -> bool:
    return all(x is not None for x in v)


def mean_of(v: Vals) -> float | None:
    """Arithmetic mean over every registered cell; None if any cell has no finite value (no mean over fewer than the registered cells)."""
    if not v or not _all_finite(v):
        return None
    return sum(float(x) for x in v if x is not None) / len(v)


def parent_means(v: Vals, per: int = 3) -> list[float | None]:
    return [mean_of(v[i : i + per]) for i in range(0, len(v), per)]


def _count(pred: Sequence[bool]) -> int:
    return sum(1 for p in pred if p)


def _ge(x: float | None, t: float) -> bool:
    return x is not None and x >= t


def _gt(x: float | None, t: float) -> bool:
    return x is not None and x > t


def d1(c: Vals, th: Thresholds) -> dict[str, Any]:
    """Capacity: mean C >= 0.005; C > 0 in >= 22/27 cells; parent mean C > 0 in >= 8/9."""
    pm = parent_means(c)
    m = mean_of(c)
    n_cell, n_par = _count([_gt(x, 0.0) for x in c]), _count([_gt(x, 0.0) for x in pm])
    return {"mean": m, "cells": n_cell, "parents": n_par, "ok": _ge(m, th.effect) and n_cell >= th.min_cells and n_par >= th.min_parents}


def d_effect(c: Vals, e: Vals, th: Thresholds) -> dict[str, Any]:
    """D2 (e = P_used) or D3 (e = X_mean): mean e >= 0.005; (C > 0 and e >= 0.5 C) in >= 22/27 cells; parent mean e > 0 in >= 8/9."""
    m = mean_of(e)
    n_cell = _count([(ci is not None and ci > 0 and ei is not None and ei >= th.half * ci) for ci, ei in zip(c, e, strict=True)])
    n_par = _count([_gt(x, 0.0) for x in parent_means(e)])
    return {"mean": m, "cells": n_cell, "parents": n_par, "ok": _ge(m, th.effect) and n_cell >= th.min_cells and n_par >= th.min_parents}


def line1(c: Vals, p_used: Vals, x_mean: Vals, th: Thresholds, *, integrity_stop: bool = False, collapsed: Sequence[bool] | None = None) -> dict[str, Any]:
    """Section 6.2: ordered rows. ``integrity_stop``: a stop or integrity case of section 10, or BASE missing or failing (row 1). A COLLAPSED cell (used-slot set under two slots) fails D2 and is listed."""
    if integrity_stop:
        return {"label": NOT_EVALUABLE, "conditions": {}, "failing": [], "collapsed": []}
    p = list(p_used)
    col = list(collapsed or [False] * len(p))
    p = [None if cl else v for v, cl in zip(p, col, strict=True)]  # fails D2 (never passes): a collapsed cell has no demonstrated stored association
    cond = {"D1": d1(c, th), "D2": d_effect(c, p, th), "D3": d_effect(c, x_mean, th)}
    ok = {k: v["ok"] for k, v in cond.items()}
    if ok["D1"] and ok["D2"] and ok["D3"]:
        label, failing = DEPENDENT, []
    elif ok["D1"]:
        label, failing = CAP_NO_DEP, [k for k in ("D2", "D3") if not ok[k]]
    else:
        label, failing = NO_CAPACITY, ["D1"]
    return {"label": label, "conditions": cond, "failing": failing, "collapsed": [i for i, cl in enumerate(col) if cl]}


def line2(c: Vals, c_dense: Vals, th: Thresholds, *, integrity_stop: bool = False) -> dict[str, Any]:
    """Section 6.3. Q = C - C_dense is the same quantity as A - H when both gains share one baseline B (it is computed from the gains so no list of NLLs is needed here)."""
    q: list[float | None] = [None if (a is None or b is None) else a - b for a, b in zip(c, c_dense, strict=True)]
    if integrity_stop or not _all_finite(c_dense):
        return {"label": NOT_EVALUABLE, "conditions": {}, "q_mean": mean_of(q)}
    mq, mc, md = mean_of(q), mean_of(c), mean_of(c_dense)
    k1 = {"mean": mq, "cells": _count([_ge(x, th.dense_tolerance) for x in q]), "parents": _count([_ge(x, th.dense_tolerance) for x in parent_means(q)])}
    k1["ok"] = _ge(mq, th.dense_tolerance) and k1["cells"] >= th.min_cells and k1["parents"] >= th.min_parents
    k2 = {"mean_C": mc, "mean_C_dense": md, "ok": mc is not None and md is not None and mc >= th.dense_share * md}
    k3 = {"mean": mq, "cells": _count([_gt(x, 0.0) for x in q]), "parents": _count([_gt(x, 0.0) for x in parent_means(q)])}
    k3["ok"] = _ge(mq, th.effect) and k3["cells"] >= th.min_cells and k3["parents"] >= th.min_parents
    cond = {"K1": k1, "K2": k2, "K3": k3}
    if md is not None and md < th.dense_floor:
        label = NOT_EVALUABLE
    elif k3["ok"]:
        label = MEMORY_AHEAD
    elif k1["ok"] and k2["ok"]:
        label = COMPETITIVE
    else:
        label = NOT_COMPETITIVE
    return {"label": label, "conditions": cond, "q_mean": mq}


def convergence_tag(m_mid: float | None, m_end: float | None, eps: float, *, failed: bool = False) -> dict[str, Any]:
    """Section 5.2: delta = M(8192) - M(16384); CONVERGED if delta < eps (a rising loss counts as converged). NOT DETERMINED (counts as NOT CONVERGED wherever read) with a failed cell."""
    if failed or m_mid is None or m_end is None:
        return {"tag": NOT_DETERMINED, "delta": None, "counts_as_not_converged": True}
    delta = m_mid - m_end
    return {"tag": CONVERGED if delta < eps else NOT_CONVERGED, "delta": delta, "counts_as_not_converged": not delta < eps}


def past_best(means: dict[int, float | None], u_star: int, margin: float, *, failed: bool = False) -> dict[str, Any]:
    """PAST BEST CHECKPOINT: the mean at U* is more than ``margin`` above the lowest earlier checkpoint mean (REP and REP-U only)."""
    end = means.get(u_star)
    earlier = [v for k, v in means.items() if k < u_star]
    if failed or end is None or not earlier or any(v is None for v in earlier):
        return {"tag": NOT_DETERMINED, "flag": False}
    return {"tag": "PAST BEST CHECKPOINT" if end - min(v for v in earlier if v is not None) > margin else None, "flag": end - min(v for v in earlier if v is not None) > margin}


def apply_tags_line2(base: dict[str, Any], *, regime: str, mem_name: str, mem_edge: bool, dense_edge: bool, mean_nll_mem: float | None, mean_nll_dense: float | None, mem_conv: dict[str, Any], dense_conv: dict[str, Any], mem_past: dict[str, Any], dense_past: dict[str, Any]) -> dict[str, Any]:
    """Section 6.4, in the order written. NOT EVALUABLE takes no tag (ambiguity listed: tags 3 and 4 are also appended to an INCONCLUSIVE label; they change no label)."""
    label, tags = base["label"], []
    if label == NOT_EVALUABLE:
        return {"label": label, "base_label": label, "tags": tags}
    if label == NOT_COMPETITIVE and mem_edge:
        label = f"{INCONCLUSIVE} (MEMORY RATE AT EDGE)"
    elif label in (COMPETITIVE, MEMORY_AHEAD) and dense_edge:
        label = f"{INCONCLUSIVE} (DENSE RATE AT EDGE)"
    losing = None
    if mean_nll_mem is not None and mean_nll_dense is not None and mean_nll_mem != mean_nll_dense:
        losing = "memory" if mean_nll_mem > mean_nll_dense else "dense"
    if losing == "memory" and mem_conv["counts_as_not_converged"]:
        tags.append("(MEMORY STILL IMPROVING)")
    if losing == "dense" and dense_conv["counts_as_not_converged"]:
        tags.append("(DENSE STILL IMPROVING)")
    if regime in ("REP", "REP-U"):
        if mem_past.get("flag"):
            tags.append(f"({mem_name} PAST BEST CHECKPOINT)")
        if dense_past.get("flag"):
            tags.append("(D-ADAPT PAST BEST CHECKPOINT)")
    return {"label": label, "base_label": base["label"], "tags": tags}


def apply_tags_line1(base: dict[str, Any], *, regime: str, conv: dict[str, Any], past: dict[str, Any], edge: bool) -> dict[str, Any]:
    tags = []
    if base["label"] != NOT_EVALUABLE:
        if conv["counts_as_not_converged"]:
            tags.append("(M-TREE NOT CONVERGED)")
        if regime in ("REP", "REP-U") and past.get("flag"):
            tags.append("(M-TREE PAST BEST CHECKPOINT)")
    return {"label": base["label"], "base_label": base["label"], "tags": tags, "rate_at_edge": edge}


def registered_line(by_regime: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Section 6.5: the registered label of a line is its FRESH regime label; REP-U and REP are printed beside it, in that order, and never make a line positive."""
    fresh = by_regime["FRESH"]
    return {"label": fresh["label"], "regime_labels": {"REP-U": by_regime.get("REP-U", {}).get("label"), "REP": by_regime.get("REP", {}).get("label")}}


def registered_positive(line1_label: str, line2_tree_base_label: str) -> dict[str, bool]:
    return {"line1": line1_label == DEPENDENT, "line2": line2_tree_base_label in (COMPETITIVE, MEMORY_AHEAD)}


def route_a(line1_fresh: str, line2_tree_fresh_base_and_final: tuple[str, str], dense_fresh_conv: dict[str, Any]) -> dict[str, Any]:
    """Section 12 and ruling 13 of open choices: A1 needs line 1 FRESH = DEPENDENT; A2 needs COMPETITIVENESS[TREE] FRESH = COMPETITIVE or MEMORY AHEAD (the final label, so any INCONCLUSIVE never qualifies);
    neither qualifies when D-ADAPT's registered FRESH tag is NOT CONVERGED (NOT DETERMINED counts as NOT CONVERGED)."""
    base, final = line2_tree_fresh_base_and_final
    a1 = line1_fresh == DEPENDENT
    a2 = final in (COMPETITIVE, MEMORY_AHEAD) and base == final
    closed = bool(dense_fresh_conv["counts_as_not_converged"])
    return {"A1_label_qualifies": a1, "A2_label_qualifies": a2, "dense_fresh_not_converged": closed, "A1": a1 and not closed, "A2": a2 and not closed, "route_a_open": a1 and a2 and not closed}


def gap_label(g: Vals, th: Thresholds, *, positive: str, negative: str, within: str = "WITHIN RESOLUTION") -> str:
    """Section 6.6 reading rule: ``positive`` if mean >= +0.005 and G > 0 in >= 22/27; ``negative`` if mean <= -0.005 and G < 0 in >= 22/27; otherwise within resolution. None anywhere: NOT DETERMINED."""
    m = mean_of(g)
    if m is None:
        return NOT_DETERMINED
    if m >= th.routing_effect and _count([x is not None and x > 0 for x in g]) >= th.min_cells:
        return positive
    if m <= -th.routing_effect and _count([x is not None and x < 0 for x in g]) >= th.min_cells:
        return negative
    return within


def trend(label_512: str, label_ustar: str) -> str:
    return "GAP CHANGES WITH DURATION" if label_512 != label_ustar else "NO CHANGE AT THIS RESOLUTION"
