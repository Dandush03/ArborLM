# ruff: noqa
"""Final M1 audit: assemble final_m1.json and the per-lineage markdown table from the outputs in this directory. Standard library only."""
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
k1 = json.load(open(H / "keys_n500.json"))
k2 = json.load(open(H / "keys_n1000_seed2611257_h1.json"))
pool = json.load(open(H / "pooled_a5.json"))["results"]
lev = json.load(open(H / "levels_a5.json"))
cap = json.load(open(H / "capacity_summary.json"))
casc = json.load(open(H / "cap_cascade.json"))
REPAIRED = {"M1.mixture_r4", "M1.gcd_lcm_r4", "M1.finite_differences_r4", "M1.average_missing_r4", "M1.clock_duration_r4"}


def stem(lid):
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        s = s.removesuffix(suf)
    return s


rows = {}
for lid in sorted(pool):
    n = mm = amb = err = 0
    for kk in (k1, k2):
        for L in range(7):
            r = kk["results"][lid][str(L)]
            n += r["N"]; mm += r["mismatch"]; amb += r["no_unique_answer"]; err += r["solver_error"]
    p = pool[lid]
    lv = lev[lid]
    pl = cap["per_lineage"][lid]
    aw = cap["as_written"]
    hyp = cap["hypothetical_per_cluster"]
    cl = pl["cluster"]
    hyp_fail = {}
    for key in ("text", "a4key"):
        for g in (8, 7):
            f = hyp[f"{key}/G={g}"]["clusters"][cl]["fails"]
            hyp_fail[f"{key}/G={g}"] = {b: v for b, v in f.items() if v}
    rows[lid] = {
        "cluster": cl, "repaired_in_fix4": lid in REPAIRED,
        "keys": {"items": n, "mismatches": mm, "solver_errors": err, "seeds": [k1["seed"], k2["seed"]]},
        "no_unique_answer": {"items": amb, "of": n, "share": amb / n},
        "rules_pooled": {"largest_counted": p["largest_counted"], "per_level_counted": [p["per_level"][str(L)]["counted_max_pooled"] for L in range(7)],
                         "verdict_at_0.15": p["verdict"], "largest_not_counted": p["largest_notcounted"], "would_drop_if_not_counted_counted": p["would_drop_if_notcounted_counted"],
                         "largest_new_fresh_only": p["largest_new"], "would_drop_on_new": p["would_drop_on_new"]},
        "levels": {"identical_level_pairs": lv["identical_level_pairs"], "stated_parameter": lv["stated_parameter"], "stated_observed_max": lv["stated_observed_max"],
                   "stated_strictly_rising": lv["stated_strictly_rising"], "mean_log10_answer": [lv["profile"][str(L)]["mean_log10_answer"] for L in range(7)],
                   "adjacent_pairs_features_differing": lv["adjacent_pairs_features_differing"]},
        "capacity": {"part": pl["part"], "n_eff_text": pl["n_eff_text"], "n_eff_a4key": pl["n_eff_a4key"], "n_eff_struct": pl["n_eff_struct"],
                     "as_written_fail_levels": {f"{key}/{rd}": aw[f"{key}/{rd}"]["fails"].get(lid, []) for key in ("text", "a4key") for rd in ("own_part_count", "smaller_part_decides", "own_part_count_minus_1", "cluster_demand_G_per_lineage", "cluster_demand_G_minus_1_per_lineage")},
                     "hypothetical_cluster_builder_fails": hyp_fail},
    }
