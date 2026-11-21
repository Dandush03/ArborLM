# ruff: noqa: E501
"""The registered outcome rules of ADR-0033 section 10, as pure functions, and the per-part analysis that applies them.

Every rule is written with no model in it: it takes records or numbers and returns a label. The labels are the
registered negative or blocking outcomes; where the opposite holds the label is descriptive (EVALUABLE, TEACHER AHEAD,
COMPLEMENTARY) and states something about the reference models on these items only. Nothing printed here is an
achievement and none of it says anything about ArborLM.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from studies.m0 import power as pw
from studies.m0 import stats as st
from studies.m0.scoring import chance_level

# ------------------------------------------------------------------ 10.1 REFERENCE NOT RUNNABLE LOCALLY

CAUSES = ("NEEDS REPOSITORY CODE", "PRECISION", "MEMORY", "COST")


def not_runnable_cause(flags: Mapping[str, bool]) -> str | None:
    """The first cause that applies, in the order NEEDS REPOSITORY CODE, PRECISION, MEMORY, COST (section 10.1)."""
    for c in CAUSES:
        if flags.get(c, False):
            return c
    return None


# ------------------------------------------------------------------ 10.2 NOT EVALUABLE (FLOOR OR CEILING)


def band(c: float, low: float = 0.10, high: float = 0.90) -> tuple[float, float]:
    """From c + low (1 - c) to high."""
    return c + low * (1.0 - c), high


def floor_or_ceiling(score: float, c: float, low: float = 0.10, high: float = 0.90) -> str:
    lo, hi = band(c, low, high)
    if score < lo:
        return "FLOOR"
    if score > hi:
        return "CEILING"
    return "INSIDE"


def part_not_evaluable(states: Mapping[str, str]) -> bool:
    """The evaluation part is NOT EVALUABLE (FLOOR OR CEILING) if no Tier 2 pair on it is inside the band.
    ``states`` maps each Tier 2 reference to FLOOR, CEILING, INSIDE, or NOT MEASURED (not runnable)."""
    return not any(v == "INSIDE" for v in states.values())


# ------------------------------------------------------------------ 10.3 TEACHER NOT AHEAD


def teacher_ahead(lower_bound: float) -> bool:
    """AHEAD if the one-sided lower 95 % bound of (score of T - score of S0) is above 0."""
    return lower_bound > 0.0


def domain_teacher_line(ahead_by_part: Mapping[str, Mapping[str, bool]]) -> str:
    """A domain reads TEACHER NOT AHEAD if no teacher is ahead on any of its gate-candidate parts."""
    if any(any(v.values()) for v in ahead_by_part.values()):
        return "TEACHER AHEAD ON NAMED PARTS"
    return "TEACHER NOT AHEAD"


# ------------------------------------------------------------------ 10.4 NO COMPLEMENTARITY


def complementarity(gu_lower: float, delta: float, teacher_not_runnable: bool = False) -> str:
    if teacher_not_runnable:
        return "NOT EVALUABLE (REFERENCE NOT RUNNABLE)"
    return "COMPLEMENTARY" if gu_lower > delta else "NO COMPLEMENTARITY"


def domain_complementarity_line(per_part: Mapping[str, str]) -> str:
    """COMPLEMENTARY ON EVERY PART, COMPLEMENTARY ON NAMED PARTS, or NO COMPLEMENTARITY (per delta)."""
    vals = list(per_part.values())
    if vals and all(v.startswith("NOT EVALUABLE") for v in vals):
        return "NOT EVALUABLE (REFERENCE NOT RUNNABLE)"
    comp = [p for p in sorted(per_part) if per_part[p] == "COMPLEMENTARY"]
    if len(comp) == len(vals) and vals:
        return "COMPLEMENTARY ON EVERY PART"
    if comp:
        return "COMPLEMENTARY ON NAMED PARTS: " + ", ".join(comp)
    return "NO COMPLEMENTARITY"


# ------------------------------------------------------------------ CAP flag (ADR-0032 section 4)


def cap_flag(delta: float, lower_bound: float, cap_fraction: float = 0.5) -> str:
    """CAP MET if delta <= L / 2, otherwise CAP NOT MET. A flag; it moves no margin."""
    return "CAP MET" if delta <= cap_fraction * lower_bound else "CAP NOT MET"


# ------------------------------------------------------------------ 10.5 NOT EVALUABLE (UNDERPOWERED)


def underpowered(floor_power: float, per_test_target: float, required: int | None, pool: int) -> list[str]:
    """Reasons (empty when none): the largest reachable per-test power is below the target; the required size is above the
    sealed pool; the required size is not reached on the ladder. Never dropped from the conjunction."""
    why = []
    if floor_power < per_test_target:
        why.append("largest reachable per-test power below the per-test target")
    if required is None:
        why.append("required size not reached on the ladder")
    elif required > pool:
        why.append("required size above the sealed pool")
    return why


def per_test_target(power: float, tests_total: int) -> float:
    """Boole's inequality: pi >= 1 - (1 - power) / M_e."""
    return 1.0 - (1.0 - power) / tests_total


