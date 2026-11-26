"""A made-up plan in run_plan.json's schema to exercise run_fresh.py with harmless commands (python3 -I -c writing a file). No plan unit is run."""
import json, os, sys
root = os.path.abspath(sys.argv[1]); os.makedirs(root, exist_ok=False)
py = "/usr/bin/python3"
def cmd(name, outdir, code):
    return {"name": name, "argv": [py, "-I", "-c", code, outdir], "cwd": root, "env": {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "SECRET_FIGURE": "0.4242"},
            "stdout_file": outdir + "/stdout.txt", "stderr_file": outdir + "/stderr.txt", "writes": [outdir + "/out.txt"]}
W = "import sys,os; open(sys.argv[1]+'/out.txt','w').write('figure 0.4242\\n'); print('figure 0.4242')"
RETRY = "import sys,os; open(sys.argv[1]+'/out.txt','w').write('figure 0.4242\\n'); print('figure 0.4242'); sys.exit(0 if sys.argv[1].endswith('_retry1') else 1)"
FAIL = "import sys; print('figure 0.4242'); sys.exit(2)"
units = {"R1a": [("w", W)], "R1b": [("w", W), ("retry", RETRY)], "R1c": [("fail", FAIL)], "R2a": [("w", W)]}
plan = {"unit_order": list(units), "output_roots": {"run": root + "/run", "dry": root + "/dry"}, "dry_run_exclusions": [],
        "units": {u: {"runs": {"1": {"output_dir": f"{root}/run/{u}/seed1", "commands": [cmd(f"{u}-{n}", f"{root}/run/{u}/seed1", c) for n, c in cs]}}} for u, cs in units.items()}}
json.dump(plan, open(root + "/plan.json", "x"), indent=1)
