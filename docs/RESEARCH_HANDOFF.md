# ArborLM — Research Origin, Problem Statement, Proposed Architecture, and Scientific Roadmap

> **Canonical research handoff | Working draft v0.1 | 2026-11-12**
>
> Repository: https://github.com/Dandush03/ArborLM
>
> Status: **Proposal / untested hypotheses. No demonstrated ArborLM speedup, quality gain, or new model exists yet.**
>
> Purpose: preserve the entire design rationale and the initial direction as an enduring source of truth for the research lead, Astra research review, lower-tier Codex implementers, future collaborators, and publication. Read this before writing model code.
>
> Companion files: `AGENTS.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/RESEARCH_LOG.md`, `docs/PAPER_OUTLINE.md`, `prompts/CODEX_KICKOFF.md`.

## 0. The original idea — read this first

ArborLM began with a simple series of questions about large-model inference:

1. Colibrì can run a very large sparse Mixture-of-Experts (MoE) model by streaming experts from SSD without fitting all weights in GPU memory. **Why is it so slow?**
2. If newer AI CPUs or NPUs produce tokens faster, **will they solve the problem?** Not if inference mostly waits for weights to arrive.
3. If M.2 NVMe SSDs are fast, **why must weights travel through RAM and CPU caches?** Conventional CPU arithmetic uses registers and processor-accessible memory, not NAND flash cells. Streaming can avoid *resident model weights*, but not all staging/buffering.
4. Could the hardware architecture change to **compute near or in storage**? Yes in principle (computational storage and processing-in-memory), but it still faces internal NAND bandwidth, latency, power and cost constraints.
5. If hardware is limited by the amount of data moved, **could we compact model weights more intelligently?** Compression, quantization and expert sharing are useful, but they preserve a model structure that might fundamentally require too many weight reads.
6. **What if the model's knowledge/computation were arranged into layers or a navigable hierarchy?** The input vector could identify a region similar to a million indexed vectors, then walk through increasingly specific branches, bringing back only relevant information or computational parameters. It would behave more like a database query planner than like a monolithic matrix traversal.
7. **What if the neural model learns that hierarchical organization itself, during training, rather than retrofitting an ordinary model into a database?** This is the chosen direction.

**Original intuition:** _Instead of asking how to read a huge model faster, can we train a model that knows where the small amount of relevant learned memory lives, visits only that region, and becomes more efficient as its total stored memory grows?_

**North star:** Build a language model whose *total learned capacity* can grow primarily with affordable storage, while its *working set, I/O per token, and active computation* grow much more slowly—without materially degrading language-model quality. This is a research goal, not an established property.

**The first approach is NOT “put SQL around Qwen,” generic RAG, or an SSD-only port of MoE.** The first approach is a **native trainable hierarchical neural memory layer**, integrated into a small causal-language-model backbone, rigorously compared to flat memory layers and dense baselines. SSD is introduced only after learning works in RAM.

## 1. Precise problem statement

### 1.1 System problem: the cost of moving parameters

Most contemporary LLMs repeatedly use large weight matrices during token generation. Dense models activate many of their parameters each forward pass; sparse MoE models activate fewer experts but may still incur costly expert loads when those weights do not fit in accelerator or system memory. In a disk-streaming system, token generation may be dominated by storage reads and unpredictable access patterns rather than arithmetic throughput.

For a **simplified, I/O-bound** case:

`token_rate <= effective_storage_bandwidth / bytes_read_from_storage_per_output_token`

That is a bandwidth-bound ceiling, **not a general performance predictor**. CPU/GPU compute, RAM/cache bandwidth, SSD random-I/O latency, batching, routing, filesystem behavior, KV cache, and host-device overhead can dominate in other settings. Sequential bandwidth specifications cannot be applied directly to scattered small reads.

Illustrative scale only: if a hypothetical inference path must read 10 GB of weights per generated token, an effective 10 GB/s stream cannot exceed ~1 token/s from that storage path regardless of how quickly the CPU can multiply those weights after arrival. Faster NPUs do not remove this dependence. Model compressibility might help, but a more radical option is **change which learned parameters need to be read at all**.

