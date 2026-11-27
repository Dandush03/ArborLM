# M0 stage 2, evaluation M1: record of conditions (29 survivor lineages)

Auditor: arbor-auditor, run as Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. Independent engineering evidence, not Astra validation and not human approval. It registers nothing and computes no cheap-rule rate.

## Result

| Condition | PASS | FAIL |
|---|---|---|
| wording | 29 | 0 |
| levels distinct | 29 | 0 |
| second solver | 0 | 29 |
| map / pair audited | not mine: `"see map_of_record"` for all 29 | |

Record: `stage2_conditions_m1.json` (SHA-256 in `SHA256SUMS.txt`). Fixture seed `int.from_bytes(sha256(b"400002|stage2-check|M1")[:8], "big")` = **5990891648193313146** (not a run seed, not a dry-run seed).

## Second solver: why every lineage fails (PENDING LEAD REVIEW on the reading)

The only text-only solver for M1 is `docs/reviews/m0-lineage-decision-2026-11-25/final_m1/solve_text_a5.py` (final check of 2026-11-25). It covers all 29 stems (`:559-564`) and agrees with the builder keys: 0 mismatches recorded over 304,500 items (`FINAL_M1.md:80`), and **0 mismatches, 0 solver errors, 0 no-unique-answer flags in my fresh 10,150 items** (50 per level per lineage). Agreement is therefore not the problem. Independence under section 8 item 1 of the approved text is:

1. **All 29, review note N3** ("the fixtures it receives carry no answer from the first solver"). The solver's author wrote it from `samples_L036.txt`, `templates.txt` and `asks.txt` (`FINAL_M1.md:7`). The first two were printed with the builder's key beside every item (`fm1_common.py:43`; `templates_a5.py:36`; 87 of the 87 item headers in `samples_L036.txt` carry `ans=`; I counted lines only and read no figure). I read N3 by its purpose (review 1: "second-solver authors should get fixtures without first-solver answers"): the builder's key is the author's answer, the same answer the author's first solver reproduces. A literal reading ("from the first solver", as distinct from the generator) would not catch this. The approved text governs and I cannot show the condition under the purposive reading, so the rule "PASS only if you can show it" gives FAIL. **PENDING LEAD REVIEW.**
2. **Five lineages, the source read.** The author read `lineages_m1_fix4.py` "which includes the six r4 builders and their answer lines" (`FINAL_M1.md:7`). Five of them are survivors: `average_missing_r4`, `clock_duration_r4`, `finite_differences_r4`, `gcd_lcm_r4`, `mixture_r4`. Section 8 item 1 requires a context "that has not read the generator's or the first solver's source". These five fail on that alone, under either reading of N3.

Section 8 item 2 already expects the existing second solvers to be "rewritten under item 1 before registration"; this solver predates the approved text. Whether a new solver is written before the hash is the lead's decision, not mine. If the lead rules N3 does not reach builder keys, the five of point 2 still fail and the other 24 would pass on this evidence.

## The R-40 points

- **M1 `gcd_lcm` (mine). Decided: levels distinct PASS.** Reason, from code: `GCD_LCM_TABLE` (`lineages_m1_fix4.py:51`) gives k = 2, 2, 2, 3, 3, 4, 4 values with (top, gmax) widening inside each k, and the answer ceiling `gcd_lcm_ceiling` rises strictly: 98,000; 177,000; 333,000; 584,640; 1,285,200; 6,122,304; 13,759,200 (`:54-57`, computed by hand from the table). No two levels share a distribution and the stated difference (more values, larger values) exists. The "false general rule exact at levels 3-6" is, by algebra on the construction (`:186-191`: pairwise coprime cofactors), the two-number identities gcd·lcm = product extended to k numbers (lcm = product / gcd^(k-1), gcd = product / lcm^(k-1)), which hold on every item by construction. That is a question about a rule that gets the answer without the procedure, i.e. a cheap rule. It belongs to the fresh run under section 7, not to "levels distinct"; I decide nothing on it and computed no rate for it. The "mean log answer dips from level 2 to 3" in R-40 is a difficulty observation; under the brief a lineage is never failed on a doubt about its difficulty.
- **R1 Venn levels 0/1, R2 `dictionary_rank` and `from_base`, C1 `slices_f4` and `binary_search_f3`:** not M1 lineages; not decided here. (The C1 point is a within-shape cheap-rule rate and belongs to the fresh run in any case.)

## What I could not establish

- Which model wrote `solve_text_a5.py`: the report's header says Claude Opus 5.5; I have no session metadata for it.
- Whether a third context audited the solver pair (section 8 item 1): that is the "pair audited" field, not mine.
- That `samples_L036.txt` and `templates.txt` are the exact files the author used: I rely on `FINAL_M1.md:7` and the committed scripts.

## Discrepancies and my own slips

1. Attempt 1 of the record (`../deliver/stage2_conditions_m1.json`) cited three solver-side line numbers wrongly (`fm1_common.py:42`, `templates_a5.py:33`, `check_keys_a5.py:51-55`; correct `:43`, `:36`, `:48-55`). The results were the same. The brief forbids editing any file, so attempt 1 stays and this folder (`deliver_r2/`) holds the corrected set; `../deliver/SUPERSEDED_BY_deliver_r2.txt` says so. **The record to hash is `deliver_r2/stage2_conditions_m1.json`.**
2. Before making my scratch folder I wrote one stray file outside it: `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/adr_tmp_view_m1auditor.md` (a copy of the approved ADR text from `git show 2c944302:...`). It is a leftover; not deleted.
3. Figures seen but not used: reading code I saw past cheap-rule figures in the `NOT_REGISTERED` reason strings of `lineages_m1_fix3.py` and `lineages_m1_fix4.py` (lineages not on the survivor list), the C1 within-shape rates quoted in the ADR's section 12 item 16, and the key and wording summary lines of `FINAL_M1.md` (lines 24-25, from a grep). None informed any judgement. I did not open `FINAL_M1.md` sections 1, 2, 4, 5 or 6, any capacity or rule output, the class table, or the amendment audit.

## Environment and commands

macOS (Darwin 27.2.0, arm64); uv 0.12.15; Python 3.12.14 via `uv run --locked`; system `python3` (stdlib only) for the JSON builder. Implementation worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` at `128a02a7`, read only (`git status` before and after shows only the two pre-existing `.bak` files plus other agents' `studies/m0/fresh_run/`, which I did not read). `D` = this folder.

```sh
cd /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python $D/s2m1_fixtures.py $D/s2m1_fixtures.out.json   # log: s2m1_fixtures.log
PYTHONHASHSEED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python $D/s2m1_fixtures.py ../work/fixtures_hash1.json  # cmp: identical
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python $D/s2m1_samples.py 2 > $D/s2m1_samples.out.txt
cd $D && python3 -I s2m1_build_json_r2.py s2m1_fixtures.out.json stage2_conditions_m1.json   # run twice, cmp identical
```

Fixture streams: `core.stream(5990891648193313146, "stage2-check", "M1", <lineage id>, <level>)`, items by `core.build_item`, ids `s2m1/<lineage>/L<level>/<i>`. Example items for reading use the label `stage2-read`. No run seed and no dry-run seed was used; no rule script was executed.

Astra review: NOT_PERFORMED
