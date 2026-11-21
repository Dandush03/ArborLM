# ruff: noqa: E501
"""M0 stage I0-a: the registered outcome rules of ADR-0033 section 10 on a synthetic registry with a known answer.
Self-checked only. Nothing here is a result."""

from __future__ import annotations

import random

import pytest

from studies.m0 import config as cfgmod
from studies.m0 import outcomes as oc
from studies.m0 import stats as st

CFG = cfgmod.load()


def test_not_runnable_precedence() -> None:
    assert oc.not_runnable_cause({"COST": True, "MEMORY": True}) == "MEMORY"
    assert oc.not_runnable_cause({"COST": True, "PRECISION": True, "MEMORY": True, "NEEDS REPOSITORY CODE": True}) == "NEEDS REPOSITORY CODE"
    assert oc.not_runnable_cause({"PRECISION": True, "COST": True}) == "PRECISION"
    assert oc.not_runnable_cause({}) is None


def test_band_and_floor_ceiling_edges() -> None:
    lo, hi = oc.band(0.25)
    assert lo == pytest.approx(0.325) and hi == 0.90
    assert oc.band(0.0) == (0.10, 0.90)
    assert oc.floor_or_ceiling(0.30, 0.25) == "FLOOR"
    assert oc.floor_or_ceiling(0.325, 0.25) == "INSIDE"  # the edge itself is inside
    assert oc.floor_or_ceiling(0.90, 0.25) == "INSIDE"
    assert oc.floor_or_ceiling(0.9001, 0.25) == "CEILING"
    assert oc.part_not_evaluable({"a": "FLOOR", "b": "CEILING"})
    assert not oc.part_not_evaluable({"a": "FLOOR", "b": "INSIDE"})
    assert oc.part_not_evaluable({"a": "NOT MEASURED"})


def test_teacher_ahead_complementarity_cap_and_domain_lines() -> None:
    assert oc.teacher_ahead(0.001) and not oc.teacher_ahead(0.0) and not oc.teacher_ahead(-0.2)
    assert oc.domain_teacher_line({"p1": {"T1": False, "T2": False}, "p2": {"T1": False, "T2": False}}) == "TEACHER NOT AHEAD"
    assert oc.domain_teacher_line({"p1": {"T1": False, "T2": True}}).startswith("TEACHER AHEAD")
    assert oc.complementarity(0.031, 0.03) == "COMPLEMENTARY" and oc.complementarity(0.03, 0.03) == "NO COMPLEMENTARITY"
    assert oc.complementarity(0.5, 0.03, teacher_not_runnable=True).startswith("NOT EVALUABLE")
    assert oc.domain_complementarity_line({"a": "COMPLEMENTARY", "b": "COMPLEMENTARY"}) == "COMPLEMENTARY ON EVERY PART"
    assert oc.domain_complementarity_line({"a": "COMPLEMENTARY", "b": "NO COMPLEMENTARITY"}) == "COMPLEMENTARY ON NAMED PARTS: a"
    assert oc.domain_complementarity_line({"a": "NO COMPLEMENTARITY"}) == "NO COMPLEMENTARITY"
    assert oc.domain_complementarity_line({"a": "NOT EVALUABLE (REFERENCE NOT RUNNABLE)"}).startswith("NOT EVALUABLE")
    assert oc.cap_flag(0.03, 0.06) == "CAP MET" and oc.cap_flag(0.031, 0.06) == "CAP NOT MET"


def test_underpowered_conjunction_and_projection_rules() -> None:
    assert oc.underpowered(0.99, 0.996, 4000, 20000)
    assert oc.underpowered(0.9999, 0.996, 24000, 20000) == ["required size above the sealed pool"]
    assert oc.underpowered(0.9999, 0.996, None, 20000) == ["required size not reached on the ladder"]
    assert oc.underpowered(0.9999, 0.996, 4000, 20000) == []
    assert oc.tests_in_conjunction(3, 11) == (5, 55)
    assert oc.tests_in_conjunction(3, 11, extra_per_part=2) == (7, 77)
    # parts that are UNDERPOWERED enter at their pool maximum
    h = oc.projected_hours({"p1": 1000, "p2": None, "p3": 30000}, {"p1": 20000, "p2": 20000, "p3": 20000}, 10.0, 9, 1, 2.0)
    assert h == pytest.approx((1000 + 20000 + 20000) * 10.0 * 11 / 3600)
    assert oc.gate_line(337, 336, 0.03).startswith("GATE NOT EVALUABLE LOCALLY (PROJECTED")
    assert not oc.gate_line(336, 336, 0.03).startswith("GATE NOT EVALUABLE")


