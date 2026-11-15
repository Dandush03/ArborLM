# P8 pre-freeze implementation audit, part 1 (training side)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`, from session metadata), auditor role. This is independent engineering/mathematical evidence only: **not Astra validation, not human approval.** Astra review: NOT_PERFORMED.
- Date: 2026-11-14 UTC. Worktree HEAD `74851bd30546ae1cafacaf6e330e191016721f3a`; audited files are untracked at HEAD and identified by SHA-256:
  - `src/arborlm/p8_core.py` d3a8e949…e09f; `p8_checkpoint.py` 7923516a…713e; `p8_objective.py` b48bf53d…f25e; `p8_train.py` 71f6362b…13f5; `configs/p8_locality_training.toml` ecefef75…66ee; ADR-0015 (rev. 2) 4dee953d…84f9. Tests `tests/test_p8_{core,objective,train}.py` read at the same time.
- Environment: macOS (Darwin 27.2.0, Apple silicon), Python 3.12.14, torch 2.8.0 (uv `--locked`, `--extra pilot`), single thread.
- Scope: training side only. `p8_panel/eval/sim/analysis/pool.py` are out of scope (part 2). No registered stage was run; no validation panel was opened; no write under `experiments/`.

## Verdict: **READY TO FREEZE** (training side), with the MAJOR items below fixed or explicitly accepted by the lead before the freeze commit

No BLOCKER found. Nothing found would invalidate the 60-cell training run. The two MAJOR items concern what the freeze binds (config completeness) and whether the run-time §10.5 gate is actually executed; neither changes a trajectory.

## Findings

### BLOCKER
None.

### MAJOR

**MAJOR-1 — The frozen config/registry lacks ADR §7.2–7.3 constants and carries one with no ADR source.** `p8_core.py:130` (`QUALITY_DELTA, GAIN_MIN = 0.005, 0.005`), `p8_core.py:206-215` (`_REGISTERED["margins"]`), `configs/p8_locality_training.toml:98-106`. ADR §7.3 fixes gain retention ≥ 0.75, association retention ≥ 0.75, "at most one of six pairs above +0.005", and §7.2 fixes "E undefined when the null mean under L-FREQ is below 0.05 misses per query". None is registered; `gain_min = 0.005` does not appear in the ADR. Because the freeze binds the config and every module in `src/arborlm`, the part-2 analysis would have to hard-code these or the config would change after the freeze.
*Fix:* add to `[margins]` and to `_REGISTERED["margins"]` / module constants: `retention_min = 0.75`, `quality_pairs_above_max = 1`, `e_null_floor = 0.05` (misses per query); remove `gain_min` or record its ADR source. Whether `gain_min` is meant as a P5-style positive-gain floor is **PENDING LEAD REVIEW** (the auditor does not choose thresholds).

**MAJOR-2 — The run-time restore gate (§10.5: ten seed-601 cells of B101/O301) is not executed by the registered stage.** `p8_train.py:671-702` (`cmd_stage`) never calls `cmd_restore_check` (`p8_train.py:706-752`); the stage manifest's `status: completed` therefore does not imply §10.5 ran. The restore logic itself is correct and not vacuous (see §3 below).
*Fix (either):* (a) after `run_stage` returns `completed`, call the restore check for the ten labels `b101-o301-s601-C01…C10` and write their results into the stage manifest as `restore_gate: {label: passed}`, making `status` `completed` only if all pass; or (b) put the ten exact `restore-check` commands into the frozen runbook as the mandatory next step and have the analysis refuse to start without ten `P8TR-*` results with `passed: true`.

### MINOR

