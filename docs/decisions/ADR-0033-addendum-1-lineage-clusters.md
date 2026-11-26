# ADR-0033 addendum 1 — lineage clusters: the strict reading, the cluster partition, the count reached

**Status: DRAFT 2 — NOT APPROVED. Draft 1 was reviewed once (`docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/REVIEW_ADDENDUM1_1.md`: approvable after required changes, 2 blocking, 10 required, 8 notes). This draft applies that review and has not been reviewed again. Nothing in this document is registered, and nothing in it authorises implementation, registration of a lineage, a package install, a download, a model run or a decision.**

- Date: 2026-11-25 (Panama time). Draft 2 written by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) on the coordinator's brief, in place, as ADR-0033's own drafts were revised (commits `c89c1f2d`, `44879b45`, `2082cdd7`, `8503fa82` all edit one file). Draft 1 is this file at commit `2c390259` (SHA-256 `bb276504…9868`). The drafter read records and code only, ran two standard-library arithmetic scripts on the locked environment, ran no model, downloaded nothing, delegated nothing and made no git write.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result.
- **What is amended.** `docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md`, revision 4, SHA-256 `7719f6d456113385a44dac37abeb28b36d6d9fb7eb569a65c7e6ccaaf19ec90b` ("ADR-0033"). That file is not edited. Line numbers below are lines of that file at that hash. Where this addendum and ADR-0033 differ, the addendum would govern once approved; until then ADR-0033 governs as written.
- **What it writes down.** The human lead's five recorded statements of 2026-11-25, on branch `claude/m0-impl` at commit `9bcec484`, folder `docs/reviews/m0-lineage-decision-2026-11-25/`: `HUMAN_LEAD_WORDS.md` ("2"; `94e9d9a2…b9a9`), `_2.md` ("m0 I already said cluster"; `005305bf…dac04`), `_3.md` ("Adopt all five"; `d0da7d11…c6286`), `_4.md` ("fix round"; `7c51b6dd…f6b09`), `_5.md` ("1": register the survivors at a bound of 0.15; `32c73ca9…dbeac`); and the lead's rulings `LEAD_RULINGS_2.md` (`e2e4128a…b123`), `_3.md` (`782d65aa…1b34`), `_4.md` (`af7128cb…1fdd`), `_5.md` (`070129e1…f9ab`). His words set a direction. This text is the drafter's rendering of them; where it goes beyond his words it says so (sections 12, 13 and 15).
- **[KNOWN] No model has been loaded, run or scored on any M0 item.** No package that would run a model is installed and no model or dataset has been fetched for M0 (the reviewer checked the same in two worktrees and could not check elsewhere). Everything that shaped this addendum is a property of item generators. **One number in it was set after measurements had been seen: the shortcut bound of section 7, set by the human lead after the auditors' item-side measurements of cheap rules were in front of him. Those are measurements of items, not of any model.** **No margin, band, alpha, power value, tolerance, pool size or grid of ADR-0033 is changed or relaxed here.**

## 0. Terms

| Term | Meaning here |
|---|---|
| Shape | One registered generator function with one question form (ADR-0033 calls it a "rule shape") |
| Lineage (as written) | A group of shapes that an author wrote as one "hand-written base rule". Its id is the registry id `<evaluation>.<name>` |
| Procedure | The algorithm a solver must carry out on an item's content to obtain the answer. (Line 419 of ADR-0033 uses "procedure" in another sense, an administrative routine; section 11) |
| Cluster | A set of lineages that share one procedure under the test of section 1. The unit for G, for every interval and for the partition |
| Global cluster | A cluster identity that holds across the four private evaluations R1, R2, M1 and C1 (section 3) |
| Map of record | The file that assigns every written lineage to a global cluster, fixed in G-gen's record of record |
| Part A, part B | The teaching-eligible and the held-out parts of an evaluation (ADR-0033 section 6.4) |
| G, G_e | The number of clusters with at least one registered lineage in one part of one private evaluation |
| NOT REGISTERED | A written lineage that enters no pool (section 8) |
| Cheap rule, tell | A rule that does not carry out the procedure and gets the answer right, or rules answers out, more often than the base rate |
| τ | The between-cluster standard deviation of a paired difference (ADR-0033 section 8) |

## 1. Answer 1: "distinct solution procedure" is read strictly

**Amended sentence** (section 6.2, line 268): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part."

**Replacement reading.**

