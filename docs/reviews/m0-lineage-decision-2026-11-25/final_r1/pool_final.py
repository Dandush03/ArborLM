# ruff: noqa
"""Final R1 audit: R-32 pooled excess per lineage (= shape, R-34) and level, over the implementer's primary and replicate runs and this auditor's fresh run.
Classes (R-31): exactly audit 4's final_table4.py classes; its definitions (EXCL, M, GENERIC, CHEAP, bare, cls) are executed from the audit file
itself (the text before 'best = defaultdict'), so nothing is retyped. Feature lookups: C (A if 'family tree'), as final_table4.py.
Pooling: per (lineage, level, source, rule) the item-weighted mean of eff and of anti over the runs that measured it; then excess = max(eff, anti);
a rule that is exact (pooled accuracy on fired >= 0.999 and fired on every item) or an error marker is dropped (as audit 4). The largest counted
(C or A) excess per lineage and level decides: > 0.15 in absolute value -> DROPS (a negative pooled eff of an open-answer rule is not an
exploitable gain and is reported only). The implementer's feature rows are identical in its two runs (same fixed seeds 8300/8400, 8500/8600;
checked byte for byte), so they are counted once.
usage: python pool_final.py <audit4 final_table4.py> <impl run1 dir> <impl run2 dir> <my run dir> <out.json>"""
import glob, json, os, sys
from collections import defaultdict

ft, d1, d2, d3, outp = sys.argv[1:6]
src = open(ft).read()
ns = {}
exec(src[: src.index("best = defaultdict")], ns)
cls0, bare = ns["cls"], ns["bare"]


def cls(h):
    if h.startswith("feat:"):
        return "A" if "family tree" in h else "C"
    return cls0(h)


SURV = ["R1.boolean_lights_r4", "R1.categories_default_exceptions_r4", "R1.compass_turns", "R1.conditional_decision_tree_r6", "R1.conditional_threshold_rule_r4",
        "R1.equivalence_exchange_rates_r6", "R1.graph_shortest_route_r6", "R1.knights_knaves_r6", "R1.spatial_grid_walk_r5", "R1.swap_tracking_r5",
        "R1.temporal_weekday_shift_r6", "R1.venn_counting_r5"]
runs = {"impl_primary": (d1, ("aud", "impl", "feat")), "impl_replicate": (d2, ("aud", "impl")), "auditor_fresh": (d3, ("aud", "impl", "feat"))}
acc = defaultdict(lambda: {"n": 0, "eff": 0.0, "anti": 0.0, "anti_n": 0, "fired": 0, "hit": 0.0, "runs": {}})
for rn, (d, srcs) in runs.items():
    for lid in SURV:
        for s in srcs:
            f = os.path.join(d, f"{lid}.{s}.jsonl")
            for line in open(f):
                if not line.strip():
                    continue
                r = json.loads(line)
                key = (r["lineage"], r["level"], s, r["heuristic"])
                a = acc[key]
                n = r["n"]
                a["n"] += n; a["eff"] += n * r["eff"]
                if r.get("anti") is not None:
                    a["anti"] += n * r["anti"]; a["anti_n"] += n
                a["fired"] += r.get("fired") or 0
                if r.get("acc_fired") is not None:
                    a["hit"] += r["acc_fired"] * r["fired"]
                a["runs"][rn] = {"n": n, "eff": r["eff"], "anti": r.get("anti")}
res = {}
for (lid, lv, s, h), a in sorted(acc.items()):
    if h.endswith("_error") or h.startswith("a4:error") or h == "a3:error":
        continue
    eff = a["eff"] / a["n"]
    anti = a["anti"] / a["anti_n"] if a["anti_n"] else None
    exact = a["fired"] == a["n"] and a["fired"] > 0 and a["hit"] / a["fired"] >= 0.999
    c = cls(h)
    slot = res.setdefault(lid, {}).setdefault(lv, {"C": [], "A": [], "M": [], "EXCL": [], "exact": []})
    exc = max(eff, anti if anti is not None else -9)
    row = {"rule": f"{s}:{bare(h)}", "excess": round(exc, 4), "eff": round(eff, 4), "anti": None if anti is None else round(anti, 4), "n_pooled": a["n"], "per_run": a["runs"]}
    if exact:
        slot["exact"].append(row)
    elif c is None:
        slot["EXCL"].append(row)
    else:
        slot[c].append(row)
