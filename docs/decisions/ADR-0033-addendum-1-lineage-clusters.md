# ADR-0033 addendum 1 — lineage clusters: the strict reading, the cluster partition, the count reached

**Status: DRAFT — NOT APPROVED. Not reviewed. Nothing in this document is registered, and nothing in it authorises implementation, registration of a lineage, a package install, a download, a model run or a decision.**

- Date: 2026-11-25 (Panama time). Drafted by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) on the coordinator's brief. The drafter read records and code only, ran one stdlib arithmetic script on the locked environment, ran no model, downloaded nothing, delegated nothing and made no git write.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result.
- **What is amended.** `docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md`, revision 4, SHA-256 `7719f6d456113385a44dac37abeb28b36d6d9fb7eb569a65c7e6ccaaf19ec90b` ("ADR-0033"). That file is not edited. Line numbers below are lines of that file at that hash. Where this addendum and ADR-0033 differ, the addendum would govern once approved; until then ADR-0033 governs as written.
- **What it writes down.** The human lead's words "Adopt all five" of 2026-11-25, recorded on branch `claude/m0-impl` at commit `f122e6bc` in `docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS_3.md` (SHA-256 `d0da7d11…c6286`), with his two earlier answers in `HUMAN_LEAD_WORDS.md` and `HUMAN_LEAD_WORDS_2.md` of the same folder, and the lead's rulings in `LEAD_RULINGS_2.md` (SHA-256 `e2e4128a…b123`). The five answers set a direction. This text is the drafter's rendering of them; where it goes beyond his words it says so (section 12).
- **[KNOWN] Thresholds are fixed before observation.** No model has been loaded, run or scored on any M0 item. No package that would run a model is installed and no model or dataset has been fetched for M0. Everything that shaped this addendum is a property of item generators (audits of lineage maps, wordings, answer keys, heuristic tells, capacity). **No margin, band, alpha, power value, tolerance, pool size or grid of ADR-0033 is changed here.**

## 0. Terms

| Term | Meaning here |
|---|---|
| Shape | One registered generator function with one question form (ADR-0033 calls it a "rule shape") |
| Lineage (as written) | A group of shapes that an author wrote as one "hand-written base rule" |
| Procedure | The algorithm a solver must carry out on an item's content to obtain the answer |
| Cluster | A set of lineages that share one procedure under the test of section 1. The unit for G, for every interval and for the partition |
| Global cluster | A cluster identity that holds across the four private evaluations R1, R2, M1 and C1 (section 3) |
| Map of record | The file that assigns every written lineage to a global cluster, fixed in G-gen's record of record |
| Part A, part B | The teaching-eligible and the held-out halves of an evaluation (ADR-0033 section 6.4) |
| G, G_e | The number of clusters with at least one registered lineage in one part of one private evaluation |
| NOT REGISTERED | A written lineage that enters no pool (section 8) |
| Tell | A property of an item's text from which a rule that does not carry out the procedure gets the answer right, or rules answers out, more often than chance |
| τ | The between-cluster standard deviation of a paired difference (ADR-0033 section 8) |

## 1. Answer 1: "distinct solution procedure" is read strictly

**Amended sentence** (section 6.2, line 268): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part."

**Replacement reading.**

1. **The test.** Two lineages are one cluster when one algorithm, written once, solves every item of both after any combination of: renaming entities; changing the setting or surface frame; changing the order of presentation; changing parameter values (sizes, depths, number systems, moduli, tie-break rules, which position or extremum is asked); negating or inverting the question; or asking for a different read-out of the same computed state. Two lineages are distinct only if the algorithm, the data structure it maintains, or the dependency structure of its steps differs. A difference of topic, vocabulary, answer type or evaluation does not make two lineages distinct.
2. **The unit.** "The cluster, for G and for every bootstrap, is the lineage" is read as: the cluster is the set of written lineages that are one procedure under item 1. G is the number of clusters per part that have at least one registered lineage. This is the merge that line 270 already prescribes ("Such a pair is merged into one lineage before the record"), applied to every pair, not to a sample.
3. **Who decides.** The map is made by an `arbor-auditor` context that wrote none of the lineages, from code and rendered items, with its judgement hashed before it reads any author's notes. **The auditor's map governs.** Where an author disagrees with a merge, the disagreement is written beside the map with its reasons; it does not un-merge. Where the auditor is unsure, the pair is listed as borderline and is not merged; borderline pairs are reported with the count they would give if merged ("strictest"). Over-counting clusters is the harmful error, so a pair the auditor judges the same is merged even if every author disagrees.
4. **The map of record** is the auditor's map after the re-audit of the four fix rounds (commits `e11ce14d`, `1bffd8cb`, `163fa419`, `5cbd9200` on `claude/m0-impl`), completed by the cross-evaluation step of section 3. The counts quoted to the human lead (27, 38, 22, 29 for R1, R2, M1, C1) are counts before that re-audit. They are not registered numbers and appear in this addendum only as the order of magnitude used for the arithmetic of section 6.
5. **The check of line 270** ("The auditor reads one rendered item from each of 50 random pairs of lineages in one family and records any pair that is the same procedure") is replaced by: the auditor judges every pair of written lineages within an evaluation, across families and across parts, and records the judgement per pair; and every pair across evaluations that section 3 requires. The 50-pair sample is no longer the check.

