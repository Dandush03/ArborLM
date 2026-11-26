# Audit 16: P10-I-S2 Part T, how the frozen code enforces stage caps during the registered run

Auditor: arbor-auditor. Session metadata says the model is Claude Opus 5.5 (claude-opus-5-5). Date 2026-11-22.
`Astra review: NOT_PERFORMED`. This is independent engineering evidence. It is not Astra validation and not human approval.

Scope: I only read code in `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f`
(HEAD 42650445). In the run directory I read only `charged_ledger.json`, `stages/*.json` and the cost fields of
`tasks/train/*.timing.json`. I also read the counting rehearsal's `charged_ledger.json` and the cost fields of its
`tasks/train/*.timing.json` (`experiments/P10IS2-T-counting-20261121`). I opened no sealed, snapshot or result file. I
created no file in the Part T worktree and ran no python, uv or git-write command there.

Commands used: `grep`, `sed -n`, `jq` (read-only) on those files. The arithmetic is plain `python3` (system interpreter, no
imports beyond builtins) run from the consolidation worktree, with the figures passed inline. Times are as of
2026-11-22 14:13 local. The Write tool was refused (worktree hook), so this file was written with a Bash heredoc.

Run state read: the ledger holds 1 entry, gates 1,428.63 s. It has no train entry yet, which fits charging at the end of
each wave (item 2). `stages/` holds only `gates.complete.json`. Eleven train timing files exist. Their `task_body_seconds`
sum to 54,383.70 s and `world_build_seconds` to 38.06 s.

---

## Item 1. A multi-task stage's cap is compared against wall clock. Verdict: PARTLY. The mechanism is confirmed but the consequence is refuted

**What is confirmed**
- `run_tasks` compares the cap it receives against wall clock since that call began: `runner.py:67` sets
  `begun = time.monotonic()`, and `runner.py:80` checks `if time.monotonic() - begun > cap_seconds`.
- The runner's own docstring calls this "the stage's wall-clock cap" (`runner.py:7`, `runner.py:63`). That
  contradicts `partt_tasks.py:9-10`, which says the cap is in charged seconds.
- Inside one call, up to `workers` (3) processes run at once. So one call can charge up to about 3x the cap it was
  handed before the runner kills anything.

**What is refuted: the cap is not evaluated once per invocation**
- `run_stage_tasks` loops over waves (`partt_tasks.py:153`). It recomputes `cap = stage_cap_for(plan, stage, led)`
  at the start of every wave (`partt_tasks.py:154`).
- It writes every worker's seconds of the finished wave to the ledger (`partt_tasks.py:162-163`) before the next wave
  starts.
- Train has three dependency waves (`partt_tasks.py:29, 52-53`). From the plan's 54 train items:
  - wave 1: M1, D1, M-joint, D-joint and E-table, 24 cells
  - wave 2: M-append, M-seq, D-append and D-seq, 24 cells
  - wave 3: M-ii, 6 cells
- So charged hours bind at wave boundaries, and wall clock binds only inside a wave.

**Consequence with the run's own cost figures (arithmetic in item 3)**
- At the observed ratio of about 1.35x the rehearsal cost, waves 1 and 2 charge about 77.3 to 79.0 h. That is above
  train's 75.68 h (272,448 s).
- When wave 3 begins, `stage_cap_for` returns 272,448 - charged(train) < 0. Lines 156-159 then mark all six M-ii cells
  `not_started` with "the cumulative hour cap is spent", and the loop breaks.
- The manifest status is PAUSED (`runner.py:135-142`). `execute_stage` returns `EXIT_INCOMPLETE` = 4
  (`partt_stages.py:127-133`) and writes no `train.complete.json`.
- Projection: train will most likely not complete in this invocation. It will stop PAUSED before M-ii with about 79 h
  charged. The registered cap is still overshot, by about 1.6 to 3.3 h, because wave 2 is checked only against wall
  clock (about 40 h of wall budget, against about 14.5 h of wall need).
- Break-even: wave 3 is refused outright when the charge of waves 1 and 2 exceeds the cap. That happens at a ratio
  above 1.294 (rehearsal M1 cell taken as its ledger total of 2,407.6 s, which includes the forced pause) or above
  1.322 (M1 taken as 1,645.5 s).
