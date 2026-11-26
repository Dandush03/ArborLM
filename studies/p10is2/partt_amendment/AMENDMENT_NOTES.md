# P10-I-S2 Part T: cap amendment, ruling 51 (notes and departures)

`Astra review: NOT_PERFORMED`. Written by the implementer for the lead's ruling 51 and for disclosure. It is not an audit and not a decision. Numbers are **measured** (a record), **analytical** (arithmetic on measured figures) or **hypothetical**.

## Authority (the human lead's words, verbatim, relayed by the lead)

- 2026-11-22: "update cap and start over if necessary my cap is 6 days for any test".
- 2026-11-23, bound: the lead asked "Shall I set the bound to 205 charged hours?" and the human lead answered "ok, yes continue at night how many ours you have left?" (the lead reads "yes" as confirming 205; recorded as such for his review). `caps.study_budget_hours` = 205.0, one key.
- 2026-11-23, direction: "agree, ok, so please work so we can resume today and have the result by tomorrow morning" (a targeted rehearsal in place of a full second counting rehearsal).

No threshold, seed, cell, rate, scientific rule or calibration selection changes. Calibration is not repeated.

## Why

The registered train stage ended PAUSED (exit 4): 50 of 54 cells complete, train charged 345,134.9 s (95.87 h) against its 75.68 h cap. The last wave (six M-ii cells, three at a time) held about 32 to 35 GB of MPS driver memory per cell on a 48 GB machine; the two finished cells took 23,669 s and 25,535 s against 2,798 s for the one M-ii cell of the counting rehearsal (same 8,000 updates, run alone). The frozen code has no way to extend a cap (audit 16).

## What changes (by file)

| File | Change |
|---|---|
| `configs/p10is2_partt.toml` | `study_budget_hours` 205.0; `caps.workers_max_single_arm = 1`, `caps.single_worker_arms = ["M-ii"]`, `caps.memory_admission_free_gib = 16.0`; new `[cap_amendment]` (`record`, `train_hours`, `combined_hours`, `targeted_allowance_hours`) |
| `studies/p10is2/partt_amendment/__init__.py` (new) | loads the amendment, applies amended caps and the total, the exemption list, the plan and config difference checks, the targeted rehearsal's gate |
| `studies/p10is2/partt_amendment/AMENDMENT_RECORD.json` (new) | names the amended cap keys, the first freeze commit and the pre-amendment plan hash, the allowed config paths and the exempt files |
| `studies/p10is2/partt_caps.py` | `proposal_from_record(..., amendment)` applies the amendment (6 lines) |
| `studies/p10is2/partt_stages.py` | candidate-plan, caps-proposal, caps-config and freeze pass the amendment; freeze accepts the first counting rehearsal against the pre-amendment plan and the targeted rehearsal against this plan; `rehearse --kind targeted`; `--rehearsal-arms`; `--targeted-rehearsal` |
| `studies/p10is2/partt_tasks.py` | `wave_workers` (the M-ii wave runs one worker); `waves_of(..., arms)`; the admission threshold passed to the runner |
| `studies/p10is2/common/runner.py` | the cap is compared with charged time (sum over workers); admission on free system memory |
| `studies/p10is2/partt_targeted.py` (new) | the targeted rehearsal entry point and its record |
| tests | `tests/test_p10is2_partt_amendment.py` (new, 14 tests); `tests/p10is2_partt_unset.py` (synthetic copies drop `[cap_amendment]`); `tests/test_p10is2_partt_budget_bound.py` (the bound is now 205) |
| `conftest.py` | one strict expected failure: `test_the_caps_come_from_a_record_with_the_formula_and_a_zero_cap_is_refused` asserts the real config has no caps entered, false since the first freeze |

No training or scoring file changes: `engine.py`, `partt_run.py`, `scoring.py`, `labels.py`, `annotations.py`, `partt_items.py`, `partt_real.py`, `calibration.py` and `quantities.py` cannot be exempted (`partt_amendment.PROTECTED`).

## Caps (charged hours, analytical)

