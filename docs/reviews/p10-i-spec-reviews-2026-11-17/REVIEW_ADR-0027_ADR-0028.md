# Independent specification review: ADR-0027 (P10-I-S4) and ADR-0028 (P10-I-S5)

- Date: 2026-11-17 UTC. Reviewer: the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`, as the session reports it). The drafter was Claude Fable 5.2 under the lead's brief; the reviewer wrote neither draft.
- Drafts reviewed (untracked files on branch `claude/p10-i-specs`, head `9b8d285`): `docs/decisions/ADR-0027-p10-i-s4-quality-against-cost.md` (159 lines), `docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md` (177 lines).
- Binding text: `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 4, 5, 7, 8; `LITERATURE_AND_ROUTING_NOTE.md`; `AGENTS.md`; `CLAUDE.md`; `docs/EXPERIMENT_PROTOCOL.md`.
- This is independent engineering and mathematical review. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. Scientific choices are flagged `PENDING LEAD REVIEW`; the reviewer chooses no threshold.

## Verdicts

| Draft | Verdict | Blocking | Required | Advisory |
|---|---|---|---|---|
| ADR-0027 (S4) | **NOT READY** | 1 | 12 | 7 |
| ADR-0028 (S5) | **NOT READY** | 1 | 14 | 6 |

Both blocking findings are about a label rule that, as written, can print a label more favourable to the memory (S4) or to the sparse path (S5) than the evidence supports. Both are fixable with a few sentences; the drafts are otherwise close to the direction and honest about their limits.

---

## Part A. ADR-0027 (P10-I-S4, quality against cost)

### A.1 Numbers and labels checked against the records

| Draft line | Claim | Record | Result |
|---|---|---|---|
| 28 | P4: dense beat memory 27 of 27; 198,401 trainable | `results/p4-2026-11-12/README.md` L6–7, L12, L27 (Q: 0 / 27 positive) | Matches |
| 29 | P10-S1 labels | `results/p10s1-run-2026-11-17/OUTCOME.md` L26–35; `ACCEPTANCE.md` L15–20 | Matches |
| 30 | a_use 32K/16K at run length: T-OQ 0.697, F-OQ 0.992, D-OQ 0.999 | `OUTCOME.md` L88 | Matches |
| 31 | 0.27–0.38 CPU; 1.32–1.87 madds; any-cell rule unregistered | `ACCEPTANCE.md` L27; `audit/AUDIT.md` L99 | Matches |
| 32 | +0.24 to +0.33 bits, 5 of 5, at matched compute | `OUTCOME.md` L75; `AUDIT.md` L120, L193 | Matches |
| 33 | memory lr 0.003 untuned; D-OQ calibrated | `OUTCOME.md` L90 | Matches |
| 34 | throughput T-OQ "about 10,100"; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | recomputed from `supplement/throughput_supplement.json` (medians of `qps`): T-OQ 10,106 / 10,211 / 10,132; F-OQ 19,177 / 7,292; D-OQ 107,879 / 16,768 | Matches (10,211 rounds to 10,200; nit) |
| 35 | backbone frozen, byte-level, 27,392, context 64 | `ADR-0021` L49 | Matches |
| 37 | "efficiency line was decided ... by which cost measure was read" | `AUDIT.md` L96–101: at 8K/16K the DENSE FASTER condition failed because the madds ratio exceeded 1 while the CPU ratio was below 1, i.e. both measures were required; the label was decided by the any-cell rule (`ACCEPTANCE.md` L27) | **Mischaracterised** (finding A-A1) |
| 65 | "every memory and dense addition ... (33,793 to 1,049,601)" | `RESULTS.md` L238 (H8 33,793) correct; L247: 1,049,601 is **R2**, the oracle-address reference rung (`ADR-0021` L115), not a memory or dense addition; the largest memory/dense arm is T-OQ 788,481 (L252). The conclusion (all exceed 27,392) still holds | **Mismatch** (A-A2) |
| 99 | P10-S0 200001–209999; P10-S2 220001–229999 | `ADR-0020` L269; `ADR-0022` L10 (G9 in `ADR-0021` L262 splits S2 into 220001–228999 and tests 229001–229999) | Matches |
| 99 | no seed in 270000–289999 | reviewer's scan of `configs studies src tests docs/decisions` in this worktree, excluding the two drafts: none | Reproduced |
| 109 | "the machine idles at 1.0–1.2" | No project record holds this. The supplement recorded one check, 0.998, against a limit of 1.0 (`throughput_supplement.json`, `quiet.load_averages`, `load_average_max`). At review time `uptime` read 2.93 / 3.32 / 3.71 | **Unsupported** (A-A3) |
| 128 | 49,251.2 s / 178 ≈ 277 s; 1,899.0 s / 1,866 | `OUTCOME.md` L13–14; 49,251.2 / 178 = 276.7 | Matches |
| 148 | macOS 27.2.1, arm64, CPython 3.12.14, torch 2.8.0 | `throughput_supplement.json` `environment` | Matches |

### A.2 DIRECTION.md section 4 (S4), constraint by constraint

