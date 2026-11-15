# P10-S2 implementation audit, part C: science rules

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Pinned source: `pin-p10s2-8ad26b5` (commit `8ad26b5`, branch `claude/p10-s2`), read-only. Spec: ADR-0022 revision 5 and the readings in `studies/p10s2/freeze/README.md`.
- Auditor: Opus 5.5 (claude-opus-5-5). I did not write any of the audited code.
- Environment for every number below: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python` (Python 3.12.14, torch 2.8.0, no numpy, no sacrebleu), macOS 27.2.1 arm64, CPU only, cwd = pinned dir. Test seeds 229501–229901 only. No network, no real model or data, no training beyond tiny CPU stand-in updates.
- Out of scope: the combined tasks C1/C2 and COMPOSES (stopped on purpose at this commit).

## Verdict: READY AFTER LISTED FIXES

There are no blockers. There are six majors: five implementation defects (C-M1 to C-M5) and one design question for the lead (C-M6, PENDING LEAD REVIEW). The core mechanics match the ADR wherever I could check them with my own code:

- the store read, ties, initialization and per-stage gates;
- freezing and gradient reach in M-append-frozen; M-ii replay; M-seq and M-joint;
- the LoRA form and parameter matching; E-table and MA-gold;
- the chrF definition;
- the GEN mechanics and the router recipe;
- the class and label logic, apart from the cases listed below.

## Findings

### Majors

**C-M1. A missing control record lets ACQ1 and ACQ2 pass without the lexical margin and the marker-only limit.** Files: `analysis.py:80-90`, `classes.py:70`.
- `Study.lexical` returns `None` when a snapshot has no `ablations` section, or no entry for the panel. `_acq` then skips both control clauses (`if lex is not None`).
- My checker showed this produces ACQUIRES-AND-RETAINS and **label row 7 (TRANSFER-POSITIVE)**. Example: case E5 in `check_edges.out.txt`, where the ablations were deleted for r0/ST1/AB and for E_A of r1/MAF/BA; there are 70 more cases in `check_rules.attempt2.out.txt`.
- `control_failed` (`analysis.py:161-163`) silently skips those cells in the same way.
- The registered `score_snapshot` always writes ablations for memory cells, so this needs a malformed or partial record. But the analysis promises that such records are "never silently dropped".
- **Fix:** for a memory-arm mechanism (first group ST1), a missing ablation section or panel should make the lexical clause NOT_EVALUATED (`Verdict(None, ("control record missing",))`), not "not applicable". Only the LoRA path (reading 1) should pass `lex=None`. `control_failed` should list a missing ablation as an engineering or incomplete problem.

**C-M2. A missing gate record never gives ENGINEERING-FAILURE.** Files: `analysis.py:346-348`, `stages.py:214-215`.
- Only gates that are present and have `ok` False are flagged.
- With `gates: {}`, or with G5 removed, the label is still **row 7** (`check_edges.out.txt`, E1 and E2).
- `stage_analysis` uses `{}` when `gates.json` is absent. As far as I can see, the registered `train` stage also does not require a passed gates record (this part belongs to lane B).
- **Fix:** require G1 and G4–G9 to be present with `ok is True`. If any is absent, give ENGINEERING-FAILURE (or INCOMPLETE). Do the same for the ensemble record (C-m2).

**C-M3. The recomputation rule mis-handles numbers that are not verdicts, and does not compare the GEN gate.** File: `recompute.py:128-137`.
- (a) In own-code mode, a difference within the 1e-6 tolerance in a score that feeds APPEND COST changes the exact float in `annotations/APPEND COST/...`. `outcome_changes` treats this as a changed annotation, which gives a **spurious ENGINEERING-FAILURE** (`check_recompute.out.txt` (a), with a 4e-7 difference).
- (b) The keyword-router GEN gate of each snapshot is not among the compared keys (`gates`, `classes`, `annotations`, `label`). In case (b), a recomputed GEN flipped from pass to fail at r0/MSEQ/AB. The study still came out **row 7**, with only the cell marked NOT_EVALUATED.
- ADR §13.3 says: "If a listed difference changes a gate … the study label is ENGINEERING-FAILURE."
- **Fix:** compare only verdict-bearing fields (booleans, class names, label), or compare numeric annotation fields under the mode's tolerance. Add the per-snapshot `gen_gate` (from `gen_table`), the `gen` holds and `control_failed` to the compared keys.

**C-M4. An undefined gap is hidden when another ACQ2 clause fails.** File: `classes.py:80-83`.
- `_acq` returns `False` when there are failure reasons, even if `g_single` or a lexical (subsample) gap is undefined.
- ADR §11.2 row 1 ("… or a gap is undefined") puts NOT_EVALUATED first. The implementation instead lets the cell reach NO-NEW-CAPABILITY, FORGETS, NOT REPLICATED or INTERMEDIATE. That can change study rows 9, 10, 11 or 12 (three cases in `check_rules.noabsent.out.txt`, e.g. M-seq showing FORGETS where the spec gives NOT_EVALUATED).
- This never produces a false positive.
- **Fix:** return `Verdict(None, ("undefined gap", *reasons))` whenever `undefined` is set, before checking `reasons`.

**C-M5. Words followed by punctuation are read at the punctuation token.** File: `tokenization.py:201-210`.
- `last = max(k for k, (s, _e) in offs if s < end)` uses the end of the whitespace-delimited raw word, including any trailing punctuation.
- With GPT-2-style pre-splitting (SmolLM2's tokenizer separates letters from punctuation), "here," is read at "," and the sentence-final word is read at ".". See `check_read_position.out.txt`.
- ADR §5.4 and §14.2 say the read is at "the last subword of each in-vocabulary source word". Almost every Tatoeba sentence ends in punctuation, so this affects one read per item, in every arm.
- **Fix (before the data-generation step):** set `end` to the offset just after the last character that survives `normalize`, then take the last token that starts before it.

**C-M6. PENDING LEAD REVIEW (design, not code): a router that sees only the position passes GEN under the registered recipe.** Files: ADR §5.4, §6.4; script `check_router_position.py`.
- I used a stub student whose block-L output depends only on the position, and trained a router with `routing.train_router` and `RouterSpec.registered()` (500 updates, batch 64, 8,000 "none" prefixes, half cut to task-prompt lengths of 9–25).
- Result: 0 of 200 triggers at token 64, so the loss increase would be exactly 0 and GEN would pass.
- The diagnostic at the first marker-like string had a false-trigger rate of 0.48, and task-prompt accuracy was 1.0.
- Cause: half of the "none" prefixes still end exactly at token 64, the GEN decision position, which no task prompt reaches. A position cue therefore separates the classes there. The revision-5 recipe (the confirmation's M2) removes the shortcut at task-prompt lengths but not at token 64.
- Only the diagnostic, which enters no rule, detects it. The implementation follows the ADR.
- Options for the lead:
  - (i) take the GEN decision at the first marker-like string for the marker stratum;
  - (ii) cut all "none" prefixes to task-prompt lengths and decide GEN at a drawn length;
  - (iii) make the diagnostic a gate.
- The most conservative option is (iii) on top of the present GEN.

### Minors

- **C-m1. Reading 4 also sends a missing GEN to the "failed" row.** `analysis.py:376-377`: `gen_maf_fails = not gen_maf_holds`, so a missing or non-finite GEN gives row 6, "GENERAL QUALITY NOT PRESERVED", which states a failure that was not measured. **Fix:** a missing or non-finite GEN is NOT_EVALUATED. Rows 6, 7 and 8 should not apply; fall through to row 12 with the reason, or give INCOMPLETE.
- **C-m2. A missing ensemble record skips the check.** `analysis.py:349-352`: with an ensemble of `None` the oracle-ensemble identity check is skipped, and the label is still row 7 (E3). With two `None` values it is satisfied trivially.
- **C-m3. A partial ablation record crashes the analysis.** `analysis.py:86-88`: if one ablation kind is absent, `analyze` raises KeyError (E6). It should be handled like C-M1.
- **C-m4. The oracle-line guard works on words, not on line types.** `output.py:27`, `75-87`; `core.GUARDED_WORDS`; `output.GUARDED_KEYS`. These printed or were accepted without the line (`check_oracle.out.txt`):
  - through `emit`: cost lines with no listed word ("value rows active not fewer …", the stored-size line, the teacher inference cost line), a route-accuracy line and a GEN line;
  - through `emit_plain`: lower-case or mixed-case labels and classes;
  - through `check_record`: records keyed `router_table`, `gen`, `Class`, or carrying a label inside a list of strings.

  The current pipeline does print these lines only inside `block()` in the report, and the terminal summary is headed by the line, so no actual output lacks it. **Fix:**
  - make `emit` always prefix the line;
  - have `write_record` require `oracle_line` at the root of every record it writes;
  - match guarded words case-insensitively;
  - add router, GEN and cost markers to the guard.
- **C-m5. Terminal class lines lack the design suffix.** In the terminal summary (`report.py:138-143`) class lines do not carry "(n replicates, U = …)" (ADR §9: "Every class and label line prints …"). In the report the class table carries it in its caption only.
- **C-m6. The report omits several items the ADR asks for:**
  - every cell's bootstrap interval (`text.bootstrap_interval` is never called);
  - scores for single-reference items alone (§5.2);
  - "When M-ii alone fails GEN, row 8 applies and the report says so" (§11.3);
  - the changed-row share, g1 change, rows and updates per cell, and "selected on D_con, then confirmed on E" (§6.3), which are in the records but not printed;
  - scores on E_open, which is never scored.

  All of these are descriptive.
- **C-m7. Route accuracy reuses the GEN windows.** `cells.py:372`: "general prefixes" for route accuracy are the first 64 tokens of the GEN windows, while §6.4 says that panel "is used for nothing else". It is numerically 1 minus the false-trigger share. Use WikiText-2 validation windows outside the panel, or record this as a reading.
- **C-m8. EXACT-MATCH WEAK will probably never be evaluated.** `analysis.py:272-280` applies the 0.30 definedness floor to the exact-match gap. Teacher-minus-student exact-match rates are likely below 0.30, so the warning would almost always print NOT_EVALUATED. PENDING LEAD REVIEW. The conservative choice is to define it whenever the denominator is above 0, or to print WEAK when it is undefined.
- **C-m9. E-table's learning rate is an unlisted reading.** E-table trains at the store's calibrated learning rate (`cells.py:125`). This is reasonable, but it is not listed among the readings.
- **C-m10. Exact thresholds are decided by IEEE arithmetic.** For example, a margin of 0.7−0.4 = 0.29999999999999993 fails 0.30 (E7). This is an observation only: adding a tolerance would relax a registered threshold.
- **C-m11. Dead code.** `mech_missing` in `analysis.py:355` and `367` is never used.

### Outside lane C (one line each)

- `stages.py:388`: `emit_plain` raises OracleLineMissing when the rung outcome is "NOT STARTED: BUDGET", so `cmd_rehearse` crashes after writing its records.
- The registered `train` stage does not require a passed gates record (see C-M2).
- `cells.py:356-360`: R-icl would repeat BOS before every demonstration if the tokenizer prepends BOS.

## Rulings on the implementer's readings (freeze README, "readings fixed by the lead")

1. **ACQ for L-seq: correct.** An adapter has no rows to permute, no codes and no marker read, so this is the only workable reading. "NO PERMUTATION CONTROL (ADAPTER)" is printed (`report.py:41-42`).
2. **Margin and marker-only on the 300-item subsample, the 0.50 thresholds on the full panel: correct.** It matches "Control G values use the teacher and Stage 0 scores of the same 300-item subsample" and compares like with like.
3. **Panel for CONTROL-FAILED = the targeted capability: correct.** For M-append-frozen, reading the first panel would fire trivially, because the first-stage rows are intact. M-seq and M-joint are read on both panels. Precondition: C-M1's fix, so that a missing control cannot pass silently.
4. **GEN must hold at every memory snapshot, first stage included: correct for rows 7 and 8, wrong for row 6.** "Missing or non-finite is not a hold" is right for the positive rows. But a missing or non-finite value must not trigger row 6, which asserts a measured failure (C-m1). Corrected reading: such values are NOT_EVALUATED, and rows 6–8 do not apply.
5. **Annotations on the mean over replicates and orders; EXACT-MATCH WEAK on M-append-frozen after Stage 2: undetermined.** The options are the mean (as implemented) or "in any replicate and order". The more conservative option, because these annotations are warnings against a claim, is "any replicate/order" for:
   - NO ADVANTAGE OVER SEPARATE ADAPTERS;
   - RETRIEVAL SUFFICES;
   - LEXICON-EQUIVALENT;
   - TEACHER-EQUIVALENT-TO-GOLD;
   - BELOW JOINT BOUND;
   - EXACT-MATCH WEAK.

   Where the ADR states "every replicate" (EQUIVALENT TO A WORD TABLE, TASK-CODED SPARSE RETENTION, ROUTER), the implementation follows it. My comparison of three of these annotations on 400 random records found 0 mismatches. EXACT-MATCH WEAK also depends on C-m8.
6. **Seen items: correct** (outside lane C). It is consistent with "drawn once … stored".
7. **G1 coverage, and two training streams may share an identity group: undetermined, deferred to auditor A.** The literal text of §5.2 says "every pair of panels and streams is disjoint in identity groups". The most conservative reading is to require it between T_A^r and T_B^r as well.
8. **"Registered seed observed": deferred to auditor B.** I saw no conflict.
9. **Partition and vocabulary details: deferred to auditor A.** "Stopping at the first group that reaches 20%" overshoots by at most one group, which is acceptable.

## What I checked and found correct (with my own code)

- **Store read** (§3), against my float64 loop over the definition: maximum absolute difference 2.9e-9.
  - Selection was identical, including exact duplicate keys and a cosine tie across stages; the tie went to the lowest index (`[3, 7, 32, …]`).
  - Initialization: key std 0.01997 and value std 0.01999 at 4,096 × (16 + 576); keys then values come from one generator (reproduced bit for bit); gate starts at 0.
  - One stage has 2,424,833 parameters, as the ADR says (`check_memory.out.txt`).
- **M-append-frozen** is one store with stages concatenated into a single top-8 (no switch).
  - After 8 real AdamW updates the first-stage keys, values and gate are bit-identical, and every appended parameter changed.
  - M-ii trains both stages with batch rows 4 + 4 replayed (32 + 32 registered), and replay is ordered by its own fresh +2 generator.
  - M-seq stays at N rows. M-joint is 2N rows from +7, trained for 2U on mixed material.
  - Student tensors are unchanged and no student parameter has `requires_grad`.
  - G5(c) gate isolation is bit-identical.
- **LoRA:**
  - α = r (scale 1); A uniform with max |A| = 0.041667 = 1/√576; B is zero and the untrained adapter is bit-identical to the student; no dropout; no adapter on route "none".
  - Rank 42 gives 2,419,200 parameters and rank 84 gives 4,838,400, both −0.2323% against one store stage and against M-joint.
- **E-table:** 2,001 × 576 + 1 parameters, N(0, 0.02) from +9, gate starting at 0, task-specific reads.
- **MA-gold:** the ST1 recipe with the +0 seed, trained on gold. No baseline is handicapped relative to the memory arms beyond the ADR's stated asymmetries.
- **chrF-norm** (`text.py:52-72`) against my implementation on 20,000 random pairs with Unicode and punctuation: maximum difference 8.3e-17. Hand cases: 7/11, 25/32, empty = 0, maximum over references.
  - Parameters: chrF2, character orders 1–6, β = 2, no word n-grams, whitespace removed, precision and recall averaged over effective orders, an item with no effective order scores 0, `eps_smoothing=False` semantics, normalization = NFC + lower case + removal of Unicode P* + whitespace collapse.
  - sacrebleu itself is not in this environment; the cross-check belongs to the data-generation step.
- **Decoding and GEN mechanics:**
  - Decoding is greedy, one item at a time, stopping at the first token containing byte 0x0A and cutting at the first newline; generated positions are never read.
  - GEN takes its decision at index 63 (token 64) and averages loss over tokens 65–256. Reads use the routed task's codes at every in-vocabulary word of the window, with no marker read. The threshold is 0.02.
- **Router recipe:** balanced batches (32/32 and 21/21/22), 8,000 prefixes of which 4,000 are cut, generator order initialization → prefixes → lengths → batches, hidden state at block L, CE(cos/0.2).
  - Note: batches are drawn with replacement. "Batch order" in the ADR could also be read as epoch permutations; this is a minor reading.
- **Classes and labels:** compared on 9,000 random synthetic records (rows 2, 5, 6, 7, 8, 11 and 12 reached; missing, failed and non-finite cells; rejected or inert M-ii; undefined denominators).
  - The 6,000 trials without absent ablations agree, except for 3 cases that are all C-M4.
  - The 3,000 trials with absent ablations disagree in 73 cases (C-M1 and C-M4).
  - The orders follow §11.2 and §11.3 ("every replicate", "both orders", first match wins).
- **Oracle-assisted line:** matches the ADR text exactly. The human lead's sentence is quoted exactly in `core.LEAD_RULE` and in the ADR (header, §11.3, §18, and a fourth occurrence). It is not printed in the report; the ADR does not require it there.
- **Existing tests:** `pytest -q -p no:cacheprovider --basetemp <mine>/pytest-tmp tests/test_p10s2_{classes,report,text,model,train}.py` → 117 passed.

## Scripts and outputs (all in this folder)

| Script | Output | Purpose |
|---|---|---|
| `spec_rules.py` | — | my implementation of §10.1 and §11 from the ADR text, and my chrF |
| `check_rules.attempt1.py` | `check_rules.attempt1.out.txt` | **FAILED checker attempt (kept):** my own bug — `"missing"` copied into an ablation value raised a TypeError |
| `check_rules.py` (`NO_ABSENT=1` for the second run) | `check_rules.attempt2.out.txt/.json`, `check_rules.noabsent.out.txt/.json` | random-record comparison of label rows and classes |
| `replay.py` | (stdout, summarized above) | replays the trials that disagreed, for diagnosis |
| `check_edges.py` | `check_edges.out.txt` | edge cases E1–E8 and the annotation comparison |
| `check_memory.py` | `check_memory.out.txt` | read, ties, initialization, gradient reach, LoRA, E-table, ablations |
| `check_chrf.py` | `check_chrf.out.txt` | chrF hand cases and random comparison |
| `check_router_position.py` | `check_router_position.out.txt` | the position-only router (C-M6) |
| `check_recompute.py` | `check_recompute.out.txt` | recomputation rule cases (C-M3) |
| `check_oracle.py` | `check_oracle.out.txt` | attempts to print without the line (C-m4, C-m5, C-m6) |
| `check_read_position.py` | `check_read_position.out.txt` | read position at punctuation (C-M5) |
| — | `pytest_subset.out.txt` | existing tests |

Commands: `cd <pin> && <python> -W ignore <this folder>/<script> <pin> [args]`. For `check_rules.py` the args are `3000 <out.json>`, or `6000` with `NO_ABSENT=1`.

**Discrepancies that were my own mistakes, kept:**
- Attempt 1 of `check_rules.py` crashed on my own data bug.
- My "loose" emulation in `check_rules.py` reported one disagreement (trial 3863) that was wrong on my side. The implementation correctly returns NOT_EVALUATED when the main gap G is undefined, and my loose variant did not.

The pytest temp directory (364 KB) was deleted; nothing in this folder exceeds 100 MB.
