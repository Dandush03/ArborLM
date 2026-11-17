# ruff: noqa: E501
"""P10S0 arm-selection script and record (ADR-0020 sections 3.2 to 3.5) and gate G10: the mapping on P9-II's committed records, every row of the table of section 3.3 enumerated against the steps of
section 3.2, the override of section 3.4 character for character, the list of arms that can still be the candidate, and a G10 that fails on every tamper. Self-check only: not independent review, not Astra
validation, not human approval."""

import copy
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10s0 import arm_selection as sel  # noqa: E402
from studies.p10s0 import core, gates  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = [sel.ADDRESSING_RELIABLE, sel.ANSWER_ONLY_RELIABLE, sel.RELIABLE_4096_ONLY, "ADDRESSING-RELIABLE AT 4,096; 16,384 NOT RUN — BUDGET", "ADDRESSING-RELIABLE AT 4,096; 16,384 INCOMPLETE", "ADDRESSING-UNRELIABLE", "ADDRESSING-FAILS", "INCONCLUSIVE", "ENGINEERING_FAIL", "INCOMPLETE", "NOT_INTERPRETED", "NOT_INTERPRETED (INCOMPLETE)"]
CARRIED = [None, "A0", "A1", "A2", "A4", "A5-C", "A5-D"]
STAGE2 = ["COMPLETE", "NOT RUN — BUDGET", "INCOMPLETE", "NOT RUN — NO ARM PASSED", "NOT_EVALUATED"]


def realizable(outcome: str, stage2: str, carried: str | None) -> bool:
    """The combinations P9-II's own rules can produce (ADR-0019 section 8.6): an interface is carried forward only from a COMPLETE Stage 2, in an outcome that carries one (A0 may be carried when the outcome
    is ADDRESSING-RELIABLE AT 4,096 ONLY). Steps (section 3.2) and table (section 3.3) agree on all of them; they differ only on combinations P9-II cannot print, which the tests do not claim."""
    if carried is None:
        return True
    if stage2 != "COMPLETE":
        return False
    return outcome in (sel.ADDRESSING_RELIABLE, sel.ANSWER_ONLY_RELIABLE) or (outcome == sel.RELIABLE_4096_ONLY and carried == "A0") or outcome in sel.NOT_RUN_OUTCOMES


@pytest.fixture(scope="module")
def record() -> dict:
    return sel.build_record(ROOT)


# --- the mapping on the committed records --------------------------------------------------------------------------------------------------------
def test_the_mapping_gives_no_fourth_arm_on_p9ii_s_committed_records(record: dict) -> None:
    m = record["mapping"]
    assert m["c4"] is None and m["printed"] == "FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)" and m["table_row"] == 3
    assert m["table_row_text"] == "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096)" and m["steps_equal_table"] and not m["not_started"]
    assert m["facts"] == {"calibration_exists": True, "outcome": "ADDRESSING-RELIABLE", "stage2_status": "COMPLETE", "carried": "A0"} and m["decided_at"] == "§3.2 item 4"


def test_the_record_holds_the_hashes_of_the_p9ii_records_read(record: dict) -> None:
    assert set(record["p9ii_inputs"]) == {"results", "outcome", "calibration"}
    for key, entry in record["p9ii_inputs"].items():
        assert entry["sha256"] == file_sha256(ROOT / entry["path"]) and entry["path"] == core.P9II_RECORDS[key]
    assert record["p9ii_inputs"]["calibration"]["sha256"].startswith("ad5d7ee2")


def test_calibrated_values_equal_the_p9ii_calibration_record(record: dict) -> None:
    c = record["calibrated"]
    assert (c["lambda"], c["u_pre"], c["mu"], c["k0_fraction"], c["k0_fraction_used"]) == (1.0, 2048.0, 1.0, 0.125, False) and c["equals_p9ii_record"]
    assert c["p9ii_record_hyper"]["lambda"] == 1.0 and c["p9ii_record_hyper"]["u_pre"] == 2048.0 and c["p9ii_record_hyper"]["mu"] == 1.0


def test_the_override_part_is_copied_from_the_adr(record: dict) -> None:
    o = record["override"]
    adr = (ROOT / core.SPEC).read_text(encoding="utf-8")
    for key in ("human_lead_words", "printed_string", "f1_annotation", "fixed_sentence"):
        assert o[key] in adr, key
    assert (o["c4"], o["mu"], o["date"]) == ("A5-D", 1.0, "2026-11-15") and o["not_an_acceptance_of_the_p9ii_outcome"]
    assert record["fourth_arm_printed"] == core.FOURTH_ARM_STRING and not record["arm_set_conflict"]


