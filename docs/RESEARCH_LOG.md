# ArborLM — Research Log

Chronological, append-only notes. Scientific decisions also go into reviewed ADRs. **There were no experimental results at project initialization; subsequent run records and their limitations are recorded below.**

## 2026-11-12 — Origin and project definition

- Starting observation: Colibrì streams large MoE experts from NVMe while achieving constrained throughput in disk-bound configurations.
- Explored faster CPU/NPU vs transfer bottlenecks; NVMe-to-RAM-to-CPU hierarchy; computational storage; lossless compression, quantization and shared parameter representations.
- Research pivot: rather than accelerating transfer of weights an unchanged model requires, train a **new architecture** that navigates learned parameter memory hierarchically and accesses very little per token.
- User emphasized input vector / related million-vector neighborhood / database or SQL indexing analogy. Interpretation: learned coarse-to-fine routing plus sparse retrieval, not literal database SQL on every token and not fetching 1M vectors.
- Chosen working name: ArborLM; layer concept HNM (Hierarchical Neural Memory).
- Decision: portable proof of concept first, not hosted in user's infrastructure; conditional future scale if evidence warrants it.
- Decision: publication-quality methodology and documentation from inception.
- User model-workflow rule: Astra for science/reasoning/orchestration/final validation; lower-tier model for implementation under Astra-approved specification.
- GitHub repository created: https://github.com/Dandush03/ArborLM . Apache-2.0 recommended; direct integration write previously failed, so verify `LICENSE` is committed.
- Open risks: trainability, novelty, fair baselines, physical read amplification, path to model migration, quality vs stored capacity.
- **No ArborLM experiment run yet; no scientific result claimed.**

## 2026-11-12 — Phase 0 implementation proposal recorded

- Read the repository policy, canonical handoff, experiment protocol, research log, ADR-0001 and kickoff prompt in full; inspected the README, paper outline and experiment-record template.
- At inspection, HEAD was `2555ed4`; the working tree was clean and contained no model implementation, tests or experiment artifacts. `LICENSE` is tracked and contains Apache-2.0 text; the root handoff copy matches the canonical document.
- Added `docs/decisions/ADR-0002-phase0-plan.md`, marked **SPEC: PENDING ASTRA REVIEW**, consolidating the inherited E0/G0 roadmap, reproducibility requirements, proposed correctness checks, review decisions and deferred memory/storage work.
- This is a planning/documentation change only. No scientific settings were approved, no model code was written, and no tests, training or benchmarks were run. No result or Astra validation is claimed.
- Next dependency: actual Astra review of the specification and recorded decisions before dependent model/data implementation; lower-tier implementation and independent validation remain pending.

## 2026-11-12 — Human authorizes alternate scientific reviewer

- The human lead explicitly selected **“Authorize this model as scientific reviewer”** in this project chat. This is a recorded session exception to the mandatory Astra reviewer preference; no Astra identity or review is inferred.
- Planning files were committed/pushed as `815f528` at the human's request.
- Added ADR-0003 as the concrete E0 specification, approved by the authorized root Codex reviewer. It resolves ADR-0002 A0–A8 for a bounded CPU correctness/reproducibility milestone; implementation and independent result inspection remain pending.
- Lower-tier implementation will follow ADR-0003. No E0 result, core-hypothesis validation, novelty, speedup or publication approval is claimed.

### Implementation service failure

- Attempted the required lower-tier implementation delegation using `glm-5.3-flash:cloud`. The agent failed before implementation with: `ollama cloud is disabled: remote model is unavailable`.
- No model code or experiment was produced by that attempt. Requested an explicit human exception for this model to implement, or restoration of the lower-tier service; reviewer authorization alone was not silently extended to coding-model authorization.
- Human response: **“use luna or sol if you see fit, not another astra agent”**. Implementation is therefore delegated to an explicitly selected Sol/Luna agent; no root-implementation exception or additional Astra agent is inferred.

## 2026-11-12 — E0 local gate accepted; real-text screen preregistered

- Sol implemented ADR-0003; Luna independently checked the contract and supplied hand-calculated loss/causality/state-isolation tests. Root inspected the model, generator, objective, checkpoint, orchestration and test code.
- Root independently ran `uv run --locked ruff check .`, `uv run --locked mypy src/arborlm`, `uv run --locked pytest` (31 passed), and the registered CPU smoke (11/11 checks passed). Exact outputs and compact raw evidence are in `results/e0-2026-11-12/`; full checkpoints/source archives remain locally under the recorded experiment directories.
- Fresh repeat, checkpoint reload and interrupted resume match bitwise within the tested macOS arm64 environment. G0 engineering gate accepted by the authorized reviewer; Astra validation NOT PERFORMED. Linux CI awaits execution. No memory architecture has yet been tested.
- Human approved pinned WikiText-2 local pilot use (ADR-0004). ADR-0005 preregisters six variants × three seeds, exact data/lookup rules, token/resource budgets and screening thresholds before pilot outcomes. A failed screen will stop promotion of that configuration, not establish universal disproof.
- Human additionally requested each checkpoint/check be pushed to GitHub for tracking; completed verification bundles and subsequent experiment outcomes will be versioned and pushed on the work branch. Merge/publication approval remains separate.

### Linux CI and data-acquisition checkpoints

