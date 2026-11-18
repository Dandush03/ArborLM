# ADR-0028 — P10-I-S5: physical SSD-backed memory (conditional specification)

**Status: DRAFT 5 — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- Date: 2026-11-18 UTC. Revision 5, after the fourth independent review (section 15) and the lead's scope decision (section 2.4). Drafted by the lead (an `arbor-lead` subagent, Claude Fable 5.2, as the session reports it) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8. The drafter ran no probe, wrote no store and executed no code. Every device figure below is **the reviewer's observation of 2026-11-18**, made on a machine that was not quiet; the third review's probes ran under an interpreter that is not the platform of record.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification with two parts. The scientific part is unchanged since draft 3 and cannot be evaluated (section 3.2). The engineering part is reduced in this revision to **a study of the device's cost model**: what uncached reads cost on the human lead's SSD as a function of request size and of the number of requests issued at once. Section 3.2, the scientific label rule (section 5.6) and the earlier review tables are kept word for word.
- No hardware purchase is proposed. The only device is the internal SSD of the human lead's working computer. Nothing here needs administrator access, a tool install, a download or a package outside the lock.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Two questions, two verdicts, never combined

| Verdict line | Question | Evidence it may use |
|---|---|---|
| **ENGINEERING SSD PERFORMANCE** | On this device, under a written uncached read discipline: do the bytes read equal the bytes predicted from the layout, what does one page cost, what does a page cost inside a larger contiguous request, and how do latency and pages per second change with the number of requests issued at once? (Sections 4 and 5.) | A synthetic file; no memory, no keys, no queries |
| **SCIENTIFIC NEURAL-MEMORY ADVANTAGE** | Does one trained neural memory, addressed without an oracle, give better task quality at equal measured block-device traffic than fair storage baselines, at a scale where storage is really needed? | Only a qualified, trained memory (section 3.2) |

A synthetic benchmark tests real storage behaviour. It is **not** evidence of useful neural-memory scaling, whatever it shows. Neither line is summarised by the other. No report sentence joins them, and no paragraph about one line cites the other's label.

| Line | Registered values |
|---|---|
| Engineering, three lines, each read alone (section 5.3) | **EQ-A** BYTES CONFIRMED EXACTLY / BYTES NOT CONFIRMED (reason). **EQ-B** CONTIGUOUS REQUEST CHEAPER PER PAGE / COST PROPORTIONAL TO PAGES / CONTIGUOUS REQUEST DEARER PER PAGE / NOT SEPARATED AT MARGIN. **EQ-D** COST TABLE REGISTERED (a measured table; descriptive; no pass or fail). Any of them: ENGINEERING NOT EVALUABLE (reason) |
| Scientific | ADVANTAGE SUPPORTED AT TESTED SCALE / NO ADVANTAGE OVER STORAGE BASELINES / INCONCLUSIVE / SCIENTIFIC NOT EVALUABLE (reason) |

No engineering value is "positive" or "negative" for ArborLM. Draft 3's contest labels were withdrawn in draft 4. Draft 4's EQ-C (does a read path's time equal its computing time plus its pages' cost) is withdrawn here, with its read-path arms (section 2.4).

**Why cold and uncached is the registered regime.** It is the regime in which storage traffic is actually paid, and the only one the counter can verify exactly (section 7). A deployed system would also cache hot pages; that is not measured here.

## 2. Background and approval context

### 2.1 What the records already hold

| Finding | Record |
|---|---|
| P7-A: CONCENTRATION-ONLY for both tree kinds: the trees' lower simulated page reads "come from using fewer rows"; "No NVMe experiment on these checkpoints is proposed" | `docs/decisions/ADR-0013-p7a-storage-page-locality.md`, outcome record |
| P7-B: WITHIN 10% OF FLAT CO-ACCESS on both streams for both tree kinds, REPLICATED; decision class N | `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` section 16 |
| P8: INCOMPLETE; no case LOCALITY-POSITIVE; every locality term acted as a concentration term | `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md`; `results/p8-2026-11-14/SUMMARY.md` |
| P10-S1 "Estimated storage traffic": arithmetic and simulation, no device | `results/p10s1-run-2026-11-17/RESULTS.md` |
| P10-S1 supplementary throughput, in RAM, descriptive, not the registered stage: T-OQ 10,106 / 10,211 / 10,132 queries/s at batch 1 at 1,024 / 4,096 / 16,384 slots (about 99 µs per query) | `results/p10s1-run-2026-11-17/OUTCOME.md` section 3; `supplement/throughput_supplement.json` |

Everything about storage in P7, P8 and P10-S1 is simulated or arithmetic. No ArborLM record contains a registered measurement on a device.

**P7-A's lesson, carried into the rules.** A read path that examines fewer candidates reads fewer pages by construction, whether or not it finds the right rows. Under the read discipline of section 7 that holds exactly: bytes are a function of the layout. So bytes are predicted before any read and only confirmed by the device (EQ-A), and what is measured is time.

**The scale gap** (unchanged). A slot is 64 key bytes plus 128 value bytes: 192 bytes. The largest cell at which learned addressing is qualified has 16,384 slots: 16,384 × 192 = 3,145,728 bytes, against 51,539,607,552 bytes of RAM, a factor of 16,384. This gap, not the device, stands between the project and the scientific verdict.

### 2.2 What the trained tree reads (from the code; used only for the arithmetic of section 5.5)

`studies/p9/model.py` `_top_tree`, `studies/p10s1/core.py` (`BRANCH_SIZE = 256`, two branches visited): T-OQ scores one router row per branch for **every** branch, in RAM, visits the two best branches, scores their 512 keys with a branch prior and reads the top 8. A branch of 256 slots of 192 bytes is 49,152 bytes, **exactly 3 pages of 16,384 bytes**. So a T-OQ-shaped query touches at most 2 branches × 3 pages.

### 2.3 The human lead's words on this study

They are recorded verbatim, in order and with the lead's reading, in `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` section 7, committed as `fa60cc4` (on the lead's branch; not yet merged into this branch). **That record governs; this section only quotes it.** The four sentences that bear on this study:

> and you have my permission to auto approve everything until you complete P10-I

> we could do a better test in my ssd not sure why not

> ok, but you are allowed to download up to 75gb of data needed for the ssd test if needed. im going to sleep, I'll let you drive the simulations

> if you need 200gb or 250gb for the test im also ok with that