1. `p8_train.py:776-830` — the p5-invariance gate does not itself tie the restored local P5 `checkpoint-512/state.pt` to the **committed** record. I verified the chain independently (below), so the existing pass is valid. *Fix:* add to `passed`: `file_sha256(folder/"checkpoint-512"/"state.pt") == read_json(core.repo_root()/core.P5_RESULTS/cell.label/"result.json")["checkpoint_state_sha256"]["checkpoint-512"]`.
2. `p8_train.py:88-91` — if the config or spec is absent from the freeze commit, `git show` raises `CalledProcessError`, not `FreezeError`. The stage is still refused before any run directory is created (observed with `verify_freeze("HEAD")`), but the message hides the real cause. *Fix:* wrap the `_git("show", …)` calls in `try/except subprocess.CalledProcessError` and add "missing from the freeze commit" to `problems`.
3. `p8_train.py:67-99` — the freeze check covers `src/arborlm/**/*.py`, the config and the spec, and nothing else. `uv.lock`, `pyproject.toml` and `tests/` could change without detection (the environment record captures the torch version but not the lock). *Fix:* add `uv.lock` and `pyproject.toml` to the `for name in (...)` loop.
4. `p8_train.py:527-584` — aggregate RSS sums only the workers' process trees; the supervisor process (which imports torch) is not counted against the 8 GiB "process-tree" ceiling. Polling is every 0.2 s, so short spikes can be missed. Observed headroom is large (3 workers peaked at 1.22 GiB aggregate), so this is not a practical risk. *Fix:* compute `aggregate = _tree_rss(psutil.Process(os.getpid()))` (includes the children), and after reading `train.json` mark the cell failed if `peak_rss_bytes > settings.rss_worker` (the worker's own `ru_maxrss` catches spikes the poll misses).
5. `p8_train.py:687-688, 927` — `--continue-after-failure` is accepted for a registered (non-dry) stage. ADR §11 says to stop on a failed cell or gate. *Fix:* refuse the flag without `--dry-run`, or record the lead's decision before the freeze (**PENDING LEAD REVIEW**).
6. `p8_objective.py:310-312` — `lambda_zero_reason` says "g_r below floor" when the cause is a non-finite `g_l_theta`. This affects the record only, not the trajectory. *Fix:* test `math.isfinite(g_l_theta)` first.
7. `p8_objective.py:283-285` — a mismatch between the proxy's top-8 and the lookup's selection raises and fails the cell. This is the correct strictness, but the run cannot be redone. Bitwise equality held in every check below, including a 512-update synthetic C10 cell, so this is noted only. No fix is required.

## What was checked, and how

### 1. Candidate scores, selection, indexing (independent float64 reference, real dimensions)
For flat, fixed tree and learned tree at seeds 601 and 602 (synthetic full-size parent, 8×64 random tokens):
- The implementation's top-8 from `candidate_scores` equals `Memory.lookup(...).selected` and the full forward's `selected`. Its top-8 score values equal the lookup's weights **bitwise** (float32).
- My float64 reference (own normalisation, explicit `(r, t)` → `r·T+t` stacking, own stable branch sort, `routes − logsumexp` prior) gives the same top-8 sets. The maximum absolute score difference from the float32 implementation is 1.35e-6, which is float32 rounding.
- Group = slot // 8: `r_co` reshapes the dense `[Q, 4096]` tensor to `[Q, 512, 8]` and agrees with my reference to 0 in float64. Tree non-candidates and slots outside the top 64 have π = 0 (scatter into zeros). R_temp cross-row and future leakage, by gradient structure: changing row 1 leaves the gradient on row 0 unchanged (max diff 0.0), and changing row 0, position 15 leaves the gradient on row 0, positions 0–6 unchanged (0.0).

### 2. Values and gradients: implementation vs. reference vs. finite differences
Reference: `docs/reviews/p8-preflight-2026-11-14/independent_objective_p8.py`. Its `ref_*` functions import nothing from `arborlm.p8_*`. π uses `sigmoid(z)` and 1−π uses `sigmoid(−z)`, so it is independent of the implementation's `−softplus`. Products use `prod`, not `exp(Σ log)`. R_temp uses an explicit loop over (row, t). Raw output: `outputs/independent_objective_p8_run1.json`.

