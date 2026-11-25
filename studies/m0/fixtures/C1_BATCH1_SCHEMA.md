# C1 batch 1: structured-form schema for the second-solver agent

Written by the implementer (Sonnet 5.5) for a separate second-solver and audit context (ADR-0033 section 6.2). Not a result; nothing here approves anything. Own checks only: not independent review, not Astra validation, not human approval.

## What is checked and how

- Item: `question` (the rendered program and the sentence 'What exactly does it print? It prints a single line.'), `structured = {"program": <tree>}`, `answer` = the key. `answer_type` is `line`, `k` is null (open answer, scored by string comparison after the registered normalisation, which lower-cases; generators redraw any program whose output is not already lower-case, trimmed, single-spaced, non-empty and not ending in a full stop).
- The key is what the locked interpreter prints: `c1grammar.run_isolated` runs the rendered source in a fresh restricted process (`python -I -S`, builtins len, sum, max, min, abs, range, sorted, str and a collecting print only, 2 s per program, CPU rlimit); the gate runs it twice. The existing independent second solver is the tree walker `solvers_c1.c1_trace(structured)`; it never calls exec, eval or compile and runs each function in its own scope (parameters and locals only). These batch lineages are NOT yet in `solvers_c1.SOLVERS`; the same walker serves them (`SOLVERS["C1.<name>"] = c1_trace`) once registered.
- A separate solver agent may re-derive each key from `structured` (or from the question text) without the generator code. Fixtures: `studies/m0/fixtures/c1_batch1/<lineage id>.jsonl`, 20 distinct items for each of the 7 levels (0 and 6 are the reserve levels), keys `id, lineage, level, question, structured, answer, answer_type, k`. Agreement on all fixtures is necessary, not sufficient.

## Conventions the answer depends on (all fixed by Python 3 and stated by the program itself)

- Integer `//` and `%` floor toward minus infinity; negative literals are rendered in parentheses, `(-1)`.
- `print` of an int is its decimal form; of a list is `[1, 2, 3]` with `, ` separators; of a string inside a list uses single quotes; a string prints bare. `str(n)` is decimal. `max` and `min` accept two or more arguments or one list.
- Lists are objects: `b = a` makes two names for one list, `a[:]` and `a + [x]` make new lists; a function that assigns to an element of its list parameter changes the caller's list, one that rebinds the parameter does not (C1.shared_lists is about exactly this). `aug` on a list is never used (`xs += ys` mutates in Python but the tree walker would rebind).
- `and` and `or` short-circuit (the insertion sort and the stack matcher rely on `j >= 0 and xs[j] > key`).
- There is no `break`: loops end by their tests. Every loop is bounded; the runner kills a program after 2 s.
- A function is defined before it is called; recursion is used only by C1.recursive_calls, with at most about 12 nested calls.

## Tree grammar (from `studies/m0/c1grammar.py`)

```
Expression nodes:  ["n", int] ["s", str] ["v", name] ["b", op, l, r] (+ - * // %) ["c", op, l, r] (< <= > >= == !=)
                   ["and", l, r] ["or", l, r] ["not", e] ["list", e...] ["idx", e, i] ["slice", e, a|None, b|None, c|None]
                   ["call", fname, args...] ["m", obj, method, args...]
Statement nodes:   ["set", name, e] ["aug", name, op, e] ["setidx", name, i, e] ["append", name, e]
                   ["for", var, start, stop, step(int), body] ["while", cond, body] ["if", cond, then, else] ["def", name, params, body]
                   ["ret", e] ["print", e]
```

## Lineages (family, strict procedure, builder description)

### `C1.bfs_queue` (family graphs; strict confidence: clear)

Procedure: breadth-first search with an array queue, head and tail pointers and a distance list.

Breadth-first search from a start node over adjacency lists (the neighbour order inside each list is as written), with dist = -1 for
unseen nodes and a queue array with head and tail pointers. About one edge in four is one-way. Shapes: the distance of a target node
(always reached, so never -1), the order in which nodes were enqueued, the sum of the distances of the nodes taken off the queue, the
node enqueued last. 5 + level nodes.

Example (level 2):

```
y = [[3, 1], [2, 3, 0], [1, 4, 5], [0, 1, 6], [2, 5], [4], [3]]
best = [(-1), (-1), (-1), (-1), (-1), (-1), (-1)]
w = [0, 0, 0, 0, 0, 0, 0]
w[0] = 0
best[0] = 0
res = 0
z = 1
while res < z:
    m = w[res]
    res += 1
    u = y[m]
    for out in range(len(u)):
        x = u[out]
        if best[x] == (-1):
            best[x] = best[m] + 1
            w[z] = x
            z += 1
print(w[0:z])
```

structured (tree): `{"program": [["set", "y", ["list", ["list", ["n", 3], ["n", 1]], ["list", ["n", 2], ["n", 3], ["n", 0]], ["list", ["n", 1], ["n", 4], ["n", 5]], ["list", ["n", 0], ["n", 1], ["n", 6]], ["list", ["n", 2], ["n", 5]], ["list", ["n", 4]], ["list", ["n", 3]]]], ["set", "best", ["list", ["n", -1], ["n", -1], ["n", -1], ["n", -1], ["n", -1], ["n", -1], ["n", -1]]], ["set", "w", ["list", ["n", 0], ["n", 0], ["n", 0], ["n", 0], ["n", 0], ["n", 0], ["n", 0]]], ["setidx", "w", ["n", 0], ["n", 0]], ["setidx", "best", ["n", 0], ["n", 0]], ["set", "res", ["n", 0]], ["set", "z", ["n", 1]], ["while", ["c", "<...`

answer: `[0, 3, 1, 6, 2, 4, 5]`

### `C1.binary_search` (family lists; strict confidence: clear)

Procedure: halve a sorted-list interval around a midpoint probe until found or empty.

