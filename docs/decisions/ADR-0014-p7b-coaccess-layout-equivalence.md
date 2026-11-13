# ADR-0014 — P7-B: co-access layout equivalence (trace-driven simulation)

- Date: 2026-11-13 (America/Panama).
- Status: **DRAFT PROPOSAL, REVISION 4 — SPEC: PENDING FINAL HUMAN EXECUTION APPROVAL (Fable-drafted, Opus-reviewed three times). NOT APPROVED FOR EXECUTION. NO IMPLEMENTATION, LAYOUT CONSTRUCTION ON EVALUATION DATA, TRACE GENERATION, SIMULATION OR EXECUTION IS AUTHORIZED BY THIS DOCUMENT.** Revision 3 applied the human research lead's review of revision 2 (recorded in §15): option (b), five partition seeds, study-specific governance. Revision 4 answers the auditor's re-review of revision 3, which found that the five-partition rule as first written could not fail; that rule is changed and is the one substantive change since the human lead last read the document (§13, §14).
- Prepared by Claude Fable 5.2 (`claude-fable-5-2`) at the human research lead's request of 2026-11-13. Revision 1 was reviewed by the auditor role (Claude Opus 5.5): `docs/reviews/p7b-spec-review-2026-11-13/REVIEW.md`, 1 blocker, 7 major, 11 minor. This revision answers it; §13 lists what changed. **Astra review: NOT_PERFORMED.**
- **Governance.** The human lead supports a **study-specific Claude workflow for P7-B only**. ADR-0012 stays pending, and every later phase needs human approval. Nothing under this workflow is Astra validation.
- Scope: a bounded simulation on the **existing P7-A traces** of the 81 frozen P5 memory checkpoints. No model is run, no checkpoint is loaded, no training, no change to weights or routing, no storage device, no key-index simulation. P1–P7-A code, records, thresholds and outcomes are immutable. P6-E stays INCONCLUSIVE and P7-A stays CONCENTRATION-ONLY whatever P7-B finds.

## 0. Read this first: how much of the answer is already visible

The review of revision 1 was allowed to use the calibration traces, and only those, to test whether the design was sound. In doing so it computed calibration-stream analogues of this study's main comparison. They are not registered results: they are fitted and scored on the same stream family, and no co-access layout has been evaluated on the evaluation stream. But they are informative: the review's split-half test on the calibration stream found layouts transfer almost perfectly to queries they were not fitted on (out-of-sample against in-sample misses: 1.000–1.014), and P7-A found a frequency layout fitted on calibration transfers to the evaluation stream with almost no loss. What they show:

- With greedy co-access clustering, **flat memory's misses fall to about 0.76 of frequency packing in the primary setting and about 0.64 in the confirmation setting.** That already exceeds the roughly 15% P7-A saw for trees from branch-aware frequency packing.
- The calibration analogue of the main comparison (branch-constrained tree against co-access flat) was a ratio of 0.99 and 1.01 in the primary setting and 0.99 and 1.10 in the confirmation setting, for fixed and learned trees, under revision 1's configuration. Under the configuration now registered (same-query affinity with refinement) the re-review found 1.00 and 1.03 in the primary setting and 1.09 and 1.21 in the confirmation setting. All of these are calibration-stream numbers and none is a registered result.

So the lead's prediction in §7, that the hypothesis fails and the comparison lands near equivalence, is now made with supporting evidence in hand, and revision 2's changes (the window, the refinement step, the utilization adjustment) were chosen after the auditor and the lead had seen those calibration-side numbers. **A run on the existing evaluation stream would therefore be confirmation of a strongly anticipated result more than a fresh test.** The human lead chose to run it **with a prospective replication on a fresh evaluation stream** (validation ranks 2560–3071), which nobody has looked at. Revision 3 makes that replication part of the registered study (§7a).

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

