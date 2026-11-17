# ADR-0028 — P10-I-S5: physical SSD-backed memory (conditional specification)

**Status: DRAFT — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run. Entry requires a separate decision by the human lead.**

- Date: 2026-11-17 UTC. Revision 2, after independent review (section 15). Drafted by the lead (Claude Fable 5.2) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification. It fixes the entry criteria, the questions, the primary comparisons, the verdict labels, the stop rules, the cost and write ceilings and what is reserved for the human lead. Section 13 lists what a later revision must fix before a freeze. Approval of the P10-I programme does not authorize this study, and authorizes no write to the drive.
- **No hardware purchase and no large write-intensive benchmark is authorized, by this document or by its approval.** The only device is the internal SSD of the human lead's working computer.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Two questions, two verdicts, never combined

| Verdict line | Question | Evidence it may use |
|---|---|---|
| **ENGINEERING SSD PERFORMANCE** | On this device, from a cold cache, at equal result quality and equal RAM held, how does a sparse tree-shaped read path over a store on SSD compare in measured block-device traffic and throughput with a flat read and an ANN index over the same bytes? | A synthetic store and synthetic queries are allowed |
| **SCIENTIFIC NEURAL-MEMORY ADVANTAGE** | Does one trained neural memory, addressed without an oracle, give better task quality at equal measured block-device traffic than fair storage baselines, at a scale where storage is really needed? | Only a qualified, trained memory (section 3.2) |

A synthetic large-store benchmark tests real storage behaviour. It is **not** evidence of useful neural-memory scaling, whatever it shows. Neither line is summarised by the other. No report sentence joins them, and no paragraph about one line cites the other's label.

| Line | Positive | Negative | Inconclusive / not evaluable |
|---|---|---|---|
| Engineering | SPARSE PATH READS LESS AND IS FASTER AT MATCHED RECALL AND RAM | BASELINE NOT WORSE | NOT SEPARATED AT MARGIN; MEASURES DISAGREE; ENGINEERING NOT EVALUABLE (reason) |
| Scientific | ADVANTAGE SUPPORTED AT TESTED SCALE | NO ADVANTAGE OVER STORAGE BASELINES | INCONCLUSIVE; SCIENTIFIC NOT EVALUABLE (reason) |

A positive engineering label is about one read path, on one device, under one synthetic workload. It says nothing about learning.

**Why cold is primary.** A cold cache is the regime in which storage traffic is actually paid, and the only one this design can verify. It is the worst case; a deployed system would also cache hot pages. Warm figures are printed for every arm under the same rule, descriptively, and enter no label.

## 2. Background: what the records already hold

| Finding | Record |
|---|---|
| P7-A: CONCENTRATION-ONLY for both tree kinds: the trees' lower simulated page reads "come from using fewer rows"; "No NVMe experiment on these checkpoints is proposed" | `docs/decisions/ADR-0013-p7a-storage-page-locality.md`, outcome record |
| P7-B: WITHIN 10% OF FLAT CO-ACCESS on both streams for both tree kinds, REPLICATED; decision class N (no storage-locality case for the hierarchy) | `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` section 16 |
| P8: INCOMPLETE (55 of 60 cells simulated); no case LOCALITY-POSITIVE; every locality term acted as a concentration term; the standard flat memory used about 127 effective slots of 4,096 | `results/p8-2026-11-14/SUMMARY.md` |
| P8 supplement: 5 of 5 collapsed cells simulated; supplementary classes of C04 and C05 QUALITY-FAILED; P8 stays INCOMPLETE | `results/p8-supplement-2026-11-14/README.md` |
| P10-S1 "Estimated storage traffic": arithmetic and simulation, no device; value pages only, keys assumed in RAM; 1,024 value bytes per query at 8 rows | `results/p10s1-run-2026-11-17/RESULTS.md` |
| P10-S1 supplementary throughput, in RAM, descriptive: T-OQ 10,106 to 10,211 queries/s at batch 1 from 1,024 to 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | `results/p10s1-run-2026-11-17/OUTCOME.md` section 3; `supplement/throughput_supplement.json` |
| P10-S1 mean a_use at 32K/16K: at the registered read point U_P, T-OQ 0.401, F-OQ 0.916, D-OQ 0.957; at the run length, 0.697, 0.992, 0.999. The comparison of the tree with the clustered index reverses between the two read points at some cells | `OUTCOME.md` section 4; `LITERATURE_AND_ROUTING_NOTE.md` section 5.1 |
| P10-S0: ADDRESSING-QUALIFIED (4,096 AND 16,384) for arm A5-D at 0.5 facts per slot; NOT DISTINGUISHED FROM A0 at 16,384; OVERLOAD NOT QUALIFIED (1 of 10 cells at two facts per slot); 65,536 slots a probe only | `results/p10s0-run-2026-11-16/OUTCOME.md` |

