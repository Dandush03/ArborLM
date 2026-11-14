# ADR-0017 design — evidence inventory (read-only clerk record)

- Date: 2026-11-14. Produced by the clerk role (session model: claude-haiku-5-5, per session metadata). No delegation to another agent is claimed.
- Worktree root: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`. All paths below are relative to this root.
- Repository state at read: branch `claude/adr-0017-design`, HEAD `afd62e5`. The local branch `claude/p8-locality-aware-training` also resolves to `afd62e5`. Untracked: `docs/reviews/adr-0017-design-2026-11-14/` (this file and the draft) and `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` (present, not read, outside this inventory's scope).
- Conventions: `NOT FOUND` = not present in the files read. `derived` = clerk arithmetic on recorded values, with the formula given. Labels are quoted as recorded. Nothing here is interpreted.
- Not done: no training, no simulation, no downloads, no writes except this file. `gh pr view 5` was not run because network calls are outside this clerk's limits. PR #5 state is therefore recorded from local files only (section 7).
- Local integrity check: the two local corpus files were hashed with `shasum -a 256`. `data/wikitext2/train-00000-of-00001.parquet` gave `e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7` and `validation-00000-of-00001.parquet` gave `204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c`. Both match `docs/decisions/ADR-0004-real-data-pilot-prerequisite.md` lines 16–17.

---

## 1. Model and memory constants (P4–P8)

### 1a. Backbone and model

| Item | Value | Source |
|---|---|---|
| Tokenizer / vocabulary | `utf8-bytes-v1`; vocab_size 256 (byte-level) | `src/arborlm/pilot_config.py` lines 41, 53 |
| d_model (width) | 32 | `pilot_config.py` line 50 |
| Blocks (layers) | 2 | `pilot_config.py` line 51 |
| Heads | 4 | `pilot_config.py` line 52 |
| FFN width | 64 (matched dense variant 1588) | `pilot_config.py` lines 55–56 |
| Memory insertion point | after block 0 (`memory_after_block: 0`) | `pilot_config.py` line 57; `docs/decisions/ADR-0009-frozen-backbone-capacity.md` line 36 |
| Context length | 64 | `pilot_config.py` line 54; `configs/p8_locality_training.toml` line 66 |
| Chunk bytes | 65 | `pilot_config.py` line 42 |
| Frozen backbone parameters | 27,392 | `src/arborlm/p4_config.py` line 25; `src/arborlm/p5_config.py` line 27; `configs/p8_locality_training.toml` line 59 |
| Batch | 8 contexts per update; 8 × 64 = 512 target positions per update | `configs/p8_locality_training.toml` lines 65–66; `src/arborlm/p8_core.py` line 90 (`TRAIN_TARGETS = STEPS*BATCH*CONTEXT`) |
| Init std | 0.02 | `configs/p4_frozen_capacity.toml` line 19 |

### 1b. Memory layout (tree and flat)

| Item | Value | Source |
|---|---|---|
| Slots | 4096 | `pilot_config.py` line 58; `src/arborlm/pilot_model.py` line 14 (`SLOTS`) |
| Branches | 16 | `pilot_config.py` line 65; `pilot_model.py` line 14 |
| Slots per branch | 256 | `pilot_model.py` line 14 (`PER_BRANCH`) |
| Visited branches | 2 | `pilot_config.py` line 66 |
| Top-k retrieved | 8 | `pilot_config.py` line 61; `pilot_model.py` line 16 (`TOP = 8`) |
| Temperature | 0.2 | `pilot_config.py` line 62; `pilot_model.py` line 16 (`TEMP`) |
| Key dim | 16 (keys tensor 4096×16) | `pilot_config.py` line 59; `pilot_model.py` line 118 |
| Value dim | 32 (values tensor 4096×32) | `pilot_config.py` line 60; `pilot_model.py` line 119 |
| Query projection wq | 16×32 | `pilot_model.py` line 120 |
| Output projection wo | 32×32 | `pilot_model.py` line 121 |
| Gate | scalar, init −2.0 | `pilot_model.py` line 122; `pilot_config.py` (gate_init −2.0) |
| Router | learned: 16×16 trainable parameter; fixed tree: 16×16 registered buffer (not trainable) | `pilot_model.py` line 124 |
| Normalisation eps | 1e-8 | `pilot_config.py` (normalize_eps); `pilot_model.py` line 16 (`EPS`) |
| Regularizer constants (P8) | BETA 0.25 (soft-inclusion temperature); ALPHA 0.5; GROUP 8; WINDOW 8; LAMBDA_FLOOR 1e-12; SOFT_TOP 64 | `src/arborlm/p8_core.py` lines 98–103; `configs/p8_locality_training.toml` lines 73–78 |
| P8 λ rule (per update) | λ = α·‖g_L,Θ‖ / ‖g_R‖, set to 0 when ‖g_R‖ < floor | `src/arborlm/p8_objective.py` lines 305–306 |

### 1c. ADDITION_PARAMETERS per variant (trainable, per addition)

| Study | Variant | ADDITION_PARAMETERS | Source |
|---|---|---|---|
| P4 | memory (learned tree) | 198,401 | `src/arborlm/p4_config.py` line 25; `configs/p4_frozen_capacity.toml` line 15 |
| P4 | dense adapter | 198,401 | `configs/p4_frozen_capacity.toml` line 15; `docs/decisions/ADR-0009-frozen-backbone-capacity.md` line 40 |
| P5 | baseline | 0 | `src/arborlm/p5_config.py` line 28 |
| P5 | flat | 198,145 | `p5_config.py` line 28 |
| P5 | fixed_tree | 198,145 (plus a 256-element router buffer counted in stored state) | `p5_config.py` line 28; `src/arborlm/p5_model.py` line 302 |
| P5 | learned_tree | 198,401 | `p5_config.py` line 28 |
| P5 | dense | 198,401 | `p5_config.py` line 28 |
| P8 | flat | 198,145 | `src/arborlm/p8_core.py` line 95 |
| P8 | fixed_tree | 198,145 | `p8_core.py` line 95 (fixed-tree variant is listed with flat in the mapping) |
| P8 | learned_tree | 198,401 | `p8_core.py` line 95; `configs/p8_locality_training.toml` line 61 |

Shape check (derived from the tensor shapes in `pilot_model.py` lines 118–124): keys 4096×16 = 65,536; values 4096×32 = 131,072; wq 16×32 = 512; wo 32×32 = 1,024; gate 1. Sum = 198,145 (flat). Adding the 16×16 router (256) gives 198,401 (learned tree).

### 1d. Dense adapter shape

- `h_next = h + sigmoid(g) · W2 · GELU(W1 · h)`. W1 is 3100×32 and W2 is 32×3100, both biasless. Exact GELU. Scalar g init −2.0. Total 3100·32 + 32·3100 + 1 = 198,401.
- Sources: `src/arborlm/p4_model.py` lines 72–76 (`DenseAdapter`, W1 `(3100, 32)`, W2 `(32, 3100)`); `docs/decisions/ADR-0009-frozen-backbone-capacity.md` line 40; `configs/p4_frozen_capacity.toml` line 16 (`dense_width = 3100`).

### 1e. Optimizer and clipping

| Item | Value | Source |
|---|---|---|
| Optimizer | AdamW, fresh, over addition parameters only (backbone absent from optimizer) | `configs/p8_locality_training.toml` line 68 (`optimizer = "fresh-adr0005-AdamW-only-addition"`); `docs/decisions/ADR-0009-frozen-backbone-capacity.md` line 36 |
| lr | 0.003 | `src/arborlm/p5_model.py` line 36 (`ADAMW_OPTIONS`); `pilot_config.py` line 78 |
| betas | (0.9, 0.999) | `p5_model.py` line 37 |
| eps | 1e-8 | `p5_model.py` line 38 |
| weight_decay | 0 | `p5_model.py` line 39 |
| amsgrad / decoupled | False / True | `p5_model.py` lines 40–46 |
| Gradient clip (norm) | 1.0 | `src/arborlm/p5_model.py` line 180; `src/arborlm/p8_objective.py` lines 38, 326; `configs/p8_locality_training.toml` line 79 |

### 1f. Update and target counts per study

| Study | Trained cells | Updates | Targets | Source |
|---|---|---|---|---|
| P1 | 18 runs | 256 per run (derived: 131,072 targets / 512) | 131,072 per run | `docs/RESEARCH_LOG.md` line 64; `pilot_config.py` (`steps: 256`) |
| P2 | 36 runs | 9,216 (derived: 36 × 256) | 4,718,592 | `docs/RESEARCH_LOG.md` line 104 |
| P3-LT | 36 continuations to 1024 | 27,648 added (derived: 36 × 768); 36,864 lifetime (derived: 36 × 1024) | 14,155,776 added; 18,874,368 lifetime | `docs/RESEARCH_LOG.md` line 125 |
| P4 | 54 trained additions (27 memory, 27 dense) | 27,648 (derived: 54 × 512) | 14,155,776 | `docs/RESEARCH_LOG.md` line 147 |
| P5 | 108 trained additions | 55,296 (derived: 108 × 512) | 28,311,552 | `docs/RESEARCH_LOG.md` line 191 |
| P6 | none (inference only) | 0 | 0 | `docs/RESEARCH_LOG.md` lines 204–209; `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md` |
| P7-A | none (trace and simulation) | 0 | 0 | `docs/RESEARCH_LOG.md` lines 221–228 |
| P7-B | none (trace and simulation) | 0 | 0 | `docs/RESEARCH_LOG.md` lines 246–253 |
| P8 | 60 cells (10 cases × 3 backbones × 2 seeds) | 30,720 (derived: 60 × 512); each cell's `steps.jsonl` has 512 records (clerk count) | 15,728,640 (derived: 60 × 262,144) | `results/p8-2026-11-14/train/P8T-20261114T043005466913Z-5da1f4d298534e9390b007efd8d98156/manifest.json` (`counts.completed: 60`); `docs/reviews/p8-results-2026-11-14/README.md` line 12 |
| P8 supplement | none (simulation) | 0 | 0 | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` §10 |

