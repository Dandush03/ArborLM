import json, re, sys, collections
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
PRE=[r"^[A-Z][a-z]+ of [A-Z][a-z]+ wrote this problem for a maths club\. ",r"^[A-Z][a-z]+ from [A-Z][a-z]+ found this problem in a puzzle book\. ",r"^This problem comes from a quiz held in [A-Z][a-z]+, set by [A-Z][a-z]+\. ",r"^At a maths club in [A-Z][a-z]+, [A-Z][a-z]+ is asked this\. "]
def norm(q):
    p=-1
    for i,pp in enumerate(PRE):
        if re.match(pp,q): q=re.sub(pp,"",q); p=i
    t=re.sub(r"\d+(\.\d+)?","#",q)
    t=re.sub(r"\b[A-Z][a-z]+\b","Nm",t)
    t=re.sub(r"(Nm, )+Nm and Nm|Nm and Nm","NAMES",t)
    return p,t
for lin in sys.argv[1:]:
    rows=[json.loads(l) for l in open(F+lin+"/fixtures.jsonl")]
    c=collections.Counter(); ex={}; pc=collections.Counter()
    for r in rows:
        p,t=norm(r["question"]); pc[p]+=1
        c[t]+=1; ex.setdefault(t,r)
    print("=====",lin,len(rows),"templates",len(c),"preambles",dict(pc))
    for t,n in c.most_common():
        print("--",n,"|",ex[t]["id"],"L",ex[t]["level"]); print(" T:",t); print(" Q:",ex[t]["question"]); print(" S:",json.dumps(ex[t]["structured"]))
