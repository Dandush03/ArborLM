# P10-S1 attempt 2 — independent recomputation of the registered result

Auditor: Opus 5.5 (arbor-auditor role, as delegated by the lead). Read-only on the repo and the run directory. This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`.

## 0. Scope, inputs, environment, commands

- Spec: `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` at freeze commit `76334ba6697b40f50aad8abb196628f4fd4cb739`. sha256 of the file is `204bafe8…daf3`, identical at the freeze commit and at `cbde677`.
- Run: `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117`. Attempt 1's directory was not opened.
- Registered outputs that were compared, not trusted: `analysis.json` (sha256 `f270c1ce…9907`) and `results/RESULTS.md` (sha256 `b4025dd4…d94d`).
- Frozen inputs used as given: `studies/p10s1/freeze/plan.json` (sha256 `01b6a1eb…50ca`, the same at the freeze commit). From it I took U_P per row (8192/8192/16384), U_L (393216, 786432), and the two cost tables. I re-derived all 24 MC entries from those cost tables using the §5.4 text; all 24 match the frozen entries.
- My code: plain `python3` (Python 3.15.1, /opt/homebrew/bin/python3), stdlib only. It imports nothing from `arborlm` or `studies`. Each verdict function was written from the ADR section cited beside it. The chance interval is my own exact binomial (tail 0.001/40/2 per side). It gives [34,100], [192,325] and [894,1159], as G2 states.
- Commands (cwd = this folder): `python3 a1_integrity.py`, `python3 a2_capacity.py`, `python3 a3_lines.py`, `python3 a4_dep_sensitivity.py`, `python3 a5_seedblock.py`, `python3 a5b_seedblock_bug.py`, `python3 a6_compare.py`, `python3 a7_margins.py`. Each `.out` file holds that script's full output.
- Implementer code was used once, read-only, through `uv run --locked python` in the worktree. It did two things: print `core.code_identity()` at HEAD `cbde677`, and print `stages.timing_items(plan)` to confirm the throughput defect. It produced no verdict.
- Machine: Darwin 27.2.0 arm64. Date 2026-11-17 UTC.
- **HEAD moved during the audit.** It went from `cbde677` to `7007caf`: commit `6470f1e` added ADR §25.21, `studies/p10s1/throughput_supplement.py` and a test, then main was merged. None of these commits touch the run directory or any file that existing `studies/p10s1/` code reads for analysis. Nothing in the run directory is newer than `report/manifest.json`.

## 1. Verdict table

| Item | Registered | Recomputed | Status |
|---|---|---|---|
| Stage manifests | train 178/178, evaluate 193/193, simulate 21/21, analyze 1/1, report 1/1 COMPLETE; timing INCOMPLETE (1 failed) | same | REPRODUCED |
| Identity | every manifest, train.json and eval.json equals the freeze identity; data manifests equal the freeze hashes; G1–G9 passed | same (0 problems over 178 cells) | REPRODUCED |
| Status COMPLETE; 185 read, 0 missing, 0 failed | as stated | 178 cell directories (150 P + 28 SB). "185" counts 150 P cells plus 35 F-OQ-IVF reads; the seed-block cells are excluded from the count | REPRODUCED WITH NOTE (D6) |
| Throughput failure diagnosis | StopIteration because F-OQ 2K/256 has no registered cell | Confirmed: `timing_items` forces `sat256=True` (stages.py:697), so its first F-OQ item is (2048,256), and stages.py:778 `next(...)` finds no cell. The quiet check had passed on its first attempt (1.37 s, no 120 s retry pause) | REPRODUCED (D5) |
| Outcomes independent of the timing stage | asserted | stages.py:833 counts only train/evaluate failures. The throughput record is optional (None), and no class reads it | REPRODUCED |
| Capacity line | CAPACITY-INCONCLUSIVE (F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE) | same; all 80 replicate verdicts, 16 step classes and 4 arm classes identical | REPRODUCED WITH NOTE (D7, D8) |
| H8 | CAPACITY_ONE_TRANSITION, UNDERTRAINED-AT-U_P | same (C2 is a CAPACITY STEP) | REPRODUCED WITH NOTE (D8, D10) |
| Saturation line | SATURATION-INCONCLUSIVE (F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED) | same; every rho identical | REPRODUCED WITH NOTE (D2, D9) |
| Efficiency line | EFFICIENCY-NEGATIVE (DENSE FASTER): F-OQ NO DIFFERENCE ×2; T-OQ FASTER STEP ×2 | same | REPRODUCED WITH NOTE (D4) |
| Hierarchy | TREE_BEHIND | same | REPRODUCED |
| DICT DOMINATES; conventional not sufficient | as stated | same (DICT accuracy 1.0; KNN-W i ≤ 0.08 bits) | REPRODUCED |
| Dense (capacity line) | F-OQ DENSE AHEAD, H8 DENSE AHEAD, F-OQ-IVF/T-OQ DENSE NOT READ | same | REPRODUCED WITH NOTE (D3) |
| Dense at saturation | DENSE HOLDS MORE for F-OQ, F-OQ-IVF, T-OQ | same, 5/5 replicates at both loaded cells (H8 also) | REPRODUCED |
| Seed block (descriptive) | "init seed dominates" in 28/28 entries | **wrong**: the extra seeds were read as F-OQ-IVF | NOT REPRODUCED (D1) |

`a6_compare.py`: 1,085 item-by-item comparisons against `analysis.json` (labels, verdicts, Δ values, rho, u_T), with 0 differences.

## 2. Capacity line: every DEPENDENCE_FAILED replicate

The rule: §8.1 DEP applies per memory cell with a_use ≥ 0.25. It requires that memory disabled gives chance, that value shuffle gives chance, and that a_use ≥ 0.95 × raw accuracy. §8.2 row 2 applies it at the snapshots a verdict reads, and ruling §22 (g) widens that to **every snapshot up to the run length**. §8.3 row 2: a step class is DEPENDENCE_FAILED if at least 2 replicates are. §8.4 row 2: an arm is DEPENDENCE_FAILED if any of its steps is.

Every failure in the run comes from the 0.95 × raw condition. The disabled and shuffled ablations were inside the chance interval at every snapshot, and there is no LEAKAGE anywhere. Every failure falls at an early snapshot (U_P/16 to U_P/4) where a_use is just above the 0.25 floor.

| Arm / step / rep | Cell, update, panel | useful / correct (n) | a_use | useful/correct (threshold 0.95) |
|---|---|---|---|---|
| F-OQ N2 r2 | 8K/16K, 2048, A / B | 2646/2803, 2700/2851 (8192) | 0.323 / 0.330 | 0.9440 / 0.9470 |
| F-OQ N2 r4 (also C1 r4) | 8K/4K, 2048, A / B | 2356/2493, 2387/2524 | 0.288 / 0.291 | 0.9450 / 0.9457 |
| F-OQ N1 r3 | 2K/4K, 1024, A / B | 643/680, 620/659 (2048) | 0.314 / 0.303 | 0.9456 / 0.9408 |
| F-OQ-IVF N2 r2 | 8K/16K, 2048, A / B | 2173/2295, 2177/2306 | 0.265 / 0.266 | 0.9468 / 0.9441 |
| F-OQ-IVF N2 r5 | 8K/16K, 2048, A / B | 2130/2260, 2095/2212 | 0.260 / 0.256 | 0.9425 / 0.9471 |
| F-OQ-IVF N1 r3 | 2K/4K, 1024, A / B | 546/582, 549/581 | 0.267 / 0.268 | 0.9381 / 0.9449 |
| F-OQ-IVF N1 r4 (A only → PANEL-DISAGREE) | 2K/4K, 1024, A | 847/893 | 0.414 | 0.9485 |
| H8 C1 r4, N2 r4 | 8K/4K, 2048, A / B | 2119/2239, 2122/2237 | 0.259 / 0.259 | 0.9464 / 0.9486 |
| H8 C1 r4 (also) | 8K/16K? no: 8K/4K small of N2 is 8K/4K; C1's large is 8K/4K | — | — | — |
| H8 N2 r4 (also) | 8K/16K, 1024, A / B | 2195/2355, 2170/2343 | 0.268 / 0.265 | 0.9321 / 0.9262 |
| H8 N1 r1, r3 (B only → PANEL-DISAGREE) | 2K/4K, 1024, B | 532/570; 735/778 | 0.260; 0.359 | 0.9333; 0.9447 |
| T-OQ N1 r3 (A only → PANEL-DISAGREE) | 2K/1K, 2048, A | 552/586 | 0.270 | 0.9420 |

(The table row marked "8K/16K? no" is my own drafting slip, kept per policy: H8 C1 r4 fails through 8K/4K at 2048, which is C1's larger cell. That is the row above it.)

- **F-OQ → DEPENDENCE_FAILED.** Step N2 has 2 DEPENDENCE_FAILED replicates (r2, r4), so its class is DEPENDENCE_FAILED by §8.3 row 2, and the arm is DEPENDENCE_FAILED by §8.4 row 2. C1 has only 1 such replicate (MIXED) and N1 has only 1 (NOT LOADED), so neither causes it. **The ADR rule as registered (§8.2 row 2 with ruling 22 (g)) makes the arm DEPENDENCE_FAILED.**
- **F-OQ-IVF → DEPENDENCE_FAILED.** N2 has r2 and r5. Same rules.
- F-OQ C2 is a CAPACITY STEP in 5/5: Δ_MU 3.11–3.18, Δ_MC 2.53–2.63, Δ_SAT 1.85–2.04, smaller cell 32K/4K loaded (i* 2.24–2.27, last-doubling gain 0.016–0.061), a_use(32K/16K; U_P) 0.909–0.932.

**Pattern (PENDING LEAD REVIEW).**
- R2 also "fails" this condition 12 times at 512–1024 updates. R2 is the one-slot-per-fact reference, whose dependence on memory holds by construction; no rule reads R2's DEP.
- Across 2,289 DEP evaluations on memory cells: 19/197 fail in a_use [0.25, 0.30), 10/277 in [0.30, 0.35), 2/86 in [0.35, 0.40), and 1/59 in [0.40, 0.45). No failure occurs above a_use 0.414.
- correct − useful (for example 157 for F-OQ N2 r2 A) is at or below what the memory-disabled backbone alone gets right on the same number of non-retained facts ((n − useful) × 229/8192 = 173).
- Reading: near the 0.25 floor, the 0.95 ratio is barely reachable even when every non-chance correct answer depends on the read.

**Sensitivity (`a4_dep_sensitivity.out`; descriptive, not a re-analysis).** Two alternative readings change F-OQ's arm class to CAPACITY_SUPPORTED (C1 and C2 CAPACITY STEPs; a_use at 32K/16K is ≥ 0.909 against the 0.80 floor):
- DEP read only at the snapshots whose values enter the verdict (the literal §8.2 row 2 before ruling (g));
- DEP not read at all.

F-OQ is DENSE AHEAD and DENSE HOLDS MORE AT SATURATION. Under either reading the capacity outcome would therefore be **CAPACITY-NEGATIVE (b)**, not INCONCLUSIVE. The registered INCONCLUSIVE rests entirely on four early snapshots in F-OQ N2 (two cells × two panels at 2048 updates). It is the registered result under ruling 22 (g). The human lead should know that it is the more favourable label for the store.

## 3. Efficiency line (§8.8)

**F-OQ: NO DIFFERENCE at both steps.**

| Step | u_T(4N)/u_T(N) | c_T ratio, cpu | c_T ratio, madds | Rule needs | Verdict |
|---|---|---|---|---|---|
| N1 | 0.556–0.642 | 0.94–1.08 | 0.67–0.78 | updates ≤ 0.5 | SAME ×5 |
| N2 | 0.534–0.570 | 0.71–0.75 | 0.91–0.97 | updates ≤ 0.5 | SAME ×5 |

Arm class: EFFICIENCY_NOT_SUPPORTED.

**T-OQ: FASTER STEP at both steps.**

| Step | u_T(4N)/u_T(N) | c_T ratio | Verdicts |
|---|---|---|---|
| N1 | 0.31–0.48 | ≤ 0.51 | FASTER ×5 |
| N2 | 0.12–0.19 | ≤ 0.23 | FASTER ×3; REACHED ONLY BY THE LARGER ×2 (r2, r3: 8K/4K right-censored above 49,152) |

Arm class: EFFICIENCY_SUPPORTED.

**DENSE FASTER for T-OQ.**
- At N1's larger cell (2K/4K), D-OQ (rate 0.1) qualifies at the first snapshot, 512 updates (left-censored). c_T(D-OQ)/c_T(T-OQ) ≤ 0.083–0.118 (cpu) and 0.32–0.46 (madds) → **5/5**.
- At N2's larger cell (8K/16K), D-OQ's u_T is 1,608–1,681. The cpu ratio is 0.27–0.38 but the madds ratio is 1.32–1.87 → **0/5**.

The arm is labelled DENSE FASTER because one cell qualifies (analysis.py:631). The outcome is EFFICIENCY-NEGATIVE (second clause of row 4). See D4.

## 4. Saturation line (§8.10), pair 1,024 → 4,096 (8K/1K at U_L 393,216 → 32K/4K at U_L 786,432)

| Arm | rho A (r1…r5) | b(N) bits/slot (A) | Verdicts | Pair class |
|---|---|---|---|---|
| F-OQ | 3.785, 3.847, 3.816, 3.875, 3.821 | 18.7–19.2 → 17.9–18.1 | PROPORTIONAL ×5 | PROPORTIONAL STEP; arm INTERMEDIATE because 256→1,024 is fixed NOT FULL (2K/256 not run; §10.1 0b, §25.12 item 6) |
| F-OQ-IVF | 1.419, 1.419, 1.457, 1.499, 1.432 | 11.8–12.5 → 4.34–4.43 | SUBPROPORTIONAL ×5 | SUBPROPORTIONAL STEP → SATURATION_DOES_NOT_SCALE |
| H8 | 4.131, 3.998, 4.073, 4.095, 3.953 | 6.46–6.70 → 6.60–6.67 | PROPORTIONAL ×5 | PROPORTIONAL ALL PAIRS (H8 cannot give the positive) |
| T-OQ | 2.922, 2.649, 2.541, 2.389, 2.664 | 8.4–9.9 → 5.6–6.2 | NOT FULL (r1, r5); SUBPROPORTIONAL (r2–r4) | NOT FULL (≥ 2) → SATURATION_NOT_MEASURED |

**Why T-OQ lists only r2–r4.** At 8K/1K, T-OQ r1 is not plateaued on Panel A: its last-doubling gain is 0.1059 > 0.10. Panel B is 0.088. T-OQ r5 is not plateaued on either panel (0.132 / 0.129). The report prints a replicate only when rho was computed (report.py:140), so NOT FULL replicates are silently omitted (D2). Every T-OQ rho, including the two not-full replicates, is below 3.0.

Outcome: neither F-OQ, T-OQ nor F-OQ-IVF is ALL_PAIRS. F-OQ and T-OQ are not both DOES_NOT_SCALE, and not both NOT_MEASURED → SATURATION-INCONCLUSIVE. This is unaffected by the T-OQ r1 knife-edge: if r1 were full, T-OQ would be DOES_NOT_SCALE, F-OQ would still be INTERMEDIATE, and the outcome would still be INCONCLUSIVE.

## 5. Dense, hierarchy, conventional

**Dense (capacity line), F-OQ at C2's larger cell 32K/16K.**
- MU d = −0.384, −0.450, −0.402, **−0.238**, −0.334 (4/5 ≤ −0.25).
- MC (F-OQ at 49,152 vs D-OQ at 16,384) d = **+0.24 to +0.33** (0/5).
- D-BEST d = −0.68 to −0.87 (5/5).
- D-OQ a_use at U_P is 0.950–0.960.
- Result: DENSE AHEAD (MU and D-BEST).

**Dense (capacity line), H8 at 32K/16K.** MU −1.03 to −1.24, MC −0.60 to −0.68, D-BEST −1.47 to −1.66. DENSE AHEAD.

**Dense at saturation, d_sat = i\*(arm; U_L) − i\*(D-OQ; U_L), 5/5 at both cells for every arm.**

| Arm | 8K/1K | 32K/4K |
|---|---|---|
| F-OQ | −1.79 to −1.87 | −1.76 to −1.81 |
| F-OQ-IVF | −2.62 to −2.69 | −3.47 to −3.52 |
| T-OQ | −2.92 to −3.15 | −3.25 to −3.35 |

D-OQ i\* is 4.16–4.20 at 8K/1K and 4.02–4.07 at 32K/4K, against F-OQ's 2.33–2.39 and 2.24–2.27.

**Hierarchy.** T-OQ/F-OQ-IVF I_use is 0.51–0.74 at 8K/4K and 0.65–0.90 at 32K/16K → TREE_BEHIND. Against exhaustive F-OQ the ratio is 0.25–0.39 and 0.23–0.32.

**Conventional.** KNN-W i at 32K/16K is 0.067–0.079 and KNN-W-IVF 0.051–0.066, against the arms' 0.93–4.30 → not sufficient. DICT is correct on 32768/32768.

## 6. Task 4 — a_use

Mean over 5 replicates of (A+B)/2, with the range over replicates and panels. U_run is 6·U_P, U_L at the loaded cells, U_P for R2.

| Arm | Cell | U_P | a_use @ U_P | U_run | a_use @ U_run |
|---|---|---|---|---|---|
| F-OQ | 2K/1K | 8192 | 0.991 (0.988–0.993) | 49152 | 0.999 |
| F-OQ | 2K/4K | 8192 | 1.000 | 49152 | 1.000 |
| F-OQ | 8K/1K | 8192 | 0.390 (0.362–0.429) | 393216 | 0.654 (0.650–0.661) |
| F-OQ | 8K/4K | 8192 | 0.948 (0.937–0.965) | 49152 | 0.996 |
| F-OQ | 8K/16K | 8192 | 0.999 | 49152 | 1.000 |
| F-OQ | 32K/4K | 16384 | 0.392 (0.374–0.429) | 786432 | 0.637 (0.634–0.639) |
| F-OQ | 32K/16K | 16384 | 0.916 (0.909–0.932) | 98304 | 0.992 |
| F-OQ-IVF | 2K/1K | 8192 | 0.916 | 49152 | 0.927 |
| F-OQ-IVF | 2K/4K | 8192 | 0.953 | 49152 | 0.960 |
| F-OQ-IVF | 8K/1K | 8192 | 0.306 | 393216 | 0.497 |
| F-OQ-IVF | 8K/4K | 8192 | 0.631 | 49152 | 0.706 |
| F-OQ-IVF | 8K/16K | 8192 | 0.911 | 49152 | 0.919 |
| F-OQ-IVF | 32K/4K | 16384 | 0.201 | 786432 | 0.270 |
| F-OQ-IVF | 32K/16K | 16384 | 0.483 | 98304 | 0.540 |
| T-OQ | 2K/1K | 8192 | 0.787 (0.738–0.862) | 49152 | 0.931 (0.886–0.960) |
| T-OQ | 2K/4K | 8192 | 0.989 | 49152 | 1.000 |
| T-OQ | 8K/1K | 8192 | 0.176 (0.147–0.226) | 393216 | 0.416 (0.399–0.441) |
| T-OQ | 8K/4K | 8192 | 0.469 (0.408–0.554) | 49152 | 0.769 (0.721–0.811) |
| T-OQ | 8K/16K | 8192 | 0.920 | 49152 | 0.996 |
| T-OQ | 32K/4K | 16384 | 0.151 (0.135–0.183) | 786432 | 0.323 (0.312–0.332) |
| T-OQ | 32K/16K | 16384 | 0.401 (0.370–0.472) | 98304 | 0.697 (0.679–0.737) |
| H8 | 2K/1K | 8192 | 0.828 | 49152 | 0.879 |
| H8 | 2K/4K | 8192 | 1.000 | 49152 | 1.000 |
| H8 | 8K/1K | 8192 | 0.209 | 393216 | 0.344 |
| H8 | 8K/4K | 8192 | 0.770 | 49152 | 0.879 |
| H8 | 8K/16K | 8192 | 1.000 | 49152 | 1.000 |
| H8 | 32K/4K | 16384 | 0.243 | 786432 | 0.346 |
| H8 | 32K/16K | 16384 | 0.812 (0.804–0.831) | 98304 | 0.879 |
| D-OQ (lr 0.1) | 2K/4K | 8192 | 1.000 | 49152 | 1.000 |
| D-OQ (lr 0.03) | 8K/1K | 8192 | 0.770 (0.749–0.781) | 393216 | 0.918 (0.913–0.920) |
| D-OQ (lr 0.1) | 8K/4K | 8192 | 0.996 | 49152 | 1.000 |
| D-OQ (lr 0.03) | 8K/16K | 8192 | 0.999 | 49152 | 1.000 |
| D-OQ (lr 0.03) | 32K/4K | 16384 | 0.576 (0.564–0.591) | 786432 | 0.901 (0.898–0.904) |
| D-OQ (lr 0.03) | 32K/16K | 16384 | 0.957 (0.950–0.960) | 98304 | 0.999 |
| R2 | 2K/4K, 8K/16K, 32K/32K | 8192/8192/16384 | 1.000 in every replicate and panel | = U_P | — |

Memory arms use rate 0.003, untuned by design (§10.1 item 3). D-OQ's rates were calibrated. D-OQ has the same parameter count as F-OQ (G8).

## 7. Discrepancies and notes

- **D1 (defect, descriptive section wrong).** analysis.py:167-169 stores both reads of a seed-block F-OQ cell under the same key `(draw, init, facts, slots)`, so the F-OQ-IVF read overwrites the F-OQ read. analysis.py:570-577 then compares the main F-OQ cell with the IVF reads of the extra seeds.
  - Effect: all 28 seed-block lines in RESULTS.md (lines 110-137) are wrong.
  - Example: 32K/16K U_run is reported as a spread of 3.172 bits; the correct F-OQ spread is 0.0025. "Init seed dominates" is printed 28/28; the correct comparison gives data draw in 24/28.
  - The section is descriptive and enters no rule. `a5b_seedblock_bug.out` matches all 28 reported numbers to this hypothesis exactly.
- **D2 (report omits records required by §8.10).** report.py:140 prints a saturation replicate only if rho exists. This drops NOT FULL replicates (T-OQ r1, r5), and it prints b(N) and gains for Panel A only. §8.10 says "b(N) is printed for every arm, size, replicate and panel, with the last doubling's gain and whether the cell is full".
- **D3 (report omits records required by §8.5).** "Every dense label is printed with D-OQ's a_use at each such cell in each reading" is not met: RESULTS.md shows only "DENSE AHEAD".
  - The reading-level picture is absent: for F-OQ, the matched-compute reading favours F-OQ in 5/5 (+0.24 to +0.33 bits), and DENSE AHEAD comes from MU (4/5, r4 at −0.238) and D-BEST.
  - The label is correct by the rule. The report reads less favourably for the store than the full records.
- **D4 (unlisted reading that decides the efficiency outcome; PENDING LEAD REVIEW).** §8.8 defines DENSE FASTER "at the larger cell of each FASTER STEP" and does not say how two cells combine. The code takes "any cell" (analysis.py:631); this is not in `READINGS`.
  - T-OQ is DENSE FASTER only at 2K/4K (5/5) and not at 8K/16K (0/5).
  - Under an "every cell" reading, the efficiency outcome would be EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED] for T-OQ.
  - "Any cell" matches how §8.5 treats DENSE AHEAD and is the conservative reading. RESULTS.md does not show the per-cell split.
- **D5 (engineering).** The throughput defect is confirmed as the lead diagnosed it (stages.py:695-702, 778). The machine was quiet: the stage passed the load check on its first try (§25.21 says 0.98).
  - At the time of review, RESULTS.md says nothing about the failed stage and has no throughput column in the cost table (§7.6). ADR §25.21, committed during this audit, now records it.
  - Status COMPLETE agrees with §7.5 and §8.7 row 2, which tie incompleteness to cells, not to the throughput stage.
- **D6 (labelling).** "Cells read: 185" counts F-OQ-IVF reads (150 + 35) and leaves out the 28 seed-block cells; the registry has 178 cells (analysis.py:739).
- **D7 (scientific; PENDING LEAD REVIEW).** The DEPENDENCE_FAILED classes come only from the 0.95 × raw condition at a_use 0.256–0.414, at U_P/16 to U_P/4, in early learning. The same thing happens to R2. Under the literal §8.2 row 2 reading or with no DEP, the capacity outcome would be CAPACITY-NEGATIVE (b) (§2). The registered rule (ruling 22 (g)) is applied correctly.
- **D8 (reading).** DEP is judged per panel, so a failure on one panel gives PANEL-DISAGREE. If a cell failed DEP whenever either panel fails, H8 N1 (r1, r3) would be DEPENDENCE_FAILED and H8's arm class would be DEPENDENCE_FAILED, not CAPACITY_ONE_TRANSITION. This does not change any outcome.
- **D9 (reads more favourably than records).** T-OQ SATURATION_NOT_MEASURED hides that rho < 3.0 in all 5 replicates (2.39–2.92). The registered rule is applied correctly; the label is not wrong.
- **D10 (minor).** H8's arm-class cell in RESULTS.md prints UNDERTRAINED-AT-U_P but not "H8 NOT CALIBRATED AT 2K/1K / 8K/1K / 32K/4K" (§8.4). Those appear only in the separate annotations bullet.
- **D11 (minor, frozen record).** plan.json `headroom.cap_seconds` = 194,400 (54 h = C_max), while `cap_seconds` = 190,800 and `cap_hours` = 53. The stage manifests use 190,800.
- **D12 (minor).** The RESULTS.md "Isolated timing" section is the rehearsal's record, with a pre-freeze identity, and is not labelled as such.

**My own failed attempts, kept.**
- One inspection command failed with a zsh error (`(eval):1: == not found`) from an unquoted `echo ==`. I re-ran it without the echo; there was no other effect.
- In §2's table I drafted a wrong row (marked "8K/16K? no"). It is kept and corrected in the parenthesis below the table.
