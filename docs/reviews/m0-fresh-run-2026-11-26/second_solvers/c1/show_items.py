"""Print given items (lineage level index ...) with my answer."""
import json, os, sys
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
D = os.path.dirname(os.path.abspath(__file__))
PRE = "Here is a Python program.\n\n"; SUF = "\n\nWhat exactly does it print? It prints a single line."
ans = {(r["id"], r["level"], r["index"]): r["answer"] for r in map(json.loads, open(os.path.join(D, "answers_c1.jsonl")))}
a = sys.argv[1:]
for i in range(0, len(a), 3):
    lin, lv, ix = "C1." + a[i], int(a[i+1]), int(a[i+2])
    for l in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(l)
        if it["level"] == lv and it["index"] == ix:
            print("=====", lin, lv, ix, "MY ANSWER:", ans[(lin, lv, ix)]); print(it["question"][len(PRE):-len(SUF)])
