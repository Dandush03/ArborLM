# ADR-0011 — P6: inference-only retrieval optimization (P6-E) and routing fidelity (P6-Q)

- Date: 2026-11-13 (America/Panama).
- Status: **SPEC: HUMAN-APPROVED (Fable-drafted) on 2026-11-13, as drafted and without the replication panel — see §7.** Drafted as a proposal at commit `43730f1`; the body below is unchanged from that draft apart from this line and §7.
- Prepared by Claude Fable 5.2 (`claude-fable-5-2`) under the workflow proposed in ADR-0012, which is itself pending human approval. **Astra review: NOT_PERFORMED.**
- Scope: two separately scoped, separately approvable studies on the **existing frozen P5 checkpoints**. No training, no new architecture, no capacity change, no SSD, no GPU, no downloads. P1–P5 code, records, thresholds and outcomes are immutable; the P5 composite criterion remains **FAILED** whatever P6 finds.
- Read before drafting: `AGENTS.md`, canonical handoff, experiment protocol, research log, ADR-0001–0010, P1–P5 result reports and reviews, P5 audits, `src/arborlm/pilot_model.py`, `p5_model.py`, `p5_timing.py`, and the Claude-workflow P5 review in `docs/reviews/p5-claude-review-2026-11-13/`.

## 1. Why these two questions, and why separately

P5 measured two things about the tree that point in opposite directions: it scores 12.89% as many key/router rows as flat (analytical, confirmed by operand traces), and its memory addition takes about 2.60× as long as flat on the registered CPU workload (measured). P5 also found that the trees select fewer distinct slots than flat and that training the router did not help.

Two different explanations are entangled and need different experiments:

- **Implementation cost (P6-E).** The existing tree path gathers 512 raw key rows per query, normalizes them again on every call, scores them with a batched product over small per-query matrices, and sorts all 512 candidate IDs per query before selection. None of that is required by the mathematics. Whether removing it makes the tree competitive with flat at 4,096 slots is an engineering question that must be answered by measurement, with outputs held fixed.
- **Retrieval quality (P6-Q).** Independently of speed, the top-2-branch restriction and the branch prior may exclude slots that the same scoring rule would select if every branch were searched. Whether that happens, how often, and whether it matters for prediction is a diagnostic question about the trained checkpoints.

They are kept separate so that an engineering speedup cannot be presented as evidence about retrieval quality and a fidelity finding cannot be presented as evidence about speed. Either study can be approved, run and reported without the other.

### Exploratory information already seen (disclosed)

Before this draft, and without loading any checkpoint or real data, the existing implementation was profiled stage by stage on synthetic random tensors (`docs/reviews/p5-claude-review-2026-11-13/operators/`). That profile informed which optimizations are listed in §3.2. No optimized implementation has been written, run or timed, and no fidelity quantity has been computed on any checkpoint. All thresholds below were written before any P6 observation.

What that synthetic profile showed, at 512 queries per call, single thread, one machine, one invocation (medians; exploratory, not registered evidence):

| Stage of the existing code | Tree, µs | Flat, µs |
|---|---:|---:|
| Gather 512 raw key rows per query | 1,950 | — |
| Normalize gathered keys / normalize key table | 894 | 17 |
| Score contraction (`bmm` / matrix product) | 1,104 | 321 |
| Sort candidate IDs and regather, inside selection | 561 | — |
| `topk(9)` | 1,520 | 1,965 |
| Router, prior, index construction, everything else | ~160 | ~10 |
| End to end | 6,529 | 2,378 |

Two consequences shape this specification. First, repeated normalization is a real cost but only about 14% of the tree path; the P5 review's emphasis on the 64× normalization volume named one contributor, not the main one. Second, `topk` costs nearly as much on the tree's 512-wide rows as on flat's 4,096-wide rows, and it is 85% of the flat path. Selection is a cost floor both paths share, so removing the tree's gather, normalization and sort cannot by itself put the tree far below flat. The practicality prediction E-H4 is therefore stated with the expectation that it may well fail, and the variant list includes a selection kernel for both architectures.

## 2. Shared material and integrity rules

- **Checkpoints.** All 81 final (step-512) P5 memory snapshots — 27 flat, 27 fixed-tree, 27 learned-tree — from suite `P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be`, and for P6-Q also the 27 shared step-0 tree snapshots. No subset, no seed selection, no replacement. Every snapshot is restored strictly and its state hash checked against the P5 record before and after use.
- **Reference implementation.** `pilot_model.Memory` exactly as frozen for P5 (execution-freeze archive `6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e`). It is never edited. All new code lives in new modules and new tests.
- **Integrity replay.** Before any P6 measurement on a checkpoint, the unmodified model must reproduce that cell's registered P5 final NLL **bitwise** on the P5 panel (ranks 2048–2559, SHA-256 `d50cbe4c…72b98`) in the matched environment. A mismatch stops the study for engineering review.
- **Environment.** Same machine class, CPU float32, deterministic algorithms, one intra-op and one inter-op thread, unchanged `uv.lock`, inference mode, eval mode. Hardware, OS, Python/torch versions and `torch.__config__` are recorded.
- **Data.** Only the already approved local WikiText-2 files. No download, no test split.
- **Process.** Human approval of this specification → implementation by the implementer role → independent audit of code and tests by the auditor role → source/config/spec/data freeze committed and pushed → explicit human authorization to execute → single registered invocation per study → independent recomputation from raw records → review. Failed runs, failed checker attempts and unexecuted cells are preserved.

