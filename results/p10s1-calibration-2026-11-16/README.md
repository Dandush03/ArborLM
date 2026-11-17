# P10-S1 calibration (ADR-0021 revision 5, §10.1 and §25.15) — 2026-11-16

- **Status:** the lead's (Claude Fable 5.2) reading of the calibration record. **Not independently recomputed at the time of writing.** Calibration draws only (`p10s1-cal-1`, `-2`; initialization seeds 2191 and 2193); no registered seed. Calibration accuracies are calibration, never results. No rehearsal, freeze or registered run exists. Astra review: NOT_PERFORMED.
- **Run directory:** `experiments/P10S1C5c-calibration-20261116` (git-ignored). **Outcome: no return to the human lead is open.** Charged 19,059 s (5.29 h) in all.
- **The ceiling of the load search was raised once after calibration data was seen**, on the human lead's direction (ADR-0021 §25.15: "Extend search once"). Every statement of S1's capacity result carries this.

## Stages

| Stage | Code commit | Runs | Charged | Result |
|---|---|---|---|---|
| timing preview | `b4c8263` | 1 | 376 s | MEASURED on the third load reading (1.14, 1.15, 0.99; limit 1.0) |
| `calibrate-load-row-up` (first search) | `b4c8263` | 22 | 6,688 s | both loaded cells NOT LOADED WITHIN ITS CEILING: returned to the human lead |
| `calibrate-load-ext` (the one extension) | `6f7b1d8` | 8 | 9,793 s (cap 16,004 s) | both loaded cells loaded |
| `calibrate-h8-dense` | `6f7b1d8` | 48 | 2,202 s | no return |

The extension changed the configuration (two candidates added), so the identity hashes of the later stages differ from the first search's; the first search's record is kept as written (`calibration_items_load_row_up.json`, sha256 in `calibration.json` as `first_items_record_sha256`).

Two earlier previews recorded NOT MEASURED because the machine was not quiet, and are kept in `unmeasured_previews/`: `P10S1C5` (load 3.68, 6.53, 2.48, 1.97) and `P10S1C5b` (1.71, 1.45, 1.59, 1.16); about 361 s charged each.

## Load search (F-OQ decides; i* in bits per fact; limit on the gain over the last doubling 0.10; two consecutive passing candidates on all four views)

| Cell | First search (ceiling) | Extension | U_L | F-OQ gain at U_L (four views) | F-OQ i* at U_L | T-OQ U_L, i* at the cell's U_L |
|---|---|---|---|---|---|---|
| 8K/1K | passes at 131,072 and 262,144 only: no U_L | passes at 262,144 and 393,216 | **393,216** | 0.007, 0.026, 0.026, 0.031 | 2.34–2.35 | 393,216; 1.00–1.21 |
| 32K/4K | passes at 262,144 and 524,288 only: no U_L | passes at 524,288 and 786,432 | **786,432** | 0.009, 0.020, 0.031, 0.037 | 2.25–2.28 | 262,144; 0.61–0.74 |

The extension's runs equal the first search's at every shared snapshot (maximum absolute difference 0.0). Cell status: BOTH ARMS in both cells; T-OQ is not predicted not loaded anywhere.

- **2K/256:** `256 NOT MEASURED — NOT FULL WITHIN CEILING` (its own fixed rule; not rerun, no return). The cell is not run; the registry is 30 configurations and 150 cells, and the pair 256 → 1,024 is NOT FULL.
- **U_P per row:** 8,192 (2,048 facts), 8,192 (8,192 facts), 16,384 (32,768 facts).

## H8 and the dense control

- **H8:** calibrated at 2K/4K, 8K/4K, 8K/16K, 32K/16K. UNDERTRAINED-AT-U_P at 8K/4K (minimum a_use 0.751) and 32K/16K (0.801). NOT CALIBRATED at 2K/1K, 8K/1K and 32K/4K.
- **Dense learning rate (a_use at the selection readout for 0.001 / 0.003 / 0.01 / 0.03 / 0.1):**

| Unit | Chosen | Readout a_use | How |
|---|---|---|---|
| 8K/1K | 0.03 | 0.444 / 0.804 / 0.851 / 0.895 / 0.858 | highest at the readout |
| 32K/4K | 0.03 | 0.133 / 0.416 / 0.582 / 0.783 / 0.746 | highest at the readout |
| 4,096 | 0.1 | 0.071 / 0.317 / 0.975 / 0.997 / 0.994 | EDGE BY TIE-WALK: 0.03 and 0.1 within 0.02 at the readout; 0.1 learns faster at 1,024 updates (0.171 against 0.122) |
| 16,384 | 0.03 | 0.050 / 0.132 / 0.787 / 0.959 / 0.903 | highest at the readout |

No rate diverged. At no unit is 0.1 ahead by more than 0.02 at the readout, so nothing returns (§10.1 item 3).

## What this does not show

Nothing here is a result of S1. A U_L of 786,432 lengthens the registered run; whether the registered run fits under C_max = 36 hours without the fixed cuts is decided only by the rehearsal's measured rates.

## Files

`calibration.json`, `calibration_items_load_row_up.json` (first search), `calibration_items_load_ext_row_up.json` (extension), `calibrate-load-ext-item-cap.json`, `timing_preview.json`, `manifests/`, `unmeasured_previews/`, `SHA256SUMS`.
