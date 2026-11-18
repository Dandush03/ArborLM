# ADR-0028 — P10-I-S5: physical SSD-backed memory (conditional specification)

**Status: DRAFT 4 — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- Date: 2026-11-18 UTC. Revision 4, after the third independent review (section 15), which probed this machine. Drafted by the lead (an `arbor-lead` subagent, Claude Fable 5.2, as the session reports it) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8. The drafter ran no probe, wrote no store and executed no code; every device figure below is **the reviewer's observation of 2026-11-18**, made on a machine that was not quiet and under an interpreter that is not the platform of record.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification with two parts. The scientific part is unchanged from draft 3 and cannot be evaluated (section 3.2). The engineering part is now a completely specified benchmark of host-side SSD read behaviour on the human lead's machine. Draft 3's sections 4 to 8, 10, 12 and 13 are replaced; its section 3.2, its scientific label rule (section 5) and its review tables are kept word for word.
- No hardware purchase is proposed. The only device is the internal SSD of the human lead's working computer. Nothing here needs administrator access, a tool install, a download or a package outside the lock.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Two questions, two verdicts, never combined

| Verdict line | Question | Evidence it may use |
|---|---|---|
| **ENGINEERING SSD PERFORMANCE** | On this device, under a written uncached read discipline: do the bytes the device is asked for equal the bytes predicted from the layout, what does a page cost, and does a read path's measured time equal its computing time plus its pages' cost? (Sections 4 and 5.) | A synthetic store and synthetic queries |
| **SCIENTIFIC NEURAL-MEMORY ADVANTAGE** | Does one trained neural memory, addressed without an oracle, give better task quality at equal measured block-device traffic than fair storage baselines, at a scale where storage is really needed? | Only a qualified, trained memory (section 3.2) |

A synthetic large-store benchmark tests real storage behaviour. It is **not** evidence of useful neural-memory scaling, whatever it shows. Neither line is summarised by the other. No report sentence joins them, and no paragraph about one line cites the other's label.

| Line | Registered values |
|---|---|
| Engineering, three lines, each read alone (section 5.4) | **EQ-A** BYTES CONFIRMED EXACTLY / BYTES NOT CONFIRMED (reason). **EQ-B** CONTIGUOUS REQUEST CHEAPER PER PAGE / COST PROPORTIONAL TO PAGES / CONTIGUOUS REQUEST DEARER PER PAGE / NOT SEPARATED AT MARGIN. **EQ-C** COST MODEL HOLDS / DEVICE DEARER THAN MODEL / DEVICE CHEAPER THAN MODEL / MODEL GAP MIXED / NOT SEPARATED AT MARGIN. Any of them: ENGINEERING NOT EVALUABLE (reason) |
| Scientific | ADVANTAGE SUPPORTED AT TESTED SCALE / NO ADVANTAGE OVER STORAGE BASELINES / INCONCLUSIVE / SCIENTIFIC NOT EVALUABLE (reason) |

**Draft 3's engineering labels are withdrawn** (SPARSE PATH READS LESS AND IS FASTER AT MATCHED RECALL AND RAM; BASELINE NOT WORSE; MEASURES DISAGREE). They named the winner of a contest between the tree and an ANN index. Section 5.2 shows that this contest is decided by the layout in every regime this draft can define, so no engineering label now names a winner between read paths, and none is "positive" or "negative" for ArborLM. The engineering lines describe the device.

**Why cold and uncached is the registered regime.** It is the regime in which storage traffic is actually paid, and the only one the counter can verify exactly (section 7). A deployed system would also cache hot pages; that is not measured here.

## 2. Background and approval context

### 2.1 What the records already hold

| Finding | Record |
|---|---|
| P7-A: CONCENTRATION-ONLY for both tree kinds: the trees' lower simulated page reads "come from using fewer rows"; "No NVMe experiment on these checkpoints is proposed" | `docs/decisions/ADR-0013-p7a-storage-page-locality.md`, outcome record |
| P7-B: WITHIN 10% OF FLAT CO-ACCESS on both streams for both tree kinds, REPLICATED; decision class N (no storage-locality case for the hierarchy) | `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` section 16 |
| P8: INCOMPLETE; no case LOCALITY-POSITIVE; every locality term acted as a concentration term; the standard flat memory used about 127 effective slots of 4,096 | `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md`; `results/p8-2026-11-14/SUMMARY.md` |
| P10-S1 "Estimated storage traffic": arithmetic and simulation, no device; 1,024 value bytes per query at 8 rows | `results/p10s1-run-2026-11-17/RESULTS.md` |
| P10-S1 supplementary throughput, in RAM, descriptive, not the registered stage: T-OQ 10,106 / 10,211 / 10,132 queries/s at batch 1 at 1,024 / 4,096 / 16,384 slots (about 99 µs per query); F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | `results/p10s1-run-2026-11-17/OUTCOME.md` section 3; `supplement/throughput_supplement.json` |
| P10-S1 mean a_use at 32K/16K: at the registered read point U_P, T-OQ 0.401, F-OQ 0.916, D-OQ 0.957; at the run length, 0.697, 0.992, 0.999 | `OUTCOME.md` section 4 |
| P10-S0: ADDRESSING-QUALIFIED (4,096 AND 16,384) for arm A5-D at 0.5 facts per slot; OVERLOAD NOT QUALIFIED | `results/p10s0-run-2026-11-16/OUTCOME.md` |

Everything about storage in P7, P8 and P10-S1 is simulated or arithmetic. No ArborLM record contains a registered measurement on a device.

**P7-A's lesson, carried into the rules.** A read path that examines fewer candidates reads fewer pages by construction, whether or not it finds the right rows. On a device the same holds, and under the read discipline of section 7 it holds exactly: bytes per query are a function of the layout and the candidate set. So this draft separates what the arithmetic decides (section 5.2, registered as a prediction before any device read) from what only the device can answer (section 5.4).

**The scale gap** (unchanged). A slot is 64 key bytes (16 × 4) plus 128 value bytes: 192 bytes. The largest cell at which learned addressing is qualified has 16,384 slots: 16,384 × 192 = 3,145,728 bytes. The machine has 51,539,607,552 bytes of RAM; 51,539,607,552 / 3,145,728 = 16,384. This gap, not the device, stands between the project and the scientific verdict.

### 2.2 What the trained tree and the index are (from the code)

`studies/p9/model.py` `_top_tree`, `studies/p10s1/model.py`, `studies/p10s1/core.py` (`BRANCH_SIZE = 256`, two branches visited), `studies/p10s1/index.py`:

- **T-OQ.** N slots in N/256 branches of 256 slots. One router row per branch (16 values). Route score = cos(q, router row)/0.2 for **every** branch: the router is one level and is scanned in full. The two best branches are visited (ties to the lower id). Each of their 512 keys is scored cos(q, key)/0.2 plus the log-softmax, over all branches, of its branch's route score (the branch prior). The top 8 are read; the weights are the softmax of those eight scores.
- **The index (F-OQ-IVF).** k-means into N/256 lists; all centroids are scored; lists are visited in descending centroid score until at least 512 candidates are collected; the 8 best by cosine are read.

So the trained tree's read path already has the shape of a one-level clustered index with a fixed number of lists visited. It differs from the index in three things only: its leaves have a fixed size, its routing rows and its slots are learned, and it adds the branch prior. A synthetic store has no learned rows, so only the fixed leaf size and the prior's arithmetic can be carried into a benchmark. Section 5.2 draws the consequence.

### 2.3 The human lead's words on this study

Quoted as the coordinating lead relayed them to the drafter for this draft. At this commit they are not all in the committed record `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`; **the lead adds them to that record**, and this section is not that record.

> we could do a better test in my ssd not sure why not

