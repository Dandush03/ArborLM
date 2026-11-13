# P7-A results and review — storage-page locality of the existing P5 memories

- Label: `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW`.
- Specification: [ADR-0013](../../decisions/ADR-0013-p7a-storage-page-locality.md), human-approved 2026-11-13, with one human-approved pre-outcome amendment (§14 item 8). Frozen at commit `e95cec6`; raw records committed at `61657cf` before interpretation.
- The study ran exactly once: trace, simulate, independent-simulator check, analyze. Nothing was rerun, retuned or selected. P1–P6 are unchanged; the P5 composite remains FAILED and P6-E's timing verdict remains INCONCLUSIVE.
- Reviewer: Claude Fable 5.2. Independent recomputation: Claude Opus 5.5, [`../p7a-results-audit-2026-11-13/AUDIT.md`](../p7a-results-audit-2026-11-13/AUDIT.md): 28,545 values compared with the implementation's analysis, zero differences; the primary setting and the concentration null re-simulated from raw traces for all 81 checkpoints. Who did what: [DELEGATION.md](DELEGATION.md).
- This is a page-count simulation on traces. No storage device was used, and nothing here is a measurement of I/O, latency or throughput.

## 1. Registered outcome

**CONCENTRATION-ONLY for both tree kinds.**

Primary setting: keys in RAM, value store only, two value rows per page (a hypothetical 2,048-byte row at 4 KiB), cache of 32 pages (64 rows), frequency-packed layout for every architecture, evaluation stream. Metric: warm capacity misses per query.

| Criterion | Fixed tree | Learned tree |
|---|---|---|
| Setting non-degenerate | yes | yes |
| **LRU_K** — fewer cached value-page reads than flat | **HOLDS**: 2.100 vs 3.164, ratio 0.663; 24/27 pairs; 9/9 parents | **HOLDS**: 1.650 vs 3.164, ratio 0.521; 27/27; 9/9 |
| **CONC_K** — the same advantage in a null that keeps only each checkpoint's slot counts | **HOLDS**: ratio 0.687; 24/27; 9/9 | **HOLDS**: ratio 0.535; 27/27; 9/9 |
| **Outcome** | **CONCENTRATION-ONLY** | **CONCENTRATION-ONLY** |
| **BR_K** — contiguous branch placement beats slot-wise placement | **FAILS**: ratio 0.989 | **FAILS**: ratio 0.983 |

In the permitted wording fixed before the run (ADR-0013 §8): **the trees touch fewer pages because they use less of the memory.** That is not a property of hierarchical placement.

## 2. What the numbers say

**The trees do read fewer cached pages than a frequency-packed flat memory**, by 34% (fixed) and 48% (learned) in the primary setting. This contradicts the first half of the lead's own registered prediction P7-H1, which expected no such advantage. That prediction failed and is recorded as failed.

**The advantage is explained by utilization.** The null stream keeps each checkpoint's exact per-slot selection counts and destroys which slots are selected together and in what order. It reproduces 98% of the flat-minus-fixed gap and 103% of the flat-minus-learned gap. Across all 81 checkpoints, a checkpoint's effective slot count alone accounts for 96.6% of the variance in cached misses, and adding the architecture label adds 0.07 of a percentage point. The second half of P7-H1 held.

| | Flat | Fixed | Learned |
|---|---:|---:|---:|
| Distinct slots selected over the stream | 428.6 | 383.4 | 313.1 |
| Effective slots | 132.3 | 96.3 | 83.0 |
| Share of selections outside the 64 hottest rows | 28.5% | 18.1% | 13.9% |
| Warm capacity misses per query (primary) | 3.164 | 2.100 | 1.650 |
| P5 final NLL relative to flat | — | +0.0008 | +0.0014 |

In effect the primary metric measures how much of a checkpoint's selection mass falls outside the rows the cache can hold.

**Structure beyond concentration exists, is small, and is not specific to trees.** Every checkpoint of every architecture has fewer misses on its real trace than on its own null: by 5.6% for flat and about 8.6% for the trees. The trees' extra three points come mostly from reuse over several queries within a context, not from slots being selected together within a query, which is where branch structure would show.

**Branches do not persist.** The top-1 branch stays the same from one query to the next 19.6% (fixed) and 20.8% (learned) of the time, at or below what the branch frequencies alone would give (21.8% and 23.2%). A context of 64 queries visits 13.1 (fixed) and 10.1 (learned) of the 16 branches. Contiguous branch placement reduced cached misses by 1–2% in the primary setting.

**The three requested block sizes at the true row size are degenerate, as predicted.** With 128-byte rows at 4, 16 and 64 KiB, 29 of the 30 (tree kind × capacity × block size) settings fail the non-degeneracy condition: the hot rows fit in the cache. At 4 KiB with a 32-page cache, frequency-packed misses are 0.0004 per query or fewer for every architecture, and exactly zero from 64 pages up. The one non-degenerate cell (4 KiB, 8-page cache, fixed tree) fails both LRU and CONC on the pair count.

**Frequency packing matters far more than architecture.** In the primary setting it cuts misses from 5.21 to 3.16 for flat, 4.20 to 2.10 for fixed, and 3.80 to 1.65 for learned. A layout fitted on the calibration stream transfers almost perfectly: 0.02% of evaluation selections land on slots the calibration stream never selected.

