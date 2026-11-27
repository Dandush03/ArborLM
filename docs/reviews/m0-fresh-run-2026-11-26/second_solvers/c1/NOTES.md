# NOTES: second solver for C1 (NAME = c1, EVAL = C1)

Written by an independent auditor context (Claude Opus 5.5) from the answer-free fixtures only. Not Astra validation, not human approval. `Astra review: NOT_PERFORMED`.

## One solver for all 26 lineages

`solver2_c1.py`: `SOLVERS` maps each of the 26 `C1.*` ids to the same function `solve_c1(question, structured)`.

- **Input used: the question text.** The program source is cut out of the fixed wrapper (`Here is a Python program.\n\n` ... `\n\nWhat exactly does it print? It prints a single line.`) and parsed with the standard `ast` module (`ast.parse`, parsing only). A tree-walking interpreter written in `solver2_c1.py` (class `Interp`) runs the tree. Nothing of the item is executed by the host interpreter: no `exec`, `eval`, `compile`, `runpy` or subprocess appears anywhere in the solver.
- **`structured` is used only as a cross-check.** `structured_to_ast` converts the `structured["program"]` tree (statement tags `set aug setidx append for while if def ret print`, expression tags `n s v b c and or not list idx slice call m`) into `ast` nodes, and `run_solver2.py` runs the same interpreter on it. Result over 7280 items: 0 disagreements between the two forms, 0 exceptions. This checks that the two input forms agree; it is not an independent computation (both go through my one interpreter).
- The answer is the single printed line. If the program prints anything other than exactly one line, the solver raises.

## Constructs found in the fixtures (enumerated by `enumerate_constructs_v2.py`, `enumerate_detail.py`, `templates.py`)

Statements: `Assign` (one target; a `Name` 33848 times or a `Subscript` with an index 3544 times), `AugAssign` (`+=`, `-=`, target always a `Name`), `Expr` (a `print(...)` call or `x.append(...)`), `If`/`elif`/`else`, `While` (no `else`), `For` over `range(...)` with a `Name` target (no `else`), `FunctionDef` (plain positional parameters, no defaults/decorators, no nesting, no `global`), `Return` (always with a value).
Expressions: int and str constants, names, list displays, `BinOp` `+ - * // %`, `UnaryOp` `-` (only on constants, e.g. `(-2)`), `BoolOp` `and` (2 operands; `or` never occurs), `Compare` with one operator `== != < <= > >=` (no chained comparison occurs), subscripts with an index (on names, calls, string constants, binops, nested subscripts) and with slices (all 27 combinations of absent / constant / negative lower, upper and step occur), calls to `print len str range sum max` and user functions, methods `list.append`, `str.lower`, `str.upper`, `str.replace(old, new)`. Every program has exactly one `print` call, with one argument.
Not occurring: `or`, `not`, chained comparisons, `min abs sorted`, `/`, `**`, tuples, dicts, comprehensions, `break`/`continue`, iteration over anything but `range`, keyword arguments, multi-argument `print`.

## Semantics implemented deliberately (and how)

