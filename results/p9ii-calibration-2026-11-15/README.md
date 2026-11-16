# P9-II calibration (ADR-0019 §6) — 2026-11-15 UTC

- **What ran:** 22 cells at 4,096 slots / 2,048 facts, U = 8,192 updates, on the two calibration draws (rehearsal seed sets 3 and 4), one initialization seed: each tunable arm at both values of its grid (16 cells) and A0, A6, A7 as a pipeline check (6 cells). Code at commit `3d779e1`. Run directory `experiments/P9IIC-20261115T071159540788Z-1a93c3ded92e40628c2abb9bd4235188`. Charged 323 s to Budget A.
- **Status:** the lead's reading; not yet audited. **These are calibration numbers on calibration draws, not results.** Nothing else may change after calibration. Astra review: NOT_PERFORMED.

## Rule

Per arm, the value with the higher minimum Panel A accuracy over the two draws; a tie or a difference below 0.02 goes to the earlier median time to first success, then to the first value listed.

## Numbers

| Arm | Setting | Minimum accuracy over the two draws | Median update of first success | Selected |
|---|---|---|---|---|
| A1 address supervision kept | λ = 0.1 | 0.996 | 2,752 | |
| | λ = 1.0 | 0.996 | 2,688 | **1.0** (tie; earlier first success) |
| A2 address pretraining, then answers | U_pre = 1,024 | 0.037 | never | |
| | U_pre = 2,048 | 0.124 | never | **2,048** |
| A4 top-k curriculum | k_0 = N/8 | 0.521 | never | **N/8** |
| | k_0 = N | 0.123 | never | |
| A5-D diversity penalty | μ = 0.1 | 1.000 | 2,752 | |
| | μ = 1.0 | 0.999 | 2,464 | **1.0** (tie; earlier first success) |

Pipeline check (Panel A accuracy; draw 3, draw 4): A0 answer-only 0.397, 0.964; A6 oracle query 1.000, 1.000; A7 dense window 0.997, 0.999. A5-C (centring) has nothing to tune and was not run.

## What it means and does not mean

- The rule selected one value per arm. It did not, and could not, make an arm work: on these two draws A2 is near chance at both settings and A4 reaches at most about half.
- The answer-only baseline differs strongly between the two draws (0.40 against 0.96), the draw sensitivity P9-I's review described. Two draws say nothing about how often.
- A1 and A5-D reach the oracle reference on both calibration draws. Whether they are reliable is what the registered stages on eight new draws test.
- The dense window control is at 0.997–0.999 at this size, so BEATS DENSE is unreachable at 4,096 (it needs the dense arm below 0.909) and the printed comparison there will be DENSE SUFFICES or DENSE AT CEILING.
