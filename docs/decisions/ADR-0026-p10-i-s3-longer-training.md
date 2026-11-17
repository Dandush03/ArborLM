# ADR-0026 — P10-I-S3: longer training of the frozen-backbone memory and its dependence on memory

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- Date: 2026-11-17 UTC. Drafted by the lead (Claude Fable 5.2) for an independent specification review (Opus 5.5) and then the human lead's review.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Direction: `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S3) and section 5 (limits); `LITERATURE_AND_ROUTING_NOTE.md` sections 3 and 5 (duration interaction of the routing gap).
- ArborLM is unproven research. No outcome of this study is a success claim. P1 to P10 are immutable: no result, threshold, seed or outcome of any earlier study is revised, and none is reopened.

## 1. Question and outcome lines

P4 trained a 198,401-parameter hierarchical memory on a frozen 27,392-parameter backbone for 512 updates. The memory helped, the help depended on its values, and an equal-size dense adapter did better in every pair. P4 could not say whether 512 updates was the limit. The question here:

**When the same frozen-backbone memory is trained to a duration fixed by a convergence rule, (1) does its contribution still depend on what is stored at which address, and (2) is it competitive with a dense adapter of equal trainable size that is tuned as carefully?**

Two outcome lines. Each has its own thresholds. Neither substitutes for the other.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| 1. DEPENDENCE | At the primary checkpoint the memory's gain is lost when trained values are reassigned among the slots in use and when reads are addressed by the wrong query. The gain is tied to addressed content. | The memory adds predictive capacity, but most of it survives those interventions (a generic additive effect), or it adds no capacity. | A required cell is missing or failed, or a validity gate failed: NOT EVALUABLE. |
| 2. COMPETITIVENESS | At the primary checkpoint the memory is within the registered tolerance of the dense adapter, each at its own searched rate. | The dense adapter is ahead by more than the tolerance. | The deciding arm's rate sits at the edge of the searched grid, or a dense cell failed: INCONCLUSIVE or NOT EVALUABLE (section 6.4). |

A positive on line 1 with a negative on line 2 is the P4 pattern at a longer duration. It is a registered outcome, not a reason to extend training further.

## 2. Background: the registered findings this follows from

All figures below were read from the records named. Where a figure is the lead's own computation from raw records it is marked so; such figures are descriptive and change nothing in the study they come from.

