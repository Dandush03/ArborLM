# ADR-0010 — P5: Hierarchical Memory Architecture Ablation

- Date: 2026-11-13 (America/Panama).
- Status: **SPEC APPROVED BY HUMAN RESEARCH LEAD AND HUMAN-AUTHORIZED CODEX SCIENTIFIC REVIEWER. IMPLEMENTATION AUTHORIZED; TRAINING REQUIRES ACCEPTED PREFLIGHT AND FREEZE.**
- Prepared and scientifically reviewed by root Codex under the documented human-authorized reviewer exception. **Astra spec/result review: NOT_PERFORMED.** Human approval and the review disposition are recorded below; this authorizes implementation followed by independently accepted preflight and freeze before execution.
- Scope: fixed-size, local CPU/RAM comparison of existing flat, fixed-tree and learned-tree mathematics on frozen backbones. No SSD, new capacity, topology restructuring, new objective, deployment or additional architectural feature. P1–P4 and every failed gate remain unchanged.
- Read before drafting: AGENTS, canonical handoff, experiment protocol, research log, ADR-0005–0009, P1/P2 finalized review records in their result READMEs, P3/P4 authorized scientific reviews, P4 implementation, and P4 preflight/artifact audits. The handoff's historical proposed phases are not automatic authorization; the current human instruction defines P5 as this ablation.

## 1. Question, evidence and competing explanations

Does the existing hierarchical organization retain useful predictive quality at lower retrieval work than exhaustive flat memory? Does training the router improve on the same initially identical router held fixed?

P1 failed promotion; P2 failed its dependence criteria; P3 failed its two dependence criteria while passing its quality guard. P4 passed capacity and slot-association criteria, with mean memory gain 0.021988695 nats/byte, but dense adapters were better in every pair and P4's composite failed. These findings motivate this separate experiment; they are not changed by any P5 outcome. The original quality panels cannot be used to select P5 configurations.

Competing explanations are fixed before outcomes:

1. The trained router learns useful selection/prior weighting and improves prediction relative to a frozen random router.
2. Fixed routing is sufficient; keys, values and query/output projections adapt around it. A fixed router does **not** mean fixed token-to-branch assignments: the query projection still trains.
3. Global flat retrieval is stronger because hierarchy excludes useful candidates or introduces an unhelpful branch prior.
4. Hierarchy offers a useful quality versus comparison-work trade-off, even with a small NLL penalty.
5. Fewer dot products fail to reduce wall time because gathers, repeated normalization, sorting, allocation or poor batching dominate. Analytical access counts do not imply physical RAM or SSD savings.
6. Generic added capacity explains the gains; dense adapters remain the stronger reference. Shared data, initialization factors, historical backbone representations and limited optimization also constrain interpretation.

The learned-versus-fixed treatment includes training 256 router scalars and its effects on subsequent optimization, including global clipping. It cannot separate learned candidate selection from learned branch-prior weighting. Flat-versus-tree compares the existing systems, which differ in both candidate restriction and branch prior; it is not a pure topology-only intervention. No significance, novelty, semantic-storage or universal efficiency claim follows from this screen.

## 2. Exact parents and proposed matrix

Use **all nine P4 baseline `checkpoint-0` snapshots**, B=101/102/103 crossed with O=301/302/303, from:

`experiments/P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd`

Compact baseline bundles are `results/p4-2026-11-12/b{B}-o{O}-baseline/`. Their frozen tensors are the nine P3 step-1024 disabled-throughout controls; P4 added no training to those backbones. P4 source freeze is `812b3fd02d81124b0665cc96d1364a32e40d403d`, archive SHA-256 `18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0`. Preserve upstream P3 linkage and its historical 1,024 updates/524,288 targets separately.

Before implementation acceptance, independently verify all nine mappings, original P4 state/index hashes, committed compact records, P4 identities, P3 provenance and exact frozen tensor digests. No parent replacement, favorable checkpoint selection or substituted retraining. A missing/mismatched parent blocks execution.

| Variant | Parents | Addition seeds | Cells | New updates/cell |
|---|---:|---|---:|---:|
| Frozen backbone baseline | 9 | none; execution seed 0 | 9 | 0 |
| A: flat memory | 9 | 501, 502, 503 | 27 | 512 |
| B: fixed-tree memory | 9 | 501, 502, 503 | 27 | 512 |
| C: learned-tree memory | 9 | 501, 502, 503 | 27 | 512 |
| D: P4 dense-adapter architecture | 9 | 501, 502, 503 | 27 | 512 |

Total **117 cells, 108 trained additions**, including 81 memory cells. Seeds 501–503 are new predetermined initialization labels, not chosen by observed loss. Use the same seed for shared components across A/B/C, and the same three labels for D. Nine baselines are reused in paired arithmetic, not counted as 27 independent controls.

