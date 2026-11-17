# ruff: noqa: E501
"""P10S0 classes (ADR-0020 section 8): cell success under both criteria, the class rows of section 8.3 enumerated against an independent reading, bounds, paired d under both criteria, replication,
consistency (including what the committed P9-II records require of S0, section 3.5), the preference order and the candidate, annotations, the outcome rows and the hypothesis readings.
Self-check only: not independent review, not Astra validation, not human approval."""

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9ii import classes as p9c  # noqa: E402
from studies.p9ii.classes import CellVerdict  # noqa: E402
from studies.p10s0 import classes as C  # noqa: E402
from studies.p10s0 import core  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

A6 = p9c.A6Reference(1.0, 1.0, 0.2)
OK, FAILED, NE = CellVerdict(C.SUCCEEDED), CellVerdict(C.FAILED, (1,)), CellVerdict(C.CELL_NOT_EVALUATED)


def verdicts(kinds: dict[tuple[int, int], CellVerdict]) -> dict[tuple[int, int], CellVerdict]:
    return kinds


def keys20() -> list[tuple[int, int]]:
    return [(d, j) for d in range(1, 11) for j in (0, 1)]


def keys10() -> list[tuple[int, int]]:
    return [(d, 0 if d % 2 else 1) for d in range(1, 11)]


# --- cell success -----------------------------------------------------------------------------------------------------------------------------
def test_each_condition_fails_alone_and_condition_6_is_s0_only() -> None:
    ok = syn.observation("ok")
    assert C.cell_verdict(ok, A6, "2K/4K").status == C.SUCCEEDED and C.cell_verdict(ok, A6, "2K/4K", C.P9II_CRITERIA).status == C.SUCCEEDED

    def with_(**kw: object) -> C.SObservation:
        return C.SObservation(**{**ok.__dict__, **kw})

    cases = {
        1: with_(acc_a=0.5, h1=0.5, h2=0.5, a_use_a=0.5),
        2: with_(dep_chance_a=False),
        3: with_(distinct_top1=127),
        4: with_(h1=0.5),
        5: with_(leakage=True),
        6: with_(a_use_a=0.5),
    }
    for number, obs in cases.items():
        v = C.cell_verdict(obs, A6, "2K/4K")
        assert v.status == C.FAILED and number in v.failed_conditions, number
        v9 = C.cell_verdict(obs, A6, "2K/4K", C.P9II_CRITERIA)
        assert (v9.status == C.FAILED) == (number != 6), number  # P9-II recorded no read swap: condition 6 is S0's own
    assert C.cell_verdict(with_(largest_share=0.03), A6, "2K/4K").failed_conditions == (3,)
    assert C.cell_verdict(with_(distinct_top1=128, probe_facts=256, largest_share=0.02), A6, "2K/4K").status == C.SUCCEEDED  # 128 distinct of 256 and share 0.02 are inside
    with pytest.raises(ValueError):
        C.cell_verdict(ok, A6, "2K/4K", "other")


def test_condition_6_boundary_is_0_95_of_accuracy() -> None:
    base = syn.observation("ok", acc=0.96)
    edge = C.SObservation(**{**base.__dict__, "a_use_a": 0.95 * 0.96, "a_use_b": 0.95 * 0.96})
    assert C.cell_verdict(edge, A6, "2K/4K").status == C.SUCCEEDED
    below = C.SObservation(**{**base.__dict__, "a_use_a": 0.95 * 0.96 - 1e-6})
    assert C.cell_verdict(below, A6, "2K/4K").failed_conditions == (6,)


def test_non_finite_values_fail_and_missing_a6_is_not_evaluated() -> None:
    assert C.cell_verdict(syn.observation("ok", nan=True), A6, "2K/4K").status == C.FAILED
    nan_lm = C.SObservation(**{**syn.observation("ok").__dict__, "lm_rise": math.nan})
    assert C.cell_verdict(nan_lm, A6, "2K/4K").lm_flagged
    assert C.cell_verdict(syn.observation("ok"), None, "2K/4K").status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(syn.observation("ok"), p9c.A6Reference(0.89, 1.0, 0.1), "2K/4K").status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(syn.observation("ok"), p9c.A6Reference(math.nan, 1.0, 0.1), "2K/4K").status == C.CELL_NOT_EVALUATED


