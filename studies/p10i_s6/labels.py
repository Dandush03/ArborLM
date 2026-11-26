# ruff: noqa: E501
"""P10IS6 labels (ADR-0031 sections 9 to 12): pure functions of plain numbers, no torch, no IO.

A per-cell list holds a float, or None for a value that is non-finite or not determined. A None anywhere in a mean makes the mean None (no mean over fewer than the registered cells, section 4). Every comparison is >=, >, <= or <
exactly as written, with no rounding first (section 4). Means follow ruling G5: Python float ``sum`` in cell order divided by the count; a parent mean likewise over three cells.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from .core import DENSE, FLAT, Thresholds

Vals = Sequence[float | None]

M_AHEAD, D_AHEAD, LEVEL, UNDECIDED, CLASS_ND = "M-AHEAD", "D-AHEAD", "LEVEL", "UNDECIDED", "NOT DETERMINED"
CONVERGED, NOT_CONVERGED, NOT_DETERMINED = "CONVERGED", "NOT CONVERGED", "NOT DETERMINED"
NOT_EVALUABLE = "NOT EVALUABLE"
MEMORY_UNSTABLE = "MEMORY UNSTABLE (FAILED CELLS)"
DEPENDENT, CAP_NO_DEP, NO_CAPACITY = "DEPENDENT", "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE", "NO CAPACITY"
ONE_DOUBLING = " (ONE DOUBLING OF EVIDENCE)"

PERSISTS = "PERSISTS AT CONVERGENCE"
ORDERING_NOT_STABLE = "ORDERING NOT STABLE AFTER CONVERGENCE"
LEVEL_AT = "LEVEL AT CONVERGENCE"
DENSE_AHEAD_AT = "DENSE AHEAD AT CONVERGENCE"
LEAD_NOT_ESTABLISHED = "LEAD NOT ESTABLISHED AT CONVERGENCE"
MEM_AHEAD_DENSE_CONV = "MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING)"
DENSE_AHEAD_MEM_CONV = "DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING)"
NR_DENSE = "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)"
NR_MEMORY = "CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING)"
NR_BOTH = "CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)"

TAG_SENTENCE = "over 16,384 to U_max updates only; descriptive; this says nothing about the ordering at convergence and is not the label PERSISTS."
TAG_ND = "TREND NOT DETERMINED"
TAG_ABSENT = "LEAD ABSENT AT RUNG 0 (16,384 UPDATES, NEW PARENTS AND DATA)"
TAG_NOT_MONOTONE = "NOT MONOTONE"
TAG_SHRINKING, TAG_GROWING, TAG_HELD = "LEAD SHRINKING", "LEAD GROWING", "LEAD HELD AT EVERY RUNG"


def mean_of(v: Vals) -> float | None:
    if not v or any(x is None for x in v):
        return None
    return sum(float(x) for x in v if x is not None) / len(v)


def parent_means(v: Vals, per: int = 3) -> list[float | None]:
    return [mean_of(v[i : i + per]) for i in range(0, len(v), per)]


def count(pred: Sequence[bool]) -> int:
    return sum(1 for p in pred if p)


def _ge(x: float | None, t: float) -> bool:
    return x is not None and x >= t


def _gt(x: float | None, t: float) -> bool:
    return x is not None and x > t


def _lt(x: float | None, t: float) -> bool:
    return x is not None and x < t


def _le(x: float | None, t: float) -> bool:
    return x is not None and x <= t


def diff(a: Vals, b: Vals) -> list[float | None]:
    """Element-wise ``a - b``; None if either is None."""
    return [None if (x is None or y is None) else x - y for x, y in zip(a, b, strict=True)]


# --- the class of a rung (section 10) and HELD (section 12.6) ---------------------------------------------------------------------------------
def _ahead(q: Vals, th: Thresholds) -> bool:
    return _ge(mean_of(q), th.effect) and count([_gt(x, 0.0) for x in q]) >= th.min_cells and count([_gt(x, 0.0) for x in parent_means(q)]) >= th.min_parents


def _behind(q: Vals, th: Thresholds) -> bool:
    return _le(mean_of(q), -th.effect) and count([_lt(x, 0.0) for x in q]) >= th.min_cells and count([_lt(x, 0.0) for x in parent_means(q)]) >= th.min_parents


def held(q: Vals, th: Thresholds) -> bool:
    """HELD(k): ADR-0026's K3 at rung k (the Q-dagger clause of class M-AHEAD is not part of it)."""
    return _ahead(q, th)


