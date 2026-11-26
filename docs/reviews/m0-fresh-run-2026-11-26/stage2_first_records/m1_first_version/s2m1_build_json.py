# ruff: noqa
"""M0 stage 2, M1: write stage2_conditions_m1.json from the auditor's per-lineage readings (below, written by hand from the code)
and the fixture check output (s2m1_fixtures.out.json). Deterministic: sorted keys, indent 2, trailing newline. Standard library only.
Usage: python3 s2m1_build_json.py s2m1_fixtures.out.json stage2_conditions_m1.json"""
import json, sys

W = "studies/m0/"
SOLVER = "docs/reviews/m0-lineage-decision-2026-11-25/final_m1/solve_text_a5.py"
# (builder location, wording note, level-dependent parameters as read in code)
L = {
 "M1.ages_r3": ("lineages_m1_fix3_a.py:184-196", "names distinct (r.sample); (k+1)b+2t=sum has one solution; ask names the person; whole-number format stated", "younger age 3..70+10L, k 2..6+L//2, t 1..15+L: every level a different range"),
 "M1.arithmetic_series_r3": ("lineages_m1_fix3_a.py:277-285", "day 1 and inclusive count stated; whole-number format stated", "days 4..12+3L: every level a different range"),
 "M1.average_missing_r4": ("lineages_m1_fix4.py:129-142", "marks out of M, whole marks, exact mean printed; the needed mark is unique and lies in 40..M by construction", "tests 4+L//2 and mark ceiling M=100+10L: every level different (LEVEL_PARAMETER strictly rising, :46, :87)"),
 "M1.change_ways_r3": ("lineages_m1_fix3_b.py:269-282", "unlimited coins, order does not matter (multisets) stated; at least one way by construction", "coin multiplicity bound 5+2L sets the target range: every level different (target and table size grow)"),
 "M1.clock_duration_r4": ("lineages_m1_fix4.py:148-171", "same day, 24-hour clock, ride time only stated; last arrival <= 23:59 by construction", "legs 2+L//2, waits 5..40+4L, rides 20..110+6L: every level different (LEVEL_PARAMETER :47, :89)"),
 "M1.consecutive_r3": ("lineages_m1_fix3_a.py:199-209", "count, step and smallest/largest ask stated; sign convention stated", "count 3+L//2, step 2 allowed from L2, first number -200..4000+2000L: every level different"),
 "M1.crt_congruence_r3": ("lineages_m1_fix3_b.py:64-85", "pairwise coprime moduli >= 9, remainders 1..m-1: least positive solution unique", "k=2 (L0-2, moduli <= 60/70/80), k=3 (L3-4, <= 36/40), k=4 (L5-6, <= 44/48): every level different"),
 "M1.division_counting_r3": ("lineages_m1_fix3_b.py:351-372", "left-over items, full pallets, fewest buses and no standing stated: one reading", "s=1+L sets box, pallet, seat and count ranges: every level different"),
 "M1.finite_differences_r4": ("lineages_m1_fix4.py:207-228", "degree stated and m >= degree+3 terms printed: the polynomial and the asked term are unique", "coefficient ceilings fd_ceilings(L) (:60-65), degree 3 from L5, one more printed term from L3: every level different, answer ceiling strictly rising"),
 "M1.fraction_remainder_r3": ("lineages_m1_fix3_a.py:132-145", "fraction of the start then of what is left stated; whole by construction", "start amount bound 3000+500L: every level a different range; the step count does not change (difference is operand size only)"),
 "M1.gcd_lcm_r4": ("lineages_m1_fix4.py:177-201", "ribbon (greatest common piece) and lights (first common flash) unambiguous; minor grammar 'all 2 flash' at k=2 does not change the key", "GCD_LCM_TABLE (:51): k=2 at L0-2, 3 at L3-4, 4 at L5-6, with (top, gmax) widening inside each k; gcd_lcm_ceiling strictly rising (98000, 177000, 333000, 584640, 1285200, 6122304, 13759200)"),
 "M1.grid_perimeter_r3": ("lineages_m1_fix3_c.py:236-263", "row/column layout, gluing along sides, corner contact and the perimeter as sides belonging to exactly one square all stated: one reading", "square count 5+3L..13+3L: every level different"),
 "M1.inclusion_exclusion_r3": ("lineages_m1_fix3_b.py:168-193", "two-set and three-set facts consistent by construction; 'do both includes all three' stated for three sets", "region size 1..20+8L, three sets from L3, exactly-one/exactly-two asks from L5: every level different"),
 "M1.last_digit_power_r3": ("lineages_m1_fix3_b.py:141-162", "repeated-factor product and modulus stated, range 0..p-1 stated; nested commas in the t>=2 sum text are awkward but parse one way (each term begins 'the product of')", "terms 1 (L0-1), 2 (L2-4), 3 (L5-6); base 2..99+30L, exponent 12..300+100L: every level different"),
 "M1.linear_equation_r3": ("lineages_m1_fix3_a.py:165-181", "operation order stated ('multiplying ... and then adding'); j != k so one solution; sign convention stated", "x range -20-10L..40+20L; two-sided form from L3: every level different"),
 "M1.median_list_r3": ("lineages_m1_fix3_b.py:311-321", "even-count median convention and decimal format stated", "count 7+L..10+2L, values 1..200+60L: every level different"),
 "M1.mixture_r4": ("lineages_m1_fix4.py:108-123", "weights, prices and flat packing per kilogram stated; whole cents by construction; '1 kilograms' is a grammar slip only", "price ceiling 30+6L, packing from L3: every level different (LEVEL_PARAMETER :42)"),
 "M1.painted_cube_r3": ("lineages_m1_fix3_c.py:266-290", "box on a table, bottom painted or not stated, 'exactly f painted faces' asked: one reading", "dimensions 3..30+4L: every level a different range (operand size only)"),
 "M1.percent_change_r3": ("lineages_m1_fix3_a.py:97-114", "each change applied to the price just before it stated; whole cents by construction", "two steps with price 4x(3..60+10L) at L0-2, three steps with price 80x(1..6+L) at L3-6: every level different"),
 "M1.pipes_work_r3": ("lineages_m1_fix3_a.py:227-237", "empty start, steady simultaneous rates stated; net rate positive (drain <= a+b-1)", "rates 2..24+2L, minutes 3..40+5L, drain from L3: every level different"),
 "M1.prime_factors_r3": ("lineages_m1_fix3_b.py:115-135", "each of the four asks defined in the item (divisors counted with 1 and n; distinct primes once; prime factors with repetition, example given)", "n drawn from 97-smooth numbers up to _NMAX[L] (:90): 30000..1600000, every level different"),
 "M1.quadratic_area_r3": ("lineages_m1_fix3_c.py:156-184", "d >= 3 so 'longer side' and 'smaller number' are unique; positive whole root unique", "x 2..150+25L, d range widening with L: every level different"),
 "M1.ratio_share_r3": ("lineages_m1_fix3_a.py:148-159", "order of the ratio and equal parts stated; names distinct (r.sample)", "parts 2 (L0-1), 3 (L2-3), 4 (L4-6); multiplier 2..60+20L: every level different"),
 "M1.rectangle_r3": ("lineages_m1_fix3_a.py:240-256", "perimeter and length relation stated; area whole by construction", "width 2..60+10L: every level a different range (operand size only)"),
 "M1.recurrence_iterate_r3": ("lineages_m1_fix3_c.py:296-332", "rule, position numbering from 1 and worked example (add_index) stated", "positions 6+L..9+2L (two shapes) and 5+L//2..7+L//2 (affine): every level a different mixture"),
 "M1.shopping_r3": ("lineages_m1_fix3_a.py:28-38", "counts, unit prices, payment and decimal format stated; plural slips ('compasss', 'scarfs') do not change the key", "kinds 2+L//2+(L>0), counts 1..6+L, prices 5..99+100(L//2) cents (x5 from L3): every level different"),
 "M1.speed_distance_r3": ("lineages_m1_fix3_a.py:41-73", "total distance or average as total distance over total time stated; average whole by construction", "legs 2+L//2, hours from 1..5+L+n, speeds 20..60+10L, average ask from L2: every level different"),
 "M1.tiered_pricing": ("lineages_m1_pricing.py:61-92", "marginal rates stated ('a higher step does not change what earlier units cost'); rates strictly increasing so the units ask has one answer", "tiers min(1+L//2+(L>=5),3), rate range 8..58+6L, tier sizes 10..40+10L, units ask from L3: every level different"),
 "M1.tip_split_r3": ("lineages_m1_fix3_a.py:117-129", "tip on the bill before tip, equal split stated; whole cents by construction", "people 2..6+L, bill up to 400+100L: every level a different range"),
}
R4_SOURCE_READ = {"M1.average_missing_r4", "M1.clock_duration_r4", "M1.finite_differences_r4", "M1.gcd_lcm_r4", "M1.mixture_r4"}