1. **The test (the drafter's text; not the human lead's words and not the auditors' rule; section 13 item 4).** Two lineages are one cluster when one algorithm, written once, solves every item of both after any combination of: renaming entities; changing the setting or surface frame; changing the order of presentation; changing parameter values (sizes, depths, number systems, moduli, tie-break rules, which position or extremum is asked); negating or inverting the question; or asking for a different read-out of the same computed state. Two lineages are distinct only if the algorithm, the data structure it maintains, or the dependency structure of its steps differs. A difference of topic, vocabulary, answer type or evaluation does not make two lineages distinct. The answer he adopted read "strict, using the auditors' maps". The auditors made their maps by their own judgement before this sentence existed. **If this test is approved, the auditor who makes the map of record re-reads every pair judgement of the working maps against it and records, per pair, "unchanged" or "changed" with the reason.** If it is not approved, this item is a description and the auditors' recorded judgement is the rule.
2. **The unit.** "The cluster, for G and for every bootstrap, is the lineage" is read as: the cluster is the set of written lineages that are one procedure under item 1. G is the number of clusters per part that have at least one registered lineage. This is the merge that line 270 already prescribes ("Such a pair is merged into one lineage before the record"), applied to every pair, not to a sample.
3. **Who decides.** The map is made by an `arbor-auditor` context that wrote none of the lineages, from code and rendered items, with its judgement hashed before it reads any author's notes. **The auditor's map governs.** Where an author disagrees with a merge, the disagreement is written beside the map with its reasons; it does not un-merge. Where the auditor is unsure, the pair is listed as borderline and is not merged; borderline pairs are reported with the count they would give if merged ("strictest"). Over-counting clusters is the harmful error, so a pair the auditor judges the same is merged even if every author disagrees. Leaving borderline pairs unmerged sits uneasily with that sentence (review note N4); printing the strictest count beside every G is the mitigation, and section 13 item 9 puts the alternative.
4. **The map of record** is the auditor's map after the narrow round of the human lead's fifth decision (section 7), completed by the cross-evaluation step of section 3. **No count quoted so far is a registered number.** The latest working counts are in `LEAD_RULINGS_4.md`: clusters left at a bound of 0.15, cheap rules only, before the cross-evaluation rule, before capacity and before the narrow round: 10 (R1), 20 (R2), 18 (M1), 17 (C1; 15 without two variants). Half of each is about 5 to 10 clusters per part. Draft 1 used 11 to 19 per part, from counts made before the bound (27, 38, 22 and 28 or 29: `LEAD_RULINGS_2.md` gives 28 for C1 as the auditor's count, `LEAD_RULINGS_3.md` gives "28 (29)", the 29 being the implementer's map; neither is used here). Section 6 therefore covers G from 5 to 19.
5. **The check of line 270** ("The auditor reads one rendered item from each of 50 random pairs of lineages in one family and records any pair that is the same procedure") is replaced by: the auditor writes one line stating the procedure of every cluster; judges every pair of written lineages within an evaluation, across families and across parts; and judges every pair of clusters of two different evaluations against those statements and rendered items. Linked and borderline pairs are listed with reasons; a pair not listed is judged distinct. The 50-pair sample is no longer the check.

## 2. Answer 2: what a code-tracing item's procedure is

**Amended text.** Section 6.2, the C1 row (line 264), and section 6.3 (line 283: "C1 measures reading and tracing code. It does not measure writing it"). Neither says what a C1 item's "solution procedure" is.

**Replacement reading.**

1. For C1 the procedure of a lineage is **the algorithm of the program the item shows**, not the act of stepping through statements. (Under the other reading every C1 item is one procedure and C1 has one cluster.) The test of section 1 applies to the programs' algorithms.
2. **A lineage is admissible only if the printed line cannot be obtained without following the program's state.** If a closed formula or a library call on the program's literals gives the printed line on every item of a shape, that shape is NOT REGISTERED. Draft 1 allowed a replacement "traced-state shape". The third audits found three of the four drafted replacements answerable by closed form (lead ruling R-14), and the fifth decision allows no new lineage and no replacement shape (R-25). So in this round a lineage with a closed form is dropped, not replaced. A closed form is a cheap rule and falls under the bound of section 7.
3. A lineage for which no admissible shape exists is NOT REGISTERED.
4. Section 6.3 is otherwise unchanged. C1 is still called code tracing, never coding.

## 3. Answer 3: one algorithm, one part, across evaluations

ADR-0033 does not address the same algorithm appearing in two evaluations. **New rule, added to section 6.4 after item 1 (line 300).**

1. **Global cluster identity.** The four per-evaluation maps are joined into one graph whose nodes are all written lineages of R1, R2, M1 and C1, registered or not. Two nodes are linked if the auditor judges them one procedure under section 1, whether they are in the same evaluation or not. A C1 lineage and a lineage of another evaluation are linked when the C1 program's algorithm is the other lineage's procedure. **A global cluster is a connected component of this graph.** Its identity is the smallest lineage id it contains, in Unicode code-point order of the id strings. Links the auditor judges weaker than "the same procedure" are listed as borderline and do not join components.
2. **Transitive merging inside an evaluation. This is a new rule. It is not in answer 3, which constrained parts only, and it lowers G (section 13 item 5).** Sameness is transitive. If a component joins two lineages of one evaluation that that evaluation's own map kept apart, they are one cluster of that evaluation, and its G falls by one. The auditor may instead withdraw a named link, with written reasons, before the map of record is fixed. Nobody else may. The alternative, in which such lineages stay two clusters and only share a part, is put in section 13.
3. **The rule.** Every global cluster with at least one registered lineage is assigned to exactly one part, A or B, for all four evaluations at once (section 4). No lineage of a part-B global cluster, in any evaluation, registered or not, and no item, template or program generated by, derived from or written to imitate a lineage of a part-B global cluster, may ever be used for teaching. This replaces "no teaching item, template or family of part B" in line 300 and "no teaching code may use part-B families, checked in M1.5 by template signature" in line 419: the check in M1.5 is by global cluster as well as by template signature. Extending the ban to unregistered lineages goes beyond answer 3 and is the drafter's (section 15, A9).
4. **What the ban does not settle.** Whether teaching material from other sources that exercises a part-B procedure is excluded (teacher-written or distilled data will contain sorting, base conversion, percentages), and how M1.5 checks it, is settled in M1.5's specification. It is not settled here: read literally over every source it could make M1.5 impossible, and read loosely it could not be enforced.
5. **K0.** K0 has one part and is not a node of the graph. Its generator is "the look-up teaching material M1.5 and M2 will need" (line 326). If a K0 generator implements a part-B procedure the auditor lists it and the human lead decides; until he does, that K0 generator is not used for teaching.
6. **The map** is one file, `studies/m0/manifests/cross_evaluation_procedures.json`, frozen at F by hash. It lists every lineage, its evaluation, its global cluster, every link with the auditor's reason, every borderline pair, and the registration status of each lineage. It does not exist yet (lead ruling R-15).
7. **Limit, stated.** The rule covers the four private evaluations. Public sets (GSM8K, BIG-Bench Hard, CRUXEval, L1, K1, K2) may contain a part-B procedure; whether they count as in-teaching is settled in M1.5 (ADR-0033 section 6.4 item 3), unchanged.

## 4. Answer 4: parts A and B are assigned by shuffling clusters

**Amended sentence** (section 6.4, line 300): "**The family partition.** At the freeze, a registered seed splits the families of each private evaluation into **part A** (teaching may draw on these families) and **part B** (held out: no teaching item, template or family of part B may ever be used for teaching). Half each. Fixed before any score, so that no result can shape it."

**Replacement reading: the cluster partition.**

**The mechanics, complete (review 1, B1).** ADR-0033 line 576 says only "SHA-256 of the seed with a text label". For this role the derivation is:

- `stream(seed, l₁, …, l_k)` is `random.Random(int.from_bytes(hashlib.sha256('|'.join([str(seed), l₁, …, l_k]).encode('utf-8')).digest()[:8], 'big'))` in CPython 3.12. In words: the decimal text of the seed and the labels, joined by the single character `|` (U+007C) with nothing before or after; encoded as UTF-8; hashed with SHA-256; the first 8 bytes of the digest read as an unsigned big-endian integer; that integer seeds CPython 3.12's `random.Random` (Mersenne Twister, MT19937).
- The seed is 400004 (ADR-0033 section 12, line 562). The labels are the ASCII strings `cluster-partition` followed by `cross`, `R1`, `R2`, `M1` or `C1`.
- **To shuffle a set of clusters** is: write their identities as a list sorted in increasing Unicode code-point order of the identity strings (Python `sorted` on `str`), then call the stream's `shuffle` method on that list once. That method is the loop of CPython 3.12's `Lib/random.py`: for i from len − 1 down to 1, j = `_randbelow(i + 1)`, swap elements i and j. Each stream is created fresh and used for that one call only.
- Lineage ids are the registry ids `<evaluation>.<name>`; a cluster's identity is the smallest id it contains (section 3 item 1).
- **Test vectors** (script `partition_vector.py`, section 6's folder; made-up identities, no cluster map read): `'400004|cluster-partition|cross'` gives the integer 3111564968117111496; the list `a` to `h`, sorted, shuffles on that stream to `e, c, b, h, d, f, g, a`. The output file holds the integer and the shuffle for all five labels and a whole worked example.

**The procedure**, computed by code on the map of record:

1. Only global clusters with at least one registered lineage are assigned. Let X be those with registered lineages in two or more evaluations, and L_e those whose registered lineages are all in evaluation e. An unregistered lineage does not make a cluster cross-evaluation.
2. **Cross-evaluation clusters first.** X is shuffled with `stream(400004, "cluster-partition", "cross")`. The element at index 0 of the shuffled list goes to A, index 1 to B, index 2 to A, and so on. With an odd number A has one more.
3. **Then each evaluation**, for e in the order R1, R2, M1, C1. G_e is the number of global clusters with a registered lineage in e. a_e is the number of X clusters of e already in A. L_e is shuffled with `stream(400004, "cluster-partition", e)`. **The split point is k_e = min(|L_e|, max(0, ⌊G_e / 2⌋ − a_e)): the elements at indices 0 to k_e − 1 of the shuffled list go to part A, the rest to part B.** With an odd G_e the held-out part B has one more. That ⌊G_e / 2⌋ goes to A, not to B, is the drafter's choice (the implementation's family partition did the same and flagged it for a ruling).
4. **No cluster is in both parts**, of one evaluation or of two. A test asserts it on the map of record.
5. **Unequal parts.** If a_e exceeds ⌊G_e / 2⌋, part A of e is overfull. If the X clusters of e in B exceed ⌈G_e / 2⌉, or L_e is too small to fill A, part B or part A is overfull in the same way. The counts are printed; nothing is moved to repair it. The reviewer's made-up scenarios show the size of this: with an evaluation of 11 clusters of which 10 are cross-evaluation, its parts differ from the half split in 47 % of seeds and the smaller part can be forced down to **one cluster** (review 1, `partition_step5_review.out.txt`). Section 9 item 5 says what a part of one or two clusters can carry.
6. Families remain a descriptive label of a shape. They no longer define the parts, and a family may have shapes in both parts. "At least 12 families" (line 268) stays as a requirement on the registered lineages of an evaluation; "(strata)" is withdrawn for private evaluations if section 9 item 1 is approved.
7. **When it is fixed (a timing change; section 15, A10).** ADR-0033 makes the partition "at the freeze" (line 300; F row, line 595). Here it is made at G-gen's record of record and hashed again at F. G-gen's record precedes G-load (line 257), so the map and the partition are fixed **after G-gen's record and before any model is run on any item**. After that record they do not change. The one exception is ADR-0033's own: the record is made again if the domain list changes or an engineering stop at the record requires it (line 587); the partition is then recomputed by the same hashed code, both partitions are kept and shown side by side, and the human lead is told. Once any model has been run on any item, nothing changes in any case.
8. **Fixed before computed (review 1, R9).** The mechanics above (and the choice of section 13 item 5) are approved, and the partition code is written and its SHA-256 recorded, **before any partition is computed on the map of record**. The code is proposed at `studies/m0/cluster_partition.py`; its hash goes into G-gen's record. It must reproduce the test vectors. Where the code and this text disagree it is an engineering stop, not a reading. Every partition ever computed is kept. The reason this matters: splits of families on seed 400004 have already been seen (`studies/m0/manifests/r1_rev4_parts.md` on `claude/m0-impl`; the "about 13 / 14" figure). The new labels give streams independent of those, and a text search of `studies/`, `tests/` and `docs/` on `claude/m0-impl` at `9bcec484` finds no code or record using the label `cluster-partition`.

Reasons for steps 2 and 3 instead of one shuffle of all global clusters: one global shuffle satisfies answers 3 and 4 but leaves each evaluation's split to chance (for 27 of 116 clusters, about 13.5 ± 2.3 in part A; reproduced by the reviewer, note N6). The two-step rule gives ⌊half⌋ per evaluation whenever step 5 does not bite. The simpler rule is an option in section 13 item 5.

## 5. Answer 5: the count registered is the count reached

**Amended sentences.** Section 6.2, line 269: "The human lead registers a minimum before G-gen's record (proposed: 300). If fewer can be written, the count written is registered, and the table below shows what it can reach." Section 8, line 409: "The human lead chooses G's minimum with this table in view." Section 14, line 628: "G = every lineage that passes the G-gen gates, with a registered minimum of 300 per private part". Section 16, choice 10 (line 662): "**the minimum G, proposed 300 lineages per part, before the generators are frozen**". The box, item 4 (line 22) and line 29 ("G-gen's record of record waits for your G and domain list"). Section 17, the held table (line 691).

**Replacement reading.**

1. **The proposed minimum of 300 is withdrawn, and no minimum is registered.** His answer 5 read "register the count reached, with no minimum of 300". The coordinator's brief for this draft states it as no minimum at all, and this text follows that; he confirms or corrects it when he reads this section. G per private part is the number of clusters of that part with at least one registered lineage, in the map of record, after the bound of section 7, the second solvers and their audit (section 8), the cross-evaluation step (section 3) and the capacity gate (section 10). "G is the number written, not a number tuned" (line 269) stands: every cluster that passes is used, and no cluster is left out to change G.
2. G per part is written into G-gen's record of record and reported to the human lead with the borderline ("strictest") counts beside it. G-gen's record still needs his domain list (choice 2). It no longer waits for a minimum G.
3. **No margin or threshold changes.** The grid {0.02, 0.03, 0.05}, alpha 0.05, power 0.8, Boole's bound, the ladder, the 20,000 pool, the planning worst-case τ of 0.10 and the known-truth tolerance are as ADR-0033 states them, each still the human lead's to confirm where ADR-0033 says so.
4. **Lineages are clusters.** Choice 19 (lineages as strata) is not taken: the human lead answered "2" and "m0 I already said cluster". Clusters remain random effects under the approved power rule. This addendum does not reopen it.

## 6. What G of 5 to 19 per part can reach (arithmetic; no measurement)

Scripts, all standard library, locked environment, in `docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/`: `addendum1_rev2_arithmetic.py` (SHA-256 `256ff109…1245`; output `addendum1_rev2_arithmetic.out.txt`, `14345463…850c`), new for this draft; `power_small_g.py` (`6f846f3e…1945`; output `6851f2c4…ee50`), draft 1's, unchanged. The reviewer recomputed draft 1's tables with code of his own and reproduced every figure (review 1, Q4), and added a direct simulation with discrete outcomes that agrees within Monte Carlo error.

Rules used, as written: section 9.4, the floor Φ(δ·√G_e / τ̂_e − z₀.₉₅) against the per-test target 1 − 0.2/M_e (lines 457 and 458); the simulated test with the t quantile on G_e − 1 degrees of freedom (line 456); section 10.5 (line 518), which reads NOT EVALUABLE (UNDERPOWERED) if the floor is below target, or the required size is above the 20,000 pool, or it is not reached on the ladder. M_e = 55 (5 tests × 11 gate-candidate parts); 70 gives slightly stricter figures (`power_small_g.out.txt`). d = 0.3 as in section 8. The standard error is the sample standard deviation of the cluster means over √G, as the implementation computes it; ADR-0033 fixes neither that form nor the divisor of the variance (review note N7; with the other form every figure of table (b) rises by 0.0004 to 0.0008).

**(a) The floor as written (normal quantiles).** Needs δ·√G/τ ≥ 4.33.

| Largest τ at which the floor is met | G = 5 | G = 8 | G = 10 | G = 13 | G = 19 |
|---|---|---|---|---|---|
| δ = 0.02 | 0.010 | 0.013 | 0.015 | 0.017 | 0.020 |
| δ = 0.03 | 0.015 | 0.020 | 0.022 | 0.025 | 0.030 |
| δ = 0.05 | 0.026 | 0.033 | 0.037 | 0.042 | 0.050 |

**(b) The test as written (t quantile on G − 1 degrees of freedom) inside the 20,000 pool, d = 0.3.** This is the binding condition. It is the exact power for normal cluster means, an idealisation of the registered simulation and not the simulation.

| Largest τ at which δ is reachable | G = 5 | G = 8 | G = 10 | G = 13 | G = 19 |
|---|---|---|---|---|---|
| δ = 0.02 | not at any τ | 0.0040 | 0.0055 | 0.0071 | 0.0094 |
| δ = 0.03 | 0.0088 | 0.0136 | 0.0160 | 0.0189 | 0.0236 |
| δ = 0.05 | 0.0187 | 0.0270 | 0.0312 | 0.0366 | 0.0453 |

At G = 5 or fewer, δ = 0.02 is not reachable inside the pool even if the clusters do not differ at all (power 0.9935 at τ = 0 against a target of 0.9964).

**(c) Smallest δ reachable inside the 20,000 pool with the t test**, for comparison with the table of section 8:

| τ | G = 5 | G = 8 | G = 10 | G = 13 | G = 19 |
|---|---|---|---|---|---|
| 0.03 | 0.076 | 0.055 | 0.048 | 0.042 | 0.036 |
| 0.05 | 0.123 | 0.088 | 0.077 | 0.066 | 0.055 |
| 0.10 | 0.244 | 0.173 | 0.150 | 0.129 | 0.105 |

(Draft 1 printed this table from the normal formula: 0.132, 0.121 and 0.101 at τ = 0.10 for G = 11, 13 and 19. The t figures are the binding ones and are larger.)

**(d) The reading is itself random at these counts (review 1, B2).** τ̂² = max(0, V − s_w²·mean(1/m)) is truncated to exactly zero whenever the cluster means of the M0 draw happen to vary less than item noise alone predicts. A τ̂ of zero meets the floor and makes the simulated power meet the target as well (exact power at τ = 0 is 0.9991 to 0.9995 at δ = 0.02 for G of 11 to 19). So whether a part reads "reachable" depends heavily on the draw. Share of M0 draws in which τ̂ is exactly zero, 1,500 items balanced over G clusters (χ² approximation, the drafter's script; the reviewer's direct simulation of the registered rule gives 0.532, 0.295 and 0.072 at G = 13):

| True τ | G = 5 | G = 8 | G = 10 | G = 13 | G = 19 |
|---|---|---|---|---|---|
| 0.00 | 0.594 | 0.571 | 0.563 | 0.554 | 0.544 |
| 0.03 | 0.283 | 0.276 | 0.280 | 0.289 | 0.307 |
| 0.05 | 0.111 | 0.090 | 0.087 | 0.089 | 0.098 |

Share of M0 draws in which a part reads "reachable within 20,000", **G = 13, under the point estimate (choice 18 a)**. First figure: the reviewer's direct simulation of the registered rule; second: the χ² approximation (the reviewer's, reproduced by the drafter's script to within 0.001):

| True τ | δ = 0.02 | δ = 0.03 | δ = 0.05 | Truly reachable? |
|---|---|---|---|---|
| 0.00 | 0.542 / 0.573 | 0.667 / 0.676 | 0.905 / 0.890 | all three yes |
| 0.01 | 0.552 / 0.536 | 0.670 / 0.641 | 0.902 / 0.869 | 0.02 no; 0.03 and 0.05 yes |
| 0.03 | 0.315 / 0.304 | 0.407 / 0.396 | 0.713 / 0.667 | 0.02 and 0.03 no (true power 0.66, 0.92); 0.05 yes |
| 0.05 | 0.080 / 0.095 | 0.117 / 0.138 | 0.352 / 0.319 | none (0.05: true power 0.948) |
| 0.10 | 0.003 / 0.002 | 0.005 / 0.003 | 0.018 / 0.012 | none |

The same at the smaller counts now expected, χ² approximation only, point estimate (a) then upper bound (b):

| G, true τ | (a) 0.02 | (a) 0.03 | (a) 0.05 | (b) 0.02 | (b) 0.03 | (b) 0.05 |
|---|---|---|---|---|---|---|
| 5, τ = 0 (0.03 and 0.05 truly reachable) | 0 | 0.635 | 0.751 | 0 | 0.057 | 0.084 |
| 5, τ = 0.05 (none truly reachable) | 0 | 0.126 | 0.180 | 0 | 0.006 | 0.009 |
| 10, τ = 0 (all truly reachable) | 0.575 | 0.661 | 0.854 | 0.052 | 0.073 | 0.161 |
| 10, τ = 0.03 (only 0.05 truly reachable) | 0.290 | 0.362 | 0.584 | 0.015 | 0.021 | 0.054 |
| 10, τ = 0.05 (none truly reachable) | 0.091 | 0.124 | 0.254 | 0.003 | 0.004 | 0.012 |
| 13, τ = 0 (all truly reachable) | 0.573 | 0.676 | 0.889 | 0.054 | 0.081 | 0.208 |

Column (b) uses a χ² interval for the between-cluster variance. **That interval is an assumption: ADR-0033 registers no interval for τ̂ below 30 clusters** (section 9 item 4).

**What this means, plainly.**

- **All three private margins, 0.02, 0.03 and 0.05, will most likely read NOT EVALUABLE (UNDERPOWERED) on every private part.** At the planning worst case ADR-0033 proposes (τ = 0.10) none is reachable at any G from 5 to 19, whatever the pool size; the smallest reachable margin is about 0.11 to 0.24. For 0.05 to be truly reachable the clusters would have to differ by no more than about 0.02 to 0.045; for 0.03, about 0.01 to 0.024; for 0.02, under 0.01, and not at all at five clusters or fewer.
- **The earlier statement to the human lead was too narrow and has been corrected to him.** He was first told that the 0.02 and 0.03 margins "will most likely" read underpowered (answer 5). The 0.05 margin is in the same position. The lead recorded the slip (`LEAD_RULINGS_3.md`) and put the corrected statement to him before his fourth decision. What he was told then was "at 11–19 clusters per part". The counts now expected are lower, about 5 to 10, and every figure is worse at them.
- **Choice 18 does more than pick the cautious figure. At these counts it decides whether the reading carries information.** Under the point estimate (a), at G = 13 a part reads δ = 0.02 reachable in about 54 % of M0 draws when τ = 0, 55 % when τ = 0.01 (where it is not reachable), 31 % when τ = 0.03 (true per-test power 0.66) and 8 % when τ = 0.05; δ = 0.05 reads reachable in 35 % of draws at τ = 0.05, where it is not. That is close to a coin flip, wrong in both directions, and **a wrongly "reachable" reading sizes M5 for a power it does not have.** Under the upper bound (b), with the assumed χ² interval, 0.02, 0.03 and 0.05 read reachable in only about 5 %, 8 % and 21 % of draws even when the clusters do not differ at all: the private parts then read UNDERPOWERED almost whatever the truth. Draft 1 said choice 18 "decides most of these readings" and that τ̂ "will read"; that understated it. Choice 18 is the human lead's (section 13 item 2) and is not taken here.
- **What follows for the ladder, by the approved text.** NOT EVALUABLE (UNDERPOWERED) is a registered outcome of M0 (section 10.5). It is not a defect and is never a reason to widen a margin (section 15, line 644). An underpowered part is never dropped from the conjunction (line 518). ADR-0032 section 5: an evaluation that cannot reach the power "is **NOT EVALUABLE (UNDERPOWERED)** and is not dropped silently; the domain then carries NOT EVALUABLE, which is not PARITY". So while the private evaluations are gate candidates, a domain that contains one cannot read PARITY at that margin. Whether the registered domain list keeps them as gate candidates is his choice 2, still open, and is not proposed here.
- **The private sets are then descriptive readings** (the human lead's fifth decision; lead ruling R-29). Wherever a private margin reads NOT EVALUABLE, every line that prints a private figure says so.
- **What P11 (the two-teacher student) may take from them:** per-part accuracy of each system on these items; paired differences with their t intervals on G − 1 degrees of freedom, read as intervals about these clusters; per-cluster and per-family tables; where the teachers disagree item by item; a check that the harness, the scorers and the private items behave (floor, ceiling, agreement of the solvers). **What it may not take from them:** PARITY or NO HARM on any private part at a margin that read NOT EVALUABLE; a claim that a difference generalises to other procedures of the same kind; a held-out (part B) generalisation claim at such a margin; a private figure used to offset a regression on a public set; an average over parts or evaluations (line 251). A private interval that happens to lie inside a margin is not a pass.
- Public parts (L1, K1, K2) are unaffected: their clusters are passages, premises and items.
- Nothing in this section is measured. τ is unknown until M0 is run.

## 7. The shortcut gate (new gate; bound 0.15, two-sided, set by the human lead)

ADR-0033 has no rule about tells in private items except K0's GENERATOR GUESSABLE. **Added to section 6.2, "Validity gates, no model involved" (line 275).**

1. **The bound is 0.15, two-sided. The human lead set it on 2026-11-25** (fifth decision, option 1: "Register the survivors at a bound of 0.15"). **It was set after measurements had been seen:** the lead's report to him carried the auditors' counts of clusters surviving at bounds of 0.10, 0.15 and 0.25 (`LEAD_RULINGS_4.md`). Those are measurements of items against cheap rules. No model had been run on any item, and none has been since. The record reads "observed before: yes (item-side measurements only)". It is a validity rule for items, not a threshold on any model outcome; it is not one of ADR-0033's thresholds and changes none of them. It is not presented as a number fixed blind.
2. **The drop rule (lead ruling R-24).** A lineage is dropped (NOT REGISTERED) if, at any level, any cheap rule in the union of the implementer's battery and the auditors' rule scripts (the third and fourth audits of that evaluation) scores more than 0.15 above or below the base rate, measured as those scripts measure it. Below counts as well as above, because a rule that is right less often than the base rate rules answers out. A cluster survives if at least one of its lineages survives. The scripts are part of the rule: their hashes go into G-gen's record, and they are not edited after it.
3. **Every level.** R-24 says "any registered level". This text reads that as each of the seven levels, the two reserve levels included, because a reserve level can carry the pools (section 10 item 2). That is the stricter reading and is the drafter's (section 13 item 8).
4. **No class of rule is exempt.** Draft 1 left open whether a rule that is a partial run of the procedure itself counts. Under R-24 every rule in the scripts counts. A closed form for a C1 program counts (section 2).
5. **What may be repaired (R-25), and nothing else:** the two package-hygiene failures; wording defects named in the fourth audits, by changing the wording or the stated convention and never by rejecting items on their answer; collapsed levels, so that every level produces distinct items with difficulty rising by a stated parameter. Any lineage with another audited defect is dropped: a cheap rule above the bound, a closed form, answer-conditional rejection not needed for the item to be well posed, a capacity failure that widening would not cure without collapsing levels. **No new lineage and no replacement shape.**
6. **No loop (R-26).** After the repairs the same scripts run again on every surviving lineage. Anything above the bound, with levels still not distinct, or failing capacity, is dropped, not repaired. There is no further repair round.
7. **Redrawing items conditional on a rule's outcome, or fitting a probability to it, is forbidden** (lead rulings R-1, R-13, R-18, R-19). These are lead rulings carried into this text, not the human lead's words; approving the addendum approves them. A rejected rule that scores exactly 0.00 is itself a tell.
8. Every convention an answer depends on is stated in the item. An item whose key changes under an ordinary alternative reading is a defect of its lineage (R-4), repaired in wording under item 5 or the lineage is NOT REGISTERED.
9. **What the gate does not show.** The bound holds only against the rules that were written. In each audit round the auditors found cheap rules the implementers' batteries lacked, some created by the repairs. A lineage that passes is one in which no written rule exceeds 0.15; it is not shown free of tells. This is one more reason the private readings are descriptive.

## 8. Second solvers, and lineages NOT REGISTERED

**Second solvers.** Line 261 ("an independent second solver re-derives it from the item's structured form") and line 275 ("The auditor context that writes the second solvers does not audit them: a separate auditor context audits the solver pair") stand and are made exact:

1. Three separate contexts. The author writes the generator and its solver. A second context, an `arbor-auditor` that has not read the generator's or the first solver's source, writes the second solver from the item's structured form, its schema and fixtures only. **The fixtures it receives carry no answer from the first solver** (review note N3). A third `arbor-auditor` context audits the pair.
2. A second solver written by the context that wrote the generator does not satisfy line 261. The implementation's own notes record that the existing second solvers were written by the implementer; they are rewritten under item 1 before registration.
3. Which model ran each context is recorded from session metadata.

**Registration.** A lineage is registered only when all of these hold and are recorded: its place in the map of record; its wording read by the auditor; no cheap rule above the bound at any level (section 7); levels distinct; capacity (section 10); a second solver under item 1 that agrees with the first on every fixture and on every generated item; the pair audited.

**NOT REGISTERED.** A written lineage that fails any condition, or is superseded, is marked NOT REGISTERED with its reason in the map of record. It is kept on file and never deleted. It is excluded everywhere: from the cluster count, from G, from fixtures, from capacity runs and from every tuning, development and sealed pool (lead ruling R-12). It stays a node of the graph of section 3, keeps its global cluster, and its cluster's part binds it under section 3 item 3. A global cluster with no registered lineage has no part; it is listed, and whether teaching may draw on it is settled in M1.5, not here. A cluster is not registered at some levels only: see section 10 item 5.

## 9. Statistics at fewer than 30 clusters (consequences in section 9 of ADR-0033)

No rule of section 9 is relaxed. The places below need exact text because clusters no longer sit inside families and are few.

1. **Strata (a new analysis choice; the human lead's, section 13 item 3).** Section 9.2 (line 435): "Cluster bootstrap, stratified by family or task". Section 9.4 (line 456) draws clusters "within strata" and defines τ̂² from "the variance of the cluster means within strata"; line 468 says the simulation keeps "the pairing, the strata and M5's own number of clusters". For private evaluation parts a cluster may now span several families, and with 5 to 19 clusters over 12 or more families most strata would hold one cluster. The implementation's reading is that a stratum with one cluster contributes nothing to the between-cluster variance; at these counts that drives τ̂ toward zero and the floor toward "met". **Proposed replacement reading: a private evaluation part is one stratum.** Families are printed as subcategories only (line 431). The reviewer checked the direction: one stratum is unfavourable to passing, not a relaxation (with 13 clusters over 12 family strata the truncation probability at τ = 0.03 is about 0.61, against about 0.29 with one stratum; it also widens every t interval). It still changes an analysis rule that ADR-0032 words as "subjects or task names are strata", so it is his. Public parts keep their strata (tasks, subjects).
2. **The small-sample rule now applies to every private part.** Line 435: "With fewer than 30 clusters: the cluster-robust standard error with a t quantile on (clusters − 1) degrees of freedom replaces the percentile bootstrap." Unchanged. Every private interval and bound of sections 9.1 and 10.2 to 10.4 is therefore a t interval on G − 1 degrees of freedom, and the "confirmation" bootstrap of line 460 is replaced by the same rule for private parts.
3. **Sentences that assumed G = 300** are read at the G written: the M0 draw is "balanced over the G clusters" (line 388), 79 to 300 items per cluster at G of 19 to 5, instead of about 5 (line 457); the sealed pool is "spread evenly over the G clusters" (line 390), about 1,050 to 4,000 sealed items per cluster. How items are spread inside a cluster is section 10, part B.
4. **The interval of τ̂ below 30 clusters is not defined (review 1, R8).** Line 457 prints τ̂ "with its cluster-bootstrap 90 % interval", and choice 18 (b) uses that interval's upper bound. Line 435 replaces the percentile bootstrap below 30 clusters but names no interval for a variance component. **Choice 18 (b) cannot be applied to a private part until a method is registered.** Proposed for the reviewer and the human lead, not adopted: the χ² interval of the between-cluster variance, upper bound τ_up² = max(0, V·(G − 1)/χ²₀.₀₅,G₋₁ − s_w²·mean(1/m_g)), with V the variance of the cluster means on divisor G − 1. It is the method the reviewer assumed and the one behind column (b) of section 6. It assumes roughly normal cluster means, which with 79 to 300 items per cluster is reasonable for the means and untested for the paired differences of real models. Whatever method is registered joins the known-truth gate (section 12 item 6). The divisor of V (G − 1) and the form of the standard error (sample standard deviation over √G) are fixed by the same registration; ADR-0033 leaves both open (review note N7).
5. **A part with one or two clusters (review 1, R6).** Section 4 step 5, the bound and the capacity gate can each leave a part with very few clusters. With one cluster there is no standard error, no t quantile and no τ̂: no interval of sections 9 or 10 exists. With two clusters the t quantile on one degree of freedom is 6.31 (against 1.645 for a normal) and τ̂ rests on one degree of freedom. ADR-0033 has no rule for this. **No minimum is proposed** (answer 5). Proposed reading, for the reviewer and the human lead: a part with one cluster is printed with its accuracies only, and every outcome that needs an interval reads NOT EVALUABLE for that part with the reason ONE CLUSTER; a part with two or more clusters is computed as written and its degrees of freedom are printed beside every figure. Section 13 item 7.

## 10. The capacity gate and the pool builder

**Amended sentence** (section 6.2, line 273): "**Capacity gate (G-gen).** For every cluster and level, the number of distinct items the generator can produce is at least 10 times the number the pools demand. Otherwise engineering stop."

### Part A. The gate

1. **What "distinct items" means is not ruled. It is the human lead's (lead ruling R-16; section 13 item 1).** ADR-0033 does not define it. Draft 1 wrote a structural definition (names, setting sentence and order of presentation erased) as if it were settled; that was lead ruling R-5 and is withdrawn from this text. The readings measured by the auditors are: (i) names relabelled only; (ii) labels and letters also relabelled; (iii) literal values that do not change the control flow or the solution path also discounted (under which 90 to 101 of 140 C1 cluster-levels fail). Whichever he chooses, its key function is hashed with the generators. The builder's own uniqueness test is a different thing and stays textual (part B item 6; review note N5).
2. **The demand is computed at the G of the map of record, by the worst-case reading (review 1, R1; lead rulings R-10, R-11).** The level mix of a part is chosen later (section 6.5) and may be a single level. The development pool and the sealed pool are each spread evenly over the clusters, so the largest cluster holds ⌈4,000/G⌉ + ⌈20,000/G⌉ of them. For a part with G clusters, **on each of the seven levels**:

   **D(G) = 10 × (⌈4,000 / G⌉ + ⌈20,000 / G⌉ + 100)** distinct items per cluster.

   4,000 is the development pool, 20,000 the sealed pool, 100 the tuning draw per level and part (section 8, lines 387 to 390). **The two reserve levels carry the full demand, not 10 × 100:** section 6.5 takes as candidates "every contiguous range of levels" and, if no range is interior, scores the reserve levels "and the rule is applied again", so a reserve level can carry the registered level mix and the pools with it. Taking the 100 tuning items whole for one cluster is more than the worst case (review note N8); it is kept because it is harmless and simpler. G is the cluster count of the part in question after exclusions.
3. **Values** (script part A): D(5) = 49,000; D(8) = 31,000; D(10) = 25,000; D(11) = 22,830; D(13) = 19,470; D(14) = 18,150; D(15) = 17,010; D(19) = 13,640. At the withdrawn G = 300 it was 1,810. A cluster must hold about seven and a half to twenty-seven times what it had to under the design as approved, on every one of seven levels. The sealed pool may be raised later, never lowered (line 409); a raise re-runs this gate.
4. **Per cluster and per lineage.** The gate is read on the cluster: the number of distinct items its registered lineages produce together at that level, counted on items generated by the builder of part B and not on a combinatorial argument. Because part B spreads a cluster's quota evenly over its registered lineages, each registered lineage of a cluster of k must also hold 10 times its own largest share: **D_lin(G, k) = 10 × (⌈⌈4,000/G⌉ / k⌉ + ⌈⌈20,000/G⌉ / k⌉ + ⌈100 / k⌉)**. For example D_lin(10, 2) = 12,500 and D_lin(13, 3) = 6,500. A lineage that cannot is NOT REGISTERED and the gate is read again without it, with k and, if the cluster empties, G recomputed.
5. **No cluster at some levels only.** A cluster that fails at any of the seven levels is not registered at all: registering it at some levels would make G differ by level, against the even spread of section 8 and the level rule of section 6.5. Lead ruling R-5 allowed "NOT REGISTERED at that level set"; this text refuses it and says so (the drafter's choice; conservative; reported to the human lead).
6. **The event is unchanged for the record of record:** a capacity failure there is an ENGINEERING STOP (section 10.7). Before the record, dropping a lineage is ordinary work under section 7 item 5, reported to the human lead with the list.

### Part B. The pool builder (a proposal; needs approval; section 13 item 6)

**The builder as written does not do what this addendum needs.** `studies/m0/core.py` on `claude/m0-impl` (`generate_pool`, read at `9bcec484`): it takes the lineages of a part from the family partition, gives every **lineage** an equal quota (`allocate(size, [1.0] * len(lins))`), splits each lineage's quota over levels by the level mix, draws with `stream(seed, role, salt_label, eval_id, part, lin.id, str(lv))`, and rejects an item whose normalised text has been used (`text_hash`: NFKC, case-folded, whitespace collapsed), so two items that differ only in names are two items. `m0_draw` balances the 1,500 over lineages in the same way. With lineages merged into clusters this is no longer "balanced over the G clusters" (line 388) or "spread evenly over the G clusters" (line 390): on a made-up part of 7 clusters holding 3, 2, 1, 1, 1, 1, 1 lineages the largest cluster would get 30 % of every pool instead of one seventh (script part E), and the effective number of clusters would be below G.

**Proposed builder.** For evaluation e, part p, a role, its seed, a size and a level mix, on the map of record:

1. **Clusters.** The global clusters assigned to p that have at least one registered lineage of e, in increasing code-point order of identity.
2. **Cluster quotas.** The size is divided equally over those clusters by largest remainder, ties to the cluster earlier in that order (`allocate` as written).
3. **Levels inside a cluster.** The cluster's quota is divided over the levels of the mix, in increasing level order, by largest remainder with the mix as weights.
4. **Lineages inside a cluster and level.** That count is divided equally over the cluster's registered lineages of e, in increasing order of id, by largest remainder. A lineage draws its shapes as its generator already does.
5. **Streams.** Unchanged: `stream(seed, role, salt_label, e, p, lineage id, level)`, with the derivation of section 4. A lineage's stream therefore does not depend on which cluster it sits in.
6. **Uniqueness and order.** Unchanged: an item is rejected if its normalised text is already used in any earlier role or earlier in this pool. Generation runs over clusters, then levels, then lineages, in the orders above, so the shared set of used texts is deterministic. A quota a lineage cannot fill is a capacity failure and is never moved to a sibling lineage or cluster.
7. **The M0 draw.** The 1,500 are divided equally over the part's clusters, then equally over each cluster's registered lineages, by largest remainder in the same orders; each lineage's items are sampled from its development items with `stream(400006, "m0-draw", lineage id)` as written.
8. **The record.** Every item carries its global cluster identity; pool hashes, counts "per family, cluster and level" (line 419) and every analysis use that field. The clusters of every interval and of the power simulation are these clusters, not lineages.

**Capacity is judged against a specified builder, never an assumed one (lead rulings R-22, R-28).** Until this part is approved, capacity is computed against `generate_pool` as written; a lineage that passes only under a per-cluster builder is reported as such and is not counted as passing. Once it is approved, capacity is computed against it, with the demand of part A, and the builder's code is hashed before the capacity run of record. Draft 1's sentence that items are spread "inside a lineage over its shapes" is withdrawn: a lineage's generator already chooses among its shapes, and this addendum adds no rule there.

## 11. Where the change propagates in ADR-0033

Every line number and quotation below was checked against ADR-0033 at `7719f6d4…` for this draft. The rows marked **(R10)** are the places review 1 found missing from draft 1; each was verified.

| Place | Text | Effect |
|---|---|---|
| Status, line 3 **(R10)** | "a rehearsal of stage G-gen at the proposed numbers" | Not edited. The proposed numbers included a minimum G of 300; a rehearsal under Decision 1 is now at the G written. Decision 1's limit to locked-environment work is unchanged |
| The box, line 16 | "at the proposed numbers a 3-point margin is not reachable…" | Superseded by section 6 here: at G of 5 to 19, none of 0.02, 0.03, 0.05 is reachable at τ = 0.10 |
| The box, item 4, line 22 | minimum number of clusters, "Proposed: at least 300" | Withdrawn (section 5). The worst-case τ stays his |
| The box, line 29 **(R10)** | "G-gen's record of record waits for your G and domain list" | It waits for his domain list, the approval of this addendum and the choices of section 13 that bind the record (items 1, 3, 5, 6). No minimum G |
| Section 3, line 81 | "the template-family partition" | Read as the cluster partition (section 4) |
| Section 6.1, line 251 **(R10)** | "its in-teaching-eligible half or its held-out half" | "Half" is read as "part"; the parts may be unequal (section 4 step 5) |
| Section 6.1, line 257 | "The generator is frozen before any model is run on any item. The record of record of G-gen precedes G-load" | Unchanged; it is what fixes the timing of section 4 item 7 |
| Section 6.2, table, lines 261 to 264 | R1, R2, M1, C1 rows | Unchanged, except what a C1 procedure is (section 2) and the second-solver contexts (section 8) |
| Section 6.2, line 268 | Families, lineages and clusters | Sections 1, 3 and 4 here; "(strata)" withdrawn for private parts if section 9 item 1 is approved |
| Section 6.2, line 269 | G; minimum 300 | Section 5 |
| Section 6.2, line 270 | 50-pair check; variance between shapes within a lineage printed | Check replaced (section 1 item 5). The descriptive variance component is printed between lineages within a cluster as well |
| Section 6.2, lines 271, 272, 274, 276, 277 | Difficulty, reproducibility, disjointness, interior check, stated limit | Unchanged. Distinct levels are made a condition of registration (section 8; lead ruling R-21). Disjointness and uniqueness stay textual (review note N5) |
| Section 6.2, line 273 | Capacity gate | Section 10 |
| Section 6.2, line 275 | Validity gates | Sections 7 and 8 added; the 50-item ambiguity reading stays |
| Section 6.3 | Code tracing | Section 2; otherwise unchanged |
| Section 6.4, line 300 | The family partition | Sections 3 and 4; made at G-gen's record, not at the freeze (section 4 item 7) |
| Section 6.4, items 2 to 4 | Both parts measured; public sets; seeds | Unchanged |
| Section 6.5, lines 309 and 311 | Candidate ranges; reserve levels scored and "the rule is applied again" | Unchanged; it is why a reserve level carries the full capacity demand (section 10) |
| Section 6.6 to 6.8; line 326 | Public sets, K0, domain list; K0 as teaching material | Unchanged, except section 3 item 5 on a K0 generator that implements a part-B procedure |
| Section 8, lines 387 to 392 | Split sizes | Unchanged numbers; "balanced over" and "spread evenly over the G clusters" are met by the builder of section 10 part B, not by the builder as written |
| Section 8, line 394 | "the same frozen generator, level mix, families and clusters" | Unchanged |
| Section 8, lines 396 to 407 | Why 20,000; the table | Unchanged as text. Its statements about G = 300 no longer describe the study; section 6 here is the reading at the G written |
| Section 8, line 409 **(R10)** | "The human lead chooses G's minimum with this table in view" | Withdrawn with the minimum. The table he has in view is section 6 here. The planning worst-case τ stays his to confirm |
| Section 8, line 411 | Option: lineages as strata | Not taken (section 5 item 4) |
| Section 8, lines 413 to 419 | Sealed pool, fingerprints, seals | Unchanged, except: "no teaching code may use part-B families, checked in M1.5 by template signature" is read by global cluster (section 3 item 3), and counts "per family, cluster and level" use the global cluster |
| Section 8, line 419 **(R10)** | "Held-out part B rests on procedure" | Unchanged. "Procedure" there means an administrative routine; everywhere in this addendum it means an item's algorithm (section 0) |
| Section 9.1, 9.3 | Measures; nuisance spreads | Unchanged |
| Section 9.2, line 435 | Intervals | Section 9 items 1, 2 and 5 here; the union of the teachers below 30 clusters is open (section 12 item 5) |
| Section 9.4, lines 456 to 460 | Power simulation, floor, conjunction, confirmation | Formulas unchanged. One stratum per private part if approved; G_e is the count of section 5; "Templates here are the clusters of section 6.2, that is the lineages" is read as the clusters of this addendum; τ̂'s interval is undefined below 30 clusters (section 9 item 4) |
| Section 9.4, lines 462 to 466 | Known-truth gate, six scenarios at G = 300, tolerance 0.03 | Unchanged. Open item: it does not exercise the simulation at the G the study will have (section 12 item 6) |
| Section 9.4, line 468 **(R10)** | "keeping the pairing, the strata and M5's own number of clusters" | For a private part: one stratum (if approved) and the G of section 5 |
| Section 10.1 to 10.4 | Outcome rules | Unchanged; private bounds are t bounds (section 9 item 2); a part of one cluster has none (section 9 item 5) |
| Section 10.5, line 518 | NOT EVALUABLE (UNDERPOWERED) | **Unchanged.** Consequence in section 6 |
| Section 10.6 | Projection | Unchanged; an underpowered part enters at its pool maximum, as written |
| Section 10.7, line 530 | Events | Unchanged; a cheap rule above the bound found at the record of record is an ENGINEERING STOP like the other validity gates |
| Section 12, line 562 | "Family partition into parts A and B: 400004" | Role renamed "cluster partition into parts A and B"; value unchanged; labels and derivation of section 4. For the seed-registry auditor (section 12 item 7) |
| Section 12, line 576 **(R10)** | "Per-evaluation, per-family, per-cluster and per-level streams are derived by SHA-256 of the seed with a text label" | Unaffected in substance. Section 4 states the derivation exactly; it is the one the implementation already uses. "Per-cluster" streams of the builder are keyed by lineage id (section 10 part B item 5) |
| Section 12, other rows | Seeds | Unchanged. No seed value is added or chosen here |
| Section 13, G-gen row, line 587 | "for the record: choices 2 and 10 (G)" | The record needs choice 2, this addendum's approval and section 13 items 1, 3, 5 and 6; no minimum G. It also holds the map of record, the partition and its code hash, G per part, the cheap-rule scripts' hashes and tables, and the builder's hash |
| Section 13, F row, line 595 | "family partition" | Cluster partition, already fixed at G-gen's record; F hashes it again |
| Section 13, Roles, line 614 | Auditor contexts | Section 8; one more context for the map of record |
| Section 14, line 628 | "registered minimum of 300 per private part" | Withdrawn; all other sizes unchanged |
| Section 14, line 632 | Thresholds | **Unchanged** |
| Section 15, line 644 | UNDERPOWERED "would not mean a reason to widen the margin" | Unchanged |
| Section 16, choice 10, line 662 | minimum G | Withdrawn from the list; the rest of choice 10 stands |
| Section 16, choices 18, 19 | τ floor; strata | 18 still his (section 13 item 2). 19 not taken |
| Section 16, line 673 | "whether 300 distinct lineages … can be written" | Answered by the audits: no |
| Section 17, line 691 | Held: "The minimum G" | No longer held; the worst-case τ stays held |
| Section 18, line 709 | "drawn only from part A families" | Read as: drawn, among the private generators, only from lineages of part-A global clusters. A cluster with no part is neither; whether teaching may draw on it is M1.5's (section 8). Material from other sources is section 3 item 4 |
| Section 19 | Departures from ADR-0032 | Rows added (section 15 here) |

## 12. Inconsistencies and open items found while drafting

Flagged, not resolved by wording.

1. **The first decision's premise.** The option the human lead chose first read "Keep lineages as clusters and repair M0 to hundreds of lineages … The stronger claim survives". The count reached is 5 to 19 clusters per part, and by section 6 the claim that clusters were kept for (a parity gate that generalises to other procedures of the same kind) will most likely be NOT EVALUABLE at every registered margin on the private parts. He has since been told so and has decided twice with it in view (fourth and fifth decisions). The fourth report gave 11 to 19 clusters per part; the fifth carried the table of clusters surviving at 0.15 per evaluation (10, 20, 18, 17). The arithmetic of section 6 at 5 to 10 per part is new and has not been put to him.
2. **The coordinator's reading of the second answer** ("The definition in section 6.2 is not amended") against answer 1. This addendum reads section 6.2's definition strictly and adds an operational test; it also replaces the 50-pair check and adds global identity. Those are amendments in substance. They need his approval of this text, not only "Adopt all five" (section 13 items 4 and 10).
3. **Answer 4 against "at least 12 families (strata)" and stratification by family.** Clusters shuffled across families cannot be nested in family strata. Section 9 item 1 proposes one stratum. The reviewer confirmed its direction. It is his.
4. **Answer 3 against answer 4 as it was put to him** ("about 13 / 14 for R1"). The cross-evaluation rule can force unequal parts, down to one cluster in a made-up case (section 4 step 5). `LEAD_RULINGS_3.md` records that 18 of R2's 37 clusters also appear in another evaluation, so this is not remote. The number of cross-evaluation clusters is not known until the map of record exists.
5. **The union of the teachers at fewer than 30 clusters.** Line 435 requires that G_U be "recomputed in every resample, including which teacher is the better one, so that choosing the better teacher on the same data is inside the bound". The small-sample rule of the same line has no resamples. The implementation uses a linearisation with the better teacher fixed at the point estimate, so the choice is outside the bound. This is a gap in ADR-0033 as written; it touches every private part's complementarity reading (section 10.4). A registered small-sample rule for G_U is needed and is not drafted here.
6. **The known-truth gate does not cover the study's G.** Its six scenarios are at G = 300 (line 464). The simulation will run at G of 5 to 19, with one stratum, a t quantile and a τ̂ that is truncated to zero in about a tenth to more than a half of draws (section 6). Proposal: add scenarios at the G of the map of record, under the same tolerance, without removing or loosening any of the six, and including whatever interval method section 9 item 4 registers. Not drafted as amending text because it adds a gate and its scenario list is a set of numbers.
7. **The seed.** Section 12 gives one seed for this role, 400004; it is reused and no value is invented. Reusing it under new labels is sound (review 1, Q3) provided the mechanics and code are fixed first (section 4 item 8). Open for the seed-registry auditor: the role's name changes; the labels `cluster-partition` replace `family-partition`; and the block 400001–409999 is still a proposal, since no `SEED_REGISTRY_R6.md` exists.
8. **Lead rulings against this text.** R-5 allowed a lineage "NOT REGISTERED at that level set"; section 10 item 5 refuses partial-level registration. R-24 says "any registered level"; section 7 item 3 reads seven levels. Both differences are stated and are in the stricter direction.
9. **Borderline pairs across parts.** A borderline pair with one member in part A and one in part B weakens the held-out reading without breaking the rule. The count is printed. Section 13 item 9.
10. **"Typed grammar" in the C1 row (line 264) against answer 2.** A program drawn from a grammar has no named algorithm unless the lineage fixes one. The drafter did not verify each C1 lineage.
11. **G may fall further.** Transitive closure across evaluations, the bound, distinct levels and the capacity gate at 25,000 to 49,000 distinct items per cluster and level each remove clusters, and the narrow round allows no repair of a capacity failure by new authoring. A part may end with fewer than five clusters. Section 6 gets worse with every cluster lost, and section 9 item 5 applies.
12. **The cheap-rule gate rests on the rules written** (section 7 item 9).

## 13. Decisions that remain the human lead's

None of these is decided here. For each: the options, and the lead's recommendation in a line. Items 1 to 6 and 10 are the ones the lead named to him after his fourth and fifth decisions; items 7 to 9 and 11 come from the review and from drafting.

1. **What counts as a distinct item for capacity (R-16).** Options: (i) names relabelled only, with exact duplicates of the rendered question removed; (ii) labels and letters also relabelled; (iii) literal values that do not change the control flow or solution path also discounted. Lead's recommendation: (i), because the gate's sentence counts "distinct items"; it is the most favourable of the three, which is why the lead did not adopt it himself.
2. **Choice 18 of ADR-0033: the τ used for the floor.** Options: (a) the point estimate; (b) the upper bound of τ̂'s 90 % interval, which first needs an interval method registered (section 9 item 4). Lead's recommendation: (b), as ADR-0033 already records, with the χ² interval. Consequence either way, from section 6: under (a) the reading is near a coin flip and can size M5 wrongly; under (b) the private parts read UNDERPOWERED almost whatever the truth.
3. **One stratum per private part.** Options: (a) one stratum (section 9 item 1; unfavourable to passing); (b) family strata as ADR-0032 words them, which needs a rule for clusters that span families and leaves about one degree of freedom for τ̂. Lead's recommendation: (a).
4. **The same-procedure test of section 1 item 1 (review 1, R7).** Options: (a) approve the written test and have the map of record re-judged against it; (b) no written test: the auditors' recorded judgement is the rule and item 1 is a description. Lead's recommendation: (a), because without a written test a third party cannot check the map.
5. **The partition mechanics.** Three choices, all to be fixed before any split is computed (section 4 item 8). The split: the two-step rule of section 4 (drafted) or one global shuffle (simpler; halves per evaluation left to chance). Odd counts: ⌊G/2⌋ to part A (drafted) or to part B. Transitive merging: a cross-evaluation component merges lineages of one evaluation that its own map kept apart and lowers G (section 3 item 2, drafted), or binds their part only. Lead's recommendation: the two-step rule, the larger half held out, and merging, since over-counting clusters is the harmful error.
6. **The per-cluster pool builder (section 10 part B).** Options: (a) approve it, and judge capacity against it; (b) keep `generate_pool` as written, which balances over lineages, so that a merged cluster gets several shares and pools are not "spread evenly over the G clusters". Lead's recommendation: (a).
7. **A part with very few clusters (review 1, R6).** Options: the reading of section 9 item 5 (one cluster: NOT EVALUABLE, ONE CLUSTER; two or more: computed, degrees of freedom printed); or a minimum number of clusters for any interval, which would be a new registered number. Lead's recommendation: the reading of section 9 item 5; no number.
8. **Levels for the bound.** Seven (drafted, section 7 item 3) or the five registered levels. Lead's recommendation: seven.
9. **Borderline pairs.** Left free (drafted), or kept in one part for the partition only without merging them for G. Lead's recommendation: kept in one part; it costs no cluster and protects the held-out reading.
10. **Approval of this addendum.** Options: approve; approve with changes; send draft 2 to a second independent review first. Lead's recommendation: a second review first. Sections 7, 9 items 4 and 5, and 10 part B are new text that no reviewer has read, and approval of this text is also approval of the lead rulings it carries (section 7 item 7) and of "no minimum at all" (section 5 item 1).
11. **Already his under ADR-0033 and unchanged:** the domain list (choice 2), including whether the private evaluations stay gate candidates knowing section 6; the planning worst-case τ, the pool size and every other number of section 14; additional known-truth scenarios at the study's G (section 12 item 6); a small-sample rule for the union of the teachers (section 12 item 5), to be drafted and reviewed.

Lineages as strata (choice 19) is not on this list. He has decided that lineages are clusters.

## 14. What this addendum does not change

- No margin, grid value, alpha, power value, band, cap fraction, tolerance, hour ceiling, pool size, draw size, ladder or token limit.
- The power rule, Boole's bound, the simulation's formulas and the rule of section 10.5.
- Clusters as random effects; choice 19 is not taken.
- The order of stages, the freeze, the sealed pools and who reads them, Decision 1's limit to locked-environment work, and Decision 2.
- Every other choice of section 16 of ADR-0033, each still the human lead's.
- The models, the stack, the one-system rule, the public sets, K0, the domain list, the download limit.
- Every non-claim of section 1. M0 measures reference models only; capability parity of ArborLM is untested.
- Every earlier record. ADR-0033, its reviews, the audits, the superseded shapes, draft 1 of this addendum and the failed attempts stay as they are.

## 15. Where the addendum departs from ADR-0032 and ADR-0033 as written

| # | Text as written | What the addendum does | Whose call |
|---|---|---|---|
| A1 | ADR-0033 section 6.2: a registered minimum G (proposed 300) before G-gen's record | No minimum; the count reached is registered | Human lead (answer 5; "no minimum at all" confirmed by approving section 5) |
| A2 | ADR-0033 section 6.4: families are split into parts; "Half each" | Global clusters are split; halves per evaluation only where the cross-evaluation rule allows | Human lead (answers 3, 4); mechanics: section 13 item 5 |
| A3 | ADR-0033 section 6.2: the 50-pair check within a family | Every pair within an evaluation and the cross-evaluation links, by an auditor whose map governs | Human lead (answer 1) |
| A4 | ADR-0033 sections 6.2 and 9.2; ADR-0032 section 5 ("subjects or task names are strata") | Private parts are one stratum each; families are descriptive | Human lead (section 13 item 3) |
| A5 | ADR-0033 section 6.2: capacity counted on "distinct items", demand implied at G = 300 | Worst-case demand at the G written on all seven levels; no partial-level clusters; "distinct" left to him | Lead after review; "distinct": human lead (section 13 item 1) |
| A6 | ADR-0033 has no gate on tells in private items | A gate at 0.15, two-sided, **set by the human lead after item-side measurements had been seen, no model run**; the drop rule of R-24; no redraw (lead rulings R-1, R-13, carried into the text) | Human lead (the bound: fifth decision); the rulings: approved with this text |
| A7 | ADR-0032 section 4, a private set "where one can be built"; section 5, an underpowered evaluation makes its domain NOT EVALUABLE, "which is not PARITY" | Private sets are built, at a cluster count that by section 6 most likely cannot support the gate at any registered margin; they are stated as descriptive readings. ADR-0032's rule is applied as written; nothing is dropped from the conjunction | Human lead (fifth decision; choice 2) |
| A8 | ADR-0032 section 4: generalisation is "an in-teaching-distribution part and an out-of-teaching part" of every evaluation | The out-of-teaching part is defined by procedure across the four private evaluations, not per evaluation | Human lead (answer 3) |
| A9 | Answer 3 constrained parts | The teaching ban is extended to unregistered lineages of part-B clusters and to material generated by, derived from or imitating them | Lead after review; then human lead |
| A10 | ADR-0033 section 6.4 and section 13, F row: the partition is made at the freeze | Made at G-gen's record, hashed again at F | Lead after review |
| A11 | Answer 1: "strict, using the auditors' maps" | Section 1 item 1, an operational test written by the drafter; if approved, the map of record is re-judged under it | Human lead (section 13 item 4) |
| A12 | Answer 3 said nothing about G | Transitive merging inside an evaluation, a new rule that lowers G | Human lead (section 13 item 5) |
| A13 | ADR-0033 lines 388 and 390: pools "balanced over" and "spread evenly over the G clusters"; the builder as written balances over lineages | A per-cluster builder is specified; capacity is judged against it once approved | Human lead (section 13 item 6) |
| A14 | ADR-0033 line 457: τ̂ "with its cluster-bootstrap 90 % interval" | States that no interval exists below 30 clusters; proposes one, adopts none | Human lead, with choice 18 |
| A15 | Draft 1 section 2: a closed-form C1 shape is replaced by a traced-state shape | Dropped, not replaced (R-14, R-25) | Human lead (fifth decision) |

## 16. Response to review 1, item by item

| Item | Where addressed, or why not |
|---|---|
| **B1** partition not reproducible from the text | Section 4, "The mechanics, complete": the string, separator, encoding, hash, truncation, generator, shuffle algorithm, ordering before the shuffle, id format, split point, the case k > \|L_e\|; test vectors in `partition_vector.out.txt`; item 8 (fixed and hashed before any split is computed) |
| **B2** section 6 understated choice 18 | Section 6, table (d) and "What this means, plainly", with the reviewer's figures and the drafter's figures at G of 5 to 10; all three margins stated as most likely NOT EVALUABLE; descriptive readings; what P11 may and may not take. Choice 18 not decided (section 13 item 2) |
| **R1** capacity worst case | Section 10 part A items 2 and 3: separate ceilings; reserve levels at full demand; 22,830, 17,010, 1,810 |
| **R2** when the map and partition stop changing | Section 4 item 7; section 15, A10 |
| **R3** transitive merges | Section 3 item 2, stated as a new rule that lowers G; section 13 item 5; section 15, A12 |
| **R4** scope of the teaching ban; K0 | Section 3 items 3, 4 and 5 (the reviewer's replacement text); section 11, row for line 709; section 15, A9. One addition beyond the reviewer's text: until he decides, a listed K0 generator is not used for teaching |
| **R5** "every global cluster" | Section 3 item 3: "with at least one registered lineage" |
| **R6** part B overfull; very few clusters; no minimum at all | Section 4 step 5; section 9 item 5; section 13 item 7; section 5 item 1. A reading is proposed for one cluster; no number is proposed |
| **R7** the operational test is the drafter's | Section 1 item 1, marked, with the statement that the map of record is re-judged under it if approved; section 13 item 4; section 15, A11 |
| **R8** τ̂'s interval below 30 clusters | Section 9 item 4: stated as a gap; a method proposed, none adopted; tied to choice 18 |
| **R9** mechanics chosen and code hashed first; ⌊G/2⌋ marked | Section 4 item 8; step 3 marks the choice as the drafter's; section 13 item 5 |
| **R10** propagation rows | Section 11: lines 3, 29, 251, 409, 468, 419 ("procedure") and 576, each verified against ADR-0033 and marked **(R10)**; also lines 257, 309, 311 and 326 added |
| Q1 table: battery gate; R-1 carried in | Section 7 item 7; section 15, A6 |
| Q7: which cross-evaluation pairs "section 3 requires" | Section 1 item 5 defines it |
| N1 C1 count 28 or 29 | Section 1 item 4: both sources named; neither figure is used |
| N2 stratification is conservative | Section 9 item 1 |
| N3 fixtures without first-solver answers | Section 8 item 1 |
| N4 borderline pairs against "over-counting is the harmful error" | Section 1 item 3; section 13 item 9 |
| N5 distinctness structural for capacity, textual for disjointness | Section 10 part A item 1 and part B item 6; section 11. Not changed: ADR-0033's disjointness and uniqueness rules stay textual; changing them is outside this addendum |
| N6 13.5 ± 2.3 reproduced | Section 4, closing paragraph |
| N7 divisor of V; CR0 or CR1 | Section 6 (rules used); section 9 item 4: to be fixed with the interval method. Not fixed here: it is an analysis rule of ADR-0033 and goes with choice 18 |
| N8 tuning 100 taken whole | Section 10 part A item 2: kept, stated as more than the worst case |

Not addressed, and why: nothing in the review is left without a place above. Two things the review asked for are met by proposals and not by rules, because a rule would be a new registered choice: the reading for very small parts (R6) and the interval method (R8).

## 17. What changed from draft 1

- **Capacity:** D(11) 22,820 → 22,830; D(15) 17,000 → 17,010; at G = 300, 1,800 → 1,810; a reserve level 1,000 → D(G). New values at G of 5, 8, 10: 49,000, 31,000, 25,000. Per-lineage demand D_lin added.
- **The range of G:** 11 to 19 per part → 5 to 19, from the counts at the bound of 0.15. Tables of section 6 recomputed for 5, 8, 10, 13, 19; the figures at 13 and 19 are unchanged.
- **Table (c)** is now the t test (0.129 and 0.105 at τ = 0.10 for G = 13 and 19), not the normal formula (0.121 and 0.101).
- **Section 6's conclusion:** from "unless τ̂ is at most…" to the reading being random; all three margins most likely NOT EVALUABLE; descriptive readings.
- **The shortcut bound:** from open to 0.15, two-sided, with the drop rule; replacement shapes withdrawn.
- **"Distinct item":** from a structural definition to an open decision.
- **New text:** the partition mechanics; the pool builder; the reading for one or two clusters; the interval gap; the response table.

## 18. Record

- Draft 2 by one context (`arbor-lead`, Claude Fable 5.2, `claude-fable-5-2`, as the session states it). No delegation was made. Review 1 was by an `arbor-auditor` context (Claude Opus 5.5, as its report states). Draft 2 has not been reviewed. Not approved by anyone.
- Read for it: ADR-0033 revision 4 (the cited lines, each checked); ADR-0032 section 5's power rule; draft 1; review 1 and the outputs of its six scripts; `HUMAN_LEAD_WORDS.md` and `_2` to `_5`, `LEAD_RULINGS_2.md` to `_5.md`, and `studies/m0/core.py` (`derive_seed`, `stream`, `family_partition`, `allocate`, `draw_items`, `generate_pool`, `m0_draw`) on `claude/m0-impl` at `9bcec484`, read-only.
- Run for it, locked environment, standard library only, no model: `addendum1_rev2_arithmetic.py` and `partition_vector.py` in `docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/`, outputs beside them (`partition_vector.py` `79b8b093…c1ae`, its output `a123304a…eaba`). Neither reads a cluster map. `uv run --locked ruff check .` was run at the end.
- Not verified by the drafter: any auditor's cluster judgement or count; the cheap-rule measurements behind the bound; the measured capacity tables; the number of cross-evaluation components; the state of the narrow round; the reviewer's direct simulation (its output was read, not re-run); that no model has been run anywhere outside the two worktrees; the state of the seed registry beyond the files named.

`SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`
