# Second solvers m1b (EVAL M1): notes per lineage

Written only from `m0_second_solver_fixtures_20261126/README.md`, `M1/<lineage>/SCHEMA.md` and `M1/<lineage>/fixtures.jsonl` for the ten lineages below.
Environment: system `python3` = Python 3.15.1, run as `python3 -I -B <script>` from this directory (`cd` into this scratch directory only), standard library only.
Every solver computes from `structured` only; the question text is not needed by any of the ten. `check_text.py` re-parses every input from the question text independently and compares it with `structured`: 0 mismatches in all 2800 items (`check_text.out`). Template enumeration: `templates.py` (digits masked, the four intro sentences, names and activity names masked); output reproduced below.
Run: `timeout 120 python3 -I -B run_solver2.py` -> `answers_m1b.jsonl` (2800 lines), `run_solver2.out`: 280 answered per lineage, 0 exceptions, 0 bad format, 0 values needing rounding.
Format checks applied in `run_solver2.py`: whole-number lineages `^(0|[1-9]\d*)$`; linear_equation `^(0|-?[1-9]\d*)$`; median/mixture/percent `^-?(0|[1-9]\d*)(\.\d?[1-9])?$`.
Hand checks: computed by hand (mental arithmetic, written in my working) before printing the solver's value for those items; all 31 agreed.

## M1.gcd_lcm_r4
Procedure: `ask`=gcd -> gcd of `values` (greatest common piece length of ribbons); `ask`=lcm -> lcm of `values` (first time all lights flash together again). Read from structured: `ask`, `values`.
Templates (2, each with 0 or one of 4 intro sentences): "X has N ribbons of lengths ... centimetres ... greatest possible length of a piece" (129); "N lights flash at the same moment ... one flashes every N seconds, [another every N seconds, ...] the other/the last every N seconds ... flash together again for the first time" (151); 2-4 values.
Hand checks: L0 i0 lcm(1300,1118)=55900; L5 i1 gcd(14352,2990,3120,5520)=2; L6 i0 lcm(16,20,28,108)=15120.

## M1.grid_perimeter_r3
Procedure: cells from the row runs; perimeter = 4*cells - 2*(number of edge-adjacent cell pairs), i.e. exactly the text's definition (sides belonging to exactly one square). Read: `rows`.
Templates: 1 (row lines vary: "column c", "columns a to b", "no squares"; 5-10 rows).
Hand checks: L0 i0 = 30; L1 i0 = 32; L0 i36 = 38 (an item with an empty cell enclosed by corner-touching squares).

## M1.inclusion_exclusion_r3
Procedure: two sets: union = A + B - AB; three sets: union = S - P + T, exactly one = S - 2P + 3T, exactly two = P - 3T (S = sum of sizes, P = sum of pair counts, T = triple; pair counts include the triple, as the text says); none = total - union. Read: `total`, `sizes`, `pairs`, `triple`, `ask`.
Templates (6): two sets x {none, at least one}; three sets x {none, at least one, exactly one, exactly two}. No two-set item asks exactly one/two. All Venn regions are non-negative in all 280 items (`check_text.py`).
Hand checks: L0 i0 = 4; L3 i1 = 131; L4 i0 = 14.

## M1.last_digit_power_r3
Procedure: each term is base**exponent mod modulus (`pow`); combine by sum or product mod modulus. Read: `modulus`, `op`, `terms`.
Templates (3, each with one of 4 intro sentences): single "the product of N factors, each equal to B" (80); "the product of all the following factors: N factors equal to B, ... and N factors equal to B" (104, op=product); "the sum of the product of N factors, each equal to B, ... and the product of ..." (96, op=sum).
Observation: in all 80 single-term items `structured.op` is `sum` while the text says "the product of N factors"; with one term sum and product are the same value, so no effect.
Hand checks: L1 i0 2^282 mod 59 = 3; L0 i1 25^232 mod 67 = 25; L1 i1 28^69 mod 47 = 1 (Euler's criterion).

## M1.linear_equation_r3
Procedure: x = (n - m)/(k - j) (j = 0 for the one-sided form), checked to be an integer. Read: `k`, `m`, `j`, `n`.
Templates (6): one-sided with adding/subtracting; two-sided with adding/subtracting on each side.
Hand checks: L0 i0 = 4; L1 i0 = -20; L3 i0 = 45; L4 i0 = 64.

## M1.median_list_r3
Procedure: sort; odd count -> middle value; even -> mean of the two middle values (exact fraction, then format). Read: `values` (`shape` always list).
Templates: 1 (with one of 4 intro sentences; 7-18 values).
Hand checks: L0 i0 = 42; L1 i0 = 120.5; L2 i1 = 155.5.

## M1.mixture_r4
Procedure: (a*x + b*y)/(x + y) + packing, exact fraction then format. Read: `a`, `b`, `x`, `y`, `packing`.
Templates (3): no packing (120); packing "N dollars per kilogram" (142); packing "1 dollar per kilogram" (18).
Hand checks: L0 i0 = 28.4; L3 i1 = 18.85; L6 i1 = 33.07.

## M1.painted_cube_r3
Procedure: per axis, count positions by number of painted end faces (length and width: both ends painted; height: top painted, bottom painted unless `bottom_unpainted`); combine the three distributions and sum those with total = `faces`. Read: `dims`, `bottom_unpainted`, `faces`. All dims >= 3 in the fixtures.
Templates (4, each with one of 4 intro sentences): {all faces painted, bottom unpainted} x {"painted faces", "painted face"}.
Hand checks: L0 i0 = 100; L1 i0 = 1019; L1 i1 = 588.

## M1.percent_change_r3
Procedure: multiply the price by (100 +/- p)/100 per step, exact fractions, no intermediate rounding; format. Read: `price`, `steps`.
Templates: 1 (2 or 3 steps). No intermediate price in any item has a fraction of a cent (`check_extra.out`), so per-step rounding to cents would not change any answer.
Hand checks: L0 i0 = 42.5; L3 i0 = 442.68; L4 i0 = 167.04.

## M1.pipes_work_r3
Procedure: minutes = volume / (a + b - drain); checked net rate > 0 and exact division (true for all 280). Read: `a`, `b`, `drain`, `volume`.
Templates (2): without drain (120), with drain (160).
Hand checks: L0 i0 = 40; L3 i0 = 50; L5 i0 = 53.
