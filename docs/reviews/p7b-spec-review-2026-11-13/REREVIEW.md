# P7-B specification re-review: ADR-0014 revision 3

- Reviewer: Claude Opus 5.5 (`claude-opus-5-5`), auditor role, separate context. Date 2026-11-13.
- Reviewed: `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md`, revision 3 (working tree, uncommitted modification on branch `claude/p7b-coaccess-layout-proposal`, HEAD `8480853`), SHA-256 `1420f67730dad899eefa69fb855e140cba7a902eb86136acbbd0e450ee9c3c15`.
- Earlier review: `docs/reviews/p7b-spec-review-2026-11-13/REVIEW.md` (revision 1). Not modified. The earlier `scripts/` and `outputs/` were not modified.
- **Status: independent engineering and mathematical evidence. Not Astra validation. Not human approval.** `Astra review: NOT_PERFORMED`. Scientific choices are marked **PENDING LEAD REVIEW**.

**Counts: 1 BLOCKER, 4 MAJOR, 14 MINOR, 6 NOTE. Recommendation: NOT READY (conditions in §6).**

## 0. Material, environment, what was and was not read

| Item | Value |
|---|---|
| Python | `.venv/bin/python -I`, CPython 3.12.14, standard library only. No `arborlm` import. No implementer analysis code used. My own revision-1 script `scripts/calib_coaccess.py` is imported for I/O, the LRU and the count-preserving null generator, with bytecode writing disabled. |
| Hardware | Apple M5 Max, 18 cores, macOS 27.2.1 |
| Trace files read | **Calibration only**: `experiments/P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e/traces/<label>/calib_selected.int16.bin` for all 81 checkpoints. Each file was checked against the SHA-256 in its P7-A trace record before use. No `calib_branches` file was read in this re-review. |
| Evaluation traces | **None opened.** No `eval_selected` or `eval_branches` file was opened. Every script asserts that no path containing `eval_` was read, and every JSON output records `eval_files_read: []`. |
| Raw validation file | **Not opened.** I listed the directory `data/wikitext2/` and opened no file in it. Nothing was reconstructed from the raw validation file. |
| Registered outcomes | None computed on any evaluation stream. Every co-access, partition and E figure below is a calibration-stream analogue (fit and score on calibration) or uses a reviewer null of the calibration stream (seed 77001, one replicate). They are not the registered quantities. |
| Text and code read | `AGENTS.md`; `CLAUDE.md`; ADR-0014 rev 3 (in full); my `REVIEW.md`; `src/arborlm/p5_data.py` (in full); `pilot_data.py` (`select`, `_sort_key`, `RECIPE`); `p7a_trace.py` lines 60–200; `p7a_core.py` (`check_trace`, null seeds, by grep); greps of `p6_fidelity_study.py`, `p6_common.py`, ADR-0011 and ADR-0013; `results/p5-preflight-2026-11-13/root-data-parent/audit.py` (grep); P7-A trace records (81, for file hashes); the P7-A trace and simulate manifests (wall seconds); P7-A worker records (key structure only); and `docs/reviews/p7b-spec-inputs-2026-11-13/panel_usage.md`. That file appeared, untracked, while this review was running (timestamp 18:02). At my first listing it did not exist. |
| Rank-use grep | `grep -rnE "2560\|3071\|3072\|2048" src configs docs tests`, and a JSON-only grep over `results/` and `experiments/` (no `.bin`). The only hits were coincidences inside IDs and counts. |

Commands, run from the repository root:

```sh
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/test_rev3.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/calib_partitions.py --jobs 16          # 35.6 s wall
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/aggregate_partitions.py               # 10 s
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/calib_learned_partition.py --jobs 16
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/adjusted_ratio_sensitivity.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/time_layouts.py --jobs 3 --labels b101-o301-flat-s501 b101-o301-fixed_tree-s501 b101-o301-learned_tree-s501
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/partition_identity.py
.venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/r1_invariance.py
```

Outputs are in `rereview/outputs/` (`*.log`, `*.json`). SHA-256 prefixes: `calib_partitions.json` `66ddfd39…`, `aggregate_partitions.json` `63f31114…`, `calib_learned_partition.json` `c37f0d5e…`, `time_layouts.json` `adc70e9a…`. Scripts: `rev3_layouts.py` `8a042a00…`, `calib_partitions.py` `bb36d968…`, `aggregate_partitions.py` `c6e38ee7…`.

**Failed attempts, kept:**

- `outputs/test_rev3_attempt1_FAILED_wrong_expectation.log`. My hand case expected the swap 1↔2. The registered rule visits slot 0 first and takes the equal-gain swap 0↔3. The mistake was mine; the code is correct. The expectation is corrected in place, with a comment.
- `outputs/time_layouts_attempt1_FAILED_affinity_w_keyerror.log`. A KeyError bug in my windowed-affinity helper `affinity_w`. Fixed in place, with a comment. After the fix, `outputs/affinity_crosscheck.log` shows A₈ identical to my revision-1 implementation, and A₀(rev 3) equal to half of A₀(rev 1) on one checkpoint. `affinity_w` is not used by `calib_partitions.py`, so those results are unaffected. `test_rev3_after_affinity_fix.log` reruns the self-checks.
- I deleted a two-checkpoint pilot output (`outputs/pilot2.json`). It had not failed. Its numbers are a subset of the full run. I disclose the deletion here.

**My own earlier error.** Revision-1 NOTE N3 said "the R = 1 invariance check is valid". That holds only for layouts whose R = 1 order equals L-FREQ (the greedy co-access layouts). It is false for L-ID, L-RAND, L-BFREQ, L-BCOAX and L-PCOAX: see RM1.

