# ADR-0013 — P7-A: storage-page locality of the existing P5 memories (trace-driven simulation)

- Date: 2026-11-13 (America/Panama).
- Status: **DRAFT PROPOSAL, REVISION 2 — SPEC: PENDING HUMAN REVIEW (Fable-drafted, Opus-reviewed). NOT APPROVED. NO IMPLEMENTATION, TRACE GENERATION, SIMULATION OR MODEL FORWARD IS AUTHORIZED BY THIS DOCUMENT.**
- Prepared by Claude Fable 5.2 (`claude-fable-5-2`) at the human research lead's request of 2026-11-13. Revision 1 was reviewed by the auditor role (Claude Opus 5.5): `docs/reviews/p7a-spec-review-2026-11-13/REVIEW.md`, 2 blockers, 8 major, 11 minor. This revision answers that review; §12 lists what changed and what was not adopted. **Astra review: NOT_PERFORMED.** ADR-0012 (review arrangement) is still awaiting the human lead's decision.
- Scope: a bounded simulation on the **existing frozen P5 checkpoints**. No training, no change to weights, routing, scoring or model quality, no SSD or NVMe device, no new CPU optimization, no capacity change, no downloads. P1–P6 code, records, thresholds and outcomes are immutable. **P6-E's timing verdict is INCONCLUSIVE and stays so**; nothing here re-times or reinterprets it.

## 1. Why this study, in light of H3, H4 and H5

The project's motivation was storage bandwidth: token rate is bounded by storage bandwidth divided by bytes read from storage per token (`docs/RESEARCH_HANDOFF.md` §1.1). The hypotheses that carry it are H3 (locality-aware training reduces physical storage traffic), H4 (on NVMe, savings in transferred bytes outweigh routing and page-fetch overhead) and H5 (I/O grows more slowly than stored memory).

P5 and P6 measured something else: CPU time of retrieval with every tensor in RAM, at 4,096 slots. In that regime flat memory costs one small matrix product and a top-k, and nothing is read from storage. The follow-ups the lead listed after P6 (a fresh confirmation timing, single-token CPU timing, more flat optimization) would all have stayed there. **The human lead's observation is correct: that line was drifting from the original motivation.** A tree could be slower than flat on a CPU and still read fewer bytes from a slow device, or faster on a CPU with no I/O advantage at all. Neither P5 nor P6 says which.

A hierarchy could help storage in two distinct ways, which must not be confused:

1. **Fewer index reads.** If keys live on storage, flat search reads every key and a tree reads the keys of the branches it visits. True by construction, independent of anything learned, and gone if keys fit in RAM, which they usually can because keys are much smaller than values.
2. **Better value locality.** Every architecture reads eight value rows per query. A tree reads fewer *pages* only if the rows it selects sit closer together on storage, or recur more across consecutive queries, than flat's do.

There is a third thing that can masquerade as the second: **using less of the memory.** P5 already showed the trees select fewer distinct slots than flat (effective slots 132 flat, 96 fixed, 83 learned). A model that concentrates on fewer rows touches fewer pages whatever its structure, and P5 found that concentration came with no quality benefit. P7-A must separate this from genuine locality, or it would report lower utilization as a storage advantage.

Fewer key comparisons is none of these.

**What P7-A can and cannot say about H3–H5.** No locality objective was ever trained, so this measures the locality that arose without one: a baseline for H3, not a test of it. It is a screen for H4, not a test: page counts under a simple model are not device behaviour. It cannot address H5: one memory size is one point.

## 2. The scale problem, and what it means for the NVMe question

The whole addition is 768 KiB: keys 256 KiB, values 512 KiB. Each checkpoint selects only 221–555 distinct slots over the whole panel. From the published P5 selection histograms, the auditor computed that with hot rows packed together, the rows accounting for 99% of selections occupy **3 to 10 pages of 4 KiB**.

Two consequences are fixed here, before any trace exists:

