# Third review of ADR-0029 (P10-I-R, frozen-checkpoint routing diagnosis): readiness for the human lead's Decision 1

- **Reviewer:** the `arbor-auditor` subagent. Model as I know it: Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0029, of P10-S1's code, or of the two earlier reviews (`REVIEW_ADR-0024.md`, `REVIEW2_ADR-0024_ADR-0029.md`), which were earlier arbor-auditor runs.
- **Standing.** This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** a human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. Scientific choices are marked **PENDING LEAD REVIEW**.
- **Draft reviewed:** `docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md`, 387 lines, SHA-256 `f35d8193657185a8522ebd3ddadce4c606797925f8be369bcc2decc3589649cc`. Worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-i-specs`, HEAD `c32169d`, clean tree.
- **Also read:** `SEED_REGISTRY.md` (revision 3, SHA-256 `7211706f…`), `seed_registry_check_r3.py` (SHA-256 `e4623604…`, matches the registry); `LITERATURE_AND_ROUTING_NOTE.md` §4–§5; `DIRECTION.md` §5, §7; ADR-0021 §8.2, §8.5 (by grep); `ADR-0024-p10-i-s1-capacity-scaling.md` and `ADR-0026-p10-i-s3-longer-training.md` (by grep); `studies/p10s1/model.py`, `index.py`, `evaluate.py` in full; `core.py` lines 800–1004; `train.py` lines 200–480; `studies/p9/model.py` lines 230–475; `src/arborlm/pilot_model.py` `stable_top`; `results/p10s1-run-2026-11-17/` `OUTCOME.md`, `RESULTS.md` line 96, `ledger_after_run.json`, `manifests/evaluate.manifest.json`.

## Verdict

**READY AFTER THE LISTED EDITS.**

All nine ADR-0029 findings of the confirmation review were addressed, and the blocking gate defect (R-N1) is fixed. I found no new blocking defect. Nine REQUIRED items remain, and each is a text edit spelled out below, old text → new text:

- three are rule gaps where a literal implementation would mislabel or fail by construction: R3-2 (adapter identity gate), R3-3 (MIXED-PANEL), R3-4 (study-level NOT EVALUABLE);
- two are definitions an implementer would otherwise have to guess: R3-1 and R3-6;
- one is a missing platform condition: R3-7;
- one fixes a label claim: R3-8;
- one completes the side-by-side table of §16 item 8: R3-9;
- one splits R-CONFIRM per component: R-CONFIRM per component (R3-5).

Once the edits are made, the scientific choices still open in §16 belong to the human lead, and the draft can be implemented under each recommended option without further rulings.

---

## A. Method, environment, commands

- Machine: Darwin 27.2.0 arm64. Scratch directory, not durable: `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/review3_0029/`.
- `uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py` (Python 3.12.14 from the lock, `timeout 300`). Exit 0, **RESULT: PASS**. The ADR-0029 literals are found at lines 99–103 of the draft, and the declared re-uses are listed as re-uses. The output is saved as `seedcheck_r3.out` in the scratch directory. A first invocation piped through `grep` printed the ADR-0029 lines but lost the RESULT line to the pipe; it was rerun with redirection. That was not a failure of the checker.
- `uv run --locked python -I save_hash_check.py <scratch>/out` (torch 2.8.0 from the lock, `timeout 120`). This uses toy tensors only and no study data. It found:
  - two stream saves of the same payload give the same file hash (`70f94bf6…`);
  - changing only the payload's `label` string changes the hash (`b1cfe112…`);
  - saving to a path instead of a stream changes the zip prefix from `archive/` to `model/` and changes the hash again (`0cc8b5b5…`).
  - The registered snapshot `P_T-OQ_f8192_n4096_d1_i2101/snapshots/u0000512/model.pt` has the prefix `archive/`: I read its zip index only, no tensor.
  - This is the evidence for R3-2.
- `python3 -I enum_labels.py` (stdlib). This enumerates the §8.3 rule as written over (gate, gap state, P, C, J, H, R). It also checks by 200,000 random draws that RESTORED implies g ≥ 0.5 wherever a gap of at least 0.5 bits exists. Result: 0 counterexamples. The output is in section C.
- Checkpoint inventory (`ls`, `[ -f ]`): every checkpoint that ADR-0029 §4 names has both `model.pt` and `eval/…/eval.json` for all 70 F-OQ and T-OQ cells, including run/2 for the plateau check. The list is U_P, the run length, the two trajectory points, and 24,576 at the 4,096/16,384-slot cells of 2K and 8K.
- Records read with `python3 -I -c`:
  - `train.json` key names and `environment.threads`: torch 2.8.0, `torch_num_threads` 1, interop 1, `deterministic_algorithms` True;
  - the ledger: evaluate 1,899.05 s charged;
  - the evaluate manifest: 193 tasks, 11,334 task-seconds, peak RSS 1.4145 GiB, and seconds per cell by arm and size.
- **Disclosure about the seal (§4).** To check the gate key paths, I loaded two `eval.json` files in a script that printed **key paths only**:
  - `P_T-OQ_f8192_n4096_d1_i2101/eval/u0008192/eval.json`;
  - `P_F-OQ_f8192_n4096_d1_i2101/eval/u0016384/eval.json`.
  - No value of `tree_recall_of_exhaustive_top8` or `recall_of_exhaustive_top8` was displayed, computed on, or seen by me. The draft's seal says no one "opens an `eval.json` of that run outside" the extractor, so the freeze record should list this access (see R3-A10).
- I computed no routing statistic and read no checkpoint tensor. I did no training and used no network.

## B. Disposition of earlier findings

### B.1 Confirmation review (`REVIEW2_ADR-0024_ADR-0029.md`), ADR-0029 findings

| Finding | Draft's text read | Judgement |
|---|---|---|
| R-N1 (BLOCKING) index-recall gate compares two quantities | §4 (b), §7 bullet 1, §11 gate 3 | **FIXED.** Gate 3 is the review's text. I checked it against the code. `_read_record` resets `IVFMemory` measures per panel and reads `measured()` after Panel A. `panel_counts` calls `select` twice, for the main and the swap read; table reads reuse `read`. Each per-query hit is k/8, and its float32 block sum and Python float sum are exact, so a recomputation is bit-exact independent of order. `tree_recall` is an integer ratio. Both recorded quantities exist where the gate reads them: U_P for T-OQ, every evaluated snapshot for F-OQ-IVF. |
| R-N2 §3 overclaims | §3 lines 59–60 | **FIXED.** Both sentences are corrected, and the re-check of the labels (line 64) is right: no rule used the false statement. |
| R-N3 exactness identities in floating point | §6, §11 gate 4, §13 | **PARTLY FIXED.** There is one code path, a v = N/256 gate read and tolerance gates. But "float tie" is undefined, "within 1e-6" does not say absolute or relative, and no tolerance has a stated reason (R3-6). Gate 2 also does not say which path computes T0 (R3-1). |
| R-N4 cell-level NOT EVALUABLE | §8.2 bullet 3 | **FIXED** at cell level. **New problem** at study level: §9 item 1 does not say which component's cell NOT EVALUABLE it means (R3-4). |
| R-N5 "the same label" | §8.2, §9, §10 | **PARTLY FIXED.** Row-name comparison, median c\*, NO GAP and MIXED-PANEL wording, the order of §9 and NOT APPLICABLE are all done. But MIXED-PANEL is not a row of the first-match table, so a literal reading labels such a replicate CONTENT, EXACT SEARCH HARMS or NOT IDENTIFIED (R3-3). |
| R-N6 NOT IDENTIFIED / CONTENT | §1, §8.3 row 8, §9 | **FIXED.** NOT IDENTIFIED recommends nothing in every combination, CONTENT has one action, and the note's "none" row is not issued and is put to the human lead (§16 item 8). |
| R-N7 departures from note §5.2 | §16 item 8 | **PARTLY FIXED.** The table exists, but it omits three departures (R3-9). |
| R-N8 JOINT claim; C may be inert | §7, §8.3 row 6, §16 item 9 | **FIXED.** |
| R-N9 bridge and P10-S1's seed gate | §10 | **FIXED** as to the seed gate (new adapter; §11 item 6 replaces `check_seed_set`). **New problem:** the identity gate compares file hashes that depend on the payload label and on how the file is written (R3-2). |
| R-N10 loaded line | §9 | **FIXED** (R-DIAGNOSIS-LOADED, printed only). |
| R-N11 memory figure | §13 | **FIXED**. 1.415 GiB matches the evaluate manifest (1.4145 GiB). |
| R-N12 sealing practice | §4 | **FIXED** (whitelist extractor). See R3-A10 for the reviewers' key-name listings. |
| R-N13 dense reference | §7 last bullet | **ANSWERED**; I accept the answer. |
| R-N14 PRIORS weights / selection | §8.3 | **FIXED** (printed descriptively). |
| R-N16 CHECKPOINT-DEPENDENT likely | §9 items 3–4, §16 item 2 | **FIXED** (applied per component; left to the human lead). |
| §F stale seed text | §5 | **FIXED.** The values match registry §4.2 and the checker passes. One residual: it cites the revision 2 checker file (R3-A2). |

### B.2 First review (`REVIEW_ADR-0024.md`), the points named in the brief

| Point | Judgement |
|---|---|
| A (run length primary, chosen knowing the data) | **FIXED.** The checkpoints are co-primary, there is a plateau check, and the disclosure sits beside the rule (§8.1). The plateau check drops the floor of ADR-0021's own plateau rule (R3-A1). |
| B (what the 2 × 2 identifies) | **FIXED**, completed by §3, the P/C/J/H/R table, testability and T1w. |
| F2 (BLOCKING) tree label misassigns causes | **FIXED.** The one remaining over-claim is in CONTENT's wording (R3-8). |
| F8 U_P / run length | **FIXED.** |
| F9 R-CONFIRM like for like | **FIXED**: pinned to P10-S1's rate and lengths, five fresh draws, A1's frozen code. **New problem:** R-CONFIRM is defined jointly and used per component (R3-5). |
| F11 recall records | **FIXED** (description, seal, gate). |
| F16 gates | **PARTLY FIXED**: the tolerance definitions are missing (R3-6). |
| F17 | Concerns ADR-0024's lane C. For ADR-0029 only the half-point snapshots matter, and they exist (section A). |

---

## C. Checks that passed (no finding)

1. **Reads against the code.**
   - T0 is `S1Memory._top_tree` → `select` → `delta`. The prior is `routes.log_softmax(-1)` over all N/256 branches, gathered at the visited ones. Selection is the top 8 of the top 64 by `stable_top` (ties to the lower slot id). The weights are the softmax of the 8 selected scores.
   - T1, T1w, T3, T2 and Tv are well defined as substitutions in that path.
   - T1w's weights are the softmax of cos/0.2 over the slots T0's rule selected.
   - I256@512 is `evaluate.ivf_model`. I64@c is `index.build_index(keys, seed, lists=N/64)` with `candidate_mask(…, minimum=c)`.
   - Feasibility: N/256 = 4, 16 and 64 branches; Tv v ∈ {1, 2, 4} at 1,024 slots, where v = 4 is T3/T2; {1, 2, 4, 8} elsewhere. I64 runs at budgets c < N.
   - Memory of the all-keys path: with the evaluation chunk of 2^20 elements, rows = 2^20 / (64·256·16) = 4 at 16,384 slots, so the gathered key block is about 1 MiB per row, which is bounded.
2. **Result space (`enum_labels.py`).**
   - Per replicate, with a gap on both panels, the seven rows 3–9 are each reachable and exactly one is assigned.
   - J and H cannot both hold: J gives i(T2) > i(T0) on both panels.
   - Because RESTORED implies g ≥ 0.5 wherever a gap exists (0 counterexamples), "P = RESTORED or g_P ≥ 0.5" is the same as g_P ≥ 0.5 on both panels. The disjunction therefore hides no panel ambiguity, and FULLY/PARTLY are pure suffixes.
   - Cells (NOT EVALUABLE / 4-of-5 row / MIXED), components (adding CELL-DEPENDENT and CHECKPOINT-DEPENDENT) and the pair each reach exactly one value at each checkpoint.
   - The index label is total and unique (4 rows).
   - The exceptions are the MIXED-PANEL gap (R3-3) and the study-level NOT EVALUABLE rule (R3-4).
3. **No recommendation where none is due.** NOT IDENTIFIED, CHECKPOINT-DEPENDENT, CELL-DEPENDENT, MIXED, NO GAP, JOINT and EXACT SEARCH HARMS recommend nothing (§9 "Recommended actions"). NO READ-TIME CAUSE IDENTIFIED recommends nothing.
4. **Thresholds and reasons.**
   - With a stated reason and a source that predates S1's registered records: 0.5 bits (ADR-0021 §8.2, "lead's choice" there), 0.25 bits, 0.90, 0.473 bits (a_use 0.25), 0.10 plateau, 512, the 4-of-5 and 2-of-5 counts.
   - Chosen knowing P10-S1's registered accuracies of T0, F0 and the index: the closure 0.5, R 0.90, the application of the retention rule in place of 95%, the cells and the co-primary reading. §8.1 discloses this beside the retention rule. §8.3 states only that R was fixed without the recall values; the matching sentence for closure and R is missing there (R3-A7).
   - The gate tolerances have no stated reason (R3-6).
5. **Numbers quoted in the draft.**
   - Retention table, gaps and the §2 table: matched by the confirmation review, and the text is unchanged.
   - Evaluation basis: 1,899.05 s charged and 1,866 snapshot evaluations (`OUTCOME.md` line 14, ledger).
   - Evaluate tasks: 11,334 task-seconds, ratio 5.97 to the charged time on six workers.
   - Memory: training peak 0.39 GiB, evaluation peak 1.415 GiB.
   - Bridge cost 0.87 h: confirmed by the confirmation review, unchanged.
6. **A1 cost.** From the evaluate manifest, a registered snapshot evaluation, which carries main, IVF, H1/H2 and the ablations, took about 2–35 worker-seconds depending on cell. On that basis the 13–17 reads per checkpoint come to roughly 1–2 charged hours plus the all-keys reads at 16,384 slots. **2–5 h is plausible and probably conservative.** The rehearsal replaces it, as the draft says.
7. **Engineering requirements.**
   - The frozen-input set is stated, with the ADR's text outside it; only its hash is kept for provenance.
   - Every stage is rehearsed end to end against the frozen plan file before its Decision 2.
   - Stages resume with PAUSED, and PAUSED — IDENTITY is restorable.
   - Analysis is tested on a synthetic registry, descriptive sections included, with a key-collision guard.
   - Platform of record, local checks.
   - No registered reading depends on wall time, so no quiet machine is needed (DIRECTION §7).
   - The limits table follows DIRECTION §5.
8. **Seeds.**
   - The values of §5 equal registry §4.2.
   - The declared re-uses match registry §4.6, and the identity gate's draw 1 with initialisation 2101 matches.
   - Checker r3 passes.
   - `core.check_seed_set` sits in `train.run_job` (via `check_job_seeds`), not in `Trainer.step`. The adapter can therefore call the update function unedited if it rewrites the loop. R3-2 makes this explicit.

---

## D. Findings

### R3-1. REQUIRED — §11 gate 2 does not say which path computes T0, so it may not validate the path the new reads use
- **Location:** §6 "Tree checkpoint" ("All tree reads go through one code path"); §11 gate 2, last sentence.
- **Problem.**
  - §6 routes every tree read, T0 included, through a new common path.
  - Gate 2 says the reproduction reads "call the same P9 and P10-S1 functions the registered evaluation called", which is `S1Memory._top_tree`.
  - If T0 is computed with P9's function, then gate 2 never tests the code that computes T1, T1w, T3, T2 and Tv. If T0 is computed with the new path, the sentence is false.
  - An implementer has to guess which.
- **Change.** Old: "These reads call the same P9 and P10-S1 functions the registered evaluation called, on the same platform, so equality is guaranteed if the code is right."
  New: "F0 and I256@512 call the same P9 and P10-S1 functions the registered evaluation called. T0 is computed through this study's common tree path (§6) at v = 2 with the prior in selection and weights; before its counts are compared, that path's selected slot ids and scores must equal the top 8 of `S1Memory._top_tree` bit for bit on every query of the checkpoint's Panel A and Panel B passes, main and address-swap reads included. Equal counts then validate the path that T1, T1w, T3, T2 and Tv use."

### R3-2. REQUIRED — §10 adapter identity gate: `model_sha256` is a file hash that depends on the payload label and on how the file is written
- **Location:** §10 "Adapter identity gate".
- **Problem.**
  - P10-S1 writes `model.pt` as `torch.save({"update", "label": <P10-S1 cell label>, "model": state_dict}, stream)` (`train.save_snapshot`, `_publish`).
  - My toy check (section A) shows the file hash changes if only the label string differs, and changes again if the file is saved to a path rather than a stream (zip prefix `model/` against `archive/`).
  - An adapter that writes its own labels, or calls `torch.save(path)`, fails the gate with identical tensors. Stage A2 then stops by construction.
  - Also, `train.run_job` refuses non-P10-S1 seed sets (`check_job_seeds`), so the adapter must rewrite the loop. The draft does not say which loop is reproduced.
- **Change.** Old: "reproduces that cell's stored checkpoint at its first three snapshots (512, 1,024, 2,048 updates) with identical `model_sha256`, on the platform of record."
  New: "reproduces that cell's stored checkpoint at its first three snapshots (512, 1,024, 2,048 updates): every tensor of the state dict is equal (`torch.equal`) to the stored `model.pt`'s, and the snapshot written through P10-S1's `train.save_snapshot` under P10-S1's cell label (`P_F-OQ_f8192_n4096_d1_i2101`, `P_T-OQ_f8192_n4096_d1_i2101`) has an identical `model_sha256`, on the platform of record. The adapter's loop is `train.run_job` without `check_job_seeds`, calling `train.Trainer.step` unedited."

### R3-3. REQUIRED — §8.3: MIXED-PANEL is not a row of the first-match table
- **Location:** §8.3 table; §8.2 bullet 1.
- **Problem.**
  - §8.2 says a replicate with a gap on one panel only "is MIXED-PANEL and satisfies no condition", but the first-match table has no such row.
  - Read literally, P, C and J are false there (g is undefined), while H ("on both panels") and R (no panel) can hold.
  - The replicate is then labelled EXACT SEARCH HARMS, CONTENT or NOT IDENTIFIED (`enum_labels.py`: gap state "one" → {CONTENT, EXACT SEARCH HARMS, NOT IDENTIFIED}). CONTENT carries an action.
- **Change.** Insert after row 2:
  "| 2a | MIXED-PANEL | a gap of at least 0.5 bits on one panel only (§8.2) | The panels disagree about whether there is a gap | none |"
  and in the sentence "Every row is reachable: …", after "rows 3–6 cover", insert "(where a gap exists on both panels)".

### R3-4. REQUIRED — §9 item 1: study-level NOT EVALUABLE does not say for which component
- **Location:** §9 "Combination", item 1; §8.2 bullet 3; §11 first consequence.
- **Problem.**
  - A replicate is NOT EVALUABLE **per label**: a failure at a T-OQ checkpoint affects the tree label only.
  - So a cell is NOT EVALUABLE per label. "If either primary cell is NOT EVALUABLE" is undefined.
  - The per-component rule of item 4 also suggests a narrower reading than the one written.
- **Change**, which clarifies the rule without changing its strictness. Old: "1. If either primary cell is NOT EVALUABLE (§8.2) at either checkpoint, **R-DIAGNOSIS is NOT EVALUABLE**. Nothing below is applied."
  New: "1. If, for either component (tree label or index label), either primary cell is NOT EVALUABLE (§8.2) at either checkpoint, **R-DIAGNOSIS is NOT EVALUABLE**, both components are printed with their NOT EVALUABLE cells, and nothing below is applied."
- **PENDING LEAD REVIEW** (an option, not required for readiness): apply item 1 per component, as item 4 does for the checkpoint rule. Then a T-OQ gate failure would not void the index component.

### R3-5. REQUIRED — §10: R-CONFIRM is defined jointly but used per component, and A2's own NOT EVALUABLE is unhandled
- **Location:** §10 "R-CONFIRM" and "What may be said".
- **Problem.**
  - CONFIRMED needs both components to match.
  - "What may be said" requires "CONFIRMED for the tree component", a value the rule never produces.
  - A2 NOT EVALUABLE with A1 evaluable has no value.
- **Change.** Old: "**R-CONFIRM** (labels compared by row name, §8.2): **CONFIRMED** if A2's tree component and index component each equal A1's, where two CHECKPOINT-DEPENDENT components are equal only if their values at U_P and at the run length are equal. **NOT CONFIRMED** otherwise, with both printed, per component. **NOT APPLICABLE** if A1's R-DIAGNOSIS is NOT EVALUABLE."
  New: "**R-CONFIRM** has one value per component, R-CONFIRM-TREE and R-CONFIRM-INDEX (labels compared by row name, §8.2): **CONFIRMED** if A2's component equals A1's, where two CHECKPOINT-DEPENDENT components are equal only if their values at U_P and at the run length are equal; **NOT CONFIRMED** otherwise, with both printed; **NOT APPLICABLE** if A1's R-DIAGNOSIS is NOT EVALUABLE; **NOT EVALUABLE** if A1's is evaluable and A2's is NOT EVALUABLE."
  Then in "What may be said", replace "requires CONFIRMED for the tree component" with "requires R-CONFIRM-TREE: CONFIRMED". In §15, replace "R-CONFIRM: CONFIRMED" with "R-CONFIRM-TREE: CONFIRMED".

### R3-6. REQUIRED — §11 gate 4: "float tie" and "within 1e-6" are undefined, and no tolerance has a reason
- **Location:** §11 gate 4, first and second bullets; §12 ("the gate tolerances").
- **Problem.**
  - An implementer has to invent what counts as a tie, and whether 1e-6 is absolute or relative.
  - The tolerances are frozen scientific thresholds (§12) but have no stated reason.
  - My bound: scores are cos/0.2 ≤ 5 plus a prior near 0 on the branches that hold the selected slots, so float32 rounding is below 1e-6. A softmax weight moves by at most w(1 − w)·Δ ≤ Δ/4 for a score error Δ.
- **Change.** Old (first bullet): "Required: selections identical except at float ties, which are counted and printed (more than 0.1% of facts fails the gate); weights equal within 1e-6."
  New: "Required: selected sets identical except at float ties, which are counted and printed (more than 0.1% of facts fails the gate); weights equal within 1e-6 absolute, slot by slot. A fact's difference is a float tie if, in either computation, the 8th and 9th largest scores (cos/0.2 plus any prior, float32) differ by at most 1e-5. Reasons: float32 scores below 8 in magnitude carry rounding errors below 1e-6, so a difference above 1e-5 at the selection boundary is not rounding; a weight moves by at most a quarter of the score error; 0.1% of facts is 8 of 8,192 and 32 of 32,768."
  In the second bullet, "(counted, same limit)" then refers to this definition. No edit is needed.

### R3-7. REQUIRED — §13: the platform of record omits the settings that the bit-exact gates depend on
- **Location:** §13 "Platform of record".
- **Problem.**
  - Gates 2, 3 and the adapter identity gate are bit-exact.
  - P10-S1 ran torch 2.8.0 with one intra-op thread, one interop thread and deterministic algorithms (`train.json` → `environment.threads`).
  - A different thread count can change BLAS summation order. A mismatch would make every replicate NOT EVALUABLE, which is not repairable under §11.
- **Change.** Old: "**Platform of record:** macOS arm64 (the machine P10-S1 ran on)."
  New: "**Platform of record:** macOS arm64 (the machine P10-S1 ran on), with the locked torch 2.8.0, `torch.set_num_threads(1)`, one interop thread and deterministic algorithms on, as P10-S1's records state (`environment.threads` of every `train.json`); the OS build is recorded with every gate result."

### R3-8. REQUIRED — §8.3 row 8 (CONTENT) claims a cause the reads cannot identify
- **Location:** §8.3 row 8, column "What it claims, and no more".
- **Problem.**
  - "The prior is not the cause" is stronger than "not P", which means T1 closes less than half the gap at read time.
  - The prior can still account for part of the gap, or act during training (§9's own limit).
- **Change.** Old: "The router already finds at least 0.90 of what the keys rank first, the prior is not the cause, and quality is still below the flat memory"
  New: "The router already finds at least 0.90 of what the keys rank first; removing the prior, the hard restriction, or both does not close most of the gap at read time; exact search does no harm; quality is still below the flat memory. The reads do not say whether the content is poor or was shaped by sparse training"

### R3-9. REQUIRED — §16 item 8: the side-by-side table omits three departures from note §5.2
- **Location:** §16 item 8 table, "What changes" column.
- **Problem.**
  - (a) When T1 and T2 both close the gap, the note would give two actions ("exact search restores" and "removing priors restores"). The ADR gives PRIORS, with one action, or SEPARATELY if T3 also closes it.
  - (b) The partial (≥ 0.5, not RESTORED) case applies to CANDIDATES, JOINT and SEPARATELY too, not only to PRIORS.
  - (c) CONTENT also needs not-P and not-C.
  - Everything else of §5.2 and §5.3 is carried. I checked: candidate recall, attention mass, end-task accuracy, prior effect, budgets 128–2,048 where feasible, loaded cells, more than one checkpoint, retention on task performance with the improvement above baseline, DICT kept, no mixed retrieval and training change.
- **Change.**
  - Row 1: append to "What changes": "Where removing the prior alone also closes most of the gap, the label is PRIORS (one action), or PRIORS AND CANDIDATES, SEPARATELY if T3 also does; the note would have issued both actions."
  - Row 2: append: "CONTENT also needs that neither T1 nor T3 closes most of the gap."
  - Row 3: replace "A partial-priors case is added; a both-work case is added" with "A partial case (closure ≥ 0.5 without RESTORED) is added for PRIORS, CANDIDATES, JOINT and SEPARATELY alike; a both-work case is added".
  - Add a row: "| Stage A includes loaded cells | Loaded cells are read and labelled as R-DIAGNOSIS-LOADED, printed only | Their labels recommend nothing |".

### R3-A1. ADVISORY — §9 plateau check: ADR-0021's floor is dropped, and the snapshots cited are those of one cell only
- **Change.** Old: "i\*(run) − i\*(run/2) ≤ 0.10 bits (the plateau limit of ADR-0021 §8.2; the snapshots at 24,576 and 49,152 exist)."
  New: "i\*(run) − i\*(run/2) ≤ 0.10 bits and i\*(run/2) ≥ 0.473 bits (both conditions of ADR-0021 §8.2's plateau rule; i\* as `studies/p10s1/classes.py` computes it; run/2 is 24,576 at 8K/4K and 49,152 at 32K/16K, and both snapshots exist)."

### R3-A2. ADVISORY — §5 cites the revision 2 checker file
- Old: "runs a copy of `seed_registry_check.py` extended with these named values".
- New: "runs a copy of `seed_registry_check_r3.py` (registry revision 3, SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`) extended with these named values".

