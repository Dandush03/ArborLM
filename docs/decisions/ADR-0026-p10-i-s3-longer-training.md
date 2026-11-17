# ADR-0026 — P10-I-S3: longer training of the frozen-backbone memory and its dependence on memory

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- Date: 2026-11-17 UTC. Revision 3, after the independent specification review and the confirmation review (section 15). Drafted and revised by the lead (Claude Fable 5.2).
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Direction: `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S3) and section 5 (limits); `LITERATURE_AND_ROUTING_NOTE.md` sections 3 and 5 (duration interaction of the routing gap).
- ArborLM is unproven research. No outcome of this study is a success claim. P1 to P10 are immutable: no result, threshold, seed or outcome of any earlier study is revised, and none is reopened.
- Two points wait for the human lead's ruling and are marked **PENDING HUMAN LEAD RULING**: the fixed duration (section 5.2, open choice 1) and the third data regime (section 3.3, open choice 5).

## 1. Question and outcome lines

P4 trained a 198,401-parameter hierarchical memory on a frozen 27,392-parameter backbone for 512 updates. The memory helped, the help depended on its values, and an equal-size dense adapter did better in every pair. P4 could not say whether 512 updates was the limit. The question here:

**When the same frozen-backbone memory is trained for 16,384 updates, (1) does its contribution depend on which trained value sits at which address, and is it lost under a context-free read, and (2) is it competitive with a dense adapter of equal trainable size that is tuned as carefully?**

Two outcome lines. Each has its own thresholds. Neither substitutes for the other.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| 1. DEPENDENCE | At the primary checkpoint, on unseen single-pass data: at least half of the memory's gain is lost when trained values are reassigned among the slots in use (the gain depends on which trained value sits at which address), and at least half is lost when every position receives the same context-free read (the batch-mean read does not keep the gain; a better constant is not tested). Nothing beyond these two statements. | The memory adds predictive capacity, but most of it survives one of those interventions, or it adds no capacity. | A required cell is missing or failed, or a validity gate failed: NOT EVALUABLE. |
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
- Additions act after block 0 and before block 1, as in ADR-0009. Existing classes and functions are imported unmodified from `src/arborlm/` (`pilot_model.Memory`, `pilot_model.tree_candidates`, `p4_model.DenseAdapter`, `p4_model.Backbone`). No file under `src/arborlm/`, `configs/`, `tests/`, `results/` or `experiments/` is edited. New code goes in `studies/p10i_s3/`; the new config is `configs/p10i_s3_longer_training.toml`.
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
| X_mean: context-free read | M-TREE, M-FLAT | In each evaluation batch the read (the combined vector before W_o) at every position is replaced by its mean over the 512 positions. | Whether the batch-mean read, applied at every position, keeps the gain. It is expected, not guaranteed, to keep between 0 and about C: the mean read is one particular constant passed through the nonlinear block 1, and it can raise the loss above B. B − H_mean is printed per cell with the count of cells in which H_mean > B. It is one context-free read, not the best one. |
| X: query reassignment | M-TREE, M-FLAT | In each evaluation batch a seeded permutation σ of the 512 positions is drawn (64 draws in batch order from one generator per seed); position σ[t] is read with the query of σ[t+1 mod 512]. Mean over 4 seeded draws. | That the read is query-specific. It is a mismatched read, not a context-free one, and it can do harm beyond the loss of the gain. Descriptive only; B − H_x and the count above baseline are printed. |
| X_dense, X_mean_dense | D-ADAPT | The same two operations on the adapter's input positions and on its output. | Descriptive like-for-like figures. Any input-dependent module shows some such effect. |
| Joint key/value permutation within branch | M-TREE | As ADR-0009. NLL must match the enabled reference within 1e-6. | Engineering invariance. |
| Exhaustive read; prior removed | M-TREE | Same checkpoint read through `tree_candidates` with `visit=16`; and with `use_prior=False`. | Retrieval alone, no training change (routing note 5.3 condition 1). |
| NEG-REF | built from each rehearsal M-TREE checkpoint | Every value row replaced by the usage-weighted mean value. The read is the same for every address by construction. | Validity reference: P_all, P_used, X and X_mean must be 0 within 1e-6 and the rule of section 6.2 must not return DEPENDENT. |

"Enabled reference" is the evaluation of the restored checkpoint with no intervention; "replay" is a second such evaluation after a fresh restore, and it must equal the reference bitwise on the platform of record.

**Line 1 is a stricter test than P4's flag 2 and is not comparable with it.** P4 used the all-slot shuffle with no ratio. Any statement about how dependence changes with duration compares P_used and X_mean at this study's own 512-update checkpoint with the same controls at U\*. It is descriptive, and it never uses P4's P.

There is no arm in this natural-text setting whose dependence on memory holds by construction (P10-S1 had R2). In its place: a planted-positive unit test of the intervention code (section 11), NEG-REF, reading line 1 at U\* only, and a synthetic-registry test of the analysis (open choice 7).

## 4. Data, seeds, sizes, checkpoints

**Corpus.** The pinned WikiText-2 acquisition of ADR-0004, byte tokenizer and chunk recipe of ADR-0005. No download, no test split. The recorded pool (`results/p4-2026-11-12/*/dataset_manifest.json`): 156,611 eligible unique train chunks and 16,407 eligible validation chunks.

**FRESH pool.** Train ranks 4,096 to 156,610: 152,515 chunks. A cell's FRESH stream is a seeded permutation of the whole pool; update k (from 0) takes entries 8k to 8k+7. 16,384 updates use 131,072 chunks. **The pool supports at most 19,064 fresh updates.** This design ceiling is why the duration is fixed (section 5.2).

**Panels.** Rule: a panel is the first 512 eligible validation chunks, walking down the ranking from rank 8,192, whose (row, byte span) overlaps no byte span drawn or designated for any panel or window by any earlier study or any P10-I sibling. Earlier chunk panels (P1 to P8, validation ranks 0–4,095) are excluded by rank. Window panels (P10-S2's 144 GEN windows and any other windows it drew from validation; ADR-0025's windows) are mapped to (row, byte-offset) spans by a documented procedure before the comparison. The registered panel is taken first, then the calibration panel. `arbor-clerk` inventories and `arbor-auditor` reconstructs independently; both must reproduce the recorded panel SHA-256 values of P1 to P8. The two panels are written into a ledger that ADR-0025 and ADR-0027 must exclude; whichever study freezes first writes first. If the walk runs out of eligible chunks, the run stops (engineering stop). The walk starts at rank 8,192 only to leave a margin above every earlier chunk panel (ranks up to 4,095); the figure has no other meaning. Each evaluation covers 32,768 targets, as in P4.

**Seeds.** All seeds of this study are new and are assigned in the programme-wide registry, `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` section 4.2, which is the authority; the values below are copied from it. Initialization: registered 330301, 330302, 330303 (seed positions 0, 1, 2); calibration 330391; dry rehearsal 330392; test mode 330398, 330399. Tests: 935001–935999. Streams and permutations: 260001–269999, laid out as in the table. The first proposal for initialization, 2601–2699, collided with P8 (2601 and 2602 are P8's seeds 601 and 602 plus 2000, the offset of the values generator; registry section 5) and was replaced; the first review's statement that it had no overlap was wrong.

Two conditions of the registry bind this study (its section 4.3). (1) The study does not call P4's or P5's permutation helpers (`src/arborlm/p4_model.py:266-270`, `p5_model.py:258-262`), which hard-code 40000 + index … 70000 + index; it uses its own P_all, P_used and X seeds. (2) The freeze gate checks every planned and recorded seed against the registry with derived values expanded (the registry's rules R2 and R3: component seeds such as seed + 1000 … + 5000, and index-derived seeds), read from code and configs, by re-running a copy of the registry checker extended with this study's values. No initialization seed is derived by arithmetic from a data, permutation, calibration, rehearsal or test seed.

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
| Test seeds | 935001–935999 | Never used outside tests |
| Spare | — | 267001–268999 and 269301–269999, unused |

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
- Edge rule (design ceiling with a written extension): if a selected rate is the lowest or highest of the grid, the grid is extended by one half-decade step on that side and the search repeated, at most twice per side. A rate still at the edge is used and tagged RATE-AT-EDGE.
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

**PENDING HUMAN LEAD RULING** (open choice 1): whether a fixed duration with a convergence tag meets DIRECTION section 4 ("a preregistered convergence-based duration"), or whether a larger corpus must be approved first.

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

The rehearsal also runs every registered stage end to end against the frozen plan in a DRY profile (section 11).

## 6. Rules that turn measurements into labels

### 6.1 Quantities and conventions

All losses are next-byte NLL in nats/byte on the registered panel, at U\*, per cell (parent p, seed s), per regime, from the run at the frozen rate for U\*. A cell's NLL is the sum of per-target losses divided by 32,768, in float64. "Mean" is the arithmetic mean over the 27 cells of the per-cell quantity; a parent's value is the mean over its three seeds. Every comparison is ≥ or > exactly as written, with no rounding first.

**Failed cells.** If any of the 27 cells of an arm is a failed cell (section 10: a non-finite loss), every mean condition of that arm in that regime is false, and the failed cell counts as failing every per-cell and per-parent count. No mean is ever computed over fewer than 27 cells. Reason: the alternatives are a mean over the 26 surviving cells, which would hide the failure and could pass, and a NaN, which two implementations treat differently. This rule cannot turn a failure into a pass.

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

A failed M-TREE cell (non-finite loss) is not an integrity case: it falls under the failed-cell rule of section 6.1 and gives NO CAPACITY.

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
| Hour caps: rehearsal 25 h, registered run 48 h, charged time | Resource cap | May be extended by the human lead on cost projections only, never on outcome values. A stage that reaches a cap is PAUSED and resumed; every planned cell still runs. |
| RSS guard 2 GiB per worker, 24 GiB aggregate | Resource cap | Same. |
| U\* = 16,384 | Design ceiling | Fixed. No extension path in this study (section 5.2). |
| FRESH pool: 152,515 chunks, at most 19,064 fresh updates | Design ceiling | Not extended in this study. No chunk is reused in FRESH. |
| Rate grid: five rates | Design ceiling | Extended by the edge rule of section 5.1, at most two steps per side. |
| Rate tie tolerance 0.0005; PAST BEST margin 0.005 | Design ceiling | Fixed; they decide a rate or a tag, never a label. |
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
| R3 rehearsal: DRY run of every registered stage on the frozen plan | Minutes | None | — |
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
| Evaluation: about 16 evaluations per M-TREE checkpoint, 12 per M-FLAT, 8 per D-ADAPT (enabled, replay, disabled, four X_dense draws, X_mean_dense); about 10,400 evaluations for the primary runs, up to about 20,000 with per-duration and anchor runs; the exhaustive read is slower than 0.5 s | — | about 1.5 h to 3.5 h |
| **Registered total** | 216 to 918 | **about 16 h to 32 h** |

Order of magnitude for the whole study: 26 to 48 hours of single-thread compute. Parallel workers shorten wall time; the rehearsal measures by how much. The caps (25 h and 48 h) are the worst-case totals times about 1.5. Checkpoint storage: about 2.4 MB per snapshot with optimizer state (arithmetic from the parameter count, not measured), at most about 4,400 snapshots by the confirmation review's count (the lead's earlier 5,700 was not reproduced and is withdrawn), so up to about 11 GB and more likely 4 to 8 GB. If the rehearsal projects more than a cap, the lead returns to the human lead before Decision 2 with the projection; the matrix is not cut.

The rehearsal measures: seconds per update per arm, rate and regime; seconds per evaluation, including the exhaustive read; the parallel slowdown; storage per snapshot; the number of distinct rates in the rate table, which fixes the per-duration and anchor rows.

## 10. Stop rules and NOT EVALUABLE

| Event | Consequence |
|---|---|
| A gate fails before training (section 8, stage G), including the prefix-identity, read-equality and planted-positive gates | Engineering stop. No registered cell is observed. A fix needs a re-freeze and the human lead's approval of a new attempt. |
| The panel walk runs out of eligible chunks; or no finite rate exists for some (arm, regime) in calibration | Engineering stop before Decision 2. |
| The auditor reports "disagree" on `rehearsal_public.json` and reconciliation fails (section 5.3) | Engineering stop before Decision 2. |
| The rehearsal's cost projection exceeds a cap and the human lead declines an extension | The study is not run. This is recorded before Decision 2. Together with the engineering stops of this table it is the only ground stated in advance for not running; a refusal on any other ground is recorded as in section 14. |
| A stage reaches a resource cap | PAUSED. Resumed after an extension decided on projections only. Completed cells are not recomputed. |
| BASE is missing or fails its bitwise replay on a parent | Every line is NOT EVALUABLE in every regime. |
| A registered run of a memory arm has a non-finite loss | The cell is kept as failed and counts as failing every condition of its arm. Nothing is rerun at another rate. |
| A registered D-ADAPT run for U\* has a non-finite loss | Line 2 is NOT EVALUABLE in that regime. |
| Any other required cell or evaluation is missing after the run ends | The lines that need it are NOT EVALUABLE in that regime. Denominators are never reduced. |
| Disabled ≠ BASE, replay ≠ enabled reference, or joint permutation outside 1e-6 on any cell; or S computed in a panel order different from the enabled read | Integrity failure; the affected arm and regime is NOT EVALUABLE. |
| mean C_dense < 0.005 | Line 2 is NOT EVALUABLE in that regime (section 6.3, order 2). |

The registered run happens once. A negative or inconclusive label is a registered outcome. It is not a reason to add updates, seeds, rates or cells.

## 11. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| P10-S1 attempt 1 was lost to a commit of a status note into a frozen input (ADR-0021 sections 25.19–25.20) | **The frozen-input set is exactly:** (1) every file under `studies/p10i_s3/`, which holds the code, the tests of this study (`studies/p10i_s3/tests/`, including the planted-positive and synthetic-registry tests), `freeze/plan.json`, `freeze/rate_table.json`, the seed plan and the extended seed checker (`freeze/seed_plan.json`, `freeze/seed_registry_check.py`) and the panel identities; (2) `configs/p10i_s3_longer_training.toml`, which carries every threshold, tolerance, grid and margin of sections 5, 6 and 7 (ε, the rate grid, the 0.0005 tie tolerance, the edge rule, the PAST BEST margin, the 1e-6 tolerances, the LOADED mark, all thresholds of section 6); (3) `rehearsal_public.json` and the sealed file's SHA-256; (4) the shared panel ledger by SHA-256; (5) by SHA-256, the `src/arborlm/` files `pilot_model.py`, `model.py`, `pilot_config.py`, `pilot_data.py`, `fetch_wikitext.py`, `io.py`, `p4_model.py`, `p4_config.py`, `p2_model.py`, `engine.py`, `longer_training.py`, `pilot_metrics.py`, and any further file an import walk from these finds, each listed by name in `plan.json`; (6) `uv.lock`; (7) the nine parent checkpoint hashes and the data hashes. Identity is checked by file hash, not by the commit at HEAD. **This ADR and everything else under `docs/` and `results/` are not run-time inputs.** This ADR's SHA-256 at Decision 1 and at Decision 2 is recorded in `plan.json`, so that the audit can compare the code with the approved text; any later edit of the ADR is an amendment with a record. No commit is made in the run's worktree while a registered stage runs. Status goes to chat or to `NOTES.md` in the git-ignored run directory. Every stage is resumable per cell or task. |
| P10-S1's throughput stage asked for a cell the frozen plan did not run (section 25.21) | Every registered stage reads its item list from `plan.json` only, and stage R3 runs each of them end to end on the frozen plan before Decision 2. Tests use that plan, not a separate one. |
| P10-S1's audit: an unstated aggregation rule, a dependence condition that misfires early, a descriptive section that compared the wrong reads | Every combination and precedence rule is in section 6. Line 1 is read at U\* only. The analysis, including sections 6.6 and 6.7, is tested on a synthetic registry with known answers: one case per label, per tag and per order row of section 6.3, and a case where two arms' reads are swapped and the test must fail. |
| No arm with dependence by construction (review F11 a) | **Planted-positive test.** A toy frozen backbone and a memory whose values are set so that each slot gives the exact correction for a disjoint set of queries. The planted corrections are built with zero mean across each evaluation batch, since otherwise the batch-mean read would keep part of the gain. On it P_used, X and X_mean must each be ≥ 0.5·C and NEG-REF must give 0. It runs in the test suite and as a gate. |
| "One run serves every duration" was assumed (F11 b) | **Prefix-identity gate.** On the platform of record, a separate 512-update run is bitwise equal to checkpoint 512 of the 16,384-update run, for each arm and regime on one calibration cell. |
| The interventions need a re-implemented read (F11 c) | **Read-equality gate.** With no intervention, the study's read equals `Memory.forward` bitwise for both variants; the exhaustive read equals `tree_candidates(visit=16)`, the path P6 used. |
| P10-S2 stopped on a count gate although quality criteria were met | Counts that are not claims are met by rule: the panels by walking the ranking, the rate grid by the edge rule. |
| P10-S0 tested one load and one training length | Three data regimes and four evaluated durations; the duration is fixed for the reason given in section 5.2 and tagged for convergence. |
| A test passed on macOS and failed on Linux (section 25.23) | Platform of record: macOS arm64, Apple M5 Max, Python and PyTorch as in `uv.lock`. Bitwise assertions are made on it only; elsewhere the same checks use a 1e-6 tolerance. |
| GitHub CI is costly | `uv run --locked ruff check .`, `mypy` and `pytest` run locally. No CI run is required by this study. `uv.lock` and `pyproject.toml` do not change. |

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

Both clauses must hold, for M-TREE. Whether a qualifying label still qualifies when D-ADAPT's registered FRESH convergence tag (section 5.2, last bullet) is NOT CONVERGED, whichever arm is losing, is the human lead's choice (open choice 13), ruled at Decision 1. The lead asks that ADR-0027 copy these names and drop the phrase "within S3's own margin".

| Line 2 result | What it would mean | What it would not mean |
|---|---|---|
| COMPETITIVE or MEMORY AHEAD | Evidence the human lead may weigh for S4 entry: at matched trainable size and matched updates, with both sides rate-searched, the memory is within tolerance on unseen single-pass data of this task. | Not a cost result. S4's primary comparison is at matched training computation, where the per-update cost counts against the memory. Not evidence at any larger store or model. Not an entry decision; that is the human lead's. |
| NOT COMPETITIVE, both arms CONVERGED | S3 supplies no entry evidence. The P4 pattern holds at 16,384 updates in this setting. | Not a statement about larger stores, where a dense alternative must grow with the store, and not a revision of P10-S1, which remains the other route the direction names (its registered label is DENSE AHEAD; the matched-compute observation at 32K/16K is an audit disclosure). |
| NOT COMPETITIVE "(MEMORY STILL IMPROVING)", or INCONCLUSIVE | No entry evidence, and no evidence against. | Not a reason to extend this study. |

COMPETITIVENESS[FLAT] is shown beside the headline in every case. A flat memory that is competitive where the tree is not points to the routing work of ADR-0029 (P10-I-R), not to S4.

## 13. Open choices reserved for the human lead

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
11. **Caps**: 25 h rehearsal, 48 h registered run, 24 GiB aggregate RSS. Recommendation: as drafted, replaced by the rehearsal's projection at Decision 2.
12. **P4-rate anchor** (section 6.7): up to 4.4 h. Recommendation: keep; without it, rate selection and duration cannot be told apart in the 512-update comparison.
13. **Convergence and S4 entry** (section 12): does a qualifying label still qualify when D-ADAPT's registered FRESH convergence tag (section 5.2, last bullet) is NOT CONVERGED, whichever arm is losing? Recommendation: no; a dense arm that is still improving may overtake. Ruled at Decision 1, before any observation; ADR-0027 copies the ruling.

## 14. Decisions and approval record

- Decision 1 (human lead): approve this specification for implementation and rehearsal only. Every open choice of section 13 is ruled at Decision 1, before the rehearsal. **Not given.**
- Decision 2 (human lead): after the rehearsal, with `rehearsal_public.json`, the auditor's agree or disagree, the cost projection and the freeze record, approve the single registered run. **Not given.**
- Grounds stated in advance for not running after Decision 1: an engineering stop of section 10, or a cost projection over a cap that the human lead declines to extend. This ADR cannot bind the human lead. If Decision 2 is refused on any other ground, the refusal and its reason are recorded in this ADR before any sealed file is opened, and the study's outcome is recorded as NOT RUN (DECISION 2 REFUSED: reason). The sealed file is then published with that record, opened by no one before the record is written.

No approval is recorded. `Astra review: NOT_PERFORMED`.

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

**Confirmation review.** Revision 2 was reviewed by the same `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW2_ADR-0026.md`, verdict READY AFTER THE LISTED EDITS, no blocking finding. It recorded two errors of the first review that revision 2 had copied (the seed "no overlap" statement and the bound on the context-free read). Revision 3, by the lead (Claude Fable 5.2), applies the listed edits. Revision 3 has not been re-reviewed.

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
