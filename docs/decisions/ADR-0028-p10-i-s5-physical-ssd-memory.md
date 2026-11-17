# ADR-0028 — P10-I-S5: physical SSD-backed memory (conditional specification)

**Status: DRAFT — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run. Entry requires a separate decision by the human lead.**

- Date: 2026-11-17 UTC. Drafted by the lead (Claude Fable 5.2) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification. It fixes the entry criteria, the questions, the primary comparisons, the verdict labels, the stop rules, the cost and write ceilings and what is reserved for the human lead. Section 13 lists what a later revision must fix before a freeze. Approval of the P10-I programme does not authorize this study.
- **No hardware purchase and no large write-intensive benchmark is authorized, by this document or by its approval.** The only device is the internal SSD of the human lead's working computer.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Two questions, two verdicts, never combined

| Verdict line | Question | Evidence it may use |
|---|---|---|
| **ENGINEERING SSD PERFORMANCE** | On this device, with caches defeated or accounted for, how does a sparse, tree-shaped read path over a store on SSD compare in measured physical I/O and throughput with a plain key-value store and an ANN index holding the same bytes? | A synthetic store and synthetic queries are allowed |
| **SCIENTIFIC NEURAL-MEMORY ADVANTAGE** | Does a trained neural memory, addressed without an oracle, give better task quality per measured physical I/O than fair storage baselines at a scale where storage is really needed? | Only a qualified, trained memory (section 3.2) |

A synthetic large-store benchmark tests real storage behaviour. It is **not** evidence of useful neural-memory scaling, whatever it shows. Neither line is summarised by the other, and no report sentence joins them.

| Line | Positive | Negative | Inconclusive / not evaluable |
|---|---|---|---|
| Engineering | SPARSE PATH READS LESS AND IS FASTER (both registered measures, section 5) | BASELINE AT LEAST AS GOOD | MEASURES DISAGREE; ENGINEERING NOT EVALUABLE (reason) |
| Scientific | ADVANTAGE SUPPORTED AT TESTED SCALE | NO ADVANTAGE OVER STORAGE BASELINES | SCIENTIFIC NOT EVALUABLE (reason); INCONCLUSIVE |

A positive engineering label means a read path behaves well on one device under one synthetic workload. It says nothing about learning.

## 2. Background: what the records already hold

| Finding | Record |
|---|---|
| P7-A: CONCENTRATION-ONLY for both tree kinds; lower simulated page misses come from using fewer rows; "No NVMe experiment on these checkpoints is proposed" | `docs/decisions/ADR-0013-p7a-storage-page-locality.md`, outcome record; `results/p7a-2026-11-13/` |
| P7-B: WITHIN 10% OF FLAT CO-ACCESS on both streams for both tree kinds, REPLICATED; decision class N (no storage-locality case for the hierarchy) | `docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md` section 16; `results/p7b-2026-11-13/` |
| P8: INCOMPLETE (55 of 60 cells simulated); no case LOCALITY-POSITIVE; every locality term acted as a concentration term | `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` status line; `results/p8-2026-11-14/SUMMARY.md` |
| P8 supplement: 5 of 5 collapsed cells simulated; supplementary classes of C04 and C05 QUALITY-FAILED; P8 stays INCOMPLETE | `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md`; `results/p8-supplement-2026-11-14/README.md` |
| P10-S1 "Estimated storage traffic": arithmetic and simulation, no device; value pages only, keys assumed in RAM; 1,024 value bytes per query at 8 rows | `results/p10s1-run-2026-11-17/RESULTS.md` |
| P10-S1 supplementary throughput, in RAM, descriptive: T-OQ about 10,100 queries/s at batch 1 from 1,024 to 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768. Accuracy at 32K/16K: T-OQ 0.697, F-OQ 0.992, D-OQ 0.999 | `results/p10s1-run-2026-11-17/OUTCOME.md` sections 3 and 4; `supplement/throughput_supplement.json` |
| P10-S0: learned addressing A5-D qualified at 4,096 and 16,384 slots; OVERLOAD NOT QUALIFIED | `DIRECTION.md` section 4 (the drafter did not re-read `results/p10s0-run-2026-11-16/OUTCOME.md`) |

Everything about storage in P7, P8 and P10-S1 is simulated or arithmetic. No ArborLM record contains a physical I/O measurement. DiskANN, SPANN and FreshDiskANN are engineering precedent for keeping routing data in RAM and contents on SSD (`LITERATURE_AND_ROUTING_NOTE.md` section 2); they concern vector search, not memories trained by gradient descent, and no number from them is used here. The drafter has not re-read those papers.

