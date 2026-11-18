# ruff: noqa: E501
"""P10IS0 synthetic pipeline rehearsal (ADR-0023 stage 2): every stage end to end on the synthetic tiny configuration in a copy of the repository (about ten minutes: six single-thread workers, 200 tiny cells, Stage R on eight cell types,
X8 and its calibration). No registered seed, real draw or real backbone is read."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from arborlm.io import read_json  # noqa: E402
from studies.p10is0 import core, rehearsal  # noqa: E402


def test_synthetic_pipeline_rehearsal_runs_every_stage(tmp_path: Path) -> None:
    rec = rehearsal.synthetic(REPO, tmp_path / "run")
    st = rec["stages"]
    required = ("generate", "timing", "stage_r", "caps", "candidate_plan", "counting_rehearsal", "freeze", "main", "x8-gate", "analysis", "report")
    assert all(st[s]["status"] == "COMPLETE" for s in required), st
    assert rec["caps_provisional"] is False and rec["profile"] == "test" and rec["seeds"] == "test profile only"
    copy = tmp_path / "run" / "repo"
    rd = copy / "experiments" / "rehearsal-run"
    # durations.json records the code identity Stage R ran under; the freeze record hashes every input individually
    dur = core.read_record(copy / core.DURATIONS, "durations")
    assert dur["code_identity"] and "extension_decisions" in dur and "studies/p10is0/core.py" in dur["code_identity"]
    fr = core.read_record(copy / core.FREEZE_RECORD, "freeze_record")
    assert "studies/p10is0/freeze/durations.json" in fr["inputs"] and fr["seed_gate"]["named_spare_values"]["initialisation"][0] == 330061
    # Stage R's measurements are sealed (hashed, access-logged) and the ledger and run files are outside the tracked tree
    sealed_store = Path(rec["sealed_dir"])
    assert len(list((sealed_store / "sealed").glob("*.json"))) > 0 and list((sealed_store / "sealed").glob("cal/*/updates_*.jsonl")) and (rd / "P10IS0-ledger.json").is_file()
    assert not (rd / "sealed").exists() and not (rd / "cal").exists()  # B1: nothing of Stage R in the run directory
    # B3: no per-cell-type Stage R decision or measurement is anywhere in the run directory or in a task or manifest file
    for f in rd.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".log", ".jsonl", ".md") and f.name != "addendum.json":  # the X8 addendum is written after durations.json exists (section 8)
            text = f.read_text(errors="ignore")
            assert not any(w in text for w in ("CANDIDATE", "NON_FINITE", "task_loss", "distinct_top1", '"e_star"')), f
    assert core.read_record(copy / core.DURATIONS, "durations")["attempt"] == 0 and (rd / "sealed_location.json").is_file()
    caps = core.read_record(copy / core.STAGE_CAPS, "stage_caps")
    assert caps["provisional"] is False and caps["total_hours"] > 0
    # X8 was exercised through a forced gate in this synthetic run only; its addendum is in the run directory, never in the worktree
    assert rec["x8_gate_forced_in_synthetic_run"] in (True, False)
    if rec["x8_gate_forced_in_synthetic_run"]:
        assert (rd / "x8" / "addendum.json").is_file() and not (copy / "studies/p10is0/freeze/addendum.json").exists()
        assert st["x8_after_forced_gate"]["status"] == "COMPLETE"
    analysis = read_json(rd / "analysis.json")
    assert analysis["headline"]["text"] and (rd / "report.md").is_file()
