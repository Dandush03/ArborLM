# C1 batch 1, revision 2: structured-form schema for the second-solver agent

Written by the implementer (Sonnet 5.5). Not a result; nothing here approves anything. Own checks only: not independent review, not Astra validation, not human approval. The interface, the key, the checker and the Python conventions are exactly those of `C1_BATCH1_SCHEMA.md` (same structured form `{"program": <tree>}`, same existing tree-walking second solver `solvers_c1.c1_trace`). Fixtures: `studies/m0/fixtures/c1_batch1_rev2/<lineage id>.jsonl`, 20 distinct items for each of the 7 levels; PROPOSED lineages are marked `"proposed": true` in every line.

## Lineages

### `C1.bracket_matching_traced` (PROPOSED additional shapes; family stacks)

PROPOSED shapes of the bracket stack (as ``bracket_matching``): the stack height after the first p characters (the loop stops at the stated
p, 3 <= p < the length); the sum of the positions of the closing brackets that popped (matched), a sum over one branch.

Example (level 2):

```
n = '[()[[(())'
k = []
for cur in range(len(n)):
    k.append(0)
out = 0
for cur in range(8):
    y = n[cur]
    if y == '(':
        k[out] = 1
        out += 1
    elif y == '[':
        k[out] = 2
        out += 1
    elif y == ')':
        if out > 0 and k[out - 1] == 1:
            out -= 1
    elif out > 0 and k[out - 1] == 2:
        out -= 1
print(out)
```

answer: `4`

### `C1.bytecode_loop_r2` (supersedes C1.bytecode_loop; family simulation)

As ``bytecode_loop`` (code is a flat list of (opcode, argument) pairs; a program counter fetches a pair, advances by two, then acts on
acc and reg; opcode numbers are a random assignment written in the code) with two changes made by construction. (1) From level 1 the
program contains exactly three skip pairs, at random positions after the first pair and before the last, and a
skip fires when acc and its argument have the same parity (about one time in two), so the sum of ALL arguments is the sum of the executed
ones only when no skip fires. (2) The register shape is offered whenever the code contains a store pair (no condition on the value).
Ops: add arg; multiply by arg; subtract arg (from level 0); skip the next pair if acc % 2 == arg % 2 (from level 1); acc = acc % arg
(from level 2); reg = acc and acc = acc + reg (from level 3). Shapes: final acc, the sum of the arguments of the pairs executed
(from level 1; a skipped pair does not count), final reg. 4 to 12 pairs.

Example (level 2):

```
best = [3, 7, 5, 3, 7, 6, 4, 3, 7, 9, 7, 5, 1, 8, 4, 2]
res = 0
u = 0
out = 0
while res < len(best):
    total = best[res]
    val = best[res + 1]
    res = res + 2
    out += val
    if total == 3:
        u = u + val
    elif total == 4:
        u = u * val
    elif total == 5:
        u = u - val
    elif total == 7:
        if u % 2 == val % 2:
            res = res + 2
    elif total == 1:
        u = u % val
print(out)
```

answer: `40`

### `C1.cellular_update_r2` (supersedes C1.cellular_update; family simulation)

As ``cellular_update`` (one-dimensional automaton on a ring from an eight-entry rule table, fresh row per generation; shapes: the row,
the sum over cells of index times cell value) but the accumulator of the weighted shape is one of the six drawn names, so it can never collide
with the loop variable (the old fixed name ``w`` did, in 3.7 % of weighted draws).

Example (level 2):

```
cur = [1, 0, 0, 0, 0, 0, 1]
q = [1, 0, 0, 1, 0, 1, 0, 0]
for v in range(3):
    m = []
    for a in range(7):
        m.append(q[cur[(a + 6) % 7] * 4 + cur[a] * 2 + cur[(a + 1) % 7]])
    cur = m
r = 0
for a in range(7):
    r += a * cur[a]
print(r)
```

