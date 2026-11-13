"""Watch a child process and finalize its run even if it cannot write a result."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import Any

import psutil

from .io import read_json, write_json
from .records import allocate_run, manifest, utc_now

POLL_SECONDS = 0.1
PROCESS_SECONDS = 300
SMOKE_SECONDS = 1500
RSS_BYTES = 2 * 1024**3


class Interrupted(Exception):
    pass


def _interrupt(signum: int, _frame: FrameType | None) -> None:
    raise Interrupted(signal.Signals(signum).name)


def _tree(process: Any) -> list[Any]:
    if process is None:
        return []
    try:
        return [process, *process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def _rss(process: Any) -> int:
    total = 0
    for child in _tree(process):
        try:
            total += int(child.memory_info().rss)
        except psutil.NoSuchProcess:
            continue
    return total


def _stop(process: subprocess.Popen[bytes], watched: Any, *, graceful: bool) -> None:
    descendants = _tree(watched)
    if graceful:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=0.5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
    # Nested smoke workers own their own process groups; snapshot their PIDs as well.
    for child in reversed(descendants):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def supervise(
    root: Path,
    operation: str,
    arguments: list[str],
    *,
    requested_argv: list[str],
    process_seconds: float = PROCESS_SECONDS,
    rss_bytes: int = RSS_BYTES,
    worker_argv: Callable[[Path], list[str]] | None = None,
) -> tuple[Path, bool]:
    run = allocate_run(root)
    cwd = Path.cwd()
    argv = (
        worker_argv(run)
        if worker_argv is not None
        else [sys.executable, "-m", "arborlm._worker", operation, str(run), *arguments]
    )
    running = manifest(
        run,
        operation,
        cwd=str(cwd),
        argv=argv,
        requested_argv=requested_argv,
        limits={
            "process_seconds": process_seconds,
            "rss_bytes": rss_bytes,
            "poll_seconds": POLL_SECONDS,
        },
    )
    write_json(run / "manifest.json", running)
    (run / "metrics.jsonl").touch()
    start = time.monotonic()
    peak = 0
    returncode = None
    failure: str | None = None
    interrupted = False
    prior_handlers = {
        sig: signal.signal(sig, _interrupt) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        with (run / "stdout.log").open("xb") as out, (run / "stderr.log").open("xb") as err:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdout=out,
                stderr=err,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            try:
                watched = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                watched = None
            try:
                while True:
                    if watched is not None:
                        peak = max(peak, _rss(watched))
                    returncode = process.poll()
                    elapsed = time.monotonic() - start
                    if peak > rss_bytes:
                        failure = "process-tree RSS limit exceeded"
                    elif elapsed > process_seconds:
                        failure = "process wall-time limit exceeded"
                    if failure or returncode is not None:
                        break
                    time.sleep(min(POLL_SECONDS, max(0.0, process_seconds - elapsed)))
                if failure and returncode is None:
                    _stop(process, watched, graceful=operation == "smoke")
            except Interrupted as exc:
                interrupted = True
                failure = f"watchdog interrupted: {exc}"
                _stop(process, watched, graceful=True)
            except BaseException:
                _stop(process, watched, graceful=True)
                raise
            returncode = process.returncode
    except Interrupted as exc:
        interrupted = True
        failure = f"watchdog interrupted: {exc}"
    except Exception as exc:
        failure = f"watchdog error: {type(exc).__name__}: {exc}"
    finally:
        for sig, handler in prior_handlers.items():
            signal.signal(sig, handler)

    result_path = run / "result.json"
    result: dict[str, Any] = {}
    try:
        if result_path.exists():
            supplied = read_json(result_path)
            if not isinstance(supplied, dict):
                raise ValueError("result is not an object")
            result = supplied
    except (OSError, ValueError) as exc:
        if failure is None:
            failure = f"invalid child result: {exc}"
    if failure is None and returncode != 0:
        failure = f"child exited with status {returncode}; see stderr.log"
    if failure is None and result.get("outcome") not in {"completed", "registered_stop"}:
        failure = "child exited without a valid result"
    status = (
        "interrupted"
        if interrupted or (failure is None and result.get("outcome") == "registered_stop")
        else "failed"
        if failure
        else "completed"
    )
    terminal = {
        "status": status,
        "reason": failure or ("registered step-16 stop" if status == "interrupted" else None),
        "returncode": returncode,
        "finished_utc": utc_now(),
        "process_wall_seconds": time.monotonic() - start,
        "peak_process_tree_rss_bytes": peak,
        "rss_method": "sampled sum of psutil RSS for child and descendants, in bytes",
        "rss_poll_seconds": POLL_SECONDS,
        "rss_platform": sys.platform,
    }
    write_json(run / "terminal.json", terminal)
    current = read_json(run / "manifest.json")
    current.update(terminal)
    write_json(run / "manifest.json", current)
    return run, failure is None
