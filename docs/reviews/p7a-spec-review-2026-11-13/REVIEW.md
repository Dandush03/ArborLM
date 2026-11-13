# Independent review of ADR-0013 (P7-A) mathematical and measurement assumptions

- Label: `AUDITOR REVIEW OF A DRAFT SPECIFICATION — NOT ASTRA VALIDATION — NOT HUMAN APPROVAL`. Astra review: NOT_PERFORMED.
- Reviewer: Claude Opus 5.5 (`claude-opus-5-5`), auditor role, 2026-11-13. I did not write ADR-0013 or any code it refers to.
- Object: `docs/decisions/ADR-0013-p7a-storage-page-locality.md` (untracked draft on branch `claude/p7a-storage-locality-proposal`, read in full, 197 lines).
- Background read: `AGENTS.md`, `docs/RESEARCH_HANDOFF.md` §0–2, `src/arborlm/pilot_model.py`, `src/arborlm/p5_data.py`, `src/arborlm/p2_config.py`, `p3_config.py`, `p4_config.py`, `p5_config.py`, `pilot_config.py`, `pilot_data.py` (ranking recipe), `results/p5-2026-11-13/README.md`, `docs/reviews/p6-results-2026-11-13/README.md`, and the 81 published P5 memory-cell `result.json` files.
- Nothing was run on a model, checkpoint or trace. All numbers below come from the published P5 histograms or from synthetic draws. Scientific choices are marked **PENDING LEAD REVIEW**; I do not choose thresholds.

Severity: **BLOCKER** = the design would produce an uninterpretable or biased answer; **MAJOR** = a material defect in validity, fairness, definition or feasibility; **MINOR** = an ambiguity or a lesser defect; **NOTE** = context or confirmation.

Counts: **2 BLOCKER, 8 MAJOR, 11 MINOR, 8 NOTE.**

---

## 0. Evidence produced for this review

| File | What it computes | Command |
|---|---|---|
| `closed_form_check.py` → `closed_form_check.out.txt` | Closed form for expected distinct pages vs 200,000-draw Monte Carlo | `python3 -I closed_form_check.py` |
| `floor_ceiling.py` → `floor_ceiling.out.txt`, `floor_ceiling.cells.json` | For each of the 81 cells: pages that hold 90 / 99 / 100% of P5 evaluation-panel selections under frequency packing and under L-ID, at all six granularities, vs registered cache sizes | `python3 -I floor_ceiling.py /Users/daniellaloush/dandush03/ArborLM/results/p5-2026-11-13` |
| `irm_null_lru.py` → `irm_null_lru.out.txt` | **Synthetic** frequency-matched independent-sampling null: 8,192 queries per cell, 8 distinct slots drawn by successive weighted sampling from that cell's published histogram; LRU exactly as in draft §5 (ascending page order, warm on the first half) plus a descending-order variant | `python3 -I irm_null_lru.py /Users/daniellaloush/dandush03/ArborLM/results/p5-2026-11-13 8192` |
| `resource_estimate.py` → `resource_estimate.out.txt` (Python 3.15.1), `resource_estimate.py312.out.txt` (project Python 3.12.14) | Enumeration of simulation passes under my reading of the draft; OrderedDict LRU and Fenwick stack-distance cost per access on a synthetic stream | `python3 -I resource_estimate.py`; `uv run --locked python -I docs/reviews/p7a-spec-review-2026-11-13/resource_estimate.py` |

Environment: Apple M5 Max, macOS (Darwin 27.2.0), system `python3` 3.15.1 for the first three scripts, plus project `uv` Python 3.12.14 for the resource benchmark. All scripts use only the standard library and import nothing from `arborlm`. Running `uv run --locked` rebuilt the editable `arborlm` package in the local `.venv`. No tracked file changed.

Failed or corrected attempts: the first `floor_ceiling.py` run printed `hottest_fraction` means as `0.0` because I used `.1f` formatting (my own error). I changed the format to `.4g` and reran. The saved output is from the rerun, and no other value changed. `irm_null_lru.py` was first run with 4-decimal output, which rounded the tiny warm-miss means to 0.0000. I changed it to 6 decimals and reran with the same seed. The rerun was deterministic and identical at the shared precision, and the saved output is from it.

---

## 1. Floor and ceiling numbers from the published P5 histograms