---

## Part E — P6-E: numerical-equivalence inference optimization

### 3.1 Question and falsifiable predictions

**Question.** Can the existing hierarchical retrieval be reimplemented for inference so that it returns the same outputs as the frozen implementation while running materially faster, and does the result reach the latency margins that P5 registered against flat?

Predictions, each of which can fail:

- **E-H1 (equivalence, cache and ordering).** Variants T1 and T2 below are **STRICT**-equivalent to the reference on every checkpoint and every query.
- **E-H2 (equivalence, contraction changes).** Variants T3, T4, T5 and F2 are at least **BOUNDED**-equivalent (T3–T5 with their guard band), i.e. identical selected slot IDs for every query.
- **E-H3 (material speedup).** At least one equivalent tree variant reaches the SP criterion in §3.6.
- **E-H4 (practicality at this size).** At least one equivalent tree variant reaches the PR criterion in §3.6, which reuses P5's registered latency margins unchanged.

E-H4 can fail while E-H3 passes. That outcome — overhead removed, flat still faster at 4,096 slots — is a legitimate and informative result, because a 512×4,096×16 product is small enough for an optimized matrix kernel that the tree's analytical advantage may not survive at this size.

### 3.2 Implementations (fixed list; additions require a recorded amendment before execution)

All variants are **inference-only**. They are constructed from a restored checkpoint, never used in training, hold no gradient state, and must refuse to run when `torch.is_grad_enabled()` or when the module is in training mode. Each cache is bound to the hash of the tensors it was built from and is rebuilt or rejected if the source tensors change.

| ID | Applies to | Change relative to the reference |
|---|---|---|
| F0 | flat | Reference `Memory.lookup` / `Memory.forward`, unmodified. |
| F1 | flat | Normalized key matrix computed once at load instead of on every call. Nothing else changes. |
| T0 | fixed, learned | Reference tree path, unmodified. |
| T1 | fixed, learned | Normalized key table and normalized router computed once at load; candidates gathered from the normalized table. Scoring, prior and selection code paths otherwise as T0. |
| T2 | fixed, learned | T1, plus candidate lists built in ascending slot-ID order (visited branches ordered by branch ID), so the per-query sort of 512 candidate IDs inside selection is unnecessary. `selected`, `branch_ids`, `candidate_ids` and `route_scores` are returned with exactly the content and order T0 returns. |
| T3 | fixed, learned | T2, plus the score contraction expressed on branch blocks (normalized keys viewed as 16×256×16) instead of a batched product over per-query 512×16 matrices. |
| T4 | fixed, learned | T2 semantics computed without gathering candidate keys: queries are grouped by visited branch and each branch block is scored with one dense matrix product, then scattered back to per-query candidate order. |
| T5 | fixed, learned | The faster of T3/T4 scoring is not assumed: T5 is T4 scoring plus an exact selection kernel that replaces `topk(9)` with eight successive first-occurrence maxima over ascending-ID candidates, followed by the registered tie-safety check and fallback. |
| F2 | flat | F1 plus the same exact selection kernel as T5. |

F1 and F2 are included so that the tree is compared against a flat baseline that received the same kinds of optimization. Comparing an optimized tree with an unoptimized flat would favor the tree unfairly. Wherever this document says "the flat comparator", it means the EQ-passing flat variant (F0, F1 or F2) with the lowest W8 `addition_forward` median in T-screen.

**Contract details fixed by the independent audit** (`docs/reviews/p5-claude-review-2026-11-13/audit/AUDIT.md` §4.3, synthetic tensors only):

- `branch_ids` must stay in route-rank order (column 0 is the top-1 branch) and `candidate_ids` in the reference's rank order. The P5 utilization statistics read `branch_ids[:, 0]`; an implementation that returned ID-ordered branches would silently change them. Internal ID ordering is allowed; the returned tensors are not.
- Scores are divided by the temperature exactly as the reference does. Multiplying by its reciprocal changed 15% of synthetic scores in the last bits.
- On the audit machine, normalizing the key table once and gathering was bitwise equal to gathering and normalizing, and `bmm` rows were bitwise invariant to row order. Those observations are the basis for predicting STRICT for T1 and T2. They were made on random tensors on one build and are predictions here, not results.
- Summation-based or full-table contractions differed from `bmm` in a large fraction of synthetic scores by up to about 1e-6 and can flip a selection at a near-tie, which is why T3–T5 carry a guard band and are only predicted BOUNDED.

**Guard band (T3, T4, T5).** Changing the order of floating-point operations can move a score by a few units in the last place and flip a selection at a near-tie. T3, T4 and T5 therefore recompute, with T2's arithmetic, every query whose fast scores have any adjacent gap smaller than δ = 1e-4 among the top 9 candidates. δ is fixed here. The fraction of queries taking this fallback is recorded for every call and its cost is included in every timed call.

