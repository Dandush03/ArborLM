# P7-B specification review: mathematical and measurement assumptions of ADR-0014 (DRAFT)

- Reviewer: Claude Opus 5.5 (`claude-opus-5-5`), auditor role, separate context. Date 2026-11-13.
- Reviewed: `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` (untracked draft, sha256 `86e9d021…5ece`) on branch `claude/p7b-coaccess-layout-proposal`, HEAD `760a800`.
- Background read: ADR-0013 (§§5, 7, 14, 15), `docs/reviews/p7a-results-2026-11-13/README.md`, `docs/reviews/p7a-results-audit-2026-11-13/AUDIT.md`, `src/arborlm/p7a_core.py`, `src/arborlm/p7a_sim.py`, `docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.md`.
- **Status: independent engineering and mathematical evidence. Not Astra validation. Not human approval.** `Astra review: NOT_PERFORMED`. Scientific choices are marked **PENDING LEAD REVIEW**.

**Counts: 1 BLOCKER, 7 MAJOR, 11 MINOR, 6 NOTE.**

## 0. Material, environment, what was and was not read

| Item | Value |
|---|---|
| Python | `.venv/bin/python -I`, CPython 3.12.14, standard library only. No `arborlm` import. No implementer analysis code reused. |
| Hardware | Apple M5 Max, macOS 27.2.1 |
| Published records read | `results/p7a-2026-11-13/simulate/P7AS-…/workers/*.result.json` (81), `results/p7a-2026-11-13/trace/P7AT-…/checkpoints/*.json` (81, for file hashes), `results/p5-2026-11-13/<label>/result.json` (81, effective slots) |
| Trace files read | **Calibration only**: `experiments/P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e/traces/<label>/calib_selected.int16.bin` (81) and `calib_branches.int8.bin` (54 tree checkpoints; used only to confirm that every selected slot lies in a visited branch). 135 files, each sha256-checked against the trace record before use. |
| Evaluation traces | **None read.** No `eval_selected` or `eval_branches` file was opened. The scripts assert this, and `outputs/calib_coaccess.json` lists the 135 files read (`eval_files_read: []`). |
| Registered outcomes | None computed. No co-access layout was evaluated on the evaluation stream. No E, ρ, HB, HU, UTIL, BC or co-access gain on the evaluation stream was computed. Evaluation-side numbers below come from layouts P7-A already published (L-FREQ, L-BFREQ, L-ID, and the count-preserving null under L-FREQ). |

Commands, run from the repository root:

```sh
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/published_ratio.py        # published records only, < 2 s
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/calib_coaccess.py --jobs 14  # calibration only, 47 s wall
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/aggregate_calib.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/matched_pairs.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/check_lru_equivalence.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/test_reading.py
```

| Script (sha256) | Output |
|---|---|
| `scripts/published_ratio.py` (`6320d245…`) | `outputs/published_ratio.json`, `.log` |
| `scripts/calib_coaccess.py` (`a3bcb8a1…`) | `outputs/calib_coaccess.json` (`9f69f063…`), `.log` |
| `scripts/aggregate_calib.py` (`4db1e347…`) | `outputs/aggregate_calib.json` (`9d4cd866…`), `.log` |
| `scripts/matched_pairs.py`, `check_lru_equivalence.py`, `test_reading.py` | `outputs/*.log` |

**Attempts.** None failed. `outputs/calib_coaccess_pilot3_v1.json` is a pilot on three checkpoints, made with an earlier version of `calib_coaccess.py`. That version lacked the random-partition, branch-ID-order, page-reversal-for-FREQ/BCOAX and descending-order variants and the affinity TV distance. The earlier script text was edited in place and is not kept separately. The pilot numbers equal the final run's for the same checkpoints and quantities.