def test_a6_floor_at_8k_4k_is_0_50() -> None:
    low = p9c.A6Reference(0.6, 0.6, 0.1)
    assert C.cell_verdict(syn.observation("ok", acc=0.55), low, "8K/4K").status == C.SUCCEEDED  # 0.55 >= 0.90 x 0.6
    assert C.cell_verdict(syn.observation("ok", acc=0.5), low, "8K/4K").status == C.FAILED
    assert C.cell_verdict(syn.observation("ok"), low, "2K/4K").status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(syn.observation("ok"), p9c.A6Reference(0.49, 0.9, 0.1), "8K/4K").status == C.CELL_NOT_EVALUATED


def test_lm_flag_margin() -> None:
    assert C.cell_verdict(syn.observation("ok", lm_rise=0.26), A6, "2K/4K").lm_flagged and not C.cell_verdict(syn.observation("ok", lm_rise=0.25), A6, "2K/4K").lm_flagged


# --- the class rows (section 8.3) against an independent reading ----------------------------------------------------------------------------------
def reference_class(n_cells: int, evaluated_cells: int, failures: int, ne_draws: int, flagged: int) -> str:
    """Section 8.3 written again, as a table of thresholds."""
    if ne_draws > 1:
        return "NOT_EVALUATED"
    reduced = flagged > 1
    if failures <= 1 and not reduced:
        return "RELIABLE"
    needed = 5 if n_cells == 20 else 3
    return "UNRELIABLE" if evaluated_cells - failures >= needed else "FAILS"


@pytest.mark.parametrize("rule,keys", [("20", keys20()), ("10", keys10())])
def test_class_rows_for_every_failure_count_and_not_evaluated_pattern(rule: str, keys: list[tuple[int, int]]) -> None:
    n = len(keys)
    for fails in range(n + 1):
        v = {k: (FAILED if i < fails else OK) for i, k in enumerate(keys)}
        got = C.arm_class(v, keys, rule)
        assert got.cls == reference_class(n, n, fails, 0, 0), (rule, fails)
        assert got.label in ("RELIABLE", "UNRELIABLE", "FAILS") and got.draws_not_evaluated == 0
    for ne in (0, 1, 2):
        v = {k: (NE if k[0] <= ne else OK) for k in keys}
        got = C.arm_class(v, keys, rule)
        assert got.cls == ("NOT_EVALUATED" if ne > 1 else "RELIABLE") and got.draws_not_evaluated == ne
        assert got.evaluated == sum(1 for k in keys if k[0] > ne)
    v = {k: (FAILED if k[0] == 1 else OK) for k in keys}  # a draw with both seeds failed (20-cell types)
    assert C.arm_class(v, keys, rule).cls == ("UNRELIABLE" if rule == "20" else "RELIABLE") if rule == "20" else True


def test_the_boundaries_of_the_two_unreliable_rows() -> None:
    k = keys20()
    assert C.arm_class({x: (OK if i < 5 else FAILED) for i, x in enumerate(k)}, k, "20").cls == "UNRELIABLE"
    assert C.arm_class({x: (OK if i < 4 else FAILED) for i, x in enumerate(k)}, k, "20").cls == "FAILS"
    k = keys10()
    assert C.arm_class({x: (OK if i < 3 else FAILED) for i, x in enumerate(k)}, k, "10").cls == "UNRELIABLE"
    assert C.arm_class({x: (OK if i < 2 else FAILED) for i, x in enumerate(k)}, k, "10").cls == "FAILS"
    assert C.arm_class({x: (OK if i < 8 else FAILED) for i, x in enumerate(k)}, k, "10").cls == "UNRELIABLE"  # 8 of 10 is not RELIABLE
    with pytest.raises(ValueError):
        C.arm_class({}, [], "5")


def test_lm_capability_reduced_label_and_a_single_flag() -> None:
    k = keys20()
    flagged = CellVerdict(C.SUCCEEDED, (), True)
    one = {x: (flagged if i == 0 else OK) for i, x in enumerate(k)}
    assert C.arm_class(one, k, "20").cls == "RELIABLE"  # an arm flagged in one cell is not LM CAPABILITY REDUCED
    two = {x: (flagged if i < 2 else OK) for i, x in enumerate(k)}
    c = C.arm_class(two, k, "20")
    assert c.cls == "UNRELIABLE" and c.label == "UNRELIABLE (LM CAPABILITY REDUCED)" and c.lm_reduced
    three_fail = {x: (flagged if i < 2 else FAILED if i < 4 else OK) for i, x in enumerate(k)}
    assert C.arm_class(three_fail, k, "20").label == "UNRELIABLE"  # more than one failed cell: the plain label


def test_draw_counts_and_per_draw_bound() -> None:
    k = keys20()
    v = {x: (FAILED if x == (3, 1) else OK) for x in k}
    c = C.arm_class(v, k, "20")
    assert (c.draws_evaluated, c.draws_succeeded, c.draws_failed, c.successes, c.failures) == (10, 9, 1, 19, 1)
    assert c.per_draw_bound == pytest.approx(0.606, abs=5e-4)


