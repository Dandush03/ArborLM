# P10-S1 pre-calibration implementation audit (ADR-0021 revision 4) — 2026-11-15

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- **Auditor:** Claude Opus 5.5 (model id `claude-opus-5-5`), the arbor-auditor role. I did not write any of the code audited here (implementation by Sonnet 5.5, commit `8747af2`).
- **Worktree:** `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-s1`, HEAD `8747af2ed60658ef6f3aaa0ac882706c5a1020ad`. I edited nothing outside this folder and made no commit.
- **Environment:** macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, uv 0.12.15. Every command was run from the worktree root as `PYTHONPATH=. uv run --locked python <script>`, with `torch.set_num_threads(1)` inside the scripts.
- **What I ran.**
  - Unit tests, the DRY stage (tiny synthetic sizes, test seed set `p10s1-test-0`), and my own scripts.
  - My scripts used only the unit-test range: seed sets `p10s1-test-5` to `-8` (bases 921501–921801) and generator seeds 921501–921799. They also read the frozen backbone B101/O301 from `experiments/`.
  - **No calibration, rehearsal or registered stage was run.** No calibration, rehearsal or registered data was generated or read.
- **Scope.** Every item of the brief:
  - ADR fidelity;
  - the bit-for-bit claim;
  - D-OQ;
  - the information measures;
  - leakage;
  - engineering;
  - the tag rule;
  - the implementer's readings (a)–(o);
  - what is untested.

## Verdict: **READY AFTER LISTED FIXES**

**Counts:**
- 0 blockers;
- 8 majors (M1–M8). Three of them, M5–M7, are **PENDING LEAD REVIEW** scientific consequences that the lead must settle before calibration;
- 16 minors.

**Order of work.**
- Make the code fixes (M1–M4, M8 and the minors the lead accepts) **before** calibration.
- Reason: ADR §8 allows nothing but its listed items to change after the calibration outputs exist. Every calibration record also carries the code identity.

**What is correct, independently verified:**

| Item | How I checked it |
|---|---|
| The registry: 30 configurations, 150 cells, seed blocks 14 / 28, cut-3 plans, calibration 46 / 50 runs | Enumerated from the ADR (c4) |
| Run lengths and snapshot schedules, MC snapshots included | c4 |
| G9 | Recomputed from the ADR's ranges and my own scan of configs and code literals (c4, c4b) |
| The §7.1 information measure and the G2 intervals | Own exact binomial: [34, 100], [192, 325], [894, 1,159] |
| Every verdict, class and outcome rule of §8.2–§8.8, both lines | My own implementation against `classes.py` (c1); against `analysis.py` end to end on my own synthetic run directories (c5) |
| F-OQ and R2 against P9-I's R1 and R2 | Three-way equal (c2) |
| D-OQ construction | c3 |
| Work counters | Against FLOP counts (c7) |
| The IVF candidate rule | c7 |
| The address swap | c7 |
| Panel and training independence | By a token-byte hash over a full registered-length run (c7) |

**What is wrong or must be decided:** see below.

---

## Findings

### Majors

**M1. Study B's "I_use grows ≥ 3.0 times" is tested on i, not on I_use. KNOWLEDGE SCALES WITH MEMORY can never be printed.**

- **Where:** `studies/p10s1/classes.py:478`, `elif not (i_s > 0 and ge(i_l / i_s, core.STUDY_B_RATIO))`. `analysis.study_b` (`analysis.py:404`, `:408`) passes per-fact i values.
- **Why it is wrong:** along the diagonal the facts grow fourfold, so the I_use ratio is 4 · i_l / i_s. The code requires i_l / i_s ≥ 3, which means an I_use growth of 12.
- **Consequence:** with the 0.85 a_use floor at every diagonal cell, the largest reachable i ratio is 5 / i(0.85) = **1.371** (c1, `study_b_ratio`). So the label is unreachable and H21-3 cannot be tested.
- **Demonstration:** a_use 0.99 at every diagonal cell, both steps memory-attributed, sublinear work:
  - my reading: KNOWLEDGE SCALES WITH MEMORY (I_use ratio 4.0 at each step);
  - `classes.study_b_label`: NOT ESTABLISHED.
- **Fix:** compare (F_l · i_l) / (F_s · i_s) ≥ 3.0. Pass the fact counts, or pass I_use instead of i, and add a unit test with these numbers.
- The unit tests did not catch it.

**M2. The report crashes on a label the ADR defines: `BEATS DENSE (DENSE AT CHANCE AT <cell>)`.**

