import json,sys,re,collections
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2/"
lin=sys.argv[1]
c=collections.Counter(); ex={}
for line in open(F+lin+"/fixtures.jsonl"):
    r=json.loads(line); q=r["question"]; s=r["structured"]
    for k in ("text","digits","word"):
        v=s.get(k)
        if isinstance(v,str) and v: q=q.replace(v,"<"+k+">")
    if "towns" in s:
        for t in sorted(s["towns"],key=len,reverse=True): q=q.replace(t,"<T>")
    if "letters" in s:
        q=q.replace(", ".join(s["letters"]),"<L>")
    q=re.sub(r"-?\d+","#",q)
    q=re.sub(r"#(, #)+","#LIST",q)
    q=re.sub(r"[01]{2,}","<bits>",q)
    c[q]+=1; ex.setdefault(q,r["id"]+" L%d i%d"%(r["level"],r["index"]))
for q,n in c.most_common():
    print("==",n,ex[q]); print(q)
print("DISTINCT",len(c))