answer: `0`

### `C1.circle_elimination_r2` (supersedes C1.circle_elimination; family simulation)

As ``circle_elimination`` (Josephus counting around a ring of flags; shapes: the index struck last, the sum of the indices struck, the
survivor) with the space widened: n = 9 + level, plus one more flag at level 0 half the time, and the position the counting starts from is drawn (stated in the code) instead of always the last flag.

Example (level 2):

```
y = [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1]
total = 8
s = 0
for cur in range(8):
    u = 0
    while u < 4:
        total = (total + 1) % 11
        if y[total] == 1:
            u += 1
    y[total] = 0
    s += total
print(s)
```

answer: `46`

### `C1.euclid_gcd_traced` (PROPOSED additional shapes; family while)

PROPOSED shapes of Euclid's remainder algorithm (as ``euclid_gcd`` with a round counter): the pair (a, b) after a stated number R of rounds,
written 'a b' (1 <= R < the number of rounds, so it is not the gcd); the sum of the quotients a // b over the rounds in which the quotient was at least 2.

Example (level 2):

```
p = 16
x = 10
u = 0
w = 0
while x != 0:
    if p // x >= 2:
        w += p // x
    d = p % x
    p = x
    x = d
    u += 1
print(w)
```

answer: `2`

### `C1.fast_power_r2` (supersedes C1.fast_power; family while)

As ``fast_power`` (modular exponentiation by repeated squaring; shapes: the result, the final b, the sum of b at the start of each round)
with the level-0 space widened: exponent bits 2 + level, plus one more bit at level 0 half the time, and the modulus up to 40 at level 0.
The formula-answerable status of these shapes (result = pow) is unchanged and goes to the human lead.

Example (level 2):

```
val = 1
k = 16
x = 13
q = 42
while x > 0:
    if x % 2 == 1:
        val = val * k % q
    k = k * k % q
    x = x // 2
print(val)
```

answer: `16`

### `C1.fast_power_traced` (PROPOSED additional shapes; family while)

PROPOSED shapes of square-and-multiply (the program of ``fast_power`` with a round counter): the result after a stated number s of rounds
(the loop also stops when it has run s rounds, 1 <= s < the number of bits); the sum of the values b has at the start of the rounds in which the
exponent bit was 1 (a sum over one branch).

Example (level 2):

```
u = 1
a = 182
val = 31
d = 217
j = 0
while val > 0 and j < 4:
    if val % 2 == 1:
        u = u * a % d
    a = a * a % d
    val = val // 2
    j += 1
print(u)
```

answer: `154`

### `C1.fib_shapes_recursive` (supersedes C1.recursive_calls; family accumulators)

The two fib-like recursive shapes of the old ``recursive_calls``: two-branch (f(n-1), f(n-2) with small multipliers) and three-branch
(n-1, n-2, n-3). Parameters widened (multipliers 1-5, offsets 0-9, base values 0-9, argument up to +2) after the capacity count showed about 1,570 programs per level. Per ruling R-2 and the audit (B6) these are shapes of the ``fib_like`` cluster (a linear recurrence), written recursively,
and carry that cluster in ``lineages_c1_clusters``. Family: accumulators, as fib_like.

Example (level 2):

```
def f(j):
    if j < 2:
        return j + 8
    else:
        return f(j - 1) * 3 + f(j - 2) * 4 + 4
print(f(6))
```

answer: `15023`

### `C1.insertion_sort_traced` (PROPOSED additional shapes; family swaps)

PROPOSED shapes of insertion sort (same program as ``insertion_sort``, K rounds, ascending or descending, strict or not): the value of the
hole index j after the inner while loop of the LAST round run; the sum, over the rounds run, of the hole index j after the inner loop (a sum of an intermediate variable).

Example (level 2):

