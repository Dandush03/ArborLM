import json, os
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
want = {"for","def","ret","slice","m","setidx","append","and","or","not","idx","call","print","aug","if","while"}
seen = {}
def walk(x):
    if isinstance(x, list) and x and isinstance(x[0], str) and x[0] in want and x[0] not in seen:
        s = json.dumps(x)
        seen[x[0]] = s[:400]
    if isinstance(x, list):
        for y in x: walk(y)
for lin in sorted(os.listdir(F)):
    for line in open(os.path.join(F, lin, "fixtures.jsonl")):
        walk(json.loads(line)["structured"]["program"])
for k, v in sorted(seen.items()): print(k, "=>", v)
# shapes of if (lengths) and slice, ret
import collections
c = collections.Counter()
def walk2(x, ctx):
    if isinstance(x, list) and x and isinstance(x[0], str):
        if x[0] in ("if","slice","ret","for","def","m","call","print","while","setidx","append","idx") and ctx=="stmt_or_expr":
            c[(x[0], len(x))] += 1
    if isinstance(x, list):
        for y in x: walk2(y, "stmt_or_expr")
for lin in sorted(os.listdir(F)):
    for line in open(os.path.join(F, lin, "fixtures.jsonl")):
        walk2(json.loads(line)["structured"]["program"], "stmt_or_expr")
for k in sorted(c): print(k, c[k])
