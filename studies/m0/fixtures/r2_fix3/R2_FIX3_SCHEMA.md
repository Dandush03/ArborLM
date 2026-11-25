# R2 fix round 3: structured-form schema for the second-solver agent (revised shapes only)

Written by the implementer. Not a result; nothing here approves anything. Same interface as `R2_BATCH1_SCHEMA.md`: a solver reads ONLY `structured`; `solve(structured) -> str`; raise `ValueError` when the form has no unique answer.
These shapes SUPERSEDE the earlier shapes of the same ids (see `SUPERSEDES` in `studies/m0/lineages_r2_fix3.py`). Fixtures: `studies/m0/fixtures/r2_fix3/<id>.jsonl`, 20 items per level 0..6.

## Revised shapes

### `R2.binary_search_trace` (family search; supersedes R2.binary_search_trace)

Procedure: binary search with middle = floor((low+high)/2). structured: {"xs": [int] (ascending, distinct), "target": int, "ask": "values" | "sum"}.
R-1: the batch-1 redraw on 'the third look is the target' is removed together with the `third` shape (its answer is one of four values near fixed fractions of the list, a 'position rule' read 0.2-0.3 whatever the construction).
The list is longer (16+4*level .. +3 numbers; a length of 2^k - 1 is stepped over, because there the roundings up and down give the same search) so that the look sequence is long and the numbers it visits are spread.
The target is in the list on a fair coin and otherwise a number that is not in it. Answer: the numbers looked at in order (comma list), or their sum.

Example (level 2):

```
question: A sorted list of 27 numbers (smallest first) is searched for 3. The positions are numbered 1 to 27. The search keeps a lower position (first 1) and an upper position (first 27). Each round it looks at the number in the position halfway between them, rounded down when needed (the sum of the two positions divided by 2, rounded down). If that number is the target the search stops; if the target is smaller, the upper position becomes one less than the position just looked at; otherwise the lower position becomes one more. If the lower position ever exceeds the upper position the search stops, having found nothing. The list: 2, 4, 5, 7, 8, 10, 14, 19, 23, 24, 27, 33, 37, 42, 58, 61, 64, 65, 66, 69, 71, 72, 100, 101, 102, 105, 107. Which numbers does the search look at, in order? Give them separated by commas.
structured: {"ask": "values", "target": 3, "xs": [2, 4, 5, 7, 8, 10, 14, 19, 23, 24, 27, 33, 37, 42, 58, 61, 64, 65, 66, 69, 71, 72, 100, 101, 102, 105, 107]}
answer: 42, 14, 5, 2, 4
```

### `R2.bracket_match` (family parsing; supersedes R2.bracket_match)

