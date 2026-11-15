# ADR-0017 — Parallel Useful-Capacity, Anti-Collapse, and Locality Diagnostics

**Date:** 2026-11-14  
**Status:** **DRAFT — PENDING SCIENTIFIC AUDIT AND HUMAN APPROVAL. NO TRAINING OR EVALUATION AUTHORIZED BY THIS DRAFT.**  
**Proposed research lead:** Claude Fable 5.2 under a *study-specific* delegation only, subject to approval. **Astra review: NOT_PERFORMED.**  
**Implementation:** Sonnet 5.5; independent mathematical, code, and result audit: Opus 5.5; read-only provenance support: Haiku 5.5. Record actual model/session metadata; substitutions must be disclosed. ADR-0012 remains pending.

## 1. Motivation and evidence boundary

ArborLM's target is **useful learned capacity that grows faster than active computation and physical I/O**. P4 demonstrated useful sparse memory on frozen backbones. P5–P7-B found no compelling advantage of the current fixed, one-level hierarchy over strong flat alternatives at 4,096 slots. P8 tried differentiable locality objectives on the same underutilized memory: the standard flat and learned-tree references used roughly 127 and 84 entropy-effective slots respectively, and regularized cases used **46–92% fewer**. Page misses decreased largely by concentrating access; null misses also vanished, leaving the registered beyond-popularity locality metric undefined. The registered P8 study remains **INCOMPLETE (55/60 simulated)** despite the separately approved five-cell supplement. No P8 case established locality-positive behavior.

Therefore **capacity utilization must be established before locality can be scientifically evaluated**. A stronger routing-entropy score is not enough: every claimed useful slot must contribute to solving a task, and simply distributing accesses or adding unused parameters is not a success. One memory size and one small repeated corpus cannot establish H5.

## 2. Primary questions and falsifiable hypotheses

- **H17-CAP (useful capacity):** On independent, high-entropy associative tasks with increasingly many facts, increasing accessible memory slots improves *held-out-query* accuracy/negative log-likelihood at controlled examples, update counts, and storage costs, and the improvement disappears under relevant memory ablations. Failing to improve against flat and non-neural retrieval controls is a negative result.
- **H17-UTIL (avoid collapse):** An explicitly bounded usage-preserving method maintains meaningful use of trained memory **without** sacrificing verified task performance. Raising selection entropy without preserving per-fact accuracy fails.
- **H17-LOC (locality beyond popularity):** Conditional on a model actually using many useful slots, a locality-aware objective reduces **null-adjusted** page misses versus a **separately optimized co-access flat baseline**, at comparable quality and useful-slot utilization. Raw misses, entropy reduction or branch grouping alone do not establish H3.
- **H17-INC (incremental acquisition):** Training a second disjoint family of facts in a versioned memory update improves B-fact accuracy while retaining A-fact accuracy, relative to matched rehearsal/adapter/retrieval baselines. Passing file-version consistency alone is not continual learning.

**All hypotheses are scoped to this testbed.** No result supports claims about billions of useful parameters, teacher-model absorption, real SSD I/O, real token/sec, general reasoning, or production safety.

## 3. Four parallel workstreams with separate claims

Parallelize **implementation, synthetic reference calculations, data generation, provenance checks and isolated experiments**. Do **not** have agents simultaneously change frozen scientific code or share mutable checkpoints. Each workstream has a distinct result directory, analysis script, and independent Opus audit. Dependency gates are explicit:

| Lane | Purpose | Can start after common freeze? | Gate to scientific interpretation |
|---|---|---|---|
| A — Capacity pressure | Design an oracle/reference and train flat/tree memory at multiple sizes | Yes | Correct facts/labels and demonstrably useful memory |
| B — Optimization and collapse | Compare bounded regularizers against matched baseline, diagnose key gradient coverage and optimizer effects | Yes | Quality and useful-utilization safeguards |
| C — Locality and physical layouts | Page simulations, count-preserving nulls, strong co-access flat layout; synthetic layout controls | Yes, using **synthetic** traces | Trained-model locality claim only after Lane A capacity gate and B guard pass |
| D — Incremental learning | Sequential fact sets A then B, versioned state, replay and forgetting comparisons | Yes, using independent synthetic sets | Tested useful knowledge, retention, and consistent versions |

Lane C may report valid algorithmic **synthetic** results even if trained-model gating fails, but must state **H17-LOC NOT EVALUATED** in that event. No post-hoc promotion of a passing subset to an aggregate result.

## 4. Ten diagnostic scenarios (predeclared questions, not an adaptive model search)

