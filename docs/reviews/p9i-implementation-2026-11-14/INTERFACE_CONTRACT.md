# ADR-0017 Part I (P9-I) — implementation contract

Written by the lead (Fable 5.2) after the human decision recorded in ADR-0017 §15.3. The specification is `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` **§18 (Part I, sections I.1–I.16)** and §15.3. Where this file and the ADR disagree, the ADR governs and the disagreement is reported to the lead, not resolved by the implementer.

## Where the code lives

- New package **`studies/p9i/`**, run from the repository root as `uv run --locked python -m studies.p9i.<module>`.
- Tests `tests/test_p9i_*.py`, with the same `sys.path` pattern as `tests/test_p9_*.py`.
- Config `configs/p9i_interface.toml` (new).
- Type check: `uv run --locked mypy src/arborlm supplements/p8s studies/p9 studies/p9i`.
- **No existing file changes**: nothing under `src/arborlm/`, `studies/p9/`, `supplements/`, `configs/`, `tests/`, `results/`, `docs/decisions/`, and not `pyproject.toml`, `uv.lock`, CI. Import `studies.p9` and `arborlm` and call them; where a P9 function cannot do what Part I needs, write the Part I version in `studies/p9i/` (copy with an equivalence test where equivalence is claimed). No monkeypatching.
- Run directories `experiments/P9I<stage>-<utc>-<id>/` in the main checkout's git-ignored `experiments/` (as P9 does). Records carry the study code `P9I`.

## Modules

| Module | Contents |
|---|---|
| `core.py` | constants of Part I; the 57-cell registry with per-row counts asserted against §I.7 (core 22 + 10 + 8 = 40; block BB 13 + 4 = 17); seeds (init 1801/1802, registered data seeds 182001 upward, calibration init 1791/1792, rehearsal draws k ≤ 9, calibration on draw 1); candidate U values and snapshot schedule; thresholds of §I.6 and §I.8; `select_updates` (the §I.6 rule, returning U and failed sizes); config load and validation; identity hashes (source digest over `studies/p9i/*.py` and the imported `studies/p9/*.py`, spec hash of the ADR, config hash); charged-time ledger for the 4-hour cap |
| `model.py` | arms N, W7, E7, A4, A4E, R1, R2 on the flat memory of ADR-0017 §5 read **at answer sites only**; D plain and D7 (answer sites only; D7 hidden width from the parameter-match rule, expected 786 / 3,090 / 12,306); block BB (BB, BB-D, BB-0) with the block-0 attention's qkv and output projection as the only trainable backbone parameters (exactly 4,224); parameter counts per arm |
| `train.py` | alphabet-only cross-entropy at answer sites (32 symbols 0x40–0x5F); matched updates U for every cell; optimizer groups (AdamW lr 0.003 for projections, gate, interface parameters, dense adapters and BB attention; row-lazy Adam lr 0.012 for key and value tables, as P9); snapshots with optimizer state; training diagnostics of ADR-0017 §6.3; modes `registered`, `calibration`, `rehearsal` (rehearsal writes only through a whitelist validator: time, memory, shapes, counts, identity — never loss or accuracy) |
| `evaluate.py` | accuracy on Panels A and B (primary), H1/H2 and mixed-cluster (secondary); η; I_acc, Σ-renormalized log-loss gain and 256-way loss (descriptive); query diagnostics of §I.5; value permutation and disabling; minimal supports restricted to the answer-site read; no-memory baseline, exact retrieval, unseen-fact control with LEAKAGE; G2; for BB arms the backbone's next-byte loss on its own corpus rows before and after |
| `classes.py` | pure functions from records to: raw class, class at a size (§I.8.1 both steps, B102 rule, MODEL_STORES_FACTS), annotations (§I.8.2: dense comparison, backbone contrast, language modelling), selection outcome (§I.8.3 steps 0–4) |
| `stages.py` | `generate`, `calibrate`, `rehearse`, `gates`, `train`, `evaluate`, `analyze`, `report`, and `dry` (tiny synthetic end-to-end), using `studies.p9.pool` for jobs with the per-worker 3 GiB and aggregate 24 GiB limits; failed records kept; no re-run with changed settings |
| `report.py` | CSV/JSON/Markdown of classes, annotations, selection, exposures per fact per size, parameters and optimizer-state bytes per arm |

## Rulings the ADR leaves to the lead

- h is the frozen block-0 output (what P9 exposes as the insertion-point hidden state). The memory read is added there at the answer site, and the frozen upper block finishes, as in P9.
- Position convention as P9: the answer site of record r is input position 8r+6. W7/E7/D7 window = positions t−6…t. A4/A4E/BB attention = causal, scores scaled by 1/√8, 4 heads × 8, no layer norm; A4/A4E have no output projection and are bias-free (3,072 parameters).
- Batch composition, key normalization, top-8, temperature 0.2, key width 16, gate and output projection: exactly as P9's flat memory. R1 and R2 exactly as P9's rungs.
- G4: with equal parameters and inputs, arm N's logits at answer sites equal P9's R0a model's logits at answer sites bit for bit **when R0a's read is restricted to the answer sites**; if P9's R0a cannot be restricted without editing it, test equality of the selection and of the read vector at the answer sites and report this to the lead. At initialization BB = N, BB-D = D plain, BB-0 = no-memory baseline (bit for bit).
- Calibration stage runs only controls, R1 and R2 (three sizes; init seeds 1791 and 1792 on B101/O301, 1791 on B102/O302; snapshots at 1,024 / 2,048 / 4,096 / 8,192 / 16,384 updates) on rehearsal draw 1, and refuses any other arm in code.
- Every stage records charged wall time in the ledger; a stage refuses to start when the remainder of the 4-hour cap is smaller than its own stage cap.
- Efficiency: single-thread workers, six at a time; answer-site-only key scoring; no per-update Python loops over facts.

## Rules for the implementer

- Do **not** run the calibration, rehearsal or any registered stage. Do not generate or read rehearsal draw 1 or any registered-seed data. Do not train on real backbones beyond what a unit test needs at tiny size; unit tests use `studies.p9.controls.synthetic_backbone`, tiny sizes and test seeds (use 900001 upward).
- Tests required: gradient reach for every arm (each trainable group gets a gradient, nothing else does; BB trains exactly 4,224 backbone parameters); N against R0a; initial-forward identities of block BB; D7 parameter match within 0.1% at the three sizes; registry counts; seed disjointness (registered, rehearsal, calibration, test); `select_updates` on synthetic tables including a failed size; every raw class, every class at a size, every annotation value and every selection outcome (steps 0–4) triggered on synthetic records; rehearsal whitelist rejects loss and accuracy; determinism and checkpoint restoration at tiny size; `dry` runs end to end.
- `uv run --locked ruff check .`, the mypy command above and `uv run --locked pytest` (full suite) pass at the end.
- Keep failed attempts in your report. Anything infeasible or ambiguous in the ADR: stop that item and report it; do not improvise a scientific choice.
- No commits.