| Quantity (8 rows × 64 positions, real dims) | float64 max abs diff | float32 max abs diff |
|---|---:|---:|
| R_conc / R_co / R_temp value, impl − ref (flat, fixed, learned) | ≤ 2.2e-16 | ≤ 6.0e-8 |
| ∂R/∂keys, impl − ref (max \|grad\| ≈ 0.013–0.042) | ≤ 5.4e-17 | ≤ 2.6e-8 |
| ∂R/∂wq, impl − ref (max \|grad\| ≈ 0.014–0.071) | ≤ 1.5e-16 | ≤ 8.2e-8 |
| ∂R/∂router (learned), impl − ref (max \|grad\| ≈ 0.058–0.123) | ≤ 1.5e-16 | ≤ 6.9e-8 |
| Central FD (h = 1e-6, on **reference** R) − impl autograd, 10 coords per param (top-6 \|grad\| + 4 random), flat and learned, all three R (2 rows × 16 positions) | ≤ 5.6e-10 | — |
| ∂R/∂{values, wo, gate} through the real model | no graph path (`None`), every R and architecture | same |

Every key, wq and (learned) router gradient was nonzero. For the fixed tree, the router is a buffer and is not in Θ_r.

### 3. Training step (ADR §4), 3 consecutive updates, all ten cases, float64 and float32
I captured the implementation's gradient at the clipping call (spy on `clip_grad_norm_`) and compared it with my reference. The reference does: g_L over all trainable addition parameters; g_R from my own R; λ = 0.5·‖g_L|Θ_r‖/‖g_R‖ with the norm taken over keys, wq and the router only when it is a parameter; sum, then my own clip; then my own AdamW (lr 3e-3, β (0.9, 0.999), ε 1e-8, wd 0).

