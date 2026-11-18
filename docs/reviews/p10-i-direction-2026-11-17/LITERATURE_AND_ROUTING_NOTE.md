# P10-I — literature note on memory, routing and indexing (recorded 2026-11-17 UTC)

**Status: INPUT TO DRAFTING. Not a specification, not a result, not an approval.** The human lead brought this note into the workflow on 2026-11-17, after accepting P10-S1, with the instruction: "document this and take it under consideration". The note was prepared outside this workflow. This file is a condensed record of it, followed by the lead's (Claude Fable 5.2) first considerations. Nothing here authorizes a study.

**Verification status of the citations.** The papers below are known publications and the one-line descriptions match the lead's knowledge of them, but the lead has not re-read the sources for this record. Before any of them is cited in a specification, the drafter checks the claim used against the paper itself. No number from these papers is a threshold for ArborLM.

## 1. The note's claim

The literature supports three ideas separately: learning a memory and retrieving from it can be separated; sparse indexing scales, including on SSD; hard routing can collapse or leave a store under-used. It does not establish that their combination beats dense alternatives or enables SSD-backed continual learning. That combination is the open question.

## 2. Research lines cited

| Line | Reference | What it shows | Bearing on ArborLM, and its limit |
|---|---|---|---|
| Product-key memory | Lample et al., "Large Memory Layers with Product Keys", NeurIPS 2019 | Large trainable key-value memories with structured lookup | A memory layer need not be a learned tree; product-key addressing is a serious alternative baseline |
| Memory utilisation | Kim and Jung, "Large Product Key Memory for Pretrained Language Models", Findings of EMNLP 2020 | Many slots become stale or under-used; initialisation and integration matter | Better routing alone is not enough; entries must receive useful updates |
| Sparse prediction of a full computation | Liu et al., "Deja Vu: Contextual Sparsity for Efficient LLMs at Inference Time", ICML 2023 | A light predictor selects a useful subset of a larger computation | An analogy for training an accurate memory first, then a sparse router to reproduce its selections. It predicts activations at inference, not addresses during continual training |
| Retrieval trained with the model | Guu et al., "REALM: Retrieval-Augmented Language Model Pre-Training", ICML 2020 | The retrieval index is refreshed asynchronously as representations change | Index maintenance need not follow every gradient update. A precedent, not proof for a trained neural memory |
| SSD-resident retrieval | Subramanya et al., "DiskANN", NeurIPS 2019; Chen et al., "SPANN", NeurIPS 2021 | Approximate nearest-neighbour search over very large stores with limited RAM | Precedent for routing data in RAM and contents on SSD. Search recall, prediction quality and training performance are three different measurements |
| Updatable SSD index | Singh et al., "FreshDiskANN", arXiv:2105.09613, 2021 | Inserts, deletes and searches without full rebuilds | Shown for vector indexing; unproven when keys and values are trained by gradient descent |
| Routing collapse | Fedus et al., "Switch Transformers", JMLR 2022; also Rae et al., "Sparse Access Memory", NeurIPS 2016, for large sparse memories | Sparse routing is unstable and unbalanced without countermeasures | Supports the concern that a tree keeps selecting favoured branches. It does not show that this caused P10-S1's quality gap |

## 3. The decomposition the note proposes to test

1. Accurate memory learning (full retrieval during training, or periodic full passes).
2. Sparse retrieval (a trained router, or an index built over the trained memory).
3. Continual updates (update selected values, keep the index consistent, consolidate periodically).
4. SSD-backed operation (routing data in RAM, contents on SSD).

Proposed comparisons, on the same facts, capacity, panels and budgets:

| Comparison | What it isolates |
|---|---|
| The existing tree read with exact retrieval | Whether the stored representations are usable once the routing restriction is removed |
| A trained flat memory read through an index | Whether an accurate memory can be made sparse after training |
| A trained flat memory with a learned router | Whether full-search retrieval can teach routing |
| A tree trained jointly with periodic full-search supervision | Whether guidance prevents loss of representation during training |
| Fixed keys against periodically refreshed keys (and fully trainable keys) | Index maintenance against the ability to place new knowledge |