**Per-query page counts in the natural layout** at 32 rows per page: fixed trees touch 0.809 and learned trees 0.768 of flat's pages per query, against 0.833 expected purely from the trees' candidates spanning 16 pages instead of 128. So the fixed tree's per-query advantage is essentially by construction, and the learned tree shows about 8% beyond it.

## 3. What this means for H3, H4, H5 and the NVMe question

- **NVMe on these checkpoints: not justified.** This was fixed before the run and the results agree with it: at the true row size, with packing, cached misses are effectively zero. A device run would measure the operating system's page cache.
- **A storage study on the strength of the existing hierarchy: not justified by this evidence.** The registered rule recommends proposing one only on a robust STRUCTURAL ADVANTAGE. The outcome is CONCENTRATION-ONLY for both tree kinds.
- **H4 (SSD viability):** no hierarchy-specific argument at this size. A flat memory that used as few rows as the trees would read as few pages.
- **H3 (locality):** this is the baseline with no locality objective. It carries a warning for any future test of H3: a locality objective could appear to succeed simply by concentrating selections on fewer rows. Any such test needs a count-preserving null like this one.
- **H5 (scaling):** untouched. One memory size.
- **If keys are on storage,** a tree reads far fewer key pages than a flat scan (about 1.5 and 0.6 per query for fixed and learned in the primary setting, against all 64 for flat). That is true by construction, vanishes when keys fit in RAM, and was not a criterion.

**Is lower utilization a benefit or a cost?** The trees use fewer stored rows, read fewer pages, and lose 0.0008–0.0014 nats/byte to flat, a difference the P5 design cannot resolve. One reading is that they get the same quality from less storage traffic. The other is that they waste stored capacity that flat puts to use. P7-A cannot choose between them. What it does establish is that the effect is concentration, which any architecture could be pushed toward, and not placement.

## 4. Two things worth a second look (not registered results)

- **Branch-aware packing.** Keeping branches contiguous and packing hot rows within each branch (L-BFREQ) gave fewer misses than plain frequency packing for the trees: 1.78 vs 2.10 (fixed) and 1.42 vs 1.65 (learned), about 15% lower. This layout was outside the registered comparison, and flat's natural counterpart, clustering rows that are selected together, was deliberately not built. It is a lead, not a finding.
- **Multi-query reuse.** The small structure beyond concentration comes from reuse across several queries in a context. Its size (3 points more for trees than flat) is within what an unbuilt co-access layout for flat might also capture.

## 5. Limits

- The primary setting uses a hypothetical row size. At the memory's true row size the question is degenerate.
- One memory size (4,096 slots, 768 KiB), one corpus, one evaluation stream of 512 unrelated 64-byte contexts. The 27 cells per architecture share nine parents and three seeds; the consistency counts describe robustness to training randomness only. Context-bootstrap intervals are 10–20 times narrower than the spread between checkpoints and do not cover training randomness.
- Frequency packing is not the best possible flat layout. Nothing here compares the trees with a flat memory under co-access clustering.
- The three architectures are different trained checkpoints receiving identical input bytes; their query vectors differ.
- Page counts only. No device, no latency, no read-ahead, no batching, no optimal caching.
- The registered eviction tie rule (ascending page number) slightly penalizes frequency packing; with descending order misses fall 2.7–3.8% and no verdict changes.

## 6. Defects in the records

- **SSD-index key-read table, tree keys under slot-wise key placement: invalid.** The cache simulator lets the cache exceed its capacity when one query needs more pages than the cache holds. Value queries never do (at most 8 pages, capacity at least 8), so no criterion is affected. Tree key reads under the random key layout do (64 key pages per query), and the recorded near-zero misses there are an artefact; flat's key reads are computed analytically under strict capacity, so that table compares two different cache models. The contiguous-key numbers quoted in §3 are valid. Found by the auditor after the run; the records are left as written.
- Stage manifests record the orchestrating process's thread settings, not the workers'; the workers apply single-thread deterministic mode in code, and every NLL replay was bitwise, but no worker record states the setting.
- Simulate and analyze manifests record `git_dirty: true`, consistent with untracked result files written by the earlier stage; not verified further.
- The freeze was committed locally and not pushed before execution, as for P6.
- All four roles are Claude models; the auditor wrote the independent simulator and the null generator's reference implementation that the study's tests compare against.

## 7. Questions for the human research lead

1. **Direction.** The existing hierarchy shows no storage-relevant structure beyond using fewer rows. Options, each needing its own specification and approval:
   - **Stop the hierarchy line** on efficiency and storage grounds, keeping "sparse learned memory adds capacity to a frozen backbone" (P4, P5) as the positive finding.
   - **Test H3 directly:** train with a locality objective and judge it against a count-preserving null, so that concentration cannot pass as locality. This involves training.
   - **A layout study:** co-access clustering for flat against branch-aware packing for trees, on the existing traces, no training. Cheap, and it would settle whether the 15% from branch-aware packing is hierarchy-specific.
   - **A larger memory,** where storage would matter, which involves training and where none of the present results is known to hold.
2. **Is concentration desirable?** Whether using fewer stored rows should count for or against an architecture needs a decision before any study that could reward it.
3. **Governance.** ADR-0012 is still open.