- **Integer floor division `//` and modulo `%` with negative operands**: `floordiv` divides the magnitudes (both non-negative); when the operand signs differ it negates the quotient and subtracts 1 if the division was inexact (floor, not truncation toward zero). `mod(a, b) = a - b * floordiv(a, b)`, so a non-zero remainder has the divisor's sign. Division by zero raises. Exercised by 110 items (48 in bytecode_loop_f3, 62 in func_compose_f4); e.g. func_compose_f4 L0 #10 needs `-3 % 19 == 16` (hand-checked: 45; truncating semantics would give 7).
- **Indexing**: int index; a negative index adds `len`; out of range raises `IndexError`.
- **Slicing with negative / out-of-range bounds and steps** (`slice_positions`): CPython's index adjustment written out. Step defaults to 1; step 0 raises. A given bound `v`: if `v < 0` add `len`, and if still `< 0` clamp to `-1` (negative step) or `0` (positive step); if `v >= len` clamp to `len - 1` (negative step) or `len` (positive step). Defaults: start `0` / stop `len` for a positive step; start `len - 1` / stop "before 0" (`-1`) for a negative step. Then walk from start by step while `i < stop` (positive) or `i > stop` (negative). Lists give a new list, strings a new string. Exercised: 375 slice evaluations with a negative or out-of-range bound, 529 with a negative step, 439 with |step| > 1.
- **Aliasing of lists**: lists are mutable objects held by reference. `b = a` binds the same object; `append`, index assignment and `list += iterable` (implemented as an in-place extend of the same object) are visible through every name; `a + b`, slices and list displays create new lists. Arguments bind the callee's parameters to the caller's objects, so a function that mutates `b[d]` and returns `b` returns the same list (shared_lists_f3 L6 #7, hand-checked: 28); rebinding a parameter (`val = val + [y]`) does not affect the caller (shared_lists_f3 L6 #0, hand-checked: 30).
- **Short-circuit `and`/`or` return an operand**: `and` returns the left operand if it is falsy, else evaluates and returns the right; `or` returns the left if truthy, else the right; the right side is not evaluated when short-circuited. Truthiness: `None`, `False`, `0`, empty str and empty list are false. (`or` and `not` are implemented but do not occur; `and` occurs only in `if`/`while` conditions, where it guards index reads such as `s > 0 and n[s - 1] == 1`, so the short circuit matters there.)
- **Chained comparisons**: `a < b < c` evaluates as `(a < b) and (b < c)` with `b` evaluated once and stopping at the first false link; the result is a bool. Implemented, does not occur. Comparison of ints (bools as ints) is numeric, of strings by code point lexicographically, of lists lexicographically (first unequal element decides, else length); `==` between different kinds is false; ordering across kinds raises.
- **Recursion and scope**: each user call gets a fresh local frame; local names are determined statically as in Python (parameters plus every name assigned, augmented-assigned, used as a `for` target or `def`'d in the body); reading a local before assignment raises; other names resolve to module globals at call time, then builtins. `return` unwinds via an internal exception; falling off the end returns `None`. User call depth is capped at 900 (CPython's default limit is 1000 frames) and the host recursion limit is raised temporarily so the walker itself does not overflow.
- **How `print` renders**: `print(a, b, ...)` joins `str(arg)` with one space (as the README states for the builder's replacement `print`). `str` of a string is the string itself (no quotes); of an int its decimal digits with a leading `-` if negative (digit loop written here; more than 4300 digits raises, as CPython's default limit would); of a bool `True`/`False`; of `None` `None`; of a list `[` + the elements' `repr` joined by `, ` + `]`, where `repr` of a string uses single quotes unless it contains `'` and no `"`, escaping `\`, the quote, `\n`, `\t`, `\r` (other non-printable characters raise as unsupported); nested lists recurse. The builtin `str(x)` uses the same rendering.
- Other: `+` on int/int, str/str, list/list; `*` int×int and sequence repetition (count ≤ 0 gives empty); `len`; `sum` (start 0); `max`/`min` (keep the first of equal elements); `abs`; `sorted` (stable); `range(stop)` and `range(start, stop[, step])` (step 0 raises); a `for` evaluates its `range` once and leaves the loop variable at its last value; `str.lower`/`upper` (ASCII; non-ASCII raises); `str.replace(old, new)` (left to right, non-overlapping; empty `old` inserts `new` around every character). Order of evaluation: assignment evaluates the right side first, then the container, then the index; augmented assignment loads the target before evaluating the right side; operands and arguments left to right.
- **Unsupported constructs raise `Unsupported("<construct>")`** and never fall through: every statement, expression, operator, builtin and method dispatch ends in such a raise. `test_primitives.py` shows five (a dict, iteration over a string, `/`, `**`, a list comprehension), each raising with the construct named. A loop guard of 5,000,000 steps raises rather than hanging.

## Checks on the implementation (no item code executed by the host)

`test_primitives.py`: 49285 checks, 0 failures. It compares my `floordiv`/`mod` (a in -40..40, b in -13..13 without 0, and 31-digit operands), slicing (lists and strings of length 0..7, bounds in -9..9 and None, steps ±1..3 and None), indexing, `str`/`repr` rendering, `replace`, `lower`/`upper` and the six comparison operators with the host's own operators on synthetic values; and runs 8 small literal programs written by me (and/or operands, chained comparisons, aliasing, in-place `+=`, recursion, parameter rebinding, negative `//`/`%`) through the interpreter against values I wrote down.

## Per lineage

Wrapper templates: exactly one question template in every lineage (checked over all 280 items each; 0 mismatches). "Skeletons" = distinct programs after abstracting names, constants and list contents (`templates.py`); every skeleton is run by the same interpreter. All 280 items per lineage ran with no exception, and the character set of my answers equals the set stated in each lineage's SCHEMA.md (`check_charsets.py`, 26 of 26 equal). Input: question text (source) for all 26; `structured` only as the cross-check, for all 26.

Hand traces: for every lineage I traced by hand, without the solver, the shortest program at levels 0, 3 and 6 (`pick_hand.py`) and compared with the solver: 78 of 78 agree. Twelve hazard items were also traced by hand (`show_items.py`), all agree: bytecode_loop_f3 L1 #6 (`-3 % 2`) -> 3, func_compose_f4 L0 #10 (`-3 % 19`) -> 45, func_compose_f4 L6 #0 -> 8, recursive_calls_r2 L0 #0 -> 73, recursive_calls_r2 L6 #0 -> 291628912, shared_lists_f3 L6 #0 -> 30, shared_lists_f3 L6 #7 -> 28, slices_f4 L0 #0 -> lmnai, slices_f4 L0 #1 -> o, slices_f4 L6 #5 -> [39, 1], string_methods_f3 L6 #0 -> xax, list_build_f3 L6 #0 -> 19.

| lineage | what the programs do | skeletons (per level 0..6) | hand-checked (level #index -> answer) |
|---|---|---|---|
| binary_search_f3 | binary search over a sorted list, accumulating probed values, probe indexes, or an l/r path | 6 (6 each) | L0 #13 -> 108; L3 #13 -> 144; L6 #17 -> 360 |
| bracket_matching_f3 | stack of bracket codes in a preallocated list; prints the remaining stack slice or mismatches*10+depth | 5 (5 each) | L0 #19 -> [2, 4, 4, 2, 2, 3]; L3 #24 -> [2, 4, 4, 2, 4, 2, 1, 3, 2]; L6 #16 -> 54 |
| bytecode_loop_f3 | opcode/operand pairs run in a while loop (add, mul, sub, conditional skip, mod, save/restore) | 7 (1,2,2,2,2,2,2) | L0 #2 -> -16; L3 #9 -> 9; L6 #33 -> 84 |
| circle_elimination_r2 | step k live positions around a 0/1 circle, eliminate, repeat; print the last position | 3 (3 each) | L0 #17 -> 2; L3 #26 -> 9; L6 #2 -> 0 |
| cond_chain_f3 | subtraction-style if/elif/else chain in a for loop, sometimes with a halving rule | 4 (2 each) | L0 #10 -> 32; L3 #28 -> 67; L6 #0 -> 170 |
| counter_list_f3 | rolling residue `(b*k + n) % m` counted into a list | 3 (3 each) | L0 #20 -> [4, 3, 1]; L3 #35 -> [4, 3, 3, 7]; L6 #6 -> [11, 11, 4] |
| digit_peel_f3 | peel base-3 digits and re-accumulate them in another base | 4 (4 each) | L0 #18 -> 6644; L3 #33 -> 706; L6 #12 -> 111366551 |
| euclid_gcd_traced_f3 | a bounded number of Euclid steps; prints the pair as "a b" | 8 (8 each) | L0 #9 -> 38 16; L3 #34 -> 6 4; L6 #3 -> 66 24 |
| fast_power_f4 | square-and-multiply with a perturbed squaring `(u*u + c) % q` | 1 (1 each) | L0 #31 -> 0; L3 #15 -> 20; L6 #29 -> 25 |
| fib_like_f3 | two-term linear recurrence in a for loop | 8 (8,8,8,7,8,8,8) | L0 #7 -> 80; L3 #10 -> 38229; L6 #20 -> 271443 |
| fib_shapes_recursive_f3 | doubly recursive `h(n-1)*a + h(n-2)*b + c` | 2 (2 each) | L0 #10 -> 7118; L3 #15 -> 865323; L6 #1 -> 145837509 |
| func_branch_f4 | piecewise function with if/elif/else, results combined with + and - | 16 (2,2,2,4,4,8,8) | L0 #32 -> 21; L3 #34 -> -55; L6 #8 -> 545 |
| func_compose_f4 | composed affine functions with a final `%` (negative operands occur) | 54 (8,8,22,19,18,15,20) | L0 #26 -> 14; L3 #37 -> 1; L6 #21 -> 21 |
| list_build_f3 | build a list with append from an expression of the loop index; print it or a weighted sum | 30 (22,18,21,21,22,24,18) | L0 #12 -> [0, 1, 4, 9, 5, 3]; L3 #31 -> [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]; L6 #26 -> [1, 2, 4, 3, 0, 1, 2, 4, 3, 0, 1, 2, 4, 3] |
| merge_two_sorted_f3 | merge loop with an `and` guard; accumulate the max or the difference of the heads | 4 (4 each) | L0 #35 -> 26; L3 #11 -> 8; L6 #12 -> 0 |
| nested_pairs_f3 | nested for loops with a condition on the pair; accumulate | 106 (31,35,29,32,31,33,35) | L0 #4 -> 0; L3 #27 -> 12; L6 #38 -> 358 |
| postfix_evaluation | postfix evaluation with negative op codes over a preallocated stack | 2 (2 each) | L0 #15 -> 11; L3 #21 -> -162; L6 #10 -> -188 |
| recursive_calls_r2 | divide-in-halves recursion, or recursion along a list passed as a parameter | 3 (3 each) | L0 #9 -> 1792; L3 #2 -> 37777; L6 #10 -> 13622 |
| run_length_scan | run-length scan of a string, printing run lengths (or symbols) | 3 (3 each) | L0 #35 -> 132; L3 #1 -> 133112; L6 #36 -> 134252111 |
| shared_lists_f3 | aliasing, copying (`[:]`, `+`), mutation, and helper functions that mutate or rebind | 248 (17,33,38,40,40,40,40) | L0 #28 -> 16; L3 #34 -> [5, 4, 1, 2, 3]; L6 #39 -> 23 |
| slices_f4 | concatenations of slices of a string or list (negative and out-of-range bounds, negative steps) | 221 (37,38,37,38,40,40,36) | L0 #5 -> raare; L3 #21 -> xeodvnrdxeodvn; L6 #1 -> anktiaxbmnaazknoirbx |
| string_build_f3 | build a string in a for loop with if/elif/else on residues | 18 (9 each) | L0 #12 -> saas; L3 #3 -> dodvdvdodv; L6 #7 -> vsppvpspvppsvpppv |
| string_methods_f3 | chains of slicing, `*`, `+`, `lower`/`upper`/`replace` on string literals | 277 (37,40,40,40,40,40,40) | L0 #14 -> rosotrosot; L3 #19 -> nartyqpuf; L6 #20 -> ixdetixdetixdetixbb |
| turtle_walk_f3 | turtle with heading 0..3 and move/turn/back codes; prints "x,y" or an accumulated weighted sum | 12 (12,12,12,12,11,11,12) | L0 #31 -> -2,-3; L3 #6 -> 378; L6 #4 -> 3,2 |
| union_find_links_f3 | union-find without path compression via a `find` function; prints the parent list | 6 (6 each) | L0 #16 -> [7, 1, 2, 2, 2, 5, 6, 7, 2]; L3 #30 -> [6, 2, 9, 3, 9, 5, 7, 1, 8, 9, 10, 11]; L6 #2 -> [0, 2, 2, 1, 6, 2, 6, 6, 9, 2, 13, 5, 12, 5, 14] |
| while_counter_f3 | while loop applying an update until a bound is passed | 6 (6,6,5,6,6,6,6) | L0 #12 -> 256; L3 #2 -> 573; L6 #25 -> 2046 |

## Files and commands

System Python 3 (`python3 --version` = Python 3.15.1), standard library only, each script run as `timeout <s> python3 -I -B <absolute path of script> [args]`.

- `solver2_c1.py`: the solver (interpreter, structured front end, `SOLVERS`).
- `run_solver2.py answers_c1.jsonl` -> `answers_c1.jsonl` (7280 lines). Its stdout was shown on the console only (items 7280, 26 lineages of 280, 0 exceptions, 0 disagreements, 0 format violations). Re-run `run_solver2.py answers_c1_rerun.jsonl > run_solver2_rerun.out`: same summary, and `answers_c1_rerun.jsonl` is byte-identical to `answers_c1.jsonl` (`cmp`).
- `enumerate_constructs.py` (first attempt; failed with `IndexError` in my own tree walk, which read a parameter list `["b"]` as a node; kept), `enumerate_constructs_v2.py` (guarded copy), `enumerate_detail.py`, `templates.py`, `show_shapes.py`: construct and template enumeration.
- `test_primitives.py`, `check_charsets.py`, `hazard_census.py`, `negdiv_by_lineage.py`: the checks described above.
- `pick_hand.py`, `show_items.py`: print items for hand tracing (the traces were done by reasoning, not by code).