Everything about storage in P7, P8 and P10-S1 is simulated or arithmetic. No ArborLM record contains a measurement on a device. DiskANN, SPANN and FreshDiskANN are engineering precedent for keeping routing data in RAM and contents on SSD (`LITERATURE_AND_ROUTING_NOTE.md` section 2); they concern vector search, not memories trained by gradient descent, and no number from them is used here. The drafter has not re-read those papers.

**P7-A's lesson, carried into the rules.** A read path that examines fewer candidates reads fewer pages by construction, whether or not it finds the right rows. On a device the same holds. So no arm is compared on traffic or speed unless it returns results of the same registered quality and holds the same amount in RAM (section 5).

**The scale gap.** The largest size with qualified learned addressing is 16,384 slots, half full. By the P10-S1 record's arithmetic a slot is about 64 key bytes (16 × 4) plus 128 value bytes, so that store is about 3.15 MB. The machine has 48 GiB of RAM. The ratio is 16,384: about four orders of magnitude. This gap, not the device, stands between the project and the scientific verdict.

## 3. Entry criteria

Entry to any part is a decision by the human lead.

### 3.1 Engineering part

- **E0, method rehearsal.** The human lead authorises stages R0 and R1 as a method rehearsal, with at most 2 GB written. This is separate from entry to the benchmark. Without E0 nothing is written.
- **Entry to E1 and E2 requires all of:** (E1) the human lead's decision on section 11, item 1; (E2) the write budget of section 6 approved; (E3) the drive's free space and health counters recorded before any write. Lifetime bytes written and percentage used cannot be read with the tools present (`smartctl` is not installed; installing it is a download). E3 therefore needs either an approved tool or the human lead reading the counters. Without one, the part is ENGINEERING NOT EVALUABLE (HEALTH COUNTERS UNREADABLE); (E4) every rehearsal check of section 7 passed in R1.

### 3.2 Scientific part

All of the following, for **one and the same trained system** at one slot count N and one load:

- **Q1, qualified access.** P10-I-S0 (ADR-0023) registers outcome row 4, **OVERLOAD-QUALIFIED UP TO ℓ**, or row 6, **OVERLOAD NOT QUALIFIED; ADDRESSING QUALIFIED UP TO L_Q**, and the system's load is at most L_Q with Line Q **QUALIFIED AT THIS CELL TYPE** at its slot count. Lines A and G license nothing (ADR-0023 section 15). An oracle-addressed result does not count.
- **Q2, useful capacity under that addressing.** The same system, addressed by Q1's learned recipe and not by an oracle, holds useful capacity at N. **No sibling draft registers this.** ADR-0024's C-CAPACITY is oracle-addressed (`STORE ONLY; ORACLE-ADDRESSED`) and has no learned-address lane, so CAPACITY-POSITIVE there does not satisfy Q2: two different systems would be meeting Q1 and Q2. Q2 needs a registered label from a later approved study of the composed system, or a reference check inside S5 on calibration draws whose rule the later revision fixes before any such draw is observed.
- **Q2-U, utilisation, fixed now.** U = N_eff / N, where N_eff is the entropy-effective number of slots selected over the evaluation queries (the measure of P8). Floor: **U ≥ 0.5**. Reason: below one half, most of the stored bytes are not in use, and the bytes on the device are mostly not memory. The figure is not fitted to pass: P8's standard flat memory had about 127 of 4,096 (0.03). `PENDING LEAD REVIEW`. No sibling draft registers a utilisation label, so U is measured in S5's reference check.
- **Q3, real storage need.** The store at N is larger than the RAM available to it.
- **Q4, fair baselines and measured traffic.** Sections 4, 5 and 7 hold.

