# E0 local verification checkpoint — 2026-11-12

Status: G0 accepted by the human-authorized root Codex reviewer after code inspection and independent rerun. Sol implemented; Luna supplied independent contract tests. Astra review NOT PERFORMED. Human merge/publication approval remains pending.

- Ruff passed; mypy passed for 11 source files; pytest: 31 passed.
- Full smoke: 11/11 gates passed, including fresh-repeat, reload and interrupted-resume bitwise comparisons in this one macOS arm64 environment.
- Root smoke runtime: 5.604292 seconds; sampled process-tree RSS peak: 297369600 bytes.
- Initial/final synthetic validation NLL: 2.7826549112796783 / 2.7135501205921173 nats/target; 2,048 validation targets each. These are engineering observations, not evidence for hierarchical memory or general language ability.
- Warning: optional NumPy initialization unavailable to PyTorch; no NumPy-dependent path is used.
- Linux CI configured; not yet verified at this checkpoint.

Exact commands and outputs are in the two verification logs. Raw per-step events, resolved configs, manifests, environment/data/source/checkpoint hashes are preserved here. Full source archives and binary checkpoints remain under `experiments/E0-20261113T021751395579Z-022ace6673384498a39ce74f2ddea257` and its children; source commit and dirty-file hashes in each source record identify the code actually executed. Recorded paths refer to the original local checkout.

The intentional step-16 interruption is preserved with interrupted status. Earlier local smoke artifacts also remain intact. No failed experiment was replaced by a successful retry. Tests of failure/corruption use synthetic unit fixtures and are not scientific experiments.

This checkpoint establishes E0 only. Flat memory, hierarchy, real-data quality, novelty, scaling and storage claims remain unvalidated. ADR-0005 preregisters the next bounded screen before its execution.

## Subsequent Linux CI verification

[GitHub Actions run 43351992585](https://github.com/Dandush03/ArborLM/actions/runs/43351992585) completed successfully at code commit `677ef8e`. Linux Ruff/mypy, all 31 tests and all 11 smoke gates passed. Status, full job log and smoke summary are preserved in `linux-ci-43351992585/`; the complete CI artifact was also downloaded locally before expiration.

Linux initial NLL was 2.782654881477356, while macOS initial NLL was 2.7826549112796783. This small observed difference confirms why the contract is same-environment repeatability, not cross-platform bitwise identity. Final NLL happened to match; no cross-platform guarantee follows.