Binary search on a sorted list of distinct integers, in one of two stated styles: closed interval (lo <= hi, stop when found) or
half-open lower bound (lo < hi, hi = mid). Shapes: the sum of the probed values, the index probed last, the string of moves made (one
letter per probe: l when the probe was below the target and lo moved up, r when it was above and hi moved down, h when it hit the
target). The target is in the list about half the time. The list has 5 to 45 entries.

Example (level 2):

```
c = [3, 9, 19, 22, 26, 27, 29, 30, 34, 35]
y = 19
val = 0
cur = len(c)
j = 0
while val < cur:
    p = (val + cur) // 2
    j = p
    if c[p] < y:
        val = p + 1
    else:
        cur = p
print(j)
```

structured (tree): `{"program": [["set", "c", ["list", ["n", 3], ["n", 9], ["n", 19], ["n", 22], ["n", 26], ["n", 27], ["n", 29], ["n", 30], ["n", 34], ["n", 35]]], ["set", "y", ["n", 19]], ["set", "val", ["n", 0]], ["set", "cur", ["call", "len", ["v", "c"]]], ["set", "j", ["n", 0]], ["while", ["c", "<", ["v", "val"], ["v", "cur"]], [["set", "p", ["b", "//", ["b", "+", ["v", "val"], ["v", "cur"]], ["n", 2]]], ["set", "j", ["v", "p"]], ["if", ["c", "<", ["idx", ["v", "c"], ["v", "p"]], ["v", "y"]], [["set", "val", ["b", "+", ["v", "p"], ["n", 1]]]], [["set", "cur", ["v", "p"]]]]]], ["print", ["v", "j"]]]}`

answer: `1`

### `C1.bracket_matching` (family stacks; strict confidence: borderline)

Procedure: stack (array plus top pointer) of open brackets matched against each closing bracket.

Two kinds of brackets, "()" and "[]". Open brackets are pushed (1 for round, 2 for square); a closing bracket pops when the top has its
kind, otherwise it counts as an error and the stack is left alone. Shapes: the errors and the final height written as one number (10 * errors + height), the final
stack height, the index of the first error. A draw whose answer would be 0 (no error, nothing left open) or -1 is redrawn. The string has 6, 7, 9, 12, 15, 18 or 21 characters, drawn as a random walk that mostly closes what is open
but sometimes closes the wrong kind or closes an empty stack.

Example (level 2):

```
t = '[]()((())'
s = []
for out in range(len(t)):
    s.append(0)
val = 0
e = 0
for out in range(len(t)):
    b = t[out]
    if b == '(':
        s[val] = 1
        val += 1
    elif b == '[':
        s[val] = 2
        val += 1
    elif b == ')':
        if val > 0 and s[val - 1] == 1:
            val -= 1
        else:
            e += 1
    elif val > 0 and s[val - 1] == 2:
        val -= 1
    else:
        e += 1
print(e * 10 + val)
```

structured (tree): `{"program": [["set", "t", ["s", "[]()((())"]], ["set", "s", ["list"]], ["for", "out", ["n", 0], ["call", "len", ["v", "t"]], 1, [["append", "s", ["n", 0]]]], ["set", "val", ["n", 0]], ["set", "e", ["n", 0]], ["for", "out", ["n", 0], ["call", "len", ["v", "t"]], 1, [["set", "b", ["idx", ["v", "t"], ["v", "out"]]], ["if", ["c", "==", ["v", "b"], ["s", "("]], [["setidx", "s", ["v", "val"], ["n", 1]], ["aug", "val", "+", ["n", 1]]], [["if", ["c", "==", ["v", "b"], ["s", "["]], [["setidx", "s", ["v", "val"], ["n", 2]], ["aug", "val", "+", ["n", 1]]], [["if", ["c", "==", ["v", "b"], ["s", ")"]], [["...`

answer: `1`

### `C1.bytecode_loop` (family simulation; strict confidence: clear)

Procedure: fetch-decode-execute loop over (opcode, argument) pairs with an accumulator, a register and a skip.

A tiny machine: code is a flat list of (opcode, argument) pairs; a program counter fetches a pair, advances by two, then acts on the
accumulator acc and register reg, the opcode numbers being a random assignment written in the code. Ops: add arg; multiply by arg;
subtract arg (from level 0); skip the next pair if acc > arg (from level 1); acc = acc % arg (from level 2); reg = acc, acc = acc + reg
(from level 3). Shapes: final acc, the sum of the arguments of the pairs executed (a skipped pair does not count; from level 1), final reg (from level 3,
kept only when it is not 0). 4 to 12 pairs.

Example (level 2):

```
res = [4, 3, 1, 30, 4, 4, 1, 23, 2, 7, 6, 4]
x = 0
s = 0
j = 0
while x < len(res):
    t = res[x]
    a = res[x + 1]
    x = x + 2
    j += a
    if t == 4:
        s = s + a
    elif t == 9:
        s = s * a
    elif t == 2:
        s = s - a
    elif t == 1:
        if s > a:
            x = x + 2
    elif t == 6:
        s = s % a
print(j)
```

structured (tree): `{"program": [["set", "res", ["list", ["n", 4], ["n", 3], ["n", 1], ["n", 30], ["n", 4], ["n", 4], ["n", 1], ["n", 23], ["n", 2], ["n", 7], ["n", 6], ["n", 4]]], ["set", "x", ["n", 0]], ["set", "s", ["n", 0]], ["set", "j", ["n", 0]], ["while", ["c", "<", ["v", "x"], ["call", "len", ["v", "res"]]], [["set", "t", ["idx", ["v", "res"], ["v", "x"]]], ["set", "a", ["idx", ["v", "res"], ["b", "+", ["v", "x"], ["n", 1]]]], ["set", "x", ["b", "+", ["v", "x"], ["n", 2]]], ["aug", "j", "+", ["v", "a"]], ["if", ["c", "==", ["v", "t"], ["n", 4]], [["set", "s", ["b", "+", ["v", "s"], ["v", "a"]]]], [["if", ...`

answer: `71`

### `C1.cellular_update` (family simulation; strict confidence: clear)

Procedure: synchronous one-dimensional automaton update from an eight-entry rule table into a fresh row.

