# ruff: noqa: E501
"""M1 fix round 4: checks stage and the survivors manifest (R-24 to R-29). Standard library, torch and ``studies`` only. Self-check only: not independent review, not Astra, not human approval; nothing is registered.

Stages (from the worktree, PYTHONHASHSEED=0 PYTHONPATH=<worktree>):
  python -m studies.m0.m1_fix4_survivors checks --out <checks.json>
  python -m studies.m0.m1_fix4_survivors build --battery <battery.json> --capacity <cap.json> --checks <checks.json> --out studies/m0/manifests/m1_fix4_survivors.json

Decision rules, applied mechanically (fixed before the measurement; the bound is the human lead's 0.15, two-sided):
  1. a lineage NOT REGISTERED in round 3 stays NOT REGISTERED;
  2. dropped if at any level the largest |rule rate - base| over the union battery (``m1_fix4_battery.summarise``; rules judged the correct procedure excluded, listed in the manifest) exceeds 0.15;
  3. dropped if two levels give byte-identical items from the same stream (the level is ignored) or a repaired lineage's stated parameter is not strictly rising;
  4. dropped if an answer key differs from the second derivation;
  5. a REPAIRED lineage is dropped if it fails capacity under the as-written builder (R-25 (c)); every other capacity failure under the as-written builder is LISTED for the lead and the lineage keeps its status (R-28).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from studies.m0.core import Lineage
from studies.m0.lineages_m1_fix3 import NOT_REGISTERED as NOT_REGISTERED_FIX3
from studies.m0.lineages_m1_fix4 import (
    FIX4,
    LEVEL_PARAMETER,
    NOT_REGISTERED_FIX4,
    REPLACES,
    load_all,
    stem,
)
from studies.m0.lineages_m1_fix4_clusters import cluster_of, strict_clusters
from studies.m0.m1_fix4_battery import procedure_exclusions
from studies.m0.m1_fix4_capacity import report as capacity_report

BOUND = 0.15
LEVELS = range(7)
REPAIRED = tuple(sorted(x.id for x in FIX4))

# where audit 4 names the lineage (AUDIT4_M1.md sections), for the reason strings
AUDIT4_REF: dict[str, str] = {
    "coins": "AUDIT4_M1 section 3 and 8: floor(total/hi) - 1 on hi asks, +0.160 at level 0 (R-13 zero on floor(total/hi))",
    "pigeonhole_worst_case": "AUDIT4_M1 section 3 and 8: 'every other colour, then k of the largest' +0.287 at level 1",
    "mode_tally": "AUDIT4_M1 section 3 and 8: the 'others' key predictable from the printed list length, +0.382 at level 1; levels flat",
    "slot_permutations": "AUDIT4_M1 section 2 and 8: leading-zero wording defect in 17.6-19.0 % of items (repair (b)) and collapsed levels (repair (c))",
    "mixture": "AUDIT4_M1 section 4: levels 0=1=2 and 3=4=5=6 identical (repair (c))",
    "gcd_lcm": "AUDIT4_M1 section 4: levels 0=1=2, 3=4, 5=6 identical (repair (c)); section 3: false general rule exact at k >= 3, PENDING LEAD REVIEW, not repaired",
    "finite_differences": "AUDIT4_M1 section 4: levels 0=1=2, 3=4, 5=6 identical (repair (c))",
    "average_missing": "AUDIT4_M1 section 4 (profile): levels 0=1, 2=3, 4=5 identical, unchanged since batch 1; read as the same collapsed-level defect (repair (c)), see the notes",
    "clock_duration": "AUDIT4_M1 section 4 (profile): levels 0=1, 2=3, 4=5 identical, unchanged since batch 1; read as the same collapsed-level defect (repair (c)), see the notes",
    "pythagoras": "AUDIT4_M1 section 6 and 8: NOT REGISTERED in round 3 (capacity and memorised triples), agreed by the audit",
    "binomial_choose": "AUDIT4_M1 section 6 and 8: NOT REGISTERED in round 3 (capacity), agreed by the audit",
    "digit_puzzle": "AUDIT4_M1 section 6 and 8: NOT REGISTERED in round 3 (capacity and the clue tell), agreed by the audit",
}

HYGIENE = {
    "file": "studies/m0/lineages_m1_fix3_c.py", "line": 116, "before": "for d in set(ds) if ds.count(d) == 1]", "after": "for d in sorted(set(ds)) if ds.count(d) == 1]",
    "lineage": "M1.digit_puzzle_r3 (NOT REGISTERED in round 3)",
    "generated_items_identical": False,
    "measurement": "60 items at levels 0-4 and 10 at levels 5-6 from the stream (seed 4001, 'fix4-hygiene', lineage id, level), SHA-256 of the items' JSON, PYTHONHASHSEED 0 and 1 gave the same hashes each time",
    "total_before": "60cbdf1e35e8d6ac15e6db206e46c51f69d3fe592c524b7277870e14aefc351d",
    "total_after": "78989ef5a9997b132d49d0810cd12cd4d30008fe3012acd6d364906467b97ebf",
    "per_level_before": ["46e8ee48", "0b1a20fa", "ed71cf9a", "029b5f92", "1ce9051e", "98c09225", "12c06b84"],
    "per_level_after": ["0f6052a3", "fd2d2883", "84314adb", "8ca88965", "f505308e", "316cb9ec", "b5d3b522"],
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return str(p)


def checks_one(lin: Lineage) -> dict[str, Any]:
    from studies.m0.m1_fix4_checks import (
        identical_level_pairs,
        key_problems,
        level_profile,
        rising_parameter_problems,
    )

    st = stem(lin.id)
    out: dict[str, Any] = {"identical_level_pairs": identical_level_pairs(lin), "profile": level_profile(lin), "key_problems": key_problems(lin)}
    out["rising_parameter_problems"] = rising_parameter_problems(st) if lin.id in REPAIRED else None
    return out


def _checks_task(lid: str) -> tuple[str, dict[str, Any]]:
    lin = {x.id: x for x in load_all()}[lid]
    return lid, checks_one(lin)


def stage_checks(out: Path, workers: int) -> None:
    import multiprocessing as mp

    ids = sorted(x.id for x in load_all() if "digit_puzzle" not in x.id)  # digit_puzzle: NOT REGISTERED, builder takes seconds per item at levels 5-6
    with mp.get_context("spawn").Pool(workers) as pool:
        res = dict(pool.imap_unordered(_checks_task, ids, chunksize=1))
    out.write_text(json.dumps({"lineages": res}, indent=1, sort_keys=True))


def decide(battery: dict[str, Any], checks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Status of every written lineage from the measurements (rules 1 to 4; rule 5 needs the capacity report and is applied in ``build``)."""
    summ = battery["summary"]
    out: dict[str, dict[str, Any]] = {}
    for x in sorted(load_all(), key=lambda y: y.id):
        lid, st = x.id, stem(x.id)
        reasons: list[str] = []
        if lid in NOT_REGISTERED_FIX3:
            reasons.append(f"NOT REGISTERED in round 3 and stays so (R-24/R-25: no new lineage, no replacement): {NOT_REGISTERED_FIX3[lid][:160]}...")
        per = {str(lv): {k: summ[lid][str(lv)][k] for k in ("max_abs_excess", "signed", "rule", "excluded_procedure_max_signed", "excluded_procedure_rule")} for lv in LEVELS}
        over = [(lv, per[str(lv)]) for lv in LEVELS if per[str(lv)]["max_abs_excess"] > BOUND]
        if over:
            lv0, p0 = max(over, key=lambda t: t[1]["max_abs_excess"])
            reasons.append(f"R-24: |rule - base| > {BOUND} at levels {[lv for lv, _ in over]}; largest {p0['signed']:+.3f} at level {lv0} ({p0['rule']})")
        c = checks["lineages"].get(lid)
        if c is not None:
            if c["identical_level_pairs"]:
                reasons.append(f"R-21/R-26: levels still identical: {c['identical_level_pairs']}")
            if c["rising_parameter_problems"]:
                reasons.append(f"R-25 (c): stated parameter not rising: {c['rising_parameter_problems']}")
            if c["key_problems"]:
                reasons.append(f"answer key differs from the second derivation: {c['key_problems'][:2]}")
        out[lid] = {"name": lid, "stem": st, "strict_cluster": cluster_of(lid), "repaired_in_round_4": lid in REPAIRED, "replaces": REPLACES.get(lid),
                    "audit4_reference": AUDIT4_REF.get(st, "AUDIT4_M1 section 8: REGISTRABLE AS IS on the audit's measurement"),
                    "reasons": reasons, "per_level_max_rule_excess": per, "level_checks": c}
    return out


