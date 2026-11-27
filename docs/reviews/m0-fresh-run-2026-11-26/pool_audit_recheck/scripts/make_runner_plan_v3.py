"""Made-up plans in run_plan.json's schema for run_fresh.py (harmless commands: python3 -I -c writing one file). No plan unit is run.
usage: make_runner_plan_v3.py ROOT KIND   KIND = fail (R1c fails twice) | runner_error (R1b's two commands share one stdout file)"""
import json, os, sys
root, kind = os.path.abspath(sys.argv[1]), sys.argv[2]; os.makedirs(root, exist_ok=False)
py = "/usr/bin/python3"
def cmd(name, outdir, code, shared=False):
    so = outdir + ("/stdout.txt" if shared else f"/{name}.stdout.txt"); se = outdir + ("/stderr.txt" if shared else f"/{name}.stderr.txt")
    return {"name": name, "argv": [py, "-I", "-c", code, outdir], "cwd": root, "env": {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
            "stdout_file": so, "stderr_file": se, "writes": [outdir + "/out.txt"]}
W = "import sys; open(sys.argv[1]+'/out.txt','w').write('figure 0.4242\\n'); print('figure 0.4242')"
FAIL = "import sys; print('figure 0.4242'); sys.stderr.write('figure 0.4242\\n'); sys.exit(2)"
units = {"R1a": [("w", W, False)], "R1b": [("w", W, kind == "runner_error"), ("w2", W, kind == "runner_error")],
         "R1c": [("f", FAIL if kind == "fail" else W, False)], "R2a": [("w", W, False)]}
def od(u, s): return f"{root}/dry/{u}" if s == "dry" else f"{root}/run/{u}/seed{s}"
plan = {"unit_order": list(units), "output_roots": {"run": root + "/run", "dry": root + "/dry"}, "dry_run_exclusions": [],
        "units": {u: {"runs": {s: {"output_dir": od(u, s), "commands": [cmd(f"{u}-{n}", od(u, s), c, sh) for n, c, sh in cs]} for s in ["1", "2", "dry"]}} for u, cs in units.items()}}
json.dump(plan, open(root + "/plan.json", "x"), indent=1)
