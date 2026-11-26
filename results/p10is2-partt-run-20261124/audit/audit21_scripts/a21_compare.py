# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21: compare my own recomputation (audit21_out/results/*.json) with the run's registered records, as ADR-0025 section 8.6 requires of the
auditor's own code: every greedy sequence identical, every item score within 1e-6. Standard library only; reads the run directory read-only.

Compared:
  1. item_records.json: every stored record (468), field by field: sequences (exact), items (1e-6), exact flags (exact), texts (exact), flags (exact),
     GEN per-window nll_base / nll_arm (1e-6) with preds and strata (exact). A stored key with no record of mine is a difference.
  2. registry.json: every key (592) against my value: the mean of my item scores, the mean of my exact flags (em:), my GEN loss increase, my
     modification. A missing key on either side is a difference.
  3. combined.json: every record (38): per item C1/C2 ids (exact) and scores (1e-6), pass flags, single sequences (exact) and scores (1e-6); and the
     304 means compared by the frozen recompute (C1/C2 mean, tested by language, single mean by language).
  4. side records: R-exact hit counts (6).
  GEN NLLs and the modification are compared twice: my float32 computation (the model's precision) and my float64 computation of the same logits /
  values. Both outcomes are printed; neither is dropped.

Usage: python3 -I a21_compare.py  -> prints the summary and writes audit21_out/compare_<UTC>.json (a new file each run)."""
import glob
import json
import math
import time
from pathlib import Path

RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit21_out")
TOL = 1e-6
sys_path = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(sys_path))
from a21_driver import tasks as all_tasks  # the task list only (stdlib)


def fmean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else float("nan")


def pm(vals, strata):
    ms = [fmean([v for v, s in zip(vals, strata) if s == n]) for n in ("marker", "ordinary") if n in strata]
    return math.fsum(ms) / len(ms)


def main():
    stored = json.loads((RUN / "item_records.json").read_text())["items"]
    registry = json.loads((RUN / "registry.json").read_text())
    comb = json.loads((RUN / "combined.json").read_text())["combined"]
    side = json.loads((RUN / "side_records.json").read_text())["side"]
    expected = all_tasks()
    mine_recs, mine_vals, mine_extra, comb_mine, missing_tasks, seconds = {}, {}, {}, {}, [], 0.0
    for t in expected:
        f = OUT / "results" / (t.replace("|", "__").replace("@", "_at_") + ".json")
        if not Path(str(f) + ".done").exists():
            missing_tasks.append(t)
            continue
        d = json.loads(f.read_text())
        seconds += d["seconds"]
        for k, v in d["records"].items():
            assert k not in mine_recs, k
            mine_recs[k] = v
        mine_vals.update(d["values"])
        if "combined" in d["extra"]:
            comb_mine[d["extra"]["combined_key"]] = d["extra"]["combined"]
        if "S0" in d["extra"]:
            comb_mine["S0"] = d["extra"]["S0"]
            comb_mine["ensemble"] = d["extra"]["ensemble"]
        if "modification_f64" in d["extra"]:
            mine_extra[t] = d["extra"]
    diffs, notes = [], []
    counts = {"item_records_stored": len(stored), "item_records_compared": 0, "sequences_compared": 0, "item_scores_compared": 0, "exact_flags_compared": 0,
              "texts_compared": 0, "edit1_flags_compared": 0, "gen_windows_compared": 0, "registry_keys": len(registry), "registry_compared": 0,
              "combined_records_stored": len(comb), "combined_records_compared": 0, "combined_item_ids_compared": 0, "combined_item_scores_compared": 0,
              "combined_single_sequences_compared": 0, "combined_means_compared": 0, "rexact_hits_compared": 0}
    f64 = {"gen_window_max": 0.0, "gen_window_over_tol": 0, "gen_value_max": 0.0, "modification_max": 0.0, "modification_over_tol": 0}
    maxima = {"item_score": 0.0, "gen_nll_f32": 0.0, "registry": 0.0, "combined_score": 0.0, "combined_mean": 0.0}

    # 1. item records
    for k, s in sorted(stored.items()):
        m = mine_recs.get(k)
        if m is None:
            diffs.append({"where": "item_records", "key": k, "why": "no record of mine"})
            continue
        counts["item_records_compared"] += 1
        if "gen" in s:
            g, h = s["gen"], m["gen"]
            if g["preds"] != h["preds"] or g["strata"] != h["strata"]:
                diffs.append({"where": "item_records", "key": k, "field": "gen preds/strata", "stored": [g["preds"], g["strata"]], "mine": [h["preds"], h["strata"]]})
            for fld in ("nll_base", "nll_arm"):
                if len(g[fld]) != len(h[fld]):
                    diffs.append({"where": "item_records", "key": k, "field": fld, "why": "length"})
                    continue
                for i, (a, b) in enumerate(zip(g[fld], h[fld])):
                    dd = abs(a - b)
                    maxima["gen_nll_f32"] = max(maxima["gen_nll_f32"], dd)
                    if dd > TOL:
                        diffs.append({"where": "item_records", "key": k, "field": fld, "window": i, "stored": a, "mine_f32": b, "diff": dd})
                    d64 = abs(a - h[fld + "_f64"][i])
                    f64["gen_window_max"] = max(f64["gen_window_max"], d64)
                    f64["gen_window_over_tol"] += d64 > TOL
            counts["gen_windows_compared"] += len(g["nll_base"])
            continue
        if "flags" in s:
            counts["edit1_flags_compared"] += len(s["flags"])
            if s["flags"] != m.get("flags"):
                bad = [i for i, (a, b) in enumerate(zip(s["flags"], m.get("flags", []))) if a != b]
                diffs.append({"where": "item_records", "key": k, "field": "flags", "items": bad[:50], "count": len(bad), "len": [len(s["flags"]), len(m.get("flags", []))]})
            continue
        n = len(s["items"])
        if len(m.get("items", [])) != n:
            diffs.append({"where": "item_records", "key": k, "why": "item count", "stored": n, "mine": len(m.get("items", []))})
            continue
        for i in range(n):
            dd = abs(s["items"][i] - m["items"][i])
            maxima["item_score"] = max(maxima["item_score"], dd)
            if dd > TOL:
                diffs.append({"where": "item_records", "key": k, "item": i, "field": "items", "stored": s["items"][i], "mine": m["items"][i], "diff": dd})
        counts["item_scores_compared"] += n
        if "sequences" in s:
            for i in range(n):
                if s["sequences"][i] != m["sequences"][i]:
                    diffs.append({"where": "item_records", "key": k, "item": i, "field": "sequences", "stored": s["sequences"][i], "mine": m["sequences"][i]})
            counts["sequences_compared"] += n
        if "exact" in s:
            for i in range(n):
                if s["exact"][i] != m["exact"][i]:
                    diffs.append({"where": "item_records", "key": k, "item": i, "field": "exact", "stored": s["exact"][i], "mine": m["exact"][i]})
            counts["exact_flags_compared"] += n
        if "texts" in s:
            for i in range(n):
                if s["texts"][i] != m["texts"][i]:
                    diffs.append({"where": "item_records", "key": k, "item": i, "field": "texts", "stored": s["texts"][i], "mine": m["texts"][i]})
            counts["texts_compared"] += n
    extra_mine = sorted(set(mine_recs) - set(stored))

    # 2. registry
    mine_reg = {}
    for k, m in mine_recs.items():
        if "gen" in m:
            mine_reg[k] = pm(m["gen"]["nll_arm"], m["gen"]["strata"]) - pm(m["gen"]["nll_base"], m["gen"]["strata"])
            v64 = pm(m["gen"]["nll_arm_f64"], m["gen"]["strata"]) - pm(m["gen"]["nll_base_f64"], m["gen"]["strata"])
            if k in registry:
                f64["gen_value_max"] = max(f64["gen_value_max"], abs(v64 - registry[k]))
            continue
        if "items" in m:
            mine_reg[k] = fmean(m["items"])
            pre, read = k.rsplit("|", 1)
            if read.startswith("s:") and "exact" in m:
                mine_reg[f"{pre}|em:{read[2:]}"] = fmean(1.0 if x else 0.0 for x in m["exact"])
    for k, v in mine_vals.items():
        if "|hits:" not in k:
            mine_reg[k] = v
    for t, e in mine_extra.items():
        _, r, o, a = t.split("|")
        key = f"M-ii|{o}|{r}|modification"
        dd = abs(e["modification_f64"] - registry[key])
        f64["modification_max"] = max(f64["modification_max"], dd)
        f64["modification_over_tol"] += dd > TOL
        notes.append({"modification": key, "registered": registry[key], "mine_f32": mine_vals.get(key), "mine_f64": e["modification_f64"], "rows_changed_share_mine": e["modification_rows_changed_share"]})
    for k in sorted(set(registry) | set(mine_reg)):
        a, b = registry.get(k), mine_reg.get(k)
        if k not in registry:
            continue  # my extra reads (E-table em, etc.) are listed below, not compared
        if b is None:
            diffs.append({"where": "registry", "key": k, "why": "no value of mine", "registered": a})
            continue
        counts["registry_compared"] += 1
        dd = abs(a - b)
        maxima["registry"] = max(maxima["registry"], dd)
        if not (math.isfinite(a) and math.isfinite(b)) or dd > TOL:
            diffs.append({"where": "registry", "key": k, "registered": a, "mine": b, "diff": dd})
    reg_extra = sorted(set(mine_reg) - set(registry))

    # 3. combined
    def cmp_kind(name, kind, s, m):
        if "items" in m:
            for it in m["items"]:
                si = s["items"][it["j"]]
                if si["ids"] != it["ids"]:
                    diffs.append({"where": "combined", "key": name, "kind": kind, "item": it["j"], "field": "ids", "stored": si["ids"], "mine": it["ids"]})
                if si.get("pass") is not None and si["pass"] != it["pass"]:
                    diffs.append({"where": "combined", "key": name, "kind": kind, "item": it["j"], "field": "pass", "stored": si["pass"], "mine": it["pass"]})
                for a, b in zip(si["scores"], it["scores"]):
                    dd = abs(a - b)
                    maxima["combined_score"] = max(maxima["combined_score"], dd)
                    if dd > TOL:
                        diffs.append({"where": "combined", "key": name, "kind": kind, "item": it["j"], "field": "scores", "stored": si["scores"], "mine": it["scores"]})
                counts["combined_item_ids_compared"] += 2
                counts["combined_item_scores_compared"] += 2
            if len(m["items"]) != len(s["items"]):
                diffs.append({"where": "combined", "key": name, "kind": kind, "why": "item count", "stored": len(s["items"]), "mine": len(m["items"])})

    def means(rec):
        out = {}
        for kind in ("C1", "C2"):
            out[f"{kind}|mean"] = rec[kind]["mean"]
            for lang in ("A", "B"):
                v = rec[kind]["tested_by_language"].get(lang)
                if v is not None:
                    out[f"{kind}|tested|{lang}"] = v
        for lang in ("A", "B"):
            sc = rec["single"]["scores"][lang]
            out[f"single|{lang}"] = fmean(sc)
        return out

    for name, s in sorted(comb.items()):
        m = comb_mine.get(name)
        if m is None:
            diffs.append({"where": "combined", "key": name, "why": "no record of mine"})
            continue
        counts["combined_records_compared"] += 1
        for kind in ("C1", "C2"):
            cmp_kind(name, kind, s[kind], m[kind])
        if "sequences" in s["single"]:
            for lang in ("A", "B"):
                for i, (a, b) in enumerate(zip(s["single"]["sequences"][lang], m["single"]["sequences"][lang])):
                    if a != b:
                        diffs.append({"where": "combined", "key": name, "field": f"single sequence {lang}", "item": i, "stored": a, "mine": b})
                counts["combined_single_sequences_compared"] += len(s["single"]["sequences"][lang])
            if s["single"].get("separate_answers") != m["single"].get("separate_answers"):
                diffs.append({"where": "combined", "key": name, "field": "separate_answers", "stored": s["single"].get("separate_answers"), "mine": m["single"].get("separate_answers")})
        for lang in ("A", "B"):
            for i, (a, b) in enumerate(zip(s["single"]["scores"][lang], m["single"]["scores"][lang])):
                if abs(a - b) > TOL:
                    diffs.append({"where": "combined", "key": name, "field": f"single score {lang}", "item": i, "stored": a, "mine": b})
        ms, mm = means(s), means(m)
        for k in sorted(set(ms) | set(mm)):
            a, b = ms.get(k), mm.get(k)
            if a is None or b is None:
                diffs.append({"where": "combined means", "key": f"{name}|{k}", "why": "missing on one side", "stored": a, "mine": b})
                continue
            counts["combined_means_compared"] += 1
            dd = abs(a - b)
            maxima["combined_mean"] = max(maxima["combined_mean"], dd)
            if dd > TOL:
                diffs.append({"where": "combined means", "key": f"{name}|{k}", "stored": a, "mine": b, "diff": dd})

    # 4. R-exact hits (side records) and the M-ii D_con rejection, from my own values
    for r in range(3):
        for n in ("E_A", "E_B"):
            k = f"R-exact|-|{r}|hits:{n}"
            if k in mine_vals:
                counts["rexact_hits_compared"] += 1
                if mine_vals[k] != side[f"r{r}/R-exact-hits"][f"hits:{n}"]:
                    diffs.append({"where": "side", "key": k, "stored": side[f"r{r}/R-exact-hits"][f"hits:{n}"], "mine": mine_vals[k]})
    rejected = []
    for r in range(3):
        for o in ("AB", "BA"):
            try:
                if any(mine_reg[f"M-ii|{o}|{r}|dcon:{c}"] < mine_reg[f"M-append|{o}|{r}|dcon:{c}"] - 0.02 for c in ("A", "B")):
                    rejected.append(f"{o}|{r}")
            except KeyError:
                rejected.append(f"{o}|{r}: not computable")
    summary = {"utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "tolerance": TOL, "tasks_expected": len(expected), "tasks_missing": missing_tasks,
               "task_seconds_sum": seconds, "counts": counts, "maxima_abs_diff": maxima, "float64_variant": f64, "differences": len(diffs),
               "m_ii_rejected_by_my_dcon": rejected, "mine_not_stored_item_keys": extra_mine, "mine_not_in_registry": reg_extra, "notes": notes}
    verdict = "INCOMPLETE" if missing_tasks else ("RECOMPUTATION AGREES" if not diffs else "ENGINEERING STOP — RECOMPUTATION")
    summary["verdict_float32_variant"] = verdict
    path = OUT / f"compare_{summary['utc']}.json"
    with open(path, "x") as f:
        json.dump({**summary, "difference_list": diffs}, f, indent=1)
    print(json.dumps(summary, indent=1))
    for dd in diffs[:40]:
        print("DIFF", json.dumps(dd)[:400])
    print("written", path)
    print("VERDICT (float32 GEN NLL and modification; float64 variant above):", verdict)


if __name__ == "__main__":
    main()