def stage_build(battery_p: Path, cap_p: Path, checks_p: Path, out: Path, text_p: Path | None = None) -> None:
    battery = json.loads(battery_p.read_text())
    cap = json.loads(cap_p.read_text())
    checks = json.loads(checks_p.read_text())
    text = json.loads(text_p.read_text()) if text_p else None
    dec = decide(battery, checks)
    survivors = sorted(k for k, v in dec.items() if not v["reasons"])
    cap_rep = capacity_report(cap, survivors, None, text)
    # rule 5: a repaired lineage that fails the as-written capacity is dropped
    aw_fail = cap_rep["as_written"]["fails"]
    for lid in REPAIRED:
        if lid in survivors and lid in aw_fail:
            dec[lid]["reasons"].append(f"R-25 (c): the repaired lineage fails capacity under the as-written builder at levels {aw_fail[lid]}")
    survivors = sorted(k for k, v in dec.items() if not v["reasons"])
    cap_rep = capacity_report(cap, survivors, None, text)
    clusters = strict_clusters(survivors)
    for lid, v in dec.items():
        v["status"] = "SURVIVES" if not v["reasons"] else "NOT_REGISTERED"
        v["reason"] = "; ".join(v["reasons"]) if v["reasons"] else v["audit4_reference"]
        v["capacity_as_written_fails_at_levels"] = cap_rep["as_written"]["fails"].get(lid) if v["status"] == "SURVIVES" else None
        v["capacity_as_written_min_margin"] = cap_rep["as_written"]["lineages"].get(lid, {}).get("min_margin")
        del v["reasons"]
    dropped = sorted(k for k, v in dec.items() if v["status"] == "NOT_REGISTERED")
    # PENDING LEAD REVIEW: rules the auditor / the implementer judged to be the correct procedure are excluded from the bound; where one of them is above the bound at some level it is listed here, so a different
    # reading of R-24 ("any cheap rule") is a visible one-line change
    proc_above: dict[str, Any] = {}
    for lid in survivors:
        rows = {lv: v for lv, v in dec[lid]["per_level_max_rule_excess"].items() if abs(v["excluded_procedure_max_signed"]) > BOUND}
        if rows:
            proc_above[lid] = {"levels": sorted(int(x) for x in rows), "largest_signed": max((v["excluded_procedure_max_signed"] for v in rows.values()), key=abs),
                               "rules": sorted({v["excluded_procedure_rule"] for v in rows.values()})}
    manifest = {
        "title": "M1 fix round 4 survivors (narrow repair round; R-24 to R-29). Implementer self-check: not independent review, not Astra validation, not human approval; nothing is registered; no model was run.",
        "bound": {"value": BOUND, "two_sided": True, "set_by": "the human lead (fifth decision)", "observed_before": "item-side measurements only"},
        "measure": "largest |rule rate - base| over the union battery (own battery by its own scoring, audit-4 script, audit-3 rule definitions by audit-3 scoring), rates over all items, base = held-out most frequent answer; MEASURED",
        "n_per_level": battery["n"], "battery_seeds": battery["seeds"],
        "inputs": {"battery": {"path": _rel(battery_p), "sha256": _sha(battery_p)}, "capacity": {"path": _rel(cap_p), "sha256": _sha(cap_p)}, "checks": {"path": _rel(checks_p), "sha256": _sha(checks_p)}, "text_capacity": ({"path": _rel(text_p), "sha256": _sha(text_p)} if text_p else None)},
        "procedure_rule_exclusions": procedure_exclusions(),
        "hygiene_edit": HYGIENE,
        "survivors": survivors, "survivor_count": len(survivors), "dropped": dropped, "dropped_count": len(dropped),
        "surviving_clusters": {k: v for k, v in clusters.items()}, "surviving_cluster_names": sorted(clusters), "surviving_cluster_count": len(clusters),
        "excluded_everywhere": ["M1.min_cost_packs_r2", "M1.min_cost_packs"],
        "survivors_with_an_excluded_procedure_rule_above_the_bound_PENDING_LEAD_REVIEW": proc_above,
        "capacity": cap_rep,
        "capacity_as_written_failures_listed_for_the_lead": {k: v for k, v in sorted(cap_rep["as_written"]["fails"].items())},
        "candidates": dec,
    }
    out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print("survivors", len(survivors), "clusters", len(clusters), "dropped", dropped, file=sys.stderr)
    print("NOT_REGISTERED_FIX4 in code:", sorted(NOT_REGISTERED_FIX4), file=sys.stderr)
    _ = LEVEL_PARAMETER


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="stage", required=True)
    c = sub.add_parser("checks")
    c.add_argument("--out", required=True)
    c.add_argument("--workers", type=int, default=6)
    b = sub.add_parser("build")
    b.add_argument("--battery", required=True)
    b.add_argument("--capacity", required=True)
    b.add_argument("--checks", required=True)
    b.add_argument("--text", default="")
    b.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.stage == "checks":
        stage_checks(Path(a.out), a.workers)
    else:
        stage_build(Path(a.battery), Path(a.capacity), Path(a.checks), Path(a.out), Path(a.text) if a.text else None)


if __name__ == "__main__":
    main()
