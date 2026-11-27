# M1 batch 1, revision 2: structured-form schema for the second-solver agent (revised shapes only)

Written by the implementer after the independent audit AUDIT_M0_M1_1 and the lead rulings 2. Not a result; nothing here approves anything. The solver interface is that of `M1_BATCH1_SCHEMA.md` (reads ONLY `structured`; `solve(structured) -> str`; ValueError when the answer is not unique; registry keyed by id; the answer string is exactly the fixture's `answer`).
Fixtures: `studies/m0/fixtures/m1_batch1_rev2/<id>.jsonl`, 20 items per level (0 and 6 reserve), structurally distinct across ALL levels of one file. The four lineages carried over unchanged (finite_differences, quadratic_area, recurrence_iterate, tiered_pricing) keep their batch-1 ids, fixtures and schema entries.
Every convention an answer depends on is stated in the item text (leading zero, the meaning of a power, the reversal of a number, what a perimeter counts, what a full pallet is); solvers still read only `structured`.

## Revised lineages

### `M1.gcd_lcm_r2` (family number_theory; supersedes `M1.gcd_lcm`)

structured: {"ask": "gcd" | "lcm", "values": [positive integers, distinct]}. All values are multiples of a common factor d >= 2 (so the product is never the lcm and the
smallest value is rarely the gcd, by construction). gcd: the largest whole length dividing every value; lcm: the first common time of periodic events with these periods.
The ask is drawn before any other choice and nothing is redrawn but a repeated value.

Example (level 2):

```
question: Anja from Garth found this problem in a puzzle book. 2 lights flash at the same moment. After that, one flashes every 546 seconds, the other every 416 seconds. After how many seconds do all 2 flash together again for the first time? Answer with a whole number.
structured: {"ask": "lcm", "values": [546, 416]}
answer: 8736
```

### `M1.crt_congruence_r2` (family number_theory; supersedes `M1.crt_congruence`)

structured: {"conditions": [[modulus, remainder]]}, pairwise coprime moduli, 0 < remainder < modulus. Answer: the least positive whole number meeting every condition.
Unchanged from batch 1 except that the redraw 'answer must exceed the largest modulus' (a heuristic-conditional redraw) is withdrawn.

Example (level 2):

```
question: Vera is thinking of a positive whole number. Dividing it by 11 leaves remainder 5; dividing it by 3 leaves remainder 1. What is the smallest positive whole number that Vera could be thinking of? Answer with a whole number.
structured: {"conditions": [[11, 5], [3, 1]]}
answer: 16
```

### `M1.prime_factors_r2` (family number_theory; supersedes `M1.prime_factors`)

structured: {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. As batch 1 with a wider prime pool and N range (capacity, ruling R-5).

Example (level 2):

```
question: This problem comes from a quiz held in Ivybridge, set by Orla. Consider the number 26000. How many different positive whole numbers divide it exactly (counting 1 and the number itself)? Answer with a whole number.
structured: {"ask": "divisors", "n": 26000}
answer: 40
```

### `M1.power_remainder_r2` (family number_theory; supersedes `M1.last_digit_power`)

structured: {"modulus": p, "op": "sum" | "product", "terms": [[base, exponent]]}, p in {17, 19, 23, 29}, no base a multiple of p. Each term is the product of `exponent` factors, each equal to `base`
(said so in the item). Answer: the remainder of the sum (or product) of the terms on division by p, by reducing each exponent modulo p - 1 (Fermat) and combining.
Supersedes last_digit_power: its heuristics '(last digit of the base)^(last digit of the exponent)' and 'square of the base digit' were right 0.33 to 0.44 of the time because
10 = 2 mod 4 (so e and e mod 10 share a residue mod 4 half the time); with a prime modulus p whose p - 1 is not a multiple of 5 (so not 11 or 31) the exponent's last digit carries almost no information about its residue mod p - 1 (the copied heuristic fails whenever the order of the base does not divide 10).
The batch-1 rejections (answer never the base digit; even exponents forced for bases ending 4 or 9) are gone.

Example (level 2):

```
question: Iris of Selby wrote this problem for a maths club. Let X be the product of all the following factors: 342 factors equal to 120 and 136 factors equal to 8. What is the remainder when X is divided by 19? Answer with a whole number.
structured: {"modulus": 19, "op": "product", "terms": [[120, 342], [8, 136]]}
answer: 11
```

### `M1.inclusion_exclusion_r2` (family counting; supersedes `M1.inclusion_exclusion`)

structured as batch 1. The ask is drawn first; the redraw 'the answer is never a stated number' is withdrawn (it was conditional on a heuristic).

Example (level 2):

```
question: 36 people were asked what they do. 18 of them paint, 6 of them sing in the choir, and 2 of them do both. How many of the 36 people do at least one of these things? Answer with a whole number.
structured: {"ask": "any", "pairs": [2], "sets": ["paint", "sing in the choir"], "sizes": [18, 6], "total": 36, "triple": null}
answer: 22
```

### `M1.binomial_choose_r2` (family counting; supersedes `M1.binomial_choose`)

structured as batch 1 ({"shape": "plain" | "include" | "two_groups", "n", "k", "x", "y", "j"}) with wider ranges (capacity, ruling R-5) and a cap of 10**12 on the answer
(a size cap, the only loop). The shape is drawn first, so the mix is a third each at every level.

Example (level 2):

```
question: This problem comes from a quiz held in Quarry, set by Fern. A club has 25 members, and Pearl is one of them. A committee of 4 members is chosen (the order does not matter), and Pearl must be on it. How many different committees are possible? Answer with a whole number.
structured: {"j": 0, "k": 4, "n": 25, "shape": "include", "x": 0, "y": 0}
answer: 2024
```

### `M1.slot_permutations_r2` (family counting; supersedes `M1.slot_permutations`)

structured: {"digits": [allowed digits], "length": s, "repeat": bool, "lead_nonzero": bool, "parity": "even" | "odd"}. Codes of s digits, every position from `digits`; no digit twice
unless `repeat`; when 0 is among the digits the item STATES whether the first digit may be 0 (a code such as 012 is then allowed); the last digit has the stated parity.
Supersedes slot_permutations: batch 1 did not state the leading-zero rule (13 of 140 fixture keys changed under the ordinary reading) and drew parity 'any' with a redraw
that forced a restriction (withdrawn: the parity restriction is now always present, by construction).

Example (level 2):

```
question: Yara from Quarry found this problem in a puzzle book. How many 4-digit codes can be written using only the digits 0, 2, 4, 5, 6 and 8, if no digit may be used more than once, the first digit may be 0 (a code such as 012 is allowed) and the last digit must be even? Answer with a whole number.
structured: {"digits": [0, 2, 4, 5, 6, 8], "lead_nonzero": false, "length": 4, "parity": "even", "repeat": false}
answer: 300
```

### `M1.change_ways_r2` (family counting; supersedes `M1.change_ways`)

structured: {"coins": [values in cents, distinct], "target": T}. Answer: the number of different multisets of coins that add up to exactly T. T is built from a random combination of the coins
(so at least one way exists, by construction); the batch-1 redraws (4 <= answer <= 150; answer != T // largest coin + 1) are withdrawn.

Example (level 2):

```
question: Opal from Westmere found this problem in a puzzle book. Using only coins worth 2, 4 and 12 cents, with as many coins of each value available as you like, in how many different ways can exactly 54 cents be paid? (Two ways are the same if they use the same number of coins of each value; the order does not matter.) Answer with a whole number.
structured: {"coins": [2, 4, 12], "target": 54}
answer: 40
```

### `M1.pigeonhole_worst_case_r2` (family counting; supersedes `M1.pigeonhole_worst_case`)

structured as batch 1 ({"counts", "goal": "same" | "all", "k"}). The goal is drawn first; for goal "same", k is drawn from 2..max(count) (so a colour with k marbles exists, by construction);
the redraws 'the cap bites' and 'counts not all equal' are withdrawn. Wider counts (capacity, R-5).

Example (level 2):

```
question: A bag holds marbles of 4 colours: 41 blue, 39 yellow, 32 red, 27 white. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the draws are, of having at least 10 marbles of the same colour? Answer with a whole number.
structured: {"counts": [41, 39, 32, 27], "goal": "same", "k": 10}
answer: 37
```

### `M1.median_list_r2` (family statistics; supersedes `M1.median_list`)

structured: {"shape": "list", "values": [numbers in the order printed]}. List shape only (the batch-1 table shape needed a redraw so that the multiplicities mattered; that redraw is
withdrawn and the shape is dropped from this revision, by construction). Values may repeat. Answer: the median (the mean of the two middle values when the count is even).

Example (level 2):

```
question: Ben from Ivybridge found this problem in a puzzle book. The values are 68, 62, 62, 11, 58, 70, 36, 26, 54, 17 and 45. What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, the number halfway between them)? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"shape": "list", "values": [68, 62, 62, 11, 58, 70, 36, 26, 54, 17, 45]}
answer: 54
```

### `M1.mode_tally_r2` (family statistics; supersedes `M1.mode_tally`)

structured: {"values": [numbers in the order printed], "ask": "mode" | "mode_count"}. Built from counts: one mode with f occurrences, r in 2..4 rival values with f - 1 each,
and a long tail of values with 1..f - 2 occurrences, then shuffled. Many rivals and many distinct values make the mode's share of the list small, so 'the last value listed',
'the first value repeated' and 'the value near the middle' are uninformative by the construction (no redraw on any heuristic). The ask is drawn first.

Example (level 2):

```
question: A teacher wrote down 42 test scores: 36, 19, 42, 5, 20, 43, 19, 42, 5, 42, 36, 43, 22, 19, 43, 27, 43, 19, 26, 42, 27, 3, 36, 36, 19, 36, 42, 27, 26, 22, 5, 11, 3, 27, 26, 43, 26, 3, 11, 26, 19 and 3. Which value occurs most often? There is exactly one such value. Answer with a whole number.
structured: {"ask": "mode", "values": [36, 19, 42, 5, 20, 43, 19, 42, 5, 42, 36, 43, 22, 19, 43, 27, 43, 19, 26, 42, 27, 3, 36, 36, 19, 36, 42, 27, 26, 22, 5, 11, 3, 27, 26, 43, 26, 3, 11, 26, 19, 3]}
answer: 19
```

### `M1.digit_puzzle_r2` (family algebra; supersedes `M1.digit_puzzle`)

structured: {"digits": 2 | 3, "clues": [[kind, parameter?]]} (kinds digit_sum S, digit_product P, reverse_gap D = reversed number minus the number, multiple_of m, parity, first_gt_last,
digit_relation q = first digit is q times the last, contains_digit d, ends_differ_by d = |first - last|, digits_distinct, middle_is_mean (3 digits)). The reversed number drops a leading zero and the item says so (120 turned round gives 21). The secret is drawn, then clues that hold for it are
added one at a time (at least 2 + (level >= 3) + (level >= 5)) until exactly one number with that many digits (no leading 0) fits all clues; that is the only loop (a unique answer).
The batch-1 redraws 'no single clue leaves fewer than 4 candidates' and 'no clue is redundant' (heuristic-conditional) are withdrawn. Level 0 uses 2-digit, all other levels 3-digit numbers.

Example (level 2):

```
question: Kate of Calder wrote this problem for a maths club. Find the 3-digit number (it does not start with 0) for which all of these are true: its digits add up to 15; the number made by writing its digits in the opposite order (a leading 0 is dropped, so 120 turned round gives 21) is the same as it; its first and last digits differ by 0 (in either order); the product of its digits is 81. There is exactly one such number. Answer with a whole number.
structured: {"clues": [["digit_sum", 15], ["reverse_gap", 0], ["ends_differ_by", 0], ["digit_product", 81]], "digits": 3}
answer: 393
```

### `M1.pythagoras_r2` (family geometry; supersedes `M1.pythagoras`)

structured as batch 1 ({"shape", "legs": [a, b], "hyp": c, "given": [..]}), (a, b, c) an integer Pythagorean triple with c <= limit(level) = 400 + 400 * level (capacity, R-5).

Example (level 2):

```
question: At a maths club in Harrow, Dell is asked this. Fern walks 945 metres due east and then 240 metres due north. How far is Fern now from the starting point in a straight line, in metres? Answer with a whole number.
structured: {"given": [945, 240], "hyp": 975, "legs": [945, 240], "shape": "walk"}
answer: 975
```

### `M1.grid_perimeter_r2` (family geometry; supersedes `M1.grid_perimeter`)

structured: {"rows": [[[first_column, last_column], ...] per row, top row first]}. n = 9 + 3 * level unit squares are placed on distinct cells chosen uniformly at random from a box of
about 3 n cells; some squares touch and some do not. Each row is listed as runs of columns (a row without squares says so). Answer: the perimeter in unit lengths = the number of sides of
squares that do not touch another square of the set (4 n - 2 x the number of touching pairs).
Supersedes grid_perimeter: its shapes were rows of one overlapping run each and a redraw rejected shapes whose perimeter equalled the bounding box's, which moved the mass to 'bounding box + 4'
(0.30 to 0.35). A compact random blob (tried and measured in the scratch notes) keeps the perimeter within a few units of the bounding box's whatever the generator does; a scattered
set does not, so 'bounding box', 'bounding box + 4' and '2 x cells + 2' are uninformative by construction and nothing is redrawn.

Example (level 2):

```
question: Unit squares (each side 1 unit long) are placed on a grid. Row 1 (counting from the top): column 1, column 4, column 6. Row 2 (counting from the top): column 3. Row 3 (counting from the top): columns 3 to 4, column 6. Row 4 (counting from the top): column 4. Row 5 (counting from the top): column 4. Row 6 (counting from the top): columns 2 to 3, column 7. Row 7 (counting from the top): columns 2 to 3, column 5. Squares with the same column number in neighbouring rows sit directly above and below each other, so some squares touch and some do not. The perimeter is the total length of all the sides of squares that do not touch another square. What is the perimeter, in units? Answer with a whole number.
structured: {"rows": [[[1, 1], [4, 4], [6, 6]], [[3, 3]], [[3, 4], [6, 6]], [[4, 4]], [[4, 4]], [[2, 3], [7, 7]], [[2, 3], [5, 5]]]}
answer: 44
```

### `M1.painted_cube_r2` (family geometry; supersedes `M1.painted_cube`)

structured as batch 1 ({"dims", "bottom_unpainted", "faces"}). Faces (0, 1 or 2) drawn first; wider dimensions (capacity, R-5); the redraw 'the answer is not a dimension and is at least 4'
(conditional on 'answer is a printed number') is withdrawn.

Example (level 2):

```
question: This problem comes from a quiz held in Vale, set by Jade. A block is made from small cubes of the same size glued together into a box 6 cubes long, 24 cubes wide and 11 cubes high. The whole box is placed on a table and every outer face is painted red except the bottom face, which stays unpainted. Then the box is taken apart into the small cubes. How many small cubes have exactly 1 painted face? Answer with a whole number.
structured: {"bottom_unpainted": true, "dims": [6, 24, 11], "faces": 1}
answer: 608
```

### `M1.min_cost_packs_r2` (family pricing; supersedes `M1.min_cost_packs`)

structured as batch 1 ({"item", "need", "single", "packs": [[size, price]]}). Answer: the least cost of at least `need` items from singles and packs. All redraws on naive plans are
withdrawn (R-1). By construction: four pack sizes (five from level 5) whose prices are all the SAME per-item rate (60 to 90 percent of the single price, rounded to whole dollars), so no pack
is the bargain and 'biggest pack first', 'best unit price' and 'one kind of pack only' have no structural edge; need is between 2 and 4 times the largest pack. In the measurement the
best of the audit's heuristics ('one kind of pack, floor, then singles') is about 0.25; see the manifest for the exact rates and whether the lineage is marked NOT REGISTERED.

Example (level 2):

```
question: At a shop, one umbrella costs 6 dollars, a pack of 3 umbrellas costs 13 dollars, a pack of 15 umbrellas costs 63 dollars, a pack of 19 umbrellas costs 80 dollars and a pack of 22 umbrellas costs 92 dollars. Hank needs at least 78 umbrellas and wants to spend as little as possible; Hank may buy more than needed and may mix packs and single items. What is the smallest total cost, in dollars? Answer with a whole number.
structured: {"item": "umbrella", "need": 78, "packs": [[3, 13], [15, 63], [19, 80], [22, 92]], "single": 6}
answer: 327
```

### `M1.division_counting_r2` (family division; supersedes `M1.division_counting`)

structured: {"shape": "pallets" | "empty_seats", ...}. The shape is drawn first and no draw is rejected, so the mix is a half each at every level (batch 1: 0.07-0.11 / 0.28 / 0.60-0.65).
pallets {"items": N, "box": k, "crate": m}: items are packed into full boxes of k (items that do not fill a box are left out); boxes go on pallets of m, as many full pallets as possible;
answer the boxes NOT on a full pallet: (N // k) % m (this replaces batch 1's 'crates', which was one ceiling, ceil(N / (k m)), an identity).
empty_seats {"people": N, "seats": k}: buses of k seats, as few as possible; answer the empty seats: ceil(N / k) * k - N.
DROPPED from this revision: batch 1's 'multiples in a range' shape. Without its redraw (R-1) the heuristic 'round((high - low) / d)' is exact on about 0.9 of its items (0.27 to 0.30 of the
whole lineage at every level), because a count of multiples is within one of range / d by construction; there is no construction that removes that, so the shape is dropped (it also
duplicates R2.multiples_between, audit section 3).

Example (level 2):

```
question: 867 people must travel by bus, and Kai hires as few buses as possible. Each bus has 31 seats, and nobody stands. When all 867 people are on board, how many seats in total are empty? Answer with a whole number.
structured: {"people": 867, "seats": 31, "shape": "empty_seats"}
answer: 1
```
