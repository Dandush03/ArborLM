import json
F="/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"
S="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_uncounted_second_20261126/deliver/uncounted_rules_second.json"
a=json.load(open(F)); b=json.load(open(S))
def rep(name,x,y):
    x=set(x);y=set(y)
    print(name,"first",len(x),"second",len(y),"agree",len(x&y))
    for e in sorted(x-y,key=str): print("   only first :",e)
    for e in sorted(y-x,key=str): print("   only second:",e)
# R1
print("R1 first sample:",[ (e["rule"],e["label"],e["lineage_stems"]) for e in a["R1"]["entries"] if e["label"]!="M"][:4])
rep("R1",[(e["rule"],str(e["lineage_stems"]).replace("every R1 lineage","all")) for e in a["R1"]["entries"]],
         [(e["rule"],e["lineage_scope"]) for e in b["R1"]])
# R2
rep("R2 klass",[(e["text"],e["label"]) for e in a["R2"]["entries"]],[(e["match"],e["class"]) for e in b["R2"] if e["kind"]=="klass_clause"])
print("R2 new first keys:",a["R2"]["new_rules"]["entries"][:1])
rep("R2 new",[json.dumps(e.get("rule",e.get("text",e)) ) for e in a["R2"]["new_rules"]["entries"]],[json.dumps(e["match"]) for e in b["R2"] if e["kind"]=="new_rule"])
rep("M1",[(e["lineage_stem"],e["rule"]) for e in a["M1"]["entries"]],[(e["lineage_stem"],e["prefixed_key"]) for e in b["M1"]])
print("C1 first sources:",sorted({e["source"] for e in a["C1"]["entries"]}))
print("C1 second outputs:",sorted({e["output_of"].split("/")[-1] for e in b["C1"]}))
rep("C1 names only",[e["text"] for e in a["C1"]["entries"]],[e["rule"] for e in b["C1"]])
