# NOTES: second solvers, NAME=m1a, EVAL=M1 (10 lineages)

Environment: macOS (darwin), system `python3` 3.15.1, run as `python3 -I -B <script>` from this directory; standard library only.
Commands: `timeout 300 python3 -I -B run_solver2.py` (output `run_solver2_attempt1.out`, `answers_m1a.jsonl`); `timeout 120 python3 -I -B edgecheck2.py` (`edgecheck2.out`). `peek.py` printed samples and templates (digits -> `#`, capitalised words -> `Name`; the template counts below come from it).

Every solver computes from `structured`. `run_solver2.py` also parses every question text with an independent regex parser (`TEXT_PARSERS` in `solver2_m1a.py`) and compares each parsed field with `structured`: 0 mismatches in all 2800 items. Each parser fails loudly if a question does not match its template, so the 2800 parses with no failures also show that every wording variant is handled.
Result: 2800 answers, 0 exceptions, 0 format failures (regex `^(0|[1-9]\d*)$`; consecutive_r3 `^(0|-?[1-9]\d*)$`).
Note: the fixture field `id` is the lineage id, not an item id. An item is identified by (`id`, `level`, `index`), and the answers file keeps all three.

## M1.ages_r3
Procedure: the older person is k times the younger; (k*y+t)+(y+t)=sum, so y=(sum-2t)/(k+1). The answer is y or k*y. The solver raises an error if the result is not a positive integer (no item did).
Source: k, t, sum from structured. Which person is asked comes from the text (the asked name is compared with the two names) and is checked against `structured.ask` (agreed on all 280). Solved from both.
Templates: 2 ("In N years" 261; "In 1 year" 19).
Hand-checked: L0#0 (5y+30=235, y=41), L3#1 (8y+4=764, y=95, older 665), L6#1 (10y+10=1040, y=103). All agree.

## M1.arithmetic_series_r3
Procedure: sum of first+step*i for i=0..days-1.
Source: structured. Templates: 1.
Hand-checked: L0#0 (8*41+7*28=524), L3#1 (420+19*15=705), L6#1 (448+19*91=2177). All agree.

## M1.average_missing_r4
Procedure: needed = n*mean - sum(scores), in exact fractions (mean_cents/100). The solver raises an error unless the result is an integer within 0..max mark.
Source: structured for the arithmetic. The maximum mark ("out of N") is only in the text, so it is read from there and used for the range check. Solved from both.
Templates: 7 (3-6 known scores; integer or decimal mean; decimals seen: .2 .25 .4 .5 .6 .75 .8).
Hand-checked: L0#0 (268-219=49), L3#1 (369-328=41), L6#1 (749-609=140). All agree. In 3 items the needed score equals the maximum mark, which is allowed.

## M1.change_ways_r3
Procedure: count unordered multisets of the 3 coin values that sum to the target (coin-change dynamic programme, combinations not permutations).
Source: structured. Templates: 4 (four framing sentences; the problem sentence is the same).
Hand-checked: L0#0 (3,7,9 -> 85: 23 by enumerating the count of 9s), L1#0 (2,4,15 -> 26: 7), L3#1 (2,3,12 -> 42: 8+6+4+2=20). All agree.

## M1.clock_duration_r4
Procedure: sum of (arrival - departure) over legs. The solver checks dep < arr within the day and that the legs are in order (minimum gap between legs is 5 minutes).
Source: structured; the text times (HH:MM) were parsed and matched.
Templates: 4 (2, 3, 4 or 5 legs).
Hand-checked: L0#0 (60+50=110), L3#1 (38+102+103=243), L6#1 (139+48+65+144+129=525). All agree.

## M1.consecutive_r3
Procedure: smallest = (sum - step*c(c-1)/2)/c (must be an integer); largest = smallest + step*(c-1).
Source: structured. Templates: 8 (step 1 "integers" / step 2 "differ from the next by 2"; largest/smallest; positive or negative sum). 6 items have a negative sum and a negative answer.
Hand-checked: L0#0 (5409/3=1803, largest 1804), L3#1 ((3600-12)/4=897, largest 903), L6#1 ((58338-30)/6=9718), plus the negative cases L0#8 (-555 -> -184) and L6#16 (-612 -> -97). All agree.

## M1.crt_congruence_r3
Procedure: smallest positive x with x mod m = r for all conditions. Brute force over one period of the lcm, stepping by the largest modulus; if all remainders were 0 this would return the lcm (no such item). No item has non-coprime moduli, but the method does not need coprime moduli.
Source: structured. Templates: 3 (2, 3 or 4 conditions).
Hand-checked: L0#0 (16+32j = 18 mod 37 gives j=7, x=240), L3#1 (13704: remainders 5/2/19 checked, below the lcm 17290), L6#1 (231897: remainders 41/9/1/3 checked, below the lcm 550056). All agree.

## M1.division_counting_r3
Procedure: empty_seats: ceil(people/seats)*seats - people. pallets: boxes = items // box; answer = boxes mod crate.
Source: structured (`shape` chooses the procedure; the text parser identifies the same shape independently).
Templates: 25 (1 bus template, 147 items; pallets: 4 framings x 6 item nouns, 133 items).
Hand-checked: L0#0 (22 buses, 1298-1289=9), L3#1 (579 boxes, 579 mod 28=19), L6#1 (6 buses, 564-498=66). All agree. 4 bus items and 14 pallet items have the answer 0.

## M1.finite_differences_r4
Procedure: exact Lagrange interpolation through the first degree+1 terms, evaluated at the asked position. The solver checks that every remaining given term lies on that polynomial and that the leading difference is non-zero (degree is exact).
Source: structured. Templates: 12 (4 framings x 5, 6 or 7 terms). The asked position is 1 or 2 past the last given term.
Hand-checked: L0#0 (second difference 12, 209+66=275), L3#1 (second difference 44, 1068+323=1391, +367=1758), L6#1 (third difference 12, 1289+488=1777). All agree.

## M1.fraction_remainder_r3
Procedure: left1 = start - start/a; answer = left1 - left1/b. The solver requires both spends to be whole dollars (true for all items).
Source: structured; the ordinal words in the text (half, third, quarter, fifth..twelfth) were mapped and matched.
Templates: 107 by the crude template key, all one sentence frame differing only in the two ordinal words.
Hand-checked: L0#0 (1341-447=894, 894-149=745), L3#1 (3696-528=3168, 3168-288=2880), L6#1 (2277-253=2024, 2024-506=1518). All agree.

## Own mistake, kept
`edgecheck.py` (output `edgecheck_attempt1_WRONG_KEY.out`) keyed answers by `id` alone. Because `id` is the lineage id, every lookup returned the last answer of the lineage, so its answer-based counts (change answers0, div ans0, consec neg answers, avg) are wrong. Its structured-only lines (crt non-coprime/all-zero, fd ask/len, ages k, clock gap, fraction a/b) are unaffected. `edgecheck2.py` repeats the answer-based checks with the key (id, level, index).