- Wave 3 starts but is killed `killed_cap` for ratios between about 1.26 and 1.29. Below about 1.26, train completes
  at about 77 to 79 h.
- The per-cell ratios seen so far run from 0.90 to 1.82 (registered body against rehearsal body), so this is a
  projection, not a certainty.

Rehearsal-scale costs per wave, from the counting rehearsal ledger (one cell per arm × the plan's cell count):

| | w1 | w2 | w3 | total |
|---|---|---|---|---|
| M1 = 2,407.6 s | 26.17 h | 32.33 h | 4.71 h | 63.21 h |
| M1 = 1,645.5 s | 24.90 h | 32.33 h | 4.71 h | 61.94 h |

At r = 1.30 / 1.35 / 1.40 (M1 = 2,407.6 s):

| r | w1 + w2 | wave-3 cap | full train |
|---|---|---|---|
| 1.30 | 76.05 h | -0.37 h | 82.18 h |
| 1.35 | 78.98 h | -3.30 h | 85.34 h |
| 1.40 | 81.90 h | -6.22 h | 88.50 h |

## Item 2. When train's ledger entries are written, and whether charge is checked against the cap. Verdict: CONFIRMED that there is no check at the end of the stage, with additions

**When entries are written**
- Entries are written per wave, after `run_tasks` returns, one entry per task (`partt_tasks.py:161-163`).
- Completed and skipped tasks get a 0 s entry (`runner.py:72`).
- Nothing is written when a worker exits mid-wave. Workers do not charge the ledger themselves: grep finds no
  `charge_process` in `run_task`. The only task-stage writer is `partt_tasks.py:163`.

**Checks**
- Charged time is checked only at the start of each wave (`partt_tasks.py:154-156`).
- There is no check at the end of a wave or of the stage that compares charged time with the stage cap or the total.
- On COMPLETE, `execute_stage` marks the stage complete whatever the overshoot (`partt_stages.py:127-132`).
- `Ledger.require_room` (`core.py:334-338`) is never called (grep finds no caller).

**Hazards (advisory)**
- (a) If the `work` orchestrator dies mid-wave, that wave's worker seconds are never charged. ADR L2 says every attempt
  is charged. Workers run in their own session (`start_new_session=True`, `runner.py:93`), so they can also outlive the
  orchestrator.
- (b) The orchestrator's own wall time is not charged for task stages.
- (c) `caps_used["total_seconds_left"] = led.remaining()` (`partt_tasks.py:155`, `core.py:331-332`) ignores the
  87,178.16 s pre-freeze charge, so the manifest overstates the total left by that amount. It is a record only and is
  not used for enforcement.

## Item 3. What later stages check, the charge before the freeze, and the remaining arithmetic. Verdict: CONFIRMED

**What each later stage checks**
- Each later stage checks the predecessor's completion record (`partt_tasks.py:75-79`, called at `partt_stages.py:122`)
  and the gates (`partt_real.py:607-613`).
- It then checks its own cap: `stage_cap_for` = min(own cap - own charge, total - charge_before_freeze - all charged)
  (`partt_tasks.py:114-120`).
- No code compares the previous stage's charge with that stage's own cap. A train overshoot reduces only the total
  term.

**`charge_before_freeze(plan)`**
- It reads `partt_freeze_record.json` -> `pre_freeze_charge.registered_ledger_starts_from_seconds`
  (`partt_tasks.py:104-111`).
- That value is 87,178.16 s = plan 34,679.46 + counting rehearsal 52,498.70. Confirmed from the record.

**Arithmetic**
- Total cap: 540,612 s (150.17 h).
- Left after the freeze: 453,433.84 s (125.954 h). Left after gates: 125.557 h.
- Later stage caps: evaluate 21.77, controls 0.01, combined 1.63, recompute 22.66, analysis 0.01, report 0.01, sum
  46.09 h.

| train charge T | total left for later stages | vs 46.09 h of caps | if every later stage used its full cap | at 1.35x the later projections (cap/2 × 1.35 = 31.11 h) |
|---|---|---|---|---|
| 75.68 h | 49.877 h | +3.787 | own caps bind throughout | margin 18.77 h |
| 78.98 h (projected PAUSE) | 46.577 h | +0.487 | own caps bind throughout | margin 15.47 h |
| 85 h | 40.557 h | -5.533 | evaluate, controls and combined: own cap. **recompute: the total binds (17.15 h < 22.66)**. analysis and report get 0 and refuse | margin 9.45 h |
| 90 h | 35.557 h | -10.533 | **recompute: the total binds (12.15 h)**. analysis and report get 0 | margin 4.45 h |

- The total binds in practice only if the later stages charge more than 40.557/23.045 = 1.76x their projection
  (T = 85 h) or 1.54x (T = 90 h).
- The total binds first at recompute, then at analysis and report.

**Single-body stages: StageGuard**
- `StageGuard` compares the elapsed wall time of that one process (from construction, `partt_real.py:330, 346-349`)
  with `stage_cap_for` (`partt_real.py:390`).
- For one process, wall time equals charged time, so this matches L2.
- If the cap is already ≤ 0, the stage raises `StageRefused` (exit 2, `partt_real.py:391-392`).
- `recompute` is in `SINGLE_BODY_STAGES` (`partt_real.py:319`). It is charged once by `run_stage` (`partt_real.py:450`;
  `charge=False` at line 414).

**Evaluate and combined are task stages with the same overshoot**
- Each runs as one wave, compared against wall clock with up to 3 workers. So each can charge up to about 3x its
  handed cap.
- Through evaluate, the total cap (and the 151 h study bound) can therefore be exceeded without a stop.

## Item 4. Any path to extend a cap or the total after the freeze. Verdict: CONFIRMED, none exists in the frozen code

Every route to a different cap is checked against a frozen identity:
- Caps are read only from the plan's `stage_caps` (`plan.py:184-188`).
- `verify_plan` requires the config's `[stage_caps]` to equal the plan's (`plan.py:224-227`). The
  `stage_caps_attempt3` branch applies only if `plan.inputs.reuse` is set, and the frozen plan has `inputs` = null.
- The config hash must equal the plan's `config_sha256` (`plan.py:221-222`).
- The plan's hash must equal the one in the freeze record (`plan.py:296-303`).
- `check_preconditions` compares `studies/p10is2` (the whole tree, `freeze/` included) and the config at HEAD against
  the freeze commit (`plan.py:270-271`). Any committed edit is PAUSED — IDENTITY, and an uncommitted edit refuses on
  a dirty tree (`plan.py:254-260`).
- The freeze record is written once (`partt_stages.py:765-766`).

A re-freeze would also need all of the following, which amounts to a new registration, not an extension:
- the config caps equal to the code-computed proposal (`partt_stages.py:793-796`)
- a counting rehearsal that names the new plan's SHA-256 (`partt_stages.py:845-847`)
- the 151 h bound check (`partt_stages.py:851`)
- a new Decision 2 naming the new commit

No code reads an extension record. The refusal messages say "the extension is the lead's" (`partt_tasks.py:156`,
`partt_real.py:392`), but no mechanism implements one. ADR §9 line 382 says the caps are "Extended on cost projections
only". How to carry that out is PENDING LEAD REVIEW.

## Item 5. Resuming after KILLED_CAP or a spent cap. Verdict: CONFIRMED, it effectively refuses (task stages pause, they do not raise)

**Task stages (train)**
- On a resume, wave 1's `stage_cap_for` is ≤ 0. Every wave-1 item is set `not_started` with "the cumulative hour cap
  is spent", the loop breaks and nothing runs (`partt_tasks.py:154-159`).
- The manifest is PAUSED and the exit code is 4. No `StageRefused` is raised.
- Side effect (advisory): `write_manifest` does `tasks.update(outcomes)` (`runner.py:159-160`). This overwrites the
  manifest's latest status of wave-1 cells that already have result files with `not_started`. Their result files stay,
  and `run_tasks` would skip them on a later run with cap left (`runner.py:71-72`), so only the manifest record is
  misleading.

**Single-body stages**
- They raise `StageRefused` (exit 2) when the cap is spent (`partt_real.py:391-392`).

**Effect on the rest of the run**
- Train cannot complete, so evaluate and every later stage refuse on the missing predecessor record.
- The N6 analysis bypass (`partt_stages.py:121`) applies only after a recorded gate failure.

## Item 6. What ADR-0025 says about the stage cap. Verdict: CONFIRMED that it is charged hours, so the wall-clock comparison inside a wave departs from the text

The governing lines in `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md`:
- Line 382 (§9): "Part Q and Part T charged hours: each registered stage 2 × its projected time, and the part's total
  its pre-freeze charge + 2 × the projected time of all its registered stages … | Resource cap | PAUSED and resumable.
  Extended on cost projections only, never on an outcome value; every planned block and cell still runs".
- Line 413 (§10 item 3): "Each registered stage's cap is 2 × its projected time … Charged time is the sum over worker
  processes of each process's wall time (section 19, L2). ADR-0029 charges stage wall time; figures of the two studies
  are not on one scale."
- Line 658 (§19 L2): "Charged time | The sum over worker processes of each process's wall time, every attempt
  (rehearsals and paused attempts included) … ADR-0029 charges stage wall time on six workers".
- Line 619 (§18): C10 "FIXED: the sum of each worker process's wall time kept; caps defined".

**Departure from the text**
- The caps are defined in charged hours.
- The runner kills on wall clock inside a wave, which lets a 3-worker wave overshoot by up to 3x. That departs from
  the registered text.
- The between-wave and between-stage checks do use charged hours.

**Earlier rulings and audits**
- I found no ruling or audit that notes this.
- Searched:
  - the addenda (`grep -i "wall.clock|cap.*wall|run_tasks|per wave"`)
  - audits `AUDIT*_P10IS2_PARTT*.md`, 1 to 15
- Results:
  - audit 15, §5 item 2, checked `stage_cap_for` and the starting charge only
  - AUDIT2 D2 noted that the registered caps were never exercised by a rehearsal
- I did not read every audit in full.

Whether this departure matters scientifically, and what to do about the projected PAUSE before M-ii, is PENDING LEAD
REVIEW.

## Item 7. Anything else in the cap and ledger path that could stop the remaining stages. Verdict: findings

1. **Main finding: train PAUSES before M-ii.** At about 1.35x, train most likely ends PAUSED before wave 3, with no
   train completion record (item 1). Nothing later can run, and the frozen code cannot extend the cap (items 4 and 5).
   This applies at a train charge of 85 to 90 h only if the full train were reached. On the code's actual path, the
   charge stops at about 77 to 79 h with M-ii untrained.
2. **Tiny caps on single-body stages.** controls, analysis and report have caps of 0.01 h = 36 s each, measured from
   guard construction, so the world build counts. In the counting rehearsal they charged 2.68, 2.78 and 2.71 s. The
   registered analysis runs on the full registry, and I did not measure it (see what I could not verify).
3. **The total binds only for large overruns.** At T = 85 to 90 h it binds at recompute, and then at analysis and report
   at 0 s, but only if the later stages charge more than 1.5 to 1.8x their projection (item 3).
4. **Evaluate can overshoot.** Evaluate (4 tasks, 3 workers, one wave) can overshoot its own cap and the total by the
   same wall-clock mechanism, without a stop.
5. **Under-charging hazard.** If the orchestrator dies mid-wave, that wave is never charged (item 2). The charge would be
   lower than what L2 requires, so this is not a stop.
6. **Gates.** Gates charged 1,428.63 s against its 1,944 s cap. Passed.

## What I could not verify
- Per-cell costs of waves 2 and 3 in the registered run (not yet run). The 1.35x ratio is the lead's figure. My recount
  gives 54,383.70 / 40,421.8 = 1.345 on body seconds, with M1 = 2,407.6 s. Per-cell ratios spread from 0.90 to 1.82.
- Worker charged seconds include process start, imports and identity checks, so they are slightly above
  `task_body_seconds`. I did not read the manifest (not in the allowed list).
- Whether the runner's worker count stays 3 for all waves. `worker_policy` reads `other_alive()` once per invocation
  (`partt_tasks.py:148`).
- Registered durations of analysis and report against their 36 s caps.
- Whether any document outside ADR-0025, its addenda and audits 1 to 15 discusses the wall-clock comparison.
