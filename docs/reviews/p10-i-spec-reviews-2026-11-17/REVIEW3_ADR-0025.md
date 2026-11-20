# Third review — ADR-0025 (P10-I-S2, sequential teacher transfer), for approval readiness

- **Object:** `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md`, 515 lines, SHA-256 `1ab20f0ca234d10b3051be780c3b6185d6d9b0667a6363e22a6c354cceaae325`, at HEAD `fc14159` (branch `claude/p10-i-r`; last changed by `e9d3da0`, which edited only §13 item 6). Line numbers below are this revision's.
- **Reviewer:** the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`, as I know it). I wrote the confirmation review `REVIEW2_ADR-0025.md` and the registry Revisions 2–3 are the auditor role's work; I wrote no part of this draft, of P10-S2's code or of its records. Independent engineering and mathematical review. **Not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.
- **Read against:** REVIEW_ADR-0025.md, REVIEW2_ADR-0025.md; ADR-0022 rev. 5 in full with all its addenda (incl. the rulings of 2026-11-15 and the 44-window addendum of 2026-11-16) and `ADR-0022-addendum-combined-tasks.md`; ADR-0029 §§11–20; ADR-0026 §4 and its frozen-input row; ADR-0027 §panels; DIRECTION.md, DELEGATION_2026-11-18.md, CLOSURE_LEDGER.md, SEED_REGISTRY.md (Rev. 3) and `seed_registry_check_r3.py`; `studies/p10s2/` (`filtering.py`, `core.py`, `datagen.py` imports, `requirements-datagen.txt`); P10-S2's on-disk data, read only: `prefreeze_record.json`, `bundle/partition.json`, `bundle/windows.json`, `bundle/bank.json`, `datagen_attempts/*.json`, `data/datagen-packages/`, `downloads/`.
- No training, generation, network, long computation or git write. No registered checkpoint or sealed value opened. I wrote this file and, under `experiments/_scratch/reviews3/`, `check3_0025.py` and its outputs.

## Verdict: NOT READY

No finding is blocking, and the confirmation review's findings are fixed apart from one partly fixed and two whose fixes create a new problem. What keeps the draft from approval under the delegation:

1. **Lessons of ADR-0029's implementation audit are not carried** (F1–F4): a hash difference of a frozen input is terminal ENGINEERING-FAILURE, not PAUSED — IDENTITY; code or environment errors inside an item have no rule (ADR-0029 ruling 11); the rehearsals run against a "frozen" plan that cannot yet exist and there is no measuring rehearsal before caps; calibration (4–7 h of MPS training) runs with no cap and no rule for code changes after it.
2. **A factual misstatement that would change the evaluation population** (F5): "Panels, all from sentences with both a German and a French reference, as in P10-S2". In P10-S2 only 337 of E_A's and 478 of E_B's 1,000 items had both references.
3. **Rules with an unreachable or wrong default** (F7–F9): GENERAL-QUALITY reads a missing or non-finite GEN value as NOT PRESERVED; MODIFICATION's FORGETS is vacuously true with zero evaluable cells; the N6 fix (NOT EVALUABLE: RECOMPUTATION) conflicts with ENGINEERING-FAILURE's "recomputation difference that changes any line".
4. **The download text contradicts itself** (F10) after `e9d3da0` updated §13 item 6 only.
5. **Gate G9 as written fails today** (F11): `seed_registry_check_r3.py` reports FAIL at HEAD (34 problems, all ADR-0029's own implemented seeds), and the draft still cites the Revision 2 checker and says two confirmed seed sets are "not yet in the registry".

Several items need a choice by the lead (F3, F4, F5's intent, F8's precedence, the rate-grid read layer), not only a text edit, so READY AFTER THE LISTED EDITS does not apply. Where a text edit suffices I give it exactly (section 5).

## 1. Confirmation-review findings

| Finding | Judgement | Note |
|---|---|---|
| N1 pool overlap (REQUIRED) | **FIXED** | Recomputed (section 6): overlap 669,893 / 669,745 (two estimates, differ by 148); split pools 198,489 / 650,199; expected 25,817 / 25,369; equalising share 0.80396; both ≥ 24,000 for shares 0.748–0.821. All draft figures match. Wording: A exceeds the target by 7.6% and B by 5.7% in expectation; "close to missing it by about 6 to 7%" reads as if they were below (advisory A1) |
| N2 Δρ guard (REQUIRED) | **FIXED** | l. 333; applied to M-seq/D-seq and TASK-CODED SPARSE RETENTION. The latter is a change to an ADR-0022 annotation and is not in the §3 table (F6) |
| N3 AGAINST-DENSE value (REQUIRED) | **FIXED** | l. 26, l. 332. The four per-quantity labels partition every cell (≥ +0.05, ≤ −0.05, strictly between), so each quantity reaches exactly one label |
| N4 unlisted changes (REQUIRED) | **PARTLY FIXED** | (a)–(g) are all fixed (words-only, CONTROL-FAILED scope, caps, ensemble check, row 15, rows 16–17 with reasons, sacrebleu, pilot rename, no intermediate snapshot scored). My own rule-by-rule diff finds four further unlisted changes (F6). The table has **24** rows, not 26 |
| N5 timing benchmark (REQUIRED) | **FIXED** | Condition read before each repetition; reason for 2.0 given; arms listed; duration measured. See F13 for scheduling |
| N6 recomputation in "every cell" rules (REQUIRED) | **FIXED — NEW PROBLEM** | l. 354 conflicts with l. 351 (F9) |
| N7 terminal label of a paused stage (REQUIRED) | **FIXED** | l. 177, l. 353, l. 461 |
| N8 regeneration tolerance (REQUIRED) | **FIXED — NEW PROBLEM** | Identity of token sequences is required, but generation batch composition is not fixed; a seeded subsample regenerated in different batches has different padding and can differ for numerical reasons (F12) |
| N9 Lane D, ADR-0020 §12.2, word count (REQUIRED) | **FIXED** | §13 item 7; §4.2 cites `filtering.py:57`. The whole `accepts` function (l. 56–61) also rejects non-finite scores and newlines; cite the function (A5) |
| N10 disjoint draws (REQUIRED) | **FIXED** | Rule 6 l. 157; seeds 250916/250917 |
| Cross-references: seeds, ledger | **PARTLY FIXED** | Seeds: values correct, text stale (F11). Ledger: the direction is stated for ADR-0026, but this study's own ordinary windows do not exclude spans already in the ledger, and "(row, byte span)" is undefined for windows that span many rows (F14) |
| §16 RETENTION and M-seq | **FIXED** | l. 470 |

## 2. Findings

**F1 — REQUIRED — identity failures are terminal. §4.4 row 1 (l. 171), §8.6 (l. 351), §15 (l. 460).**
*Problem.* "A hash mismatch" and "a difference between frozen and running inputs" give QUALIFICATION-ENGINEERING-FAILURE / ENGINEERING-FAILURE, and "a second attempt needs the human lead's decision". P10-S1 attempt 1 was lost this way (a status commit into a frozen file), and ADR-0029 §13 now makes such a difference PAUSED — IDENTITY, resumable once the file is restored. The draft also lists "a digest mismatch at a resume" (a real data difference) in the same row as a file-hash difference (an operator error).
*Change.* Add to §11 item 2: "A hash difference of a frozen input file found when a task starts stops the task as PAUSED — IDENTITY. Restoring the file bit for bit lets the stage resume; completed blocks and cells are kept. ENGINEERING-FAILURE stays for differences in what the study produced: a teacher digest or regeneration difference, the ensemble check, a failed gate." In §4.4 row 1 and §8.6, replace "a hash mismatch" with "a failed gate on study-produced data (as §11 item 2 distinguishes)".

**F2 — REQUIRED — code and environment errors have no rule. §8.3 (l. 301), §8.6, §15.**
*Problem.* An exception inside a training cell or a scoring item has no stated effect. Read literally it leaves a record missing: "INCOMPLETE … no line is derived", a registered study status that reads as a result. ADR-0029 ruling 11 (§20) fixed this after its implementation audit: an `item_error` makes the analysis refuse (ENGINEERING STOP — ITEM ERRORS), and an environment error propagates and is never recorded as a failed gate or NOT EVALUABLE. Separately, ADR-0022's re-check ruling R16 let the data step resume after an engineering stop. P10-S2 needed eight attempts: three engineering stops at set-up, two guard stops at 8.09 and 9.38 GiB (`datagen_attempts/attempt-006/007.json`), one lead stop. The draft drops R16 without listing it.
*Change.* Add to §8.6: "A code or environment error inside a block, cell or item stops its stage. While any such error is recorded, the analysis refuses: ENGINEERING STOP — ITEM ERRORS. It is never NOT EVALUABLE or INCOMPLETE. In Part Q, a step stopped by such an error before any value of Q1–Q4 has been computed resumes from its last completed block once the cause is recorded, as ADR-0022's ruling R16 allowed. After that point a second attempt is the human lead's decision." Add a §3 row for the R16 change if the lead does not adopt it.

**F3 — REQUIRED (lead's choice) — rehearsal order, the candidate plan and caps. §10 (l. 376–387), §11 item 5 (l. 397), §4.3 rule 7.**
*Problem.*
- The Part Q rehearsal "runs the frozen Part Q plan" and §11 item 5 says "rehearsal against the frozen plan itself", but the freeze comes after the rehearsal. ADR-0029 ruling 5 resolved this: a candidate `plan.json`, rehearsed, with its hash recorded, and a freeze that refuses any other hash.
- The draft has one rehearsal per part, and no cap governs it. ADR-0029 needed a measuring rehearsal, then caps computed by code, then a counting rehearsal under those caps (commit `dd273b3`; §20).
- The text does not say that every stage derives its items from the plan file only.
*Change.*
- Replace "the frozen Part Q plan" and "the frozen plan itself" with "the candidate plan file itself; its SHA-256 goes into the rehearsal record, and the freeze refuses a plan with any other hash".
- Add: "Each part has a measuring rehearsal, with a fixed cap stated here, after which its caps are computed by code; then a counting rehearsal under those caps. Every stage derives its blocks, cells and items from its plan file only." The lead must state the measuring rehearsals' caps.

**F4 — REQUIRED (lead's choice) — calibration has no cap and no code-identity rule. §7, §10 stage 4.**
*Problem.*
- Stage 4 (calibration, the ladder to 8,000 updates, the pilot) is projected at 4–7 h of MPS training. It comes before the Part T rehearsal from which every Part T cap is computed, so it runs uncapped.
- No rule says what happens to the calibration records if Part T's training or scoring code changes after calibration, which the rehearsal and the implementation audit are likely to cause. ADR-0022's re-check ruling N3 made pre-freeze records carry the code commit and refused stand-in records.
- Calibration also has an implementer's guess (see G1): the 36-unit count implies one rate grid at a single read layer, then the other read layer at the chosen rate, but the text does not name that layer.
*Change.* State:
- the cap of stage 4, and its source (for example a short measuring rehearsal of Part T before calibration);
- "Calibration records carry the hashes of the training and scoring files they ran. The Part T freeze refuses calibration records whose hashes differ from the frozen files. A changed file means calibration is re-run on calibration seeds before the freeze."
- the read layer of the rate grid.

**F5 — REQUIRED — the panel population is misstated. §4.1 step 3 (l. 94).**
*Problem.* "Panels, all from sentences with both a German and a French reference, as in P10-S2." In P10-S2's `partition.json` only Q_fit, Q_check, D_cal, D_con and E_C are all both-reference. E_A has 337 of 1,000, E_B 478 of 1,000 and E_open 131 of 500. ADR-0022 §5.2 defines E_A and E_B as sentences "with German / French references", stratified by reference count. An implementer following the sentence would restrict E_A and E_B to both-reference sentences. That is an unlisted change of the evaluation population, and the draft describes it as no change.
*Change* (if the intent is "as in P10-S2"): "Panels, as in P10-S2: Q_fit, the Q_check reserve, D_cal, D_con and E_C from sentences with both a German and a French reference; E_A, E_B and E_open from evaluation-side sentences with a reference in their language, stratified by reference count (ADR-0022 section 5.2)." If the intent is all-both, add a §3 row with a reason.

**F6 — REQUIRED — the §3 table is still incomplete.** My diff of ADR-0022 §§4–14 with all addenda against this draft finds four changes outside the 24 rows, besides F2's R16 and F5:
- (a) **TASK-CODED SPARSE RETENTION** now has the G_second ≥ 0.50 guard (l. 333). ADR-0022 §11.4 had none.
- (b) **Order in ACQUISITION.** CONTROL-FAILED (row 2) is now read before NEGATIVE (row 3). ADR-0022 §11.3 read NO-ACQUISITION (row 4) before CONTROL-FAILED (row 5).
- (c) **The 300-item subsample's denominator.** Below 0.30 it now makes the cell's gap undefined, so ACQUISITION is NOT EVALUABLE (l. 285). Before, only the full-panel denominator could.
- (d) **Q_check reserve size.** The reserve of 16 blocks (8,000 items) has no reason. It was chosen knowing B's Q_check acceptance share of 0.044 in P10-S2, which needs about 3,409 items. Say so beside the rule.

*Change.* Add rows 25–28 for (a)–(c) and the R16 change, and add the disclosure for (d) in §4.3's table.

**F7 — REQUIRED — GENERAL-QUALITY has no NOT EVALUABLE. §8.3 (l. 327), §8.4.**
*Problem.* "NOT PRESERVED otherwise" makes a missing, non-finite or recomputation-failed GEN value a measured failure. That reverses ADR-0022's ruling C-M1/C-M2 ("never read as passed and never as a measured failure"). The milestone would then print WITHHELD on an engineering defect.
*Change.* Replace "NOT PRESERVED otherwise." with "NOT PRESERVED if every reading is recorded and finite and one exceeds 0.02. NOT EVALUABLE if a reading is missing, non-finite or failed recomputation. The milestone line is then NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE)."

**F8 — REQUIRED — MODIFICATION is vacuously FORGETS. §8.5 (l. 344).**
*Problem.* "FORGETS UNDER MODIFICATION if ρ < 0.70 in every evaluable cell" holds when no cell is evaluable. RETENTION has the "at least four evaluable cells" guard; MODIFICATION does not. A CONSOLIDATION-REJECTED cell also has no stated snapshot for the other readings that use M-ii (C1/C2, the GEN suffix, ROUTER).
*Change.* Insert before FORGETS: "NOT EVALUABLE if fewer than four cells are evaluable for M-ii (section 8.1), or a cell it reads failed recomputation". Add: "In a CONSOLIDATION-REJECTED cell, M-ii's snapshot for every other reading is the pinned M-append snapshot, and it is marked as such."

**F9 — REQUIRED (lead's choice) — recomputation precedence. §8.6 l. 351 against l. 354.**
*Problem.* A cell beyond tolerance makes every line that reads it NOT EVALUABLE: RECOMPUTATION. That changes a line, so the same event is also "a recomputation difference that changes any … line" and therefore ENGINEERING-FAILURE. The text does not say which applies, or whether lines are derived under ENGINEERING-FAILURE; only INCOMPLETE says "no line is derived".
Two readings are coherent:
- (i) ADR-0029's: a difference beyond tolerance is an engineering stop, never a scientific NOT EVALUABLE.
- (ii) Keep N6, and compare verdicts computed from the registered scores with verdicts from the recomputed ones. A verdict difference means ENGINEERING-FAILURE with no line derived. NOT EVALUABLE: RECOMPUTATION applies only when no verdict changes.

Reading (i) is consistent with ruling 11; this is **PENDING LEAD REVIEW**.

**F10 — REQUIRED — the download text contradicts itself. §3 row 21 (l. 79), §4.4 (l. 179), §12 (l. 413, l. 415), §13 item 6 (l. 426).**
*Problem.* §13 item 6 records the 50 GB delegation. Row 21 still says "no download without the human lead", §4.4 says the fallback "needs a download (section 12)", and §12 says the P10 delegation "does not cover P10-I". Units differ: "10 GB" in row 21, "10 GiB" in §9.
*What the delegation changes:*
- The fallback's files (315.3 MB + 8.1 MB) no longer need a download approval. The **invocation** of the fallback stays the human lead's: it is decided after a teacher has failed and it changes teachers and data.
- Nothing else in the plan downloads anything.
- The delegation does not cover packages outside the lock (`DELEGATION_2026-11-18.md` §3). The packages are already on disk anyway (126,182,132 bytes, 28 packages; my byte count of the installed tree equals the download ledger, l. 37). So the question is their **use**, not a download.
- It does not help if the Tatoeba copy is lost, because a new fetch is a different weekly export.

*Change.* Edits E2–E5 in section 5.

**F11 — REQUIRED — gate G9 fails as written, and the seed text is stale. §6 (l. 245, 254, 257).**
*Problem.*
- Run at HEAD `fc14159`, `seed_registry_check_r3.py` (SHA-256 `e462…7594`, unchanged) gives **RESULT: FAIL** with 34 problems. All are P10-I-R's own seeds, now present in `configs/p10ir_routing.toml` and `tests/test_p10ir_*.py`, counted against its own allocation. None concerns ADR-0025: section [2] shows 0 collisions for 250916–250917 and 252901–252914. The FAIL occurs on the committed config too, so it is not caused by the uncommitted edits in the tree. The Revision 2 checker also FAILs. Three other third-review runs in this folder record the same 34.
- The draft cites `seed_registry_check.py` with "RESULT: PASS".
- It marks 250916/250917 and 252901–252914 "Not yet in the registry", but Revision 2 confirmed them.
- Once this study is implemented, its own seeds will make the checker fail the same way.

*Change.* Edit E6 (section 5): cite the r3 checker. G9 runs a copy that excludes this study's own files, with the copy's hash recorded, as ADR-0029 §19 ruling 6 did. Remove both "Not yet in the registry".

**F12 — REQUIRED — the regeneration identity depends on batch layout. §4.3 rule 9, §4.4 recomputation (l. 181).**
*Problem.* Teacher outputs differ with the thread count (P10-S2). They can also differ with batch composition, because padding changes matrix shapes and float rounding, and a beam can flip. P10-S2 generated in batches of 32 (`generation_config.A.first_batch.n = 32`). Regenerating "a seeded subsample of 1,000 sources" in new batches could produce a spurious QUALIFICATION-ENGINEERING-FAILURE. The 100-sentence digest at resume has the same exposure.
*Change.* Add to rule 9: "Generation runs in batches of 32 sources in stored block order. The digest and the regeneration subsample are whole stored batches, drawn by seed 250914 and regenerated with the same composition and order."

**F13 — REQUIRED — Part T would need the tokenizer for R-gloss-icl. §4.1 step 8, §5.2 (l. 214).**
*Problem.* The registered path never encodes text (ADR-0022 §2): every model input is a concatenation of segment ids made in the data step. R-gloss-icl places "the top gloss of each source word" in the prompt. Those gloss words are target-language word types from the replicate's lexicon, and they are in no stored segment. The prompt template is also not given. As written, Part T needs the out-of-lock tokenizer, or R-gloss-icl cannot run.
*Change.* Add to step 8: "token ids of every target-language word type of the accepted pools, each as its own segment with a leading space, for R-gloss-icl". Add the R-gloss-icl template to §5.2. The template is the lead's choice.

**F14 — REQUIRED — shared panel ledger. §4.1 l. 111.**
*Problem.*
- ADR-0026 §4 already excludes P10-S2's 144 windows. On the same grid these include the same 44 marker-like windows, so the 44 are protected whichever study freezes first.
- This study's 100 ordinary windows are new (seed 250907). If ADR-0026 freezes first, they must avoid its panels; the draft does not say so.
- "(row, byte span)" is undefined for a 256-token window over the concatenated validation rows (ADR-0022 ruling A-B3).
- Reconciliation of 44 and 144: 144 = 44 marker-like + 100 ordinary. Both numbers are right, and step 2's "44" is the exact count P10-S2's record holds (`fixed_input_counts`, with 924 ordinary windows).

*Change.* Edit E7 (section 5).

**F15 — REQUIRED — the frozen-input sets are incomplete. §11 item 2.**
*Problem.*
- Part Q's set omits `uv.lock`/`pyproject.toml`, although Part Q runs on the lock plus the packages.
- It omits the installed package set itself (names, versions, file hashes; ADR-0022 ruling R2), every imported file outside the package (`studies/p10s2/*` and `src/arborlm/*`, if reused), launch scripts and stage caps.
- Part T's set omits the import walk, launch scripts, stage caps and the shared panel ledger (ADR-0026 freezes the ledger by SHA-256).
- P10-S2's seed function refuses seeds outside 220001–229999 (`studies/p10s2/core.py:147–188`), so reusing it needs new code, as ADR-0029 needed for P10-S1's whitelist.

*Change.* List these in both sets, and add: "Imported P10-S2 code is listed by file and hash; seeding goes through this study's own function."

**F16 — ADVISORY.**
- A1: "Both teachers are close to missing the disjoint target, by about 6 to 7%" → "In expectation A exceeds the disjoint target by about 7.6% and B by about 5.7%. A fall in yield of 7.0% (A) or 5.4% (B) misses it." The binomial spread of the counts is only about 150, so the outcome depends on the yield the new filter setting gives, not on sampling.
- A2: "about a fifth of B's [sources] a German one" → "about 18%" (114,344 / 650,199).
- A3: Give reasons beside the convergence 0.01, the pilot 0.25, GEN 0.02 (ADR-0022's revision-1 value) and the 10,000 minimum (ADR-0022's 8,000 × 1.25).
- A4: Define "most permissive" as the largest accepted share on Q_fit (ADR-0022 §5.3).
- A5: Cite `filtering.py:56–61`, the whole `accepts` function.
- A6: The Part Q rehearsal's partition is a different split of the same corpus, so its sealed per-item teacher and student scores include registered evaluation-side sentences. They are sealed, so this is harmless; say so, or draw the rehearsal panels from the registered training side.
- A7: Length is 515 lines.
- A8: "Decision 1" here means "run Part Q", whereas in ADR-0029 it means approval of the specification. Rename one of them.
- A9: "No study process running" before the benchmark: say whether other studies' processes count. If they do, the benchmark must be scheduled when no study runs.

## 3. Implementer's guesses, with the ruling I would recommend

| # | Guess | Recommended ruling |
|---|---|---|
| G1 | Read layer of the rate grid; E-table's layer and rate; which rate M-joint, M-ii, D-append and D-joint use | Rate grid at one named layer (the lead names it). Then the other layer at the chosen rate (this matches the 36 units). E-table uses the store's chosen layer with its own rate. Every arm uses its module type's rate |
| G2 | Which snapshot the pilot reads; what an undefined D_cal gap does | M1 of calibration draw 1 at the chosen U. An undefined gap gives NOT STARTED: PILOT (GAP UNDEFINED) |
| G3 | Convergence: a decrease at 2u; arms not checked | Any difference below 0.01, negative included, counts as converged. E-table and the joint arms are not checked (stated limit) |
| G4 | Calibration validity after code changes; calibration cap | F4 |
| G5 | Batch composition of generation, digest and regeneration | F12 |
| G6 | Thread count and determinism of CPU scoring and recomputation | Six threads and deterministic algorithms, as `studies/p10s2/stages.py` sets them, recorded with every score. Bit-exact claims only under those settings |
| G7 | Workers: Part T workers within 24 GiB; Part Q teachers in parallel or in sequence | State the worker count. Part Q: one teacher per worker, at most two workers, guard 12 GiB each |
| G8 | R-gloss-icl template and token ids | F13 |
| G9 | Which rows and codes the permutation controls act on in M-seq, M-ii and M-joint (no separate "second-stage rows") | M-seq and M-ii: all N (2N) rows and the second task's codes. M-joint: all 2N rows and both tasks' codes, each task's controls read on its own panel |
| G10 | M-ii's snapshot in a CONSOLIDATION-REJECTED cell; MODIFICATION with no evaluable cell | F8 |
| G11 | GEN missing or non-finite | F7 |
| G12 | ENGINEERING-FAILURE against NOT EVALUABLE: RECOMPUTATION | F9 |
| G13 | Item, code and environment errors; Part Q re-runs | F2 |
| G14 | Hash mismatch of a frozen file | F1 |
| G15 | Q3 fails for one teacher: does the other's Q_check run? | Yes. The per-teacher table is complete; the label is row 3 |
| G16 | ACQUISITION-NEGATIVE when both the first and the second criterion hold | Print "(FIRST TEACHER; SECOND TEACHER)" |
| G17 | Rule 4 mechanics | Identity units in sorted key order (ADR-0022 lane-A ruling: a no-gold source's unit is its contraction-expanded string). One uniform draw each from seed 250904; B if u < 0.8 |
| G18 | Span format and exclusion of ordinary windows | F14 |
| G19 | Seed of the 200 WikiText train pieces for route accuracy (ADR-0022 lane-C ruling) | List it. Either a registry entry (for example 250918) or "+13, after the prefixes", stated |
| G20 | Disk: retention of resume checkpoints; does the durable copy count against 10 GiB? | Delete a cell's resume checkpoints once its final snapshot is recorded (otherwise at U = 8,000: 66 cells × 16 checkpoints × about 39 MB ≈ 41 GB). The durable copy (≈ 2.6 GB of P10-S2 data plus 0.13 GB of packages) counts separately |
| G21 | Where the Part T measuring rehearsal gets real data before Part Q exists | PENDING LEAD REVIEW (section 4) |
| G22 | Timing benchmark: does the 30-minute bound apply to each repetition or to the first? | To each repetition's start, counted from the stage's opening |

## 4. The packages outside the lock, what can run without them, and the request

**Which parts need them.** Teachers run only through `transformers`, `sentencepiece` and their companions. New text can be tokenized for the student only with `tokenizers`.

| Part | Needs the packages? |
|---|---|
| Part Q step 1: applied generation configuration, tokenizer record, student conversion and equivalence (G8) | Yes. The conversion and equivalence could instead reuse P10-S2's hash-recorded `student_plain_fp32.pt` and `equivalence_tensors.pt`, which are on disk. That needs a line in the spec |
| Part Q steps 2–4: Tatoeba counts, partition, pools, the split, the Q_check reserve order | No (standard library), **except** the GEN-window count and sampling. `windows.json` holds only P10-S2's 144 windows and the train ids, not the validation grid, so a new ordinary-window draw needs the student tokenizer |
| Part Q steps 5–6: teachers and the untrained student on Q_fit; Q_check | Yes (teacher generation; student token ids for new prompts). The Q1–Q4 arithmetic itself (chrF, filter grid, Wilson) runs on the lock from stored outputs |
| Part Q step 7: generation | Yes |
| Part Q step 8: panel outputs, token bank (including F13's gloss words), sacrebleu cross-check | Yes |
| Part Q rehearsal | Yes ("with the real teachers") |
| Independent recomputation of Part Q: regeneration of 1,000 sources per teacher | Yes |
| Part T: calibration, rehearsal, gates, registered run, recomputation, timing benchmark | **No**, provided Part Q's bank holds every segment (F13) |

**What can be done without them, using what is on disk.**
- Implementation and tests of both parts on synthetic stand-ins (P10-S2 did exactly this).
- A Part Q rehearsal of steps 2–4 only.
- Technically, a Part T **measuring** rehearsal of training and scoring rates on P10-S2's bundle (student, token bank, 7,804 / 2,341 accepted outputs, its D_cal). This would replace §14's unmeasured Part T rates. It is not in the draft; it would show whether the student learns from teacher output on P10-S2's D_cal, so its scores should be sealed. **PENDING LEAD REVIEW.**
- Nothing registered can run: Part T needs Part Q's outputs, and Part Q needs the teachers.

**The smallest request to the human lead.** Approve the *use*, with no download, of the 28 hash-pinned packages already installed at `.claude/worktrees/agent-a91c79a181109bb9c/data/datagen-packages/`:
- 126,182,132 bytes;
- requirements file `studies/p10s2/requirements-datagen.txt`, SHA-256 `d549380e67b220945d183a159a2cc2a85c2c982947367c70fd411038769e8867`, the set he approved for P10-S2's data step;
- on the path of the data-generation process only, for ADR-0025 Part Q only: its rehearsal, its registered run and the independent regeneration check;
- nothing in Part T and no other package.

Ask him at the same time to name the durable location (section 11, item 1). The packages live in an agent worktree that may be cleaned.

## 5. Exact text edits (the ones that need no choice)

- **E1** (§3 table, after row 24): add rows 25–28 for F6 (a)–(c) and the R16 change of F2, each "ADR-0022 | this study | why" as F6 states. In §4.3's table beside "the reserve (at most 8,000 items)" add: "16 blocks: about 2.3 times the 3,409 items B needs at its P10-S2 Q_check share (0.044); chosen knowing that share".
- **E2** (§3 row 21): "no download without the human lead" → "downloads within the human lead's delegation of 2026-11-17 (under 50 GB in total, no per-item approval), each recorded in the download ledger; none is planned except the fallback's files if the fallback is invoked"; "new disk 10 GB" → "new disk 10 GiB".
- **E3** (§4.4, l. 179): "It needs a download (section 12), and the Spanish files" → "Its files (323.4 MB) fall within the download delegation (section 12); the invocation remains the human lead's decision. The Spanish files".
- **E4** (§12 fallback row, "Needs"): → "The human lead's decision to invoke the fallback; the download is within the 50 GB delegation". (§12 l. 415): "The ledger's running total is 1,188,183,868 bytes of 30 GB. That delegation was given for P10 and does not cover P10-I." → "The ledger's running total is 1,188,183,868 bytes. Downloads for P10-I fall under the human lead's delegation of 2026-11-17 (under 50 GB in total, no per-item approval). It covers no package outside the lock (`DELEGATION_2026-11-18.md` section 3); the packages above are already on disk, so their use, not a download, is the open question."
- **E5** (§9 row "Memory guard"): append "Resume checkpoints of a training cell are deleted once its final snapshot is recorded; the durable copy of section 11, item 1 is not counted against the 10 GiB."
- **E6** (§6 l. 245): "(`seed_registry_check.py`: RESULT: PASS). Gate G9 re-runs the check, extended with this study's named values, before each freeze." → "(`seed_registry_check_r3.py`, Revision 3). Gate G9 runs a copy of that checker that excludes this study's own files, as ADR-0029 section 19 ruling 6 did, with the copy's SHA-256 in the gate record, and checks this study's named values against the registry's allocation rows, before each freeze." (l. 254 and l. 257): delete "**Not yet in the registry**" twice and write "(registry Revision 2)".
- **E7** (§4.1 l. 111, append): "The 100 ordinary windows are sampled only from ordinary windows whose byte spans overlap no span already in the shared ledger at the Part Q freeze (ADR-0026's panels included, if it froze first); step 2 counts the ordinary windows after that exclusion. A window is recorded by its start and end byte offsets in the validation text concatenated as ADR-0022's ruling A-B3 defines, with its first and last row."
- **E8** (§8.3 GENERAL-QUALITY): as F7.
- **E9** (§8.5 MODIFICATION): as F8.
- **E10** (§4.3 rule 9, append): as F12.
- **E11** (§4.1 step 8, append): as F13, first sentence.
- **E12** (§4.1 step 3): as F5, if the intent is "as in P10-S2".
- **E13** (§11 item 2): as F1's first paragraph and F15's lists.
- **E14** (§8.6, append): as F2.
- **E15** (§4.3 projection): A1's and A2's sentences.

## 6. Numbers checked (my own code)

| Draft | Quoted | Recomputed | Result |
|---|---|---|---|
| l. 45, 159 | overlap about 669,900; A-exclusive about 64,500, B-exclusive about 114,300 | 669,893 / 669,745; 64,525; 114,344 (67,626 keys with both references) | match |
| l. 159 | pools 198,500 / 650,100; accepted 25,800 / 25,400 | 198,489 / 650,199; 25,817 / 25,369 | match |
| l. 64, 159 | 0.804 equalises; both ≥ 24,000 for 0.75–0.82 | 0.80396; 0.7476–0.8209 | match |
| l. 159 | Q_check about 1,000 (A), 3,400 (B) | 962; 3,409 | match |
| l. 124–129 | 35/53/69/84; tolerated 4/0, 29/8 | same | match |
| l. 133 | Q4 fails about one in six at 0.92 | 0.146 (150), 0.177 (155), 0.141 (160) | match |
| l. 43, 51 | precision 0.9231, 0.9545; Wilson lower bounds 0.842, 0.782 | 0.92308, 0.95455; 0.84217, 0.78202 | match |
| l. 435 | 12.3 / 14.1 ms; 26 s; 178 s | 12.33 / 14.07; 26.4; 178.1 (`memory_by_phase`) | match |
| l. 439–441 | 1.3 h / 3.0 h / 3.2 h; ×2–3 | 1.26 / 3.04 / 3.22 h; 2.5–3.8 / 6.1–9.1 / 6.4–9.7 h | match |
| l. 449–456 | 7–13 h, 4–7 h, 4–14 h, 1.2–4.9 h, totals 20–60 h / 40–100 h | 6.7–13.0; 3.7–7.2; 4.1–13.7; 1.2–4.7; totals 21.1–56.9 h / 41.2–95.9 h | match |
| l. 191, 204, 233 | 2,424,833; 2,419,200; 1,152,577; loads 0.49 / 0.98 | same | match |
| l. 410–411 | 936,320,520 B (29 files); 126,182,132 B | 936,325,387 B over 30 files minus `fetch_record.json` (4,867 B) = 936,320,520; 126,182,132 B over 4,270 installed files | match |
| l. 81 | guard stops at 8.09 and 9.38 GiB | `attempt-006.json`, `attempt-007.json` | match |
| l. 93, 111 | 44 marker-like windows | `fixed_input_counts`: 44 marker-like, 924 ordinary | match |
| l. 94 | panels all both-reference "as in P10-S2" | E_A 337/1,000, E_B 478/1,000, E_open 131/500 both-reference | **wrong (F5)** |
| l. 245 | registry check PASS | r3 and r2 checkers FAIL at HEAD, 34 problems, none ADR-0025's | **stale (F11)** |

## 7. Cost, and running beside another study

- **Part Q:** about 2.5–3.8 h of generation if the pools stop at the 10,000 minimum, 6.1–9.1 h to the 24,000 target, and at most 6.4–9.7 h for the whole split pools. These figures assume a 2–3× slowdown at six threads, which is unmeasured. Add Q_fit / Q_check (minutes), the bank (P10-S2's took about 6 minutes) and the rehearsal (about 1–2 h). **About 4–12 charged hours.**
- **Part T:** 21–57 h at U = 2,000 and 41–96 h at U = 8,000. Not included: rehearsals, gates and routers.
- **Whole study:** about 25–110 charged hours, consistent with the delegation record's "20–100".
- **Must run alone:** only stage 7, the timing benchmark. Its quiet condition excludes other studies' processes.
- **Can share the machine:** every other stage. No registered label reads wall or CPU time. Teacher outputs are fixed by thread count and batch layout (F12), not by load. CPU scoring is deterministic at fixed threads. G4's MPS–CPU check uses tolerances.
- **Costs of sharing:**
  - Charged hours (k·t) grow under contention. Caps computed from a quiet rehearsal can then PAUSE. The rehearsal record should state the load it ran under.
  - Memory: Part T's 24 GiB aggregate plus, for example, P10-I-R's 18 GiB comes to 42 of 48 GiB on the human lead's working computer. While another study runs, Part T should use at most two workers (16 GiB).
  - Never run it in another study's frozen worktree.

## 8. Open choices of §13 under the delegation

| Item | Recommended option sound? | By delegation? |
|---|---|---|
| 1 Part Q separate | yes | yes |
| 2 one teacher qualifies | yes (Part T does not run) | the fallback **invocation must not** be taken by delegation: it comes after a failure is observed and changes teachers and data |
| 3 descriptive lines kept | yes | yes |
| 4 oracle, three replicates, every cell | yes | yes |
| 5 cap extension | yes; matches DIRECTION §5 | yes |
| 6 packages; durable location | — | **Packages: not by delegation** (`DELEGATION_2026-11-18.md` §3). The location may be named by the lead (git-ignored, recorded) |
| 7 Lane D, ADR-0020 §12.2 declined | yes | Closure-ledger §10 item 3 reserves the disposition to the human lead. Declining runs nothing and can be reversed, so it does not block approval. Record it as declined under the delegation, or leave it with him |
| 8 timing benchmark scheduling | **no recommendation given**, so nothing can be "taken at the recommended option" | Add one, for example "run when no study runs; NOT MEASURED otherwise". It needs the human lead's computer quiet, so schedule it with him |
| 9 independence from S0, S1 | yes | yes |
| Design choices shown for veto | Q_fit 2,000 and the 4/5 split were chosen knowing P10-S2's data, and both are disclosed. Neither can favour the memory: the split never reaches qualification, and the OVERLAPPING fallback is fixed by rule | yes |

**0.804.** The registered value is 4/5. 0.804 is a rationale computed from P10-S2's yields and should not be registered as a parameter. The difference between them is about −350 expected accepted items for A and +100 for B, against a yield uncertainty that decides the DISJOINT / OVERLAPPING outcome on its own. It does not matter for any label.

## 9. Commands and environment

```
cd <worktree>/experiments/_scratch/reviews3
PYTHONDONTWRITEBYTECODE=1 python3 -I check3_0025.py <agent-a91c79a181109bb9c>/data/p10s2-pre-20261115/data   # check3_0025.out
#   attempt 1 failed (TypeError: gold_pool entries are dicts, not keys): check3_0025.attempt1_failed.out, kept
PYTHONDONTWRITEBYTECODE=1 python3 -I docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py   # r3_seedcheck_python3.out: RESULT: FAIL (34, all P10-I-R)
PYTHONDONTWRITEBYTECODE=1 python3 -I docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py      # r3_seedcheck_r2checker_python3.out: RESULT: FAIL
python3 -I -c '<read-only json of prefreeze_record.json, partition.json (panel reference sets), windows.json, bank.json, datagen_attempts/*.json>'
find .../data/datagen-packages -type f | stat sizes; find .../downloads -type f | stat sizes; shasum -a 256 studies/p10s2/requirements-datagen.txt
git show e9d3da0; git show HEAD:configs/p10ir_routing.toml | grep (seed literals)
```

Environment: Python 3.15.1, standard library only, no repository package imported; Darwin arm64. I did not use `uv run --locked`, so that nothing would be written into the worktree's environment during another study's run. The checker's optional section [6] was therefore skipped (it needs `arborlm`), and sections [1]–[5] and [7] ran. One checker attempt of mine failed (above) and is kept. No earlier figure of mine needed correction.

`Astra review: NOT_PERFORMED`. This review is not human approval.
