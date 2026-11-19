# Part Q: from the measuring rehearsal to the registered run

Self-check by the implementer, not independent review. `PENDING LEAD REVIEW` marks a choice the lead must confirm; `UNSURE` marks something I could not verify. Durations are **hypothetical** (analytical, from the rates of the measuring record at `P10IS2-Q-rehearsal-measure2-20261118`, measured on a loaded machine) unless marked measured.

Every command runs from the repository (the worktree the study runs from), with `UV_OFFLINE=1`. Variables used below:

```sh
REPO=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f   # UNSURE: the worktree you run the study from
EXP=/Users/daniellaloush/dandush03/ArborLM/experiments                                  # git-ignored
Q="uv run --locked --offline python -m studies.p10is2.partq.stages"
```

# ATTEMPT 3 (ADR-0025 addendum `docs/decisions/ADR-0025-addendum-part-q-attempt-3.md`): the sequence

Attempt 2 stopped at `outputs` on test (a) of the R-gloss-icl prompts. Attempt 3 carries its six completed stages (inputs, partition, qfit, qcheck, generation, regeneration, computed under freeze `55017df4616a81795918e21e0792fa742f77bdc4`) into a NEW run directory and runs only `reuse`, `regeneration` (the identity check, again), `outputs`, `analysis`. Same registered seeds, no re-draw. `AT2=$EXP/P10IS2-Q-registered2-20261118` (never written: only hashed as bytes), `R3=$EXP/P10IS2-Q-registered3-20261119`, `FZ2=55017df4616a81795918e21e0792fa742f77bdc4`. Durations are hypothetical (from attempt 2's recorded stage seconds and the rates of the measuring record) unless marked.

1. **Pre-freeze prompt check** (no teacher output, nothing sealed; needs the packages, like the ledger command; about 5 to 15 minutes; no quiet machine needed):
   `cd "$REPO" && sh studies/p10is2/launch/partq_prompt_check.sh "$EXP/P10IS2-Q-prompt-check-20261119.json"` (exit 0 and `required_ok: true` required). It recomputes the registered partition (a pure function of the corpus and the registered seeds; nothing drawn anew), builds the prompt TEXT of every E_A, E_B and D_cal item with EVERY in-vocabulary source word given a placeholder gloss (four kinds: letter, digit-initial, accented, apostrophe), runs test (a) with the amended rule, and sweeps every reference word type of the corpus as a gloss word between letter-, digit- and punctuation-initial source words. It decides the rule for the last newline from the tokenizer and records it. NOT covered (left to the registered `outputs` stage, which runs test (a) on the real prompts and stops on any mismatch): the lexicon's actual gloss words, which are target words of the accepted pools (teacher outputs, a product of the generation stage it must not read).
2. **The ledger pin.** The shared ledger changed on 2026-11-19 (another study appended 1,024 windows; hash `ba14c714…`; attempt 2 pinned `62f81116…`). Attempt 3 pins the PRESERVED copy `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-backups/panel_ledger.before-s6.json` (hash `62f81116…`, the file the reused stages ran against) by setting `paths.panel_ledger` in `configs/p10is2_partq.toml` to that path (the one hand edit of the config, committed; the live file is not read by any stage of attempt 3: `inputs` is not run, and `outputs` reads only this study's own windows, which are an unchanged prefix of both files). The freeze REFUSES unless the plan's pinned ledger hash equals the hash the earlier freeze's plan pinned (`reusecheck.check_ledger_pin`).
3. **Caps of attempt 3** (the rule of the addendum section 4 condition 5, by the one shared function `qplan.caps_proposal`): total = the charge so far (EVERY ledger: the measuring runs, every rehearsal, attempts 1 and 2) + 2 x the projection of the REMAINING stages only (`regeneration`, `outputs`, `analysis`, and `reuse`, projected as the measured `inputs` overhead: an upper bound, since `inputs` hashes more bytes than the reuse set); each remaining stage cap = 2 x its projection (whole-process formula of step 0 below). Needs a measuring record with `caps_formula` (the measuring rehearsal of step 0 below, through the entry point). The caps of the six reused stages are not set (0.0): they do not run.
   `cd "$REPO" && $Q caps-reset --reason "..."` (if caps are entered), commit; then
   `cd "$REPO" && $Q caps-config --measuring-rehearsal <measuring record> --attempt3 --charged-ledger <every Part Q charged_ledger.json, absolute> ... --apply`, commit.
4. **Inputs with the reuse block** (the existing inputs file is unchanged by this attempt): `cd "$REPO" && $Q reuse-file --source-run-dir "$AT2" --freeze-commit "$FZ2" --base-inputs "$EXP/<inputs file>.json" --out "$EXP/<inputs file attempt3>.json"`. It hashes every file of the six stages as bytes (inputs/, partition/, partition_counts.json, qfit/, qcheck/, generation/, regeneration/, regeneration.json and the six `stages/*.complete.json`), opens nothing sealed, writes nothing in `$AT2`.
5. **Candidate plan**: `cd "$REPO" && $Q candidate-plan --supersede --run-dir "$R3" --inputs "$EXP/<inputs file attempt3>.json" --charged-ledger <the same ledgers>`, commit. The plan lists every reused file with its SHA-256 as a frozen input, checked at the freeze and at the start AND end of every stage (a difference is PAUSED — IDENTITY), and records the charge before the freeze, which the registered cap check counts (`remaining = total - charge before the freeze - this run's charges`; attempt 2's code used the total less this run's charges only, 54,540 s where the rule allows 38,707 s).
6. **Counting rehearsal of attempt 3** (through the registered entry point, fresh process per stage, rehearsal draws; stages `reuse`, `regeneration`, `outputs`, `analysis`; a rehearsal reuse of a rehearsal run, here the measuring rehearsal's directory, whose six stages completed in rehearsal mode; ONE forced PAUSED — IDENTITY on a reused file, then the restore): `cd "$REPO" && sh studies/p10is2/launch/partq_rehearse.sh counting "$EXP/<new counting dir>" --reuse-source "$EXP/<measuring rehearsal dir>" --charged-ledger <ledgers>`. About 30 to 40 minutes. Needs a quiet machine (within_cap is checked).
7. **Freeze**: `cd "$REPO" && $Q freeze --measuring-rehearsal <record> --counting-rehearsal "$EXP/<counting dir>/rehearsal_counting.json" --attest-sealed-unopened lead,implementer,auditor` (or `--seal-broken`). For a plan that reuses stages it additionally: re-hashes every reused file; runs `reusecheck.confined_diff` against `$FZ2` and REFUSES unless every difference is confined (below); checks the ledger pin and the seeds; requires the attempt-3 counting record (every stage COMPLETE and within its cap, the forced identity stop on a reused file) and prints each stage's seconds against its cap. The freeze record lists the differences by file and definition and `requires_auditor_certification`.
8. **Decision 2** as in step 6 below, for the new freeze commit. The outcome text of attempt 3 must state that stages 1 to 6 were computed under freeze `55017df` and reused (addendum condition 6).
9. **Registered stages of attempt 3**, in this order (`FREEZE` the new freeze commit):
   ```sh
   cd "$REPO"
   for S in reuse regeneration outputs analysis; do
       sh studies/p10is2/launch/partq_registered.sh "$S" "$R3" "$FREEZE" || break
   done
   ```
   `reuse` (hash the reused files again, link inputs/partition/qfit/qcheck/generation and `partition_counts.json` into `$R3`, write the five completion records naming their source; no world, no package, about 30 s), `regeneration` (the identity check again, zero differing token sequences: attempt 2 charged 520 s), `outputs` (attempt 2 charged 819 s to the stop; the whole stage may take a little more), `analysis` (seconds: after a recorded engineering failure it now derives the row-1 label QUALIFICATION-ENGINEERING-FAILURE instead of refusing). A cap stop stays PAUSED: caps are frozen.

**How the allowed difference from freeze `55017df` is enforced** (`partq/reusecheck.py`, at the freeze, by code; not by trust): file by file over the frozen set of that freeze. A new file is allowed. A Python file is compared definition by definition by the dump of its syntax tree (comments and formatting do not count): a changed or removed definition is refused unless it is on the allow list of that path (whole files: `gloss.py` (the segment rule), `freeze.py`, `counting.py`, `plan.py`, `reuse.py`, `reusecheck.py`, `promptcheck.py`; by function: `step8.step_gloss`, `pipeline.hashes_of`, `pkgmanifest.verify_inputs`, `real_stages.{stage_outputs, write_manifest, require_prerequisites, run_stage, order_of, make_ctx, build_world}`, `stages.{build_parser, cmd_registered, main, REGISTERED_STAGES, ...}`, `real.{run_rehearsal, run_rehearsal_stage, run_registered_stage}`); added imports and definitions are allowed, a removed import or a changed module-level constant is refused. The config may differ only in `stage_caps`, `caps.provisional` and `paths.panel_ledger`; `common/`, `uv.lock`, `pyproject.toml` and the other launch scripts must be byte-identical. **What code cannot decide**: functions that the six reused stages EXECUTED and that were edited (`run_stage`, `require_prerequisites`, `write_manifest`, `verify_inputs`, `hashes_of`, `build_parser`, `cmd_registered`, `main`, and the launch script `partq_registered.sh`) are allowed by name and listed under `requires_auditor_certification`: that the edit inside them touches only the cap check, the stage order, the reuse stage or the analysis is for the independent auditor to certify from the diff. The same check run now (`experiments/_scratch/realdiff.py`) against `55017df` passes with exactly that list.

## Step 0. Correct the caps, then measure through the registered entry point

**Why.** The caps entered from `measure3` were twice the per-unit rate x units measured INSIDE one process with the world already built. The registered run (and the counting rehearsal) runs each stage in a FRESH process that builds the world first, and a stage's charge is the whole process. The counting rehearsal's `partition` took 391 s against a cap of 144 s (measured, `counting4`); the caps of the short stages cannot hold on the registered path. This is a correction of a cost projection made before any registered result exists, not a relaxation after an observation; the superseded values are kept in a record. The old measuring records (`measure2`, `measure3`: no `caps_formula`) stay readable and are refused for caps.

**Formula (`caps_formula = whole-process-v2`).** For each stage: projected seconds = measured per-process overhead + (measured per-unit rate x units). The overhead is the time the stage process spent building its world (`overhead_seconds`: input hashing, package manifest, corpus, student, teachers; `analysis` builds none). The rate is `(whole-process seconds - overhead) / units measured`. A stage cap is 2 x projected; the total is the pre-freeze charge plus 2 x all eight stages. `caps-proposal`, `caps-config` and the freeze's comparison call the same function. One overhead per stage PROCESS: the batches of a stage (generation, qfit, qcheck) are inside its one process and are counted by units (generation: sources; qfit, qcheck: items; regeneration: sources of its stored batches), never by processes; a stage that is paused and resumed pays the overhead again, and that is charged.

```sh
cd "$REPO" && $Q caps-reset --reason "caps came from in-process rates without the per-process overhead (counting4: partition 391 s vs cap 144 s)"
cd "$REPO" && git add -A configs studies/p10is2/freeze/superseded && git commit -S -m "P10-I-S2: Part Q caps reset by code (superseded values recorded)"
cd "$REPO" && sh studies/p10is2/launch/partq_rehearse.sh measuring "$EXP/P10IS2-Q-rehearsal-measure4-20261119" --inputs "$EXP/<inputs file>.json" \
    --charged-ledger <each earlier Part Q ledger, absolute>                                           # NEW directory name
```

- `caps-reset` moves the nine entered caps into `studies/p10is2/freeze/superseded/partq_caps_superseded_<UTC>.json` (with the reason, the config hash before, and the note above), sets the config back to `0.0` / `provisional = true`, and leaves a dated comment under `[stage_caps]` naming that record. It refuses once a freeze record exists and when the caps are not entered. A hand edit is never needed.
- The measuring rehearsal refuses to run while caps are entered (so no stage can stop on the cap it measures), builds its plan in its own run directory from the config and the inputs file (never under `freeze/`), runs `partq_ledger.sh rehearsal` then every stage as `partq_registered.sh <stage> <dir> - --rehearsal --rehearsal-kind measuring` in a fresh process (one generation block per capability, one Q_check block), and writes `<dir>/rehearsal_measuring.json` with `rates_seconds_per_unit`, `overhead_seconds`, `projection_units`, `units_measured`, `stage_process_seconds`, `caps_formula`.
- Duration, hypothetical: about 1 h of stage work plus one world build per stage process (`inputs` took 67 s in total in `counting4`; `partition`'s process took 391 s on a saturated machine), so about 1.2 to 2 h. **Needs a quiet machine**: the overhead and the rates become the caps.

## Step 1. Inputs file (by code)

```sh
cd "$REPO" && $Q inputs-file --out "$EXP/P10IS2-Q-freeze-inputs-20261118.json"
```

- Writes (once; refuses an existing file, so give a NEW name when you rerun it) the JSON for `candidate-plan --inputs`: every model and Tatoeba file under the durable downloads. Each file is first checked against P10-S2's constant (and the committed Tatoeba record); the entry then stores the file's REAL SHA-256 under `sha256` (what every stage re-hashes) and the upstream checksum under `upstream_checksum` with its kind in `upstream_checksum_kind` (P10-S2 pins 19 of the 33 files by git blob SHA-1, 40 hex; the first version stored those as "sha256", which made every stage refuse: fixed, tested un-stubbed), the two WikiText-2 parquet files (verified against ADR-0004's pins), the requirements file and ADR-0004 (both stored repo-relative and resolved against the repository the stage runs from, so the plan names no particular worktree), and under `package_manifest` the manifest of the durable package copy (names, versions, every file's hash, the tree hash, the lock packages it shadows).
- Every file entry is re-hashed at the start of every registered stage AND of the counting rehearsal (the same check, through `build_world` with the plan); a difference exits 75 (PAUSED — IDENTITY).
- Duration: UNSURE, about a minute (hashing about 1.5 GB plus 4,270 package files; the package manifest alone took 0.9 s in the audit, measured). Quiet machine not needed. Writes nothing under the repository.

## Step 2. Units, charge and caps (by code; nothing typed)

```sh
cd "$REPO" && $Q units-file --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure4-20261119/rehearsal_measuring.json" --out "$EXP/P10IS2-Q-freeze-units-20261118.json"
cd "$REPO" && $Q caps-proposal --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure4-20261119/rehearsal_measuring.json" --units "$EXP/P10IS2-Q-freeze-units-20261118.json"
cd "$REPO" && $Q caps-config  --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure4-20261119/rehearsal_measuring.json"            # prints the lines
```

- `units-file` writes the record's `projection_units` (both split pools generated to the end, the whole Q_check reserve, the whole regeneration subsample). `caps-proposal` prints projected seconds and the hours; without `--charged-hours` it uses the record's `charged_before_freeze_seconds`, which is exactly what the freeze compares against, so do not type a charge (the sum of the ledgers is already in the record, step 0). The rule is unchanged: each stage cap is 2 x its projected time, the total is the pre-freeze charge plus 2 x all stages, rounded up to 0.01 h. `analysis` (records only, no rate to measure) is projected at a fixed 60 s: `ANALYSIS_PROJECTED_SECONDS` in `partq/plan.py`, PENDING LEAD REVIEW.
- Projected seconds per stage are overhead + rate x units (see step 0); the old figures (generation about 38,500 s, 10.7 h) did not include the per-process overhead and are superseded. The new figures come from `measure4` and are printed by `caps-proposal`.
- **Caps are frozen: a batch stage whose cap is spent stays PAUSED, and the only way on is a recorded new freeze by the lead; no code path extends a cap.** (The same sentence is in the PAUSED message.) `partition`, `regeneration` and `analysis` have no guard between batches and can finish past their cap: their completion record then says `within_cap: false` and a warning goes to stderr, never silently.
- The caps entered earlier (`f882eb4`) are reset by `caps-reset` in step 0 (a recorded correction). Where the caps are entered: `configs/p10is2_partq.toml`, section `[stage_caps]`, the nine keys `inputs_hours` ... `total_hours`, and in `[caps]` `provisional = false`. By code:

```sh
cd "$REPO" && $Q caps-config --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure4-20261119/rehearsal_measuring.json" --apply
cd "$REPO" && git diff configs/p10is2_partq.toml          # only those ten lines
cd "$REPO" && git add configs/p10is2_partq.toml && git commit -S -m "P10-I-S2: Part Q stage caps from the measuring rehearsal"
```

- `--apply` refuses unless every cap is still `0.0` and `provisional` is `true`. The freeze refuses a config whose caps differ from the rule applied to the measuring record, and refuses a record that lacks a rate, an overhead or units for any of the eight stages, or that lacks `caps_formula` (an old in-process record).
- Tests: the config test reads the rule (all caps `0.0` while provisional; otherwise every cap set and the total not below the sum of the stage caps up to the 0.01 h rounding), so it needs no edit when the caps are entered.

## Step 3. Candidate plan

```sh
cd "$REPO" && $Q candidate-plan --run-dir "$EXP/P10IS2-Q-registered-20261118" --inputs "$EXP/P10IS2-Q-freeze-inputs-20261118.json"
```

- `--run-dir` is the REGISTERED run directory (git-ignored, must not exist yet): every registered stage must later be launched with exactly this path. Writes `studies/p10is2/freeze/partq_plan.json` once; after the inputs file changed, add `--supersede` (the existing candidate plan is moved to `freeze/superseded/`, never deleted). It pins the shared ledger by absolute path and SHA-256 (it must begin `62f81116…`; the command refuses a missing ledger or one without this study's 144 windows) and records the frozen-file hashes, the import walk, seeds, caps and the 2,000-item Q_fit etc.
- Prints the plan's SHA-256. Commit the plan (`git add studies/p10is2/freeze/partq_plan.json`; the tree must be clean for the next steps). Duration: under a minute; it runs an import walk. Quiet machine not needed.

## Step 4. Counting rehearsal

```sh
cd "$REPO" && sh studies/p10is2/launch/partq_rehearse.sh counting "$EXP/P10IS2-Q-rehearsal-counting3-20261118"     # a NEW directory name each time
```

- It drives the SAME entry point as the registered run: for each stage in the registered order it runs `partq_registered.sh <stage> <run-dir> - --rehearsal` in a FRESH process (the `-` stands for the freeze commit it does not have). The same launch script (per-stage environment), `stages work`, `real_stages.run_stage` (stage order, per-stage caps and the cumulative ledger of the plan, the stage-start check of the plan's inputs and package manifest, completion records, manifests), the same stage bodies. Documented overrides, and only these: no freeze commit or Decision 2; the plan is verified against its own run directory; mode `rehearsal` (seeds 2529xx, a candidate ledger made first by `partq_ledger.sh rehearsal`, sealed layout); `caps.rehearsal_generation_blocks` generation blocks per capability and one Q_check block; every stage runs whatever Q1-Q4 gave; ONE forced pause (`generation` with `--pause-after-batches 4` exits 4, the same command resumes it) and ONE forced identity difference (`qfit` with `--plan-file` naming a copy of the plan with one frozen hash altered exits 75 and writes nothing; then the real run).
- It runs BEFORE the freeze only: it refuses once a freeze record exists, refuses the plan's own run directory, and takes `-` as its commit; every record, manifest and ledger entry of a directory carries its mode and a registered stage refuses a directory holding a rehearsal record (and the reverse).
- Output `<run-dir>/rehearsal_counting.json` (names the plan's SHA-256; per-stage seconds against the plan's stage caps in `stages.<s>.within_cap`), per-process logs in `<run-dir>/logs/`, sealed values in `<run-dir>/sealed/`. A stage that exits otherwise than expected stops the rehearsal and the record says which (exit 2, record `status: INCOMPLETE`).
- Duration: about 1.5 h plus a world build per stage process (hypothetical; the rehearsal measures it); the candidate ledger step first. Cap 3.0 h. **Needs a quiet machine**. The freeze REQUIRES `within_cap: true` for every stage of this record and prints each stage's seconds against its cap. `seconds` is the stage's whole charge: the wall time of each of its processes from the start of `execute`, so the world build (corpus, student, teachers) is inside it and the interpreter start and the preconditions are not (a few seconds). Check `within_cap` of every stage in the record: the caps came from in-process rates and do not include the per-process world build (UNSURE whether the short stages, partition, regeneration, analysis, stay inside them; this run is the first to measure it). Its charge is in its own ledger, not in the caps' total: PENDING LEAD REVIEW.

## Step 5. Freeze

```sh
cd "$REPO" && $Q freeze --measuring-rehearsal "$EXP/P10IS2-Q-rehearsal-measure3-20261118/rehearsal_measuring.json" \
    --counting-rehearsal "$EXP/P10IS2-Q-rehearsal-counting-20261118/rehearsal_counting.json" --attest-sealed-unopened lead,implementer,auditor
```

- Attestation: `--attest-sealed-unopened lead,implementer,auditor` (all three; recorded, not verified by code) or, if any sealed value was opened, `--seal-broken` instead.
- A malformed rehearsal record is a refusal (exit 2 with a message), not a crash. Refuses unless: caps not provisional and equal to the rule on the measuring record; the plan equals a re-derivation; the import walk reaches only listed files; the plan's inputs hold the package manifest; the counting record shows all eight stages COMPLETE, one forced pause and resume, one forced identity pause and restore, and this plan's SHA-256; gate G9; the shared ledger exists in format `p10i-panel-ledger-v1` with its check passed; section 7 of the delegation record is on the branch. Writes `studies/p10is2/freeze/partq_freeze_record.json` once.
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

- A killed process (SIGKILL, power loss) is charged by the next launch of that stage from its start marker `stages/<stage>.running.json` (refreshed every 10 s by a heartbeat): a lower bound within about 10 s of the true time; a stage whose marker names a live process is refused.
- Every stage is one process (UNSURE of the speed-up of two workers: not implemented; R1 accepted for Part Q). Wall time of every process is charged to `<run-dir>/charged_ledger.json`, also when it stops.
- Stages other than `analysis` get the 28 packages from the verified durable copy by absolute path, offline, with `PYTHONDONTWRITEBYTECODE=1` (the launch script sets it); `analysis` runs on the lock alone.
- Any ending other than TEACHERS-QUALIFIED (DISJOINT or OVERLAPPING DRAWS) leaves Part T NOT STARTED (`partq/labels.py`).