**How the record reads them, and no further:** the engineering part may be entered before a neural memory is qualified at scale; drive writes up to 250 GB, kept to the minimum a proper test needs (this draft caps them at 10 GB, section 6); downloads up to 75 GB if needed (none is expected: the file is synthetic); nothing needing administrator access. The words do not say that the scientific part may be entered, that a threshold may move, or that any result is expected. EC1 and EC2 are met only from that record (the fourth review's X-1). Under the record's last rule, a choice that a reviewer advised should go to the human lead and that the lead takes under the delegation is reported to him as the first item of this study's record, so that he can overrule it before the run decision. There are two: the restated EC3 (section 3.1) and the scope decision (section 2.4).

### 2.4 The lead's scope decision (2026-11-18), with its reasons

The fourth review offered a choice: keep draft 4's study (a 16 GiB store, seven read-path arms, 19.5 GB written, 4 to 6.5 hours) with twelve edits, or run a smaller study of the device alone. **The lead adopts the smaller study.** Reasons, as the lead gave them:

1. **The tree-versus-index contest is decided by construction for the arms the trained tree allows.** T-OQ's router is one level and is scanned in full, so an index over the same leaves reads the same key pages; the prior cannot raise recall for a fixed candidate set; with keys resident both are one arm (the fourth review's section 2 confirms each step). The regimes in which layouts would really differ are unequal lists, a multi-level router with only its top in RAM, and reuse of hot pages. They belong to the redesign after P10-I, not to a benchmark of today's one-level tree. Unequal lists are, besides, a question that arithmetic in RAM on P10-S1's own keys can answer without a device.
2. **Draft 4's EQ-C is nearly insensitive on this machine.** The reviewer timed routing at about 0.9 to 1.1 ms per query in RAM at 349,525 branches against about 0.3 to 0.8 ms of I/O; a 30 % error in page cost would move the gap by 6 to 13 %, under the margin. COST MODEL HOLDS would have been reached almost by construction.
3. **What the human lead can use for a redesign is the device's cost model, and its largest missing piece is parallel reads**, which is how SSD-backed indexes keep their speed. With a table of cost by request size and by requests issued at once, the latency of any future layout can be predicted by arithmetic.

Consequences: the read paths of the trained tree are **no longer arms**; there is no store of keys and values, no query, no recall, no index, no resident-budget ladder and no workload calibration. What a T-OQ-shaped query would cost under the measured table is printed as arithmetic only (section 5.5).

## 3. Entry criteria

### 3.1 Engineering part

- **EC1, entry before qualification.** Met only from the delegation record, section 7 (`fa60cc4`).
- **EC2, write budget.** Section 6 (10 GB hard cap, inside the 250 GB of the record).
- **EC3, device record.** Before and after every stage that writes, the study records SMART status (`diskutil info disk0`; it must read `Verified`), free space (`df -k`) and the disk0 driver's bytes written since boot (`ioreg -r -c IOBlockStorageDriver -l -w0`). Lifetime bytes written, percentage used and temperature cannot be read without administrator access or a tool install (the reviewer's observation); they are printed **NOT READABLE** in every record and report, and that does **not** make the part NOT EVALUABLE. Wear is accounted in the study's own bytes written. A status other than `Verified` is PAUSED and goes to the human lead. The fourth review judged this sound; it is reported to the human lead as section 2.3 says.
- **EC4, method.** Every check of section 7 passed in R1 under the platform of record.
- **Decisions.** Decision 1 covers implementation, R0, R1 and the two rehearsals (at most 1.21 GB written). Decision 2, taken on the rehearsal records and an independent implementation audit, covers E1, P and E2.

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

Section 3.2 is draft 3's text, unchanged. Its Q4 points to "sections 4, 5 and 7" and to "the resident budget of section 5". Draft 5's engineering part defines no arm, baseline or resident budget, so the scientific part could not be entered without a revision that defines them again; that changes nothing in its present value.

## 4. The benchmark: file, tiling, cells

### 4.1 The file

| Quantity | Value | Why |
|---|---|---|
| Page | 16,384 B | `hw.pagesize` on this machine. The reviewer's probe 1E: a 4 KiB uncached request reads 16 KiB. Every request is whole pages at page offsets |
| Tile | 64 pages = 1,048,576 B (1 MiB) | The largest request size; the unit of the no-page-twice rule |
| File | 4,096 tiles = 262,144 pages = **4,294,967,296 B (4 GiB)** | Sized from the sweep's needs (section 4.3): 3,996 tiles used, 100 never read |
| Rehearsal file | 1,024 tiles = 1,073,741,824 B (1 GiB) | Holds R1, M and K (section 8) |
| Contents | Tile t is 1,048,576 bytes of `torch.randint(0, 256, …, dtype=torch.uint8)` from a generator whose state is the first 8 bytes of SHA-256(`p10is5|store|<seed>|<t>`) modulo 2⁶³ | Incompressible; any page can be regenerated from the seed without reading the file |