## 2. Answer 2: what a code-tracing item's procedure is

**Amended text.** Section 6.2, the C1 row (line 264), and section 6.3 (line 283: "C1 measures reading and tracing code. It does not measure writing it"). Neither says what a C1 item's "solution procedure" is.

**Replacement reading.**

1. For C1 the procedure of a lineage is **the algorithm of the program the item shows**, not the act of stepping through statements. (Under the other reading every C1 item is one procedure and C1 has one cluster.) The test of section 1 applies to the programs' algorithms.
2. **A lineage is admissible only if the printed line cannot be obtained without following the program's state.** If a closed formula or a library call on the program's literals gives the printed line on every item of a shape (the audit found this at rate 1.00 for five lineages), that shape is replaced by a **traced-state shape**: a program of the same algorithm whose printed line is a function of intermediate state that the closed formula does not give (for example the state after a stated number of iterations, or a count of an internal event). A traced-state shape belongs to the cluster of the lineage it replaces. The replaced shape is kept on file and is NOT REGISTERED.
3. Whether a traced-state shape meets item 2 is judged by the auditor in the re-audit and measured by the battery of section 7. A lineage for which no admissible shape exists is NOT REGISTERED.
4. Section 6.3 is otherwise unchanged. C1 is still called code tracing, never coding.

## 3. Answer 3: one algorithm, one part, across evaluations

ADR-0033 does not address the same algorithm appearing in two evaluations. **New rule, added to section 6.4 after item 1 (line 300).**

1. **Global cluster identity.** The four per-evaluation maps are joined into one graph whose nodes are all written lineages of R1, R2, M1 and C1. Two nodes are linked if the auditor judges them one procedure under section 1, whether they are in the same evaluation or not. A C1 lineage and a lineage of another evaluation are linked when the C1 program's algorithm is the other lineage's procedure. **A global cluster is a connected component of this graph.** Its identity is the lexicographically smallest lineage id it contains. Links the auditor judges weaker than "the same procedure" are listed as borderline and do not join components.
2. **Consistency inside an evaluation.** Sameness is transitive. If a component joins two lineages of one evaluation that that evaluation's own map kept apart, they are one cluster of that evaluation, and its G falls by one. The auditor may instead withdraw a named link, with written reasons, before the map of record is fixed. Nobody else may.
3. **The rule.** Every global cluster is assigned to exactly one part, A or B, for all four evaluations at once (section 4). No lineage of a part-B global cluster, in any evaluation, registered or not, and no item, template or program of its procedure, may ever be used for teaching. This replaces "no teaching item, template or family of part B" in line 300 and "no teaching code may use part-B families, checked in M1.5 by template signature" in line 419: the check in M1.5 is by global cluster, by procedure as well as by template signature.
4. **The map** is one file, `studies/m0/manifests/cross_evaluation_procedures.json`, frozen at F by hash. It lists every lineage, its evaluation, its global cluster, every link with the auditor's reason, every borderline pair, and the registration status of each lineage.
5. **Limit, stated.** The rule covers the four private evaluations. Public sets (GSM8K, BIG-Bench Hard, CRUXEval, L1, K1, K2) may contain a part-B procedure; whether they count as in-teaching is settled in M1.5 (ADR-0033 section 6.4 item 3), unchanged. K0 has one part and is outside this rule.

## 4. Answer 4: parts A and B are assigned by shuffling clusters

**Amended sentence** (section 6.4, line 300): "**The family partition.** At the freeze, a registered seed splits the families of each private evaluation into **part A** (teaching may draw on these families) and **part B** (held out: no teaching item, template or family of part B may ever be used for teaching). Half each. Fixed before any score, so that no result can shape it."

**Replacement reading: the cluster partition.** Computed by code on the map of record, with the registered seed that section 12 gives for this role (400004; see section 12 of this addendum). `stream(seed, label…)` is the SHA-256 derivation of section 12, line 576.

