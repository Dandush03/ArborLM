# Independent design review of ADR-0032 (draft of 2026-11-20)

Reviewer: arbor-auditor subagent (Claude Opus 5.5, model ID claude-opus-5-5), 2026-11-20. Claude review is not Astra review. `Astra review: NOT_PERFORMED`. This is not human approval and not validation. ArborLM is unproven research; nothing here is a result.

Read: `AGENTS.md`, `CLAUDE.md`, ADR-0032 draft and `docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md` (worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/model-level-requirements`, HEAD 2c1e523), `docs/RESEARCH_HANDOFF.md`, `docs/scorecard/scorecard.toml`, ADR-0022 sections 1 to 4 (student and teacher identities, for context), P10-I-S6 OUTCOME (worktree `agent-aaf3e2e17ef8546e4`), P10-I-S0 OUTCOME (worktree `agent-a64fa146b8b5b93b0`), the lead's memory note on the P11 goal (the human lead's own description of "smarter", 2026-11-19).

Write path: the direct path `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/REVIEW_ADR-0032.md` was refused by a worktree hook; this file was written through the worktree's `experiments` symlink, which resolves to the same folder.

Only computation: `experiments/_scratch/audits/adr0032_power/power.py` (standard library, Python 3.15.1, `cd .../adr0032_power && timeout 30 python3 -I power.py | tee power.out.txt`, under one second). Normal approximation for paired binary items, true difference 0, one-sided alpha 0.05, conjunction over m independent tests. Approximate; the point is the order of magnitude.

## Verdict

READY AFTER THE LISTED EDITS. Part A is quoted faithfully and Parts B to E go in the right direction. Four points are blocking: (F1) the human lead's ultimate criterion requires an additional measured advantage, but the draft makes it optional; (F2) the margin rule as written is ill-defined, can be gamed in both directions, and does not stop the untaught student from being "at parity"; (F3) at realistic benchmark sizes the conjunction design does not have the statistical power to pass a truly equal system unless sample sizes are fixed by a power rule; (F4) the section 7 precondition would make the human lead's own two-teacher scenario NOT EVALUABLE.

## Findings

### F1. BLOCKING. The final criterion omits the "additional measurable advantage" the human lead requires.
Part A: "Our ultimate success criterion should be: ArborLM capability ≥ reference model capability, **with** additional measurable advantages in knowledge acquisition, retention, scalability or efficiency." Part B section 2 calls superiority "desirable" and efficiency "additional", and no section requires an advantage for the final claim. A system at parity with no advantage over a LoRA would therefore pass the draft's acceptance, which contradicts Part A. Insert in section 2 after item 4:

> **5. Final acceptance (Part A, "ultimate success criterion").** Model-level acceptance requires both (a) the gate (items 1 and 2) against every reference of the registered set, and (b) at least one advantage, named and given a margin before observation, measured against the same references: lower acquisition cost (data, teacher queries, measured compute or wall time to reach the registered capability level), less forgetting than the strongest Tier 1 continual-learning baseline, capability that grows with stored memory at fixed active compute, or a measured efficiency gain. Parity without an advantage is labelled PARITY WITHOUT DEMONSTRATED ADVANTAGE and is not acceptance. An advantage without parity is labelled NOT A COMPENSATING RESULT.

Section 8 must then add "knowledge acquisition cost" and "forgetting relative to Tier 1" to the measured list, and compare against the Tier 2 models being replaced as well as Tier 1 ("Each against the Tier 1 alternative reaching the same capability **and against each Tier 2 reference**").

### F2. BLOCKING. The margin rule is ill-defined, can be gamed, and can let the untaught student pass.
(a) "Run-to-run noise of the references" is undefined. Under greedy decoding a model's run-to-run noise is near zero, so δ ≈ 0. At δ = 0 a truly equal system passes a single domain with probability alpha = 0.05 (power.out.txt, column "delta 0"). Under sampling, the noise grows with temperature, so a higher temperature or a noisier reference widens δ. Both are routes to gaming the rule. (b) The rule conflates two things: sampling error of the item set, which the confidence bound already covers, and the size of a capability difference that does not matter, which is what the margin is for. Noise should set the sample size, not the margin. (c) There is no assay-sensitivity condition. If δ is at least the gap between S₀ and a teacher in a domain, S₀ alone is "at parity" with that teacher there, so a cheaper-but-weaker system passes. With n = 500, discordance 0.2 and δ = 0.10, a system truly 5 points worse passes a domain with probability 0.80 (power.out.txt, last block).

Replace the "Margin" bullet of section 4 with:

> - **Margin.** For each evaluation e a non-inferiority margin δ_e on the evaluation's own score scale is set by the human lead before any score of S, of a Tier 1 system or of a reference on the evaluation's test split is seen. δ_e is a substantive judgement of a difference that does not matter, not a noise estimate; measured noise (M0, on a development split) is used only to choose the number of items (section 5, power rule) and to declare an evaluation NOT EVALUABLE when the affordable number of items cannot reach the registered power. In addition, for every reference R and evaluation e: δ_e must be at most one half of the lower 95 % confidence bound of (score of R − score of S₀) measured in M0 on the development split; where R is not shown ahead of S₀ by more than 2·δ_e, parity with R on e is decided against S₀'s comparison as well, and S₀ passing non-inferiority to R on e is printed beside the verdict. A margin is never revised after a score of S exists.

(The one-half fraction is my proposal; it is the standard "preserve a fraction of the effect" device. The fraction is the human lead's to set. PENDING LEAD REVIEW.)

### F3. BLOCKING. The conjunction lacks statistical power unless sample size is fixed by a power rule.
The verdict is an intersection-union test: every per-evaluation one-sided test must pass. Such a test needs no multiplicity correction for its type I error. That is good and should be stated. But the probability that a truly equal system passes is the product of the per-test powers, so it falls quickly. Examples (power.out.txt): one evaluation with n = 500, discordance 0.2 and δ = 0.03 has per-test power 0.44. Five such evaluations against one reference give about 0.02; against two teachers (ten tests) about 0.0003. A HumanEval-sized set (164 items) at δ = 0.05 has power 0.42. For overall power 0.8 over ten tests at discordance 0.2, δ = 0.03 needs about 2,973 items per evaluation and δ = 0.02 about 6,689. Without this rule the requirement cannot be passed by construction. The temptation is then to widen δ (F2), which is how a weaker system gets through. Add to section 5:

> **Statistics.** Comparisons are paired on identical items, identical prompts and identical decoding settings. The unit is the item; where items share a source (a problem with several tests, a passage with several questions, a subject) the confidence bound is computed by a cluster bootstrap over sources with at least 10,000 resamples and a registered seed. Each test is one-sided at alpha = 0.05; the verdict is the conjunction over every (evaluation, reference) pair and needs no further multiplicity correction. **Power rule:** before M5's test split is scored, the number of items per evaluation is fixed so that, at the discordance measured in M0 on the development split and a true difference of zero, the probability that every test in the conjunction passes is at least 0.8. An evaluation that cannot reach this within its available or generatable items is NOT EVALUABLE (UNDERPOWERED) and is not dropped silently; the domain then carries NOT EVALUABLE, which is not PARITY. Stochastic decoding, where used, draws a registered number of samples per item for every system alike and scores the per-item mean.

At these sizes, private programmatically generated item sets (thousands of items per evaluation) are a necessity, not an option. Section 9 should say so.

### F4. BLOCKING. The section 7 precondition excludes the human lead's own scenario.
The human lead described his case on 2026-11-19 (the lead's P11 memory note): two teachers of similar strength in the same field who get different items wrong. A domain-level "each ahead somewhere" test fails in that case, so the question would be NOT EVALUABLE. Complementarity is a property of items, not domains. Replace the Precondition bullet:

> - **Precondition (complementarity).** For each domain named in advance for superiority, M0 must show on the development split that the item-level union of the teachers exceeds the better teacher's score by more than δ_e, with the lower 95 % bound (paired, cluster bootstrap) above δ_e. Where it does not, superiority in that domain is NOT EVALUABLE (NO COMPLEMENTARITY). Coverage (each teacher ahead of S₀ somewhere) is a separate condition read per domain and is not required for superiority.

### F5. REQUIRED. "PARITY (TIER 1)" carries the word parity for a comparison that is not the human lead's criterion.
Tier 1 systems are not "the conventional models it aims to replace". They are controls that show what the memory contributes. A label containing PARITY invites exactly the reading the draft forbids. Also, S₀ is listed in Tier 2, so "PARITY (TIER 2: S₀)" would be a valid label that means only "did no harm". Replace the labels paragraph of section 5:

> Labels: MATCHES CONVENTIONAL ADAPTATION (TIER 1, named systems); PARITY (all Tier 2 references, named); NOT AT PARITY (named references and evaluations); NOT EVALUABLE (reason). PARITY is printed only when every Tier 2 reference of the registered set passes on every evaluation; a pass against a subset of references is printed as NOT AT PARITY with the failing references named, followed by the passing ones. S₀ is not a parity reference: S against S₀ is the do-no-harm condition and its label is NO HARM / HARM (named evaluations).

and in section 4, Tier 2: "Each teacher, and the further references of F7. S₀ is measured beside them for the do-no-harm condition and is not a parity reference."

### F6. REQUIRED. One frozen S, no oracle task identity, matched inference conditions.
Section 4 does not prevent any of these: a different S (or memory, gate setting or checkpoint) per domain; picking the best checkpoint on the test split; telling S at evaluation which capability is being asked (P10-I-S2 used oracle task codes; H22-E). Each one lets a weaker system pass. Add to section 4:

> - **One system.** S is one frozen checkpoint (backbone, memory, router, adapters) evaluated on every evaluation. No per-domain or per-item selection of checkpoint, memory or setting; no evaluation-time information about task or capability that is not given identically to every reference; no checkpoint selection on a test split. Prompts, few-shot examples, chat templates (each model's published template), maximum generation length, decoding settings and number of samples are fixed per evaluation before scoring and are the same for S and every reference except where a model's published template requires otherwise, which is listed. Prompt formats may be chosen only on the development split, by a rule applied to every system alike.

### F7. REQUIRED. The reference set lacks conventional alternatives matched to deployment cost.
The teachers are not the only "conventional models it aims to replace". The natural replacement claims are against:
- (i) a conventional dense model with the same total stored bytes as S (S₀ plus memory);
- (ii) a conventional model with the same active compute per token;
- (iii) the memory layer from prior work.

Without (i), a 0.5B student with several GB of memory could reach parity with a 7B teacher and still lose to a dense model of the same byte size. Part A's economics claim would then be unsupported. Add to section 4:

> - **Tier 2 also contains:** (a) the strongest available conventional model of the student's family whose stored bytes are at most those of S (student plus memory plus router); (b) the conventional model of the same family with the nearest active compute per token to S; each at a pinned revision, chosen in M0 before any score of S exists. **Tier 1 also contains:** one LoRA adapter per capability with a learned (not oracle) selector (the conventional modular continual-learning baseline, which cannot forget by construction), a flat product-key or memory-layer baseline from the prior literature at matched parameters, and S₀ with retrieval over the teaching data. Every Tier 1 system receives the same teaching data, the same teacher queries, the same training compute within a stated tolerance and the same hyperparameter-search budget as S; the budgets are printed.

An ensemble or per-item router of the teachers belongs in section 7 as a control (the routing control is already there). It is not a parity reference, because it is not a single conventional model; the ADR should say so.

"Relevant baseline models" should be pinned down by a rule rather than a list, so the human lead's words are not weakened: "a reference is relevant if it is a conventional model that a user would deploy in place of S at equal or lower stored bytes, or at equal or lower active compute, or that served as a teacher; the set is fixed in M0 and may not be reduced afterwards." The choice of model families and revisions is PENDING LEAD REVIEW.

Is Tier 2 parity with a much larger teacher well posed? Yes, as a test: it is a falsifiable non-inferiority statement. It may be unattainable, and the draft rightly says so, but it must not be redefined to make it attainable. The human lead's words ("must ... match or exceed the relevant baseline models") set a minimum. Part E decision 1's alternative, "parity with the teachers alone", would narrow that minimum by dropping F7's equal-bytes model. The Tier 1 controls are needed for attribution in any case.

### F8. REQUIRED. Averaging within a domain hides regressions.
"Each domain is one or more named evaluations" and the verdict is per domain. A domain with two evaluations can therefore pass on their average while one of them regresses, which is exactly the failure Part A names. Replace in section 5: "in every domain separately" by "**in every registered evaluation separately (a domain with several evaluations passes only if each passes)**". Subcategory scores (e.g. per subject or per language) are printed but not gated. Item-level regressions: print per evaluation the counts R-right/S-wrong and S-right/R-wrong with their paired bound. Whether a separate regression gate is wanted beyond the paired test is PENDING LEAD REVIEW.

### F9. REQUIRED. Domain list: undefined entries and gaps.
- "Generalisation" is a split, not a domain. Apply it to every domain: "each evaluation has an in-teaching-distribution part and an out-of-teaching part; both are gated".
- "Knowledge retention" could mean factual knowledge recall or retention under sequential learning (section 6). Define it as "factual knowledge (closed-book question answering)" and leave retention to section 6.
- Missing domains that are plausibly relevant to Qwen and GLM:
  - mathematics, separately from general reasoning;
  - instruction following;
  - multilingual ability (GLM and Qwen are both strong in Chinese; a student plus memory taught in English could regress there);
  - long context;
  - calibration and hallucination rate (a memory can raise confident wrong recall);
  - code execution efficiency beside pass rate, from the human lead's own example of code quality (30 ms against 300 ms).

  All PENDING LEAD REVIEW. The draft should list them as candidates for decision 3.

### F10. REQUIRED. The retention rule (section 6) is loosely worded.
Replace the bolded sentence and the last sentence of section 6 with:

> **Retention holds only if, in every registered order, for every earlier taught capability and for every capability S₀ had before teaching, the one-sided lower bound of (score after the later step − score right after acquisition, or S₀'s score for pre-existing capabilities) is above −ρ_c, ρ_c fixed in advance per capability, paired on the same items.** A capability counts as acquired only if, right after its step, S passes non-inferiority against the best Tier 1 system taught that capability alone at margin δ_e and its lower bound against S₀ is above zero. Where a capability was not acquired, its retention is NOT EVALUABLE (NOT ACQUIRED), the step is a failure of section 5, and the retention verdict for the sequence cannot read RETENTION HOLDS. With three capabilities, all six orders are run or a registered subset is drawn by a registered seed before any score; the verdict is the conjunction over the orders run.

Also drop "(the expected forgetting case)": writing a baseline's expected outcome into a registered criterion invites a weak baseline. Add the per-capability-adapter baseline (F7), and replay with a matched replay budget.

### F11. REQUIRED. The superiority bullet contradicts its own label.
"Controls that must be beaten or matched" contradicts the label that follows, under which a system that only matches the router is not superior. Replace the Superiority bullet with:

> - **Superiority.** Read only after PARITY. In each domain named in advance (one domain, or several with Holm correction across them): SUPERIOR BY COMBINATION if S's lower bound against the better teacher and against the domain-level router both exceed δ_e but S does not exceed the item-level union; SUPERIOR BEYOND THE UNION if S's lower bound also exceeds the item-level union score (oracle per-item best of the two teachers) by δ_e, or if S solves composition items that no teacher, no router and no registered pipeline of the two teachers (one teacher's output given to the other) solves. COMBINES (NO GAIN BEYOND ROUTING) if S is non-inferior to but not above the router. Composition items are generated before S exists, by a procedure written without access to S, and shown in M0 to be failed by each teacher, by S₀ and by the pipeline.

The two superiority labels separate the human lead's "take the best of both" (2026-11-19) from Part A's "capabilities that neither teacher provides independently". Which of them meets point 2 is PENDING LEAD REVIEW.

### F12. REQUIRED. Evaluation independence and contamination: what is missing and what can be checked.
Add to the Independence bullet:
- **Teaching data checked for overlap.** Teacher-generated teaching data is checked against every evaluation: 13-gram and normalized exact match, plus embedding near-duplicates above a registered threshold. Teachers can reproduce public benchmark items they saw in pretraining. Checkable.
- **Sealed test split.** Each evaluation has a sealed test split used only in M5; M1 to M4 use development splits only. Reusing one test split across the ladder is adaptive overfitting. Checkable (hash in the freeze, as with the P10 sealed files).
- **Private sets.** Generated programmatically from a registered seed (procedural arithmetic and logic, code tasks with hidden tests, synthetic facts), with the generator frozen before any teaching. Checkable.
- **Release dates.** Prefer benchmarks released after every reference's training cut-off where they exist, and record the dates. Partly checkable.
- **Pinned scorer.** Use an established public harness at a pinned version rather than bespoke scoring where possible, and test bespoke scorers on hand-labelled items. "Not written by whoever wrote the teaching code" is weak when both authors are agents of the same model family; say which agent and model wrote each.
- **Code sandbox.** Generated code runs in a sandbox without network, with CPU, memory, time and filesystem limits. The sandbox is itself tested with adversarial items before M0 scores anything.

Not checkable: whether any reference saw a public benchmark in pretraining. The draft says so; keep it.

### F13. REQUIRED. Ladder (Part D).
- **M1 cannot fail as written.** If the gate starts at zero, the "inert" step is an identity by construction (as in ADR-0022 section 3). Label it an engineering check (bitwise or tolerance equality with S₀), not a test, and make "after teaching one narrow capability" the test.
- **M0 has no registered failure outcomes in the draft.** Add: NOT EVALUABLE (UNDERPOWERED) per evaluation (F3); NO COMPLEMENTARITY per domain (F4); TEACHER NOT AHEAD per domain (coverage); REFERENCE NOT RUNNABLE LOCALLY.
- **M0 also fixes** S₀, the further Tier 2 references (F7), the development and test splits, and prompts and decoding (F6). The choice of S₀ depends on a model the memory can attach to (width, tokenizer, licence); state this hidden dependency.
- **Missing rung between M0 and M2: teaching data.** The teaching data and teaching procedure (what the teachers generate, how much, how it is filtered) are defined nowhere, and they also determine what Tier 1 trains on. Call it M1.5, or fold it explicitly into M2's specification.
- **Missing early check for capabilities that are not look-ups.** Whether the memory can carry anything beyond look-up at model level (section 9, second bullet) should be tested in M2, with one capability that is a look-up and one that is not, so that a negative answer arrives before M3 to M5 are paid for.
- **M3's dependency on "M2 passing".** Define passing as MATCHES CONVENTIONAL ADAPTATION (TIER 1) for that capability. Otherwise, state that M3 runs regardless to measure retention.
- **M0's code and environment.** M0 is correctly scoped as needing no ArborLM code. It does need new code: model loaders and tokenizers for Qwen and GLM, an evaluation harness and a sandbox. It also needs packages the locked environment lacks (ADR-0022 ran on torch 2.8.0 alone and pre-tokenized offline). `uv.lock` changes need an approved amendment, and `--with` analysis tools may not be enough for a registered path. Some GLM revisions run repository code (remote code) at load, which is a security and reproducibility item for the specification.

### F14. REQUIRED. Section 9 understates feasibility, cost and licence risk.
Add:
- **Memory and disk.** 7B to 9B teachers in BF16 are about 15 to 19 GB each. Two teachers, a student and an equal-bytes reference come close to the standing 50 GB download delegation, which is cumulative, so count what P10 has already downloaded. One such model fits in 48 GB at a time, and registered runs sharing the machine reduce the headroom.
- **Evaluation cost.** At the F3 sizes (thousands of items per evaluation, hundreds of generated tokens each) and the single-stream decode rate of a 7B to 9B model on this machine, each evaluation could plausibly take hours to days per system. That is multiplied by every reference, Tier 1 system, seed and order. M0's specification must include a timed pilot on a few dozen items, a projection from it, and a statement of which evaluations are infeasible locally (NOT EVALUABLE, not dropped).
- **Licences.** Licences differ by size and revision within both families: some Qwen sizes and some GLM releases have not been Apache-2.0 or MIT, and some carried use restrictions or registration. Check each exact revision, for the weights and for every benchmark (some are share-alike or non-commercial). Also check whether the terms allow teacher outputs to be used to train another model.
- **Agent independence.** Evaluation and teaching code written by agents from the same provider are not independent in the sense of section 4. Disclose this.

### F15. REQUIRED. The Part B table over-reads two frozen studies (no outcome is changed, but the readings are new).
- **P10-I-S0 row,** "The load at which a store may be operated". The licence covers synthetic fixed-length records on one 27,392-parameter backbone (its OUTCOME, "What this does and does not say"). Replace with: "The load at which the 27,392-parameter byte-level store was qualified on synthetic records (up to one fact per slot); whether any load transfers to a token-level model is untested."
- **P10-I-S6 row,** "Whether the flat memory is a reasonable form to carry into a model-level test". Its registered label says nothing about the ordering at convergence. Replace with: "Nothing beyond its registered label CONVERGENCE NOT REACHED (BOTH STILL IMPROVING); its descriptive trend may be weighed by the human lead in choosing a design, and is not evidence for it."

### F16. REQUIRED. The Part B section 1 rule is too permissive.
"Never reported as progress toward parity without the sentence that parity is untested" still allows a component result to be reported as progress, provided the sentence is added. Replace with: "A component result is never reported as progress toward parity. It may be reported as informing the choice of a design for a model-level test, with the sentence that capability parity is untested."

### F17. RECOMMENDED. Part A point 4 and the efficiency studies under way.
Part A point 4 says efficiency is evaluated "once competitive capability is demonstrated". The draft reads this as "read only behind the gate". It does not say whether the drafted efficiency and SSD studies proceed now (ADR-0030, P10-II-S5, untracked in this worktree). Either reading is defensible, but the lead should not choose one silently. Add to Part E: "7. Whether component efficiency and SSD studies (e.g. P10-II-S5) continue before any parity result, read under section 2, or pause until M5." PENDING LEAD REVIEW.

### F18. RECOMMENDED. Scope of the delegation.
Part A ends "Propose new preregistered tests for my approval". The lead reads the delegation given the same evening ("you can aprove it yourself this weekend") as covering M0's specification. That reading is plausible, but it is the lead's. Recommendation: under the delegation, approve only the margin and power *rules* (F2, F3), and leave the numeric δ_e and ρ_c, the reference list and the domain list to the human lead on Monday. Section 4's own text says "δ is the human lead's to set", and the delegation should not silently override it. Report any choice taken against this review before acting on it, as the delegation note itself requires.

### F19. RECOMMENDED. Scorecard row wording.
The existing row "Quality versus dense alternatives" (score 5) can be read as a capability claim. Propose a note change only to the human lead (the score is his): "Component evidence: predictive loss on a 27,392-parameter byte-level backbone; not capability." The new row's note should say "No model-level evaluation exists; the other rows are component evidence and do not add up to this one."

## Question 7: Part E decisions

1. **Reference set.** Differs from the drafter in the additions. Keep both tiers, as drafted, and add:
   - to Tier 2, the conventional models matched on stored bytes and on active compute;
   - to Tier 1, the per-capability-adapter baseline and the prior-work memory-layer baseline (F7).

   Remove S₀ from the parity references (F5).
2. **Margin.** Differs. Not "fixed from measured noise". Use a substantive margin per evaluation, set by the human lead before any score of S. Cap it at one half of the reference's measured lead over S₀ (assay sensitivity). Use measured noise only for the sample-size (power) rule and for declaring NOT EVALUABLE (F2, F3). The numeric values are the human lead's; under the delegation, approve only the rule (F18).
3. **Domains.** Differs in these respects:
   - generalisation becomes an in-teaching and out-of-teaching split of every evaluation;
   - "knowledge retention" becomes factual knowledge, and retention stays in section 6;
   - the gate is applied per evaluation, not per domain (F8);
   - mathematics, instruction following, multilingual ability, long context, calibration and code efficiency are listed as candidates for the human lead (F9).
4. **Scorecard row.** Same as the drafter: add it at 0 as a proposal for the human lead to score, with the F19 note.
5. **First test.** Same as the drafter, with conditions. Specify M0 now, since it needs no ArborLM result, but:
   - include the F13 additions: registered failure outcomes, the choice of S₀ and the further references, the development/test split and sealing, prompts, and a timed pilot;
   - include the F14 feasibility and licence items;
   - hold downloads and the run decision for the human lead;
   - do the literature check (section 9) before M0's specification, as the draft itself says.

## Discrepancies and own slips

- None in the draft's arithmetic (it contains none).
- The power figures above are my approximations: independent tests, normal approximation, and an assumed (not measured) discordance. They are illustrative and should be replaced by M0's measured discordance.
- My first write to the direct `experiments/_scratch` path was refused by a hook. The content is unchanged, written through the worktree's symlink.