---

## 2. Headline registered outcomes (one line each)

| Study | Outcome with exact numbers | Stated in |
|---|---|---|
| P4 (frozen backbone) | Memory: mean capacity gain C = 0.021988695, disabled effect D = 0.021988695, shuffled-value effect P = 0.022221519; C and P positive in 27/27 runs and 9/9 parent means. Dense adapter mean gain 0.028171332; mean Q (dense minus memory) −0.006182638; dense lower loss in 27/27 matched pairs. Dense tolerance, secondary flag and composite P4 criterion FAILED. Recorded as "bounded frozen-backbone contribution". | `docs/RESEARCH_LOG.md` line 148; `results/p4-2026-11-12/README.md` (opening paragraph) |
| P5 (flat vs fixed tree vs learned tree) | Mean gains: flat 0.022938682, fixed 0.022133329, learned 0.021549867, dense 0.027317625. Usefulness U passed for all three memories. R (learned minus fixed) mean −0.000583461, positive in 10/27 cells and 3/9 parents: FAIL. Flat-quality tolerance Q passed for both trees (26/27 cells, 9/9 parents). Observed score work W = 0.12890625 of flat. Addition latency ratio to flat (geometric mean): fixed 2.603052, learned 2.598485; L criteria FAILED. Composite full-learned-hierarchy criterion FAILED. | `results/p5-2026-11-13/README.md` lines 16–26, 42; `docs/RESEARCH_LOG.md` line 192 |
| P6 (retrieval optimisation and routing fidelity) | P6-E: numerical equivalence PASS for both trees, zero queries selecting a different slot. Speed criteria SP and PAR INCONCLUSIVE; 344 of 1,296 confirmation timing records (26.5%) failed the stability rule (P5: 4 of 612, 0.65%). P6-Q: all four flags FAIL. Recall of exhaustive selection 0.791 (fixed) and 0.915 (learned). Removing the prior: ΔNLL +0.00386 (fixed), +0.00393 (learned), below the registered 0.005. | `docs/reviews/p6-results-2026-11-13/README.md` lines 53, 77, 83; `docs/RESEARCH_LOG.md` lines 208–209 |
| P7-A (storage page locality, simulation) | CONCENTRATION-ONLY. Trees read 34% (fixed) and 48% (learned) fewer cached value pages than frequency-packed flat in the primary setting. A count-preserving null reproduces the gap; effective slot count explains 96.6% of variance in cached misses; 29 of 30 settings degenerate. | `docs/reviews/p7a-results-2026-11-13/README.md` line 27; `docs/RESEARCH_LOG.md` line 225 |
| P7-B (co-access layout equivalence, simulation) | WITHIN 10% OF FLAT CO-ACCESS, replicated on stream A (existing evaluation stream) and stream B (validation ranks 2560–3071), both tree kinds. Primary tree-to-flat ratio of incremental locality: fixed 0.994–0.996, learned 1.024–1.027. Co-access clustering cut flat misses 25% and 41%; branch-constrained co-access cut tree misses 20–22% and 29–34%. | `docs/reviews/p7b-results-2026-11-13/README.md` lines 28–29, 47; `docs/RESEARCH_LOG.md` line 251 |
| P8 (locality-aware training, ten-case pilot) | Study INCOMPLETE: 60/60 trained and evaluated, 55/60 simulated. No case LOCALITY-POSITIVE. Classes: C04 INCOMPLETE; C05 INCOMPLETE; C06 COLLAPSED; C07 CONCENTRATION-ONLY; C08 QUALITY-FAILED; C09 NOT REPLICATED ACROSS PANELS (QUALITY-FAILED on A, COLLAPSED on B); C10 QUALITY-FAILED. Registered decision map output: "none". Every regularised case reduced slots in use by 46–92% (U-ratio 0.076 to 0.539). | `docs/reviews/p8-results-2026-11-14/README.md` lines 14–29, 52–56; `results/p8-2026-11-14/report/analysis.json` key `study_status`, `cells_with_complete_records: 55`, `decision_inputs.section_8_option_indicated: "none"`; `docs/RESEARCH_LOG.md` lines 260–263 |
| P8 supplement (ADR-0016 §10) | 5 of 5 collapsed cells simulated (11.2 s, one worker, peak worker RSS 242 MB). All nine predictions hold (zero counted misses; null equal to actual; E undefined in all five cells). Supplementary, not registered: C04 and C05 QUALITY-FAILED on both panels. Registered P8 study remains INCOMPLETE with decision `none`; the supplement "tested and replicated nothing" (ADR-0016 §10). | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` §10 (outcome record); `results/p8-supplement-2026-11-14/` |

---

## 3. P8 specifics

### 3a. Standard references (scorecard, mean over six cells per panel)

Source: `results/p8-2026-11-14/report/scorecard.csv` (columns `A_n_eff`, `B_n_eff`, `A_distinct_slots`, `B_distinct_slots`); cross-checked against `results/p8-2026-11-14/report/analysis.json`.

| Case | Architecture, objective | N_eff A | N_eff B | Distinct slots A | Distinct slots B |
|---|---|---|---|---|---|
| C01 | flat, standard | 127.06 | 127.68 | 391.33 | 396.33 |
| C02 | fixed tree, standard | 103.18 | 103.51 | 397.50 | 395.00 |
| C03 | learned tree, standard | 83.63 | 83.76 | 312.33 | 308.50 |

### 3b. All ten cases (scorecard)

Source: `results/p8-2026-11-14/report/scorecard.csv`. C04 and C05 U-ratio and ΔNLL cells are blank in the scorecard (see note below).

| Case | Architecture, objective | N_eff A / B | Distinct A / B | U-ratio A / B | ΔNLL A / B | Class A / B / study |
|---|---|---|---|---|---|---|
| C04 | flat, conc | 10.61 / 10.59 | 22.75 / 21.25 | NOT FOUND in analysis.json (review gives 0.076) | NOT FOUND in scorecard (review §3 table, line 40, gives +0.0106 / +0.0100) | INCOMPLETE / INCOMPLETE / INCOMPLETE |
| C05 | learned, conc | 9.66 / 9.65 | 31.00 / 22.33 | NOT FOUND in analysis.json (review gives 0.105) | NOT FOUND in scorecard (review §3 table, line 41, gives +0.0117 / +0.0106) | INCOMPLETE / INCOMPLETE / INCOMPLETE |
| C06 | flat, co | 49.48 / 49.84 | 103.17 / 102.67 | 0.37089 / 0.37184 | 0.00333 / 0.00341 | COLLAPSED (both) |
| C07 | learned, co | 45.63 / 45.78 | 96.33 / 93.00 | 0.53840 / 0.53918 | 0.00093 / 0.00109 | CONCENTRATION-ONLY (both) |
| C08 | flat, temp | 21.63 / 21.60 | 32.83 / 32.67 | 0.17270 / 0.17151 | 0.00420 / 0.00436 | QUALITY-FAILED (both) |
| C09 | learned, temp | 20.91 / 20.89 | 37.67 / 34.83 | 0.25083 / 0.25016 | 0.00409 / 0.00379 | QUALITY-FAILED / COLLAPSED / NOT REPLICATED |
| C10 | learned, co+temp | 20.09 / 20.06 | 27.50 / 27.33 | 0.23854 / 0.23779 | 0.00673 / 0.00620 | QUALITY-FAILED (both) |

Notes:
- U-ratio is defined as the geometric mean over pairs of N_eff,c ÷ N_eff,b (`docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 141). Guard: ≥0.80 retained, 0.50 to 0.80 reduced, <0.50 collapsed (line 150).
- Scorecard C04/C05 means average only simulated cells (`docs/reviews/p8-results-2026-11-14/README.md` §7 item 3). The review's C04/C05 values use all six evaluation cells.
- Derived range for "46–92% fewer": 1 − U-ratio over regularised cases gives 1 − 0.539 = 46.1% (C07, panel B) to 1 − 0.076 = 92.4% (C04, auditor value). With C06–C10 only (recorded in analysis.json), the range is 1 − 0.539 = 46.1% to 1 − 0.1715 = 82.9%.
- Derived N_eff reduction against each case's own architecture baseline (A panel; C01 for flat cases, C03 for tree cases): C04 91.7%, C05 88.5%, C06 61.1%, C07 45.5%, C08 83.0%, C09 75.0%, C10 76.0%.