**Utilization-adjusted ratio.** For a comparison of tree kind K with flat (54 checkpoints), fit by ordinary least squares `E = a + b · x + d · [tree]`, where x is the natural log of the checkpoint's entropy-effective slot count on the evaluation trace and [tree] is 1 for tree checkpoints. With x̄ the mean of x over the 54 checkpoints, **ρ_adj = (a + b·x̄ + d) ÷ (a + b·x̄)**: the ratio of tree to flat E at common utilization. The fitted slope b is reported. x uses the effective slot count of the stream being analysed. If a + b·x̄ is not positive, ρ_adj is undefined and the comparison is classified INTERMEDIATE. The re-review found that a single shared slope fits the primary setting but is rejected in the confirmation setting on calibration, where separate slopes would move the adjusted ratio between about 0.90 and 1.08 depending on where it is evaluated. Requiring the raw and the adjusted ratio to agree makes a material classification harder to reach, which is the conservative direction.

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
| **L-PCOAX-1 … L-PCOAX-5** | all | As L-BCOAX, but with the slots divided into 16 groups of 256 by a fixed pseudo-random partition in place of branches. **Five predetermined partitions**, seeds 91601, 91602, 91603, 91604, 91605: for seed s, `random.Random(s).shuffle` is applied to the list 0…4,095 and group g is entries 256g…256g+255 of the shuffled list. The same five partitions are used for every checkpoint and architecture. Groups are ordered by descending total calibration count (ties: lowest group index), exactly as branches are in L-BCOAX. | **Control: arbitrary partitions of the same shape** |
| L-NCOAX | all | L-COAX built from the checkpoint's **calibration null** stream (first replicate). | **Control: the algorithm must not manufacture locality** |
| L-COAX8, L-BCOAX8 | as above | The same with A₈. | Sensitivity |
| L-COAXg, L-BCOAXg | as above | Step 1 only, no refinement. | Sensitivity |

Co-access layouts depend on R and are built once per R. For R = 512, where a page holds two branches or groups, L-BCOAX and the L-PCOAX layouts order the 16 groups by the same two steps applied to groups (group affinity is the sum of A between their slots, group frequency their total count) with a page of two groups. With all affinities zero, L-COAX equals L-FREQ and L-BCOAX equals frequency packing within count-ordered branches.

**Exactness.** In a swap, each slot takes the position the other held in its page. For R = 512 the rows inside a group keep the order produced by the two steps at R = 256. A layout's identity is its **canonical hash**: the SHA-256 of the pages in page order, each page's slot IDs sorted ascending, written as little-endian 16-bit integers. Row order within a page does not affect any result, so the canonical hash ignores it. The five partitions are registered by the SHA-256 of their shuffled lists as little-endian 16-bit integers (identical under Python 3.12.14 and 3.15.1):

| Seed | SHA-256 of the shuffled list |
|---|---|
| 91601 | `ae626b43df264708466a8afc9c2b5434c3db053e7b57f27800b9674192b16487` |
| 91602 | `0d310a05d82ef6eba8cc5adbeba16a88d74a5221353eb0208c1e755f3230e9f3` |
| 91603 | `55cbff61076689e78f030d374b741aa28f448484694f51d3f65dbc56db183af5` |
| 91604 | `98142918ba5f6ef34e6b9d3efc1f27a7c5ea9fd821bfb2b862641145af6f25a2` |
| 91605 | `8d55366cd4d23a08e651161638e0b0cc34dbee0ad13764e3181ffa2b5db26a0c` |

A partition whose hash differs stops the study.

**Effort and fairness.** Every architecture gets the same algorithm, the same refinement budget and the same information. Each of the five partition layouts is built with exactly the construction and budget of L-BCOAX: the same greedy fill inside each group, the same swap refinement restricted to the group, the same 12-pass limit. No partition is tuned, replaced or selected, and all five enter every result. Trees have one layout flat cannot have (L-BCOAX, which needs branches); the partition layouts give flat partition-constrained counterparts and, on tree traces, show whether real branches do better than arbitrary groups. A constrained heuristic can beat an unconstrained one, so "branch-constrained is at least as good as unconstrained" is **not** read as "branches contain the structure"; it is read against L-PCOAX.