- **Where the label is built:** `classes.py:416`.
- **Where the report fails:**
  - `report.show` (`report.py:35–38`) appends the tag after the parenthesis.
  - `classes._TAG_AFTER` (`classes.py:66`) accepts a tag only *immediately* after the label, so `emit` raises `UntaggedPositiveLabel`.
  - `classes.printable` fails the same way (c6: `report_show_then_emit` and `printable` are both REFUSED).
- **Reachability:** the label is reachable. Take any arm with a CAPACITY STEP whose larger cell is at 16,384 slots (A1 or B1). There, the dense MC pair is established (M5). If D-OQ is at chance at U_P, the capacity table raises.
- **Consequence:** the registered report stage fails and cannot be re-run with changed code.
- **Fix (either):**
  - build the label as `BEATS DENSE [STORE ONLY; ORACLE-ADDRESSED; DENSE AT CHANCE AT …]`; or
  - let `_TAG_AFTER` skip one parenthetical group.
- **Test to add:** render a report whose dense label is this one.

**M3. Registered-mode stages run without the freeze, and the registered driver accepts typed caps and ledger overrides.**

*Without the freeze* (c10, code path):
- `train`, `evaluate` and `gates` with `--mode registered --freeze-commit HEAD --stage-cap-seconds N` pass `check_preconditions` (`stages.py:248–274`) on a clean tree.
- That function never loads or verifies `plan.json`.
- `frozen_of` then builds the default plan with the placeholder cost table: c10 shows the plan and 164 cells used with `freeze_plan = None`.
- A typed `generate` (allowed pre-freeze) → `gates` → `train` sequence therefore trains registered cells on registered seeds with no freeze, no frozen caps and placeholder MC snapshots.
- This contradicts §11 items 7–9 and the claim in `freeze/README.md` that "every registered stage refuses to run without them".

*Inside the driver:*
- The `registered` sub-command inherits every common flag (`stages.py:1282`).
- `stage_cap()` returns `--stage-cap-seconds` in preference to the frozen cap (`stages.py:333–334`). c10 shows `registered train … --stage-cap-seconds 999999` yields a cap of 999999.
- `--ledger-root` or `--experiments-root` points the ledger at a fresh file.
- `--rss-worker-bytes` changes the memory caps, and `--only` trains a subset.
- The launch scripts pass none of these (verified), but the driver does not enforce what its docstring states.

*Fix:*
- Refuse `--mode registered` for every command except `registered`, the worker entry point and `generate`.
- Make `cmd_registered` reject every flag other than `--run-dir`, `--freeze-commit` and `--caps`.
- Have `work` in registered mode verify the frozen plan's sha256, passed by the driver.

**M4. As written, the freeze procedure makes the registered run impossible.**

- `freeze/README.md:42–44` puts the freeze commit at step 12. Decision 2 comes after it (step 13), "recorded in section 15", as ADR §11 item 8 requires.
- Both checks refuse an ADR edited after the freeze commit:
  - `check_preconditions` compares `core.SPEC` at HEAD with the freeze commit (`stages.py:265`);
  - `verify_plan` compares `code_identity`, which includes `spec_sha256` (`stages.py:1123`).