| Constraint | Draft | Assessment |
|---|---|---|
| Entry requires credible evidence from P10-I-S3 or P10-S1 | §3, Routes A and B | Complies in substance. DIRECTION's text says "P10-S1"; the draft reads it as P10-I-S1 (ADR-0024) without saying so. P10-S1 fails either reading (§3 last paragraph). See A-A4 |
| One primary comparison at matched training computation against strong optimised alternatives | §4, §5 | Partly. "Matched" is not yet well defined (A-R1, A-R2, A-R3); the search rule contradicts itself for D+ (A-R6); KV's role in the label is ambiguous (A-R4) |
| Wall time, latency, energy, RAM, storage separate, not combined into a success claim | §5, §6 | Complies for the five named axes. Measured CPU seconds do enter the primary label (as concordance). Not wall time, but a measured time quantity gating a success label: `PENDING LEAD REVIEW` (already reserved as §11 item 3) |
| LoRA not forced where not meaningful | §4 | Complies; reasoning should be restated (A-A5) |
| No advantage from parameter counts or logical retrieval operations | §5 last paragraph | **Internal tension**: the matching variable is itself an analytic (logical) count that omits gather, top-k and index costs, i.e. counts retrieval operations as nearly free (A-B1) |

### A.3 Findings

**A-B1. BLOCKING. §5 "Combination" and "Training computation, measure 1".**
Problem. Two choices together tilt the primary label towards the memory.
(i) The matching variable is analytic multiply-adds. ADR-0021 §22 M6 counts matrix products and gather-weighted sums plus 4 per trainable parameter, but not top-k selection, sorting, indexing or memory-bound gathers. On P10-S1's records this credits sparse arms with a per-update advantage that measured CPU does not show. At 16,384 slots (8K/16K cell, same U_P for both arms): analytic multiply-adds per update T-OQ / D-OQ = 5.21e11 / 2.65e12 = **0.197**, F-OQ / D-OQ = **0.396** (`RESULTS.md` L221, L228, L252). Measured CPU per update in the rehearsal's isolated timing (descriptive; `RESULTS.md` L256 ff., unlabelled per audit finding 5): T-OQ / D-OQ = 0.01156 / 0.01204 = **0.960**, F-OQ / D-OQ = **0.768**. The cost table's CPU seconds to U_P give 0.834 and 0.787 (L221, L228, L252). So at matched analytic compute T-OQ would get about five times D-OQ's updates, while the measured cost is about equal. On a 27,392-parameter backbone the backbone term is small, so this is mostly a comparison of the additions' arithmetic intensity.
(ii) When the two measures disagree, the draft prints COST-MEASURE DEPENDENT (inconclusive). This also converts a CPU-supported ALTERNATIVE AHEAD into "inconclusive". P10-S1's own rule did the opposite: on MC-AMBIGUOUS the pair "is read in the direction that favours the comparator" and "the larger of the two multipliers is used" (`ADR-0021` L193). The draft departs from the project's precedent in the memory's favour without saying so; this is the exact pattern P10-S1 produced at 8K/16K (analytic favoured T-OQ, CPU favoured dense).
Change. (a) Make the cost combination asymmetric, mirroring the panel rule: MEMORY AHEAD only if it holds under both measures; ALTERNATIVE AHEAD if it holds under either measure; COST-MEASURE DEPENDENT only for the remaining disagreements. (b) If measure 2 is NOT MEASURED, an ALTERNATIVE AHEAD under measure 1 still stands; only the other cases become NOT EVALUABLE. (c) State the departure from, or adoption of, `ADR-0021` §5.4's MC-AMBIGUOUS rule explicitly. (d) Either extend the analytic formula to count comparisons of top-k/selection and gathered bytes, or state in §5 and §14 that the analytic measure omits memory-bound and selection work and why it is still used as the matching variable. Reword §5's last paragraph so it does not appear to forbid the very kind of count used for matching. Which measure is primary stays `PENDING LEAD REVIEW` (§11 item 3), but the draft's recommendation should cite these ratios.

**A-R1. REQUIRED. §5 "Primary budget B\*".** "The computation at which the strongest alternative meets the registered convergence rule" is not computable the same way by two people: "strongest" by what measure and at what budget (strength depends on the budget, which is circular); whether KV, which has no training computation, can be it; whether it is computed after the rate search (whose outcome depends on the budget searched). Change: define B\* as an explicit function, e.g. "max over D, D+ and FT, after their registered searches, of the cumulative measure-1 computation at which each meets the convergence rule on the calibration draws, median over the two draws"; state the order search → convergence → B\*; exclude KV; add NOT EVALUABLE (B\* NOT DETERMINED) if no alternative converges within the cap.

**A-R2. REQUIRED. §5 "Combination" ("B\* converted to measure 2").** The conversion is undefined. Measure 2 is taken on the isolated timing stage (§8), not on the training stage; cumulative CPU seconds per arm must therefore be built as updates × measured CPU per update, which the draft does not say. Change: state the formula (e.g. B\*_2 = CPU seconds the B\*-defining alternative needs to reach B\*, from its isolated per-update CPU; each arm read at the last snapshot with updates × its per-update CPU ≤ B\*_2), and state which isolated timing (per arm, per size, median of repeats) is used.

**A-R3. REQUIRED. §5 "Every arm is read at the last snapshot whose cumulative computation is at most B\*" and §7 "Snapshots on a fixed grid".** Snapshots on a fixed update grid give each arm a different shortfall below B\*; with per-update costs differing up to about 5× (A-B1), an arm can be read at well under B\*. Change: put the snapshot grid in computation units per arm (snapshots at fixed fractions of B\*), or bound the shortfall (e.g. reading must be within a stated fraction of B\*), and add NOT EVALUABLE (NO SNAPSHOT AT B\*) when an arm's first snapshot exceeds B\*.

