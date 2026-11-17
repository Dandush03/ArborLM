# ruff: noqa: E501
"""P10S0 analysis and report on synthetic records of the whole registry (ADR-0020 section 10.2): every outcome row, every class under both criteria, every consistency and replication label, the
overload, record-length and probe annotations and every block status, the override of section 3.4 and the list of section 3.5 as they reach the printed text, missing / failed / non-finite cells, failed
gates, a replaced draw and cut 3. The A5-D provenance block is checked on every rendered report. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s0 import analysis, arm_selection, core, report  # noqa: E402
from studies.p10s0 import classes as C  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

BAD = syn.always("bad")


def run(**kw):  # type: ignore[no-untyped-def]
    res = analysis.analyze(syn.make_run(**kw))
    md = report.render_markdown(res)
    assert report.check_a5d_provenance(md) == [], report.check_a5d_provenance(md)
    json.dumps(core.jsonable(res))  # the whole result is JSON-able (no objects, no NaN)
    return res, md


def arms_in(*arms: str, kind: str = "bad", cts: tuple[str, ...] = ("2K/4K", "8K/16K")):  # type: ignore[no-untyped-def]
    return {(a, ct): syn.always(kind) for a in arms for ct in cts}


# --- outcome rows ----------------------------------------------------------------------------------------------------------------------------
def test_row_4_candidate_a5d_with_the_full_printed_text() -> None:
    res, md = run(patterns=syn.a0_unreliable(), candidate="A5-D")
    o = res["outcome"]
    assert (o["row"], o["outcome"], o["arm"]) == (4, "ADDRESSING-QUALIFIED (4,096 AND 16,384)", "A5-D")
    assert res["selection"]["also_qualifies"] == ["ALSO QUALIFIES: A2 (4,096 ONLY)", "ALSO QUALIFIES: A1 (4,096 AND 16,384)"] or res["selection"]["also_qualifies"][-1].startswith("ALSO QUALIFIES: A1")
    assert res["overload"] == "OVERLOAD-QUALIFIED" and res["q2_status"] == {"wx": "COMPLETE", "probe": "COMPLETE"} and res["record_length"]["label"] == "RECORD-LENGTH-FREE VARIANT: PASSES"
    assert res["probe"]["label"].startswith("3 of 3 succeed") and "per-draw bound 0.368" in res["probe"]["label"]
    for needle in (
        "1. **Arm and calibrated value:** A5-D; μ = 1.0", core.FOURTH_ARM_STRING, core.F1_ANNOTATION, core.PROVENANCE_SENTENCE, "(LABEL-FREE)", "512 exposures per fact", "0.5 facts per slot",
        "**CONSISTENT ACROSS STUDIES**", "REPLICATES P9-II", "DOES NOT REPLICATE P9-II", "OVERLOAD-QUALIFIED", "RECORD-LENGTH-FREE VARIANT: PASSES", "AT 65,536 (probe; not a qualification; S0 only; three draws; one initialization seed)",
        core.FIXED_SENTENCES, "7. **Fixed sentences:**", "COLLAPSE-FREE", "per-draw bound",
    ):
        assert needle in md, needle
    assert "no pooled per-draw bound is printed for A5-D" in md
    assert md.count(core.PROVENANCE_SENTENCE) >= 1


def test_row_4_candidate_a1_prints_the_supervised_label_and_the_negative_control() -> None:
    res, md = run(patterns={**arms_in("A5-D"), **syn.a0_unreliable()}, candidate="A1")
    assert res["outcome"]["arm"] == "A1" and res["outcome"]["row"] == 4
    assert res["overload"] == "OVERLOAD NOT RUN — NO TARGET INJECTION" and "(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)" in md
    assert "P9-II NEGATIVE CONTROL: 4,096: not failed; 16,384: not failed" in md and "λ = 1.0" in md
    assert res["hypotheses"]["H20-O"]["reading"] == "not tested" and res["q2_status"]["wx"] == "COMPLETE"


def test_row_5_qualified_at_4096_only_with_every_reason_for_16384() -> None:
    # UNRELIABLE / FAILS at 16,384
    res, md = run(patterns=arms_in("A5-D", "A1", cts=("8K/16K",)))
    o = res["outcome"]
    assert (o["row"], o["arm"], o["scope"]) == (5, "A5-D", "4,096 ONLY") and o["detail"]["why_16384_missing"] == "FAILS" and "Why 16,384 is missing" in md
    assert res["q2_status"] == {"wx": "NOT RUN — NO CANDIDATE", "probe": "NOT RUN — NO CANDIDATE"} and res["overload"] == "OVERLOAD NOT RUN — NO CANDIDATE"
    unrel = {("A5-D", "8K/16K"): lambda d, j: "bad" if d <= 5 else "ok", ("A1", "8K/16K"): BAD}
    assert run(patterns=unrel)[0]["outcome"]["detail"]["why_16384_missing"] == "UNRELIABLE"
    # not ADDRESS STABLE at 16,384
    res, _ = run(patterns={("A1", "8K/16K"): BAD}, stability={("A5-D", "8K/16K"): 0.5})
    assert res["outcome"]["row"] == 5 and res["outcome"]["detail"]["why_16384_missing"] == "not ADDRESS STABLE at 16,384"
    # INCONSISTENT ACROSS STUDIES (P9-II <class>; pooled <failed> of <n>)
    classes = syn.committed_p9ii_classes()
    classes["A5-D"]["16384"] = syn.p9ii_class("UNRELIABLE", 2, 4)
    res, md = run(patterns={("A5-D", "8K/16K"): syn.failing_cells({(1, 0)}), ("A1", "8K/16K"): BAD}, selection=syn.selection_record(classes=classes))
    assert res["outcome"]["row"] == 5 and res["outcome"]["detail"]["why_16384_missing"] == "RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 3 of 14 draws failed)"
    assert "INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 3 of 14 draws failed)" in md
    # NOT_EVALUATED at 16,384 is not read as a failure
    res, _ = run(patterns={}, a6_bad={"8K/16K": {1, 2}})
    assert res["outcome"]["row"] == 5 and "NOT_EVALUATED at 16,384 (not read as a failure)" in res["outcome"]["detail"]["why_16384_missing"]


def test_row_6_not_qualified_prints_only_what_s0_found() -> None:
    res, md = run(patterns=arms_in("A0", "A1", "A2", "A5-D"))
    assert res["outcome"]["row"] == 6 and "NOT QUALIFIED IN S0" in md
    assert C.NOT_QUALIFIED_NEUTRAL in md and "ORACLE-ADDRESSED" not in md and "capacity scales" not in md.lower()
    for arm in core.CORE_LEARNED_ARMS:
        for ct in core.CORE_CELLTYPES:
            assert f"| {arm} | {ct} | FAILS" in md


def test_row_6_names_the_added_criterion_where_p9ii_s_criteria_hold_but_s0_s_do_not() -> None:
    res, md = run(patterns={("A5-D", "2K/4K"): syn.always("dep"), ("A5-D", "8K/16K"): syn.always("dep"), **arms_in("A0", "A1", "A2")})
    e = res["arms"]["A5-D"]["2K/4K"]
    assert e["s0"]["cls"] != "RELIABLE" and e["p9ii_criteria"]["cls"] == "RELIABLE" and e["added_criterion_failed"] == "condition 6 (fact-specific dependence)"
    assert "condition 6 (fact-specific dependence)" in md and res["outcome"]["row"] == 6
    res, _ = run(patterns=arms_in("A0", "A1", "A2"), stability={("A5-D", "2K/4K"): 0.5, ("A5-D", "8K/16K"): 0.5})
    assert res["arms"]["A5-D"]["2K/4K"]["added_criterion_failed"] == "ADDRESS STABLE" and res["outcome"]["row"] == 6


def test_row_6_lists_arms_that_met_s0_s_criteria_but_were_inconsistent() -> None:
    res, md = run(patterns=syn.a0_unreliable({("A5-D", "2K/4K"): BAD, ("A5-D", "8K/16K"): BAD, ("A1", "2K/4K"): BAD, ("A1", "8K/16K"): BAD, ("A2", "2K/4K"): BAD, ("A2", "8K/16K"): BAD}) | {("A0", "2K/4K"): syn.always("ok"), ("A0", "8K/16K"): syn.always("ok")})
    assert res["outcome"]["row"] == 6
    assert "Arms that met S0's criteria but were INCONSISTENT ACROSS STUDIES" in md and "A0 at 4,096 slots (2K/4K): RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II UNRELIABLE; pooled 6 of 18 draws failed)" in md
    assert res["selection"]["answer_only_suffices"] is None and "(ANSWER-ONLY SUFFICES)" not in md  # cannot be printed on the committed records


def test_row_3_inconclusive_and_the_one_draw_tolerance() -> None:
    res, md = run(a6_bad={"2K/4K": {1, 2}})
    assert res["outcome"]["row"] == 3 and res["outcome"]["outcome"] == "INCONCLUSIVE" and "Outcome (row 3): INCONCLUSIVE" in md
    one, _ = run(a6_bad={"2K/4K": {1}})
    assert one["outcome"]["row"] != 3 and one["arms"]["A5-D"]["2K/4K"]["s0"]["draws_not_evaluated"] == 1 and one["arms"]["A5-D"]["2K/4K"]["s0"]["evaluated"] == 18
    assert one["arms"]["A5-D"]["2K/4K"]["s0"]["cls"] == "RELIABLE"  # classes are read from the 18 evaluated cells; no denominator is changed


def test_row_1_not_started_without_a_calibration_record() -> None:
    sel = syn.selection_record(arm_selection.P9IIFacts(False, "ADDRESSING-RELIABLE", "COMPLETE", "A0"))
    res, md = run(selection=sel)
    assert res["outcome"]["row"] == 1 and res["outcome"]["outcome"] == "NOT STARTED — NO P9-II CALIBRATION RECORD" and "arms" not in res
    assert "NOT STARTED — NO P9-II CALIBRATION RECORD" in md and "Classes per arm" not in md


@pytest.mark.parametrize(
    "kw,needle",
    [
        ({"gates": {**syn.passing_gates(), "g4_passed": False}}, "G4 failed"),
        ({"gates": {**syn.passing_gates(), "g10_passed": False}}, "G10 failed"),
        ({"gates": {**syn.passing_gates(), "g9_passed": None}}, "G9 not recorded"),
        ({"gates": {**syn.passing_gates(), "g2_by_draw": {"4": False}}}, "G2 failed on draw 4"),
        ({"gates": {**syn.passing_gates(), "harness_errors": ["no data for 8192 facts"]}}, "HARNESS ERROR (not a gate failure): no data for 8192 facts"),
        ({"missing": {"Q1-A5-D-8K16K-d03-j1"}}, "Q1 cell without a record: Q1-A5-D-8K16K-d03-j1"),
        ({"failed_tasks": ["train-q1:Q1-A0-2K4K-d01-j0"]}, "failed task train-q1:Q1-A0-2K4K-d01-j0"),
        ({"frozen_mismatch": ["train-q1: identity source_sha256 differs"]}, "frozen/running mismatch"),
        ({"draw_plan": {"ok": False, "replacements": {}}}, "reserve list is exhausted"),
    ],
)
def test_row_2_engineering_fail_or_incomplete_derives_no_label(kw: dict, needle: str) -> None:
    res, md = run(**kw)
    assert res["outcome"]["row"] == 2 and "arms" not in res and needle in "; ".join(res["outcome"]["detail"]["reasons"]) and needle in md
    assert "Classes per arm" not in md and "hypothesis" not in md.split("## Hypothesis")[0].lower().replace("hypothesis readings", "")


def test_gates_missing_is_row_2() -> None:
    run_data = syn.make_run()
    run_data.gates = None
    res = analysis.analyze(run_data)
    assert res["outcome"]["row"] == 2 and "gates record missing" in res["outcome"]["detail"]["reasons"]


def test_a_replaced_draw_is_printed_and_does_not_stop_the_study() -> None:
    plan = {"ok": True, "replacements": {"4": "p10s0-reserve-1"}, "seed_set_of": {}}
    res, md = run(draw_plan=plan)
    assert res["replacements"] == {"4": "REPLACED BY RESERVE 1"} and "REPLACED BY RESERVE 1" in md and res["outcome"]["row"] != 2


def test_a_non_finite_cell_fails_and_the_analysis_completes() -> None:
    res, _ = run(nan_cells={"Q1-A5-D-2K4K-d02-j0"})
    s0 = res["arms"]["A5-D"]["2K/4K"]["s0"]
    assert s0["failures"] == 1 and s0["cls"] == "RELIABLE" and res["arms"]["A5-D"]["2K/4K"]["failed_conditions"] == {"2/0": [1, 4, 6]}
    two, _ = run(nan_cells={"Q1-A5-D-2K4K-d02-j0", "Q1-A5-D-2K4K-d05-j1"})
    assert two["arms"]["A5-D"]["2K/4K"]["s0"]["cls"] == "UNRELIABLE"


# --- classes under both criteria, labels ---------------------------------------------------------------------------------------------------------------------
def test_every_class_under_both_criteria_appears() -> None:
    patterns = {
        ("A0", "2K/4K"): syn.always("ok"), ("A0", "8K/16K"): lambda d, j: "bad" if d <= 3 else "ok",
        ("A1", "2K/4K"): lambda d, j: "bad" if d <= 8 else "ok", ("A1", "8K/16K"): BAD,
        ("A2", "2K/4K"): syn.always("dep"), ("A2", "8K/16K"): syn.failing_cells({(1, 0)}),
        ("A5-D", "2K/4K"): syn.always("ok"), ("A5-D", "8K/16K"): syn.always("dep"),
    }
    res, md = run(patterns=patterns)
    got = {(a, ct): (e["s0"]["cls"], e["p9ii_criteria"]["cls"]) for a, per in res["arms"].items() for ct, e in per.items() if ct != "8K/4K"}
    assert got[("A0", "2K/4K")] == ("RELIABLE", "RELIABLE") and got[("A0", "8K/16K")] == ("UNRELIABLE", "UNRELIABLE") and got[("A1", "2K/4K")] == ("FAILS", "FAILS")
    assert got[("A2", "2K/4K")] == ("FAILS", "RELIABLE") and got[("A2", "8K/16K")] == ("RELIABLE", "RELIABLE") and got[("A5-D", "8K/16K")] == ("FAILS", "RELIABLE")
    assert res["arms"]["A1"]["8K/16K"]["s0"]["label"] == "FAILS" and "| A2 (ADDRESS-SUPERVISED IN TRAINING) | 2K/4K |" in md
    assert res["a6"]["2K/4K"]["1"]["evaluated"] and "Oracle-query reference A6" in md


def test_lm_capability_reduced_prints_the_label() -> None:
    res, md = run(lm_rise={("A1", "2K/4K"): 0.5})
    e = res["arms"]["A1"]["2K/4K"]["s0"]
    assert e["lm_reduced"] and e["label"] == "UNRELIABLE (LM CAPABILITY REDUCED)" and "UNRELIABLE (LM CAPABILITY REDUCED)" in md


def test_consistency_and_replication_labels_reach_the_report() -> None:
    cls = syn.committed_p9ii_classes()
    res, md = run(patterns=syn.a0_unreliable({("A0", "2K/4K"): syn.always("ok")}), selection=syn.selection_record(classes=cls))
    a = res["arms"]
    assert a["A0"]["2K/4K"]["consistency"]["label"] == "INCONSISTENT ACROSS STUDIES" and a["A5-D"]["2K/4K"]["consistency"]["label"] == "CONSISTENT ACROSS STUDIES"
    assert a["A2"]["8K/16K"]["consistency"]["label"] == "SINGLE-STUDY EVIDENCE" and a["A2"]["2K/4K"]["consistency"]["label"] == "INCONSISTENT ACROSS STUDIES"
    assert a["A0"]["2K/4K"]["replication"] == "DOES NOT REPLICATE P9-II" and a["A5-D"]["2K/4K"]["replication"] == "REPLICATES P9-II" and a["A2"]["8K/16K"]["replication"] == "NOT COMPARABLE"
    assert a["A1"]["8K/16K"]["replication"] == "DOES NOT REPLICATE P9-II"  # RELIABLE in S0, UNRELIABLE in P9-II
    assert a["A5-D"]["2K/4K"]["pooled"]["per_draw_bound"] is None and "no pooled per-draw bound" in a["A5-D"]["2K/4K"]["pooled"]["text"]
    assert a["A1"]["2K/4K"]["pooled"]["per_draw_bound"] is not None and a["A5-D"]["8K/4K"]["pooled"]["text"].startswith("NOT AVAILABLE")
    # S0 NOT_EVALUATED: nothing to pool
    ne, _ = run(a6_bad={"2K/4K": {1, 2}})
    assert ne["outcome"]["row"] == 3 and ne["arms"]["A0"]["2K/4K"]["consistency"]["label"] == "NOT DEFINED (S0 NOT_EVALUATED)"


def test_consistency_single_study_when_p9ii_has_no_class() -> None:
    cls = {a: {"4096": syn.unavailable(), "16384": syn.unavailable()} for a in core.CORE_LEARNED_ARMS}
    res, md = run(selection=syn.selection_record(arm_selection.P9IIFacts(True, "ADDRESSING-RELIABLE", "COMPLETE", "A0"), cls), patterns=syn.a0_unreliable(), candidate="A5-D")
    assert res["outcome"]["row"] == 4 and all(res["arms"]["A5-D"][ct]["consistency"]["label"] == "SINGLE-STUDY EVIDENCE" for ct in core.CORE_CELLTYPES)
    assert "SINGLE-STUDY EVIDENCE" in md and res["selection"]["per_arm"]["A5-D"]["single_study_sizes"] == ["2K/4K", "8K/16K"]
    assert res["selection"]["candidate"] == "A0" or res["arms"]["A0"]["2K/4K"]["meets"] is False


def test_collapse_free_and_address_labels() -> None:
    res, md = run(collapsed={("A0", "2K/4K")})
    assert res["arms"]["A0"]["2K/4K"]["collapse_free"]["k"] == 0 and res["arms"]["A5-D"]["2K/4K"]["collapse_free"]["k"] == 20
    assert "COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset" in md
    assert res["arms"]["A1"]["2K/4K"]["address_recall"] is not None and "address_recall" not in res["arms"]["A5-D"]["2K/4K"]


def test_dense_comparison_and_class_at_u_are_printed() -> None:
    res, md = run()
    assert res["arms"]["A5-D"]["2K/4K"]["dense_comparison"]["label"] in ("DENSE AT CEILING", "DENSE SUFFICES", "BEATS DENSE") and "DENSE COMPARISON" in md
    assert res["arms"]["A2"]["8K/16K"]["class_at_u"]["label"].startswith("MID-SCHEDULE") and res["arms"]["A5-D"]["8K/16K"]["class_at_u"]["label"] == "ALSO AT MATCHED UPDATES"
    assert "class_at_u" not in res["arms"]["A5-D"]["2K/4K"]


def test_8k_4k_uses_one_seed_and_the_ten_cell_rule() -> None:
    res, _ = run(patterns={("A5-D", "8K/4K"): lambda d, j: "bad" if d in (1, 2) else "ok"})
    e = res["arms"]["A5-D"]["8K/4K"]
    assert e["rule"] == "10" and e["s0"]["cls"] == "UNRELIABLE" and e["s0"]["evaluated"] == 10 and e["replication"] == "NOT COMPARABLE" and e["consistency"] is None
    assert "paired_against_a0" in e


def test_cut_3_uses_the_ten_cell_rule_at_8k_16k() -> None:
    res, md = run(cut3=True, patterns=syn.a0_unreliable())
    e = res["arms"]["A5-D"]["8K/16K"]
    assert res["cut3"] and e["rule"] == "10" and e["s0"]["evaluated"] == 10 and res["arms"]["A5-D"]["2K/4K"]["rule"] == "20"
    assert res["outcome"]["row"] in (4, 5, 6)
    missing = analysis.analyze(syn.make_run(cut3=False, missing={"Q1-A0-8K16K-d01-j1"}))
    assert missing["outcome"]["row"] == 2  # under cut 3 that cell would not exist; without cut 3 it is a Q1 cell without a record


# --- the override and the list, as they reach the text ------------------------------------------------------------------------------------------------------------
def test_the_override_and_the_candidate_list_are_printed() -> None:
    _, md = run()
    assert "FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)" in md and core.HUMAN_LEAD_WORDS in md and "μ = 1.0" in md and "U_pre = 2,048" in md and "λ = 1.0" in md
    assert "Arms that can still be the candidate (section 3.5): A5-D, A1" in md and "A0 (P9-II failed draws at 4,096 already exceed two (6 of 8))" in md


def test_every_row_of_section_3_3_reaches_the_arm_selection_section() -> None:
    for outcome, stage2, carried in [("ADDRESSING-RELIABLE", "COMPLETE", "A0"), ("ADDRESSING-RELIABLE", "COMPLETE", "A1"), ("ADDRESSING-RELIABLE", "COMPLETE", "A2"), ("ANSWER-ONLY RELIABLE", "COMPLETE", "A0"), ("ADDRESSING-FAILS", "COMPLETE", None), ("ENGINEERING_FAIL", "COMPLETE", None), ("ANSWER-ONLY RELIABLE", "INCOMPLETE", None)]:
        sel = syn.selection_record(arm_selection.P9IIFacts(True, outcome, stage2, carried))
        res, md = run(selection=sel)
        assert f"table row {sel['mapping']['table_row']} of section 3.3" in md and sel["mapping"]["printed"] in md and core.FOURTH_ARM_STRING in md


def test_a_mapping_that_names_another_arm_is_printed_with_the_conflict() -> None:
    sel = syn.selection_record(arm_selection.P9IIFacts(True, "ADDRESSING-RELIABLE", "COMPLETE", "A5-C"))
    res, md = run(selection=sel)
    assert res["arm_selection"]["c4"] == "A5-C" and "fourth arm by the mapping: A5-C" in md


# --- Q2 blocks ----------------------------------------------------------------------------------------------------------------------------------------------------
def test_block_statuses() -> None:
    base = {"patterns": syn.a0_unreliable(), "candidate": "A5-D"}
    assert run(**base)[0]["q2_status"] == {"wx": "COMPLETE", "probe": "COMPLETE"}
    budget = run(**base, block_status={"wx": "NOT RUN — BUDGET", "probe": "NOT RUN — BUDGET"})[0]
    assert budget["q2_status"] == {"wx": "NOT RUN — BUDGET", "probe": "NOT RUN — BUDGET"} and budget["record_length"]["label"] == "RECORD-LENGTH-FREE VARIANT: NOT RUN — BUDGET"
    memory = run(**base, block_status={"probe": "NOT RUN — MEMORY"})[0]
    assert memory["q2_status"] == {"wx": "COMPLETE", "probe": "NOT RUN — MEMORY"} and memory["hypotheses"]["H20-S"]["reading"] == "not tested"
    incomplete = run(**base, missing={"WX-WX-A5-D-2K4K-d02-j1"})[0]
    assert incomplete["q2_status"]["wx"] == "INCOMPLETE" and incomplete["outcome"]["row"] == 4  # Q1's outcome stands
    inc_probe = run(**base, missing={"PR-A5-D-32K64K-d12-j0"})[0]
    assert inc_probe["q2_status"]["probe"] == "INCOMPLETE" and inc_probe["outcome"]["row"] == 4
    failed = run(**base, failed_tasks=["train-probe:PR-A5-D-32K64K-d12-j0"])[0]
    assert failed["q2_status"]["probe"] == "INCOMPLETE"
    not_eval = run(**base, probe_a6_bad={12})[0]
    assert not_eval["q2_status"]["probe"] == "NOT_EVALUATED" and not_eval["probe"]["label"] == "NOT_EVALUATED"
    none = run(patterns=arms_in("A0", "A1", "A2", "A5-D"))[0]
    assert none["q2_status"] == {"wx": "NOT RUN — NO CANDIDATE", "probe": "NOT RUN — NO CANDIDATE"}


def test_record_length_variant_and_probe_counts() -> None:
    res, md = run(patterns=syn.a0_unreliable(), candidate="A5-D", wx_pattern=lambda d, j: "bad" if d > 8 else "ok")  # 2 of 10 fail at each size: not RELIABLE at either
    assert res["record_length"]["label"].startswith("RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required)")
    assert res["hypotheses"]["H20-L"]["reading"] == "not supported"
    res, _ = run(patterns=syn.a0_unreliable(), candidate="A5-D", wx_pattern=lambda d, j: "bad" if d == 1 else "ok")  # one failed cell per size: RELIABLE
    assert res["record_length"]["label"] == "RECORD-LENGTH-FREE VARIANT: PASSES"
    res, _ = run(patterns=syn.a0_unreliable(), candidate="A5-D", probe_kind=lambda d, j: "bad" if d == 13 else "ok")
    assert res["probe"]["label"] == "2 of 3 succeed" and res["hypotheses"]["H20-S"]["reading"] == "not supported"
    res, _ = run(patterns=syn.a0_unreliable(), candidate="A5-D", probe_kind="bad")
    assert res["probe"]["label"] == "0 of 3 succeed" and res["hypotheses"]["H20-S"]["reading"] == "CONTRADICTED"
    res, _ = run(patterns=syn.a0_unreliable(), candidate="A5-D", probe_kind="bad", probe_a6_bad={11})
    assert res["hypotheses"]["H20-S"]["reading"] == "not supported"  # NOT_EVALUATED: contradicted only with A6 evaluated on every draw


def test_overload_not_qualified_and_not_evaluated() -> None:
    res, _ = run(patterns={**syn.a0_unreliable(), ("A5-D", "8K/4K"): BAD}, candidate="A5-D")
    assert res["overload"] == "OVERLOAD NOT QUALIFIED" and res["hypotheses"]["H20-O"]["reading"] == "not supported"
    res, _ = run(patterns=syn.a0_unreliable(), candidate="A5-D", a6_bad={"8K/4K": {1, 2}})
    assert res["overload"] == "OVERLOAD NOT_EVALUATED"


def test_h20_d_note_with_the_committed_shape() -> None:
    res, md = run(patterns={("A0", "2K/4K"): BAD, ("A0", "8K/16K"): syn.always("ok")})  # A0 succeeds at 8K/16K (P9-II: 8 of 8): d cannot reach 4
    assert res["arms"]["A5-D"]["8K/16K"]["s0"]["cls"] == "RELIABLE" and res["hypotheses"]["H20-D"]["reading"] == "not supported" and "unreachable" in md


# --- the report ----------------------------------------------------------------------------------------------------------------------------------------------------
def test_every_section_naming_a5d_carries_the_block_and_the_checker_catches_a_missing_one() -> None:
    _, md = run(patterns=syn.a0_unreliable(), candidate="A5-D")
    assert report.check_a5d_provenance(md) == []
    broken = md.replace(core.F1_ANNOTATION, "x", 1).replace(core.PROVENANCE_SENTENCE, "y")
    assert report.check_a5d_provenance(broken)
    stripped = md.replace(core.FOURTH_ARM_STRING, "z")
    assert report.check_a5d_provenance(stripped)
    sections = [p for p in md.split("\n## ")[1:] if "A5-D" in p.replace(core.a5d_block(), "")]
    assert len(sections) >= 5 and all(core.F1_ANNOTATION in s and core.PROVENANCE_SENTENCE in s and core.FOURTH_ARM_STRING in s for s in sections)


def test_the_report_makes_no_claim_beyond_the_records() -> None:
    _, md = run(patterns=syn.a0_unreliable(), candidate="A5-D")
    low = md.lower()
    for forbidden in ("breakthrough", "speedup of", "capacity scales", "oracle-addressed", "astra validated"):
        assert forbidden not in low, forbidden
    assert not re.search(r"\bproves?\b|\bproven\b(?! research)", low)
    assert "Astra review: NOT_PERFORMED" in md and "A Claude review is neither Astra validation nor a human approval" in md and "What may not be said" in md
    assert "The human lead accepted the P9-II outcome as registered (docs/decisions/ADR-0019-robust-sparse-address-learning.md section 16" in md


def test_write_report_to_disk_and_never_over_an_existing_file(tmp_path: Path) -> None:
    res = analysis.analyze(syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D"))
    run_dir = tmp_path / "P10S0TEST-run"
    run_dir.mkdir()
    core.write_record(run_dir / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": res, "identity": core.code_identity(), "environment": core.environment()}))
    paths = report.write_report(run_dir, tmp_path / "results", banner="synthetic")
    assert [p.name for p in paths] == ["RESULTS.md", "results.json", "classes.csv"]
    data = json.loads((tmp_path / "results/results.json").read_text())
    assert data["result"]["outcome"]["row"] == 4 and data["not_claimed"] and "A5-D,2K/4K" in (tmp_path / "results/classes.csv").read_text()
    with pytest.raises(FileExistsError):
        report.write_report(run_dir, tmp_path / "results")


def test_the_report_refuses_to_write_without_the_a5d_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    res = analysis.analyze(syn.make_run())
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    core.write_record(run_dir / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": res}))
    monkeypatch.setattr(report, "check_a5d_provenance", lambda md: ["Classes"])
    with pytest.raises(ValueError, match="provenance"):
        report.write_report(run_dir, tmp_path / "out")


def test_analysis_never_edits_its_inputs() -> None:
    sel = syn.selection_record()
    before = copy.deepcopy(sel)
    analysis.analyze(syn.make_run(selection=sel, candidate="A5-D"))
    assert sel == before


def test_sustained_success_is_counted_and_printed() -> None:
    res, md = run(collapsed={("A0", "2K/4K")})
    assert res["arms"]["A5-D"]["2K/4K"]["sustained_success"] == {"cells_with_first_success": 20, "sustained": 20, "label": "sustained success: 20 of 20 cells with a first success (descriptive)"}
    assert res["arms"]["A0"]["2K/4K"]["sustained_success"]["sustained"] == 0 and "sustained success: 20 of 20 cells with a first success" in md
    assert "Number labels:" in md and "MEASURED" in md and "ANALYTICAL" in md
