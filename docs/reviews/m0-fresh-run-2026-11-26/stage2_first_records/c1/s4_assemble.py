# ruff: noqa
"""Stage-2 C1 audit, step 4: assemble stage2_conditions_c1.json (sorted keys, indent 2, trailing newline) from
(a) the auditor's code-reading judgements written below (wording, levels distinct, second-solver authorship), with file:line,
(b) the result of the final auditor's committed text-only solver (final_c1/f2_keys.py, run unmodified) on my fixtures (s2_f2keys_result.json),
(c) the fixture meta (seed, rows per lineage). Standard library only. Usage: python3 -I <this> FIXTURE_DIR F2_RESULT_JSON EXAMPLES_TXT OUT_JSON"""
import json, os, sys

fix_dir, f2_json, ex_txt, out_json = sys.argv[1:5]
meta = json.load(open(os.path.join(fix_dir, "meta.json")))
f2 = json.load(open(f2_json))
ex_lines = open(ex_txt).read().split("\n")

SOLVER = "docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f2_keys.py"  # implementation worktree, committed at b78e58b1, SHA-256 be5f1bf993acf6aa50aee4fbef1841bd9d577443c0fec3dbba7111435b6fa69a
FAIL_KINDS = ("frame_bad", "timeout", "error", "stderr", "not_one_line", "empty_line", "key_mismatch", "run_disagreement", "text_program_differs_from_render")