### 1.2 Scientific problem: capacity versus active working set

Can we train a parameterized memory that carries useful information in millions or billions of entries, while only activating a small number of entries for each token? Can the routing be both **semantically useful** (quality) and **physically local** (cache/I/O), under stable training? Can the resulting model remain competitive with conventional alternatives at comparable training and inference budgets?

### 1.3 Boundaries of the claim

- **Total learned parameters are not the same as reasoning ability.** A model with 1T stored memory parameters does not automatically have the capability of a dense 1T model.
- **Sparse access is not automatically fast.** Random small reads, lookup overhead and branches can negate byte savings.
- **Hierarchy is not automatically better than flat memory.** Prior product-key and sparse-memory layers are strong baselines.
- **No current evidence establishes our method as a novel publication.** Literature review and controlled experiments must determine whether there is a unique contribution.
- **No expectation to use the owner's homelab/production infrastructure.** This is a portable proof of concept. Larger external compute/storage may be considered only if results warrant it.

## 2. Research objective, hypotheses, and falsification

### Primary research question

> **Can a language model learn a multi-stage, locality-aware hierarchy over trainable neural memory that matches the quality of flat memory alternatives while reducing actual bytes read from slow storage, latency, and/or cost per output token as total memory grows?**

### Candidate hypotheses (all unverified)

**H1 — Learnability:** A small transformer plus trainable hierarchical key–value memory can be trained end-to-end without unstable routing collapse, and improves held-out language-model loss over a matched no-memory baseline at useful memory budgets.

**H2 — Hierarchy value:** Hierarchical routing can match or improve a strong flat memory-layer baseline at matched total parameters, active FLOPs, train tokens, retrieval count, and tuning budget (or establish a better quality/latency Pareto point).

**H3 — Locality:** Explicit locality/I/O-aware training objectives improve reuse of nearby entries and reduce physical storage traffic without unacceptable quality degradation.

**H4 — SSD viability:** After porting the learned values to NVMe, the savings in transferred bytes outweigh routing, indexing, page fetching and decompression overhead under at least one controlled workload with total memory exceeding available RAM.

**H5 — Scaling:** As total memory increases, quality improves on at least some well-defined tasks while active compute and I/O grow materially more slowly than total stored parameters; scaling relationships must be measured, not asserted.

### Null / failure outcomes to report

- Flat memory is consistently equal or better at the same budget.
- Hierarchy learns poor routing and collapses into few hot leaves.
- Routing is sensitive to token/context shifts and generalizes poorly.
- More memory increases memorization but not reasoning or downstream accuracy.
- Random I/O latency dominates despite small payloads.
- Training cost or index-maintenance cost overwhelms inference gains.
- Gains disappear after fair hyperparameter tuning and multiple seeds.

A **negative or null result is scientific data**. Preserve failed runs, profiling traces, and reasons for stopping.

## 3. Proposed first architecture: HNM-Layer v0

Working name: **ArborLM** (project/model family); **HNM** (Hierarchical Neural Memory, layer concept). Names are provisional; do not claim an established class of models.

### 3.1 Components

1. **Small causal transformer backbone:** handles token context, attention, composition, and the computations memory lookup cannot replace. First tests use a train-from-scratch small model, not a huge existing checkpoint.
2. **Query projector:** maps hidden state `h` to a retrieval query `q`.
3. **Learned high-level router:** selects a small number of promising branches/partitions, perhaps with differentiable soft routing during warm-up and sparse routing after stabilization.
4. **Local key index:** ranks keys within selected branches (not the whole store) and selects `k` value slots. Key organization and branch boundaries should eventually be learned.
5. **Trainable memory values:** parameters updated through the training objective, not a static corpus of retrieved documents. Values can form a weighted combination, undergo small value transformations, then be projected back into the model's hidden dimension.
6. **Fusion/gating:** memory result is gated into the backbone residual stream to reduce destabilization.
7. **Storage policy (later):** indexes and frequently accessed values in RAM; cold values in block-aligned NVMe segments; cache/prefetch routines; immutable/versioned memory snapshots for reproducibility.