- So recording Decision 2 in the ADR stops every registered stage.
- **Fix (lead's choice):**
  - record Decision 2 in a separate file outside the hashed spec (for example `results/p10s1-freeze-…/DECISION_2.md`) and amend the ADR after the run; or
  - hash the ADR with §15 excluded.
- State the choice in the freeze README.

**M5 (PENDING LEAD REVIEW). BEATS DENSE is structurally unreachable. Where the dense matched-compute reading is not established, the arm is labelled DENSE MATCHES even when D-OQ is far behind.**

- **Mechanism:**
  - D-OQ costs about three times F-OQ per update at equal parameters. Its W is 48h against 16N + 1,280, and the dense map uses all of w2.
  - In the dense MC pair the arm is the cheaper cell and must be read at m·U_P.
  - At 65,536 slots the arm's run is 2·U_P, so the pair is MC-SHORT.
  - For T-OQ and H8 it is MC-SHORT at every cell.
  - `_dense_cells` then sets the MC reading to (d = inf, r = 1.0) (`analysis.py:282`). That blocks BEATS DENSE and DENSE AHEAD under MC.
- **Measured multipliers** (c3; "counted" = torch FLOP counter of one whole training update):

| Dense pair (arm vs D-OQ) | Implemented analytic multiplier | Counted multiplier | Status under either |
|---|---|---|---|
| F-OQ, 8K/16K or 32K/16K | 2.87 → grid 3 | 2.57 → grid 3 | OK (arm read at 24,576 ≤ 32,768) |
| F-OQ, 8K/64K or 32K/64K | 2.88 → grid 3 | 3.40 → grid 4 | **MC-SHORT** (run 16,384) |
| T-OQ, 16K / 64K | 41.7 / 67.2 | 5.32 / 18.2 | **MC-SHORT** |
| H8, 16K / 64K | 115 / 135 | 5.54 / 19.2 | **MC-SHORT** |

- **Consequences:**
  - CAPACITY_SUPPORTED needs a CAPACITY STEP in 16K→64K, whose larger cell is at 65,536 slots. So **no CAPACITY_SUPPORTED arm can be BEATS DENSE**; the best is DENSE MATCHES.
  - On my synthetic "capacity" scenario (c5), D-OQ sits at a_use 0.2 against arms near 1.0, and every supported arm is labelled DENSE MATCHES.
  - §8.5's DENSE MATCHES sentence, "a dense map with the same parameters, input and compute retained as much", would then be false. The implementation does not print that mandated sentence at all; `grep` finds no "retained as much".
- **Not an implementation error.** The rule is applied as written. But the lead must decide before calibration:
  - (a) accept and reword the printed DENSE MATCHES text where MC is not established; or
  - (b) define the dense MC reading differently, for example the costlier D-OQ read earlier rather than the arm read later.
- Option (a) is the conservative one.

**M6 (PENDING LEAD REVIEW; implementer's reading (d)). The analytic multiply-add measure omits the frozen backbone's forward and backward pass, which every arm pays and which dominates most cells.**

- **Size of the omission** (c3):
  - The backbone forward and backward of one update is 57.5 M multiply-adds (115,089,408 FLOPs).
  - The implemented formula 3 × 128 × W + 4 × trainable gives 26.4 M for F-OQ at 4K; the counted total is 74.7 M.
  - It gives 1.0 M for H8 at 4K; counted 57.9 M.
- **Effect on the multipliers:** the implemented formula's ratios are much larger than a whole-step count:

| Pair | Implemented | Counted |
|---|---|---|
| F-OQ 4K→16K | 3.94 | 1.67 |
| F-OQ 16K→64K | 3.986 | 2.61 |
| T-OQ 4K→16K | 1.59 | 1.00 |
| T-OQ 16K→64K | 2.48 | 1.01 |
| H8 4K→16K | 2.54 | 1.00 |
| H8 16K→64K | 3.43 | 1.00 |

- **Why it matters:** "the larger of the two multipliers is used", so this measure decides every MC readout. Two consequences:
  1. F-OQ's A2/B2 MC readout lands exactly on the smaller cell's run length (4.0 · U_P = 32,768). Any CPU ratio above 4 makes it MC-SHORT, and then F-OQ cannot be CAPACITY_SUPPORTED.
  2. On the efficiency line, FASTER for F-OQ needs u_T(4N) ≤ 0.8 / 3.94 = **0.20** · u_T(N). With a whole-step count it would need 0.48.
- **Conservative choice:** the implemented formula is conservative for the capacity positive and very harsh on the efficiency line.
- **Options for the lead, to record before the rehearsal (the MC plan is frozen from it):**
  1. As implemented.
  2. Whole training step including the frozen backbone (FLOP-counted or analytic), consistent with the CPU measure.
  3. Memory-only multiply-adds without the optimizer term.

**M7 (PENDING LEAD REVIEW; implementer's item (a)). The dense-rate tie will predictably stop the calibration, and the calibration does not record what "faster" would need.**

- `calibrate.select_dense_rate` raises `TieNeedsLead` when two rates are within 0.02 (`calibrate.py:109`).
- At 8K/16K, D-OQ is likely near its ceiling at two of three rates. The DRY calibration already returned to the lead on this tie (d1).
- The D-OQ calibration cells are evaluated only at {U_P, U_run} (`calibrate.py:39`). So "the faster of the two" in the learning-speed sense cannot be computed from the records.
- **Fix:**
  - the lead defines "faster" before calibration (see ruling (a));
  - add the doubling snapshots (U_P/16 … U_P) to the dense-rate calibration cells. This is evaluation only and adds no training.

**M8. The registered path (driver, launch scripts, freeze commit) has never been executed end to end.**

- The DRY stage freezes into a temporary directory under `--mode rehearsal`/`calibration`, and the registered mode refuses synthetic data. As a result, these have never run:
  - `cmd_registered`;
  - `verify_plan` against a real freeze commit;
  - `check_preconditions` passing;
  - any `launch/*.sh` script.
- The unit tests cover `check_preconditions` and `verify_plan` in pieces, in temporary repositories, but not a launched stage.
- This is the gap behind P9-I attempt 1 and P9-II `GENERATE_ATTEMPT1.md`.
- **Fix before the freeze:** a clone rehearsal of the whole registered sequence. Run `generate.sh` → freeze commit → `gates.sh` … `report.sh` on test seeds, through a test-only switch that the registered driver honours only for `p10s1-test-*` seed sets. Alternatively do it in a clone with substituted seed constants, as P9-II's `c5_preconditions_clone.sh` did.

### Minors

| # | Where | Finding | Fix |
|---|---|---|---|
| m1 | `analysis.py:322–323` | The DENSE NOT READ override replaces DENSE AHEAD too. If a read cell is DENSE AHEAD and a cut cell is not read, CAPACITY-NEGATIVE (b) can no longer fire. §8.5 says DENSE AHEAD "takes precedence over every other label". | Skip the override when the label is DENSE AHEAD |
| m2 | `core.py:417–419` | With the overload row the seed block runs F-OQ on 9 cells (+18 per draw), not "all seven cells" (+14) (c4: 208 vs 204 cells). | Follow the ADR (seven cells) or have the lead record the extension |
| m3 | `classes.py:722` | DENSE FASTER, a blocking label, uses "for every value the bounds allow". When the arm's u_T is left-censored (lo = 0) it can never block. The ADR states the every-value rule only for the step verdict. PENDING LEAD REVIEW | Lead to choose |
| m4 | `budget.py:238`; `launch/generate.sh` | The projection omits the registered generation and G1 of five draws. `generate.sh` carries a provisional 1,800 s cap that "the lead replaces". | Measure G1 at the plan's table size on the rehearsal draw; add 5× it to `Fixed`; put the measured cap in the script before calibration (the script is in the source digest) |
| m5 | `tests/test_p10s1_core.py:245` | The test fails whenever any untracked file exists outside the p10s1 paths. My review folder made it fail (t0). It will also fail once review or results files exist. Same class as P9-II's post-freeze test fix | Restrict the check to tracked files, or to `studies/p9*`, `src/`, `configs/` |
| m6 | `stages.py:742`; `classes`/`report` | The analyze stage prints bare labels to stdout (`"capacity": "CAPACITY-POSITIVE"`). `results.json` and `analysis.json` carry untagged class names. Per-replicate FASTER and REACHED ONLY BY THE LARGER, and the variants "CAPACITY STEPS" / "CAPACITY STEPs", are not caught by `emit` (c6). | Tag in stdout; add a top-level tag note to `results.json` (`analysis.result` has `store_only_tag`); widen the regex to plurals |
| m7 | `timing.py:34` | 30 s × 3 retries. After a six-worker stage the 1-minute load average needs about 107 s to fall from 6 to 1, so THROUGHPUT and cost timing may come out NOT MEASURED. | Longer pause, or an operator wait recorded in the procedure |
| m8 | `train.py:143` | `_valid_work` does not check key names: a `work_counters` key "accuracy" passes the whitelist. | Apply `_clean_name` |
| m9 | `stages.py:265` | The whole `studies/` tree must equal the freeze commit, so S0 or S2 code merged later blocks S1's registered stages. | Run S1's registered stages from a worktree pinned to its freeze commit; say so in the README |
| m10 | `freeze/README.md:7` | Stale: "the ADR copy in this worktree still says 12" (it says 16). | Edit |
| m11 | `analysis.py:422` | The ME line prints only the §5.4 sentence, not ME values (U_P/16, U_P/4 snapshots exist). | Print the ME readout of the diagonal |
| m12 | `stages.py:1268`, `frozen.py:178` | The lane L status is free CLI text, and `fz.lane_l_status` is not wired to S0's record. | Derive it from S0's recorded outcome at the freeze |
| m13 | `analysis.py:654` | A human-directed no-loaded row covering only one transition is not representable (§10.1 allows "for the transition concerned"). | Lead to state the per-transition semantics |
| m14 | `stages.py:756–783` | The rehearsal's synthetic stage runs 5 scenarios; §10.2's list (each arm in turn NOT_EVALUATED, DEPENDENCE_FAILED, …) is covered only by unit tests and by my c1/c5. | Add those scenarios to `work_synthetic` so the rehearsal record shows them |
| m15 | `cmd_freeze` | The freeze does not compare the calibration and rehearsal records' code identity with the frozen identity, nor list the files that changed in between. | Record and list them |
| m16 | G9 (`core.py:719–739`) | Reads P1–P8 seeds from configs only. P6/P7 seeds live in code (`src/arborlm/p7a_core.py:44–49`). My literal scan (c4b) found no overlap: the only hit, 2112, is a P5 call count. | Informative; extend the scan or note it |

### Disclosures of my own process

- **t0.** The p10s1 unit-test run (149 passed, 1 failed) failed only because of my untracked review folder (m5). Kept: `outputs/t0_pytest_p10s1.txt`.
- **Two failed checker attempts, kept:**
  - `outputs/c4_attempt1_failed_tuple_keys.txt`: my JSON dump had tuple keys;
  - `outputs/c7_attempt1_failed_shape.txt`: I passed a `[64, 8, 5]` tensor to `encode_identifiers`.
  - Both were my bugs and were fixed in place. The fixes are marked in the scripts.
- **Scratchpad collision.** The DRY run used the shared scratchpad path `scratchpad/dry1/root`. Another session's P10-S0 DRY run had already written there, and my run's final `DRY_SUMMARY.json` overwrote theirs.
  - I backed their file up first (sha256 `2522e297…`), saved mine as `outputs/d1_DRY_SUMMARY_s1.json`, and restored theirs byte-identically.
  - No other file of theirs was touched; the S1 DRY writes only `P10S1*` paths and its own ledger file.

---

## Rulings on the implementer's readings

Rulings are of three kinds:
- **correct**: the implementer read the ADR correctly;
- **wrong**: the right reading is given;
- **undetermined**: a choice for the lead, with the options and which one is most conservative.

**(a) Dense-rate tie, "goes to the faster of the two".** *Undetermined; the lead must choose before calibration (M7).*
- Options:
  1. The higher learning rate.
  2. The faster learner: the tied rate whose minimum Panel A accuracy first reaches a fixed level on the doubling snapshots. This needs those snapshots recorded.
  3. Return to the lead (implemented). It is safe but will very likely stop the calibration.
- Most conservative for S1's positive claims: option 2. It gives D-OQ the rate that learns earliest, and the MU and MC readings are at or before U_P.

**(b) Lane L off; the freeze refuses `--lane-l` because S0's frozen code is absent.** *Correct for the expected timeline (§5.6 item 7). Undetermined if S0 qualifies before S1's freeze.*
- In that case §5.6 says the lane runs if it fits, so refusing is a deviation and must go to the lead. It must not be printed as OMITTED.
- Conservative: refuse and return to the lead (m12).

**(c) §7.5 page-miss setting (8 rows per page, ρ = 1/4, ascending tie).** *Undetermined, descriptive, enters no rule.*
- The pick is one of P9's four primary settings (ρ ∈ {1/16, 1/4} × R ∈ {8, 32}, tie `asc`; `studies/p9/sim.py:434–436`, `:1209`).
- The lead ratifies it. No option is more conservative for any class.

**(d) Analytic multiply-adds = 3 × 128 × W + 4 × trainable.** *Undetermined and consequential (M6).*
- It omits the 57.5 M multiply-adds of the backbone's forward and backward.
- Most conservative for the capacity positive: as implemented. It is the harshest on EFFICIENCY.
- The lead records the choice before the rehearsal.

**(e) Overload row: R2 only at 64K/64K; 8 configurations; 40 cells.** *Correct.*
- R2 is undefined where facts exceed slots (§3).
- "(R2 at 65,536 slots … is its REF cell)" fixes the cell.
- c4 confirms 38 configurations per replicate and 190 cells without the seed block. The seed-block size is m2.

**(f) OPTIMIZER-ASSISTED tests the share ratio.** *Correct (§8.8 says "share … exceeds … by more than 1.5 times").*
- The implementation flags a replicate if either U_P or the hit snapshot qualifies. That is conservative for an annotation.

**(g) DEP read at U_P of both cells, the MC readouts and the i\* argmax snapshots.** *Undetermined.*
- Options:
  1. As implemented (earliest argmax on ties).
  2. Every snapshot ≤ U_run of both cells, since i\* is a maximum over all of them.
- Option 2 is stricter: it blocks positives and negatives alike and turns them into INCONCLUSIVE. It is the more conservative for the positive line.
- Either way, state the tie-break.

**(h) "In at least 4 replicates" counts a replicate only if both panels satisfy.**
- For TREE_AHEAD / TREE_COMPETITIVE: *undetermined; both panels is the conservative choice for these positive/descriptive labels*.
- For DENSE AHEAD, a label that blocks: *undetermined*. Both panels is the **least** conservative choice. Options:
  1. Both panels (implemented).
  2. Per panel: ≥ 4 on Panel A or ≥ 4 on Panel B.
  3. Either panel within a replicate.
- Most conservative against a false positive: option 3, then option 2.
- In c1's random comparison options 2 and 3 changed DENSE MATCHES into DENSE AHEAD in 72–77% of random cases. Those cases are synthetic, so this shows the rule matters, not how often it would in a real run.

**(i) MC-AMBIGUOUS when the cost measures disagree; MC-SHORT above 6.**
- MC-SHORT above 6: *correct* (no grid snapshot exists).
- MC-AMBIGUOUS: *undetermined*. The implemented option is the conservative one: Δ_MC is undefined, so there is no CAPACITY and no dense MC reading.
- Under the implemented multiply-add measure the two measures can disagree only through CPU noise.

**(j) §10.1 items 1 and 2 use raw accuracy.** *Undetermined.*
- §7.1 says every rule uses i, i\* or I_use. REF, which the U_P check anticipates, uses a_use ≥ 0.95. a_use ≤ raw accuracy.
- Most conservative: a_use, or require both. With raw accuracy, the U_P check can pass while REF fails in the registered run.
- The counts for both are recorded, so the change is one line (`calibrate.py:153`, `:158`). The lead decides before calibration.

**(k) Efficiency: a FASTER STEP with no D-OQ cell prints DENSE NOT READ and is not blocked.** *Correct literal reading.*
- §8.8 blocks only on DENSE FASTER.
- The capacity line's "cannot by itself support" has no efficiency counterpart.
- The conservative alternative is to treat DENSE NOT READ as unable to support EFFICIENCY_SUPPORTED. It matters only after cut 3. Lead's choice.

**(l) G2 stays at level 0.001/40 with the overload row.** *Correct.*
- §8.1 makes that interval "chance" in every rule. Changing it would change every rule.
- With the row there are 50 tests, which raises the family-wise false-fail rate from 0.0010 to 0.00125. `g2_report` records both numbers.

**(m) Seed-block spread at U_P and U_run.** *Undetermined; descriptive.*
- Acceptable. I recommend both panels (it is Panel A only, `analysis.py:485`) and i\*(U_run) (SAT) rather than i(U_run).
- No class is affected.

**(n) Robustness on Panel A only.** *Undetermined; descriptive.*
- The conservative alternative is to require both panels for RISES WITH SLOTS.
- Note that `evaluate.py:311` computes the robustness tables on Panel A only, so changing this is an evaluation change and must precede calibration.

**(o) §20 item 5: REACHED ONLY BY THE LARGER mixed with FASTER IN UPDATES ONLY is MIXED.** *Correct.* My independent implementation gives the same.

---

## Section-by-section fidelity (summary of the evidence)

### Registry, arms, run lengths, snapshots (§5.1, §5.4, §6.1, §10.1)
- My enumeration equals `core.registered_cells` for these plans (c4):
  - default: 150 cells;
  - seed block on draw 1: 164;
  - seed block on draws 1 and 2: 178;
  - both cut-3 cells cut: 140;
  - overload row without the seed block: 190.
- The overload row with a seed block differs (m2).
- Every cell's run length equals 6 / 4 / 2·U_P, or U_P for R2; the overload row uses its own U_P.
- Snapshots equal my own schedule for every cell: U_P × {1/16 … 4} ≤ U_run, U_run/2, U_run, plus the MC snapshots.
- Calibration has 46 runs (50 with the overload row): 16 load, 12 U_P, 6 H8, 12 dense.
  - Load snapshots include 24,576 / 49,152 at 4K and 16,384 / 32,768 at 16K.
  - Loadedness is read at the registered U_run.
  - The rule table and the cut-3 eligibility inputs match §10.1 / §10.3.

### Arms (§3, §4, §5.3)
- **F-OQ and R2 are bit-for-bit P9-I's R1 and R2** (c2). Covered:
  - the real backbone;
  - test set `p10s1-test-5`;
  - 4K / 16K / 64K for F-OQ, 4K / 64K for R2;
  - initial parameters, forward logits on 4 batches, and the loss, every parameter and both AdamW moments after each of 6 steps.
  - All are `torch.equal` across P9-I's Trainer, P10S1's Trainer and **my own loop** written from the ADR: alphabet CE at the 8 sites, AdamW 0.003 / (0.9, 0.999) / 1e-8 / wd 0, clip 1.0.
- **T-OQ:** P9's learned tree. Router of N/256 × 16, 2 branches visited, 512 candidates, with the router's log-softmax prior added to candidate scores (as in P9).
- **H8:** 8 distinct hashed slots, softmax of zeros = 1/8 each, values / wo / gate learned. Gradient reaches exactly the hashed rows. I did not re-derive this; it rests on the implementer's G5 unit test, which passes.
- **D-OQ** (c3):

| Slots | h | Parameters (D-OQ / F-OQ) | Relative difference |
|---|---|---|---|
| 4K | 4,033 | 197,618 / 197,633 | 7.6e-5 |
| 16K | 16,071 | 787,480 / 787,457 | 2.9e-5 |
| 64K | 64,219 | 3,146,732 / 3,146,753 | 6.7e-6 |

  - h is the best integer each time.
  - Initialization: w1 and b1 lie within ±1/4, w2 within ±1/√h, with variance ratios to the uniform 0.998–1.002. Gate −2.
  - The input equals F-OQ's code tensor (`torch.equal`).
  - My own forward from the §5.3 formula equals the addition to 2.8e-8 (float order). It is zero off the answer sites.
  - No backbone parameter is trainable.
  - Same loss, optimizer, clip and updates. The rate comes from calibration.
  - **Nothing in the code handicaps D-OQ.**
  - Two properties of the specification, not the code:
    - The pre-activation std at init is 0.20, because unit-norm 16-wide codes against a fan-in-16 bound. GELU starts nearly linear, so the rate calibration matters.
    - D-OQ gets about three times F-OQ's multiply-adds per update under MU. That favours the control.

### Information measures, plateau, "loaded", u_T, MC, counters (§5.4, §7.1, §7.4, §8.2, §8.8)
- i equals my own Fano formula on every 7th count at n = 2,048 / 8,192 / 32,768 (0 differences). Checkpoints: 1.523 / 3.287 / 4.036 / 4.466.
- i is zero at or below the interval's upper end.
- Hand cases (c9):
  - u_T interpolation on log₂ updates gives 2,895.37, equal to the hand value;
  - left- and right-censoring;
  - plateau 0.08 (plateaued and loaded) against 0.15 (not plateaued);
  - the MC readout of a ×3.94 pair is read at 32,768;
  - a ×4.29 pair with run 32,768 is MC-SHORT;
  - a CAPACITY verdict computed by hand (Δ_MU 1.25, Δ_SAT 0.87, Δ_MC 0.91).
- Counters (c7): K and V from the read's matmul FLOPs equal the counters and the §7.4 table for every arm at 4K / 16K / 64K. D-OQ's W is 48h.
- F-OQ-IVF's K = N/256 + candidates, measured.

### Rules (§8.2–§8.8)
- **c1, my own implementation against `classes.py`:**

| Rule | Cases | Mismatches | Coverage |
|---|---|---|---|
| Capacity verdict, one panel | 60,000 random | 0 | All 10 verdicts |
| Step class | All 3,003 multisets | 0 | — |
| Arm class | All 13,122 cases | 0 | Every class |
| Capacity outcome | All 65,856 combinations of class × dense label × engineering / incomplete | 0 | — |
| Efficiency verdict | 40,000 random + 2,646 grid | 0 (and 0 in u_T) | Every row, every censoring combination |
| Efficiency step class, arm class, outcome | Exhaustive | 0 | — |
| Dense label | 20,000 random | 0 against the both-panels reading | — |

  - §10.2's requirement holds over every combination: CAPACITY-NEGATIVE never fires when every arm is NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, ONE_TRANSITION or INTERMEDIATE.
- **c5, end to end:** my own run-directory generator and my own wiring (REF, leakage, MC from the frozen cost table, dense MU / MC / D-BEST, DENSE NOT READ, transitions, u_T, dense-faster). Over 28 scenarios, every replicate verdict, step class, arm class, dense label and both outcomes equal `analysis.analyze_study` (0 differences). The report renders in all 28.
  - My wiring mirrors theirs on the DENSE NOT READ override, so m1 was found by reading, not by c5.

### Leakage and independence (§3, §6.3, §7.1)
- The address swap changes only bytes 8r+1..8r+4 of trained-fact records, to π(f)'s identifier.
- π has 0 fixed points and 0 equal answers.
- D-OQ's swapped input is π(f)'s code.
- The backbone sees the original tokens (`evaluate.py:154–156`).
- Over a full 6 × 8,192-update run (786,432 training contexts) of a test draw, 0 Panel A / B, H1, H2 or calibration contexts occur in training, and the panels are pairwise disjoint. Checked by a 64-byte hash, not by fact ids.
- Oracle codes reach only F-OQ, T-OQ, F-OQ-IVF (query) and D-OQ (input). H8 and R2 use controlled addresses. KNN-W uses backbone states only.
- `check_seed_set` refuses every cross-mode seed set I tried (c4).
- G9: no overlap (c4, c4b).
- Rehearsal writers emit whitelisted fields only. I read every writer; see m8 for the validator gap.

### Engineering (P9-II classes)
- Already in place:
  - the launch scripts pass exactly run-dir, commit and `--caps`, which fixes P9-II's missing-flag defect;
  - projections include the per-task start-up;
  - the memory rule includes the evaluation and pool-task peaks;
  - per-configuration stage caps are in the cap table;
  - failed cells are kept, not re-run, and make the study S1-INCOMPLETE;
  - missing, failed and non-finite cells make the study S1-INCOMPLETE (c5 and unit tests);
  - one ledger is charged.
- Gaps: M3, M4, M8, m4, m7, m9.
- Per-task data rebuild costs 0.48 s CPU at 32,768 facts and 1.18 s at 65,536 (c8), so per-task data cost is negligible.

## What is untested, and what must be exercised before a freeze

1. **The registered driver path** through a real freeze commit with the launch scripts (M8). This includes `generate.sh` at real size, with its G1 time measured to replace the provisional cap (m4).
2. **Real-size gates:**
   - G4 / G5 / G7 at 64K;
   - G5 for all 30 (or 38) configurations;
   - G2 over five draws, in the registered gates.
   The rehearsal's gates stage runs one draw. The registered one builds five, which is cheap per c8.
3. **The overload row end to end.** Not covered in the DRY stage (no `--with-overload`). Covered only by synthetic analysis tests. The calibration's `--with-overload` path, its 4-run U_P read and the overload rehearsal items (38 configurations) are unexercised.
4. **The timing quiet-wait** under a real post-evaluation load (m7). The 64K evaluation memory peak at real size, including k-means on 65,536 keys and deep measures at 32K facts.
5. **The calibration rules on real records:**
   - the dense-rate tie (M7);
   - the U_P check reading (j);
   - the load table at registered U_run.
6. **The report on a CAPACITY-POSITIVE / BEATS DENSE case** (M2), and on the overload plan.

## Scripts and outputs (all in this folder; outputs in `outputs/`)

| Script | What it checks | Output |
|---|---|---|
| `c1_rules_independent.py` | §7.1, §8.2–§8.8 from the ADR text against `classes.py` | `c1_rules_independent.json` |
| `c2_bit_for_bit.py` | F-OQ / R2 against P9-I R1 / R2, three trainers, 6 steps | `c2_bit_for_bit.json` |
| `c3_doq_and_costs.py` | D-OQ construction; FLOP-counted multiply-adds; MC multipliers | `c3_doq_and_costs.json` |
| `c4_registry_seeds.py`, `c4b_seed_literal_scan.py` | Registry, run lengths, snapshots, calibration, G9 | `c4_registry_seeds.json`, `c4b_seed_literal_scan.json`, failed attempt `c4_attempt1_failed_tuple_keys.txt` |
| `c5_synthetic_registry.py` | Own synthetic run directories; `analysis.py` + report end to end | `c5_synthetic_registry.json` |
| `c6_tag_rule.py` | Attempts to break the tag rule | `c6_tag_rule.json` |
| `c7_counters_leakage.py` | Counters by FLOPs, IVF rule, swap, panel disjointness | `c7_counters_leakage.json`, failed attempt `c7_attempt1_failed_shape.txt` |
| `c8_data_build_time.py` | Per-task data cost at registered size (test seeds) | `c8_data_build_time.json` |
| `c9_hand_cases.py` | Hand-worked u_T, plateau, MC, CAPACITY | `c9_hand_cases.json` |
| `c10_driver_arguments.py` | Driver and registered-mode argument handling (pure) | `c10_driver_arguments.json` |
| DRY stage: `python -m studies.p10s1.stages dry --out-root <scratchpad>/dry1/root --workers 4` | Every stage at tiny size, 5 min 2 s | `d1_dry_stage.txt`, `d1_DRY_SUMMARY_s1.json` |
| `pytest tests/test_p10s1_*.py` | 149 passed, 1 failed (m5, caused by this folder) | `t0_pytest_p10s1.txt` |
| full suite `uv run --locked pytest -q`; `ruff check .`; `mypy src/arborlm` | Full suite: 2,056 passed, 4 skipped, 1 failed, in 15 min 22 s. The one failure is m5, caused by this folder; the implementer's claim otherwise holds. `ruff check .`: all checks passed. `mypy src/arborlm`: no issues in 85 files | `t1_pytest_full_suite.txt`, `t2_ruff_mypy.txt` |

- `ruff.toml` here extends `docs/reviews/ruff.toml` for these scripts only. `uv run --locked ruff check docs/reviews/p10s1-implementation-audit-2026-11-15` passes.

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**