# where each builder is (s0_locate.out.json), and the level parameter lines (read by me)
LEVELS = {
 "C1.binary_search_f3": ("studies/m0/lineages_c1_fix3_lists.py:106-136", "list length n = (12, 14, 16, 20, 26, 34, 48)[level] (:112), strictly rising, so the number of probes rises; style and shape draws are level-free. Every step changes the size of the searched list. R-40 C1 point on this lineage (within-shape rate of the probes shape under the half-open style) is a cheap-rule rate, not a level point: it belongs to the fresh run (within-shape rates are reported, not counted, section 7 item 2); nothing decided here.", False),
 "C1.bracket_matching_f3": ("studies/m0/lineages_c1_fix3_other.py:28-75", "string length n = (14, 15, 16, 18, 20, 22, 24)[level] (:39), strictly rising; the stop p of the remain_at shape is drawn in 3n//4..n-1 (:55) and rises with n. Every step lengthens the scanned bracket string.", False),
 "C1.bytecode_loop_f3": ("studies/m0/lineages_c1_fix3_other.py:196-241", "pairs n = (4, 9, 9, 10, 11, 12, 14)[level] (:204) and the instruction set grows (:205): skip from level 1, mod from level 2, store/load from level 3; sumarg shape from level 1 (:220). L1->L2 keeps 9 pairs and adds the mod opcode (a larger dispatch chain and a new operation), so it is a real change of the program, not a relabel; every other step adds pairs or opcodes.", False),
 "C1.circle_elimination_r2": ("studies/m0/lineages_c1_rev2.py:303-332", "ring size n = 9 + level, plus 0 or 1 at level 0 only (:310); nothing else depends on the level. Levels 1-6 have disjoint ring sizes 10..15. Weak step L0->L1: level 1 is exactly level 0's n = 10 half (level 0 is half n = 9, half n = 10), so the two distributions differ (no n = 9 at level 1) and the stated size rises in mean (9.5 -> 10), but the step is small. Not a relabel and not the same distribution: PASS, with the weak step reported.", False),
 "C1.cond_chain_f3": ("studies/m0/lineages_c1_fix3_numbers.py:84-97", "operands 15..60 + 40 * level (:91), rounds 2 + level + (0..2) (:97), and from level 3 an extra halving rule in every round (:93-94). Every step lengthens the loop and widens the operands; L2->L3 also adds a statement.", False),
 "C1.counter_list_f3": ("studies/m0/lineages_c1_fix3_lists.py:162-184", "number of values 8 + 3 * level (:172); the machine styles are level-free. Every step adds three steps of the state machine.", False),
 "C1.digit_peel_f3": ("studies/m0/lineages_c1_fix3_numbers.py:123-150", "number of digits 4 + level, two more below base 5 (:131); every step adds one peel round at every base.", False),
 "C1.euclid_gcd_traced_f3": ("studies/m0/lineages_c1_fix3_numbers.py:48-81", "operand bound hi = (40, 44, 50, 56, 64, 76, 96)[level] (:56), common factor g up to 6 + level (:57), minimum rounds max(4, 3 + level // 2) (:64), so the minimum is 4, 4, 4, 4, 5, 5, 6. Every step changes the operand distribution and the trace length distribution; L0->L1, L1->L2, L2->L3 and L4->L5 change only operand ranges (the minimum round count is unchanged), a small step. Not a relabel; distributions differ at every step.", False),
 "C1.fast_power_f4": ("studies/m0/lineages_c1_fix4.py:91-107", "exponent with 3 + level bits drawn in [2^(bits-1), 2^bits - 1] (:102-103): the exponent ranges are disjoint across levels and the loop runs exactly 3 + level rounds; modulus 40..200 + 60 * level (:99). Every step adds one squaring round.", False),
 "C1.fib_like_f3": ("studies/m0/lineages_c1_fix3_other.py:361-374", "iterations n = randint(4, 8) + 3 * level (:366); every step adds three recurrence steps in expectation (adjacent supports overlap, distributions differ).", False),
 "C1.fib_shapes_recursive_f3": ("studies/m0/lineages_c1_fix3_other.py:377-393", "call argument 3 + level + (0..2) for the two-branch shape (:387) and 3 + level + (0..1) for the three-branch shape (:390): the recursion depth rises by one per level (adjacent supports overlap, distributions differ); multipliers and offsets are level-free.", False),
 "C1.func_branch_f4": ("studies/m0/lineages_c1_fix4.py:114-131", "threshold t 2..12 + 2 * level (:121), multiplier a 2..5 + level // 2 and offsets 1..9 + level (:122), even test in the else branch from level 2 (:124-125), calls 2, 2, 2, 3, 3, 4, 4 (:127) with arguments 0..20 + 4 * level. Every step changes a stated parameter and the item distribution; L0->L1, L3->L4 and L5->L6 change only literal ranges (same program skeleton and call count), a small step. Not a relabel; distributions differ at every step (the repair of the collapsed levels, section 7 item 5 (c), holds as written: distinct items, a stated parameter rising).", False),
 "C1.func_compose_f4": ("studies/m0/lineages_c1_fix4.py:134-160", "a 2..3 + level, b and c 1..13 + level (:141), modulus m 7..17 + 2 * level of h from level 3 (:152-154), argument -9..24 + level (:157), sum or difference of two calls from level 2 (:159). L1->L2 and L2->L3 change the program; L0->L1, L3->L4, L4->L5 and L5->L6 change only literal ranges, a small step. Not a relabel; distributions differ at every step (section 7 item 5 (c) as written).", False),
 "C1.list_build_f3": ("studies/m0/lineages_c1_fix3_lists.py:187-209", "number of iterations n = randint(5, 8) + level (:193); every step adds one append in expectation.", False),
 "C1.merge_two_sorted_f3": ("studies/m0/lineages_c1_fix3_lists.py:58-77", "list lengths 3 + level // 2 .. 4 + level each (:66), values up to max(na, nb) + 3 + level (:67); every step lengthens the merge (upper bound rises at every step, lower bound every second step).", False),
 "C1.nested_pairs_f3": ("studies/m0/lineages_c1_fix3_lists.py:212-229", "loop bounds a, b 4..8 + level (:218); every step enlarges the double loop's range.", False),
 "C1.postfix_evaluation": ("studies/m0/lineages_c1_stacks.py:72-102", "operand count m = 3 + level (:78), so 2m - 1 tokens; every step adds one operand and one operator.", False),
 "C1.recursive_calls_r2": ("studies/m0/lineages_c1_rev2.py:229-258", "split shape argument 6 + 4 * level .. 12 + 6 * level (:242), listfold list size 4 + 2 * level (:247), mutual argument 3 + 2 * level + (0..1) (:254); every shape grows at every step.", False),
 "C1.run_length_scan": ("studies/m0/lineages_c1_strings.py:16-38", "number of runs 3 + level (:25), run length 1..3 + level // 2 (:27); every step adds a run.", False),
 "C1.shared_lists_f3": ("studies/m0/lineages_c1_fix3_other.py:112-190", "number of operations 2 + level (:129); every step adds one list operation.", False),
 "C1.slices_f4": ("studies/m0/lineages_c1_fix4.py:163-188", "string of 2 + level // 2 pseudo-words plus level % 2 letters (:170); every PSEUDO word has 5 letters (vocab.py:32; checked: 7,568 words, all of length 5), so the string length is 10, 11, 15, 16, 20, 21, 25, strictly rising; list of 6 + level values (:174). Every step lengthens the sliced sequence (the repair of the collapsed levels holds as written). R-40 C1 point on this lineage (within-shape rate of the sum shape) is a cheap-rule rate, not a level point: it belongs to the fresh run (within-shape rates are reported, not counted, section 7 item 2); nothing decided here.", False),
 "C1.string_build_f3": ("studies/m0/lineages_c1_fix3_other.py:437-452", "loop end b = a + (4..8) * step + 2 * level (:446), and from level 2 a second modular test and a third letter (:448-449); every step adds two iterations.", False),
 "C1.string_methods_f3": ("studies/m0/lineages_c1_fix3_other.py:399-434", "chain of 2 + level string operations (:410); every step adds one operation.", False),
 "C1.turtle_walk_f3": ("studies/m0/lineages_c1_fix3_other.py:244-282", "commands n = (14, 16, 18, 20, 22, 24, 26)[level] (:252), the backward command 6 from level 3 (:253); every step adds two commands.", False),
 "C1.union_find_links_f3": ("studies/m0/lineages_c1_fix3_other.py:81-109", "nodes 9 + level and link pairs 4 + level (:88-89); every step adds a node and a union.", False),
 "C1.while_counter_f3": ("studies/m0/lineages_c1_fix3_numbers.py:20-45", "grow threshold 40 + 60 * level .. 200 + 400 * level (:30); collatz start 3..25 + 20 * level and down start 100 + 50 * level .. 400 + 150 * level (:33); every step raises the range of loop lengths.", False),
}