### 3.2 Proposed forward pass

For hidden state `h` at a selected transformer layer:

```text
q = W_q h
branch_candidates = route_top_b(q, learned_tree)
S = local_top_k(q, branch_candidates, learned_keys)
a_i = softmax(score(q, key_i) / temperature) for i in S
m = sum_{i in S} a_i * value_i
h_next = h + sigmoid(gate(h)) * W_o m
```

These equations are a **prototype**; alternative scoring, normalization, multihead lookup, temperature, or value transforms should be logged as design choices. Router gradients require explicit treatment: start with dense/soft local routing for differentiability, then investigate sparse selections/straight-through or other estimators. Do not assume ordinary `top_k` is differentiable through selection.

### 3.3 Why hierarchical rather than one giant vector search?

The initiating analogy was a query vector matching a universe of **~1 million related vectors**. The intended optimization is **search over a large universe, retrieve only a tiny relevant subset**. Transferring all one million entries would defeat the purpose. A tree or graph narrows the search in stages, potentially enabling: small in-memory routing metadata, fewer comparisons, physically co-located relevant values, bounded memory traffic, and hardware-aware caching.

The scientific uncertainty is whether the learned hierarchy and all its lookup costs outperform existing flat/product-key/hashed retrieval mechanisms.

### 3.4 Example size calculation (illustrative, not a benchmark)

At one memory layer:

| Item | Calculation | Raw size |
|---|---:|---:|
| One million FP16 keys, dim 128 | `1,000,000 × 128 × 2 bytes` | **256 MB** |
| One million FP16 values, dim 1,024 | `1,000,000 × 1,024 × 2` | **2.048 GB** |
| Top-32 values actually read | `32 × 1,024 × 2` | **65,536 bytes = 64 KiB** |

This excludes metadata, router params, index memory, page/block amplification, caching, attention/FFN traffic and any intermediate vectors. It shows the *opportunity*, not realized SSD I/O: 32 random reads could be very slow. Also, a 1M-entry store may be too large for phase-0 training; begin with 4K/16K/65K slots.

### 3.5 Learning the hierarchy

Start simple and iterate:

- **v0a — fixed balanced tree, learned keys/values:** isolates the effect of hierarchical lookup from tree-learning difficulty.
- **v0b — learned branch routers:** train gating weights/centroids while maintaining fixed partitions. Track entropy, usage balance, gradients and load.
- **v0c — adaptive topology:** occasionally split oversubscribed branches or merge underused branches at checkpoint boundaries; retrain/recalibrate router after a rebuild. Never silently reorder learned values in-place.
- **v0d — locality-aware training:** add a penalty/proxy for number of blocks/pages touched and miss probability, rather than simply the number of retrieved bytes. Optimize a measured systems proxy, validate with physical I/O traces.

Objective candidate:

`L_total = L_language + λ L_router + β L_io_proxy + γ L_load_balance [+ δ L_distillation]`

Coefficients, objective proxies and stability mechanisms are experimental choices and require ablations. A proxy can be gamed: route to one nearby leaf but lose predictive capability. Quality always remains a gating metric.

### 3.6 What belongs in memory?

Trainable key-value **model parameters**, not plain-language SQL rows and not an external static document RAG corpus. SQL/database metaphors guide indexing, clustering and layout. At inference, the critical path should use compact binary tensors and efficient lookup kernels; SQLite/RocksDB/SQL may be useful for metadata, run management or offline indexing, but should not be presumed optimal per-token data-path engines.

Separate, versioned external knowledge stores may be explored later, but must not be confused with this architecture's learned parameter memory.

### 3.7 Where to insert layers

Initially insert **one memory layer** at a controlled backbone location and evaluate. Then test multiple layers. Avoid immediately replacing every FFN—attention and nonlinearity can carry capabilities not restored by a simple value lookup. Only experiment with partial FFN replacement after safe additive augmentation is proven.

## 4. Other approaches discussed, and why they are not phase 1

