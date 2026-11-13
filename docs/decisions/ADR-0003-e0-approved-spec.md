# ADR-0003 — Executable E0 specification under human reviewer override

- Date: 2026-11-12
- Status: **SPEC APPROVED BY AUTHORIZED CODEX REVIEWER; NOT ASTRA REVIEWED**.
- Authority: In the current project chat, the human lead explicitly answered **“Authorize this model as scientific reviewer”** to the question requesting an exception to the Astra requirement. This permits this session's reviewer to resolve scientific specifications and review results. It does not establish Astra validation, grant publication approval, or authorize spending/deployment.
- Reviewer: current root Codex session; no claim of Astra identity. Implementation must be delegated to a lower-tier model under this brief.
- Reviewed material: ADR-0002 and source packet committed in `815f528`; canonical project policy/handoff/protocol. This document resolves A0–A8 for E0. Historical pending documents and the review-prompt snapshot remain historical records.
- Implementation/result review: **PENDING**. Human merge approval for new implementation: **PENDING**. The human explicitly authorized the earlier planning commit/push.

## Question and scope (A0, A8)

E0/G0 checks correctness and repeatability of a small CPU causal-language-model training loop. It does not test H1–H5, novelty, general reasoning, storage performance or architectural advantage. No external dataset, pretrained weights, GPU, cloud, hierarchy, locality objective or SSD engine belongs in this implementation.

Build the package, reproducibility framework, deterministic synthetic validation data, dense reference, tests, CLI and CI specified below. The implementer may choose function/module organization and serialization helpers; it may not change scientific settings, gates or data semantics. Stop and report ambiguity to the reviewer. A failed gate is preserved and investigated, never hidden through seed selection or relaxed tolerances.

## Data and targets (A1, A2)

- Vocabulary: integer IDs 0–15, identity tokenizer, no special/padding tokens. These are generated symbolic data, not a real-language corpus.
- Generator version `sha256-cycle8-v1`. For split `train`/`validation`, use seed 101/202, respectively. For increasing counter starting at zero, hash UTF-8 `arborlm-e0-v1:{seed}:{counter}`; take the first eight digest bytes modulo 16 as a motif. Reject an already accepted motif across either split. Generate train first (256 rows), then validation (64 rows). Cyclically repeat each motif to make a row of 33 IDs. No final test set in E0.
- Dataset is fixed before training. Disjoint full motifs/rows are required; shared vocabulary and shorter subsequences are expected, not leakage. Do not use validation data for generation, gradients or adaptation.
- Input is row positions 0:32 and targets 1:33, all 32 targets valid. No packing across rows; causal attention including the diagonal. Position IDs 0–31. Inputs must be int64 `[B,T]`, `1 <= T <= 32`; output float32 `[B,T,16]`. Reject invalid shape/dtype/IDs/context length.
- Example motif `[0,1,2,3,4,5,6,7]`: input `[0,1,...,7]` repeated four times; targets `[1,2,...,7,0]` repeated four times; mask is all ones.
- Persist arrays as deterministic JSON (compact separators, sorted keys for objects, UTF-8, trailing newline) and checksum their exact bytes; tokenizer/generator definitions have versions and checksums. Generated fixture provenance is this repository's code; record code license Apache-2.0 and no third-party dataset. No external license grant is inferred.

## Exact model (A3)

Two pre-LayerNorm transformer blocks; width 32, four heads of width 8; FFN width 64; learned absolute positional embeddings (32 positions); token embeddings (16 tokens). Each block:

1. `u = LayerNorm(h, eps=1e-5)`; affine scale/bias.
2. QKV = one biased linear 32→96, split heads; attention = softmax((QKᵀ)/sqrt(8) + upper-triangular -inf mask); biased output projection 32→32; add residual.
3. LayerNorm with same epsilon; biased linear 32→64; exact GELU (`approximate='none'`); biased linear 64→32; add residual.

Final affine LayerNorm; output logits use token embedding transpose, no output bias. No dropout, auxiliary objective, cache or stochastic layer. Initialize all embedding/linear matrices with normal mean 0, std 0.02 exactly once per unique parameter; linear/norm biases zero, norm scales one. Apply final LayerNorm to hidden states before tied output projection.

Expected unique parameters: embeddings `16*32 + 32*32 = 1536`; each block `4*32 + (3*32*32+3*32) + (32*32+32) + (2*32*64+64+32) = 8544`; final norm 64; total **18,688**. All are trainable. This is a calculation, to be asserted against implementation.

