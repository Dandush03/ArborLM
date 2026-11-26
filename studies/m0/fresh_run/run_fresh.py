# ruff: noqa: E501
"""The runner of the M0 fresh run (ADR-0033 addendum 1, section 4A, stage 1S point 11). Standard library only.

    uv run --locked python run_fresh.py --plan run_plan.json --expect-plan-sha256 HEX --seed-set {dry,1,2,3} [--units R1a,R2b,...] [--jobs N] [--check-only]
(run from the worktree root; the plan's own commands are run with their own argv, this script only needs the standard library)

For each unit, in the plan's fixed order: it creates the unit's output directory (it refuses to start if that directory already exists and is
non-empty; nothing is ever overwritten), executes each command exactly as planned (argv, cwd, the plan's environment added to a minimal inherited
environment of PATH and HOME), redirects standard output and standard error to the planned files, records the exit status and the wall time, and, as
the unit ends, records the SHA-256 and the size of every file under its output directory into <root>/hashes_seed<i>.json (<root>/hashes_dry.json for
the dry set). It opens no output for any purpose but hashing it, and prints no content of any output (only unit names and exit statuses).

A command that exits non-zero ends the unit's chain; the unit's whole chain (every command from the first) is then run once again, unchanged except
for the output-directory prefix, into the sibling directory <unit>/seed<i>_retry1 (<unit>_retry1 for the dry set); both attempts are recorded. If that
also fails, no further unit is started, running units are left to end, and the runner exits 1, printing only the unit name and the exit statuses.
A runner error (an exception of this script, not an exit status of a command) is recorded for that unit (exception type and message), stops everything
the same way, and no later unit starts. It refuses to start (exit 2) if the plan's SHA-256 is not the expected one, or if any hash record under the run
or the dry output root, for this seed set or any other, holds a unit whose final status is not ok.
Exit status: 0 all units ended with exit 0; 1 a unit failed twice or the runner failed on a unit; 2 a refusal (a usage error, a plan hash mismatch, a
failed unit in an earlier record, an output directory that is not empty, a unit already recorded) before any command was started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

LOCK = threading.Lock()
STOP = threading.Event()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hashes(root: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = {"sha256": sha256_file(p), "size": os.path.getsize(p)}
    return out


def rewrite(obj: Any, old: str, new: str) -> Any:
    if isinstance(obj, str):
        return obj.replace(old, new)
    if isinstance(obj, list):
        return [rewrite(x, old, new) for x in obj]
    if isinstance(obj, dict):
        return {k: rewrite(v, old, new) for k, v in obj.items()}
    return obj


def utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_nonempty_dir(p: str) -> bool:
    return os.path.isdir(p) and bool(os.listdir(p))


def run_chain(unit: str, commands: list[dict[str, Any]], outdir: str) -> dict[str, Any]:
    """Run the commands of one attempt, in order; stop at the first non-zero exit. Returns the attempt record (no output content)."""
    os.makedirs(outdir, exist_ok=True)
    rec: dict[str, Any] = {"dir": outdir, "commands": [], "start_utc": utc()}
    ok = True
    for c in commands:
        env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], **c["env"]}
        for p in (c["stdout_file"], c["stderr_file"]):
            os.makedirs(os.path.dirname(p), exist_ok=True)
        t0 = time.monotonic()
        with open(c["stdout_file"], "xb") as so, open(c["stderr_file"], "xb") as se:
            try:
                status = subprocess.run(c["argv"], cwd=c["cwd"], env=env, stdout=so, stderr=se, check=False).returncode
            except OSError as e:  # the command could not even start
                status = 127
                se.write(f"runner: {type(e).__name__}\n".encode())
        rec["commands"].append({"name": c["name"], "exit_status": status, "wall_seconds": round(time.monotonic() - t0, 3)})
        if status != 0:
            ok = False
            break
    rec["ok"] = ok
    rec["end_utc"] = utc()
    rec["files"] = tree_hashes(outdir)  # hashed, never read otherwise
    return rec


def run_unit(plan: dict[str, Any], unit: str, seed_set: str, record: dict[str, Any], record_path: str, plan_sha: str) -> bool:
    run = plan["units"][unit]["runs"][seed_set]
    outdir = run["output_dir"]
    attempts = []
    a1 = run_chain(unit, run["commands"], outdir)
    attempts.append(a1)
    ok = a1["ok"]
    if not ok:
        retry = outdir + "_retry1"
        cmds2 = rewrite(run["commands"], outdir, retry)
        assert rewrite(cmds2, retry, outdir) == run["commands"], "retry command differs by more than the output-directory prefix"
        a2 = run_chain(unit, cmds2, retry)
        attempts.append(a2)
        ok = a2["ok"]
    with LOCK:
        record["units"][unit] = {"attempts": attempts, "ok": ok}
        write_record(record_path, record, plan_sha)
    statuses = [[c["exit_status"] for c in a["commands"]] for a in attempts]
    print(f"unit {unit} seed-set {seed_set}: exit statuses per attempt {statuses}; ok={ok}", flush=True)
    if not ok:
        STOP.set()
    return ok


def write_record(path: str, record: dict[str, Any], plan_sha: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"plan_sha256": plan_sha, **record}, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--expect-plan-sha256", required=True, help="the SHA-256 recorded for the run plan; checked before anything runs")
    ap.add_argument("--seed-set", required=True, choices=["dry", "1", "2", "3"])
    ap.add_argument("--units", default=None, help="comma-separated subset; they still run in the plan's fixed order")
    ap.add_argument("--jobs", type=int, default=1, help="units run concurrently (independent units only); default 1")
    ap.add_argument("--check-only", action="store_true", help="make the refusal checks and print the units, execute nothing")
    a = ap.parse_args(argv)
    STOP.clear()
    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    plan_sha = sha256_file(a.plan)
    if plan_sha != a.expect_plan_sha256:
        print("refusing: the plan does not have the expected SHA-256", file=sys.stderr)
        return 2
    order = plan["unit_order"]
    want = order if a.units is None else a.units.split(",")
    for u in want:
        if u not in order:
            print(f"refusing: unknown unit {u}", file=sys.stderr)
            return 2
    excluded = {e["unit"] for e in plan.get("dry_run_exclusions", []) if not e.get("lineages")}
    units = [u for u in order if u in want and u not in excluded]
    ss = a.seed_set
    root = plan["output_roots"]["dry" if ss == "dry" else "run"]
    record_path = os.path.join(root, "hashes_dry.json" if ss == "dry" else f"hashes_seed{ss}.json")
    for rt in (plan["output_roots"]["run"], plan["output_roots"]["dry"]):  # a unit that did not end ok in ANY record stops the run for good
        if not os.path.isdir(rt):
            continue
        for fn in sorted(os.listdir(rt)):
            if fn.startswith("hashes_") and fn.endswith(".json"):
                with open(os.path.join(rt, fn), encoding="utf-8") as f:
                    old = json.load(f)
                for ou, orec in sorted(old.get("units", {}).items()):
                    if not orec.get("ok", False):
                        print(f"refusing: {fn} holds unit {ou} whose final status is not ok; the run stopped and goes to the human lead", file=sys.stderr)
                        return 2
    record: dict[str, Any] = {"seed_set": ss, "units": {}}
    if os.path.exists(record_path):
        with open(record_path, encoding="utf-8") as f:
            record = json.load(f)
        record.pop("plan_sha256", None)
    for u in units:
        d = plan["units"][u]["runs"][ss]["output_dir"]
        if is_nonempty_dir(d) or is_nonempty_dir(d + "_retry1"):
            print(f"refusing: the output directory of unit {u} exists and is not empty", file=sys.stderr)
            return 2
        if u in record["units"]:
            print(f"refusing: unit {u} is already recorded in {record_path}", file=sys.stderr)
            return 2
    if a.check_only:
        for u in units:
            print(f"unit {u}: {len(plan['units'][u]['runs'][ss]['commands'])} command(s) -> {plan['units'][u]['runs'][ss]['output_dir']}")
        return 0
    os.makedirs(root, exist_ok=True)
    ok_all = True

    def job(u: str) -> bool:
        if STOP.is_set():
            print(f"unit {u}: not started (an earlier unit failed twice)", flush=True)
            return False
        try:
            return run_unit(plan, u, ss, record, record_path, plan_sha)
        except BaseException as e:  # an error of the runner itself: recorded for the unit, everything stops
            STOP.set()
            d = plan["units"][u]["runs"][ss]["output_dir"]
            try:
                files = tree_hashes(d) if os.path.isdir(d) else {}
            except OSError:
                files = {}
            with LOCK:
                record["units"][u] = {"ok": False, "runner_exception": {"type": type(e).__name__, "message": str(e)[:300]}, "attempts": [], "files_present": files}
                try:
                    write_record(record_path, record, plan_sha)
                except OSError:
                    pass
            print(f"unit {u} seed-set {ss}: runner error {type(e).__name__}", flush=True)
            return False

    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        results = list(ex.map(job, units))
    ok_all = all(results)
    if not ok_all:
        failed = [u for u, r in zip(units, results, strict=True) if not r and u in record["units"]]
        for u in failed:
            if "runner_exception" in record["units"][u]:
                ex = record["units"][u]["runner_exception"]
                print(f"STOP unit={u} runner error {ex['type']}: {ex['message']}", file=sys.stderr)
                continue
            st = [[c["exit_status"] for c in at["commands"]] for at in record["units"][u]["attempts"]]
            print(f"STOP unit={u} exit statuses per attempt {st}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
