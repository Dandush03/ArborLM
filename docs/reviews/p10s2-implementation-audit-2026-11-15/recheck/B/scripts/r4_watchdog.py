"""Re-check B, R4: the StageGuard watchdog in a process that ignores SIGINT (a background launch), against the old mechanism (_thread.interrupt_main), and its latency inside a long C call.

Each case runs in a fresh child: ``python r4_watchdog.py <pin> child <case> <sigint: ignore|default>``. The parent prints one JSON line per case.
Cases: guard_python_loop (cap 1.0 s around a 6 s pure-Python loop), old_interrupt_main (a thread calling _thread.interrupt_main after 1.0 s around the same loop),
guard_sleep (cap 0.5 s around time.sleep(2.0): the asynchronous exception is delivered only when the C call returns), guard_train_arm (cap 1.0 s around train_arm on a stand-in for 100000 updates on CPU).
"""

import json
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()


def child(case: str, sig: str) -> None:
    if sig == "ignore":
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    sys.path.insert(0, str(PIN))
    from studies.p10s2 import stages, train

    t0 = time.perf_counter()
    out: dict[str, object] = {"case": case, "sigint": sig}
    try:
        if case == "guard_python_loop":
            with stages.StageGuard("r4", cap_seconds=1.0, interval=0.05):
                while time.perf_counter() - t0 < 6.0:
                    sum(range(1000))
            out["result"] = "loop ran to its end (no stop)"
        elif case == "old_interrupt_main":
            import _thread

            threading.Timer(1.0, _thread.interrupt_main).start()
            while time.perf_counter() - t0 < 6.0:
                sum(range(1000))
            out["result"] = "loop ran to its end (no stop)"
        elif case == "guard_sleep":
            with stages.StageGuard("r4", cap_seconds=0.5, interval=0.05):
                time.sleep(2.0)
                while time.perf_counter() - t0 < 4.0:
                    sum(range(1000))
            out["result"] = "ran to its end (no stop)"
        elif case == "guard_train_arm":
            from studies.p10s2 import core, standins

            core.reset_seed_record()
            world, _ = standins.build_synthetic_world(1, updates=4)
            from studies.p10s2.memory import MemoryArm, SparseStore

            plan = world.plan(0)
            arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (recheck r4)")), world.layer, world.codes(0))
            t0 = time.perf_counter()
            with stages.StageGuard("r4", cap_seconds=1.0, interval=0.05):
                rec = train.train_arm(world.student, arm, world.train_examples(0, "A"), 100000, world.batch, world.store_lr, plan.gen(2, "batch order (recheck r4)"), world.marker_index)
            out["result"] = f"train_arm returned: status {rec.status}, updates {rec.updates}, error {rec.error[:120]!r}"
    except BaseException as e:  # noqa: BLE001
        out["result"] = f"{type(e).__name__}: {str(e)[:160]}"
    out["seconds"] = round(time.perf_counter() - t0, 3)
    print(json.dumps(out))


def main() -> None:
    rows = []
    for case in ("guard_python_loop", "old_interrupt_main", "guard_sleep", "guard_train_arm"):
        for sig in ("ignore", "default"):
            p = subprocess.run([sys.executable, __file__, str(PIN), "child", case, sig], capture_output=True, text=True, timeout=120, check=False)
            line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
            rows.append(json.loads(line[-1]) if line else {"case": case, "sigint": sig, "exit": p.returncode, "stderr": p.stderr[-400:]})
            print(json.dumps(rows[-1]))
    Path(sys.argv[2]).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "child":
        child(sys.argv[3], sys.argv[4])
    else:
        main()
