# Review 2 of ADR-0033 addendum 1 (lineage clusters), draft 2

- Reviewer: `arbor-auditor` context, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-25. I wrote none of the draft, none of ADR-0033, none of review 1 and none of the implementation.
- `Astra review: NOT_PERFORMED`. This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. It approves nothing and decides nothing; scientific questions are marked PENDING LEAD REVIEW.
- ArborLM is unproven research. Nothing here is a result about any model. No model was loaded, run or scored; nothing was downloaded or installed; no git state was changed; nothing was written in any worktree.

## Inputs, by hash

| File | SHA-256 | Matches the draft's citation |
|---|---|---|
| `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` (draft 2, HEAD `a2fb316f3abdc2e18dc38f71b0fc7e0dfb1078c5`) | `0df152b1…087f` | n/a |
| Draft 1 (`git show 2c390259:…`) | `bb276504…9868` | yes |
| `docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md` | `7719f6d4…ec90b` | yes |
| `addendum1_scripts/addendum1_rev2_arithmetic.py` / `.out.txt` | `256ff109…1245` / `14345463…850c` | yes / yes |
| `addendum1_scripts/partition_vector.py` / `.out.txt` | `79b8b093…c1ae` / `a123304a…eaba` | yes / yes |
| `addendum1_scripts/power_small_g.py` / `.out.txt` | `6f846f3e…1945` / `6851f2c4…ee50` | yes / yes |
| `HUMAN_LEAD_WORDS.md`, `_2` … `_5`; `LEAD_RULINGS_2` … `_5` (worktree `agent-a0c9d741…`, HEAD `9bcec484`) | all nine match the draft's prefixes/suffixes | yes |
| `studies/m0/core.py` at `9bcec484` (read-only) | read for `stream`, `family_partition`, `allocate`, `generate_pool`, `m0_draw` | n/a |

## Environment and commands

macOS 27.2.1 arm64; uv 0.12.15; CPython 3.12.14 (locked environment). All scripts are standard library only and import nothing from `studies/`, from the drafter's scripts or from review 1's scripts. Run from the specification worktree root, output only to my folder:

```sh
D=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_addendum1_review2_20261125/deliver
S=docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts
uv run --locked python $D/partition_from_text_review2.py > $D/partition_from_text_review2.out.txt   # written before reading partition_vector.py
uv run --locked python $D/arithmetic_review2.py         > $D/arithmetic_review2.out.txt          # ~6 s; MC seed 20261125
uv run --locked python $D/cr0_small_g_review2.py        > $D/cr0_small_g_review2.out.txt
uv run --locked python -I -B $S/addendum1_rev2_arithmetic.py > $D/rerun_drafter_addendum1_rev2_arithmetic.out.txt
uv run --locked python -I -B $S/partition_vector.py         > $D/rerun_drafter_partition_vector.out.txt
```

Both reruns of the drafter's scripts are byte-identical to the committed outputs (SHA-256 `14345463…850c`, `a123304a…eaba`). `git status` of the specification worktree was unchanged afterwards.

Process disclosures. (1) The Write tool's worktree hook refused the deliver path (it lies in the base checkout's git-ignored `experiments/_scratch/`); I wrote the files there with a shell heredoc instead, as the brief directs. No other path was written. (2) My own slips, kept: in `arithmetic_review2.py` the line "largest tau at any n (n -> inf), delta=0.05 … (approx, normal-in-mean)" uses an incorrect mixed formula (t quantile plus the normal target quantile); it is not used for any finding. My reconstruction of the test-vector map (made from the `.out.txt` only) marked `R1.delta` registered, where the drafter's map has it NOT REGISTERED; this does not change any output because `R1.gamma` is registered in the same component.

## Verdict

**APPROVABLE AFTER REQUIRED CHANGES.** 1 blocking (F1), 13 required (F2–F14), 10 notes (F15–F24).

The two blocking items of review 1 are resolved. The partition reproduces from the text alone, byte for byte, and every number in sections 6, 9 and 10 that I recomputed reproduces except one (F7: the stated size of the CR0/CR1 effect). The new blocking finding is about order, not arithmetic: the text defines registration, capacity, G per part and the partition in terms of each other, with no stated order. As a result the registered partition cannot be computed in only one way.

## Q2. The partition from the text alone (B1)

