# ADR-0031 — P10-I-S6: does the flat memory's lead over the dense adapter persist at convergence on fresh data?

**Status: DRAFT 3 — NOT APPROVED. Reviewed twice by the `arbor-auditor` subagent (Claude Opus 5.5); second verdict READY AFTER THE LISTED EDITS; those edits are applied in this draft and have not been re-read. Decision 1 is the human lead's own. Nothing under this ADR may be implemented, downloaded, rehearsed, frozen or run.**

> **For the human lead.**
> - **What it can tell you.** If both arms converge within 16 times the old duration: whether the flat memory's lead over an equal-size dense adapter holds at convergence, on new parents and new data.
> - **Most likely they will not converge** (P10-I-S3's gain per doubling showed no bend). You then get a registered description of whether the lead held, shrank or was lost up to 262,144 updates, and nothing about the ordering at convergence.
> - **What it cannot tell you.** Nothing about cost, efficiency, SSD, scaling, the tree, other dense forms or other corpora. It does not open ADR-0027's Route A.
> - **Cost.** About 16–31 charged hours on the shared machine; one 0.3 GB download (WikiText-103); 12 small backbones trained from scratch.
> - **Choices that are yours alone (section 20), with the recommended option:** (1) corpus: WikiText-103 raw train, approve; (2) ladder: (a) 16×, no continuation rung; (3) parents: twelve new backbones plus the old-parent anchor; (5) larger dense arm: none; (6) thresholds: unchanged from ADR-0026; (7) label structure: as drafted, with the trend line; (13) convergence measure: ε on both the envelope and the run.
> - **Also yours:** Decision 1 itself (11); the byte-matched store R-KNN (14; drafter: in as a descriptive readout; reviewer: no recommendation either way); no "ordering without convergence" rule (15).

**Most likely outcome, stated first [KNOWN]: CONVERGENCE NOT REACHED.** In P10-I-S3's FRESH regime the gain per doubling was flat at about 0.017 to 0.022 nats/byte from 2,048 to 16,384 updates for both arms (reviewer's recomputation from the public `analysis.json`). To meet ε = 0.001 at the last rung that gain must fall about twentyfold within four doublings, and nothing in the record shows it bending. The recommended design (about 16 to 31 charged hours) will therefore most likely end without a converged comparison. In that case the study still describes whether the lead held over the range it trained, through the registered descriptive trend line of section 12.6 (the lead and its sign counts at every rung up to 16 times the old duration, with one tag from a closed list). That answer is a description of the trained range; it is never a statement about the ordering at convergence and never the label PERSISTS.

- Date: 2026-11-19 UTC. Drafted and revised by an `arbor-lead` subagent (Claude Fable 5.2) on the scientific lead's brief (`experiments/_scratch/BRIEF_P10I_S6.md`). Reviewed twice by the `arbor-auditor` subagent (Claude Opus 5.5): `experiments/_scratch/audits/REVIEW_ADR-0031.md` and `REVIEW2_ADR-0031.md`, both READY AFTER THE LISTED EDITS, no blocking finding. The drafter read records and code only; it ran no training, opened no sealed value and used no network.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- The human lead's words (2026-11-19), as given in the brief: "the most encouraging new result is the longer-trained flat memory's quality advantage. We should investigate whether it persists before making a larger architectural or hardware commitment, let's see if we can validate it"; and earlier the same day: "if there is another study from the P10 that still inconclusive please proceed chasing a result (negative or positive)".
- ArborLM is unproven research. No outcome of this study is a success claim. P1 to P10-I are immutable: no result, threshold, seed, label or ruling of any earlier study is revised or reinterpreted. P10-I-S3's labels stand as recorded.
- **This study is designed knowing P10-I-S3's registered outcome.** Every rule that the observation could have shaped carries the mark **[KNOWN]** with what was known. The primary evidence comes from a corpus, parents, streams, panels and initialisations that P10-I-S3 never used (sections 6, 7, 14).

## 1. Question, outcomes and non-claims

**Question.** On unseen single-pass byte-level text, with a frozen backbone, does the flat key-value memory (M-FLAT) remain ahead of the equal-size dense adapter (D-ADAPT) when both are trained until each has converged by a registered criterion, each at a rate calibrated for that duration, within a registered maximum of 262,144 updates (16 times P10-I-S3's duration)?

Three outcome families are registered. None is the default reading of an unfinished run.

| Family | Meaning | Labels (section 12) |
|---|---|---|
| The lead persists | At the reading rung both arms are converged (or the dense arm is converged and the memory is still improving) and the memory is ahead by the registered rule at that rung and at every later rung | PERSISTS AT CONVERGENCE; MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING) |
| The lead does not persist | Under the same convergence conditions the dense adapter is within the margin, or ahead, or the memory's lead is not established by the counts, or the ordering changes between converged rungs | LEVEL AT CONVERGENCE; DENSE AHEAD AT CONVERGENCE; DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING); LEAD NOT ESTABLISHED AT CONVERGENCE; ORDERING NOT STABLE AFTER CONVERGENCE; MEMORY UNSTABLE (FAILED CELLS) |
| Convergence not reached | At 262,144 updates an arm still improves by at least ε per doubling and the ordering is not implied | CONVERGENCE NOT REACHED (three variants), always with the registered descriptive trend line of section 12.6. **Nothing is claimed about the ordering at convergence.** |

**Non-claims, whatever the outcome.** Nothing about the tree, about hierarchy, about a scalable index (M-FLAT scores all 4,096 keys at every position), about SSD, active computation, cost or efficiency; nothing beyond one corpus kind, byte-level text, one 27,392-parameter backbone family and one addition size; nothing about joint training; no p-value. "Converged" means converged by the rule of section 9 at a constant rate chosen per duration; it is not a statement about the optimum of either arm.

## 2. What is known, and what it could have shaped

Quoted from `results/p10i-s3-run-2026-11-18/OUTCOME.md` and `REPORT.md`; the independent recomputation (`audit/RECOMPUTE.md`) reproduced every label.

| Known fact | Source |
|---|---|
| FRESH regime, 16,384 updates, 27 cells over 9 parents: COMPETITIVENESS[FLAT] = **MEMORY AHEAD (DENSE STILL IMPROVING)**. "Mean Q +0.0127 against 0.005, 27 of 27 cells, smallest parent mean +0.0044." | OUTCOME section 3 |
| Every arm NOT CONVERGED at 16,384 in FRESH: deltas D-ADAPT +0.0172, M-FLAT +0.0208, M-TREE +0.0181 against ε = 0.001. "both arms are still improving by more per measurement interval than the flat memory's lead (0.0208 and 0.0172 against 0.0127), so the ordering at convergence is not identified." | OUTCOME sections 1, 3 |
| The fixed duration was taken against the reviewer's advice to prefer a larger corpus; fresh data ends at 19,064 updates. | OUTCOME section 1; ADR-0026 section 5.2 |
| Selected FRESH rates at 16,384: D-ADAPT 0.01, M-FLAT 0.01 (both interior); M-TREE 0.3, at the edge of the extended grid. | `rehearsal_public.json` |
| Line 1 was read on M-TREE and "passes D2 largely through harm": reassigned values left the model worse than the backbone in 27 of 27 cells (mean B − H_used = −0.150); the batch-mean read was worse in 19 of 27. M-FLAT's D1–D3 were descriptive only. | OUTCOME section 3 |
| A 3-cell parent mean had a standard error of about 0.0012; the nine parents are a 3 × 3 crossing of backbone and order seeds and are correlated. Calibration used three of the nine registered parents. | OUTCOME section 3; ADR-0026 section 5 |
| Route A to ADR-0027 is closed by the open-choice-13 ruling (D-ADAPT NOT CONVERGED). ADR-0027 section 3 names COMPETITIVENESS[FLAT] as never qualifying. | OUTCOME sections 1, 2; ADR-0027 section 3 |
| Measured unit costs at six workers (R2): M-FLAT 0.008237 s/update, D-ADAPT 0.011063, M-TREE 0.028774. Registered run: 621 training items, 21,904 s of training charged on a shared machine, against 16,980 s projected from those rates (ratio 1.29). | `studies/p10i_s3/freeze/plan.json`; `ledger.json` |

**[KNOWN] choices that follow the observation and are disclosed as such:** the choice of M-FLAT as the subject and of FRESH as the only regime (they are where the observed lead is); the start of the ladder at 16,384; the centre of the rate grid (section 8); the exclusion of the tree (section 3); keeping 0.005 and ε = 0.001 unchanged (section 13). None of these is a threshold moved after observation; each is argued on grounds that do not use the observed sign. What cannot be removed: the study exists because the observation was encouraging. The safeguard is that every primary measurement is on new data, new parents and new seeds, and that the negative and unfinished outcomes have labels as reachable as the positive one.

## 3. Scope and exclusions

In scope: two trained arms (M-FLAT, D-ADAPT) and BASE on fresh single-pass data from a new, larger corpus; a five-rung doubling ladder of durations; a convergence rule; a comparison line (P) read at a rung fixed by the rule; a dependence line for the flat memory (D[FLAT]) at the same rung; a replication readout at 16,384 updates (R16); one anchor block on P10-I-S3's nine parents (OA).

Excluded, with the reason:

| Excluded | Reason |
|---|---|
| M-TREE (recommended; open choice 4) | The question is about the flat memory's lead. The tree at 262,144 updates costs about 3.5 times a flat run and its FRESH rate optimum lies above 0.3, outside any grid run so far, so its calibration alone is of the order of 9 charged hours (section 18). Its INCONCLUSIVE line stays open and is not touched. |
| REP and REP-U regimes | The registered label of P10-I-S3 is its FRESH label; repeated data measures fitting of a fixed set (ADR-0026 section 3.3). |
| A larger or deeper dense arm as a registered arm (open choice 5) | Section 5: D-ADAPT is already matched in bytes and uses about 2.9 times M-FLAT's multiply-adds per position. |
| A decaying rate schedule | One change at a time against P10-I-S3; a constant rate keeps "checkpoint c of a longer run is a c-update run" (open choice 10). |
| Any wall-time, throughput or cost reading | Not registered. Seconds are cost records for caps only. Logical work counts are not reported as efficiency. |
| Early stopping on registered values | Every rung always runs (section 9.4). No registered value is read before the analysis stage. |

## 4. Definitions

All losses are next-byte NLL in nats/byte on the registered panel (section 6.4), per cell, computed on the one arithmetic path of ADR-0026 section 16 ruling 1 (per-batch float32 sum, accumulated as a Python float, divided by 32,768). Every comparison is ≥, >, ≤ or < exactly as written, with no rounding.

