"""v2: categories level-6 keys relabelled (v1 swapped the two level-6 items: hand answers were attached to the wrong index); more items added.
Compare hand-worked answers (worked in the auditor's head from the question text, before looking at the solver output) with answers_r1.jsonl."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
HAND = {
 ("R1.boolean_lights_r4",0,0):"yes", ("R1.boolean_lights_r4",0,1):"yes", ("R1.boolean_lights_r4",6,0):"no", ("R1.boolean_lights_r4",6,1):"yes",
 ("R1.categories_default_exceptions_r4",0,0):"no", ("R1.categories_default_exceptions_r4",0,1):"yes", ("R1.categories_default_exceptions_r4",6,0):"yes", ("R1.categories_default_exceptions_r4",6,1):"no",
 ("R1.categories_default_exceptions_r4",3,0):"yes", ("R1.categories_default_exceptions_r4",3,1):"yes",
 ("R1.equivalence_exchange_rates_r6",6,0):"100", ("R1.knights_knaves_r6",3,0):"knight", ("R1.swap_tracking_r5",3,0):"apple",
 ("R1.temporal_weekday_shift_r6",3,0):"Wednesday", ("R1.spatial_grid_walk_r5",6,0):"Lilor",
 ("R1.compass_turns",0,0):"east", ("R1.compass_turns",0,1):"north", ("R1.compass_turns",3,0):"east", ("R1.compass_turns",6,1):"west",
 ("R1.conditional_threshold_rule_r4",0,0):"no", ("R1.conditional_threshold_rule_r4",0,1):"no", ("R1.conditional_threshold_rule_r4",3,0):"yes", ("R1.conditional_threshold_rule_r4",6,1):"no",
 ("R1.equivalence_exchange_rates_r6",0,0):"2", ("R1.equivalence_exchange_rates_r6",0,1):"18", ("R1.equivalence_exchange_rates_r6",3,1):"5",
 ("R1.knights_knaves_r6",0,0):"knave", ("R1.knights_knaves_r6",0,1):"knight",
 ("R1.spatial_grid_walk_r5",0,0):"Kanek", ("R1.spatial_grid_walk_r5",0,1):"Ralar", ("R1.spatial_grid_walk_r5",3,0):"Niler",
 ("R1.swap_tracking_r5",0,0):"scarf", ("R1.swap_tracking_r5",0,1):"globe",
 ("R1.temporal_weekday_shift_r6",0,0):"Tuesday", ("R1.temporal_weekday_shift_r6",0,1):"Sunday",
 ("R1.venn_counting_r5",0,0):"28", ("R1.venn_counting_r5",0,1):"13", ("R1.venn_counting_r5",3,0):"60", ("R1.venn_counting_r5",3,1):"65", ("R1.venn_counting_r5",6,0):"165",
}
A = {}
for l in open(os.path.join(HERE, "answers_r1.jsonl")):
    r = json.loads(l); A[(r["id"], r["level"], r["index"])] = r["answer"]
bad = 0
for k, v in HAND.items():
    ok = A[k] == v; bad += not ok
    print("OK  " if ok else "DIFF", k, "hand", v, "solver", A[k])
print("hand-checked", len(HAND), "differences", bad)