### R3-A3. ADVISORY — stale ruling and review text
- Header, line 8: old "Giving it its own ADR is the reviewer's and the lead's recommendation, **PENDING HUMAN LEAD RULING**." → new "Giving it its own ADR was the reviewer's and the lead's recommendation."
- §17.1, row "Point C": old "FIXED, pending the human lead's ruling" → new "FIXED; ruled by the human lead on 2026-11-17 ("Keep ADR-0029")".
- §17: old "**This draft has not been re-reviewed.**" → new "This draft was reviewed in `REVIEW3_ADR-0029.md`."
- (Outside this draft: ADR-0024 line 8 still says the split is PENDING and that the file name "keeps '-and-routing-diagnosis'", while its line 415 records the ruling and the file was renamed.)

### R3-A4. ADVISORY — §0 counts cells as checkpoints
- Old: "The same frozen reads on 20 fresh checkpoints" → new: "The same frozen reads on 20 fresh cells (40 checkpoints: U_P and the run length)".

### R3-A5. ADVISORY — §7: name the functions, and define E8 on the scores the read uses
- In the End-task row, after "a_use, i", insert "(i by `studies/p10s1/core.py` `bits_per_fact`)".
- In the CR8 row, replace "E8 and E1 are the top 8 and top 1 by cosine over all keys of **the same checkpoint**, without priors, by `stable_top`" with "E8 and E1 are the top 8 and top 1 over all keys of **the same checkpoint** of cos/0.2 against `F.normalize(keys, eps=EPS)` (the scores the flat read computes), without priors, by `stable_top`".
- Reason: with that definition SR8 = CR8 for an index read holds exactly. Dividing by 0.2 can merge two distinct cosines into one float, and the slot-id tie rule then decides.

