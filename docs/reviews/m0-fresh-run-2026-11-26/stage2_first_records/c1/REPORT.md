# M0 stage 2, record of conditions for C1 (26 survivor lineages)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`), `arbor-auditor` role, from this session's model metadata. Independent engineering evidence only. **Not Astra validation, not human approval.** I wrote none of the lineages, rule scripts, run copies or the solver checked.
- Specification: ADR-0033 addendum 1 as approved (`2c944302` on `claude/m0-spec`), section 4A stage 2, sections 1, 2, 7, 8, 12 item 16; `LEAD_RULINGS_7.md` R-40; `LEAD_RULINGS_8.md`.
- Code read: implementation worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `128a02a7`; `git diff 7cd0ac5a HEAD -- studies/m0/*.py` is empty. Untracked `studies/m0/fresh_run/` was not read or touched.
- Record: `stage2_conditions_c1.json`, SHA-256 `aa583b13e48803df750ee396e67c9cd9630b8f7933911ead6e5d1749bc1c6b80` (rebuilt a second time byte-identical).

## Counts (26 lineages)

| condition | PASS | FAIL |
|---|---|---|
| wording | 26 | 0 |
| levels distinct | 26 | 0 |
| second solver | 0 | 26 |
| map / pair audited | not mine: `see map_of_record` | |

Every FAIL has the same single reason: the second solver's authorship (below). On the fixtures, 0 mismatches in 9,100 items.

## Second solver (the reason for all 26 FAILs)

- **Solver of record for C1**, as the brief names it: the final auditor's `docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f2_keys.py` (committed at `b78e58b1`, SHA-256 `be5f1bf993acf6aa50aee4fbef1841bd9d577443c0fec3dbba7111435b6fa69a`). It takes the program out of the item text, using the fixed frame, and runs it in a fresh `python -I -S -c` subprocess under two interpreters. It imports nothing from `studies/` (f2_keys.py:13). It works on any item in the C1 frame, so it covers all 26 lineages. Recorded agreement: 0 / 94,500 over 27 lineages, 3,500 per lineage (FINAL_C1.md:28-31 and the table at :54-80).
- **My fixture check.** Seed `int.from_bytes(sha256(b"400002|stage2-check|C1").digest()[:8], "big")` = **10594161246369239290**. This is not a run seed and not a dry-run seed. My labelling: `core.stream(S, "<lineage id>", "<level>")`. 50 items per level per lineage come from `core.build_item` on `all_written()[id]`, which gives 9,100 items. Running f2_keys.py **unmodified** gives: **0 mismatches**, 0 frame failures, 0 errors or timeouts, 0 stderr, 0 static flags, 0 disagreements between interpreters (CPython 3.12.14 with PYTHONHASHSEED 0; 3.15.1 with 2718281), and the program in the text equals the rendered program in every item. Mismatching item ids: none. I rebuilt the fixtures under PYTHONHASHSEED 12345 and got identical per-file SHA-256s.
- **Why FAIL anyway.** Section 8 item 1 requires the second solver to be written by "an `arbor-auditor` that has not read the generator's or the first solver's source". Section 8 "Registration" and stage 2 require "a second solver under item 1". The record shows that the final C1 auditor read both: it audited the C1 code (FINAL_C1.md:3-12), and its own draw script wraps `lineages_c1._finish`, which computes the key (final_c1/f1_draw.py:53-77). Its report also says "No second solver (my key check is an independent re-execution, not a tree walker)" (FINAL_C1.md:218). The brief calls it an "independent tracer/interpreter", and the report does not support that description. Under "PASS only if you can show it", the authorship cannot be shown, so the condition is FAIL. Agreement is fully shown, and it is recorded in the `fixtures`/`mismatches` fields.
- **PENDING LEAD REVIEW.** (a) If the lead rules that this solver meets section 8 item 1, the 26 `second_solver.result` fields become PASS and nothing else changes. (b) The alternative is to have a context that has not read the C1 generators, `c1grammar.py` or `lineages_c1._finish` write a C1 second solver before the stage-2 hash. (c) The same authorship question probably applies to the text-only solvers of R1, R2 and M1 (the `b78e58b1` commit calls all four "text-only second solvers"). I did not read those, and they are not mine to decide.
- **What agreement can show for C1.** The builder's key is CPython executing the rendered program with restricted builtins (c1grammar.py:129-141). The checker is CPython executing the text. Agreement therefore confirms that the text matches the structured program, that output is deterministic across processes, hash seeds and two interpreter versions, and that the restricted builtins have no effect. It does not test Python semantics independently, because for C1 the key is defined by them. An implementer-written tree walker exists (`studies/m0/solvers_c1.py`). Under section 8 item 2 it does not count, and I did not use it.

