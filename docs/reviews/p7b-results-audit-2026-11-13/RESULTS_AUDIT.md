# P7-B results audit: independent recomputation from the simulation records

- Auditor role: Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-13 (records time-stamped 2026-11-14 UTC).
- Scope: ADR-0014 §§2, 4–11, 15. Records under `results/p7b-2026-11-13/` (panel, layouts, trace-b, simulate-a, simulate-b, analyze), compared with the implementation's `analyze/P7BA-…/analysis.json` (SHA-256 `6c142fc0…c9db47c9`).
- **This is independent engineering and mathematical evidence. It is not Astra validation and not human approval.** Astra review: NOT_PERFORMED. Scientific questions are marked PENDING LEAD REVIEW.
- I wrote nothing under `src/`, `configs/`, `results/`, `experiments/` or the ADRs, ran no study stage and no model, and left the existing confirmation, detail and log files in this folder unchanged.

## Commands and environment

Python 3.12.14 (`.venv/bin/python`, Clang 22.1.3), macOS 27.2 arm64 (Apple M5 Max), standard library only, run from the repository root at HEAD `65ed720`.

| # | Command | Result | Output |
|---|---|---|---|
| 1 | `.venv/bin/python -I docs/reviews/p7b-results-audit-2026-11-13/recompute_p7b.py --repo . --out docs/reviews/p7b-results-audit-2026-11-13/recompute_p7b.json` | 6,103 values compared with `analysis.json`, **0 differences**, largest relative difference 1.8e-16, 0 integrity problems, 3.0 s | `recompute_p7b.json`, `recompute_p7b.log` |
| 1a (failed attempt, kept) | the same command, first version of the script, output to the scratchpad | 18 differences; all 18 were my own comparison mistakes (see Discrepancies) | `failed_attempts/recompute_p7b.attempt1.py`, `failed_attempts/recompute_attempt1.json`, `failed_attempts/README_recompute_attempt1.txt` |
| 2 | `.venv/bin/python -I docs/reviews/p7b-preflight-2026-11-13/tools/independent_resim.py --repo . --stream A --jobs 1 --selection b102-o301-flat-s501 b101-o302-fixed_tree-s501 b101-o303-learned_tree-s502 --hash-table results/p7b-2026-11-13/layouts/P7BL-…/layout_hash_table.json --simulate-dir results/p7b-2026-11-13/simulate-a/P7BSA-… --out …/extra_resim_confirmation_A.json --detail …/extra_resim_detail_A.json` | **AGREE**, 3 checkpoints, 380 simulations, 0 differences, 31.1 s | `extra_resim_A.log`, `extra_resim_confirmation_A.json`, `extra_resim_detail_A.json` |
| 3 | the same with `--stream B --simulate-dir …/simulate-b/P7BSB-… --trace-b-compact results/p7b-2026-11-13/trace-b/P7BT-… --trace-b-dir experiments/P7BT-…/traces` | **AGREE**, 3 checkpoints, 380 simulations, 0 differences, 30.2 s | `extra_resim_B.log`, `extra_resim_confirmation_B.json`, `extra_resim_detail_B.json` |
| 2a/3a (failed attempt, kept) | commands 2 and 3 with the labels in an unquoted zsh variable | StopIteration: zsh passed the three labels as one argument; my command error | `failed_attempts/extra_resim_{A,B}.attempt1.log`, `failed_attempts/README_extra_resim_attempt1.txt` |

Tool hashes: `recompute_p7b.py` `fd57ca6c…caa3`; `recompute_p7b.json` `7fc9a91b…142a`; the auditor's committed tools are unchanged (`independent_layouts.py` `bfb21a57…77b9`, `independent_resim.py` `4e53ebbc…02f1`; `git diff --quiet HEAD` checked before commands 2 and 3).

**Definitions used (taken from the ADR, written without reference to `p7b_analysis.py`).** m = (misses_warm − first_touch_warm) / 16,384 counted queries. E = m(actual, L) / mean of m(null_k, L-FREQ) over three nulls, under the same R, C and tie rule. S = m(actual, L) / mean m(null_k, L). G = m(actual, L) / m(actual, L-FREQ). x = ln(effective slots) of the stream being analysed. The OLS of E on [1, x, tree] over 54 cells is solved exactly in rationals, with E an exact ratio of integer counts. Parents are (backbone, order). Pairs are (backbone, order, seed).

## Verified