| Stage | Frozen | Amended | Basis |
|---|---|---|---|
| gates | 0.54 | 0.54 | done (0.40 h charged) |
| train | 75.68 | **125.8** | 95.87 h charged + 29.93 h for the four unfinished M-ii cells (three with checkpoints, one not started) = 7.48 h each, above the 7.09 h a cell took under memory thrash (the worst case) |
| evaluate | 21.77 | 21.77 | projected 14.7 h at the observed 1.35x |
| controls | 0.01 | 0.01 | seconds |
| combined | 1.63 | **6.0** | 2.9 h projected by the counting rehearsal (audit 14 A1) x 1.35 = 3.9 h, with margin |
| recompute | 22.66 | 22.66 | projected 15.3 h at 1.35x |
| analysis, report | 0.01 each | 0.01 each | seconds |
| Sum of stage caps | 122.31 | 176.80 | |

Counting-type allowance: the second counting allowance (18.26 h) is replaced by **3.0 h** for the targeted rehearsal. Plan charge before the freeze: 24.22 h (87,178.16 s: measuring 22,379 s + calibration 12,300.46 s + the first counting rehearsal 52,498.70 s, all measured).

**Total cap = 24.22 + 3.0 + 176.80 = 204.02 h** against the bound **205 h** (margin 0.98 h). The study total used so far is 120.48 h (24.22 plan charge + 96.27 registered). If the registered run uses its caps in full the study would charge 24.22 + the targeted rehearsal + 176.80 h; the expected charge, from the projections, is about 24.2 + 1 + 0.4 + 95.9 + 5 (M-ii alone) + 14.7 + 3.9 + 15.3 = about 160 h.

The caps are config values the code reads. A later change that only edits a cost figure needs no code edit, but it does need a new plan (the plan carries the caps), a new targeted rehearsal against that plan, and a new freeze record.

## The M-ii cell alone

- Measured: the counting rehearsal's M-ii cell, 8,000 updates, ran alone as the single task of its wave: 2,798 s, driver memory 42.5 GB. The two registered cells that finished (three at a time): 23,669 s and 25,535 s, 34.9 GB of driver memory each; peak resident memory 2.3 GB, which is why the 8 GiB resident guard never saw it.
- The update counts are equal (8,000), so the eightfold difference is not panel size. A training cell's cost does not depend on the panels. The cause is three cells of about 35 GB each on a 48 GB machine (analytical: about 100 GB of demand).
- **Estimate for one cell alone at registered size, hypothetical:** 2,800 s x (0.86 to 1.35, the registered/counting ratios of the other stage-2 cells) = about 2,400 to 3,800 s (0.7 to 1.1 h). Upper bound from the records: the 25,535 s of a cell under thrash (7.1 h). The remaining four cells alone: about 3 to 4.5 h expected, 28.4 h bound.
- Checkpoint cadence is 500 updates (`engine.train_cell`, `checkpoint_every`); the three killed cells resume from their last checkpoint. The progress of each was not read (no checkpoint was opened).

## How the remaining cells resume

On resume `stage_cap_for` gives the stage what is left of the amended caps; `waves_of` returns the six M-ii cells as the third wave; `wave_workers` limits that wave to one worker, so the cells run one at a time. The two finished cells have result files and are skipped; each killed cell has a checkpoint and `engine.train_cell` resumes it ("resumed" in its record); the cell that never started starts fresh. Cell records and the stage markers carry no plan hash or freeze commit (`partt_real.py` writes `envelope` only; `partt_tasks.mark_complete`), so the completed gates and the 50 completed cells remain valid under the new plan; the freeze commit appears only in the stage manifest, rewritten at every invocation. The new plan keeps the same `run_dir`.

## The targeted rehearsal (clock and charge, hypothetical)

`partt_stages rehearse --kind targeted --run-dir <new rehearsal dir> --part-q-dir <Part Q dir>`: (d) the preflight; (c) the two checks with tiny workers; gates marked complete as not re-rehearsed; M1 and M-append at 200 updates (parents only); the M-ii cell to a cap of about 700 charged seconds (stopped, killed_cap, checkpoint on disk) and then resumed from its checkpoint to the calibrated U = 8,000, alone. Rehearsal seeds, stand-in panels, no outcome value read. Estimate: clock 1.0 to 1.3 h (M-ii about 2,400 to 3,900 s of it); charged 0.9 to 1.2 h; allowance 3.0 h (which also stops the run PAUSED if a lone cell is as slow as the thrashed ones). It sets the M-ii cost figure. The record is `rehearsal_targeted.json`; `freeze --targeted-rehearsal` reads it.

## The second freeze (steps for the lead; the code does the checks)

