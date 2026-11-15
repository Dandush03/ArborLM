# ruff: noqa: E501
"""P10S1 end-to-end exercise (ADR-0021 section 22 M8). The fast structural test is always on. The full exercise (a source-only clone of this repository, the real fixed launch scripts, the
test-only switch that admits only the test seed sets, the whole registered sequence generate -> freeze commit -> Decision 2 -> gates -> ... -> report, and the refusal probes) takes several
minutes and is opt-in: set ``P10S1_E2E=1``. It creates no virtual environment and deletes its clone and outputs when it ends. Every number is tiny-size and synthetic. Self-check only: not
independent review, not Astra validation, not human approval."""

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import core, e2e  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_the_exercise_is_source_only_and_uses_the_current_environment() -> None:
    env = e2e.environment()
    assert env[core.TEST_SWITCH_ENV] == "1" and env["UV_NO_SYNC"] == "1" and env["UV_PROJECT_ENVIRONMENT"] == sys.prefix and "VIRTUAL_ENV" not in env
    assert e2e.stages("freeze")[:3] == [sys.executable, "-m", "studies.p10s1.stages"]
    text = (ROOT / "studies" / "p10s1" / "e2e.py").read_text()
    assert '"sync"' not in text and "venv" not in text.replace("virtual environment", "") and "reuse" not in text.lower()
    assert e2e.REGISTERED_SCRIPTS == ("gates", "train", "evaluate", "timing", "simulate", "analysis", "report")


def test_the_clone_is_source_files_only(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    e2e.make_clone(ROOT, clone)
    assert (clone / "studies" / "p10s1" / "e2e.py").is_file() and (clone / "configs" / "p10s1_capacity.toml").is_file()
    assert not (clone / ".venv").exists() and not (clone / "experiments").exists() and not (clone / "data").exists()
    shutil.rmtree(clone)


@pytest.mark.skipif(os.environ.get("P10S1_E2E") != "1" or shutil.which("sh") is None or shutil.which("git") is None, reason="the full exercise is opt-in: P10S1_E2E=1")
def test_the_registered_sequence_runs_end_to_end_on_test_seeds_through_the_launch_scripts(tmp_path: Path) -> None:
    work = tmp_path / "e2e"
    summary = e2e.run_e2e(work)
    failed = [s for s in summary["steps"] if not s["ok"]]
    assert summary["ok"] and not failed and "error" not in summary, (summary.get("error"), failed)
    names = [s["step"] for s in summary["steps"]]
    for expected in ("generate.sh (five test draws)", "freeze", "gates.sh", "train.sh", "evaluate.sh", "timing.sh", "simulate.sh", "analysis.sh", "report.sh"):
        assert expected in names
    probes = [s for s in summary["steps"] if s["step"].startswith("probe")]
    assert len(probes) == 3 and all(s["exit"] == 2 for s in probes)
    assert summary["analysis"]["status"] == "COMPLETE" and summary["report_bytes"] > 0
    assert summary["draws"] == list(core.TEST_DRAW_NAMES)  # only the five test sets: never a registered draw
    assert set(summary["plan"]["data_manifests"]) == set(core.TEST_DRAW_NAMES) and summary["plan"]["generation"]["provisional"] is False
    assert sorted(p.name for p in work.iterdir()) == ["E2E_SUMMARY.json", "logs"]  # the clone and the outputs are gone
    assert json.loads((work / "E2E_SUMMARY.json").read_text())["ok"] is True