The published histograms (`final.retrieval.selected_slot_counts`) sum to 262,144 = 32,768 × 8 in every cell. Unique-slot counts match `unique_selected_slots` and the draft's §6 figures: flat 221–555 (mean 428.6), fixed 276–488 (383.4), learned 226–434 (313.1).

**The structural fact.** Every registered cache is a fixed fraction of a store of 4,096 rows. In **both** geometries and at **every** block size, the caches therefore hold **512 / 1,024 / 2,048 rows**. That is at least as large as the entire set of rows any checkpoint selects on the panel (at most 555). The hypothetical geometry changes rows per page. It does not change cache rows against working-set rows.

Slots that account for a share of selections (min / median / mean / max over 27 cells):

| | 90% of selections | 99% of selections | all (unique) | effective slots (P5) |
|---|---|---|---|---|
| Flat | 71 / 118 / 121.7 / 188 | 115 / 212 / 216.9 / 312 | 221 / 430 / 428.6 / 555 | 85–199, mean 132.3 |
| Fixed tree | 37 / 92 / 88.5 / 128 | 109 / 182 / 180.7 / 227 | 276 / 385 / 383.4 / 488 | 43–142, mean 96.2 |
| Learned tree | 48 / 70 / 75.1 / 114 | 94 / 139 / 144.2 / 193 | 226 / 299 / 313.1 / 434 | 55–124, mean 83.0 |