Both candidate recall and end-task quality are measured, since good neighbour recall does not guarantee good predictions. The note's 95% quality-retention figure is a proposed engineering target, not a validated threshold; it would have to be registered in advance and read against the dense and the flat baselines.

The note's recommendation: use these papers as the literature basis of the routing-quality work in ADR-0024, test the interaction with training duration in ADR-0026, and do not replace the current tree before learning whether its lower quality comes from missing the right entries, from damage done by sparse training, or from the branch-prior weighting.

## 4. The lead's considerations for the drafting

These are the lead's, not the human lead's, and are open to the review of each specification.

1. **P10-S1 already holds a first data point for "index a trained flat memory".** Its F-OQ-IVF arm reads the trained flat memory through a clustered index. At the run length its mean accuracy was 0.540 against the flat memory's 0.992 at 32K facts / 16K slots, and 0.497 against 0.654 at 8K / 1K; its saturation step was SUBPROPORTIONAL in 5 of 5 replicates (`results/p10s1-run-2026-11-17/OUTCOME.md`, `audit/AUDIT.md`). So post-hoc indexing did not preserve quality there. Two cautions: that arm used one index design at one registered candidate count, and the oracle codes are crowded by construction (nearest-neighbour cosine about 0.83 at the saturation cells). The next study should report candidate recall beside accuracy, at more than one candidate count, so that "the index missed the entry" and "the entry was found but not usable" can be told apart.
2. **The tree is already behind that index.** P10-S1 registered TREE_BEHIND against F-OQ-IVF at equal candidate count. The three explanations the note lists (missed entries, damage from sparse training, branch-prior weighting) are exactly what P10-S1 could not separate. The exact-retrieval read of the trained tree is the cheapest of the proposed comparisons, because it needs no new training.
3. **Scope of ADR-0024.** It already carries the capacity question, the untested 16,384→65,536 transition and four items from P10-S1's audit. Adding the routing decomposition risks a study with too many questions. Proposal for the drafting: a separate routing-quality lane inside ADR-0024 with its own outcome line and its own budget, so that neither line can stand in for the other; the reviewer is asked whether it should instead be its own study.
4. **Baselines.** A product-key memory arm and the dictionary baseline belong in the comparison. P10-S1 printed DICT DOMINATES ON THIS TASK; a routing result on a task that a plain lookup solves does not show value a lookup cannot provide.
5. **Measured speed is part of the picture, kept apart.** In the supplementary throughput of P10-S1 (descriptive only), the tree's read-path throughput stayed flat from 1,024 to 16,384 slots while the flat memory's and the dense adapter's fell. A design that keeps this and closes the quality gap is the point of the routing work; the two are reported separately and neither is a success claim alone.
6. **Thresholds.** Any retention target (the proposed 95%) and any recall target are fixed in the specification before observation, with the reason for the figure stated. None is taken from the literature.
7. **SSD claims stay with P10-I-S5** and its two separate verdicts. The SSD papers support the engineering precedent only.

`Astra review: NOT_PERFORMED`.

## 5. Addendum: correction to consideration 2, and the human lead's direction for the routing work (2026-11-17 UTC)

The human lead brought a second note (prepared outside this workflow) that agrees with section 4 with one correction and adds a structure for the routing work. The lead checked its figures against `results/p10s1-run-2026-11-17/audit/AUDIT.md` (branch `claude/p10-s1`); they match.

### 5.1 Correction: the tree is not behind the clustered index at every checkpoint

Consideration 2 said "the tree is already behind that index". That is true of the registered verdict, which is read at U_P, and not of the end of training. Mean a_use over five replicates and both panels, at U_P → at the run length:

