# ruff: noqa: E501
"""P10IS1 report (ADR-0024 section 18): the text prints every replicate, panel, cell and reading the rules name, each section names its run and stage, the standing tag follows every positive label, the table of labels
unreachable without measured CPU cost is printed, and a refused or incomplete analysis prints no outcome. Self-check only."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is1 import analysis, core, report, synthetic  # noqa: E402
from studies.p10is1 import labels as L  # noqa: E402


@pytest.fixture(scope="module")
def text() -> str:
    res = analysis.analyze(synthetic.build())
    return report.render(res, throughput={"state": "PAUSED"}, caps={"train": 12, "total": 60})


def test_every_positive_label_has_the_standing_tag(text: str) -> None:
    assert L.untagged_positive_labels(text) == []
    assert f"CAPACITY-POSITIVE [{core.STANDING_TAG}" in text and f"SATURATION-PROPORTIONAL [{core.STANDING_TAG}" in text and f"EFFICIENCY-POSITIVE [{core.STANDING_TAG}" in text
    assert text.count("DICT DOMINATES ON THIS TASK") >= 4


def test_every_capacity_outcome_prints_block_x_not_tested_and_the_lane_line(text: str) -> None:
    assert "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED" in text and "1,024 TO 16,384 SLOTS" in text
    assert core.LANE_L_NOT_LICENSED in text
    cap_head = next(line for line in text.splitlines() if line.startswith("**CAPACITY-POSITIVE"))
    assert "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED" in cap_head


def test_every_replicate_and_panel_of_the_saturation_pairs_is_printed(text: str) -> None:
    sec = text[text.index("## C-SATURATION") : text.index("## C-EFFICIENCY")]
    rows = [line for line in sec.splitlines() if line.startswith("| 1K→4K |")]
    assert len(rows) >= 5 * 2 * 4  # F-OQ, F-OQ-IVF, T-OQ, H8 x 5 replicates x 2 panels
    assert {int(m.group(1)) for line in rows if (m := re.match(r"\| 1K→4K \| (\d) \|", line))} == {1, 2, 3, 4, 5}
    assert "NOT A PROPERTY OF THE STORE ALONE" in sec and "EIGHT FACTS PER SLOT" in sec


def test_a_not_full_replicate_is_printed_not_dropped() -> None:
    lv = synthetic.positive_levels()
    lv[("F-OQ", 8192, 1024)] = (3.0, 400000)
    lv[("F-OQ", 8192, 4096)] = (0.36, 8192)
    res = analysis.analyze(synthetic.build(levels=lv, u_run={**synthetic.U0, "8K/1K": 262144}))
    t = report.render(res)
    sec = t[t.index("## C-SATURATION") : t.index("## C-EFFICIENCY")]
    foq = sec[sec.index("### F-OQ:") : sec.index("### F-OQ-IVF:")]
    assert foq.count("NOT FULL") >= 5 * 2  # five replicates x two panels, each printed with its verdict
    assert "NOT FULL WITHIN BUDGET" in t


def test_dense_labels_print_every_reading_and_the_saturation_detail(text: str) -> None:
    assert "dense, larger cell 8K/4K: STORE NOT BEHIND [" in text and "MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 0" in text
    assert "dense at saturation, loaded cell 32K/4K: STORE HOLDS MORE AT SATURATION [" in text and "dense at saturation, loaded cell 8K/1K: SAME AT SATURATION" in text
    assert "d_sat at the shorter length" in text and "D-OQ a_use at U_P" in text


def test_sections_name_their_run_and_stage_and_counts_say_what_they_count(text: str) -> None:
    for stage in ("analysis (capacity)", "analysis (saturation)", "analysis (efficiency)", "train (ladder)", "throughput"):
        assert f"stage: {stage}" in text
    assert text.count("_Run: SYNTHETIC REGISTRY") >= 5
    assert re.search(r"Counts: 155 planned cells \(cells\); \d+ read records of \d+ expected \(reads;", text)
    assert "Items beyond the stop are recorded NOT REACHED, not missing" in text
    assert "THROUGHPUT PENDING" in text and "Caps (the plan's figures, in charged hours): train 12, total 60" in text


def test_the_unreachable_table_is_printed(text: str) -> None:
    assert "Labels that cannot be reached without measured CPU cost" in text
    for row in report.UNREACHABLE:
        assert row[1] in text
    assert "`CAPACITY-POSITIVE` (`STORE NOT BEHIND` needs MC-T)" in text


def test_mc_t_not_measured_is_stated_beside_the_outcomes() -> None:
    t = report.render(analysis.analyze(synthetic.build(cpu=None)), throughput={"state": "NOT MEASURED"})
    assert "MC-T NOT MEASURED (by a recorded decision)" in t and "MATCHED COMPUTE IN MC-A ONLY" in t and "MEASURED COST NOT AVAILABLE: a positive was not reachable" in t
    assert "(E-A ONLY; MEASURED COST NOT AVAILABLE)" in t and "THROUGHPUT NOT MEASURED (by a recorded decision)" in t and L.untagged_positive_labels(t) == []


def test_refused_incomplete_and_paused_print_no_outcome() -> None:
    for status, expect in (({"item_errors": ["e"]}, "ENGINEERING STOP — ITEM ERRORS"), ({"gate_failures": ["g"]}, "ENGINEERING-FAILURE"), ({"paused": ["QUIET CONDITION NOT MET"]}, "PAUSED")):
        t = report.render(analysis.analyze(synthetic.build(status=status)))
        bare = re.sub(r"`[^`]*`", "", t)  # the table of unreachable labels names labels between back-quotes; nothing else may
        assert f"Status: **{expect}**" in t and "No outcome is printed on any line" in t and "CAPACITY-POSITIVE" not in bare and "CAPACITY-NEGATIVE" not in bare and "EFFICIENCY-POSITIVE" not in bare
    inc = report.render(analysis.analyze(synthetic.build(drop=lambda k: k.endswith("u00000512|main") and "_n1024_d1_" in k)))
    assert "Status: **INCOMPLETE**" in inc and "registered reads with no record" in inc and "(reads, not cells)" in inc


def test_reference_qualification_and_failures_are_printed() -> None:
    def ex(a: str, f: int, n: int, d: int, u: int, r: str, p: str) -> int:
        return 300 if (a, f, n, d, u) == ("R2", 8192, 16384, 3, 4096) else 0

    res = analysis.analyze(synthetic.build(excess=ex, qualification={"8192": {"0.5": ["a", "b"]}}))
    t = report.render(res)
    assert "NOT QUALIFIED AT row 8192 fraction 0.5: ['c']" in t
    assert "REFERENCE FAILED DEP" not in t  # R2's failure of a condition that was already unqualified there is not a failure of a qualified one
    t2 = report.render(analysis.analyze(synthetic.build(excess=ex)))
    assert "REFERENCE FAILED DEP: row 8192, replicate 3, update 4096, conditions ['c']" in t2