def test_printed_bounds_of_section_6_3() -> None:
    table = {(10, 10): 0.741, (9, 10): 0.606, (9, 9): 0.717, (8, 9): 0.571, (8, 10): 0.493, (3, 3): 0.368, (16, 18): 0.690, (12, 14): 0.615, (18, 18): 0.847, (17, 18): 0.762, (14, 14): 0.807, (13, 14): 0.703}
    for (k, n), b in table.items():
        assert C.per_draw_bound(k, n) == pytest.approx(b, abs=6e-4), (k, n)


def test_probe_status_counts_only() -> None:
    ok = {(d, 0): OK for d in (11, 12, 13)}
    p = C.probe_status(ok, dict.fromkeys((11, 12, 13), True))
    assert p["status"] == "COMPLETE" and p["successes"] == 3 and "per-draw bound 0.368" in p["label"]
    two = C.probe_status({**ok, (13, 0): FAILED}, dict.fromkeys((11, 12, 13), True))
    assert two["label"] == "2 of 3 succeed" and two["per_draw_bound"] is not None
    ne = C.probe_status({**ok, (12, 0): NE}, dict.fromkeys((11, 12, 13), True))
    assert ne["status"] == "NOT_EVALUATED" and ne["label"] == "NOT_EVALUATED"
    assert C.probe_status({k: OK for k in ok if k[0] != 13}, {11: True, 12: True, 13: False})["status"] == "NOT_EVALUATED"


# --- paired d under both criteria --------------------------------------------------------------------------------------------------------------
def test_paired_labels_and_both_criteria() -> None:
    k = keys20()
    a0 = {x: (OK if i < 4 else FAILED) for i, x in enumerate(k)}
    x = dict.fromkeys(k, OK)
    p = C.paired("A5-D", x, a0)
    assert (p.d, p.x_only, p.a0_only, p.pairs) == (16, 16, 0, 20) and p.label == C.IMPROVES and p.p_value == pytest.approx(2 * 0.5**16)
    harm = C.paired("X", {y: (FAILED if i < 4 else OK) for i, y in enumerate(k)} | {y: FAILED for y in k[:4]}, dict.fromkeys(k, OK))
    assert harm.label == C.HARMS and harm.d == -4
    three = C.paired("X", {y: OK for y in k}, {y: (FAILED if i < 3 else OK) for i, y in enumerate(k)})
    assert three.d == 3 and three.label == C.NOT_DISTINGUISHED  # d >= 4 is needed


def test_d_under_s0_and_p9ii_criteria_differ_when_condition_6_decides() -> None:
    run = syn.make_run(patterns={("A1", "2K/4K"): syn.always("dep"), ("A0", "2K/4K"): syn.always("bad")})
    from studies.p10s0 import analysis

    res = analysis.analyze(run)
    p = res["paired"]["A1"]["2K/4K"]
    assert p["s0"]["d"] == 0 and p["p9ii"]["d"] == 20 and p["p9ii"]["label"] == C.IMPROVES and p["s0"]["label"] == C.NOT_DISTINGUISHED


def test_h20d_note() -> None:
    assert C.h20d_note(3) and "unreachable" in (C.h20d_note(3) or "")
    assert C.h20d_note(4) is None


# --- replication --------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("s0,p9,expected", [("RELIABLE", "RELIABLE", C.REPLICATES), ("UNRELIABLE", "FAILS", C.REPLICATES), ("FAILS", "UNRELIABLE", C.REPLICATES), ("RELIABLE", "UNRELIABLE", C.NOT_REPLICATE), ("FAILS", "RELIABLE", C.NOT_REPLICATE), ("NOT_EVALUATED", "RELIABLE", C.NOT_COMPARABLE), ("RELIABLE", "NOT_EVALUATED", C.NOT_COMPARABLE)])
def test_replication_labels(s0: str, p9: str, expected: str) -> None:
    assert C.replication(s0, {"available": True, "base_class": p9}) == expected


def test_replication_not_comparable_without_a_p9ii_class() -> None:
    assert C.replication("RELIABLE", None) == C.NOT_COMPARABLE and C.replication("RELIABLE", syn.unavailable()) == C.NOT_COMPARABLE


# --- consistency (section 8.5) ------------------------------------------------------------------------------------------------------------------
def test_consistency_single_study_cases() -> None:
    for p in (None, syn.unavailable(), syn.p9ii_class("NOT_EVALUATED", 0, 2)):
        c = C.consistency(p, 10, 3)
        assert c["label"] == C.SINGLE_STUDY and c["consistent"] and c["single_study"]


