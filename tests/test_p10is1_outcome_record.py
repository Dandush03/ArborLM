# ruff: noqa: E501
"""P10IS1 outcome record (results/p10is1-run-2026-11-21/): the copied records are what the supplement manifest says they are, the labels in the record are the printed ones, the ledger figures in the record equal the ledger,
and the record carries its plain statements. Self-check only: not an independent review, not Astra validation, not human approval."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "p10is1-run-2026-11-21"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_the_copied_supplement_files_are_the_ones_the_manifest_names() -> None:
    man = json.loads((OUT / "SUPPLEMENT_MANIFEST.json").read_text())
    for rel, name in (("report/REPORT_SUPPLEMENT.md", "REPORT_SUPPLEMENT.md"), ("analysis/analysis_supplement.json", "analysis_supplement.json"), ("ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json", "ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json")):
        assert sha(OUT / name) == man["files_sha256"][rel], name
    assert man["stage_manifests"] == {"baselines": "COMPLETE", "evaluate": "COMPLETE"} and man["item_errors"] == 0 and man["analysis_status"] == "COMPLETE"
    stop = json.loads((OUT / "ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json").read_text())
    assert stop["status"] == "ENGINEERING STOP — ANALYSIS LOADER DEFECT" and stop["traceback_count"] == 2 and "truncated" in stop["tracebacks_note"].lower()
    assert "{" not in "".join(ln[:1] for t in stop["tracebacks"] for ln in t.splitlines())
    for s in ("gates", "timing", "train", "ladder", "evaluate", "baselines", "throughput"):
        assert json.loads((OUT / "stage_manifests" / f"{s}.json").read_text())["status"] == "COMPLETE", s


def test_the_labels_in_the_record_are_the_printed_ones_and_the_analysis_json_agrees() -> None:
    text = (OUT / "OUTCOME.md").read_text()
    printed = (OUT / "REPORT_SUPPLEMENT.md").read_text()
    for label in ("**CAPACITY-NEGATIVE**", "**SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; arms F-OQ; EIGHT FACTS PER SLOT; 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED]**", "**EFFICIENCY-INCONCLUSIVE**"):
        assert label in printed, label
    for label in ("**C-CAPACITY: CAPACITY-NEGATIVE**", "**C-SATURATION: SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; arms F-OQ; EIGHT FACTS PER SLOT; 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED]**", "**C-EFFICIENCY: EFFICIENCY-INCONCLUSIVE**"):
        assert label in text, label
    res = json.loads((OUT / "analysis_supplement.json").read_text())["result"]
    assert res["lines"] == {"C-CAPACITY": "CAPACITY-NEGATIVE", "C-EFFICIENCY": "EFFICIENCY-INCONCLUSIVE", "C-SATURATION": "SATURATION-PROPORTIONAL"}
    assert (res["capacity"]["outcome"]["clause"], res["capacity"]["outcome"]["arms"], res["mct_measured"]) == ("(b)", ["F-OQ"], True)
    arms = res["capacity"]["arms"]
    mins = {a: min(p["a_use_large_up"] for rep in arms[a]["steps"]["C2"]["replicates"] for p in rep["detail"]["panels"].values()) for a in arms}
    assert round(mins["F-OQ"], 3) == 0.907 and round(mins["H8"], 3) == 0.861 and round(mins["T-OQ"], 3) == 0.679 and round(mins["F-OQ-IVF"], 3) == 0.516  # the figures the record states
    assert arms["F-OQ"]["dense_cells"]["32K/16K"]["counts"] == {"D-BEST": 5, "MC-A": 0, "MC-C": 0, "MC-T": 0, "MU": 0}
    assert (res["counts"]["cells"], res["counts"]["reads_recorded"], res["counts"]["ladder_cells_with_not_reached"], sum(len(v) for v in res["not_reached"].values())) == (155, 2395, 45, 140)
    assert res["ladder_stops"] == {"2K/256": {"u_run": 196608}, "32K/4K": {"u_run": 393216}, "8K/1K": {"u_run": 98304}}


def test_the_ledger_figures_in_the_record_equal_the_ledger() -> None:
    led = json.loads((OUT / "ledger.json").read_text())["entries"]
    pre = json.loads((OUT / "ledger.before-evaluate-cap-extension.json").read_text())["entries"]
    assert led[: len(pre)] == pre and len(led) == len(pre) + 5  # the two extension entries and the three later stage entries
    ev = [e["seconds"] for e in led if e["stage"] == "evaluate" and not str(e["run"]).startswith("EXTENSION")]
    assert round(sum(ev), 1) == 3725.7 and round(sum(e["seconds"] for e in led if e["stage"] == "evaluate"), 1) == 125.7
    assert abs(sum(e["seconds"] for e in led) / 3600 - 15.676) < 0.001
    text = (OUT / "OUTCOME.md").read_text()
    for needle in ("3,725.7 s (1.035 h)", "15.676 h of the 52 h total cap", "7.709 h by the registered stages"):
        assert needle in text, needle


def test_the_record_carries_its_plain_statements_and_the_disclosures() -> None:
    text = (OUT / "OUTCOME.md").read_text()
    for needle in (
        "**Not accepted by the human lead yet. Astra review: NOT_PERFORMED.** Nothing here is a success claim.", "component evidence only", "capability parity", "on this task the dense map is the better use of the parameters",
        "the single most likely outcome", "clause (b), carried by F-OQ alone", "It must not be read as a dense lead at matched compute", "ENGINEERING STOP — ANALYSIS LOADER DEFECT", "may overrule it in favour of an amending freeze (route (a))",
        "ladder's continuation path ran for the first time", "although MC-T was measured", "98 of 110", "Approve 1 h", "`Astra review: NOT_PERFORMED`",
    ):
        assert needle in text or needle.lower() in text.lower(), needle
    for n in range(1, 13):
        assert f"\n{n}. **" in text, n  # the twelve numbered disclosures
    assert (OUT / "recomputation" / "RECOMPUTATION.md").is_file() and (OUT / "audits" / "AUDIT_P10IS1_CAP_EXTENSION_3.md").is_file()
    assert "The text of the lead's ruling" in text  # the one item the author of the record could not verify is marked pending