def test_the_arms_that_can_still_be_the_candidate_are_a5d_and_a1(record: dict) -> None:
    c = record["candidates"]
    assert c["arms"] == ["A5-D", "A1"] and set(c["excluded"]) == {"A0", "A2"}
    assert "exceed two (6 of 8)" in c["excluded"]["A0"] and "exceed two (8 of 8)" in c["excluded"]["A2"]
    assert record["arm_set"] == ["A0", "A1", "A2", "A5-D"]


def test_p9ii_classes_as_read_from_the_record(record: dict) -> None:
    k = record["p9ii_classes"]
    assert (k["A0"]["4096"]["class"], k["A0"]["4096"]["successes"], k["A0"]["4096"]["failed_draws"], k["A0"]["4096"]["evaluated_draws"]) == ("UNRELIABLE", 4, 6, 8)
    assert (k["A0"]["16384"]["class"], k["A0"]["16384"]["failed_draws"], k["A0"]["16384"]["evaluated_draws"]) == ("RELIABLE", 0, 4)
    assert (k["A5-D"]["4096"]["class"], k["A5-D"]["4096"]["successes"], k["A5-D"]["16384"]["successes"], k["A5-D"]["16384"]["failed_draws"]) == ("RELIABLE", 16, 8, 0)
    assert (k["A1"]["4096"]["class"], k["A1"]["16384"]["class"], k["A1"]["16384"]["failed_draws"], k["A1"]["16384"]["successes"]) == ("RELIABLE", "UNRELIABLE", 2, 6)
    assert k["A2"]["4096"]["class"] == "FAILS" and k["A2"]["4096"]["failed_draws"] == 8 and not k["A2"]["16384"]["available"]
    assert record["p9ii_negative_control"] == {"4096": False, "16384": False}


def test_the_record_is_deterministic_and_the_script_writes_it_once(tmp_path: Path) -> None:
    a, b = sel.build_record(ROOT, commit_of=False), sel.build_record(ROOT, commit_of=False)
    assert json.dumps(core.jsonable(a), sort_keys=True) == json.dumps(core.jsonable(b), sort_keys=True)
    out = tmp_path / "arm_selection.json"
    assert sel.main(["--out", str(out)]) == 0 and out.is_file()
    assert sel.main(["--out", str(out)]) == 2  # never over an existing file


# --- the steps of section 3.2 against the table of section 3.3, enumerated --------------------------------------------------------------------------
def test_steps_and_table_agree_on_every_p9ii_outcome() -> None:
    n = 0
    seen_rows: set[int] = set()
    for outcome, st2, carried, cal in itertools.product(OUTCOMES, STAGE2, CARRIED, (True, False)):
        if not realizable(outcome, st2, carried):
            continue
        f = sel.P9IIFacts(cal, outcome, st2, carried)
        m = sel.evaluate_mapping(f)
        n += 1
        assert m["steps_equal_table"], (outcome, st2, carried, cal)
        if cal:
            seen_rows.add(m["table_row"])
        assert m["c4"] in (None, "A4", "A5-C", "A5-D")
    assert n > 150 and seen_rows == set(range(1, 12))


@pytest.mark.parametrize(
    "outcome,stage2,carried,row,c4",
    [
        (sel.ADDRESSING_RELIABLE, "COMPLETE", "A5-C", 1, "A5-C"), (sel.ADDRESSING_RELIABLE, "COMPLETE", "A5-D", 1, "A5-D"), (sel.ADDRESSING_RELIABLE, "COMPLETE", "A4", 1, "A4"),
        (sel.ADDRESSING_RELIABLE, "COMPLETE", "A2", 2, None), (sel.ADDRESSING_RELIABLE, "COMPLETE", "A1", 2, None), (sel.ADDRESSING_RELIABLE, "COMPLETE", "A0", 3, None),
        (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A0", 4, None), (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A5-D", 5, "A5-D"), (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A5-C", 5, "A5-C"), (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A4", 5, "A4"),
        (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A2", 6, None), (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", "A1", 6, None), (sel.ANSWER_ONLY_RELIABLE, "COMPLETE", None, 6, None),
        (sel.ANSWER_ONLY_RELIABLE, "INCOMPLETE", "A5-D", 7, None), (sel.ANSWER_ONLY_RELIABLE, "NOT RUN — BUDGET", None, 7, None),
        (sel.RELIABLE_4096_ONLY, "COMPLETE", "A0", 8, None), (sel.RELIABLE_4096_ONLY, "COMPLETE", None, 8, None),
        ("ADDRESSING-RELIABLE AT 4,096; 16,384 NOT RUN — BUDGET", "NOT RUN — BUDGET", None, 9, None), ("ADDRESSING-RELIABLE AT 4,096; 16,384 INCOMPLETE", "INCOMPLETE", "A5-D", 9, None),
        ("ADDRESSING-UNRELIABLE", "COMPLETE", None, 10, None), ("ADDRESSING-FAILS", "COMPLETE", None, 10, None), ("INCONCLUSIVE", "COMPLETE", None, 10, None),
        ("ENGINEERING_FAIL", "COMPLETE", "A5-D", 11, None), ("INCOMPLETE", "COMPLETE", "A5-D", 11, None), ("NOT_INTERPRETED", "COMPLETE", "A4", 11, None),
    ],
)
def test_every_row_of_section_3_3(outcome: str, stage2: str, carried: str | None, row: int, c4: str | None) -> None:
    m = sel.evaluate_mapping(sel.P9IIFacts(True, outcome, stage2, carried))
    assert (m["table_row"], m["c4"], m["table_c4"]) == (row, c4, c4) and m["table_row_text"] == sel.TABLE_ROWS[row]


