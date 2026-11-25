# P10-I-S2 Part T — independent implementation audit (before any Part T rehearsal)

Auditor: `arbor-auditor` subagent, model Claude Opus 5.5 (claude-opus-5-5). Date 2026-11-19 (local).
`Astra review: NOT_PERFORMED`. This is an engineering and mathematical audit. It is not Astra validation and not human approval. Nothing here is a transfer, retention or memory result: no Part T value exists.

**Object:** `git archive 3d92e65` (branch `claude/p10-i-s2-impl`; the commit that holds the Part Q outcome record), extracted to `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-partt/`. I did not read the implementer's live worktree. Paths below are relative to that copy.

**Specification read:** ADR-0025 in full; its attempt-3 addendum; ADR-0022 §6.3 and §12.3 where ADR-0025 cites them; ADR-0029 §13; the Part Q outcome record and `audit/RECOMPUTE_P10IS2_PARTQ.md`.

## Verdict: NOT READY

The scientific core is right:

- **Labels, quantities and the order of reading.** My own implementation from the ADR text agrees with the study's on 60,000 random registries: 0 disagreements.
- **Thresholds.** Every one equals the ADR.
- **Arms.** Each arm trains and freezes what the ADR says.
- **Permutation controls.** They act on the rows and codes of §5.2.
- **R-gloss-icl.** It follows the amended segment rule.

The engineering around that core is not ready. Four findings block any rehearsal:

- The counting rehearsal cannot run on the real data, and if it did it would test nothing of the registered path.
- Both rehearsals score E_A and E_B before the registered run. The ADR forbids that.
- The registered path deadlocks between the recomputation and the analysis.
- The caps cannot be computed from the measuring rehearsal, which also does not measure what the caps need.

This repeats Part Q's defect classes: the rehearsal path differs from the registered path; timing is measured inside one process; there is a chicken-and-egg precondition. Fix the BLOCKING and REQUIRED items and re-audit before the measuring rehearsal is spent.

## How I checked (commands; environment)

- **Environment.** macOS 27.2.1 arm64; `/Users/daniellaloush/dandush03/ArborLM/.venv/bin/python` (Python 3.12.14, torch 2.8.0). I ran one process at a time, each under `timeout`, on CPU only. I used test-range seeds only: the study's tiny world (934001–934999, 330298/330299) and my generators 934101/934102.
- **Data.** No real training and no teacher run. No sealed value was opened.
- **Part Q files.** From Part Q's run directory I read file NAMES and JSON KEYS only: the manifest structure, the panel names and sizes in `partition.json`, and the keys of `result.json` and `gloss_bank.json`. I read no scores.
- **Writes.** Scripts and outputs are under `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-partt/_audit/`. Nothing was written to /tmp. There were no git writes.

```sh
A=/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-partt; PY=/Users/daniellaloush/dandush03/ArborLM/.venv/bin/python
git -C /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f archive 3d92e65 | tar -x -C $A
cd $A
timeout 900  $PY -I -B _audit/compare_labels.py "$PWD" 20000 934101            > _audit/out/compare_labels.txt           # random registries
timeout 1500 $PY -I -B _audit/compare_labels_boundary.py "$PWD" 40000 934102   > _audit/out/compare_labels_boundary.txt  # canonical positive + 0-10 boundary perturbations
timeout 900  $PY -I -B _audit/probe_engine.py "$PWD" "$PWD/_audit/scratch"     > _audit/out/probe_engine.txt
TMPDIR=$PWD/_audit/scratch timeout 1500 $PY -B -m pytest -q -p no:cacheprovider --basetemp=$PWD/_audit/scratch/pytest \
  tests/test_p10is2_partt_{labels,rules,plan,gates,tasks,real,stage8,annotations,e2e}.py tests/test_p10is2_engine.py   # 113 passed (314 s)
```

Script SHA-256 values:

| Script | SHA-256 |
|---|---|
| `ref_labels.py` | `967c2316…` |
| `compare_labels.py` | `0aa7d2c3…` |
| `compare_labels_boundary.py` | `78ac4f1e…` |
| `probe_engine.py` | `d05d84e2…` |

`ref_labels.py` imports nothing from `studies/`. The two compare scripts and the probe import the study's modules only as the system under test.

**Discrepancies of my own.** The first boundary run wrote an empty output file. I ran it at 60,000 registries and redirected stderr into the same pipe, so the cause was most likely the stderr redirection. I re-ran it at 40,000 with stderr kept separately; that is the recorded run. The random run (20,000) and the boundary run (40,000) make 60,000 registries.

## 1. Labels, quantities, order of reading (§8)

