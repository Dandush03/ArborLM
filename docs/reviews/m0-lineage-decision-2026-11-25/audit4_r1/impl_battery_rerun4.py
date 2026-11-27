# ruff: noqa
"""Audit 4 (R1): rerun the IMPLEMENTER's battery (studies.m0.r1_fix3_battery.measure, unchanged, imported read-only) on every shape of
registered_v3(), with the auditor's throwaway seeds; writes its rows (plus which of its heuristic functions raised on the shape).
usage (implementation worktree root): PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <n> <seed> <fit> <out.jsonl> <lineage id>
"""
import json, sys
sys.path.insert(0, ".")
from studies.m0 import r1_fix3_battery as B
from studies.m0.lineages_r1_fix3_clusters import registered_v3

n, seed, fit, out, lid = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
lin = {x.id: x for x in registered_v3()}[lid]
rows = B.measure(lin, n, seed, fit)
with open(out, "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
errs = sorted({r["heuristic"] for r in rows if r["heuristic"].endswith("_error")})
print(json.dumps({"id": lid, "error_functions": errs, "summary": B.summarise(rows)}))
