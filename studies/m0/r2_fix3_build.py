# ruff: noqa: E501
"""Builds the R2 fix-round-3 deliverables: fixtures for the revised shapes (``fixtures/r2_fix3/``), the schema document, the before/after shortcut table, the capacity table, the strict cluster map and the manifest.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix3_build --before BAT_CURRENT.json --after BAT_FIX3.json --capacity CAP.json``.
Seeds: fixtures use the throwaway integer 953922 with text labels. Nothing here is a result about any model; nothing is registered in ``core.REGISTRY``. Self-checked; not independent review, not Astra, not human approval.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, build_item, stream
from studies.m0.lineages_r2_fix3 import SUPERSEDES, load_fix3
from studies.m0.r2_fix3_battery import is_p
from studies.m0.r2_fix3_capacity import summarise as capacity_summary
from studies.m0.r2_fix3_clusters import (
    BORDERLINE_GROUPS,
    STRICT_MERGES,
    clusters,
    cross_eval_for_cluster,
    demand,
    part_sizes,
)
from studies.m0.r2_fix3_set import NOT_REGISTERED, fix3_set

ROOT = Path(__file__).resolve().parents[2]
FIX_SEED = 953922
G = 17

DROPPED_SHAPES = {
    "R2.binary_search_trace": "`third` (its answer is one of about four values at fixed fractions of the list; the 1/8-7/8 position rule read 0.21-0.32 whatever the construction)",
    "R2.cellular_automaton": "`count` (a handful of answers; constant guess 0.24)",
    "R2.hash_probe": "`slot` and `probes` (single-key answers: 0.4-0.57 with spread homes, 0.73-0.98 with the round-2 near-full table)",
    "R2.cache_eviction": "`misses` (small answer, the other policy's count 0.42-0.60) and `present` (yes/no read off the last requests, 0.85-0.91)",
    "R2.bracket_match": "`valid` (a partial pair check reads 0.5 + half its coverage: 0.79-0.84) and `match` (one of about twenty positions; 'last/next same-kind closer' 0.35-0.51)",
    "R2.count_divisible": "`count` (small answers: constant guess 0.23, the estimate (numbers over t) // m 0.26)",
    "R2.interval_scheduling": "the count answer (a small number: constant guess 0.2-0.35)",
    "R2.coin_change_min": "the single-amount question and round 2's `ways` question (duplicated M1.change_ways and C1.coin_change_table)",
    "R2.subtraction_game": "the two-pile shape (win/lose-of-each-pile rule 0.79-0.82)",
    "R2.chip_toppling": "all shapes (NOT REGISTERED)",
}

FIXES: dict[str, tuple[str, str]] = {
    "R2.interval_scheduling": ("R-1 redraw on 'earliest start' and 'shortest first' (fitted 0.8); count answer", "no redraw; 5 + level//2 independent time blocks of 4-6 meetings, shuffled numbering, answer = the list of meetings chosen by the stated earliest-finish rule"),
    "R2.binary_search_trace": ("R-1 redraw on 'third = target' (fitted 0.8); 'third' position rules", "no redraw; `third` dropped; list of 16 + 4*level numbers (2^k - 1 stepped over); fair-coin absent target; shapes `values` and `sum` of the looks"),
    "R2.bst_traversal": ("R-1 rejection of answers equal to the insertion or sorted order", "no rejection; n = 8 + level (the chance of an equal walk is the Catalan number over n!, 0.035 at n = 8)"),
    "R2.min_heap_ops": ("R-1 rejection of answers equal to the insertion or sorted order", "no rejection; n = 10 + level"),
    "R2.cellular_automaton": ("R-1 rejection of final = start, all-equal final, table 000 -> 1; closed-boundary reading; `count` shape", "no such rejection; end cells fixed to 1, 2 + level//2 steps, mirror-image triples drawn different, `count` dropped, 11 + 2*level cells; only constant tables retried (validity)"),
    "R2.dictionary_rank": ("R-1 redraw on rank 1 or last; capacity under letter relabelling (46-1,436 structures)", "no redraw; words of `length` different letters taken from an alphabet of 8-11 letters (draw per item), widened so the letter-blind space exceeds the demand at every level"),
    "R2.run_length": ("capacity under letter relabelling (54 and 1,280 at levels 0 and 1)", "6 + level runs of length 1 .. 4 + level//2, each run's letter drawn from the six letters other than the previous one"),
    "R2.hash_probe": ("shortcut: block-start rule 0.95-0.98, len(keys) - home 0.86-0.94, max(home, min home + index) 0.73-0.83", "answers are about the whole table (`table`, `checksum`); homes spread over the table; round(0.7 m) numbers"),
    "R2.cache_eviction": ("shortcut: 'among the last cap distinct requests' 0.88-0.91; other policy 0.42-0.60", "answers are lists (`evicted`, `contents` FIFO only); sequences start with cap + 1 different items and then mix hits on cached items with draws"),
    "R2.bracket_match": ("shortcut: top-level pairs only 0.79-0.84; last/next same-kind closer 0.35-0.51", "shapes `match_all` (closers of every opener of one kind) and `first_error` (two nested pairs with swapped closers); 14 + level pairs, kinds shared evenly"),
    "R2.expression_eval": ("wrong-rule agreement 0.3-0.9 left 'natural' in rev2", "the structure that makes each misreading differ is planted: a later product term, a parenthesised sum inside a product, '-' directly before '+' (ranked); '+'/'-' directly before '*', a parenthesised chain with the same pattern (left_to_right)"),
    "R2.subtraction_game": ("shortcut: win/lose-of-each-pile rule 0.79-0.82", "four piles, 5-6 allowed amounts; key balanced 50/50 (on the key only)"),
    "R2.cheapest_network": ("shortcut: grouped-triangle template read 1.00 at levels 0-2", "towns are grid points, a cable costs the walking distance, the 2n shortest pairs are offered; n = 8 + level//2"),
    "R2.max_subarray_sum": ("shortcut: planted +++ - +++ block, best window of 7 and two-run rule 1.00", "2U + 1 alternating falling/rising phases of random length (rising phases alternate a positive number and a dip); the row starts and ends with a falling phase"),
    "R2.coin_change_min": ("round-2 fix asked for the number of ways (duplicate of M1.change_ways_r2 and C1.coin_change_table); batch-1 greedy / ceil+1 tells", "fewest coins restored, for each of FIVE amounts as a list; no coin 1; amounts drawn among the payable ones"),
    "R2.lcs_length": ("shortcut: greedy matching 0.46 at level 0, constant guess 0.26", "longer strings (15 + 2*level .. 21 + 3*level), alphabet 8-12, plant at least 35% of the shorter length"),
    "R2.gcd_euclid": ("shortcut: g always prime at levels 0-2, 'smallest common prime factor' 1.00", "g drawn among the non-squarefree numbers; cofactors at least 5"),
    "R2.multiples_between": ("shortcut: b//m - a//m 0.87-0.89, round((b-a+1)/m) 0.75 (end-offset family, not removable for random ends)", "both ends are multiples of m; shapes `count` and `sum`; widened for capacity"),
    "R2.count_letter": ("shortcut: 'words containing the letter' 0.69-0.88; constant 0.59 at level 0", "one word holds the letter exactly twice (planted); per-item chance spreads the totals; 8 + 2*level words"),
    "R2.count_divisible": ("shortcut: '>= t' 0.98-0.99, 'ignore > t' 0.65-0.74, constant 0.47", "t is a multiple of m and planted in the list; `count` dropped, question is the sum; 18 + 4*level numbers"),
    "R2.palindrome_check": ("shortcut: 'at most one odd count' 0.96", "a 'no' text is a palindrome with two letters swapped (same letter counts); 12 + level letters per half"),
    "R2.stack_machine": ("shortcut: 'last pushed value' 0.41-0.59 (exact when the last step is a push); constant 0 at 8-11% (dup, sub)", "the final step is always add, multiply or subtract; no subtraction directly after a duplication; values 1..20"),
    "R2.permutation_power": ("shortcut: 'the start' 0.29-0.52, 'one application' 0.30-0.53, 't mod n' up to 0.83", "n = 12 + level numbers, one long cycle of n - a numbers (a coprime to n), start inside it, t 30 .. 90 + 10*level"),
    "R2.prime_factor_query": ("capacity at level 0 under the reserve-at-core-demand reading (about 4,029)", "level 0 widened to 5 factors from the primes up to 79"),
}


def write_fixtures(lins: list[Lineage], out_dir: Path, per_level: int = 20) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for lin in lins:
        lines = []
        for lv in ALL_LEVELS:
            r = stream(FIX_SEED, "r2-fix3-fixture", lin.id, str(lv))
            for i in range(per_level):
                it = build_item(lin, lv, r, "A", f"{lin.id}/fix3/fixture/{lv}/{i}")
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (out_dir / f"{lin.id}.jsonl").write_text(text)
        hashes[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    return hashes


def write_schema(lins: list[Lineage], path: Path) -> None:
    parts = [
        "# R2 fix round 3: structured-form schema for the second-solver agent (revised shapes only)\n",
        "Written by the implementer. Not a result; nothing here approves anything. Same interface as `R2_BATCH1_SCHEMA.md`: a solver reads ONLY `structured`; `solve(structured) -> str`; raise `ValueError` when the form has no unique answer.",
        "These shapes SUPERSEDE the earlier shapes of the same ids (see `SUPERSEDES` in `studies/m0/lineages_r2_fix3.py`). Fixtures: `studies/m0/fixtures/r2_fix3/<id>.jsonl`, 20 items per level 0..6.\n",
        "## Revised shapes\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        r = stream(FIX_SEED, "r2-fix3-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append(f"### `{lin.id}` (family {lin.family}; supersedes {SUPERSEDES[lin.id]})\n\n{doc}\n")
        parts.append("Example (level 2):\n\n```\nquestion: " + it.question + "\nstructured: " + json.dumps(it.structured, sort_keys=True) + f"\nanswer: {it.answer}\n```\n")
    path.write_text("\n".join(parts))


def level_stats(res: dict[str, Any]) -> dict[str, Any]:
    """Per lineage and level: max over shapes of the worst cue (excluding (P) rules), of the most-frequent-answer rule, and of the (P) rules."""
    out: dict[str, Any] = {}
    for lid, lv in res.items():
        rec: dict[str, Any] = {"cue": [0.0] * 7, "cue_rule": [""] * 7, "mode": [0.0] * 7, "p": [0.0] * 7}
        for lvs, rows in lv.items():
            i = int(lvs)
            for sh, e in rows.items():
                for hn, v in e["heur"].items():
                    ef = round(v["effect"], 3)
                    if hn.startswith("most frequent"):
                        rec["mode"][i] = max(rec["mode"][i], ef)
                    elif is_p(hn, sh, lid):
                        rec["p"][i] = max(rec["p"][i], ef)
                    elif ef > rec["cue"][i]:
                        rec["cue"][i], rec["cue_rule"][i] = ef, f"[{sh}] {hn}"
        out[lid] = rec
    return out


def _f(xs: list[float]) -> str:
    return " ".join(f"{x:.2f}" for x in xs)


def table_md(before: dict[str, Any], after: dict[str, Any]) -> str:
    lines = ["# R2 fix round 3: worst two-sided cheap-rule effect per lineage and level, before and after (measured, 2,000 items per level and shape draw; not thresholded)\n",
             "Effect = accuracy for open answers (chance 0), |accuracy - 0.5| for yes/no. 'cue' excludes the valid-alternative (P) rules and the most-frequent-answer rule (the 'mode' column). 'before' = the shape held by the registries before this round, measured with the auditor's battery only; 'after' = this round, auditor's battery plus this round's own rules. The lead's +-0.10 is a working target, not a registered bound.\n",
             "| Lineage | state | cue L0..L6 | mode L0..L6 | (P) max | worst rule after (level) |", "|---|---|---|---|---|---|"]
    for lid in sorted(after):
        b, a = before.get(lid), after[lid]
        lv = max(range(7), key=lambda i: a["cue"][i])
        if b is not None:
            lines.append(f"| {lid} | before | {_f(b['cue'])} | {_f(b['mode'])} | {max(b['p']):.2f} | |")
        lines.append(f"| {lid} | after | {_f(a['cue'])} | {_f(a['mode'])} | {max(a['p']):.2f} | {a['cue_rule'][lv][:90]} (L{lv}) |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--capacity", type=Path, required=True)
    a = ap.parse_args()
    lins = [x for x in load_fix3() if x.id not in NOT_REGISTERED]
    fx = write_fixtures(lins, ROOT / "studies" / "m0" / "fixtures" / "r2_fix3")
    write_schema(lins, ROOT / "studies" / "m0" / "fixtures" / "r2_fix3" / "R2_FIX3_SCHEMA.md")
    before = level_stats(json.loads(a.before.read_text())["lineages"])
    after = level_stats(json.loads(a.after.read_text())["lineages"])
    man = ROOT / "studies" / "m0" / "manifests"
    (man / "r2_fix3_shortcuts.json").write_text(json.dumps({"before": before, "after": after, "n_per_level_and_shape": json.loads(a.after.read_text())["n"]}, indent=1, sort_keys=True))
    (man / "r2_fix3_shortcuts_table.md").write_text(table_md(before, after))
    capd = json.loads(a.capacity.read_text())
    ctext, cdata = capacity_summary(capd, G)
    (man / "r2_fix3_capacity.json").write_text(json.dumps({"G": G, "demand": demand(G), "draws_per_lineage_level": capd["draws"], "readings": {"A": "names, settings and order relabelled", "B": "labels and letters also relabelled"}, "per_cluster_level": cdata["table"], "failing": cdata["fails"], "per_lineage": {lid: {lv: {k: v for k, v in row.items() if k in ("A", "B")} for lv, row in rec.items()} for lid, rec in capd["lineages"].items()}}, indent=1, sort_keys=True))
    (man / "r2_fix3_capacity.txt").write_text(ctext + "\n")
    cl = clusters()
    cmap = {
        "source": "AUDIT3_R2.md section 2 (strict map, four merges); deferred_acceptance_partner and chip_toppling excluded (R-12)",
        "cluster_count": len(cl),
        "strict_merges": [list(g) for g in STRICT_MERGES],
        "borderline_groups_not_merged": [list(g) for g in BORDERLINE_GROUPS],
        "parts_if_split_evenly": list(part_sizes()),
        "G_used": G,
        "demand_per_cluster_level": demand(G),
        "excluded": NOT_REGISTERED,
        "clusters": {k: {"members": list(v), "other_evaluations_sharing_the_algorithm": cross_eval_for_cluster(k)} for k, v in cl.items()},
    }
    (man / "r2_fix3_cluster_map.json").write_text(json.dumps(cmap, indent=1, sort_keys=True))
    unchanged = sorted(set(fix3_set()) - {x.id for x in lins})
    manifest = {
        "batch": "r2_fix3",
        "note": ("Fix round 3 after AUDIT3_R2 under LEAD_RULINGS_2 and LEAD_RULINGS_3 (R-1 by construction, R-4 wording, R-5 structural capacity, R-10 reserve levels at the core demand, R-11 demand formula, R-12 exclusion, R-13). No new lineages. "
                 "Revised SHAPES in studies/m0/lineages_r2_fix3*.py (own registry FIX3); earlier shapes stay on file, superseded where listed. Self-checked only: not independent review, not Astra validation, not human approval. Nothing is registered in core.REGISTRY."),
        "revised_shapes": [{"id": x.id, "family_reported": x.family, "supersedes": SUPERSEDES[x.id], "defect": FIXES[x.id][0], "fix": FIXES[x.id][1], "dropped_shapes": DROPPED_SHAPES.get(x.id), "fixture_sha256": fx[x.id]} for x in lins],
        "not_registered": NOT_REGISTERED,
        "unchanged_in_the_set": unchanged,
        "set_size": len(fix3_set()),
        "clusters": {"strict_count": len(cl), "map_file": "r2_fix3_cluster_map.json"},
        "capacity": {"G": G, "demand": demand(G), "files": ["r2_fix3_capacity.json", "r2_fix3_capacity.txt"], "failing_A": cdata["fails"]["A"], "failing_B": cdata["fails"]["B"]},
        "shortcuts": {"files": ["r2_fix3_shortcuts.json", "r2_fix3_shortcuts_table.md"]},
    }
    (man / "r2_fix3_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"revised": len(lins), "set": len(fix3_set()), "clusters": len(cl), "failing_A": len(cdata["fails"]["A"]), "failing_B": len(cdata["fails"]["B"])}))


if __name__ == "__main__":
    main()
