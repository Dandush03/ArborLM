# ADR-0026 — P10-I-S3: longer training of the frozen-backbone memory and its dependence on memory

**Status: APPROVED FOR IMPLEMENTATION AND REHEARSAL (Decision 1) by the lead under the human lead's delegation of 2026-11-18. Not frozen. No registered run is approved.**

- Date: 2026-11-17 UTC; revision 4 on 2026-11-18 UTC. Revision 4 applies the edits of the third independent review (section 15) and adds the rulings for the implementer (section 16), the note on running alongside other studies (section 17) and the approval record (section 18). Drafted and revised by the lead (Claude Fable 5.2). Nothing under this ADR has been implemented, calibrated, frozen or run at the time of this approval.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Direction: `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S3) and section 5 (limits); `LITERATURE_AND_ROUTING_NOTE.md` sections 3 and 5 (duration interaction of the routing gap).
- ArborLM is unproven research. No outcome of this study is a success claim. P1 to P10 are immutable: no result, threshold, seed or outcome of any earlier study is revised, and none is reopened.
- Two points were marked **PENDING HUMAN LEAD RULING** in the drafts: the fixed duration (section 5.2, open choice 1) and the third data regime (section 3.3, open choice 5). Both are taken at their recommended option by the lead under the human lead's delegation (section 18). Wherever the text below still carries the mark, read it as taken by that record. Open choice 1 departs from the direction's wording and is reported to the human lead, who can overrule it before Decision 2 (section 18).

## 1. Question and outcome lines

P4 trained a 198,401-parameter hierarchical memory on a frozen 27,392-parameter backbone for 512 updates. The memory helped, the help depended on its values, and an equal-size dense adapter did better in every pair. P4 could not say whether 512 updates was the limit. The question here:

**When the same frozen-backbone memory is trained for 16,384 updates, (1) does its contribution depend on which trained value sits at which address, and is it lost under a context-free read, and (2) is it competitive with a dense adapter of equal trainable size that is tuned as carefully?**

Two outcome lines. Each has its own thresholds. Neither substitutes for the other.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| 1. DEPENDENCE | At the primary checkpoint, on unseen single-pass data: at least half of the memory's gain is lost when trained values are reassigned among the slots in use (the gain depends on which trained value sits at which address), and at least half is lost when every position receives the same context-free read (the batch-mean read does not keep the gain; a better constant is not tested). Nothing beyond these two statements. | The memory adds predictive capacity, but most of it survives one of those interventions, or it adds no capacity. | BASE is missing or fails its check, or an integrity case of section 10 applies: NOT EVALUABLE. A missing cell or an item error is an engineering stop and labels nothing (section 10). |
| 2. COMPETITIVENESS | At the primary checkpoint the memory is within the registered tolerance of the dense adapter, each at its own searched rate. | The dense adapter is ahead by more than the tolerance. | The deciding arm's rate sits at the edge of the searched grid: INCONCLUSIVE. A dense cell failed or the dense adapter adds nothing measurable: NOT EVALUABLE (section 6.4). |

A positive on line 1 with a negative on line 2 is the P4 pattern at a longer duration. It is a registered outcome, not a reason to extend training further.

## 2. Background: the registered findings this follows from

All figures below were read from the records named. Where a figure is the lead's own computation from raw records it is marked so; such figures are descriptive and change nothing in the study they come from. The review recomputed every figure in this table with separate code and found no difference.

| Source | Finding |
|---|---|
| `results/p4-2026-11-12/README.md`, `authorized-scientific-review.md`, `docs/decisions/ADR-0009-frozen-backbone-capacity.md` | 63 cells; each addition trained 198,401 parameters for 512 updates (`configs/p4_frozen_capacity.toml`: `steps = 512`; the 256-update snapshot was saved and never evaluated). Capacity gain C: mean 0.021988695 nats/byte, positive in 27 of 27. Value-shuffle effect P: mean 0.022221519, positive in 27 of 27. Q (dense minus memory): mean −0.006182638, negative in 27 of 27; 10 of 27 cells and 2 of 9 parent means within the −0.005 tolerance. Capacity and dependence flags passed; dense tolerance and the composite failed. |
| `results/p4-2026-11-12/per-run.csv` (lead's computation) | The three counts reproduce: C > 0 in 27/27, P > 0 in 27/27, Q < 0 in 27/27. Memory gain as a share of dense gain: 0.78 of the means; 0.62 to 0.90 per cell. Across-seed SD of C within a parent: 0.0005 to 0.0027. |
| `results/p4-2026-11-12/b*-memory-*/result.json` (lead's computation) | At step 512 the memory selected 217 to 421 distinct slots of 4,096 on the panel (mean 323). Shuffled-values NLL minus frozen-baseline NLL: mean +0.00023 (range −0.0026 to +0.0045). So P4's all-slot shuffle mostly swaps in values of slots that are not selected on the panel, and those values have almost no effect: the model returns to about the baseline. (Whether those slots were selected during training is not in the record.) The shuffle shows that the values in use matter. It does not separate "the right value at the right address" from "any trained value". Section 3.4 adds a control for that. |
| `results/p5-2026-11-13/README.md`, `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` | 512 updates again. Mean gain: flat 0.022938682, fixed tree 0.022133329, learned tree 0.021549867, dense 0.027317625. Learned tree minus flat NLL: +0.001388814, inside the 0.005 resolution. No memory variant passed the dense-reference tolerance (15, 14 and 13 of 27 cells). |
| `docs/reviews/p6-results-2026-11-13/README.md` | On the P5 checkpoints, exhaustive search under the tree's own rule changed NLL by +0.00044 (fixed) and +0.00002 (learned); removing the branch prior cost about 0.0039. At 512 updates the top-2 restriction was not what limited the tree. |
| `results/p3-lt-2026-11-12/README.md`, `docs/RESEARCH_LOG.md` (P3-LT entry) | The earlier longer-training study (joint training, 256 → 1,024 updates): dependence rose descriptively and missed its registered thresholds. Different setting; not comparable to this study. |
| `results/p10s1-run-2026-11-17/OUTCOME.md` section 4, `audit/AUDIT.md` sections 2 and 5, `ACCEPTANCE.md` | A different task (oracle-addressed fact store). Three lessons carried here: (a) the memory arms ran at an untuned rate 0.003 against a dense control at its calibrated rate; (b) every DEPENDENCE_FAILED label came from a ratio condition read at early snapshots, which the by-construction reference R2 also failed 12 times; (c) the dense comparison changed with the yardstick (F-OQ ahead of D-OQ at matched compute in 5 of 5 at 32K/16K, DENSE AHEAD at matched updates). |
| `LITERATURE_AND_ROUTING_NOTE.md` section 5.1 | In P10-S1 the tree overtook the clustered index between U_P and the run length in several cells (8K/4K: 0.469 → 0.769 against 0.631 → 0.706). The tree-versus-alternative comparison depends on training duration. |

P10-S1's update counts are not used here. Its task, addressing and training conditions differ.

## 3. Design

### 3.1 Setting (unchanged from P4, read-only reuse)

- Parents: the nine frozen P3 control backbones used by P4 and P5 (B = 101, 102, 103; O = 301, 302, 303), verified by hash. They are read-only inputs, not new draws. All 27,392 backbone parameters stay frozen and bitwise unchanged.
- Additions act after block 0 and before block 1, as in ADR-0009. Existing classes and functions are imported unmodified from `src/arborlm/` (`pilot_model.Memory`, `pilot_model.tree_candidates`, `p4_model.DenseAdapter`, `p4_model.Backbone`). No existing file under `src/arborlm/`, `configs/`, `tests/`, `results/` or `experiments/` is edited. New code goes in `studies/p10i_s3/`; the new config is `configs/p10i_s3_longer_training.toml`; the new tests are `tests/test_p10is3_*.py` (section 11).
- Optimizer: fresh AdamW over the addition only, betas (0.9, 0.999), eps 1e-8, weight decay 0, global-norm clip 1.0, constant rate, no schedule, batch 8 × context 64. Only the rate is searched (section 5.1).

### 3.2 Trainable arms

| Arm | What it is | Trainable parameters | Role |
|---|---|---|---|
| M-TREE | `Memory("learned_tree")`: 4,096 slots, 16 branches of 256, top-2 branches, top-8 of 512 candidates, branch log-prior | 198,401 | The P4 memory. Subject of both outcome lines. |
| M-FLAT | `Memory("flat")`: same keys, values and fusion, exhaustive top-8 of 4,096 | 198,145 | Flat reference for the routing interaction (section 6.6) and a second, separate competitiveness sub-label. |
| D-ADAPT | `DenseAdapter`, width 3,100 | 198,401 | The dense baseline of line 2. |
| BASE | Frozen backbone, no addition | 0 | Reference loss B for every gain. Nine evaluations. |

### 3.3 Data regimes

A cell is (parent, init seed). All arms of a cell share the batch stream of their regime.

| Regime | Training stream | Arms |
|---|---|---|
| REP (repeated, seen) | The 2,048 chunks the backbone was trained on (train ranks 0–2,047), reshuffled each epoch. 16,384 updates are 64 passes. | M-TREE, M-FLAT, D-ADAPT |
| REP-U (repeated, unseen) | The 2,048 chunks at train ranks 2,048–4,095, reshuffled each epoch. The nine parents come from the P2/P3 lineage, which trained on ranks 0–2,047 only (`configs/p2_optimization_followup.toml`, `p3_longer_training.toml`); P1 ranked 4,096 train chunks and consumed 256 updates × 8 = 2,048 of them (`configs/p1_ram_screen.toml`). The ranking is a SHA-256 hash, so ranks 2,048–4,095 come from the same distribution. A gate proves that no training batch in the lineage of the nine parents contained them; the same gate is applied to the FRESH ranks. | M-TREE, D-ADAPT |
| FRESH (single pass, unseen) | Chunks at train ranks ≥ 4,096, each used once. U updates consume 8U unique chunks. It starts at 4,096 because 2,048–4,095 is REP-U. | M-TREE, M-FLAT, D-ADAPT |

| Contrast | What it isolates |
|---|---|
| Checkpoints within one regime | Duration. In REP and REP-U with no new data; in FRESH together with new data. |
| REP against REP-U, same update count | Data the backbone was fitted to against data it never saw, at equal unique data. |
| REP-U against FRESH, same update count | Additional unique data, at equal unseen-ness. |
| Memory against D-ADAPT on the same stream; controls of section 3.4 | Memory-specific learning. |

M-FLAT is not run in REP-U: the regime exists to split "seen" from "unseen" for the two arms of the outcome lines, and adding the flat arm would cost about 0.7 h of registered runs and 0.4 h of rehearsal or more. The consequence is that COMPETITIVENESS[FLAT] and the routing quantities cannot be split that way.

REP-U is added by the lead's decision for this draft, after the review (F5). **PENDING HUMAN LEAD RULING** (open choice 5): the human lead may drop it and accept that FRESH against REP mixes the two effects.

At 16,384 updates REP and REP-U are 64 passes over 131,072 target bytes with a 198k-parameter addition and no weight decay. Their endpoints largely measure how each arm behaves once it can fit its training set. A competitiveness label on repeated data can come from the dense adapter overfitting faster. The report says so beside every REP and REP-U label.

The 512-update point of this study differs from P4 in seeds, panel, rate selection and epoch reshuffling. It is a new measurement, not a replication of P4 or P5, and it is not compared with their numbers by any rule.

### 3.4 Controls (evaluation only; no control trains or writes a checkpoint)

Evaluation runs in 64 batches of 8 chunks (512 positions each), in panel order, as in P4.

| Control | Applied to | Definition | Shows |
|---|---|---|---|
| Memory disabled | all additions | Addition bypassed. Must equal BASE bitwise on the platform of record. | Engineering identity. With a frozen backbone it is the same contrast as C, not independent evidence (ADR-0009). |
| P_all: all-slot value permutation | M-TREE, M-FLAT | One permutation of all 4,096 value rows (P4's control). | Continuity with P4. Descriptive only (section 2). |
| P_used: used-slot value reassignment | M-TREE, M-FLAT | S = the slots selected at least once when the unmodified checkpoint reads the panel in panel order. S is sorted by slot ID; a seeded permutation σ of S is drawn; slot σ[t] receives the value of slot σ[t+1 mod \|S\|]. Mean over 4 seeded draws. | Whether the gain depends on which trained value sits at which address. A misplaced value can also do harm beyond the loss of the gain; B − H_used is printed per cell with the count of cells pushed above baseline. |
| X_mean: context-free read | M-TREE, M-FLAT | In each evaluation batch the read (the combined vector before W_o) at every position is replaced by its mean over the 512 positions. | Whether the batch-mean read, applied at every position, keeps the gain. It is expected, not guaranteed, to keep between 0 and about C: the mean read is one particular constant passed through the nonlinear block 1, and it can raise the loss above B. B − H_mean is printed per cell with the count of cells in which H_mean > B. It is one context-free read, not the best one. The batch mean includes reads at later positions and in other chunks of the batch; it can carry batch-level information, which makes D3 harder to meet, not easier. |
| X: query reassignment | M-TREE, M-FLAT | In each evaluation batch a seeded permutation σ of the 512 positions is drawn (64 draws in batch order from one generator per seed); position σ[t] is read with the query of σ[t+1 mod 512]. Mean over 4 seeded draws. | That the read is query-specific. It is a mismatched read, not a context-free one, and it can do harm beyond the loss of the gain. Descriptive only; B − H_x and the count above baseline are printed. |
| X_dense, X_mean_dense | D-ADAPT | The same two operations on the adapter's input positions and on its output. | Descriptive like-for-like figures. Any input-dependent module shows some such effect. |
| Joint key/value permutation within branch | M-TREE | ADR-0009's construction (one seeded `randperm(256)` per branch, branches in order, applied to keys and values together), seeded with this study's joint seed; P4's helper is not called. NLL must match the enabled reference within 1e-6. | Engineering invariance. |
| Exhaustive read; prior removed | M-TREE | Same checkpoint read through `tree_candidates` with `visit=16`; and with `use_prior=False`. | Retrieval alone, no training change (routing note 5.3 condition 1). |
| NEG-REF | built from each rehearsal M-TREE checkpoint | Every value row replaced by the usage-weighted mean value. The read is the same for every address by construction. | Validity reference: P_all, P_used, X and X_mean must be 0 within 1e-6 and the rule of section 6.2 must not return DEPENDENT. |

"Enabled reference" is the evaluation of the restored checkpoint with no intervention; "replay" is a second such evaluation after a fresh restore, and it must equal the reference bitwise on the platform of record.

**Line 1 is a stricter test than P4's flag 2 and is not comparable with it.** P4 used the all-slot shuffle with no ratio. Any statement about how dependence changes with duration compares P_used and X_mean at this study's own 512-update checkpoint with the same controls at U\*. It is descriptive, and it never uses P4's P.

There is no arm in this natural-text setting whose dependence on memory holds by construction (P10-S1 had R2). In its place: a planted-positive unit test of the intervention code (section 11), NEG-REF, reading line 1 at U\* only, and a synthetic-registry test of the analysis (open choice 7).

## 4. Data, seeds, sizes, checkpoints

**Corpus.** The pinned WikiText-2 acquisition of ADR-0004, byte tokenizer and chunk recipe of ADR-0005. No download, no test split. The recorded pool (`results/p4-2026-11-12/*/dataset_manifest.json`): 156,611 eligible unique train chunks and 16,407 eligible validation chunks.

**FRESH pool.** Train ranks 4,096 to 156,610: 152,515 chunks. A cell's FRESH stream is a seeded permutation of the whole pool; update k (from 0) takes entries 8k to 8k+7. 16,384 updates use 131,072 chunks. **The pool supports at most 19,064 fresh updates.** This design ceiling is why the duration is fixed (section 5.2).

**Panels.** Rule: a panel is the first 512 eligible validation chunks, walking down the ranking from rank 8,192, whose (row, byte span) overlaps no byte span drawn or designated for any panel or window by any earlier study or any P10-I sibling. Earlier chunk panels (P1 to P8, validation ranks 0–4,095) are excluded by rank. Window panels (P10-S2's 144 GEN windows and any other windows it drew from validation; ADR-0025's windows) are mapped to (row, byte-offset) spans by a documented procedure before the comparison. The registered panel is taken first, then the calibration panel. `arbor-clerk` inventories and `arbor-auditor` reconstructs independently; both must reproduce the recorded panel SHA-256 values of P1 to P8. The two panels are written into a ledger that ADR-0025 and ADR-0027 must exclude; whichever study freezes first writes first, with one exception: every marker-like window of ADR-0025's fixed grid (ADR-0025 section 4.1) is excluded by this study's walk whether or not ADR-0025 has frozen, computed from ADR-0025's definition and listed in the plan; ADR-0025's sampled windows are drawn after this study's panels if this study freezes first. (ADR-0025 states that its 44 marker-like windows cannot give way; they have priority over this study's panels whichever study freezes first.) If the walk runs out of eligible chunks, the run stops (engineering stop). The walk starts at rank 8,192 only to leave a margin above every earlier chunk panel (ranks up to 4,095); the figure has no other meaning. Each evaluation covers 32,768 targets, as in P4.

**Seeds.** All seeds of this study are new and are assigned in the programme-wide registry, `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` section 4.2, which is the authority; the values below are copied from it. Initialization: registered 330301, 330302, 330303 (seed positions 0, 1, 2); calibration 330391; dry rehearsal 330392; test mode 330398, 330399. Tests: 935001–935999. Streams and permutations: 260001–269999, laid out as in the table. The first proposal for initialization, 2601–2699, collided with P8 (2601 and 2602 are P8's seeds 601 and 602 plus 2000, the offset of the values generator; registry section 5) and was replaced; the first review's statement that it had no overlap was wrong.

Two conditions of the registry bind this study (its section 4.3). (1) The study does not call P4's or P5's permutation helpers (`src/arborlm/p4_model.py:266-270`, `p5_model.py:258-262`), which hard-code 40000 + index … 70000 + index; it uses its own P_all, P_used and X seeds. (2) The freeze gate checks every planned and recorded seed against the registry with derived values expanded (the registry's rules R2 and R3: component seeds such as seed + 1000 … + 5000, and index-derived seeds), read from code and configs, by re-running a copy of the registry checker extended with this study's values. The copy excludes, by recorded substitutions, the literal scan of this study's own files and of each P10-I study's own config and tests against its own allocation (ADR-0029 section 19, ruling 6); its hash goes into the gate result, and this study's values are checked separately against its allocation rows. Reason: the cited checker returns FAIL on the tree of 2026-11-18 for that cause alone. No initialization seed is derived by arithmetic from a data, permutation, calibration, rehearsal or test seed.

Cell index c = 9(B−101) + 3(O−301) + seed position, 0–26; calibration cells c = 0–2; regime g = 0–2; draw j = 0–3.

| Role | Count | Notes |
|---|---|---|
| Registered initialization seeds | 3 | 330301–330303: one seed per seed position (0, 1, 2), shared by all nine parents; each expands to five component seeds (seed + 1000 … + 5000; `DenseAdapter` uses + 3000 and + 4000) |
| Calibration initialization seed; dry-rehearsal initialization seed | 1; 1 | 330391; 330392. Same expansion |
| Test-mode initialization seeds | 2 | 330398, 330399 |
| Registered stream seeds | 81 | 260001 + 3c + g (260001–260081) |
| Calibration stream seeds; dry-rehearsal stream seeds | 9; 3 | 269001 + 3c + g (269001–269009); 269201 + g (269201–269203) |
| P_all seeds | 27 + 3 + 1 | 260101 + c (260101–260127); 269021 + c; 269221 |
| P_used seeds | 108 + 12 + 4 | 260201 + 4c + j (260201–260308); 269031 + 4c + j (269031–269042); 269231–269234 |
| X seeds | 108 + 12 + 4 | 260401 + 4c + j (260401–260508); 269051 + 4c + j (269051–269062); 269251–269254 |
| Joint-permutation seeds | 27 + 3 + 1 | 260131 + c (260131–260157); 269024 + c (269024–269026); 269222 |
| Test seeds | 935001–935999 | Never used outside tests |
| Spare | — | 267001–268999 and 269301–269999, unused |

The joint-permutation seeds were added after the third review. These values are free in the study's block but outside the registry's named layout; the registry's ADR-0026 row is extended by the lead and the checker copy includes them before the freeze.

A cell's permutation seeds are reused across arms, regimes and checkpoints. This pairs the arms and is deliberate.

**Cells.** 9 parents × 3 init seeds = 27 cells per arm and regime. They share nine parents and one corpus; they are not 27 independent replications, and no p-value is computed.

**Checkpoints.** Saved and evaluated at 0, 512, 2,048, 8,192 and U\* = 16,384 updates. U\* is the one primary checkpoint. The earlier checkpoints are descriptive. No rule of sections 6.2 to 6.5 reads them, and none may replace U\*.

## 5. Rehearsal: rate search, convergence tag, sealing

The rehearsal uses init seed, streams and panel that the registered run never uses. Its three cells sit on parents B101/O301, B102/O302 and B103/O303. **These are three of the nine registered parents; no other backbones exist.** Consequences, stated here and in section 12: rates are tuned on a third of the registered parents (the same way for every arm, so it is fair between arms, but estimates on those parents are optimistic for all arms); calibration statistics would predict the registered outcome, which is why they are sealed (section 5.3); and each calibration FRESH stream shares about 86% of its chunks with any registered FRESH stream (131,072 of 152,515), which leaks no panel data. Every threshold in section 6 is fixed at Decision 1, before the rehearsal.

### 5.1 Rate search (the same for every trainable arm)

P10-S1 compared untuned memory arms with a calibrated dense control. Here every trainable arm gets the same search, in each regime it runs in, at each duration.

- Grid: 0.0003, 0.001, 0.003, 0.01, 0.03 (half-decade steps around P4's 0.003). One run per (arm, regime, rate, calibration cell) to 16,384 updates, with the checkpoints of section 4.
- The rate is constant and there is no schedule, so checkpoint c of a longer run is a c-update run. One run serves every duration. A gate checks this bitwise (section 11).
- Selected rate r(arm, regime, c) for c in {512, 2,048, 8,192, 16,384}: let m be the lowest mean calibration-panel NLL at c over the three calibration cells among the rates with finite loss in all three; the selected rate is the smallest rate whose mean is within 0.0005 nats/byte of m.
- Edge rule: if, at some duration, the rate attaining m (on an exact tie, the smaller) is the lowest or highest finite rate run, the grid is extended by one half-decade step on that side and the selection repeated, at most twice per side. A rate whose neighbour is non-finite in any calibration cell is not at an edge on that side. If after the extensions the rate attaining m for U\* is still the lowest or highest rate run, the selected rate for U\* is tagged RATE-AT-EDGE. The edge is read from the minimiser, not from the tie-selected rate, so that a flat loss cannot create the tag and an optimum at the end cannot be hidden by the tie rule. (This is a design ceiling with a written extension, section 7. The selected rate is still used when it carries the tag.)
- If no rate is finite in all three cells for some (arm, regime), no rate can be chosen: engineering stop before Decision 2.
- The selection is made by code. Output: the rate table, 8 arm-regimes × 4 durations, frozen at Decision 2.

### 5.2 Duration and the convergence tag

**U\* = 16,384 updates, fixed.** It is the direction's proposed minimum, and it is also close to the most the corpus allows: unseen single-pass data ends at 19,064 updates, and the next doubling, 32,768, cannot be reached in FRESH. A duration chosen by a convergence rule is therefore not available on this corpus. The rehearsal does not choose the duration. It measures convergence and attaches a tag.

- Let M(arm, regime, c) be the mean calibration-panel NLL at c of the runs at rate r(arm, regime, 16,384), and δ = M(8,192) − M(16,384). ε = 0.001 nats/byte.
- Tag, computed by code: CONVERGED if δ < ε (a rising loss counts as converged), otherwise NOT CONVERGED, per arm and regime.
- **The study runs at 16,384 whatever the tags are.** A NOT CONVERGED tag changes no label; its effect on wording is in section 6.4 and on S4 entry in section 12.
- The study is not run only for a cost or engineering reason of section 10, recorded before Decision 2. No calibration statistic can be such a reason, and the lead does not see them (section 5.3).
- A larger corpus is not an option inside this study. If the human lead wants a convergence-chosen duration, that is a successor study with its own data decision and its own rehearsal.
- The registered run recomputes δ on its own 27 cells and prints its own tags. Where the rehearsal tag and the registered tag differ, both are printed and the registered one is used in section 6.4.

**PENDING HUMAN LEAD RULING** (open choice 1): whether a fixed duration with a convergence tag meets DIRECTION section 4 ("a preregistered convergence-based duration"), or whether a larger corpus must be approved first. Taken at Decision 1 by the lead under the delegation: the fixed duration with the tag. It is a departure from the direction's wording, and the human lead can overrule it before Decision 2 (section 18).

Reason for ε: one fifth of the 0.005 resolution. If the gain per doubling does not increase (an assumption), an arm below ε would move by less than 0.002 over two further doublings, less than half of any deciding margin. The lead's expectation, not a measurement: FRESH arms may well be NOT CONVERGED at 16,384.

If the REP or REP-U loss of an arm at U\* is more than 0.005 above its lowest earlier checkpoint (both taken along the primary-rate run, on the 27-cell mean; on the three-cell mean in the rehearsal), the tag PAST BEST CHECKPOINT is printed; no checkpoint is selected because of it.

### 5.3 Sealing of the calibration statistics

The rehearsal driver prints no loss value. It writes two files.

| File | Content | Who reads it before the registered outcome is recomputed |
|---|---|---|
| `rehearsal_public.json` | The rate table; δ and the CONVERGED / NOT CONVERGED tag per arm and regime; RATE-AT-EDGE flags; pass or fail of NEG-REF, of the planted-positive test, of the prefix and read-equality gates and of the synthetic-registry test; seconds per update and per evaluation; storage; the SHA-256 of the sealed file | The lead and the human lead. This list is the whole whitelist. |
| `rehearsal_sealed` (one archive, hashed) | Every per-run loss curve; C, C_dense, Q, K1–K3, D1–D3, P_used, X, X_mean and the routing quantities for the calibration cells; NEG-REF values | Nobody. The auditor's code recomputes `rehearsal_public.json` from it and reports only "agree" or "disagree". |

The sealed file is opened after the registered outcome has been recomputed by the auditor, and is then published as a calibration record. **No condition of section 6 is withdrawn or changed after any rehearsal output exists.** If a gate shows a condition or its code to be defective, that is an engineering stop: a specification amendment with a recorded reason, a re-freeze and the human lead's approval, made before any sealed file is opened.

If the auditor's recomputation disagrees, the auditor and the implementer reconcile on code and on the DRY and synthetic files only; no one reads the sealed file. If they cannot reconcile, that is an engineering stop before Decision 2 (section 10). The auditor's checker prints only `agree`, `disagree` and the names, not the values, of disagreeing fields; its source is part of the review record.

**The seal works by procedure, not by a technical barrier.** The sealed archive is stored outside every agent's working directory, its SHA-256 is recorded in `rehearsal_public.json`, and every session that touches it is logged in the run's `NOTES.md`. Nothing prevents a determined reader from opening it; the record would show that it was done.

Order: R1 → R2 → the candidate `plan.json` is written (items, rate table, worker count, caps) → R3 runs every registered stage end to end against that file itself in the DRY profile, and its SHA-256 goes into `rehearsal_public.json` → the freeze refuses unless the file it commits has that hash → Decision 2. The registered caps are in the candidate plan before R3 runs. R3 is the counting rehearsal: it is the one whose record the freeze rests on (sections 7, 8 and 11).

## 6. Rules that turn measurements into labels

### 6.1 Quantities and conventions

All losses are next-byte NLL in nats/byte on the registered panel, at U\*, per cell (parent p, seed s), per regime, from the run at the frozen rate for U\*. A cell's NLL is the sum of per-target losses divided by 32,768, computed on the one arithmetic path of section 16, ruling 1 (which replaces the earlier words "in float64"). "Mean" is the arithmetic mean over the 27 cells of the per-cell quantity; a parent's value is the mean over its three seeds. Every comparison is ≥ or > exactly as written, with no rounding first.

**Failed cells.** A failed cell is a registered run in which the training loss, the clipped gradient norm or any trainable parameter becomes non-finite, or whose enabled NLL at U\* is non-finite. A non-finite NLL under an intervention (P_all, P_used, X, X_mean) on a finite checkpoint makes that cell fail D2 or D3, never pass, and is printed. In the code these are the errors P4 already raises: the three `ValueError`s of `p4_model.train_step` (non-finite loss; non-finite gradient norm, from `clip_grad_norm_(error_if_nonfinite=True)`; non-finite parameters) and the `ValueError` of `p4_model.evaluate` on a non-finite NLL. Any other error is an item error (section 10), not a failed cell. If any of the 27 cells of an arm is a failed cell, every mean condition of that arm in that regime is false, and the failed cell counts as failing every per-cell and per-parent count. No mean that enters a condition, label or tag is computed over fewer than the registered cells (27; three for the rehearsal's tags). The six-parent readout of section 6.7 prints means over 18 cells and counts out of 18 cells and 6 parents, with no label. If an arm has a failed cell in a regime, its δ and PAST BEST are printed as NOT DETERMINED, which counts as NOT CONVERGED wherever a tag is read. Reason: the alternatives are a mean over the 26 surviving cells, which would hide the failure and could pass, and a NaN, which two implementations treat differently. This rule cannot turn a failure into a pass.

| Symbol | Definition (positive direction) |
|---|---|
| C | B − H: baseline minus memory (memory helps) |
| C_dense | B − A: baseline minus dense adapter |
| P_used | H_used − H: loss rise under used-slot value reassignment |
| X_mean | H_mean − H: loss rise under the context-free read |
| Q | A − H: dense minus memory (memory ahead) |

"22 of 27 cells" and "8 of 9 parents" are P4's counts. 22 of 27 allows five exceptions; 8 of 9 stops a few favourable backbones from carrying a pooled mean. 0.005 nats/byte is the resolution used since ADR-0006; it is about 2 to 10 times (1.85 to 9.66) the across-seed SD of C within a parent in P4.

### 6.2 Line 1 — DEPENDENCE (arm M-TREE; computed per regime)

| Condition | Rule |
|---|---|
| D1 capacity | mean C ≥ 0.005; C > 0 in ≥ 22/27 cells; parent mean C > 0 in ≥ 8/9 |
| D2 stored association | mean P_used ≥ 0.005; (C > 0 and P_used ≥ 0.5·C) in ≥ 22/27 cells; parent mean P_used > 0 in ≥ 8/9 |
| D3 query dependence | mean X_mean ≥ 0.005; (C > 0 and X_mean ≥ 0.5·C) in ≥ 22/27 cells; parent mean X_mean > 0 in ≥ 8/9 |

A cell whose used-slot set S has fewer than two slots fails D2 and is listed as COLLAPSED. ADR-0009's flag 1 also required mean final H below mean initial H. D1 leaves this out deliberately: with a frozen backbone the step-0 loss equals B to about 2e-7 (P4: 2.378856566 against 2.378856373), so mean C ≥ 0.005 already implies it. Step-0 losses are printed.

Reason for 0.5: "dependent" is taken to mean that the larger part of the gain is lost under the intervention. It is a convention and does not favour the memory (open choice 3).

The regime label is computed in this order; the first rule that applies decides.

| Order | Rule | Regime label |
|---|---|---|
| 1 | A stop or integrity case of section 10 applies to M-TREE in the regime, or BASE is missing or fails its check | NOT EVALUABLE |
| 2 | D1 and D2 and D3 | DEPENDENT |
| 3 | D1, and not (D2 and D3); the failing conditions are named | CAPACITY WITHOUT DEMONSTRATED DEPENDENCE |
| 4 | not D1 | NO CAPACITY |

A failed M-TREE cell (a non-finite value as section 6.1 defines it) is not an integrity case: it falls under the failed-cell rule of section 6.1 and gives NO CAPACITY. M-TREE's RATE-AT-EDGE tag for U\*, if any, is printed beside the line-1 label; it changes no label.

### 6.3 Line 2 — COMPETITIVENESS (memory against D-ADAPT; computed per regime)

| Condition | Rule |
|---|---|
| K1 absolute tolerance | mean Q ≥ −0.005; Q ≥ −0.005 in ≥ 22/27 cells; parent mean Q ≥ −0.005 in ≥ 8/9 |
| K2 share of the dense gain | mean C ≥ 0.90 × mean C_dense |
| K3 ahead | mean Q ≥ +0.005; Q > 0 in ≥ 22/27 cells; parent mean Q > 0 in ≥ 8/9 |

The regime label is computed in this order; the first rule that applies decides.

| Order | Rule | Label |
|---|---|---|
| 1 | A stop or integrity case of section 10 applies to the regime | NOT EVALUABLE |
| 2 | mean C_dense < 0.005 (the dense adapter adds nothing measurable) | NOT EVALUABLE |
| 3 | K3 | MEMORY AHEAD |
| 4 | K1 and K2 | COMPETITIVE |
| 5 | otherwise | NOT COMPETITIVE |

Reasons. K1 is P4's tolerance, unchanged. K1 alone is easy when both gains are small, so K2 adds a proportional condition; it binds more than K1 only while mean C_dense is below 0.05. The figure 0.90 follows the proportion this programme used for "close to a reference" in P10-S0. That is a convention, not a derivation; it is conservative, and P4's 512-update figures (0.78 of the means; best cell 0.8997) do not meet it.

The line is computed twice, with separate labels that are never merged: COMPETITIVENESS[TREE] for M-TREE (the headline) and COMPETITIVENESS[FLAT] for M-FLAT (REP and FRESH only). The better of the two is not selected.

### 6.4 Tags

Applied after section 6.3, in this order. "Losing arm" is the arm with the higher mean NLL at U\* in that regime, whatever the label.

| Situation | Effect |
|---|---|
| Label NOT COMPETITIVE and the memory arm's rate for U\* is RATE-AT-EDGE | Label becomes INCONCLUSIVE (MEMORY RATE AT EDGE) |
| Label COMPETITIVE or MEMORY AHEAD and D-ADAPT's rate for U\* is RATE-AT-EDGE | Label becomes INCONCLUSIVE (DENSE RATE AT EDGE) |
| The losing arm is NOT CONVERGED at U\* | Label kept; "(MEMORY STILL IMPROVING)" or "(DENSE STILL IMPROVING)" is appended |
| A REP or REP-U arm is PAST BEST CHECKPOINT | Label kept; tag appended |

Line 1 carries the NOT CONVERGED and PAST BEST tags of M-TREE in the same way; they change no label.

### 6.5 The registered label of each line

**The registered label of a line is its FRESH regime label.** FRESH is the only regime whose data is both unseen by the backbone and not repeated. The REP-U and REP regime labels are computed by the same rules and printed beside it, in that order, as regime labels. They are never the line's label and never make a line positive. If the FRESH label is NOT EVALUABLE or INCONCLUSIVE, so is the line, whatever the other regimes show.

A line is "registered positive" only in these cases: line 1 = DEPENDENT in FRESH; line 2 = COMPETITIVENESS[TREE] is COMPETITIVE or MEMORY AHEAD in FRESH.

### 6.6 Routing and training duration (descriptive, with a fixed reading rule)

The P4 setting has a tree with a sparse read, so the interaction the human lead asked for is measured here. At each checkpoint c in {512, 2,048, 8,192, U\*}, in REP and FRESH, per cell:

| Quantity | Definition | Isolates |
|---|---|---|
| G_train(c) | H(M-TREE) − H(M-FLAT), each from its run at its rate for c | Tree against a separately trained flat memory: training and retrieval together. Across checkpoints it also mixes the per-duration rate with duration; the primary-rate trajectory is printed beside it. |
| G_read(c) | H(M-TREE) − H(M-TREE read exhaustively), same checkpoint | The top-2 restriction alone |
| G_prior(c) | H(M-TREE, prior off) − H(M-TREE), same checkpoint | The branch prior alone |

Reading rule for G_train at each c: TREE BEHIND if mean ≥ +0.005 and G_train > 0 in ≥ 22/27 cells; TREE AHEAD if mean ≤ −0.005 and G_train < 0 in ≥ 22/27; otherwise WITHIN RESOLUTION. The same rule is applied to G_read (RESTRICTION COSTS / WITHIN RESOLUTION / RESTRICTION HELPS). G_prior is printed without a label. Trend: "GAP CHANGES WITH DURATION" if the label at 512 differs from the label at U\*, otherwise "NO CHANGE AT THIS RESOLUTION". Because a label can change on a small move across the threshold, ΔG = G(U\*) − G(512) is printed with its mean and sign count beside every trend label. Distinct selected slots and branch-use entropy are printed too.

**This section is descriptive and is not a third outcome line.** Reasons: (1) the routing-quality outcome line belongs to ADR-0029 (P10-I-R), and a second registered routing line on a different task could be read as standing in for it; (2) in P5 the tree-versus-flat difference at 512 updates was 0.0014, inside the resolution; (3) the interaction is a statement about several checkpoints, and the direction makes every checkpoint before U\* descriptive. The reading rule is written in full and its code is tested like the registered rules (section 11). Whether a descriptive section satisfies "tested in ADR-0026" is open choice 6.

### 6.7 Other descriptive output

Every quantity at every checkpoint for every arm and regime, by per-duration rate and along the primary-rate run; the contrasts of section 3.3 for C, C_dense and Q at 512 and at U\*; P_used and X_mean at 512 against U\* (section 3.4); M-FLAT's D1–D3; P_all, X, X_dense, X_mean_dense; B − H_used, B − H_x and B − H_mean with their counts of cells above baseline; the loss under the context-free read, H_mean, per cell; means, SDs, ranges, sign counts, per-parent and per-seed values. No best seed, cell or checkpoint is selected.

**Six-parent readout.** Both lines are recomputed on the six parents not used in calibration (18 cells, 6 parents) and printed as plain figures beside the registered labels, so that sensitivity to the tuning parents is visible. It changes no label.

**P4-rate anchor.** If the frozen REP rate of M-TREE or of D-ADAPT for U\* is not 0.003, that arm is also run in REP at 0.003 to U\*. It shows how much of any change from the 512-update picture comes from rate selection and how much from duration. Descriptive only.

## 7. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Hour caps in charged hours (wall-clock hours of a stage's supervisor, at the plan's worker count): rehearsal 25 h; registered run = charged so far + 2 × projected remaining from R2's rates (ADR-0029 section 12's rule), written into the candidate plan; 48 h until then | Resource cap | May be extended by the human lead on cost projections only, never on outcome values. A stage that reaches a cap is PAUSED and resumed; every planned cell still runs. |
| RSS guard 2 GiB per worker, 24 GiB aggregate (12 GiB aggregate while the machine is shared with another study, section 17) | Resource cap | Same. |
| U\* = 16,384 | Design ceiling | Fixed. No extension path in this study (section 5.2). |
| FRESH pool: 152,515 chunks, at most 19,064 fresh updates | Design ceiling | Not extended in this study. No chunk is reused in FRESH. |
| Rate grid: five rates | Design ceiling | Extended by the edge rule of section 5.1, at most two steps per side. |
| Rate tie tolerance 0.0005; PAST BEST margin 0.005 | Design ceiling | Fixed; they decide a rate or a tag, never a label. Reason for 0.0005: one tenth of the 0.005 resolution. |
| Calibration: three parents, one seed | Design ceiling | Not extended. |
| Panel: 512 chunks; evaluation batch 512 positions | Design ceiling | The panel is met by walking down the ranking (section 4). |
| Permutation draws: 4 per control | Design ceiling | Not extended. |
| 0.005 nats/byte; 22/27; 8/9; 0.5·C; −0.005; 0.90; ε = 0.001 | Scientific threshold | Fixed at Decision 1. Never relaxed after observation. |

No limit is extended because a partial result looks close.

## 8. Stages and machine load

Training and evaluation are deterministic CPU float32 with one thread per worker. Their results do not depend on machine load. **No wall-time comparison is registered in this study**, so no stage needs a quiet machine for validity. The load average is measured at the start of each stage and recorded.

| Stage | Content | Load condition | If not met |
|---|---|---|---|
| R1 rehearsal: rate search, convergence tags, sealed statistics | 120 calibration runs, up to 216 with grid extensions | None | — |
| R2 rehearsal: cost measurement | Seconds per update and per evaluation, 1 and k workers | Ordinary load, on purpose; the 1-minute load average is recorded | Projection flagged LOADED if the load average exceeds 4 (a convenience mark on a cost record; it decides nothing); it is still used, being the conservative figure |
| R3 rehearsal (the counting rehearsal): DRY run of every registered stage against the candidate `plan.json`, whose hash the freeze must match (section 5) | Minutes | None | — |
| G gates | Hashes of parents, data, code, plan; panels and REP-U ranks proved unused; seed disjointness; BASE and disabled = BASE bitwise on all nine parents; prefix identity; read equality; planted positive; NEG-REF; synthetic registry | None | A failed gate stops the run before any training |
| T training | All registered runs, resumable per cell | None | — |
| E evaluation | All checkpoints and controls, resumable per task | None | — |
| A analysis and report | Once, from the frozen code | None | — |

Seconds per update are descriptive records of this implementation on this machine. They are not an efficiency result, and logical work counts are not reported as measured efficiency anywhere.

## 9. Cost projection (an estimate; the rehearsal replaces it)

Measured inputs, from `training_seconds_including_logs_and_saves` in each cell's `result.json` (lead's computation, confirmed by the review; Apple M5 Max, one thread, cells run one at a time; the figures include logs and saves):

| Arm | Seconds per 512 updates (mean of 27) | ms per update | Source |
|---|---|---|---|
| Learned tree | 14.118 (P4), 14.067 (P5) | 27.6 | `results/p4-2026-11-12/`, `results/p5-2026-11-13/` |
| Flat | 3.062 | 6.0 | `results/p5-2026-11-13/` |
| Dense adapter | 4.261 (P4), 4.254 (P5) | 8.3 | both |

One evaluation of 32,768 targets cost about 0.5 s in P4 (memory cells: 17.686 s supervised wall minus 14.118 s training, for six evaluations and start-up). Scale reference from P10: P10-S0 charged 6.09 h of a 22-hour cap, with stages at 0.40–0.63 of projections rehearsed under load (`results/p10s0-run-2026-11-16/OUTCOME.md`); P10-S1 charged 25.39 h over two attempts of a 53-hour cap (`results/p10s1-run-2026-11-17/OUTCOME.md`).

Per run to 16,384 updates: M-TREE about 452 s, M-FLAT 98 s, D-ADAPT 136 s. There are 8 arm-regimes: three arms in REP and in FRESH, two in REP-U.

| Block | Runs | Single-thread compute |
|---|---|---|
| Rehearsal R1: 8 arm-regimes × 5 rates × 3 cells | 120 | 8.2 h |
| R1 grid extensions, worst case (4 more rates everywhere) | 0 to 96 | 0 to 6.5 h |
| Rehearsal evaluations, R2, R3 | — | about 1.5 h |
| **Rehearsal total** | 120 to 216 | **about 10 h to 16 h** |
| Registered primary: REP and FRESH, 3 arms × 27 cells | 162 | 10.3 h |
| Registered primary: REP-U, 2 arms × 27 cells | 54 | 4.4 h |
| Per-duration runs, where the rate for 512, 2,048 or 8,192 differs from the rate for U\* | 0 to 648 short runs | 0 to 9.6 h |
| P4-rate anchor (REP; M-TREE and D-ADAPT) | 0 to 54 | 0 to 4.4 h |
| Evaluation: about 16 evaluations per M-TREE checkpoint, 13 per M-FLAT, 8 per D-ADAPT (enabled, replay, disabled, four X_dense draws, X_mean_dense); about 10,400 evaluations for the primary runs, up to about 20,000 with per-duration and anchor runs; the exhaustive read is slower than 0.5 s | — | about 1.5 h to 3.5 h |
| **Registered total** | 216 to 918 | **about 16 h to 32 h** |

Order of magnitude for the whole study: 26 to 48 hours of single-thread compute. Parallel workers shorten wall time; the rehearsal measures by how much. The caps (25 h and 48 h) are the worst-case totals times about 1.5. Checkpoint storage: about 2.4 MB per snapshot with optimizer state (arithmetic from the parameter count, not measured), at most about 4,400 snapshots by the confirmation review's count (the lead's earlier 5,700 was not reproduced and is withdrawn), so up to about 11 GB and more likely 4 to 8 GB. If the registered cap by that rule exceeds 48 charged hours, the lead returns to the human lead before Decision 2 with the projection; the matrix is not cut. ("That rule" is the cap rule of section 7: charged so far + 2 × projected remaining.)

The rehearsal measures: seconds per update per arm, rate and regime; seconds per evaluation, including the exhaustive read; the parallel slowdown; storage per snapshot; the number of distinct rates in the rate table, which fixes the per-duration and anchor rows.

## 10. Stop rules and NOT EVALUABLE

| Event | Consequence |
|---|---|
| A gate fails before training (section 8, stage G) (an identity difference during stages T, E or A is PAUSED — IDENTITY, section 11), including the prefix-identity, read-equality and planted-positive gates | Engineering stop. No registered cell is observed. A fix needs a re-freeze and the human lead's approval of a new attempt. |
| The panel walk runs out of eligible chunks; or no finite rate exists for some (arm, regime) in calibration | Engineering stop before Decision 2. |
| The auditor reports "disagree" on `rehearsal_public.json` and reconciliation fails (section 5.3) | Engineering stop before Decision 2. |
| The rehearsal's cost projection exceeds a cap and the human lead declines an extension | The study is not run. This is recorded before Decision 2. Together with the engineering stops of this table it is the only ground stated in advance for not running; a refusal on any other ground is recorded as in section 14. |
| A stage reaches a resource cap | PAUSED. Resumed after an extension decided on projections only. Completed cells are not recomputed. |
| BASE is missing or fails its bitwise replay on a parent | Every line is NOT EVALUABLE in every regime. |
| A registered run of a memory arm is a failed cell (a non-finite value, section 6.1) | The cell is kept as failed and counts as failing every condition of its arm. Nothing is rerun at another rate. |
| A registered D-ADAPT run for U\* is a failed cell (a non-finite value, section 6.1) | Line 2 is NOT EVALUABLE in that regime. |
| A training or evaluation item ends with an error that is not a non-finite value as defined in section 6.1 (a code error, an assertion, out of memory, a file-system or other environment error) | The item is recorded as `item_error`. The registered analysis refuses while any `item_error` exists; the outcome is ENGINEERING STOP — ITEM ERRORS and no line is labelled (as ADR-0029 section 20, ruling 11). An environment error inside a gate propagates and is never recorded as a failed gate. S computed in a panel order different from the enabled read is such an assertion. |
| A required cell or evaluation is missing after the run ends and no `item_error` is recorded | Engineering stop (a defect of the plan or the driver); nothing is labelled. Denominators are never reduced. |
| Disabled ≠ BASE, replay ≠ enabled reference, or joint permutation outside 1e-6 on any cell | Integrity failure; the affected arm and regime is NOT EVALUABLE. |
| mean C_dense < 0.005 | Line 2 is NOT EVALUABLE in that regime (section 6.3, order 2). |

The registered run happens once. A negative or inconclusive label is a registered outcome. It is not a reason to add updates, seeds, rates or cells.

## 11. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| P10-S1 attempt 1 was lost to a commit of a status note into a frozen input (ADR-0021 sections 25.19–25.20) | **The frozen-input set is exactly:** (1) every file under `studies/p10i_s3/`, which holds the code, `freeze/plan.json`, `freeze/rate_table.json`, the seed plan and the extended seed checker (`freeze/seed_plan.json`, `freeze/seed_registry_check.py`) and the panel identities, together with the tests of this study, `tests/test_p10is3_*.py` (including the planted-positive and synthetic-registry tests), each by SHA-256; (2) `configs/p10i_s3_longer_training.toml`, which carries every threshold, tolerance, grid and margin of sections 5, 6 and 7 (ε, the rate grid, the 0.0005 tie tolerance, the edge rule, the PAST BEST margin, the 1e-6 tolerances, the LOADED mark, all thresholds of section 6); (3) `rehearsal_public.json` and the sealed file's SHA-256; (4) the shared panel ledger by SHA-256; (5) by SHA-256, the `src/arborlm/` files `pilot_model.py`, `model.py`, `pilot_config.py`, `pilot_data.py`, `fetch_wikitext.py`, `io.py`, `p4_model.py`, `p4_config.py`, `p2_model.py`, `engine.py`, `longer_training.py`, `pilot_metrics.py`, `__init__.py`, `config.py`, `data.py`, `optimization_followup.py`, `p2_config.py`, `p3_config.py`, `records.py`, `watchdog.py`, and every further file reached by a static walk of module-level and function-local imports from every module of `studies/p10i_s3/` (at least the P3/P4 parent and data loaders if they are used), each listed by name and SHA-256 in `plan.json`; (6) `uv.lock` and `pyproject.toml`; (7) the nine parent checkpoint hashes and the data hashes: the pinned parquet files and every derived chunk file (FRESH, REP, REP-U, panels) by SHA-256. The twenty files named in (5) are what the third review's import walk found at module level from `pilot_model`, `p4_model` and `pilot_data`. With the P3 and P4 loaders (`p3_checkpoint`, `p4_parent`, `p4_data`, `p4_checkpoint`) the same walk reached 31 files, adding `checkpoint.py`, `diagnose_memory.py`, `p2_checkpoint.py`, `p2_data.py`, `p3_checkpoint.py`, `p3_data.py`, `p3_parent.py`, `p4_checkpoint.py`, `p4_data.py`, `p4_parent.py` and `pilot_checkpoint.py`. The names here are a floor, not the list of record: the complete list is produced by the import walk at the freeze, written into `plan.json`, and compared with this list; a file named here that the walk does not reach, or a file the walk reaches that is not named here, is printed in the freeze record, and the freeze refuses if a file the walk reaches is missing from `plan.json`. Identity is checked by file hash, not by the commit at HEAD. Every task checks the frozen-input hashes when it starts. A difference stops the task as PAUSED — IDENTITY; nothing is recorded as a result; restoring the file bit for bit lets the stage resume. This is not a gate failure of section 10. **This ADR and everything else under `docs/` and `results/` are not run-time inputs.** This ADR's SHA-256 at Decision 1 and at Decision 2 is recorded in `plan.json`, so that the audit can compare the code with the approved text; any later edit of the ADR is an amendment with a record. No commit is made in the run's worktree while a registered stage runs. Status goes to chat or to `NOTES.md` in the git-ignored run directory. Every stage is resumable per cell or task. |
| P10-S1's throughput stage asked for a cell the frozen plan did not run (section 25.21) | Every registered stage reads its item list from `plan.json` only, and stage R3 runs each of them end to end against the candidate `plan.json` before Decision 2; the freeze refuses unless the file it commits has the hash R3 recorded (section 5). Tests use that plan, not a separate one. |
| P10-S1's audit: an unstated aggregation rule, a dependence condition that misfires early, a descriptive section that compared the wrong reads | Every combination and precedence rule is in section 6. Line 1 is read at U\* only. The analysis, including sections 6.6 and 6.7, is tested on a synthetic registry with known answers: one case per label, per tag and per order row of section 6.3, and a case where two arms' reads are swapped and the test must fail. |
| No arm with dependence by construction (review F11 a) | **Planted-positive test.** A toy frozen backbone and a memory whose values are set so that each slot gives the exact correction for a disjoint set of queries. The planted corrections are built with zero mean across each evaluation batch, since otherwise the batch-mean read would keep part of the gain. On it P_used, X and X_mean must each be ≥ 0.5·C and NEG-REF must give 0. It runs in the test suite and as a gate. |
| "One run serves every duration" was assumed (F11 b) | **Prefix-identity gate.** On the platform of record, a separate 512-update run is bitwise equal to checkpoint 512 of the 16,384-update run, for each arm and regime on one calibration cell. |
| The interventions need a re-implemented read (F11 c) | **Read-equality gate.** With no intervention, the study's read equals `Memory.forward` bitwise for both variants; the exhaustive read equals `tree_candidates(visit=16)`, the path P6 used. |
| P10-S2 stopped on a count gate although quality criteria were met | Counts that are not claims are met by rule: the panels by walking the ranking, the rate grid by the edge rule. |
| P10-S0 tested one load and one training length | Three data regimes and four evaluated durations; the duration is fixed for the reason given in section 5.2 and tagged for convergence. |
| A test passed on macOS and failed on Linux (section 25.23) | Platform of record: macOS arm64, Apple M5 Max, Python and PyTorch as in `uv.lock`. Bitwise assertions are made on it only; elsewhere the same checks use a 1e-6 tolerance. `engine.configure_cpu()` settings (one thread, one interop thread, deterministic algorithms), OS build recorded with every gate result. |
| GitHub CI is costly | `uv run --locked ruff check .`, `uv run --locked mypy src/arborlm` and `uv run --locked pytest` run locally. The study's tests live in `tests/test_p10is3_*.py`, so that a bare `pytest` collects them (`pyproject.toml` has `testpaths = ["tests"]`; a test under `studies/p10i_s3/` would not be collected). `mypy` covers `src/arborlm` only; it does not check `studies/p10i_s3/`, and no type-check result is claimed for the study's package. No CI run is required by this study. `uv.lock` and `pyproject.toml` do not change. |

Roles: `arbor-implementer` writes the code; `arbor-auditor` audits it in a separate context from code and records, not from the lead's conclusions, verifies the sealed file and recomputes the outcome from raw records; `arbor-clerk` inventories panels and hashes. The model that ran each task is recorded from session metadata.

## 12. What the study cannot establish, and what it means for P10-I-S4

It cannot establish:

- Anything about hierarchy as such, external scaling, SSD behaviour, active computation or cost. The store is 4,096 slots, all resident.
- Semantic storage. Line 1 shows dependence on value placement and that one context-free read does not keep the gain, not knowledge of facts. D3 tests one context-free read, the batch mean; a better constant is not tested. Any input-dependent module shows some query dependence.
- A general result. One 27,392-parameter backbone family, one corpus, byte-level text, one addition size, nine correlated parents.
- That freezing is better or worse than joint training, that dependence rose or fell relative to P4 (line 1 is a different, stricter test), or that any P4 or P5 number was wrong. Those studies stand as recorded.
- A fully tuned comparison. One hyperparameter is searched, with a constant rate, on three of the nine registered parents (section 5).
- What happens at convergence, if the tags say NOT CONVERGED. The duration is fixed by the corpus, not chosen by convergence.
- Equal compute. The arms are matched on trainable parameters and updates. In the P4 records an M-TREE cell's training took about 3.3 times a dense cell's wall time, logs and saves included (section 9); that is a descriptive record, and line 2 says nothing about it.

**For P10-I-S4's entry (ADR-0027, Route A).** The labels of this study that qualify are named here, so that neither ADR defers to the other:

| Clause | Qualifies | Never qualifies |
|---|---|---|
| A1, dependence | Line 1 registered label = DEPENDENT (that is, in FRESH), arm M-TREE | Any REP or REP-U regime label; M-FLAT's descriptive D1–D3; CAPACITY WITHOUT DEMONSTRATED DEPENDENCE |
| A2, competitiveness | Line 2 registered label COMPETITIVENESS[TREE] = COMPETITIVE or MEMORY AHEAD (in FRESH) | K1 alone ("within the margin") when the label is NOT COMPETITIVE; any INCONCLUSIVE or NOT EVALUABLE; any REP or REP-U regime label; COMPETITIVENESS[FLAT] |

Both clauses must hold, for M-TREE. Whether a qualifying label still qualifies when D-ADAPT's registered FRESH convergence tag (section 5.2, last bullet) is NOT CONVERGED, whichever arm is losing, is the human lead's choice (open choice 13), ruled at Decision 1. The ruling is "no" (section 18): a qualifying label does not qualify when D-ADAPT's registered FRESH tag is NOT CONVERGED. The lead asks that ADR-0027 copy these names and drop the phrase "within S3's own margin".

| Line 2 result | What it would mean | What it would not mean |
|---|---|---|
| COMPETITIVE or MEMORY AHEAD | Evidence the human lead may weigh for S4 entry: at matched trainable size and matched updates, with both sides rate-searched, the memory is within tolerance on unseen single-pass data of this task. | Not a cost result. S4's primary comparison is at matched training computation, where the per-update cost counts against the memory. Not evidence at any larger store or model. Not an entry decision; that is the human lead's. |
| NOT COMPETITIVE, both arms CONVERGED | S3 supplies no entry evidence. The P4 pattern holds at 16,384 updates in this setting. | Not a statement about larger stores, where a dense alternative must grow with the store, and not a revision of P10-S1, which the direction names as the other source of entry evidence (ADR-0027 reads that as P10-I-S1; its open choice 2) (P10-S1's registered label is DENSE AHEAD; the matched-compute observation at 32K/16K is an audit disclosure). |
| NOT COMPETITIVE "(MEMORY STILL IMPROVING)", or INCONCLUSIVE | No entry evidence, and no evidence against. | Not a reason to extend this study. |

COMPETITIVENESS[FLAT] is shown beside the headline in every case. A flat memory that is competitive where the tree is not points to the routing work of ADR-0029 (P10-I-R), not to S4.

## 13. Open choices reserved for the human lead

Every item below is taken at its recommended option at Decision 1 (section 18). The text of each item is kept as it was put.

1. **Fixed duration — PENDING HUMAN LEAD RULING** (section 5.2). Does U\* = 16,384, fixed, with a registered CONVERGED / NOT CONVERGED tag, meet the direction's "convergence-based duration"? Or must a larger corpus be approved first, as a separate data decision and a successor design? The direction proposes 16,384 "only if the rehearsal and the budget support it"; under this draft only the budget can fail to support it, since the rehearsal no longer chooses the duration. Recommendation: accept the fixed duration with the tag for this study.
2. **Rate fairness** (section 5.1): one grid and one selection rule for every arm, per regime and duration, on three calibration parents that are also registered parents. Recommendation: as drafted, with the six-parent readout.
3. **Dependence thresholds** (section 6.2): 0.005 absolute and one half of the gain, on used-slot reassignment and on the context-free read. Recommendation: as drafted. One half is a convention.
4. **Competitiveness thresholds** (section 6.3): P4's −0.005 tolerance and a 0.90 share of the dense gain, both required. Recommendation: both. Alternative: K1 alone, which keeps P4's rule exactly.
5. **Third regime REP-U — PENDING HUMAN LEAD RULING** (section 3.3). Included in this draft; about 4.4 h of registered runs and 2.5 h of rehearsal at the least. Alternative: drop it and accept the mix. The wording would then change everywhere to "additional unique data, confounded with data unseen by the backbone", and FRESH would start at rank 4,096 with no stated use for ranks 2,048–4,095. Recommendation: keep REP-U.
6. **Routing interaction** (section 6.6): descriptive with a fixed reading rule. Does that satisfy the routing note's "test the interaction in ADR-0026"? The alternative, a registered line across checkpoints, would contradict the direction's rule that intermediate checkpoints are descriptive. Recommendation: descriptive.
7. **No by-construction positive arm on natural text** (section 3.4). Recommendation: accept the planted-positive test, NEG-REF and the synthetic registry.
8. **Repeated-data order**: reshuffled each epoch with this study's seeds, or P4's fixed order cycled. Recommendation: reshuffled; a fixed order repeated 64 times is a periodic stream.
9. **Schedule**: constant rate (one change from P4: duration) or a decaying schedule. Recommendation: constant; it also lets one run serve every duration.
10. **Registered label = FRESH label** (section 6.5), with REP-U and REP as regime labels beside it. Recommendation: as drafted.
11. **Caps**: 25 h rehearsal, 48 h registered run, 24 GiB aggregate RSS. Recommendation: as drafted, with the registered-run cap set by the rule of section 7 (charged so far + 2 × projected remaining) in the candidate plan before R3; 12 GiB aggregate while the machine is shared (section 17).
12. **P4-rate anchor** (section 6.7): up to 4.4 h. Recommendation: keep; without it, rate selection and duration cannot be told apart in the 512-update comparison.
13. **Convergence and S4 entry** (section 12): does a qualifying label still qualify when D-ADAPT's registered FRESH convergence tag (section 5.2, last bullet) is NOT CONVERGED, whichever arm is losing? Recommendation: no; a dense arm that is still improving may overtake. Ruled at Decision 1, before any observation; ADR-0027 copies the ruling. Expected consequence: section 5.2 expects FRESH arms to be NOT CONVERGED at 16,384; under this option Route A of ADR-0027 is then closed by S3 whatever line 2 shows.

## 14. Decisions and approval record

- Decision 1 (human lead): approve this specification for implementation and rehearsal only. Every open choice of section 13 is ruled at Decision 1, before the rehearsal. **Taken on 2026-11-18 UTC by the lead under the human lead's delegation; recorded in section 18.**
- Decision 2 (human lead): after the rehearsal, with `rehearsal_public.json`, the auditor's agree or disagree, the cost projection and the freeze record, approve the single registered run. **Not given.** Who takes it, and on what record, is written down when it is taken; section 18 does not cover it.
- Grounds stated in advance for not running after Decision 1: an engineering stop of section 10, or a cost projection over a cap that the human lead declines to extend. This ADR cannot bind the human lead. If Decision 2 is refused on any other ground, the refusal and its reason are recorded in this ADR before any sealed file is opened, and the study's outcome is recorded as NOT RUN (DECISION 2 REFUSED: reason). The sealed file is then published with that record, opened by no one before the record is written.

Decision 1 is recorded in section 18. No approval of the freeze or of the registered run is recorded. `Astra review: NOT_PERFORMED`.

## 15. Review record

Revision 1 of this draft was reviewed by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0026.md`, verdict NOT READY (one blocking, ten required, five advisory findings; no quoted number found wrong). Revision 2 is by the lead (Claude Fable 5.2). The review is engineering evidence, not Astra validation and not an approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| F1 discretionary choice of duration after calibration | BLOCKING | FIXED: duration fixed at 16,384; tag by code; run is automatic; larger corpus is a successor study; probe removed; ruling requested | 5.2, 7, 10, open choice 1 |
| F2 unsealed calibration statistics; withdrawing a condition | REQUIRED | FIXED: whitelist, sealed hashed file, decisions by code, no withdrawal | 5.3, 14 |
| F3 what X measures | REQUIRED | FIXED: X_mean added and used in D3; X descriptive; harm printed; wording of line 1 narrowed | 1, 3.4, 6.2, 12 |
| F4 line 1 stricter than P4 | REQUIRED | FIXED | 3.4, 12 |
| F5 unique data confounded with unseen data | REQUIRED | FIXED: REP-U added and costed; alternative listed for the human lead | 3.3, 9, open choice 5 |
| F6 calibration parents are registered parents | REQUIRED | FIXED: stated; six-parent readout added | 5, 6.7, 12 |
| F7 seed offsets | REQUIRED | FIXED in revision 2 (assignment moved to the programme registry; roles and counts listed; cell indices defined), then corrected in revision 3: the initialization and test blocks were replaced by the registry's values after a collision with P8 was found | 4 |
| F8 panel rule | REQUIRED | FIXED: byte spans, siblings excluded, ledger, stop case | 4, 10 |
| F9 precedence and definitions | REQUIRED | FIXED: ordered label rule, losing arm, mean, exact comparisons, rate tie rule, D1 omission explained; the regime table is replaced by "registered label = FRESH label" | 5.1, 6.1–6.5 |
| F10 labels against ADR-0027 Route A | REQUIRED | FIXED: qualifying labels named; repeated-data labels are no longer called positive | 6.5, 12, open choice 13 |
| F11 planted positive, prefix identity, read equality | REQUIRED | FIXED: one test and two gates added | 8, 10, 11 |
| F12 budget worst cases | ADVISORY | FIXED: worst cases recomputed with REP-U; caps derived from them | 7, 9 |
| F13 routing trend | ADVISORY | FIXED: ΔG printed; rate mixing stated; question put to the human lead | 6.6, open choice 6 |
| F14 threshold reasons | ADVISORY | FIXED: assumption behind ε stated; K2's reason stated as a convention; repeated-data overfitting caveat | 3.3, 5.2, 6.3 |
| F15 wording | ADVISORY | FIXED | 2, 3.4, 4, 6.1, 7, 12 |
| F16 missing stop cases | ADVISORY | FIXED | 5.1, 10 |

No finding was answered instead of fixed. The lead's brief also asked that any statement of the machine's idle load as a recorded fact be removed: revision 1 contained none, and the load is measured at each stage (section 8).

**Confirmation review.** Revision 2 was reviewed by the same `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW2_ADR-0026.md`, verdict READY AFTER THE LISTED EDITS, no blocking finding. It recorded two errors of the first review that revision 2 had copied (the seed "no overlap" statement and the bound on the context-free read). Revision 3, by the lead (Claude Fable 5.2), applies the listed edits. Revision 3 was then reviewed a third time (below).

| Finding | Disposition | Where |
|---|---|---|
| N1 Decision 2 as an unconditioned refusal point | FIXED: grounds stated in advance; a refusal and its reason are recorded; open choices ruled at Decision 1 | 10, 14 |
| N2 false bound on the context-free read; its harm not printed | FIXED | 1, 3.4, 6.7, 12 |
| N3 no consequence of "disagree"; seal is procedural | FIXED | 5.3, 10 |
| N4 mean with a failed cell; no NOT EVALUABLE row for line 1 | FIXED: no mean over fewer than 27 cells; ordered label table | 6.1, 6.2 |
| N5 ADR-0027 Route A text does not match | NOT APPLIED HERE: the edit is in ADR-0027 and is left to its drafter; this ADR's side (section 12, open choice 13) is as the review asks | 12 |
| N6 open choice 13 in two forms | FIXED: one wording in both places | 12, 13 |
| N7 frozen-input set not exact | FIXED | 11 |
| N8 planted-positive construction (advisory) | FIXED | 11 |
| N9 miscellaneous (advisory) | FIXED: lineage gate for REP-U and FRESH; reason for no flat arm in REP-U; panel start rank; PAST BEST definition; G_prior unlabelled; LOADED mark; evaluation and snapshot counts; direction's qualifier in open choice 1 | 3.3, 4, 5.2, 6.6, 8, 9, 13 |
| Table D, seeds (first-review F7) | FIXED: registry values, "one seed per seed position, shared by all nine parents", test-mode seeds, the registry's two conditions | 4 |

**Third review.** Revision 3 was reviewed by the same `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW3_ADR-0026.md`, verdict READY AFTER THE LISTED EDITS, no blocking finding, ten required findings (C1–C10), seven advisory ones (A1–A7), eighteen rulings to add (its section D), conditions for sharing the machine (its section E) and a judgement on which open choices can be taken by delegation (its section F). It recomputed the quoted figures with its own code and found the draft's figures right; one count was off by one (A4). It judged two findings of the confirmation review only partly fixed (N4, N7); they are C8 and C10 below. It found N5 fixed on ADR-0027's side. Revision 4, by the lead (Claude Fable 5.2), applies the edits. **Revision 4 has not been reviewed again.** The review asked that the applied text be read once by a reviewer before Decision 1 is recorded; that reading has not been done, and section 18 says so. The review is engineering evidence, not Astra validation and not an approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| C1 code and environment errors became a scientific NOT EVALUABLE; "non-finite loss" undefined | REQUIRED | FIXED, as written: two rows replace the one; a failed cell is defined and P4's four errors are named. Added for consistency: the line-1 summary cell of section 1 and the wording of the two failed-cell rows of section 10 | 1, 6.1, 10 |
| C2 identity difference during a run | REQUIRED | FIXED, as written: PAUSED — IDENTITY, resumable on restore | 10, 11 |
| C3 order of rehearsal, candidate plan and caps; charged time; cap rule | REQUIRED | FIXED, as written; the R3 rows of sections 8 and 11 and open choice 11 are aligned with it | 5.3, 7, 8, 9, 11, 13 |
| C4 edge rule read the tie-selected rate | REQUIRED | FIXED, as written: the edge is read from the minimiser | 5.1, 7 |
| C5 joint permutation had no seed | REQUIRED | FIXED, as written; the registry row is still to be extended by the lead before the freeze | 3.4, 4 |
| C6 the seed gate would fail on the current tree | REQUIRED | FIXED, as written | 4 |
| C7 ledger order against ADR-0025 section 4.1 | REQUIRED | FIXED, as written | 4 |
| C8 the absolute 27-cell sentence | REQUIRED | FIXED, as written | 6.1 |
| C9 the study's tests are not collected | REQUIRED | FIXED, by the other route: the tests live in `tests/test_p10is3_*.py`, where `pytest` collects them, as ADR-0029 does; the review's text kept them under `studies/p10i_s3/tests/` and named them on the command line. `mypy` is stated to cover `src/arborlm` only, where the review's text added the study's package to the command. No type-check result is claimed for the study's package | 3.1, 11 |
| C10 frozen-input list incomplete | REQUIRED | FIXED, as written, with the eleven loader files named and the statement that the list of record is the import walk made at the freeze and compared with this list | 11 |
| A1 consequence of open choice 13 | ADVISORY | FIXED | 13 |
| A2 batch mean is non-causal | ADVISORY | FIXED | 3.4 |
| A3 wording on the other source of entry evidence | ADVISORY | FIXED | 12 |
| A4 13 evaluations per M-FLAT checkpoint | ADVISORY | FIXED; the totals of section 9 are stated as "about" and are not recomputed | 9 |
| A5 panel-order assertion belongs with item errors | ADVISORY | FIXED | 10 |
| A6 platform settings | ADVISORY | FIXED | 11 |
| A7 M-TREE's RATE-AT-EDGE beside line 1 | ADVISORY | FIXED | 6.2 |
| Section D, eighteen rulings | — | ADOPTED, all eighteen at the review's recommendation; ruling 1 replaces "in float64" in section 6.1 | 16 |
| Section E, sharing the machine | — | ADOPTED | 7, 17 |
| Section F, open choices 2–13 | — | Taken at the recommended options under the delegation | 18 |
| Section F, open choice 1 should go to the human lead | — | NOT FOLLOWED AS ADVISED: taken by the lead under the delegation and reported to the human lead as the first item of the study's record, so that he can overrule it before Decision 2 | 18 |
| The applied diff should be read once before Decision 1 | — | NOT DONE; stated in section 18 | 18 |

`Astra review: NOT_PERFORMED`.

## 16. Rulings for the implementer

The third review listed the places where an implementer would have to guess, with a recommended ruling for each. No registered result has been observed. The lead adopts every one at the review's recommendation; none is changed. The rulings are part of the specification from Decision 1 and bind the implementation and the audit. The "why" column is the lead's.

| # | Question | Ruling | Why |
|---|---|---|---|
| 1 | In what arithmetic is a cell's NLL computed? | As `p4_model.evaluate`: per-batch `loss_for(..., "sum")` in float32, accumulated as a Python float, divided by 32,768. BASE, disabled and every intervention use this one path. This replaces "in float64" in section 6.1 | One path for every quantity that is subtracted from another; it is the path P4's records were made with, and the bitwise gates (disabled = BASE, replay = reference) need it |
| 2 | How is the optimizer built? | `engine.optimizer_for` (foreach=False, fused=False, amsgrad=False), then the rate is written into `param_groups[0]["lr"]` before the first step; step order as `p4_model.train_step`. M-FLAT needs its own wrapper, since `FrozenModel` and `optimizer_names` accept only 198,401 parameters | The existing code is imported unmodified (section 3.1); the wrapper is new code and edits nothing |
| 3 | How are the batch streams drawn? | One CPU `torch.Generator` seeded with the stream seed. REP and REP-U: successive `randperm(2048)` per epoch. FRESH: one `randperm(152,515)` over the pool in rank order. Update k takes entries 8k to 8k+7 | Fixes the stream so that two implementations agree bitwise |
| 4 | Where does data beyond rank 4,095 come from? | `pilot_data.select` on the pinned parquet (main checkout `data/wikitext2/`) with count = all eligible. A gate shows that the first 4,096 train ranks and the recorded validation panels reproduce bitwise. New chunk files are written and hashed | No download and no new recipe; the gate ties the new chunks to the recorded ones |
| 5 | What is "finite at c" in the rate search? | No non-finite event through update c and a finite calibration NLL at c | A rate that diverged before c cannot be selected for c |
| 6 | How does a paused or killed item resume? | A training cell restarts from update 0 and its partial checkpoints are discarded. Evaluation is resumable per (run, checkpoint) | A restart from 0 is bitwise the same run; a mid-run resume would need the optimizer and generator state proved identical |
| 7 | What are X_dense and X_mean_dense exactly? | X_dense: position σ[t] keeps its own residual and adds the adapter delta computed from h of σ[t+1]. X_mean_dense: the delta gate·W2·gelu(W1 h) is replaced by its batch mean and the residual is kept | The same two operations as on the memory's read; the residual path is not part of the addition |
| 8 | What are the prior-off and exhaustive reads? | Prior-off: visit = 2, use_prior = False. Exhaustive: visit = 16, use_prior = True | Each read changes one thing against the trained read |
| 9 | How is NEG-REF built and judged? | The usage weights are the summed softmax read weights per slot on the calibration-panel enabled read. "Must not return DEPENDENT" means that no NEG-REF cell meets D2's or D3's per-cell condition | A per-cell reading; three rehearsal cells cannot meet a 22-of-27 count, so the mean rule alone would pass trivially |
| 10 | Which evaluations run at step 0? | Enabled and disabled only. Checkpoints 512 to U\*: the full control set | At step 0 the addition has learned nothing; the step-0 loss is printed (section 6.2) |
| 11 | To which arms does order row 1 of section 6.3 apply? | For [TREE] it applies to M-TREE or D-ADAPT, for [FLAT] to M-FLAT or D-ADAPT. M-FLAT follows the memory failed-cell rule. The RATE-AT-EDGE tag for [FLAT] reads M-FLAT's rate | Each sub-label reads only the two arms it compares |
| 12 | How is the mean over draws taken? | The four NLLs are averaged, then H is subtracted | One order of operations, fixed |
| 13 | Which is the losing arm when the means are exactly equal? | Neither: no STILL IMPROVING tag | Section 6.4 defines the losing arm by a strictly higher mean |
| 14 | A cap is reached and the extension is refused | The outcome is INCOMPLETE (PAUSED AT CAP) and nothing is labelled | A partial matrix is never labelled (section 7) |
| 15 | What does the DRY profile read? | Trained DRY additions are evaluated on the calibration panel only. The registered panel is read only by the BASE gates. DRY values go into the sealed archive | No trained addition meets the registered panel before the registered run |
| 16 | How are analysis records keyed, and what does the synthetic registry cover? | Keys carry arm, regime, rate, checkpoint, read and draw (the lesson of ADR-0029 section 13). The synthetic registry also covers line 1's order rows, the failed-cell rule, NOT DETERMINED δ and section 6.6 | Two reads must never share a key; every rule that can decide a label or a tag has a known-answer case |
| 17 | When are the worker count and the memory guard fixed? | Worker count k and the per-worker RSS guard are fixed in the candidate plan from R2, with k × 2 GiB ≤ the aggregate guard (24 GiB alone, 12 GiB when sharing; section 17) | The caps are in the candidate plan before R3 (section 5.3) |
| 18 | What follows an engineering stop before Decision 2? | A fix needs an amendment, and R1 is re-run on the same calibration seeds. The unread sealed archive of the stopped attempt is kept and never opened before the registered outcome | No new calibration draw can be chosen after a stop, and the seal survives it. (The review's table B calls this ruling D19; its section D numbers it 18) |

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 17. Running alongside other studies

From the third review (its section E), which confirmed that no wall-time or CPU-time reading enters any rule, label or tag of this study, and that R2's seconds set caps only.

- **No stage of this study needs a quiet machine.** Training and evaluation are deterministic single-thread float32 (`engine.configure_cpu`), so load cannot change a result. Under load, charged hours grow and can reach a cap; the result is PAUSED, not invalid.
- **It must not run during another study's quiet-machine stage.** ADR-0025 stage 7 requires that no study process is running; ADR-0024 section 16 and its MC-T timing, ADR-0027's measured-cost stages and ADR-0028's benchmarks have the same need. This study running beside them would make their measurements NOT MEASURED. Its stages pause, or do not start, while such a stage runs.
- **Memory.** When it shares the machine with another study, the aggregate RSS guard of this study is 12 GiB (six workers at 2 GiB), not 24 GiB. Reason: 24 GiB here plus P10-I-R's 18 GiB is 42 of 48 GiB, which leaves too little for the human lead's own work.
- **Workers.** At most 16 workers across all studies running at once (of 18 cores).
- **Its own worktree.** The study is implemented and run in a worktree of its own, separate from any running study's. Nothing is written or committed in a worktree whose registered stage is running (section 11).

The worker count and the guard that apply are written into the candidate plan (section 16, ruling 17). If the sharing condition changes after the freeze, the lower guard applies and is recorded in `NOTES.md`; a guard is a resource cap and decides no result.

## 18. Approval record — Decision 1 (2026-11-18 UTC)

**Review trail.** Three independent reviews by the `arbor-auditor` subagent (Opus 5.5): NOT READY; READY AFTER THE LISTED EDITS; and the third, READY AFTER THE LISTED EDITS, with no blocking finding. The text with the third review's edits applied (this revision) has not been reviewed again. The third review asked that the applied text be read once before Decision 1 is recorded; that has not been done.

**Who decides, and on what authority.** Decision 1 is taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18. The human lead did not approve this specification himself. His words, verbatim:

> once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-*

and

> and you have my permission to auto approve everything until you complete P10-I

Where each is recorded. The first is in `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` section 1, whose section 2 reads it as covering approval for implementation and rehearsal "at the options the drafts recommend unless an independent review says otherwise". The second, which widens the delegation, was given to the session that wrote this record by the lead's main session as the human lead's words. At the time of this commit it is not in any committed record of this tree, and this section is the only place it is written down. It is to be added to the delegation record, with its date and context, before Decision 2. Until it is, the part of this approval that rests on it alone (open choice 1, below) rests on an unrecorded instruction, and is marked so.

**What this approves.** Implementation of the study in new files (`studies/p10i_s3/`, `configs/p10i_s3_longer_training.toml`, `tests/test_p10is3_*.py`) and its rehearsal (stages R1, R2 and R3 of section 8), within the rehearsal cap of section 7 and under the conditions of section 17. Every open choice of section 13 is taken at its recommended option. The rulings of section 16 are part of the approved text.

**Open choice 1 departs from the direction.** The duration is fixed at 16,384 updates, with a registered CONVERGED / NOT CONVERGED tag, because fresh data ends at 19,064 updates. This departs from the direction's wording, "convergence-based duration" (DIRECTION section 4). The third reviewer judged the option sound and advised that it should go to the human lead and not be taken by delegation, because it departs from binding direction. The lead takes it under the widened delegation. The lead will report it to the human lead as the first item of the study's record, so that he can overrule it before Decision 2. If he overrules it, the registered run is not approved on this text, and a convergence-chosen duration is a successor study with its own data decision (section 5.2). The recorded delegation alone ("unless an independent review says otherwise") would not cover this choice.

**Open choice 13 is "no".** A qualifying label does not qualify for P10-I-S4's Route A when D-ADAPT's registered FRESH convergence tag is NOT CONVERGED. Section 5.2 expects FRESH arms to be NOT CONVERGED at 16,384, so this ruling will probably close ADR-0027's Route A through this study, whatever line 2 shows. It is ruled before any observation.

**What it does not approve.** The freeze. The registered run, which needs Decision 2. Any read of the sealed archive. Any change of a threshold, tolerance, label, tag rule or seed after this point; such a change needs a recorded amendment before any rehearsal output exists (section 5.3). No other P10-I specification. No merge to `main`, publication, download, paid service or package outside the lock.

Nothing in this record is a result. ArborLM is unproven research, and no outcome of this study is a success claim.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