- E0 implementation/evidence pushed as `677ef8e`; draft PR #1 tracks this work. GitHub Actions run `43351992585` passed Linux lint/typecheck, 31 tests and 11 smoke gates. Logs/status and compact CI evidence are preserved under `results/e0-2026-11-12/linux-ci-43351992585/`; full CI artifacts were downloaded locally before expiry.
- Luna acquired approved pinned train/validation files plus the upstream README, 7,025,216 bytes transferred. Both corpus SHA-256 values match ADR-0004; test data was neither acquired nor inspected. Root reran the downloader's 9 mocked tests, Ruff and mypy successfully.
- Root review caught an idempotency bug accepting a manifest when a data file was missing; Luna corrected it and added regression coverage before the acquisition checkpoint was accepted. Failed acquisition attempts now retain status/error history.
- The publisher README has conflicting license metadata (front matter 3.0/GFDL, body 4.0); both are preserved without choosing legal precedence. Exact-byte local-use approval remains recorded; release rights are unresolved. No pilot model has been trained at this checkpoint.

### RAM pilot preflight accepted before trial

- Sol implemented the six registered variants and bounded suite; Luna audited lookup math, tie handling, gradients, initialization, parameter counts and data rules. Root independently reviewed code and reran locked Ruff/mypy, 59 tests and E0 smoke (11 gates), all passing.
- Root independently reconstructed the selected UTF-8 byte chunks and matched both arrays and rank/row/offset identities. Evidence is in `results/p1-preflight-2026-11-12/`.
- Source/config/spec are frozen before trial. Root authorizes the exact ADR-0005 command under its registered CPU/RSS/token/time bounds. No observed pilot loss was used to select thresholds or change settings.
- At the human's request, each completed run will be reported in chat with observed loss/runtime and a bounded interpretation, and completed checkpoints will be pushed to GitHub.

### P1 completed — promotion threshold missed

- All 18 preregistered runs completed within limits; each consumed 131,072 targets. Every run was reported in chat and all six controls for seeds 42/43/44 were preserved/pushed. See `results/p1-2026-11-12/` for full-precision raw results and the authorized reviewer interpretation.
- Learned-tree mean validation NLL: 2.578732837; small dense: 2.588018314. Improvement 0.0092854773 nats/byte is below the required 0.01. **Promotion gate FAILED; do not scale this configuration under this protocol.** The gate was not relaxed.
- Learned routing beat fixed routing for all seeds and avoided the registered gross-collapse condition. Parameter-matched dense had lower loss for all seeds and lower observed training time. These are bounded observations, not significance, novelty, inference speed or general concept proof/disproof.
- ADR-0006 preregisters a separate post-screen diagnostic on existing checkpoints, with no additional training. Its outcome cannot reverse the original gate. Independent artifact/arithmetic audit is pending; Astra review remains NOT PERFORMED.

- Subsequent Luna read-only artifact audit confirmed all 18 cells, target/event counts, arithmetic, identities and actual checkpoint hashes. One Git HEAD changed mid-suite because of a result-only push; the auditor verified identical source archive hashes and no code/config/spec/data changes. See the separate audit record; original metadata remains unchanged.

### Frozen-memory diagnostic — inconsistent contribution

- ADR-0006's 12 evaluations completed with zero training. All original replays and paired key/value permutations within branches reproduced the original validation NLL exactly; checkpoint files remained unchanged.
- Disabling memory slightly improved loss in seeds 42 and 43 but worsened seed 44 by 0.0067755841 nats/byte. Shuffling values followed the same directions. Mean disabled delta was +0.0020039926; mean shuffled-value delta was +0.0021469779. Both missed the registered +0.005 diagnostic threshold.
- Preserve the seed-44 positive dependence and the two opposite-sign outcomes. Useful memory contribution was not reliably demonstrated across seeds at this budget. Nonzero router gradients alone do not establish useful inference memory.
- Results and all 12 raw records are in `results/memory-diagnostic-2026-11-12/`. Earlier promotion failure remains unchanged; scaling is stopped. The broad concept is unproven, not universally disproved. Human merge/publication approval remains pending and Astra review NOT PERFORMED.
- Luna independently audited all 12 raw diagnostic records, target counts, lack of training events, arithmetic and current original checkpoint/index hashes; no discrepancy found. This is recorded separately as an engineering audit, not Astra scientific validation.

### Final tracking checkpoint

- At the research lead's request, each completed run was reported in chat and verification and results checkpoints were pushed to GitHub for tracking. The final local verification passed 67 tests, and [Linux CPU CI run 43354341475](https://github.com/Dandush03/ArborLM/actions/runs/43354341475) passed at commit `6ce7928`.

### Follow-up hypothesis from human lead

For seed 44, validation NLL was 2.5893889144062996 nats/byte for small dense, 2.5889271199703217 for the learned-tree checkpoint with memory disabled, and 2.582151535898447 with memory enabled. The interventions support a benefit from memory in that frozen checkpoint on this validation set; they do not establish statistical generalization. The lead's hypothesis is that optimization inconsistently discovers and exploits useful memory. Validation noise, effects of the shared training trajectory, the finite training budget, and sensitivity to initialization remain plausible explanations. The disabled model retains its jointly trained backbone, so it cannot substitute for a model trained without memory.

A candidate follow-up would separate the random seeds for backbone initialization, memory and router initialization, and batch order; cross those seeds under a fixed budget; and pair evaluations with memory enabled, disabled, and values shuffled. It would also include a control with memory disabled throughout training, report every seed, and define interaction and dependence metrics and thresholds before running. Confirmatory claims would require fresh held-out data because the current validation set informed the hypothesis. This design is neither preregistered nor approved for execution. No new experiments started, and the failed promotion gate remains unchanged.