| Idea | What it helps | Why not phase 1 |
|---|---|---|
| Faster CPU / NPU / GPU | Arithmetic throughput | Does not inherently fix cold weight I/O bottlenecks |
| Bigger/faster NVMe, multi-drive striping | Transfer bandwidth and parallelism | Hardware-dependent scaling; unchanged weight access demand |
| More RAM / HBM | Residency, latency, bandwidth | Expensive capacity; less useful for proving new algorithmic idea |
| Computational storage or in-memory compute | Move arithmetic close to data | Requires specialized hardware; NAND/internal bandwidth still matters |
| Better lossless compression | Fewer transferred bytes without altered math | Compression ratio/decode speed are limited; may not solve the access pattern |
| Quantization / shared expert bases | Smaller representation; cheaper access | Useful future baseline/add-on but can change quality and doesn't test new hierarchy |
| Traditional sparse MoE | Only some experts activated | Strong baseline; cold experts may still require large disk reads |
| Flat trainable memory / product-key memory | Sparse learned parameter retrieval | **Required baseline**, not our proposed hierarchy |
| RAG / document vector DB | Retrieve external information | Different scientific target: learned model parameters, not a corpus |

**Key pivot:** We are not trying to squeeze an unchanged huge model into existing hardware. We are asking whether **training a new model to access only selected learned representations** changes the memory-scaling curve.

## 5. Relationship to prior work — novelty is provisional

Literature below must be rechecked and expanded before any originality claim. Links are official/primary when available.

1. **Lample et al., _Large Memory Layers with Product Keys_ (NeurIPS 2019)**: structured trainable memory and efficient product-key lookup. https://proceedings.neurips.cc/paper/2019/hash/9d8df73a3cfbf3c5b47bc9b50f214aff-Abstract.html
2. **Berges et al., _Memory Layers at Scale_ (ICML 2025)**: sparse trainable key-value memory scaled to large numbers of memory parameters. https://proceedings.mlr.press/v267/berges25a.html
3. **Huang et al., _UltraMemV2_ (ICLR 2026)**: redesigned sparse memory layers with results at high total capacity. https://proceedings.iclr.cc/paper_files/paper/2026/hash/bfc03f077688d8885c0a9389d77616d0-Abstract-Conference.html
4. **Zhu et al., _ReMoE_ (ICML 2026)**: improve expert reuse/locality through router tuning in memory-constrained MoE, illustrating an important neighboring idea. https://proceedings.mlr.press/v306/zhu26ab.html
5. **Zeng et al., _Attention with Routed-Memory for Learnable Sparse Control_ (ICML 2026)**: hierarchical routing applied to KV-cache memory, importantly **different from a trainable parameter store** but relevant precedent. https://proceedings.mlr.press/v306/zeng26h.html
6. **Colibrì (JustVugg)**: systems inspiration for disk-streamed MoE weights, caching, prefetching and multi-tier residency; an inference system, not the proposed new model class. https://github.com/JustVugg/colibri

**Potential differentiation (not established):** jointly learned hierarchical *parameter memory* with explicitly optimized storage locality, physical value placement, and measured NVMe I/O as a first-class component of language-model training/evaluation. Prior work may cover parts or all of this; conduct systematic novelty search and run corresponding baselines.

## 6. Experiment and migration plan

The scientific path must move from cheapest falsification to costly scale. **Do not start with a 700B model, multi-GPU cloud cluster, Rust engine or production service.**

### Phase 0 — research hygiene and minimal runnable loop

- Pin Python, PyTorch and dependencies; deterministic seeding; one tiny text or synthetic dataset; uniform tokenizer; unit tests.
- Implement and validate a tiny dense autoregressive transformer; demonstrate train/evaluate/save/load/reproduce.
- Establish the experiment registry and benchmark metric logging before proposing any speed claim.
- Produce fixed seed data partitions, repository SHA, environment snapshot, checkpoint hashes, and raw metrics.
- Deliverables: reference baseline and validated protocol.

### Phase 1 — proof of scientific signal in RAM