| | float64 | float32 |
|---|---:|---:|
| C01–C03 combined grad diff / param diff after step | 0 / 1.4e-17 | 0 / 7.5e-9 |
| C04–C10 combined grad diff (max over cases) | ≤ 3.9e-19 | ≤ 2.2e-10 |
| λ relative diff (incl. both λ's of C10) | ≤ 1.6e-15 | ≤ 2.5e-6 |
| param diff after the AdamW step (my AdamW vs torch's) | ≤ 1.4e-14 | ≤ 7.4e-6 |

The largest float32 parameter difference (C06) comes from Adam's first-step g/(|g|+ε) normalisation on coordinates whose gradient is about 1e-8. It is not a difference in the rule.

Code reading confirms the following. The standard path is P5's `train_step` operation for operation (`p8_objective.py:221-255, 326-338` vs `p5_model.py:146-183`). The logging additions are pure reads. `diagnostics` runs under `no_grad`, the model has no dropout, and nothing in the step draws from the global RNG. The first `loss.backward()` is the only accumulation into `.grad`. Each g_R comes from `torch.autograd.grad`, not from accumulation. A single proxy graph is reused across C10's two R's with `retain_graph=True` until the last one. λ is a Python float. The λ = 0 path skips the addition. Clipping runs over all addition parameters (1.0). P5's optimizer checks run every step through `optimizer_names`. The pytest bitwise tests of standard vs. P5, λ=0 vs. standard, logging on vs. off, and repeat determinism are genuine comparisons of two independently trained models, not tautologies. The one partial exception is `test_matched_pressure…`: it checks λ·‖g_R‖ = α·‖g_L|Θ‖ using the record's own norms. My check above covers the norms themselves.

### 4. Registry and matrix
There are exactly 60 cells. Index = 20·parent + 10·seed + case. Labels, case→variant/objective/baseline/flat-counterpart, parents (101,301),(102,302),(103,303) and seeds 601/602 match ADR §5 (`p8_core.py:50-95, 262-306`; the config is validated against `_REGISTERED`). Seeding is `random.seed(seed)` then `torch.default_generator.manual_seed(seed)`, then `Model(cell, backbone)`. That is the same order as `hierarchy_ablation._cell:246-248`, after `configure_cpu`. `Memory(variant, seed)` uses its own generators (seed+1000…+5000), so initialisation is P5's construction at seeds 601/602. Cases sharing a variant and seed start identically.

### 5. Data
`load_training` opens only `frozen-data/dataset_manifest.json` and `train.bytes`. It checks the manifest hash against the P5 quality manifest, P1_TRAIN_SHA256, and the length. The order file is checked against the parent's provenance `order_sha256`, against `generator_seed == order`, and as a permutation of 0..2047. Rows 2048+ (calibration) cannot be indexed. Batches use `batch_offset = ((step−1)·8) mod 2048`, the same as `p5_config.batch_offset`. No validation file is touched on the training path. The p5-invariance result proves end to end that P8's data path reproduces P5's training bitwise (see 7).

### 6. Frozen backbone
The backbone is loaded through `p5_parent.verify_parent`/`extract_verified`, with provenance and the backbone digest checked against P5 `baselines.json`. `requires_grad` is False (P5's Model and `optimizer_names` refuse otherwise). The digest is checked at steps 0, 256 and 512 and before/after the cell, the fixed router buffer at each checkpoint, and optimizer membership every step.

### 7. Checkpoints, restore, freeze gate, supervision
- **Checkpoints and restore.** Steps 0, 256 and 512 are saved atomically, never overwritten, with optimizer state, RNG state and identity. Restore rebuilds the model from its *initial* state, loads, and verifies the state digest. A failed load would therefore change the 512 digest, so the check is not vacuous. Synthetic dry run: restore from 256 then retrain reached the recorded step-512 digest for C10 (`a00a9999f191…`) and C02 (`f38d6b89bc9d…`). The digests at 256 were different (`838635e2…`, `2157cdc8…`). Log: `outputs/training_dry_restore_checks.log`.
- **Freeze gate.** `verify_freeze("HEAD")` refused (p8 files are untracked at HEAD, so `src/arborlm` differs and the config is missing). A nonexistent commit was refused with `FreezeError`. I could not construct a vacuous pass. `source_hashes` and `repo_root` derive from the same `__file__`, and `arborlm` imports from this worktree's `src/` (editable). Any `.py` file added, removed or changed under `src/arborlm` fails. Workers report `source_sha256` and the supervisor compares it with the header. Gaps are MINOR-2/3.
- **Supervision.** A failed or killed cell is recorded as `failed` with its reason. The remaining cells are recorded as `unexecuted`, and the denominator stays at the label count. A cell folder can never be retrained in place (`mkdir(exist_ok=False)`). Caps are 600 s per cell (wall time from launch, conservative), 5,400 s for the stage, 2 GiB per worker tree and 8 GiB aggregate. Each is unit-tested with a fake worker. See MINOR-4/5.
- **Dry-run timing.** Three synthetic full-size cells with 3 workers took 49.6 s of stage wall time. C01 trained in 3.9 s, C02 in 14.7 s and C10 in 46.4 s, with worker peak RSS of 319, 448 and 474 MiB and a peak aggregate of 1.22 GiB. Even if all 60 cells took as long as C10 (about 49 s wall), 4 workers would need about 735 s, which is ≤ 14% of the 5,400 s cap. The worst cell used about 8% of the 600 s cell cap. This is my synthetic measurement, not the registered rehearsal (§10.8 remains the implementer's gate).

### 8. Tests and §10 gates
`uv run --locked --extra pilot pytest tests/test_p8_core.py tests/test_p8_objective.py tests/test_p8_train.py -q` → **71 passed, 1 skipped** in 13.6 s. The skip is `test_real_training_rows_identity_local_only`, which needs local data; the data identity was instead exercised by p5-invariance. My judgement of each gate:
- **Gate 1:** genuine. `gradcheck` covers each R on flat and tree-like instances, the zero gradient on values/wo/gate through the real model, and the nonzero gradient on keys, wq and router. My FD check above adds the real dimensions and parameter-space derivatives.
- **Gate 2:** genuine. Covers 8 > ½ at three scales, the tie giving 7 and two at exactly ½, zero outside the top 64, the closed form at p ∈ {0.51, 0.9, 0.999}, about 1 for eight groups, the R_temp extremes and window, and the R_conc ordering and 0.25 floor.
- **Gate 3:** genuine. The standard path is bitwise P5 in unit tests, and λ = 0 (α = 0 and floor) is bitwise standard. **P5 invariance on real training rows:** the implementer's run `experiments/P8TI-20261114T034510617868Z-79bf…/result.json` reports `passed: true`, with P8 step-512 state digest = P5 checkpoint-512 restored digest = `4e9bf5c1…6515` and all state tensors bitwise equal. I independently confirmed that the local `checkpoint-512/state.pt` SHA-256 equals both its `index.json` and the committed `results/p5-2026-11-13/b101-o301-flat-s501/result.json` value `e3cb9050…5b44`. My own rerun of the gate failed twice for environment reasons of my own (attempts kept in `failed_attempts/`). The first failed because the symlinked scratch experiments root lacked the P3 suite. The second failed because P5's parent provenance records an absolute `checkpoint_path`, which a symlinked root cannot reproduce: "P8 actual parent does not match P5 suite preflight". This is correct strictness and not an implementation defect. I did not rerun it against the real experiments root, because that would write there.
- **Gate 5:** genuine (synthetic). The tests restore at the midpoint, check that the optimizer state is non-empty, and assert the final digest, for C07, C01 and C02 plus the CLI path for C07 and C10. My dry run confirms this at 512 updates. The run-time part is MAJOR-2.
- **Gate 9:** genuine. Repeated cells give identical digests, and P5's `configure_cpu` is used (1 thread, deterministic algorithms).

## Commands run (cwd = worktree; S = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/audit1`)
```sh
uv run --locked --extra pilot pytest tests/test_p8_core.py tests/test_p8_objective.py tests/test_p8_train.py -q   # 71 passed, 1 skipped
uv run --locked --extra pilot python docs/reviews/p8-preflight-2026-11-14/independent_objective_p8.py > $S/indep_run1.json   # 26.7 s
uv run --locked ruff check docs/reviews/p8-preflight-2026-11-14/independent_objective_p8.py   # clean
# FAILED x2 (kept): p5-invariance against a symlinked scratch root
uv run --locked --extra pilot python -m arborlm.p8_train p5-invariance --experiments-root $S/exp --data-dir /Users/daniellaloush/dandush03/ArborLM/data
uv run --locked --extra pilot python -m arborlm.p8_train stage --dry-run --experiments-root $S/dry --data-dir /Users/daniellaloush/dandush03/ArborLM/data --labels b101-o301-s601-C01,b101-o301-s601-C10,b101-o301-s601-C02 --workers 3
uv run --locked --extra pilot python -m arborlm.p8_train restore-check --experiments-root $S/dry --data-dir /Users/daniellaloush/dandush03/ArborLM/data --run-dir $S/dry/P8TD-20261114T035423154406Z-fe26ee0c7a8a4164b445fb9d53620d76 --label b101-o301-s601-C10   # and ...-C02
uv run --locked --extra pilot python -c "from arborlm import p8_train as t; t.verify_freeze('HEAD')"   # refused
python3 (stdlib hashlib) on experiments/P5HIER-…/quality/P5QUALITY-…/cells/P5HIER-20261113T125208328534Z-41c1…/checkpoint-512/state.pt vs index.json vs results/p5-2026-11-13/b101-o301-flat-s501/result.json
```
Archived outputs: `outputs/independent_objective_p8_run1.json`, `outputs/training_tests_pytest.log`, `outputs/training_dry_stage3.log`, `outputs/training_dry_stage3_manifest.json`, `outputs/training_dry_restore_checks.log`; failed attempts in `failed_attempts/p5_invariance_attempt{1,2}_FAILED_*.log`.