def test_every_branch_of_section_3_2_prints_its_own_string() -> None:
    f = sel.P9IIFacts
    assert sel.evaluate_mapping(f(False, "ADDRESSING-RELIABLE", "COMPLETE", "A0"))["printed"] == core.NOT_STARTED
    assert sel.evaluate_mapping(f(False, "ADDRESSING-RELIABLE", "COMPLETE", "A0"))["not_started"] and sel.evaluate_mapping(f(False, "ADDRESSING-RELIABLE", "COMPLETE", "A0"))["decided_at"] == "§3.2 item 1"
    assert sel.evaluate_mapping(f(True, "ENGINEERING_FAIL", "COMPLETE", "A5-D"))["printed"] == "FOURTH ARM: NONE — P9-II ENGINEERING_FAIL"
    assert sel.evaluate_mapping(f(True, "ANSWER-ONLY RELIABLE", "NOT RUN — BUDGET", "A5-D"))["decided_at"] == "§3.2 item 3"
    for arm in ("A0", "A1", "A2"):
        assert sel.evaluate_mapping(f(True, "ADDRESSING-RELIABLE", "COMPLETE", arm))["printed"] == f"FOURTH ARM: NONE — P9-II CARRIED {arm} (ALREADY IN S0)"
    assert sel.evaluate_mapping(f(True, "ADDRESSING-RELIABLE", "COMPLETE", None))["printed"] == "FOURTH ARM: NONE — P9-II CARRIED NONE"
    assert sel.evaluate_mapping(f(True, "ADDRESSING-RELIABLE", "COMPLETE", "A5-C"))["c4"] == "A5-C"


def test_a_mapping_that_names_another_arm_is_flagged_as_a_conflict_with_the_fixed_arm_set() -> None:
    rec = syn.selection_record(sel.P9IIFacts(True, "ADDRESSING-RELIABLE", "COMPLETE", "A5-C"))
    assert rec["arm_set_conflict"] and rec["mapping"]["c4"] == "A5-C"
    assert not syn.selection_record()["arm_set_conflict"]


def test_candidate_list_rule_on_synthetic_p9ii_classes() -> None:
    c = syn.committed_p9ii_classes()
    assert sel.candidate_arms(c)["arms"] == ["A5-D", "A1"]
    c2 = copy.deepcopy(c)
    c2["A5-D"]["4096"] = syn.p9ii_class("UNRELIABLE", 3, 8)  # more than two failed draws: excluded
    assert sel.candidate_arms(c2)["arms"] == ["A1"]
    c3 = copy.deepcopy(c)
    c3["A1"]["4096"] = syn.p9ii_class("UNRELIABLE", 1, 8, lm=True)  # LM CAPABILITY REDUCED printed: excluded
    assert sel.candidate_arms(c3) == {"arms": ["A5-D"], "excluded": {"A0": c3 and sel.candidate_arms(c3)["excluded"]["A0"], "A2": sel.candidate_arms(c3)["excluded"]["A2"], "A1": "P9-II printed LM CAPABILITY REDUCED at 4,096"}}
    c4 = copy.deepcopy(c)
    c4["A0"]["4096"] = syn.p9ii_class("RELIABLE", 2, 8)  # exactly two failed draws is not excluded
    assert "A0" in sel.candidate_arms(c4)["arms"]
    c5 = {a: {"4096": syn.unavailable("P9-II not interpreted"), "16384": syn.unavailable()} for a in core.PREFERENCE_ORDER}
    assert sel.candidate_arms(c5)["arms"] == list(core.PREFERENCE_ORDER)  # no P9-II class: nothing excludes an arm


def test_p9ii_classes_are_read_only_when_p9ii_is_interpreted_and_stage_2_complete() -> None:
    results = json.loads((ROOT / core.P9II_RECORDS["results"]).read_text())
    full = sel.p9ii_classes(results, True)
    assert full["A0"]["16384"]["available"]
    assert not sel.p9ii_classes(results, False)["A0"]["4096"]["available"]
    results["result"]["stage2"]["status"] = "INCOMPLETE"
    inc = sel.p9ii_classes(results, True)
    assert inc["A0"]["4096"]["available"] and not inc["A0"]["16384"]["available"] and "INCOMPLETE" in inc["A0"]["16384"]["reason"]  # a class printed for a Stage 2 that is not COMPLETE is not read


