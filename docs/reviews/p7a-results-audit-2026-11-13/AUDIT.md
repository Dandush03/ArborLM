# P7-A results audit: independent recomputation and critical reading

- Auditor model: Claude Opus 5.5 (`claude-opus-5-5`), auditor role. Date 2026-11-13.
- Scope: recompute the registered criteria and the main descriptive results of the single registered P7-A run from the per-checkpoint records (and, where stated, from the raw local traces), then give a critical reading. No study stage or model was rerun. Nothing outside this folder was written.
- **Status of this document:** independent engineering and mathematical evidence. **It is not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

## Material and environment

| Item | Value |
|---|---|
| Branch / HEAD | `claude/p7a-storage-locality-proposal` at `61657cf` (freeze `e95cec6`) |
| Trace run | `P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e` |
| Simulation run | `P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b` (81 worker records) |
| Analysis run | `P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a`, `analysis.json` sha256 recorded in `recompute_p7a.json` |
| Raw traces | `experiments/P7AT-…/traces/<label>/` (sha256 checked against the records for all 81) |
| Python | `.venv/bin/python -I`, CPython 3.12.14, standard library only; no `arborlm` import; `p7a_analysis.py` not reused |
| Hardware | Apple M5 Max, macOS 27.2 (same machine as the run) |

Command (from the repository root), final run:

```sh
.venv/bin/python -I docs/reviews/p7a-results-audit-2026-11-13/recompute_p7a.py \
  --raw-primary-all --raw-full b103-o303-flat-s503 b103-o303-fixed_tree-s503 b103-o303-learned_tree-s503 \
  > docs/reviews/p7a-results-audit-2026-11-13/recompute_attempt4_final.log
```

47 s wall time. `recompute_p7a.py` sha256 `715f5756…22af`; output `recompute_p7a.json` sha256 `1e8779da…3ddf`.

Attempts. All are kept:

| Log | What happened |
|---|---|
| `recompute_attempt1_noraw.log` | **Failed check, auditor's own errors.** 39 differences against `analysis.json` and 81 integrity "problems". (a) 36 were string formatting only: `str(Fraction(0))` is `'0'` and the analysis writes `'0/1'`. (b) 3 learned-tree grid cells (R2C128, R8C32, R32C8): my code labelled CONC `HOLDS` where the analysis says `DEGENERATE`. The analysis is right. ADR §7 says that in a DEGENERATE setting *every* criterion is DEGENERATE, and item 9 only adds a flat floor on top of that; my first version applied item 9's floor alone. (c) I compared the P5 `checkpoint_state_sha256`, which is a dict by step, as a scalar. It should be the `checkpoint-512` entry. |
| `recompute_attempt2_noraw.log` | After the fixes: 28,545 values compared, 0 differences, 0 integrity problems. |
| `recompute_attempt3_raw.log` | Same run with the raw-trace checks: 0 differences, 0 raw problems. |
| `recompute_attempt4_final.log` | Same as attempt 3, plus a capacity lower-bound check, which found discrepancy D1. This run produced the JSON that is kept. |

The attempt-1 and attempt-2 JSON outputs were written to the session scratchpad and are not kept. The logs above are what remains of them.

## Verified

1. **Registered verdicts reproduce exactly** (exact rational arithmetic, ties counted as not lower):
   - fixed_tree: LRU **HOLDS**, CONC **HOLDS**, so the outcome is **CONCENTRATION-ONLY**. BR **FAILS**.
   - learned_tree: LRU **HOLDS**, CONC **HOLDS**, so the outcome is **CONCENTRATION-ONLY**. BR **FAILS**.
   - The robustness rule does not apply, because neither outcome is STRUCTURAL ADVANTAGE. In no other non-degenerate setting with R ≤ 8 does LRU hold while CONC fails.
