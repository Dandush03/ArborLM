# Independent P4 artifact audit

The read-only audit passed for suite `P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd` (63/63 registered cells). This is an engineering/artifact audit, not scientific validation.

## Verified

- All 63 archived source bundles have SHA-256 `18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0`; each bundle has the same 82-file map and an empty `source.diff`.
- All 55 accepted-source-file hashes and the separate 55-file P3 preservation map match. Shared source/spec/config/lock/data/approval/parent-spec identities match across cells.
- Every cell's P3 checkpoint state and index hashes match the registered parent mapping; all 9 parent backbones remain byte-identical. The 171 P4 checkpoint states and indexes agree with the result records and compact indexes.
- Checkpoint counters, baseline bypass, frozen backbone tensor bytes, canonical backbone/mask digest, fresh same-seed additions, and parent order copies match the records. The causal mask is a nonpersistent runtime buffer; this audit verified its canonical digest from reconstructed checkpoint/model context rather than claiming it is serialized in the checkpoint state dict.
- For all trained-cell snapshots, requires-grad names match the exact registered addition parameters (memory: six; dense: three), with 27,392 frozen backbone parameters and 198,401 trainable addition parameters. The serialized AdamW contains exactly one ordered, duplicate-free parameter group with expected hyperparameters. Step-zero optimizer states are empty; the 256/512 states contain exactly the expected parameter IDs, AdamW clocks, and correctly shaped first/second moments. Baselines have no optimizer.
- Event accounting: 27,648 training updates, 54 initial evaluations, 63 final evaluations, 171 intervention evaluations, and 9 parent-restore integrity checks. The audit itself performed zero model forwards and zero training updates.
- The fresh validation panel hash is `4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f` (512 rows).

The saved machine-readable output is `independent-artifact-audit.json`; `issues` is empty. Actual HEAD and dirty-state counts are preserved in that JSON and are distinct from the frozen archive identity.

## Reproduction

Run from the repository root with the registered local dependencies and P4 experiment artifacts available:

```sh
uv run --locked --extra pilot python results/p4-2026-11-12/independent-artifact-audit.py
```

Exit status was 0, and rerun stdout was byte-identical to `independent-artifact-audit.json`. The captured stderr warning only reports that optional NumPy is unavailable in the local PyTorch runtime; it did not affect the audit. Ruff check on the published checker passed.

## Portability-only contract-test repair

The preserved code-freeze Linux CI log (`results/p4-preflight-2026-11-12/code-freeze-ci-43366259292.log`) recorded a single test-reference mismatch: a whole-nine-row float32 `cross_entropy` reduction differed from the evaluator's 8+1 batch reductions by about `3.71e-7`. The evaluator was not changed. The synthetic test now uses an independent float64 tokenwise `logsumexp`/target-logit oracle and a `2e-6` tolerance for float32 reduction roundoff. A controlled known-logit nine-row test has one final four-token batch and verifies token weighting differs materially from an incorrect unweighted mean of batch means.

Focused test result after this test-only repair: `19 passed`; Ruff check passed. Full CI was not rerun by this auditor; root is running full validation. No P4 model results or scientific thresholds were changed.
