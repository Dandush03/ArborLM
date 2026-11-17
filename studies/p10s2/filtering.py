# ruff: noqa: E501
"""Teacher interface, acceptance filter, filter fitting and the qualification gate (ADR-0022 sections 4.3, 5.3).

Filter. An output is accepted if (a) its length-normalized beam log-probability is >= tau; (b) the ratio of its word count to the source's lies in [rho1, rho2]; (c) it differs from the source
after normalization. (tau, rho1, rho2) is chosen on Q_fit from the grid as the most permissive setting (largest accepted share) whose 95% Wilson lower bound of precision is >= 0.90, precision
being the share of accepted outputs with chrF >= 0.60 against the best reference; among settings with the same accepted share the larger tau, then the narrower length-ratio range. The chosen
setting must then show a point precision >= 0.90 on Q_check with at least ``check_min_accepted`` accepted items, otherwise the teacher is not qualified.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from . import core
from .data import Item, TrainItem
from .text import chrf_item, mean, normalize, wilson


class Teacher(Protocol):
    """What the data-generation step needs from a teacher: sequence-level outputs with a length-normalized beam score (the real ones are Marian models run only there)."""

    name: str
    revision: str

    def translate(self, sources: Sequence[str]) -> list[tuple[str, float]]: ...


class TokenizerRecording(Protocol):
    """Optional: a teacher that can write the tokenizer record of section 4.1 (the real Marian teachers; the synthetic stand-ins have none)."""

    def tokenizer_record(self, sentences: Sequence[str]) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class Output:
    source: str
    text: str
    score: float  # the library's sequence score with length penalty 1, the end-of-sequence token counted: the sum of the token log-probabilities of the returned hypothesis divided by its token count (ruling on A-M7)


@dataclass(frozen=True)
class FilterSetting:
    tau: float
    rho1: float
    rho2: float

    def to_json(self) -> dict[str, float]:
        return {"tau": self.tau, "rho1": self.rho1, "rho2": self.rho2}


def run_teacher(teacher: Teacher, sources: Sequence[str]) -> list[Output]:
    return [Output(s, t, sc) for s, (t, sc) in zip(sources, teacher.translate(sources), strict=True)]


def accepts(o: Output, f: FilterSetting) -> bool:
    ws, wo = len(normalize(o.source).split()), len(normalize(o.text).split())
    if ws == 0 or not math.isfinite(o.score) or "\n" in o.text or "\n" in o.source:  # an empty source, a non-finite score (NaN or +-inf) or a newline in the source or output is never accepted
        return False
    ratio = wo / ws
    return o.score >= f.tau and f.rho1 <= ratio <= f.rho2 and normalize(o.text) != normalize(o.source)


def settings_grid() -> list[FilterSetting]:
    flt = core.CFG["filter"]
    return [FilterSetting(round(t, 2), lo, hi) for t in flt["tau_grid"] for lo, hi in flt["ratio_ranges"]]


@dataclass(frozen=True)
class FilterFit:
    setting: FilterSetting | None
    accepted: int
    accepted_share: float
    precision: float
    wilson: tuple[float, float]
    candidates: int

    def to_json(self) -> dict[str, Any]:
        return {"setting": None if self.setting is None else self.setting.to_json(), "accepted": self.accepted, "accepted_share": self.accepted_share, "precision": self.precision, "wilson": list(self.wilson), "candidates": self.candidates}


def precision_of(outputs: Sequence[Output], refs: Sequence[Sequence[str]], f: FilterSetting) -> tuple[int, int, float]:
    """(accepted, correct, point precision) where correct means chrF >= 0.60 against the best reference."""
    thr = core.CFG["filter"]["chrf_correct"]
    acc = [(o, r) for o, r in zip(outputs, refs, strict=True) if accepts(o, f)]
    ok = sum(1 for o, r in acc if chrf_item(o.text, r) >= thr)
    return len(acc), ok, (ok / len(acc) if acc else float("nan"))


def fit_filter(outputs: Sequence[Output], refs: Sequence[Sequence[str]]) -> FilterFit:
    """Selection on Q_fit by the 95% Wilson lower bound. Ties in accepted share: larger tau, then the narrower range (J12). Returns a fit with ``setting`` None if no setting reaches the bound."""
    lb_min = core.CFG["filter"]["wilson_lower_bound"]
    best: tuple[tuple[float, float, float], FilterSetting, int, int] | None = None
    candidates = 0
    for f in settings_grid():
        n, ok, _ = precision_of(outputs, refs, f)
        if n == 0:
            continue
        lo, _hi = wilson(ok, n)
        if lo < lb_min:
            continue
        candidates += 1
        key = (n / len(outputs), f.tau, -(f.rho2 - f.rho1))  # more accepted, then larger tau, then narrower range
        if best is None or key > best[0]:
            best = (key, f, n, ok)
    if best is None:
        return FilterFit(None, 0, 0.0, float("nan"), (0.0, 1.0), 0)
    _, f, n, ok = best
    return FilterFit(f, n, n / len(outputs), ok / n, wilson(ok, n), candidates)


def check_filter(f: FilterSetting, outputs: Sequence[Output], refs: Sequence[Sequence[str]], min_accepted: int) -> dict[str, Any]:
    """Point precision >= 0.90 on Q_check with at least ``min_accepted`` accepted items."""
    n, ok, p = precision_of(outputs, refs, f)
    need = core.CFG["filter"]["check_precision"]
    return {"accepted": n, "correct": ok, "precision": p, "wilson": list(wilson(ok, n)), "ok": n >= min_accepted and n > 0 and p >= need}


def accepted_pool(outputs: Sequence[Output], items: Sequence[Item], f: FilterSetting, eval_refs_norm: set[str]) -> tuple[list[TrainItem], int]:
    """Accepted outputs as training items; an output that, normalized, equals a normalized reference of any evaluation panel is dropped and counted."""
    out: list[TrainItem] = []
    dropped = 0
    for o, it in zip(outputs, items, strict=True):
        if not accepts(o, f):
            continue
        if normalize(o.text) in eval_refs_norm:
            dropped += 1
            continue
        out.append(TrainItem(it.key, it.en, o.text, it.group))
    return out, dropped


# --- qualification (section 4.3) -------------------------------------------------------------------------------------------------------------
def qualify(
    teacher_scores: Mapping[str, Mapping[str, float]],
    student_scores: Mapping[str, float],
    fits: Mapping[str, FilterFit],
    checks: Mapping[str, Mapping[str, Any]],
    accepted_counts: Mapping[str, int],
    accepted_min: int,
) -> dict[str, Any]:
    """On panel Q with s the mean sentence chrF against the best reference:
    1. each teacher on its own capability: s >= 0.55;
    2. margin: own score minus the larger of the other teacher's score and the untrained student's score on that capability >= 0.30;
    3. the filter reaches the required precision (fit and check) and the accepted pool is at least 8,000 items per capability.
    ``teacher_scores[teacher][capability]``; teacher A is the German teacher, B the French one."""
    cfg = core.CFG["teachers"]
    detail: dict[str, Any] = {}
    failed: list[str] = []
    for c in core.TASKS:
        o = other_task(c)
        own = teacher_scores[c][c]
        margin = own - max(teacher_scores[o][c], student_scores[c])
        d = {"own": own, "other_teacher": teacher_scores[o][c], "student": student_scores[c], "margin": margin, "filter_fit": fits[c].to_json(), "filter_check": dict(checks[c]), "accepted": accepted_counts[c]}
        detail[c] = d
        if not own >= cfg["own_score_min"]:
            failed.append(f"{c}: own score {own:.3f} below {cfg['own_score_min']}")
        if not margin >= cfg["margin_min"]:
            failed.append(f"{c}: margin {margin:.3f} below {cfg['margin_min']}")
        if fits[c].setting is None or not checks[c]["ok"]:
            failed.append(f"{c}: the acceptance filter does not reach the required precision")
        if accepted_counts[c] < accepted_min:
            failed.append(f"{c}: accepted pool {accepted_counts[c]} below {accepted_min}")
    return {"ok": not failed, "failed": failed, "detail": detail, "outcome": None if not failed else "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"}


def other_task(t: str) -> str:
    return core.other_task(t)


def mean_teacher_score(outputs: Sequence[Output], refs: Sequence[Sequence[str]]) -> float:
    return mean([chrf_item(o.text, r) for o, r in zip(outputs, refs, strict=True)])
