# P10-S1 freeze procedure (ADR-0021, design revision 5: sections 10, 11 and 25.12)

Status: procedure only. Nothing in this directory is a freeze: `plan.json` and `stage_caps.json` do not exist until the lead's `freeze` command writes them, and every
registered stage refuses to run without them. Implementation, calibration and rehearsal of revision 5 are decided by the lead (section 25.12, Decision 1; revision 4's approval does not carry over and its freeze does not carry over); **the registered run is NOT approved**
(it needs a clean implementation audit, a rehearsal that satisfies the twofold headroom rule under the cap in force, this freeze, and a separate recorded decision 2).
Astra review: NOT_PERFORMED. No human approval is recorded for the cap; the cap in force is the config value `resources.cap_hours` of `configs/p10s1_capacity.toml`
(16.0, raised from 12.0 by the human lead as relayed by the coordinator; the ADR now says 16; the lead may change it, and the freeze refuses a projection computed under a different value).

## Order (each step before the next; the freeze commit is step 12)

All commands are `uv run --locked python -m studies.p10s1.stages <command> ...` from the repository root. Run directories live under the main checkout's git-ignored
`experiments/` (study code `P10S1`); one ledger `experiments/P10S1-ledger.json` is charged by every stage (calibration, rehearsal, registered stages).

1. Code passes the implementation audit. `uv run --locked pytest tests/test_p10s1_*.py`.
1a. Timing preview (item 0a; time and memory only; refused while a process of `studies.p10s0` or `studies.p10s2` is alive; the check is recorded in the stage manifest):
   `timing --mode rehearsal --preview --run-dir <calibration-dir>`. It writes `timing_preview.json` (wall and CPU seconds per update and peak memory of every arm and slot count through the
   whitelist validator, the projected wall time of each calibration item at six workers and each item's cap: twice the projection).
2. Calibration (calibration draws `p10s1-cal-1` and `-2`, initialization seed 2191 on draw 1 and 2193 on draw 2; never registered seeds), section 10.1, 70 runs, in this order, all in one
   `<calibration-dir>`; each run starts once and is never re-run; a failed run or a run stopped at its item cap is kept and is an input to the rules:
   `calibrate --items load,row-up --timing <timing_preview.json> --run-dir <calibration-dir>` (items 0b and 1: 10 + 12 runs);
   `calibrate --finalize-items load,row-up --run-dir <calibration-dir>` (U_L of 8K/1K, 32K/4K and 2K/256, U_P of each row, the returns; **items 2 and 3 do not start while a return is open**);
   `calibrate --items h8,dense --timing <timing_preview.json> --run-dir <calibration-dir>` (items 2 and 3 at the row U_P just fixed: 8 + 40 runs);
   `calibrate --finalize --run-dir <calibration-dir>`. It writes `calibration.json`: U_L per loaded cell and for 2K/256 (or '256 NOT MEASURED — NOT FULL WITHIN CEILING'), T-OQ PREDICTED NOT
   LOADED flags, U_P per row, H8's annotations, D-OQ's rate per unit (EDGE BY TIE-WALK recorded), the measured six-worker training seconds per update of every configuration, the charged
   seconds, and `returns_to_lead`. Any non-empty `returns_to_lead` goes to the human lead; nothing proceeds.
3. Generate the rehearsal draw and G1-check it: `generate --mode rehearsal --run-dir <rehearsal-dir> --stage-cap-seconds <cap>`. Its measured wall time is the basis of the registered
   generation cap (step 9a) and of the projection's generation line (five times it, charged before the freeze).
4. Gates at real size on the rehearsal draw (section 8.1: before the freeze and again on registered seeds before training): `gates --mode rehearsal --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. A harness error is reported in `harness_errors`, separately from a gate failure.
5. Rehearsal, **bound to the calibration record** (all 31 configurations (30 without 2K/256) at real size for 64 updates and one full evaluation each, plus the
   baselines, six workers): `rehearse --run-dir <rehearsal-dir> --calibration <calibration.json> --stage-cap-seconds <cap>`. Rehearsal records
   follow the whitelist (time, memory, finiteness, shapes, counts, identity); no loss or accuracy is written or displayed.
6. Isolated timing part (one process, nothing else running; refused above a load average of 1.0, retried up to three times): `timing --mode rehearsal --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. It writes `timing.json` (CPU seconds per update for every arm and slot count: the measured cost of the matched-compute plan).
7. Analysis and report on synthetic records of the whole registry (missing, failed and non-finite cells, a failed gate): `synthetic --run-dir <rehearsal-dir>
   --stage-cap-seconds <cap>`. It writes `synthetic.json` (the wall time of one analysis and one report, which bound those stages' caps).
8. The projection, the headroom rule and the cuts: `project --run-dir <rehearsal-dir> --calibration <calibration.json> --timing <timing.json> --gates <gates.json> --synthetic
   <synthetic.json>`. It writes `projection.json`: rates with task start-up time, the memory rule **including evaluation peaks**, the two cost tables, the matched-compute plan, the contention ratio c (the larger of the rehearsal's and the calibration's six-worker over isolated wall seconds per update, never below 1.0), the plan chosen by the cuts of section 10.3 in their fixed order (seed block on draw 2, on draw 1, D-OQ at 8K/16K), C_need = charged + 2 x remaining (training from isolated rates x c, evaluation from rehearsed seconds per snapshot, longest first on six workers), the computed cap (C_need rounded up to the hour, at most C_max = `resources.cap_max_hours`) and the cap table of every configuration. If C_need exceeds C_max after the three cuts the record says NOT STARTED: BUDGET and returns to the human lead; if the memory rule fails the record carries that return; nothing is chosen.
8a. `set-cap --projection <projection.json>` writes the computed cap into `resources.cap_hours` of the config (refused without a computed cap or above C_max); commit the result. The freeze refuses unless the config's cap is the projection's computed cap.
9a. `set-generation-cap --run-dir <rehearsal-dir>` writes twice the rehearsal draw's measured generation and G1 time (rounded up to 10 s) into `[generation]` of
   `configs/p10s1_capacity.toml`, clears its `provisional` flag, records whether the figure was measured (with the manifest's sha256) or typed (`--generation-seconds`: recorded as typed, and the freeze refuses it outside the test switch) and may set the registered table size (`--generation-table-facts`); commit the result. The registered generation refuses
   while the cap is provisional and takes no cap from the command line; the freeze refuses while it is provisional or the table size differs from the plan's.
9. Registered generation and G1 (allowed before the freeze commit by the explicit `--i-understand-freeze-time` that the fixed script passes; the code commit must equal a clean
   HEAD): `sh studies/p10s1/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the five draws `p10s1-draw-1 .. 5` and writes no plan (there are no reserve draws).
10. Lane L status (section 5.6) is derived from S0's recorded outcome, not typed: pass `--s0-record <json>` (`outcome`, `candidate`, `overload_qualified`) to the freeze, which prints S0's
    status line (K7(c), section 13 item 5; default `S0 NOT YET DECIDED` without a record) and lane L's status. **Lane L is not implemented**: F-LA is S0's frozen candidate and S0's code is
    not in this tree, so `freeze --lane-l` is refused. If S0 qualified an interface before the freeze so that the lane would run, the freeze refuses and the question returns to the
    lead (ADR-0021 section 22 (b)); nothing is printed OMITTED in that case. Under the lead's ruling P1 this applies to ANY qualified interface (at 4,096 only, or at both sizes), whether or not the lane would run.
    Outside the test switch (and `--dry`) the freeze also refuses records marked DRY, a plan whose unit is not U_P = 8,192, and a calibration with open returns to the lead; `verify_plan` repeats the DRY and unit checks for every registered stage.
11. Write the freeze files: `freeze --run-dir <registered-run-dir> --projection <projection.json> --calibration <calibration.json> --timing <timing.json> --gates <gates.json>
    [--s0-record <json>] [--no-loaded-transitions "<transition>,..."]`. It refuses unless the projection has no return to the lead, every binding hash holds, the
    cap in the config is the cap the projection computed, the memory rule holds and the five draws have a passed G1 record; it writes `plan.json` and `stage_caps.json` here,
    deterministically (a pure function of its inputs).
12. Write the section 8.1 / 11 freeze record (code hashes, calibration, data identities, gates, caps, launch commands, cuts) and make **one freeze commit** containing it, `plan.json`
    and `stage_caps.json`. Nothing may be edited after it: every registered stage compares `studies/`, the config, the ADR and `tests/test_p10s1_*` with that commit.
13. Decision 2 (the single registered run) is the lead's, **recorded in a committed file outside the hashed specification, `results/p10s1-freeze-<date>/DECISION_2.md`, that names
    the freeze commit** (ADR-0021 section 22 M4: the ADR is hashed into the freeze identity and `check_preconditions` compares it with the freeze commit, so it cannot be edited after the
    freeze; it is amended with Decision 2 after the registered run). The file must contain the exact line `DECISION: RUN` and the full freeze commit hash; a file without that line, or with `DECISION: DO NOT RUN`, is refused, and the committed content decides. Every registered stage and every registered worker refuses unless such a file is committed; `results/` is not among the
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
reached only through `registered <stage>`, the worker entry point and `generate`; every registered worker (including `work generate`, which refuses a provisional generation cap and any override) re-checks for itself: the plan must be `studies/p10s1/freeze/plan.json` (not a typed file), and `check_preconditions`, `verify_plan` and `require_decision_2` run against the freeze commit passed through.

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

## Revision 5 additions

- The timing preview, the isolated timing, the throughput stage, the rehearsal and every registered stage refuse to start while a process of `studies.p10s0` or `studies.p10s2` stages is alive (ADR-0021 section 25.12 item 4); the freeze record states whether any was alive at the freeze and the lead confirms that P10-S0's last training stage has finished before Decision 2.
- Item caps are per item (twice the item's projected wall time at six workers) and bound training wall seconds; a run still running at its cap is stopped, kept and has no U_L.
