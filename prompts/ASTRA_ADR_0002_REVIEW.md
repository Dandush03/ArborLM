# Astra review request — ADR-0002 / E0 implementation specification

The operator must select the actual Astra model/session before using this prompt. This text does not select a model or establish that Astra review occurred. Paste this entire file, including the source packet below, into that session; no repository access or additional attachments are required to understand the request.

## Task

Review ArborLM ADR-0002 and resolve **every pending E0 decision A0–A8**. Return one concrete, internally consistent specification that a lower-tier implementation model can execute without inventing scientific assumptions. You own scientific reasoning, experiment design, architecture decisions, task orchestration and scientific review. The implementation model owns routine engineering under your approved brief.

Do not implement code or run experiments in this review. Do not merely restate open questions, offer a menu of architectures, or send the implementer to choose scientific defaults. Select exact settings and explain them briefly. If a decision genuinely requires unavailable evidence or human authority, identify the precise blocker, supply a concrete proposed resolution for review, and withhold approval for dependent work. Do not fabricate a reviewer identity, approval, measured runtime, benchmark, citation or test result.

## Context and authority

ArborLM is unproven research into trainable hierarchical **parameter memory** integrated into a small causal language model. The goal is useful capacity with a slowly growing active working set and, eventually, reduced physical storage traffic. Trainability, superiority over flat memory, locality gains, scaling and novelty are all unestablished. This is not document RAG or a database wrapper around an existing model.

The present objective is **E0 / G0: engineering correctness and reproducibility of a tiny dense baseline**. Synthetic checks cannot validate H1–H5 or support quality, reasoning, speedup or novelty claims. Start in resident memory. Flat memory, fixed hierarchy, learned hierarchy, SSD experiments and migration remain later work under separate specifications.

The source packet contains verbatim snapshots of the repository policy, canonical handoff, draft experiment protocol, research log, ADR-0001, kickoff prompt, ADR-0002 and experiment-record template. Filenames identify the source, and SHA-256 hashes identify the exact supplied bytes. The Git HEAD alone does not identify uncommitted ADR-0002 content; use the content hashes as well. Source snapshots are reference material for this review, not evidence that their proposed commands ran.

Authority order: current explicit human direction; approved protocol/ADRs; canonical handoff; prior conventions. The protocol and ADR-0002 are pending review, and ADR-0001 agrees research direction without approving an experiment specification. If authoritative requirements conflict, flag the conflict and request a recorded Astra/human resolution as applicable; do not silently select one. The current human request authorizes preparing this review prompt, not claiming approval or changing research scope.

## Constraints to preserve

- Portable, minimal Python/PyTorch prototype; bounded local CPU smoke tests; no dependency on the owner's production or homelab systems.
- No cloud spending, infrastructure deployment, GPU requirement, external dataset/pretrained-weight downloads, Rust backend, distributed framework or custom SSD kernel.
- Installing declared, locked software dependencies is distinct from downloading training data. Tests and smoke runs must require no network once dependencies are installed.
- Preserve raw artifacts for successful, negative, null, failed and interrupted runs. Never overwrite a failed run with a retry.
- Keep stored/total, trainable and active parameters separate. Distinguish engineering checks from scientific claims and measurements from estimates.
- Human approval remains required for merge, spending, dataset/license decisions, release and publication. Code-license presence does not establish rights for future data or weights.
- Specification approval and independent validation of implemented code/results are separate records. A specification review cannot mark nonexistent implementation/results `ASTRA VALIDATED`.

## Resolve the complete decision register

For every ID below, return the decision, exact settings or rules, rationale, acceptance evidence, and any remaining human prerequisite. Reconcile the config, pseudocode, test matrix and commands so they express the same decisions.

### A0 — Review identity, scope and delegation