Procedure: match brackets with a last-opened-first-closed stack. structured: {"s": str, "ask": "match_all" | "first_error", "kind": "(" | "[" | "{" or null}.
Fix round 3 (R-1, R-13): the yes/no `valid` shape is DROPPED: a rule that checks only some of the pairs (the top-level ones, or those at one depth) reads 0.5 + half the share of pairs it checks (0.79-0.84 measured), and no
corruption that keeps the counts of every kind can be placed so that every partial check misses it. The single-position `match` shape is DROPPED (the answer is one of about twenty positions; 'last/next closer of the same
kind' read 0.35-0.51). New shapes whose answer is a LIST that a partial rule cannot give: `match_all`: for every opening bracket of one stated kind, the position of its closer, in the order of the openers;
`first_error`: the text is correct except that the closers of two pairs have been swapped, a pair and a pair that encloses it, both enclosing something, of different kinds, their closers not next to each other (a swap of two separate pairs would show in the running count of a kind: the closer's kind has not been opened yet, 0.9 measured); the answer is the position of the first closing bracket that does not match
the most recently opened bracket still open. By construction the kinds are shared out evenly over the 14 + level pairs (so every kind has at least four pairs; with 9 + level the 'k-th closer goes with the k-th opener' rule read 0.25), and the nesting is deep (opening chance 0.58).

Example (level 2):

```
question: In the text ({}[[{{(()()}}({})([]))][{[]}]]) (positions are counted from 1 at the left) every opening bracket should be closed by a closing bracket of the same kind, with brackets opened later closed earlier, but the text breaks this rule. Reading from the left, each closing bracket should match the opening bracket most recently opened and not yet closed. At which position is the first closing bracket that does not match?
structured: {"ask": "first_error", "kind": null, "s": "({}[[{{(()()}}({})([]))][{[]}]])"}
answer: 13
```

### `R2.bst_traversal` (family structures; supersedes R2.bst_traversal)

Procedure: binary-search-tree insertion then a tree walk. structured: {"xs": [int] (distinct, inserted in this order), "kind": "pre" | "post" | "level"}.
R-1: the batch-1 rejection of answers equal to the insertion order or the sorted order is REMOVED. By construction n is 8 + level (batch 1: 5 + level): for a random order the chance that a
walk equals the insertion order is the Catalan number over n! (0.035 at n = 8, under 0.001 at n = 11), so no exclusion is needed. Answer: the numbers in that walk order, as a comma list.

Example (level 2):

```
question: Numbers are put one at a time into a tree. The first number is the top of the tree. Every later number starts at the top and moves down: at each number it meets, it goes to the left if it is smaller and to the right if it is larger, and it stays in the first empty place it reaches. The numbers are put in this order: 35, 50, 55, 90, 20, 58, 87, 57, 43, 80. Read the tree like this: write a number, then everything in its left branch, then everything in its right branch (applied the same way inside each branch). Give the numbers in that reading order, separated by commas.
structured: {"kind": "pre", "xs": [35, 50, 55, 90, 20, 58, 87, 57, 43, 80]}
answer: 35, 20, 50, 43, 55, 90, 58, 57, 87, 80
```

### `R2.cache_eviction` (family structures; supersedes R2.cache_eviction)

Procedure: cache with a stated eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "evicted" | "contents"}.
Fix round 3: the `misses` count (a small answer; the other policy's count read 0.42-0.60) and the yes/no `present` question (0.85-0.91 read off the last requests) are DROPPED. The answers are now LISTS that a counting or
last-requests rule cannot give: `evicted`: the items removed to make room, in the order they were removed (either policy); `contents` (FIFO only, because under LRU the contents are read off the last requests backwards):
the items in the cache at the end, from the one loaded longest ago to the one loaded most recently. By construction the request sequence begins with cap+1 different items (so something is always removed)
and each later request is, with chance 0.65 for `contents` and 0.4 for `evicted` (which needs many misses, so a long list), a re-request of an item that is in the cache at that moment (under the stated rule), otherwise a draw from a pool of cap + 3 (cap + 5 for `evicted`) + level//2 items; the hits are what make the two rules differ.
Nothing is redrawn on what any rule gives.

Example (level 2):

```
question: A cache holds at most 4 items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; if it is not, it is put into the cache, and if the cache was full the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order). Requests in order: pencil, teapot, quilt, candle, spoon, teapot, spoon, candle, orange, spoon, yo-yo, orange, candle, spoon, yo-yo, orange, orange, feather, teapot, feather, pencil, yo-yo, pencil, yo-yo, yo-yo, quilt, yo-yo. Which items are removed from the cache to make room, in the order in which they are removed? Write the item names separated by commas.
structured: {"ask": "evicted", "cap": 4, "policy": "fifo", "seq": ["pencil", "teapot", "quilt", "candle", "spoon", "teapot", "spoon", "candle", "orange", "spoon", "yo-yo", "orange", "candle", "spoon", "yo-yo", "orange", "orange", "feather", "teapot", "feather", "pencil", "yo-yo", "pencil", "yo-yo", "yo-yo", "quilt", "yo-yo"]}
answer: pencil, teapot, quilt, candle, spoon, orange, yo-yo, feather
```

### `R2.cellular_automaton` (family dynamics; supersedes R2.cellular_automaton)

Procedure: synchronous three-neighbour table update. structured: {"row": [0|1], "table": {"LCR": 0|1} (all 8 triples), "steps": int, "ask": "row"}.
R-1: the batch-1 rejections (final row equal to the start, all-equal final row, table with 000 -> 1) are REMOVED. By construction the row is 11 + 2*level cells whose two END cells are 1 (so the
rule that a periodic edge would give differs from the stated zero edge at the first step with chance 1/2 per end), there are 2 + level//2 steps (batch 1: 1 + level//2, 4 at level 6), the `count` shape
(a handful of answers, 0.24 constant) is dropped, the table has 64 free choices once the mirror-image pairs are tied, so the row is 11 cells at level 0 for capacity (9 cells gave 8,117 different items), the values of the mirror-image triples 100/001 and 110/011 are drawn different (by construction: the right-to-left misreading of the table then always changes the rule) and the only table excluded is a constant one (a table that ignores its input; validity, not a shortcut gate). Answer: the row after the steps as 0/1 digits.

Example (level 2):

```
question: A row of 15 cells holds 0s and 1s: 100101001001101. In one step every cell changes at the same moment, according to the three digits (left neighbour, the cell itself, right neighbour): 111 becomes 1, 110 becomes 1, 101 becomes 1, 100 becomes 1, 011 becomes 0, 010 becomes 1, 001 becomes 0, 000 becomes 1. The cells beyond the two ends of the row count as 0. After 3 steps, what does the row look like? Give the digits with no spaces.
structured: {"ask": "row", "row": [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1], "steps": 3, "table": {"000": 1, "001": 0, "010": 1, "011": 0, "100": 1, "101": 1, "110": 1, "111": 1}}
answer: 001101111011001
```

### `R2.cheapest_network` (family graphs; supersedes R2.cheapest_network)

Procedure: cycle-avoiding cheapest-edge selection. structured as before: {"towns": [name], "cables": [[a, b, cost]]}.
Fix round 3: the grouped-towns construction (a cheap triangle in each group, dear cables between groups) was itself a solver: 'cheap cables minus the dearest of each triangle plus the (g-1) cheapest dear cables' read 1.00 at
levels 0-2. By construction the towns are now POINTS on a 26 x 26 grid, a cable costs the walking distance between its two towns (at least 1), and the 2n cheapest pairs are the cables offered. Nearby towns form
cycles of cheap cables, so adding up the n-1 cheapest cables is the answer on about 6% of items (random weights need 12 towns for that), and no group template exists. n = 8 + level//2 towns (8..11). A draw whose cables
do not connect all the towns is drawn again (validity). Answer: the least total cost of a set of cables that joins all the towns.

Example (level 2):

```
question: The towns Arden, Brook, Dunmore, Fenwick, Harrow, Marlow, Selby, Upton and Yarrow must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. A cable between Harrow and Brook would cost 8. A cable between Upton and Selby would cost 5. A cable between Brook and Dunmore would cost 19. A cable between Fenwick and Marlow would cost 20. A cable between Harrow and Yarrow would cost 20. A cable between Arden and Fenwick would cost 15. A cable between Yarrow and Marlow would cost 10. A cable between Upton and Dunmore would cost 19. A cable between Arden and Yarrow would cost 13. A cable between Arden and Marlow would cost 5. A cable between Selby and Yarrow would cost 11. A cable between Harrow and Dunmore would cost 13. A cable between Selby and Dunmore would cost 14. A cable between Upton and Yarrow would cost 12. A cable between Harrow and Fenwick would cost 18. A cable between Dunmore and Yarrow would cost 19. A cable between Brook and Arden would cost 21. A cable between Brook and Fenwick would cost 10. What is the smallest total cost of a set of cables that joins all the towns?
structured: {"cables": [["Harrow", "Brook", 8], ["Upton", "Selby", 5], ["Brook", "Dunmore", 19], ["Fenwick", "Marlow", 20], ["Harrow", "Yarrow", 20], ["Arden", "Fenwick", 15], ["Yarrow", "Marlow", 10], ["Upton", "Dunmore", 19], ["Arden", "Yarrow", 13], ["Arden", "Marlow", 5], ["Selby", "Yarrow", 11], ["Harrow", "Dunmore", 13], ["Selby", "Dunmore", 14], ["Upton", "Yarrow", 12], ["Harrow", "Fenwick", 18], ["Dunmore", "Yarrow", 19], ["Brook", "Arden", 21], ["Brook", "Fenwick", 10]], "towns": ["Upton", "Harrow", "Brook", "Arden", "Fenwick", "Selby", "Dunmore", "Yarrow", "Marlow"]}
answer: 76
```

### `R2.coin_change_min` (family dynprog; supersedes R2.coin_change_min)

Procedure: unbounded-supply capacity table, FEWEST coins (restored: round 2 had changed the question to the number of ways, which duplicated M1.change_ways_r2 and C1.coin_change_table). structured: {"coins": [int], "amounts": [int], "ask": "fewest"}.
The batch-1 tells (largest-first greedy, amount // largest + 1) came from asking for ONE amount: a rule that is wrong on 40% of amounts is right on 60% of single questions. By construction the question now asks for the fewest coins
for EACH of FIVE amounts, as a list, so a rule must be right on all five (a rule right on 70% of amounts is right on 17% of lists). Coins: 3 different worths from 3 .. 23 + 2*level (4 worths from level 3, the smallest at most 6),
no coin of worth 1 (with 2 .. 14 and four amounts 'amount / largest coin, rounded up' read 0.24); an amount is drawn uniformly among the amounts from 40 + 4*level to 100 + 8*level that CAN be paid exactly (validity: a stated amount must be payable). Answer: the five least numbers of coins, in the order of the amounts.

Example (level 2):

```
question: You have an unlimited supply of coins worth 4, 11 and 14. For each of the amounts 52, 71, 101, 79 and 70, in this order, what is the smallest number of coins that adds up to exactly that amount? Give the five numbers separated by commas, in the same order as the amounts.
structured: {"amounts": [52, 71, 101, 79, 70], "ask": "fewest", "coins": [4, 11, 14]}
answer: 6, 6, 9, 7, 5
```

### `R2.count_divisible` (family counting; supersedes R2.count_divisible)

Procedure: a linear scan with a counter (or an accumulator) for a predicate. structured: {"xs": [int], "m": int, "t": int, "ask": "sum"}. Fix round 3: the COUNT shape is DROPPED (its answers are small: the constant guess read 0.23 and the estimate (numbers over t) // m 0.26, which no construction removes); '>= t' instead of '> t' read 0.98-0.99,
'ignore > t' 0.65-0.74 and the constant 0 0.47 at level 0. By construction the threshold t is itself a multiple of m and the number t is PLANTED in the list once (so a reader who counts '>= t', or who ignores the threshold,
always differs), m is 2, 3 or 4, the list has 18 + 4*level numbers (10 .. 99 + 100*(level//2)) so the counts spread, and the question is the SUM of the numbers that are divisible by m and greater than t.
Answer: that sum.

Example (level 2):

```
question: What is the sum of the numbers in this list that are divisible by 2 and greater than 114? List: 114, 18, 48, 49, 197, 93, 152, 40, 169, 171, 183, 176, 151, 85, 121, 166, 58, 78, 113, 197, 78, 34, 17, 106, 146, 56.
structured: {"ask": "sum", "m": 2, "t": 114, "xs": [114, 18, 48, 49, 197, 93, 152, 40, 169, 171, 183, 176, 151, 85, 121, 166, 58, 78, 113, 197, 78, 34, 17, 106, 146, 56]}
answer: 640
```

### `R2.count_letter` (family counting; supersedes R2.count_letter)

Procedure: a linear scan with a counter for a predicate. structured: {"words": [str], "letter": str}. Fix round 3: 'count the words that contain the letter' read 0.69-0.88 (most words hold the letter at most once) and the
most frequent answer 0.59 at level 0. By construction the asked letter is one that some invented word can hold twice, each of the 8 + 2*level words holds it 0, 1 or 2 times (two independent chances each, with a per-item chance drawn from
0.15 .. 0.75, so the totals spread), and ONE word, chosen at random, holds it exactly twice (planted: 'words that contain the letter' is then never the total). Words are drawn from the invented-word list, distinct.
Answer: how many times the letter appears in total.

Example (level 2):

```
question: How many times does the letter 'e' appear in total in these words: kenen kidix lozer kelex nesex ziman lizak verok lerex belek seden kedek?
structured: {"letter": "e", "words": ["kenen", "kidix", "lozer", "kelex", "nesex", "ziman", "lizak", "verok", "lerex", "belek", "seden", "kedek"]}
answer: 16
```

### `R2.dictionary_rank` (family combinatorics; supersedes R2.dictionary_rank)

Procedure: mixed-radix ranking/unranking of words of different letters in dictionary order. structured: {"letters": [str] (sorted), "length": int, "ask": "word" | "position", "k": int or null, "word": str or null}.
Widened for capacity under the reading in which letters are relabelled (reading b of the fix round): the words have `length` different letters TAKEN FROM a larger alphabet (batch 1: arrangements of all the letters,
only 24-5,040 different structures), the alphabet size is drawn per item. R-1: the batch-1 redraw on rank 1 or last is removed (it is a negligible chance here). Answer, word: the word at position k (2 .. last - 1); position: the number of `word`.

Example (level 2):

```
question: Write every word of 5 letters that can be made from the letters b, k, m, o, q, r, u, v, z when no letter is used twice in the same word, and list all the words in dictionary order (as in a dictionary, comparing letter by letter from the left, with a before b before c and so on). Number the words 1, 2, 3, ... in that list. What is the number of the word mbruk?
structured: {"ask": "position", "k": null, "length": 5, "letters": ["b", "k", "m", "o", "q", "r", "u", "v", "z"], "word": "mbruk"}
answer: 3466
```

### `R2.expression_eval` (family parsing; supersedes R2.expression_eval)

Procedure: evaluate an infix expression under a stated convention. structured: {"text": str, "convention": "ranked" | "left_to_right"}. Wording as in rev2 (the rule applies inside parentheses too; + and - are one rank).
Fix round 3 (R-1): rev2 left the wrong-rule rate 'natural' (the item evaluated under the other rule, or with parentheses ignored, agreed with the key on 0.3-0.9 of items). Now the structure that makes each misreading
differ is PLANTED rather than hoped for, and no item is redrawn on any rule's value. ranked: a chain of 3 + level//2 (+0/1) terms; a later term is a product; one factor of a product is a parenthesised sum;
the operators contain '-' directly followed by '+' (so 'plus before minus' differs); further factors and parentheses are added at random with the level. left_to_right: a chain of 4 + level//2 (+0/1) numbers; some '+' or '-' is directly
followed by '*'; one later number is a parenthesised chain with a '+'/'-' followed by '*' inside it. Numbers are 2..9 (2..20 from level 4).

Example (level 2):

```
question: Work out 2 - 9 - 7 + 7 * 9 - 9 * (2 + 6) * 6. Use these rules, in this order, also inside every pair of parentheses: do what is inside parentheses first, innermost first; then do all the multiplications, from left to right; then do all the additions and subtractions together as one group, strictly from left to right (so 8 - 3 + 2 is worked as (8 - 3) + 2 = 7, and 8 + 3 - 2 as (8 + 3) - 2 = 9). What is the result?
structured: {"convention": "ranked", "text": "2 - 9 - 7 + 7 * 9 - 9 * (2 + 6) * 6"}
answer: -383
```

### `R2.gcd_euclid` (family numtheory_b1; supersedes R2.gcd_euclid)

Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm"}. Fix round 3: in round 2 the common divisor g had no prime factor below 11, so at levels 0-2 it was always a PRIME (g <= 60) and
'the smallest common prime factor' read 1.00 (0.90-0.94 at levels 3-6). By construction g is drawn uniformly among the numbers from 8 to 60 + 30*level that are NOT squarefree (they have a repeated prime factor, so g is never a prime, never
the product of its distinct primes, and never the smallest or largest prime factor of a or b); the cofactors p, q (each at least 5, so one Euclid step 'a mod b' is not the answer) are coprime and not within 1 of each other (a stated validity: then g is the greatest common divisor).
Answer: the greatest common divisor or the least common multiple (shape drawn 50/50).

Example (level 2):

```
question: What is the least common multiple of 7904 and 7384?
structured: {"a": 7904, "ask": "lcm", "b": 7384}
answer: 561184
```

### `R2.hash_probe` (family structures; supersedes R2.hash_probe)

Procedure: linear-probing hash table. structured: {"m": int, "keys": [int], "ask": "table" | "checksum"}.
Fix round 3: the single-key shapes `slot` and `probes` are DROPPED. Round 2's design (almost full table, every home in the first third) made the whole table one block that starts at the smallest home, so
'start of the block + position' read 0.73-0.98; with homes spread over the table a single key is often at its home or after only same-home keys (0.4-0.57). By construction the answer is now about the WHOLE table:
`table`: the final contents of every slot from 0 to m-1 (a dash for a slot that stays empty), which a rule that places keys by a formula cannot get right without doing the placements; `checksum`: the sum of the numbers of the
slots that end up holding a number (slot numbers, not the held numbers), which depends on which slots stay empty (a total of probes was tried and dropped: its answers cluster, constant guess 0.2).
m = 10 + level slots, round(0.7 m) distinct numbers (10..99), homes spread over the whole table. No item is chosen or redrawn by what any rule gives.

Example (level 2):

```
question: A table has 12 slots numbered 0 to 11. A number goes into the slot whose number is the remainder of the number divided by 12; if that slot is taken, it goes into the next slot up (slot 11 is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: 99, 56, 91, 71, 16, 38, 26, 48. After all the numbers are added, add up the NUMBERS OF THE SLOTS that hold a number (for example, if only slots 2 and 5 held numbers the answer would be 7; the numbers held do not matter, only which slots are taken). What is the sum?
structured: {"ask": "checksum", "keys": [99, 56, 91, 71, 16, 38, 26, 48], "m": 12}
answer: 40
```

### `R2.interval_scheduling` (family greedy; supersedes R2.interval_scheduling)

Procedure: pick by earliest finish time (activity selection). structured: {"meetings": [[start, end]], "ask": "chosen"} (integer times, start < end).
R-1: the batch-1 redraw on 'earliest start' and 'shortest first' is removed, and so is the count answer (a small number: the constant guess read 0.2-0.35 whatever the construction). By construction
the day is made of 5 + level//2 independent BLOCKS of 4-6 meetings, each in its own time window (windows 24 minutes apart; a meeting starts 0-12 minutes into its window and lasts 2-9, so none touches another block), the meetings are numbered in a shuffled order,
and the answer is the LIST of the chosen meetings' numbers: a rule that errs in one block errs on the item, and nothing is drawn conditional on what any rule gives.
Answer: the numbers of the meetings the stated earliest-finish rule chooses (ties in finishing minute: the smaller number), smallest number first.

Example (level 2):

```
question: A person can attend only one meeting at a time. Times are whole numbers of minutes: meeting 1 runs from 73 to 82; meeting 2 runs from 124 to 128; meeting 3 runs from 0 to 8; meeting 4 runs from 24 to 29; meeting 5 runs from 35 to 37; meeting 6 runs from 104 to 112; meeting 7 runs from 101 to 105; meeting 8 runs from 57 to 63; meeting 9 runs from 124 to 129; meeting 10 runs from 55 to 58; meeting 11 runs from 77 to 85; meeting 12 runs from 36 to 41; meeting 13 runs from 32 to 39; meeting 14 runs from 50 to 57; meeting 15 runs from 120 to 127; meeting 16 runs from 78 to 84; meeting 17 runs from 129 to 133; meeting 18 runs from 1 to 8; meeting 19 runs from 76 to 84; meeting 20 runs from 100 to 104; meeting 21 runs from 126 to 135; meeting 22 runs from 49 to 58; meeting 23 runs from 129 to 131; meeting 24 runs from 108 to 111; meeting 25 runs from 3 to 12; meeting 26 runs from 2 to 10; meeting 27 runs from 78 to 86. Two meetings clash if they share any stretch of time; a meeting that ends at the very minute another starts does not clash with it. The person chooses meetings in rounds: in each round, among the meetings that do not clash with any meeting already chosen, the one that ends first is chosen (if two end at the same minute, the one with the smaller number); rounds go on until no meeting can be added. Which meetings are chosen? Give their numbers, smallest first, separated by commas.
structured: {"ask": "chosen", "meetings": [[73, 82], [124, 128], [0, 8], [24, 29], [35, 37], [104, 112], [101, 105], [57, 63], [124, 129], [55, 58], [77, 85], [36, 41], [32, 39], [50, 57], [120, 127], [78, 84], [129, 133], [1, 8], [76, 84], [100, 104], [126, 135], [49, 58], [129, 131], [108, 111], [3, 12], [2, 10], [78, 86]]}
answer: 1, 3, 4, 5, 8, 14, 15, 20, 23, 24
```

### `R2.lcs_length` (family dynprog; supersedes R2.lcs_length)

Procedure: two-string prefix table. structured: {"a": str, "b": str}. Fix round 3: strings are longer (15 + 2*level .. 21 + 3*level letters; rev2 8 + level .. 14 + 2*level), because 'greedy matching, the better of both directions'
read 0.46 at level 0 and fell to 0.08 only at level 6, and the constant guess 0.26. A common subsequence of length k (uniform from 35% of the shorter length to the shorter length minus 2, so the plant is longer than the common subsequence of two random strings) is PLANTED; the answer is computed by the table, not from the plan;
the alphabet has 8-12 letters drawn per item (with 4-6 letters a random pair already shares a long subsequence, so the answers cluster at 60% of the length).

Example (level 2):

```
question: A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). What is the length of the longest string that is a subsequence of both 'jfiddgebhckfhcagkefdc' and 'jfgiihhcfdiddhhkfkdghgcfd'?
structured: {"a": "jfiddgebhckfhcagkefdc", "b": "jfgiihhcfdiddhhkfkdghgcfd"}
answer: 12
```

### `R2.max_subarray_sum` (family dynprog; supersedes R2.max_subarray_sum)

Procedure: best-ending-here scan. structured: {"xs": [int]}. Fix round 3: the planted block (+++ - +++ between strongly negative separators) was a template ('best window of 7' and 'two longest runs plus the dip' read 1.00).
By construction the row is now a chain of 2U+1 PHASES (U = 2 + level//3 'rising' phases between 'falling' ones, the row starts and ends with a falling phase), 3-8 numbers long (rising phases 6-12): in a rising phase numbers alternate between a
positive number (3..9) and a dip (-1..-6), with a repeated positive on a 30% chance; in a falling phase a number is a small positive (1..3) on a 20% chance and otherwise -2..-9. So the best block crosses dips (a run of
non-negative numbers is rarely the answer), it never starts at the first number or ends at the last (a prefix or a suffix is never the answer), and phase lengths vary (no fixed window). Nothing is drawn by what any rule gives.
Answer: the largest total a block of neighbouring numbers can have (computed from the row, not from the plan).

Example (level 2):

```
question: Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: -9, -3, -2, 4, 9, -1, 9, 3, -5, 7, -5, 1, -4, -8, -7, 6, 4, -6, 7, 4, 4, -4, 7, -4, 6, -1, 3, -6, -3, 2, 2, -9, -9, -8, -8.
structured: {"xs": [-9, -3, -2, 4, 9, -1, 9, 3, -5, 7, -5, 1, -4, -8, -7, 6, 4, -6, 7, 4, 4, -4, 7, -4, 6, -1, 3, -6, -3, 2, 2, -9, -9, -8, -8]}
answer: 29
```

### `R2.min_heap_ops` (family structures; supersedes R2.min_heap_ops)

Procedure: array binary min-heap with sift-up insertion and sift-down removal. structured: {"xs": [int] (distinct, inserted in order), "removals": int}.
R-1: the batch-1 rejection of answers equal to the insertion order or sorted is REMOVED. By construction n is 10 + level (batch 1: 5 + level): the chance that a random order is already a heap
is about 0.005 at n = 8, and building the heap by sifting up differs from Floyd's whole-row method (which the audit lists as a valid alternative) in most orders. Answer: the array (positions 1..) after the inserts and the removals.

Example (level 2):

```
question: A heap is a row of numbers in positions 1, 2, 3, ... where the number in position p is never larger than the numbers in positions 2p and 2p+1 (when those exist). To add a number: put it in the first free position at the end, then, while it is smaller than the number in position (its position divided by 2, rounded down), swap the two. To remove the smallest: take out the number in position 1, put the number from the last position into position 1 (the row is now one shorter), then, while it is larger than the smaller of the numbers in positions 2p and 2p+1 (those that exist), swap it with that smaller number. Start with an empty heap and add these numbers in order: 96, 14, 33, 84, 56, 37, 29, 75, 11, 10, 47, 67. Then remove the smallest 1 time. Give the row from position 1 to the end, separated by commas.
structured: {"removals": 1, "xs": [96, 14, 33, 84, 56, 37, 29, 75, 11, 10, 47, 67]}
answer: 11, 14, 29, 56, 47, 37, 33, 96, 75, 84, 67
```

### `R2.multiples_between` (family numtheory; supersedes R2.multiples_between)

Procedure: the multiples of m inside a range, by floor division. structured: {"a": int, "b": int, "m": int, "ask": "count" | "sum"}. Fix round 3: with a and b drawn at random the count is b//m - (a-1)//m and every cheap formula is the true
count plus an offset in {-1, 0, +1} that depends only on whether a or b is a multiple of m; a fixed offset is right whenever the end is not a multiple (measured: b//m - a//m 0.87-0.89, round((b-a+1)/m) 0.75), and no choice of how often
the ends are multiples makes every such offset rare. By construction BOTH ENDS ARE MULTIPLES of m (the item says both ends are counted), so every formula that drops an end, floors the start or rounds is wrong on every item, and
the only formulas that hold are the counting rule itself ((b-a)/m + 1, or the arithmetic series for the sum), which are the procedure and reported as such. The shape is drawn 50/50: the count of the multiples, or their sum.
m 3..19; the first multiple m*k1 with k1 from 2 (so the first multiple is never m itself) to 300*(level+1)/m + 2, and the last m*k2 with k2 - k1 from max(2, 20//m) to 600*(level+1)//m (batch 1: a up to 50*(level+1), b - a up to 200*(level+1); widened for capacity: 5,915 and 14,724 different items at levels 0 and 1).

Example (level 2):

```
question: How many whole numbers from 590 to 880, counting both ends, are multiples of 10?
structured: {"a": 590, "ask": "count", "b": 880, "m": 10}
answer: 30
```

### `R2.palindrome_check` (family palindrome; supersedes R2.palindrome_check)

Procedure: compare a text with its reverse (spaces ignored). structured: {"phrase": str}. Fix round 3: 'at most one letter with an odd count' read 0.96 at every level, because a 'no' text was a palindrome with ONE letter
replaced, which changes two letter counts. By construction a 'no' text is a palindrome with TWO of its letters SWAPPED (the letter counts are exactly those of a palindrome, so the count rule says 'yes' for both answers) and the
texts are longer (2 * (12 + level) letters, or one more in the middle), so a rule that compares only the outer letters meets the swap on a small share of items. A swap that leaves a palindrome is drawn again (validity: the wanted
key must hold). The key is drawn 50/50 and spaces cut the text into 2 + level//2 words at random. Answer yes/no.

Example (level 2):

```
question: Ignoring the spaces, does the text 'cggejkgaf eb g ahbhagbefagkjeggc' read the same forwards and backwards? Answer yes or no.
structured: {"phrase": "cggejkgaf eb g ahbhagbefagkjeggc"}
answer: yes
```

### `R2.permutation_power` (family permutation; supersedes R2.permutation_power)

Procedure: apply a mapping t times (iterate a map). structured: {"img": [int], "s": int, "t": int}. Fix round 3: with a random mapping on 4 .. 10 numbers the start's cycle is short, so 'the start' (0.29-0.52), 'one
application' (0.30-0.53) and 't mod n applications' (up to 0.83) were each right on about 1/(cycle length) of items. By construction the mapping on n = 12 + level numbers has ONE long cycle through n - a of the numbers
(a drawn from 1..3 with a coprime to n, so the long cycle length n - a has no common factor with n and 't mod n' is not the reduction), the other a numbers are mapped among themselves at random, the numbers are labelled at random, and the start is a number of the long
cycle; t is drawn from 30 .. 90 + 10*level. Each of those rules is then right on about 1/(n-a), under one in ten. Answer: the number reached after t applications.

Example (level 2):

```
question: A mapping on the numbers 1 to 14 sends: 1 goes to 3, 2 goes to 11, 3 goes to 4, 4 goes to 12, 5 goes to 14, 6 goes to 10, 7 goes to 5, 8 goes to 1, 9 goes to 6, 10 goes to 8, 11 goes to 9, 12 goes to 7, 13 goes to 13, 14 goes to 2. Start at 10 and apply the mapping 65 times in a row. Which number do you end on?
structured: {"img": [3, 11, 4, 12, 14, 10, 5, 1, 6, 8, 9, 7, 13, 2], "s": 10, "t": 65}
answer: 10
```

### `R2.prime_factor_query` (family numtheory; supersedes R2.prime_factor_query)

Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}. Same construction as rev2 (largest prime factor uniform over the primes 17 .. top of the pool, one prime used twice, the other factors
uniform among the primes up to it; no gate), widened at level 0 only, for capacity under the reading in which a reserve level carries the core demand (R-10): rev2 had 4 factors from the primes up to 61 at level 0 (about 4,029 different
items); now 5 factors from the primes up to 79 (the other levels are unchanged: 5 factors, primes up to 97, 6 at level 6).
Answer: the largest prime factor, or the sum of the primes in the factorisation counting repeats.

Example (level 2):

```
question: What is the largest prime number that divides 157827679 exactly?
structured: {"ask": "largest", "n": 157827679}
answer: 73
```

### `R2.run_length` (family rle; supersedes R2.run_length)

Procedure: run-length encoding. structured: {"s": str}. Widened for capacity under the reading in which letters are relabelled (reading b): 6 + level runs of length 1 .. 4 + level//2 (batch 1: 3 + level runs of
length 1 .. 3 + level, only 54 different letter-blind structures at level 0). Each run's letter is drawn from the six letters other than the previous run's, so every run is maximal by construction (no redraw).
Answer: each maximal run as the letter followed by its length.

Example (level 2):

```
question: Compress zzxxxxxbbbccxxxcccbzzz by run-length encoding: replace each maximal run of one repeated letter by the letter followed by the run length (for example aaab becomes a3b1). What is the result?
structured: {"s": "zzxxxxxbbbccxxxcccbzzz"}
answer: z2x5b3c2x3c3b1z3
```

### `R2.stack_machine` (family stack; supersedes R2.stack_machine)

Procedure: a stack machine. structured: {"prog": [[op, value?]]}. Fix round 3: 'the last pushed value' read 0.41-0.59 and was exact on every item whose last step is a push (31-45%). By construction the program is 5 + 2*level
random steps (batch 1: 4 + 2*level; values 1..20, batch 1: 1..9) followed by a FINAL step that is always an arithmetic operation (add, multiply or subtract; if fewer than two numbers are on the stack a push comes first), so
the last step is never a push. A subtraction never directly follows a duplication (dup then sub always gives 0, which made 0 the constant guess at 8-11%). Answer: the number on top of the stack at the end.

Example (level 2):

```
question: A stack starts empty. Do these steps in order: push 20, duplicate the top, swap the top two, push 3, swap the top two, multiply the top two (replace them by their product), multiply the top two (replace them by their product), push 1, add the top two (replace them by their sum), push 3, add the top two (replace them by their sum). What number is on top of the stack at the end?
structured: {"prog": [["push", 20], ["dup"], ["swap"], ["push", 3], ["swap"], ["mul"], ["mul"], ["push", 1], ["add"], ["push", 3], ["add"]]}
answer: 1204
```

### `R2.subtraction_game` (family games; supersedes R2.subtraction_game)

Procedure: label pile sizes from small to large (position values, combined over several piles by the exclusive-or rule). structured: {"piles": [int], "n": int, "moves": [int]}.
Fix round 3 (R-1): with two piles, the rule 'each pile alone is a win or a loss; equal -> no' read 0.79-0.82, and any exclusive-or of position values has a partial-bit rule (the parity of the sum of the values: 0.75-0.86, a
valid partial computation, reported as (P)). By construction there are FOUR piles (sizes 6 .. 20 + 6*level) and 5 allowed amounts (6 from level 3) taken from 1 .. 10 + level, so the position values spread over about six values and
'count the winning piles' falls to about 0.6; no heuristic enters. A turn removes an allowed amount from ONE pile; a player unable to move loses. Answer yes/no: does the first player win with perfect play; the wanted answer is drawn 50/50 and the draw
repeated until the KEY matches (balancing on the key, not on a heuristic, as in rev2).

Example (level 2):

```
question: Two players take turns. There are four piles of stones, with 29, 32, 27 and 30 stones. On a turn a player picks ONE pile and removes from it one of these amounts of stones: 2 or 3 or 6 or 10 or 11; an amount can be chosen only if that pile still has at least that many stones. A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.
structured: {"moves": [2, 3, 6, 10, 11], "n": 118, "piles": [29, 32, 27, 30]}
answer: no
```