- Compare **dense baseline**, **flat trainable memory**, **fixed-tree hierarchical memory**, then **learned-router hierarchical memory**.
- Begin with 4K-65K memory slots; only grow toward 1M when training is stable. A 20M–50M total-parameter backbone is a **planning target**, not a requirement for the smoke test.
- Record next-token NLL/perplexity, throughput, peak RAM, trained/activated parameter count, router utilization and lookup statistics.
- Keep memory in RAM to remove NVMe system noise and isolate the model-learning question.
- First success gate: quality at a fair budget and trainability without collapse. If not, investigate failure and stop scaling.

### Phase 2 — stronger, fair comparison and ablations

- Match tokenization, data, training tokens, active FLOPs, evaluation protocol and tuning efforts as closely as feasible. Also report unavoidable mismatches.
- Ablate flat vs fixed-tree vs learned-tree vs learned-tree + locality penalty; vary top-k and branch fan-out, depth, number of memory layers, and memory capacity.
- Use **at least 3 seeds** for principal claims if budget permits; otherwise label results exploratory and do not claim significance.
- Separate end-to-end quality from index-only microbenchmarks.
- Deliverables: tables, confidence intervals or variability, failed-run notes, reproducible scripts.

### Phase 3 — SSD-backed inference without changing weights

- Freeze a trained checkpoint and memory index; store memory values in block-aligned immutable NVMe segments with versioned metadata.
- Keep learned router/index and a cache in RAM; test cold cache, warm cache, and memory larger than host RAM.
- Measure actual bytes/read operations per generated token, random I/O amplification, prefill vs decode, p50/p95 latency and token throughput. Capture cache hit rates.
- First compare to **the exact same checkpoint with resident memory** to isolate storage tax; then to other architectures at comparable quality.
- Add grouped reads and prefetch only after measuring initial bottlenecks.
- Deliverables: read traces, SSD-vs-RAM curves, hardware fingerprint, correctness parity tests.

### Phase 4 — storage-aware training and learned topology

- Train an I/O proxy based on block accesses, locality and cache behavior; periodically rebuild physical layout from stable router/slot statistics.
- Checkpoint tree/key/value/physical layout atomically with schema IDs. Test deterministic retrieval after restore and migration.
- Ablate prefetch, cache policies, tree rebuilds, locality loss and data arrangement individually.
- Deliverables: quality/throughput/I/O Pareto frontier and honest analysis of collapse and instability.

### Phase 5 — migrate an existing teacher model (optional research branch)

- Use a legally compatible open-weight pretrained teacher (candidate: small Qwen model; **verify exact checkpoint and license before choosing**).
- Begin **additive**: freeze teacher backbone, learn memory projections and values with language-model + teacher-logit distillation; then optionally unfreeze adapters.
- Compare to teacher, same-size student without memory, flat-memory student, and additive HNM student. Record distillation compute and data cost.
- Only attempt partial FFN replacement after quality survives. It is **not** a direct file-format conversion of arbitrary teacher weights.
- Deliverables: validated migration procedure, mapping/versioning specs, quality and cost deltas.

### Phase 6 — native ArborLM scaling (conditional)

- Train backbone + hierarchical memory jointly from scratch once earlier gates pass.
- Consider external compute if needed, but do not deploy or spend substantial money without explicit approval.
- Scale total learned memory while keeping *active* parameters and I/O as controlled metrics.
- Compare memory-parameter count, activated parameters, backbone size and dataset scaling separately.
- Deliverables: reproducible model family and scaling-law **measurements**, not a promise of GML/trillion-model performance.

## 7. Fair evaluation and definitions

### Quality

- Held-out cross-entropy / perplexity under a declared tokenizer and corpus; standardized downstream tests only when model scale makes them meaningful.
- Memorization, novel composition, generalization to out-of-distribution text, long-context retention and coding/reasoning probes as relevant.
- Document train/test contamination risks. Do not advertise general reasoning gains from perplexity alone.

### Systems metrics

- Prompt prefill throughput separately from decode tokens/sec; time to first token; per-token latency distribution.
- Host RAM, accelerator memory, peak storage use, number/size of read operations, logical requested bytes versus **physical disk bytes**.
- Effective random versus sequential I/O, cache hit/miss, average branches visited, entries selected, routing distribution, imbalance/entropy.
- Cost per useful token (hardware/cloud/time) if and only if a credible cost model exists.