| Source | Finding |
|---|---|
| `results/p4-2026-11-12/README.md`, `authorized-scientific-review.md`, `docs/decisions/ADR-0009-frozen-backbone-capacity.md` | 63 cells; each addition trained 198,401 parameters for 512 updates (`configs/p4_frozen_capacity.toml`: `steps = 512`; the 256-update snapshot was saved and never evaluated). Capacity gain C: mean 0.021988695 nats/byte, positive in 27 of 27. Value-shuffle effect P: mean 0.022221519, positive in 27 of 27. Q (dense minus memory): mean −0.006182638, negative in 27 of 27; 10 of 27 cells and 2 of 9 parent means within the −0.005 tolerance. Capacity and dependence flags passed; dense tolerance and the composite failed. |
| `results/p4-2026-11-12/per-run.csv` (recomputed by the lead for this draft) | The three counts reproduce: C > 0 in 27/27, P > 0 in 27/27, Q < 0 in 27/27. Memory gain as a share of dense gain: 0.78 of the means; 0.62 to 0.90 per cell. Across-seed SD of C within a parent: 0.0005 to 0.0027. |
| `results/p4-2026-11-12/b*-memory-*/result.json` (lead's computation) | At step 512 the memory selected 217 to 421 distinct slots of 4,096 on the panel (mean 323). Shuffled-values NLL minus frozen-baseline NLL: mean +0.00023 (range −0.0026 to +0.0045). So P4's all-slot shuffle mostly replaces trained values by untrained ones and returns the model to about the baseline. It shows that trained values matter. It does not separate "the right value at the right address" from "any trained value". Section 3.4 adds a control for that. |
| `results/p5-2026-11-13/README.md`, `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` | 512 updates again. Mean gain: flat 0.022938682, fixed tree 0.022133329, learned tree 0.021549867, dense 0.027317625. Learned tree minus flat NLL: +0.001388814, inside the 0.005 resolution. No memory variant passed the dense-reference tolerance (15, 14 and 13 of 27 cells). |
| `docs/reviews/p6-results-2026-11-13/README.md` | On the P5 checkpoints, exhaustive search under the tree's own rule changed NLL by +0.00044 (fixed) and +0.00002 (learned); removing the branch prior cost about 0.0039. At 512 updates the top-2 restriction was not what limited the tree. |
| `results/p3-lt-2026-11-12/README.md`, `docs/RESEARCH_LOG.md` (P3-LT entry) | The earlier longer-training study (joint training, 256 → 1,024 updates): dependence rose descriptively and missed its registered thresholds. Different setting (backbone trained jointly); not comparable to this study. |
| `results/p10s1-run-2026-11-17/OUTCOME.md` section 4, `audit/AUDIT.md` sections 2 and 5, `ACCEPTANCE.md` | A different task (oracle-addressed fact store). Three lessons carried here: (a) the memory arms ran at an untuned rate 0.003 against a dense control at its calibrated rate; (b) every DEPENDENCE_FAILED label came from a ratio condition read at early snapshots, which the by-construction reference R2 also failed 12 times; (c) the dense comparison changed with the yardstick (F-OQ ahead of D-OQ at matched compute in 5 of 5 at 32K/16K, DENSE AHEAD at matched updates). |
| `LITERATURE_AND_ROUTING_NOTE.md` section 5.1 | In P10-S1 the tree overtook the clustered index between U_P and the run length in several cells (8K/4K: 0.469 → 0.769 against 0.631 → 0.706). The tree-versus-alternative comparison depends on training duration. |

P10-S1's update counts are not used here. Its task, addressing and training conditions differ. Every duration in this study comes from its own rehearsal (section 5).

## 3. Design

### 3.1 Setting (unchanged from P4, read-only reuse)

- Parents: the nine frozen P3 control backbones used by P4 and P5 (B = 101, 102, 103; O = 301, 302, 303), verified by hash. They are read-only inputs, not new draws. All 27,392 backbone parameters stay frozen and bitwise unchanged.
- Additions act after block 0 and before block 1, as in ADR-0009. Existing classes are imported unmodified from `src/arborlm/` (`pilot_model.Memory`, `p4_model.DenseAdapter`, `p4_model.Backbone`). No file under `src/arborlm/`, `configs/`, `tests/`, `results/` or `experiments/` is edited. New code goes in `studies/p10i_s3/`; the new config is `configs/p10i_s3_longer_training.toml`.
- Optimizer: fresh AdamW over the addition only, betas (0.9, 0.999), eps 1e-8, weight decay 0, global-norm clip 1.0, constant rate, no schedule, batch 8 × context 64. Only the rate is searched (section 5.1).

### 3.2 Trainable arms

| Arm | What it is | Trainable parameters | Role |
|---|---|---|---|
| M-TREE | `Memory("learned_tree")`: 4,096 slots, 16 branches of 256, top-2 branches, top-8 of 512 candidates, branch log-prior | 198,401 | The P4 memory. Subject of both outcome lines. |
| M-FLAT | `Memory("flat")`: same keys, values and fusion, exhaustive top-8 of 4,096 | 198,145 | Flat reference for the routing interaction (section 6.6) and a second competitiveness sub-label. |
| D-ADAPT | `DenseAdapter`, width 3,100 | 198,401 | The dense baseline of line 2. |
| BASE | Frozen backbone, no addition | 0 | Reference loss B for every gain. Nine evaluations. |

### 3.3 Data regimes

Each trainable arm runs in both regimes. A cell is (parent, init seed); all arms of a cell share the batch stream of their regime.

| Regime | Training stream | What it isolates when compared |
|---|---|---|
| REP (repeated) | The 2,048 chunks the backbone was trained on (train ranks 0–2,047), reshuffled each epoch. At U updates the stream has been seen U/256 times. | Along REP checkpoints: duration with no new data. |
| FRESH | Chunks the backbone has never seen (train ranks ≥ 4,096), each used once. U updates consume 8U unique chunks. | FRESH against REP at the same update count: additional unique data at equal duration. |

Memory-specific learning is read inside each regime: memory against D-ADAPT on the same stream, and the controls of section 3.4. REP and FRESH also differ in whether the backbone has seen the data; the design does not separate that from the amount of unique data (open choice 5).

The 512-update point of this study differs from P4 in seeds, panel, rate selection and epoch reshuffling. It is a new measurement, not a replication of P4 or P5, and it is not compared with their numbers by any rule.

### 3.4 Controls (evaluation only; no control trains or writes a checkpoint)

| Control | Applied to | Definition | Isolates |
|---|---|---|---|
| Memory disabled | all additions | Addition bypassed. Must equal BASE bitwise on the platform of record. | Engineering identity. With a frozen backbone it is the same contrast as C, not independent evidence (ADR-0009). |
| P_all: all-slot value permutation | M-TREE, M-FLAT | One permutation of all 4,096 value rows (P4's control). | Continuity with P4. Descriptive only (section 2 explains why it is weak). |
| P_used: used-slot value reassignment | M-TREE, M-FLAT | Let S be the slots selected at least once when the checkpoint reads the panel. Values are moved along a random cyclic order of S, so every slot in S holds another trained value. Mean over 4 seeded draws. | Whether the gain needs the right trained value at the right address. |
| X: query reassignment | M-TREE, M-FLAT | Within each evaluation batch (512 positions) the normalized queries are moved along a random cyclic order of positions before the lookup; each position receives a read addressed by another position's query. Mean over 4 seeded draws. | Whether the gain needs content-specific addressing, or a context-free read would do. |
| X_dense | D-ADAPT | The adapter's input is moved across positions the same way. | Descriptive like-for-like figure for X. |
| Joint key/value permutation within branch | M-TREE | As ADR-0009. NLL must match the reference within 1e-6. | Engineering invariance. |
| Exhaustive read; prior removed | M-TREE | Same checkpoint read with all 16 branches visited; and with the branch prior off. | Retrieval alone, no training change (routing note 5.3 condition 1). |
| NEG-REF | built from each rehearsal M-TREE checkpoint | Every value row replaced by the usage-weighted mean value. The read is the same for every address by construction. | Validity reference: P_all, P_used and X must be 0 within 1e-6 and the dependence rule must return "not dependent". |

There is no arm in this natural-text setting whose dependence on memory holds by construction (P10-S1 had R2). Three safeguards replace it: line 1 is read at the primary checkpoint only; its conditions are absolute in nats, with a ratio applied only where the gain itself is positive and the mean is above the resolution; and the analysis is tested on a synthetic registry with known answers. This is flagged for the review (open choice 7).

## 4. Data, seeds, sizes, checkpoints

**Corpus.** The pinned WikiText-2 acquisition of ADR-0004, byte tokenizer and chunk recipe of ADR-0005. No download, no test split. The recorded pool (`results/p4-2026-11-12/*/dataset_manifest.json`): 156,611 eligible unique train chunks and 16,407 eligible validation chunks.

**FRESH pool.** Train ranks 4,096 to 156,610: 152,515 chunks. A run of U updates needs 8U. 16,384 updates need 131,072 chunks. **The pool supports at most 19,064 fresh updates.** This is a design ceiling of the study (section 7) and it bounds the convergence rule (section 5.2).

**Panels.** Validation ranks 0 to 4,095 are used by earlier panels (P1 0–511, P2 512–1,023, P3 1,024–1,535, P4 1,536–2,047, P5 2,048–2,559, P7-B 2,560–3,071, P8 3,072–4,095). P10-S2 drew 144 windows from WikiText-2 validation on its own grid (`configs/p10s2_transfer.toml`). Rule: the registered panel is the first 512 eligible validation chunks at rank ≥ 8,192 that share no byte with any text evaluated in an earlier study; the calibration panel is the next 512 under the same rule. An inventory (`arbor-clerk`) and an independent reconstruction (`arbor-auditor`) prove both unused before the freeze. The count is met by walking further down the ranking, not by relaxing the rule. Each evaluation covers 32,768 targets, as in P4.

**Seeds.** New namespaces. The lead checked them against `configs/*.toml`: P1–P5 use 42–44, 101–103, 201–203, 301–303, 401–403, 501–503; P8 601–602 and 91xxx; P9 17xx, 18xx and 179xxx; P10-S0 200001–209999 with inits 20xx; P10-S1 210001–219999 with inits 21xx; P10-S2 220001–229999. Sibling drafts seen at drafting time: ADR-0023 uses inits 3001, 3002 and 3091; ADR-0027 proposes 270001–279999 and 2701–2799; ADR-0028 proposes 280001–289999. None overlaps the ranges below. ADR-0024 and ADR-0025 were not available; a gate at the freeze asserts disjointness from every earlier and sibling study.

| Use | Seeds |
|---|---|
| Registered init seeds (three per parent) | 2601, 2602, 2603 |
| Calibration init seed | 2691 |
| Dry-rehearsal init seed | 2692 |
| Registered streams and permutations | 260001–268999. Cell index i = 9(B−101) + 3(O−301) + (s−2601). REP stream 260001+i; FRESH stream 260101+i; P_all 260201+i; P_used 260301+10i+j; X 260601+10i+j (j = 0..3). |
| Calibration and rehearsal streams and permutations | 269001–269999, same offsets |
| Tests | 926001–926999 |

**Cells.** 9 parents × 3 init seeds = 27 cells per arm and regime. The 27 cells share nine parents and one corpus; they are not 27 independent replications, and no p-value is computed.

**Checkpoints.** Saved and evaluated at 0, 512, 2,048, 8,192 and U\* updates. U\* is the one primary checkpoint; it is fixed by the rehearsal (section 5.2) and frozen before any registered seed is observed. The checkpoints before U\* are descriptive. No rule of sections 6.2 to 6.5 reads them, and none may replace U\*.

## 5. Rehearsal: rate search and convergence

The rehearsal uses calibration draws only: init seed 2691, calibration streams, the calibration panel, and three parents (B101/O301, B102/O302, B103/O303). No registered seed and no registered-panel evaluation is touched. Every threshold in section 6 is fixed at Decision 1, before the rehearsal.

### 5.1 Rate search (the same for every trainable arm)

P10-S1 compared untuned memory arms with a calibrated dense control. Here M-TREE, M-FLAT and D-ADAPT get the same search, in each regime, at each duration.

- Grid: 0.0003, 0.001, 0.003, 0.01, 0.03 (half-decade steps around P4's 0.003). One run per (arm, regime, rate, calibration cell) to U_cal = 16,384, with the checkpoints of section 4.
- Because the rate is constant and there is no schedule, the checkpoint at c updates of a longer run is exactly a c-update run. One run therefore serves every duration.
- Selected rate r(arm, regime, c) for each c in {512, 2,048, 8,192, 16,384}: the rate with the lowest mean calibration-panel NLL at c over the three calibration cells. A rate with a non-finite loss in any calibration cell is excluded. If two rates are within 0.0005 nats/byte, the smaller rate is taken.
- Edge rule (design ceiling with a written extension): if a selected rate is the lowest or highest of the grid, the grid is extended by one half-decade step on that side and the search repeated, at most twice per side. A rate still at the edge is used and tagged RATE-AT-EDGE.
- Output: the rate table, 3 arms × 2 regimes × 4 durations. It is frozen at Decision 2.

### 5.2 Convergence rule and the primary checkpoint

Let M(arm, regime, c) be the mean calibration-panel NLL at c updates of the runs at rate r(arm, regime, 16,384). Let δ(arm, regime) = M(8,192) − M(16,384), the improvement over the last doubling. ε = 0.001 nats/byte.

1. An arm is CONVERGED in a regime if δ < ε. A loss that rises counts as converged (δ < 0).
2. **If all three arms are CONVERGED in both regimes, U\* = 16,384.**
3. If any arm is not, U\* is not fixed by the lead. The rehearsal adds one probe: REP only, the three arms at their selected rates, to 32,768 updates, to show whether one more doubling would satisfy rule 1. The lead then stops at the gate. The human lead chooses among: (a) run at U\* = 16,384 with the tag NOT CONVERGED on the affected arms; (b) approve a larger pinned corpus so that FRESH can reach 32,768 (a separate data decision; nothing is downloaded under this ADR); (c) not run. The choice uses rehearsal figures only.
4. U\* is never below 16,384 and never differs between regimes or arms.

Reason for ε: it is one fifth of the 0.005 resolution on which every line is read. An arm that gains less than 0.001 per doubling, at a non-increasing pace, would move by less than 0.002 over two further doublings (four times the training), less than half of any deciding margin.

The registered run recomputes δ on its own cells at U\* and prints CONVERGED or NOT CONVERGED per arm and regime as a tag. The tag changes no label except as stated in section 6.4. If the REP loss of an arm at U\* is more than 0.005 above its lowest descriptive checkpoint, the tag PAST BEST CHECKPOINT is printed; no checkpoint is selected because of it.

### 5.3 What else the rehearsal does

- Measures seconds per update and per evaluation for each arm, alone and with k parallel single-thread workers, under ordinary machine load, and the checkpoint storage. These replace the estimates of section 9.
- Runs NEG-REF through every dependence statistic and through the rule of section 6.2.
- Prints every statistic of section 6 for the calibration cells at every checkpoint, for information. A condition may be withdrawn before Decision 2 only if NEG-REF or the synthetic registry shows it is defective, and only by the human lead. It is never withdrawn because a memory arm fails it.
- Runs every registered stage end to end against the frozen plan itself in a DRY profile (section 11).

## 6. Rules that turn measurements into labels

### 6.1 Quantities

All losses are mean next-byte NLL in nats/byte on the registered panel, at U\*, per cell (parent p, seed s), per regime. Each arm is read from its run at the frozen rate for the duration in question.

| Symbol | Definition (positive direction) |
|---|---|
| C | B − H: baseline minus memory (memory helps) |
| C_dense | B − A: baseline minus dense adapter |
| P_used | H_used − H: loss rise under used-slot value reassignment |
| X | H_x − H: loss rise under query reassignment |
| Q | A − H: dense minus memory (memory ahead) |

Counting rule used throughout: "22 of 27 cells" and "8 of 9 parents", where a parent's value is the mean over its three seeds. These are P4's counts. 22 of 27 allows five exceptions; 8 of 9 stops a few favourable backbones from carrying a pooled mean. They are kept so that the yardstick does not change with duration. 0.005 nats/byte is the resolution used since ADR-0006; it is 2 to 10 times the across-seed SD of C within a parent in P4 (section 2).

### 6.2 Line 1 — DEPENDENCE (arm M-TREE; read per regime)

| Condition | Rule |
|---|---|
| D1 capacity | mean C ≥ 0.005; C > 0 in ≥ 22/27 cells; parent mean C > 0 in ≥ 8/9 |
| D2 stored association | mean P_used ≥ 0.005; (C > 0 and P_used ≥ 0.5·C) in ≥ 22/27 cells; parent mean P_used > 0 in ≥ 8/9 |
| D3 addressing | mean X ≥ 0.005; (C > 0 and X ≥ 0.5·C) in ≥ 22/27 cells; parent mean X > 0 in ≥ 8/9 |

A cell whose used-slot set S has fewer than two slots fails D2 and is listed as COLLAPSED.

Reason for 0.5: "dependent" is taken to mean that the larger part of the gain is lost when the association or the address is broken. Below one half, most of the gain survives the intervention and is better described as a generic additive effect. The figure is a design choice (open choice 3).

| Regime label | Rule |
|---|---|
| DEPENDENT | D1 and D2 and D3 |
| CAPACITY WITHOUT DEMONSTRATED DEPENDENCE | D1, and not (D2 and D3); the failing conditions are named |
| NO CAPACITY | not D1 |

### 6.3 Line 2 — COMPETITIVENESS (memory against D-ADAPT; read per regime)

| Condition | Rule |
|---|---|
| K1 absolute tolerance | mean Q ≥ −0.005; Q ≥ −0.005 in ≥ 22/27 cells; parent mean Q ≥ −0.005 in ≥ 8/9 |
| K2 share of the dense gain | mean C ≥ 0.90 × mean C_dense, and mean C_dense ≥ 0.005 |
| K3 ahead (sub-label only) | mean Q ≥ +0.005; Q > 0 in ≥ 22/27 cells; parent mean Q > 0 in ≥ 8/9 |

| Regime label | Rule |
|---|---|
| MEMORY AHEAD | K3 |
| COMPETITIVE | K1 and K2, not K3 |
| NOT COMPETITIVE | not (K1 and K2) |

Reasons. K1 is P4's tolerance, unchanged: a memory inside the resolution of the dense adapter is not distinguishable from it in this study. K1 alone is too easy when both gains are small and hard to interpret when both are large, so K2 adds a proportional condition. 0.90 is the proportion this programme already uses for "close to a reference" (P10-S0: 0.90 of the oracle reference's accuracy). It is not met by P4's 512-update figures (0.78), so it is not fitted to pass. If mean C_dense < 0.005 the dense adapter itself adds nothing measurable and the regime is NOT EVALUABLE for line 2.

The line is computed twice, with separate labels that are never merged: COMPETITIVENESS[TREE] for M-TREE (the headline, since M-TREE is the P4 memory) and COMPETITIVENESS[FLAT] for M-FLAT. The better of the two is not selected.

### 6.4 Tags that qualify a label

| Situation | Effect |
|---|---|
| The memory arm's rate for U\* is RATE-AT-EDGE and the label is NOT COMPETITIVE | INCONCLUSIVE (MEMORY RATE AT EDGE) |
| D-ADAPT's rate for U\* is RATE-AT-EDGE and the label is COMPETITIVE or MEMORY AHEAD | INCONCLUSIVE (DENSE RATE AT EDGE) |
| The losing arm is NOT CONVERGED at U\* | Label kept; printed with "(MEMORY STILL IMPROVING)" or "(DENSE STILL IMPROVING)" |
| A REP arm is PAST BEST CHECKPOINT | Label kept; tag printed |

### 6.5 Combining the two regimes

Each line reports both regime labels. The line's registered label follows from the pair by this table; "positive" is DEPENDENT for line 1 and COMPETITIVE or MEMORY AHEAD for line 2.

| FRESH | REP | Registered label of the line |
|---|---|---|
| positive | positive | positive, BOTH REGIMES |
| positive | not positive | positive, FRESH ONLY |
| not positive | positive | positive, REPEATED DATA ONLY |
| not positive | not positive | the FRESH label, with the REP label beside it |
| either regime NOT EVALUABLE or INCONCLUSIVE | — | each regime is printed as it is; the line carries no combined label |

"REPEATED DATA ONLY" is weaker evidence than "FRESH ONLY": the repeated stream is the data the backbone was fitted to, and at long duration both additions can fit it. The report says so wherever that label appears.

### 6.6 Routing and training duration (descriptive, with a fixed reading rule)

The P4 setting has a tree with a sparse read, so the interaction the human lead asked for is measured here. At each checkpoint c in {512, 2,048, 8,192, U\*} and in each regime, per cell:

| Quantity | Definition | Isolates |
|---|---|---|
| G_train(c) | H(M-TREE) − H(M-FLAT), each from its run at its rate for c | Tree against a separately trained flat memory: training and retrieval together |
| G_read(c) | H(M-TREE) − H(M-TREE read exhaustively), same checkpoint | The top-2 restriction alone |
| G_prior(c) | H(M-TREE, prior off) − H(M-TREE), same checkpoint | The branch prior alone |

Reading rule for G_train at each c: TREE BEHIND if mean ≥ +0.005 and G_train > 0 in ≥ 22/27 cells; TREE AHEAD if mean ≤ −0.005 and G_train < 0 in ≥ 22/27; otherwise WITHIN RESOLUTION. The same rule is applied to G_read (RESTRICTION COSTS / WITHIN RESOLUTION / RESTRICTION HELPS). Trend: "GAP CHANGES WITH DURATION" if the label at 512 differs from the label at U\*, otherwise "NO CHANGE AT THIS RESOLUTION". Distinct selected slots and branch-use entropy are printed beside each figure.

**This section is descriptive and is not a third outcome line.** Reasons: (1) the routing-quality outcome line belongs to ADR-0024, and a second registered routing line on a different task could be read as standing in for it; (2) in P5 the tree-versus-flat difference at 512 updates was 0.0014, inside the resolution, so a registered label here would mostly certify "within resolution"; (3) the interaction is a statement about several checkpoints, and the direction makes every checkpoint before U\* descriptive. The reading rule is still written here in full, and the code that prints it is tested like the registered rules (section 11), because P10-S1's descriptive sections were where its report went wrong. The alternative is open choice 6.

### 6.7 Other descriptive output

The full table of every quantity at every checkpoint for every arm and regime, by per-duration rate and along the primary-rate run; the 2 × 2 of (512 against U\*) × (REP against FRESH) for C, C_dense and Q; M-FLAT's D1–D3; P_all; X_dense; the P4-rate anchor (below); means, SDs, ranges, sign counts, per-parent and per-seed values. No best seed, cell or checkpoint is selected.

**P4-rate anchor.** If the frozen REP rate of M-TREE or of D-ADAPT for U\* is not 0.003, that arm is also run in REP at 0.003 to U\*. It shows how much of any change from the 512-update picture comes from rate selection and how much from duration. Descriptive only.

## 7. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Hour caps: rehearsal 14 h, registered run 36 h, charged time | Resource cap | May be extended by the human lead on cost projections only, never on outcome values. A stage that reaches a cap is PAUSED and resumed; every planned cell still runs. |
| RSS guard 2 GiB per worker, 24 GiB aggregate | Resource cap | Same. |
| U\* and the update ladder | Design ceiling | Fixed by section 5.2. Extended only by its rule 3. |
| FRESH pool: 152,515 chunks, at most 19,064 fresh updates | Design ceiling | Extended only by a separately approved corpus (rule 3 b). No chunk is reused in FRESH. |
| Rate grid: five rates | Design ceiling | Extended by the edge rule of section 5.1, at most two steps per side. |
| Calibration: three parents, one seed | Design ceiling | Not extended. |
| Panel: 512 chunks | Design ceiling | Met by walking down the ranking (section 4). |
| Permutation draws: 4 per control | Design ceiling | Not extended. |
| 0.005 nats/byte; 22/27; 8/9; 0.5·C; −0.005; 0.90; ε = 0.001 | Scientific threshold | Fixed at Decision 1. Never relaxed after observation. |

No limit is extended because a partial result looks close.

## 8. Stages and machine load

Training and evaluation are deterministic CPU float32 with one thread per worker. Their results do not depend on machine load. **No wall-time comparison is registered in this study**, so no stage needs a quiet machine for validity.

| Stage | Content | Load condition | If not met |
|---|---|---|---|
| R1 rehearsal: rate search and convergence | 90 calibration runs, more if the grid is extended | None | — |
| R2 rehearsal: cost measurement | Seconds per update and per evaluation, 1 and k workers | Ordinary load, on purpose; the 1-minute load average is recorded | Projection flagged LOADED if the load average exceeds 4; it is still used, being the conservative figure |
| R3 rehearsal: DRY run of every registered stage on the frozen plan | Minutes | None | — |
| G gates | Hashes of parents, data, code, plan; panels proved unused; seed disjointness; disabled = BASE bitwise on all nine parents; NEG-REF; synthetic-registry test | None | A failed gate stops the run before any training |
| T training | All registered runs, resumable per cell | None | — |
| E evaluation | All checkpoints and controls, resumable per task | None | — |
| A analysis and report | Once, from the frozen code | None | — |

Seconds per update are reported with the load average at the start of each stage. They are descriptive records of this implementation on this machine. They are not an efficiency result, and logical work counts are not reported as measured efficiency anywhere.

## 9. Cost projection (an estimate; the rehearsal replaces it)

Measured inputs, from `training_seconds_including_logs_and_saves` in each cell's `result.json` (lead's computation; Apple M5 Max, one thread, cells run one at a time):

| Arm | Seconds per 512 updates (mean of 27) | ms per update | Source |
|---|---|---|---|
| Learned tree | 14.118 (P4), 14.067 (P5) | 27.6 | `results/p4-2026-11-12/`, `results/p5-2026-11-13/` |
| Flat | 3.062 | 6.0 | `results/p5-2026-11-13/` |
| Dense adapter | 4.261 (P4), 4.254 (P5) | 8.3 | both |

One evaluation of 32,768 targets cost about 0.5 s in P4 (memory cells: 17.686 s supervised wall minus 14.118 s training, for six evaluations and start-up). Scale reference from P10: P10-S0 charged 6.09 h of a 22-hour cap, with stages at 0.40–0.63 of projections rehearsed under load (`results/p10s0-run-2026-11-16/OUTCOME.md`); P10-S1 charged 25.39 h over two attempts of a 53-hour cap (`results/p10s1-run-2026-11-17/OUTCOME.md`).

Per run to 16,384 updates: M-TREE about 452 s, M-FLAT 98 s, D-ADAPT 136 s.

| Block | Runs | Single-thread compute |
|---|---|---|
| Rehearsal R1: 3 arms × 2 regimes × 5 rates × 3 cells to 16,384 | 90 | 5.7 h (up to about 8 h with grid extensions) |
| Rehearsal: convergence probe (only under rule 3), R2, R3 | ≤ 9 + small | ≤ 1.5 h |
| Registered primary: 3 arms × 2 regimes × 27 cells to U\* = 16,384 | 162 | 10.3 h |
| Registered per-duration runs, where the rate for 512, 2,048 or 8,192 differs from the rate for U\* | 0 to 486 short runs | 0 to 6.8 h |
| P4-rate anchor (REP; M-TREE and D-ADAPT; only if their rate is not 0.003) | 0 to 54 | 0 to 4.4 h |
| Evaluation: 5 checkpoints; about 15 evaluations per M-TREE checkpoint, 11 per M-FLAT, 2 per D-ADAPT | — | about 2 h |
| **Registered total** | 162 to 702 | **about 12 h to 23.5 h** |

Order of magnitude for the whole study: 20 to 35 hours of single-thread compute. Parallel workers shorten wall time; the rehearsal measures by how much. Checkpoint storage is of the order of a few GB (about 2.4 MB per snapshot with optimizer state, a few thousand snapshots at most; an estimate from the parameter count, not a measured figure). The proposed caps (14 h and 36 h) are the worst-case rows plus about half again. If the rehearsal projects more than a cap, the lead returns to the human lead before Decision 2 with the projection; the matrix is not cut.

The rehearsal measures: seconds per update per arm at each rate and in each regime; seconds per evaluation including the exhaustive read; the parallel slowdown; storage per snapshot; the number of distinct rates in the rate table, which fixes the per-duration and anchor rows.

## 10. Stop rules and NOT EVALUABLE

| Event | Consequence |
|---|---|
| A gate fails before training | Engineering stop. No registered cell is observed. A fix needs a re-freeze and the human lead's approval of a new attempt. |
| A stage reaches a resource cap | PAUSED. Resumed after an extension decided on projections only. Completed cells are not recomputed. |
| A registered run of a memory arm has a non-finite loss | The cell is kept as failed and counts as failing every condition of its arm. Nothing is rerun at another rate. |
| A registered D-ADAPT run for U\* has a non-finite loss | Line 2 is NOT EVALUABLE in that regime. |
| Any other required cell or evaluation is missing after the run ends | The lines that need it are NOT EVALUABLE in that regime. Denominators are never reduced. |
| Disabled ≠ BASE, replay ≠ reference, or joint permutation outside 1e-6 on any cell | Integrity failure; the affected arm and regime is NOT EVALUABLE. |
| mean C_dense < 0.005 | Line 2 is NOT EVALUABLE in that regime (section 6.3). |
| Convergence fails in the rehearsal | Section 5.2 rule 3: stop at the gate; the human lead decides. |

The registered run happens once. A negative or inconclusive label is a registered outcome. It is not a reason to add updates, seeds, rates or cells.

## 11. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| P10-S1 attempt 1 was lost to a commit of a status note into a frozen input (ADR-0021 sections 25.19–25.20) | The frozen-input set is exactly: this ADR at its freeze hash, `configs/p10i_s3_longer_training.toml`, `studies/p10i_s3/`, the imported `src/arborlm/` modules, `uv.lock`, the nine parent checkpoint hashes, the data hashes, the panel identities, the rate table and `plan.json`. No commit is made in the frozen worktree while a registered stage runs. Status goes to chat or to `NOTES.md` in the run directory under `experiments/`, which is git-ignored and outside the set. Every stage is resumable per cell or task. |
| P10-S1's throughput stage asked for a cell the frozen plan did not run (section 25.21) | Every registered stage reads its item list from `plan.json` only, and stage R3 runs each of them end to end on the frozen plan before Decision 2. Tests use that plan, not a separate one. |
| P10-S1's audit: an unstated aggregation rule, a dependence condition that misfires early, a descriptive section that compared the wrong reads | Every combination rule is in section 6 (cells, parents, regimes, arms). Line 1 is read at U\* only. NEG-REF passes through every dependence statistic in rehearsal. The analysis, including sections 6.6 and 6.7, is tested on a synthetic registry with known answers: one case per label, per tag and per row of the regime table, and a case where two arms' reads are swapped and the test must fail. |
| P10-S2 stopped on a count gate although quality criteria were met | Counts that are not claims are met by rule: the panels by walking the ranking, the rate grid by the edge rule. |
| P10-S0 tested one load and one training length | Duration comes from a convergence rule, and four checkpoints are reported. |
| A test passed on macOS and failed on Linux (section 25.23) | Platform of record: macOS arm64, Apple M5 Max, Python and PyTorch as in `uv.lock`. Bitwise assertions are made on it only; elsewhere the same checks use a 1e-6 tolerance. |
| GitHub CI is costly | `uv run --locked ruff check .`, `mypy` and `pytest` run locally. No CI run is required by this study. `uv.lock` and `pyproject.toml` do not change. |

Roles: `arbor-implementer` writes the code; `arbor-auditor` audits it in a separate context from code and records, not from the lead's conclusions, and recomputes the outcome from raw records; `arbor-clerk` inventories panels and hashes. The model that ran each task is recorded from session metadata.

## 12. What the study cannot establish, and what it means for P10-I-S4

It cannot establish:

- Anything about hierarchy as such, external scaling, SSD behaviour, active computation or cost. The store is 4,096 slots, all resident.
- Semantic storage. Dependence on addressed content is not knowledge of facts.
- A general result. One 27,392-parameter backbone family, one corpus, byte-level text, one addition size, nine correlated parents.
- That freezing is better or worse than joint training, or that any P4 or P5 number was wrong. Those studies stand as recorded.
- A fully tuned comparison. One hyperparameter is searched, on three parents shared with the registered run, with a constant rate.
- A separation of "more unique data" from "data unseen by the backbone" (section 3.3).
- Equal compute. The arms are matched on trainable parameters and updates. In the P4 records an M-TREE update took about 3.3 times a dense update in wall time (section 9); that is a descriptive record, and line 2 says nothing about it.

**For P10-I-S4's entry criterion** (DIRECTION.md: "credible evidence from P10-I-S3 or P10-S1 that memory is competitive enough"; the draft ADR-0027 states its Route A as both lines of this study positive at the primary checkpoint):

| Line 2 result | What it would mean | What it would not mean |
|---|---|---|
| COMPETITIVE or MEMORY AHEAD in FRESH, CONVERGED, no edge tag | Evidence the human lead may weigh for S4 entry: at matched trainable size and matched updates, with both sides rate-searched, the memory is within tolerance on this task. | Not a cost result. S4's primary comparison is at matched training computation, where the per-update cost counts against the memory. Not evidence at any larger store or model. Not an entry decision; that is the human lead's. |
| Positive, REPEATED DATA ONLY | Weak evidence; the report states it should not by itself support S4 entry. | Not competitiveness on new data. |
| NOT COMPETITIVE, CONVERGED | S3 supplies no entry evidence. The P4 pattern holds at long duration in this setting. | Not a statement about larger stores, where a dense alternative must grow with the store, and not a revision of P10-S1, which remains the other route the direction names (its registered label is DENSE AHEAD; the matched-compute observation at 32K/16K is an audit disclosure). |
| NOT COMPETITIVE with "(MEMORY STILL IMPROVING)", or INCONCLUSIVE | No entry evidence, and no evidence against. | Not a reason to extend this study. |

COMPETITIVENESS[FLAT] is shown beside the headline in every case. A flat memory that is competitive where the tree is not points to the routing work of ADR-0024, not to S4. Which of this study's labels satisfy ADR-0027's Route A is fixed in ADR-0027, by name, before any S3 outcome exists.

## 13. Open choices reserved for the human lead

1. **Convergence rule** (section 5.2): ε = 0.001 per doubling, read on the last doubling, all arms and both regimes; failure stops at the gate. Recommendation: as drafted.
2. **Rate fairness** (section 5.1): one grid and one selection rule for all three arms, per regime and duration, on three calibration parents. Recommendation: as drafted. Alternative: all nine parents in calibration (three times the rehearsal cost).
3. **Dependence thresholds** (section 6.2): 0.005 absolute and one half of the gain, on used-slot reassignment and on query reassignment. Recommendation: as drafted. The one-half figure is the least grounded number in this draft; the reviewer is asked to challenge it.
4. **Competitiveness thresholds** (section 6.3): P4's −0.005 tolerance and a 0.90 share of the dense gain, both required. Recommendation: both. Alternative: K1 alone, which keeps P4's rule exactly.
5. **A third regime**: 2,048 chunks unseen by the backbone, repeated, to separate "unseen" from "more unique data". Cost: about half again of the registered run. Recommendation: not in this study; the limit is stated.
6. **Routing interaction** (section 6.6): descriptive with a fixed reading rule, or a registered third line read at U\* only. Recommendation: descriptive.
7. **No by-construction positive reference** (section 3.4). Recommendation: accept the three safeguards and NEG-REF. Alternative: build a synthetic keyed-recall reference on the same backbones, at added implementation cost.
8. **REP order**: reshuffled each epoch with this study's seeds, or P4's fixed order cycled. Recommendation: reshuffled; a fixed order repeated 64 times is a periodic stream.
9. **Schedule**: constant rate (one change from P4: duration) or a decaying schedule. Recommendation: constant; it also lets one run serve every duration.
10. **Corpus ceiling**: if convergence fails at 16,384, FRESH cannot go further on WikiText-2. Recommendation: decide only if rule 3 fires.
11. **Caps**: 14 h rehearsal, 36 h registered run, 24 GiB aggregate RSS. Recommendation: as drafted, replaced by the rehearsal's projection at Decision 2.
12. **P4-rate anchor** (section 6.7): up to 4.4 h. Recommendation: keep; without it, rate selection and duration cannot be told apart in the 512-update comparison.

## 14. Decisions and approval record

- Decision 1 (human lead): approve this specification for implementation and rehearsal only. **Not given.**
- Decision 2 (human lead): after the rehearsal, with U\*, the rate table, the cost projection and the freeze record, approve the single registered run. **Not given.**

No independent specification review has been performed on this draft yet. No approval is recorded. `Astra review: NOT_PERFORMED`.