I implemented section 4 from the addendum's text before reading `partition_vector.py` (`partition_from_text_review2.py`). I rebuilt the made-up map from `partition_vector.out.txt`, using its components, its parts and its per-evaluation counts.

- Derived integers for all five labels, SHA-256 digests, and the shuffle of `a`…`h` on all five streams: **identical** to `partition_vector.out.txt`. The spelled-out loop (`i` from n−1 down to 1, `j = _randbelow(i+1)`) gives the same lists as `random.shuffle` (asserted).
- The whole procedure on the made-up map: cross order `M1.alpha, C1.beta, C1.gamma, C1.alpha`; part A and part B; per-evaluation (4,2,2), (5,2,3), (4,2,2), (4,2,2): **identical**.
- Ambiguities I had to resolve. Each is a finding.
  1. What "X clusters of e" means in step 3 (a_e): clusters with a *registered* lineage in e, or with *any* lineage in e. The test vector cannot tell the two apart. My probe (section 4 of the output) has an X cluster with registered R1 and R2 lineages and an unregistered C1 lineage, and the two readings give different C1 parts: A/B = 2/2 against 1/3 (F6). The drafter's code uses "registered".
  2. G_e in step 3 counts clusters over the whole evaluation. Section 0 and section 6 define G_e per part (F4).
  3. Which side is larger when |X| is odd. Step 2 starts with A, so A has one more. Step 3 and section 13 item 5 hold the larger half out (F5).
  4. The order between the partition and the capacity gate (F1).
- Not exercised by the vector: the clamp k_e = |L_e|; a_e > ⌊G_e/2⌋ (step 5); a cluster with no registered lineage ("unassigned: []"); an odd |X|; the a_e ambiguity (F19).
- I checked `studies/`, `tests/` and `docs/` on `claude/m0-impl` at `9bcec484`, and the uncommitted working tree of that worktree. Neither contains the label `cluster-partition` (`git grep` and `grep -r`, no match). The draft's R9 statement holds.

## Q3. Numbers recomputed (all reproduce except F7)

| Draft place | Draft | Mine (`arithmetic_review2.out.txt`) |
|---|---|---|
| 6(a) floor, z sum 4.33, 15 cells | as printed | 4.3289; all 15 cells round to the draft |
| 6(b) largest τ within 20,000, 15 cells | as printed | identical to 4 decimals; G = 5, δ = 0.02 "none" |
| power at τ = 0, δ = 0.02 | 0.9935 (G = 5); 0.9991–0.9995 (G 11–19) | 0.9935; 0.9991–0.9995 |
| 6(c) smallest δ, t test, 15 cells | as printed | identical |
| 6(d) P(τ̂ = 0), 15 cells | as printed | identical (χ² approximation). Direct item-level simulation, 3,000 draws per cell: G = 5: 0.597, 0.284, 0.113; G = 10: 0.560, 0.279, 0.094 (MC s.e. ≤ 0.009) |
| 6(d) small-G reachability table, 36 cells | as printed | identical (χ²). Direct simulation, point estimate, G = 5 and 10, τ ∈ {0, 0.03, 0.05}: within 0.006 of the χ² figures (e.g. G = 10, τ = 0.03: 0.289 / 0.364 / 0.586 against 0.290 / 0.362 / 0.584) |
| 6, "0.11 to 0.24"; "0.02 to 0.045"; "0.01 to 0.024"; "under 0.01" | as printed | 0.105–0.244; 0.0187–0.0453; 0.0088–0.0236; 0.0040–0.0094 |
| 6, rules used: CR0 raises table (b) "by 0.0004 to 0.0008" | as printed | **Not reproduced at G ≤ 10:** +0.0010, +0.0008, +0.0011 (G = 8); +0.0012, +0.0016 (G = 5); at G = 5, δ = 0.02 becomes reachable (τ ≤ 0.0016) (F7). Holds at G = 13 and 19 |
| 9.1: 0.61 against 0.29 | as printed | 0.611; 0.289 |
| 9.3: 79–300 items, 1,050–4,000 sealed per cluster | as printed | 78.9–300; 1,052.6–4,000 |
| 4 closing (N6): 13.5 ± 2.3 | as printed | 13.5, s.d. 2.286 |
| 10 A.3: D(5, 8, 10, 11, 13, 14, 15, 19, 300) | 49,000 … 1,810 | identical; ratio 7.54–27.07 ("seven and a half to twenty-seven") |
| 10 A.4: D_lin(10,2), D_lin(13,3) | 12,500; 6,500 | identical |
| 10 B, part E: 30 % | 0.300 | 0.3 |
| 1.4 counts 10/20/18/17 (15); 27/38/22; 18 of 37 | as printed | match `LEAD_RULINGS_4.md`, `_2.md`, `_3.md` |

