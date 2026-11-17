# ruff: noqa: E501
"""P10S2 fix lane C, the oracle-assisted line and the report (audit C-m4, C-m5, C-m6 of the audit, the lead's ruling on the bootstrap seed). The line is attached structurally: the audit's own
counterexamples are tried here. Synthetic records, test seeds 229001-229999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import io
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import cell, panel, study  # noqa: E402

from studies.p10s2 import analysis, core, output, report  # noqa: E402
from studies.p10s2 import classes as C  # noqa: E402

LINE = core.ORACLE_LINE


def printed(fn: Any, *args: Any) -> str:
    buf = io.StringIO()
    fn(*args, buf)
    return buf.getvalue()


# --- the audit's counterexamples, through emit and emit_plain ---------------------------------------------------------------------------------------
AUDIT_LINES = [
    C.value_rows(5000.0, 2419200.0, 8192)["line"],
    C.value_rows(5e6, 2419200.0, 8192)["line"],  # "value rows active not fewer": no listed word
    C.stored_size_line(134515008, 8192, [73944309, 74669178], 0.8, 0.7, 576),
    "teacher inference cost per accepted training item: 0.4 s",
    "replicate 0, router AB: route accuracy {'A': 1.0, 'B': 1.0, 'general': 1.0}",
    "r0/MAF/AB GEN loss increase 0.001: gate passes; the keyword router stayed silent",
    "M-ii: AB ACQUIRES-AND-RETAINS",
    "label: transfer-positive (append-frozen)",
    "M-append-frozen: Acquires-And-Retains in both orders",
    "rehearsal record written to x; rung rule outcome: NOT STARTED: BUDGET",
    "a mechanism line without any listed word: mechanism M-seq kept its first capability",
    "C1 M-append-frozen: composes in both orders",
]


@pytest.mark.parametrize("line", AUDIT_LINES)
def test_emit_always_heads_what_it_prints_with_the_line(line: str) -> None:
    out = printed(output.emit, [line]).splitlines()
    assert out[0] == LINE and line in out


@pytest.mark.parametrize("line", AUDIT_LINES)
def test_emit_plain_never_prints_a_guarded_line_bare_and_never_crashes(line: str) -> None:
    out = printed(output.emit_plain, line).splitlines()
    assert out[0] == LINE and line in out  # printed under the line, whatever the case of the words (the audit's A7-A9)


def test_emit_attaches_the_line_even_to_a_line_with_no_reading() -> None:
    assert printed(output.emit, ["seeds and sizes"]).splitlines()[0] == LINE  # structural: the path to the terminal for results always attaches it
    assert printed(output.emit_plain, "freeze files written: plan.json") == "freeze files written: plan.json\n"  # a path or count needs none


def test_the_second_fixed_line_follows_any_composition_line_in_any_case() -> None:
    for line in ("C2 L-sep: COMPOSITION INCONCLUSIVE", "C1 M-ii: composes", "C2 M-joint: does not compose"):
        out = printed(output.emit, [line]).splitlines()
        assert out[0] == LINE and out[1] == core.COMBINED_LINE
        with pytest.raises(output.OracleLineMissing, match="second fixed line"):
            output.check_text(f"{LINE}\n{line}")


@pytest.mark.parametrize(
    "rec",
    [
        {"router_table": [{"accuracy": {"A": 1.0}}]},
        {"gen": {"M-append-frozen": True}},
        {"cost_lines": ["TRAINING COST COMPARABLE"]},
        {"Class": "ACQUIRES-AND-RETAINS"},
        {"summary": ["TRANSFER-POSITIVE (append-frozen)"]},
        {"notes": ["the label is transfer-positive"]},
        {"GEN_TABLE": [1]},
        {"verdicts": {"gate/G1": True}},
        {"x": {"y": {"classes": {}}}},
    ],
)
def test_the_audits_record_counterexamples_are_refused(rec: dict[str, Any], tmp_path: Path) -> None:
    with pytest.raises(output.OracleLineMissing):
        output.check_record({"oracle_line": LINE, "wrapper": rec} if "x" not in rec else {"oracle_line": LINE, **rec})  # a nested mapping needs the line as a field of its own
    with pytest.raises(output.OracleLineMissing):
        output.write_record(tmp_path / "r.json", rec)  # and a record without the line at its root is never written
    assert not (tmp_path / "r.json").exists()


def test_write_record_requires_the_line_at_the_root_even_for_a_record_with_no_guarded_field(tmp_path: Path) -> None:
    with pytest.raises(output.OracleLineMissing):
        output.write_record(tmp_path / "plain.json", {"anything": 1})
    output.write_record(tmp_path / "ok.json", {"oracle_line": LINE, "anything": 1})
    assert json.loads((tmp_path / "ok.json").read_text())["oracle_line"] == LINE


def test_stamp_and_check_agree_on_every_mapping_of_a_real_outcome_record() -> None:
    out = analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=20)
    rec = report.render_json(out)  # render_json runs check_record on the stamped record
    assert rec["oracle_line"] == LINE
    assert rec["outcome"]["router_table"][0]["oracle_line"] == LINE if rec["outcome"]["router_table"] else True
    assert rec["outcome"]["recomputation"]["oracle_line"] == LINE if "recomputation" in rec["outcome"] else True
    assert rec["outcome"]["combined_line"] == core.COMBINED_LINE  # the mapping that carries a composition field carries the second fixed line


def test_the_whole_report_goes_through_blocks_notes_included() -> None:
    text = report.render_report(analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=20))
    output.check_text(text)
    for blk in text.split("\n\n"):
        lines = [ln for ln in blk.split("\n") if ln.strip()]
        if lines and not lines[0].startswith("#") and not lines[0].startswith("Standing:"):
            assert lines[0] == LINE, lines[0][:80]  # every block after the heading and the standing line is headed by the line
    assert text.index("## Notes") < text.index(LINE, text.index("## Notes")) and text.index("## What S2 cannot establish") < text.index(LINE, text.index("## What S2 cannot establish"))


# --- the terminal summary: class lines carry "(n replicates, U = ...)" -------------------------------------------------------------------------------
def test_terminal_class_lines_carry_the_design_suffix() -> None:
    out = analysis.analyze(study())
    lines = report.summary_lines(out)
    assert all(x.endswith("(2 replicates, U = 2000)") for x in lines if x.startswith(("M-", "L-")))
    assert any(x.startswith("M-append-frozen: AB ACQUIRES-AND-RETAINS, BA ACQUIRES-AND-RETAINS (2 replicates, U = 2000)") for x in lines)
    text = printed(output.emit, lines)
    assert text.splitlines()[0] == LINE and "label: TRANSFER-POSITIVE (append-frozen + consolidation) (2 replicates, U = 2000)" in text
    rep = report.render_report(out)
    row = next(ln for ln in rep.split("\n") if ln.startswith("| M-ii |"))
    assert row.endswith("(2 replicates, U = 2000) |")  # the class table carries it on every row as well as in its caption


# --- the bootstrap intervals (seed 220906, analysis stage only, a fresh generator per interval) ---------------------------------------------------------
def test_intervals_are_drawn_only_when_asked_and_with_one_fresh_generator_each() -> None:
    core.reset_seed_record()
    analysis.analyze(study())
    analysis.analyze(study(), set())
    assert core.seed_record() == []  # nothing in the analysis draws 220906 unless the analysis stage asks
    out = analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=50)
    uses = core.seed_record()
    drawn = [e for e in out["intervals"] if e["n"] is not None]  # a score with no per-item values (or a non-finite one) has no interval and draws nothing
    assert len(out["intervals"]) > 100 and len(uses) == len(drawn) > 50
    assert {u.seed for u in uses} == {core.partition_seeds("test")["bootstrap"]}  # the test-range stand-in of 220906
    assert [u.purpose for u in uses] == [f"bootstrap interval {e['name']}" for e in drawn]  # registry order, one generator per printed interval
    again = analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=50)
    assert again["intervals"] == out["intervals"]  # deterministic
    core.reset_seed_record()


def test_the_registered_seed_is_220906() -> None:
    core.reset_seed_record()
    g1, g2 = core.bootstrap_generator("registered-analysis", "a"), core.bootstrap_generator("registered-analysis", "b")  # the analysis stage's own seed mode
    assert [(u.seed, u.mode) for u in core.seed_record()] == [(220906, "registered-analysis")] * 2 and core.PARTITION_STREAMS["bootstrap"] == 220906
    with pytest.raises(core.SeedRefused):
        core.bootstrap_generator("registered-data", "c")  # 220906 is not a data-step seed
    with pytest.raises(ValueError):
        core.bootstrap_generator("registered-run", "c")  # a registered replicate process has no partition-side seeds
    import torch

    assert torch.equal(torch.randint(0, 100, (5,), generator=g1), torch.randint(0, 100, (5,), generator=g2))  # each is fresh: the same stream from its start
    core.reset_seed_record()


def test_interval_values_and_degenerate_cases() -> None:
    def tweak(s: dict[str, Any]) -> None:
        sn = cell(s, 0, "MAF", "AB")["scores"]["r0/MAF/AB"]
        sn["panels"]["E_A"] = {**panel(0.5), "items": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], "mean": 0.45, "single_reference": {"n": 3, "mean": 0.25}, "reference_counts": {"1": 3, "2": 5}}
        sn["panels"]["E_B"] = {**panel(0.5), "items": [0.1, "nan"]}
    out = analysis.analyze(study(tweak=tweak), bootstrap_mode="test", bootstrap_resamples=300)
    by = {e["name"]: e for e in out["intervals"]}
    e = by["r0/MAF/AB E_A"]
    assert 0.1 <= e["lo"] <= 0.45 <= e["hi"] <= 0.8 and e["n"] == 8 and e["single_reference"] == {"n": 3, "mean": 0.25}
    assert by["r0/MAF/AB E_B"]["lo"] is None and by["r0/MAF/AB E_B"]["n"] is None  # a non-finite item makes the interval NOT_EVALUATED, never a number
    assert by["r0/ST1/AB E_A"]["lo"] == by["r0/ST1/AB E_A"]["hi"]  # identical items: a point interval
    text = report.render_report(out)
    assert "| r0/MAF/AB E_A | 0.450 |" in text and "| 3 | 0.250 | {'1': 3, '2': 5} |" in text
    assert "single-reference" in text and "300 resamples, seed 220906" in text


def test_intervals_cover_combined_cells_baselines_assembled_arms_and_retrieval() -> None:
    names = [e["name"] for e in analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=20)["intervals"]]
    assert "Stage 0 student E_A" in names and "teacher E_B" in names
    assert "Stage 0 student C1" in names and "ensemble C2" in names
    assert "r0/MAF/AB C1" in names and "r1/LJOINT/- C2" in names and "r0/MAF/AB@append E_A" in names
    assert "r0 L-sep C1" in names and "r1 M-i-separate E_B" in names
    assert "r0 R-nn E_A" in names and "r1 R-icl E_B" in names
    cells_first = [n for n in names if n.startswith("r0/")]
    assert names.index("r0/ST1/AB E_A") < names.index("r0/MAF/AB E_A") < names.index("r1/ST1/AB E_A") and cells_first  # registry order


def test_the_report_says_when_intervals_were_not_computed_and_when_e_open_was_not_scored() -> None:
    text = report.render_report(analysis.analyze(study()))
    assert "Table 5. Scores with bootstrap intervals: NOT_EVALUATED" in text
    text2 = report.render_report(analysis.analyze(study(), bootstrap_mode="test", bootstrap_resamples=20))
    assert "E_open (descriptive only; at least one out-of-vocabulary word): not scored in this record (NOT_EVALUATED)" in text2


def test_report_prints_the_section_6_3_statistics_and_the_updates_and_rows() -> None:
    def tweak(s: dict[str, Any]) -> None:
        cell(s, 0, "MII", "AB")["extras"]["consolidation"].update(changed_row_share=0.37, g1_change=-0.02, below_floor=False)
        cell(s, 0, "MII", "AB")["train"][0].update(updates=2000, rows_per_update=64, replay_rows=32, batch=32, device="mps")
    text = report.render_report(analysis.analyze(study(tweak=tweak)))
    assert "| r0/MII/AB | False | True | False | 0.300 | 0.370 | -0.020 | selected on D_con, then confirmed on E |" in text
    assert "| r0/MII/AB | 2000 | 32 | 32 | 64 | mps |" in text and "Table 7." in text


def test_the_report_notes_name_the_readings_and_the_expected_not_evaluated() -> None:
    text = report.render_report(analysis.analyze(study()))
    for needle in ("expected to print NOT_EVALUATED", "E-table trains at the store's calibrated learning rate", "never on the GEN windows", "measured twice for the marker stratum", "any replicate or order"):
        assert needle in text
    assert "The bootstrap intervals over items are not computed" not in text and "partition-side seed that G9 does not allow" not in text