**What follows from the sibling drafts as they stand.** ADR-0023 licenses learned addressing only at 512 to 16,384 slots (its section 15). At 16,384 slots the store is about 3 MB. So no outcome of P10-I-S0 to S3 can make Q1 and Q3 true together without a restriction of RAM by construction, and Q2 has no registered source. Under this ADR's own ceilings (16 GB per store, 48 GiB of RAM) Q3 can likewise be met only by construction. Any scientific label would then carry `RAM RESTRICTED BY CONSTRUCTION`, and such a label cannot show that storage was needed (section 14). **As capped, the scientific part cannot answer its own question.** It is kept here so that the conditions are on record before any result exists. Today, and after any outcome of P10-I-S0 to S3, the line reads **SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)**.

"RAM restriction" on macOS without administrator access is not an enforced limit: there is no per-process page-cache limit. It means only uncached reads (section 7) plus the resident budget of section 5.

## 4. Arms and baselines

| Arm | What it isolates |
|---|---|
| S-TREE: routing data in RAM, tree-shaped candidate set, value pages on SSD | The subject read path |
| S-FLAT: the same store, exact search over all keys | The cost of not routing; the exact-search reference for recall |
| ANN: an approximate nearest-neighbour index over the same keys and values (clustered or graph) | The conventional answer to the same retrieval problem |
| KV: a plain key-value store, one lookup per requested row, address given | The floor: what storage costs when the address is known. Printed beside every label; decides none |
| RAM: each arm with its store fully in memory | Value parity of the SSD read within dtype tolerance (`docs/EXPERIMENT_PROTOCOL.md`) |

Common to every arm: the same store bytes, queries, page size, read primitive (positional reads on a descriptor with caching and read-ahead off; no memory mapping), block size, one thread, queue depth 1. A higher queue depth is a different measurement and is descriptive. Baseline implementations are fixed by the later revision. A production key-value or ANN library is a new dependency and possibly a download, needs an approved amendment, and must be able to use the common read primitive; a library that can only memory-map is ENGINEERING NOT EVALUABLE (BASELINE NOT FAIR) for that arm.

Workloads are synthetic and fixed, with reasons, in the later revision. The label is read on one primary pattern in which each repeat's queries touch pages no other repeat touches. A pattern replayed from a trained checkpoint's trace repeats pages by nature; it is descriptive.

## 5. Measures and label rules

**Measures.**

- **Bytes read per query**: bytes the operating system requested from the block device for the study's process. Primary counter: the per-process disk I/O counters of the process's resource usage. Cross-check: the system-wide block-driver statistics, minus an idle-window baseline. Both are host-side, block-layer figures. They are never called NAND or media traffic.
- **Queries per second**, and latency median and p99, on a quiet block.
- **Recall at 8** against S-FLAT's exact result on the same store and queries.
- **Resident bytes**: the keys, routing data and index each arm holds in RAM.