2. **Every number in `analysis.json` that I could map was reproduced: 28,545 values, 0 differences.** That covers the criteria, both 30-cell grids, both BR grids, the decomposition (by architecture and per checkpoint), pages against the uniform reference, warm capacity misses by layout, cold misses and amplification, context-shuffled against actual, page reuse, branch locality, utilization, eviction sensitivity, SSD key reads, the flat exchangeability report, the bootstrap table and the cumulative curves.
3. **Raw traces.**
   - All 81 checkpoints: trace sha256 matches; IDs are in range and distinct within each query; every tree selection lies in a visited branch; the evaluation histogram equals P5's `selected_slot_counts`; effective slots equal P5's to within 0.0.
   - All 81 checkpoints: I re-simulated the primary setting (R=2, C=32, L-FREQ, actual stream) from the raw traces with my own LRU, under both the ascending (registered) and descending eviction orders. Every miss count matches.
   - All 81 checkpoints × 3 replicates: I regenerated the exact count-preserving frequency-matched stream from ADR item 8 with `random.Random`. The stream sha256, the swap count, the per-slot counts, the distinct-slot check and the primary miss counts all match. **CONC is therefore reproduced end to end from the raw traces, not only from the records.**
   - Full re-simulation of 3 checkpoints outside the 18 already checked (chosen by the rule "last checkpoint of each architecture in registered order"). This covers every R and C on the actual stream under L-ID, L-FREQ and L-BFREQ, and the three FM streams under L-ID and L-FREQ: 780 cache configurations and 1,262 stream statistics, with 0 differences. It also covers the uniform closed form per layout (exact rational arithmetic, 0 differences) and the branch-locality statistics (0 differences).
4. **Integrity from the records** (§9 and item 2 of the brief):
   - 81 of 81 completed.
   - 81 of 81 bitwise NLL replays; each recorded NLL equals P5 `final.nll`; checkpoint files unchanged; the state hash matches P5's `checkpoint-512`.
   - 81 of 81 FM `counts_equal_trace` and `distinct_slots_per_query` true, with the correct generator seed and cell index.
   - 7,614 stream × layout × R groups and 38,070 cache results: first-touch misses do not depend on C and equal the stream's distinct pages; capacity misses never increase with C (warm and whole-stream); misses never exceed touches; cold misses are never below distinct pages; the histograms agree with `pages_sum`; the warm-up split agrees with the first-half distinct count.
5. **Resource caps.**

   | Stage | Active time | Cap | Peak RSS |
   |---|---:|---:|---:|
   | trace | 135.3 s | 900 s | 556 MB |
   | simulate | 765.9 s | — | 517 MB (largest worker process tree 329 MB) |
   | analyze | 0.34 s | — | — |
   | simulate + analyze | 766.2 s | 3,600 s | — |
   | combined | 901.5 s | 4,500 s | — |
   | auditor's independent simulator (separate budget) | 186 s | 1,800 s | — |

   Every RSS figure is below the 2 GiB cap. Margins: trace 6.7×, simulation and analysis 4.7×.

## Discrepancies

| ID | Severity | Finding |
|---|---|---|
| **D1** | Major for the descriptive SSD-index table. **No criterion is affected.** | **Tree key-read simulation lets the cache exceed its capacity.** `p7a_sim.lru_pass` evicts only `while len(cache) > capacity and len(cache) > n`. When a query touches n > C pages, the cache grows to n. For values n ≤ 8 ≤ C, so this never triggers: 0 violations in all value results. Tree keys under L-RAND are different. At 4 KiB each query touches all 64 key pages, and at 16 KiB all 16. The record nevertheless shows ≈0 warm misses at C = 8, 16 and 32 (respectively C = 8), where a cache of C pages must miss at least n − C pages per query. My lower-bound check finds **648 violations** (27 cells × 3 seeds × 8 key settings), all in tree-key L-RAND. Flat's key reads are computed under the opposite convention (strict capacity: all 64 pages miss when C < 64). The table therefore compares two different cache models. For example, `analysis.json` gives fixed-tree keys at R2/C32 as 0.38 misses per query (the mean of L-ID 1.52 and three L-RAND ≈0.003) against flat's 64. Under flat's own convention, tree L-RAND would also be 64 per query, and that mean would be about 48. The label and note in `analysis.json` do not disclose this. The value-page results and every verdict are unaffected. |
| **D2** | Minor (records and documentation) | Stage manifests record `deterministic_algorithms: false` and `threads: {intra_op: 6}`. That is the orchestrator's state. The workers call `configure_deterministic_cpu()` in code, but no worker record states it. ADR item 13 ("workers write their own environment record") is not evidenced in the records I read. The bitwise NLL replay of all 81 checkpoints is the substantive evidence for the trace stage, and the simulation is integer bookkeeping. |
| **D3** | Minor | Simulate and analyze manifests record `git_dirty: true`. `tracked_state_sha256` is the empty-input hash `e3b0c442…`, which is consistent with dirtiness from untracked result files only, not from tracked edits. I did not verify this further. |
| **D4** | Note (auditor-side, resolved) | My attempt-1 errors are described in the attempt table above. Each one was mine. None was a difference in the implementation. |