### 3c. Maximum locality coefficient λ observed (per cell, per update)

Source: each cell's `steps.jsonl` key `lam` (per update) and `train.json` key `summary.lambda`. Clerk scan over all 60 cells, 512 updates each.

| Case | Regularizer key | Max λ | Cell label | Update | Where recorded |
|---|---|---|---|---|---|
| C04 | conc | 393,250.147 | b103-o303-s602-C04 | 512 | steps.jsonl `lam.conc` |
| C05 | conc | 603,648.197 | b101-o301-s602-C05 | 506 | steps.jsonl `lam.conc` |
| C06 | co | 0.170 | b101-o301-s601-C06 | 481 | steps.jsonl `lam.co` |
| C07 | co | 0.275 | b103-o303-s601-C07 | 318 | steps.jsonl `lam.co` |
| C08 | temp | 0.363 | b102-o302-s602-C08 | 469 | steps.jsonl `lam.temp` |
| C09 | temp | 1.502 | b103-o303-s602-C09 | 295 | steps.jsonl `lam.temp` |
| C10 | co | 464,230.126 | b102-o302-s602-C10 | 493 | steps.jsonl `lam.co`; `train.json` `summary.lambda.co.max` |
| C10 | temp | 269,250.169 | b102-o302-s602-C10 | 482 | steps.jsonl `lam.temp`; `train.json` `summary.lambda.temp.max` |

