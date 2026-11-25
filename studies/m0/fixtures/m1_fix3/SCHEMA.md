# M1 fix round 3: structured-form schema for the second-solver agent (registered candidates only)

Written by the implementer. Not a result; nothing here approves anything. A second solver reads ONLY `structured` (never the question text, never the key) and returns the answer string exactly as in the fixture; it raises ValueError when the answer is not unique. Fixtures: `studies/m0/fixtures/m1_fix3/<id>.jsonl`, 20 items per level (0 and 6 reserve), structurally distinct across ALL levels of one file. NOT REGISTERED lineages have no fixtures (their builders stay on file as attempts). `min_cost_packs` is excluded everywhere.

Every answer format and convention is stated in the item text (answer format, units, sign, inclusive or exclusive counts, leading zeros, what a perimeter counts, what a full pallet is).

## Lineages

### `M1.ages_r3` (family age)

structured {"k", "t", "sum", "ask": "younger" | "older"}. n1 is k times as old as n2 now; in t years their ages add up to `sum`. The ask (drawn first) is the younger person's age now or the older person's age now.
Ranges widened: younger age 3..70+10*level, k 2..6+level//2, t 1..15+level. Ages are whole numbers of years.

Example (level 2):

```
question: Sam is 6 times as old as Zed now. In 12 years from now, their two ages added together will be 556. All ages are whole numbers of years. How old is Sam now, in years? Answer with a whole number.
structured: {"ask": "older", "k": 6, "sum": 556, "t": 12}
answer: 456
```

### `M1.arithmetic_series_r3` (family series)

structured {"first": a, "step": d, "days": n}. a 1..99, d 1..30, n 4..12+3*level days; day 1 is the first day and the total counts days 1..n inclusive.

Example (level 2):

```
question: Sia saves 69 dollars on day 1 and then saves 20 dollars more each day than on the day before. How many dollars has Sia saved in total after 18 days (counting day 1 to day 18, both included)? Answer with a whole number.
structured: {"days": 18, "first": 69, "step": 20}
answer: 4302
```

### `M1.average_missing_r3` (family average)

structured {"scores": [..], "mean_cents": c, "n": n}. n = 4 + level // 2 tests, scores 40..100. The missing score is drawn from the values that make the mean a number with at most two decimals
(batch 1 retried), so no draw is rejected.

Example (level 2):

```
question: Greta has scored 57, 51, 75, 88 on 4 tests, each marked out of 100 with whole-number marks. What score is needed on the next test to make the mean of all 5 tests exactly 66.6? Answer with a whole number.
structured: {"mean_cents": 6660, "n": 5, "scores": [57, 51, 75, 88]}
answer: 62
```

### `M1.change_ways_r3` (family counting)

structured {"coins": [3 values in cents], "target": T}. Coins drawn from 17 values (2..9, 10, 12, 15, 20, 25, 30, 40, 50); T = sum of c_i * x_i (x_i uniform 0..5+2*level) + 6 * smallest coin, so at least one
way exists by construction. Answer: the number of multisets of coins summing to T (a change-making table). No redraw.

Example (level 2):

```
question: This problem comes from a quiz held in Ravenna, set by Greta. Using only coins worth 4, 6 and 9 cents, with as many coins of each value available as you like, in how many different ways can exactly 87 cents be paid? (Two ways are the same if they use the same number of coins of each value; the order does not matter.) Answer with a whole number.
structured: {"coins": [4, 6, 9], "target": 87}
answer: 21
```

### `M1.clock_duration_r3` (family time)

structured {"legs": [[departure_minutes, arrival_minutes]]}. 2 + level // 2 legs on one day. Waits 5..60 minutes and rides 20..150 minutes are drawn first; the first departure is then drawn from
05:00..min(14:00, the latest start that still ends before midnight), which is never empty for five legs (worst case 1050 minutes), so nothing is redrawn (batch 1 retried).

Example (level 2):

```
question: A journey has several legs on the same day (times on a 24-hour clock): leg 1 leaves at 12:51 and arrives at 14:12; leg 2 leaves at 14:55 and arrives at 16:54; leg 3 leaves at 17:08 and arrives at 19:05. How many minutes in total is the traveller actually on the move (the time between each leg's departure and its arrival, not counting the waiting between legs)? Answer with a whole number.
structured: {"legs": [[771, 852], [895, 1014], [1028, 1145]]}
answer: 317
```