1. **Every registered classification, outcome, pairing, decision class and the recommendation row** agree exactly with `analysis.json` on both streams. That covers 8 HB, 8 HU and 8 PART classes per stream, and every by-tie number: ρ (also exactly, as a rational string), ρ_adj, a, b, d, x̄, the level a + b·x̄, cell and parent counts, the non-degeneracy numerators and denominators, the PART aggregates, the per-partition ratios, the raw ratios, the spread and the null denominators.
2. **Descriptive numbers** agree to 1e-9 or better: G for every layout key, popularity cost, BC_K, the L-NCOAX rows and the flag, flat partition layouts, utilization, calibration transfer at the criterion settings, pages and misses at the criterion settings (ascending), the robustness grid (all 30 R × C cells per tree kind, for HB, HU, HB_A8, HB_greedy and HB_order_shuffled), quality means and paired NLL counts, and split-half stability.
3. **E at both criterion settings from raw traces and my own layouts, for three checkpoints per stream outside the registered 18.** Choice: `random.Random(20261113).choice` over the non-registered checkpoints of each architecture in registered order, giving `b102-o301-flat-s501`, `b101-o302-fixed_tree-s501`, `b101-o303-learned_tree-s502`. On both streams all 380 simulations agree count for count (actual and three nulls; L-FREQ, L-COAX, L-PCOAX-1…5, L-BCOAX; L-NCOAX on actual; both tie rules; both settings). The E, S and G values of these checkpoints are therefore reproduced from traces. Together with the earlier registered 18, 21 of 81 checkpoints per stream are now re-simulated independently.
4. **Integrity from the records** (`recompute_p7b.json` → `integrity`, `resources`):
   - 81/81 completed on each stream, 27 per architecture.
   - Stream A reproduces P7-A: 33,210 configurations (all four counts of every P7-A actual, null and order-shuffled configuration, ascending), 0 differences.
   - Stream-A null hashes equal P7-A's `stream_sha256` with seeds (91301+k)·1000 + cell. Stream-B null hashes equal the stream-B manifest with seeds 91321…91323.
   - Every trace file's SHA-256 matches its record (stream A also matches the identity manifest). Effective slots and unique slots, which I recomputed from the trace files, equal the records exactly (difference 0.0).
   - Stream-B selected, branches and counts hashes match the manifest, and `loss_computed_on_stream_b` is false for all 81.
   - R = 1 invariants hold (pages per query, histogram, first-touch, and C = 8 capacity misses identical across layouts) in every stream of every record. First-touch does not depend on C or the tie rule, and equals the number of distinct pages in the stream. Capacity misses never increase with C. Misses never exceed touches. No query touches more pages than the smallest C.
   - One spec hash (`3e418cb4…384b`, equal to the ADR file now) and one P7-B source-hash set across all 162 simulation workers and all six stage manifests. Every frozen check at the end of each stage passed.
   - Layout hash table `5cc0e11d…cdab` and each layout file hash agree across the layout stage, the hash table and both simulation stages. The stream-B manifest file hashes to `fbc76639…e6ee`, as recorded by trace-b and by all 162 simulation workers.
   - The five partition seeds reproduce the registered hashes.
