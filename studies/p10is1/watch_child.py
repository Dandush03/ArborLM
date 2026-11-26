# ruff: noqa: E501
"""P10IS1 in-measurement watch as a CHILD process (ruling N3). MC-T counts the timing process's CPU seconds, and reading the conditions (``ps``, ``pmset``, ``ioreg``) costs about 25 ms of CPU per reading; run as a thread in
the timing process that would fall on some items and not others. The stage starts this process BEFORE the measurement, it reads the conditions of A3.3 (``quiet.watch_conditions``: the same conditions as a quiet reading,
and the set of Claude processes compared with the reading the measurement started from) at its first tick and every interval, appends each tick to its record file as it is taken, and on SIGTERM takes a last tick and
writes a summary line with its own CPU seconds. It is a descendant of the stage (part of its own process family for the study-process check). It exits by itself if its parent is gone. Reads no seed and no data."""

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from . import core, quiet


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studies.p10is1.watch_child")
    ap.add_argument("--args", required=True, help="a JSON file: first (the quiet reading), cfg_path, interval, out, parent_pid")
    a = json.loads(Path(ap.parse_args(argv).args).read_text(encoding="utf-8"))
    cfg = core.load_config(Path(a["cfg_path"])) if a.get("cfg_path") else core.load_config()
    out, interval, parent = Path(a["out"]), float(a["interval"]), int(a["parent_pid"])
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    ticks = 0

    def tick() -> None:
        nonlocal ticks
        try:
            failed = quiet.watch_conditions(a["first"], cfg=cfg)
        except Exception as exc:  # noqa: BLE001 - an unreadable condition fails closed
            failed = [f"CONDITIONS UNREADABLE DURING THE MEASUREMENT ({str(exc)[:80]})"]
        ticks += 1
        quiet.append_line(out, {"t": time.time(), "tick": ticks, "failed": failed})

    tick()  # the first tick is also the "ready" signal the stage waits for
    while not stop.wait(interval):
        if os.getppid() != parent:
            break  # the stage is gone
        tick()
    tick()
    t = os.times()
    quiet.append_line(out, {"summary": True, "ticks": ticks, "cpu_seconds": float(t.user + t.system)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