**A-R4. REQUIRED. §4 KV row and §5 "Label under one measure".** KV is "Required where defined" but "reported beside the label". Whether KV is among "every required alternative" for MEMORY AHEAD, and among "any one alternative" for ALTERNATIVE AHEAD, can be read both ways. P10-S1 printed DICT DOMINATES ON THIS TASK and the acceptance notes that a later study must show value a plain lookup cannot provide (`ACCEPTANCE.md` L37). As written, MEMORY AHEAD can be printed on a task a dictionary solves. Change: state that KV does not enter the matched-compute rule (it has no training computation) and add a registered qualifier: if KV's quality is at least M's minus δ on both panels in at least 4 of 5 replicates, every S4 label carries `LOOKUP SUFFICIENT ON THIS TASK`, and MEMORY AHEAD is not printed without it. Which of these the human lead wants is `PENDING LEAD REVIEW`; the draft must pick one.

**A-R5. REQUIRED. §5 "MEMORY AHEAD if at least 4 of 5 replicates favour M against every required alternative".** Two readings: per alternative (for each alternative, at least 4 of 5 replicates) or joint (at least 4 replicates in each of which M is ahead of all alternatives). They give different labels. Change: write the quantifier order explicitly (the joint reading is the stricter one).

**A-R6. REQUIRED. §4 last paragraph vs D+ row.** "The same number of search cells per arm" contradicts D+'s "registered width and depth grid": D+ either gets more cells than M, or a coarser learning-rate search than the other arms. Change: state D+'s budget as the same number of cells as M, spread over the grid by a registered rule, or allow D+ more cells and say so (more cells for the alternative is the conservative direction). Also state the per-arm rate grid and that M's architecture is fixed while D+'s is searched.

**A-R7. REQUIRED. §1 label MEMORY MATCHES AT MATCHED COMPUTE.** This label is assigned whenever neither side reaches 4 of 5. That is "not separated at margin δ", not a demonstrated match; with five replicates an equivalence claim needs its own condition. A hostile reader will cite "matches" as parity. Change: rename to NOT SEPARATED AT MARGIN, or add an equivalence condition (|difference| < δ on both panels in at least 4 of 5 replicates for every alternative) and keep a separate NOT SEPARATED label for the rest.

**A-R8. REQUIRED. §5 "δ".** "Twice the between-seed SD on calibration draws" with two calibration draws is an SD with one degree of freedom per arm; its value is close to arbitrary. Also unspecified: which arm's SD, data-seed or initialisation-seed variation, which panel, pooled or not. Change: specify the estimator (e.g. pooled over arms and panels, from both draws × two initialisation seeds) and make the floor carry the weight, fixed with a reason in the revision approved before calibration. The 4 of 5 figure is `PENDING LEAD REVIEW` (one-sided sign probability of at least 4 of 5 under no difference is 6/32 = 0.19).

**A-R9. REQUIRED. §3 Route B, clauses B1 and B2.** (a) P10-S1's capacity labels are step labels over a pair of cells (`ADR-0021` §8.2–8.4), not cell labels, so "a positive capacity label ... at one and the same cell" is not computable if ADR-0024 keeps that structure. (b) B2 "no label that places the dense control ahead" is vacuously met if the dense comparison is not run, NOT EVALUABLE, MC-SHORT or PANEL-DISAGREE at that cell. (c) "One arm at one cell" out of about 4 arms × 7 cells is a multiplicity choice made after observation. Change: (a) say "for one step, S4 runs at the larger cell of that step"; (b) require a registered dense comparison at that cell that is positive or within margin, as A2 does; (c) fix in advance which cell S4 uses if more than one qualifies (e.g. the largest).

**A-R10. REQUIRED. §9 NOT EVALUABLE "an alternative's search ends at a boundary of its grid".** A search ceiling is a design ceiling (DIRECTION §5); closing the study on it without a written extension rule is the case the human lead objected to ("we close expiriment due to self impose caps"). Change: add a rule such as "extend the grid by one step past the boundary, at most twice, within the hour cap"; NOT EVALUABLE only if the boundary persists.

**A-R11. REQUIRED. §8 isolated timing and §5 measure 2 NOT MEASURED.** "Repeated at most twice, then NOT MEASURED", and NOT MEASURED makes the whole study S4 NOT EVALUABLE. Failure of a quiet window is a scheduling condition on the human lead's working computer, not a scientific outcome; per DIRECTION §5 rule 1 it should be PAUSED and rescheduled. Change: a failed quiet block is PAUSED and rescheduled with the human lead; NOT MEASURED only after a number of rescheduled attempts fixed in advance. Classify the retry count as a design ceiling in the §9 table. Also make "a quiet machine" computable: load threshold, minimum idle window before a block, and the measure taken (§9 lists the CV rule and load figure as "to be fixed"; that is acceptable only if the table names them).

**A-R12. REQUIRED. §9 limits table, against DIRECTION §5.** Not classified: retries of quiet blocks; the reference-check tolerance (scientific threshold); the load-average figure and CV rule; the convergence rule's parameters; the D+ grid bounds. Change: add each with its kind and rule.