### Fairness

- Same data split, tokenizer, number of train tokens and budget where possible; matching a single parameter count is insufficient for sparse models.
- Report total parameters, *activated* parameters, trainable parameters, model FLOPs, optimizer state, data consumed and training wall time.
- Run meaningful controls: dense, flat retrieval, fixed/random hierarchy, trained hierarchy; same checkpoint in RAM vs SSD.
- Distinguish **quality of architecture** from **efficiency of implementation**.
- Track cold and warm disk caches; define whether the OS page cache is enabled, controlled, or explicitly flushed.

### Example go/no-go gates (to review before experiments)

- **Learning gate:** hierarchical model trains stably and is not materially worse than strong flat baseline at similar active cost.
- **Novelty gate:** literature scan identifies an unresolved contribution and requisite comparison.
- **I/O gate:** SSD implementation demonstrates a real measured byte or latency benefit at matched quality, not just synthetic bandwidth projection.
- **Scale gate:** added stored memory improves something measurable without unacceptable compute/training inflation.

These are provisional gates, not achieved results. Record changes before observing the main evaluation results.

## 8. Migration/compatibility design for future model families

Do not tie the memory backend to a single transformer or vendor. Define a versioned contract:

- `backbone`: architecture, revision/hash, hidden dimension, layer insertion points, tokenizer id.
- `query_adapter`: hidden-to-key dimensions, normalization, weights, architecture version.
- `router`: tree metadata, branch weights, fan-out, selection strategy, router schema version.
- `memory`: slot IDs, keys, values, dtype, dimension, optimizer/checkpoint consistency.
- `placement`: immutable block files, slot-to-block map, alignment, compression, checksum, index version.
- `training`: dataset manifest, loss terms, teacher/revision, optimizer state, RNG state.

Migration scenarios:

1. **Same backbone, reorganized physical memory:** no learned weights change, rebuild slot-to-block map and validate identical retrieved values.
2. **Same backbone, changed routing topology:** remap stable slot IDs, retrain/calibrate router, quantify quality/latency regression.
3. **New backbone, same hidden dimension:** test adapter alignment; do **not** assume old memory is semantically compatible; re-distill and evaluate.
4. **New backbone, different hidden dimension:** new query/output adapters and likely retraining of memory. Compatibility is a hypothesis requiring tests.
5. **Fresh native model:** train backbone and memory jointly under a new version; use benchmark continuity, not direct weight compatibility, as the migration contract.

Version all components together; never promise lossless transfer of learned memory semantics across dissimilar backbones.

## 9. Research operation with Codex and Astra — mandatory preference

**Owner's explicit instruction:** All *scientific reasoning, hypothesis formulation, architectural decision-making, experiment design, result interpretation, and final validation* are to be performed using **Astra**. **Lower-tier models** should drive routine implementation, scripting, test-writing, benchmarks, documentation formatting, and mechanical refactors **under an Astra-approved specification**. Astra orchestrates, reviews and validates their outputs.

**This is a workflow policy, not a capability claim.** Repository files and prompts cannot forcibly select Astra or dynamically switch the Codex model. The operator must choose the actual model in the product/environment where available. If Astra is not available in a particular environment, leave a pending **Astra-review checkpoint**; a lower-tier coding agent must not claim that review occurred.

### Required workflow for every substantive change

1. **Astra — SPEC:** formalize research objective, hypotheses, expected invariants, evaluation, risks, and implementation acceptance tests. Save a reviewed task brief or ADR in Git.
2. **Lower-tier implementer — BUILD:** write or modify code and tests strictly within the brief. Flag scientific ambiguities instead of inventing new assumptions. Capture actual commands and outputs.
3. **Lower-tier implementer — SELF-CHECK:** run tests/formatters, record benchmark environment and results; open PR for review.
4. **Astra — VALIDATE:** independently review diffs, math, data splits, loss functions, gradients, benchmark fairness, reproducibility, results and claims. Re-run or request verification for suspicious metrics. Mark `ASTRA VALIDATED` only if an Astra session demonstrably performed that review, with a link/record.
5. **Human research lead — APPROVE:** decide merge, budget, release, credit/authorship and publication. Models never silently approve themselves.

