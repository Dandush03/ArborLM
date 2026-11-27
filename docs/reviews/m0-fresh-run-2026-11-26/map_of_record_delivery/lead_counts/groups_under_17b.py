import json
m=json.load(open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_map_of_record_20261126/deliver/map_of_record.json"))
s=json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
surv={i:e for e,l in s.items() for i in l}
of={x:c["cluster_id"] for c in m["clusters"] for x in c["members"]}
sc={}
for i,e in surv.items(): sc.setdefault(of[i],set()).add(e)
par={c:c for c in sc}
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
n=0
for a,b in m["borderline_pairs"]:
    ca,cb=of[a],of[b]
    if ca in sc and cb in sc and ca!=cb: par[f(ca)]=f(cb); n+=1
g={}
for c in sc: g.setdefault(f(c),[]).append(c)
print("cluster-level borderline pairs between two survivor-holding clusters:",n)
print("groups among 52 survivor clusters under item 17 (b):",len(g),"sizes>1:",sorted([len(v) for v in g.values() if len(v)>1],reverse=True))
for v in g.values():
    if len(v)>1: print("  size",len(v),{e:sum(1 for c in v if e in sc[c]) for e in ("R1","R2","M1","C1")})
# how many borderline pairs came from which source judgement is in MAP_REASONS; count pairs by whether both lineages are survivors / one / none
bp=m["borderline_pairs"]
print("borderline pairs: both survivor",sum(1 for a,b in bp if a in surv and b in surv),"one",sum(1 for a,b in bp if (a in surv)!=(b in surv)),"none",sum(1 for a,b in bp if a not in surv and b not in surv))