**The scale gap.** The largest size with qualified learned addressing is 16,384 slots. By the P10-S1 record's arithmetic a slot is about 64 key bytes (16 × 4) plus 128 value bytes (1,024 bytes per query over 8 rows), so that store is about 3 MB. The machine has 48 GB of RAM (`sysctl hw.memsize`, read 2026-11-17). A store that needs an SSD is four to five orders of magnitude beyond any qualified size. This gap, not the device, is what stands between the project and the scientific verdict.

## 3. Entry criteria

Entry to either part is a decision by the human lead.

### 3.1 Engineering part

All of: (E1) the human lead decides the reserved question of section 11, item 1; (E2) the write budget of section 6 is approved with an endurance figure the human lead accepts; (E3) the drive's free space and health counters are recorded before any write; (E4) the cache-verification method of section 7 has passed its rehearsal, including its positive control.

### 3.2 Scientific part

All of the following, as registered and accepted outcomes at one and the same slot count N:

- **Q1, qualified access.** P10-I-S0 (ADR-0023) registers learned addressing as qualified at N without an oracle. An oracle-addressed result does not count.
- **Q2, useful capacity and utilisation.** P10-I-S1 (ADR-0024) registers a positive capacity label for the memory arm at N, with its dependence check passed, and the registered utilisation measure at N is at or above a floor fixed before observation. A store that collapses onto a few slots (P8) has nothing to read from storage.
- **Q3, real storage need.** The store at N, in the layout tested, is larger than the RAM the comparison allows it. If this is achieved only by an artificial RAM restriction, every scientific label carries `RAM RESTRICTED BY CONSTRUCTION`.
- **Q4, fair baselines and measured I/O.** Section 4's baselines run on the same device, same bytes, same cache regime, and section 7's verification passes.

On today's records Q1 holds at 16,384 slots at most (P10-S0, not P10-I-S0), Q2 does not hold (P10-S1: CAPACITY-INCONCLUSIVE, T-OQ at 0.697), and Q3 fails by orders of magnitude. **The scientific verdict is currently SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)**, and that is the line a report prints if only the engineering part runs.

## 4. Arms and baselines

| Arm | What it isolates |
|---|---|
| S-TREE: routing data in RAM, value pages on SSD, tree-shaped candidate set | The subject read path |
| S-FLAT: the same store, keys scanned in RAM, selected value pages read from SSD | The cost of not routing |
| KV: a plain key-value store on the same device, one lookup per requested row | The floor: what storage costs when the address is simply known |
| ANN: an approximate nearest-neighbour index on the same device (clustered or graph), keys and contents as its design places them | The conventional answer to the same retrieval problem |
| RAM: the same store fully in memory | The no-storage reference; parity of returned values within dtype tolerance (`docs/EXPERIMENT_PROTOCOL.md`) |

Same checkpoint or synthetic store, same queries, same page size and same cache regime for every arm; one change per comparison. Baseline implementations are fixed by the later revision. A production key-value or ANN library would be a new dependency and possibly a download, which needs an approved amendment; baselines written inside the project avoid that and are weaker evidence of fairness (section 11, item 4).

For the engineering part the store and queries are synthetic. The access pattern must be stated and justified in the later revision, because the result depends on it; at least one pattern is uniform and one is replayed from a trained checkpoint's trace scaled up, labelled as such.

## 5. Measures and label rules

- **Physical bytes read per query**, from device-level counters, with an idle-window baseline subtracted (section 7).
- **Queries per second and latency percentiles** (median, p99), on a quiet stage.
- **Task quality** (scientific part only): the entry study's registered quality measure.

Engineering label, per registered store size, cold regime, five repeats. S-TREE is positive only if it is better than **both** ANN and S-FLAT on **both** physical bytes per query and queries per second, by margins fixed before observation from rehearsal variability, in at least 4 of 5 repeats. If ANN or S-FLAT is at least as good as S-TREE on both measures in at least 4 of 5 repeats, BASELINE AT LEAST AS GOOD. Otherwise MEASURES DISAGREE. KV is printed beside every label as the floor and decides none. Across store sizes the rule is explicit: the line's label is that of the largest registered size; smaller sizes are descriptive.

Scientific label: quality at equal measured physical bytes per query against ANN and KV serving the same task, five fresh draws, both panels, at least 4 of 5; read only if Q1 to Q4 hold. Its margins are fixed by the later revision.

Rows read, pages simulated, parameters touched and any other logical count are never reported as measured I/O or as efficiency.

## 6. Storage-write budget