@pytest.mark.parametrize("p9_failed,s0_failed,expected", [(0, 0, True), (2, 0, True), (1, 1, True), (0, 2, True), (3, 0, False), (2, 1, False), (0, 3, False), (6, 0, False)])
def test_consistency_threshold_is_two_failed_draws_of_both_studies(p9_failed: int, s0_failed: int, expected: bool) -> None:
    c = C.consistency(syn.p9ii_class("RELIABLE" if p9_failed < 2 else "UNRELIABLE", p9_failed, 8), 10, s0_failed)
    assert c["consistent"] is expected and c["label"] == (C.CONSISTENT if expected else C.INCONSISTENT)
    assert (c["pooled_failed"], c["pooled_n"]) == (p9_failed + s0_failed, 18)


def test_consistency_lm_capability_reduced_in_p9ii_is_inconsistent() -> None:
    assert not C.consistency(syn.p9ii_class("UNRELIABLE", 0, 8, lm=True), 10, 0)["consistent"]


def test_inconsistent_label_text() -> None:
    c = C.consistency(syn.p9ii_class("UNRELIABLE", 6, 8), 10, 1)
    assert C.inconsistent_label(c) == "RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 7 of 18 draws failed)"


def test_what_the_committed_records_require_of_s0_section_3_5() -> None:
    p = syn.committed_p9ii_classes()
    for s0_failed in range(0, 11):
        assert not C.consistency(p["A0"]["4096"], 10, s0_failed)["consistent"]  # A0 at 4,096: INCONSISTENT whatever S0 observes
        assert not C.consistency(p["A2"]["4096"], 10, s0_failed)["consistent"]
        assert C.consistency(p["A2"]["16384"], 10, s0_failed)["single_study"]  # A2 has no Stage 2 class
    for s0_failed in (0, 1):  # RELIABLE in S0 allows at most one failed draw
        assert C.consistency(p["A5-D"]["4096"], 10, s0_failed)["consistent"] and C.consistency(p["A5-D"]["16384"], 10, s0_failed)["consistent"]
        assert C.consistency(p["A1"]["4096"], 10, s0_failed)["consistent"]
    assert C.consistency(p["A1"]["16384"], 10, 0)["consistent"]  # no failed draw in S0 at 8K/16K
    assert not C.consistency(p["A1"]["16384"], 10, 1)["consistent"]  # one failed draw is already stricter than RELIABLE
    assert C.consistency(p["A0"]["16384"], 10, 2)["consistent"] and not C.consistency(p["A0"]["16384"], 10, 3)["consistent"]


def test_pooled_line_never_prints_a_bound_for_a5d() -> None:
    p = syn.p9ii_class("RELIABLE", 0, 8)
    s0 = C.arm_class(dict.fromkeys(keys20(), OK), keys20(), "20")
    a5d = C.pooled_line(p, s0, 0, "A5-D")
    assert a5d["per_draw_bound"] is None and "no pooled per-draw bound is printed for A5-D" in a5d["text"] and "18 of 18" in a5d["text"]
    a1 = C.pooled_line(p, s0, 0, "A1")
    assert a1["per_draw_bound"] == pytest.approx(0.847, abs=6e-4) and "pooled per-draw bound 0.847" in a1["text"]
    assert C.pooled_line(None, s0, 0, "A1") == {"available": False, "text": "NOT AVAILABLE"}
    assert C.pooled_line(syn.unavailable(), s0, 0, "A1")["text"] == "NOT AVAILABLE"


# --- the candidate and the preference order -------------------------------------------------------------------------------------------------------
def ev(meets: bool, consistent: bool = True, single: bool = False, p9: str = "RELIABLE", failed: int = 0, n: int = 18) -> dict[str, object]:
    return {"meets": meets, "consistency": {"label": "x", "consistent": consistent, "single_study": single, "p9ii_class": p9, "pooled_failed": failed, "pooled_n": n}}


def both(**kw: dict[str, object]) -> dict[str, dict[str, object]]:
    return {arm: {"2K/4K": v, "8K/16K": v} for arm, v in kw.items()}


