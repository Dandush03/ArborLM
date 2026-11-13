# P7-B spec inputs: validation and training-pool rank usage (panel_usage)

- Generated: 2026-11-13. Run by the evidence clerk role as a Claude Code session, model `claude-haiku-5-5`. No subagent delegation.
- Branch snapshot: `claude/p7b-coaccess-layout-proposal`, last commit `8480853`.
- Status: evidence inventory only. It records what the listed sources state. It is not an approval, a gate decision or a scientific interpretation. No training, evaluation, network call, trace binary or `data/` file was opened.
- Machine-readable copy with every occurrence: `docs/reviews/p7b-spec-inputs-2026-11-13/panel_usage.json`.
- Scratch scripts used for the sweep are in `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM/c47a0921-2b26-427b-b887-15fe3547efa1/scratchpad/` (`scan.py`, `sweep.py`, `bounds2.py`, `keys.py`, `final.py`, `build.py`).

Ranks are zero-based. Intervals are written as [start, end) unless the source states otherwise. See NEEDS REVIEW 1.

## 1. Validation and training-pool ranks by study (item 1)

| Study | Validation ranks | Training-pool ranks | Panel SHA-256 (source) |
|---|---|---|---|
| P1 | [0, 512): 512 validation chunks, first ranked (derived, NEEDS REVIEW 2) | pool 4096 ranked; rows consumed [0, 2048) (derived, NEEDS REVIEW 2) | `2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200` (results/p1-2026-11-12/dataset_manifest.json) |
| memory diagnostic (P1DIAG) | same frozen file as P1, [0, 512) by inheritance (NEEDS REVIEW 3) | none (zero training targets) | `2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200` (results/memory-diagnostic-2026-11-12/seed-42/disabled/dataset_manifest.json) |
| P2 | [512, 1024) | [0, 2048) of 4096 ranked | `8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2` (results/p2-2026-11-12/b101-o301-control/dataset_manifest.json) |
| P3-LT | [1024, 1536) | [0, 2048) of 4096 ranked | `a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0` (results/p3-lt-2026-11-12/b101-o301-control/dataset_manifest.json) |
| P4 | [1536, 2048) | [0, 2048) | `4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f` (results/p4-2026-11-12/b101-o301-baseline/dataset_manifest.json) |
| P5 | [2048, 2560) = ranks 2048..2559 | [0, 2048) | `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98` (results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json) |
| P6-E | P5 panel [2048, 2560) by ADR and code only (NEEDS REVIEW 4) | none stated (inference-only) | not found in P6-E records |
| P6-Q | [2048, 2560) = P5 primary panel only | none stated (inference-only) | `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98` (results/p6-q-2026-11-13/cells/b101-o301-fixed_tree-s501-final/result.json, panel.sha256) |
| P7-A | evaluation [2048, 2560) = P5 panel (NEEDS REVIEW 5) | calibration [2048, 2560) of training pool; training used 0..2047 | not found in P7-A records |
| E0 (not requested) | synthetic validation rows (seed 202, 64 rows); no corpus ranks | synthetic | n/a |

### 1.1 Quoted sources per study

**P1**
- `configs/p1_ram_screen.toml:12` `validation_chunks = 512`; `:11` `train_chunks = 4096`.
- `results/p1-2026-11-12/config.resolved.json` (one-line JSON): `"train_chunks":4096`, `"validation_chunks":512`.
- `src/arborlm/pilot_data.py:80` `return ranked[:count], set(by_digest), counts`.
- `docs/decisions/ADR-0005-ram-pilot-spec.md:23` "After exclusions, take first 4096 train and 512 validation chunks".
- Consumed rows (derived): `src/arborlm/pilot_config.py:23` `STEPS, BATCH_SIZE, TRAIN_ROWS, VAL_ROWS = 256, 8, 4096, 512`; `src/arborlm/pilot.py:242` `start_row = (step - 1) * BATCH_SIZE % TRAIN_ROWS`. 256 x 8 = 2048 rows.
- SHA-256 field: `results/p1-2026-11-12/dataset_manifest.json` `checksums_sha256.validation.bytes`.