1. Only global clusters with at least one registered lineage are assigned. Let X be those with registered lineages in two or more evaluations, and L_e those with registered lineages in evaluation e only.
2. **Cross-evaluation clusters first.** X is sorted by identity, shuffled with `stream(400004, "cluster-partition", "cross")`, and assigned in shuffled order alternately A, B, A, B and so on.
3. **Then each evaluation**, for e in R1, R2, M1, C1. G_e,total is the number of global clusters with a registered lineage in e. The target for part A is ⌊G_e,total / 2⌋ (with an odd count the held-out part B has one more). L_e is sorted by identity and shuffled with `stream(400004, "cluster-partition", e)`. Its first max(0, target − number of X clusters of e already in A) clusters go to part A, the rest to part B.
4. **No cluster is in both parts**, of one evaluation or of two. A test asserts it on the map of record.
5. If the X clusters already in A exceed an evaluation's target, the evaluation's parts are unequal. The counts are printed; nothing is moved to repair it.
6. Families remain a descriptive label of a shape. They no longer define the parts, and a family may have shapes in both parts. "At least 12 families" (line 268) stays as a requirement on the registered lineages of an evaluation; "(strata)" is withdrawn for private evaluations (section 9 of this addendum).
7. The partition is fixed when G-gen's record of record is made and is frozen at F. If the map of record changes before G-load, the record is made again (ADR-0033 section 13, G-gen row) and the partition is recomputed by the same code; every earlier record is kept. After any model has scored any item the map and the partition do not change.

Reasons for steps 2 and 3 instead of one shuffle of all global clusters: one global shuffle satisfies answers 3 and 4 but leaves each evaluation's split to chance (for 27 clusters, about 13.5 ± 2.3 in part A [E]); the human lead was shown "about 13 / 14 for R1". The two-step rule gives ⌊half⌋ per evaluation whenever step 5 does not bite. The simpler rule is listed in section 13 for the reviewer and the human lead.

## 5. Answer 5: the count registered is the count reached

**Amended sentences.** Section 6.2, line 269: "The human lead registers a minimum before G-gen's record (proposed: 300). If fewer can be written, the count written is registered, and the table below shows what it can reach." Section 14, line 628: "G = every lineage that passes the G-gen gates, with a registered minimum of 300 per private part". Section 16, choice 10 (line 662): "**the minimum G, proposed 300 lineages per part, before the generators are frozen**". The box, item 4 (line 22). Section 17, the held table (line 691).

**Replacement reading.**

1. **The proposed minimum of 300 is withdrawn. No minimum is registered.** G per private part is the number of clusters of that part with at least one registered lineage, in the map of record, after the re-audit, the second solvers and their audit (section 8), the battery (section 7) and the capacity gate (section 10). "G is the number written, not a number tuned" (line 269) stands: every cluster that passes is used, and no cluster is left out to change G.
2. G per part is written into G-gen's record of record and reported to the human lead with the borderline ("strictest") counts beside it. G-gen's record still needs his domain list (choice 2). It no longer waits for a minimum G.
3. **No margin or threshold changes.** The grid {0.02, 0.03, 0.05}, alpha 0.05, power 0.8, Boole's bound, the ladder, the 20,000 pool, the planning worst-case τ of 0.10 and the known-truth tolerance are as ADR-0033 states them, each still the human lead's to confirm where ADR-0033 says so.
4. Choice 19 (lineages as strata) is not taken. The human lead answered "2" and "m0 I already said cluster". Clusters remain random effects under the approved power rule.

## 6. What G of 11 to 19 per part can reach (arithmetic; no measurement)

Script: `docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/power_small_g.py` (SHA-256 `6f846f3e…1945`), output `power_small_g.out.txt` beside it (`6851f2c4…ee50`). Standard library, locked environment. Its part 0 reproduces the table of section 8 (lines 402 to 407) to the four decimals of review 2's `power_check2.out.txt`; ADR-0033 rounds halves up, so 0.0075 prints there as 0.008 and here as 0.007.

Rules used, as written: section 9.4, the floor Φ(δ·√G_e / τ̂_e − z₀.₉₅) against the per-test target 1 − 0.2/M_e (line 457 and line 458); the simulated test with the t quantile on G_e − 1 degrees of freedom (line 456); section 10.5 (line 518), which reads NOT EVALUABLE (UNDERPOWERED) if the floor is below target, or the required size is above the 20,000 pool, or it is not reached on the ladder. M_e = 55 (5 tests × 11 gate-candidate parts) unless stated; 70 gives slightly stricter figures (in the output). d = 0.3 as in section 8.

**(a) The floor as written (normal quantiles).** Needs δ·√G/τ ≥ 4.33.

| Largest τ at which the floor is met | G = 11 | G = 13 | G = 14 | G = 15 | G = 19 |
|---|---|---|---|---|---|
| δ = 0.02 | 0.015 | 0.017 | 0.017 | 0.018 | 0.020 |
| δ = 0.03 | 0.023 | 0.025 | 0.026 | 0.027 | 0.030 |
| δ = 0.05 | 0.038 | 0.042 | 0.043 | 0.045 | 0.050 |

**(b) The test as written (t quantile on G − 1 degrees of freedom) inside the 20,000 pool, d = 0.3.** This is the binding condition. It is the exact power for normal cluster means, an idealisation of the registered simulation and not the simulation.

