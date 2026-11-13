# P6-E and P6-Q results: independent recomputation (auditor role)

- Auditor model: `claude-opus-5-5` (Claude Code subagent, auditor role). Date 2026-11-13.
- What this is: independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. Astra review: NOT_PERFORMED.
- Records audited: `results/p6-e-2026-11-13/` and `results/p6-q-2026-11-13/` as committed in `c389fe7` (results-only commit on top of freeze `a786c5d`; the working tree under `results/` was clean when I checked). Local raw logs: `experiments/P6E{EQ,SCR,CON,ANA}-*`, `experiments/P6Q-20261113T180439281981Z-*`.
- Spec: ADR-0011 §3.3–3.6, §4.3–4.5, §7 (clarifications 1–31).
- Independence: my scripts use only the Python standard library. They do not import `arborlm` and do not reuse the implementation's analysis code. I read `src/arborlm/p6_timing_study.py`, `p6_analysis.py` and `p6_equivalence.py` only to learn the storage order of raw samples and how NLL is accumulated. **Limitation:** the float64 reference behind P6-Q gate (iv) was written by the auditor role before the freeze (clarification 5). My review of gate (iv) is therefore not independent of the auditor role.
- Nothing was re-run, re-timed or forwarded. No model was loaded.

## Commands and environment

```sh
cd docs/reviews/p6-results-audit-2026-11-13
uv run --locked python -I recompute_p6e.py   # -> recompute_p6e.json
uv run --locked python -I recompute_p6q.py   # -> recompute_p6q.json
```

Environment: Python 3.12.14 (project venv via `uv 0.12.15`), Apple M5 Max, macOS (darwin). No third-party package is imported. The raw `.bin` arrays are read with `array` after a SHA-256 check (the machine is little-endian).

Attempt log, all kept in this folder:

| Attempt | Exit | What happened |
|---|---|---|
| p6e-01 (`p6e-attempt-01.py.txt`) | 1 | ZeroDivisionError. My code divided by a guard-fallback query count of 0 for variants that have no guard band. My bug. |
| p6e-02 (`p6e-attempt-02.py.txt`, `.json`) | 0 | Complete. |
| p6e-03 (= `recompute_p6e.py`) | 0 | Added round-matched ratios and a manifest metadata scan. Earlier numbers unchanged. |
| p6q-01 (`p6q-attempt-01.py.txt`) | 1 | KeyError `run_id`: unexecuted suite cells have no run id. My bug. |
| p6q-02 (`p6q-attempt-02.py.txt`, `.json`) | 0 | **Wrong gate (iv) rule (my mistake):** any set difference was counted as a gate failure, which listed 11 cells as failing. Clarification 7 stops only when the sets differ *and* the reference boundary gap exceeds 1e-5. |
| p6q-03 (`p6q-attempt-03.py.txt`) | 0 | Gate (iv) rule corrected. No failures. |
| p6q-04 (= `recompute_p6q.py`) | 0 | Added descriptive correlations. Earlier numbers unchanged. |

`source-hash-check.stdout`: the 11 P6 source files at HEAD match the SHA-256 values in the stage specs. Source archive `061b2bf0…` and code commit `a786c5d` are shared by P6-E and P6-Q.

A note on the JSON outputs. The `g_sensitivity_NOT_REGISTERED` section of `recompute_p6e.json` contains fields named `cells_ok` and `gm_ok`. They compare usable-subset counts with the registered 22/27-style requirements. They are bookkeeping, not verdicts, and should not be read as pass/fail.

---

## Verified

### P6-E

**(a) Raw timing records.** I recomputed all 4,536 records from the raw nanosecond samples (screen 3,240, confirm 1,296; 80 samples each, 8 rounds of 10). Median, round medians, nearest-rank p10/p50/p90/p95, min, max, round-median ratio and the reliability rule all agree exactly with the stored values. Every record's samples also equal, in order, the per-block durations in the local `metrics.jsonl` of the same worker run. Every unusable record fails only the round-stability clause (max/min round median > 1.25). None fails the positivity or clock-resolution clauses.

**(b) Equivalence gate.** I re-derived every scope class and every checkpoint class from the per-checkpoint summaries using the §3.3 rules.

| Variant | Checkpoints | STRICT / BOUNDED / NOT EQ | EQ | Max \|Δscore\| | Max \|Δlogit\| | Max \|ΔNLL\| | Panel guard fallback |
|---|---:|---|---|---:|---:|---:|---|
| F1 | 27 | 27 / 0 / 0 | pass | 0 | 0 | 0 | — |
| F2 | 27 | 27 / 0 / 0 | pass | 0 | 0 | 0 | 6 of 946,944 queries |
| T1 | 54 | 54 / 0 / 0 | pass | 0 | 0 | 0 | — |
| T2 | 54 | 54 / 0 / 0 | pass | 0 | 0 | 0 | — |
| T3 | 54 | 54 / 0 / 0 | pass | 0 | 0 | 0 | 0.292% (0.195–0.381% per checkpoint) |
| T4 | 54 | 0 / 54 / 0 | pass | 1.91e-6 | 4.77e-6 | 3.73e-8 | 0.292% (0.195–0.385%) |
| T5 | 54 | 0 / 54 / 0 | pass | 1.91e-6 | 4.77e-6 | 3.73e-8 | 0.292% (0.195–0.385%) |