Both readings of BR's non-degeneracy condition were checked: tree L-RAND floor only, and that floor plus a flat L-RAND floor. They give the same status in every cell.

## Findings by item

m means warm capacity misses per query. Means are over 27 checkpoints. "Primary" means R=2, C=32, L-FREQ, actual stream.

### 1. Primary criteria

| | flat | fixed | learned |
|---|---:|---:|---:|
| m, actual stream | 3.1645 (466619/147456) | 2.0995 (464377/221184) | 1.6495 (364849/221184) |
| m, FM stream (mean of 3) | 3.3385 | 2.2923 | 1.7847 |

| Clause | fixed | learned |
|---|---|---|
| Non-degenerate (flat ≥ 0.05, tree ≥ 0.01) | yes | yes |
| LRU: ratio of means ≤ 0.80 | 0.6635 | 0.5213 |
| LRU: pairs strictly lower (≥ 22/27), ties | 24, 0 tied | 27, 0 tied |
| LRU: parent means lower (≥ 8/9) | 9 | 9 |
| **LRU** | **HOLDS** | **HOLDS** |
| CONC flat floor (FM flat 3.3385 ≥ 0.05) | met | met |
| CONC: ratio / pairs / parents | 0.6866 / 24 / 9 | 0.5346 / 27 / 9 |
| **CONC** | **HOLDS** | **HOLDS** |
| **Outcome** | **CONCENTRATION-ONLY** | **CONCENTRATION-ONLY** |
| BR at R2C32: L-ID / L-RAND (ratio) | 4.196 / 4.241 (0.989) | 3.799 / 3.864 (0.983) |
| BR: cells / parents lower | 17 / 8 | 22 / 8 |
| **BR** | **FAILS** | **FAILS** |

**Grid.** In every non-degenerate cell, LRU and CONC give the same verdict: 14 cells for fixed, 11 for learned. The largest gap between the LRU and CONC ratios is 0.024 (fixed) and 0.014 (learned). The per-cell table, with status, means and clauses, is in `recompute_p7a.json` under `criteria.<kind>.grid`. In summary:

- **R = 1 and R = 2:** C = 8 and 16 fail. Exception: learned R2C16 and R1C32 hold, with LRU ratios 0.747 and 0.749. C = 32 and 64 hold. At C = 128: fixed fails on the pairs clause (21 of 27 pairs lower, although the ratio is 0.28); learned is DEGENERATE at R2C128.
- **R = 8:** C = 8 and 16 hold. Fixed R8C32 fails on pairs (20 of 27). C = 64 and 128 are DEGENERATE.
- **R ≥ 32:** DEGENERATE everywhere except fixed R32C8. That cell is non-degenerate (flat 0.1004, fixed 0.0303) and fails on pairs (21 of 27).

### 3. Registered decomposition (primary R and layout; mean of per-checkpoint ratios, with [min, max])