One-dimensional cellular automaton on a ring: the new cell is rule[4 * left + 2 * centre + right], the neighbours wrapping around, the
whole new row built in a fresh list before it replaces the old one. The eight-entry rule table is random (never all equal) and shown in
the program. Shapes after G generations: the row, the sum over cells of (index times cell value). 5 + level cells, G from 1 to 5.

Example (level 2):

```
u = [0, 0, 1, 0, 0, 0, 0]
acc = [0, 1, 1, 1, 0, 0, 1, 0]
for z in range(3):
    t = []
    for val in range(7):
        t.append(acc[u[(val + 6) % 7] * 4 + u[val] * 2 + u[(val + 1) % 7]])
    u = t
print(u)
```

structured (tree): `{"program": [["set", "u", ["list", ["n", 0], ["n", 0], ["n", 1], ["n", 0], ["n", 0], ["n", 0], ["n", 0]]], ["set", "acc", ["list", ["n", 0], ["n", 1], ["n", 1], ["n", 1], ["n", 0], ["n", 0], ["n", 1], ["n", 0]]], ["for", "z", ["n", 0], ["n", 3], 1, [["set", "t", ["list"]], ["for", "val", ["n", 0], ["n", 7], 1, [["append", "t", ["idx", ["v", "acc"], ["b", "+", ["b", "+", ["b", "*", ["idx", ["v", "u"], ["b", "%", ["b", "+", ["v", "val"], ["n", 6]], ["n", 7]]], ["n", 4]], ["b", "*", ["idx", ["v", "u"], ["v", "val"]], ["n", 2]]], ["idx", ["v", "u"], ["b", "%", ["b", "+", ["v", "val"], ["n", 1]], [...`

answer: `[1, 0, 1, 0, 0, 0, 1]`

### `C1.circle_elimination` (family simulation; strict confidence: clear)

Procedure: Josephus counting: advance K live flags around a ring and strike the flag reached.

A circle of n flags (1 live, 0 already out). pos starts at n - 1; each round moves pos forward K live flags (counting only live ones,
wrapping) and strikes the flag it lands on. Shapes after R rounds: the index struck last, the sum of the indices struck, the index of the
only live flag after all but one are struck. n = 9 + level; K from 2 to 5; some flags start out.

Example (level 2):

```
y = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
count = 10
for p in range(7):
    t = 0
    while t < 2:
        count = (count + 1) % 11
        if y[count] == 1:
            t += 1
    y[count] = 0
print(count)
```

structured (tree): `{"program": [["set", "y", ["list", ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1]]], ["set", "count", ["n", 10]], ["for", "p", ["n", 0], ["n", 7], 1, [["set", "t", ["n", 0]], ["while", ["c", "<", ["v", "t"], ["n", 2]], [["set", "count", ["b", "%", ["b", "+", ["v", "count"], ["n", 1]], ["n", 11]]], ["if", ["c", "==", ["idx", ["v", "y"], ["v", "count"]], ["n", 1]], [["aug", "t", "+", ["n", 1]]], []]]], ["setidx", "y", ["v", "count"], ["n", 0]]]], ["print", ["v", "count"]]]}`

answer: `4`

### `C1.coin_change_table` (family tables; strict confidence: borderline)

Procedure: one-dimensional table over amounts updated from smaller amounts, coin by coin (ways, ordered ways, fewest coins).

Coin table over amounts 0..T: with coins processed one after another (outer loop over coins) ways[a] += ways[a - c] counts the
combinations; with amounts in the outer loop it counts ordered sequences (the code shows which); or best[a] = min(best[a], best[a - c] + 1)
gives the fewest coins. Shapes: ways[T], the fewest coins for T, the sum of the whole table. T = 8 + 3 * level + (0, 1 or 2), 2 to 4 coin values from 1 to 12.

Example (level 2):

```
w = [2, 5, 10]
out = [0]
for cur in range(16):
    out.append(99)
for a in range(len(w)):
    m = w[a]
    for cur in range(m, 17):
        out[cur] = min(out[cur], out[cur - m] + 1)
print(out[16])
```

structured (tree): `{"program": [["set", "w", ["list", ["n", 2], ["n", 5], ["n", 10]]], ["set", "out", ["list", ["n", 0]]], ["for", "cur", ["n", 0], ["n", 16], 1, [["append", "out", ["n", 99]]]], ["for", "a", ["n", 0], ["call", "len", ["v", "w"]], 1, [["set", "m", ["idx", ["v", "w"], ["v", "a"]]], ["for", "cur", ["v", "m"], ["n", 17], 1, [["setidx", "out", ["v", "cur"], ["call", "min", ["idx", ["v", "out"], ["v", "cur"]], ["b", "+", ["idx", ["v", "out"], ["b", "-", ["v", "cur"], ["v", "m"]]], ["n", 1]]]]]]]], ["print", ["idx", ["v", "out"], ["n", 16]]]]}`

answer: `4`

### `C1.digit_peel` (family while; strict confidence: borderline)

Procedure: digit extraction: n mod base, n // base, folded, until n is 0.

Digit extraction: repeat d = n % base, n = n // base until n is 0, folding the digits into one accumulator. Shapes: digit sum,
the digits read back in reverse order as a decimal number (leading zeros vanish; base below 10 only), the count of digits at or above a threshold, the sum
of the even digits. The base is 10 or a smaller base, the number is given in decimal.

Example (level 2):

```
cur = 16121
m = 0
while cur > 0:
    val = cur % 4
    m = m * 10 + val
    cur = cur // 4
print(m)
```

structured (tree): `{"program": [["set", "cur", ["n", 16121]], ["set", "m", ["n", 0]], ["while", ["c", ">", ["v", "cur"], ["n", 0]], [["set", "val", ["b", "%", ["v", "cur"], ["n", 4]]], ["set", "m", ["b", "+", ["b", "*", ["v", "m"], ["n", 10]], ["v", "val"]]], ["set", "cur", ["b", "//", ["v", "cur"], ["n", 4]]]]], ["print", ["v", "m"]]]}`

answer: `1233233`

