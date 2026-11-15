# P9-I (ADR-0017 Part I): final re-check before a re-freeze (commit `8261f22`)

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`). I wrote `AUDIT.md`, `RECHECK.md` and `GATE_FIX_AUDIT.md` in this folder (X1 major, X2 minor). The X1/X2 fix is the implementer's (Sonnet 5.5). I did not write it.
- **Date:** 2026-11-15 UTC, 01:21 to 01:45. **Worktree:** `.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design`, HEAD `8261f22`. Diffs reviewed: `0e0fbfb..8261f22` and `dd8b205..8261f22` (studies/p9i, tests).
- **Status:** independent engineering and mathematical evidence. It is not Astra validation, not human approval, and not a decision on a second attempt. **Astra review: NOT_PERFORMED.**
- **Environment:** Apple M5 Max, macOS 27.2.1 (Darwin 27.2.0 arm64), Python 3.12.14, torch 2.8.0 CPU float32. Commands use `uv run --locked` with `PYTHONPATH=.`, run from the worktree root. `$E` = `/Users/daniellaloush/dandush03/ArborLM/experiments`, `$S` = this session's scratchpad. `$C` = a throw-away `git clone` of this worktree checked out at `dd8b205`, under `$S/f/clone_dd8b205`.

## What ran

| # | Command | Output (`outputs/`) | Result |
|---|---|---|---|
| 1 | `… a3_rehearsal_replay.py $E/P9IH-20261114T231255388625Z-… $E $S/f/a3run N-n4096-b101-o301-s1801 BB-n4096-b101-o301-s1802 A4E-n16384-b101-o301-s1801` | `f0_a3_replay_at_8261f22.txt` | byte-identical to `g2_a3_…_at_0e0fbfb.txt`: 3 of 3 bit-identical replays |
| 2 | `… a4_arm_forward.py $E` | `f0_a4_…` | byte-identical to the `0e0fbfb` output |
| 3 | `… a5_classes_enumeration.py` | `f0_a5_…` | byte-identical; 20,000 tables, 0 disagreements |
| 4 | `… a1_calibration_rule.py $E/P9IC-20261114T225847947431Z-…`, `… a11_registry_seeds.py` | `f0_a1_…`, `f0_a11_…` | byte-identical to the pre-freeze outputs |
| 5 | `… g3_analyze_report.py $S/f/g3run results/p9i-run-attempt1-2026-11-14/gates.json` | `f0_g3_…` | **0 failed checks**; S9 now passes (it crashed at `0e0fbfb`) |
| 6 | `… g3b_nonfinite.py $S/f/g3brun …/gates.json` | `f0_g3b_…` | S9a, S9b, S9c, S11 and S12 all exit 0; S12 pool manifest COMPLETE; `results.json` written |
| 7 | `… f3_x1_contents.py $S/f/g3brun/g3_import_side_effect` | `f3_x1_contents.txt` | 12 of 12 checks pass |
| 8 | `… f1_nonfinite_readers.py $S/f/f1run2 …/gates.json $C <worktree>/.venv/bin/python` | `f1_nonfinite_readers.txt` | 192 checks pass, 0 fail |
| 9 | `… f2_classes_with_lm.py` (once with `PYTHONPATH=.`, once with `PYTHONPATH=$C`) | `f2_…_at_8261f22.txt`, `f2_…_at_dd8b205.txt` | see §2 |
| 10 | `python -m studies.p9i.stages generate --mode rehearsal --draw 2 --run-dir $S/f/gen2 --experiments-root $E --ledger $S/f/ledger_gen2.json --stage-cap-seconds 600 --workers 1` | `f4_…` | data identity equals the lead's `P9IG` draw-2 run (made at `0e0fbfb`) |
| 11 | `… f5_attempt1_identities.py results/p9i-run-attempt1-2026-11-14 $E/P9IP-20261114T235955649302Z-…` | `f5_attempt1_identities.txt` | attempt-1 values for the freeze record |
| 12 | `uv run --locked pytest -p no:cacheprovider -q -rf` | `f6_pytest_at_8261f22.txt` | **1745 passed, 4 skipped, 3 warnings, 519.11 s**, exit 0 |
| 13 | `uv run --locked ruff check .`; `uv run --locked mypy src/arborlm` | — | All checks passed; no issues in 85 files |

**What I did not do:**

- I ran no registered stage, generated no registered seeds, trained nothing and evaluated nothing on real data.
- In the kept attempt-1 run directory I opened no `updates.jsonl`. From the restoration `train.json` files I read only `snapshot_sha256`, `run_updates` and `status`. For the snapshot files I computed file hashes only, and from `snapshot.json` I printed only `label` and `update`.
- All pool stages used private ledgers. `$E/P9I-ledger.json` is unchanged: sha256 `54a5921b…`, 6 entries, 965.07 s charged.
- I edited no existing file and made no commit.

**Failed checker attempts (my mistakes, kept):**

- `f1_…_attempt1_FAILED_auditor_bug.txt`: I looked for the L run directories under the wrong root. `g3.build` writes under `g3.SCRATCH`.
- `f3_…_attempt1_FAILED_auditor_bug.txt`: my check compared the ratio dict as a whole instead of its four values. The written values were already `"+inf"`.

Both are marked in the scripts. The implementer's code was not at fault in either.

## 1. X1 and X2: FIXED

- **X1.** `work_analyze` and `report.write_report` pass their records through `core.jsonable`, which writes ±inf and NaN as `"+inf"`, `"-inf"` and `"nan"`.
  - S9, S9a, S9b and S12 (pool) now finish: analysis and report exit 0 and the manifests are COMPLETE.
  - In S9a the dense-comparison ratios are `{"1801/A": "+inf", …}` and `smallest` is `"+inf"`, with the label BEATS DENSE. In S9b the contrast ratios are `"+inf"`, with the label BACKBONE HURTS ADDRESSING. Both are the rule's reading of an infinite ratio (≥ 1.10 and ≥ 1.03).
  - Every `*.json` file in these runs parses as strict JSON (no NaN or Infinity tokens).
- **X2, per the lead's ruling.**
  - `evaluate.language_modelling` writes a non-finite loss or rise as its string form and sets `degraded` True. `evaluate._finite` leaves strings alone.
  - `stages.work_analyze` reads the rise with `core.number`, which accepts the three strings and maps `None` to NaN. `classes.language_modelling_annotation` treats a non-finite rise as above 5%.
  - Results at 16,384 / seed 1801 (f1, L cases), each through `work analyze` and `work report`:

    | Relative rise | Label |
    |---|---|
    | `"+inf"`, `"-inf"`, `"nan"`, `None` | DEGRADED |
    | next float above 0.05 | DEGRADED |
    | 0.05 | PRESERVED |
    | 0.0 | PRESERVED |

  - In every L case the selection stays BB at step 1 and the classes are unchanged. The stored rise is the string, or `"nan"` for a legacy `None`. `classes.csv`, `cells.csv` and `RESULTS.md` carry the label or the string.
  - The eval-record writer (f1, E cases) was run on 10 (before, after) pairs:
    - Non-finite pairs give the strings and `degraded: true`.
    - The 5 finite pairs equal the `dd8b205` formula exactly: (2.0, 2.1) gives a rise of 0.050000000000000044, which is degraded; (1.7, 1.785) gives 0.04999999999999998, which is not.

## 2. No rule, class, annotation, selection or finite number changed versus `dd8b205`

- **Diff scope** (`f0_diffstat_dd8b205_to_8261f22.txt`):
  - `classes.py` ±2, `core.py` +35, `evaluate.py` +10/−3, `report.py` +2/−1, `stages.py` +47/−8 (`git diff --numstat`).
  - Two new test files.
  - No change to `model.py`, `train.py`, `studies/p9/`, `configs/`, `src/`, `pyproject.toml` or `uv.lock`.
  - **`core.py` is one pure-append hunk** (`@@ -761,0 +762,35 @@`, 0 lines removed). The registry, seeds, thresholds, `LM_DEGRADED_RELATIVE`, `select_updates` and the rest of `core.py` are untouched. `a11` (57-cell registry and seed ranges) and `a1` (§I.6 rule recomputed without importing `studies.p9i`) are byte-identical.
- **Calibration binding.** `results/p9i-calibration-2026-11-14/calibration.json` has sha256 `087bf0b5885859a78781e32cb0e0ce8d3b154dfcc471965cf82f06718c509f44`. `a1` recomputes U = 8,192 with the binding cell R1 at 65,536. g3 and f1 run with that file and U = 8,192 and pass the binding checks.
- **Classes and selection.**
  - `a5` (20,000 tables, no rises) gives the same result at HEAD as before.
  - **f2** draws 20,000 new tables (seed 900002). Each BB (size, seed) gets a rise from {−0.5, 0, 0.01, 0.0499999, 0.05, next float above 0.05, 0.0500001, 0.08, 1, +inf, −inf, nan}, or none.
    - At HEAD: 0 disagreements with my reference. That covers classes, dense comparisons, contrasts and selection (all equal to the no-rise result, so a rise never changes a class or the selection) and 46,524 DEGRADED and 12,889 PRESERVED labels.
    - The 4,451 all-finite tables give the same output digest at HEAD and at `dd8b205`: `28e61cc9…bbc21`.
    - At `dd8b205` the only differences are the 9,884 non-finite label cases (`nan` and `-inf` were PRESERVED there). That is the intended change.
- **Analyze and report outputs (finite).** f1 Q covers 11 synthetic runs (S1–S8 and the three finite L cases). The `dd8b205` workers (`$C`, subprocess) and the HEAD workers give equal `analysis.json` (without `identity`) and `results.json`, and byte-identical `RESULTS.md`, `classes.csv` and `cells.csv`.
- **Forward and training.** `a4` (10 arms against my reference forward) and `a3` (64-update replays, every `model.pt` and `optimizer.pt` tensor equal to the rehearsal run's) are byte-identical to the earlier outputs.
- **Code identity at HEAD.** `source_sha256` is `6407936e9b5faf933cf605306a9c12bf488e62cf7c022fd33403947e93c11b56`. It was `43a611c4…` at `0e0fbfb` and `7573da72…` in attempt 1. `spec 2798a8db…`, `config 7cc20791…` and `frozen_source 8b5a03a0…` are unchanged. The freeze edit will change `spec`.

## 3. Reader side

I checked every consumer of `analysis.json` and of eval records in `studies/` with `grep` and a read:

- **`stages.work_analyze`:** `classes.measures_from_eval` reads accuracies and intervals, which `evaluate._finite` keeps finite at registered sizes. The rise is read with `core.number`.
- **`classes.analyze_classes`:** handles non-finite rises.
- **`report.load_cell_records` / `_rows_cells`:** pass `lm_*` and other values through. `jsonable` runs before the CSV and JSON writers, and `eta` is `None` when R1 is 0.
- **`report._rows_classes`:** reads labels only.
- **`render_markdown`:** formats only `exposure_per_fact_analytical`, which is computed from integers and is finite.
- **`cmd_dry`:** reads `status` and `outcome` only.
- No other module reads these records.

f1 L/Q, f3 and g3b exercise all of these paths.

**For anyone recomputing outside the code**, including me after the run: eval records now carry two conventions.

- The `language_modelling` block uses the strings.
- Every other non-finite float is still `None` (unchanged `_finite`).
- A legacy `None` rise reads as NaN, so it is DEGRADED. In `cells.csv` it shows as an empty cell, while `analysis.json` shows `"nan"`. Only pre-`8261f22` records can contain that.

## 4. Anything new

Nothing blocking.

- **N1 (info).** `relative_rise = (after − before) / before` would raise on `before == 0`. `before` is the frozen B101 loss, 2.3494 nats (`a8`), so this cannot happen.
- **N2 (process; must go in the freeze record).** In a new run directory, `verified_data` compares the data only with that run's own freshly written `data_manifest.json`. **No code compares attempt 2 with attempt 1.** The comparisons in §5 must therefore be made explicitly, before the next stage starts. Ideally a small script with the expected values would be committed in the freeze commit.
- **N3.** `tests/test_p9i_nonfinite.py` (8 tests) and `tests/test_p9i_gates_harness.py` must be in the freeze commit, because `check_preconditions` compares every `tests/test_p9i_*` with it. The review files written today (`f1`–`f5`, `outputs/f*`, this file) must be committed first so the tree is clean.
- **N4.** A rehearsal draw-2 regeneration at HEAD reproduces the lead's `P9IG` data exactly:
  - the 14-entry `sha256s` block and every non-identity manifest field are equal;
  - `g1.json` sha256 is `8cc41927…` in both.

  So the data code path is the same at `0e0fbfb` and HEAD, across processes. The full suite count is reproducible: 1,745 = 1,737 + 8.

## 5. The new freeze record: what it must contain

1. **Commits and code identity.**
   - State the freeze commit and the code commit (`8261f22` or its descendant), with the new `source_sha256` and `spec_sha256`.
   - Diff from `dd8b205`:
     - `studies/p9i/stages.py`: gate inputs, `HarnessError`, restoration mode, DRY sizes, `core.number` and `jsonable` in analyze;
     - `core.py`: an appended non-finite helper block only;
     - `classes.py`: the LM annotation treats a non-finite rise as above 5%;
     - `evaluate.py`: the LM block writes strings;
     - `report.py`: `jsonable` before writing;
     - `tests/test_p9i_gates_harness.py` and `tests/test_p9i_nonfinite.py`.
   - State that `model.py`, `train.py`, `studies/p9/`, the config and the registry are unchanged, and that classes, selection and every finite number are unchanged (this file, §2).
2. **The lead's ruling on X2**, recorded as a decision: a non-finite next-byte loss or rise is written as a string and counts as LANGUAGE MODELLING DEGRADED. It never blocks selection. The record should say that this reading was made before any registered evaluation.
3. **The attempt-1 account.**
   - Run directory `P9IP-20261114T235955649302Z-8756ef5f9d1541bd9e0efaece6f7c27b`, kept and never reused.
   - It stopped at the gates stage on the R2 gradient-reach harness. It also had the structural cause: the gates stage could not run on rehearsal seeds.
   - Charged: generate 11.32 s, gates 5.62 s.
4. **Everything observed on registered seeds:**
   - G1's checks;
   - the G2 counts (B101 and B102);
   - exact-retrieval controls;
   - the N-vs-R0a and initial identities;
   - 12 gradient-reach booleans;
   - the lead's diagnostic (64 fact ids, R2's reach);
   - the G4 restoration training of N and BB, 32 updates each at 4,096 / seed 1801, whose `updates.jsonl` stay unread until the run is complete.

   No trained-arm accuracy was computed.
5. **The human lead's recorded decision authorizing attempt 2.** §15.6 excludes a re-run, so the existing delegation does not cover it.
6. **Data.**
   - Same registered seed set `p9i-registered` (182001+) and the same backbones.
   - A new run directory, with `generate --mode registered --i-understand-freeze-time` run at freeze time.
   - State that the `data_manifest.json` file hash will **not** be `8d73e555…`, because it embeds the code identity.
7. **Calibration.** Binding unchanged: `087bf0b5…`, U = 8,192, no failed size.
8. **Budget.** The exact command line and cap per stage. The project ledger has 965.07 s charged, leaving 13,434.93 s, against the 5,700 s of run caps plus generate.
9. **The comparison list below**, with the expected values written in and the procedure for a mismatch.

### Comparisons attempt 2 must pass (expected values from attempt 1; `f5_attempt1_identities.txt`)

**After generate, before gates:**

- **C1.** `g1.json` sha256 = `ab324b8546a377acb954606dc7205a4fba7228f4e2cb8a51fed8032ce0445143`. The file is byte-identical because it has no identity block.
- **C2.** The `sha256s` block of the new `data_manifest.json` equals attempt 1's, entry by entry (14 entries; canonical sha256 `3f9c8ea0…f520`):

  | Entry | sha256 |
  |---|---|
  | facts | `6dca28be…54da` |
  | lane_d | `fdead3fd…61b8` |
  | pool | `7d9b9cd9…eb91` |
  | templates | `a7a15632…4063` |
  | stream:calibration | `fa9103c0…40b` |
  | stream:h1 | `1cd778a2…3278` |
  | stream:h2 | `f3f7efa7…f51a` |
  | stream:lane_d_a_A | `7789b97d…2da` |
  | stream:lane_d_a_B | `56032a36…2d86` |
  | stream:lane_d_b_A | `3a5f769e…03f4` |
  | stream:lane_d_b_B | `1d6e5a81…215a` |
  | stream:mixed | `a5d7d0ba…17ab` |
  | stream:panel_a | `b115c320…a855` |
  | stream:panel_b | `d95d4ba1…a49e` |

  Full values are in `f5`.
- **C3.** Every non-identity field of `data_manifest.json` (seeds, `seed_set`, `template_pool`, `g1_passed` True, `g1_failed_checks` [], `dry` False) is equal. Canonical sha256 `1f678f9d…2922`.

**After gates, before train:**

- **C4.** `gates.json` `g2` block canonical sha256 `4ae2fe6c…0906`, i.e. the B101 counts:

  | Panel | 2,048 | 8,192 | 32,768 | unseen |
  |---|---|---|---|---|
  | A | 70 | 259 | 1,077 | 60 |
  | B | 62 | 256 | 1,005 | 66 |

  Intervals are [36, 96], [198, 318] and [905, 1147].
- **C5.** `controls` block canonical sha256 `a0b71a5a…147c`. This includes the B102 replicate counts and exact accuracy 1.0 at all three sizes:

  | Panel | 2,048 | 8,192 | 32,768 | unseen |
  |---|---|---|---|---|
  | A | 64 | 262 | 1,019 | 61 |
  | B | 79 | 291 | 1,037 | 80 |
- **C6.** `restoration` block canonical sha256 `19698d02…7fb7`: identical True, 55 tensors for N and 67 for BB, split 16, 32 updates.
- **C7.** The restoration snapshot files at `g4_restore/{N,BB}/restore_check/first/snapshots/u0000016/` hash as follows:

  | File | N | BB |
  |---|---|---|
  | `model.pt` | `36aef885…6104` | `cbbc998d…a04c` |
  | `optimizer.pt` | `8b0527bd…0320` | `97340cb7…c269` |
  | `movement.pt` | `f0d46529…eb54` | `41629255…b5bf5` |
  | `snapshot.json` | `54005d6d…bbfdd` | `8e2cc5da…8233b` |

  These are expected to be identical because:
  - `build_model` seeds the global generators with the init seed;
  - the restoration jobs do not depend on the changed gate inputs;
  - the mode is REGISTERED in both attempts;
  - snapshot bytes are identical across processes and code versions (`a3`).
- **C8.** `g4_defects` is []. All 12 arms reach every trainable tensor: A4 8, A4E 8, BB 9, BB-0 4, BB-D 7, D 3, D7 3, E7 5, N 5, R1 4, R2 3, W7 5. All N-vs-R0a and initial identities are True on both parents. C8 is already a registered gate condition; the counts are a consistency check.

**Recommendation (PENDING LEAD REVIEW; the decision is the lead's):**

- **Any mismatch in C1–C7 should stop the run before the next stage starts**, and be recorded with no re-run until the lead decides.
  - Every one of these quantities is a deterministic function of unchanged code, seeds and backbones.
  - A difference would mean that attempt 2 is not the same registered computation.
  - Continuing would make the attempt-1 observations, and the claim that nothing was re-drawn, unverifiable.
- C8 failing is already a gate failure under the registered rules.
- Make the check mechanical: a committed comparison script with these values, run between generate and gates and between gates and train, rather than a reading at run time.
- The `data_manifest.json` file hash, the `identity` blocks and `gates.json`'s file hash are **expected to differ** and must not be compared.

## Verdict

**READY TO RE-FREEZE.**

X1 and X2 are fixed and tested. No rule, class, annotation, selection, threshold, registry entry, seed or finite number changed versus `dd8b205`. The calibration binding (`087bf0b5…`, U = 8,192) holds. The full suite passes at HEAD (1,745 passed, 4 skipped). There are no remaining code fixes.

What is left is process, not code, and must be in place before attempt 2:

- the freeze record items 1–9;
- the lead's written X2 ruling and the human authorization of attempt 2;
- the C1–C8 comparisons with the stop procedure.

Astra review: NOT_PERFORMED. This audit is not human approval and not a decision on a second attempt.