N3 = ("FAIL under section 8 item 1 of the approved text (read as below; PENDING LEAD REVIEW): the solver's author built its fixtures with the builder's keys printed "
      "(fm1_common.py:42 prints 'ans=' per sample; templates_a5.py:33 prints 'ans=' per example; FINAL_M1.md:7 says the solver was written from samples_L036.txt, templates.txt, asks.txt), "
      "so the fixtures it received carried the author's answers (review note N3). ")
SRC = ("It also read lineages_m1_fix4.py, which holds this lineage's builder and answer line (FINAL_M1.md:7), so it is not a context that has not read the generator's source (section 8 item 1). ")


def main(fx_path, out_path):
    fx = json.load(open(fx_path))
    assert sorted(fx["lineages"]) == sorted(L), "lineage sets differ"
    out = {}
    for lid in sorted(L):
        loc, word, lev = L[lid]
        f = fx["lineages"][lid]
        agree = (f"Coverage: SOLVERS maps this stem (solve_text_a5.py:559-564); recorded agreement 0 key mismatches over 500 per level at seed 2611251 and 1,000 per level at 2611257 for all 29 survivors (FINAL_M1.md:80; check_keys_a5.py:51-55 loops every survivor). "
                 f"Fresh check: {f['items']} items (50 per level), {f['mismatches']} key mismatches, {f['solver_errors']} solver errors, {f['no_unique_answer']} no-unique-answer flags.")
        reason = N3 + (SRC if lid in R4_SOURCE_READ else "") + agree
        out[lid] = {
            "wording": {"result": "PASS", "reason": f"Read {W}{loc} and two items per level (s2m1_samples.out.txt): {word}. No wording defect makes the key wrong or non-unique; the text solver flagged no item of the fresh fixtures as without a unique answer."},
            "levels_distinct": {"result": "PASS", "reason": f"Read {W}{loc}: {lev}. No two levels share one item distribution and the difference is the one the builder states (size or depth), not a relabel."},
            "second_solver": {"result": "FAIL", "solver": SOLVER, "fixtures": f["items"], "mismatches": f["mismatches"], "reason": reason},
            "map": "see map_of_record",
        }
    doc = {"evaluation": "M1", "fixture_seed": fx["fixture_seed"], "lineages": out}
    with open(out_path, "w") as fh:
        json.dump(doc, fh, sort_keys=True, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
