# ruff: noqa: E501
"""P10S2 confirmation of the re-check fixes (F4, N3, F5 (freeze side), F9, F10, F11, F12 and the ledger of record), on fakes and test seeds. Self-check only: not independent review, not Astra
validation, not human approval."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import core, fetch_guard, freeze, output, stages  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- F4: closing an orphan --------------------------------------------------------------------------------------------------------------------------------------
def test_f4_an_orphan_is_closed_by_a_recorded_entry_charged_at_min_of_elapsed_and_cap(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.jsonl")
    led.record("train", 0.0, status="started", run_id="a", t_start=time.time() - 7200, cap_seconds=600.0)  # killed two hours ago, cap ten minutes
    led.record("datagen", 0.0, status="started", run_id="b", t_start=time.time() - 60)  # killed a minute ago, no cap recorded
    assert len(led.unfinished()) == 2
    closed = led.close_orphans("the lead")
    assert {e["run_id"] for e in closed} == {"a", "b"} and led.unfinished() == []
    by = {e["run_id"]: e for e in led.entries() if e["status"] == "orphan-closed"}
    assert by["a"]["charged_hours"] == pytest.approx(600.0 / 3600.0) and by["b"]["charged_hours"] == pytest.approx(60.0 / 3600.0, rel=0.2)
    assert "closes an orphan" in by["a"]["note"] and "written by the lead" in by["a"]["note"] and by["a"]["status"] == "orphan-closed"
    assert sum(1 for e in led.entries() if e["status"] == "started") == 2  # the markers stay: nothing is rewritten
    before = led.total_hours()
    assert led.close_orphans("again") == [] and led.total_hours() == before  # idempotent


def test_f4_the_close_orphans_command_cannot_touch_the_real_ledger_under_pytest() -> None:
    real = ROOT / "experiments" / "P10S2" / "ledger.jsonl"
    before = real.read_bytes() if real.exists() else None
    with pytest.raises(core.TestGuardRefused):
        stages.main(["close-orphans", "--written-by", "a test"])
    assert (real.read_bytes() if real.exists() else None) == before


def test_f4_the_freeze_refuses_while_a_marker_is_open_and_accepts_after_closing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_p10s2_fixB_freeze import Setup

    s = Setup(tmp_path, monkeypatch)
    s.led.record("train", 0.0, status="started", run_id="o", t_start=time.time() - 5, cap_seconds=60.0)
    with pytest.raises(freeze.FreezeRefused, match="start marker with no end"):
        s.freeze()
    s.led.close_orphans("the lead")
    reh = json.loads((s.pre / "rehearsal.json").read_text())
    reh["charged_hours_at_end_of_rehearsal"] = s.led.total_hours()  # the closing charged a few seconds: P of the rung rule is read from the rehearsal record, which the lead re-makes
    (s.pre / "rehearsal.json").write_text(json.dumps(reh))
    s.freeze()
    assert (s.repo / core.PLAN_FILE).exists()


# --- N3: the commit of the pre-freeze records ---------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a], check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def make_repo(tmp: Path) -> Path:
    r = tmp / "repo"
    (r / "studies/p10s2").mkdir(parents=True)
    (r / "src/arborlm").mkdir(parents=True)
    (r / "configs").mkdir()
    for f in ("studies/p10s2/budget.py", "studies/p10s2/gates.py", "studies/p10s2/data.py", "studies/p10s2/train.py", "src/arborlm/io.py", "configs/p10s2_transfer.toml", "studies/p10s2/README.txt"):
        (r / f).write_text("x\n")
    subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True)  # noqa: S603, S607
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "a")
    return r


def test_n3_each_records_commit_must_be_an_ancestor_and_differing_paths_the_record_executes_refuse(tmp_path: Path) -> None:
    r = make_repo(tmp_path)
    a = git(r, "rev-parse", "HEAD")
    (r / "studies/p10s2/budget.py").write_text("y\n")  # the freeze's own arithmetic: no pre-freeze record executes it except the rehearsal
    (r / "studies/p10s2/README.txt").write_text("y\n")
    git(r, "commit", "-qam", "b")
    d = freeze.record_commit_diffs(r, {"data": a, "calibration": a, "prefreeze_gates": a})
    assert d["data"]["commit"] == a and d["data"]["differing_paths"] == ["studies/p10s2/README.txt", "studies/p10s2/budget.py"]  # listed for the lead's approval
    with pytest.raises(freeze.FreezeRefused, match="executes it"):
        freeze.record_commit_diffs(r, {"rehearsal": a})  # the rehearsal projects with budget.py
    (r / "studies/p10s2/train.py").write_text("y\n")
    git(r, "commit", "-qam", "c")
    with pytest.raises(freeze.FreezeRefused, match="executes it"):
        freeze.record_commit_diffs(r, {"calibration": a})  # calibration trains
    assert freeze.record_commit_diffs(r, {"data": a})["data"]["differing_paths"][-1] == "studies/p10s2/train.py"  # data generation does not execute train.py
    (r / "configs/p10s2_transfer.toml").write_text("y\n")
    git(r, "commit", "-qam", "d")
    for kind in freeze.RECORD_EXECUTES:
        with pytest.raises(freeze.FreezeRefused, match="executes it"):
            freeze.record_commit_diffs(r, {kind: a})  # the configuration and src/arborlm are executed by every record
    git(r, "checkout", "-q", "-b", "side", a)
    (r / "studies/p10s2/README.txt").write_text("z\n")
    git(r, "commit", "-qam", "side")
    side = git(r, "rev-parse", "HEAD")
    git(r, "checkout", "-q", "main")
    with pytest.raises(freeze.FreezeRefused, match="not an ancestor"):
        freeze.record_commit_diffs(r, {"data": side})
    with pytest.raises(freeze.FreezeRefused, match="not a commit"):
        freeze.record_commit_diffs(r, {"data": "c0ffee"})


def test_n3_the_named_constants_cover_every_record_kind_and_the_plan_lists_the_differences(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert set(freeze.RECORD_EXECUTES) == {"data", "calibration", "prefreeze_gates", "rehearsal"} and freeze.CONFIG_PATH == "configs/p10s2_transfer.toml"
    assert freeze.executed_by("data", "studies/p10s2/datagen.py") and not freeze.executed_by("data", "studies/p10s2/budget.py") and freeze.executed_by("rehearsal", "studies/p10s2/budget.py")
    assert freeze.executed_by("calibration", "src/arborlm/io.py") and not freeze.executed_by("calibration", "studies/p10s2/launch/datagen.sh") and not freeze.executed_by("calibration", "studies/p10s2/freeze/README.md")
    from test_p10s2_fixB_freeze import Setup

    s = Setup(tmp_path, monkeypatch)
    (s.repo / "studies/p10s2/launch").mkdir(exist_ok=True)
    (s.repo / "studies/p10s2/launch/x.sh").write_text("echo\n")
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "a launch script, executed by no record")
    s.freeze()
    plan = freeze.load_plan(s.repo)
    assert plan["record_commit_diffs"]["data"]["commit"] == s.code and plan["record_commit_diffs"]["rehearsal"]["differing_paths"] == ["studies/p10s2/launch/x.sh"]


# --- F9: the pre-freeze stages run on the completed data record of their bundle ----------------------------------------------------------------------------------------------
def test_f9_a_prefreeze_stage_needs_the_completed_data_record_naming_its_bundle(tmp_path: Path) -> None:
    run, bundle = tmp_path / "run", tmp_path / "run" / "data" / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "manifest.json").write_text("{}")
    with pytest.raises(stages.StageRefused, match="does not exist"):
        stages._require_data_record(run, bundle, "calibration")
    rec = run / "data" / "prefreeze_record.json"
    from arborlm.io import file_sha256

    rec.write_text(json.dumps({"stopped": "RegisteredTestStop: x", "bundle_manifest_sha256": file_sha256(bundle / "manifest.json")}))
    with pytest.raises(stages.StageRefused, match="stop record"):
        stages._require_data_record(run, bundle, "calibration")
    rec.write_text(json.dumps({"bundle_manifest_sha256": "other"}))
    with pytest.raises(stages.StageRefused, match="another bundle"):
        stages._require_data_record(run, bundle, "the rehearsal")  # a stand-in or wrong bundle is caught before a write-once record is spent
    rec.write_text(json.dumps({"bundle_manifest_sha256": file_sha256(bundle / "manifest.json")}))
    stages._require_data_record(run, bundle, "calibration")


# --- F10: a refusal in the registered sequence leaves a stop record and the analysis writes the section 11 outcome ----------------------------------------------------------------------
def test_f10_a_failed_gate_or_no_room_leaves_a_stop_record_and_the_analysis_stage_may_run(tmp_path: Path) -> None:
    from test_p10s2_fixB_stages import GATES_OK, put_gates, write_stage

    run = tmp_path / "run"
    write_stage(run, "gates")
    put_gates(run, {**GATES_OK, "G5": {"ok": False}, "ok": False})
    with pytest.raises(stages.GatesFailed):
        stages.require_order(run, "train")
    with pytest.raises(stages.StageRefused):
        stages.require_order(run, "analysis")  # no stop record yet: the order stands
    stages._refusal_stop(run, "train", stages.GatesFailed("refused: the second gates stage did not pass (G5)"), "ENGINEERING-FAILURE")
    stages.require_order(run, "analysis")
    out = stages.stage_analysis(run, {"replicates": 1, "updates": 4}, {"teacher_only": True}, seed_mode="test")
    assert out["label"] == "ENGINEERING-FAILURE" and any("train refused" in e for e in out["engineering"])
    run2 = tmp_path / "run2"
    write_stage(run2, "gates")
    stages._refusal_stop(run2, "train", RuntimeError("no room under the cap"), "INCOMPLETE")
    stages.require_order(run2, "analysis")
    stages._refusal_stop(run2, "evaluate", RuntimeError("second"), "INCOMPLETE")  # write-once: the first refusal stays
    assert json.loads((run2 / "stop_record.json").read_text())["stage"] == "train"
    out2 = stages.stage_analysis(run2, {"replicates": 1, "updates": 4}, {"teacher_only": True}, seed_mode="test")
    assert out2["label"] == "INCOMPLETE" and any("train refused" in e for e in out2["incomplete"])


# --- F11, F12 ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_f11_a_typed_override_is_refused_unless_pytest_is_really_running(monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    args = argparse.Namespace(updates=5, full_updates=None, device=None)
    stages._refuse_typed(args)  # under pytest
    monkeypatch.delitem(sys.modules, "pytest")  # the environment variable alone (set by hand) is not enough
    try:
        with pytest.raises(stages.StageRefused, match="not typed outside tests"):
            stages._refuse_typed(args)
    finally:
        monkeypatch.undo()


def test_f12_no_line_may_speak_of_autonomy_outside_the_three_fixed_phrases() -> None:
    line = core.ORACLE_LINE
    output.check_text(f"{line}\nlabel: x")  # the oracle line itself says "not autonomous learned memory"
    output.check_text(f"{line}\n- {core.LEAD_RULE}\n- Autonomous learned memory: addresses and routes are supplied by rule.")
    for bad in ("autonomous learned-memory success on French", "The store is AUTONOMOUS here", "autonomy was reached"):
        with pytest.raises(output.OracleLineMissing, match="autonomy"):
            output.check_text(f"{line}\n{bad}")


# --- the ledger of record -------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_download_ledger_of_record_is_one_file_that_holds_the_first_downloads_rows() -> None:
    assert str(fetch_guard.DOWNLOAD_LEDGER) == "docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md"
    path = ROOT / fetch_guard.DOWNLOAD_LEDGER
    _head, rows, _tail = fetch_guard._read_ledger(path)
    first = [r for r in rows if r[1] == "P10-S2" and r[8].strip().startswith("completed") and "datagen" not in r[2]]
    assert len(first) >= 29 and fetch_guard.ledger_total_bytes(path) >= 936_320_520  # the model files and the seven Tatoeba files, 936,320,520 bytes
    assert [p.name for p in ROOT.rglob("DOWNLOAD_LEDGER*.md") if ".venv" not in p.relative_to(ROOT).parts] == ["DOWNLOAD_LEDGER.md"]  # no other copy
    src = (ROOT / "studies/p10s2/fetch.py").read_text() + (ROOT / "studies/p10s2/install_datagen.py").read_text()
    assert src.count("fetch_guard.DOWNLOAD_LEDGER") + src.count("g.DOWNLOAD_LEDGER") >= 2  # fetch and the install both name that one path
