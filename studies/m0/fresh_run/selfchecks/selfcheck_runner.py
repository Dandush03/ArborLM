"""Implementer's self-check of run_fresh.py on a TOY plan (made-up commands that run `python -c`; no unit of the fresh run is executed).
Writes only under m0_fr_pool_impl_20261126/runs_runner/<timestamp>/."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import time

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies", "m0", "fresh_run")
SCR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("run_fresh", os.path.join(HERE, "run_fresh.py"))
rf = importlib.util.module_from_spec(spec)
sys.modules["run_fresh"] = rf
spec.loader.exec_module(rf)
ROOT = os.path.join(SCR, "runs_runner", time.strftime("%Y%m%d-%H%M%S"))
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS", name)
    else:
        FAIL += 1
        print("FAIL", name, detail)


def cmd(name, d, code, root, extra_env=None):
    marker = os.path.join(root, "marker_" + name)
    py = (
        "import os,sys;"
        f"open({d!r}+'/out.txt','w').write('hello {name}');"
        f"open({d!r}+'/env.txt','w').write(','.join(sorted(os.environ)));"
        "print('some stdout');print('some stderr',file=sys.stderr);"
    )
    if code == "retry-ok":
        py += f"m={marker!r};e=os.path.exists(m);open(m,'a').write('x');sys.exit(0 if e else 3)"
    else:
        py += f"sys.exit({code})"
    return {"name": name, "argv": [sys.executable, "-c", py], "cwd": root, "env": {"TOY": "1", **(extra_env or {})}, "stdout_file": d + f"/{name}.stdout.txt", "stderr_file": d + f"/{name}.stderr.txt", "writes": [d + "/out.txt"]}


def make(name, specs):
    root = os.path.join(ROOT, name)
    os.makedirs(root)
    units, order = {}, []
    for u, code in specs:
        d = f"{root}/{u}/seed1"
        units[u] = {"runs": {"1": {"output_dir": d, "commands": [cmd(u + "-a", d, 0, root), cmd(u + "-b", d, code, root)]}}}
        order.append(u)
    plan = {"unit_order": order, "output_roots": {"run": root, "dry": root + "_dry"}, "units": units, "dry_run_exclusions": []}
    pp = os.path.join(root, "plan.json")
    json.dump(plan, open(pp, "w"))
    return root, pp


def go(args, expect=True):
    plan = args[args.index("--plan") + 1]
    if expect:
        args = args + ["--expect-plan-sha256", hashlib.sha256(open(plan, "rb").read()).hexdigest()]
    err, so = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(so):
        code = rf.main(args)
    return code, so.getvalue(), err.getvalue()


def main():
    global FAIL
    root, pp = make("ok", [("T1", 0), ("T2", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--check-only"])
    check("--check-only executes nothing and prints the units", code == 0 and "unit T1" in so and not os.path.exists(root + "/T1"), (code, so))
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--jobs", "2"])
    rec = json.load(open(root + "/hashes_seed1.json"))
    f = rec["units"]["T1"]["attempts"][0]["files"]
    out = open(root + "/T1/seed1/out.txt", "rb").read()
    check("two units ran concurrently, exit 0, both recorded", code == 0 and set(rec["units"]) == {"T1", "T2"} and rec["units"]["T1"]["ok"], (code, so, err))
    check("SHA-256 and size of every file under the output directory are recorded", f["out.txt"] == {"sha256": hashlib.sha256(out).hexdigest(), "size": len(out)} and "T1-a.stdout.txt" in f and "T1-b.stderr.txt" in f and "env.txt" in f, f)
    check("both commands of the chain ran, with exit status and wall time recorded", [c["exit_status"] for c in rec["units"]["T1"]["attempts"][0]["commands"]] == [0, 0] and "wall_seconds" in rec["units"]["T1"]["attempts"][0]["commands"][0])
    envs = open(root + "/T1/seed1/env.txt").read().split(",")
    check("the environment is PATH and HOME plus the plan's variables (no USER)", "PATH" in envs and "HOME" in envs and "TOY" in envs and "USER" not in envs, envs)
    check("nothing but unit names and exit statuses is printed (no output content)", "hello" not in so and "some stdout" not in so and "some stderr" not in so and "out.txt" not in so, so)
    # refuse: non-empty
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--units", "T1"])
    check("an existing non-empty output directory is refused (exit 2), nothing overwritten", code == 2 and "refusing" in err and open(root + "/T1/seed1/out.txt", "rb").read() == out, (code, err))
    # retry success
    root, pp = make("retry", [("T1", "retry-ok"), ("T2", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1"])
    rec = json.load(open(root + "/hashes_seed1.json"))
    at = rec["units"]["T1"]["attempts"]
    check("a failing command is re-run once, unchanged, into the sibling seed1_retry1; both attempts recorded", code == 0 and len(at) == 2 and at[0]["ok"] is False and at[1]["ok"] is True and at[1]["dir"].endswith("seed1_retry1") and os.path.isdir(root + "/T1/seed1_retry1")
          and "out.txt" in at[1]["files"] and at[0]["commands"][-1]["exit_status"] == 3, (code, at))
    check("the retry ran the whole chain into the sibling directory (its files are there, the first attempt's files stay)", os.path.exists(root + "/T1/seed1_retry1/T1-a.stdout.txt") and os.path.exists(root + "/T1/seed1/T1-b.stderr.txt"))
    # fail twice -> stop everything
    root, pp = make("stop", [("T1", 0), ("T2", 5), ("T3", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1"])
    rec = json.load(open(root + "/hashes_seed1.json"))
    check("a unit that fails twice stops everything: exit 1, T3 not started, unit name and exit statuses only on stderr", code == 1 and "T3" not in rec["units"] and "STOP unit=T2" in err and "[[0, 5], [0, 5]]" in err and not os.path.exists(root + "/T3"), (code, err, so))
    # --units subset, then a recorded unit refused
    root, pp = make("subset", [("T1", 0), ("T2", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--units", "T2"])
    check("--units runs a subset", code == 0 and os.path.isdir(root + "/T2") and not os.path.exists(root + "/T1"), (code, err))
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--units", "T1"])
    rec = json.load(open(root + "/hashes_seed1.json"))
    check("a later invocation adds the other unit to the same record", code == 0 and set(rec["units"]) == {"T1", "T2"}, (code, err))
    # dry set uses the dry root and hashes_dry.json
    root, pp = make("dry", [("T1", 0)])
    plan = json.load(open(pp))
    plan["units"]["T1"]["runs"]["dry"] = {"output_dir": root + "_dry/T1", "commands": [cmd("T1-d", root + "_dry/T1", 0, root)]}
    json.dump(plan, open(pp + ".dry", "w"))
    code, so, err = go(["--plan", pp + ".dry", "--seed-set", "dry"])
    check("the dry set records into <dry root>/hashes_dry.json", code == 0 and os.path.exists(root + "_dry/hashes_dry.json"), (code, err))
    # ---- P10: the expected plan hash is required and checked
    root, pp = make("hashcheck", [("T1", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--expect-plan-sha256", "0" * 64], expect=False)
    check("a plan with another SHA-256 than expected is refused (exit 2) before anything runs", code == 2 and "SHA-256" in err and not os.path.exists(root + "/T1"), (code, err))
    try:
        go(["--plan", pp, "--seed-set", "1"], expect=False)
        missing = False
    except SystemExit as e:
        missing = e.code == 2
    check("--expect-plan-sha256 is required", missing)
    # ---- P1: a failed unit in ANY hash record (this seed set or another, run or dry root) refuses a later start
    root, pp = make("p1", [("T1", 0), ("T2", 5), ("T3", 0)])
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--units", "T1,T2"])
    check("P1 set-up: T2 fails twice, exit 1", code == 1, (code, err))
    code, so, err = go(["--plan", pp, "--seed-set", "1", "--units", "T3"])
    check("P1: a later invocation for the same seed set is refused (exit 2) and starts nothing", code == 2 and "not ok" in err and not os.path.exists(root + "/T3"), (code, err))
    plan = json.load(open(pp))
    plan["units"]["T3"]["runs"]["2"] = {"output_dir": root + "/T3/seed2", "commands": [cmd("T3-x", root + "/T3/seed2", 0, root)]}
    plan["units"]["T3"]["runs"]["dry"] = {"output_dir": root + "_dry/T3", "commands": [cmd("T3-d", root + "_dry/T3", 0, root)]}
    json.dump(plan, open(pp + ".more", "w"))
    code, so, err = go(["--plan", pp + ".more", "--seed-set", "2", "--units", "T3"])
    check("P1: also refused for ANOTHER seed set (seed 2) when the record of seed 1 holds a failed unit", code == 2 and not os.path.exists(root + "/T3"), (code, err))
    code, so, err = go(["--plan", pp + ".more", "--seed-set", "dry", "--units", "T3"])
    check("P1: also refused for the dry set", code == 2 and not os.path.exists(root + "_dry/T3"), (code, err))
    # ---- P2: an error of the runner itself is recorded for the unit, everything stops
    root, pp = make("p2", [("T1", 0), ("T2", 0), ("T3", 0)])
    plan = json.load(open(pp))
    c2 = plan["units"]["T2"]["runs"]["1"]["commands"]
    c2[1]["stdout_file"] = c2[0]["stdout_file"]  # two commands of a chain share a stdout file: the second open raises FileExistsError in the runner
    json.dump(plan, open(pp, "w"))
    code, so, err = go(["--plan", pp, "--seed-set", "1"])
    rec = json.load(open(root + "/hashes_seed1.json"))
    t2 = rec["units"].get("T2", {})
    check("P2: a runner exception is recorded for its unit (type and message), later units do not start, exit 1",
          code == 1 and t2.get("ok") is False and t2.get("runner_exception", {}).get("type") == "FileExistsError" and "T3" not in rec["units"] and not os.path.exists(root + "/T3") and "STOP unit=T2 runner error FileExistsError" in err, (code, err, t2))
    check("P2: the record keeps the hashes of what existed and no output content", "T2-a.stdout.txt" in json.dumps(t2.get("files_present", {})) and "hello" not in json.dumps(rec))
    print(f"RESULT pass={PASS} fail={FAIL} run_dir={ROOT}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
