# M1 batch 1 lineages: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything.

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field: a whole number, or a decimal with at most two places and no trailing zeros (a negative sign never occurs in this batch). It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`M1.<name>`); one module per family, `studies/m0/solvers_m1_<family>.py` (family names in the lineage headings below).
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Fixtures: `studies/m0/fixtures/m1_batch1/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. `answer_type` is always `number` and `k` is null. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).
- The question text is in the fixture only so that an auditor can check the wording, the stated answer format and the units against the structured form; solvers must not parse it.
- Every question states its answer format inside the item ("Answer with a whole number." or the decimal sentence); units are named in the question where they matter (centimetres, seconds, dollars); there is no rounding anywhere: every answer is exact.
- Solvers should use a different method from the one described here where possible (for example brute-force enumeration instead of a closed form), so that the pair is a real check.

## Lineages (family, strict procedure, the builder's description of its structured form and answer rule)

### `M1.binomial_choose` (family counting, firmness: firm)

Strict procedure: Unordered selection: choose k of n by the binomial coefficient, optionally with a forced member or an exact split between two groups (product of two coefficients).

structured: {"shape": "plain" | "include" | "two_groups", "n": n, "k": k, "x": x, "y": y, "j": j}. plain: choose k of n people (order does not matter): C(n, k).
include: as plain but one named person must be in the group: C(n - 1, k - 1). two_groups: x women and y men, choose k with exactly j women: C(x, j) * C(y, k - j).
(Fields not used by a shape are 0.)

Example (level 2):

```
question: Jules from Oakham found this problem in a puzzle book. A club has 9 members. A committee of 4 members is chosen (the order of choosing does not matter). How many different committees are possible? Answer with a whole number.
structured: {"j": 0, "k": 4, "n": 9, "shape": "plain", "x": 0, "y": 0}
answer: 126
```

### `M1.change_ways` (family counting, firmness: borderline)

Strict procedure: Count the non-negative integer solutions of a linear coin equation (dynamic programming / systematic enumeration of the number of each coin).

structured: {"coins": [values in cents, distinct], "target": T}. Answer: the number of different multisets of coins (unlimited supply of each value) that add up to exactly T cents.
Borderline against digit_puzzle (both enumerate integer solutions of linear constraints); here the answer counts all solutions.

Example (level 2):

```
question: Using only coins worth 3, 7 and 9 cents, with as many coins of each value available as you like, in how many different ways can exactly 79 cents be paid? (Two ways are the same if they use the same number of coins of each value; the order does not matter.) Answer with a whole number.
structured: {"coins": [3, 7, 9], "target": 79}
answer: 21
```

### `M1.crt_congruence` (family number_theory, firmness: firm)

Strict procedure: Simultaneous congruences with coprime moduli: find the least positive number meeting every remainder condition (search / Chinese remainder construction).

structured: {"conditions": [[modulus, remainder]]} with pairwise coprime moduli and 0 < remainder < modulus.
Answer: the smallest positive whole number that leaves each remainder on division by its modulus (it is at most the product of the moduli).

Example (level 2):

```
question: Kurt is thinking of a positive whole number. Dividing it by 11 leaves remainder 7; dividing it by 8 leaves remainder 5. What is the smallest positive whole number that Kurt could be thinking of? Answer with a whole number.
structured: {"conditions": [[11, 7], [8, 5]]}
answer: 29
```

### `M1.digit_puzzle` (family algebra, firmness: firm)

Strict procedure: Generate-and-test over all candidate numbers: keep the digit strings that meet every clue until exactly one remains.

structured: {"digits": 2 | 3, "clues": [[kind, parameter?]]} with kinds digit_sum S, digit_product P, reverse_gap D (reversed number minus the number), multiple_of m, parity "even"|"odd",
first_gt_last, digit_relation q (first digit = q times last digit). Answer: the one number with that many digits (no leading zero) for which every clue holds; the generator
checks, by testing all candidates, that it is unique and that dropping any one clue leaves more than one candidate.

Example (level 2):

```
question: Ada of Kelso wrote this problem for a maths club. Find the 3-digit number (it does not start with 0) for which all of these are true: the product of its digits is 40; reversing its digits gives a number that is 198 more than it. There is exactly one such number. Answer with a whole number.
structured: {"clues": [["digit_product", 40], ["reverse_gap", 198]], "digits": 3}
answer: 254
```

### `M1.division_counting` (family division, firmness: firm)

Strict procedure: Whole-number division with floor and ceiling: nested packing (ceil of ceil), counting multiples in a range (floor of the top minus floor of the bottom), and empty seats after filling vehicles.

structured: {"shape": "crates" | "multiples" | "empty_seats", ...}. crates: {"items": N, "box": k, "crate": m}: N items go into boxes of k (the last box may be partly filled), the boxes go
into crates holding m boxes (the last crate may be partly filled); answer the number of crates: ceil(ceil(N / k) / m). multiples: {"low": a, "high": b, "div": d}: how many whole numbers from a to b
inclusive are divisible by d: floor(b / d) - floor((a - 1) / d). empty_seats: {"people": N, "seats": k}: buses of k seats each carry everyone in as few buses as possible; answer the empty seats overall: ceil(N / k) * k - N.
The generator rejects items where the answer equals the plain rounded quotient.

Example (level 2):

```
question: 856 people must travel by bus, and Ulf hires as few buses as possible. Each bus has 27 seats, and nobody stands. When all 856 people are on board, how many seats in total are empty? Answer with a whole number.
structured: {"people": 856, "seats": 27, "shape": "empty_seats"}
answer: 8
```

### `M1.finite_differences` (family sequences, firmness: firm)

Strict procedure: Polynomial pattern extension: build the table of differences until it is constant, then extend it to the asked position.

structured: {"terms": [the printed first terms, positions 1..m], "degree": 2 | 3, "ask": position}. The terms come from an integer polynomial of the stated degree in the position.
Answer: the term at position `ask` (m + 1 or m + 2), found by extending the table of differences (or by fitting the polynomial).

Example (level 2):

```
question: Lila of Norwick wrote this problem for a maths club. The first 5 numbers of a pattern are 20, 42, 72, 110 and 156. The pattern continues in the same way, and each number is given by a polynomial of degree 2 in its position (position 1 is the first number). What is the number in position 6? Answer with a whole number.
structured: {"ask": 6, "degree": 2, "terms": [20, 42, 72, 110, 156]}
answer: 210
```

### `M1.gcd_lcm` (family number_theory, firmness: firm)

Strict procedure: Euclid / prime-exponent comparison: the greatest common divisor, or the least common multiple, of 2-4 whole numbers.

structured: {"ask": "gcd" | "lcm", "values": [positive integers, distinct]}.
gcd: the largest whole length that divides every value exactly (ribbons cut with nothing left over). lcm: the smallest positive time at which
every periodic event (periods = values) happens together again, all having started together. Generator guarantees gcd >= 2 and gcd < min(values),
or max(values) < lcm < product(values); with three or four values, dropping any one value changes the answer; for gcd no two values differ by exactly the answer.

Example (level 2):

```
question: Hal has 2 ribbons of lengths 304 and 416 centimetres. Hal cuts every ribbon into pieces that all have the same whole-number length in centimetres, with nothing left over from any ribbon. What is the greatest possible length of a piece, in centimetres? Answer with a whole number.
structured: {"ask": "gcd", "values": [304, 416]}
answer: 16
```

### `M1.grid_perimeter` (family geometry, firmness: firm)

Strict procedure: Exposed-edge counting: perimeter = 4 x squares - 2 x (number of shared edges between neighbouring squares) for a tiled shape given row by row.

structured: {"rows": [[first_column, last_column]] from the top row down}. Unit squares fill, in each row, every column from first to last (inclusive); consecutive rows share at least one column.
Answer: the perimeter of the whole shape in unit lengths (every side of a unit square that has no unit square of the shape on its other side). The generator rejects shapes whose
perimeter equals that of their bounding box.

Example (level 2):

```
question: Unit squares (each side 1 unit long) are placed on a grid to make one shape. Row 1 (counting from the top) has squares in columns 3 to 5, both included. Row 2 (counting from the top) has squares in columns 3 to 8, both included. Row 3 (counting from the top) has squares in columns 6 to 7, both included. Row 4 (counting from the top) has squares in columns 4 to 10, both included. Every column number is a position along the row, so squares with the same column number in neighbouring rows sit directly above and below each other. What is the perimeter of the whole shape, that is, the total length of its outer boundary, in units? Answer with a whole number.
structured: {"rows": [[3, 5], [3, 8], [6, 7], [4, 10]]}
answer: 30
```

### `M1.inclusion_exclusion` (family counting, firmness: firm)

Strict procedure: Inclusion-exclusion over 2 or 3 overlapping groups (add sizes, subtract pair overlaps, add the triple overlap) to count the union, its complement, or exactly one / two groups.

structured: {"total": N, "sets": [name], "sizes": [|A|, ...], "pairs": [|A and B|, ...] (2 sets: one entry; 3 sets: AB, AC, BC), "triple": |A and B and C| or null,
"ask": "none" | "any" | "exactly_one" | "exactly_two"}. Answer: how many of the N people are in none of the sets / at least one set / exactly one / exactly two,
by inclusion-exclusion over the stated overlaps. The answer is never one of the stated numbers.

Example (level 2):

```
question: 41 people were asked what they do. 21 of them swim, 27 of them play chess, and 15 of them do both. How many of the 41 people do at least one of these things? Answer with a whole number.
structured: {"ask": "any", "pairs": [15], "sets": ["swim", "play chess"], "sizes": [21, 27], "total": 41, "triple": null}
answer: 33
```

### `M1.last_digit_power` (family number_theory, firmness: borderline)

Strict procedure: Cycle detection: the last digit of a power repeats with a short period, so reduce the exponent modulo the period, then combine terms modulo 10.

structured: {"op": "sum" | "product", "terms": [[base, exponent]]}. Answer: the last (units) digit of the sum (or product) of the numbers base**exponent.
Borderline: modular arithmetic like crt_congruence, but the procedure is cycle-finding in the last digit of powers.

Example (level 2):

```
question: At a maths club in Quarry, Yuri is asked this. Let the number X be 12 raised to the power 44 times 58 raised to the power 75 (the power means 12 multiplied by itself 44 times, and likewise for the others). What is the last digit of X, that is, its digit in the units place? Answer with a whole number.
structured: {"op": "product", "terms": [[12, 44], [58, 75]]}
answer: 2
```

### `M1.median_list` (family statistics, firmness: firm)

Strict procedure: Order statistic: sort the values (expanding a frequency table by its counts), then take the middle value or the mean of the two middle values.

structured: {"shape": "list" | "table", "values": [numbers in the order printed] (list) or [[value, how_many], ...] (table)}.
Answer: the median: sort all the values (a table row counts `how_many` times); the middle value if the count is odd, the mean of the two middle values if even.

Example (level 2):

```
question: The values are 29, 29, 29, 59, 35, 46, 38 and 60. What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, the number halfway between them)? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"shape": "list", "values": [29, 29, 29, 59, 35, 46, 38, 60]}
answer: 36.5
```

### `M1.min_cost_packs` (family pricing, firmness: firm)

Strict procedure: Minimum-cost combination: compare mixes of pack deals and single items, including buying more than needed, by searching over how many of each pack to buy.

structured: {"item": word, "need": N, "single": s, "packs": [[size, price]]} (prices in whole dollars; a pack is not always a bargain). Answer: the least total cost in dollars of buying AT LEAST `need` items,
using any mix of singles and packs (buying more than needed is allowed). The class of the item is drawn first: half the items are drawn (by repeated parameter draws inside the builder) so that the optimum is
found by none of five naive plans (singles only; biggest pack floor + singles; biggest pack ceil; best-unit-price pack floor + singles; best-unit-price pack ceil), the other half so that exactly one named naive plan
(drawn uniformly; no other naive plan reaches the same cost) reaches it.

Example (level 2):

```
question: At a shop, one orange costs 5 dollars, and a pack of 7 oranges costs 36 dollars and a pack of 12 oranges costs 63 dollars. Lars needs at least 18 oranges and wants to spend as little as possible; Lars may buy more than needed and may mix packs and single items. What is the smallest total cost, in dollars? Answer with a whole number.
structured: {"item": "orange", "need": 18, "packs": [[7, 36], [12, 63]], "single": 5}
answer: 90
```

### `M1.mode_tally` (family statistics, firmness: borderline)

Strict procedure: Frequency tally: count each value's occurrences and select the unique most frequent value (or its count).

structured: {"values": [numbers in the order printed], "ask": "mode" | "mode_count"}. Tally how often each value occurs; the most frequent value is unique in every item.
Answer: that value ("mode"), or how many times it occurs ("mode_count"). The printed order is drawn so that the first value to repeat is the mode in only a minority of items.
Borderline against median_list (statistic of a list; here the procedure is a tally, not a sort).

Example (level 2):

```
question: A teacher wrote down 10 test scores: 23, 23, 24, 3, 21, 23, 23, 24, 23 and 21. How many times does the most frequent value occur? There is exactly one most frequent value. Answer with a whole number.
structured: {"ask": "mode_count", "values": [23, 23, 24, 3, 21, 23, 23, 24, 23, 21]}
answer: 5
```

### `M1.painted_cube` (family geometry, firmness: firm)

Strict procedure: Region decomposition of a box of unit cubes (corners, edges, faces, interior) to count cubes by number of painted faces, with the bottom possibly unpainted.

structured: {"dims": [a, b, c], "bottom_unpainted": true | false, "faces": f}. A block a x b x c is built from unit cubes, then every outer face is painted (except the bottom face if
`bottom_unpainted`) and the block is taken apart. Answer: how many unit cubes have exactly f painted faces (f is 0, 1 or 2).

Example (level 2):

```
question: This problem comes from a quiz held in Thornbury, set by Raul. A block is made from small cubes of the same size glued together into a box 5 cubes long, 6 cubes wide and 5 cubes high. The whole box is placed on a table and every outer face (including the bottom) is painted red. Then the box is taken apart into the small cubes. How many small cubes have exactly 0 painted faces? Answer with a whole number.
structured: {"bottom_unpainted": false, "dims": [5, 6, 5], "faces": 0}
answer: 36
```

### `M1.pigeonhole_worst_case` (family counting, firmness: firm)

Strict procedure: Worst-case (adversarial) draw counting: an unlucky draw takes as many of each colour as it can without reaching the goal, then one more.

structured: {"counts": [n_1..n_c] (items per colour in a bag), "goal": "same" | "all", "k": k}. Items are drawn blindly one at a time without replacement.
Answer: the number of draws that GUARANTEES, however unlucky, either k items of one colour (goal "same") or at least one item of every colour (goal "all", k = 1).
same: 1 + sum(min(n_i, k - 1)); all: total - min(n_i) + 1. The generator requires the cap min(n_i, k - 1) to bite for goal "same".

Example (level 2):

```
question: A bag holds marbles of 4 colours: 4 white, 15 purple, 8 black, 8 red. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the draws are, of having at least 10 marbles of the same colour? Answer with a whole number.
structured: {"counts": [4, 15, 8, 8], "goal": "same", "k": 10}
answer: 30
```

### `M1.prime_factors` (family number_theory, firmness: firm)

Strict procedure: Prime factorisation of one number by trial division, then read off a divisor count, largest prime, distinct-prime sum or prime-factor count.

structured: {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. N is factorised into primes.
divisors: how many positive whole numbers divide N exactly (1 and N included). largest: the largest prime that divides N. distinct_sum: the sum of the
different primes that divide N. factor_count: how many primes are multiplied when N is written as a product of primes (a prime used twice counts twice).

Example (level 2):

```
question: Nico from Upton found this problem in a puzzle book. Consider the number 22295. What is the largest prime number that divides it exactly? Answer with a whole number.
structured: {"ask": "largest", "n": 22295}
answer: 13
```

### `M1.pythagoras` (family geometry, firmness: firm)

Strict procedure: Pythagorean relation: combine or separate squared side lengths of a right triangle (ladder, walk, diagonal, perimeter) with whole-number triples.

structured: {"shape": "ladder_top" | "ladder_base" | "walk" | "diagonal" | "perimeter", "legs": [a, b], "hyp": c, "given": [..the numbers in the item..]}; (a, b, c) is a Pythagorean triple.
ladder_top: a ladder of length c leans on a wall, its foot is a from the wall; answer the height reached. ladder_base: length c, reaching height a; answer the distance of the foot.
walk: walk a east then b north; answer the straight-line distance back. diagonal: a rectangle a by b; answer its diagonal. perimeter: a right triangle with legs a and b; answer its perimeter.

Example (level 2):

```
question: At a maths club in Westmere, Zara is asked this. A rectangular screen is 20 centimetres wide and 99 centimetres tall. What is the length of its diagonal, in centimetres? Answer with a whole number.
structured: {"given": [20, 99], "hyp": 101, "legs": [20, 99], "shape": "diagonal"}
answer: 101
```

### `M1.quadratic_area` (family algebra, firmness: firm)

Strict procedure: Solve a quadratic equation arising from a rectangle (area, or area with perimeter) or from a product or sum of squares of two numbers a given amount apart; keep the positive whole root.

structured: {"shape": "rect_area" | "rect_perimeter" | "product" | "squares", "d": d, "area": A, "perimeter": P, "total": S}. All answers are the positive whole root x of a quadratic.
rect_area: width x, length x + d, area A; answer x. rect_perimeter: a rectangle with perimeter P and area A; answer the LONGER side. product: two whole numbers that differ by d have product A;
answer the smaller. squares: two whole numbers that differ by d have squares adding up to S; answer the smaller. (Fields not used by a shape are 0.) d >= 3.

Example (level 2):

```
question: At a maths club in Garth, Jon is asked this. A rectangular garden has an area of 3318 square metres. Its length is 37 metres more than its width. What is its width, in metres? Answer with a whole number.
structured: {"area": 3318, "d": 37, "perimeter": 0, "shape": "rect_area", "total": 0}
answer: 42
```

### `M1.recurrence_iterate` (family sequences, firmness: firm)

Strict procedure: Unroll a stated recurrence (sum of the two previous terms, an affine map, or previous term plus its index) step by step to the asked position.

structured: {"shape": "sum_prev_two" | "affine" | "add_index", "first": [a] or [a, b], "mult": c, "add": d, "position": n}. Terms are numbered from 1.
sum_prev_two: every term after the second is the sum of the two before it. affine: every term after the first is mult * previous + add.
add_index: every term after the first is the previous term plus its own position number. Answer: the term at `position`, by applying the rule step by step.

Example (level 2):

```
question: Nico of Selby wrote this problem for a maths club. A list of numbers is built by a rule. The first number is 27. Every number after it is 2 times the number just before it, plus 14. What is the number in position 8 of the list (position 1 is the first number)? Answer with a whole number.
structured: {"add": 14, "first": [27], "mult": 2, "position": 8, "shape": "affine"}
answer: 5234
```

### `M1.slot_permutations` (family counting, firmness: firm)

Strict procedure: Ordered slot-filling with position restrictions: count digit strings position by position (most restricted position first), with or without repeats.

structured: {"digits": [allowed digits], "length": s, "repeat": true | false, "lead_nonzero": true | false, "parity": "even" | "odd" | "any"}.
Answer: how many s-digit numbers (every position filled from `digits`; no digit used twice unless `repeat`; first digit not 0 if `lead_nonzero`;
last digit of the stated parity) exist. Counted by filling the most restricted positions first.

Example (level 2):

```
question: How many 4-digit numbers can be written using only the digits 0, 1, 2, 3, 4, 7, 8 and 9, if no digit may be used more than once, the number may not start with the digit 0 and the number must be odd? Answer with a whole number.
structured: {"digits": [0, 1, 2, 3, 4, 7, 8, 9], "lead_nonzero": true, "length": 4, "parity": "odd", "repeat": false}
answer: 720
```

### `M1.tiered_pricing` (family pricing, firmness: firm)

Strict procedure: Marginal-rate accumulation over price steps: charge each unit at the rate of its own step (forward), or invert the step totals to recover the units from a bill.

structured: {"mode": "bill" | "units", "tiers": [[units_in_tier, cents_per_unit]] for every tier but the last, "last_rate": cents_per_unit above all tiers, "used": U or null, "bill_cents": B or null}.
Each unit is charged at the rate of the tier it falls in (marginal rates: the first tiers[0][0] units at tiers[0][1], the next tiers[1][0] at tiers[1][1], ..., all further units at last_rate).
bill: answer the bill for U units in dollars (a number with at most two decimals). units: answer the whole number of units U that gives a bill of B cents. Generator makes U exceed every tier boundary at higher levels.

Example (level 2):

```
question: A utility charges for use in steps: the first 17 units cost 16 cents each, the next 50 units cost 32 cents each, and every unit after that costs 44 cents each. Each unit costs the rate of the step it falls in (a higher step does not change what earlier units cost). What is the bill for 91 units, in dollars? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"bill_cents": null, "last_rate": 44, "mode": "bill", "tiers": [[17, 16], [50, 32]], "used": 91}
answer: 29.28
```
