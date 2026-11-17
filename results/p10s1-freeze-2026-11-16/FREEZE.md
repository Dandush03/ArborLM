# P10-S1 — freeze record (ADR-0021 revision 5 and §25.12–§25.17), 2026-11-16 UTC

Written by the scientific lead (Claude Fable 5.2) at the freeze commit, which adds this file, `CODE_SHA256.txt`, `studies/p10s1/freeze/plan.json` and `studies/p10s1/freeze/stage_caps.json`. Nothing here is a result. No model has been trained or evaluated on a registered draw. Results under oracle addressing are not autonomous learned memory. Astra review: NOT_PERFORMED.

## Identities

- Code commit before the freeze commit: `368599c6f3eb56728a126e8498691cbf914e992c`. The five registered draws were generated at `8b6b6bf`; the freeze binds each draw by the sha256 of its data manifest (in `plan.json`). SHA-256 of every file of the frozen specification: `CODE_SHA256.txt` (48 files: `studies/p10s1/`, `configs/p10s1_capacity.toml`, `tests/test_p10s1_*`, ADR-0021).
- Frozen plan: `studies/p10s1/freeze/plan.json`, sha256 `dcebf40de5328880b5d2fb8ccc05cb232dafcf6efe5cf68e9bb9bc20aa65e5ad`. Cap table: `studies/p10s1/freeze/stage_caps.json`, sha256 `78120ff35a05c10aec7eb62210ab59ab993ef753b58e31d8dee0210ad7be5adf`.
- Run directory: `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-20261116`.
- Inputs (git-ignored, under `experiments/`), sha256: calibration `P10S1C5c-calibration-20261116/calibration.json` `f85e60e5…08fe37`; projection `P10S1R5-rehearsal-20261116/projection_cmax50.json` `5e8c63fd…2b59d2` (the first projection, `projection.json` `900719cd…126cd2`, is NOT STARTED: BUDGET under C_max 36 h and is kept); timing `timing.json` `51700831…386521`; rehearsal gates `gates.json` `9d2b6ced…2b40c7`; synthetic `synthetic.json` `80930331…b226d1`. Full digests are in `plan.json`.
- S0: status `S0 ADDRESSING-QUALIFIED (4,096 AND 16,384)`; lane L `OMITTED — NOT OVERLOAD-QUALIFIED` by the lead's ruling of §25.17 (`studies/p10s1/freeze/lane_ruling.json`, `s0_record.json`).

## The plan

- 30 configurations per replicate, five registered draws `p10s1-draw-1 .. 5`, the seed blocks on draws 1 and 2: **178 cells** (150 per-replicate, 28 seed-block). No cut applies. 2K/256 is not run (`256 NOT MEASURED — NOT FULL WITHIN CEILING`).
- Loaded run lengths from the calibration (the load search was extended once after calibration data was seen, on the human lead's direction, §25.15): U_L = 393,216 at 8K/1K and 786,432 at 32K/4K. U_P = 8,192 / 8,192 / 16,384 for the rows of 2,048 / 8,192 / 32,768 facts.
- Dense rates: 0.03 (8K/1K), 0.03 (32K/4K), 0.1 (4,096 slots, EDGE BY TIE-WALK), 0.03 (16,384 slots). H8: UNDERTRAINED-AT-U_P at 8K/4K and 32K/16K; NOT CALIBRATED at 2K/1K, 8K/1K, 32K/4K.
- The step 16,384 → 65,536 is NOT TESTED.

## Gates, generation, caps

- Rehearsal-draw gates: all passed, no harness error (`experiments/P10S1R5-rehearsal-20261116`). The registered gates run first.
- Registered generation: five draws, 26.6–26.9 s each against the 40 s cap, G1 passed.
- Cap: C_max 50 hours (raised from 36 by the human lead, §25.16); C_need 174,764 s (48.55 h); **computed cap 49 hours**; charged before the freeze 25,741 s; contention ratio c = 1.9457 (rehearsal, as measured).
- Stage caps (2 × projection): train 142,872 s; evaluate 5,444 s; gates 60 s; timing 399.5 s; simulate 120 s; analysis 60 s; report 60 s. Projections (not results): training 71,436 s (19.8 h), evaluation 2,722 s.
- The registered `timing` stage measures throughput and needs a load average of at most 1.0; under load it records THROUGHPUT NOT MEASURED. It does not block the analysis or the report.

## Launch commands (in this order; `<freeze>` is the commit that adds this file)

`sh studies/p10s1/launch/<stage>.sh /Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-20261116 <freeze>` for `gates`, `train`, `evaluate`, `timing`, `simulate`, `analysis`, `report`.

## Audits and conditions

- Implementation audits of revision 5 and their re-checks: `docs/reviews/p10s1-implementation-audit-2026-11-15/rev5/`. Load-search extension audit: ADR §25.15 and commits `8fed6f4`, `6f7b1d8`. Pre-freeze audit: `docs/reviews/p10s1-prefreeze-2026-11-16/PREFREEZE.md` (one blocker); its re-check found the blocker closed, with two low findings (the ruling's S0 hashes are stated, not enforced by code — the reviewer verified them against S0's files by hand; `--lane-ruling` accepts any tracked file).
- Changes after calibration data was seen, all on the human lead's direction and before any registered seed was observed: the capacity grid (§24), the load-search ceiling (§25.15), C_max (§25.16). Every statement of S1's capacity result carries the first two.
- The run decision is `DECISION_2.md` beside this file.