**Dense-reference decision proposed for approval:** retrain the unchanged P4 dense-adapter architecture under P5 seeds, data/order/update budget and evaluation conditions. Do not import its trained P4 addition weights or old-panel losses. This spends 27 fresh training cells to avoid mixing histories or panels. The original P4 dense outcomes remain preserved historical evidence. Likewise, initialize all P5 memory additions afresh; no trained P4 memory is reused. Only the nine frozen baseline backbones are reused, identically for every architecture.

Execution order: B ascending, O ascending; baseline first for each parent, then seeds ascending. Define `i=(B-101)*9+(O-301)*3+(seed-501)` in 0..26. Within each seed, rotate `[flat, fixed_tree, learned_tree, dense]` left by `i mod 4`. Record the complete order before execution. Component RNG isolation makes this scheduling rotation irrelevant to training tensors; it reduces consistent architecture-position bias in descriptive training times. No scientific early stopping or winner selection.

## 3. Unchanged mathematics and explicit parameter accounting

Backbone: exact P4 frozen token/tied-output weights, positions, two transformer blocks, final LayerNorm and causal mask, **27,392 unique parameters**. Copy/restore original tensor bytes without changing normalization, activation, dtype or insertion point. Every parameter has `requires_grad=False`, `grad=None`, and is excluded from AdamW. Buffers remain immutable. Gradients must flow through the frozen suffix into the addition; do not detach its output or disable suffix autograd during training.

All additions enter after block 0, before block 1. Memory uses the existing `pilot_model.Memory` math: 4,096 independent key rows of dimension 16, values of dimension 32, biasless query 32→16, biasless output 32→32, scalar gate initially −2.0. Query/key normalization epsilon 1e-8; cosine-score temperature 0.2; exactly eight selected values; softmax over selected scores; gated additive fusion. Stable descending score/ascending slot-ID ties. No new normalization, cache, estimator, warm-up, loss or regularization.

- **A / flat:** score all 4,096 normalized keys; exact global top-8. No router, branch prior or partition restriction.
- **B / fixed_tree:** existing 16 partitions of 256 slots; 16×16 normalized router, top-2 branches, score their 512 keys, add the existing `log_softmax(route_scores)[branch]` prior, then global top-8 among candidates. Router is a persistent, nontrainable buffer. It is initialized normally and must remain byte-identical through training/restoration.
- **C / learned_tree:** identical structure, math and initialization to B; the router is a trainable parameter. Ordinary gradients through selected scores/values, not discrete indices. No straight-through estimator. Record gradient norms and movement, including zero gradients; zero useful learning is a possible scientific outcome.
- **D / dense:** unchanged P4 `h + sigmoid(g)*W2*GELU(W1*h)`, exact GELU, W1=(3100,32), W2=(32,3100), no biases/dropout/normalization, scalar g=−2.0.

For memory seed s, independent CPU generators use s+1000 for keys, +2000 values, +3000 query, +4000 output, +5000 router; matrix entries normal(0,0.02). Dense uses s+3000 for W1 and +4000 for W2, same normal distribution and gate. A/B/C shared components must start bitwise equal for each s and across parents; B/C router tensors must also match. Dense shapes/functions and output variance differ and are not claimed matched. Construction/evaluation may not perturb training RNG.

| Variant | Trainable addition | Frozen backbone | Total parameters | Extra router-buffer scalars | Addition scalar state including router buffer |
|---|---:|---:|---:|---:|---:|
| Baseline | 0 | 27,392 | 27,392 | 0 | 0 |
| Flat | 198,145 | 27,392 | 225,537 | 0 | 198,145 |
| Fixed tree | 198,145 | 27,392 | 225,537 | 256 | 198,401 |
| Learned tree | 198,401 | 27,392 | 225,793 | 0 | 198,401 |
| Dense adapter | 198,401 | 27,392 | 225,793 | 0 | 198,401 |

Common memory addition count is `4096*16 + 4096*32 + 16*32 + 32*32 + 1 = 198145`. The learned router adds 256 trainable scalars; fixed tree stores the same 256 as a buffer. No dummy parameters or size changes. Dense matches C exactly, while exceeding A/B trainable count by 256. Report parameter and buffer bytes separately, including other backbone buffers and optimizer states; the table is not total process memory. No claim of matched FLOPs or active compute.

## 4. Data and fixed training budget

Use only the approved pinned local WikiText-2 train/validation files and original UTF-8 byte tokenizer/65-byte chunk recipe. Preserve row boundaries, rank hashes, deduplication and exclusion against **all** train candidates. No download or test split. Retain attribution and unresolved publisher card license discrepancy (CC-BY-SA-3.0/GFDL front matter versus CC-BY-SA-4.0 body). Local-use approval does not authorize redistribution of corpus or weights.