### `C1.euclid_gcd` (family while; strict confidence: borderline)

Procedure: Euclid's algorithm, remainder form: (a, b) -> (b, a mod b) until b is 0.

Euclid's algorithm in the remainder form (a, b -> b, a % b until b is 0). Shapes: the value left in a, the sum of the quotients
a // b over the rounds, or the sum of the remainders. Input scale grows with the level (and so does the least number of rounds); the
pair is built from a chosen divisor so that the gcd is spread (not mostly 1) and, for the printed-gcd shape, is never one of the two
literals.

Example (level 2):

```
c = 28
k = 72
total = 0
while k != 0:
    total += c // k
    out = c % k
    c = k
    k = out
print(total)
```

structured (tree): `{"program": [["set", "c", ["n", 28]], ["set", "k", ["n", 72]], ["set", "total", ["n", 0]], ["while", ["c", "!=", ["v", "k"], ["n", 0]], [["aug", "total", "+", ["b", "//", ["v", "c"], ["v", "k"]]], ["set", "out", ["b", "%", ["v", "c"], ["v", "k"]]], ["set", "c", ["v", "k"]], ["set", "k", ["v", "out"]]]], ["print", ["v", "total"]]]}`

answer: `7`

### `C1.fast_power` (family while; strict confidence: borderline)

Procedure: square-and-multiply modular exponentiation over the binary digits of the exponent.

Modular exponentiation by repeated squaring: while e > 0: if e is odd, res = res * b % m; b = b * b % m; e = e // 2.
Shapes: the final result, the final value of b, the sum of the values b has when each round starts. The exponent has 2 + level bits.

Example (level 2):

```
best = 1
m = 2
out = 11
total = 14
while out > 0:
    if out % 2 == 1:
        best = best * m % total
    m = m * m % total
    out = out // 2
print(best)
```

structured (tree): `{"program": [["set", "best", ["n", 1]], ["set", "m", ["n", 2]], ["set", "out", ["n", 11]], ["set", "total", ["n", 14]], ["while", ["c", ">", ["v", "out"], ["n", 0]], [["if", ["c", "==", ["b", "%", ["v", "out"], ["n", 2]], ["n", 1]], [["set", "best", ["b", "%", ["b", "*", ["v", "best"], ["v", "m"]], ["v", "total"]]]], []], ["set", "m", ["b", "%", ["b", "*", ["v", "m"], ["v", "m"]], ["v", "total"]]], ["set", "out", ["b", "//", ["v", "out"], ["n", 2]]]]], ["print", ["v", "best"]]]}`

answer: `4`

### `C1.grid_path_table` (family tables; strict confidence: borderline)

Procedure: row-wise table of best (largest, least, or count) right-and-down paths over a grid.

Best value of a path from the top-left to the bottom-right cell moving only right or down, kept in one row that is updated cell by cell.
Shapes: the greatest path sum, the least path sum (values 1 to 9), or the number of paths avoiding blocked cells (cells marked 0).
Grids are 2x3, 3x3, 3x4, 4x4, 4x5, 5x5, 5x6 for levels 0 to 6; a path-count answer of 0 is redrawn.

Example (level 2):

```
acc = [[6, 5, 1, 7], [8, 7, 2, 5], [2, 3, 2, 9]]
k = []
for res in range(4):
    k.append(0)
for total in range(3):
    for res in range(4):
        count = acc[total][res]
        if total == 0 and res == 0:
            k[res] = count
        elif total == 0:
            k[res] = k[res - 1] + count
        elif res == 0:
            k[res] = k[res] + count
        else:
            k[res] = min(k[res], k[res - 1]) + count
print(k[3])
```

structured (tree): `{"program": [["set", "acc", ["list", ["list", ["n", 6], ["n", 5], ["n", 1], ["n", 7]], ["list", ["n", 8], ["n", 7], ["n", 2], ["n", 5]], ["list", ["n", 2], ["n", 3], ["n", 2], ["n", 9]]]], ["set", "k", ["list"]], ["for", "res", ["n", 0], ["n", 4], 1, [["append", "k", ["n", 0]]]], ["for", "total", ["n", 0], ["n", 3], 1, [["for", "res", ["n", 0], ["n", 4], 1, [["set", "count", ["idx", ["idx", ["v", "acc"], ["v", "total"]], ["v", "res"]]], ["if", ["and", ["c", "==", ["v", "total"], ["n", 0]], ["c", "==", ["v", "res"], ["n", 0]]], [["setidx", "k", ["v", "res"], ["v", "count"]]], [["if", ["c", "=="...`

answer: `25`

### `C1.insertion_sort` (family swaps; strict confidence: borderline)

Procedure: insertion: shift larger elements of the sorted prefix right to open a hole for the next element.

Insertion sort run for the first K outer rounds (K is the whole list about one time in five): key = xs[i]; shift every larger
element of xs[0..i-1] one place right; drop key in the hole. The order is ascending (test '>') or descending (test '<'), and the test is
strict or not (stated in the code). Shapes: the list afterwards, the number of shifts made, the element at one index afterwards.
The list has 4 + level entries with repeated values.

Example (level 2):

```
y = [10, 18, 1, 10, 16, 11]
for u in range(1, 3):
    p = y[u]
    x = u - 1
    while x >= 0 and y[x] < p:
        y[x + 1] = y[x]
        x = x - 1
    y[x + 1] = p
print(y[3])
```

structured (tree): `{"program": [["set", "y", ["list", ["n", 10], ["n", 18], ["n", 1], ["n", 10], ["n", 16], ["n", 11]]], ["for", "u", ["n", 1], ["n", 3], 1, [["set", "p", ["idx", ["v", "y"], ["v", "u"]]], ["set", "x", ["b", "-", ["v", "u"], ["n", 1]]], ["while", ["and", ["c", ">=", ["v", "x"], ["n", 0]], ["c", "<", ["idx", ["v", "y"], ["v", "x"]], ["v", "p"]]], [["setidx", "y", ["b", "+", ["v", "x"], ["n", 1]], ["idx", ["v", "y"], ["v", "x"]]], ["set", "x", ["b", "-", ["v", "x"], ["n", 1]]]]], ["setidx", "y", ["b", "+", ["v", "x"], ["n", 1]], ["v", "p"]]]], ["print", ["idx", ["v", "y"], ["n", 3]]]]}`