### Responsibility matrix

| Work | Astra | Lower-tier implementation agent | Human research lead |
|---|---|---|---|
| Scientific reasoning & architecture | **Owns** | May report factual observations, not change hypothesis | Approves |
| Experimental protocol and primary metrics | **Owns** | Implements protocol | Approves |
| Code, tests, CI and scripts | Specifies/reviews | **Implements** | Reviews as needed |
| Dataset, compute/cloud spend, licenses | Reviews scientific/ethical implications | Checks tooling | **Approves** |
| Analyze benchmark conclusions | **Owns** | Produces raw data | Approves claims |
| Manuscript scientific interpretation | **Owns drafting/review** | Formatting/automation only | **Responsible author** |

Do not present AI systems as paper co-authors. Disclose AI assistance as required by venues/policies; human contributors remain responsible for integrity, rights and authorship.

### Suggested labels

`STATUS: PROPOSAL`, `STATUS: SPEC-APPROVED`, `STATUS: IMPLEMENTED-UNREVIEWED`, `STATUS: ASTRA-VALIDATED`, `STATUS: HUMAN-APPROVED`, `STATUS: REJECTED`, `STATUS: SUPERSEDED`.

## 10. Reproducibility, documentation and publication rules

- Every important run receives a unique ID and immutable experiment directory containing the experiment protocol, config, code SHA, environment/hardware fingerprint, seed, data manifest+checksums, command, logs, summary metrics, checkpoint hashes, runtime/cost and exceptions.
- Keep raw output **separate** from derived summaries; preserve failure/negative outcomes.
- Save pre-registered hypotheses and acceptance gates before looking at held-out results. Note exploratory changes explicitly.
- Never include invented performance, reproducibility claims, statistical significance or citations. Distinguish projections from measured numbers.
- Require peer-review-style reproducibility: enough details to rebuild architecture, datasets, environment and evaluations. Align with NeurIPS paper checklist: https://neurips.cc/public/guides/PaperChecklist
- Use Git tags/releases, permanent artifact archives/DOIs (e.g., Zenodo when ready), and separate licensing for code, datasets, checkpoints and manuscript when needed.
- Maintain bibliography (`paper/references.bib` later), claim-to-experiment table, limitations, responsible-release notes, related-work matrix, and exact reproduction commands.
- Submission path is conditional: public repo/technical report -> preprint as appropriate -> workshop or peer-reviewed venue if scientifically justified. Check current venue rules, deadlines, anonymization and AI-use policies before submission.

**Terminology:**
- *total parameters*: all learned scalar parameters including inactive memory.
- *active parameters*: parameters accessed/computed for a token (report estimator details).
- *on-disk capacity*: weights/values that fit in persistent storage; not synonymous with capability.
- *quality matched*: models compared under a declared statistical/metric tolerance, not assumed equivalent.
- *reproducible*: environment, code and data sufficiently specified for independent verification, not merely "seed set".

## 11. First Codex task — what to build before anything else

**Initial PR: repository scaffolding and a working baseline, not a performance claim.**

1. Read this handoff and `AGENTS.md`, then write `docs/decisions/ADR-0002-phase0-plan.md` for Astra review. Do not implement model-code scientific decisions until that review.
2. Create `pyproject.toml`, a small `src/arborlm/` package, tests, and deterministic train/eval scripts. Prefer PyTorch + standard Python, no premature Rust or custom SSD kernel.
3. Implement a **minimal causal transformer baseline** and a synthetic/test-size dataset; provide one bounded CPU smoke test that trains, serializes, reloads and reproduces an evaluation result.
4. Add structured run manifest/logging and unit tests for tensor shapes, causal masking, gradient flow, checkpoint restore and seed behavior.
5. Implement the **flat memory layer** after baseline correctness is verified; document API and expected invariants.
6. Implement **fixed-tree HNM** once a comparable flat baseline is available; do not silently change optimization budgets or training data.
7. Raise an explicit Astra review checkpoint before any assertion that ArborLM improves model quality or token speed.