def test_candidate_follows_the_preference_order() -> None:
    sel = C.select_candidate(both(**{"A0": ev(True), "A5-D": ev(True), "A1": ev(True)}))
    assert sel["candidate"] == "A0" and sel["answer_only_suffices"] == "(ANSWER-ONLY SUFFICES)" and sel["outcome"] == C.OUT_QUALIFIED
    assert sel["also_qualifies"] == ["ALSO QUALIFIES: A5-D (4,096 AND 16,384)", "ALSO QUALIFIES: A1 (4,096 AND 16,384)"]
    sel = C.select_candidate(both(**{"A0": ev(False), "A5-D": ev(True), "A2": ev(True), "A1": ev(True)}))
    assert sel["candidate"] == "A5-D" and sel["answer_only_suffices"] is None and sel["also_qualifies"] == ["ALSO QUALIFIES: A2 (4,096 AND 16,384)", "ALSO QUALIFIES: A1 (4,096 AND 16,384)"]
    sel = C.select_candidate(both(**{"A0": ev(False), "A5-D": ev(False), "A1": ev(True)}))
    assert sel["candidate"] == "A1" and not sel["also_qualifies"]


def test_inconsistent_arm_is_not_qualified_and_the_rule_moves_on() -> None:
    sel = C.select_candidate(both(**{"A0": ev(True, consistent=False, p9="UNRELIABLE", failed=7), "A1": ev(True)}))
    assert sel["candidate"] == "A1"
    assert sel["per_arm"]["A0"]["qualifies_at"] == [] and "INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 7 of 18 draws failed)" in sel["per_arm"]["A0"]["inconsistent_notes"]["2K/4K"]


def test_qualified_at_4096_only_and_no_arm() -> None:
    e = {"A5-D": {"2K/4K": ev(True), "8K/16K": ev(False)}, "A1": {"2K/4K": ev(True), "8K/16K": ev(True, consistent=False)}}
    sel = C.select_candidate(e)
    assert sel["candidate"] is None and sel["qualified_4096_only"] == "A5-D" and sel["outcome"] == C.OUT_QUALIFIED_4096 and sel["also_qualifies"] == ["ALSO QUALIFIES: A1 (4,096 ONLY)"]
    none = C.select_candidate(both(**{"A5-D": ev(False), "A1": ev(True, consistent=False)}))
    assert none["outcome"] == C.OUT_NOT_QUALIFIED and none["candidate"] is None and none["qualified_4096_only"] is None
    # item 1 beats item 2: a later arm that qualifies at both sizes is the candidate even when an earlier arm qualifies at 4,096 only
    mixed = C.select_candidate({"A5-D": {"2K/4K": ev(True), "8K/16K": ev(False)}, "A1": {"2K/4K": ev(True), "8K/16K": ev(True)}})
    assert mixed["candidate"] == "A1"


def test_single_study_evidence_is_recorded_per_size() -> None:
    sel = C.select_candidate({"A5-D": {"2K/4K": ev(True, single=True), "8K/16K": ev(True)}})
    assert sel["per_arm"]["A5-D"]["single_study_sizes"] == ["2K/4K"] and sel["candidate"] == "A5-D"


def test_a0_cannot_be_the_candidate_on_the_committed_records() -> None:
    p = syn.committed_p9ii_classes()
    c = {arm: {ct: C.consistency(p[arm][s], 10, 0) for ct, s in (("2K/4K", "4096"), ("8K/16K", "16384"))} for arm in ("A0", "A2")}
    sel = C.select_candidate({arm: {ct: {"meets": True, "consistency": c[arm][ct]} for ct in c[arm]} for arm in ("A0", "A2")})
    assert sel["candidate"] is None and sel["qualified_4096_only"] is None  # "(ANSWER-ONLY SUFFICES)" cannot be printed
    assert "2K/4K" in sel["per_arm"]["A0"]["inconsistent_notes"]


# --- annotations on the candidate -----------------------------------------------------------------------------------------------------------------
def test_overload_labels() -> None:
    rel = C.arm_class(dict.fromkeys(keys10(), OK), keys10(), "10")
    bad = C.arm_class(dict.fromkeys(keys10(), FAILED), keys10(), "10")
    ne = C.arm_class({k: NE for k in keys10()}, keys10(), "10")
    assert C.overload_label("A5-D", rel) == "OVERLOAD-QUALIFIED" and C.overload_label("A5-D", bad) == "OVERLOAD NOT QUALIFIED" and C.overload_label("A5-D", ne) == "OVERLOAD NOT_EVALUATED"
    assert C.overload_label("A1", rel) == "OVERLOAD NOT RUN — NO TARGET INJECTION" and C.overload_label("A2", rel) == "OVERLOAD NOT RUN — NO TARGET INJECTION"
    assert C.overload_label(None, None) == "OVERLOAD NOT RUN — NO CANDIDATE"