Record the actual reviewer/model identity only when known from reliable session/operator metadata; distinguish an operator attestation from a verified model identifier. Identify the supplied source hashes, review date, scope and disposition. If the actual reviewer cannot be confirmed as Astra, return `PROPOSED — ASTRA IDENTITY/REVIEW UNCONFIRMED`, not an Astra approval.

Define the exact brief delegated to a lower-tier implementation model, permitted routine engineering discretion, changes that require renewed scientific review, and the route for a separate post-implementation Astra review. Do not claim the operator has selected an implementation model unless there is evidence.

### A1 — Synthetic validation data

Specify a complete deterministic generator using mathematical rules or precise pseudocode: token alphabet, distribution/structure, lengths, sample counts, RNG algorithm, seeds and seed derivation. Choose train/validation/test roles and explicitly decide whether E0 needs a held-out final test set.

Specify the split unit, construction order, sampling with/without replacement, cross-split duplicate/overlap policy, within-split duplicate policy, serialization and checksum inputs. Make leakage checks compatible with the finite synthetic distribution; do not demand impossible uniqueness or call shared vocabulary leakage. Distinguish legitimate structural overlap from forbidden reuse. Define data provenance and the record needed for human license/rights review without asserting ungranted approval.

### A2 — Tokenizer, sequence construction and targets

Specify exact token-to-ID mapping, vocabulary size, reserved/special tokens or their explicit absence, context length, padding, packing, sequence/document boundaries, attention/loss masks and next-token shift. State which positions contribute to loss and how zero-valid-token inputs are handled. Provide one small fully worked input/target/mask example that follows the chosen generator and mapping.

### A3 — Dense causal baseline

Select exact layer count, hidden width, attention head count/head dimension, FFN width, activation, normalization location/type/epsilon, positional representation, residual structure, biases, initialization, dropout and embedding/output weight tying. Define attention scaling/masking, input/output tensor contracts and numerical dtype. Give forward-pass pseudocode precise enough to resolve ordering and boundary behavior.

Choose a genuinely tiny E0 configuration; the handoff's 20M–50M backbone range is a later planning target, not a smoke-test requirement. State an analytic parameter-count formula and expected count for the selected configuration, with shared parameters counted once. These are calculations, not measured implementation results.

### A4 — Optimization, execution and bounded resources

Specify objective/reduction, optimizer and all relevant hyperparameters, parameter groups and weight-decay exclusions, scheduler or explicit absence, clipping, batch size, accumulation, sampling/shuffling, final partial-batch behavior, total optimizer steps and corresponding valid-token budget, evaluation/checkpoint cadence, and evaluation batch size.

Provide explicit seeds for data, initialization/training and the repeat/resume checks. Decide RNG libraries, DataLoader workers, thread settings, deterministic algorithm flags, CPU dtype and any allowed numerical backend settings. Specify exactly when RNG state is captured/restored relative to model/optimizer/data-loader creation.

Define hard CPU wall-time and memory limits, timeout enforcement, supported reference environment and what happens on slower/unsupported hardware. Caps are proposed acceptance bounds until measured; do not promise a runtime or silently reduce training when a cap is exceeded. Bound all fresh/repeat/resume jobs and CI total, not just one training segment.

Decide the dependency policy: exact Python/package/tool versions when verifiable, or a tightly bounded, explicitly delegated compatibility-and-lock step before runs. Do not invent availability checks. Separate verified package facts from unverified candidates and specify what compatibility evidence the implementer must return. Scientific settings cannot be delegated through unspecified framework defaults.

### A5 — G0 tests and numerical gates

Define a test matrix with test ID, input/setup, procedure, compared outputs, exact assertion, absolute/relative tolerances, execution budget and artifact evidence. Cover:

1. Shape/dtype validation and rejection of invalid config/input.
2. Causal isolation under future-token perturbation.
3. Next-token alignment, boundaries, masking and token-weighted loss aggregation, including an independently calculable fixture.
4. Finite gradients, intended parameter updates and evaluation without parameter/optimizer updates or changes to subsequent training state.
5. Deterministic generation, split integrity and leakage checks.
6. Fresh-run repeatability in separate processes.
7. Checkpoint reload/evaluation equivalence.
8. Interrupted/resumed versus uninterrupted trajectory, including exact interruption point, state comparison and data cursor/order.
9. Corrupt/incomplete/incompatible checkpoint rejection and interrupted-save safety.
10. Manifest completeness, distinct run IDs, preserved failure/retry evidence and a bounded CPU integration workflow.

Explicitly decide whether loss reduction is required for the smoke test. If yes, preregister the comparison, threshold and checkpoint steps before any run; if no, explain what the sanity check establishes. Do not turn synthetic validation loss into a scientific generalization claim.

Distinguish same-process, same-environment and cross-platform guarantees. Choose whether comparisons require bitwise tensor equality or numerical tolerance; serialized checkpoint hashes need not be identical merely because tensors match. Set stopping/failure rules and prohibit post-hoc threshold relaxation or seed selection to manufacture a pass. Explain how exploratory troubleshooting remains recorded separately from preregistered acceptance.

### A6 — Metrics and accounting

Define NLL in explicit units, its valid-token denominator, perplexity conversion and overflow/non-finite handling. State whether batch losses are summed or averaged and how aggregate evaluation avoids weighting errors.

Specify total/trainable/active parameter counting, including tied tensors and accessed embedding rows versus full output projection. An active estimate must declare its convention and aggregation unit. Decide which FLOPs, inference timing and memory measurements are required for E0 and which may be deferred; document estimation formulas and timing boundaries for required metrics.

Separate startup, data preparation, training, evaluation and checkpoint overhead where relevant. State RSS/peak-memory measurement semantics and platform limitations. Explicitly mark router, lookup and physical NVMe metrics not applicable to E0. Never turn unmeasured values into zero. Timing observations from a smoke run cannot establish a comparative speed claim.

### A7 — Configuration, run records and checkpoints

Return a complete versioned config schema and resolved E0 config. Unknown/misspelled keys should fail clearly. Runtime-discovered values such as Git SHA and hardware may be generated, but chosen scientific settings cannot remain `TBD`, `REPLACE`, implicit or dependent on implementer judgment.

Resolve the protocol example's `experiment_family: E0` / `hypothesis: H1` mismatch explicitly: define E0's engineering question and exact schema/text amendments so it cannot be read as an H1 test. Preserve the canonical scientific H1–H5 definitions.

Provide a manifest schema/example, raw metric-event schema, directory layout, required artifacts, checkpoint schema and status transition rules. Include spec review references/hashes, full resolved config, command, working directory, Git SHA plus dirty-tree/source recovery, dependency lock/hash and actual installed versions, hardware, seeds, data/tokenizer/split hashes, consumed tokens/steps, optimizer state, runtime, raw metrics, checkpoint hashes, exceptions and stop reasons. Separate spec review, result review and human approval statuses.

Define atomic save/finalization, version compatibility checks, checksum coverage, RNG/data-order restoration, recovery after abrupt termination, append-only review/invalidation records and retry/parent-run linkage. Clarify mutable active-run files versus immutable finalized evidence. Define `null`/not-applicable/not-measured semantics. Reserve future schema evolution without implementing routers, keys, values, index or storage layout now.

Specify artifact retention beyond expiring CI uploads, with a minimal local durable procedure and any human-controlled publication/archive decisions left explicitly pending. No cloud service or paid storage is authorized.

### A8 — Acceptance and next phase

Define the exact evidence bundle and decision procedure for G0 acceptance, independent Astra result validation and human merge approval. Distinguish a failed correctness assertion, resource-cap failure, invalid run, supported exploratory troubleshooting and a completed run awaiting review.

State the strongest permissible claim after engineering checks pass and the additional evidence required for Astra validation. Commissioning an E1 specification is distinct from authorizing flat-memory implementation. Keep E1–E6 design choices deferred and list their future review gates without selecting their scientific settings now.