## The R-40 points

- **C1 (mine): within-shape rates in `slices_f4` (sum shape) and `binary_search_f3` (probes shape).** This point concerns a cheap rule's rate, not the levels. It belongs to the fresh run (section 7 items 2 and 9: within-shape rates are reported and not counted). **I decide nothing on it.** On the levels themselves, from code: `slices_f4` string length is 10, 11, 15, 16, 20, 21, 25 (all 7,568 PSEUDO words have 5 letters) and the list length is 6 + level, so levels are distinct. `binary_search_f3` list length is 12, 14, 16, 20, 26, 34, 48, so levels are distinct.
- **R1 Venn levels 0/1, R2 `dictionary_rank` and `from_base`, M1 `gcd_lcm`.** These belong to the other evaluations' stage-2 auditors. They were not decided here.

## Levels distinct: the rule applied, and the weak steps

PASS if every adjacent step changes the item distribution through a parameter that the builder states, moving the way it states, with no level a relabel of another. This is the standard of section 7 item 5 (c): "distinct items, difficulty rising by a stated parameter". All 26 meet it. Some steps change only literal ranges and leave the program skeleton the same. They are reported, and no lineage is failed on them, because "a lineage is never failed on a doubt about its difficulty":

- `func_branch_f4`: L0→1, L3→4 and L5→6 change only literal ranges.
- `func_compose_f4`: L0→1, L3→4, L4→5 and L5→6 change only literal ranges.
- `euclid_gcd_traced_f3`: L0→1, L1→2, L2→3 and L4→5 change only operand ranges, and the minimum round count stays the same.
- `circle_elimination_r2`: L0→1 — level 1 is exactly level 0's n = 10 half.

Whether literal-range-only steps meet the brief's gloss "a real difference in the procedure's size or depth" is **PENDING LEAD REVIEW**. Under the approved text they pass.

## Wording

Every item uses one fixed frame that states the question (the exact printed line) and the answer form (one line). Each program carries every constant. Each key is the deterministic output of a one-print program, and the shared finish refuses keys the scorer would change. The fixture check above confirms this for every item. I read one item at level 0 and one at level 6 per lineage (`s3_examples_L0_L6.txt`) and checked six keys by hand. I found no wording defect. Python-defined hazards (negative `//`, `%`, slice bounds) are fixed by the stated language.

## What I could not establish, and departures

- The authorship of the C1 second solver (above).
- The levels decisions come from reading code, as instructed. I made no distributional measurement of the levels.
- **Past figures seen.** The brief sends me to FINAL_C1.md, and that report carries cheap-rule figures. LEAD_RULINGS_7 R-40 and the spec also quote figures. I read them while reading those files. None of my conditions uses a rate, and no lineage was failed or passed on one.
- **A file outside my named directory** (my error): `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_adr33a1_c1_audit_spec_view.txt` is a copy of the approved spec text, written by an early command before I created my directory. It is left in place; I deleted nothing.
- I made no write in any worktree, ran no run seed or dry-run seed, executed no rule script and computed no cheap-rule rate. No subprocess of mine is left running (checked with `ps`).

## Commands (cwd = implementation worktree root; `$D` = `experiments/_scratch/m0_fr_stage2_c1_20261126`; uv 0.12.15, venv CPython 3.12.14, macOS arm64)

```
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python $D/deliver/s0_locate.py > $D/deliver/s0_locate.out.json
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python $D/deliver/s1_fixtures.py $D/work/fixtures
PYTHONHASHSEED=12345 PYTHONDONTWRITEBYTECODE=1 uv run --locked python $D/deliver/s1_fixtures.py $D/work/fixtures_repro_hs12345   # identical per-file hashes
PYTHONDONTWRITEBYTECODE=1 uv run --locked python docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f2_keys.py $D/work/fixtures 50 $D/deliver/s2_f2keys_result.json .venv/bin/python3.12:0 /opt/homebrew/bin/python3.15:2718281 10
python3 -I $D/deliver/s3_examples.py $D/work/fixtures 0,6 1 > $D/deliver/s3_examples_L0_L6.txt          # python3 = /opt/homebrew 3.15.1, stdlib only
python3 -I $D/deliver/s4_assemble.py $D/work/fixtures $D/deliver/s2_f2keys_result.json $D/deliver/s3_examples_L0_L6.txt $D/deliver/stage2_conditions_c1.json
python3 -I $D/deliver/s5_reasons.py $D/deliver/stage2_conditions_c1.json $D/deliver/REASONS.md
```

Astra review: NOT_PERFORMED
