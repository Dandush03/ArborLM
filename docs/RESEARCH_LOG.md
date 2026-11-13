# ArborLM — Research Log

Chronological, append-only notes. Scientific decisions also go into reviewed ADRs. **There are no experimental results yet.**

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
