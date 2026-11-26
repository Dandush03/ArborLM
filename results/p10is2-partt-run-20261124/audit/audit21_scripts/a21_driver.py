# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21 driver: every recomputation task, at most 3 processes of 6 threads, CPU only. Resumable: a task whose results/<task>.json.done exists is
skipped. Each task has a 3-hour timeout; the driver launches nothing after its deadline (default 12 h from start). Standard library only.

Run (from anywhere):  nohup python3 -I a21_driver.py > ../audit21_out/driver.log 2>&1 &
Finished when ../audit21_out/driver.log ends with a line 'DRIVER END' (and 'all tasks done: True' when complete)."""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit21_out")
RES = OUT / "results"
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f"
MAXP = 3
TASK_TIMEOUT = 3 * 3600
DEADLINE = time.time() + float(os.environ.get("A21_DEADLINE_HOURS", "12")) * 3600


def tasks():
    out = []
    for r in range(3):
        for o in ("AB", "BA"):
            for a in ("M-append", "M-ii", "D-seq", "D-append"):
                out.append(f"comb|{r}|{a}|{o}")
        for a in ("M-joint", "D-joint", "M-sep", "D-sep"):
            out.append(f"comb|{r}|{a}|-")
    for r in range(3):
        for o in ("AB", "BA"):
            for a in ("M-append", "M1", "M-ii", "M-seq", "D-seq", "D1", "D-append", "M-append@append"):
                out.append(f"cell|{r}|{o}|{a}")
    for r in range(3):
        out += [f"base|{r}", f"joint|{r}|M-joint", f"sep|{r}", f"joint|{r}|D-joint", f"etable|{r}"]
    out += ["combref", "ref"]
    return out


def done(t):
    return (RES / (t.replace("|", "__").replace("@", "_at_") + ".json.done")).exists()


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def main():
    RES.mkdir(parents=True, exist_ok=True)
    (OUT / "task_logs").mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "6", "MKL_NUM_THREADS": "6", "VECLIB_MAXIMUM_THREADS": "6", "UV_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
    queue = [t for t in tasks() if not done(t)]
    log(f"DRIVER START pid={os.getpid()} tasks={len(tasks())} to_run={len(queue)}")
    running = {}
    while queue or running:
        for t, (p, t0, fh) in list(running.items()):
            rc = p.poll()
            if rc is None and time.time() - t0 > TASK_TIMEOUT:
                p.kill()
                rc = p.wait()
                log(f"TIMEOUT {t}")
            if rc is not None:
                fh.close()
                log(f"END {t} rc={rc} wall={time.time() - t0:.1f}s done={done(t)}")
                del running[t]
        while queue and len(running) < MAXP and time.time() < DEADLINE:
            t = queue.pop(0)
            fh = open(OUT / "task_logs" / (t.replace("|", "__").replace("@", "_at_") + f".{int(time.time())}.log"), "w")
            p = subprocess.Popen(["uv", "run", "--locked", "--offline", "python", str(HERE / "a21_task.py"), t], cwd=WT, env=env, stdout=fh, stderr=subprocess.STDOUT)
            running[t] = (p, time.time(), fh)
            log(f"START {t} pid={p.pid}")
        if time.time() >= DEADLINE and queue and not running:
            log(f"DEADLINE reached; not started: {len(queue)}")
            break
        time.sleep(5)
    log(f"all tasks done: {all(done(t) for t in tasks())}")
    log("DRIVER END")


if __name__ == "__main__":
    main()
