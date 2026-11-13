# ADR-0014 — P7-B: co-access layout equivalence (trace-driven simulation)

- Date: 2026-11-13 (America/Panama).
- Status: **DRAFT PROPOSAL, REVISION 2 — SPEC: PENDING HUMAN REVIEW (Fable-drafted, Opus-reviewed). NOT APPROVED. NO IMPLEMENTATION, LAYOUT CONSTRUCTION ON EVALUATION DATA, SIMULATION OR EXECUTION IS AUTHORIZED BY THIS DOCUMENT.**
- Prepared by Claude Fable 5.2 (`claude-fable-5-2`) at the human research lead's request of 2026-11-13. Revision 1 was reviewed by the auditor role (Claude Opus 5.5): `docs/reviews/p7b-spec-review-2026-11-13/REVIEW.md`, 1 blocker, 7 major, 11 minor. This revision answers it; §13 lists what changed. **Astra review: NOT_PERFORMED.**
- **Governance.** ADR-0012 (the Claude review arrangement) is still pending human approval. P6 and P7-A ran under it by the human lead's study-by-study direction. This document does not treat it as approved for P7-B or any later study; §14 asks for an explicit decision.
- Scope: a bounded simulation on the **existing P7-A traces** of the 81 frozen P5 memory checkpoints. No model is run, no checkpoint is loaded, no training, no change to weights or routing, no storage device, no key-index simulation. P1–P7-A code, records, thresholds and outcomes are immutable. P6-E stays INCONCLUSIVE and P7-A stays CONCENTRATION-ONLY whatever P7-B finds.

## 0. Read this first: how much of the answer is already visible

The review of revision 1 was allowed to use the calibration traces, and only those, to test whether the design was sound. In doing so it computed calibration-stream analogues of this study's main comparison. They are not registered results: they are fitted and scored on the same stream family, and no co-access layout has been evaluated on the evaluation stream. But they are informative: the review's split-half test on the calibration stream found layouts transfer almost perfectly to queries they were not fitted on (out-of-sample against in-sample misses: 1.000–1.014), and P7-A found a frequency layout fitted on calibration transfers to the evaluation stream with almost no loss. What they show:

- With greedy co-access clustering, **flat memory's misses fall to about 0.76 of frequency packing in the primary setting and about 0.64 in the confirmation setting.** That already exceeds the roughly 15% P7-A saw for trees from branch-aware frequency packing.
- The calibration analogue of the main comparison (branch-constrained tree against co-access flat) is a ratio of 0.99 and 1.01 in the primary setting and 0.99 and 1.10 in the confirmation setting, for fixed and learned trees.

So the lead's prediction in §7, that the hypothesis fails and the comparison lands near equivalence, is now made with supporting evidence in hand, and revision 2's changes (the window, the refinement step, the utilization adjustment) were chosen after the auditor and the lead had seen those calibration-side numbers. **A run on the existing evaluation stream would therefore be confirmation of a strongly anticipated result more than a fresh test.** The human lead is asked in §14 to choose between running it as specified, adding a replication on a fresh evaluation stream, or treating the calibration-side evidence as sufficient. This draft specifies the first and defines the second as an option.

## 1. Question

P7-A found that the trees read fewer simulated cached value pages than a frequency-packed flat memory, and that a null preserving only each checkpoint's slot counts reproduces the gap: the trees use fewer rows. Outside its registered comparison it showed that packing hot rows within each branch gave the trees about 15% fewer misses than plain frequency packing. Flat memory was never given a layout that exploits which rows are selected together.

> **Does hierarchical organization offer a storage-locality advantage beyond what can be achieved by arranging arbitrary flat-memory slots according to their observed co-access patterns?**

Competing explanations the design must separate:

1. **Hierarchy-specific locality.** Branches group rows that are used together, so a branch-respecting layout captures structure a flat memory lacks or that clustering its slots cannot recover.
2. **Generic co-access structure.** Any trained memory has rows that are used together; flat gains as much from a co-access layout as trees gain from branch-aware placement.
3. **Concentration.** Trees use fewer rows; apparent locality is utilization again.
4. **Optimizer artefact.** A weak clustering heuristic does better when handed a partition (branches) than when left to find one, so a tree looks better only because its layout problem was made easier.
5. **Arbitrary partition.** Any partition into 16 groups of 256 would help as much as the real branches.

## 2. The measure

P7-A's test asked whether a null reproduces the tree's advantage over flat. Because lower utilization alone exceeds the threshold, it returns "concentration" whether or not additional structure exists. P7-B measures the increment. For checkpoint c and layout L:

**E_c(L) = m_c(actual evaluation stream, layout L) ÷ m_c(mean of that checkpoint's three count-preserving null replicates, layout L-FREQ)**

with m the warm capacity misses per query. The denominator is what the checkpoint's slot popularity alone costs under the layout best suited to popularity. E below 1 is locality from real co-selection and temporal structure, as far as layout L extracts it.

**This normalization does not fully remove utilization, and the design does not rely on it alone.** In P7-A's published records E under frequency packing still rises with effective slot count (pooled slope +0.070 per unit of ln effective slots at the primary setting), enough by itself to make a tree-to-flat ratio of about 0.97. On calibration the trend vanishes under co-access clustering in the primary setting and reverses in the confirmation setting. The sign is not fixed, so every classification in §7 is made twice: on the raw ratio and on a **utilization-adjusted ratio**, and a material difference must appear in both.

**Utilization-adjusted ratio.** For a comparison of tree kind K with flat (54 checkpoints), fit by ordinary least squares `E = a + b · x + d · [tree]`, where x is the natural log of the checkpoint's entropy-effective slot count on the evaluation trace and [tree] is 1 for tree checkpoints. With x̄ the mean of x over the 54 checkpoints, **ρ_adj = (a + b·x̄ + d) ÷ (a + b·x̄)**: the ratio of tree to flat E at common utilization. The fitted slope b is reported.

## 3. Inputs and identities (immutable)

- **Traces.** The P7-A calibration and evaluation traces of all 81 final P5 checkpoints, trace run `P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e`. Identity manifest: `docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json` (270 trace files, all verified against their recorded SHA-256; overall hash `77dea76d96672b13336415ff325388c9c76d8e3b09cf25f2242d9cfe44e2a86a`). P7-B re-verifies every file before use and stops on a mismatch.
- **Checkpoints.** Not loaded. Their identity enters through the trace records.
- **Quality.** The unchanged P5 final NLL of each checkpoint.
- **Evaluation null streams.** The exact count-preserving streams of ADR-0013 §14 item 8, same seeds; each must reproduce the `stream_sha256` P7-A recorded.
- **Calibration null streams** (new, for a control): the same construction applied to each checkpoint's calibration trace with seeds 91311, 91312, 91313 and generator seed `s * 1000 + cell_index`.
- **Streams.** Calibration: training-pool ranks 2048–2559 (never trained on). Evaluation: the P5 panel, validation ranks 2048–2559. Contexts are unrelated 64-byte windows.
- **The evaluation stream is held out from layout construction, not unseen** (§0). P7-A reported results on it under L-ID, L-RAND, L-FREQ and L-BFREQ, and from those records tree L-BFREQ against flat L-FREQ in E terms is already known (0.82 and 0.84 in the primary setting, 0.64 and 0.71 in the confirmation setting). No co-access layout has been evaluated on it.

## 4. Layouts

All layouts are built from the **calibration trace only**: its per-slot counts f and its co-access affinity A. Nothing from the evaluation trace enters any placement. Every layout is one deterministic construction with the same steps and the same bounded refinement for every architecture: no tuning per architecture, no restarts, no choice among candidates.

**Affinity (registered: W = 0).** A[i, j] for i ≠ j is the number of calibration queries in which slots i and j are both selected. It is symmetric by definition and each query contributes once per unordered pair. The windowed variant A₈[i, j] counts ordered pairs of queries (t, u) in the same context with 0 ≤ t − u ≤ 8 (nine offsets, including t = u) such that i is selected at t and j at u, i ≠ j, and is then symmetrized by adding its transpose; it is built as a **sensitivity** variant. Revision 1 registered the window. The review showed, on calibration only, that about 90% of the windowed affinity's mass is chance co-occurrence of popular slots and that same-query affinity clusters as well or better, so same-query affinity is registered. That choice used calibration evidence only and applies identically to every architecture.

**Step 1 — greedy page fill.** Given a set S of slots, page size R, f and A:

1. While S has unplaced slots, start a page with the unplaced slot of highest f (ties: lowest slot ID).
2. Keep a score vector s, initialized to that slot's row of A. While the page has fewer than R rows and unplaced slots remain: add the unplaced slot with the highest s (ties: higher f, then lowest slot ID) and add its row of A to s.
3. Pages are numbered in the order created; rows within a page in the order added.

**Step 2 — bounded swap refinement** (applied to every co-access layout). Objective: total within-page affinity. Visit slots with at least one nonzero affinity in order of descending f, ties by slot ID. For slot x on page P, consider swapping it with a slot y on another page Q that contains at least one slot with nonzero affinity to x; the gain is the change in total within-page affinity. Make the single best strictly positive swap for x (ties: lowest page number Q, then lowest slot ID y). Repeat passes over all slots until a pass makes no swap or 12 passes are done. Revision 1 had no refinement. The review showed greedy alone leaves about 3% (primary) and 10% (confirmation) of misses on the table for unconstrained clustering but only 2–3% for branch-constrained clustering, which would have favoured the trees.

| ID | Applies to | Construction | Role |
|---|---|---|---|
| L-ID | all | Position = slot ID. | Reference control |
| L-RAND | all | The three P7-A permutations, averaged. | Reference control |
| L-FREQ | all | Descending calibration count, ties by slot ID. | Popularity baseline |
| L-BFREQ | trees | Branches in branch-ID order; within a branch by descending count. As P7-A. | Reported |
| **L-COAX** | all | Steps 1 and 2 over all 4,096 slots. | **Co-access clustering with no hierarchy information** |
| **L-BCOAX** | trees | Branches ordered by descending total calibration count (ties: lowest branch ID); steps 1 and 2 inside each branch, swaps restricted to the same branch. | **Co-access clustering constrained to contiguous branches** |
| **L-PCOAX** | all | As L-BCOAX, but with the slots divided into 16 groups of 256 by a fixed pseudo-random partition (seed 91601) in place of branches. | **Control: an arbitrary partition of the same shape** |
| L-NCOAX | all | L-COAX built from the checkpoint's **calibration null** stream (first replicate). | **Control: the algorithm must not manufacture locality** |
| L-COAX8, L-BCOAX8 | as above | The same with A₈. | Sensitivity |
| L-COAXg, L-BCOAXg | as above | Step 1 only, no refinement. | Sensitivity |

Co-access layouts depend on R and are built once per R. For R = 512, where a page holds two branches or groups, L-BCOAX and L-PCOAX order the 16 groups by the same two steps applied to groups (group affinity is the sum of A between their slots, group frequency their total count) with a page of two groups. With all affinities zero, L-COAX equals L-FREQ and L-BCOAX equals frequency packing within count-ordered branches.

**Effort and fairness.** Every architecture gets the same algorithm, the same refinement budget and the same information. Trees have one layout flat cannot have (L-BCOAX, which needs branches); L-PCOAX gives flat a partition-constrained counterpart and, on tree traces, shows whether real branches do better than arbitrary groups. A constrained heuristic can beat an unconstrained one, so "branch-constrained is at least as good as unconstrained" is **not** read as "branches contain the structure"; it is read against L-PCOAX.

**At R = 1 every layout is identical in page terms.** All layouts must give identical results there. Co-access layouts at R ≥ 32 are built and reported but are descriptive only: at ArborLM's actual row sizes P7-A found the cached question degenerate.

## 5. Page model

Value pages only, keys assumed in RAM. **The key-index path is left out of P7-B entirely**; the P7-A defect affected only simulated key reads. P7-B adds a hard check that the cache never holds more than C pages after a query is served.

Otherwise ADR-0013's model, unchanged: per-query service; least-recently-used eviction among pages not used by the current query; warm-up on the first 256 evaluation contexts and counting on the last 256; misses classified as first-touch or capacity; **m = warm capacity misses per query**.

**Eviction ties.** When eviction must split the pages of the oldest query, the order depends on page numbers, and page numbering is part of a layout. The review measured this at 2.5–4% of misses in the primary setting and 5–12% in the confirmation setting, differing by layout. P7-B therefore runs every criterion under **both** tie rules (ascending and descending page number), on numerators and denominators alike, and a classification stands only if it is the same under both. Row order within a page does not affect results.

**Rows per page R** ∈ {1, 2, 8, 32, 128, 512}. R = 32, 128 and 512 are ArborLM's actual 128-byte value rows at 4, 16 and 64 KiB. **R = 1, 2 and 8 are hypothetical row sizes** and are labelled so wherever they appear. **Cache capacity C** ∈ {8, 16, 32, 64, 128} pages.

**Settings for the criteria.** Primary: **R = 2, C = 32**. Confirmation: **R = 8, C = 8**. Both cache 64 rows. Both are non-degenerate in P7-A's records (null means under frequency packing: 3.34, 2.29, 1.78 and 3.09, 2.15, 1.68 misses per query for flat, fixed, learned; smallest single checkpoint 0.50). In the confirmation setting keeping branches contiguous has a real popularity cost (on calibration nulls, L-BCOAX costs about 1.2 times L-FREQ, more for concentrated checkpoints), so E under L-BCOAX there is a net of a cost and a gain; both parts are reported.

## 6. Measurements

For every architecture, layout, R and C, on the evaluation stream:

- distinct value pages per query and its distribution;
- warm capacity misses per query, and per complete context of 64 queries (mean and quantiles across the 256 counted contexts);
- first-touch misses, cold misses from an empty cache, uncached and cached read amplification;
- cache-size sensitivity across C;
- per-slot utilization: distinct slots selected and entropy-effective slots;
- **E**, and its decomposition per checkpoint: null under L-FREQ → null under layout L (the **popularity cost of the layout**, m(null, L) ÷ m(null, L-FREQ)) → actual under L (the structure the layout exploits);
- the **co-access gain** G(L) = m(actual, L) ÷ m(actual, L-FREQ);
- every criterion layout on the null and order-shuffled streams;
- calibration-to-evaluation transfer per layout (m on the calibration stream against m on the evaluation stream);
- quality against misses: each checkpoint's unchanged P5 NLL beside m and E, and the paired tree-minus-flat NLL difference. "Equivalent quality" means what P5 registered and found: both trees within 0.005 nats/byte of flat in 26 of 27 cells.

Not measured and not claimable: device latency, physical I/O, throughput, hardware speed, SSD viability.

## 7. Hypothesis, criteria and outcomes

**Hierarchy-specific locality hypothesis (H-P7B).** *For at least one tree kind, branch-constrained co-access placement gives a tree materially more incremental locality than unconstrained co-access clustering gives flat memory: E_tree(L-BCOAX) is at most 0.80 of E_flat(L-COAX) in the raw and in the utilization-adjusted ratio, consistently across pairs and parents, under both eviction tie rules, in both the primary and the confirmation setting, and real branches do materially better than an arbitrary partition.*

**The lead predicts H-P7B fails**, with the comparison within 10% in both settings (§0).

Comparisons are per tree kind K ∈ {fixed, learned} against flat, paired by parent and seed: 27 pairs in 9 parents. The cells share one corpus and one stream; counts describe robustness to training randomness only and are not significance tests.

**Non-degeneracy, checked first in each setting.** NON-DEGENERATE for K if, under both tie rules: the mean null denominator is at least 0.05 per query for flat and 0.01 for tree kind K; every checkpoint's denominator is at least 0.005; and the mean numerator m(actual, L) is at least 0.01 for both layouts being compared. Otherwise every classification there is DEGENERATE.

**Classification of a tree layout against a flat layout.** ρ is the mean of E over the 27 tree cells divided by the mean over the 27 flat cells; ρ_adj is defined in §2. "Counts favour the tree" means the tree's E is strictly lower than its paired flat cell's in at least 22 of 27 pairs and the tree's parent mean is strictly lower in at least 8 of 9 parents; "counts favour flat" is the mirror. Ties count for neither. The classes are evaluated in this order and the first that applies is taken:

| Class | Condition |
|---|---|
| **TREE MATERIALLY BETTER** | ρ ≤ 0.80 **and** ρ_adj ≤ 0.80 **and** counts favour the tree |
| **FLAT MATERIALLY BETTER** | ρ ≥ 1.25 **and** ρ_adj ≥ 1.25 **and** counts favour flat |
| **WITHIN 10%** | 0.90 ≤ ρ ≤ 1.10 **and** 0.90 ≤ ρ_adj ≤ 1.10 |
| **INTERMEDIATE** | anything else |

WITHIN 10% is a statement about size only. Its direction and counts are always reported beside it, and a consistent direction inside the band is described as "small and consistent", not as no difference. A classification is recorded only if it is the same under both eviction tie rules; otherwise it is **TIE-RULE DEPENDENT**, which is treated as INTERMEDIATE.

**Registered comparisons**, each in the primary and the confirmation setting:

- **HB_K — branch-aware tree against co-access flat** (the question asked): E_tree(L-BCOAX) against E_flat(L-COAX).
- **HU_K — the same rule for everyone:** E_tree(L-COAX) against E_flat(L-COAX), trees treated as arbitrary slots. It shows whether tree traces hold more exploitable co-access structure than flat traces when no hierarchy information is used. It does not enter the outcome; it explains it.
- **PART_K — real branches against an arbitrary partition, on the tree's own traces:** m_tree(L-BCOAX) against m_tree(L-PCOAX). REAL BRANCHES BETTER if the ratio of means is at most 0.80 with L-BCOAX lower in at least 22 of 27 cells and 8 of 9 parent means, under both tie rules; otherwise NOT BETTER.

**Reported with a fixed descriptive rule, no pass or fail:**

- **Co-access gain per architecture:** G(L-COAX) for flat and trees, G(L-BCOAX) for trees. The direct answer to whether flat, given co-access clustering, matches the gain trees got from branch-aware placement.
- **BC_K:** m_tree(L-BCOAX) ÷ m_tree(L-COAX), read only together with PART_K.
- **Control L-NCOAX:** G(L-NCOAX) must be within 0.97–1.03 for every architecture's mean; outside that the algorithm is manufacturing or destroying locality by itself and every co-access result is flagged.
- **Popularity cost of each layout** and **raw misses**, always shown beside effective slots.

**Outcome for tree kind K** (rows evaluated in order; the first that applies is taken):

| Condition | Outcome |
|---|---|
| HB_K DEGENERATE in the primary setting | **UNRESOLVED** |
| HB_K TREE MATERIALLY BETTER in both settings **and** PART_K REAL BRANCHES BETTER in both settings | **HIERARCHY-SPECIFIC ADVANTAGE** |
| HB_K TREE MATERIALLY BETTER in both settings, PART_K not in both | **PARTITION ADVANTAGE, NOT BRANCH-SPECIFIC**: an arbitrary partition does as well |
| HB_K TREE MATERIALLY BETTER in the primary setting only (confirmation anything else, including DEGENERATE) | **NOT ROBUST** |
| HB_K FLAT MATERIALLY BETTER in the primary setting | **FLAT CO-ACCESS BETTER** (the confirmation class is reported beside it) |
| HB_K WITHIN 10% in the primary setting | **WITHIN 10% OF FLAT CO-ACCESS** (the confirmation class is reported beside it) |
| anything else | **INTERMEDIATE**, with direction |

**Robustness grid, reported in full and never substitutable:** every R × C with its non-degeneracy status; the A₈ and greedy-only layouts; the order-shuffled stream.

**Optional replication on a fresh evaluation stream** (only if the human lead approves it in §14): traces for validation ranks 2560–3071 generated with the frozen P7-A trace code (unmodified models, bitwise NLL replay), which is the only step in P7-B that would run a model; the same layouts, built from the same calibration traces, evaluated once on it; every classification and outcome computed again. An outcome is called **replicated** only if it is identical on both streams.

## 8. What could mislead, stated in advance

- **The result is anticipated** (§0), and revision 2's design choices were made with calibration-side analogues visible.
- **Utilization.** E is a ratio of ratios; the adjusted ratio assumes a common linear slope in ln effective slots across architectures, on 54 points.
- **Optimizer strength.** One greedy pass and a bounded swap refinement is still a heuristic. The review found the remaining gap after refinement larger for unconstrained than for constrained clustering, so a better optimizer would probably help flat more. A finding in the tree's favour is therefore an upper estimate; a finding of WITHIN 10% or FLAT BETTER would not be reversed by a stronger optimizer.
- **Stability.** In the confirmation setting, unconstrained layouts fitted on different halves of the calibration stream differed by 3–5% per checkpoint on average and up to 16%; branch-constrained layouts by about 1%. Differences of that size between a tree and a flat cell are within layout noise.
- **Affinity choice.** Same-query affinity is registered; the windowed variant is reported. A result that appears under one only is described as affinity-dependent.
- **Hypothetical row sizes** in both criterion settings; one memory size; one corpus.
- **Simulated page misses are not I/O.**

## 9. Permitted interpretations and decision rule

Recommendations are made per tree kind and combined as follows: the most favourable outcome among the two tree kinds decides whether scaling is proposed; if the kinds differ, both are reported and the recommendation states which kind it rests on.

| Outcome | Permitted bounded statement | Recommendation to the human lead |
|---|---|---|
| HIERARCHY-SPECIFIC ADVANTAGE for at least one tree kind | Under this page model, branch-constrained placement gives the existing trees incremental locality that refined co-access clustering does not give flat memory and that an arbitrary partition does not give the tree, in two settings, at common utilization. | Grounds to **propose** a memory-capacity scaling design whose first question is whether the advantage persists with size. Because both settings use hypothetical row sizes on a 768 KiB memory, this supports a proposal for review and nothing more. It involves training and needs its own specification and approval. |
| WITHIN 10% OF FLAT CO-ACCESS or FLAT CO-ACCESS BETTER for both tree kinds | A flat memory whose slots are arranged by observed co-access gets locality within 10% of, or better than, the existing hierarchy's. Any remaining difference is stated with its size and direction. | Do **not** scale the existing hierarchy on storage-locality grounds. The options are to redesign it (a locality-aware objective, H3, or routing whose branches persist across queries) or to stop the hierarchy line. |
| PARTITION ADVANTAGE, NOT BRANCH-SPECIFIC | Constraining placement to groups helps this heuristic, but real branches do no better than arbitrary groups. | No case for the hierarchy; note that a partition-constrained layout may be a useful heuristic for any memory. |
| INTERMEDIATE or NOT ROBUST | A difference smaller than the registered margin, or in one setting only, or dependent on the tie rule. | Not sufficient to recommend scaling. Report size and direction; the human lead decides whether a stronger test is worth it. |
| UNRESOLVED | The registered setting cannot discriminate. | No recommendation. |
| Any | No statement about hardware speed, physical I/O, SSD viability, larger memories, training or quality. No earlier outcome changes. | — |

Every recommendation goes to the human lead. None is an authorization.

## 10. Correctness requirements

- Every trace file matches the identity manifest; regenerated evaluation null streams match P7-A's `stream_sha256`.
- **Reproduction of P7-A**, for exactly the configurations P7-A ran (actual stream on L-ID, L-RAND, L-FREQ, L-BFREQ; null and order-shuffled streams on L-ID and L-FREQ; ascending tie rule): every miss count at every R and C equals the P7-A record. A difference stops the study.
- Layouts are permutations of 0…4,095; L-BCOAX keeps every branch contiguous and L-PCOAX every group; no layout builder is given the evaluation trace (enforced by interface and by a test that fails if it is).
- Greedy fill and refinement checked on hand-built affinities with known answers: ties at every level; zero affinity (L-COAX must equal L-FREQ); R = 1; a case where refinement must make a specific swap; termination within 12 passes; within-page affinity never decreases.
- At R = 1 all layouts give identical results. The cache never exceeds C pages; first-touch misses do not depend on C or on the tie rule; capacity misses do not increase with C; misses never exceed touches.
- The auditor role rebuilds L-COAX, L-BCOAX and L-PCOAX for all 81 checkpoints at R = 2 and R = 8 with its own standard-library code and compares layout hashes, and re-simulates both criterion settings under both tie rules for a registered selection of checkpoints, before analysis. Any difference stops the study.

## 11. Resource limits and stop conditions

No training, CPU only, and no model unless the optional replication is approved. Per checkpoint: two affinities (sparse); co-access layouts for six R; simulation of the actual stream on every layout, of the three evaluation nulls and the order-shuffled stream on the criterion layouts, the calibration-transfer runs, and both tie rules for the two criterion settings. The review estimated about 1,700 s for simulation on the reference machine.

Caps: layout construction ≤ 900 s; simulation and analysis ≤ 5,400 s; combined ≤ 6,300 s; the auditor's rebuild and re-simulation ≤ 1,800 s outside the study budget; optional replication traces ≤ 600 s and its simulation ≤ 5,400 s; sampled process-tree RSS ≤ 2 GiB. Before the freeze the implementer must time the complete configuration set, including layout construction, on full-size synthetic traces and show at least a twofold margin against each cap; otherwise the specification returns to the lead. Stop on: identity mismatch, failure to reproduce P7-A, any invariant violation, disagreement with the auditor's rebuild, or a resource breach. Partial and unexecuted records are preserved; configurations are never dropped to fit.

## 12. Process and audit

Human approval of this ADR → implementation by the implementer role (Sonnet 5.5) in new modules only → pre-freeze audit by the auditor role (Opus 5.5) in a separate context, with its own layout builder and simulator → fixes → re-audit → source/spec freeze commit → single registered invocation (layouts, simulate, independent check, analyze) → independent recomputation from raw records → review. Routine evidence organization by the clerk role (Haiku 5.5). The auditor receives code and records, not the lead's conclusions. Models actually used are recorded from session metadata. Failed runs and failed checker attempts are kept. Intermediate commits stay local until one push.

## 13. Independent review of assumptions and the lead's response

The auditor role reviewed revision 1: `docs/reviews/p7b-spec-review-2026-11-13/REVIEW.md`, with scripts and outputs. It read the 81 calibration selection files and the 54 tree calibration branch files, published P7-A and P5 records, and **no evaluation trace**; no co-access layout touched the evaluation stream and no registered outcome was computed. Independent mathematical and engineering evidence, not Astra validation and not approval.

| Finding | Response in this revision |
|---|---|
| **B1.** The utilization check (UTIL_K) measured only how well a layout packs popular rows and could never fire; and dividing by a checkpoint's own null demonstrably leaves a utilization trend. | Adopted. UTIL_K removed. A utilization-adjusted ratio is defined (§2) and required alongside the raw ratio for every material classification (§7). The null ratio is kept as the reported popularity cost of a layout. |
| **M1.** The eviction tie rule made page numbering a hidden layout choice worth 2.5–12% of misses. | Adopted: every classification must agree under both tie rules (§5, §7). |
| **M2.** Greedy clustering favoured the branch-constrained layout; "the constraint only removes placements" was wrong for a heuristic. | Adopted: a bounded swap refinement is registered for every co-access layout (§4); the claim is withdrawn; greedy-only layouts are a sensitivity result. |
| **M3.** In the confirmation setting branch contiguity carries a large, utilization-dependent popularity cost. | Adopted: the popularity cost and the exploited structure are reported separately (§6); the setting is kept because that cost is a real property of contiguous branches; stated in §5. |
| **M4.** Much of the outcome is already visible from published records and calibration analogues. | Adopted: §0 and §3 state it; an optional fresh-stream replication is defined (§7) and put to the human lead (§14). |
| **M5.** EQUIVALENT by ratio alone could hide a consistent direction, and the decision text over-read it. | Adopted: the class is renamed WITHIN 10%, direction and counts are always reported, and §9 is reworded. |
| **M6.** Outcome and decision tables were not total. | Adopted: ordered, exhaustive tables; the role of HU_K and the handling of differing tree kinds are stated (§7, §9). |
| **M7.** The window W = 8 was mostly chance co-occurrence and was not matched to cache residency. | Adopted: same-query affinity registered, the window kept as sensitivity (§4). |
| Minor 1–11. | Adopted: exact affinity definitions; denominator stated as the mean of three replicates; zero-affinity behaviour stated; the reproduction requirement limited to what P7-A ran; larger caps and a dry run that includes layout construction; the null-fit control (L-NCOAX) and the random-partition control (L-PCOAX, promoted to a criterion input); instability stated; numerator floors added; R ≥ 32 co-access layouts descriptive only. |
| **Not adopted.** Optimal (Belady) caching as a bound; other optimizers or windows beyond the two registered. | Left out to keep the study bounded. |

Scientific choices the auditor marked for the lead, decided above and now for the human lead to confirm: the form of the utilization adjustment; requiring agreement under both tie rules; the refinement step; same-query affinity; the WITHIN 10% band; and whether the run is still worth doing.

## 14. Decisions requested from the human lead

1. **Whether to run P7-B at all, and on what.** Options: (a) run as specified on the existing evaluation stream; (b) run as specified **and** add the fresh-stream replication of §7, which needs model forwards on unused validation ranks 2560–3071 and so consumes fresh held-out data; (c) do not run, and record the calibration-side evidence in §0 as exploratory. The lead recommends (b): the run is cheap, and with the result this predictable a replication on data nobody has looked at is what would make it evidence.
2. **Governance:** whether P7-B may run under the Claude workflow as a study-specific direction with ADR-0012 still pending, or whether ADR-0012 must be decided first.
3. Approve the layout construction: same-query affinity, greedy page fill, the bounded swap refinement, one fixed layout per comparison, and the controls L-PCOAX and L-NCOAX.
4. Approve E, the utilization-adjusted ratio, and the requirement that classifications agree under both eviction tie rules.
5. Approve the thresholds (0.80 / 1.25 material; 0.90–1.10 band; 22 of 27 and 8 of 9) and the primary and confirmation settings.
6. Approve the decision rule in §9 for scaling versus redesign.
7. Approve the resource caps in §11.

## 15. Approval record

*Empty. No approval has been given.*
