# ArborLM

**ArborLM** is a research proposal for a language model with **trainable hierarchical neural parameter memory**. The motivating hypothesis is that a model might learn to navigate a very large parameter-memory store while retrieving only a small, useful and physically local working set per token, potentially reducing data movement in SSD-backed inference.

> **Scientific status: untested.** No ArborLM architecture, speedup, model quality or scaling claim is validated as of this starter handoff.

## Begin here

- **[Canonical research context](docs/RESEARCH_HANDOFF.md)** — origin story, precise problem, proposed first architecture, hypotheses, prior art, phases, migration and publication rules.
- [Agent policy](AGENTS.md) — mandatory Astra research-orchestration/validation vs lower-tier coding model split.
- [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md) — baselines, metrics, scientific controls, reproducibility requirements.
- [Research log](docs/RESEARCH_LOG.md) — chronology, decisions and negative outcomes.
- [Paper outline](docs/PAPER_OUTLINE.md) — publication-ready structure without invented results.
- [Codex kickoff prompt](prompts/CODEX_KICKOFF.md) — first implementation task.

## Scope

Initial experiments run locally on whatever ordinary machine is convenient; **this project is not intended to deploy to the owner's infrastructure**. We start with a tiny dense baseline, flat trainable memory and fixed/learned hierarchy in RAM. An NVMe backend and distillation/migration arrive only after the scientific signal is established. Scale is conditional on evidence.

## Code license

Apache-2.0 (see `LICENSE`). Datasets, pretrained weights and future paper artifacts require separate rights review.

## Repository

https://github.com/Dandush03/ArborLM
