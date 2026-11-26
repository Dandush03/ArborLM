# ruff: noqa
"""Final R2 audit: pooled shortcut effects (R-32) per lineage and level, classes per R-31.
Inputs: my fresh-seed counts (f_rules_4000.json, and optionally a NEW-rule file) and the implementer's two seed sets
(bat_a4_2000.json, bat_f4_2000.json; crt_smallest taken from bat_*_2000_crt.json, which hold the repaired crt shape).
Pooling: per (lineage, level, shape, rule) the counts k, napp and the shape's item count n are SUMMED over the seed sets (item-weighted).
A rule absent from a seed set's file (the implementer's harness omits rules that never apply) contributes k = 0, napp = 0, n = that set's n.
Effect (audit 4's definition, a4_shortcuts.py/a4_summ2.py): open answers -> k/n (rule's None = wrong), '[cond]' rules -> k/napp;
yes/no -> |k/napp - 0.5|. Classes: audit 4's klass() (a4_summ2.py), re-typed below. R-31: for R2 the lead's 'bound 0.15' column
(LEAD_RULINGS_4 table: R2 15/20/24) is audit 4's 'cues only' row, so only class 'cue' is counted; partial, construct, P, artifact are reported.
Two units are reported: per shape (max over the question shapes, as audit 4's harness measured) and all shapes together (R-34 literal:
the rule's counts summed over the lineage's shapes of one answer type).
Usage: python3 -I f_pool.py MINE.json IMPL_DIR OUT.json [NEW.json]"""
import json, math, sys

MINE, IMPL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NEWF = sys.argv[4] if len(sys.argv) > 4 else None
BOUND = 0.15

MISREAD = [
    "[a3] digits read right to left", "[a3] k-th largest", "[a3] syndrome read with the bits reversed", "[a3] doubling the other parity",
    "[a3] check digit: payload total without the new digit", "[mine] check digit: payload's own last digit not doubled",
    "[a3] first occurrence only per rule", "[a3] largest: largest prime <= sqrt(n) dividing n", "[a3] (b-a)//m + 1",
    "[mine] latest start first", "[mine] Floyd bottom-up heapify", "[mine] inverse mapping t times",
]
PARTIAL = [
    "letter pairs", "[a3] outer two letters each side match", "[a3] first letter equals last letter",
    "centres only", "[a3] longest odd palindrome only", "[a3] longest even palindrome only", "longest palindrome of length <= 7",
    "scanning only primes up to 61", "first failing check", "plain digit sum",
    "count of piles that are a win alone is odd", "odd number of piles that are first-player wins alone", "[cond] ignore",
]
CONSTRUCT = ["t mod (n-1) applications", "t mod 10 applications"]


def klass(hn, sh, lv):
    if "(P" in hn:
        return "P"
    if hn in ("[a3] ignore reverses", "[a3] ignore moves to the end"):
        return "artifact"
    if hn == "[a3] removal by deleting the minimum and keeping the order of the rest" and sh == "removals=0":
        return "artifact"
    if hn in ("[a3] only the first rule", "[a3] only the last rule, on the start string", "[a3] rules in reverse order") and lv == 0:
        return "artifact"
    if hn == "[a3] rules in reverse order" or hn == "[mine] [cond] rules in reverse order" or hn == "[mine] [cond] all rules applied to the start string at once (left to right, first matching rule)":
        return "P"
    if any(hn.startswith(m) for m in MISREAD):
        return "P"
    if any(p in hn for p in PARTIAL):
        return "partial"
    if any(c in hn for c in CONSTRUCT):
        return "construct"
    return "cue"


def load(path):
    return json.load(open(path))["lineages"]


mine = load(MINE)
a4 = load(f"{IMPL}/bat_a4_2000.json")
f4 = load(f"{IMPL}/bat_f4_2000.json")
a4.update(load(f"{IMPL}/bat_a4_2000_crt.json"))
f4.update(load(f"{IMPL}/bat_f4_2000_crt.json"))
SETS = {"impl_a4": a4, "impl_f4": f4, "final": mine}
if NEWF:
    new = load(NEWF)


def eff(hn, at, k, napp, n):
    if at == "yn":
        return abs(k / napp - 0.5) if napp else 0.0
    if "[cond]" in hn:
        return k / napp if napp else 0.0
    return k / n


def se(hn, at, k, napp, n):
    m = napp if (at == "yn" or "[cond]" in hn) else n
    if not m:
        return 0.0
    p = k / m
    return math.sqrt(p * (1 - p) / m)


