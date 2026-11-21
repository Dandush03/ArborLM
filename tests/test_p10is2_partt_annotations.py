# ruff: noqa: E501
"""P10IS2 Part T annotations, cost lines and thresholds shared with P10-S2's classes, on hand-built registries (ADR-0025 section 8.5; ADR-0022 section 11.4). Self-check only. Seeds 934001-934999."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_partt_fixtures import CFG_T, Spec, build, quantities  # noqa: E402

from studies.p10is2 import annotations as A  # noqa: E402
from studies.p10is2 import cost  # noqa: E402
from studies.p10is2.quantities import Quantities, key  # noqa: E402
from studies.p10s2 import core as c2  # noqa: E402


def both(arm: str, value: float, spec: Spec | None = None) -> Spec:
    s = spec or Spec()
    for r in (0, 1, 2):
        for c in "AB":
            s.set(arm, "-", r, c, "full", value)
    return s


def test_thresholds_reused_from_p10s2_classes_equal_this_studys_config() -> None:
    g = c2.CFG["gates"]
    for k in ("composes_ratio_min", "composes_negative", "acq_gap_min"):
        assert g[k] == CFG_T["gates"][k]
    assert c2.GAP_MIN == CFG_T["data"]["gap_denominator_min"]


def test_defaults_hold_no_row_annotation() -> None:
    q = quantities()
    for fn in (A.no_advantage_over_separate, A.equivalent_to_word_table):
        assert fn(q)["holds"] is False  # D-sep 0.85 against 0.90; E-table 0.40 against 0.90
    assert A.lookup_within(q, ("R-icl", "R-nn"), "RETRIEVAL SUFFICES", True)["holds"] is False
    assert A.below_joint(q, "M-append", "M-joint", "BELOW JOINT BOUND")["holds"] is False  # 0.90 against 0.85
    assert A.below_joint(q, "M-joint", "D-joint", "BELOW ADAPTER JOINT")["holds"] is False
    assert A.task_coded_sparse_retention(q)["holds"] is False  # M-seq and D-seq lose the same
    assert A.append_cost(q)["holds"] is None  # no append snapshot recorded


def test_each_row_annotation_holds_when_its_rule_does() -> None:
    assert A.no_advantage_over_separate(quantities(both("D-sep", 0.87)))["holds"] is True  # exactly 0.03 below: within
    assert A.no_advantage_over_separate(quantities(both("D-sep", 0.8699)))["holds"] is False
    assert A.equivalent_to_word_table(quantities(both("E-table", 0.87)))["holds"] is True
    s = both("R-nn", 0.88)
    assert A.lookup_within(quantities(s), ("R-icl", "R-nn"), "RETRIEVAL SUFFICES", True)["holds"] is True  # the best of the two
    assert A.lookup_within(quantities(both("R-gloss", 0.9)), ("R-gloss",), "LEXICON-EQUIVALENT", False)["holds"] is True


def test_below_joint_edge_and_task_coded_guard() -> None:
    q = quantities(both("M-joint", 1.0))
    assert A.below_joint(q, "M-append", "M-joint", "BELOW JOINT BOUND")["holds"] is False  # 0.90 is not below 0.90 x 1.0
    q2 = quantities(both("M-joint", 1.01))
    assert A.below_joint(q2, "M-append", "M-joint", "BELOW JOINT BOUND")["holds"] is True
    assert A.below_joint(quantities(both("D-joint", 1.0)), "M-joint", "D-joint", "BELOW ADAPTER JOINT")["holds"] is True  # 0.85 < 0.90
    # M-seq forgets 0.60 of G, D-seq 0.80: M-seq's loss is smaller by 0.20 >= 0.10 in every cell
    s = Spec()
    for r, o in CELLS_ALL:
        s.set("D-seq", o, r, o[0], "full", 0.10)
    assert A.task_coded_sparse_retention(quantities(s))["holds"] is True
    s2 = Spec()
    for r, o in CELLS_ALL:
        s2.set("D-seq", o, r, o[0], "full", 0.10)
    s2.set("D-seq", "AB", 0, "B", "full", 0.40)  # a dense second stage that learned little: the guard
    r = A.task_coded_sparse_retention(quantities(s2))
    assert r["holds"] is None and "NOT EVALUABLE" in r["detail"]["reason"]


CELLS_ALL = [(r, o) for r in (0, 1, 2) for o in ("AB", "BA")]


def test_append_cost_and_exact_match_weak_and_router_rows() -> None:
    reg = build()
    for r, o in CELLS_ALL:
        p = "E_A" if o[0] == "A" else "E_B"
        reg.values[key("M-append@append", o, r, f"s:{p}")] = 0.8  # G 0.80 at the append point against M1's 0.90
    q = Quantities(reg, quantities().th)
    ac = A.append_cost(q)
    assert ac["holds"] is True and abs(ac["detail"]["change_in_G_first"]["0AB"] + 0.10) < 1e-12
    for c in "AB":
        p = "E_A" if c == "A" else "E_B"
        reg.values[key("S0", "-", "-", f"em:{p}")] = 0.0
        reg.values[key("TEACHER", "-", "-", f"em:{p}")] = 0.8
        for r, o in CELLS_ALL:
            reg.values[key("M-append", o, r, f"em:{p}")] = 0.05
    em = A.exact_match_weak(reg)
    assert em["holds"] is True and abs(em["detail"]["gap_closed"]["A"] - 0.0625) < 1e-12  # 0.05 / 0.8 < 0.10
    for c in "AB":
        p = "E_A" if c == "A" else "E_B"
        for r, o in CELLS_ALL:
            reg.values[key("M-append", o, r, f"em:{p}")] = 0.4
    assert A.exact_match_weak(reg)["holds"] is False
    # ROUTER: learned-route scores equal the oracle ones, accuracy at 0.99 on all three readings
    for r, o in CELLS_ALL:
        for p in ("E_A", "E_B"):
            reg.values[key("M-append", o, r, f"lr:{p}")] = reg.values[key("M-append", o, r, f"s:{p}")]
    side = {f"r{r}/M-append/{o}": {"route": {"route_accuracy": {"A": 1.0, "B": 0.99, "general": 0.995}}} for r, o in CELLS_ALL}
    q2 = Quantities(reg, quantities().th)
    assert A.router_qualified(q2, side)["holds"] is True
    side["r1/M-append/BA"]["route"]["route_accuracy"]["general"] = 0.98
    assert A.router_qualified(q2, side)["holds"] is False


def test_cost_lines_always_carry_the_note_and_the_function_is_hand_checkable() -> None:
    lines = A.cost_lines({"M-append": 1.5e9}, {"M-append": 12.0})
    assert "enters no label" in lines[0] and "not measured efficiency" in lines[0] and "no comparison label" in lines[1]
    assert "never a speedup" in cost.COST_NOTE and "COST_NOTE" in cost.__doc__
