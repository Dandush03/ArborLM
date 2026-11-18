# Part Q: from the measuring rehearsal to the registered run

Self-check by the implementer, not independent review. `PENDING LEAD REVIEW` marks a choice the lead must confirm; `UNSURE` marks something I could not verify. Durations are **hypothetical** (analytical, from the rates of the measuring record at `P10IS2-Q-rehearsal-measure2-20261118`, measured on a loaded machine) unless marked measured.

Every command runs from the repository (the worktree the study runs from), with `UV_OFFLINE=1`. Variables used below:

```sh
REPO=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f   # UNSURE: the worktree you run the study from
EXP=/Users/daniellaloush/dandush03/ArborLM/experiments                                  # git-ignored
Q="uv run --locked --offline python -m studies.p10is2.partq.stages"
```

## Step 0. The measuring rehearsal must be run again (the one at measure2 cannot give caps)

The record at `measure2` has **no rate for `regeneration`**: its one generation block per capability ends DATA-EXHAUSTED and the pipeline skipped the regeneration check (measured: no `regeneration.json` in that run directory; `rates_seconds_per_unit` has no `regeneration`). The freeze and `caps-config` now refuse such a record. A rehearsal now runs and times the regeneration check whatever the draws label (`pipeline._run_all`, test `test_a_rehearsal_runs_and_times_the_regeneration_check…`). Resuming in the same directory would time only the stages that run in that process (a finished stage keeps no wall time in its record, so its rate would be missing), so run it fresh:

```sh
cd "$REPO" && sh studies/p10is2/launch/partq_rehearse.sh measuring "$EXP/P10IS2-Q-rehearsal-measure3-20261118" \
    --charged-ledger "$EXP/<earlier Part Q run dir>/charged_ledger.json" ...      # one option per earlier ledger, ABSOLUTE paths
```

- Output: `<run-dir>/rehearsal_measuring.json` (public keys only; `sealed/` is not to be opened), `<run-dir>/charged_ledger.json`.
- `--charged-ledger` adds that ledger's charge to `charged_before_freeze_seconds` (the pre-freeze charge the caps rule uses) and lists each ledger in `charged_ledgers`. Name every earlier Part Q ledger: `measure2`'s own (3,468 s, measured) and the ledger command's run directory if it wrote one (UNSURE which directory). The failed first attempt `P10IS2-Q-rehearsal-measure-20261118` wrote no ledger (it died before the charge; a failed rehearsal is now charged, but that one was not). Its wall time is not recorded by code: PENDING LEAD REVIEW whether to add an estimate by hand (it cannot be added by code).
- Duration: about 1 h (measured 3,369 s for the run that failed to measure regeneration, plus about 100 s for regeneration, hypothetical). Fixed cap 3.0 h. **Needs a quiet machine**: the rates become the caps (a loaded machine inflates them; the record lists `other_studies_alive`). The memory guard is 12 GiB per process.
- Exit 0 and a printed whitelist (timings, memory, counts, batches, generation items/s, stages). Nothing else is to be read before the registered analysis.

## Step 1. Inputs file (by code)

```sh
cd "$REPO" && $Q inputs-file --out "$EXP/P10IS2-Q-freeze-inputs-20261118.json"
```

- Writes (once; refuses an existing file) the JSON for `candidate-plan --inputs`: every model and Tatoeba file under the durable downloads (path and SHA-256, verified against P10-S2's constants and the committed Tatoeba record), the two WikiText-2 parquet files (verified against ADR-0004's pins), the requirements file, ADR-0004's working-tree hash, and under `package_manifest` the manifest of the durable package copy (names, versions, every file's hash, the tree hash, the lock packages it shadows).
- Every file entry is re-hashed at the start of every registered stage; a difference exits 75 (PAUSED — IDENTITY).
- Duration: UNSURE, about a minute (hashing about 1.5 GB plus 4,270 package files; the package manifest alone took 0.9 s in the audit, measured). Quiet machine not needed. Writes nothing under the repository.

## Step 2. Units, charge and caps (by code; nothing typed)

```sh
cd "$REPO" && $Q units-file --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json" --out "$EXP/P10IS2-Q-freeze-units-20261118.json"
cd "$REPO" && $Q caps-proposal --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json" --units "$EXP/P10IS2-Q-freeze-units-20261118.json"
cd "$REPO" && $Q caps-config  --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json"            # prints the lines
```

