"""Compare the auditor's rows with pooled_table.json, row by row where both define the same row. Stdlib only.
Usage: python compare.py MY_DIR POOLED_TABLE OUT_JSON"""
import json, sys
from fractions import Fraction as F
from collections import Counter, defaultdict
MY, PT, OUTJ = sys.argv[1], sys.argv[2], sys.argv[3]
mine = [json.loads(l) for l in open(f"{MY}/rows.jsonl")]
theirs = json.load(open(PT))
def fx(d):
    return F(d["fraction"]) if d is not None else None
def key_m(r):
    rd = r["reading"]
    if rd == "k_over_napp-0.5":
        rd = "k_over_napp"
    rule = r["rule"]
    src = r["src"][:-5] if r["src"].endswith(".json") else r["src"]
    if r["unit"].startswith("M1") and rule.endswith(":base(most frequent answer)"):
        rule = "<base>"
    return (r["unit"], src, r["lineage"], r["level"], rule, rd, r.get("shape"), bool(r.get("bracket_stripped")))
def key_t(r):
    rule = r["rule"]
    if r["unit"].startswith("M1") and (rule == "base" or (rule.startswith("base[") and rule.endswith("]"))):
        rule = "<base>"
    return (r["unit"], r["source"], r["lineage"], r["level"], rule, r["reading"], r["shape"], bool(r.get("bracket_stripped")))
M = defaultdict(list); T = defaultdict(list)
for r in mine: M[key_m(r)].append(r)
none_t = [r for r in theirs if r["excess"] is None]
for r in theirs:
    if r["excess"] is not None:
        T[key_t(r)].append(r)
print("their rows with no figure (excess None):", len(none_t), Counter((r["unit"], r["reading"], r["answer_type"], r["items"]) for r in none_t))
only_m = sorted(set(M) - set(T), key=str); only_t = sorted(set(T) - set(M), key=str)
diff_val = []; diff_cnt = []; diff_unc = []; diff_over = []; dup = []
for k in set(M) & set(T):
    if len(M[k]) != 1 or len(T[k]) != 1:
        dup.append([str(k), len(M[k]), len(T[k])]); continue
    a, b = M[k][0], T[k][0]
    ea, eb = F(a["excess"]["fraction"]), fx(b["excess"])
    if ea != eb: diff_val.append([list(k), str(ea), str(eb), a["items"], b["items"]])
    if a["counted"] != b["counted"]: diff_cnt.append([list(k), a["counted"], b["counted"], a["entry"], b.get("class_entry")])
    if F(a["unc"]["fraction"]) != fx(b["rounding_uncertainty"]): diff_unc.append([list(k), a["unc"]["fraction"], b["rounding_uncertainty"]["fraction"]])
    if a["over"] != b["over_bound"]: diff_over.append([list(k), a["over"], b["over_bound"]])
res = {"n_mine": len(mine), "n_theirs": len(theirs), "matched_keys": len(set(M) & set(T)),
       "only_mine": [list(map(str, k)) for k in only_m], "only_theirs": [list(map(str, k)) for k in only_t],
       "value_differences": diff_val, "counted_differences": diff_cnt, "uncertainty_differences": diff_unc,
       "over_bound_differences": diff_over, "duplicate_keys": dup}
json.dump(res, open(OUTJ, "w"), indent=1, default=str)
for k, v in res.items():
    print(k, v if isinstance(v, int) else len(v))
print("only_mine by (unit,src,reading):", Counter((k[0], k[1], k[5]) for k in only_m))
print("only_theirs by (unit,src,reading):", Counter((k[0], k[1], k[5]) for k in only_t))
print("value diffs by (unit,src,reading):", Counter((d[0][0], d[0][1], d[0][5]) for d in diff_val))
print("unc diffs by (unit,src):", Counter((d[0][0], d[0][1], d[1], d[2]) for d in diff_unc))
print("counted diffs:", diff_cnt[:20])
print("over diffs:", diff_over[:20])