out = {}
for lid in sorted(mine):
    per_level = {}
    for lv in sorted(mine[lid], key=int):
        L = int(lv)
        shapes = sorted(set().union(*(SETS[s][lid][lv].keys() for s in SETS)))
        pooled = {}  # (shape, rule) -> dict
        for sh in shapes:
            ats = {SETS[s][lid][lv][sh]["answer_type"] for s in SETS if sh in SETS[s][lid][lv]}
            assert len(ats) == 1, (lid, lv, sh, ats)
            at = ats.pop()
            rules = sorted(set().union(*(SETS[s][lid][lv][sh]["rules"].keys() for s in SETS if sh in SETS[s][lid][lv])))
            for hn in rules:
                tot = {"k": 0, "napp": 0, "n": 0}
                by = {}
                for s in SETS:
                    ent = SETS[s][lid][lv].get(sh)
                    if ent is None:
                        continue
                    v = ent["rules"].get(hn, {"k": 0, "napp": 0})
                    tot["k"] += v["k"]; tot["napp"] += v["napp"]; tot["n"] += ent["n"]
                    by[s] = round(eff(hn, at, v["k"], v["napp"], ent["n"]), 4)
                pooled[(sh, hn)] = {"at": at, "class": klass(hn, sh, L), **tot, "effect": eff(hn, at, tot["k"], tot["napp"], tot["n"]),
                                    "se": se(hn, at, tot["k"], tot["napp"], tot["n"]), "by_set": by}
        # NEW rules (my fresh seeds only)
        newrows = []
        if NEWF and lid in new:
            for sh, ent in new[lid][lv].items():
                for hn, v in ent["rules"].items():
                    if not hn.startswith("[NEW]"):
                        continue
                    newrows.append({"shape": sh, "rule": hn, "effect": round(eff(hn, ent["answer_type"], v["k"], v["napp"], ent["n"]), 4), "n": ent["n"], "napp": v["napp"]})
        # per-shape reading
        best = {}
        for (sh, hn), v in pooled.items():
            c = v["class"]
            if c not in best or v["effect"] > best[c]["effect"]:
                best[c] = {"effect": round(v["effect"], 4), "se": round(v["se"], 4), "rule": hn, "shape": sh, "n": v["n"], "by_set": v["by_set"]}
        # all-shapes-together reading (R-34 literal), per answer type
        agg = {}
        for (sh, hn), v in pooled.items():
            a = agg.setdefault((v["at"], hn), {"k": 0, "napp": 0, "n": 0, "class": v["class"]})
            a["k"] += v["k"]; a["napp"] += v["napp"]; a["n"] += v["n"]
        best_all = {}
        for (at, hn), a in agg.items():
            e = eff(hn, at, a["k"], a["napp"], a["n"])
            c = a["class"]
            if c not in best_all or e > best_all[c]["effect"]:
                best_all[c] = {"effect": round(e, 4), "rule": hn, "answer_type": at, "n": a["n"]}
        per_level[lv] = {"per_shape": best, "all_shapes": best_all, "new": sorted(newrows, key=lambda x: -x["effect"])[:5],
                         "n_items_pooled": sum(SETS[s][lid][lv][sh]["n"] for s in SETS for sh in SETS[s][lid][lv])}
    cue_max = max(per_level.values(), key=lambda x: x["per_shape"].get("cue", {"effect": 0})["effect"])
    lvmax = max(per_level, key=lambda lv: per_level[lv]["per_shape"].get("cue", {"effect": 0})["effect"])
    res = {"levels": per_level}
    res["max_cue_per_shape"] = {"level": int(lvmax), **per_level[lvmax]["per_shape"]["cue"]}
    lvmax2 = max(per_level, key=lambda lv: per_level[lv]["all_shapes"].get("cue", {"effect": 0})["effect"])
    res["max_cue_all_shapes"] = {"level": int(lvmax2), **per_level[lvmax2]["all_shapes"]["cue"]}
    res["verdict_cue_per_shape"] = "STAYS" if res["max_cue_per_shape"]["effect"] <= BOUND else "DROPS"
    res["verdict_cue_all_shapes"] = "STAYS" if res["max_cue_all_shapes"]["effect"] <= BOUND else "DROPS"
    for c in ("partial", "construct", "P", "artifact"):
        vals = [(per_level[lv]["per_shape"][c]["effect"], int(lv), per_level[lv]["per_shape"][c]["rule"]) for lv in per_level if c in per_level[lv]["per_shape"]]
        res[f"max_{c}"] = max(vals) if vals else None
    nv = [(r["effect"], int(lv), r["rule"]) for lv in per_level for r in per_level[lv]["new"]]
    res["max_new"] = max(nv) if nv else None
    out[lid] = res

json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
print(f"{'lineage':30s} {'cue/shape':>9s} L  {'cue/all':>8s}  verdict   partial  construct  P      artifact  NEW   | top cue rule")
for lid, r in out.items():
    m = r["max_cue_per_shape"]
    f = lambda x: f"{x[0]:.3f}" if x else "  -  "
    print(f"{lid[3:]:30s} {m['effect']:9.4f} {m['level']}  {r['max_cue_all_shapes']['effect']:8.4f}  {r['verdict_cue_per_shape']:7s}  {f(r['max_partial']):7s}  {f(r['max_construct']):7s}  {f(r['max_P']):5s}  {f(r['max_artifact']):7s}  {f(r['max_new']):5s} | {m['rule'][:60]} [{m['shape']}] se={m['se']} by_set={m['by_set']}")
print("\nWould drop if a non-counted class counted (per-shape, pooled, > 0.15):")
for c in ("partial", "construct", "P", "artifact"):
    print(f"  {c}: " + ", ".join(f"{lid[3:]} {r[f'max_{c}'][0]:.3f} (L{r[f'max_{c}'][1]}: {r[f'max_{c}'][2][:50]})" for lid, r in out.items() if r[f"max_{c}"] and r[f"max_{c}"][0] > BOUND))
if NEWF:
    print("  NEW (my fresh seeds only): " + ", ".join(f"{lid[3:]} {r['max_new'][0]:.3f} (L{r['max_new'][1]}: {r['max_new'][2]})" for lid, r in out.items() if r["max_new"] and r["max_new"][0] > BOUND))