### `M1.coins_r3` (family coins)

structured {"lo", "hi", "count", "cents", "ask": "lo" | "hi"}. The coin pair is drawn from pairs with hi / lo <= 10 (1,2,5,10,20,25,50,100,200 cents). Counts: the number of LOW coins is at least
ceil(hi / lo) (so the low coins are worth at least one high coin), 2..30+4*level otherwise; this is a range of the draw, not a retry, and it makes 'total value / high coin' wrong by construction
(audit: +0.12 to +0.17). Answer: the count of the asked coin.

Example (level 2):

```
question: A jar holds only 2-cent coins and 10-cent coins. It holds 12 coins worth 64 cents in all. How many 10-cent coins are in the jar? Answer with a whole number.
structured: {"ask": "hi", "cents": 64, "count": 12, "hi": 10, "lo": 2}
answer: 5
```

### `M1.consecutive_r3` (family linear)

structured {"count": n, "step": 1 | 2, "sum": S, "ask": "largest" | "smallest"}. n = 3 + level // 2 numbers in a row (step 2 allowed from level 2); first number -200..4000+2000*level (may be negative).

Example (level 2):

```
question: The sum of 4 consecutive integers (listed from smallest to largest, positive or negative whole numbers) is 14250. What is the largest of them? Answer with a whole number (write a minus sign if it is negative).
structured: {"ask": "largest", "count": 4, "step": 1, "sum": 14250}
answer: 3564
```

### `M1.crt_congruence_r3` (family number_theory)

structured {"conditions": [[modulus, remainder]]}. Pairwise coprime moduli, every modulus >= 9 (k = 2 below level 3: up to 60 + 10 * level; k = 3, 4: up to 24 + 4 * level), remainder 1..m-1 uniformly.
The answer is the least positive solution. Moduli of 9 or more make 'the remainder of the largest modulus' and 'the solution of all but the last condition' right only with chance about 1 / modulus
(audit: +0.09 to +0.12 with moduli from 3); nothing is redrawn on the answer.

Example (level 2):

```
question: Viv is thinking of a positive whole number. Dividing it by 35 leaves remainder 27; dividing it by 62 leaves remainder 44. What is the smallest positive whole number that Viv could be thinking of? Answer with a whole number.
structured: {"conditions": [[35, 27], [62, 44]]}
answer: 1532
```

### `M1.division_counting_r3` (family division)

