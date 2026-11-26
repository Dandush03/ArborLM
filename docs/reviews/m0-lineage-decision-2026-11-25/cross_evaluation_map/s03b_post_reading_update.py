# ruff: noqa
"""Cross-evaluation map (M0), step 2b: changes made AFTER reading the audit3/audit4 overlap lists and the fix-4 notes.
The judgement made before reading is kept unchanged in judgement_before_reading_notes_or_audit_overlap_lists.json (SHA-256 in
judgement_before_reading.sha256). This script adds, never edits: one pair (B16, through an unregistered member of a surviving
cluster), the audits' grades beside mine where they differ, and links through unregistered lineages named by the audits that this
auditor did not render. Standard library only.

Run: python s03b_post_reading_update.py   (reads and rewrites cross_evaluation_procedures_proposed.json in this folder)
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRE = HERE / "judgement_before_reading_notes_or_audit_overlap_lists.json"
OUT = HERE / "cross_evaluation_procedures_proposed.json"

doc = json.loads(PRE.read_text())
doc["judgement_before_reading_sha256"] = hashlib.sha256(PRE.read_bytes()).hexdigest()
doc["pairs"].append({
    "id": "B16", "a": ["M1", "S7_step_rule"], "b": ["C1", "B1"], "grade": "BORDERLINE", "added_after_reading": True,
    "lineages_compared": "M1.arithmetic_series_r3 ~ C1.loop_sum (NOT REGISTERED; still a member of C1 cluster B1 in c1_fix4_survivors.json removed_member_of_a_standing_cluster)",
    "reason": "For: loop_sum sums an affine function over an arithmetic range (audit 4 C1: arithmetic-series closed form 1.000), and M1's own map and audit 4 C1 call it strong. "
              "Against: its modulus filter and mixed-sign updates make it B1's filter-accumulate loop more than a plain series; implementer's C1 map and audit 4 M1 call it medium. "
              "It matters because the addendum's graph has unregistered nodes: a link from an unregistered member of a surviving cluster joins that whole cluster."})
doc["audit_grades_where_they_differ"] = [
    {"pair": "B14 (M1.S7 ~ C1.B6)", "mine": "BORDERLINE", "audits": "STRONG in audit3_m1, audit4_m1, audit4_c1 and the C1 implementer map", "sensitivity": "s04_recompute_sensitivity_B14_strong.out.txt"},
    {"pair": "B16 (M1.S7 ~ C1.B1 via C1.loop_sum)", "mine": "BORDERLINE (added after reading)", "audits": "STRONG in M1's map and audit4_c1; medium in audit4_m1 and the C1 implementer map", "sensitivity": "s04_recompute_sensitivity_B16_strong.out.txt"},
    {"pair": "R2.list_ops ~ C1.B3", "mine": "considered, not linked", "audits": "medium in audit4_r2, audit3_c1 and the C1 implementer map", "sensitivity": "not run"},
    {"pair": "B4, B5, B6, B7, B11, B15 (mine)", "mine": "BORDERLINE", "audits": "not listed by any audit", "sensitivity": "reading 2"},
]
doc["unregistered_links_from_audits_not_rendered_here"] = [
    {"unregistered": "R1.activity_selection_r5", "survivor_cluster": "R2.interval_scheduling", "audit_grade": "strong (audit3_r2, audit4_r2)"},
    {"unregistered": "R1.mst_cost_r4", "survivor_cluster": "R2.cheapest_network", "audit_grade": "strong (audit3_r2, audit4_r2)"},
    {"unregistered": "R1.containers_queue_line_r5", "survivor_cluster": "R2.list_ops", "audit_grade": "strong (audit3_r2) / medium (audit4_r2); the r5 builder is a queue simulation (read here), not Josephus"},
    {"unregistered": "R1.equivalence_classes_r5 / R1.road_reachability_r5 (dropped cluster R1.categories_follow)", "survivor_cluster": "C1.union_find_links (medium, audit4_c1)", "audit_grade": "medium"},
    {"unregistered": "R2.permutation_power (in R2's modular_power cluster)", "survivor_cluster": "M1.last_digit_power via R2.modular_power", "audit_grade": "R2 map merge"},
    {"unregistered": "C1.bubble_pass (dropped)", "survivor_cluster": "R2.sort_list cluster; M1.median_list", "audit_grade": "medium"},
    {"unregistered": "R2.multiples_between (dropped)", "survivor_cluster": "M1.division_counting", "audit_grade": "weak/borderline"},
    {"unregistered": "M1.mode_tally_r3 (dropped)", "survivor_cluster": "C1.counter_list_state_machine; R2.count_divisible cluster (count_letter)", "audit_grade": "weak/borderline"},
    {"unregistered": "M1.slot_permutations_r4 / binomial_choose_r3 (dropped cluster S4)", "survivor_cluster": "R2.dictionary_rank", "audit_grade": "not listed by the audits; this auditor's guess, BORDERLINE, not rendered"},
]
OUT.write_text(json.dumps(doc, indent=1) + "\n")
print("pre-reading judgement sha256", doc["judgement_before_reading_sha256"])
print("pairs now:", sum(p["grade"] == "STRONG" for p in doc["pairs"]), "STRONG,", sum(p["grade"] == "BORDERLINE" for p in doc["pairs"]), "BORDERLINE")
print("wrote", OUT, "sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