### First milestone definition of done

- `pytest` and the tiny CPU test pass locally/CI with no external downloads required.
- Repeat-run seed produces matching metrics within declared numerical tolerance; determinism limitations documented.
- Experimental config and README contain exact run instructions.
- No GPU/cloud/large dataset required for smoke tests.
- Flat memory and HNM are either implemented/tested or tracked as later tasks; do not hide unfinished scope.
- PR has `SPEC -> IMPLEMENTATION -> VALIDATION` traceability, even if Astra/human review is pending.

## 12. Outstanding decisions — not assumptions Codex may invent

- Which first benchmark dataset/tokenizer, and its redistribution/training license?
- Exact baseline architecture, memory dimensions, depth, top-k, routing temperature and budget matching?
- Which gradient estimator and topology-update policy avoids unstable indexing?
- How to charge routing/index work in FLOPs and activated-parameter metrics?
- Which SSD layouts and cache policies are realistically portable?
- Whether compression/quantization is allowed in phase-3 baseline or only as separate ablation?
- What size model is realistic for first CPU experiments? No production hosting planned.
- Naming/branding clearance and eventual paper authorship, repository governance, release rights.
- How Astra is selected and its actual validation is recorded in the available Codex/ChatGPT environment.

## 13. Decision log of this conversation

| Decision | Status | Rationale |
|---|---|---|
| Work under the name **ArborLM** | Chosen, working name | Memorable hierarchical/tree analogy |
| Build a new model rather than just compress existing weights | Chosen research direction | Optimize access pattern at training time |
| Trainable hierarchical neural parameter memory | **Core hypothesis** | Learn to navigate small relevant working sets |
| Small causal transformer backbone | Initial design | Preserve contextual reasoning/composition |
| Start in RAM, SSD later | Chosen experiment order | Separate learning validity from systems noise |
| Portable proof of concept; not hosted on owner's infrastructure | Explicit constraint | Minimize cost and dependencies |
| Potential very-large-scale/GML-scale future | Aspirational | Conditional on evidence, not a phase-0 commitment |
| Treat SQL as an indexing analogy | Clarification | Do not query relational SQL for each token by default |
| Publish reproducible research including failures | Explicit goal | Scientific accountability |
| GitHub repository `Dandush03/ArborLM` | Existing | Source of truth; commits/PRs for changes |
| Prefer Apache-2.0 for code | Prior recommendation | Permissive reuse + explicit patent grant; verify LICENSE is committed |
| Astra for scientific reasoning/orchestration/validation; lower-tier coding model for implementation | **Mandatory owner preference** | Lower implementation cost, independent scientific review |

## 14. Non-goals and safety rails

- Do not promise a capability-equivalent 700B/1T model on a laptop.
- Do not optimize for artificial benchmarks at the cost of held-out utility.
- Do not imply a successful experiment that has not been run.
- Do not fetch large datasets or launch expensive cloud compute without explicit approval.
- Do not modify any production system, personal infrastructure or proprietary company resources.
- Do not copy substantial third-party model implementation or weights into the repo without license and attribution review.
- Do not consider a model's self-evaluation sufficient scientific validation.

## 15. Short abstract (proposal, NOT results)

**ArborLM** investigates whether a language model can learn a hierarchical organization of trainable neural memory such that only a small, semantically relevant and physically local subset of memory parameters is accessed for each prediction. We propose augmenting a compact causal transformer with learned multi-stage routing, sparse key-value retrieval and an optional I/O-aware objective. A staged evaluation compares dense, flat-memory, fixed-hierarchy and learned-hierarchy baselines first in resident memory and then with identical trained values placed on NVMe storage. We will measure language-model quality, activated computation, training cost, physical data movement and end-to-end latency under controlled settings. The initial aim is to determine whether learned memory organization creates a useful accuracy-versus-storage-I/O trade-off, and to identify failure modes before considering larger models.

---

**Research integrity:** Every forward-looking claim in this file is a hypothesis or engineering proposal unless it names a verifiable external reference. This file preserves the *starting rationale*, not evidence that ArborLM works.