> ok, but you are allowed to download up to 75gb of data needed for the ssd test if needed

> if you need 200gb or 250gb for the test im also ok with that

and the general delegation:

> and you have my permission to auto approve everything until you complete P10-I

**How the lead reads them, and no further.** (1) The engineering part may be entered before a neural memory is qualified at scale: entry condition EC1 (section 3.1). (2) Writes to the drive of up to 250 GB are permitted; they are to be kept to the minimum needed, and this draft caps them at 40 GB (section 6). (3) Downloads of up to 75 GB are permitted if needed; none is expected, because the store is synthetic. (4) Nothing that needs administrator access or a tool install is permitted, and no package outside the lock. The words do not say that the scientific part may be entered, that any threshold may move, or that any result is expected. This reading supersedes, for this study, the exclusion of the SSD write budget in the delegation record's sections 3 and 6; that is the human lead's change, made in his own words above, not the drafter's. This draft itself is NOT APPROVED: the decisions of section 11 are recorded by the lead or the human lead, not by this text.

## 3. Entry criteria

### 3.1 Engineering part

- **EC1, entry before qualification.** Met by the human lead's first sentence above, as the lead reads it. It is recorded in the delegation record before Decision 1.
- **EC2, write budget.** Section 6 approved (40 GB hard cap, inside the 250 GB permitted).
- **EC3, device record (restated after the third review, F6).** Before and after every stage that writes, the study records: SMART status (`diskutil info disk0`; it must read `Verified`), free space (`df -k`), and the disk0 driver's bytes written since boot (`ioreg -r -c IOBlockStorageDriver -l -w0`). Lifetime bytes written, percentage used and temperature cannot be read without administrator access or a tool install (the reviewer's observation); they are printed **NOT READABLE** in every record and report, and that does **not** make the part NOT EVALUABLE. Wear is accounted in the study's own bytes written (section 6). A SMART status other than `Verified` is PAUSED and goes to the human lead.
- **EC4, method.** Every check of section 7 passed in R1 under the platform of record.
- **Decisions.** Decision 1 covers implementation, R0, R1, C and the two rehearsals (at most 2.3 GB written). Decision 2, taken on the rehearsal records and an independent implementation audit, covers E1, P and E2.

### 3.2 Scientific part

All of the following, for **one and the same trained system** at one slot count N and one load:

- **Q1, qualified access.** P10-I-S0 (ADR-0023) registers, by the procedure of its section 7, step 3 (**OVERLOAD-QUALIFIED UP TO L_Q**) or step 4, 5 or 6 (each ending **ADDRESSING QUALIFIED UP TO L_Q**), recomputed and accepted. The system is A5-D as ADR-0023 freezes it, at one of ADR-0023's tested cell types (its section 4.1) with load at most L_Q, where Line Q **HOLDS** (its section 6.4). This is ADR-0023's own licence (its section 15, items 1 and 2: the licence depends on L_Q only, whatever the status of the first failing load). Steps 0 to 2 give no licence. Lines A and G license nothing. An oracle-addressed result does not count. The licence is for a flat memory; ADR-0023 section 15 item 7 says it tells nothing about addressing into a tree.
- **Q2, useful capacity under that addressing.** The same system, addressed by Q1's learned recipe and not by an oracle, holds useful capacity at N. **There is currently no approved source of this, and none proposed for approval.** ADR-0024's C-CAPACITY and X-CAPACITY are oracle-addressed and do not satisfy Q2: Q1 and Q2 would be met by two different systems. ADR-0024's lane L (its section 13) is the only place the programme would register capacity under learned addressing, and in the third draft it is "to be specified in a revision of this ADR before its own freeze; not approved with this draft": its line L-CAPACITY has only the registered values OMITTED — NOT LICENSED and OMITTED — NOT LICENSED AT THE FREEZE. Q2 can be met only after lane L is specified, approved, run and accepted with a positive value that its revision defines, or after another approved study of the composed system. Whether a lane L label with no dense or saturation reading would be "useful capacity" in this sense is `PENDING LEAD REVIEW` and cannot be judged until that revision exists.
- **Q2-U, utilisation, fixed now.** *Measure.* Take every fact of the cell once as a query, on Panel A. Count, for each slot j, the number of times c_j it is among the 8 rows selected for a query (all 8 selections of every query, unweighted). N_eff = exp(−Σ_j p_j ln p_j) with p_j = c_j / Σ c, the entropy-effective number of slots (P8's measure, `results/p8-2026-11-14/SUMMARY.md`). λ = Σ c / N is the number of selections per slot. E(λ) is the expected N_eff / N when the same number of selections falls on slots uniformly at random; by the reviewer's computation E = 0.365, 0.564, 0.752, 0.875, 0.938 at λ = 0.5, 1, 2, 4, 8. *Why all 8 and not the top one:* at load 0.5 the top-1 count has λ = 0.5, where random placement gives 0.365 and even a perfect one-fact-per-slot memory gives exactly 0.5, so an absolute floor there would sit on the boundary by construction. With all 8 selections at load 0.5, λ = 4 and E = 0.875. *Floor.* **U = (N_eff / N) / E(λ) ≥ 0.5**, with N_eff / N, λ and E(λ) printed beside U. Reason: U compares the memory's spread with unstructured use at the same number of selections; below one half the reads are concentrated on a minority of the slots that even random use would touch, and most bytes on the device are then not memory in use. The figure is not fitted to pass: P8's standard flat memory had N_eff about 127 of 4,096 at λ = 64 (E = 0.992), U about 0.03. `PENDING LEAD REVIEW`. No sibling draft registers a utilisation label, so U is measured in S5's own reference check.
- **Q3, real storage need.** The store at N is larger than the RAM available to it.
- **Q4, fair baselines and measured traffic.** Sections 4, 5 and 7 hold.

**What follows from the sibling drafts as they stand: the scientific part cannot be evaluated as capped, for two independent reasons.**

1. **No approved learned-address capacity line.** Q2 has no approved source (above). Until ADR-0024's lane L is specified and approved in a revision, or another study is approved, no outcome of the programme can satisfy Q2.
2. **The largest licensed cell is about 3 MB.** ADR-0023 licenses learned addressing only at its tested cell types with load at most L_Q (its section 15, item 1); the largest has 16,384 slots, and lane L may use only licensed cells. 16,384 × 192 bytes = 3,145,728 bytes. So even with Q2 met, Q1, Q2 and Q3 can be true together only if RAM is restricted by construction. Under this ADR's own ceilings (16 GB per store, 48 GiB of RAM) Q3 can likewise be met only by construction.

Any scientific label would then carry `RAM RESTRICTED BY CONSTRUCTION`, and such a label cannot show that storage was needed (section 14). The part is kept here so that the conditions are on record before any result exists. Today, and after any outcome of P10-I-S0 to S3 as drafted, the line reads **SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)**.

"RAM restriction" on macOS without administrator access is not an enforced limit: there is no per-process page-cache limit. It means only uncached reads (section 7) plus the resident budget of section 5.

Section 3.2 is draft 3's text, unchanged. Where it says "the resident budget of section 5", draft 4 has that budget in section 4.2.

## 4. The benchmark: store, layout, arms, workload

### 4.1 The store

One store, written once. It is T-OQ's shape scaled up: branches of 256 slots, a 64-byte key and a 128-byte value per slot.