### R3-A6. ADVISORY, PENDING LEAD REVIEW — §11: scope of NOT EVALUABLE for an index-only failure
- As written, an I64 rebuild failure or an I256@512 count mismatch voids the tree label too, although only F0 is shared.
- Option: old "(a T-OQ checkpoint: the tree label; an F-OQ checkpoint: both labels, since F0 is the reference of both)" → new "(a T-OQ checkpoint: the tree label; an F-OQ checkpoint whose F0 fails: both labels, since F0 is the reference of both; an F-OQ checkpoint whose I256@512 or an I64 index fails while F0 passes: the index label only)".

### R3-A7. ADVISORY — §8.3: disclosure beside the rule
- After "R is fixed without the recall values having been opened (§4).", insert: "The closure figure 0.5, the figure 0.90 for R, the list size 64 and the budgets of I64 were chosen knowing P10-S1's registered accuracies of T0, F0 and I256@512 (§8.1 disclosure); none was chosen knowing a recall value or any read of §6 other than those three."
- In §9, replace "registered for the hierarchy label before any S1 record" with "registered for the hierarchy label before any registered S1 record". ADR-0021 lines 1078 and 435 place these cells in revision 5, "forced by the grid", after calibration records existed.

### R3-A8. ADVISORY — §9: the reference to ADR-0026 for CHECKPOINT-DEPENDENT
- Old: "the record says the answer depends on training duration and refers to ADR-0026." → new "the record says the answer depends on training duration; ADR-0026 studies duration on a different memory and task and does not resolve it for these memories."