- `units-file` writes the record's `projection_units` (both split pools generated to the end, the whole Q_check reserve, the whole regeneration subsample). `caps-proposal` prints projected seconds and the hours; without `--charged-hours` it uses the record's `charged_before_freeze_seconds`, which is exactly what the freeze compares against, so do not type a charge (the sum of the ledgers is already in the record, step 0). The rule is unchanged: each stage cap is 2 x its projected time, the total is the pre-freeze charge plus 2 x all stages, rounded up to 0.01 h. `analysis` (records only, no rate to measure) is projected at a fixed 60 s: `ANALYSIS_PROJECTED_SECONDS` in `partq/plan.py`, PENDING LEAD REVIEW.
- Rough figures (hypothetical, from the measure2 rates and units): partition 72 s, inputs 99 s, qfit about 1,000 s, qcheck about 730 s, **generation about 38,500 s (10.7 h)**, outputs about 355 s, regeneration about 100 s: about 11.3 h projected, caps about double.
- Where the caps are entered: `configs/p10is2_partq.toml`, section `[stage_caps]`, the nine keys `inputs_hours`, `partition_hours`, `qfit_hours`, `qcheck_hours`, `generation_hours`, `regeneration_hours`, `outputs_hours`, `analysis_hours`, `total_hours` (each `0.0` now), and in `[caps]` `provisional = true` becomes `false`. By code:

```sh
cd "$REPO" && $Q caps-config --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json" --apply
cd "$REPO" && git diff configs/p10is2_partq.toml          # only those ten lines
cd "$REPO" && git add configs/p10is2_partq.toml && git commit -S -m "P10-I-S2: Part Q stage caps from the measuring rehearsal"
```

- `--apply` refuses unless every cap is still `0.0` and `provisional` is `true`. The freeze refuses a config whose caps differ from the rule applied to the measuring record, and refuses a record that lacks a rate or units for any registered stage.
- Tests: the config test reads the rule (all caps `0.0` while provisional; otherwise every cap set and the total not below the sum of the stage caps up to the 0.01 h rounding), so it needs no edit when the caps are entered.

## Step 3. Candidate plan

```sh
cd "$REPO" && $Q candidate-plan --run-dir "$EXP/P10IS2-Q-registered-20261118" --inputs "$EXP/P10IS2-Q-freeze-inputs-20261118.json"
```

