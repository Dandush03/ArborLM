# ruff: noqa
"""Final M1 audit: R-32 pooled excess per lineage and level, R-31 classes, verdict at 0.15 two-sided. Standard library only.
Inputs: my fresh run (rules_fresh_n4000.json, N=4000, seed 2611252) and the implementer's raw battery (m1_fix4_battery_raw.json: own 410302, a4 17, a3 5; N=2000 each),
whose every value I recomputed (compare_repro.txt: 3,190 values, 0 differences).
Pooling: item-weighted mean of (rate - base) over every measurement of the SAME rule definition:
  im:X  <- implementer 'own' X (seed 410302) + implementer 'a4' im:X (seed 17) + mine im:X
  a4:X  <- implementer 'a4' a4:X + mine a4:X
  a3:X  <- implementer 'a3' X (seed 5) + mine a3:X
  echo_best_position <- implementer 'own' + implementer 'a3' + mine (same algorithm)
Classes (R-31): NOT COUNTED = the rules in audit 4's short_summary_a4.PROC (read from the file), and the audit-3 rule of the same name and definition for the same lineage
(an extension by name, flagged). COUNTED = every other a3/a4/im rule. NEW = my rules (not pooled; fresh seed only; reported separately).
Verdict: DROPS if at any level a COUNTED rule's pooled |excess| > 0.15, else STAYS."""
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

BOUND = 0.15
fresh = json.load(open(sys.argv[1]))
raw = json.load(open(sys.argv[2]))["raw"]
out_path = sys.argv[3]
src = Path("docs/reviews/m0-lineage-decision-2026-11-25/audit4_m1/short_summary_a4.py").read_text()
tree = ast.parse(src)
PROC = None
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PROC":
        PROC = ast.literal_eval(node.value)
assert PROC


def stem(lid):
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        s = s.removesuffix(suf)
    return s


def bare(k):
    for p in ("im:", "a4:", "a3:"):
        if k.startswith(p):
            return k[len(p):]
    return k


res = {}
for lid in sorted(fresh["results"]):
    st = stem(lid)
    proc = set(PROC.get(st, {}))
    proc_bare = {bare(k) for k in proc}
    per = {}
    for L in range(7):
        acc = defaultdict(lambda: [0.0, 0])  # rule -> [sum N*excess, N]
        mine = fresh["results"][lid][str(L)]
        Nm = mine["N"]
        for k, v in mine["minus_base"].items():
            if k.startswith("new:"):
                continue
            acc[k][0] += Nm * v; acc[k][1] += Nm
        for s_, d in (("own", raw["own"][lid][str(L)]), ("a4", raw["a4"][lid][str(L)]), ("a3", raw["a3"][lid][str(L)])):
            n = d["N"]
            for k, v in d["minus_base"].items():
                if k.endswith("__within_applicable"):
                    continue
                if s_ == "a4":
                    key = k
                elif k.startswith("echo_best_position"):
                    key = "echo_best_position"
                else:
                    key = ("im:" if s_ == "own" else "a3:") + k
                acc[key][0] += n * v; acc[key][1] += n
        pooled = {k: (s / n, n) for k, (s, n) in acc.items()}
        counted, notc = {}, {}
        for k, (v, n) in pooled.items():
            is_proc = k in proc or (k.startswith("a3:") and bare(k) in proc_bare)
            (notc if is_proc else counted)[k] = (round(v, 4), n)
        kc = max(counted, key=lambda k: abs(counted[k][0]))
        kn = max(notc, key=lambda k: abs(notc[k][0])) if notc else None
        newr = {k: v for k, v in mine["minus_base"].items() if k.startswith("new:")}
        knew = max(newr, key=lambda k: abs(newr[k]))
        fresh_only = {k: v for k, v in mine["minus_base"].items() if not k.startswith("new:") and not (k in proc or (k.startswith("a3:") and bare(k) in proc_bare))}
        kf = max(fresh_only, key=lambda k: abs(fresh_only[k]))
        per[str(L)] = {"counted_max_rule": kc, "counted_max_pooled": counted[kc][0], "counted_max_N": counted[kc][1],
                       "fresh_only_max_rule": kf, "fresh_only_max": round(fresh_only[kf], 4),
                       "notcounted_max_rule": kn, "notcounted_max_pooled": notc[kn][0] if kn else None,
                       "new_max_rule": knew, "new_max_fresh": round(newr[knew], 4), "new_all": {k: round(v, 4) for k, v in newr.items()},
                       "base_fresh": mine["base"], "a3_skipped_items_fresh": mine["a3_skipped_items"],
                       "notcounted_all": notc, "extra": {k: mine[k] for k in ("one_op_best", "asked_is_largest_observed_vs_uniform") if k in mine}}
    worst = max(range(7), key=lambda L: abs(per[str(L)]["counted_max_pooled"]))
    wn = [L for L in range(7) if per[str(L)]["notcounted_max_pooled"] is not None]
    wn = max(wn, key=lambda L: abs(per[str(L)]["notcounted_max_pooled"])) if wn else None
    wnew = max(range(7), key=lambda L: abs(per[str(L)]["new_max_fresh"]))
    res[lid] = {"per_level": per, "largest_counted": [per[str(worst)]["counted_max_pooled"], per[str(worst)]["counted_max_rule"], worst],
                "verdict": "DROPS" if any(abs(per[str(L)]["counted_max_pooled"]) > BOUND for L in range(7)) else "STAYS",
                "largest_notcounted": [per[str(wn)]["notcounted_max_pooled"], per[str(wn)]["notcounted_max_rule"], wn] if wn is not None else None,
                "would_drop_if_notcounted_counted": bool(wn is not None and abs(per[str(wn)]["notcounted_max_pooled"]) > BOUND),
                "largest_new": [per[str(wnew)]["new_max_fresh"], per[str(wnew)]["new_max_rule"], wnew],
                "would_drop_on_new": abs(per[str(wnew)]["new_max_fresh"]) > BOUND}
json.dump({"bound": BOUND, "proc_list_source": "audit4_m1/short_summary_a4.py PROC", "results": res}, open(out_path, "w"), indent=1, sort_keys=True)
print("lineage | verdict | largest counted pooled (rule, level) | per-level counted pooled | largest NOT counted (rule, level) | largest NEW fresh (rule, level)")
for lid, r in res.items():
    pl = " ".join(f"{r['per_level'][str(L)]['counted_max_pooled']:+.3f}" for L in range(7))
    lc = r["largest_counted"]; ln = r["largest_notcounted"]; lnw = r["largest_new"]
    print(f"{lid} | {r['verdict']} | {lc[0]:+.3f} ({lc[1]}, L{lc[2]}) | {pl} | " + (f"{ln[0]:+.3f} ({ln[1]}, L{ln[2]})" if ln else "-") + f"{' >0.15' if r['would_drop_if_notcounted_counted'] else ''} | {lnw[0]:+.3f} ({lnw[1]}, L{lnw[2]}){' >0.15' if r['would_drop_on_new'] else ''}")
print("STAYS:", sum(r["verdict"] == "STAYS" for r in res.values()), "DROPS:", [k for k, r in res.items() if r["verdict"] == "DROPS"])
print("would drop if not-counted rules counted:", [k for k, r in res.items() if r["would_drop_if_notcounted_counted"]])
print("would drop on NEW rules:", [k for k, r in res.items() if r["would_drop_on_new"]])