### R3-A9. ADVISORY, PENDING LEAD REVIEW — run gates 1 and 2 in the rehearsal on the registered checkpoints
- Gate 2 compares counts that are already seen, so running it before the freeze observes nothing new.
- Running it then would catch platform or library drift (R3-7) before Decision 2, rather than after it, when a systematic failure makes A1 NOT EVALUABLE and unrepairable.
- Gate 3 should not be run before the freeze, because the seal forbids opening those keys.

### R3-A10. ADVISORY — the seal's wording against reviewers' key-name listings
- All three reviews read `eval.json` key names. This one loaded two files programmatically and printed paths only (section A).
- Suggest replacing "No one prints or opens an `eval.json` of that run outside it" with "From this ADR's approval, no one prints or opens an `eval.json` of that run outside it; before approval, reviewers listed key names only, and the freeze record lists those accesses (REVIEW_ADR-0024, REVIEW2, REVIEW3) and states that no value of the two sealed keys was displayed."

### R3-A11. ADVISORY — §10: list A2's gates in one place
- After "R-CONFIRM does not change R-DIAGNOSIS." add: "Gates of stage A2: gate 1 for the bridge draws' manifests; gate 6 with the bridge values; the adapter identity gate; gate 2 as replaced above; gate 4; gate 5. A failure of gate 1, 5, 6 or the identity gate stops the stage before training."

