# P10-I-R implementation audit (ADR-0029), 2026-11-17

**Auditor:** `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`). I did not write any of the audited code; the `arbor-implementer` subagent (Sonnet 5.5) wrote it under the lead's brief.
**Object:** branch `claude/p10-i-r`, commit `aeac3fd` (worktree `arborlm-consolidation-experiment-2b31c1`), against `docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md` (Decision 1, implementation and rehearsal).
**Status of this document:** independent engineering and mathematical evidence. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.

**Seal attestation (auditor).** I opened no `eval.json` and no checkpoint under `experiments/P10S1-registered-attempt2-20261117`, ran nothing that reads them, and saw no value of `tree_recall_of_exhaustive_top8` or `ivf_measured.recall_of_exhaustive_top8`. I read only committed files of the repository (including `results/p10s1-run-2026-11-17/manifests/train.manifest.json` for its key structure and one task entry, and `studies/p10s1/freeze/plan.json` key `data_manifests`).

## Verdict

**READY FOR REHEARSAL AFTER THE LISTED FIXES** (B1–B3 and R1–R6), followed by a focused re-audit of those fixes before the rehearsal is run.

The scientific core is right: every read (T0, T1, T1w, T2, T3, Tv, F0, I256@512, I64@c) agrees with my own brute-force implementation from the ADR's definitions, T0 equals `S1Memory._top_tree` bit for bit, the fact-level measures and pair statistics agree, the label table, index rule, cell rule, plateau rule, combination and R-CONFIRM agree with my independent oracle except at three readings listed for a ruling, the adapter reproduces P10-S1's `run_job` file for file, and the seal holds on every code path I traced. The defects are in orchestration and memory, and three of them would lose the registered result: the fact-level passes retain autograd graphs (A1 cannot finish at the registered sizes), a worker that refuses on an identity check is recorded FAILED and never re-run (the P10-S1 failure mode), and R-CONFIRM cannot be computed if A2 completes after A1's analysis.

## Environment and commands

