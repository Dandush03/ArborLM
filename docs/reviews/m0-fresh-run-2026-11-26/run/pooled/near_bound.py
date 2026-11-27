import json
O="/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/pooled/"
per=json.load(open(O+"per_lineage.json"))
rows=[]
for lid,v in per.items():
    if v["dropped"]: continue
    best=max(((float(l["largest_counted_abs_excess"]["decimal_12dp"])+float(l["rounding_uncertainty"]["decimal_12dp"]),lv,l["rule"],l.get("unit")) for lv,l in v["levels"].items() if l.get("largest_counted_abs_excess")),default=None)
    rows.append((best[0],lid,best[1],best[2][:50],best[3]))
rows.sort(reverse=True)
print("survivors:",len(rows))
for r in rows[:14]: print("  %.4f %-36s L%s %s @%s"%r)
import collections
b=collections.Counter()
for r in rows:
    b["<0.05" if r[0]<0.05 else "0.05-0.10" if r[0]<0.10 else "0.10-0.13" if r[0]<0.13 else "0.13-0.15"]+=1
print(dict(b))
