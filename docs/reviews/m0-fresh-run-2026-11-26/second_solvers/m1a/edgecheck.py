import json, math
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
def rows(l): return [json.loads(x) for x in open(F+"M1."+l+"/fixtures.jsonl")]
A={}
for x in open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_solver2_m1a_20261126/answers_m1a.jsonl"):
    o=json.loads(x); A[o["id"]]=o["answer"]
# crt
nc=0; zero=0
for r in rows("crt_congruence_r3"):
    ms=[m for m,_ in r["structured"]["conditions"]]
    if any(math.gcd(a,b)>1 for i,a in enumerate(ms) for b in ms[i+1:]): nc+=1
    if all(rr==0 for _,rr in r["structured"]["conditions"]): zero+=1
print("crt noncoprime",nc,"allzero",zero)
# fd
print("fd ask<=len", sum(r["structured"]["ask"]<=len(r["structured"]["terms"]) for r in rows("finite_differences_r4")),
      "len-degree", sorted(set((len(r["structured"]["terms"]),r["structured"]["degree"],r["structured"]["ask"]-len(r["structured"]["terms"])) for r in rows("finite_differences_r4"))))
# change
print("change target0", sum(r["structured"]["target"]==0 for r in rows("change_ways_r3")), "answers0", sum(A[r["id"]]=="0" for r in rows("change_ways_r3")))
# division
for sh in ("empty_seats","pallets"):
    rs=[r for r in rows("division_counting_r3") if r["structured"]["shape"]==sh]
    print("div",sh,len(rs),"ans0",sum(A[r["id"]]=="0" for r in rs))
rs=[r for r in rows("division_counting_r3") if r["structured"]["shape"]=="pallets"]
print("pallets boxes<crate", sum(r["structured"]["items"]//r["structured"]["box"]<r["structured"]["crate"] for r in rs))
# consec
print("consec neg answers", sum(A[r["id"]].startswith("-") for r in rows("consecutive_r3")), "steps", sorted(set(r["structured"]["step"] for r in rows("consecutive_r3"))))
# avg
print("avg answer 0 or =max", [(r["id"],A[r["id"]]) for r in rows("average_missing_r4") if A[r["id"]]=="0"])
import re
print("avg mean formats", sorted(set(re.search(r"exactly ([\d.]+)\?",r["question"]).group(1).split(".")[-1] if "." in re.search(r"exactly ([\d.]+)\?",r["question"]).group(1) else "int" for r in rows("average_missing_r4")))[:30])
# ages
print("ages younger ask",sum(r["structured"]["ask"]=="younger" for r in rows("ages_r3")), "k", sorted(set(r["structured"]["k"] for r in rows("ages_r3"))))
# clock gaps
print("clock min gap", min(b[0]-a[1] for r in rows("clock_duration_r4") for a,b in zip(r["structured"]["legs"],r["structured"]["legs"][1:])))
# fraction
print("frac a,b ranges", sorted(set(r["structured"]["a"] for r in rows("fraction_remainder_r3"))), sorted(set(r["structured"]["b"] for r in rows("fraction_remainder_r3"))))
print("frac words", sorted(set(w for r in rows("fraction_remainder_r3") for w in re.findall(r"one (\w+) of", r["question"]))))
