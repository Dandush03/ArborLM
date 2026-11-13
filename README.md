# ArborLM

**ArborLM** is a research proposal for a language model with **trainable hierarchical neural parameter memory**. The motivating hypothesis is that a model might learn to navigate a very large parameter-memory store while retrieving only a small, useful and physically local working set per token, potentially reducing data movement in SSD-backed inference.

> **Scientific status: frozen-backbone memory helped, but the matched dense adapter did better.** The earlier promotion failure stands, the broader hierarchical memory concept remains unproven, and scaling is not authorized. The human research lead authorized a Codex reviewer exception; Astra review was not performed.

- [E0 CPU baseline](results/e0-2026-11-12/) passed its training, evaluation and checkpoint reproducibility checks.
- [18-run RAM screen](results/p1-2026-11-12/) found a mean learned-tree improvement of 0.0092854773 nats/byte over the small dense baseline, below the registered 0.01 required for promotion.
- [12 frozen-checkpoint evaluations](results/memory-diagnostic-2026-11-12/) found mean validation loss increases of +0.002003993 nats/byte with memory disabled and +0.002146978 with values shuffled. Effects went in opposite directions across seeds, and both means were below the registered +0.005 threshold.
- [36-run controlled follow-up](results/p2-2026-11-12/) found mean loss increases of +0.000693748 nats/byte with memory disabled and +0.000685635 with values shuffled. Both effects were positive in 22 of 27 learned runs; neither reached +0.005 in any run. All three registered descriptive flags were false. Most of the mean gain over controls trained without memory (0.006731979 nats/byte) persisted after disabling memory (0.006038231). Training outcomes varied, but the follow-up did not establish a strong retained memory benefit at this budget. The earlier promotion failure stands.
- [36 longer-training continuations](results/p3-lt-2026-11-12/) improved validation loss for every learned run and control. Memory-dependence effects grew, but their mean changes and endpoint means remained below the registered 0.005 nats/byte thresholds. The endpoint quality guard passed; the two dependence flags failed.
- [63-cell frozen-backbone comparison](results/p4-2026-11-12/) passed the registered capacity and slot-association criteria: mean loss fell by 0.021989 nats/byte versus the unchanged backbone and rose by 0.022222 when values were shuffled. The equal-parameter dense adapter had lower loss in all 27 matched pairs, so dense tolerance and the composite P4 criterion failed. P1–P3 outcomes are unchanged.

## Begin here

- **[Canonical research context](docs/RESEARCH_HANDOFF.md)** — origin story, precise problem, proposed first architecture, hypotheses, prior art, phases, migration and publication rules.
- [Agent policy](AGENTS.md) — mandatory Astra research-orchestration/validation vs lower-tier coding model split.
- [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md) — baselines, metrics, scientific controls, reproducibility requirements.
- [Research log](docs/RESEARCH_LOG.md) — chronology, decisions and negative outcomes.
- [Paper outline](docs/PAPER_OUTLINE.md) — publication-ready structure without invented results.
- [Codex kickoff prompt](prompts/CODEX_KICKOFF.md) — first implementation task.

## Scope

The completed model experiments ran locally on CPU with model weights in RAM. The project will not deploy to the owner's infrastructure. NVMe, distillation and scaling remain outside the current scope.

## Code license

Apache-2.0 (see `LICENSE`). Datasets, pretrained weights and future paper artifacts require separate rights review.

## Repository

https://github.com/Dandush03/ArborLM

## E0 CPU baseline

[E0's approved specification](docs/decisions/ADR-0003-e0-approved-spec.md) tests a
small dense Transformer's training, evaluation and checkpoint infrastructure on
generated integer motifs. This is an engineering check; it supplies no evidence
about hierarchy, storage I/O or language ability. The specification was reviewed
under the research lead's Codex override. Astra review was not performed.

Use a Git checkout on macOS arm64 or Linux x86-64. Install the pinned Python and
dependencies, then run the checks from the repository root:

```sh
uv python install
uv sync --locked --extra pilot
uv run --extra pilot ruff check .
uv run --extra pilot mypy src/arborlm
uv run --extra pilot pytest
uv run python -m arborlm smoke --config configs/e0_cpu_smoke.toml --output-root experiments
```

The smoke command creates two independent training runs, reloads the first final
checkpoint in a new process, and compares a separate interrupted/resumed run.
It checks bitwise equality within one numerical environment. macOS and Linux are
separate numerical environments; no cross-platform bitwise match is promised.

Run individual operations with the same configuration:

```sh
uv run python -m arborlm train --config configs/e0_cpu_smoke.toml --output-root experiments
uv run python -m arborlm eval --checkpoint experiments/<run-id>/checkpoint-32 --output-root experiments
uv run python -m arborlm train --config configs/e0_cpu_smoke.toml --output-root experiments --stop-after 16
uv run python -m arborlm train --config configs/e0_cpu_smoke.toml --output-root experiments --resume experiments/<stopped-run-id>/checkpoint-16
```

Substitute actual run IDs. Load only trusted local checkpoints generated by
ArborLM; checksums detect corruption, not a maliciously altered checkpoint and
index. Atomic publication requires a local filesystem supporting an exclusive
directory rename.

Each command prints a unique run directory, with a terminal status, captured
stdout/stderr, source snapshot and lock hash, resolved config, dataset
checksums and raw events. Smoke stores its five child runs under `children/`.
Training runs also retain immutable checkpoints. Retries write a fresh run
directory; preserve failure records and local artifacts for review. CI artifact
uploads are temporary and do not replace the local research archive.


## Registered RAM pilot (local only)

[The P1_SCREEN protocol](docs/decisions/ADR-0005-ram-pilot-spec.md) defines the
fixed six-variant, three-seed screen. After reviewer preflight, run against the
approved local train and validation acquisition:

```sh
uv sync --locked --extra pilot
uv run --locked --extra pilot python -m arborlm pilot \
  --config configs/p1_ram_screen.toml --data-dir data/wikitext2 --output-root experiments
```

The suite rechecks the pinned files, freezes one ranked byte-token dataset,
and records all cells under a unique local run directory. The suite stops on a
failed cell and retains partial evidence and the unexecuted cell list. Keep
dataset bytes and binary checkpoints local. CI only exercises synthetic
fixtures and E0; it does not acquire WikiText-2 or execute this pilot.

## Controlled optimization follow-up (local only)

[ADR-0007](docs/decisions/ADR-0007-controlled-optimization-followup.md) defines the
27 learned runs and nine controls, all at the same model size and training
budget. To reproduce the run with the approved local data, use a fresh results
directory; the command refuses to overwrite an existing export.

```sh
uv sync --locked --extra pilot
uv run --locked --extra pilot python -m arborlm.optimization_followup \
  --data-dir data/wikitext2 --output-root experiments \
  --results-root results/p2-reproduction
```

Keep corpus bytes and binary checkpoints local. Astra review was not performed;
human merge and publication approval remain pending.