- Across all variants and scopes: selected-slot mismatches 0, tie-rule violations 0 (variant and reference), `branch_ids` and `candidate_ids` equal everywhere, and Wtok (descriptive) selected mismatches 0.
- All 27 `mismatches.jsonl` files are empty (0 records, SHA-256 of the empty string).
- On the fixtures, T3–T5 flagged 1,906 of 5,400 queries, of which 1,873 had exact ties in the reference top 9. F2 flagged 364 of 999, all of which had exact ties.
- My classifications agree with the stage `gate` and with the analysis for every variant. E-H1 holds and E-H2 holds, as recorded.

**(c) Screen selection and linkage.** W8 `addition_forward` geometric mean of median(v)/median(T0) over 27 pairs:

| Variant | Fixed | Learned |
|---|---:|---:|
| T1 | 0.8669 | 0.8586 |
| T2 | 0.7904 | 0.7870 |
| T3 | 0.7334 | 0.7235 |
| T4 | 0.3767 | 0.3666 |
| **T5** (selected) | **0.2895** | **0.2820** |

Flat comparator (median of the 27 worker medians, W8 `addition_forward`): F0 2,594.1 µs, **F1 2,584.4 µs (selected)**, F2 5,998.9 µs. F1 beats F0 by 0.37%.

Every screen table entry is `all_usable: false`. The selection rule does not require reliability, and T5's margin over T4 is large. Selection and tables match `selection.json` to ≤1e-12.

Linkage checks, all true:
- The confirm stage-spec names the equivalence and screen runs.
- Its `equivalence_result_sha256`, `screen_result_sha256` and `selection_sha256` equal the SHA-256 of those files. The screen spec likewise points to the equivalence result.
- The `results/` copies are byte-identical to the `experiments/` copies.
- The confirm plan is exactly {T0, T5} for each tree kind and {F0, F1} for flat. All 27 confirm workers timed exactly those 6 entities (48 records each).
- No supersede argument was used. There is exactly one run directory per stage in both `results/` and `experiments/`.

**(d) Registered criteria** (T-confirm, W8, T5 against comparator F1). The "point" columns give the clause values before applying the reliability rule.

| Kind | Criterion | Point clauses | All clauses met at point? | Usable pairs | **Registered verdict** |
|---|---|---|---|---|---|
| fixed | SP | gm 0.2918 ≤ 0.50; 27/27 < 1; 9/9 parents < 1 | yes | 17/27 | **INCONCLUSIVE** |
| fixed | PAR | add gm 0.7475 ≤ 1.00, 27/27, 9/9; fwd gm 0.8121 ≤ 1.05, 27/27, 9/9 | yes | add 16, fwd 17 | **INCONCLUSIVE** |
| fixed | PR | add gm 0.7475 ≤ 0.80, 27/27 < 1, 9/9 < 1; fwd as PAR | yes | add 16, fwd 17 | **INCONCLUSIVE** |
| learned | SP | gm 0.2860; 27/27; 9/9 | yes | 18/27 | **INCONCLUSIVE** |
| learned | PAR | add 0.7294, 27/27, 9/9; fwd 0.7892, 27/27, 9/9 | yes | 17, 17 | **INCONCLUSIVE** |
| learned | PR | add 0.7294 ≤ 0.80; fwd 0.7892 | yes | 17, 17 | **INCONCLUSIVE** |

- Per-pair ranges: SP ratio 0.272–0.342 (fixed) and 0.266–0.340 (learned). Addition vs F1: max 0.854 / 0.810. Model forward vs F1: max 0.886 / 0.848.
- Against F0 (the weaker comparison): add 0.7411 / 0.7232, fwd 0.8140 / 0.7912. All clauses are met at the point, and the verdict is again INCONCLUSIVE for both kinds.
- E-H3 and E-H4 are **undecided** under clarification 21. Every verdict, every geometric mean, every count and every per-pair usable flag agrees with `analysis/result.json`.

**(e) Descriptive ratios (confirm, geometric mean over 27 pairs).**

| T5 over … | W8 lookup | W8 add | W8 fwd | W1 lookup | W1 add | W1 fwd | Wtok lookup | Wtok add |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| T0, fixed | 0.275 | 0.292 | 0.379 | 0.532 | 0.561 | 0.647 | **2.067** | **1.888** |
| T0, learned | 0.269 | 0.286 | 0.371 | 0.493 | 0.533 | 0.613 | **1.987** | **1.833** |
| F1, fixed | 0.739 | 0.747 | 0.812 | **1.507** | **1.456** | **1.277** | **4.927** | **3.383** |
| F1, learned | 0.724 | 0.729 | 0.789 | **1.381** | **1.368** | **1.210** | **4.855** | **3.330** |

- At W1, T5 is slower than F1 in **every** pair: 0 of 27 pairs below 1 for addition and model forward, in both kinds.
- F1 over F0: W8 add 0.991, W8 fwd 1.002, W1 add 0.955, Wtok add 0.755.
- All screen and confirm descriptive ratios in the analysis match mine to ≤1e-12.