**A-A1. ADVISORY. §2 second lesson.** Replace "and by which cost measure was read" with the record's wording: the label was decided by an unregistered any-cell rule; at 8K/16K the measures disagreed (`ACCEPTANCE.md` L27).

**A-A2. ADVISORY. §4 LoRA paragraph.** Fix the range to "33,793 to 788,481 (memory and dense arms; R2, a reference, has 1,049,601)". Restate the reason for NOT APPLICABLE on capability, not parameter counts: on this backbone full fine-tuning contains every LoRA solution and costs about the same per update (both need the backbone backward pass), so LoRA cannot be a stronger alternative than FT. The reviewer agrees with NOT APPLICABLE on that basis. Note that FT on a memorisation task with 27,392 parameters is weak by construction, so beating FT is not informative on Route B's task; the label must not be read as "memory beats fine-tuning" in general (§14 already nearly says this).

**A-A3. ADVISORY. §8 "(the machine idles at 1.0–1.2)".** Remove or source it. Recorded: one check at 0.998 (supplement). Observed at review: 2.93 / 3.32 / 3.71 with other sessions running. The machine has 18 cores (`hw.ncpu`), so a 1-minute load threshold near 1 is meaningful but may be rarely met.

**A-A4. ADVISORY. §3.** Say explicitly that DIRECTION §4 names "P10-S1" and that the draft reads it as "P10-I-S1 (ADR-0024)"; P10-S1 fails under either reading. `PENDING LEAD REVIEW` for the reading.

**A-A5. ADVISORY. §6 Peak RAM and stored bytes.** In P10-S1 peak RSS was 320–376 MB per process (`RESULTS.md` L324–477), dominated by the Python and torch runtime; per-arm differences of a 27,392-parameter model will be invisible. Report also the analytic bytes of parameters plus optimiser state; define whether "stored bytes" includes optimiser state.

**A-A6. ADVISORY. §5 measure 2 and §13.** Single-thread CPU seconds on Apple silicon depend on whether the scheduler places the thread on a performance or efficiency core, and on power source (the machine is a laptop, `hw.model` Mac17,6, battery present). Record core placement or QoS, power source and Low Power Mode with every timing block.

**A-A7. ADVISORY. §4.** The literature note names product-key memory as "a serious alternative baseline" (`LITERATURE_AND_ROUTING_NOTE.md` §2). Whether S4's alternative list should include it, at least on Route A, is `PENDING LEAD REVIEW`.

### A.4 Other checks requested

- **Entry criteria (item 5).** Computable on registered outcomes once ADR-0024 and ADR-0026 label names exist; descriptive figures are excluded explicitly. P10-S1 cannot satisfy them (no route names P10-S1; and §3 shows it fails anyway). Subject to A-R9.
- **Thresholds favouring the memory (item 4).** A-B1 (matching variable and disagreement rule). δ's estimator (A-R8) has no direction bias but no stated reason for "twice". 4 of 5 is stated as a proposal. The asymmetric panel rule is kept (good).
- **Missing NOT EVALUABLE cases (item 10).** B\* NOT DETERMINED (A-R1); NO SNAPSHOT AT B\* (A-R3); analytic formula check against a counted run fails (M6 test); non-finite training in any arm, including FT; measure-2 timing UNSTABLE under the CV rule (distinct from not measured); platform change between stages; entry-route label renamed or withdrawn between entry and freeze.
- **Overclaim (item 9).** MEMORY MATCHES (A-R7). The label names should carry the scope sentence of §4 ("one frozen 27,392-parameter backbone; ...") wherever printed, not only in §4.

---

## Part B. ADR-0028 (P10-I-S5, physical SSD-backed memory)

### B.1 Numbers and labels checked against the records

| Draft line | Claim | Record | Result |
|---|---|---|---|
| 31 | P7-A CONCENTRATION-ONLY both kinds; "No NVMe experiment on these checkpoints is proposed" | `ADR-0013` L279, L283 | Matches |
| 32 | P7-B WITHIN 10% ... REPLICATED; class N | `ADR-0014` L373 | Matches |
| 33 | P8 INCOMPLETE 55 of 60; no LOCALITY-POSITIVE; every locality term a concentration term | `results/p8-2026-11-14/SUMMARY.md` L3, L23, L47 | Matches |
| 34 | P8 supplement 5 of 5; C04, C05 QUALITY-FAILED; P8 INCOMPLETE | `results/p8-supplement-2026-11-14/README.md` L3, L10 | Matches |
| 35 | P10-S1 storage traffic: arithmetic, value pages only, keys in RAM, 1,024 bytes/query at 8 rows | `RESULTS.md` L497–533 | Matches |
| 36 | throughput figures | recomputed from JSON (see A.1) | Matches |
| 36, 148 | "Accuracy at 32K/16K: T-OQ 0.697, F-OQ 0.992, D-OQ 0.999" citing OUTCOME §§3–4 | `OUTCOME.md` L88: these are mean a_use **at the run length**; at the registered read point U_P they are 0.401, 0.916, 0.957. §3 holds no accuracy | **Read point omitted; wrong section cited** (B-R13) |
| 37 | P10-S0 A5-D qualified 4,096 and 16,384; OVERLOAD NOT QUALIFIED | `results/p10s0-run-2026-11-16/OUTCOME.md` L7, L13 | Matches; omits that qualification was at 0.5 facts per slot (L7) and A5-D is NOT DISTINGUISHED FROM A0 at 16,384 (L12) (B-A2) |
| 41 | slot ≈ 64 key + 128 value bytes; store ≈ 3 MB at 16,384 | `RESULTS.md` L508 (K × 16 × 4), L533 | Matches: 16,384 × 192 B = 3.15 MB |
| 41 | 48 GB RAM | `sysctl -n hw.memsize` = 51,539,607,552 B = 48 GiB | Matches |
| 41 | "four to five orders of magnitude" | 48 GiB / 3.15 MB = 16,384 ≈ 10^4.2 | "About four" is accurate (B-A3) |
| 93, 95 | 1.8 TiB drive; 675 GiB free | `df -k`: 1,948,404,040 KiB = 1.81 TiB; available 708,292,508 KiB = 675.5 GiB; `diskutil info /` container 2.0 TB | Matches |
| 93 | 64 GB ≈ 3.2% of one drive write; 0.011% at 300 drive writes | 64 / 2,000 = 3.2%; 64 / 600,000 = 0.0107% | Matches |
| 111 | counters' readability without admin "unknown until the rehearsal" | `ioreg -c IOBlockStorageDriver -r -k Statistics` returned per-driver `Bytes (Read)` and `Bytes (Write)` without administrator access at review time; `smartctl` is not installed | Partly answerable now (B-R5) |
| 140 | 26.9 s for 30 figures | `throughput_supplement.json` `seconds` 26.918 | Matches |