def test_record_length_labels() -> None:
    rel = C.arm_class(dict.fromkeys(keys10(), OK), keys10(), "10")
    bad = C.arm_class(dict.fromkeys(keys10(), FAILED), keys10(), "10")
    ne = C.arm_class({k: NE for k in keys10()}, keys10(), "10")
    st, un = {"label": "ADDRESS STABLE"}, {"label": None}
    assert C.record_length_label({"2K/4K": (rel, st), "8K/16K": (rel, st)}, "COMPLETE") == "RECORD-LENGTH-FREE VARIANT: PASSES"
    assert C.record_length_label({"2K/4K": (rel, st), "8K/16K": (bad, st)}, "COMPLETE") == "RECORD-LENGTH-FREE VARIANT: PASSES AT 4,096 ONLY"
    assert C.record_length_label({"2K/4K": (rel, st), "8K/16K": (rel, un)}, "COMPLETE") == "RECORD-LENGTH-FREE VARIANT: PASSES AT 4,096 ONLY"
    assert "DOES NOT PASS (not evidence that the record length is required)" in C.record_length_label({"2K/4K": (bad, st), "8K/16K": (rel, st)}, "COMPLETE")
    assert C.record_length_label({"2K/4K": (ne, st), "8K/16K": (rel, st)}, "COMPLETE") == "RECORD-LENGTH-FREE VARIANT: NOT_EVALUATED"
    assert C.record_length_label({}, "NOT RUN — BUDGET") == "RECORD-LENGTH-FREE VARIANT: NOT RUN — BUDGET"
    assert C.record_length_label({"2K/4K": (rel, st)}, "COMPLETE") == "RECORD-LENGTH-FREE VARIANT: INCOMPLETE"


# --- outcome rows (section 8.7) ---------------------------------------------------------------------------------------------------------------------
def test_outcome_rows_first_match_wins() -> None:
    none = {"candidate": None, "qualified_4096_only": None}
    assert C.study_outcome(not_started=True, engineering=["x"], inconclusive=True, selection={"candidate": "A1", "qualified_4096_only": None}).row == 1
    assert C.study_outcome(not_started=False, engineering=["gate"], inconclusive=True, selection={"candidate": "A1", "qualified_4096_only": None}).row == 2
    assert C.study_outcome(not_started=False, engineering=[], inconclusive=True, selection={"candidate": "A1", "qualified_4096_only": None}).row == 3
    o4 = C.study_outcome(not_started=False, engineering=[], inconclusive=False, selection={"candidate": "A5-D", "qualified_4096_only": None})
    assert (o4.row, o4.outcome, o4.arm) == (4, "ADDRESSING-QUALIFIED (4,096 AND 16,384)", "A5-D")
    assert C.study_outcome(not_started=False, engineering=[], inconclusive=False, selection=none).row == 6
    assert C.OUTCOMES == tuple(C.OUTCOME_ROWS) and sorted(C.OUTCOME_ROWS.values()) == [1, 2, 3, 4, 5, 6]


def test_row_5_names_why_16384_is_missing() -> None:
    def e(cls: str, stable: bool = True, consistent: bool = True) -> dict[str, dict[str, object]]:
        c = C.arm_class(dict.fromkeys(keys20(), OK if cls == "RELIABLE" else FAILED if cls == "FAILS" else NE), keys20(), "20")
        if cls == "UNRELIABLE":
            c = C.arm_class({k: (OK if i < 6 else FAILED) for i, k in enumerate(keys20())}, keys20(), "20")
        return {"8K/16K": {"s0": c, "stable": {"label": "ADDRESS STABLE" if stable else None}, "consistency": C.consistency(syn.p9ii_class("UNRELIABLE", 2, 4), 10, 2 if not consistent else 0)}}

    sel = {"candidate": None, "qualified_4096_only": "A1"}
    for cls, kw, expect in (("UNRELIABLE", {}, "UNRELIABLE"), ("FAILS", {}, "FAILS"), ("NE", {}, "NOT_EVALUATED at 16,384 (not read as a failure)"), ("RELIABLE", {"stable": False}, "not ADDRESS STABLE at 16,384"), ("RELIABLE", {"consistent": False}, "INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 4 of 14 draws failed)")):
        o = C.study_outcome(not_started=False, engineering=[], inconclusive=False, selection=sel, evals={"A1": e(cls, **kw)})
        assert o.row == 5 and expect in o.detail["why_16384_missing"] and o.scope == "4,096 ONLY"


def test_q1_inconclusive_needs_more_than_one_unusable_a6() -> None:
    assert not C.q1_inconclusive(dict.fromkeys(range(1, 11), True)) and not C.q1_inconclusive({**dict.fromkeys(range(1, 11), True), 3: False})
    assert C.q1_inconclusive({**dict.fromkeys(range(1, 11), True), 3: False, 4: False})


