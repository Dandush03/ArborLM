# ADR-0017 (P9) — interface contract for implementation

Written by the lead after human decision 1. The specification is `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` (revision 3). Where this file and the ADR disagree, the ADR governs and the disagreement is reported to the lead, not resolved by the implementer.

## Where the code lives (a change from the execution plan's file names)

**Not under `src/arborlm/`.** The frozen P8 source digest covers every `*.py` there, and an existing test and the ADR-0016 supplement verify that digest. New code goes in a new top-level package **`studies/p9/`** (`studies/__init__.py`, `studies/p9/__init__.py`), run from the repository root as `uv run --locked python -m studies.p9.<module>`. Tests are `tests/test_p9_*.py`; each inserts the repository root into `sys.path` before importing `studies.p9` (same pattern as `tests/test_p8s_*.py`). Type checking: `uv run --locked mypy src/arborlm supplements/p8s studies/p9`. `pyproject.toml`, `uv.lock`, `tests/conftest.py`, CI and every existing file stay unchanged. No monkeypatching of `arborlm` modules; import and call, or copy with an equivalence test.

Config: `configs/p9_diagnostics.toml` (new). Run directories: `experiments/P9<stage>-<utc>-<id>/` in the main checkout's git-ignored `experiments/`. Committed records: `results/p9-<date>/`.

## Modules and owners

| Module | Package | Contents |
|---|---|---|
| `core.py` | I0 | constants of the ADR, the 100-cell registry with blocks and dependencies, update and snapshot schedule as a function of E, seeds, thresholds, config load and validation, identity hashes (P9 source digest over `studies/p9/*.py`, spec hash, config hash, frozen-input check of `src/arborlm` against git blobs), record IO through `arborlm.io` |
| `data.py` | I1 | alphabet, checksum identifiers, facts, clusters, templates, streams and panels (training, calibration, A, B, H1, H2, mixed-cluster, unseen control), Lane D sets, hashing, gate G1 checks, rehearsal seed namespace |
| `controls.py` | I1 | exact retrieval, no-memory evaluation, frozen-hidden probes (nearest stored state, per-position linear probe), attainable answer probability from frozen weights, G2 intervals |
| `model.py` | I2 | scalable memory (sizes, key widths, constant-candidate tree, rungs R0, R0a, R1, R2, oracle branch), matched dense adapter, model wrapper around the frozen backbone, exact P5 forward invariance at 4,096/16 |
| `objective.py` | I2 | soft inclusion, global usage floor with the b-free gradient, co-access term, absolute coefficients |
| `train.py` | I2 | answer-site loss, AdamW and row-lazy Adam, training loop, snapshots with optimizer state, instrumentation of §6.3, modes `registered`, `calibration`, `rehearsal` (rehearsal writes only through the whitelist validator) |
| `evaluate.py` | I3 | cached selections and weights, accuracy, I_acc with the chance floor, log-loss gain, seven-position knock-outs, minimal supports, U\*, specificity, group ablation, value permutation and disabling, usage statistics, LEAKAGE check, trace export |
| `layout.py`, `sim.py` | I4 | general-N layouts (identity, frequency, sparse co-access, random partition, branch-constrained, oracle cluster), general-N page simulator with exact equivalence to P7-B at 4,096, count-preserving nulls with ADR-0016's identity null, cache rule, planted-trace generator, key-traffic identity |
| `incremental.py`, `store.py` | I5 | Lane D phases and arms, replay, fresh optimizer at V1, copy-on-write version store and its consistency test |
| `pool.py` | I6 | job manager: immutable task ids, stage manifests, worker semaphores, RSS and time limits, failed records kept, dependent-cell stop rule in every stage |
| `analysis_a.py` … `analysis_d.py`, `report.py` | I6 | class rules of §8 per lane, decision map, CSV/JSON/Markdown, dashboard |

## Shared types (defined in `core.py`, used unchanged by everyone)

- `Cell` — frozen dataclass: `block`, `arch` ∈ {flat, fixed_tree, learned_tree, dense}, `slots`, `key_width`, `rung` ∈ {R0, R0a, R1, R2, OB}, `track` ∈ {proportional, fixed}, `facts`, `optimizer` ∈ {adamw, lazy}, `alpha_u`, `alpha_c`, `parent` (backbone, optimizer-parent pair as in P5–P8), `seed`, `lane_d_arm` (or None), `index`, `label`, `depends_on` (labels).
- `cells()` returns exactly 100 cells; per-block counts are asserted against ADR §10.
- `updates(cell, exposure)` and `snapshots(cell, exposure)` implement ADR §5.5.
- Position convention, fixed for all modules: a context is 64 bytes; model input is bytes 0..62, targets bytes 1..63; record r occupies bytes 8r..8r+7 (separator, 5 identifier bytes, binding byte, answer byte); the answer site of record r is input position 8r+6 and its target is byte 8r+7.

## Interfaces between packages

I0 delivers, besides `core.py` and the config, **typed stub modules** for every file above: public function and class signatures with docstrings, bodies raising `NotImplementedError`. The lead reviews the stubs; they are then the contract. An implementer may add private helpers freely, and may change a public signature only by reporting it to the lead.

## Rules for every implementer

- Edit only the files of your package. No existing file changes.
- Run only your own tests while other packages are in progress (`uv run --locked pytest tests/test_p9_<yours>*.py`), plus `ruff check` on your files; the lead runs the full suite.
- Do not run any calibration, rehearsal or registered stage, and do not train any model on registered seeds. Unit tests use tiny synthetic sizes and test seeds.
- Never write loss or accuracy of a compared arm from a rehearsal path.
- Keep failed attempts; report anything in the ADR that is infeasible or ambiguous instead of improvising.
- No commits.
