"""Enumerate constructs in C1 fixtures (ast node types from the question source, and tags in structured)."""
import ast, json, os, sys, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
PRE = "Here is a Python program.\n\n"
SUF = "\n\nWhat exactly does it print? It prints a single line."
nodes = collections.Counter(); tags = collections.Counter(); calls = collections.Counter(); methods = collections.Counter()
ops = collections.Counter(); bad = 0; per_lin_methods = collections.defaultdict(set); per_lin_calls = collections.defaultdict(set)
def walk_s(x, lin):
    if isinstance(x, list) and x and isinstance(x[0], str):
        tags[x[0]] += 1
        if x[0] in ("b", "c", "aug"):
            ops[(x[0], x[1] if x[0] != "aug" else x[2])] += 1
        if x[0] == "call": per_lin_calls[lin].add(x[1])
        if x[0] == "m": per_lin_methods[lin].add(str(x[1:3]))
        for y in x[1:]: walk_s(y, lin)
    elif isinstance(x, list):
        for y in x: walk_s(y, lin)
for lin in sorted(os.listdir(F)):
    for line in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(line); q = it["question"]
        if not (q.startswith(PRE) and q.endswith(SUF)): bad += 1; continue
        src = q[len(PRE):-len(SUF)]
        t = ast.parse(src)
        for n in ast.walk(t):
            nodes[type(n).__name__] += 1
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name): calls[n.func.id] += 1
                elif isinstance(n.func, ast.Attribute): methods[n.func.attr] += 1
                else: calls["<other>"] += 1
            if isinstance(n, ast.Constant): nodes["Const:" + type(n.value).__name__] += 1
        walk_s(it["structured"]["program"], lin)
        assert list(it["structured"].keys()) == ["program"], it["structured"].keys()
print("template mismatches", bad)
print("AST nodes", dict(sorted(nodes.items())))
print("calls", dict(calls)); print("methods", dict(methods))
print("struct tags", dict(tags)); print("ops", dict(ops))
for lin in sorted(per_lin_methods): print(lin, per_lin_methods[lin])
