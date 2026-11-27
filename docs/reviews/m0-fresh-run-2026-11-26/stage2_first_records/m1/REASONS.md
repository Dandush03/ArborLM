# M0 stage 2, evaluation M1: what was read, per lineage

Auditor: arbor-auditor, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. Read-only in the implementation worktree `agent-a0c9d741ea96ce52f` at HEAD `128a02a7` (the generator files are byte-identical to `7cd0ac5a`: `git diff --stat 7cd0ac5a HEAD` on them is empty). Paths below are relative to that worktree. `L` is the level.

## Common to all 29 lineages

- Loader: `studies/m0/lineages_m1_fix4.py:285-301` (`load_all`: the r3 set with the five repaired stems replaced by r4, plus `tiered_pricing`); r3 registry `lineages_m1_fix3.py:43-50`, `lineages_m1_fix3_common.py:33-44`; item construction `core.py:157-164` (`build_item`), streams `core.py:26-33`.
- Format sentences: `lineages_m1_fix3_common.py:27-29` (WHOLE, WHOLE_SIGNED, DECIMAL); `fmt_exact` `:56-64` asserts every decimal key is a whole number of cents.
- Items read: `s2m1_samples.out.txt` (two per level per lineage, label `stage2-read`, not the fixtures).
- Wording rule applied: PASS when the question, the answer format and every convention needed for one key are stated in the item, and no wording defect makes the keyed answer wrong or non-unique. Grammar slips that do not change the key are noted, not failed.
- Levels rule applied: PASS when, by the code, no two of the seven levels draw from one item distribution and the difference is the one the builder states (a size or depth parameter), not a relabel. A difference only in operand size counts as a size difference; doubts about difficulty fail nothing (STAGE2 brief).
- Second solver rule applied (section 8 item 1 of the approved text): PASS only if (a) a solver exists from a context that had not read this lineage's generator or first-solver source, (b) the fixtures that context received carried no answer from the author's code (review note N3), and (c) it agrees with the builder key on every fixture (recorded and fresh). Evidence for (a) and (b): `docs/reviews/m0-lineage-decision-2026-11-25/final_m1/FINAL_M1.md:7` (what the solver's author read; written from `samples_L036.txt`, `templates.txt`, `asks.txt`); `final_m1/fm1_common.py:43` (samples printed with `ans=`); `final_m1/templates_a5.py:36` (each template example printed with `ans=`). Evidence for (c): `FINAL_M1.md:80`, `final_m1/check_keys_a5.py:48-55` (every survivor), `solve_text_a5.py:559-564` (29 stems), and my fixture run (`s2m1_fixtures.out.json`).

## Per lineage (builder, wording, levels)

| Lineage | Builder read | Wording (PASS) | Levels distinct (PASS) |
|---|---|---|---|
| M1.ages_r3 | `lineages_m1_fix3_a.py:184-196` | names distinct (`r.sample`); (k+1)b+2t=sum, one solution | younger 3..70+10L, k 2..6+L//2, t 1..15+L |
| M1.arithmetic_series_r3 | `lineages_m1_fix3_a.py:277-285` | day 1, inclusive count stated | days 4..12+3L |
| M1.average_missing_r4 | `lineages_m1_fix4.py:129-142` | marks out of M, exact mean; unique needed mark in 40..M | tests 4+L//2, M=100+10L (`:46`, `:87`) |
| M1.change_ways_r3 | `lineages_m1_fix3_b.py:269-282` | unlimited coins, multisets stated | multiplicity bound 5+2L (target range) |
| M1.clock_duration_r4 | `lineages_m1_fix4.py:148-171` | same day, 24 h, ride time only | legs 2+L//2, waits 5..40+4L, rides 20..110+6L (`:47`, `:89`) |
| M1.consecutive_r3 | `lineages_m1_fix3_a.py:199-209` | count, step, ask, sign convention | count 3+L//2, step 2 from L2, start range by L |
| M1.crt_congruence_r3 | `lineages_m1_fix3_b.py:64-85` | coprime moduli >= 9, least positive solution unique | k 2/3/4 at L0-2/3-4/5-6, modulus caps 60,70,80,36,40,44,48 |
| M1.division_counting_r3 | `lineages_m1_fix3_b.py:351-372` | left-overs, full pallets, fewest buses stated | s=1+L sets every range |
| M1.finite_differences_r4 | `lineages_m1_fix4.py:207-228` | degree stated, m >= degree+3 terms | `fd_ceilings` (`:60-65`), degree 3 from L5, extra term from L3 |
| M1.fraction_remainder_r3 | `lineages_m1_fix3_a.py:132-145` | "of what is left" stated | start bound 3000+500L (operand size only) |
| M1.gcd_lcm_r4 | `lineages_m1_fix4.py:177-201` | gcd and lcm settings unambiguous; "all 2 flash" grammar only | `GCD_LCM_TABLE` (`:51`); ceiling strictly rising (see R-40 in REPORT.md) |
| M1.grid_perimeter_r3 | `lineages_m1_fix3_c.py:236-263` | layout, gluing, perimeter definition stated | squares 5+3L..13+3L |
| M1.inclusion_exclusion_r3 | `lineages_m1_fix3_b.py:168-193` | consistent facts; "do both includes all three" stated | region size 1..20+8L, 3 sets from L3, two more asks from L5 |
| M1.last_digit_power_r3 | `lineages_m1_fix3_b.py:141-162` | product, modulus, range stated; nested commas awkward, one parse | terms 1/2/3 at L0-1/2-4/5-6; base and exponent ranges by L |
| M1.linear_equation_r3 | `lineages_m1_fix3_a.py:165-181` | operation order stated; j != k | x range by L; two-sided from L3 |
| M1.median_list_r3 | `lineages_m1_fix3_b.py:311-321` | even-count convention, decimal format | count 7+L..10+2L, values 1..200+60L |
| M1.mixture_r4 | `lineages_m1_fix4.py:108-123` | flat packing per kg stated; "1 kilograms" grammar only | price ceiling 30+6L (`:42`), packing from L3 |
| M1.painted_cube_r3 | `lineages_m1_fix3_c.py:266-290` | table, bottom painted or not, "exactly f" stated | dimensions 3..30+4L (operand size only) |
| M1.percent_change_r3 | `lineages_m1_fix3_a.py:97-114` | each change on the previous price | 2 steps, price 4x(3..60+10L) at L0-2; 3 steps, 80x(1..6+L) at L3-6 |
| M1.pipes_work_r3 | `lineages_m1_fix3_a.py:227-237` | empty start, simultaneous steady rates; net rate > 0 | rates 2..24+2L, minutes 3..40+5L, drain from L3 |
| M1.prime_factors_r3 | `lineages_m1_fix3_b.py:115-135` | each ask defined in the item | 97-smooth n up to `_NMAX[L]` (`:90`) |
| M1.quadratic_area_r3 | `lineages_m1_fix3_c.py:156-184` | d >= 3: longer side / smaller number unique | x 2..150+25L, d range by L |
| M1.ratio_share_r3 | `lineages_m1_fix3_a.py:148-159` | order of the ratio stated; names distinct | parts 2/3/4, multiplier 2..60+20L |
| M1.rectangle_r3 | `lineages_m1_fix3_a.py:240-256` | perimeter and relation stated | width 2..60+10L (operand size only) |
| M1.recurrence_iterate_r3 | `lineages_m1_fix3_c.py:296-332` | rule, numbering, worked example | positions 6+L..9+2L and 5+L//2..7+L//2 (mixture differs every level) |
| M1.shopping_r3 | `lineages_m1_fix3_a.py:28-38` | counts, prices, payment, format; "compasss", "scarfs" grammar only | kinds 2+L//2+(L>0), counts 1..6+L, price range by L |
| M1.speed_distance_r3 | `lineages_m1_fix3_a.py:41-73` | total or average (defined) asked | legs 2+L//2, hours, speeds 20..60+10L, average from L2 |
| M1.tiered_pricing | `lineages_m1_pricing.py:61-92` | marginal rates stated; rates strictly increasing so the units ask is unique | tiers min(1+L//2+(L>=5),3), rate and tier ranges by L, units ask from L3 |
| M1.tip_split_r3 | `lineages_m1_fix3_a.py:117-129` | tip on pre-tip bill, equal split | people 2..6+L, bill up to 400+100L |

## Second solver, per lineage

All 29: solver `docs/reviews/m0-lineage-decision-2026-11-25/final_m1/solve_text_a5.py`, stem present in `SOLVERS` (`:559-564`); recorded 0 key mismatches at 500 + 1,000 items per level (`FINAL_M1.md:80`); my fresh fixtures 350 items each (50 per level), 0 mismatches, 0 solver errors, 0 no-unique-answer flags. Result FAIL for all 29 on (b): the fixtures its author worked from carried the builder's keys (`fm1_common.py:43`, `templates_a5.py:36`, `FINAL_M1.md:7`). For `M1.average_missing_r4`, `M1.clock_duration_r4`, `M1.finite_differences_r4`, `M1.gcd_lcm_r4` and `M1.mixture_r4` it also fails (a): its author read `lineages_m1_fix4.py`, which holds these builders and their answer lines (`FINAL_M1.md:7`; builders at `lineages_m1_fix4.py:108-228`).

Astra review: NOT_PERFORMED
