import sys
from pathlib import Path

from arborlm.io import read_json
from arborlm.watchdog import supervise


def test_failed_watchdog_record_is_retained_on_retry(tmp_path: Path) -> None:
    first, ok = supervise(
        tmp_path,
        "fixture",
        [],
        requested_argv=["unit-fixture"],
        worker_argv=lambda run: [sys.executable, "-c", "import sys; print('failed'); sys.exit(3)"],
    )
    assert not ok
    original = (first / "terminal.json").read_bytes()
    assert read_json(first / "terminal.json")["status"] == "failed"
    assert read_json(first / "terminal.json")["returncode"] == 3
    assert (first / "stdout.log").read_text().strip() == "failed"
    second, ok = supervise(
        tmp_path,
        "fixture",
        [],
        requested_argv=["unit-fixture"],
        worker_argv=lambda run: [
            sys.executable,
            "-c",
            "from pathlib import Path; Path(__import__('sys').argv[1]).write_text('invalid')",
            str(run / "result.json"),
        ],
    )
    assert not ok
    assert first != second and (first / "terminal.json").read_bytes() == original
    assert "invalid child result" in read_json(second / "terminal.json")["reason"]


def test_watchdog_kills_timed_out_child_and_saves_logs(tmp_path: Path) -> None:
    run, ok = supervise(
        tmp_path,
        "fixture",
        [],
        requested_argv=["unit-fixture"],
        process_seconds=0.4,
        worker_argv=lambda run: [
            sys.executable,
            "-u",
            "-c",
            "import time; print('started'); time.sleep(60)",
        ],
    )
    assert not ok
    terminal = read_json(run / "terminal.json")
    assert terminal["status"] == "failed"
    assert terminal["reason"] == "process wall-time limit exceeded"
    assert terminal["returncode"] < 0
    assert terminal["process_wall_seconds"] < 5
    assert (run / "stdout.log").read_text().strip() == "started"


def test_watchdog_kills_over_budget_process_tree(tmp_path: Path) -> None:
    run, ok = supervise(
        tmp_path,
        "fixture",
        [],
        requested_argv=["unit-fixture"],
        rss_bytes=1,
        worker_argv=lambda run: [sys.executable, "-c", "import time; time.sleep(60)"],
    )
    assert not ok
    terminal = read_json(run / "terminal.json")
    assert terminal["status"] == "failed"
    assert terminal["reason"] == "process-tree RSS limit exceeded"
    assert terminal["peak_process_tree_rss_bytes"] > 1
