# P10-S0 — freeze record (ADR-0020 revision 4 and addenda), 2026-11-15 UTC

Written by the scientific lead at the freeze commit, which adds this file, `studies/p10s0/freeze/plan.json` and `CODE_SHA256.txt`. Nothing here is a result. No model has been trained or evaluated on a registered draw. Astra review: NOT_PERFORMED.

## Identities

- Code commit at which the registered draws were generated: `5e4289497d282733e74b1acfecc7a62971867484`. `train.py`, `evaluate.py`, `model.py` identical to `3a9a742` (the rehearsed code). SHA-256 of every file under `studies/p10s0/` and of `configs/p10s0_qualification.toml`: `CODE_SHA256.txt` beside this file.
- Frozen plan: `studies/p10s0/freeze/plan.json` (profile `registered`; it names every data manifest of the 13 registered and 2 reserve draws by sha256).
- Arm-selection record: `studies/p10s0/freeze/arm_selection.json`, sha256 `e8bbd2c0b574e74f3d68a7463043ff60a846a633dc57e8a38d48a5ec04e5692c`. Arms: A0, A1, A2, and A5-D (`FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)`).
- Draw plan: sha256 `f55c411dce919b612ab7f693ecf9e81579748f10ddf003a53ea1ca9bbd257995`; 15 of 15 draws passed G1; no reserve substituted.
- Run directory: `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S0-registered-20261115`.
- Projection: `experiments/P10S0J-projection-20261115-r2/projection.json`, sha256 `f7e13716bf670b3861cd36f041d3a16202bb33f018083ec27007a55909097c9a`; `guard_seconds_per_task` 0.26484929100843146 (measured once; frozen at this value).
- Cap table: `studies/p10s0/freeze/stage_caps.json`, sha256 `b9f85b41bc190664c76c1904be2e29100971333497685b471373e2029115adb8`.
- Pinned auditor scripts: `c2_mapping_enumeration.py` `c3629201d85be3e71a855b59731d13a6fcec9475d1060a12f52455ee3463fbb5`; `c5_rev2_mapping_and_consistency.py` `886e2d274a81784e2661c31cc53ba4938568f1e7dfa947ea6d01dbca0365b89e`. The auditor's recomputations: `docs/reviews/p10s0-implementation-audit-2026-11-15/` (`AUDIT.md`, `recheck/RECHECK.md`, `prefreeze/PREFREEZE.md`, `prefreeze/CONFIRM.md`).

## Gates, generation, caps

- Rehearsal-draw gates: G1, G2, G4, G5, G6, G9, G10 passed (`experiments/P10S0G-rehearsal-gates-20261115`). The registered gates run first in the launch order.
- Generation cap 66.898 s per draw (2 × the rehearsal draw's 33.449 s). Registered generation: 15 draws, 19.7–20.3 s each, 299.6 s in total (MEASURED).
- Hour cap 22 hours. Stage caps as in the cap table: gates 156.2 s; Q1 train 58,841 s and evaluate 1,711 s (cut 3: 40,772 s and 1,260 s); WX train 5,873 / 7,652 s (A5-D / A1); probe train 23,497 / 39,462 s; analysis 60 s; report 60 s; reserve for analysis and report 60 s.
- Projections (not results): Q1 30,276 s; cut 3 21,016 s; WX 3,033 / 3,920 s; probe 11,825 / 19,818 s. Cut 3 of section 10.4 does not apply at projection. Margin of the headroom rule at the Q1 gate: +18,023 s (A5-D), +260.8 s (A1); with A1 the probe is refused if Q1 runs 0.86 % slower than projected.

## Launch commands (in this order; `<freeze>` is the commit that adds this file)

`sh studies/p10s0/launch/<stage>.sh /Users/daniellaloush/dandush03/ArborLM/experiments/P10S0-registered-20261115 <freeze>` for `gates`, `q1`, `q1_gate`, `wx`, `probe`, `analysis`, `report`. WX runs before the probe.

## The lead's conditions (section 18) and approvals

- The run decision is `DECISION.md` beside this file. Registered gates are launched with no other study computing.
- Every printed string the ADR does not fix is approved as worded in the tables of `studies/p10s0/freeze/README.md` at this commit (sections "Implementer additions accepted by the lead" and "Implementer-worded strings"), including the fourth-arm strings, `NOT DEFINED (S0 NOT_EVALUATED)`, `NOT AVAILABLE (S0 NOT_EVALUATED)`, the overload and record-length-free strings, `NOT QUALIFIED IN S0` with its neutral sentence, the P9-II acceptance banner, the hypothesis table notes, the `ADDRESS STABLE` non-finite counting and the block-status strings of section 8.7.
- No oracle-assisted or supervised result of S0 is to be worded as autonomous learned-memory success.