| Symbol | Definition |
|---|---|
| Rung k, U_k | k = 0..4; U_k = 16,384 · 2^k: 16,384; 32,768; 65,536; 131,072; 262,144. U_max = U_4. U_{−1} = 8,192 is a calibrated duration used only for δ(·, 0). |
| k_max | The index of U_max after the ceiling rule of section 6.5 (4 unless that rule cuts the ladder). Wherever this ADR writes "rung 4", "conv(arm)", "Q(4)", "K\* = 4" or "the last rung", read k_max. Every range or bound that ends at 4 (−1..4, 0..4, k ≤ j ≤ 4) ends at k_max. |
| r(arm, k) | The rate frozen for that arm at U_k (section 8), k = −1..4. |
| H_c(k), A_c(k) | Cell c's NLL of M-FLAT, of D-ADAPT, at update U_k of that cell's run at rate r(arm, k). B_c: the cell's parent's BASE NLL. |
| Q_c(k) | A_c(k) − H_c(k). Positive: memory ahead. C_c(k) = B_c − H_c(k); Cd_c(k) = B_c − A_c(k). |
| L(arm, k) | The arithmetic mean over the 27 registered cells of that arm's NLL at rung k. This is the best-rate envelope: each rung is read from the run at the rate calibrated for that rung. |
| δ(arm, k) | L(arm, k−1) − L(arm, k), for k = 0..4: the envelope's improvement over the last doubling. |
| δrun(arm, k) | The 27-cell mean NLL of the run at r(arm, k) at update U_{k−1} minus the same at U_k (U_{−2} := 4,096 is not used; δrun is defined for k = 0..k_max). |
| Mean, parent mean | Over the 27 cells; over a parent's three cells. No mean that enters a rule is taken over fewer cells (failed-cell rule, section 12.2). |
| j† | The rung in 0..4 with the lowest L(D-ADAPT, ·); on an exact tie, the larger rung. Q†_c(k) = A_c(j†) − H_c(k). |

## 5. Arms, and what "matched" means

Code imported unmodified: `pilot_model.Memory("flat")`, `p4_model.DenseAdapter`, `p4_model.Backbone`. Additions act after block 0 and before block 1. Optimizer as ADR-0026 section 3.1 and section 16 ruling 2 (fresh AdamW over the addition only, betas (0.9, 0.999), eps 1e-8, weight decay 0, global-norm clip 1.0, constant rate, batch 8 × context 64).

| Arm | Trainable parameters | Trainable bytes (float32) | Multiply-adds per position, forward (from the code) |
|---|---|---|---|
| M-FLAT | keys 4,096 × 16 + values 4,096 × 32 + W_q 16 × 32 + W_o 32 × 32 + gate = 198,145 | 792,580 | W_q 512; key scores 4,096 × 16 = 65,536; values 8 × 32 = 256; W_o 1,024: **67,328**, plus the normalisation of the 4,096 × 16 keys once per forward call (about 128 per position at 512 positions) and a top-8 selection over 4,096 scores |
| D-ADAPT (width 3,100) | 3,100 × 32 + 32 × 3,100 + gate = 198,401 | 793,604 | 99,200 + 99,200 = **198,400**, plus 3,100 GELU |
| BASE | 0 | 0 | — |

"Matched" in this study means: trainable bytes within 0.13% (1,024 bytes more for the dense arm), the same number of updates, the same batches, the same optimizer family, the same rate search. In multiply-adds per position the dense arm uses about 2.9 times the flat memory's (198,400 against about 67,456). At every position the dense arm uses all its parameters; the memory uses all 65,536 key parameters, W_q, W_o and 8 of 4,096 value rows. These counts are descriptions of the code, not an efficiency result. **Decision: no larger dense adapter is a registered arm.** Reason: a parameter- or compute-matched dense arm is the arm already present; a wider one would be larger than the memory in both bytes and multiply-adds, and "memory behind a larger dense" would not answer the question asked. What stays unanswered is stated in section 19: the result is against one dense form (one hidden layer of width 3,100 on a 32-wide residual), at one size. Open choice 5 offers a descriptive D-2X arm.

## 6. Data

### 6.1 Why fresh data ended at 19,064 updates

`pilot_data.select` cuts each row of the pinned WikiText-2 raw train parquet into non-overlapping 65-byte chunks, drops duplicates and ranks by a SHA-256 of (split, row, offset). The recorded pool is 156,611 eligible unique train chunks. Ranks 0–2,047 trained the parents, 2,048–4,095 are REP-U, and FRESH is ranks 4,096–156,610: 152,515 chunks. One update takes 8 chunks, so 152,515 // 8 = **19,064** updates (`configs/p10i_s3_longer_training.toml` `[data]`). The limit is the size of WikiText-2, nothing else.

### 6.2 What the ladder needs

One stream to U_max = 262,144 updates uses 2,097,152 unique chunks (about 136 MB of eligible text); 4 times the old duration needs 524,288 chunks; 8 times, 1,048,576. WikiText-2 cannot supply any of these. A larger corpus is required.

### 6.3 The corpus (open choice 1)

**Proposed: WikiText-103 raw (`wikitext-103-raw-v1`), train split only, from the same publisher repository and the same pinned revision as the WikiText-2 acquisition** (`Salesforce/WikiText`, revision `b08601e04326c79dfdd32d625aee71d232d685c3`, `src/arborlm/fetch_wikitext.py`). From the publisher card already held locally (`data/wikitext2/README.upstream.md`): train 546,500,949 bytes of text in 1,801,350 rows; download size of the configuration 315,466,397 bytes. Same kind of text (Wikipedia articles, same raw preprocessing); WikiText-2's train articles are a subset of it, and the two share their validation split. Licence: as recorded for WikiText-2 (card front matter CC-BY-SA-3.0/GFDL, body CC BY-SA 4.0; the discrepancy is unresolved and local use only was approved, `pilot_data.freeze_dataset`). The test split is not fetched. The validation parquet is not fetched: the pinned WikiText-2 validation file already held is used.

- **Download.** At most about 0.32 GB (315,466,397 bytes is the whole configuration; the train files alone are a little smaller). The ledger's header records a 30 GB standing permission (2026-11-15) and the brief cites a 50 GB delegation (2026-11-17); either covers it. The ledger's running total is 1,188,183,868 bytes. The train parquet file names are taken from the repository listing at the pinned revision; one ledger row per file is written before the fetch (URL at the pinned revision, expected bytes and SHA-256 from the LFS metadata, as for WikiText-2) and completed after it; the parquet is read with `pyarrow` in `-I` mode from its own directory; a size or hash mismatch is an engineering stop. The fetch is new code (`studies/p10i_s6/fetch.py`; the existing fetcher hard-codes the WikiText-2 subset and a 10 MB cap) and it runs only after Decision 1. It is listed as an open choice because the licence note of the earlier acquisition is "local use only" with an unresolved discrepancy, which is not routine.
- **Not proposed:** enwik8 / enwik9 (raw XML with markup: a different kind of byte text); text8 (27 symbols: not the same tokenisation problem); repeating WikiText-2 (not fresh).
- **Expected pool, an estimate and not a measurement:** WikiText-2 kept 156,611 × 65 bytes of about 10.9 MB; at the same share, less WikiText-2's own articles, WikiText-103 gives about 7.5 to 7.7 million eligible chunks (the reviewer's estimate; the first draft's 7.6 to 7.9 did not subtract the excluded articles): about 2.5 million in the calibration pool and 5.0 million in the registered pool. The data-preparation stage measures it. The figures of section 6.5 are rules, not expectations.

### 6.4 Disjointness from everything earlier

