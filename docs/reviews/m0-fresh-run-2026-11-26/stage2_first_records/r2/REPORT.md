# M0 stage 2, record of conditions for R2 (17 survivor lineages)

Auditor: arbor-auditor, Claude Opus 5.5 (model id `claude-opus-5-5`, from session metadata). Independent engineering evidence; not Astra validation, not human approval. I wrote none of the lineages, rule scripts, run copies or the solver. Nothing here registers a lineage. Astra review: NOT_PERFORMED.

## Counts (`stage2_conditions_r2.json`, SHA-256 in `SHA256SUMS.txt`)

| Condition | PASS | FAIL |
|---|---|---|
| wording | 17 | 0 |
| levels distinct | 17 | 0 |
| second solver | 0 | 17 |
| map / pair audited | not mine: `"see map_of_record"` | |

**Second solver FAIL, all 17, one reason:** section 8 item 1 is not shown. `final_r2/f_solver.py` covers all 17 (including `to_base_wide`), reads only the question, was written by a context separate from the builder's, agrees on every recorded item (FINAL_R2.md:31: 0 of 133,000) and on every one of my 5,950 fresh fixtures (0 mismatches, 0 errors). But its author wrote it from `f_render.out`/`f_shapes.out` (f_solver.py:3), and `f_render.py`:20 and `f_shapes.py`:33 print the generator's key beside every item: the fixtures it received carried the first solver's answers, which item 1 forbids (review note N3). That its author did not read the generator's source is not recorded either. **PENDING LEAD REVIEW:** under the brief's shorter wording ("written from the item text alone by a separate context … agrees on every fixture") the result would be PASS for all 17 with 0 mismatches. I applied the approved text (COMMON.md: the specification governs). Section 8 item 2 already expects second solvers to be rewritten under item 1 before registration; a rewrite from answer-free fixtures, before the fresh run, would settle it.

## R-40 points decided (R2 only)

- **`dictionary_rank` level 1 → 2: PASS (levels distinct).** Criterion: ADR-0033 §6.2 "levels (depth, steps or program size)". L1 words have 4 letters and L2 words 5 (`_DR_PLAN`, lineages_r2_fix3.py:293). That is one more position in the mixed-radix rank/unrank, so the supports are disjoint. The list size rises only from 6,966 to 8,120 on average because the alphabet falls from 10.5 to 8 letters. The R-40 note rests on that difficulty measure, and a doubt about difficulty is not a ground for failing. The thinnest step in this lineage is in fact L0 → L1, which the R-40 note does not name. Both levels have 4 letters; L1 adds a 12-letter alphabet, so the two item distributions are 1/4 apart in total variation. That is a real size difference, not a relabel and not one distribution, so PASS, reported here.
- **`from_base` texts shared across levels: not a failure of levels distinct; PASS.** Digits = 3+L+U{0,1,2} (lineages_r2.py:109), so each level adds exactly one Horner step on average. The base set widens at L2. Adjacent supports overlap (L0/L1 differ by 1/3 in total variation), so the same text can occur at two levels, but no two levels have one item distribution. Whether a text repeats across levels is a question for item uniqueness and disjointness. `draw_items`' text set (core.py:166-191) and the distinct-item key handle that, not this condition. Whether ADR-0033's "Items are unique after normalisation" should also bind across levels inside one pool is a pool-construction question for the lead; I did not decide it.
- Other R-40 points (R1 Venn 0/1, M1 `gcd_lcm`, C1 `slices_f4`/`binary_search_f3`) are not R2's and I decided nothing on them. Of those, M1 `gcd_lcm`'s false general rule and C1's within-shape rates are about cheap-rule rates, not levels. They belong to the fresh run.

## Other facts a reader needs