**At R = 1 every page holds one row**, so layouts cannot change which rows share a page. Required to be identical across all layouts there: distinct pages per query, first-touch misses, and capacity misses at C = 8. At larger C the eviction tie rule depends on page numbers, so capacity misses may differ between layouts by a few percent even at R = 1; that is not a violation. Co-access layouts at R ≥ 32 are built and reported but are descriptive only: at ArborLM's actual row sizes P7-A found the cached question degenerate.

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
- the three null replicates and the order-shuffled stream on L-FREQ, L-COAX and (trees) L-BCOAX at every R and C; and, at the two criterion settings only, the three null replicates on each of the five partition layouts under both tie rules, which PART_K needs;
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
- **PART_K — real branches against arbitrary partitions, on the tree's own traces, scored on exploited structure.** For a layout L define the **exploited structure** S_c(L) = m_c(actual stream, L) ÷ m_c(mean of the three null replicates, L): the checkpoint's misses under L relative to what the same layout costs on a stream with the same slot popularity and no co-access structure. For each tree checkpoint let S_B = S(L-BCOAX) and S_P the **mean of S over the five partition layouts**. PART_K is **REAL BRANCHES BETTER** only if all of the following hold under both tie rules:
  1. *Aggregate:* the mean of S_B over the 27 cells is at most 0.80 times the mean of S_P; S_B is strictly lower than S_P in at least 22 of 27 cells; and the parent mean of S_B is strictly lower in at least 8 of 9 parents.
  2. *Every partition:* against each of the five partitions taken alone, the mean of S_B over the 27 cells is at most 0.80 times the mean of that partition's S.

  Otherwise **NOT BETTER**. PART_K is DEGENERATE in a setting if any null denominator involved is below 0.005 for a checkpoint or below 0.01 on average.

  **Why exploited structure and not raw misses.** The re-review showed that a comparison of raw misses cannot fail: a random partition scatters a checkpoint's popular rows across 16 groups, so it packs popularity badly (on calibration nulls, 1.33–1.47 times frequency packing in the primary setting and 2.26–2.76 times in the confirmation setting, against about 1.05 and 1.28 for real branches). Real branches beat every one of 25 random partitions on raw misses by a wide margin (0.58–0.63 and 0.26–0.29) for that reason alone, in all 53,130 choices of five. Dividing each layout's misses by its own cost on the null removes how well the partition happens to pack popular rows and leaves what the question is about: whether real branches let the layout exploit more real co-access structure than arbitrary groups do. On calibration that ratio was 0.77–0.79 in the primary setting, so the rule can go either way. The raw ratio is still reported, labelled as dominated by popularity cost.

  Reported beside it: each partition's ratio, the smallest and largest of the five, the spread across partitions per checkpoint, and in how many cells S_B is lower than all five. Five partitions cannot support a statement about partitions in general. A stronger null, partitions that keep each branch's popularity profile and scramble only its membership, was considered and not adopted because it would make the partitions depend on each checkpoint; that is a stated limit.

**Reported with a fixed descriptive rule, no pass or fail:**

- **Co-access gain per architecture:** G(L-COAX) for flat and trees, G(L-BCOAX) for trees. The direct answer to whether flat, given co-access clustering, matches the gain trees got from branch-aware placement.
- **BC_K:** m_tree(L-BCOAX) ÷ m_tree(L-COAX), read only together with PART_K. The five-partition counterpart, mean m_P ÷ m_tree(L-COAX), is shown beside it.
- **Partition layouts on flat traces:** the same five layouts on flat checkpoints, raw and in exploited-structure terms, each against flat L-COAX. Descriptive.
- **Split-half stability:** each criterion layout fitted on each half of the calibration contexts and scored on the other half, per checkpoint. Calibration only; reported so that tree-against-flat differences can be read against layout noise.
- **Control L-NCOAX:** G(L-NCOAX) must be within 0.97–1.03 for every architecture's mean; outside that the algorithm is manufacturing or destroying locality by itself and every co-access result is flagged.
- **Popularity cost of each layout** and **raw misses**, always shown beside effective slots.

**Outcome for tree kind K** (rows evaluated in order; the first that applies is taken):

| Condition | Outcome |
|---|---|
| HB_K DEGENERATE in the primary setting | **UNRESOLVED** |
| HB_K TREE MATERIALLY BETTER in both settings **and** PART_K REAL BRANCHES BETTER in both settings | **HIERARCHY-SPECIFIC ADVANTAGE** |
| HB_K TREE MATERIALLY BETTER in both settings, PART_K anything else in either setting (NOT BETTER, DEGENERATE or tie-rule dependent) | **ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC** |
| HB_K TREE MATERIALLY BETTER in the primary setting only (confirmation anything else, including DEGENERATE) | **NOT ROBUST** |
| HB_K FLAT MATERIALLY BETTER in the primary setting | **FLAT CO-ACCESS BETTER** (the confirmation class is reported beside it) |
| HB_K WITHIN 10% in the primary setting | **WITHIN 10% OF FLAT CO-ACCESS** (the confirmation class is reported beside it) |
| anything else | **INTERMEDIATE (tree-favouring)** if ρ < 1 in the primary setting under the ascending tie rule, otherwise **INTERMEDIATE (flat-favouring)**; the direction is part of the label |