### B.2 DIRECTION.md section 4 (S5), constraint by constraint

| Constraint | Draft | Assessment |
|---|---|---|
| Two verdicts, never combined | §1 | Complies. No sentence joins them. §11 item 1 "the flat read-path throughput" is ambiguous with arm S-FLAT (B-A4) |
| Synthetic benchmark not evidence of neural-memory scaling | §1, §14 | Complies |
| Advantage requires qualified access, utilisation, fair baselines, measured physical I/O | §3.2 Q1–Q4 | Partly. Q1 and Q2 may be met by two different systems from two studies (B-R2); the utilisation floor's timing permits choosing it after seeing ADR-0024 (B-R3); "physical I/O" is block-layer host I/O (B-R5); fairness lacks result parity and RAM parity (B-B1) |
| Cache verification, write budget, NOT EVALUABLE in the design | §6, §7, §9 | Present; technically incomplete (B-R4 to B-R8) |
| No hardware purchase, no large write-intensive benchmark | header, §11 item 6 | Complies; nothing implies a purchase. The benchmark stage (E2) is read-only; whether 50–64 GB of store builds counts as "large" is `PENDING LEAD REVIEW` |

### B.3 Findings

**B-B1. BLOCKING. §5 engineering label; §4 arms.**
Problem. The engineering label compares physical bytes per query and queries per second across S-TREE, S-FLAT and ANN without requiring that they return the same results or hold the same amount in RAM.
(i) Result parity. VALUE PARITY in §9 compares an arm's SSD read with its own RAM read; nothing requires S-TREE, S-FLAT and ANN to retrieve the same candidates. A tree that examines fewer candidates reads fewer pages by construction, whether or not it finds the right rows. This is P7-A's lesson (CONCENTRATION-ONLY: "lower page reads come from using fewer rows", `ADR-0013` L283) moved onto a device, and the draft cites P7-A without carrying it into the rule. As written, SPARSE PATH READS LESS AND IS FASTER can be printed for a read path that returns worse results.
(ii) RAM parity. S-TREE and S-FLAT keep routing data and keys in RAM; ANN places "keys and contents as its design places them". An arm that keeps more in RAM reads less from SSD. At the planned scale this is not small: 64 key bytes per slot is a third of a 192-byte slot, so a 16 GB store carries about 5 GB of keys.
Change. (a) Register a result-quality condition for every arm at every size: recall at k against exact search on the same store and queries, at or above a figure fixed before observation; an arm below it is not compared (ENGINEERING NOT EVALUABLE (RECALL NOT MATCHED)) or is compared only at a candidate count that reaches it. Report recall beside every bytes and QPS figure. (b) Fix a common resident-RAM budget per arm (bytes of keys, routing data and index held in RAM), record the actual residency, and compare at equal budget; or print the RAM held by each arm in the label line and forbid the label when residencies differ by more than a registered factor. (c) Fix the I/O primitive, block size, thread count and queue depth to be the same for all arms; QPS at queue depth 1 and at a higher depth are different measurements.

**B-R1. REQUIRED. §5 engineering label quantifiers and MEASURES DISAGREE.** (a) "Better than both ANN and S-FLAT on both measures ... in at least 4 of 5 repeats": per comparison, or jointly per repeat? (b) BASELINE AT LEAST AS GOOD has no margin ("at least as good"), while the positive label has one. (c) Any case that is neither (for example S-TREE better on both measures but within the margin) is labelled MEASURES DISAGREE although the measures agree. Change: write the quantifier order; give the negative its margin or define "at least as good" as "not worse by the margin"; add NOT SEPARATED AT MARGIN for the remainder; keep MEASURES DISAGREE for real disagreement between bytes and QPS.