### 3.3 Equivalence classes and gate

Evaluated per variant on **every** applicable checkpoint (27 for each F-variant; 54 for each T-variant), on:

- (a) all 32,768 queries of the P5 panel, through the full model;
- (b) the P5 timing inputs (ranked training chunks 0–31) at both registered batch shapes;
- (c) synthetic fixtures with constructed exact ties (duplicated key rows within a branch and across the two visited branches, duplicated router rows), checked against the registered tie rule: descending score, then ascending slot ID.

| Class | Requirement, relative to the reference on the same inputs |
|---|---|
| **STRICT** | `selected` identical in order; selected scores bitwise equal; `branch_ids`, `candidate_ids`, `route_scores` bitwise equal; full-model logits bitwise equal; panel NLL bitwise equal. |
| **BOUNDED** | `selected` identical in order for 100% of queries; `branch_ids` and `candidate_ids` identical; max abs selected-score difference ≤ 1e-5; max abs logit difference ≤ 1e-4; per-checkpoint abs panel-NLL difference ≤ 1e-6. |
| **NOT EQUIVALENT** | Anything else, including a single query with a different selected slot or order on any checkpoint. |

**Gate EQ(v):** variant v is STRICT or BOUNDED on all its checkpoints, on (a), (b) and (c). A variant that is NOT EQUIVALENT is excluded from every latency decision and is not timed in the registered timing stage. Its mismatches are preserved: query index, both selections, reference scores, and the reference score gap at the selection boundary.

There is no tie-tolerant third class. If the human lead wants one, it must be defined and approved before execution (see §6, question 4).

### 3.4 Workloads and timing protocol

The P5 protocol (ADR-0010 §7) is reused without change so that P6-E numbers are comparable with P5's: inputs from ranked training chunks 0–31 only; scopes `lookup_score_select`, `addition_forward`, `model_forward` with the same boundaries; `perf_counter_ns`; GC disabled only inside timing blocks; no outlier deletion, no adaptive repetition, no best-time selection; for each workload/scope 8 rounds, each model block 2 untimed warmups then 10 timed calls, variant order rotated by `(i + round) mod n`; reliability rule (all durations positive, median ≥ 100× clock resolution, max/min round median ≤ 1.25) with unusable measurements retained and the affected flag reported **INCONCLUSIVE** without re-timing.

| Workload | Shape | Queries per call | Status |
|---|---|---:|---|
| W8 | batch 8 × context 64 | 512 | **Primary** (same as P5) |
| W1 | batch 1 × context 64 | 64 | Secondary (same as P5); reported in full, cannot replace W8 |
| Wtok | batch 1 × context 1 | 1 | Descriptive only; `lookup_score_select` and `addition_forward` scopes; no criterion. This is a single-position forward, not autoregressive decoding with a KV cache. |

One worker per parent/seed (27 workers), holding that parent/seed's flat, fixed-tree and learned-tree checkpoints and every implementation variant that passed EQ. No other intentional load; Git activity and audits are paused during timed workers using the P5 acknowledgement handshake.

**Two timing stages, to avoid choosing a winner on noise:**

- **T-screen:** all EQ-passing variants. Used only to apply the fixed selection rule: for each tree kind, the *selected variant* is the EQ-passing T-variant with the lowest W8 `addition_forward` geometric-mean ratio to T0; the flat comparator is chosen by the rule in §3.2.
- **T-confirm:** fresh workers, fresh processes, same protocol, timing only T0, the selected T-variant, F0 and the flat comparator. **All registered latency criteria are evaluated on T-confirm only.** T-screen numbers are reported in full as screening data.

**Reported for every variant/scope/workload:** median, nearest-rank p10/p50/p90/p95, min, max, all round medians, all raw nanosecond samples. Repeated timings of one model are not independent replications.

**Cold and warm conditions.** All registered timings are process-warm, model-warm (after 2 warmups), with every tensor resident in RAM. Separately and descriptively: one-time cache construction time per variant, and the duration of the first call after model load. No OS cache flushing; nothing here is a cold-storage measurement.

**Memory behavior (reported, no criterion):**

- Persistent extra state per variant in bytes, from tensor sizes (`nbytes`), e.g. the normalized key table.
- Transient allocation per call, measured in a separate untimed pass with PyTorch's CPU memory profiler: total bytes allocated and peak live bytes per call. Labelled as allocator-level measurements.
- Process RSS before load, after load, after cache construction and after the timing stage, with the caveat that sampled RSS is coarse.
- Not measured: cache misses, memory bandwidth, physical I/O, energy. No statement about them is permitted.

### 3.5 Resource limits

No training. CPU only. Equivalence stage ≤ 1,200 s active worker time; T-screen ≤ 1,200 s; T-confirm ≤ 600 s; P6-E combined ≤ 3,000 s; no transfer of unused time between stages. Per timing worker ≤ 90 s (T-screen) and ≤ 45 s (T-confirm). Sampled process-tree RSS ≤ 2 GiB per worker and per stage. These are caps, not predictions. A breach stops the stage and preserves partial and unexecuted records; repetition counts are never reduced to fit.

