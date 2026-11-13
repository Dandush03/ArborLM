# Root independent P5 engineering acceptance

Reviewer: root Codex under the documented human-authorized scientific-reviewer exception. **Astra review: NOT_PERFORMED.** Engineering preflight is accepted; real-data execution still requires the separately committed source/config/spec/data/lock freeze and explicit orchestration authorization.

The root reviewed the P5 implementation, configuration and both test files, the existing retrieval/backbone mathematics they reuse, Sol's implementation evidence, and Luna's separate engineering findings. The final independent locked checks passed: Ruff for the whole repository, mypy for 47 source files, and **161 tests**. An earlier independent run passed 158 tests; its logs remain preserved. The final run includes the invalid-ACK correction and both independently authored regression checks. The two warnings are the existing optional-NumPy warning and a deliberately duplicated optimizer parameter in a rejection fixture.

Exact final commands from the repository root:

```sh
uv run --locked --extra pilot ruff check .
uv run --locked --extra pilot mypy src/arborlm
uv run --locked --extra pilot pytest
```

The independent E0 smoke command was:

```sh
uv run --locked --extra pilot python -m arborlm smoke --config configs/e0_cpu_smoke.toml --output-root experiments
```

All 11 E0 gates passed. This E0 check preceded the last P5-only ACK correction, which does not enter the E0 execution path; the final complete regression ran afterward. Logs, E0 results and exact reviewed source fingerprints are retained here.

Acceptance covers frozen backbone parameters and nonpersistent causal mask, fixed-router buffer immutability, fresh seeded additions and shared initialization, strict single-group AdamW settings/membership, checkpoint restoration/resume/RNG and corruption rejection, intervention semantics, float64 token-loss oracle and unequal-batch weighting, causal/tied-output math and gradients through the frozen suffix, actual operand traces, timing scope/schedule/state isolation, decision arithmetic, reliability boundaries, exclusive result exports, and resource-clock/ACK failure paths. Existing unchanged pilot tests independently cover stable top-k, full-branch tree/flat equivalence and selected router/value gradients.

The root and Luna separately reconstructed the raw data and parent provenance. Root additionally strictly restored all nine actual P4/P3 parents through the P5 interfaces and checked every one of the first 2,560 validation selection identities against Luna's reconstruction. These checks performed **zero real-data model forwards**. The new panel and derived manifest identities are in the linked prior audit bundles.

Pre-outcome defects were corrected and retained in the engineering evidence: inconsistent parent labels, flat-router access, duplicate exclusive export, omitted stage-finalization time, permissive optimizer grouping/settings, platform-specific equivalent matmul trace dispatch, and invalid-ACK time exclusion. Rejected or interrupted ACK waits now receive no exclusion. These repairs changed no approved model dimensions, data ranks, initialization seeds, optimizer numerics, training budget, inference scopes, thresholds or resource ceilings.

A Git comparison against finalized P4 commit `71128eaf5d6028a59ed8ea48df6747f781a4495e` found no changes to 2,763 protected existing source/config/test/result/ADR/lock files. P1–P4 conclusions remain unchanged. Engineering acceptance is not evidence for the P5 scientific hypotheses. All scientific decisions await the preregistered runs and independent aggregate/artifact audits. Human merging, publication and additional scaling remain unapproved.

Root also checked hand-calculated scalar fixtures against the analysis: positive-effect means/all quality flags, separate gain/shuffle/initial-loss clauses, strict 22-cell/8-parent usefulness counts, all quality-penalty and dense-tolerance clauses, .80/1.05 latency boundaries and rejection above the addition-time margin. All passed. `analysis-clauses.py`/JSON/log preserve this additional check; it uses the independently authored synthetic scalar fixture definitions and performs no model calls. Command: `uv run --locked --extra pilot python experiments/review/p5-root-preflight/analysis-clauses.py`.
