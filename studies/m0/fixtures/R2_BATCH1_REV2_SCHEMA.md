# R2 batch 1, revision 2: structured-form schema for the second-solver agent (revised shapes only)

Written by the implementer. Not a result; nothing here approves anything. Same interface as `R2_BATCH1_SCHEMA.md` (a solver reads ONLY `structured`; `solve(structured) -> str`; raise `ValueError` when the form has no unique answer).
These shapes SUPERSEDE the batch-1 shapes of the same ids (see `SUPERSEDES` in `studies/m0/lineages_r2_rev2.py`); lineages not listed here are unchanged from batch 1. Fixtures: `studies/m0/fixtures/r2_batch1_rev2/<id>.jsonl`, 20 items per level 0..6.

## Revised shapes

### `R2.bracket_match` (family parsing; supersedes R2.bracket_match)

Procedure: match brackets with a stack. structured: {"s": str, "ask": "valid" | "match", "p": int or null (1-based)}.
valid (yes/no, drawn 50/50 as a coin, not redrawn): the base text is a random correctly nested text that has at least two nested-or-enclosing pairs of DIFFERENT kinds
(a structural requirement shared by both answers); a `no` text swaps the closing kinds of two such pairs, so counts of each kind are kept and the wrong closer never sits next to its opener
(an adjacent wrong-kind pair cannot occur by construction). match: a random correctly nested text, and an opener drawn UNIFORMLY among those whose pair encloses something (so 'the very next position' cannot be the partner; no other partner position is excluded). Three kinds at every level (batch 1 used two kinds up to level 2) and 8+level pairs (batch 1: 5+level), because the 'last closer of the same kind' tell shrinks with length.

Example (level 2):

```
question: In the text (()){{[]{}}}(({}[])) every opening bracket must be closed by a closing bracket of the same kind, and brackets that are opened later must be closed earlier (the kinds are round, square and curly). Is the text correctly nested? Answer yes or no.
structured: {"ask": "valid", "p": null, "s": "(()){{[]{}}}(({}[]))"}
answer: yes
```

### `R2.cache_eviction` (family structures; supersedes R2.cache_eviction)

Procedure: cache with a stated eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "misses" | "present", "item": item or null}.
Batch-1 `agree` logic removed. `misses`: either policy, no gate. `present`: FIFO only (under LRU the cache is the last cap distinct requests, which the tell "among the last requests" reads off),
the pool is 2*cap items and the asked item is drawn uniformly from it, so about half the draws are in a full cache BY CONSTRUCTION (no balancing redraw).

Example (level 2):

```
question: A cache holds at most 2 items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; if it is not, it is put into the cache, and if the cache was full the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order). Requests in order: kettle, kettle, needle, pencil, pencil, pencil, teapot, teapot, needle, pencil, kettle, kettle, pencil, kettle, needle, needle. After the last request, is teapot in the cache? Answer yes or no.
structured: {"ask": "present", "cap": 2, "item": "teapot", "policy": "fifo", "seq": ["kettle", "kettle", "needle", "pencil", "pencil", "pencil", "teapot", "teapot", "needle", "pencil", "kettle", "kettle", "pencil", "kettle", "needle", "needle"]}
answer: no
```

### `R2.cheapest_network` (family graphs; supersedes R2.cheapest_network)