| Step | flat | fixed | learned |
|---|---|---|---|
| (a) pages/query: uniform | 7.9932 | 7.9492 | 7.9494 |
| FM / uniform (concentration) | 0.959 [0.945, 0.973] | 0.947 [0.878, 0.969] | 0.940 [0.912, 0.967] |
| OS / FM (co-selection) | 0.928 [0.890, 0.983] | 0.934 [0.863, 1.025] | 0.926 [0.874, 0.979] |
| actual / OS (temporal order) | 1.000 (order-free, exact) | 1.000 | 1.000 |
| (b) m: FM | 3.339 | 2.292 | 1.785 |
| OS / FM (co-selection) | 0.988 [0.958, 1.008] | 0.980 [0.929, 1.029] | 0.995 [0.943, 1.050] |
| actual / OS (temporal order) | 0.955 [0.888, 0.983] | 0.931 [0.864, 0.975] | 0.920 [0.861, 0.992] |
| **actual / FM (structure beyond concentration)** | **0.944 [0.851, 0.977]** | **0.912 [0.849, 0.964]** | **0.915 [0.826, 0.986]** |
| cells with actual < FM | 27/27 | 27/27 | 27/27 |
| context-shuffled / actual | 0.997 | 1.005 | 1.002 |

Answers to the questions in item 3:

- **How much lower is the actual stream than its own FM null?** In every one of the 27 cells for every architecture. The reduction is 5.6% for flat and 8.8% / 8.5% for fixed / learned.
- **Is that structure larger for trees than for flat?** Slightly. The paired difference in actual/FM (tree minus flat) is −0.032 for fixed (tree lower in 23/27 pairs) and −0.029 for learned (19/27).
- **Where does the structure come from?** Mostly from temporal order within contexts (actual/OS), not from co-selection (OS/FM). Co-selection is where branch structure would show, and it is nearly 1 for every architecture.
- **How much of the tree advantage does the null account for?** The FM gap reproduces 98.2% (fixed) and 102.6% (learned) of the flat−tree gap on the actual stream.

### 4. Pages per query against the uniform reference (mean pages / mean uniform)

| R | flat ID | flat RAND | flat FREQ | fixed ID | fixed RAND | fixed FREQ | learned ID | learned RAND | learned FREQ |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 1.000 | 1.000 | 0.890 | 0.999 | 1.000 | 0.884 | 0.998 | 1.000 | 0.871 |
| 8 | 0.999 | 0.999 | 0.656 | 0.985 | 0.998 | 0.614 | 0.987 | 0.999 | 0.593 |
| 32 | 0.998 | 0.999 | 0.380 | 0.969 | 0.996 | 0.366 | 0.920 | 0.996 | 0.339 |
| 128 | 1.000 | 0.997 | 0.189 | 0.921 | 0.997 | 0.264 | 0.836 | 0.993 | 0.248 |
| 512 | 0.997 | 1.002 | 0.191 | 0.929 | 1.000 | 0.359 | 0.864 | 1.000 | 0.354 |

R = 1 is 8/8 everywhere.

**Tree/flat ratio at R=32, L-ID:**

| | Actual pages | Uniform (by construction) |
|---|---:|---:|
| fixed / flat | 0.809 | 0.833 |
| learned / flat | 0.768 | 0.833 |

The closed form is 6.4876 / 7.7911 = 0.8327. Fixed's per-query advantage is almost entirely by construction. Learned's has about 8% more.

### 5. Actual row sizes (R = 32, 128, 512, i.e. 4, 16 and 64 KiB blocks)

- **Degeneracy:** DEGENERATE in 14 of 15 cells for fixed and 15 of 15 for learned. The only non-degenerate cell is **fixed R32C8**: flat 0.1004, fixed 0.0303, ratio 0.30, 21 of 27 pairs lower. LRU **FAILS** on the pairs clause, CONC **FAILS** likewise, so the cell's outcome is NO ADVANTAGE.
- **L-FREQ m at C = 8:**

  | R | flat | fixed | learned |
  |---|---:|---:|---:|
  | 32 | 0.100 | 0.030 | 0.0085 |
  | 128 | 0.0013 | 0.0008 | 0.0005 |
  | 512 | 0 | 0 | 0 |

