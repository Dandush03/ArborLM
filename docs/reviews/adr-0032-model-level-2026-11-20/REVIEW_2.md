# Independent design review 2 of ADR-0032 (revision 2, commit 9881701)

Reviewer: arbor-auditor subagent (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-20. Claude review is not Astra review. `Astra review: NOT_PERFORMED`. This is not human approval and not validation. ArborLM is unproven research; nothing here is a result.

## What was read and run

**Read** (worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/model-level-requirements`, HEAD 9881701):
- ADR-0032 revision 2;
- `docs/reviews/adr-0032-model-level-2026-11-20/` `HUMAN_LEAD_STATEMENT_2.md`, `LITERATURE_NOTE_1.md`, `DELEGATION.md`;
- the scorecard commit 3b702b9.

**Ran** (trivial CPU, Python 3.15.1, standard library, `python3 -I`):
- `diff` of ADR Part A2 (lines 40–91) against the statement file (lines 5–56): identical.
- `diff` of A1 against draft 1's Part A at 2c1e523: identical apart from headings.
- `cmp` of `LITERATURE_NOTE_1.md` against `experiments/_scratch/audits/LITERATURE_ADR-0032.md`: identical bytes.
- `experiments/_scratch/audits/adr0032_power/power2.py`, output in `power2.out.txt` beside it.

The literature note was not re-fetched. Statements below "from my own knowledge" are marked as such and are unverified.

## Verdict

**READY AFTER THE LISTED EDITS** for the rules of Parts B–D that E2 proposes to approve under the delegation, except section 7's superiority labels: they should not be approved until G1 is fixed.

**NOT READY as a frame for Part S** until G5–G10 are addressed. Part S is not under the delegation anyway, so this blocks nothing this weekend; it should go to the human lead with those edits applied or listed.

Review 1's findings: F1–F19 all closed; F2 and F13 closed not as written, both acceptable. Details in section 1.

## 1. Status of Review 1's findings

| F | Status | Note |
|---|---|---|
| F1 | Closed | Section 2 "Final acceptance"; section 8 adds acquisition cost, forgetting relative to Tier 1, and Tier 2 comparisons. |
| F2 | Closed not as written; acceptable with G3 | The fallback replaces my unclear clause. It makes the cap a flag rather than a constraint: δ_e is never lowered. That is defensible, because δ_e is the human lead's substantive value and a pair where S₀ is already non-inferior cannot discriminate. "Must be at most" still reads as a constraint, and the split on which S₀'s non-inferiority is read is not stated. G3 gives wording. |
| F3 | Closed, with gaps (G4) | Power rule present. Two things are not defined: which discordance is used, and whether the NO HARM tests count in the conjunction. |
| F4 | Closed | |
| F5 | Closed | |
| F6 | Closed | "One stack, one precision" added, which improves on my wording. |
| F7 | Closed, with a gap (G2) | The equal-bytes and equal-compute references are defined relative to S, whose size is unknown at M0. |
| F8 | Closed | The regression cap is left to each specification (E1.4). |
| F9 | Closed | |
| F10 | Closed | The no-backbone-retraining condition is added from statement 2, which is correct. |
| F11 | Closed as I wrote it, but my wording was defective (G1) | |
| F12 | Closed, with a gap (G11) | The L-series could consume M5's sealed splits. |
| F13 | Closed not as written; acceptable | The M1a / M1.5 / M1b split is better than my proposal: M1b cannot be specified without the teaching procedure, and M1a is correctly an engineering check. Gap: "non-look-up" in M2 is not defined operationally (G5). |
| F14 | Closed as a statement, with gaps (G12) | The download total is still not computed, and the cost estimate uses a different stack and precision from the one M0 must use. |
| F15 | Closed | |
| F16 | Closed | |
| F17 | Closed | Put to the human lead as E1.6. |
| F18 | Closed | E2 is limited to rules; Part S is outside the delegation. |
| F19 | Closed as a proposal, but E3 is out of step (G13) | Four rows are already committed in 3b702b9. |

The table at the end of the ADR matches the text for every row. One exception: the F2 row says the fraction is "kept as a proposed value", which is true, but it does not mention that the cap no longer lowers δ.

## 2. Part A fidelity

- A2 is verbatim and complete against `HUMAN_LEAD_STATEMENT_2.md`, including the closing line. Whether that file is itself verbatim to the human lead's message I cannot check.
- A1 is unchanged from draft 1.
- Parts B–S are faithful on almost every point. The exceptions are G14 (the mapping of "preserve complementary capabilities"), G15 (INTERFERENCE is not part of acceptance) and G16 ("once sufficiently capable" against component-scale pillar A).
- No frozen outcome is reinterpreted.

## 3. Findings

### G1. REQUIRED (must be fixed before E2.3 covers section 7). The "domain-level router" control is vacuous, and this is my error from Review 1.
Within a single domain, "each item sent to the teacher better on that domain" is the better teacher, so the router control equals the better-teacher control. As a result COMBINES (NO GAIN BEYOND ROUTING) and SUPERIOR BY COMBINATION are decided by the better teacher alone. The labels are also not exhaustive: S above the better teacher but below a real router gets no label. Replace the three label bullets of section 7 with:

> - The routing controls are: (i) a per-item router learned on the development split from features available at inference time (no oracle), and (ii) the better teacher with k samples and majority vote (or best-of-k by the same verifier S may use), k set so its inference cost does not exceed the registered multiple of S's. Their better score per evaluation is "the best control".
> - **COMBINES (NO GAIN BEYOND ROUTING)**: S non-inferior to the best control and not above it beyond δ_e.
> - **BELOW ROUTING**: S's bound against the best control below −δ_e (printed even when S exceeds the better teacher).
> - **SUPERIOR BY COMBINATION**: S's lower bound against the better teacher and against the best control both exceed δ_e, and S does not exceed the item-level union beyond δ_e.
> - **SUPERIOR BEYOND THE UNION**: S's lower bound against the item-level union exceeds δ_e, or S solves composition items that no teacher, no control and no registered pipeline solves.

The note's evidence supports both controls (RouterBench: learned routers reach the best single model; Self-MoA: sampling the best model k times beats mixing). Both are in section 4 only as "candidates"; promote them.

### G2. REQUIRED. The equal-bytes and equal-compute references cannot be chosen in M0 as worded.
S's stored bytes and active compute are unknown until S is built, but section 4 fixes those references "in M0 before any score of S". Replace in section 4 Tier 2 (b), (c):

> (b) and (c) are chosen in M0 against a registered **upper bound** on S's total stored bytes and on its active compute per token, fixed in M0's specification. S may not exceed either bound in any later test; a design that needs more is a new reference choice, made before it is scored.

### G3. REQUIRED. Make the cap operational.
Replace from "In addition, for every reference R…" to "…contributed." with:

> **Cap.** For every pair (R, e), let L be the lower 95 % bound of (score of R − score of S₀) on the development split in M0. The pair is CAP MET if δ_e ≤ L/2, and CAP NOT MET otherwise. δ_e is never raised or lowered by the cap. A CAP NOT MET pair is still gated at δ_e; when S₀ itself passes non-inferiority to R on e on the same split and items as S, it is also labelled S₀ ALREADY NON-INFERIOR. Every PARITY verdict prints the count of CAP NOT MET and S₀ ALREADY NON-INFERIOR pairs. Coverage (section 7) and the advantage of section 2 are never read on an S₀ ALREADY NON-INFERIOR pair.

Recommended, the human lead's call: fix δ_e in M0's specification before M0 scores anything. As worded, δ_e may be set after the development-split gaps of the references are seen, which is a researcher degree of freedom.

### G4. REQUIRED. Close the gaps in the power rule.
Add to "Statistics":

> The conjunction for the power rule contains every test of the gate: every (evaluation, split part, Tier 2 reference) parity test and every NO HARM test against S₀. The discordance used is, per evaluation, the largest measured in M0 between S₀ and any Tier 2 reference. Power is computed by simulation from the measured paired item outcomes, not by assuming independence. The sealed test split is generated (or drawn from an oversized sealed pool by a registered seed) at the size so fixed. Clusters are items sharing a passage, template or problem; subjects or task names are strata (stratified resampling), not clusters. Where an evaluation has fewer than 30 clusters, a registered small-sample method replaces the percentile bootstrap.

Scale check (power2.out.txt, independence assumed): with 4 domains × 2 parts × 4 Tier 2 references plus 8 NO HARM tests (m = 40), overall power 0.8 needs about 17.5·d/δ² items per test. That is 3,889 items at d = 0.2, δ = 0.03, and 5,834 at d = 0.3, per evaluation part. Discordance between a 1B student and a 9B teacher is plausibly near 0.3. Section 9 should print this order of magnitude.

The "subject" fix corrects my own Review 1 F3 wording, which listed "a subject" as a cluster.

### G5. REQUIRED. Define "non-look-up" (M2, PB-1).
PB-1 and the label NON-LOOK-UP NOT CARRIED depend on this definition, and it does not exist. Add to M2:

> A capability is **non-look-up** for this test only if (i) its evaluation items come from templates or task families held out from teaching, and (ii) on the development split the Tier 1 system "S₀ with retrieval over the teaching data" does not exceed S₀ beyond δ_e. Both are checked before S is scored.

### G6. REQUIRED. Part S labels that ordinary practice, curricula or stored content can earn.
- **SELF-DIRECTED GAIN (ONE CYCLE) requires beating only arm 2 (uniform random).** A simple difficulty curriculum beats uniform random. Require arm 1 to exceed, beyond the margin: arm 2; arm 3; a new arm 2b, random items with the same difficulty histogram as arm 1's selections; and a new arm 9, a non-learned adaptive curriculum that keeps the verified success rate in a registered band. Otherwise the label is GAIN FROM CURRICULUM, NOT FROM SELF-DIRECTION.
- **Stored content.** "MATCHED BY RETRIEVAL" is only a qualifier. Replace with: if arm 7 is non-inferior to arm 1, the label is GAIN EXPLAINED BY STORED SOLUTIONS, not SELF-DIRECTED GAIN. Also add: sealed items are checked against all practice items by exact and near-duplicate match, because both come from the same frozen generator.
- **ACCUMULATES OVER k CYCLES requires no baseline comparison.** Random practice for K cycles may accumulate equally. Add to the label's conditions: "and the cycle-k arm-1 system exceeds arms 2, 2b, 3 and 9 run for the same K cycles at equal cumulative compute, beyond the margin. Otherwise ACCUMULATES (NOT ATTRIBUTABLE TO SELF-DIRECTION)."
- **Per-cycle multiplicity.** "At least m cycles each show a gain … lower bound above zero" at one-sided 0.05 per cycle gives spurious "gains". With no true gain, P(at least 2 of 10) ≈ 0.086 and P(at least 2 of 20) ≈ 0.26 (power2.out.txt). Require per-cycle tests at 0.05/K, or Holm over the K cycle tests, and define "repeats in R independent runs" as "holds in each of the R runs".
- **Promoted-checkpoint selection.** Add to S2: "The checkpoint that carries a claim is the one named by the registered promotion rule, fixed before sealed scoring. It is never chosen by sealed score. All cycles' sealed scores are printed."
- **Equal compute and equal examples cannot both be matched.** Make compute primary, print examples. For arm 4, the teacher's inference compute is reported separately and not charged to the student budget; a secondary comparison at equal total compute including teacher inference is printed.
- **Self-graded feedback.** In L-B3, "an independent validity check" must be a frozen program that establishes the item's answer itself, never a model. Move the second-verifier sample of S5 into L-B1 as well; reward hacking of a verifier starts in the first cycle.
- **ERROR REINFORCEMENT "rises".** Define as a registered one-sided trend test on per-cycle rates.

### G7. REQUIRED. Separate elicitation from acquisition: a concrete control (the drafter's concern 4).
Add to S4 arms, and make SELF-DIRECTED GAIN conditional on it:

> Arm 10, the elicitation ceiling: S₀ (and the cycle-0 system) with best-of-N sampling filtered by the same verifier, N registered (e.g. 64), and with the arm-1 practice items' verified solutions as in-context examples. A gain whose sealed score does not exceed this ceiling beyond δ is labelled GAIN WITHIN ELICITATION CEILING (DRAWING OUT NOT EXCLUDED). In addition, at least one practised family is a **novel** family (invented rules or entities generated after every model's release, on which S₀ is at floor even at best-of-N). Acquisition is claimed only there.

From my own knowledge, unverified: there are 2025 reports that verifier-rewarded training mostly raises pass@1 towards the base model's pass@k without raising large-k pass@k. If so, that makes this control decisive. It belongs in the pending self-learning literature check.

### G8. REQUIRED. "Cannot inspect or optimise" is not operationally enforceable as written on one machine under one account.
S2 says separation is "enforced by the operating system (separate user, file permissions, no network)".
- **Needs administrator access.** Creating a separate macOS user needs it, and DELEGATION.md excludes administrator access. So does a reliable network block for a native training process.
- **The real adversary is not the improving process.** The agents and people writing it can read every file on the account, and earlier seals (P10) were procedural.

**Enforceable on this machine:**
- (a) Commit-reveal. The sealed and new-family sets **do not exist** during the run. They are generated after the last cycle from a frozen generator and a seed whose SHA-256 was recorded (in git, on another branch) before cycle 1. The seed is held by the human lead or drawn after the run from a public source. This is the only seal that holds against everyone on one account.
- (b) Tamper evidence. Hashes of harness, evaluation code, limits and stop rules, recorded outside the run directory before the run and checked after. This detects; it does not prevent.
- (c) Model-generated code run in a container without network (needs the image download and approval).
- (d) An append-only ledger whose running hash is recorded outside the run.

**Not enforceable:**
- separation of the promotion set from the improving process against its authors;
- "no read access" for a native process under the same user;
- agents not looking.

Replace the first paragraph of S2 with:

> **Three roles, three processes** (improving process, evaluator, supervisor). Enforcement on this machine is: (a) the sealed and new-family sets are created only after the last cycle, by commit-reveal of a seed recorded before cycle 1; (b) hashes of harness, evaluation code, limits and stop rules recorded outside the run before cycle 1 and checked after every cycle, a mismatch making the run INVALID (TAMPERED); (c) model-generated code executed only in a networkless container; (d) an append-only ledger with a running hash recorded outside the run. Operating-system user separation would need administrator access and the human lead's approval; until then, separation of the promotion set is procedural and is disclosed as such.

### G9. REQUIRED. Pillar A: "self" and the baselines.
- **The shift test is not required for any label.** As written, SELF-OPTIMISES (COMPONENT) is earned by any learned policy that beats external search on one workload, which is ordinary learned-index or meta-optimisation work. Make the S3 "one place 'self' could mean something" paragraph a fourth gate for both SELF-OPTIMISES labels. Without it, use LEARNED POLICY BEATS EXTERNAL SEARCH (COMPONENT).
- **Define "external search at equal compute".** The same action space; the same observable signals; a named algorithm (random search and one model-based search); compute counted the same way, including the self-optimiser's meta-training and design-time runs on the tuning workload; the held-out and shifted workloads sealed until both are frozen; the better of the external searches used.
- **Cost on a shared machine.** Prefer counted physical costs (bytes and reads from the device, FLOPs) to wall time, or require a quiet machine as P10-I-S1 does. PA-1 inherits S1's blockage otherwise.
- **The human lead's words "identify inefficiencies in its own operation"** are not tested by any stage. Recommended: an L-A0 measurement of whether the system's own signals rank its bottlenecks as measured profiling does. PENDING LEAD REVIEW.

### G10. REQUIRED. Make S6 (learning efficiency) sound.
- **"What a system already knew … does not move the measure" is false.** Prior knowledge changes gain through transfer and through headroom (ceiling, regression to the mean). Replace with: "The measure is the normalised gain (after − before)/(max − before), and the number of examples to reach a registered criterion, on new families where both systems start in the interior; starts are printed and the difference in starts is reported beside the measure."
- **Define the storage control.** "Everything the cycle-k system stored" is learned vectors, not text. Replace with: "the verified practice items and solutions of cycles 1..k, retrieved by a registered retriever into the cycle-0 system's context, under the same learning budget; and the cycle-0 system with its memory enlarged by the same number of untrained rows (capacity control)". LEARNS FASTER (NOT EXPLAINED BY STORED CONTENT) requires cycle-k's lower bound against both controls to exceed a registered margin.
- **New families need sealed splits.** The new families need a learning split and a sealed test split, and both are created by commit-reveal (G8).

### G11. REQUIRED. The L-series must not consume M5's sealed splits.
L-A3 and L-B run before M5 and read "every registered evaluation". Add to S2: "L-stages use development splits of the M evaluations or their own sealed sets; they never score an M5 sealed test split."

### G12. REQUIRED. Section 9 feasibility.
- **Download total.** Replace "neither was counted" with: "The cumulative total already downloaded under the delegation is counted and printed in M0's specification before any choice of set; a set that does not fit with the code-execution image and the (b)/(c) references is not specified."
- **Cost estimate.** The note's throughput figures are llama.cpp 4-bit. Section 4 requires the M1 stack and precision (PyTorch MPS or MLX, BF16), so the estimate is a lower bound of unknown slack. Also, G4's item counts × about 10 systems (S, S₀, 4 Tier 2, 5 Tier 1) put M5 beyond "one to three days". Add: "The power rule's item counts multiplied by every system and both splits can place M5 in weeks of machine time; if M0's pilot projects that, the gate is NOT EVALUABLE LOCALLY, recorded as such. Infeasibility is never a reason to widen δ_e or drop a reference; any reduction of scope is the human lead's explicit change of the requirement."

### G13. RECOMMENDED. Scorecard consistency.
- E3 says "the lead will not edit `docs/scorecard/`", but commit 3b702b9 already added four rows, at the human lead's request. E3 should say so, give the committed text, and leave only the fifth row and the F19 note change as proposals.
- ADR line 7 cites the git-ignored scratch path of the literature note. Cite the committed `docs/reviews/adr-0032-model-level-2026-11-20/LITERATURE_NOTE_1.md` (identical bytes).

### G14. RECOMMENDED (PENDING LEAD REVIEW). The mapping of "preserve complementary capabilities" raises the bar.
Preserving each teacher's strengths is coverage: non-inferiority to each teacher where it leads, plus no INTERFERENCE. PARITY with both teachers already implies the first part. Mapping it to SUPERIOR BY COMBINATION requires exceeding the better teacher, which is the combination question ("whether their combination enables additional capabilities"). Proposed E1.5 wording:

> "Preserve complementary capabilities" = coverage with no INTERFERENCE; "whether their combination enables additional capabilities" = SUPERIOR BY COMBINATION or BEYOND THE UNION; "capabilities that neither teacher provides independently" = SUPERIOR BEYOND THE UNION only.

### G15. RECOMMENDED (PENDING LEAD REVIEW). INTERFERENCE is outside acceptance.
A loss beyond the margin against the single-teacher S is a regression that an average could hide (statement 2, property 1). Propose: "INTERFERENCE on any evaluation bars final acceptance."

### G16. RECOMMENDED (PENDING LEAD REVIEW). "Once sufficiently capable".
Statement 2 frames self-learning as for ArborLM "once sufficiently capable". L-A0–L-A2 at component scale are a reading that goes earlier. That is acceptable as component evidence with (PARITY UNTESTED), but it should be listed in E1.11 as a choice, not assumed.

### G17. RECOMMENDED. The phrase "recursive self-improvement".
The rule is close but not tight. Add to S7:

> Neither the phrase nor a synonym ("self-improving system", "recursive", "compounding self-improvement", "improves its ability to improve") appears in any label, report, scorecard, README or commit message. "Independently validated" in his rule is not met by Claude audit alone; it needs at least recomputation from raw records by a party other than the run's author plus Astra validation or the human lead's acceptance. Even ACCUMULATES together with LEARNS FASTER does not license the phrase; only his decision does.

### G18. RECOMMENDED. Literature spot-check (no re-fetch; marks as in the note).

| # | Claim the ADR leans on | Representation | Comment |
|---|---|---|---|
| 1 | Dutta et al. 2024: 4-bit flips 5.7–10.9 % of MMLU answers "while the total barely moves" (section 4) | Slight overstatement | The note gives −0.8 to −2.1 points, which is not "barely" against a margin of 2–3 points. Say "while the total moves by 0.8 to 2.1 points". Consistent with my own recollection of the paper's thesis. |
| 2 | Sclar et al. 2023 (formatting up to 76 points); Alzahrani et al. 2024 (rankings move up to 8 places) | Fine | Matches my recollection. |
| 3 | Geng et al. 2024: kNN-LM helps memory tasks, mostly lowers reasoning (section 9) | Hedged, but the mechanism differs | kNN-LM is non-parametric output interpolation, not a trained key-value memory read into the residual stream. Say so; it is suggestive, not "direct" evidence. |
| 4 | Memory layers that helped broadly were trained jointly from scratch (Lample 2019; Berges 2024) | Fine | From my own knowledge, unverified: a 2025 Meta report on continual learning by sparse fine-tuning of memory layers (reporting less forgetting than LoRA or full fine-tuning) is directly relevant to properties 3 and 4 and is missing. Add it to the check. |
| 5 | FuseLLM below the best source on every code task; RouterBench oracle 0.957 against 0.828; Self-MoA beats mixed MoA | Fine as [V] | I cannot confirm the exact numbers. These support G1. |
| 6 | Miller 2024: about 1,000 questions per evaluation | Fine | Matches my recollection of the paper's recommendation. |
| 7 | Licences: GLM-4-9B-0414 MIT; older glm-4 licence with a naming clause; some Qwen2.5 sizes under other licences | Hedged correctly | Consistent with my recollection (Qwen2.5-3B and -72B differ); the naming clause I cannot confirm. |
| 8 | Cost: "hours per model, one to three days for four models" | Understated for this design | See G12: different stack and precision, and too few items for the power rule. |

Entries dated after my knowledge cutoff (Qwen3.5/3.8, GLM-5.x, M5 throughput rows) I cannot check at all.

"Published 'student beats teacher' results rest on this [V]" (section 4): the note says "mostly". Use "rest mostly on".

## 4. The drafter's own concerns

1. **Gate possibly unpassable.** Stated in parts (section 9, power, Tier 2 "may be unattainable"), but nowhere as a rule on what happens. G12 gives the wording: NOT EVALUABLE LOCALLY, and no widening of δ or dropping of references.
2. **Download budget not totalled.** Stated, but not made a precondition. G12 makes it one.
3. **Pillar A's "self" thin.** Stated (S1, section 9) but not built into the labels. G9 makes the shift test a gate.
4. **B and C only in rule-checkable domains; no elicitation-against-acquisition control.** The scope limit is stated adequately (section 9, S4). The control is missing; G7 provides it.
5. **Containment not built.** Stated, but S2 asserts OS enforcement as if it were available. G8 replaces it with what is enforceable and discloses the rest.

## 5. Part E

**E2 against "for my approval".**
- E2.1 (margin rule) and E2.2 (power rule) are rules governing future tests, not tests. Approving them under the delegation is consistent with his words, after G3 and G4.
- E2.3 should be narrowed:
  - the two levels of evidence, and the labels of sections 5 and 6: acceptable;
  - section 7's labels: not acceptable until G1 is fixed. Their mapping to his words is E1.5 and his;
  - the "final acceptance" definition operationalises his own "ultimate success criterion". It follows his words closely, but he may want to own it. Recommend approving it and flagging it first in the Monday list.
- E2.4 (ladder order): acceptable as an order only, since each rung needs its own approval.

Nothing in E2 needs to move to E1 except the section 7 labels.

**E1, my recommendations.**

| # | Recommendation | Same as the drafter? |
|---|---|---|
| 1 | Agree, with G2 (upper bounds on S's bytes and compute fixed in M0). | Agrees, with G2 |
| 2 | Agree; fix δ_e before M0 scores (G3). | Agrees, with G3 |
| 3 | Agree: four domains plus mathematics and multilingual. | Same |
| 4 | Print always; additionally guard subcategories: no registered subcategory with at least a registered number of items may fall below R by more than 2·δ_e. | Differs slightly |
| 5 | As G14. | Differs |
| 6 | Agree. | Same |
| 7 | Agree at 0. Keep the fifth row separate: his closing sentence is the point of the pillar. | Same |
| 8 | Agree; specify M0 after G2, G4, G12 and the re-read of the note's relied-on items. Downloads, lockfile and run held for him. | Agrees, with conditions |
| 9 | No recommendation of a set. Considerations: set C needs transformers from main (lockfile) and multimodal checkpoints; set B is the simplest but has the oldest teachers; avoid glm-4-licensed models. | — |
| 10 | Accept as a frame only after G5–G11. | Agrees, with conditions |
| 11 | L-A0 first, after the self-learning literature check, with counted costs (G9). Present the component-scale reading as his choice (G16). | Agrees, with conditions |
| 12 | Agree; add the cycle-multiplicity rule (G6). | Agrees, with G6 |
| 13 | Agree, with (PARITY UNTESTED). | Same |
| 14 | Yes, with G5's definition. | Same, with G5 |
| 15 | Agree, with G17. | Same, with G17 |

## 6. Own slips, recorded

- **Review 1, F11.** I introduced the "domain-level router", which within one domain is just the better teacher (G1).
- **Review 1, F3.** I listed "a subject" as a bootstrap cluster; subjects are strata (G4).
- **Review 1, write path.** The first write was refused by a worktree hook (already recorded there).
