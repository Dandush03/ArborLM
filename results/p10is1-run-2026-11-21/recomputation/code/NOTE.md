# P10-I-S1: independent recomputation, prepared before the registered results (2026-11-21)

Author: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`). Independent engineering work. **Not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

Nothing of the registered run was read. Its evaluate, ladder and analysis outputs were not opened, nor any sealed file (qfit, qcheck, generation, sealed). The implementer worktree was only read: through `git archive 46bf55a` into `./frozen/`, and its `.venv` Python was run with `-I` as a plain 3.12 interpreter.

## What to run once the report stage has finished

```
sh /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/p10is1_recompute_20261121/run_registered.sh
```

The script:
- refuses unless `$RUN/report/REPORT.md` exists;
- refuses unless the frozen plan's SHA-256 is `e1479e36…` and the rehearsal record named by the freeze record is `87854244…`;
- writes into a NEW directory `registered_<UTC>/`, with a timeout on each step:
  - `recompute.py` → `recompute.json` and `recompute.log`;
  - `compare.py` against `$RUN/analysis/analysis.json` → `compare.out`.

## What `recompute.py` covers

It uses only the standard library, imports nothing from `studies/` or `arborlm/`, and is written from the text of ADR-0024 (§§7.2, 8.1, 8.2, 9.1–9.6, 10, 14, 23) and of ADR-0021 where ADR-0024 refers to it (§§7.1, 8.1, 8.2, 8.8, 8.10). It covers:

- **Records and identity checks**
  - The raw records: `evaluate/<label>/uXXXXXXXX.json` (the reads `main` and `ivf`), `baselines/dN_fF.json`, `ladder/<cell>.json` and `timing/timing.json` (MC-T).
  - The status rows: item errors refuse; a gates record that is missing or not passed is an engineering failure; a failed cell, a missing read or a missing ladder decision is INCOMPLETE.
  - The ladder stop rule, recomputed. A recorded U_run that differs from it is an engineering failure.
- **Measurement primitives**
  - G2 chance intervals, computed exactly. They reproduce [34, 100], [192, 325] and [894, 1,159].
  - a_use, and i = 5 − h₂(e) − e·log₂31, set to 0 at or below the chance bound. It reproduces 1.523, 3.287, 4.036, 4.466 and 0.473.
  - DEP-a, DEP-b and DEP-c: DEP-c's quantile is exact, computed in log space. D-OQ is read without DEP-b (ruling 17).
  - LEAKAGE.
  - The R2 reference table and the registered R2 re-read (rulings 3 and 4).
  - REF; i\*; plateau, full at U (two consecutive ladder points) and loaded.
- **The capacity line**
  - MC-A, MC-T and MC-C matched snapshots, MC-SHORT and MC-AMBIGUOUS (§8.2; rulings 1, 5 and 6).
  - The capacity verdict per panel and per replicate (rows 1–10), the step class and the arm class.
  - The dense labels per CAPACITY STEP cell in MU, MC-A, MC-T, MC-C and D-BEST, with ruling 17's D-OQ blocking.
  - Dense at saturation; the arm-level dense label; C-CAPACITY; KEY-LEARNING-LIMITED.
- **The saturation line**: pair verdicts, pair, arm and outcome classes, ρ.
- **The efficiency line**: u_T (interpolated in log₂ updates, with censoring); step verdicts per cost reading E-A and E-T; step and arm classes; dense speed; C-EFFICIENCY.
- **The sparse label** at U_P and at the run length.

## Not recomputed independently

- **MC-A's analytic multiply-adds per update.** These are an *input* computed with the frozen formula of ADR-0021 §22 M6 (`studies/p10s1/frozen.py` at 46bf55a, run by `make_madds_input.py` from the archive): `madds_per_update.json`. Reproducing the formula would need the model's shapes. The ratios used are in that file.
- **Printed annotations only.** H8's UNDERTRAINED and NOT CALIBRATED annotations, the counted-work table and the crowding note are not recomputed. They enter no rule.

## How it was tested, and the discrepancies found (all my own errors, now corrected; every failed run is kept)

**On the counting rehearsal** (`P10IS1-counting-20261121`, one replicate):
- The study's frozen analysis was run from the archive by `run_study_analysis_on_rehearsal.py`, with the replicate count patched to 1 in memory, because the rehearsal has a single replicate.
- `compare_run1.out` gave **20 differences**. All came from my restricting an arm's own full length at a ladder cell to points at or above U0. ADR-0024 §7.2 item 6 says "the first ladder point at which it was full, read on snapshots up to U_run", with no lower bound. Corrected.
- After that: `compare_run2.out`, **0 of 628**.

**On 18 synthetic five-replicate run directories** (`make_fuzz.py`, seeds 1–6, 101–106 and 201–206):
- They were built from the rehearsal's records with seeded perturbations: DEP failures, leakage, REF failure, drift and noise, qualification drops and CPU costs per arm or per cell. Both programs were run on each.
- **u_T and the dense speed (seeds 5 and 6).** My u_T stopped with a "depfail" kind where the study returns right-censored with a DEP flag. The verdicts were identical, so this was a representation difference, but it would have mattered for dense speed. I adopted the study's reading, which is the one that cannot favour the store. I also made dense speed per panel: either panel for DENSE FASTER, both panels for DENSE NOT FASTER. The ADR text does not state the panel rule for dense speed. `PENDING LEAD REVIEW` if he wants it written down.
- **Capacity MC (seeds 201–206): 80–150 differences per seed.** I had not applied ruling 1 / §9.1: in a reading where the larger cell costs no more per update, U_MC = U_P. Corrected.
- **Final regression** (`final_regression.out`): **0 differences in every one of the 19 runs**, about 43,000 compared values in all: per-panel verdicts, Δ_MU, Δ_MC in each reading with its snapshots and status, Δ_SAT, Δ_FULL, classes, dense labels and counts, d_sat, lengths, ρ, u_T bounds, sparse ratios, R2 failures, ladder stops and the three lines.
- **Efficiency verdict directly** (`compare_eff_verdict.py`): 20,000 random u_T and cost cases against the study's frozen `classes.efficiency_step`. **0 differences**, all eight verdicts exercised.

**What the tests never reached**, so it has not been cross-checked end to end (`coverage_final.out`):
- CAPACITY-POSITIVE and CAPACITY NOT TESTED;
- the arm classes CAPACITY_NOT_SUPPORTED and NOT_TESTED_BY_LOAD; the step classes REVERSED and NO GAIN;
- NOT BEHIND DENSE and DENSE SPLIT; STORE HOLDS MORE AT SATURATION;
- SATURATION-SUBPROPORTIONAL as an outcome;
- the efficiency step classes FASTER STEP, UPDATES-ONLY STEP and SLOWER STEP;
- every dense-speed label, and EFFICIENCY-POSITIVE and EFFICIENCY-NEGATIVE;
- the sparse labels COMPETITIVE and BEHIND;
- the engineering statuses.

These branches are implemented from the ADR text and have not been compared with the study's code.

## Readings that are interpretations (stated so that they can be reviewed)

- **Strict comparisons.** I use exact float comparisons; the study uses a tolerance of 1e-12. A value within 1e-9 of a threshold should be looked at by hand.
- **Arm-level dense label.** For an arm with no CAPACITY STEP it is NOT APPLICABLE, even where dense-at-saturation is DENSE HOLDS MORE (§9.2, "Arm-level combination").
- **The sparse label** needs both panels in a replicate.
- **The one-replicate outputs** (`rehearsal_*`) are a test of code only. They are not results, and their labels mean nothing.

## Leftovers

Listed in `experiments/_scratch/CLEANUP_LOG.md`: `fuzz_s*/`, about 152 MB of synthetic data, and a `__pycache__/`. Keep `frozen/` until the registered recomputation is done.
