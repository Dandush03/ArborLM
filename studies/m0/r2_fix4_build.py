# ruff: noqa: E501
"""R2 fix round 4: builds ``manifests/r2_fix4_survivors.json`` from the recorded measurements (battery JSONs, levels JSONs, capacity JSONs; paths and sha256 are written into the manifest).

Decision rules (the lead's brief and ``LEAD_RULINGS_5.md``): a lineage is NOT_REGISTERED if (1) at any level, on either seed set, a rule of class cue, partial or construct (``r2_fix4_battery.klass``) is more than ``BOUND`` = 0.15 above its base
rate (open answers: accuracy, base rate 0; yes/no: |accuracy - 0.5|); (2) it carries an audit-4 defect outside the allowed repairs (``DEFECTS``); (3) its levels are not distinct after the allowed repair (``r2_fix4_levels``); or
(4) it fails capacity against ``core.generate_pool`` as written at the demand of the final G (R-28; a lineage that passes only under a per-cluster builder is NOT_REGISTERED and flagged). Nothing is registered by this file.
Usage: ``python -m studies.m0.r2_fix4_build --bat a4=F1.json,F1c.json --bat f4=F2.json,F2c.json --levels L1.json,L2.json --cap C.json[,C2.json] --out OUT.json``."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from studies.m0.r2_fix4_battery import worst

BOUND = 0.15
REPAIRED = {
    "R2.count_divisible": "(b) wording: the question now says every entry counts each time it appears (audit 4 s2: the set-of-values reading changed the key on 0.27-0.38 of items)",
    "R2.caesar_shift": "(c) levels: 1 + level words (was 1 + level // 2: levels 0/1, 2/3, 4/5 identical)",
    "R2.cheapest_network": "(c) levels: 8 + level towns (was 8 + level // 2)",
    "R2.interval_scheduling": "(c) levels: 5 + level blocks (was 5 + level // 2)",
    "R2.expression_eval": "(c) levels: 3 + level (+0/1) terms or 4 + level (+0/1) numbers (was level // 2)",
    "R2.crt_smallest": "(c) levels: moduli from range(3 + 5*level, 30 + 10*level) (was range(3, 30 + 10*level): levels 0-2 and 3-6 hardly differ)",
}
# audit-4 defects outside the allowed repairs (R-25), by lineage: (reason text with the audit reference)
DEFECTS = {
    "R2.subtraction_game": "audit 4 s3: rejection sampling on the answer value (until(800, make, ok) on the yes/no key) = R-18 (the earlier acceptance as 'balancing' is withdrawn); not needed for well-posedness; construction of positions would be a new shape (R-25).",
    "R2.multiples_between": "audit 4 s4/s5/s8: with both ends multiples of m the floor counting step collapsed into (b - a)/m + 1 (the registered procedure lost its step); restoring it means random ends, whose end-offset cue read 0.87-0.89 in audit 3: not a wording repair, so dropped (R-25).",
}
AUDIT4 = {
    "R2.gcd_euclid": "audit 4 s4 new rule 1 (gcd from the common powers of 2, 3, 5, 7: 0.91-0.62, created by the round-3 fix); named in the brief",
    "R2.max_subarray_sum": "audit 4 s4 new rule 2 (cut at two adjacent negatives: 0.46-0.29); named in the brief",
    "R2.count_letter": "audit 4 s4 new rule 3 (words containing the letter + 1: 0.31-0.16); named in the brief",
    "R2.permutation_power": "audit 4 s4 new rule 4 (t mod (n-1) applications: 1.00 at levels 0 and 6; 61-666 label-free items); named in the brief",
    "R2.cache_eviction": "audit 4 s4 new rule 5 (last cap distinct names, FIFO contents: 0.37-0.14); named in the brief",
    "R2.coin_change_min": "audit 4 s4 new rule 6 (largest coin k, k-1, k-2 times, greedy for the rest: 0.32-0.16); named in the brief",
    "R2.palindrome_check": "audit 4 s4 new rule 7 (partial pair checks 0.46, halves with the same letters 0.29); named in the brief",
    "R2.kth_smallest": "audit 4 s4 (untouched lineage: value nearest to the quantile 0.58); named in the brief",
    "R2.merge_smallest_cost": "audit 4 s4 (untouched lineage: pairwise rounds in sorted order 0.72); named in the brief",
    "R2.lcs_length": "audit 4 s4 (greedy matching from both ends 0.27 at level 0)",
    "R2.bst_traversal": "audit 4 s4 (root, then the smaller, then the larger, in insertion order: 0.31)",
    "R2.stack_machine": "audit 4 s4 (last operation applied to the last two pushed values 0.22)",
    "R2.bracket_match": "audit 4 s4 (first_error: first closer whose kind differs 0.19)",
    "R2.hash_probe": "audit 4 s4 (checksum: slots filled contiguously from the lowest home 0.154 at level 0); audit 4 also notes the checksum does not depend on insertion order",
    "R2.lis_length": "audit 4 s4 (untouched lineage: ascents + 1 0.38)",
    "R2.modular_power": "audit 4 s4 (untouched lineage: a^(e mod 10) mod m 0.38)",
    "R2.longest_palindromic_substring": "audit 4 s4 (untouched lineage: odd centres only 0.54, a half procedure; most frequent answer 0.165)",
    "R2.hamming_error_position": "audit 4 s4 (partial: first failing check position only 0.22)",
    "R2.prime_factor_query": "audit 4 s4 (partial: scanning only primes up to 61, 0.74; audit 3 s-summary: PENDING)",
}
# lineages whose shortcut verdict depends on counting the auditor's 'partial' class (truncated procedures)
PARTIAL_ONLY = {"R2.hamming_error_position", "R2.prime_factor_query"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_bat(spec: str) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    merged: dict[str, Any] = {}
    files = []
    for f in spec.split(","):
        d = json.loads(Path(f).read_text())
        merged.update(d["lineages"])
        files.append((f, sha(Path(f))))
    return {"lineages": merged}, files


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def main() -> None:
    from studies.m0.r2_fix3_clusters import clusters
    from studies.m0.r2_fix4_set import fix4_set

    ap = argparse.ArgumentParser()
    ap.add_argument("--bat", action="append", required=True)
    ap.add_argument("--levels", required=True)
    ap.add_argument("--cap", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cap-extra", default="", help="capacity files at other G, reported only (e.g. G = 8)")
    ap.add_argument("--cap-superseded", default="", help="capacity file at the superseded whole-evaluation G = 18")
    a = ap.parse_args()
    inputs: dict[str, Any] = {}
    worst_by: dict[str, dict[str, Any]] = {}
    for spec in a.bat:
        tag, files = spec.split("=", 1)
        d, fl = load_bat(files)
        worst_by[tag] = worst(d)
        inputs[f"battery_{tag}"] = [{"path": f, "sha256": h} for f, h in fl]
    levels: dict[str, Any] = {}
    inputs["levels"] = []
    for f in a.levels.split(","):
        levels.update(json.loads(Path(f).read_text()))
        inputs["levels"].append({"path": f, "sha256": sha(Path(f))})
    cap: dict[str, Any] = {}
    inputs["capacity"] = []
    g_cap = None
    for f in a.cap.split(","):
        d = json.loads(Path(f).read_text())
        cap.update(d["lineages"])
        g_cap = d["g"]
        inputs["capacity"].append({"path": f, "sha256": sha(Path(f)), "g": d["g"], "demand": d["demand"]})
    extra: dict[str, Any] = {}
    for f in [x for x in a.cap_extra.split(",") if x]:
        d = json.loads(Path(f).read_text())
        extra[f"G={d['g']}"] = {"path": f, "sha256": sha(Path(f)), "demand": d["demand"], "supplied": {k: [v["supplied"][str(lv)] for lv in range(7)] for k, v in sorted(d["lineages"].items())}}
    sup_old: dict[str, Any] = {}
    for f in [x for x in a.cap_superseded.split(",") if x]:
        d = json.loads(Path(f).read_text())
        sup_old = {"status": "SUPERSEDED (G = 18 was the whole evaluation, not per part; lead's correction)", "path": f, "sha256": sha(Path(f)), "g": d["g"], "demand": d["demand"], "supplied": {k: [v["supplied"][str(lv)] for lv in range(7)] for k, v in sorted(d["lineages"].items())}}
    ids = sorted(fix4_set())
    cl = clusters()
    cl_of = {m: k for k, v in cl.items() for m in v}
    out_l: dict[str, Any] = {}
    for lid in ids:
        name = lid.split(".", 1)[1]
        per_level: dict[str, Any] = {}
        mx = (0.0, "", "", "")
        for lv in range(7):
            best = None
            for tag in sorted(worst_by):
                w = worst_by[tag][lid][str(lv)]
                if best is None or w["max_counted"] > best["largest_abs_excess"]:
                    best = {"largest_abs_excess": w["max_counted"], "rule": w["rule"], "class": w["class"], "shape": w["shape"], "seed_set": tag}
            assert best is not None
            best["by_seed_set"] = {tag: worst_by[tag][lid][str(lv)]["max_counted"] for tag in sorted(worst_by)}
            nc = max((worst_by[t][lid][str(lv)] for t in sorted(worst_by)), key=lambda w: w["max_not_counted"])
            best["largest_not_counted_P_or_artifact"] = nc["max_not_counted"]
            best["not_counted_rule"] = nc["not_counted_rule"]
            best["not_counted_class"] = nc["not_counted_class"]
            per_level[str(lv)] = best
            if best["largest_abs_excess"] > mx[0]:
                mx = (best["largest_abs_excess"], best["rule"], str(lv), best["seed_set"])
        reasons: list[str] = []
        over = [lv for lv, v in per_level.items() if v["largest_abs_excess"] > BOUND]
        if over:
            reasons.append(f"shortcut: {mx[1]!r} reads {mx[0]:.3f} at level {mx[2]} (seed set {mx[3]}), above 0.15 at levels {', '.join('L' + x for x in over)} (R-24); {AUDIT4.get(lid, '')}".strip())
        if lid in DEFECTS:
            reasons.append(DEFECTS[lid])
        lv_res = levels.get(name)
        if lv_res is not None and not lv_res["levels_distinct"]:
            bad = [p["pair"] for p in lv_res["pairs"] if not (p["distinct"] and p["param_rises"])]
            reasons.append(f"levels not distinct (r2_fix4_levels): pairs {', '.join(bad)} (R-21); no repair for a lineage that does not otherwise survive, or one that needs a new procedure (R-25(c))")
        rec: dict[str, Any] = {
            "name": name,
            "id": lid,
            "strict_cluster": cl_of[lid],
            "repair": REPAIRED.get(lid),
            "per_level_largest_abs_excess": per_level,
            "max_abs_excess": round(mx[0], 4),
            "max_rule": mx[1],
            "levels_check": None if lv_res is None else {"levels_distinct": lv_res["levels_distinct"], "min_best_ks": lv_res["min_best_ks"], "parameter": lv_res["parameter"], "parameter_mean_by_level": lv_res["parameter_mean_by_level"], "cross_level_identical_texts": lv_res["cross_level_identical_texts"]},
        }
        if lid in PARTIAL_ONLY and over and all(worst_by[t][lid][lv]["class"] == "partial" for t in worst_by for lv in per_level if worst_by[t][lid][lv]["max_counted"] > BOUND):
            rec["note_partial_only"] = "the only rules above 0.15 are of the auditor's class 'partial' (a truncated procedure); R-24 counts every cheap rule, so it is dropped; whether partial rules count is PENDING LEAD REVIEW"
        rec["reasons_before_capacity"] = reasons
        rec["status_before_capacity"] = "NOT_REGISTERED" if reasons else "SURVIVES"
        out_l[lid] = rec
    # clusters and capacity at the G of the survivors
    alive = [lid for lid, r in out_l.items() if r["status_before_capacity"] == "SURVIVES"]
    final_alive: list[str] = []
    for lid in alive:
        c = cap.get(lid)
        if c is None:
            out_l[lid]["capacity"] = {"checked": False}
            continue
        sup = c["supplied"]
        rows = {lv: {"supplied": sup[lv], "demand": c["demand"], "passes_as_written": sup[lv] >= c["demand"]} for lv in sorted(sup)}
        out_l[lid]["capacity"] = {"checked": True, "g_used": g_cap, "demand": c["demand"], "per_level": rows, "passes_as_written": all(v["passes_as_written"] for v in rows.values())}
    for lid in alive:
        cap_r = out_l[lid]["capacity"]
        if cap_r.get("checked") and not cap_r["passes_as_written"]:
            members = [m for m in cl[cl_of[lid]] if m in alive and out_l[m]["capacity"].get("checked")]
            per_cluster_ok = all(sum(out_l[m]["capacity"]["per_level"][lv]["supplied"] for m in members) >= cap_r["demand"] for lv in cap_r["per_level"] if not cap_r["per_level"][lv]["passes_as_written"])
            cap_r["passes_only_under_a_per_cluster_builder"] = bool(per_cluster_ok and len(members) > 1)
            fails = [f"L{lv} supplied {v['supplied']} of {v['demand']}" for lv, v in cap_r["per_level"].items() if not v["passes_as_written"]]
            out_l[lid]["reasons_after_capacity"] = [f"capacity against core.generate_pool as written at G = {g_cap} (demand {cap_r['demand']}): " + "; ".join(fails) + (" (passes only under a per-cluster builder: R-28, not counted as passing, fate left to the addendum)" if cap_r["passes_only_under_a_per_cluster_builder"] else "")]
            out_l[lid]["status"] = "NOT_REGISTERED"
        else:
            out_l[lid]["status"] = "SURVIVES"
            final_alive.append(lid)
    for lid, r in out_l.items():
        if r["status_before_capacity"] == "NOT_REGISTERED":
            r["status"] = "NOT_REGISTERED"
        r["reason"] = "; ".join(r["reasons_before_capacity"] + r.get("reasons_after_capacity", [])) or (REPAIRED.get(lid) and f"survives; repaired: {REPAIRED[lid]}") or "survives; no repair needed"
    clusters_out: dict[str, Any] = {}
    for k, members in cl.items():
        st = [out_l[m]["status"] for m in members]
        clusters_out[k] = {"members": list(members), "member_status": dict(zip(members, st, strict=True)), "survives": "SURVIVES" in st}
        live = [m for m in members if out_l[m]["status"] == "SURVIVES"]
        if live:
            per_lv: dict[str, Any] = {}
            for lv in sorted(out_l[live[0]]["capacity"]["per_level"]):
                sup = {m: out_l[m]["capacity"]["per_level"][lv]["supplied"] for m in live}
                dm = out_l[live[0]]["capacity"]["demand"]
                per_lv[lv] = {"demand": dm, "supplied_by_member": sup, "every_surviving_member_passes_as_written": all(v >= dm for v in sup.values())}
            clusters_out[k]["capacity_as_written"] = per_lv
    surv_clusters = sorted(k for k, v in clusters_out.items() if v["survives"])
    g_final = len(surv_clusters)
    res = {
        "round": "M0-R2 fix round 4 (narrow repair round, LEAD_RULINGS_5 R-24..R-29)",
        "status_note": "Nothing in this file is a registration. Self-check by the implementer, not independent review, not Astra validation, not human approval. Astra review: NOT_PERFORMED.",
        "shortcut_bound": BOUND,
        "bound_measure": "largest effect over rules of class cue, partial, construct (auditor's classes, copied in r2_fix4_battery.klass); open answers: accuracy over all items (base rate 0); yes/no: |accuracy among items where it applies - 0.5|; per level the larger of the two seed sets (a4 = the auditor's seeds, f4 = own seeds), 2,000 test items per level and shape; P (valid alternative or full solve) and artifact rules are reported (largest_not_counted_P_or_artifact), not counted",
        "inputs": inputs,
        "lineages": out_l,
        "clusters": clusters_out,
        "surviving_clusters": surv_clusters,
        "surviving_cluster_count": g_final,
        "surviving_lineages": sorted(final_alive),
        "G_used_for_capacity": g_cap,
        "G_final": g_final,
        "G_per_part": g_final // 2,
        "demand_at_G_per_part": demand(g_final // 2),
        "capacity_consistent_with_G_per_part": g_cap == g_final // 2,
        "capacity_at_other_G_reported_only": extra,
        "capacity_superseded_G18": sup_old,
    }
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True))
    print("surviving lineages", len(final_alive), "clusters", g_final, "G used for capacity", g_cap, "demand per part", demand(g_final // 2))
    print("surviving clusters:", surv_clusters)
    for lid in ids:
        r = out_l[lid]
        print(f"{r['status']:15s} {lid:38s} max {r['max_abs_excess']:.3f}")


if __name__ == "__main__":
    main()
