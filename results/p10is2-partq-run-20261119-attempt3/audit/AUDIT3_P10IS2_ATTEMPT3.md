# P10-I-S2 Part Q, attempt 3: confirmation of 438d200 (the freeze's re-derivation fix)

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19, about 22:34–22:40 local time.
- **What was read.**
  - `git diff 0306c8b 438d200` and `git diff 438d200 c75d0bd`;
  - the rebuilt candidate plan `182e043f…`, read **by commit** (`git show c75d0bd:…`), not from the working tree;
  - the ten ledgers it names, read only.
- **What was run.** One `pytest` process with `timeout`, on a scratch git copy of `438d200` at `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-a5/`.
- **Not touched:** the running counting rehearsal (`counting7`), the worktree's freeze folder, attempt 2's run directory, the preserved ledger. No git writes to project repositories, no `/tmp`, no network.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdict: CONFIRMED — FREEZE

## 1. Can a hand edit of the plan loosen a cap?

**The re-derivation builds from the plan's own recorded values**, as before for `inputs` and now also for `charge_before_freeze`. Each of those is tied to something outside the plan file:

**`inputs` and the reuse block.** They are re-hashed against the files themselves:
- the reuse block by `reuse.verify_block` at the freeze and at every stage;
- the other inputs by `verify_inputs` at every stage.

An edited hash is refused as PAUSED — IDENTITY. This is unchanged.

**`charge_before_freeze`, and which direction is unsafe.**
- The freeze requires the config's `[stage_caps_attempt3].total_hours` to equal `proposal_attempt3(measuring record, recorded charge)`, which is charge + 2 × Σ projected.
- The plan carries that same section.
- `run_stage` computes `left_in_total = total − recorded charge − this run's charges = 2 × Σ projected − this run's charges`.
- **The recorded charge cancels.** Recording it smaller lowers `total` and `before` by the same amount, so the run's room is unchanged.
- The per-stage caps (2 × projected) do not depend on it at all.
- **So no direction is unsafe for the registered run.** A wrong charge can misstate only the recorded overall budget, not loosen any cap.

**What ties the recorded charge to the ledgers.** `check_charge_unchanged` refuses a named ledger that now holds **less** than recorded, and reports any that grew.

**Not checked (ADVISORY).**
- That `seconds` equals the sum of the recorded per-ledger values.
- That the named ledgers are all of Part Q's ledgers.

As shown above, neither can loosen a cap. On the plan at `c75d0bd` I checked both by hand:
- recorded `seconds` **47,493.993** equals the sum of its **10** ledgers;
- every ledger holds at least what was recorded, and none has grown;
- total by hand 47,494 + 2 × (25.8 + 466.6 + 637.4 + 11.9) s = **13.827 h, rounded up to 13.83 h**, equal to the committed `[stage_caps_attempt3]`;
- the stage caps are reuse 0.02, regeneration 0.26, outputs 0.36, analysis 0.01, each 2 × (measured + 10.6 s hashing), checked by hand;
- the reuse block holds 25,792 files with tree `b6777dbccf5c…`, equal to my own hash of attempt 2's directory.

**Tampering after the counting rehearsal is caught by the plan hash.** The plan file's SHA-256 is fixed by the counting rehearsal record and the freeze record (`reuse_rehearsal_gate`).

**A genuinely different plan is still refused.** The test `test_a_genuinely_different_plan_is_still_refused_and_the_differing_fields_are_named` passes. The refusal now names up to ten differing paths.

## 2. The reuse certification stands

`partq/freeze.py` is in `reusecheck.ALLOWED_FILES` as a whole file ("the freeze, plan and caps commands (not executed by a stage)"). The `work` path never calls it; `stages.py` only imports it. Nothing the reused stages executed changed in this diff: the only other changes are tests, the config's attempt-3 caps section and the freeze folder's records.

## 3. Tests and the rest of the diff

- `test_p10is2_e2e_reuse.py`, `test_p10is2_reusecheck.py`, `test_p10is2_partq_freeze.py` and `test_p10is2_partq_commands.py`: **71 passed in 86.6 s**.
- They include the new case that was missing: a plan built with **both** a charge and a reuse block re-derives equal (`test_the_rederivation_of_a_plan_built_with_a_charge_and_a_reuse_block_equals_the_plan`).
- Attempt 2's plan and freeze record were moved to `freeze/attempt2-stopped-at-outputs/` (a rename, bytes equal). As with the attempt-1 folder, the code's fixed paths, the one-level `foreign_freeze_records` glob and the frozen sets do not pick it up.
- **ADVISORY:** make `check_charge_unchanged` also refuse when `seconds` differs from the sum of the recorded per-ledger values. It costs one line and makes the record self-consistent; it is not needed for safety.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