Not recomputed: review 1's step-5 scenario (47 %, one cluster). Its scenario parameters are in review 1's script, which I did not reuse. The reachability simulation computes τ* at d = 0.3 and does not re-estimate d̂ per draw, so it is an idealisation like the drafter's.

## Findings

### Blocking

**F1 (blocking). Registration, capacity, G per part and the partition are defined in a circle, with no stated order.** §8 registers a lineage only after capacity (§10). §10 A.2 computes the demand "at the G of the map of record … G is the cluster count of the part in question after exclusions", so it needs the partition. §4 step 1 partitions "only global clusters with at least one registered lineage", so it needs registration. §10 A.4 says that after a drop "the gate is read again … with k and, if the cluster empties, G recomputed", but it never says whether the partition is then recomputed. At least three implementations fit the text, and they register different parts:
- (a) partition once, then drop clusters for capacity without re-partitioning, which leaves unequal parts;
- (b) re-partition after every drop, which reshuffles every remaining cluster;
- (c) iterate to a fixed point.

§4.8 ("every partition ever computed is kept") does not say which one governs. This is the determinism that B1 required, one level up. Required change: state the order. One example is computing capacity at a G fixed in advance, such as the evaluation's ⌈G_e/2⌉ or the smaller part, then registering, then partitioning once. If drops after the partition are allowed, state what happens to the partition. The order itself is the human lead's to approve as part of §13 item 5 (PENDING LEAD REVIEW).

### Required

**F2 (required). Capacity "against `generate_pool` as written" cannot be run under the cluster partition, and no demand formula is given for it.** §10 B (last paragraph) and R-28: "Until this part is approved, capacity is computed against `generate_pool` as written". In `core.py` at `9bcec484`, `generate_pool` calls `part_lineages`, which calls `family_partition`, which splits *families* on the label `family-partition`. So the interim rule pairs a builder that implements the withdrawn family partition with the cluster partition of §4. D(G) and D_lin(G, k) are also derived for the per-cluster builder. Under the builder as written, the demand per lineage is D evaluated at the number of *lineages* in the part, and a cluster of k lineages carries k shares. The text gives neither. State which partition the interim run uses and give its demand formula, or state that no capacity run of record happens before §13 item 6 is decided.

**F3 (required). "Two-sided" is attributed to the human lead, but his recorded words do not contain it.** Section 7's heading, §7.1 ("The bound is 0.15, two-sided. The human lead set it") and A6. `HUMAN_LEAD_WORDS_5.md` quotes option 1 as "Register the survivors at a bound of 0.15" and the answer "1". "Two-sided" comes from lead rulings R-3 ("per level, two-sided") and R-24. It is probably the convention behind the counts he was shown, but the record does not say so. Attribute it accurately: the human lead set the number 0.15, and two-sidedness is the measurement convention of R-3/R-24, carried in and approved with the text. Everything else in the description of the bound is accurate against the records: it was set after item-side measurements had been seen ("observed before: yes (item-side measurements only)"), before any model run, the 0.10/0.15/0.25 table was in his report, and it is not one of ADR-0033's thresholds.

**F4 (required). G_e has two meanings.** §0 defines "G, G_e" as the clusters "in one part of one private evaluation", and §6 uses G_e per part (the floor and the t test on G_e − 1 df). §4 step 3 uses "G_e is the number of global clusters with a registered lineage in e", which is the evaluation total. That is the only reading under which k_e = ⌊G_e/2⌋ − a_e makes sense, but an implementer who follows §0 reads it per part. Rename the step-3 quantity (for example N_e).