**Memory diagnostic (P1DIAG)**
- `docs/decisions/ADR-0006-frozen-memory-diagnostic.md:10` "Use exactly the three final learned-tree checkpoints and frozen validation chunks in `experiments/P1-20261113T023302942989Z-…`".
- `results/memory-diagnostic-2026-11-12/README.md:25` "Every condition used 32,768 validation targets with zero training targets."
- `experiments/P1DIAG-20261113T024308074540Z-ace5d3680604461a8f1e9bea48f466f0/cells/P1DIAG-20261113T024308256323Z-7e1dad7b8c16465188b6934426d09059/parent_config.resolved.json`: `validation_chunks` 512, `train_chunks` 4096 (not a rank interval).
- SHA-256: `results/memory-diagnostic-2026-11-12/seed-42/disabled/dataset_manifest.json` `checksums_sha256.validation.bytes` = `2e6b71b9…2200` (same as P1).

**P2**
- `configs/p2_optimization_followup.toml:12` `validation_rank_interval = [512, 1024]`; `:13` `train_rank_interval = [0, 2048]`; `:14` `train_ranked_chunks = 4096`.
- `results/p2-2026-11-12/b101-o301-control/config.resolved.json`: `"validation_rank_interval":[512,1024]`, `"train_rank_interval":[0,2048]`.
- `results/p2-2026-11-12/b101-o301-control/dataset_manifest.json`: `measured_ranks` [512, 1024]; `checksums_sha256.validation.bytes` `8cd4ab927f9f…455cd2`.
- `src/arborlm/p2_config.py:22` `VAL_START, VAL_END, TRAIN_SEEN, TRAIN_RANKED = 512, 1024, 2048, 4096`.
- `docs/decisions/ADR-0007-controlled-optimization-followup.md:24` "reserve ranks **512 through 1023 (zero-based)** as P2's sole measured panel".

**P3-LT**
- `configs/p3_longer_training.toml:10` `ranked_train = 4096`; `:11` `used_train = 2048`; `:13` `validation_ranks = [1024, 1536]`.
- `results/p3-lt-2026-11-12/b101-o301-control/config.resolved.json`: `"validation_ranks":[1024,1536]`, `"ranked_train":4096`, `"used_train":2048`.
- `results/p3-lt-2026-11-12/b101-o301-control/dataset_manifest.json`: `"scientific_panel_ranks":[1024,1536]`; SHA `a2d63d4e…724b0`.
- `results/p3-lt-2026-11-12/b101-o301-control/order.json`: `"rank_interval":[0,2048]`.
- `src/arborlm/p3_config.py:21` `VAL_START, VAL_END = 1024, 1536`.

**P4**
- `configs/p4_frozen_capacity.toml:23` `train_ranks = [0, 2048]`; `:24` `validation_ranks = [1536, 2048]`.
- `results/p4-2026-11-12/b101-o301-baseline/dataset_manifest.json`: `"scientific_panel_ranks":[1536,2048]`; SHA `4c6fb3f3…dc28f`.
- `results/p4-2026-11-12/b101-o301-baseline/config.resolved.json`: `"train_ranks":[0,2048]`, `"validation_ranks":[1536,2048]`.
- `docs/decisions/ADR-0009-frozen-backbone-capacity.md:50` "Fresh sole P4 scientific validation panel: eligible validation ranks **1536..2047**, zero-based".
- `src/arborlm/p4_data.py:24` `VAL_START, VAL_END = 1536, 2048`.

**P5**
- `configs/p5_hierarchy_ablation.toml:26` `train_ranks = [0, 2048]`; `:27` `validation_ranks = [2048, 2560]`.
- `results/p5-2026-11-13/b101-o301-baseline/config.resolved.json`: `"train_ranks":[0,2048]`, `"validation_ranks":[2048,2560]`.
- `results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json`: `"scientific_panel_ranks":[2048,2560]`; `checksums_sha256.validation.bytes` `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`.
- `docs/decisions/ADR-0010-hierarchical-memory-ablation.md:79` "Proposed sole scientific validation panel: eligible ranks **2048..2559**, zero-based, under the existing recipe."
- `results/p5-2026-11-13/README.md:66` "The fresh panel comprises 512 eligible chunks at ranks 2048–2559".
- `docs/RESEARCH_LOG.md:170` "PASS: 512 chunks at ranks 2048..2559".
- `src/arborlm/p5_data.py:26` `VAL_START, VAL_END = 2048, 2560`; `src/arborlm/p5_config.py:59` `"validation_ranks": [2048, 2560],`.

