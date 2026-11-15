# P10-S0 freeze procedure (ADR-0020 sections 10, 13, 14, 18 and the addenda)

Status: procedure only. Nothing in this directory is a freeze until the freeze commit adds `plan.json` and `stage_caps.json` (both, or neither: no test asserts either is absent). Every registered stage refuses to
run without them, and without the freeze commit being the commit that added `plan.json`. `arm_selection.json` is the arm-selection record produced by `studies.p10s0.arm_selection` from P9-II's committed records;
it is part of the freeze and is recomputed by the auditor (gate G10). The human lead's acceptance of the P9-II outcome is recorded (ADR-0019 section 16; ADR-0020 addendum). Step 8 still needs a clean
implementation audit, a rehearsal that meets the twofold rule, and the lead's separate recorded decision (`results/p10s0-freeze-<date>/DECISION.md`, below). Astra review: NOT_PERFORMED.

## Nothing is recorded in the hashed specification after the freeze (the lead's ruling on M5)

- **The run decision** is the file `results/p10s0-freeze-<date>/DECISION.md`, outside every hashed path (the preconditions compare `studies/`, the config, ADR-0020 and `tests/test_p10s0_*` with the freeze
  commit; `results/` is not among them). It is committed before registered generation (the generation command refuses without it) and may be committed again after the freeze without stopping any stage.
  Nothing is recorded in ADR-0020 after the freeze commit: the ADR is amended with the run's records only after the registered run (after `report`).
- **The hour cap is fixed at the freeze.** A raise under the human lead's delegation can only be made before the freeze: at the rehearsal's headroom check, by changing `cap_hours` in the config and recording the raise
  in ADR-0020 (old and new cap, the measured projection that required it, what it protects), then the freeze commit. After the freeze the cap is fixed; the Q1 gate uses the frozen cap and applies the registered
  cuts; no raise is ever made after a registered seed has been observed.
- **The freeze must not hash anything designed to be written after it.** `plan.json` hashes only files that exist before the freeze (the arm-selection record, the projection, the cap table, the draw plan, the data
  manifests, the pinned auditor scripts). The ledger, gates, results and DECISION.md are written after it and are not hashed.

## Order (each step before the next; the freeze commit is step 10)

1. Implementation, tests, the DRY stage (`uv run --locked python -m studies.p10s0.stages dry`), ruff, mypy, the full test suite, and **the end-to-end exercise of the whole registered sequence through the real launch scripts
   on test seeds**: `uv run --locked python -m studies.p10s0.e2e --out <new-dir>` (one command; a throwaway clone; the TEST_PROFILE marker selects test seeds, tiny sizes and a synthetic backbone; exit 0 when the
   rehearsal, generation, `set-generation-cap`, gates, `projection` with cut 3 and a probe over the memory limit, `caps`, `generate.sh`, `freeze-plan`, the freeze commit, `gates.sh`, `q1.sh`, `q1_gate.sh`, `wx.sh`,
   `probe.sh` (refused), `analysis.sh`, `report.sh` and a refused second `q1.sh` behaved as expected). Repeat it after any change under `studies/`.
2. The pipeline check (section 10.1), on the check draw (data base 209001, init 2091): A0, A6, A7 at 2K/4K, three cells. Accuracies are not results and select nothing:
   `uv run --locked python -m studies.p10s0.stages check --stage-cap-seconds <cap>`.