**Simulator check.** My calibration LRU (per-query service, ascending page number among the oldest query's pages, warm-up on the first half, warm capacity misses) equals, on 108 configurations, the LRU of my P7-A results audit. That LRU matched the P7-A records exactly on all 81 checkpoints (`outputs/check_lru_equivalence.log`).

**How I read §4.** These readings are pinned by `test_reading.py`:

- N[i][j] counts pairs (t, u) with 0 ≤ t − u ≤ W in one context, i selected at t, j at u, i ≠ j; then A = N + Nᵀ.
- Greedy page fill follows steps 1–3 exactly. Ties go to the higher score, then the higher f, then the lowest ID. The seed is the highest f, ties to the lowest ID.
- L-BCOAX orders branches by descending total count and runs the greedy inside each branch. Branch b holds slots 256b to 256b+255.

**Calibration-stream quantities.** All are on the calibration stream:

- **In-sample:** fit and evaluate on all 512 contexts, warm-up on 256 and counting on 256, as the registered protocol does.
- **Split-half:** fit on contexts 0–255 and evaluate on 256–511 (warm-up 128, count 128), and the reverse.
- **Reviewer null:** a count-preserving null of the calibration stream, generated with the ADR-0013 item 8 algorithm under my own seed (77001·1000 + cell index). It is not the registered null.

"Primary" means R=2, C=32 and "confirmation" means R=8, C=8. m means warm capacity misses per query. Values are means over 27 checkpoints per architecture, with [min, max] where given.

---

## 1. Key numbers

### 1.1 Residual utilization trend of the published P7-A ratio (evaluation stream, L-FREQ, published records)

E_FREQ(c) = m_c(actual, L-FREQ) / mean over 3 replicates of m_c(count-preserving null, L-FREQ). This is the E of ADR-0014 with L = L-FREQ, and the "actual/FM" ratio already published by P7-A.

| | R2C32 flat | fixed | learned | R8C8 flat | fixed | learned |
|---|---:|---:|---:|---:|---:|---:|
| mean E_FREQ | 0.944 | 0.912 | 0.915 | 0.881 | 0.848 | 0.877 |
| SD across 27 | 0.025 | 0.028 | 0.039 | 0.031 | 0.042 | 0.052 |
| slope of E on ln(effective slots), within architecture (SE) | +0.064 (0.017) | +0.050 (0.020) | +0.101 (0.028) | +0.013 (0.026) | +0.065 (0.031) | +0.036 (0.046) |

- **Pooled over 81 checkpoints:**
  - R2C32: slope **+0.070 (SE 0.010)** per ln(effective slots), R² 0.385.
  - R8C8: slope +0.033 (SE 0.016), R² 0.05.
- **ρ under L-FREQ for both sides** (not a registered comparison):

  | Setting | Tree kind | ρ_FREQ | Tree lower: pairs | Tree lower: parents |
  |---|---|---:|---:|---:|
  | R2C32 | fixed | 0.966 | 23/27 | 9/9 |
  | R2C32 | learned | 0.969 | 19/27 | 7/9 |
  | R8C8 | fixed | 0.962 | 20/27 | 9/9 |
  | R8C8 | learned | 0.995 | 16/27 | 7/9 |

- **How much of ρ_FREQ utilization alone predicts.** I fitted the pooled regression with no architecture term and evaluated it at each architecture's mean ln(effective slots):

  | Setting | Utilization-predicted ρ (fixed / learned) | Common-slope adjusted ρ at the pooled mean (fixed / learned) |
  |---|---|---|
  | R2C32 | **0.977 / 0.966** | **0.989 / 1.004** |
  | R8C8 | 0.988 / 0.983 | 0.976 / 1.015 |

  So at the primary setting, most of the trees' 3-point "extra structure" reported by P7-A (all of it for learned) is the utilization trend of E itself. **Dividing by a checkpoint's own null does not remove utilization.** A more concentrated checkpoint has a lower E for the same layout.
- **Alternative aggregates.** Ratio of mean E, ratio of pooled sums, and ratio of geometric means differ by at most 0.006 on these data. The aggregate is not the problem (NOTE N1).
- **Utilization overlap of pairs.** The tree/flat effective-slot ratio of a pair has median 0.729 (fixed) and 0.639 (learned). Only 12/27 (fixed) and 3/27 (learned) pairs lie within ±20%. Matched-pair analysis is therefore weak for learned trees. Across all 81 checkpoints the effective-slot ranges overlap: flat 85–199, fixed 43–142, learned 55–124.

### 1.2 Already known about the evaluation stream (published P7-A records)

E_tree(L-BFREQ) / E_flat(L-FREQ) uses P7-A layouts only and is not a registered P7-B quantity:

| Setting | Fixed tree | Learned tree |
|---|---|---|
| R2C32 | 0.820, 27/27 pairs, 9/9 parents | 0.839, 27/27, 9/9 |
| R8C8 | **0.643**, 27/27, 9/9 | **0.712**, 27/27, 9/9 |

### 1.3 Non-degeneracy (published null under L-FREQ)

| | flat mean / min | fixed mean / min | learned mean / min | 0.005 floor violated |
|---|---|---|---|---|
| R2C32 | 3.339 / 1.798 | 2.292 / 0.503 | 1.785 / 0.597 | 0 of 81 |
| R8C8 | 3.092 / 1.634 | 2.149 / 0.499 | 1.677 / 0.594 | 0 of 81 |

Both criterion settings are non-degenerate with a wide margin. The floors never bind. On calibration, co-access layouts do not drive the numerator near zero at the confirmation setting: m(L-COAX) for flat is 1.71 [1.05, 2.38], and m(L-BCOAX) is 1.16 [0.41, 1.72] for fixed and 0.98 [0.54, 1.67] for learned. **R8C8 stays informative after co-access packing.** Both settings cache 64 rows, so they differ only in page granularity.

### 1.4 Affinity sparsity (calibration, all 81)

| | flat | fixed | learned |
|---|---|---|---|
| A₈ nonzero, share of all 8.4 M slot pairs | 0.65% | 0.49% | 0.35% |
| A₈ nonzero, share of pairs among calibration-used slots | 58% | 56% | 57% |
| A₈ mean degree of a used slot | 248 | 212 | 181 |
| A₈ nonzero pairs with count 1 / ≤ 2 | 14.7% / 23.5% | 15.1% / 24.1% | 14.2% / 23.0% |
| A₈ mass in the top 10% of pairs | 79% | 86% | 86% |
| A₀ nonzero, share of used-slot pairs (mean degree) | 9.2% (39) | 9.0% (34) | 10.8% (34) |
| **Total-variation distance, A₈(actual) vs A₈(null), as a share of mass** | **0.099** | **0.091** | **0.085** |
| Total-variation distance, A₀(actual) vs A₀(null) | 0.768 | 0.710 | 0.690 |
| Same-branch share of A₀ / A₈ mass (null A₈) | — | 0.62 / 0.20 (0.15) | 0.69 / 0.24 (0.19) |

**About 90% of A₈'s mass is what popularity alone produces.** A₈ is not sparse among used slots. It is dense and dominated by chance co-occurrence of hot slots. A₀ is mostly structure, and for trees mostly within-branch structure (62–69% of mass, against about 15–19% by chance).

### 1.5 Calibration-stream behaviour of the layouts (in-sample)

| | R2C32 flat | fixed | learned | R8C8 flat | fixed | learned |
|---|---:|---:|---:|---:|---:|---:|
| G(L-COAX) = m(L-COAX)/m(L-FREQ) | 0.764 | 0.760 | 0.780 | 0.638 | 0.645 | 0.664 |
| G(L-COAX0) | 0.767 | 0.766 | 0.792 | **0.604** | **0.624** | 0.676 |
| G(L-BCOAX) | — | 0.777 | 0.793 | — | 0.657 | 0.703 |
| G(L-BFREQ) | — | 0.849 | 0.867 | — | 0.669 | 0.716 |
| **Null-fit control**: G(L-COAX fitted on the null's affinity) | 0.999 | 1.008 | 1.009 | 1.000 | 1.010 | 1.006 |
| Random-partition control: G(greedy inside 16 random groups of 256) | 0.973 | 1.006 | 1.026 | **1.479** | **2.032** | **2.453** |
| BC = m(L-BCOAX)/m(L-COAX) | — | 1.023 | 1.017 | — | 1.017 [0.897, 1.407] | 1.059 [0.883, 1.353] |
| m(null, L)/m(null, L-FREQ), L = L-COAX | 1.009 | 1.012 | 1.015 | 1.024 | 1.034 | 1.037 |
| m(null, L)/m(null, L-FREQ), L = L-BCOAX | — | 1.025 | 1.027 | — | **1.219 [1.05, 1.92]** | **1.195 [1.04, 1.47]** |

### 1.6 Greedy against a stronger flat baseline (split-half, cross-fitted)

The stronger baseline is the greedy layout followed by a deterministic first-improvement swap search that maximizes within-page A₈ mass:

- At most 12 passes; at most 9 were used.
- For L-BCOAX, swaps are restricted to the same branch, so branches stay contiguous.
- The search is fitted on one half and scored by LRU misses on the other half, averaged over both directions.

| m(refined)/m(greedy), out of sample | R2C32 flat | fixed | learned | R8C8 flat | fixed | learned |
|---|---:|---:|---:|---:|---:|---:|
| L-COAX (unconstrained) | 0.969 | 0.967 | 0.969 | **0.896** | **0.891** | **0.899** |
| L-BCOAX (branch-constrained) | — | 0.976 | 0.979 | — | 0.975 | 0.971 |
| Cross-fitted BC, greedy | — | 1.021 | 1.014 | — | 1.017 | 1.033 |
| Cross-fitted BC, refined | — | 1.031 | 1.024 | — | **1.113** | **1.115** |

The tree-to-flat gain ratio (G_BCOAX,tree / G_COAX,flat, cross-fitted) is calibration-only and not the registered test:

| Setting | Tree kind | Greedy | Refined |
|---|---|---:|---:|
| R2C32 | fixed | 1.011 | 1.018 |
| R2C32 | learned | 1.028 | 1.040 |
| R8C8 | fixed | 1.012 | 1.103 |
| R8C8 | learned | 1.084 | 1.176 |

**Greedy leaves about 3% (primary) and about 10% (confirmation) on the table for unconstrained clustering, but only 2–3% for branch-constrained clustering.** The gap is about the same for flat and for trees' own L-COAX. It differs between constrained and unconstrained clustering.

### 1.7 Split-half transfer (fit on one half, evaluate on the other, against in-sample on the same half)

| out-of-sample / in-sample m | R2C32 flat | fixed | learned | R8C8 flat | fixed | learned |
|---|---:|---:|---:|---:|---:|---:|
| L-FREQ | 1.000 | 1.000 | 0.999 | 1.001 | 1.002 | 1.002 |
| L-COAX | 1.005 | 1.006 | 1.005 | 1.008 | 1.010 | 1.014 |
| L-BCOAX | — | 1.004 | 1.004 | — | 1.004 | 1.004 |
| mean \|ln(out/in)\| for L-COAX ("layout lottery") | 0.010 | 0.011 | 0.012 | **0.033** | **0.037** | **0.048** |
| mean \|ln(out/in)\| for L-BCOAX | — | 0.009 | 0.011 | — | 0.011 | 0.013 |

- **Overfitting is negligible** at both settings, with half the calibration data. It does not differ by architecture at the primary setting.
- At the confirmation setting, unconstrained greedy layouts are **unstable**. Two fits on different halves give per-checkpoint differences of 3–5% on average and up to 12–18% (maximum |ln| 0.112–0.163; 0.184 for the refined learned-tree layout). Branch-constrained layouts give about 1%.

### 1.8 Page numbering and the eviction tie rule (calibration, in-sample)

Reversing the order of pages, which is the same as descending eviction order, changes m as follows (ratio reversed/registered):

| | R2C32 flat | fixed | learned | R8C8 flat | fixed | learned |
|---|---:|---:|---:|---:|---:|---:|
| L-FREQ | 0.972 | 0.965 | 0.960 | **0.923** | **0.897** | **0.884** |
| L-COAX | 0.975 | 0.970 | 0.968 | 0.938 | 0.925 | 0.921 |
| L-BCOAX | — | 0.976 | 0.973 | — | 0.958 | 0.949 |
| Reversing row order within pages | 1.000 exactly | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| L-BCOAX with branch-ID order / registered branch order | — | 0.995 | 0.997 | — | 0.988 | 0.988 |

### 1.9 Cache residence against the window

Median queries from a page's last use to its eviction, counted half:

| Setting | flat L-FREQ / L-COAX | fixed L-FREQ / L-COAX | learned L-FREQ / L-COAX |
|---|---|---|---|
| R2C32 | 6.2 / 8.2 | 8.2 / 10.9 | 9.0 / 11.9 |
| R8C8 | 1.7 / 2.8 | 2.1 / 3.3 | 2.1 / 3.4 |

At R8C8, at least 96% of evictions happen within 8 queries of last use.

---

## 2. Findings

### BLOCKER

**B1 — UTIL_K does not test the concentration correction, and the correction is measurably incomplete (§2, §7 UTIL_K, §8 first bullet, §9 first row).**

*What is wrong.* On a count-preserving null there is no co-access structure. E_null(L) = m(null, L)/m(null, L-FREQ) therefore measures only **how much worse L is than L-FREQ as a popularity layout**. It says nothing about whether dividing by the null removes utilization from E on the actual stream. Three consequences:

1. **UTIL_K cannot return ADVANTAGE.** L-FREQ is close to optimal for a structureless stream. On calibration, m(null, L)/m(null, L-FREQ) is about 0.99 for a layout fitted to the null, 1.01–1.04 for L-COAX, and 1.03 (R2C32) or 1.20–1.22 (R8C8) for L-BCOAX (§1.5). A tree ratio of 0.80 times flat's is out of reach. So the "UTILIZATION-CONFOUNDED" row is unreachable, and HIERARCHY-SPECIFIC ADVANTAGE reduces to "HB_K ADVANTAGE in both settings". Its qualifier "not explained by utilization" (§9) would rest on no test.
2. **The failure it should detect is present.** On the published P7-A records, E_FREQ rises with effective slots: pooled +0.070 (SE 0.010) per ln(effective slots) at R2C32. The trees' lower utilization alone predicts ρ_FREQ = 0.977 (fixed) and 0.966 (learned), against observed 0.966 and 0.969 (§1.1). The trend is not a fixed offset either. On calibration it vanishes under L-COAX at R2C32 (+0.011, SE 0.010) and **reverses** at R8C8 (pooled −0.062, SE 0.017; flat −0.113, SE 0.024). Its sign therefore depends on layout and setting. With the trees' ln(effective slots) 0.32 (fixed) and 0.46 (learned) below flat's, the utilization component of ρ can be several percent in either direction. That is enough to move ρ across 0.90 or 1.10. It is not enough by itself to reach 0.80.
3. **UTIL_K's likely evaluation value has no row in the outcome table.** The calibration analogue of UTIL_K with HB's layouts is ρ = 1.015 / 1.018 at R2C32. At R8C8 it is **1.191 / 1.168, with flat lower in 27/27 pairs**, close to FLAT BETTER. The outcome table has no row for UTIL_K = FLAT BETTER or DEGENERATE. It also does not say in which setting or settings UTIL_K is evaluated.

*Why it matters.* The positive outcome, the one that licenses proposing a scaling design, carries a claim ("not explained by utilization") that the design cannot check.

*Concrete change (the method is PENDING LEAD REVIEW):*

- Replace UTIL_K as the guard with a **utilization-adjusted comparison**, registered as a required co-condition for ADVANTAGE:
  - Per setting and per layout pair, regress E on ln(effective slots) over the 54 checkpoints, with a common slope and an architecture intercept.
  - Classify the adjusted ratio at the pooled mean ln(effective slots) with the same thresholds.
  - Effective slots come from P5's published histograms or from the evaluation counts, which the null already uses.
  - Report the slope with its SE and the matched-pair subset (12/27 fixed, 3/27 learned within ±20%) descriptively.
- Keep m(null, L)/m(null, L-FREQ) as a reported **"popularity cost of layout L"**, not as a criterion.
- State the settings for every criterion. Make the outcome table total.

### MAJOR

**M1 — The eviction tie rule turns page numbering into a hidden layout parameter, with layout-dependent effects as large as the effects being measured (§4 step 3, §5, §7 robustness grid).**

ADR-0013's tie rule evicts the oldest query's pages in ascending page number. Greedy page fill numbers pages in creation order, hottest seed first. That is the same structure the P7-A audit showed penalizes L-FREQ. On calibration, reversing the page order changes m as follows (§1.8):

- R2C32: by 2.5–4%.
- R8C8: by **5–12%**.
- The effect differs by layout. L-FREQ is penalized most (0.88–0.92), then L-COAX (0.92–0.94), then L-BCOAX (0.95–0.96).

So the draft's implicit premise that page creation order and branch order do not matter is wrong under the registered tie rule. Only row order within a page is exactly irrelevant (verified: ratio 1.000). E's denominator uses L-FREQ and its numerators use L-COAX or L-BCOAX, so the tie rule enters E differently on each side. At R8C8 it favours tree L-BCOAX over flat L-COAX by roughly 1–2 points of ρ and moves G by up to about 8 points. The branch-ordering rule ("by total count" against branch ID) acts only through this channel, by 0.3–1.2%.

*Change:*

- Report the descending order **for both numerator and denominator**, including the null streams, which P7-A never ran under descending order.
- Require each registered class to be the same under both orders at both criterion settings. Otherwise it is classed as order-dependent (MARGINAL).
- Alternatively, register a page-number-free tie rule for P7-B. Keep the ascending rule only for the P7-A reproduction check. **PENDING LEAD REVIEW.**
- §10 should add a test that row order within a page is irrelevant and that page relabelling changes results only through ties.

**M2 — Greedy is asymmetric between constrained and unconstrained clustering, so "the branch constraint only removes placements" is wrong in effect, and BC_K's descriptive reading is biased (§4 "Fairness of effort", §7 BC_K, §8 second bullet).**

A constrained greedy can beat an unconstrained greedy. Per checkpoint, BC reaches 0.88–0.90 at R8C8 (§1.5): the tree's branch-constrained layout gives 10–12% fewer misses than its own unconstrained greedy layout. The reason is that the branch restriction is an informative prior (62–69% of A₀ mass is within-branch) and also regularizes a myopic, hub-seeded heuristic.

A bounded refinement pass applied identically to both shows the asymmetry (§1.6):

- It improves unconstrained L-COAX by 3% (R2C32) and **10–11%** (R8C8).
- It improves L-BCOAX by only 2–3%.
- With refinement, cross-fitted BC moves from 1.02–1.03 to **1.11** at R8C8, and the tree/flat gain ratio moves from 1.01/1.08 to **1.10/1.18**.

Consequences:

- **(a)** An HB_K ADVANTAGE at the confirmation setting can come partly from the optimizer's weakness on the flat side. §8's statement that ADVANTAGE over greedy flat is an upper estimate is right, but §9 then uses it to license a scaling proposal.
- **(b)** "BC at or below 1: branches already contain the co-access structure" is optimizer-dependent and leans toward the hierarchy.
- **(c)** The opposite reading is safe. A stronger optimizer helps flat more, so EQUIVALENT or FLAT BETTER under greedy would not reverse. §8's sentence about EQUIVALENT ("conservative … only in the sense that it holds for this optimizer") should say this plainly.

*Change:*

- Register one deterministic, bounded refinement step applied identically to every co-access layout, either as part of the construction or as a required co-condition for ADVANTAGE. The swap search in `calib_coaccess.py` is one candidate. It costs well under a second per layout.
- Report BC under both greedy and refined layouts. Reword BC_K's reading.
- Correct "it is not extra search effort" in §4. **PENDING LEAD REVIEW.**

**M3 — The branch constraint's popularity cost is large at the confirmation setting and itself depends on utilization, so E(L-BCOAX) at R8C8 is a net of large opposing terms (§5 settings, §7).**

On the calibration null, L-BCOAX at R8C8 costs **1.22 (fixed) and 1.20 (learned)** times L-FREQ's misses, up to 1.92. L-COAX costs 1.03. The cost grows with concentration: slopes −0.50 (SE 0.09) and −0.37 (SE 0.06) per ln(effective slots). The random-partition control shows how expensive a structureless constraint is at R8C8: G = 1.48 for flat and 2.0–2.5 for trees. Packing 8-row pages inside 256-row groups strands hot rows on partly cold pages.

E_tree(L-BCOAX) at R8C8 therefore combines:

- a large within-branch co-selection benefit;
- a large, utilization-dependent popularity penalty;
- the tie-rule effect (M1);
- greedy's favourable asymmetry (M2).

A null result could hide a hierarchy benefit offset by these terms, and an ADVANTAGE could hide them the other way. The draft's rationale for R8C8, "more room for clustering to matter", omits the penalty.

*Change:*

- Register and report the two-part decomposition per layout: popularity cost m(null, L)/m(null, L-FREQ), and exploited structure m(actual, L)/m(null, L).
- Decide, recording it as a decision, whether R8C8 remains the confirmation setting or whether another non-degenerate setting with smaller pages relative to the branch would serve better (P7-A non-degenerate cells: R1–R2 × C8–C64, R8 × C8–C16). **PENDING LEAD REVIEW.**

**M4 — What is already known about the evaluation outcome, and the forking paths that follow (§3 last bullet, §5 settings, §8, §14 item 6).**

- **(a)** From published P7-A records alone, tree L-BFREQ against flat L-FREQ in E terms is 0.820 / 0.839 at R2C32 and **0.643 / 0.712 at R8C8, 27/27 pairs and 9/9 parents** (§1.2). The confirmation setting was chosen with these figures available.
- **(b)** Calibration-to-evaluation transfer is near-perfect. P7-A found that 0.02% of evaluation selections fall on calibration-zero slots. Here, split-half out-of-sample/in-sample is 1.000–1.014 (§1.7). Calibration-stream analogues therefore preview the evaluation outcome.
- **(c)** To answer this review's questions I computed those analogues (in-sample, calibration only, not registered tests):

  | Setting | Comparison | ρ (fixed / learned) | Tree lower in |
  |---|---|---|---|
  | R2C32 | HB-analogue | 0.987 / 1.011 | 16/27, 15/27 |
  | R8C8 | HB-analogue | 0.994 / 1.100 | 19/27, 8/27 |
  | R2C32 | HU-analogue | 0.965 / 0.993 | — |
  | R8C8 | HU-analogue | 0.977 / 1.039 | — |

  Under the registered rule all of these would be EQUIVALENT. The flat co-access gain on calibration (G = 0.76 at R2C32, 0.64 at R8C8) already exceeds the 15% branch-aware gain P7-A reported. The lead and the human lead now hold this information before the thresholds are approved.

§3 is honest that no layout is fitted to the evaluation stream. It does not say that the settings were chosen, and that the thresholds and prediction would be approved, with (a) to (c) available.

*Change:*

- Record in §8 and §14 exactly what was known when the settings, thresholds and prediction were fixed, citing this review's calibration figures.
- Do not change the thresholds or the equivalence band in response to them without recording that.
- The human lead should decide whether the evaluation run adds enough beyond the calibration analogue to justify running it, or whether a fresh stream is needed (question 6). **PENDING LEAD REVIEW.**

**M5 — "EQUIVALENT" by ratio alone can coexist with a consistent direction, and §9 over-reads it (§7 classes, §9 second row).**

The band 0.90–1.10 is about 10 naive standard errors of ρ wide. The paired SD of ln(E_tree/E_flat) is 0.038–0.049 at R2C32 and 0.058–0.069 at R8C8, which gives an SE of about 0.01. With the published L-FREQ numbers, ρ = 0.966 with the tree lower in **23/27 pairs and 9/9 parents** would be labelled EQUIVALENT. EQUIVALENT means "difference under 10%", not "no difference". §9's "The hierarchy adds nothing for storage that a post-hoc layout does not" overstates it.

The burden is also asymmetric. ADVANTAGE needs both settings, while EQUIVALENT and FLAT BETTER need only the primary. EQUIVALENT in the primary setting fixes the outcome even if the confirmation shows ADVANTAGE or FLAT BETTER.

Boundary cases, checked against the text:

- ρ = 0.80, 0.90, 1.10 and 1.25 all fall in closed intervals and resolve uniquely.
- ρ ≤ 0.80 without the counts, or ρ ≥ 1.25 without the counts, falls to MARGINAL.
- ρ in the band with 27/27 pairs one way is EQUIVALENT.
- The four classes are mutually exclusive and exhaustive.

*Change (PENDING LEAD REVIEW):*

- Either require EQUIVALENT to have neither side lower in ≥ 22/27 pairs, or rename the class "WITHIN ±10%" and always report direction and counts.
- Reword §9 to "a flat co-access layout comes within 10% of the hierarchy's incremental locality under greedy clustering".
- Decide whether EQUIVALENT and FLAT BETTER also need the confirmation setting.

**M6 — The outcome and decision tables are not total (§7 outcome table, §9).**

Missing cases:

- UTIL_K equal to FLAT BETTER or DEGENERATE (see B1);
- confirmation DEGENERATE combined with primary EQUIVALENT, FLAT BETTER or MARGINAL (only "any" is written);
- mixed tree-kind outcomes in §9, for example:
  - fixed EQUIVALENT with learned MARGINAL;
  - fixed ADVANTAGE with learned FLAT BETTER;
  - one tree kind UNRESOLVED.

  The "MARGINAL, NOT ROBUST or UTILIZATION-CONFOUNDED" row does not say "for at least one".

HU_K is registered in both settings but enters no outcome. That is fine if it is stated.

*Change:* add a precedence rule across tree kinds and complete the rows.

**M7 — The window W = 8 is not matched to the cache, and its stated rationale does not follow (§4 affinity).**

- The affinity excludes i = j, so reuse of the same row across queries, which is what P7-A's multi-query structure mostly was, never enters A_W. The LRU captures it under any layout.
- About 90% of A₈'s mass is chance co-occurrence of popular slots (TV distance from the null 0.085–0.099), against 0.69–0.77 for A₀.
- At R8C8, pages are evicted a median 1.7–3.4 queries after last use. Lags up to 8 mostly describe pairs the cache cannot exploit.
- On calibration, A₀ layouts do as well as A₈ at R2C32 and **better** at R8C8: G 0.604 against 0.638 (flat) and 0.624 against 0.645 (fixed).
- Residence times differ by architecture (trees' pages live longer), so a fixed W interacts with utilization.

*Change:* state the rationale correctly. Consider registering W per setting (for example W = 0 or a window tied to the measured eviction age) or W = 0 as primary, with W = 8 as the sensitivity variant. Any choice must be fixed before the run. **PENDING LEAD REVIEW.**

### MINOR (one line each)

- **m1 (§4, §10).** The affinity text is ambiguous enough to break §10's layout-hash agreement. Points to pin:
  - "adding the transpose" weights a same-query pair 2 per direction and a lagged pair 1 (verified in `test_reading.py`);
  - W = 8 means 9 query offsets, 0 to 8;
  - whether window pairs whose two queries both contain the same slot need any special handling (under my reading they need none).
- **m2 (§2, §11).** E's denominator should say "mean of the three null replicates' m", as P7-A averaged.
- **m3 (§10).** "A zero-affinity matrix must equal L-FREQ" holds for L-COAX (verified on all 81). For L-BCOAX, zero affinity gives branch-count-ordered within-branch frequency packing, which is not L-BFREQ, because L-BFREQ orders branches by ID. State the expected L-BCOAX result.
- **m4 (§10).** "Every miss count on the actual and null streams equals the P7-A record" for L-ID, L-RAND, L-FREQ and L-BFREQ cannot be checked as written: P7-A ran the null streams only on L-ID and L-FREQ, and the context-shuffled stream is not in P7-B. Enumerate exactly which P7-A records are re-produced. L-RAND reproduction depends on torch's generator under the locked `uv.lock`.
- **m5 (§11).** The 450/660 counts match the listed configurations. They omit:
  - the §6 calibration-stream transfer simulations (about 19,000 cache results);
  - whatever P7-A re-runs m4 requires (about 15,000).

  At P7-A's measured rate (38,070 results in 766 s), the full set is about 1,700 s against a 3,600 s cap. That is close to the mandatory twofold margin.
- **m6 (§11).** Layout construction is cheap if done sparsely. In my implementation, A₈ took 0.97 s, A₀ 0.11 s, and all greedy layouts at two R values 0.07 s per checkpoint. A dense 4,096-wide argmax per placement would be roughly 100× slower and could approach the 900 s cap. The timed dry run must include layout construction on full-size synthetic traces.
- **m7 (§8, omissions).** Register the **null-fit control** (co-access layouts fitted on the calibration null's affinity). On calibration, G = 0.999–1.010, so the algorithm does not manufacture locality. It is cheap and shows the result is not an artefact.
- **m8 (omissions).** Add a **random-partition constrained layout** for flat, with the same page structure as branches, as a descriptive control. On calibration it costs G = 1.48 for flat at R8C8, which calibrates how much a structureless constraint costs.
- **m9 (§6, §7).** At R8C8, unconstrained greedy layouts are unstable (mean |ln| between half-fits 0.033–0.048, maximum 0.11–0.16). L-BCOAX's is about 0.012. This adds per-checkpoint noise mainly to flat's E and to the pair counts. Report the split-half stability of each layout.
- **m10 (§7).** The non-degeneracy floors check only the L-FREQ null denominator. Add a floor or report on the numerators under co-access layouts. On calibration the numerators stay well above zero (minimum about 0.29), so this is a guard and not a current problem.
- **m11 (§4).** L-BCOAX at R = 512 (branch pairing by summed affinity) differs from every other R in kind. R ≥ 32 was degenerate in P7-A anyway. Say that R ≥ 32 co-access layouts are descriptive only.

### NOTE

- **N1.** ρ as a ratio of means of per-checkpoint ratios is acceptable. On the published data it differs from the pooled ratio and from the geometric-mean ratio by at most 0.006.
- **N2.** The greedy tie rules are complete and deterministic. (score, f) ties occur 1–29 times per layout, so the final slot-ID rule is exercised and must be tested. The seed rule and the "zero score: hottest unplaced" fall-through behave as described. Zero-score fills also place used slots (23–84 per layout), which is frequency packing within the page, as §4 says.
- **N3.** At R = 1 every greedy layout equals L-FREQ exactly (verified on all 81 calibration traces), so the R = 1 invariance check is valid.
- **N4.** Minimum detectable effect: because the paired SD of ln E is about 0.04–0.07, any effect reaching ρ ≤ 0.80 almost certainly also meets 22/27 and 8/9. The ratio clause binds and the count clauses are near-automatic at the threshold.
- **N5.** A trace-only structural prior for flat comparable to branches does not exist. Key geometry needs the checkpoints. The closest trace-only counterpart is a partition learned from flat's own A₀ (greedy at page size 256). That is co-access clustering at a coarser granularity and adds little beyond L-COAX.
- **N6.** A Belady (optimal-caching) bound was not computed. It would show how much of any layout effect is LRU-specific. It is nice to have, not required.

## 3. Answers to the specific questions, briefly

1. **E.** It is well-defined: the denominator is never below 0.49 at either setting. It does not remove utilization: there is a residual positive trend under L-FREQ and a negative one under L-COAX at R8C8 (B1). The ratio-of-means aggregate is fine (N1). UTIL_K measures the popularity cost of a layout. Under a working correction it should equal 1 only if the two layouts had equal popularity costs, which is unrelated to the correction. It can fail (L-BCOAX at R8C8 costs about 20% more than L-COAX) or pass for reasons unrelated to utilization, and it cannot return ADVANTAGE (B1). The utilization-adjusted ratio proposed in B1 is the better check.
2. **Layout algorithm.** The specification is unambiguous apart from m1. Greedy is hub-seeded and A₈ is about 90% popularity. Even so, the null-fit control shows no manufactured locality. Page creation order matters through the tie rule (M1). Branch ordering matters by under 1.2%, through ties only. Constrained greedy can beat unconstrained greedy, so the "only removes placements" claim fails in effect, and BC and HB lean toward trees at R8C8 (M2, M3).
3. **Greedy strength.** Greedy leaves 3% (R2C32) and 10% (R8C8) for unconstrained clustering, flat and tree alike, and 2–3% for constrained clustering. EQUIVALENT or FLAT BETTER is safe. ADVANTAGE, especially at the confirmation setting, is not, and §9 should not license a proposal on it without a registered refinement (M2).
4. **Sparsity and transfer.** See §1.4 and §1.7. Overfitting is negligible and does not differ by architecture at the primary setting. Unconstrained layouts are unstable at R8C8 (m9). W = 8 exceeds the cache residence at R8C8 by a factor of 3–4 (M7).
5. **Criteria.** The classes are exclusive and exhaustive. The outcome tables are not total (M6). EQUIVALENT by ratio alone can hide 23/27 lopsidedness (M5). The floors never bind. The confirmation setting remains informative after packing (§1.3).
6. **Reproduction and reuse.** Exact reproduction is feasible. My P7-A audit reproduced the primary setting for all 81 checkpoints and the full grid for 21, with independent code. The requirement as written is ill-defined (m4). The forking-paths exposure is real and only partly disclosed (M4).
7. **Decision rule.** ADVANTAGE → "propose capacity scaling" is too permissive as written: there is no valid utilization guard (B1), the optimizer is asymmetric (M2) and the confirmation setting is confounded (M3). EQUIVALENT → "do not scale the existing hierarchy" is supported in direction, because a stronger optimizer helps flat more, but the wording "adds nothing" is too strong (M5).
8. **Omissions.**
   - Cheap and needed: null-fit control (m7), a utilization-adjusted ρ (B1), descending order on both sides (M1), the popularity-cost / structure decomposition (M3), and a registered refinement pass (M2).
   - Nice to have: random-partition control (m8), in-sample calibration E (already computable), and the Belady bound (N6).
9. **Resources.** See m5 and m6. The registered set fits the caps if layouts are built sparsely, but the enumeration is incomplete.

## 4. What this review did not check

- Anything on the evaluation traces. Every co-access figure is a calibration-stream or calibration-null analogue. The calibration analogues are not the registered outcomes and are not predictions with stated error.
- The registered count-preserving null streams of the evaluation stream. I used a reviewer null of the calibration stream under my own seed.
- Reproduction of L-RAND (torch generator) or of the shuffled streams.
- Belady bounds, other optimizers (agglomerative merging, LRU-objective search), other windows than 0 and 8, and R ∉ {1, 2, 8} for co-access layouts.
- Whether ADR-0012 governance permits this study. That is a human decision.
- Implementation code. None exists for P7-B.