| Quantity | Value | Why |
|---|---|---|
| Page | 16,384 B | `hw.pagesize` on this machine. The reviewer's probe 1E: a 4 KiB uncached request reads 16 KiB. Every request is whole pages at page offsets |
| Row | key 16 × float32 (64 B) + value 32 × float32 (128 B) = 192 B, little-endian | P10-S1's key and value widths |
| Branch | 256 rows = 49,152 B = **exactly 3 pages**: 1 key page (256 × 64 B) and 2 value pages (128 values each). No padding | `BRANCH_SIZE = 256` |
| Branches B | 349,525 | The largest whole number of branches in 16 GiB |
| Rows N | 89,478,400 | 256 × B |
| File | 17,179,852,800 B = 1,048,575 pages (16 GiB less one page) | The reviewer's smallest study: 16 GiB satisfies disjoint pages and index realism; 8 GiB was the least it would defend |
| Rehearsal store | B_r = 21,845 branches, 1,073,725,440 B | Same generator and layout, 1 GiB |

**Layout (one file).** Pages 0 to B − 1 are the **key region** (5,726,617,600 B, 5.33 GiB): page b holds the 256 keys of branch b. Pages B to 3B − 1 are the **value region**: pages B + 2b and B + 2b + 1 hold the values of rows 0–127 and 128–255 of branch b. Row j of branch b has its key at byte 64j of page b and its value at byte 128 × (j mod 128) of page B + 2b + ⌊j/128⌋. The key region is, as it stands, the contiguous key file an exact scan needs, so S-FLAT needs no file of its own. A second, interleaved layout was considered and dropped: it would cost another 16 GiB of writes to compare one 48 KiB request with three requests, which the request-size sweep (SWEEP) measures directly on the one file.

**Contents (synthetic; generated, never downloaded).** For branch b: a centre c_b = normalize(g), g ~ N(0, I₁₆); 256 keys normalize(c_b + σ·ε), ε ~ N(0, I₁₆/16); values 32 × N(0, 1). Generation is by blocks of 1,024 branches; block g's generator state is the first 8 bytes of SHA-256(`p10is5|store|<seed>|<g>`) reduced modulo 2⁶³, so any page can be regenerated from the seed without reading the file. The **routing table** is one row per branch: the normalised mean of the branch's 256 keys. Rows are placed by the generator, not by nearest centre, so a key may lie nearer another branch's routing row, as a trained slot may.

