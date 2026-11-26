# ruff: noqa
"""Final C1 audit (fix 4), step 4: pooled cheap-rule excess per lineage and level (R-31, R-32, R-34), from the RAW outputs of the three rule scripts
on (i) the implementer's draws (audit-4 and audit-3 scripts on gen72 = seed 71, n = 400 per level; the battery at seed 83, n = 400) and (ii) mine
(gen9311, n = 2,000 per level; battery seed 9323, n = 2,000). Stdlib only; reads JSON outputs; imports nothing from studies/.

Measures (open answers: base rate 0, so excess = accuracy). For each measure the pooled estimate is item-weighted: (n1 r1 + n2 r2) / (n1 + n2), with
rule hits recovered as round(share * n) where only a share is stored. A rule absent in one source counts 0 hits there.
CLASS (R-31: counted = what audit 4 counted in its 'bound 0.15' column = cheap, i.e. S + generic + most-frequent-key; closed forms F are counted as drops too):
  a4: EFF_S, MF, MFsh (cheap); per-shape rules S.* and F.* -> share of the level (cheap / closed); M.* and EFF_SM -> partial trace (NOT counted); H.* hazard (NOT counted)
  battery: MF_cv, BEST_generic_cv (cheap); rules C.* control (excluded); rules that run a MUTATED program (BATTERY_MUT, read from c1_fix3_battery.py:
    mut()/regex_run() call sites) -> partial trace (NOT counted under the strict reading; counted by the implementer); other S.*/F.* cheap
  a3: MF_cv, MF_shape_cv, BEST_generic_cv (cheap); S.no_turns, S.no_back, S.no_skips, S.all_ones_start (mutations) -> partial trace; other rules cheap
Two readings are output: STRICT (R-31 as I read it) and IMPLEMENTER (battery mutation rules counted as cheap, as c1_fix4_rules_table.py does).
Also: per-shape (in-shape) rates of a4 rules and MF_in_shape_cv pooled by shape size (R-34: reported, not counted); partial-trace level-wide maxima.
Usage: python3 f4_pool.py IMPL_SCRATCH MY_SCRATCH OUT_JSON
"""
import glob, json, os, sys
from collections import defaultdict

ALIAS = {"C1.sieve_marking_f3": "C1.sieve_marking_f4", "C1.fast_power_f3": "C1.fast_power_f4", "C1.func_branch": "C1.func_branch_f4",
         "C1.func_compose_f3": "C1.func_compose_f4", "C1.slices": "C1.slices_f4"}
BATTERY_MUT = {"S.all_ones_start", "S.no_halving", "S.no_c_term", "S.thr0_run", "S.run_inc_1", "S.naive_copy", "S.no_skips", "S.always_skip", "S.no_turns", "S.no_back", "S.no_mod", "S.ignore_step"}
A3_MUT = {"S.no_turns", "S.no_back", "S.no_skips", "S.all_ones_start"}
BOUND = 0.15


def fid(x):
    return ALIAS.get(x, x)


def load_a4(path):
    d = json.load(open(path))
    return {fid(k): v for k, v in d.items()}


def load_a3(dirp):
    out = {}
    for fn in sorted(glob.glob(os.path.join(dirp, "*.json"))):
        b = os.path.basename(fn)
        if b == "run_log.json":
            continue
        tag, kind = b[:-5].split("__")
        data = json.load(open(fn))
        lid = fid("C1." + tag)
        if lid in out and kind == "own":
            continue
        out[lid] = (kind, data[sorted(data)[0]])
    # prefer alias runs that succeeded; own only when the alias failed (as the runners do)
    log = json.load(open(os.path.join(dirp, "run_log.json")))
    res = {}
    for k, rec in log.items():
        l = fid(k)
        tag = k.replace("C1.", "")
        use = "alias" if rec.get("alias_rc") == 0 else "own"
        fn = os.path.join(dirp, f"{tag}__{use}.json")
        data = json.load(open(fn))
        res[l] = {"kind": use, "per": data[sorted(data)[0]]}
    return res


def measures(a4, bat, a3, lid, lv):
    """{measure: (hits, n, class)}; class in cheap, closed, partial, hazard, control"""
    M = {}
    if a4 and lid in a4:
        p = a4[lid][str(lv)]
        n = p["n"]
        for k in ("EFF_S", "MF", "MFsh"):
            M[f"a4.{k}"] = (p[k] * n, n, "cheap")
        M["a4.EFF_SM"] = (p["EFF_SM"] * n, n, "partial")
        for key, v in p["rules"].items():
            sh, r = key.split("|", 1)
            if r.startswith("MF_in_shape"):
                continue
            c = r.split(".")[0]
            cls = {"S": "cheap", "F": "closed", "M": "partial", "H": "hazard"}.get(c, "other")
            M[f"a4.{key}"] = (round(v["share_of_level"] * n), n, cls)
    if bat and lid in bat:
        p = bat[lid][str(lv)]
        n = p["n"]
        M["battery.MF_cv"] = (p["MF_cv"] * n, n, "cheap")
        M["battery.BEST_generic_cv"] = (p["BEST_generic_cv"] * n, n, "cheap")
        for key, v in p["S"].items():
            sh, r = key.split("|", 1)
            if r.startswith("C."):
                cls = "control"
            elif r in BATTERY_MUT:
                cls = "partial_battery"
            elif r.startswith("F."):
                cls = "closed"
            else:
                cls = "cheap"
            M[f"battery.{key}"] = (v["hit"], n, cls)
    if a3 and lid in a3:
        p = a3[lid]["per"][str(lv)]
        n = p["n"]
        for k in ("MF_cv", "MF_shape_cv", "BEST_generic_cv"):
            M[f"a3.{k}"] = (p[k] * n, n, "cheap")
        for key, v in p["S"].items():
            sh, r = key.split("|", 1)
            cls = "partial" if r in A3_MUT else ("closed" if r.startswith("F.") else "cheap")
            M[f"a3.{key}"] = (v["hit"], n, cls)
    return M