### 3.6 Registered criteria (evaluated on T-confirm, W8, per tree kind K ∈ {fixed, learned}, selected variant v)

- **EQ(v)** — §3.3.
- **SP(K) — material speedup over the original implementation.** Geometric mean over the 27 pairs of median(v)/median(T0) at `addition_forward` ≤ 0.50; ratio < 1 in at least 26/27 pairs and in 9/9 parent geometric means; reliability rule passed for all 27 pairs.
- **PAR(K) — no slower than flat.** Against the flat comparator: `addition_forward` geometric-mean ratio ≤ 1.00 with at least 22/27 pair ratios ≤ 1.00 and 8/9 parent geometric means ≤ 1.00; and `model_forward` geometric-mean ratio ≤ 1.05 with at least 22/27 pairs ≤ 1.05 and 8/9 parent geometric means ≤ 1.05.
- **PR(K) — practicality at the registered size.** Exactly P5's L clauses, against the flat comparator: `addition_forward` geometric-mean ratio ≤ 0.80, at least 22/27 ratios < 1, at least 8/9 parent geometric means < 1; and `model_forward` geometric-mean ratio ≤ 1.05, at least 22/27 ratios ≤ 1.05, at least 8/9 parent geometric means ≤ 1.05.

The same ratios against uncached F0 are reported alongside, labelled as the weaker comparison. The 0.50 margin in SP and the parity definition PAR are new design judgments made before observation; PR's margins are P5's, unchanged. **A PR pass in P6-E does not change P5's L or composite outcome**: P5 tested the implementation it registered.

### 3.7 Stop conditions

Integrity replay mismatch; checkpoint hash change; any variant running with gradients enabled or mutating model state, buffers or RNG; resource breach; nonfinite output. Each stops the affected stage with all evidence preserved. If no T-variant passes EQ, P6-E ends with the equivalence result and no timing. Unreliable timing yields INCONCLUSIVE, never a re-run.

---

## Part Q — P6-Q: routing fidelity diagnostic

### 4.1 Question and what "exhaustive reference" means here

**Question.** For the trained tree checkpoints, does restricting the search to the top-2 routed branches exclude slots that an exhaustive search would select under a stated scoring rule, and does that exclusion, or the branch prior, change prediction?

The registered tree rule scores a candidate slot i in visited branch b as

`s(i) = cos(q, key_i) / 0.2 + log_softmax(route_scores)[b]`, with `route_scores = cos(q, router_row) / 0.2`,

and takes the top 8 over the 512 candidates in the 2 highest-routed branches, ties broken by ascending slot ID. "Exhaustive" is therefore ambiguous unless the prior is specified. Four selection rules are defined, forming a 2×2 design:

| Rule | Branches searched | Branch prior | Meaning |
|---|---|---|---|
| **T2P** | top 2 | on | The registered rule. |
| **T2N** | top 2 | off | Same candidates, prior removed from scores. |
| **X16P** | all 16 | on | Exhaustive reference under the tree's own scoring rule. T2P is exactly X16P restricted to the two highest-prior branches. |
| **X16N** | all 16 | off | Exhaustive cosine reference: the flat rule applied to the tree checkpoint's keys. |

T2P versus X16P isolates the candidate restriction. T2P versus T2N isolates the prior among visited candidates. X16N differs from T2P in both.

### 4.2 Interpretation limits fixed in advance

- **Recall against a reference is not relevance.** During training a key received gradient only from queries routed to its branch. A slot in an unvisited branch can score highly for a query under X16P or X16N without its value ever having been trained for that context. Low recall therefore shows that the restriction changes the selection; it does not by itself show that useful information was lost.
- **Prediction effects are asymmetric.** These checkpoints were trained under T2P. If evaluating the same weights under X16P *lowers* NLL, that is direct evidence the restriction costs predictive quality even without retraining. If it *raises* NLL or leaves it unchanged, that does not show the restriction is harmless: the alternative rule is off-distribution for these weights, and a model trained under it might behave differently. Only the first direction supports a strong statement.
- No rule other than T2P was used in training; nothing in P6-Q is a result about training with exhaustive search, and no retraining is proposed here.
- P6-Q is a diagnostic on a panel whose T2P outcomes are already known. It selects no checkpoint and tunes nothing.

### 4.3 Measurements

For every tree checkpoint (54 final; 27 shared initial, descriptive), every query of the panel, record under each rule the selected slot IDs, selected scores, visited branches, route scores and softmax weights. Derived per checkpoint:

