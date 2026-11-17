# P10-S1 — freeze record of the second attempt (ADR-0021 §25.19 and §25.20), 2026-11-17 UTC

Written by the scientific lead (Claude Fable 5.2) at the freeze commit, which adds this file, `CODE_SHA256.txt`, `studies/p10s1/freeze/plan.json` and `studies/p10s1/freeze/stage_caps.json`. Nothing here is a result. Attempt 1 ended S1-INCOMPLETE on an engineering stop caused by the lead (§25.19); the human lead approved a second attempt ("Yes, second attempt"). No evaluation has run on a registered draw and no training record of attempt 1 has been opened. Results under oracle addressing are not autonomous learned memory. Astra review: NOT_PERFORMED.

The first freeze record (`results/p10s1-freeze-2026-11-16/FREEZE.md`) stays as written. Everything in it that is not listed below as changed holds for this freeze.

## Identities

- Code commit before the freeze commit: `52123bcc7f0a524990ff1384336a59871ad2af34`. The five registered draws were regenerated at `322b154` into the new run directory; the freeze binds each draw by the sha256 of its data manifest (in `plan.json`). SHA-256 of every file of the frozen specification: `CODE_SHA256.txt` (46 files).
- Frozen plan: `studies/p10s1/freeze/plan.json`, sha256 `01b6a1eb15a28f3b4ffc3ac7d7e095c10dfcc20d0313b0e8c69ee8e34fe450ca`. Cap table: `studies/p10s1/freeze/stage_caps.json`, sha256 `78120ff35a05c10aec7eb62210ab59ab993ef753b58e31d8dee0210ad7be5adf`, identical to attempt 1's.
- Run directory: `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117`.
- Inputs: the same calibration, timing, rehearsal gates and synthetic records as the first freeze. Projection: `P10S1R5-rehearsal-20261116/projection_cmax54_attempt2.json`, sha256 `28e7c6301c5b223a83a400811297f932249b53af4e5344a2c823c31e1e7f9fe0`.
- Attempt 1's plan and cap table: `results/p10s1-freeze-2026-11-16/attempt1-freeze-files/`, moved unchanged.

## What changed since the first freeze

- C_max 50 → 54 hours (the lead, under the P10 delegation, reported to the human lead before this freeze). Charged before this freeze: 40,099 s plus the regeneration of the draws; C_need 189,122 s (52.53 h); **computed cap 53 hours** (was 49).
- ADR-0021 gained §25.18 to §25.20. One test assertion pair follows the C_max change.
- Nothing else: the same 178 cells with no cut, the same draws and seeds, the same calibrated values, the same stage caps (train 142,872 s; evaluate 5,444 s; gates 60 s; timing 399.5 s; simulate 120 s; analysis 60 s; report 60 s), the same thresholds and analysis rules, lane L omitted as before.

## Generation

Five draws regenerated, 27.3–27.8 s each against the 40 s cap, G1 passed.

## Launch commands (in this order; `<freeze>` is the commit that adds this file)

`sh studies/p10s1/launch/<stage>.sh /Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117 <freeze>` for `gates`, `train`, `evaluate`, `timing`, `simulate`, `analysis`, `report`.

## Condition of this attempt

After the second Decision 2 is committed, nothing is committed or written in this working tree until the report stage has finished. The independent check before this freeze (Opus 5.5) returned READY WITH NOTES; its notes are answered in ADR-0021 §25.20.
