# ruff: noqa
"""Audit step 4a: check every C1 batch-1 fixture item with the auditor's own evaluator.

Per item: question frame; ast.parse(question source) -> tree equals `structured.program` (render fidelity, parse only);
own evaluator output == key; constructs vs what solvers_c1 implements (read, not imported); hazards; step count;
then (optional, --isolated) the repo's own isolated runner c1grammar.run_isolated twice on all sources (the only place a
program source is executed by Python, as the task allows).
Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this> [--isolated]
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from a02_myeval import EvalError, construct_problems, evaluate, tree_from_question

OUT = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob("studies/m0/fixtures/c1_batch1/*.jsonl"))
items = []
for f in files:
    with open(f) as fh:
        for line in fh:
            items.append(json.loads(line))
print("files", len(files), "items", len(items))
ids = Counter(it["id"] for it in items)
print("duplicate ids", [k for k, v in ids.items() if v > 1][:5])
per = Counter((it["lineage"], it["level"]) for it in items)
print("cells", len(per), "per-cell counts", sorted(set(per.values())))
qdup = Counter((it["lineage"], it["question"]) for it in items)
print("duplicate questions within lineage", sum(1 for v in qdup.values() if v > 1))
print("keys", sorted(set().union(*[set(it) for it in items])))

bad = []
hz_tot = defaultdict(Counter)
cons_tot = defaultdict(Counter)
steps_max = defaultdict(int)
depth_max = defaultdict(int)
for it in items:
    lid = it["lineage"]
    prog = it["structured"]["program"]
    try:
        t = tree_from_question(it["question"])
    except Exception as ex:
        bad.append((it["id"], "parse", repr(ex)))
        continue
    if json.loads(json.dumps(t)) != prog:
        bad.append((it["id"], "render-mismatch", ""))
    try:
        out, m = evaluate(prog)
    except EvalError as ex:
        bad.append((it["id"], "myeval-error", str(ex)))
        continue
    if out != it["answer"]:
        bad.append((it["id"], "myeval!=key", f"{out!r} vs {it['answer']!r}"))
    for k, v in m.hz.items():
        hz_tot[lid][k] += 1
    for p in construct_problems(prog):
        cons_tot[lid][p] += 1
    steps_max[lid] = max(steps_max[lid], m.steps)
    depth_max[lid] = max(depth_max[lid], m.max_depth)
    if it["answer_type"] != "line" or it["k"] is not None:
        bad.append((it["id"], "type", f"{it['answer_type']} {it['k']}"))
    a = it["answer"]
    if a != a.lower() or a != a.strip() or "  " in a or a == "" or a.endswith("."):
        bad.append((it["id"], "normalisation", a))

print("problems", len(bad))
for b in bad[:50]:
    print("  ", b)
print("hazards per lineage (items with >=1 occurrence):")
for lid in sorted(hz_tot):
    print("  ", lid, dict(hz_tot[lid]))
print("constructs the second solver lacks:")
for lid in sorted(cons_tot):
    print("  ", lid, dict(cons_tot[lid]))
print("max evaluator steps / max call depth per lineage:")
for lid in sorted(steps_max):
    print(f"   {lid:28s} steps {steps_max[lid]:7d} depth {depth_max[lid]}")

if "--isolated" in sys.argv:
    from studies.m0.c1grammar import run_isolated
    from a02_myeval import source_of_question
    srcs = [source_of_question(it["question"]) for it in items]
    r1 = run_isolated(srcs)
    r2 = run_isolated(srcs)
    nd = [(it["id"], a, b) for it, a, b in zip(items, r1, r2) if a != b]
    wrong = [(it["id"], a) for it, a in zip(items, r1) if a["out"] != it["answer"]]
    print("isolated: nondeterministic", len(nd), "run1 != key", len(wrong))
    for x in (nd + wrong)[:20]:
        print("  ", x)
json.dump({"n": len(items), "problems": bad, "hazards": {k: dict(v) for k, v in hz_tot.items()},
           "constructs_missing_in_solver": {k: dict(v) for k, v in cons_tot.items()},
           "steps_max": steps_max, "depth_max": depth_max}, open(os.path.join(OUT, "a03_fixtures_result.json"), "w"), indent=1, sort_keys=True)
