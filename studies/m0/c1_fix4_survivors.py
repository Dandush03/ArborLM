# ruff: noqa: E501
"""C1 fix 4: assemble ``manifests/c1_fix4_survivors.json`` from the fix-4 measurements (no new measurement is made here).

Inputs (outputs of the runs described in ``NOTES_FIX4_C1.md``): the rules table of the final set (``c1_fix4_rules_table`` on the draw of the 27 candidate lineages), the rules table of the audit's 37
fix-3 lineages (for the dropped ones), the level check, the capacity run, the execution check, and the audit-4 reference (``lineages_c1_fix4.DROPPED_AUDIT4``).

Status rule (R-24 to R-26; applied in this order, the first that fires decides):
  NOT_REGISTERED if the lineage is named in ``DROPPED_AUDIT4`` (the audit's finding, R-25), or its largest level-wide cheap excess over levels 0-6 is above BOUND = 0.15, or its levels are collapsed,
  or the execution check found an error or a key mismatch, or it supplies fewer items than the demand at some level (per lineage, as ``core.generate_pool`` allocates, R-28).
  Otherwise SURVIVES. Partial-trace mutations (audit class M) are reported, not counted (see ``c1_fix4_rules_table``); in-shape excesses are reported, not counted.
Base rate: every C1 answer is an open line, so chance is 0 and the excess of a rule is its accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any

BOUND = 0.15


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def per_level(entry: dict[str, Any]) -> dict[str, Any]:
    return {lv: {"largest_abs_excess": v["max_excess"], "rule": v["rule"]} for lv, v in sorted(entry["level_wide_cheap"].items())}


def shapes_of(entry: dict[str, Any]) -> dict[str, Any]:
    return {sh: {lv: {"largest_in_shape_rate": v["rate"], "rule": v["rule"]} for lv, v in sorted(perlv.items())} for sh, perlv in sorted(entry["in_shape_max_by_shape"].items())}


SHAPE_DROPS: dict[str, tuple[str, dict[str, str]]] = {
    # fix-4 lineage: (the fix-3 original's name in the rules table, {dropped shape: reason})
    "C1.sieve_marking_f4": ("C1.sieve_marking_f3", {"flags": "audit4 section 3: the order-free divisor test answers the flag-list shape in 1.000 of items at every level"}),
    "C1.fast_power_f4": ("C1.fast_power_f3", {"base": "ruling R-20: the res shape only; audit4 section 6: base and bsum use the exponent only as a round count", "bsum": "ruling R-20: the res shape only; audit4 section 6: base and bsum use the exponent only as a round count"}),
}


def dropped_shapes(name: str, r71: dict[str, Any]) -> dict[str, Any] | None:
    if name not in SHAPE_DROPS:
        return None
    orig, shapes = SHAPE_DROPS[name]
    e = r71[orig + "[fix-3 original, all shapes]"]
    sh = shapes_of(e)
    return {s: {"status": "NOT_REGISTERED", "reason": why, "per_level_in_shape_of_the_fix3_original": sh.get(s, {})} for s, why in shapes.items()}


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules72", required=True)
    ap.add_argument("--rules71", required=True)
    ap.add_argument("--levels72", required=True)
    ap.add_argument("--levels71-orig", required=True)
    ap.add_argument("--capacity", required=True)
    ap.add_argument("--exec", dest="exec_", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from studies.m0.c1_fix4_capacity import demand
    from studies.m0.c1_fix4_draw import audit4_set
    from studies.m0.lineages_c1_fix3_clusters import cluster_of as fix3_cluster_of
    from studies.m0.lineages_c1_fix4 import (
        DROPPED_AFTER_REMEASURE,
        DROPPED_AUDIT4,
        RETRY_SITES,
        SHARED_FINISH_REJECT,
        SUPERSEDES4,
        current_after_audit4,
    )
    from studies.m0.lineages_c1_fix4_clusters import (
        DROPPED_CLUSTERS,
        DROPPED_MEMBERS,
        MEMBERS,
        VARIANT_CLUSTERS,
        cluster_of,
        smaller_part,
    )

    r72, r71 = load(a.rules72)["lineages"], load(a.rules71)["lineages"]
    lev72, lev71 = load(a.levels72), load(a.levels71_orig)
    cap, exe = load(a.capacity), load(a.exec_)
    cap_by: dict[str, dict[int, int]] = {}
    for row in cap["rows"]:
        cap_by.setdefault(row["lineage"], {})[row["level"]] = row["supplied"]
    audit_set = audit4_set()
    current = current_after_audit4()
    out_lineages: list[dict[str, Any]] = []

    def base_entry(name: str, table: dict[str, Any]) -> dict[str, Any]:
        e = table.get(name)
        if e is None:
            raise KeyError(name)
        return e

    # ---- lineages the fix-3 set had that were dropped by the audit's findings, then the survivors and the repaired ones
    superseded_by_f4 = {v: k for k, v in SUPERSEDES4.items()}
    for name in audit_set:
        if name in superseded_by_f4:  # replaced by a fix-4 lineage; reported under the fix-4 id
            continue
        e = base_entry(name, r71)
        fix3 = fix3_cluster_of(name)
        reason = DROPPED_AUDIT4.get(name)
        status = "NOT_REGISTERED" if reason else "SURVIVES"
        if not reason and name in current:
            continue  # a survivor candidate: reported below from the final measurements
        out_lineages.append({
            "name": name, "strict_cluster": fix3, "status": status, "reason": reason or "", "supersedes": None,
            "level_wide_cheap_per_level": per_level(e), "level_wide_max": e["level_wide_max"], "in_shape_max_overall": e["in_shape_max_overall"],
            "partial_trace_M_level_wide": e["partial_trace_M_level_wide_EFF_SM"], "shapes": shapes_of(e),
            "measured_in": "fix-4 re-run (seed 71 draw, battery seed 83) of the fix-3 builders as they were",
        })
    n_surv = 0
    for name in current:
        e = base_entry(name, r72)
        lv = lev72[name]
        ex = exe["lineages"][name]
        caps = cap_by[name]
        problems: list[str] = []
        reason = DROPPED_AUDIT4.get(name) or DROPPED_AFTER_REMEASURE.get(name, "")
        if e["level_wide_max"] > BOUND:
            problems.append(f"level-wide cheap excess {e['level_wide_max']} above {BOUND}")
        if not lv["levels_distinct"]:
            problems.append("levels collapsed: " + "; ".join(lv["collapsed"]))
        if ex["errors"] or ex["key_mismatches"] or ex["second_solver_mismatches"] or ex["run_disagreements"] or ex["not_one_line"]:
            problems.append(f"execution check: {ex}")
        status = "NOT_REGISTERED" if (problems or reason) else "SURVIVES"
        n_surv += status == "SURVIVES"
        entry: dict[str, Any] = {
            "name": name, "strict_cluster": cluster_of(name) if status == "SURVIVES" and name in sum((list(v) for v in MEMBERS.values()), []) else "", "status": status,
            "reason": reason or "; ".join(problems) or "no cheap rule or closed form above 0.15 at any level in the union of the three scripts (level-wide); levels distinct; keys execute; capacity measured",
            "supersedes": SUPERSEDES4.get(name),
            "level_wide_cheap_per_level": per_level(e), "level_wide_max": e["level_wide_max"], "in_shape_max_overall": e["in_shape_max_overall"],
            "in_shape_flag_above_bound_PENDING_LEAD_REVIEW": e["in_shape_max_overall"] > BOUND,
            "partial_trace_M_level_wide": e["partial_trace_M_level_wide_EFF_SM"],
            "partial_trace_M_max_PENDING_LEAD_REVIEW": max(e["partial_trace_M_level_wide_EFF_SM"].values()),
            "shapes": shapes_of(e),
            "levels": {"distinct": lv["levels_distinct"], "collapsed": lv["collapsed"], "weakly_separated_steps": lv["weakly_separated"], "stated_parameter": lv["stated_parameter"]},
            "retry_sites": list(RETRY_SITES[name]) if name in RETRY_SITES else None,
            "shared_finish_reject": SHARED_FINISH_REJECT,
            "shapes_dropped": dropped_shapes(name, r71),
            "execution": ex,
            "capacity_supplied_per_level_capped_at_count": {str(k): v for k, v in sorted(caps.items())},
            "measured_in": "fix-4 draw (seed 71), battery (seed 83), a3 run, capacity (seed 4242), execution (seed 5)",
        }
        out_lineages.append(entry)
    surviving = {c: [m for m in ms if any(x["name"] == m and x["status"] == "SURVIVES" for x in out_lineages)] for c, ms in MEMBERS.items()}
    surviving = {c: ms for c, ms in surviving.items() if ms}
    n_clusters = len(surviving)
    g = smaller_part(n_clusters)
    dem = demand(g)
    cap_clusters: dict[str, Any] = {}
    for c, ms in sorted(surviving.items()):
        per_lv: dict[str, Any] = {}
        for lv_i in range(7):
            sup = {m: cap_by[m][lv_i] for m in ms}
            per_lv[str(lv_i)] = {"supplied_by_member": sup, "sum": sum(sup.values()), "demand": dem, "pass_per_lineage": all(v >= dem for v in sup.values()), "pass_per_cluster": sum(sup.values()) >= dem}
        cap_clusters[c] = {"members": ms, "per_level": per_lv, "all_levels_pass_per_lineage": all(v["pass_per_lineage"] for v in per_lv.values()), "all_levels_pass_per_cluster": all(v["pass_per_cluster"] for v in per_lv.values())}
    manifest = {
        "round": "M0 C1 fix 4 (narrow repair round, lead rulings 5, R-24 to R-29). Nothing here is a registration. Astra review: NOT_PERFORMED.",
        "bound": BOUND, "bound_set_by": "the human lead (HUMAN_LEAD_WORDS_5.md), two-sided, after item-side measurements had been seen; no model has been run",
        "base_rate": "0 for every lineage (open answers: a rule's excess over the base rate is its accuracy)",
        "level_wide_cheap": "see c1_fix4_rules_table.py (the union of the audit-4 rules, the fix-3 battery and the audit-3 rules; mutations, control rules and the any-literal oracle are not counted)",
        "inputs_sha256": {k: sha(getattr(a, k)) for k in ("rules72", "rules71", "levels72", "levels71_orig", "capacity", "exec_")},
        "lineages": sorted(out_lineages, key=lambda x: x["name"]),
        "superseded": {v: k for k, v in SUPERSEDES4.items()},
        "pre_repair_levels": {k: {"collapsed": v["collapsed"], "levels_distinct": v["levels_distinct"], "steps": v["steps"]} for k, v in sorted(lev71.items())},
        "removed_member_of_a_standing_cluster": DROPPED_MEMBERS,
        "dropped_clusters": {c: list(ms) for c, ms in sorted(DROPPED_CLUSTERS.items())},
        "surviving_clusters": {"count": n_clusters, "count_without_variants": n_clusters - len([c for c in surviving if c in VARIANT_CLUSTERS]), "variant_clusters": [c for c in surviving if c in VARIANT_CLUSTERS], "list": sorted(surviving)},
        "surviving_lineages": {"count": n_surv, "list": sorted(x["name"] for x in out_lineages if x["status"] == "SURVIVES")},
        "G": {"smaller_part_N_div_2": g, "demand_per_cluster_and_level": dem, "formula": "10 * (ceil(4000/G) + ceil(20000/G) + 100)", "literal_G_equals_N": {"G": n_clusters, "demand": demand(n_clusters)}},
        "capacity": {"count_drawn": cap["count"], "seed": cap["seed"], "builder": "core.draw_items as core.generate_pool calls it (R-28), fresh taken set per lineage and level", "clusters": cap_clusters,
                     "all_clusters_all_levels_pass_per_lineage": all(v["all_levels_pass_per_lineage"] for v in cap_clusters.values())},
    }
    with open(a.out, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"survivors {n_surv}; clusters {n_clusters} ({manifest['surviving_clusters']['count_without_variants']} without the variants); G {g}; demand {dem}; capacity pass per lineage: {manifest['capacity']['all_clusters_all_levels_pass_per_lineage']}")


if __name__ == "__main__":
    main()