## Required response format

Return all of the following in one response, with no unresolved scientific placeholders in any work labeled approved:

1. **Review record and disposition:** actual reviewer evidence, reviewed content identifiers, date, approved/revise/blocked status, scope and any human prerequisites. State that implementation/result validation has not occurred.
2. **A0–A8 decision table:** one explicit resolution per ID with rationale and traceability to config/test sections. Expand subdecisions where needed; do not hide them in “standard defaults.”
3. **Complete implementation specification:** deterministic data-generation pseudocode, worked target example, model forward pseudocode, training/evaluation/resume algorithms and exact accounting rules.
4. **Resolved configuration:** one valid TOML or YAML block with every scientific/numerical setting, plus schema constraints. Include all auxiliary seeds and test settings in a named companion block if necessary.
5. **Artifact contracts:** directory tree, manifest/event/checkpoint schemas, concrete illustrative records clearly labeled as examples, and lifecycle/recovery rules. Do not present sample metric numbers as results.
6. **Acceptance matrix:** exact tests, thresholds/tolerances, budgets, evidence and stop rules. Map it to all eight G0 checks in ADR-0002.
7. **Ordered lower-tier work packages:** files/modules, function/CLI contracts, dependencies, acceptance criteria and safe engineering discretion. Include pinned/declarative dependencies, lint/typecheck, unit tests, CPU smoke CI and documentation. Keep the package small.
8. **Reproduction interface:** exact proposed install/lint/typecheck/test/train/eval/resume/smoke commands consistent with the chosen tooling and config paths. These are commands to implement/run later, not evidence they ran. Only artifact paths and runtime-generated identifiers may use documented placeholders.
9. **Repository amendments:** replacement text or an apply-ready diff for ADR-0002 and the applicable E0 protocol/template sections. Preserve history and pending result/human review status; do not retroactively label unreviewed results validated.
10. **Handoff and completeness audit:** check every A0–A8 item, declare allowed versus forbidden claims, list residual blockers and deferred E1–E6 work, and give the exact next instruction to the implementation model. If any scientific blocker remains, label the affected work unapproved and state precisely what evidence/decision is missing.

Before finalizing, cross-check vocabulary versus IDs; context versus shifts; width versus heads; tied weights versus parameter count; batch/steps versus token totals; evaluation denominator; checkpoint contents versus resume guarantees; tolerances versus determinism scope; CLI paths versus config; resource caps versus the complete test workflow; and review labels versus actual evidence. Resolve contradictions in your own specification before handing it off.

---

## Verbatim source packet

The following snapshots are included so this request stands alone. Review their contents; do not claim to have accessed the live repository if you only read this packet. If a later implementation sees different bytes, reconcile the changes and obtain renewed review for any scientific difference before proceeding.

Snapshot date: 2026-11-12 (America/Panama).
Base Git HEAD: `2555ed4f25a6a3f9897ce6857c6ecf70a90b2ea0`. This packet includes working-tree content.

### Source: AGENTS.md

SHA-256: `8da5bb85e261b790a45bd88edc000ca8911b8d77b5c7268e6771f45ee30bbea2`

<!-- BEGIN SOURCE: AGENTS.md -->

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

<!-- END SOURCE: AGENTS.md -->

### Source: docs/RESEARCH_HANDOFF.md

SHA-256: `a2851058d99426363d6d4ef79a20ac31f73eec1849fce57173bcf84fc9b58cb5`

<!-- BEGIN SOURCE: docs/RESEARCH_HANDOFF.md -->

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

<!-- END SOURCE: docs/RESEARCH_HANDOFF.md -->

### Source: docs/EXPERIMENT_PROTOCOL.md

SHA-256: `f70116006c66449e28ee79fd04c74b8285c5b1e3e568f9ab96a883c07dd61264`

<!-- BEGIN SOURCE: docs/EXPERIMENT_PROTOCOL.md -->