- **An NVMe experiment on these checkpoints cannot be informative, whatever P7-A finds.** A 512 KiB value store sits entirely in the operating system's page cache after the first pass; a device run would measure that cache. P7-A therefore cannot justify an NVMe run on the existing checkpoints. The most it can justify is *proposing a storage study at a memory size where storage matters*, which needs new training and its own approval.
- **At the actual row size the cached-read question is close to trivial.** Any cache large enough to serve one query holds most of a packed working set. Revision 1's cache sizes would have put every architecture at zero misses, so its main criterion would have been decided by ties.

P7-A is therefore a study of **access structure**: which rows are touched together and how often they recur. Block size affects a page model only through **rows per page, R**. The study is parametrized by R, and the informative regime is small R, where a page holds few rows, as it would for the large value rows a storage-scale memory would have.

| R, value rows per page | Corresponds to | Value pages | Pages per branch |
|---:|---|---:|---:|
| 512 | actual 128 B rows, 64 KiB blocks | 8 | 0.5 |
| 128 | actual rows, 16 KiB blocks | 32 | 2 |
| 32 | actual rows, 4 KiB blocks | 128 | 8 |
| 8 | **hypothetical** 512 B rows at 4 KiB | 512 | 32 |
| 2 | **hypothetical** 2,048 B rows at 4 KiB (the handoff's illustrative 1,024-dim FP16 value) | 2,048 | 128 |
| 1 | **hypothetical**: one row per page | 4,096 | 256 |

R = 32, 128 and 512 are the three block layouts requested, at the true row size. R = 1, 2 and 8 change no selection and no weight; they relabel bytes per row and are marked hypothetical wherever they appear. Key rows are 64 B: 64 / 16 / 4 key pages at 4 / 16 / 64 KiB.

## 3. Material and integrity rules

- **Checkpoints.** All 81 final (step-512) P5 memory snapshots — 27 flat, 27 fixed-tree, 27 learned-tree — from suite `P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be`. No subset, no selection. Strict restore; state hash checked against the P5 record before and after.
- **Model.** The unmodified frozen `pilot_model.Memory` inside the unmodified P5 model. No P6 variant. Before a trace is taken the model must replay that cell's recorded P5 final NLL **bitwise** on the P5 panel; a mismatch stops the study.
- **Traces.** Per query, in stream order: the eight selected slot IDs in the order returned, and for trees the two visited branch IDs in rank order. Nothing else from the model enters the simulation. Trace generation is the only step that runs a model. The simulator must consume queries in exactly the registered stream order (context by context, position 0 to 63), regardless of how the model was batched to produce them.
- **Streams.** Each context is a 64-byte window and contributes 64 queries in position order.
  - **Evaluation stream:** the P5 panel, validation ranks 2048–2559 in rank order (512 contexts, 32,768 queries).
  - **Calibration stream:** ranked training-pool chunks 2048–2559 (512 contexts). Neither the additions nor the frozen backbones trained on these ranks (training used ranks 0–2047), and they are disjoint from every validation panel. Already local and hash-verified. Used only to fit layouts. It comes from the training split and the evaluation stream from the validation split, so how well a fitted layout transfers between them is part of what is measured.
- **What the streams are not.** Contexts are ordered by a hash rank, so neighbouring contexts are unrelated windows of text. Temporal structure exists only within a context's 64 queries; attention restarts at each context, and the first query of a context depends on a single byte. This is teacher-forced evaluation, not generation, and not a continuous document.
- **"Identical query traces"** means the three architectures of a parent/seed receive identical input bytes in identical order. Their query vectors differ, because each addition trained its own query projection. That is inherent in comparing trained models.
- **Environment.** CPU float32, deterministic algorithms, single thread, unchanged `uv.lock`. The simulation is integer bookkeeping and is not timing-sensitive.
- **Process.** Human approval → implementation by the implementer role → audit by the auditor role, including an independently written simulator → source/spec freeze commit → single registered invocation → independent recomputation → review. Failed runs and failed checker attempts are kept.

## 4. Physical layouts (fixed list)

A layout assigns each slot a position 0…4,095; the row at position p lies in page `floor(p / R)`. Keys and values are separate stores with separate layouts.

| ID | Applies to | Definition | What it represents |
|---|---|---|---|
| **L-ID** | all | Position = slot ID. | Natural layout. For trees this is **contiguous branch placement** (branch b at positions 256b…256b+255). For flat, slot IDs carry no structure, so it is an arbitrary fixed layout. |
| **L-RAND** | all | A fixed pseudo-random permutation; three registered seeds (91101, 91102, 91103); metrics averaged over the three. | **Slot-wise placement**: each slot placed independently of its branch. |
| **L-FREQ** | all | Slots sorted by descending selection count in that checkpoint's own calibration trace; ties by ascending slot ID. | The cheapest post-hoc layout any system could apply. Needs no hierarchy. |
| **L-BFREQ** | trees | Branches contiguous in branch-ID order; within each branch, slots by descending calibration count, ties by ascending slot ID. | Branch placement with hot rows packed inside each branch. |

**The primary comparison uses L-FREQ for every architecture.** One rule, applied identically, so that neither side gets to choose. Revision 1 let trees pick the best of three layouts while flat had one; that favoured the trees and is removed. L-ID, L-RAND and L-BFREQ are reported for what they show about placement.

Key-store layouts: L-ID and L-RAND only (trees read whole branches of keys; frequency order is meaningless for an exhaustive flat scan). Key and value layouts are not crossed: the key store has its own cache (§5).

## 5. Access model (every assumption explicit)

All quantities are counts under this model. None is a device measurement.

**What a query reads.** Values, every architecture: the pages holding its eight selected value rows. Keys, flat: every key page. Keys, tree: the pages holding the 512 key rows of its two visited branches. Router (16 × 16 floats, 1 KiB): always in RAM and never counted, which favours the trees by one kilobyte. Query and output projections, gate and backbone are in RAM and outside the model.

**Index regimes.**

- **RAM-index (primary):** keys cost no storage reads; only value pages count. This isolates value locality, the scientific question.
- **SSD-index:** key reads are added, from a **separate key cache**. Value-page results are identical in both regimes by construction. Flat's key reads are a full scan of every key page on every query: with a key cache smaller than the key store this is computed analytically as all key pages per query, and with one at least as large it is zero after the first query, which is the RAM-index regime. Tree key reads are simulated. This regime mostly restates the by-construction fact of §1 and is labelled analytical; it carries no criterion.

**Per query, no cache.** Distinct value pages touched (1 to 8) and its distribution; distinct key pages (SSD-index); **uncached read amplification** = bytes of distinct pages ÷ bytes of rows needed (8 value rows; 4,096 or 512 key rows).

**Uniform analytical reference.** For k rows drawn uniformly without replacement from N candidate rows, with m_j of them on page j:

`E[distinct pages] = Σ_j [ 1 − C(N − m_j, k) / C(N, k) ]`

(with equal pages of R rows on P pages: `P · [1 − C(N − R, k) / C(N, k)]`). For k = 8 at R = 32 this gives 7.79 pages over the whole store and 6.49 over two branches, a ratio of 0.833; at R = 2 the two figures are 7.99 and 7.95. So in the natural layout a tree looks about 17% better than flat per query at 4 KiB purely because its candidates span 16 pages instead of 128, and that advantage vanishes when pages hold few rows. Per-query page counts are reported against this reference and carry **no pass/fail criterion**.

**Cache model.** One cache of value pages with capacity C pages. A query is served as a unit: its distinct pages are determined first; pages not in the cache are **misses**; the query's pages are then all held, evicting the least recently used pages *not used by the current query*. Recency is per query, so order within a query does not matter. C is at least 8, the most pages one query can need, so a query never evicts its own pages.

- Capacities: **C ∈ {8, 16, 32, 64, 128} pages**, at every R. Capacity is stated in pages, with the cached row count C × R shown beside every result, because the cache has to be small relative to what a checkpoint uses for the question to be open.
- **Warm misses per query:** warm the cache on the first 256 contexts of the evaluation stream, count on the last 256 (16,384 queries).
- Every miss is classified: **first-touch** (the page has not been read before in the stream, counting the warm-up) or **capacity** (it was read before and evicted). **The cached metric used by the criteria is warm capacity misses per query.** First-touch misses are reported separately; they measure how many pages a checkpoint ever uses, not cache behaviour.
- Cold misses from an empty cache over the whole stream, and **cached read amplification** (bytes of missed pages ÷ bytes of rows needed), are descriptive.

**Across queries.** Distinct pages per context and over the stream; the cumulative distinct-page curve; and **page reuse**, defined as the pooled fraction (total reused page touches ÷ total page touches) of pages also touched by the immediately preceding query, reported separately for pairs within a context and pairs that cross a context boundary.

**Nulls that separate causes.** Each is run through the same simulator.

| Stream | What it keeps | What it removes |
|---|---|---|
| **Actual** | everything | — |
| **Order-shuffled** (seed 91201) | each query's own set of eight slots | all temporal structure |
| **Frequency-matched independent** (seeds 91301–91303, averaged) | each checkpoint's own slot selection frequencies on the evaluation stream | co-selection within a query and all temporal structure: each query's eight distinct slots are drawn without replacement with probability proportional to that checkpoint's counts |
| **Uniform reference** | the number of rows per query | concentration as well |

The registered decomposition, per checkpoint and metric: uniform → frequency-matched (the effect of **concentration**) → order-shuffled (the effect of **co-selection**, which is where a hierarchy's branches would show) → actual (the effect of **temporal order**).

A context-shuffled stream (contexts in a fixed pseudo-random order, seed 91202) is also run. Since contexts are already unrelated, it is a second arbitrary order and gives an estimate of order variance, not a test.

**Branch locality (trees).** Fraction of consecutive query pairs with the same top-1 branch, and sharing at least one visited branch, reported separately within and across context boundaries; run lengths of the top-1 branch within contexts; distinct branches visited per context; and every value-page metric under L-ID versus L-RAND on the same trace.

**Data sensitivity.** For the order-free per-query metrics, a bootstrap over the 512 contexts (1,000 resamples, seed 91401) gives an interval showing sensitivity to which contexts were drawn. It does not account for the shared parents and seeds.

**Not modelled, and no statement permitted about them:** device latency, sequential versus random read cost, read-ahead, queue depth, request merging, file system and OS page cache, batching across concurrent queries, compression, writes, energy, and optimal (Belady) caching. A page-read count is not a time.

## 6. Predictions (each can fail)

Written before any trace exists. Known beforehand from published P5 records: the slot-utilization figures and the auditor's packed-page estimates in §2.

- **P7-H1.** Under L-FREQ, in the primary setting, trees do **not** show the registered advantage over flat in warm capacity misses; and where they come close, the frequency-matched null reproduces it, meaning it comes from lower utilization. This is the lead's expectation and it counts against a hierarchy-specific storage advantage.
- **P7-H2.** For a tree's own trace, contiguous branch placement (L-ID) gives fewer capacity misses than slot-wise placement (L-RAND).
- **P7-H3.** At R = 32, 128 and 512 (the actual row size) the non-degeneracy condition of §7 fails at most capacities: the hot rows fit in the cache.
- **P7-H4.** Per-query distinct pages in the natural layout track the uniform reference closely, i.e. the per-query tree advantage at R = 32 is mostly the by-construction 0.833.

## 7. Registered criteria

Comparisons are per tree kind K ∈ {fixed, learned} against flat, paired by parent and seed: 27 pairs in 9 parents (3 backbones × 3 batch-order seeds). The seeds index training randomness; all cells share one corpus and one evaluation stream. The consistency counts therefore describe robustness to training randomness only, and are not significance tests.

**Metric.** m = warm capacity misses per query.

**Primary setting.** RAM-index, value store, **R = 2, C = 32 pages** (64 rows cached, against 221–555 distinct slots used per checkpoint), L-FREQ for every architecture, actual evaluation stream. R = 2 is a hypothetical row size; it is primary because it is the regime in which the question is open, as §2 explains.

**Non-degeneracy (checked first, per setting).** A setting is **NON-DEGENERATE** if the mean of m over the 27 flat cells is at least 0.05 per query **and** over the 27 tree cells of kind K is at least 0.01 per query. Otherwise every criterion in that setting is **DEGENERATE** for K: neither pass nor fail, and no conclusion may be drawn from it.

**ADV(setting, stream)** holds when, in a NON-DEGENERATE setting: the mean of m over the 27 tree cells is at most 0.80 times the mean over the 27 flat cells; the tree cell is strictly lower than its paired flat cell in at least 22 of 27 pairs; and the tree's parent mean is strictly lower in at least 8 of 9 parents. A tie counts as not lower. Ratios are between means, never per pair.

- **LRU_K — cached value reads.** ADV(primary setting, actual stream).
- **CONC_K — is it only concentration?** ADV(primary setting, frequency-matched independent stream for both architectures). If this holds, lower utilization alone is enough to produce the advantage.
- **BR_K — branch placement.** In the primary R and C, for tree kind K's own actual traces: the setting is non-degenerate for K under L-RAND; mean m under L-ID is at most 0.80 times mean m under L-RAND; lower in at least 22 of 27 cells and 8 of 9 parent means.

**Outcome for tree kind K:**

| LRU_K | CONC_K | Outcome |
|---|---|---|
| DEGENERATE | — | **UNRESOLVED**: the memory is too small for this setting to discriminate. |
| fails | — | **NO ADVANTAGE** over a frequency-packed flat memory under this page model. |
| holds | holds | **CONCENTRATION-ONLY**: the tree reads fewer pages because it uses fewer rows. Not a property of hierarchical placement, and P5 found the lower utilization came with no quality gain. |
| holds | fails | **STRUCTURAL ADVANTAGE**: fewer cached page reads than flat, not reproduced by utilization alone. |

**Robustness grid, reported in full, never substitutable for the primary setting:** every R in {1, 2, 8, 32, 128, 512} × every C in {8, 16, 32, 64, 128}, with the non-degeneracy status of each cell; L-ID, L-RAND and L-BFREQ for trees; the context-shuffled stream; the SSD-index key reads. A STRUCTURAL ADVANTAGE is described as *robust* only if LRU_K also holds and CONC_K fails in at least one other NON-DEGENERATE setting with R ≤ 8.

The 0.80 ratio, the 0.05 and 0.01 floors and the choice of primary R and C are new design judgments made before observation; they are for the human lead to approve or change.

## 8. Permitted interpretations, fixed before observation

| Evidence | Permitted bounded statement |
|---|---|
| UNRESOLVED | At this memory size the page model cannot tell the architectures apart in the registered setting. This is not evidence for or against hierarchy at larger sizes. |
| NO ADVANTAGE (both tree kinds) | With hot rows packed, the existing trees read no fewer cached pages than flat. Their access structure offers no storage argument for hierarchy at this size. |
| CONCENTRATION-ONLY | The trees touch fewer pages because they use less of the memory. Report utilization beside the result. Whether that is a benefit or a waste of stored capacity is a separate question P7-A does not settle. |
| STRUCTURAL ADVANTAGE, not robust | An advantage beyond utilization appears in one setting only. Treat as provisional. |
| STRUCTURAL ADVANTAGE, robust, for at least one tree kind | The existing hierarchy shows value-locality beyond utilization against a frequency-packed flat memory, in the few-rows-per-page regime, under this page model. This supports **proposing** a storage study at a memory size where storage matters. |
| BR holds | Contiguous branch placement is worth keeping if trees are used. By itself it is not a reason to use them. |
| BR fails | Branch contiguity buys nothing measurable for these traces. |
| Any outcome | No statement about device latency, throughput, large memories, capacity scaling, training or quality. No P1–P6 result changes, and P6-E stays INCONCLUSIVE. Frequency packing is not the best possible flat layout; an advantage over it is not an advantage over co-access clustering. |

**Is an NVMe experiment justified?** On the existing checkpoints: **no, under any P7-A outcome** (§2). What P7-A decides is narrower: whether the existing hierarchy's access structure gives any reason to plan a storage study at a larger memory. The lead will recommend proposing one only on a robust STRUCTURAL ADVANTAGE for at least one tree kind. On NO ADVANTAGE or CONCENTRATION-ONLY the recommendation is that the existing hierarchy does not earn one, and that the storage hypothesis would first need a locality-aware training objective (H3) or a different routing design. On UNRESOLVED the recommendation is that the question cannot be answered at this size. Each recommendation goes to the human lead; none is an authorization.

## 9. Correctness requirements

- Trace integrity: bitwise NLL replay per checkpoint; selected IDs in range and distinct within a query; for trees every selected slot lies in a visited branch; P5's recorded unique-selected-slot count and per-slot selection histogram reproduced exactly from the evaluation trace.
- Layouts are permutations of 0…4,095; L-BFREQ preserves branch membership; L-FREQ and L-BFREQ depend on the calibration trace only.
- Simulator checked on hand-computed traces (capacity exactly 8, a cache larger than the store, repeated pages within a query, first-touch versus capacity classification, the warm-up boundary) and against a second simulator written independently by the auditor role on the full traces of at least three checkpoints per architecture, across all R and C.
- The closed form of §5 checked against Monte Carlo on synthetic draws; the frequency-matched generator checked to reproduce target frequencies.
- Invariants: misses never exceed touches; cold misses are at least the number of distinct pages; capacity misses at a larger cache never exceed those at a smaller one; first-touch misses do not depend on C.
- **Report-only check, not a stop:** flat under L-ID against its three L-RAND layouts. If slot IDs carry no structure the four are exchangeable, so L-ID falls outside the others' range half the time by chance.
- No weight, buffer, RNG state or checkpoint file changes.

## 10. Resource limits, enumeration and stop conditions

Configurations per checkpoint: actual stream on every layout (5 for flat, 6 for trees) × 6 R × 5 C; the four other streams (order-shuffled, three frequency-matched replicates counted as three, context-shuffled) on L-FREQ and L-ID only × 6 R × 5 C. That is about 480 simulations of 32,768 queries with at most eight page touches each, roughly 1 × 10^10 page touches over 81 checkpoints. Flat's key scan is analytical and tree key reads add a small separate simulation. A direct LRU with a hash map and recency list, one pass per capacity, is the prescribed algorithm.

Caps: trace generation ≤ 900 s active worker time; simulation and analysis ≤ 3,600 s; combined ≤ 4,500 s; the auditor's independent simulator has its own cap of 1,800 s and is not part of the study's budget; sampled process-tree RSS ≤ 2 GiB. **Before the freeze the implementer must time the full configuration set on full-size synthetic traces and show it fits the simulation cap with at least a twofold margin; if it does not, the specification returns to the lead for a recorded amendment before anything is run on real traces.**

Traces stay local under `experiments/` with SHA-256 in the compact records; compact per-checkpoint results go under `results/p7a-<date>/`. Stop on: NLL replay mismatch, checkpoint hash change, any trace-integrity or invariant violation, disagreement with the independent simulator, or a resource breach. Partial and unexecuted records are preserved. Configurations are never dropped to fit the budget.

## 11. Alternatives considered

- **Go straight to NVMe.** Rejected: uninformative at 768 KiB (§2), and a device adds effects on top of an access pattern nobody has characterized.
- **More CPU work first.** Deferred: it answers an in-RAM question the storage motivation does not depend on.
- **Co-access clustering layouts.** The strongest post-hoc layout, and the right next baseline if frequency packing leaves a gap. Left out to keep the study bounded; the limit is stated in §8.
- **Optimal (Belady) caching** as a lower bound. Useful, not needed for the registered comparison; omitted.
- **Synthetic larger memories.** Deferred: selections at larger sizes are unknown without training, and random tensors have no learned access structure.
- **Letting each architecture pick its best layout.** Rejected after review: it gives the side with more layouts more chances.
- **Byte-fixed cache capacities as fractions of the store** (revision 1). Rejected after review: every such cache held more rows than any checkpoint uses.

## 12. Independent review of assumptions and the lead's response

The auditor role reviewed revision 1 without running any model: `docs/reviews/p7a-spec-review-2026-11-13/REVIEW.md`, with scripts and outputs. It used the 81 published P5 selection histograms and synthetic draws only. It is independent mathematical and engineering evidence, not Astra validation and not approval.

| Finding | Response in this revision |
|---|---|
| **B1.** With the registered cache sizes every architecture's hot rows fit in the cache; the cached criterion and both halves of PLAUSIBLE would sit at zero and be decided by ties. | Adopted. Capacities are now in pages and small (§5); a non-degeneracy condition and an UNRESOLVED outcome exist (§7); misses are split into first-touch and capacity, and the criterion uses capacity misses; ties count as not lower. The primary setting moved to R = 2. |
| **B2.** Nothing separated lower slot utilization from hierarchy structure; a pass could come from trees simply using fewer rows, and revision 1's §8 wrongly said flat shares that concentration. | Adopted. The frequency-matched independent stream and the registered decomposition are added (§5); CONC_K and the CONCENTRATION-ONLY outcome are added (§7); the incorrect statement is removed. |
| **M1.** LRU broke when one query needed more pages than the cache held. | Adopted: per-query service, capacity at least 8 pages. |
| **M2.** Trees chose among three layouts, flat had one, and the choice was scored on the stream the layouts were fitted on. | Adopted: L-FREQ for every architecture in the primary comparison; no selection step remains. |
| **M3.** A stop condition would fire by chance half the time. | Adopted: report-only. |
| **M4.** The compute plan was not enumerated and probably exceeded the cap. | Adopted: enumeration, prescribed algorithm, analytical flat key scan, mandatory timed dry run before the freeze (§10). |
| **M5.** A shared key/value cache made flat flush the cache on every query by construction. | Adopted: separate caches; value results come from the RAM-index regime. |
| **M6.** ADV had no rule for zero means or ties. | Adopted (§7). |
| **M7.** The NVMe rule was both too permissive and too strict. | Adopted: NVMe on these checkpoints is ruled out in advance; a pass supports only proposing a study at a larger memory; a degenerate setting is UNRESOLVED, not a fail (§2, §8). |
| **M8.** "Resembles reading text" overclaimed; contexts are unrelated. | Adopted: wording corrected; reuse and branch metrics reported within and across contexts (§3, §5). |
| Minor 1–11. | Adopted: closed form registered; PQ dropped as a criterion because its threshold sat just below the by-construction ratio; the duplicate hypothetical-64-KiB setting removed by parametrizing on R; reuse and run-length definitions fixed; cached and uncached amplification separated; backbone training ranks stated; stream-order requirement added; context bootstrap added; auditor time budget set. |
| **Not adopted.** A key-clustered contiguous layout for flat as a structural counterpart to branch placement; optimal caching as a bound. | Left out to keep the study bounded. Both are listed as limits (§8, §11). |

Open points the auditor marked for the lead, decided above and now for the human lead to confirm: the 0.80 ratio; the non-degeneracy floors; the primary R and C; and whether lower utilization should count as a benefit at all (this draft says it is reported, not credited).

## 13. Decisions requested from the human lead

1. Approve, amend or reject P7-A.
2. Accept that **no NVMe experiment on the existing checkpoints is proposed under any outcome**, and that the most P7-A can support is proposing a storage study at a larger memory.
3. Approve the primary setting: hypothetical R = 2 (2,048-byte value rows at 4 KiB), cache of 32 pages, L-FREQ for all architectures. The three requested block sizes at the true row size are measured and reported, and are expected to be degenerate.
4. Approve the cache model (per-query service, capacities 8–128 pages, warm capacity misses) and the layouts, including the omission of co-access clustering.
5. Approve the criteria and outcomes in §7: the 0.80 ratio, the 0.05 and 0.01 non-degeneracy floors, and the rule that an advantage reproduced by the frequency-matched null is labelled CONCENTRATION-ONLY.
6. Approve the calibration stream (training-pool ranks 2048–2559) for fitting layouts.
7. Approve the resource caps and the mandatory timed dry run in §10.
8. Decide ADR-0012 (review arrangement), still open.

## 14. Approval record

*Empty. No approval has been given.*