out = {"bound": 0.15, "pooling": "item-weighted per rule over impl_primary, impl_replicate, auditor_fresh (feature rows: impl once + auditor)", "lineages": {}}
print(f"{'shape':38s} " + " ".join(f"   L{lv}  " for lv in range(7)) + "  max  rule                                   verdict | M max (not counted)")
for lid in SURV:
    per = {}
    for lv in range(7):
        sl = res[lid][lv]
        best = max(sl["C"] + sl["A"], key=lambda r: r["excess"])
        mbest = max(sl["M"], key=lambda r: r["excess"]) if sl["M"] else {"rule": "", "excess": 0.0}
        xbest = max(sl["EXCL"], key=lambda r: r["excess"]) if sl["EXCL"] else {"rule": "", "excess": 0.0}
        low = min(sl["C"] + sl["A"], key=lambda r: r["eff"])
        top5 = sorted(sl["C"] + sl["A"], key=lambda r: -r["excess"])[:5]
        # per-run counted maxima (for transparency; R-32 decides on the pooled value)
        prun = {}
        for rn in runs:
            vals = [max(r["per_run"][rn]["eff"], r["per_run"][rn]["anti"] if r["per_run"][rn]["anti"] is not None else -9) for r in sl["C"] + sl["A"] if rn in r["per_run"]]
            prun[rn] = round(max(vals), 4) if vals else None
        per[lv] = {"pooled_max_counted": best["excess"], "rule": best["rule"], "class": "C" if best in sl["C"] else "A", "n_pooled": best["n_pooled"],
                   "per_run_max_counted": prun, "top5_counted": [{k: r[k] for k in ("rule", "excess", "eff", "anti", "n_pooled")} for r in top5],
                   "M_max_not_counted": {"rule": mbest["rule"], "excess": mbest["excess"]}, "EXCL_max_not_counted": {"rule": xbest["rule"], "excess": xbest["excess"]},
                   "most_negative_eff_counted": {"rule": low["rule"], "eff": low["eff"], "anti": low["anti"]}}
    lvmax = max(per, key=lambda k: per[k]["pooled_max_counted"])
    m = per[lvmax]
    mm = max(per.values(), key=lambda v: v["M_max_not_counted"]["excess"])["M_max_not_counted"]
    verdict = "DROPS" if any(abs(per[k]["pooled_max_counted"]) > 0.15 for k in per) else "STAYS"
    m_verdict = "would DROP if M counted" if mm["excess"] > 0.15 else ""
    out["lineages"][lid] = {"per_level": per, "largest": {"level": lvmax, "excess": m["pooled_max_counted"], "rule": m["rule"], "class": m["class"]}, "verdict": verdict,
                             "largest_M_not_counted": mm, "verdict_if_M_counted": "DROPS" if max(verdict == "DROPS", mm["excess"] > 0.15) else "STAYS"}
    print(f"{lid:38s} " + " ".join(f"{per[lv]['pooled_max_counted']:+.3f}" for lv in range(7)) + f"  {m['pooled_max_counted']:.3f} L{lvmax} {m['rule'][:36]:36s} {verdict} | {mm['excess']:.3f} {mm['rule']} {m_verdict}")
print()
for lid in SURV:
    print(lid)
    for lv in range(7):
        p = out["lineages"][lid]["per_level"][lv]
        print(f"   L{lv} pooled {p['pooled_max_counted']:+.4f} ({p['class']}) {p['rule']}  n={p['n_pooled']}  per-run {p['per_run_max_counted']}  M {p['M_max_not_counted']['excess']:+.3f} {p['M_max_not_counted']['rule']}  EXCL {p['EXCL_max_not_counted']['excess']:+.3f} {p['EXCL_max_not_counted']['rule']}")
json.dump(out, open(outp, "w"), indent=1, sort_keys=True)