answer: `10`

### `C1.kadane_scan` (family minmax; strict confidence: clear)

Procedure: maximum-subarray scan: cur = max(cur + x, x), best = max(best, cur).

Maximum-subarray scan: cur = max(cur + x, x) and best = max(best, cur) over the list from its second element (cur and best start at
xs[0]). Shapes: best, the final cur, the sum of the values cur has after each step. The list has 5 + 2 *
level entries; about 40 percent of them are negative, so neither the largest element nor the sum of the positives is the answer.

Example (level 2):

```
j = [5, (-3), 5, (-2), 2, (-7), 6, 4, 3]
z = j[0]
out = z
k = 0
for best in range(1, 9):
    z = max(z + j[best], j[best])
    out = max(out, z)
    k += z
print(k)
```

structured (tree): `{"program": [["set", "j", ["list", ["n", 5], ["n", -3], ["n", 5], ["n", -2], ["n", 2], ["n", -7], ["n", 6], ["n", 4], ["n", 3]]], ["set", "z", ["idx", ["v", "j"], ["n", 0]]], ["set", "out", ["v", "z"]], ["set", "k", ["n", 0]], ["for", "best", ["n", 1], ["n", 9], 1, [["set", "z", ["call", "max", ["b", "+", ["v", "z"], ["idx", ["v", "j"], ["v", "best"]]], ["idx", ["v", "j"], ["v", "best"]]]], ["set", "out", ["call", "max", ["v", "out"], ["v", "z"]]], ["aug", "k", "+", ["v", "z"]]]], ["print", ["v", "k"]]]}`

answer: `50`

### `C1.majority_vote_scan` (family minmax; strict confidence: clear)

Procedure: Boyer-Moore pairing scan: a candidate with a count that cancels against different values.

Boyer-Moore pairing scan: if cnt == 0 take the element as candidate with cnt 1; else cnt += 1 on an equal element and cnt -= 1 on a
different one. Shapes: the final candidate; the candidate and the count written together as 'candidate count'; the number of times a new
candidate was taken. The list (6 + 2 * level values from 1 to 6) is drawn so that the final candidate is neither the first nor the last
element and is the most frequent value in only about a quarter of the items, so 'answer the mode' or 'answer the last value' is not a
shortcut.

Example (level 2):

```
n = [2, 3, 5, 5, 5, 3, 4, 5, 3, 1]
res = 0
x = 0
for e in range(10):
    if x == 0:
        res = n[e]
        x = 1
    elif n[e] == res:
        x += 1
    else:
        x -= 1
print(str(res) + ' ' + str(x))
```

structured (tree): `{"program": [["set", "n", ["list", ["n", 2], ["n", 3], ["n", 5], ["n", 5], ["n", 5], ["n", 3], ["n", 4], ["n", 5], ["n", 3], ["n", 1]]], ["set", "res", ["n", 0]], ["set", "x", ["n", 0]], ["for", "e", ["n", 0], ["n", 10], 1, [["if", ["c", "==", ["v", "x"], ["n", 0]], [["set", "res", ["idx", ["v", "n"], ["v", "e"]]], ["set", "x", ["n", 1]]], [["if", ["c", "==", ["idx", ["v", "n"], ["v", "e"]], ["v", "res"]], [["aug", "x", "+", ["n", 1]]], [["aug", "x", "-", ["n", 1]]]]]]]], ["print", ["b", "+", ["b", "+", ["call", "str", ["v", "res"]], ["s", " "]], ["call", "str", ["v", "x"]]]]]}`

answer: `5 0`

### `C1.merge_two_sorted` (family lists; strict confidence: clear)

Procedure: two-pointer merge of two sorted lists, always moving the smaller front element.

The comparison loop of merging two sorted lists with two read positions: while both lists have a next element, move the smaller (the
left one when equal, or when 'strictly less' is the stated test, the right one) to the output. Shapes: the number of comparisons, the
output list built so far when one list runs out (the leftover is NOT appended), the number of times the source list changed. Values
repeat across the two lists, so ties matter.

Example (level 2):

```
p = [6, 9, 10, 11, 11, 11]
cur = [1, 2, 4, 5, 10]
j = 0
v = 0
out = []
res = 0
y = (-1)
while j < len(p) and v < len(cur):
    if p[j] < cur[v]:
        if y != 0:
            res += 1
            y = 0
        out.append(p[j])
        j += 1
    else:
        if y != 1:
            res += 1
            y = 1
        out.append(cur[v])
        v += 1
print(res)
```

structured (tree): `{"program": [["set", "p", ["list", ["n", 6], ["n", 9], ["n", 10], ["n", 11], ["n", 11], ["n", 11]]], ["set", "cur", ["list", ["n", 1], ["n", 2], ["n", 4], ["n", 5], ["n", 10]]], ["set", "j", ["n", 0]], ["set", "v", ["n", 0]], ["set", "out", ["list"]], ["set", "res", ["n", 0]], ["set", "y", ["n", -1]], ["while", ["and", ["c", "<", ["v", "j"], ["call", "len", ["v", "p"]]], ["c", "<", ["v", "v"], ["call", "len", ["v", "cur"]]]], [["if", ["c", "<", ["idx", ["v", "p"], ["v", "j"]], ["idx", ["v", "cur"], ["v", "v"]]], [["if", ["c", "!=", ["v", "y"], ["n", 0]], [["aug", "res", "+", ["n", 1]], ["set",...`

answer: `3`

### `C1.mirror_pointers` (family strings; strict confidence: borderline)

Procedure: two pointers walking inward from both ends of a string, comparing the pair they stand on.

