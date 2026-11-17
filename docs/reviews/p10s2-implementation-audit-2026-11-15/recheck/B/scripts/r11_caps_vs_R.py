"""Re-check B, R11: the frozen stage-cap table against 2R, for the rates the exercise's rehearsal measured and for a scaled-up copy (pinned configuration: the registered rungs).
Usage: PYTHONPATH=<pin>/src python r11_caps_vs_R.py <pin> <rates.json>"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from studies.p10s2 import budget
base = budget.Rates.from_json(json.loads(Path(sys.argv[2]).read_text()))
import dataclasses
for label, ovh in (("as measured", base.task_overhead_seconds), ("start-up 60 s", 60.0)):
    rates = dataclasses.replace(base, task_overhead_seconds=ovh)
    caps = budget.stage_caps(rates)
    for n, u in budget.rungs():
        k = budget.config_key(n, u)
        s = sum(caps[k].values()); twoR = 2 * budget.registered_run_seconds(n, u, rates)["total"]
        print(json.dumps({"rates": label, "config": k, "sum_of_stage_caps_s": round(s, 3), "two_R_s": round(twoR, 3), "excess_s": round(s - twoR, 3), "two_x_overhead_s": round(2 * ovh, 3)}))