Procedure: cycle-avoiding cheapest-edge selection. structured as batch 1. Batch-1 gate on the naive outcome REMOVED. By construction the n = 3g towns (g = 2 + level//3) form g groups of three; the three cables inside a group (a triangle) cost 1..6 and every cable between groups costs 7..20.
The n cables inside groups are the n cheapest, so the n-1 cheapest always contain a cycle, and every town's cheapest cable is inside its group, so 'add up the n-1 cheapest' is never the answer and a per-town cheapest-cable sum is the answer only by coincidence (measured under 1%); a connection between groups is always needed.

Example (level 2):

```
question: The towns Calder, Dunmore, Fenwick, Larkin, Yarrow and Zennor must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. A cable between Yarrow and Zennor would cost 14. A cable between Fenwick and Calder would cost 1. A cable between Dunmore and Zennor would cost 4. A cable between Larkin and Fenwick would cost 16. A cable between Yarrow and Calder would cost 4. A cable between Yarrow and Fenwick would cost 2. A cable between Larkin and Dunmore would cost 4. A cable between Larkin and Zennor would cost 5. What is the smallest total cost of a set of cables that joins all the towns?
structured: {"cables": [["Yarrow", "Zennor", 14], ["Fenwick", "Calder", 1], ["Dunmore", "Zennor", 4], ["Larkin", "Fenwick", 16], ["Yarrow", "Calder", 4], ["Yarrow", "Fenwick", 2], ["Larkin", "Dunmore", 4], ["Larkin", "Zennor", 5]], "towns": ["Yarrow", "Larkin", "Dunmore", "Fenwick", "Zennor", "Calder"]}
answer: 25
```

### `R2.chip_toppling` (family dynamics; supersedes R2.chip_toppling)

Procedure: topple until stable (abelian sandpile on a path with open ends). structured: {"row": [int], "ask": "topplings" | "topplings_of", "cell": int or null (1-based)}.
The batch-1 shapes `final` and `lost` are DROPPED: conservation of chips and of the first moment answer them in closed form (audit: 0.97-1.00 and 0.82-0.90).
Order does not change any cell's number of topplings. Answer: the total number of topplings, or the number of times cell `cell` topples. Bound: 2 to 400 topplings (a size bound, not a heuristic gate).

Example (level 2):

```
question: A row of 7 cells holds chips: 1, 5, 2, 3, 1, 4, 1 (from left to right). A cell that holds 2 or more chips topples: it gives up 2 chips, one going to the cell on its left and one to the cell on its right; a chip that goes past either end of the row is lost for good. Cells topple one at a time, in any order you like, until no cell holds 2 or more chips (the outcome, including how many times each cell topples, does not depend on the order). How many topplings happen in total?
structured: {"ask": "topplings", "cell": null, "row": [1, 5, 2, 3, 1, 4, 1]}
answer: 73
```

### `R2.coin_change_min` (family dynprog; supersedes R2.coin_change_min)

Procedure: unbounded-supply capacity table (the same lineage; the final question changes). structured: {"coins": [int], "amount": int, "ask": "ways"}.
The batch-1 question (fewest coins) is SUPERSEDED: greedy and amount/largest bounds answer it (audit: ceil+1 0.55-0.69, an overshoot created by excluding ceil). Now the question is the
number of different sets of coins (order does not matter) that add up exactly to `amount`; no greedy or bound answers it. Answer: that count (at least 1).

Example (level 2):

```
question: You have an unlimited supply of coins worth 4, 19 and 21. In how many different ways can exactly 58 be paid? Two ways are the same when they use the same number of coins of each worth (the order in which coins are handed over does not matter).
structured: {"amount": 58, "ask": "ways", "coins": [4, 19, 21]}
answer: 2
```

### `R2.crt_smallest` (family numtheory_b1; supersedes R2.crt_smallest)

Procedure: combine congruences with coprime moduli. structured: {"congruences": [[remainder, modulus]]}. Same shape as batch 1 with wider moduli (3..30+10*level) so that the structure count meets the demand
at the G written (batch 1: 1,212 and 2,215 distinct structures at levels 0 and 1). Answer: the smallest positive whole number with all the stated remainders (unique, at most the product of the moduli).

Example (level 2):

```
question: What is the smallest positive whole number that leaves remainder 6 when divided by 8, and leaves remainder 9 when divided by 17?
structured: {"congruences": [[6, 8], [9, 17]]}
answer: 94
```

### `R2.deferred_acceptance_partner` (family graphs; supersedes R2.deferred_acceptance_partner)

Procedure: proposal-and-hold rounds. structured as batch 1. Batch-1 redraw on the first-choice and best-ranked-by outcomes REMOVED. n is 4 + level//2 (4..7; batch 1 had 3..6), preferences independent
and uniform. Residual heuristic rates are natural, not engineered; see the manifest (this lineage is reported NOT REGISTERED if they stay far above chance).

Example (level 2):

```
question: Ada, Dara, Glen, Sam and Tina each want to be paired with one of Greta, Opal, Pete, Sven and Walt, and each of those wants one of the first group. Sam ranks Greta, Walt, Sven, Pete and Opal from best to worst. Ada ranks Pete, Opal, Sven, Walt and Greta from best to worst. Tina ranks Greta, Sven, Walt, Pete and Opal from best to worst. Glen ranks Walt, Sven, Opal, Pete and Greta from best to worst. Dara ranks Opal, Pete, Walt, Sven and Greta from best to worst. Pete ranks Glen, Tina, Sam, Dara and Ada from best to worst. Greta ranks Sam, Tina, Glen, Dara and Ada from best to worst. Opal ranks Tina, Ada, Dara, Sam and Glen from best to worst. Walt ranks Dara, Glen, Sam, Ada and Tina from best to worst. Sven ranks Tina, Dara, Ada, Glen and Sam from best to worst. They are paired by rounds: in each round every unpaired person from the first group asks the best-ranked person (on their own list) they have not asked before; a person who is asked keeps the best-ranked asker so far and turns the others down (a person who was kept is let go if someone better asks later). Rounds go on until everyone is paired. Who is Tina paired with? Choose from Greta, Opal, Pete, Sven and Walt.
structured: {"prefs_p": {"Ada": ["Pete", "Opal", "Sven", "Walt", "Greta"], "Dara": ["Opal", "Pete", "Walt", "Sven", "Greta"], "Glen": ["Walt", "Sven", "Opal", "Pete", "Greta"], "Sam": ["Greta", "Walt", "Sven", "Pete", "Opal"], "Tina": ["Greta", "Sven", "Walt", "Pete", "Opal"]}, "prefs_r": {"Greta": ["Sam", "Tina", "Glen", "Dara", "Ada"], "Opal": ["Tina", "Ada", "Dara", "Sam", "Glen"], "Pete": ["Glen", "Tina", "Sam", "Dara", "Ada"], "Sven": ["Tina", "Dara", "Ada", "Glen", "Sam"], "Walt": ["Dara", "Glen", "Sam", "Ada", "Tina"]}, "proposers": ["Sam", "Ada", "Tina", "Glen", "Dara"], "responders": ["Pete", "Greta", "Opal", "Walt", "Sven"], "who": "Tina"}
answer: Sven
```

### `R2.expression_eval` (family parsing; supersedes R2.expression_eval)

Procedure: evaluate an infix expression under a stated convention. structured: {"text": str, "convention": "ranked" | "left_to_right"}.
Both conventions now say that the rule is used inside parentheses as well, and ``ranked`` defines addition and subtraction as ONE rank worked left to right
(the batch-1 words "operators of the same kind" could be read as the same symbol). No item is redrawn on what the other convention gives. Answer: the integer value.

Example (level 2):

```
question: Work out ((9 * 4) - 2) * 1 * (1 + 3). Use these rules, in this order, also inside every pair of parentheses: do what is inside parentheses first, innermost first; then do all the multiplications, from left to right; then do all the additions and subtractions together as one group, strictly from left to right (so 8 - 3 + 2 is worked as (8 - 3) + 2 = 7, and 8 + 3 - 2 as (8 + 3) - 2 = 9). What is the result?
structured: {"convention": "ranked", "text": "((9 * 4) - 2) * 1 * (1 + 3)"}
answer: 136
```

### `R2.gcd_euclid` (family numtheory_b1; supersedes R2.gcd_euclid)

Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm"}. The `steps` shape is DROPPED (its answers sit in a narrow range, the constant 3 scored 0.27-0.38).
By construction the common divisor g has no prime factor below 11 (so 'the product of the common small primes' is always 1), and the cofactors p, q are coprime and not within 1 of each other.

Example (level 2):

```
question: What is the greatest common divisor of 3737 and 1480?
structured: {"a": 3737, "ask": "gcd", "b": 1480}
answer: 37
```

### `R2.hash_probe` (family structures; supersedes R2.hash_probe)

Procedure: linear-probing hash table. structured: {"m": int, "keys": [int], "ask": "slot" | "probes", "target": int}.
By construction: the table is filled to m-1 of m slots and every key's home slot (key mod m) lies in the first third of the table (0..m//3), so clusters are long and spill over; the asked key is drawn UNIFORMLY among the keys (slot) or is the last key (probes); no preference for displaced keys.
Answer: the slot where `target` ends up, or the number of slots looked at when the last key is added.

Example (level 2):

```
question: A table has 9 slots numbered 0 to 8. A number goes into the slot whose number is the remainder of the number divided by 9; if that slot is taken, it goes into the next slot up (slot 8 is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: 65, 74, 63, 27, 47, 64, 82, 36. When 36 (the last number) is added, how many slots are looked at, counting the slot where it is finally placed?
structured: {"ask": "probes", "keys": [65, 74, 63, 27, 47, 64, 82, 36], "m": 9, "target": 36}
answer: 8
```

### `R2.lcs_length` (family dynprog; supersedes R2.lcs_length)

Procedure: two-string prefix table. structured: {"a": str, "b": str}. By construction a common subsequence of length k (k uniform from 2 to the shorter length minus 2) is PLANTED, so the answer
(>= k, computed by the table, not from the plan) does not follow the letter-count overlap or the string lengths; alphabet size 4..6 and lengths 8+level..14+2*level are drawn per item.

Example (level 2):

```
question: A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). What is the length of the longest string that is a subsequence of both 'dcedebeadee' and 'abbadeeedaa'?
structured: {"a": "dcedebeadee", "b": "abbadeeedaa"}
answer: 5
```

### `R2.lis_length` (family dynprog; supersedes R2.lis_length)

Procedure: longest strictly increasing subsequence. structured: {"xs": [int]} (distinct). By construction an increasing subsequence of length k (k uniform from 3 to n-3) is PLANTED by sorting the values at k random positions of a random row (the other numbers stay random), so the answer (at least k, computed by the DP, not from the plan) is spread over a wide range and does not follow 2*sqrt(n); n is drawn from 9+level..18+3*level.

Example (level 2):

```
question: Choose some of these numbers, keeping the order in which they are written, so that each chosen number is larger than the one chosen before it (the chosen numbers need not be next to each other). What is the largest count of numbers you can choose? Numbers: 53, 50, 63, 57, 60, 74, 14, 87, 36, 70, 76.
structured: {"xs": [53, 50, 63, 57, 60, 74, 14, 87, 36, 70, 76]}
answer: 5
```

### `R2.longest_palindromic_substring` (family strings; supersedes R2.longest_palindromic_substring)

Procedure: expand around each centre. structured: {"s": str}. By construction a palindrome of length uniform from 3 to 12 is planted in a string of 16+2*level letters (batch 1: 3..7+level in 14+2*level),
so the answer is spread over about ten values. The answer is computed from the string.

Example (level 2):

```
question: Look at the string 'babbbbcbabbabcccccac'. Find the longest block of letters, all next to each other in the string, that reads the same forwards and backwards. How many letters long is it?
structured: {"s": "babbbbcbabbabcccccac"}
answer: 8
```

### `R2.max_subarray_sum` (family dynprog; supersedes R2.max_subarray_sum)

Procedure: best-ending-here scan. structured: {"xs": [int]}. Batch-1 rejection on (largest, sum of positives, total) REMOVED. By construction the row is built from runs of positive numbers separated by
strongly negative numbers (-20..-12), and the planted best block is two positive runs joined across ONE small dip (the dip is smaller than both runs' sums), so the best block contains a negative number
and 'the best run of non-negative numbers' cannot be it; decoy runs of one or two numbers (1..5) are placed on either side, so the planted block (at least 16) always wins. Answer: the largest sum of a block of neighbouring numbers (computed from the row, not from the plan).

Example (level 2):

```
question: Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: -17, 5, 7, 8, -17, 5, 9, 7, -20, 4, -20, -19, 3, 5, -18.
structured: {"xs": [-17, 5, 7, 8, -17, 5, 9, 7, -20, 4, -20, -19, 3, 5, -18]}
answer: 24
```

### `R2.merge_smallest_cost` (family greedy; supersedes R2.merge_smallest_cost)

Procedure: repeatedly merge the two smallest (Huffman-style cost). structured: {"ws": [int]}. Wording now says ANY two piles may be joined (not only neighbours).
Widened at level 0 (5 piles of 1..20; batch 1 had 4 piles of 1..9, 488 distinct multisets). No gate on the answer. Answer: the least total cost.

Example (level 2):

```
question: There are piles of stones with these sizes: 27, 12, 9, 22, 24, 13, 14. Any two piles (they need not be next to each other in this list) can be joined into one pile; joining costs as many coins as the size of the new pile. The piles are joined, two at a time, until one pile is left. What is the smallest total number of coins that can be paid?
structured: {"ws": [27, 12, 9, 22, 24, 13, 14]}
answer: 333
```

### `R2.modular_power` (family numtheory_b1; supersedes R2.modular_power)

Procedure: repeated squaring modulo m. structured: {"a": int, "e": int, "m": int}. Batch-1 rejection of answers 0, 1 and a REMOVED. By construction m is a product of two different primes (so
reductions that need a prime modulus, such as Fermat's, are not valid shortcuts), m >= 35 at level 0, and e is at least 2m (so e mod (m-1) is a genuine reduction and a^2 mod m is not the answer except by chance).

Example (level 2):

```
question: Multiply together 205 copies of the number 36 (a product with 205 factors, each equal to 36). What is the remainder when this product is divided by 55?
structured: {"a": 36, "e": 205, "m": 55}
answer: 1
```

### `R2.prime_factor_query` (family numtheory_b1; supersedes R2.prime_factor_query)

Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}. By construction the LARGEST prime factor is drawn uniformly from the primes 17..(pool maximum: 61 at level 0, 97 after; 4 to 6 prime factors, widened for capacity),
one prime up to it is used TWICE (so 'the sum of the different primes' is never the sum asked), and the other factors are drawn uniformly from the primes up to it (batch 1 drew all factors from the pool, so the largest sat at the top of the pool: constant 0.17-0.21). Answer: the largest prime factor, or the sum of the primes in the
factorisation counting repeats.

Example (level 2):

```
question: What is the largest prime number that divides 8250033 exactly?
structured: {"ask": "largest", "n": 8250033}
answer: 89
```

### `R2.string_rewrite_nonidentity` (family rewrite; supersedes R2.string_rewrite)

Procedure: sequential substitution (the existing R2.string_rewrite, same cluster). structured: {"s": str, "rules": [[pattern, replacement]]}.
Every rule is drawn so that it does something: the pattern is a substring of the string as it stands when the rule is reached, and the replacement differs from it
(it may be empty = deletion). Steps scan left to right over non-overlapping matches. Answer: the final string (never empty).

Example (level 2):

```
question: Start with the string bcaaabaaac. Do these steps in order, each step scanning left to right over non-overlapping matches in the string as it is when the step starts: replace every 'ca' with 'b'; delete every 'bb'. What is the final string?
structured: {"rules": [["ca", "b"], ["bb", ""]], "s": "bcaaabaaac"}
answer: aabaaac
```

### `R2.subtraction_game` (family games; supersedes R2.subtraction_game)

Procedure: label pile sizes from small to large (here with two piles, so each pile needs its own label, combined by the exclusive-or rule). structured: {"piles": [n1, n2], "n": n1 + n2, "moves": [int]}.
Batch-1 one-pile shape SUPERSEDED (audit: residue tells 0.55-0.62 and an overshoot from excluding one). Two piles: a turn removes an allowed amount from ONE pile; the player unable to move loses.
Answer yes/no: does the first player win with perfect play. The wanted answer is drawn 50/50 and the piles are redrawn until the KEY matches (balancing on the key, not on any heuristic).

Example (level 2):

```
question: Two players take turns. There are two piles of stones, with 37 and 20 stones. On a turn a player picks ONE pile and removes from it one of these amounts of stones: 3 or 4 or 7; an amount can be chosen only if that pile still has at least that many stones. A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.
structured: {"moves": [3, 4, 7], "n": 57, "piles": [37, 20]}
answer: yes
```

### `R2.to_base_wide` (family base; supersedes R2.to_base)

Procedure: repeated division (the existing R2.to_base, same cluster). structured: {"n": int, "base": int}. Widened: bases 2..9 at levels 0-1 and the batch-0 set
beyond, and n up to 500 * 4^(level+1) (the existing L0 space was 151 values x 5 bases = 755 items). Answer: the digits (0-9 then a-f).

Example (level 2):

```
question: Write the decimal number 18674 in base 5. Use digits 0-9 and then lowercase letters a-f for ten to fifteen.
structured: {"base": 5, "n": 18674}
answer: 1044144
```
