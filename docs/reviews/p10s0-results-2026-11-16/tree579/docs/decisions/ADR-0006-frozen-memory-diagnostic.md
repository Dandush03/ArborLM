# ADR-0006 — Frozen-checkpoint memory contribution diagnostic

- Date: 2026-11-12
- Status: **APPROVED BY HUMAN-AUTHORIZED CODEX REVIEWER; NOT ASTRA REVIEWED**.
- Context: the completed ADR-0005 screen missed its promotion gate (mean learned-tree gain 0.0092854773 nats/byte versus required 0.01). Do not change that outcome, retune or scale. This is a new exploratory diagnostic designed after observing the screen, with its own rules frozen before diagnostic results.
- Question: do the existing learned-tree checkpoints depend on their memory module and learned key/value association? This does not test general reasoning, factual knowledge, novelty or a superior efficiency frontier.

## Fixed inputs and conditions

Use exactly the three final learned-tree checkpoints and frozen validation chunks in `experiments/P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8`. Verify original checkpoint, data/config/spec hashes before loading; retain provenance to their run IDs. Do not train, tune, update the index, access test data or acquire any data. Original checkpoints and suite are read-only.

For each seed 42/43/44, run four fresh CPU subprocesses in this order, each loading/restoring the original checkpoint before applying its condition:

1. `original`: unchanged checkpoint. Validation NLL must match that seed's original pilot result bitwise in the same environment.
2. `disabled`: bypass only the additive memory module; leave the trained backbone unchanged. This is a counterfactual, not a separately trained no-memory baseline.
3. `values_permuted`: permute all 4096 value rows using `torch.randperm(4096, generator=CPU_Generator.manual_seed(9001+seed))`; leave keys, router and other weights unchanged. This preserves the multiset of values but breaks slot binding. It can expose coadaptation; it does not by itself demonstrate semantic knowledge.
4. `joint_within_branch`: for branches 0..15 in order, draw `randperm(256)` from one CPU generator seeded 10001+seed; permute keys and values together within each branch. Router remains unchanged. This preserves each candidate branch's key/value pairs; validation NLL must match original within absolute 1e-6, relative 0. Save permutation IDs/hash for both permutation conditions.

Use the same float32, CPU/thread/determinism settings, tokenizer, 512 validation rows, batch8, 64 target positions and NLL aggregation as ADR-0005: 32,768 targets per evaluation. Checkpoint identities refer to ADR-0005; diagnostic run manifests refer to ADR-0006 as well as the parent spec. Check that original forward/data/loss/checkpoint source files still match the original run's recorded hashes before running; allow only new diagnostic orchestration and documentation.

Twelve evaluations total, 60-second cap per subprocess, 300-second cap for entire diagnostic suite, 2 GiB sampled process-tree RSS. Use the existing watchdog and immutable run-directory pattern. Preserve command/source/environment/parent hashes, actual metrics and failures. Never overwrite trained weights or finalize diagnostic data into an original run. Stop on resource/correctness failure and mark remaining cells unexecuted.

## Required tests and interpretation

Unit tests must verify that disabling leaves backbone tensors untouched, value permutation changes only values and preserves their multiset, joint permutation preserves branch membership and paired keys/values, repeated permutation seeds are deterministic, and original checkpoint bytes remain unchanged. Review CLI and run records before real evaluations; no new architecture or training setting may be chosen by the implementer.

Report all per-seed NLLs and `condition NLL - original NLL` deltas. Original replay or joint-permutation invariance failure is a diagnostic correctness failure, not scientific evidence against memory. If both disabled and values-permuted mean deltas are at least **0.005 nats/byte**, record dependence on the trained memory module and slot bindings at this diagnostic sensitivity. Otherwise record which dependence is not established by this check. Report every per-seed direction; do not use the mean to hide an opposite sign.

These are exploratory sensitivity thresholds, not significance tests. The earlier promotion gate remains failed under every possible diagnostic outcome. Any future training change requires a new specification; scaling and publication remain unapproved.
