# ADR-0002 — Phase 0 baseline and reproducibility framework

- Date: 2026-11-12
- Status: **SPEC: PENDING ASTRA REVIEW**
- Scope: proposed implementation sequence for E0 / G0 only.
- Scientific owner and independent validator: Astra; review record **PENDING**.
- Implementation owner: operator-selected lower-tier coding model, after specification approval.
- Merge, budget, data/license and publication authority: human research lead.
- This document is a Codex consolidation of the existing roadmap for review, not an Astra-authored or approved scientific specification. No experiment or validation occurred while drafting it.

## 1. Sources and repository state

Read in full: `AGENTS.md`, `docs/RESEARCH_HANDOFF.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/RESEARCH_LOG.md`, `docs/decisions/ADR-0001-research-direction.md`, and `prompts/CODEX_KICKOFF.md`. Also inspected the README, paper outline and experiment-record template.

At inspection, HEAD was `2555ed4` and the working tree was clean. The repository contained documentation, the starter archive and an Apache-2.0 `LICENSE`, with no source package, dependency configuration, tests, CI or experiment artifacts. The root handoff copy matched the canonical handoff byte-for-byte. The experiment protocol is a draft and ADR-0001 records research direction, not formal experiment-spec approval.

## 2. Objective and limits

The inherited research question is whether learned hierarchical parameter memory can provide competitive quality with a small active working set and eventually lower measured storage traffic or latency. H1–H5 remain untested. Useful routing, stable training, advantage over strong flat memory, locality benefits, scaling benefits and novelty are all unproven.

Phase 0 implements the existing E0 question: is the training/evaluation infrastructure correct and reproducible? It establishes a tiny resident dense causal-transformer reference and an auditable train/evaluate/save/load/resume path. Synthetic results are engineering checks, not evidence for H1, language-model capability, hierarchy, storage performance or novelty.

The rationale comes from the handoff: establish correctness cheaply before adding retrieval, then isolate learning in RAM before investigating storage. This ADR does not select missing scientific settings. Astra must supply or approve the decision register below before the dependent implementation begins.

## 3. First implementation sequence

| Work package | Deliverables | Dependency and acceptance |
|---|---|---|
| P0 — Reviewable specification | Resolved decision register, frozen E0 configuration, explicit correctness gates, versioned review record | Astra reviews this ADR and applicable protocol sections; record reviewer/model, date, scope and exact reviewed revision |
| P1 — Minimal scaffold | `pyproject.toml`, exact dependency lock, declared Python version, `src/arborlm/`, `tests/`, lint/typecheck configuration and README commands | Routine engineering under the approved brief; verify package installation and command entry points |
| P2 — Experiment records | Validated config and manifest schema; unique run directories; environment capture; raw event logging; checkpoint hashes; failure records | Preserve the protocol's minimum fields and approved E0 applicability rules; test missing fields, collisions and failed-run preservation |
| P3 — E0 reference | Approved synthetic generator/tokenizer/splits, tiny dense causal transformer, bounded CPU train/eval and resume commands | Implement only the exact Astra-approved data, model, objective, optimizer and budget settings |
| P4 — Correctness and reproducibility | Unit tests and one bounded CPU integration smoke workflow covering fresh repeat, reload and interrupted resume | All approved G0 checks pass; capture actual commands and outputs, including failures |
| P5 — CI and handoff | CI running lint, typecheck, unit tests and the CPU smoke workflow; reproduction instructions; implementation PR and review bundle | No external data or model downloads; dependencies installed from the lock; upload diagnostic artifacts on success and failure |

P0 is the current deliverable. No model implementation, benchmark run, dependency installation or PR creation is part of this planning change. Exact package versions and tool configuration must be resolved and recorded during scaffold work, not invented in a run record.

Proposed source responsibilities: configuration validation, synthetic data preparation, dense model, training/evaluation, checkpoint handling and run-artifact recording. Keep these small; do not introduce a distributed framework or a generic storage engine.

## 4. Reproducibility contract to implement after approval

Each run receives a collision-resistant ID and its own directory under `experiments/`. Preserve:

