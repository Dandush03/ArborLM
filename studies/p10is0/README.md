# studies/p10is0 — P10-I-S0 (ADR-0023): the commands of the real rehearsal phase and what follows

Status: implementation self-checked and audited by the `arbor-auditor` subagent; no registered run is approved; nothing is frozen. Not Astra validation, not human approval.
Everything below is run from the worktree root with `uv run --locked python -m studies.p10is0.stages <command> ...` (written `stages` below). Every command has a timeout of its own; wrap each in `timeout <seconds>` yourself.
Estimates marked **(est.)** are mine from P10-S0's rates, not measurements. Anything marked **UNSURE** I did not verify on this machine.

## Two directories, set once

- `RUN` = a named, git-ignored directory inside the worktree, e.g. `experiments/p10is0-run`. All stages use the same one (ledger, manifests, draws, timing, cell records). Created on first use.
- `SEALED` = a directory **outside every git working tree and outside `/Users/daniellaloush/dandush03/ArborLM`** (symlinks are resolved and refused), e.g. `/Users/daniellaloush/ArborLM-sealed/p10is0`. Stage R's measurements, logs, snapshots, per-task files and the rehearsal draw's cell records live there. **Nobody opens it** (the lead, the implementer): a read is a disclosure that voids the blindness claim for that cell type. **UNSURE:** that this path is acceptable on your disk layout; the command refuses a bad one and says why.
- The code must not change from the start of Stage R. Any change after `freeze/durations.json` exists is an ENGINEERING STOP (exit 4); a change before it needs `--cause-file results/<something>.md` and starts a repeat on the spare draws.

## Sequence

| # | Command | Where output goes | Expected duration | Quiet machine? |
|---|---|---|---|---|
| 0 | `stages platform` | stdout (platform record) | seconds | no |
| 1 | `stages rehearse --run-dir RUN --phase real --cell-type 2K/4K --exposures 512 --sealed-dir SEALED` | `RUN/rehearsal_real.json` (whitelisted: status, seconds, memory, item count, platform); the rehearsal draw's cell records go to `SEALED/sealed/rehearsal/` | 10–20 min **(est.)**: generates and G1-checks the rehearsal draw, then times and trains each arm at real size for 512 exposures | no |
| 2 | `stages generate --run-dir RUN --cap-hours 3` | `RUN/draws/<set>/data_manifest.json`, `RUN/draw_plan.json` (replacements by reserve; fewer than ten passing is an engineering stop) | 1–3 h **(est., UNSURE)**: 14 draws, G1 on both fact sets, six workers | no |
| 3 | `stages quiet-check` then `stages timing --run-dir RUN --cap-hours 3` | `RUN/timing/` (attempts, rates, memory peaks) | quiet read 1 min; then about 15 min quiet plus about 30 min with twelve busy processes **(est.)** | **YES, stage 3 only.** It reads the load average every 10 s for 60 s (every sample at most 2.0, no other study's process alive) BEFORE its workers start, and again at the end. If not quiet it exits 3 and records the attempt (never used); run it again later. Three attempts within 24 h, then PAUSED — MACHINE NOT QUIET |
| 4 | `stages stage-r --run-dir RUN --sealed-dir SEALED --events-dir results/p10is0-freeze-<date>` | measurements and per-task files in `SEALED`; `studies/p10is0/freeze/durations.json` (only e*, T, SHOWN or not, flags, extension decisions, code identity); `EVENT_<n>.md` files in the results directory for the events of section 5.2 | 12–19 h worst case with one task per run **(est.: `ladder.stage_r_makespan_hours`)**; it prints nothing until the end. Resumable: run the same command again after a pause (exit 5) | no |
| 5 | `stages a0-memory --run-dir RUN` | `RUN/timing/a0_memory.json` (time and memory only); its records go to `SEALED` | about 2 h **(est.)**: one A0 cell at the longest frozen T of series M on the rehearsal draw | no |
| 6 | `stages caps --run-dir RUN` | `studies/p10is0/freeze/stage_caps.json` (charged hours so far + twice the projection at the larger of quiet and busy rates) | seconds | no |
| 7 | `stages seed-gate` | stdout (`RESULT: PASS` of the registry checker copy) | about 1–2 min | no |
| 8 | `stages candidate-plan --run-dir RUN` | `studies/p10is0/freeze/plan.json` (holds `stage_r_projection` and the draw manifests' hashes; the command prints the file hash and the cell count) | seconds | no |
| 9 | `stages counting-rehearsal --out RUN/counting_rehearsal.json` | that file | seconds | no |
| 10 | `stages freeze --rehearsal RUN/counting_rehearsal.json --attest-sealed-unopened lead,implementer,auditor --sealed-dir SEALED` | `studies/p10is0/freeze/freeze_record.json` (the hash of every frozen input individually, the sealed files' hashes, the seed gate and the twelve spare values). Add `--disclosed-read <file>` for each sealed file the lead read, or `--seal-broken` | about 2 min (runs the registry checker) | no |

After step 10 the lead commits the freeze directory files and writes `results/p10is0-freeze-<date>/DECISION_2.md` naming the freeze commit. Registered stages then run only through the launch scripts: `studies/p10is0/launch/{main,x8-gate,x8,analysis,report,disclose}.sh <run-dir> <freeze-commit>`.

## Notes and things I am unsure of

- **Order of steps 6 to 8.** The ADR's order is plan, rehearsal, caps. The code needs `stage_caps.json` for the freeze but excludes it from the plan comparison, so caps first (as above) and then a candidate plan that records them works; I did not try the other order. `freeze` refuses provisional caps and a plan that differs from a re-derivation.
- **Working tree.** Stage R writes `freeze/durations.json` into the worktree (an untracked file). The registered stages need a **clean tree** at the freeze commit, so commit the freeze files before running `main.sh`; commit nothing between the start of a registered stage and its end.
- **Exit codes** (every command): 0 complete, 5 paused (a cap, the disk rule, the memory guard, identity, environment: run the same command again), 1 failed task (an item error: a bug, not a result; the analysis refuses), 2 refused (a precondition, the platform, a bad directory), 3 not quiet or an analysis stop, 4 engineering stop (code changed; worker count below one; a peak above 3 GiB per worker), 75 identity.
- **Memory and disk.** Worker count is `min(6, floor(9 GiB / largest measured peak))`, from stage 3, Stage R and step 5. The 110 GiB cap counts `RUN` plus `SEALED`; free space must stay above 50 GiB on both. Stage R's logs and snapshots are about 13 GiB at the base ceiling **(est.)**.
- **Wave sizes** in Stage R's public manifests (a task count and the wave's duration) show that some cell type decided or that a run went non-finite, not which.
- **Step 1** uses the 2K/4K cell type at 512 exposures only to check the real-size code path (data, backbone, timing, evaluation, the sealed records); its numbers are not a calibration and enter nothing. **UNSURE:** that 512 exposures is the length you want; any `--exposures` that makes `exposures x 2,048 / 128` an integer works.
- **Not run by me:** every command in this table at real size.