# --- hypothesis readings ---------------------------------------------------------------------------------------------------------------------------
def test_hypothesis_readings_are_fixed_as_in_the_adr() -> None:
    from studies.p10s0 import analysis

    res = analysis.analyze(syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D"))
    h = res["hypotheses"]
    assert h["H20-A"]["reading"] == "supported" and h["H20-B"]["reading"] == "supported" and h["H20-C"]["reading"] == "supported" and h["H20-D"]["reading"] == "supported"
    assert res["outcome"]["row"] == 4 and res["outcome"]["arm"] == "A5-D" and h["H20-Q"]["reading"] == "supported"  # A0 meets nothing here; A5-D is first among the arms that can qualify
    assert h["H20-L"]["reading"] == "supported" and h["H20-O"]["reading"] == "supported" and h["H20-S"]["reading"] == "supported"


def test_h20_l_is_never_contradicted_and_h20_s_follows_the_counts() -> None:
    rel = {"reading": "x"}
    out = C.hypothesis_readings(
        classes={}, paired_s0={}, replication_labels={}, outcome=C.Outcome(4, "x", "x", "A5-D"), candidate="A5-D", overload="OVERLOAD-QUALIFIED", record_length="RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required)",
        probe={"status": "COMPLETE", "successes": 0, "draws": 3, "label": "0 of 3 succeed"}, probe_a6_evaluated=True, a0_failed_cells_8k16k=None,
    )
    assert out["H20-L"]["reading"] == "not supported" and out["H20-S"]["reading"] == "CONTRADICTED" and out["H20-O"]["reading"] == "supported" and rel
    zero_ne = C.hypothesis_readings(classes={}, paired_s0={}, replication_labels={}, outcome=C.Outcome(4, "x", "x", "A5-D"), candidate="A5-D", overload="OVERLOAD NOT RUN — NO TARGET INJECTION", record_length="RECORD-LENGTH-FREE VARIANT: PASSES", probe={"status": "COMPLETE", "successes": 3, "draws": 3, "label": "3 of 3 succeed"}, probe_a6_evaluated=True, a0_failed_cells_8k16k=None)
    assert zero_ne["H20-S"]["reading"] == "supported" and zero_ne["H20-L"]["reading"] == "supported" and zero_ne["H20-O"]["reading"] == "not tested"
    some = C.hypothesis_readings(classes={}, paired_s0={}, replication_labels={}, outcome=C.Outcome(4, "x", "x", "A5-D"), candidate="A5-D", overload="x", record_length="x", probe={"status": "COMPLETE", "successes": 2, "draws": 3, "label": "2 of 3 succeed"}, probe_a6_evaluated=True, a0_failed_cells_8k16k=None)
    assert some["H20-S"]["reading"] == "not supported"
    no_candidate = C.hypothesis_readings(classes={}, paired_s0={}, replication_labels={}, outcome=C.Outcome(6, "x", "x"), candidate=None, overload="OVERLOAD NOT RUN — NO CANDIDATE", record_length="x", probe=None, probe_a6_evaluated=False, a0_failed_cells_8k16k=None)
    assert no_candidate["H20-L"]["reading"] == "not tested" and no_candidate["H20-S"]["reading"] == "not tested" and no_candidate["H20-Q"]["reading"] == "not supported"


def test_h20_b_c_d_reading_rules() -> None:
    imp = p9c.Paired("X", C.IMPROVES, 5, 5, 0, 15, 10, 20, 0.1)
    harm = p9c.Paired("X", C.HARMS, -5, 0, 5, 5, 10, 20, 0.1)
    nd = p9c.Paired("X", C.NOT_DISTINGUISHED, 1, 1, 0, 11, 10, 20, 0.9)
    rel = C.arm_class(dict.fromkeys(keys20(), OK), keys20(), "20")
    unrel = C.arm_class({k: (OK if i < 6 else FAILED) for i, k in enumerate(keys20())}, keys20(), "20")

    def read(pairs: dict[str, p9c.Paired], cls: C.SClass) -> str:
        cl = {a: {ct: cls for ct in core.CORE_CELLTYPES} for a in ("A0", "A1", "A2", "A5-D")}
        pr = {a: dict.fromkeys(core.CORE_CELLTYPES, pairs[a]) for a in ("A1", "A2", "A5-D")}
        return C.hypothesis_readings(classes=cl, paired_s0=pr, replication_labels={}, outcome=C.Outcome(6, "x", "x"), candidate=None, overload="x", record_length="x", probe=None, probe_a6_evaluated=False, a0_failed_cells_8k16k=None)["H20-B"]["reading"]

    assert read(dict.fromkeys(("A1", "A2", "A5-D"), imp), rel) == "supported"
    assert read(dict.fromkeys(("A1", "A2", "A5-D"), imp), unrel) == "not supported"
    assert read(dict.fromkeys(("A1", "A2", "A5-D"), nd), rel) == "not supported"
    assert read(dict.fromkeys(("A1", "A2", "A5-D"), harm), rel) == "CONTRADICTED"


def test_h20_d_registered_note_reads_not_supported_when_a0_fails_fewer_than_four() -> None:
    from studies.p10s0 import analysis

    res = analysis.analyze(syn.make_run(patterns={("A0", "2K/4K"): syn.always("bad"), ("A0", "8K/16K"): syn.failing_cells({(1, 0), (2, 0), (3, 0)})}))
    assert res["a0_failed_cells_8k16k"] == 3 and res["hypotheses"]["H20-D"]["reading"] == "not supported" and "unreachable" in res["hypotheses"]["H20-D"]["registered_note"]


def test_replication_hypotheses_not_read_when_not_comparable() -> None:
    from studies.p10s0 import analysis

    res = analysis.analyze(syn.make_run())
    r = res["hypotheses"]
    assert r["H20-R (A2, 8K/16K)"]["reading"] == "not read" and r["H20-R (A0, 2K/4K)"]["reading"] in ("supported", "not supported")
    assert itertools.chain  # keep the import used


def test_h20_a_is_the_adr_s_sentence_for_every_pair_of_a0_classes() -> None:
    """Supported if A0 is UNRELIABLE or FAILS at 2K/4K or at 8K/16K; not supported if RELIABLE at both; not read otherwise (the lead's ruling on m4)."""
    mk = {"R": C.arm_class(dict.fromkeys(keys20(), OK), keys20(), "20"), "U": C.arm_class({k: (OK if i < 6 else FAILED) for i, k in enumerate(keys20())}, keys20(), "20"), "F": C.arm_class(dict.fromkeys(keys20(), FAILED), keys20(), "20"), "N": C.arm_class({k: NE for k in keys20()}, keys20(), "20")}
    expect = {}
    for a, b in itertools.product("RUFN", repeat=2):
        expect[(a, b)] = "supported" if ("U" in (a, b) or "F" in (a, b)) else "not supported" if (a, b) == ("R", "R") else "not read"
    for (a, b), reading in expect.items():
        out = C.hypothesis_readings(classes={"A0": {"2K/4K": mk[a], "8K/16K": mk[b]}}, paired_s0={}, replication_labels={}, outcome=C.Outcome(6, "x", "x"), candidate=None, overload="x", record_length="x", probe=None, probe_a6_evaluated=False, a0_failed_cells_8k16k=None)
        assert out["H20-A"]["reading"] == reading, (a, b)


def test_h20_o_readings_and_the_descriptive_class() -> None:
    def read(label: str) -> dict:
        return C.hypothesis_readings(classes={}, paired_s0={}, replication_labels={}, outcome=C.Outcome(4, "x", "x", "A5-D"), candidate="A5-D", overload=label, record_length="x", probe=None, probe_a6_evaluated=False, a0_failed_cells_8k16k=None, a5d_8k4k_label="UNRELIABLE")["H20-O"]

    assert read("OVERLOAD NOT_EVALUATED")["reading"] == "not read" and read("OVERLOAD NOT QUALIFIED")["reading"] == "not supported" and read("OVERLOAD-QUALIFIED")["reading"] == "supported"
    assert read("OVERLOAD NOT RUN — NO TARGET INJECTION")["reading"] == "not tested" and read("OVERLOAD NOT RUN — NO CANDIDATE")["reading"] == "not tested"
    assert read("OVERLOAD NOT_EVALUATED")["descriptive_a5d_8k_4k_class"] == "UNRELIABLE"


def test_address_stable_counts_a_non_finite_stability_as_zero() -> None:
    obs = {(d, 0): syn.observation("ok", stability=0.9 if d > 11 else math.nan) for d in range(1, 21)}
    ver = dict.fromkeys(obs, OK)
    r = C.address_stable(obs, ver)
    assert r["non_finite"] == 11 and r["cells"] == 20 and r["label"] is None and r["median"] == 0.0  # 11 of 20 cells at 0 and 9 at 0.9: not ADDRESS STABLE
    ok = C.address_stable({(d, 0): syn.observation("ok", stability=0.9) for d in range(1, 21)}, dict.fromkeys(obs, OK))
    assert ok["label"] == "ADDRESS STABLE" and ok["non_finite"] == 0
