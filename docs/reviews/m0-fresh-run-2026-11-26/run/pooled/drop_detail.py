import json, collections
O="/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/pooled/"
drop=json.load(open(O+"dropped.json")); per=json.load(open(O+"per_lineage.json"))
r0=drop[0]["all_rows_over_the_bound"][0]; print("row keys:",sorted(r0))
for d in drop:
    rows=d["all_rows_over_the_bound"]
    c=collections.defaultdict(list)
    for r in rows: c[(r["rule"][:70],r["unit"])].append((r["level"],float(r.get("excess_decimal", r.get("excess",0)) if not isinstance(r.get("excess"),str) else 0)))
    print("\n",d["lineage"],len(rows),"rows;",len(c),"distinct rule@unit")
    for k,v in sorted(c.items(),key=lambda kv:-len(kv[1]))[:7]: print("    ",k[0],"@",k[1],"levels",sorted({a for a,_ in v}))
dl={d["lineage"] for d in drop}
k0=next(iter(per)); print("\nper_lineage entry keys:",json.dumps(per[k0])[:500])
