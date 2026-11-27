import json, sys, re
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
lin=sys.argv[1]
rows=[json.loads(l) for l in open(F+"M1."+lin+"/fixtures.jsonl")]
for lv in range(7):
    for r in [x for x in rows if x["level"]==lv][:2]:
        print(lv, r["index"], repr(r["question"])); print("   ", r["structured"])
tmpl={}
for r in rows:
    t=re.sub(r"\d+","#",r["question"])
    t=re.sub(r"\b[A-Z][a-z]+\b","Name",t)
    tmpl.setdefault(t,0); tmpl[t]+=1
print("templates", len(tmpl))
for t,c in sorted(tmpl.items(), key=lambda x:-x[1])[:12]: print(c, repr(t))