| Item | Proposed | Kind |
|---|---|---|
| Total bytes written by the study, all stages and attempts, failed ones included | **64 GB** | Resource cap on a physical resource; **not** extendable by the lead; only the human lead may change it |
| Share of endurance | 64 GB is about 3.2% of one full write of the drive (1.8 TiB by `df`, about 2 TB). Under an **unverified planning assumption** of 300 full drive writes over the drive's life, about 0.011% of endurance. Ceiling: 0.05% of the endurance figure the human lead accepts | Same |
| Largest single store | 16 GB | Design ceiling |
| Free space kept at all times | At least 500 GB (675 GiB were free on 2026-11-17, `df`) | Resource cap |
| Method rehearsal (section 8, stages R0 and R1) | At most 2 GB of the 64 GB | Resource cap |

The endurance rating of this drive is not in any project record, and the drafter knows of no published figure for it. The 300-writes figure is a placeholder, not a fact about the drive. The later revision records the drive's own health counters (lifetime bytes written, percentage used) before and after; reading them may need a tool that is not installed (`smartctl` is absent) or administrator access, in which case the human lead reads them. Writes are counted twice: the study's own logical bytes, and the device write-counter delta over the run, which also counts other processes and is the figure charged. A run that would exceed the cap stops before the write. Stores hold incompressible data, are preallocated once, are never rewritten in a loop, and are deleted at the end; local filesystem snapshots that would retain them are checked.

Update traffic (the FreshDiskANN-style question of in-place trained updates on SSD) is write-intensive and is **outside** this document.

## 7. Cache verification

| Cache | Treatment | Verification rule |
|---|---|---|
| OS page cache | Reads issued with caching and read-ahead disabled on the file | Device read-counter delta, minus idle baseline, divided by logical bytes requested, must be at least 0.9. Below that: CACHE NOT DEFEATED |
| Counter validity | Positive control: the same reads with caching allowed, second pass | Ratio must fall below 0.1. If it does not, the counter cannot see caching and the method is invalid |
| Drive and controller cache | Cannot be defeated from software; accounted for | Each cold pass touches a page at most once; the store is far larger than the pages touched; a repeated pass faster than the first by more than a registered factor is flagged DEVICE CACHE SUSPECTED and reported as a separate warm figure |
| Filesystem effects | Encryption, copy-on-write and fragmentation are properties of this device and stay on | Recorded in the hardware fingerprint; the same for every arm |

The figures 0.9 and 0.1 are proposals with this reason: reads are page-aligned, so physical bytes should equal or exceed logical bytes, and a tenth is a wide allowance for counter granularity and other processes. The rehearsal checks them on the reference arm (KV) first; a check the reference fails is not used. Whether the counters can be read without administrator access is unknown until the rehearsal; if they cannot, the stage is ENGINEERING NOT EVALUABLE (NO PHYSICAL COUNTER) unless the human lead provides access.

## 8. Stages

| Stage | Writes | Quiet machine | Notes |
|---|---|---|---|
| R0 device record | none | No | Free space, health counters, hardware and filesystem fingerprint |
| R1 method rehearsal | at most 2 GB | Yes, about 30 minutes | Cache verification with positive control; variability of counters and timings; fixes margins |
| Freeze, Decision 2 | none | No | |
| E1 store build | up to 16 GB per layout | No | Resumable per layout; bytes charged before each write |
| E2 read benchmark | none | Yes, about 1 to 2 hours (estimate) | 1-minute load average at most a figure fixed at the freeze (the machine idles at 1.0–1.2), and no other heavy disk activity, checked before and after each block; a failing block is repeated at most twice, then NOT MEASURED |
| S scientific comparison | within the same cap | Yes | Only if Q1 to Q4 hold |
| Analysis, report, independent recomputation | none | No | |

No throughput, latency or I/O comparison is registered on a stage that cannot be isolated. Quiet stages are scheduled with the human lead; background backup and indexing activity is part of the condition.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind | Rule |
|---|---|---|
| 64 GB written; 0.05% of endurance; 500 GB free | Resource cap (physical) | Changed only by the human lead, on projection, never on outcome values |
| Charged time, proposed 8 hours | Resource cap | Extendable on projection; a stop is PAUSED and resumable |
| Store sizes, repeats (5), access patterns | Design ceiling | Fixed at the freeze |
| Margins, 4 of 5, cache ratios 0.9 and 0.1 | Scientific threshold | Never relaxed after observation |

The study stops and returns to the human lead on: a projected write above the cap; a drive health warning or an I/O error; free space below the floor; a failed gate. NOT EVALUABLE reasons, each printed by name: PREREQUISITES NOT MET; CACHE NOT DEFEATED; NO PHYSICAL COUNTER; MACHINE NOT QUIET; BASELINE NOT FAIR (a baseline could not be built on the same bytes and cache regime); VALUE PARITY FAILED (SSD and RAM reads differ beyond dtype tolerance); THERMAL OR BACKGROUND INTERFERENCE (repeat CV above the registered rule). No limit is extended because a partial result looks close.