3. Gates at real size on the rehearsal draw (data base 209101, init 2092) and the implementation audit (section 13 step 5). First generate the rehearsal draw (its three fact sets with G1), **timing it**:
   `uv run --locked python -m studies.p10s0.stages generate --mode rehearsal --run-dir <dir> --stage-cap-seconds <cap>`; then
   `uv run --locked python -m studies.p10s0.stages gates --mode rehearsal --run-dir <dir> --arm-selection studies/p10s0/freeze/arm_selection.json --stage-cap-seconds <cap>`.
   `gates.json` records `timing.per_draw_seconds` (the rebuild, hash check and G2 of one draw's three fact sets): the registered gates do this for thirteen draws.
4. **The generation cap** (the lead's ruling on item 2): `... set-generation-cap --generate-manifest <dir>/generate-p10s0-rehearsal/manifest.json` rewrites the `[generation]` block of
   `configs/p10s0_qualification.toml` to max(60 s, 2 x the measured generation time of the rehearsal draw). The block is provisional until then; registered generation and the freeze refuse while it is. Commit the config.
5. Analysis and report exercised on synthetic records of the whole registry (tests: every row of section 3.3, the override of section 3.4, the list of section 3.5, every class under both criteria, every consistency and
   replication label, every outcome row, missing, failed and non-finite cells, a replaced draw, each cut, the cut-3 label, the A5-D strings in every output).
6. The arm-selection record: `uv run --locked python -m studies.p10s0.stages arm-selection --out studies/p10s0/freeze/arm_selection.json`. The auditor recomputes it from the ADR text (G10, which also re-runs Part 1
   of `docs/reviews/p10-design-2026-11-15/adr-0020-review/c5_rev2_mapping_and_consistency.py` and cites the matching table cell; the freeze pins the hash of that script and of its sibling `c2_mapping_enumeration.py`,
   and G10 runs neither if a hash differs). The record also lists the auditor's own recomputation file and its sha256 (the freeze record template).
7. The rehearsal, twice (section 10.3), on the rehearsal draw, six single-thread workers: alone, and with twelve other busy single-thread processes (the larger measured rate is used; the lead rehearses with other
   studies' workers busy): `... rehearse --arm-selection studies/p10s0/freeze/arm_selection.json --stage-cap-seconds <cap>` and the same with `--busy-processes 12`. Then
   `... projection --rehearsal-alone <dir1> --rehearsal-busy <dir2> --arm-selection <record> --out <projection.json>`. The projection includes the per-task start-up time (the P9-II audit's B1), the memory peaks of
   training, evaluation and the pool task (M2; a block whose rehearsal peak exceeds 1.5 GiB per worker is NOT RUN — MEMORY), one entry per block configuration (M3), and, as information and not as a start
   condition, the rehearsed projection of WX and the probe at the most expensive candidate and whether the rule would hold after a Q1 that ran at its projection. Rehearsal and gates must be repeated after any change
   to `train.py`, `evaluate.py` or `model.py`.
8. Measure the wall time of one `analysis` and one `report` on synthetic full-registry records, and take the gates wall time and its per-draw part from the rehearsal-draw gates run (step 3). **The headroom rule counts the
   analysis and report time, doubled, as part of what is still to run at both evaluations (the lead's ruling on M6).**
9. Write the cap table (one source of truth, a pure function of the projection) and the plan, from files and never by hand:
   `... caps --projection <projection.json> --gates-wall-seconds G --gates-per-draw-seconds P --analysis-wall-seconds A --report-wall-seconds R --generate-wall-seconds N --out studies/p10s0/freeze/stage_caps.json`.
   The gates cap is 2 x (G + 12 P): thirteen draws x three fact sets (the lead's ruling on M8). Then, after registered generation (step 11):
   `... freeze-plan --run-dir <registered-run-dir> --arm-selection studies/p10s0/freeze/arm_selection.json --projection <projection.json> --out studies/p10s0/freeze/plan.json`.
10. **Freeze record template** (committed with the freeze; the lead approves it): code hashes, arm-selection record hash, data identities, gates, caps, projections, cut 3 of section 10.4, launch commands, the lead's
    conditions of section 18, the generation cap and its measurement, the pinned auditor scripts, the auditor's recomputation file and sha256, and **every printed string the ADR does not fix** (the lead's ruling on item 6),
    which the lead approves there: `FOURTH ARM: NONE — P9-II STAGE 2 <status>`; `FOURTH ARM: <arm> — P9-II CARRIED <arm>`; `NOT DEFINED (S0 NOT_EVALUATED)` and `NOT AVAILABLE (S0 NOT_EVALUATED)`;
    `OVERLOAD NOT RUN — NO CANDIDATE`; `OVERLOAD NOT_EVALUATED`; `RECORD-LENGTH-FREE VARIANT: NOT RUN — <status>` / `INCOMPLETE`; `NOT QUALIFIED IN S0` with its neutral sentence; the banner sentences about the acceptance
    of the P9-II outcome; the hypothesis table notes; `ADDRESS STABLE` non-finite counting; the block-status strings of section 8.7. The freeze commit adds `plan.json` and `stage_caps.json`.
11. **Registered generation** (before the freeze commit, with the tree clean at the code commit; it refuses without the recorded acceptance, without `results/p10s0-freeze-*/DECISION.md`, with a provisional generation
    cap, with a typed cap, or with any override): `sh studies/p10s0/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the thirteen registered and two reserve draws (all three fact sets each),
    G1-checks each and writes `draw_plan.json` (REPLACED BY RESERVE k; an exhausted reserve list makes the plan not ok and nothing runs). Run directories live under
    `/Users/daniellaloush/dandush03/ArborLM/experiments/` with study code P10S0.
12. Launch, in this order, each with `sh studies/p10s0/launch/<stage>.sh <registered-run-dir> <freeze-commit>`: `gates`, `q1`, `q1_gate`, `wx`, `probe`, `analysis`, `report`. **WX runs before the probe** (the lead's
    ruling on item 7): `probe` refuses while a WX block that is to run has no evaluation manifest.

## The launch scripts

Each script takes exactly two arguments, the run directory and a commit, and passes its stage cap file (`--caps studies/p10s0/freeze/stage_caps.json`); `generate.sh` passes `--generation-cap-from-config`. The registered
driver accepts no other option: `--stage-cap-seconds`, `--ledger-root`, `--experiments-root`, memory caps, `--synthetic-backbone`, `--only`, `--cut3`, `--restore-split` and every other option of the parser are refused,
whatever their value. No typed command defaults into registered mode, and `--mode registered` is refused on every command but `generate` and the driver. Every worker the driver starts re-verifies the frozen plan,
the freeze commit and the absence of overrides. The two arguments are guarded: the driver refuses unless the working tree is clean, the commit is an ancestor of HEAD **and is the commit that added `plan.json`**,
`studies/`, the config, the ADR and `tests/test_p10s0_*` equal their content at that commit, the frozen inputs verify, and every hash in `plan.json` holds for the run directory it names. The scripts are covered by the
source digest. A test runs every script's argument check and parses its command line with the real parser; the end-to-end exercise runs them.

## What the registered stages enforce

- Training and evaluation need `draw_plan.json` with `ok` true, a passed G1 for every draw they name, and a `gates.json` in which G1, G2, G4, G5, G6, G9 and G10 all passed.
- Q1 starts only under the headroom rule of section 10.4 (reading A), with the rehearsed analysis and report time reserved: hours already charged + 2 x the rehearsed projection of Q1, of the stages before Q1 that have not
  run, and of the analysis and report is at most 16 hours; if not, cut 3 (one initialization seed per draw at 8K/16K, printed as "one initialization seed per draw at 16,384"); if not, nothing registered is run and the matter
  returns to the human lead. The decision is written to `q1_start.json`.
- After Q1, `q1_gate` computes the candidate by the fixed rule, re-evaluates the rule on WX and the probe with the candidate's rehearsed rates, the hours charged and the reserve (cut 1: drop the probe; cut 2: drop WX), and
  applies the memory rule per block. `wx` and `probe` refuse unless the Q1 gate allows them. Each block's cap is the table's entry for its configuration (Q1: full or cut3; WX and the probe: the candidate). The cap is the
  frozen one; nothing is raised here.
- A block that reaches its cap is stopped and is INCOMPLETE; a failed cell is kept and not re-run; no setting is changed after a start.
- Any in-process tool that trains (the gates, the rehearsal, a test harness) must call `studies.p10s0.train.configure()`: without it two identical runs differ by about 4e-8 after one update (audit m12). Every worker does.
- Every machine product that carries an A5-D class, label, candidate or reading (`analysis.json`, `q1_gate.json`, `results.json`, `classes.csv`, `RESULTS.md`, stdout lines) carries the fourth-arm string, P9-II's F1
  annotation and the fixed provenance sentence, through one emit path (`core.stamp`, `core.write_record`, `core.emit_stdout`).
