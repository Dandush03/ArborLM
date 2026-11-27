import json, collections
from fractions import Fraction
O="/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/pooled/"
drop=json.load(open(O+"dropped.json")); per=json.load(open(O+"per_lineage.json"))
print("excess form:",json.dumps(drop[0]["all_rows_over_the_bound"][0])[:300])
def val(r):
    a=r["abs_excess_plus_uncertainty"]
    if isinstance(a,dict): a=a.get("decimal") or a.get("fraction")
    try: return float(a)
    except Exception: return float(Fraction(str(a)))
for d in drop:
    rows=d["all_rows_over_the_bound"]; c=collections.defaultdict(list)
    for r in rows: c[(r["rule"][:64],r["unit"])].append((r["level"],val(r)))
    print("\n",d["lineage"],len(rows),"rows;",len(c),"distinct rule@unit")
    for k,v in sorted(c.items(),key=lambda kv:-max(b for _,b in kv[1]))[:6]: print("    %-64s @%s levels %s max %.3f"%(k[0],k[1],sorted({a for a,_ in v}),max(b for _,b in v)))
dl={d["lineage"] for d in drop}
k0=next(iter(per)); print("\nper_lineage entry:",json.dumps(per[k0])[:700])