Two pointers: i = 0, j = len(s) - 1; while i < j compare s[i] with s[j], then i += 1 and j -= 1. Shapes: the left characters of the
unequal pairs in order, the sum of the left indices of the unequal pairs, both characters of every unequal pair in order (a draw with no
unequal pair is redrawn). The string has 4 + 2 * level characters over three letters and is a palindrome with each pair broken at random,
so the answer is not 'is it a palindrome'.

Example (level 2):

```
u = 'mbmzzbmm'
t = 0
z = len(u) - 1
w = 0
while t < z:
    if u[t] != u[z]:
        w += t
    t += 1
    z -= 1
print(w)
```

structured (tree): `{"program": [["set", "u", ["s", "mbmzzbmm"]], ["set", "t", ["n", 0]], ["set", "z", ["b", "-", ["call", "len", ["v", "u"]], ["n", 1]]], ["set", "w", ["n", 0]], ["while", ["c", "<", ["v", "t"], ["v", "z"]], [["if", ["c", "!=", ["idx", ["v", "u"], ["v", "t"]], ["idx", ["v", "u"], ["v", "z"]]], [["aug", "w", "+", ["v", "t"]]], []], ["aug", "t", "+", ["n", 1]], ["aug", "z", "-", ["n", 1]]]], ["print", ["v", "w"]]]}`

answer: `3`

### `C1.partition_pass` (family swaps; strict confidence: borderline)

Procedure: Lomuto partition: sweep with a boundary index, swap elements not above the pivot behind it, pivot placed last.

Lomuto partition around the last element of the first m entries (the pivot): i = -1; for j over the entries before the pivot, when
xs[j] <= pivot (or < pivot, as the code states) do i += 1 and swap xs[i] with xs[j]; finally swap xs[i + 1] with the pivot. Shapes: the list
afterwards, the sum of the positions j at which a swap was made inside the loop. The final position of the pivot is never asked (it is a
count), and a draw whose list comes out unchanged is redrawn. 5 + level entries, m = the whole list or the first m_ >= 4.

Example (level 2):

```
z = [10, 14, 1, 7, 20, 18, 17]
u = z[6]
c = (-1)
for total in range(6):
    if z[total] < u:
        c += 1
        m = z[c]
        z[c] = z[total]
        z[total] = m
m = z[c + 1]
z[c + 1] = u
z[6] = m
print(z)
```

structured (tree): `{"program": [["set", "z", ["list", ["n", 10], ["n", 14], ["n", 1], ["n", 7], ["n", 20], ["n", 18], ["n", 17]]], ["set", "u", ["idx", ["v", "z"], ["n", 6]]], ["set", "c", ["n", -1]], ["for", "total", ["n", 0], ["n", 6], 1, [["if", ["c", "<", ["idx", ["v", "z"], ["v", "total"]], ["v", "u"]], [["aug", "c", "+", ["n", 1]], ["set", "m", ["idx", ["v", "z"], ["v", "c"]]], ["setidx", "z", ["v", "c"], ["idx", ["v", "z"], ["v", "total"]]], ["setidx", "z", ["v", "total"], ["v", "m"]]], []]]], ["set", "m", ["idx", ["v", "z"], ["b", "+", ["v", "c"], ["n", 1]]]], ["setidx", "z", ["b", "+", ["v", "c"], ["n",...`

answer: `[10, 14, 1, 7, 17, 18, 20]`

### `C1.postfix_evaluation` (family stacks; strict confidence: borderline)

Procedure: reverse-Polish evaluation: push operands, replace the top two by the operator's result.

Reverse Polish evaluation over a list of ints: a token >= 0 is pushed; a negative token pops two values x (below) and y (top) and
pushes x + y, x - y or x * y, the code of each operator being fixed by a random assignment shown in the program. Shapes: the final top,
the sum of the values the operators wrote back. 3 + level operands (1 to 9).

Example (level 2):

```
m = [3, 4, (-2), 2, (-1), 9, 4, (-2), (-2)]
e = []
for v in range(len(m)):
    e.append(0)
k = 0
for v in range(len(m)):
    y = m[v]
    if y >= 0:
        e[k] = y
        k += 1
    else:
        z = e[k - 1]
        x = e[k - 2]
        k -= 1
        if y == (-2):
            e[k - 1] = x + z
        elif y == (-3):
            e[k - 1] = x - z
        else:
            e[k - 1] = x * z
print(e[k - 1])
```

structured (tree): `{"program": [["set", "m", ["list", ["n", 3], ["n", 4], ["n", -2], ["n", 2], ["n", -1], ["n", 9], ["n", 4], ["n", -2], ["n", -2]]], ["set", "e", ["list"]], ["for", "v", ["n", 0], ["call", "len", ["v", "m"]], 1, [["append", "e", ["n", 0]]]], ["set", "k", ["n", 0]], ["for", "v", ["n", 0], ["call", "len", ["v", "m"]], 1, [["set", "y", ["idx", ["v", "m"], ["v", "v"]]], ["if", ["c", ">=", ["v", "y"], ["n", 0]], [["setidx", "e", ["v", "k"], ["v", "y"]], ["aug", "k", "+", ["n", 1]]], [["set", "z", ["idx", ["v", "e"], ["b", "-", ["v", "k"], ["n", 1]]]], ["set", "x", ["idx", ["v", "e"], ["b", "-", ["v",...`

answer: `27`

### `C1.recursive_calls` (family functions; strict confidence: clear)

Procedure: evaluate a recursive definition by expanding its call tree down to the base cases.