def rung_class(q: Vals, q_dag: Vals, th: Thresholds) -> str:
    """Section 10: the first row that applies. NOT DETERMINED (never reached by a label) if a mean is not defined."""
    m = mean_of(q)
    if m is None or mean_of(q_dag) is None:
        return CLASS_ND
    if _ahead(q, th) and _ahead(q_dag, th):
        return M_AHEAD
    if _behind(q, th):
        return D_AHEAD
    if -th.effect < m < th.effect:
        return LEVEL
    return UNDECIDED


# --- convergence (section 9) ---------------------------------------------------------------------------------------------------------------------
def convergence_state(delta: float | None, delta_run: float | None, eps: float) -> str:
    """Converged at rung k iff delta(arm, k) < eps and deltarun(arm, k) < eps (a rise counts as below eps). NOT DETERMINED (counts as not converged) if either is not defined."""
    if delta is None or delta_run is None:
        return NOT_DETERMINED
    return CONVERGED if (delta < eps and delta_run < eps) else NOT_CONVERGED


def is_converged(state: str) -> bool:
    return state == CONVERGED


def settled_from(states: Mapping[int, str], k: int, k_max: int) -> bool:
    return all(is_converged(states[j]) for j in range(k, k_max + 1))


def k_star(states: Mapping[str, Mapping[int, str]], k_max: int) -> int | None:
    """Section 9.2: the smallest k in 0..k_max such that both arms are settled from k; None if there is none (at least one arm is not converged at k_max)."""
    for k in range(0, k_max + 1):
        if all(settled_from(states[a], k, k_max) for a in (FLAT, DENSE)):
            return k
    return None


def j_dagger(l_dense: Mapping[int, float | None], k_max: int) -> int | None:
    """Section 4 and ruling G13: the rung in 0..k_max with the lowest L(D-ADAPT, .); on an exact tie the larger rung. None if any L is not defined."""
    vals = [l_dense[k] for k in range(0, k_max + 1)]
    if any(v is None for v in vals):
        return None
    best = None
    for k in range(0, k_max + 1):
        v = float(l_dense[k])  # type: ignore[arg-type]
        if best is None or v <= float(l_dense[best]):  # type: ignore[arg-type]
            best = k
    return best


# --- line P (section 12.3) -----------------------------------------------------------------------------------------------------------------------------
def line_p(*, causes: Sequence[str], flat_failed: bool, k_star_: int | None, k_max: int, classes: Mapping[int, str], conv_end: Mapping[str, bool], conv_prev: Mapping[str, bool]) -> dict[str, Any]:
    """The first row that applies decides. ``conv_end`` is "converged at k_max", ``conv_prev`` "converged at k_max - 1" (for the ONE DOUBLING note of rows 8 and 9)."""
    if causes:
        return {"row": 1, "label": f"{NOT_EVALUABLE} ({'; '.join(causes)})", "base": NOT_EVALUABLE, "one_doubling": False}
    if flat_failed:
        return {"row": 2, "label": MEMORY_UNSTABLE, "base": MEMORY_UNSTABLE, "one_doubling": False}
    if k_star_ is not None:
        cls = [classes[k] for k in range(k_star_, k_max + 1)]
        one = k_star_ == k_max
        if len(set(cls)) != 1:
            return {"row": 3, "label": f"{ORDERING_NOT_STABLE} ({', '.join(cls)})", "base": ORDERING_NOT_STABLE, "one_doubling": one, "classes": cls}
        row, lab = {M_AHEAD: (4, PERSISTS), LEVEL: (5, LEVEL_AT), D_AHEAD: (6, DENSE_AHEAD_AT), UNDECIDED: (7, LEAD_NOT_ESTABLISHED)}[cls[0]]
        return {"row": row, "label": lab + (ONE_DOUBLING if one else ""), "base": lab, "one_doubling": one}
    cd, cm = conv_end[DENSE], conv_end[FLAT]
    end_class = classes[k_max]
    if cd and not cm and end_class == M_AHEAD:
        one = not conv_prev[DENSE]
        return {"row": 8, "label": MEM_AHEAD_DENSE_CONV + (ONE_DOUBLING if one else ""), "base": MEM_AHEAD_DENSE_CONV, "one_doubling": one}
    if cm and not cd and end_class == D_AHEAD:
        one = not conv_prev[FLAT]
        return {"row": 9, "label": DENSE_AHEAD_MEM_CONV + (ONE_DOUBLING if one else ""), "base": DENSE_AHEAD_MEM_CONV, "one_doubling": one}
    if not cd and cm:
        return {"row": 10, "label": NR_DENSE, "base": NR_DENSE, "one_doubling": False}
    if cd and not cm:
        return {"row": 11, "label": NR_MEMORY, "base": NR_MEMORY, "one_doubling": False}
    return {"row": 12, "label": NR_BOTH, "base": NR_BOTH, "one_doubling": False}


