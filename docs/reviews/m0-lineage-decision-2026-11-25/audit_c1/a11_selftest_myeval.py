# ruff: noqa
"""Self-test of the auditor's evaluator (a02) on its riskiest primitives, against the host language's own operators on
random VALUES (no generated program source is executed): slice adjustment, floor division/modulo, str of nested lists,
string count/replace; plus a mutation test: perturbing one literal in fixture programs must change the evaluator's output
for most of them (the checker can fail)."""
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
from a02_myeval import Machine, _adjust_slice, evaluate, to_str

r = random.Random(5)
bad = 0
for _ in range(200000):
    n = r.randint(0, 12)
    a = r.choice([None, r.randint(-15, 15)])
    b = r.choice([None, r.randint(-15, 15)])
    c = r.choice([None, r.choice([-3, -2, -1, 1, 2, 3])])
    xs = list(range(n))
    if [xs[i] for i in _adjust_slice(n, a, b, c)] != xs[a:b:c]:
        bad += 1
print("slice mismatches", bad)
m = Machine()
bad = 0
for _ in range(200000):
    x, y = r.randint(-500, 500), r.choice([v for v in range(-30, 31) if v])
    if m.binop("//", x, y) != x // y or m.binop("%", x, y) != x % y:
        bad += 1
print("floor div/mod mismatches", bad)
hz = Counter()
bad = 0
for _ in range(20000):
    v = [r.randint(-50, 50) for _ in range(r.randint(0, 5))]
    w = [v, "ab", [r.randint(0, 3)], -7]
    if to_str(w, hz) != str(w) or to_str(v, hz) != str(v):
        bad += 1
print("str() mismatches", bad)
bad = 0
for _ in range(20000):
    s = "".join(r.choice("abc") for _ in range(r.randint(0, 9)))
    o = "".join(r.choice("abc") for _ in range(r.randint(1, 2)))
    nw = "".join(r.choice("xy") for _ in range(r.randint(0, 2)))
    if m.method(s, "count", [o]) != s.count(o) or m.method(s, "replace", [o, nw]) != s.replace(o, nw):
        bad += 1
print("count/replace mismatches", bad)

# mutation test on fixtures
changed = total = 0
for f in sorted(glob.glob("studies/m0/fixtures/c1_batch1/*.jsonl")):
    for line in open(f):
        it = json.loads(line)
        prog = it["structured"]["program"]
        lits = []

        def walk(x, path):
            if isinstance(x, list):
                if len(x) == 2 and x[0] == "n" and isinstance(x[1], int):
                    lits.append(path)
                for i, y in enumerate(x):
                    walk(y, path + [i])

        walk(prog, [])
        if not lits:
            continue
        p2 = json.loads(json.dumps(prog))
        path = lits[len(lits) // 2]
        node = p2
        for i in path:
            node = node[i]
        node[1] += 1
        total += 1
        try:
            out, _ = evaluate(p2)
        except Exception:
            changed += 1
            continue
        if out != it["answer"]:
            changed += 1
print(f"mutation test: {changed}/{total} perturbed programs give a different output or an error")