5. **Resources against ADR §11** (active seconds from each stage's `result.json`):

| Stage | Active s | Cap s | Peak RSS (stage / max worker) |
|---|---:|---:|---|
| layouts (incl. calibration transfer, split-half) | 710.1 | 2,700 | 479 MB / 294 MB |
| panel + trace-b | 0.39 + 180.2 = 180.6 | 600 | not recorded / 578 MB stage, 372 MB worker |
| simulate A | 1,216.7 | 5,400 | 527 MB / 309 MB |
| simulate B | 1,219.9 | 5,400 | 512 MB / 312 MB |
| analyze | 2.7 | 600 | not recorded |
| **study total** | **3,330.0** | **14,700** | max 578 MB ≤ 2 GiB |

Refinement never reached the 12-pass bound: across all layout records the maximum was 9 passes (L-NCOAX), and 0 layouts used 12.

## Discrepancies

**Between my recomputation and `analysis.json`: none.** The final run compares 6,103 values with 0 differences.

**My own mistakes, kept.** The first script version (`failed_attempts/`) reported 18 differences, all caused by my comparison code:

- 16 were the BC_K five-partition counterpart. I had compared my mean of per-checkpoint ratios with the implementation's ratio of means. The two readings differ by 1–7% (for example 1.696 against 1.675 at R2C32 for fixed trees, and 4.05 against 3.80 at R8C8). The ADR wording, "mean m_P ÷ m_tree(L-COAX)", admits both; `recompute_p7b.json` reports both.
- 2 were the robustness-grid R8C8 HB class for fixed trees. I had compared my ascending-only class with the grid entry, which at the criterion settings carries the class combined over both tie rules (TIE-RULE DEPENDENT).

The extra re-simulation's first attempt failed because of my zsh quoting.

**Defects or gaps in the records and the analysis (none changes a registered result):**

- D1 (reporting). `analysis.json` sets `ncoax_control_flagged: true` for both streams, which is correct under clarification 8. But the combined outcome, pairing and recommendation text do not carry the flag. ADR §7 requires "every co-access result is flagged". See C6.
- D2 (labelling). The robustness-grid note says sensitivity variants run ascending only "except at the criterion settings". The records contain no descending runs for L-COAX8, L-BCOAX8, L-COAXg or L-BCOAXg at any setting; descending exists only for the nine criterion layouts. This is consistent with §11, since the sensitivity layouts enter no criterion. The note is wrong, and the W = 8 and greedy-only classes are single-tie-rule classes.
- D3 (reporting). `quality_vs_misses` gives per-architecture means only. §6 asks for "each checkpoint's unchanged P5 NLL beside m and E", which is recoverable from `E_decomposition_per_checkpoint` but not printed beside it. The paired E difference and the within-architecture correlation are not computed; I computed them (item 6).
- D4 (accounting). No peak RSS is recorded for the panel and analyze stages. Neither stage loads a model, so a breach is implausible, but "sampled throughout" is not evidenced there.
- D5 (evidence). The hard check that the cache never holds more than C pages is not written to any study record. From the records I can verify only its preconditions: no query touches more than 8 pages, and the counts are consistent. The check itself is verified only by my simulator, which enforces it, on 21 checkpoints per stream.

## Findings by item (stream A | stream B)

### 1–2. Non-degeneracy at the criterion settings (HB; HU uses the same denominators)

All 16 HB rows and all 16 HU rows are NON-DEGENERATE under both tie rules. Thresholds: flat denominator ≥ 0.05, tree denominator ≥ 0.01, every checkpoint ≥ 0.005, numerators ≥ 0.01.

| Setting, tie | flat den | fixed den | learned den | min den (fixed / learned comparison) | flat num L-COAX | fixed num L-BCOAX | learned num L-BCOAX |
|---|---|---|---|---|---|---|---|
| R2C32 asc | 3.339 \| 3.339 | 2.292 \| 2.292 | 1.785 \| 1.785 | 0.503/0.597 \| 0.499/0.594 | 2.372 \| 2.380 | 1.618 \| 1.625 | 1.287 \| 1.289 |
| R2C32 desc | 3.218 \| 3.218 | 2.202 \| 2.202 | 1.717 \| 1.717 | 0.495/0.577 \| 0.493/0.575 | 2.322 \| 2.331 | 1.584 \| 1.590 | 1.257 \| 1.259 |
| R8C8 asc | 3.092 \| 3.094 | 2.149 \| 2.148 | 1.678 \| 1.681 | 0.499/0.594 \| 0.497/0.595 | 1.572 \| 1.573 | 1.165 \| 1.166 | 0.988 \| 0.990 |
| R8C8 desc | 2.752 \| 2.753 | 1.872 \| 1.871 | 1.464 \| 1.466 | 0.469/0.520 \| 0.468/0.519 | 1.504 \| 1.504 | 1.121 \| 1.122 | 0.947 \| 0.949 |

Stream-A denominators reproduce the ADR §5 figures (3.34, 2.29, 1.78; 3.09, 2.15, 1.68; smallest 0.50). Per-checkpoint E, m and denominators for all 81 checkpoints, both streams, both settings and both ties, for every layout, are in `recompute_p7b.json` → `per_checkpoint_E_criterion_settings`. Effective slots (mean): flat 132.3 \| 132.6, fixed 96.2 \| 96.3, learned 83.0 \| 83.1.

### 3. HB_K and HU_K

"tl" is the number of cells in which the tree is strictly lower, then parents with the tree strictly lower (27 cells, 9 parents; no ties occurred). "Sep." is the descriptive separate-slope ratio at the flat-mean and tree-mean x, with z the slope-difference statistic.

| Comp | K | Setting | tie | ρ (A \| B) | ρ_adj (A \| B) | a, b, d (A) | x̄ (A \| B) | tl cells/parents (A \| B) | class per tie | **class** |
|---|---|---|---|---|---|---|---|---|---|---|
| HB | fixed | R2C32 | asc | 0.9942 \| 0.9950 | 0.9847 \| 0.9890 | 0.816, −0.0215, −0.0110 | 4.699 \| 4.700 | 15/5 \| 14/5 | W \| W | **WITHIN 10%** both |
| HB | fixed | R2C32 | desc | 0.9959 \| 0.9963 | 0.9908 \| 0.9951 | 0.780, −0.0117, −0.0067 | | 16/5 \| 15/4 | W \| W | |
| HB | fixed | R8C8 | asc | 1.0826 \| 1.0849 | 0.9619 \| 0.9657 | 1.493, −0.2010, −0.0209 | | 5/1 \| 5/1 | W \| W | **TIE-RULE DEPENDENT** both |
| HB | fixed | R8C8 | desc | **1.1024 \| 1.1036** | 0.9899 \| 0.9925 | 1.525, −0.1993, −0.0059 | | 5/1 \| 5/1 | I \| I | |
| HB | learned | R2C32 | asc | 1.0273 \| 1.0259 | 0.9887 \| 0.9906 | 1.002, −0.0597, −0.0082 | 4.626 \| 4.627 | 10/4 \| 11/5 | W \| W | **WITHIN 10%** both |
| HB | learned | R2C32 | desc | 1.0244 \| 1.0229 | 0.9924 \| 0.9954 | 0.967, −0.0503, −0.0056 | | 10/4 \| 11/5 | W \| W | |
| HB | learned | R8C8 | asc | 1.1988 \| 1.2009 | 0.9945 \| 0.9961 | 1.629, −0.2289, −0.0032 | | 1/0 \| 2/0 | I \| I | **INTERMEDIATE** both |
| HB | learned | R8C8 | desc | 1.2137 \| 1.2171 | 1.0103 \| 1.0119 | 1.742, −0.2440, +0.0063 | | 0/0 \| 2/0 | I \| I | |
| HU | fixed | R2C32 | asc/desc | 0.963/0.960 \| 0.964/0.961 | 0.951/0.953 \| 0.955/0.956 | | | 24/9, 25/9 \| 23/9, 25/9 | W | **WITHIN 10%** both |
| HU | fixed | R8C8 | asc/desc | 0.993/0.997 \| 0.994/0.997 | 0.906/0.918 \| 0.910/0.921 | | | 16/4, 16/4 \| 16/4, 13/4 | W | **WITHIN 10%** both |
| HU | learned | R2C32 | asc/desc | 1.004/0.996 \| 1.003/0.995 | 0.979/0.978 \| 0.981/0.980 | | | 12/4, 15/6 \| 14/5, 14/6 | W | **WITHIN 10%** both |
| HU | learned | R8C8 | asc/desc | 1.119/1.117 \| 1.119/1.118 | 0.923/0.925 \| 0.925/0.926 | | | 4/0, 4/0 \| 4/0, 4/0 | I | **INTERMEDIATE** both |

Counts favour flat (≥ 22/27 and ≥ 8/9) in HB R8C8 for both kinds under both ties on both streams: fixed 22/8, learned 25–27/9. Counts favour the tree in HU R2C32 for fixed trees (23–25/27, 9/9). Separate-slope check, HB R8C8 asc: z = −2.88 \| −3.11 (fixed) and −2.86 \| −2.87 (learned), so the common slope is rejected as on calibration. The separate-slope ratio ranges 0.92–1.00 (fixed) and 0.89–1.07 (learned) depending on the evaluation point. At R2C32, |z| ≤ 2.05. Using the record's `entropy_nats` instead of ln(effective slots) changes ρ_adj by less than 1e-15.

### 4. PART_K (exploited structure S)

| K | Setting | tie | mean S_B (A \| B) | mean S_P | aggregate S_B/S_P (A \| B) | per-partition min–max (A \| B) | cells / parents | raw m_B/m_P (A \| B) | spread (A) | lower than all five | per-tie | **class** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixed | R2C32 | asc | 0.673 \| 0.675 | 0.875 \| 0.878 | **0.769 \| 0.770** | 0.765–0.772 \| 0.765–0.774 | 27/9 \| 27/9 | 0.617 \| 0.618 | 0.047 | 27 \| 27 | better | **REAL BRANCHES BETTER** both |
| fixed | R2C32 | desc | 0.674 \| 0.677 | 0.879 \| 0.881 | 0.768 \| 0.768 | 0.764–0.771 \| 0.764–0.773 | 27/9 | 0.609 \| 0.610 | 0.046 | 27 | better | |
| fixed | R8C8 | asc | 0.438 \| 0.438 | 0.942 \| 0.942 | 0.465 \| 0.466 | 0.461–0.468 \| 0.462–0.468 | 27/9 | 0.284 \| 0.284 | 0.075 | 27 | better | **REAL BRANCHES BETTER** both |
| fixed | R8C8 | desc | 0.460 \| 0.459 | 0.942 \| 0.941 | 0.488 \| 0.488 | 0.483–0.492 \| 0.484–0.492 | 27/9 | 0.284 \| 0.285 | 0.075 | 27 | better | |
| learned | R2C32 | asc | 0.687 \| 0.688 | 0.874 \| 0.877 | **0.786 \| 0.785** | 0.782–**0.790** \| 0.781–0.788 | 27/9 | 0.590 \| 0.589 | 0.048 | 27 | better | **REAL BRANCHES BETTER** both |
| learned | R2C32 | desc | 0.685 \| 0.686 | 0.876 \| 0.880 | 0.782 \| 0.780 | 0.779–0.785 \| 0.777–0.783 | 27/9 | 0.582 \| 0.581 | 0.046 | 27 | better | |
| learned | R8C8 | asc | 0.483 \| 0.484 | 0.957 \| 0.957 | 0.505 \| 0.506 | 0.501–0.509 \| 0.502–0.510 | 27/9 | 0.258 \| 0.259 | 0.066 | 27 | better | **REAL BRANCHES BETTER** both |
| learned | R8C8 | desc | 0.500 \| 0.502 | 0.958 \| 0.959 | 0.522 \| 0.524 | 0.518–0.526 \| 0.520–0.528 | 27/9 | 0.260 \| 0.260 | 0.068 | 27 | better | |

PART null denominators are never degenerate (smallest single-checkpoint denominator 0.534).

### 5. Outcomes, pairing, decision, recommendation

| K | Stream A outcome | Stream B outcome | Pairing | Decision class |
|---|---|---|---|---|
| fixed | WITHIN 10% OF FLAT CO-ACCESS (confirmation: TIE-RULE DEPENDENT) | the same (confirmation: TIE-RULE DEPENDENT) | WITHIN 10% OF FLAT CO-ACCESS, **REPLICATED** | **N** |
| learned | WITHIN 10% OF FLAT CO-ACCESS (confirmation: INTERMEDIATE) | the same (confirmation: INTERMEDIATE) | WITHIN 10% OF FLAT CO-ACCESS, **REPLICATED** | **N** |

The recommendation is **row 2, "Both tree kinds in N"**: do not scale the existing hierarchy on storage-locality grounds. The options are to redesign it or stop the line; the decision belongs to the human lead. The outcome rule takes WITHIN 10% from the primary HB class alone; PART and the confirmation class do not enter that row.

### 6. Descriptive results

**Co-access gain G = m(actual, L)/m(actual, L-FREQ), mean of per-checkpoint ratios, ascending (ratio of means in `recompute_p7b.json`; descending differs by ≤ 0.07).**

| Setting | Kind | L-COAX | L-BCOAX | L-BFREQ | L-PCOAX 1–5 | L-NCOAX | L-COAX8 / L-BCOAX8 | L-COAXg / L-BCOAXg |
|---|---|---|---|---|---|---|---|---|
| R2C32 | flat | 0.755 \| 0.756 | — | — | 1.149–1.163 \| 1.152–1.166 | 1.007 \| 1.005 | 0.744 \| 0.746 | 0.768 \| 0.769 |
| R2C32 | fixed | 0.752 \| 0.752 | 0.776 \| 0.777 | 0.849 \| 0.851 | 1.252–1.295 \| 1.251–1.294 | 1.019 \| 1.019 | 0.737/0.758 \| 0.737/0.759 | 0.766/0.787 \| 0.767/0.788 |
| R2C32 | learned | 0.782 \| 0.781 | 0.800 \| 0.798 | 0.867 \| 0.865 | 1.358–1.438 \| 1.359–1.437 | 1.018 \| 1.016 | 0.758/0.778 \| 0.758/0.776 | 0.795/0.804 \| 0.793/0.803 |
| R8C8 | flat | 0.587 \| 0.588 | — | — | 1.769–1.782 \| 1.775–1.787 | 1.017 \| 1.016 | 0.576 \| 0.576 | 0.607 \| 0.607 |
| R8C8 | fixed | 0.607 \| 0.606 | 0.663 \| 0.663 | 0.671 \| 0.671 | 2.47–2.55 \| 2.46–2.54 | **1.060 \| 1.060** | 0.579/0.640 \| 0.578/0.641 | 0.628/0.675 \| 0.626/0.674 |
| R8C8 | learned | 0.660 \| 0.661 | 0.708 \| 0.710 | 0.717 \| 0.719 | 2.99–3.03 \| 2.99–3.03 | **1.036 \| 1.037** | 0.605/0.683 \| 0.606/0.684 | 0.680/0.718 \| 0.681/0.720 |

**BC_K = m(L-BCOAX)/m(L-COAX), ratio of means (mean of ratios), asc/desc.** Fixed R2C32: 1.033/1.038 \| 1.034/1.038. Learned R2C32: 1.017/1.022 \| 1.017/1.022. Fixed R8C8: 1.078/1.094 \| 1.079/1.095 (mean of ratios 1.089/1.106). Learned R8C8: 1.074/1.089 \| 1.075/1.090. The partition counterpart mean m_P/mean m(L-COAX) is 1.67–1.76 at R2C32 and 3.80–4.20 at R8C8. On flat traces, partitions against flat L-COAX give 1.49–1.52 raw and 1.28–1.29 in exploited structure at R2C32, and 2.92–2.95 raw and 1.98–1.99 exploited at R8C8 (asc, both streams).

**Popularity cost, mean of nulls under L / under L-FREQ, asc (mean of ratios).**

| Setting | Kind | L-COAX | L-BCOAX | L-PCOAX 1–5 |
|---|---|---|---|---|
| R2C32 | flat | 1.027 \| 1.026 | — | 1.216–1.228 |
| R2C32 | fixed | 1.038 \| 1.037 | 1.052 \| 1.051 | 1.303–1.347 |
| R2C32 | learned | 1.053 \| 1.052 | 1.064 \| 1.063 | 1.423–1.498 |
| R8C8 | flat | 1.097 \| 1.097 | — | 1.656–1.681 |
| R8C8 | fixed | 1.145 \| 1.146 | 1.275 \| 1.277 | 2.21–2.26 |
| R8C8 | learned | 1.200 \| 1.197 | 1.279 \| 1.275 | 2.71–2.77 |

**Decomposition, means, asc (stream A \| B): null under L-FREQ → null under L → actual under L; E; S.**

| Setting | Kind, layout | null-FREQ | null-L | actual-L | E | S |
|---|---|---|---|---|---|---|
| R2C32 | flat L-COAX | 3.339 \| 3.339 | 3.418 \| 3.418 | 2.372 \| 2.380 | 0.712 \| 0.714 | 0.693 \| 0.695 |
| R2C32 | fixed L-COAX | 2.292 \| 2.292 | 2.371 \| 2.369 | 1.566 \| 1.572 | 0.685 \| 0.688 | 0.661 \| 0.663 |
| R2C32 | fixed L-BCOAX | 2.292 \| 2.292 | 2.403 \| 2.402 | 1.618 \| 1.625 | 0.708 \| 0.710 | 0.673 \| 0.675 |
| R2C32 | learned L-COAX | 1.785 \| 1.785 | 1.867 \| 1.867 | 1.266 \| 1.268 | 0.715 \| 0.716 | 0.678 \| 0.680 |
| R2C32 | learned L-BCOAX | 1.785 \| 1.785 | 1.875 \| 1.875 | 1.287 \| 1.289 | 0.731 \| 0.732 | 0.687 \| 0.688 |
| R8C8 | flat L-COAX | 3.092 \| 3.094 | 3.367 \| 3.367 | 1.572 \| 1.573 | 0.517 \| 0.516 | 0.470 \| 0.470 |
| R8C8 | fixed L-COAX | 2.149 \| 2.148 | 2.432 \| 2.434 | 1.080 \| 1.081 | 0.513 \| 0.513 | 0.448 \| 0.447 |
| R8C8 | fixed L-BCOAX | 2.149 \| 2.148 | 2.673 \| 2.675 | 1.165 \| 1.166 | 0.559 \| 0.560 | 0.438 \| 0.438 |
| R8C8 | learned L-COAX | 1.678 \| 1.681 | 1.957 \| 1.958 | 0.920 \| 0.921 | 0.578 \| 0.578 | 0.479 \| 0.479 |
| R8C8 | learned L-BCOAX | 1.678 \| 1.681 | 2.079 \| 2.078 | 0.988 \| 0.990 | 0.619 \| 0.620 | 0.483 \| 0.484 |

**L-NCOAX control band (0.97–1.03, mean of per-checkpoint G).** The values lie within the band for flat in both settings (1.005–1.017) and for both trees at R2C32 (1.016–1.020). They lie outside the band for fixed trees at R8C8 (1.057–1.060) and learned trees at R8C8 (1.035–1.037), on both streams and under both ties. Every co-access result is therefore flagged (C6).

**Sensitivity (ascending only; no descending runs exist).** HB at R2C32 is WITHIN 10% under W = 8 (fixed ρ 0.985 \| 0.986, ρ_adj 0.985 \| 0.990; learned 1.012 \| 1.011, ρ_adj 1.001 \| 1.003) and under greedy-only (fixed 0.991 \| 0.993; learned 1.015 \| 1.015). At R8C8 fixed trees are WITHIN 10% under both variants (ρ 1.067 \| 1.070 W = 8; 1.066 \| 1.068 greedy) and learned trees INTERMEDIATE (ρ 1.178 \| 1.179; 1.177 \| 1.178; ρ_adj 0.97–1.00). The order-shuffled numerator gives R2C32 fixed 1.018 \| 1.023 and learned 1.066 \| 1.071 (flat lower in 25–26/27 cells and 9/9 parents), and R8C8 fixed 1.076 \| 1.082 and learned 1.211 \| 1.212.

**Robustness grid, HB ascending (class, ρ/ρ_adj; D = DEGENERATE). The same on both streams to ±0.02.**

| R \ C | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|
| 1 (fixed \| learned) | W 1.00/1.00 \| W 1.00/1.00 | W 0.99/1.00 \| W 0.99/0.99 | W 0.98/0.99 \| W 0.98/0.99 | W 0.99/1.00 \| W 0.98/1.01 | W 1.00/1.01 \| W 1.02/1.02 |
| 2 | W 0.99/0.98 \| W 1.01/0.98 | W 0.98/0.98 \| W 1.00/0.97 | W 0.99/0.98 \| W 1.03/0.99 | W 1.07/1.00 \| I 1.16/1.04 | D \| D |
| 8 | W 1.08/0.96 \| I 1.20/0.99 | I 1.17/0.93 \| I 1.50/1.03 | D \| D | D \| D | D \| D |
| 32, 128, 512 | D | D | D | D | D |

R = 1 cells are near 1 by construction (layouts cannot share pages there). No cell is TREE or FLAT MATERIALLY BETTER. Both trees are DEGENERATE at every real row size (R ≥ 32).

**Raw misses, first touch, amplification and per-context quantiles** (criterion settings, both ties, every criterion layout) are in `recompute_p7b.json` → `descriptive.*.pages_and_misses`. Raw m, asc, R2C32 for L-COAX / L-BCOAX: flat 2.372 \| 2.380; fixed 1.566/1.618 \| 1.572/1.625; learned 1.265/1.286 \| 1.268/1.289. R8C8: flat 1.572 \| 1.573; fixed 1.080/1.165 \| 1.081/1.166; learned 0.920/0.988 \| 0.921/0.990. Raw tree-to-flat ratios are 0.53–0.74, against effective-slot ratios of 0.73 (fixed) and 0.63 (learned). First-touch misses are 0.002–0.008 per query over the whole stream, under 0.2% of counted misses.

**Calibration → evaluation transfer** (asc; mean m on evaluation over calibration): stream A 0.997–1.009, stream B 0.997–1.011, for every criterion layout and kind. Layouts lose about 1% on the fresh stream.

**Split-half stability** (calibration only; mean |fit₀→score₁ − fit₁→score₀| / pair mean): 1.4–4.8% per checkpoint on average, at most 16.3% (learned L-COAX R8C8). Flat L-COAX: 1.4% / 2.1%. Fixed L-BCOAX: 1.8% / 1.7%. Learned L-BCOAX: 1.8% / 2.9%.

**Quality against misses** (P5 final NLL; the same values for both streams because no NLL exists on stream B). Tree minus flat NLL is +0.0008 (fixed) and +0.0014 (learned) nats/byte, within 0.005 in 26/27 cells each (maximum 0.0057 and 0.0052). The paired HB E difference (tree L-BCOAX − flat L-COAX), asc, is −0.004 \| −0.004 (fixed R2C32), +0.019 \| +0.018 (learned R2C32), +0.043 \| +0.044 (fixed R8C8) and +0.103 \| +0.104 (learned R8C8). The Pearson correlation of ΔNLL with ΔE across the 27 pairs is 0.13 \| 0.14, −0.05 \| −0.05, 0.32 \| 0.32 and −0.08 \| −0.11. The within-architecture correlation of E with NLL (n = 27) lies between −0.45 and +0.21 across kinds, layouts and settings (largest |r|: learned L-FREQ R8C8, −0.43 \| −0.45). None of these is registered, and no quality effect is implied.

## Critical reading

**C1. What the records establish.** Under this page model, at the two hypothetical row sizes and one 768 KiB memory, refined co-access clustering of flat memory's slots gives incremental locality within 10% of what branch-constrained clustering gives either tree, in the primary setting, under both tie rules, on both evaluation streams. The decision class is N for both kinds, and recommendation row 2 follows mechanically. The records do not establish that hierarchy and flat are *equivalent*: WITHIN 10% is a size band. Nor do they establish anything about real row sizes, where every co-access comparison is degenerate. They say nothing about latency, I/O, SSD viability, larger memories, training or quality. They do not show flat is better in the primary setting: there ρ_adj < 1 for both kinds on both streams, and the cell counts are mixed.

**C2. Stream A against stream B.** The streams agree far more closely than the architectures do. Across the 16 HB/HU ρ values per stream, |ρ_A − ρ_B| is at most 0.0034 (mean 0.0012); |ρ_fixed − ρ_learned| is 0.027–0.126 (mean 0.076). Per-checkpoint E differs by 0.9–1.0% on average between streams (at most 4.0%), with between-stream correlations of 0.97–0.996. No ρ, ρ_adj, slope b or tree coefficient d changes sign between streams. The per-cell tree-versus-flat direction is the same on both streams in 26–27 of 27 pairs. The only changes are two HU rows whose cell majority sits at the 13/14 split (fixed R8C8 desc 16→13; learned R2C32 asc 12→14). This is strong replication, but of the same corpus and the same articles (§7a), with layouts fitted on a third stream of that corpus. It shows the result is not an artefact of the particular 512 contexts. It does not show it would hold on independent text. The cell-level stability also means the mixed primary-setting counts reflect real heterogeneity between checkpoint pairs, not stream noise.

**C3. Distance to class boundaries, and what would change the class.**
- *Primary HB*: ρ 0.994–1.027 and ρ_adj 0.985–0.995, at least 0.07 from 0.90/1.10 and about 0.18 from 0.80. No alternative changes the class: not the other tie rule, not W = 8 (0.985–1.012), not greedy-only (0.991–1.015), not raw against adjusted. The primary class, and with it every outcome, decision and the recommendation, is robust to everything examined.
- *Confirmation HB, fixed*: the class depends on 0.0024 (A) and 0.0036 (B). Descending ρ is 1.1024 \| 1.1036, just above 1.10; ascending ρ is 1.0826 \| 1.0849; ρ_adj is 0.96–0.99. With the adjusted ratio alone it would be WITHIN 10% under both ties. W = 8 and greedy-only give ρ 1.066–1.070 under ascending only, so whether either would remove the tie-rule dependence is unknown.
- *Confirmation HB, learned*: INTERMEDIATE because raw ρ is 1.199–1.217, against ρ_adj 0.995–1.012 inside the band. It is 0.03–0.05 short of the 1.25 raw threshold, and FLAT MATERIALLY BETTER is impossible anyway because ρ_adj is about 1.
- *PART, learned primary*: the aggregate is 0.780–0.786, and the worst single partition is 0.790 (A asc), 0.010 under 0.80. Fixed primary is 0.764–0.774. The confirmation values (0.47–0.52) are far from the boundary. A change in PART would not alter any outcome here, because PART matters only after TREE MATERIALLY BETTER.
- *Raw against adjusted ratio*: in the confirmation setting they disagree on direction (raw 1.08–1.22, flat-favouring; adjusted 0.96–1.01). The slope is strongly negative (b about −0.20 to −0.24) and the common-slope assumption is rejected (z about −2.9). The separate-slope ratio moves between 0.89 and 1.07 depending on where it is evaluated. The confirmation-setting tree-versus-flat comparison is therefore not identified apart from utilization by this design. PENDING LEAD REVIEW.

**C4. Is WITHIN 10% hiding a consistent direction?** In the registered primary HB comparison, no: fixed trees are lower in 14–16/27 cells and 4–5/9 parents, learned trees in 10–11/27 and 4–5/9. Elsewhere it does:
- The confirmation-setting HB is consistently flat-favouring in raw E. Fixed: flat lower in 22/27 cells and 8/9 parents under both ties on both streams, which meets "counts favour flat" while the class is WITHIN 10% (asc) or TIE-RULE DEPENDENT. Learned: 25–27/27 and 9/9.
- HU fixed in the primary setting is small and consistently tree-favouring: ρ 0.960–0.964, tree lower in 23–25/27 cells and 9/9 parents, again meeting "counts favour the tree". Fixed-tree traces carry about 4% more co-access structure exploitable by unconstrained clustering than flat traces. Imposing the branch constraint (BC 1.03) removes that edge, so HB lands at 0.99.
- The ADR requires these to be described as "small and consistent", not as no difference.

**C5. Comparison with the calibration analogues computed before the run.** The result came out as anticipated, almost to the second decimal.

| Quantity | Calibration analogue (REREVIEW §1.1–1.2) | Evaluation, A \| B |
|---|---|---|
| HB R2C32 asc ρ, fixed / learned | 0.999 / 1.032 | 0.994 / 1.027 \| 0.995 / 1.026 |
| HB R2C32 asc ρ_adj | 0.988 / 0.992 | 0.985 / 0.989 \| 0.989 / 0.991 |
| HB R8C8 ρ, fixed asc / desc / learned asc | 1.088 / 1.108 (TIE-RULE DEPENDENT) / 1.208 | 1.083 / 1.102 / 1.199 \| 1.085 / 1.104 / 1.201 |
| HB R8C8 ρ_adj, the same three | 0.964 / 0.994 / 0.999 | 0.962 / 0.990 / 0.995 \| 0.966 / 0.993 / 0.996 |
| PART exploited structure R2C32 / R8C8 (fixed, learned) | 0.768, 0.785 / 0.463, 0.504 | 0.769, 0.786 / 0.465, 0.505 \| 0.770, 0.785 / 0.466, 0.506 |
| BC R2C32 / R8C8 (fixed, learned) | 1.034, 1.018 / 1.079, 1.080 | 1.033, 1.017 / 1.078, 1.074 \| 1.034, 1.017 / 1.079, 1.075 |
| Flat G(L-COAX) R2C32 / R8C8 | about 0.76 / 0.64 (revision-1 configuration) | 0.755 / 0.587 \| 0.756 / 0.588 |
| Analogue outcome | WITHIN 10% for both kinds, PART REAL BRANCHES BETTER | the same on both streams |

The registered run is therefore confirmation of a result already visible on calibration (ADR §0), now replicated on a fresh stream of the same corpus.

**C6. The L-NCOAX flag.** In the confirmation setting, L-COAX built from a popularity-only calibration null is 3.5–6% worse than plain frequency packing for trees, and 1.6% worse for flat. The algorithm is not manufacturing locality: that would show as G < 0.97. It is destroying some when its affinities are chance. The cost is larger on the more concentrated tree checkpoints, which suggests the clustering also pays a noise cost on real data. That would bias against trees in L-COAX terms (HU) by up to a few percent at R8C8, and probably less in L-BCOAX, whose search space is smaller. This does not plausibly overturn a 0.99 primary ratio. But the ADR's flag is mechanically raised on both streams, and the combined decision text in `analysis.json` does not carry it (D1). How to report it beside the N decision is PENDING LEAD REVIEW.

**C7. What PART shows, given that HB never reached TREE MATERIALLY BETTER.** PART is REAL BRANCHES BETTER on all eight setting × kind × stream combinations, with 27/27 cells and 9/9 parents. It should be read narrowly. Three facts from the records:
- In exploited structure, real branches are about as good as no partition at all. S(L-BCOAX) is 0.673 / 0.438 against S(L-COAX) 0.661 / 0.448 for fixed trees, and 0.687 / 0.483 against 0.678 / 0.479 for learned (R2C32 / R8C8).
- On flat traces, unconstrained clustering beats the same five random partitions by a very similar factor: S(L-COAX)/S(PCOAX) is about 0.78 and 0.50, against 0.77–0.79 and 0.47–0.52 for branches on tree traces.
- In raw misses, branches still cost 2–9% against unconstrained clustering (BC 1.02–1.09).

So PART shows that branches are not arbitrary groups: they are roughly as good a grouping as a data-driven clustering finds. It does not show structure that unconstrained clustering cannot recover. Competing explanation 5 (arbitrary partition) is rejected. Explanation 2 (generic co-access structure) explains the HB result. Explanation 4 (optimizer artefact) is not supported either, since BC > 1. Because HB is not TREE MATERIALLY BETTER, PART enters no outcome. Five partitions cannot support a statement about partitions in general, and the profile-matched null was not registered (§7 limit).

**C8. Does flat's co-access gain exceed the trees' branch-aware gain?** Yes, as calibration suggested, on both streams and in both settings. G_flat(L-COAX) is 0.755 / 0.587. G_tree(L-BCOAX) is 0.776 / 0.663 (fixed) and 0.800 / 0.708 (learned). G_tree(L-BFREQ) is 0.849 / 0.671 and 0.867 / 0.717. Flat gains about 25% and 41% from co-access placement; the trees gain 20–22% and 29–34% from branch-aware co-access placement, and 13–15% and 28–33% from branch-aware frequency packing. Flat starts from a worse frequency-packing E (0.944 / 0.881 against 0.91–0.92 / 0.85–0.88), which is why ρ ends near 1. In the confirmation setting, co-access placement inside branches adds almost nothing over frequency packing inside branches (0.663 against 0.671; 0.708 against 0.717).

**C9. Limits.** The limits are:
- Both criterion settings use hypothetical row sizes. At ArborLM's real 128-byte rows (R ≥ 32) every comparison is DEGENERATE, so the study says nothing at real row sizes.
- One memory size (4,096 slots, 768 KiB) and one cache size per setting.
- Both streams and the calibration stream come from one corpus.
- The optimizer is greedy fill plus bounded swap refinement on same-query affinity, and refinement never needed more than 9 passes. ADR §8 argues a stronger optimizer would probably help flat more, so WITHIN 10% would not reverse in the tree's favour. That argument rests on calibration evidence, not on this run.
- The 27 cells share data and backbones (9 parents), so counts are robustness descriptions, not tests.
- The utilization adjustment assumes a common slope that is rejected in the confirmation setting.
- The descending tie rule exists only for criterion layouts.
- Quality comparisons reuse stream-A-panel NLL for stream B.

**C10. Implications for the ADR §9 decision rule and for H3/H4/H5.** The rule worked as written and produced the same total-function result on both streams. The decision is fully determined by the primary-setting HB class, which sits about 0.07 inside the band. The confirmation setting, PART and the NCOAX control could not have changed the decision given that primary class. That is a property of the registered rule, not a defect, but it means the confirmation setting acted as description only. Whether the confirmation-setting flat-favouring raw direction and its utilization confound should be carried into the lead's statement is PENDING LEAD REVIEW. For the hypotheses: the records give no storage-locality case for the existing hierarchy. Any revival would need a hierarchy whose branches encode co-access structure that unconstrained clustering of a flat memory cannot recover, for example the locality-aware objective (H3) or persistent routing named in §9. How this bears on H3/H4/H5 as worded in the protocol is PENDING LEAD REVIEW; I make no claim about them beyond these records.

## Could not verify

- That the cache never held more than C pages in the study's own simulator (D5). This is evidenced only by my simulator, on 21/81 checkpoints per stream, and by preconditions in the records.
- Counts for the 60 of 81 checkpoints per stream outside the 21 re-simulated. Their internal consistency (invariants, P7-A reproduction on stream A, hashes) is verified; their individual miss counts are not reproduced from traces.
- The stream-B tracing itself (model replay, byte-identical regeneration). I checked only the recorded flags and hashes against the manifest; no model was run.
- Calibration-transfer and split-half miss counts from traces. They agree with `analysis.json` but were not re-simulated.
- Process-tree RSS for the panel and analyze stages (D4), and whether stage "active seconds" equals sequential worker time beyond the near-equality with summed worker wall time (layouts 709.7 against 710.1 s; simulate 1,216.2 against 1,216.7 and 1,219.5 against 1,219.9 s).
- Descending-tie classes for the W = 8 and greedy-only variants (not simulated).

## Open questions (PENDING LEAD REVIEW)

1. Whether, and how, the L-NCOAX flag (fixed and learned trees outside 0.97–1.03 at R8C8 on both streams) is attached to the N decision and recommendation text.
2. How to state the confirmation-setting result: raw E consistently flat-favouring (fixed 22/27 and 8/9, learned 25–27/27 and 9/9, ρ 1.08–1.22), adjusted ratio about 1, common slope rejected (z about −2.9). One option is "not separable from utilization in this design".
3. Whether the "small and consistent" tree-favouring HU result for fixed trees in the primary setting (ρ 0.96, 23–25/27, 9/9) should be reported beside the HB outcome as the ADR's WITHIN 10% wording requires.
4. Which reading of the BC_K partition counterpart (ratio of means, as implemented, or mean of ratios) the report should use; they differ by 1–7%.
5. How the result bears on H3/H4/H5 and on whether any further storage-locality study is worth specifying. That is a human-lead decision; nothing here is an authorization.