WORD_SPECIFIC = {
 "C1.binary_search_f3": "the move string (l, r, h) and the probe list 'm1,m2,...,' are built by the program itself (fix3_lists.py:118-125), so the printed form is fixed by the code",
 "C1.bracket_matching_f3": "the '>' case is the final else of the chain (fix3_other.py:65-69); the string holds only the eight bracket characters (:42-53), so the chain is exhaustive and correct",
 "C1.bytecode_loop_f3": "opcode numbers are literals of the dispatch chain (fix3_other.py:224-229); the skip test is written in the code",
 "C1.circle_elimination_r2": "the start position and step count are literals (rev2.py:316-319); the survivor shape's final loop is written in the code (:331)",
 "C1.cond_chain_f3": "all constants are literals of the loop (fix3_numbers.py:92-97)",
 "C1.counter_list_f3": "the machine's transition is written in the code (fix3_lists.py:174-180); the printed list form is Python's",
 "C1.digit_peel_f3": "the base and fold multiplier are literals (fix3_numbers.py:137-139)",
 "C1.euclid_gcd_traced_f3": "the stated number of rounds is the loop guard literal (fix3_numbers.py:70); the pair is printed as 'a b' by the program (:80)",
 "C1.fast_power_f4": "the added c and the modulus are literals (fix4.py:104-105)",
 "C1.fib_like_f3": "the recurrence, modulus and iteration count are literals (fix3_other.py:370-374)",
 "C1.fib_shapes_recursive_f3": "the recursive definition and argument are written in full (fix3_other.py:388-393)",
 "C1.func_branch_f4": "the threshold branch and calls are written in full (fix4.py:126-131)",
 "C1.func_compose_f4": "the function definitions and calls are written in full (fix4.py:150-160)",
 "C1.list_build_f3": "the expression and the optional filter are literals (fix3_lists.py:197-208)",
 "C1.merge_two_sorted_f3": "the tie rule is the written comparison (<= or <, fix3_lists.py:69, :74)",
 "C1.nested_pairs_f3": "the condition, bounds and increment are literals (fix3_lists.py:222-229)",
 "C1.postfix_evaluation": "the operator codes are literals of the chain (stacks.py:91-92)",
 "C1.recursive_calls_r2": "each shape's definitions are written in full (rev2.py:244-257)",
 "C1.run_length_scan": "the encoding is built by the program (strings.py:32-37)",
 "C1.shared_lists_f3": "aliasing and copying are Python semantics of the written statements; the helper functions are defined in the program when used (fix3_other.py:185-188)",
 "C1.slices_f4": "slice bounds and steps are literals; negative indices and steps are Python-defined (fix4.py:178-187)",
 "C1.string_build_f3": "the loop range and tests are literals (fix3_other.py:446-452)",
 "C1.string_methods_f3": "the chain is one expression of literals; the tail always lower-cases, so the answer is a fixed point of the scorer's normalisation by construction (fix3_other.py:432-434)",
 "C1.turtle_walk_f3": "headings and turns are written as branches (fix3_other.py:264-275); the position is printed as 'x,y' by the program (:281)",
 "C1.union_find_links_f3": "find and the link rule are written in the code (fix3_other.py:99-102)",
 "C1.while_counter_f3": "all constants are literals of the loop (fix3_numbers.py:31, :35-44)",
}