**P6-E** (equivalence stage; inference only on P5 checkpoints)
- `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md:42` "…on the P5 panel (ranks 2048–2559, SHA-256 `d50cbe4c…72b98`)…".
- `src/arborlm/p6_equivalence.py:5` "1. replays the unmodified model on the P5 panel and requires the registered final NLL bitwise,".
- `docs/RESEARCH_LOG.md:201` "…two separately scoped inference-only studies on the frozen P5 checkpoints…".
- Records (`results/p6-e-2026-11-13/`, `experiments/P6EANA-`, `P6ECON-`, `P6EEQ-`, `P6ESCR-`): no rank interval and no SHA-256 found (NEEDS REVIEW 4).

**P6-Q**
- `results/p6-q-2026-11-13/suite/manifest.json` and `experiments/P6Q-20261113T180439281981Z-fdc287dd79274cfd962ab29fbffd1087/manifest.json`: `"panel":"P5 primary panel only (ranks 2048-2560); replication panel not approved"`.
- `results/p6-q-2026-11-13/cells/b101-o301-fixed_tree-s501-final/result.json`: `"panel": {"queries": 32768, "ranks": [2048, 2560], "sha256": "d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98"}`.
- `src/arborlm/p6_fidelity_study.py:382` `"ranks": [2048, 2560],`; `:556` `panel="P5 primary panel only (ranks 2048-2560); replication panel not approved"`.

**P7-A** (trace, simulate and analyze stages)
- `results/p7a-2026-11-13/trace/P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e/checkpoints/b101-o301-fixed_tree-s501.json`: `"evaluation_stream":{"contexts":512,"ranks":[2048,2560],"split":"validation"}`; `"calibration_stream":{"contexts":512,"ranks":[2048,2560],"split":"training pool"}`.
- `docs/decisions/ADR-0013-p7a-storage-page-locality.md:53` "Evaluation stream: the P5 panel, validation ranks 2048–2559 in rank order (512 contexts, 32,768 queries)."
- `docs/decisions/ADR-0013-p7a-storage-page-locality.md:54` "Calibration stream: ranked training-pool chunks 2048–2559 (512 contexts). Neither the additions nor the frozen backbones trained on these ranks (training used ranks 0–2047)…".
- `src/arborlm/p7a_core.py:57-58`: `CAL_START, CAL_END = 2048, 2560  # training-pool ranks used only to fit layouts`; `EVAL_RANKS = (2048, 2560)`.
- `docs/reviews/p7a-preflight-2026-11-13/AUDIT.md:110`: evaluation = P5 `validation.bytes` (ranks 2048–2559).
- P7-A records state no panel SHA-256 (NEEDS REVIEW 5).

## 2. Occurrence classification (item 2)

Searched: the spec sources listed in item 1 of the brief, plus the extension sources noted in NEEDS REVIEW 8. Whole-token matches of 2560, 2561, 3071, 3072 were taken from all searched lines. Range and symbol patterns (`2560..3071`, `2560–3071`, `2560-3071`, `ranks 2560`, `VAL_END`, `VAL_START`) and validation-context bounds with an upper value of at least 2560 were added. The 2048–2559 range form was also recorded as class (a) because it is the other end of the same convention.

- Token matches: 7543 across the searched files, in 4484 lines (classes below).
- Lines by class: **(a) 935**, **(b) 7**, **(c) 3542**.
- Substring-only matches (for example inside hex hashes) are not occurrences and are excluded: 7748 lines in 1510 files (JSON, `sub_files_substring_only`).

### 2.1 Class (b): ranks 2560–3071 named as PROPOSED or DECLINED (all 7 lines)

- `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md:201`: "te (i). Replication, subject to separate human approval (§6, question 6): eligible validation ranks 2560–3071 under the existing recipe, reconstructed and independently audited for overlap exactly as "
- `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md:251`: "6. Approve or decline use of fresh validation ranks 2560–3071 as a P6-Q replication panel. Declining leaves P6-Q on the already observed P5 panel only."
- `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md:262`: "- **§6 item 6, replication panel.** The draft made fresh validation ranks 2560–3071 "subject to separate human approval". A general instruction to proceed is not treated as that separate approval. **T"
- `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md:16`: "d chose to run it **with a prospective replication on a fresh evaluation stream** (validation ranks 2560–3071), which nobody has looked at. Revision 3 makes that replication part of the registered stu"
- `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md:174`: "- **Stream B — prospective replication.** Validation ranks 2560–3071 under the existing panel recipe: 512 contexts that no ArborLM study has evaluated. Its traces are generated with the frozen P7-A tr"
- `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md:176`: "committed record and local manifest is searched for any earlier use of validation ranks at or above 2560. The clerk role's inventory of rank ranges used by every prior study is `docs/reviews/p7b-spec-"
- `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md:285`: "- "My preferred direction is **option (b): existing evaluation stream plus a prospective replication on validation ranks 2560–3071**.""