**Why the file need not exceed RAM.** The page cache is excluded per read by the discipline of section 7, and the per-process counter verifies that exactly on every pass (the reviewer's probes 1B, 1B2, 3). A size-based cold state is not valid here: reclaimable file-backed pages (about 14 GB at the third review) mean even a file twice the size of RAM would be partly cached and never exact. The 250 GB permission would allow such a file; the reviewer's figures show it would buy nothing exact, so it is not used. The cost of this choice is stated in section 14.

**Why 4 GiB and not 16.** No page is read twice (section 4.3), so the file need only hold the pages the sweep reads once; a working set "far beyond any device cache" is not needed when nothing is re-read. The reviewer's candidate was "one roughly 4 GiB file".

### 4.2 Cells

A **cell** is one request size s at one depth k. A **pass** is one cell in one repeat, run in its own process.

- **Request sizes s (pages):** 1, 3, 8, 64. Three pages is one T-OQ branch. Sixty-four pages is 1 MiB: at a 16 KiB page the "64 pages" and "1 MiB" of the fourth review's X-7 are one size.
- **Depths k:** 1, 2, 4, 8, 16, 32. Depth k means k threads, each issuing one `os.pread` at a time and the next as soon as it returns (a closed loop). It is the number of requests the host has outstanding. What the drive's own queue holds cannot be read from software and is not claimed.
- **Requests per pass n(s):** 400, 400, 160, 64 for s = 1, 3, 8, 64. Reason: at least two full rounds of 32 threads at the largest size, and 400 samples per repeat (2,000 over five repeats) for the percentiles of the small sizes that a layout would use most.
- **24 cells × 5 repeats = 120 passes**, 30,720 requests and 209,280 pages (3.43 GB read). One spare repeat is planned (section 8).

**Threads and the interpreter lock.** `os.pread` releases CPython's global interpreter lock for the duration of the system call, so k threads can have k reads outstanding. The lock is held for the few interpreter operations around each call (the timer, the loop). At high k and short reads these serialise and can add to the latency seen. So every figure is the **host-visible cost through this harness**, not the drive's service time, and the harness's own cost is measured and printed beside it (section 5.4). No package outside the lock and no native code is used.

### 4.3 Tiling: no page is read twice, by construction (the fourth review's N1)

Draft 4 accepted requests one by one against a list of used pages and, by the reviewer's simulation, ran out of pages by the second or third repeat. Draft 5 has no acceptance loop.

- One seeded permutation of the 4,096 tiles assigns tiles to (repeat, k, s). Repeats are 1 to 5 and the spare, 6.
- A tile given to size s is cut into ⌊64/s⌋ aligned, non-overlapping segments from its start: 64, 21, 8 and 1 segments for s = 1, 3, 8, 64.
- Tiles per pass: 7, 20, 20, 64 (448, 420, 160 and 64 segments; the first n(s) in a seeded order are used). That is 111 tiles per (repeat, k); × 6 depths × 6 repeats = **3,996 of 4,096**.
- Because the assignment is a permutation of the whole file, every cell's requests are spread over the whole file (the fourth review's X-9: no cell samples only a region written early or late).
- Within a pass the requests are issued in a seeded order and dealt to the k threads in turn.

Exhaustion cannot occur: the counts above are fixed arithmetic. Each tile belongs to one pass and each page to at most one request, so in E2 no page of the file is read twice.

## 5. Measures, the prediction, and the registered questions

### 5.1 Measures

- **Bytes read per pass**: `ri_diskio_bytesread` of `proc_pid_rusage(getpid(), RUSAGE_INFO_V2)`, read through `ctypes` on `/usr/lib/libSystem.B.dylib`, as the reviewer's probe did (`ssd_probe_0028.py`, `proc_io`), in the one process that issues every read of the pass; all its threads are in that process. Not `getrusage` (its block counts stayed 0 in the probes) and not `psutil` (no I/O counters on macOS). Cross-checks, printed only: the APFS volume's "Bytes read from block device" and the disk0 driver's `Bytes (Read)`, which are system-wide. All are host-side, block-layer figures. They are never called NAND or media traffic.
- **Latency per request**: `time.perf_counter_ns` immediately before and after each `os.pread`, in the issuing thread.
- **Pages per second of a pass**: pages read over the wall time from the release of the start barrier to the last thread's last return.
- Counter snapshots and all `ioreg` calls are outside the timed region.

### 5.2 The registered prediction

The plan defines every pass (section 12). Stage P, after the freeze and before E2, expands each pass into its ordered list of requests (offset, length, thread) and its predicted bytes, 16,384 × pages: 6,553,600 / 19,660,800 / 20,971,520 / 67,108,864 bytes for s = 1, 3, 8, 64. It also writes the expected SHA-256 of every page. The prediction record's SHA-256 is recorded and E2 refuses to start on any other. Each pass derives its requests again from the plan and asserts they equal the record's before issuing any; a difference is ENGINEERING STOP (PREDICTION MISMATCH).

### 5.3 The registered questions

Five repeats. One repeat (block) is one pass of each of the 24 cells, in the order given by that repeat's order seed.

**EQ-A. Do the bytes read equal the layout's prediction exactly?** *BYTES CONFIRMED EXACTLY* only if **every pass of every repeat attempted**, including any repeat run again and the spare if used, has counter bytes equal to its predicted bytes (the counter rule of section 7). Otherwise *BYTES NOT CONFIRMED* with the reason of the first failing pass, and every failing pass is printed beside its second attempt. There is one rule and no "4 of 5": a label that says "exactly" cannot sit over a failed pass (the fourth review's N5). EQ-A uses every pass, whether or not its block was quiet.

**EQ-B. What does one uncached page cost at depth 1, and what does a page cost inside a contiguous request?** c_r(s) is the median latency of the n(s) requests of size s at depth 1 in repeat r. Registered as measured: c_r(1) with its p90, p99 and maximum, per repeat and pooled; and ρ_r(s) = c_r(s) / (s × c_r(1)) for s = 3, 8, 64. The label is on ρ_r(3), because three pages is one branch and that is the figure a layout decision needs:

| Label | Rule |
|---|---|
| CONTIGUOUS REQUEST CHEAPER PER PAGE | ρ_r(3) ≤ 1 − m_t in at least 4 of 5 repeats |
| CONTIGUOUS REQUEST DEARER PER PAGE | ρ_r(3) ≥ 1 + m_t in at least 4 of 5 |
| COST PROPORTIONAL TO PAGES | \|ρ_r(3) − 1\| < m_t in at least 4 of 5 |
| NOT SEPARATED AT MARGIN | otherwise |