**Robustness grid, reported in full and never substitutable:** every R × C with its non-degeneracy status; the A₈ and greedy-only layouts; the order-shuffled stream.

## 7a. Two evaluation streams (registered)

P7-B is evaluated on two streams. Everything in §4 to §7 applies to each stream separately and identically.

- **Stream A — existing.** The P7-A evaluation traces (validation ranks 2048–2559). Held out from layout construction but already seen under other layouts (§3).
- **Stream B — prospective replication.** Validation ranks 2560–3071 under the existing panel recipe: 512 contexts that no ArborLM study has evaluated. Its traces are generated from the unmodified models by the same selection-recording path P7-A used, after the same bitwise replay of each checkpoint's recorded P5 NLL on the P5 panel (exact handling below). This is the only step in P7-B that runs a model. No loss or quality number is computed or recorded on stream B; only selected slot IDs and visited branch IDs are kept. Its count-preserving nulls use the ADR-0013 construction on its own counts.

**Stream B must be shown to be unused before the freeze.** The panel is reconstructed independently from the raw validation file by two separate implementations (implementer and auditor), as earlier panels were; both reconstructions must also reproduce the recorded SHA-256 of the P1 to P5 panels from the same file; the new panel must have zero exact overlap with the four earlier validation panels, the P7-A evaluation panel (which is the P5 panel), the calibration stream and the full training candidate pool; and every committed record and local manifest is searched for any earlier use of validation ranks at or above 2560. The clerk role's inventory of rank ranges used by every prior study is `docs/reviews/p7b-spec-inputs-2026-11-13/panel_usage.md`. If the panel turns out to have been used, or cannot be reconstructed identically twice, the study stops before any evaluation and returns to the human lead. The clerk's inventory found no record of any evaluation, trace or loss on validation ranks at or above 2560, and the panel code confirms the recorded range for P5 is half-open (the first 2,560 ranked candidates). Stream B comes from the same corpus split, and so from the same articles, as stream A; it is fresh in the sense of never having been evaluated, not in the sense of being an independent corpus.

**Freeze before either stream.** Code, parameters, seeds, thresholds, outcome classifications, this specification, **and the layouts themselves** are fixed before any evaluation simulation. Layouts depend only on the calibration traces: they are built once, their hashes are recorded and independently reproduced by the auditor role, and the same layouts are then used on both streams. Stream B's traces are generated after the freeze. Both streams are simulated before any analysis is run, and the analysis stage runs once, on both. No result from one stream can influence anything about the other, and no change is made between them.

**Stream B, exact handling.**

- *Tracing.* For each checkpoint, in one process: replay the recorded P5 NLL on the P5 panel bitwise; regenerate the calibration and stream-A traces and require them to be byte-identical to the identity manifest; then trace stream B. No loss is computed on stream B.
- *Integrity.* Selected IDs in range and distinct within a query; for trees every selected slot in a visited branch. There is no earlier histogram to compare with, so the byte-identical regeneration of the existing traces in the same process is the evidence that the tracing path is the one P7-A used.
- *Identity before simulation.* A stream-B identity manifest (every trace file's SHA-256, each checkpoint's per-slot selection counts hash, and the hashes of its null streams) is written and committed before any simulation of either stream.
- *Nulls.* Stream B's count-preserving nulls use seeds 91321, 91322, 91323 with generator seed `s * 1000 + cell_index`, distinct from stream A's.
- *Adjusted ratio and non-degeneracy.* Computed from stream B's own effective slot counts and its own nulls, by the same rules.
- *Order.* Once stream A's simulation starts, stream B is simulated unconditionally. Nothing computed on stream A is an input to anything on stream B.

**Combining the streams.** Each tree kind gets one outcome label per stream from §7 (the direction is part of an INTERMEDIATE label). The pair is then described as:

| Stream A and stream B | Description |
|---|---|
| the same label, not UNRESOLVED | that outcome, **REPLICATED** |
| both UNRESOLVED | **UNRESOLVED ON BOTH STREAMS** |
| exactly one UNRESOLVED | the other stream's outcome, **SINGLE-STREAM** |
| two different labels, neither UNRESOLVED | **NOT REPLICATED**; both are reported and neither is treated as established |

