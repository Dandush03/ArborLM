# M0 lineage repair: pilot batch 1 (R1), notes (implementer: Claude Sonnet 5.5; self-checked, not independent review)

Nothing here is a result about any model; no model was run, nothing downloaded. Not Astra review, not human approval.

## Basis and rulings (arbor-lead, Fable 5.2, for the pilot only; none is human approval)

The human lead decided on 2026-11-25 that lineages stay CLUSTERS and M0 is repaired to hundreds of lineages (`docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS.md`). For the pilot the lead ruled:

- Ruling 6: cross-family and cross-part distinctness checks are mandatory, beside (not instead of) section 6.2's within-family 50-pair check.
- Ruling 7: second-solver interface confirmed: structured form + schema doc + a fixture of 20 items per lineage and level; the solver reads only `structured`; registry by lineage id; one module per family. I write no solver. A separate agent writes them, a third audits the pairs.
- Ruling 5: no new threshold is registered. The pilot MEASURES skeleton-overlap and answer-distribution statistics; values may be proposed afterwards, noting they would be set after seeing generator statistics (not any model score).
- Rulings 1, 2, 3, 4, 8 (gate operating point, estimator, items per lineage, lineage target, family count) are not acted on here.
- New-lineage definition: the algorithm, the data structure or the dependency graph must differ; parameter space at least 2,000 distinct items per level (the G = 300 demand is 1,800 per core level); rejection at authoring time.

## What was delivered

- 20 new R1 lineages, 10 intended for part A and 10 for part B (the registered partition is by seed over the final families), in 12 families (4 of them new: containers, elimination, boolean_state, equivalence): `studies/m0/lineages_r1_<family>.py`, registered in their own registry (`lineages_r1_common.PILOT`), NOT in `core.REGISTRY`, because they have no second solvers yet and the existing suite parametrises over the core registry. Ids are `R1.<name>`.
- `studies/m0/lineage_gates.py`: the mechanical gates and measurements (builder signature, operation profile, sentence skeletons, answer statistics, capacity exhibition at the G = 300 demand, fixtures, schema document, per-family checks).
- `studies/m0/manifests/r1_pilot_manifest.json` (per lineage: family, intended part, file, signature, capacity result, fixture hash), `r1_pilot_stats.json` and `r1_pilot_stats_table.md` (the measurements for the 15 old and 20 new R1 lineages).
- For the solver agent: `studies/m0/fixtures/R1_PILOT_SCHEMA.md` and `studies/m0/fixtures/r1_pilot/<id>.jsonl` (140 items per lineage: 20 per level 0 to 6).
- Tests: `tests/test_m0_r1_<family>.py` (12 files) and `tests/test_m0_r1_pilot_gates.py`.
- Time log (scratch, not in git): `experiments/_scratch/m0/pilot_timelog.txt`.

## Attempts, rejections, time (measured; read the caveat)

- Drafted and delivered: 20. Drafted then rejected by a mechanical gate: 0. No lineage failed the capacity gate (all 140 lineage-levels reached 10 x the G = 300 demand), none had an equal signature, none raised in 7 levels x 30 items.
- Rejected at DESIGN time, before a line of code (my own judgement, not a gate), 6: inclusion-exclusion counting (open numeric answers); parity chains (the same procedure as `equivalence_classes`); kin-term composition (ambiguous composition table); topological-order questions (the same procedure as reachability); numeric rank from differences (the same procedure as `event_timeline`); alibi/liar variants (the same procedure as `one_culprit`).
- Cosmetic defects found by reading one rendered item per lineage and fixed (not rejections): "1 blocks/days/dollars", "lamps 3", "is true is false", an awkward "the job of A and B are all finished".
- Wall clock from the tool log: first line to the 20th lineage drafted 07:17:16 to 07:19:11 (115 s, about 6 s per lineage); gate module written 07:19:11 to 07:20:08; first gate run, cosmetic fixes, family and gate tests to 07:21:45. **Caveat: these are tool-visible timestamps; they do not include the design reasoning I did before the first line was written, which I could not clock and which was the larger part of the effort. Per-lineage start/end times were not separately logged (files were written in family batches). Read the 6 s as a floor, not as an authoring cost.**
- Machine time (measured, niced): sampling and building 2,000 items per lineage, median 0.02 s (range 0.01 to 0.06 s) for the new, median 0.03 s (up to 0.23 s) for the old; answer statistics under 5 ms per lineage; capacity exhibition over 7 levels, median 0.17 s (0.09 to 0.37) for the new, 3.7 s in all; fixtures 0.04 s for 2,800 items; the whole `pilot-r1` run (35 lineages) 14.6 s; the 12 family test files 0.24 s together; the gate test file 3.8 s.

## The statistics (full table: `manifests/r1_pilot_stats_table.md`)

