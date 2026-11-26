"""Pick, per lineage, the shortest program at levels 0, 3 and 6 for hand tracing; print source and my answer."""
import json, os, sys
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
D = os.path.dirname(os.path.abspath(__file__))
PRE = "Here is a Python program.\n\n"; SUF = "\n\nWhat exactly does it print? It prints a single line."
ans = {(r["id"], r["level"], r["index"]): r["answer"] for r in map(json.loads, open(os.path.join(D, "answers_c1.jsonl")))}
lins = sorted(os.listdir(F))[int(sys.argv[1]):int(sys.argv[2])]
for lin in lins:
    items = [json.loads(l) for l in open(os.path.join(F, lin, "fixtures.jsonl"))]
    for lv in (0, 3, 6):
        cand = [it for it in items if it["level"] == lv]
        it = min(cand, key=lambda it: (len(it["question"]), it["index"]))
        print("=====", lin, "level", lv, "index", it["index"], "MY ANSWER:", ans[(lin, lv, it["index"])])
        print(it["question"][len(PRE):-len(SUF)])