**(h) Absolute medians** (median over the 27 workers of each worker's median, µs, confirm):

| Entity | W8 lookup | W8 add | W8 fwd | W1 add | W1 fwd | Wtok add |
|---|---:|---:|---:|---:|---:|---:|
| fixed T0 | 6,717 | 6,823 | 7,703 | 909 | 1,153 | 95.1 |
| fixed T5 | 1,799 | 1,951 | 2,863 | 501 | 730 | 174.3 |
| learned T0 | 6,686 | 6,789 | 7,675 | 887 | 1,155 | 95.4 |
| learned T5 | 1,740 | 1,912 | 2,785 | 463 | 710 | 171.9 |
| flat F0 | 2,491 | 2,651 | 3,548 | 366 | 597 | 68.9 |
| flat F1 | 2,453 | 2,639 | 3,571 | 346 | 581 | 52.7 |

Comparison with P5 (same 27 pairs, same scopes):

| Reference | W8 add, P6 / P5 (µs) | Ratio | W8 fwd, P6 / P5 (µs) | Ratio | T0/F0 gm, P6 | Tree/flat gm, P5 |
|---|---|---:|---|---:|---:|---:|
| fixed | 6,823 / 6,311 | 1.081 | 7,703 / 7,196 | 1.070 | add 2.540, fwd 2.145 | add 2.603, fwd 2.190 |
| learned | 6,789 / 6,325 | 1.073 | 7,675 / 7,166 | 1.071 | add 2.528, fwd 2.134 | add 2.598, fwd 2.184 |
| flat | 2,651 / 2,431 | 1.090 | 3,548 / 3,304 | 1.074 | — | — |

- Absolute reference medians are 3–9% slower than in P5 across all scopes.
- The relative tree-over-flat reference ratio is within about 3% of P5 (W8: 2.54 vs 2.60). The reference is comparable in relative terms, not in absolute terms.

**(i) Memory and one-time costs** (confirm; median over workers, with min–max where it matters).

- Persistent extra state: T5 265,216 B and F1 262,144 B. 262,144 B is the 4,096×16 float32 normalized key table. The extra 3,072 B is consistent with the 16×16 router (1,024 B) plus int64 `slot_offsets` (2,048 B).
- Transient memory per W8 call (profiler, allocator level, allocated / peak live):

  | Entity | `addition_forward` | `lookup_score_select` |
  |---|---|---|
  | T0 | 50.97 / 36.78 MB | 49.57 / 36.75 MB |
  | T5 | 12.4 / 5.44 MB | 11.0 / 5.41 MB |
  | F0 | 18.58 / 16.81 MB | 17.18 / 16.78 MB |
  | F1 | 18.28 / 16.81 MB | — |

- Cache construction: T5 52 µs (fixed) and 41 µs (learned); F1 52 µs. The one-time binding hash is a further 106–136 µs.
- First W8 forward after load, taken after the integrity replay and therefore model-warm: fixed T0 7.97 ms, T5 3.11 ms, F0 3.98 ms, F1 3.58 ms.
- RSS: 184 MB before load, 257 MB after load, 341 MB after caches, 337 MB after timing. One worker sampled 175 MB after timing, which is a sampling artifact of coarse RSS.
- Guard fallback during timed calls: T5 fixed 0.352% and learned 0.279% of queries (per-worker range 0.087–0.69%).
- Caps:

  | Stage | Active worker time | Cap | Slowest worker | Worker cap |
  |---|---:|---:|---:|---:|
  | Equivalence | 411.1 s | 1,200 s | — | — |
  | Screen | 819.6 s | 1,200 s | 35.7 s | 90 s |
  | Confirm | 341.2 s | 600 s | 16.5 s | 45 s |
  | Combined | 1,571.9 s | 3,000 s | — | — |

  Peak stage process-tree RSS was 617 MB against the 2 GiB cap. All 81 workers completed.

**(j) Integrity.** In all three stages and all 27 workers:
- source recheck unchanged;
- checkpoint files unchanged, and state and RNG unchanged;
- integrity replay bitwise for every restored checkpoint;
- `recorded_final_nll` equal to the P5 `final.nll`, and `state_sha256` equal to P5's `checkpoint-512` hash, for all 81 checkpoints;
- no dry-run or synthetic flag.

### P6-Q

**Completeness.** All 54 finals are completed. 16 of 27 step-0 checkpoints are completed. The 11 unexecuted ones are b102-o303-s502 and s503 and all nine b103 step-0 checkpoints, recorded as budget. Flag status is COMPUTED. All 70 compact records pass my internal-consistency checks:
- histogram sums;
- overlap sum = Σk·hist[k], so the mean is exact;
- `fraction_one`;
- lost count = 8Q − overlap;
- lost-per-query histogram is the mirror of the recall histogram;
- trained + untrained = lost;
- pooled trained recall;
- no X16P loss in route rank 1 or 2;
- monotone width curve with endpoints recall_P and 1;
- each ΔNLL field equals the NLL-field difference exactly;
- unique / effective / hottest / normalized entropy recomputed from the 4,096 slot counts;
- per-branch counts are contiguous 256-slot sums;
- certificate fraction;
- per-token "changed" counts consistent with recall and with T2N≠T2P fractions;
- coverage identities.

**(a) Registered flags** (54 finals, primary panel):

| Kind | Flag | Mean | Cells | Parents | Clauses (mean / cells / parents) | **Verdict** |
|---|---|---:|---|---|---|---|
| fixed | FID | 0.7909 | 0/27 ≥ 0.95 | 0/9 | F / F / F | **FAIL** |
| fixed | COS | 0.2623 | 0/27 | 0/9 | F / F / F | **FAIL** |
| fixed | LOSS | +0.000441 | 5/27 < 0 | 1/9 < 0 | F / F / F | **FAIL** |
| fixed | PRIOR | +0.003863 (sign +) | 27/27 positive | 9/9 | magnitude F / cells T / parents T | **FAIL** |
| learned | FID | 0.9145 | 4/27 | 1/9 | F / F / F | **FAIL** |
| learned | COS | 0.2729 | 0/27 | 0/9 | F / F / F | **FAIL** |
| learned | LOSS | +0.0000197 | 14/27 < 0 | 3/9 < 0 | F / F / F | **FAIL** |
| learned | PRIOR | +0.003934 (sign +) | 27/27 | 9/9 | magnitude F / cells T / parents T | **FAIL** |

Means, every parent mean, counts and clauses agree with `analysis.json` to ≤1e-15. The §4.5 row that applies to both kinds is "FID fails, LOSS fails". PRIOR does not pass, so no PRIOR statement from §4.5 is licensed.

**(b) Recall** (27 cells per kind; mean, with min–max):

| Quantity | Fixed | Learned |
|---|---|---|
| recall_P | 0.791 (0.634–0.874) | 0.915 (0.854–0.967) |
| Fraction of queries with recall_P = 1 | 0.320 (0.188–0.490) | 0.655 (0.421–0.842) |
| recall_C | 0.262 (0.180–0.343) | 0.273 (0.197–0.378) |
| Fraction of queries with recall_C = 1 | ≈ 1e-5 | ≈ 2e-5 |
| Exactness certificate | 0.024 (0.0002–0.120) | 0.169 (0.021–0.335) |

- Certified queries with recall below 1: 0 in every cell.
- Width curve (mean recall_P, k = 2/3/4/6/8/12/16):
  - fixed: 0.791 / 0.895 / 0.947 / 0.986 / 0.997 / 1.000 / 1;
  - learned: 0.915 / 0.972 / 0.990 / 0.998 / 0.9997 / 0.99996 / 1.
- Cells with mean recall_P ≥ 0.95 by width:
  - fixed: k = 4 gives 14/27, k = 6 gives 26/27, k = 8 gives 27/27;
  - learned: k = 3 gives 23/27, k = 4 gives 27/27.
- Pooled recall_P histogram, counts for 0 to 8 overlapping slots:
  - fixed: 111 / 2,961 / 15,684 / 38,052 / 82,876 / 111,688 / 157,312 / 192,543 / 283,509;
  - learned: 32 / 484 / 3,543 / 11,040 / 20,174 / 42,638 / 88,933 / 138,399 / 579,493.

**(c) Training coverage.**
- Fraction of slots trained (key or value bitwise changed): fixed 0.745 (0.667–0.822), learned 0.670 (0.599–0.748). Key and value change together: key-only = value-only = 0 in all cells, and the two coverage arrays are byte-identical in the sampled cells.
- Lost X16P candidates: fixed 1,477,693 trained vs 2,021 untrained (0.14% untrained); learned 604,126 vs 851 (0.14%).
- Lost X16N candidates: fixed 6.0% untrained, learned 6.6% untrained.
- Recall restricted to trained reference slots is close to the overall recall:

  | Kind | recall_P macro / pooled | Overall recall_P | recall_C macro / pooled | Overall recall_C |
  |---|---|---:|---|---:|
  | fixed | 0.7912 / 0.7912 | 0.7909 | 0.2750 / 0.2745 | 0.2623 |
  | learned | 0.9146 / 0.9146 | 0.9145 | 0.2875 / 0.2868 | 0.2729 |

  Every query has at least one trained reference slot.

**(d) Lost candidates.** X16P losses by route rank, pooled:
- fixed: rank 3 = 50.0%, rank 4 = 24.7%, rank 5 = 12.1%, rank 6 = 6.5%, ranks 7 and above = 6.7%;
- learned: rank 3 = 67.8%, rank 4 = 21.1%, rank 5 = 6.3%, ranks 6 and above = 4.8%.

Weighted recall, P / C: fixed 0.882 / 0.304, learned 0.956 / 0.323. The minimum lost-candidate margin to the T2P boundary is 3.7e-6 (fixed) and 5.2e-6 (learned). The median of cell medians is 0.880 (fixed) and 0.655 (learned).

**(e) Prior effects** (fixed vs learned).
- Fraction of queries with all 8 selected slots in the top-1 branch: 0.149 vs 0.290.
- Route gap, top-1 minus top-2, in score units:

  | Quantity | Fixed | Learned |
  |---|---:|---:|
  | Mean | 1.23 | 1.75 |
  | Median | 1.15 | 1.70 |
  | q10 | 0.21 | 0.33 |
  | q90 | 2.36 | 3.24 |

- Fraction of queries where T2N and T2P select different sets: 0.715 vs 0.814. Mean overlap |T2P ∩ T2N|/8: 0.817 vs 0.724.

**(f) Concentration** (mean over cells, unique / effective slots / hottest share):

| Rule | Fixed | Learned |
|---|---|---|
| T2P | 383 / 96.2 / 0.041 | 313 / 83.0 / 0.043 |
| T2N | 534 / 114.8 / 0.039 | 505 / 106.2 / 0.041 |
| X16P | 310 / 99.9 / 0.039 | 277 / 84.2 / 0.042 |
| X16N | 884 / 211.7 / 0.025 | 851 / 209.0 / 0.025 |

For all 54 finals, T2P slot counts, unique count, effective count and hottest share equal the P5 `final.retrieval` record exactly. For the 16 step-0 checkpoints they equal the P5 `initial.retrieval` of both the fixed and the learned cell.

**(g) NLL deltas** (nats per byte; 27 cells each):

| Kind | Δ | Mean | SD | Min | Max | − / + | Parents − / + |
|---|---|---:|---:|---:|---:|---|---|
| fixed | restrict | +0.000441 | 0.00050 | −0.00041 | +0.00142 | 5 / 22 | 1 / 8 |
| fixed | prior | +0.003863 | 0.00154 | +0.00159 | +0.00726 | 0 / 27 | 0 / 9 |
| fixed | both | +0.01277 | 0.00385 | +0.00685 | +0.02205 | 0 / 27 | 0 / 9 |
| learned | restrict | +0.0000197 | 0.00018 | −0.00030 | +0.00032 | 14 / 13 | 3 / 6 |
| learned | prior | +0.003934 | 0.00177 | +0.00177 | +0.00921 | 0 / 27 | 0 / 9 |
| learned | both | +0.01103 | 0.00358 | +0.00544 | +0.01803 | 0 / 27 | 0 / 9 |

Marginal means of Δ_prior by order: fixed 0.0029 / 0.0035 / 0.0052 and learned 0.0025 / 0.0035 / 0.0058 for o301 / o302 / o303. By backbone and by seed the spread is small (see JSON). Order o303 carries the largest Δ_prior and Δ_both.

Per-token split, mean of the cell mean differences (alternative − T2P):

| Rule | Fixed changed | Fixed unchanged | Learned changed | Learned unchanged |
|---|---:|---:|---:|---:|
| X16P | +0.00058 | +0.00008 | +0.00004 | ≈0 |
| T2N | +0.00486 | +0.00119 | +0.00464 | +0.00080 |

Under X16N almost every position changes (mean 32,767.6 of 32,768), so its "unchanged" group is effectively empty.

**(h) Paired learned − fixed** (27 pairs):

| Quantity | Mean | Learned higher / lower | Parents higher / lower |
|---|---:|---|---|
| recall_P | +0.1236 | 27 / 0 | 9 / 0 |
| recall_C | +0.0106 | 18 / 9 | 5 / 4 |
| Weighted recall P | +0.073 | 27 / 0 | — |
| Route gap mean | +0.526 | 25 / 2 | 9 / 0 |
| All-in-top-1 fraction | +0.141 | 24 / 3 | — |
| Δ_restrict | −0.00042 | 6 / 21 | — |
| Δ_prior | +0.00007 | 13 / 14 | — |
| Δ_both | −0.00174 | 6 / 21 | — |
| NLL(T2P) | +0.00058 | 17 / 10 | — |
| Slots trained | −307 | 1 / 26 | — |
| T2P unique slots | −70 | 3 / 23 (1 zero) | — |

All 19 paired quantities I recomputed match `analysis.json` in mean, sign counts and parent sign counts.

**(i) Step-0.**
- 16 of 27 completed (listed above). Fixed and learned share these snapshots.
- recall_P 0.862 (0.804–0.911) and recall_C 0.111. On the same 16 pairs, fixed finals have 0.797 and learned finals 0.928.
- Route-gap median 0.46.
- All three ΔNLL are of order 1e-7 (|max| 2.9e-6). At initialization the memory has essentially no effect on prediction, so step-0 prediction deltas carry no information.

**(j) Engineering gates.** In all 70 checkpoints:
- (i) holds: the unmodified, recorded and T2P-wrapper NLL agree bitwise and equal P5 `final.nll` or `initial.nll`, and T2P concentration reproduces P5;
- (ii) holds, with 0 restricted-score mismatches over 32,768 queries;
- (iii) holds;
- state and RNG are unchanged, the before and after state hashes are equal and equal the P5 recorded hashes, and the width cross-check passed.

Gate (iv): 64 disagreements in 40 cells (25 X16P, 39 X16N).
- 52 are order-only with equal sets.
- 12 have differing sets, each a single swapped slot. Their reference boundary gaps lie between 1.7e-8 and 8.3e-7, all ≤ 1e-5 and flagged `near_tie`.
- No gate-(iv) stop condition was met.
- Certified queries with recall below 1: 0.

**(k) Resources.**
- Active worker time 1,750.7 s against the 1,800 s cap. The suite stopped before b102-o303-shared_initial-s502 with 49.3 s remaining, below the 60 s per-checkpoint cap.
- Slowest checkpoint 30.8 s against the 60 s cap. Finals took 23.9–30.8 s each, step-0 checkpoints 24.2–25.0 s.
- Peak RSS 1.08 GB (ru_maxrss and suite sampling) against the 2 GiB cap.

**Raw arrays** (sample fixed before looking: b101-o301-fixed-s501, b102-o302-learned-s502, b103-o303-learned-s503, b101-o301-shared_initial-s501). For all four, every array's SHA-256 and byte size match the compact record. From the raw arrays I reproduced the following:
- **Exactly:** recall_P, recall_C and both histograms; lost route-rank histograms (P and C); trained/untrained split of lost slots; fraction of slots trained; width curve at k = 3/4/6/8/12; fraction all-in-top-1; route-gap mean, min and max; T2N≠T2P fraction; slot counts under all four rules; the certificate count (float64 log-softmax: 14, 5,993, 1,722 and 2, equal to the record); weighted recall (difference 0.0); per-token X16P "changed" mean difference.
- **To within 4e-8:** the mean token loss against the registered NLL, and the ΔNLL against the record. Deltas recomputed from float32 per-token losses differ from the record by ≤ 6.6e-8, which is accumulation precision.

Route scores are identical across the four rules, and T2P selections obey descending score then ascending ID (0 violations).

---

## Discrepancies

Between my recomputation and the implementation's analyses:

- **Numerical or verdict discrepancies: none.** For P6-E this covers every equivalence count, the selection, every criterion clause, every per-pair ratio and usable flag, every verdict, the E-H statuses and every descriptive ratio. For P6-Q it covers every flag, mean, parent mean, count and clause, the 19 paired quantities, the step-0 summary and the unexecuted list.

Record-metadata discrepancies:

1. **P6-E worker manifests are mislabelled.** All 81 worker manifests (27 per stage) carry:
   - `authorized_spec_reference: docs/decisions/ADR-0003-e0-approved-spec.md`;
   - `question_id: G0`;
   - `hypothesis_null_reason: "infrastructure validation only; does not test H1-H5"`.

   The stage spec and source records correctly point to the frozen P6 source.
2. **P6-Q cell manifests carry a template string.** The 70 cell manifests cite ADR-0011 correctly but also carry the same `hypothesis_null_reason` string.
3. **P6-E stage manifests have empty review fields.** The four stage-level manifests have null `astra_result_review` and `authorized_result_review` fields.

None of these affects any number. They should not be cited as evidence of what the runs tested.

My own mistakes, kept in the attempt log: p6e-01 crash, p6q-01 crash, and p6q-02's wrong gate-(iv) rule (see the table above).

---

## P6-E findings

1. **Registered outcome.** EQ passes for every variant. Selected variant T5 for both kinds, flat comparator F1. **SP, PAR and PR are INCONCLUSIVE for both kinds.** E-H3 and E-H4 are undecided. E-H1 and E-H2 hold as recorded.

2. **Unreliable records** (all of them fail the round-stability clause only):

   | Study / stage | Unusable records | Share |
   |---|---:|---:|
   | P6-E screen | 792 of 3,240 | 24.4% |
   | P6-E confirm | 344 of 1,296 | 26.5% |
   | P5 (recomputed) | 4 of 612 | 0.65% |

   Round-median ratio quantiles:

   | Quantile | P6-E confirm | P6-E screen | P5 |
   |---|---:|---:|---:|
   | Median | 1.129 | 1.126 | 1.053 |
   | p90 | 1.524 | 1.486 | 1.111 |
   | Max | 3.04 | 3.81 | 1.45 |

3. **Where the instability falls** (confirm).
   - **By entity:**

     | Entity | Unusable |
     |---|---:|
     | fixed T0 | 45 of 216 |
     | learned T0 | 46 |
     | F0 | 52 |
     | F1 | 56 |
     | learned T5 | 67 |
     | fixed T5 | 78 |

     The references are affected nearly as much as the variants; T5 is somewhat more affected.
   - **By workload:** W8 24.7%, W1 27.4%, Wtok 28.1%.
   - **The registered W8 `addition_forward`/`model_forward` records:** 79 of 324 unusable.
   - **By worker:** 24 of 27 workers have at least one unusable record. b101-o303-s502 (41/48), b103-o303-s502 (43/48), b103-o302-s503 (36/48) and b103-o302-s502 (32/48) dominate.
   - **By time:** with workers split into thirds by start time, unusable counts are 88 / 59 / 197 in confirm and 429 / 240 / 123 in screen. Instability comes in time clusters, early in screen and late in confirm.
   - **By round:** the outlying round is spread over all eight round positions and across each worker's block sequence (median relative position about 0.5). This looks like intermittent machine-level interference, not a warm-up effect.

   No load, thermal or frequency records exist to identify a cause. Absolute reference medians were 3–9% slower than in P5.

4. **Sensitivity over pairs where both records are usable.** This is **not** a registered result and **not** a substitute verdict.

   | Kind | SP vs T0 | PAR/PR addition vs F1 | PAR/PR model forward vs F1 |
   |---|---|---|---|
   | fixed | 17 pairs, gm 0.2859, 17/17 < 1, 7 parents represented, 7/7 < 1 | 16 pairs, gm 0.7417, 16/16 < 1, 7/7 parents < 1 | 17 pairs, gm 0.8038, 17/17 ≤ 1.05, 9/9 |
   | learned | 18 pairs, gm 0.2783, 18/18 < 1, 7/7 | 17 pairs, gm 0.7197, 17/17 < 1, 6/6 | 17 pairs, gm 0.7820, 17/17, 9/9 |

   The point estimates barely move. Not every parent is represented (6–7 of 9 for addition).

5. **Round-matched ratios.** Also descriptive and not registered. Entities are interleaved within each round, so round r of numerator and denominator ran close in time.

   | T5 over … (W8) | Fixed | Learned |
   |---|---|---|
   | T0, addition | 216/216 round pairs ≤ 0.50 (max 0.490) | 216/216 ≤ 0.50 (max 0.432) |
   | F1, addition | 210/216 < 1 (max 1.17) | 212/216 < 1 (max 1.13) |
   | F1, model forward | 209/216 < 1 | 215/216 < 1 |

   The ordering at W8 is not a product of a few noisy rounds. The registered verdict stays INCONCLUSIVE.

6. **Workload dependence.** At W1, T5 is slower than F1 in all 27 pairs:

   | T5 over F1 at W1 | Fixed | Learned |
   |---|---:|---:|
   | Addition | 1.456 | 1.368 |
   | Model forward | 1.277 | 1.210 |

   It is also below 1 in only 0–9 of 216 matched rounds. At Wtok, T5 is 1.8–2.1× slower than T0 and 3.3–4.9× slower than F1. The W8 advantage is specific to 512-query calls.

7. **Guard-band fallback.**
   - Rates: panel 0.29%; timed calls 0.35% (fixed) and 0.28% (learned).
   - Effect on speed: across workers the Pearson correlation between fallback fraction and the T5/T0 W8 ratio is 0.08 (fixed) and 0.01 (learned). Nothing in the records suggests that the speedup depends on the fallback rate at these rates.
   - Fixtures: all 1,873 exact-tie fixture queries went through the fallback. The T5 (and F2) kernel's own ordering of exact ties is therefore protected by the guard rather than exercised directly. Outputs are correct either way: 0 tie-rule violations.

8. **Equivalence NLL resolution.** The panel NLL compared for STRICT and BOUNDED is a Python sum of per-batch float32 `reduction="sum"` losses (`p6_equivalence.py` lines 338, 364). T4/T5 logit differences up to 4.8e-6 therefore produced NLL differences of 0 in many checkpoints and at most 3.7e-8 in others. The NLL clause is coarse evidence. The selected-ID and score clauses carry the equivalence.

---

## P6-Q findings

1. **Registered outcome.** For both kinds: FID FAIL, COS FAIL, LOSS FAIL, PRIOR FAIL (PRIOR fails on magnitude only). The permitted statement is §4.5 "FID fails, LOSS fails": the restriction changes the selection, but these weights do not predict better with exhaustive search; whether training with wider search would help is not answered.

2. **Scale of the selection change.**
   - Fixed: the top-2 restriction changes on average 21% of the X16P selection (recall_P 0.79). Only 32% of queries are unchanged.
   - Learned: the change is 8.5% (0.915), with 65% of queries unchanged.
   - The lost slots carry less weight than their count suggests: weighted recall is 0.88 for fixed and 0.96 for learned.
   - Width 4 (fixed) or 3 (learned) would bring mean recall_P above 0.95 in most cells.

3. **Prediction effect of exhaustive search.** It is essentially zero for these weights: mean Δ_restrict +0.00044 (fixed) and +0.00002 (learned), with the most negative cell at −0.0004, about 12× smaller than the LOSS margin. Removing the prior (Δ_prior) and exhaustive cosine search (Δ_both) both make every cell worse.

4. **Trained versus untrained lost slots.** 99.86% of lost X16P candidates are slots whose key and value moved in training. Recall restricted to trained reference slots equals overall recall to three decimals. Low recall_P is therefore not explained by untrained slots, but the coverage measure is coarse: "trained" means changed at least once, by any query routed to that branch.

---

5. **Fixed versus learned recall_P.** This difference is at least partly an effect of prior strength, not of better routing:
   - Learned recall_P is higher in 27/27 pairs (+0.124).
   - The learned router is sharper: its route gap is larger in 25/27 pairs (+0.53), and more queries have all 8 slots in the top-1 branch.
   - X16P adds log-softmax(route) to every slot score, so a sharper router penalizes unvisited branches more. X16P then agrees with T2P more often by construction.
   - The prior-free recall_C differs by only +0.011 (18/27 pairs, 5/9 parents).
   - Across the 54 cells, recall_P correlates with mean route gap at r = 0.71. Within kinds r = 0.27 (fixed) and 0.42 (learned); for the paired differences r = 0.37.
   - Step-0 recall_P (0.862) lies between fixed (0.797) and learned (0.928) on the same 16 pairs. Training lowered fidelity for the fixed router and raised it for the learned one.

   PENDING LEAD REVIEW: whether any reading of "learned routing is more faithful" is permissible beyond "its prior is sharper".

6. **Results close to a threshold.**
   - **PRIOR** is the only one.
     - Mean Δ_prior is +0.00386 (fixed) and +0.00393 (learned) against the 0.005 margin, short by 0.0011.
     - All 27 cells and 9 parents are positive in both kinds.
     - 6/27 cells and 2/9 parent means exceed 0.005 in each kind, and the cell SD is 0.0015–0.0018.
     - The effect is concentrated in order o303 (parent means 0.0055–0.0065).
     - With 27 correlated cells on one already-observed panel and no replication panel, these records cannot settle whether the prior effect is above or below the margin. Registered: FAIL. The direction is consistent; its size relative to the margin is not settled. PENDING LEAD REVIEW.
   - **FID** (learned): mean 0.915, with 4/27 cells and 1/9 parents ≥ 0.95. The miss is not marginal on the cells clause.
   - **LOSS and COS** are far from their thresholds.

7. **Asymmetry (§4.2).** LOSS failing means only that these T2P-trained weights do not gain from exhaustive search when evaluated off-distribution. It does not show that the restriction is harmless. The positive Δ_prior and Δ_both (worse without the prior) also measure how strongly the weights depend on the rule they were trained under; they are not evidence about which design is better.

8. **Per-token split** (descriptive; clarification 26).
   - X16P "changed" positions carry nearly all of the small Δ_restrict for fixed (+0.00058 changed vs +0.00008 unchanged).
   - X16N changes every position, so its split is uninformative.
   - Later positions attend to earlier ones, so "unchanged" positions are not counterfactually untouched.

9. **Step-0 coverage.** The step-0 summary covers backbones 101 and 102 only (16 of 27; every b103 is unexecuted), so its means are not comparable with all-27 final means. The 16-pair matched comparison above avoids this.

10. **Gates.** No engineering-gate violation in any of the 70 checkpoints. The 12 set-differing disagreements in gate (iv) are near-ties of at most 8.3e-7. They change recall by at most 1/8 on 12 of 4,587,520 query-rule evaluations (70 checkpoints × 32,768 queries × 2 reference rules) and cannot affect any flag.

## Critical reading

**P6-E.**

What the records establish:
- The optimized paths T1–T5 and F1/F2 return the reference selections on every checkpoint, query and fixture recorded. T1–T3, F1 and F2 are bitwise; T4 and T5 differ by ≤ 1.9e-6 in score and ≤ 4.8e-6 in logit.
- The registered procedure was followed: one invocation per stage, screen-to-confirm linkage, and comparator chosen by the fixed rule.
- At W8 the point estimates are large and consistent in sign: T5 runs at about 0.29× the original tree and about 0.73–0.75× the comparator at addition, 0.79–0.81× at model forward. They hold in every pair, every parent and almost every matched round.

What they do not establish:
- Any registered PASS. Under §3.4 a point estimate taken under failed reliability is INCONCLUSIVE and may not be re-timed. The 27% unusable rate, 40 times P5's, is itself the finding about measurement quality on this run. Describing SP or PR as "met" would contradict the registered rule.
- That the tree is faster than flat in general. At W1 T5 is 21–46% slower than F1, and at single-token calls 3–5× slower.
- Anything about P5's L or composite outcome, quality, capacity scaling or storage.

On fairness:
- The comparator choice of F1 over F0 was a 0.37% decision under unreliable screen data, and it is immaterial: the comparisons with F0 are nearly identical.
- The tree received five optimization variants, including a selection kernel that helps on 512-wide rows. The flat side received normalization caching and the same kernel, which was 2.3× slower on 4,096-wide rows. No flat variant targeted flat's dominant `topk` cost with a method suited to wide rows.
- Within the approved list the comparison is as registered. Read it as "optimized tree vs. cached-normalization flat", not as a comparison against an equally optimized flat. PENDING LEAD REVIEW.
- I found no sign that the speedup depends on the guard-band fallback rate at the observed 0.1–0.7%. It does depend strongly on the workload.

**P6-Q.**

What the records establish:
- The top-2 restriction materially changes the selection relative to the tree's own exhaustive rule. This is clear for fixed (recall_P 0.79) and smaller for learned (0.91).
- The exhaustive cosine rule shares only about 27% of slots with T2P.
- Evaluating the same weights exhaustively does not improve NLL (|Δ_restrict| ≤ 0.0014 in every cell).
- Lost slots are almost all trained slots, sit mostly in route ranks 3–4, and carry small softmax weight.

What they do not establish:
- Whether training with wider search, or without the prior, would help (§4.2 asymmetry; §4.5 row 3).
- That learned routing is "better": its higher fidelity tracks a sharper prior.
- Whether the prior's effect exceeds 0.005. It is directionally consistent, 0.0011 short of the margin, and on a single already-observed panel.

What could mislead:
- Reading low recall as lost information. Lost slots are trained but carry little weight, and exhaustive evaluation does not help.
- Reading the fixed-vs-learned recall gap as routing quality.
- Reading the "unchanged" per-token group as a counterfactual control.
- Reading step-0 means (backbones 101–102 only, memory effect about 1e-7) alongside final means.

## Open questions (PENDING LEAD REVIEW)

1. P6-E reliability: should the instability (27% unusable vs 0.65% in P5) be investigated as a machine-state issue before any future timing study? The records hold no load, thermal or frequency data. No re-run of P6-E is implied: §3.7 forbids it.
2. Whether the W1/Wtok reversal (T5 slower than flat) should be stated alongside any W8 description in the result report.
3. Whether the asymmetric optimization effort (5 tree variants vs 2 flat) limits the meaning of the tree-vs-flat point estimates.
4. Whether any statement about learned-router fidelity beyond "sharper prior" is supportable.
5. How to report PRIOR: registered FAIL, with a uniformly positive sign and 0.0011 short of the margin.
6. Whether the metadata mislabelling in the P6-E worker manifests (ADR-0003 / G0) should be annotated in the result report. The records themselves are immutable.

## Could not verify

- **P6-E per-query equivalence.** I recomputed classes from the per-checkpoint summaries and confirmed that the mismatch files are empty. I did not and could not recompute selections, scores, logits or NLL, which would need model forwards, and those were out of scope.
- **The timing values themselves.** I checked that raw samples, summaries and the local per-block logs are internally consistent. I did not re-time anything, and no record exists that could explain the instability (system load, thermal state, CPU frequency).
- **P6-E memory-profiler and RSS figures.** Reported as recorded. Only the persistent-byte figure was checked for arithmetic plausibility.
- **P6-Q raw arrays beyond the sample.** I checked 4 of 70 checkpoints. Coverage L2 distances were not recomputed.
- **P6-Q gate (ii).** The full X16P score matrices are not stored, so I could not re-check it from arrays.
- **P6-Q gate (iv) reference.** The float64 reference outputs are not stored as arrays. That reference was also written by the auditor role, so my review of gate (iv) is not independent of it.
- **Registered NLL values.** They need forwards. I checked only their equality with P5's records and their consistency with the per-token arrays in the sample.
