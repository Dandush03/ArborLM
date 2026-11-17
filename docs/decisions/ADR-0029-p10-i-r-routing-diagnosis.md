# ADR-0029 — P10-I-R — frozen-checkpoint routing diagnosis (Stage A)

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). Draft 2 of this ADR. It began as the routing lane of ADR-0024 draft 1, was revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, NOT READY) and moved to its own ADR, and is revised again after the confirmation review (`REVIEW2_ADR-0024_ADR-0029.md` beside it, NOT READY). §17 maps every finding that concerns it. **SPEC: PENDING ASTRA REVIEW.** `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- **Study code** P10IR. **Package** `studies/p10ir/` (new code only; no file of `studies/p9` or `studies/p10s1` is edited). **Config** `configs/p10ir_routing.toml`. **Tests** `tests/test_p10ir_*.py`.
- **Origin.** `docs/reviews/p10-i-direction-2026-11-17/LITERATURE_AND_ROUTING_NOTE.md` sections 4 and 5 (binding direction). The question as the note puts it: can ArborLM keep the flat memory's accuracy while using tree-like sparse retrieval, without losing its ability to keep learning? This study addresses only the first, diagnostic step.
- **Where it lives.** The human lead's direction (note §5.4) placed this lane inside ADR-0024. Giving it its own ADR is the reviewer's and the lead's recommendation, **PENDING HUMAN LEAD RULING**. Reasons: it shares no rule, budget or frozen input with the capacity study; it is a short re-analysis where that is a long training study; and one ADR hashed into two freezes repeats the failure of P10-S1 attempt 1. The content of the lane is unchanged by where it lives. **The human lead ruled on 2026-11-17: "Keep ADR-0029".** The routing diagnosis stays this ADR.
- **Immutability.** P10-S1's code, records, labels and run directory are not edited or revised. Its registered TREE_BEHIND stands. ArborLM is unproven research; nothing below is a success claim.
- **Approval.** The human lead alone approves this specification, its budget and each run. Lead's choices open to his ruling are marked **PENDING HUMAN LEAD RULING** and collected in §16.
- **Scope.** Stage A only. **Stage B (any new router, index training, product-key memory, periodic refresh, or other new architecture) is outside this ADR**; if this study indicates it, it is a separate study with its own specification.

## 0. What kind of study this is

**A registered re-analysis of observed cells, with one confirmatory step on fresh checkpoints.**

| Stage | What | Trains? | What it can support |
|---|---|---|---|
| **A1** | New reads of P10-S1's existing frozen flat and tree checkpoints | No | Where a Stage B study would look. Not a statement about cause |
| **A2** (bridge) | The same frozen reads on 20 fresh checkpoints trained exactly as P10-S1 trained them | Yes: P10-S1's arms, rate and lengths; no new architecture | Whether A1's labels hold on cells whose accuracies were not seen when the rules were written. **Any claim about cause needs A2** |

Every label of this study is printed with `REGISTERED RE-ANALYSIS OF OBSERVED CELLS` (A1) or `FRESH CHECKPOINTS` (A2), and with `ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`.

## 1. Question, and what each outcome would mean

On the memories P10-S1 trained: is the tree's lower quality, relative to the flat memory, attributable at read time to the branch priors, to the router's hard restriction of candidates, to both, or to neither; and does an index built after training keep the flat memory's quality at the tree's candidate budget?

- The outcome line **R-DIAGNOSIS** has two components, a tree label and an index label (§9). It is a diagnosis, not a positive or negative for ArborLM.
- **"Identified"** means: a read-time change, with nothing retrained, restored or mostly closed the gap. **NOT IDENTIFIED** is a registered value; it means the reads cannot tell, and **it recommends nothing, in every combination** (§9).
- **NOT EVALUABLE** and **CHECKPOINT-DEPENDENT** are registered values. A component that is CHECKPOINT-DEPENDENT carries no recommended action.
- The second line, **R-CONFIRM**, says whether A2 reproduced A1's labels. Neither line substitutes for the other.

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

`studies/p9/model.py`, `_top_tree`, `select`, `delta`; `src/arborlm/pilot_model.py`, `stable_top`; checked by both reviews.

- The query is the fact's fixed oracle code. It does not depend on the context, so recall and attention measures are per fact.
- Route scores are cos(q, router row)/0.2 for each of the N/256 branches. The two best branches are visited (ties to the lower id). Each of their 512 keys is scored cos(q, key)/0.2 **plus the log-softmax, over all branches, of its branch's route score** (the branch prior). The top 8 are selected; the read's weights are the softmax of those eight scores.
- **The prior is one constant per branch.** It shifts every key of a branch equally. So it has exactly two effects: it can change *which* slots are selected, by moving slots of one branch above or below slots of the other; and it changes the *relative weight between selected slots of different branches*. It never changes the order or the relative weights of slots within one branch.
- **If all eight slots selected with the prior lie in one branch, the prior does not change their weights; it may still have decided which slots were selected.** (Draft 1 of this ADR, and the first review, said the prior then has no effect at all. That was false.) With one branch visited there is no other branch, and priors on and off are mathematically the same read.
- A slot received no gradient from a fact at any update at which the router did not visit its branch for that fact. Routing changes during training and its history is not recorded.

Consequences for the design: "priors distort the weights" can only mean cross-branch reweighting and cross-branch selection; a read over all keys with the priors kept is a soft branch restriction, not exact search; with a confident router the prior on unvisited branches is very negative, so that read may select the same slots as the trained read; and exact search over a jointly trained tree can select slots that were rarely or never trained for the fact, so it can do harm without the content being poor.

*Re-check of the labels against the corrected sentence.* No rule of §8 used the false statement: every row is defined on end-task information of whole reads (T0, T1, T2, T3) and on recall. The one measure that could be misread is "share of facts whose eight selected slots span both branches" (§7): it bounds where reweighting can act, not where the prior can act, and is now described so.

## 4. Inputs, and what has already been seen

**Checkpoints (A1).** P10-S1 attempt 2, `experiments/P10S1-registered-attempt2-20261117/cells/<label>/snapshots/u<update>/model.pt`, F-OQ and T-OQ at the seven grid cells, five replicates: 70 cells. The directory is local and git-ignored. Each `model_sha256` in `snapshot.json` is checked against the cell's `train.json`, whose digest is in the committed `results/p10s1-run-2026-11-17/manifests/train.manifest.json`. P10-S1's draws are regenerated by its fixed generation script and checked against its freeze hashes. Nothing in the run directory is written. Both reviews confirmed that every checkpoint named below exists on disk.

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

**The recorded recall values, described exactly.** P10-S1's evaluation stored two quantities in each cell's `eval.json`:

- (a) `tree_recall_of_exhaustive_top8`, **for T-OQ only, at U_P only** (`studies/p10s1/evaluate.py`, `tree_recall`): over the oracle codes of all trained facts of the cell, the share of the exhaustive top 8 whose branch the router visited. The exhaustive top 8 is taken by `topk` of the cosine against `F.normalize(keys)`, without the slot-id tie rule.
- (b) `ivf_measured.recall_of_exhaustive_top8`, **for every F-OQ-IVF read, at every snapshot** (`studies/p10s1/index.py`, `IVFMemory.measured`). It is accumulated over **every query the index read receives during the Panel A pass** of `_read_record`: the main read and the address-swap read, all eight records of every context (facts outside the cell and unseen-control facts included), each weighted by how often it occurs. It is **not** recall over the trained facts of the cell.

Neither appears in `analysis.json`, `results.json`, `RESULTS.md` or the audit outputs. Both reviewers read the code and key names only. No one in this workflow reports having opened the values; the drafter has not.

**Sealing rule.** No one opens those two keys before this ADR's freeze. The counts the reproduction gate needs sit in the same `eval.json` files, so **every access to an `eval.json` of that run goes through one whitelist extractor** in `studies/p10ir/`, which returns only the keys a gate names and prints equal or not equal for the sealed ones, never their values. No one prints or opens an `eval.json` of that run outside it. The freeze record states, for the lead, the implementer and the auditor, that none has. If the seal is broken, the freeze record says so and the CONTENT label (§8.3), which uses recall, carries RECALL SEEN BEFORE FREEZE.

## 5. Seeds

Values are those of `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` §4.2 (checker result PASS):

| Role | Values |
|---|---|
| Bridge draw sets (A2), complete P10-S1-style draws | 290001 + 100(d − 1), d = 1..5 (P10-S1's in-set layout; index seed at base + 60) |
| Bridge initialisation | draw d → 330600 + d (330601–330605) |
| I64 index seeds | 298001, 298002, 298003 |
| Rehearsal draw and initialisation | 299201 with 330692 |
| Test mode; unit tests | 330698, 330699; 938001–938999 |
| **Declared re-use, not an allocation** | P10-S1's five registered draws (bases 210001–210401) and their index seeds (base + 60), for the reproduction reads of stage A1; one P10-S1 cell's draw and initialisation seed for the adapter identity gate of §10 |

The registry assigns every role this draft needs. Before the freeze, the seed gate runs a copy of `seed_registry_check.py` extended with these named values, with rules R2 and R3 expanded (registry §4.3 item 5), and requires RESULT: PASS; it lists the re-used P10-S1 seeds as re-used, not as new.

## 6. Reads

Every read changes one stated thing against a named reference. Values, output projection and gate are the checkpoint's. Nothing is trained or tuned in stage A1.

**Tree checkpoint.** All tree reads go through **one code path**: "the router's v best branches, prior on or off in selection, prior on or off in weights". T3 and T2 are that path with v = N/256.

| Read | Keys scored | Prior | Changed against | What the difference can show |
|---|---|---|---|---|
| **T0** | router's 2 branches (512) | in selection and weights | — | The registered read. Must reproduce P10-S1's counts exactly |
| **T1** | router's 2 branches | removed | T0 | The whole read-time effect of the prior, candidates fixed |
| **T1w** | router's 2 branches | kept in the selection of the 8, removed from their weights | T0, T1 | Splits the prior's effect into cross-branch reweighting (T1w − T0) and selection (T1 − T1w) |
| **T3** | all N keys (v = N/256) | kept (every key has its branch's prior) | T0 | Removing the **hard** restriction while the **soft** one stays. **This is not exact search**, and it may select what T0 selects |
| **T2** | all N keys (v = N/256) | removed | T1, T3 | **Exact search**: the tree's keys and values read as a flat memory |
| **Tv** | router's v best branches, priors on and off | | T0 | Candidate budget. v ∈ {1, 2, 4, 8} with v ≤ N/256. At 1,024 slots (4 branches) v ∈ {1, 2, 4}, and v = 4 is T3 / T2; v = 8 does not exist there. A budget of 128 does not exist for 256-slot branches |

**Flat checkpoint.**

| Read | What | Purpose |
|---|---|---|
| **F0** | exhaustive, as registered | Reference. Must reproduce P10-S1's counts exactly |
| **I256@512** | the registered index (N/256 lists, at least 512 candidates, P10-S1's index seed) | Reproduction of F-OQ-IVF |
| **I64@c** | k-means into N/64 lists (the registered construction otherwise); lists visited in order of centroid score until **at least** c keys are collected; c ∈ {128, 256, 512, 1,024, 2,048} with c < N; three index seeds | Post-hoc sparse retrieval per budget. Lists of 64 make 128 distinct from 256 |

Feasibility: at 1,024 slots the index budgets are 128, 256, 512 (1,024 and 2,048 are not below N); at 4,096 and 16,384 all five. c is a minimum; the measured mean and 99th-percentile candidate counts are printed beside every nominal c. Cells at 1,024 slots are marked SHALLOW (four branches; 512 candidates is half the store).

## 7. Measurements

Per checkpoint and read:

| Measure | Definition |
|---|---|
| End-task | a_use, i, raw accuracy on Panels A and B, with P10-S1's derangement (ADR-0021 §7.1) |
| Candidate recall CR8, CR1 (**new measurements of this study**) | Over all trained facts of the cell, each once: mean of \|C ∩ E8\| / 8, and the share of facts with E1 ∈ C. C is the set of keys the read scores. E8 and E1 are the top 8 and top 1 by cosine over all keys of **the same checkpoint**, without priors, by `stable_top` (ties to the lower slot id). They are per fact and have no panel |
| Selection overlap SR8 | Mean of \|S ∩ E8\| / 8; S is the 8 slots the read selects |
| Recovered attention mass AM_C, AM_S | Σ of w_E(s) over s ∈ C, and over s ∈ S; w_E is the softmax at temperature 0.2 over E8's cosines |
| Prior effect | i(T1) − i(T0), i(T1w) − i(T0), i(T2) − i(T3); the share of facts whose selected set changes between T0 and T1; the share of facts whose eight selected slots span both branches (where reweighting can act); the mean total-variation distance between the two reads' weights, over the union of the two selected sets with weight zero outside each |
| **Testability of the candidate restriction** | The share of facts whose T3 selection equals T0's. Printed with every tree label. If it is near 1, T3 could not differ from T0 and the row CANDIDATES was not testable at that cell |
| Work | Keys scored per query, counted. Logical; not measured efficiency |

- **CR8 is not either recorded quantity of §4.** The tree record uses another tie rule; the index record averages another query population. The recorded quantities are recomputed by their own definitions for the gate of §11 and enter no label.
- For an index read of the flat memory there is no prior, so SR8 = CR8 and AM_S = AM_C, and a fact whose E8 is wholly among the candidates is read exactly as F0 reads it. A loss of quality there is a loss of recall by construction; the curve of quality against AM_C per budget is the finding.
- For the tree, recall is recall of what the tree's own keys rank first. It does not say those slots hold the fact. **This is why recall enters only one rule (§8.3, CONTENT), as a necessary condition, and is otherwise descriptive.**
- **Why the dense map is not a reference here.** The outside note (§3) asks that retention be read "against the dense and the flat baselines". This study asks whether a retrieval change over a given memory keeps what exhaustive retrieval over a memory of the same kind gets; the flat memory F0 is that reference. D-OQ has no retrieval to change. The comparison with the dense map belongs to ADR-0024 (its §9.2) and is not repeated here; D-OQ's a_use at the same cells is printed for context from P10-S1's records.

## 8. Labels

### 8.1 The retention rule

For a read X and a reference Y of the same cell, checkpoint, replicate and panel:

- **A gap exists** if i(Y) − i(X) ≥ 0.5 bits (the programme's unit of a material difference, ADR-0021 §8.2).
- **X is RESTORED to Y** if i(Y) − i(X) ≤ 0.25 bits **and** i(X) ≥ 0.90 · i(Y), with i(Y) ≥ 0.473 bits (a_use ≥ 0.25); below that floor the comparison is WEAK REFERENCE.
- **Gap closure** of a tree read X′: g(X′) = [i(X′) − i(T0)] / [i(F0) − i(T0)], defined where a gap exists between T0 and F0. Write g_P = g(T1), g_C = g(T3), g_PC = g(T2).

*Why not 95% of accuracy (the note's proposal).* At the flat memory's 0.992, 95% is 0.942: a loss of 0.50 bits per fact, the size this programme calls a full capacity step. At a loaded cell (0.654) it is a loss of 0.19 bits. A ratio of accuracies means different things across the range. The rule uses the information measure every rule already uses. 0.25 bits is the "not behind" margin ADR-0021 fixed for every comparator label before any S1 record; it binds above about 2.5 bits. 0.90 is the pass ratio against an oracle reference used in P10-S0 and in the U_P rule; it binds below. In bits, i is zero at or below the chance interval and counts only answers that depend on the read, so the ratio of i is the retained improvement above the no-memory baseline in bits; the floor stops a weak reference from being matched trivially. The accuracy version, [acc(X) − acc₀] / [acc(Y) − acc₀], is printed beside it and decides nothing.

*What the rule requires in accuracy* (both reviews' computation from the mean a_use of F0; the rule itself is applied per replicate and panel):

| Cell, checkpoint | F0 a_use | a_use a read needs to be RESTORED | Share of the improvement above chance retained |
|---|---|---|---|
| 8K/4K, U_P | 0.948 | 0.920 | 0.969 |
| 8K/4K, run length | 0.996 | 0.974 | 0.977 |
| 32K/16K, U_P | 0.916 | 0.885 | 0.965 |
| 32K/16K, run length | 0.992 | 0.969 | 0.976 |
| 8K/1K (loaded), U_P / run length | 0.390 / 0.654 | 0.366 / 0.613 | 0.933 / 0.934 |
| 32K/4K (loaded), U_P / run length | 0.392 / 0.637 | 0.368 / 0.597 | 0.933 / 0.934 |

At every primary cell it is stricter than 95% of accuracy; at the loaded cells it is slightly looser (0.613 against 0.621 at 8K/1K).

**Disclosure, placed with the rule.** These thresholds, the choice of cells and the reading of the two checkpoints were fixed knowing P10-S1's registered accuracies of T0, F0 and the index for the same five draws. At the run length the tree's gap to F0 is 1.87 and 2.28 bits at the primary cells (3.08 and 3.11 at U_P), and the index's is 2.27 and 3.17 (2.23 and 2.73 at U_P). So a tree read is closer to RESTORED at the run length and an index read is further from it. That is why neither checkpoint is primary (§9) and why a claim about cause needs A2 (§10).

### 8.2 Accounting, and what "the same label" means

- **Panels.** A condition on i holds in a replicate only if it holds on both panels. **NO GAP** needs the gap below 0.5 on both panels. A replicate with a gap on one panel only is **MIXED-PANEL** and satisfies no condition. R (below) is per fact and has no panel.
- **Replicates.** The denominator is always 5. A replicate that is NOT EVALUABLE, WEAK REFERENCE or MIXED-PANEL, or whose g is undefined, satisfies no condition. A cell's label at a checkpoint is the row held by at least 4 of 5 replicates; otherwise **MIXED**.
- **A cell is NOT EVALUABLE at a checkpoint** if at least 2 of its 5 replicates are NOT EVALUABLE there (a gate failure of either arm's checkpoint, §11, or WEAK REFERENCE). This is applied before the 4-of-5 rule.
- **Labels are compared by row name only**, in the 4-of-5 rule, in CELL-DEPENDENT, in CHECKPOINT-DEPENDENT and in R-CONFIRM. The suffix FULLY / PARTLY, the descriptive tags and c\* are printed and do not enter any comparison. A cell's c\* is the median of its replicates' c\* (replicates without one are listed).
- For I64@c, a replicate's i on a panel is the mean over the three index seeds, taken before the panel test.

### 8.3 Tree label, per cell and checkpoint

Reference F0 at the same cell, update count and replicate. Define, per replicate: **P** = T1 is RESTORED to F0, or g_P ≥ 0.5. **C** = T3 is RESTORED, or g_C ≥ 0.5. **J** = T2 is RESTORED, or g_PC ≥ 0.5. **H** = i(T2) ≤ i(T0) − 0.25 on both panels. **R** = CR8(T0) ≥ 0.90. First match wins.

| Order | Replicate label | Rule | What it claims, and no more | Next action |
|---|---|---|---|---|
| 1 | NOT EVALUABLE | a gate of §11 fails for the T-OQ or the F-OQ checkpoint; or WEAK REFERENCE | — | none |
| 2 | NO GAP | no gap between T0 and F0 on both panels | Nothing to explain at this cell | none |
| 3 | PRIORS AND CANDIDATES, SEPARATELY | P and C | Either change alone closes most of the gap at read time | Either: how routing scores enter the read, or candidate coverage |
| 4 | PRIORS | P, not C | Removing the prior, candidates unchanged, closes most of the gap | Redesign how routing scores enter the read |
| 5 | CANDIDATES | C, not P | Removing the hard restriction, prior kept, closes most of the gap | Improve the router and candidate coverage |
| 6 | JOINT | J, not P, not C | Only removing both closes most of the gap; neither alone does. The reads do not say whether the two must change together or whether the soft restriction left T3 untestable | none; no single fix is indicated |
| 7 | EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME | H, not P, not C | Exact search selects slots that serve the fact worse than the trained read. The content may be sound for the read it was trained under | none |
| 8 | CONTENT | not P, not C, not J, not H, and R | The router already finds at least 0.90 of what the keys rank first, the prior is not the cause, and quality is still below the flat memory | Improve memory training and representation |
| 9 | NOT IDENTIFIED | not P, not C, not J, not H, not R | The router misses what the keys rank first, yet scoring all keys does not help. The reads cannot say why | none |

Rows 3–6 are suffixed FULLY (the named read is RESTORED) or PARTLY (closure ≥ 0.5 only). PRIORS also prints, descriptively, **mainly weights** or **mainly selection**, by which of i(T1w) − i(T0) and i(T1) − i(T1w) is larger. Every row is reachable: rows 3–6 cover the seven combinations of P, C, J with at least one true; rows 7–9 split the remaining case by H and R. (J and H cannot both hold where a gap exists, so row 6 never hides a harm.)

- **The figure 0.5 for closure** means "most of the gap". **The figure 0.90 for R** is the same oracle-reference ratio as above: if nine tenths of what exact search would select is already scored, exact search can change at most one slot in ten, so the candidate restriction cannot be the main cause. Both are the lead's choices, **PENDING HUMAN LEAD RULING**; R is fixed without the recall values having been opened (§4).
- **Whether C was testable.** With a confident router T3 may equal T0 on nearly every fact; C is then false by construction, and a real effect of the restriction appears only as JOINT. The testability share (§7) is printed with every label so that this can be seen. Whether row 5 should become NOT TESTABLE above some share is **PENDING HUMAN LEAD RULING** (§16 item 9); this draft sets no such threshold.
- **Printed with every label:** i and a_use of T0, T1, T1w, T2, T3 and F0; g_P, g_C, g_PC; i(F0) − i(T2); the sweep Tv; CR8, CR1, SR8, AM_C, AM_S of T0; the prior-effect and testability measures.

### 8.4 Index label, per cell and checkpoint

Reference F0. A budget c is **sufficient** in a replicate if I64@c is RESTORED to F0 at c and at every larger feasible budget. A replicate's c\* is its smallest sufficient budget.

| Replicate label | Rule |
|---|---|
| SPARSE INDEX APPROACHES FLAT | c\* exists and c\* ≤ 512. **512 is the tree's candidate count**, the equal-candidate standard of ADR-0021 §8.5 |
| INDEX APPROACHES FLAT ONLY ABOVE 512 | c\* exists and c\* > 512 (reachable at 4,096 and 16,384 slots; at 1,024 slots no budget above 512 is read) |
| INDEX DOES NOT APPROACH FLAT | no sufficient budget |
| NOT EVALUABLE | a gate of §11 fails for the F-OQ checkpoint; or WEAK REFERENCE |

Printed with it: i, a_use, CR8, CR1, AM_C and the measured mean and 99th-percentile candidate counts at every budget; the cell's median c\*, as a count and as a share of N; and N/8 for comparison. The note's action for the first row is "investigate a separately trained sparse index"; the other rows carry none.

## 9. R-DIAGNOSIS: cells, checkpoints and combination

- **Primary cells: 8K/4K and 32K/16K.** They are the cells ADR-0021 §8.5 registered for the hierarchy label before any S1 record. 2K/1K, 2K/4K and 8K/16K are printed.
- **R-DIAGNOSIS-LOADED (descriptive; printed only).** The loaded cells 8K/1K and 32K/4K get the same labels by the same rules, printed under this name. It has no combination rule and enters nothing. There the flat reference itself holds 0.65 and 0.64: "restored" means restored to a full store.
- **U_P and the run length are co-primary.** Neither is "the" checkpoint. Draft 1 named the run length primary; the first review showed that the choice was made knowing which way it leans (§8.1 disclosure) and that it would decide what Stage B is pointed at. It is withdrawn.
- **Plateau check at the run length (existing snapshots; nothing new is trained).** For T-OQ and for F-OQ at each primary cell and replicate, on both panels: i\*(run) − i\*(run/2) ≤ 0.10 bits (the plateau limit of ADR-0021 §8.2; the snapshots at 24,576 and 49,152 exist). If it fails in at least 2 of 5 replicates, the cell's labels at the run length carry the tag **TREE STILL LEARNING** or **FLAT STILL LEARNING**. These i values are in P10-S1's records; the drafter has not computed the check.
- **Combination, explicit, in this order.**
  1. If either primary cell is NOT EVALUABLE (§8.2) at either checkpoint, **R-DIAGNOSIS is NOT EVALUABLE**. Nothing below is applied.
  2. Per component (tree label; index label) and per checkpoint: the component's value is the common row of the two primary cells; if they differ it is **CELL-DEPENDENT**, both printed.
  3. Per component: if its value is the same at U_P and at the run length, that is the component's value. Otherwise the component is **CHECKPOINT-DEPENDENT**, printed with both values, **and carries no recommended action**; the record says the answer depends on training duration and refers to ADR-0026.
  4. **R-DIAGNOSIS is the pair** (tree component, index component). The checkpoint rule is applied to each component separately, so that a tree label that is stable is not lost because the index label moves (confirmation review R-N16; §16 item 2).
- **Recommended actions.** A component recommends its row's action (§8.3, §8.4) only if it is a single row at both cells and both checkpoints. MIXED, CELL-DEPENDENT, CHECKPOINT-DEPENDENT, NO GAP, JOINT, EXACT SEARCH HARMS and NOT IDENTIFIED recommend nothing.
- **The note's last row ("none → consider a more fundamental change of the memory") is not issued by this study.** When the tree component is EXACT SEARCH HARMS or NOT IDENTIFIED and the index component is INDEX DOES NOT APPROACH FLAT, the record prints **NO READ-TIME CAUSE IDENTIFIED** and recommends nothing: a failure of read-time reads to identify a cause is not evidence that nothing short of a fundamental change would work. CONTENT keeps its one action whatever the index component is. This is a departure from the directed table (§16 item 8).
- The trajectory checkpoints of §4 are printed and enter no label.

**A limit printed with every label.** These are read-time changes to memories trained under the registered read. The tree's values and output projection were trained with the prior in the weights and two branches visited. A read-time change that does not help does not show that training without it would not; one that helps shows only that the trained content tolerates it. Causes that act during training need Stage B.

## 10. Stage A2 — the confirmatory read (bridge block)

- **Cells.** F-OQ and T-OQ at 8K/4K and 32K/16K, five fresh draws, one initialisation seed each: **20 cells.** Seeds: §5.
- **Pinned to P10-S1.** Learning rate 0.003; U_P 8,192 and run length 49,152 at 8K/4K; U_P 16,384 and run length 98,304 at 32K/16K; P10-S1's snapshot schedule, loss, optimizer and batch. The only differences from P10-S1's cells are the data draws and initialisation seeds. Nothing is taken from ADR-0024; this stage does not depend on it.
- **New adapter code is needed; existing code is not edited.** `studies/p10s1/core.py` refuses data seeds outside 210001–219999 (its `SEED_RANGE` and seed check), so the bridge cannot run "through `studies/p10s1` unedited" as the previous draft said. The bridge has its own plan, generation, training and evaluation wrappers in new files under `studies/p10ir/`. They call P10-S1's and P9's model, generator, loss and update functions unedited, and do not pass through P10-S1's seed whitelist; this study's seed gate (§11 item 6) replaces it (registry §4.3 item 4).
- **Adapter identity gate.** Before any bridge seed is used: the adapter, given one P10-S1 registered cell's draw and initialisation seed (F-OQ and T-OQ at 8K/4K, draw 1), reproduces that cell's stored checkpoint at its first three snapshots (512, 1,024, 2,048 updates) with identical `model_sha256`, on the platform of record. A mismatch stops stage A2 before training. This re-use of P10-S1 seeds is declared in §5.
- **Read.** The frozen A1 code, with no change of read, threshold or rule, at U_P and at the run length. Fresh checkpoints have no recorded recall; gate 3 of §11 does not apply, and gate 2 is replaced by "T0, F0 and I256@512 through the new read code equal the same checkpoints through P10-S1's evaluation functions, called from the adapter".
- **R-CONFIRM** (labels compared by row name, §8.2): **CONFIRMED** if A2's tree component and index component each equal A1's, where two CHECKPOINT-DEPENDENT components are equal only if their values at U_P and at the run length are equal. **NOT CONFIRMED** otherwise, with both printed, per component. **NOT APPLICABLE** if A1's R-DIAGNOSIS is NOT EVALUABLE. **NOT RUN** if the stage is not funded or not complete. R-CONFIRM does not change R-DIAGNOSIS.
- **What may be said.** After A1 alone: "the re-analysis points to …". A statement that the tree's gap *is caused by* a named factor at read time requires CONFIRMED for the tree component. Neither supports a statement about training-time causes.
- **Cost.** At P10-S1's measured seconds per update (0.0091 and 0.0129 at 8K/4K; 0.0124 and 0.0147 at 32K/16K): 49,152 × (0.0091 + 0.0129) + 98,304 × (0.0124 + 0.0147) = 3,745 s per replicate, about 18,700 worker-seconds, **0.87 charged hours** on six workers. The confirmation review recomputed it (0.867 h; the 20 matching P10-S1 cells took 0.871 h) and withdrew the first review's "about 7". With generation, the identity gate, gates and evaluation: about 1.5.

## 11. Gates, stop rules and NOT EVALUABLE outcomes

Engineering gates of stage A1. A failure of gate 1, 5 or 6 stops the stage before any new read is computed. Gates 2–4 are per checkpoint.

1. **Identities.** Checkpoint and data identities (§4).
2. **Count reproduction (bit-exact on the platform of record).** T0, F0 and I256@512 reproduce P10-S1's recorded correct and useful counts exactly, for every cell and checkpoint read; I256@512's index hash equals the recorded one. These reads call the same P9 and P10-S1 functions the registered evaluation called, on the same platform, so equality is guaranteed if the code is right.
3. **Recall reproduction (sealed values; the recorded quantities by their own definitions).**
   (a) P10-S1's `tree_recall`, recomputed as P10-S1 defined it (all trained facts' oracle codes; exhaustive top 8 by `topk` of the cosine against `F.normalize(keys)`; integer hit and total counts), equals the recorded `tree_recall_of_exhaustive_top8` at U_P.
   (b) P10-S1's index recall, recomputed as P10-S1 defined it (every query `IVFMemory._top_flat` receives during the Panel A pass of `studies/p10s1/evaluate.py` `_read_record`, the address-swap reads included; top 8 of the masked scores against `stable_top` of the unmasked scores), equals the recorded `ivf_measured.recall_of_exhaustive_top8` at every checkpoint read.
   The gate prints equal or not equal only. **These gate quantities are not CR8 and enter no label.**
4. **Exactness identities, with the precision each can have.**
   - Tv with v = 1, priors on against off: mathematically the same read. In floating point, adding the constant can create or remove a tie at the eighth place and can change a weight in the last digits. Required: selections identical except at float ties, which are counted and printed (more than 0.1% of facts fails the gate); weights equal within 1e-6.
   - T3 and T2 are the common code path at v = N/256, so they are that path by construction. An **independent** flat computation (`q @ keys.T` over all keys, with and without the per-key prior) is run as an extra gate read at every cell: selections identical to T3 / T2 except at float ties (counted, same limit); weights within 1e-6. At 4,096 and 16,384 slots this v = N/256 read is beyond the sweep's largest v = 8 and exists for the gate and for T2 / T3 only.
   - An index is bit-identical on rebuild with the same seed, on the platform of record.
5. **Rehearsal.** Every stage has run end to end against the frozen plan file itself.
6. **Seeds** (§5), with the declared re-use.

Consequences and stop rules:

- A checkpoint that fails gate 2, 3 or 4 makes its replicate NOT EVALUABLE at that checkpoint for the labels that use it (a T-OQ checkpoint: the tree label; an F-OQ checkpoint: both labels, since F0 is the reference of both). It is not repaired. The cell-level and study-level consequences are §8.2 and §9 item 1.
- A stop on a resource cap is PAUSED and resumable; completed cells and reads are not recomputed.
- Stage A2: a failed cell is kept and not re-run; the stage is INCOMPLETE and R-CONFIRM is NOT RUN; a second attempt is the human lead's decision. No A2 seed is observed before its Decision 2.
- No read, threshold, cell, checkpoint or rule changes after the freeze. No read is added because a result looks close.

## 12. Limits, classified (DIRECTION.md §5)

| Limit | Kind | Rule |
|---|---|---|
| Hour cap of A1 and of A2; memory guards (3 GiB per worker, 18 GiB aggregate) | Resource cap | Set after the rehearsal as charged + 2 × projected remaining. Extended by the human lead on cost projections only. A stage at its cap is PAUSED |
| Candidate budgets, visit counts, three index seeds, ten Lloyd iterations, the four checkpoints per cell | Design ceiling | Fixed. "Feasible" means c < N and v ≤ N/256, and nothing else |
| A2's run lengths | Design ceiling | Pinned to P10-S1's; not extended, since the purpose is the same checkpoints on new draws |
| 0.5 (gap), 0.25 and 0.90 (RESTORED), 0.473 (floor), 0.5 (closure), 0.90 (R), 0.10 (plateau), 512, 4 of 5, 2 of 5 (NOT EVALUABLE), the gate tolerances | Scientific threshold | Never changed after the freeze |

## 13. Stages, frozen inputs and machine load

- **Order.** Independent review of this draft → the human lead's approval → implementation with tests and an independent implementation audit → rehearsal of every stage end to end against the frozen plan itself, on a synthetic memory and on one rehearsal-trained tree and flat cell (rehearsal seeds of §5) → freeze → the human lead's Decision 2 for A1 → A1 once → independent recomputation (the auditor receives the specification, code and records, not the lead's conclusions; it also recomputes CR8 and AM_C of T0 at one primary cell from the checkpoint tensors) → outcome record. A2 has its own Decision 2, before or after A1's result; its reads use the same freeze.
- **One frozen-input set, and the ADR text is not in it:** `studies/p10ir/**`; the config, which holds every threshold; launch scripts; `freeze/plan.json` (the list of cells, checkpoints and reads; every stage derives its items from this file only); stage caps; the checkpoint digests; P10-S1's data manifests; for A2, the bridge draws' manifests. Identity is by SHA-256 of each listed file. The freeze record stores the ADR's hash for provenance only. A test asserts that every threshold in this ADR equals the config's value. Nothing is written in the frozen files between a Decision 2 and the end of that stage's report; notes go to the human lead directly or to another branch. An identity difference stops a task as PAUSED — IDENTITY; restoring the file bit for bit lets the stage resume.
- **Machine load.** No stage needs a quiet machine: this study registers no wall-time or CPU-time comparison. Seconds per read are recorded descriptively. The machine is also the human lead's working computer. Memory: P10-S1's evaluation tasks peaked at **1.415 GiB per worker** (`manifests/evaluate.manifest.json`); its training peak was 0.39 GiB. Six workers are within the 18 GiB guard on those figures; the all-keys reads are measured in the rehearsal.
- **Platform of record:** macOS arm64 (the machine P10-S1 ran on). Bit-exact assertions (gates 1–3, the index rebuild, the adapter identity gate) are made on it only; elsewhere they are skipped, and only the tolerance gates run. Checks (`ruff`, `mypy`, `pytest`) run locally; a GitHub run is not required.
- **Analysis tests.** The analysis and the report are tested on a synthetic registry with known answers covering every row of §8.3 and §8.4, MIXED-PANEL, MIXED, cell-level NOT EVALUABLE, CELL-DEPENDENT, CHECKPOINT-DEPENDENT per component, NO READ-TIME CAUSE IDENTIFIED, both STILL LEARNING tags, every value of R-CONFIRM and every descriptive section; registry keys carry the read's name so that two reads of one cell cannot share a key (the defect of `studies/p10s1/analysis.py` lines 167–169).

## 14. Cost projection (estimates, to be replaced by the rehearsal)

Measured basis: P10-S1's evaluation charged 1,899 s for 1,866 snapshot evaluations on six workers, each with the full ablation set (`ledger_after_run.json`, `OUTCOME.md` §1); one snapshot of a 32,768-fact cell took about 20–30 worker-seconds.

| Item | Charged hours, six workers |
|---|---|
| A1: 70 cells × 4 checkpoints = 280 checkpoints; about 14 tree reads or about 17 flat reads each, plus the gate reads | **2–5** |
| A2: training 20 cells (0.87), generation, identity gate, gates, the same reads on 40 checkpoints | **about 1.5** |
| Rehearsal and gates | under 1 |
| **Total** | **about 4–8** |

The rehearsal measures seconds per read at 16,384 slots and 32,768 facts, and peak memory of the all-keys reads.

## 15. What this study cannot establish

- Any cause that acts during training. That a fix would work. Anything about a router or index trained for the purpose, a refreshed index, or product-key memory: those are Stage B.
- A confirmed read-time cause without R-CONFIRM: CONFIRMED.
- Whether the candidate restriction matters by itself, wherever T3 selects what T0 selects (§8.3).
- Anything beyond P10-S1's memories: one task that a lookup table solves, oracle addressing, rate 0.003, one tree design (2 of N/256 branches of 256 slots), one index construction, crowded oracle codes.
- That the tree should be kept or replaced, or that a more fundamental change is or is not needed. That longer training closes the gap to the flat memory (ADR-0026).
- That recall of the tree's own nearest keys is recall of the entries that hold the fact.
- Efficiency, speed or I/O: keys scored are logical counts.
- Anything that revises P10-S1's TREE_BEHIND or any other registered label.

## 16. Open choices reserved for the human lead

1. **Own ADR or a part of ADR-0024.** Own ADR recommended by the reviewer and the lead. **RULED by the human lead on 2026-11-17: "Keep ADR-0029".** This supersedes the placement in `LITERATURE_AND_ROUTING_NOTE.md` section 5.4; the directed content of the lane is unchanged.
2. **Checkpoints.** Co-primary, the rule applied to the tree label and the index label separately, and no recommendation for a component that differs between them (recommended). Or one primary checkpoint named in advance; or the rule applied to the pair as a whole.
3. **The recall floor R = 0.90 and the closure figure 0.5** (§8.3). **PENDING HUMAN LEAD RULING.**
4. **The retention rule** (0.25 bits and 0.90 of the reference's information) in place of the note's 95% of accuracy (recommended).
5. **Stage A2.** Fund it with A1 (recommended; about 1.5 hours), and require CONFIRMED before any Stage B specification states a cause. Or run A1 alone.
6. **May a Stage B study be proposed on A1 alone?** Recommended: proposed yes, with its re-analysis status stated; approved only with R-CONFIRM in hand.
7. **Order against ADR-0024 and ADR-0026.** Recommended: this study first; it is short and informs both. **RULED by the human lead on 2026-11-17:** asked whether this study should be the first P10-I study prepared for approval, the human lead answered "yes it should". This fixes the order of preparation; it does not approve the specification.
8. **Departures from the next-action table of the note's §5.2.** The note is binding direction; each departure below changes directed content and is **PENDING HUMAN LEAD RULING**. The reasons are in §3 and §8.3.

| Note §5.2: Stage A result → next action | This ADR | What changes |
|---|---|---|
| Exact search restores the tree's quality → improve the router and candidate coverage | CANDIDATES (T3 closes most of the gap, prior kept) → the same action. JOINT (only T2 does) → no action | "Exact search restores" is split. Where only removing both the restriction and the prior helps, no single fix is named |
| Exact search does not restore it → improve memory training and representation | CONTENT → the same action, **only if** the router already finds at least 0.90 of what the keys rank first and exact search does no harm. EXACT SEARCH HARMS and NOT IDENTIFIED → no action | "Does not restore" no longer implies poorly learned content by itself |
| Removing branch priors restores it → redesign how routing scores enter the read | PRIORS → the same action, also when the gap is mostly (≥ 0.5) but not fully closed. PRIORS AND CANDIDATES, SEPARATELY → either action | A partial-priors case is added; a both-work case is added |
| Post-hoc indexing approaches the flat memory → investigate a separately trained sparse index | SPARSE INDEX APPROACHES FLAT → the same action, only at a budget of at most 512 keys that also holds at every larger budget. ONLY ABOVE 512 → no action | "Approaches" is tied to the tree's candidate count |
| None → consider a more fundamental change of the memory | NO READ-TIME CAUSE IDENTIFIED → no action | **The row is not issued.** Unidentified is not treated as evidence for a fundamental change |
| (not in the note) | CHECKPOINT-DEPENDENT, CELL-DEPENDENT, MIXED → no action; a retention rule in bits in place of 95% of accuracy; the confirmatory stage A2 | Added |

9. **Testability of the candidate restriction** (§8.3). Print the share and leave row 5 as it is (this draft), or make CANDIDATES "NOT TESTABLE" above a registered share of facts on which T3 selects what T0 selects.

## 17. Review record

Both reviews are by the `arbor-auditor` subagent (Claude Opus 5.5). Both revisions are by the lead's workflow (Claude Fable 5.2). **This draft has not been re-reviewed.** Neither review is Astra validation or a human approval. Findings that concern only the capacity study are in ADR-0024 §22.

### 17.1 First review (`REVIEW_ADR-0024.md`, NOT READY)

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| Point A: run length primary, chosen knowing the data | — | FIXED | §8.1, §9 |
| Point B: what the 2 × 2 can identify; recall enters no rule | — | FIXED (completed in this draft: §3 corrected, JOINT narrowed, testability printed) | §3, §6, §7, §8.3 |
| Point C: own ADR | — | FIXED, pending the human lead's ruling | header, §16 item 1 |
| F2 tree label misassigns causes | BLOCKING | FIXED | §6, §8.3 |
| F3 N/8 | REQUIRED | FIXED | §8.4 |
| F8 U_P / run length | REQUIRED | FIXED | §9 |
| F9 R-CONFIRM | REQUIRED | FIXED; cost ANSWERED (0.87 charged hours; confirmed by the second review) | §10 |
| F10 (d) cost | REQUIRED | FIXED | §14 |
| F11 recall records | REQUIRED | FIXED (completed in this draft: the index record's query population; the gate recomputes the recorded quantities; whitelist extractor) | §4, §7, §11 |
| F12 one ADR, two freezes | REQUIRED | FIXED | §13 |
| F15 disclosure placement | REQUIRED | FIXED | §8.1, §9 |
| F16 gates; seed-gate exemption | REQUIRED | FIXED (completed in this draft: tolerances, the v = N/256 gate read, F0 failure) | §5, §6, §11 |
| F20 bridge duplication | ADVISORY | FIXED by construction | §10 |
| F21 measurement definitions | ADVISORY | FIXED (the false sentence it shared with draft 1 is corrected) | §3, §6, §7 |
| F24 replicate accounting | ADVISORY | FIXED (completed in this draft: cell-level NOT EVALUABLE restored) | §8.2 |
| F25 tags | ADVISORY | FIXED | §0 |
| F26 retention table; "in bits" | ADVISORY | FIXED | §8.1 |
| F27 seeds | ADVISORY | FIXED: registry values cited | §5 |

### 17.2 Confirmation review (`REVIEW2_ADR-0024_ADR-0029.md`, NOT READY)

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| R-N1 index-recall gate compares two quantities | BLOCKING | FIXED: the gate recomputes each recorded quantity by its own definition; CR8 is a separate, new measurement | §4, §7, §11 gate 3 |
| R-N2 §3 overclaims | REQUIRED | FIXED; labels re-checked | §3 |
| R-N3 exactness identities in floating point | REQUIRED | FIXED: one code path; tolerance gates; bit-exact only on the platform of record where guaranteed | §6, §11 gate 4, §13 |
| R-N4 cell-level NOT EVALUABLE | REQUIRED | FIXED | §8.2, §9 item 1, §11 |
| R-N5 "the same label" | REQUIRED | FIXED: row name only; median c\*; NO GAP and MIXED-PANEL; order of §9; R-CONFIRM NOT APPLICABLE | §8.2, §9, §10 |
| R-N6 NOT IDENTIFIED / CONTENT contradiction | REQUIRED | FIXED: NOT IDENTIFIED never recommends; CONTENT has one action; the note's "none" row is not issued; put to the human lead | §1, §9, §16 item 8 |
| R-N7 departures from note §5.2 | REQUIRED | FIXED: side-by-side table | §16 item 8 |
| R-N8 JOINT row; C may be inert | REQUIRED | FIXED: claim narrowed; testability share printed; a threshold left to the human lead | §7, §8.3, §16 item 9 |
| R-N9 bridge and P10-S1's seed gate | REQUIRED | FIXED: new adapter code, identity gate | §10 |
| R-N10 loaded-cell line unnamed | ADVISORY | FIXED: R-DIAGNOSIS-LOADED, printed only | §9 |
| R-N11 memory figure | ADVISORY | FIXED | §13 |
| R-N12 sealing practice | ADVISORY | FIXED: whitelist extractor | §4 |
| R-N13 dense reference | ADVISORY | ANSWERED: why D-OQ is not a reference here | §7 |
| R-N14 PRIORS: weights or selection | ADVISORY | FIXED: printed descriptively | §8.3 |
| R-N16 CHECKPOINT-DEPENDENT likely | ADVISORY | FIXED: the rule is applied per component; left open to the human lead | §9, §16 item 2 |
| §F stale seed text | REQUIRED | FIXED | §5 |

Changed in this draft and not yet reviewed: the per-component checkpoint rule, the adapter identity gate, the gate tolerances (1e-6; 0.1% of facts at float ties), and the decision not to issue the note's last row.

`Astra review: NOT_PERFORMED`.
