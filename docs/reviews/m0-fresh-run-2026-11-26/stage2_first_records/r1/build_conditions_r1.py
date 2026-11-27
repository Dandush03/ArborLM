# ruff: noqa
"""Writes stage2_conditions_r1.json (sorted keys, indent 2, trailing newline) from the auditor's written judgements below and
the fixture counts of run1/fixture_summary_r1.json. Standard library only. usage: python3 <this> <deliver dir>"""
import json, os, sys
D = sys.argv[1]
S = json.load(open(os.path.join(D, "run1", "fixture_summary_r1.json")))
SOLVER = "docs/reviews/m0-lineage-decision-2026-11-25/final_r1/solvers_final.py"
RULE_L = ("Rule applied to all ten: PASS iff (a) the builder's level parameters differ between every two levels (no two levels share an item distribution), "
          "confirmed by no shared normalised text across levels in the 350 fixtures and no two levels equal under a shared-stream identity test; "
          "(b) a stated size/steps/depth parameter is non-decreasing from level 0 to 6 and larger at 6; (c) each adjacent pair differs in at least one stated parameter in the direction of more work.")
WORD = ("Builder code read and 14 rendered fixtures read (2 per level); question stated, answer form stated, key unique by construction and agreed by the text-only solver on 350 of 350 fixtures with 0 'ambiguous'. ")
J = {
 "R1.boolean_lights_r4": (
   WORD + "Start state stated with 'all the lamps not named here are off'; toggle semantics stated per switch; 'Answer yes or no.'",
   "lamps 4+L (4..10), presses 3+2L (3..15) strictly rising at every level; switches 3+L//3. "),
 "R1.categories_default_exceptions_r4": (
   WORD + "Linear chain 'Every X is a Y', member in the smallest group, one rule per group on the asked verb, none on the member's own group; precedence convention stated ('the rule about the smaller (more specific) group wins'); 'Answer yes or no.' Cosmetic: 'A' before vowel-initial pseudo-words; does not affect the key.",
   "chain c = T+8+2L (17,19,23,25,29,31,35) strictly rising; rules on the asked verb T = 9+2(L//2) (9,9,11,11,13,13,15). "),
 "R1.compass_turns": (
   WORD + "Turn commands map to fixed multiples of 90 degrees; walks do not change heading; 'Answer north, east, south or west.'",
   "commands 3+2L (3..15) strictly rising. "),
 "R1.conditional_threshold_rule_r4": (
   WORD + "Weights, votes, threshold and the abstention convention stated; 'at least' stated; negative thresholds are printed as e.g. '-18' and are unambiguous; 'Answer yes or no.'",
   "members 6+L (6..12) strictly rising. "),
 "R1.equivalence_exchange_rates_r6": (
   WORD + "Rates form a tree (spine plus hanging items), so every ratio is determined; the answer is a whole number by construction; the question 'How many units of Y ...' fixes an open whole-number answer. Cosmetic: '1 units of' appears; does not affect the key.",
   "spine length 3+L (hops X..Y 3..9) strictly rising; rates 5..13. "),
 "R1.knights_knaves_r6": (
   WORD + "Knight/knave convention stated; statements unambiguous (self-reference allowed and well defined); a unique solution over all people is enforced by the builder (validity redraw); 'Answer knight or knave.'",
   "people 4+L (4..10) strictly rising. "),
 "R1.spatial_grid_walk_r5": (
   WORD + "Orientation (row 1 northernmost, column 1 westernmost), wall cells and the convention 'A move into a wall or off the map does nothing' stated; place names distinct; no place is named 'wall'; 'Choose from' lists every place.",
   "grid cells 9,9,12,16,16,20,25 (non-decreasing); free moves 4+L+U(0..3) (support shifts by one at every level); blocked moves 3+L//3; total moves rise at every level. "),
 "R1.swap_tracking_r5": (
   WORD + "Swap and three-way hand-over stated as simultaneous ('all at once'); 'Choose from' lists every object.",
   "operations 6+2L (6..18) strictly rising; people 5+L//2. "),
 "R1.temporal_weekday_shift_r6": (
   WORD + "One anchor weekday; links form a tree, so every event's weekday is determined; the question asks for a day of the week (a closed set of seven names). The answer form is stated by the question and not by an explicit list: the auditor's reading, applied to every open or category answer here.",
   "spine length 5+L (hops anchor..asked 5..11) strictly rising; links 7..15. "),
 "R1.venn_counting_r5": (
   WORD + "Group sizes and every intersection stated; 'Each person is counted once in each number that applies to them' fixes the inclusive reading of 'both' and 'all of'; the question fixes an open count.",
   "groups 2,2,3,3,3,4,4 (non-decreasing, rising overall); the asked read-out changes by level (none, one, none, two, at least two, none, two); region range 1..24+4L and none range 0..30+2L strictly wider at every level. R-40 point (levels 0/1) decided here: levels 0 and 1 are distinct (different read-out and wider number ranges; not a relabel, not one distribution), but the procedure's size (2 groups) does not rise from 0 to 1 (nor from 3 to 4); (c) is met by the number ranges only. Whether level 1 is harder than level 0 is a difficulty question, on which no lineage is failed. PASS under the rule; a stricter reading requiring the procedure's size to rise at every adjacent pair would FAIL it: PENDING LEAD REVIEW. "),
}
SOLV_REASON = ("The final R1 auditor's text-only solver covers this lineage (SOLVERS, solvers_final.py:463-476); it imports only re, itertools, collections.deque, fractions.Fraction and heapq and reads only the question string. "
               "Recorded agreement (FINAL_R1.md section 1): 0 mismatches, 0 ambiguous, 0 parse errors on 10,500 items per shape (84,000 + 42,000 over 12 shapes). "
               "Stage-2 fixture check (seed 14961762383913329776, 50 items per level): agree {agree} of {n}; mismatch {mismatch}; ambiguous {ambiguous}; parse {parse}. "
               "Caveat common to all ten (not a failure under this condition as briefed): samples.py, the dump the solver was written from, prints the builder's KEY (samples.py:2,15), so the record does not show the sentence of section 8 item 1 that fixtures carry no answer from the first solver: PENDING LEAD REVIEW.")
