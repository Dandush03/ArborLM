# ruff: noqa: E501
"""P10IR analysis and report tests on synthetic registries with known answers (ADR-0029 section 13, 'Analysis tests'): every row of sections 8.3 and 8.4, MIXED-PANEL, MIXED, cell-level
NOT EVALUABLE, CELL-DEPENDENT, CHECKPOINT-DEPENDENT per component, NO READ-TIME CAUSE IDENTIFIED, both STILL LEARNING tags, every value of R-CONFIRM-TREE and R-CONFIRM-INDEX, every descriptive
section, and the read-qualified registry keys. The values are typed in ``studies/p10ir/synthetic.py`` to have known answers; they are not measurements. Self-check only: not independent review, not
Astra validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import analysis, core, labels, report, synthetic  # noqa: E402
from studies.p10ir.registry import KeyCollision, Registry, scope_ok  # noqa: E402

CFG = core.load_config()
A1, A2 = core.STAGE_A1, core.STAGE_A2
PRIMARY = [s.name for s in core.primary_cells(CFG)]
DEFAULT = (labels.CONTENT, labels.NOT_APPROACH)


TEST_SEEDS = core.i64_seeds(CFG, test=True)  # the unit tests never read an index with the registered seeds 298001-298003


def label_of(arm: str, spec: core.CellSpec, draw: int) -> str:
    """Labels that are NOT the config's derivation (as the rehearsal's items are not): the analysis must take its labels from what it is given (audit R2, A12)."""
    return f"X_{arm}_{spec.name.replace('/', '-')}_d{draw}"


def run(stage: str = A1, plan: dict[tuple[str, str], tuple[Any, Any]] | None = None, **kw: Any) -> dict[str, Any]:
    reg = synthetic.full_registry(stage, plan, CFG, label_of, i64_seeds=TEST_SEEDS)
    return analysis.analyze_stage(reg, stage, CFG, plateau=synthetic.plateau_series(CFG) if stage == A1 else None, label_of=label_of, i64_seeds=TEST_SEEDS, **kw)


def cell(a: dict[str, Any], name: str, cp: str, comp: str) -> str:
    return str(a["cells"][name]["checkpoints"][cp][comp]["label"])


# --- registry keys ----------------------------------------------------------------------------------------------------------------------------
def test_registry_keys_carry_the_read_name_so_two_reads_of_one_cell_never_share_a_key() -> None:
    reg = Registry()
    a = synthetic.read_record(A1, "P_T-OQ_f8192_n4096_d1_i2101", 8192, "T0", (3.0, 3.0))
    b = synthetic.read_record(A1, "P_T-OQ_f8192_n4096_d1_i2101", 8192, "T1", (3.5, 3.5))
    ka, kb = reg.put_read(a), reg.put_read(b)
    assert ka != kb and ka.endswith("|T0") and kb.endswith("|T1")
    with pytest.raises(KeyCollision):
        reg.put_read(a)  # one read of one cell twice
    assert reg.read(A1, "P_T-OQ_f8192_n4096_d1_i2101", 8192, "T1") == b
    with pytest.raises(ValueError):
        core.read_key(A1, "cell", 8192, "T9")  # not a read name
    # every read name of every kind the study makes is a valid key part, and I64's index seed is part of the key
    names = [*core.TREE_NAMED, *core.FLAT_NAMED, core.tv_name(4, "on"), core.tv_name(4, "off"), core.i64_name(256, 938901), core.i64_name(256, 938902)]
    keys = {core.read_key(A1, "c", 1, n) for n in names}
    assert len(keys) == len(names)
    assert core.parse_read_key(core.read_key(A1, "c", 1, "I64@256/s938901")) == (A1, "c", 1, "I64@256/s938901")


def test_the_registry_holds_one_record_per_read_of_a_full_synthetic_stage() -> None:
    reg = synthetic.full_registry(A1, None, CFG, label_of, i64_seeds=TEST_SEEDS)
    assert len(set(reg.reads)) == len(reg.reads)
    # 7 cells x 4 checkpoints x 5 replicates; each tree checkpoint has 5 named reads plus the sweep reads not aliased to them
    tree_reads = [k for k in reg.reads if "_T-OQ_" in k]
    assert all(core.parse_read_key(k)[3] for k in tree_reads)
    assert any(k.endswith("|Tv1_on") for k in tree_reads) and any(k.endswith("|Tv1_off") for k in tree_reads)
    assert not any(k.endswith("|Tv2_on") for k in tree_reads)  # v = 2 is T0 / T1; v = N/256 is T3 / T2: never a second record


# --- section 8.3: every row of the tree table, at known cells -----------------------------------------------------------------------------------
TREE_PLAN = {
    ("2K/1K", "U_P"): labels.NO_GAP, ("2K/1K", "RUN"): labels.MIXED_PANEL, ("2K/4K", "U_P"): labels.PRIORS_AND_CANDIDATES, ("2K/4K", "RUN"): labels.PRIORS, ("8K/16K", "U_P"): labels.CANDIDATES,
    ("8K/16K", "RUN"): labels.JOINT, ("8K/1K", "U_P"): labels.EXACT_SEARCH_HARMS, ("8K/1K", "RUN"): labels.CONTENT, ("32K/4K", "U_P"): labels.NOT_IDENTIFIED, ("32K/4K", "RUN"): labels.NOT_EVALUABLE,
}  # fmt: skip


def test_every_tree_row_is_reached_at_a_cell_with_its_known_label() -> None:
    a = run(plan={k: (v, labels.NOT_APPROACH) for k, v in TREE_PLAN.items()})
    reached = set()
    for (name, cp), want in TREE_PLAN.items():
        rows = {r["row"] for r in a["cells"][name]["checkpoints"][cp]["tree"]["replicates"]}
        assert rows == {want}, (name, cp)  # every replicate of the cell reached the row
        reached |= rows
        # ruling 2: MIXED-PANEL is a replicate row only; a cell of five MIXED-PANEL replicates is MIXED
        assert cell(a, name, cp, "tree") == (labels.MIXED if want == labels.MIXED_PANEL else want), (name, cp)
    assert reached == set(labels.TREE_ROWS)


def test_fully_and_partly_and_the_mainly_tag_are_printed() -> None:
    a = run(plan={("2K/4K", "U_P"): (["PARTLY:PRIORS"] * 5, labels.NOT_APPROACH), ("2K/4K", "RUN"): (labels.PRIORS, labels.NOT_APPROACH)})
    partly = a["cells"]["2K/4K"]["checkpoints"]["U_P"]["tree"]["replicates"][0]
    fully = a["cells"]["2K/4K"]["checkpoints"]["RUN"]["tree"]["replicates"][0]
    assert (partly["row"], partly["suffix"]) == (labels.PRIORS, labels.PARTLY) and (fully["row"], fully["suffix"]) == (labels.PRIORS, labels.FULLY)
    assert fully["tags"]["mainly"] in ("weights", "selection", "equal")
    assert cell(a, "2K/4K", "U_P", "tree") == labels.PRIORS  # the suffix is printed and never compared


def test_suffix_differences_do_not_break_the_four_of_five_rule() -> None:
    rows = ["PARTLY:PRIORS", "PARTLY:PRIORS", labels.PRIORS, labels.PRIORS, labels.PRIORS]
    a = run(plan={("2K/4K", "U_P"): (rows, labels.NOT_APPROACH)})
    assert cell(a, "2K/4K", "U_P", "tree") == labels.PRIORS


# --- section 8.4: every row of the index table ---------------------------------------------------------------------------------------------------
def test_every_index_row_with_its_median_c_star_and_shares() -> None:
    plan = {
        ("8K/16K", "U_P"): (labels.CONTENT, labels.SPARSE_APPROACHES), ("8K/16K", "RUN"): (labels.CONTENT, labels.ONLY_ABOVE_512),
        ("2K/4K", "U_P"): (labels.CONTENT, labels.NOT_APPROACH), ("2K/4K", "RUN"): (labels.CONTENT, labels.NOT_EVALUABLE),
    }  # fmt: skip
    a = run(plan=plan)
    assert cell(a, "8K/16K", "U_P", "index") == labels.SPARSE_APPROACHES
    ck = a["cells"]["8K/16K"]["checkpoints"]["U_P"]["index"]
    assert ck["c_star_median"] == 256.0 and ck["c_star_share_of_N"] == 256 / 16384 and ck["descriptive"]["N_over_8"] == 2048.0 and ck["replicates_without_c_star"] == []
    assert cell(a, "8K/16K", "RUN", "index") == labels.ONLY_ABOVE_512
    assert a["cells"]["8K/16K"]["checkpoints"]["RUN"]["index"]["c_star_median"] == 1024.0
    assert cell(a, "2K/4K", "U_P", "index") == labels.NOT_APPROACH
    assert a["cells"]["2K/4K"]["checkpoints"]["U_P"]["index"]["replicates_without_c_star"] == [1, 2, 3, 4, 5]
    assert cell(a, "2K/4K", "RUN", "index") == labels.NOT_EVALUABLE


def test_infeasible_budgets_and_visits_are_not_applicable_items_never_silently_skipped() -> None:
    a = run()
    shallow = a["cells"]["2K/1K"]
    assert shallow["shallow"] and any(t.startswith("SHALLOW") for t in shallow["tags"])
    d = shallow["checkpoints"]["U_P"]
    assert d["index"]["descriptive"]["budgets"]["1024"]["status"] == "NOT APPLICABLE" and d["index"]["descriptive"]["budgets"]["2048"]["status"] == "NOT APPLICABLE"
    assert d["index"]["descriptive"]["budgets"]["512"]["status"] == "READ"
    assert d["tree"]["descriptive"]["sweep"]["8"]["status"] == "NOT APPLICABLE"  # v = 8 does not exist at 1,024 slots (4 branches)
    assert d["tree"]["descriptive"]["sweep"]["4"]["status"].endswith("(as T3 / T2)")  # v = 4 is T3 / T2 there
    big = a["cells"]["8K/16K"]["checkpoints"]["U_P"]
    assert all(big["index"]["descriptive"]["budgets"][str(c)]["status"] == "READ" for c in (128, 256, 512, 1024, 2048))
    assert big["tree"]["descriptive"]["sweep"]["8"]["status"] == "READ"


# --- section 8.2: replicates and cells -----------------------------------------------------------------------------------------------------------
def test_mixed_and_cell_level_not_evaluable_and_one_tolerated_replicate() -> None:
    P, C, NE = labels.PRIORS, labels.CONTENT, labels.NOT_EVALUABLE
    plan = {
        ("2K/1K", "U_P"): ([P, P, P, C, C], DEFAULT[1]), ("2K/1K", "RUN"): ([P, P, P, P, NE], DEFAULT[1]), ("2K/4K", "U_P"): ([P, P, P, NE, NE], DEFAULT[1]),
        ("2K/4K", "RUN"): ([P, P, P, P, C], DEFAULT[1]), ("8K/16K", "U_P"): ([P, P, P, NE, C], DEFAULT[1]), ("8K/16K", "RUN"): (["WEAK"] * 5, DEFAULT[1]),
    }  # fmt: skip
    a = run(plan=plan)
    assert cell(a, "2K/1K", "U_P", "tree") == labels.MIXED
    assert cell(a, "2K/1K", "RUN", "tree") == P  # one NOT EVALUABLE replicate, four equal
    assert cell(a, "2K/4K", "U_P", "tree") == NE  # two of five
    assert cell(a, "2K/4K", "RUN", "tree") == P
    assert cell(a, "8K/16K", "U_P", "tree") == labels.MIXED
    assert cell(a, "8K/16K", "RUN", "tree") == NE  # WEAK REFERENCE counts as NOT EVALUABLE in every replicate
    assert a["cells"]["8K/16K"]["checkpoints"]["RUN"]["tree"]["replicates"][0]["reason"] == labels.WEAK


def test_gate_scopes_tree_f0_and_index() -> None:
    reg = synthetic.full_registry(A1, None, CFG, label_of, i64_seeds=TEST_SEEDS)
    spec = core.spec_of(8192, 16384, CFG)
    of = label_of
    upd = spec.u_p
    # an index-only failure (the F-OQ item's index gate) voids the index label of the replicate and leaves the tree label
    f_item = reg.item(A1, of("F-OQ", spec, 1), upd)
    assert f_item is not None
    f_item["gates"]["i256_counts"]["passed"] = False
    assert not scope_ok(f_item, "index")[0] and scope_ok(f_item, "f0")[0]
    assert labels.tree_replicate(analysis.tree_rep(reg, A1, spec, 1, upd, of), core.Thresholds.from_config(CFG)).row == labels.CONTENT
    assert analysis.index_rep(reg, A1, spec, 1, upd, of, CFG, TEST_SEEDS).evaluable is False
    # a F0 failure voids both
    f_item["gates"]["f0_counts"]["passed"] = False
    assert analysis.tree_rep(reg, A1, spec, 1, upd, of).evaluable is False
    # a T-OQ failure voids the tree label only
    t_item = reg.item(A1, of("T-OQ", spec, 2), upd)
    assert t_item is not None
    t_item["gates"]["t0_path"]["passed"] = False
    assert analysis.tree_rep(reg, A1, spec, 2, upd, of).evaluable is False and analysis.index_rep(reg, A1, spec, 2, upd, of, CFG, TEST_SEEDS).evaluable is True
    # a missing or incomplete item is not evaluable, never silently ok
    assert scope_ok(None, "tree") == (False, "no item record")
    assert scope_ok({"complete": False}, "tree")[0] is False


# --- section 9: R-DIAGNOSIS ------------------------------------------------------------------------------------------------------------------------
def uniform_plan(tree: Any, index: Any) -> dict[tuple[str, str], tuple[Any, Any]]:
    return {(c, cp): (tree, index) for c in PRIMARY for cp in ("U_P", "RUN")}


def test_r_diagnosis_a_single_row_per_component_recommends_its_action() -> None:
    a = run(plan=uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES))
    rd = a["r_diagnosis"]
    assert rd["evaluable"] and rd["pair"] == [labels.PRIORS, labels.SPARSE_APPROACHES]
    assert rd["recommended"] == {"tree": "Redesign how routing scores enter the read", "index": "Investigate a separately trained sparse index"}


def test_cell_dependent_and_checkpoint_dependent_per_component_and_the_two_components_move_apart() -> None:
    plan = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    plan[("32K/16K", "U_P")] = (labels.CONTENT, labels.NOT_APPROACH)
    plan[("32K/16K", "RUN")] = (labels.CONTENT, labels.NOT_APPROACH)
    plan[("8K/4K", "RUN")] = (labels.PRIORS, labels.SPARSE_APPROACHES)
    plan[("32K/16K", "RUN")] = (labels.CONTENT, labels.SPARSE_APPROACHES)
    rd = run(plan=plan)["r_diagnosis"]
    assert rd["components"]["tree"]["value"] == labels.CELL_DEPENDENT and rd["components"]["tree"]["at"]["U_P"]["cells"] == {"8K/4K": labels.PRIORS, "32K/16K": labels.CONTENT}
    assert rd["components"]["index"]["value"] == labels.CHECKPOINT_DEPENDENT  # NOT APPROACH at U_P, SPARSE at the run length
    assert rd["recommended"] == {"tree": None, "index": None}
    # a stable tree component is not lost because the index label moves
    plan2 = uniform_plan(labels.CANDIDATES, labels.NOT_APPROACH)
    plan2[("8K/4K", "RUN")] = (labels.CANDIDATES, labels.SPARSE_APPROACHES)
    plan2[("32K/16K", "RUN")] = (labels.CANDIDATES, labels.SPARSE_APPROACHES)
    rd2 = run(plan=plan2)["r_diagnosis"]
    assert rd2["components"]["tree"]["value"] == labels.CANDIDATES and rd2["components"]["index"]["value"] == labels.CHECKPOINT_DEPENDENT
    assert rd2["recommended"]["tree"] == "Improve the router and candidate coverage" and rd2["recommended"]["index"] is None


def test_checkpoint_dependent_tree_component() -> None:
    plan = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    plan[("8K/4K", "RUN")] = (labels.CONTENT, labels.NOT_APPROACH)
    plan[("32K/16K", "RUN")] = (labels.CONTENT, labels.NOT_APPROACH)
    rd = run(plan=plan)["r_diagnosis"]
    assert rd["components"]["tree"]["value"] == labels.CHECKPOINT_DEPENDENT and rd["recommended"]["tree"] is None


@pytest.mark.parametrize("tree", [labels.EXACT_SEARCH_HARMS, labels.NOT_IDENTIFIED])
def test_no_read_time_cause_identified(tree: str) -> None:
    rd = run(plan=uniform_plan(tree, labels.NOT_APPROACH))["r_diagnosis"]
    assert rd["no_read_time_cause_identified"] and rd["banner"] == labels.NO_READ_TIME_CAUSE and rd["recommended"] == {"tree": None, "index": None}
    rd2 = run(plan=uniform_plan(labels.CONTENT, labels.NOT_APPROACH))["r_diagnosis"]
    assert not rd2["no_read_time_cause_identified"] and rd2["recommended"]["tree"] == "Improve memory training and representation"  # CONTENT keeps its action


def test_r_diagnosis_is_not_evaluable_when_either_primary_cell_of_either_component_is() -> None:
    plan = uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES)
    plan[("32K/16K", "RUN")] = (labels.PRIORS, labels.NOT_EVALUABLE)
    rd = run(plan=plan)["r_diagnosis"]
    assert not rd["evaluable"] and rd["value"] == labels.NOT_EVALUABLE and rd["pair"] is None
    assert ["index", "32K/16K", "RUN"] in rd["not_evaluable_cells"]
    assert rd["components"]["tree"]["value"] == labels.PRIORS  # both components are still printed
    plan3 = uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES)
    plan3[("8K/4K", "U_P")] = (labels.NOT_EVALUABLE, labels.SPARSE_APPROACHES)
    rd3 = run(plan=plan3)["r_diagnosis"]
    assert not rd3["evaluable"] and rd3["components"]["index"]["value"] == labels.SPARSE_APPROACHES  # a T-OQ gate failure voids R-DIAGNOSIS as a whole (section 9 item 1)


def test_loaded_cells_are_printed_only_and_recommend_nothing() -> None:
    plan = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    plan[("8K/1K", "U_P")] = (labels.PRIORS, labels.SPARSE_APPROACHES)
    plan[("8K/1K", "RUN")] = (labels.CONTENT, labels.SPARSE_APPROACHES)
    a = run(plan=plan)
    ld = a["r_diagnosis_loaded"]
    assert ld["printed_only"] and set(ld["cells"]) == {"8K/1K", "32K/4K"} and ld["cells"]["8K/1K"]["U_P"] == {"tree": labels.PRIORS, "index": labels.SPARSE_APPROACHES}
    assert "recommend" not in str(ld["cells"]) and a["r_diagnosis"]["pair"] == [labels.PRIORS, labels.NOT_APPROACH]  # nothing in it enters R-DIAGNOSIS


def test_trajectory_checkpoints_are_printed_and_enter_no_label() -> None:
    a = run(plan={("8K/4K", "TRAJ1"): (labels.JOINT, labels.SPARSE_APPROACHES)})
    ck = a["cells"]["8K/4K"]["checkpoints"]
    assert ck["TRAJ1"]["descriptive_only"] and ck["TRAJ1"]["tree"]["label"] == labels.JOINT and ck["TRAJ1"]["update"] == 16384
    assert a["r_diagnosis"]["pair"] == [labels.CONTENT, labels.NOT_APPROACH]
    assert set(ck) == {"U_P", "RUN", "TRAJ1", "TRAJ2"}
    assert a["cells"]["32K/16K"]["checkpoints"]["RUN"]["update"] == 98304 and a["cells"]["32K/4K"]["checkpoints"]["RUN"]["update"] == 786432


# --- the plateau check and the STILL LEARNING tags ----------------------------------------------------------------------------------------------------
def test_both_still_learning_tags() -> None:
    reg = synthetic.full_registry(A1, None, CFG, label_of, i64_seeds=TEST_SEEDS)
    tags = {}
    for failing, key in (({"8K/4K:tree": [1, 2]}, "tree"), ({"8K/4K:flat": [3, 4, 5]}, "flat"), ({"8K/4K:tree": [1]}, "one"), ({}, "none")):
        a = analysis.analyze_stage(reg, A1, CFG, label_of=label_of, i64_seeds=TEST_SEEDS, plateau=synthetic.plateau_series(CFG, failing=failing))
        tags[key] = a["cells"]["8K/4K"]["checkpoints"]["RUN"]["plateau"]["tags"]
        assert "plateau" not in a["cells"]["8K/4K"]["checkpoints"]["U_P"]  # the check is made at the run length only
    assert tags["tree"] == ["TREE STILL LEARNING"] and tags["flat"] == ["FLAT STILL LEARNING"] and tags["one"] == [] and tags["none"] == []
    both = analysis.analyze_stage(reg, A1, CFG, label_of=label_of, i64_seeds=TEST_SEEDS, plateau=synthetic.plateau_series(CFG, failing={"32K/16K:tree": [1, 2], "32K/16K:flat": [1, 2]}))
    assert both["cells"]["32K/16K"]["checkpoints"]["RUN"]["plateau"]["tags"] == ["TREE STILL LEARNING", "FLAT STILL LEARNING"]
    assert "plateau" not in both["cells"]["2K/4K"]["checkpoints"]["RUN"]  # primary cells only
    # the tag does not change the label (printed, never compared)
    assert both["cells"]["32K/16K"]["checkpoints"]["RUN"]["tree"]["label"] == labels.CONTENT


# --- R-CONFIRM, every value --------------------------------------------------------------------------------------------------------------------------
def test_every_value_of_r_confirm_through_the_analysis() -> None:
    p = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    a1 = run(A1, p)
    same = run(A2, p)
    got = analysis.analyze_all(a1, same)["r_confirm"]
    assert got["R-CONFIRM-TREE"]["value"] == labels.CONFIRMED and got["R-CONFIRM-INDEX"]["value"] == labels.CONFIRMED
    diff = run(A2, uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES))
    got = analysis.analyze_all(a1, diff)["r_confirm"]
    assert (got["R-CONFIRM-TREE"]["value"], got["R-CONFIRM-INDEX"]["value"]) == (labels.CONFIRMED, labels.NOT_CONFIRMED)
    got = analysis.analyze_all(a1, run(A2, uniform_plan(labels.CONTENT, labels.NOT_APPROACH)))["r_confirm"]
    assert got["R-CONFIRM-TREE"]["value"] == labels.NOT_CONFIRMED and got["R-CONFIRM-TREE"]["a1"] == labels.PRIORS and got["R-CONFIRM-TREE"]["a2"] == labels.CONTENT
    assert analysis.analyze_all(a1, None)["r_confirm"]["R-CONFIRM-TREE"]["value"] == labels.NOT_RUN
    assert analysis.analyze_all(a1, same, a2_complete=False)["r_confirm"]["R-CONFIRM-INDEX"]["value"] == labels.NOT_RUN
    ne2 = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    ne2[("8K/4K", "U_P")] = (labels.NOT_EVALUABLE, labels.NOT_APPROACH)
    got = analysis.analyze_all(a1, run(A2, ne2))["r_confirm"]
    assert got["R-CONFIRM-TREE"]["value"] == labels.NOT_EVALUABLE
    ne1 = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    ne1[("8K/4K", "U_P")] = (labels.NOT_EVALUABLE, labels.NOT_APPROACH)
    got = analysis.analyze_all(run(A1, ne1), same)["r_confirm"]
    assert got["R-CONFIRM-TREE"]["value"] == labels.NOT_APPLICABLE and got["R-CONFIRM-INDEX"]["value"] == labels.NOT_APPLICABLE
    full = analysis.analyze_all(a1, same)
    assert full["statement_allowed"]["caused_by_a_named_factor_at_read_time"] is True and full["statement_allowed"]["training_time_causes"] is False
    assert analysis.analyze_all(a1, diff)["A1"]["r_diagnosis"] == a1["r_diagnosis"]  # R-CONFIRM does not change R-DIAGNOSIS


def test_a2_uses_the_two_primary_cells_at_u_p_and_run_only_and_its_plateau_is_not_checked() -> None:
    a2 = run(A2, uniform_plan(labels.PRIORS, labels.NOT_APPROACH))
    assert set(a2["cells"]) == set(PRIMARY) and set(a2["cells"]["8K/4K"]["checkpoints"]) == {"U_P", "RUN"}
    assert a2["stage_tag"] == core.A2_TAG and a2["cells"]["8K/4K"]["checkpoints"]["RUN"]["plateau"]["status"] == "NOT CHECKED"
    assert "bridge" not in str(a2["cells"]["8K/4K"]["checkpoints"]["U_P"]["tree"]["replicates"])
    labels_used = {core.bridge_label("T-OQ", 8192, 4096, d, 8192, 49152, CFG) for d in range(1, 6)}
    assert all(label.endswith(f"i33060{d}") for d, label in enumerate(sorted(labels_used), start=1))


# --- descriptive sections --------------------------------------------------------------------------------------------------------------------------------
def test_every_descriptive_section_is_present() -> None:
    a = run(plan={("8K/4K", "U_P"): (labels.PRIORS, labels.SPARSE_APPROACHES)}, context={"D-OQ a_use": {"8K/4K": 0.9}})
    ck = a["cells"]["8K/4K"]["checkpoints"]["U_P"]
    d = ck["tree"]["descriptive"]
    assert set(d["reads"]) == {"T0", "T1", "T1w", "T2", "T3", "F0"} and all(set(v) >= {"i", "a_use", "keys_scored_per_query"} for v in d["reads"].values())
    assert set(d["closure_means"]) == {"g_P", "g_C", "g_PC"} and d["i_f0_minus_t2"] is not None
    assert set(d["sweep"]) == {"1", "2", "4", "8"}
    assert set(d["t0_measures"]) == {"cr8", "cr1", "sr8", "am_c", "am_s", "share_span_both"} and d["t0_measures"]["cr8"] is not None
    assert d["prior_effect"]["i_T1_minus_T0"] > 0 and d["prior_effect"]["share_selection_changed_T0_to_T1"] == 0.4
    assert d["testability"]["share_T3_selection_equals_T0"] == pytest.approx(0.6)
    idx = ck["index"]["descriptive"]
    assert {"F0", "I256@512", "budgets", "N_over_8"} <= set(idx) and idx["I256@512"]["candidates_p99"] is not None
    assert idx["budgets"]["256"]["cr8"] is not None and idx["budgets"]["256"]["candidates_mean"] is not None and idx["budgets"]["256"]["am_c"] is not None
    assert a["context"] == {"D-OQ a_use": {"8K/4K": 0.9}}
    assert "ORACLE-ADDRESSED" in a["standing_tag"] and "DICT DOMINATES" in a["standing_tag"]


def test_recall_seen_before_freeze_is_carried_when_the_seal_is_broken() -> None:
    a = run(seal_broken=True)
    assert a["seal_broken"] and a["cells"]["8K/4K"]["checkpoints"]["U_P"]["tree"]["seal_note"] == "RECALL SEEN BEFORE FREEZE"
    assert "seal_note" not in run()["cells"]["8K/4K"]["checkpoints"]["U_P"]["tree"]


# --- the report ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_report_tags_every_label_prints_every_section_and_claims_no_success() -> None:
    p = uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES)
    full = analysis.analyze_all(run(A1, p), run(A2, p))
    text = report.render(full)
    assert "R-DIAGNOSIS" in text and "R-DIAGNOSIS-LOADED" in text and "R-CONFIRM-TREE: CONFIRMED" in text and "R-CONFIRM-INDEX: CONFIRMED" in text
    assert core.LIMIT_SENTENCE in text and "Astra review: NOT_PERFORMED" in text and "unproven research" in text
    for line in text.splitlines():
        if line.lstrip().startswith(("- tree label:", "- index label:")) or line.startswith("**R-DIAGNOSIS:"):
            assert core.STANDING_TAG in line and (core.A1_TAG in line or core.A2_TAG in line), line
    assert core.A1_TAG in text and core.A2_TAG in text
    for section in ("visit sweep Tv", "testability of the candidate restriction", "prior effect", "median c*", "I64@128", "SHALLOW", "NOT APPLICABLE", "trajectory", "plateau check"):
        assert section in text, section
    assert "success" not in text.lower().replace("not a success", "")
    assert "neither a positive nor a negative result for ArborLM" in text


def test_the_report_prints_no_read_time_cause_banner_and_not_evaluable_cells() -> None:
    p = uniform_plan(labels.NOT_IDENTIFIED, labels.NOT_APPROACH)
    text = report.render(analysis.analyze_all(run(A1, p), None))
    assert labels.NO_READ_TIME_CAUSE in text and "R-CONFIRM-TREE: NOT RUN" in text
    ne = uniform_plan(labels.PRIORS, labels.NOT_APPROACH)
    ne[("8K/4K", "U_P")] = (labels.NOT_EVALUABLE, labels.NOT_APPROACH)
    text2 = report.render(analysis.analyze_all(run(A1, ne), None))
    assert "NOT EVALUABLE (component, cell, checkpoint): tree / 8K/4K / U_P" in text2 and "R-CONFIRM-TREE: NOT APPLICABLE" in text2


# --- rulings 2 and 3, audit R2 and A12 ------------------------------------------------------------------------------------------------------------------
def test_a_cell_with_four_mixed_panel_replicates_is_mixed_and_one_panel_closure_is_not_p() -> None:
    mp = labels.MIXED_PANEL
    a = run(plan={("2K/1K", "U_P"): ([mp, mp, mp, mp, labels.PRIORS], labels.NOT_APPROACH), ("2K/4K", "U_P"): (["ONE-PANEL-CLOSURE"] * 5, labels.NOT_APPROACH)})
    assert cell(a, "2K/1K", "U_P", "tree") == labels.MIXED
    assert [r["row"] for r in a["cells"]["2K/1K"]["checkpoints"]["U_P"]["tree"]["replicates"]].count(mp) == 4
    # T1 closes the gap on Panel A only: P needs both panels, so the replicate is CONTENT (R holds), and that is the cell's label
    one = a["cells"]["2K/4K"]["checkpoints"]["U_P"]["tree"]["replicates"][0]
    assert one["row"] == labels.CONTENT and one["tags"]["P"] is False and cell(a, "2K/4K", "U_P", "tree") == labels.CONTENT


def test_the_analysis_takes_its_labels_from_what_it_is_given_never_from_the_config() -> None:
    reg = synthetic.full_registry(A1, None, CFG, label_of, i64_seeds=TEST_SEEDS)
    # the config's derivation names other cells: every replicate is then "no item record", NOT EVALUABLE; the analysis must be told the plan's labels
    blind = analysis.analyze_stage(reg, A1, CFG, i64_seeds=TEST_SEEDS)
    reasons = {r["reason"] for c in blind["cells"].values() for ck in c["checkpoints"].values() for r in ck["tree"]["replicates"]}
    assert all("no item record" in x for x in reasons) and not blind["r_diagnosis"]["evaluable"]
    plan_items = [{"cell_name": s.name, "arm": arm, "draw": d, "cell": label_of(arm, s, d)} for s in core.cell_specs(CFG) for arm in ("T-OQ", "F-OQ") for d in range(1, 6)]
    seen = analysis.analyze_stage(reg, A1, CFG, label_of=analysis.label_of_from_items(plan_items), i64_seeds=TEST_SEEDS)
    rows = {r["row"] for c in seen["cells"].values() for ck in c["checkpoints"].values() for r in ck["tree"]["replicates"]}
    assert rows == {labels.CONTENT} and seen["r_diagnosis"]["evaluable"]
    assert not any("no item record" in r["reason"] for c in seen["cells"].values() for ck in c["checkpoints"].values() for r in ck["tree"]["replicates"])


def test_the_accuracy_version_of_the_retention_ratio_is_computed_and_printed_beside_every_comparison() -> None:
    from studies.p10s1 import core as s1

    a = run(plan={("8K/4K", "U_P"): (labels.PRIORS, labels.SPARSE_APPROACHES)})
    rep = a["cells"]["8K/4K"]["checkpoints"]["U_P"]["tree"]["replicates"][0]
    acc = lambda i: s1.i_to_a_use(i)  # noqa: E731 - the synthetic records set accuracy = a_use; acc0 = 0.03 (memory disabled)
    want = (acc(3.9) - 0.03) / (acc(4.0) - 0.03)
    assert rep["retention"]["T1"]["A"]["status"] == labels.RESTORED and rep["retention"]["T1"]["A"]["accuracy_version"] == pytest.approx(want)
    assert rep["retention"]["T3"]["A"]["status"] == labels.NOT_RESTORED and rep["retention"]["T3"]["B"]["accuracy_version"] is not None
    idx = a["cells"]["8K/4K"]["checkpoints"]["U_P"]["index"]["replicates"][0]["retention"]
    assert idx["128"]["A"]["status"] == labels.NOT_RESTORED and idx["256"]["A"]["status"] == labels.RESTORED and idx["256"]["A"]["accuracy_version"] == pytest.approx(want)
    assert set(idx) == {"128", "256", "512", "1024", "2048"}
    text = report.render(analysis.analyze_all(a, None))
    assert f"accuracy version {want:.3f}" in text and "retention against F0 per panel A/B" in text and "decides nothing" in text
    assert "T1 A: RESTORED (accuracy version" in text and "T3 A: NOT RESTORED (accuracy version" in text and "256 A: RESTORED" in text.replace("I64@", "") or "256 A: RESTORED" in text


def test_the_convention_of_the_slack_and_the_rulings_are_printed() -> None:
    text = report.render(analysis.analyze_all(run(plan=uniform_plan(labels.PRIORS, labels.SPARSE_APPROACHES)), None))
    assert "1e-12" in text and "RULING 2" in text and "RULING 1" in text and "RULING 3" in text