A recursive definition printed at one argument. Shapes of the recurrence (the code states base cases and every step): two-branch
(f(n-1) and f(n-2) with small multipliers), three-branch (n-1, n-2, n-3), halving split (f(n // 2) and f(n - n // 2) plus n % 3),
index recursion over a list literal (skip or add the element, by parity), mutual recursion of two functions. The argument grows with
the level so that the call tree has roughly 5 to 150 calls.

Example (level 2):

```
def g(u):
    if u < 2:
        return u + 1
    else:
        return g(u - 1) * 3 + g(u - 2) * 3 + 4
print(g(5))
```

structured (tree): `{"program": [["def", "g", ["u"], [["if", ["c", "<", ["v", "u"], ["n", 2]], [["ret", ["b", "+", ["v", "u"], ["n", 1]]]], [["ret", ["b", "+", ["b", "+", ["b", "*", ["call", "g", ["b", "-", ["v", "u"], ["n", 1]]], ["n", 3]], ["b", "*", ["call", "g", ["b", "-", ["v", "u"], ["n", 2]]], ["n", 3]]], ["n", 4]]]]]]], ["print", ["call", "g", ["n", 5]]]]}`

answer: `721`

### `C1.run_length_scan` (family strings; strict confidence: clear)

Procedure: run-length encoding: compare each character with the current run, close the run on a change.

Run-length scan: cur = s[0], n = 1; for each next character: same as cur -> n += 1, else close the run (append cur + str(n) to the
output) and restart; the last run is closed after the loop. Shapes: the encoded string (every run), the encoded string keeping only runs
of length 2 or more (a draw with nothing kept is redrawn), only the run lengths written one after another. The string has 3 + level runs of length 1
to 3 + level // 2 over three letters, adjacent runs differing.

Example (level 2):

```
count = 'zznnnnznnnzz'
q = ''
c = count[0]
v = 1
for d in range(1, len(count)):
    if count[d] == c:
        v += 1
    else:
        q = q + str(v)
        c = count[d]
        v = 1
q = q + str(v)
print(q)
```

structured (tree): `{"program": [["set", "count", ["s", "zznnnnznnnzz"]], ["set", "q", ["s", ""]], ["set", "c", ["idx", ["v", "count"], ["n", 0]]], ["set", "v", ["n", 1]], ["for", "d", ["n", 1], ["call", "len", ["v", "count"]], 1, [["if", ["c", "==", ["idx", ["v", "count"], ["v", "d"]], ["v", "c"]], [["aug", "v", "+", ["n", 1]]], [["set", "q", ["b", "+", ["v", "q"], ["call", "str", ["v", "v"]]]], ["set", "c", ["idx", ["v", "count"], ["v", "d"]]], ["set", "v", ["n", 1]]]]]], ["set", "q", ["b", "+", ["v", "q"], ["call", "str", ["v", "v"]]]], ["print", ["v", "q"]]]}`

answer: `24132`

### `C1.shared_lists` (family references; strict confidence: clear)

Procedure: track which names share one list through assignment, copy, mutation and function calls.

Two or three list names, then 2 + level operations drawn from: ``b = a`` (same list), ``b = a[:]`` (copy), ``b = a + [v]`` (new list),
``b.append(v)``, ``b[i] = v``, ``b = bump(a, i, v)`` (a function that adds v to xs[i] IN the list it is given and returns that list), and
``b = grow(a, v)`` (a function that rebinds its parameter to xs + [v] and returns it). Shapes: one list, its sum, its length, one of
its elements. The item is kept only when the true answer differs from the one a reader would get by treating every assignment and every
argument as a fresh copy, so the sharing always matters.

Example (level 2):

```
def h(u, cur, n):
    u[cur] = u[cur] + n
    return u
y = [2, 2, 1, 4]
x = [5, 2]
y = h(x, 0, 5)
x = x + [5]
y = y + [3]
x[2] = 4
print(x)
```

structured (tree): `{"program": [["def", "h", ["u", "cur", "n"], [["setidx", "u", ["v", "cur"], ["b", "+", ["idx", ["v", "u"], ["v", "cur"]], ["v", "n"]]], ["ret", ["v", "u"]]]], ["set", "y", ["list", ["n", 2], ["n", 2], ["n", 1], ["n", 4]]], ["set", "x", ["list", ["n", 5], ["n", 2]]], ["set", "y", ["call", "h", ["v", "x"], ["n", 0], ["n", 5]]], ["set", "x", ["b", "+", ["v", "x"], ["list", ["n", 5]]]], ["set", "y", ["b", "+", ["v", "y"], ["list", ["n", 3]]]], ["setidx", "x", ["n", 2], ["n", 4]], ["print", ["v", "x"]]]}`

answer: `[10, 2, 4]`

### `C1.sieve_marking` (family lists; strict confidence: clear)

Procedure: sieve of Eratosthenes marking: for each still-flagged index, strike its multiples in a flag list.

Sieve marking pass over a literal 0/1 flag list (not necessarily the usual all-ones start, so no prime table helps): for i from 2:
if flags[i] is 1, strike flags[j] = 0 for j = start(i), start(i) + i, ... below n, with start(i) = i * i, i + i or 3 * i (stated in the
code). Shapes: how many flags remain 1, the sum of the indices that remain 1, how many strike writes were executed (re-strikes count). 10 to 38 flags.

Example (level 2):

```
p = [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1]
q = 0
for total in range(2, 17):
    if p[total] == 1:
        val = 3 * total
        while val < 17:
            q += 1
            p[val] = 0
            val += total
print(q)
```

structured (tree): `{"program": [["set", "p", ["list", ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 0], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 0], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1], ["n", 1]]], ["set", "q", ["n", 0]], ["for", "total", ["n", 2], ["n", 17], 1, [["if", ["c", "==", ["idx", ["v", "p"], ["v", "total"]], ["n", 1]], [["set", "val", ["b", "*", ["n", 3], ["v", "total"]]], ["while", ["c", "<", ["v", "val"], ["n", 17]], [["aug", "q", "+", ["n", 1]], ["setidx", "p", ["v", "val"], ["n", 0]], ["aug", "val", "+", ["v", "total"]]]]], []]]], ["print", ["v", "q"]]]}`

answer: `10`

### `C1.string_pair_table` (family tables; strict confidence: borderline)

Procedure: two-dimensional table over prefixes of two strings (longest common subsequence, edit distance).

Table over prefixes of two short strings, stored flat with row width len(b) + 1. Longest common subsequence: equal characters take the
diagonal + 1, else the larger of up and left. Edit distance: first row and column are 0, 1, 2, ...; each cell is the least of up + 1, left + 1
and diagonal + (0 if the characters are equal else 1). Shapes: the corner cell (the LCS length or the edit distance, which is also the last cell of the table), the last row of the table as a list,
the sum of the whole table. Lengths 3 to 6 over three letters (3x3, 3x4, 4x4, 4x5, 5x5, 5x6, 6x6).

Example (level 2):

```
d = 'nnqn'
count = 'qono'
j = len(d)
c = len(count)
p = c + 1
best = []
for s in range((j + 1) * p):
    best.append(0)
for s in range(j + 1):
    best[s * p + 0] = s
for res in range(c + 1):
    best[0 * p + res] = res
for s in range(1, j + 1):
    for res in range(1, c + 1):
        if d[s - 1] == count[res - 1]:
            cst = 0
        else:
            cst = 1
        best[s * p + res] = min(best[(s - 1) * p + res] + 1, best[s * p + (res - 1)] + 1, best[(s - 1) * p + (res - 1)] + cst)
print(best[j * p + 0:])
```

structured (tree): `{"program": [["set", "d", ["s", "nnqn"]], ["set", "count", ["s", "qono"]], ["set", "j", ["call", "len", ["v", "d"]]], ["set", "c", ["call", "len", ["v", "count"]]], ["set", "p", ["b", "+", ["v", "c"], ["n", 1]]], ["set", "best", ["list"]], ["for", "s", ["n", 0], ["b", "*", ["b", "+", ["v", "j"], ["n", 1]], ["v", "p"]], 1, [["append", "best", ["n", 0]]]], ["for", "s", ["n", 0], ["b", "+", ["v", "j"], ["n", 1]], 1, [["setidx", "best", ["b", "+", ["b", "*", ["v", "s"], ["v", "p"]], ["n", 0]], ["v", "s"]]]], ["for", "res", ["n", 0], ["b", "+", ["v", "c"], ["n", 1]], 1, [["setidx", "best", ["b", "+...`

answer: `[4, 3, 3, 3, 4]`

### `C1.turtle_walk` (family simulation; strict confidence: borderline)

Procedure: position-and-heading state machine over a command string (turn counter modulo 4).

A walker with position (x, y) and heading d in 0..3 reads a string of commands: F steps forward, B steps backward (from level 3), L and
R turn (d changes by 3 and 1 mod 4, or 1 and 3, as the code states). What each heading means is written in the code. Shapes: Manhattan
distance from the start, the final position written 'x,y', the greatest Manhattan distance reached at the end of any command. 5, 7, 9,
11, 13, 15 or 18 commands.

Example (level 2):

```
cur = 'FFFFLFFFF'
acc = 0
w = 0
t = 0
far = 0
for e in range(len(cur)):
    d = cur[e]
    if d == 'F':
        if t == 0:
            acc += 1
        elif t == 1:
            w -= 1
        elif t == 2:
            acc -= 1
        else:
            w += 1
    elif d == 'L':
        t = (t + 1) % 4
    elif d == 'R':
        t = (t + 3) % 4
    elif d == 'B':
        if t == 0:
            acc -= 1
        elif t == 1:
            w += 1
        elif t == 2:
            acc += 1
        else:
            w -= 1
    far = max(far, abs(acc) + abs(w))
print(far)
```

structured (tree): `{"program": [["set", "cur", ["s", "FFFFLFFFF"]], ["set", "acc", ["n", 0]], ["set", "w", ["n", 0]], ["set", "t", ["n", 0]], ["set", "far", ["n", 0]], ["for", "e", ["n", 0], ["call", "len", ["v", "cur"]], 1, [["set", "d", ["idx", ["v", "cur"], ["v", "e"]]], ["if", ["c", "==", ["v", "d"], ["s", "F"]], [["if", ["c", "==", ["v", "t"], ["n", 0]], [["aug", "acc", "+", ["n", 1]]], [["if", ["c", "==", ["v", "t"], ["n", 1]], [["aug", "w", "-", ["n", 1]]], [["if", ["c", "==", ["v", "t"], ["n", 2]], [["aug", "acc", "-", ["n", 1]]], [["aug", "w", "+", ["n", 1]]]]]]]]], [["if", ["c", "==", ["v", "d"], ["s",...`

answer: `8`

### `C1.union_find_links` (family graphs; strict confidence: clear)

Procedure: parent array: find follows links to a root, union hangs one root under another.

Parent array p (p[x] == x for a root); find(p, x) follows p[x] until a root. For each listed pair the two roots are found and, when
different, one is hung under the other by a rule stated in the code (first under second, second under first, or the larger root under the
smaller). Shapes: the root of a queried node, the whole parent array, the sum of the roots of all nodes.
5 + level nodes and 3 + level pairs (the number of components is never asked).

Example (level 2):

```
def find(y, d):
    while y[d] != d:
        d = y[d]
    return d
y = [0, 1, 2, 3, 4, 5, 6]
res = [4, 5, 0, 6, 5]
total = [5, 2, 5, 1, 1]
for v in range(len(res)):
    t = find(y, res[v])
    best = find(y, total[v])
    if t != best:
        y[t] = best
print(y)
```

structured (tree): `{"program": [["def", "find", ["y", "d"], [["while", ["c", "!=", ["idx", ["v", "y"], ["v", "d"]], ["v", "d"]], [["set", "d", ["idx", ["v", "y"], ["v", "d"]]]]], ["ret", ["v", "d"]]]], ["set", "y", ["list", ["n", 0], ["n", 1], ["n", 2], ["n", 3], ["n", 4], ["n", 5], ["n", 6]]], ["set", "res", ["list", ["n", 4], ["n", 5], ["n", 0], ["n", 6], ["n", 5]]], ["set", "total", ["list", ["n", 5], ["n", 2], ["n", 5], ["n", 1], ["n", 1]]], ["for", "v", ["n", 0], ["call", "len", ["v", "res"]], 1, [["set", "t", ["call", "find", ["v", "y"], ["idx", ["v", "res"], ["v", "v"]]]], ["set", "best", ["call", "find",...`

answer: `[2, 1, 1, 3, 5, 2, 1]`
