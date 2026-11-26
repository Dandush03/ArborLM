# ruff: noqa: E501
"""Write field_table.json: for every output form of the eleven run units, every field the pooling script reads (with the role it plays) and
every field it does not read (with the reason). Stage 1S point 2 ("The field table") and ruling R-46. Standard library only.

    python3 -I studies/m0/fresh_run/make_field_table.py [--out PATH]

The pooling script takes the status and the role of every structural field from the written file, not from its own code: a field that is
not listed makes it stop, a field listed as not read is never read, and the fields of R-46 are not read because this table says so.
Verified by the implementer against the committed code (b78e58b1) and against the keys (not the values) of the implementers' dry outputs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))


def R(role: str, note: str = "", **kw: Any) -> dict[str, Any]:
    return {"status": "read", "role": role, "note": note, **kw}


def P(role: str, note: str = "", **kw: Any) -> dict[str, Any]:
    """Written into the report only (R-57: rates within one shape); never a rule, enters no decision."""
    return {"status": "report_only", "role": role, "note": note, **kw}


def N(reason: str, note: str = "", **kw: Any) -> dict[str, Any]:
    return {"status": "not_read", "reason": reason, "note": note, **kw}


R46 = "R-46: its value uses the answers of the items it is scored on (an oracle or a best-of choice made and scored on the same items); not a rule"
DESC = "descriptive: not a rule's figure"
HELP = "helper: input of a later step of the unit, not a result"

FORMS: dict[str, Any] = {
    "r1_rows": {
        "units": ["R1a", "R1b"],
        "files": "<id>.aud.jsonl, <id>.impl.jsonl, <id>.feat.jsonl (one JSON object per line)",
        "scopes": {"row": {
            "lineage": R("lineage_id", "mapped to the survivor-list id by the plan's id map; a lineage that is not on the map is not read"),
            "level": R("level"),
            "heuristic": R("rule_name", "the rule's name as written; one rule = one name in one kind of file of one unit for one lineage"),
            "n": R("items", "the row's own item count (1,000 per level for the R1a fitted lookups, as the text says)"),
            "eff": R("excess_eff", "already the rate less chance, rounded to 4 decimals by the script (pooled as the item-weighted mean of the written figures)", decimals=4),
            "anti": R("excess_anti", "the gain from choosing among the options the rule did not pick; None for an open answer and for the fitted lookups; read as an excess of its own", decimals=4),
            "fired": R("exact_listing_fired", "read only to list exact rows (point 8): items on which the rule answered"),
            "acc_fired": R("exact_listing_acc", "read only to list exact rows (point 8): accuracy on the items it answered; None when it never fired"),
            "chance": N(DESC, "eff is already the excess over chance (point 7), so chance is not needed"),
            "mode_rate": N(R46, "R1b audit rows only: the rate of the commonest answer among the scored items themselves (heuristics4.py:634). Under R-46 it is not a rule; the fitted constant rule constant_mfk_fitted is a row of its own and is read", unsure=True),
        }},
    },
    "r1c_stdout": {
        "units": ["R1c"],
        "files": "stdout.txt: one line per lineage and rule, f\"{lid:36s} {h[:60]:60s} eff \" + 7 values with +.3f + \"   anti \" + 7 values (new_rules_final.py, last line)",
        "scopes": {"line": {
            "lineage_id": R("lineage_id", "first token; padded to 36 characters"),
            "rule_name": R("rule_name", "cut to 60 characters by the script; read as printed (trailing blanks removed)"),
            "eff_values": R("excess_eff_levels", "exactly 7 values, levels 0 to 6; 4-decimal rounding then 3-decimal printing: uncertainty 0.00055 (point 7)", decimals_uncertainty="0.00055"),
            "anti_values": R("excess_anti_levels", "exactly 7 values, levels 0 to 6; same uncertainty", decimals_uncertainty="0.00055"),
            "item_count": N(DESC, "the script writes none; the plan's items per level is used (R1c, point 8 last bullet: no row can be set aside)"),
        }},
    },
    "r2_json": {
        "units": ["R2a", "R2b"],
        "files": "r2a.json, f_rules.json, f_rules_new.json",
        "scopes": {
            "top": {
                "lineages": R("lineage_map", "{lid: {level: {shape: ...}}}; lid mapped by the plan's id map"),
                "n": N(DESC, "the item count the script was asked for; each shape's own n is read"),
                "seeds": N(DESC, "a literal description or tag of the original, not the seed; seeds are taken from the plan"),
            },
            "shape": {
                "n": R("items", "items of the shape (the test draw); summed over the shapes of the level"),
                "answer_type": R("answer_type", "yn gives the base 0.5 and the statistic k/napp; list, number and text give the base 0"),
                "rules": R("rules_map", "{rule name: counts}; R2a writes no rule with napp = 0, R2b writes every rule"),
                "distinct_answers": N(DESC),
                "yes_share": N(DESC, "R2a, yes/no shapes only"),
            },
            "rule": {
                "k": R("hits"),
                "napp": R("applicable", "items on which the rule gives an answer"),
                "nerr": N(DESC, "items on which the rule raised; the script counts them as no answer, which k and napp already reflect"),
                "acc_all": N("derived: k / n of the shape, which the script forms itself from k and n"),
                "acc_app": N("derived: k / napp, which the script forms itself from k and napp"),
            },
        },
    },
    "m1_battery": {
        "units": ["M1a"],
        "files": "battery.json",
        "scopes": {
            "top": {
                "raw": R("sections", "sections own, a4 and a3, each {lid: {level: row, a3_skipped_items}}"),
                "n": N(DESC),
                "seeds": N("not the true seeds: the literals of the original (410302, 17, 5) are written whatever the seeds were (K15); seeds are taken from the plan"),
                "exclusions": N(DESC, "the original's list of procedure exclusions; classes come from the class table only"),
                "summary": N("derived: the script's own maxima over the same rates; the pooling script forms every figure itself"),
            },
            "lineage": {"a3_skipped_items": N(DESC, "items on which an audit-3 rule raised; section a3 only")},
            "level_own": {
                "N": R("items"),
                "base": R("base", "held-out rate of the most frequent answer; read as the rule 'most frequent answer' against chance and as the second base (point 7)", decimals=4),
                "rates": R("rates_map", "{key: rate}; named 'im:' + key; keys ending __within_applicable are not rules (K7)", decimals=4),
                "minus_base": N("derived: rates less base, formed by the pooling script from the two pooled figures"),
                "mode_insample": N(R46, "the commonest answer's rate among the scored items themselves", unsure=True),
                "halfwidth95": N("derived: a half-width, not a rule's figure"),
                "answer_echoed_anywhere": N(R46, "whether the answer occurs among the numbers of the question, counted over the scored items", unsure=True),
            },
            "level_a4": {
                "N": R("items"),
                "base": R("base", "as in own", decimals=4),
                "rates": R("rates_map", "{key: rate}; named as written (they already carry a4: or im:)", decimals=4),
                "minus_base": N("derived"),
                "best_echo": N(DESC, "names of the echo rules chosen on the held-out halves"),
                "answer_echoed_anywhere": N(R46, "as in own", unsure=True),
                "within_applicable": N("K7: not a rule; the rate over the items a rule applies to"),
            },
            "level_a3": {
                "N": R("items"),
                "base": R("base", "as in own", decimals=4),
                "rates": R("rates_map", "{key: rate}; named 'a3:' + key", decimals=4),
                "minus_base": N("derived"),
            },
        },
    },
    "m1_results": {
        "units": ["M1b", "M1c"],
        "files": "out.json",
        "scopes": {
            "top": {
                "results": R("lineage_map", "{lid: {level: row}}"),
                "mode": N(DESC), "N": N(DESC, "the item count asked for; each row's N is read"), "label": N(DESC),
                "seed": N("seeds are taken from the plan, and this is the same integer"),
            },
            "level": {
                "N": R("items"),
                "base": R("base", "rounded to 5 decimals", decimals=5),
                "rates": R("rates_map", "{key: rate}; named as written; rounded to 5 decimals; keys ending __within_applicable are not rules (K7)", decimals=5),
                "minus_base": N("derived: formed by the pooling script from the two pooled figures"),
                "within_applicable": N("K7: not a rule"),
                "a3_skipped_items": N(DESC),
                "one_op_best": N("K7: not a rule; names of the operands chosen"),
                "asked_is_largest_observed_vs_uniform": N("K7: not a rule; a diagnostic of the answer's position (ratio_share only)"),
            },
        },
    },
    "c1_s5": {
        "units": ["C1a", "C1c"],
        "files": "s5.json (audit4_c1/s5_analyse_v2.py), source 'a4' of the class table",
        "scopes": {
            "level": {
                "n": R("items"),
                "MF": R("rule_scalar", "most frequent key, 2-fold CV; 3 decimals", decimals=3),
                "MFsh": R("rule_scalar", "most frequent key per shape, 2-fold CV; 3 decimals", decimals=3),
                "EFF_S": R("rule_scalar", "3 decimals", decimals=3),
                "EFF_SM": R("rule_scalar", "read; left uncounted only by the class table (measure equal on EFF_SM)", decimals=3),
                "EFF_F": R("rule_scalar", "counts as written, whole (point 6, K8): its components cannot be read apart", decimals=3),
                "rules": R("rules_map", "{'<shape>|<rule>': row}; the rule is the part after the first '|'"),
                "parse_fail": N(DESC),
                "shapes": N(DESC, "shape sizes; each rule row carries its own n_shape"),
                "distinct_keys": N(DESC),
            },
            "rule": {
                "rate_in_shape": R("share_in_shape", "hits of the shape = round(rate_in_shape x n_shape), summed over the shapes (R-34; the text's reading); 3 decimals", decimals=3),
                "n_shape": R("items_in_shape"),
                "share_of_level": R("alt_recovery_share", "read only for the report: f4b_pool_v2.py recovers hits as round(share_of_level x n); the report lists rules whose decision would change under it", decimals=3, unsure=True),
            },
            "rule_name": {"MF_in_shape_cv": P("shape_rate_row", "R-34 and R-57: an in-shape rate is reported (report_extras.json, rates_within_one_shape_reported_only) and not counted; the row has no share_of_level")},
        },
    },
    "c1_a3": {
        "units": ["C1a", "C1c"],
        "files": "a3/<draw>__alias.json or <draw>__own.json (audit3_c1/a3_shortcuts.py), source 'a3'; a3/run_log.json",
        "scopes": {
            "level": {
                "n": R("items"),
                "MF_cv": R("rule_scalar", "3 decimals", decimals=3),
                "MF_printform_cv": R("rule_scalar", "R-46: its prediction needs no answer (cross-validated), so it counts", decimals=3),
                "MF_shape_cv": R("rule_scalar", "3 decimals", decimals=3),
                "BEST_generic_cv": R("rule_scalar", "3 decimals", decimals=3),
                "S": R("rules_map", "{'<shape>|<rule>': row}"),
                "oracle_any_literal": N(R46, "R-46, named by the ruling: 'any literal in the program equals the answer', counted over the scored items"),
                "BEST_generic_chosen": N(DESC, "names of the generic rules chosen on the folds"),
                "shapes": N(DESC),
                "distinct_keys": N(DESC),
            },
            "S_row": {
                "hit": R("hits", "items on which the rule's answer equals the key; summed over shapes"),
                "applies": N(DESC, "items on which the rule gives an answer; a non-applicable item is a miss and is inside n"),
                "n_shape": P("shape_items", "R-57: items of the shape, reported with the in-shape rates"),
                "rate_in_shape": P("shape_rate", "R-34 and R-57: an in-shape rate, reported and not counted"),
                "ci": N(DESC),
                "share_of_level": N("R-46 note: the shape's share of the level (len(sub) / n), not a hit share; hits are read from hit"),
                "mf_in_shape_cv": P("shape_rate_mf", "R-34 and R-57: an in-shape rate, reported and not counted"),
            },
            "run_log": {
                "alias": N(DESC, "the draw id the wrapper ran under"),
                "alias_rc": R("fallback_status", "alias_rc != 0 means the wrapper fell back to the lineage's own id: reported (K18)"),
                "alias_err": R("fallback_report", "kept in the report, first 300 characters"),
                "own_rc": N(DESC), "own_err": N(DESC),
            },
        },
    },
    "c1_battery": {
        "units": ["C1b"],
        "files": "battery.json (c1_fix4_battery.py), source 'battery'",
        "scopes": {
            "level": {
                "n": R("items"),
                "MF_cv": R("rule_scalar", "3 decimals", decimals=3),
                "BEST_generic_cv": R("rule_scalar", "3 decimals", decimals=3),
                "MF_shape_cv": R("rule_shape_map", "{shape: in-shape cross-validated rate}, shapes of 20 items or more only; hits recovered as round(rate x shapes[shape]) and summed (the text's rule for a share written per shape); 3 decimals; the committed pool script does not read it", decimals=3, unsure=True),
                "shapes": R("shape_sizes", "items per shape, for the recovery of MF_shape_cv"),
                "S": R("rules_map", "{'<shape>|<rule>': row}"),
                "best_generic_in_shape": N(R46, "R-46, named by the ruling: the best generic rule per shape, chosen and scored on the same items"),
                "oracle_any_literal": N(R46, "R-46, named by the ruling"),
                "BEST_generic_chosen": N(DESC),
                "distinct_keys": N(DESC),
                "retries": N(DESC, "retries of the draw"),
            },
            "S_row": {
                "hit": R("hits"),
                "n_shape": P("shape_items", "R-57: items of the shape, reported with the in-shape rates"),
                "rate": P("shape_rate", "R-34 and R-57: an in-shape rate, reported and not counted"),
            },
        },
    },
    "c1_closed": {
        "units": ["C1c"],
        "files": "f5.json and f5b.json (the closed-form scripts), source 'closed forms'",
        "scopes": {
            "lineage": {
                "per_level": R("per_level_shares", "{level: {rule: share of the level}}; 4 decimals; a rule with no hit at a level is not written", decimals=4),
                "n_per_level": R("items_per_level"),
                "errors": N(DESC, "items on which a closed form raised; they stay inside n_per_level as misses"),
            },
        },
    },
}

FILES_NOT_READ = {
    "c1_draw_rows": {"units": ["C1a", "C1c"], "files": "gen/<draw>.jsonl.gz", "fields": ["lid", "lv", "i", "src", "key", "q", "retries", "atype", "fid"], "reason": HELP},
    "c1_s4_records": {"units": ["C1a", "C1c"], "files": "rules/<draw>.jsonl.gz", "fields": ["lid", "lv", "i", "key", "shape", "R", "err"], "reason": HELP},
    "c1_meta": {"units": ["C1a", "C1c"], "files": "gen/meta.json", "reason": HELP},
    "c1_a3_inputs": {"units": ["C1a", "C1c"], "files": "a3/in/<tag>/<name>.jsonl.gz", "reason": HELP},
    "stdout_stderr": {"units": "all but R1c (whose stdout.txt is read)", "files": "*.stdout.txt, *.stderr.txt, stdout.txt, stderr.txt", "reason": "progress and error text; not read, only hashed"},
}


def build() -> dict[str, Any]:
    return {
        "table_kind": "field table of stage 1S point 2 (ADR-0033 addendum 1, approved 2026-11-26); hashed with the pooling script",
        "rulings": {"R-46": "A field is a rule only if its prediction for an item can be computed without that item's answer. oracle_any_literal (both C1 outputs) and best_generic_in_shape (C1 battery) are not read; MF_printform_cv counts; BEST_generic_cv counts; share_of_level in the a3 output is not a hit share and hits are read from hit.",
                    "R-57": "Rates within one shape (C1 rate_in_shape, mf_in_shape_cv, rate, MF_in_shape_cv; the battery's MF_shape_cv per shape; R2 per-shape counts) are written into report_extras.json under rates_within_one_shape_reported_only and enter no decision.",
                    "K7": "M1: keys ending __within_applicable, within_applicable, one_op_best and asked_is_largest_observed_vs_uniform are not rules and are not read."},
        "verification": "names checked against the committed code at b78e58b1 (and the run copies under studies/m0/fresh_run) and against the keys, not the values, of the implementers' dry outputs; fields marked unsure are listed in the report of the task",
        "forms": FORMS,
        "files_not_read": FILES_NOT_READ,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "field_table.json"))
    a = ap.parse_args()
    with open(a.out, "x") as f:
        json.dump(build(), f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote " + a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
