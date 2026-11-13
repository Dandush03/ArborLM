# ADR-0001 — Pursue trainable hierarchical parameter memory (provisional)

- Date: 2026-11-12
- Status: **RESEARCH-DIRECTION AGREED; FORMAL ASTRA EXPERIMENT-SPEC REVIEW PENDING**
- Decision owner: Human research lead
- Context: See `docs/RESEARCH_HANDOFF.md`, sections 0–4.

## Decision

Pursue a novel (subject to literature review) language-model architecture consisting of a small causal transformer with trainable hierarchical key-value parameter memory. Train a proof-of-concept from scratch in RAM before introducing an SSD backend. Benchmarks must compare dense, flat-memory, fixed-tree and learned-tree alternatives under controlled budgets.

## Alternatives considered

Faster CPU/GPU/NPU, larger RAM/HBM, NVMe striping, computational storage, conventional compression/quantization, retrofitting MoE expert paging, external RAG. These remain potential baselines or later optimizations but do not test the key hypothesis of learning a better parameter-access pattern.

## Consequences

Positive: testable research hypothesis; hardware-independent first stage; possible scalable storage-backed capacity.

Risks: routing collapse; failure to beat established memory layers; poor generalization; SSD access latency; unproven novelty; training cost.

## Review needed

Astra must approve specific H1 experiment configuration, metrics, statistical gates and code-level scientific invariants before model implementation beyond safe infrastructure scaffolding.
