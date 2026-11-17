# P10-S0 — the lead's run decision (ADR-0020 section 18), 2026-11-15 UTC

Decision: **run P10-S0 once, as registered**, under ADR-0020 revision 4 and its addenda. This is the scientific lead's decision under the human lead's recorded delegation that P10 studies may be self-approved (`docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md` on `claude/p10-design`). It is not a result and claims nothing about S0's outcome. Astra review: NOT_PERFORMED. The reviews named here are Claude reviews.

## What the decision rests on

- The human lead's acceptance of the P9-II outcome is recorded (ADR-0019 section 16); A5-D enters S0 as the fourth arm by the human lead's decision, as a confirmatory replication.
- Implementation audit, re-check, pre-freeze audit and the confirmation of the pre-freeze fixes: `docs/reviews/p10s0-implementation-audit-2026-11-15/` (`AUDIT.md`, `recheck/RECHECK.md`, `prefreeze/PREFREEZE.md`, `prefreeze/CONFIRM.md` with the lead's rulings). The confirmation's two conditions are met: both end-to-end variants (`memory`, `probe`) exited 0 at commit `1ccfffd`, and the projection is named below.
- `train.py`, `evaluate.py` and `model.py` are unchanged since the rehearsal (identical to `3a9a742`).
- Pipeline check, rehearsal-draw gates (all passed) and both rehearsals: `experiments/P10S0K-20261115T164503637681Z-0442e02f363f4c21b710c24896f44de0`, `P10S0G-rehearsal-gates-20261115`, `P10S0H-rehearsal-alone-20261115`, `P10S0H-rehearsal-busy-20261115`.

## Frozen inputs

- Projection: `experiments/P10S0J-projection-20261115-r2/projection.json`, sha256 `f7e13716bf670b3861cd36f041d3a16202bb33f018083ec27007a55909097c9a`. It replaces `d6f6e6be…` because the fix of F10 changed the projection code; totals differ by seconds, from the re-measured per-task guard.
- Analysis and report timing: `experiments/P10S0M-analysis-timing-20261115/timing.json`, sha256 `300a749510af7e2a9443577817abcd26b758d94845f09e4815450f6d97629354` (22.29 s and 0.507 s; both caps are the 60 s floor).
- Cap table: `studies/p10s0/freeze/stage_caps.json`, sha256 `b9f85b41bc190664c76c1904be2e29100971333497685b471373e2029115adb8`, recomputed independently in `CONFIRM.md` (16 of 16 entries equal).
- Hour cap: 22 hours. Ledger before the registered run: 486 s.

## Projected time and margins (projections, not results)

- Q1 full 30,276 s (8.41 h); under cut 3 21,016 s. WX 3,033 s (A5-D) / 3,920 s (A1). Probe 11,825 s (A5-D) / 19,818 s (A1).
- Headroom rule at 22 hours: before Q1 +17,461 s (cut 3 does not apply at projection); at the Q1 gate +18,023 s with A5-D and +260.8 s with A1. With A1 as candidate the probe is refused if Q1 runs 0.86 % slower than projected or generation and gates reach their caps. That is the registered rule; the cap is not raised for it.

## Conditions

- Registered generation and the registered gates run with no other study computing on the machine.
- Nothing is changed after the freeze commit. Every outcome, including a negative, a null, an incomplete block or a refused probe, is recorded as it falls.
