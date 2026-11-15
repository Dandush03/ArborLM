# P10-S0 freeze procedure (ADR-0020 sections 10, 13, 14, 18)

Status: procedure only. Nothing in this directory is a freeze. `plan.json` and `stage_caps.json` do not exist until the freeze procedure writes them (step 9), and every registered stage refuses to
run without them. `arm_selection.json` (step 6) is the arm-selection record, produced by `studies.p10s0.arm_selection` from P9-II's committed records; it is part of the freeze and is recomputed by the
auditor (gate G10). **Step 8 (generation of the registered draws) and the freeze wait for the human lead's recorded acceptance of the P9-II outcome (ADR-0020 sections 11 and 18, condition 7).**
Astra review: NOT_PERFORMED. Nothing here has been run at real size.

## Order (each step before the next; the freeze commit is step 10)

1. Implementation, tests, the DRY stage (`uv run --locked python -m studies.p10s0.stages dry`), ruff, mypy, the full test suite. (Section 13 step 4.)
2. The pipeline check (section 10.1), on the check draw (data base 209001, init 2091): A0, A6, A7 at 2K/4K, three cells. Accuracies are not results and select nothing:
   `uv run --locked python -m studies.p10s0.stages check --stage-cap-seconds <cap>`.
3. Gates at real size on the rehearsal draw (data base 209101, init 2092) and the implementation audit (section 13 step 5), then the same gates on registered seeds before training (the `gates` launch
   script): `uv run --locked python -m studies.p10s0.stages gates --mode rehearsal --run-dir <dir> --arm-selection studies/p10s0/freeze/arm_selection.json --stage-cap-seconds <cap>`.
4. Analysis and report exercised on synthetic records of the whole registry (tests: every row of section 3.3, the override of section 3.4, the list of section 3.5, every class under both criteria,
   every consistency and replication label, every outcome row, missing, failed and non-finite cells, a replaced draw, each cut).
5. (Section 13 step 6) The arm-selection record: `uv run --locked python -m studies.p10s0.stages arm-selection --out studies/p10s0/freeze/arm_selection.json`. The auditor recomputes it from the ADR
   text (G10, which also re-runs Part 1 of `docs/reviews/p10-design-2026-11-15/adr-0020-review/c5_rev2_mapping_and_consistency.py` and cites the matching table cell).
6. The rehearsal, twice (section 10.3), on the rehearsal draw, six single-thread workers: alone, and with twelve other busy single-thread processes (the larger measured rate is used):
   `uv run --locked python -m studies.p10s0.stages rehearse --arm-selection studies/p10s0/freeze/arm_selection.json --stage-cap-seconds <cap>` and the same with `--busy-processes 12`.
   Then `... projection --rehearsal-alone <dir1> --rehearsal-busy <dir2> --arm-selection <record> --out <projection.json>`. The projection includes the per-task start-up time (the P9-II audit's B1),
   the memory peaks of training, evaluation and the pool task (M2; a block whose rehearsal peak exceeds 1.5 GiB per worker is NOT RUN — MEMORY), one entry per block configuration (M3), and, as
   information and not as a start condition, the rehearsed projection of WX and the probe at the most expensive candidate and whether the rule would hold after a Q1 that ran at its projection.
7. **Not before the human lead's recorded acceptance of the P9-II outcome:** generation, G1 and the draw plan, in the registered run directory under `/Users/daniellaloush/dandush03/ArborLM/experiments/`
   (study code P10S0), before the freeze commit: `sh studies/p10s0/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the thirteen registered and two reserve draws (all three fact sets
   each), G1-checks each and writes `draw_plan.json` (REPLACED BY RESERVE k; an exhausted reserve list makes the plan not ok and nothing runs).
8. Measure the wall time of one `analysis` and one `report` on synthetic full-registry records and take the gates wall time from the rehearsal-draw gates run.
9. Write the cap table (one source of truth, a pure function of the projection) and the plan:
   `... caps --projection <projection.json> --gates-wall-seconds G --analysis-wall-seconds A --report-wall-seconds R --generate-wall-seconds N --out studies/p10s0/freeze/stage_caps.json`;
   then the plan, written by a command from the files and never by hand:
   `... freeze-plan --run-dir <registered-run-dir> --arm-selection studies/p10s0/freeze/arm_selection.json --projection <projection.json> --out studies/p10s0/freeze/plan.json`.
   `plan.json` holds `arm_selection` {`path`, `sha256`}, `projection` {`path`, `sha256`} (its `arm_selection_sha256` must equal the record's hash; the command refuses otherwise), `stage_caps_sha256`, `run_dir`,
   `draw_plan` {`sha256`}, `data_manifests` {seed-set name: `sha256`} for all fifteen sets, and `before_q1_projected_seconds` {stage name: projected seconds} for the stages before Q1 that have not run.
10. One freeze commit with the freeze record (code hashes, arm-selection record hash, data identities, gates, caps, projections, cut 3 of section 10.4, launch commands, the lead's conditions of section 18).
11. Launch, in this order, each with `sh studies/p10s0/launch/<stage>.sh <registered-run-dir> <freeze-commit>`: `gates`, `q1`, `q1_gate`, `probe`, `wx`, `analysis`, `report`.

## The launch scripts

Each script takes exactly two arguments, the run directory and a commit, and passes its stage cap file (`--caps studies/p10s0/freeze/stage_caps.json`); the driver refuses any other path. Everything else
(caps per block configuration, arm-selection record, projection, draw plan, seeds, the headroom decision) comes from the frozen plan and the frozen cap table. The two arguments are guarded: the driver
refuses unless the working tree is clean, the commit is an ancestor of HEAD, `studies/`, the config, the ADR and `tests/test_p10s0_*` equal their content at that commit, the frozen inputs verify, and
every hash in `plan.json` holds for the run directory it names. The scripts are covered by the source digest. A test runs every script (argument checks) and asserts that each passes `--caps`.

## What the registered stages enforce

- Training and evaluation need `draw_plan.json` with `ok` true, a passed G1 for every draw they name, and a `gates.json` in which G1, G2, G4, G5, G6, G9 and G10 all passed.
- Q1 starts only under the headroom rule of section 10.4 (reading A): hours already charged + 2 x the rehearsed projection of Q1 and of the stages before Q1 that have not run is at most 16 hours; if not,
  cut 3 (one initialization seed per draw at 8K/16K); if not, nothing registered is run and the matter returns to the human lead. The decision is written to `q1_start.json`.
- After Q1, `q1_gate` computes the candidate by the fixed rule, re-evaluates the rule on WX and the probe with the candidate's rehearsed rates and the hours charged (cut 1: drop the probe; cut 2: drop WX),
  and applies the memory rule per block. `wx` and `probe` refuse unless the Q1 gate allows them. Each block's cap is the table's entry for its configuration (Q1: full or cut3; WX and the probe: the candidate).
- A block that reaches its cap is stopped and is INCOMPLETE; a failed cell is kept and not re-run; no setting is changed after a start.