| Largest τ at which δ is reachable | G = 11 | G = 13 | G = 14 | G = 15 | G = 19 |
|---|---|---|---|---|---|
| δ = 0.02 | 0.006 | 0.007 | 0.008 | 0.008 | 0.009 |
| δ = 0.03 | 0.017 | 0.019 | 0.020 | 0.021 | 0.024 |
| δ = 0.05 | 0.033 | 0.037 | 0.038 | 0.040 | 0.045 |

**(c) Smallest δ reachable** (normal formula of section 8, 20,000 items / any number of items), for comparison with the table of section 8:

| τ | G = 11 | G = 13 | G = 15 | G = 19 |
|---|---|---|---|---|
| 0.03 | 0.043 / 0.039 | 0.040 / 0.036 | 0.037 / 0.034 | 0.034 / 0.030 |
| 0.05 | 0.067 / 0.065 | 0.062 / 0.060 | 0.058 / 0.056 | 0.052 / 0.050 |
| 0.10 | 0.132 / 0.131 | 0.121 / 0.120 | 0.113 / 0.112 | 0.101 / 0.099 |
| 0.15 | 0.197 / 0.196 | 0.181 / 0.180 | 0.168 / 0.168 | 0.150 / 0.149 |

**What this means, plainly.**

- **At the planning worst case that ADR-0033 proposes (τ = 0.10), no margin of the registered grid is reachable on any private part.** The smallest reachable margin is about 0.10 to 0.13. Every private part (R1, R2, M1 and C1, parts A and B: eight parts) would read **NOT EVALUABLE (UNDERPOWERED)** at 0.02, at 0.03 and at 0.05, whatever the pool size.
- **δ = 0.02** will read NOT EVALUABLE (UNDERPOWERED) on every private part unless τ̂ is at most about 0.006 to 0.009. Per-test power at τ = 0.02 and 20,000 items is 0.83 to 0.94 against a target of 0.996.
- **δ = 0.03** will read NOT EVALUABLE (UNDERPOWERED) on every private part unless τ̂ is at most about 0.017 to 0.024.
- **δ = 0.05** will read NOT EVALUABLE (UNDERPOWERED) unless τ̂ is at most about 0.033 to 0.045. At τ = 0.05 it is not reachable at any G from 11 to 19. **This is wider than what was put to the human lead**, who was told that the 0.02 and 0.03 private margins "will most likely" read underpowered; the 0.05 margin is in the same position unless the clusters differ much less than the planning worst case.
- **The reading will rest on an imprecise estimate.** With about 13 clusters of about 115 M0-draw items each, the sampling error of τ̂² is of the order of τ² itself for τ up to about 0.04 [E]; for a true τ of 0.03 the estimate is truncated to exactly zero in roughly three draws in ten [E], and a τ̂ of zero meets every floor. Choice 18 of ADR-0033 (point estimate or the upper bound of τ̂'s 90 % interval; the lead's recommendation is the upper bound) therefore decides most of these readings. It is the human lead's and is not taken here. Under the upper bound, with 12 degrees of freedom, every figure of table (b) falls further.
- NOT EVALUABLE (UNDERPOWERED) is a registered outcome of M0 (section 10.5). It is not a defect and is never a reason to widen a margin (section 15, line 644). What it means for the ladder: with these parts underpowered, the M5 parity gate on the private evaluations is NOT EVALUABLE at that margin, which is not PARITY (ADR-0032 section 5). Whether to continue to M1a on that footing, to choose a wider margin on substantive grounds before stage R1, or to reopen choice 19 is the human lead's decision and none is proposed here.
- Public parts (L1, K1, K2) are unaffected: their clusters are passages, premises and items.
- Nothing in this section is measured. τ is unknown until M0 is run.

## 7. The shortcut battery (new gate; its bound is left open)

ADR-0033 has no rule about tells in private items except K0's GENERATOR GUESSABLE. **Added to section 6.2, "Validity gates, no model involved" (line 275).**

1. **The battery** for an evaluation is a fixed set of heuristics: a generic text battery (answer position, mention counts, first and last mentioned, extreme numbers, the commonest key); every heuristic its authors wrote; every heuristic the auditors wrote; and for C1 the closed forms of section 2. Its code is hashed before the measurement of record.
2. **Measured per lineage and per level, each of the seven levels separately, never only pooled.** For each heuristic: the share of items on which it gives an answer, its accuracy on those items, the chance level on those items, and the gain (accuracy minus chance) times the share. **Two-sided:** a heuristic that is right less often than chance is a tell as well, because it rules answers out.
3. **The bound is not set here.** It is a new registered number and belongs to the human lead (section 13, item 1). Until he registers it, G-gen's record of record is not made, and no lineage is registered. It will be proposed after the re-audit, with the measured distributions in view. That is after generator statistics have been seen and before any model has produced any output; the proposal will say so.
4. **Repair by construction only.** A tell is removed by the way the item is built, so that the heuristic is uninformative at every level. **Redrawing items conditional on a heuristic's outcome, or fitting a probability to it, is forbidden** (lead ruling R-1, which withdrew the lead's own earlier ruling). A lineage whose tell cannot be removed by construction is NOT REGISTERED. Shapes already repaired by redraw are superseded and kept on file.
5. A heuristic that is a partial or alternative run of the procedure itself (the audits call it an approximate procedure) is measured and reported separately. Whether it counts against the bound is put to the human lead with the bound.
6. Every convention an answer depends on is stated in the item. An item whose key changes under an ordinary alternative reading is a defect of its lineage (lead ruling R-4), found by the auditor's reading of rendered items, and is fixed in wording or the lineage is NOT REGISTERED.

