# R2 batch 1 lineages: structured-form schema for the second-solver agent

Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything.

## Interface

- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.
- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`R2.<name>`); suggested file `studies/m0/solvers_r2_batch1_<family>.py`.
- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).
- Answer formats: `number` = a decimal integer (may be negative); `list` = integers separated by `, `; `text` = one line; `yn` = `yes` or `no`; `name` = a name copied from the question.
- Fixtures: `studies/m0/fixtures/r2_batch1/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient.
- The question text is in the fixture only so that an auditor can check the wording and the stated conventions against the structured form; solvers must not parse it.
- No intended part is given: the part of each family is fixed by the registered partition seed over the final family list.

## Lineages (family, strict procedure, the builder's description of its structured form and answer rule)

### `R2.binary_search_trace` (family search)

Strict procedure: binary search with a stated midpoint rule: values looked at, or the third value.

Procedure: binary search with middle = floor((low+high)/2). structured: {"xs": [int] (ascending, distinct), "target": int, "ask": "values" | "third"}.
Positions are 1..n; low=1, high=n; look at the middle; stop if it equals the target; if the target is smaller set high = middle - 1, else low = middle + 1; stop (not found) when low > high.
Answer: the values looked at in order (comma list), or the third value looked at. The target is in the list about 70% of the time. Rejected: fewer than 3 values looked at.

Example (level 2):

```
question: A sorted list of 16 numbers (smallest first) is searched for 19. The positions are numbered 1 to 16. The search keeps a lower position (first 1) and an upper position (first 16). Each round it looks at the number in the position halfway between them, rounded down when needed (the sum of the two positions divided by 2, rounded down). If that number is the target the search stops; if the target is smaller, the upper position becomes one less than the position just looked at; otherwise the lower position becomes one more. If the lower position ever exceeds the upper position the search stops, having found nothing. The list: 2, 14, 19, 21, 22, 23, 24, 29, 31, 41, 45, 47, 48, 53, 61, 63. Which numbers does the search look at, in order? Give them separated by commas.
structured: {"ask": "values", "target": 19, "xs": [2, 14, 19, 21, 22, 23, 24, 29, 31, 41, 45, 47, 48, 53, 61, 63]}
answer: 29, 21, 14, 19
```

### `R2.bracket_match` (family parsing)

Strict procedure: last-opened-first-closed matching of three kinds of bracket: validity, or the partner position.

Procedure: match brackets with a last-opened-first-closed stack. structured: {"s": str, "ask": "valid" | "match", "p": int or null (1-based)}.
Answer, valid: yes/no, is every opener closed by the same kind of bracket in the right order (wrong strings are made by swapping two unlike characters, so the counts of each kind stay equal);
Answer, match: the 1-based position of the bracket that closes the opener at position p (the string is then balanced).

Example (level 2):

```
question: In the text [][]()[([][])] every opening bracket must be closed by a closing bracket of the same kind, and brackets that are opened later must be closed earlier (the kinds are round, square and curly). Is the text correctly nested? Answer yes or no.
structured: {"ask": "valid", "p": null, "s": "[][]()[([][])]"}
answer: yes
```

### `R2.bst_traversal` (family structures)

Strict procedure: binary-search-tree insertion, then a pre-, post- or level-order walk.

Procedure: binary-search-tree insertion then a tree walk. structured: {"xs": [int] (distinct, inserted in this order), "kind": "pre" | "post" | "level"}.
Answer: the numbers in that walk order, as a comma list. Rejected when the answer equals the insertion order or the sorted order.

Example (level 2):

```
question: Numbers are put one at a time into a tree. The first number is the top of the tree. Every later number starts at the top and moves down: at each number it meets, it goes to the left if it is smaller and to the right if it is larger, and it stays in the first empty place it reaches. The numbers are put in this order: 39, 25, 84, 72, 5, 57, 42. Read the tree like this: write everything in a number's left branch, then everything in its right branch, then the number itself (applied the same way inside each branch). Give the numbers in that reading order, separated by commas.
structured: {"kind": "post", "xs": [39, 25, 84, 72, 5, 57, 42]}
answer: 5, 25, 42, 57, 72, 84, 39
```

### `R2.cache_eviction` (family structures)

Strict procedure: cache with a stated eviction rule (LRU or FIFO): misses, or presence at the end.

Procedure: cache with an eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "misses" | "present", "item": item or null}.
A request for an item already in the cache is a hit; otherwise it is a miss, the item is loaded and, if the cache is full, the victim is removed first.
lru: the victim is the item whose last request is oldest; fifo: the item loaded longest ago (a hit changes nothing). Answer: the number of misses (never the number of distinct items nor the other policy's count), or yes/no whether `item` is in the cache at the end (balanced 50/50, and "among the last cap requests" is right in about half the items).

Example (level 2):

```
question: A cache holds at most 3 items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; if it is not, it is put into the cache, and if the cache was full the item that was requested longest ago (counting its latest request) is removed to make room. Requests in order: feather, feather, book, mirror, mirror, hammer, hammer, mirror, mirror, mirror, yo-yo, feather, mirror, yo-yo, mirror, mirror. After the last request, is book in the cache? Answer yes or no.
structured: {"ask": "present", "cap": 3, "item": "book", "policy": "lru", "seq": ["feather", "feather", "book", "mirror", "mirror", "hammer", "hammer", "mirror", "mirror", "mirror", "yo-yo", "feather", "mirror", "yo-yo", "mirror", "mirror"]}
answer: no
```

### `R2.cellular_automaton` (family dynamics)

Strict procedure: synchronous three-neighbour table update of a row, repeated.

Procedure: synchronous three-neighbour table update. structured: {"row": [0|1], "table": {"LCR": 0|1} (all 8 triples), "steps": int, "ask": "row" | "count"}.
Cells beyond either end count as 0. Answer: the row after `steps` steps as a 0/1 string without spaces, or the number of 1s in it. Rejected: constant tables, a final row equal to the start, or an all-equal final row.

Example (level 2):

```
question: A row of 11 cells holds 0s and 1s: 00011110110. In one step every cell changes at the same moment, according to the three digits (left neighbour, the cell itself, right neighbour): 111 becomes 1, 110 becomes 0, 101 becomes 0, 100 becomes 1, 011 becomes 1, 010 becomes 0, 001 becomes 1, 000 becomes 0. The cells beyond the two ends of the row count as 0. After 2 steps, what does the row look like? Give the digits with no spaces.
structured: {"ask": "row", "row": [0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0], "steps": 2, "table": {"000": 0, "001": 1, "010": 0, "011": 1, "100": 1, "101": 0, "110": 0, "111": 1}}
answer: 01111011000
```

### `R2.cheapest_network` (family graphs)

Strict procedure: cycle-avoiding cheapest-edge selection (minimum spanning network weight).

Procedure: Kruskal-style cycle-free edge selection. structured: {"towns": [name], "cables": [[a, b, cost]] (a, b are town names)}.
Answer: the least total cost of a set of cables that connects every town to every other (directly or through other towns). In 70% of items (drawn per item)
neither adding up the n-1 cheapest cables nor adding up each town's cheapest cable gives the answer.

Example (level 2):

```
question: The towns Calder, Dunmore, Penrith, Quarry, Thornbury and Upton must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. A cable between Quarry and Thornbury would cost 2. A cable between Calder and Penrith would cost 18. A cable between Thornbury and Penrith would cost 17. A cable between Calder and Dunmore would cost 12. A cable between Dunmore and Upton would cost 14. A cable between Calder and Thornbury would cost 18. A cable between Calder and Upton would cost 4. A cable between Thornbury and Upton would cost 7. A cable between Quarry and Calder would cost 16. A cable between Quarry and Dunmore would cost 8. What is the smallest total cost of a set of cables that joins all the towns?
structured: {"cables": [["Quarry", "Thornbury", 2], ["Calder", "Penrith", 18], ["Thornbury", "Penrith", 17], ["Calder", "Dunmore", 12], ["Dunmore", "Upton", 14], ["Calder", "Thornbury", 18], ["Calder", "Upton", 4], ["Thornbury", "Upton", 7], ["Quarry", "Calder", 16], ["Quarry", "Dunmore", 8]], "towns": ["Quarry", "Calder", "Thornbury", "Dunmore", "Penrith", "Upton"]}
answer: 38
```

### `R2.chip_toppling` (family dynamics)

Strict procedure: topple cells with 2+ chips until stable (abelian sandpile on a path with open ends).

Procedure: topple until stable (abelian sandpile on a path with open ends). structured: {"row": [int], "ask": "final" | "topplings" | "lost"}.
A cell with 2 or more chips topples: -2 for itself, +1 to each neighbour; a chip passed beyond an end is lost. Order does not change the end state, the number of topplings or the chips lost.
Answer: the final row (comma list), the total number of topplings, or the chips lost. Rejected when fewer than 2 or more than 400 topplings.

Example (level 2):

```
question: A row of 7 cells holds chips: 0, 2, 2, 4, 0, 2, 0 (from left to right). A cell that holds 2 or more chips topples: it gives up 2 chips, one going to the cell on its left and one to the cell on its right; a chip that goes past either end of the row is lost for good. Cells topple one at a time, in any order you like, until no cell holds 2 or more chips (the outcome does not depend on the order). How many chips are lost past the two ends in total?
structured: {"ask": "lost", "row": [0, 2, 2, 4, 0, 2, 0]}
answer: 4
```

### `R2.coin_change_min` (family dynprog)

Strict procedure: unbounded-supply capacity table: fewest coins for an exact amount (greedy is wrong in most items).

Procedure: unbounded-supply capacity table (fewest coins). structured: {"coins": [int], "amount": int}.
Answer: the fewest coins that sum exactly to amount (the amount is always reachable). In 80% of items (drawn per item) taking the largest coin first is NOT optimal; in 90% the amount divided by the largest coin, rounded up, is not the answer.

Example (level 2):

```
question: You have an unlimited supply of coins worth 4, 7 and 15. What is the smallest number of coins that add up to exactly 54?
structured: {"amount": 54, "coins": [4, 7, 15]}
answer: 7
```

### `R2.crt_smallest` (family numtheory)

Strict procedure: combine congruences with coprime moduli: smallest positive solution.

Procedure: combine congruences (Chinese remainder). structured: {"congruences": [[remainder, modulus]]} with pairwise coprime moduli.
Answer: the smallest positive integer x with x mod modulus = remainder for every pair (unique and at most the product of the moduli).

Example (level 2):

```
question: What is the smallest positive whole number that leaves remainder 5 when divided by 6, and leaves remainder 3 when divided by 11?
structured: {"congruences": [[5, 6], [3, 11]]}
answer: 47
```

### `R2.deferred_acceptance_partner` (family graphs)

Strict procedure: proposal-and-hold rounds (Gale-Shapley deferred acceptance).

Procedure: proposal-and-hold rounds (Gale-Shapley). structured: {"proposers": [name], "responders": [name], "prefs_p": {proposer: [responder best first]}, "prefs_r": {responder: [proposer best first]}, "who": proposer}.
Answer: the responder that `who` ends up with. The end result does not depend on the order of proposals. In 70% of items (drawn per item) it is neither `who`'s first choice nor the responder who ranks `who` highest.

Example (level 2):

```
question: Ada, Neva, Nico and Reed each want to be paired with one of Bram, Jules, Mona and Rhea, and each of those wants one of the first group. Nico ranks Rhea, Jules, Bram and Mona from best to worst. Reed ranks Mona, Bram, Jules and Rhea from best to worst. Ada ranks Jules, Rhea, Bram and Mona from best to worst. Neva ranks Jules, Rhea, Mona and Bram from best to worst. Jules ranks Neva, Nico, Ada and Reed from best to worst. Mona ranks Ada, Neva, Nico and Reed from best to worst. Bram ranks Reed, Ada, Nico and Neva from best to worst. Rhea ranks Ada, Neva, Nico and Reed from best to worst. They are paired by rounds: in each round every unpaired person from the first group asks the best-ranked person (on their own list) they have not asked before; a person who is asked keeps the best-ranked asker so far and turns the others down (a person who was kept is let go if someone better asks later). Rounds go on until everyone is paired. Who is Nico paired with? Choose from Bram, Jules, Mona and Rhea.
structured: {"prefs_p": {"Ada": ["Jules", "Rhea", "Bram", "Mona"], "Neva": ["Jules", "Rhea", "Mona", "Bram"], "Nico": ["Rhea", "Jules", "Bram", "Mona"], "Reed": ["Mona", "Bram", "Jules", "Rhea"]}, "prefs_r": {"Bram": ["Reed", "Ada", "Nico", "Neva"], "Jules": ["Neva", "Nico", "Ada", "Reed"], "Mona": ["Ada", "Neva", "Nico", "Reed"], "Rhea": ["Ada", "Neva", "Nico", "Reed"]}, "proposers": ["Nico", "Reed", "Ada", "Neva"], "responders": ["Jules", "Mona", "Bram", "Rhea"], "who": "Nico"}
answer: Bram
```

### `R2.dictionary_rank` (family combinatorics)

Strict procedure: factorial-base ranking or unranking of arrangements in dictionary order.

Procedure: factorial-base ranking/unranking of arrangements of distinct letters in dictionary order. structured: {"letters": [str] (sorted), "ask": "word" | "position", "k": int or null, "word": str or null}.
The arrangements of the n letters (each used once) are listed in dictionary order, numbered from 1. Answer, word: the arrangement at position k. Answer, position: the number of the arrangement `word`.

Example (level 2):

```
question: Write every arrangement of the letters c, l, p, x, z (each used exactly once in each arrangement) as a word, and list all the words in dictionary order (as in a dictionary, comparing letter by letter from the left, with a before b before c and so on). Number the words 1, 2, 3, ... in that list. What is the number of the word xzlpc?
structured: {"ask": "position", "k": null, "letters": ["c", "l", "p", "x", "z"], "word": "xzlpc"}
answer: 94
```

### `R2.expression_eval` (family parsing)

Strict procedure: evaluate an infix expression under a stated operator-precedence convention.

Procedure: evaluate an infix expression (operator ranks, parentheses). structured: {"text": str, "convention": "ranked" | "left_to_right"}.
ranked: parentheses first, then multiplication, then addition and subtraction, equal ranks left to right. left_to_right: parentheses first, then every operator left to right with no ranks.
Answer: the integer value (can be negative). In 90% of items (by internal redraw) the other convention gives a different value. In `match` items the answer is neither the next closer of the same kind nor the mirror position.

Example (level 2):

```
question: Work out 9 + 1 * (8 * (3 * 4) + 7) by this rule, which is not the usual one: do what is inside parentheses first, and then do the operators strictly in the order they are written from left to right, with multiplication getting no priority over addition or subtraction. What is the result?
structured: {"convention": "left_to_right", "text": "9 + 1 * (8 * (3 * 4) + 7)"}
answer: 1030
```

### `R2.gcd_euclid` (family numtheory)

Strict procedure: Euclid's remainder algorithm (gcd, lcm or step count).

Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm" | "steps"} with a > b > 0.
Answer: the greatest common divisor, the least common multiple, or the number of replacements (x, y) -> (y, x mod y) made until the second number is 0.

Example (level 2):

```
question: What is the greatest common divisor of 74 and 38?
structured: {"a": 74, "ask": "gcd", "b": 38}
answer: 2
```

### `R2.hamming_error_position` (family codes)

Strict procedure: parity-check syndrome of a Hamming code: the flipped position.

Procedure: parity-check syndrome of a Hamming code. structured: {"bits": [0|1] (position 1 is the leftmost), "n": int}.
Positions that are powers of two (1, 2, 4, 8, ...) are check positions; the check at position 2^j is set so that the count of 1s among all positions whose number has a 1 in binary place 2^j (itself included) is even.
The word was a correct codeword before at most one position was flipped. Answer: the flipped position, or 0 when nothing was flipped (level 0 always has a flip). Half the flips are drawn from the non-check positions only.

Example (level 2):

```
question: A word of 15 binary digits is written below; position 1 is the leftmost digit. Positions 1, 2, 4, 8, ... (the powers of two) are check positions. The check at position 2^j was chosen so that, among all positions whose number written in binary has a 1 in the place worth 2^j (the check position itself included), the count of 1s is even. The word was correct when it was sent, and at most one digit has been flipped since. Word: 101100000011011. Which position was flipped? Answer 0 if none was.
structured: {"bits": [1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1], "n": 15}
answer: 0
```

### `R2.hash_probe` (family structures)

Strict procedure: open-addressing hash table with linear probing: final slot or number of probes.

Procedure: open-addressing hash table with linear probing. structured: {"m": int, "keys": [int] (distinct, inserted in order), "ask": "slot" | "probes", "target": int}.
Slot of a key = key mod m, then the next slot, wrapping from m-1 to 0, until free. Answer: the slot where `target` ends up, or the number of slots looked at when the LAST key was inserted (including the free slot).
About 80% of the `slot` questions ask about a key that is not in its home slot, and about 80% of the `probes` questions have a last key that is not in its home slot.

Example (level 2):

```
question: A table has 9 slots numbered 0 to 8. A number goes into the slot whose number is the remainder of the number divided by 9; if that slot is taken, it goes into the next slot up (slot 8 is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: 74, 80, 12, 84, 94. In which slot does 74 end up?
structured: {"ask": "slot", "keys": [74, 80, 12, 84, 94], "m": 9, "target": 74}
answer: 2
```

### `R2.interval_scheduling` (family greedy)

Strict procedure: earliest-finish-time selection of non-overlapping intervals.

Procedure: pick by earliest finish time (activity selection). structured: {"meetings": [[start, end]]} (integer times, start < end).
Answer: the largest number of meetings one person can attend when no two attended meetings overlap (a meeting ending exactly when another starts does not overlap it).
In 80% of items (drawn per item) neither choosing by earliest start nor choosing the shortest meeting first is optimal.

Example (level 2):

```
question: A person can attend only one meeting at a time. Times are whole numbers of minutes: meeting 1 runs from 16 to 21; meeting 2 runs from 20 to 25; meeting 3 runs from 11 to 16; meeting 4 runs from 1 to 4; meeting 5 runs from 29 to 31; meeting 6 runs from 51 to 57; meeting 7 runs from 19 to 25; meeting 8 runs from 12 to 15; meeting 9 runs from 49 to 52; meeting 10 runs from 44 to 50; meeting 11 runs from 37 to 39; meeting 12 runs from 39 to 41; meeting 13 runs from 35 to 41; meeting 14 runs from 19 to 20. Two meetings clash if they share any stretch of time; a meeting that ends at the very minute another starts does not clash with it. What is the largest number of meetings the person can attend without any clash?
structured: {"meetings": [[16, 21], [20, 25], [11, 16], [1, 4], [29, 31], [51, 57], [19, 25], [12, 15], [49, 52], [44, 50], [37, 39], [39, 41], [35, 41], [19, 20]]}
answer: 9
```

### `R2.lcs_length` (family dynprog)

Strict procedure: fill a two-string prefix table: longest common subsequence length.

Procedure: two-sequence prefix table (longest common subsequence). structured: {"a": str, "b": str}.
Answer: the length of the longest string that is a subsequence (letters kept in order, not necessarily adjacent) of both strings.

Example (level 2):

```
question: A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). What is the length of the longest string that is a subsequence of both 'cababccbcaa' and 'ccaaaaacba'?
structured: {"a": "cababccbcaa", "b": "ccaaaaacba"}
answer: 6
```

### `R2.lis_length` (family dynprog)

Strict procedure: longest strictly increasing subsequence length.

Procedure: longest strictly increasing subsequence. structured: {"xs": [int]} (distinct). Answer: its length. In 70% of items "ascents + 1" and "longest run of ascents" are not the answer.

Example (level 2):

```
question: Choose some of these numbers, keeping the order in which they are written, so that each chosen number is larger than the one chosen before it (the chosen numbers need not be next to each other). What is the largest count of numbers you can choose? Numbers: 100, 5, 3, 40, 220, 98, 185, 166, 83, 25, 50, 120, 85, 160, 105, 119, 30, 208, 54, 66, 94, 92, 226.
structured: {"xs": [100, 5, 3, 40, 220, 98, 185, 166, 83, 25, 50, 120, 85, 160, 105, 119, 30, 208, 54, 66, 94, 92, 226]}
answer: 8
```

### `R2.longest_palindromic_substring` (family strings)

Strict procedure: expand around every centre: longest palindromic block length.

Procedure: expand around each centre. structured: {"s": str}. Answer: the length of the longest block of neighbouring letters that reads the same forwards and backwards.
A palindrome of a random length is planted in a random string, so the answer is spread; the true longest is computed afterwards (it may exceed the planted one).

Example (level 2):

```
question: Look at the string 'cbbcabacccbbccccbc'. Find the longest block of letters, all next to each other in the string, that reads the same forwards and backwards. How many letters long is it?
structured: {"s": "cbbcabacccbbccccbc"}
answer: 8
```

### `R2.luhn_check` (family codes)

Strict procedure: alternate-digit doubling checksum (Luhn): validity or check digit.

Procedure: alternate-digit doubling checksum (Luhn). structured: {"digits": [int] (the number as written), "ask": "valid" | "check_digit"}.
valid: yes/no, whether the whole number's total is a multiple of 10 (invalid items change exactly one digit of a valid number, which is always detected). check_digit: payload `digits`;
the check digit is written at the right end of the payload and the rule above is applied to the whole number (so the digit written is NOT doubled and the payload's last digit IS doubled). Answer: the digit 0-9 that makes the total a multiple of 10.

Example (level 2):

```
question: Start at the rightmost digit and move left: leave the 1st digit as it is, double the 2nd, leave the 3rd, double the 4th, and so on. Whenever a doubled digit is more than 9, subtract 9 from it. Add up all the results. A number is valid if the total is a multiple of 10. One more digit is to be written at the right end of 0744761398 so that the new number is valid (the digit written there is the rightmost digit of the new number). Which digit must be written?
structured: {"ask": "check_digit", "digits": [0, 7, 4, 4, 7, 6, 1, 3, 9, 8]}
answer: 0
```

### `R2.max_subarray_sum` (family dynprog)

Strict procedure: running best-ending-here scan: largest sum of a contiguous block.

Procedure: running best-ending-here scan (Kadane). structured: {"xs": [int]}. Answer: the largest sum of one or more neighbouring numbers
(a block with no gaps). Items are rejected when the answer is the single largest number, the sum of the positives or the total.

Example (level 2):

```
question: Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: 7, -6, 3, -3, -6, 3, -1, 3, -3, 6.
structured: {"xs": [7, -6, 3, -3, -6, 3, -1, 3, -3, 6]}
answer: 8
```

### `R2.merge_smallest_cost` (family greedy)

Strict procedure: repeatedly merge the two smallest items (Huffman-style total cost).

Procedure: repeatedly merge the two smallest (Huffman-style cost; ties do not change the total). structured: {"ws": [int]}.
Answer: the total of the costs paid, each merge costing the sum of the two parts joined.

Example (level 2):

```
question: There are piles of stones with these sizes: 11, 12, 4, 8, 16, 2. Two piles can be joined into one pile; joining costs as many coins as the size of the new pile. The piles are joined, two at a time, until one pile is left. What is the smallest total number of coins that can be paid?
structured: {"ws": [11, 12, 4, 8, 16, 2]}
answer: 126
```

### `R2.min_heap_ops` (family structures)

Strict procedure: array binary min-heap: sift-up insertion and sift-down removal.

Procedure: array binary min-heap with sift-up insertion and sift-down removal. structured: {"xs": [int] (distinct, inserted in order), "removals": int}.
Answer: the array (positions 1..n) after the inserts and then `removals` removals of the smallest. Rejected when the answer is the insertion order or sorted.

Example (level 2):

```
question: A heap is a row of numbers in positions 1, 2, 3, ... where the number in position p is never larger than the numbers in positions 2p and 2p+1 (when those exist). To add a number: put it in the first free position at the end, then, while it is smaller than the number in position (its position divided by 2, rounded down), swap the two. To remove the smallest: take out the number in position 1, put the number from the last position into position 1 (the row is now one shorter), then, while it is larger than the smaller of the numbers in positions 2p and 2p+1 (those that exist), swap it with that smaller number. Start with an empty heap and add these numbers in order: 30, 7, 81, 65, 43, 71, 85. Give the row from position 1 to the end, separated by commas.
structured: {"removals": 0, "xs": [30, 7, 81, 65, 43, 71, 85]}
answer: 7, 30, 71, 65, 43, 81, 85
```

### `R2.modular_power` (family numtheory)

Strict procedure: repeated squaring modulo m.

Procedure: repeated squaring modulo m. structured: {"a": int, "e": int, "m": int}. Answer: the remainder of a^e divided by m (never 0 or 1).

Example (level 2):

```
question: Multiply together 33 copies of the number 4 (a product with 33 factors, each equal to 4). What is the remainder when this product is divided by 27?
structured: {"a": 4, "e": 33, "m": 27}
answer: 19
```

### `R2.prime_factor_query` (family numtheory)

Strict procedure: trial-division prime factorisation (largest prime, or sum of the prime factors with multiplicity).

Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}.
Answer: the largest prime factor of n, or the sum of all the primes in its prime factorisation, repeated primes counted each time (12 = 2 x 2 x 3 gives 7).

Example (level 2):

```
question: What is the largest prime number that divides 3410 exactly?
structured: {"ask": "largest", "n": 3410}
answer: 31
```

### `R2.subtraction_game` (family games)

Strict procedure: label pile sizes win/lose from small to large (backward induction).

Procedure: label every pile size win/lose from small to large (a size is a win when some allowed move reaches a losing size). structured: {"n": int, "moves": [int]}.
Answer: yes/no, does the player who moves first win with perfect play. A player who cannot move loses. The wanted answer is drawn 50/50 per item; in 70% of items the "pile size mod (largest move + 1)" rule is wrong.

Example (level 2):

```
question: Two players take turns removing stones from one pile of 46 stones. On a turn a player must remove one of these amounts of stones: 3 or 4 or 6; an amount can be chosen only if the pile still has at least that many stones. A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.
structured: {"moves": [3, 4, 6], "n": 46}
answer: no
```