# ArborLM — Experiment Protocol (pre-registration draft)

**Status: DRAFT — PENDING ASTRA REVIEW.** This is a proposed methodology. No experiment listed here has been executed by ArborLM.

## 1. Objective and controlled questions

Primary: does learned hierarchical **parameter-memory** routing improve the quality / active-compute / physical-I/O frontier versus strong flat memory alternatives? See the canonical hypotheses H1–H5 in `RESEARCH_HANDOFF.md`.

Use separate experiment families so model-quality, retrieval implementation and storage speed are not conflated.

## 2. Experiment matrix (order matters)

| ID | Model | Memory layout | Question |
|---|---|---|---|
| E0 | Dense baseline | All resident | Is the training/eval infrastructure correct? |
| E1 | Dense + flat learned key-value memory | RAM | How much does generic memory help? |
| E2 | Dense + fixed-tree learned key-value memory | RAM | Does hierarchical selection help? |
| E3 | Dense + learned-router hierarchical memory | RAM | Is trainable routing helpful? |
| E4 | E3 + storage-locality objective | RAM + recorded block layout | Can training learn locality without quality loss? |
| E5 | **Same checkpoint as E3/E4** | NVMe; cold/warm/mixed caches | Real storage tax and I/O benefits |
| E6 | Teacher-distilled student variants | RAM first | Can existing-model behavior migrate? |

No E4/E5/E6 claims before E0–E3 are controlled, tested, and reviewed.

## 3. Baseline matching

- Freeze data partitions, tokenizer, next-token objective, text preprocessing and evaluation prompts before comparing alternatives.
- Report **total parameters**, **active parameters**, **trainable parameters**, FLOPs/token, memory values read/token, training tokens, tokens/sec and train wall-clock.
- Record extra router FLOPs and index work, not just backbone compute.
- Keep hyperparameter tuning budget comparable across alternatives; declare unavoidable deviations.
- Begin with deterministic synthetic data for validation, then choose a real openly licensed dataset before quality claims. Dataset decision must be an Astra-reviewed ADR with license and contamination assessment.
- Use at least three independent seeds for primary reported results if budget permits. Otherwise call findings exploratory; never claim statistical significance from single-run noise.

## 4. Metrics

**Quality:** held-out NLL, perplexity (tokenizer-dependent), chosen task accuracy, routing collapse metrics, generalization under shifted distributions.

**Inference:** prefill tokens/sec, decode tokens/sec, TTFT, per-output-token latency distribution, end-to-end wall-clock.

**Memory/I/O:** process RAM peak, accelerator memory, *physical disk bytes* read/token, number/sizes of read operations, page/block amplification, OS page-cache behavior, cache hit rates, slots/branches touched, routing entropy and load balance.

**Cost/reproducibility:** training elapsed time, energy/cost if measured, device/OS/compiler/driver versions, commit SHA, data SHA, dependency lock, seeds, checkpoint SHA, run command and failure notes.

## 5. Run manifest (minimum schema)

```yaml
run_id: EXP-YYYYMMDD-001
status: planned  # planned | running | failed | completed | invalidated
experiment_family: E0
hypothesis: H1
code_commit: REPLACE_WITH_GIT_SHA
astra_spec_review: PENDING
astra_result_review: PENDING
human_approval: PENDING
seed: 42
environment:
  os: REPLACE
  python: REPLACE
  torch: REPLACE
  accelerator: cpu
  cpu: REPLACE
  ram_gb: REPLACE
  storage_device: REPLACE
dataset:
  name: REPLACE
  source_revision: REPLACE
  license: REPLACE
  train_checksum: REPLACE
  eval_checksum: REPLACE
model:
  kind: dense_baseline
  parameters_total: null
  parameters_active_estimate: null
  checkpoint_sha256: null
train:
  tokens: null
  batch_size: null
  steps: null
  optimizer: null
  learning_rate: null
  command: REPLACE
metrics:
  eval_nll: null
  eval_ppl: null
  decode_tokens_per_second: null
  ttft_seconds: null
  physical_nvme_bytes_per_output_token: null
notes: []
```