**Thresholds.** Every one in `configs/p10is2_partt.toml` equals ADR-0025 or the ADR-0022 value it carries:

| Group | Values |
|---|---|
| Gap and acquisition | gap denominator 0.30; ACQ gap 0.50; lexical margin 0.30; marker-only 0.25; ACQ2 ratio 0.80 |
| Retention | F 0.03; ρ 0.90; negative zones 0.25 / 0.70 |
| Cell counts and pressure | forgetting pressure 4 cells, G_second 0.50, ρ 0.90; RETENTION-NEGATIVE 4 cells; CONTROL-FAILED 0.50 |
| GEN and comparisons | GEN 0.02 nats; dense 0.05; lookup 0.03 / 0.05; second not acquired 0.50 |
| M-ii | D_con 0.02; modification floor 0.10 |
| Pilot and combined tasks | pilot 0.25; COMPOSES 0.80 / 0.50 |
| Calibration | subsample 300; rates {0.001, 0.003, 0.01} and {0.0001, 0.0003, 0.001}; tie 0.01; ladder {1,000, 2,000, 4,000}, top 8,000; convergence 0.01 |
| Design | N 4,096; ranks 42 / 84; top-8; temperature 0.2 |
| MPS gate | 1e-3 and 1e-4 |
| Timing | 2.0 load / 60 s / 30 min / 5 attempts / CV 0.05 / 200 items / 3 repetitions |
| Caps and memory | 3.0 h + 3.0 h; 8 / 24 GiB; 3 workers, 2 when shared; 10 GiB disk |

The only departure is a code use: G4 runs 4 CPU updates, not the configured 20 (R4).

**Agreement with my reference.** My reference (`_audit/ref_labels.py`) implements ACQUISITION, RETENTION, GENERAL-QUALITY, AGAINST-DENSE (both pairs), AGAINST-LOOKUP, MODIFICATION and the milestone line from the ADR text. Compared with `labels.derive_all` on 20,000 random and 40,000 boundary-perturbed registries: **0 disagreements, and no input without a label or with two labels.**

**Labels reached.** Every row of every line was reached except:

- MODIFICATION's FORGETS UNDER MODIFICATION.
- AGAINST-LOOKUP's LOOKUP SUFFICES was reached only in the random run.

The tests reach the remaining rows on hand-built registries.

**Points the comparison confirms:**

- Row 2 of RETENTION is read before FIRST NOT ACQUIRED, over evaluable cells only. A retention failure in at least four evaluable cells cannot become NOT EVALUABLE.
- CONTROLS UNDEFINED removes control passes and never makes CONTROL-FAILED fire.
- Δρ is guarded.
- A missing GEN reading gives NOT EVALUABLE, never NOT PRESERVED, even when another reading is above 0.02. The milestone line is then NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE), never WITHHELD.
- The "+ consolidation" suffix needs RETAINS UNDER MODIFICATION and M-ii's GEN to pass.
- **Study status** (`labels.study_status`) is read first and derives nothing under: ENGINEERING-FAILURE, item errors, a non-finite value, a recomputation failure, or a required key that is missing (INCOMPLETE).
- `partt_plan.required_keys()` covers every key the lines read, so a missing record cannot reach a rule as a `Missing` exception.
- A NaN GEN reading is caught as ENGINEERING STOP — NON-FINITE VALUE before any line.

**Gaps in the second guard (ADVISORY A7).** GENERAL-QUALITY and AGAINST-DENSE take no `recompute_failed` argument. The study status stops first, so this cannot move a label.

**No input reaches a label more favourable than the text.** The labels' wiring does have unfavourable or unfaithful inputs, listed under R9 and R13.

## 2. Engine and arms (§5, G4–G6)

