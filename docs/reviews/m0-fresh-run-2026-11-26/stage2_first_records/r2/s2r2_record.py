# ruff: noqa
"""M0 stage 2, R2: writes stage2_conditions_r2.json from the auditor's judgements (below, written by hand from code reading) and the
fixture-check output s2r2_check.out.json. Standard library only. Run: python3 -I <this> <deliver dir>"""
import json, sys

D = sys.argv[1]
chk = json.load(open(f"{D}/s2r2_check.out.json"))
SOLVER = "docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_solver.py"

# wording: (reason). Every one is PASS; file:line in REASONS.md.
W = {
 "binary_search_trace": "Rule stated in full (positions 1..n, mid = floor((low+high)/2), update and stop rules, absent target ends with 'found nothing'); list sorted and distinct; ask 'which numbers, in order, comma-separated' or 'sum'; key = _probe_positions, which is exactly the stated rule. Unique.",
 "caesar_shift": "Direction (forward), amount, wrap z->a and 'spaces stay' stated; text is lowercase words only (PSEUDO checked: 7,568 words, all [a-z]+). Unique.",
 "cellular_automaton": "All 8 triples given with their value, neighbour order (left, self, right) stated, synchronous update stated, edge cells count as 0 stated, step count and output format (digits, no spaces) stated. Unique.",
 "cheapest_network": "Towns listed, every offered cable with its cost listed, connectivity goal stated; builder redraws a disconnected offer (Retry), so a spanning tree exists; the minimum total cost is unique even with tied costs. Number answer.",
 "count_divisible": "Fix-4 sentence 'Every entry of the list counts each time it appears: a number that is listed twice is added twice' settles the multiset reading (the solver's flag set_reading_differs_but_stated fired on 108/350 fixtures, always with the clause present); 'greater than t' strict; t itself is in the list and excluded by 'greater than'. Unique.",
 "crt_smallest": "Moduli pairwise coprime (Retry otherwise), remainders x mod m < m, so the smallest positive solution is unique in 1..prod; key x drawn in 1..prod is that solution (x = prod gives all remainders 0 and answer prod, still the smallest positive). Unique.",
 "dictionary_rank": "Word length, letter set (sorted), no repetition, dictionary order and 1-based numbering stated; rank k drawn in 2..total-1, asked word built from the letters with distinct letters, so both asks are in range. Unique.",
 "expression_eval": "Each item states its convention in full (ranked: parentheses, then * left to right, then + and - as one group left to right with two worked examples; left-to-right: parentheses first, same rule inside, no priority for *, worked example). Integers 2..20, no division, no unary minus. Key from evaluate() under the stated convention. Unique.",
 "from_base": "Base and digit string stated; letter digits defined; leading digit non-zero; every digit < base (drawn from range(b)). Decimal number answer. Unique.",
 "grid_sum": "Rows and columns stated with row-major listing; asks row i, column j or 'the diagonal from the top left corner (cells (1,1), (2,2), and so on)'. On a non-square grid (54/350 fixtures) the diagonal is the cells (i,i) that exist, i = 1..min(rows, cols), which the parenthesis defines; I read no second admissible reading. Unique.",
 "list_ops": "Start list and ordered steps from a closed set of five phrases; removals are replaced by 'add' when the list has <= 2 entries, so no step acts on an empty list; comma-separated output stated. Unique.",
 "luhn_check": "Doubling rule stated from the right (1st kept, 2nd doubled, ...), minus 9 rule and validity stated; 'no' items change one digit, which Luhn always detects (assert in the builder); the check digit is stated to be the new rightmost (undoubled) digit, so exactly one of 0..9 works. Answer yes/no or a digit. Unique.",
 "min_heap_ops": "Heap property, insert (sift up) and remove-smallest (last to root, sift down to the smaller child) stated; inserted numbers are distinct (r.sample), so no tie between children; output 'row from position 1, comma-separated' stated. Unique.",
 "run_length": "Encoding defined with an example; each run's letter differs from the previous run's by construction, so every written run is maximal and the key equals the encoding. Unique.",
 "sort_list": "Direction and comma-separated output stated; numbers distinct (r.sample). Unique.",
 "string_rewrite_nonidentity": "Steps in order, each 'scanning left to right over non-overlapping matches in the string as it is when the step starts' - the semantics of str.replace used for the key; each pattern occurs in the string when its step is reached; final string never empty (Retry). Unique.",
 "to_base_wide": "Decimal n >= 10, base stated, digit symbols 0-9 then a-f stated (bases up to 16). Unique.",
}