| Cell | F-OQ-IVF | T-OQ | Ahead at U_P | Ahead at the run length |
|---|---|---|---|---|
| 2K/1K | 0.916 → 0.927 | 0.787 → 0.931 | index | about equal |
| 2K/4K | 0.953 → 0.960 | 0.989 → 1.000 | tree | tree |
| 8K/1K (loaded) | 0.306 → 0.497 | 0.176 → 0.416 | index | index |
| 8K/4K | 0.631 → 0.706 | 0.469 → 0.769 | index | tree |
| 8K/16K | 0.911 → 0.919 | 0.920 → 0.996 | about equal | tree |
| 32K/4K (loaded) | 0.201 → 0.270 | 0.151 → 0.323 | index | tree |
| 32K/16K | 0.483 → 0.540 | 0.401 → 0.697 | index | tree |

The two cells the human lead's note cites (8K/4K and 32K/16K) reverse between U_P and the run length. The reversal is not general: at 8K/1K the index is still ahead at the run length. Both arms stay far below the exhaustive flat read at the loaded and near-full cells. These figures are descriptive. The registered TREE_BEHIND is not changed by them, and they do not show that longer training closes the gap to the flat memory. They do show that the comparison depends on training duration, so the routing work reads more than one checkpoint.

### 5.2 Structure directed for the routing work

**Stage A — diagnosis without training.** Existing flat and tree checkpoints are frozen. Measured: candidate recall against exact search, recovered attention mass, end-task accuracy, and the effect of the branch priors. Candidate budgets 128, 256, 512, 1,024 and 2,048 where feasible; loaded cells included; more than one checkpoint (5.1).

**Stage B — intervention, only if Stage A justifies it.** Post-hoc indexing, teacher-guided routing, product-key memory and periodic index refresh, each as an individually identifiable change with a fair optimisation and cost budget.

What Stage A must separate: the router selects the wrong candidates; the memory content was poorly learned; the branch priors distort the retrieval weights. Each needs a different fix.

| Stage A result | Next action |
|---|---|
| Exact search restores the tree's quality | Improve the router and candidate coverage |
| Exact search does not restore it | Improve memory training and representation |
| Removing branch priors restores it | Redesign how routing scores enter the read |
| Post-hoc indexing approaches the flat memory | Investigate a separately trained sparse index |
| None | Consider a more fundamental change of the memory |

### 5.3 Conditions

1. A retrieval change and a training change are never mixed in one comparison. A frozen checkpoint read through another index isolates retrieval; retraining memory and router together answers a different question.
2. Quality retention is defined against a registered reference and on task performance. At 32K/16K, 95% of the flat memory's 0.992 is 0.9424, far above the 0.540 (index) and 0.697 (tree) measured. The improvement retained above the no-memory baseline is also assessed, so that a weak model cannot pass trivially.
3. The dictionary baseline is kept. Exact retrieval is not general learning: a later study has to show generalisation and updating beyond key-value lookup.

### 5.4 Scope

The frozen-checkpoint diagnosis (Stage A) is a separate lane of ADR-0024 with its own outcome line. If it shows that a substantial new training architecture is needed, that becomes a separate study and is not added to ADR-0024.

### 5.5 Asked of the independent review of ADR-0024

The reviewer (Opus 5.5) checks in particular: the U_P against run-length distinction of 5.1 and how the specification reads it; the planned candidate-recall measurements; and whether ADR-0024 can keep independent outcome lines without becoming unmanageable.

### 5.6 Standing of this addendum

The human lead's note recommends approving section 4's drafting considerations with the correction above. It is recorded as direction for the drafting. It approves no specification and no run; the agreed approval process for each specification is unchanged. The question as the note puts it: can ArborLM keep the flat memory's accuracy while using tree-like sparse retrieval, without losing its ability to keep learning?

`Astra review: NOT_PERFORMED`.