- Approved specification revision and review references; resolved configuration and its hash; experiment family and actual question being checked.
- Exact command/arguments and working directory; full Git SHA, dirty-tree status and a source snapshot or patch when needed to recover the executed code.
- Python/PyTorch and installed dependency versions, dependency-lock hash, OS, hardware, device, numerical dtype, thread settings and determinism settings/limitations.
- All RNG seeds/states; synthetic-generator revision and parameters; tokenizer definition/hash; split construction and checksums; data provenance and applicable license record.
- Actual training steps and non-padding tokens consumed, optimizer/scheduler settings, elapsed time, parameter counts, and raw training/evaluation observations with evaluated-token counts.
- Atomic, versioned checkpoint containing model, optimizer, scheduler if present, step/token counters, RNG and data-order/cursor state, plus config/data identity and checksums.
- Terminal status, errors, interruption/stop reason, deviations and artifacts/checkpoint hashes. A retry is a new run linked to its predecessor; it never replaces failed output.

While a run is active, append raw events and write new checkpoint versions. Finalize artifacts without later overwriting raw evidence; derived summaries and subsequent review/invalidation records remain separately linked and append-only. Finalization after an abrupt process termination must preserve partial evidence and label incompleteness.

Reserve schema versioning for future backbone/router/keys/values/index/layout consistency; do not implement absent memory components in E0. Reject incompatible or incomplete checkpoints rather than silently loading a subset.

Keep total, trainable and active-parameter estimates distinct, with accounting method attached. Metrics not applicable or not measured must carry an explicit reason, never an invented zero. Physical NVMe traffic and routing metrics are not E0 measurements. The protocol example associates E0 with H1; Astra must approve how the manifest explicitly records that E0 checks infrastructure and does not test H1.

## 5. Proposed G0 acceptance checks

These operationalize the existing correctness requirements; Astra must approve numerical tolerances and resource limits before execution.

1. Package installation, lint, typecheck and unit tests pass in the declared environment.
2. Shapes/dtypes and next-token input/target alignment are correct; changing future input tokens cannot change earlier logits within the approved tolerance.
3. The approved objective handles sequence boundaries and masking correctly; evaluation aggregates loss by the approved token weighting and consumes no training updates.
4. The tiny training loop produces finite losses/gradients and updates intended parameters. Any loss-decrease requirement must be preregistered by Astra; do not choose a threshold after seeing a run.
5. Split construction is deterministic and audited for leakage under the approved synthetic-data rules. Evaluation cannot modify model, optimizer or training-data state.
6. Save/reload reproduces evaluation; interrupted/resumed training matches the uninterrupted trajectory under the approved same-environment tolerance, including data position and optimizer/RNG state.
7. Two fresh runs with the same approved configuration and seed reproduce the declared numerical outputs; timestamps, run IDs and elapsed time are not expected to match. Document cross-platform limitations rather than promising bitwise portability.
8. A bounded CPU workflow completes without external datasets, pretrained weights, GPU or cloud services, and emits complete manifests and raw artifacts. Failure-path checks retain evidence without overwriting earlier runs.

If G0 fails, retain the run, label the failure and investigate correctness. Do not escalate architecture or compute to obscure a failed gate. Passing G0 permits only a claim about the checked engineering behavior; independent Astra validation remains separate.

Proposed command interface to implement and document (not available or executed yet):

```sh
python -m ruff check .
python -m mypy src/arborlm
python -m pytest
python -m arborlm.smoke --config configs/e0_cpu_smoke.toml --output-root experiments
```

The smoke entry point should orchestrate train/eval/reload/repeat/resume checks and preserve each run separately. Installation, individual train/eval/resume commands and exact outputs must be supplied with the implementation PR once the lock and CLI exist.

## 6. Decisions requiring Astra review before E0 model work

All entries are **PENDING ASTRA REVIEW**; no implicit defaults are approved by this ADR.

