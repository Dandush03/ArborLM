# ADR-0005 — Preregistered bounded RAM signal screen

- Date: 2026-11-12
- Status: **SPEC APPROVED BY AUTHORIZED CODEX REVIEWER; NOT ASTRA REVIEWED**.
- Authority: human's recorded reviewer exception in ADR-0003 and explicit authorization to implement with Sol/Luna; WikiText-2 local-use approval recorded in ADR-0004.
- Prerequisite satisfied locally: root independently ran Ruff, mypy, all 31 tests and E0 smoke on macOS arm64; all passed. Evidence: `experiments/review/root-e0/verification.log`, smoke `E0-20261113T021751395579Z-022ace6673384498a39ce74f2ddea257`. Linux CI remains unverified at registration.
- This specification is frozen before looking at any pilot training/evaluation result. It is a small exploratory screen of specified configurations, not proof/disproof of the general concept. Human publication/release approval and Astra validation have not occurred.

## Question, controls and limits

Can this particular sparse learned-router prototype train, avoid gross routing collapse, and meet the declared validation-loss gates against dense and flat controls within a small fixed token budget? Passing justifies stronger experiments; failure rejects promotion of this configuration at this budget. Neither outcome settles novelty, general reasoning, scaling or NVMe viability.

Implement six variants: `dense_small`, `dense_parameter_matched`, `flat`, `product_key`, `fixed_tree`, `learned_tree`. Use the same data, byte tokenizer, backbone width/depth, target-token budget, seed list and optimizer. Dense parameter-matched control has a larger FFN; product-key control uses factorized keys, so report its lower total key-parameter count. Training FLOPs and tuning quality are not matched; this screen cannot establish a Pareto improvement. No hyperparameter sweep or selection of favorable seeds is authorized.

The product-key control implements exact separable product-key lookup as a relevant structured-flat control; it is not a full reproduction of Lample et al. or later memory-layer methods. Modern multihead/value-transform/tuned baselines remain required before competitive-efficiency claims.

## Dataset and tokenization

Use only approved/pinned train and validation Parquet files from ADR-0004, verifying hashes first. Do not download or inspect test data. Retain publisher provenance and license record. Add an exact available PyArrow release to the dependency lock before parsing; record installed versions. This is the only new data-reading dependency required.

Byte tokenizer: UTF-8 bytes, IDs 0–255, no special or padding tokens. Preserve each Parquet `text` field exactly; encode UTF-8 with no normalization/added separator. Never concatenate across rows. For each row take nonoverlapping chunks of exactly 65 bytes at offsets 0,65,130,..., dropping a shorter remainder. Each chunk yields input bytes 0:64 and targets 1:65; all 64 targets valid, causal attention with diagonal. This is a byte-level task; its perplexity must not be compared with word/subword perplexities from publications.

Deduplicate exact 65-byte chunks within train and within validation. Exclude every validation chunk whose SHA-256 matches any full train candidate chunk, not merely the sampled train subset. Count and report exclusions; this exact-chunk check does not establish absence of near-duplicate/article contamination. For duplicate occurrences retain the occurrence with lexicographically smallest rank hash. Rank candidates by SHA-256 of UTF-8 `arborlm-pilot-v1:{split}:{row_index}:{byte_offset}` (ties resolved by row/offset). After exclusions, take first 4096 train and 512 validation chunks; fail if insufficient. Record selected row/offset IDs, bytes/checksums, discarded counts and dataset recipe/hash. Freeze this selection for all seeds/models. No final test set evaluation in this screen.

## Model contracts

Backbone follows ADR-0003 with vocabulary 256 and context 64; all other dimensions/normalization/activation/initialization stay unchanged. Small backbone unique parameter count: **27,392**. Parameter-matched dense uses FFN width **1,588** in both blocks, otherwise identical: **225,512** parameters. Memory variants retain FFN width 64 and insert one additive memory module after block 1 (zero-based index 0), before block 2. Final tied output projection remains unchanged.