def in_shape(a4, lid, lv):
    out = {}
    if not a4 or lid not in a4:
        return out
    p = a4[lid][str(lv)]
    for key, v in p["rules"].items():
        sh, r = key.split("|", 1)
        c = "MF" if r.startswith("MF_in_shape") else r.split(".")[0]
        if c in ("S", "F", "MF"):
            out[key] = (v["rate_in_shape"] * v["n_shape"], v["n_shape"])
    return out


def main():
    imp, mine, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    src = {"impl": (load_a4(os.path.join(imp, "s5_72.json")), {k: v for k, v in json.load(open(os.path.join(imp, "battery83b.json"))).items()}, load_a3(os.path.join(imp, "a3run72"))),
           "mine": (load_a4(os.path.join(mine, "s5_9311.json")), json.load(open(os.path.join(mine, "battery9323.json"))), load_a3(os.path.join(mine, "a3run9311")))}
    lids = sorted(src["mine"][0])
    res = {}
    for lid in lids:
        per = {}
        for lv in range(7):
            pooled = defaultdict(lambda: [0.0, 0, None])
            each = {}
            for s, (a4, bat, a3) in src.items():
                m = measures(a4, bat, a3, lid, lv)
                each[s] = m
            # union of measures; n per source per script family
            names = sorted(set(each["impl"]) | set(each["mine"]))
            fam_n = {s: {} for s in src}
            for s in src:
                for k, (h, n, c) in each[s].items():
                    fam_n[s][k.split(".")[0]] = n
            rows = {}
            for k in names:
                fam = k.split(".")[0]
                h = n = 0
                cls = None
                parts = {}
                for s in src:
                    nn = fam_n[s].get(fam, 0)
                    if k in each[s]:
                        hh, nn2, cls = each[s][k]
                        parts[s] = round(hh / nn2, 4)
                        h += hh
                        n += nn2
                    else:
                        parts[s] = 0.0 if nn else None
                        n += nn
                rows[k] = {"pooled": round(h / n, 4) if n else None, "n": n, "class": cls, "per_source": parts}
            def best(classes):
                c = [(v["pooled"], k) for k, v in rows.items() if v["class"] in classes and v["pooled"] is not None]
                return max(c) if c else (0.0, None)
            strict = best({"cheap", "closed"})
            impl_reading = best({"cheap", "closed", "partial_battery"})
            partial = best({"cheap", "closed", "partial", "partial_battery"})
            # in-shape
            ish = defaultdict(lambda: [0.0, 0])
            for s, (a4, _, _) in src.items():
                for k, (h, n) in in_shape(a4, lid, lv).items():
                    ish[k][0] += h
                    ish[k][1] += n
            ish_rates = {k: round(h / n, 4) for k, (h, n) in ish.items() if n >= 50}
            top_ish = sorted(((v, k) for k, v in ish_rates.items()), reverse=True)[:3]
            per[lv] = {"strict_max": strict, "implementer_reading_max": impl_reading, "with_partial_trace_max": partial,
                       "in_shape_top3": top_ish, "rows": rows}
        smax = max((per[lv]["strict_max"][0], lv, per[lv]["strict_max"][1]) for lv in range(7))
        imax = max((per[lv]["implementer_reading_max"][0], lv, per[lv]["implementer_reading_max"][1]) for lv in range(7))
        pmax = max((per[lv]["with_partial_trace_max"][0], lv, per[lv]["with_partial_trace_max"][1]) for lv in range(7))
        ishmax = max(((per[lv]["in_shape_top3"][0][0], lv, per[lv]["in_shape_top3"][0][1]) if per[lv]["in_shape_top3"] else (0, lv, None)) for lv in range(7))
        res[lid] = {"strict_max": smax, "implementer_reading_max": imax, "with_partial_trace_max": pmax, "in_shape_max": ishmax,
                    "verdict_strict": "DROPS" if smax[0] > BOUND else "STAYS", "verdict_implementer_reading": "DROPS" if imax[0] > BOUND else "STAYS",
                    "would_drop_if_partial_trace_counted": pmax[0] > BOUND, "levels": per}
        print(f"{lid:30s} strict {smax[0]:.4f} L{smax[1]} {smax[2]} | impl {imax[0]:.4f} | partial {pmax[0]:.4f} L{pmax[1]} {pmax[2]} | in-shape {ishmax[0]:.4f} L{ishmax[1]} {ishmax[2]}")
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