**F5 (required). The larger half goes to A among cross-evaluation clusters, which contradicts "the larger half held out", and the choice is not disclosed.** §4 step 2: "index 0 … to A … With an odd number A has one more." Step 3 and §13 item 5 (lead's recommendation: "the larger half held out") send the larger half to B. When X dominates an evaluation, step 2 decides that evaluation's balance. §13 item 5 lists only the step-3 odd-count choice. Mark step 2's start-with-A as the drafter's choice and add it to §13 item 5 (PENDING LEAD REVIEW).

**F6 (required). "a_e is the number of X clusters of e" can be read two ways.** Is a cluster "of e" when it has a registered lineage in e, or any lineage in e? An X cluster can include an unregistered lineage of a third evaluation. My probe shows the two readings give different parts (C1 2/2 against 1/3). Write "with a registered lineage in e".

**F7 (required). The CR0/CR1 sentence is wrong at the counts now expected, and one conclusion depends on that choice.** §6, rules used: "with the other form every figure of table (b) rises by 0.0004 to 0.0008". That range is review 1's at G = 11–19. At G = 10 the rise is 0.0006–0.0009, at G = 8 it is 0.0008–0.0011, and at G = 5 it is 0.0012–0.0016. At G = 5, δ = 0.02 is reachable under CR0 for τ ≤ 0.0016 (`cr0_small_g_review2.out.txt`). So "At G = 5 or fewer, δ = 0.02 is not reachable inside the pool even if the clusters do not differ at all" holds only under the CR1 form, which ADR-0033 does not fix (N7). Correct the range and qualify the statement. Fixing CR0 or CR1 matters more at small G than the draft says (PENDING LEAD REVIEW, with §9.4).

**F8 (required). The draft gives inconsistent and incomplete lists of what G-gen's record waits for.** §5.2 says the record "needs his domain list (choice 2). It no longer waits for a minimum G." The §11 rows for lines 29 and 587 say: choice 2, approval of the addendum, and §13 items 1, 3, 5 and 6. Three further items bind the map of record or the partition, which are fixed at that record (§4.7):
- item 4, the same-procedure test, under which the map of record is re-judged;
- item 8, seven or five levels for the bound, which decides which lineages survive;
- item 9, keeping borderline pairs in one part, which changes the partition, and §4.8 hashes the partition code only after "the choice of section 13 item 5".

Item 3 (one stratum) is an analysis rule and does not bind G-gen's record. Make one list and use it in §4.8, §5.2 and §11.

**F9 (required). An unlisted change: line 460's confirmation bootstrap.** §9.2: "the 'confirmation' bootstrap of line 460 is replaced by the same rule for private parts". Line 460 is the power-confirmation step of §9.4 ("2,000 simulations with the full percentile bootstrap inside"), not an interval of §9.2. The §11 row for lines 456–460 says "Formulas unchanged", and §15 has no row for it. Either it follows from line 435, and the text should say why (the simulation's inner test is the t rule at G_e < 30), or it is a change and needs a §15 row.

**F10 (required). The consequence of the missing τ̂ interval for M0's printing is not stated.** ADR-0033 line 457: "Until it is decided M0 prints the floor both ways". Line 700 (§17): for choices 15–19, "Nothing in M0 waits". §9.4 here: "Choice 18 (b) cannot be applied to a private part until a method is registered." Together these mean M0 cannot print the upper-bound floor for any private part until a method is registered. So either something in M0 now waits, or the private floor is printed one way only. Neither consequence is stated, and line 700 is missing from §11.

**F11 (required). A departure from lead ruling R-11 is not listed.** R-11: "G is the smaller part's cluster count after exclusions". §10 A.2: "G is the cluster count of the part in question". For the larger part this is less strict. Per-part G is defensible, but §12.8 claims to list the lead rulings this text departs from, names only R-5 and R-24, and describes both as being "in the stricter direction". Add R-11 and say which direction it goes.

**F12 (required). Disclosure of post-observation choices is narrower than the facts.** The header says "One number in it was set after measurements had been seen: the shortcut bound". Several pending decisions will also be taken with item-side counts in view, and each changes which clusters are registered:
- §13 item 1, the "distinct item" reading: R-16 measured 90–101 of 140 C1 cluster-levels failing under reading (iii), and the human lead has the counts;
- item 8, levels for the bound: per-level cheap-rule results exist;
- items 5 and 9, merging and borderline pairs: the working maps exist.

None of these involves a model. But ADR-0033 fixes thresholds before observation, and the bound itself is recorded as "observed before: yes (item-side measurements only)". Ask for the same record line on each of these decisions.

**F13 (required). The consequence of "at least 12 families" at the counts reached is undefined.** §4.6: "'At least 12 families' (line 268) stays as a requirement on the registered lineages of an evaluation". At a bound of 0.15, R1 has 10 surviving clusters (`LEAD_RULINGS_4.md`). Whether its registered lineages still span 12 families is not known, and the text does not say what follows if they do not: an engineering stop, NOT REGISTERED for the evaluation, or a descriptive flag. One evaluation may fail this requirement as soon as it is applied, so state the consequence or withdraw the requirement (PENDING LEAD REVIEW).