Reuse original 4,096 ranked training chunks with SHA-256 `1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07`; train only the first 2,048. Reuse each parent's exact O permutation, generated by CPU `randperm(2048)` with seed O, twice without reshuffling. At step s=1..512 use offsets `8*((s-1) mod 256)` through the next seven rows. Same examples and batch order for every architecture; these are examples the frozen backbone has already seen.

Proposed sole scientific validation panel: eligible ranks **2048..2559**, zero-based, under the existing recipe. P4 records 16,407 eligible validation chunks, so this interval is available according to prior metadata; actual reconstruction/disjointness remains an engineering prerequisite. Reconstruct all first 2,560 selected IDs independently from raw Parquet before any P5 model evaluation. Verify the old panel hashes:

| Panel | Ranks | SHA-256 |
|---|---|---|
| P1 | 0..511 | `2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200` |
| P2 | 512..1023 | `8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2` |
| P3 | 1024..1535 | `a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0` |
| P4 | 1536..2047 | `4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f` |

Verify zero exact overlap with all four panels and the full training candidate pool, and check other experiment records for prior use of the proposed interval. If previously used or insufficient, stop for a pre-outcome amendment; do not silently advance ranks. Save the new bytes/hash/IDs before source/config/data freeze. The hash is a derived preflight artifact, not a freely chosen setting. Same-corpus, shared-article and near-duplicate limitations remain.

CPU float32, deterministic algorithms, one intra/inter-op thread, matched parent numerical environment, unchanged locked dependencies. Baseline execution RNG seed 0; addition execution seed s. Fresh AdamW over only named trainable addition parameters: lr=.003, betas=(.9,.999), eps=1e-8, weight_decay=0, amsgrad/foreach/fused=False; global norm clip 1.0, error on nonfinite, zero_grad(set_to_none=True). No scheduler, accumulation, mixed precision or compiled kernels. B's router is excluded from optimizer and clipping; A has no router. No parent optimizer moments are imported.

Batch 8, context 64, 512 targets/update, exactly **512 updates and 262,144 new targets per trained cell**. Total **55,296 updates and 28,311,552 new targets**. Baselines train zero targets. Save steps **0,256,512** for additions and 0 for baselines: **333 P5 snapshots**. Step 512 is the sole primary endpoint; there is no step-256 validation or selection.

## 5. Quality evaluations and interventions

All scientific NLL evaluations use all 512 new-panel chunks in batches of eight, 32,768 targets, unchanged token-weighted aggregation. Evaluate initial step 0 and final step 512 for additions; baseline reference only at 0. No gradients or state/RNG/mode changes. Report initial and final NLL, nats/byte, and byte perplexity; no comparison with word/subword perplexities.

Each baseline also gets exactly one **old P4-panel integrity-only evaluation**, requiring bitwise equality to its recorded P4 baseline NLL in the matched environment. Exclude these nine checks from P5 scientific metrics. All cross-variant quality contrasts use the same new P5 panel.

Restore the same final snapshot afresh before each intervention, preserving original checkpoint bytes/index:

1. Enabled replay for every cell: bitwise equality to its new-panel reference.
2. Disabled addition for every trained cell: bitwise equality to the paired frozen baseline. Check full-logit equality on synthetic fixtures as well.
3. Memory only: globally permute all 4,096 value rows with CPU generator `60000+i`, identical permutation IDs across A/B/C for a paired cell.
4. Memory only: paired key/value permutation. **Flat uses one global `randperm(4096)`** with seed `70000+i`. **Both trees use 16 consecutive `randperm(256)` draws** with seed `70000+i`, with branch offsets, preserving branch membership. This is an invariance control, not an architecture-effect contrast; the flat and tree permutation domains intentionally differ. Record IDs/hashes. NLL must match the reference at absolute 1e-6, relative zero.

Stable IDs retain the existing row-index semantics. Joint permutation can change exact-tie ordering when different values have tied scores; do not claim unconditional invariance under such ties. Synthetic tests must distinguish correct stable tie handling from pair-permutation invariance on fixtures without selection-boundary ties. A real-data joint-control failure stops the study for engineering review, preserving outputs; do not relax tolerance, choose a different permutation or count it as scientific failure/success.

Exactly **612 scientific evaluations**: 81 memory cells×6 (initial, final, replay, disabled, shuffled, joint) + 27 dense×4 (initial, final, replay, disabled) + 9 baselines×2 (reference, replay). Exactly **20,054,016 scientific evaluation targets**, separate from 294,912 targets in nine old-panel integrity checks. Every evaluation records zero training targets. Timing/shape probes below use training inputs without labels or NLL and are accounted separately.

## 6. Four distinct work/accounting measures

Do not collapse these measures into one speedup:

| Per memory query | Flat | Either tree |
|---|---:|---:|
| Full 16-dimensional key dot products | 4,096 | 512 |
| 16-dimensional router dot products | 0 | 16 |
| Logical candidate-key scalar elements | 65,536 | 8,192 |
| Logical router scalar elements | 0 | 256 |
| Selected value scalar elements | 256 | 256 |
| Common query/output/gate scalars | 1,537 | 1,537 |
| Distinct addition-state scalars logically consulted/query | 67,329 | 10,241 |

1. **Analytical score work:** predicted `(512+16)/4096 = .12890625` ratio, or 87.109375% fewer equal-dimensional score dot products including router. Value retrieval count does not shrink. This is an algebraic property, not an empirical discovery or total-FLOPs reduction.
2. **Observed execution work:** independently trace operand shapes/call counts for actual matmul/bmm, normalization, candidate gather, top-k/tie-sort and selected-value gather on the fixed profiling inputs. Confirm query/candidate/selected counts against returned lookup IDs and reference fixtures. Preserve raw traces; constants merely copied into manifests do not qualify as measured work. Report normalization/sorting/materialization separately. Existing flat code normalizes 4,096 keys once per batch and uses matrix multiplication; tree code normalizes 512 gathered key rows separately per query. At 512 queries, this is 65,536 versus 4,194,304 key-normalization input elements per call, before router normalization. Do not hide this countervailing cost or describe all computation as reduced.
3. **Logical consulted-state fraction:** addition-only numerator above divided by addition parameter-plus-router-buffer state: flat `67329/198145 ≈33.9797%`, either tree `10241/198401 ≈5.1618%`, dense 100%. Fixed tree's denominator includes its real router buffer, not dummy parameters. Also report trainable-only fractions: fixed `(10241-256)/198145 ≈5.0392%`; learned `10241/198401`; flat unchanged. Baseline addition fraction is N/A. These per-query logical estimates are not physical bytes, batch-wide unique traffic, resident RAM savings or whole-model active-parameter fractions. Report batch/panel unions separately; all backbone and addition tensors remain resident.
4. **Measured wall time and RSS:** separate fixed-workload timing below, training-loop time, supervised cell wall time, and sampled process-tree RSS. Training times include unequal backward work and possible logging/snapshot overhead; report their boundaries. Physical traffic, FLOPs, energy, cache misses, SSD reads, decode latency and generation throughput are **not measured**.

On the full new panel preserve every slot's selected count, candidate union, unique selected slots, hottest selected-slot share, empirical normalized selected-slot entropy and effective selected-slot count `exp(entropy)`. Trees additionally report top-1/visited/selected-value branch counts, empirical top-1 entropy, mean query-router entropy, hottest branch share and nonzero top-1 branches. Flat branch fields are N/A. Record gate trajectories and final router movement/gradient counts. Do not invent a post-outcome collapse threshold or treat nonzero gradients as useful routing.

## 7. Prespecified RAM latency protocol

Timing runs only after the quality stage is complete and frozen, for **all** final models regardless of quality flags. No training, new checkpoints, quality selection or tuning. Load snapshots afresh, verify immutable parent/model/buffer/RNG/checkpoint identities before and after. Time in isolated sequential workers on the same CPU environment, no parallel training or other intentional compute load. Pause our GitHub pushes/audits during timed workers and report those external pauses separately. Uncontrolled OS activity, thermal state and CPU scheduling remain limitations.

Use inputs only from ranked training chunks 0..31, never the new validation panel. Two workloads: **primary B=8,T=64** (four batches, rows 0..7, 8..15, 16..23, 24..31), and **secondary B=1,T=64** (rows 0,8,16,24). These are full fixed-context forwards without a KV cache, not autoregressive decode. Freeze input bytes/order/hash. No cache flushing or claims about cold caches.

Three explicit scopes for memory, two for dense, one for baseline:

- `lookup_score_select`: existing `Memory.lookup(q)` on normalized projected queries prepared outside timing. Includes key/router normalization, scoring, branch choice and slot selection; excludes value gathering, query projection and fusion. Label this boundary explicitly.
- `addition_forward`: the full existing addition on insertion-point h, including query projection, lookup, selected-value read/weighting, output and gate/fusion; dense includes its full adapter. h is computed from the frozen backbone outside timing solely to isolate this scope.
- `model_forward`: unchanged full forward from input IDs through final logits, including normal forward validation, additions and returned lookup metadata. No loss, retrieval-statistics tracker, optimizer, disk I/O or logging inside the timed interval.

Precomputed q/h are used only for isolated timing, not quality evaluation or training. No caching of normalized keys/router, new kernel, compiled path or model refactor is allowed. Verify timed functions equal the registered math and preserve state on synthetic fixtures. Measure with `perf_counter_ns`, CPU inference mode, eval mode, single thread. Disable Python GC only during each timing block and restore its original setting; do not subtract empty-loop overhead.