**Matching conditions (from P7-A's lesson).**

1. **Recall floor R_min = 0.90**, proposed, `PENDING LEAD REVIEW`. Reason: 0.90 is the proportion this programme uses for "close to a reference" (P10-S0, ADR-0026). S-TREE and ANN are each read at the smallest registered candidate budget whose recall is at least R_min in every repeat. An arm with no such budget is not compared: ENGINEERING NOT EVALUABLE (RECALL NOT MATCHED). Recall is printed beside every bytes and speed figure.
2. **Common resident budget.** One budget in bytes, fixed at the freeze, for keys, routing data and index. Each arm is configured within it and its actual residency is recorded. An arm above the budget is not compared: ENGINEERING NOT EVALUABLE (RAM RESIDENCY NOT MATCHED). If the budget is below the bytes of all keys, S-FLAT reads keys from the device; that is its cost.
3. **Cache ratio** of section 7 within bounds for every arm, and arms' ratios within 0.05 of each other.

**Engineering label**, at the largest registered store size, cold, five repeats (smaller sizes descriptive). Margins m_b (bytes) and m_q (speed) are fixed at the freeze from R1's repeat variability, each at least twice the repeat-to-repeat coefficient of variation. A repeat flagged DEVICE CACHE SUSPECTED (section 7) is invalid; fewer than four valid repeats is NOT EVALUABLE.

| Label | Rule (first match) |
|---|---|
| SPARSE PATH READS LESS AND IS FASTER AT MATCHED RECALL AND RAM | In at least 4 of 5 repeats, in each of them S-TREE is better than **both** ANN and S-FLAT by the margin on **both** bytes per query and queries per second |
| BASELINE NOT WORSE | For one and the same baseline (ANN or S-FLAT), in at least 4 of 5 repeats S-TREE is better by the margin on neither measure |
| MEASURES DISAGREE | For one and the same baseline, in at least 4 of 5 repeats S-TREE is better by the margin on one measure and worse by the margin on the other |
| NOT SEPARATED AT MARGIN | Otherwise |

**Scientific label** (structure fixed now; read only if Q1 to Q4 hold). The memory is read at its registered operating point; its mean bytes per query there is b0. Each baseline (ANN, S-FLAT, and KV) is swept over a registered list of candidate budgets and read at the smallest budget whose bytes per query are at least b0, so a baseline never has less traffic than the memory. No such point: SCIENTIFIC NOT EVALUABLE (NO MATCHING POINT AT EQUAL BYTES). KV is addressed by the task's own surface key, never by an oracle slot address; if KV's quality is within the margin of the memory's, every label carries `LOOKUP SUFFICIENT ON THIS TASK`. Five fresh draws; a replicate favours the memory only if on both panels it is ahead of every baseline by the margin, and favours a baseline if on either panel that baseline is ahead. ADVANTAGE SUPPORTED: at least 4 of 5 favour the memory. NO ADVANTAGE: at least 4 of 5 favour one and the same baseline. INCONCLUSIVE: otherwise. Margins are fixed by the later revision before any such draw.

Rows read, pages simulated, parameters touched and any other logical count are never reported as measured traffic or as efficiency.

## 6. Storage-write budget

| Item | Proposed | Kind |
|---|---|---|
| Bytes written by the study's own processes, all stages and attempts, failed ones included | **64 GB** | Resource cap on a physical resource; only the human lead may change it |
| Share of endurance | 64 GB is about 3.2% of one full write of the drive (1.81 TiB by `df`, 2.0 TB). Under an **unverified placeholder** of 300 full drive writes, about 0.011%. Ceiling: 0.05% of the endurance figure the human lead accepts | Same |
| Largest single store | 16 GB | Design ceiling |
| Free space kept at all times, stores included | At least 500 GB (675 GiB free on 2026-11-17, `df`) | Resource cap |
| Method rehearsal R0 and R1 | At most 2 GB of the 64 GB | Resource cap |

**What is charged.** The study's own logical bytes written, cross-checked by its per-process write counter. The system-wide device counter is not charged, because it counts every process on a working computer: the reviewer measured about 1 MB/s of background writes over 20 s and 5.6 MB/s on average since boot. It is recorded over the study's write windows and the remainder reported as background. A run stops before any write that would pass the cap.

**Endurance.** No project record holds this drive's endurance rating and the drafter knows of no published figure; the 300-writes figure is a placeholder, not a fact. For context, descriptive: the reviewer read about 3.8 TB written in the 7.9 days since boot, a period that includes registered P10 runs; against that, 64 GB is small. Health counters are recorded before and after (entry condition E3).

**Store hygiene, checked in R0, before E1 and before each E2 block.** The store directory is outside any synced folder, excluded from backup and from search indexing, and no local filesystem snapshot holds it (`tmutil listlocalsnapshots /` needs no administrator access). The method of exclusion is verified in R0; if exclusion needs administrator access it is the human lead's action. Stores hold incompressible data, are written once with uncached, page-aligned writes, are never rewritten in a loop, persist across a PAUSE, and are deleted at the end; a store that cannot be shown deleted is reported STORE RETAINED BY SNAPSHOT.

Update traffic (in-place trained updates on SSD) is write-intensive and is **outside** this document.

## 7. Cache verification: rehearsal checks, not assumptions

Nothing in this section has been tested on this machine. Each item is a check in R1 on the reference arm (KV) and then on the exact build-then-read path of every arm. A check that fails is ENGINEERING NOT EVALUABLE with the reason named; a check the reference fails is not used.

| Check | What R1 must show | If it fails |
|---|---|---|
| Counter visibility | The per-process counters and the block-driver statistics can be read without administrator access and move with a known uncached read (the reviewer could read the driver statistics; the per-process counters are untested) | NO PHYSICAL COUNTER, unless the human lead provides access |
| Cold state reachable | After an uncached, aligned build, a first read pass has cache ratio (counted bytes over logical bytes requested) at least 0.9. Disabling caching on a descriptor is not known to evict pages already cached, so the build path matters. The system-wide cache flush (`purge`) is believed to need administrator access and is not relied on; if a cold state can be reached only that way, or only by a restart, it is the human lead's action and the procedure after a pause or restart is written into the freeze | CACHE NOT DEFEATED |
| Ratio upper bound | The ratio is at most 1.1 times the layout's expected read amplification, so other processes' reads cannot pass as the study's | COUNTER CONTAMINATED |
| Positive control | The same reads with caching allowed, second pass: ratio below 0.1. Run last, or on pages no cold pass uses | The counter cannot see caching; the method is invalid |
| Drive and controller cache | Cannot be defeated from software. A settling interval after E1 fixed at the freeze; disjoint pages per repeat; arm order randomised within a block; a repeat pass faster than its first pass by more than a registered factor is DEVICE CACHE SUSPECTED and that repeat is invalid | Fewer than four valid repeats: NOT EVALUABLE |
| Counter continuity | No restart or sleep inside a block (driver statistics are since boot); the machine is kept awake | COUNTER RESET; the block is PAUSED and repeated |

The 0.9 floor still allows up to a tenth of an arm's reads to be cache hits, which would favour an arm with concentrated access (P7-A's mechanism again). That is why each arm's ratio is printed and arms whose ratios differ by more than 0.05 are not compared. 0.9, 0.1, 1.1 and 0.05 are proposals with these reasons: aligned reads should count at least their logical bytes; a tenth allows for counter granularity. All four are `PENDING LEAD REVIEW`. Encryption, copy-on-write and fragmentation are properties of this device, stay on, and are recorded in the hardware fingerprint.