## 10. Cost projection (estimate; replaced by the rehearsal)

Time is small: P10-S1's supplementary throughput took 26.9 s for 30 figures in RAM (`throughput_supplement.json`). No record holds a device write or read rate, so the time to build and read 16 GB stores is a guess: minutes to an hour per layout, and 2 to 6 hours for the engineering part. The binding cost is wear: three on-device layouts of 16 GB (the tree and flat arms share one store) plus rehearsal is about 50 GB of the 64 GB cap. The rehearsal measures write amplification seen by the device counter, read and write rates, timing variability, and whether the counters are readable. The scientific part cannot be costed until a qualifying memory exists.

Seeds: proposed namespace **280001–289999**; a scan of `configs`, `studies`, `src` and `docs/decisions` in the p10-i-design worktree found no seed in 270000–289999. A freeze gate asserts disjointness from every earlier study and from ADR-0023 to ADR-0027, whose namespaces this drafter could not read.

## 11. Reserved for the human lead

1. **May the engineering part run before a neural memory is qualified at scale?**
   - For: it does not depend on any neural result; the project's motivation is storage (`docs/RESEARCH_HANDOFF.md`) and no physical measurement exists yet; cache verification on this machine is hard and is better debugged before a scientific result depends on it; it would show early whether the flat read-path throughput seen in RAM survives real I/O.
   - Against: P7-A, P7-B and P8 found no storage-locality case for the hierarchy, in simulation; the workload must be invented, and the label depends on it; the tree's quality gap (0.697 against 0.992) means the read path benchmarked may not be the one that survives P10-I-S1's routing work; it wears the human lead's working drive; a favourable engineering label is easily misread as progress on the objective.
   - Recommendation: allow only R0 and R1 (method rehearsal, at most 2 GB) early. Hold E1 and E2 until P10-I-S1's routing lane has fixed which read path is worth benchmarking.
2. **The write budget and the endurance figure.** Recommendation: 64 GB and the 0.05% ceiling, or lower.
3. **Administrator access** for health counters or device counters, if the rehearsal shows it is needed. Recommendation: the human lead runs those commands; the lead does not hold the access.
4. **Baseline implementations**: written in the project, or an approved dependency amendment for a production key-value store and ANN library. Recommendation: an amendment; fairness is the point of the baselines.
5. **Artificial RAM restriction** as a way to meet Q3. Recommendation: allowed for the engineering part only; a scientific label under it carries the qualifier.
6. **The entry decision for each part**, and approval of the revised specification. Any other device or any purchase is a separate decision and is not proposed.

## 12. Engineering requirements carried from P10

- The frozen-input set is listed file by file. Status and run notes go to a notes file outside it; nothing is committed in the frozen worktree during a run. Stages are resumable; PAUSED continues; completed layouts and blocks are not redone, which also protects the write budget.
- Every registered stage is rehearsed end to end against the frozen plan itself before Decision 2, at a reduced store size.
- Every reading rule is in the specification, including how repeats, measures and store sizes combine (section 5). The reference arm (KV) is run through every validity check in rehearsal; a check it fails is not used. The analysis, with its descriptive sections, is tested on a synthetic registry with known answers.
- No count gate on generated data: stores are "generate until built, within the write budget".
- Platform of record: the research machine (macOS 27.2.1, arm64, CPython 3.12.14, torch 2.8.0, as in the throughput supplement's environment record). Bit-exact and value-parity assertions are made on it only. Checks run locally; GitHub CI is not relied on.
- Delegated work records the model that ran it from session metadata; implementer and auditor in separate contexts.

## 13. What a later revision must fix before a freeze

Baseline implementations and versions; the synthetic access patterns and their justification; page size and layout; store sizes; margins from rehearsal; the load and CV rules; the utilisation floor of Q2; the label names of ADR-0023 and ADR-0024 used in Q1 and Q2; the counter-reading method; the accepted endurance figure; seeds; the frozen-input set.

## 14. What S5 cannot establish

- From the engineering part: anything about learning, useful capacity, neural-memory scaling or the project objective.
- Behaviour on any other drive, filesystem, operating system or under concurrent load; sustained-write or update behaviour; endurance.
- That an advantage holds beyond the tested store size, access pattern and cache regime.
- From a scientific label under `RAM RESTRICTED BY CONSTRUCTION`: that storage was needed.
- That hypotheses H3 to H5 hold in general. P7 and P8 outcomes are unchanged whatever S5 finds.

`Astra review: NOT_PERFORMED`.