- **Routing recall.** `recall_P` = mean over queries of |sel(T2P) ∩ sel(X16P)| / 8; `recall_C` likewise against X16N. Also the fraction of queries with recall 1, and the distribution over 0…8.
- **Recall as a function of search width.** `recall_P` recomputed with k = 2, 3, 4, 6, 8, 12, 16 visited branches (prior on), giving the width at which the selection stops changing. Descriptive.
- **Exactness certificate.** The fraction of queries for which the tree's 8th selected score is at least `1/0.2 + max over unvisited branches of the prior`; for those queries T2P provably equals X16P. Reported as a cross-check on `recall_P`.
- **Training coverage of lost slots.** For every slot, whether its key and value differ bitwise from the paired step-0 snapshot, and the L2 distance moved. With zero weight decay a slot never selected in training keeps its initial bytes. Each lost candidate is classified as trained or untrained, and recall is reported both overall and restricted to trained reference slots. This addresses the first interpretation limit in §4.2 directly.
- **Lost candidates.** Per query, the reference-selected slots absent from T2P: count, the route rank (1–16) of the branch each lies in, its reference score, and the score margin to the T2P boundary.
- **Weighted recall.** The reference rule's softmax weight (over its own 8) that falls on slots T2P also selected. A lost slot with negligible weight matters less than one that would dominate.
- **Prior effects.** Distribution of the top-1 minus top-2 route-score gap; fraction of queries whose 8 selected slots all lie in the top-1 branch; fraction of queries where T2N and T2P select different sets; overlap |sel(T2P) ∩ sel(T2N)| / 8.
- **Selection concentration.** Unique selected slots, effective selected slots `exp(entropy)`, hottest-slot share and per-branch selected-value counts under each of the four rules, computed exactly as in P5 for T2P (which must reproduce the P5 record) and identically for the others.
- **Prediction effects.** Panel NLL under each rule with the same weights: `ΔNLL_restrict = NLL(X16P) − NLL(T2P)`, `ΔNLL_prior = NLL(T2N) − NLL(T2P)`, `ΔNLL_both = NLL(X16N) − NLL(T2P)`. Negative means the alternative rule predicts better than the registered rule. Per-token loss differences are also reported separately for positions whose selected set changed under the alternative rule and positions where it did not.
- **Fixed versus learned.** Paired learned-minus-fixed differences in every quantity above for each parent/seed, with means, sign counts and parent means. Descriptive.

**Reference correctness.** X16P and X16N are computed two ways: with the frozen `tree_candidates(visit=16, use_prior=…)`, and with an independent float64 implementation written by the auditor role that scores all 4,096 slots directly. Engineering gates: (i) T2P reproduces the P5 registered NLL bitwise; (ii) for every query, sel(T2P) equals the top 8 of the X16P scores restricted to the two visited branches; (iii) every lost slot lies in a branch of route rank ≥ 3; (iv) the two reference computations agree on selected IDs except at near-ties, where a near-tie is a reference boundary gap ≤ 1e-5, and every disagreement is listed. A violation of (i)–(iii), or a disagreement in (iv) outside near-ties, stops the study for engineering review.

**Panels.** Primary: the P5 panel (ranks 2048–2559), which allows gate (i). Replication, subject to separate human approval (§6, question 6): eligible validation ranks 2560–3071 under the existing recipe, reconstructed and independently audited for overlap exactly as P5's panel was. Flags below are evaluated on the primary panel; on the replication panel each flag is evaluated again and both outcomes are reported, and a finding is described as replicated only if the flag agrees.

### 4.4 Registered descriptive flags (per tree kind K, final checkpoints, primary panel)

The 0.005 nats/byte margin and the 22/27 and 8/9 consistency counts are the project's standing descriptive conventions. They are not significance tests; the 27 cells share nine parents, three seeds and one panel.

- **FID_K — high fidelity to the tree's own rule.** Mean `recall_P` ≥ 0.95, at least 22/27 cells ≥ 0.95, at least 8/9 parent means ≥ 0.95. Failure means the top-2 restriction materially changes the selection relative to exhaustive search under the same scoring rule.
- **COS_K — agreement with exhaustive cosine search.** The same three clauses for `recall_C`. Reported separately; it mixes restriction and prior.
- **LOSS_K — the restriction costs prediction.** Mean `ΔNLL_restrict` ≤ −0.005, at least 22/27 cells < 0, at least 8/9 parent means < 0.
- **PRIOR_K — the prior matters for prediction.** |mean `ΔNLL_prior`| ≥ 0.005 with at least 22/27 cells and 8/9 parent means sharing the sign of the mean; the sign is reported (positive: removing the prior hurts).
- Concentration and fixed-versus-learned differences have no pass/fail flag.

### 4.5 Permitted interpretations, fixed before observation

| Evidence | Permitted bounded statement |
|---|---|
| FID passes, LOSS fails | The top-2 restriction rarely changes the selection under the tree's own rule. Candidate loss is not a supported explanation for the tree's quality gap to flat. |
| FID fails, LOSS passes | The restriction excludes slots that improve prediction even without retraining. Candidate loss is a supported contributor to the quality gap for these checkpoints. |
| FID fails, LOSS fails | The restriction changes the selection, but these weights do not predict better with exhaustive search. Whether training with wider search would help is **not** answered. |
| FID passes, LOSS passes | Inconsistent with the structure of the rules if recall is near 1; treat as a possible defect and review before interpreting. |
| PRIOR passes, positive sign | The trained weights depend on the prior weighting. |
| PRIOR passes, negative sign | The prior hurts prediction for these weights; it is a candidate design fault. |
| Any outcome | No statement about speed, memory, I/O, capacity scaling or learned routing in general. No outcome reopens P5's R or composite decision. |

