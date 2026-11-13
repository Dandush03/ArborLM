# P4 engineering preflight

Root accepted the implementation against
[ADR-0009](../../docs/decisions/ADR-0009-frozen-backbone-capacity.md)
under the human-authorized reviewer exception. Execution remains conditional on
the code freeze and explicit authorization. **No real-data P4 model forward,
evaluation, or training update occurred.** The E0 smoke and unit tests use
synthetic data and are not P4 scientific outcomes. Astra review was not
performed; human merge and publication approval remain pending.

Root independently read the seven P4 modules, strict config, and both test files.
[Root verification](root-verification.log) and
[implementer verification](implementer-verification.log) passed Ruff, mypy
(38 files), all 116 tests, and all 11 E0 smoke gates. The only test warning was
PyTorch's optional NumPy integration; NumPy is not needed for these checks. The
root E0 smoke record is `E0-20261113T043021992435Z-b82abb95271c43f79f5fa9871bec417b`.

The data audit reconstructed the registered 512-chunk panel at eligible
validation ranks 1536–2047. It verified the earlier panel hashes, training-byte
identity, and exact-chunk disjointness. The new validation-byte SHA-256 is
`4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f`.
The data audit exits 0; its stdout matches the preserved
[root audit JSON](root-data-parent-audit.json),
[independent audit JSON](independent-data-parent-audit.json), and
[root audit log](root-data-parent-audit.log) byte for byte. Luna's separate
[data and parent audit](luna-data-parent-audit.json) is also retained.

Root independently verified and strictly restored all nine registered P3
step-1024 parents. Each restored backbone contained exactly 27,392 frozen
parameters and matched its source tensor bytes. The baseline, memory, and dense
variants shared the same frozen-backbone digest, which includes the causal mask.
The two trained variants each had exactly 198,401 addition parameters, with fresh
AdamW state and exact addition-only optimizer membership. The parents remained
unchanged, and the restore audit performed no forwards or optimizer updates.
See the [restore evidence](root-restore-audit.json) and
[passing log](root-restore-audit.log).

The [initial restore-audit log](root-restore-audit-initial-error.log) preserves
a tooling error: a dtype view on a scalar tensor required flattening with
`reshape(-1)` first. The corrected byte comparison passed. This changed the
audit helper only, with no change to the model or experiment.

Run the checks from the repository root:

```sh
uv lock --check
uv run --locked --extra pilot ruff check .
uv run --locked --extra pilot mypy src/arborlm
uv run --locked --extra pilot pytest
uv run --locked --extra pilot python -m arborlm.frozen_capacity --help
uv run --locked --extra pilot python -m arborlm smoke --config configs/e0_cpu_smoke.toml --output-root experiments
git diff --check
```

The audit commands require the pinned local Parquet files and original P3
checkpoint binaries. Those files and source archives are retained locally;
this directory contains compact evidence only.

```sh
uv run --locked --extra pilot python results/p4-preflight-2026-11-12/independent-data-parent-audit.py
uv run --locked --extra pilot python results/p4-preflight-2026-11-12/independent-restore-audit.py
```