## 8. What could mislead, stated in advance

- **The result is anticipated** (§0), and revision 2's design choices were made with calibration-side analogues visible.
- **Utilization.** E is a ratio of ratios; the adjusted ratio assumes a common linear slope in ln effective slots across architectures, on 54 points.
- **Optimizer strength.** One greedy pass and a bounded swap refinement is still a heuristic. The review found the remaining gap after refinement larger for unconstrained than for constrained clustering, so a better optimizer would probably help flat more. A finding in the tree's favour is therefore an upper estimate; a finding of WITHIN 10% or FLAT BETTER would not be reversed by a stronger optimizer.
- **Stability.** In the confirmation setting, unconstrained layouts fitted on different halves of the calibration stream differed by 3–5% per checkpoint on average and up to 16%; branch-constrained layouts by about 1%. Differences of that size between a tree and a flat cell are within layout noise.
- **Affinity choice.** Same-query affinity is registered; the windowed variant is reported. A result that appears under one only is described as affinity-dependent.
- **Hypothetical row sizes** in both criterion settings; one memory size; one corpus.
- **Simulated page misses are not I/O.**

## 9. Permitted interpretations and decision rule

Each tree kind is placed in exactly one decision class from its two stream outcomes:

| Decision class for tree kind K | Condition |
|---|---|
| **S — supports proposing scaling** | HIERARCHY-SPECIFIC ADVANTAGE on both streams |
| **U — unresolved** | UNRESOLVED on both streams |
| **N — no storage-locality case for the hierarchy** | on each stream the outcome is one of: WITHIN 10% OF FLAT CO-ACCESS, FLAT CO-ACCESS BETTER, ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC (the two streams need not give the same one) |
| **I — inconclusive** | every other combination, including any INTERMEDIATE, NOT ROBUST or single UNRESOLVED |

The recommendation follows from the two tree kinds' classes, checked in this order:

| Classes | Permitted bounded statement | Recommendation to the human lead |
|---|---|---|
| At least one tree kind in S | Under this page model, branch-constrained placement gives that tree kind incremental locality that refined co-access clustering does not give flat memory, at common utilization, in two settings and on two streams, and real branches let the layout exploit materially more structure than arbitrary groups. | Grounds to **propose** a memory-capacity scaling design whose first question is whether the advantage persists with size, resting on the tree kind named. Both settings use hypothetical row sizes on a 768 KiB memory, so this supports a proposal for review and nothing more. It involves training and needs its own specification and approval. |
| Both tree kinds in N | A flat memory whose slots are arranged by observed co-access gets locality within 10% of, or better than, the existing hierarchy's, or the tree's edge is not attributable to its branches. Any remaining difference is stated with its size and direction. | Do **not** scale the existing hierarchy on storage-locality grounds. The options are to redesign it (a locality-aware objective, H3, or routing whose branches persist across queries) or to stop the hierarchy line. |
| Both tree kinds in U | The registered settings cannot discriminate. | No recommendation. |
| Anything else | A difference smaller than the registered margin, or in one setting or one stream only, or dependent on the tie rule, or differing between tree kinds. | Not sufficient to recommend scaling. Report sizes and directions for each kind; the human lead decides whether a stronger test is worth it. |

Under any outcome: no statement about hardware speed, physical I/O, SSD viability, larger memories, training or quality, and no earlier outcome changes. Every recommendation goes to the human lead. None is an authorization.

## 10. Correctness requirements

- Every trace file matches the identity manifest; regenerated evaluation null streams match P7-A's `stream_sha256`.
- **Reproduction of P7-A on stream A**, for exactly the configurations P7-A ran (actual stream on L-ID, L-RAND, L-FREQ, L-BFREQ; null and order-shuffled streams on L-ID and L-FREQ; ascending tie rule): every miss count at every R and C equals the P7-A record. A difference stops the study.
- Layouts are permutations of 0…4,095; L-BCOAX keeps every branch contiguous and each L-PCOAX layout every one of its groups; the five partitions are each 16 disjoint groups of 256 covering all slots and are pairwise different; no layout builder is given the evaluation trace (enforced by interface and by a test that fails if it is).
- Greedy fill and refinement checked on hand-built affinities with known answers: ties at every level; zero affinity (L-COAX must equal L-FREQ); R = 1; a case where refinement must make a specific swap; termination within 12 passes; within-page affinity never decreases.
- At R = 1 the quantities named in §4 are identical across layouts. The cache never exceeds C pages; first-touch misses do not depend on C or on the tie rule; capacity misses do not increase with C; misses never exceed touches.
- The auditor role rebuilds L-COAX, L-BCOAX, L-NCOAX and all five partition layouts for all 81 checkpoints at R = 2 and R = 8 with its own standard-library code and compares canonical layout hashes, and re-simulates both criterion settings under both tie rules on **both streams**, before analysis, for the registered selection of 18 checkpoints fixed in ADR-0013 §14 item 12 (the first three of each architecture in registered order plus `random.Random(91501).sample` of three more each). Any difference stops the study.

