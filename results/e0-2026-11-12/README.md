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