surv = sorted(rows)
clusters = sorted({r["cluster"] for r in rows.values()})
final = {"title": "M0-M1 final independent re-measurement after fix 4 (auditor: arbor-auditor, Claude Opus 5.5). Not Astra validation, not human approval, not a registration.",
         "astra_review": "NOT_PERFORMED", "bound": 0.15, "lineages": rows,
         "rule_verdict": {"stays": [l for l in surv if rows[l]["rules_pooled"]["verdict_at_0.15"] == "STAYS"], "drops": [l for l in surv if rows[l]["rules_pooled"]["verdict_at_0.15"] == "DROPS"]},
         "clusters_after_rules": clusters, "cluster_count_after_rules": len(clusters), "G": cap["G"], "demand_G": cap["demands"],
         "as_written_summary": {k: {"failing": sorted(v["fails"]), "clusters_left_single_pass": v["clusters_remaining_if_failing_dropped"]} for k, v in cap["as_written"].items()},
         "as_written_cascade": {k: {"lineages_left": v["lineages_left"], "cluster_count": v["cluster_count"], "clusters_lost": sorted(set(clusters) - set(v["clusters_left"]))} for k, v in casc.items()},
         "held_R36_confirmed_a4key_own_part": sorted(cap["as_written"]["a4key/own_part_count"]["fails"]),
         "not_counted_rule_judgements": {
             "consecutive": "im:mean_plus_step: the procedure for 3 numbers (L0-1, +0.49/+0.50); at L2-3 (4 numbers) a wrong rule right by round-half-even coincidence, +0.12/+0.13 (under 0.15); 0 at L4-6. Agree: not a shortcut.",
             "division_counting": "k - (N mod k): the procedure without the exact-fit case; 96-97 % right within the bus items. Agree: not a shortcut.",
             "finite_differences": "next_term_when_asked_later: one extension of the difference table, 100 % within m+1 asks at L0-4 (degree 2); 0 % at L5-6 (degree 3). Agree: the procedure.",
             "gcd_lcm": "product_over_gcd_of_all (k = 2): the textbook lcm, agree. The k >= 3 false general rules are exact on 100 % of items at L3-6 (+0.47 to +0.49 pooled): not cheaper than the procedure, but a construct-validity issue left unrepaired; PENDING LEAD REVIEW.",
             "prime_factors": "largest_le_sqrt: needs trial division to sqrt(n); 87-99 % within the 'largest' ask, rising with level (the large-cofactor case almost never occurs). Agree: procedure; construct note.",
             "ratio_share": "largest/smallest share: a person guess plus the full procedure; observed P(asked = largest-part holder) equals the uniform expectation (L0 0.525 vs 0.531, L6 0.285 vs 0.282). Agree: not a shortcut. My NEW first/last-named rules are the same class (+0.53 at L0-1)."},
         "discrepancies": [
             "Implementer's raw battery: 3,190 values recomputed at their seeds, 0 differences (after my attempt-1 tie-order error, 1 difference, fixed).",
             "As-written failing list on the audit-4 key: the implementer's eight lineages and failing levels reproduced exactly at a fresh seed.",
             "Capacity unit: on the TEXT key (what draw_items de-duplicates) only consecutive (L0-1), percent_change (L0-1) and rectangle (L0-6) fail; the eight are on the audit-4 structural key. Which unit counts is not ruled: PENDING LEAD REVIEW.",
             "R-30 'smaller part decides' read for the as-written per-lineage demand (18,150 in both parts instead of 17,010 in part B) adds tip_split L0 (17,617) to the failures on every key; then all four S3 members fail.",
             "Dropping the eight changes the part sizes; iterated to a fixed point tip_split and mixture also fail: 19 lineages, 16 clusters (S3 lost) on the audit-4 key, own-part reading. The implementer's single-pass count is 17.",
             "Hypothetical per-cluster builder, G = 8: prime_factors L0 Chao1 30,913 < 31,000 at my seed (theirs 31,275, pass); n_eff 31,093 (pass by 0.3 %); audit 4 exact 31,236. At the edge of sampling noise. At G = 7 prime_factors fails on all bases.",
             "gcd_lcm mean log10 answer dips L2 -> L3 at my seed too (2.923 -> 2.745; theirs 2.833 -> 2.813); the stated ceiling and the observed max rise; the gcd-ask cap falls from 60 to 24 at L3.",
             "Audit 4's PROC list contains im:next_term_only although its reason says 'kept as a rule'; pooled value about -0.002, no consequence.",
             "Fixtures: studies/m0/fixtures/m1_fix3 still holds coins_r3, pigeonhole_worst_case_r3, mode_tally_r3 and the r3 versions of the six replaced lineages; no fix-4 fixture set exists (disclosed by the implementer).",
             "core.generate_pool as written cannot pool the survivors at all: part_lineages reads core.REGISTRY['M1'] (16 batch-1 lineages, no fix-3/fix-4 id). The as-written capacity is a simulation of its allocation rule.",
             "The worktree HEAD moved during this audit (commit 7cd0ac5a at 22:33:58 by another session, adding the fix-4 files); every input file's mtime precedes the start of this audit (22:17), so the audited bytes are the committed bytes."],
         "not_verified": ["exact support (only sampled n_eff and Chao1)", "model behaviour of any kind", "difficulty for a reader across levels", "the M0 test suite (not run by me)", "the cross-evaluation map", "fixture hashes"]}
json.dump(final, open(H / "final_m1.json", "w"), indent=1, sort_keys=True)


def fl(v):
    return "pass" if not v else "L" + ",".join(map(str, v))


print("| lineage | cluster | key mismatches / n | no unique answer | largest pooled excess (rule, level) | verdict 0.15 | levels: identical pairs; stated parameter max rising | as written, text key (own part / smaller part) | as written, audit-4 key (own part / smaller part) | per-cluster builder (hypothetical), G=8 text / a4key |")
print("|---|---|---|---|---|---|---|---|---|---|")
for lid in surv:
    r = rows[lid]
    lc = r["rules_pooled"]["largest_counted"]
    c = r["capacity"]["as_written_fail_levels"]
    h8t = r["capacity"]["hypothetical_cluster_builder_fails"]["text/G=8"]
    h8a = r["capacity"]["hypothetical_cluster_builder_fails"]["a4key/G=8"]
    hs = lambda h: "pass" if not h else "; ".join(f"{b} {fl(v)}" for b, v in h.items())
    print(f"| `{stem(lid)}`{' (r4)' if r['repaired_in_fix4'] else ''} | {r['cluster']} | {r['keys']['mismatches']} / {r['keys']['items']:,} | {r['no_unique_answer']['items']} / {r['no_unique_answer']['of']:,} | {lc[0]:+.3f} ({lc[1]}, L{lc[2]}) | {r['rules_pooled']['verdict_at_0.15']} | "
          f"{'none' if not r['levels']['identical_level_pairs'] else r['levels']['identical_level_pairs']}; {'yes' if r['levels']['stated_strictly_rising'] else 'see note'} | "
          f"{fl(c['text/own_part_count'])} / {fl(c['text/smaller_part_decides'])} | {fl(c['a4key/own_part_count'])} / {fl(c['a4key/smaller_part_decides'])} | {hs(h8t)} / {hs(h8a)} |")
