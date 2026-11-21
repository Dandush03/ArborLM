# P10-I-S2 Part Q, attempt 3: audit of a7611cd (and of the addendum)

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I wrote none of the audited code.
- **Object.** `git diff 931a1c2 a7611cd`, read by commit only. 931a1c2 equals freeze `55017df` plus the Decision 2 file.
- **Scratch.** `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-a3/` holds the archive, my scripts and their outputs. I made a `git init` there, in my own scratch, so that the prompt check's committed-record test runs. No project repository was written.
- **Limits observed.** One process at a time, `timeout` on everything, no network, no `/tmp`, no teacher generation.
- **Read-only access to attempt 2** (`experiments/P10IS2-Q-registered2-20261118`):
  - `outputs/gloss_test.json`;
  - the `keys` lists of `outputs/teacher_{A,B}/{E_A,E_B,D_cal}` batch files;
  - **bytes only** (SHA-256 by the code's own `reuse.hash_files`) of the six reused stages.
  - Nothing of `qfit/`, `qcheck/`, `generation/` or `sealed/` was parsed.
- **Not written:** attempt 2's run directory, the live ledger, the preserved copy.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdicts

**READY AFTER THE LISTED FIXES** (R1–R3 below) for the counting rehearsal and the freeze.

**REUSE CERTIFIED** for stages inputs, partition, qfit, qcheck, generation and regeneration, under the condition stated in R3.

## 1. The amended segment rule (`gloss.py`, `step8.step_gloss`, `real_stages.stage_outputs`, `scoring.gloss_icl_ids`)

All checks below use my own BPE (`own_bpe.py`, validated in REAUDIT4 on all 144 recorded P10-S2 windows), with the study's code injected with my tokenizer object (`a3_prompts.py`, output `out/a3_prompts.txt`).

| Check | Result |
|---|---|
| Every E_A, E_B and D_cal item of attempt 2's panels, every in-vocabulary word given a line, 14 gloss rotations (the three real glosses of the recorded prompt; letter, digit-initial `7th`/`230`/`10`, accented `été`/`ß`/`ça`, apostrophe and hyphen forms as `normalize` writes them, one-letter words): **42,000 prompts** | **My own implementation of the rule, written from the addendum's text: 0 mismatches. The study's code (`gloss_bank` + `icl_prompt_ids`, then the first task piece): 0 mismatches.** |
| The study's `tokenization_test_a` over the 3,000 prompts | 0 mismatches |
| The **old** rule on the same E_A prompts | 1 mismatch (the attempt-2 item) |
| The recorded attempt-2 prompt (decoded from its whole-string ids, `' ill = werde\n wait = warten\n till = geöffnet\n 23'`) | Byte-identical to the amended code's `icl_prompt_text`, so the **prompt text is unchanged**. The amended ids equal the whole-string tokenization |
| The last newline | Decided by `last_newline_rule` from the tokenizer and the first task piece `"English:"` of every item: **own-segment**, recorded in the bank |
| Nothing dropped | `icl_lines` is unchanged. `gloss_icl_ids` returns the unchanged task ids when there are no lines, as before |

**Why the rule is sound by construction.** Gloss and source words are `normalize`d word types: letters and digits, no whitespace, no punctuation. Every stored segment except the post-newline one starts with a space, and the regex never joins across a space. The only cross-segment fusion is newline-then-space, which the amended rule now stores as one call.

**What Part T reads that changes.**
- The bank gains `source_words` (now filled from the vocabulary), `source_words_after_newline` and `last_newline`.
- `scoring.gloss_icl_ids` uses them, and feeds only the R-gloss-icl baseline (`baseline_reads`, hence the AGAINST-LOOKUP line).
- The R-gloss-icl baseline uses S0 with no store, so no store addresses are involved.
- Unchanged: truncation limits (D_cal references), the ExampleBank's keys, the task-prompt segments and the scoring of other arms. The last newline is own-segment, so the task ids are untouched.
- Part T reads `outputs/gloss_bank.json` as the raw bank: `step_gloss` writes an envelope, then `stage_outputs` overwrites it with `write_json(gb)`. That is consistent with `partt_real`.

## 2. The pre-freeze prompt check (`partq_prompt_check.sh`)

- **Run once** from my scratch repository: **exit 0 in 127 s**. Items checked 3,000 (E_A 1,000, E_B 1,000, D_cal/A 500, D_cal/B 500), **0 mismatches**. Gloss sweep: **226,928 reference word types × 2 line patterns, 0 mismatches**. Last newline: own-segment.
- **What it covers:**
  - every in-vocabulary source word of every registered E_A, E_B and D_cal item, recomputed from the corpus and the registered partition seeds (a deterministic recomputation; nothing new is drawn), at its position, with placeholder glosses;
  - every reference word type as a gloss word around letter-, digit- and punctuation-initial probes.
- **What it cannot cover:**
  - the lexicon's real gloss words (teacher outputs);
  - a source word that is FIRST in a real prompt but later in the check, because the check gives every word an entry.
- **Neither gap can fuse.** First-line digit words are equal at the start of the text, and real glosses are `normalize`d types of the same classes as the sweep's (digit-initial, non-ASCII letters; no punctuation, no empty word, no whitespace).
- The registered `outputs` test (a) remains the binding check on the real lexicon.
- **Wording (ADVISORY, addendum §3):** "test (a) run over the registered PROMPT TEXTS" overstates. The check runs over the registered sources with placeholder glosses, because the real texts need the lexicon.

## 3. Reuse: certification of the edits listed as `requires_auditor_certification`

`git diff 55017df a7611cd` (`55017df`..`931a1c2` changes only `DECISION_2_PARTQ.md`). Each edit is judged by whether it could have altered what stages 1–6 computed or wrote had it been in force then:

| Item | What changed | Effect under attempt 2's plan (no `reuse` block, no `charge_before_freeze`) | Ruling |
|---|---|---|---|
| `real_stages.run_stage` | `order_of(plan)` (equal to `STAGE_ORDER` without a reuse block); prerequisites by that order; stage cap read from `plan.data["stage_caps"]` (the same number `plan.cap_seconds` gave); the total check `total − before − charged` with `before = 0` (equal to `led.remaining()`, both pausing at ≤ 0); the `reuse` branch only for `stage == "reuse"`; the end-of-body `verify_block` only with a reuse block | Identical arithmetic and branches for stages 1–6 | **CERTIFIED** |
| `require_prerequisites` | Added the `order` parameter (default `STAGE_ORDER`) and the analysis exception after a failure record | Stages 1–6 unchanged | **CERTIFIED** |
| `write_manifest` | Called only by `outputs` and `analysis`. Optional `reused` summary | Not executed by stages 1–6 | **CERTIFIED** |
| `pkgmanifest.verify_inputs` | New branch only for an input named `reuse` with `source_run_dir` | Absent in attempt 2's plan | **CERTIFIED** |
| `pipeline.hashes_of` | Skips top-level symbolic links. Used only by `write_manifest` | Not executed by stages 1–6 | **CERTIFIED** |
| `build_parser` / `main` | New subcommands (`prompt-check`, `reuse-file`) and arguments (`--reuse-source`, `--charged-ledger` on candidate-plan) | The `work` parser and its dispatch are unchanged | **CERTIFIED** |
| `cmd_registered` | **No change** between `55017df` and `a7611cd` (listed by name only) | — | **CERTIFIED** |
| `REGISTERED_STAGES` | Added `"reuse"` | Stages 1–6 unchanged | **CERTIFIED** |
| `partq_registered.sh` | The `analysis` branch becomes `analysis\|reuse`. The branch for inputs to outputs is byte-identical | — | **CERTIFIED** |
| `make_ctx`, `build_world` | Listed in `MIXED` but **unchanged** | — | **CERTIFIED** |

**The other changed files of the earlier frozen set** are whole-file allowed (`gloss.py`, `freeze.py`, `counting.py`, `plan.py`) or definition-allowed (`step8.step_gloss`, `stage_outputs`). None is executed by stages 1–6: gloss runs only in `outputs`, and the freeze, counting and plan code is never run by a stage. The config differs only in `[stage_caps]` (`reuse_hours`).

**The import-walk files of `55017df`** (`studies/p10s2/**`, `src/arborlm/**`, `configs/p10s2_transfer.toml`, `uv.lock`): I compared all 71 frozen files of attempt 2's plan with `a7611cd`. Only the 12 Part Q files above differ. **All 37 files outside `studies/p10is2/` are byte-identical.**

**Reuse mechanics.**
- `reuse.hash_files` on attempt 2's directory: **25,792 files, 0.62 GiB, 5.3 s** per pass (`out/a3_hash.txt`; bytes only).
- Links go only into the new run directory. Every write of the remaining stages lands outside the linked directories:
  - `regeneration.json` at the top level (not linked);
  - runner manifests in `regeneration/`, `outputs/`, `analysis/` and `reuse/` (not linked);
  - `stages/` and the ledger, which are real directories of the new run.
- `build_world` writes no student file, because it already exists through the link. `step_partition` rewrites nothing, because the record exists.
- Attempt 2's `engineering_failures.json` and `outputs/` are **not** linked, so attempt 3 starts with no failure record.
- `verify_block` runs at the start of the stage (through `verify_inputs` or `link_and_record`) and at the end of each stage.
- The regeneration check runs again; seeds are checked equal (`check_seeds`); the ledger pin is checked (`check_ledger_pin`).

## 4. The ledger

- The preserved copy `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-backups/panel_ledger.before-s6.json` hashes `62f8111614207fec61173af0f91246f1629d744739a4173778af0de293921756`. **This equals the pin of attempt 2's plan.** The live ledger is now `ba14c714…`, extended by S6.
- **Readers of `paths.panel_ledger`:**
  - `stage_inputs`: not run in attempt 3;
  - `command_ledger`: refused in registered mode once a plan exists;
  - `build_candidate`: the pin;
  - `_stored_windows` in `outputs`: reads only owner `P10IS2-partq` windows.
- No other stage reads it.
- **But `configs/p10is2_partq.toml` at `a7611cd` still names the LIVE file** (see R2).

## 5. The three code fixes (`a3_fixes.py`, output `out/a3_fixes.txt`)

| Fix | Result |
|---|---|
| `analysis` after a recorded failure | Allowed in both stage orders, and the label derived is `QUALIFICATION-ENGINEERING-FAILURE`. Refused without a failure record. `outputs` without its predecessor is still refused |
| The cap check subtracts the charge before the freeze | A plan whose total was spent before the freeze gives PAUSED ("cumulative hour cap is spent") |
| The template unit test | `test_the_old_rule_fails_on_a_digit_after_a_newline…`, with 28 tests of the three new files (`test_p10is2_gloss_segment_rule.py`, `test_p10is2_reusecheck.py`, `test_p10is2_e2e_reuse.py`) **passing in 153 s** on the scratch copy |

## 6. Caps of attempt 3

**The conflict.** `caps-config --attempt3 --apply` uses `apply_caps`, which needs every proposal key to read `0.0`. With attempt 2's caps entered, that forces `caps-reset`. Decision 2 of attempt 2 recorded: "`caps-reset` is not used again for this part, and never once a registered record of Part Q exists". Registered records exist. **The implementer's sequence breaks that rule** (R1).

**How they must be set: a separate attempt-3 caps section.** Attempt 2's caps stay as its record; nothing is reset or relaxed. Exact changes:
1. **Config:** a new `[stage_caps_attempt3]` with `reuse_hours`, `regeneration_hours`, `outputs_hours`, `analysis_hours` and `total_hours`, all `0.0`. Drop the `reuse_hours` line added to `[stage_caps]`.
2. **`freeze.cmd_caps_config --attempt3 --apply`:** write only that section, refusing unless all its keys are `0.0`. Never touch `[stage_caps]` or `caps.provisional`.
3. **`planmod.build_plan` / `qplan.build_candidate`:** for a plan with a `reuse` block, store `stage_caps` from `[stage_caps_attempt3]`, so that `run_stage` reads them from the plan as now.
4. **`planmod.verify_plan`:** compare the config section that the plan's caps came from, `[stage_caps_attempt3]` for a reuse plan.
5. **`cmd_freeze`:** compare `proposal_attempt3` with `[stage_caps_attempt3]` (`caps_match_config` on that section).
6. **`reusecheck.CONFIG_FREE_SECTIONS`:** add `("stage_caps_attempt3",)`. Then remove `("stage_caps",)` and `("caps", "provisional")`, so that the freeze refuses any edit of attempt 2's caps.

**The numbers** (`whole-process-v2` from `measure4`):
- projected seconds: reuse 15.2 (the inputs overhead), regeneration 456.0, outputs 626.8, analysis 1.3; sum 1,099.4 s;
- caps by the shared function: reuse 0.01 h, regeneration 0.26 h, outputs 0.35 h, analysis 0.01 h;
- total = the charge so far (15,832.8 + 26,804.0 = 42,636.8 s = 11.84 h, **plus the attempt-3 counting rehearsal's charge once it exists**) + 2 × 1,099.4 s = **about 12.46 h + the counting rehearsal**.

It is lower than attempt 2's 15.15 h because only the remaining stages are projected, which is the rule's reading, not a relaxation.

**Checks against attempt 2's own measurements.**
- Attempt 2's regeneration took **520.4 s against 456.0 s projected (1.14×)**, inside the 936 s cap.
- Attempt 2's outputs had used **819.2 s** before it stopped, already above the 626.8 s projection. Bundle writing and the manifest come after. Expect about 0.9–1.1 × 10³ s against the 1,260 s cap.
- **ADVISORY:** each remaining stage also pays two full hashings of the reuse set (about 11 s warm, more when the cache is cold), which are not in the projection.
  - `analysis` (cap 36 s) will spend about 11 s hashing the reuse set plus about 5 s hashing the bundle. It can end with `within_cap: false`, but it has no inner guard and will not pause.
  - The `reuse` stage (cap 36 s): about 11 s.
  - Consider projecting `reuse` and the hashing overhead from this measured 5.3 s per pass, with a cold-cache factor.

## 7. The attempt-3 counting rehearsal (`run_reuse_counting_rehearsal`)

It runs the same entry point (`partq_registered.sh <stage> <run-dir> - --rehearsal --plan-file <copy>`), one fresh process per stage, in the order reuse, regeneration, outputs, analysis. The forced identity check (one reused file's hash altered in a plan copy) expects exit 75 and no completion record, then the restore.

**Rehearsal-only branches:**
- the rehearsal reuse block also hashes the source's `sealed/` stage records and its candidate ledger, and `link_and_record` **copies** those (rehearsal mode);
- rehearsal seeds, the sealed layout, the candidate ledger;
- `TEACHER_GATED` skipped (`force_generation`).

**Registered-only paths it cannot show:**
1. **The teacher gate** (`gate_outcome`) reading the reused Q records through the links. It reads the same bytes, hash-verified, that let attempt 2 run `generation`, `regeneration` and `outputs`, so it decides the same way.
2. **The preserved ledger** read by `outputs` (R2).
3. **The mode check.** It reads only the new run directory's `stages/` and ledger. The reuse stage writes the reused completion records with `mode = registered`, and attempt 2's own records are never read by the check. **It will not refuse the registered reuse.**

## Findings

**R1 (REQUIRED, code; §6).** Set the attempt-3 caps in a separate config section, without `caps-reset`, as specified in §6 items 1–6. Then build the candidate plan.

**R2 (REQUIRED, config, before the candidate plan).** Set `paths.panel_ledger` to the preserved copy `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-backups/panel_ledger.before-s6.json`. Otherwise the plan pins the live file (`ba14c714…`), `check_ledger_pin` refuses the freeze, and `outputs` would read a file still being extended.

**R3 (REQUIRED, code or record; `reusecheck.confined_diff`).** It compares only the Part Q frozen set at `55017df`. It does **not** compare the import-walk files that the reused stages executed (`studies/p10s2/**`, `src/arborlm/**`, `configs/p10s2_transfer.toml`). They are byte-identical today (checked above). Either make `confined_diff` also compare every entry of the earlier plan's `frozen_files` by hash, which is the simplest fix, or have the auditor repeat this check at the freeze commit. **The REUSE CERTIFIED verdict holds on that condition.**

**ADVISORY:**
- The reuse-set hashing is not in the projections (§6).
- Make attempt 2's run directory read-only (`chmod -R a-w`) before the freeze. Today it is protected only by code and by the `verify_block` hashing.
- Addendum wording, §3 "PROMPT TEXTS" (§2).
- **Addendum open case:** if attempt 3's regeneration re-check finds a token difference, ADR-0025 gives row 1 (QUALIFICATION-ENGINEERING-FAILURE). The addendum does not say that this also voids the reuse, as it would. Worth one sentence.

## Scripts

All are in `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-a3/`, with outputs in `out/`:
- `own_bpe.py` (copied from the stop audit);
- `a3_prompts.py`;
- `a3_hash.py`;
- `a3_fixes.py`.

The prompt check was run with the study's own `studies/p10is2/launch/partq_prompt_check.sh` at `a7611cd`, writing `out/prompt_check.json`.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