out = {"evaluation": "R1", "fixture_seed": S["fixture_seed"], "lineages": {}}
for lid, (w, lev) in sorted(J.items()):
    rec = S["lineages"][lid]
    t = rec["totals"]
    ok_lev = (sum(rec["cross_level_shared_texts"].values()) == 0 and not rec["identity_equal_level_pairs"])
    assert ok_lev
    solver_ok = rec["solver_covers"] and t["mismatch"] == 0 and t["ambiguous"] == 0 and t["parse"] == 0 and t["agree"] == t["n"] == 350
    out["lineages"][lid] = {
        "wording": {"result": "PASS", "reason": w},
        "levels_distinct": {"result": "PASS", "reason": lev + RULE_L + " Fixtures: 0 shared normalised texts across levels; identity test: no two levels equal."},
        "second_solver": {"result": "PASS" if solver_ok else "FAIL", "solver": SOLVER, "fixtures": t["n"], "mismatches": t["mismatch"],
                          "reason": SOLV_REASON.format(**t) + ("" if solver_ok else " FAIL: mismatch, ambiguity or parse error; ids " + ",".join(rec["mismatch_ids"] + rec["ambiguous_ids"] + rec["parse_ids"]))},
        "map": "see map_of_record",
    }
assert sorted(out["lineages"]) == sorted(S["lineages"])
with open(os.path.join(D, "stage2_conditions_r1.json"), "w") as f:
    json.dump(out, f, sort_keys=True, indent=2); f.write("\n")
print("written", len(out["lineages"]))