1. **Articles.** A WikiText-103 train row is an article heading if, after removing leading and trailing white space, it starts with `= `, ends with ` =` and its third character is not `=`. An article is a heading row and the rows up to the next heading. Rows before the first heading form article 0.
2. **Exclusion by article.** Let E be the set of SHA-256 digests of every 65-byte candidate chunk (`select`'s cutting, before de-duplication) of the WikiText-2 train parquet and of the WikiText-2 validation parquet. Every WikiText-103 article that contains at least one chunk whose digest is in E is removed whole. The number of removed articles and chunks is printed. Reason for whole articles: every earlier study trained or evaluated on chunks of those two files (P1–P8 chunk panels, P10-I-S3's REP, REP-U, FRESH and panels, P10-S2's and ADR-0025's windows all come from them), and removing the article also removes row remainders and short rows that a chunk comparison would miss.
3. **The pool.** `select`'s recipe on the remaining rows, with the rank string `p10i-s6-v1:train103:{row}:{offset}` (row = the row's index in the concatenated train files in file order) and with `excluded` = E. The implementation may stream. The order is fixed: (1) the train files are read in lexicographic order of file name, rows numbered consecutively across files; (2) articles are segmented on `str.strip()` of each row; (3) articles with a chunk digest (hex SHA-256 of the 65-byte payload, at `select`'s offsets, before any de-duplication) in E are removed; (4) `select`'s cutting, de-duplication and ranking are applied once to all remaining rows; (5) each kept chunk goes to the pool of the article holding its kept occurrence. The implementation may use compact binary digests and arrays, but a gate proves it equal to `pilot_data.select`: run on the WikiText-2 train parquet with the old rank string, it reproduces the recorded SHA-256 of the first 4,096 train ranks. A second gate: zero digest overlap between the pool and E.
4. **Calibration and registered pools are disjoint by article.** Articles are numbered in file order after the exclusion. Articles with number mod 3 = 2 form the calibration pool; the others form the registered pool. A chunk whose duplicate digest occurs in both keeps its lowest rank (the `select` rule) and so lies in one pool only.
5. **Streams.** A cell's stream is `randperm(pool size)` from one CPU generator seeded with its stream seed, over its pool in rank order; update u (from 0) takes entries 8u to 8u+7 (ADR-0026 section 16 ruling 3). No chunk is used twice in a stream. Registered streams share chunks with each other (each uses about 2.1 of about 5 million); none shares a chunk with any calibration stream.
6. **Panels.** The registered panel, then the calibration panel, 512 chunks each, by ADR-0026 section 4's walk over the pinned WikiText-2 validation ranking, continuing after every span already in the shared panel ledger (`data/p10i-shared/panel_ledger.json`) and after P10-I-S3's two panels; the two new panels are appended to the ledger. If the walk runs out: engineering stop before Decision 2. The parents never saw validation text; the pool excludes it by rule 2.
7. The chunk table is stored as uint8 (one file, hashed, memory-mapped), not as the int64 tensor of `studies/p10i_s3/data.py`, which would be about 4 GB.

### 6.5 Does the change of corpus change the question?

The kind of text does not change; the distribution is wider (about 28,000 articles against about 600) and the parents were fitted to WikiText-2 chunks. So the old 16,384-update figure is **not** carried over by assumption. It is re-anchored twice: **R16**, rung 0 of this study (new parents, new corpus, 16,384 updates), read by ADR-0026's line-2 rule; and **OA**, the old nine parents with new initialisations on the new corpus at 16,384 updates only, which separates the change of corpus from the change of parents. Both are printed beside the line-P label and change no label (section 12.4).

**Ladder ceiling rule (fixed before calibration).** If the registered pool has fewer than 2,097,152 chunks or the calibration pool fewer than 2,097,152, U_max is the largest rung both pools support and the ladder is cut there in the config before any calibration run. If that is below rung 2 (65,536): engineering stop — CORPUS TOO SMALL. No calibration or registered value can move U_max. If the calibration pool is short and defining it instead as the articles with number mod 2 = 1 gives both pools at least 2,097,152 chunks, that definition is used; this is decided by code from counts alone, before any calibration run, and printed. D0 records: candidate chunks, articles and chunks removed, duplicates, both pool sizes, and the eligible validation spans left for the panels.

## 7. Parents and cells

**Fresh parents (open choice 3).** Twelve new backbones are trained by the recipe that produced the nine P3 control parents (the P2 control followed by the P3 continuation to 1,024 updates on WikiText-2 train ranks 0–2,047, memory bypassed), each with its own backbone seed and its own order seed: nine registered parents and three calibration parents. Unlike the old 3 × 3 crossing, no two new parents share a backbone seed or an order seed. The existing code accepts only the registered P1/P2 seeds (`p2_config.Cell.__post_init__`), so the recipe is run through a new adapter in `studies/p10i_s6/`. **Adapter identity gate:** from the recorded seeds and order of each of the nine old parents the adapter must reproduce that parent's recorded backbone digest (`results/p4-2026-11-12/b*-baseline/result.json`) bitwise on the platform of record, before any new parent is trained. The adapter must pass by both seed whitelists (`p2_config.Cell` and `p2_data.order_ids`). The frozen control memory of the old recipe (`Memory("learned_tree", 201)`, built after the backbone) is not constructed for new parents; if the identity gate needs it, 201 is a declared re-use. The new parents are trained on the same 2,048 WikiText-2 chunks as the old ones: "fresh" means new backbone and order seeds, nothing more. If the gate cannot be met, that is an engineering stop before Decision 2 and the human lead decides between an amended recipe and open choice 3's alternative; the study does not fall back silently. Training twelve 27,392-parameter backbones for 1,024 updates is new training and needs the human lead's explicit approval, which Decision 1 would carry.

**Cells.** 9 registered parents × 3 initialisation seeds = 27 cells per arm. Every cell has its own addition seed and its own stream seed (section 14); both arms of a cell share the stream. Calibration: 3 calibration parents × 1 seed = 3 cells, on the calibration pool and the calibration panel. **Why nine parents and 27 cells:** the counts 22 of 27 and 8 of 9 are then ADR-0026's, unchanged, and no count had to be chosen after the observation. Nine parents with independent seeds are less correlated than the old nine. They are still one corpus and one recipe, not nine independent replications of anything wider, and no p-value is computed. More parents are open choice 3b.

**OA block.** The old nine parents (read-only, verified by hash as `studies/p10i_s3/parents.py` does) × 3 new initialisation seeds, both arms, registered pool, 16,384 updates, rates r(arm, 0). These rates are calibrated on the new calibration parents (P10-I-S3's were calibrated on old ones); the report says so beside OA.

## 8. Calibration (rates), on calibration draws only

- **Grid [KNOWN]:** 0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, the same for both arms. It is ADR-0026's grid with one more step on each side. Known when it was chosen: both arms selected 0.01 at 16,384 in P10-I-S3, and longer constant-rate training usually prefers lower rates. The grid gives each arm four steps below and two above that value; it is identical for the two arms.
- One run per (arm, rate, calibration cell) to U_max, snapshots at 8,192 and at every rung, evaluated on the calibration panel (enabled read only).
- **Selection, by code (ADR-0026 section 5.1, unchanged):** at each duration k = −1..4, m = the lowest three-cell mean among rates finite in all three cells through U_k (ruling 5); r(arm, k) = the smallest rate whose mean is within 0.0005 of m.
- **Interior rule.** At each duration the rate attaining m (exact tie: the smaller) must not be the lowest or the highest rate run. If it is, the grid is extended by one half-decade step on that side for that arm and the selection repeated; down to 0.000001 and up to 1.0 (four steps down, two up). A rate whose neighbour on that side is non-finite in any calibration cell is not at an edge on that side. If a minimiser is still at an edge after these extensions: **ENGINEERING STOP — CALIBRATION NOT INTERIOR**, before Decision 2; the grid is amended with a recorded approval and the calibration re-run on the same calibration seeds, the sealed archive unread. **The grid is extended before the registered run and never after. No registered run carries a RATE-AT-EDGE tag; the tag does not exist in this study.**
- If no rate is finite in all three cells at some duration: engineering stop before Decision 2.
- **Sealing** as ADR-0026 section 5.3: the driver prints no loss; `rehearsal_public.json` holds the rate table, the interior flags, gate results, seconds and storage, and the sealed archive's SHA-256; δ, δrun and the convergence states of the calibration cells are in the sealed archive only, because no decision before the registered run uses them and their preview would let Decision 2 be taken knowing the likely label; the sealed archive (every curve and every calibration statistic) is stored outside every git working tree and is opened only after the registered outcome has been independently recomputed. The auditor's checker reports `agree` or `disagree` and field names only.
- **The study runs whatever the calibration's convergence states are; nobody sees them before the registered outcome is recomputed.** U_max, the ladder, ε and every threshold are fixed at Decision 1, before any calibration run exists.
- Limits stated here and in section 19: one hyperparameter is searched; the selection rests on three cells (in P10-I-S3 two rehearsal convergence tags differed from the registered ones).

## 9. The convergence rule

### 9.1 Criterion

An arm is **converged at rung k** if δ(arm, k) < ε **and** δrun(arm, k) < ε, with ε = 0.001 nats/byte (a rise counts as below ε for the quantity that rises; both conditions are required). Reason: a rate chosen per rung on three calibration cells can transfer badly, so that the envelope rises or flattens while the arm still improves along its run; without the second condition such a dense arm would be declared converged while behind. An arm is **settled from rung k** if it is converged at every rung j with k ≤ j ≤ 4. Both are computed by code from the 27-cell means of the registered run. Per-parent δ and δrun are printed; per-parent δ decides nothing.

Reasons. (i) ε and the per-doubling interval are ADR-0026's, unchanged **[KNOWN: the observed deltas were 17 to 21 times ε; ε was not moved]**. One fifth of the 0.005 margin: if the gain per doubling does not increase (an assumption), an arm below ε moves by less than 0.002 over two further doublings. (ii) The envelope is used beside the single run because a constant-rate run can stop improving only because its rate is too high for a longer duration; the envelope lets a lower rate at the next rung show that. (iii) "Settled" requires every later rung because one doubling below ε can be noise; with five rungs the rule has at most four confirmations and at the last rung none, which is stated beside any label read at rung 4.

### 9.2 The reading rung

K\* = the smallest k in 0..4 such that **both** arms are settled from k. If no such k exists (at least one arm is not converged at rung 4), K\* does not exist. The reading rung is R = K\* if it exists, otherwise 4.

### 9.3 The dense arm's best rung

On single-pass data a later rung is not expected to be worse, but nothing may favour the memory: the memory at a rung is also compared with the dense arm at the dense arm's best rung j† (section 4). The memory gets no such choice. This is one-sided on purpose and can only make the positive harder.

### 9.4 Every rung always runs

All runs of all rungs are executed whatever any value is. Reasons: no registered value is read while the run is in progress; the cost is bounded and known in advance (section 18); the rungs after K\* are the confirmation the label needs. What may stop early by rule: nothing scientific. Resource caps pause a stage (section 17).

### 9.5 Continuation rung (NOT part of the default specification; applies only if the human lead takes open choice 2(c) at Decision 1)

The recommended option is 2(a), under which this subsection has no effect: k_max is at most 4, no rung-4 value is withheld, and every other section is complete without it.

In this subsection "rung 4" is literal: the continuation exists only if the ladder was not cut by section 6.5 (k_max = 4 before it); after it k_max = 5 everywhere. A sixth rung, U_5 = 524,288, is run after the analysis of rungs −1..4 if and only if all of the following hold, computed by code from counts and from δ alone; **no condition reads Q, a class or a trend tag (item 1 reads convergence states only):**

1. K\* does not exist with k_max = 4 (at least one arm is not converged at rung 4). This reads convergence states only.
2. Every arm that is not converged at rung 4 has δ(arm, 4) < 2ε and δrun(arm, 4) < 2ε (0.002). Reason: an arm within a factor of two of ε reaches ε in one more doubling if its gain per doubling halves; an arm further away cannot be expected to, and the rung would be spent on another unfinished result.
3. The registered pool has at least 4,194,304 chunks (measured at D0; about 5.0 million is the estimate; under section 6.5's mod-2 fallback it would not suffice) and the resume-identity gate passed.

Before the continuation decision the analysis computes only δ, δrun and the convergence states; no class, Q, label or trend tag of rung 4 is computed, written or shown until rung 5 has run or the trigger has failed. The rung-5 runs are items of the frozen plan, conditional on the trigger, and the registered cap includes their projection from the start, so no cap or run decision is taken after the trigger. A non-finite event after U_4 fails that cell for rung 5 only; the rung-5 label then follows rows 1–2 of section 12.3, and the rung-4 label is printed as INTERIM. At rung 5 the envelope and the run coincide (r(arm, 5) = r(arm, 4)), so section 9.1's protection against a rate that is too high for the longer duration does not apply there: a plateau at the rung-4 rate can register as convergence for either arm, and every rung-5 label says so. The direction of that risk, stated: a dense arm that plateaus at a stale rate while behind would read as converged, which is the direction favourable to the memory in P10-I-S3's situation.

Rung 5 has no calibration: the calibration pool cannot supply 4,194,304 chunks. Each arm's run at r(arm, 4) is resumed to U_5, so r(arm, 5) := r(arm, 4) and δ(arm, 5) = δrun(arm, 5). Line P, D[FLAT] and the trend line are then recomputed with k_max = 5 by the same rows; that label is the registered label and carries "(RUNG 5 AT THE RUNG-4 RATE, NOT CALIBRATED)"; the rung-4 label is printed beside it as INTERIM. If the conditions do not hold, the rung-4 label is the registered label and the report says which condition failed. The continuation is one rung, once; there is no rung 6.

## 10. The comparison at a rung

The **class** of rung k is the first row that applies.

| Order | Class | Rule at rung k |
|---|---|---|
| 1 | M-AHEAD | mean Q(k) ≥ +0.005; Q_c(k) > 0 in ≥ 22 of 27 cells; parent mean Q(k) > 0 in ≥ 8 of 9; **and** the same three conditions with Q†(k) in place of Q(k) |
| 2 | D-AHEAD | mean Q(k) ≤ −0.005; Q_c(k) < 0 in ≥ 22 of 27 cells; parent mean Q(k) < 0 in ≥ 8 of 9 |
| 3 | LEVEL | −0.005 < mean Q(k) < +0.005 |
| 4 | UNDECIDED | otherwise (a mean beyond the margin on either side whose counts are not met, or the memory ahead of the dense arm's rung k but not of its best rung) |

M-AHEAD without the Q† clause is ADR-0026's K3; D-AHEAD is its mirror image. ADR-0026's K2 (share of the dense gain) is not used: it binds only while the dense gain is below 0.05, and the floor of section 12.2 covers a dense arm that adds nothing. **[KNOWN: the observed dense gain was 0.129.]**

## 11. Controls for the flat memory (evaluation only)

Run on M-FLAT at every rung on the run at r(M-FLAT, k); the rules read rung R only. Definitions are ADR-0026 section 3.4's and section 16's (rulings 9, 10, 12), through `studies/p10i_s3/model.py`'s `memory_read`.

| Control | Definition | Use |
|---|---|---|
| Memory disabled | Addition bypassed; must equal BASE bitwise on the platform of record. Also for D-ADAPT. | Integrity |
| Replay | A second enabled evaluation after a fresh restore; must equal the first bitwise. | Integrity |
| P_used | Values reassigned among the slots selected at least once on the panel, by a seeded cyclic shift of a seeded permutation; mean of 4 draws; P_used = H_used − H. | F2 |
| X_mean | The read at every position replaced by its mean over the 512 positions of the evaluation batch; X_mean = H_mean − H. | F3 |
| V_mean (new, descriptive) | Every value row replaced by the usage-weighted mean value row (NEG-REF's construction, ADR-0026 ruling 9, with the weights from the enabled read of the same checkpoint on the panel being evaluated: the registered panel in registered mode only, the calibration panel otherwise). With every value row equal the read is one vector at every position whatever the query, so V_mean is a second context-free read built from the stored values. V_mean = H_vmean − H. | Printed with B − H_vmean; no rule reads it. It shows whether a constant built from the stored values keeps the gain; it does not separate content from W_o and the gate. |
| X_mean_dense | The adapter's delta replaced by its batch mean. | Descriptive like-for-like figure |

**Harm figures, required in the report (P10-I-S3's report omitted them):** per rung (counts use strict ">"), mean B − H_used and the count of cells with H_used > B; mean B − H_mean and the count with H_mean > B; mean B − H_vmean and its count; the number of used slots per cell.

Conditions at rung R, on M-FLAT (ADR-0026 section 6.2's rules with M-FLAT in place of M-TREE):

| Condition | Rule |
|---|---|
| F1 capacity | mean C ≥ 0.005; C > 0 in ≥ 22/27; parent mean C > 0 in ≥ 8/9 |
| F2 stored association | mean P_used ≥ 0.005; (C > 0 and P_used ≥ 0.5·C) in ≥ 22/27; parent mean P_used > 0 in ≥ 8/9 |
| F3 query dependence | mean X_mean ≥ 0.005; (C > 0 and X_mean ≥ 0.5·C) in ≥ 22/27; parent mean X_mean > 0 in ≥ 8/9 |

A cell with fewer than two used slots fails F2 and is listed COLLAPSED. A non-finite NLL under an intervention on a finite checkpoint fails that cell's condition and is printed. F2 can pass through harm, as it did for the tree; the report states, beside the D[FLAT] label, in how many cells H_used > B, and the V_mean figure. What these controls show is that the loss depends on which value sits at which address and on the query; they do not show retrieval of content in any stronger sense.

Validity references carried from ADR-0026: the planted-positive test and NEG-REF on each calibration M-FLAT checkpoint at rung 4 (P_used, X_mean and V_mean must be 0 within 1e-6 on NEG-REF, and no NEG-REF cell may meet F2's or F3's per-cell condition), both as gates. No check in this study compares two different computations up to a tolerance except NEG-REF; ADR-0026's joint-permutation check, which failed on float32 score ties, is not used. Every other identity compares the same computation bitwise, and the top-8 tie-break by slot index is deterministic.

## 12. Labels

### 12.1 Outcomes that are not labels

| Event | Outcome |
|---|---|
| A gate fails before training; the panel walk or the corpus rule stops; the adapter identity gate fails; calibration is not interior; the auditor's `disagree` cannot be reconciled | ENGINEERING STOP (named). No registered cell is observed. A fix needs an amendment, a re-freeze and the human lead's approval. |
| A training or evaluation item ends with an error that is not a non-finite value (section 12.2) | `item_error`; the analysis refuses; ENGINEERING STOP — ITEM ERRORS. Nothing is labelled. |
| A required record is missing with no `item_error` | ENGINEERING STOP — INCOMPLETE REGISTRY. Denominators are never reduced. |
| A frozen input's hash differs when a task starts | PAUSED — IDENTITY. Nothing is recorded; restoring the file bit for bit lets the stage resume. |
| A stage reaches a resource cap | PAUSED. Resumed after an extension decided on projections only. If the extension is refused: INCOMPLETE (PAUSED AT CAP); nothing is labelled, including rungs already complete. |

An engineering stop is never a scientific NOT EVALUABLE.

### 12.2 Failed cells and NOT EVALUABLE (the only scientific causes)

A failed cell is a registered run with a non-finite training loss, clipped gradient norm or trainable parameter, or a non-finite enabled NLL at a snapshot a rule reads (the errors `p4_model.train_step` and `p4_model.evaluate` raise for these; the implementer records the exception types the code actually raises, since ADR-0026's text named `ValueError` where the code raises `RuntimeError`).

Line P is **NOT EVALUABLE**, with the cause printed, if and only if one of these holds; "a rule reads" means the enabled, replay and disabled evaluations of the 27 cells of each arm at rungs −1..4 on the run at r(arm, k), the enabled read at U_{k−1} of that run (for δrun), and nothing else (the scope ADR-0026 left unstated):

1. BASE is missing or fails its bitwise replay on a registered parent.
2. Disabled ≠ BASE or replay ≠ enabled on any evaluation a rule reads.
3. A D-ADAPT run that a rule reads is a failed cell.
4. Mean Cd(R) < 0.005 (the dense adapter adds nothing measurable at the reading rung).

An M-FLAT failed cell on a run a rule reads gives **MEMORY UNSTABLE (FAILED CELLS)** (order 2 below): a memory failure counts against the memory and is not hidden. Nothing is rerun at another rate.

If an arm has a failed cell on a run a rule reads, its L at the rungs that run serves, its δ, δrun and convergence state are NOT DETERMINED, which counts as not converged; if K\* cannot be computed for that reason, R = k_max. A run stops at the non-finite error; its later snapshots are recorded as not produced (failed cell), which is not a missing record of section 12.1. A non-finite event after U_k fails the run for every rung it serves.

### 12.3 Line P — PERSISTENCE (the registered label)

Let conv(arm) = "the arm is converged at rung 4". The first row that applies decides. Every (integrity state, failure state, convergence state of each arm at each rung, class at each rung) reaches exactly one row.

| Order | Condition | Label |
|---|---|---|
| 1 | A cause of section 12.2, items 1–4 | NOT EVALUABLE (cause) |
| 2 | An M-FLAT failed cell on a run a rule reads | MEMORY UNSTABLE (FAILED CELLS) |
| 3 | K\* exists and the classes of rungs K\*..4 are not all the same | ORDERING NOT STABLE AFTER CONVERGENCE (the classes are printed) |
| 4 | K\* exists; class M-AHEAD at every rung K\*..4 | **PERSISTS AT CONVERGENCE** |
| 5 | K\* exists; class LEVEL at every rung K\*..4 | **LEVEL AT CONVERGENCE** |
| 6 | K\* exists; class D-AHEAD at every rung K\*..4 | **DENSE AHEAD AT CONVERGENCE** |
| 7 | K\* exists; class UNDECIDED at every rung K\*..4 | **LEAD NOT ESTABLISHED AT CONVERGENCE** |
| 8 | K\* does not exist; conv(D-ADAPT) and not conv(M-FLAT); class of rung 4 is M-AHEAD | MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING) |
| 9 | K\* does not exist; conv(M-FLAT) and not conv(D-ADAPT); class of rung 4 is D-AHEAD | DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING) |
| 10 | K\* does not exist; not conv(D-ADAPT) and conv(M-FLAT) | CONVERGENCE NOT REACHED (DENSE STILL IMPROVING) |
| 11 | K\* does not exist; conv(D-ADAPT) and not conv(M-FLAT) | CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING) |
| 12 | K\* does not exist; neither converged at rung 4 | CONVERGENCE NOT REACHED (BOTH STILL IMPROVING) |

Notes. (a) K\* does not exist exactly when at least one arm is not converged at rung 4, so rows 8–12 are complete; if both are converged at rung 4 then K\* ≤ 4 exists. (b) Rows 8 and 9 are mirror images: the arm that has stopped improving is behind an arm that is still improving. Row 8 cannot arise when the dense arm is the one still improving, which is P10-I-S3's situation; that situation is row 10 and claims nothing. (c) A label read with K\* = k_max, or a label of rows 8 or 9 whose converged arm is not converged at k_max − 1, carries "(ONE DOUBLING OF EVIDENCE)". (d) Every label of rows 3–12 carries the registered descriptive trend line of section 12.6; under rows 10–12 it is printed directly under the label. (e) No label is reported from a subset of rungs, cells or parents.

### 12.4 Line D[FLAT] — DEPENDENCE at rung R, and the readouts

D[FLAT], first row that applies: NOT EVALUABLE (line P is NOT EVALUABLE by items 1–2, or M-FLAT has a failed cell at rung R); DEPENDENT (F1 and F2 and F3); CAPACITY WITHOUT DEMONSTRATED DEPENDENCE (F1 and not both; the failing conditions named); NO CAPACITY (not F1). It is printed beside line P and never replaces it. A line-P label of rows 4 or 8 is called **dependence-qualified** only if D[FLAT] = DEPENDENT.

**R16 (replication readout, no label of this study):** ADR-0026's section 6.3 rule (K1, K2, K3 and the dense floor) applied at rung 0, printed as REPLICATED AT 16,384 (K3 holds), NOT REPLICATED (WITHIN TOLERANCE) (K1 and K2, not K3) or NOT REPLICATED (otherwise), with the convergence states at rung 0. **OA:** the same rule on the old nine parents, printed the same way. R16 and OA change no label. If R16 is not REPLICATED, line P is still computed and the report says first that the 16,384-update lead was not reproduced on new parents and data.

### 12.5 Other descriptive output

Every quantity at every rung and at 8,192 by cell, parent and seed, with means, SDs, ranges and sign counts; along-run curves; the six registered rates per arm; per-parent δ; X_mean_dense; calibration-versus-registered convergence states where they differ (both printed, as ADR-0026 section 5.2 required and its report omitted); step-0 losses. No best seed, cell, parent or rung is selected. Also printed, with no rule: the share of registered-panel chunks that have a 32-byte substring occurring in the registered pool (near-duplicates at other offsets, such as shared templates, which the aligned 65-byte exclusion does not catch and which a key-value memory may use more than a dense arm; P10-I-S3 had the same exposure).

### 12.6 The registered descriptive trend line (fixed now; carried by every label of rows 3–12)

**What it is for.** If convergence is not reached, this line is what the study says about "whether it persists": a description of the lead over the trained range, 16,384 to U_max. **[KNOWN]** Its thresholds are ADR-0026's 0.005, 22 of 27 and 8 of 9, reused unchanged and set knowing that P10-I-S3's lead at 16,384 met them.

**Printed at every rung k = 0..k_max:** mean Q(k); the number of cells of 27 with Q_c(k) > 0; the number of parents of 9 with parent mean Q(k) > 0; δ(arm, k) and δrun(arm, k) for each arm; the class of section 10.

**HELD(k)** is true if mean Q(k) ≥ +0.005 and Q_c(k) > 0 in ≥ 22 of 27 cells and parent mean Q(k) > 0 in ≥ 8 of 9 (ADR-0026's K3 at rung k; the Q† clause of class M-AHEAD is not part of it). Rung 0 is the first rung of this study's ladder on its 27 registered cells; HELD(0) is the same condition as R16's K3 on the same cells, so tag 2 occurs exactly when R16 is not REPLICATED AT 16,384. Δ = mean Q(k_max) − mean Q(0). **One tag, the first row that applies:**

| Order | Tag | Rule |
|---|---|---|
| 1 | TREND NOT DETERMINED | Line P is NOT EVALUABLE or MEMORY UNSTABLE (a failed cell or an integrity cause at a rung a rule reads) |
| 2 | LEAD ABSENT AT RUNG 0 (16,384 UPDATES, NEW PARENTS AND DATA) | not HELD(0) |
| 3 | LEAD LOST BY RUNG k | HELD(0); k is the smallest rung with not HELD(k); and not HELD(j) for every j from k to k_max |
| 4 | NOT MONOTONE | HELD(0); some rung is not HELD; and some later rung is HELD |
| 5 | LEAD SHRINKING | HELD at every rung 0..k_max and Δ ≤ −0.005 |
| 6 | LEAD GROWING | HELD at every rung 0..k_max and Δ ≥ +0.005 |
| 7 | LEAD HELD AT EVERY RUNG | HELD at every rung 0..k_max and −0.005 < Δ < +0.005 |

**The printed text of every tag ends with this sentence, which is part of the tag:** "over 16,384 to U_max updates only; descriptive; this says nothing about the ordering at convergence and is not the label PERSISTS." Beside the tag the report prints one sentence with |mean Q(k_max)| and each arm's δ(arm, k_max), and, if either δ is at least |mean Q(k_max)|, the words "an arm is still improving per doubling by at least the size of the lead". A tag never changes a label, never qualifies for anything in section 19, and is never quoted without its sentence. Tags of rows 3–7 are printed with Δ and with mean Q(k) at every rung in the same line, for example "LEAD HELD AT EVERY RUNG (Δ = −0.0049; 0.0127, …, 0.0078)".

## 13. Thresholds and reasons

| Value | Use | Reason | Chosen knowing P10-I-S3? |
|---|---|---|---|
| 0.005 nats/byte | Margin of the classes; floors of F1–F3 and of the dense gain | The resolution used since ADR-0006 and in ADR-0026; unchanged | Kept, not chosen: **[KNOWN]** the observed mean lead was 0.0127 and the smallest parent mean 0.0044 |
| 22 of 27; 8 of 9 | Cell and parent counts | ADR-0026's, unchanged; the design keeps 27 cells and 9 parents so that they apply as written | Kept **[KNOWN: 27 of 27 and 9 of 9 parents positive]** |
| ε = 0.001 per doubling | Convergence | ADR-0026's, unchanged (section 9.1) | Kept **[KNOWN: deltas 0.017–0.021]** |
| 0.5·C | F2, F3 | ADR-0026's convention | Kept **[KNOWN for the tree only]** |
| 0.0005 | Rate tie tolerance | One tenth of the margin; decides a rate, never a label | Kept |
| U_max = 262,144; five rungs | Ladder | 16 times the old duration, the brief's upper preference; the largest whole doubling the proposed corpus supports with disjoint calibration | New **[KNOWN: 16,384 was far from converged]** |
| Q† clause; "settled"; same class at every later rung | Line P | Each can only remove a positive or a negative that one rung would give; the stability rule is symmetric, the Q† clause is one-sided against the memory | New; chosen to make the label harder to reach by one noisy rung |
| 1e-6 | NEG-REF tolerance | ADR-0026's | Kept |

No threshold is relaxed after any calibration or registered value exists. A defect found in a rule is an engineering stop with an amendment before any sealed file is opened.

## 14. Seeds (proposal; the registry revision and the checker run are the auditor's)

Read against `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` (revision 3): the blocks below lie in ranges the registry lists as free (data blocks 310001–319999 and 320001–329999; the P10-I spare initialisation sub-rows 330701–330999; test ranges 939001–939999 then 952001 upward). ADR-0030 is being drafted at the same time and was not read; the higher of the two free data blocks and the second free test range are proposed here to lower the chance that both drafts ask for the same values. The auditor resolves any overlap. No initialisation seed is derived from a data seed. Cell index c = 3p + s for registered parent p = 0..8 and seed position s = 0..2; draw j = 0..3.

| Role | Count | Proposed values |
|---|---|---|
| Registered stream seeds | 27 | 320001 + c |
| OA stream seeds | 27 | 320101 + c |
| P_used seeds (registered; reused across rungs) | 108 | 320201 + 4c + j |
| Order seeds of the new parents | 9 + 3 | 321001–321009 registered; 321091–321093 calibration |
| Calibration stream seeds; calibration P_used seeds | 3; 12 | 329001 + c; 329031 + 4c + j |
| Dry-rehearsal stream; P_used | 1; 4 | 329201; 329231–329234 |
| Addition initialisation, registered (one per cell) | 27 | 330701 + c (each expands to + 1000 … + 5000, inside the registry's derivation reserve) |
| Addition initialisation, OA (one per seed position, shared by the old nine parents as in P10-I-S3) | 3 | 330731–330733 |
| Backbone seeds of the new parents | 9 + 3 | 330741–330749 registered; 330751–330753 calibration |
| Calibration, dry-rehearsal and test-mode initialisation | 1; 1; 2 | 330791; 330792; 330798, 330799 |
| Test seeds | — | 952001–952999 |
| R-KNN store-sampling seeds (only if open choice 14 is taken) | 27 + 3 | 320401 + c registered (320301–320308 are P_used seeds of cells 25 and 26); 329301 + c calibration |

The freeze gate re-runs a copy of the registry checker extended with these values, with rules R2 and R3 expanded, and tolerates later studies' own allocations (it checks this study's values against its own rows and against earlier inventories, not the absence of others). Calibration cell index in the seed formulas is the calibration parent q = 0..2. A test asserts that no data seed of this study is ever expanded by + 1000·k. The reviewer's extended checker copy found no binding problem involving these values and no overlap with ADR-0030's draft (310001–319999, 939001–939999); the registry's sentence that the initialisation row sits 20,000 above the highest P10-I data block is no longer true with this block and is the auditor's to correct in the registry revision.

## 15. Frozen inputs and imports

**The frozen-input set is exactly:** every file under `studies/p10i_s6/` except `studies/p10i_s6/printing/` (below), including `freeze/plan.json`, `freeze/rate_table.json`, the seed plan and the checker copy; `configs/p10i_s6_flat_lead_persistence.toml`, which holds every threshold, grid, rung, tolerance and seed of sections 4–14; `tests/test_p10i_s6_*.py`; `rehearsal_public.json` and the sealed archive's SHA-256; the panel ledger; `uv.lock` and `pyproject.toml` (unchanged); the downloaded parquet files, the pinned WikiText-2 parquet files, the chunk table and pool index files; the twelve new parent checkpoints and the nine old ones; and every imported file, each by SHA-256. The compact records the parent loaders and the adapter identity gate read at run time (`results/p3-lt-2026-11-12/b*-control/manifest.json` and `order.json`, `results/p4-2026-11-12/b*-baseline/result.json`) are frozen inputs by SHA-256. This ADR, everything under `docs/`, and every other file under `results/` are not run-time inputs; the ADR's hash is recorded for provenance only. A test asserts that every threshold in this ADR equals the config's value.

**Imports from P10-I-S3 (each a frozen input by hash; nothing in `studies/p10i_s3/` is edited):** `model.py` (`memory_read`, `dense_read`, `Ctl`, `Collector`, the training step and evaluation wrappers for M-FLAT and D-ADAPT); `labels.py` (the K1–K3 and D1–D3 condition functions, used for R16, OA and F1–F3); `calibration.py` (`selection`, `sealed_bytes`, `write_sealed`, `require_outside_repo`, `check_public_against_sealed`'s pattern); `data.py` (`overlaps`, `count_overlaps`, `walk_panels`, `ledger`); `parents.py` (`load_backbone`, for OA); `planted.py` (the planted-positive construction); `core.py` (`EngineeringStop`, `FailedCell`, `jsonable`). **Condition:** an imported function may be used only if it reads no P10-I-S3 config value, regime list or path implicitly; where it does, it is re-implemented in the new package and a test proves it equal to the original on a fixture. Not imported as they stand, because they read P10-I-S3's config, seed layout or arm list: `core.envelope` (it stamps `study: P10IS3`), `core.Seeds` and `core.Thresholds.from_config` without an explicit argument, `model.evaluate_reads`, `calibration.rate_table`, `calibration.require_outside_repo` without `forbidden_roots`, `data.corpus_from_parquet`, `planted.planted_positive` and `planted.neg_ref_check`. The implementer lists the final imports in `plan.json`. From `src/arborlm/`: the files reached by the static import walk at the freeze, as ADR-0026 section 11 item 5.

**Files that only print are separated.** `studies/p10i_s6/printing/` holds the report renderer and completion messages. Its identity binds no result: stage records carry the hashes of the computing files only, so a later fix to a printed line does not invalidate a finished stage.

## 16. Stages, rehearsals and engineering requirements

| Stage | Content | May share the machine? |
|---|---|---|
| D0 download and data preparation | Fetch with ledger rows; article exclusion; pools; chunk table; gates of section 6.4; panels | Yes. Network is used here only. Single process; RSS measured, guard 8 GiB (the de-duplication of about 8 million chunks is the largest structure of the study; a literal `select` in Python objects would need about 5–6 GB, so compact digests and arrays are used, section 6.4) |
| P0 parents | Adapter identity gate; twelve new backbones; hashes | Yes |
| R1 calibration | Rate search to U_max, sealed | Yes |
| R2 measuring rehearsal | Whole-process seconds per item type at the plan's worker count | Yes, on purpose under ordinary load |
| R3 counting rehearsal | Every registered stage end to end in the DRY profile against the candidate `plan.json`; the freeze refuses unless the committed plan has the hash R3 recorded | Yes |
| G gates | Hashes; pool and panel disjointness; seeds; BASE and disabled = BASE on all parents; prefix identity; resume identity; read equality; planted positive; NEG-REF; synthetic registry | Yes |
| T, E | All runs of all rungs and OA; all evaluations | Yes |
| A, report | Once, pure functions over records | Yes |

**No stage of this study needs a quiet machine, because no wall-time, CPU-time or throughput reading is registered:** training and evaluation are deterministic single-thread float32 CPU (`engine.configure_cpu`), so load changes charged hours and nothing else. It may run beside P10-I-S0's main grid (six workers). Conditions, as ADR-0026 section 17: at most 16 workers across all studies; aggregate RSS guard 12 GiB while sharing; its stages pause or do not start while another study's quiet-machine stage runs (ADR-0025 stage 7, ADR-0024 MC-T, ADR-0027 and ADR-0028/0030 measured stages); its own worktree; no write or commit in any worktree whose registered stage is running. The quiet-rule lesson (measured idle limits, settle period) therefore has no rule to attach to here; if a later amendment adds a timing reading, that lesson applies in full before it may be registered.

Requirements, each from a P10-I lesson (`BRIEF_P10II_S5.md`, items 1–9):

1. **Same path.** R1, R2 and R3 drive the same entry point and the same launch scripts as the registered run, one fresh process per stage. R2 times whole processes, including start-up, imports, per-process input hashing and the memory-mapping of the chunk table. Caps = charged so far + 2 × projected remaining from that record, written by code into the candidate plan before R3.
2. **Quiet rule:** not applicable (above); the load average and the top CPU processes are recorded at each stage start as a cost record only.
3. **Process family.** Each stage records its own process family, including the keep-awake watcher of its launch script, and the list of other study processes running; tested on the real launch shape.
4. **Attempts and waits.** Every discarded, refused or failed attempt is written into the run directory as it happens and kept. No wait without a deadline; a supervisor's deadline exceeds its stage's cap.
5. **Tests** do not depend on the repository's planning state, on nothing else being frozen, or on sibling studies' files being absent or present.
6. **Outputs.** Public-output guards do not match inside opaque identifiers (hashes, run ids). A completion print cannot fail a finished stage: the stage's record is written and closed before any message is formatted, and printing errors are caught and logged.
7. **Stops and analysis.** Identity failures pause and resume. Code and environment errors are engineering stops. The analysis and the report are pure functions over records, tested on a synthetic registry with a known answer for every row of sections 10, 12.3 and 12.4, every NOT EVALUABLE cause, R16's three readings, the three trend words, the failed-cell rules, the j† tie rule and a case where two rungs' records are swapped and the test must fail. Registry keys carry arm, cell, rate, rung, read and draw. The outcome record is written only after `arbor-auditor` has recomputed every label from raw records with code that imports nothing from the study.
8. **First-process effects** exist here only as cost: R2's whole-process timing includes them, and no reading excludes or includes anything on their account.
9. **Harness limits:** not applicable; nothing is timed for a claim. No package outside the lock is needed (`pyarrow` comes from the existing optional `pilot` extra, as in P10-I-S3).

Further gates specific to this study. **Prefix identity:** on one calibration cell per arm, a separate run to 8,192 equals snapshot 8,192 of the long run bitwise. **Resume identity:** a run stopped at a rung and resumed from its snapshot (model, optimizer state, stream position) equals the uninterrupted run bitwise at the next rung, per arm, on one calibration cell; if this gate fails, every run restarts from update 0 (ADR-0026 ruling 6) and the cost projection uses the restart figures. **Run sharing:** one run per distinct (arm, cell, rate), trained to the largest rung that rate serves; rung k reads snapshot U_k of the run at r(arm, k). Platform of record: macOS arm64, Apple M5 Max, torch as locked; bitwise assertions on it only. Checks run locally (`ruff`, `mypy src/arborlm`, `pytest`); no CI run is required. Roles: `arbor-implementer` writes the code; `arbor-auditor` audits it in a separate context from code and records, verifies the sealed file by `agree`/`disagree` and recomputes the outcome; `arbor-clerk` inventories panels and hashes. The model that ran each task is recorded from session metadata.

ADR-0026 section 16 rulings 1–3, 5, 7, 9, 10 and 12–18 apply with M-TREE, REP and REP-U removed; ruling 4 is replaced by section 6.4; ruling 6 (a training item restarts from update 0) applies only if the resume-identity gate fails, and otherwise a paused or killed training item resumes from its last snapshot at 8,192 or at a rung; rulings 8 and 11 have no object in this study. Ruling 15 binds: no trained addition is evaluated on the registered panel outside registered mode. Pause for another study's quiet stage: the lead creates the run directory's pause file; workers start no new item while it exists; an item in progress finishes (or, if the resume-identity gate passed, stops at its next rung snapshot and resumes from it); the other study's quiet stage starts only when this study's process family is empty. Worker RSS is the process RSS including file-backed pages, so each worker counts up to about 0.5 GB of the memory-mapped chunk table.

## 16a. Rulings for the implementer (the review's section D, adopted as written)

"Edit Cn" in this table refers to the review's edits, all applied in this draft: C2 is section 12.2's NOT DETERMINED paragraph, C7 the V_mean row of section 11, C8 the paragraph above, C9 the order of section 6.4 and the fallback of section 6.5, C13 section 21.

| # | Guess | Ruling |
|---|---|---|
| G1 | Is rung −1 run on registered cells? | Yes. The 27 cells × 2 arms at r(arm, −1) to 8,192, sharing a run when the rate is equal; reads enabled, replay and disabled; "a rule reads" includes them. Cost +≤0.2 h |
| G2 | Snapshots and evaluations of each registered run | Snapshot at 8,192 and at every rung up to the run's maximum, with optimizer state. Enabled read at U_{k−1} of the run at r(arm, k) for δrun |
| G3 | Failed cell, K\* and R | Edit C2 |
| G4 | Exception types | A failed cell is the non-finite errors of `p4_model.train_step` and `evaluate` as the code raises them (identified by type and message in a test); everything else is `item_error` |
| G5 | Mean arithmetic | Python float `sum` in cell order c = 0..26, divided by 27; parent mean likewise over s = 0..2; δ is the difference of those floats |
| G6 | Pool construction order | Edit C9 |
| G7 | E | Hex SHA-256 of each 65-byte payload of the WikiText-2 train and validation parquet at `select`'s offsets, before de-duplication and before cross-split exclusion |
| G8 | Calibration cell index | c = calibration parent q = 0..2 in seed formulas (329001 + c, 329031 + 4c + j) |
| G9 | New parents' control memory | Not constructed (the backbone draw comes first and is unaffected); if the identity gate needs it, 201 is a declared re-use |
| G10 | Identity gate scope | All nine old parents (F16) |
| G11 | NEG-REF and V_mean weights | Calibration panel on calibration checkpoints at the last calibrated rung (4, or the cut ladder's last rung) (ADR-0026 ruling 9); edit C7 |
| G12 | Reads per rung | M-FLAT at rungs 0..k_max on the run at r(M-FLAT, k): enabled, replay, disabled, P_used × 4, X_mean, V_mean. D-ADAPT: enabled, replay, disabled, X_mean_dense. Rung −1 and δrun points: G1 and G2 |
| G13 | j† domain | Rungs 0..k_max only; tie to the larger rung |
| G14 | Extension counting | Per arm, across all durations −1..k_max; at most 4 steps down and 2 up per arm; each new rate run to U_max on all three calibration cells |
| G15 | Prefix and resume gate cells | Calibration cell 0 at rate 0.01. Prefix: 8,192. Resume: stop at 16,384, resume to 32,768 |
| G16 | uint8 table | Batch = table[rows].long(); a gate shows bitwise equality with the int64 path of `studies/p10i_s3/data.py` on WikiText-2 ranks |
| G17 | OA and R16 failures | R16 follows line P's integrity and failed-cell state; OA prints NOT EVALUABLE (cause) and changes nothing; BASE on the old parents is in stage G |
| G18 | Pause mechanism | Edit C8 |
| G19 | Decision 2 and disagreement | Edit C13 |
| G20 | Download file names | From the repository listing at the pinned revision, written to the ledger rows with LFS size and SHA-256 before the fetch |
| G21 | Harm counts | Strict ">" (F26) |
| G22 | RSS measure | As P10-I-S3 (process RSS including file-backed pages), stated in the plan |

## 17. Caps and limits

| Limit | Kind | Rule |
|---|---|---|
| Hour caps, in charged hours (a stage supervisor's wall clock at the plan's worker count): D0 + P0 2 h; rehearsal 16 h; registered run = charged so far + 2 × projected remaining from R2, in the candidate plan; if that exceeds 40 h the lead returns to the human lead before Decision 2 and the matrix is not cut | Resource cap | Extended by the human lead on cost projections only. A stage at a cap is PAUSED. |
| RSS 2 GiB per worker, 12 GiB aggregate while sharing (24 GiB alone); D0 8 GiB | Resource cap | Same. |
| Download: the train files of one configuration, expected 0.32 GB; hard stop at 1 GB | Resource cap | A larger size is an engineering stop, not an extension. |
| Storage: about 2.07 MB per snapshot (measured in P10-I-S3); at most about 1,900 registered and 500 calibration snapshots, about 5 GB; the chunk table about 0.5 GB | Resource cap | Measured in R2. |
| U_max = 262,144; rungs; U_{−1} | Design ceiling | Fixed; cut only by the corpus rule of section 6.5 before calibration. Extended only by the single continuation rung of section 9.5, by its code rule, if open choice 2(c) is taken; never otherwise. |
| Rate grid and its extensions | Design ceiling | Extended only by section 8's rule, before Decision 2. |
| 9 + 3 new parents; 27 cells; 3 calibration cells; panel 512 chunks; 4 P_used draws | Design ceiling | Not extended. |
| 0.005; 22/27; 8/9; ε; 0.5·C | Scientific threshold | Fixed at Decision 1. Never relaxed. |

The registered run happens once. A negative or unfinished label is a registered outcome; it is not a reason to add rungs (beyond section 9.5's rule, if taken), seeds, rates, parents or cells. A longer ladder would be a successor study.

## 18. Cost projection (estimates from measured figures; R2 replaces them)

Basis: P10-I-S3's R2 unit costs at six workers (M-FLAT 0.008237 s/update, D-ADAPT 0.011063, M-TREE 0.028774; full read set 3.25 s, 2.02 s, 10.34 s), six workers, and the ratio 1.29 of charged to projected training seconds that P10-I-S3's registered run showed on a shared machine (21,904 s against 16,980 s); P10-I-S3's first calibration round charged 1.37 times its projection. The new corpus, the memory-mapped table and the new parents may change the per-update cost; R2 measures it.

| Block | Recommended design (U_max 262,144, 7 rates) | Smallest design (U_max 65,536, 5 rates of ADR-0026's grid) |
|---|---|---|
| Calibration R1: rates × 3 cells × 2 arms to U_max | 21 pairs × 5,059 s = 106,243 s; 4.9 h | 15 pairs × 1,265 s; 0.9 h |
| R1 extensions, up to 6 more rates per arm | 0 to 4.2 h (up to four rates below and two above per arm) | 0 to 0.7 h |
| Registered runs, 27 cells × 2 arms, one rate serving every rung (resume gate passes) | 136,593 s; 6.3 h | 1.6 h |
| Same, worst case: a different rate at every rung (sum of rungs 507,904 updates per cell and arm, or 114,688) | 12.3 h | 2.8 h |
| OA; gates; evaluations (about 5 s per cell and rung); P0; D0 | about 1 h | about 0.8 h |
| **Projected total** | **about 12 to 23 h** | **about 3.5 to 5 h** |
| **With the 1.29 to 1.37 sharing ratio** | **about 16 to 31 charged hours** | **about 4.5 to 6.5 charged hours** |

Options (additional to the recommended design): M-TREE as a secondary line: 27 runs × 7,543 s = 9.4 h, up to 18.3 h with a rate per rung, plus a calibration of at least nine rates (the optimum is above 0.3) of about 9.4 h: **about 19 to 28 h more**. A descriptive D-2X arm (width 6,200; cost per update not measured, taken as twice D-ADAPT's): about 7 h registered and 5.6 h calibration.

**Expectation, not a measurement [KNOWN]:** in P10-I-S3's FRESH regime the envelope's gain per doubling did not fall between 2,048 and 16,384 updates (D-ADAPT 0.0208 then 0.0172, M-FLAT 0.0219 then 0.0208 per doubling). To meet ε at the last rung an arm's gain must fall about twentyfold within four doublings. If the curves keep their shape, the recommended design most likely ends in CONVERGENCE NOT REACHED (BOTH STILL IMPROVING), which claims nothing about the ordering. The human lead weighs this at open choice 2.

**What the hours buy in that case.** The trend line of section 12.6: the lead, its cell and parent counts and each arm's gain per doubling at five durations up to 16 times the old one, on new parents and data, with R16 saying first whether the 16,384-update lead was reproduced at all. That is a registered description of whether the lead held, shrank or was lost over the trained range. It is not a converged comparison, and section 19 gives it no licence beyond that.

**Ladder length: three options side by side (open choice 2).** Chances are as far as P10-I-S3's four points can say, which is little: they show no bend.

| Option | Fresh data available? | Projected / charged hours | Chance of reaching convergence |
|---|---|---|---|
| (a) 16× (U_max 262,144), as drafted | Yes on the estimate (2,097,152 chunks per stream against about 5.0 M registered and 2.5 M calibration); measured at D0 | 12 to 23 / 16 to 31 | Low: needs a twentyfold fall of the gain per doubling in four doublings |
| (b) 64× (U_max 1,048,576) | **No.** One stream needs 8,388,608 chunks; the whole WikiText-103 pool is estimated at 7.5–7.7 M, split into two pools. Even 32× (4,194,304 per stream) cannot be calibrated on disjoint data (calibration pool about 2.5 M, or 3.8 M under the mod-2 split, which then leaves the registered pool short). It would need a second corpus of the same kind of about 1.1 GB of eligible text per pool; the drafter knows none. To be measured before this option could even be costed properly: both pool sizes | If data existed, about four times (a)'s run cost: roughly 45 to 85 / 60 to 115 | Still not indicated: a twentyfold fall in six doublings is a fall of 1.65 times per doubling, against none observed |
| (c) 16× now, with the continuation rung of section 9.5 (to 32× on the registered pool, only if K\* does not exist and every unfinished arm is within 2ε; it reads convergence states and δ only, never the lead; rung-4 values stay hidden until the code has decided) | 16×: as (a). Rung 5: only if the registered pool reaches 4,194,304 chunks (estimate 5.0 M; measured at D0); no calibration data for rung 5, so it runs at the rung-4 rate and says so | As (a), plus 6.3 projected (about 8.5 charged) only if the rule fires; that amount is inside the registered cap from the start | As (a), plus the one case where it matters: arms that have bent to within a factor of two of ε at 16×. On P10-I-S3's trend the rule would most likely not fire, and then it costs nothing |

**Recommendation: (a).** The first draft of this table recommended (c); the lead and the reviewer recommend (a) and the drafter agrees. Reason: on P10-I-S3's trend the continuation rule is unlikely to fire, and when it does its reading is the weakest in the study (rung 5 has no calibrated rate, so the envelope protection of section 9.1 is absent there) while it is the most complex rule in the document. (c) stays available to the human lead exactly as section 9.5 defines it; (b) is not available on fresh data. **The smallest design** (right-hand column of the cost table, 4×) reaches three rungs and would almost certainly end unfinished with a three-point trend line; it is not recommended.

## 19. What each outcome would and would not license

| Outcome | Would mean | Would not mean |
|---|---|---|
| PERSISTS AT CONVERGENCE, dependence-qualified, R16 REPLICATED | On this corpus kind, at matched trainable bytes and updates, each arm at a rate calibrated per duration on separate parents and data, the flat memory's lead of at least 0.005 nats/byte held at every converged rung, and its loss depends on value placement and on the query. It is evidence the human lead may weigh before a larger commitment. | Not a cost or efficiency result: M-FLAT is read exhaustively over 4,096 keys. Nothing about a scalable index, the tree, a larger store, SSD, another corpus kind, another dense form or size, or joint training. **It does not open Route A of ADR-0027:** ADR-0027 section 3 names COMPETITIVENESS[FLAT] as never qualifying, requires both clauses for M-TREE, and bounds Route A at 19,064 updates. Open choice 13's ruling ("no while D-ADAPT is NOT CONVERGED") would no longer be the obstacle, since D-ADAPT would be converged by rule; the remaining obstacles are in ADR-0027's own text. A cost study on the flat memory is a new or amended specification and the human lead's decision (open choice 9). |
| PERSISTS, not dependence-qualified | The lead held, but the controls do not show that it depends on stored content. | Not evidence for a memory mechanism; the lead may come from the added projections. |
| MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING) | The dense arm stopped improving by rule while behind. | Not a converged comparison; the size of the lead at convergence is not identified. |
| LEVEL AT CONVERGENCE / DENSE AHEAD / LEAD NOT ESTABLISHED / ORDERING NOT STABLE / the row-9 label | If R16 is REPLICATED AT 16,384: the 16,384-update lead did not hold once both arms had converged in this setting. Otherwise the lead was not reproduced on new parents and data even at 16,384, and the label does not say whether duration or the change of parents and corpus removed it. P10-I-S3's label stands as the record of what was measured at 16,384. | Not a statement that a memory cannot lead at other sizes or with other training; not a revision of P10-I-S3. |
| CONVERGENCE NOT REACHED, with its trend tag | Sixteen times the duration was not enough by the registered criterion. The trend line describes the lead over the trained range: for example LEAD HELD AT EVERY RUNG means the lead met ADR-0026's K3 at 16,384 and at every doubling up to U_max on new parents and data. The human lead may weigh that description. | Nothing about the ordering at convergence, in either direction; no tag is PERSISTS, and none qualifies for anything PERSISTS would. Not a reason to extend this study (section 9.5's rule applies only if choice 2(c) was taken at Decision 1). |
| R16 NOT REPLICATED (with any line-P label) | The 16,384-update lead did not carry to new parents and a wider corpus of the same kind; OA shows which change mattered. | Not a revision of P10-I-S3. |

## 20. Open choices reserved for the human lead

**Marked NOT FOR DELEGATION** are the choices the independent review lists as ones the human lead should take himself (its section F): 1, 2, 3, 5, 6, 7 and 13. The reviewer and the drafter both recommend that the human lead take Decision 1 himself (choice 11). Choices 14 and 15 are new in this draft and are the human lead's.

1. **Corpus and download — NOT FOR DELEGATION** (the download is within the standing download permission; the corpus defines the evidence). WikiText-103 raw train, same publisher and revision, at most about 0.32 GB, licence note as for WikiText-2 (local use only; discrepancy unresolved). Recommendation: approve. Without a larger corpus this study cannot run.
2. **Ladder length — NOT FOR DELEGATION** (cost against a likely unfinished result). Options (a) 16×, (b) 64×, (c) 16× with the continuation rung, costed in section 18; a fourth, 4×, is the smallest design. Recommendation of the lead, the drafter and the reviewer: (a), 16× without the continuation rung, because (c) probably does not fire on P10-I-S3's trend and, when it fires, reads convergence at an uncalibrated rate, the weakest reading in the study; if the human lead takes (c), section 9.5 applies as amended by confirmation review R6 and R7. (b) is not available on fresh data.
3. **Parents — NOT FOR DELEGATION** (new training). (a) Twelve new backbones by the P2→P3 control recipe through a new adapter with an identity gate on all nine old parents, plus the OA block (recommended; the reviewer agrees: the across-parent SD of Q in P10-I-S3 was 0.0069, about six times a 3-cell parent mean's standard error). (b) The old nine parents only. (3b) More than nine new parents: would need new counts chosen after the observation; not recommended.
4. **The tree.** (a) Out (recommended). (b) In, as a separately labelled secondary line with its grid extended until interior; about 19 to 28 charged hours more.
5. **A larger dense arm — NOT FOR DELEGATION** (it decides the fairness of the comparison). Not registered (recommended; section 5). Alternative: a descriptive D-2X arm, about 7 h registered and 5.6 h calibration, changing no label.
6. **Thresholds — NOT FOR DELEGATION.** 0.005, 22/27, 8/9, ε = 0.001 per doubling, all unchanged from ADR-0026, also for the trend tags (recommended). Any change would be made after seeing P10-I-S3. Left open by the review: whether to keep the 0.0005 rate tie tolerance now that the envelope switches rates (it is half of ε); the along-run condition removes most of its effect; recommendation: keep.
7. **Label structure — NOT FOR DELEGATION** (it could favour the memory). "Settled" convergence, the same class at every later rung, the one-sided Q† clause, the mirror-image rows 8 and 9, and the trend line with its closed tag list (recommended as drafted). Alternative: read k_max only, with convergence tags.
8. **Every rung always runs** (recommended) or stop at K\* + 1 by code.
9. **Route A.** Recommendation: no outcome of this study opens ADR-0027 automatically; the reviewer found this consistent with ADR-0027 section 3.
10. **Constant rate** (recommended) or a decaying schedule.
11. **Who approves.** Recommendation of the drafter and of the reviewer: the human lead takes Decision 1 himself. The delegation record of 2026-11-18 was written before this study existed and excludes "a new redesign study after P10-I"; whether any standing delegation covers this study is for him to confirm.
12. **Caps:** as section 17. **Panel size:** 512 chunks (recommended).
13. **Convergence measure — NOT FOR DELEGATION** (it could favour the memory). **ε on both the envelope and the along-run improvement per doubling** (recommended), against either alone.
14. **A byte-matched store of raw contexts, R-KNN (new; not a default; it is not a retrieval baseline as normally meant).** The project has never compared the memory with plain retrieval. Definition, if taken: per registered cell, a non-learned store of 6,144 entries, each a key (the frozen backbone's 32 float32 hidden values at the insertion point, after block 0, for one training position: 128 bytes) and a value (that position's target byte: 1 byte), 6,144 × 129 = 792,576 bytes against M-FLAT's 792,580. At each rung k the store is built from the first 6,144 entries of `randperm(U_k × 512)` from a generator seeded 320401 + c, entry n meaning position n mod 512 (row-major in the 8 × 64 batch) of update n // 512 of the cell's own registered stream, so that the store and the arms have seen the same stream up to the same update. Read at a panel position with hidden state h: cosine similarity of h with every key (`F.normalize` with the code's EPS), top 8 by `stable_top`, weights = softmax of the eight similarities divided by the code's TEMP, p_knn(b) = the summed weight of neighbours whose value is b, p = (1 − λ)·p_BASE + λ·p_knn, p is computed in float32 from BASE's float32 softmax; a position's loss is −log p[target] in float32; losses are summed per evaluation batch in float32, accumulated as a Python float and divided by 32,768. λ is the one fitted number: from {0.02, 0.05, 0.1, 0.2, 0.4}, the value with the lowest mean calibration-panel NLL over the three calibration cells (calibration stores, below), ties to the smaller. Output: C_knn = B − H_knn per cell, its mean and counts, printed beside C(k) and Cd(k) at every rung; no label, no rule. **Cost from measured rates:** one read is about one enabled dense read (6,144 × 32 = 196,608 multiply-adds per position against 198,400; 0.28 s per 32,768 targets at six workers); 27 registered reads per rung (135 over five rungs) and 15 calibration reads, plus the backbone passes that build the stores: under 0.1 charged hours. The cost is implementation and audit, not compute. **What it could show:** whether a same-size store of raw contexts with no learning gets a gain comparable to the trained memory's. **What it could not show:** anything about retrieval as it is normally used, where the store grows with the data (every position seen in 16,384 updates would be 8.4 million entries, about 1.1 GB, 1,365 times the memory's bytes; its exhaustive read is estimated, not measured, at about 2 charged hours for 27 cells); anything about a learned retriever; anything for line P. The printed sentence beside every R-KNN figure is: "R-KNN is a non-learned store of 6,144 training contexts at the memory's byte count; it is not retrieval as normally used, whose store grows with the data (about 1.1 GB here). A memory ahead of R-KNN is not ahead of retrieval; a memory behind R-KNN is behind a byte-matched store of raw contexts." Calibration stores use 329301 + c, built from the calibration stream up to 16,384 updates. **Drafter's recommendation: in, as a descriptive readout at matched bytes, with that sentence printed beside it (the reviewer finds it acceptable as a descriptive readout and makes no recommendation either way, noting the added implementation and audit work);** the data-matched store is left to a successor. Reason: it is the first such comparison, it costs minutes, and it changes no label. Reason against, for the human lead to weigh: a byte-matched store is a weak form of retrieval, and a favourable figure is easy to over-read.
15. **Reading of an unfinished run (new).** The trend line of section 12.6 is a registered description, not a label. The reviewer left open whether an "ordering identified without convergence" rule is wanted and judged that any such rule, chosen knowing P10-I-S3, is the human lead's call. Recommendation: no such rule; the trend line with its sentence is the most this design can honestly say.

**What the drafter could not decide from the records:** whether the P2→P3 control lineage can be reproduced for new seeds past both seed whitelists (the identity gate on nine parents decides); the actual size of both pools after exclusion (section 6.5's rules decide; the continuation rung depends on it); how many eligible validation chunks remain for two new panels (the walk decides); whether per-update cost on a memory-mapped uint8 table equals P10-I-S3's (R2 decides).

## 21. Decisions and approval record

- Decision 1 (the human lead): approve this specification, after independent review, for the download, the parent training, implementation and rehearsal only. Every open choice of section 20 is ruled at Decision 1. **Not given.**
- Decision 2 (the human lead, unless he delegates it in writing at Decision 1; recorded in `results/p10i-s6-freeze-<date>/DECISION_2.md`): after the rehearsal record, the auditor's `agree`, the implementation audit, the cost projection and the freeze record, approve the single registered run. **Not given.**
- Grounds stated in advance for not running after Decision 1: an engineering stop of section 12.1, or a cost projection over a cap that the human lead declines to extend. A refusal on any other ground is recorded with its reason before any sealed file is opened, and the outcome is NOT RUN (DECISION 2 REFUSED: reason).
- If the independent recomputation disagrees with the frozen analysis, the frozen labels are recorded as written with the disagreement beside them; no label is changed without a recorded amendment.

No approval of any kind is recorded for this draft. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 22. Review record

First draft (SHA-256 `fe83a1bc…`) reviewed by the `arbor-auditor` subagent (Claude Opus 5.5, per the review's own header), 2026-11-19: `experiments/_scratch/audits/REVIEW_ADR-0031.md`, verdict READY AFTER THE LISTED EDITS, no blocking finding. Second draft by the drafter (Claude Fable 5.2); the confirmation review below is the read the first review asked for. The review is engineering evidence, not Astra validation and not an approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| F1 dense arm declared converged while improving | REQUIRED | APPLIED (C1) | 4, 9.1, 20 item 13 |
| F2 calibration convergence states public | REQUIRED | APPLIED (C4) | 8 |
| F3 licensing table claims a cause | REQUIRED | APPLIED (C11) | 19 |
| F4 likely outcome not stated | REQUIRED | APPLIED (C10), and by the lead's instruction stated in the status block, with the registered trend line; the "ordering without convergence" question is put to the human lead | Status, 12.6, 18, 20 item 15 |
| F5 LEAD GROWING reads as encouraging | ADVISORY | APPLIED: tag text ends with a fixed sentence; δ against the lead printed beside it | 12.6 |
| F6 label name | ADVISORY | APPLIED (C11): LEVEL AT CONVERGENCE | 1, 12.3, 19 |
| F7 compute description | REQUIRED | APPLIED (C6) | 5, 3 |
| F8 V_mean; "content-qualified" | ADVISORY | APPLIED (C7): dependence-qualified | 11, 12.4, 19 |
| F9 rate tie tolerance 0.0005 | ADVISORY | LEFT: kept at 0.0005 and put to the human lead; changing it would be a change after observation | 20 item 6 |
| F10 near-duplicates | ADVISORY | APPLIED: printed share, no rule | 12.5 |
| F11 reading rung under a failed cell | REQUIRED | APPLIED (C2) | 12.2 |
| F12 extension and D-2X figures; R1 ratio | REQUIRED | APPLIED (C14) | 18, 20 item 5 |
| F13 rung 4 hard-coded | REQUIRED | APPLIED (C3); with the continuation rung k_max can also be 5 | 4, 9.5 |
| F14 frozen inputs and imports | REQUIRED | APPLIED (C5) | 15 |
| F15 registered panel and DRY profile | REQUIRED | APPLIED (C7, C8) | 11, 16 |
| F16 identity gate on nine parents; whitelists; control memory; "fresh" | ADVISORY | APPLIED | 7, 16a G9, G10 |
| F17 pool order of operations | REQUIRED | APPLIED (C9) | 6.4 |
| F18 calibration pool can cut the ladder | REQUIRED | APPLIED (C9) | 6.5 |
| F19 pause mechanism | REQUIRED | APPLIED (C8), with ruling 6 limited to a failed resume-identity gate (confirmation review R1) | 16 |
| F20 D0 memory; RSS of the mapped table | ADVISORY | APPLIED | 6.4, 16 |
| F21 OA rates and failures | ADVISORY | APPLIED | 7, 16a G17 |
| F22 no tolerance comparison except NEG-REF | ADVISORY | APPLIED | 11 |
| F23 one doubling of evidence on rows 8, 9 | ADVISORY | APPLIED (C12) | 12.3 |
| F24 Decision 2 and disagreement | REQUIRED | APPLIED (C13) | 21 |
| F25 download record | ADVISORY | APPLIED | 6.3 |
| F26 strict ">" | ADVISORY | APPLIED | 11 |
| F27 seed registry | ADVISORY | APPLIED in part: the test is required here; the registry revision is the auditor's | 14 |
| C15 rulings G1–G22 | — | APPLIED: inserted as written. The review's findings text cited ruling numbers that do not match its own table (the reviewer's error, confirmed in `REVIEW2_ADR-0031.md`): F17's "G7–G10" are G6–G7, F19's "G20" is G18, F24's "G25, G26" are G19. Section 16a is the reference. | 16a |
| Lead's additions: trend line; R-KNN as an open choice; three ladder options; non-delegable marks | — | ADDED in draft 2; reviewed in the confirmation review below | 12.6, 9.5, 18, 20 |

**Confirmation review.** Second draft (SHA-256 `2802816b…`) reviewed by the same `arbor-auditor` subagent (Claude Opus 5.5): `experiments/_scratch/audits/REVIEW2_ADR-0031.md`, verdict READY AFTER THE LISTED EDITS (R1–R14). It found every required finding of the first review fixed or fixed with small residues, and five problems in the new material. Third draft by the drafter (Claude Fable 5.2). **The text with R1–R14 applied has not been re-read by a reviewer.**

| Finding | Disposition | Where |
|---|---|---|
| R1 resume or restart rule; drafter's note removed | APPLIED | 16 |
| R2 ruling numbers in the record | APPLIED | 22 (rows F19, C15) |
| R3 ranges ending at 4 | APPLIED | 4 |
| R4 tag 2 renamed; rung 0 is R16's condition | APPLIED | 12.6 |
| R5 Δ and Q at every rung inside the tag | APPLIED | 12.6 |
| R6 continuation: trigger on convergence states only; rung-4 values hidden; cost inside the cap; uncalibrated-rate caveat | APPLIED, with one sentence added stating the direction of the risk (the lead's instruction) | 9.5 |
| R7 section 17 consistent with the continuation | APPLIED | 17 |
| R8 R-KNN: seeds 320401 + c; store per rung; loss arithmetic; printed sentence | APPLIED; the heading and the cost line of item 14 adjusted to match (reads at five rungs) | 14, 20 item 14 |
| R9 non-finite after U_4 | COVERED by R6 | 9.5 |
| R10 "answers" to "describes" | APPLIED | Status |
| R11 stale cost-table label | APPLIED | 18 |
| R12 typo | APPLIED | 6.4 |
| R13 G11 | APPLIED | 16a |
| R14 ladder recommendation | APPLIED WITH A CHANGE, on the lead's instruction: the reviewer's text recorded "Drafter's recommendation: (c)"; the lead's recommendation is now (a) and the drafter agrees, so the item gives (a) as the recommendation of all three, with the reviewer's reason | 18, 20 item 2 |
| Lead's instructions for draft 3: status line; box for the human lead; default text complete without the continuation rung | APPLIED; not reviewed | Top, 9.5, 18 |

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