Do not overwrite failed run records. Raw data belongs in immutable per-run artifacts, with derived dashboards separate. Use code in `src` and manifests in `experiments` after scaffold creation.

## 6. Correctness tests before benchmarking

- Autoregressive masking blocks future tokens.
- Exact shapes/dtypes, no inadvertent broadcasting.
- Memory lookup returns deterministic slot IDs for fixed inputs and snapshot.
- Sparse memory values selected by query receive expected gradients; router estimator is tested separately.
- Checkpoint resume restores optimizer, RNG, keys, values, router and index coherently.
- CPU train/eval smoke test under a bounded resource budget.
- Same checkpoint RAM-vs-NVMe retrieval emits matching values within dtype tolerance.
- No leakage from evaluation into training or adaptively updated inference memory.

## 7. Planned initial go/no-go

- **G0:** testable training/evaluation loop and repeatable manifests; no publication claim.
- **G1:** hierarchical model is trainable and quality is competitive with flat memory within an **Astra-approved numerical threshold set before evaluation**.
- **G2:** measured locality improves in a way that survives held-out prompts, rather than learning a single frequently accessed branch.
- **G3:** SSD experiment shows favorable throughput/I/O at matched checkpoints and measured cache regimes.

If a gate fails, record it, troubleshoot confounders and obtain Astra review before escalating complexity or compute spend.

## 8. Statistical reporting

Report mean, dispersion and raw per-seed results; confidence intervals only using an appropriate documented method. Avoid cherry-picking the best seed or best few prompts. State multiple comparisons and exploratory tuning. Publish full measurement scripts and raw artifacts when licenses/privacy permit.

<!-- END SOURCE: docs/EXPERIMENT_PROTOCOL.md -->

### Source: docs/RESEARCH_LOG.md

SHA-256: `517ecabac0eb81baa33386029608a0c4281d0e7141ebb37859d092bc4113bcaf`

<!-- BEGIN SOURCE: docs/RESEARCH_LOG.md -->

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

## 2026-11-12 — Phase 0 implementation proposal recorded

- Read the repository policy, canonical handoff, experiment protocol, research log, ADR-0001 and kickoff prompt in full; inspected the README, paper outline and experiment-record template.
- At inspection, HEAD was `2555ed4`; the working tree was clean and contained no model implementation, tests or experiment artifacts. `LICENSE` is tracked and contains Apache-2.0 text; the root handoff copy matches the canonical document.
- Added `docs/decisions/ADR-0002-phase0-plan.md`, marked **SPEC: PENDING ASTRA REVIEW**, consolidating the inherited E0/G0 roadmap, reproducibility requirements, proposed correctness checks, review decisions and deferred memory/storage work.
- This is a planning/documentation change only. No scientific settings were approved, no model code was written, and no tests, training or benchmarks were run. No result or Astra validation is claimed.
- Next dependency: actual Astra review of the specification and recorded decisions before dependent model/data implementation; lower-tier implementation and independent validation remain pending.

<!-- END SOURCE: docs/RESEARCH_LOG.md -->

### Source: docs/decisions/ADR-0001-research-direction.md

SHA-256: `8e7fe02fa921551f4a2c2301203cba2a6932564a169c3436f5a35d156739ba15`

<!-- BEGIN SOURCE: docs/decisions/ADR-0001-research-direction.md -->

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

<!-- END SOURCE: docs/decisions/ADR-0001-research-direction.md -->

### Source: prompts/CODEX_KICKOFF.md

SHA-256: `7dc5bc9af050f19551dd2ef63c0baf9703813c9844564ee5ccfb1959ddbfa5c3`

<!-- BEGIN SOURCE: prompts/CODEX_KICKOFF.md -->

