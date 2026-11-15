# P10-S0 freeze procedure (ADR-0020 sections 10, 13, 14, 18 and the addenda)

Status: procedure only. Nothing in this directory is a freeze until the freeze commit adds `plan.json` and `stage_caps.json` (both, or neither: no test asserts either is absent). Every registered stage refuses to
run without them, and without the freeze commit being the commit that added `plan.json`. `arm_selection.json` is the arm-selection record produced by `studies.p10s0.arm_selection` from P9-II's committed records;
it is part of the freeze and is recomputed by the auditor (gate G10). The human lead's acceptance of the P9-II outcome is recorded (ADR-0019 section 16; ADR-0020 addendum). Step 8 still needs a clean
implementation audit, a rehearsal that meets the twofold rule, and the lead's separate recorded decision (`results/p10s0-freeze-<date>/DECISION.md`, below). Astra review: NOT_PERFORMED.

## Nothing is recorded in the hashed specification after the freeze (the lead's ruling on M5)

- **The run decision** is the file `results/p10s0-freeze-<date>/DECISION.md`, outside every hashed path (the preconditions compare `studies/`, the config, ADR-0020 and `tests/test_p10s0_*` with the freeze
  commit; `results/` is not among them). It is committed before registered generation (the generation command refuses without it) and may be committed again after the freeze without stopping any stage.
  Nothing is recorded in ADR-0020 after the freeze commit: the ADR is amended with the run's records only after the registered run (after `report`).
- **The hour cap is fixed at the freeze.** A raise under the human lead's delegation can only be made before the freeze: at the rehearsal's headroom check, by changing `resources.cap_hours` in the config **(the one place the cap is set: the ledger, the headroom rule and the
  context multiples read it through `core.cap_hours()`; the config check accepts any positive finite value there and keeps every other resource at its registered constant, so a raise is exactly one changed value)**
  and recording the raise in ADR-0020 (old and new cap, the measured projection that required it, what it protects), then the freeze commit. After the freeze the cap is fixed; the Q1 gate uses the frozen cap and applies the registered
  cuts; no raise is ever made after a registered seed has been observed.
- **The freeze must not hash anything designed to be written after it.** `plan.json` hashes only files that exist before the freeze (the arm-selection record, the projection, the cap table, the draw plan, the data
  manifests, the pinned auditor scripts). The ledger, gates, results and DECISION.md are written after it and are not hashed.

## Order (each step before the next; the freeze commit is step 10)