**How I read revision 3 §4.** These readings are implemented in `rev3_layouts.py` and checked by `test_rev3.py`:

- A₀[i][j] = number of queries with i and j both selected.
- Greedy fill exactly as steps 1–3.
- Refinement:
  - visit slots with nonzero affinity in (−f, id) order;
  - candidate pages Q ≠ P that hold a slot with nonzero affinity to x, in x's group if constrained;
  - y ranges over every slot on Q;
  - gain = new minus old within-page affinity = w(x,Q) − 2a(x,y) + w(y,P) − w(x,P) − w(y,Q);
  - take the best strictly positive gain, ties to lowest Q, then lowest y;
  - **y takes x's position and x takes y's (my reading: the text is silent)**;
  - at most 12 passes.
- Groups are ordered by descending total f, ties to lowest index.

The self-checks pass:

- a hand case with one forced swap;
- 300 random small cases, in which the objective never decreases, and on convergence a brute-force search finds no improving swap among those the rule considers, constrained and unconstrained;
- zero affinity gives L-FREQ with no swaps at R = 1, 2, 8 and 32;
- the five partitions cover all slots and are distinct.

---

## 1. Key numbers (calibration stream only, in-sample; not registered outcomes)

### 1.1 Five-partition control (PART_K analogue)

m_B is the misses under L-BCOAX. m_P is the mean of the misses under the five registered partition layouts, each built by the registered construction. Cell and parent counts are "m_B strictly lower".

| Setting, tie | Kind | mean m_B / mean m_P | cells | parents | per-partition ratio min..max | mean of per-cell ratios (Jensen) | CV across the 5 per checkpoint, mean / median / max | (max−min)/mean per checkpoint, mean / max | m_B below all five | clause 1 / clause 2 |
|---|---|---:|---:|---:|---|---:|---|---|---:|---|
| R2C32 asc | fixed | **0.616** | 27 | 9 | 0.608..0.627 | 0.611 | 0.045 / 0.038 / 0.098 | 0.111 / 0.234 | 27 | pass / pass |
| R2C32 asc | learned | **0.589** | 27 | 9 | 0.583..0.602 | 0.577 | 0.058 / 0.054 / 0.159 | 0.144 / 0.393 | 27 | pass / pass |
| R2C32 desc | fixed | 0.608 | 27 | 9 | 0.600..0.619 | 0.603 | 0.045 / 0.038 / 0.100 | 0.110 / 0.237 | 27 | pass / pass |
| R2C32 desc | learned | 0.581 | 27 | 9 | 0.575..0.592 | 0.569 | 0.058 / 0.053 / 0.160 | 0.143 / 0.399 | 27 | pass / pass |
| R8C8 asc | fixed | **0.282** | 27 | 9 | 0.279..0.285 | 0.279 | 0.063 / 0.053 / 0.167 | 0.157 / 0.354 | 27 | pass / pass |
| R8C8 asc | learned | **0.257** | 27 | 9 | 0.255..0.259 | 0.254 | 0.062 / 0.062 / 0.157 | 0.155 / 0.367 | 27 | pass / pass |
| R8C8 desc | fixed | 0.282 | 27 | 9 | 0.279..0.286 | 0.280 | 0.069 / 0.061 / 0.178 | 0.174 / 0.402 | 27 | pass / pass |
| R8C8 desc | learned | 0.258 | 27 | 9 | 0.256..0.260 | 0.255 | 0.074 / 0.073 / 0.194 | 0.184 / 0.424 | 27 | pass / pass |

**Operating characteristics.** I built 20 further random partitions with reviewer seeds 91701–91720 under the same construction. I then evaluated clause 1 and clause 2 on all C(25,5) = 53,130 five-subsets of the 25 partitions:

| Setting, tie | Kind | per-partition aggregate ratio over 25: mean (SD) [min, max] | P(clause 1) | P(clause 2) | P(clauses disagree) | five-subset mean ratio range |
|---|---|---|---:|---:|---:|---|
| R2C32 asc | fixed | 0.617 (0.0066) [0.603, 0.628] | 1.000 | 1.000 | 0.000 | 0.607–0.626 |
| R2C32 asc | learned | 0.593 (0.0081) [0.582, 0.615] | 1.000 | 1.000 | 0.000 | 0.584–0.605 |
| R8C8 asc | fixed | 0.282 (0.0028) [0.277, 0.288] | 1.000 | 1.000 | 0.000 | 0.278–0.286 |
| R8C8 asc | learned | 0.259 (0.0037) [0.254, 0.268] | 1.000 | 1.000 | 0.000 | 0.255–0.265 |

The descending-tie rows are the same to within 0.008 (`aggregate_partitions.log`).

**Why random partitions lose: popularity cost.** Popularity cost is m(null, L) / m(null, L-FREQ) on the reviewer calibration null, ascending ties:

| | branches (L-BCOAX) | random partitions (mean of 5) | profile-matched partitions (mean of 5) |
|---|---:|---:|---:|
| R2C32 fixed / learned | 1.052 / 1.065 | **1.331 / 1.474** | 1.178 / 1.218 |
| R8C8 fixed / learned | 1.279 / 1.281 | **2.262 / 2.755** | 1.597 / 1.698 |

The profile-matched partitions are a stronger null I constructed for this review; they are not registered. Within each bin of 16 consecutive calibration-frequency ranks, the real branch labels are permuted at random (seeds 91801–91805). So each group keeps its branch's popularity profile while its membership is scrambled.

