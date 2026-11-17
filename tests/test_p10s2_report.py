# ruff: noqa: E501
"""P10S2 oracle qualification: every printed class, mechanism, router, composition and cost line, table, caption, machine-readable record and log summary is headed by the oracle-assisted line (ADR-0022
section 11.3), checked on synthetic records of the whole registry for every outcome row. The human lead's rule: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results."
Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import cell, cells_of, rec_outcome, set_panels, study  # noqa: E402

from studies.p10s2 import analysis, core, output, recompute, report  # noqa: E402

LINE = core.ORACLE_LINE
POSITIVE = ("ACQUIRES-AND-RETAINS", "TRANSFER-POSITIVE", "QUALIFIED", "COMPOSES", "TRAINING COST COMPARABLE", "FEWER VALUE ROWS ACTIVE")


def scenarios() -> dict[str, Callable[[dict[str, Any]], None]]:
    def forgets(s: dict[str, Any]) -> None:
        set_panels(s, None, "MAF", "AB", 0.15, 0.78)
        set_panels(s, None, "MAF", "BA", 0.78, 0.15)

    def none_new(s: dict[str, Any]) -> None:
        set_panels(s, None, "MAF", "AB", 0.8, 0.1)
        set_panels(s, None, "MAF", "BA", 0.1, 0.8)

    def no_acq(s: dict[str, Any]) -> None:
        set_panels(s, None, "ST1", "AB", 0.15, 0.1)
        set_panels(s, None, "ST1", "BA", 0.1, 0.15)

    def control_failed(s: dict[str, Any]) -> None:
        cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["ablations"]["E_A"]["code_perm"]["mean"] = 0.7

    def missing(s: dict[str, Any]) -> None:
        del s["replicates"][1]["cells"]["r1/MAF/AB"]

    return {
        "row 7": lambda s: None,
        "row 8 (rejected)": lambda s: cell(s, 1, "MII", "AB")["extras"]["consolidation"].update(rejected=True, published=False),
        "row 8 (inert)": lambda s: cell(s, 0, "MII", "BA")["extras"]["consolidation"].update(below_floor=True),
        "row 6": lambda s: cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["gen"].update(loss_increase=0.5),
        "row 9": forgets,
        "row 10": none_new,
        "row 11": lambda s: set_panels(s, None, "MAF", "BA", 0.1, 0.8),
        "row 12": lambda s: [set_panels(s, None, "MAF", "AB", 0.8, 0.45), set_panels(s, None, "MAF", "BA", 0.45, 0.8)],
        "row 5": control_failed,
        "row 4": no_acq,
        "row 3": lambda s: s["prefreeze"].update(stop="TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"),
        "row 2 (missing)": missing,
        "row 2 (failed)": lambda s: cell(s, 0, "MAF", "AB").update(status="failed"),
        "row 1": lambda s: s["gates"]["G5"].update(ok=False, problems=["x"]),
        "non-finite": lambda s: set_panels(s, 0, "MAF", "AB", 0.8, "nan"),
        "undefined gap": lambda s: s["baseline"]["teacher"].update(E_B={"mean": 0.3, "subsample_mean": 0.3, "exact_rate": 0.9}),
    }


def blocks(text: str) -> list[list[str]]:
    return [[ln for ln in b.split("\n") if ln.strip()] for b in text.split("\n\n") if b.strip()]


@pytest.mark.parametrize("name", list(scenarios()))
def test_every_outcome_row_reports_under_the_oracle_line(name: str) -> None:
    out = analysis.analyze(study(tweak=scenarios()[name]))
    text = report.render_report(out)
    output.check_text(text)
    guarded_blocks = 0
    for b in blocks(text):
        if any(output.is_guarded(ln) for ln in b):
            guarded_blocks += 1
            assert b[0] == LINE, (name, b[:2])  # an independent re-check of the module's own test: the line is the first line of every block that holds a guarded line
    assert guarded_blocks >= 3
    assert out["label_with_design"] in text and "2 replicates, U = 2000" in text  # every label is printed with "(n replicates, U = ...)"
    assert "Table 1." in text and LINE in text.split("Table 1.")[0].split("\n\n")[-1] + "\n"  # the caption of a table sits in the table's block, under the line
    lines = text.split("\n")
    for k, ln in enumerate(lines):
        if ln.startswith("| mechanism |") or ln.startswith("| mechanism/order |"):
            j = k
            while lines[j].strip() and j > 0:
                j -= 1
            assert lines[j + 1] == LINE  # the table's block starts with the line, then the caption, then the header row
            assert lines[j + 2].startswith("Table ")
    assert "Astra review: NOT_PERFORMED" in text and "What S2 cannot establish" in text
    stripped = text.replace(LINE + "\n", "").replace(LINE, "")
    assert output.positive_wording_without_line(stripped)  # without the line the same text is refused


@pytest.mark.parametrize("name", list(scenarios()))
def test_every_outcome_row_gives_a_machine_readable_record_with_the_line(name: str, tmp_path: Path) -> None:
    out = analysis.analyze(study(tweak=scenarios()[name]))
    rec = report.render_json(out)
    assert rec["oracle_line"] == LINE and rec["outcome"]["oracle_line"] == LINE
    for mech, by in rec["outcome"]["classes"].items():
        for o, c in by.items():
            assert c["oracle_line"] == LINE and "class" in c, (mech, o)
    output.check_record(rec)
    path = tmp_path / "outcome.json"
    output.write_record(path, rec)
    back = json.loads(path.read_text())
    assert back["oracle_line"] == LINE and back["outcome"]["classes"]["M-append-frozen"]["AB"]["oracle_line"] == LINE
    bad = json.loads(path.read_text())
    del bad["outcome"]["classes"]["M-append-frozen"]["AB"]["oracle_line"]
    with pytest.raises(output.OracleLineMissing):
        output.check_record(bad)  # the oracle-assisted line is a field of the same record as each class
    bad2 = json.loads(path.read_text())
    del bad2["outcome"]["oracle_line"]
    with pytest.raises(output.OracleLineMissing):
        output.write_record(tmp_path / "refused.json", bad2)
    assert not (tmp_path / "refused.json").exists()
    wrong = json.loads(path.read_text())
    wrong["oracle_line"] = "oracle-assisted"
    with pytest.raises(output.OracleLineMissing):
        output.check_record(wrong)  # a shortened line is not the line


@pytest.mark.parametrize("word", POSITIVE)
def test_no_positive_wording_can_be_emitted_without_the_line(word: str, capsys: pytest.CaptureFixture[str]) -> None:
    line = f"result: {word} (2 replicates, U = 2000)"
    with pytest.raises(output.OracleLineMissing):
        output.check_text(line)
    with pytest.raises(output.OracleLineMissing):
        output.check_text("plain heading\n\n" + line)  # a heading is not the line
    with pytest.raises(output.OracleLineMissing):
        output.check_text(f"{LINE}\n\nplain\n\n{line}")  # the line must head the block that holds the word, not an earlier block
    head = f"{LINE}\n{core.COMBINED_LINE}" if word == "COMPOSES" else LINE  # a composition word needs the second fixed line as well (addendum section 9)
    output.check_text(f"{head}\n{line}")
    if word == "COMPOSES":
        with pytest.raises(output.OracleLineMissing, match="second fixed line"):
            output.check_text(f"{LINE}\n{line}")
    output.emit_plain(line)  # the plain printer never prints a guarded line bare: it goes through emit and is printed under the line
    assert capsys.readouterr().out.splitlines()[0] == LINE
    output.emit([line])
    out = capsys.readouterr().out
    assert out.splitlines()[0] == LINE and line in out and (out.splitlines()[1] == core.COMBINED_LINE) == (word == "COMPOSES")  # a terminal or log summary is printed only under the line(s)
    with pytest.raises(output.OracleLineMissing):
        output.write_text(Path("/nonexistent-dir") / "x.md", line)  # a text file is refused before anything is written
    assert output.positive_wording_without_line(line) and not output.positive_wording_without_line(f"{head}\n{line}")


def test_the_writers_refuse_text_and_records_without_the_line(tmp_path: Path) -> None:
    with pytest.raises(output.OracleLineMissing):
        output.write_text(tmp_path / "r.md", "TRANSFER-POSITIVE (append-frozen) (4 replicates, U = 2000)\n")
    assert not (tmp_path / "r.md").exists()
    with pytest.raises(output.OracleLineMissing):
        output.write_record(tmp_path / "r.json", {"label": "TRANSFER-POSITIVE (append-frozen)"})
    with pytest.raises(output.OracleLineMissing):
        output.write_record(tmp_path / "r2.json", {"classes": {"M-append-frozen": {"AB": {"class": "ACQUIRES-AND-RETAINS"}}}})
    output.write_record(tmp_path / "ok.json", output.guarded({"label": "INCOMPLETE"}))
    output.write_text(tmp_path / "ok.md", output.block(["TRANSFER-NEGATIVE: FORGETTING (3 replicates, U = 1000)"]))
    assert json.loads((tmp_path / "ok.json").read_text())["oracle_line"] == LINE and (tmp_path / "ok.md").read_text().startswith(LINE)
    output.write_text(tmp_path / "plain.md", "a heading with a count of 4\n")  # a line with no class, label or cost reading needs no header


def test_every_guarded_word_of_the_adr_is_guarded() -> None:
    for w in POSITIVE:
        assert w in core.GUARDED_WORDS
    for w in ("TRANSFER-NEGATIVE", "TRANSFER-INCONCLUSIVE", "FORGETS", "NO-NEW-CAPABILITY", "RETENTION BY INERTIA", "NOT REPLICATED", "INTERMEDIATE", "ENGINEERING-FAILURE", "INCOMPLETE", "NOT_EVALUATED", "BY CONSTRUCTION", "NOT STARTED"):
        assert w in core.GUARDED_WORDS
    for w in ("NO ADVANTAGE OVER SEPARATE ADAPTERS", "EQUIVALENT TO A WORD TABLE", "RETRIEVAL SUFFICES", "LEXICON-EQUIVALENT", "TEACHER-EQUIVALENT-TO-GOLD", "BELOW JOINT BOUND", "BELOW ADAPTER JOINT", "TASK-CODED SPARSE RETENTION", "APPEND COST", "EXACT-MATCH WEAK", "ROUTER (keyword-level)"):
        assert w in core.GUARDED_WORDS  # the annotations of section 11.4
    assert "NOT QUALIFIED" in "ROUTER (keyword-level) NOT QUALIFIED" and output.is_guarded("ROUTER (keyword-level) NOT QUALIFIED") and output.is_guarded("UNQUALIFIED")  # a negation of a positive word is guarded as well
    assert not output.is_guarded("seeds and sizes") and not output.is_guarded("Astra review: NOT_PERFORMED")


def test_cost_composition_router_and_annotation_lines_sit_under_the_line() -> None:
    out = analysis.analyze(study())
    text = report.render_report(out)
    for needle in ("FEWER VALUE ROWS ACTIVE", "TRAINING COST", "ROUTER (keyword-level) QUALIFIED", "NO ADVANTAGE OVER SEPARATE ADAPTERS", "stored parameters (arithmetic"):
        i = text.index(needle)
        start = text.rfind("\n\n", 0, i) + 2
        assert text[start:].startswith(LINE), needle  # each such line's block begins with the oracle-assisted line
    assert text.count(LINE) >= 5


def test_the_terminal_summary_is_headed_by_the_line(capsys: pytest.CaptureFixture[str]) -> None:
    out = analysis.analyze(study())
    output.emit(report.summary_lines(out))
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == LINE and "TRANSFER-POSITIVE" in lines[1] and any("M-append-frozen: AB ACQUIRES-AND-RETAINS" in x for x in lines)
    incomplete = analysis.analyze(study(tweak=scenarios()["row 2 (missing)"]))
    output.emit(report.summary_lines(incomplete))
    assert capsys.readouterr().out.splitlines()[0] == LINE


def test_report_after_a_recomputation_carries_the_line_on_its_state_line() -> None:
    s = study()
    rec = cells_of(s)
    import copy

    r2 = copy.deepcopy(rec)
    r2["r0/ETABLE/A"]["scores"]["r0/ETABLE/A"]["panels"]["E_A"]["mean"] = 0.779
    out = rec_outcome(s, r2, recompute.FROZEN)
    text = report.render_report(out)
    assert "Independent recomputation: state complete" in text and "r0/ETABLE/A" in text
    i = text.index("Independent recomputation")
    assert text[text.rfind("\n\n", 0, i) + 2 :].startswith(LINE)
    out2 = rec_outcome(s, None, recompute.FROZEN)
    text2 = report.render_report(out2)
    assert "NO CLASS (INCOMPLETE)" in text2 and "INCOMPLETE" in text2.split("\n\n")[2] and not output.positive_wording_without_line(text2)
    assert "ACQUIRES-AND-RETAINS" not in text2 and "TRANSFER-POSITIVE" not in text2  # no class is printed when the recomputation did not complete


def test_the_report_makes_no_claim_of_success_and_names_what_it_cannot_establish() -> None:
    text = report.render_report(analysis.analyze(study()))
    for phrase in ("Autonomous learned memory: addresses and routes are supplied by rule.", "A failure of the ArborLM concept, whatever the outcome.", "That MPS-trained snapshots would be reproduced by re-running."):
        assert phrase in text
    assert "Astra review: NOT_PERFORMED" in text and "not human approval" in text
    assert f"- {core.LEAD_RULE}" in text  # re-check C, m1: the human lead's sentence is printed, exactly (the one place the phrase may appear)
    for forbidden in ("autonomous learned-memory success", "validated by Astra", "ASTRA VALIDATED"):
        assert forbidden not in text.replace(core.LEAD_RULE, "")
    assert len(report.NOT_ESTABLISHED) == 10


def test_lseq_is_printed_with_no_permutation_control() -> None:
    text = report.render_report(analysis.analyze(study()))
    row = next(ln for ln in text.split("\n") if ln.startswith("| L-seq |"))
    assert "NO PERMUTATION CONTROL (ADAPTER)" in row and "NO PERMUTATION CONTROL (ADAPTER)" not in next(ln for ln in text.split("\n") if ln.startswith("| M-seq |"))
    assert not output.positive_wording_without_line(text)
    assert output.positive_wording_without_line("NO PERMUTATION CONTROL (ADAPTER)")


def test_gen_table_and_router_diagnostic_are_printed_beside_the_classes() -> None:
    def tweak(s: dict[str, Any]) -> None:
        cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["gen"].update(loss_increase=0.5, false_trigger_count={"marker": 3, "ordinary": 1})
        for r in range(2):
            s["replicates"][r]["routers"]["AB"]["diagnostic_first_marker"] = {"count": 1, "n": 4, "rate": 0.25}

    out = analysis.analyze(study(tweak=tweak))
    assert len(out["gen_table"]) == 2 * 11 and {r["cell"].split("/")[1] for r in out["gen_table"]} == {"ST1", "MAF", "MII", "MSEQ", "MJOINT", "LSEQ"}  # every ST1 and stage-2 snapshot
    text = report.render_report(out)
    i = text.index("Table 3. General quality under the keyword router")
    assert text[text.rfind("\n\n", 0, i) + 2 :].startswith(LINE)  # the table and its diagnostic lines sit under the oracle-assisted line
    assert "| r1/MAF/BA | 0.500 | 0.001 | False | 3 / 1 |" in text and "keyword router stayed silent" in text and "0.250 (1 of 4 windows)" in text and "enters no rule" in text
    rec = report.render_json(out)
    assert rec["outcome"]["router_table"][0]["diagnostic_first_marker"]["rate"] == 0.25
