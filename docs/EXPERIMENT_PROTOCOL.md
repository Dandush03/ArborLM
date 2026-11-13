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
