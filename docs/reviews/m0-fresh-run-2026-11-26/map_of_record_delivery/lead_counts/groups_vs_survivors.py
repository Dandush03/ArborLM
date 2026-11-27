import json
m=json.load(open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_map_of_record_20261126/deliver/map_of_record.json"))
s=json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
surv={i:e for e,l in s.items() for i in l}
cl={c["cluster_id"]:c["members"] for c in m["clusters"]}
of={x:cid for cid,ms in cl.items() for x in ms}
print("survivors missing from map:",[i for i in surv if i not in of])
sc={}  # cluster -> set of evals with survivors
for i,e in surv.items(): sc.setdefault(of[i],set()).add(e)
print("clusters holding a survivor:",len(sc))
for e in ("R1","R2","M1","C1"): print(" ",e,"survivor lineages",len(s[e]),"-> clusters",sum(1 for c,v in sc.items() if e in v))
print("survivor clusters spanning >1 evaluation:",sum(1 for v in sc.values() if len(v)>1))
ingroup={c:gi for gi,g in enumerate(m["groups"]) for c in g}
print("groups total",len(m["groups"]),"sizes>1:",sorted([len(g) for g in m["groups"] if len(g)>1],reverse=True))
for gi,g in enumerate(m["groups"]):
    if len(g)>1:
        k=[c for c in g if c in sc]
        per={e:sum(1 for c in k if e in sc[c]) for e in ("R1","R2","M1","C1")}
        print(" group of",len(g),"clusters: survivor-holding clusters",len(k),per)
free=[c for c in sc if len(m["groups"][ingroup[c]])==1] if all(c in ingroup for c in sc) else None
print("survivor clusters in singleton groups:",None if free is None else len(free), "not in any group:",sum(1 for c in sc if c not in ingroup))
if free is not None:
    print(" per evaluation:",{e:sum(1 for c in free if e in sc[c]) for e in ("R1","R2","M1","C1")})
bp=m["borderline_pairs"]; 
both=[p for p in bp if p[0] in surv and p[1] in surv]
print("borderline pairs",len(bp),"with both ends survivors",len(both),"with >=1 survivor end",sum(1 for p in bp if p[0] in surv or p[1] in surv))
