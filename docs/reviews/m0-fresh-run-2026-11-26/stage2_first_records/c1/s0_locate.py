# ruff: noqa
"""Stage-2 C1 audit, step 0: locate the builder function (file:line) of every survivor lineage. Reads code only; builds no item."""
import inspect, json, os, sys
sys.path.insert(0, os.getcwd())
from studies.m0.lineages_c1_fix4 import all_written
surv = json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["C1"]
w = all_written()
out = {}
for lid in surv:
    lin = w[lid]
    fn = lin.build if hasattr(lin, "build") else None
    f = getattr(lin, "fn", None) or getattr(lin, "builder", None) or fn
    try:
        src, line = inspect.getsourcelines(f)
        out[lid] = {"file": os.path.relpath(inspect.getsourcefile(f)), "line": line, "len": len(src), "family": lin.family}
    except Exception as ex:
        out[lid] = {"err": repr(ex), "attrs": sorted(vars(lin)) if hasattr(lin, "__dict__") else str(type(lin))}
print(json.dumps(out, indent=1, sort_keys=True))
