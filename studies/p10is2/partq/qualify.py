# ruff: noqa: E501
"""Part Q quality criteria Q1-Q4 and the filter fit (ADR-0025 sections 4.2, 4.3; ruling G15). Pure functions over teacher outputs and per-item records; no model, no corpus.

Thresholds and the grid are read from ``configs/p10is2_partq.toml`` only. The accept function, the output record and the chrF-norm are P10-S2's (``studies/p10s2/filtering.py:56-61`` and ``text.py``; section
4.2 names them), re-used unedited: the filter's length ratio counts whitespace-separated words after normalization, a non-finite score or a newline is never accepted.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from studies.p10s2.filtering import FilterSetting, Output, accepts
from studies.p10s2.text import chrf_item

CAPABILITIES = ("A", "B")


def wilson(successes: int, n: int, z: float) -> tuple[float, float]:
    """Wilson score interval (lower, upper); (0, 1) for n = 0. Own implementation: z is this study's config value."""
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def settings_grid(cfg: Mapping[str, Any]) -> list[FilterSetting]:
    q = cfg["quality"]
    return [FilterSetting(round(float(t), 2), float(lo), float(hi)) for t in q["tau_grid"] for lo, hi in q["ratio_ranges"]]


def item_scores(outputs: Sequence[Output], refs: Sequence[Sequence[str]]) -> list[float]:
    """chrF-norm of each output against its best reference (stored per item on Q_fit and Q_check)."""
    return [chrf_item(o.text, r) for o, r in zip(outputs, refs, strict=True)]


def grid_table(outputs: Sequence[Output], scores: Sequence[float], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The full grid on Q_fit: for each setting the accepted count and share, the correct count (chrF >= 0.60), point precision and the 95% Wilson lower bound. Stored and hashed (rule 8)."""
    cut, z = float(cfg["quality"]["chrf_correct"]), float(cfg["quality"]["wilson_z"])
    rows: list[dict[str, Any]] = []
    for f in settings_grid(cfg):
        acc = [s for o, s in zip(outputs, scores, strict=True) if accepts(o, f)]
        ok = sum(1 for s in acc if s >= cut)
        lo, hi = wilson(ok, len(acc), z)
        rows.append({"tau": f.tau, "rho1": f.rho1, "rho2": f.rho2, "accepted": len(acc), "accepted_share": len(acc) / len(outputs) if outputs else 0.0, "correct": ok, "precision": ok / len(acc) if acc else None, "wilson_lower": lo, "wilson_upper": hi})
    return rows


@dataclass(frozen=True)
class Q3Result:
    setting: FilterSetting | None
    accepted: int
    correct: int
    precision: float | None
    wilson: tuple[float, float]
    candidates: int

    def to_json(self) -> dict[str, Any]:
        return {"setting": None if self.setting is None else self.setting.to_json(), "accepted": self.accepted, "correct": self.correct, "precision": self.precision, "wilson": list(self.wilson), "candidates": self.candidates}


def select_filter(table: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> Q3Result:
    """Q3. Among the settings whose Wilson lower bound is >= 0.90, the most permissive (the largest accepted share); ties: the larger tau, then the narrower range. A setting with no accepted item is not a
    candidate. ``setting`` is None if none qualifies: Q3 fails."""
    lb_min = float(cfg["quality"]["wilson_lower_bound"])
    best: tuple[tuple[float, float, float], Mapping[str, Any]] | None = None
    candidates = 0
    for r in table:
        if r["accepted"] == 0 or r["wilson_lower"] < lb_min:
            continue
        candidates += 1
        key = (float(r["accepted_share"]), float(r["tau"]), -(float(r["rho2"]) - float(r["rho1"])))
        if best is None or key > best[0]:
            best = (key, r)
    if best is None:
        return Q3Result(None, 0, 0, None, (0.0, 1.0), 0)
    r = best[1]
    return Q3Result(FilterSetting(float(r["tau"]), float(r["rho1"]), float(r["rho2"])), int(r["accepted"]), int(r["correct"]), float(r["precision"]), (float(r["wilson_lower"]), float(r["wilson_upper"])), candidates)


def q1(own_scores: Mapping[str, float], cfg: Mapping[str, Any]) -> dict[str, bool]:
    """Q1: each teacher's mean sentence chrF-norm on its own capability, on Q_fit, >= 0.55."""
    return {c: bool(own_scores[c] >= float(cfg["quality"]["q1_own_score_min"])) for c in CAPABILITIES}


def q2(teacher_scores: Mapping[str, Mapping[str, float]], student_scores: Mapping[str, float], cfg: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Q2: Q1's score minus the larger of the other teacher's and the untrained student's score on that capability >= 0.30. ``teacher_scores[teacher][capability]``; teacher A is the German one."""
    out: dict[str, dict[str, Any]] = {}
    for c in CAPABILITIES:
        o = "B" if c == "A" else "A"
        own, other, stud = teacher_scores[c][c], teacher_scores[o][c], student_scores[c]
        margin = own - max(other, stud)
        out[c] = {"own": own, "other_teacher": other, "student": stud, "margin": margin, "pass": bool(margin >= float(cfg["quality"]["q2_margin_min"]))}
    return out


def precision_on_check(outputs: Sequence[Output], scores: Sequence[float], f: FilterSetting, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Q4: point precision of the fixed setting on every accepted item of every drawn Q_check block, read on at least 150 accepted items (``read_ok``), precision >= 0.90 (``pass``). Computed once."""
    cut = float(cfg["quality"]["chrf_correct"])
    acc = [s for o, s in zip(outputs, scores, strict=True) if accepts(o, f)]
    ok = sum(1 for s in acc if s >= cut)
    p = ok / len(acc) if acc else None
    n_min = int(cfg["quality"]["q4_min_accepted"])
    z = float(cfg["quality"]["wilson_z"])
    return {"accepted": len(acc), "correct": ok, "precision": p, "wilson": list(wilson(ok, len(acc), z)), "read_ok": len(acc) >= n_min, "pass": bool(len(acc) >= n_min and p is not None and p >= float(cfg["quality"]["q4_precision_min"]))}


def wilson_error_allowance(n_accepted: int, z: float, lower_bound: float) -> int | None:
    """The largest number of wrong items among ``n_accepted`` that still gives a Wilson lower bound >= ``lower_bound`` (None if even zero errors fail). A reading aid for section 4.2's table."""
    best = None
    for errors in range(n_accepted + 1):
        if wilson(n_accepted - errors, n_accepted, z)[0] >= lower_bound:
            best = errors
        else:
            break
    return best