- `to_base_wide` (levels distinct, PASS): the exact expected number of division steps is 5.229, 6.200, 6.182, 7.036, 7.865, 8.685, 9.558 for levels 0–6 (`s2r2_levels_exact.out.txt`). It is flat, −0.018, at L1→L2, because bases 11–16 enter there. For every base common to both levels the steps rise, and the dividend is 4× larger. I passed it on input size and the base set, and report the dip.
- Wording notes (all PASS): `grid_sum` asks for the diagonal of a non-square grid on 54/350 fixtures, and "(cells (1,1), (2,2), and so on)" defines it as i = 1..min(rows, cols). `count_divisible` gives a different answer under the set-of-values reading on 108/350 fixtures, and the fix-4 clause settles it. `luhn_check`'s numbers all have odd length (noted in FINAL_R2.md:38), which does not make the wording defective.

## Method and environment

- Fixture seed `int.from_bytes(sha256(b"400002|stage2-check|R2")[:8], "big")` = **5773622561510341714**. I checked it with a second derivation (`python3 -I -c …`). It is not among the 109 integers of `addendum1_rev6_fresh_run.out.txt`, which hold the run seeds, the dry-run seeds and the bases. The stream per lineage and level is `random.Random(int.from_bytes(sha256(f"{S}|{lid}|{L}")[:8], "big"))`. There are 50 items per level through `core.build_item` on `r2_fix4_set.fix4_set()[lid]`, 350 per lineage and 5,950 in all. Only `it.question` goes to the solver, and answers are compared by exact string equality: format-only differences count as mismatches (there were none). No run seed or dry-run seed was used, no run unit was executed, and no cheap rule was computed.
- Commands, run from the implementation worktree root (HEAD `128a02a7`; generators unchanged since `7cd0ac5a`). uv 0.12.15 and `uv run --locked python` = Python 3.12.14, Apple arm64.
  - `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python <D>/s2r2_check.py studies/m0/manifests/survivor_list_of_record.json docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_solver.py <D>` → `s2r2_check.out.json`, `s2r2_check.out.txt`, `s2r2_examples.out.json`
  - The same with `PYTHONHASHSEED=4242` into `<D>/repro_h4242/` gave a byte-identical `s2r2_check.out.json` (cmp).
  - `python3 -I <D>/s2r2_levels_exact.py` (Python 3.15.1, standard library only) → `s2r2_levels_exact.out.txt`
  - `python3 -I <D>/s2r2_record.py <D>` → `stage2_conditions_r2.json`. I ran it again into `<D>/rerun_record/`, and the SHA-256 is identical.
  - `<D>` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_stage2_r2_20261126/deliver`.
- What I read: the approved addendum at `2c944302` (§0, §1, §2, §4A stages 0–2 and 1S, §8, §12 item 16); ADR-0033 §6.2; LEAD_RULINGS_7 R-40; LEAD_RULINGS_8; the survivor list; the builder code and helpers (REASONS.md); `final_r2/f_solver.py`, `f_keys.py`, `f_render.py`, `f_shapes.py`, `f_phrases.py`; FINAL_R2.md lines 1–40.

## Departures and exposures, recorded

- **I was shown past figures by accident.** A `grep` over FINAL_R2.md printed lines that hold cheap-rule figures and level/capacity figures (lines 36, 43–44, 55–56, 61–65, 80–93, 108–110, 121), and I printed the first 5 lines of `f_keys_1000_k1.out`, a past output (key agreement only). None of these entered a judgement. Every condition here rests on code and my own fixtures; the two R-40 figures I quote, 317 shared texts and the L1→L2 list-size note, are the specification's own text.
- `FINAL_R2.md` is a past report. The brief directs it to be read for solver coverage and agreement, and I read it for that.
- Left in the scratch folder: `repro_h4242/` and `rerun_record/`, the reproduction copies. Nothing was deleted or moved. No file in any worktree was written. No process remains running.

## Not established

- Whether the final R2 auditor read the generator's source. This is not recorded anywhere I read.
- The pair audit (the third context of section 8) and the place in the map are not mine.