## 8. Second solvers, and lineages NOT REGISTERED

**Second solvers.** Line 261 ("an independent second solver re-derives it from the item's structured form") and line 275 ("The auditor context that writes the second solvers does not audit them: a separate auditor context audits the solver pair") stand and are made exact:

1. Three separate contexts. The author writes the generator and its solver. A second context, an `arbor-auditor` that has not read the generator's or the first solver's source, writes the second solver from the item's structured form, its schema and fixtures only. A third `arbor-auditor` context audits the pair.
2. A second solver written by the context that wrote the generator does not satisfy line 261. The implementation's own notes record that the existing second solvers were written by the implementer; they are rewritten under item 1 before registration.
3. Which model ran each context is recorded from session metadata.

**Registration.** A lineage is registered only when all of these hold and are recorded: its place in the map of record; its wording read by the auditor; the battery within the registered bound; capacity (section 10); a second solver under item 1 that agrees with the first on every fixture and on every generated item; the pair audited.

**NOT REGISTERED.** A written lineage that fails any condition, or is superseded, is marked NOT REGISTERED with its reason in the map of record. It is kept on file and never deleted. It supplies no item to any tuning, development or sealed pool and is not counted in G. It keeps its global cluster, and its cluster's part binds it under section 3 item 3. A global cluster with no registered lineage has no part; it is listed, and whether teaching may draw on it is settled in M1.5, not here. A cluster is not registered at some levels only: see section 10 item 4.

## 9. Statistics at fewer than 30 clusters (consequences in section 9 of ADR-0033)

No rule of section 9 is relaxed. Three places need exact text because clusters no longer sit inside families.

1. **Strata.** Section 9.2 (line 435): "Cluster bootstrap, stratified by family or task". Section 9.4 (line 456) draws clusters "within strata" and defines τ̂² from "the variance of the cluster means within strata". For private evaluation parts a cluster may now span several families, and with 11 to 19 clusters over 12 or more families most strata would hold one cluster. The implementation's reading is that a stratum with one cluster contributes nothing to the between-cluster variance; at these counts that drives τ̂ toward zero and the floor toward "met". **Replacement reading: a private evaluation part is one stratum.** Families are printed as subcategories only (line 431). This is the less favourable reading: variance between families is counted as between-cluster variance. Public parts keep their strata (tasks, subjects).
2. **The small-sample rule now applies to every private part.** Line 435: "With fewer than 30 clusters: the cluster-robust standard error with a t quantile on (clusters − 1) degrees of freedom replaces the percentile bootstrap." Unchanged. Every private interval and bound of sections 9.1 and 10.2 to 10.4 is therefore a t interval on 10 to 18 degrees of freedom, and the "confirmation" bootstrap of line 460 is replaced by the same rule for private parts.
3. **Sentences that assumed G = 300** are read at the G written: the M0 draw is "balanced over the G clusters" (line 388), about 79 to 136 items per cluster instead of about 5 (line 457); the sealed pool is "spread evenly over the G clusters" (line 390), about 1,050 to 1,820 sealed items per cluster. Inside a cluster, items are spread evenly over its registered lineages, and inside a lineage over its shapes (largest remainder, ties to the lower id).

Two problems found here are not settled by this addendum; they are in section 12.

## 10. The capacity gate at the G written

**Amended sentence** (section 6.2, line 273): "**Capacity gate (G-gen).** For every cluster and level, the number of distinct items the generator can produce is at least 10 times the number the pools demand. Otherwise engineering stop."

**Replacement reading.**

1. **"Distinct" is structural.** Two items are distinct only if their structured forms differ after erasing entity names, the setting sentence and the order of presentation (for C1: after renaming every identifier in order of first appearance). A change of names, setting or order alone is not a distinct item. The key function is hashed with the generators.
2. **The demand is computed at the G of the map of record, by the worst-case reading.** The level mix of a part is chosen later (section 6.5) and may be a single level, so the whole development and sealed pools of a part may fall on one level. For a part with G clusters:
   - on each of the five registered levels: **D(G) = 10 × (⌈(4,000 + 20,000) / G⌉ + 100)** structurally distinct items per cluster. 4,000 is the development pool, 20,000 the sealed pool, 100 the tuning draw per level and part (section 8, lines 387 to 390), taken whole for one cluster;
   - on each of the two reserve levels: 10 × 100 = 1,000.
