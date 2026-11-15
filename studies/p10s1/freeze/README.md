# P10-S1 freeze procedure (ADR-0021, design revision 4: sections 10, 11 and 15)

Status: procedure only. Nothing in this directory is a freeze: `plan.json` and `stage_caps.json` do not exist until the lead's `freeze` command writes them, and every
registered stage refuses to run without them. Implementation, calibration and rehearsal are approved by the lead (section 15); **the registered run is NOT approved**
(it needs a clean implementation audit, a rehearsal that satisfies the twofold headroom rule under the cap in force, this freeze, and a separate recorded decision 2).
Astra review: NOT_PERFORMED. No human approval is recorded for the cap; the cap in force is the config value `resources.cap_hours` of `configs/p10s1_capacity.toml`
(16.0, raised from 12.0 by the human lead as relayed by the coordinator; the ADR now says 16; the lead may change it, and the freeze refuses a projection computed under a different value).

## Order (each step before the next; the freeze commit is step 12)

All commands are `uv run --locked python -m studies.p10s1.stages <command> ...` from the repository root. Run directories live under the main checkout's git-ignored
`experiments/` (study code `P10S1`); one ledger `experiments/P10S1-ledger.json` is charged by every stage (calibration, rehearsal, registered stages).

1. Code passes the implementation audit. `uv run --locked pytest tests/test_p10s1_*.py`.
2. Calibration (calibration draws `p10s1-cal-1` and `-2`, initialization seed 2191; never registered seeds), section 10.1 items 0 to 3, 46 runs (50 with the overload row's
   U_P calibration, `--with-overload`, only if the load rule of item 0 calls for it): `calibrate --stage-cap-seconds <cap>`. It writes `calibration.json`: the load table, the
   load rule's decision (GRID_STANDS, OVERLOAD_ROW or RETURN_TO_LEAD), cut-3 eligibility, the U_P check, the H8 report, D-OQ's learning rates (a tie within 0.02 is
   **not** resolved by code: `dense_tie_needs_lead`), and `returns_to_lead`. Any non-empty `returns_to_lead` goes to the human lead (section 13 item 1); nothing proceeds.
3. Generate the rehearsal draw and G1-check it: `generate --mode rehearsal --run-dir <rehearsal-dir> --stage-cap-seconds <cap>`. Its measured wall time is the basis of the registered
   generation cap (step 9a) and of the projection's generation line (five times it, charged before the freeze).
4. Gates at real size on the rehearsal draw (section 8.1: before the freeze and again on registered seeds before training): `gates --mode rehearsal --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. A harness error is reported in `harness_errors`, separately from a gate failure.
5. Rehearsal, **bound to the calibration record** (all 30 configurations, 38 with the overload row, at real size for 64 updates and one full evaluation each, plus the
   baselines, six workers): `rehearse --run-dir <rehearsal-dir> --calibration <calibration.json> --stage-cap-seconds <cap> [--overload-u-p <U_P>]`. Rehearsal records
   follow the whitelist (time, memory, finiteness, shapes, counts, identity); no loss or accuracy is written or displayed.
6. Isolated timing part (one process, nothing else running; refused above a load average of 1.0, retried up to three times): `timing --mode rehearsal --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. It writes `timing.json` (CPU seconds per update for every arm and slot count: the measured cost of the matched-compute plan).
7. Analysis and report on synthetic records of the whole registry (missing, failed and non-finite cells, a failed gate): `synthetic --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. It writes `synthetic.json` (the wall time of one analysis and one report, which bound those stages' caps).
8. The projection, the headroom rule and the cuts: `project --run-dir <rehearsal-dir> --calibration <calibration.json> --timing <timing.json> --gates <gates.json> --synthetic
   <synthetic.json>`. It writes `projection.json`: rates with task start-up time, the memory rule **including evaluation peaks**, the two cost tables, the matched-compute plan, the
   plan chosen by the cuts of section 10.3 in their fixed order (seed block on draw 2, on draw 1, D-OQ at 8K/64K, at 32K/16K, each only where cut 3 permits), the headroom proof
   (charged so far + 2 x remaining <= cap), and the cap table of every configuration. If the headroom rule does not hold after the allowed cuts, or the memory rule fails, the record
   carries the return to the human lead (raise the cap, or shorten the run lengths: a new design revision) and nothing is chosen.
9a. `set-generation-cap --run-dir <rehearsal-dir>` writes twice the rehearsal draw's measured generation and G1 time (rounded up to 10 s) into `[generation]` of
   `configs/p10s1_capacity.toml`, clears its `provisional` flag and may set the registered table size (`--generation-table-facts`); commit the result. The registered generation refuses
   while the cap is provisional and takes no cap from the command line; the freeze refuses while it is provisional or the table size differs from the plan's.
9. Registered generation and G1 (allowed before the freeze commit by the explicit `--i-understand-freeze-time` that the fixed script passes; the code commit must equal a clean
   HEAD): `sh studies/p10s1/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the five draws `p10s1-draw-1 .. 5` and writes no plan (there are no reserve draws).
10. Lane L status (section 5.6) is derived from S0's recorded outcome, not typed: pass `--s0-record <json>` (`outcome`, `candidate`, `overload_qualified`) to the freeze, which prints S0's
    status line (K7(c), section 13 item 5; default `S0 NOT YET DECIDED` without a record) and lane L's status. **Lane L is not implemented**: F-LA is S0's frozen candidate and S0's code is
    not in this tree, so `freeze --lane-l` is refused. If S0 qualified an interface before the freeze so that the lane would run, the freeze refuses and the question returns to the
    lead (ADR-0021 section 22 (b)); nothing is printed OMITTED in that case.