# levels distinct: (reason). Every one is PASS; criterion: ADR-0033 6.2 'Five registered levels (depth, steps or program size), and two reserve levels'.
L = {
 "binary_search_trace": "List length n = 16+4L+U{0..3} (31 and 63 stepped to 32 and 64): supports of adjacent levels disjoint except n=32 at L3/L4; list size (and look count ~log2 n) rises every level. Fixtures: n 16-19, 20-23, 24-27, 28-32, 32-35, 36-39, 40-43.",
 "caesar_shift": "Words = 1+L (fix 4): letters to shift 5, 10, ..., 35 on the fixtures; every adjacent pair has disjoint size.",
 "cellular_automaton": "Cells 11+2L every level, steps 2+L//2 (2,2,3,3,4,4,5): cells x steps rises every level; supports of adjacent levels disjoint.",
 "cheapest_network": "Towns 8+L, cables offered 2(8+L) (fix 4): graph size rises every level; supports disjoint.",
 "count_divisible": "List length 18+4L every level (fix 4) and value range 99+100*(L//2): supports of adjacent levels disjoint in length.",
 "crt_smallest": "Moduli from range(3+5L, 30+10L) (fix 4), 2 congruences to L2 and 3 from L3: the smallest and largest admissible modulus rise every level, the number of congruences at L2->L3; laws differ at every step (supports overlap at some steps, never equal).",
 "dictionary_rank": "Word length (positions of the mixed-radix rank/unrank) 4,4,5,5,6,6,7; alphabet sizes U{9,10,11}, U{9..12}, U{7,8,9}, U{8,9,10}, U{8,9,10}, U{9,10,11}, U{9,10,11}. Even->odd steps raise the alphabet (list size), odd->even steps raise the depth by one position. L0/L1: same length, L1 adds alphabet 12 (mean list size 5,328 -> 6,966; item laws differ, total-variation distance 1/4) - the thinnest step, not a relabel and not one law. R-40 point L1->L2: depth 4 -> 5 positions, disjoint supports; decided PASS (see REPORT).",
 "expression_eval": "Chain of 3+L(+0/1) terms (ranked) or 4+L(+0/1) numbers (left to right) (fix 4), extra parentheses from L2 and L3: number count and nesting rise every level (fixture means 5.98, 6.98, 8.66, 9.90, 11.98, 13.34, 16.08 numbers).",
 "from_base": "Digits = 3+L+U{0,1,2} (mean 4+L, so one more Horner step per level), base set widens at L2. Adjacent laws differ (L0/L1 total-variation 1/3). R-40 point (shared texts across levels): overlapping supports are not one law; cross-level duplicates are a uniqueness/disjointness matter handled by draw_items' text set and the distinct-item key, not by this condition; decided PASS (see REPORT).",
 "grid_sum": "Rows 3+L//2, columns 3+(L+1)//2: 3x3, 3x4, 4x4, 4x5, 5x5, 5x6, 6x6; one more row or column at every step, so every summed line or the diagonal grows by the step, and the grid read grows.",
 "list_ops": "Operations 2+L every level; start length 4+L//2. Step count rises at every level; supports disjoint.",
 "luhn_check": "Payload 6+2L digits every level (7..19 digits in the valid ask): digits processed rise by 2 per level; supports disjoint.",
 "min_heap_ops": "Inserted numbers 10+L every level; removals U{0,0,1} to L2 and U{0,0,1,2} from L3. Inserts rise every level; supports of n disjoint.",
 "run_length": "Runs 6+L every level, run length up to 4+L//2: run count rises every level; supports disjoint in runs.",
 "sort_list": "List length 4+L every level, range up to 100(1+L): supports disjoint.",
 "string_rewrite_nonidentity": "String length 6+2L every level; rules 1+(L+1)//2 (1,2,2,3,3,4,4). Length rises every level, rule count at odd steps; supports disjoint in length.",
 "to_base_wide": "n ~ U{10..500*4^(L+1)} (input +2 bits per level), bases 2..9 to L1 and 2..9,11,12,13,16 from L2. Exact expected division steps (digits of the answer): 5.229, 6.200, 6.182, 7.036, 7.865, 8.685, 9.558 - flat (-0.018) at L1->L2 because larger bases enter; for every base common to both levels the expected steps rise, the dividend is 4x larger, and letter digits enter. Laws differ at every step. PASS on 'size' (input magnitude, base set); the L1->L2 step-count dip is reported, not a failure (a lineage is not failed on a doubt about difficulty).",
}

SS_REASON = ("NOT SHOWN under section 8 item 1. The solver exists, covers this lineage (SOLVERS of f_solver.py:464-466), reads only the question "
             "text, was written by a context separate from the builder's (FINAL_R2.md:3-5), FINAL_R2.md:31 records 0 mismatches and 0 errors in 133,000 items over 19 lineages incl. this one, "
             "and my fresh fixtures agree on every item. But section 8 item 1 requires that the second solver be written from structured form, schema and fixtures only, "
             "that 'the fixtures it receives carry no answer from the first solver', and that its author has not read the generator's or the first solver's source. "
             "f_solver.py:3 says it was written from f_render.out, f_shapes.out and f_phrases.out; f_render.py prints '--> ANSWER: <key>' under every item and f_shapes.py prints each "
             "example's key: the author received the first solver's answers. That the author did not read the generator's source is not recorded. The third-context audit of the pair "
             "(section 8 item 1) is outside this field. PENDING LEAD REVIEW: under the brief's shorter wording (text-only solver, separate context, agreement) the condition would read PASS.")

lineages = {}
for lid, rec in chk["lineages"].items():
    nm = lid.split(".", 1)[1]
    lineages[lid] = {
        "wording": {"result": "PASS", "reason": W[nm]},
        "levels_distinct": {"result": "PASS", "reason": L[nm]},
        "second_solver": {"result": "FAIL", "solver": SOLVER, "fixtures": rec["items"], "mismatches": rec["mismatches"] + rec["errors"],
                          "reason": SS_REASON + f" Fixture check: {rec['items']} items (50 per level, levels 0-6), {rec['mismatches']} mismatches, {rec['errors']} solver errors; items hash {rec['items_hash']}."},
        "map": "see map_of_record",
    }
assert sorted(lineages) == sorted(W and ["R2." + k for k in W]), "lineage set differs"
out = {"evaluation": "R2", "fixture_seed": chk["fixture_seed"], "lineages": lineages}
with open(f"{D}/stage2_conditions_r2.json", "w") as f:
    json.dump(out, f, sort_keys=True, indent=2)
    f.write("\n")
print("written", len(lineages), "lineages")