- At C ≥ 16 (R=32) or C ≥ 32 (R=128) every value is ≤ 0.002 or exactly 0.
- This confirms P7-H3.

### 6. Layouts (m, actual stream)

| R2C32 | L-ID | L-RAND | L-FREQ | L-BFREQ | FREQ/ID |
|---|---:|---:|---:|---:|---:|
| flat | 5.213 | 5.209 | 3.164 | — | 0.607 |
| fixed | 4.196 | 4.241 | 2.099 | 1.781 | 0.500 |
| learned | 3.799 | 3.864 | 1.650 | 1.416 | 0.434 |

- **Frequency packing** removes about 39% of misses for flat and 50% / 57% for fixed / learned.
- **L-BFREQ** removes a further 15% / 14% for trees. This is a hierarchy-aware layout that is not part of the registered comparison, and flat has no counterpart in the study.
- **BR across the grid:**
  - At R ≤ 2, L-ID ≈ L-RAND (ratios 0.98–1.00); BR fails.
  - At R=8 it holds only at large C (fixed C128; learned C64 and C128).
  - At R=32 it holds strongly (C ≤ 64), and also at R=128 (C ≤ 16), with ratios 0.06–0.78.
  - In those same cells L-FREQ is more than 100× lower than L-ID, and often exactly 0. For example, fixed R32C8: L-ID 4.98, L-FREQ 0.030 (166×); learned R32C8: 4.53 against 0.0085.
  - So branch contiguity beats slot-wise random placement and loses heavily to frequency packing.
- **Flat L-ID outside the range of its three L-RAND layouts:** 10–20 of 27 cells in the non-trivial cells. This is consistent with exchangeability (report-only).

### 7. Utilization

| | unique slots: mean [min, max] | effective slots: mean [min, max] | P5 NLL mean |
|---|---|---|---:|
| flat | 428.6 [221, 555] | 132.3 [85.1, 199.0] | 2.33369 |
| fixed | 383.4 [276, 488] | 96.3 [42.9, 142.2] | 2.33450 |
| learned | 313.1 [226, 434] | 83.0 [55.2, 124.0] | 2.33508 |

**Effective slots against primary m:**

| | Pearson | Spearman |
|---|---:|---:|
| flat | 0.981 | 0.991 |
| fixed | 0.991 | 0.987 |
| learned | 0.991 | 0.970 |
| pooled, 81 checkpoints | 0.983 | 0.993 |

- Pooled R² is 0.966 for effective slots alone and 0.967 when architecture intercepts are added.
- At equal effective slots the fitted m is 2.325 (flat), 2.324 (fixed) and 2.264 (learned).
- 97.4% of cross-architecture checkpoint pairs are ordered the same way by effective slots as by m.
- **Utilization alone orders the checkpoints regardless of architecture.** Learned is about 2.6% below the pooled fit.

**m against P5 NLL within architecture:**

| | Pearson | Spearman |
|---|---:|---:|
| flat | −0.16 | −0.14 |
| fixed | +0.22 | −0.005 |
| learned | −0.11 | −0.22 |

There is no detectable relation. Paired NLL (tree − flat) is +0.0008 for fixed (tree higher in 15/27 pairs) and +0.0014 for learned (19/27). The trees' lower utilization therefore came with no NLL benefit. At this resolution (NLL SD ≈ 0.02 across seeds) it came with no measurable NLL cost either.

### 8. Temporal structure (pooled reuse fraction with the immediately preceding query)

| R2, L-FREQ, within / across | actual | order-shuffled | context-shuffled | FM |
|---|---|---|---|---|
| flat | 0.142 / 0.125 | 0.144 / 0.152 | 0.142 / 0.145 | 0.170 / 0.169 |
| fixed | 0.205 / 0.185 | 0.208 / 0.214 | 0.205 / 0.205 | 0.230 / 0.231 |
| learned | 0.220 / 0.203 | 0.223 / 0.231 | 0.220 / 0.220 | 0.252 / 0.251 |