## 8. Stages

| Stage | Writes | Quiet machine | Notes |
|---|---|---|---|
| R0 device record | none | No | Free space, health counters (E3), fingerprint, store-hygiene checks |
| R1 method rehearsal (needs E0) | at most 2 GB | Yes, about 30 minutes | Every check of section 7; repeat variability; background I/O rates; fixes margins |
| Freeze, Decision 2 | none | No | |
| E1 store build | up to 16 GB per layout | No | Resumable per layout; bytes charged before each write |
| E2 read benchmark | none | Yes, about 1 to 2 hours (estimate) | See below |
| S scientific comparison | within the same cap | Yes | Only if Q1 to Q4 hold |
| Analysis, report, independent recomputation | none | No | |

**Quiet condition, measured at the stage.** No record states this machine's idle load or idle disk activity; R1 measures both. A block is quiet if, over a window before it and at its end, the 1-minute load average and the background read and write rates from the driver statistics stay at or below figures fixed at the freeze, the machine is on mains power, not in Low Power Mode, and reports no thermal pressure. A block that is not quiet is **PAUSED** and rescheduled with the human lead, in up to three further sessions; only then MACHINE NOT QUIET. No throughput, latency or traffic comparison is registered on a block that was not quiet.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind | Rule |
|---|---|---|
| 64 GB written; 0.05% of endurance; 500 GB free | Resource cap (physical) | Changed only by the human lead, on projection, never on outcome values. Reaching one is **PAUSED**, resumable from the last completed layout |
| Charged time, proposed 8 hours | Resource cap | Extendable on projection; PAUSED and resumable |
| 16 GB per store; store sizes; repeats (5); patterns; candidate budgets | Design ceiling | Fixed at the freeze |
| Rescheduled quiet sessions (3); settling interval; idle-baseline window | Design ceiling | Fixed now (3) or at the freeze |
| Load and background-I/O figures; device-cache factor | Validity threshold | Fixed at the freeze from R1; not changed after |
| R_min 0.90; U ≥ 0.5; margins; 4 of 5; ratios 0.9, 0.1, 1.1, 0.05 | Scientific threshold | Never relaxed after observation |