### 4.6 Resource limits and stop conditions

No training. CPU only. Exhaustive evaluation materializes about 134 MB per 512-query batch per intermediate tensor. Caps: ≤ 1,800 s active worker time for P6-Q (≤ 2,400 s if the replication panel is approved), ≤ 60 s per checkpoint evaluation, sampled process-tree RSS ≤ 2 GiB. Stop on any engineering-gate violation in §4.3, checkpoint hash change, state/RNG mutation, nonfinite output or resource breach, preserving partial and unexecuted records.

---

## 5. Combined decision matrix (recommendations only; none is an authorization)

| P6-E | P6-Q | Recommendation to put to the human lead |
|---|---|---|
| EQ + PR pass | LOSS fails | Hierarchical retrieval is computationally practical at 4,096 slots in this implementation, with selection unchanged. Request review of a bounded, preregistered **kernel size-scaling** study on synthetic tensors before any capacity or SSD work. No capacity, I/O or quality claim. |
| EQ + PR pass | LOSS passes | Practical to compute, but the restriction costs quality. Request review of a routing-design study (search width, prior) before any scaling. |
| EQ passes, SP passes, PR fails | any | Overhead was real and removable, but flat remains faster at this size. The open question becomes at what memory size, if any, the tree's work reduction outweighs flat's kernel efficiency; propose a synthetic size-scaling kernel study, or stop. |
| EQ passes, SP fails | any | The implementation-overhead explanation is not supported. Do not pursue hierarchy on efficiency grounds without a new idea. |
| No variant passes EQ | any | Report the equivalence failure and its cause. No latency claim. |
| any | FID fails, LOSS fails | Record that selection differs from exhaustive search without a counterfactual gain; note that only retraining could resolve it, which needs its own approved specification. |

No row authorizes training, capacity expansion, SSD experiments, merging or publication. Each needs a new human decision and its own reviewed preregistration.

## 6. Decisions requested from the human lead

1. Approve, amend or reject **P6-E** and **P6-Q** separately.
2. Approve the fixed implementation list in §3.2, including the flat comparators F1 and F2, the selection kernel in T5/F2 and the guard band δ = 1e-4.
3. Approve the equivalence classes and tolerances in §3.3 (1e-5 scores, 1e-4 logits, 1e-6 panel NLL), and that a single selected-slot mismatch makes a variant NOT EQUIVALENT.
4. Decide whether a tie-tolerant class should exist at all. The draft says no.
5. Approve the P6-E criteria in §3.6: the new 0.50 speedup margin, the parity definition, reuse of P5's L margins for PR, and evaluation on the confirmation timing stage only.
6. Approve or decline use of fresh validation ranks 2560–3071 as a P6-Q replication panel. Declining leaves P6-Q on the already observed P5 panel only.
7. Approve the P6-Q flags in §4.4, including the 0.95 recall level, which is a design judgment.
8. Approve the resource caps in §3.5 and §4.6 (P6-E ≤ 3,000 s, P6-Q ≤ 1,800 s or 2,400 s, 2 GiB RSS, local CPU only).
9. Confirm the review arrangement for P6 (ADR-0012), since this specification was drafted under a workflow that is itself awaiting approval.

## 7. Approval record

**Human approval, 2026-11-13.** After receiving the P5 review, this draft and the list of decisions in §6, the human research lead instructed in the project chat: "proceed p6 and then push once all togather so we wont spend our gh action usage". The lead records this as approval of P6-E and P6-Q **as drafted**, including the implementation list, equivalence classes and tolerances, criteria, flags and resource caps (§6 items 1–5, 7, 8), and as authorization to implement, freeze and execute them in this session. No threshold, variant, tolerance or cap was changed between the draft the human saw (commit `43730f1`) and this record.

What the instruction did not explicitly decide, and how it is handled:

- **§6 item 6, replication panel.** The draft made fresh validation ranks 2560–3071 "subject to separate human approval". A general instruction to proceed is not treated as that separate approval. **The replication panel is not used.** P6-Q runs on the P5 panel only, as the draft specified for that case. No new validation data is consumed.
- **§6 item 4, tie-tolerant class.** Stays as drafted: none exists.
- **§6 item 9 / ADR-0012.** The instruction is taken as the human lead's direction to run P6 under the Claude workflow. ADR-0012's other questions (temporary or standing, labels, `AGENTS.md` pointer, Astra) remain open and are not inferred.

Status after this record: **SPEC: HUMAN-APPROVED (Fable-drafted). Implementation and execution authorized for P6-E and P6-Q as drafted, without the replication panel.** Astra review: NOT_PERFORMED. Merge, publication, training, capacity and SSD work remain unauthorized.

### Pre-outcome engineering clarifications (recorded before any P6 implementation or observation)