| ID | Experiment | Crucial baseline / failure interpretation |
|---|---|---|
| **D01** | Associative-memory oracle on 4K, 16K and 64K slots; deterministic exact lookup | Validates task/data difficulty and the attainable ceiling |
| **D02** | Same frozen backbone + flat learned memory at 4K, 16K, 64K | Size without improved quality = capacity scaling unsupported |
| **D03** | At 16K, compare flat, fixed tree and learned tree | A tree must beat strong flat after accounting for active work and quality |
| **D04** | Fixed number of facts across all sizes | Tests whether extra empty slots alone help; should not be mistaken for useful capacity |
| **D05** | Proportional number of independent facts at every size | Main capacity-pressure comparison; verify exposure/compute budgets |
| **D06** | Oracle-routed and ordinary-routed memory | Separates representation/capacity limit from route-selection failure |
| **D07** | Flat and tree with a **bounded** utilization-preserving objective; zero-penalty controls | Entropy inflation, gate suppression, or forgotten facts = failure |
| **D08** | Flat and tree with utilization preservation **plus** locality objective | Compare null-adjusted misses with optimized flat co-access, at matched utility |
| **D09** | Trace simulations across cache sizes, hypothetical row widths and key-in-RAM vs key-on-storage assumptions | Null floors, row-size accounting, hit rates and simulated I/O; **no NVMe claims** |
| **D10** | Sequential fact-set A → B training with immutable snapshots and replay/adapter/exact-retrieval baselines | Measures acquisition, retention, cost and version correctness separately |

These are **ten diagnostic families**, not ten training cells. Their *exact* crossed architecture × seed × size × objective matrix, number of repetitions, budget and primary contrasts must be frozen in the reviewed experiment config **before any outcome**. The lead may remove a scientifically redundant or infeasible branch **only before the freeze and with documented human approval**, not after seeing results. Use at least two predetermined initialization seeds for trained comparisons and preserve pairing across interventions. Factorial/shared-parent data are correlated, not independent model replications.

## 5. Task and data contract

Build **two distinct task families**, both deterministic and generated entirely locally, with data-generator source and seeds frozen before training:

1. **Independent associations:** pseudorandom identifiers and pseudorandom target labels/short strings, independent of identifiers. No exploitable rule from ID to value. Evaluate *seen facts in previously unseen prompt templates/contexts*, separately from unseen-fact controls which should be near chance. Distinguish memorization/retention from generalization. Train and evaluate with equal key/fact-frequency options; avoid assigning identity labels that let the input tokenizer trivially decode outputs.
2. **Structured/compositional access:** two or more independently stored associations must be combined to answer a query. Include explicit single-hop and two-hop scores to determine whether increased memory supports computation rather than merely a lookup table. Require an exact external-retrieval baseline.

For the **proportional pressure track**, propose 2,048, 8,192 and 32,768 independent fact associations for 4K, 16K and 64K slots respectively. These counts are provisional and require a full-size throughput rehearsal and mathematical review; change them *before* freezing if the 64K cell is infeasible. No interpretation is allowed if the task-generator leakage checks, coverage checks or factual oracle fail.

Use separate splits of fact IDs where appropriate, prompt templates, and evaluation query seeds. Crucial distinction: **unseen prompts about taught facts** test retained knowledge; **unseen random facts** cannot be answered without additional information and test leakage rather than memory competence. Freeze test-set identities and hashes before fitting. No novel teacher LLM calls, new corpus downloads or third-party data are needed for this phase.

Separately, report one fixed-task-size track and one proportional-fact-count track; never compare their quality differences as though compute and data exposure were matched. Report examples, tokens, optimizer updates, unique facts, exposure distribution and wall time for every cell. Include a deterministic exact key–value retrieval control and a parameter-matched dense/adapter control for learning claims.

## 6. Model, controls and budget fairness

Keep the historical P1–P8 mathematics and records immutable. New isolated source modules may reuse the verified frozen-backbone interface. Preserve FP32 CPU reference correctness, with optional MPS acceleration **only if** numerically validated and reported as a separate hardware stratum. Never mix MPS and CPU results in a paired quality comparison without a verified equivalence plan.

- Define a fair flat and fixed/learned-tree capacity scaling rule **before** implementation: record branch count, partition size, router width, visited branches, candidate counts and actual active work at each memory size. The current 16-branch design does *not* guarantee sublinear retrieval as N grows; do not claim it does.
- Frozen-backbone and memory checkpoints are immutable inputs. No optimizer history may silently carry from another case. Report every trainable parameter, initialized slot and optimizer state byte.
- At each size, preserve both **fixed training compute** comparisons and **matched examples per fact** comparisons as separate estimands. A model given 16× as many facts is not compute-matched to a model trained on the original fact set.
- If different sizes are too costly to train locally, Lane A may finish as a **synthetic oracle + engineering throughput** result, not a claim about trained capacity.
- Measure utilization as unique selected slots, entropy-effective slots, slot visitation by fact, learning-gradient/update coverage, trained-versus-disabled value effects, and per-shard/slot-group ablations. An increase in active slot count without positive task contribution does not establish usefulness.