The study stops and returns to the human lead on a drive health warning, an I/O error, or a failed gate. No limit is extended because a partial result looks close.

NOT EVALUABLE reasons, each printed by name: PREREQUISITES NOT MET; HEALTH COUNTERS UNREADABLE; NO PHYSICAL COUNTER; CACHE NOT DEFEATED; COUNTER CONTAMINATED; COUNTER RESET (after the allowed repeats); MACHINE NOT QUIET (after rescheduling); POWER OR THERMAL STATE; RECALL NOT MATCHED; RAM RESIDENCY NOT MATCHED; BASELINE NOT FAIR; VALUE PARITY FAILED; DEVICE CACHE SUSPECTED (fewer than four valid repeats); WRITE BUDGET EXHAUSTED (only if the human lead declines more after a PAUSE); NO MATCHING POINT AT EQUAL BYTES (scientific part).

## 10. Cost projection (estimate; replaced by the rehearsal)

Time is small: P10-S1's supplementary throughput took 26.9 s for 30 figures in RAM (`throughput_supplement.json`). No record holds a device read or write rate, so build and read times are a guess: minutes to an hour per layout, 2 to 6 hours for the engineering part. The binding cost is wear: about three on-device layouts of 16 GB plus rehearsal is about 50 GB of the 64 GB cap; whether 50 to 64 GB of store builds counts as "large" is the human lead's judgement (section 11, item 2). R1 measures rates, variability and counter behaviour and replaces this. The scientific part cannot be costed.

Seeds: proposed namespace **280001–289999**; a scan of `configs`, `studies`, `src`, `tests` and `docs/decisions` found no earlier use. Sibling drafts as read on 2026-11-17: ADR-0023 300001–309999; ADR-0024 240001–249999; ADR-0025 250001–259999; ADR-0026 initialisation 2601–2691; ADR-0027 270001–279999. A freeze gate asserts disjointness.

## 11. Reserved for the human lead

1. **May the engineering part run before a neural memory is qualified at scale?**
   - For: it depends on no neural result; the project's motivation is storage (`docs/RESEARCH_HANDOFF.md`) and no device measurement exists; the cache method is untested here and is better debugged before a scientific result depends on it; it would show whether the tree's constant read-path throughput in RAM (about 10,100 queries/s at batch 1 from 1,024 to 16,384 slots) survives real I/O.
   - Against: P7-A, P7-B and P8 found no storage-locality case for the hierarchy, in simulation; the workload must be invented and the label depends on it; the tree's quality is behind the flat memory's at both read points (0.401 against 0.916 at U_P, 0.697 against 0.992 at the run length), so the read path benchmarked may not be the one that survives ADR-0024's routing work, and a favourable label would be about that path only; it wears the working drive; an engineering label is easily misread as progress on the objective.
   - Recommendation: authorise only E0 (R0 and R1, at most 2 GB) early. Hold E1 and E2 until ADR-0024's R-DIAGNOSIS has shown which read path is worth benchmarking.