# --- D[FLAT] (sections 11 and 12.4) -----------------------------------------------------------------------------------------------------------------------
def f1(c: Vals, th: Thresholds) -> dict[str, Any]:
    pm = parent_means(c)
    m = mean_of(c)
    n_cell, n_par = count([_gt(x, 0.0) for x in c]), count([_gt(x, 0.0) for x in pm])
    return {"mean": m, "cells": n_cell, "parents": n_par, "ok": _ge(m, th.effect) and n_cell >= th.min_cells and n_par >= th.min_parents}


def f_effect(c: Vals, e: Vals, th: Thresholds) -> dict[str, Any]:
    """F2 (e = P_used) or F3 (e = X_mean): mean e >= 0.005; (C > 0 and e >= 0.5 C) in >= 22 cells; parent mean e > 0 in >= 8 parents."""
    m = mean_of(e)
    n_cell = count([(ci is not None and ci > 0 and ei is not None and ei >= th.half * ci) for ci, ei in zip(c, e, strict=True)])
    n_par = count([_gt(x, 0.0) for x in parent_means(e)])
    return {"mean": m, "cells": n_cell, "parents": n_par, "ok": _ge(m, th.effect) and n_cell >= th.min_cells and n_par >= th.min_parents}


def d_flat(c: Vals, p_used: Vals, x_mean: Vals, th: Thresholds, *, collapsed: Sequence[bool], not_evaluable: bool) -> dict[str, Any]:
    """Section 12.4. A collapsed cell (fewer than two used slots) fails F2 and is listed. NOT EVALUABLE if line P is NOT EVALUABLE by items 1-2 or M-FLAT has a failed cell at rung R (``not_evaluable``)."""
    if not_evaluable:
        return {"label": NOT_EVALUABLE, "conditions": {}, "failing": [], "collapsed": []}
    p = [None if cl else v for v, cl in zip(p_used, collapsed, strict=True)]
    cond = {"F1": f1(c, th), "F2": f_effect(c, p, th), "F3": f_effect(c, x_mean, th)}
    ok = {k: v["ok"] for k, v in cond.items()}
    if ok["F1"] and ok["F2"] and ok["F3"]:
        label, failing = DEPENDENT, []
    elif ok["F1"]:
        label, failing = CAP_NO_DEP, [k for k in ("F2", "F3") if not ok[k]]
    else:
        label, failing = NO_CAPACITY, ["F1"]
    return {"label": label, "conditions": cond, "failing": failing, "collapsed": [i for i, cl in enumerate(collapsed) if cl]}


def dependence_qualified(line_row: int, d_label: str) -> bool:
    """A label of rows 4 or 8 is dependence-qualified only if D[FLAT] = DEPENDENT."""
    return line_row in (4, 8) and d_label == DEPENDENT


# --- R16 and OA: ADR-0026 section 6.3's rule (K1, K2, K3 and the dense floor), section 12.4 ---------------------------------------------------------------------
REPLICATED = "REPLICATED AT 16,384"
NOT_REPL_WITHIN = "NOT REPLICATED (WITHIN TOLERANCE)"
NOT_REPL_OTHER = "NOT REPLICATED (otherwise)"