| ID | Decision Astra must settle | Required recorded outcome |
|---|---|---|
| A0 | Review scope and delegation | Actual Astra session/model selected by the operator; reviewed Git revision/content; approval or requested changes; bounded brief for a lower-tier implementer; independent result-review route |
| A1 | Synthetic validation task | Generator/distribution, vocabulary, sample sizes, seed separation, train/validation/test roles, split unit, duplicate/overlap policy and leakage checks; define whether any final test split is needed for G0 |
| A2 | Tokenization and sequence semantics | Tokenizer, special tokens, context length, packing, sequence boundaries, padding/masking and next-token targets |
| A3 | Exact dense baseline | Layers, hidden/FFN sizes, attention heads, positional representation, normalization, activation, residual structure, initialization, dropout, biases and embedding/output weight tying |
| A4 | Training and compute budget | Loss reduction, batch/accumulation size, optimizer and all settings, schedule, clipping, steps/tokens, evaluation cadence, seed list, dtype, device/thread policy, CPU time and RAM bounds |
| A5 | G0 numerical gates | Repeat/reload/resume tolerances and comparison outputs, any learning-sanity threshold, determinism scope, stopping rules and treatment of failures |
| A6 | Measurement definitions | Token-weighted NLL/perplexity semantics, total/trainable/active parameter accounting, FLOPs method and applicability, timing boundaries, memory measurement and required versus deferred inference metrics |
| A7 | Protocol/manifest applicability | Explicit E0/G0 question instead of implying H1 evidence; required fields, missing/not-applicable reasons, artifact sufficiency and allowable deviations |
| A8 | Phase transition | Evidence and independent review required to accept G0 and commission the next specification; distinction between engineering smoke success and scientific quality evidence |

Human approval remains required for dataset rights/use, spending, merge, release and publication. The committed code license does not establish rights to future datasets, weights or manuscripts. No Astra review is claimed by this document.

## 7. Deferred scientific decisions and tracked work

These remain pending and do not block a separately approved E0:

- **E1 / flat memory:** strong flat/product-key baseline selection and prior-work verification; memory dimensions/slots, scoring, retrieval count, fusion, insertion location, trainability and gradient invariants.
- **E2–E3 / hierarchy:** fixed/random controls, partitions, fan-out/depth, router and gradient estimator, temperature/warm-up, tie handling, load balancing, topology changes and stable slot identity.
- **Comparative quality experiments:** real dataset/tokenizer and licenses/contamination assessment; fairness across total capacity, active compute, train tokens, retrieval work and tuning effort; seeds/statistical method; preregistered quality tolerance, collapse and go/no-go thresholds. Principal claims require the protocol's multi-seed standard or explicit exploratory labeling.
- **E4–E5 / locality and storage:** locality objective/proxy and coefficients, physical layout and rebuild policy, cache regimes, actual I/O instrumentation, workloads exceeding RAM, compression/quantization controls, same-checkpoint RAM/SSD parity and measured storage gates.
- **E6 / migration and later scaling:** exact teacher/license, distillation budgets/objectives and controls, adapter/unfreezing policy, compatibility tests, scale gates and human-approved compute budget.
- **Publication/governance:** verified novelty and required baselines, claims tied to raw experiments, artifact retention/release arrangements, naming, rights, authorship and human publication approval.

Order retained: dense baseline → flat memory → fixed hierarchy → learned hierarchy in RAM; storage and migration remain gated later work. Every later scientific design needs its own reviewed specification. Flat memory and HNM are intentionally unfinished tracked scope.

## 8. Risks, evidence and review handoff

Primary phase-0 risks are leakage through generated/packed data, incorrect autoregressive targets or masking, incomplete resume state, nondeterministic kernels, unrecorded environment/source changes, biased loss aggregation and synthetic-task results being mistaken for scientific evidence. The checks above address engineering failure modes; Astra owns their scientific adequacy and interpretation.

The implementation PR must include intent/question, scope/files changed, exact commands and outputs, dependency/environment records, seed/config/data/checkpoint hashes, raw successful/failed/null runs, license/data considerations, unexpected observations, unresolved decisions and separate spec/result/human approval status. Use `templates/EXPERIMENT_RECORD.md` for each substantive experiment. Submit diffs and artifacts for independent Astra review before marking anything `ASTRA VALIDATED`.

Current evidence: document inspection only. No tests, training, benchmarks, literature verification or scientific validation were performed. No performance, novelty or quality claim follows from this plan.