1. The registered run directory stays as it is.
2. Move the first freeze record aside by a commit (a `git mv` into `studies/p10is2/freeze/<attempt>/`, as Part Q did); `candidate-plan --supersede` moves the old plan to `freeze/superseded/`.
3. Zero the config `[stage_caps]`, `caps-config --apply` writes the amended caps and the total; `candidate-plan --supersede ... --manifests` with the extra entry `cap_amendment_record` (path and SHA-256 of `AMENDMENT_RECORD.json`) and `--charged-ledger` for measuring attempts 1 and 2 and the first counting rehearsal; commit.
4. The targeted rehearsal against that plan (the record pins its hash); then `freeze --counting-rehearsal <the FIRST counting record> --targeted-rehearsal <the targeted record>`. The freeze checks: the first counting record COMPLETE against the pre-amendment plan hash named in the amendment record; the targeted record COMPLETE against this plan with the five checks passed; the first freeze commit's plan and config differ from this plan and config only where `partt_amendment.plan_diff_problems` and `config_diff_problems` allow (the amended caps and total, the bound, the M-ii worker count, the admission threshold, the config hash, the allowance, the charge, the amendment's own files and hashes); the calibration record's hashes equal every non-exempt `studies/p10is2/*.py` file. Any other difference refuses.
5. A new Decision 2 naming the new freeze commit.

## Departures from ADR-0025 (for ruling 51 and disclosure)

1. **Section 7.1 rule 4** (no Part T training or scoring file changes after a calibration output; the freeze refuses calibration records whose hashes differ): six `studies/p10is2/*.py` files (the cap arithmetic, the runner, the task orchestration, the freeze and the new modules) are exempt from the comparison, named in the amendment record; no training, scoring, label or calibration file is. Calibration is not repeated.
2. **Section 10 item 3** (stage cap = 2 x projected time): the train and combined caps are set by cost projection, not by the rule (section 9 allows an extension on cost projections only). The lead's one-time extension to at most twice a cap (ADR line 463) covers train (1.66x) but not combined (3.7x); the human lead's word covers both.
3. **Section 10 item 5** (a counting rehearsal against the exact plan file, shown COMPLETE for every stage): the second freeze rests on the first counting rehearsal against the pre-amendment plan and a **targeted** rehearsal against the amended plan. Gates, evaluate, controls, combined, recompute, analysis and report are NOT re-rehearsed against the amended plan; the first counting rehearsal rehearsed them against the pre-amendment plan, and the amendment changes none of their code or items (checked by the plan and config difference checks). Gates and the 50 cells have already run in the registered run.
4. **A second freeze record and a second Decision 2**; the first record is kept under another name.
5. **Resume** of a registered run directory whose cells were trained under the first freeze commit (items, seeds, training and scoring code unchanged).
6. **The bound** 95.68 (ruling 41), 151 (ruling 46) and now 205 charged hours (the human lead's answer above, read by the lead as a yes).
7. **Memory admission** looks at free system memory, not at MPS driver memory (not measurable per process here): a worker that grows after it starts is not seen. It is a limit, not a guarantee. The M-ii wave's one worker is the real protection.
8. **The charged-time cap check** (`runner.py`) replaces the wall-clock comparison inside a wave that audit 16 found; it is the registered text's meaning (charged time is the sum over workers). A wave is now stopped as soon as the charged time of its workers reaches the cap.
9. The targeted rehearsal marks `gates` complete in its own directory without running them, and trains M-ii's parents at 200 updates (the cell's cost does not depend on its parent's content).

## Tests (CPU, niced; measured)

- New file: 14 passed. Part T files with the MPS tests deselected: 360 passed and 5 failed before the helper fix (four tests of the 2026-11-21 caps-in-config state, which no one had re-run since the first freeze entered the caps, and one more of the same cause); after the fix, those files plus the config and budget-bound tests: 218 passed, 2 xfailed (the ruling-40 row and the new caps-entered row). Part Q files: 234 passed. `ruff` and `mypy src/arborlm` pass.

## Not done or not verified

- Nothing was run on the GPU and no rehearsal or registered stage was run by the implementer. The targeted rehearsal's entry point was tested only through its parts (the preflight is not exercised against a real run directory; the real launch path is untested until the lead runs it).
- The progress of the three checkpointed cells is unknown.
- The M-ii cost figures above are estimates until the targeted rehearsal has run.
