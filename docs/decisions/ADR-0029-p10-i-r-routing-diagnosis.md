# ADR-0029 — P10-I-R — frozen-checkpoint routing diagnosis (Stage A)

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). This text is the routing lane of ADR-0024 draft 1, revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, verdict NOT READY) and moved to its own ADR. §17 maps every finding that concerns it. **SPEC: PENDING ASTRA REVIEW.** `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- **Study code** P10IR. **Package** `studies/p10ir/` (new code only; `studies/p9` and `studies/p10s1` are imported unedited). **Config** `configs/p10ir_routing.toml`. **Tests** `tests/test_p10ir_*.py`.
- **Origin.** `docs/reviews/p10-i-direction-2026-11-17/LITERATURE_AND_ROUTING_NOTE.md` sections 4 and 5 (binding direction). The question as the note puts it: can ArborLM keep the flat memory's accuracy while using tree-like sparse retrieval, without losing its ability to keep learning? This study addresses only the first, diagnostic step.
- **Where it lives.** The human lead's direction (note §5.4) placed this lane inside ADR-0024. Giving it its own ADR is the reviewer's and the lead's recommendation, **PENDING HUMAN LEAD RULING**. Reasons: it shares no rule, budget or frozen input with the capacity study; it is a short re-analysis where that is a long training study; and one ADR hashed into two freezes repeats the failure of P10-S1 attempt 1. The content of the lane is unchanged by where it lives; if the human lead rules for one ADR, this text returns to ADR-0024 as a part.
- **Immutability.** P10-S1's code, records, labels and run directory are not edited or revised. Its registered TREE_BEHIND stands. ArborLM is unproven research; nothing below is a success claim.
- **Approval.** The human lead alone approves this specification, its budget and each run. Lead's choices open to his ruling are marked **PENDING HUMAN LEAD RULING** and collected in §16.
- **Scope.** Stage A only. **Stage B (any new router, index training, product-key memory, periodic refresh, or other new architecture) is outside this ADR**; if this study indicates it, it is a separate study with its own specification.

## 0. What kind of study this is

**A registered re-analysis of observed cells, with one confirmatory step on fresh checkpoints.**

| Stage | What | Trains? | What it can support |
|---|---|---|---|
| **A1** | New reads of P10-S1's existing frozen flat and tree checkpoints | No | Where a Stage B study would look. Not a statement about cause |
| **A2** (bridge) | The same frozen reads on 20 fresh checkpoints trained exactly as P10-S1 trained them | Yes: P10-S1's arms, rate and lengths; no new architecture | Whether A1's label holds on cells whose accuracies were not seen when the rules were written. **Any claim about cause needs A2** |

Every label of this study is printed with `REGISTERED RE-ANALYSIS OF OBSERVED CELLS` (A1) or `FRESH CHECKPOINTS` (A2), and with `ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`.

## 1. Question, and what each outcome would mean

On the memories P10-S1 trained: is the tree's lower quality, relative to the flat memory, attributable at read time to the branch priors, to the router's hard restriction of candidates, to both, or to neither; and does an index built after training keep the flat memory's quality at the tree's candidate budget?

- The outcome line **R-DIAGNOSIS** is a diagnosis, not a positive or negative for ArborLM. Its values name what the reads identified (§8) and, where one exists, the next action of the note's §5.2 that it points to.
- **"Identified"** means: a read-time change, with nothing retrained, restored or mostly closed the gap. **"Not identified"** is a registered value. It means the reads cannot tell, and it recommends nothing.
- **NOT EVALUABLE** and **CHECKPOINT-DEPENDENT** are registered values. When the two checkpoints disagree, no single next action is recommended.
- The second line, **R-CONFIRM**, says whether A2 reproduced A1's value. Neither line substitutes for the other.

## 2. Background (quoted from the records)

1. P10-S1 registered TREE_BEHIND: T-OQ against F-OQ-IVF at equal candidate count, read at U_P at 8K/4K and 32K/16K (`results/p10s1-run-2026-11-17/OUTCOME.md` §2; ADR-0021 §8.5).
2. Mean a_use over five replicates and both panels, U_P → run length (`audit/AUDIT.md` §6; note §5.1):

| Cell | F-OQ (exhaustive) | F-OQ-IVF (512 candidates) | T-OQ |
|---|---|---|---|
| 2K/1K | 0.991 → 0.999 | 0.916 → 0.927 | 0.787 → 0.931 |
| 2K/4K | 1.000 → 1.000 | 0.953 → 0.960 | 0.989 → 1.000 |
| 8K/1K (loaded) | 0.390 → 0.654 | 0.306 → 0.497 | 0.176 → 0.416 |
| 8K/4K | 0.948 → 0.996 | 0.631 → 0.706 | 0.469 → 0.769 |
| 8K/16K | 0.999 → 1.000 | 0.911 → 0.919 | 0.920 → 0.996 |
| 32K/4K (loaded) | 0.392 → 0.637 | 0.201 → 0.270 | 0.151 → 0.323 |
| 32K/16K | 0.916 → 0.992 | 0.483 → 0.540 | 0.401 → 0.697 |

3. The tree-against-index order reverses between U_P and the run length at 8K/4K and 32K/16K, and not at 8K/1K. Both stay far below the exhaustive flat read at the loaded and near-full cells.
4. The oracle codes are crowded by construction (nearest-neighbour cosine about 0.83 at 32,768 facts; `RESULTS.md` line 96).
5. The supplementary read-path throughput of the tree stayed flat from 1,024 to 16,384 slots while the flat memory's fell (`supplement/throughput_supplement.json`; descriptive; not part of this study).

## 3. How the trained tree reads (from the code; this fixes what the reads can identify)

`studies/p9/model.py`, `_top_tree`, `select`, `delta`; checked by the review (§B).

- The query is the fact's fixed oracle code. It does not depend on the context, so recall and attention measures are per fact.
- Route scores are cos(q, router row)/0.2 for each of the N/256 branches. The two best branches are visited (ties to the lower id). Each of their 512 keys is scored cos(q, key)/0.2 **plus the log-softmax, over all branches, of its branch's route score** (the branch prior). The top 8 are selected; the read's weights are the softmax of those eight scores.
- **The prior is one constant per branch.** A softmax is unchanged by a common shift, so the prior has exactly two effects: it changes *which* slots are selected at the boundary between branches, and it changes the *relative weight between slots of different branches*. Among slots of one branch it changes nothing. If all eight selected slots lie in one branch, the prior has no effect on the read at all. With one branch visited, priors on and priors off are the same read.
- A slot outside the branches the router visits for a fact never received that fact's gradient. Its key's cosine to the fact's code is whatever it happens to be.

Consequences for the design: "priors distort the weights" can only mean cross-branch reweighting and boundary selection; a read over all keys with the priors kept is a soft branch restriction, not exact search; and exact search over a jointly trained tree can select slots that were never trained for the fact, so it can do harm without the content being poor.

## 4. Inputs, and what has already been seen

**Checkpoints (A1).** P10-S1 attempt 2, `experiments/P10S1-registered-attempt2-20261117/cells/<label>/snapshots/u<update>/model.pt`, F-OQ and T-OQ at the seven grid cells, five replicates: 70 cells. The directory is local and git-ignored. Each `model_sha256` in `snapshot.json` is checked against the cell's `train.json`, whose digest is in the committed `results/p10s1-run-2026-11-17/manifests/train.manifest.json`. P10-S1's draws are regenerated by its fixed generation script and checked against its freeze hashes. Nothing in the run directory is written. The review confirmed every checkpoint named below exists on disk.

| Cells | U_P | Run length | Also read (trajectory, descriptive) |
|---|---|---|---|
| 2K/1K, 2K/4K, 8K/4K, 8K/16K | 8,192 | 49,152 | 16,384, 32,768 |
| 32K/16K | 16,384 | 98,304 | 32,768, 65,536 |
| 8K/1K (loaded) | 8,192 | 393,216 | 49,152, 196,608 |
| 32K/4K (loaded) | 16,384 | 786,432 | 98,304, 393,216 |

**What has and has not been seen.**

| Seen by the lead, the auditor and the human lead | Not printed in any committed record |
|---|---|
| a_use, i and raw accuracy of the registered reads (F-OQ exhaustive, F-OQ-IVF at 512 candidates, T-OQ as trained) at every snapshot, replicate and panel; the hierarchy ratios; the reversal of §2 item 3 | Any read of the tree with priors removed, with all keys scored, or with another number of branches. Any index read at another candidate count or list size. Attention mass for any read |
| | **Two recall quantities that already sit in the cell records** (below) |

**The recorded recall values, described exactly (review F11).** P10-S1's evaluation stored: (a) for T-OQ only, at U_P only, `tree_recall_of_exhaustive_top8`, the share of the exhaustive top 8 that lies in the router's visited branches (`studies/p10s1/evaluate.py`, `tree_recall`); (b) for every F-OQ-IVF read, at every snapshot, `ivf_measured.recall_of_exhaustive_top8` (`studies/p10s1/index.py`, `IVFMemory.measured`). Neither appears in `analysis.json`, `results.json`, `RESULTS.md` or the audit outputs. The reviewer checked key names and presence only. No one in this workflow reports having opened the values; the drafter has not.

**Sealing rule.** No one opens those two keys before this ADR's freeze. The freeze record states, for the lead, the implementer and the auditor, that none has. The implementer's code reads them only inside the gate of §11, which prints equal or not equal and never the values, until the registered stage. If the seal is broken, the freeze record says so and the label of §8 that uses recall (CONTENT) carries RECALL SEEN BEFORE FREEZE.

## 5. Seeds

All of this study's seeds are assigned in `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` (being written); none is fixed here. Roles and counts: index seeds for I64, 3; bridge data draws, 5, each a complete P10-S1-style draw; bridge initialisation seeds, 5; one rehearsal draw and one rehearsal initialisation seed; a unit-test range. Before the freeze, a gate checks every literal and derived seed (initialisation seed + 1000·k; draw base + offsets, as P10-S1's generators derive them) against the registry and every earlier range. **Declared exemption:** stage A1 re-uses P10-S1's five draws and P10-S1's index seed (draw base + 60) on purpose, for the reproduction reads only; the gate lists them as re-used, not as new.

## 6. Reads

Every read changes one stated thing against a named reference. Values, output projection and gate are the checkpoint's. Nothing is trained or tuned in stage A1.

**Tree checkpoint.**

| Read | Keys scored | Prior | Changed against | What the difference can show |
|---|---|---|---|---|
| **T0** | router's 2 branches (512) | in selection and weights | — | The registered read. Must reproduce P10-S1's counts exactly |
| **T1** | router's 2 branches | removed | T0 | The whole read-time effect of the prior, candidates fixed |
| **T1w** | router's 2 branches | kept in the selection of the 8, removed from their weights | T0, T1 | Splits the prior's effect into cross-branch reweighting (T1w − T0) and boundary selection (T1 − T1w) |
| **T3** | all N keys | kept (every key has its branch's prior) | T0 | Removing the **hard** restriction while the **soft** one stays. **This is not exact search** |
| **T2** | all N keys | removed | T1, T3 | **Exact search**: the tree's keys and values read as a flat memory |
| **Tv** | router's v best branches, priors on and off | | T0 | Candidate budget. v ∈ {1, 2, 4, 8} with v ≤ N/256. At 1,024 slots v ∈ {1, 2, 4} and v = 4 is T3 / T2. A budget of 128 does not exist for 256-slot branches |

**Flat checkpoint.**

| Read | What | Purpose |
|---|---|---|
| **F0** | exhaustive, as registered | Reference. Must reproduce P10-S1's counts exactly |
| **I256@512** | the registered index (N/256 lists, at least 512 candidates, P10-S1's index seed) | Reproduction of F-OQ-IVF |
| **I64@c** | k-means into N/64 lists (the registered construction otherwise); lists visited in order of centroid score until **at least** c keys are collected; c ∈ {128, 256, 512, 1,024, 2,048} with c < N; three index seeds | Post-hoc sparse retrieval per budget. Lists of 64 make 128 distinct from 256 |

Feasibility: at 1,024 slots the index budgets are 128, 256, 512; at 4,096 and 16,384 all five. c is a minimum; the measured mean and 99th-percentile candidate counts are printed beside every nominal c. Cells at 1,024 slots are marked SHALLOW (four branches; 512 candidates is half the store).

## 7. Measurements

Per checkpoint and read:

| Measure | Definition |
|---|---|
| End-task | a_use, i, raw accuracy on Panels A and B, with P10-S1's derangement (ADR-0021 §7.1) |
| Candidate recall CR8, CR1 | Over all trained facts of the cell: mean of \|C ∩ E8\| / 8, and the share of facts with E1 ∈ C. C is the set of keys the read scores. E8 and E1 are the top 8 and top 1 by cosine over all keys of **the same checkpoint**, without priors, ties to the lower slot id (`stable_top`) |
| Selection overlap SR8 | Mean of \|S ∩ E8\| / 8; S is the 8 slots the read selects |
| Recovered attention mass AM_C, AM_S | Σ of w_E(s) over s ∈ C, and over s ∈ S; w_E is the softmax at temperature 0.2 over E8's cosines |
| Prior effect | i(T1) − i(T0), i(T1w) − i(T0), i(T2) − i(T3); the share of facts whose selected set changes; the share of facts whose eight selected slots span both branches; the mean total-variation distance between the two reads' weights, taken over the union of the two selected sets with weight zero outside each |
| Work | Keys scored per query, counted. Logical; not measured efficiency |

- For an index read of the flat memory there is no prior, so SR8 = CR8 and AM_S = AM_C, and a fact whose E8 is wholly among the candidates is read exactly as F0 reads it. A loss of quality there is a loss of recall by construction; the curve of quality against AM_C per budget is the finding.
- For the tree, recall is recall of what the tree's own keys rank first. It does not say those slots hold the fact. **This is why recall enters only one rule (§8, CONTENT), as a necessary condition, and is otherwise descriptive.**

## 8. Labels

### 8.1 The retention rule

For a read X and a reference Y of the same cell, checkpoint, replicate and panel:

- **A gap exists** if i(Y) − i(X) ≥ 0.5 bits (the programme's unit of a material difference, ADR-0021 §8.2).
- **X is RESTORED to Y** if i(Y) − i(X) ≤ 0.25 bits **and** i(X) ≥ 0.90 · i(Y), with i(Y) ≥ 0.473 bits (a_use ≥ 0.25); below that floor the comparison is NOT EVALUABLE — WEAK REFERENCE.
- **Gap closure** of a tree read X′: g(X′) = [i(X′) − i(T0)] / [i(F0) − i(T0)], defined where a gap exists between T0 and F0. Write g_P = g(T1), g_C = g(T3), g_PC = g(T2).

*Why not 95% of accuracy (the note's proposal).* At the flat memory's 0.992, 95% is 0.942: a loss of 0.50 bits per fact, the size this programme calls a full capacity step. At a loaded cell (0.654) it is a loss of 0.19 bits. A ratio of accuracies means different things across the range. The rule uses the information measure every rule already uses. 0.25 bits is the "not behind" margin ADR-0021 fixed for every comparator label before any S1 record; it binds above about 2.5 bits. 0.90 is the pass ratio against an oracle reference used in P10-S0 and in the U_P rule; it binds below. In bits, i is zero at or below the chance interval and counts only answers that depend on the read, so the ratio of i is the retained improvement above the no-memory baseline in bits; the floor stops a weak reference from being matched trivially. The accuracy version, [acc(X) − acc₀] / [acc(Y) − acc₀], is printed beside it and decides nothing.

*What the rule requires in accuracy* (the review's computation from the mean a_use of F0; the rule itself is applied per replicate and panel):

| Cell, checkpoint | F0 a_use | a_use a read needs to be RESTORED | Share of the improvement above chance retained |
|---|---|---|---|
| 8K/4K, U_P | 0.948 | 0.920 | 0.969 |
| 8K/4K, run length | 0.996 | 0.974 | 0.977 |
| 32K/16K, U_P | 0.916 | 0.885 | 0.965 |
| 32K/16K, run length | 0.992 | 0.969 | 0.976 |
| 8K/1K (loaded), U_P / run length | 0.390 / 0.654 | 0.366 / 0.613 | 0.933 |
| 32K/4K (loaded), U_P / run length | 0.392 / 0.637 | 0.368 / 0.597 | 0.933 |

At every primary cell it is stricter than 95% of accuracy; at the loaded cells it is slightly looser (0.613 against 0.621 at 8K/1K).

**Disclosure, placed with the rule.** These thresholds, the choice of cells and the reading of the two checkpoints were fixed knowing P10-S1's registered accuracies of T0, F0 and the index for the same five draws. At the run length the tree's gap to F0 is 1.87 and 2.28 bits at the primary cells (3.08 and 3.11 at U_P), and the index's is 2.27 and 3.17 (2.23 and 2.73 at U_P) (review §A). So a tree read is closer to RESTORED at the run length and an index read is further from it. That is why neither checkpoint is primary (§9) and why a claim about cause needs A2 (§10).

### 8.2 Replicate accounting

A condition holds in a replicate only if it holds on both panels. The denominator is always 5. A replicate that is NOT EVALUABLE, or whose g is undefined, does not satisfy any condition. For I64@c, a replicate's i on a panel is the mean over the three index seeds, taken before the panel test. A cell's label is the label held by at least 4 of 5 replicates; otherwise MIXED.

### 8.3 Tree label, per cell and checkpoint

Reference F0 at the same cell, update count and replicate. Define, per replicate: **P** = T1 is RESTORED to F0, or g_P ≥ 0.5. **C** = T3 is RESTORED, or g_C ≥ 0.5. **J** = T2 is RESTORED, or g_PC ≥ 0.5. **H** = i(T2) ≤ i(T0) − 0.25 on both panels. **R** = CR8(T0) ≥ 0.90. First match wins.

| Order | Replicate label | Rule | What it claims, and no more | Next action (note §5.2) |
|---|---|---|---|---|
| 1 | NOT EVALUABLE | a gate of §11 fails for the cell or its F0; or WEAK REFERENCE | — | none |
| 2 | NO GAP | no gap between T0 and F0 | Nothing to explain at this cell | none |
| 3 | PRIORS AND CANDIDATES, SEPARATELY | P and C | Either change alone closes most of the gap at read time | Either; both are candidates for redesign |
| 4 | PRIORS | P, not C | Removing the prior, candidates unchanged, closes most of the gap | Redesign how routing scores enter the read |
| 5 | CANDIDATES | C, not P | Removing the hard restriction, prior kept, closes most of the gap | Improve the router and candidate coverage |
| 6 | JOINT | J, not P, not C | Only removing both closes most of the gap; neither alone does | Both must change together; no single fix is indicated |
| 7 | EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME | H, not P, not C | Exact search selects slots that serve the fact worse than the trained read. The content may be sound for the read it was trained under | none |
| 8 | CONTENT | not P, not C, not J, not H, and R | The router already finds at least 0.90 of what the keys rank first, the prior is not the cause, and quality is still below the flat memory | Improve memory training and representation |
| 9 | NOT IDENTIFIED | not P, not C, not J, not H, not R | The router misses what the keys rank first, yet scoring all keys does not help. The reads cannot say why | none |

Each of rows 3–6 is suffixed FULLY (the named read is RESTORED) or PARTLY (closure ≥ 0.5 only). Every row is reachable: rows 3–6 cover the seven combinations of P, C, J with at least one true; rows 7–9 split the remaining case by H and R.

- **The figure 0.5 for closure** means "most of the gap". **The figure 0.90 for R** is the same oracle-reference ratio as above: if nine tenths of what exact search would select is already scored, exact search can change at most one slot in ten, so the candidate restriction cannot be the main cause. Both are the lead's choices, **PENDING HUMAN LEAD RULING**; R is fixed without the recall values having been opened (§4).
- **Printed with every label:** i and a_use of T0, T1, T1w, T2, T3 and F0; g_P, g_C, g_PC; i(F0) − i(T2); the sweep Tv; CR8, CR1, SR8, AM_C, AM_S of T0; the prior-effect measures.

### 8.4 Index label, per cell and checkpoint

Reference F0. A budget c is **sufficient** if I64@c is RESTORED to F0 at c and at every larger feasible budget. c\* is the smallest sufficient budget.

| Label | Rule |
|---|---|
| SPARSE INDEX APPROACHES FLAT (c\*) | c\* exists and c\* ≤ 512. **512 is the tree's candidate count**, the equal-candidate standard of ADR-0021 §8.5 |
| INDEX APPROACHES FLAT ONLY ABOVE 512 (c\*) | c\* exists and c\* > 512 (reachable at 4,096 and 16,384 slots; at 1,024 slots no budget above 512 is read) |
| INDEX DOES NOT APPROACH FLAT | no sufficient budget |
| NOT EVALUABLE | as row 1 of §8.3 |

Printed with it: i, a_use, CR8, CR1, AM_C and the measured mean and 99th-percentile candidate counts at every budget; c\* as a share of N; and N/8 for comparison. The next action of the note for SPARSE INDEX APPROACHES FLAT is "investigate a separately trained sparse index".

## 9. R-DIAGNOSIS: cells, checkpoints and combination

- **Primary cells: 8K/4K and 32K/16K.** They are the cells ADR-0021 §8.5 registered for the hierarchy label before any S1 record. The loaded cells 8K/1K and 32K/4K are labelled as a secondary line (there the flat reference itself holds 0.65 and 0.64: "restored" means restored to a full store). 2K/1K, 2K/4K and 8K/16K are printed.
- **U_P and the run length are co-primary.** Neither is "the" checkpoint. Draft 1 named the run length primary; the review showed that the choice was made knowing which way it leans (§8.1 disclosure) and that it would decide what Stage B is pointed at. It is withdrawn.
- **Plateau check at the run length (existing snapshots; nothing new is trained).** For T-OQ and for F-OQ at each primary cell and replicate, on both panels: i\*(run) − i\*(run/2) ≤ 0.10 bits (the plateau limit of ADR-0021 §8.2). If it fails in at least 2 of 5 replicates, the cell's labels at the run length carry **TREE STILL LEARNING** or **FLAT STILL LEARNING**. These i values are in P10-S1's records; the drafter has not computed the check.
- **Combination, explicit.**
  1. At a checkpoint, the tree label is the common label of the two primary cells; if they differ it is CELL-DEPENDENT, both printed. The same for the index label.
  2. If the pair (tree label, index label) is the same at U_P and at the run length, **R-DIAGNOSIS is that pair**.
  3. Otherwise **R-DIAGNOSIS is CHECKPOINT-DEPENDENT**, printed with both pairs, **and no single next action is recommended**. The record says that the answer depends on training duration and refers to ADR-0026.
  4. If either primary cell is NOT EVALUABLE at either checkpoint, R-DIAGNOSIS is NOT EVALUABLE.
- **The note's "none"** is: CONTENT or NOT IDENTIFIED for the tree together with INDEX DOES NOT APPROACH FLAT, at both checkpoints → consider a more fundamental change of the memory.
- The trajectory checkpoints of §4 are printed and enter no label.

**A limit printed with every label.** These are read-time changes to memories trained under the registered read. The tree's values and output projection were trained with the prior in the weights and two branches visited. A read-time change that does not help does not show that training without it would not; one that helps shows only that the trained content tolerates it. Causes that act during training need Stage B.

## 10. Stage A2 — the confirmatory read (bridge block)

- **Cells.** F-OQ and T-OQ at 8K/4K and 32K/16K, five fresh draws, one initialisation seed each: **20 cells.**
- **Pinned to P10-S1.** Learning rate 0.003; U_P 8,192 and run length 49,152 at 8K/4K; U_P 16,384 and run length 98,304 at 32K/16K; P10-S1's snapshot schedule, loss, optimizer, batch and code path (`studies/p10s1` trainer, called unedited). The only differences from P10-S1's cells are the data draws and initialisation seeds. Nothing is taken from ADR-0024; this stage does not depend on it.
- **Read.** The frozen A1 code, with no change of read, threshold or rule, at U_P and at the run length. Fresh checkpoints have no recorded recall; the recall gates of §11 do not apply, and the reproduction gate is replaced by "T0 and F0 through the new code equal the same checkpoints through `studies/p10s1`'s evaluation".
- **R-CONFIRM.** **CONFIRMED** if A2's R-DIAGNOSIS equals A1's: the same pair at both checkpoints, or CHECKPOINT-DEPENDENT with the same two pairs. **NOT CONFIRMED** otherwise, with both printed. **NOT RUN** if the stage is not funded or not complete. R-CONFIRM does not change R-DIAGNOSIS.
- **What may be said.** After A1 alone: "the re-analysis points to …". A statement that the tree's gap *is caused by* a named factor at read time requires CONFIRMED. Neither supports a statement about training-time causes.
- **Cost.** At P10-S1's measured seconds per update (0.0091 and 0.0129 at 8K/4K; 0.0124 and 0.0147 at 32K/16K), 20 cells are about 18,700 worker-seconds: about 5.2 worker-hours, **about 0.9 charged hours** on six workers; with generation, gates and evaluation, about 1.5. (The review's "about 7 charged hours" does not follow from the per-update figures it cites; the arithmetic here is 49,152 × (0.0091 + 0.0129) + 98,304 × (0.0124 + 0.0147) = 3,745 s per replicate.)

## 11. Gates, stop rules and NOT EVALUABLE outcomes

Engineering gates (stage A1; a failure stops the stage before any new read is computed):

1. Checkpoint and data identities (§4).
2. **Count reproduction.** T0, F0 and I256@512 through the new code reproduce P10-S1's recorded correct and useful counts exactly, for every cell and checkpoint read. I256@512's index hash equals the recorded one.
3. **Recall reproduction (uses the sealed values).** T0's CR8 at U_P equals the recorded `tree_recall_of_exhaustive_top8`; I256@512's CR8 equals the recorded index recall at every checkpoint read. The gate prints equal or not equal only.
4. **Exactness identities.** Tv with v = 1: priors on and off give identical selections and weights. Tv with v = N/256, priors on, equals T3; priors off, equals T2. An index is identical on rebuild.
5. Seeds (§5), with the declared exemption.

- A cell that fails gate 2 or 3 is NOT EVALUABLE and is not repaired. If its F0 fails, the cell is NOT EVALUABLE for both labels. The consequence for R-DIAGNOSIS is §9 item 4.
- A stop on a resource cap is PAUSED and resumable; completed cells and reads are not recomputed.
- Stage A2: a failed cell is kept and not re-run; the stage is INCOMPLETE and R-CONFIRM is NOT RUN; a second attempt is the human lead's decision. No A2 seed is observed before its Decision 2.
- No read, threshold, cell, checkpoint or rule changes after the freeze. No read is added because a result looks close.

## 12. Limits, classified (DIRECTION.md §5)

| Limit | Kind | Rule |
|---|---|---|
| Hour cap of A1 and of A2; memory guards (3 GiB per worker, 18 GiB aggregate) | Resource cap | Set after the rehearsal as charged + 2 × projected remaining. Extended by the human lead on cost projections only. A stage at its cap is PAUSED |
| Candidate budgets, visit counts, three index seeds, ten Lloyd iterations, the four checkpoints per cell | Design ceiling | Fixed. "Feasible" means c < N and v ≤ N/256, and nothing else |
| A2's run lengths | Design ceiling | Pinned to P10-S1's; not extended, since the purpose is the same checkpoints on new draws |
| 0.5 (gap), 0.25 and 0.90 (RESTORED), 0.473 (floor), 0.5 (closure), 0.90 (R), 0.10 (plateau), 512, 4 of 5 | Scientific threshold | Never changed after the freeze |

## 13. Stages, frozen inputs and machine load

- **Order.** Independent review of this draft → the human lead's approval → implementation with tests and an independent implementation audit → rehearsal of every stage end to end against the frozen plan itself, on a synthetic memory and on one rehearsal-trained tree and flat cell → freeze → the human lead's Decision 2 for A1 → A1 once → independent recomputation (the auditor receives the specification, code and records, not the lead's conclusions; it also recomputes CR8 and AM_C of T0 at one primary cell from the checkpoint tensors) → outcome record. A2 has its own Decision 2, before or after A1's result; its reads use the same freeze.
- **One frozen-input set, and the ADR text is not in it:** `studies/p10ir/**`; the config, which holds every threshold; launch scripts; `freeze/plan.json` (the list of cells, checkpoints and reads; every stage derives its items from this file only); stage caps; the checkpoint digests; P10-S1's data manifests; for A2, the bridge draws' manifests. Identity is by SHA-256 of each listed file. The freeze record stores the ADR's hash for provenance only. A test asserts that every threshold in this ADR equals the config's value. Nothing is written in the frozen files between a Decision 2 and the end of that stage's report; notes go to the human lead directly or to another branch. An identity difference stops a task as PAUSED — IDENTITY; restoring the file bit for bit lets the stage resume.
- **Machine load.** No stage needs a quiet machine: this study registers no wall-time or CPU-time comparison. Seconds per read are recorded descriptively. The machine is also the human lead's working computer; six workers at about 0.4 GiB each, as P10-S1 measured.
- **Platform of record:** macOS arm64 (the machine P10-S1 ran on). The reproduction gates are bit-exact and are asserted on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; a GitHub run is not required.
- **Analysis tests.** The analysis and the report are tested on a synthetic registry with known answers covering every row of §8.3 and §8.4, CELL-DEPENDENT, CHECKPOINT-DEPENDENT, both STILL LEARNING tags, every value of R-CONFIRM and every descriptive section; registry keys carry the read's name so that two reads of one cell cannot share a key (the defect of `studies/p10s1/analysis.py` lines 167–169).

## 14. Cost projection (estimates, to be replaced by the rehearsal)

Measured basis: P10-S1's evaluation charged 1,899 s for 1,866 snapshot evaluations on six workers, each with the full ablation set (`ledger_after_run.json`, `OUTCOME.md` §1); one snapshot of a 32,768-fact cell took about 20–30 worker-seconds.

| Item | Charged hours, six workers |
|---|---|
| A1: 70 cells × 4 checkpoints = 280 checkpoints; about 14 tree reads or about 17 flat reads each | **2–5** (the review's estimate; the draft's earlier 1–3 was tight) |
| A2: training 20 cells, generation, gates, the same reads on 40 checkpoints | **about 1.5** |
| Rehearsal and gates | under 1 |
| **Total** | **about 4–8** |

The rehearsal measures seconds per read at 16,384 slots and 32,768 facts, and peak memory of the all-keys reads.

## 15. What this study cannot establish

- Any cause that acts during training. That a fix would work. Anything about a router or index trained for the purpose, a refreshed index, or product-key memory: those are Stage B.
- A confirmed read-time cause without R-CONFIRM: CONFIRMED.
- Anything beyond P10-S1's memories: one task that a lookup table solves, oracle addressing, rate 0.003, one tree design (2 of N/256 branches of 256 slots), one index construction, crowded oracle codes.
- That the tree should be kept or replaced. That longer training closes the gap to the flat memory (ADR-0026).
- That recall of the tree's own nearest keys is recall of the entries that hold the fact.
- Efficiency, speed or I/O: keys scored are logical counts.
- Anything that revises P10-S1's TREE_BEHIND or any other registered label.

## 16. Open choices reserved for the human lead

1. **Own ADR or a part of ADR-0024.** Own ADR recommended by the reviewer and the lead. **PENDING HUMAN LEAD RULING.**
2. **Co-primary checkpoints with no recommendation when they differ** (recommended), or one primary checkpoint named in advance.
3. **The recall floor R = 0.90 and the closure figure 0.5** (§8.3). **PENDING HUMAN LEAD RULING.**
4. **The retention rule** (0.25 bits and 0.90 of the reference's information) in place of the note's 95% of accuracy (recommended).
5. **Stage A2.** Fund it with A1 (recommended; about 1.5 hours), and require CONFIRMED before any Stage B specification states a cause. Or run A1 alone.
6. **May a Stage B study be proposed on A1 alone?** Recommended: proposed yes, with its re-analysis status stated; approved only with R-CONFIRM in hand.
7. **Order against ADR-0024 and ADR-0026.** Recommended: this study first; it is short and informs both.

## 17. Review record

Independent review by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, verdict NOT READY; its sections A, B and C and the findings below concern this lane. This revision is by the lead's workflow (Claude Fable 5.2). It has not been re-reviewed. Neither is Astra validation or a human approval. Findings that concern only the capacity study are in ADR-0024 §22.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| Point A: run length primary, chosen knowing the data | — | FIXED: co-primary; no single action when they differ; plateau check; disclosure beside the rule | §8.1, §9 |
| Point B: what the 2 × 2 can identify; recall enters no rule | — | FIXED | §3, §6, §7, §8.3 |
| Point C: own ADR | — | FIXED, pending the human lead's ruling | header, §16 item 1 |
| F2 tree label misassigns causes | BLOCKING | FIXED: P, C, J, H, R table; EXACT SEARCH HARMS; CONTENT gated on recall; T1w added | §6, §8.3 |
| F3 N/8 | REQUIRED | FIXED: 512; sufficiency at every larger budget; measured counts printed | §8.4 |
| F8 U_P / run length | REQUIRED | FIXED | §9 |
| F9 R-CONFIRM | REQUIRED | FIXED: bridge funded here, pinned to P10-S1's lengths, both pairs compared. ANSWERED on cost: about 0.9 charged hours by the cited figures, not about 7 | §10 |
| F10 (d) Lane R cost | REQUIRED | FIXED | §14 |
| F11 recall records | REQUIRED | FIXED: described exactly, sealed, used as gates | §4, §11 |
| F12 one ADR, two freezes | REQUIRED | FIXED: split; ADR text not a frozen input | §13 |
| F15 disclosure placement | REQUIRED | FIXED | §8.1, §9 |
| F16 gates; G9 exemption | REQUIRED | FIXED | §5, §6, §11 |
| F20 bridge duplication | ADVISORY | FIXED by construction: the bridge is on its own draws at 0.003 and duplicates no registered cell | §10 |
| F21 measurement definitions | ADVISORY | FIXED | §3, §6, §7 |
| F24 replicate accounting | ADVISORY | FIXED | §8.2 |
| F25 tags | ADVISORY | FIXED | §0 |
| F26 retention table; "in bits" | ADVISORY | FIXED | §8.1 |
| F27 seeds | ADVISORY | ANSWERED: all seeds go to the seed registry | §5 |

Added in this revision and not yet reviewed: the read T1w, the nine-row table of §8.3 with the recall floor, the sufficiency rule of §8.4, and stage A2's training inside this ADR.

`Astra review: NOT_PERFORMED`.
