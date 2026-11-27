import json, sys
D="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R1/"
lin=sys.argv[1]; levels=[int(x) for x in sys.argv[2].split(",")]
for line in open(D+"R1."+lin+"/fixtures.jsonl"):
    r=json.loads(line)
    if r["level"] in levels and r["index"]<int(sys.argv[3]):
        print("---",r["id"]); print(r["question"]); print(json.dumps(r["structured"]))