1. **Push timing.** The human directed a single push at the end to limit CI usage. The source/config/spec freeze is therefore committed locally and identified by commit hash and source-archive SHA-256 before execution, and pushed with the results. This departs from §2's "committed and pushed" and from earlier studies' per-cell pushes, at the human's instruction. Local commit timestamps and hashes are the pre-execution evidence; they are weaker than a remote push made at the time.
2. **No acknowledgement handshake.** Because nothing is pushed and no audit runs during execution, the P5 reporting handshake has nothing to synchronize. Timing workers run sequentially with no other intentional load from this session; the orchestrator starts no agent, test or Git operation while a timing stage runs.
3. **Raw record placement.** Compact per-checkpoint and per-worker records go under `results/p6-e-2026-11-13/` and `results/p6-q-2026-11-13/`. Large per-query arrays stay local under `experiments/` (git-ignored) with SHA-256 recorded in the compact records, following the existing policy for binaries.
4. **Selection kernel detail (T5, F2).** The kernel takes nine successive first-occurrence maxima over ascending-ID candidates; the first eight are the selection and the ninth serves only the guard-band test. Its tie behaviour is verified on the constructed-tie fixtures like every other variant.
5. **Audit sequence.** The auditor role reviews the implementation and tests before the freeze and writes the independent float64 reference for P6-Q; after execution it recomputes every flag from raw records without importing the implementation's analysis.

### Further pre-outcome clarifications from implementation (recorded before the freeze and before any P6 outcome)

6. **P6-Q run order.** On synthetic tensors one checkpoint evaluation took about 26 s plus process start, which projects to roughly 2,300 s for all 81 against the approved 1,800 s cap. The cap is not raised. The 54 final checkpoints, which carry every registered flag, run first (parent/seed ascending, fixed then learned); the 27 shared step-0 checkpoints, which are descriptive, run afterwards in the remaining budget. Any step-0 checkpoint not reached is recorded as unexecuted and reported.
7. **Engineering gate (iv), reading.** A disagreement between the frozen and the float64 reference stops the study when their selected ID *sets* differ and the reference boundary gap (8th minus 9th score, in score units after division by the temperature and including the prior) exceeds 1e-5. Differences in order only, with equal sets, are listed with the smallest adjacent reference gap among the top 8 and do not stop the study; they reflect float32 versus float64 ordering of near-equal selected scores and do not change which slots are selected.
8. **Trained slot.** A slot counts as trained if its key or its value differs bitwise from the paired step-0 snapshot; key-only, value-only and both are also counted. Coverage is undefined for step-0 checkpoints.
9. **Recall restricted to trained reference slots** is reported two ways: the mean over queries that have at least one trained reference slot, and the pooled ratio.
10. **Exactness certificate** uses "≥" as written in §4.3. A certified query with recall below 1 is counted and reported; with "≥" this can only arise from an exact tie.
11. **Lost-candidate margins** are reported against X16P only, where scores are on the same scale as T2P; for X16N counts, branch ranks and trained status are reported.
12. **Additional stop conditions** beyond §4.3 and §4.6, all integrity checks: T2P concentration statistics not reproducing the P5 record; queries or route scores differing between rules on the same checkpoint; any change to module state or RNG.
13. **Per-checkpoint cap** of 60 s applies to the whole worker process, including imports, restore and replay.
14. **Float64 reference** rejects non-finite inputs and does not renormalize the already normalized float32 query, matching the frozen code's use of the query as given.

### Pre-outcome decisions on the independent pre-freeze audit (recorded before the freeze and before any P6 outcome)

The auditor role's pre-freeze audit is `docs/reviews/p6-preflight-2026-11-13/AUDIT.md` (1 blocker, 2 major, 11 minor, 13 notes; none in the retrieval mathematics). The lead's decisions, none of which changes a registered quantity, threshold, variant, tolerance, workload or cap:

15. **Blocker B1 fixed.** P6-Q flags are computed from the 54 final checkpoints alone and reported INCOMPLETE if any final is missing. Step-0 results are summarized over the checkpoints that completed, with unexecuted ones listed. No checkpoint is started with less than the per-checkpoint cap remaining; it is recorded as unexecuted.
16. **M1.** The search-width curve is computed from the X16P candidate scores already captured in route-rank order (visit-k candidates are the first 256·k columns), selected with the frozen `stable_top`, with a first-batch cross-check against `tree_candidates(visit=k)` on every checkpoint. Same quantity, less repeated work.
17. **M2.** A registered stage cannot be run twice without an explicit recorded supersede and reason, and the analysis asserts that the confirm, screen and equivalence runs it reads belong together.
18. **Minor items 1, 2, 4, 6–11 fixed as suggested.** In particular a variant that violates the tie rule on the constructed-tie fixtures is NOT EQUIVALENT, and a missing comparison scope counts as NOT EQUIVALENT.
19. **Integrity replay in timing workers (minor 3).** Each timing worker replays the recorded P5 NLL bitwise for every checkpoint it restores, outside all timed regions, before measuring.
20. **Flat comparator rule, reading.** "Lowest W8 `addition_forward` median in T-screen" is the median across the 27 workers of each worker's median.
21. **E-H3 / E-H4 wording.** A prediction holds if the criterion passes for at least one tree kind with an EQ-passing selected variant; it is undecided if none passes and any verdict is INCONCLUSIVE or INCOMPLETE; otherwise it fails. Per-kind verdicts are always reported.
22. **T3 as implemented** scores branch blocks with a batched product over 2N blocks of 256×16. The auditor found it arithmetically identical to T2 on synthetic tensors on this build, so it may measure layout and guard cost more than a different contraction. It is left as implemented; T4 and T5 are the gather-free variants.
23. **Cache binding in timed calls** uses an O(1) fingerprint (storage address, version counter, shape) with a full hash check before and after each timing schedule; it would not detect a `.data` write between those checks. The equivalence stage uses the full hash on every call. `slot_offsets` (an index range) is an additional load-time cache in tree variants.
24. **Wtok equivalence** is computed and reported but is not part of the EQ gate, which is (a), (b) and (c) as §3.3 states.
25. **Loader smoke test.** Because the real-checkpoint loading paths cannot be unit-tested without real fixtures, a `loader-smoke` command restores one real cell per study and replays the unmodified model's recorded P5 NLL, computing no P6 quantity. It is run once before the freeze to confirm the loaders work.
26. **Per-token split caveat.** Positions are split by whether their own selection changed. Because later positions attend to earlier ones, "unchanged" positions are not counterfactually untouched; the split is descriptive.
27. **Exposure disclosed.** During implementation and audit, variants were run and timed on synthetic random tensors only (dry runs and budget checks). Those runs showed, on synthetic tensors, the successive-maxima kernel slower than `topk` on flat's 4,096-wide rows and faster on the tree's 512-wide rows. No variant, comparison or fidelity quantity has been computed on any real checkpoint. Real-checkpoint contact so far: restore and unmodified-model NLL replay of three cells by implementers.