**Stronger comparisons (trees, ascending; descending within 0.03):**

| | mean m_B / mean m_M (profile-matched), cells, parents | exploited structure, B vs random P: S = m(actual,L)/m(null,L), ratio, cells, parents | exploited structure, B vs profile-matched M |
|---|---|---|---|
| R2C32 fixed | 0.719, 27, 9 | **0.768**, 27, 9 | **0.800**, 27, 9 |
| R2C32 learned | 0.736, 27, 9 | **0.785**, 27, 9 | **0.835**, 27, 9 |
| R8C8 fixed | 0.419, 27, 9 | 0.463, 27, 9 | 0.520, 27, 9 |
| R8C8 learned | 0.463, 27, 9 | 0.504, 27, 9 | 0.598, 27, 9 |

**A data-derived partition.** This is a reviewer control, not registered: 16 groups formed by step-1 greedy at page size 256 on A₀, followed by the L-BCOAX construction. It gives m / m(L-COAX) = 0.998–1.002 for every kind and both settings. It equals unconstrained clustering and adds nothing beyond it. Under the registered configuration BC = m(L-BCOAX) / m(L-COAX) is 1.034 / 1.018 at R2C32 and 1.079 / 1.080 at R8C8 (fixed / learned, ascending). On calibration, the branch constraint no longer helps the heuristic on the trees' own traces.

**Flat checkpoints.** m(partition) / m(L-COAX) = 1.50–1.52 at R2C32 and 2.95–2.98 at R8C8 (ascending). The CV across the five partitions is 0.030 and 0.043.

### 1.2 The registered layout construction

- **Refinement.** Over 3,780 layouts at R = 2 and 8, built from A₀, at most **7** passes were used, and every layout converged inside 12 passes. On the three timed checkpoints, across all six R values and the A₈ variants, at most 6 passes were used. The 12-pass bound never binds.
- **Effect of refinement, m(refined) / m(greedy) for L-COAX:** 0.983 (flat), 0.981 (fixed), 0.983 (learned) at R2C32, and 0.969, 0.970, 0.969 at R8C8. Per checkpoint the range is 0.87–1.07. Refinement maximizes affinity, not misses, and can increase misses by up to 7%.
- **HB analogue under the registered configuration.** E = m(actual, L) / m(reviewer null, L-FREQ), with x the ln of the calibration effective-slot count:

| Comp, setting, tie | Kind | ρ | tree lower: cells, parents | common slope b (SE) | a + b·x̄ | ρ_adj | class (analogue) |
|---|---|---:|---|---|---:|---:|---|
| HB R2C32 asc | fixed | 0.999 | 14, 4 | −0.026 (0.014) | 0.715 | 0.988 | WITHIN 10% |
| HB R2C32 asc | learned | 1.032 | 10, 4 | −0.062 (0.024) | 0.725 | 0.992 | WITHIN 10% |
| HB R8C8 asc | fixed | 1.088 | 5, 2 | −0.205 (0.024) | 0.548 | 0.964 | WITHIN 10% |
| HB R8C8 desc | fixed | 1.108 | 5, 1 | −0.201 (0.025) | 0.588 | 0.994 | INTERMEDIATE → **TIE-RULE DEPENDENT** |
| HB R8C8 asc | learned | **1.208** | 2, 0 | −0.233 (0.039) | 0.569 | **0.999** | INTERMEDIATE |

All 16 HB and HU rows are in `aggregate_partitions.log`. On calibration, the registered rule would give **WITHIN 10% OF FLAT CO-ACCESS for both tree kinds**, with PART_K REAL BRANCHES BETTER in both settings. §0 of the ADR still quotes the revision-1 configuration (A₈, greedy): 0.99 / 1.01 and 0.99 / 1.10.

### 1.3 Utilization adjustment: the common-slope assumption (`adjusted_ratio_sensitivity.log`)

| Setting, tie | Kind | tree slope (SE) | flat slope (SE) | z(difference) | separate-slope ratio at pooled x̄ / flat mean / tree mean |
|---|---|---|---|---:|---|
| R2C32 asc | fixed | −0.030 (0.024) | −0.021 (0.016) | −0.33 | 0.988 / 0.986 / 0.990 |
| R2C32 asc | learned | −0.108 (0.046) | −0.021 (0.016) | −1.81 | 0.990 / 0.961 / 1.018 |
| R8C8 asc | fixed | −0.272 (0.037) | −0.137 (0.024) | **−3.05** | 0.964 / **0.921 / 1.004** |
| R8C8 asc | learned | −0.345 (0.071) | −0.137 (0.024) | **−2.78** | 0.993 / **0.900 / 1.077** |

The ln effective-slot ranges are 3.75–4.95 for trees and 4.44–5.29 for flat, so they overlap only partly.

### 1.4 R = 1 invariance (`r1_invariance.log`, calibration)

Capacity misses per query at R = 1, L-ID against L-FREQ:

- They are equal at C = 8.
- They differ at C ≥ 16. For example, for learned s501 at C32, ascending ties: 3.761 against 3.816 (1.5%). With descending ties the order reverses: 3.746 against 3.686.
- Across checkpoints and C the difference is 0.3–3%.

### 1.5 Partition identity (`partition_identity.log`)