## 7. Address P8's objective/optimizer failure explicitly

P8 used step-wise gradient-norm matching with a locality coefficient λ that increased to roughly 6×10^5 after the proxy saturated, while AdamW updated sparse-key coordinates that had no language-loss gradient. **Do not reuse this as a safety guarantee.**

Preregister two matched alternatives: **(a)** standard loss with no locality penalty, **(b)** a static or explicitly capped coefficient with a separately specified utilization floor/constraint. If testing a dual/augmented Lagrangian method, register hard bounds on multiplier values and update norms and compare it with (b). Include dose zero and a *small prespecified* dose set; no response-dependent coefficient search or selection.

Independent tests must measure actual parameter movement in key/value/router groups, compare `g_L` and `g_reg` on selected and unselected slots, detect the rank-8/9 margin saturation mechanism and verify that a null/collapsed routing pattern is not accepted as useful capacity. Differentiate soft proxy gradients from discrete top-k and page assignment. An added load-balancing loss is **not** a sufficient cure unless per-fact competence and ablation dependence survive.

## 8. Locality simulator and nulls

Reuse P7-B's audited value-page simulation with **fair optimized flat co-access placement**, frequency packing, branch-constrained placement and random-partition controls. For the main trained locality comparison:

- Fit layouts only on a calibration stream; evaluate on separately frozen panels. Do not fit or choose layouts from evaluation access patterns.
- Use the exact count-preserving null for degenerate fixed-eight-slot streams (ADR-0016). This is a narrowly proven identity case, not permission to alter the general generator.
- Set cache capacities relative to *measured useful working sets* via a prespecified rule from training/calibration data, keeping each comparison nondegenerate; do not choose settings after inspecting model evaluation misses. Report cache-to-working-set ratio for all cells.
- Evaluate actual versus null misses, null denominator, utilization, per-query pages, within-query co-selection and temporal reuse separately. If the null miss floor is not met, record **UNIDENTIFIABLE/DEGENERATE** rather than a win.
- Keep key-index traffic, values traffic, metadata and cache placement separate. Any key-on-storage test is a new corrected simulation with strict cache-capacity invariants, not the known-invalid P7-A key table.
- Both eviction-tie rules and independent recomputation are required. Simulation cannot prove physical I/O, throughput or H4.

## 9. Incremental learning and multi-teacher relevance (Lane D)

Use two deterministic **oracle teachers** exposing disjoint sets of correct associations, A and B; this is a *mechanistic rehearsal*, **not** successful absorption of real language models. Keep the same backbone. Train A, snapshot V1, then train B from V1, snapshot V2. Compare: (i) new B accuracy, (ii) retained A accuracy, (iii) old/combined validation, (iv) memory regions actually updated, (v) active lookup work, (vi) training examples/updates and (vii) bytes written to publish version V2. Compare memory-only updates against rehearsal, full adapter fine-tuning and exact retrieval.

Use immutable copy-on-write snapshots and atomic manifest publication only in a **local simulated store**. An inference worker must pin V1 while a separate training worker prepares V2; verify no mixed index/value versions, replay equivalence and rollback. This is a *version-consistency test*, not a claim of productive continual learning or NAS/SSD viability.

## 10. Prespecified outcome classes and hard boundaries

The reviewed ADR must finalize numeric thresholds, denominators, expected exposure counts and a complete decision table **before any learned-model outcome is observed**. Required classification for every lane:

- `ENGINEERING_FAIL` — identity, gradient, deterministic correctness, reproducibility or checkpoint integrity broken.
- `INCOMPLETE` — any mandatory registered cell omitted, even when other cells have interpretable records.
- `CAPACITY_POSITIVE` / `CAPACITY_NOT_SUPPORTED` — paired task gains against matched baselines, with useful-slot attribution and utilization at multiple sizes.
- `UTILIZATION_PRESERVED` / `COLLAPSED` — usage plus held-out knowledge retention; entropy-only success forbidden.
- `LOCALITY_POSITIVE` / `CONCENTRATION_ONLY` / `DEGENERATE` — positive only beyond count-preserving null and optimized flat, at retained predictive quality and useful utilization.
- `INCREMENTAL_POSITIVE` / `FORGETTING` / `NO_NEW_CAPABILITY` — based on A/B performance and update costs, not stored parameter count.

