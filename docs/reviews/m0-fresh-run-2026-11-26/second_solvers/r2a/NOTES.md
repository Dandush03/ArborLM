# NOTES: second solvers r2a (R2, 9 lineages)

Environment: `/opt/homebrew/bin/python3` (Python 3.15.1), standard library only, run as `python3 -I -B <script>`.
Commands: `timeout 300 python3 -I -B run_solver2.py` (attempt 1, `run_solver2.out`), `timeout 300 python3 -I -B run_solver2_v2.py` (attempt 2, `run_solver2_v2.out`), `python3 -I -B templates.py R2.<lineage>` (`templates.out`), `python3 -I -B props.py` (`props.out`).

Source of inputs: every solver computes from `structured`. For every item the runner also parses the inputs from the question text with an independent regex parser (`parse_*` in `solver2_r2a.py`), checks it equals `structured`, and checks the answer computed from the text-parsed inputs equals the answer from `structured`. Attempt 2: 0 mismatches over 2520 items. So "structured" and "text" are interchangeable here; the deliverable uses `structured`.

Templates: "template" = question text with numbers, lists, words and town names masked (`templates.py`). Counts below; full list in `templates.out`.

## R2.binary_search_trace
Procedure: simulate the stated search (1-based lo=1, hi=n, mid=(lo+hi)//2; stop on hit or lo>hi); record the values looked at. `values` -> `a, b, c`; `sum` -> their sum.
Read: `xs`, `target`, `ask` (structured); text: cross-check only. Templates: 2 (values 149 items, sum 131). 144 targets present, 136 absent.
Hand-checked: L0 i0 (44+16+32+29=121), L0 i1 (32+11+18+23=84), L6 i0 (67+133+149+140+135=624). All agree with code.

## R2.caesar_shift
Procedure: each letter forward by k mod 26, spaces kept. Read: `k`, `text`. Templates: 1. k in 1..25.
Hand-checked: L0 i0 davar+19 = wtotk; L0 i1 toman+24 = rmkyl; L6 i1 first word lonix+9 = uxwrg. Agree.

## R2.cellular_automaton
Procedure: synchronous update for `steps` steps, cells beyond the ends are 0, rule table keyed by 'LCR'. Read: `row`, `table`, `steps`. Templates: 1 (steps 2..5; table always full).
Hand-checked: L0 i0 both steps by hand (01100111100 -> 00110011111). Agree. Also checked from the text-parsed table (identical).

## R2.cheapest_network
Procedure: minimum spanning tree weight (Kruskal, union-find); error if not all towns joined (never happened). Read: `towns`, `cables`. Templates: 7, differing only in the number of towns/cables (one per level). Every item has tied costs; ties do not change the MST weight. No duplicate pairs, no self loops.
Hand-checked: L0 i0 by hand Kruskal (4+4+5+9+9+13+16=60). Agree. (Only one fully hand-run item at this lineage; L3/L6 rely on the same code path plus the text cross-check.)

## R2.count_divisible
Procedure: sum of entries x (with repetition) with x % m == 0 and x > t (strict). Read: `xs`, `m`, `t`. Templates: 1. In all 280 items t itself is in the list and divisible by m (it must be excluded: "greater than"). 6 items have answer 0.
Hand-checked: L0 i0 (74+80+74+88+92+80=488), L0 i1 (45+51+72+90=258). Agree.

## R2.crt_smallest
Procedure: general CRT merge (works for non-coprime moduli; none occur), smallest positive: if the residue is 0 the answer is the lcm. Every answer verified by brute force (no smaller positive solution; max answer 356010). Read: `congruences`. Templates: 2 (two congruences 120 items, three 160).
Hand-checked: L0 i0 (37), L0 i1 (200), and the all-zero item L1 i5 (lcm(10,17)=170). Agree.

## R2.dictionary_rank
Procedure: words = ordered arrangements without repetition of `length` letters from `letters`, in lexicographic order, numbered from 1. `word`: unrank k-1 by factorial-number-system blocks perm(remaining-1, L-1-i); `position`: rank + 1. Every item (280) also checked against brute-force enumeration with itertools.permutations. Read: `letters`, `length`, `ask`, `k`/`word`. Templates: 2 (word 157, position 123).
Hand-checked: L0 i0 (k=763 -> knga), L0 i1 (fbpv -> 531). Agree.

## R2.expression_eval
Procedure: tokenizer + recursive parser; each parenthesised group evaluated first. `ranked`: multiplications left to right, then + and - left to right. `left_to_right`: all operators strictly left to right. Unary minus would raise (none present); no nested parentheses occur. Read: `text`, `convention` (convention also identified from the text template and cross-checked). Templates: 2 (ranked 134, left_to_right 146). 98 negative answers.
Hand-checked: L0 i0 ranked (1), L0 i1 left_to_right ((3-2)*6=6; ((4+5)-6)*6=18), L6 i1 ranked (189). Agree.

## R2.from_base
Procedure: positional value of `digits` in `base` (digit a=10 ... f=15); error if a digit >= base (never). Read: `base`, `digits`. Templates: 1 (bases 2,3,4,5,7,8,9,16).
Hand-checked: L0 i0 (1111_2=15), L0 i1 (11012_3=113), L6 i0 (1101110100_2=884). Agree.

## Attempts kept
- Attempt 1 (`run_solver2.py` -> `run_solver2.out`, `answers_r2a.jsonl`): 280 "problems", all `PARSE MISMATCH` in R2.cheapest_network, caused by my checker comparing the town list in order (the text lists towns alphabetically, `structured` does not). Solver not involved.
- Attempt 2 (`run_solver2_v2.py`, generated from attempt 1 by a one-off inline Python string replacement (its only output, `ok`, is `make_v2.out`): compares towns as a set and writes `answers_r2a_v2.jsonl`) -> `run_solver2_v2.out`: 0 problems; `answers_r2a_v2.jsonl` is byte-identical to `answers_r2a.jsonl` (`cmp`). `answers_r2a.jsonl` is the deliverable.