2. **The write budget, the endurance figure, and whether 50 to 64 GB of store builds is acceptable.** Recommendation: 64 GB and the 0.05% ceiling, or lower.
3. **Actions that need administrator access or a tool install:** reading drive health counters (E3); a cache flush or restart if R1 shows a cold state needs one; backup or indexing exclusions if they need it; device counters if R1 shows they need it. Recommendation: the human lead runs these; the lead does not hold the access.
4. **Baseline implementations**: written in the project, or an approved dependency amendment. Recommendation: an amendment, if the library can use the common read primitive.
5. **The scientific part as capped cannot answer its question** (section 3.2). Options: leave it NOT EVALUABLE on record (recommended); or, in a later and separate decision, a larger store and a study of the composed learned-address system.
6. **R_min, U ≥ 0.5, the cache ratios, 4 of 5.**
7. **The entry decision for each part**, and approval of the revised specification. Any other device or any purchase is a separate decision and is not proposed.

## 12. Engineering requirements carried from P10

- The frozen-input set is listed file by file. Status and run notes go to a notes file outside it; nothing is committed in the frozen worktree during a run. Stages are resumable; PAUSED continues; completed layouts and blocks are not redone, which also protects the write budget.
- Every registered stage is rehearsed end to end against the frozen plan itself before Decision 2, at a reduced store size.
- Every reading rule is in the specification (section 5). The reference arm (KV) is run through every validity check in rehearsal; a check it fails is not used. The analysis, with its descriptive sections, is tested on a synthetic registry with known answers, one for each label row.
- No count gate on generated data: stores are "generate until built, within the write budget".
- Platform of record: the research machine (macOS 27.2.1, arm64, CPython 3.12.14, torch 2.8.0, as in the throughput supplement's environment record). Bit-exact and value-parity assertions are made on it only. Checks run locally; GitHub CI is not relied on.
- Delegated work records the model that ran it from session metadata; implementer and auditor in separate contexts.

## 13. What a later revision must fix before a freeze

Baseline implementations and versions; the workloads and their reasons; page size, block size and layout; store sizes; candidate budgets; the resident budget; margins from R1; the quiet figures; the settling interval and device-cache factor; the cold-state procedure; the rule of the Q2 reference check, if the scientific part is ever proposed; seeds; the frozen-input set. Fixed already: the label rules, R_min, U, the cache ratios, what is charged to the write budget.

## 14. What S5 cannot establish

- From the engineering part: anything about learning, useful capacity, neural-memory scaling or the project objective; anything about a read path other than the one tested.
- NAND or media traffic, endurance, sustained-write or update behaviour; behaviour on another drive, filesystem or operating system, at another queue depth, or with warm caches.
- That an advantage holds beyond the tested store size, workload and recall floor.
- From a scientific label under `RAM RESTRICTED BY CONSTRUCTION`: that storage was needed.
- That hypotheses H3 to H5 hold in general. P7 and P8 outcomes are unchanged whatever S5 finds.

## 15. Review record

Independent review by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0027_ADR-0028.md`, verdict NOT READY (1 blocking, 14 required, 6 advisory). This revision is by the lead (Claude Fable 5.2). It has not been re-reviewed. Neither is Astra review or human approval. Device observations quoted from the review are the reviewer's; the drafter ran nothing.

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
| B-R9 health counters unreadable | REQUIRED | FIXED | §3.1 E3, §11 item 3 |
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

`Astra review: NOT_PERFORMED`.