**B-R2. REQUIRED. §3.2 Q1 and Q2.** Q1 comes from P10-I-S0 (learned addressing, e.g. A5-D) and Q2 from P10-I-S1 (whose store results so far carry `STORE ONLY; ORACLE-ADDRESSED`). Both "at the same N" can be met by two different systems, neither of which is a trained memory that is both qualified in access and useful in capacity. DIRECTION §2: "No study's result substitutes for another's." Change: require that one trained system satisfies both (Q2's positive capacity label obtained with Q1's learned addressing, not an oracle), or add a reference check in S5 itself on calibration draws that the composed system meets both, with SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET) otherwise. Also fix the step-versus-cell issue as in A-R9(a).

**B-R3. REQUIRED. §3.2 Q2 "a floor fixed before observation" and §13.** Before observation of what? If the floor is fixed in the later revision of ADR-0028, ADR-0024's utilisation figures may already be on record, and the floor could be chosen to admit or exclude them. Change: fix the utilisation measure and floor in this ADR now (or name the ADR-0024 quantity and threshold) before any P10-I-S1 registered seed is observed, with the reason for the figure.

**B-R4. REQUIRED. §7 OS page cache: the design has no means of reaching a cold state.** On macOS the per-file controls are `fcntl(F_NOCACHE)` and `fcntl(F_RDAHEAD, 0)`. To the reviewer's knowledge (not tested here, and to be confirmed in R1), F_NOCACHE stops new caching for that descriptor but does not evict pages already in the unified buffer cache, and unaligned requests can still be cached. The stores are written by the study (E1) through the cache, the 16 GB ceiling is a third of the 48 GiB of RAM, and the R1 positive control deliberately loads pages into the cache. `purge` exists at `/usr/sbin/purge` but, to the reviewer's knowledge, requires administrator rights on current macOS (not run). The 0.9 ratio would detect the failure, so the method is a sound detector but not a working procedure. Change: build stores with F_NOCACHE and page-aligned writes; run the positive control last or on pages no cold pass uses; state how a cold state is reached after a pause or a reboot; require every arm, including any library baseline, to use the same read primitive (pread with F_NOCACHE), because a memory-mapped baseline cannot be made cold this way; R1 must show the cold ratio on the exact build-then-read path.