## Training/execution (A4)

- CPU float32, torch CPU RNG seed 42; seed Python random 42. No NumPy required. CPU threads 1, inter-op threads 1 (set once on process startup), deterministic algorithms enabled with errors (not warnings). No mixed precision, compile or fused attention.
- Train 32 optimizer steps, batch 8, accumulation 1: 8,192 valid target tokens. Deterministic cyclic row order, no shuffle/workers: batch at step s uses rows `(s*8+j)%256`, j=0..7. Thus one epoch in this E0. No partial batches.
- AdamW over all unique parameters, lr 0.003, betas (0.9,0.999), epsilon 1e-8, weight_decay 0, amsgrad false, foreach false, fused false; no scheduler. Global gradient norm clip 1.0 with error on non-finite gradients. Zero gradients with set_to_none true each step.
- Objective: mean next-token cross entropy over all B*T positions. Eval: sum cross entropy over all validation positions / total positions, batches of 8; eval at steps 0 and 32, no grad, restore training/eval mode afterward. Evaluation must not perturb training RNG/state. Log every train step, including pre-update loss and gradient norm.
- Checkpoint after step 16 and 32, after update and counter advancement, with RNG state for the next step. Resume regenerates/verifies the dataset, creates/loads model and optimizer, restores counters/data cursor, then restores RNG **after** initialization/loading. Resume destination is a new run linked to parent.
- Runtime caps: 300 seconds per train/eval process, 1,500 seconds for complete smoke workflow, 2 GiB process-tree RSS; parent watchdog polling at <=0.5 seconds kills a timed-out/over-limit child, preserves output and records resource failure. Dependency installation is outside timed experiment budget. Unsupported hardware/environment or exceeded cap is an explicit failure, not permission to shorten training.
- Reference Python 3.12; choose an available patch version and record it in `.python-version`. Declare and lock exact compatible PyTorch, pytest, ruff, mypy, psutil and build-tool releases. Implementation may resolve installable versions and platform markers, then freeze `uv.lock` before any runs; record installed versions and lock hash. macOS arm64 local and Linux CPU CI are separate numerical environments. No cross-platform bitwise guarantee.

## Metrics and tests (A5, A6)

NLL is natural-log nats per valid target token; perplexity = exp(NLL). Reject non-finite NLL; overflowed perplexity is null with reason, never silently infinity/zero. Training and evaluation token counts are separate. No required loss-decrease threshold: E0 establishes execution/state correctness, not useful learning. Publish observed before/after loss without selecting favorable runs.

Required G0 assertions:

| Test | Gate |
|---|---|
| Shape/dtype/config | Valid tensor contracts; reject unknown config fields, invalid token/range/dtype/context/shape and unsupported scientific settings |
| Causality | Alter tokens strictly after a selected position; logits at/before it unchanged at atol=1e-7, rtol=0 in eval mode |
| Target/loss fixture | Uniform logits produce NLL ln(16) within 1e-6; independent hand-calculable nonuniform and unequal-batch aggregation fixtures; exact shifted targets |
| Gradients/update | All intended parameter tensors have finite gradients on test batch, at least one parameter changes after step; total unique count 18,688 |
| Evaluation isolation | Model/optimizer tensors and Python/torch RNG states unchanged by evaluation; model mode restored |
| Data integrity | Repeat generation byte-identical; disjoint full rows/motifs, exact counts and checksum verification |
| Fresh repeat | Two fresh subprocess runs, same environment/config/seed, same per-step losses, final parameter/optimizer tensors and eval NLL: bitwise equality |
| Reload | Same checkpoint, fresh process eval NLL bitwise equal to saved evaluation |
| Resume | Train to step 16, new process resumes to 32; per-step suffix losses, final model/optimizer/RNG/cursor and eval equal uninterrupted run bitwise |
| Checkpoint integrity | Corrupt hash, unknown schema, mismatched config/data identity and missing state rejected; failure during staged save cannot expose incomplete final checkpoint |
| Run records | Unique run IDs, strict required metadata, retry preserves parent, failure/interruption status retained; source recovery and required artifacts present |

Parameter/optimizer tensor equality is distinct from serialized-file hash equality. Tests do not demand identical checkpoint binary hashes. Timestamps, IDs, wall time and RSS are not deterministic outputs.

