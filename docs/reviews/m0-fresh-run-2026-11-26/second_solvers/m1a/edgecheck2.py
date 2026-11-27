import json, re
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
def rows(l): return [json.loads(x) for x in open(F+"M1."+l+"/fixtures.jsonl")]
A={}
for x in open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_solver2_m1a_20261126/answers_m1a.jsonl"):
    o=json.loads(x); A[(o["id"],o["level"],o["index"])]=o["answer"]
print("unique answer keys", len(A))
K=lambda r:(r["id"],r["level"],r["index"])
print("change answers0", sum(A[K(r)]=="0" for r in rows("change_ways_r3")), "max", max(int(A[K(r)]) for r in rows("change_ways_r3")))
for sh in ("empty_seats","pallets"):
    rs=[r for r in rows("division_counting_r3") if r["structured"]["shape"]==sh]
    print("div",sh,len(rs),"ans0",sum(A[K(r)]=="0" for r in rs))
rc=rows("consecutive_r3")
print("consec neg answers", sum(A[K(r)].startswith("-") for r in rc), "zero", sum(A[K(r)]=="0" for r in rc))
for r in rc:
    if r["structured"]["sum"]<0: print("  ",r["level"],r["index"],r["structured"],A[K(r)])
ra=rows("average_missing_r4")
print("avg answers 0", sum(A[K(r)]=="0" for r in ra), "== max", sum(int(A[K(r)])==int(re.search(r"out of (\d+)",r["question"]).group(1)) for r in ra))
