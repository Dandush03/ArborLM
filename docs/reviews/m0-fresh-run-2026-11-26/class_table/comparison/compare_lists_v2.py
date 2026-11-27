import json,sys
F="/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"
S="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_uncounted_second_20261126/deliver/uncounted_rules_second.json"
a=json.load(open(F)); b=json.load(open(S)); ok=True
def rep(name,x,y):
    global ok
    x=set(x);y=set(y); d=(x-y)|(y-x)
    print(name,"first",len(x),"second",len(y),"agree",len(x&y),"differ",len(d))
    for e in sorted(d,key=str): print("   DIFF",e)
    ok = ok and not d
def stems(v): return "all" if v=="every R1 lineage" else ",".join(sorted(v))
rep("R1",[(e["rule"],stems(e["lineage_stems"])) for e in a["R1"]["entries"]],[(e["rule"],e["lineage_scope"]) for e in b["R1"]])
rep("R2 klass (text,class,order)",[(e["text"],e["label"],e["order"]) for e in a["R2"]["entries"]],[(e["match"],e["class"],e["clause_index"]) for e in b["R2"] if e["kind"]=="klass_clause"])
rep("R2 new",[e["rule"] for e in a["R2"]["new_rules"]["entries"]],[e["match"] for e in b["R2"] if e["kind"]=="new_rule"])
rep("M1",[(e["lineage_stem"],e["rule"]) for e in a["M1"]["entries"]],[(e["lineage_stem"],e["prefixed_key"]) for e in b["M1"]])
def src1(s):
    if s.startswith("a3"): return ["a3_shortcuts.py"]
    if s.startswith("a4"): return ["s5_analyse_v2.py"]
    if s.startswith("battery"): return ["battery"]
    return ["f5_closed_forms.py","f5b_closed_forms_v2.py"]
def src2(p):
    n=p.split("/")[-1]; return "battery" if n=="c1_fix3_battery.py" else n
rep("C1 (output,name)",[(s,e["text"]) for e in a["C1"]["entries"] for s in src1(e["source"])],[(src2(e["output_of"]),e["rule"]) for e in b["C1"]])
print("ALL AGREE" if ok else "DIFFERENCES"); sys.exit(0 if ok else 1)