def replication(c_flat: Vals, c_dense: Vals, th: Thresholds, *, integrity_stop: bool = False) -> dict[str, Any]:
    q = diff(c_flat, c_dense)  # Q = A - H = C - Cd when both gains share one baseline
    if integrity_stop or any(x is None for x in c_dense) or any(x is None for x in c_flat):
        return {"label": NOT_EVALUABLE, "q_mean": mean_of(q)}
    mq, mc, md = mean_of(q), mean_of(c_flat), mean_of(c_dense)
    k1_cells = count([_ge(x, th.dense_tolerance) for x in q])
    k1_par = count([_ge(x, th.dense_tolerance) for x in parent_means(q)])
    k1 = _ge(mq, th.dense_tolerance) and k1_cells >= th.min_cells and k1_par >= th.min_parents
    k2 = mc is not None and md is not None and mc >= th.dense_share * md
    k3 = _ge(mq, th.effect) and count([_gt(x, 0.0) for x in q]) >= th.min_cells and count([_gt(x, 0.0) for x in parent_means(q)]) >= th.min_parents
    if md is not None and md < th.dense_floor:
        label = NOT_EVALUABLE
    elif k3:
        label = REPLICATED
    elif k1 and k2:
        label = NOT_REPL_WITHIN
    else:
        label = NOT_REPL_OTHER
    return {"label": label, "q_mean": mq, "K1": k1, "K2": k2, "K3": k3}


# --- the trend line (section 12.6) -----------------------------------------------------------------------------------------------------------------------------
def trend_tag(held_by_rung: Mapping[int, bool], mean_q: Mapping[int, float | None], k_max: int, th: Thresholds, *, nd: bool) -> dict[str, Any]:
    """One tag, the first row that applies. Tags of rows 3 to 7 carry delta = mean Q(k_max) - mean Q(0) and mean Q(k) at every rung. The fixed sentence ends every tag's text."""
    if nd:
        return {"order": 1, "tag": TAG_ND, "text": f"{TAG_ND}; {TAG_SENTENCE}", "delta": None}
    h = [held_by_rung[k] for k in range(0, k_max + 1)]
    q0, qm = mean_q[0], mean_q[k_max]
    delta = None if (q0 is None or qm is None) else qm - q0
    series = ", ".join("n/a" if mean_q[k] is None else f"{mean_q[k]:.4f}" for k in range(0, k_max + 1))
    if not h[0]:
        return {"order": 2, "tag": TAG_ABSENT, "text": f"{TAG_ABSENT}; {TAG_SENTENCE}", "delta": delta}
    if not all(h):
        first_lost = next(k for k in range(0, k_max + 1) if not h[k])
        if not any(h[first_lost:]):
            tag = f"LEAD LOST BY RUNG {first_lost}"
            return {"order": 3, "tag": tag, "text": f"{tag} (Δ = {delta:.4f}; {series}); {TAG_SENTENCE}" if delta is not None else f"{tag}; {TAG_SENTENCE}", "delta": delta, "first_lost": first_lost}
        return {"order": 4, "tag": TAG_NOT_MONOTONE, "text": f"{TAG_NOT_MONOTONE} (Δ = {delta:.4f}; {series}); {TAG_SENTENCE}" if delta is not None else f"{TAG_NOT_MONOTONE}; {TAG_SENTENCE}", "delta": delta}
    assert delta is not None
    if delta <= -th.trend_delta:
        order, tag = 5, TAG_SHRINKING
    elif delta >= th.trend_delta:
        order, tag = 6, TAG_GROWING
    else:
        order, tag = 7, TAG_HELD
    return {"order": order, "tag": tag, "text": f"{tag} (Δ = {delta:.4f}; {series}); {TAG_SENTENCE}", "delta": delta}


def lead_sentence(q_end: float | None, delta_flat: float | None, delta_dense: float | None) -> str:
    """Beside the tag: |mean Q(k_max)| and each arm's delta(arm, k_max); the extra words if either delta is at least |mean Q(k_max)|."""
    if q_end is None:
        return "|mean Q(k_max)| is not determined."
    s = f"|mean Q(k_max)| = {abs(q_end):.4f}; δ(M-FLAT, k_max) = {_f(delta_flat)}; δ(D-ADAPT, k_max) = {_f(delta_dense)}."
    if any(d is not None and d >= abs(q_end) for d in (delta_flat, delta_dense)):
        s += " an arm is still improving per doubling by at least the size of the lead"
    return s


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.4f}"