**Hard interpretation hierarchy:** if capacity usefulness is unestablished, report locality as *diagnostic only*; if utilization collapses or the null is degenerate, locality cannot pass; if quality drops outside the fixed guard, locality cannot pass; if the flat comparator is absent, hierarchy advantage cannot pass. Never treat a failed preregistered gate as a successful partial result. Report medians, full distributions, parent-level paired contrasts and failures; shared parents and datasets preclude naïve independent-replicate confidence intervals.

The decision after this phase is one of: (1) capacity works, proceed to a separately approved capacity-scaling protocol; (2) useful capacity works but locality doesn't, redesign placement/routing; (3) route/optimization cannot learn sufficient capacity, investigate representation and training objectives; (4) neither works, pause the architecture line. No result automatically authorizes next-phase training, SSD testing or scaling.

## 11. M5 Max execution and resource contract (proposal)

- Hardware target: M5 Max, 48 GB unified memory. First benchmark synthetic full-size cells and measure CPU/MPS memory, throughput and thermal/load sensitivity. This is not a guaranteed performance envelope.
- **Parallelize bounded independent CPU simulation tasks**, up to four workers *if measured* within a proposed 8 GiB aggregate RSS ceiling. Permit at most two concurrent training workers under the same tested aggregate cap. **Isolate any timing/latency microbenchmark**: no other study workers, no unrelated load, and record workload stability. P6 demonstrated that loaded-machine timing is unreliable.
- Proposed cap: **2 GiB sampled RSS per worker**, **8 GiB aggregate**, and **8 hours total charged active execution** for the bounded pilot; no cloud spending or new data. Exact stage caps must be determined from full-size rehearsal and approved before execution; require at least 2× projected headroom per stage. Larger sizes may be reduced *only before the freeze* and with human approval.
- Job manager maintains immutable task IDs, stage manifests, explicit hardware assignment, a concurrency semaphore, output directory separation, shared source/config/data checksums, and all-failures-preserved semantics. A worker failure triggers **no new dependent work**; unrelated lanes may continue if explicitly specified before the freeze. Do not retry with changed settings.
- Keep Git operations, raw result publication and PR creation outside high-load timing sections. No automatic merges. Preserve all P1–P8 outcomes and the P8 supplement as separately labelled.

## 12. Scientific and engineering preflight

Before execution, Fable must produce a revision with: exact matrix and seed list; task generator specification; fact ID/templating/hashing rules; primary panels and null identities; complete formulas for bounded usage and locality objectives; exact quality/usefulness/utilization thresholds; reference baseline algorithms; worker-level stage budgets; complete stopping and decision rules.

Opus must independently check: unbiased/specified task generation; no train/eval leakage; expectation for unseen random facts; oracle correctness; gradient reach and optimizer state; capacity-per-fact exposure; null generator including full collapse; page simulator and cache capacity; CPU/MPS parity if relevant; the reproducibility and budget controls. Run synthetic smoke tests that deliberately trigger collapsed, unidentifiable and incomplete outcomes. Only **after independent READY TO FREEZE** and **explicit human approval of the final revision** may a scientific run begin.

## 13. Evidence, audit, and delivery

Source freeze and panel/hash manifest precede all scientific outcomes. Preserve raw training logs, actual gradient/movement norms, checkpoint hashes, trace IDs, nulls, simulations, all negative/incomplete outcomes and environmental provenance. Do not commit restricted corpus bytes, teacher outputs without rights review, or huge checkpoint binaries. Opus's recomputation must use raw records and a separate analysis implementation; disclose any code/tooling written earlier by the auditor.

Deliver a draft PR containing the reviewed ADR and isolated code, verified freeze and run logs, `RESULTS.md`, reproducible JSON/CSV, and an HTML dashboard including: capacity-versus-quality curves, slot-use/quality scatter, per-fact exposure and recall, entropy and unique-slot coverage, router/gradient heatmaps, null-adjusted locality by layout/cache, optimizer coefficient and key movement traces, and sequential A/B retention/forgetting curves. The lead must explain which question each plot answers. Keep the PR draft; **do not merge without explicit approval**.

## 14. Decisions reserved for the human lead

1. Approve or amend **this ADR's exact final matrices and numerical gates**, after Opus review; this draft is **not** permission to train.
2. Approve the total time/RSS budget and any MPS use after full-size dry-run evidence.
3. Approve study-specific Claude delegation; ADR-0012 remains undecided and Astra review not performed.
4. Approve any external dataset, teacher-model weights, paid compute or physical SSD experiment separately.
5. Approve merge, publication, capacity expansion and the next research phase separately.

**Disposition:** Awaiting agent design revision and independent review. No run authorized.