Common memory: 4,096 stable slot IDs 0–4095, key dimension 16, value dimension 32, exactly 8 selected values per query. `q = normalize(Wq*h, eps=1e-8)`, biasless Wq 32→16. Each key is normalized at lookup with the same epsilon. Scores are cosine dot products divided by temperature **0.2**. Select by descending score, breaking exact ties by ascending stable slot ID. `m = sum(softmax(selected_scores)*selected_values)`. Fuse `h + sigmoid(g)*Wo*m`, biasless Wo 32→32, scalar trainable gate g initialized to **-2.0**. Memory matrices init normal(0,0.02). No additional LayerNorm, dropout, regularization, locality loss, cache or FFN replacement.

- `flat`: full independent 4096×16 keys, exact exhaustive top-8; 4096×32 values.
- `product_key`: independent left/right key matrices 64×8 each. Normalize each subkey, concatenate a left and right subkey and divide by sqrt(2); full slot key ID `left*64+right`. Its score is `(q_left·normalized_left + q_right·normalized_right)/(sqrt(2)*0.2)`. For exact top-8, take top-8 left scores and top-8 right scores (ties by subkey ID), enumerate their 64 Cartesian candidates, then stable top-8 full-slot scores. Validate against exhaustive 4096-key scoring, including ties. Same values/Wq/Wo/gate as flat.
- `fixed_tree` / `learned_tree`: 16 balanced fixed partitions, branch j owns slots `[256*j,256*(j+1))`. Router matrix R is 16×16. Initialize R normal(0,0.02), normalize rows at lookup. Route scores `r=q*normalize(R)^T/0.2`. Visit top-2 branches (ties by ascending branch ID), score only their 512 independent keys, and form slot score `q·normalized_key/0.2 + log_softmax(r)[branch]`. Select top-8 slots globally among candidates, then fuse as above. R is a fixed buffer for fixed_tree and a trainable parameter for learned_tree; all other math/data/initial values match.

Router learning uses ordinary gradients through selected scores and parameter values, **not** through discrete top-k indices. No straight-through/Gumbel estimator or warm-up. Only relative selected-branch scores can receive useful router signal; if all selected values lie in one branch, the branch prior can cancel in the final softmax. Log router gradient norms and movement; failure/collapse is an outcome, not a reason to silently change the estimator. Branch partitions/slot IDs never change.

Expected trainable parameter counts: flat and fixed_tree **225,537**; learned_tree **225,793**; product_key **161,025**. Fixed router adds 256 stored nontrainable buffer scalars, reported separately. Verify all counts in tests.

Initialization fairness: for each seed, construct/init the backbone first with that seed. Use independent CPU generators for memory components: keys seed+1000, values seed+2000, Wq seed+3000, Wo seed+4000, router seed+5000; product subkeys consume the key generator in left/right order. Do not let model construction order change shared backbone/memory initialization. Dense parameter-matched weights necessarily differ in shape; report this. Model seeds **42,43,44**. All three seeds run for every variant.

## Training, measurements and preservation

Same deterministic CPU float32, one intra/inter-op thread, optimizer settings and clipping as E0, including lr 0.003 and zero weight decay. Batch 8, context 64, 256 optimizer steps, no accumulation/shuffle: cyclic fixed ranked training rows `(step*8+j)%4096`. Exactly **131,072 valid targets per model/seed**; all 18 runs total 2,359,296 train targets. No adaptive early stopping except correctness/resource failure. Evaluate all 512 validation rows (32,768 targets) at step 0 and 256 only; log every training step; save at steps 128/256. No retuning after validation results.

Run order: seeds ascending; within each seed variants in the order listed above. Determinism is within one environment; no equality across different model variants/seeds is expected. Per-run cap 300 seconds and 2 GiB sampled process-tree RSS; full suite cap 1,800 seconds. Abort suite on resource failure or non-finite/model-integrity failure, preserve partial runs and label unexecuted cells. Dependencies/downloads outside experiment clock. No GPU/cloud or data beyond the pinned small corpus.

Use versioned pilot config/schema distinct from E0; reject unknown keys/settings. Extend shared orchestration only where defaults preserve E0 behavior; all E0 tests and smoke must still pass. Pilot records must identify family `P1_SCREEN` and this spec/hash, not falsely say E0/G0/H1 confirmed. Record the human data approval and reviewer override, never Astra validation.