The first label is the expected one (a command's fixed latency usually exceeds the transfer time of two more pages; the fourth review calls it near-certain). EQ-B is therefore mostly a confirmation with a measured size. It is registered because the figure, not the label, is what the redesign needs.

**EQ-D. How do latency and pages per second change with depth and request size?** A measured table of the 24 cells. For each cell and repeat: the median, p90, p99 and maximum request latency, and pages per second. Across repeats: the median of the per-repeat medians, their range and their coefficient of variation. **This line is descriptive.** No ordering, speed-up or monotonicity is registered as a hypothesis: the drafter can justify no threshold for one before observing the device, and a rule written without one would be a guess dressed as a test. What is registered is the table's definition, its dispersion figures and its validity rule: a cell is reported only from valid repeats (section 5.4), needs at least 4 of 5, and is otherwise printed CELL NOT EVALUABLE; the line's value is COST TABLE REGISTERED when at least 20 of the 24 cells are reported, and ENGINEERING NOT EVALUABLE (reason) otherwise.

### 5.4 Margin, validity and the harness figure

- **The margin m_t (EQ-B only), from the measuring rehearsal, fixed before the candidate plan exists.** CV_R is the larger of the repeat-to-repeat coefficients of variation (sample standard deviation over mean of the five per-repeat medians) of c(1) and c(3) at depth 1 in stage M. m_t = max(0.10, 2 × CV_R). Reasons: a difference under a tenth is not an engineering finding on a working computer; twice the spread keeps noise alone from crossing. If m_t would exceed 0.30, EQ-B's label is registered as ENGINEERING NOT EVALUABLE (TIMING SPREAD) in the config, before any registered read, and its figures are printed descriptively. There is no margin on EQ-A (the quantity is deterministic) and none on EQ-D (no comparison is registered).
- **Valid repeat (EQ-B, EQ-D).** The block was quiet at its start and at its end (section 8) and every one of its passes met the counter rule. The denominator stays 5. The first invalid block is replaced once by the spare repeat, on tiles no pass has read; a second invalid block stays invalid.
- **Harness figure.** In R1 and at the start of E2, the same threaded loop runs at each depth on cached pages of R1's own control file (never on the store), 400 single-page requests. Its median, h(k), is the cost of the loop itself. It is printed beside every cell; a cell whose depth has h(k) above a quarter of the cell's median latency is tagged HARNESS-LIMITED. The tag is descriptive, changes no label and removes no cell.

### 5.5 Printed as arithmetic only

**ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH.** With L(k, s) the pooled median request latency of cell (k, s) from EQ-D's table, the report prints, for each depth k, what the page reads of one T-OQ-shaped query (2 branches × 3 pages; section 2.2) would cost under the table:

- as two 3-page requests: ⌈2 / min(k, 2)⌉ × L(min(k, 2), 3);
- as six 1-page requests: ⌈6 / k′⌉ × L(k′, 1), with k′ the largest depth of the grid not above min(k, 6), that is 1, 2, 4, 4, 4, 4.

It excludes the routing computation in RAM (which the fourth review timed at about 1 ms at 349,525 branches, descriptively, and which no stage here measures), assumes the pages are not cached, and assumes rounds add. No query is issued, no branch exists in the file, and nothing in these lines is a measurement of ArborLM's tree or of any memory. The lines carry that heading wherever they are printed.

### 5.6 Scientific label (kept from draft 3, word for word)

**Scientific label** (structure fixed now; read only if Q1 to Q4 hold). The memory is read at its registered operating point; its mean bytes per query there is b0. Each baseline (ANN, S-FLAT, and KV) is swept over a registered list of candidate budgets and read at the smallest budget whose bytes per query are at least b0, so a baseline never has less traffic than the memory. No such point: SCIENTIFIC NOT EVALUABLE (NO MATCHING POINT AT EQUAL BYTES). KV is addressed by the task's own surface key, never by an oracle slot address; if KV's quality is within the margin of the memory's, every label carries `LOOKUP SUFFICIENT ON THIS TASK`. Five fresh draws; a replicate favours the memory only if on both panels it is ahead of every baseline by the margin, and favours a baseline if on either panel that baseline is ahead. ADVANTAGE SUPPORTED: at least 4 of 5 favour the memory. NO ADVANTAGE: at least 4 of 5 favour one and the same baseline. INCONCLUSIVE: otherwise. Margins are fixed by the later revision before any such draw.

Rows read, pages simulated, parameters touched and any other logical count are never reported as measured traffic or as efficiency. The predicted bytes of section 5.2 are a prediction; only counter bytes are called measured.

## 6. Storage-write budget, free space, file hygiene

| File | Stage | Bytes | Builds planned |
|---|---|---|---|
| Probe files | R0 | at most 67,108,864 (64 MiB) | 1 |
| Control file (positive control, harness figure) | R1 | 67,108,864 | 1 |
| Rehearsal file (R1, M and K) | R1 | 1,073,741,824 | 1 |
| The file | E1 | 4,294,967,296 | 1 |
| **Planned total** | | **5,502,926,848 B (5.50 GB)** | |
| One rebuild of the file (recovery from pollution, section 7) | | 4,294,967,296 | |
| **Planned plus that rebuild** | | **9,797,894,144 B (9.80 GB)** | |
| **Hard cap, all stages and attempts, failed ones included** | | **10,000,000,000 B (10 GB)** | |

- **Rebuilds** are taken first come within the cap. A rebuild of the rehearsal file uses most of the allowance, and a later pollution of the file is then PAUSED and goes to the human lead. No file is built a third time.
- **Share of the drive**, from the reviewer's figures (drive 2,001,111,162,880 B; mean write rate since boot 5.53 MB/s): the cap is **0.50 %** of one full drive write and about 30 minutes of this machine's ordinary writing; the planned total is 0.27 % and about 17 minutes. The cap is 4 % of the 250 GB the human lead permitted. Endurance is not readable and no figure for it is assumed.
- **What is charged:** the study's own logical bytes written, before each write, and the larger of that and its `ri_diskio_byteswritten` after it (they were equal in the reviewer's probe 1A). The system-wide counter is recorded and not charged. A run stops before any write that would pass the cap: **PAUSED**, resumable. Only the human lead changes the cap, on projection, never on outcome values.
- **Free space:** at least 500 GB at all times (721.3 GB free at the fourth review). Checked before every write stage.
- **Location:** one directory whose name ends in `.noindex`, under the human lead's home directory, outside every git worktree and every synced folder; its path is in the plan.
- **Hygiene, all without administrator access, checked in R0, before E1, before each E2 block and after deletion:**

| Check | Command | If it cannot be made or fails |
|---|---|---|
| Local snapshots | `tmutil listlocalsnapshots /` and `/System/Volumes/Data`; `diskutil apfs listSnapshots disk3s5` | A snapshot present while a file exists: recorded STORE RETAINED BY SNAPSHOT; its removal is the human lead's action. Not a stop for reads |
| Time Machine | `tmutil destinationinfo`; `tmutil isexcluded <dir>`; `tmutil addexclusion <dir>` without `-p` | Recorded. If the exclusion cannot be set without administrator access: EXCLUSION NOT SET |
| Spotlight | `mdutil -s`; `mdfind -onlyin <dir> .` must return nothing | The `.noindex` rule is untested (both reviews). If the directory is indexed: PAUSED before E1. A reader that cached pages is caught by the counter rule in any case |
| Deletion | The file is unlinked, its absence checked, free space and snapshots recorded | STORE RETAINED BY SNAPSHOT if a snapshot holds it |