**F14 (required). The list of what P11 may not take omits the teacher readings.** §6, "What P11 … may not take". P11 is the two-teacher study. §12.5 says the small-sample rule for G_U (complementarity, §10.4 of ADR-0033) is a gap. The implementation's linearisation fixes the better teacher at the point estimate, so it is "outside the bound". At G < 30 the same applies to every private part's COMPLEMENTARY / NO COMPLEMENTARITY reading. Yet the may-take list includes "where the teachers disagree item by item", and the may-not list says nothing about complementarity or TEACHER AHEAD on private parts. Add: no COMPLEMENTARY reading from a private part until a small-sample rule for G_U is registered. Apart from this, the description of the private sets as descriptive readings matches `HUMAN_LEAD_WORDS_5.md` and R-29, and is honest. Notable lines: "a private interval that happens to lie inside a margin is not a pass", no averaging over parts or evaluations, no offsetting of a public regression, no generalisation to other procedures.

### Notes

**F15 (note).** §6(d): "A τ̂ of zero meets the floor and makes the simulated power meet the target as well". This is false at G ≤ 5 for δ = 0.02: power is 0.9935 at τ = 0, below the 0.9964 target. The parenthetical covers only G 11–19, but the section now spans G 5–19.

**F16 (note).** §6, may-take list: "t intervals … read as intervals about these clusters". A cluster-robust t interval estimates the mean over the population of clusters, not over these specific clusters. Reading it as about these clusters is conservative, not anti-conservative, but the wording invites a fixed-effects reading. Since the human lead has chosen clusters, consider "intervals under the cluster model, on G − 1 df, from these clusters".

**F17 (note).** The may-not list does not exclude *adaptive* use: choosing P11's teaching design (teacher, mix, curriculum) on part-B development readings. That would weaken part B as a held-out set for M5, which uses the same clusters. PENDING LEAD REVIEW whether to add it.

**F18 (note).** §3.1–3.2: unregistered lineages remain nodes, so an unregistered lineage in another evaluation can join two registered lineages of e into one cluster and lower G_e. That follows from the text, but it is not said, and the link judgements will involve lineages dropped for tells. State it.

**F19 (note).** The test vector does not exercise the k_e clamp, step 5 (a_e > ⌊G_e/2⌋), an unassigned cluster, an odd |X| or F6's case. A second vector covering these would make the hashed code's conformance test (§4.8) meaningful. Its "no cluster in both parts" assertion holds by construction.

**F20 (note; review 1 N1 partly).** §1.4 says "the 29 being the implementer's map". `LEAD_RULINGS_3.md` labels the column only "(map)", and `HUMAN_LEAD_WORDS_3.md` calls 27/38/22/29 "the auditors' maps". The records I read do not support the attribution. Neither figure is used, so nothing changes.

**F21 (note; review 1 R6).** "No minimum at all" (§5.1) has no §13 item with options of its own. It is approved only by bundling, through item 10 and A1 ("confirmed by approving section 5"). `HUMAN_LEAD_WORDS_2.md`'s reading says the minimum "is still his to state and is not assumed". Consider listing it as its own decision.

**F22 (note).** An ENGINEERING STOP for a cheap rule above the bound found *at* the record of record appears only in the §11 row for line 530, not in §7. §10 A.6 draws the same before-record/at-record distinction for capacity explicitly. Put it in §7.

**F23 (note).** §1.4 and §6 cover G from 5 to 19, while §12.11 says a part "may end with fewer than five clusters". The drafter's output already has table (b) at G = 3 and 4 (δ = 0.03: τ ≤ 0.0012 and 0.0063). Printing those would show the human lead what the lower end looks like.

**F24 (note).** The drop rule says the bound is "measured as those scripts measure it". It is reproducible only if each script's item sample (seed, items per level) and its base-rate definition are fixed with its hash. Results near 0.15 are subject to sampling noise. State that the scripts are seeded and that their per-level sample sizes are recorded.

## Q4. Changes to ADR-0033 beyond the list

