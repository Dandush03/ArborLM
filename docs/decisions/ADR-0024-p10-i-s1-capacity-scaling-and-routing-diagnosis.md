# ADR-0024 — P10-I-S1: Useful capacity scaling, with a frozen-checkpoint routing diagnosis lane

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). **Drafted by:** the lead's workflow (Claude Fable 5.2). **SPEC: PENDING ASTRA REVIEW.** `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- **Study code** P10IS1. **Package** `studies/p10is1/` (new code only). **Config** `configs/p10is1_*.toml`. **Tests** `tests/test_p10is1_*.py`.
- **Origin.** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` (sections 2, 4, 5, 7) and `LITERATURE_AND_ROUTING_NOTE.md` (sections 4 and 5, binding direction for the routing lane). Successor of P10-S1 (ADR-0021), whose registered outcome the human lead accepted as recorded (`results/p10s1-run-2026-11-17/ACCEPTANCE.md`).
- **Immutability.** P1–P10 code, configs, records, thresholds, seeds and outcomes are not edited, revised or reopened. P10-S1's labels stand as registered. ArborLM is unproven research; no label below is a success claim.
- **Approval.** The human lead alone approves this specification, its budget and each run. The lead takes no Decision 1 or Decision 2 under this ADR without a recorded approval. Each lane is approved, frozen and run separately (§17).
- **Roles.** Specification review, implementation audit and recomputation: Opus 5.5 in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that ran each delegated task is recorded from session metadata. ADR-0012 stays not approved.

## 0. Two lanes, four outcome lines

| Lane | What it is | Outcome lines | Trains? |
|---|---|---|---|
| **C** — capacity scaling | P10-S1's questions on fresh seeds, with its audit's corrections, a fair rate search and (if funded) the transition 16,384 → 65,536 slots | C-CAPACITY, C-SATURATION, C-EFFICIENCY | Yes |
| **R** — routing diagnosis, Stage A only | New reads of P10-S1's existing frozen flat and tree checkpoints | R-DIAGNOSIS | No |

No line implies or substitutes for another. Each lane has its own frozen inputs, budget, stop rules and decisions. Stage B of the routing work (any new training architecture) is **outside this ADR**; if Lane R indicates it, it is a separate study with its own specification.

## 1. Questions, and what each outcome would mean

**Lane C.** With addressing supplied by an oracle, and with every trained arm given the same rate search: does a larger store retain more useful information about a fixed fact set at matched updates, at matched compute and against the smaller store when full; does a full store keep its bits per slot as it grows; does a larger store reach a fixed level sooner; and how does each compare with a dense map of equal parameters?

| Line | Positive would mean | Negative would mean | Inconclusive / not tested |
|---|---|---|---|
| C-CAPACITY | Within the sizes read, the store passes a necessary condition of the storage claim, and the dense map of equal size is not ahead at matched compute or when full | The store does not gain from slots, or it does and the dense map is ahead at every cell read | No decision on this line; the reason is printed |
| C-SATURATION | A full store kept at least three quarters of its bits per slot per fourfold step | It did not, for both the flat and the tree memory | A size was not full within its budget, or the arms disagree |
| C-EFFICIENCY | A larger store reached 3.0 bits per fact in fewer updates and less cost under **both** cost readings, and the dense map was not faster at any cell under either | No arm did, or the dense map was faster at every cell under both readings | The readings or the cells disagree; each is printed |

Every Lane C positive carries `STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK` (§3). No Lane C outcome can establish milestone question 1.

**Lane R.** On the memories P10-S1 trained, is the tree's lower quality explained by the router's candidates, by the stored content, or by the branch priors in the read; and does an index built after training keep the flat memory's quality at a sparse candidate budget? R-DIAGNOSIS is a diagnosis, not a positive or a negative for ArborLM: it names which of the next actions of the note's section 5.2 the evidence points to (§14). NOT EVALUABLE and CELL-DEPENDENT are registered values of the line.

## 2. Background: registered findings (quoted from the records)

From `results/p10s1-run-2026-11-17/OUTCOME.md`, `ACCEPTANCE.md`, `audit/AUDIT.md`:

1. Registered outcome: CAPACITY-INCONCLUSIVE (F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED); SATURATION-INCONCLUSIVE (F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED); EFFICIENCY-NEGATIVE (DENSE FASTER); milestone question 1 not established. Also TREE_BEHIND, DICT DOMINATES ON THIS TASK, DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ.
2. **Dependence (audit §2, D7).** Every DEPENDENCE_FAILED verdict comes from `a_use ≥ 0.95 × raw accuracy` at 1,024–2,048 updates, at a_use 0.256–0.414 (ratios 0.9262–0.9486 across arms; 0.9425–0.9471 for the F-OQ and F-OQ-IVF failures at 2,048 updates). The reference arm R2 fails the same condition 12 times at 512–1,024 updates. In one disclosed case the excess of correct over useful answers (157) is below what the memory-disabled backbone gets right on the non-retained facts (173).
3. **Dense speed (audit §3, D4).** DENSE FASTER for T-OQ holds in 5 of 5 replicates at 2K/4K and 0 of 5 at 8K/16K. At 8K/16K, D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds. The code applied an any-cell rule (`studies/p10s1/analysis.py`, line 631) that ADR-0021 §8.8 does not state.
4. **Dense quality (audit §5, D3).** At 32K/16K, F-OQ against D-OQ: matched updates d = −0.238 to −0.450 bits (4 of 5 at or below −0.25); matched compute d = +0.24 to +0.33 (F-OQ ahead, 5 of 5); D-OQ's best snapshot d = −0.68 to −0.87 (5 of 5). At saturation D-OQ holds 1.76–1.87 bits per fact more than F-OQ at both loaded cells (5 of 5).
5. **Seed block (audit D1; `ERRATUM_SEED_BLOCK.md`).** `analysis.py` lines 167–169 store two reads under one key; 28 printed lines are wrong (corrected: the data draw dominates in 24 of 28).
6. **Saturation (audit §4).** 1,024→4,096: F-OQ ρ 3.785–3.875 (PROPORTIONAL, 5 of 5); T-OQ ρ 2.389–2.922 with two replicates NOT FULL at 8K/1K (last-doubling gains 0.1059 and 0.132 against the limit 0.10). 2K/256 was not full within its ceiling of 262,144 updates and was not run; 128K/16K was not funded (ADR-0021 §5.1, §25.15).
7. **Rates.** Memory arms ran at 0.003, untuned by design; D-OQ at its calibrated 0.1 or 0.03 (audit §6; ADR-0021 §10.1 item 3).
8. **Tree against index, by checkpoint** (note §5.1; mean a_use, U_P → run length): 8K/4K index 0.631 → 0.706, tree 0.469 → 0.769; 32K/16K index 0.483 → 0.540, tree 0.401 → 0.697; 8K/1K index 0.306 → 0.497, tree 0.176 → 0.416. The flat exhaustive read is 0.948 → 0.996, 0.916 → 0.992 and 0.390 → 0.654 at the same cells.
9. **Throughput.** The registered stage failed in 1.4 s on a plan mismatch; the supplementary record is descriptive only (`supplement/throughput_supplement.json`).
10. **Never run:** any cell at 65,536 slots under ADR-0021 revision 5; 128K/16K beyond 65,536 updates (revision 4's calibration saw 1.46–1.52 bits per fact there, still gaining 0.54–0.62 per doubling; ADR-0021 §1 fact 13).

## 3. What a capacity result on this task can and cannot show

The task is recall of trained random facts: 8-byte synthetic records, a 5-bit answer, the fact's identity given by an oracle. A hash table solves it exactly with one probe (DICT: 32,768 of 32,768 correct in P10-S1).

- **It can show** properties of the store and its optimizer: whether gradient descent through a sparse top-8 read writes more facts into more slots, how interference grows with facts per slot, what a full slot holds, and how these compare with a dense map of equal parameters. These are necessary conditions of ArborLM's storage claim.
- **It cannot show** value that a lookup does not provide: generalisation, updating beyond key-value recall, use by a language model, or learned addressing. A positive here is not "useful capability".
- **Decision: the task is not changed in this ADR.** Changing it together with the audit's corrections would confound them, and the corrections are what the human lead carried into this study. Every Lane C label is printed with DICT DOMINATES ON THIS TASK, and the milestone reading available to Lane C is capped at "necessary condition met / not met / not established". Value beyond lookup is a question for a study designed for it (open choice 1, §23).

---

# PART C — Capacity scaling

## 4. Arms, controls and baselines

| Arm | What it is | Learned | Isolates |
|---|---|---|---|
| **F-OQ** | Flat memory, oracle query code (width 16), all keys scored, top-8, temperature 0.2 — as ADR-0021 §3 | keys, values, output projection, gate | The store with exhaustive retrieval |
| **T-OQ** | Learned tree: router picks 2 of N/256 branches, top-8 of their 512 keys, branch priors in the scores — as ADR-0021 §3 | router, keys, values, projection, gate | Hierarchical sparse retrieval trained jointly |
| **PK-OQ** (new baseline) | Product-key memory, defined in §4.1 | two sub-key tables, values, projection, gate | A structured sparse address that is not a tree |
| **D-OQ** | Dense map of the same code, parameters within 0.1% of F-OQ's — as ADR-0021 §5.3 | both layers, gate | Parameters alone |
| **R2** | One dedicated slot per fact | values, projection, gate | Reference rung; validity of every check (§9) |
| F-OQ-IVF (evaluation only) | F-OQ's keys read through the registered index (N/256 lists, at least 512 candidates) | nothing | Post-hoc sparse retrieval, as P10-S1 read it |
| DICT, no-memory, unseen-fact control, KNN-W | As ADR-0021 §5.5 | nothing | Lookup baseline; chance; leakage; a non-oracle baseline |

One change per comparison: cells of one row differ only in slots; arms at one cell differ only in the addition. **H8 is not run** (proposed; open choice 6): its label KEY-LEARNING-LIMITED was False and F-OQ was at or above H8 at every cell at the run length (audit §6); its cost pays for PK-OQ.

### 4.1 PK-OQ, defined here in full

The slot count is N = n² (n = 32, 64, 128, 256 for 1,024, 4,096, 16,384, 65,536). The oracle code q (width 16, unit) is split into halves q₁, q₂ (width 8), each re-normalised. Two sub-key tables K₁, K₂ of shape [n, 8], initialised as F-OQ's keys. Slot (a, b) has score [cos(q₁, K₁ₐ) + cos(q₂, K₂ᵦ)] / (2 · 0.2). The read takes the top 8 of each half, forms the 64 pairs, and takes the top 8 pairs by score, which is the exact top 8 of the product for a sum of scores. Weights, value read, output projection and gate are F-OQ's. Counted work: 2n scores of width 8 and 64 sums. It has fewer key parameters than F-OQ (16n against 16N); the count is printed. The construction follows the idea of Lample et al. (NeurIPS 2019); **the drafter has not re-read the paper**, and nothing here depends on it. PK-OQ is a baseline: it enters the sparse-arm comparison (§10.6) and no outcome clause.

**Placement (task item 9).** PK-OQ belongs in Lane C, because Lane R trains nothing and a baseline needs the grid, panels, controls and rate search Lane C already has. The note's §5.2 lists product-key memory under Stage B; this is flagged as a possible conflict with the direction record (open choice 5).

## 5. Grid, steps and blocks

"8K/1K" is 8,192 facts in 1,024 slots. Load is facts per slot.

| Facts \ Slots | 256 | 1,024 | 4,096 | 16,384 | 65,536 |
|---|---|---|---|---|---|
| 2,048 | 2K/256 (8; F-OQ only) | 2K/1K (2) | 2K/4K (0.5) | | |
| 8,192 | | 8K/1K (8) | 8K/4K (2) | 8K/16K (0.5) | |
| 32,768 | | | 32K/4K (8) | 32K/16K (2) | *32K/64K (0.5)* |
| 131,072 | | | | *128K/16K (8)* | *128K/64K (2)* |

| Block | Cells | Status |
|---|---|---|
| **M** (main) | The seven cells of ADR-0021 §5.1 and 2K/256 | Registered if Lane C is approved |
| **X** (the transition 16,384 → 65,536; italic cells) | 128K/16K, 128K/64K, 32K/64K; R2 at 128K/128K | **In scope, separately funded** (open choice 2). If not funded, every capacity outcome prints "16,384→65,536 NOT TESTED — NOT FUNDED" |
| **B** (bridge) | F-OQ and T-OQ at 8K/4K and 32K/16K at P10-S1's rate 0.003 | Descriptive in Lane C (§7); read by Lane R's confirmatory step (§15) |

Steps (same facts, four times the slots): loaded steps C1 (8K/1K→8K/4K), C2 (32K/4K→32K/16K), C3 (128K/16K→128K/64K, block X); control steps N1 (2K/1K→2K/4K), N2 (8K/4K→8K/16K), N3 (32K/16K→32K/64K, block X). Transitions: 1K→4K, 4K→16K, 16K→64K. Saturation cells (load 8): 2K/256, 8K/1K, 32K/4K, 128K/16K.

**Trained configurations per replicate.** Block M: F-OQ 8, T-OQ 7, PK-OQ 7, D-OQ 6 (as ADR-0021 §5.3), R2 3 = 31. Block X: F-OQ, T-OQ, PK-OQ, D-OQ at three cells and R2 at one = 13. Block B: 4. Five replicates: 155 + 65 + 20 = 240 cells. No seed block is run: P10-S1's corrected seed block already shows the data draw dominating in 24 of 28 comparisons.

**A confound that grows with the row.** The oracle codes have width 16 at every size. The share of facts with a neighbour above cosine 0.8 was 0.10, 0.38 and 0.85 at 2,048, 8,192 and 32,768 facts (ADR-0021 §8.10). It has not been computed at 131,072; the rehearsal computes it (no training is needed) and it is printed beside every block X figure. The width is not changed (open choice 3).

## 6. Data, seeds, replicates

- Generator, task, panels A and B, held-out panels H1 and H2, unseen-fact control: as ADR-0021 §4 and §6.2. Each draw has a fact table of 131,072 facts if block X is funded (32,768 otherwise), whose first 32,768, 8,192 and 2,048 are the smaller sets.
- **Five replicates, never reduced.** Replicate r is data draw r with initialisation seed 2400 + r. Pairing as ADR-0021 §6.2.
- **Seed namespace 240001–249999** (new; no overlap with any earlier study). Registered draws `p10is1-draw-1…5`, bases 240001, 240101, 240201, 240301, 240401; calibration draws 249001, 249101 (initialisation seeds 2491, 2493); rehearsal draw 249201 (2492); Lane R index seeds 248001–248999; unit tests 924001–924999. Initialisation seeds 2401–2405.
- **Gate G9** asserts disjointness, including derived seeds, from every range ADR-0021 §6.3 lists, from P10-S1's own (210001–219999, 2101–2193, 921001–921999), and from the namespaces of ADR-0023 and ADR-0025 to ADR-0028, which this drafter could not all read (ADR-0027 and ADR-0028 propose 27xxxx and 28xxxx).
- Lane R reads P10-S1's own draws and checkpoints by design (§11); its only new randomness is the index seeds above.

## 7. Fairness of learning rates (task item 8)

**Rule: every trained arm gets the same search.** Grid {0.001, 0.003, 0.01, 0.03, 0.1}, both calibration draws, the selection rule of ADR-0021 §10.1 item 3 and §22 M7 (highest minimum Panel A a_use over the two draws at the readout; ties within 0.02 by the walk down the doubling grid; then the smaller rate), applied identically to F-OQ, T-OQ, PK-OQ, D-OQ and R2.

| Unit | Selection cell | Readout at |
|---|---|---|
| 1,024 / 4,096 / 16,384 / 65,536 slots, not loaded | 2K/1K / 8K/4K / 32K/16K / 128K/64K | the row's U_P |
| Loaded cells and 2K/256 | each loaded cell itself | 65,536 updates |

- **Edge rule (design ceiling, extended by rule).** If the best rate of a unit is at an end of the grid by more than 0.02, the grid is extended one step in that direction (0.3; 0.0003), at most twice per unit. A diverged rate is recorded and left out. If the best is still at the edge after two extensions, the unit prints RATE AT EDGE and the work returns to the human lead before the freeze.
- **Reason.** `docs/EXPERIMENT_PROTOCOL.md` §3 requires a comparable tuning budget across alternatives. In P10-S1 one side was tuned and the other was not, so DENSE AHEAD and DENSE FASTER could reflect the rate. A tuned store may still be behind; then the label means more.
- **Bridge (block B).** A tuned rate and new seeds change two things against P10-S1. Block B keeps P10-S1's rate on the new seeds at two cells, so that the effect of the rate is read apart from the effect of the draw. Descriptive; it enters no rule of Lane C.
- **Limit.** At a loaded cell the rate is chosen at 65,536 updates although the cell runs far longer. This is stated in §22.

## 8. Run lengths

- **U_P per row, by rule** (ADR-0021 §10.1 item 1, at the calibrated rates): the smallest value on the doubling ladder from 8,192 at which, on both calibration draws and both panels, F-OQ reaches a_use ≥ 0.90 at the row's larger step cell and R2 reaches a_use ≥ 0.95. The ladder has no fixed top; it extends by doubling within the calibration budget (§16).
- **Cells that are not loaded** run 6 · U_P of their row; R2 runs U_P. Snapshots as ADR-0021 §5.4.
- **Loaded cells: run until full, within a budget (task item 6).** The fixed ceiling of ADR-0021 §10.1 item 0b is replaced.
  1. *Ladder.* 65,536 × {1, 1.5, 2, 3, 4, 6, 8, …} (alternating ×1.5 and ×4/3), with a snapshot at every ladder point.
  2. *Full at U* (a cell, on its own snapshots): on both panels, i\*(U) − i\*(U/2) ≤ 0.10 bits and i\*(U/2) ≥ 0.473 bits (ADR-0021 §8.2, unchanged), at two consecutive ladder points, of which U is the second.
  3. *Calibration* runs F-OQ and T-OQ at each loaded cell on both calibration draws up the ladder until full at U on all four views; that U is the arm's starting length U₀. Every other arm starts at the larger of the two.
  4. *Registered run.* Each registered cell (arm, replicate) trains to U₀, and then continues ladder point by ladder point until it is full or reaches **4 · U₀**. The frozen code applies the rule to the cell's own plateau statistic and to nothing else; no comparison between arms, sizes or replicates enters it. Continuation uses checkpoint restoration (gate G4: train-restore-continue equals the straight run).
  5. A cell not full at 4 · U₀ is **NOT FULL WITHIN BUDGET**: a registered value, not a negative. The figure 4 is two further doublings, the horizon ADR-0021 §8.2 row 4 already uses for "the gap survives".
  6. **Loaded** (for the capacity line): full, and i\* ≤ 4.0 bits (ADR-0021 §8.2, unchanged).
- This is the same rule for 2K/256 (which P10-S1 could not fill under a fixed ceiling) and for 128K/16K (which P10-S1 did not fund).

## 9. Measurements and validity checks

Primary measure, a_use, i, i\*, I_use, the address-swap derangement, the ablations, and gates G1–G9 are those of ADR-0021 §7.1–§7.4 and §8.1, with the changes below.

### 9.1 The dependence test (task item 1)

P10-S1's third condition compared useful answers with all correct answers. Near the floor, the backbone alone answers about 1 in 32 of the facts the store has not retained, so the ratio falls below 0.95 even when every other correct answer depends on the read. The condition is replaced by a test against that null.

For a memory cell, snapshot and panel, with n facts, c correct answers, u usefully retained facts, m = n − u, and b the no-memory baseline's correct count on the same panel and fact set of the same draw:

| Condition | Rule |
|---|---|
| DEP-a | Memory disabled gives chance (the G2 interval). Unchanged |
| DEP-b | Value shuffle gives chance. Unchanged |
| DEP-c (new) | Fails only if **both**: (i) c − u exceeds the upper 1 − 10⁻⁴ quantile of Binomial(m, p⁺), where p⁺ is the upper end of the G2 chance interval for n divided by n; and (ii) (c − u − m · b/n) / n > 0.01 |
| LEAKAGE | Unseen facts above chance. Unchanged |

- **Reasons for the figures.** 10⁻⁴: P10-S1 made 2,289 dependence evaluations on memory cells (audit §2); at that level fewer than one false failure is expected in a study of that size. 0.01: an unexplained share of one fact in a hundred moves i by at most about 0.09 bits, below the smallest threshold any rule uses (0.10). Neither figure is taken from P10-S1's values; the drafter has **not** recomputed P10-S1's evaluations under this rule, beyond the one case in §2 item 2.
- **Where DEP is read.** At every snapshot it is computed and printed. It enters a verdict only at the snapshots whose values that verdict reads; each rule of §10 lists them. A failure elsewhere is printed DEP-EARLY and changes no class. Reason: a verdict is invalidated by evidence about the numbers it uses.
- **Reference qualification (binding).** In the rehearsal, R2 is run through DEP-a, b and c at every snapshot fraction of U_P, at each of its cells, on the rehearsal and both calibration draws. A condition that R2 fails at a fraction on any view is **not used at that fraction for any arm of that row**, and the report prints DEP-c NOT QUALIFIED AT that fraction. Beyond U_P, R2 is at its ceiling and a condition qualified at U_P stays qualified. In the registered run, R2 is read again at the same snapshots; if it fails a qualified condition in a replicate, that condition is not applied at that snapshot in that replicate and REFERENCE FAILED DEP is printed. This rule is fixed before any registered seed is observed and applies to every arm alike.

### 9.2 Cost readings

Two readings, never merged:

- **MC-A, analytic.** Multiply-adds of one whole training update, by the formula of ADR-0021 §22 M6 and §22.1, checked against a FLOP count at small size. Deterministic and independent of machine load. It is a matching rule and a counted quantity. **It is never reported as measured efficiency.**
- **MC-T, measured.** Single-thread process CPU-seconds per update from the isolated timing stage (§17). If the machine is not quiet by the rule, MC-T is NOT MEASURED; no wall-time or CPU-time comparison is then made.

For each reading, the matched snapshot of the cheaper cell is the smallest of {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} · U_P whose cumulative cost is at least the costlier cell's at U_P; beyond the run length the pair is MC-SHORT in that reading. The "larger of the two multipliers" rule and the comparator rule for MC-AMBIGUOUS of ADR-0021 §5.4 are not used: disagreement is now reported, not resolved.

## 10. Rules of Lane C

Panels are read separately. "Favouring" conditions need both panels in a replicate; "blocking" conditions need either (ADR-0021 §22 (h)). The denominator is always 5.

### 10.1 Capacity step, one replicate (ADR-0021 §8.2, restated; first match wins)

Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC), in reading MC-A. Δ_SAT = i(4N; U_P) − i\*(N; U_run). Δ_FULL = i\*(4N; U_run) − i\*(N; U_run). Snapshots read by DEP: U_P and U_MC of both cells, and the last two ladder points (or U_run/2 and U_run) of both.

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row (R2 a_use < 0.95 at U_P on a panel), or LEAKAGE |
| 2 | DEPENDENCE_FAILED | either cell fails a qualified DEP condition at a snapshot listed above |
| 3 | CEILING | i(N; U_P) ≥ 4.5 |
| 4 | CAPACITY | Δ_MU ≥ 0.5; Δ_MC ≥ 0.5; Δ_SAT ≥ 0.5; the smaller cell is loaded; Δ_SAT − 2 · [i\*(N; U_run) − i\*(N; U_run/2)] ≥ 0.5; a_use(4N; U_P) ≥ 0.5 |
| 5 | GAIN WITHIN BUDGET ONLY | Δ_MU ≥ 0.5, not row 4 |
| 6 | REVERSED | Δ_MU ≤ −0.5 and Δ_FULL ≤ −0.5 |
| 7 | BEHIND WITHIN BUDGET | Δ_MU ≤ −0.5, not row 6 |
| 8 | NULL | \|Δ_MU\| < 0.25 and \|Δ_FULL\| < 0.25; both cells full; the smaller cell loaded |
| 9 | FLAT, NOT LOADED | as row 8, the smaller cell not loaded |
| 10 | UNRESOLVED | otherwise |

Different verdicts on the two panels give PANEL-DISAGREE. Where MC-T is measured, Δ_MC is also computed in it and printed; a CAPACITY verdict whose MC-T value is below 0.5 carries NOT CONFIRMED AT MEASURED CPU COST. Every threshold is ADR-0021's, fixed there before any S1 record.

**Step class** (first match): NOT_EVALUATED (≥ 2 replicates); DEPENDENCE_FAILED (≥ 2); NOT REPLICATED (≥ 2 PANEL-DISAGREE); CAPACITY STEP (CAPACITY in all 5); GAIN WITHIN BUDGET (rows 4–5 in all 5); NOT LOADED (CEILING or FLAT, NOT LOADED in ≥ 4); REVERSED (≥ 4); NO GAIN (NULL or REVERSED in ≥ 4); NOT FULL WITHIN BUDGET (the smaller cell not full in ≥ 2); MIXED.

**Arm class** (F-OQ, F-OQ-IVF, T-OQ; first match), over the transitions that are funded: NOT_EVALUATED (every step of a transition); DEPENDENCE_FAILED (any step); CAPACITY_SUPPORTED (a CAPACITY STEP in every funded transition, no step REVERSED, a_use ≥ 0.80 at the largest funded loaded step's larger cell at U_P in all 5); CAPACITY_SOME_TRANSITIONS (at least one CAPACITY STEP); NOT_TESTED_BY_LOAD (in some transition every step is NOT LOADED or NOT FULL WITHIN BUDGET); CAPACITY_NOT_SUPPORTED (a NO GAIN or REVERSED step in every transition and no CAPACITY STEP); INTERMEDIATE. The label names the transitions read.

### 10.2 Dense comparison: which reading is primary (task item 3)

**Decision, before observation: matched compute is the primary reading of the dense comparison within a budget. Matched updates (MU) and D-OQ's best snapshot (D-BEST) are printed and decide nothing.**

- *Reason.* An update is not a resource. D-OQ costs more per update than the store (0.0216 against 0.0124 seconds per update at 32K/16K in P10-S1's six-worker training, `manifests/train.manifest.json`; up to 2.5 times in multiply-adds, ADR-0021 §8.5). At equal updates the dense map has had more compute. D-BEST gives it up to six times the updates. `EXPERIMENT_PROTOCOL.md` §3 asks for fair training budgets.
- *Disclosure.* This choice is made after seeing that matched compute favoured F-OQ at 32K/16K in 5 of 5 replicates of P10-S1 (+0.24 to +0.33 bits), while matched updates favoured D-OQ in 4 of 5. That observation is a hypothesis for fresh seeds, not a result. P10-S1's DENSE AHEAD stands as registered.
- *Guards.* A label that favours the store needs **both** cost readings, measured; the saturation reading, which no budget choice affects, blocks independently; and on what P10-S1 saw at saturation (D-OQ ahead by 1.76–1.87 bits, 5 of 5) this change alone cannot produce a positive.

Per arm, per larger cell of each CAPACITY STEP, per reading (MC-A, MC-T), d = i(arm) − i(D-OQ), the cheaper of the two at its matched snapshot:

| Cell label | Rule |
|---|---|
| DENSE AHEAD (cell) | d ≤ −0.25 in ≥ 4 replicates in MC-A, and in MC-T where measured |
| STORE NOT BEHIND (cell) | d > −0.25 on both panels in all 5 replicates in MC-A **and** MC-T; MC-T must be measured and neither MC-SHORT |
| DENSE COMPARISON SPLIT (cell) | otherwise; the readings and replicate counts are printed |

Dense at saturation, per loaded cell, both arms full, each at its own full length: DENSE HOLDS MORE (d_sat ≤ −0.25 in ≥ 4); STORE HOLDS MORE (I_use ratio ≥ 1.10 on both panels in all 5, D-OQ full); SAME AT SATURATION otherwise, with DENSE STILL RISING if D-OQ is not full. Every dense label is printed for every cell with MU, D-BEST and D-OQ's a_use beside it (the omission of audit D3 is closed by a test, §20).

**Arm-level combination across cells, explicit:** DENSE AHEAD (arm) if DENSE AHEAD at every such cell, or DENSE HOLDS MORE at every loaded cell read. NOT BEHIND DENSE (arm) if STORE NOT BEHIND at every such cell and DENSE HOLDS MORE at no loaded cell. DENSE SPLIT (arm) otherwise.

### 10.3 C-CAPACITY outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING-FAILURE | an engineering gate fails, or frozen and running identities differ and cannot be restored (§20) |
| 2 | PAUSED / INCOMPLETE (status) | a registered cell has no record. PAUSED if the cause is a resource cap or a restorable identity stop; no outcome is printed and the run is resumable |
| 3 | CAPACITY-POSITIVE | F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and NOT BEHIND DENSE |
| 4 | CAPACITY-NEGATIVE | (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least one of the three is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD |
| 5 | CAPACITY NOT TESTED | for F-OQ and T-OQ, every step is NOT LOADED or NOT FULL WITHIN BUDGET |
| 6 | CAPACITY-INCONCLUSIVE | otherwise, with the reason (DEPENDENCE_FAILED, DENSE SPLIT with the cells, SOME TRANSITIONS, INTERMEDIATE, …) |

Printed with the transitions read, each cell's dense labels in each reading, the saturation outcome, the sparse-arm label (§10.6) and the tags of §1. **The lead's expectation, written before any observation under this ADR:** F-OQ shows capacity steps; DENSE HOLDS MORE at saturation is likely again; CAPACITY-NEGATIVE by clause (b) is the single most likely outcome unless the rate search changes the picture.

### 10.4 C-SATURATION

S(N) = F · i\*(cell at its full length), ρ = S(4N)/S(N), b(N) = S(N)/N. Pair verdict, class, arm class and outcome are ADR-0021 §8.10's with the threshold 3.0 unchanged and three changes: NOT FULL means NOT FULL WITHIN BUDGET under §8; the registered pairs are 256→1,024 (F-OQ), 1,024→4,096 and, if block X is funded, 4,096→16,384 (F-OQ, F-OQ-IVF, T-OQ; PK-OQ printed); and every replicate is printed on both panels with ρ, the last ladder gain and its full status, including replicates that are not full (audit D2, D9). Outcomes: SATURATION-PROPORTIONAL, -SUBPROPORTIONAL, NOT MEASURED, -INCONCLUSIVE. The separability figures are printed beside every ρ; a SUBPROPORTIONAL verdict is never read as a property of the store alone (§5).

### 10.5 C-EFFICIENCY and the dense-speed rule (task item 2)

The line reads the control steps N1, N2 (and N3). Level i_T = 3.0 bits; u_T, censoring, c_T and the step verdicts FASTER, FASTER IN UPDATES ONLY, REACHED ONLY BY THE LARGER, SLOWER, SAME, NOT_ASSESSED are ADR-0021 §8.8's, with one change: **every verdict that uses cost is computed once per cost reading**, giving an efficiency reading E-A and an efficiency reading E-T, each with its own step classes and arm classes. A snapshot qualifies only if DEP passes there (the DEP snapshots of this line are the qualifying snapshot and the one before it).

**Dense speed, per FASTER-STEP larger cell, per reading:** DENSE FASTER (cell, reading) if D-OQ's c_T is at most 0.8 of the arm's in ≥ 4 replicates; DENSE NOT FASTER if it is above 0.8 in all 5; DENSE SPEED UNDECIDED otherwise. **Every cell and reading is printed.** No any-cell and no every-cell rule is applied silently:

| Order | Outcome | Rule |
|---|---|---|
| 3 | EFFICIENCY-POSITIVE | F-OQ or T-OQ is EFFICIENCY_SUPPORTED in **both** E-A and E-T, and is DENSE NOT FASTER at **every** FASTER-STEP cell in **both** readings. E-T must be measured |
| 4 | EFFICIENCY-NEGATIVE | F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED in both readings; or at least one is EFFICIENCY_SUPPORTED in both and every such arm is DENSE FASTER at **every** FASTER-STEP cell in **both** readings |
| 5 | EFFICIENCY-INCONCLUSIVE | otherwise, with the reason: DENSE SPEED SPLIT (cells and readings named), READINGS DISAGREE, MEASURED COST NOT AVAILABLE, … |

A positive needs every cell and both readings; so does a negative; anything between is inconclusive. This is the symmetric rule the acceptance asked for: a label is never evidence about a cell or a reading it did not hold in. Applied to nothing in P10-S1.

### 10.6 Descriptive labels (enter no outcome)

- **Sparse arms.** T-OQ against F-OQ-IVF at equal candidate count, and PK-OQ against both, on I_use at 8K/4K and 32K/16K (and 128K/64K): ratio ≥ 1.03 AHEAD, ≥ 0.97 COMPETITIVE, otherwise BEHIND, in ≥ 4 replicates at every cell read. **Read at U_P and at the run length; both labels are printed and neither is called "the" label.**
- Counted work per query (SUBLINEAR or LINEAR KEY SCORING), as ADR-0021 §7.4. Logical counts; not measured efficiency.
- Read-path throughput (RAM, one process, quiet machine), as ADR-0021 §7.5; THROUGHPUT NOT MEASURED otherwise. Not storage I/O, not a system's latency.
- Bridge (block B): i at 0.003 against i at the calibrated rate, same cell and replicate.

---

# PART R — Routing diagnosis, Stage A (no training)

## 11. Checkpoints, and what has already been seen

**Inputs.** P10-S1 attempt 2, `experiments/P10S1-registered-attempt2-20261117/cells/<label>/snapshots/u<update>/model.pt`, for F-OQ and T-OQ at the seven grid cells, five replicates (70 cells). The directory is local and git-ignored. Each checkpoint's `model_sha256` in its `snapshot.json` is checked against the cell's `train.json`, whose digest is in the committed `results/p10s1-run-2026-11-17/manifests/train.manifest.json`. The data draws are regenerated by P10-S1's fixed generation script and checked against the freeze hashes. Nothing in the run directory is written.

**Checkpoints read.**

| Cells | U_P | Run length | Also read (descriptive) |
|---|---|---|---|
| 2K/1K, 2K/4K, 8K/4K, 8K/16K | 8,192 | 49,152 | 16,384, 32,768 |
| 32K/16K | 16,384 | 98,304 | 32,768, 65,536 |
| 8K/1K (loaded) | 8,192 | 393,216 | 49,152, 196,608 |
| 32K/4K (loaded) | 16,384 | 786,432 | 98,304, 393,216 |

**This lane is a re-analysis of observed cells.** Exactly:

| Already seen (by the lead, the auditor and the human lead) | Not seen by anyone in this workflow |
|---|---|
| a_use, i and raw accuracy of the registered reads (F-OQ exhaustive, F-OQ-IVF at 512 candidates, T-OQ as trained) at every snapshot, every replicate and panel; the hierarchy ratios; the saturation figures (`audit/AUDIT.md` §4–§6) | Any read of the tree with priors removed, with all branches visited, or with a different number of branches |
| That the tree-against-index order reverses between U_P and the run length at 8K/4K and 32K/16K and not at 8K/1K (note §5.1) | Any index read at a candidate count other than 512 or a list size other than 256 |
| | Recovered attention mass, for any read |
| | Candidate recall: P10-S1's evaluation computed the share of the exhaustive top-8 found by the tree and by the index at U_P and stored it in the cell records; it is not printed in `RESULTS.md`, `OUTCOME.md` or `AUDIT.md`, and the drafter has not opened those records |

Consequences: the thresholds of §14 are fixed knowing the left column and not the right; the labels of this lane are printed **REGISTERED RE-ANALYSIS OF OBSERVED CELLS**; and a confirmatory read needs fresh checkpoints (§15).

## 12. Reads

Every read changes one thing against a named reference. Values, output projection and gate are the checkpoint's; nothing is trained or tuned.

**Tree checkpoint — a 2 × 2 of candidates and priors, and a sweep.** The trained read scores a candidate key as cos/0.2 plus the log-softmax, over all branches, of its branch's route score (`studies/p9/model.py`, `_top_tree`); the prior therefore enters both the choice of the top 8 and their weights.

| Read | Candidates | Priors | Against | Isolates |
|---|---|---|---|---|
| **T0** | router's 2 branches (512) | on | — | The registered read; must reproduce P10-S1's counts exactly |
| **T1** | router's 2 branches | off | T0 | The priors, candidates fixed |
| **T3** | all keys | on | T0 | The candidate restriction, priors kept |
| **T2** | all keys | off | T1, T3 | Both removed: the tree's keys and values read as a flat memory ("exact search") |
| **Tv** | router's v best branches, v ∈ {1, 2, 4, 8} (256–2,048 candidates), priors on and off | | T0 | Candidate budget; a budget of 128 is not defined for a tree of 256-slot branches |

**Flat checkpoint.**

| Read | What | Isolates |
|---|---|---|
| **F0** | exhaustive, as registered | Reference; must reproduce P10-S1's counts exactly |
| **I256@512** | the registered index (N/256 lists, ≥ 512 candidates, P10-S1's index seed) | Reproduction of F-OQ-IVF |
| **I64@c** | k-means into N/64 lists (the registered construction otherwise), lists visited until at least c keys are collected, c ∈ {128, 256, 512, 1,024, 2,048} with c < N; three index seeds from 248001– | Post-hoc sparse retrieval at each budget. Lists of 64 make the budget 128 distinct from 256; with lists of 256 they are the same read |

At 1,024 slots the feasible budgets are 128–512 and the tree has four branches; these cells are read and marked SHALLOW.

## 13. Measurements

Per checkpoint and read:

| Measure | Definition |
|---|---|
| End-task | a_use, i, raw accuracy on Panels A and B, with P10-S1's derangement (ADR-0021 §7.1) |
| Candidate recall CR8, CR1 | Over all trained facts of the cell (the query does not depend on the context): mean of \|C ∩ E8\| / 8, and the share of facts with E1 ∈ C. C is the set of keys the read scores; E8 and E1 are the top 8 and top 1 by cosine over all keys of **the same checkpoint**, without priors |
| Selection overlap SR8 | Mean of \|S ∩ E8\| / 8; S is the 8 slots the read selects |
| Recovered attention mass AM_C, AM_S | Σ of w_E(s) over s ∈ C, and over s ∈ S; w_E is the softmax at temperature 0.2 over E8's cosines, the exhaustive read's own weights |
| Prior effect | i(T1) − i(T0) and i(T2) − i(T3); the share of facts whose selected set changes; the mean total-variation distance between the read's weights with and without priors |
| Work | Keys scored per query, counted. Logical; not measured efficiency |

Recall and mass are measured against exact search of the same checkpoint. They say whether the read finds what that memory's own keys rank first. They do not say that those entries hold the fact: for the tree, that is what the end-task figure of T2 tells. Both are always printed together, per the note's §4 item 1.

## 14. Labels of Lane R

**Thresholds, fixed now, with reasons.** For a read X and a reference Y of the same cell, checkpoint, replicate and panel:

- **A gap exists** if i(Y) − i(X) ≥ 0.5 bits. (0.5 is the programme's unit of a material difference, ADR-0021 §8.2.)
- **X is RESTORED to Y** if i(Y) − i(X) ≤ 0.25 bits **and** i(X) ≥ 0.90 · i(Y), with i(Y) ≥ 0.473 bits (a_use ≥ 0.25); otherwise the comparison is NOT EVALUABLE — WEAK REFERENCE.
- **Gap closure** of a read X′ of the tree: g = [i(X′) − i(T0)] / [i(F0) − i(T0)], defined where a gap exists between T0 and F0.

*Why not 95% of accuracy.* The note's 95% is a proposal. At the flat memory's 0.992, 95% is 0.942: a loss of 0.50 bits per fact, the size this programme calls a full capacity step. At a loaded cell (0.654) the same 95% is a loss of 0.19 bits. A ratio of accuracies means different things across the range. The rule above uses the information measure every rule already uses. 0.25 bits is the "not behind" margin ADR-0021 fixed for every comparator label before any S1 record; it binds above about 2.5 bits (at 0.992 it requires a_use ≥ about 0.969, stricter than 95%). 0.90 is the pass ratio against an oracle reference used in P10-S0 and in the U_P rule; it binds below. Because i is zero at or below the chance interval, a ratio of i **is** the retained improvement above the no-memory baseline; the reference floor stops a weak reference from being matched trivially. The raw-accuracy version, [acc(X) − acc₀] / [acc(Y) − acc₀] with acc₀ the no-memory baseline, is printed beside it and decides nothing.

**Replicate rule.** A condition holds in a replicate if it holds on both panels. A label needs at least 4 of 5 replicates. For I64@c a replicate's i is the mean over the three index seeds.

**Tree label, per cell and checkpoint (first match wins).** Reference F0 at the same cell, update count and replicate.

| Order | Label | Rule | Next action it points to (note §5.2) |
|---|---|---|---|
| 1 | NOT EVALUABLE | an integrity gate of §19 fails for the cell; or WEAK REFERENCE in ≥ 2 replicates | none |
| 2 | NO GAP | no gap between T0 and F0 in ≥ 4 replicates | none at this cell |
| 3 | REMOVING PRIORS RESTORES | T1 is RESTORED to F0 | Redesign how routing scores enter the read |
| 4 | EXACT SEARCH RESTORES | T2 or T3 is RESTORED to F0 (which one is printed) | Improve the router and candidate coverage |
| 5 | EXACT SEARCH PARTLY RESTORES | g ≥ 0.5 for T2 or T3, not row 4 | Both coverage and content; neither alone |
| 6 | EXACT SEARCH DOES NOT RESTORE | g < 0.5 for both T2 and T3 | Improve memory training and representation |
| 7 | MIXED | otherwise | none |

Printed with every label: all four reads' i and a_use, the decomposition i(T1) − i(T0), i(T3) − i(T0), i(T2) − i(T0), i(F0) − i(T2), the sweep Tv, and CR8, CR1, SR8, AM_C, AM_S of T0.

**Index label, per cell and checkpoint.** Reference F0. c\* is the smallest budget at which I64@c is RESTORED to F0.

| Label | Rule |
|---|---|
| SPARSE INDEX APPROACHES FLAT (c\*) | c\* exists and c\* ≤ N/8. N/8 is the share of keys the tree scores at 4,096 slots (512), the equal-candidate standard of ADR-0021 §8.5 |
| INDEX APPROACHES FLAT ONLY ABOVE N/8 (c\*) | c\* exists and c\* > N/8 |
| INDEX DOES NOT APPROACH FLAT | no feasible budget is RESTORED |
| NOT EVALUABLE | as row 1 above |

Printed with it: i, a_use, CR8, CR1 and AM_C at every budget, so that "the index missed the entry" and "the entry was found" can be told apart. For the flat memory a query whose E8 is wholly among the candidates is read exactly as F0 reads it; a loss of quality is then a loss of recall by construction, and the curve of quality against AM_C is the finding.

**R-DIAGNOSIS: cells and checkpoints (task flag).**

- **Primary cells: 8K/4K and 32K/16K.** They are the cells ADR-0021 §8.5 registered for the hierarchy label before any S1 record. The loaded cells 8K/1K and 32K/4K are read and labelled as a secondary line; there the flat reference itself holds 0.65 and 0.64, so a "restored" tree is restored to a full store, not to a good one. 2K/1K, 2K/4K and 8K/16K are printed.
- **Two checkpoints, two labels, one primary.** The label is computed at U_P and at the run length separately. **The run length is primary**, for one reason: a diagnosis of what limits a trained memory should be made where missing training is least likely to be the answer (at U_P the tree's a_use at the primary cells was 0.469 and 0.401). The U_P label is registered beside it. P10-S1's registered TREE_BEHIND was read at U_P and is not revised by anything here.
- **Combination, explicit.** At a checkpoint, the lane's tree label is the common label of the two primary cells; if they differ it is CELL-DEPENDENT with both printed. R-DIAGNOSIS is the pair (tree label, index label) at the run length. If either differs at U_P, the outcome carries **CHECKPOINT-DEPENDENT** with the U_P pair, and its recommended next action adds "the answer depends on training duration; coordinate with ADR-0026". The intermediate checkpoints of §11 are printed as a trajectory and enter no label.
- **"None" of the note's table** is: EXACT SEARCH DOES NOT RESTORE together with INDEX DOES NOT APPROACH FLAT at both primary cells → consider a more fundamental change of the memory.

**A limit that must travel with every Lane R label.** These are read-time changes to memories trained under the registered read. The tree's values and output projection were trained with the priors in the weights and with two branches visited. If removing the priors at read time does not help, that does not show that training without them would not; if it harms, that does not show the priors are useful. Stage A separates read-time causes. Causes that act during training need Stage B, which is not in this ADR.

## 15. Confirmatory read on fresh checkpoints

Lane R's label rests on cells whose accuracies were seen before its thresholds were written. It is enough to choose where Stage B would look. It is not a confirmed finding.

If Lane C runs, block B trains F-OQ and T-OQ at the two primary cells on new seeds, at P10-S1's rate. The frozen Lane R code, with no change of read, threshold or rule, is then applied to those 20 cells at U_P and at the run length. The result is printed as **R-CONFIRM: CONFIRMED** (the same pair of labels at the run length), **NOT CONFIRMED** (with both pairs), or **NOT RUN — NO FRESH CHECKPOINTS**. Lane R trains nothing in either case. R-CONFIRM changes neither R-DIAGNOSIS nor any Lane C line. Whether a Stage B study may be proposed on R-DIAGNOSIS alone is open choice 8.

---

# COMMON

## 16. Limits, classified (DIRECTION.md §5)

| Limit | Kind | Rule |
|---|---|---|
| Hour cap of a lane; per-stage caps; 3 GiB per worker, 18 GiB aggregate | Resource cap | Set after the rehearsal as charged + 2 × projected remaining, rounded up to the hour. May be extended by the human lead (or under his standing delegation) on cost projections only, never on outcome values. A stage that reaches its cap is **PAUSED**, keeps its completed cells and resumes; every planned cell still runs |
| Calibration budget for the U_P ladder, the rate search and the load search | Resource cap | As above; a search stopped by it is PAUSED, not "no U_L" |
| Loaded-cell run length (4 · U₀); rate grid (two extensions); U_P ladder | Design ceiling | Extended only by the rules of §7 and §8. Reaching it gives the registered value NOT FULL WITHIN BUDGET or RATE AT EDGE. No ceiling is raised because a partial result looks close |
| Candidate budgets and visit counts of Lane R; three index seeds; ten Lloyd iterations | Design ceiling | Fixed; "where feasible" means c < N, and nothing else |
| Five replicates; block X funded or not | Design ceiling | Never reduced after the freeze; block X is decided once, before the freeze, on the rehearsal's cost projection |
| 0.5, 0.25, 0.10, 0.473, 4.0, 4.5, 3.0, 0.8, 1.10, 0.90, 0.95 (REF), 0.80, 4-of-5 and 5-of-5, the DEP-c figures, N/8, g ≥ 0.5 | Scientific threshold | Never changed after the freeze |

## 17. Stages, decisions and machine load

The machine is the human lead's working computer and idles at a load of about 1.0–1.2. Platform of record: macOS arm64 (the M5 Max of ADR-0021 §10.3), CPU only. Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; a GitHub run is not required.

| Lane | Stage | Quiet machine? | If the condition is not met |
|---|---|---|---|
| C | Timing preview and isolated timing (about 4–7 minutes each; 202–376 s in P10-S1's ledger) | **Yes**: load average ≤ 1.0 at start, three retries two minutes apart | MC-T NOT MEASURED. No measured-cost comparison is made; C-EFFICIENCY cannot be positive; favouring dense labels are unavailable. Lane C stays complete |
| C | Read-path throughput (about 7 minutes) | **Yes**, same rule | THROUGHPUT NOT MEASURED (descriptive only) |
| C | Calibration, rehearsal, generate, gates, train, evaluate, analyze, report | No | No rule uses their wall time. CPU-seconds per snapshot are recorded descriptively |
| R | Gates, reads, analyze, report | No | Lane R makes no time comparison |

Order per lane: independent specification review → the human lead's approval → implementation with tests and an independent implementation audit → (Lane C) calibration → rehearsal **of every registered stage end to end against the frozen plan itself** → freeze → the human lead's Decision 2 → one registered run → independent recomputation from raw records → outcome record → the human lead's acceptance. Lane R needs no calibration and can run first.

## 18. Cost projection (estimates, to be replaced by the rehearsal)

Measured basis: P10-S1 attempt 2 charged 49,251 s for 178 training cells and 1,899 s for evaluation with six workers; all attempts and calibration charged 25.39 h (`results/p10s1-run-2026-11-17/ledger_after_run.json`, `OUTCOME.md` §1). Median training seconds per update in that run, from `manifests/train.manifest.json`: F-OQ 0.0050 / 0.0081–0.0092 / 0.0124–0.0136 at 1,024 / 4,096 / 16,384 slots; T-OQ 0.0116–0.0147; D-OQ 0.0051 / 0.0088–0.0104 / 0.0177–0.0216; peak 0.39 GiB per worker. At 65,536 slots nothing was timed under P10-S1; the only figures are older: 0.035–0.049 s per update (P9-I rehearsal) and 0.071–0.077 for D-OQ (revision 4's calibration), ADR-0021 §1 facts 7 and 17. PK-OQ has never been timed and is taken between H8's and T-OQ's cost.

| Item | Charged hours, six workers (order of magnitude) |
|---|---|
| **Lane R**, all reads (70 cells, about 4 checkpoints, up to about 25 reads; a registered evaluation of one snapshot cost about 10–30 s) | **1–3** |
| Lane C block M: training at P10-S1's lengths (H8 out, PK-OQ in) | 11–14 |
| Block M: calibration (rate search for four arms, load search, U_P) | about 6 |
| Block M: evaluation, 2K/256, bridge block B, rehearsal, gates | about 3 |
| **Lane C, block M** | **about 20–25**, plus up to about 20 more if every loaded cell ran to 4 · U₀ |
| Block X: training. 128K/16K, if it fills near 1.57 million updates (twice 32K/4K's 786,432, as 32K/4K was twice 8K/1K's): about 17–20. 128K/64K and 32K/64K at 6 · U_P: about 8–12 | 25–32 |
| Block X: calibration (load search at 128K/16K on two draws, about 9; rates and U_P at 65,536 slots, about 5) | about 14 |
| Block X: evaluation | 1–4 |
| **Lane C, block X** | **about 40–50** |
| **Lane C, both blocks** | **about 60–75**; the cap by the twofold rule would be of the order of 130–150 hours |

Unknowns the rehearsal measures before any cap is set: seconds per update of every arm at 65,536 slots and of PK-OQ at every size; evaluation seconds per snapshot at 131,072 facts; the contention ratio at six workers (1.946 in P10-S1's rehearsal under unrelated load) and at a higher worker count; peak memory at 65,536 slots; code crowding at 131,072 facts. The U_L of 128K/16K is an extrapolation from two points and may be wrong by a factor of two either way. **Block X costs about twice the whole of P10-S1.** A reduced block X (F-OQ and D-OQ only) would cost roughly half of it and would leave the tree and PK-OQ untested at 65,536 slots.

## 19. Stop rules and NOT EVALUABLE outcomes

- A failed engineering gate stops a lane before its training or reads. Lane R's gates: checkpoint and data identities (§11); T0, F0 and I256@512 reproduce P10-S1's recorded correct and useful counts exactly for every cell and checkpoint read; T3 with every branch visited equals the all-keys read on a synthetic memory; an index is identical on rebuild.
- A Lane R cell that fails reproduction is NOT EVALUABLE and is not repaired; if either primary cell is NOT EVALUABLE in ≥ 2 replicates, R-DIAGNOSIS is NOT EVALUABLE.
- A registered cell that fails for a reason other than a cap or a restorable identity stop is kept and not re-run; the lane is INCOMPLETE and a second attempt is the human lead's decision.
- A stop on a resource cap is PAUSED. Completed cells are not recomputed.
- No registered seed of Lane C is observed before Decision 2, apart from G1. The frozen code's own use of a cell's plateau statistic (§8) is not an observation by the lead.
- REF failure: the replicate is NOT_EVALUATED for the row. LEAKAGE: NOT_EVALUATED for the cells concerned.
- No stage is re-run with changed settings. No threshold, seed, replicate count or rule changes after the freeze.

## 20. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| A status note committed to a frozen ADR stopped 171 cells (ADR-0021 §25.19–25.20) | The frozen-input set of each lane is listed in its freeze record by path and SHA-256: this ADR, `studies/p10is1/**`, the lane's config, launch scripts, `freeze/plan.json`, stage caps, calibration records, data manifests and, for Lane R, the checkpoint digests. **Nothing is written or committed in the frozen worktree between Decision 2 and the end of the report stage.** Approvals, status and run-time notes go to the human lead directly or to files on another branch; after approval this ADR is amended only by separate record files. A task that finds an identity difference stops as PAUSED — IDENTITY; if the frozen file is restored bit for bit the stage resumes, and completed cells are kept |
| The throughput stage's item list did not match the frozen plan; the tests used another plan (§25.21) | Every registered stage of both lanes is rehearsed end to end on the rehearsal draw **against the frozen plan file itself**, and each stage's item list is derived from that file only. A stage whose items are not all in the plan refuses at the freeze, not at the run |
| An unstated combination rule; a check the reference fails; a report section comparing the wrong reads (audit D4, D7, D1) | Every reading and combination rule is in §9–§14. R2 is run through every validity check in the rehearsal and a check it fails is not used (§9.1). **The analysis and the report are tested on a synthetic registry with known answers that covers every verdict, class, label and outcome of both lanes and every descriptive section** (task item 4): each registry key carries the read's name, two reads of one cell can never share a key, and a test plants distinct values in every read and asserts each printed figure. The report prints every replicate, panel, cell and reading a rule names (audit D2, D3, D6, D9, D10, D12) |
| A count gate stopped P10-S2 although its quality criteria were met | Loaded cells run until full within a stated budget (§8); searches extend by rule (§7, §8) |
| P10-S0 tested overload at one load and one length | Not this study's question; loaded cells here run to a convergence rule, and Lane R reads more than one checkpoint |
| A tie test passed on macOS and failed on Linux (§25.23) | The platform of record is named (§17); exact reproduction (Lane R's gates, G4) is asserted on it only |
| GitHub CI is costly | Checks run locally (§17) |

## 21. Independent verification

The auditor receives the frozen specification, the code and the raw records, not the lead's conclusions. It recomputes every label of each lane with its own code. For Lane R it also recomputes CR8 and AM_C for T0 at one primary cell from the checkpoint tensors directly.

## 22. What this study cannot establish

- Anything about an autonomous learned memory, the language model forming queries, natural language, or capability beyond recall of trained random facts. Addressing is supplied by an oracle in both lanes.
- Value beyond a lookup table (§3). Efficiency, latency, energy or I/O of any system: counted work and MC-A are logical; MC-T and throughput are in-RAM CPU figures for a 27,392-parameter backbone on one machine.
- Capacity above the largest funded size, or at 65,536 slots if block X is not funded.
- That a SUBPROPORTIONAL saturation verdict is a property of the store (code crowding, §5). A capacity "per slot" in general.
- That the store or the dense map is better "when tuned": each has one family and one grid, with the rate chosen at 65,536 updates at loaded cells.
- Lane R: a cause that acts during training; that a fix would work; anything about an index or router trained for the purpose; a confirmed finding without R-CONFIRM. Its labels describe P10-S1's memories at P10-S1's rate 0.003, on one task.
- That the tree should be replaced or kept. That longer training closes the gap to the flat memory (ADR-0026's question).
- TRANSFER or SYSTEM outcomes, Astra validation, or any approval not recorded.

## 23. Open choices reserved for the human lead

1. **Task (§3).** Keep the task, with every label capped at "necessary condition" (recommended), or stop Lane C until a task a lookup cannot solve is designed.
2. **Block X (§5, §18).** Fund the transition 16,384 → 65,536 in full, about 40–50 charged hours (recommended only if the rehearsal's projection confirms the order of magnitude); fund the reduced version; or leave it NOT FUNDED again.
3. **Oracle code width at 131,072 facts.** Keep width 16 and print the crowding (recommended), or widen the code for every row, which changes the task against P10-S1.
4. **Primary dense reading (§10.2).** Matched compute, with a favouring label needing both cost readings (recommended), or keep P10-S1's "any one reading blocks".
5. **PK-OQ (§4.1).** In Lane C as a baseline (recommended), or deferred to a Stage B study as the note's §5.2 lists it.
6. **H8.** Dropped (recommended), or kept at about 13% more training.
7. **Symmetric rule for split results (§10.2, §10.5).** Positive and negative each need every cell and both readings (recommended), or a conservative any-cell block.
8. **Lane R and Stage B.** May a Stage B study be proposed on R-DIAGNOSIS alone (recommended: proposed yes, approved only after R-CONFIRM or with the re-analysis status stated in its specification)?
9. **Lane R as its own ADR** (§24). Recommended: yes, or at least a separate approval and freeze.
10. **Order.** Lane R first (recommended; it costs 1–3 hours and informs ADR-0026 and any Stage B).
11. **Worker count.** Six as in P10-S1, or the count the rehearsal finds cheaper in charged hours.

## 24. For the independent reviewer (asked by the human lead)

1. **U_P against the run length.** Lane R registers a label at each and names the run length primary, with CHECKPOINT-DEPENDENT when they differ (§14). Lane C keeps U_P as the matched-budget readout of ADR-0021 and prints the sparse-arm label at both (§10.6). Please check that no rule lets the favourable checkpoint be chosen after the fact, and whether "primary = run length" is itself a choice made knowing which way the reversal goes (it is: the tree looks better at the run length; the drafter's reason is stated and may not be sufficient).
2. **Candidate recall.** Recall and attention mass are defined against exact search of the same checkpoint (§13). For the tree this is recall of what the tree's own keys rank first, not of "the right entry". Please check that the 2 × 2 of §12 separates what the note asks to separate, and that the label using "T2 or T3" (a choice of two reads) is acceptable.
3. **Thresholds seen through observed data.** The RESTORED rule was written knowing the registered accuracies. Please check the reasons given for 0.25, 0.90, 0.5 and N/8, and the DEP-c figures, which were not tested on P10-S1's records.
4. **Can the lines stay independent?** The drafter's honest view: the lanes share no rule, no budget and no frozen input, and they differ in kind — a 60–75-hour training study on fresh seeds, and a 1–3-hour re-analysis of observed cells. Keeping them in one ADR is manageable only because this text keeps them in separate parts; it gains nothing and it ties the cheap lane's approval and freeze to the expensive one's. **Lane R would be cleaner as its own ADR.** The one link, R-CONFIRM reading block B, can be a cross-reference. The direction record (note §5.4) places the lane inside ADR-0024, so it is drafted here and the split is put to the human lead (open choice 9).
5. Whether the symmetric split rule (§10.5) or the demotion of matched updates (§10.2) relaxes anything in effect, given that both were written after P10-S1's values were seen.

## 25. Approval record

None. No review has been performed on this draft. No approval exists. `Astra review: NOT_PERFORMED`.
