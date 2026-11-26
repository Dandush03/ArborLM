import json,sys
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2/"
lin=sys.argv[1]; lv=[int(x) for x in sys.argv[2].split(",")]
for line in open(F+lin+"/fixtures.jsonl"):
    r=json.loads(line)
    if r["level"] in lv and r["index"]<int(sys.argv[3]):
        print("---",r["id"],r["level"],r["index"]); print(r["question"]); print(json.dumps(r["structured"]))