```
m = [3, 18, 15, 16, 1, 1]
for s in range(1, 4):
    k = m[s]
    z = s - 1
    while z >= 0 and m[z] > k:
        m[z + 1] = m[z]
        z = z - 1
    m[z + 1] = k
print(z)
```

answer: `1`

### `C1.kadane_scan_traced` (PROPOSED additional shapes; family minmax)

PROPOSED shapes of the maximum-subarray scan (as ``kadane_scan``): the value of cur after the first p elements (the loop stops at the
stated p, 3 <= p < n); the sum of the indices i at which cur was negative before the step (the restart branch ran).

Example (level 2):

```
z = [2, 9, 2, 9, 5, 3, 2, (-5), 2, 8]
v = z[0]
a = v
for acc in range(1, 9):
    v = max(v + z[acc], z[acc])
    a = max(a, v)
print(v)
```

answer: `29`

### `C1.majority_vote_scan_r2` (supersedes C1.majority_vote_scan; family minmax)

As ``majority_vote_scan`` (Boyer-Moore pairing scan; shapes: the final candidate; 'candidate count'; the number of times a new candidate
was taken) WITHOUT the old redraws (final candidate neither first nor last element, mode 25 %). Those redraws were conditioned on two
heuristics' outcomes (ruling R-1) and moved the tell to the elements next to the last: the audit battery's literal-position rules reached
0.85 inside the candidate shape at level 4. Items are now drawn as they come, and the candidate-alone shape is dropped (NOT REGISTERED, see
``NOT_REGISTERED``: the final candidate is the last element in about 0.75-0.79 of its cell, inherent to the pairing scan). Shapes: 'candidate
count' and the sum of the candidates taken (the value of every new candidate, added when it is taken). The list has 6 + 2 * level values from 1 to 6.

Example (level 2):

```
k = [1, 1, 2, 3, 3, 2, 1, 2, 3, 3]
x = 0
c = 0
q = 0
for m in range(10):
    if c == 0:
        x = k[m]
        c = 1
        q += x
    elif k[m] == x:
        c += 1
    else:
        c -= 1
print(q)
```

answer: `8`

### `C1.merge_two_sorted_r2` (supersedes C1.merge_two_sorted; family lists)

As ``merge_two_sorted`` (comparison loop of a two-pointer merge; values repeat across the lists, ties matter) with TWO shapes dropped
(NOT REGISTERED, see ``NOT_REGISTERED``): the partial output list (it is sorted(a + b) minus the leftover) and the comparison count
(len(a) + len(b) - 1 hits 0.50-0.57 of its cell at every level). The one shape kept: the number of times the source list changed.

Example (level 2):

```
a = [3, 4, 5, 6, 9, 11]
best = [2, 4, 7, 7, 9, 9]
n = 0
out = 0
w = []
y = 0
k = (-1)
while n < len(a) and out < len(best):
    if a[n] < best[out]:
        if k != 0:
            y += 1
            k = 0
        w.append(a[n])
        n += 1
    else:
        if k != 1:
            y += 1
            k = 1
        w.append(best[out])
        out += 1
print(y)
```

answer: `5`

### `C1.recursive_calls_r2` (supersedes C1.recursive_calls; family functions)