1. Implementation, tests, the DRY stage (`uv run --locked python -m studies.p10s0.stages dry`), ruff, mypy, the full test suite, and **the end-to-end exercise of the whole registered sequence through the real launch scripts
   on test seeds**: `uv run --locked python -m studies.p10s0.e2e --out <new-dir>` (one command; a throwaway clone; the TEST_PROFILE marker selects test seeds, tiny sizes and a synthetic backbone; the scaled Q1 projection is derived from the config's hour cap, so cut 3 applies at any cap; exit 0 when the
   rehearsal, generation, `set-generation-cap`, gates, `projection` with cut 3 and a probe over the memory limit, `caps`, `generate.sh`, `freeze-plan`, the freeze commit, `gates.sh`, `q1.sh`, `q1_gate.sh`, `wx.sh`,
   `probe.sh` (refused), `analysis.sh`, `report.sh` and a refused second `q1.sh` behaved as expected). Repeat it after any change under `studies/`. `--variant probe` runs the same sequence without the cut and without the raised peak: the probe stage is refused until `wx` has run, then `wx` and the probe run.
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
8. Measure the wall time of one `analysis` and one `report` on synthetic full-registry records: `uv run --locked python -m studies.p10s0.stages measure-analysis --out <timing.json> [--out-root <dir>]`
   (test seeds and synthetic records only; no registered input). It builds, in a temporary directory, all 230 Q1 cells and the WX and probe cells of A5-D with the real number of update-log lines and diagnostics
   per cell (about 3 GB, printed first and deleted at the end unless `--keep`; the record layout is copied from one tiny real cell trained and evaluated on test seeds), with missing cells, a failed cell, a
   non-finite value and a replaced draw; it times the real workers `work analyze` and `work report` as subprocesses and, in process, the analysis and report of synthetic registries that reach outcome rows 1-6, missing
   and non-finite cells, a failed gate and cut 3. The record (kind `timing`) holds both times: `analysis_wall_seconds` and `report_wall_seconds` are the figures for `caps` (the stage time plus the largest in-process row
   time: the computation counted twice, so they err high); `--tiny` (tests only) writes the same at the DRY unit and the record says `for_caps: false`. Then take the gates wall time and its per-draw part from the rehearsal-draw gates run (step 3). **The headroom rule counts the
   analysis and report time as part of what is still to run at both evaluations; the reserve is (analysis cap + report cap) / 2, so that doubled it is the sum of the frozen analysis and report stage caps, each
   with its 60 s floor (the lead's rulings on M6 and N4). `stage_caps.json` carries it as `measured.reserve_analysis_report` with the rule stated beside it.**
9. Write the cap table (one source of truth, a pure function of the projection) and the plan, from files and never by hand:
   `... caps --projection <projection.json> --gates-wall-seconds G --gates-per-draw-seconds P --analysis-wall-seconds A --report-wall-seconds R --out studies/p10s0/freeze/stage_caps.json`. The generation
   time is read from the config's `[generation].measured_seconds` (the one source; `caps` refuses while the block is provisional, and refuses a typed `--generate-wall-seconds` that differs from it).
   The gates cap is 2 x (G + 12 P): thirteen draws x three fact sets (the lead's ruling on M8). Then, after registered generation (step 11):
   `... freeze-plan --run-dir <registered-run-dir> --arm-selection studies/p10s0/freeze/arm_selection.json --projection <projection.json> --out studies/p10s0/freeze/plan.json`.
10. **Freeze record template** (committed with the freeze; the lead approves it): code hashes, arm-selection record hash, data identities, gates, caps, projections, cut 3 of section 10.4, launch commands, the lead's
    conditions of section 18, the generation cap and its measurement, the pinned auditor scripts, the auditor's recomputation file and sha256, and **every printed string the ADR does not fix** (the lead's ruling on item 6),
    which the lead approves there: `FOURTH ARM: NONE — P9-II STAGE 2 <status>`; `FOURTH ARM: <arm> — P9-II CARRIED <arm>`; `NOT DEFINED (S0 NOT_EVALUATED)` and `NOT AVAILABLE (S0 NOT_EVALUATED)`;
    `OVERLOAD NOT RUN — NO CANDIDATE`; `OVERLOAD NOT_EVALUATED`; `RECORD-LENGTH-FREE VARIANT: NOT RUN — <status>` / `INCOMPLETE`; `NOT QUALIFIED IN S0` with its neutral sentence; the banner sentences about the acceptance
    of the P9-II outcome; the hypothesis table notes; `ADDRESS STABLE` non-finite counting; the block-status strings of section 8.7; **the wording tables below**. The freeze commit adds `plan.json` and `stage_caps.json`.
11. **Registered generation** (before the freeze commit, with the tree clean at the code commit; it refuses without the recorded acceptance, without `results/p10s0-freeze-*/DECISION.md`, with a provisional generation
    cap, with a typed cap, or with any override): `sh studies/p10s0/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the thirteen registered and two reserve draws (all three fact sets each),
    G1-checks each and writes `draw_plan.json` (REPLACED BY RESERVE k; an exhausted reserve list makes the plan not ok and nothing runs). Run directories live under
    `/Users/daniellaloush/dandush03/ArborLM/experiments/` with study code P10S0.
12. Launch, in this order, each with `sh studies/p10s0/launch/<stage>.sh <registered-run-dir> <freeze-commit>`: `gates`, `q1`, `q1_gate`, `wx`, `probe`, `analysis`, `report`. **WX runs before the probe** (the lead's
    ruling on item 7): `probe` refuses while a WX block that is to run has no evaluation manifest.

## Implementer additions accepted by the lead

- **`guard_seconds_per_task`** (an implementer addition the lead accepted; it is not in ADR-0020 section 10.3). The projection measures, once, the time of the per-task guards a registered worker runs at start (git status, the frozen-input hashes of `src/`, the hashing of the frozen files and of fifteen manifests: `stages.measure_guard_seconds`) and adds it to every task's start-up overhead in every projection. It can only increase the projected seconds, is measured like the rates, and is recorded in the projection record
  the freeze hashes (`guard_seconds_per_task`). The lead sees its measured value in the freeze record.
- **The gates timing ratio**: a registered `gates.json` records `timing.registered_over_rehearsal_per_draw_ratio` (the registered per-draw time over the rehearsal draw's, the audit's re-check observed about 1.6), so the
  margin of the gates cap (2 x (G + 12 P)) is visible; it changes no threshold.

## Implementer-worded strings (generated; the lead approves each wording in the freeze record)

Generated by `uv run --locked python -m studies.p10s0.implementer_strings`: module-level string constants of `classes`, `core`, `report` and `analysis` of three or more words that ADR-0019 and ADR-0020 do not contain, and
the function-body strings of `classes` and `analysis` that do not occur in either ADR. A test requires every wording the scan finds to appear below. Strings of `report`'s and `core`'s function bodies are layout and
error text and are not scanned; the wordings fixed by ADR-0020 (the fourth-arm string, P9-II's F1 annotation, the provenance sentence, the cut-3 label, the override strings) are not implementer-worded.

| constant | wording |
| --- | --- |
| `classes.NOT_QUALIFIED_NEUTRAL` | No tested arm met S0's criteria on S0's draws. This text makes no statement about S1 or S2 (ADR-0020 section 17 item 0). |
| `classes.OVERLOAD_NO_CANDIDATE` | OVERLOAD NOT RUN — NO CANDIDATE |
| `core.MAPPING_NONE_TEMPLATE` | FOURTH ARM: NONE — P9-II CARRIED {arm} (ALREADY IN S0) |
| `core.MAPPING_NONE_STATUS_TEMPLATE` | FOURTH ARM: NONE — P9-II {status} |
| `report.NOT_CLAIMED[0]` | Nothing about capacity, useful-capacity scaling, locality, transfer or adding facts later. |
| `report.NOT_CLAIMED[1]` | Not an unbiased first test of A5-D: it was added after P9-II's outcome was observed, knowing it was RELIABLE there (confirmatory replication on new draws). |
| `report.NOT_CLAIMED[2]` | Nothing about natural language, another backbone or student, loads other than 0.5 and (label-free arms) 2 facts per slot, or any regime other than 512 exposures per fact. |
| `report.NOT_CLAIMED[3]` | Nothing reliable about 65,536 slots: three draws, one initialization seed, a probe. |
| `report.NOT_CLAIMED[4]` | Not that the interface finds where to read: the memory is told the answer position in every arm, WX included. |
| `report.NOT_CLAIMED[5]` | Not that a qualified arm beats a tuned baseline (A0 is untuned by design), and no efficiency, latency or storage claim. |
| `report.NOT_CLAIMED[6]` | Not a failure of the ArborLM concept, whatever the outcome; not a success of it either. |
| `report.NUMBER_LABELS` | Number labels: every accuracy, count, class and label in this report is MEASURED on S0's own cells (or, where it says P9-II, copied from P9-II's committed records); per-draw bounds are ANALYTICAL (one-sided 95% Clopper-Pearson); no HYPOTHETICAL number appears; no cost figure is an efficiency claim or a speedup. |
| `report.BANNER_BASE` | ArborLM is unproven research. Astra review: NOT_PERFORMED. A Claude review is neither Astra validation nor a human approval. |
| `report.CALIBRATED_TEXT['A0']` | no calibrated value |
| `report.CALIBRATED_TEXT['A1']` | λ = 1.0 (P9-II's audited calibration record) |
| `report.CALIBRATED_TEXT['A5-D']` | μ = 1.0 (P9-II's audited calibration record) |
| `report.CALIBRATED_TEXT['A2']` | U_pre = 2,048 updates at 2,048 facts and 8,192 at 8,192 facts (P9-II's audited calibration record, exposure-scaled) |
| `report.REGIME_TEXT` | 512 exposures per fact (U = 8,192 updates at 2,048 facts, 4U = 32,768 at 8,192 facts); schedules in exposures per fact; 0.5 facts per slot at 2K/4K and 8K/16K |
| `report.SIZE_NAME['2K/4K']` | 4,096 slots (2K/4K) |
| `report.SIZE_NAME['8K/16K']` | 16,384 slots (8K/16K) |
| `report.SIZE_NAME['8K/4K']` | 8K/4K (two facts per slot) |
| `report.TEST_PROFILE_BANNER` | TEST PROFILE — test seeds, tiny sizes, synthetic backbone; not a result |
| `classes.arm_class: rule is '20' or '10'` | rule is '20' or '10' |
| `classes.h20d_note:  of its cells at 8K/16K, fewer than four` |  of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading) |
| `classes.added_criterion_failed: condition 6 (fact-specific dependence)` | condition 6 (fact-specific dependence) |
| `classes.pooled_line:  draws succeeded (P9-II ` |  draws succeeded (P9-II  |
| `classes.pooled_line: ; pooled per-draw bound ` | ; pooled per-draw bound  |
| `classes.record_length_label: RECORD-LENGTH-FREE VARIANT: DOES NOT PAS` | RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required) |
| `classes.record_length_label: RECORD-LENGTH-FREE VARIANT: INCOMPLETE` | RECORD-LENGTH-FREE VARIANT: INCOMPLETE |
| `classes.record_length_label: RECORD-LENGTH-FREE VARIANT: NOT_EVALUATE` | RECORD-LENGTH-FREE VARIANT: NOT_EVALUATED |
| `classes.record_length_label: RECORD-LENGTH-FREE VARIANT: PASSES` | RECORD-LENGTH-FREE VARIANT: PASSES |
| `classes.record_length_label: RECORD-LENGTH-FREE VARIANT: PASSES AT 4,` | RECORD-LENGTH-FREE VARIANT: PASSES AT 4,096 ONLY |
| `classes.reason_missing_at_16384: NOT_EVALUATED at 16,384 (not read as a f` | NOT_EVALUATED at 16,384 (not read as a failure) |
| `classes.reason_missing_at_16384: not ADDRESS STABLE at 16,384` | not ADDRESS STABLE at 16,384 |
| `classes.study_outcome: ; 16,384 missing: ` | ; 16,384 missing:  |
| `classes.hypothesis_readings: a failure of WX is never evidence that t` | a failure of WX is never evidence that the record length is required; H20-L is never contradicted |
| `classes.hypothesis_readings: A0 NOT_EVALUATED or missing at a size an` | A0 NOT_EVALUATED or missing at a size and not UNRELIABLE or FAILS at the other |
| `classes.hypothesis_readings: annotation; never part of the label; per` | annotation; never part of the label; permits nothing |
| `analysis.eval_arm: bits per fact (i = 5 - h2(e) - e log2 31` | bits per fact (i = 5 - h2(e) - e log2 31; 0 at or below the chance interval); reported, enters no rule |
| `analysis.eval_arm: NOT DEFINED (S0 NOT_EVALUATED)` | NOT DEFINED (S0 NOT_EVALUATED) |
| `analysis.eval_arm: NOT AVAILABLE (S0 NOT_EVALUATED)` | NOT AVAILABLE (S0 NOT_EVALUATED) |
| `analysis.eval_arm:  cells with a first success (descriptive` |  cells with a first success (descriptive) |
| `analysis.eval_arm: NOT AVAILABLE (S0's protocol at this cel` | NOT AVAILABLE (S0's protocol at this cell type is not P9-II's) |
| `analysis.assess: gates record missing` | gates record missing |
| `analysis.assess: HARNESS ERROR (not a gate failure): ` | HARNESS ERROR (not a gate failure):  |
| `analysis.assess: Q1 cell without a record: ` | Q1 cell without a record:  |
| `analysis.assess: draw plan: the reserve list is exhausted` | draw plan: the reserve list is exhausted or a reserve failed G1 |
| `analysis.assess: G2 failed on draw ` | G2 failed on draw  |
| `analysis._analyze: no class, annotation or selection is der` | no class, annotation or selection is derived: registered cells, records or gates are missing or defective |
| `analysis._analyze: S0 did not start: no audited P9-II calib` | S0 did not start: no audited P9-II calibration record |

## The launch scripts

Each script takes exactly two arguments, the run directory and a commit, and passes its stage cap file (`--caps studies/p10s0/freeze/stage_caps.json`); `generate.sh` passes `--generation-cap-from-config`. The registered
driver accepts no other option: `--stage-cap-seconds`, `--ledger-root`, `--experiments-root`, memory caps, `--synthetic-backbone`, `--only`, `--cut3`, `--restore-split` and every other option of the parser are refused,
whatever their value. No typed command defaults into registered mode, and `--mode registered` is refused on every command but `generate` and the driver. Every worker the driver starts re-verifies the frozen plan,
the freeze commit and the absence of overrides, **and presents the stage token**: the driver writes `<run>/<stage>/RUNNING.json` (a nonce, the task labels and the cells) before it starts a stage and passes
`P10S0_STAGE_TOKEN=<stage>:<nonce>` to the stage's workers; a registered worker refuses without a token that matches a running stage (one with no manifest yet), for a stage of another kind, and for a cell that is
not among the stage's tasks or not in the frozen matrix. `work generate --mode registered` takes the same token and the acceptance, `DECISION.md` and non-provisional-cap checks of the generation command. A registered path
run from a test (`PYTEST_CURRENT_TEST` set) refuses unless the repository and the run root are temporary directories. The token is a guard against a worker started by hand, not a defence against someone who edits
`RUNNING.json` while a stage runs (the marker is removed when the stage ends). The two arguments are guarded: the driver refuses unless the working tree is clean, the commit is an ancestor of HEAD **and is the commit that added `plan.json`**,
`studies/`, the config, the ADR and `tests/test_p10s0_*` equal their content at that commit, the frozen inputs verify, and every hash in `plan.json` holds for the run directory it names. The scripts are covered by the
source digest. A test runs every script's argument check and parses its command line with the real parser; the end-to-end exercise runs them.

## What the registered stages enforce

- Training and evaluation need `draw_plan.json` with `ok` true, a passed G1 for every draw they name, and a `gates.json` in which G1, G2, G4, G5, G6, G9 and G10 all passed.
- Q1 starts only under the headroom rule of section 10.4 (reading A), with the rehearsed analysis and report time reserved: hours already charged + 2 x the rehearsed projection of Q1, of the stages before Q1 that have not
  run, and of the analysis and report is at most the cap in the config (`core.cap_hours()`); if not, cut 3 (one initialization seed per draw at 8K/16K, printed as "one initialization seed per draw at 16,384"); if not, nothing registered is run and the matter
  returns to the human lead. The decision is written to `q1_start.json`.
- After Q1, `q1_gate` computes the candidate by the fixed rule, re-evaluates the rule on WX and the probe with the candidate's rehearsed rates, the hours charged and the reserve (cut 1: drop the probe; cut 2: drop WX), and
  applies the memory rule per block. `wx` and `probe` refuse unless the Q1 gate allows them. Each block's cap is the table's entry for its configuration (Q1: full or cut3; WX and the probe: the candidate). The cap is the
  frozen one; nothing is raised here. The probe's evaluation cap is, like every block cap, 2 x the rehearsed projection (the larger of the alone and busy rates); the probe is one round of six cells, so it is the
  tightest cap in the plan, and the end-to-end exercise has a variant in which the probe is not refused for memory and runs (`--variant probe`).
- A block that reaches its cap is stopped and is INCOMPLETE; a failed cell is kept and not re-run; no setting is changed after a start.
- Any in-process tool that trains (the gates, the rehearsal, a test harness) must call `studies.p10s0.train.configure()`: without it two identical runs differ by about 4e-8 after one update (audit m12). Every worker does.
- Every machine product that carries an A5-D class, label, candidate or reading (`analysis.json`, `q1_gate.json`, `results.json`, `classes.csv`, `RESULTS.md`, stdout lines) carries the fourth-arm string, P9-II's F1
  annotation and the fixed provenance sentence, through one emit path (`core.stamp`, `core.write_record`, `core.emit_stdout`).