### Freeze record (before any P6 outcome)

28. **Re-audit.** The auditor role's re-audit (`docs/reviews/p6-preflight-2026-11-13/REAUDIT.md`) reports B1, M1, M2 and minors 1–11 fixed, no blocker or major finding, and recommends READY TO FREEZE. Its five new minor findings are accepted as follows, without code change: (1) if a P6-E timing stage fails, the analysis ends failed with no criteria — accepted; such a result will be reported as criteria not evaluated; (2) P6-Q flags would show as computed even if a gate violation stopped the suite in a step-0 cell — accepted; any gate violation will be reported prominently and the flags treated as unreviewed until the violation is explained; (4) the descriptive "first call after load" is taken after the integrity replay, so it is model-warm in the sense of an earlier full-panel pass — it is reported with that caveat; (5) the P6-Q time margin is unproven on real cells — accepted under clarifications 6 and 15; (3) is procedural: **no file under version control, including documentation, is edited while a P6 stage runs.**
29. **Flags when a final is missing.** If any of the 54 final checkpoints is missing or incomplete, all P6-Q flags and paired differences are INCOMPLETE for both tree kinds.
30. **Loader smoke outputs** recorded before the freeze: `docs/reviews/p6-preflight-2026-11-13/loader-smoke-p6e.out.txt` and `loader-smoke-p6q.out.txt` (cell b103-o303, seed 503; restore, hash check and unmodified-model bitwise NLL replay only). An earlier smoke run by the implementer on b101-o301 seed 501 found and fixed a loader defect; its output was reported in the session and not saved to a file.
31. **Execution.** One invocation each, in this order, with nothing else running from this session during a stage: P6-E `equivalence`, `screen`, `confirm`, `analyze`; then P6-Q `run`, `analyze`. The freeze is the commit that contains this record; its hash and the source hashes are written into every stage manifest.

## 8. Outcome record (2026-11-13)

Each study was executed once from freeze `a786c5d`; raw records were committed as `c389fe7` before interpretation. Review and independent recomputation: `docs/reviews/p6-results-2026-11-13/` and `docs/reviews/p6-results-audit-2026-11-13/`.

- **P6-E.** EQ: PASS for all seven variants on every checkpoint (F1, F2, T1, T2, T3 STRICT; T4, T5 BOUNDED with zero selection mismatches). E-H1 and E-H2 held. **SP, PAR and PR: INCONCLUSIVE for both tree kinds**, because 344 of 1,296 confirmation timing records failed the registered stability rule; E-H3 and E-H4 are undecided. Every numeric clause was met at the primary workload (T5/T0 0.292 / 0.286; T5/F1 addition 0.747 / 0.729; forward 0.812 / 0.789), which the registration does not allow to be reported as a pass. Nothing was re-timed. At 64 queries and at one query per call the optimized tree was slower than flat.
- **P6-Q.** FID: FAIL (recall 0.791 fixed, 0.915 learned). COS: FAIL. LOSS: FAIL (exhaustive search changed NLL by +0.00044 / +0.00002). PRIOR: FAIL on magnitude (+0.00386 / +0.00393, positive in all 54 checkpoints). Permitted interpretation: the restriction changes the selection, these weights do not predict better with exhaustive search, and whether training with wider search would help is not answered. 16 of 27 descriptive step-0 checkpoints ran; 11 were unexecuted when the budget ended.
- The combination "EQ passes, timing inconclusive" is not a row of the §5 decision matrix. No recommendation in that matrix is triggered.
- P5's L and composite outcomes are unchanged. No training, capacity, SSD, merge or publication step is authorized. Astra review: NOT_PERFORMED. Human review of these results is pending.