3. **Check against ADR-0033's pool sizes.** D(11) = 22,820; D(13) = 19,470; D(14) = 18,150; D(15) = 17,000; D(19) = 13,640. At the withdrawn G = 300 it was 1,800. A cluster must hold more than ten times what it had to under the design as approved. The sealed pool may be raised later, never lowered (line 409); a raise re-runs this gate.
4. **Per cluster and per lineage.** The gate is read on the cluster: the number of structurally distinct items its registered lineages can produce together at that level. Because section 9 item 3 spreads a cluster's items evenly over its registered lineages, each registered lineage must also hold 10 times its own share, D(G) / k for a cluster of k registered lineages. A lineage that cannot is NOT REGISTERED and the gate is read again without it. A cluster that then fails at any of the seven levels is not registered at all: registering a cluster at some levels only would make G differ by level, against the even spread of section 8 and the level rule of section 6.5.
5. **The event is unchanged for the record of record:** a capacity failure there is an ENGINEERING STOP (section 10.7). Before the record, widening a generator or marking a lineage NOT REGISTERED is ordinary authoring, reported to the human lead with the list.

## 11. Where the change propagates in ADR-0033

| Place | Text | Effect |
|---|---|---|
| The box, line 16 | "at the proposed numbers a 3-point margin is not reachable…" | Superseded by section 6 here: at G of 11 to 19, none of 0.02, 0.03, 0.05 is reachable at τ = 0.10 |
| The box, item 4, line 22 | minimum number of clusters, "Proposed: at least 300" | Withdrawn (section 5). The worst-case τ stays his |
| Section 3, line 81 | "the template-family partition" | Read as the cluster partition (section 4) |
| Section 6.1 | Units | Unchanged |
| Section 6.2, table, line 261 to 264 | R1, R2, M1, C1 rows | Unchanged, except what a C1 procedure is (section 2) and the second-solver contexts (section 8) |
| Section 6.2, line 268 | Families, lineages and clusters | Sections 1, 3 and 4 here; "(strata)" withdrawn for private parts |
| Section 6.2, line 269 | G; minimum 300 | Section 5 |
| Section 6.2, line 270 | 50-pair check; variance between shapes within a lineage printed | Check replaced (section 1 item 5). The descriptive variance component is printed between lineages within a cluster as well |
| Section 6.2, lines 271, 272, 274, 276, 277 | Difficulty, reproducibility, disjointness, interior check, stated limit | Unchanged |
| Section 6.2, line 273 | Capacity gate | Section 10 |
| Section 6.2, line 275 | Validity gates | Sections 7 and 8 added; the 50-item ambiguity reading stays |
| Section 6.3 | Code tracing | Section 2; otherwise unchanged |
| Section 6.4, line 300 | The family partition | Sections 3 and 4 |
| Section 6.4, items 2 to 4 | Both parts measured; public sets; seeds | Unchanged |
| Section 6.5 | Level ranges | Unchanged |
| Sections 6.6 to 6.8 | Public sets, K0, domain list | Unchanged |
| Section 8, lines 387 to 392 | Split sizes | Unchanged numbers; "balanced over" and "spread evenly over the G clusters" read at the G written (section 9 item 3) |
| Section 8, line 394 | "the same frozen generator, level mix, families and clusters" | Unchanged |
| Section 8, lines 396 to 409 | Why 20,000; the table; planning τ | Unchanged as text. Its statements about G = 300 no longer describe the study; section 6 here is the reading at the G written |
| Section 8, line 411 | Option: lineages as strata | Not taken (section 5 item 4) |
| Section 8, lines 413 to 419 | Sealed pool, fingerprints, seals | Unchanged, except "part-B families" in line 419 (section 3 item 3) and counts "per family, cluster and level" now also per global cluster |
| Section 9.1, 9.3 | Measures; nuisance spreads | Unchanged |
| Section 9.2, line 435 | Intervals | Section 9 items 1 and 2 here |
| Section 9.4, lines 456 to 460 | Power simulation, floor, conjunction, confirmation | Formulas unchanged. One stratum per private part; G_e is the count of section 5; "Templates here are the clusters of section 6.2, that is the lineages" is read as the clusters of this addendum |
| Section 9.4, lines 462 to 466 | Known-truth gate, six scenarios at G = 300, tolerance 0.03 | Unchanged. Open item: it does not exercise the simulation at the G the study will have (section 12 item 6) |
| Section 10.1 to 10.4 | Outcome rules | Unchanged; private bounds are t bounds (section 9 item 2) |
| Section 10.5, line 518 | NOT EVALUABLE (UNDERPOWERED) | **Unchanged.** Consequence in section 6 |
| Section 10.6 | Projection | Unchanged; an underpowered part enters at its pool maximum, as written |
| Section 10.7, line 530 | Events | Unchanged; a battery result above the registered bound at the record of record is an ENGINEERING STOP like the other validity gates |
| Section 12, line 562 | "Family partition into parts A and B: 400004" | Role renamed "cluster partition into parts A and B"; value unchanged; labels of section 4. For the seed-registry auditor (section 12 item 7) |
| Section 12, other rows | Seeds | Unchanged. No seed value is added or chosen here |
| Section 13, G-gen row, line 587 | "for the record: choices 2 and 10 (G)" | The record needs choice 2, the shortcut bound (section 13 item 1) and this addendum's approval; no minimum G. It also holds the map of record, the partition, G per part and the battery tables |
| Section 13, F row, line 595 | "family partition" | Cluster partition, already fixed at G-gen's record; F hashes it |
| Section 13, Roles, line 614 | Auditor contexts | Section 8; one more context for the map of record |
| Section 14, line 628 | "registered minimum of 300 per private part" | Withdrawn; all other sizes unchanged |
| Section 14, line 632 | Thresholds | **Unchanged** |
| Section 15, line 644 | UNDERPOWERED "would not mean a reason to widen the margin" | Unchanged |
| Section 16, choice 10, line 662 | minimum G | Withdrawn from the list; the rest of choice 10 stands |
| Section 16, choices 18, 19 | τ floor; strata | 18 still his, and now decisive (section 6). 19 not taken |
| Section 16, line 673 | "whether 300 distinct lineages … can be written" | Answered by the audits: no |
| Section 17, line 691 | Held: "The minimum G" | Replaced by the shortcut bound; the worst-case τ stays held |
| Section 18, line 709 | "drawn only from part A families" | Read as part-A global clusters |
| Section 19 | Departures from ADR-0032 | Three rows added (section 15 here) |

