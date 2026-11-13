# ArborLM — agent operating policy

**Start here:** Read `docs/RESEARCH_HANDOFF.md` in full, then `docs/EXPERIMENT_PROTOCOL.md`, before editing model or experiment code. ArborLM is **unproven research**: never claim scientific success until validated experiments exist.

## Mandatory research-model split requested by project lead

- **Astra is responsible for research reasoning, hypothesis/architecture decisions, experiment design, orchestration, interpretation, and final scientific validation.** The actual model must be selected by the user/operator where available.
- A **lower-tier coding model** should perform implementation, tests, scripts, CI, refactors and routine formatting strictly according to an Astra-reviewed specification. It may solve local code tasks, but must not invent or silently change scientific assumptions or report its own work as Astra-validated.
- **`AGENTS.md` is policy text, not a model selector.** Codex may not support Astra in the same environment. If Astra cannot be selected, proceed only with clearly scoped implementation based on already approved specs and mark new scientific choices `PENDING ASTRA REVIEW`.
- Human research lead approves merge/publication/budget decisions. Never claim Astra or human approval without a traceable record.

## Working protocol

1. Record hypothesis, design rationale, baseline, success/failure gates and scientific risks in an ADR or issue marked `SPEC: PENDING ASTRA REVIEW`.
2. After Astra approves, implement the smallest useful change with tests. Do not run costly external services or download large training data without approval.
3. Save exact commands, configs, package versions, seeds, hardware, dataset licenses/checksums and raw metrics for every experiment.
4. Submit code and results for **independent Astra scientific validation**; mark `ASTRA VALIDATED` only with evidence of a real review.
5. Record negative and null outcomes; never inflate the results. Publication claims require human approval.

## Technical defaults

- Small, portable Python/PyTorch prototype first; **no infrastructure deployment** and no premature distributed framework/Rust backend.
- Preserve strong baselines: same dataset/tokenizer and fair training/inference budgets for dense, flat memory, fixed tree and learned hierarchy.
- Keep model-learning questions separate from SSD I/O questions: first RAM only, then same checkpoint with different storage policies.
- Do not confuse *stored parameters* with *active parameters* or *reasoning quality*; report them separately.
- Design atomic/versioned checkpoints for backbone, learned router, keys, values, index and physical layout.
- Run relevant tests before describing work as complete; if tests weren't run, explicitly state so.

## On every PR

Include: intent/hypothesis, scope, files changed, exact commands run, test results, reproducibility artifacts, license/data considerations, unexpected observations, Astra-validation status, and unresolved scientific decisions.

## Repository authority order

1. Human research lead's current explicit direction.
2. Approved research protocol/ADRs.
3. `docs/RESEARCH_HANDOFF.md` origin and north-star constraints.
4. Prior code conventions and routine implementation choices.

If documents disagree, stop and request a recorded Astra/human decision rather than silently choosing.
