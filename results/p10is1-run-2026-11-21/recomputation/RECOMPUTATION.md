# P10-I-S1: independent recomputation of the registered outcome (2026-11-21)

Auditor: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`). Independent engineering evidence. **It is not Astra validation, not human approval and not acceptance.** `Astra review: NOT_PERFORMED`.

- **Run:** freeze commit `46bf55a5cc0eda11b7201c4ab777e69c6970c4cd`, run directory `experiments/P10IS1-pre-20261118`.
- **The analysis compared against:** the frozen analysis function applied through the disclosed corrected loader, `experiments/P10IS1-pre-20261118-analysis-supplement/analysis/analysis_supplement.json` (route (c) of `ADR-0024-addendum-analysis-loader-defect.md`). The registered `analysis` and `report` stages are ENGINEERING STOP — ANALYSIS LOADER DEFECT.
- **No sealed value was opened** for any check here.

## 1. Result

| Line | Recomputed | Study (supplement) |
|---|---|---|
| C-CAPACITY | **CAPACITY-NEGATIVE**, clause (b), carried by **F-OQ** | CAPACITY-NEGATIVE, clause (b), arms [F-OQ] |
| C-SATURATION | **SATURATION-PROPORTIONAL** (F-OQ) | the same |
| C-EFFICIENCY | **EFFICIENCY-INCONCLUSIVE** (F-OQ and T-OQ are NOT_EVALUATED in E-A and E-T) | the same |

`compare.py`: **2,652 values compared, 0 differences**.

The comparison covers:
- every per-panel capacity verdict, with Δ_MU, Δ_MC in MC-A, MC-T and MC-C (with the matched snapshots and their status), Δ_SAT and Δ_FULL;
- step classes, arm classes, arm-level dense labels;
- the dense-cell labels with their counts per reading, the dense-at-saturation labels with d_sat and lengths;
- ρ and the saturation pair and arm classes;
- the efficiency verdicts, classes and u_T bounds;
- the sparse ratios and labels;
- the R2 failures (none), the ladder stops and the three lines.

**Engineering statuses** (recomputed from the run directory, not from the study's status):
- gates passed;
- no item errors, no failed cells, no missing read (2,395 of 2,395 expected), no missing ladder decision;
- the recorded U_run of every ladder cell equals the stop rule recomputed from the data: 2K/256 196,608; 8K/1K 98,304; **32K/4K 393,216, one ladder round beyond U₀ = 196,608**. That round exercised the continuation path, which no rehearsal had run.

## 2. How it was recomputed

**The program.** `code/recompute.py` uses only the standard library and imports nothing from `studies/` or `arborlm/`. It was written from the text of ADR-0024 (§§7.2, 8.1, 8.2, 9.1–9.6, 10, 14, 23) and, where ADR-0024 defers to it, of ADR-0021 (§§7.1, 8.1, 8.2, 8.8, 8.10).

**What it reads directly:**
- every `evaluate/<label>/uXXXXXXXX.json` (the reads `main` and `ivf`, both panels);
- `baselines/d*_f*.json`;
- `ladder/<cell>.json`;
- `timing/timing.json` (MC-T);
- `gates/gates.json`, `*/item_errors/`, `train/cells/*/cell_failed.json`;
- the frozen plan, as a `git archive` of the freeze commit (SHA-256 `e1479e36…`);
- the R2 table, from the counting rehearsal record named by the freeze record (SHA-256 `87854244…`).

**Launch and comparison.** `code/run_registered.sh` checks both hashes, writes into a new directory, and compares with `compare.py`. The outputs are in `registered_output/`.

**Input taken, not recomputed: MC-A's analytic multiply-adds per update.**
- They come from the frozen formula of ADR-0021 §22 M6 (`studies/p10s1/frozen.py` at 46bf55a), run read-only by `code/make_madds_input.py` → `code/madds_per_update.json`.
- They are an input to MC-A, MC-C and E-A.
- Reproducing that formula independently would need the model's shapes; it was not done.

## 3. How the recomputation itself was tested (before any registered value existed)

- **Counting rehearsal, one replicate.** Against the study's frozen analysis run read-only from an archive with the replicate count set to 1 in memory: **0 differences of 628**.
- **18 synthetic five-replicate run directories** (`make_fuzz.py`): seeded perturbations covering DEP failures, leakage, REF failures, drift, noise, qualification drops and CPU costs per arm and per cell, which give MC-SHORT and disagreement between the measures. **0 differences in every run**, about 43,000 values (`final_regression.out`).
- **The efficiency step verdict:** 20,000 random cases against the frozen `classes.efficiency_step`, **0 differences**, all eight verdicts reached.
- **Branches these tests never reached:** `coverage_final.out` lists them. Every registered label that falls on one of them is checked by hand in §4.

## 4. Hand checks of the registered branches the tests never reached

`handcheck.py` → `handcheck_run1.out`. It computes directly from the raw records with an inline i formula and the ADR's printed chance bounds, not through `recompute.py`'s functions. Each line below states the rule and what the raw records give.

- **CAPACITY-NEGATIVE, clause (b)** of ADR-0024 §9.3 row 4.
  - Among F-OQ, T-OQ and F-OQ-IVF only **F-OQ** is CAPACITY_SUPPORTED, and its arm-level dense label is DENSE AHEAD. So "at least one is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD" holds.
  - Clause (a) fails, because F-OQ is not CAPACITY_NOT_SUPPORTED.
  - H8 is also CAPACITY_SUPPORTED, but it is not an arm of rows 3–5. KEY-LEARNING-LIMITED is absent, since F-OQ is supported.
- **Arm class row 3** (a_use ≥ 0.80 at 32K/16K at U_P in all 5, both panels).
  - F-OQ: minimum 0.907, passes. H8: minimum 0.861, passes.
  - T-OQ: minimum 0.679, fails. F-OQ-IVF: minimum 0.516, fails. Both therefore stay CAPACITY_ONE_TRANSITION, although they have a CAPACITY STEP in each transition.
- **DENSE AHEAD (NOT AT MATCHED COMPUTE)** at 32K/16K for F-OQ, T-OQ and H8.
  - Only D-BEST holds a lead of −0.25 or more: in 5 of 5 replicates (F-OQ −0.80 to −0.85; T-OQ about −2.4; H8 about −1.2).
  - MU, MC-A and MC-T are far from it: F-OQ +1.7 to +2.7; T-OQ +0.12 to +1.97; H8 +1.4 to +1.9.
  - **For F-OQ the negative therefore rests on D-OQ's best snapshot up to its run length (6·U_P), against F-OQ at U_P, and on the dense-at-saturation label. It does not rest on a matched-compute reading.** That is what the rule says (§9.2: "a lead in any one reading"), and it is stated here so that it is not read as more.
- **STORE NOT BEHIND** (F-OQ at 8K/4K; H8 at 2K/4K and 8K/16K). Every reading is above −0.25 in every replicate: F-OQ 8K/4K worst −0.16; H8 2K/4K and 8K/16K worst 0.00. So it holds.
- **DENSE AHEAD at the T-OQ, F-OQ-IVF and H8 8K/4K cells:** MU 5/5, MC-A 4 or 5, MC-T 5. These match the printed counts.
- **DENSE HOLDS MORE AT SATURATION** (every arm, both loaded cells).
  - Taking i\* of the arm up to U_run, an upper bound on its value at the arm's own full length, against i\* of D-OQ at its own length: d_sat is at most −1.67 for F-OQ and lower for the other arms, in every replicate.
  - That is far below −0.25, so the label does not depend on the reading of the arm's own full length.
- **The sparse label AHEAD.** T-OQ against F-OQ-IVF on i at U_P: the ratio is 1.63–1.68 at 8K/4K and 1.54–1.59 at 32K/16K in 5/5, against 1.03, so AHEAD. The run-length reading is in `recompute.json`.
- **Efficiency.**
  - F-OQ and T-OQ at 2K/1K and 2K/4K reach i ≥ 3.0 at their first snapshot (512), so both are left-censored. N1 is therefore NOT_ASSESSED, so the transition 1K→4K is NOT_ASSESSED, so each arm is NOT_EVALUATED, so the line is EFFICIENCY-INCONCLUSIVE.
  - T-OQ N2: both u_T are known (about 1,290 and 704 in replicate 1), neither halved nor doubled, so SAME 5/5 (NO DIFFERENCE).
  - F-OQ N2: the larger cell is left-censored, so NOT_ASSESSED.
- **C-SATURATION.** F-OQ ρ is 3.65–3.76 (256→1K) and 3.59–3.83 (1K→4K), every cell full, so PROPORTIONAL 5/5 in both pairs (SATURATION_PROPORTIONAL_ALL_PAIRS). T-OQ is SUBPROPORTIONAL in 4/5, F-OQ-IVF in 5/5.

## 5. `REPORT_SUPPLEMENT.md`

**Does it print anything the JSON does not support? No.** `report_vs_recompute.py` → `report_vs_recompute_run1.out`: **149 printed rows and labels checked against the independent recomputation, 0 differences**. That is every capacity table row (verdict, d_MU on A and B), every saturation table row (verdict, ρ), every dense-cell label with its counts, and every dense-at-saturation label.

**What it omits that the ADR asks for.** The frozen `labels.printable` adds details to positive labels only:
1. C-CAPACITY is printed bare, as **CAPACITY-NEGATIVE**. It lacks the clause (b), the carrying arm F-OQ, the reason and "1,024 TO 16,384 SLOTS", which §9.3 requires. The JSON holds all of them.
2. C-EFFICIENCY is printed bare. It lacks the reason that §9.5 row 5 requires (JSON: "E-A: F-OQ: NOT_EVALUATED, T-OQ: NOT_EVALUATED"; the same for E-T) and "SIZES 1,024–16,384" (ADR-0021 §8.8).
3. The capacity-step dense labels are printed with their counts per reading. They are not printed with the d values per reading, or with D-OQ's a_use, which §9.2 requires ("every dense label is printed for every cell with all four readings and D-OQ's a_use"). D-OQ's a_use is printed only at the saturation cells.
4. The throughput section prints the state MEASURED and no figures (they are in `throughput/throughput.json`).
5. The separability figures that ADR-0021 §8.10 asks to be printed beside every ρ are not printed.
6. The §10 table ("labels that cannot be reached without measured CPU cost") is printed with every report by design, although **MC-T was measured** (`mct_measured: true`). A reader must not take it to mean that MC-T was missing.
7. The caps line shows evaluate 1.0 h; the effective cap was 2.0 h (the extension).

Items 1–7 must be carried in the outcome record. The report is frozen.

## 6. Ledger and stage manifests

**The ledger** (`experiments/P10IS1-ledger.json`, 14 entries) and its pre-image (9 entries, kept as a prefix): the extension entries are present (evaluate −3,600 s; `evaluate-cap-extension-offset` +3,600 s; approval hash `9cc1615c…`).

| Stage | Ledger sum (s) | True charged (s) | Manifest (last invocation only, s) |
|---|---|---|---|
| pre-freeze H_c | 28,679.4 | 28,679.4 (7.966 h) | — |
| gates | 36.6 | 36.6 | 36.6 |
| timing | 198.5 | 198.5 | 198.5 |
| train | 16,534.4 | 16,534.4 | 16,534.4 |
| ladder | 7,049.6 | 7,049.6 | 7,049.6 |
| **evaluate** | **125.7** (3,600.03 − 3,600 + 125.67) | **3,725.7 (1.035 h)** | **125.7** |
| baselines | 26.4 | 26.4 (0.01 + 26.42) | 26.4 |
| analysis (crashed) | 0.37 | 0.37 | — (no manifest) |
| report (crashed) | 0.0 | 0.0 | — |
| throughput | 181.3 | 181.3 (1,200 s waited, not charged) | 181.3 |
| evaluate-cap-extension-offset | 3,600.0 | 0 (never ran) | — |
| **Total** | **56,432.4 s = 15.676 h** | **15.676 h** (the credit and offset cancel) | |

- **Total against the cap:** 15.676 h of the 52 h total cap, headroom 36.32 h. The registered stages took 7.71 h (15.676 − 7.966).
- **Evaluate:** 1.035 h, over the frozen 1.0 h and within the approved 2.0 h on the `evaluate` key (evaluate + baselines = 1.042 h).
- **Correction required (a false statement in two committed texts).** `ADR-0024-addendum-evaluate-cap-extension.md` §3 and `OWED_DISCLOSURES.md` item 3 say evaluate's true charged time is "the sum of the stage manifests' `charged_seconds` (one per invocation)", "equivalently" the ledger without the two EXTENSION entries.
  - **The first half is wrong.** `execute_stage` overwrites `run_dir/<stage>/manifest.json` at each invocation, so the evaluate manifest holds only the second invocation (125.7 s).
  - It happens to equal the ledger's credited `evaluate` sum. **Both figures would make a reader believe evaluate took 125.7 s.**
  - The true figure is the ledger's `evaluate` entries **without the credit**: 3,600.03 + 125.67 = **3,725.7 s**.
  - Both texts should say so. The outcome record should give 3,725.7 s.

## 7. What remains unverified

- MC-A's analytic multiply-adds per update: an input (§2).
- Branches of the rules that neither the tests nor this run reached (`coverage_final.out`). They do not occur in the registered result, so they cannot affect it.
- The model's evaluation itself: the records' `useful` and `correct` counts are taken as recorded. Their production by the frozen evaluation code is not recomputed here.
- H8's annotations, the counted-work table and the throughput figures: printed only, not recomputed.

## 8. My own errors and misses, in order

1. **Arm's full length.** In the first rehearsal comparison I restricted an arm's own full length at a ladder cell to points at or above U₀. ADR-0024 §7.2 item 6 sets no lower bound. Corrected: 20 differences, then 0.
2. **Ruling 1 omitted.** In the cost-perturbed synthetic runs, I had omitted ruling 1 (U_MC = U_P where the larger cell is not costlier). Corrected: 80–150 differences per seed, then 0.
3. **u_T representation.** My first u_T marked a DEP-failing first hit differently. I adopted the frozen reading, which cannot favour the store. The dense-speed panel combination was then ruled by the lead: the frozen reading is registered, and differences of interpretation are disclosures only. No dense-speed label occurs in this result.
4. **The loader defect.** While building this recomputation, my own loader crashed on `baselines/manifest.json` of the counting rehearsal. I patched my loader and **did not see that the study's `build_registry` globs the same directory**. The registered analysis stage then crashed on it. I should have reported it then.
5. **Python version, twice in later checks.** I ran a check under the system Python 3.9 (no `tomllib`, no `datetime.UTC`). Each failed attempt is kept beside its rerun.

## Files in this folder

- `code/`: `recompute.py`, `compare.py`, `run_registered.sh`, `make_madds_input.py`, `madds_per_update.json`, `NOTE.md`
- `registered_output/`: `recompute.json`, `compare.out`, `recompute.log` (from `registered_20261121T173414Z`)
- `tests_of_the_recomputation/`: the harness, the synthetic generator, the coverage tally and their outputs
- `handcheck.py` and `handcheck_run1.out`; `report_vs_recompute.py` and `report_vs_recompute_run1.out`
- `SHA256SUMS.txt`

`Astra review: NOT_PERFORMED`