# Codex kickoff task: initialize ArborLM correctly

Use the repository `https://github.com/Dandush03/ArborLM`.

Read `AGENTS.md`, `docs/RESEARCH_HANDOFF.md` and `docs/EXPERIMENT_PROTOCOL.md` **in full** before code changes. The research handoff is the canonical context from the originating discussions; do not reduce ArborLM to a vector DB + existing model, or claim unproven performance.

**Agent policy:** Astra handles scientific reasoning, specifications, orchestration, interpretation and validation. A lower-tier Codex coding model implements approved tasks and tests. `AGENTS.md` cannot automatically switch models. Mark pending Astra validation when it was not actually performed.

First task only:

1. Summarize the scientific objective, unproven assumptions and initial experimental controls; create an ADR-0002 phase-0 implementation specification marked `PENDING ASTRA REVIEW`.
2. Establish minimal Python/PyTorch source and test structure with exact pinned/declarative dependencies, lint/typecheck and CPU smoke-test commands.
3. After approval of ADR-0002, implement the smallest causal-transformer baseline and reproducible synthetic dataset. Do **not** begin the novel model layer or expensive training until scientific spec approval.
4. Log seeds, git SHA, environment, data checksums, loss metrics and checkpoint hash in a simple per-run manifest.
5. Add CI for unit tests and a tiny CPU training/resume/evaluation smoke test.
6. Keep all result claims honest and label unfinished work explicitly. Never make up benchmarks.
7. Open a PR containing the initial scaffold, exact test outputs, pending review items, and next tasks.

No cloud spend, production deployment, personal homelab dependence, huge model downloads or silent research-methodology changes.

<!-- END SOURCE: prompts/CODEX_KICKOFF.md -->

### Source: docs/decisions/ADR-0002-phase0-plan.md

SHA-256: `612dbb4ad05a8cbb42f6f2c1c97681752cc2010bfacd3327bed6a819f6ea4db2`

<!-- BEGIN SOURCE: docs/decisions/ADR-0002-phase0-plan.md -->

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

<!-- END SOURCE: docs/decisions/ADR-0002-phase0-plan.md -->

### Source: templates/EXPERIMENT_RECORD.md

SHA-256: `7873991afeaa7cffd4d089ce1e2f6845c1f4e9ac8c5031c7339cfa01fc02a4cb`

<!-- BEGIN SOURCE: templates/EXPERIMENT_RECORD.md -->

# Experiment: EXP-YYYYMMDD-001

- **Status:** planned / running / completed / failed / invalidated
- **Hypothesis:** H?
- **Registration date (before evaluation):**
- **Spec review:** PENDING ASTRA REVIEW
- **Implementation PR / commit:**
- **Result review:** PENDING ASTRA REVIEW
- **Human approval:** PENDING

## Pre-registered question, comparison and go/no-go threshold

_What evidence would support or refute the hypothesis? What confounders are anticipated?_

## Exact implementation, training and dataset information

- Architecture / memory dims / top-k / router:
- Dataset source, license, checksums, split, tokenizer:
- Training tokens, batch size, optimizer, seeds:
- Environment, versions, GPU/CPU, RAM, SSD:
- Full commands and config paths:
- Checkpoint SHA256 and artifacts location:

## Raw findings (attach logs; never invent results)

- Held-out loss / perplexity by seed:
- Train wall-clock / compute / active FLOPs:
- Prefill and decode tok/sec; TTFT; latency quantiles:
- Physical SSD reads, bytes/token, read amplification, cache status:
- Router selection distribution and entropy:
- Warnings, failures, unexpected behavior:

## Interpretation (Astra only)

**PENDING ASTRA VALIDATION**. No conclusions until independent review.

## Human signoff and follow-up

- Decision:
- Limitations:
- Reproduction steps:
- Next experiment:

<!-- END SOURCE: templates/EXPERIMENT_RECORD.md -->