## 12. Inconsistencies and open items found while drafting

Flagged, not resolved by wording.

1. **The first decision's premise no longer holds.** The option the human lead chose on 2026-11-25 read "Keep lineages as clusters and repair M0 to hundreds of lineages … The stronger claim survives". Answer 5 registers 11 to 19 clusters per part. At those counts the claim that clusters were kept for (a parity gate that generalises to other procedures of the same kind) is, by section 6, most likely NOT EVALUABLE at every registered margin on the private parts. The three answers are consistent as instructions. They are not consistent with the reason given for the first one. He should see section 6 before this addendum is approved.
2. **The coordinator's reading of the second answer** ("The definition in section 6.2 is not amended") against answer 1. This addendum reads section 6.2's definition strictly and adds an operational test; it also replaces the 50-pair check and adds global identity. Those are amendments in substance. They need his approval of this text, not only "Adopt all five".
3. **Answer 4 against section 6.2's "at least 12 families (strata)" and section 9.2's stratification by family.** Clusters shuffled across families cannot be nested in family strata. Section 9 item 1 here takes the less favourable reading (one stratum). It changes an analysis rule before any observation and needs the reviewer's check.
4. **Answer 3 against answer 4 as it was put to him** ("about 13 / 14 for R1"). A cross-evaluation rule can force unequal parts in an evaluation (section 4 step 5). The numbers of cross-evaluation clusters are not known until the map of record exists.
5. **The union of the teachers at fewer than 30 clusters.** Line 435 requires that G_U be "recomputed in every resample, including which teacher is the better one, so that choosing the better teacher on the same data is inside the bound". The small-sample rule of the same line has no resamples. The implementation uses a linearisation with the better teacher fixed at the point estimate, so the choice is outside the bound. This is a gap in ADR-0033 as written; it now touches every private part's complementarity reading (section 10.4). A registered small-sample rule for G_U is needed and is not drafted here.
6. **The known-truth gate does not cover the study's G.** Its six scenarios are at G = 300 (line 464). The simulation will run at G of 11 to 19, with one stratum, a t quantile and a τ̂ that is often truncated to zero. Proposal for the reviewer and the human lead: add scenarios at the G of the map of record, under the same tolerance, without removing or loosening any of the six. Not drafted as amending text because it adds a gate and its scenario list is a set of numbers.
7. **The seed.** Section 12 gives one seed for this role, 400004, and the SHA-256 label derivation; both are reused and no value is invented. Open for the seed-registry auditor: the role's name changes; the labels `"cluster-partition"` replace `"family-partition"`; and the block 400001–409999 is still a proposal, since no `SEED_REGISTRY_R6.md` was found in either worktree.
8. **Lead ruling R-5 against section 10 item 4.** R-5 allows a lineage to be "NOT REGISTERED at that level set". This addendum refuses partial-level registration of a cluster, for the reason given there. R-5 is a lead ruling, not approved text; the difference is stated.
9. **Borderline pairs across parts.** A borderline pair with one member in part A and one in part B weakens the held-out claim without breaking the rule. The count is printed. Whether borderline pairs should be kept in one part is listed in section 13.
10. **"Typed grammar" in the C1 row (line 264) against answer 2.** A program drawn from a grammar has no named algorithm unless the lineage fixes one. The 14 existing C1 lineages were written under the reading of answer 2 per lead ruling R-8; the drafter did not verify each.
11. **G may fall below 11 to 19.** Transitive closure across evaluations (section 3 item 2), the re-audit, the battery bound and the capacity gate can each remove clusters. The R1 capacity table already lists two clusters that fail at several levels at G = 13. Section 6 gets worse with every cluster lost.