# --- G10 --------------------------------------------------------------------------------------------------------------------------------------------
def test_g10_passes_on_the_committed_record_and_cites_the_table_cell(record: dict) -> None:
    g = gates.g10_check(record, ROOT)
    assert g["passed"], g["problems"]
    assert g["table_row"] == 3 and g["table_cell_cited"] == "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096)"
    assert g["independent"] == {"table_row": 3, "c4": None, "candidates": ["A5-D", "A1"], "excluded": {"A0": "failed draws 6", "A2": "failed draws 8"}}
    assert g["auditor_script_run"] is False


def test_g10_fails_on_every_tamper(record: dict) -> None:
    def tampered(mutate) -> dict:  # type: ignore[no-untyped-def]
        r = copy.deepcopy(record)
        mutate(r)
        return gates.g10_check(r, ROOT)

    assert not tampered(lambda r: r["mapping"].update(c4="A5-D"))["passed"]
    assert not tampered(lambda r: r["mapping"].update(table_row=1))["passed"]
    assert not tampered(lambda r: r["mapping"].update(steps_equal_table=False))["passed"]
    assert not tampered(lambda r: r["candidates"].update(arms=["A5-D", "A1", "A0"]))["passed"]
    assert not tampered(lambda r: r["override"].update(human_lead_words="yes s0 should include the penalty"))["passed"]
    assert not tampered(lambda r: r["override"].update(printed_string=r["override"]["printed_string"].replace("A5-D", "A5-C")))["passed"]
    assert not tampered(lambda r: r["override"].update(f1_annotation=r["override"]["f1_annotation"] + " "))["passed"]
    assert not tampered(lambda r: r["override"].update(fixed_sentence=r["override"]["fixed_sentence"].replace("16/16", "15/16")))["passed"]
    assert not tampered(lambda r: r["override"].update(mu=0.1))["passed"]
    assert not tampered(lambda r: r["calibrated"].update(mu=0.1))["passed"]
    assert not tampered(lambda r: r["calibrated"].update(equals_p9ii_record=False))["passed"]
    assert not tampered(lambda r: r["p9ii_inputs"]["results"].update(sha256="0" * 64))["passed"]


def test_g10_reruns_part_1_of_the_auditor_script_when_asked(tmp_path: Path, record: dict) -> None:
    good = tmp_path / "script_ok.py"
    good.write_text('def part1():\n    print("Part 1: 3 P9-II records enumerated")\n    print("  rule-vs-table disagreements: none")\n')
    r = gates.g10_check(record, ROOT, run_script=True, script=good)
    assert r["passed"] and r["auditor_script"]["no_disagreements"] and r["auditor_script"]["script_sha256"] == file_sha256(good)
    bad = tmp_path / "script_bad.py"
    bad.write_text('def part1():\n    print("  rule-vs-table disagreements: {(1, 2): 3}")\n')
    assert not gates.g10_check(record, ROOT, run_script=True, script=bad)["passed"]
    assert (ROOT / gates.AUDITOR_SCRIPT).is_file()


def test_the_independent_evaluation_matches_the_scripts_on_synthetic_records(tmp_path: Path) -> None:
    (tmp_path / "results/p9ii-run-2026-11-15").mkdir(parents=True)
    (tmp_path / "results/p9ii-calibration-2026-11-15").mkdir(parents=True)
    (tmp_path / core.P9II_RECORDS["calibration"]).write_text("{}")
    base = json.loads((ROOT / core.P9II_RECORDS["results"]).read_text())
    for outcome, st2, carried in itertools.product(["ADDRESSING-RELIABLE", "ANSWER-ONLY RELIABLE", "ADDRESSING-RELIABLE AT 4,096 ONLY", "ADDRESSING-FAILS", "ENGINEERING_FAIL"], ["COMPLETE", "INCOMPLETE"], [None, "A0", "A1", "A2", "A5-C", "A5-D"]):
        if not realizable(outcome, st2, carried):
            continue
        results = copy.deepcopy(base)
        results["result"]["outcome"]["outcome"] = outcome
        results["result"]["stage2"]["status"] = st2
        results["result"]["carried_forward"]["arm"] = carried
        (tmp_path / core.P9II_RECORDS["results"]).write_text(json.dumps(results))
        mine = sel.evaluate_mapping(sel.p9ii_facts(results, {"hyper": {}}))
        ind = gates.independent_evaluation(tmp_path)
        assert (ind["table_row"], ind["c4"]) == (mine["table_row"], mine["c4"]), (outcome, st2, carried)
