# Primary-source check before architectural experiments

Checked 2026-11-12 by the authorized Codex reviewer. Scope: existence, titles and abstract-level relevance of the handoff's references. This is not a systematic novelty review, reproduction or assessment of the papers' full methods/results. No ArborLM performance follows from these papers.

| Primary source | Relevance and required follow-up |
|---|---|
| [Large Memory Layers with Product Keys, NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/9d8df73a3cfbf3c5b47bc9b50f214aff-Abstract.html) | Structured trainable memory with product-key retrieval is established prior art. A simple exhaustive flat implementation is a correctness control, not sufficient by itself to establish an efficiency advantage over strong flat retrieval. Read full method and implementation/license before choosing a comparative baseline. |
| [Memory Layers at Scale, ICML 2025](https://proceedings.mlr.press/v267/berges25a.html) | Trainable sparse key-value layers have been studied at large scale. Stored memory size and sparse activation alone are not a novelty claim. Full architecture, optimization and accounting details still require review before a fair comparison. |
| [UltraMemV2, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/bfc03f077688d8885c0a9389d77616d0-Abstract-Conference.html) | Memory-layer placement, value transforms, initialization and memory/FFN allocation are relevant confounders. A failed small prototype cannot dismiss all such variants. |
| [ReMoE, ICML 2026](https://proceedings.mlr.press/v306/zhu26ab.html) | Router training for expert reuse and storage-constrained inference is relevant locality prior art. Its MoE setting differs from ArborLM's proposed parameter-memory layer. |
| [Attention with Routed-Memory, ICML 2026](https://proceedings.mlr.press/v306/zeng26h.html) | Learned hierarchical routing also appears in KV-cache memory. Distinguish dynamically updated activation memory from persistent trained parameter memory; the hierarchy analogy alone is not a contribution. |

## Consequence for the current milestone

E0 is solely an engineering validation. Passing it neither establishes nor refutes the architecture. A subsequent synthetic memory pilot can expose implementation failures and characterize a particular configuration, but scientific language-model quality claims require an approved real-data protocol and strong matched baselines. Broader novelty, scaling and NVMe claims remain untested.

Negative results must name the tested configuration, data, budget and gate. Positive results must name the same restrictions. Neither direction licenses a blanket proof/disproof of every hierarchical neural memory architecture.