### R3-A12. ADVISORY, PENDING LEAD REVIEW — a closure on one panel only
- P, C and J need closure on both panels.
- A replicate in which removing the prior closes most of the gap on Panel A but not on Panel B is therefore not P, and can reach CONTENT if R holds. Since the query and the selection are per fact, panel differences come from the backbone context only and are likely small.
- Whether such a replicate should be MIXED-PANEL as well is a scientific choice.

---

## E. §16 open choices: are they the human lead's, and can the draft be implemented under each recommended option?

| Item | His? | Implementable under the recommended option without further rulings? |
|---|---|---|
| 1 Own ADR | Ruled | — |
| 2 Co-primary checkpoints, per component | His | Yes |
| 3 R = 0.90, closure 0.5 | His | Yes (values written) |
| 4 Retention rule | His | Yes |
| 5 Fund A2 | His | Yes, after R3-2 and R3-5 |
| 6 Stage B on A1 alone | His | Yes (affects no code) |
| 7 Order | Ruled | — |
| 8 Departures from note §5.2 | His; it changes directed content | Yes, once the table is complete (R3-9) |
| 9 Testability threshold | His | Yes ("print only" needs no number) |

R3-4's per-component option and R3-A6, A9 and A12 are further choices for him. None is needed for readiness.

## F. Cross-references

- **ADR-0024** (`docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md`). §9.2 (dense comparison) exists as ADR-0029 §7 cites it. ADR-0024 lines 270 and 403 point routing questions to ADR-0029, and its §22 maps F2, F3, F8, F9, F11, F16, F20, F21 and F24 to ADR-0029 sections that exist. Its line 8 is stale (R3-A3).
- **ADR-0026.** Lines 283 and 419 name "ADR-0029 (P10-I-R)" (the confirmation review's §F item is fixed). ADR-0029's reference to it is reworded in R3-A8.
- **Seed registry.** ADR-0029 §5 equals registry §4.2 and §4.6. Checker r3: PASS.

`Astra review: NOT_PERFORMED`.
