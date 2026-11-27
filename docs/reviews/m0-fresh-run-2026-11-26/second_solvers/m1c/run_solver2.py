"""Apply solver2_m1c to the answer-free fixtures; write answers_m1c.jsonl.
Also: check text-parsed inputs equal `structured`, answer format, and count
items where the tip split is not a whole number of cents."""
import json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_m1c as S

FIX = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
LINS = sorted(S.SOLVERS)
INT_RE = re.compile(r"^(0|[1-9]\d*)$")
MONEY_RE = re.compile(r"^-?(0|[1-9]\d*)(\.\d?[1-9])?$")
MONEY = {"M1.shopping_r3", "M1.tiered_pricing", "M1.tip_split_r3"}

out = []
problems = []
stats = collections.Counter()
for lin in LINS:
    rows = [json.loads(l) for l in open(os.path.join(FIX, lin, "fixtures.jsonl"))]
    assert len(rows) == 280, (lin, len(rows))
    for r in rows:
        st = r["structured"]
        try:
            ans = S.SOLVERS[lin](r["question"], st)
        except Exception as e:
            problems.append((r["id"], "solver error: %r" % e)); continue
        try:
            t = S.TEXT_PARSERS[lin](r["question"])
            if json.loads(json.dumps(t)) != st:
                problems.append((r["id"], "text != structured: %r vs %r" % (t, st)))
            ans_t = S.SOLVERS[lin](r["question"], t)
            if ans_t != ans:
                problems.append((r["id"], "text answer differs %r %r" % (ans_t, ans)))
        except Exception as e:
            problems.append((r["id"], "text parse error: %r" % e))
        fmt = MONEY_RE if lin in MONEY else INT_RE
        if not fmt.match(ans):
            problems.append((r["id"], "format %r" % ans))
        if ans.startswith("-"):
            problems.append((r["id"], "negative answer %r" % ans))
        if lin == "M1.tip_split_r3" and (S.tip_split_exact(st) * 100).denominator != 1:
            problems.append((r["id"], "tip split not whole cents: exact %s" % S.tip_split_exact(st)))
        stats[lin] += 1
        out.append({"id": r["id"], "level": r["level"], "index": r["index"], "answer": ans})

with open(os.path.join(HERE, "answers_m1c.jsonl"), "w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")
print("answers written:", len(out))
for lin in LINS:
    print(lin, stats[lin])
print("problems:", len(problems))
for p in problems:
    print(" ", p)
