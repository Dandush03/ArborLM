"""Auditor perturbation check: p7b_reproduction must report DIFFERENT when one P7-B recorded count is perturbed in memory."""
import copy, sys
from pathlib import Path
from arborlm import p8_sim
orig = p8_sim.read_json
target = sys.argv[1]  # which field to perturb
def patched(path):
    d = orig(path)
    p = str(path)
    if "simulate-a" in p and p.endswith("b101-o301-flat-s501.result.json"):
        d = copy.deepcopy(d)
        g = d["record"]["streams"][target.split("|")[0]]["L-COAX|R2"]["by_c"]["32"]["asc"]
        g[target.split("|")[1]] += 1
    return d
p8_sim.read_json = patched
rec = p8_sim.p7b_reproduction(Path(sys.argv[2]), Path.cwd(), labels=("b101-o301-flat-s501",))
v = rec["labels"]["b101-o301-flat-s501"]
print(target, rec["verdict"], v["count_differences"], [k for k,x in v["m_table"].items() if not x["equal"]])