## 13. Open choices reserved for the human lead

1. **The shortcut bound** (section 7): a new registered number, per level, two-sided, and whether approximate procedures count against it. To be proposed after the re-audit. No value is proposed here.
2. **Choice 18 of ADR-0033** (point estimate or upper bound of τ̂ for the floor), now decisive for the private parts.
3. **Whether to proceed knowing section 6**, and whether choice 19 stays refused. No recommendation is made in this draft.
4. **The partition mechanics**: the two-step rule of section 4 (drafted) or one global shuffle (simpler, unequal halves per evaluation).
5. **Borderline pairs**: left free (drafted) or kept in one part for the partition only, without merging them for G.
6. **Additional known-truth scenarios at the study's G** (section 12 item 6).
7. **A small-sample rule for the union of the teachers** (section 12 item 5), to be drafted and reviewed.
8. The planning worst-case τ, the pool size and every other number of section 14 remain his as ADR-0033 lists them.

## 14. What this addendum does not change

- No margin, grid value, alpha, power value, band, cap fraction, tolerance, hour ceiling, pool size, draw size, ladder or token limit.
- The power rule, Boole's bound, the simulation's formulas and the rule of section 10.5.
- Clusters as random effects; choice 19 is not taken.
- The order of stages, the freeze, the sealed pools and who reads them, Decision 1's limit to locked-environment work, and Decision 2.
- Every other choice of section 16 of ADR-0033, each still the human lead's.
- The models, the stack, the one-system rule, the public sets, K0, the domain list, the download limit.
- Every non-claim of section 1. M0 measures reference models only; capability parity of ArborLM is untested.
- Every earlier record. ADR-0033, its reviews, the audits, the superseded shapes and the failed attempts stay as they are.

## 15. Where the addendum departs from ADR-0032 and ADR-0033 as written

| # | Text as written | What the addendum does | Whose call |
|---|---|---|---|
| A1 | ADR-0033 section 6.2: a registered minimum G (proposed 300) before G-gen's record | No minimum; the count reached is registered | Human lead (answer 5) |
| A2 | ADR-0033 section 6.4: families are split into parts; "Half each" | Global clusters are split; halves per evaluation only where the cross-evaluation rule allows | Human lead (answers 3, 4) |
| A3 | ADR-0033 section 6.2: the 50-pair check within a family | Every pair within an evaluation and the cross-evaluation links, by an auditor whose map governs | Human lead (answer 1) |
| A4 | ADR-0033 sections 6.2 and 9.2; ADR-0032 section 5 ("subjects or task names are strata") | Private parts are one stratum each; families are descriptive | Lead after review; then human lead |
| A5 | ADR-0033 section 6.2: capacity counted on "distinct items", demand implied at G = 300 | Structural distinctness; worst-case demand at the G written; no partial-level clusters | Lead after review |
| A6 | ADR-0033 has no gate on tells in private items | A measured battery with a bound he registers; repair by construction only | Human lead (the bound) |
| A7 | ADR-0032 section 4, a private set "where one can be built"; section 5, "NOT EVALUABLE (UNDERPOWERED) … is not PARITY" | Private sets are built, at a cluster count that by section 6 most likely cannot support the gate at the registered margins. ADR-0032's rule is applied as written; nothing is dropped from the conjunction | Human lead |
| A8 | ADR-0032 section 4: generalisation is "an in-teaching-distribution part and an out-of-teaching part" of every evaluation | The out-of-teaching part is defined by procedure across the four private evaluations, not per evaluation | Human lead (answer 3) |

## 16. Record

- Drafted by one context (`arbor-lead`, Claude Fable 5.2, `claude-fable-5-2`). No delegation was made for this draft. Not reviewed by `arbor-auditor`. Not approved by anyone.
- Read for it: ADR-0033 revision 4 in full; ADR-0032 sections 4 and 5; on `claude/m0-impl` at `f122e6bc`: the three records of the human lead's words, `LEAD_RULINGS_2.md`, the four audit reports in part (cluster, cross-evaluation, closed-form and capacity sections), `studies/m0/r1_registration_plan.md`, `studies/m0/manifests/r1_rev4_parts.md`, the four cluster maps, and the partition, capacity-demand and statistics code as it stands.
- Not verified by the drafter: any auditor's cluster judgement; the measured capacity and battery tables; that the traced-state shapes meet section 2 item 2; the number of cross-evaluation components; the state of the seed registry beyond the files named.

`SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`
