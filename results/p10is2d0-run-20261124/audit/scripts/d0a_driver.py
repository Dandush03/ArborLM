# ruff: noqa
"""Audit D0 driver (stdlib only): stage 1 = the six gate jobs; stage 2 (only if all six gates pass) = the six cell jobs. At most 3 processes of 6
threads, CPU only. Worker-hour cap: the sum over computing processes of their wall time; when finished + running elapsed reaches CAP_HOURS (default 8)
every running job is killed (Popen child, pid known) and nothing more is launched. Per-job timeout 3 h. Resumable (tasks skip done files).

Run: nohup python3 -I d0a_driver.py > ../audit_d0_out/driver_<stamp>.log 2>&1 &
Finished when the log ends with 'DRIVER END'."""
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit_d0_out")
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124"
MAXP = 3
JOB_TIMEOUT = 3 * 3600
CAP = float(os.environ.get("D0A_CAP_HOURS", "8")) * 3600
CELLS = [(r, o) for r in range(3) for o in ("AB", "BA")]
LEDGER = OUT / "worker_seconds_ledger.jsonl"


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def prior_seconds():
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(x)["wall"] for x in LEDGER.read_text().splitlines() if x.strip())


def gate_state():
    res = {}
    for r, o in CELLS:
        p = OUT / "gate" / f"gate_r{r}_{o}.json"
        res[(r, o)] = json.loads(p.read_text())["gate_pass"] if Path(str(p) + ".done").exists() else None
    return res


def run_stage(jobs, env):
    queue = list(jobs)
    running = {}
    used0 = prior_seconds()
    while queue or running:
        now = time.time()
        used = used0 + sum(now - t0 for (_p, t0, _f) in running.values())
        for j, (p, t0, fh) in list(running.items()):
            rc = p.poll()
            if rc is None and (now - t0 > JOB_TIMEOUT or used >= CAP):
                log(f"KILL {j} pid={p.pid} ({'cap' if used >= CAP else 'timeout'}) used={used:.0f}s")
                p.kill()
                rc = p.wait()
            if rc is not None:
                fh.close()
                wall = time.time() - t0
                with open(LEDGER, "a") as f:
                    f.write(json.dumps({"job": j, "pid": p.pid, "rc": rc, "wall": wall, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
                used0 += wall
                log(f"END {j} rc={rc} wall={wall:.1f}s")
                del running[j]
        if used0 >= CAP:
            log(f"CAP reached: {used0:.0f}s; not started: {queue}")
            return False
        while queue and len(running) < MAXP:
            j = queue.pop(0)
            fh = open(OUT / "logs" / (j.replace(" ", "_") + f".{int(time.time())}.log"), "w")
            p = subprocess.Popen(["uv", "run", "--locked", "--offline", "python", str(HERE / "d0a_task.py"), *j.split()], cwd=WT, env=env, stdout=fh, stderr=subprocess.STDOUT)
            running[j] = (p, time.time(), fh)
            log(f"START {j} pid={p.pid}")
        time.sleep(10)
    return True


def main():
    (OUT / "logs").mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "6", "MKL_NUM_THREADS": "6", "VECLIB_MAXIMUM_THREADS": "6", "UV_OFFLINE": "1",
                "HF_HUB_OFFLINE": "1", "CUDA_VISIBLE_DEVICES": "", "PYTORCH_ENABLE_MPS_FALLBACK": "0"})
    log(f"DRIVER START pid={os.getpid()} prior_worker_seconds={prior_seconds():.0f} cap={CAP:.0f}")
    gs = gate_state()
    todo = [f"gate {r} {o}" for (r, o), v in gs.items() if v is None]
    if todo and not run_stage(todo, env):
        log("DRIVER END (cap in gate stage)")
        return
    gs = gate_state()
    log(f"gate results: { {f'r{r}{o}': v for (r, o), v in gs.items()} }")
    if not all(v is True for v in gs.values()):
        log("GATE FAILED or missing: ENGINEERING STOP; no counterfactual pass is launched")
        log("DRIVER END")
        return
    ok = run_stage([f"cell {r} {o}" for r, o in CELLS], env)
    log(f"cell stage finished={ok} worker_seconds_total={prior_seconds():.0f}")
    log("DRIVER END")


if __name__ == "__main__":
    main()
