# Audit 19 (delta): P10-I-S2 Part T, commits 9db20a45 and 0993af45

VERDICT: READY FOR SECOND FREEZE AFTER A COMPLETE SECOND TARGETED REHEARSAL

- Auditor: arbor-auditor, run as Claude Opus 5.5 (claude-opus-5-5). Date 2026-11-23.
- Strictly read-only. In worktree agent-acd0bce1f7811562f (HEAD 0993af45) I ran only `git show`, `git log`, `sed`
  and `grep`.
- I read these files with stdlib `python3 -I` json loads:
  - the failed run's driver log;
  - the failed run's ledger and its train manifest status;
  - the registered run's `stages/` listing and the `status` field of `train/manifest.json`.
- I did not open sealed/, snapshots/ or any checkpoint.
- This is engineering evidence from a Claude review. It is not Astra review and not human approval.

## 1. The diagnosis is correct and driver-only
**What happened in the failed run.**
- The driver log P10IS2-T-targeted-20261123_driver_logs/train-m-ii-to-the-cap.log ends in
  `RuntimeError: .../P10IS2-T-targeted-20261123/train/manifest.json is COMPLETE; a completed stage is never rewritten`.
- That error comes from runner.write_manifest (common/runner.py:164), called from partt_tasks.py:179.
- The failed run's train manifest is COMPLETE, and its only history entry holds just M1 and M-append. The parents'
  invocation completed the stage because the M-ii wave was empty under `--rehearsal-arms M1,M-append`.
- The ledger shows M-ii AB r0 charged 700.2 s and a checkpoint `r0__M-ii__AB.ckpt` exists. The charge was recorded
  because partt_tasks.py:176 charges the ledger before line 179 writes the manifest.

**Why the real resume is not affected.**
- In the registered run, `stages/` holds only gates.complete.json, and `train/manifest.json` has status PAUSED.
- write_manifest refuses only when the prior status is COMPLETE. It is called once per invocation, at the end of
  run_stage_tasks, and never during polls.
- At a cap stop the prior status is PAUSED, so the manifest is rewritten as PAUSED.
- At completion the prior status is still PAUSED, so the manifest is written as COMPLETE and then marked complete.
- So the exception cannot occur at the real resume. It would occur only if train were launched again after it
  completed, and then it would exit 1 with nothing changed.

## 2. The 9db20a45 diff
- Only partt_targeted.py and the test file change.
- **What the fix does:**
  - It trains the parents in `<run_dir>_parents`, a directory claimed in rehearsal mode, with its own gates marker.
  - It copies the parents' flat snapshot files (`<label>.pt` and `.manifest.json`, see engine.py:188/207) into the
    M-ii run directory.
  - It adds the parents' charge to the main ledger as one entry. The freeze reads that main ledger, so the charge is
    counted once.
- **The timed M-ii cell is unchanged.** It is the same cell (U = 8,000, workers = 1, parents at 200 updates as before).
- **It cannot pass vacuously.** These conditions still apply:
  - the cap stop must be KILLED_CAP;
  - a checkpoint must exist;
  - the resumed cell must record `resumed`;
  - units must equal U.
- **A missing or wrong parent snapshot would fail loudly**, with an ERROR or a FAILED stage, not silently.
- **Tests:** the commit adds two tests. They reproduce the COMPLETE-manifest refusal and check the snapshot copy.

## 3. The regenerated plan (0993af45)
**Differences from the first freeze's plan.** I recomputed the differences from c25d4f0b's plan. They are only:
- the charge ledgers and seconds;
- the config sha;
- the allowance;
- the frozen hashes of the config, the six exempt files and the three amendment files;
- the import walk: exactly partt_targeted.py and partt_amendment/__init__.py added;
- the cap_amendment_record manifest entry, which has sha 10463ef9…, the hash ruling 51 cites;
- the train, combined and total caps.

All of these are allowed. Train is 125.8 h, combined 6.0 h and the allowance 3.0 h.

**Total cap.**
- The plan charge is 88,018.92 s (24.45 h), including the failed targeted ledger's 840.75 s.
- Total = ceil(24.4497 + 3.0 + 176.80) = 204.25 h, which is ≤ 205.

**Handling of the failed attempt's charge.**
- Putting it into the plan charge follows the precedent set by the failed measuring attempts 1 and 2 and by the first
  counting rehearsal under the amendment: every Part T charge made before the plan goes into the plan charge.
- Disclosure: the 3.0 h targeted allowance is effectively renewed for the second attempt (as under ruling 20's
  re-plan). No charge is lost.
- The headroom after train at its full cap narrows to 53.4 − t h against 50.46 h of later caps. They still fit for a
  targeted charge t ≤ 2.9 h.

## 4. M-ii rate
- **What I verified.** The failed run charged 700.2 s to the M-ii cell before the kill, and a checkpoint exists.
- **What I could not verify.** I did not open the checkpoint, so I cannot confirm "update 1,500".
- **Arithmetic if update 1,500 is right.** About 0.44 s/update including world build, so 8,000 updates take about
  0.98 h. That is consistent with 2,798 s (0.78 h) for the counting rehearsal's M-ii cell alone, and roughly 7× under
  the 7.48 h per-cell cap.
- **Remaining work.** About 27,000 updates at about 0.44 s each is about 3.3 h, plus four world builds. That is far
  inside the remaining 29.93 h of train cap.
- **Before 08:00.** It fits if training starts by about 04:00 local. PENDING LEAD REVIEW: the clock depends on the
  freeze steps.
- **Caveat.** This is one cap-stopped segment. The second targeted rehearsal's full-cell figure is the measurement of
  record.

Astra review: NOT_PERFORMED
