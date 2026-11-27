import json, collections
O="/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/pooled/"
drop=json.load(open(O+"dropped.json")); per=json.load(open(O+"per_lineage.json")); x=json.load(open(O+"report_extras.json"))
s=json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
m=json.load(open("studies/m0/manifests/map_of_record.json"))
of={i:c["cluster_id"] for c in m["clusters"] for i in c["members"]}
grp={c:gi for gi,g in enumerate(m["groups"]) for c in g}; gsz={gi:len(g) for gi,g in enumerate(m["groups"])}
print("dropped keys:",sorted(drop[0])[:20])
dl={d.get("lineage") or d.get("id") for d in drop}
big=max(gsz,key=gsz.get)
for e in ("R1","R2","M1","C1"):
    left=[i for i in s[e] if i not in dl]
    cb=len({of[i] for i in s[e]}); ca={of[i] for i in left}
    print(e,"lineages",len(s[e]),"->",len(left),"| clusters",cb,"->",len(ca),"| of which in the big group",sum(1 for c in ca if grp[c]==big),"outside",sum(1 for c in ca if grp[c]!=big))
allc={of[i] for e in s for i in s[e] if i not in dl}
print("global clusters with a remaining lineage:",len(allc),"in big group",sum(1 for c in allc if grp[c]==big))
# which rules drop each lineage (distinct rule names over the bound)
print("per_lineage type",type(per), (list(per)[:3] if isinstance(per,dict) else per[0].keys()))
for d in drop:
    lid=d.get("lineage") or d.get("id")
    rows=d.get("rows_over_the_bound") or d.get("rows") or []
    names=collections.Counter((r.get("rule"),r.get("unit")) for r in rows) if rows else {}
    print(lid, "| distinct (rule,unit) over bound:",len(names), "|", "; ".join(f"{k[0][:48]}@{k[1]}x{v}" for k,v in list(names.items())[:6]))
print("R-56 differing:",x["m1a_bracket_second_reading_lineages_whose_outcome_differs"])
print("exact R1 rows:",json.dumps(x["r1_exact_rows"])[:600])
print("fallbacks:",json.dumps(x["a3_wrapper_fallbacks"])[:500])
print("counted rows with no items:",len(x["counted_rows_with_no_items"]))