macOS 27.2.1 arm64 (Darwin 27.2.0), the locked environment (Python 3.12, torch 2.8.0), one thread, one interop thread, deterministic algorithms on (the platform of record; the miniature's item records report it). Commands run from the worktree root; scripts are in the scratchpad `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10ir-audit/` (not durable; the important ones are reproduced verbatim in the appendix).

| Command | Result |
|---|---|
| `timeout 900 uv run --locked pytest tests/test_p10ir_*.py -q -p no:cacheprovider` | 187 passed, 2 warnings, 101 s |
| `uv run --locked ruff check .` | All checks passed |
| `uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py` (cited file, unmodified) | RESULT: FAIL, 30 problems, every one a hit of ADR-0029's own allocation on `configs/p10ir_routing.toml` or on literals in `tests/test_p10ir_*.py` |
| `uv run --locked python -c "from studies.p10ir import gates; print(gates.seed_gate())"` | passed; extended copy RESULT: PASS, copy SHA-256 `95301b03…2fab3` |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_reads.py` | 4,100 tree queries in 100 read cases, 66 flat, 462 index queries: **0 problems** (attempt 2; attempt 1 below) |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_labels.py` | 200,000 tree, 90,000 index, 32,768 cell, 100,000 combination, 6,561 R-CONFIRM, 20,000 plateau cases: only the three reading classes below (attempt 2; attempt 1 below) |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_grad_memory.py {grad,nograd} {64,256}` | peak RSS growth 220.5 / 841.6 MiB with autograd, 19.9 / 21.9 MiB under `no_grad` (B1) |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_pipeline.py <scratch>/pipe` | rehearsal analysis finds no item (R2); analysis re-run refused (B3); refused worker FAILED and not re-run (B2) |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_analysis_planlabels.py <scratch>/pipe` | with labels from the plan, every replicate is found and is WEAK REFERENCE (R2) |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_adapter.py <scratch>/adapt` | `run_job` and `adapter.run_cell`: model.pt and optimizer.pt identical, every tensor equal (F-OQ and T-OQ, 3 snapshots) |
| `sh <scratch>/audit_refusals.sh` (a `git clone --local` of the worktree in the scratchpad; code from the worktree via `PYTHONPATH`, `--repo` the clone) | every registered refusal fires as designed, except an edit of `studies/p10s1` after the freeze (A6) |

Seeds used by me: 938401–938802 and 938901 (unit-test range) only. No registered seed, no training beyond 32-update tiny cells, no network.

## Findings

### BLOCKING

**B1. The fact-level passes and gate 4 run with autograd on and retain every chunk's graph; A1 cannot complete at the registered sizes.**
`studies/p10ir/reads.py:262-298` (`tree_fact_pass`), `studies/p10ir/gates.py:100-138` (`_collect`, `exactness_gates`), called from `studies/p10ir/items.py:218` and `:242` without `torch.no_grad()`. The checkpoint's `keys` and `router` are Parameters (`requires_grad=True`); `tree_path` normalises gathered key blocks, and the pair statistics (`tv`) and gate-4 score lists keep references to every chunk's output, so every `[rows, v·256, 16]` block of T3/T2 stays alive until the function returns. Measured (16,384 slots, chunk 2^20): 841.6 MiB growth for 256 facts against 21.9 MiB under `no_grad`, about 3.3 MiB per fact, linear (64 facts: 220.5 MiB). Extrapolated: about 27 GiB at 8K/16K and about 100 GiB at 32K/16K; the 3 GiB per-worker guard kills the task (`killed_rss`, PAUSED), and every resume recomputes the same pass and is killed again. The rehearsal's real-size phase would show it, but the study cannot run as written.
Reproducer: `audit_grad_memory.py` (appendix). Fix: wrap the fact passes and gate 4 in `run_tree_item` and `run_flat_item` (or the functions themselves) in `torch.inference_mode()`/`no_grad()`, or pass `keys.detach()`/`router.detach()`; add a test that every returned tensor of the fact pass has no `grad_fn` and a memory-bound test at a moderate size.

**B2. A worker that refuses on an identity or precondition check is recorded FAILED and is never re-run; the ADR requires PAUSED — IDENTITY, resumable after the file is restored.**
`studies/p10ir/stages.py:371-387` (every registered worker re-runs `check_preconditions`, `verify_plan`, `require_decision_2`), `:429-431` (`StageRefused` → exit 2), `studies/p10ir/runner.py:96-101` (non-zero exit → FAILED and a failed record), `:67-68` (a failed record is never re-run), `:125-126` (any FAILED task → stage FAILED). ADR §13: "An identity difference stops a task as PAUSED — IDENTITY; restoring the file bit for bit lets the stage resume." `verify_plan` even says "(PAUSED — IDENTITY)" in its message. The clean-tree check counts any untracked file anywhere in the repository, so writing `DECISION_2_A2.md` (or any note) while A1 runs fails, permanently, every task that starts at that moment; a FAILED `a1` then blocks the analysis (`stages.py:227-229`) and no R-DIAGNOSIS exists. This is the P10-S1 failure (a commit during a registered run made 171 cells refuse).
Reproducer: `audit_pipeline.py` step 3: a task exiting 2 → `failed`, stage `FAILED`; the same task after the cause is removed → `failed - refused: a failed record exists; it is kept and the task is not re-run`. Fix: workers exit with a distinct code on `StageRefused` (for example 75); the runner records `paused_identity` (no failed record) and the stage PAUSED; the next invocation re-runs those tasks. Add a test with a dirty tree during a stage.

**B3. R-CONFIRM cannot be computed if stage A2 completes after A1's analysis.**
`studies/p10ir/plan.py:28` (`analysis` and `report` belong to group A1), `studies/p10ir/stages.py:214-216` (a COMPLETE stage is never re-run), `:305-321` (R-CONFIRM is computed only inside `run_analysis`, NOT RUN when `a2` is absent). ADR §13: A2 "has its own Decision 2, before or after A1's result". If A1's analysis and report run first (the natural order when A2's Decision 2 comes after A1's result), they are COMPLETE with R-CONFIRM-TREE/INDEX: NOT RUN and nothing in the frozen code can produce R-CONFIRM later.
Reproducer: `audit_pipeline.py` step 2: re-running `analysis` → `refused: …/analysis/manifest.json is COMPLETE`. Fix: a separate registered stage in group A2 (for example `confirm`) that analyses A2, computes R-CONFIRM against A1's frozen `analysis.json`, writes its own record and report section, and never rewrites A1's; or a recorded ruling that A1's analysis waits for A2, enforced by code.

### REQUIRED

**R1. Gate 1 is per checkpoint and does not stop the stage; two identity links of §4 are not checked.**
`studies/p10ir/items.py:163-180` and `:219-220`, `:259-260`; `studies/p10ir/stages.py:155-164`; `studies/p10ir/freeze.py:135-149`. ADR §11: "A failure of gate 1, 5 or 6 stops the stage before any new read is computed. Gates 2–4 are per checkpoint." The code (i) records checkpoint identity inside each item with scope tree/f0, so a failure makes a replicate NOT EVALUABLE instead of stopping A1, and in `run_tree_item` the fact pass is computed before the identity gate; (ii) never checks a cell's `train.json` against the committed `results/p10s1-run-2026-11-17/manifests/train.manifest.json` (it holds `result_sha256` per task label; §4: "whose digest is in the committed … train.manifest.json") — the frozen digests are simply the files' hashes on the day of the freeze; (iii) never checks the draws' `data_manifest.json` against P10-S1's freeze hashes (`studies/p10s1/freeze/plan.json` key `data_manifests`; §4 "checked against its freeze hashes"); (iv) regenerates and checks each draw lazily inside an item, where a mismatch raises and fails the task (B2's consequence). Fix: in `gates-a1`, for all 280 checkpoints check model.pt = snapshot.json = train.json entry = plan digest and sha256(train.json) = the committed manifest's `result_sha256`; regenerate the five draws and compare with their manifests and the manifests' file hashes with P10-S1's frozen `data_manifests`; fail `gates-a1` on any difference. Keep the per-item check as a second line.

**R2. The analysis takes cell labels from the config, not from the plan; the rehearsal's analysis therefore examined nothing, and its test accepts that.**
`studies/p10ir/analysis.py:19-27`, `:241-243`; `studies/p10ir/stages.py:310`, `:317`; `tests/test_p10ir_rehearsal.py:137-138`. §13: "every stage derives its items from freeze/plan.json only". In the registered plan the two derivations coincide (`verify_plan` compares items with a re-derivation), but the rehearsal's items carry other initialisation seeds, so its analysis looks up `P_T-OQ_f128_n1024_d1_i2101_u8_y16` while the items are `…_i330698_…`: all 120 replicate labels are NOT EVALUABLE for "no item record", the stage is COMPLETE, and the test's `all("gate" not in x for x in reasons)` passes. With labels taken from the plan (`audit_analysis_planlabels.py`) every replicate is found and every one is WEAK REFERENCE (16-update memories at chance), so even after the fix the rehearsal exercises only row 1. Fix: build `label_of` from the plan's items; make the rehearsal's analysis run on records whose F0 is above the floor (a longer synthetic training or a synthetic registry keyed by the plan's own labels) and assert that rows other than NOT EVALUABLE are reached; make the test fail on "no item record".

**R3. The rehearsal does not run against the frozen plan file. PENDING LEAD REVIEW (ordering).**
`studies/p10ir/rehearsal.py` (three plans of its own), `studies/p10ir/gates.py:295-304`, `configs/p10ir_routing.toml:167-169`. ADR §11 gate 5: "Every stage has run end to end against the frozen plan file itself"; §13 order: rehearsal "against the frozen plan itself" → freeze. The code cannot do that literally (the freeze refuses without a rehearsal record), and the registered plan's own content — 280 + 40 items, `bridge_cells` from P10-S1's frozen plan, `plateau` label lists, the D-OQ `context`, absolute paths — is first exercised by the registered run. Fix (for the lead's ruling): write the candidate `plan.json` first, rehearse every stage against that file in a dry mode (enumerate tasks, items, labels, paths and manifests; run analysis and report on a synthetic registry keyed by its labels), record its SHA-256 in `rehearsal.json`, and make `freeze` refuse unless the file it commits has that hash.

**R4. The accuracy version of the retention ratio is never printed.**
`studies/p10ir/labels.py:340-343` (`accuracy_retained`, unused by `analysis.py` and `report.py`); `tests/test_p10ir_labels.py:324` tests the function only. §8.1: "[acc(X) − acc₀] / [acc(Y) − acc₀] is printed beside it and decides nothing." Fix: print it beside every RESTORED comparison (T1, T3, T2 and each I64@c against F0). acc₀ is not defined in the ADR (chance 1/32, or P10-S1's no-memory baseline of the same panel): PENDING LEAD REVIEW.

**R5. An exception inside one item fails the whole cell task and, through it, the A1 analysis.**
`studies/p10ir/items.py:310-323` (no handling), `studies/p10ir/stages.py:227-229`. A `SealedMissing` from gate 2's or gate 3's reference read, a non-finite tensor in `load_model_state`, or a plan/read mismatch raises; the task (all four checkpoints of the cell) is FAILED and not re-run, `a1` is FAILED and the analysis refuses, so a defect at one checkpoint removes R-DIAGNOSIS instead of making one replicate NOT EVALUABLE (§11: a checkpoint that fails gate 2, 3 or 4 makes its replicate NOT EVALUABLE). Fix: catch per gate and record the gate as failed with its scope (message without values); let the other checkpoints of the cell run; decide (PENDING LEAD REVIEW) whether the analysis may run on an `a1` with failed items, treating them as NOT EVALUABLE.

**R6. Two label readings differ from the ADR's literal text and need a ruling before the freeze.** (Details under choices 8 and "new reading" below.) (a) CELL-DEPENDENT at both checkpoints with different per-cell rows is CHECKPOINT-DEPENDENT in the code, CELL-DEPENDENT on the literal reading of §9 item 3; it changes the printed component and R-CONFIRM (example: tree X = (U_P EXACT SEARCH HARMS, RUN PRIORS), Y = (CONTENT, CONTENT): code CHECKPOINT-DEPENDENT, literal CELL-DEPENDENT; R-CONFIRM-TREE for A1 (PRIORS, PRIORS | PRIORS, CONTENT) against A2 (PRIORS, PRIORS | PRIORS, JOINT): code NOT CONFIRMED, literal CONFIRMED). (b) A cell whose replicates are four MIXED-PANEL and one other is labelled MIXED-PANEL by the code; §8.2 says a MIXED-PANEL replicate "satisfies no condition", which reads as MIXED. Neither recommends an action under either reading.

### ADVISORY

- **A1. Declared re-use list incomplete.** `studies/p10ir/gates.py:207-211`: the identity-gate re-use has 33 values; registry §4.6 lists 38 (2101 with its component seeds 3101–7101). Add the R2 images.
- **A2. Seed ranges not tied to the registry.** `configs/p10ir_routing.toml:157-163` are the registry's ranges, but nothing compares them with the checker's `ALLOC`; part (1) of gate 6 trusts the study's own config. Add a test that parses `ALLOC` rows of ADR-0029 from the cited checker and compares.
- **A3. Registry docstring overclaims.** `studies/p10ir/registry.py:4-5` says a record whose fields do not give the key it is stored under is refused; `load` keys by the record's content only. Collisions are still refused. Either implement the file-name check or correct the text.
- **A4. Adapter has no point-of-use seed check.** `studies/p10ir/adapter.py:68-85` trains whatever `bridge_cells` says; `plan.verify_plan` compares `items` with a re-derivation but not `bridge_cells`, and the label check (`:83`) does not cover `seed_base`. Assert `seed_name`/`seed_base` = `core.bridge_seeds(draw)` and every set value inside the registry's bridge range before training.
- **A5. Rehearsal and tests use the registered I64 index seeds 298001–298003** (on synthetic and rehearsal keys; `items.py:263`). No registered result is observed, but the registry allocates those values to the registered reads; the lead may prefer rehearsal values.
- **A6. Code imported by every read is not in the freeze comparison.** `studies/p10ir/plan.py:274` compares only `studies/p10ir` and the config between the freeze commit and HEAD; an edit of `studies/p10s1/index.py` committed after the freeze passed every precondition (`audit_refusals.sh` step 10). The ADR's frozen-input list does not name P10-S1's code, but it is immutable by policy and gate 2 would not catch, for example, a change to `bits_per_fact`. Extend the comparison to `studies/p10s1`, `studies/p9`, `studies/p9i`.
- **A7. No guard that the run directory is git-ignored.** A run directory inside the repository and not ignored makes the tree dirty at the first write (and, with B2, fails every later task). Refuse such a run directory.
- **A8. Seal hygiene.** `items.py:347` (rehearsal gates 1 and 2 on the registered F-OQ checkpoints) recomputes P10-S1's index-recall quantity before the freeze; it is never written or printed (verified), but pop it at once. `cmd_work --mode rehearsal --run-sealed` with a plan whose `s1_run_dir` is the registered run would call `sealed_equal` before the freeze; refuse `run_sealed` outside registered mode unless `s1_run_dir` is a rehearsal directory.
- **A9. Float32 means.** `reads.py:254-255` averages per-fact measures in float32. At the primary cells CR8 lies on a grid of 1/65,536 or 1/262,144, at least 6e-6 from 0.90, far above the rounding, so R is not affected; compute from integer counts in float64 anyway.
- **A10. `labels.py` compares with a slack of 1e-12** (`ge`, `le`). Harmless (i comes from integer counts); my first oracle without it disagreed only at float boundaries built by its generator. Print the convention in the readings.
- **A11. H reuses `restored_margin_bits`.** `labels.py:152`. Same value (0.25) by the ADR; a separate config key would decouple them.
- **A12. Test quality.** The analysis tests build the registry with the same `default_label_of` that the analysis uses (R2 could not be caught); the rehearsal test tolerates an analysis with no item; the runner test asserts the FAILED-not-re-run behaviour that B2 shows contradicts §13; no test runs a fact pass at a size where memory matters (B1); synthetic prototypes put equal values on both panels except for MIXED-PANEL, so one-panel closure is tested only in `labels` unit tests; `accuracy_retained` is tested as a function, not as printed output. The read, measure, label and gate tests that I re-derived are sound and mostly non-mirrored (they use loops in float64).

## What I checked and found correct

1. **Reads.** My brute force (float64 loops from §3, §6: route = cos/0.2, v best branches with ties to the lower id, prior = log-softmax over all branches, selection score and weight score with the prior on or off, top 8 by score then slot id, softmax weights, read vector Σ w·values) against `reads.tree_path` for T0, T1, T1w, T3, T2, Tv1 on/off and Tv4 on/off on 12 random trees (2, 4, 6 branches; exact duplicate keys within and across branches; duplicate router rows; queries exactly on duplicated keys; router scales 0.02, 1, 25): ids, visited branches, weight scores (2e-5), weights (1e-6) and read vectors (1e-5) all equal; no float-tie skip was needed. T0 equals `S1Memory._top_tree` bit for bit (values, ids, branches). `exhaustive_top` equals `S1Memory._top_flat` bit for bit and my loop; `IVFBudgetMemory` at budgets 128–1,024 with lists N/64 and N/256 equals my own list-visiting loop (lists by centroid cosine, ties to the lower list, until at least c keys) on ids and candidate counts.
2. **Measures.** CR8, CR1, SR8, AM_C, AM_S, share spanning branches, the T0–T1, T0–T1w, T0–T3, T3–T2 changed shares and TV distances, and the index reads' CR8, CR1, SR8 (= CR8, as §7 says), AM_C and candidate means agree with my loops. E8/E1 use the read's own float32 scores and `stable_top`, as §7 requires. `read_counts` goes through P10-S1's `panel_counts` and `bits_per_fact`; on the miniature run every T0, F0 and I256@512 count gate passed bit for bit against P10-S1's own `evaluate_cell` records, as did both gate-3 recomputations (tree recall at U_P, index recall at every checkpoint), on the platform of record.
3. **Labels.** Under the same 1e-12 slack, my oracle and `labels.py` agree on every tree row (first-match order, rows 1, 2, 2a, 3–9, WEAK REFERENCE on either panel → row 1, P/C/J both-panel rule, H, R), the FULLY/PARTLY suffix of rows 4–6, every index label and c\* (sufficiency at c and every larger feasible budget, c\* ≤ 512), the cell rule (2 of 5 NOT EVALUABLE first, then 4 of 5, else MIXED), the plateau rule (i\* = max over snapshots ≤ limit, gain ≤ 0.10, i\*(run/2) ≥ 0.473, 2 of 5), the combination (study-level NOT EVALUABLE, per-component checkpoint rule, actions only for a single row, NO READ-TIME CAUSE IDENTIFIED) and every special value of R-CONFIRM. Since a gap ≥ 0.5 and RESTORED (margin ≤ 0.25) imply g ≥ 0.5, the "RESTORED or g ≥ 0.5" conditions reduce to g ≥ 0.5 on both panels, so the per-panel or whole-replicate grouping of the "or" cannot matter. The floor is `fano_bits_per_fact(0.25)` = 0.4730746, P10-S1's `PLATEAU_FLOOR_I`.
4. **Gates and seal.** Tie definition and tolerances of gate 4 are §11's (8th–9th score gap ≤ 1e-5 in either computation, 0.1% of facts, 1e-6 per slot by id). Gate 2's T0 path check covers every query of both panels, main and swap reads. Gate 3 recomputes each recorded quantity by P10-S1's own code path (`evaluate.tree_recall`; `IVFMemory` over the Panel A pass with the same chunking) and compares through `sealed.sealed_equal`, which returns a boolean only. `sealed.py` is the only module that opens an `eval.json`; the sealed keys appear nowhere else; `read_record` drops P10-S1's recall before writing; gate 3 runs only with `run_sealed`, set only by registered entry points and by the rehearsal's own miniature. The registered entry point refused, in a scratch clone, with an untracked file, without a plan, with provisional caps, without a Decision 2, with an uncommitted Decision 2, with A1's Decision 2 for an A2 stage, with a contradictory Decision 2, with a frozen file edited after the freeze, and without a gates record. The frozen-input set is `studies/p10ir/**` (launch scripts and freeze files included, plan excluded from its own hash), the config, the plan, caps, digests, P10-S1's data manifests and the bridge manifests; the ADR is hashed for provenance only and no check compares it.
5. **Config.** Every threshold and list matches the ADR (§6, §8.1–8.4, §9, §11, §12, §13); seeds match registry §4.2 and §4.6; the seven cells, their U_P, run lengths and trajectory checkpoints match §4; A2 cells, rate and lengths match §10; caps are provisional and the freeze refuses them.
6. **Gate 6.** The cited checker fails by construction (30 problems, all self-hits). The three substitutions exclude exactly `configs/p10ir_routing.toml` and every `.py` file under `src/arborlm`, `studies`, `tests` whose name or path contains `p10ir`, and fix the root. Every six-digit literal in those files is inside ADR-0029's allocation, a declared re-use (210001, 210401) or a size (196608, 393216, 786432); the copy prints RESULT: PASS.

## The implementer's 18 choices

| # | Choice | Judgement |
|---|---|---|
| 1 | Gate 6 as an extended copy with three substitutions | **Right in substance; needs the lead's recorded ruling.** The letter of §5 ("extended with these named values") is not what was done (revision 3 already contains ADR-0029's named values; the copy instead removes this study's own files from the inventory). What the copy still tests: ADR-0029's allocation, R1–R3 expanded, collides with nothing else in the repository, plus the re-use section; the study's own values are checked separately against the configured ranges (see A1, A2). |
| 2 | Floor = Fano(0.25) by P10-S1's function | Right. |
| 3 | A2 plateau NOT CHECKED | Defensible (A2 reads only U_P and the run length; the tag enters nothing); **needs the lead's ruling** because A2 is "the frozen A1 code, with no change of … rule". |
| 4 | A1: missing snapshots fail the plateau check; tags on primary cells only | Right (§9 names the primary cells; failing is the conservative course). |
| 5 | Reference below the floor on either panel → NOT EVALUABLE for that label | Right (§8.1 per comparison, §8.2 both-panels rule, §8.2 counts WEAK REFERENCE as NOT EVALUABLE). |
| 6 | Row 3 FULLY needs T1 and T3 RESTORED on both panels | Acceptable; the suffix enters no comparison. No ruling needed; the lead may confirm. |
| 7 | "mainly weights / selection" on the panel mean | Right (descriptive). |
| 8 | CELL-DEPENDENT equality by per-cell rows | **Needs ruling** (R6a; differs from the literal §9 item 3). |
| 9 | MIXED as a shareable component value | Right (it recommends nothing either way). |
| 10 | Gate 1 on T-OQ voids the tree label, on F-OQ both | Right scope for gates 2–4; **wrong for gate 1**, which stops the stage (R1). |
| 11 | Bit-exact gates skipped off the platform of record; registered runs require it | Right. |
| 12 | Caps provisional; freeze refuses | Right (§12). |
| 13 | Attestations recorded from flags | Right (code cannot verify them). The auditor's attestation is at the top of this file. |
| 14 | Decision 2 at `results/p10ir-freeze-*/DECISION_2_A1.md`, `…_A2.md` | Acceptable procedure; **needs the lead's (or the human lead's) confirmation**, since the ADR names no location. |
| 15 | Sweep aliases (v = 2 is T0/T1, v = N/256 is T3/T2) | Right (§6: T3 and T2 are the path at v = N/256; Tv is "priors on and off"). |
| 16 | Candidate counts printed are Panel A's | Right; the per-fact counts are also stored (`candidates_facts`) and could be printed beside them. |
| 17 | Miniature P10-S1 run under names `p10s1-test-k` with test-range values | Acceptable test device (values 938001+ are this study's); P10-S1's whitelist checks names only. |
| 18 | Helper module `tests/test_p10ir_tiny.py` | Acceptable; it defines no test. A name outside the `test_` pattern would avoid collection. |

**New reading not in the implementer's list:** four MIXED-PANEL replicates make a MIXED-PANEL cell (R6b). Needs a ruling.

## The adapter

`adapter.run_cell` against `train.run_job`, line by line: it omits `check_job_seeds` (intended), `init_snapshot` resume (a bridge cell restarts from scratch after a kill; acceptable, nothing completed is recomputed), the `deadline_epoch` check (never set by a registered stage), `parameter_report`, `psutil` sampling, `updates.jsonl` and P10-S1's `train.json` (replaced by the `bridge_train` record, which carries `snapshot_sha256` for gate 1). None of these touches a generator, parameter or optimizer state. Everything that does — `job_model` (seeds Python's and torch's generators with the initialisation seed), `Trainer(job, model)`, the `stream.batch(update)` order, `Trainer.step`, `snapshot_marks`, the optimizer marks and `save_snapshot` with `trainer.snapshot_extra()` — is called unedited in the same order. My own tiny run (F-OQ and T-OQ, 128 facts, 1,024 slots, 32 updates, test seeds) gave identical `model.pt` files at 8, 16 and 32 updates and identical `optimizer.pt` at 32. **It is a legitimate way to run the bridge cells.** The registered identity gate (8K/4K draw 1, 512/1,024/2,048 updates, `torch.equal` on every tensor and equal `model_sha256` under P10-S1's label) is implemented as §10 states and runs only on the platform of record. Replacing the seed check: gate 6 checks every planned bridge value against the registry's range and the declared re-uses, `verify_plan` checks that the plan's items are the config's derivation, and `train_bridge_cell` verifies the regenerated draw against its frozen manifest; that is adequate at the gate level, but nothing checks the seeds at the point of use (A4).

## Discrepancies that were my own mistakes (kept)

1. `audit_reads.py` attempt 1 reported 36 problems: the pair statistics and candidate means were compared with absolute tolerances (1e-9 and 1e-6) tighter than the float32 means the code computes (differences about 2e-8 relative). Attempt 2 uses 1e-6 (relative for the means); 0 problems. Both versions and outputs are in the scratchpad (`audit_reads_attempt1.*`).
2. `audit_labels.py` attempt 1 (exact comparisons) reported 44 disagreement classes; 26 were at float boundaries built by my generator (for example a gap of 0.49999999999999956 from 2.4185 − 1.9185), where `labels.py` applies a 1e-12 slack. Attempt 2 applies the same slack; the 18 remaining classes are all R6a, R6b and my deliberately different row-3 suffix reading (choice 6).
3. `audit_refusals.sh` prints `exit=0` after each step: that is the exit status of `tail`, not of the driver. The refusal lines are the evidence; the exit code was not captured.

## Appendix: auditor scripts (verbatim)

The scratchpad is not durable; the scripts below are the versions that produced the results above.

### `audit_grad_memory.py`

```python
"""Peak RSS of reads.tree_fact_pass on a 16,384-slot tree whose keys are Parameters (requires_grad, as in a loaded checkpoint),
with autograd enabled (as run_tree_item calls it) or under torch.no_grad(). Usage: audit_grad_memory.py <grad|nograd> <facts>.
Random tensors, test seeds only; nothing written."""

import resource
import sys

import torch
from torch.nn import functional as F

from studies.p9.model import AdditionSpec
from studies.p10ir import reads
from studies.p10s1.model import S1Memory

torch.set_num_threads(1)
mode, facts = sys.argv[1], int(sys.argv[2])
mem = S1Memory(AdditionSpec("learned_tree", 16384, 16, "R1", 64, 0), 938801)
assert mem.keys.requires_grad and mem.router.requires_grad
g = torch.Generator().manual_seed(938802)
q = F.normalize(torch.randn(facts, 16, generator=g), dim=-1)
specs = [s for s in reads.tree_read_specs(16384) if s.name in ("T0", "T1", "T1w", "T3", "T2")]
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if mode == "grad":
    out = reads.tree_fact_pass(mem, q, specs, chunk_elements=1 << 20)
else:
    with torch.no_grad():
        out = reads.tree_fact_pass(mem, q, specs, chunk_elements=1 << 20)
after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print({"mode": mode, "facts": facts, "peak_rss_mib_before": round(before / 2**20, 1), "peak_rss_mib_after": round(after / 2**20, 1), "growth_mib": round((after - before) / 2**20, 1), "cr8_T0": round(out["T0"]["facts"]["cr8"], 6)})
```

### `audit_pipeline.py`

```python
"""Auditor's pipeline reproducers on the implementer's synthetic rehearsal (test seeds 938001-938999, tiny sizes, random backbone).
1. what the rehearsal's analysis stage actually labels (are any replicates found?);
2. whether the analysis can be re-run after A2 completes (R-CONFIRM after A1's analysis);
3. whether a worker that refuses on an identity check leaves the task PAUSED (resumable) or FAILED (not re-run).
Writes only under the scratchpad directory given as argv[1]."""

import collections
import json
import sys
from pathlib import Path

from studies.p10ir import core, rehearsal, runner, stages
from studies.p10ir import plan as planmod

root = Path(sys.argv[1]) / "synthetic"
repo = Path.cwd()
res = rehearsal.run_synthetic(root, draws=5, repo=repo, inline=True)
print("1. stage statuses:", {k: v["status"] for k, v in res["stages"].items()})
full = json.loads((root / "analysis" / "analysis.json").read_text())
reasons = collections.Counter()
rows = collections.Counter()
for stage in ("A1", "A2"):
    for cell in (full[stage] or {}).get("cells", {}).values():
        for ck in cell["checkpoints"].values():
            for comp in ("tree", "index"):
                for r in ck[comp]["replicates"]:
                    rows[(stage, comp, r["row"])] += 1
                    reasons[(stage, comp, r["reason"][:60])] += 1
print("   replicate rows:", dict(rows))
print("   reasons:", dict(reasons))
plan = planmod.Plan.load(root / "freeze" / "plan.json")
print("   plan A1 labels (first 2):", stages.labels_of_stage(plan, "a1")[:2])
from studies.p10ir import analysis

lab = analysis.default_label_of(core.STAGE_A1)
spec = stages._specs_of(plan, core.STAGE_A1)[0]
print("   analysis looks up:", lab("T-OQ", spec, 1), lab("F-OQ", spec, 1))

# 2. the analysis stage is COMPLETE; can it be run again after A2?
ctx = stages.ctx_for(plan, root, run_sealed=True, experiments_root=None)
try:
    stages.execute_stage("analysis", plan, ctx, root, root / "freeze" / "plan.json", repo=repo, workers=1, inline=True)
    print("2. analysis re-run: allowed")
except planmod.StageRefused as exc:
    print("2. analysis re-run refused:", str(exc)[:160])

# 3. a worker that refuses (exit 2, as stages.main returns on StageRefused, e.g. a dirty tree or a frozen file that differs)
t = runner.Task("x", (sys.executable, "-c", "import sys; sys.exit(2)"), root / "probe" / "x.done.json", root / "probe" / "x.failed.json", root / "probe" / "x.log")
out1, _ = runner.run_tasks([t], workers=1, cap_seconds=60, rss_worker_bytes=1 << 31, rss_aggregate_bytes=1 << 33)
print("3. first invocation:", out1["x"]["status"], "| stage status:", runner.stage_status(out1))
t2 = runner.Task("x", (sys.executable, "-c", "print('restored')"), t.result_path, t.failed_path, t.log_path)
out2, _ = runner.run_tasks([t2], workers=1, cap_seconds=60, rss_worker_bytes=1 << 31, rss_aggregate_bytes=1 << 33)
print("   second invocation after the cause is removed:", out2["x"]["status"], "-", out2["x"].get("reason"))
```

### `audit_analysis_planlabels.py`

```python
"""Auditor: re-run the analysis of the synthetic rehearsal (argv[1]) with cell labels taken from the plan's items instead of the config; in memory only."""
import collections, sys
from pathlib import Path
from studies.p10ir import analysis, core, registry, stages
from studies.p10ir import plan as pm
root = Path(sys.argv[1]) / "synthetic"
plan = pm.Plan.load(root / "freeze" / "plan.json")
for stage in (core.STAGE_A1, core.STAGE_A2):
    m = {(it["cell_name"], it["arm"], it["draw"]): it["cell"] for it in plan.items(stage)}
    lab = lambda arm, spec, d, m=m: m[(spec.name, arm, d)]
    a = analysis.analyze_stage(registry.load(root, stage), stage, label_of=lab, specs=stages._specs_of(plan, stage))
    rows = collections.Counter((comp, r["row"], r["reason"][:40]) for c in a["cells"].values() for ck in c["checkpoints"].values() for comp in ("tree", "index") for r in ck[comp]["replicates"])
    print(stage, dict(rows))
    print("   R-DIAGNOSIS evaluable:", a["r_diagnosis"]["evaluable"], a["r_diagnosis"]["components"]["tree"]["value"], "/", a["r_diagnosis"]["components"]["index"]["value"])
```

### `audit_adapter.py`

```python
"""Auditor: P10-S1's own train.run_job against adapter.run_cell on the same tiny cell (synthetic backbone, test-range seeds 938501..), F-OQ and T-OQ,
32 updates, snapshots 8/16/32: model.pt file hashes and every state-dict tensor must be equal. Writes only under argv[1]."""

import sys
from pathlib import Path

import torch

from arborlm.io import file_sha256
from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p10ir import adapter
from studies.p10s1 import core as s1
from studies.p10s1 import train

train.configure()
out = Path(sys.argv[1])
corpus = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
seeds = s1.seed_set("p10s1-test-5", 938501)
data = d.build_study_data(seeds, corpus, sizes=d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128))
bb = controls.synthetic_backbone(101, 301)
ok = True
for arm, slots in (("F-OQ", 1024), ("T-OQ", 1024)):
    cell = s1.make_cell("P", arm, 128, slots, 1, 330698, u_p=16, run_updates=32)
    common = dict(cell=cell, data=data, stream=train.training_stream_for(data, cell.facts), backbone=bb, r1_seed=seeds.r1_codes, hash_seed=s1.h8_seed(seeds), updates=32, snapshots=(8, 16, 32), optimizer_marks=(32,))
    train.run_job(train.TrainJob(out_dir=out / "s1" / cell.label, mode="calibration", **common))
    res = adapter.run_cell(train.TrainJob(out_dir=out / "ad" / cell.label, mode="p10ir", **common))
    for u in (8, 16, 32):
        a = out / "s1" / cell.label / "snapshots" / s1.snapshot_stem(u) / "model.pt"
        b = out / "ad" / cell.label / "snapshots" / s1.snapshot_stem(u) / "model.pt"
        ta, tb = torch.load(a, weights_only=True)["model"], torch.load(b, weights_only=True)["model"]
        same_t = ta.keys() == tb.keys() and all(torch.equal(ta[k], tb[k]) for k in ta)
        same_f = file_sha256(a) == file_sha256(b) == res["snapshot_sha256"][str(u)]
        opt_same = file_sha256(a.parent / "optimizer.pt") == file_sha256(b.parent / "optimizer.pt") if (a.parent / "optimizer.pt").exists() else None
        print(arm, u, "tensors equal", same_t, "| model.pt hash equal", same_f, "| optimizer.pt hash equal", opt_same)
        ok = ok and same_t and same_f
print("ALL EQUAL" if ok else "MISMATCH")
```

### `audit_refusals.sh`

```sh
#!/bin/sh
# Auditor: try the registered entry point's refusals in a scratch clone (never in the worktree). Code from the worktree (PYTHONPATH), repository = the clone (--repo).
# Each step prints the exit code and the refusal line. Commits are made in the scratch clone only.
S=/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10ir-audit
W=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1
C=$S/clone
RUN=$S/regrun
PY="$W/.venv/bin/python"
G="git -C $C -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false"
reg() { (cd "$W" && PYTHONPATH="$W" timeout 300 "$PY" -m studies.p10ir.stages registered "$1" --run-dir "$RUN" --freeze-commit "$2" --repo "$C" 2>&1 | grep -v NumPy | grep -v conversion_method | tail -2); echo "   exit=$?"; }
HEAD0=$($G rev-parse HEAD)
echo "step 1: dirty tree (an untracked file)"; touch "$C/untracked.txt"; reg a1 "$HEAD0"; rm "$C/untracked.txt"
echo "step 2: clean tree, no plan"; reg a1 "$HEAD0"
echo "step 3: a registered plan committed, caps still provisional"
(cd "$W" && PYTHONPATH="$W" "$PY" - "$C" "$RUN" <<'EOF'
import sys
from pathlib import Path
from studies.p10ir import core, plan as pm
repo, run = Path(sys.argv[1]), Path(sys.argv[2])
cfg = core.load_config(repo / core.CONFIG)
rec = pm.build_plan(mode=pm.REGISTERED, cfg=cfg, repo=repo, items=pm.registered_items(cfg), run_dir=run, s1_run_dir=None, extra={})
core.write_record(repo / core.PLAN, rec)
EOF
) 2>&1 | grep -v NumPy | grep -v conversion_method
$G add -A >/dev/null && $G commit -qm "scratch: fake freeze (provisional caps)"; F1=$($G rev-parse HEAD); reg a1 "$F1"
echo "step 4: caps not provisional, plan rebuilt and committed; no Decision 2"
sed -i '' 's/^provisional = true/provisional = false/' "$C/configs/p10ir_routing.toml"; rm "$C/studies/p10ir/freeze/plan.json"
(cd "$W" && PYTHONPATH="$W" "$PY" - "$C" "$RUN" <<'EOF'
import sys
from pathlib import Path
from studies.p10ir import core, plan as pm
repo, run = Path(sys.argv[1]), Path(sys.argv[2])
cfg = core.load_config(repo / core.CONFIG)
rec = pm.build_plan(mode=pm.REGISTERED, cfg=cfg, repo=repo, items=pm.registered_items(cfg), run_dir=run, s1_run_dir=None, extra={})
core.write_record(repo / core.PLAN, rec)
EOF
) 2>&1 | grep -v NumPy | grep -v conversion_method
$G add -A >/dev/null && $G commit -qm "scratch: fake freeze"; F2=$($G rev-parse HEAD); reg a1 "$F2"
echo "step 5: Decision 2 file present but not committed"
mkdir -p "$C/results/p10ir-freeze-x"; printf 'DECISION: RUN\nfreeze commit %s\n' "$F2" > "$C/results/p10ir-freeze-x/DECISION_2_A1.md"; reg a1 "$F2"
echo "step 6: Decision 2 for A1 committed; a1 (gates-a1 not run)"; $G add -A >/dev/null && $G commit -qm "scratch: decision 2 A1"; reg a1 "$F2"
echo "step 7: A2 stage with only A1's Decision 2"; reg a2-train "$F2"
echo "step 8: Decision 2 says DO NOT RUN as well"; printf 'DECISION: RUN\nDECISION: DO NOT RUN\n%s\n' "$F2" > "$C/results/p10ir-freeze-x/DECISION_2_A1.md"; $G commit -qam "scratch: contradictory"; reg a1 "$F2"
echo "step 9: a frozen file edited after the freeze and committed"; printf 'DECISION: RUN\n%s\n' "$F2" > "$C/results/p10ir-freeze-x/DECISION_2_A1.md"; echo "# edit" >> "$C/studies/p10ir/labels.py"; $G commit -qam "scratch: edit frozen file"; reg a1 "$F2"
echo "step 10: a studies/p10s1 file (imported by every read) edited after the freeze and committed; frozen p10ir files restored"
$G checkout -q "$F2" -- studies/p10ir/labels.py; echo "# edit" >> "$C/studies/p10s1/index.py"; $G commit -qam "scratch: edit p10s1"; reg a1 "$F2"
```

### `audit_labels.py`

```python
"""Auditor's independent oracle of ADR-0029 sections 8.1-8.4, 8.2, 9, 10, written from the ADR text, fuzzed against studies/p10ir/labels.py.
No torch. Prints every disagreement class with one minimal input."""

import itertools
import math
import random
import sys

from studies.p10ir import core, labels

TH = core.Thresholds.from_config()
FLOOR = TH.floor_i_bits
P = ("A", "B")
random.seed(938901)
disagree: dict[str, tuple] = {}
n_cases = {"tree": 0, "index": 0, "cell": 0, "combine": 0, "confirm": 0}


# ---- oracle: section 8.1
E = 1e-12  # attempt 2: the same float tolerance as labels.py (attempt 1 used exact comparisons; every row/suffix/index difference it found was at a float boundary built by the generator)


def weak(iy):
    return iy < FLOOR - E


def restored(ix, iy):
    return (not weak(iy)) and (iy - ix <= 0.25 + E) and (ix >= 0.90 * iy - E)


def gap(iy, ix):
    return iy - ix >= 0.5 - E


# ---- oracle: section 8.3 (first match wins)
def tree_oracle(i, cr8, evaluable=True):
    if not evaluable:
        return ("NOT EVALUABLE", None)
    if any(weak(i["F0"][p]) for p in P):
        return ("NOT EVALUABLE", None)  # WEAK REFERENCE is row 1
    gaps = {p: gap(i["F0"][p], i["T0"][p]) for p in P}
    if not any(gaps.values()):
        return ("NO GAP", None)
    if not all(gaps.values()):
        return ("MIXED-PANEL", None)

    def g(r, p):
        return (i[r][p] - i["T0"][p]) / (i["F0"][p] - i["T0"][p])

    def cond(r):  # "T is RESTORED to F0, or g >= 0.5", as a condition on i that must hold on both panels
        return all(restored(i[r][p], i["F0"][p]) or g(r, p) >= 0.5 - E for p in P)

    Pp, C, J = cond("T1"), cond("T3"), cond("T2")
    H = all(i["T2"][p] <= i["T0"][p] - 0.25 + E for p in P)
    R = cr8 >= 0.90 - E
    rest = {r: all(restored(i[r][p], i["F0"][p]) for p in P) for r in ("T1", "T3", "T2")}
    if Pp and C:
        return ("PRIORS AND CANDIDATES, SEPARATELY", "FULLY" if (rest["T1"] or rest["T3"]) else "PARTLY")  # see note: suffix reading differs
    if Pp:
        return ("PRIORS", "FULLY" if rest["T1"] else "PARTLY")
    if C:
        return ("CANDIDATES", "FULLY" if rest["T3"] else "PARTLY")
    if J:
        return ("JOINT", "FULLY" if rest["T2"] else "PARTLY")
    if H:
        return ("EXACT SEARCH HARMS", None)
    return ("CONTENT" if R else "NOT IDENTIFIED", None)


def rand_i(base=None):
    # values concentrated near the thresholds: F0 in [0, 5], others as F0 minus offsets near 0.25 / 0.5 / closures
    f0 = random.choice([random.uniform(0, 5), FLOOR, FLOOR - 1e-9, FLOOR + 1e-9, 0.0, 4.0, 1.0])
    out = {"F0": f0}
    for r in ("T0", "T1", "T1w", "T2", "T3"):
        d = random.choice([0.0, 0.25, 0.5, 0.49, 0.51, 0.24, 0.26, random.uniform(0, 3), random.uniform(-1, 1), 0.1 * f0, 0.11 * f0])
        out[r] = max(0.0, f0 - d)
    return out


def check_tree():
    for _ in range(200000):
        n_cases["tree"] += 1
        a, b = rand_i(), rand_i()
        if random.random() < 0.5:
            b = {k: v + random.choice([0.0, 0.0, 0.01, -0.01, 0.3]) for k, v in a.items()}
            b = {k: max(0.0, v) for k, v in b.items()}
        i = {r: {"A": a[r], "B": b[r]} for r in a}
        cr8 = random.choice([0.9, 0.8999999, 0.95, 0.5, 1.0])
        want = tree_oracle(i, cr8)
        got = labels.tree_replicate(labels.TreeRep(True, i, cr8), TH)
        if got.row != want[0]:
            disagree.setdefault(f"tree row: oracle {want[0]} / code {got.row}", (i, cr8))
        elif want[1] is not None and got.suffix != want[1] and want[0] != "PRIORS AND CANDIDATES, SEPARATELY":
            disagree.setdefault(f"tree suffix {want[0]}: oracle {want[1]} / code {got.suffix}", (i, cr8))
        elif want[0] == "PRIORS AND CANDIDATES, SEPARATELY" and got.suffix != want[1]:
            disagree.setdefault(f"row 3 suffix (reading): oracle-any {want[1]} / code-both {got.suffix}", (i, cr8))


# ---- oracle: section 8.4
def index_oracle(f0, budgets):
    if any(weak(f0[p]) for p in P):
        return ("NOT EVALUABLE", None)
    cs = sorted(budgets)
    ok = {c: all(restored(budgets[c][p], f0[p]) for p in P) for c in cs}
    suff = [c for k, c in enumerate(cs) if all(ok[x] for x in cs[k:])]
    if not suff:
        return ("INDEX DOES NOT APPROACH FLAT", None)
    c = min(suff)
    return ("SPARSE INDEX APPROACHES FLAT" if c <= 512 else "INDEX APPROACHES FLAT ONLY ABOVE 512", c)


def check_index():
    for slots in (1024, 4096, 16384):
        feas = [c for c in (128, 256, 512, 1024, 2048) if c < slots]
        for _ in range(30000):
            n_cases["index"] += 1
            f0 = {p: random.choice([4.0, FLOOR, FLOOR - 1e-9, 2.0, random.uniform(0, 5)]) for p in P}
            bud = {c: {p: max(0.0, f0[p] - random.choice([0.0, 0.1, 0.25, 0.26, 0.5, 0.1 * f0[p], 0.11 * f0[p]])) for p in P} for c in feas}
            want = index_oracle(f0, bud)
            got = labels.index_replicate(labels.IndexRep(True, f0, bud), TH)
            if got.row != want[0] or got.tags.get("c_star") != want[1]:
                disagree.setdefault(f"index: oracle {want} / code {(got.row, got.tags.get('c_star'))}", (f0, bud))


# ---- oracle: section 8.2 cell label
ROWS = ["NOT EVALUABLE", "NO GAP", "MIXED-PANEL", "PRIORS", "CANDIDATES", "JOINT", "CONTENT", "NOT IDENTIFIED"]


def cell_oracle(rows):
    if sum(r == "NOT EVALUABLE" for r in rows) >= 2:
        return "NOT EVALUABLE"
    for r in set(rows):
        if r in ("NOT EVALUABLE", "MIXED-PANEL"):
            continue  # "a replicate that is ... MIXED-PANEL ... satisfies no condition" (literal reading)
        if sum(x == r for x in rows) >= 4:
            return r
    return "MIXED"


def check_cells():
    for rows in itertools.product(ROWS, repeat=5):
        n_cases["cell"] += 1
        want, got = cell_oracle(list(rows)), labels.cell_label(list(rows), TH)
        if want != got:
            disagree.setdefault(f"cell: oracle {want} / code {got}", rows)


# ---- oracle: section 9 combination (literal: values compared as strings)
CELLV = ["NOT EVALUABLE", "NO GAP", "PRIORS", "CONTENT", "NOT IDENTIFIED", "EXACT SEARCH HARMS", "MIXED", "MIXED-PANEL"]
IDXV = ["NOT EVALUABLE", "SPARSE INDEX APPROACHES FLAT", "INDEX DOES NOT APPROACH FLAT", "MIXED"]
ACTION_T = {"PRIORS AND CANDIDATES, SEPARATELY", "PRIORS", "CANDIDATES", "CONTENT"}


def combine_oracle(lab):
    bad = any(lab[c][cell][cp] == "NOT EVALUABLE" for c in ("tree", "index") for cell in ("X", "Y") for cp in ("U_P", "RUN"))
    comp = {}
    for c in ("tree", "index"):
        at = {}
        for cp in ("U_P", "RUN"):
            a, b = lab[c]["X"][cp], lab[c]["Y"][cp]
            at[cp] = a if a == b else "CELL-DEPENDENT"
        comp[c] = at["U_P"] if at["U_P"] == at["RUN"] else "CHECKPOINT-DEPENDENT"
    if bad:
        return (False, None, None, None)
    rec_t = comp["tree"] if comp["tree"] in ACTION_T else None
    rec_i = comp["index"] if comp["index"] == "SPARSE INDEX APPROACHES FLAT" else None
    nrc = comp["tree"] in ("EXACT SEARCH HARMS", "NOT IDENTIFIED") and comp["index"] == "INDEX DOES NOT APPROACH FLAT"
    return (True, (comp["tree"], comp["index"]), (rec_t is not None, rec_i is not None), nrc)


def check_combine():
    for _ in range(100000):
        n_cases["combine"] += 1
        lab = {"tree": {cell: {cp: random.choice(CELLV) for cp in ("U_P", "RUN")} for cell in ("X", "Y")}, "index": {cell: {cp: random.choice(IDXV) for cp in ("U_P", "RUN")} for cell in ("X", "Y")}}
        want = combine_oracle(lab)
        d = labels.combine(lab, ["X", "Y"])
        got = (d.evaluable, d.pair, None if not d.evaluable else (d.recommended["tree"] is not None, d.recommended["index"] is not None), None if not d.evaluable else d.no_read_time_cause)
        if want[0] != got[0] or (want[0] and want[1:] != got[1:]):
            disagree.setdefault(f"combine: oracle {want} / code {got}", lab)


def check_confirm():
    # A1 vs A2 per component (values compared by row name; two CHECKPOINT-DEPENDENT equal only if their U_P and RUN values are equal)
    def comp_lab(tu, tr):
        return {"tree": {"X": {"U_P": tu[0], "RUN": tr[0]}, "Y": {"U_P": tu[1], "RUN": tr[1]}}, "index": {"X": {"U_P": "MIXED", "RUN": "MIXED"}, "Y": {"U_P": "MIXED", "RUN": "MIXED"}}}

    vals = ["PRIORS", "CONTENT", "JOINT"]
    for a in itertools.product(vals, repeat=4):
        for b in itertools.product(vals, repeat=4):
            n_cases["confirm"] += 1
            l1, l2 = comp_lab(a[:2], a[2:]), comp_lab(b[:2], b[2:])
            d1, d2 = labels.combine(l1, ["X", "Y"]), labels.combine(l2, ["X", "Y"])

            def lit(lab):
                at = {}
                for cp in ("U_P", "RUN"):
                    x, y = lab["tree"]["X"][cp], lab["tree"]["Y"][cp]
                    at[cp] = x if x == y else "CELL-DEPENDENT"
                return ("V", at["U_P"]) if at["U_P"] == at["RUN"] else ("CD", at["U_P"], at["RUN"])

            want = "CONFIRMED" if lit(l1) == lit(l2) else "NOT CONFIRMED"
            got = labels.r_confirm(d1, d2)["R-CONFIRM-TREE"]["value"]
            if want != got:
                disagree.setdefault(f"R-CONFIRM-TREE (literal reading): oracle {want} / code {got}", (a, b))
    ne = labels.combine({"tree": {"X": {"U_P": "NOT EVALUABLE", "RUN": "PRIORS"}, "Y": {"U_P": "PRIORS", "RUN": "PRIORS"}}, "index": {"X": {"U_P": "MIXED", "RUN": "MIXED"}, "Y": {"U_P": "MIXED", "RUN": "MIXED"}}}, ["X", "Y"])
    ok = labels.combine(comp_lab(("PRIORS", "PRIORS"), ("PRIORS", "PRIORS")), ["X", "Y"])
    exp = {("ne", "ok"): "NOT APPLICABLE", ("ok", "ne"): "NOT EVALUABLE", ("ok", None): "NOT RUN", ("ne", None): "NOT APPLICABLE"}
    for (x, y), w in exp.items():
        got = labels.r_confirm(ne if x == "ne" else ok, None if y is None else (ne if y == "ne" else ok))["R-CONFIRM-TREE"]["value"]
        if got != w:
            disagree.setdefault(f"R-CONFIRM special: ({x},{y}) oracle {w} / code {got}", None)
    if labels.r_confirm(ok, ok, a2_complete=False)["R-CONFIRM-TREE"]["value"] != "NOT RUN":
        disagree.setdefault("R-CONFIRM incomplete A2", None)


def check_plateau():
    # i*(run) - i*(run/2) <= 0.10 and i*(run/2) >= floor, both panels; >= 2 of 5 failing -> tag
    run = 49152
    for _ in range(20000):
        s = {p: {u: random.choice([3.0, 3.05, 3.1, 3.11, 0.4, FLOOR, 3.2]) for u in (8192, 16384, 24576, 32768, 49152)} for p in P}
        def istar(series, lim):
            return max(v for u, v in series.items() if u <= lim)
        want = all(istar(s[p], run) - istar(s[p], run // 2) <= 0.10 + E and istar(s[p], run // 2) >= FLOOR - E for p in P)
        got = labels.plateau_ok(s, run, TH)
        if want != got:
            disagree.setdefault(f"plateau: oracle {want} / code {got}", s)


check_tree(); check_index(); check_cells(); check_combine(); check_confirm(); check_plateau()
print("floor", FLOOR, "cases", n_cases)
print("disagreement classes:", len(disagree))
for k, v in disagree.items():
    print("-", k)
    print("   example:", repr(v)[:600])
sys.exit(0)
```

### `audit_reads.py`

```python
"""Auditor's independent brute-force check of P10IR reads and fact-level measures (ADR-0029 sections 6, 7).
Own implementation from the ADR text; compares with studies/p10ir/reads.py, P10-S1's S1Memory._top_tree / _top_flat, IVFMemory.
Seeds: unit-test range 938001-938999 only. Tiny CPU tensors. Nothing is trained, nothing is written."""

import math
import sys

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS
from studies.p9.model import AdditionSpec
from studies.p10ir import reads
from studies.p10s1 import index as s1index
from studies.p10s1.model import S1Memory

torch.set_num_threads(1)
CHUNK = 1 << 20
problems: list[str] = []
counts = {"tree_cases": 0, "tree_queries": 0, "tie_skips": 0, "flat_queries": 0, "ivf_queries": 0}


def tree_mem(branches: int, seed: int, *, dup: bool, scale_router: float) -> S1Memory:
    mem = S1Memory(AdditionSpec("learned_tree", 256 * branches, 16, "R1", branches, 0), seed)
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        mem.keys.copy_(torch.randn(mem.keys.shape, generator=g))
        mem.router.copy_(torch.randn(mem.router.shape, generator=g) * scale_router)
        mem.values.copy_(torch.randn(mem.values.shape, generator=g))
        if dup:  # exact duplicate keys: within a branch (3 -> 7) and across branches (5 -> 256 + 9, 2*256+1 -> 11)
            mem.keys[7] = mem.keys[3]
            mem.keys[256 + 9] = mem.keys[5]
            if branches > 2:
                mem.keys[11] = mem.keys[2 * 256 + 1]
            if branches > 3:  # duplicate router rows: a route tie between branches 1 and 3
                mem.router[3] = mem.router[1]
    return mem


def queries(n: int, seed: int, mem: S1Memory | None = None) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    q = F.normalize(torch.randn(n, 16, generator=g), dim=-1)
    if mem is not None:  # some queries exactly on a key direction (ties of duplicates are then the top)
        k = F.normalize(mem.keys.detach(), dim=-1)
        q[0] = k[3]
        q[1] = k[5]
        q[2] = F.normalize(mem.router.detach()[1], dim=-1)
    return q


def brute_tree(mem: S1Memory, q: torch.Tensor, v: int, ps: bool, pw: bool):
    """Per query, float64: route = cos(q, router_b)/0.2; v best branches (ties lower id); each key of them
    scored cos/0.2 (+ prior if ps); top 8 by (score desc, slot id asc); weights softmax(cos/0.2 + prior if pw)."""
    keys = F.normalize(mem.keys.detach().double(), dim=-1, eps=EPS)
    router = F.normalize(mem.router.detach().double(), dim=-1, eps=EPS)
    per, nb = 256, mem.spec.branches
    out = []
    for row in q.double():
        routes = (router @ row) / 0.2
        lsm = routes - torch.logsumexp(routes, 0)
        vis = sorted(range(nb), key=lambda b: (-float(routes[b]), b))[:v]
        cand = []
        for b in vis:
            for s in range(b * per, (b + 1) * per):
                c = float(keys[s] @ row) / 0.2
                cand.append((c + (float(lsm[b]) if ps else 0.0), s, c + (float(lsm[b]) if pw else 0.0)))
        cand.sort(key=lambda t: (-t[0], t[1]))
        top = cand[:9]
        w = torch.tensor([t[2] for t in top[:8]], dtype=torch.float64).softmax(0)
        vec = (w[:, None] * mem.values.detach().double()[[t[1] for t in top[:8]]]).sum(0)
        out.append({"ids": [t[1] for t in top[:8]], "sel": [t[0] for t in top], "w": w.tolist(), "vis": vis, "vec": vec, "wsc": [t[2] for t in top[:8]]})
    return out


def check_tree(branches: int, seed: int, dup: bool, scale: float) -> None:
    mem = tree_mem(branches, seed, dup=dup, scale_router=scale)
    q = queries(41, seed + 1, mem)
    cases = [("T0", 2, True, True), ("T1", 2, False, False), ("T1w", 2, True, False), ("T3", branches, True, True), ("T2", branches, False, False), ("Tv1_on", 1, True, True), ("Tv1_off", 1, False, False)]
    if branches >= 4:
        cases += [("Tv4_on", 4, True, True), ("Tv4_off", 4, False, False)]
    # T0 against P10-S1's own read, bit for bit
    rv, ri, rb, _ = mem._top_tree(q)
    t0 = reads.tree_path(mem.keys.detach(), mem.router.detach(), q, 2, True, True, per=256, chunk_elements=CHUNK)
    if not (torch.equal(rv[:, :8], t0.values[:, :8]) and torch.equal(ri[:, :8], t0.ids[:, :8]) and torch.equal(rb, t0.branch_ids)):
        problems.append(f"T0 != S1Memory._top_tree (branches={branches}, seed={seed}, dup={dup})")
    for name, v, ps, pw in cases:
        counts["tree_cases"] += 1
        out = reads.tree_path(mem.keys.detach(), mem.router.detach(), q, v, ps, pw, per=256, chunk_elements=CHUNK)
        ref = brute_tree(mem, q, v, ps, pw)
        w = out.values[:, :8].softmax(-1).double()
        for r, b in enumerate(ref):
            counts["tree_queries"] += 1
            gap = b["sel"][7] - b["sel"][8]
            near_tie = abs(gap) <= 1e-5 and b["sel"][7] != b["sel"][8]  # float-ordering tie only; exact ties must follow the id rule
            if out.ids[r, :8].tolist() != b["ids"]:
                if near_tie:
                    counts["tie_skips"] += 1
                    continue
                problems.append(f"{name} ids differ b={branches} seed={seed} dup={dup} q={r}: code {out.ids[r, :8].tolist()} brute {b['ids']} gap8-9={gap:.3g}")
                continue
            if out.branch_ids[r].tolist() != b["vis"]:
                problems.append(f"{name} visited branches differ q={r}: {out.branch_ids[r].tolist()} vs {b['vis']}")
            if max(abs(float(x) - y) for x, y in zip(out.values[r, :8].tolist(), b["wsc"], strict=True)) > 2e-5:
                problems.append(f"{name} weight scores differ q={r}")
            if max(abs(float(x) - y) for x, y in zip(w[r].tolist(), b["w"], strict=True)) > 1e-6:
                problems.append(f"{name} weights differ q={r}: max {max(abs(float(x) - y) for x, y in zip(w[r].tolist(), b['w'], strict=True)):.3g}")
            vec = (w[r][:, None] * mem.values.detach().double()[out.ids[r, :8]]).sum(0)
            if float((vec - b["vec"]).abs().max()) > 1e-5:
                problems.append(f"{name} read vector differs q={r}")
    # the measures of tree_fact_pass against my own computation (E8 by brute force over all keys, float64, ties to lower id)
    specs = [reads.TreeReadSpec(n, (None if v == branches else v), ps, pw) for n, v, ps, pw in cases[:5]]
    got = reads.tree_fact_pass(mem, q, specs, chunk_elements=CHUNK, chunk=16)
    keys = F.normalize(mem.keys.detach(), dim=-1, eps=EPS)
    sc = (q @ keys.T) / 0.2  # float32, the flat read's own scores
    e_ids = []
    for row in sc:
        order = sorted(range(row.numel()), key=lambda s: (-float(row[s]), s))[:8]
        e_ids.append(order)
    for n, v, ps, pw in cases[:5]:
        ref = brute_tree(mem, q, v, ps, pw)
        cr8 = cr1 = sr8 = amc = ams = span = 0.0
        for r, b in enumerate(ref):
            E = e_ids[r]
            C = {s for br in b["vis"] for s in range(br * 256, (br + 1) * 256)}
            wE = torch.tensor([float(sc[r, s]) for s in E], dtype=torch.float64).softmax(0).tolist()
            S = set(b["ids"])
            cr8 += sum(s in C for s in E) / 8
            cr1 += float(E[0] in C)
            sr8 += len(S & set(E)) / 8
            amc += sum(wE[k] for k, s in enumerate(E) if s in C)
            ams += sum(wE[k] for k, s in enumerate(E) if s in S)
            span += float(len({s // 256 for s in b["ids"]}) > 1)
        m = len(ref)
        mine = {"cr8": cr8 / m, "cr1": cr1 / m, "sr8": sr8 / m, "am_c": amc / m, "am_s": ams / m, "share_span_both": span / m}
        for k, val in mine.items():
            if abs(got[n]["facts"][k] - val) > 1e-5:
                problems.append(f"tree_fact_pass {n}.{k}: code {got[n]['facts'][k]:.6f} mine {val:.6f} (b={branches} seed={seed} dup={dup})")
    # pair statistics: share changed and TV distance T0 vs T1, T3 vs T0, T2 vs T3
    for a, bname in (("T1", "T0"), ("T1w", "T0"), ("T3", "T0"), ("T2", "T3")):
        ra = brute_tree(mem, q, dict((c[0], c[1]) for c in cases)[a], *dict((c[0], c[2:]) for c in cases)[a])
        rb = brute_tree(mem, q, dict((c[0], c[1]) for c in cases)[bname], *dict((c[0], c[2:]) for c in cases)[bname])
        ch = tv = 0.0
        for x, y in zip(ra, rb, strict=True):
            ch += float(set(x["ids"]) != set(y["ids"]))
            wa = dict(zip(x["ids"], x["w"], strict=True))
            wb = dict(zip(y["ids"], y["w"], strict=True))
            tv += 0.5 * sum(abs(wa.get(s, 0.0) - wb.get(s, 0.0)) for s in set(wa) | set(wb))
        if abs(got[a]["pair"]["share_selected_changed"] - ch / len(ra)) > 1e-6 or abs(got[a]["pair"]["tv_mean"] - tv / len(ra)) > 1e-6:
            problems.append(f"pair {a} vs {bname}: code {got[a]['pair']} mine changed {ch / len(ra):.6f} tv {tv / len(ra):.6f}")


def check_flat(slots: int, seed: int) -> None:
    mem = S1Memory(AdditionSpec("flat", slots, 16, "R1", 0, 0), seed)
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        mem.keys.copy_(torch.randn(mem.keys.shape, generator=g))
        mem.keys[9] = mem.keys[4]  # exact tie
    q = queries(33, seed + 2)
    q[0] = F.normalize(mem.keys.detach()[4], dim=-1)
    v_ref, i_ref = mem._top_flat(q)
    v, i = reads.exhaustive_top(mem.keys.detach(), q, 64, CHUNK)
    if not (torch.equal(v_ref, v) and torch.equal(i_ref, i)):
        problems.append(f"exhaustive_top != S1Memory._top_flat (slots={slots})")
    keys = F.normalize(mem.keys.detach(), dim=-1, eps=EPS)
    sc = (q @ keys.T) / 0.2
    for r in range(q.shape[0]):
        counts["flat_queries"] += 1
        order = sorted(range(slots), key=lambda s: (-float(sc[r, s]), s))[:8]
        if i[r, :8].tolist() != order:
            problems.append(f"F0 top8 differs from brute force (slots={slots}, q={r})")
    # index reads at several budgets: my own list visiting rule against IVFBudgetMemory and candidate_mask
    for idx_seed, lists in ((938401, slots // 64), (938402, slots // 256)):
        idx = s1index.build_index(mem.keys.detach(), idx_seed, lists)
        for c in (128, 256, 512, 1024):
            if c >= slots:
                continue
            ivf = reads.IVFBudgetMemory(mem, idx, c)
            iv, ii = ivf._top_flat(q)
            cent = idx.unit
            for r in range(q.shape[0]):
                counts["ivf_queries"] += 1
                cs = q[r] @ cent.T
                order = sorted(range(idx.lists), key=lambda L: (-float(cs[L]), L))
                got_lists, tot = [], 0
                for L in order:
                    got_lists.append(L)
                    tot += int(idx.sizes[L])
                    if tot >= c:
                        break
                cand = [s for s in range(slots) if int(idx.assign[s]) in got_lists]
                if len(cand) != tot:
                    problems.append("candidate count bookkeeping")
                if int(ivf.candidate_counts[r // max(1, ivf._rows(slots))][r % max(1, ivf._rows(slots))]) != tot if False else False:
                    pass
                top = sorted(cand, key=lambda s: (-float(sc[r, s]), s))[:8]
                if ii[r, :8].tolist() != top:
                    problems.append(f"I@{c} (lists {lists}) top8 differs q={r}: code {ii[r, :8].tolist()} mine {top}")
            allc = torch.cat(ivf.candidate_counts)
            mask, cnt = s1index.candidate_mask(idx, q, c)
            if not torch.equal(allc, cnt) or not torch.equal(mask.sum(1), cnt):
                problems.append(f"candidate counts differ at c={c}")
            # flat_fact_pass measures for this index read
            fp = reads.flat_fact_pass(mem, q, {"X": (idx, c)}, chunk=8)
            cr8 = cr1 = amc = sr8 = 0.0
            cnts = []
            for r in range(q.shape[0]):
                E = sorted(range(slots), key=lambda s: (-float(sc[r, s]), s))[:8]
                C = set(mask[r].nonzero().squeeze(1).tolist())
                S = set(ii[r, :8].tolist())
                wE = torch.tensor([float(sc[r, s]) for s in E], dtype=torch.float64).softmax(0).tolist()
                cr8 += sum(s in C for s in E) / 8
                cr1 += float(E[0] in C)
                sr8 += len(S & set(E)) / 8
                amc += sum(wE[k] for k, s in enumerate(E) if s in C)
                cnts.append(len(C))
            m = q.shape[0]
            for k, val in {"cr8": cr8 / m, "cr1": cr1 / m, "sr8": sr8 / m, "am_c": amc / m}.items():
                if abs(fp["X"]["facts"][k] - val) > 1e-5:
                    problems.append(f"flat_fact_pass {k} c={c}: code {fp['X']['facts'][k]:.6f} mine {val:.6f}")
            if abs(fp["X"]["candidates_facts"]["mean"] - sum(cnts) / m) > 1e-6 * max(1.0, sum(cnts) / m):
                problems.append(f"flat_fact_pass candidate mean: code {fp['X']['candidates_facts']['mean']} mine {sum(cnts) / m}")
            if fp["X"]["facts"]["sr8"] != fp["X"]["facts"]["cr8"] and abs(fp["X"]["facts"]["sr8"] - fp["X"]["facts"]["cr8"]) > 1e-6:
                problems.append(f"index read: SR8 != CR8 at c={c} (ADR section 7 says they are equal for an index read)")


for branches in (2, 4, 6):
    for k, (dup, scale) in enumerate(((False, 1.0), (True, 1.0), (True, 25.0), (False, 0.02))):
        check_tree(branches, 938601 + 10 * branches + k, dup, scale)
for slots in (1024, 4096):
    check_flat(slots, 938701 + slots // 1024)
print(counts)
print(f"problems: {len(problems)}")
for p in problems[:60]:
    print("  ", p)
sys.exit(1 if problems else 0)
```

### Outputs

```text
== audit_grad_memory.out
{'mode': 'nograd', 'facts': 64, 'peak_rss_mib_before': 187.2, 'peak_rss_mib_after': 207.0, 'growth_mib': 19.9, 'cr8_T0': 0.037109}
{'mode': 'nograd', 'facts': 256, 'peak_rss_mib_before': 187.1, 'peak_rss_mib_after': 209.0, 'growth_mib': 21.9, 'cr8_T0': 0.030762}
{'mode': 'grad', 'facts': 64, 'peak_rss_mib_before': 187.2, 'peak_rss_mib_after': 407.8, 'growth_mib': 220.5, 'cr8_T0': 0.037109}
{'mode': 'grad', 'facts': 256, 'peak_rss_mib_before': 187.4, 'peak_rss_mib_after': 1029.1, 'growth_mib': 841.6, 'cr8_T0': 0.030762}
== audit_pipeline.out
1. stage statuses: {'gates-a1': 'COMPLETE', 'a1': 'COMPLETE', 'gates-a2': 'COMPLETE', 'a2-train': 'COMPLETE', 'a2': 'COMPLETE', 'analysis': 'COMPLETE', 'report': 'COMPLETE'}
   replicate rows: {('A1', 'tree', 'NOT EVALUABLE'): 40, ('A1', 'index', 'NOT EVALUABLE'): 40, ('A2', 'tree', 'NOT EVALUABLE'): 20, ('A2', 'index', 'NOT EVALUABLE'): 20}
   reasons: {('A1', 'tree', 'T-OQ: no item record; F-OQ: no item record'): 40, ('A1', 'index', 'F0: no item record; index: no item record'): 40, ('A2', 'tree', 'T-OQ: no item record; F-OQ: no item record'): 20, ('A2', 'index', 'F0: no item record; index: no item record'): 20}
   plan A1 labels (first 2): ['P_T-OQ_f128_n1024_d1_i330698_u8_y16', 'P_F-OQ_f128_n1024_d1_i330698_u8_y16']
   analysis looks up: P_T-OQ_f128_n1024_d1_i2101_u8_y16 P_F-OQ_f128_n1024_d1_i2101_u8_y16
2. analysis re-run refused: refused: /private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b
3. first invocation: failed | stage status: FAILED
   second invocation after the cause is removed: failed - refused: a failed record exists; it is kept and the task is not re-run
== audit_analysis_planlabels.out
A1 {('tree', 'NOT EVALUABLE', 'WEAK REFERENCE'): 40, ('index', 'NOT EVALUABLE', 'WEAK REFERENCE'): 40}
   R-DIAGNOSIS evaluable: False NOT EVALUABLE / NOT EVALUABLE
A2 {('tree', 'NOT EVALUABLE', 'WEAK REFERENCE'): 20, ('index', 'NOT EVALUABLE', 'WEAK REFERENCE'): 20}
   R-DIAGNOSIS evaluable: False NOT EVALUABLE / NOT EVALUABLE
== audit_adapter.out
F-OQ 8 tensors equal True | model.pt hash equal True | optimizer.pt hash equal None
F-OQ 16 tensors equal True | model.pt hash equal True | optimizer.pt hash equal None
F-OQ 32 tensors equal True | model.pt hash equal True | optimizer.pt hash equal True
T-OQ 8 tensors equal True | model.pt hash equal True | optimizer.pt hash equal None
T-OQ 16 tensors equal True | model.pt hash equal True | optimizer.pt hash equal None
T-OQ 32 tensors equal True | model.pt hash equal True | optimizer.pt hash equal True
ALL EQUAL
== audit_refusals.out
step 1: dirty tree (an untracked file)
refused: the working tree is not clean:
?? untracked.txt
   exit=0
step 2: clean tree, no plan
refused: no freeze plan at <scratch>/clone/studies/p10ir/freeze/plan.json: nothing registered runs before the freeze
   exit=0
step 3: a registered plan committed, caps still provisional
refused: the caps are provisional: the human lead sets them after the rehearsal (section 12)
   exit=0
step 4: caps not provisional, plan rebuilt and committed; no Decision 2
refused: no committed results/p10ir-freeze-*/DECISION_2_A1.md contains the line 'DECISION: RUN' (and not 'DECISION: DO NOT RUN') and the full freeze commit 16bade140fdf78d8f712f063ee2c3bf4632543f7: Decision 2 is recorded there before anything registered runs
   exit=0
step 5: Decision 2 file present but not committed
refused: the working tree is not clean:
?? results/p10ir-freeze-x/DECISION_2_A1.md
   exit=0
step 6: Decision 2 for A1 committed; a1 (gates-a1 not run)
refused: no gates record at <scratch>/regrun/gates-a1/gates.json: run gates-a1 first
   exit=0
step 7: A2 stage with only A1's Decision 2
refused: no committed results/p10ir-freeze-*/DECISION_2_A2.md contains the line 'DECISION: RUN' (and not 'DECISION: DO NOT RUN') and the full freeze commit 16bade140fdf78d8f712f063ee2c3bf4632543f7: Decision 2 is recorded there before anything registered runs
   exit=0
step 8: Decision 2 says DO NOT RUN as well
refused: no committed results/p10ir-freeze-*/DECISION_2_A1.md contains the line 'DECISION: RUN' (and not 'DECISION: DO NOT RUN') and the full freeze commit 16bade140fdf78d8f712f063ee2c3bf4632543f7: Decision 2 is recorded there before anything registered runs
   exit=0
step 9: a frozen file edited after the freeze and committed
refused: studies/p10ir at HEAD differs from the freeze commit
   exit=0
step 10: a studies/p10s1 file (imported by every read) edited after the freeze and committed; frozen p10ir files restored
refused: no gates record at <scratch>/regrun/gates-a1/gates.json: run gates-a1 first
   exit=0
== audit_reads.out (attempt 2)
{'tree_cases': 100, 'tree_queries': 4100, 'tie_skips': 0, 'flat_queries': 66, 'ivf_queries': 462}
problems: 0
== audit_labels.out (attempt 2; examples truncated)
floor 0.4730746427507113 cases {'tree': 200000, 'index': 90000, 'cell': 32768, 'combine': 100000, 'confirm': 6561}
disagreement classes: 18
- row 3 suffix (reading): oracle-any FULLY / code-both PARTLY
   example: ({'F0': {'A': 1.256452186610129, 'B': 1.556452186610129}, 'T0': {'A': 0.0, 'B': 0.0}, 'T1': {'A': 1.016452186610129, 'B': 1.316452186610129}, 'T1w': {'A': 1.118242446083015, 'B': 1.118242446083015}, 'T2': {'A': 1.118242446083015, 'B': 1.108242446083015}, 'T3': {'A': 1.1308069679491162, '
- cell: oracle MIXED / code MIXED-PANEL
   example: ('NOT EVALUABLE', 'MIXED-PANEL', 'MIXED-PANEL', 'MIXED-PANEL', 'MIXED-PANEL')
- combine: oracle (True, ('CELL-DEPENDENT', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'CELL-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'MIXED', 'RUN': 'CONTENT'}, 'Y': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'MIXED'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'CHECKPOINT-DEPENDENT'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'PRIORS'}, 'Y': {'U_P': 'CONTENT', 'RUN': 'CONTENT'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'PRIORS', 'RUN': 'CONTENT'}, 'Y': {'U_P': 'NOT IDENTIFIED', 'RUN': 'EXACT SEARCH HARMS'}}, 'index': {'X': {'U_P': 'MIXED', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}}}
- combine: oracle (True, ('CHECKPOINT-DEPENDENT', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'CONTENT', 'RUN': 'MIXED'}, 'Y': {'U_P': 'CONTENT', 'RUN': 'NOT IDENTIFIED'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}, 'Y': {'U_P': 'MIXED', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('CELL-DEPENDENT', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'NO GAP', 'RUN': 'NO GAP'}, 'Y': {'U_P': 'CONTENT', 'RUN': 'CONTENT'}}, 'index': {'X': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'INDEX DOES NOT APPROACH FLAT'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'INDEX DOES NOT APPROACH FLAT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'NO GAP'}, 'Y': {'U_P': 'CONTENT', 'RUN': 'CONTENT'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}}}
- combine: oracle (True, ('NOT IDENTIFIED', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('NOT IDENTIFIED', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'NOT IDENTIFIED', 'RUN': 'NOT IDENTIFIED'}, 'Y': {'U_P': 'NOT IDENTIFIED', 'RUN': 'NOT IDENTIFIED'}}, 'index': {'X': {'U_P': 'MIXED', 'RUN': 'MIXED'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'MIXED'), (False, False), False) / code (True, ('CHECKPOINT-DEPENDENT', 'MIXED'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'NOT IDENTIFIED', 'RUN': 'PRIORS'}, 'Y': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'CONTENT'}}, 'index': {'X': {'U_P': 'MIXED', 'RUN': 'MIXED'}, 'Y': {'U_P': 'MIXED', 'RUN': 'MIXED'}}}
- combine: oracle (True, ('CELL-DEPENDENT', 'SPARSE INDEX APPROACHES FLAT'), (False, True), False) / code (True, ('CHECKPOINT-DEPENDENT', 'SPARSE INDEX APPROACHES FLAT'), (False, True), False)
   example: {'tree': {'X': {'U_P': 'CONTENT', 'RUN': 'NOT IDENTIFIED'}, 'Y': {'U_P': 'MIXED', 'RUN': 'NO GAP'}}, 'index': {'X': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}, 'Y': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('MIXED', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('MIXED', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'MIXED', 'RUN': 'MIXED'}, 'Y': {'U_P': 'MIXED', 'RUN': 'MIXED'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}, 'Y': {'U_P': 'MIXED', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}}}
- combine: oracle (True, ('EXACT SEARCH HARMS', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('EXACT SEARCH HARMS', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'EXACT SEARCH HARMS'}, 'Y': {'U_P': 'EXACT SEARCH HARMS', 'RUN': 'EXACT SEARCH HARMS'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'MIXED', 'RUN': 'SPARSE INDEX APPROACHE
- combine: oracle (True, ('PRIORS', 'CELL-DEPENDENT'), (True, False), False) / code (True, ('PRIORS', 'CHECKPOINT-DEPENDENT'), (True, False), False)
   example: {'tree': {'X': {'U_P': 'PRIORS', 'RUN': 'PRIORS'}, 'Y': {'U_P': 'PRIORS', 'RUN': 'PRIORS'}}, 'index': {'X': {'U_P': 'MIXED', 'RUN': 'INDEX DOES NOT APPROACH FLAT'}, 'Y': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'MIXED'}}}
- combine: oracle (True, ('NO GAP', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('NO GAP', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'NO GAP', 'RUN': 'NO GAP'}, 'Y': {'U_P': 'NO GAP', 'RUN': 'NO GAP'}}, 'index': {'X': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}, 'Y': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}}}
- combine: oracle (True, ('MIXED-PANEL', 'CELL-DEPENDENT'), (False, False), False) / code (True, ('MIXED-PANEL', 'CHECKPOINT-DEPENDENT'), (False, False), False)
   example: {'tree': {'X': {'U_P': 'MIXED-PANEL', 'RUN': 'MIXED-PANEL'}, 'Y': {'U_P': 'MIXED-PANEL', 'RUN': 'MIXED-PANEL'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}, 'Y': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- combine: oracle (True, ('CONTENT', 'CELL-DEPENDENT'), (True, False), False) / code (True, ('CONTENT', 'CHECKPOINT-DEPENDENT'), (True, False), False)
   example: {'tree': {'X': {'U_P': 'CONTENT', 'RUN': 'CONTENT'}, 'Y': {'U_P': 'CONTENT', 'RUN': 'CONTENT'}}, 'index': {'X': {'U_P': 'INDEX DOES NOT APPROACH FLAT', 'RUN': 'MIXED'}, 'Y': {'U_P': 'SPARSE INDEX APPROACHES FLAT', 'RUN': 'SPARSE INDEX APPROACHES FLAT'}}}
- R-CONFIRM-TREE (literal reading): oracle CONFIRMED / code NOT CONFIRMED
   example: (('PRIORS', 'PRIORS', 'PRIORS', 'CONTENT'), ('PRIORS', 'PRIORS', 'PRIORS', 'JOINT'))
```

`Astra review: NOT_PERFORMED`.