4 KiB pages (actual geometry, 32 rows per page) needed to hold those selections. Under **frequency packing by the evaluation counts** ("FREQ-oracle", a lower bound for the draft's calibration-fitted L-FREQ):

| | 90% | 99% | 100% | cells whose 99% / 100% set fits the 64 KiB cache (16 pages) |
|---|---|---|---|---|
| Flat | 3–6 (mean 4.2) | 4–10 (7.2) | 7–18 (13.9) | 27/27 / 22/27 |
| Fixed | 2–4 (3.3) | 4–8 (6.2) | 9–16 (12.5) | 27/27 / 27/27 |
| Learned | 2–4 (2.7) | 3–7 (5.0) | 8–14 (10.3) | 27/27 / 27/27 |

Under **L-ID** (pages ranked by selection mass):

| | 90% | 99% | 100% | fits 16 pages |
|---|---|---|---|---|
| Flat | 44–78 (60.8) | 65–109 (92.0) | 103–128 (123.3) | 0/27 |
| Fixed | 23–57 (42.2) | 56–91 (73.9) | 103–123 (115.0) | 0/27 |
| Learned | 21–46 (33.1) | 35–74 (55.3) | 69–114 (91.2) | 0/27 |

In the hypothetical geometry at 4 KiB (2 rows per page), FREQ-oracle holds 99% of selections in 47–156 pages and 100% in 111–278 pages. The smallest cache is 256 pages. All 81 cells fit at 99%, and 76/81 fit at 100%. The full per-granularity table is in `floor_ceiling.out.txt`.

**Synthetic null (no co-selection, no temporal structure; `irm_null_lru.out.txt`), warm misses per query with the smallest cache:**

| Setting | Flat | Fixed | Learned | Fixed/flat | Learned/flat |
|---|---:|---:|---:|---:|---:|
| actual 4 KiB, FREQ-oracle, 16 pages | 0.000316 | 0.000018 | 0.000018 | 0.057 | 0.057 |
| same, 32 pages | 0.000009 | 0.000018 | 0.000018 | 2.000 | 2.000 |
| hyp 4 KiB, FREQ-oracle, 256 pages (= 512 and 1,024) | 0.0037 | 0.0034 | 0.0025 | 0.90 | 0.67 |
| actual 4 KiB, L-ID, 16 pages | 5.86 | 4.70 | 4.03 | 0.80 | 0.69 |
| actual 4 KiB, L-ID, 64 pages | 1.21 | 0.40 | 0.075 | 0.33 | 0.062 |
| actual 4 KiB, FREQ-oracle, distinct pages/query (no cache) | 3.64 | 3.05 | 2.78 | **0.838** | **0.765** |

Packed layouts drive warm misses to about 10⁻⁵–10⁻³ per query for every architecture. Each tree mean of 0.000018 is a single miss event: one miss in 4,096 measured queries, in 2 of 27 cells. At that level the ratio of means swings from 0.057 to 2.0 between adjacent cache sizes. In the hypothetical geometry, the 256-, 512- and 1,024-page caches give identical misses: these are compulsory first touches, not capacity effects. **This null preserves only marginal concentration. It is not a forecast of the study's values.** Real traces add co-selection (trees confine each query to two branches) and the calibration-to-evaluation mismatch of L-FREQ, neither of which can be estimated without traces.

---

## 2. Uniform analytical reference (draft §5, §6)

Draw k distinct rows uniformly without replacement from a candidate set of N rows, of which m_j lie on page j (Σ m_j = N). Page j is untouched with probability C(N − m_j, k) / C(N, k), so

**E[distinct pages] = Σ_j [ 1 − C(N − m_j, k) / C(N, k) ]**  (general form; register this one)

and when every page holds R candidate rows on P pages (N = PR):

**E[distinct pages] = P · [ 1 − C(N − R, k) / C(N, k) ]**.

Exact values (rational arithmetic) against Monte Carlo with 200,000 draws, k = 8 (`closed_form_check.out.txt`). The absolute difference is ≤ 0.0032 in every case:

| Geometry, block | Flat, whole store | Tree, two branches |
|---|---:|---:|
| actual 4 KiB (R = 32) | **7.7911** (draft "about 7.8": correct) | **6.4876** (draft "about 6.5": correct) |
| actual 16 KiB (R = 128) | 7.1831 | 3.6069 |
| actual 64 KiB (R = 512) | 5.2538 | **1** if the branches are 2b and 2b + 1 (same page); **1.9926** otherwise |
| hyp 4 KiB (R = 2) | 7.9932 | 7.9452 |
| hyp 16 KiB (R = 8) | 7.9523 | 7.6254 |
| hyp 64 KiB (R = 32) | 7.7911 | 6.4876 |

The tree/flat ratio under the uniform model is **0.8327** at the primary setting and **0.994** at hyp 4 KiB. See MINOR m1.

---

## 3. BLOCKERS

### B1 — The primary cached criterion and both legs of PLAUSIBLE sit at a floor. The outcome would be set by tail noise and ties, not by locality (§5 "With a cache", §7 LRU_K, PLAUSIBLE_K, §8)

*Why it matters.* The capacities are 12.5 / 25 / 50% of the store. In rows that is 512 / 1,024 / 2,048 in every geometry and block size, and that already covers the whole selected working set (221–555 rows) of every checkpoint. Under any frequency packing, 99% of selections lie in 3–10 pages at 4 KiB. The 16-page (64 KiB) cache holds that set in **81/81** cells, and the full selected set in **76/81** (§1). The hypothetical geometry does not escape this, because its cache scales with its store: 256 pages hold the packed 99% set in 81/81 cells.

So LRU_K ("tree's calibration-chosen layout vs flat L-FREQ") compares two quantities near zero. What remains is:

- (a) compulsory first touches of rare slots in the second half;
- (b) slots that are hot on the evaluation panel but were cold on the calibration stream, so L-FREQ placed them by ascending slot ID among the cold rows.

Neither is storage locality. (b) measures how stable each checkpoint's hot set is between the WikiText-2 train and validation splits.

The ADV arithmetic then fails in both directions:

- If both means are 0, "mean ≤ 0.80 × mean" holds (0 ≤ 0) while the strict-lower counts fail on ties.
- If both means are about 10⁻⁵ to 10⁻⁴ (a handful of miss events), the ratio is noise. The null swings it from 0.057 to 2.0 between adjacent cache sizes.

PLAUSIBLE requires LRU in both geometries, i.e. two floor-bound tests joined by AND. The likely registered result is a FAIL by ties. §8 would then report "no hierarchy-specific storage advantage … not justified", when the actual cause is that a 64 KiB cache holds everything any architecture uses.

*Suggested change* (thresholds PENDING LEAD REVIEW):

1. Register a **non-degeneracy precondition** for every cached criterion: for example, a minimum number of capacity-miss events in the flat arm, with misses decomposed into compulsory (first touch in the stream) and capacity/conflict misses. If the precondition fails, the criterion is recorded as **DEGENERATE / UNRESOLVED**, not PASS or FAIL. §8 needs a row for that outcome.
2. Add caches **smaller than the working set**, specified in rows or pages rather than as a fraction of the store. The informative range at 4 KiB actual is about 1–8 pages (32–256 rows). At hyp 4 KiB it is about 8–128 pages. An alternative is to set capacities relative to each checkpoint's 90% working set, but that is architecture-dependent and needs a lead decision.
3. State explicitly which regime carries the storage question. At the registered sizes the primary setting is the least informative one.
4. Register the tie rule for all-zero pairs and zero means (see M6).

### B2 — Nothing separates selection concentration from co-selection or branch structure, and §8 misattributes concentration to flat (§4, §7 PQF/LRU, §8 rows "BR fails" and "PLAUSIBLE passes")

*Why it matters.* The architectures differ strongly in marginal concentration:

- effective slots: flat 132, fixed 96, learned 83;
- unique slots: 429 / 383 / 313;
- 90% of selections held by 122 / 89 / 75 slots on average.

Under L-FREQ, a more concentrated histogram means fewer pages per query and fewer misses, whatever the hierarchy does. In the synthetic null, which preserves only each checkpoint's marginal and draws queries independently, learned-tree L-FREQ distinct pages per query is **0.765×** flat. That would satisfy PQF's 0.80 mean clause on concentration alone; fixed is 0.838×. L-ID warm misses at 64 pages are 0.062× flat for learned trees, again with no co-selection at all.

§8's row "BR fails → any tree advantage comes from concentration of selections, **which flat shares**" is contradicted by the published histograms: flat is the least concentrated. A PASS of PQF, LRU or PLAUSIBLE could therefore be produced by the trees using fewer distinct slots. That is a utilization property and arguably a capacity cost relevant to H5. It would then be reported as "a value-locality advantage over a fairly laid-out flat memory".

*Suggested change:*

1. Add, per checkpoint and per stream, the **frequency-matched independent-sampling null**: 8 distinct slots per query drawn from that checkpoint's own evaluation marginal, with a registered sampler and seed, simulated with identical layouts and caches.
2. Report the decomposition: uniform reference → concentration (null) → co-selection (order-shuffled real trace minus null) → temporal locality (ordered minus order-shuffled).
3. Allow hierarchy-attribution language in §8 only if the tree's advantage over flat exceeds what the two nulls predict. Rewrite the "BR fails" row.
4. Report unique and effective slots next to every locality result, so that an advantage bought by using less of the memory is visible.

Whether concentration counts as a hierarchy benefit or a cost is **PENDING LEAD REVIEW**.

---

## 4. MAJORS

### M1 — The LRU rule is ill-defined or degenerate when a query needs more pages than the cache holds (§5 "With a cache"; §9 hand tests)

The capacities at 64 KiB are 1 / 2 / 4 pages and at 16 KiB the smallest is 4, while a query can touch up to 8 value pages, plus key pages in SSD-index. With pages touched in ascending order, a query's low pages evict its own high pages before the next query can reuse them. At a capacity of 1 page, a hit is possible only when the next query's lowest page equals this query's highest page.

The cached metric then collapses to the no-cache count. In the null at actual 64 KiB, L-ID, 1 page: warm misses 5.2451 per query against 5.2469 distinct pages per query. Ascending versus descending order differed by at most 0.003 per query in my null (small, but structurally arbitrary). With co-selected real traces it can matter more.

The draft also does not say how key pages and value pages interleave in the SSD-index shared cache.

*Fix.* Either:

- define **batch-atomic** query semantics: hits are the pages already resident; misses are inserted; eviction chooses the least recent page not used by the current query; this needs capacity ≥ the query's page count, and settings below it are reported as N/A; or
- register a capacity floor of 8 value pages (plus key pages in SSD-index).

Also register the key/value interleaving order. The §9 hand test "cache of one page" should then test the declared semantics.

### M2 — The layout menu favours trees, and the trees' layout is selected in-sample (§4, §7 "Tree's calibration-chosen layout")

Trees get the best of three layouts (L-ID, L-FREQ, L-BFREQ). Flat gets one. Flat has no structural layout analogous to branch placement, although one is cheap and needs no trace: cluster flat's keys, for example into 16 groups of 256 by a registered deterministic procedure, and place each cluster contiguously.

L-FREQ and L-BFREQ are fitted on the calibration stream and then scored on the same stream. That favours the fitted layouts over L-ID, and with misses near zero (B1) it is decided by the tie rule. The draft also does not say at which block size and geometry the choice is made, or whether it is re-made for each robustness setting.

*Fix* (PENDING LEAD REVIEW):

- either use the **same layout rule** for both architectures in the primary criterion (tree L-FREQ against flat L-FREQ), with the tree's best-of-three reported as secondary;
- or give flat an equally sized menu, including a key-clustered contiguous layout, chosen by the same rule.

Make the selection out-of-sample (fit layouts on calibration contexts 0–255, choose on 256–511) and state the granularity at which the choice is made.

### M3 — A conservation check fails by chance half the time and is a stop condition (§9, §10)

"Results under L-ID and L-RAND agree for flat within the spread of the three permutations." If flat slot IDs carry no structure, L-ID and the three L-RAND results are four exchangeable values. The probability that L-ID lies outside [min, max] of the other three is **2/4 = 1/2** for continuous values. §10 stops the study on "any … conservation violation", so this check would halt a correct run about half the time.

*Fix.* Make it report-only, or replace it with a registered tolerance, for example relative to the permutation standard deviation over many cheap extra permutations.

### M4 — The resource plan is unenumerated and probably over the 3,600 s cap; no algorithm is specified (§10)

The draft does not list the configuration count. Under my reading:

- RAM-index: flat 5 and tree 6 value layouts × 6 granularities × 3 evaluation streams, plus tree calibration-selection passes, for 9,234 passes of ≤ 262,144 accesses each;
- SSD-index: value layouts crossed with 2 key layouts, sharing one cache.

That gives an upper bound of **5.18 × 10¹⁰ page accesses** with a separate pass per capacity, and **1.73 × 10¹⁰** if one pass serves all capacities. SSD-index accounts for about 86% of this, mostly flat's 64-key-page scan per query at 4 KiB.

Measured cost on this machine, synthetic stream: an OrderedDict LRU at **78 ns per access** (project Python 3.12.14) gives about **4,050 s**, over the cap. A pure-Python Fenwick-tree stack-distance pass costs **2,456 ns per access**. It is exact (identical miss count) but about 30× slower per access, so "one pass for all capacities" in pure Python is **not** a saving, at about 42,000 s.

Per-query sorting and deduplication, trace I/O, nulls and the auditor's independent simulator on ≥ 9 checkpoints (§9) are not counted, and neither is the slower registered machine, if different. Because "configurations are never dropped … the study stops", the likely outcome is a registered stop.

*Fix:*

1. Register the exact enumeration, including whether key and value layouts are crossed.
2. Remove the flat full-scan key simulation. An exact analytic rule is available: when the per-query key pages are at least the capacity, every key access misses and the cache is flushed. Or use separate key and value caches (M5).
3. Prescribe the algorithm: one OrderedDict pass per capacity, or numpy-vectorised per-query batch processing.
4. Require a timed dry run on synthetic traces of full size before approval.
5. State whether the auditor's simulator time counts against the caps.

### M5 — The SSD-index shared cache makes value-side results in that regime determined by construction (§5 "Two index regimes")

At 4 KiB, flat reads 64 key pages per query, and every cache is 16–64 pages. Every query therefore flushes the cache, so flat's value pages always miss as well. At 64 KiB, flat reads 4 key pages against caches of 1–4 pages, with the same effect. Tree key pages are 8 per query under L-ID and about 64 under L-RAND keys. The value-side comparison in SSD-index is thus fixed by construction, beyond the key reads the draft already labels analytical.

*Fix.* Use separate key and value caches, or report SSD-index keys analytically and take value results from RAM-index only. Specify whether key L-RAND is crossed with each value layout and whether it uses the same permutation seeds.

### M6 — ADV is undefined at zero and has no minimum effect (§7)

Ratios of means avoid 0/0 per pair but not at the level of means. When both means are 0, the mean clause passes while the count clauses fail on ties. "Strictly lower" makes exact ties (likely at the floor) count against the tree. Nothing requires a minimum absolute difference, so 0.000018 against 0.000316 per query (one miss event against a few) "passes" the mean clause.

*Fix* (PENDING LEAD REVIEW): define the zero/zero case, the tie treatment and a resolution floor below which the clause is DEGENERATE (ties in with B1).

### M7 — The NVMe decision rule is both too permissive and too strict for a 768 KiB memory (§8 "Is an NVMe experiment justified?")

*Too permissive.* A PLAUSIBLE pass on these checkpoints cannot justify an NVMe experiment *on these checkpoints*. The value store is 512 KiB, smaller than the 1–4 MiB caches in the hypothetical geometry and than any OS page cache. A device run would measure page-cache hits, and B2 means a pass may reflect lower utilization.

*Too strict.* A FAIL at the floor (B1) is not evidence against hierarchical locality at a scale where the working set exceeds the cache.

*Fix.* Make the decision rule conditional on non-degeneracy and on beating the concentration null (B2). Re-scope the positive branch to "supports drafting a proposal for a larger-memory study, which requires new training". State that a FAIL in a degenerate regime is UNRESOLVED (PENDING LEAD REVIEW).

### M8 — "The stream resembles reading text" is an overclaim that limits every temporal-locality metric (§3 "Query streams", §5 controls, warm/cold split)

Panel and calibration contexts are hash-ranked chunks (`pilot_data.py`: rank = sha256 of split, row and offset), so consecutive contexts are unrelated 64-byte windows. Attention restarts at every context, and the position-0 query depends on one byte only (at most 256 distinct values per checkpoint), which gives a period-64 recurrence. Temporal locality therefore exists only inside 64-query windows.

Rank order carries no text order, so the **context-shuffled control is an exchangeable redraw**: it gives a variance estimate, not a test of rank-order structure. Warm-up over 16,384 queries is ample for caches ≤ 64 pages. At the hyp 4 KiB caches, which hold everything, warm misses are only compulsory first touches; the null gave identical values at 256, 512 and 1,024 pages.

*Fix.*

- Replace the wording with "512 independent 64-byte teacher-forced windows; attention restarts at each".
- Report reuse within a context and across context boundaries separately.
- Describe the context-shuffled stream as a variance and redraw check.
- State that no conclusion about locality over longer text or generation (decode) is supported.

---

## 5. MINORS (one paragraph each)

- **m1 (§5, §6, §7 PQ).** Register the general form Σ_j[1 − C(N − m_j, k)/C(N, k)]. The P·R form does not cover 64 KiB actual, where a branch is half a page and the result is 1 or 1.99 depending on whether the two visited branches share a page. The uniform reference over the whole store is not the relevant null given concentration (B2). Also: PQ's 0.80 threshold lies just below the by-construction ratio 0.8327 at the primary setting, and at hyp 4 KiB the by-construction ratio is 0.994, so PQ there needs about 20% beyond construction (PENDING LEAD REVIEW; flagged, not judged).
- **m2 (§2, §7 robustness).** Hypothetical 64 KiB is identical to actual 4 KiB: R = 32 and 16 / 32 / 64 cache pages in both. That is one configuration counted twice. Drop it or label it as a duplicate.
- **m3 (§5 page reuse).** "Fraction of a query's pages touched by the previous query" can be a mean of per-query fractions or a pooled ratio. The handling of the first query, context boundaries and the 64-query window at stream start is unspecified.
- **m4 (§5 branch locality).** The top-1 run lengths and the "consecutive queries" fractions do not say whether they cross context boundaries.
- **m5 (§5 read amplification).** "Bytes read per query = misses × block size, with amplification as above" mixes the cached and uncached definitions. At 64 KiB actual, amplification is at least 64 for everyone by construction. State this, and define cached amplification separately.
- **m6 (§7).** The tree-layout choice does not specify block size or geometry, or whether it is re-chosen per robustness setting (also in M2).
- **m7 (§6 vs §7).** P7-H2 says "the better of L-FREQ and L-BFREQ"; §7 chooses among L-ID, L-FREQ and L-BFREQ. Make them consistent.
- **m8 (§7 statistics).** The 9 parents are 3 backbones × 3 order seeds, and pairing flat and tree "by seed" is nominal (shared seed integers, different variants). All 27 cells see one fixed stream, so the 22/27 and 8/9 counts describe training-randomness consistency only, with no data-sampling variability. A descriptive bootstrap over the 512 contexts would show sensitivity to the data. This is not a significance test.
- **m9 (§3 calibration).** The draft says the *additions* never trained on ranks 2048–2559. The registered configs show the backbones never did either: P2 `train_rank_interval [0, 2048]`, P3 `used_train 2048` cycled, P4 and P5 `train_ranks [0, 2048]`. State this. I did not trace each parent's provenance chain bit by bit. The calibration stream comes from the train split and the panel from the validation split, so L-FREQ ranking across splits is part of what is measured (B1(b)). This mismatch applies to all architectures and is not a leak.
- **m10 (§9).** "P5's per-slot histogram reproduced exactly from the evaluation trace" is good. Also require that the trace's stream order (context order, then position) matches what the simulator consumes, since P5 evaluated 8 contexts per batch.
- **m11 (§10).** The auditor's independent simulator (§9) has no budget and no statement of whether it counts against the caps.

---

## 6. NOTES

- **n1.** Independently recomputed: the §2 table (rows per page, pages, pages per branch, key pages, 768 KiB, 8 MiB hypothetical store), the §5 cache page counts, the §6 utilization ranges, and the uniform values 6.49 and 7.79. All are correct.
- **n2 (§3 fairness, in the trees' and flat's favour equally).** The memory sits after frozen block 0, so for a given parent the pre-memory hidden states are **identical** across flat, fixed and learned. Only `wq` differs. "Identical query traces" is stronger than the draft says. A cheap bitwise check of the block-0 output across the three architectures per parent would make that a registered fact.
- **n3 (§5 router).** Holding the 1 KiB router in RAM is a negligible bias and is disclosed. In the SSD-index regime, the trees' dependent read depth (router, then keys, then values) is not modelled, consistent with §5's exclusions.
- **n4.** P6-Q found tree selections recover 0.79 (fixed) and 0.92 (learned) of exhaustive selections. Any tree locality is the locality of an approximate search. P6 LOSS found no material prediction penalty, so this is context, not a defect.
- **n5 (nice to have).** A Belady/OPT bound per setting, computed from next-use indices, would show the headroom any layout or cache policy has. Per-context working-set size is already partly covered by "distinct value pages per context".
- **n6 (H3, H4, H5).** I agree with §1 that P7-A is a baseline for H3, a screen for H4 and silent on H5. It cannot say anything about device time, about locality under a locality objective, or about a memory whose working set exceeds RAM. Even a clean pass concerns a 512 KiB value store whose entire selected set fits in 64 KiB.
- **n7.** The draft's "true by construction" framing of index reads (§1 item 1, IDX) is correct and appropriately not a criterion.
- **n8.** Running `uv run --locked` rebuilt the editable `arborlm` install in the local `.venv`, as noted in §0. No tracked file changed.

---

## 7. Omissions, separated

**Needed for validity:**

1. A frequency-matched independent-sampling null per checkpoint (B2).
2. A non-degeneracy precondition, a DEGENERATE outcome, and caches below the working set (B1).
3. A compulsory versus capacity miss decomposition (B1).
4. Batch-atomic query semantics or a capacity floor (M1).
5. Equal layout menus or a same-rule primary criterion, with out-of-sample selection (M2).
6. A replacement for the 50%-false-alarm check (M3).
7. A configuration enumeration with an algorithm and a dry run (M4).
8. Separate key and value caches or an analytic SSD-index treatment (M5).
9. Zero and tie rules (M6).

**Nice to have:**

- a Belady/OPT bound;
- a key-clustered flat layout, if not adopted under M2;
- a context bootstrap;
- a block-0 hidden-state identity check (n2);
- a co-access clustering layout (already a stated limit in §11);
- utilization reported beside each locality metric.

---

## 8. What this review did not check

- Calibration-to-evaluation hot-set stability, co-selection within queries, actual per-query page counts for trees, and temporal reuse. All of these need traces, which I was not permitted to generate. The null in §1 ignores the trees' two-branch confinement and therefore **understates** tree locality under L-ID.
- Whether the tie rule and ordering in `stable_top` affect trace content beyond what P6-E already established.
- The full parent provenance chain beyond the registered rank intervals in the config files.
- Timing on the registered execution machine. My estimates are micro-benchmarks on synthetic streams on an Apple M5 Max and are not registered benchmarks.
- Anything about Astra validation, human approval, or whether P7-A should be run. Those decisions belong to the lead and the human.