Preserve all E0-level provenance/config/environment/source recovery/commands/status/raw metrics. Checkpoint model state must atomically include backbone, query/output adapters, gate, keys/values or subkeys, router/buffers and unchanged slot/partition definitions, optimizer, RNG and step/data cursor. Give schema/component IDs; reject incompatible variant/config/data/spec states. Store all binary checkpoints locally and compact raw metrics/manifests in review artifacts. No dataset/checkpoint publication.

Metrics: token-weighted validation NLL (nats/byte) and byte perplexity, training loss, pre-clip norm, parameter counts, wall time and RSS. Log analytical per-query lookup work separately: flat 4096 full-key dot products; product_key 128 eight-dimensional subkey dot products plus 64 scalar candidate sums; tree 16 router dot products plus 512 full-key dot products. Report key/value elements logically requested (8×32 value elements/query), not physical memory/disk traffic or measured FLOPs. Do not equate these heterogeneous work units or call them a speedup.

For each memory model report unique slots visited, selected-slot counts and concentration; for tree models also top-1 router branch counts, visited-branch counts and selected-value branch counts on the full validation set. Report normalized router entropy, hottest top-1 branch fraction, and count of branches with nonzero top-1 selection. Learned router: training gradient norm per step and final L2 movement from initialization. Label dense routing fields not applicable. No decode/TTFT/SSD or reasoning metric is inferred.

## Preregistered screen gates and interpretation

First correctness gates: exact lookup references (including tie order), selected-value gradients with no gradients on unselected value rows, router conditional gradients on a constructed multi-branch fixture, fixed-router immutability, parameter counts, all-branches/zero-prior tree equivalence to flat on a unit fixture, finite losses/gradients, coherent checkpoint restore and same-checkpoint deterministic validation. Unit-test fixture overrides do not change registered run settings.

Promote this **particular learned-tree configuration** to a stronger study only if all are true:

1. All 18 cells complete with finite results and correct token counts; all correctness tests pass.
2. Learned-tree final validation NLL is below its own initial NLL for each seed; router gradient is nonzero on at least one training step and router parameters change in each seed.
3. Mean learned-tree NLL is no more than **0.02 nats/byte** worse than the lower mean of flat/product_key, and no more than 0.02 worse than parameter-matched dense; it improves on small dense by at least **0.01 nats/byte** on average.
4. In each learned-tree run, at least 4 of 16 branches have nonzero top-1 selections on validation, and the hottest branch holds strictly less than **90%** of top-1 selections.

Report raw per-seed values, means, sample standard deviations and paired deltas for every control. Thresholds are screening tolerances, not significance tests or universal quality equivalence. No p-value/significance claim from these three seeds. Multiple controls and limited token budget must be explicit. Fixed-tree comparison isolates this router update choice as far as possible; a failure to improve it is a reported null result even if other gates pass.

Failure means **do not scale/promote this configuration under this protocol**. Diagnose whether the issue is implementation, undertraining, unsuitable task, routing collapse or lack of benefit; any changed settings require a new preregistration and retain this result. Success means **bounded preliminary support worth investigating**, not concept proven. General concept, novelty, matched-compute frontier, larger models and physical-I/O claims remain unresolved.

## Pre-run numerical and measurement clarifications

Before pilot implementation/training, the reviewer approves reporting both unique selected and candidate slots, hottest selected-slot fraction, normalized entropy of empirical top-1 counts and mean normalized per-query router entropy. These distinguish selection concentration from router-distribution uncertainty.

Float32 product-key pair addition/scaling can collapse near-boundary score differences into ties. To preserve the stable exhaustive-reference selection, if either 8th/9th subscore gap is <= **1e-5** on unscaled `q_half dot normalized_subkey` scores (bounded by [-1,1]), use exhaustive 4096 separable pair scores for that query. Otherwise use the 64-candidate path. Record actual candidate counts and fallback fraction; do not claim unconditional 64-candidate work. Validate all-zero/exact ties and adversarial near-boundary examples against full float32 separable scoring. This conservative fallback trades extra work for the registered deterministic tie convention; it was specified before pilot outcomes.