For each parent/seed, hold all four final additions in one benchmark worker to allow paired interleaving. Workloads in the listed order; scopes in the listed order, omitting unavailable scopes. For each workload/scope run **8 rounds**, rotating the applicable variant list left by `(i+round) mod list_length`. For each model block, run **2 untimed warmups followed by 10 individually timed calls**, using batch index `(round*10+j) mod 4` for timed j=0..9 and `(round*2+j) mod 4` for warmup j=0..1. Retain all 80 durations and 8 round medians. No outlier deletion, adaptive repetition or best-time selection. Baseline is benchmarked once per parent with the same workload/round/call counts, in a separate baseline worker before that parent's seed groups.

This is 46,656 memory, 10,368 dense and 1,728 baseline scope calls, **58,752 total** (including warmups); shape traces, input-feature preparation and integrity checks are separately counted untimed calls. Timed calls contain no target labels/NLL and do not add to the 612 scientific quality evaluations. Record all preparation/probe counts, wall time and transient allocation/RSS observations.

For every model/scope/workload report median, nearest-rank p10/p90/p95, minimum/maximum, all round medians and raw nanoseconds; summaries over matched models do not make repeated timings independent model replications. A measurement is usable for a registered latency decision only if all raw durations are positive, median≥100 times the reported monotonic-clock resolution and `max(round_medians)/min(round_medians)≤1.25`. All 27 paired models in the relevant comparison/scope must pass. Otherwise the corresponding latency flag is **INCONCLUSIVE**, with noisy measurements retained, no replacement run or adaptive budget. The secondary B=1 workload is reported in full and cannot replace a failed/inconclusive primary workload.

## 8. Prespecified effects, flags and interpretation

For each parent p and seed s, let Z be new-panel frozen-baseline NLL, A/B/C/D the final flat/fixed/learned/dense NLLs. For memory X define `G_X=Z-X`, `P_X=shuffled_X-X`, `R=B-C` (positive favors learned routing), `T_X=X-A` (positive is a quality penalty versus flat), and `Q_X=D-X` (positive favors memory over dense). Verify disabled_X=Z bitwise, so disabled effect=G_X, not independent evidence. Verify `Q_X=G_X-(Z-D)` within 1e-12. Report B−A, C−A, B−C and every dense contrast explicitly.

All thresholds below are proposed, descriptive screening rules, not significance/noninferiority tests. Equal-weight means over 27 cells and separate means over each parent's three seeds are required. Shared parents, three backbone initializations, orders, seeds and data preclude treating 27 cells as independent backbone replications. No p-values or independent-replicate confidence intervals.

**U_X — useful memory**, separately for each X=A/B/C: mean G_X≥.005, mean P_X≥.005, at least 22/27 cells with both G_X>0 and P_X>0, at least 8/9 parents with both corresponding parent means>0, and mean final X below mean initial X. Report every clause and sign.

**R — learned routing benefit:** U_C passes, mean B−C≥.005, at least 22/27 B−C>0, at least 8/9 parent mean B−C>0. This is the primary learned-versus-fixed decision. Nonzero router gradients/movement alone cannot pass it. A failure does not establish equivalence or that learned routing can never help.

**Q_C — acceptable learned-tree quality versus flat:** mean C−A≤.005, at least 22/27 C−A≤.005, and at least 8/9 parent mean C−A≤.005. Evaluate the identical **Q_B** rule for fixed tree as a separately declared secondary result, not a replacement for Q_C.

**W_X — observed score-work reduction**, separately for B/C: every audited query has no more than 25% of flat's full-dimensional key-plus-router score dot products and no more than 25% of flat's logical candidate-key-plus-router elements, with eight selected values and independently validated traces. The expected ratio is .12890625 for both counts. Report actual normalization, sort and gather work even if W_X passes. A mismatch with the exact registered 512-key/16-router path is an engineering defect, not grounds to silently accept a different algorithm. W_X certifies this limited work component, not lower total computation or physical access.

**L_X — measured RAM quality-cost support**, separately for B/C: use primary workload, pair each hierarchy to flat on the same parent/seed. For each model use median measured duration, then ratio hierarchy/flat. For `addition_forward`, require geometric mean ratio≤.80, at least 22/27 ratios<1 and at least 8/9 parent geometric mean ratios<1. For `model_forward`, require geometric mean ratio≤1.05, at least 22/27 ratios≤1.05 and at least 8/9 parent geometric means≤1.05. Both scopes must meet reliability rules and both sets of clauses must pass. Pure score/select timing is explanatory; it cannot replace addition/full-model timing. No latency conclusion from analytical W_X alone.