- **Immediate-predecessor reuse in the actual stream is at or below the order-shuffled level.** At L-ID R2 it is clearly below: flat 0.079 vs 0.094.
- **Yet actual m is 4–8% below order-shuffled.** The cache benefit therefore comes from reuse over a window of several queries, not from consecutive queries. The registered reuse metric does not capture it.
- Context-shuffled vs actual m differs by at most 0.5% (mean ratio 0.997–1.005), consistent with contexts being unrelated.
- The across-context column rests on only 511 pairs per checkpoint.

### 9. Branch locality and keys

**Branch locality (pooled values, which is the analysis's definition):**

| | fixed | learned |
|---|---:|---:|
| same top-1 branch, within / across contexts | 0.196 / 0.193 | 0.208 / 0.204 |
| chance level (Σp² of the top-1 distribution) | 0.218 | 0.232 |
| share a visited branch, within / across | 0.417 / 0.388 | 0.497 / 0.466 |
| top-1 mean run length | 1.25 | 1.27 |
| distinct branches per 64-query context (of 16) | 13.1 | 10.1 |

Consecutive queries pick the same top-1 branch slightly *less often* than chance. There is no branch persistence.

**Keys:**

- Flat (analytical): 64 pages per query at 4 KiB when C < 64, 0 when C ≥ 64. At 16 KiB: 16 pages when C = 8. At 64 KiB: 0.
- Trees under L-ID (simulated, valid): R2C32 1.52 (fixed) and 0.57 (learned); C=8: 6.03 and 5.64; 0 at C ≥ 64.
- Tree L-RAND key numbers are invalid (D1).

### 10. Misses and amplification

| L-FREQ | first-touch / query, whole stream | cold / query | warm capacity m | cached amplification (capacity) | uncached amplification |
|---|---|---|---|---|---|
| R2C32 flat | 0.0076 | 3.154 | 3.164 | 0.791 | 1.779 |
| R2C32 fixed | 0.0068 | 2.103 | 2.100 | 0.525 | 1.756 |
| R2C32 learned | 0.0055 | 1.653 | 1.650 | 0.412 | 1.731 |
| R32C8 flat | 0.0016 | 0.101 | 0.100 | 0.402 | 11.83 |
| R32C8 fixed | 0.0014 | 0.031 | 0.030 | 0.121 | 9.76 |
| R32C8 learned | 0.0011 | 0.0093 | 0.0085 | 0.034 | 9.05 |
| R32C32 flat / fixed / learned | 0.0016 / 0.0014 / 0.0011 | ≤ 0.0018 | 0.0004 / 0.0002 / 0.0001 | ≤ 0.002 | as above |

### 11. Eviction order (primary setting)

| | ascending m (registered) | descending m | desc / asc | cells where descending is lower |
|---|---:|---:|---:|---:|
| flat | 3.164 | 3.080 | 0.973 | 27/27 |
| fixed | 2.100 | 2.026 | 0.965 | 27/27 |
| learned | 1.650 | 1.588 | 0.962 | 27/27 |

Under descending order:

- LRU: fixed 0.658 (24/27, 9/9), learned 0.516 (27/27, 9/9). Both **HOLD**. **No verdict changes.**
- The CONC stream was not simulated with descending order, so CONC under descending order is not available.

**Mechanism.** Under L-FREQ, low page numbers hold the hottest rows, so the ascending tie rule evicts hot pages first. That is a small systematic penalty on L-FREQ, visible even at R=1, where the layout otherwise cannot matter (flat C32: L-FREQ 5.306 vs L-ID 5.266). The penalty is slightly larger for trees.

### 12. Bootstrap over contexts (pages per query; 1,000 resamples; implementation's generator)

| R2, L-FREQ | flat | fixed | learned |
|---|---:|---:|---:|
| mean interval width | 0.016 | 0.017 | 0.017 |
| between-checkpoint SD | 0.17 | 0.25 | 0.30 |

- The architecture differences (flat − fixed 0.09; flat − learned 0.19) are 5–12 times the interval widths, but smaller than the SD across training seeds.
- My own bootstrap (stdlib generator, 3 checkpoints) gives widths within about 10% of the recorded ones.
- The bootstrap does not cover m.

### 13. Calibration-to-evaluation transfer (raw traces, all 81)

| | flat | fixed | learned |
|---|---|---|---|
| evaluation selections on slots with zero calibration count | 0.02% [0.01, 0.04] | 0.02% [0.01, 0.03] | 0.02% [0.01, 0.03] |
| evaluation-used slots with zero calibration count (mean) | 44.6 | 40.2 | 31.7 |
| evaluation mass in the first 64 L-FREQ rows | 71.5% | 81.9% | 86.1% |
| shortfall against the evaluation trace's own top 64 | ≤ 0.08 pp | ≤ 0.13 pp | ≤ 0.07 pp |

Transfer is essentially perfect and does not differ by architecture. The 64-row mass column restates concentration.

### 14. Resources

All within caps; see Verified item 5.

## Critical reading

**What the records establish.** The computation is right. Every registered number reproduces from the records, and the primary actual-stream and FM results reproduce from the raw traces for all 81 checkpoints. Under the registered page model, with frequency packing, a 32-page cache and hypothetical 2 KiB rows, both trees incur fewer warm capacity misses than flat: 34% fewer (fixed) and 48% fewer (learned). Under the registered rule this is **CONCENTRATION-ONLY** for both. The exact count-preserving null reproduces 98% and 103% of the flat−tree gap. Across all 81 checkpoints, effective slot count alone explains 96.6% of the variance in m, and adding architecture moves R² by 0.0007. In plain terms, the page model mostly measures how concentrated a checkpoint's slot selections are, and the trees are more concentrated.

**The CONCENTRATION-ONLY logic and the structure that remains.** A null that reproduces the advantage does not show that no structure exists. Here the structure can be quantified:

- Every architecture, flat included, sits below its own FM null in all 27 cells. Flat by 5.6%; fixed and learned by 8.8% and 8.5%. The trees' excess over flat is about 3 points, larger than flat's in 23/27 and 19/27 pairs.
- Almost all of it is temporal reuse over several queries within a context. Co-selection inside a query, which is where branch structure would appear, contributes about 1–2% and less for learned than fixed. Branch persistence is at or below chance.
- The one hierarchy-specific effect the records show is that branch-aware packing (L-BFREQ) cuts misses a further 15%. It is outside the registered comparison, and flat's comparable layout (co-access clustering) was never built.

Whether a 3-point within-context temporal excess, or the L-BFREQ effect, deserves follow-up is **PENDING LEAD REVIEW**. Neither was registered, and neither amounts to a STRUCTURAL ADVANTAGE under §7.

**The 0.80 threshold.**

- It sits nowhere near the primary ratios (0.66 / 0.69 and 0.52 / 0.53).
- In the grid it sits close to fixed R1C32 and R2C16 (LRU 0.82, CONC 0.83: both fail) and learned R1C32 and R2C16 (0.75 / 0.76: both hold).
- Because LRU and CONC ratios never differ by more than 0.024, no placement of the threshold could have produced a STRUCTURAL ADVANTAGE in any cell. The outcome does not depend on the threshold.
- Several low-miss cells with extreme ratios (about 0.28–0.30) fail on the 22/27 pairs clause. The grid's "NO ADVANTAGE" labels there reflect consistency, not magnitude.

**P7-H1 against the outcome.**

- The lead predicted that LRU would **not** hold. It holds for both tree kinds with wide margins. That part of the prediction failed and should be recorded as failed.
- The second part, that the FM null would reproduce whatever advantage appears, was borne out.
- P7-H2 (L-ID < L-RAND for trees): right in direction almost everywhere, but negligible at R ≤ 2, so BR fails at the primary setting. It holds strongly at R=32 and R=128.
- P7-H3: confirmed.
- P7-H4: confirmed for fixed (0.809 against 0.833 by construction). For learned it is partly confirmed (0.768): learned has about 8% beyond the by-construction ratio.

**Lower utilization: benefit or cost?** P5's NLL does not separate the architectures: tree − flat is +0.0008 and +0.0014, tree higher in 15/27 and 19/27 pairs. Within each architecture, a checkpoint's page reads are unrelated to its NLL (|r| ≤ 0.22). The trees' fewer page reads therefore bought no measured quality, and their under-use of stored rows (313–383 of 4,096 unique slots against 429) cost no measured NLL at this size. In storage terms, fewer distinct rows touched is cheaper. In capacity terms, it is stored memory the model does not use. ADR §8 leaves the choice between those readings open, and it is **PENDING LEAD REVIEW**. Nothing here credits concentration as an advantage.

**H3, H4 and H5.**

- H3: no locality objective was trained. These records are a baseline: untrained locality is explained almost entirely by concentration. They also suggest that a locality objective could "succeed" simply by concentrating, so any future H3 test needs this study's FM null or an equivalent (**PENDING LEAD REVIEW**).
- H4: the screen gives no hierarchy-specific argument at this size under this page model, and P7-A makes no device statement.
- H5: untouched; there is one memory size.

**NVMe on these checkpoints.** I agree that it is uninformative. At the true row size (R=32, 4 KiB), frequency packing and a 128 KiB cache (C=32) give 0.0001–0.0004 warm capacity misses per query, and 0 at C ≥ 64. The entire value store is 512 KiB, or 128 pages. Any device run would measure the operating system's page cache.

**What could mislead.**

1. **"The trees read 34–48% fewer cached pages."** Correct under the model, but it is a utilization effect. The FM null and utilization should always be quoted alongside it.
2. **R=2 is hypothetical.** Selections are unchanged; with 64 cached rows against 221–555 used slots, the primary setting is close to a measurement of each checkpoint's mass outside its top 64 rows (28.5% flat, 18.1% fixed, 13.9% learned).
3. **The SSD-index table (D1).** It overstates the trees' key-read advantage, because tree L-RAND key reads are near 0 only through a cache-overflow artefact.
4. **The registered eviction tie rule slightly penalizes L-FREQ.** No verdict depends on it.
5. **Per-query page differences look significant against the context bootstrap,** but the bootstrap does not cover training randomness, which is 10–20 times larger.
6. **Consistency counts are not significance tests** (as the ADR states).

## Could not verify

- L-RAND layouts, the order-shuffled and context-shuffled permutations, and the bootstrap draws use `torch` generators. I did not regenerate them with the standard library, so those streams were checked only through the records' internal invariants and cross-stream consistency. L-RAND page counts at R=1 equal 8 per query, and order-free per-query metrics of the shuffled streams equal the actual stream's exactly.
- That the workers ran single-threaded and deterministic (D2), beyond the bitwise NLL replay.
- The cause of `git_dirty: true` (D3), beyond the empty tracked-state hash.
- The FM stream under descending eviction (not simulated by the study).
- Anything about devices, latency, larger memories or quality beyond P5's recorded NLL.

## Open questions (PENDING LEAD REVIEW)

1. Whether D1 should be corrected in a descriptive addendum. Two options: report tree L-RAND key reads under strict capacity, as flat's are computed, or mark per-query key pages > C as outside the model. Records and code are immutable, so this would be a new file.
2. Whether the roughly 3-point within-context temporal excess of trees over their FM null, and the L-BFREQ gain, merit any follow-up. Neither is a registered result.
3. How to treat lower utilization (benefit or waste) in any future storage proposal, given P5's NLL parity.
4. Recording P7-H1 as a failed prediction in its first clause.
