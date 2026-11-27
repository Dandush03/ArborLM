# ruff: noqa: E501
"""Builds the R2 rev2 deliverables: fixtures for the revised shapes (``fixtures/r2_batch1_rev2/``), the schema document, the compact before/after shortcut and capacity tables, and the manifest.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_rev2_build --shortcuts <shortcuts_all.json> --capacity <dir with capacity json files>``.
Nothing here is a result about any model. Self-checked; not independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, build_item, lineages_of, stream
from studies.m0.lineages_r2_clusters import (
    DISAGREEMENTS,
    STRICT_MERGES,
    STRICTEST_EXTRA,
    strict_clusters,
    strictest_clusters,
)
from studies.m0.lineages_r2_common import load_batch1
from studies.m0.lineages_r2_rev2 import FAMILY_RENAME, SUPERSEDES, load_rev2
from studies.m0.r2_rev2_measure import G_WRITTEN, need

ROOT = Path(__file__).resolve().parents[2]
FIX_SEED = 953911

NOT_REGISTERED = {
    "R2.deferred_acceptance_partner": (
        "the audit's tells cannot be removed by construction: with independent uniform preferences 'the responder-proposing stable partner' is right on 0.68-0.77 of items "
        "(the stable matching is usually unique) and 'own first choice' on 0.46-0.56; any preference structure that makes the stable matching non-unique makes the proposer-optimal partner the proposer's "
        "first choice, and any structure that makes first choices collide makes the matching unique. The batch-1 redraw is withdrawn (R-1); n was widened to 4..7. Left out of the registered set until a construction exists."),
}

# what each revised shape changes, per defect (for the manifest)
FIXES = {
    "R2.expression_eval": ("wording R-4", "fixed by construction of the wording: both conventions state that the rule applies inside parentheses; ranked defines + and - as one rank worked left to right; the batch-1 redraw on the other convention's value is removed. The wrong-rule rate (evaluating under the other stated rule) is natural: about 0.8 at level 0 down to 0.4 at level 6, reported, not counted as a cue."),
    "R2.merge_smallest_cost": ("wording R-4 + capacity R-5", "fixed: 'any two piles'; level 0 widened to 5 piles of 1..20"),
    "R2.string_rewrite_nonidentity": ("existing lineage string_rewrite: identity rules", "fixed by construction: each pattern is a substring of the current string and differs from its replacement"),
    "R2.to_base_wide": ("existing lineage to_base: level 0 capacity 755", "fixed: wider bases and n range"),
    "R2.chip_toppling": ("shortcut R-1 (closed forms)", "fixed by dropping `final` and `lost`; new shape `topplings_of` (order-independent per-cell count)"),
    "R2.bracket_match": ("shortcut R-1", "fixed by construction: wrong texts swap the closing kinds of two pairs that enclose something (no adjacent wrong pair possible; counts kept); match asks about an enclosing opener, no exclusion of other partner positions; 3 kinds, 8+level pairs. Residual: 'last closer of the same kind' 0.51 at level 0, falling with level"),
    "R2.coin_change_min": ("shortcut R-1 (greedy, ceil+1)", "fixed by changing the final question to the number of ways (no greedy or bound answers it); wider space for capacity"),
    "R2.hash_probe": ("shortcut R-1", "mostly fixed by construction: m-1 of m slots filled, homes in the first third of the table, asked key uniform. Residual: 'home + earlier keys with the same home' 0.62 at level 0 (0.74-0.82 in batch 1)"),
    "R2.cache_eviction": ("shortcut R-1 (agree logic)", "fixed: `present` is FIFO only with a pool of 2*cap and a uniform asked item; no coupling to a heuristic. Residual: other-policy count 0.59 on `misses` at level 0"),
    "R2.subtraction_game": ("shortcut R-1 (residues, overshoot)", "changed by construction to two piles (a position label per pile, combined by exclusive-or); the heuristic-outcome exclusion is removed; answer balanced 50/50 on the key only. Residual: 'residues of the piles xor' 0.59 at level 0, 'n mod (largest+1)' about 0.5"),
    "R2.deferred_acceptance_partner": ("shortcut R-1", "NOT REGISTERED (see reason)"),
    "R2.cheapest_network": ("shortcut R-1 (level 0 and per-town sums)", "fixed by construction: groups of three towns with a cheap triangle each and dearer cables between groups; n-1 cheapest never right; per-town sums right only by coincidence (under 1%)"),
    "R2.max_subarray_sum": ("shortcut R-1 (best run of non-negative numbers)", "fixed by construction: planted best block across one small dip, strongly negative separators, smaller decoy runs; 'best run' accuracy 0.0"),
    "R2.gcd_euclid": ("shortcut R-1 (common small primes, steps constant)", "fixed by construction: common divisor with no prime factor below 11; steps shape dropped"),
    "R2.modular_power": ("shortcut R-1 (level 0, Fermat)", "fixed by construction: modulus a product of two primes, e at least 2m; 'a^(e mod (m-1))' 0.32 at level 0 (0.70 in batch 1)"),
    "R2.lcs_length": ("shortcut R-1 (answer range)", "partly fixed: planted common subsequence of uniform length, alphabet 4..6, lengths 8+level..14+2*level. Residual: constant guess 0.27 at level 0 (batch 1: 0.29); greedy matching, better of both directions, 0.47 at level 0"),
    "R2.lis_length": ("shortcut R-1 (answer range)", "fixed: planted increasing subsequence of uniform length, random elsewhere, n drawn per item; constant guess at most 0.19 (batch 1: 0.33)"),
    "R2.longest_palindromic_substring": ("shortcut R-1 (mode)", "fixed: planted palindrome 3..12; constant guess at most 0.15 (batch 1: 0.30)"),
    "R2.prime_factor_query": ("shortcut R-1 (largest = pool top) + capacity R-5", "fixed by construction: largest prime uniform over 17..pool, one prime repeated, 4..6 factors; capacity widened"),
    "R2.crt_smallest": ("capacity R-5 (level 1-2 close to the demand)", "widened moduli"),
}


def write_fixtures(lins: list[Lineage], out_dir: Path, per_level: int = 20) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for lin in lins:
        lines = []
        for lv in ALL_LEVELS:
            r = stream(FIX_SEED, "r2-rev2-fixture", lin.id, str(lv))
            for i in range(per_level):
                it = build_item(lin, lv, r, "A", f"{lin.id}/rev2/fixture/{lv}/{i}")
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (out_dir / f"{lin.id}.jsonl").write_text(text)
        hashes[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    return hashes


def write_schema(lins: list[Lineage], path: Path) -> None:
    parts = [
        "# R2 batch 1, revision 2: structured-form schema for the second-solver agent (revised shapes only)\n",
        "Written by the implementer. Not a result; nothing here approves anything. Same interface as `R2_BATCH1_SCHEMA.md` (a solver reads ONLY `structured`; `solve(structured) -> str`; raise `ValueError` when the form has no unique answer).",
        "These shapes SUPERSEDE the batch-1 shapes of the same ids (see `SUPERSEDES` in `studies/m0/lineages_r2_rev2.py`); lineages not listed here are unchanged from batch 1. Fixtures: `studies/m0/fixtures/r2_batch1_rev2/<id>.jsonl`, 20 items per level 0..6.\n",
        "## Revised shapes\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        r = stream(FIX_SEED, "r2-rev2-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append(f"### `{lin.id}` (family {lin.family}; supersedes {SUPERSEDES[lin.id]})\n\n{doc}\n")
        parts.append("Example (level 2):\n\n```\nquestion: " + it.question + "\nstructured: " + json.dumps(it.structured, sort_keys=True) + f"\nanswer: {it.answer}\n```\n")
    path.write_text("\n".join(parts))


def compact_shortcuts(path: Path) -> dict[str, Any]:
    res = json.loads(path.read_text())
    out: dict[str, Any] = {"seed": res["seed"], "lineages": {}}
    for lid, rec in sorted(res["lineages"].items()):
        o: dict[str, Any] = {"revised": rec["revised"]}
        for tag in ("before", "after"):
            if tag not in rec:
                continue
            lv_rows = {}
            for lv, d in rec[tag]["levels"].items():
                row = {}
                for sh, sd in d["shapes"].items():
                    hs = sd["heuristics"]
                    top = max(hs.items(), key=lambda kv: kv[1]["acc"]) if hs else ("", {"acc": 0.0})
                    row[sh] = {"chance": sd["chance"], "mode_key_share": sd["mode_key_share"], "worst_heuristic": top[0], "worst_acc_two_sided": top[1]["acc"], "items": sd["items"]}
                lv_rows[lv] = row
            o[tag] = {"worst_heuristic": rec[tag]["worst_heuristic"], "worst_mode": rec[tag]["worst_mode"], "per_level_and_shape": lv_rows}
        out["lineages"][lid] = o
    return out


def md_table(comp: dict[str, Any]) -> str:
    lines = ["# R2 rev2: worst two-sided shortcut accuracy per lineage, before (batch-1 shapes) and after (rev2 shapes)\n",
             "Per level, two-sided (yes/no read as max(acc, 1-acc)), auditor's battery plus the author's, 2,000 items per level (seed 953901). Measured, not thresholded. 'before' is shown for lineages whose shape changed; 'after' for all.\n",
             "| Lineage | state | worst heuristic (acc, its chance, level, name) | worst constant key (share, chance, level) |", "|---|---|---|---|"]
    for lid, rec in comp["lineages"].items():
        for tag in ("before", "after"):
            if tag not in rec:
                continue
            w, m = rec[tag]["worst_heuristic"], rec[tag]["worst_mode"]
            lines.append(f"| {lid} | {tag} | {w['acc']:.3f} / {w['chance']:.2f} / L{w['level']} / {w['name'][:60]} | {m['share']:.3f} / {m['chance']:.2f} / L{m['level']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shortcuts", type=Path, required=True)
    ap.add_argument("--capacity", type=Path, nargs="+", required=True, help="capacity json files (later files override earlier ones)")
    a = ap.parse_args()
    rev2 = load_rev2()
    fx = write_fixtures(rev2, ROOT / "studies" / "m0" / "fixtures" / "r2_batch1_rev2")
    write_schema(rev2, ROOT / "studies" / "m0" / "fixtures" / "R2_BATCH1_REV2_SCHEMA.md")
    comp = compact_shortcuts(a.shortcuts)
    (ROOT / "studies" / "m0" / "manifests" / "r2_rev2_shortcuts.json").write_text(json.dumps(comp, indent=1, sort_keys=True))
    (ROOT / "studies" / "m0" / "manifests" / "r2_rev2_shortcuts_table.md").write_text(md_table(comp))
    cap: dict[str, Any] = {}
    for f in a.capacity:
        cap.update(json.loads(f.read_text())["lineages"])
    failing = {lid: [(r["level"], r["found_structural"], r["need"]) for r in rec["after"]["rows"] if not r["passed"]] for lid, rec in sorted(cap.items()) if rec["after"]["levels_failed"]}
    sc, st = strict_clusters(), strictest_clusters()
    manifest = {
        "batch": "r2_batch1_rev2",
        "note": ("Fix round after AUDIT_M0_R2_1 under LEAD_RULINGS_2 (R-1 shortcuts by construction, R-4 wording, R-5 structural capacity). No new lineages. Revised SHAPES in studies/m0/lineages_r2_rev2.py (own registry REV2); batch-1 shapes stay on file, "
                 "superseded where listed. Self-checked only: not independent review, not Astra validation, not human approval. Nothing is registered in core.REGISTRY."),
        "superseded_shapes": {lid: SUPERSEDES[lid] for lid in sorted(SUPERSEDES)},
        "revised_shapes": [{"id": x.id, "family_reported": x.family, "supersedes": SUPERSEDES[x.id], "defect_and_fix": FIXES.get(x.id), "fixture_sha256": fx[x.id]} for x in rev2],
        "not_registered": NOT_REGISTERED,
        "family_rename_in_rev2": FAMILY_RENAME,
        "capacity": {
            "reading": "R-5: distinct canonical STRUCTURED forms (names relabelled by first appearance, presentation order dropped where the answer does not depend on it); lower bound from 2*need+1000 draws",
            "G": G_WRITTEN,
            "G_derivation": "the auditor's strict map has 38 clusters over the 42 R2 lineages (lineages_r2_clusters.strict_clusters); two parts of 19 clusters each",
            "demand_rule": f"core level: 10 x (ceil(24,000 / G) + 100) = {need(1)}; reserve level: 10 x 100 = {need(0)} (ADR-0033 section 6.2, same arithmetic as lineage_gates.demand_at_g with G = 19 instead of 300)",
            "levels_failing_after": failing,
            "per_lineage": {lid: {"revised": rec["revised"], "levels_failed_after": rec["after"]["levels_failed"], "levels_failed_before": rec.get("before", {}).get("levels_failed")} for lid, rec in sorted(cap.items())},
        },
        "clusters": {"strict_count": len(sc), "strictest_count": len(st), "strict_merges": [list(g) for g in STRICT_MERGES], "strictest_extra": [list(g) for g in STRICTEST_EXTRA], "disagreements": DISAGREEMENTS},
        "existing_not_edited": sorted(x.id for x in lineages_of("R2")),
        "batch1_ids": sorted(x.id for x in load_batch1()),
    }
    (ROOT / "studies" / "m0" / "manifests" / "r2_rev2_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"revised": len(rev2), "failing_capacity": failing, "strict": len(sc), "strictest": len(st)}))


if __name__ == "__main__":
    main()
