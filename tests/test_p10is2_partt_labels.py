# ruff: noqa: E501
"""P10IS2 Part T labels on a synthetic registry with known answers (ADR-0025 sections 8.1 to 8.6, 11 item 8). Every row of every line the labels module derives is reached with a hand-chosen registry; the
expected label of each case is written here, not derived with the helper under test. Self-check only: not independent review. Seeds 934001-934999."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_partt_fixtures import Spec, build, quantities  # noqa: E402

from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2.quantities import CELLS, Missing, Quantities, gap, key  # noqa: E402

CELL_NAMES = [f"{r}{o}" for r, o in CELLS]


def test_defaults_reach_every_positive_row() -> None:
    q = quantities()
    r = L.derive_all(q)
    assert r["ACQUISITION"]["label"] == "ACQUISITION-POSITIVE"
    assert r["RETENTION"]["label"] == "RETENTION-POSITIVE" and r["RETENTION"]["table"]["forgetting_pressure"]["cells"] == 6
    assert r["GENERAL-QUALITY"]["label"] == "PRESERVED" and r["GENERAL-QUALITY"]["note"] == "the keyword router stayed silent"
    assert r["AGAINST-DENSE"]["value"] == "acquisition: MEMORY AHEAD; retention: NOT DISTINGUISHED"  # dG = 0.90 - 0.80; drho = 1 - 1
    assert r["AGAINST-LOOKUP"]["label"] == "MEMORY ADDS OVER LOOKUP" and r["AGAINST-LOOKUP"]["baseline"] == "E-table"
    assert r["MODIFICATION"]["label"] == "RETAINS UNDER MODIFICATION" and r["M-ii GEN"] is True
    assert r["MILESTONE"]["label"] == "SUPPORTED (append-frozen + consolidation)"


def test_gap_hand_values_and_the_denominator_rule() -> None:
    assert gap(0.5, 0.0, 1.0, 0.30) == 0.5 and gap(0.5, 0.0, 0.30, 0.30) == pytest.approx(0.5 / 0.30)
    assert gap(0.5, 0.0, 0.2999, 0.30) is None and gap(float("nan"), 0.0, 1.0, 0.30) is None
    q = quantities()
    assert q.G("M-append", "AB", 0, "A") == 0.90 and q.G("M-append", "AB", 0, "B") == 0.90
    assert q.rho("M-append", "AB", 0) == 1.0 and q.forgetting("M-append", "AB", 0) == 0.0
    assert q.rho("M-seq", "AB", 0) == pytest.approx(0.30 / 0.90) and q.forgetting("M-seq", "AB", 0) == pytest.approx(0.60)


# --- ACQUISITION -------------------------------------------------------------------------------------------------------------------------------
def test_acquisition_row_1_not_evaluable() -> None:
    q = quantities(teacher_full={"B": 0.29})
    assert L.acquisition(q)["label"] == "NOT EVALUABLE"
    assert L.acquisition(quantities(), recompute_failed=[(0, "AB")])["label"] == "NOT EVALUABLE"  # the second guard
    assert L.acquisition(quantities(teacher_full={"B": 0.30}))["label"] != "NOT EVALUABLE"  # 0.30 is defined (>=)


def test_acquisition_row_2_negative_first_second_and_both() -> None:
    assert L.acquisition(quantities(Spec().all_cells("M1", "first", "full", 0.20)))["label"] == "ACQUISITION-NEGATIVE (FIRST TEACHER)"
    assert L.acquisition(quantities(Spec().all_cells("M-append", "second", "full", 0.20)))["label"] == "ACQUISITION-NEGATIVE (SECOND TEACHER)"
    both = Spec().all_cells("M1", "first", "full", 0.20).all_cells("M-append", "second", "full", 0.24)
    assert L.acquisition(quantities(both))["label"] == "ACQUISITION-NEGATIVE (FIRST TEACHER; SECOND TEACHER)"  # ruling G16
    # 0.25 is the edge: not below it
    assert L.acquisition(quantities(Spec().all_cells("M1", "first", "full", 0.25)))["label"] == "ACQUISITION-INCONCLUSIVE"
    # five of six cells negative is not "every cell"
    s = Spec().all_cells("M1", "first", "full", 0.20)
    s.set("M1", "AB", 0, "A", "full", 0.60)
    assert not L.acquisition(quantities(s))["label"].startswith("ACQUISITION-NEGATIVE")


def test_acquisition_row_2_precedes_control_failed_and_row_1_precedes_row_2() -> None:
    s = Spec().all_cells("M1", "first", "full", 0.20).set("M-seq", "AB", 0, "B", "value", 0.60)
    assert L.acquisition(quantities(s))["label"] == "ACQUISITION-NEGATIVE (FIRST TEACHER)"  # NO-ACQUISITION is read before CONTROL-FAILED (row 26)
    assert L.acquisition(quantities(s, teacher_full={"A": 0.2}))["label"] == "NOT EVALUABLE"


@pytest.mark.parametrize(
    ("arm", "order", "cap", "cond"),
    [("M1", "AB", "A", "value"), ("M1", "BA", "B", "code"), ("M-append", "AB", "B", "value"), ("M-seq", "BA", "A", "code"), ("M-ii", "AB", "B", "code")],
)
def test_acquisition_row_3_control_failed_for_each_memory_cell(arm: str, order: str, cap: str, cond: str) -> None:
    s = Spec().set(arm, order, 1, cap, cond, 0.50)  # exactly 0.50 fires
    assert L.acquisition(quantities(s))["label"] == "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED"
    s2 = Spec().set(arm, order, 1, cap, cond, 0.4999)
    assert L.acquisition(quantities(s2))["label"] in ("ACQUISITION-POSITIVE", "ACQUISITION-INCONCLUSIVE")


def test_acquisition_row_3_m_joint_each_task_on_its_own_panel() -> None:
    assert L.acquisition(quantities(Spec().set("M-joint", "-", 2, "B", "code", 0.55)))["label"] == "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED"
    assert L.acquisition(quantities(Spec().set("M-joint", "-", 0, "A", "value", 0.55)))["label"] == "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED"


def test_acquisition_row_4_5_and_passing_cells_per_order() -> None:
    s = Spec().set("M-append", "BA", 2, "A", "marker", 0.26)  # marker-only above 0.25 in one cell
    r = L.acquisition(quantities(s))
    assert r["label"] == "ACQUISITION-INCONCLUSIVE" and r["passing_cells_per_order"]["ACQ2"] == {"AB": [0, 1, 2], "BA": [0, 1]} and r["passing_cells_per_order"]["ACQ1"] == {"AB": [0, 1, 2], "BA": [0, 1, 2]}
    margin = Spec().set("M1", "AB", 0, "A", "value", 0.61)  # own 0.90 - 0.61 = 0.29 < 0.30 (and value 0.61 >= 0.50 also fires CONTROL-FAILED, which row 3 reads first)
    assert L.acquisition(quantities(margin))["label"] == "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED"
    margin2 = Spec().set("M1", "AB", 0, "A", "own", 0.70).set("M1", "AB", 0, "A", "value", 0.45)  # margin 0.25 < 0.30, no permutation at 0.50
    assert L.acquisition(quantities(margin2))["label"] == "ACQUISITION-INCONCLUSIVE"
    ratio = Spec().set("M-append", "AB", 0, "B", "full", 0.70)  # 0.70 < 0.80 x 0.90 = 0.72 (M1 of the other order on B is 0.90)
    assert L.acquisition(quantities(ratio))["label"] == "ACQUISITION-INCONCLUSIVE"
    ok = Spec().set("M-append", "AB", 0, "B", "full", 0.73)  # 0.73 >= 0.8 x 0.90 (0.72 itself is a float-noise edge: 0.8 x 0.9 is 0.7200000000000001)
    assert L.acquisition(quantities(ok))["label"] == "ACQUISITION-POSITIVE"
    low = Spec().set("M1", "AB", 0, "A", "full", 0.4999)  # ACQ1 needs G_first >= 0.50
    assert L.acquisition(quantities(low))["label"] == "ACQUISITION-INCONCLUSIVE"


def test_correction_c3_undefined_controls_cannot_hide_a_negative_and_cannot_fire_control_failed() -> None:
    sub_small = {"teacher_sub": {"A": 0.20}}  # the subsample denominator on capability A is 0.20 < 0.30
    q = quantities(Spec().all_cells("M1", "first", "full", 0.10), **sub_small)
    assert L.acquisition(q)["label"] == "ACQUISITION-NEGATIVE (FIRST TEACHER)"  # the negative zone reads full-panel values only
    s = Spec().set("M1", "AB", 0, "A", "value", 0.90)  # would fire CONTROL-FAILED, but the cell's controls on A are UNDEFINED
    r = L.acquisition(quantities(s, **sub_small))
    assert r["label"] == "ACQUISITION-INCONCLUSIVE" and "0AB:A" in r["table"]["CONTROLS UNDEFINED"]  # not CONTROL-FAILED; the control parts of ACQ1/ACQ2 fail in that cell
    assert r["table"]["ACQ1"]["0AB"] is False and r["table"]["ACQ1"]["0BA"] is True  # capability B's controls are defined in the BA cells (first = B)
    q2 = quantities(**sub_small)
    assert q2.margin_ok("M1", "AB", 0, "A") is None and q2.margin_ok("M1", "BA", 0, "B") is True
    # retention on the same registry: negative zone and rho are read as usual, no NOT EVALUABLE row appears because of undefined controls
    assert L.retention(quantities(Spec().all_cells("M-append", "first", "full", 0.30), **sub_small))["label"] == "RETENTION-NEGATIVE: FORGETTING"


# --- RETENTION ---------------------------------------------------------------------------------------------------------------------------------
def test_retention_rows_in_order() -> None:
    assert L.retention(quantities(teacher_full={"A": 0.1}))["label"] == "NOT EVALUABLE: GAP UNDEFINED / RECOMPUTATION"
    neg = Spec().all_cells("M-append", "first", "full", 0.30)  # rho = 0.30 / 0.90 = 0.33 in six evaluable cells
    assert L.retention(quantities(neg))["label"] == "RETENTION-NEGATIVE: FORGETTING"
    # exactly four evaluable cells all below 0.70: still negative; three evaluable: row 3 (FIRST NOT ACQUIRED), never negative
    four = Spec().all_cells("M-append", "first", "full", 0.30).set("M1", "AB", 0, "A", "full", 0.40).set("M1", "BA", 1, "B", "full", 0.40)
    assert L.retention(quantities(four))["label"] == "RETENTION-NEGATIVE: FORGETTING"
    three = Spec().all_cells("M-append", "first", "full", 0.30)
    for r, o in (("0", "AB"), ("1", "BA"), ("2", "AB")):
        three.set("M1", o, int(r), "A" if o == "AB" else "B", "full", 0.40)
    assert L.retention(quantities(three))["label"] == "NOT EVALUABLE: FIRST NOT ACQUIRED"
    # the negative zone is read first: a cell whose ACQ1 fails because of the controls does not turn a negative into NOT EVALUABLE
    assert L.retention(quantities(Spec().all_cells("M-append", "first", "full", 0.30).set("M1", "AB", 0, "A", "marker", 0.60)))["label"] == "RETENTION-NEGATIVE: FORGETTING"
    assert L.retention(quantities(Spec().set("M1", "AB", 0, "A", "marker", 0.60)))["label"] == "NOT EVALUABLE: FIRST NOT ACQUIRED"
    assert L.retention(quantities(Spec().set("M-append", "AB", 2, "B", "full", 0.4999)))["label"] == "RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED"
    assert L.retention(quantities(Spec().all_cells("M-seq", "first", "full", 0.90)))["label"] == "RETENTION-INCONCLUSIVE: NOT CHALLENGED — NO FORGETTING PRESSURE"
    assert L.retention(quantities(Spec().set("M-append", "AB", 0, "A", "full", 0.855)))["label"] == "RETENTION-INCONCLUSIVE"  # F = 0.045 > 0.03 though rho = 0.95
    assert L.retention(quantities(Spec().set("M-append", "AB", 0, "A", "full", 0.80)))["label"] == "RETENTION-INCONCLUSIVE"  # rho 0.889 < 0.90
    assert L.retention(quantities(Spec().set("M-append", "AB", 0, "A", "full", 0.875)))["label"] == "RETENTION-POSITIVE"  # F = 0.025 (<= 0.03), rho 0.972


def test_retention_ret_boundaries_exact() -> None:
    q = quantities(Spec().set("M1", "AB", 0, "A", "full", 1.0).set("M-append", "AB", 0, "A", "full", 0.90))  # F = 0.10
    assert not q.ret("M-append", "AB", 0)
    q = quantities(Spec().set("M1", "AB", 0, "A", "full", 0.5).set("M-append", "AB", 0, "A", "full", 0.5))
    assert q.rho("M-append", "AB", 0) == 1.0 and q.ret("M-append", "AB", 0)  # G_first(V1) = 0.50 is evaluable (>=)
    q = quantities(Spec().set("M1", "AB", 0, "A", "full", 0.4999).set("M-append", "AB", 0, "A", "full", 0.4999))
    assert q.rho("M-append", "AB", 0) is None and q.forgetting("M-append", "AB", 0) is None and not q.ret("M-append", "AB", 0)  # NOT EVALUABLE: FIRST NOT ACQUIRED


def test_forgetting_pressure_needs_four_of_six_and_defined_rho() -> None:
    s = Spec()
    for r, o in CELLS[:3]:
        s.set("M-seq", o, r, o[0], "full", 0.95)  # three cells with no forgetting
    assert L.forgetting_pressure(quantities(s))["cells"] == 3 and not L.forgetting_pressure(quantities(s))["holds"]
    s2 = Spec()
    for r, o in CELLS[:2]:
        s2.set("M-seq", o, r, o[0], "full", 0.95)
    assert L.forgetting_pressure(quantities(s2))["cells"] == 4 and L.forgetting_pressure(quantities(s2))["holds"]
    s3 = Spec().set("M-seq", "AB", 0, "B", "full", 0.4999)  # second capability not acquired by the unprotected store
    assert L.forgetting_pressure(quantities(s3))["cells"] == 5
    s4 = Spec().all_cells("M1", "first", "full", 0.4)  # rho undefined: no cell counts
    assert L.forgetting_pressure(quantities(s4))["cells"] == 0
    assert L.forgetting_pressure(quantities(Spec().set("D-seq", "AB", 0, "A", "full", 0.1)))["d_seq_rho"]["0AB"] == pytest.approx(0.1 / 0.9)  # printed beside, never counted


# --- GENERAL-QUALITY and the milestone -----------------------------------------------------------------------------------------------------------
def test_general_quality_rows_and_edge() -> None:
    assert L.general_quality(quantities())["label"] == "PRESERVED"
    reg = build()
    reg.values[key("M-append", "BA", 2, "gen:first_marker")] = 0.02  # exactly the limit: PRESERVED (<=)
    assert L.general_quality(Quantities(reg, quantities().th))["label"] == "PRESERVED"
    reg.values[key("M-append", "BA", 2, "gen:first_marker")] = 0.0201
    r = L.general_quality(Quantities(reg, quantities().th))
    assert r["label"] == "NOT PRESERVED" and list(r["over"]) == ["2BA:first_marker"]
    reg.values.pop(key("M-append", "AB", 0, "gen:token64"))
    assert L.general_quality(Quantities(reg, quantities().th))["label"] == "NOT EVALUABLE"  # missing is never NOT PRESERVED
    reg2 = build()
    reg2.values[key("M-append", "AB", 0, "gen:token64")] = float("nan")
    assert L.general_quality(Quantities(reg2, quantities().th))["label"] == "NOT EVALUABLE" and L.study_status(reg2)["status"] == L.STOP_NONFINITE


def test_milestone_rows() -> None:
    def ms(spec: Spec | None = None, gen_over: bool = False, mii_gen_over: bool = False, **kw):  # type: ignore[no-untyped-def]
        reg = build(spec, **kw)
        if gen_over:
            reg.values[key("M-append", "AB", 1, "gen:token64")] = 0.05
        if mii_gen_over:
            reg.values[key("M-ii", "AB", 1, "gen:token64")] = 0.05
        return L.derive_all(Quantities(reg, quantities().th))["MILESTONE"]["label"]

    assert ms() == "SUPPORTED (append-frozen + consolidation)"
    assert ms(mii_gen_over=True) == "SUPPORTED (append-frozen)"  # M-ii fails the GEN check: no suffix
    assert ms(Spec().set("M-ii", "AB", 0, "A", "full", 0.5)) == "SUPPORTED (append-frozen)"  # MODIFICATION not RETAINS
    assert ms(gen_over=True) == "WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE"
    assert ms(Spec().all_cells("M-seq", "first", "full", 0.9)) == "NOT ESTABLISHED"  # retention not challenged
    assert ms(Spec().all_cells("M1", "first", "full", 0.1), gen_over=True) == "NOT ESTABLISHED"  # a negative acquisition is not WITHHELD
    reg = build()
    reg.values.pop(key("M-append", "AB", 0, "gen:token64"))
    assert L.derive_all(Quantities(reg, quantities().th))["MILESTONE"]["label"] == "NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE)"
    reg3 = build()
    reg3.values.pop(key("M-ii", "AB", 0, "gen:token64"))
    assert L.derive_all(Quantities(reg3, quantities().th))["MILESTONE"]["label"] == "SUPPORTED (append-frozen)"  # the suffix is not given if an M-ii reading is not evaluable
    # a result printed BY CONSTRUCTION satisfies no rule: M-sep and D-sep scores changed to zero change nothing
    base = L.derive_all(quantities())
    zeroed = Spec()
    for r in (0, 1, 2):
        for c in ("A", "B"):
            for arm in ("M-sep", "D-sep"):
                zeroed.set(arm, "-", r, c, "full", 0.0)
    assert L.derive_all(quantities(zeroed)) == base  # no rule reads a score that is printed BY CONSTRUCTION


def test_milestone_carries_the_lookup_baseline_when_lookup_suffices() -> None:
    s = Spec()
    for r in (0, 1, 2):
        for c in ("A", "B"):
            s.set("E-table", "-", r, c, "full", 0.88)  # within 0.03 of M-append's 0.90
    d = L.derive_all(quantities(s))
    assert d["AGAINST-LOOKUP"]["label"] == "LOOKUP SUFFICES" and d["AGAINST-LOOKUP"]["baseline"] == "E-table"
    assert d["MILESTONE"]["label"] == "SUPPORTED (append-frozen + consolidation)" and d["MILESTONE"]["line_tail"] == " — a lookup baseline does as well: E-table"


# --- AGAINST-DENSE ---------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("deltas", "want"),
    [([0.05] * 6, "MEMORY AHEAD"), ([0.0499] * 6, "NOT DISTINGUISHED"), ([-0.05] * 6, "DENSE AHEAD"), ([0.05, 0.05, 0.05, 0.05, 0.05, 0.0499], "MIXED"), ([0.05, -0.05, 0.0, 0.0, 0.0, 0.0], "MIXED"), ([0.01, -0.01, 0.0, 0.02, 0.0, -0.04], "NOT DISTINGUISHED")],
)
def test_delta_label_rows(deltas: list[float], want: str) -> None:
    assert L.delta_label(deltas, 0.05) == want


def test_against_dense_pair_is_two_labels_and_the_guard() -> None:
    r = L.against_dense(quantities())
    assert r["value"] == "acquisition: MEMORY AHEAD; retention: NOT DISTINGUISHED" and "merged" not in r
    s = Spec().all_cells("D-append", "second", "full", 0.4)  # dense second stage learned little: rho near 1 trivially: the guard
    r2 = L.against_dense(quantities(s))
    assert r2["acquisition"] == "MEMORY AHEAD" and r2["retention"] == "NOT EVALUABLE" and r2["value"] == "acquisition: MEMORY AHEAD; retention: NOT EVALUABLE"
    s2 = Spec().set("D1", "AB", 0, "A", "full", 0.4)  # D1 did not acquire: the dense rho is undefined in that cell
    assert L.against_dense(quantities(s2))["retention"] == "NOT EVALUABLE"
    s3 = Spec().all_cells("D-append", "first", "full", 0.30)  # dense forgets: memory's rho 1.0 against 0.33
    assert L.against_dense(quantities(s3))["retention"] == "MEMORY AHEAD"
    s4 = Spec().all_cells("D-append", "second", "full", 0.99)
    assert L.against_dense(quantities(s4))["acquisition"] == "DENSE AHEAD"  # 0.90 - 0.99 = -0.09
    seq = L.derive_all(quantities())["AGAINST-DENSE (M-seq vs D-seq)"]
    assert seq["acquisition"] == "NOT DISTINGUISHED" and seq["retention"] == "NOT DISTINGUISHED"  # same numbers in the defaults
    assert L.against_dense(quantities(teacher_full={"A": 0.2}))["value"] == "acquisition: NOT EVALUABLE; retention: NOT EVALUABLE"


# --- AGAINST-LOOKUP ------------------------------------------------------------------------------------------------------------------------------
def test_against_lookup_rows_boundaries_and_naming() -> None:
    s = Spec()
    for r in (0, 1, 2):
        for c in ("A", "B"):
            s.set("R-icl", "-", r, c, "full", 0.87)  # exactly 0.03 below M-append's 0.90: SUFFICES (>=)
    r1 = L.against_lookup(quantities(s))
    assert r1["label"] == "LOOKUP SUFFICES" and r1["baseline"] == "R-icl"
    s2 = Spec().set("R-nn", "-", 1, "B", "full", 0.8700001)
    assert L.against_lookup(quantities(s2))["label"] == "MIXED"  # one reading within 0.03 does not make every cell sufficient
    s3 = Spec()
    for r in (0, 1, 2):
        for c in ("A", "B"):
            s3.set("E-table", "-", r, c, "full", 0.85)  # s - b = 0.05: ADDS (>=)
    assert L.against_lookup(quantities(s3))["label"] == "MEMORY ADDS OVER LOOKUP"
    s4 = Spec().set("E-table", "-", 0, "A", "full", 0.8501)  # one reading just inside 0.05
    assert L.against_lookup(quantities(s4))["label"] == "MIXED"
    s5 = Spec().set("R-gloss", "-", 1, "A", "full", 0.60)
    r5 = L.against_lookup(quantities(s5))
    assert r5["label"] == "MEMORY ADDS OVER LOOKUP" and any(x["best"] == "R-gloss" and x["b"] == 0.60 for x in r5["readings"]) and r5["baseline"] == "E-table"  # named by frequency
    assert len(r5["readings"]) == 12  # 6 cells x 2 capabilities


# --- MODIFICATION (M-ii) -----------------------------------------------------------------------------------------------------------------------------
def mod(**kw):  # type: ignore[no-untyped-def]
    spec, raw = kw.pop("spec", Spec()), kw.pop("raw", {})
    spec.raw.update(raw)
    return L.modification(quantities(spec, **kw))


def test_modification_rows() -> None:
    assert mod()["label"] == "RETAINS UNDER MODIFICATION"
    rej = mod(raw={key("M-ii", "AB", 0, "dcon:A"): 0.579, key("M-ii", "BA", 1, "dcon:B"): 0.50})
    assert rej["label"] == "CONSOLIDATION-REJECTED" and rej["count"] == 2 and rej["pinned_append_snapshot_used_in_rejected_cells"]
    assert mod(raw={key("M-ii", "AB", 0, "dcon:A"): 0.58})["label"] != "CONSOLIDATION-REJECTED"  # exactly M-append - 0.02 passes
    few = Spec()
    for r, o in (("0", "AB"), ("1", "BA"), ("2", "AB")):
        few.set("M1", o, int(r), o[0], "full", 0.4)
    assert mod(spec=few)["label"] == "NOT EVALUABLE" and mod(spec=few)["evaluable_cells"] == 3
    assert mod(spec=Spec().all_cells("M-ii", "first", "full", 0.3))["label"] == "FORGETS UNDER MODIFICATION"
    assert mod(raw={key("M-ii", "AB", 0, "modification"): 0.09})["label"] == "RETENTION BY INERTIA"
    assert mod(spec=Spec().set("M-ii", "AB", 0, "A", "full", 0.60))["label"] == "INTERMEDIATE"  # rho 0.667 < 0.90 in one cell, not every cell below 0.70


# --- study status --------------------------------------------------------------------------------------------------------------------------------
def test_study_status_order_and_refusals() -> None:
    reg = build()
    required = set(reg.values)
    assert L.study_status(reg, required=required) == {"status": "OK", "why": "", "derive": True}
    assert L.study_status(reg, engineering_failure=["gate G4"], item_errors=["x"])["status"] == "ENGINEERING-FAILURE"
    assert L.study_status(reg, item_errors=["cell M-append 0AB: out of memory"])["status"] == L.STOP_ITEMS
    reg2 = build()
    reg2.values[key("M-append", "AB", 0, "s:E_A")] = float("inf")
    assert L.study_status(reg2, recompute_failed=[(0, "AB")])["status"] == L.STOP_NONFINITE  # non-finite before recomputation
    assert L.study_status(reg, recompute_failed=[(0, "AB")])["status"] == L.STOP_RECOMPUTATION
    reg3 = build()
    reg3.values.pop(key("M-seq", "BA", 2, "s:E_A"))
    st = L.study_status(reg3, required=required)
    assert st["status"] == "INCOMPLETE" and not st["derive"] and "no denominator is reduced" in st["why"]
    with pytest.raises(Missing):
        Quantities(reg3, quantities().th).score("M-seq", "BA", 2, "A")
    assert all(not L.study_status(reg, item_errors=["e"])[k] for k in ("derive",))


def test_registry_refuses_a_second_record_under_one_key_and_keys_carry_every_name() -> None:
    reg = build()
    with pytest.raises(ValueError, match="already registered"):
        reg.put("M-append", "AB", 0, "s:E_A", 0.5)
    assert key("M-append", "AB", 0, "s:E_A") != key("M-append", "BA", 0, "s:E_A") != key("M-seq", "BA", 0, "s:E_A")
    with pytest.raises(ValueError):
        key("M-append", "XY", 0, "s:E_A")
    names = {key(a, o, r, rd) for a in ("M-append", "D-append") for o in ("AB", "BA") for r in (0, 1) for rd in ("s:E_A", "s:E_B", "sub:value:E_A")}
    assert len(names) == 24