- **Answer distribution.** For the 20 new lineages the share of the commonest key divided by the mean chance 1/k is at most 1.25 (`conditional_threshold_rule`; then 1.10, 1.10, 1.09, 1.03, and below 1 for open-ish name lists). Among the 15 old lineages one stands out: `categories_follow`, 2.33 (top key "cannot be determined", share 0.776 against chance 1/3); the next old lineage is 1.10. So this measurement, computed mechanically, separates the known defect from every other R1 lineage by a wide margin. A value for a rule would be chosen after seeing this; a bound anywhere from about 1.3 to about 2.0 separates these 35, so the choice is a judgement, not a result.
- **Sentence-skeleton overlap.** The largest sentence-skeleton Jaccard with any other R1 lineage is 0.19 for the new and 0.17 for the old; no pair shares more than a fifth of its sentence templates. Cross-family and cross-part pairs are included (all 35 against all 35).
- **Builder signature.** All 35 builders have different abstracted-AST hashes (no two are the same code up to names and constants). This catches only literal re-skins.
- **Operation-profile similarity is NOT discriminating.** The weighted Jaccard of operation multisets lies between 0.71 and 0.87 for every lineage's nearest neighbour, new or old; the best-matching pairs are not the pairs I judge similar. I propose to drop it as a gate.
- **Item-skeleton diversity** (distinct skeletons among 400 level-3 items): from 2 to 400 for both old and new; a lineage with a single sentence template scores 2 whether it is good or bad (`order_compare` 2, `elimination_bracket` 2). It measures surface variety of one rule and says nothing about procedure distinctness. Not a gate.
- **Capacity.** All 20 new lineages pass at G = 300 (1,800 per core level, 1,000 per reserve level). So does every old R1 lineage. Because names and numbers count as distinct items under the ADR's wording, the gate is weak for R1-type rules: only small-parameter-space rules (the M1 and R2 failures found before) fail it. It does not measure procedural distinctness.

## Candid assessment of distinctness (my judgement, not mechanical; a separate auditor must repeat it)

Of the 20, I judge about 12 to 14 to be genuinely distinct procedures against each other and the 15 old ones. The mechanical gates did not find the overlaps I see by reading:

- Offset propagation along a spanning tree: `temporal_weekday_shift`, `spatial_relative_directions`, `equivalence_exchange_rates` (and the old `event_timeline`): one procedure in four skins (additive mod 7, 2-D additive, multiplicative, additive).
- Simulating a short operation list on a small state: `containers_stack_piles`, `containers_queue_line`, `tracking_accounts` (and the old `swap_tracking`): one family of procedure, three to four data structures.
- Evaluating a stated formula on given values: `conditional_threshold_rule` with the old `attribute_rule`.
- `kinship_descendants` is the downward counterpart of the old `kinship_ancestor` (a tree walk).

On that reading the 20 yield 12 to 14 distinct procedures, and 35 R1 lineages in all yield about 25 to 28.

## Defects and limits of the pilot (not hidden)

- **Not verified by any independent solver.** Keys are what the builders compute from the same data they print. I read one rendered item per lineage; no separate context checked the wording or the keys. The 20 fixtures x 7 levels are for the solver agent. Until then a key error in a lineage would be undetected by me. Uniqueness of the answer is enforced inside builders by rejection (unique extreme, unique shortest path, forced answers by construction) and is not verified independently.
- **Answer balance.** `conditional_threshold_rule` is 62.6 % "no" although the target is drawn uniformly (rejection at high levels is uneven); not fixed (no threshold exists).
- The intended parts are mine; part B is not yet checked for procedure overlap with part A as ruling 6 requires beyond the signature and skeleton measures above (the judgement above is the only cross-check, and it is mine).
- The first-person reading of "distinct procedure" is subjective; a mechanical test for it does not exist yet (see the operation-profile finding).

## Revised estimate [E] for the full repair (replaces the earlier plan's figures)

Inputs: measured machine times above (negligible: under a minute per 100 lineages for every gate); the tool-visible authoring time (a floor); the judged yield of distinct procedures (12 to 14 of 20, about 65 %, in the FIRST pilot, with the easiest procedures taken first).

- Machine time for 2,400 lineages (600 per evaluation x 4): authoring gates under one machine-hour in all; pools, solvers, fixtures a few machine-hours [E].
- Agent time [E, range]: authoring about 5 to 15 agent-minutes per lineage when the procedure is already decided, plus the design effort of finding a new procedure, which I could not measure; solver 10 to 20; audit 5 to 10. For 2,400 lineages: about 800 to 2,400 agent-hours, if the yield stayed at 65 %. **It will not:** procedures I can state as distinct get scarcer quickly.
- Candid estimate of what is reachable: with several authors and a taxonomy, I think a further 25 to 45 genuinely distinct procedures per evaluation (so about 40 to 75 per evaluation, about 20 to 40 per part) are reachable before new lineages are mostly variants of old ones; reaching 300 per part would need either far more than I can list as distinct procedures or a reading of "distinct" that section 6.2 forbids (mechanical variants share a lineage). I do not expect 300 genuinely distinct procedures per part from hand-writing alone. This is an estimate, not a measurement; a second pilot with different authors would test it.
- What this implies for the design (not decided here): at G of 20 to 40 per part the cluster floor of section 8 applies (the table there: for tau = 0.10, G = 60 reaches 0.058, G = 150 reaches 0.039), so 0.02 and 0.03 margins would be NOT EVALUABLE (UNDERPOWERED) on private parts, which is the registered outcome and not a reason to relax a threshold.

## Not done

No solver, no registration of the pilot lineages in the core registry, no partition seed run over the new families, no pools, no change to any existing file under `studies/m0/` other than new files, no threshold.