11. Write the freeze files: `freeze --run-dir <registered-run-dir> --projection <projection.json> --calibration <calibration.json> --timing <timing.json> --gates <gates.json>
    [--s0-record <json>] [--no-loaded-transitions "<transition>,..."]`. It refuses unless the projection has no return to the lead, every binding hash holds, the
    cap in the config equals the cap of the projection, the memory rule holds and the five draws have a passed G1 record; it writes `plan.json` and `stage_caps.json` here,
    deterministically (a pure function of its inputs).
12. Write the section 8.1 / 11 freeze record (code hashes, calibration, data identities, gates, caps, launch commands, cuts) and make **one freeze commit** containing it, `plan.json`
    and `stage_caps.json`. Nothing may be edited after it: every registered stage compares `studies/`, the config, the ADR and `tests/test_p10s1_*` with that commit.
13. Decision 2 (the single registered run) is the lead's, **recorded in a committed file outside the hashed specification, `results/p10s1-freeze-<date>/DECISION_2.md`, that names
    the freeze commit** (ADR-0021 section 22 M4: the ADR is hashed into the freeze identity and `check_preconditions` compares it with the freeze commit, so it cannot be edited after the
    freeze; it is amended with Decision 2 after the registered run). Every registered stage refuses unless such a file is committed and names the freeze commit; `results/` is not among the
    paths compared with the freeze commit. Before anything registered runs, only if the audits end with no open blocker or major, nothing
    changed after calibration except what section 8 allows, the headroom rule holds and no registered seed has been observed.
14. Launch, in this order, each with `sh studies/p10s1/launch/<stage>.sh <registered-run-dir> <freeze-commit>`:
    `gates`, `train`, `evaluate`, `timing`, `simulate`, `analysis`, `report`.

## The launch scripts (section 10.3: each registered stage is started by a fixed script that is part of the freeze)

Each script takes exactly two arguments, the run directory and a commit, and everything else comes from the frozen plan and the frozen cap table (`stage_caps.json`: one entry per
possible configuration; a stage whose configuration has no entry refuses). Every expansion is quoted and no argument is re-parsed by the shell. The driver refuses unless the working
tree is clean, the commit is an ancestor of HEAD, `studies/`, the config, the ADR and `tests/test_p10s1_*` equal their content at that commit, the frozen inputs verify and every hash in
`plan.json` holds for the run directory it names. `generate.sh` is run before the freeze; its cap per draw is the config value `[generation].cap_seconds` (step 9a), not a figure typed or written in the script.
The scripts are covered by the source digest. No registered stage is launched by a typed command.

**Overrides are refused.** The driver (`registered <stage>`) accepts only `--run-dir`, `--freeze-commit` and `--caps` (which must name the frozen table); `--stage-cap-seconds`,
`--ledger-root`, `--experiments-root`, `--rss-worker-bytes`, `--rss-aggregate-bytes`, `--only`, `--repo`, `--workers` and every other option are refused (exit 2). `--mode registered` is
reached only through `registered <stage>`, the worker entry point and `generate`; a registered worker needs the frozen plan and the digest the driver verified (`--freeze-plan-sha256`).

**Run the registered stages from a worktree pinned to the freeze commit.** `check_preconditions` requires the whole `studies/` tree, the config, the ADR and `tests/test_p10s1_*` to equal
their content at the freeze commit, so code merged into `studies/` afterwards (S0 or S2 work, for example) would stop every registered stage. Make a worktree at the freeze commit (plus the
commit that records Decision 2, which touches only `results/`) and run the launch scripts there; the run directory and the ledger live under the main checkout's git-ignored `experiments/`
(audit m9).

## The end-to-end exercise on test seeds (before the freeze)

`uv run --locked python -m studies.p10s1.e2e [--workdir DIR]` runs the whole registered sequence through the real launch scripts in a throwaway clone: the DRY prerequisites,
`set-generation-cap`, `generate.sh`, `freeze`, the freeze commit, Decision 2, and `gates.sh` to `report.sh`, with refusal probes before the freeze, before Decision 2 and for a typed
override. The test-only switch `P10S1_TEST_SEEDS=1` makes the registered driver accept only `p10s1-test-0..4` (the five test sets, synthetic backbone, DRY sizes) and never a registered
draw; without it only `p10s1-draw-1..5` are accepted. Everything is tiny-size and synthetic; it measures nothing (ADR-0021 section 22 M8). It creates no virtual environment (the clone is source files only and uses the current interpreter) and deletes the clone and outputs when it ends, keeping only a log folder and `E2E_SUMMARY.json`. `tests/test_p10s1_e2e.py` runs it only with `P10S1_E2E=1`; the lead runs it explicitly before the freeze.

## What the registered stages enforce

- `train` needs the gates record with G1, G2 and G4 to G9 passed, and the five draws with a passed G1; a cell outside the frozen registry is refused (`RegisteredRefused`).
- A stage refuses to start if the remaining cap (config value, charged-time ledger) is below its stage cap (`LedgerRefused`), and is stopped at its cap (the study is then S1-INCOMPLETE).
- `train` and `evaluate` refuse (NOT RUN — BUDGET (MEMORY)) if twice the largest measured peak, evaluation peaks included, exceeds 3 GiB per worker or 18 GiB aggregate.
- `evaluate`, `timing`, `simulate` and `analysis` need the previous stage's manifest; `report` needs `analysis.json`. Training and evaluation never overlap a timing stage.
- A failed cell is kept and not re-run; the analysis then reports S1-INCOMPLETE and no outcome (the denominator is never reduced). No stage is re-run with changed settings.
