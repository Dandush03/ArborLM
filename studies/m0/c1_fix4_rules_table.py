# ruff: noqa: E501
"""C1 fix 4: the table of cheap-rule and closed-form rates per lineage, level and shape, from the three rule scripts' outputs (measurement; no threshold is set here).

Inputs (all outputs of runs described in ``NOTES_FIX4_C1.md``): the audit-4 analysis ``s5_analyse_v2.py`` output (``--a4``), the fix-3 battery re-run by ``c1_fix4_battery`` (``--battery``), the audit-3
script's outputs per lineage from ``c1_fix4_a3_run`` (``--a3-dir``), and optionally the audit-4 analysis of the two fix-3 originals whose shapes were dropped (``--a4-orig``).

What is measured at a level (open answers, so the base rate is 0 and the excess is the rule's accuracy):
  level-wide cheap excess = the largest of: the audit-4 ``EFF_S`` (best of {most frequent key in shape, every S and G rule} per shape, chosen on one half and scored on the other), its most frequent key
  (2-fold CV), the share of the level that one S or F rule gets right (``rules[...]['share_of_level']``), the battery's most-frequent-key, best-generic-literal and per-rule level shares (hit / n),
  the audit-3 script's most-frequent-key, per-shape most-frequent-key, best-generic and per-rule level shares. Not counted: the audit's partial-trace mutations (class M: one feature of the
  program ignored, the rest traced; for the audit-3 script its four mutation rules, ``A3_MUTATIONS``), convention hazards (class H), the battery's control rules (``C.*``: the program's own algorithm
  re-run), and the 'any literal' oracle (an upper bound, not a rule). The audit-4 mutation level-wide figure is reported separately.
  in-shape excess = the same rules, inside one shape (audit-4 ``rate_in_shape``), reported per shape and level; not used for the drop decision (see the notes).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any

BOUND = 0.15
# audit-3 rules that run a MUTATED copy of the program (class M of the audit-4 scheme: one feature ignored, the rest traced). The audit-3 script scores a mutation that changes nothing as a hit (audit 4,
# section 10, slip (1): the same flaw in its own first version), so they are reported apart and are not counted as cheap rules.
A3_MUTATIONS = ("S.no_turns", "S.no_back", "S.no_skips", "S.all_ones_start")
from studies.m0.c1_fix4_draw import RULE_ALIAS  # noqa: E402

A4_NAME = {v: k for k, v in RULE_ALIAS.items()}  # the id the rule scripts know -> the fix-4 id


def _cls(rule: str) -> str:
    return rule.split(".")[0] if "." in rule else rule


def a4_lineage(per: dict[str, Any]) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    shapes: dict[str, dict[str, Any]] = {}
    m_wide: dict[str, float] = {}
    for lv in range(7):
        p = per[str(lv)]
        cand: list[tuple[float, str]] = [(p["EFF_S"], "a4.EFF_S"), (p["MF"], "a4.MF"), (p["MFsh"], "a4.MFsh")]
        for k, v in sorted(p["rules"].items()):
            shape, rule = k.split("|", 1)
            if rule.startswith("MF_in_shape"):
                if v["n_shape"] >= 25:
                    shapes.setdefault(shape, {}).setdefault(str(lv), []).append((v["rate_in_shape"], "MF_in_shape_cv"))
                continue
            c = _cls(rule)
            if c in ("S", "F"):
                cand.append((v["share_of_level"], f"a4.{shape}|{rule}"))
                if v["n_shape"] >= 25:
                    shapes.setdefault(shape, {}).setdefault(str(lv), []).append((v["rate_in_shape"], rule))
        # closed forms over all the level's shapes at once: per shape the best F rule's level share, summed (the audit's closed forms are per shape; a lineage whose every shape has one is answered in full)
        best_f: dict[str, float] = {}
        for k, v in sorted(p["rules"].items()):
            shape, rule = k.split("|", 1)
            if _cls(rule) == "F" and v["share_of_level"] > best_f.get(shape, 0.0):
                best_f[shape] = v["share_of_level"]
        cand.append((min(1.0, sum(best_f.values())), "a4.closed_forms_best_per_shape_summed"))
        levels[str(lv)] = cand
        m_wide[str(lv)] = p["EFF_SM"]
    return {"cand": levels, "shapes": shapes, "m_wide": m_wide, "shape_counts": {str(lv): per[str(lv)]["shapes"] for lv in range(7)}}


def battery_levels(per: dict[str, Any]) -> dict[str, list[tuple[float, str]]]:
    out: dict[str, list[tuple[float, str]]] = {}
    for lv in range(7):
        p = per[str(lv)]
        n = p["n"]
        cand = [(p["MF_cv"], "battery.MF_cv"), (p["BEST_generic_cv"], "battery.BEST_generic_cv")]
        for k, v in sorted(p["S"].items()):
            if "|C." in k:  # control rules: the program's own algorithm re-run (the battery's self-check), not a shortcut
                continue
            cand.append((v["hit"] / n, f"battery.{k}"))
        out[str(lv)] = cand
    return out


def a3_levels(per: dict[str, Any]) -> dict[str, list[tuple[float, str]]]:
    out: dict[str, list[tuple[float, str]]] = {}
    for lv in range(7):
        p = per[str(lv)]
        n = p["n"]
        cand = [(p["MF_cv"], "a3.MF_cv"), (p["MF_shape_cv"], "a3.MF_shape_cv"), (p["BEST_generic_cv"], "a3.BEST_generic_cv")]
        for k, v in sorted(p["S"].items()):
            if k.split("|", 1)[1] in A3_MUTATIONS:
                continue
            cand.append((v["hit"] / n, f"a3.{k}"))
        out[str(lv)] = cand
    return out


def merge(lid: str, a4: dict[str, Any] | None, bat: dict[str, Any] | None, a3: dict[str, Any] | None) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    srcs = {"a4": a4["cand"] if a4 else {}, "battery": battery_levels(bat) if bat else {}, "a3": a3_levels(a3) if a3 else {}}
    for lv in range(7):
        allc: list[tuple[float, str]] = []
        for s in ("a4", "battery", "a3"):
            allc.extend(srcs[s].get(str(lv), []))
        best = max(allc, key=lambda t: (t[0], t[1]))
        levels[str(lv)] = {"max_excess": round(best[0], 4), "rule": best[1], "per_source_max": {s: round(max((x[0] for x in srcs[s].get(str(lv), [])), default=0.0), 4) for s in ("a4", "battery", "a3")}}
    shapes_out: dict[str, Any] = {}
    if a4:
        for sh, perlv in sorted(a4["shapes"].items()):
            shapes_out[sh] = {lv: {"rate": round(max(x[0] for x in rs), 3), "rule": max(rs)[1]} for lv, rs in sorted(perlv.items())}
    return {
        "lineage": lid,
        "level_wide_cheap": levels,
        "level_wide_max": round(max(v["max_excess"] for v in levels.values()), 4),
        "in_shape_max_by_shape": shapes_out,
        "in_shape_max_overall": round(max((v["rate"] for sh in shapes_out.values() for v in sh.values()), default=0.0), 3),
        "partial_trace_M_level_wide_EFF_SM": a4["m_wide"] if a4 else {},
        "shape_counts_by_level": a4["shape_counts"] if a4 else {},
    }


def load_a3(d: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fn in sorted(glob.glob(os.path.join(d, "*.json"))):
        if os.path.basename(fn) == "run_log.json":
            continue
        tag = os.path.basename(fn).replace(".json", "")
        name = "C1." + tag.split("__")[0]
        with open(fn) as f:
            data = json.load(f)
        out[name] = data[sorted(data)[0]]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a4", required=True)
    ap.add_argument("--a4-orig", default="")
    ap.add_argument("--alias-ids", default=",".join(sorted(RULE_ALIAS.values())), help="the ids (as the rule scripts know them) whose draw came from the fix-4 builder; they are reported under the fix-4 id")
    ap.add_argument("--battery", required=True)
    ap.add_argument("--a3-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.a4) as f:
        a4_all = json.load(f)
    with open(a.battery) as f:
        bat_all = json.load(f)
    a3_all = load_a3(a.a3_dir)
    alias_ids = set(a.alias_ids.split(",")) if a.alias_ids else set()
    res: dict[str, Any] = {"bound": BOUND, "lineages": {}}
    for lid in sorted(a4_all):
        name = A4_NAME[lid] if lid in A4_NAME and lid in alias_ids else lid
        res["lineages"][name] = merge(name, a4_lineage(a4_all[lid]), bat_all.get(name), a3_all.get(lid))
    if a.a4_orig:
        with open(a.a4_orig) as f:
            orig = json.load(f)
        for lid in sorted(orig):
            res["lineages"][lid + "[fix-3 original, all shapes]"] = merge(lid, a4_lineage(orig[lid]), None, None)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    for name, r in sorted(res["lineages"].items()):
        print(f"{name:60s} level-wide max {r['level_wide_max']:.3f}  in-shape max {r['in_shape_max_overall']:.3f}")


if __name__ == "__main__":
    main()