Dense reference: report all Q_A/Q_B/Q_C values, means, dispersions, signs and parent means; separately report the P4-style .005 dense-quality tolerance (mean Q_X≥−.005, at least 22/27 cells and 8/9 parent means≥−.005). It is not a hierarchy-versus-flat gate and cannot rescue R/Q/W/L failures.

Decision table, fixed before outcomes:

| Evidence | Permitted bounded interpretation / recommendation |
|---|---|
| U_C + Q_C + W_C | Learned hierarchy is a candidate quality versus score-work trade-off. A ≤.005 NLL penalty is accepted only at the registered work reduction; no RAM speed claim follows. |
| Above + R | Useful trained routing adds enough benefit to justify **requesting human review** of a possible learned-topology follow-up. This is not authorization to design/execute a new phase automatically. |
| Above + R + L_C | Full P5 learned-hierarchy criterion passes at the registered workload. Recommend requesting human approval to consider a bounded capacity-scaling design; no capacity/SSD claim or execution permission is granted. |
| Q/W pass but L fails or is inconclusive | Preserve algorithmic comparison-work finding; report runtime disadvantage/uncertainty. Do not claim a measured efficiency advantage or recommend capacity scaling on this gate. |
| R fails but fixed-tree U_B/Q_B/W_B (and possibly L_B) pass | Report evidence for fixed partitioning at this budget; learned routing is not justified by the registered effect threshold. Do not relabel this as learned-router success. |
| U or quality conditions fail | Reject the corresponding registered configuration/trade-off. Preserve favorable individual cells, all negative outcomes and incomplete/noisy measurements. |

Report every flag separately plus the full learned-hierarchy conjunction; no retrospective substitution of fixed for learned, primary for secondary workload, analytical for timed work, or dense for flat. All 117 cells are needed for a complete quality study; all registered timing workers are needed for a complete timing study. A completed quality stage remains publishable as bounded evidence if timing is incomplete, with the overall efficiency conclusion unresolved.

## 9. Bounds, stopping and staged approval

Proposed hard scientific-worker ceilings: **1,800 seconds for quality/training**, **600 seconds for profiling/timing**, **2,400 seconds combined**, no transfer of unused time between stage caps. Quality cells: 300 seconds each. Timing workers: 45 seconds per parent/seed quartet, 15 seconds per baseline. **2 GiB sampled process-tree RSS** per cell/worker and stage/suite; existing 0.1-second polling semantics. Record worker wall time, stage totals, supervisor finalization after exit and external reporting pauses. These are caps, not runtime predictions; flat matrix operations may be faster than tree gathers despite higher score counts.

The earliest applicable cell, stage or combined-suite deadline takes precedence. Per-worker maxima are not additive allocations: the 600-second timing stage can terminate an unfinished worker even though its individual limit remains. Preserve that worker's partial evidence and every unexecuted worker; do not shrink repetition counts, drop variants or grant unused time from another stage to complete the matrix. The same precedence applies to quality cells. All loading, trace preparation, warmups, measured calls and ordinary evidence packaging inside a stage count toward that stage's wall time.

This is a proposed increase from P4's 1,800-second total ceiling to cover a larger comparison matrix and explicit timing. **The human approved this exact 2,400-second budget on 2026-11-13; stage and RSS ceilings remain unchanged.** No cloud/GPU/download/hardware change, silent extension, shorter replacement budget, skipped slow cell, seed substitution or rerun of an unfavorable result. Nonfinite loss/parameters, identity/freeze/optimizer/restore failure, wrong counts, failed invariance or resource breach stops the stage/suite and preserves partial, failed and unexecuted records. Engineering fixes need a recorded amendment and fresh run identity before any rerun. Timing instability retains an INCONCLUSIVE flag without retiming; it is not itself a model failure.

No experiment implementation until this exact specification receives an authorized scientific approval record. After approval, Sol implements; Luna independently reviews equations, gradients, shapes, counters, checkpoints and timing. Root provides independent scientific/preflight acceptance under the exception. Any model selection change must be disclosed; never substitute agent names for actual Astra review. Human merge, publication and further-phase/scaling approval remain separate.

## 10. Implementation contract and independent preflight after approval

Use isolated P5 modules, strict configuration and a distinct family/schema. Do not alter P1–P4 numerical sources, validators, configs, ADRs, raw records or dependency lock. Existing `Memory` supports A/B/C, but P4 assumes every memory has a trainable router, requires tree routing in evaluation, and assumes 198,401 trainable addition parameters. P5 must explicitly handle flat/no-router, fixed/buffer-router and learned/parameter-router cases rather than weakening old contracts. A fixed router has state-dict entries but no named optimizer parameter; do not equate state-dict keys with parameter names.

Required independent acceptance evidence:

- Correct nine-parent mapping; actual strict P4 restore and upstream tensor equivalence; original files unchanged. Baseline/bypass equality and causal/tied-output math preserved.
- Exact shared initialization and isolated RNG; B/C forward equality at step zero; fixed router and all backbone tensors/buffers immutable after updates; frozen gradients absent; gradients reach memory through the frozen suffix.
- Flat exhaustive score/ID reference; tree exhaustive-within-selected-branches reference including branch prior; exact tie ordering, shapes/dtypes, selected-value gradients, router gradients on a constructed multibranch fixture; full-branch/zero-prior tree-to-flat synthetic equivalence. Fixture overrides cannot change real settings.
- Exact parameter/buffer counts, ordered optimizer membership, one duplicate-free AdamW group and numerical settings; initial moments empty; later state IDs/clocks/shapes correct; fixed router never optimized.
- Strict atomic snapshots at 0/256/512, full family/cell/data/parent/source/spec/config/lock identities, freeze flags, router buffer, keys/values/index/partition metadata, optimizer, RNG and cursor. Corruption/mismatch rejection. Synthetic uninterrupted-versus-resumed model/optimizer/RNG equivalence and exact restoration of representative actual artifacts before interpretation.
- Independent raw-Parquet panel reconstruction, prior hashes and full-train exclusion; explicit previously-unused-panel audit. Freeze exact IDs/bytes/hash without model evaluation before training.
- Token-weighted NLL checked by an independent float64 per-token oracle with justified float32 tolerance and a known-logit unequal-batch fixture; separate bitwise replay/bypass gates unchanged. Evaluation/interventions/timing preserve mode, tensors, optimizer, RNG and checkpoint bytes.
- Flat global paired permutation and tree within-branch paired permutation; value-only shuffle changes only values; fixed permutations/IDs across paired architectures; expected invariance and exact-tie limitations tested independently.
- Independent work traces and logical fractions, including buffer denominator, per-batch amortization, candidate/selected unions and the countervailing key-normalization work. Hand-calculated tests for all analysis clauses, signs, equality boundaries, parent aggregation and geometric latency ratios.
- Synthetic timing harness verifies exact call order/counts, two workloads, scope boundaries, GC/RNG restoration, percentile definition and unstable-timing INCONCLUSIVE behavior. No quality selection, state mutation, outlier filtering or hidden repetitions.
- Watchdog/partial export tests. Run locked Ruff/mypy/full tests/E0; preserve all failures. Root reads implementation and independent tests, reruns relevant checks, accepts engineering evidence, and records the numerical code/config/data/spec/lock freeze before explicitly authorizing real-data execution.

Archive execution source and exact environments. During execution allow results-only commits, retaining actual HEAD/dirty flags while asserting invariant numerical archives and identities. New tests or documentation that affect captured source wait until the suite finishes. No source repair during a running study.

## 11. Evidence and reporting deliverables

Each completed quality cell gets a separate GitHub checkpoint containing compact manifests, raw metrics, checkpoint indexes, source/config/spec/lock/environment/data/parent identities, seeds, order/permutation records, training/routing logs and terminal status. Report each cell here with loss, useful-memory contrasts when available, runtime and integrity status. Keep original binary weights/optimizer/source archives/corpus locally. Timing outputs are pushed after each completed worker, outside timed intervals; report measured scope/workload and uncertainty explicitly. Never rewrite execution-time pending-review fields to imply retrospective approval.

After completion, independent arithmetic must reconstruct all 27 paired contrasts per architecture, parent and factor summaries, each clause/flag and timing ratios from raw records without importing the implementation analysis. A separate read-only artifact audit inspects all 333 actual snapshots, original parent hashes, buffer/optimizer contents, data/order identities, source maps and evaluation/profiling accounting. Root reviews and reruns audits before final scientific acceptance. Preserve negative results, noisy timing, failed preflights and unexecuted cells.

The final report includes all initial/final/intervention losses, means/sample SD/min/max/sign counts, nine parent means and all seed values, B/O/seed marginal means, all dense comparisons, routing/utilization, train/supervised/timing wall times, RSS, analytical versus traced work, and a quality-versus-work/latency table (with standalone scientific figure if useful). Repeated timings/shared factors are not independent replicas. A measured result applies to this CPU implementation and workload, not a hardware-independent algorithmic speedup.

## 12. Decisions requiring authorized scientific review

The following resolutions were proposed at commit `dabb5db22b38977838da36a801c410ee3544e738` and subsequently approved in full by the human and authorized reviewer, as recorded below:

1. Use the nine P4 baseline snapshots, fresh shared seeds 501–503, and freshly train the unchanged dense reference alongside all three memory architectures: 117 cells/108 trainings, with no reuse of trained P4 additions.
2. Retain exact old retrieval/optimization mathematics and expose the real 256-scalar router difference; accept that flat-versus-tree includes the branch prior and fixed routing still has a trained query.
3. Use new panel ranks 2048..2559, global paired permutation for flat, branch-preserving paired permutation for trees, and the explicit 612+9 evaluation budget.
4. Approve .005 quality/effect margins and 22/27 plus 8/9 consistency clauses; 75% observed score-work reduction; .80 addition-time and 1.05 full-forward ratios with the fixed timing-reliability rule. These thresholds are design judgments requiring review, not inferred significance levels.
5. Approve the two timing workloads/scopes/repetition schedule, addition-only consulted-state definitions, distinction between algebraic/traced work and latency, and the conditional continuation recommendations. A score-work pass cannot stand in for a runtime pass.
6. Approve the proposed 1,800+600=2,400-second worker ceiling and 2 GiB bounds. Obtain any necessary human budget decision before execution. Human approval is still required before further phases, merging or publication.

## 13. Approval record before implementation

On 2026-11-13 (America/Panama), the human research lead explicitly instructed: “Approve ADR-0010 and the 2,400-second budget. Use Sol to implement and Luna to review, complete preflight and freeze settings before training. Report every run here and push each checkpoint to GitHub.” This supersedes the proposal-only stop instruction and approves all six decisions above and the exact existing numerical protocol. No scientific thresholds, seeds, dimensions, durations or resource ceilings were changed by this approval entry.

Root Codex accepts the scientific design under the standing human-authorized reviewer exception. Rationale: all nine frozen parents and shared fresh initializations avoid checkpoint selection; identical fixed/learned starting tensors isolate router training as specified; fresh dense training keeps the reference on the same protocol; new-panel construction, paired interventions and independent artifacts guard validity; separate score-work and latency flags prevent an analytical operation reduction from becoming an unsupported speed claim. Parameter/buffer differences, branch-prior confounding, repeated key normalization, correlated cells and timing reliability limits are explicit. The stricter composite cannot be rescued by secondary fixed-tree, dense or workload results.

Sol owns implementation/execution under this specification; Luna owns separate engineering review. Root must independently accept preflight and record exact source/config/spec/data/lock identities before authorizing real-data training or timing. No model outcome informed this approval. Engineering clarifications must be recorded before outcomes; substantive scientific changes require a new reviewed amendment. Human merge, publication and further-phase/scaling approvals remain pending. Astra review remains NOT_PERFORMED.

**Approval record: HUMAN_AND_AUTHORIZED_REVIEWER_APPROVED. Implementation: AUTHORIZED. Engineering preflight: PENDING. Source/data freeze: NOT_PERFORMED. P5 model evaluation/training/timing: NOT_STARTED. Astra review: NOT_PERFORMED.**

### Pre-outcome engineering clarification: timing and checkpoint reporting

On 2026-11-13, the authorized reviewer accepted Sol's proposed reporting handshake. After each isolated timing worker completes, its supervisor waits for an explicit filesystem acknowledgement from the orchestrator that the exact worker has been reported and its evidence committed and pushed. No timing child remains alive during this wait, and no timing child overlaps Git operations or independent audits. The acknowledgement identifies the suite, expected worker, pushed commit and push completion; wrong, reused or out-of-order acknowledgements are rejected. Cumulative accounting and the unique expected worker identity are persisted atomically.

Only the precisely recorded external acknowledgement wait is excluded from the timing stage's active clock and combined worker budget. Timing active time is stage wall time minus these waits, including loading, identity verification, trace preparation, warmups, measured calls, supervision, packaging and every other overhead. The quality ceiling remains 1,800 seconds, timing ceiling 600 seconds, combined ceiling 2,400 seconds, with no transfer or reset. Per-worker deadlines remain 45 seconds for a quartet and 15 seconds for a baseline. Synthetic clock tests must demonstrate that only the external wait is excluded. This operational clarification enables the already-required per-worker report/push without introducing competing Git workload into latency measurements; it does not add scientific worker time or change any measurement or decision criterion.

Untimed operand-level `TorchDispatchMode` probes are accepted for the registered executed-shape work audit. They observe the actual lookup operations without changing retrieval mathematics; their preparation and execution count against the relevant active worker budget. These clarifications precede all P5 real-data model outcomes. Astra review: NOT_PERFORMED.

The same acknowledgement is required once at timing-stage entry, using the finalized quality-stage run ID, before the first timing worker starts. This lets the orchestrator finish reporting/pushing the last quality cell and finalized quality-stage records without overlap. Only this explicitly measured external wait is excluded; setup and finalization are charged normally. It is a synchronization event, not an additional timing run or model call. This clarification was accepted by the authorized reviewer before outcomes and before source freeze.