Recursive definitions that are NOT the fib-like recurrences (those two shapes, 'two' and 'tri', moved to ``fib_shapes_recursive`` in the
fib_like cluster). Shapes: halving split f(n // 2) and f(n - n // 2) with random multipliers plus n % m; index recursion over a list literal
(skip or add by a parity or divisibility test); mutual recursion of two functions with random multipliers and offsets. Parameters are widened
(multipliers 1-4, offsets 0-6, moduli 2-5, base values) so each shape has far more than a few hundred distinct programs per level.

Example (level 2):

```
def step(best, k):
    if k >= len(best):
        return 0
    elif best[k] % 2 == 1:
        return best[k] + step(best, k + 1)
    else:
        return 5 * step(best, k + 1) - 2
print(step([4, 9, 2, 6, 9, 1, 3, 9], 0))
```

answer: `2733`

### `C1.sieve_marking_r2` (supersedes C1.sieve_marking; family lists)

As ``sieve_marking`` (sieve marking pass over a literal 0/1 flag list with a stated start rule) with the count shape dropped (NOT
REGISTERED, see ``NOT_REGISTERED``). Shapes: the sum of the indices that remain 1, the sum of the indices struck (every strike write counts, re-strikes too; replaces the old count
of strike writes, whose answers were concentrated on a few small values).
10 to 38 flags.

Example (level 2):

```
r = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1]
j = 0
for p in range(2, 17):
    if r[p] == 1:
        cur = 3 * p
        while cur < 17:
            j += cur
            r[cur] = 0
            cur += p
print(j)
```

answer: `145`

### `C1.turtle_walk_r2` (supersedes C1.turtle_walk; family simulation)

Walker with position (x, y) and heading d in 0..3 reading a LIST of integer commands: 1, 2 or 3 move forward that many cells in the
current heading; 4 turns one way; 5 turns the other way; 6 (from level 3) moves one cell backward. What each heading means and which turn adds
what is written in the code. Compared with ``turtle_walk`` (letters F, L, R, B, where the number of F commands equalled the distance
in about 0.8 of the distance shapes) the step lengths vary and turns are as frequent as steps, so no count of commands gives a coordinate, and the
distance shapes are dropped (NOT REGISTERED, see ``NOT_REGISTERED``). Shapes: the final position written 'x,y'; the final x; the final y; the
sum of the forward steps made while the heading was 2 or 3 (traced through the heading).

Example (level 2):

```
val = [5, 5, 2, 1, 3, 5, 4, 2, 5, 2]
s = 0
w = 0
c = 2
for out in range(len(val)):
    m = val[out]
    if m <= 3:
        if c == 0:
            w += m
        elif c == 1:
            s += m
        elif c == 2:
            w -= m
        else:
            s -= m
    elif m == 4:
        c = (c + 1) % 4
    elif m == 5:
        c = (c + 3) % 4
    elif m == 6:
        if c == 0:
            w -= 1
        elif c == 1:
            s -= 1
        elif c == 2:
            w += 1
        else:
            s += 1
print(s)
```

answer: `-2`

## NOT REGISTERED shapes (tell cannot be removed by construction)

- `C1.majority_vote_scan[cand shape]`: the final candidate equals the LAST element in 0.75-0.79 of the shape (battery num[-k] rule, levels 1-5) once the old redraws are gone; it is inherent to the pairing scan (whenever the count is 0 before the last element the last element becomes the candidate); the old redraws that hid it were conditional on heuristic outcomes (R-1) and moved the tell to the elements next to the last
- `C1.merge_two_sorted[cmp shape]`: the comparison count is len(a) + len(b) minus the leftover, and the leftover is usually one element: 'len(a) + len(b) - 1' hits 0.50-0.57 of the shape at levels 1, 3 and 5 (battery R.len_a+len_b-1); the leftover cannot be hidden by construction
- `C1.merge_two_sorted[out shape]`: the partial output list is sorted(a + b) without the leftover; 'sorted all but last' hits 0.50-0.52 of that shape (audit R.sorted_all_but_last); the leftover cannot be hidden by construction
- `C1.sieve_marking[count shape]`: the count of flags still 1 after striking is, in 36-48 % of the shape, the count of ones at indices 0, 1 and at primes (audit R.ones_minus_strikes_naive); with an all-ones start it would be a prime-count lookup
- `C1.turtle_walk[far shape]`: same reason as the manhattan shape (audit count_F 0.81 in the shape at level 1)
- `C1.turtle_walk[manhattan shape]`: distance equals the number of F commands whenever the path does not double back (audit count_F 0.79 in the shape at level 1); turns do not remove it by construction at short lengths