## 11. Resource limits and stop conditions

No training, CPU only. Models are run only to generate stream B's traces.

**Work per checkpoint (revised for five partitions and two streams).**

- *Layouts, built once from calibration.* Co-access layouts per R (six values): L-COAX, L-NCOAX, L-COAX8, L-COAXg for every architecture; L-BCOAX, L-BCOAX8, L-BCOAXg for trees; **five partition layouts** for every architecture. That is 9 co-access layouts per R for flat (54 builds) and 12 for trees (72 builds), against 5 and 8 per R in revision 2. Each partition layout costs what L-BCOAX costs.
- *Simulation, per evaluation stream.* The actual stream on every layout across 6 R × 5 C; the three nulls and the order-shuffled stream on L-FREQ, L-COAX and (trees) L-BCOAX; calibration-transfer runs; and the descending tie rule for the two criterion settings on every layout that enters a criterion, which now includes the five partition layouts. The partition layouts are simulated on the actual stream at every setting and, at the two criterion settings under both tie rules, on the three nulls (5 layouts × 3 replicates × 2 settings × 2 tie rules = 60 further runs per checkpoint per stream). Calibration-transfer and split-half runs use calibration data only and are done once, in the layout stage. Relative to revision 2 this is about one quarter more simulation per stream, and the second stream doubles the total. The re-review projected about 1,560 s for stream A and 1,370 s for stream B at P7-A's measured rate before the 60 partition-null runs, and about 125 s for all layout builds.

**Caps.**

| Stage | Cap |
|---|---:|
| Layout construction, calibration-transfer and split-half runs (once) | 2,700 s |
| Stream B panel reconstruction and trace generation | 600 s |
| Simulation, stream A | 5,400 s |
| Simulation, stream B | 5,400 s |
| Analysis (both streams) | 600 s |
| **Study total** | **14,700 s** |
| Auditor's layout rebuild and re-simulation (outside the study budget) | 3,600 s |

Caps are active worker time with workers run one at a time. Sampled process-tree RSS ≤ 2 GiB throughout. These are ceilings, not predictions; the review of revision 1 estimated about 1,700 s of simulation per stream before the partition layouts were added. **Before the freeze the implementer must time the complete configuration set, including all layout builds, on full-size synthetic traces and show at least a twofold margin against each cap; otherwise the specification returns to the lead for a recorded amendment before anything touches an evaluation stream.** Stop on: identity mismatch, stream B not shown to be unused, failure to reproduce P7-A on stream A, any invariant violation, disagreement with the auditor's rebuild, or a resource breach. Partial and unexecuted records are preserved; configurations and partitions are never dropped to fit.

## 12. Process and audit

Final human execution approval of this ADR → implementation by the implementer role (Sonnet 5.5) in new modules only → pre-freeze audit by the auditor role (Opus 5.5) in a separate context, with its own layout builder and simulator → fixes → re-audit → independent double reconstruction of the stream B panel and proof that it is unused → source/spec freeze commit → single registered sequence (build and hash layouts; auditor reproduces layout hashes; generate stream B traces; simulate stream A; simulate stream B; independent check on both; analyze both, once) → independent recomputation from raw records → review. Routine evidence organization by the clerk role (Haiku 5.5). The auditor receives code and records, not the lead's conclusions. Models actually used are recorded from session metadata. Failed runs and failed checker attempts are kept. Intermediate commits stay local until one push.

## 13. Independent review of assumptions and the lead's response

The auditor role reviewed revision 1: `docs/reviews/p7b-spec-review-2026-11-13/REVIEW.md`, with scripts and outputs. It read the 81 calibration selection files and the 54 tree calibration branch files, published P7-A and P5 records, and **no evaluation trace**; no co-access layout touched the evaluation stream and no registered outcome was computed. Independent mathematical and engineering evidence, not Astra validation and not approval.