Any check whose command needs administrator access on the platform of record is printed NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS and the study continues on the counter rule. Files are written once, never rewritten in a loop, persist across a PAUSE and are deleted after the independent recomputation. Update traffic (trained updates in place on SSD) is write-intensive and is **outside** this document.

## 7. The counter rule and the read discipline

**Counter rule (exact).** For every uncached pass, the per-process bytes read between the snapshot before the start barrier is released and the snapshot after the last thread has joined must equal 16,384 × the number of pages requested. Below: **STORE PAGES CACHED**. Above: **COUNTER CONTAMINATED**. Either makes the pass invalid. The rule was chosen after the third review's probes on this machine (ratio 1.000 on probes 1B, 1B2, 3; 0 on cached pages), before any registered observation. With it no pass can benefit from cache hits. The process's bytes written during a read pass must be 0.

**Read discipline.**

1. Files are written only on a descriptor with `F_NOCACHE` 1 (`fcntl` command 48), in 1 MiB `os.pwrite` calls, and closed after `F_FULLFSYNC` (51). A buffered build leaves the file warm (probe 2(i)).
2. Every read of the file or the rehearsal file by any part of the study (passes, checks, hashes, a human) uses `F_NOCACHE` 1 and `F_RDAHEAD` 0 (45) and whole pages at page offsets. `F_NOCACHE` does not bypass pages already cached (probe 1D): one cached read pollutes those pages until evicted. Reference data are regenerated from the seed, not read back; no memory mapping; no `shasum`, `cat` or Finder preview.
3. Cached reads (the positive control, the pollution control, the 4 KiB amplification, the harness figure) run **only on R1's control file**.
4. Every import, allocation and thread start happens before the first snapshot; no file other than the one being read is opened between snapshots; nothing is printed or written between snapshots (output is held in memory).
5. **Recovery from pollution** (a pass below prediction): the pass and its block are invalid; the file is deleted and rebuilt once, charged to the write budget, and the block is run again as the spare on tiles not yet read. A second pollution is PAUSED: a restart, or `purge`, is the human lead's action (no reviewer ran `purge`; that it needs administrator access is untested). EQ-A is BYTES NOT CONFIRMED in either case (section 5.3).
6. **Parity: bit identity.** The bytes of every request are kept in memory during the pass; after the last snapshot, the SHA-256 of every page read must equal the expected hash written by stage P. A mismatch is an ENGINEERING STOP (DATA MISMATCH), not a label.

**R1 must show, under the platform of record:** on the rehearsal file's reserved band (tiles 896 to 1,023), the counter rule on a first and a repeated uncached pass for requests of 1, 3, 8 and 64 pages (1 MiB), at depth 1 and at depth 32 (so that the per-process counter is shown to cover every thread); on the control file, the positive control (a second cached pass counts 0 bytes), the pollution control (probe 1D), the 4 KiB amplification (probe 1E) and the harness figure h(k); descriptively, uncached re-reads back to back at working sets of 32, 64 and 128 MiB; and, over a 10-minute idle window sampled every 10 s, the 1-minute load average and the disk0 driver's read and write bytes and operations. A failed check is ENGINEERING NOT EVALUABLE with the reason: NO PHYSICAL COUNTER, CACHE NOT DEFEATED, POSITIVE CONTROL FAILED.

**What cannot be verified from software:** the drive's internal caches, its own queue and NAND traffic. The no-page-twice tiling and the seeded pass order are the safeguards. Encryption (FileVault), copy-on-write and fragmentation are properties of this device, stay on and are recorded.

## 8. Stages

| Stage | Writes | Machine | Content |
|---|---|---|---|
| R0 device record | ≤ 64 MiB | shared | EC3 record, fingerprint, hygiene checks, the third review's three probes repeated under the platform of record |
| R1 method rehearsal | 1.14 GB | **alone** | Builds the control and rehearsal files; section 7's list; the idle figures |
| M measuring rehearsal | none | **alone** | Every stage end to end on the rehearsal file in the rehearsal geometry: 24 cells × 5 repeats with n(s) = 100, 100, 40, 16 (28 tiles per (repeat, k), 840 of tiles 0 to 895). Measures rates, times and CV_R |
| Config fixed | none | — | m_t (or TIMING SPREAD) and the quiet figures are written into the config from M's and R1's records; the caps are set (charged hours so far + 2 × projected remaining, ADR-0029's rule) |
| Candidate plan | none | shared | `plan.json` written: definitions only (section 12) |
| K counting rehearsal | none | **alone** | The same end-to-end run against the candidate plan file itself, on the rehearsal file with K's own seeds, and the registered geometry's passes enumerated and checked in RAM (tile counts, no page twice). K produces nothing that any frozen file contains |
| Freeze, Decision 2 | none | — | Refuses unless the plan file has the SHA-256 in K's record |
| E1 build | 4.29 GB | not alongside another study's wall-time stage | 1 GiB chunks, each verified; resumable |
| P prediction | none | shared | Section 5.2 |
| E2 read benchmark | none | **alone** | The harness figure, then five blocks, then the spare if needed |
| S scientific comparison | — | **alone** | Not entered (section 3.2) |
| Analysis, report, independent recomputation, deletion | none | shared | The auditor receives the specification, code and records, not the lead's conclusions |

**R1, M, K, E2 and S run alone on a quiet machine.** Checked at the start of the stage and around every block, all without administrator access:

- **load:** the 1-minute load average (`sysctl -n vm.loadavg`), read before the block's first pass process starts and again after its last one has exited and 120 s have passed, is at most the 95th percentile of R1's idle window plus 0.5. The figure is fixed in the config before the candidate plan. It is never read while the stage's own process loads the machine (the fourth review's N6: an absolute 1.0 could not pass; idle load there was 1.95 to 2.13). R1's own check uses this rule on its own idle window, taken first;
- **no other study's process alive:** no process, other than the stage's own, whose command line contains `studies/`, `arborlm` or `pytest` (`ps -Ao pid,command`). E2 therefore cannot overlap any registered stage of another P10-I study;
- `HIDIdleTime` at least 600 s (the human lead is not using the machine);
- AC power, power mode not low, no thermal warning (`pmset -g batt`, `pmset -g`, `pmset -g therm`);
- disk0 driver read and write rates and operations over a 30 s window at or below the 95th percentile of R1's idle window, fixed in the config;
- no sleep or restart inside a block (boot time unchanged; the stage runs under `caffeinate -i`, a system tool).

