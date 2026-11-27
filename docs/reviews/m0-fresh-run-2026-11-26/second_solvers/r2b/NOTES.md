# NOTES: second solvers r2b (EVAL R2), 8 lineages

Environment: system `python3 -I -B` (Python 3.15.1), standard library only. Commands:
`timeout 120 python3 -I -B .../m0_solver2_r2b_20261126/run_solver2.py` (output `run_solver2.out`: items 2240, bad 0, text_struct_mismatch 0);
`templates_r2b.py` -> `templates_r2b.out` (template enumeration); `probe_r2b.py` -> `probe_r2b.out` (edge-case probe).

All solvers compute from `structured`. For every one of the 2240 items, `run_solver2.py` also parses the inputs from the question text (`parse_text_*` in `solver2_r2b.py`) and checks they equal `structured` exactly: 0 mismatches. So text and structure carry the same inputs; the answers would be the same computed from either.

## R2.grid_sum
Procedure: `what` = `row k` -> sum of row k (1-based, top first); `column k` -> sum of column k (1-based); the diagonal -> sum of cells (i,i), i = 1..min(rows, cols).
Read: `grid`, `what` (structured); the text gives the same.
Templates (3): "...sum of the numbers in the diagonal from the top left corner (cells (1,1), (2,2), and so on)?" (100), "...in column N?" (94), "...in row N?" (86). Shapes 3x3..6x6 including 3x4, 4x5, 5x6; 46 diagonal items are non-square (rows < cols).
Hand-checked: L0#0 = 3+2+3 = 8; L1#0 (3x4) = 9+0+7 = 16; L3#0 (4x5) = 4+1+8+0 = 13; L6#39 column 5 = 5+6+4+5+8+3 = 31. All equal the code.

## R2.list_ops
Procedure: apply ops in order to a copy of `xs`: append v; drop_first; drop_last; reverse; first_to_end (move first element to the end). Output `, `-joined.
Read: `xs`, `ops`. One sentence template; five step phrases: "add N at the end", "remove the first element", "remove the last element", "reverse the list", "move the first element to the end". Never reaches an empty list (minimum start length 4; no exception).
Hand-checked: L0#0 -> 72, 3, 4, 40; L1#0 -> 98, 48, 77; L3#0 -> 86, 46, 53, 93, 47, 13, 2; L6#39 -> 39, 24, 34. All equal.

## R2.luhn_check
Procedure: total = sum over digits counted from the right (rightmost is 1st), doubling even positions and subtracting 9 when the double exceeds 9. `valid`: yes iff total % 10 == 0. `check_digit`: the unique c in 0..9 with payload+[c] valid (c is the new 1st digit, so the payload's rightmost digit becomes the 2nd and is doubled); uniqueness asserted.
Read: `digits`, `ask`. Templates (2): check-digit wording "A number is valid if ... One more digit is to be written at the right end of N ... Which digit must be written?" (147) and validity wording "The number is valid if ... Is the number N valid? Answer yes or no." (133). 27 items have a leading 0 digit; the text shows it too (text parse equals structured).
Hand-checked: L0#0 914208 -> 4; L1#0 83139901 -> 9; L3#0 964167337616 -> 8; L6#39 9543390772689028958 total 97 -> no. All equal.

## R2.min_heap_ops
Procedure: 1-based array; insert = append then swap with parent pos//2 while strictly smaller; remove-min = pop last, put it at position 1 (if anything remains), then while strictly larger than the smaller existing child, swap with that child. Output positions 1..end.
Read: `xs`, `removals`. Templates (3): no removal sentence (removals 0, 158), "Then remove the smallest 1 time." (80), "Then remove the smallest N times." (42; N = 2 only).
Ties: no item has repeated values (probe), so equal children never occur; the code raises if they did (it never raised).
Hand-checked: L0#0 -> 12, 35, 38, 47, 45, 87, 77, 81, 49; L1#0 -> 5, 18, 41, 28, 31, 73, 93, 48, 75, 62, 50. Both equal (worked in full by hand).

## R2.run_length
Procedure: scan maximal runs, emit letter + decimal run length, concatenate.
Read: `s`. One template. Alphabet a, b, c, x, y, z.
Hand-checked: L0#0 -> x4c4y1x4a4b4; L1#0 -> c2y1a4y3z2a2c1; L3#0 -> y4b5y5c4x3z5y2c5a3. All equal.

## R2.sort_list
Procedure: sort ascending, or descending when `desc`; `, `-joined, negatives with `-`.
Read: `xs`, `desc`. Templates (2): "from smallest to largest" (141), "from largest to smallest" (139). No duplicates.
Hand-checked: L0#0 -> -43, -33, -29, 4; L1#0 -> 171, 158, 65, -24, -35; L3#0 -> 380, 325, 269, 249, 85, 44, -50. All equal.

## R2.string_rewrite_nonidentity
Procedure: for each rule in order, one left-to-right scan of the string as it is at the start of the step: at each position, if the pattern starts here, emit the replacement and skip the pattern's length, else copy one character; replacements are not rescanned in the same step. Delete = empty replacement. (Own scanner; equivalent to str.replace semantics.)
Read: `s`, `rules`. One sentence template; two step phrases: "replace every 'X' with 'Y'" (562 steps), "delete every 'X'" (198 steps). Patterns of length 1 and 2 (including self-overlapping ones aa, bb, cc).
Hand-checked: L0#0 cababc -> caac; L1#0 -> acacacaccc; L3#0 -> baaababa. All equal to the code, but my FIRST hand attempt at L3#0 was wrong (I dropped a character when deleting the c's: wrote "bbabbaba" instead of "babbaba", giving "aabaaababa"); redone by hand: aacccabaaaba -> cbccccabcbcaba -> babbaba -> baaababa, which equals the code. Kept here as a recorded checker error (mine).

## R2.to_base_wide
Procedure: repeated divmod by base, digits 0-9a-f, most significant first, no leading zeros.
Read: `n`, `base`. One template. Bases 2..9, 11, 12, 13, 16; n >= 46.
Hand-checked: L0#0 1040 base 5 -> 13130; L1#0 1118 base 3 -> 1112102; L3#0 121569 base 8 -> 355341. All equal.