**Probe results** (`probe_engine.py` on the study's tiny world, CPU, parents loaded from snapshots as the registered worker does):

- **Trainable parts.** M-append trains only stage 1: 3 tensors, its keys, values and gate. Stage 0 receives no gradient.
- **Student.** No student parameter gets a gradient in any arm.
- **D-append.** The first adapter receives no gradient; only the second trains (12 tensors).
- **M-seq.** Trains stage 0.
- **M-ii.** Trains both stages, with 32 replayed first-teacher examples per batch, ordered by a fresh +2 generator.
- **D-seq.** Continues D1's adapter, which is trainable after loading.
- **Joint arms.** M-joint has 2N rows and runs 2U; D-joint has rank 84 and runs 2U.
- **CPU determinism.** Two runs of the same cell give the same hash. The snapshot round trip holds.
- **Reads.** M-append's top-8 is one scan over all 2N rows.
- **Addresses** are (task, word) codes from the +10 seed. G6 compares the reads of a training row with those of its prompt.
- **Seeds.** Every seed is in the registry plan (250001 + 1, 2, 4, 10, 13; 330201 + 10r + j). They are distinct across replicates.
- **Repeated calibration.** It uses the listed values 330261/330271, not the formula.

**Controls** (`scoring.CONTROL_STAGES`):

| Arm | Value rows permuted | Codes permuted |
|---|---|---|
| M1 | stage 0 | first task |
| M-append | stage 1 | second task |
| M-seq | stage 0, all N rows | second task |
| M-ii | stages 0 and 1, all 2N rows | second task |
| M-joint | stage 0, all 2N rows | both tasks, each read on its own panel |

This is as §5.2.

**R-gloss-icl** (`scoring.gloss_icl_ids`):

- Lines come from the replicate's lexicon (same `gloss_lexicon` and `normalize`), in source order, repeats kept.
- The first line uses `source_words`; later lines use `source_words_after_newline`. Then the separator, the gloss word, and the last newline as the bank's recorded rule says.
- The task prompt is S0's, unchanged.
- This duplicates Part Q's `partq/gloss.icl_prompt_ids` line for line by reading (A9).

**Sequential order.** M-seq, M-append and D-append, D-seq continue the stage-1 snapshot of the same cell. M-ii continues M-append's result. M-joint and D-joint are trained once on mixed material. The waves in `partt_tasks.WAVES` respect these dependencies.

## 3. Findings

Directions are with respect to the memory (M-append):

- **favours** means the defect could make a positive transfer, retention or memory label easier.
- **against** means harder.
- **neutral** means an engineering or record defect with no label direction.

### BLOCKING

**B1 — The counting rehearsal is not a rehearsal of the registered path, and cannot run on the real data.**

- *Where:* `partt_real.py:204–232`; `partt_stages.py:147–158`; `common/gates.py rehearsal_gate`.
- *Spec:* §10 item 4: "Tasks, items, labels, paths and manifests are enumerated from it". §11 item 5: "For Part T: every cell type, one cell of each trained type at full U, one combined scoring of each arm kind, one forced pause and resume". ADR-0029 §13: "rehearsal of every stage end to end against the frozen plan itself".
- *Code:*
  - The plan file only supplies its SHA-256. Nothing is enumerated from it.
  - `partt_run.train_all` trains ALL 54 cells of ALL three replicates at full U, in one process, outside the task runner. That is the whole registered training (7–52 h) under a 3.0 h cap.
  - In `rehearsal` mode replicates 1 and 2 have no seeds. My probe: `SeedPlanT(cfg,"rehearsal",1)` raises "SeedRefused: the Part T rehearsal uses draw 0 only". The rehearsal therefore stops at replicate 1.
  - Evaluate, controls and analysis are written `COMPLETE` unconditionally (lines 224, 230).
  - None of these is exercised: the worker processes and their freeze re-check, `make_tasks`/`run_tasks`, `run_task`, `merge_results`, the recomputation, the item-error path, the cap ledger. The freeze's `rehearsal_gate` would still accept the record.
- *Fix:*
  - Drive `partt_stages registered/work` (the same entry point and task runner) against the candidate plan, in a rehearsal run directory, with a rehearsal-mode flag.
  - Take a plan-derived subset: one cell of each of the ten trained types at full U (rehearsal seeds, draw 0), one combined scoring of each arm kind, the recomputation, the analysis and the report on a synthetic registry keyed by the plan's labels.
  - Write each stage's status from its real manifest.
- *Direction:* neutral. A freeze could otherwise be taken on a record that exercised none of the registered code.

**B2 — Both rehearsals score the evaluation panels, on the registered training draws.**

- *Where:*
  - `partt_real.py:189–192` (`measure_rates` scores M1 on 20 items of E_A and E_B).
  - `partt_real.py:221–227` (the counting rehearsal runs `score_all`, which covers the full E_A and E_B, controls and lookups, then `run_gates` G2, which scores the full E_A and E_B twice).
  - `load_part_q` (lines 40–42) returns the registered replicate draws in every mode.
- *Spec:* §4.1, panel table: E_A, E_B, E_C, E_open are "**Never scored before the registered run of Part T**". §10: the Part T measuring rehearsal runs "with the rehearsal seeds of section 6 and **D_cal only**".
- *Code:* scores of trained modules on E_A and E_B are computed before the freeze, and snapshots trained on the registered draws stay in the rehearsal directory. Nothing is printed, but nothing seals or forbids it either.
- *Fix:*
  - Rehearsals score D_cal only (D_con for the M-ii constraint, if needed).
  - G2 in a rehearsal scores D_cal.
  - Rehearsal training material should not be the registered replicate draws. This is a ruling (Q1 below).
- *Direction:* **favours the memory.** Evaluation-panel information exists before settings, U and the code are frozen.

**B3 — Recomputation and analysis deadlock on the registered path.**

- *Where:* `partt_real.py:410–419`, `292–294`, `381–396`.
- *Spec:* §8.6: no result is reported before every registered score is recomputed. The pattern: "a stage never requiring a record only it or a later stage writes".
- *Code:*
  - The evaluate tasks write `tasks/evaluate/*.result.json`.
  - `run_recompute` reads `run_dir/registry.json`, which only `merge_results` writes.
  - `merge_results` is called only by the analysis stage, after `require_recomputation`, which refuses without `recomputation.json`.
  - So the recomputation fails with FileNotFoundError and the analysis refuses forever. The in-process `run_stage("evaluate")` would write `registry.json`, but the registered entry point never takes that path.
  - The recomputation is also not a plan stage: it has no cap and is not rehearsed.
- *Fix:* merge the results at the end of the evaluate and combined stages, as a plan stage, or as the first step of the recomputation. Make the recomputation a registered stage with its own cap (ruling Q7).
- *Direction:* neutral.

**B4 — Caps by code cannot be computed, and the measuring rehearsal does not measure what they need.**

- *Where:* `partt_real.py:172–201`; `partt_stages.py:203–209, 222–228`; `partt_tasks.py:81–84`; `common/caps.py:12–20`.
- *Spec:* §10 items 2–3; §9; L2; §7.1 rule 4.
- *The measuring rehearsal must* measure, on MPS, 200 updates of every trained cell type; 20 scoring items of each kind on CPU, D_cal only; combined scoring of one arm of each kind; router training; the gates; and the benchmark's duration. It must record peak memory per worker, disk use, the load average and the other studies alive with every figure.
- *Code:*
  1. Rates are keyed `train:M1`, `train:D1`, `train:M-joint`, `train:D-joint`, `router_seconds`, `score_seconds_per_item`, `combined_seconds_per_arm_cell`. Units are keyed `train`, `evaluate`, `combined`. `project_stage_seconds` raises `ValueError: no measured rate for stage 'train'` (my probe), so the freeze and `caps-proposal` crash.
  2. The units are of the wrong kind. `evaluate` counts plan items (about one per cell) and multiplies them by seconds per SCORED SENTENCE. One evaluate task scores about 72,400 greedy items.
  3. Six of the ten trained types are not measured: M-append (2N scan), M-seq, M-ii (64 examples per batch), D-append (two adapters), D-seq, E-table.
  4. Only one scoring kind is measured. Missing: the controls, R-icl (long prompts), R-gloss-icl, D_con, learned routes, GEN.
  5. There is no per-process overhead. Each worker re-reads and re-hashes the bundle and rebuilds the bank. This is the defect "caps measured inside one process" again.
  6. There is no load or other-studies record, no disk figure, and no MPS memory.
  7. Gates, controls, analysis, calibration and the recomputation get no projection. Their configured caps stay 0.0, which `stage_cap_for` turns into 1e12 (uncapped).
  8. The pre-freeze charge comes from `meas["charged_before_freeze_seconds"]`, a key the measuring record never has, so it is always 0. Meanwhile `rehearse` and `calibrate` charge no ledger at all, so Part T's pre-freeze charge (calibration about 4–7 h plus the rehearsals) is recorded nowhere.
  9. `caps-proposal` takes its units from a hand-written `--units` file, not from the plan.
- *Fix:*
  - One shared function: projected seconds per stage = Σ over the plan's task kinds of (count from the plan × measured seconds per unit of that kind) + tasks × measured per-process overhead.
  - Measure every kind through the registered entry point, in fresh processes, with whole-process timing.
  - Charge every Part T process (rehearsals, calibration, the counting rehearsal) to one Part T ledger.
  - The freeze reads the pre-freeze charge from that ledger. How the counting rehearsal's own charge enters is ruling Q4.
- *Direction:* neutral (resources). Uncapped stages and a total that omits the pre-freeze charge break the cap rule both ways.

### REQUIRED

**R1 — Part T reads Part Q files without checking them against the Part Q manifest (the open advisory, confirmed).**

- *Where:* `partt_real.py:31–52` (`load_part_q`) and `321–323` (`calibrate_command`); `partt_stages.py:242–246`.
- *Spec:* L12: "The Part Q manifest's files only, by hash." §11.2 lists the Part Q manifest among Part T's frozen inputs.
- *Code:*
  - `outputs/bundle/*` is checked only against the bundle's OWN `manifest.json` (`read_bundle`), which is not compared with Part Q's run manifest.
  - `outputs/gloss_bank.json` (listed in the attempt-3 manifest) is not checked.
  - `generation/pools.json` and `generation/result.json` are not checked. They are reused attempt-2 files (attempt 3's `generation` is a symlink into attempt 2's directory) and are absent from the attempt-3 manifest's `files` (259 entries). They are covered only by the attempt-3 plan's reuse list and tree hash.
  - The freeze verifies only the hashes of `manifest.json`, `ACCEPTANCE` and the panel ledger as files.
- *Fix:* one reader that, at every task start, hashes every Part Q file it opens against the attempt-3 manifest's `files`, or for reused files against the frozen attempt-3 plan's reuse list. A difference is PAUSED — IDENTITY. Read the training pools from the listed `outputs/bundle/accepted.json` (the Part Q recompute verified it equals `pools.json`) rather than `generation/pools.json`.
- *Direction:* neutral.

**R2 — The Part Q run directory is not in the plan, and the registered launch cannot reach it.**

- *Where:* `launch/partt_registered.sh` passes no `--part-q-dir`; `partt_stages.py:322` defaults to `.`; `make_tasks` passes it on.
- *Effect:* the registered path reads `./outputs/bundle` in the repository and fails.
- *Fix:* the plan names the Part Q run directory (attempt 3) and its manifest by path and hash. Tasks take it from the plan, never from the command line.
- *Direction:* neutral.

**R3 — Gate G1 crashes on the real bundle.**

- *Where:* `partt_gates.g1` → `studies/p10s2/data.py gate_g1`.
- *Code:* `gate_g1` indexes `p.panels["Q_check"]`. Part Q's bundle holds D_cal, D_con, E_A, E_B, E_C, E_open and Q_fit, with no Q_check. The synthetic bundle in the tests has Q_check, so the tests pass. My probe on a partition without Q_check gives `KeyError: 'Q_check'`.
- *Fix:* give G1 the Q_check identity groups and keys from Part Q's records, by hash (ruling Q6), or use a Part T copy of G1 over the panels the bundle has plus those groups.
- *Direction:* neutral. The gate would stop the registered run.

**R4 — G4 does not test what it names.**

- *Where:* `partt_gates.py:44–58, 163`.
- *Spec:* ADR-0022 §12.3, carried by ADR-0025 §7.3: "gradient reach (in M-append-frozen no first-stage row, gate or student parameter receives a gradient; in every memory arm no student parameter does)", plus "the frozen first adapter"; "20 updates on CPU repeated bit-identically".
- *Code:* gradient reach is run on M1 only, which has no frozen part. CPU determinism uses 4 updates. G5(b) ("a new store with gate 0 on an empty base changes nothing") is not tested.
- *Note:* my probe shows the engine itself is correct.
- *Fix:* run gradient reach on M-append, M-seq, M-ii, D-append and D-seq, built from loaded parents. Use 20 updates. Add G5(b).
- *Direction:* neutral.

**R5 — Per-item records are not stored, so the auditor's §8.6 recomputation is impossible.**

- *Where:* `scoring.panel_means` (36–43) and `reference_reads` (62–78) store means only. Routers are trained inside scoring and not snapshotted (81–88).
- *Spec:* §8.6: "with the auditor's own code every greedy sequence must be identical and every item score within 1e-6". The same gap was Part Q's correction C1, for the untrained student.
- *Fix:* store, hashed, every greedy token sequence and every item chrF for every registered read (S0 and the teacher included), and snapshot each router.
- *Direction:* neutral.

**R6 — The `controls` stage repeats the whole evaluation.**

- *Where:* `partt_real.py:357–363`.
- *Code:* both the evaluate and controls tasks call `score_replicate`, which already includes the controls. `merge_results` reads evaluate only.
- *Effect:* one more full scoring pass, about 217,000 greedy items or about 5.4 h at the P10-S2 anchor, outside ADR §14's projection.
- *Fix:* split the work, or drop the stage.
- *Direction:* neutral (cost).

**R7 — Calibration records are overwritable and not bound to the plan; calibration has no cap and no charge.**

- *Where:* `partt_real.py:315–332` (`overwrite=True`); `partt_stages.py:181–186`; `partt_plan.py:125`.
- *Spec:* §7.1 rule 4: earlier records are kept and marked SUPERSEDED; the repetition used is never chosen on its values; calibration runs under a computed cap.
- *Code:*
  - The plan's U, rates, layer and `pilot.passed` come from a `--calibration` JSON assembled by hand. Only its `records`' code hashes are checked.
  - Re-running `calibrate` overwrites `calibration_<rep>.json`.
  - MPS training is not bit-reproducible, so a failed pilot could be redrawn by re-running with the same seeds.
- *Fix:*
  - `overwrite=False`, with every attempt kept.
  - The freeze re-derives U, the rates, the layer and the pilot from the calibration record files, listed in the plan by SHA-256.
  - Calibration runs through a capped and charged entry point that refuses if a record for that repetition exists.
- *Direction:* **favours the memory** (a pilot or a rate selection could be redrawn or entered by hand).

**R8 — `recomputation.json` is overwritten.**

- *Where:* `partt_recompute.py:82`.
- *Effect:* a failed recomputation (ENGINEERING STOP — RECOMPUTATION) can be erased by running it again.
- *Fix:* keep every attempt. The analysis refuses if any attempt differs, unless a lead record names the cause (§8.6).
- *Direction:* **favours the memory**.

**R9 — ENGINEERING-FAILURE cannot be reached, and the ensemble integrity check is missing.**

- *Where:* `partt_real.py:300` (`engineering_failure` is never passed); `partt_real.py:369–373`; `partt_run.combined_reference`.
- *Code:*
  - A failed gate becomes an item error, and the status reads "ENGINEERING STOP — ITEM ERRORS".
  - §8.6's "the oracle-routed ensemble's score differing from the teacher's own" is computed nowhere.
- *Fix:* the gates record and the ensemble check feed `engineering_failure`.
- *Direction:* neutral. No line is derived in either case, but the registered status would be wrong.

**R10 — A precondition refusal in a worker becomes an item error, not a pause.**

- *Where:* `partt_stages.py:341–343`; `common/plan.py:259–260`.
- *Code:* any refusal other than a frozen-file difference (for example an untracked note in the worktree: "the working tree is not clean") exits 2. The runner records FAILED, an item error is written, and each task then needs a `retry`. The runner's own docstring says a dirty tree exits 75 (PAUSED — IDENTITY). This is the class of the "171 cells refuse" incident.
- *Fix:* every precondition refusal in a worker exits 75.
- *Direction:* neutral.

**R11 — The timing benchmark's "nothing alive" check counts the benchmark's own `uv` parent.**

- *Where:* `common/procs.own_study_alive` (28–37); `partt_timing.anything_alive`.
- *Code:* the check excludes only its own pid. Launched as `uv run … python -m studies.p10is2.partt_stages timing`, the live `uv` parent's command line contains "python" and "studies.p10is2", so the stage refuses at every opening.
- *Fix:* exclude the process's ancestors.
- *Direction:* neutral (a descriptive stage).

**R12 — A test depends on the planning state.**

- *Where:* `tests/test_p10is2_partt_plan.py:124`.
- *Code:* it asserts that the real repository has no Part T plan and no freeze record, so it fails as soon as the candidate plan is written.
- *Fix:* use a temporary repository.
- *Direction:* neutral.

**R13 — M-ii in a CONSOLIDATION-REJECTED cell is not replaced by the pinned M-append snapshot.**

- *Where:* `partt_run.score_replicate`, `combined_replicate`; `labels.acquisition` lines 77–86.
- *Spec:* §8.5: "In a CONSOLIDATION-REJECTED cell, M-ii's snapshot for every other reading is the pinned M-append snapshot, and it is marked as such."
- *Code:* the unpublished M-ii is scored, its controls feed CONTROL-FAILED, and its combined tasks are recorded.
- *Fix:* in rejected cells, register M-ii's reads from M-append's snapshot, marked.
- *Direction:* against the memory for CONTROL-FAILED (an extra chance to fire); neutral elsewhere.

**R14 — The report omits what the ADR prints with each line.**

- *Where:* `report.py:39–59`.
- *Missing:*
  - The RETENTION per-cell table, with the number of evaluable cells in the negative zone.
  - The passing cells per order.
  - CONTROLS UNDEFINED.
  - The per-cell values behind NOT EVALUABLE.
  - AGAINST-DENSE's companions: the M-sep and D-sep scores, NO ADVANTAGE OVER SEPARATE ADAPTERS and the counted multiply-adds.
  - WITHHELD's false-trigger rate and per-cell loss increases.
  - The annotations, the cost lines, the seen-item and E_open lines (A4), and the edit-distance-1 share with the scores without those items (§5.3).
- *Direction:* neutral.

**R15 — No guard separates the rehearsal and calibration directories from the registered run directory.**

- *Where:* `partt_stages.cmd_rehearse`, `cmd_calibrate`.
- *Code:* they check only that the directory is git-ignored. They may write into the plan's registered run directory, and the registered stages do not refuse a directory that holds rehearsal records.
- *Fix:* both refusals.
- *Direction:* neutral.

### ADVISORY

1. **A1.** `engine.py:284`, `getattr(world, "etable_lr", world.store_lr)`: a missing E-table rate silently becomes the store's rate. Make it required. Direction: favours the memory (a mis-tuned baseline).
2. **A2.** `engine.py:355` deletes the checkpoint before `run_cell` saves the final snapshot (`:376`). A crash between the two loses the resume point. A snapshot saved but not recorded makes the resume fail on FileExistsError. Delete only after the snapshot (G20).
3. **A3.** The Q_fit panel (keys and references, no scores) is loaded into the world. Only G1 uses it. Ruling Q3.
4. **A4.** Seen items are the first 300 of the training draw (`engine.py:125–126`), not Part Q's seed-250912 order. Seen-item and E_open scores are not computed. Both are descriptive.
5. **A5.** AGAINST-LOOKUP names the baseline that is best most often, not the baseline per cell. Ruling Q5.
6. **A6.** `annotations.composition` covers 4 of the 12 arm-cells (not M-joint, D-joint, M-sep, D-sep).
7. **A7.** GENERAL-QUALITY and AGAINST-DENSE take no `recompute_failed` second guard; the status stops first.
8. **A8.** Calibration code hashes are taken at the END of calibration. Take them at the start and refuse a change during the run.
9. **A9.** Add a test that `scoring.gloss_icl_ids` equals Part Q's `icl_prompt_ids` on the real bank, for every replicate lexicon.
10. **A10.** `cmd_timing` builds a ledger with total `max(1.0, total_hours*3600)`, which is 1 s while caps are unset.

## 4. What Part T reads from Part Q (summary)

| File read | Listed in the attempt-3 manifest? | Checked by Part T? |
|---|---|---|
| `outputs/bundle/*` (partition with Q_fit, accepted, bank, windows, teacher outputs, student) | yes (`outputs/bundle/*`) | only against the bundle's own `manifest.json` |
| `outputs/gloss_bank.json` | yes | no |
| `generation/pools.json`, `generation/result.json` (symlinked into attempt 2) | no; reuse list of the attempt-3 plan only | no |

- **Sealed values.** No Part Q sealed value is read, and no Q_fit or Q_check per-item score. The Q_fit panel's keys and references are loaded through `partition.json` (A3).
- **Attempt 3's directory.** It is read correctly through the symlinks, but it is not named in the plan (R2).

## 5. Cost, counted from the plan

**Trained cells.** Per replicate: per order, M1, D1, M-append, M-seq, M-ii, D-append and D-seq (14 cells), plus M-joint, D-joint and E-table A and B. That is 18 per replicate and **54 in all**, which matches §14.

**Units of U.** 42 store-type, of which M-ii is 12 because of its 64-example batch, and 24 LoRA. **66 in all**, as §14 says.

**Calibration.** 36 units of 2,000: 22 store-type and 14 LoRA (`calibration.calibration_units`). This matches §14.

**Scoring, greedy decodes per scoring pass:**

| Item | Greedy decodes |
|---|---|
| Full panels: 22 snapshot-pairs per replicate × 2,000 | 44,000 |
| Learned-route reads of M-append | 4,000 |
| Controls: 4 memory arms × 6 runs × 300 × 2 orders, plus M-joint 2 × 6 × 300 | 18,000 |
| D_con | 2,400 |
| R-icl and R-gloss-icl | 4,000 |
| **Per replicate** | **72,400** |
| **Three replicates, plus S0's 2,000** | **about 219,000** |

At P10-S2's anchor of 0.089 s per greedy answer, one pass is about 5.4 h for one worker. R-icl's longer prompts cost more.

**Passes in the code.** The code runs a pass in evaluate, again in controls (R6), and again in the recomputation. That is three passes, where the ADR has two (registered and recomputation).

**ADR arithmetic.** It checks:

- Training 7–13 h at U = 2,000 (42 × 5–10 min + 24 × 8–15 min = 6.7–13 h).
- Calibration 3.7–7.2 h.
- Total 21.2–57.9 h at U = 2,000.
- 41–97 h at U = 8,000 (training 27–52 h). The ADR prints 41–96.

**What can stop early by rule:**

- Calibration: every rate of a module type diverges, or a non-finite value appears in the ladder or the pilot (CalibrationStop, back to the human lead).
- The pilot gate (NOT STARTED: PILOT, and nothing more is trained).
- A failed gate (ENGINEERING-FAILURE before training).
- A non-finite cell (its dependants are skipped).
- No label stops the run early.
- The convergence ladder can pick a smaller U, cutting training cost by up to a factor of 8.

## 6. Machine requirements (quiet stages)

**Only stage 7, the descriptive timing benchmark, needs a quiet machine.** Its condition is:

- No process of THIS OR ANY OTHER study alive at the opening and before each repetition.
- A 1-minute load average ≤ **2.0**, read BEFORE each repetition, after ≥ 60 s with no study process.
- Each repetition must start within 30 minutes of the attempt's opening.
- After five attempts without three repetitions, the lead records NOT MEASURED.

No label reads it. The figure is 2.0, not P10-I-S1's 1.0.

How often this machine meets 2.0 is unmeasured. My one sample was 3.13 / 4.07 / 3.21 (1, 5 and 15 minutes) with the implementer's test run and another study alive. As coded it is unreachable when launched through `uv run` (R11).

**Every other stage** shares the machine: at most 3 workers, 2 while another study runs; 8 GiB per worker; 24 GiB aggregate, 16 GiB when shared. No wall time enters a label.

## 7. Rulings needed from the lead (PENDING LEAD REVIEW)

1. **Q1.** Which training material Part T rehearsals use. Today they use the registered replicate draws with rehearsal seeds. Alternatives: a draw from the pool with seed 252002 (rehearsal +1), or a calibration-style draw.
2. **Q2.** Calibration draws are random 8,000-item draws from the whole accepted pool, so they overlap the registered disjoint draws. Is that acceptable? ADR §7 does not say.
3. **Q3.** Is the Q_fit panel excluded from Part T entirely, or kept for G1's disjointness check only (keys and references, no scores)?
4. **Q4.** Which charges make up Part T's pre-freeze charge (measuring rehearsal, calibration and its repetition, counting rehearsal; Part Q's 13.48 h is Part Q's), and how the counting rehearsal's own charge enters a plan that must exist before it runs. Part Q's attempt-3 Decision 2 excluded it by ruling.
5. **Q5.** In AGAINST-LOOKUP, "the baseline that gave b is named": per cell and capability, or the most frequent?
6. **Q6.** The source of the Q_check groups and keys for G1 (Part Q's partition records, by hash).
7. **Q7.** Is the recomputation a registered stage with its own cap, placed before the analysis? §8.6 requires it before any result; §10 lists it as stage 8.
8. **Q8.** Routers are trained objects. Are they snapshotted and re-read in the recomputation, or retrained bit-identically?
9. **Q9.** The pinned M-append snapshot in a rejected M-ii cell also applies to CONTROL-FAILED (R13). Confirm.

## 8. What a rehearsal must show that no test can

- G1 and G8 on the real bundle.
- G4's MPS-against-CPU gate on this machine.
- Seconds per update of all ten trained types on MPS at N = 4,096 and the real student.
- The peak RSS and MPS memory of a worker against the 8 GiB guard.
- The per-process overhead of building the world (bundle hashing, bank).
- Real R-icl and R-gloss-icl prompt lengths against the truncation limit, and that no gloss word of any replicate lexicon is missing from the bank.
- GEN and route accuracy on the real windows.
- Disk per snapshot and checkpoint.
- A forced pause and resume, and a forced PAUSED — IDENTITY, of an MPS cell through a worker process.
- Bit-identical CPU scoring across two fresh processes, with routers.
- The recomputation reading what the evaluate tasks wrote (B3).

## 9. Not audited

- `partt_cost.py` (cost recording) beyond the multiply-add function. I checked `cost.py`'s hand rules by reading. The parameter counts match: 2,419,200 for LoRA and 2,424,833 for the store.
- P10-S2's reused modules beyond the functions named above. I did not re-audit `routing.train_router`, `combined.py`, `evaluate.general_quality`, `model.py` or the chrF implementation (`text.chrf_pair`); P10-S2's audits covered them.
- `annotations.py` rules against ADR-0022 §11.4 in detail. Only their guard and their inputs were checked.
- `launch/` beyond `partt_registered.sh`; `common/panel_ledger.py`; the G9 checker copy.
- The tests of other parts. I ran only the 113 Part T tests named above; all passed.
- No real-data, MPS or multi-process execution: none was permitted.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. Auditor: `arbor-auditor`, Claude Opus 5.5.
