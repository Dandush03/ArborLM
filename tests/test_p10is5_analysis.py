# ruff: noqa: E501
"""P10IS5 analysis and report tests on synthetic registries with known answers (ADR-0028 section 12 'Analysis tests'): every row of section 5.3 (EQ-A, EQ-B, EQ-D), HARNESS-LIMITED, every NOT EVALUABLE reason in the
ADR's order, ENGINEERING STOP (the analysis refuses), the invalid-block and spare rules, and the arithmetic lines of section 5.5. The expected values are computed BY HAND in this file (closed-form arithmetic on the
typed latencies), not with the analysis's helpers. Nothing here touches a device, a file of the study or a registered seed. Self-check only: not independent review, not Astra validation, not human approval."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import analysis, core, report, synthetic  # noqa: E402
from studies.p10is5.synthetic import DEPTHS, GRID, QUIET_BAD, QUIET_OK, default_thresholds, make_registry  # noqa: E402


def base(r: int, k: int, s: int) -> int:
    """The default synthetic median in ns, written out here (independent of the module's lambda)."""
    return round(50_000 + 20_000 * (s - 1) / (1 + 0.1 * (k - 1)))


def test_all_valid_default_registry() -> None:
    res = analysis.analyse(make_registry())
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"
    assert res["n_valid"] == 5
    b = res["EQ-B"]
    # rho(3) = 90,000 / (3 x 50,000) = 0.6 <= 1 - 0.10 in all five repeats
    assert b["label"] == "CONTIGUOUS REQUEST CHEAPER PER PAGE"
    assert b["counts"] == {"cheaper": 5, "dearer": 0, "proportional": 0, "of": 5, "denominator": 5}
    assert b["per_repeat"][1]["rho"][3] == pytest.approx(0.6)
    assert b["per_repeat"][1]["rho"][8] == pytest.approx(190_000 / (8 * 50_000))
    assert b["per_repeat"][1]["rho"][64] == pytest.approx(1_310_000 / (64 * 50_000))
    c1 = b["per_repeat"][1]["c1"]
    assert (c1["median"], c1["p90"], c1["p99"], c1["max"]) == (50_000, 50_000, 50_000, 500_000)  # 399 at the median and one ten times: nearest rank
    assert b["pooled_c1"]["max"] == 500_000
    assert res["EQ-D"]["label"] == "COST TABLE REGISTERED"
    assert len(res["EQ-D"]["rows"]) == 24
    assert res["scientific"]["label"] == "SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)"


@pytest.mark.parametrize(
    ("l3", "label"),
    [(90_000, "CONTIGUOUS REQUEST CHEAPER PER PAGE"), (135_000, "CONTIGUOUS REQUEST CHEAPER PER PAGE"), (136_000, "COST PROPORTIONAL TO PAGES"), (150_000, "COST PROPORTIONAL TO PAGES"), (164_000, "COST PROPORTIONAL TO PAGES"), (165_000, "CONTIGUOUS REQUEST DEARER PER PAGE"), (200_000, "CONTIGUOUS REQUEST DEARER PER PAGE")],
)
def test_eq_b_rows_at_the_margin(l3: int, label: str) -> None:
    # c(1) = 50,000 so s c(1) = 150,000: rho = l3 / 150,000; m_t = 0.10: cheaper iff l3 <= 135,000, dearer iff l3 >= 165,000 (boundaries inclusive), proportional strictly between
    reg = make_registry(median_of=lambda r, k, s: l3 if (k, s) == (1, 3) else base(r, k, s))
    assert analysis.analyse(reg)["EQ-B"]["label"] == label


def test_eq_b_needs_four_of_five_and_the_denominator_stays_five() -> None:
    def med(prop: set[int]):  # type: ignore[no-untyped-def]
        return lambda r, k, s: (150_000 if (k, s) == (1, 3) and r in prop else base(r, k, s))

    three_one = analysis.analyse(make_registry(median_of=med({4, 5})))["EQ-B"]
    assert three_one["label"] == "NOT SEPARATED AT MARGIN" and three_one["counts"]["cheaper"] == 3 and three_one["counts"]["proportional"] == 2
    four_one = analysis.analyse(make_registry(median_of=med({5})))["EQ-B"]
    assert four_one["label"] == "CONTIGUOUS REQUEST CHEAPER PER PAGE" and four_one["counts"]["cheaper"] == 4
    # one invalid block (and no valid spare): four valid repeats, all cheaper -> label stands; an invalid repeat is none of the three
    reg = make_registry(quiet={2: (QUIET_OK, QUIET_BAD)})
    out = analysis.analyse(reg)
    assert out["n_valid"] == 4 and out["EQ-B"]["label"] == "CONTIGUOUS REQUEST CHEAPER PER PAGE" and out["EQ-B"]["counts"]["of"] == 4
    # two proportional of four valid: neither reaches four
    reg = make_registry(quiet={2: (QUIET_OK, QUIET_BAD)}, median_of=med({1, 3}))
    assert analysis.analyse(reg)["EQ-B"]["label"] == "NOT SEPARATED AT MARGIN"


def test_margin_rule_floor_ceiling() -> None:
    cfg = core.load_config()
    assert core.margin_from_cv(0.04, cfg) == (0.10, False)  # max(0.10, 0.08)
    m, spread = core.margin_from_cv(0.10, cfg)
    assert m == pytest.approx(0.20) and not spread
    m, spread = core.margin_from_cv(0.15, cfg)
    assert m == pytest.approx(0.30) and not spread  # exactly 0.30 is not above the ceiling
    m, spread = core.margin_from_cv(0.20, cfg)
    assert m == pytest.approx(0.40) and spread


def test_timing_spread_makes_eq_b_not_evaluable_and_keeps_descriptive_figures() -> None:
    res = analysis.analyse(make_registry(thresholds=default_thresholds(m_t=0.4, timing_spread=True)))
    b = res["EQ-B"]
    assert b["label"] == "ENGINEERING NOT EVALUABLE (TIMING SPREAD)" and b["reasons"] == ["TIMING SPREAD"]
    assert b["figures_descriptive"]["per_repeat"][1]["rho"][3] == pytest.approx(0.6)
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY" and res["EQ-D"]["label"] == "COST TABLE REGISTERED"  # TIMING SPREAD applies to EQ-B only


def test_eq_d_dispersion_figures_by_hand() -> None:
    # medians at (k=1, s=1) by repeat: 50,000 x (1, 1.1, 1.2, 1.3, 1.4) = 50,000 55,000 60,000 65,000 70,000
    reg = make_registry(median_of=lambda r, k, s: round(base(r, k, s) * (1 + 0.1 * (r - 1))))
    row = analysis.analyse(reg)["EQ-D"]["rows"]["k1|s1"]
    assert row["median_of_medians"] == 60_000 and row["range"] == [50_000, 70_000]
    mean, var = 60_000.0, ((10_000) ** 2 * 2 + (5_000) ** 2 * 2) / 4
    assert row["cv"] == pytest.approx(math.sqrt(var) / mean)  # sample standard deviation, n - 1
    assert row["pooled_median"] == 60_000  # 5 x 399 requests at the five medians: the 998th of 1,995 sorted values
    assert row["tag"] is None


def test_harness_limited_tag_and_not_measured() -> None:
    # the pooled median of (k=32, s=1) is 50,000 (one page: the synthetic median does not depend on depth) and a quarter is 12,500: h(32) = 13,000 is above, 12,500 (not above) and 12,000 are not
    ok = analysis.analyse(make_registry(harness_ns={32: 12_500}))["EQ-D"]["rows"]["k32|s1"]
    limited = analysis.analyse(make_registry(harness_ns={32: 13_000}))["EQ-D"]["rows"]["k32|s1"]
    assert ok["tag"] is None and limited["tag"] == "HARNESS-LIMITED" and limited["limited"]
    # the other depths keep h = 1,000 and are not tagged
    assert analysis.analyse(make_registry(harness_ns={32: 13_000}))["EQ-D"]["rows"]["k1|s1"]["tag"] is None
    reg = make_registry()
    reg["harness"][4] = {"status": "NOT MEASURED"}
    assert analysis.analyse(reg)["EQ-D"]["rows"]["k4|s8"]["tag"] == "HARNESS FIGURE NOT MEASURED"


def test_tag_removes_no_cell_and_changes_no_label() -> None:
    a = analysis.analyse(make_registry(harness_ns={32: 10**9}))
    b = analysis.analyse(make_registry())
    assert a["EQ-D"]["label"] == b["EQ-D"]["label"] and len(a["EQ-D"]["rows"]) == len(b["EQ-D"]["rows"]) == 24 and a["EQ-B"]["label"] == b["EQ-B"]["label"]


def test_arithmetic_table_by_hand() -> None:
    res = analysis.analyse(make_registry())
    rows = {r["k"]: r for r in res["arithmetic"]}

    def L(k: int, s: int) -> int:
        return base(1, k, s)

    expect = {  # k: (two 3-page requests, six 1-page requests), written out: ceil(2/min(k,2)) L(min(k,2),3); ceil(6/k') L(k',1), k' in 1,2,4,4,4,4
        1: (2 * L(1, 3), 6 * L(1, 1)), 2: (1 * L(2, 3), 3 * L(2, 1)), 4: (1 * L(2, 3), 2 * L(4, 1)), 8: (1 * L(2, 3), 2 * L(4, 1)), 16: (1 * L(2, 3), 2 * L(4, 1)), 32: (1 * L(2, 3), 2 * L(4, 1)),
    }  # fmt: skip
    for k in DEPTHS:
        assert rows[k]["two_3page_ns"] == expect[k][0], k
        assert rows[k]["six_1page_ns"] == expect[k][1], k
    assert [rows[k]["six_1page_depth_used"] for k in DEPTHS] == [1, 2, 4, 4, 4, 4]
    assert [rows[k]["six_1page_rounds"] for k in DEPTHS] == [6, 3, 2, 2, 2, 2]


def test_no_arithmetic_when_eq_d_is_not_evaluable() -> None:
    res = analysis.analyse(make_registry(manifest={"quiet_exhausted": True}))
    assert "arithmetic" not in res and res["EQ-D"]["label"] == "ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET)"


# --- EQ-A ----------------------------------------------------------------------------------------------------------------------------------
def test_eq_a_one_failing_pass_spoils_the_label_and_is_printed_beside_the_replacing_block() -> None:
    reg = make_registry(spare=True, bad_cells={(3, 4, 8): core.STORE_PAGES_CACHED})
    res = analysis.analyse(reg)
    a = res["EQ-A"]
    assert a["label"].startswith("BYTES NOT CONFIRMED (E2|r3|k4|s8|a1: STORE PAGES CACHED") and len(a["failing"]) == 1
    assert a["failing"][0]["replacing_block_pass"]["key"] == "E2|r6|k4|s8|a1"  # the same cell in the replacing block (the spare)
    assert res["selection"]["replaced_block"] == "E2|r3|a1" and res["n_valid"] == 5  # the spare replaces the invalid block
    assert res["EQ-B"]["label"] == "CONTIGUOUS REQUEST CHEAPER PER PAGE"  # EQ-B and EQ-D stand on valid repeats only


def test_eq_a_counts_the_spare_and_every_attempt_whether_or_not_the_block_was_valid() -> None:
    reg = make_registry(spare=True, spare_bad_cells={(1, 1): core.COUNTER_CONTAMINATED})
    a = analysis.analyse(reg)["EQ-A"]
    assert a["label"].startswith("BYTES NOT CONFIRMED") and a["failing"][0]["counter_status"] == "COUNTER CONTAMINATED"
    # a block that was not quiet still counts its passes in EQ-A
    reg = make_registry(quiet={1: (QUIET_BAD, QUIET_OK)}, bad_cells={(1, 2, 3): core.STORE_PAGES_CACHED})
    assert analysis.analyse(reg)["EQ-A"]["label"].startswith("BYTES NOT CONFIRMED")


def test_eq_a_first_failing_pass_is_by_sequence() -> None:
    reg = make_registry(bad_cells={(4, 1, 1): core.STORE_PAGES_CACHED, (2, 32, 64): core.COUNTER_CONTAMINATED})
    a = analysis.analyse(reg)["EQ-A"]
    assert "E2|r2|k32|s64|a1: COUNTER CONTAMINATED" in a["reason"] and len(a["failing"]) == 2


def test_eq_a_is_not_a_four_of_five_rule() -> None:
    reg = make_registry(bad_cells={(5, 32, 64): core.STORE_PAGES_CACHED})
    assert analysis.analyse(reg)["EQ-A"]["label"].startswith("BYTES NOT CONFIRMED")


# --- the spare, validity ---------------------------------------------------------------------------------------------------------------------
def test_spare_replaces_only_the_first_invalid_block_once() -> None:
    reg = make_registry(spare=True, quiet={2: (QUIET_OK, QUIET_BAD), 4: (QUIET_BAD, QUIET_OK)})
    res = analysis.analyse(reg)
    assert res["selection"]["replaced_block"] == "E2|r2|a1" and res["n_valid"] == 4  # 1, 3, 5 and the spare; block 4 stays invalid
    assert "E2|r4|a1" not in res["valid_repeats"] and "E2|r6|a1" in res["valid_repeats"]
    assert res["EQ-D"]["label"] == "COST TABLE REGISTERED"


def test_three_invalid_blocks_leave_fewer_than_four_valid_repeats() -> None:
    reg = make_registry(spare=True, quiet={2: (QUIET_OK, QUIET_BAD), 3: (QUIET_BAD, QUIET_OK), 4: (QUIET_BAD, QUIET_BAD)})
    res = analysis.analyse(reg)
    assert res["n_valid"] == 3
    for line in ("EQ-B", "EQ-D"):
        assert res[line]["label"] == "ENGINEERING NOT EVALUABLE (FEWER THAN FOUR VALID REPEATS)"
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"  # EQ-A does not depend on quietness or on valid repeats


def test_an_invalid_spare_does_not_replace() -> None:
    reg = make_registry(spare=True, quiet={2: (QUIET_OK, QUIET_BAD)}, spare_quiet=(QUIET_BAD, QUIET_OK))
    res = analysis.analyse(reg)
    assert res["n_valid"] == 4 and res["selection"]["replaced_block"] is None


def test_a_block_with_missing_cells_is_invalid() -> None:
    reg = make_registry()
    blk = reg["blocks"][0]
    blk["pass_keys"] = blk["pass_keys"][:-1]
    assert analysis.analyse(reg)["n_valid"] == 4


# --- NOT EVALUABLE reasons, in the ADR's order ---------------------------------------------------------------------------------------------------
def test_reasons_are_ordered_and_all_printed() -> None:
    reg = make_registry(r1_reasons=["POSITIVE CONTROL FAILED", "NO PHYSICAL COUNTER"], cold_outcomes=["ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD"], manifest={"quiet_exhausted": True, "write_budget_declined": True}, thresholds=default_thresholds(0.4, True))
    res = analysis.analyse(reg)
    assert res["EQ-A"]["label"] == "ENGINEERING NOT EVALUABLE (NO PHYSICAL COUNTER)"
    assert res["EQ-A"]["reasons"] == ["NO PHYSICAL COUNTER", "POSITIVE CONTROL FAILED", "STORE CANNOT BE HELD COLD", "WRITE BUDGET EXHAUSTED"]  # no TIMING SPREAD and no MACHINE NOT QUIET on EQ-A
    assert res["EQ-B"]["reasons"] == ["NO PHYSICAL COUNTER", "POSITIVE CONTROL FAILED", "STORE CANNOT BE HELD COLD", "TIMING SPREAD", "MACHINE NOT QUIET", "WRITE BUDGET EXHAUSTED"]
    assert res["EQ-D"]["reasons"] == ["NO PHYSICAL COUNTER", "POSITIVE CONTROL FAILED", "STORE CANNOT BE HELD COLD", "MACHINE NOT QUIET", "WRITE BUDGET EXHAUSTED"]
    assert res["EQ-D"]["label"] == "ENGINEERING NOT EVALUABLE (NO PHYSICAL COUNTER)"


@pytest.mark.parametrize("reason", ["NO PHYSICAL COUNTER", "CACHE NOT DEFEATED", "POSITIVE CONTROL FAILED"])
def test_each_r1_reason_alone(reason: str) -> None:
    res = analysis.analyse(make_registry(r1_reasons=[reason]))
    for line in ("EQ-A", "EQ-B", "EQ-D"):
        assert res[line]["label"] == f"ENGINEERING NOT EVALUABLE ({reason})"


def test_store_cannot_be_held_cold_and_write_budget_each_alone() -> None:
    res = analysis.analyse(make_registry(cold_outcomes=["COLD", "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD"]))
    assert res["EQ-A"]["label"] == "ENGINEERING NOT EVALUABLE (STORE CANNOT BE HELD COLD)"
    res = analysis.analyse(make_registry(manifest={"write_budget_declined": True}))
    assert res["EQ-B"]["label"] == "ENGINEERING NOT EVALUABLE (WRITE BUDGET EXHAUSTED)"
    res = analysis.analyse(make_registry(cold_outcomes=["COLD"]))
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"


def test_machine_not_quiet_applies_to_b_and_d_only() -> None:
    res = analysis.analyse(make_registry(manifest={"quiet_exhausted": True}))
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"
    assert res["EQ-B"]["label"] == res["EQ-D"]["label"] == "ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET)"


# --- ENGINEERING STOP ---------------------------------------------------------------------------------------------------------------------------------
def test_engineering_stop_refuses_and_is_never_a_label() -> None:
    with pytest.raises(analysis.AnalysisRefused, match="DATA MISMATCH"):
        analysis.analyse(make_registry(stops=[{"cause": "DATA MISMATCH", "resolved": False}]))
    with pytest.raises(analysis.AnalysisRefused, match="PREDICTION MISMATCH"):
        analysis.analyse(make_registry(stops=[{"cause": "PREDICTION MISMATCH"}]))
    res = analysis.analyse(make_registry(stops=[{"cause": "DATA MISMATCH", "resolved": True}]))  # resolved by a complete rerun on the spare
    assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"
    reg = make_registry()
    reg["passes"][5]["parity_ok"] = False
    with pytest.raises(analysis.AnalysisRefused, match="DATA MISMATCH"):
        analysis.analyse(reg)
    reg = make_registry()
    reg["passes"][5]["memory_guard_exceeded"] = True
    with pytest.raises(analysis.AnalysisRefused, match="MEMORY GUARD"):
        analysis.analyse(reg)


# --- the report ---------------------------------------------------------------------------------------------------------------------------------
def render(reg: dict | None = None) -> str:  # type: ignore[type-arg]
    return report.render_report(analysis.analyse(reg or make_registry()), {"device": {"smart_status": "Verified"}, "write_ledger_bytes": 123, "hours": 1.0}, GRID)


def split_sections(text: str) -> tuple[str, str]:
    eng, sci = text.split("## SCIENTIFIC NEURAL-MEMORY ADVANTAGE")
    return eng, sci


def test_report_keeps_the_two_verdicts_apart() -> None:
    text = render()
    eng, sci = split_sections(text)
    assert "SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)" in sci and "SCIENTIFIC NOT EVALUABLE" not in eng
    for label in ("BYTES CONFIRMED", "COST TABLE REGISTERED", "CONTIGUOUS REQUEST", "COST PROPORTIONAL", "ENGINEERING NOT EVALUABLE"):
        assert label not in sci
    assert sci.count("\n1. ") == 1 and sci.count("\n2. ") == 1  # its two reasons
    assert "3,145,728" in sci and "lane L" in sci
    # nothing joins them: no engineering label in a sentence with the scientific one
    for line in text.splitlines():
        assert not ("SCIENTIFIC" in line and ("EQ-" in line or "BYTES" in line))


def test_report_carries_the_arithmetic_heading_and_not_readable_counters() -> None:
    text = render()
    assert text.count("ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH") >= 2
    assert text.count("NOT READABLE") >= 3
    arith = text.split("### ARITHMETIC ONLY")[1].split("### Device record")[0]
    assert "analytical" in arith and "No query is issued" in arith


def test_report_makes_no_claim_about_the_memory_accuracy_or_trained_tree() -> None:
    text = render()
    limits_start = text.index("### What the engineering result can and cannot say")
    limits_end = text.index("## SCIENTIFIC NEURAL-MEMORY ADVANTAGE")
    outside = text[:limits_start] + text[limits_end:]
    for word in ("ArborLM", "accuracy", "trained tree", "advantage supported", "speeds up", "faster", "success"):
        assert word not in outside.replace("SCIENTIFIC NEURAL-MEMORY ADVANTAGE", ""), word
    assert "T-OQ" not in text or "ARITHMETIC ONLY" in text


def test_report_for_not_evaluable_lines_prints_reasons_and_descriptive_figures() -> None:
    text = render(make_registry(manifest={"quiet_exhausted": True}, thresholds=default_thresholds(0.4, True)))
    assert "ENGINEERING NOT EVALUABLE (TIMING SPREAD)" in text and "ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET)" in text
    assert "Figures below are descriptive" in text
    assert "### ARITHMETIC ONLY" not in text  # no arithmetic table over a table that is not registered


def test_report_names_the_replaced_block_and_harness_tags() -> None:
    text = render(make_registry(spare=True, quiet={2: (QUIET_OK, QUIET_BAD)}, harness_ns={32: 10**6}))
    assert "E2|r2|a1 was invalid and was replaced once by the spare E2|r6|a1" in text
    assert "HARNESS-LIMITED" in text


def test_synthetic_grid_matches_the_config() -> None:
    cfg = core.load_config()
    assert [list(c) for c in GRID] == [list(c) for c in core.registered_geometry(cfg).cells()]
    assert synthetic.N_OF == dict(zip(cfg["cells"]["sizes"], cfg["cells"]["requests_per_pass"], strict=True))