def tests_in_conjunction(n_tier2_refs: int, n_parts: int, extra_per_part: int = 0) -> tuple[int, int]:
    """m tests per part (one per Tier 2 reference, one NO HARM, one interference, plus ``extra_per_part`` placeholders),
    M_e = m * P with P every gate-candidate part of the registered domain list. Returns (m, M_e)."""
    m = n_tier2_refs + 2 + extra_per_part
    return m, m * n_parts


# ------------------------------------------------------------------ 10.6 GATE NOT EVALUABLE LOCALLY (PROJECTED)


def projected_hours(required_by_part: Mapping[str, int | None], pool_by_part: Mapping[str, int], seconds_per_item: float, n_systems_s0_rate: int, retrieval_systems: int = 1, retrieval_factor: float = 2.0) -> float:
    """Sum over gate-candidate parts of (required size x measured seconds per item) over the systems, all at S0's rate
    except retrieval at S0's rate x retrieval_factor. A part UNDERPOWERED at delta (required None or above the pool)
    enters at its pool maximum. Returns charged hours."""
    total_items = 0
    for part, pool in pool_by_part.items():
        req = required_by_part.get(part)
        total_items += pool if (req is None or req > pool) else req
    factor = n_systems_s0_rate + retrieval_systems * retrieval_factor
    return total_items * seconds_per_item * factor / 3600.0


def gate_line(hours: float, limit_hours: float, delta: float) -> str:
    if hours > limit_hours:
        return f"GATE NOT EVALUABLE LOCALLY (PROJECTED, {delta})"
    return "GATE WITHIN THE PROJECTED LIMIT (a projection, not a decision)"


# ------------------------------------------------------------------ per-part analysis


@dataclass
class Roles:
    student: str
    teachers: tuple[str, str]
    tier2: tuple[str, ...]  # every Tier 2 reference that is a model (teachers and the sibling)
    runnable: dict[str, bool] = field(default_factory=dict)

    def is_runnable(self, name: str) -> bool:
        return self.runnable.get(name, True)


@dataclass
class PartInput:
    domain: str
    evaluation: str
    part: str
    recs: list[st.Rec]
    ks: list[int | None]  # options per item (None for open answers)
    n_clusters_sealed: int  # G_e of the sealed split
    pool: int = 20000


@dataclass
class PartOutcome:
    evaluation: str
    part: str
    domain: str
    chance: float
    scores: dict[str, st.Interval]
    floor_ceiling: dict[str, str]
    part_not_evaluable: bool
    paired_lower: dict[str, st.Interval]
    teacher_ahead: dict[str, bool]
    discordance: dict[str, st.Discordance]
    d_e: float
    d_pair: str
    union: dict[float, str]
    union_detail: Any
    cap: dict[tuple[str, float], str]
    tau: tuple[float, float, float]
    floor_power: dict[float, tuple[float, float]]  # delta -> (with the point estimate, with the upper bound)
    required: dict[float, int | None]
    required_table: dict[float, list[tuple[int, float, float]]]
    underpowered: dict[float, list[str]]
    lines: list[str] = field(default_factory=list)