| Seed | SHA-256 of 4,096 uint8 group IDs in slot order (auditor's encoding) | SHA-256 of the shuffled list (uint16 LE) |
|---|---|---|
| 91601 | `0ae2804b84b4ecc130c4860b5f5da2c5b75ecbcfe6b01cee5062e07c0769fcef` | `ae626b43df264708466a8afc9c2b5434c3db053e7b57f27800b9674192b16487` |
| 91602 | `1c3710a9123245697138c597ced80043ee2ef1e3d4a62bb095cd7b66010ece85` | `0d310a05d82ef6eba8cc5adbeba16a88d74a5221353eb0208c1e755f3230e9f3` |
| 91603 | `806f4a0b146196c93f68e7146d9cab31915b5df3d79efd56906778e255a08e75` | `55cbff61076689e78f030d374b741aa28f448484694f51d3f65dbc56db183af5` |
| 91604 | `5ed106a5370d2afadd118230986a1ecf1b47343b99279f70954eb3b12f2f73c1` | `98142918ba5f6ef34e6b9d3efc1f27a7c5ea9fd821bfb2b862641145af6f25a2` |
| 91605 | `75b8bee3da6934b1d463e5445f9f75d5656befe6be6f61f8e4d812beeaf4c8ff` | `8d55366cd4d23a08e651161638e0b0cc34dbee0ad13764e3181ffa2b5db26a0c` |

- All five are pairwise different as set partitions. The largest overlap between any two groups of different partitions is 33 of 256 slots.
- The largest overlap between a random group and a real branch is 28 of 256; 16 would be expected.

### 1.6 Resource projections (counts under my reading of §6 and §11)

| Per checkpoint, per stream | Flat | Tree |
|---|---:|---:|
| Actual stream, every layout × 30 settings (ascending) | 14 layouts → 420 | 18 → 540 |
| 3 nulls + order-shuffled on L-FREQ, L-COAX (+ L-BCOAX) × 30 | 240 | 360 |
| Descending ties at the 2 criterion settings: criterion numerators + L-FREQ actual + 3 L-FREQ nulls | 10 | 22 |
| **Stream B total** | **670** | **922** |
| Stream A extra: L-ID on 3 nulls + order-shuffled (P7-A reproduction) | +120 | +120 |
| Calibration-transfer, if every layout × 30 (the same for both streams) | 420 | 540 |
| If "popularity cost of each layout" (§7) puts every other co-access and partition layout on the 3 nulls × 30 | +720 | +990 |

Simulation totals and times. Times use P7-A's measured sequential rate of 38,070 results in 766 s (49.7 per second, one process). My own pure-Python LRU runs at about 0.04 s per result, roughly 2× slower.

| Stage | Results | Time at the P7-A rate | Against 5,400 s |
|---|---:|---:|---|
| Stream A, minimal reading | 77,598 | 1,561 s | 3.5× |
| Stream B, minimal reading | 67,878 | 1,366 s | 4.0× |
| Calibration transfer, once | 40,500 | 815 s | — |
| Stream A, if transfer is charged to it | 118,098 | 2,376 s | **2.3×** |
| Maximal reading (every layout on nulls, plus transfer), stream A | 191,000 | ≈3,840 s | **1.4×, fails the 2× rule unless parallel** |
| Maximal reading, stream B | 181,000 | ≈3,650 s | 1.5× |

Layout construction, measured on three checkpoints:

- The complete revision-3 set is A₀, A₈, a calibration null with its A₀ for L-NCOAX, and every co-access and partition layout at all six R values: 54 builds for flat and 72 for trees, with greedy-only layouts as intermediates.
- It took **1.3–1.6 s per checkpoint** in one process. A₈ accounts for about 0.75 s of that.
- For 81 checkpoints that is about 125 s sequential, against **2,700 s: about 21×**.
- The stated build counts (9 per R for flat, 12 for trees) are consistent with §4.

Stream B trace generation: P7-A's trace stage, which replayed the NLL and wrote evaluation and calibration traces for 81 checkpoints, took 135 s wall. A stream-B stage of the same kind fits 600 s at about 4×, including the regeneration check recommended in RM3.

---

## 2. Part 1: status of the revision-1 findings

| Finding | Status | Section | Reasoning |
|---|---|---|---|
| **B1** UTIL_K could not fire; utilization residue | **FIXED**, with residual minors r1 and r2 | §2, §7 | UTIL_K is removed. ρ_adj is defined and required with ρ for every non-INTERMEDIATE class. Residual gaps: which x for stream B, a ≤ 0 denominator, and the common slope at R8C8 (§1.3). Because both are required, a model-dependent ρ_adj can only block a class, never create one. Under co-access layouts the slope is negative, so for "tree better" the raw ratio is the binding side. The bias is toward INTERMEDIATE, symmetric and conservative. |
| **M1** tie rule | **FIXED** | §5, §7 | Both orders apply to numerators and denominators, and the class must agree. The rule bites: the calibration analogue is TIE-RULE DEPENDENT at R8C8 for fixed trees (§1.2). New consequence: the R = 1 invariant is false (RM1). |
| **M2** greedy asymmetry | **FIXED** | §4 | Refinement is registered for every co-access layout, the claim is withdrawn, and greedy-only is kept as a sensitivity. The rule matches my revision-1 search in structure: same visit order, same candidate pages, best swap per x, 12 passes. It differs in the final tie rule (mine took the first found) and in the affinity (A₈ then, A₀ now). Under the registered rule, 12 passes always sufficed (at most 7). The §4 rationale numbers (3% and 10%) come from the A₈ configuration; with A₀ the figures are 1.7% and 3.1% (r6). |
| **M3** contiguity's popularity cost | **FIXED** | §5, §6 | The decomposition is registered, and keeping R8C8 is the lead's recorded choice. |
| **M4** outcome already visible | **FIXED by the lead's decision** (stream B) | §0, §7a | The §0 figures are stale for the registered configuration (r6), and §13 keeps a remnant (r9). |
| **M5** EQUIVALENT | **FIXED** | §7, §9 | Renamed WITHIN 10%, with direction always reported. The asymmetry between settings remains, and the lead accepted the decision framework (§15). |
| **M6** tables not total | **PARTLY** | §7, §7a, §9 | The §7 outcome table is ordered and total (checked below). The two-stream layer and §9 reintroduce conflicts and undefined orders (RM2). |
| **M7** window | **FIXED** | §4 | A₀ is registered and the definition is unambiguous. A₈'s offset-0 term is 2·A₀, consistent with my revision-1 reading. |
| m1 affinity text | **FIXED** | §4 | New hash ambiguities elsewhere (RM4). |
| m2 denominator | FIXED | §2 | |
| m3 zero affinity | FIXED | §4 | Verified: zero A gives L-FREQ with no swaps. |
| m4 reproduction scope | FIXED | §10 | Stream A only. |
| m5 resource enumeration | **PARTLY** | §11 | Qualitative only. Whether calibration transfer is counted once or per stream, nulls for "every layout", and wall time against worker time are all undefined (r3). |
| m6 layout timing / dry run | FIXED | §11 | |
| m7 null-fit control | FIXED | §4 | L-NCOAX. |
| m8 random-partition control | **FIXED as asked, but the control is non-discriminating** | §4, §7 | See RB1. |
| m9 report split-half stability | **PARTLY** | §8 | Stated as a risk, not registered as a measurement (r14). |
| m10 numerator floors | FIXED | §7 | |
| m11 R ≥ 32 descriptive | FIXED | §4 | |
| N3 (mine) R = 1 check valid | **My error** | §4, §10 | See RM1. |

**§7 class order and exhaustiveness.**

- The four classes are evaluated in order, and INTERMEDIATE catches everything else, so the list is total. TIE-RULE DEPENDENT maps to INTERMEDIATE.
- TREE MATERIALLY BETTER and FLAT MATERIALLY BETTER cannot both hold.
- WITHIN 10% cannot coexist with either material class, because their ρ ranges are disjoint.
- Boundaries 0.80, 0.90, 1.10 and 1.25 are closed and resolve uniquely.
- The outcome table is total: its last row is "anything else".
- Odd but registered cases:
  - Primary WITHIN 10% with confirmation TREE MATERIALLY BETTER gives WITHIN 10% OF FLAT CO-ACCESS.
  - PART_K DEGENERATE or TIE-RULE DEPENDENT with HB better in both settings gives "PARTITION ADVANTAGE … an arbitrary partition does as well", a statement no test supports (r10).

**Greedy and refinement tie rules.**

- Greedy: complete.
- Refinement:
  - Complete for choosing the swap. Integer gains make ties common, and the specified order (Q, then y) resolves them.
  - The gain formula is implied unambiguously by "change in total within-page affinity".
  - Not specified: where y goes inside P. That is irrelevant to misses but matters for hashes (RM4).
  - Exactly one layout results once the swap position and the R = 512 within-group order are fixed.

---

## 3. Findings

### BLOCKER

**RB1. The five-partition guard (PART_K) cannot fail, so the positive outcome's "branch-specific" qualifier rests on no test (§4 L-PCOAX, §7 PART_K, outcome rows 2–3, §9 row 1).**

*What is wrong.* A random partition into 16 groups of 256 is not a neutral constraint. It scatters each checkpoint's popular rows across 16 groups, so every group ends with partly hot pages. On the calibration null, the five registered partitions cost 1.33–1.47× L-FREQ's misses at R2C32 and 2.26–2.76× at R8C8. Real branches cost 1.05–1.07× and 1.28×. Consequences:

- **It always passes.** On calibration, m_B / mean m_P = 0.58–0.62 at R2C32 and 0.26–0.28 at R8C8, with 27/27 cells and 9/9 parents under both tie rules.
- **Its operating characteristics are degenerate.** All 53,130 five-subsets of 25 random partitions satisfy both clauses. Clause 2 never disagrees with clause 1. The largest single-partition ratio among 25 is 0.628, against a threshold of 0.80. Calibration-to-evaluation transfer is near-perfect (revision-1 §1.7), so there is no realistic evaluation-stream path to NOT BETTER.
- **The decision tree collapses.** HIERARCHY-SPECIFIC ADVANTAGE reduces to "HB_K TREE MATERIALLY BETTER in both settings", and the row PARTITION ADVANTAGE, NOT BRANCH-SPECIFIC is unreachable in practice.
- **Explanations 4 and 5 are not separated.** Explanation 5 ("any partition helps as much") is refuted trivially, because random partitions hurt. Explanation 4 (a constraint makes the heuristic's problem easier) would need a constraint with a comparable popularity cost, and a random partition makes the problem harder.
- **This is the same defect as revision-1 B1.** A registered guard on the only scale-licensing outcome cannot fire.

Five partitions are ample for what PART_K measures: the SD of the per-partition aggregate ratio is 0.003–0.008. The number of partitions is not the problem; the null is.

*Why it matters.* §9 row 1 lets the study state that branch placement gives locality "that an arbitrary partition does not give the tree" and propose capacity scaling. The comparison behind that phrase is decided before the run.

*Concrete change. The choice is a scientific one: **PENDING LEAD REVIEW**.* Any one of these, fixed before the freeze:

1. **Evaluate PART_K on exploited structure.** Use S(L) = m(actual, L) / mean over the three nulls of m(null, L), so each layout is normalized by its own popularity cost. This needs the five partition layouts on the three null streams at the two criterion settings under both tie rules: 60 extra simulations per tree checkpoint per stream, negligible. On calibration this gives B/P = 0.77–0.79 at R2C32, near the 0.80 margin and therefore informative, and 0.46–0.52 at R8C8.
2. **Use a popularity-matched null.** Partitions that keep each branch's popularity profile and scramble membership, for example my profile-matched construction: label permutation within 16-rank frequency bins, five seeds. Raw B/M is 0.72–0.74 at R2C32 and 0.42–0.47 at R8C8; exploited-structure B/M is 0.80–0.84 at R2C32. Combining 1 and 2 is the strictest option.
3. **Keep the current PART_K but demote it.** Report it descriptively as "real branches cost less than random groups of the same shape". Remove it from outcome rows 2 and 3. Delete "and that an arbitrary partition does not give the tree" from §9 row 1. State that explanation 4 is addressed only through BC_K and HU_K. Under the registered configuration on calibration, BC_K = 1.02–1.08, so the branch constraint does not help the heuristic.

A data-derived partition (greedy at page size 256) is not a useful null: it reproduces L-COAX to within 0.2%.

### MAJOR

**RM1. "At R = 1 every layout is identical" is false under the registered tie rule, and §10 and §11 make it a stop condition (§4 last paragraph, §10 fourth bullet, §11 stop list).**

At R = 1 every page is a single row, so page numbers differ between layouts. When eviction must split the oldest query's pages (C ≥ 16), capacity misses depend on the layout. On calibration, L-ID and L-FREQ differ by 0.3–3%, and the direction flips between tie rules (§1.4). They agree only at C = 8, and among layouts whose R = 1 order equals L-FREQ (the greedy co-access layouts; this is what my revision-1 N3 verified). As written, the first R = 1 check across L-ID, L-RAND, L-BFREQ, L-BCOAX or L-PCOAX would raise an "invariant violation" and stop the study. That would invite an unregistered mid-run fix.

*Change:* Restate the invariant. At R = 1, these are identical across all layouts:

- distinct pages per query;
- first-touch misses;
- uncached read amplification;
- capacity misses at C ≤ 8.

Capacity misses at C ≥ 16 are identical only among layouts with the same row order. In §4, replace "All layouts must give identical results there" with that statement.

**RM2. The decision layer is not a function of the outcomes after the two-stream amendment (§7a combination table, §9).**

- **(i) Two rows apply to one state.** Fixed trees WITHIN 10% on stream A and FLAT CO-ACCESS BETTER on stream B is NOT REPLICATED under §7a, which points to §9 row 4 ("human lead decides whether a stronger test is worth it"). It also satisfies §9 row 2 ("the two streams need not give the same one of these two"), which says "do not scale … redesign or stop". The §9 rows are not declared ordered.
- **(ii) "Most favourable outcome among the two tree kinds"** has no defined order. Row 2 requires both kinds, which conflicts with "the most favourable decides". Example: fixed WITHIN 10% REPLICATED and learned INTERMEDIATE.
- **(iii) Both streams UNRESOLVED** matches both "identical → REPLICATED" and "either UNRESOLVED → SINGLE-STREAM".
- **(iv) Direction.** It is not said whether the direction in "INTERMEDIATE, with direction" is part of the label compared for identity.
- **(v) The §7a table** has "identical | identical" and "differ | differ" in the per-stream columns, so it does not map pairs of outcomes to a combined outcome.

*Change:*

- Define the combined outcome as a function, with precedence: both UNRESOLVED → UNRESOLVED; one UNRESOLVED → SINGLE-STREAM; labels equal (direction excluded or included, stated) → REPLICATED; otherwise NOT REPLICATED.
- Add an explicit ranking of outcomes for combining tree kinds.
- Make §9's rows ordered and first-match, and decide whether the WITHIN 10% / FLAT BETTER cross-stream mix belongs in row 2 or row 4. **PENDING LEAD REVIEW** for the order and the mix.

**RM3. Stream B trace generation and integrity are under-specified (§7a second bullet, §10, §3).**

- P7-A's `trace_checkpoint` (`p7a_trace.py:75–123`) replays the NLL on `source.panel` and traces that same panel together with the calibration stream. It cannot produce stream B unchanged: feeding it the stream-B panel would compute an NLL on stream B (which §7a forbids) and fail the bitwise check. Only `collect_trace` and `check_trace` are reusable as-is.
- P7-A's strongest integrity check, that the evaluation histogram equals the P5 per-slot histogram (`check_trace(recorded=…)`), has no stream-B counterpart. Stream B's correctness would rest on structural checks alone.
- No stream-B trace or null hash is required to be recorded before simulation.

*Change. Specify a new driver:*

1. Load each checkpoint, replay the P5 NLL bitwise on the P5 panel, and check file hashes before and after.
2. Run `collect_trace` on the stream-B panel.
3. In the same process, regenerate the stream-A evaluation trace and the calibration trace, and require them to be byte-identical to the identity manifest. This substitutes for the missing histogram check and costs about the P7-A trace time, inside 600 s.
4. Run `check_trace` with `recorded=None`.
5. Write a stream-B identity manifest: panel SHA-256, trace-file SHA-256s, per-slot histograms, unique counts, and null-stream `stream_sha256`. Commit it before any simulation. The auditor regenerates the stream-B null hashes independently.

**RM4. Layout hashes are not reproducible from the text, and a hash mismatch is a stop condition (§4 step 2, §4 R = 512, §10 last bullet).**

Three things are unspecified:

- (a) **The position of the swapped slots.** Does y take x's place in P? Row order within a page does not change misses, but it does change any position-based hash.
- (b) **Row order inside each group at R = 512,** where a page is two whole groups.
- (c) **The hash encoding.** What is hashed, and in what byte order?

An implementer and an auditor reading the text independently can disagree on all three. §10 then stops the study.

*Change:* State that a swap exchanges positions, and fix the within-group order at R = 512 (for example, step 1 at R = 256 inside the group, or ascending slot ID). Better still, define the layout hash over a canonical form, for example the sequence of pages in page order with each page's slot IDs sorted ascending, as little-endian uint16. Within-page order then cannot cause spurious mismatches. Add the partition group-ID hashes (§1.5) to the frozen record.

### MINOR (one line each)

- **r1 (§2).** Say that x is ln of the exp-entropy effective slot count of the stream being classified, from its own trace over all 32,768 queries. For stream A this equals the P5 histogram by P7-A's integrity check. Also give a rule for a + b·x̄ ≤ 0.05 (ρ_adj undefined → INTERMEDIATE). On calibration the denominator is 0.55–0.73, so it never binds.
- **r2 (§2, §8).** The common slope is adequate at R2C32 (|z| ≤ 1.8) but rejected at R8C8 (z −2.0 to −3.1). There the separate-slope ratio spans 0.90–1.08 depending on the evaluation point. Report the per-architecture slopes, the interaction z and the separate-slope ratios at both architecture means descriptively. Any new rule is **PENDING LEAD REVIEW**.
- **r3 (§11).** Say whether the caps are wall time or active worker time and whether parallel workers are allowed. Say whether calibration transfer is run once or per stream and at which settings. Under the maximal reading (r4), sequential simulation misses the 2× margin (1.4–1.5×).
- **r4 (§6 vs §11 vs §7).** §6 puts "every criterion layout" on the null and order-shuffled streams, and §7 reports the "popularity cost of each layout". §11 runs the partition layouts on the actual stream only and the nulls only on L-FREQ, L-COAX and L-BCOAX. Pick one and enumerate it. RB1 option 1 needs the partition layouts on the nulls.
- **r5 (§7a).** Stream-B nulls reuse stream A's seeds (91301–91303 × 1000 + cell index). The occurrence lists have the same length (262,144), so `random.Random.shuffle` applies the same position permutation on both streams, and their Monte Carlo noise is coupled. Use distinct seeds (for example 91321–91323), or state the coupling. **PENDING LEAD REVIEW.**
- **r6 (§0, §4).** The §0 analogue figures and the §4 refinement rationale (3% and 10%) come from the revision-1 configuration (A₈, greedy, my own first-found tie rule). Under the registered configuration on calibration:
  - HB ρ is 1.00 / 1.03 at R2C32 and 1.09 / 1.21 at R8C8, with ρ_adj 0.99 / 0.99 and 0.96 / 1.00;
  - the analogue outcome is WITHIN 10% for both kinds;
  - refinement gains are 1.7% and 3.1%;
  - BC is 1.02–1.08.

  Disclose these as calibration-only figures now known.
- **r7 (§4, §10).** `random.Random.shuffle` is not guaranteed stable across Python versions; only `random()` is. Python is pinned to 3.12.*. Register the five partitions' hashes (§1.5) and test against them. Define "pairwise different" as different set partitions (verified).
- **r8 (§7 PART_K).** Clause 2 implies clause 1's ratio part, because the mean over partitions of the per-partition means is the mean of m_P. So clause 1 adds only the counts. The DEGENERATE rule (mean m_P < 0.01) cannot bind, because partitions inflate m_P. Mirror HB's rule instead: both tie rules, a per-checkpoint floor and an m_B floor.
- **r9 (remnants).**
  - §13 M4 row says "an optional fresh-stream replication is defined (§7) and put to the human lead (§14)".
  - §13 says "whether the run is still worth doing".
  - The §13 minor row reads "L-PCOAX, promoted to a criterion input" (singular), and §4 reads "it is read against L-PCOAX".
  - §3's "Streams" bullet and §6's "on the evaluation stream" name one evaluation stream.
  - §3 and §10's null `stream_sha256` check applies to stream A only and should say so.
  - §9 row 1's "an arbitrary partition" generalizes beyond five.
- **r10 (§7 outcome row 3).** "PART_K not in both" includes PART DEGENERATE and TIE-RULE DEPENDENT, yet the label asserts "an arbitrary partition does as well". Add a row, or word it as "real-branch advantage not shown".
- **r11 (§10).**
  - Fix the auditor's "registered selection of checkpoints" at the freeze.
  - The auditor's rebuild omits L-NCOAX, the control that can flag every co-access result.
  - It also omits R ∉ {2, 8}. Include L-NCOAX at R = 2 and 8 at least.
- **r12 (§7a, §12).**
  - State that once stream A simulation starts, stream B is simulated unconditionally unless a listed stop condition fires, and that any other abort is a recorded deviation.
  - Commit the stream-B trace hashes before stream A is simulated.
  - Run both simulations in one invocation if possible.
  - §7a says the layouts are "fixed before any evaluation simulation", but §12 makes the freeze commit before the layouts are built. Say that the layout hashes are committed, after the auditor reproduces them, before simulation.
- **r13 (§7a, §8: freshness and independence).**
  - Exact-payload disjointness is guaranteed by construction. The recipe deduplicates by payload digest across the whole validation split, keeping the lowest rank. It excludes every training-candidate digest, which covers the calibration ranks. Ranking is a total order, so the first 3,072 contain the first 2,560 unchanged.
  - The required checks remain cheap confirmation. Also require the 3,072-row reconstruction to reproduce the P1–P5 panel hashes.
  - Rank is a hash of (row, offset), so stream B samples the same articles as stream A. The replication is over fresh contexts from the same articles, not an independent text source. Say so in §8.
  - `panel_usage.md` (clerk) finds no use of ranks ≥ 2560. Its NEEDS REVIEW 1 (interval convention) is settled by code: `p5_data.panel` requires exactly 2,560 selected candidates and slices `validation[2048:]`, so rank 2560 was never selected.
  - That file is untracked and should be committed before the freeze.
- **r14 (§6).** Revision-1 m9: register the split-half stability of each criterion layout as a measurement, not only as a §8 risk.

### NOTE

- **n1.** The five-partition construction is exactly specified and reproducible on CPython 3.12.14. Groups are taken by position in the shuffled list and ordered by descending total count, ties to lowest group index. Group ordering affects results only through eviction ties.
- **n2.** The fitting budget for L-BCOAX and the L-PCOAX layouts is identical in effect: same greedy, same restricted refinement, the 12-pass bound never binds, same R = 512 group-level step. Partition layouts make fewer swaps (mean 20–34 against 28–36), because within-group affinity is sparse. That is a property of the null, not of the budget.
- **n3.** Averaging misses over partitions before forming the ratio, rather than averaging per-partition ratios, changes the PART ratio by at most 0.012. This is immaterial.
- **n4.** Requiring identical labels across streams is appropriate for the positive outcome. For WITHIN 10% it is unlikely to bind, because the calibration analogue sits about 0.07–0.10 from the band edges at R2C32.
- **n5.** Nothing computed on stream A enters stream B's processing. Layouts come from calibration only. x, the nulls and non-degeneracy are per stream. Analysis runs once. The residual exposure is an abort after viewing stream A's raw miss counts (r12).
- **n6.** Should partitions keep branch sizes or branch order? Keeping sizes and shuffling membership is what L-PCOAX does. Shuffling branch order alone is irrelevant (≤ 1.2%, through ties). The right null for "real branches carry co-access structure" must also keep the popularity profile (RB1). **PENDING LEAD REVIEW.**

---

## 4. Part 2 answers in brief

- **(a) Five partitions.**
  - The construction is exact and reproducible on the pinned Python (r7 for hashes).
  - The partitions are distinct (§1.5), and the budget is identical (n2).
  - The aggregate rule is well-defined and not circular, but not falsifiable in practice (RB1).
  - Spread across the five, per checkpoint: CV 4–7% on average and up to 16–19%; (max − min)/mean up to 0.42. The aggregate SD is 0.003–0.008.
  - Five partitions are enough for the aggregate statement. A random partition is the wrong null for the branch-specific claim.
- **(b) Two streams.**
  - The combination rule is not total as written (RM2).
  - Stream B is under-specified in trace generation and integrity (RM3), in x (r1) and in null seeds (r5).
  - There is no outcome leak by design (n5).
  - Layout-hash reproduction is sufficient once the hash is defined (RM4) and the stream-B trace hashes are committed before simulation (r12).
  - The §12 order is coherent.
- **(c) Fresh panel.**
  - Disjointness holds by construction and should still be checked (r13).
  - No code path or record that I read touches ranks ≥ 2560. P6-Q's replication was declined (ADR-0011 §262), its code hard-codes the P5 panel, P7-A uses `EVAL_RANKS = (2048, 2560)`, and the P5 preflight audit slices `[:2560]`.
  - I cannot exclude use outside the repository.
- **(d) Resources.** See §1.6. The layout stage has about 21× margin. Simulation has 2.3–4.0× margin under the minimal reading, and too little under the maximal sequential reading (r3, r4).
- **(e) Contradictions and remnants.** RM1, RM2, r4, r9, r10 and r12.

## 5. What this re-review did not check

- Anything on an evaluation trace, the registered evaluation or calibration null streams (I used a reviewer null), or L-RAND, L-ID, L-NCOAX and the A₈ layouts on calibration misses (A₈ was used only for timing).
- Out-of-sample (split-half) behaviour under the registered A₀ configuration.
- Co-access layouts at R ∉ {2, 8} for misses (they were timed only), and R = 512 group-level construction beyond timing.
- The raw validation file, the stream-B panel itself, and any external or uncommitted use of ranks ≥ 2560.
- Implementation code: none exists for P7-B.
- Whether the study-specific governance is adequate. That is a human decision.

## 6. Recommendation

**NOT READY.** Conditions before final human execution approval:

1. **RB1:** a recorded lead decision on the partition null: option 1, 2 or 3, or a stated alternative. **PENDING LEAD REVIEW.**
2. **RM1:** restate the R = 1 invariant.
3. **RM2:** make the stream combination and the §9 decision rows a total, ordered function, including the order of outcomes across tree kinds.
4. **RM3:** specify the stream-B trace driver, its integrity checks and a pre-simulation stream-B identity manifest.
5. **RM4:** make the layout hashes reproducible from the text: swap position, R = 512 within-group order, a canonical hash encoding, and registered partition hashes.

The MINOR items are recommended. r3/r4 (resource reading) and r12 (abort rule) should be settled before the timing dry run.

Independent mathematical and engineering evidence only. Not Astra validation, not human approval.