**Why the store need not exceed RAM.** The page cache is excluded per read by the discipline of section 7, and the per-process counter verifies that exactly on every pass (the reviewer's probes 1B, 1B2, 3). A size-based cold state is not valid here: reclaimable file-backed pages (about 14 GB at the review) mean even a store twice the size of RAM would be partly cached and never exact. The human lead's 250 GB permission would allow a store above RAM; the reviewer's figures show it would buy nothing exact, so it is not used. The cost of this choice is stated in section 14: the store fits in RAM and is only made to behave as if it did not.

### 4.2 Resident budgets (formulas)

R = 64 × B = 22,369,600 B (the routing table). K = 64 × N = 5,726,617,600 B (all keys). "Resident" is an accounting rule: the bytes of the arrays an arm holds, counted from their shapes, with `ri_phys_footprint` printed beside it. macOS enforces no per-process memory limit without administrator access (the reviewer's finding). Each pass runs in its own process, which holds only its arm's arrays.

| Rung | Budget | Arms |
|---|---|---|
| NONE | 0 (a 1 MiB scan buffer) | S-FLAT |
| ROUTING | R | S-TREE, IVF-1, IVF-2, IVF-4, IVF-8 |
| KEYS | K | X-RES |
| (address given) | 0 | KV |

### 4.3 Arms

Every arm reads the same file through the same primitive: `os.pread` of whole pages on one descriptor opened with `F_NOCACHE` 1 and `F_RDAHEAD` 0, one thread, queue depth 1, `torch.set_num_threads(1)`.

| Arm | Read path | Requests per query | Predicted bytes per query |
|---|---|---|---|
| **S-TREE** | T-OQ's read path (section 2.2) on the synthetic routing table: score all B routing rows in RAM; the 2 best branches; read their 2 key pages; score the 512 keys with the branch prior; top 8 (ties to the lower id); read the distinct value pages holding those 8 rows | 2 + v single-page requests, v from 1 to 4 | 16,384 × (2 + v) |
| **IVF-p**, p = 1, 2, 4, 8 | In-project IVF-flat: the routing table is its centroid table (the same array); the p best lists by cosine; read their p key pages; top 8 by cosine, no prior; read the distinct value pages. IVF-2 is P10-S1's index rule on this layout (512 candidates = 2 lists) | p + v, v from 1 to min(8, 2p) | 16,384 × (p + v) |
| **X-RES** | All keys held in RAM (regenerated from the seed); exact search; read the value pages of the exact top 8 | v, from 1 to 8 | 16,384 × v |
| **KV** | The addresses of the exact top 8 are given; read their value pages. The floor: what storage costs when the address is known | v, from 1 to 8 | 16,384 × v |
| **S-FLAT** | Exact search with nothing resident: read the whole key region in 64-page (1 MiB) requests, then the value pages of the top 8 | 5,462 + v (5,461 of 64 pages and one of 21 pages) | 5,726,617,600 + 16,384 × v |
| **SWEEP** | Not a read path: single requests of s = 1, 2, 3, 4, 8, 16, 64 contiguous pages at registered offsets in the value region, 400 per size | 1 | 16,384 × s |

Within a query, requests are issued in the order key pages (by route rank), then value pages (ascending offset). A graph index is out of scope: it is not buildable in pure Python at this size in hours (the reviewer's judgement), and no package outside the lock is permitted.

### 4.4 Workload, recall reference, queries per pass

- **Queries.** A query is a stored key plus noise: choose a branch and a row uniformly; q = normalize(key + (σ/2)·ε). One pattern only. Draft 3's second pattern is withdrawn: a skewed pattern re-reads pages and cannot be disjoint.
- **σ is fixed in stage C, in RAM, before any store is written:** the largest σ in {0.05, 0.10, 0.15, 0.20, 0.30, 0.40} at which IVF-2's recall at 8 is at least 0.95 on 500 calibration queries over a full-size key set from the calibration seed; if none qualifies, 0.05, and the fact is printed. This fits the workload so that a read of two branches passes the floor. It is stated as such: recall on this workload is a validity condition, not a finding.
- **Recall floor R_min = 0.90**, against exact search (unchanged). The reference is the exact top 8 by cosine over all keys, computed in RAM in stage P from regenerated keys, never from the device. An arm whose recall is below 0.90 in any repeat is tagged BELOW RECALL FLOOR: it is still timed (EQ-C does not depend on recall) but it does not appear in the matched table of section 5.5. The ROUTING rung's operating point is the smallest p whose IVF-p meets the floor in every repeat; this is fixed in stage P, before any device read, so no operating point is chosen on a timing.
- **Queries per pass.** S-TREE, each IVF-p and KV: 1,000. X-RES: 200 (each costs an exact search over 89,478,400 keys on one thread). S-FLAT: **2 per repeat, 10 in all**, run after the last block. Reason: its bytes are known by construction and identical for every query, so more queries add nothing on bytes; ten give a median and a range of the scan time. At the reviewer's 72 to 121 µs per page a scan is 25 to 42 s, so ten are at most about 7 minutes; 1,000 × 5 would be 35 to 60 hours (F10).
- **Disjoint pages.** The plan builder, in RAM, takes candidate queries in a fixed order and accepts one only if no page it requests is requested by any query or sweep request already accepted in any pass of any repeat ("generate until met", from at most three times the needed number of candidates; running out is an ENGINEERING STOP before any device read). So until S-FLAT runs, no page of the store is read twice in E2. S-FLAT reads the whole key region and therefore runs last.

## 5. Measures, what the layout decides, the prediction, and the registered questions

### 5.1 Measures

- **Bytes read per pass**: `ri_diskio_bytesread` of `proc_pid_rusage(getpid(), RUSAGE_INFO_V2)`, read through `ctypes` on `/usr/lib/libSystem.B.dylib`, as the reviewer's probe did (`ssd_probe_0028.py`, `proc_io`), in the single process that issues every read of the pass. Not `getrusage` (its block counts stayed 0 in the probes) and not `psutil` (no I/O counters on macOS). Cross-checks, printed only: the APFS volume's "Bytes read from block device" and the disk0 driver's `Bytes (Read)`, which are system-wide. All are host-side, block-layer figures. They are never called NAND or media traffic.
- **Latency per query and per request**: `time.perf_counter_ns` around each query (routing, reads and selection included) and around each request. Counter snapshots and all `ioreg` calls are outside the timed region.
- **Queries per second**: queries of the pass over the sum of their latencies, at queue depth 1.
- **Recall at 8**; **resident bytes** (section 4.2).

### 5.2 What is decided by construction (F5, F13)

Under the read discipline, bytes per query = 16,384 × (pages requested). Nothing about the device enters. Therefore:

1. **S-TREE against IVF-2: the same key pages, by construction.** Both score every routing row and take the two best by the same ranking and the same tie rule, so for one query they read the same two key pages. They differ only in the prior, which is one constant per branch (ADR-0029 section 3).
2. **S-TREE's recall cannot exceed IVF-2's, by construction.** For a fixed candidate set, the top 8 by cosine contain every candidate that is in the exact top 8. The prior can only replace such a row with another.
3. **At equal recall and budget R the tree cannot read fewer key pages than the index, by construction.** The index's scan of the routing rows picks the nearest leaves exactly. Any difference in value pages (1 to 4) follows from which 8 rows are selected and is arithmetic too.
4. **A differently built index (unbalanced k-means lists) would differ only through the partition** of an invented distribution. Its bytes would again be computable before any read, and the result would be about a balancing step on synthetic data, not about ArborLM's trained tree. It is not built.
5. **KEYS rung: tied by construction.** With all keys resident, any arm searches exactly and reads exactly the 8 value rows' pages. Tree and index are the same arm there (X-RES).
6. **S-FLAT: loses on bytes by construction** at rung NONE (5.33 GiB per query) and equals X-RES in pages at rung KEYS.
7. **A deeper router** (several levels, so that less than R is resident) is not T-OQ's read path and has no trained counterpart in the records. It is not defined here.

**Conclusion, stated plainly: in every regime this draft can define, the bytes comparison between the tree and the index is fixed by the layout, and their time differs only by a few arithmetic operations in RAM. No contest between them is registered.** S-TREE and IVF-2 are both run, and their figures are printed side by side under the heading BY CONSTRUCTION; no label compares them. A trained tree could differ from this through learned routing rows, learned slot placement and a learned prior. None of these exists in a synthetic store, and none is measured.

### 5.3 The registered prediction

Stage P runs in RAM after the freeze and before E2. For every pass of every repeat it writes the accepted queries, each query's ordered list of requests (offset, length), the pass's predicted bytes (16,384 × pages), each arm's recall and the operating point. The prediction record's SHA-256 is recorded and E2 refuses to start on any other. Predicted bytes per query lie in the ranges of section 4.3; the exact figures follow from the seeds.

### 5.4 The registered questions (what only the device answers)

Five repeats (blocks). One block = one pass of each of S-TREE, IVF-1, IVF-2, IVF-4, IVF-8, KV, X-RES and SWEEP, in the order given by that repeat's arm-order seed.

**EQ-A. Does the device confirm the predicted bytes exactly?** For every pass, the counter rule of section 7. *BYTES CONFIRMED EXACTLY*: every pass of at least 4 of 5 repeats, and every S-FLAT query, has counter bytes equal to predicted bytes. Otherwise *BYTES NOT CONFIRMED* with the reason of the first failing pass. There is no margin: the quantity is deterministic (F4).

**EQ-B. What does a page cost, and is a contiguous request cheaper per page?** c_r(s) is the median latency of the 400 s-page requests of repeat r. Printed for every s with p90, p99 and maximum. Label on ρ_r = c_r(3) / (3 × c_r(1)); s = 3 because a branch is three pages, so this is the figure a future layout decision would need:

| Label | Rule |
|---|---|
| CONTIGUOUS REQUEST CHEAPER PER PAGE | ρ_r ≤ 1 − m_t in at least 4 of 5 repeats |
| CONTIGUOUS REQUEST DEARER PER PAGE | ρ_r ≥ 1 + m_t in at least 4 of 5 |
| COST PROPORTIONAL TO PAGES | \|ρ_r − 1\| < m_t in at least 4 of 5 |
| NOT SEPARATED AT MARGIN | otherwise |

**EQ-C. Is a read path's time its computing time plus its pages' cost?** For each of the seven read-path arms a and repeat r: after the device pass, the same process replays the same queries from the bytes it has just read, issuing no request, which gives t_cpu(q). The model is L̂(q) = t_cpu(q) + pages(q) × c_r(1). The gap is g(a, r) = median_q L(q) / median_q L̂(q) − 1. Arm a is DEARER if g ≥ m_t in at least 4 of 5 repeats, CHEAPER if g ≤ −m_t in at least 4 of 5, WITHIN if \|g\| < m_t in at least 4 of 5.

| Label | Rule (first match) |
|---|---|
| COST MODEL HOLDS | every arm WITHIN |
| MODEL GAP MIXED | some arm DEARER and some arm CHEAPER |
| DEVICE DEARER THAN MODEL | some arm DEARER |
| DEVICE CHEAPER THAN MODEL | some arm CHEAPER |
| NOT SEPARATED AT MARGIN | otherwise |

**The margin m_t (F4), fixed by this rule now and by its value at the freeze.** CV_R is the largest repeat-to-repeat coefficient of variation (sample standard deviation over mean of the five per-repeat medians) among c(1), c(3) and each read-path arm's median latency, in the counting rehearsal. m_t = max(0.10, 2 × CV_R). Reasons: a difference under a tenth is not an engineering finding on a working computer; twice the spread keeps noise alone from crossing. If m_t would exceed 0.30, EQ-B and EQ-C are registered as ENGINEERING NOT EVALUABLE (TIMING SPREAD) at the freeze, before any registered read, and their figures are printed descriptively. A repeat with an invalid pass (section 7) is invalid; the denominator stays 5; fewer than four valid repeats is NOT EVALUABLE.

### 5.5 Printed, with no label

- **The matched table**: for each rung, the arm at recall ≥ 0.90 (S-FLAT; the ROUTING operating point, and S-TREE if it meets the floor; X-RES), with resident bytes, recall, predicted and counted bytes per query, latency median, p90, p99, maximum and mean, and queries per second, per repeat. This is how cost changes with the resident budget. Its order on bytes is by construction; its order on time is largely fixed by computing time in RAM (X-RES pays an exact search). It is a description, not a contest.
- S-TREE beside IVF-2, BY CONSTRUCTION. KV beside every arm. Every IVF-p with its recall.

### 5.6 Scientific label (kept from draft 3, word for word)

**Scientific label** (structure fixed now; read only if Q1 to Q4 hold). The memory is read at its registered operating point; its mean bytes per query there is b0. Each baseline (ANN, S-FLAT, and KV) is swept over a registered list of candidate budgets and read at the smallest budget whose bytes per query are at least b0, so a baseline never has less traffic than the memory. No such point: SCIENTIFIC NOT EVALUABLE (NO MATCHING POINT AT EQUAL BYTES). KV is addressed by the task's own surface key, never by an oracle slot address; if KV's quality is within the margin of the memory's, every label carries `LOOKUP SUFFICIENT ON THIS TASK`. Five fresh draws; a replicate favours the memory only if on both panels it is ahead of every baseline by the margin, and favours a baseline if on either panel that baseline is ahead. ADVANTAGE SUPPORTED: at least 4 of 5 favour the memory. NO ADVANTAGE: at least 4 of 5 favour one and the same baseline. INCONCLUSIVE: otherwise. Margins are fixed by the later revision before any such draw.

Rows read, pages simulated, parameters touched and any other logical count are never reported as measured traffic or as efficiency. The predicted bytes of section 5.3 are a prediction; only counter bytes are called measured.

## 6. Storage-write budget, free space, store hygiene

| File | Stage | Bytes | Builds planned |
|---|---|---|---|
| Probe files | R0 | at most 67,108,864 (64 MiB) | 1 |
| KV file | R1 | 1,073,741,824 | 1 |
| Positive-control file | R1 | 67,108,864 | 1 |
| Rehearsal store (used by both rehearsals) | M | 1,073,725,440 | 1 |
| The store | E1 | 17,179,852,800 | 1 |
| **Planned total** | | **19,461,537,792 B (19.46 GB)** | |
| One rebuild of each file except the probes (recovery from a polluted store, section 7) | | 19,394,428,928 | |
| **Planned plus one rebuild of everything** | | **38,855,966,720 B (38.86 GB)** | |
| **Hard cap, all stages and attempts, failed ones included** | | **40,000,000,000 B (40 GB)** | |

- **Per file:** at most two builds of any file. A third is PAUSED and goes to the human lead.
- **Share of the drive**, from the reviewer's figures (drive 2,001,111,162,880 B; mean write rate since boot 5.53 MB/s): the cap is **2.00 %** of one full drive write and about 2.0 hours of this machine's ordinary writing; the planned total is 0.97 % and about 1 hour. The cap is below the reviewer's 64 GB and uses 16 % of the 250 GB the human lead permitted. Endurance is not readable and no figure for it is assumed.
- **What is charged:** the study's own logical bytes written, before each write, and the larger of that and its `ri_diskio_byteswritten` after it (they were equal in the reviewer's probe 1A). The system-wide counter is recorded and not charged. A run stops before any write that would pass the cap: **PAUSED**, resumable. Only the human lead changes the cap, on projection, never on outcome values.
- **Free space:** at least 500 GB at all times (680.0 GiB free at the review). Checked before every write stage.
- **Store location:** one directory whose name ends in `.noindex`, under the human lead's home directory, outside every git worktree and every synced folder; its path is in the plan.
- **Hygiene, all without administrator access, checked in R0, before E1, before each E2 block and after deletion:**

| Check | Command | If it cannot be made or fails |
|---|---|---|
| Local snapshots | `tmutil listlocalsnapshots /` and `/System/Volumes/Data`; `diskutil apfs listSnapshots disk3s5` | A snapshot present while a store exists: recorded STORE RETAINED BY SNAPSHOT; its removal is the human lead's action. Not a stop for reads |
| Time Machine | `tmutil destinationinfo`; `tmutil isexcluded <dir>` | Recorded. Setting an exclusion is attempted only if it needs no administrator access; otherwise printed EXCLUSION NOT SET |
| Spotlight | `mdutil -s`; `mdfind -onlyin <dir> .` must return nothing | The `.noindex` rule is untested (the reviewer's note). If the directory is indexed: PAUSED before E1; a reader that cached store pages is caught by the counter rule in any case |
| Deletion | The file is unlinked, absence checked, free space and snapshots recorded | STORE RETAINED BY SNAPSHOT if a snapshot holds it |

Any check whose command needs administrator access on the platform of record is printed NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS and the study continues on the counter rule. Stores are written once, never rewritten in a loop, persist across a PAUSE and are deleted after the independent recomputation. Update traffic (trained updates in place on SSD) is write-intensive and is **outside** this document.

## 7. The counter rule and the read discipline (F1, F2, F7)

**Counter rule (exact; replaces draft 3's ratios 0.9, 1.1, 0.1 and 0.05).** For every uncached pass, the per-process bytes read between the snapshot before the first request and the snapshot after the last must equal 16,384 × the number of pages requested (a request of fewer than 16,384 bytes would count its whole page; the study issues none). Below: **STORE PAGES CACHED**. Above: **COUNTER CONTAMINATED**. Either makes the pass invalid. The rule was chosen after the third review's probes on this machine (2026-11-18: ratio 1.000 on probes 1B, 1B2, 3; 0 on cached pages), before any registered observation. With it no arm can benefit from cache hits, which is the P7-A mechanism closed exactly. The process's bytes written during a read pass must be 0.

**Read discipline.**

1. Stores are written only on a descriptor with `F_NOCACHE` 1 (`fcntl` command 48), in 1 MiB `os.pwrite` calls, and closed after `F_FULLFSYNC` (51). A buffered build leaves the store warm (probe 2(i)).
2. Every read of a store file by any part of the study (arms, checks, hashes, the plan builder, a human) uses `F_NOCACHE` 1 and `F_RDAHEAD` 0 (45) and whole pages at page offsets. `F_NOCACHE` does not bypass pages already cached (probe 1D): one cached read pollutes those pages until evicted. Reference data are regenerated from the seed, not read from the store; no memory mapping; no `shasum`, `cat` or Finder preview of a store.
3. The positive control (cached reads, second pass must count 0 bytes) runs **only on R1's own control file**, never on a store.
4. Every import, allocation and warm-up happens before the first snapshot; no file other than the store is opened between snapshots; results are written after the last snapshot.
5. **Recovery from a polluted store** (a pass below prediction): the pass and its repeat are invalid; the store is deleted and rebuilt once, charged to the write budget, and the invalid repeat is run again on the rebuilt store. A second pollution is PAUSED: a restart, or `purge`, is the human lead's action (the reviewer did not run `purge`; that it needs administrator access is untested).
6. **Value parity (F14): bit identity.** SHA-256 of every page read equals SHA-256 of the regenerated page. A mismatch is an ENGINEERING STOP (DATA MISMATCH), not a label.

**R1 must show, under the platform of record, on its 1 GiB KV file:** the counter rule on a first and a repeated uncached pass; the positive control; the pollution control (probe 1D) on the control file; the 4 KiB amplification (probe 1E) on the control file; a device-cache test (uncached re-reads back to back at working sets of 256 MiB, 512 MiB and 1 GiB: a re-read faster than its first read by more than m_t at the largest set is DEVICE CACHE SUSPECTED and is the lead's stop before the freeze); and disk0 driver bytes and operations over a 10-minute idle window. A failed check is ENGINEERING NOT EVALUABLE with the reason: NO PHYSICAL COUNTER, CACHE NOT DEFEATED, POSITIVE CONTROL FAILED.

**What cannot be verified from software:** the drive's internal caches and NAND traffic. Disjoint pages, the arm order from a seed, and S-FLAT last are the safeguards; latency is the only signal. Encryption (FileVault), copy-on-write and fragmentation are properties of this device, stay on and are recorded.

## 8. Stages

| Stage | Writes | Machine | Content |
|---|---|---|---|
| R0 device record | ≤ 64 MiB | shared | EC3 record, fingerprint, hygiene checks, the reviewer's three probes repeated under the platform of record |
| R1 method rehearsal | 1.14 GB | **alone** | Section 7's list |
| C workload calibration | none | shared, memory guard | σ (section 4.4), in RAM |
| Candidate plan | none | shared | `plan.json` written |
| M measuring rehearsal | 1.07 GB | **alone** | Every stage end to end on the rehearsal store against the candidate plan; rates and times measured |
| Caps | none | — | Charged hours so far + 2 × projected remaining (ADR-0029's rule) |
| K counting rehearsal | none | **alone** | The same, against the candidate plan itself, under the caps just set; gives CV_R and m_t and the quiet figures |
| Freeze, Decision 2 | none | — | Refuses unless the plan file has the hash in K's record |
| E1 store build | 17.18 GB | not alongside another study's wall-time stage; memory guard | Checksummed 1 GiB chunks; resumable |
| P prediction | none | shared, memory guard | Section 5.3 |
| E2 read benchmark | none | **alone** | Five blocks, then S-FLAT |
| S scientific comparison | — | **alone** | Not entered (section 3.2) |
| Analysis, report, independent recomputation, deletion | none | shared | The auditor receives the specification, code and records, not the lead's conclusions |

**R1, M, K, E2 and S run alone on a quiet machine.** Checked at the start of the stage, before every block and at its end, all without administrator access:

- 1-minute load average at most 1.0 (`sysctl -n vm.loadavg`);
- **no other study's process alive**: no process, other than the stage's own, whose command line contains `studies/`, `arborlm`, `pytest` or `torch` (`ps -Ao pid,command`);
- `HIDIdleTime` at least 600 s (the human lead is not using the machine);
- AC power, power mode not low, no thermal warning (`pmset -g batt`, `pmset -g`, `pmset -g therm`);
- disk0 driver read and write rates and operations over a 30 s window at or below the 95th percentile of R1's idle window, fixed at the freeze;
- no sleep or restart inside a block (boot time unchanged; the stage runs under `caffeinate -i`, a system tool).

If the check fails, the stage waits and retries every 10 minutes for at most 6 hours, then is **PAUSED** with the failed readings recorded and is rescheduled, in up to three further sessions; only then ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET). A block that was not quiet at its end is discarded and repeated on fresh pages only if the plan holds spare accepted queries; otherwise that repeat is invalid. No latency or throughput figure is registered from a block that was not quiet. Every wait has a deadline.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind (DIRECTION.md section 5) | Rule |
|---|---|---|
| 40 GB written; two builds per file; 500 GB free | Resource cap (physical) | Only the human lead changes it, on projection, never on outcome values. Reaching it is PAUSED, resumable from the last verified chunk |
| Charged hours (section 10) | Resource cap | Set before K by the rule; extendable on projection; PAUSED, resumable |
| Memory guard: 12 GiB of `ri_phys_footprint` per process, one such process at a time (F12) | Resource cap | A stage refuses to start if its projected peak (K + R + 1 GiB ≈ 6.4 GiB for C, P and X-RES) exceeds it; passing it at run time is ENGINEERING STOP (MEMORY GUARD) |
| Store size; one store; arms; p values; sweep sizes; queries per pass; 5 repeats; S-FLAT 10 queries; σ grid; candidate factor 3 | Design ceiling | Fixed now. "Generate until met" for accepted queries, within the factor |
| Quiet sessions (1 + 3); retry 10 min for 6 h; idle window 10 min | Design ceiling | Fixed now |
| Load 1.0; idle time 600 s; background I/O at R1's 95th percentile; counter exactness; bit identity | Validity threshold | Fixed now (the I/O figures by rule, at the freeze); never changed after |
| R_min 0.90; m_t rule and its 0.10 floor and 0.30 ceiling; 4 of 5; the label rules of 5.4; U ≥ 0.5 (scientific) | Scientific threshold | Never relaxed after observation |

**ENGINEERING STOP (F8; ADR-0029 section 20, ruling 11).** A code error inside an item, or an environment error (I/O error, out of memory, full disk, data mismatch, plan exhausted), refuses the registered analysis of its stage. The outcome is ENGINEERING STOP (cause). It is never recorded as NOT EVALUABLE and never as a label, and nothing is labelled from that stage until the cause is fixed under a recorded amendment and the stage is run again on pages not yet read. An identity difference in a frozen input is PAUSED — IDENTITY; restoring the file bit for bit lets the stage resume. A drive health warning is PAUSED and goes to the human lead. No limit is extended because a partial result looks close.

**NOT EVALUABLE reasons, checked in this order; the first failing one is the label and all failing ones are printed.** Engineering: NO PHYSICAL COUNTER; CACHE NOT DEFEATED; POSITIVE CONTROL FAILED; TIMING SPREAD (EQ-B and EQ-C only); MACHINE NOT QUIET (after rescheduling); STORE PAGES CACHED or COUNTER CONTAMINATED (fewer than four valid repeats after the one rebuild); WRITE BUDGET EXHAUSTED (only if the human lead declines more after a PAUSE). Scientific: PREREQUISITES NOT MET; NO MATCHING POINT AT EQUAL BYTES. Unreadable wear counters are not on this list (EC3).

## 10. Cost and seeds

**Hours (estimates from the reviewer's descriptive timings; replaced by M).** R0 0.2; R1 0.5 to 1; C 0.5; M and K 1 to 1.5 together; E1 0.3 to 1 (generation and a 16 GiB uncached write); P 0.5 to 1 (about 46,000 exact searches, batched, threads allowed, nothing timed); E2 about 1 (per block: roughly 46,000 single-page requests and 2,800 sweep requests, under a minute of device time, plus X-RES's exact searches; then S-FLAT, at most about 7 minutes), plus quiet waiting, which is not charged; analysis 0.2. **Total about 4 to 6.5 charged hours.** The cap is set before K by the rule; until then the provisional figure is 10 hours. Bytes read in E2 are about 60 GB, almost all of it S-FLAT's ten scans; reads are not charged to the write budget.

**Seeds** (`docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md`, revision 3, section 4.2 row P10-I-S5). A gate re-runs the registry checker before the freeze.

| Role | Registered | R1 | Rehearsal (M and K) |
|---|---|---|---|
| Store contents | 280101 (280102, 280103 unused: one store size) | 289001 | 289201 |
| Query workload, one per repeat | 280001–280005 (280006–280010 unused: one pattern) | 289011 (page offsets); 289013 (positive control); 289012 unused | 289211; 289212 unused |
| Arm order, one per repeat | 280201–280205 | 289021 | 289221 |
| ANN index build | 280301–280303 **unused**: the IVF's centroids are the branch means, with no random build | 289031 unused | 289231 unused |

**Roles the registry lacks** (proposed values in free ranges of this study's blocks; `PENDING` a registry revision 4 by the auditor before the freeze): SWEEP offsets, one per repeat, 287001–287005 (auxiliary block), rehearsal 289241; stage C calibration, key set 289041 and queries 289042; R1 device-cache test offsets 289051. S-FLAT's queries need no seed: they are the first two candidates of each repeat's KV candidate list that were not accepted for any pass. Initialisation 330501–330599 stays unused (scientific part).

## 11. Open choices, with the lead's recommendation

1. **Entry before qualification (EC1).** Read as granted by the human lead's words in section 2.3. Recommendation: enter; the benchmark no longer depends on which read path survives ADR-0029, because it registers no contest between read paths (the third review's F18).
2. **Write cap 40 GB** (permitted: 250 GB). Recommendation: 40 GB. A store above RAM (for example 2 × 96 GiB, about 206 GB) is within the permission and is **not** recommended: the reviewer's figures show it is not exact.
3. **EC3 restated** so that unreadable wear counters do not block the part. The reviewer called this the human lead's decision; the lead reads the write permission as covering it and asks the human lead to confirm.
4. **One file and no second layout; no unbalanced IVF; no contest label** (section 5.2). Recommendation: as drafted. The alternative, a k-means IVF over 89 million keys in its own 16 GiB file, costs about 17 GB more writes and one to two hours, and answers a question about a balancing step on invented data.
5. **S-FLAT: ten queries.** Alternative: none on device (bytes are by construction). Recommendation: ten, for the NONE rung's measured time.
6. **σ fitted so that two branches pass the floor** (section 4.4). Alternative: a fixed σ. Recommendation: the rule, disclosed.
7. **m_t rule; label of EQ-B on three pages; R_min 0.90; 4 of 5.** As drafted.
8. **The scientific part stays NOT EVALUABLE on record** (section 3.2). Recommended; nothing here changes it.
9. **Decision 1 and Decision 2**, and whether they are taken under the general delegation quoted in section 2.3. The drafter stops here.

## 12. Engineering pattern (ADR-0029 sections 13 and 18 to 20)

- **Order:** independent review of this draft → Decision 1 → implementation in new files (`studies/p10is5/`, `configs/p10is5_ssd.toml`, `tests/test_p10is5_*.py`) with an independent implementation audit → R0, R1, C → candidate `plan.json` → measuring rehearsal → caps → counting rehearsal against the candidate plan itself, whose SHA-256 goes into its record → freeze, which refuses any other hash → Decision 2 → E1 → P → E2 → independent recomputation → outcome record → deletion.
- **Frozen inputs, with this ADR outside them:** `studies/p10is5/**`; the config, which holds every threshold; launch scripts; `freeze/plan.json` (store geometry, seeds, σ, m_t, quiet figures, store path, every pass); stage caps; R1's and K's records. Identity by SHA-256 of each file. The freeze stores this ADR's hash for provenance only. A test asserts that every threshold here equals the config's value. A difference is PAUSED — IDENTITY.
- **The store directory is outside every worktree.** Nothing is written or committed in the frozen worktree between a Decision 2 and the end of that stage's report; status goes to the lead in chat or to another branch.
- **Analysis tests:** the analysis and report are tested on a synthetic registry with known answers for every row of section 5.4, every NOT EVALUABLE reason and ENGINEERING STOP.
- **Platform of record:** the research machine, macOS arm64, the project `.venv` (CPython 3.12.14, torch 2.8.0), one thread. The reviewer's probes ran under another interpreter; R0 repeats them. Checks run locally. Delegated work records the model that ran it from session metadata; implementer and auditor in separate contexts.

## 13. Rulings for the implementer

1. **Geometry, generator, layout, arms, request order:** exactly sections 4.1 to 4.3. Float32 little-endian. No numpy (it is not in the lock); torch and the standard library only.
2. **Constants:** `F_RDAHEAD` 45, `F_NOCACHE` 48, `F_FULLFSYNC` 51; `proc_pid_rusage(pid, 2, …)` with the structure of `ssd_probe_0028.py` (`ri_diskio_bytesread`, `ri_diskio_byteswritten`, `ri_phys_footprint`). A non-zero return is an environment error.
3. **Scores:** cosine with unit-normalised rows, divided by 0.2; S-TREE's prior is the log-softmax over all B route scores; selection by the repository's `stable_top` rule (ties to the lower id). IVF-p ranks lists by the same route scores.
4. **One process per pass.** It holds its arm's arrays only; X-RES regenerates the keys before its first snapshot. Imports and warm-up (one untimed query against memory) come first.
5. **Timing:** `perf_counter_ns` per query and per request; snapshots outside; the replay for t_cpu follows the device pass in the same process, on the bytes read, with the same code path and no `pread`.
6. **Statistics:** medians and percentiles by the nearest-rank rule on the sorted values; CV with the sample standard deviation (n − 1).
7. **Plan builder:** passes in the order repeat 1 to 5, then within a repeat SWEEP, S-TREE, IVF-1, IVF-2, IVF-4, IVF-8, KV, X-RES (this is the acceptance order, not the run order); a candidate is accepted if all its pages are unused. S-FLAT's queries are exempt from disjointness.
8. **Build:** chunks of 1 GiB (the last one shorter), each written, then verified by an uncached read against the regenerated SHA-256 (this read is charged to no budget and happens before any registered pass; it leaves nothing cached, probes 1B2 and 3). Resume at the first unverified chunk; rewritten bytes are charged.
9. **Settling:** E2 starts no sooner than 10 minutes after E1's last write and after a quiet check.
10. **Order of checks at the start of every stage:** identity, EC3 record, free space, hygiene, memory guard, quiet check (if the stage needs it), write-budget projection.
11. **Outcomes:** exactly the names in sections 1, 7 and 9. Nothing else is printed as an outcome. Wear counters print `NOT READABLE`.
12. **Records:** every pass writes its requests, per-request and per-query latencies, counter snapshots (process, volume, driver), page hashes and quiet readings, outside the worktree's frozen files, under a git-ignored run directory; a guard asserts that it is ignored.
13. **Anything not ruled here is a question to the lead before code is written, not a choice.**

## 14. What the engineering result can and cannot say

**It can say**, for one Apple SSD (AP2048Z) behind APFS with FileVault, at queue depth 1, with 16 KiB uncached requests, on a 16 GiB synthetic store that fits in RAM and is only made to behave as if it did not: whether the host-side counter equals the layout's arithmetic; what one page and one contiguous run of pages cost in time, with their distributions; whether a read path's time is its computing time plus its pages' cost; and how time and bytes change over three resident budgets at a recall of at least 0.90 on an invented workload.

**It cannot say anything about:**

- ArborLM's trained memory, its learned routing, its prior, its capacity, its quality or its usefulness. **The S-TREE arm is T-OQ's arithmetic applied to random vectors; it is not a neural memory and its figures are not a neural-memory result.** No sentence about the project's objective, about hypotheses H3 to H5, or about the scientific line may cite an engineering label.
- Whether the tree or an index is better: that comparison is fixed by the layout here (section 5.2).
- Whether storage is needed (the store fits in RAM); other drives, filesystems, queue depths or warm caches; NAND traffic, wear, endurance, sustained writes or updates.
- Published ANN systems. The index is a hand-written IVF-flat; SPANN-like systems are themselves centroids in RAM with posting lists on SSD, and graph indexes hide latency with parallel I/O that queue depth 1 forbids. No number from them is used.
- From a scientific label under `RAM RESTRICTED BY CONSTRUCTION`: that storage was needed. P7 and P8 outcomes are unchanged whatever S5 finds.

## 15. Review record

Independent review by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0027_ADR-0028.md`, verdict NOT READY (1 blocking, 14 required, 6 advisory). This revision is by the lead (Claude Fable 5.2). It has not been re-reviewed. Neither is Astra review or human approval. Device rates and write totals quoted from the review are the reviewer's. The drafter ran no measurement; at first drafting it read RAM size, disk size, free space and the presence of tools, read-only (`sysctl`, `df`, `which`).

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| B-B1 result parity and RAM parity | BLOCKING | FIXED | §1, §2 "P7-A's lesson", §4, §5 matching conditions |
| B-R1 quantifiers, margins, MEASURES DISAGREE | REQUIRED | FIXED | §5 label table |
| B-R2 Q1 and Q2 met by different systems | REQUIRED | FIXED: one system required; no sibling label exists for Q2, stated | §3.2 |
| B-R3 utilisation floor timing | REQUIRED | FIXED: measure and floor fixed now | §3.2 Q2-U |
| B-R4 no means of reaching a cold state | REQUIRED | FIXED as rehearsal checks with NOT EVALUABLE | §4, §6, §7 |
| B-R5 what the counters measure | REQUIRED | FIXED | §5 measures, §7 |
| B-R6 what is charged to the write cap | REQUIRED | FIXED | §6 |
| B-R7 backup, snapshots, indexing | REQUIRED | FIXED | §6 "Store hygiene" |
| B-R8 device cache, repeats, replayed traces | REQUIRED | FIXED | §4, §5, §7 |
| B-R9 health counters unreadable | REQUIRED | FIXED | §3.1 EC3, §11 item 3 |
| B-R10 rehearsal writes before entry | REQUIRED | FIXED (E0) | §3.1, §8 |
| B-R11 scientific part cannot answer as capped | REQUIRED | FIXED: stated; RAM restriction defined | §3.2, §11 item 5 |
| B-R12 scientific label not computable | REQUIRED | FIXED (structure; margins later) | §5 |
| B-R13 read point of the accuracies | REQUIRED | FIXED | §2, §11 item 1 |
| B-R14 PAUSED; unclassified limits | REQUIRED | FIXED | §8, §9 |
| B-A1 quiet disk condition, power, thermal | ADVISORY | FIXED | §7, §8 |
| B-A2 P10-S0 row | ADVISORY | FIXED (record re-read) | §2 |
| B-A3 orders of magnitude | ADVISORY | FIXED | §2 |
| B-A4 "flat read-path throughput" | ADVISORY | FIXED | §11 item 1 |
| B-A5 endurance context | ADVISORY | FIXED (quoted as the reviewer's observation) | §6 |
| B-A6 why cold is primary | ADVISORY | FIXED | §1 |
| B.4 further NOT EVALUABLE cases; no cross-citation | — | FIXED | §9, §1 |

**Confirmation review** by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW2_ADR-0027_ADR-0028.md` (NOT READY: 0 blocking, 5 required, 5 advisory) and the stale reference listed in `REVIEW2_ADR-0024_ADR-0029.md` section E. Revision 3 is by the lead (Claude Fable 5.2), against the sibling texts on disk at the time. It has not been re-reviewed. Rows above keep their first-review dispositions; where the confirmation review reopened one, the row below governs.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| S5-N1 / Y1 Q1 named wrong steps and states | REQUIRED | FIXED: steps 3 to 6, Line Q HOLDS, tested cell types | §3.2 Q1 |
| S5-N2 / Y2, Y3 Q2 and lane L | REQUIRED | FIXED, against the third draft of ADR-0024, not the review's replacement text: lane L is unspecified and not approved, so there is no approved source; two reasons stated; the 3.15 MB figure shown | §2, §3.2, §11 item 5 |
| S5-N3 utilisation measure | REQUIRED | FIXED: all 8 selections, one query per fact, Panel A; floor relative to random placement; PENDING LEAD REVIEW | §3.2 Q2-U |
| S5-N4 S-FLAT is exact; the resident budget decides | REQUIRED | FIXED: two budgets by formula; ANN is the deciding baseline; comparisons with S-FLAT marked BY CONSTRUCTION; recall gap printed | §5 |
| S5-N5 / Y5 seeds | REQUIRED | FIXED: registry values; roles and counts proposed | §10 |
| S5-N6 unnamed outcomes | ADVISORY | FIXED | §5, §7, §9 |
| S5-N7 clause names clash with stage names | ADVISORY | FIXED (EC1 to EC4) | §3.1 |
| S5-N8 relative margins; denominator; meaning of BASELINE NOT WORSE | ADVISORY | FIXED | §5 |
| S5-N9 device facts not attributed; snapshot caveat | ADVISORY | FIXED: each fact carries who observed it and when | §2, §3.1, §6, §15 |
| S5-N10 / Y4 pointer to R-DIAGNOSIS | ADVISORY | FIXED (ADR-0029) | §11 item 1 |
| Quiet-load ceiling (raised for ADR-0027 as S4-N5) | — | FIXED here as well: 1.0 | §8, §9 |

Section numbers in the two tables above are draft 3's. In draft 4 the engineering content of its sections 4 to 8, 10, 12 and 13 is replaced; section 3.2 and the scientific label rule are unchanged.

**Third review** by the `arbor-auditor` subagent (Claude Opus 5.5, as that review reports): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW3_ADR-0028.md`, copied word for word from the reviewer's working file; engineering part only; verdict NOT READY (3 blocking, 10 required, 5 advisory). It probed this machine on 2026-11-18 (56 MiB written and deleted). Draft 4 is by the lead (an `arbor-lead` subagent, Claude Fable 5.2). **Draft 4 has not been reviewed.** The drafter ran no probe and no code; it ran read-only commands, `ruff` and `git`.

| Finding | Disposition | Where |
|---|---|---|
| F1 exact counter rule in place of the ratios | FIXED: exactness; STORE PAGES CACHED, COUNTER CONTAMINATED | §7; §5.4 EQ-A |
| F2 uncached build and reads; nothing may warm the store | FIXED: read discipline; reference data regenerated, never read cached | §7 |
| F3 the benchmark undefined | FIXED: store, layout, arms, workload, budgets, page, queries per pass | §4 |
| F4 margins | FIXED: none on bytes; m_t = max(0.10, 2 × CV_R) with a 0.30 ceiling, the quantity named | §5.4 |
| F5 bytes computable before any read; same leaves give the tree no advantage | ACCEPTED IN FULL: the contest is withdrawn; a prediction is registered; the device answers EQ-A to EQ-C | §1, §5.2, §5.3, §5.4 |
| F6 EC3 and unreadable health counters | FIXED as the brief directs: printed NOT READABLE, not a NOT EVALUABLE reason; put to the human lead for confirmation | §3.1, §9, §11 item 3 |
| F7 counter API named | FIXED | §5.1, §13 item 2 |
| F8 engineering stops; order of NOT EVALUABLE reasons | FIXED | §9 |
| F9 in-project IVF; no package outside the lock; weak-evidence asymmetry; SPANN note | FIXED: IVF-flat in the project. The asymmetry no longer applies, because no label compares the tree with the index; the SPANN note is kept | §4.3, §5.2, §14 |
| F10 S-FLAT's cost | FIXED: reference exact in RAM; ten on-device queries; hours stated | §4.4, §10 |
| F11 rehearsal order, caps, frozen inputs | FIXED: ADR-0029's order and rule; ADR outside the frozen set; store outside worktrees | §8, §12 |
| F12 memory guard; the RAM arm | FIXED: 12 GiB guard; no arm loads the store; parity against regenerated pages | §9, §7 item 6 |
| F13 KEYS RESIDENT decided by construction | FIXED: one arm, X-RES, at that rung | §4.2, §5.2 item 5 |
| F14 bit identity | FIXED | §7 item 6 |
| F15 symmetric recall gap | SUPERSEDED: no label compares two arms' recall; every arm's recall is printed | §4.4, §5.5 |
| F16 seeds cited | FIXED; five roles the registry lacks are listed | §10 |
| F17 device facts updated and attributed | FIXED | header, §6, §12 |
| F18 reason for holding E1 and E2 | FIXED: no hold; no read path is contested | §11 item 1 |
| E-1 | SUPERSEDED by the human lead's words (§2.3) and this revision | §2.3, §3.1 |
| E-2, E-3, E-4, E-5, E-7 | APPLIED (reworded into the new sections) | §7, §5.1, §9, §12 |
| E-6 | APPLIED: platform of record, idle time, no other stage, power, idle window. The idle window is 10 minutes as proposed | §7, §8 |
| Section D, guesses 1 to 24 | RULED. Departures from the reviewer's recommendation: one file, not one per arm (3); no padding, because a branch is exactly 3 pages (4); one pattern (5); operating point fixed in stage P (20); S-FLAT 2 per repeat, not 10 (11) | §4, §13 |
| "Smallest study worth running" | TAKEN, made smaller: one layout, 19.5 GB planned, 40 GB cap | §6, §8 |

**Not answered by this draft:** whether `.noindex` keeps Spotlight out, whether `purge` needs administrator access, whether the drive has a read cache, and what the quiet machine's idle I/O is. Each is a check in R0 or R1 and none could be settled without a probe, which the drafter was not permitted to run.

`Astra review: NOT_PERFORMED`.