Report total/trainable parameters exactly. Active-parameter estimate convention: unique scalar weights participating in the forward of one example, including its distinct token/position rows and all dense layers; token embedding is tied to full output projection, so all 512 token weights participate. For T=32 this is all 18,688; for T<32 subtract `(32-T)*32` unused positions. Label it a per-example estimate, not FLOPs or unique per-token weights. FLOPs, prefill/decode/TTFT and accelerator memory are deferred with explicit reasons. Required timing: train-loop seconds and full process wall seconds, separately; peak process-tree RSS sampled by watchdog, with sample interval and platform units. Physical NVMe and routing metrics are not applicable.

## Records/checkpoints (A7)

Use schema version 1, experiment_family E0, question_id G0, hypothesis null with reason `infrastructure validation only; does not test H1-H5`. This approved E0 specialization supersedes the misleading E0/H1 pairing in the protocol example without changing H1–H5.

Strict TOML config stores every scientific setting above; config loading rejects unknown keys and invalid values. CLI may override output paths and resume source only; tests may construct smaller fixtures explicitly labeled unit tests, not accepted E0 runs. Runtime values (hardware, package versions, timestamps, source SHA) are discovered, not hardcoded.

Each unique run directory contains resolved config, manifest, dataset/tokenizer manifests and checksums, `metrics.jsonl`, stdout/stderr, source identity/recovery, environment/installed packages, checkpoints/checksums, final result and terminal status. Running records may update atomically; raw events are append-only; finalized records are never replaced by retries. Interrupted children retain a watchdog terminal record; later invalidation/review is a separate append-only sidecar, preserving original artifacts. Generate collision-resistant IDs using UTC timestamp plus UUID.

Record full Git SHA, dirty status, `git diff HEAD` plus actual tracked/untracked source/config/test files required to recover the code (exclude secrets, `.venv`, caches, experiments, `.git`); archive bytes with checksum. Record exact argv/cwd, lock hash, seeds, hardware/OS/CPU/RAM, versions, time limits, actual tokens/steps and measured values with units/methods. Review fields must distinguish this authorized reviewer from Astra (`astra_spec_review: NOT_PERFORMED`, `astra_result_review: NOT_PERFORMED`, authorized spec reference, result-review PENDING, human merge/publication PENDING).

Checkpoint state: schema, model and optimizer, Python/torch RNG, completed step, next row cursor, train token counter, config/data/tokenizer hashes and spec reference. Save into a temporary sibling directory, flush/fsync contents, hash, write index, then atomically rename to a new immutable checkpoint directory. Never overwrite an existing checkpoint. Load only local trusted generated checkpoints, verify checksums before deserialization and validate identities/full schema/state; no permissive partial loading. Absent scheduler/router/memory/index/layout components must be explicitly not applicable, not fabricated.

Keep full artifacts locally in `experiments/` (gitignored); preserve compact raw per-step metrics, manifests/config and checksum indexes for review in version-controlled `results/` after review, excluding large binary checkpoints. CI uploads artifacts on success/failure, but CI expiration is not durable archival: local run evidence stays until an explicit human retention decision. No remote artifact service is authorized.

## Implementation deliverables and review

Create `pyproject.toml`, `.python-version`, `uv.lock`, `.gitignore`, source modules for config/data/model/train/eval/checkpoint/run/watchdog, `configs/e0_cpu_smoke.toml`, tests, README commands and CPU CI. CLI contracts: `python -m arborlm train --config ... --output-root ... [--stop-after 16] [--resume CHECKPOINT]`, `eval --checkpoint ... --output-root ...`, and `smoke --config ... --output-root ...`. `--stop-after` is solely for the registered interruption check; it cannot change the target 32-step config. Lint `uv run ruff check .`, typecheck `uv run mypy src/arborlm`, tests `uv run pytest`, smoke `uv run python -m arborlm smoke --config configs/e0_cpu_smoke.toml --output-root experiments`.

First implementer supplies exact dependency compatibility evidence, commands, output and raw artifacts. Root reviewer independently inspects code/data/objective/state logic and re-runs checks before accepting G0. Do not mark Astra validation. G0 acceptance permits a separately preregistered E1–E3 pilot, never establishes the core concept. Finite experiments may falsify specific configurations/hypotheses within their tested conditions; no finite E0 run proves/disproves all hierarchical-memory architectures.

References consulted for implementation constraints: [PyTorch deterministic algorithms](https://docs.pytorch.org/docs/stable/generated/torch.use_deterministic_algorithms.html) and [AdamW](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html). Exact installed version behavior still requires tests; documentation alone is not evidence of repeatability.
