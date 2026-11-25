# ruff: noqa: E501
"""The arithmetic and the fixed wording of ADR-0035 sections 6 and 7, and the label lines. Everything here is descriptive: none of it is a label."""

import math
from collections.abc import Sequence
from typing import Any

from studies.p10is2.common.core import ORACLE_LINE

POSTHOC = "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL"
CUTOFF = 2 / 3
CELLS_NEEDED = 5


def share(term: float, total: float | None) -> float | None:
    """term / T; None where T is not positive (the ADR's shares are defined for a loss; a cell without one is printed as undefined and never counts toward a word)."""
    if total is None or not (total > 0) or term is None:
        return None
    return term / total


def decompose(s: dict[str, float], registered_f: float | None = None) -> dict[str, Any]:
    """Section 6, first capability, final store. ``s`` holds the mean chrF-norm on E_first of b1, d1, e1, a and g1. One path: (i) + (ii) + (iii) = T up to float rounding; the values-first order and the interaction."""
    t = s["b1"] - s["a"]
    i, ii, iii = s["b1"] - s["d1"], s["d1"] - s["e1"], s["e1"] - s["a"]
    vf_values, vf_comp = s["b1"] - s["g1"], s["g1"] - s["a"]
    return {
        "T": t, "i": i, "ii": ii, "iii": iii, "residual": None if registered_f is None else registered_f - t,
        "values_first_values": vf_values, "values_first_competition": vf_comp, "interaction": iii - vf_values,
        "shares": {"i": share(i, t), "ii": share(ii, t), "iii": share(iii, t), "competition_path": share(i + ii, t), "values_path": share(iii, t),
                   "competition_values_first": share(vf_comp, t), "values_values_first": share(vf_values, t)},
    }  # fmt: skip


def decompose_append(s_m1: float, s_d1_append: float, s_a_append: float) -> dict[str, Any]:
    """Section 6, at the append point: (i) = s[M1] - s[d(1) at append]; (ii) = s[d(1) at append] - s[a at append]; (iii) is zero by identity."""
    t = s_m1 - s_a_append
    return {"T": t, "i": s_m1 - s_d1_append, "ii": s_d1_append - s_a_append, "iii": 0.0, "shares": {"i": share(s_m1 - s_d1_append, t), "ii": share(s_d1_append - s_a_append, t)}}


def summary_word(competition: Sequence[float | None], values: Sequence[float | None]) -> str:
    """COMPETITION-LARGER if the competition share is >= 2/3 in at least five of six cells; VALUES-LARGER if the values share is; otherwise MIXED."""
    if sum(1 for x in competition if x is not None and x >= CUTOFF) >= CELLS_NEEDED:
        return "COMPETITION-LARGER"
    if sum(1 for x in values if x is not None and x >= CUTOFF) >= CELLS_NEEDED:
        return "VALUES-LARGER"
    return "MIXED"


def final_wording(path: str, values_first: str, interactions: Sequence[float], totals: Sequence[float]) -> str:
    """The path-order word; ORDER-DEPENDENT is added if |interaction| >= T / 3 in any cell or if the two orders give different words."""
    large = any(t is not None and t > 0 and abs(x) >= t / 3 for x, t in zip(interactions, totals, strict=True))
    return f"{path}; ORDER-DEPENDENT" if (large or path != values_first) else path


def counterfactual_ret(forgetting: float | None, rho: float | None, evaluable: bool, f_max: float, rho_min: float) -> str:
    """ADR-0025's RET arithmetic (F <= f_max and rho >= rho_min, unchanged) applied to a counterfactual read. It is not RET."""
    if not evaluable or forgetting is None or rho is None:
        return "NOT EVALUABLE"
    return "HOLDS" if (forgetting <= f_max and rho >= rho_min) else "DOES NOT HOLD"


def paired_contrast(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]:
    """Mean of the per-item differences x - y and its standard error sd / sqrt(n), sd the sample standard deviation (n - 1). No resampling."""
    d = [a - b for a, b in zip(x, y, strict=True)]
    n = len(d)
    m = sum(d) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in d) / (n - 1)) if n > 1 else float("nan")
    return {"mean": m, "se": sd / math.sqrt(n) if n > 1 else float("nan"), "n": n}


def block(title: str, lines: Sequence[str]) -> str:
    """A report block: Part T's oracle line, the post-hoc line, then the title and the lines."""
    return "\n".join([ORACLE_LINE, POSTHOC, title, *lines])


def require_labelled(text: str) -> str:
    """Every blank-line-separated block of a report begins with the oracle line and the post-hoc line."""
    for b in (b for b in text.split("\n\n") if b.strip()):
        ls = b.splitlines()
        if len(ls) < 2 or ls[0] != ORACLE_LINE or ls[1] != POSTHOC:
            raise ValueError("a report block lacks the oracle line and the post-hoc line")
    return text