def analyse_part(p: PartInput, roles: Roles, cfg: Mapping[str, Any], *, b: int, seed: int, sims: int, tests_total: int, m_tests: int) -> PartOutcome:
    """Apply sections 9.1, 9.4 and 10 to one evaluation part. ``b`` bootstrap resamples, ``sims`` simulated samples.

    ``tests_total`` is M_e, the size of the whole conjunction (Boole's bound uses it for both the size search and the floor
    check); ``m_tests`` is the per-part count and is kept for the record only (audit B1)."""
    deltas = list(cfg["stats"]["margin_grid"])
    lo, hi = cfg["bands"]["floor_ceiling_low"], cfg["bands"]["floor_ceiling_high"]
    S0 = roles.student
    run_sys = [S0] + [s for s in sorted({*roles.tier2, *roles.teachers}) if roles.is_runnable(s)]
    tab = st.Table.from_recs(p.recs, run_sys)
    c = chance_level(p.ks)
    scores = {s: st.score_interval(tab, s, b, seed, p.evaluation + p.part) for s in run_sys}
    fc: dict[str, str] = {}
    for ref in roles.tier2:
        fc[ref] = floor_or_ceiling(scores[ref].estimate, c, lo, hi) if roles.is_runnable(ref) else "NOT MEASURED"
    paired = {t: st.paired_difference(tab, t, S0, b, seed, True, p.evaluation + p.part) for t in roles.teachers if roles.is_runnable(t)}
    ahead = {t: teacher_ahead(paired[t].lo) if t in paired else False for t in roles.teachers}
    runnable_refs = [r for r in roles.tier2 if roles.is_runnable(r)]
    disc = {r: st.discordance(tab, S0, r) for r in runnable_refs}
    d_pair = max(sorted(disc), key=lambda r: disc[r].share) if disc else ""
    d_e = disc[d_pair].share if disc else float("nan")
    teachers_ok = all(roles.is_runnable(t) for t in roles.teachers)
    union: dict[float, str] = {}
    ug = None
    if teachers_ok:
        ug = st.union_gain(tab, roles.teachers[0], roles.teachers[1], b, seed, p.evaluation + p.part)
        for dl in deltas:
            union[dl] = complementarity(ug.lower.lo, dl)
    else:
        for dl in deltas:
            union[dl] = complementarity(0.0, dl, teacher_not_runnable=True)
    cap = {(t, dl): cap_flag(dl, paired[t].lo, cfg["stats"]["cap_fraction"]) for t in paired for dl in deltas}
    tau = (float("nan"),) * 3
    floor_pw: dict[float, tuple[float, float]] = {}
    req: dict[float, int | None] = {}
    tried: dict[float, list[tuple[int, float, float]]] = {}
    under: dict[float, list[str]] = {}
    if d_pair:
        by_cluster: dict[str, tuple[str, list[float]]] = {}
        for r in p.recs:
            if r.correct.get(S0) is None or r.correct.get(d_pair) is None:
                continue
            by_cluster.setdefault(r.cluster, (r.stratum, []))[1].append(float(r.correct[S0] - r.correct[d_pair]))
        clusters = [by_cluster[k] for k in sorted(by_cluster)]
        comp = pw.components(clusters)
        tau = pw.tau_interval(clusters, b, seed, p.evaluation + p.part)
        target = per_test_target(cfg["stats"]["power"], tests_total)
        for dl in deltas:
            floor_pw[dl] = (pw.cluster_floor(comp, dl, p.n_clusters_sealed), pw.cluster_floor(comp, dl, p.n_clusters_sealed, tau=tau[2]))
            req[dl], tried[dl] = pw.required_size(comp, dl, p.n_clusters_sealed, tests_total, sims, seed, cfg["stats"]["power"], tuple(cfg["stats"]["size_ladder"]), label=p.evaluation + p.part)
            under[dl] = underpowered(floor_pw[dl][0], target, req[dl], p.pool)
    out = PartOutcome(p.evaluation, p.part, p.domain, c, scores, fc, part_not_evaluable(fc), paired, ahead, disc, d_e, d_pair, union, ug, cap, tau, floor_pw, req, tried, under)
    out.lines = outcome_lines(out, roles, deltas)
    return out


def outcome_lines(o: PartOutcome, roles: Roles, deltas: Sequence[float]) -> list[str]:
    tag = f"{o.evaluation} part {o.part}"
    ln = []
    for ref, state in o.floor_ceiling.items():
        ln.append(f"{tag}: {ref}: " + ("NOT EVALUABLE (FLOOR)" if state == "FLOOR" else "NOT EVALUABLE (CEILING)" if state == "CEILING" else "NOT MEASURED (REFERENCE NOT RUNNABLE LOCALLY)" if state == "NOT MEASURED" else "inside the band (EVALUABLE)"))
    if o.part_not_evaluable:
        ln.append(f"{tag}: NOT EVALUABLE (FLOOR OR CEILING): no Tier 2 pair is inside the band")
    for t, a in o.teacher_ahead.items():
        ln.append(f"{tag}: {t}: " + ("TEACHER AHEAD (descriptive: on these items only)" if a else f"TEACHER NOT AHEAD ({t}, {o.evaluation})"))
    for dl in deltas:
        u = o.union[dl]
        ln.append(f"{tag}: {u} ({o.evaluation}, {dl})" if u == "NO COMPLEMENTARITY" else f"{tag}: delta {dl}: {u}")
        if dl in o.underpowered and o.underpowered[dl]:
            ln.append(f"{tag}: NOT EVALUABLE (UNDERPOWERED, {o.evaluation}, {dl}): " + "; ".join(o.underpowered[dl]))
    return ln


def finite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))