- Global maximum: 603,648.197 (conc, C05). This matches the audit's "6.0·10⁵ (C05)" (`docs/reviews/p8-results-audit-2026-11-14/RESULTS_AUDIT.md` line 238).
- `train.json` `summary.clipped_updates` = 0 in every cell (clerk scan; also `steps.jsonl` key `clipped` false throughout).
- `lambda_zero_event` = false for all updates in all cells (clerk scan of `steps.jsonl`).

### 3d. Margin saturation (8th–9th score gap) and soft mass outside the top eight

Source: `steps.jsonl` key `diagnostics` (`mean_gap_8_9`, `mean_pi_mass_outside_top8`), averaged over the six cells per case (clerk aggregation).

| Case | gap 8–9 at update 1 | at 128 | at 256 | at 512 | π-mass outside top 8 at 512 |
|---|---|---|---|---|---|
| C01 | 0.033 | 0.129 | 0.122 | 0.100 | 4.218 |
| C02 | 0.053 | 0.205 | 0.225 | 0.193 | 1.574 |
| C03 | 0.053 | 0.199 | 0.242 | 0.214 | 1.607 |
| C04 | 0.033 | 2.957 | 5.395 | 6.893 | 0.0331 |
| C05 | 0.053 | 4.720 | 6.804 | 8.537 | 0.0 |
| C06 | 0.033 | 0.250 | 0.891 | 0.992 | 2.727 |
| C07 | 0.053 | 0.494 | 0.791 | 0.917 | 3.194 |
| C08 | 0.033 | 0.254 | 0.139 | 0.080 | 4.232 |
| C09 | 0.053 | 1.283 | 0.982 | 0.793 | 1.238 |
| C10 | 0.053 | 3.161 | 3.096 | 4.128 | 0.209 |

- Per-cell maximum of `mean_gap_8_9` over all updates: C04 8.69, C05 8.76, C10 8.69 (clerk scan).
- The P8 review's "soft mass outside the top eight went to about zero" (`docs/reviews/p8-results-2026-11-14/README.md` line 75) holds for C04 (0.033) and C05 (0.0) at update 512 but not for C10 (0.209). See section 8, item N1.

### 3e. Key movement and gradient reach (per case, mean over six cells)