# ---------------------------------------------------------------- synthetic registry with a known answer


def _registry(seed: int = 1, n_clusters: int = 40, per: int = 25, swap: tuple[str, str] | None = None) -> oc.PartInput:
    """Designed scores: S0 0.45, Qwen teacher 0.75, GLM teacher 0.55, sibling 0.60; teachers' errors independent."""
    r = random.Random(seed)
    p = {"S0": 0.45, "TQ": 0.75, "TG": 0.55, "SIB": 0.60}
    recs = []
    for c in range(n_clusters):
        for i in range(per):
            recs.append(st.Rec(f"{c}-{i}", f"c{c:03d}", f"f{c % 4}", {k: int(r.random() < v) for k, v in p.items()}))
    if swap:
        a, b = swap
        recs = [st.Rec(x.item_id, x.cluster, x.stratum, {**x.correct, a: x.correct[b], b: x.correct[a]}) for x in recs]
    return oc.PartInput("reasoning", "R1", "A", recs, [4] * len(recs), n_clusters_sealed=40, pool=20000)


ROLES = oc.Roles("S0", ("TQ", "TG"), ("TQ", "TG", "SIB"))


def _run(p: oc.PartInput, roles: oc.Roles = ROLES) -> oc.PartOutcome:
    return oc.analyse_part(p, roles, CFG, b=400, seed=400008, sims=100, tests_total=55, m_tests=5)


def test_known_answer_registry() -> None:
    o = _run(_registry())
    assert o.chance == 0.25
    assert o.floor_ceiling == {"TQ": "INSIDE", "TG": "INSIDE", "SIB": "INSIDE"} and not o.part_not_evaluable
    assert o.teacher_ahead == {"TQ": True, "TG": True}  # 0.75 and 0.55 against 0.45 with 1,000 items in 40 clusters
    assert o.d_pair in ("TQ", "TG", "SIB") and 0 < o.d_e < 1
    assert o.union[0.02] == "COMPLEMENTARY"  # independent teachers at 0.75 and 0.55: union ~0.89 against 0.75
    assert o.cap[("TQ", 0.05)] == "CAP MET" and o.cap[("TG", 0.05)] in ("CAP MET", "CAP NOT MET")
    assert all(0 <= v[0] <= 1 for v in o.floor_power.values())
    assert any("TEACHER AHEAD" in line for line in o.lines)


def test_swapped_records_are_detected_by_the_known_answer_checks() -> None:
    base = _run(_registry())
    swapped = _run(_registry(swap=("S0", "TQ")))  # the student's and the Qwen teacher's records are exchanged
    assert swapped.teacher_ahead["TQ"] is False and base.teacher_ahead["TQ"] is True
    assert swapped.lines != base.lines


def test_teacher_not_runnable_gives_not_evaluable_never_no_complementarity() -> None:
    roles = oc.Roles("S0", ("TQ", "TG"), ("TQ", "TG", "SIB"), runnable={"TG": False})
    p = _registry()
    recs = [st.Rec(x.item_id, x.cluster, x.stratum, {k: v for k, v in x.correct.items() if k != "TG"}) for x in p.recs]
    o = _run(oc.PartInput(p.domain, p.evaluation, p.part, recs, p.ks, p.n_clusters_sealed), roles)
    assert o.floor_ceiling["TG"] == "NOT MEASURED"
    assert all(v.startswith("NOT EVALUABLE") for v in o.union.values())
    assert not o.teacher_ahead["TG"]


def test_floor_part_is_not_evaluable_and_teacher_not_ahead_when_equal() -> None:
    r = random.Random(9)
    recs = [st.Rec(f"{c}-{i}", f"c{c}", f"f{c % 2}", {"S0": int(r.random() < 0.2), "TQ": int(r.random() < 0.2), "TG": int(r.random() < 0.2), "SIB": int(r.random() < 0.2)}) for c in range(30) for i in range(20)]
    o = _run(oc.PartInput("reasoning", "R2", "B", recs, [None] * len(recs), 30))
    assert o.chance == 0.0 and all(v == "INSIDE" for v in o.floor_ceiling.values())  # 0.2 is inside the open-answer band
    recs2 = [st.Rec(x.item_id, x.cluster, x.stratum, {k: int(r.random() < 0.05) for k in x.correct}) for x in recs]
    o2 = _run(oc.PartInput("reasoning", "R2", "B", recs2, [None] * len(recs2), 30))
    assert o2.part_not_evaluable and not any(o2.teacher_ahead.values())
    assert any("NOT EVALUABLE (FLOOR OR CEILING)" in line for line in o2.lines)