If the check fails at a start, the stage waits and retries every 10 minutes for at most 6 hours, then is **PAUSED** with the failed readings recorded and is rescheduled, in up to three further sessions; only then ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET). A block that was not quiet at its end is invalid and is replaced once by the spare repeat (workload seed 280006). No latency or throughput figure is registered from a block that was not quiet. Every wait has a deadline.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind (DIRECTION.md section 5) | Rule |
|---|---|---|
| 10 GB written; no third build of a file; 500 GB free | Resource cap (physical) | Only the human lead changes it, on projection, never on outcome values. Reaching it is PAUSED, resumable from the last verified chunk |
| Charged hours (section 10) | Resource cap | Set before the candidate plan by the rule; extendable on projection; PAUSED, resumable |
| Memory guard: 4 GiB of `ri_phys_footprint` per process | Resource cap | No stage needs more than about 1 GiB (the largest pass holds 64 MiB of read bytes). Passing it is ENGINEERING STOP (MEMORY GUARD) |
| File size; sizes s; depths k; n(s); 5 repeats and one spare; tiling | Design ceiling | Fixed now. No count gate on generated data: the counts are fixed arithmetic |
| Quiet sessions (1 + 3); retry 10 min for 6 h; idle window 10 min; 120 s settle | Design ceiling | Fixed now |
| Load ceiling by the rule of section 8; idle time 600 s; background I/O at R1's 95th percentile; counter exactness; bit identity; the HARNESS-LIMITED quarter | Validity threshold | The rules are fixed now, the figures in the config before the candidate plan; never changed after |
| m_t rule with its 0.10 floor and 0.30 ceiling; 4 of 5 (EQ-B); 20 of 24 cells (EQ-D); EQ-A's every-pass rule; U ≥ 0.5 and R_min 0.90 (scientific part) | Scientific threshold | Never relaxed after observation |

**ENGINEERING STOP (ADR-0029 section 20, ruling 11).** A code error inside an item, or an environment error (I/O error, out of memory, full disk, data mismatch, prediction mismatch), refuses the registered analysis of its stage. The outcome is ENGINEERING STOP (cause). It is never recorded as NOT EVALUABLE and never as a label, and nothing is labelled from that stage until the cause is fixed under a recorded amendment and the stage is run again on tiles not yet read. An identity difference in a frozen input is PAUSED — IDENTITY; restoring the file bit for bit lets the stage resume. A drive health warning is PAUSED and goes to the human lead. No limit is extended because a partial result looks close.