WORD_COMMON = ("Every item is the fixed frame 'Here is a Python program.' + the rendered program + 'What exactly does it print? It prints a single line.' (lineages_c1.py:37): the question (the exact printed line) "
               "and the answer format (one line) are stated, and the program carries every constant, so no convention outside Python's own semantics is needed. The key is what the program prints "
               "(lineages_c1.py:30-31 -> c1grammar.py:129-141, exactly one line enforced), which is unique for a deterministic program; the shared finish refuses programs that raise and keys that the scorer's "
               "normalisation would change (lineages_c1.py:32-36). Checked on my 350 fixtures of this lineage by the final auditor's committed checker (f2_keys.py, unmodified): the frame matches, the text "
               "program equals the rendered structured program, 0 static flags (one print as the last top-level statement; no import, set, dict, hash, id, eval or I/O), 0 errors, stdout exactly one non-empty line, "
               "the same output under CPython 3.12.14 (PYTHONHASHSEED 0) and 3.15.1 (PYTHONHASHSEED 2718281). Read: example items at levels 0 and 6 in s3_examples_L0_L6.txt (line {line}).")

SOLVER_REASON = ("FAIL on authorship only (section 8 item 1, required by section 8 'Registration' and section 4A stage 2). The solver of record for C1 is the final auditor's text-only key check {solver} "
                 "(extracts the program from the item text, runs it in a fresh CPython subprocess under two interpreters; imports nothing from studies/). It covers this lineage: FINAL_C1.md:28-31 and its per-lineage table "
                 "(:54-80) record 0 key mismatches on 3,500 items (500 per level), and on my fresh fixtures it agrees with the builder's key on {n} of {n} items (mismatching item ids: none). But section 8 item 1 requires a "
                 "second context 'that has not read the generator's or the first solver's source'. The record shows the opposite: the same context audited the C1 code (FINAL_C1.md:3-12) and, in its own draw script, wrapped the "
                 "builder's shared finish, which computes the key (final_c1/f1_draw.py:53-77, patching lineages_c1._finish); and the report itself says 'No second solver (my key check is an independent re-execution, "
                 "not a tree walker)' (FINAL_C1.md:218). The brief's description of it as an 'independent tracer/interpreter' is not what the report says. Agreement is shown; the authorship that section 8 item 1 "
                 "requires is not, so under 'PASS only if shown' the condition fails. PENDING LEAD REVIEW: if the lead rules that this solver meets section 8 item 1, this field becomes PASS with nothing else changed; "
                 "or a context that has not read the C1 generator, c1grammar or lineages_c1._finish writes a C1 second solver before the stage-2 hash.")

ex_line = {}
for k, l in enumerate(ex_lines, 1):
    if l.startswith("===== ") and l.endswith("") and "/L0/0" in l:
        ex_line[l.split()[1].split("/L0/0")[0]] = k

per = f2["per_lineage_level"]
lineages = {}
for lid in meta["lineages"]:
    n = sum(per.get(f"{lid}|{lv}", {}).get("n", 0) for lv in range(7))
    bad = sum(per.get(f"{lid}|{lv}", {}).get(kd, 0) for lv in range(7) for kd in FAIL_KINDS)
    flags = sum(per.get(f"{lid}|{lv}", {}).get("static_flag", 0) for lv in range(7))
    assert n == meta["files"][lid]["rows"] == 350, (lid, n)
    where, lv_reason, _ = LEVELS[lid]
    wording_ok = bad == 0 and flags == 0
    lineages[lid] = {
        "wording": {"result": "PASS" if wording_ok else "FAIL",
                    "reason": f"{WORD_COMMON.format(line=ex_line[lid])} Lineage-specific: {WORD_SPECIFIC[lid]}." + ("" if wording_ok else f" FAIL: {bad} checker failures, {flags} static flags.")},
        "levels_distinct": {"result": "PASS", "reason": f"Read {where}. {lv_reason}"},
        "second_solver": {"result": "FAIL", "solver": SOLVER, "fixtures": n, "mismatches": bad, "reason": SOLVER_REASON.format(solver=SOLVER, n=n)},
        "map": "see map_of_record",
    }
assert len(lineages) == 26
doc = {"evaluation": "C1", "fixture_seed": meta["seed"], "lineages": lineages}
with open(out_json, "w") as f:
    f.write(json.dumps(doc, sort_keys=True, indent=2) + "\n")
from collections import Counter
print(json.dumps({c: dict(Counter(v[c]["result"] for v in lineages.values())) for c in ("wording", "levels_distinct", "second_solver")}, sort_keys=True))
print("fixtures", sum(v["second_solver"]["fixtures"] for v in lineages.values()), "mismatches", sum(v["second_solver"]["mismatches"] for v in lineages.values()))