I checked every line number and quotation in §11 against ADR-0033 at `7719f6d4…`, including lines 3, 16, 22, 29, 81, 251, 257, 261–277, 300, 309, 311, 326, 387–419, 435, 456–468, 518, 530, 562, 576, 587, 595, 614, 628, 632, 644, 662, 673, 691 and 709. All are accurate. No margin, grid value, alpha, power value, tolerance, pool size, ladder or the planning τ is changed. The items missing from the list are F9 (line 460), F10 (lines 457 and 700) and F11 (R-11, a lead ruling, not an ADR line). Nothing found relaxes a threshold. The CR0/CR1 point (F7) is an existing gap in ADR-0033 that matters more at small G; it is not a change.

## Q5. Decisions belonging to the human lead

Nothing found is decided in the text without being flagged, except:
- the start-with-A alternation in step 2 (F5);
- the per-part G of the capacity demand against R-11 (F11, which is the lead's own ruling).

The K0 interim restriction (§3.5), the refusal of partial-level registration (§10 A.5) and the seven-level reading (§7.3) are disclosed as the drafter's. Lineages remain clusters; I make no recommendation on strata.

## Status of review 1's items (verified against the text, not the response table)

| Item | Status | Where / residual |
|---|---|---|
| B1 partition reproducibility | **Resolved** | Reproduced byte for byte from text alone. Residual: F1 (order), F4, F5, F6 |
| B2 reading is random | **Resolved** | §6(d), "What this means"; figures reproduce. Residual: F7, F15 |
| R1 capacity worst case | **Resolved** | Formula and values reproduce. Residual: F2, F11 |
| R2 when fixed | **Resolved** | §4.7, A10 |
| R3 transitive merges | **Resolved** | §3.2, §13.5, A12. Note F18 |
| R4 teaching-ban scope; K0 | **Resolved** | §3.3–3.5, §11 row for line 709, A9; the K0 interim restriction is a disclosed addition |
| R5 "with at least one registered lineage" | **Resolved** | §3.3 |
| R6 overfull B; very few clusters; minimum | **Mostly resolved** | §4 step 5, §9.5, §13.7. "No minimum at all" is only bundled (F21) |
| R7 operational test is the drafter's | **Resolved** | §1.1, §13.4, A11 |
| R8 τ̂ interval below 30 | **Partly** | Gap stated, method proposed, none adopted; the consequence for line 457/700 is missing (F10) |
| R9 mechanics and code hashed first | **Partly** | §4.8 for item 5; items 4 and 9 also bind (F8) |
| R10 propagation rows | **Resolved** | All rows verified. Further missing rows: lines 460 and 700 (F9, F10) |
| N1 C1 28 vs 29 | **Partly** | Both named, neither used; the attribution of 29 is unsupported (F20) |
| N2 stratification conservative | **Resolved** | §9.1; 0.611 / 0.289 reproduce |
| N3 fixtures without answers | **Resolved** | §8.1 |
| N4 borderline pairs | **Resolved** | §1.3 mitigation; §13.9 |
| N5 structural vs textual | **Resolved** | Stated, not changed |
| N6 13.5 ± 2.3 | **Resolved** | Reproduces (s.d. 2.286) |
| N7 divisor; CR0/CR1 | **Partly** | Deferred to the interval registration; the effect size stated is wrong at G ≤ 10 (F7) |
| N8 tuning 100 whole | **Resolved** | §10 A.2 |

## Files

In `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_addendum1_review2_20261125/deliver/`:

| File | SHA-256 |
|---|---|
| `partition_from_text_review2.py` / `.out.txt` | `0235789a…4fae` / `96f15559…bb75` |
| `arithmetic_review2.py` / `.out.txt` | `5371233c…f109` / `bfa9f364…abb7` |
| `cr0_small_g_review2.py` / `.out.txt` | `fed816ba…17fd` / `eeceaed7…c169` |
| `rerun_drafter_addendum1_rev2_arithmetic.out.txt` | `14345463…850c` (identical to committed) |
| `rerun_drafter_partition_vector.out.txt` | `a123304a…eaba` (identical to committed) |

## What I could not verify

- The auditors' cluster judgements and every count.
- The cheap-rule measurements behind the bound.
- Whether the counts shown to the human lead were two-sided.
- Whether R1's registered lineages span 12 families.
- The number of cross-evaluation components.
- The state of the narrow round: the implementation worktree has 60 uncommitted changes, including `*_fix4*` manifests, which I did not read.
- That no model has been run anywhere outside the worktrees I looked at.
- Review 1's step-5 scenario.

`Astra review: NOT_PERFORMED`