| Finding | Response in this revision |
|---|---|
| **B1.** The utilization check (UTIL_K) measured only how well a layout packs popular rows and could never fire; and dividing by a checkpoint's own null demonstrably leaves a utilization trend. | Adopted. UTIL_K removed. A utilization-adjusted ratio is defined (§2) and required alongside the raw ratio for every material classification (§7). The null ratio is kept as the reported popularity cost of a layout. |
| **M1.** The eviction tie rule made page numbering a hidden layout choice worth 2.5–12% of misses. | Adopted: every classification must agree under both tie rules (§5, §7). |
| **M2.** Greedy clustering favoured the branch-constrained layout; "the constraint only removes placements" was wrong for a heuristic. | Adopted: a bounded swap refinement is registered for every co-access layout (§4); the claim is withdrawn; greedy-only layouts are a sensitivity result. |
| **M3.** In the confirmation setting branch contiguity carries a large, utilization-dependent popularity cost. | Adopted: the popularity cost and the exploited structure are reported separately (§6); the setting is kept because that cost is a real property of contiguous branches; stated in §5. |
| **M4.** Much of the outcome is already visible from published records and calibration analogues. | Adopted: §0 and §3 state it; a fresh-stream replication was defined and, at the human lead's direction, is now part of the registered study (§7a). |
| **M5.** EQUIVALENT by ratio alone could hide a consistent direction, and the decision text over-read it. | Adopted: the class is renamed WITHIN 10%, direction and counts are always reported, and §9 is reworded. |
| **M6.** Outcome and decision tables were not total. | Adopted: ordered, exhaustive tables; the role of HU_K and the handling of differing tree kinds are stated (§7, §9). |
| **M7.** The window W = 8 was mostly chance co-occurrence and was not matched to cache residency. | Adopted: same-query affinity registered, the window kept as sensitivity (§4). |
| Minor 1–11. | Adopted: exact affinity definitions; denominator stated as the mean of three replicates; zero-affinity behaviour stated; the reproduction requirement limited to what P7-A ran; larger caps and a dry run that includes layout construction; the null-fit control (L-NCOAX) and the random-partition control (L-PCOAX, promoted to a criterion input); instability stated; numerator floors added; R ≥ 32 co-access layouts descriptive only. |
| **Not adopted.** Optimal (Belady) caching as a bound; other optimizers or windows beyond the two registered. | Left out to keep the study bounded. |

Scientific choices the auditor marked for the lead, decided above and now for the human lead to confirm: the form of the utilization adjustment; requiring agreement under both tie rules; the refinement step; same-query affinity; and the WITHIN 10% band. The human lead accepted these in the review of revision 2 (§15).

### Revision 3 amendment and its re-review

Revision 3 was prepared at the human lead's direction (§15) without inspecting any evaluation outcome: no co-access or partition layout has been evaluated on either evaluation stream, and stream B's traces do not exist. It changes four things relative to revision 2: the arbitrary-partition control uses five predetermined partitions with a fixed aggregate rule (§4, §7); the fresh-stream replication is part of the registered study, with a rule for combining streams and a requirement to prove the fresh panel unused (§7a); the freeze explicitly covers the layouts and precedes both streams (§7a); and the resource accounting is revised (§11).

**Re-review of revision 3** (`docs/reviews/p7b-spec-review-2026-11-13/REREVIEW.md`; calibration traces and published records only; no evaluation trace and no raw validation file opened): of the revision-1 findings, the blocker and six majors are fixed and one major was partly fixed; it found 1 new blocker, 4 major and 14 minor, and recommended NOT READY. Revision 4 responds:

| Finding | Response in revision 4 |
|---|---|
| **RB1.** The five-partition rule compared raw misses and could not fail: random partitions pack popular rows badly, so real branches won against all 25 partitions tested and all 53,130 choices of five, for a reason unrelated to co-access structure. | Adopted, option 1 of the three the auditor offered: PART_K is scored on exploited structure, each layout's misses relative to its own cost on the null (§7). The five seeds, the aggregate-plus-every-partition rule and the 0.80 margin are unchanged. The raw ratio is reported and labelled. **This is the substantive change the human lead has not yet seen.** |
| **RM1.** "At R = 1 every layout gives identical results" is false above the smallest cache, and as a stop condition would have halted the study. | Adopted: the invariant is restated (§4, §10). |
| **RM2.** The decision layer was not a total function. | Adopted: per-stream labels including direction; a four-row description of the stream pair; four decision classes per tree kind; an ordered recommendation table (§7a, §9). |
| **RM3.** Stream B tracing was under-specified; reusing P7-A's routine would have computed a loss on stream B. | Adopted: exact handling, byte-identical regeneration of existing traces in the same process, and a stream-B identity manifest committed before any simulation (§7a). |
| **RM4.** Layout hashes could not be reproduced from the text. | Adopted: swap positions, group order at R = 512 and a canonical layout hash are defined, and the five partition hashes are registered (§4). |
| Minor 1–14. | Adopted: effective slots and the undefined case for the adjusted ratio; the shared-slope caveat; caps as sequential active time; one consistent list of layouts simulated on nulls; distinct null seeds for stream B; §0 figures updated to the registered configuration; partition hashes; redundant clause wording left in for clarity; revision-2 leftovers removed; the non-branch-specific outcome reworded to cover degenerate and tie-dependent cases; the auditor's re-simulation sample registered and L-NCOAX added to its rebuild; stream B simulated unconditionally and its hashes committed first; reconstruction to reproduce the P1–P5 panel hashes; split-half stability registered as a measurement. |
| **Not adopted.** Partitions that preserve each branch's popularity profile (the auditor's option 2). | Stated as a limit in §7. |

## 14. Decision requested from the human lead

The human lead's review of revision 2 settled the direction, the governance for this study and the registered choices (§15), and a later message gave approval to proceed once the amended ADR is pushed (§15). One point is put back for confirmation before anything runs, because it changes a rule the human lead asked for:

1. **Confirm the corrected five-partition rule (§7, PART_K).** The five predetermined seeds, the aggregate rule and the 0.80 margin are as directed. What changed is the quantity compared: exploited structure (each layout's misses relative to its own cost on a popularity-only null) in place of raw misses, because the re-review showed the raw comparison would have passed for any random partition. Without this change the arbitrary-partition control would have been decorative.

Everything else in revision 4 is correction or clarification of the approved design.

## 15. Record of human direction

**Review of revision 2, 2026-11-13.** The human research lead reviewed draft PR #4 and ADR-0014 revision 2 and wrote:

- "My preferred direction is **option (b): existing evaluation stream plus a prospective replication on validation ranks 2560–3071**."
- "The arbitrary-partition control currently uses only one random partition. Propose five predetermined partition seeds, with a fixed aggregate comparison rule, identical fitting budgets and revised resource accounting. Have Opus independently review that amendment. Do not inspect evaluation outcomes during this revision."
- "I otherwise accept the proposed same-query affinity, bounded refinement, utilization-adjusted analysis, both eviction tie rules, registered margins and decision framework as reasonable bounded descriptive choices."
- "For governance, I support a **study-specific Claude workflow for P7-B only**, retaining ADR-0012 as pending and human approval for later phases. Do not label this Astra validation."
- "Freeze all code, parameters, seeds, thresholds and outcome classifications before running either evaluation stream. Verify that the fresh panel is unused. Run and report both streams without outcome-dependent changes."
- "Keep P1–P7-A immutable and preserve unsuccessful results. Do not begin SSD work, additional training, capacity scaling, publication or merging."
- "Prepare the amended ADR and Opus re-review for my final execution approval. **This message is not authorization to execute P7-B yet.**"

Recorded effect: the direction (option b), the study-specific governance, and the registered choices listed in the third bullet are accepted by the human lead. Execution is **not** approved.

**Later message, 2026-11-13,** sent while the re-review of revision 3 was still running: "I've read the adr and seems logic to me, please proceed with the validation once you finish the push of pr 4".

The lead reads this as approval to execute P7-B once the amended ADR is pushed. Two cautions are recorded with it. First, at that moment PR #4 showed revision 2 and revision 3 existed only as a local file, so it is not certain which text the human lead had read. Second, the re-review then found a blocker whose fix changes a registered rule. The lead had told the human lead that a substantive change would be brought back before anything runs, and does so in §14.

### Execution approval

*Conditional: given in the message above for the document as amended and pushed; the lead is holding execution until the human lead confirms the corrected PART_K rule in §14. Nothing has been implemented or run.*
