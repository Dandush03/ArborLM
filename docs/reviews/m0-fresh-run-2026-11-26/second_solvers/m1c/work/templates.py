import json, re, sys, collections
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
for lin in sys.argv[1:]:
    rows=[json.loads(l) for l in open(F+lin+"/fixtures.jsonl")]
    c=collections.Counter(); ex={}
    for r in rows:
        t=re.sub(r"\d+(\.\d+)?","#",r["question"])
        t=re.sub(r"\b[A-Z][a-z]+\b","Nm",t)
        c[t]+=1; ex.setdefault(t,r)
    print("=====",lin,len(rows),"templates",len(c))
    for t,n in c.most_common():
        print("--",n,"|",ex[t]["id"],ex[t]["level"]); print(ex[t]["question"]); print(json.dumps(ex[t]["structured"]))
