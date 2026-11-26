"""Copy auditor, step 7: facts on conventions that differ across the four plan fragments. python3 -I a7_conventions.py"""
import json, re
from pathlib import Path
H = Path(__file__).resolve().parent
FR = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f/studies/m0/fresh_run")
out = []
def walk_strings(o):
    if isinstance(o, dict):
        for v in o.values(): yield from walk_strings(v)
    elif isinstance(o, list):
        for v in o: yield from walk_strings(v)
    elif isinstance(o, str): yield o
for ev in ("r1", "r2", "m1", "c1"):
    p = json.loads((FR / ev / f"run_plan_{ev}.json").read_text())
    s = list(walk_strings(p))
    roots = sorted({m.group(1) for x in s for m in [re.match(r"(/Users/\S+?/experiments/(?:_scratch/)?[^/]+)", x)] if m})
    envnames = sorted({k for x in [p] for k in re.findall(r'"([A-Z][A-Z0-9_]{2,})":', json.dumps(p))})
    py = sorted({x for x in s if x.startswith("PYTHONPATH")} )
    out.append(f"== {ev}: top keys {list(p)}")
    out.append(f"   output/dry roots: {roots}")
    out.append(f"   upper-case keys (env vars): {envnames}")
    U = p["units"]; u0 = next(iter(U.values()))
    sets = list(u0["runs"]) if "runs" in u0 else list(u0)
    out.append(f"   seed-set keys: {sets}")
    pp = sorted({v for x in [json.dumps(p)] for v in re.findall(r'"PYTHONPATH": "([^"]*)"', x)})
    out.append(f"   PYTHONPATH values: {pp}")
    out.append(f"   '-I' used in argv: {'-I' in s}; dirs per unit/seed sample: {sorted({re.sub(r'^.*/experiments/', '', x).split('/')[0:3].__str__() for x in s if '/experiments/m0_fresh_run' in x})[:6]}")
    for k in ("dry_run_exclusions", "copies", "copies_sha256", "run_copies"):
        if k in p: out.append(f"   {k}: {json.dumps(p[k])[:300]}")
txt = "\n".join(out) + "\n"
(H / "a7_conventions.out.txt").write_text(txt)
print(txt)