structured {"shape": "pallets" | "empty_seats", ...}. Shape drawn first (half each). pallets {"items": N, "box": k, "crate": m}: answer (N // k) % m, the boxes not on a full pallet.
empty_seats {"people": N, "seats": k}: answer ceil(N / k) * k - N. Ranges widened (rev2 level 0 had 20,040 distinct items): box 4..30+3*level, pallet 3..20+2*level, seats 8..60+5*level.

Example (level 2):

```
question: Gwen of Quarry wrote this problem for a maths club. A factory makes 3234 spoons. They are packed into boxes that each hold exactly 27 spoons; spoons that do not fill a box are left out. The boxes are then put on pallets that each hold 7 boxes, and as many full pallets as possible are made. How many boxes are not on a full pallet? Answer with a whole number.
structured: {"box": 27, "crate": 7, "items": 3234, "shape": "pallets"}
answer: 0
```

### `M1.finite_differences_r3` (family sequences)

structured {"terms": [the printed first terms, positions 1..m], "degree": 2 | 3, "ask": position}. Integer polynomial with NON-NEGATIVE coefficients (so every term is positive, no retry): degree 2 below level 5:
a 1..15, b 0..25, c 0..60; degree 3 from level 5: coefficients 0..60, 0..20, 0..9 and a leading 1..4. m = degree + 3 + (level >= 3) terms printed (positions 1..m); ask = m + 1 or m + 2.
Answer: the term at the asked position (extend the table of differences or fit the polynomial). Batch 1 retried on negative or repeated terms and had a space of about 5,000 items.

Example (level 2):

```
question: This problem comes from a quiz held in Harrow, set by Reed. The first 5 numbers of a pattern are 62, 83, 106, 131 and 158. The pattern continues in the same way, and each number is given by a polynomial of degree 2 in its position (position 1 is the first number). What is the number in position 6? Answer with a whole number.
structured: {"ask": 6, "degree": 2, "terms": [62, 83, 106, 131, 158]}
answer: 187
```

### `M1.fraction_remainder_r3` (family remainder)

structured {"start": n, "a": a, "b": b}. a, b in 2..12 (one a-th, then one b-th of what is left). n is a multiple of a * b / gcd(b, a - 1), the least start for which both spends are whole
numbers of dollars, up to 3000 + 500 * level (a bound on size, not a retry).

Example (level 2):

```
question: Sam has 2835 dollars. Sam spends one fifth of it on books, then one ninth of what is left on lunch. How many dollars does Sam have left? Answer with a whole number.
structured: {"a": 5, "b": 9, "start": 2835}
answer: 2016
```

### `M1.gcd_lcm_r3` (family number_theory)

structured {"ask": "gcd" | "lcm", "values": [positive integers]}. Ask drawn first; pairwise coprime q_1..q_k (k = 2 below level 3, 3 for levels 3-4, 4 from level 5; q <= 50 / 30 / 24) and a common
factor g (2..40 / 24 / 24). The values depend on the ask, BY CONSTRUCTION:
  gcd: v_i = g * prod(q_j, j != i). gcd(values) = g exactly, while the gcd of ANY proper subset is larger (it contains the omitted q's), so 'gcd of the two smallest', 'of the two largest',
  'of the first two', 'smallest value', 'smallest difference' are not the gcd (audit: gcd of the two smallest +0.32 to +0.38 with values d * u for random u).
  lcm: v_i = g * q_i. lcm(values) = g * prod(q), while the lcm of any proper subset is smaller, so 'lcm of the two largest' and 'lcm of the first two' are not the lcm, and neither is the product
  (it carries g^k) nor the largest value. (The dual construction would make the lcm of any two values the lcm of all: first attempt, measured +0.49 on the lcm ask, kept in the notes.)
gcd: the longest ribbon piece cutting every ribbon exactly; lcm: the first common flash time.

Example (level 2):

```
question: Otto has 2 ribbons of lengths 714 and 884 centimetres. Otto cuts every ribbon into pieces that all have the same whole-number length in centimetres, with nothing left over from any ribbon. What is the greatest possible length of a piece, in centimetres? Answer with a whole number.
structured: {"ask": "gcd", "values": [714, 884]}
answer: 34
```

### `M1.grid_perimeter_r3` (family geometry)

structured {"rows": [[[first_column, last_column], ...] per row, top row first]}. n unit squares (n uniform on 5+3*level .. 13+3*level; rev2 had exactly 9+3*level) on distinct random cells of a box
of about d * n cells (d drawn from 2, 3, 4). Wording (one reading only): two squares that share a SIDE are glued along it; the perimeter is the number of unit sides that belong to exactly ONE square
(a side shared by two squares is not counted at all; squares that meet only at a corner share no side). Key: 4 n - 2 * (number of shared sides). The wider spread of n and of the density spreads the
answer (rev2: the most frequent answer was 0.13-0.24).

Example (level 2):

```
question: Unit squares (each side 1 unit long) are placed on a grid. Row 1 (counting from the top): columns 4 to 5. Row 2 (counting from the top): columns 1 to 2, column 6. Row 3 (counting from the top): column 1. Row 4 (counting from the top): column 6, column 8. Row 5 (counting from the top): column 4, column 7. Row 6 (counting from the top): column 5, column 8. Row 7 (counting from the top): columns 1 to 2, column 6. Row 8 (counting from the top): column 2. Squares with the same column number in neighbouring rows sit directly above and below each other. Two squares that share a side are glued together along that side (squares that meet only at a corner share no side). The perimeter of the whole figure is the number of unit-length sides that belong to exactly one square: a side shared by two squares is not counted at all. What is the perimeter of the figure, in units? Answer with a whole number.
structured: {"rows": [[[4, 5]], [[1, 2], [6, 6]], [[1, 1]], [[6, 6], [8, 8]], [[4, 4], [7, 7]], [[5, 5], [8, 8]], [[1, 2], [6, 6]], [[2, 2]]]}
answer: 54
```

### `M1.inclusion_exclusion_r3` (family counting)

structured {"total", "sets", "sizes", "pairs", "triple", "ask"}. As rev2 with a wider region size (1..20+8*level; rev2 had 1..8+8*level, which gave only 4,356 distinct level-0 items) and an explicit
convention: in a three-set item every 'do both' number includes the people who do all three.

Example (level 2):

```
question: 74 people were asked what they do. 19 of them play tennis, 36 of them sing in the choir, and 8 of them do both. How many of the 74 people do at least one of these things? Answer with a whole number.
structured: {"ask": "any", "pairs": [8], "sets": ["play tennis", "sing in the choir"], "sizes": [19, 36], "total": 74, "triple": null}
answer: 47
```

### `M1.last_digit_power_r3` (family number_theory)

structured {"modulus": p, "op": "sum" | "product", "terms": [[base, exponent]]}. As rev2 with the prime set {29, 37, 43, 47, 53, 59, 67, 79} (all have p - 1 not a multiple of 5);
a larger p flattens the answer distribution (rev2 with p in 17..29: the most frequent answer was 0.15-0.16 at levels 0-1; a first widening to 17..59 gave 0.117). Each term is the product of `exponent` factors, each equal to `base` (stated).

Example (level 2):

```
question: Jana of Ivybridge wrote this problem for a maths club. Let X be the product of all the following factors: 223 factors equal to 35 and 152 factors equal to 64. What is the remainder when X is divided by 37 (a whole number from 0 to 36)? Answer with a whole number.
structured: {"modulus": 37, "op": "product", "terms": [[35, 223], [64, 152]]}
answer: 2
```

### `M1.linear_equation_r3` (family linear)

structured {"k", "m", "j", "n"}: k*x + m = n (j = 0) or k*x + m = j*x + n (j != 0). The constants are never 0 (batch 1 could print 'adding 0'); the answer may be negative and the item says how to write it.

Example (level 2):

```
question: I think of a number. Multiplying it by 6 and then subtracting 20 gives 22. What is my number? Answer with a whole number (write a minus sign if it is negative).
structured: {"j": 0, "k": 6, "m": -20, "n": 22}
answer: 7
```

### `M1.median_list_r3` (family statistics)

structured {"shape": "list", "values": [..]}. n = 7+level .. 10+2*level values (so odd and even counts both occur), each 1..200+60*level (rev2: 1..30+20*level); repeats are rare, so 'the mode of the values' and
'a printed value at a fixed position' are right only by chance (audit: +0.155 at level 0). Answer: the median (the mean of the two middle values when the count is even), at most two decimals.

Example (level 2):

```
question: At a maths club in Oakham, Hana is asked this. The values are 18, 254, 253, 297, 304, 66, 289, 81 and 263. What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, the number halfway between them)? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"shape": "list", "values": [18, 254, 253, 297, 304, 66, 289, 81, 263]}
answer: 254
```

### `M1.mixture_r3` (family ratio)

structured {"x", "y", "a", "b", "packing"}. Batch 1 retried until the cost was a whole number of cents, which favoured x = y (the unweighted mean of the two prices was right on 0.24-0.28).
Here the total weight s = x + y is drawn from the divisors of 100 that give no equal split by default (5, 10, 20, 25, 50, 100), x uniformly in 1..s-1, and the two prices are DIFFERENT, so every
mean is a whole number of cents by construction and no retry exists. Levels >= 3 add a flat packing cost of p dollars (1..9) per kilogram.

Example (level 2):

```
question: A shop mixes 9 kilograms of nuts costing 17 dollars per kilogram with 11 kilograms of raisins costing 23 dollars per kilogram. What is the cost of one kilogram of the finished mixture, in dollars? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"a": 17, "b": 23, "packing": 0, "x": 9, "y": 11}
answer: 20.3
```

### `M1.mode_tally_r3` (family statistics)

structured {"values": [..], "ask": "mode" | "others"}. Ask drawn first. One mode occurring f times (f 4..6), R rivals (7..10) occurring f - 1 times each, and a tail of T (2..4) values occurring
1..f - 2 times, then shuffled. 'mode': which value occurs most often. 'others' (replaces rev2's 'how many times does the mode occur', whose answer had only 4-8 possible values, a most frequent answer of
0.15 at level 0): how many of the scores are NOT equal to the most frequent value (n - f, a number that varies over about 30 values). Both need the full frequency table. More rivals than rev2 (2-4) lower
the chance that 'the first value that repeats' or 'the most common value of the first half' is the mode. There is exactly one most frequent value (said in the item). The list grows with the level only
through the value range (a longer list would be a different task).

Example (level 2):

```
question: A teacher wrote down 46 test scores: 15, 42, 35, 32, 34, 67, 22, 42, 25, 15, 56, 35, 25, 51, 16, 22, 32, 56, 22, 16, 22, 42, 56, 15, 32, 16, 67, 35, 14, 32, 51, 51, 14, 35, 15, 14, 34, 16, 60, 56, 67, 42, 67, 51, 14 and 35. Which value occurs most often? There is exactly one such value. Answer with a whole number.
structured: {"ask": "mode", "values": [15, 42, 35, 32, 34, 67, 22, 42, 25, 15, 56, 35, 25, 51, 16, 22, 32, 56, 22, 16, 22, 42, 56, 15, 32, 16, 67, 35, 14, 32, 51, 51, 14, 35, 15, 14, 34, 16, 60, 56, 67, 42, 67, 51, 14, 35]}
answer: 35
```

### `M1.painted_cube_r3` (family geometry)

structured {"dims", "bottom_unpainted", "faces"}. As rev2 with wider dimensions (3..30+4*level; rev2 level 0 had 16,968 distinct items) and the count by position classes (closed form,
checked against a loop over every cube in the tests). Faces (0, 1 or 2) drawn first; the bottom is painted or not (stated).

Example (level 2):

```
question: This problem comes from a quiz held in Westmere, set by Bea. A block is made from small cubes of the same size glued together into a box 6 cubes long, 4 cubes wide and 6 cubes high. The whole box is placed on a table and every outer face is painted red except the bottom face (the face on the table), which stays unpainted. Then the box is taken apart into the small cubes. How many small cubes have exactly 2 painted faces? Answer with a whole number.
structured: {"bottom_unpainted": true, "dims": [6, 4, 6], "faces": 2}
answer: 32
```

### `M1.percent_change_r3` (family percent)

structured {"price": P, "steps": [["up" | "down", percent]]}. Two steps (up then down) below level 3, three (up, down, up) from level 3. Percents are multiples of 5 (up 5..80, down 5..75, third up 5..60).
The price is a multiple of 4 (two steps) or of 80 (three steps), which makes the final price a whole number of cents by construction (batch 1 retried); the step count per level is unchanged.

Example (level 2):

```
question: A jacket costs 84 dollars. Its price rises by 80 percent, then falls by 35 percent, each change applied to the price just before it. What is the final price in dollars? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"price": 84, "steps": [["up", 80], ["down", 35]]}
answer: 98.28
```

### `M1.pigeonhole_worst_case_r3` (family counting)

structured {"counts", "goal": "same" | "all", "k"}. Goal drawn first. Colour counts are drawn LOG-uniformly on 2..200+30*level, so the smallest count is usually far below the largest and 'ignore the caps,
(k - 1) c + 1' is right only when every colour has at least k - 1 marbles (audit: +0.10 to +0.18 with uniform counts); for goal 'same', k is uniform on 2..max(count), so a colour with k marbles exists.

Example (level 2):

```
question: A bag holds marbles of 4 colours: 23 green, 87 white, 20 blue, 105 black. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the draws are, of having at least one marble of every colour? Answer with a whole number.
structured: {"counts": [23, 87, 20, 105], "goal": "all", "k": 1}
answer: 216
```

### `M1.pipes_work_r3` (family rates)

structured {"a", "b", "drain", "volume"}. Two filling pipes (litres per minute 2..24+2*level), a drain from level 3 (1..a+b-1 litres per minute), minutes 3..40+5*level; the tank starts empty and all run together.

Example (level 2):

```
question: A tank is empty. One pipe adds 27 litres of water every minute and a second pipe adds 13 litres every minute, all at the same time and at a steady rate. How many minutes does it take for the tank to hold 720 litres? Answer with a whole number.
structured: {"a": 27, "b": 13, "drain": 0, "volume": 720}
answer: 18
```

### `M1.prime_factors_r3` (family number_theory)

structured {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. Ask drawn first. N is drawn UNIFORMLY from the integers 12..nmax(level) (30,000 at level 0 up to 1,600,000 at level 6)
whose prime factors are all at most 97 and that have at least two different prime factors (a precomputed list; no rejection). Batch 1 and rev2 built N from a small prime pool, which capped capacity.

Example (level 2):

```
question: Kate from Eastvale found this problem in a puzzle book. Consider the number 1023. How many different positive whole numbers divide it exactly (counting 1 and the number itself)? Answer with a whole number.
structured: {"ask": "divisors", "n": 1023}
answer: 8
```

### `M1.quadratic_area_r3` (family algebra)

structured {"shape": "rect_area" | "rect_perimeter" | "product" | "squares", "d", "area", "perimeter", "total"}. As batch 1 (positive whole root x of a quadratic; d >= max(3, isqrt(4x) + 3) so that
'sqrt(area)' and 'sqrt(area) - d/2' are not the root) with the ranges widened: x 2..150+25*level, d from that minimum up to the minimum + 120 + 15*level. The shape is drawn first (a quarter each).

Example (level 2):

```
question: Pia of Harrow wrote this problem for a maths club. Two positive whole numbers differ by 40, and the sum of their squares is 14578. What is the smaller of the two numbers? Answer with a whole number.
structured: {"area": 0, "d": 40, "perimeter": 0, "shape": "squares", "total": 14578}
answer: 63
```

### `M1.ratio_share_r3` (family ratio)

structured {"parts": [..], "total": n, "who": index}. Parts are 1..16 (two parts, three from level 2, four from level 4); total = k * sum(parts), k in 2..60+20*level; every share is a whole number of stickers.

Example (level 2):

```
question: Rosa, Bea and Gwen share 273 stickers in the ratio 1:16:4 (in that order: the first named person gets the first number of parts, and so on; every part has the same number of stickers, and the shares are whole numbers of stickers). How many stickers does Rosa get? Answer with a whole number.
structured: {"parts": [1, 16, 4], "total": 273, "who": 0}
answer: 13
```

### `M1.rectangle_r3` (family geometry)

structured {"shape": "ratio" | "excess", "perimeter": P, "ratio": k, "excess": d}. Shape (drawn first; 'ratio' with probability 0.3, 'excess' with 0.7, because the ratio shape has a space of only 649 items at level 0): the length is k times the width (k 2..12), or the length is d centimetres more than the width (d 1..60).
Width 2..60+10*level; the perimeter is built from the whole width, so it is always consistent. Answer: the area in square centimetres (whole by construction).

Example (level 2):

```
question: A rectangle has a perimeter of 146 centimetres and its length is 15 centimetres more than its width. What is its area in square centimetres? Answer with a whole number.
structured: {"excess": 15, "perimeter": 146, "ratio": 0, "shape": "excess"}
answer: 1276
```

### `M1.recurrence_iterate_r3` (family sequences)

structured {"shape": "sum_prev_two" | "affine" | "add_index", "first": [a] or [a, b], "mult": c, "add": d, "position": n}. Terms are numbered from 1; the answer is the term at `position`.
sum_prev_two: first two terms 1..299, position 6+level..9+2*level. affine: first term 1..199, term = c * previous + d with c in {2, 3} and d in -(min(40, (c-1)a - 1))..40, d != 0 (so every term is positive and
the list grows), position 5+level//2..7+level//2. add_index: first term 1..400, every term is the previous plus `add` times its own position (add 1..9), position 6+level..9+2*level. All values stay
below 10**8 by these ranges, so there is no retry (batch 1 retried on size and sign).

Example (level 2):

```
question: Pearl of Fenwick wrote this problem for a maths club. A list of numbers is built by a rule. The first number is 5. Every number after it is 2 times the number just before it, minus 4. What is the number in position 6 of the list (position 1 is the first number)? Answer with a whole number.
structured: {"add": -4, "first": [5], "mult": 2, "position": 6, "shape": "affine"}
answer: 36
```

### `M1.shopping_r3` (family shopping)

structured {"items": [[count, price_cents]], "paid": cents}. Unchanged computation (change = paid - total); states the answer format (dollars, up to two decimals).

Example (level 2):

```
question: Xan buys 7 compasss at $1.47 each, 1 ribbon at $0.10 each, 4 whistles at $1.37 each, 3 scarfs at $1.37 each. Xan pays with $25.00. How many dollars of change does Xan get back? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"items": [[7, 147], [1, 10], [4, 137], [3, 137]], "paid": 2500}
answer: 5.02
```

### `M1.slot_permutations_r3` (family counting)

structured {"digits": [..], "length": s, "repeat": bool, "first": rule, "last": rule}. Codes of s digits written with the allowed digits (4..9 of 0-9, uniformly among the 847 subsets); no digit twice unless `repeat`;
the FIRST digit obeys one of {any, not 0, odd, even, >= 5, < 5} (not 0 only when 0 is allowed; for 'any' with 0 allowed the item says a code such as 012 is allowed) and the LAST digit one of {odd, even,
>= 5, < 5} (always a restriction, by construction). The answer is positive (a validity loop). Level: the code length is as in rev2 (3 at levels 0-1 up to 6 at level 5). Widened from rev2's parity-only
last-digit rule (capacity: 1,163 distinct at level 1).

Example (level 2):

```
question: Kai from Ravenna found this problem in a puzzle book. How many 3-digit codes can be written using only the digits 0, 1, 3, 5, 7 and 9, if no digit may be used more than once, the first digit must be odd and the last digit must be even? Answer with a whole number.
structured: {"digits": [0, 1, 3, 5, 7, 9], "first": "odd", "last": "even", "length": 3, "repeat": false}
answer: 20
```

### `M1.speed_distance_r3` (family rates)

structured {"legs": [[hours, speed]], "average": bool}. The leg durations are DISTINCT by construction (sampled without replacement), so 'sum of speeds x mean hours' is not
right when the hours are equal (audit: +0.21 at L0-L1). The average ask (levels >= 2) is built so that the total distance is a multiple of the total hours (the average is a whole number):
the last speed is drawn from the values that make it so (batch 1 did this with a Retry). Distance in kilometres, speeds in kilometres per hour, durations in whole hours.

Example (level 2):

```
question: A van drives for 2 hours at 72 kilometres per hour, then drives for 9 hours at 72 kilometres per hour, then drives for 10 hours at 37 kilometres per hour. How many kilometres does it travel in total? Answer with a whole number.
structured: {"average": false, "legs": [[2, 72], [9, 72], [10, 37]]}
answer: 1162
```

### `M1.tiered_pricing` (family pricing)

structured: {"mode": "bill" | "units", "tiers": [[units_in_tier, cents_per_unit]] for every tier but the last, "last_rate": cents_per_unit above all tiers, "used": U or null, "bill_cents": B or null}.
Each unit is charged at the rate of the tier it falls in (marginal rates: the first tiers[0][0] units at tiers[0][1], the next tiers[1][0] at tiers[1][1], ..., all further units at last_rate).
bill: answer the bill for U units in dollars (a number with at most two decimals). units: answer the whole number of units U that gives a bill of B cents. Generator makes U exceed every tier boundary at higher levels.

Example (level 2):

```
question: A utility charges for use in steps: the first 43 units cost 12 cents each, the next 14 units cost 50 cents each, and every unit after that costs 60 cents each. Each unit costs the rate of the step it falls in (a higher step does not change what earlier units cost). What is the bill for 64 units, in dollars? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"bill_cents": null, "last_rate": 60, "mode": "bill", "tiers": [[43, 12], [14, 50]], "used": 64}
answer: 16.36
```

### `M1.tip_split_r3` (family percent)

structured {"bill": B, "tip": percent, "people": n}. Tip is any whole percent 5..30, people 2..6+level, bill 20..400+100*level dollars chosen as a multiple of n / gcd(n, 100 + tip), so each
person's share is a whole number of cents by construction (batch 1 retried). The tip is on the bill before tip, the total is split equally.

Example (level 2):

```
question: A dinner bill is 291 dollars before tip. The group adds a 30 percent tip, calculated on the bill before tip, and splits the total (bill plus tip) equally between 2 people. How many dollars does each person pay? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros.
structured: {"bill": 291, "people": 2, "tip": 30}
answer: 189.15
```