**B-R5. REQUIRED. §5 "Physical bytes read per query, from device-level counters" and §7 counter validity.** The counters the reviewer could read without administrator access are IOKit `IOBlockStorageDriver` `Statistics`, which count bytes the OS issued to the block device, since boot, for all processes, including swap, Spotlight and backups. They are not NAND traffic and not per process. Measured at review time on the internal driver: 20-second background of 0.30 MB/s read and 1.01 MB/s write with load average about 3; since boot (uptime 680,100 s) 3,100,593,311,744 bytes read and 3,836,560,117,760 bytes written, i.e. averages of 4.56 MB/s read and 5.64 MB/s write (about 487 GB/day; this window includes registered P10 runs, so it is not "ordinary use"). Change: (a) name the measure as "block-device bytes requested by the OS (IOKit), system-wide", never "NAND" or "physical media"; (b) give the cache ratio an upper bound as well (for example at most 1.1 times the layout's expected amplification) so that other processes' reads cannot pass as cold reads and inflate one arm's bytes; (c) evaluate per-process counters (`proc_pid_rusage` `ri_diskio_bytesread` / `ri_diskio_byteswritten`, readable for the study's own process; behaviour to be verified in R1) as the primary counter, with the IOKit delta as a cross-check; (d) state that the 0.9 floor still allows up to 10% cache hits per arm, which favours an arm with concentrated access (again P7-A's mechanism). The figure is `PENDING LEAD REVIEW`; a per-arm ratio must be printed and arms whose ratios differ by more than a registered amount are not compared.

**B-R6. REQUIRED. §6 "the device write-counter delta over the run ... is the figure charged".** The device counter includes every process on the human lead's working computer. At the sampled 1.01 MB/s, background alone is about 3.6 GB per hour; at the since-boot average it is about 20 GB per hour. Over the proposed 8 charged hours this is 29 to 160 GB, so the 64 GB cap could be exhausted by the human lead's own activity, and "a run that would exceed the cap stops before the write" cannot be projected for background writes. Change: charge the study's own bytes (logical bytes written, cross-checked by per-process write counters) against the cap; record the device delta only over the study's write windows and report the remainder as background. Keep the drive-health counters as before-and-after records.

**B-R7. REQUIRED. §6, §8 E1 and §12: stores on a working machine.** Not addressed: Time Machine would back up 16 GB stores (heavy reads on this SSD during a benchmark and writes elsewhere); local APFS snapshots taken while stores exist keep them after deletion (`tmutil listlocalsnapshots /` currently lists none and needs no administrator access); Spotlight indexing of new files; iCloud-synced folders. Change: store directory outside synced folders, excluded from Time Machine and Spotlight (for example a `.noindex` directory; exclusion method verified in R0), checked before E1 and before each E2 block; stores persist across PAUSED and their bytes are held against the free-space floor until deletion.

**B-R8. REQUIRED. §7 drive cache row vs §4 replayed traces and §5 five repeats.** "Each cold pass touches a page at most once" contradicts the replayed-trace pattern (§4), in which pages repeat across queries; and five repeats over the same store and queries touch the same pages again, so repeats 2–5 may hit controller or SLC caches. Newly written data may also read faster for some time after E1. DEVICE CACHE SUSPECTED has no stated effect on the label. Change: disjoint page sets per repeat (or per-repeat query sets drawn from disjoint regions), a registered settling interval after E1, arm order randomised within each block, and a rule that a block flagged DEVICE CACHE SUSPECTED does not enter the 4 of 5 count.

**B-R9. REQUIRED. §3.1 E3 and §6 health counters.** Lifetime bytes written and percentage used are not readable with the tools present: `smartctl` is absent, installing it is a download needing approval, and `system_profiler` reports only a SMART status (reviewer's knowledge; not run). E3 as written may therefore be unmeetable without a decision. Change: state in E3 and §11 item 3 that reading these counters needs a tool install or the human lead's action, and that E3 fails without one.

**B-R10. REQUIRED. §3.1 entry vs §8 R0–R1 vs §11 item 1.** E4 requires R1 to have passed, but R1 writes up to 2 GB to the drive and is part of the study; §11 recommends running R0–R1 early. Change: add an explicit E0, "the human lead authorises R0–R1 as a method rehearsal (at most 2 GB written)", separate from entry to E1–E2, so that no write happens on the programme approval alone.

**B-R11. REQUIRED. §3.2 Q3 and §6 ceilings.** With a 16 GB store ceiling, a 64 GB write cap and 48 GiB of RAM, Q3 can only ever be met by artificial RAM restriction under this ADR. Every scientific label would carry `RAM RESTRICTED BY CONSTRUCTION`, and §14 says such a label cannot establish that storage was needed; i.e. the scientific part, as capped, cannot answer its own question ("at a scale where storage is really needed"). Change: say this explicitly in §3.2 and §11 item 5, and define what "RAM restriction" means on macOS without administrator access (there is no per-process page-cache limit; in practice it is F_NOCACHE reads).

**B-R12. REQUIRED. §5 scientific label.** "Quality at equal measured physical bytes per query" is not computable: bytes per query is a measured outcome, not a setting, so equality needs a sweep (for example over candidate counts) and an interpolation or matching rule. Also unstated: what KV is given as the address in the scientific part (an oracle address makes KV unbeatable; an exact key lookup is a dictionary, which P10-S1 found dominant), why S-FLAT is absent from the scientific baselines, and the conditions for INCONCLUSIVE. Change: write the matching rule, the quantifiers (as B-R1), KV's address source, and the INCONCLUSIVE condition; this can stay conditional, but the structure must be fixed now.

**B-R13. REQUIRED. §2 L36 and §11 L148: read point.** Add "at the run length" to the 0.697 / 0.992 / 0.999 figures, give the U_P figures (0.401 / 0.916 / 0.957) beside them, and cite `OUTCOME.md` §4 only. The literature note's addendum (§5.1) shows the tree comparison reverses between U_P and the run length; the reserved question in §11 item 1 should not rest on one read point.

**B-R14. REQUIRED. §9 limits and stop rules against DIRECTION §5.** (a) The stop on the write cap and on the free-space floor is not labelled PAUSED (rule 1); say so, resumable from the last completed layout. (b) A failed quiet block "repeated at most twice, then NOT MEASURED" ends the engineering part as MACHINE NOT QUIET on a scheduling condition: make it PAUSED and rescheduled, with the number of reschedulings fixed in advance (as A-R11). (c) Unclassified: the 16 GB single-store ceiling (in §6 but not §9), the DEVICE CACHE "registered factor", the idle-baseline window, quiet-block retries, the recall floor of B-B1.

**B-A1. ADVISORY. §8 E2 "no other heavy disk activity".** Not operational. Use the IOKit or per-process counters: background read and write rates over a pre-block window below figures fixed at the freeze. Also record power source and Low Power Mode (the machine is a laptop: `hw.model` Mac17,6, internal battery present, on AC at review time), and thermal state (`pmset -g therm`); keep the machine awake during blocks (`caffeinate`).

**B-A2. ADVISORY. §2 P10-S0 row.** Add that A5-D's qualification was at 0.5 facts per slot and NOT DISTINGUISHED FROM A0 at 16,384 (`results/p10s0-run-2026-11-16/OUTCOME.md` L7, L12); both bear on Q1 and on utilisation (Q2). Remove "the drafter did not re-read" once checked.

**B-A3. ADVISORY. §2 L41.** "Four to five orders of magnitude" → "about four orders of magnitude (48 GiB / 3.15 MB = 16,384)".

**B-A4. ADVISORY. §11 item 1, "For" bullet.** "Whether the flat read-path throughput seen in RAM survives real I/O" reads as arm S-FLAT; write "whether the tree's constant read-path throughput in RAM (about 10,100 queries/s at batch 1, 1,024 to 16,384 slots) survives real I/O". Also note under "Against" that a favourable engineering label can only be about the read path tested, which the routing work may change.

**B-A5. ADVISORY. §6 endurance.** Context for the human lead, descriptive: the internal driver's counter shows about 3.8 TB written in the 7.9 days since boot, so 64 GB is a small fraction of this machine's routine writing; the reviewer judges the wear risk of 64 GB negligible whatever the drive's unpublished rating, provided B-R6 (charging) and B-R7 (backups, snapshots) are fixed. Apple does not publish an endurance rating for this drive to the reviewer's knowledge; the 300-writes placeholder is correctly marked unverified.

**B-A6. ADVISORY. §1 engineering question and §5 "cold regime".** Cold-only reading measures the worst case and removes any benefit of caching hot pages that a deployed system would have; say why cold is primary and print warm figures descriptively for all arms under the same rule.

### B.4 Other checks requested

- **Never combined (item 8).** Holds in §1, §5, §14. No label or sentence feeds one verdict into the other. Recommend adding to §5: "No report sentence cites the engineering label in the scientific line's paragraph or vice versa", for a hostile reader.
- **Entry criteria (item 5).** The scientific part is computable on registered outcomes once ADR-0023/0024 names exist; P10-S1 cannot meet it (Q1 and Q2 name P10-I studies; §3.2 last paragraph). The engineering part's entry depends on the human lead's reserved decision, as DIRECTION §8 requires; see B-R10 for the rehearsal writes.
- **Thresholds favouring the sparse path (item 4).** The 0.9 cache floor (B-R5 d); the missing recall and RAM parity (B-B1). The 0.1 positive-control ceiling and 4 of 5 have stated reasons or are marked as proposals.
- **Missing NOT EVALUABLE cases (item 10).** RECALL NOT MATCHED (B-B1); RAM RESIDENCY NOT MATCHED (B-B1); WRITE BUDGET EXHAUSTED before all layouts (PAUSED first; NOT EVALUABLE only if the human lead declines more); HEALTH COUNTERS UNREADABLE (B-R9); COUNTER RESET (reboot or sleep inside a block; IOKit counters are since boot); POWER OR THERMAL STATE (battery, Low Power Mode, thermal pressure); STORE RETAINED BY SNAPSHOT; for the scientific part, NO MATCHING POINT AT EQUAL BYTES (B-R12).
- **Seeds.** 280001–289999 is disjoint from ADR-0027's 270001–279999 and, per the reviewer's scan, from every range in `configs studies src tests docs/decisions`. ADR-0023 to ADR-0026 do not exist on `main`, `claude/p10-i-design` or `claude/p10-i-specs`, so their ranges cannot yet be checked by anyone; the freeze gate the drafts require is the right control.

---

## Commands and environment

Environment: macOS 27.2.1 (build 26B131), Darwin 27.2.0, `hw.model` Mac17,6, 18 logical CPUs, 48 GiB; system `python3` 3.15.1, run with `-I`; no project code or `arborlm.*` module imported. All commands read-only, run from the worktree root on 2026-11-17 between about 21:00 and 21:22 UTC.

- Record reads: `Read` of the two drafts, `DIRECTION.md`, `LITERATURE_AND_ROUTING_NOTE.md`, `AGENTS.md`, `results/p10s1-run-2026-11-17/{OUTCOME,ACCEPTANCE}.md`, `RESULTS.md` L210–300 and L495–540; `grep -n` over `RESULTS.md`, `audit/AUDIT.md` (L85–125 by `sed`), `ADR-0013`, `ADR-0014`, `ADR-0020`, `ADR-0021`, `ADR-0022`, `ADR-0009`, `results/p4-2026-11-12/README.md`, `results/p8-2026-11-14/SUMMARY.md`, `results/p8-supplement-2026-11-14/README.md`, `results/p10s0-run-2026-11-16/OUTCOME.md`.
- Throughput recomputation: `python3 -I -c` loading `supplement/throughput_supplement.json` and taking `statistics.median` of each `results[arm|slots]["1"]["qps"]`; compared with `median_qps` and with `OUTCOME.md` L45–59 (all 15 batch-1 figures equal).
- Ratios: `python3 -I -c` arithmetic on `RESULTS.md` L221, L228, L252 (analytic multiply-adds and CPU seconds to U_P) and the `cpu_per_update` block after L256.
- Seed scan: `grep -rn -E "\b2[78][0-9]{4}\b" configs studies src docs/decisions` (excluding the two drafts) and the same over `tests`: no hits.
- Sibling ADRs: `git ls-tree --name-only <branch> docs/decisions/` for `claude/p10-i-design`, `claude/p10-i-specs`, `main`: no ADR-0023 to ADR-0028 committed.
- Device facts: `sysctl -n hw.memsize hw.model hw.ncpu`; `df -k / /System/Volumes/Data`; `which smartctl purge iostat fs_usage`; `ioreg -c IOBlockStorageDriver -r -w0 -k Statistics`; `diskutil info /`; `pmset -g batt`; `tmutil listlocalsnapshots /`; `uptime`.
- Background I/O sample: scratchpad script `iosample.py` (two `ioreg` reads 20.0 s apart, run under `timeout 60`); result on the internal driver: 0.30 MB/s read, 1.01 MB/s write.

Failed or empty checker attempts, kept for the record: (1) a search for ADR-0023 to ADR-0026 drafts in the `p10-i-design` worktree returned exit code 1 (no such files); (2) `grep ... results/p7a-2026-11-13/*.md` and `results/p7b-2026-11-13/*.md` failed with "no matches found" because those result folders hold no Markdown; the P7-A and P7-B outcomes were then verified in `ADR-0013` §15 and `ADR-0014` §16 instead. The reviewer's own first reading that "idles at 1.0–1.2" might come from the throughput supplement was wrong; the supplement holds 0.998 and a limit of 1.0, and the only "1.0-1.2" in the repository is an unrelated operator table in `docs/reviews/p5-claude-review-2026-11-13/`.

Nothing was run that trains, benchmarks, writes to a store, or changes a setting. No file other than this report was created or edited, and no git write was made.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