**NOT EVALUABLE reasons, checked in this order; the first failing one is the label and all failing ones are printed.** Engineering: NO PHYSICAL COUNTER; CACHE NOT DEFEATED; POSITIVE CONTROL FAILED; TIMING SPREAD (EQ-B's label only); MACHINE NOT QUIET (after rescheduling; EQ-B and EQ-D only); FEWER THAN FOUR VALID REPEATS (EQ-B) or FEWER THAN TWENTY CELLS (EQ-D); WRITE BUDGET EXHAUSTED (only if the human lead declines more after a PAUSE). EQ-A uses every pass whether or not its block was quiet, and neither TIMING SPREAD nor MACHINE NOT QUIET applies to it. Scientific: PREREQUISITES NOT MET; NO MATCHING POINT AT EQUAL BYTES. Unreadable wear counters are not on this list (EC3).

## 10. Cost and seeds

**Hours (estimates from the reviewers' descriptive timings; replaced by M).** R0 0.2; R1 0.5 (two builds, the checks, a 10-minute idle window); M 0.3 to 0.5; K 0.3; E1 0.1 to 0.2; P under 0.1; E2 0.5 to 0.8 (120 passes, each a process start, well under a second of reads and its hashing, plus 120 s of settling per block), plus quiet waiting, which is not charged; analysis 0.2. **Total about 2 to 3 charged hours.** The cap is set by the rule after M; until then the provisional figure is 5 hours. E2 reads 3.43 GB (4.11 GB with the spare); reads are not charged to the write budget.

**Seeds** (`docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md`, revision 3, section 4.2 row P10-I-S5). A gate re-runs the registry checker before the freeze.

| Role | Registered | R1 | Rehearsal M | Rehearsal K |
|---|---|---|---|---|
| File contents | 280101 (280102, 280103 unused) | 289001 (rehearsal file); 289013 (control file) | — (R1's file) | — |
| Request order, one per repeat ("query workload" in the registry) | 280001–280005; spare 280006; 280007–280010 unused | 289011 | 289211–289215 | 289216–289220 |
| Pass order, one per repeat ("arm order") | 280201–280205; spare **280206** | 289021 | 289221–289225 | 289226–289230 |
| Tile assignment, one per file | **287001** | — (reserved band) | **289241** | **289242** |
| Re-read test offsets | — | **289051** | — | — |

**Roles and values the registry lacks** (bold above, and the rehearsal values beyond 289211, 289212 and 289221; all lie in this study's own blocks and are unassigned by the fourth review's check; `PENDING` a registry revision 4 by the auditor before the freeze): the tile-assignment role (287001, 289241, 289242); the spare's pass order (280206); rehearsal request orders 289213–289220 and pass orders 289222–289230; R1's re-read offsets 289051. **No longer used:** 289012 and 289201 (one R1 order; the rehearsal file is R1's), the ANN build seeds (280301–280303, 289031, 289231) and the workload-calibration seeds, which the fourth review moved to 287101 and 287102: this revision has no index and no calibration, so those two values stay unassigned. Initialisation 330501–330599 stays unused (scientific part).

## 11. Open choices, with the lead's recommendation

1. **Scope: the device cost-model study** (section 2.4). Taken by the lead under the delegation with the recorded reasons; reported to the human lead first. The alternative is draft 4's study with the fourth review's twelve edits.
2. **EC3 restated** so that unreadable wear counters do not block the part. Sound by the fourth review; reported to the human lead with item 1.
3. **Write cap 10 GB** (permitted: 250 GB). A file above RAM is within the permission and is not recommended: it is not exact.
4. **Depths 1 to 32 and sizes 1, 3, 8, 64 pages; n(s).** The reviewer's candidate named depths 1 to 16; 32 is added at the lead's direction and costs 111 tiles per repeat. Alternative: stop at 16 and raise n(64).
5. **EQ-D descriptive, with no registered ordering.** Alternative: a three-way label on pages per second at depth 4 against depth 1 at one page, at margin m_t. Not recommended: the drafter cannot say in advance which depth a redesign would use, and the harness's own cost may bound the high depths.
6. **m_t rule; EQ-B's label on three pages; 4 of 5; 20 of 24.** As drafted.
7. **The scientific part stays NOT EVALUABLE on record** (section 3.2). Nothing here changes it.
8. **Decision 1 and Decision 2.** The drafter stops here.

## 12. Engineering pattern (ADR-0029 sections 13 and 18 to 20)

- **Order:** independent review of this draft → Decision 1 → implementation in new files (`studies/p10is5/`, `configs/p10is5_ssd.toml`, `tests/test_p10is5_*.py`) with an independent implementation audit → R0, R1 → measuring rehearsal → config fixed (m_t, quiet figures, caps) → candidate `plan.json` → counting rehearsal against that file, whose SHA-256 goes into its record → freeze, which refuses any other hash → Decision 2 → E1 → P → E2 → independent recomputation → outcome record → deletion.
- **Nothing a rehearsal produces after the candidate plan is inside a frozen file (the fourth review's N2).** The margin and the quiet figures come from R1 and M and are in the config before the plan is written. `plan.json` holds **definitions, not outputs**: the registered and the rehearsal geometries, the seeds, the cells, n(s), the tiling rule, the file paths. It does not hold m_t, the quiet figures, request lists or any measured value. The prediction record (every request) is written by P after the freeze and bound by E2's refusal rule.
- **Frozen inputs, with this ADR outside them:** `studies/p10is5/**`; the config, which holds every threshold; launch scripts; `freeze/plan.json`; stage caps; R1's and M's records. Identity by SHA-256 of each file. The freeze stores this ADR's hash for provenance only. A test asserts that every threshold here equals the config's value. A difference is PAUSED — IDENTITY.
- **The file directory is outside every worktree.** Nothing is written or committed in the frozen worktree between a Decision 2 and the end of that stage's report; status goes to the lead in chat or to another branch.
- **Analysis tests:** the analysis and report are tested on a synthetic registry with known answers for every row of section 5.3, CELL NOT EVALUABLE, HARNESS-LIMITED, every NOT EVALUABLE reason and ENGINEERING STOP, and the arithmetic lines of section 5.5.
- **Platform of record:** the research machine, macOS arm64, the project `.venv` (CPython 3.12.14, torch 2.8.0). The third review's probes ran under another interpreter; R0 repeats them. Checks run locally. Delegated work records the model that ran it from session metadata; implementer and auditor in separate contexts.

## 13. Rulings for the implementer

The fourth review's rulings G1 to G14 are taken where they still apply; G2, G3's routing table, G8, G9, G13 and G14 concerned the withdrawn read paths.

1. **Generator (G1).** Exactly section 4.1: one generator per tile, one `torch.randint` call of 1,048,576 `uint8` values. No numpy (it is not in the lock); torch and the standard library only.
2. **Constants.** `F_RDAHEAD` 45, `F_NOCACHE` 48, `F_FULLFSYNC` 51; `proc_pid_rusage(pid, 2, …)` with the structure of `ssd_probe_0028.py` (`ri_diskio_bytesread`, `ri_diskio_byteswritten`, `ri_phys_footprint`). A non-zero return is an environment error.
3. **Tile assignment (G6).** `torch.randperm(4096, generator=torch.Generator().manual_seed(seed))`; tiles are dealt in the order repeat 1 to 6, then k = 1, 2, 4, 8, 16, 32, then s = 1, 3, 8, 64, taking 7, 20, 20, 64 tiles each. Segment i of a tile starts at page i × s of the tile. In the rehearsal geometry the permutation is over tiles 0 to 895 and the counts are 2, 5, 5, 16.
4. **Request order.** The pass's segments, listed by (tile position in the deal, segment index), are permuted by `torch.randperm` with a generator whose state is the first 8 bytes of SHA-256(`p10is5|order|<repeat seed>|<k>|<s>`) modulo 2⁶³; the first n(s) are used; request j goes to thread j mod k.
5. **Pass order (G11).** `torch.randperm(24, generator=manual_seed(order seed))` over the cells listed k-major as in ruling 3.
6. **Harness.** One process per pass. k `threading.Thread`s, each with its own descriptor (opened with the discipline before the first snapshot), started and parked on a `threading.Barrier`; snapshot; release; each thread runs its list with `t0 = perf_counter_ns(); b = os.pread(fd, n, off); t1 = perf_counter_ns()` and keeps (t0, t1, b); join; snapshot. A short read is an environment error. `sys.getswitchinterval()` is recorded and not changed; `torch.set_num_threads(1)`.
7. **Live requests against the prediction (G3, X-10).** As section 5.2.
8. **Hashing (G4, X-11).** After the pass's last snapshot, never between snapshots.
9. **No print and no file write between snapshots (G10).**
10. **Statistics.** Medians and percentiles by the nearest-rank rule on the sorted values; CV with the sample standard deviation (n − 1); "pooled" means all requests of a cell over its valid repeats.
11. **Rehearsals (G5, G12).** M and K use the rehearsal geometry with their own seeds; K's tiles may repeat M's (nothing is cached on the host, and K's timings decide nothing). Neither reads the file, which does not exist before E1.
12. **Spare (G7, X-12).** One, seeds 280006 and 280206, repeat 6 of the tiling; used for the first invalid block only.
13. **Build.** Chunks of 1 GiB, each written, then verified by an uncached read against the regenerated SHA-256 (it leaves nothing cached, probes 1B2 and 3; it precedes every registered pass). Resume at the first unverified chunk; rewritten bytes are charged. E2 starts no sooner than 10 minutes after E1's last write and after a quiet check.
14. **Order of checks at the start of every stage:** identity, EC3 record, free space, hygiene, memory guard, write-budget projection, quiet check (if the stage needs it).
15. **Outcomes and records.** Exactly the names in sections 1, 5, 7 and 9; wear counters print `NOT READABLE`. Every pass writes its requests, per-request times and thread, counter snapshots (process, volume, driver), page hashes and quiet readings under a git-ignored run directory outside the frozen files; a guard asserts that it is ignored.
16. **Anything not ruled here is a question to the lead before code is written, not a choice.**

## 14. What the engineering result can and cannot say

**It can say**, for one Apple SSD (AP2048Z) behind APFS with FileVault, with uncached whole-page requests issued from CPython threads on a 4 GiB synthetic file that fits in RAM and is only made to behave as if it did not: whether the host-side counter equals the layout's arithmetic; what one page costs at depth 1, with its distribution; whether a page costs less inside a contiguous request; and how request latency and pages per second change over six depths and four request sizes, as seen by the host through this harness.

**It cannot say anything about:**

- **accuracy, the trained tree, or a neural-memory advantage.** No memory, key, query or index is in the file. The lines of section 5.5 are arithmetic on the cost table, not a measurement of T-OQ, and no sentence about the project's objective, about hypotheses H3 to H5 or about the scientific line may cite an engineering label or those lines;
- whether a tree or an index is better: for today's one-level tree that is fixed by the layout (section 2.4), and the regimes where it is not belong to the redesign;
- the cost of routing or of any computation in RAM, which is of the same order as the I/O for a T-OQ-shaped query and is not measured here;
- whether storage is needed (the file fits in RAM); warm or hot-page caching; other drives, filesystems or operating systems; an asynchronous or native I/O path, which may be cheaper than threads under the interpreter lock; the drive's internal queue;
- NAND traffic, wear, endurance, sustained writes or updates;
- published ANN systems: no number from them is used;
- from a scientific label under `RAM RESTRICTED BY CONSTRUCTION`: that storage was needed. P7 and P8 outcomes are unchanged whatever S5 finds.

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

Section numbers in the two tables above are draft 3's.

**Third review** by the `arbor-auditor` subagent (Claude Opus 5.5, as that review reports): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW3_ADR-0028.md`, copied word for word; engineering part only; verdict NOT READY (3 blocking, 10 required, 5 advisory). It probed this machine on 2026-11-18 (56 MiB written and deleted). Draft 4 (commit `2d92c27`) answered it; the table is draft 4's, with draft 4's section numbers. Rows about the store of keys and values, the read-path arms, the index, recall, the resident budgets and S-FLAT describe content that draft 5 withdraws (section 2.4); the counter rule, the read discipline, EC3, the engineering stops and the engineering pattern stand.

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

**Fourth review** by the `arbor-auditor` subagent (Claude Opus 5.5, as that review reports; the same reviewer as the third, which it discloses): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW4_ADR-0028.md`, copied word for word; verdict READY AFTER THE LISTED EDITS (X-1 to X-12), with two blocking construction problems (N1, N2) and a smaller study offered as a scope choice. The lead adopted the smaller study (section 2.4). Draft 5 is by the lead (an `arbor-lead` subagent, Claude Fable 5.2). **Draft 5 has not been reviewed**, and the reviewer's "ready after the edits" was given for draft 4's scope, not for this one. The drafter ran no probe and no code; it ran read-only commands, `ruff` and `git`.

| Finding or edit | Disposition | Where |
|---|---|---|
| N1 (blocking) the disjoint-page plan runs out of pages | FIXED by construction: a seeded permutation of tiles, aligned segments, fixed counts, no acceptance loop | §4.3 |
| N2 (blocking) the counting rehearsal's outputs inside the file it rehearses; rehearsal geometry; rehearsal seeds | FIXED: margin and quiet figures from M and R1, in the config before the plan; the plan holds definitions only; a rehearsal geometry that fits the rehearsal file; five seeds per rehearsal | §5.4, §8, §10, §12 |
| N3 EQ-C nearly insensitive | ACCEPTED: EQ-C withdrawn with its arms | §1, §2.4 |
| N4 EQ-B's outcome near-certain; the sweep sampled one region | FIXED: said in the text; every cell is spread over the whole file | §5.3, §4.3 |
| N5 "exactly" under 4 of 5 | FIXED: every pass of every repeat attempted | §5.3 EQ-A |
| N6 the quiet rule could not pass | FIXED: R1's idle 95th percentile plus 0.5, read before the stage's own process loads the machine and 120 s after | §8 |
| Section 2: "by construction" partly the draft's own definition; regimes (a) to (e); the prior costs one pass over the routes | ACCEPTED and recorded with the scope decision | §2.4 |
| X-1 | APPLIED: the delegation record, section 7, commit `fa60cc4`, governs; EC1 and EC2 are met only from it | §2.3, §3.1 |
| X-2 | APPLIED in substance (the stage that measures is M, not K, at the lead's direction) | §8, §10, §12 |
| X-3 queries per pass, reserved band | SETTLED by the scope decision: no queries; the band idea became the tiling | §4.3 |
| X-4 EQ-C on the I/O part | SETTLED by the scope decision: EQ-C withdrawn; EQ-D in its place | §5.3 |
| X-5 | APPLIED | §5.3 |
| X-6 | APPLIED, with the figure fixed from R1 before the candidate plan | §8, §9 |
| X-7 | APPLIED: 1, 3, 8 and 64 pages; 64 pages is 1 MiB; also at depth 32 | §7 |
| X-8 | APPLIED | §9 |
| X-9 | APPLIED as whole-file sampling; the calibration seeds 287101 and 287102 have no use, because no calibration remains | §4.3, §10 |
| X-10 | APPLIED to request lists; there is no routing table | §5.2, §13 item 7 |
| X-11 | APPLIED; the S-FLAT clause has no object | §7 item 6, §13 item 8 |
| X-12 | APPLIED: one spare, 280006, with pass-order seed 280206 | §8, §13 item 12 |
| G1, G4 to G7, G10 to G12 | RULED | §13 |
| G2, G3 (routing table), G8, G9, G13, G14 | NO OBJECT after the scope decision | §13 heading |
| Section 8, open choices | Taken as recommended; scope and EC3 are reported to the human lead first | §2.3, §11 |

**Not settled by this draft:** whether `.noindex` keeps Spotlight out; whether `purge` needs administrator access; what the idle load and idle I/O of this machine are, and so whether the quiet rule can be met in a reasonable wait; whether Python threads can load the drive at depths 16 and 32 or the harness bounds those cells (the HARNESS-LIMITED tag reports it; it is not known in advance); whether the per-process counter is exact with several threads (R1 checks it; the probes were single-threaded). None could be settled without a probe, which the drafter was not permitted to run.

`Astra review: NOT_PERFORMED`.