Sources: `train.json` keys `key_movement_l2`, `router_movement_l2`; `steps.jsonl` at update 512, keys `reach_g_l_key_rows`, `reach_g_r_key_rows`, `reach_g_r_not_hard_selected` (clerk takes the maximum over the case's regularizer keys; the reach fields exist for regularised cases only).

| Case | key_movement_l2 | router_movement_l2 | reach: keys with L-gradient | reach: keys with R-gradient | reach: R-gradient, not hard-selected |
|---|---|---|---|---|---|
| C01 | 9.309 | n/a | 222.0 | n/a | n/a |
| C02 | 9.778 | n/a | 206.3 | n/a | n/a |
| C03 | 8.848 | 1.195 | 161.2 | n/a | n/a |
| C04 | 18.301 | n/a | 11.0 | 887.2 | 877.3 |
| C05 | 11.559 | 0.974 | 9.3 | 324.0 | 317.0 |
| C06 | 12.838 | n/a | 88.0 | 1194.8 | 1106.8 |
| C07 | 13.842 | 1.115 | 76.3 | 1192.5 | 1116.2 |
| C08 | 17.323 | n/a | 25.8 | 1271.8 | 1246.0 |
| C09 | 14.319 | 1.165 | 23.2 | 565.5 | 542.7 |
| C10 | 14.413 | 1.191 | 22.0 | 623.5 | 601.5 |

- `key_movement_l2` is the total key-parameter movement (all key rows). No record separates movement of key rows without a language-loss gradient. The per-step `param_change_l2` keys are `other` and `theta_r` only. Record status for that separation: NOT FOUND.
- Design-level statements: `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 79 ("In C01–C03 unselected keys never move; in regularized cases they do"); line 188 ("Unselected keys move" listed as a limitation); line 122 (gradient-reach definition).
- Pre-freeze probe, initialisation geometry only: `docs/reviews/p8-spec-review-2026-11-14/proxy_checks.out.txt` line 65 ("among unselected rows: 1933"; "rows with any such coordinate: 4096"). Not a trained-cell measurement.
- Adam per-coordinate movement, pre-freeze: `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 79 (3.00·10⁻³ at λ = 1 and 0.1; 2.97·10⁻³ at 0.01).

### 3f. Layout controls and other P8 numbers used in the review

- Arbitrary 16×256 partitions cost 1.5–2.4× co-access in the primary setting (`docs/reviews/p8-results-2026-11-14/README.md` line 79).
- Identity layout m: 0.59 (C06), 0.41 (C07) against 0.34 and 0.21 under co-access clustering (review line 80).
- Temporal reuse actual-to-null ratio 1.00–1.03 for regularised cases; branch-persistence ratio 0.66–0.94 (review lines 60–61).

---

## 4. Measured resources

### 4a. P8

| Stage | Wall (s) | Cap (s) | Workers | Peak worker RSS (bytes) | Peak aggregate RSS (bytes) | Source |
|---|---:|---:|---:|---:|---:|---|
| Training, 60 cells | 392.94 | 5,400 | 4 | 499,220,480 (max of cells `peak_rss_bytes`; review: 0.47 GiB) | 1,925,627,904 | `results/p8-2026-11-14/train/P8T-…/manifest.json` (`stage_wall_seconds`, `settings.workers`, `peak_aggregate_rss_bytes`); cells `train.json` `wall_seconds`, `peak_rss_bytes` |
| Training, per-cell wall sum | 1,382.3 (derived, sum of 60 cells) | — | — | — | — | `train.json` `wall_seconds` |
| Restore gate | passed 10/10 | — | — | — | — | `docs/reviews/p8-results-2026-11-14/README.md` line 144 |
| Evaluation and traces | 105.55 | 1,800 | 4 | 423,690,240 | 1,654,800,384 | `results/p8-2026-11-14/evaluate/P8E-…/manifest.json`; `logs/eval_stage.log` |
| Simulation (55 records, status INCOMPLETE) | 74.43 | 5,400 | 4 | 268,206,080 | 1,051,312,128 | `results/p8-2026-11-14/simulate/P8S-…/manifest.json`. The review table (§8) shows "—" for this stage's peak RSS; the record does contain it (see section 8, item R1). |
| Analysis | 0.996 | 600 | NOT FOUND | NOT FOUND | NOT FOUND | `results/p8-2026-11-14/analysis/P8A-…/manifest.json` |
| Overall active time | about 1 h 45 min of an 8 h limit | 28,800 | — | — | — | `OVERNIGHT_REPORT.md` line 102 |
| Supplement simulation (5 cells) | 11.197 | — | 1 | 242,270,208 | 242,270,208 | `results/p8-supplement-2026-11-14/simulate/P8SUP-…/manifest.json` |
| Supplement analysis | 0.31 | — | — | — | — | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` §10 |

### 4b. Earlier studies

| Study | Stage / total | Wall (s) | Peak RSS (bytes) | Workers | Source |
|---|---|---:|---:|---|---|
| P2 | suite | 321.710 | 676,052,992 (sampled process tree) | NOT FOUND | `docs/RESEARCH_LOG.md` line 104 |
| P3-LT | suite | 871.734423 | 650,657,792 (sampled process tree) | NOT FOUND | `docs/RESEARCH_LOG.md` line 125 |
| P4 | suite worker wall | 652.374330791 | 670,498,816 (sampled process tree) | NOT FOUND | `docs/RESEARCH_LOG.md` line 147; per-cell cap 300 s (`configs/p4_frozen_capacity.toml` line 49) |
| P5 | quality stage | 1,281.554949 (cap 1,800) | 858,423,296 (suite sampled) | NOT FOUND (research log: 36 timing workers) | `results/p5-2026-11-13/README.md` line 72; `docs/RESEARCH_LOG.md` line 191 |
| P5 | active timing | 214.904311 (cap 600) | — | — | `results/p5-2026-11-13/README.md` line 72 |
| P5 | combined active | 1,496.459260 (cap 2,400); 822.690904 s of reporting waits excluded | — | — | `results/p5-2026-11-13/README.md` line 72 |
| P6 | equivalence / screening / confirmation | 411 / 820 / 341 (total 1,572 of 3,000 s cap) | 617 MB (stated) | NOT FOUND | `docs/reviews/p6-results-2026-11-13/README.md` line 69 |
| P7-A | trace stage | 135.331 | 556,466,176 (trace worker `result.json`, maximum found) | NOT FOUND | `results/p7a-2026-11-13/trace/P7AT-…/manifest.json`, `…/result.json` |
| P7-A | simulate stage | 765.953 | 314,064,896 (worker process-tree maximum found) | NOT FOUND | `results/p7a-2026-11-13/simulate/P7AS-…/manifest.json`, `…/workers/*.manifest.json` |
| P7-A | analyze stage | 0.419 | NOT FOUND | — | `results/p7a-2026-11-13/analyze/P7AA-…/manifest.json` |
| P7-B | layouts / trace-b / simulate-a / simulate-b / panel | 710.20 / 180.26 / 1,216.71 / 1,219.98 / 0.46 (total 3,330 of 14,700 s cap) | 578 MB stated; trace-b result 578,256,896 | NOT FOUND | `docs/reviews/p7b-results-2026-11-13/README.md` line 75; `results/p7b-2026-11-13/*/P7B*/manifest.json` and `result.json` |

Timing-reliability records (P6):
- `docs/reviews/p6-results-2026-11-13/README.md` line 53: 344 of 1,296 confirmation records (26.5%) failed the reliability rule; P5 had 4 of 612 (0.65%).
- `docs/reviews/p6-results-2026-11-13/README.md` line 122: "No machine load was recorded during timing."
- `docs/RESEARCH_LOG.md` line 208: "on a machine carrying unrelated load." This conflicts with line 122 (see section 8, item R2).

---

## 5. Data

| Item | Value | Source |
|---|---|---|
| Corpus | WikiText-2 raw, subset `wikitext-2-raw-v1`, revision `b08601e04326c79dfdd32d625aee71d232d685c3` | `data/wikitext2/manifest.json` keys `dataset`, `dataset_subset`, `dataset_revision` (main checkout) |
| Train file | 6,357,543 bytes; sha256 `e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7` | `docs/decisions/ADR-0004-real-data-pilot-prerequisite.md` line 16; `data/wikitext2/manifest.json` `files` |
| Validation file | 657,209 bytes; sha256 `204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c` | ADR-0004 line 17 |
| Test file | 732,610 bytes; NOT acquired; NOT inspected; deferred pending a preregistered final-evaluation decision | ADR-0004 line 18; `data/wikitext2/manifest.json` key `deferred_test` |
| Corpus payload | 7,014,752 selected bytes (7,025,216 downloaded this run); cap 10,000,000 | `data/wikitext2/manifest.json` keys `payload_bytes_selected_total`, `payload_bytes_downloaded_this_run`, `payload_cap_bytes` |
| Licence | Publisher front matter lists CC-BY-SA-3.0 and GFDL; body says CC BY-SA 4.0; both preserved; release rights unresolved | `docs/decisions/ADR-0004-real-data-pilot-prerequisite.md` line 32; `docs/RESEARCH_LOG.md` line 53 |
| Local location | `data/wikitext2/` in the main checkout (`/Users/daniellaloush/dandush03/ArborLM/data/wikitext2`). The directory is NOT present in this worktree. Git-ignored. | `data/wikitext2/manifest.json`; `CLAUDE.md` (Commands section) |
| Checkpoints and traces (P8) | About 460 MB under `experiments/P8*`, local, not published | `OVERNIGHT_REPORT.md` line 111 |
| Chunking | chunk_bytes 65; train chunks 4096; validation chunks 512; deduplicated | `src/arborlm/pilot_config.py` lines 42–45 |
| Rank rule | SHA-256 over `arborlm-pilot-v1:{split}:{row}:{offset}`; rank ordering defines panels | `src/arborlm/pilot_data.py` line 19 |

### 5a. Validation ranks and training ranks used by each study

| Study | Ranks used | Source |
|---|---|---|
| P1 | 512 validation chunks. Explicit rank interval NOT FOUND; P2's text implies ranks 0–511. | `pilot_config.py` line 44; `docs/RESEARCH_LOG.md` line 93 (implied, see section 8, N2) |
| P2 | 512–1023 | `src/arborlm/p2_config.py` line 22; `docs/RESEARCH_LOG.md` line 93 |
| P3-LT | 1024–1535 (new panel) | `src/arborlm/p3_config.py` line 37; `docs/RESEARCH_LOG.md` line 114 |
| P4 | 1536–2047 (validation) | `configs/p4_frozen_capacity.toml` line 24; `src/arborlm/p4_config.py` line 52 |
| P5 | 2048–2559 (validation, 512 chunks) | `configs/p5_hierarchy_ablation.toml` line 27; `src/arborlm/p5_config.py` line 59 |
| P6 | 2048–2559 (primary, the P5 panel). Replication 2560–3071 NOT used. | `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md` line 201; line 262 |
| P7-A | 2048–2559 (evaluation stream) | `src/arborlm/p7a_core.py` line 58 |
| P7-B | Stream A: P7-A evaluation stream (2048–2559). Stream B: 2560–3071 (fresh, used once). | `src/arborlm/p7b_core.py` line 67; `docs/RESEARCH_LOG.md` lines 246–251 |
| P8 | Training 0–2047 (cycle 2048); calibration 2048–2559 (same ranks as P5 and P7-A evaluation); Panel A 3072–3583; Panel B 3584–4095 | `configs/p8_locality_training.toml` lines 82–85; `src/arborlm/p8_core.py` lines 106–109; `src/arborlm/p8_panel.py` lines 48, 50 |
| Unused by P1–P8 as recorded | Validation ranks 3072–4095 are recorded as "unused" before the P8 freeze. Ranks ≥ 4096: NOT FOUND in the records read. | `docs/RESEARCH_LOG.md` line 259; `docs/reviews/p8-results-2026-11-14/README.md` line 12 |

Implication for new synthetic work: none of the recorded P1–P8 validation ranks is needed for synthetic tasks, but any trained-model work that reuses the P8 panels touches ranks 3072–4095 that the P8 study has already scored (see section 8, item N3).

---

## 6. Known-invalid or caveated artefacts (do not reuse without a new check)

| Artefact | Caveat as recorded | Source |
|---|---|---|
| P7-A SSD-index key-read table, tree keys under slot-wise key placement | "invalid": the cache simulator lets the cache exceed capacity when one query needs more pages than the cache holds. No criterion affected. | `docs/reviews/p7a-results-2026-11-13/README.md` §6 (line 78); `docs/RESEARCH_LOG.md` line 227 |
| P7-B null-fit control (L-NCOAX) | "flagged": co-access fitted to a structureless null costs 1.060 (fixed) and 1.036 (learned) in the confirmation setting. Flag present in per-stream records, missing from the combined recommendation text. | `docs/reviews/p7b-results-2026-11-13/README.md` line 71; §8 (line 97) |
| P7-B records | No memory figure for panel and analysis stages; cache-capacity hard check has no record of running; quality reported as per-architecture means only. | `docs/reviews/p7b-results-2026-11-13/README.md` §8 (lines 95–104) |
| P7-A records | Stage manifests record orchestrator thread settings, not worker settings; simulate and analyze manifests record `git_dirty: true`. | `docs/reviews/p7a-results-2026-11-13/README.md` §6 |
| P6 records | 81 P6-E worker manifests and 70 P6-Q manifests carry E0-helper template text (cite ADR-0003, `question_id: G0`, "infrastructure validation only"). Numbers not affected. Stage-level manifests have empty review fields. | `docs/reviews/p6-results-2026-11-13/README.md` §6 (line 118 onward) |
| P6 timing verdicts | INCONCLUSIVE; not an efficiency claim; "Nothing was re-timed". | `docs/reviews/p6-results-2026-11-13/README.md` lines 53, 65 |
| P8 defects 1–12 | Listed in §7 items 1–12 (see 6a). None changes a registered number per the review. | `docs/reviews/p8-results-2026-11-14/README.md` §7 (lines 124–137) |
| P8 concentration controls C04/C05 | Five of twelve cells select the same eight slots on every query; no simulation record; the count-preserving null generator raised an invariant error. | `docs/reviews/p8-results-2026-11-14/README.md` §3.3 (lines 62–66); ADR-0015 §17 (lines 283–284) |
| P8 supplement (ADR-0016) | Supplementary classes are not registered classes. The single-set null rule is "PENDING ASTRA REVIEW". Partial means understated collapse: C04 Panel A distinct slots 22.75 → 17.83, C05 31.0 → 19.5; memory gain C04 0.0154 → 0.0131, C05 0.0139 → 0.0108. | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` §10 |
| P8 supplement, implementer test run | The first full test run showed ten failures in `tests/test_p7b_study.py` that did not reproduce; the log was not kept. | ADR-0016 §10 |
| P8 classes C06–C10 | Accepted "as registered" by the human lead, scope as recorded. Study remains INCOMPLETE. | `docs/reviews/p8-results-2026-11-14/HUMAN_DECISION.md` (answer "yeah"; scope section) |
| P1 promotion gate | FAILED (0.0092854773 vs required 0.01). "do not scale this configuration under this protocol." | `docs/RESEARCH_LOG.md` lines 62–66 |
| P5 composite and R criterion | Composite FAILED; R FAILED; learned routing not shown to beat fixed. | `results/p5-2026-11-13/README.md` lines 24–26 |

### 6a. P8 defects list (`docs/reviews/p8-results-2026-11-14/README.md` §7), short form

1. Stop rule not enforced in the simulation pool (kept launching after first failure). Human has accepted C06–C10 classes (scope in HUMAN_DECISION.md).
2. Registered null generator fails on fully collapsed selections; five cells without simulation.
3. C04/C05 case means in `analysis.json`, `scorecard.csv` and figures average simulated cells only.
4. Where E is undefined, pair and parent counts are written as 0, not null.
5. ADR-0015 §4 "λ is bounded" is wrong operationally (reached about 6·10⁵).
6. Two RSS measurements differ slightly between records (cosmetic).
7. Simulation manifest points at a scratch copy of the P7-B reproduction record; the committed copy matches by hash.
8. Determinable C04/C05 guard results are not in the implementation output.
9. `results/p8-2026-11-14/report/make_report.py` edited after the run (division-by-zero guard); analysis-only tool.
10. Logged reason for a λ = 0 event can be mislabelled (no such event occurred).
11. First launcher line failed on shell quoting before any stage started (`results/p8-2026-11-14/logs/launcher_failed_attempt.md`).
12. Commit messages reduced to single signed lines before push; freeze commit cited as `80f46ae` pushed as `378aeac` (`docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md`).

---

## 7. Open human decisions and governance status

| Item | Recorded status | Source |
|---|---|---|
| ADR-0010 (P5) | SPEC APPROVED BY HUMAN RESEARCH LEAD AND HUMAN-AUTHORIZED CODEX SCIENTIFIC REVIEWER | `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` line 4 |
| ADR-0011 (P6) | SPEC: HUMAN-APPROVED (Fable-drafted) 2026-11-13; executed once | `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md` line 4 |
| ADR-0012 (governance) | "PROPOSAL — PENDING HUMAN RESEARCH LEAD APPROVAL. Not in force." | `docs/decisions/ADR-0012-claude-workflow-governance-amendment.md` line 4 |
| ADR-0013 (P7-A) | SPEC: HUMAN-APPROVED 2026-11-13; executed once | `docs/decisions/ADR-0013-p7a-storage-page-locality.md` line 4 |
| ADR-0014 (P7-B) | SPEC: HUMAN-APPROVED FOR EXECUTION 2026-11-13, revision 4; executed once | `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` line 4 |
| ADR-0015 (P8) | EXECUTED ONCE, 2026-11-14 — STUDY INCOMPLETE (55 of 60 cells simulated); NO CASE LOCALITY-POSITIVE — PENDING HUMAN REVIEW. Astra review: NOT_PERFORMED. | `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 4; §17 lines 279–290 |
| ADR-0016 (P8 supplement) | HUMAN-APPROVED (§9), EXECUTED ONCE on 2026-11-14, COMPLETE (5/5 cells); registered P8 study remains INCOMPLETE with decision `none` | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` line 3; §9 (lines 128–140) |
| Astra review label | NOT_PERFORMED across P4–P8 records | `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 4; `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` §10; `docs/RESEARCH_LOG.md` (P4–P8 entries) |
| Claude-review label | "RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW" | `docs/reviews/p8-results-2026-11-14/README.md` line 3; P6/P7-A/P7-B reviews line 3 |
| Human decisions open, P8 | (1) complete the five missing simulations; (2) direction: stop this line or authorise a new specification; (3) ADR-0012; (4) merge or leave PR #5 as draft | `docs/reviews/p8-results-2026-11-14/README.md` §9 (lines 151–157); `OVERNIGHT_REPORT.md` lines 117–123 |
| Human decisions open, P7-A | Direction (stop; test H3 directly; layout study; larger memory); concentration desirable?; ADR-0012 | `docs/reviews/p7a-results-2026-11-13/README.md` §7 |
| Human decisions open, P7-B | Redesign or stop; test H3 directly; ADR-0012; merging PRs #3 and #4 (merged, see below) | `docs/reviews/p7b-results-2026-11-13/README.md` §9 |
| Draft ADR-0017 §14 decisions | (1) approve final matrices and gates after Opus review; (2) total time/RSS and MPS budget; (3) study-specific delegation, ADR-0012 undecided; (4) external data, teacher weights, paid compute, SSD experiments; (5) merge, publication, capacity expansion | `docs/reviews/adr-0017-design-2026-11-14/ADR-0017-draft-rev0-human.md` lines 136–142 |
| PR #3 (P7-A) and PR #4 (P7-B) | Merged into `main` with merge commits, `8d52862` and `57be5ff` | `docs/RESEARCH_LOG.md` line 257; `OVERNIGHT_REPORT.md` lines 13–15 |
| PR #5 (P8 draft) | NOT VERIFIED from GitHub (network call excluded). Local records: "Draft PR … (draft, not merged)"; "PR #5 remains an unmerged draft" (2026-11-14). Head at the time of writing OVERNIGHT_REPORT: `b78f53840fabf6c02fea3c2bd101a46f2d2c43a7`; the report says the final head is in the PR. | `OVERNIGHT_REPORT.md` lines 23–25; `docs/reviews/p8-results-2026-11-14/HUMAN_DECISION.md` (scope section) |
| Local `claude/p8-locality-aware-training` head | `afd62e5` (local ref; not compared with the remote) | `git rev-parse` in the worktree |

---

## 8. Record discrepancies and items for NEEDS REVIEW

| ID | Statement and record | Status |
|---|---|---|
| R1 | P8 review §8 table shows the simulation peak RSS as "—". The simulation manifest records `peak_worker_rss_bytes` 268,206,080 and `peak_aggregate_rss_bytes` 1,051,312,128. | NEEDS REVIEW (record inconsistency; no number changed) |
| R2 | P6 review line 122: "No machine load was recorded during timing." Research log line 208: timing run "on a machine carrying unrelated load." | NEEDS REVIEW (the two records disagree on whether load was recorded) |
| R3 | P8 review §3.5 (line 75): "soft mass outside the top eight went to about zero" in C04, C05 and C10. Record at update 512: C04 0.0331, C05 0.0, C10 0.209. | NEEDS REVIEW (true for C04 and C05, not for C10) |
| R4 | ADR-0015 line 79: "P5's clipping never activated … and λ is bounded, so neither is a concern." P8 record: λ up to 603,648 (C05) and clipping count 0 in all cells. | NEEDS REVIEW (the review and audit already flag "λ is bounded" as wrong; `docs/reviews/p8-results-audit-2026-11-14/RESULTS_AUDIT.md` line 238) |
| N1 | C04/C05 U-ratios and ΔNLL are absent from `analysis.json` and `scorecard.csv` (blank). They appear only in the review table (auditor's reading). | NOT FOUND in analysis records; values taken from the review §3 table are the auditor's |
| N2 | P1 explicit validation rank interval: NOT FOUND. P2 text implies 0–511. | NOT FOUND (explicit); inferred only |
| N3 | P8 panels cover ranks 3072–4095; P8 calibration (2048–2559) is the same range as the P5 and P7-A evaluation panel. | Recorded facts; relevant to any reuse |
| N4 | Worker counts for P2, P3-LT, P4, P5 quality, P7-A and P7-B stages: NOT FOUND in the manifests checked. P5's research log gives 36 timing workers. | NOT FOUND |
| N5 | Scorecard column `A_n_eff`, `B_n_eff`, `A_distinct_slots`, `B_distinct_slots`: values match the review table (127/128, 103/104, 84/84). | Consistent |
| N6 | Review §2 U-ratio for C08 is 0.172; scorecard A value 0.17270 (rounds to 0.173); B value 0.17151. | Rounding difference only |
| N7 | `docs/reviews/p8-results-2026-11-14/README.md` line 52 says "the regularized memories use 20–50". Scorecard N_eff for regularised cases is 9.7–49.8. | NEEDS REVIEW (C04 and C05 are below 20) |

---

## 9. ADR-0017 draft §1 and §7: statements the records contradict or do not support

Checked against the records in sections 1–8. Quotes are from `docs/reviews/adr-0017-design-2026-11-14/ADR-0017-draft-rev0-human.md`.

| ID | Draft sentence (location) | Record | Classification |
|---|---|---|---|
| C1 | "P4 demonstrated useful sparse memory on frozen backbones." (§1, line 10) | `docs/RESEARCH_LOG.md` line 148: "This establishes bounded frozen-backbone contribution under the registered conditions"; same line: dense adapter "lower loss in all 27 matched comparisons"; "Dense tolerance, the secondary advantage flag, and the composite criterion failed." `results/p4-2026-11-12/README.md`: "The dense tolerance and composite P4 criteria failed." | NOT FULLY SUPPORTED as unqualified. The record's own wording is "bounded" and the composite P4 criterion failed. |
| C2 | "null misses also vanished" (§1, line 10) | `docs/reviews/p8-results-2026-11-14/README.md` §3.1 (line 54): null misses "are 0.00 in every C08, C09 and C10 cell and below the registered 0.05 floor in three of the twelve co-access cells." The other co-access cells are not recorded as zero. | PARTLY SUPPORTED. Vanished for temporal cases; not recorded as vanished for all co-access cells. |
| C3 | "the standard flat and learned-tree references used roughly 127 and 84 entropy-effective slots respectively, and regularized cases used 46–92% fewer" (§1, line 10) | `results/p8-2026-11-14/report/scorecard.csv` (`A_n_eff`, `B_n_eff`); `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 141 defines U-ratio, and 46–92% equals 1 − U-ratio (0.076 to 0.539). Per-case reductions are against each case's own architecture baseline. C04 and C05 U-ratios are not in `analysis.json`. | SUPPORTED WITH CLARIFICATION. The sentence reads as if the 127 and 84 references applied to every case. |
| C4 | "λ that increased to roughly 6×10^5 after the proxy saturated" (§7, line 78) | `steps.jsonl` `lam.conc` for b101-o301-s602-C05 reaches 603,648.197 at update 506. Other maxima: C10 464,230 (co) and 269,250 (temp); C04 393,250 (conc). The figure is one cell's maximum, not a typical value. "After the proxy saturated" is not a separately recorded timing. | SUPPORTED for C05; qualify as a single-cell maximum. |
| C5 | "AdamW updated sparse-key coordinates that had no language-loss gradient" (§7, lines 78–79) | Mechanism stated in `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` line 79. Gradient-reach counts at update 512 (`steps.jsonl` `reach_g_r_not_hard_selected`) are recorded, e.g. C05 mean 317, C10 mean 601.5 (section 3e). No record separates the parameter movement of those key rows; `train.json` `key_movement_l2` is total key movement. ADR-0015 line 188 lists "Unselected keys move" as an unresolved limitation. The pre-freeze probe in `docs/reviews/p8-spec-review-2026-11-14/proxy_checks.out.txt` line 65 was at initialisation geometry. | NOT MEASURED AS RECORDED. Supported by design reasoning and gradient-reach counts only. |

Checked and supported without contradiction (for reference): 127/84 effective slots (`scorecard.csv`); study INCOMPLETE 55/60 with the supplement not changing it (ADR-0016 §10); no case LOCALITY-POSITIVE (`analysis.json` `decision_inputs.locality_positive_cases_both_panels: []`); page misses fall with concentration (`docs/reviews/p8-results-2026-11-14/README.md` §3.1); step-wise gradient-norm matching (`src/arborlm/p8_objective.py` line 306); "P5–P7-B found no compelling advantage" (`docs/RESEARCH_LOG.md` lines 192, 225, 251).