Status for these lines: the replication panel was declined in ADR-0011 (line 262: "The replication panel is not used."). ADR-0014 is a draft that is NOT APPROVED (line 4).

### 2.2 Class (a): human-authored sources (every line)

| File | Line | Quoted line (≤200 chars) |
|---|---|---|
| `configs/p5_hierarchy_ablation.toml` | 27 | validation_ranks = [2048, 2560] |
| `docs/RESEARCH_LOG.md` | 159 | h shared seeds 501–503, unchanged 512-update optimization, a new panel at eligible validation ranks 2048–2559, and fresh dense-adapter training under the same protocol: 117 cells, 108 trainings, 333 s |
| `docs/RESEARCH_LOG.md` | 170 | pshots against P3 tensor bytes without ArborLM imports or model forwards. PASS: 512 chunks at ranks 2048..2559, hash `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`, no exact prior- |
| `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` | 79 | Proposed sole scientific validation panel: eligible ranks **2048..2559**, zero-based, under the existing recipe. P4 records 16,407 eligible validation chunks, so this interval is available according t |
| `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` | 227 | 3. Use new panel ranks 2048..2559, global paired permutation for flat, branch-preserving paired permutation for trees, and the explicit 612+9 evaluation budget. |
| `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md` | 42 | odified model must reproduce that cell's registered P5 final NLL **bitwise** on the P5 panel (ranks 2048–2559, SHA-256 `d50cbe4c…72b98`) in the matched environment. A mismatch stops the study for engi |
| `docs/decisions/ADR-0013-p7a-storage-page-locality.md` | 53 |   - **Evaluation stream:** the P5 panel, validation ranks 2048–2559 in rank order (512 contexts, 32,768 queries). |
| `docs/decisions/ADR-0013-p7a-storage-page-locality.md` | 54 |   - **Calibration stream:** ranked training-pool chunks 2048–2559 (512 contexts). Neither the additions nor the frozen backbones trained on these ranks (training used ranks 0–2047), and they are disjo |
| `docs/decisions/ADR-0013-p7a-storage-page-locality.md` | 231 | 6. Approve the calibration stream (training-pool ranks 2048–2559) for fitting layouts. |
| `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` | 51 | - **Streams.** Calibration: training-pool ranks 2048–2559 (never trained on). Evaluation: the P5 panel, validation ranks 2048–2559. Contexts are unrelated 64-byte windows. |
| `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` | 173 | - **Stream A — existing.** The P7-A evaluation traces (validation ranks 2048–2559). Held out from layout construction but already seen under other layouts (§3). |
| `docs/reviews/p7a-preflight-2026-11-13/AUDIT.md` | 90 | ource guard (M1), the frequency-matched degenerate path (M3), and the real-path slicing `train[2048:2560]` / `shape[0] == 4096` (`p7a_study.py:103-105`), which is untested apart from the loader-smoke  |
| `docs/reviews/p7a-preflight-2026-11-13/AUDIT.md` | 110 | e.panel` = P5 `validation.bytes` (ranks 2048–2559, `p5_data.py:59, 166`). Calibration = `train[2048:2560]` of the 4,096 ranked chunks (`p7a_study.py:103-105`). Training used ranks 0–2047 (`p5_config.p |
| `docs/reviews/p7a-spec-review-2026-11-13/REVIEW.md` | 254 | - **m9 (§3 calibration).** The draft says the *additions* never trained on ranks 2048–2559. The registered configs show the backbones never did either: P2 `train_rank_interval [0, 2048]`, P3 `used_tra |
| `src/arborlm/p5_config.py` | 59 |         "validation_ranks": [2048, 2560], |
| `src/arborlm/p5_data.py` | 26 | VAL_START, VAL_END = 2048, 2560 |
| `src/arborlm/p5_data.py` | 29 |     "scientific_panel_ranks": [VAL_START, VAL_END], |
| `src/arborlm/p5_data.py` | 49 |     if len(validation) != VAL_END: |
| `src/arborlm/p5_data.py` | 50 |         raise ValueError("P5 requires the first 2560 ranked validation candidates") |
| `src/arborlm/p5_data.py` | 52 |     if len(hashes) != VAL_END or hashes & full_train: |
| `src/arborlm/p5_data.py` | 87 |         _rows(source / DOWNLOAD_FILES[1]), "validation", VAL_END, excluded=full_train |
| `src/arborlm/p5_data.py` | 123 |         "scientific_panel_ranks": [VAL_START, VAL_END], |
| `src/arborlm/p6_fidelity_study.py` | 382 |             "ranks": [2048, 2560], |
| `src/arborlm/p6_fidelity_study.py` | 556 |         panel="P5 primary panel only (ranks 2048-2560); replication panel not approved", |
| `src/arborlm/p7a_core.py` | 57 | CAL_START, CAL_END = 2048, 2560  # training-pool ranks used only to fit layouts |
| `src/arborlm/p7a_core.py` | 58 | EVAL_RANKS = (2048, 2560) |
| `src/arborlm/p7a_study.py` | 45 |     """The calibration stream of a real cell: training-pool ranks 2048-2559 of the frozen pool of |

### 2.3 Class (a): machine records (summary by study and pattern; every line in JSON)

| Study group | Pattern | Lines |
|---|---|---|
| experiments/P5 | `[2048,2560]` | 309 |
| experiments/P6-Q | `(see text)` | 12 |
| experiments/P6-Q | `2048-2560` | 1 |
| experiments/P6-Q | `[2048,2560]` | 58 |
| experiments/P7-A | `[2048,2560]` | 27 |
| experiments/review | `2048–2559` | 1 |
| experiments/review | `[2048,2559]` | 1 |
| experiments/review | `[2048,2560]` | 2 |
| experiments/review | `[2048:2560]` | 1 |
| experiments/review | `[:2560]` | 1 |
| results/P5 | `2048..2559` | 1 |
| results/P5 | `2048–2559` | 3 |
| results/P5 | `[2048,2560]` | 312 |
| results/P6-Q | `(see text)` | 12 |
| results/P6-Q | `2048-2560` | 1 |
| results/P6-Q | `[2048,2560]` | 58 |
| results/P7-A | `[2048,2560]` | 108 |

### 2.4 Class (c): other (summary; every line in JSON)

| Study group | Lines |
|---|---|
| docs/reviews/p5-claude-review-2026-11-13 | 1 |
| docs/reviews/p6-preflight-2026-11-13 | 1 |
| docs/reviews/p6-results-audit-2026-11-13 | 2 |
| docs/reviews/p7a-preflight-2026-11-13 | 21 |
| docs/reviews/p7b-spec-review-2026-11-13 | 1 |
| experiments/E0 (not requested) | 102 |
| experiments/P1 | 43 |
| experiments/P2 | 176 |
| experiments/P3-LT | 367 |
| experiments/P4 | 285 |
| experiments/P5 | 752 |
| experiments/P7-A | 11 |
| experiments/ci | 60 |
| experiments/memory diagnostic | 12 |
| experiments/review | 21 |
| results/E0 (not requested) | 6 |
| results/P1 | 42 |
| results/P2 | 175 |
| results/P3-LT | 366 |
| results/P4 | 284 |
| results/P5 | 757 |
| results/P6-Q | 1 |
| results/P7-A | 11 |
| results/memory diagnostic | 12 |
| src | 33 |

Class (c) human-authored lines are: `VAL_START`/`VAL_END` in src/arborlm/p2_data.py, p3_data.py, p4_data.py and p2_config.py/p3_config.py (bounds of other studies, e.g. `VAL_START, VAL_END = 1536, 2048` at p4_data.py:24); `bound 91301, 91302` seed sets (ADR-0013 lines 246 and 258, REAUDIT.md:76); and ADR-0014 line 176 is class (b) (see 2.1).

## 3. Item 3: model evaluation, trace or loss on validation ranks at or above 2560

**Answer: none found in the searched sources.**

Searches run (all read-only, text sources only):

- `grep -rn -E '2560|2561|3071|3072|VAL_END|VAL_START|ranks? 2560' docs/decisions docs/RESEARCH_LOG.md docs/reviews configs src/arborlm` (and the same patterns over the JSON, JSONL, log and CSV records under `results/` and `experiments/`, excluding traces/ and arrays/).
- A structured walk of every JSON metadata file in scope (skipping frozen-data, `*.selected.json` and files over 3 MB) for rank, panel, validation, interval and SHA-256 keys.
- A per-file maximum over scalar `rank` and `ranks` values. Result: P5 audit records 2048..2559 (512 rows) only.
- Validation-context bounds with upper value at or above 2560. Result: only the bracket pairs `[2048, 2560]` (and `2048-2560` text) in P5, P6-Q and P7-A records, which are the half-open convention in NEEDS REVIEW 1.
- `grep` for `d50cbe4c` in `results/p6-e-2026-11-13`, `results/p7a-2026-11-13`, `experiments/P6E*`, `experiments/P7A*`: zero files.
- The P7-B identity manifest in this directory: no validation bound at or above 2560.

Relevant non-evaluation record: `experiments/review/p5-root-data-audit.py` hashes validation ranks `[0, 2560)` and the P5 slice `[2048:2560]` (lines 74, 78). It does not reach ranks at or above 2560.

## 4. Local listing: directories under experiments/ (one level)

33 entries:

- `E0-20261113T021519633244Z-7cb9a2c706074a459efb8b82107696f5`
- `E0-20261113T021737609016Z-f9af346e45f94803973c1a4e681d233a`
- `E0-20261113T021751395579Z-022ace6673384498a39ce74f2ddea257`
- `E0-20261113T023000474943Z-68c623a86fc34e199f863b21904a56de`
- `E0-20261113T023057321599Z-db358750bd8144bf98db0a06d9244db7`
- `E0-20261113T023150557313Z-f15c15bf02b840da9638fc7f34c60d4d`
- `E0-20261113T025937174570Z-38e182f980da40abbccb0efad9edfa6b`
- `E0-20261113T030013937138Z-0178955490dc4cf4b3ee7e9e0aebed9d`
- `E0-20261113T033146241027Z-5fdc210cb927450a8ce42b65e9d96ec5`
- `E0-20261113T033317763832Z-d3235d1651914531a2d568df747b9552`
- `E0-20261113T042831282007Z-2fc48517d9ab4ac696fe30aa5264a3de`
- `E0-20261113T042925468139Z-b37a34341068462b8781b945ead74079`
- `E0-20261113T043021992435Z-b82abb95271c43f79f5fa9871bec417b`
- `E0-20261113T044851909363Z-1a7aa64e65bd4d91a2544ad34c6a2664`
- `E0-20261113T124019386667Z-dd95f779549449dc8a1c1ea7d5723ac5`
- `E0-20261113T124435147087Z-c639d979f77240718281e53bab42d482`
- `E0-20261113T124524395330Z-83849e36dff2465499a30b8bead714d7`
- `P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8`
- `P1DIAG-20261113T024308074540Z-ace5d3680604461a8f1e9bea48f466f0`
- `P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7`
- `P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d`
- `P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd`
- `P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be`
- `P6EANA-20261113T180400246467Z-b0ad0be91c75450eb482ef6cf8b3ab59`
- `P6ECON-20261113T175807956983Z-2f66ed206eb24230b888583ae892bd39`
- `P6EEQ-20261113T173700724372Z-c3d45d6d7fa140bea302c4aaf44fc95f`
- `P6ESCR-20261113T174408566062Z-28df28f7b3b3436492d2d8379b217a2d`
- `P6Q-20261113T180439281981Z-fdc287dd79274cfd962ab29fbffd1087`
- `P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a`
- `P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b`
- `P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e`
- `ci`
- `review`

## 5. NEEDS REVIEW

1. Interval notation: validation ranks are written as bracket pairs such as [2048, 2560] (configs/p5_hierarchy_ablation.toml:27; results/p5-2026-11-13/b101-o301-baseline/config.resolved.json "validation_ranks"). Read as half-open, the meaning is ranks 2048..2559, which is what the code slices (src/arborlm/p5_data.py:26, 49-50, 58-59) and the ADR prose (ADR-0010 line 79; ADR-0013 line 53) state. The brackets alone do not show whether 2560 is excluded. If the brackets were read as closed, rank 2560 would appear in the P5, P6-Q and P7-A evaluations, and the item-3 answer would change. The lead should confirm the convention. This inventory does not resolve it.
2. P1 validation range [0, 512) and training consumption [0, 2048) are not written as rank intervals in any P1 record. They are derived from configs/p1_ram_screen.toml:11-12, src/arborlm/pilot_data.py:80 (ranked[:count]), src/arborlm/pilot_config.py:23 and src/arborlm/pilot.py:242. The training-consumption figure is a derivation from the step and batch arithmetic, not a recorded statement.
3. The memory diagnostic's validation range is not stated as a rank interval in its own records. It reuses the P1 frozen validation file (ADR-0006 line 10; validation.bytes SHA-256 2e6b71b9… is identical to P1), so [0, 512) is inherited by reference.
4. P6-E records (results/p6-e-2026-11-13/ and experiments/P6EANA-, P6ECON-, P6EEQ-, P6ESCR-) contain no validation rank interval and no panel SHA-256. The P5 panel identity for P6-E comes only from ADR-0011 (line 42) and the module docstring src/arborlm/p6_equivalence.py lines 1-5.
5. P7-A records give the evaluation and calibration ranks ([2048,2560]) in the trace checkpoint JSON but no panel SHA-256. The P5 panel hash d50cbe4c… appears in P6-Q and P5 records only. The P7-A panel identity is stated in ADR-0013 line 53 and docs/reviews/p7a-preflight-2026-11-13/AUDIT.md line 110, which give no hash.
6. Class (b) status: ADR-0011 line 4 and line 262 record that the replication panel (2560–3071) was not used, and line 266 records P6-E/P6-Q as approved without it. ADR-0014 is DRAFT PROPOSAL REVISION 3, NOT APPROVED (line 4). Its Stream B (2560–3071) is therefore proposed, not approved. ADR-0014 is also modified and uncommitted in the working tree (gitStatus snapshot at session start).
7. ADR-0010 line 79 reads 'Proposed sole scientific validation panel' inside an ADR whose status line says SPEC APPROVED (line 4). The wording is pre-execution text and is reported as written.
8. Scope gaps. Searched: docs/decisions/ADR-*.md, docs/RESEARCH_LOG.md, all docs/reviews/**/*.md, configs/*.toml, src/arborlm/*.py, results/**/*.json and *.md, and experiments/**/*.json. Also searched as an extension: docs/reviews non-md text (json, py, txt, log, csv, stdout, stderr, exit), and in results/ and experiments/ the text files *.jsonl, *.log, *.csv, *.txt, *.stdout, *.stderr, *.exit, *.md, *.py, *.sh. Not searched: *.bin (2,586 files), *.pt (894), *.tar (514), *.diff (514), any traces/ or arrays/ directory, and data/ (git-ignored corpus). A missing hit in those is not evidence of absence.
9. Structured JSON key pass skipped 76 files (frozen-data or *.selected.json, and files over 3 MB). Those files were still covered by the regex sweep. The regex sweep read the text of experiments/**/frozen-data/*.json (for example train.selected.json and validation*.selected.json) and the review copies of them. The brief excluded data-file contents. These are dataset-selection records, not data/ or traces, and no content was interpreted beyond the regex matches and the rank-field checks listed in the method. Disclosed for the lead to accept or reject.
10. Training-pool ordinal fields: frozen train.selected.json files carry a "rank" ordinal over the 4096-chunk ranked training pool (src/arborlm/p2_data.py:32-44, _selection). Ordinals of 2560 and above therefore occur in those files. They are training-pool positions, not validation ranks, and are class (c). They are listed in the JSON because they match the required tokens.
11. Substring-only matches are excluded from occurrence classes, for example 80307234e104 (contains 3072) at docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.md line 58. The count is 7,748 lines across 1,510 files. Their file list is in the JSON under sub_files_substring_only.
12. Trimming: the quoted line is trimmed to 200 characters. For lines longer than 200 characters the window is centred on the first match. Single-line JSON files report line 1. The complete class (c) listing is in the JSON; the markdown summarises it.
13. Item 3 answer depends on the interval convention (first item). Under the half-open reading, no record shows evaluation at ranks >= 2560. Under the closed reading, the P5, P6-Q and P7-A records would include rank 2560 and would need review.
14. experiments/review/p5-root-data-audit.py (lines 74 and 78) hashes validation ranks [0, 2560) and the P5 slice [2048:2560]. It is a data-hash audit script, not a model evaluation, and it does not touch ranks at or above 2560. Its reads are recorded as class (a) occurrences for completeness.
15. E0 is outside the requested study list and is listed only for completeness.
16. Output directory: docs/reviews/p7b-spec-inputs-2026-11-13/ already contains identity_manifest.json and identity_manifest.md. Those were read by the sweep. They contain no validation rank bound at or above 2560 (only the substring noted above).

