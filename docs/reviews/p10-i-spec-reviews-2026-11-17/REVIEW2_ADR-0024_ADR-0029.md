# Confirmation review of ADR-0024 draft 2 (P10-I-S1, capacity) and ADR-0029 (P10-I-R, routing diagnosis)

- Reviewer: the `arbor-auditor` subagent. Model as I know it: Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of either draft. The first review (`REVIEW_ADR-0024.md`) was written by an earlier arbor-auditor run; where it was wrong I say so below (section D).
- This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. Scientific choices are marked **PENDING LEAD REVIEW**.
- Drafts reviewed (worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-i-specs`, HEAD `26ea57b`):
  - ADR-0024: sha256 `6e744cf0466e35318024059e65be4e0c41db9f3abf37ab9ce94336830b187b77`, 422 lines.
  - ADR-0029: sha256 `5ef26f484b8a28e21f56c341e0acc20f6fed4b10f6e42524220e1ab74db1e8df`, 311 lines.
  - SEED_REGISTRY.md `b3fe7cab…`; CLOSURE_LEDGER.md `10d0f1ec…`.
  - ADR-0023 and ADR-0026 had uncommitted edits in the worktree while I read them (sibling revisions). ADR-0023 line 395 is quoted from that working copy.
- **I did not open the sealed recall values.** I read the code that writes them (`studies/p10s1/evaluate.py`, `index.py`) and the directory listings only. I did not open any `eval.json`.

## Verdicts

| Draft | Verdict |
|---|---|
| **ADR-0024** | **NOT READY.** Block M is close: its remaining defects are rule gaps with mechanical fixes (B-M1 to B-M4, B-M6). Lane L is not specified enough to approve (B-M5), and the arm that can carry an entry label for ADR-0027 is not stated (B-M13). If the lead strikes lane L from this approval as written in B-M5, and applies B-M1 to B-M4, B-M6, B-M12 and B-M13, I would expect block M to be ready. |
| **ADR-0029** | **NOT READY.** One blocking defect: as written, the index recall reproduction gate compares two different quantities. It would fail by construction and make every primary cell NOT EVALUABLE (R-N1). Several label-combination rules are also undefined (R-N4, R-N5), and the draft contradicts itself on what NOT IDENTIFIED recommends (R-N6). |

---

## A. Method, environment and commands

- Machine: Darwin 27.2.0 arm64.
- Scripts: `python3 -I` (Python 3.15.1, `/opt/homebrew/bin/python3`), stdlib only. They import nothing from `arborlm`, `studies` or the implementer's analysis code. They live in the scratchpad `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/review2_0024/`, which is not durable. Their logic is summarised in the appendix.
  - `python3 -I b1_bridge_cost.py <repo>/results/p10s1-run-2026-11-17`: the A2 bridge cost, from `manifests/train.manifest.json`, the ledger and each cell's `train.json` (`run_updates`, `u_p`).
    - **Failed attempts, kept:** `b1_bridge_cost.attempt1_failed.out` and `b1_bridge_cost.attempt2_failed.out`. Both came from my label regex, which first assumed every label carries `_u…_y…` and then that both appear together. Non-loaded cells have neither, and 32K/16K has `_u` only. The regex was fixed and rerun. Neither failure was a defect in the records.
  - `python3 -I b2_retention.py`: the retention table and gaps of ADR-0029 §8.1.
  - `python3 -I b3_spu_all.py <results dir>`: seconds per update for every registered cell of P10-S1 attempt 2.
  - Inline `python3 -I -c` reads: peak RSS from the train and evaluate manifests; H8 seconds per cell; load readings in `supplement/throughput_supplement.json`.
- Seed checker: `uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py` (Python 3.12.14, 300 s deadline). Result: exit 0, **RESULT: PASS**.
- Code read to check the drafts' claims:
  - `studies/p9/model.py`: `_top_tree`, `_top_flat`, `select`, `delta`.
  - `src/arborlm/pilot_model.py`: `stable_top`.
  - `studies/p10s1/model.py`.
  - `studies/p10s1/evaluate.py`: `tree_recall`, `separability`, `deep_measures`, `_read_record`, `panel_counts`.
  - `studies/p10s1/index.py`: `IVFMemory`, `candidate_mask`, `build_index`.
  - `studies/p10s1/core.py`: seed layout and `SEED_RANGE`.
- Checkpoint presence: directory listing of `experiments/P10S1-registered-attempt2-20261117/cells/P_[FT]-OQ_*/snapshots/*/model.pt`. All 70 F-OQ and T-OQ cells exist, no `model.pt` is missing, and every checkpoint ADR-0029 §4 names is present (for example `u0049152` and `u0196608` at 8K/1K).

## B. Checks of numbers and code claims

| Claim | Where | My result | Verdict |
|---|---|---|---|
| The branch prior is one constant per branch | ADR-0029 §3 | `_top_tree`: `routes.log_softmax(-1)` is taken over **all** N/256 branches, gathered at the visited branches and `repeat_interleave`d over each branch's 256 keys. The weights are `softmax` of the 8 selected scores (`delta`). Ties go to the lower slot id (`stable_top` sorts by id first). | **Correct.** The prior shifts every key of a branch equally, so it changes weights only between branches. T3 (all keys, priors on) is well defined. |
| "If all eight selected slots lie in one branch, the prior has no effect on the read at all" | ADR-0029 §3 line 58 | **False.** Without the prior, slots of the other visited branch can enter the top 8, so the selection can change. Given the selection, the weights are unchanged. The first review made the same error (section D). | R-N2 |
| A2 bridge costs about 0.9 charged hours, not about 7 | ADR-0029 §10 | Medians of seconds per update: F-OQ 0.00913 and T-OQ 0.01288 at 8K/4K; F-OQ 0.01244 and T-OQ 0.01465 at 32K/16K. The formula gives 3,745.4 s per replicate, 18,727 worker-seconds (5.20 worker-hours) and **0.867 charged hours**. The 20 matching registered cells actually took 18,813 cell-seconds (0.871 h at six workers; cell-seconds / charged training = 295,340 / 49,251 = 5.997). The longest cell is 1,441 s. | **Drafter correct; first review wrong.** |
| Retention table: implied a_use 0.920 / 0.974 / 0.885 / 0.969; 0.366 / 0.613; 0.368 / 0.597; shares 0.969 / 0.977 / 0.965 / 0.976 / 0.933 | ADR-0029 §8.1 | I get 0.9195 / 0.9735 / 0.8853 / 0.9686; 0.3661 / 0.6130; 0.3679 / 0.5970. Shares 0.9690 / 0.9767 / 0.9653 / 0.9757; loaded cells 0.9333 at U_P and **0.9342 / 0.9340 at the run length**. 95% of 0.992 is a loss of 0.4963 bits; at 0.654 it is 0.1887 bits; i = 2.5 at a_use 0.6783; i(0.25) = 0.4731. | Matches. Only the loaded run-length share rounds to 0.934, not 0.933 (trivial). |
| Gaps T0 → F0: 3.08 / 3.11 at U_P, 1.87 / 2.28 at the run length; index 2.23 / 2.73 and 2.27 / 3.17 | ADR-0029 §8.1 | Same. | Matches |
| §2 a_use table | ADR-0029 §2 | Matches `audit/AUDIT.md` lines 149–167. The 0.83 nearest-neighbour cosine matches `RESULTS.md` line 96 (0.829). | Matches |
| Plateau check computable from existing snapshots | ADR-0029 §9 | run/2 exists: `u0024576` at 8K/4K, `u0049152` at 32K/16K. | Computable |
| Seconds per update quoted in ADR-0024 §9.2, §12, §17 | ADR-0024 | Medians: F-OQ 0.0060 at 2K/1K and 0.0050 at 8K/1K; 0.0081–0.0092 at 4,096 slots; 0.0124–0.0136 at 16,384. T-OQ 0.0116–0.0147. D-OQ 0.0051, 0.0088–0.0104, 0.0177–0.0216. Peak training memory 0.390 GiB. H8 per cell: medians 1,619 s and 3,204 s. Block M training at P10-S1's lengths without H8 or the seed block: 216,279 cell-seconds, which is **10.0 h** on six workers. 0.035–0.049 and 0.071–0.077 at 65,536 slots: ADR-0021 lines 43 and 76. | Matches |
| Block X low / central / upper of about 25 / 45–50 / over 120 h | ADR-0024 §12 | My arithmetic on the stated assumptions gives 8.9 / 17.7 / 71 h for 128K/16K, against the draft's 9 / 19 / 75. 6·U_P cells come to about 6–7 h at U_P 16,384. | Consistent. Correctly called unbounded before a rehearsal. |
| "P10-S1 passed at 0.98–0.998 on its first to third reading" | ADR-0024 §16 | The records show: rehearsal timing 1.34 and then 0.73 (passed on the second reading, ADR-0021 line 1260); registered timing started at 0.98 (line 1372); supplement 0.998 on one attempt (`throughput_supplement.json`). | Inaccurate wording (B-M8) |
| "Six workers at about 0.4 GiB" for A1 reads | ADR-0029 §13 | 0.390 GiB is the **training** peak. P10-S1's **evaluation** tasks peaked at 1.415 GiB (`evaluate.manifest.json`, 193 tasks). | R-N11 |
| Seed registry | both | Checker PASS. Allocations agree with the roles and counts each draft states, except lane L's data (section E). | see E |

## C. First-review findings: judgement of the revision

| First-review finding | Revision says | My judgement |
|---|---|---|
| F1 U_P and rate search depend on each other; R2/D-OQ units (BLOCKING) | FIXED §7.1 | **PARTLY FIXED.** The order terminates, gives a unique result and uses calibration draws only (blind to registered seeds). R2 has units and D-OQ no longer has a 1,024-slot unit. Three ambiguities remain (B-M3). |
| F2 tree label misassigns causes (BLOCKING) | MOVED, ADR-0029 §6–§8 | **PARTLY FIXED.** The P/C/J/H/R table labels every replicate exactly once. Remaining: the §3 overstatement (R-N2), the JOINT row's causal claim (R-N8), undefined label equality (R-N5), and the contradiction over "none" (R-N6). |
| F3 N/8 (REQUIRED) | MOVED, §8.4 | **FIXED** (512; sufficient at every larger budget; measured counts printed). How c\* is aggregated across replicates is open (R-N5). |
| F4 matched compute made primary after observation | FIXED §9.2 | **PARTLY FIXED.** The rule is the one the first review proposed. The disclosure beside it is inaccurate: removing D-BEST from the blocking side **is** a relaxation relative to ADR-0021 §8.5 (B-M4). |
| F5 efficiency counterfactual; rows 1–2 | FIXED §9.5 | **FIXED** |
| F6 DEP snapshots | FIXED §8.1 | **FIXED** (ruling 22 (g) kept; the record and the a_use floor are stated) |
| F7 DEP-c reasons | FIXED | **FIXED** |
| F8 U_P against run length | MOVED, ADR-0029 §9 | **FIXED** (co-primary; no single action; plateau tag; disclosure placed with the rule). See R-N16 on likely outcomes. |
| F9 R-CONFIRM like for like; cost | MOVED, §10; cost ANSWERED | **FIXED**, and the cost answer is **correct** (0.87 h; section B). The first review's "about 7" was wrong. |
| F10 cost projection | FIXED §12, §17 | **FIXED**, except that the upper case assumes a finite U₀ (B-M2) |
| F11 recall records misdescribed, unsealed | MOVED, §4, §11 | **FIX INTRODUCED A NEW PROBLEM.** The description and the seal are right. The index-recall gate, as the first review itself worded it, compares two different query populations (R-N1). |
| F12 one ADR, two freezes | FIXED (split) | **FIXED.** Recorded PENDING HUMAN LEAD RULING in both headers (ADR-0024 §21 item 8, ADR-0029 §16 item 1). The closure ledger does not follow it yet (section E). |
| F13 PK-OQ | FIXED (removed) | **FIXED** in ADR-0024. ADR-0027 still cites "ADR-0024's PK-OQ" (section E). |
| F14 quiet machine | FIXED §10, §16 | **FIXED.** The idle claim is gone, there is a deadline, and the unreachable table is correct (checked row by row). One residual wording point (B-M8). |
| F15 disclosure placement | FIXED | **FIXED** |
| F16 Lane R gates; G9 exemption | MOVED, §5, §11 | **PARTLY FIXED.** All the requested gates are present. Gate 3 is defective (R-N1). Gate 4 is bit-exact where floating point does not guarantee it (R-N3). |
| F17 snapshot schedule; arm names; NOT FULL cost | FIXED §7.2, §12 | **PARTLY FIXED.** Half-points are listed and D-OQ is named. The loaded-cell schedule lacks the U_P multiples that matched compute needs (B-M1). |
| F18 crowding at 131,072 | FIXED | **FIXED** |
| F19 H8 | ANSWERED | **Answer accepted.** The loss is stated (§4, §20) and the choice stays open (§21 item 5). |
| F20 bridge duplication | MOVED | **FIXED by construction** (own draws) |
| F21 measurement definitions | MOVED | **FIXED**, but with the new §3 overstatement (R-N2) |
| F22 STORE HOLDS MORE cost condition | FIXED | **FIXED** |
| F23 quotation details | FIXED / ANSWERED | **FIXED.** The answer on 1.946 is correct: ADR-0021 line 1271 does record "under unrelated load (load average about 5.4)". The first review was wrong to call it a gloss. |
| F24 replicate accounting | MOVED, §8.2 | **FIX INTRODUCED A NEW PROBLEM.** The per-replicate rule is stated, but draft 1's cell-level NOT EVALUABLE rule ("WEAK REFERENCE in ≥ 2 replicates") was lost, so §9 item 4 is undefined (R-N4). |
| F25 tags | FIXED | **FIXED** |
| F26 small items | FIXED | **FIXED** |
| F27 seeds | ANSWERED | **Answer accepted then.** The text is now stale: both drafts say the registry is "being written" (section E). |
| Points A, B, C | FIXED | A: FIXED. B: PARTLY (R-N1, R-N2, R-N8). C: FIXED, pending the human lead's ruling. |

---

## D. Errors in the first review (kept on the record)

1. **F9:** "20 cells cost about 7 charged hours." Wrong. The cited figures give 0.87 h, and the actual cells took 0.87 h.
2. **F23:** "'under unrelated load' is the drafter's gloss." Wrong. ADR-0021 line 1271 records it.
3. **Section B / F21:** "Whenever all eight selected slots lie in one branch, the prior's total-variation effect is exactly zero." Wrong. The selection can change without the prior.
4. **F11 / F16:** "I256@512's CR8 must equal the recorded index recall at every checkpoint read." The recorded quantity is not CR8 over trained facts (R-N1). The revision implemented this wording and inherited the defect.
5. **F4:** the proposed registration was said to remove "the post-observation relaxation of the positive". It still drops D-BEST from the blocking side, which ADR-0021 §8.5 included. That part is a relaxation, chosen after D-BEST favoured D-OQ in 5 of 5 replicates.

---

## E. New findings

### ADR-0029

**R-N1. BLOCKING — §11 gate 3 (index part) compares two different quantities.**
- What P10-S1 recorded: `IVFMemory._top_flat` accumulates recall over **every query of the Panel A pass** of `_read_record` (`evaluate.py`, reset at line 311, read at line 324). Through `panel_counts` that is:
  - the main read and the **address-swap read** (`model.select(h, tok_sw)`);
  - all eight records of every context, including facts outside the cell and unseen-control facts;
  - each record weighted by how often it occurs.
- What the gate compares it with: CR8 of §7, "over all trained facts of the cell".
- Result: the two values will differ. The gate fails, the cell is "NOT EVALUABLE and not repaired", so every F-OQ cell is NOT EVALUABLE, and R-DIAGNOSIS is NOT EVALUABLE by §9 item 4.
- Tree part: the recorded `tree_recall` uses all trained facts, as CR8 does. But it takes the exhaustive top 8 with `topk` (no id tie rule) over `F.normalize(keys)` at the default eps, not `stable_top`.
- **Change.** Replace gate 3 with:
  > "Recall reproduction (sealed values). (a) P10-S1's `tree_recall`, recomputed by its own definition (all trained facts' oracle codes; exhaustive top 8 by `topk` of cosine against `F.normalize(keys)`; integer hit and total counts), equals the recorded `tree_recall_of_exhaustive_top8` at U_P. (b) P10-S1's index recall, recomputed by its own definition (every query `IVFMemory._top_flat` receives during the Panel A pass of `studies/p10s1/evaluate.py` `_read_record`, the address-swap reads included; top 8 of the masked scores against `stable_top` of the unmasked scores), equals the recorded `ivf_measured.recall_of_exhaustive_top8` at every checkpoint read. These gate quantities are not CR8 and enter no label."

**R-N2. REQUIRED — §3 line 58 and line 59 overclaim.**
- Replace "If all eight selected slots lie in one branch, the prior has no effect on the read at all" with:
  > "If all eight slots selected with the prior lie in one branch, the prior does not change their weights; it may still have decided which slots were selected."
- Replace "never received that fact's gradient" with:
  > "received no gradient from that fact at any update at which the router did not visit its branch; routing changes during training and its history is not recorded."

**R-N3. REQUIRED — §11 gate 4's exactness identities are not guaranteed in floating point.**
- `softmax(s + c)` and `softmax(s)` agree mathematically, not bit for bit. Adding c can also create or remove a tie at the 8th place.
- T2 and T3 computed through `q @ keys.T` and Tv computed through `bmm` may round differently.
- **Change.** Either implement T2 and T3 as Tv with v = N/256 through the same code path, or add: "selections identical except at float ties (counted and printed); weights equal within 1e-6".
- State also that v = N/256 is an extra gate read at 4,096 and 16,384 slots, since the sweep stops at v = 8.

**R-N4. REQUIRED — "cell NOT EVALUABLE" is undefined at cell level.**
- §8.2 gives a label per replicate and "≥ 4 of 5, else MIXED". §9 item 4 and §11 ("a cell that fails gate 2 or 3 is NOT EVALUABLE") use a cell-level NOT EVALUABLE that no rule defines.
- **Change** (restores draft 1's count):
  > "A cell is NOT EVALUABLE at a checkpoint if at least 2 of its 5 replicates are NOT EVALUABLE (a gate failure of either arm, or WEAK REFERENCE)."

**R-N5. REQUIRED — what counts as "the same label" is undefined.** This is the lead's choice and must be written before the freeze.
- Does the FULLY/PARTLY suffix count for the 4-of-5 rule (§8.2), CELL-DEPENDENT (§9 item 1), CHECKPOINT-DEPENDENT (§9 item 3) and R-CONFIRM (§10)? Does the c\* value of the index label count?
- Suggested text:
  > "Labels are compared by row name only; suffixes and c\* are printed. A cell's c\* is the median of its replicates' c\*."
- Also undefined:
  - "gap exists" and NO GAP when the panels disagree. Suggested: "NO GAP if the gap is below 0.5 on both panels; a replicate with a gap on one panel only is MIXED-PANEL and satisfies no condition."
  - R has no panel; say so.
  - The relative order of §9 items 2–4: item 4 should be applied first.
  - R-CONFIRM when A1 is NOT EVALUABLE: it should be NOT APPLICABLE.

**R-N6. REQUIRED — the draft contradicts itself on what NOT IDENTIFIED and CONTENT recommend.**
- §1 says NOT IDENTIFIED "recommends nothing". §9 "The note's 'none'" maps CONTENT **or** NOT IDENTIFIED, together with INDEX DOES NOT APPROACH FLAT at both checkpoints, to "consider a more fundamental change".
- CONTENT therefore carries two actions.
- Choose one of the two readings and put the choice in §16 (PENDING HUMAN LEAD RULING).

**R-N7. REQUIRED — departures from the directed table of note §5.2 are not put to the human lead.**
- The note (binding direction) maps "exact search restores" to "improve the router" and "does not restore" to "improve memory training".
- ADR-0029 changes both:
  - T2 alone restoring gives JOINT with no single fix;
  - "does not restore" gives CONTENT only with R, otherwise EXACT SEARCH HARMS or NOT IDENTIFIED with no action.
- The reasons are sound (first review F2), but they change directed content. Add to §16: "Departure from note §5.2's next-action table (rows 1–2) as in §8.3. PENDING HUMAN LEAD RULING."
- Nothing else of §5.2 or §5.3 was lost in the move. Checked: candidate recall, attention mass, end-task accuracy, prior effect, budgets 128–2,048 where feasible, loaded cells, more than one checkpoint, retention defined on task performance with the improvement above baseline also assessed, DICT kept, a retrieval change never mixed with a training change.

**R-N8. REQUIRED — the JOINT row claims a cause the reads cannot identify, and C may be an inert test.**
- With a confident router (temperature 0.2), the prior on unvisited branches is very negative, so T3 ≈ T0. Removing the restriction then shows up only in T2, and the row reads "Both must change together".
- **Change.**
  - Row 6 claim: delete "Both must change together;". Keep "Only removing both closes most of the gap; no single fix is indicated".
  - Print, with every tree label, the share of facts whose T3 selection equals T0's (whether C was testable).
- Whether C should become NOT TESTABLE above some share is PENDING LEAD REVIEW.

**R-N9. REQUIRED — A2 cannot run "studies/p10s1 called unedited" without addressing its seed gate.**
- `studies/p10s1/core.py` lines 820 and 961 refuse data seeds outside 210001–219999. The bridge draws are 290001 and up (registry §4.3 item 4).
- **Change.** Add to §10: "P10-S1's own `seed_check` is not applied to the bridge draws; ADR-0029's seed gate (§11 item 5) replaces it."

**R-N10. ADVISORY.** The loaded-cell "secondary line" has no name and no combination rule. Name it (for example R-DIAGNOSIS-LOADED, descriptive) or call it printed only.

**R-N11. ADVISORY.** In §13, cite the evaluation peak of 1.415 GiB per worker, not 0.4 GiB.

**R-N12. ADVISORY — sealing practice.** The counts that gate 2 needs sit in the same `eval.json` as the sealed keys. Require a whitelist extractor, and require that no one prints or opens any `eval.json` outside it.

**R-N13. ADVISORY.** Note §3 (the outside note, not the human lead's direction) asked that retention be "read against the dense and the flat baselines". State why D-OQ is not a reference here.

**R-N14. ADVISORY.** PRIORS cannot tell reweighting from boundary selection. Print the T1w split inside the label, for example PRIORS (mainly weights / mainly selection), descriptively.

**R-N16. ADVISORY, PENDING LEAD REVIEW — CHECKPOINT-DEPENDENT is the likely outcome.**
- A pair of two labels, each with about 10 values, must match at both checkpoints, and the disclosure says the gaps move in opposite directions.
- Option: apply the checkpoint rule to the tree label and the index label separately.

### ADR-0024

**B-M1. REQUIRED — matched compute cannot be read at the loaded steps.**
- §7.2 item 2 gives loaded cells only ladder points, their halves, and the doubling grid below 32,768.
- Δ_MC and the MC-T reading (§8.2) need the smaller cell at U_P × {1.25, 1.5, 2.5, 3}. At U_P 8,192 that is 10,240, 12,288, 20,480 and 24,576, which the schedule lacks.
- The smaller cell of C1 and C2 is the loaded one, and it is also the cheaper one, so it is the one read at a multiplied snapshot (F-OQ 0.0050 against 0.0091 s per update).
- **Change.** Append to §7.2 item 2: "and at U_P × {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} of the cell's row".

**B-M2. REQUIRED — the U₀ calibration ladder (and the U_P ladder) has no design ceiling.**
- P10-S1's 2K/256 was not full at 262,144 updates (§2 item 6).
- As written, a cell that never becomes full keeps the calibration PAUSED indefinitely, and block M cannot freeze.
- **Change** (§7.2 item 4 and §15):
  > "If a cell is not full on all four views when the calibration cap is reached, the work returns to the human lead before the freeze (as for RATE AT EDGE)."

**B-M3. REQUIRED — three ambiguities in the order rule (§7.1).**
- "that row's units" → "the units whose selection cell lies in that row".
- "at most twice per unit" → "at most twice per unit in total, across both selections".
- Add:
  > "U_P is not re-checked at the re-selected rates; R2's unit is re-selected with its row, and a registered REF failure that follows is NOT_EVALUATED as §9.1 row 1 states."

**B-M4. REQUIRED — the disclosure in §9.2 is inaccurate.**
- Replace "It is built so that nothing the store gains from it is a relaxation" with:
  > "One part is a relaxation: D-BEST, which ADR-0021 §8.5 let block a positive and which favoured D-OQ in 5 of 5 replicates, is now descriptive; the saturation label (DENSE HOLDS MORE at no loaded cell) is the remaining guard on that side."

**B-M5. BLOCKING for lane L (not for block M) — lane L is not specified enough to approve.**
1. **"The address swap is not defined for a learned query" is wrong.** ADR-0020 §8.1 (line 279) defines a read swap and a_use for learned queries. ADR-0023's own composite uses it (condition 6, a_use ≥ 0.95 × accuracy). The invented measure, correct-with-memory and wrong-with-memory-disabled, is weaker: it is not fact-specific, and a shared or collapsed read passes it. This is a missing rule, not a free choice for the lead.
2. **The success test needs A6, not F-OQ.** ADR-0023 line 395 (working copy): "A lane that applies this study's composite must run A6 as frozen here (R1 codes, learning rate 0.003)… An oracle arm with a searched learning rate is not A6, and condition 1 is not defined against it."
   - ADR-0024 §13 (line 298) applies the composite "unchanged" but names only F-OQ, which goes through §7.1's rate search. **The coordinator's point (1) is correct.**
   - Lane L must add A6 at 0.003, or F-OQ only where its selected rate is 0.003.
3. **The step compares two different training lengths.** Each cell runs at its own cell type's T (loads 2 and 0.5 have different T).
4. **The F-OQ comparator "snapshot added there" does not exist.** ADR-0023's T is at least 1,024 exposures, which is 65,536 updates at 8,192 facts. Block M's F-OQ runs 49,152 updates at those cells and is frozen before lane L. The comparator cells must be trained anew.
5. **Data are undefined.** §13 says "this study's draws" (P10-S1 layout). SEED_REGISTRY line 143 reserves 247001– for lane L's own data in ADR-0023's layout, "never mixed with P10-S1's layout", and marks it PENDING. **The coordinator's point (2) is correct.** ADR-0023's composite also needs H1/H2 and a probe set from its own generator.
6. **There are no CEILING or NOT LOADED rows.** At the 2K steps both cells are near ceiling (F-OQ a_use 0.999 at 2K/1K at the run length), so NO GAIN is near-certain and would read as a negative.
- **Change.** Mark §13:
  > "TO BE SPECIFIED IN A REVISION BEFORE LANE L'S FREEZE; not part of this approval. Registered now only: OMITTED — NOT LICENSED, OMITTED — NOT LICENSED AT THE FREEZE."
- Delete the lane L half of §21 item 7.

**B-M6. REQUIRED — block X's entry condition and its draws.**
- **The conditioning is sound as a pre-registered gate.** It is fixed before observation; all five replicates enter, so no replicate is selected; X-CAPACITY is computed from X's own cells.
- **But X re-uses block M's draws.** Its 131,072-fact tables extend the very draws whose first 32,768 facts produced the observed C2 success, so X runs on draw sets selected for a favourable C2. Two further points:
  - Funding after block M is decided with block M's outcomes visible.
  - Re-using 32K/16K in N3 requires that the extended table keep the 32,768-fact prefix, and its streams, bit-identical.
- **Change.** Either use fresh draws for block X (registry headroom: 65 sets), or add beside §12:
  > "X runs on the draws selected by C2's success, and its funding is decided with block M's outcomes known; X-CAPACITY is read conditionally on both. The extended tables must reproduce block M's first 32,768 facts and streams bit for bit (a gate)."
- PENDING LEAD REVIEW.

**B-M7. ADVISORY.** "§9.3's table with CAPACITY_SUPPORTED read as…" leaves block X's arm classes and the role of F-OQ-IVF in X to interpretation. Write X's arm classes out for its one transition (C3, N3).

**B-M8. ADVISORY.** In §16, replace "passed at 0.98–0.998 on its first to third reading" with:
> "passed at 0.73 on its second reading after 1.34 (rehearsal timing, ADR-0021 §25.16), at 0.98 (registered timing start) and at 0.998 (supplement, first reading)".

**B-M9. ADVISORY.** The arm-level dense label is vacuously both AHEAD and NOT BEHIND when an arm has no CAPACITY STEP. Print NOT APPLICABLE there.

**B-M10. ADVISORY.** Closure ledger item 110 ("185 cells read", unlabelled rehearsal timing, two cap figures) is not named in §18. Name each.

**B-M11. ADVISORY.** The file name still says "…-and-routing-diagnosis".

**B-M12. REQUIRED (mechanical).** The seed text is stale (section F).

**B-M13. REQUIRED — which arms may carry a label another study uses for entry.** (The coordinator's point (3).)
- §9.3 row 3 lets **F-OQ-IVF** (evaluation-only: no training, no rate search, no MC-T cost of its own) make C-CAPACITY positive.
- ADR-0027's Route B reads "an arm CAPACITY_SUPPORTED and NOT BEHIND DENSE" as entry and gives each such arm its own S4 memory arm. An evaluation-only read would then enter a quality-against-training-cost study that it has no training cost for.
- **Change.** Add to §9.3:
  > "A label that another study uses for entry may be carried only by a trained arm (F-OQ, T-OQ); F-OQ-IVF's CAPACITY_SUPPORTED is printed and enters C-CAPACITY, but it names F-OQ's trained memory read post hoc and qualifies no arm for entry elsewhere."
- PENDING LEAD REVIEW on whether F-OQ-IVF should enter C-CAPACITY at all.

---

## F. Cross-reference mismatches

| File | Line | What it says | What it must say |
|---|---|---|---|
| ADR-0024 | 100 | Seeds "assigned in SEED_REGISTRY.md (being written)"; G9 "against every range ADR-0021 §6.3 lists" | "assigned in SEED_REGISTRY.md §4.2: initialisation 330101–330105 (replicate r → 330100 + r); calibration 330191 (draw 1), 330193 (draw 2) on draws 249001, 249101; rehearsal 330192 on 249201; test mode 330198–330199; tests 933001–933999; lane L: PENDING (registry 247001–, 330111–330115). G9 runs a copy of `seed_registry_check.py` with R2 and R3 expanded (registry §4.3 item 5)" |
| ADR-0024 | 297–298 | Lane L on "this study's draws"; composite applied "unchanged" against F-OQ | As B-M5: data source fixed or PENDING, matching registry line 143; A6 at 0.003 as ADR-0023 line 395 requires |
| SEED_REGISTRY | 143 | Lane L own data "if needed; PENDING" | Must match whatever ADR-0024 §13 decides |
| ADR-0029 | 87 | "SEED_REGISTRY.md (being written)" | "§4.2: bridge draws 290001 + 100(d−1), d = 1..5 (index seed base + 60); I64 seeds 298001–298003; bridge initialisation 330601–330605; rehearsal draw 299201, initialisation 330692; test mode 330698–330699; tests 938001–938999; P10-S1 seed whitelist bypassed (registry §4.3 item 4)" |
| CLOSURE_LEDGER | 16 | "S1 (ADR-0024, capacity scaling, with the frozen-checkpoint routing diagnosis lane)" | "S1 (ADR-0024, capacity scaling); routing diagnosis in draft ADR-0029 (P10-I-R), split PENDING HUMAN LEAD RULING" |
| CLOSURE_LEDGER | 28, 106, 107 | "P10-I-S1" / "P10-I-S1 (routing diagnosis lane)" | "P10-I-R (ADR-0029; split PENDING HUMAN LEAD RULING)" |
| ADR-0027 | 49 | "CAPACITY-POSITIVE (ADR-0024 section 10.3)"; "dependence conditions at the snapshots the verdicts read"; "STORE NOT BEHIND under both cost readings"; "largest funded transition" | "§9.3"; "at every snapshot up to the run length (§8.1)"; "in MC-A, MC-T and MU"; C-CAPACITY covers 1,024→16,384 only, and X-CAPACITY is a separate line (state whether it enters); trained arms only (B-M13) |
| ADR-0027 | 51 | "Lane R (R-DIAGNOSIS)" of ADR-0024 | "ADR-0029's R-DIAGNOSIS" |
| ADR-0027 | 68, 173 | "ADR-0024's PK-OQ"; "include on Route B, where ADR-0024 defines PK-OQ" | ADR-0024 no longer defines PK-OQ (removed, Stage B); defer or define |
| ADR-0027 | 83, 108 | "ADR-0024 section 9.2" (cost readings), "section 10.2", "section 10.5" | §8.2, §9.2, §9.5. The quoted rule is now "matched compute under both cost measures and matched updates" |
| ADR-0028 | 62 | ADR-0024 "has no learned-address lane" | "has a conditional lane L (LEARNED-ADDRESS, flat memory, licensed cells ≤ 8,192 facts, not yet specified), which is not Q2's composed system" |
| ADR-0026 | 283, 419 | "routing-quality outcome line belongs to ADR-0024"; "routing work of ADR-0024" | "ADR-0029 (P10-I-R)" |

The labels that drafts read from each other exist with the cited names and meanings, except as listed above. Checked:
- ADR-0024 reads from ADR-0023: L_Q, Line Q, "OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023)", reference regime, convergence status.
- ADR-0027 reads from ADR-0024: CAPACITY_SUPPORTED, NOT BEHIND DENSE, STORE NOT BEHIND.

## G. Choices reserved for the human lead: are they his?

**ADR-0024 §21**

| Item | Judgement |
|---|---|
| 1 Task | His |
| 2 Block X | His, but the draw-selection issue (B-M6) belongs in the item |
| 3 Lane L timing | His |
| 4 Dense reading | His, with the D-BEST disclosure corrected (B-M4) |
| 5 H8 | His |
| 6 Symmetric split rule | His |
| 7 DEP-c floor | His |
| 7 Lane L's dependence measure | **Not a free choice.** A registered measure exists (ADR-0020 §8.1); this is a missing rule (B-M5) |
| 8 Split | His |
| 9 Worker count | A cost rule ("the count with the lower projected charged hours"), not a scientific choice |

Missing from the list:
- the calibration ceiling (B-M2), which is a missing rule;
- the arms entitled to carry an entry label (B-M13).

**ADR-0029 §16**

| Item | Judgement |
|---|---|
| 1 Split | His |
| 2 Co-primary checkpoints | His |
| 3 R and closure figures | His |
| 4 Retention rule | His |
| 5 Fund A2 | His |
| 6 Stage B on A1 alone | His |
| 7 Order | His |

Missing from the list:
- the departure from note §5.2's next-action table (R-N7);
- the "none" contradiction (R-N6);
- the definition of label equality (R-N5), which is a missing rule.

## H. The human lead's three audit points, answered for the revised pair

1. **U_P against the run length.**
   - Handled soundly now. ADR-0029 makes them co-primary, recommends no single action when they differ, adds a plateau tag, places the disclosure beside the rule, and pins A2 to both checkpoints.
   - Remaining: equality of labels is undefined (R-N5), and CHECKPOINT-DEPENDENT is a likely result (R-N16).
   - In ADR-0024 both are printed for the sparse-arm label, and neither is called "the" label.
2. **Candidate-recall measurements.**
   - The definitions match the code. The prior is constant per branch, so it acts only through cross-branch weights and boundary selection.
   - Recall enters one rule, CONTENT, as a necessary condition.
   - The index-recall reproduction gate is defective and would void the study (R-N1, blocking). The §3 wording overclaims (R-N2).
   - The three explanations are separated at read time only partly. Priors are separated (T1, T1w). Candidates are separated only when T3 differs from T0 (R-N8). Content is separated only under high recall without exact-search harm. EXACT SEARCH HARMS, NOT IDENTIFIED and all training-time causes stay unidentifiable.
3. **Independent outcome lines manageable?**
   - Yes for block M (3 lines, 120 cells) and ADR-0029 (R-DIAGNOSIS, R-CONFIRM). Each has its own freeze and an ADR text outside the frozen set.
   - Block X (X-CAPACITY) is properly separate but unbounded in cost.
   - Lane L is not yet a specified line (B-M5).
   - Total: 5 lines in ADR-0024 and 2 in ADR-0029. Roughly 8 approval or decision points across ADR-0024's three parts, and 4 for ADR-0029.

---

## Appendix — logic of the scripts

- `b1_bridge_cost.py`:
  - Parse each `train.manifest.json` label: kind, arm, facts, slots, draw, init, optional `_u`, optional `_y`, rest. Where the label omits `_y`, take `run_updates` and `u_p` from the cell's `train.json` (metadata only).
  - Seconds per update = task `seconds` / `run_updates`. Median per (arm, cell) over the 5 registered cells with no suffix.
  - Bridge = 49,152 × (F + T at 8K/4K) + 98,304 × (F + T at 32K/16K), times 5, divided by 6 × 3,600.
- `b2_retention.py`:
  - i(a) = 5 − h₂(1 − a) − (1 − a)·log₂31.
  - Threshold = max(i(F0) − 0.25, 0.9·i(F0)), inverted by bisection.
  - Share = (a_req − 1/32)/(a_F0 − 1/32). Gaps = i(F0) − i(read) at the mean a_use of ADR-0029 §2.
- `b3_spu_all.py`: as b1, for every registered (arm, facts, slots, suffix).

`Astra review: NOT_PERFORMED`.