- `--run-dir` is the REGISTERED run directory (git-ignored, must not exist yet): every registered stage must later be launched with exactly this path. Writes `studies/p10is2/freeze/partq_plan.json` once (`--supersede` moves an old one aside). It pins the shared ledger by absolute path and SHA-256 (it must begin `62f81116…`; the command refuses a missing ledger or one without this study's 144 windows) and records the frozen-file hashes, the import walk, seeds, caps and the 2,000-item Q_fit etc.
- Prints the plan's SHA-256. Commit the plan (`git add studies/p10is2/freeze/partq_plan.json`; the tree must be clean for the next steps). Duration: under a minute; it runs an import walk. Quiet machine not needed.

## Step 4. Counting rehearsal

```sh
cd "$REPO" && sh studies/p10is2/launch/partq_rehearse.sh counting "$EXP/P10IS2-Q-rehearsal-counting-20261118"
```

- Runs every registered stage (inputs, partition, qfit, qcheck, generation with 2 blocks per capability, regeneration, outputs, analysis) against THE candidate plan file, one forced pause and resume, one forced PAUSED — IDENTITY and restore. Output `<run-dir>/rehearsal_counting.json` (names the plan's SHA-256); sealed values go to `<run-dir>/sealed/`.
- Duration: about 1.5 h (hypothetical: qfit 1,000 s + two generation blocks per capability about 3,600 s + the rest about 700 s); cap 3.0 h. **Needs a quiet machine** (its stages are checked against the computed caps). Its wall time is charged to its own ledger and is NOT in the caps' total (the total was fixed before it ran): PENDING LEAD REVIEW.

## Step 5. Freeze

```sh
cd "$REPO" && $Q freeze --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json" \
    --counting-rehearsal "$EXP/P10IS2-Q-rehearsal-counting-20261118/rehearsal_counting.json" --attest-sealed-unopened lead,implementer,auditor
```

- Attestation: `--attest-sealed-unopened lead,implementer,auditor` (all three; recorded, not verified by code) or, if any sealed value was opened, `--seal-broken` instead.
- Refuses unless: caps not provisional and equal to the rule on the measuring record; the plan equals a re-derivation; the import walk reaches only listed files; the plan's inputs hold the package manifest; the counting record shows all eight stages COMPLETE, one forced pause and resume, one forced identity pause and restore, and this plan's SHA-256; gate G9; the shared ledger exists in format `p10i-panel-ledger-v1` with its check passed; section 7 of the delegation record is on the branch. Writes `studies/p10is2/freeze/partq_freeze_record.json` once.
- Then (your acts): `git add studies/p10is2/freeze/partq_freeze_record.json && git commit -S -m "P10-I-S2: Part Q freeze"`. **That commit is the freeze commit**: `FREEZE=$(git rev-parse HEAD)` (the full 40 hex).

## Step 6. Decision 2

A committed file whose path matches `results/p10is2-partq-freeze-*/DECISION_2_PARTQ.md`, with the full 40-hex freeze commit anywhere in the text and a line that is exactly `DECISION: RUN`, for example `results/p10is2-partq-freeze-20261118/DECISION_2_PARTQ.md`:

```
freeze <the full 40-hex freeze commit>
DECISION: RUN
```

Commit it (`git add results/p10is2-partq-freeze-20261118 && git commit -S -m "P10-I-S2: Part Q Decision 2"`). Any other `DECISION:` line `DECISION: DO NOT RUN` makes every stage refuse. After this commit the worktree is frozen: no write of any kind in it while the registered run goes on (a commit during a run made 171 cells refuse in an earlier study); status goes in chat or another branch.

## Step 7. Registered stages, in this order, each with the launch script

```sh
cd "$REPO"
for S in inputs partition qfit qcheck generation regeneration outputs analysis; do
    sh studies/p10is2/launch/partq_registered.sh "$S" "$EXP/P10IS2-Q-registered-20261118" "$FREEZE" || break
done
```

Run them one at a time (the loop stops at the first non-zero exit). Exit codes: 0 complete (also `NOT RUN BY RULE`, the registered negative path: generation, regeneration and outputs do not run when a teacher fails Q1-Q4, and `analysis` then writes the NEGATIVE: QUALITY label); 2 refused (no completion record; run it again after fixing the cause); 4 PAUSED on its cap or memory guard (run the same command to resume; extending a cap is the lead's); 75 PAUSED — IDENTITY (a frozen file or input differs; restore it bit for bit and re-run).

| Stage | Output | Duration (hypothetical) | Quiet machine |
|---|---|---|---|
| inputs | `stages/inputs.complete.json`, `inputs/` (converted student, tokenizer record, G8 equivalence) | about 100 s | recommended |
| partition | `partition_counts.json` | about 70 s | no |
| qfit | `qfit/record.json` (Q1-Q3, per-item inputs) | about 1,000 s | **yes** |
| qcheck | `qcheck/teacher_*/result.json` (Q4) | about 730 s | **yes** |
| generation | `generation/` (accepted pools, draws label) | about 38,500 s (10.7 h) | **yes** (the longest; cap 2 x) |
| regeneration | `regeneration.json` | about 100 s | **yes** (zero token tolerance, no timing but charged) |
| outputs | `outputs/bundle`, `manifest.json`, teacher outputs on the panels | about 355 s | recommended |
| analysis | `qualification.json` (the registered label) | seconds | no |

- Every stage is one process (UNSURE of the speed-up of two workers: not implemented; R1 accepted for Part Q). Wall time of every process is charged to `<run-dir>/charged_ledger.json`, also when it stops.
- Stages other than `analysis` get the 28 packages from the verified durable copy by absolute path, offline, with `PYTHONDONTWRITEBYTECODE=1` (the launch script sets it); `analysis` runs on the lock alone.
- Any ending other than TEACHERS-QUALIFIED (DISJOINT or OVERLAPPING DRAWS) leaves Part T NOT STARTED (`partq/labels.py`).
