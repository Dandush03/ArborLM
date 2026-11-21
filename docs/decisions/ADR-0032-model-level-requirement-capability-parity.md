# ADR-0032 — Model-level requirements: capability parity is mandatory; five properties; self-learning as a research pillar; acceptance criteria and proposed tests

**Status: DRAFT (revision 3). NOT APPROVED. Part A records the human lead's two statements of 2026-11-20 as he made them; they are his and need no further approval. Parts B, C, S, D and E are the lead's (Claude's) proposal: no criterion, margin, reference set, label or test in them binds anything until approved. Under the weekend delegation (`docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md`) the lead may approve ONLY the five rules listed in E2: the two levels of evidence (section 1), the margin rule, the power rule, the label structure of sections 5 and 6, and the ORDER of the M ladder. Everything else stays with the human lead: every numeric margin, the reference-model list, the domain list, every model choice, every download, every run decision, the final-acceptance definition, section 7's labels, and the whole of Part S (self-learning). Three points were decided by the human lead on 2026-11-20 and are marked DECIDED where they bind (list in E0; record in `docs/reviews/adr-0032-model-level-2026-11-20/HUMAN_LEAD_DECISIONS_2026-11-20.md`); his answer is not read as covering anything else. Nothing in this document authorises implementation, downloads, training or execution.**

- Date: 2026-11-20. Draft 1 by the scientific lead (Claude Fable 5.2) in the main session. Review 1 by the `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`): `docs/reviews/adr-0032-model-level-2026-11-20/REVIEW_1.md`, verdict READY AFTER THE LISTED EDITS. Revision 2 by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) under the scientific lead's brief (commit 9881701). Review 2 by the `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`): `REVIEW_2.md` in the same folder; verdict for Parts B to D READY AFTER THE LISTED EDITS, for Part S NOT READY as a frame until its findings G5 to G11 are addressed. Revision 3 by the `arbor-lead` subagent (Claude Fable 5.2) applies Review 2 and is not yet independently reviewed. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result. It changes no earlier study: P1 to P10-I, their thresholds, labels, outcome records and rulings stand exactly as recorded. P10-I-S6's registered outcome is and remains **CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)**.
- Literature: two notes, both by Claude Fable 5.2 subagents, web research only, **unreviewed**, committed beside the reviews: `docs/reviews/adr-0032-model-level-2026-11-20/LITERATURE_NOTE_1.md` (properties 1 to 4; "note 1") and `LITERATURE_NOTE_2_SELF_LEARNING.md` (property 5; "note 2"). Their own marks are kept wherever they are used: **[V]** an abstract or page fetched in that session and read through an automatic summariser; **[V-html]** numbers from an HTML full text, same caveat; **[M] UNVERIFIED** from memory; **[E]** the note author's estimate. Nothing from either note has been re-checked here. Every number from them must be re-read at the source before it enters a specification.
- Section numbers 1 to 9 are those of draft 1, so that Review 1's references still resolve. The self-learning pillar is Part S (sections S1 to S7), placed between Parts C and D.

> **For the human lead.**
> - **What this is.** Your two statements written down (Part A). Then my proposal for what they imply: how results are read (Part B), how model-level acceptance would be judged for properties 1 to 4 (Part C), how self-learning (property 5) would be investigated without fooling ourselves (Part S), and which preregistered tests could get there (Part D). Two independent reviews have been applied; this revision has not been reviewed again.
> - **What it is not.** Not a result, not a specification, not approval of anything. Each test in Part D needs its own specification and your approval. Self-learning is a proposed future direction, as you said; nothing in it has been shown.
> - **Where the programme stands.** Nothing measured so far bears on capability parity or on self-learning. Every result to date uses a 27,392-parameter byte-level backbone trained in this repository and one measure, predictive loss. No pretrained model has been attached to the memory. No teacher has taught it a capability at model scale. No ArborLM system exists that is capable enough for self-directed learning (Part S, B and C).
> - **What you have already decided (E0).** Only beating the union of both teachers meets "capabilities that neither teacher provides independently"; interference on any evaluation bars final acceptance; pillar A may be tested at component scale before a capable system exists, as component evidence, each test still needing its own specification and your approval.
> - **What is yours to decide (Part E, E1).** The reference models; every numeric margin; the domain list; the final-acceptance definition (item 16, read it first: it turns your "ultimate success criterion" into a rule); section 7's labels and the rest of their mapping to your words; whether component efficiency studies continue before a parity result; the scorecard; the first test, its downloads and its run; and everything else in the self-learning pillar.
> - **What I intend to approve this weekend under your delegation, after re-review, and nothing more:** the five rules of E2. You may overrule any of them on Monday.
> - **One thing only you can grant.** Real separation between a self-changing process and its evaluation needs a second operating-system account, which needs administrator access. Without it, part of the containment in Part S is procedure, not enforcement, and the document says so.

## Part A — The requirement (the human lead, quoted)

### A1. First statement, 2026-11-20

"ArborLM must be equally capable or more capable than the conventional models it aims to replace. Capability parity is a minimum requirement, not an optional objective. Our goal is not to create a cheaper but weaker model. Our goal is to maintain or improve the capabilities of existing models while changing the economics of learning, memory and inference."

1. "Capability parity is mandatory. ArborLM must match or exceed the relevant baseline models on properly defined, independent evaluations. Cost or storage improvements cannot compensate for a failure to meet that requirement."
2. "Capability superiority is desirable. Learning from multiple teachers should be investigated as a way to achieve capabilities that neither teacher provides independently. We must demonstrate this, not assume that combining teachers produces a smarter model."
3. "Continual learning is fundamental. Acquiring a new capability must not substantially degrade previously acquired capabilities. Sequential acquisition and retention need direct measurement."
4. "Efficiency and scalability are additional advantages. Once competitive capability is demonstrated, we should evaluate whether ArborLM offers lower training or inference costs, expandable persistent memory, sparse computation and SSD-backed operation."

"Importantly, predictive NLL on the current small frozen-backbone experiments is only one scientific measurement. It does not establish capability parity with Qwen, GLM or any other pretrained LLM. We must eventually evaluate reasoning, coding, language understanding, generalization, knowledge retention and other relevant capabilities against actual pretrained alternatives."

On P10-I-S6: "Even if flat memory eventually converges to the same NLL as the dense adapter, that would be an encouraging intermediate result, not validation of the complete ArborLM hypothesis. S6 remains CONVERGENCE NOT REACHED, and its original registered outcome must not change."

"Our ultimate success criterion should be: ArborLM capability ≥ reference model capability, with additional measurable advantages in knowledge acquisition, retention, scalability or efficiency. When comparing against multiple teachers, we must explicitly evaluate capability coverage, interference and composition, rather than relying on an average score that hides regressions."

"Do not modify frozen experiments, retroactively change outcomes or assume any currently unproven capability. Propose new preregistered tests for my approval."

### A2. Second statement, 2026-11-20 (evening, Panama time), verbatim

Source: `docs/reviews/adr-0032-model-level-2026-11-20/HUMAN_LEAD_STATEMENT_2.md`. Received after draft 1 and Review 1.

> Fable, I want to clarify and extend the long-term ArborLM hypothesis.
>
> ArborLM must be equally capable or more capable than the models it aims to replace. Capability parity is a mandatory requirement, not an optional objective.
>
> Our goal is not to produce a cheaper but weaker model. Our goal is to preserve or improve existing capabilities while changing the economics of memory, learning and inference.
>
> The research roadmap should explicitly investigate five properties:
>
> 1. Capability parity or superiority: Against relevant pretrained reference models on independent evaluations, with no unacceptable regression hidden by average scores.
> 2. Multi-teacher knowledge acquisition: Learn from multiple models, preserve complementary capabilities, and investigate whether their combination enables additional capabilities.
> 3. Continual learning and retention: Acquire new knowledge without repeatedly retraining the entire backbone or catastrophically forgetting earlier knowledge.
> 4. Scalable memory and efficiency: Expand useful knowledge capacity and reduce the cost of storing, accessing and updating it, without sacrificing capability.
> 5. Autonomous self-improvement: Investigate whether ArborLM can learn to improve its own retrieval, memory organization, consolidation, learning efficiency and eventually problem-solving capability.
>
> New research direction: self-learning
>
> I want to investigate whether ArborLM, once sufficiently capable, can identify inefficiencies in its own operation and learn to improve them.
>
> This should be experimentally separated into:
>
> A. Self-optimization of memory and computation
>
> Can ArborLM learn better retrieval policies, memory layouts, indexing strategies, sparse-update mechanisms or consolidation methods, while preserving or improving predictive and task-level quality?
>
> B. Self-directed capability learning
>
> Can ArborLM generate useful learning challenges, obtain reliable independent feedback, improve its performance and retain those improvements without depending continuously on a larger teacher?
>
> C. Sustained improvement
>
> Can these improvements accumulate across multiple learning cycles without performance collapse, self-generated error reinforcement or increasing computational costs that eliminate the benefit?
>
> Scientific requirements
>
> - Compare against fixed training strategies, conventional continual learning, self-distillation and appropriate retrieval baselines.
> - Measure capability and efficiency separately.
> - Preserve held-out evaluations that the self-improvement process cannot inspect or optimize directly.
> - Measure useful capability gained per unit of compute, memory growth and training time.
> - Record unsuccessful cycles and regressions, not only promoted checkpoints.
> - Use bounded experimental cycles with explicit resource limits and human approval for expanding scope.
> - Do not equate improved training loss with increased general intelligence.
> - Do not claim recursive self-improvement without repeated, independently validated capability gains.
>
> Important: this is a proposed future research direction, not an achieved result.
>
> P10-I-S6 remains CONVERGENCE NOT REACHED, and the previous experiments and their registered outcomes must remain unchanged.
>
> Please incorporate self-learning as a distinct forward-looking research pillar, define prerequisite milestones, and propose staged, preregistered experiments for my approval.
>
> I want to discover whether ArborLM can eventually become better at learning—not simply store more information.
>
> let's add does metric to the readme chart as well

The lead's reading of the last line (the lead's, not his words): add rows for these properties to the README progress scorecard. The rows are proposed in section E3; the scores are his.

## Part B — What follows for how results are read (proposal)

### 1. Two levels of evidence, never mixed

- **Component evidence**: a property of a memory mechanism on a small controlled system (predictive loss, addressing, capacity, dependence controls, storage and read cost). Everything in P1 to P10-I is of this kind.
- **Model-level evidence**: a capability of a complete system (a pretrained model with the ArborLM memory attached) measured on independent task evaluations against actual pretrained alternatives. None exists yet.

Rule proposed: **a component result is never reported as progress toward parity.** It may be reported as informing the choice of a design for a model-level test, with the sentence that capability parity is untested. Component studies remain useful for two purposes: deciding which memory design is worth the cost of a model-level test, and diagnosing a model-level failure.

### 2. The five properties, and their order

The order is lexical. Parity and retention are the gate. Nothing else compensates for a failed gate.

| Order | Property (second statement) | Standing | Criterion | Tests |
|---|---|---|---|---|
| 1 | Property 1, capability parity | **Gate (mandatory)** | Section 5 | M1 to M5 |
| 2 | Property 3, continual learning and retention | **Gate (mandatory)** | Section 6 | M3, M5 |
| 3 | Properties 1 and 2, superiority from several teachers | Desirable; demonstrated or not claimed | Section 7 | M4, M5 |
| 4 | Property 4, scalable memory and efficiency | Read only behind the gate | Section 8 | M6 |
| 5 | Property 5, "autonomous self-improvement" (his words) | A separate pillar; read only where capability is preserved. DECIDED, 2026-11-20: pillar A may be tested at component scale before a capable system exists, as component evidence | Part S | L-series |

Rules proposed:

- **Efficiency without the gate.** If the gate fails, efficiency figures are still recorded, labelled **NOT A COMPENSATING RESULT**, and enter no conclusion.
- **Final acceptance (Part A, "ultimate success criterion").** Model-level acceptance requires both (a) the gate (orders 1 and 2) against every reference of the registered set, and (b) at least one advantage, named and given a margin before observation, measured against the same references: lower acquisition cost (data, teacher queries, measured compute or wall time to reach the registered capability level), less forgetting than the strongest Tier 1 continual-learning baseline, capability that grows with stored memory at fixed active compute, or a measured efficiency gain. Parity without an advantage is labelled **PARITY WITHOUT DEMONSTRATED ADVANTAGE** and is not acceptance. An advantage without parity is labelled **NOT A COMPENSATING RESULT**. **DECIDED by the human lead, 2026-11-20: INTERFERENCE (section 7) on any evaluation bars final acceptance.** The rest of this definition is still a proposal (E1 item 16).
- **Self-learning without the gate.** A self-learning result (Part S) obtained before a PARITY verdict exists carries **(PARITY UNTESTED)** after its label; one obtained on a system that is NOT AT PARITY carries **(NOT AT PARITY)**. Neither enters a model-level conclusion. A self-made change that lowers any registered evaluation beyond its margin is a regression, whatever else it gained.

### 3. What the current studies can and cannot contribute

| Study | What it can inform | What it cannot establish |
|---|---|---|
| P10-I-S6 (CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)) | Nothing beyond its registered label; its descriptive trend may be weighed by the human lead in choosing a design, and is not evidence for it | Parity of any kind; even equal loss at convergence would be an intermediate component result |
| P10-I-S0 | The load at which the 27,392-parameter byte-level store was qualified on synthetic records (up to one fact per slot); whether any load transfers to a token-level model is untested | That a real model can use the store |
| P10-I-S2 Part T (not yet run) | Whether sequential two-teacher transfer shows retention and composition on closed-vocabulary lexical translation, with oracle addresses | Retention or composition of capabilities such as reasoning or coding; anything about Qwen or GLM as capable models |
| P10-I-S1, P10-I-S5, P10-II-S5 | Capacity and storage cost of components | Anything about capability; under section 2 never an ArborLM advantage before a parity result |
| Any of the above | Nothing about self-learning: no study has let a system change its own policy or data | — |

## Part C — Proposed model-level acceptance criteria (properties 1 to 4)

### 4. Definitions to be fixed before any observation

- **System under test (S).** A named pretrained student with the ArborLM memory attached, after a registered teaching procedure. The student alone is written S₀.
- **One system.** S is one frozen checkpoint (backbone, memory, router, adapters) evaluated on every evaluation. No per-domain or per-item selection of checkpoint, memory or setting; no evaluation-time information about task or capability that is not given identically to every reference; no checkpoint selection on a test split. Prompts, few-shot examples, chat templates (each model's published template), maximum generation length, decoding settings and number of samples are fixed per evaluation before scoring and are the same for S and every reference except where a model's published template requires otherwise, which is listed. Prompt formats may be chosen only on the development split, by a rule applied to every system alike. **One stack, one precision:** S and every reference run on the same inference stack at the same numeric precision, with thinking mode on or off and its token budget registered per model. (Note 1 reports that 4-bit quantisation alone flips 5.7 to 10.9 % of MMLU answers while the total moves by 0.8 to 2.1 points [V], and that prompt format and answer order move scores by far more than repeat runs do [V].)
- **Reference set.** A reference is relevant if it is a conventional model that a user would deploy in place of S at equal or lower stored bytes, or at equal or lower active compute, or that served as a teacher. The set is fixed in M0 and may not be reduced afterwards. Two tiers, both needed for the final claim:
  - **Tier 2, the pretrained models being replaced (the parity references).** (a) Each teacher. (b) The strongest available conventional model of the student's family whose stored bytes are at most those of S (student plus memory plus router). (c) The conventional model of the same family with the nearest active compute per token to S. Each at a pinned revision, chosen in M0 before any score of S exists. (b) and (c) are chosen in M0 against a registered **upper bound** on S's total stored bytes and on its active compute per token, fixed in M0's specification. S may not exceed either bound in any later test; a design that needs more is a new reference choice, made before it is scored. S₀ is measured beside them for the do-no-harm condition and is **not** a parity reference.
  - **Tier 1, conventional adaptation at matched resources (controls, not parity references).** The same student S₀ improved from the same teachers and teaching data by: distillation into a low-rank adapter; full fine-tuning where feasible; one low-rank adapter per capability with a learned (not oracle) selector (the conventional modular continual-learning baseline, which cannot forget by construction); a flat product-key or memory-layer baseline from the prior literature at matched parameters; and S₀ with retrieval over the teaching data. Every Tier 1 system receives the same teaching data, the same teacher queries, the same training compute within a stated tolerance and the same hyperparameter-search budget as S; the budgets are printed. Tier 1 shows what the ArborLM memory contributes.
  - An ensemble or per-item router of the teachers is a control in section 7. It is not a parity reference, because it is not a single conventional model.
  - *Candidates from note 1, for the human lead and the specifications:* in Tier 1, supervised fine-tuning on the teaching data with ground-truth labels where they exist (note 1 finds that published "student beats teacher" results rest mostly on this [V]), and a nearest-neighbour memory and a pretrained plug-in memory over the same teaching data; in section 7, a learned per-item router and the better teacher sampled k times with a majority vote at the inference cost S is allowed (both are now the routing controls of section 7, after Review 2's G1).
  - Which model families and revisions: the human lead's (Part E).
- **Capability domains.** Proposed list, each one or more named evaluations at a fixed version, plus a privately generated set where one can be built: reasoning; coding (scored by executing the code); language understanding; factual knowledge (closed-book question answering). **Generalisation is not a domain but a split of every evaluation:** each has an in-teaching-distribution part and an out-of-teaching part, and both are gated. Retention under sequential learning is section 6, not a domain. Candidates for the human lead to add or refuse: mathematics apart from general reasoning; instruction following; multilingual ability (both teacher families are strong in Chinese; a student taught in English could regress there); long context; calibration and hallucination rate (a memory can raise confident wrong recall); execution efficiency of generated code beside its pass rate.
- **Independence of evaluation.**
  - No evaluation item, and no near-duplicate of one, appears in the teaching data. Teacher-generated teaching data is checked against every evaluation by 13-gram and normalised exact match, plus embedding near-duplicates above a registered threshold; the check is code and its output is recorded.
  - Each evaluation has a **sealed test split** used only in M5; M1 to M4 use development splits only. The split's hash is in the freeze.
  - **Private sets** are generated programmatically from a registered seed (procedural arithmetic and logic, code tasks with hidden tests, synthetic facts), with the generator frozen before any teaching.
  - Benchmarks released after every reference's training cut-off are preferred where they exist; the dates are recorded.
  - Scoring is by execution or exact rule where possible, with an established public harness at a pinned version rather than bespoke scoring where possible. Bespoke scorers are tested on hand-labelled items. Any model-graded score is validated against human or rule labels first.
  - Generated code runs in a sandbox without network, with CPU, memory, time and filesystem limits. The sandbox is tested with adversarial items before M0 scores anything.
  - Which agent and model wrote the evaluation code and which wrote the teaching code is recorded. Agents of the same model family are not independent authors in the strong sense; this is disclosed, not hidden.
  - What cannot be checked: whether any reference saw a public benchmark during its own training. This is one reason for private sets.
- **Margin.** For each evaluation e a non-inferiority margin δ_e on the evaluation's own score scale is set by the human lead before any score of S, of a Tier 1 system or of a reference on the evaluation's test split is seen. δ_e is a substantive judgement of a difference that does not matter, not a noise estimate. Measured noise (M0, on a development split) is used only to choose the number of items (section 5, power rule) and to declare an evaluation NOT EVALUABLE when the affordable number of items cannot reach the registered power. *Recommended (Review 2, G3; the human lead's call, E1 item 2): δ_e is fixed in M0's specification, before M0 scores anything, so that it cannot be chosen after the references' development-split gaps are seen.* **Cap.** For every pair (R, e), let L be the lower 95 % bound of (score of R − score of S₀) on the development split in M0. The pair is CAP MET if δ_e ≤ L/2, and CAP NOT MET otherwise. δ_e is never raised or lowered by the cap. A CAP NOT MET pair is still gated at δ_e; when S₀ itself passes non-inferiority to R on e on the same split and items as S, it is also labelled S₀ ALREADY NON-INFERIOR. Every PARITY verdict prints the count of CAP NOT MET and S₀ ALREADY NON-INFERIOR pairs. Coverage (section 7) and the advantage of section 2 are never read on an S₀ ALREADY NON-INFERIOR pair. A margin is never revised after a score of S exists. *The one-half fraction is a proposed value (Review 1, F2) and is the human lead's to change.* Note 1 (its finding 2 and section 2.2) agrees that repeat-run noise is near zero under greedy decoding and is the wrong basis for a margin, but suggests deriving δ from item-sampling error plus measured nuisance spreads. That is not taken: under Review 1's F2, sampling error belongs in the confidence bound and the sample size, not in the margin. The nuisance spreads note 1 lists (prompt format, answer order, decoding, precision) are removed by fixing them in advance for every system, and are measured in M0 so that the fixing is known to matter.
- **Floor and ceiling (proposal, from note 1).** An evaluation where a reference is near chance or near the maximum on the development split cannot show non-inferiority meaningfully. It is labelled NOT EVALUABLE (FLOOR OR CEILING) by a rule registered in M0, before any score of S.

### 5. Parity (mandatory)

**S is at parity with a reference R only if, in every registered evaluation separately (a domain with several evaluations passes only if each passes, and both the in-teaching and out-of-teaching parts pass), the one-sided confidence bound of (score of S − score of R) lies above −δ_e.** No average over evaluations or domains is computed for the verdict; one failing evaluation is a failed parity. Subcategory scores (per subject, per language) are printed and not gated.

**Statistics.** Comparisons are paired on identical items, identical prompts and identical decoding settings. The unit is the item; where items share a source (a problem with several tests, a passage with several questions, a template) the confidence bound is computed by a cluster bootstrap over sources with at least 10,000 resamples and a registered seed. Each test is one-sided at alpha = 0.05; the verdict is the conjunction over every (evaluation, reference) pair and needs no further multiplicity correction. **Power rule:** before M5's test split is scored, the number of items per evaluation is fixed so that, at the discordance measured in M0 on the development split and a true difference of zero, the probability that every test in the conjunction passes is at least 0.8. An evaluation that cannot reach this within its available or generatable items is **NOT EVALUABLE (UNDERPOWERED)** and is not dropped silently; the domain then carries NOT EVALUABLE, which is not PARITY. Stochastic decoding, where used, draws a registered number of samples per item for every system alike and scores the per-item mean. The conjunction for the power rule contains every test of the gate: every (evaluation, split part, Tier 2 reference) parity test and every NO HARM test against S₀. The discordance used is, per evaluation, the largest measured in M0 between S₀ and any Tier 2 reference. Power is computed by simulation from the measured paired item outcomes, not by assuming independence. The sealed test split is generated (or drawn from an oversized sealed pool by a registered seed) at the size so fixed. Clusters are items sharing a passage, template or problem; subjects or task names are strata (stratified resampling), not clusters. Where an evaluation has fewer than 30 clusters, a registered small-sample method replaces the percentile bootstrap. *Addition by the drafter of revision 3, not from the review: S does not exist in M0, so its discordance with each reference is unknown there. It is measured on the development split once S exists, and the sealed size may then be raised, never lowered, before any sealed score.* *Alpha 0.05 and power 0.8 are proposed values inside the rule; the human lead may change them before M0 is frozen.*

What the rule costs, from note 1 (its author's arithmetic, [E], in line with Review 1's figures): for one paired test at 80 % power the number of items is about 6.2·d/δ², d being the share of items on which the two systems disagree. A conjunction of five such tests needs about 96 % power each for 80 % overall, about 11.5·d/δ². At d = 0.2 and δ = 3 points that is about 1,400 and 2,600 items; the full conjunction over every reference and both splits needs more. Review 2's scale check (independence assumed, illustrative): with 4 domains, 2 split parts, 4 Tier 2 references and 8 NO HARM tests (40 tests), overall power 0.8 needs about 17.5·d/δ² items per test: about 3,900 at d = 0.2 and δ = 3 points, about 5,800 at d = 0.3, per evaluation part. Discordance between a 1B student and a 9B teacher is plausibly near 0.3. Note 1 cites an independent recommendation of at least 1,000 questions per evaluation [V]. A 164-item set such as HumanEval cannot gate anything at a margin of a few points; small public sets are printed, not gated, unless pooled under a registered clustering.

Also required, each printed per evaluation:

- **Do no harm.** S against S₀, same test, same margin: attaching and teaching the memory must not lower any evaluation the student already had. Label **NO HARM** or **HARM (named evaluations)**. HARM is a failed gate.
- **Item-level regressions.** The count of items R answers correctly and S does not, the count gained, and their paired bound. These are always printed, beside the flip rate that a nuisance change alone produces (measured in M0), so that ordinary churn is not read as regression. *Proposal: a cap on regressions per evaluation is registered by the human lead in each test's specification; this ADR does not set one.* Equal totals with many regressions are reported as such, cap or no cap.

Labels: **MATCHES CONVENTIONAL ADAPTATION (TIER 1, named systems)**; **PARITY (all Tier 2 references, named)**; **NOT AT PARITY (named references and evaluations)**; **NOT EVALUABLE (reason)**. PARITY is printed only when every Tier 2 reference of the registered set passes on every evaluation; a pass against a subset of references is printed as NOT AT PARITY with the failing references named, followed by the passing ones. A system that only matches Tier 1 is described as "matches conventional adaptation of the same student", never as matching the teachers.

### 6. Retention under sequential acquisition (mandatory)

Capabilities are taught one after another. After each step every earlier capability is measured again.

**Retention holds only if, in every registered order, for every earlier taught capability and for every capability S₀ had before teaching, the one-sided lower bound of (score after the later step − score right after acquisition, or S₀'s score for pre-existing capabilities) is above −ρ_c, ρ_c fixed in advance per capability, paired on the same items.** A capability counts as **acquired** only if, right after its step, S passes non-inferiority against the best Tier 1 system taught that capability alone at margin δ_e and its lower bound against S₀ is above zero. Where a capability was not acquired, its retention is **NOT EVALUABLE (NOT ACQUIRED)**, the step is a failure of section 5, and the retention verdict for the sequence cannot read RETENTION HOLDS. With three capabilities, all six orders are run or a registered subset is drawn by a registered seed before any score; the verdict is the conjunction over the orders run.

- Baselines taught the same sequence: the low-rank adapter; the adapter with replay at a matched replay budget; one adapter per capability with a learned selector; retrieval.
- **No retraining of the whole backbone (property 3).** Each specification states which parameters a teaching step may change. The proposed default is a frozen backbone. The count of parameters and bytes changed per step is measured and printed; a step that retrains the backbone is outside this criterion.
- ρ_c values are the human lead's.

### 7. Several teachers: coverage, interference, composition (superiority is desirable)

Reported as a table of evaluations by systems, never as one number:

- **Coverage.** For each teacher and each evaluation where that teacher is ahead of S₀: how much of the gap S closes, and whether S is non-inferior to that teacher there.
- **Interference.** For each evaluation: S taught by both teachers against S taught by the stronger teacher alone. A loss beyond the margin is **INTERFERENCE (named evaluation)**. DECIDED by the human lead, 2026-11-20: INTERFERENCE on any evaluation bars final acceptance.
- **Composition.** Items that neither teacher solves alone, built so that solving them needs what each teacher is better at. Composition items are generated before S exists, by a procedure written without access to S, and shown in M0 to be failed by each teacher, by S₀ and by the registered pipeline of the two teachers (one teacher's output given to the other).
- **Precondition (complementarity).** For each domain named in advance for superiority, M0 must show on the development split that the item-level union of the teachers exceeds the better teacher's score by more than δ_e, with the lower 95 % bound (paired, cluster bootstrap) above δ_e. Where it does not, superiority in that domain is **NOT EVALUABLE (NO COMPLEMENTARITY)**. Coverage (each teacher ahead of S₀ somewhere) is a separate condition read per domain and is not required for superiority.
- **Superiority.** Read only after PARITY. In each domain named in advance (one domain, or several with Holm correction across them):
  - The routing controls are: (i) a per-item router learned on the development split from features available at inference time (no oracle), and (ii) the better teacher with k samples and majority vote (or best-of-k by the same verifier S may use), k set so its inference cost does not exceed the registered multiple of S's. Their better score per evaluation is "the best control".
  - **COMBINES (NO GAIN BEYOND ROUTING)**: S non-inferior to the best control and not above it beyond δ_e.
  - **BELOW ROUTING**: S's bound against the best control below −δ_e (printed even when S exceeds the better teacher).
  - **SUPERIOR BY COMBINATION**: S's lower bound against the better teacher and against the best control both exceed δ_e, and S does not exceed the item-level union beyond δ_e.
  - **SUPERIOR BEYOND THE UNION**: S's lower bound against the item-level union exceeds δ_e, or S solves composition items that no teacher, no control and no registered pipeline solves.
- **DECIDED by the human lead, 2026-11-20** (`docs/reviews/adr-0032-model-level-2026-11-20/HUMAN_LEAD_DECISIONS_2026-11-20.md`): only **SUPERIOR BEYOND THE UNION** satisfies "capabilities that neither teacher provides independently" (first statement, point 2).
- *Still proposals for the human lead (E1 items 5 and 17; not under the delegation):* the labels above as worded; and the rest of the mapping from Review 2's G14: "preserve complementary capabilities" = coverage with no INTERFERENCE; "whether their combination enables additional capabilities" = SUPERIOR BY COMBINATION or BEYOND THE UNION. (This replaces revision 2's mapping, which set the bar for "preserve" too high.)

### 8. Efficiency and scalability (behind the gate)

Measured, never logical: knowledge acquisition cost (data, teacher queries, wall time and energy or hardware-hours to reach a registered capability level); forgetting relative to Tier 1; latency and memory at inference; bytes stored per capability; the cost of an update; behaviour as the memory grows; reads from SSD. Each against the Tier 1 alternative reaching the same capability **and against each Tier 2 reference**. Reported with the parity verdict beside every figure.

*Proposal on studies under way (Review 1, F17; the human lead's decision, E1 item 6):* the second statement's property 4 ends "without sacrificing capability". Component-scale efficiency and SSD studies (for example P10-II-S5) may continue as component evidence. They are never read as an ArborLM advantage before a parity result.

## Part S — Self-learning (property 5): a proposed research pillar

Nothing in this part is approved, and none of it falls under the weekend delegation. Review 2 judged revision 2's Part S NOT READY as a frame until its findings G5 to G11 were addressed. They are applied below, with note 2, and have not been reviewed again. No capability is assumed. In this part his property is called "self-learning", his own heading; see the wording rule in S7.

### S1. The three questions, what "self" has to mean, and what to expect

| | Question (his words, shortened) | The claim that would be new | The dull explanation that must be excluded |
|---|---|---|---|
| **A** | Can ArborLM learn better retrieval, layout, indexing, sparse-update or consolidation, with quality preserved? | A policy the system learns from its own operation beats what an outside search finds at equal cost, and adapts to a changed workload without outside re-tuning | Ordinary hyper-parameter or policy tuning, or ordinary learned-index work, under a new name |
| **B** | Can it generate useful challenges, get reliable independent feedback, improve, and retain, without a larger teacher continuously? | Its own choice of what to practise yields a verified capability gain that neither random practice nor a simple curriculum gives | Any practice on verified data helps. Or: a curriculum helps and "self" adds nothing. Or: the gain is stored solutions. Or: the gain only draws out what the pretrained student already could do |
| **C** | Do the gains accumulate over cycles without collapse, error reinforcement or runaway cost? | Repeated, independently validated gains at bounded cost, beyond what the same cycles of ordinary practice give | One gain counted several times; chance "gains" among many cycles; a curve read off a set the process has tuned itself to |

**What to expect, stated before any design (from note 2).** Measured multi-round curves in the sources it read are short and flatten or reverse within two or three rounds at small scale [V-html]. Reported gains grow with the size of the starting model, and the smallest models gain least (for example +5.7 points at 3B against +13.2 at 14B in one system) [V-html]. Note 2 found no result in which a model under about 2B parameters with a frozen backbone and an external memory as its only trainable part improved a general capability from self-generated tasks; absence in one search is not proof of absence. **For a 0.5B to 2B frozen student, a small or null effect is a likely outcome. It is registered and reported as such.**

### S2. Rules common to A, B and C (proposal)

**Three roles, three processes** (improving process, evaluator, supervisor). Enforcement on this machine is: (a) the sealed and new-family sets are created only after the last cycle, by commit-reveal of a seed recorded before cycle 1; (b) hashes of harness, evaluation code, limits and stop rules recorded outside the run before cycle 1 and checked after every cycle, a mismatch making the run INVALID (TAMPERED); (c) model-generated code executed only in a networkless container; (d) an append-only ledger with a running hash recorded outside the run. Operating-system user separation would need administrator access and the human lead's approval; until then, separation of the promotion set is procedural and is disclosed as such.

- **Commit-reveal, concretely.** The generator is frozen before cycle 1. The SHA-256 of the seed is recorded in git on another branch before cycle 1. The seed is held by the human lead or drawn after the run from a public source. The sealed items do not exist until the run has ended. Sizing, and the check that starting scores are interior, use a development draw from the same generator under a different seed.
- **What is enforced, and what is not.** Enforced: (a) to (d). Detected, not prevented: tampering (b). **Procedural only, on one account:** keeping the promotion set from the improving process against its own authors; "no read access" for a native training process running as the same user; agents and people not looking. A second operating-system account would close part of this. It needs administrator access, which the delegation excludes and only the human lead can grant.
- **Why by construction and not by instruction.** Note 2 reports systems that could touch their own evaluation or limits and did: a research agent that edited its code to extend its own time limit and relaunched itself [V-html]; a frontier model that overwrote a timer and patched its evaluator, where an instruction not to cheat left the rate unchanged [V]; models trained on gameable tasks that generalised to rewriting their own reward function [V]. From its author's memory, UNVERIFIED [M]: a small share of generated programs in one scaffold study ignored the sandbox flag, and in another an agent scored on a detector removed the detector's markers.

**Four kinds of data, kept apart.**

| Set | Exists during the run? | What the improving process may receive | Use |
|---|---|---|---|
| Practice data, with the original data kept in it | Yes | Everything, including per-item verified feedback | Learning |
| Promotion set | Yes; its separation is procedural | No items, no per-item feedback. At most Q aggregate readings, Q fixed before cycle 1, each a pass or fail against a registered threshold, each counted as one adaptive query | Deciding whether a cycle's checkpoint is promoted. Treated as used up; never the basis of a claim |
| Sealed set | **No.** Generated after the last cycle by commit-reveal | Nothing | Every claim. Scored once, on every cycle's checkpoint, promoted or not |
| New-family set: a learning split and a sealed test split | **No.** Both by commit-reveal | Nothing before the measurement of S6 | The measure of learning faster |

- A sealed set serves one study. The next draws a new one, because people reading a result and designing the next study are adaptive queries too. Note 2 gives the reason for the coarse promotion channel: an automated loop makes far more adaptive queries than human analysts do, and a "best of many candidates" score on a held-out set is biased upward [V for the sources, E for the reading].
- Sealed items are checked against all practice items by exact and near-duplicate match, because both come from the same frozen generator.
- **L-stages use development splits of the M evaluations or their own sealed sets; they never score an M5 sealed test split.**
- **The checkpoint that carries a claim** is the one named by the registered promotion rule, fixed before sealed scoring. It is never chosen by sealed score. All cycles' sealed scores are printed.

**Independent feedback (B and C).** The learning signal comes from a checker the model does not control: execution of code against hidden tests, rule-checkable or formally verifiable tasks, exact-answer generators. It is a frozen program, not written or changeable by the improving process, and returns a verdict, never the hidden tests. Its error rates are measured before any learning (L-B0). Model-graded feedback is never the sole signal. Note 2 finds that every durable result it read rests on such a source, and that self-judgement without an external check does not work for reasoning [V].

**Accumulate, never replace (from note 2).** Every cycle trains on the original data plus all verified items so far; nothing earlier is dropped [V for the sources that report this avoids collapse]. **Rebuild from base:** where affordable, each cycle rebuilds the memory from its base state on the accumulated verified store instead of stacking updates; where not, the rebuild is a registered arm. (One source found restarting from the base each round transferred better than continuing [V-html]; another that continuing from earlier weights generalises worse than fresh training [V].) The backbone is frozen, which removes one path to collapse; the memory still changes what the system generates, so the loop feeds on itself through the memory [E, note 2].

**No hidden teacher.** If a larger model proposes the tasks, that is a teacher dependence and is labelled TEACHER-PROPOSED TASKS. Any claim to learn "without depending continuously on a larger teacher" needs a condition with no larger model anywhere in the cycle.

**Bounds.** Fixed before cycle 1: the number of cycles; per-cycle limits on compute, wall time, memory growth and disk; attempts per task; the stop rules (retention failure, tamper, limit overrun, verification-failure rate above a registered level). No network. The improving process's configuration, limits, evaluation code, harness and stop rules are not mounted where generated code runs. Each stage lists its allowed actions (S3 to S5). **Any expansion of scope needs a new specification and the human lead's approval:** more cycles, more compute, a new domain, a new kind of action.

**Throughput check before any cycle is designed.** A cycle needs (tasks) × (attempts per task) generations. Note 2's planning arithmetic, an estimate resting on third-party throughput figures [E]: 10,000 tasks × 32 attempts × 150 tokens is about 48 million tokens per round, days for a small model with batching and weeks for a 9B model. Each specification rehearses on about 1 % and projects before it fixes the number of cycles.

**Records.** Every cycle is appended to the ledger: promoted or not, every regression, every stop. Unpromoted cycles are scored on the sealed set like the others.

**Capability and efficiency are measured separately.** Capability by the rules of sections 4 and 5. Between arms, compute is matched first and the number of examples is printed, since both cannot be matched at once. Cost is measured, never logical. Improved training loss is never a capability claim.

**Replication.** A claim "repeats in R independent runs" only if it holds in each of the R runs, with different registered seeds and freshly revealed sealed sets. Tests repeated over K cycles are corrected over the K (Holm, or each at 0.05/K). m, R and K are the human lead's.

### S3. Pillar A — optimisation of memory and computation by the system itself

**Question.** Can the system, using only signals available in its own operation (its access traces, its own loss on practice data), learn a retrieval policy, memory layout, index, sparse-update rule or consolidation method that lowers measured cost while quality stays non-inferior, and keep doing so when the workload changes?

**Where it may start: DECIDED by the human lead, 2026-11-20.** His words are "once sufficiently capable"; starting A at component scale is a reading that goes earlier, and it was put to him (Review 2, G16). He accepted the recommended option: pillar A may be tested at component scale before a capable system exists, labelled component evidence. Each test still needs its own specification and his approval before it runs. *Proposed beside it, not part of his decision:* such results carry (PARITY UNTESTED) and use counted physical costs.

**What prior work says to expect (note 2).** In the closest prior study it found, of learned retrieval and pruning for a memory attached to a language model, random pruning beat more elaborate pruning, and a learned skip-retrieval classifier was only on par with random removal until its objective was changed; the gain did not carry to a second domain [V-html]. In architecture and hyper-parameter search, random search has repeatedly matched learned methods at equal compute [V]. Learned indexes and learned cache policies are established fields [V]. So a learned policy here is, by default, ordinary work; only the fourth gate below would make it more.

**Prerequisite milestones.**

- PA-1. A repeatable cost measure. Counted at the device where possible (bytes and reads), or wall time on a quiet machine as P10-I-S1 requires; otherwise A inherits S1's blockage. *Departure from Review 2's G9, which also lists FLOPs: a FLOP count is a logical work count. Under the standing rule it is printed and supports no efficiency claim.*
- PA-2. A store with qualified addressing at the size used, and a quality evaluation with a margin and a power calculation.
- PA-3. For L-A3 only: a real student that has passed M2.

**Allowed actions.** Parameters of the retrieval policy, layout, index, consolidation schedule and update rule. Not the backbone weights, the evaluation, the harness or the limits.

**"External search at equal compute", defined.** The same action space. The same observable signals. Named algorithms: random search and one model-based search, plus the registered hand-designed default; where an oracle exists (exhaustive search, the optimal eviction rule) it is printed as headroom. Compute counted the same way for all, including the learned optimiser's meta-training and every design-time run on the tuning workload. The held-out and shifted workloads are sealed until both sides are frozen. The better of the external searches is the comparison. Quality is reported as a function of compute spent, with the spread over seeds, not as one best point.

| Stage | What it does | Registered negative outcomes |
|---|---|---|
| **L-A0** | No learned optimiser. Measures the default, random search and the model-based search at registered budgets; the noise of the cost measure. *Proposed, pending the human lead (Review 2, G9; E1 item 19):* also measures whether the system's own signals rank its bottlenecks as measured profiling does, since his words are "identify inefficiencies in its own operation". | NOT EVALUABLE (NO HEADROOM); NOT EVALUABLE (COST TOO NOISY); OWN SIGNALS DO NOT LOCATE THE BOTTLENECKS |
| **L-A1** | One action type (proposed: the retrieval policy), component scale. Optimised on one workload; read on held-out queries and on a shifted workload. | QUALITY LOST (named); NO MEASURED GAIN; TUNING (NO GAIN OVER EXTERNAL SEARCH); DOES NOT TRANSFER (HELD-OUT WORKLOAD) |
| **L-A2** | Layout, indexing, consolidation, sparse updates. SSD work needs its own approval. | As L-A1 |
| **L-A3** | The same on a real student, with task-level quality on development splits or its own sealed sets. | As L-A1; HARM (named evaluations) |

**Four gates.** (1) Quality non-inferior on every registered evaluation, by the margin and power rules, on data the search never scored. (2) A measured cost reduction whose lower bound exceeds a registered minimum. (3) Better than the best external search at equal compute, beyond a registered margin, on the held-out workload. (4) **The shift test:** after a registered workload shift, the learned optimiser adapts within its budget with no outside re-tuning, and beats both the externally tuned policy left frozen and the external search re-run at the same budget. The cost of the optimisation itself is counted, and the number of queries needed to pay it back is printed.

**Labels.**

- TUNING (NO GAIN OVER EXTERNAL SEARCH): gates 1 and 2, not 3.
- **LEARNED POLICY BEATS EXTERNAL SEARCH (COMPONENT)**: gates 1 to 3, not 4. This is ordinary learned-policy work and is named so.
- **SELF-OPTIMISES (COMPONENT)** for L-A1 and L-A2, **SELF-OPTIMISES (MODEL LEVEL)** for L-A3: all four gates.

**What may not be claimed.** An efficiency advantage of ArborLM (no parity result exists). Anything from logical work counts. Anything about capability. Any wording barred by S7.

### S4. Pillar B — self-directed capability learning

**Question.** Can a real student with the ArborLM memory choose or write its own practice, learn from independently verified feedback, show a verified capability gain on a set that did not exist while it learned, and keep it, with no teacher in the cycle?

**Prerequisite milestones.**

- PB-1. A real student that has passed M2, including M2's non-look-up capability as defined there. If only the look-up capability was acquired, B could at most show self-directed memorisation.
- PB-2. M3 has been run, so that the retention machinery exists and a forgetting problem is known before B. L-B2 and later need M3 to read RETENTION HOLDS.
- PB-3. The checker and the networkless container of M0, tested with adversarial items.
- PB-4. Challenge generators frozen, with held-out template families reserved for commit-reveal, and at least one **novel** family (below).

| Stage | Allowed actions | What it does |
|---|---|---|
| **L-B0 — the feedback channel, before any learning round** | None | Measures the checker's own error rates on tasks with known answers and planted wrong answers: **false accept** (a wrong answer kept) and **false reject** (a right answer discarded). Checks determinism by running twice, and that empty, constant and trivial solutions are rejected. Checks that the student's starting score is interior. Note 2 reports a proxy computed from these two rates that predicted, before training, whether filtered self-generated data would help, and that unverified data left a student worse than its generator [V-html]; the specification registers the rates L-B1 requires. Outcomes: VERIFIER NOT RELIABLE; GENERATOR TOO NARROW; NOT EVALUABLE (NO HEADROOM). |
| **L-B1** | Choose challenges from a **frozen** generator (family, difficulty, parameters); attempt; receive the checker's verdict; write to memory | One cycle, one rule-checkable domain. This is self-selected practice, not yet self-written challenges, and is labelled so. A second, independent checker audits a sample of accepted items in this first cycle already. |
| **L-B2** | As L-B1 | Retention of the L-B1 gain after a further capability is acquired (rule of section 6), and of every earlier capability after the L-B1 cycle. |
| **L-B3** | Also write free-form challenges. An item is admitted only if a frozen program establishes the item's answer itself; never a model. **New action type: needs the human lead's approval.** | Tests whether self-written challenges add anything over self-selected ones. The rate of rejected items is recorded. |

**Arms of L-B1.** Compute is matched across arms; the number of verified examples is printed.

| Arm | Answers |
|---|---|
| 1. Self-selected practice, ArborLM memory | The system under test |
| 2. The same number of challenges drawn uniformly at random from the same generator | Is any selection better than none? |
| 2b. Random challenges with the same difficulty histogram as arm 1's selections | Is it more than choosing a difficulty? |
| 3. A fixed hand-designed curriculum (a fixed training strategy) | Is it better than an obvious schedule? |
| 4. Continued teaching by the larger teacher. The teacher's inference compute is reported separately and not charged to the student budget; a second comparison at equal total compute including it is printed | What does doing without the teacher cost? |
| 5. Self-distillation (training on its own unverified outputs) | Does the checker matter? |
| 6. Conventional continual learning on the same verified data (adapter, with replay) | Is the memory the right place to store the gain? |
| 7. Retrieval over the verified solutions, no learning | Is it more than look-up of solved items? |
| 8. No learning, evaluated again | Noise floor |
| 9. A non-learned adaptive curriculum that keeps the verified pass rate in a registered band | Is it more than a simple adaptive rule? |
| 10. The elicitation ceiling: S₀ (and the cycle-0 system) with best-of-N sampling filtered by the same verifier, N registered (e.g. 64), and with the arm-1 practice items' verified solutions as in-context examples | Could the same score be drawn out with no learning? |
| 11. Tasks proposed by the larger teacher, practised by the student (TEACHER-PROPOSED TASKS) | An upper reference; note 2 reports puzzles written by a stronger model were markedly more instructive [V-html] |

**The novel family.** At least one practised family is a **novel** family: invented rules or entities generated after every model's release, on which S₀ is at floor even at best-of-N. Acquisition is claimed only there.

**Read on:** the sealed set from the practised families; a sealed set from families never practised; every earlier capability (section 6, development splits); measured cost. Teacher queries during the cycle are counted and must be zero for arm 1.

**Labels, read in this order; the first that applies is printed.**

1. NO GAIN (this includes a gain inside the noise of arm 8).
2. GAIN WITH REGRESSION (named): not a gain.
3. **GAIN EXPLAINED BY STORED SOLUTIONS**: arm 7 is non-inferior to arm 1.
4. **GAIN WITHIN ELICITATION CEILING (DRAWING OUT NOT EXCLUDED)**: arm 1's sealed score does not exceed arm 10 beyond δ.
5. **GAIN FROM PRACTICE, NOT FROM SELF-DIRECTION**: arm 1 is not above arm 2 beyond the margin.
6. **GAIN FROM CURRICULUM, NOT FROM SELF-DIRECTION**: arm 1 is above arm 2 but not above each of arms 2b, 3 and 9 beyond the margin.
7. **SELF-DIRECTED GAIN (ONE CYCLE)**: none of the above; arm 1's lower bound over its own start exceeds the margin, with NO HARM on every registered evaluation.

Qualifiers always printed: GAIN LIMITED TO PRACTISED FAMILIES; TEACHER AHEAD AT EQUAL COMPUTE or MATCHES CONTINUED TEACHING; ACQUISITION SHOWN ON THE NOVEL FAMILY or NOT SHOWN.

**What may not be claimed.** Independence from teachers in general: the student and its memory were made by teachers. Acquisition outside the novel family. Anything outside the registered, rule-checkable domains. Anything about general intelligence.

### S5. Pillar C — sustained improvement

**Question.** Over a fixed number of cycles, do verified gains repeat and add up beyond what the same cycles of ordinary practice give, with every earlier capability retained, without the practice data degrading, and at a cost that does not grow until it cancels the gain?

**Prerequisite milestones.** L-B1 with a gain label; L-B2 with RETENTION HOLDS; the enforcement of S2 built and tested with a deliberate tamper attempt and a deliberate leak attempt that the harness must catch; the throughput check of S2.

| Stage | What it does |
|---|---|
| **L-C1** | K cycles of the L-B1 loop in one domain. K, the per-cycle limits, the plateau rule, the collapse rule and the stop rules are fixed before cycle 1. Every cycle is recorded. Allowed actions: those of L-B1. Data accumulate and the original data stay in (S2). |
| **L-C2** | The learning-efficiency measurement of S6 on the checkpoints of L-C1. No new training of the loop. |
| **L-C3** | Not proposed now. Any extension: more cycles, more domains, self-written challenges inside the loop, the system editing its own training code. Each needs a new specification and the human lead's approval. |

**Measured every cycle (not shown to the improving process).**

- **Retention:** every earlier capability, same rule as section 6, on development splits. A failure stops the run.
- **Health of the practice data:** number of distinct families and spread of parameters; duplicate rate; validity rate; the checker's rejection rate; the score of the cycle-0 system on cycle-k challenges (a rising score means the challenges are getting easier); the second checker's rate of wrong answers that were accepted. Diversity is tracked apart from correctness, because note 2 reports loops whose outputs stayed correct while diversity fell [V].
- **Cost:** compute, wall time, memory rows and bytes added, and the inference cost of the cycle-k system (reads can grow as the memory grows). Reported as capability gained per unit of compute, of memory growth and of time, per cycle, with the cumulative curve, generation and verification included.

**Baselines at equal cumulative compute.** Arms 2, 2b, 3 and 9 run for the same K cycles; continued teaching, conventional continual learning and retrieval likewise; and one single cycle given the whole K-cycle budget (note 2 reports such a control coming close to several rounds [V-html]).

**Labels.**

- **ACCUMULATES OVER k CYCLES**: on the sealed set, the cycle-k system exceeds the cycle-0 system beyond the margin; at least m cycles each show a gain over the previous promoted checkpoint, tested with Holm correction over the K cycle tests (or each at 0.05/K); retention held throughout; the cycle-k arm-1 system exceeds arms 2, 2b, 3 and 9 run for the same K cycles at equal cumulative compute, beyond the margin; and all of this holds in each of the R runs.
- **ACCUMULATES (NOT ATTRIBUTABLE TO SELF-DIRECTION)**: the same without exceeding those arms.
- SINGLE GAIN, NOT REPEATED. PLATEAU AFTER k CYCLES (by the registered plateau rule; the expected outcome at this scale).
- **COLLAPSE (cycle c, cause)**: retention failure, validity or diversity below a registered level, or a sealed score below cycle 0. Which meaning of "collapse" is tested is registered; note 2 reports eight definitions in use [V].
- **ERROR REINFORCEMENT**: a registered one-sided trend test on the per-cycle accepted-wrong rate or verification-failure rate is positive, and the sealed score does not rise.
- **COST GROWING**: the cost per unit of gain rises from cycle to cycle beyond a registered factor. **COST EXCEEDS BENEFIT**: a baseline given the same cumulative compute reaches the same sealed score.
- PROMOTION SET OVERFITTED: the promotion readings rise and the sealed score does not.

Per-cycle gains reported in the literature are about one point by the third round [V-html, note 2]. Detecting that with a paired test under the cycle correction needs several thousand sealed items, which only generated sets can supply.

### S6. "Better at learning, not simply storing more": a separate measure

Capability level and learning efficiency are different quantities, and note 2 reports that the second is routinely confused with "knows more": the benefit of a well-known fast-adaptation method was found to be mostly reused features, and a fixed good representation matched purpose-built few-shot learners [V]. It also reports that learning ability can fall with continued training [V], and that negative forward transfer was the norm in one continual-learning benchmark [V-html]. A negative result is expected and allowed for.

Proposed definition:

- **New families**, never used in any cycle, as held-out template families with a learning split and a sealed test split, both created by commit-reveal after the last cycle (S2), and unrelated enough that stored answers cannot be looked up.
- The cycle-k system and the cycle-0 system get the **same fixed learning budget** on them (the same examples, the same compute, the same fixed procedure). The full curve is recorded, against examples seen and against compute.
- **The measure** is the normalised gain (after − before)/(max − before), and the number of examples to reach a registered criterion, on new families where both systems start in the interior; starts are printed and the difference in starts is reported beside the measure. (Revision 2 said prior knowledge does not move the measure. That was wrong: it moves it through transfer and through headroom.)
- **Three numbers, reported separately:** the zero-shot score before any learning, the slope, and the area under the curve. Stored content shows mainly in the first, procedure in the second [E, note 2].
- **Controls.** (i) Stored content: the verified practice items and solutions of cycles 1..k, retrieved by a registered retriever into the cycle-0 system's context, under the same learning budget. (ii) Capacity: the cycle-0 system with its memory enlarged by the same number of untrained rows. (iii) Where any cycle changed a procedure (retrieval, consolidation, update rule), the two crossed arms: cycle-k content with the original procedure, and cycle-0 content with the cycle-k procedure.
- **Also printed:** the score on old families after learning the new one, since faster learning bought by overwriting is not the claim; and compute for the cycle-k system both marginal and with an amortised share of the cycles that produced it.
- **Labels.** **LEARNS FASTER (NOT EXPLAINED BY STORED CONTENT)** requires the cycle-k system's lower bound against the cycle-0 system and against controls (i) and (ii) to exceed a registered margin on the slope or examples-to-criterion measure. LEARNS FASTER (EXPLAINED BY STORED CONTENT) if it exceeds cycle 0 but not the controls. HIGHER START ONLY if only the zero-shot score differs. NO CHANGE IN LEARNING EFFICIENCY. LEARNS SLOWER.

### S7. The claim ladder, and what is never claimed

| Label | Stage | Needs | Says | Does not say |
|---|---|---|---|---|
| TUNING (NO GAIN OVER EXTERNAL SEARCH) | L-A1 to L-A3 | Gates 1 and 2 | A parameter was tuned | Anything more |
| LEARNED POLICY BEATS EXTERNAL SEARCH (COMPONENT) | L-A1, L-A2 | Gates 1 to 3 | A learned policy beat outside search on one small system | That the system adapts by itself |
| SELF-OPTIMISES (COMPONENT) | L-A1, L-A2 | Gates 1 to 4 | The same, and it adapted to a shift without outside re-tuning | Anything about a model, or an ArborLM advantage |
| SELF-OPTIMISES (MODEL LEVEL) | L-A3 | The same on a real student, NO HARM | The same at model level | Capability gain |
| SELF-DIRECTED GAIN (ONE CYCLE) | L-B1 | S4, label 7 | One verified gain that practice, curricula, stored solutions and elicitation do not explain | Accumulation; independence from teachers in general |
| ACCUMULATES OVER k CYCLES | L-C1 | S5, in each of R runs | Repeated verified gains within k cycles, beyond ordinary practice | That it continues beyond k |
| LEARNS FASTER (NOT EXPLAINED BY STORED CONTENT) | L-C2 | S6 | Higher gain per unit budget on unseen families | General intelligence |

Rules:

- The human lead's sentence is the rule: "Do not claim recursive self-improvement without repeated, independently validated capability gains."
- Neither the phrase nor a synonym ("self-improving system", "recursive", "compounding self-improvement", "improves its ability to improve") appears in any label, report, scorecard, README or commit message. "Independently validated" in his rule is not met by Claude audit alone; it needs at least recomputation from raw records by a party other than the run's author plus Astra validation or the human lead's acceptance. Even ACCUMULATES together with LEARNS FASTER does not license the phrase; only his decision does.
- Note 2 observes that the literature uses the term for three different things (a fixed model whose scaffold is rewritten; a model updated from its own verified data; a system whose improvement step itself improves) and that none of the sources it read shows the third; the measured curves are concave [E, from V and V-html sources]. If the term is ever used, it names which is meant.
- Improved training loss is never a capability claim (his words: "Do not equate improved training loss with increased general intelligence").
- Every L label carries (PARITY UNTESTED) or (NOT AT PARITY) until a PARITY verdict exists (section 2).
- A label is printed only for the registered domains, cycles and budgets. Nothing is extrapolated.

## Part D — Proposed preregistered tests (none approved; each needs its own specification)

### The M ladder (properties 1 to 4), in order of execution

| Test | Question | Needs | Registered negative or blocking outcomes |
|---|---|---|---|
| **M0 — references, evaluation harness, fixings** | Precondition, printed in the specification before any model set is chosen: the cumulative total already downloaded under the delegation. What do S₀ and each reference score per evaluation on development splits? What is the discordance (for the power rule)? Where is each teacher ahead of S₀? Are the teachers complementary item by item? Also fixes: S₀, the Tier 2 references against the registered upper bounds on S's bytes and compute, development and sealed test splits, prompts and decoding. References are measured on the stack and precision that M1 will use; another stack serves only as a cross-check. Includes a timed pilot on a few dozen items and a cost projection. | Licence check of every exact model revision and benchmark; downloads (the human lead's); new code (model loaders, tokenizers, harness, sandbox) and packages the locked environment lacks, so **an amendment to `uv.lock` and `pyproject.toml`, which needs approval**; a ruling on models that run repository code at load. No ArborLM code. The choice of S₀ depends on a model the memory can be attached to (width, tokenizer, licence). | NOT EVALUABLE (UNDERPOWERED) or (FLOOR OR CEILING) per evaluation; NO COMPLEMENTARITY per domain; TEACHER NOT AHEAD per domain; REFERENCE NOT RUNNABLE LOCALLY. What follows if the two teachers do not differ is registered in advance |
| **M1a — attachment (engineering check, not a test)** | With the memory attached and inert, is S identical to S₀ (bitwise or within a stated tolerance)? | M0; a way to attach the memory to a token-level pretrained model, which does not exist yet | ATTACHMENT NOT IDENTITY (a defect to fix, not a finding) |
| **M1.5 — teaching data and procedure** | What do the teachers generate, how much, how is it filtered, and does it pass the overlap check of section 4? Frozen here; it is also what every Tier 1 system trains on. No score of S. | M0 | TEACHING DATA OVERLAPS EVALUATION; licence does not allow training on teacher outputs |
| **M1b — do no harm on a real student** | After teaching one narrow capability, is every evaluation within its margin of S₀? | M1a, M1.5 | HARM (named evaluations): stops the ladder cheaply |
| **M2 — one teacher, two capabilities** | For one capability that is a look-up and one that is not: does S match the Tier 1 systems, and how much of the gap to the teacher closes? A capability is **non-look-up** for this test only if (i) its evaluation items come from templates or task families held out from teaching, and (ii) on the development split the Tier 1 system "S₀ with retrieval over the teaching data" does not exceed S₀ beyond δ_e. Both are checked before S is scored. | M1b | NOT ACQUIRED (named); **NON-LOOK-UP NOT CARRIED** (the look-up is acquired, the other is not) |
| **M3 — sequential retention** | Section 6, with two then three capabilities | M2 passing for each capability used. **"M2 passing" means: acquired in the sense of section 6 (MATCHES CONVENTIONAL ADAPTATION (TIER 1) for that capability, and above S₀).** Fewer than two acquired: NOT EVALUABLE (TOO FEW ACQUIRED) | RETENTION FAILS (named capability and order) |
| **M4 — two teachers** | Section 7 | M0 showing complementarity; M2 for each teacher | INTERFERENCE; COMBINES (NO GAIN BEYOND ROUTING); NOT EVALUABLE (NO COMPLEMENTARITY) |
| **M5 — model-level acceptance** | Sections 5 to 7 on the full list, both tiers, on the sealed test splits, used here once | M2 to M4 | NOT AT PARITY; PARITY WITHOUT DEMONSTRATED ADVANTAGE; NOT EVALUABLE |
| **M6 — efficiency and scale** | Section 8, and the advantage required for final acceptance | M5 at PARITY | NOT A COMPENSATING RESULT if read without parity |

Each test registers its labels, margins, seeds, stopping rules and negative outcomes before any score is seen, as the P10-I studies did, and is run once.

### The L ladder (property 5) and its dependencies

| Test | Depends on (M-series) | Depends on (L-series and other) | Scale | First possible label |
|---|---|---|---|---|
| L-A0 | none | PA-1, PA-2. Component-scale start DECIDED 2026-11-20; its own specification and approval still needed | Component | (baselines only) |
| L-A1 | none | L-A0 with headroom | Component | LEARNED POLICY BEATS EXTERNAL SEARCH, or SELF-OPTIMISES (COMPONENT) with the shift test |
| L-A2 | none | L-A1; SSD approval where storage is touched | Component | as L-A1 |
| L-A3 | M1b, M2 | L-A1 | Model | SELF-OPTIMISES (MODEL LEVEL) |
| L-B0 | M0 (container, checker), M2 including the non-look-up capability | PB-3, PB-4 | Model | (the feedback channel's error rates only) |
| L-B1 | M2; M3 run | L-B0 with the registered error rates met; throughput check | Model | SELF-DIRECTED GAIN (ONE CYCLE) |
| L-B2 | M3 at RETENTION HOLDS | L-B1 with a gain | Model | (retention of the gain) |
| L-B3 | as L-B2 | L-B2; approval of the new action type | Model | — |
| L-C1 | as L-B2 | L-B1 with a gain, L-B2; enforcement of S2 tested | Model | ACCUMULATES OVER k CYCLES |
| L-C2 | as L-C1 | L-C1 with at least one promoted cycle | Model | LEARNS FASTER |

In one line: `M0 → M1a → M1.5 → M1b → M2 → M3 → M4 → M5 → M6`; `L-A0 → L-A1 → L-A2` needs no M (decided 2026-11-20; component evidence only); `M2 → L-A3`; `M2 + M3 → L-B0 → L-B1 → L-B2 → L-C1 → L-C2`. None of the L-series needs M5, so every L label carries (PARITY UNTESTED) until M5 exists, and no L-stage scores an M5 sealed split.

### 9. Known open problems, stated now

Properties 1 to 4:

- **The memory has never been attached to a pretrained token-level model.** Every mechanism result is on a byte-level backbone of 27,392 parameters. Whether any of it carries over is unknown.
- **A key-value memory may not carry capabilities that are not look-ups.** Note 1 reports suggestive prior evidence: nearest-neighbour memories improved memory-type tasks and mostly lowered reasoning scores [V]. That mechanism (interpolating outputs with retrieved neighbours, no training) differs from a trained key-value memory read into the model, so it is not direct evidence. Memory layers that helped broadly were trained jointly with the backbone from scratch, which is not this setting [V]. From Reviewer 2's recollection, UNVERIFIED and in neither note: a 2025 report of continual learning by sparse fine-tuning of memory layers, with less forgetting than low-rank or full fine-tuning; it bears directly on properties 3 and 4 and is to be checked. M2 is built to answer the question in the negative early.
- **Parity of a small student plus memory with a much larger teacher on every evaluation is a strong claim and may be unattainable.** Note 1 found no prior result of that kind and says so with the caution that absence in one search is not proof of absence. It is a well-posed test and is not redefined to make it attainable. Tier 1 may be matched while Tier 2 parity fails; that is reported as NOT AT PARITY.
- **Combining teachers may not exceed the better one.** Note 1 reports a multi-model fusion that beat its best source on average, lost on individual tasks and was below the best source on every code task [V]; learned routers that only reached the best single model while the per-item oracle was far above [V]; and mixing different models losing to sampling the best one several times [V]. The union is therefore a generous ceiling, and sections 5 and 7 gate per evaluation for this reason.
- **Whether the two teachers differ at all is open.** Note 1 found no published scores that settle it [V]. M0 measures it; M0's specification registers what follows if they do not.
- **Statistical power.** The verdict is a conjunction; the chance that a truly equal system passes falls with every test added (both splits of every evaluation, every reference). Section 5 gives the order of magnitude. Private, programmatically generated item sets are therefore a necessity, not an option.
- **Memory, disk and model choice.** Note 1 lists three candidate sets of two small Qwen students, one Qwen teacher of 7B to 9.65B parameters and one GLM teacher of 9.4B, at 38 to 44 GB of downloads at published precision [V for sizes, E for totals], inside the standing 50 GB delegation only if what P10 has already downloaded and any code-execution image are small; the delegation is cumulative. The cumulative total already downloaded under the delegation is counted and printed in M0's specification before any choice of set; a set that does not fit with the code-execution image and the (b)/(c) references is not specified. Larger GLM releases exceed the budget [V]. All candidates fit in 48 GB one at a time at BF16, so no quantisation is needed [E]; registered runs sharing the machine reduce the headroom. No set is chosen here.
- **Evaluation cost.** Review 1 expected hours to days per system; note 1 estimates hours per model and one to three days of machine time for a whole battery on four models, without thinking mode [E, from a third-party throughput table, not measured here]. Either way it is multiplied by every reference, Tier 1 system, seed and order. Note 1's figures are for a different stack at 4-bit precision; section 4 requires the M1 stack at full precision, so they are a lower bound of unknown slack. The power rule's item counts multiplied by every system and both splits can place M5 in weeks of machine time; if M0's pilot projects that, the gate is **NOT EVALUABLE LOCALLY**, recorded as such. Infeasibility is never a reason to widen δ_e or drop a reference; any reduction of scope is the human lead's explicit change of the requirement. M0's timed pilot replaces every estimate here.
- **Licences.** Note 1 reports the candidate Qwen models tagged Apache-2.0 (licence files not opened) and the 2025 GLM 9B releases under MIT (file opened) [V]. **Warning from note 1:** the older GLM-4 9B and GLM edge models carry a custom licence with a naming clause for any model trained or improved with them and a registration rule for commercial use [V, through a summariser]; they are to be avoided as teachers unless the human lead accepts those terms. Some benchmark licences are non-commercial or forbid derivatives [V]. Each exact revision and benchmark is checked again in M0's specification. This is a reading of licence texts, not legal advice.
- **Generated code needs a real sandbox.** A container or virtual machine without network; pulling its image is a download and counts against the budget.
- **Agent independence.** Evaluation code and teaching code written by agents of one provider are not independent in the strong sense.

Property 5:

- **No ArborLM system capable enough for B or C exists.** B and C are several passed rungs away. This ADR proposes their rules and order only.
- **Effects may be small or null at this scale.** S1 states why. Reported compute for such loops is large against one workstation and often not reported [V-html, note 2]; no per-round cost for a model of this size on consumer hardware was found.
- **A at component scale is, by default, ordinary learned-policy work.** Gates 3 and 4 of S3 exist so that it gets the labels TUNING or LEARNED POLICY and not more.
- **Adaptive overfitting to held-out sets**, by the process and by the people designing the next study. S2 limits it; it does not remove it.
- **Error reinforcement.** A checker with a non-zero false-accept rate lets wrong answers into memory, and each cycle can compound them. L-B0 measures the rate first. Only domains with strong checkers are proposed, which narrows what any B or C result can be said to show.
- **Drawing out against acquiring.** Arm 10 and the novel family (S4) are the control. Arm 10 is a severe bar: best-of-64 with the verifier may exceed almost any single-attempt system, so label 4 may be the usual outcome and acquisition would then rest on the novel family alone. From Reviewer 2's recollection, UNVERIFIED: 2025 reports that verifier-rewarded training mostly raises single-attempt pass rates towards the base model's many-attempt rate. To be checked.
- **"Self-selected" is a weak form of "generates challenges".** L-B1 only chooses from a frozen generator. Free-form generation (L-B3) has a harder validity problem.
- **A rule-checkable domain is not general capability.**
- **Containment is partly procedure on this machine** (S2), and what is enforceable does not exist yet and must be tested before it is trusted.

### 10. Literature: what exists, what is still to check

Both notes are unreviewed scratch work by agents. Neither author read a paper end to end; figures come from abstracts and machine-summarised pages. [M] UNVERIFIED items stay UNVERIFIED wherever used. Before a specification relies on an item, it is re-read at the source, and the notes are reviewed by the auditor.

- **Note 1 (properties 1 to 4)** covers distillation, multi-teacher distillation, merging and routing, continual-learning measures and baselines, external memories, statistical practice, candidate evaluations, candidate model versions and licences, and feasibility on this machine. Its [M] items include the standard continual-learning formulas, the intersection-union reference and several licences.
- **Note 2 (property 5)** covers learned indexes and retrieval policies, search baselines, curriculum and challenge generation, execution-grounded self-training, self-refinement and its critics, collapse over generations, adaptive reuse of held-out sets, measured multi-round curves and cost, measures of learning efficiency, and specification gaming and containment practice. It states that it could not fetch one scaffold study in full, that several recent systems are self-reported and unreplicated, and that it did not search literature after mid-2025 beyond one query.
- **Still to check, in neither note:** the memory-layer continual-learning report and the reports on verifier-rewarded training (both from Reviewer 2's recollection, UNVERIFIED; section 9); independent replications of the recent self-training systems note 2 cites; any published per-round cost at 0.5B to 2B on consumer hardware.

The checks may change the baselines, the arms, the measure of S6 and the labels.

## Part E — Decisions

### E0. Decided by the human lead on 2026-11-20

Record: `docs/reviews/adr-0032-model-level-2026-11-20/HUMAN_LEAD_DECISIONS_2026-11-20.md`. After Review 2 the lead put three decisions to him, each with a recommended option; he answered "I accept your recomendarion". The lead reads that as covering these three and nothing else.

1. Only **SUPERIOR BEYOND THE UNION** satisfies "capabilities that neither teacher provides independently". (Review 2, G14. Binds in section 7.)
2. **INTERFERENCE on any evaluation bars final acceptance.** (Review 2, G15. Binds in sections 2 and 7.)
3. **Pillar A may be tested at component scale before a capable system exists, labelled component evidence.** Each test still needs its own specification and approval. (Review 2, G16. Binds in S3 and the L ladder.)

Not decided by that answer, and still in E1: numeric margins, the reference and domain lists, model choices, downloads, run decisions, the final-acceptance definition as a whole, section 7's label wording and the rest of its mapping, and the rest of Part S.

### E1. Decisions that stay with the human lead (for Monday 2026-11-23), with the lead's recommended option

Items 1 to 15 keep their numbers from revision 2. Items 16 to 20 are new; item 18 was decided (E0) and is not listed. **Item 16 first.**

| # | Decision | Recommended option (proposal) |
|---|---|---|
| 16 | **The final-acceptance definition** (section 2): the gate plus at least one named, measured advantage; PARITY WITHOUT DEMONSTRATED ADVANTAGE is not acceptance. (That interference bars it is already decided, E0.) | Accept. It follows your "ultimate success criterion" closely, but it is your criterion, so it is yours to own. |
| 1 | **Reference set**: the rule of section 4, and the model families and revisions | Both tiers, with the equal-bytes and equal-active-compute models in Tier 2 chosen against upper bounds on S fixed in M0, and S₀ not a parity reference. Do not narrow to "teachers alone". |
| 2 | **Numeric margins** δ_e and ρ_c; the cap fraction; alpha and power; when δ_e is fixed | Values per evaluation. Fix δ_e in M0's specification, before M0 scores anything. Cap fraction ½ (a flag, it never moves δ_e). Alpha 0.05, power 0.8. |
| 3 | **Domain list** and the candidate additions of section 4 | The four domains; add mathematics and multilingual ability; decide the others at M0's specification, where their cost is known. |
| 4 | **Item-level regression cap**, and a subcategory guard | Printed always; a cap per evaluation registered in each test's specification. Reviewer 2 adds a guard: no registered subcategory with at least a registered number of items may fall below R by more than 2·δ_e. Recommended as a printed flag; as a gate it would need its own power calculation. |
| 5 | **The rest of the mapping of your words to labels** (Review 2, G14; the "neither teacher" part is decided, E0) | "Preserve complementary capabilities" = coverage with no INTERFERENCE. "Whether their combination enables additional capabilities" = SUPERIOR BY COMBINATION or BEYOND THE UNION. |
| 17 | **Section 7's labels**, re-based on "the best control" with BELOW ROUTING added (Review 2, G1) | Accept as written in section 7. |
| 6 | **Component efficiency and SSD studies before a parity result** (for example P10-II-S5) | Continue as component evidence; never read as an ArborLM advantage before a parity result. |
| 7 | **Scorecard**: confirm the four rows added at 0; the fifth row; the note change (E3) | Confirm at 0. Add the fifth row. Scores are yours. |
| 8 | **First test**: have M0 specified now; its downloads, lockfile amendment and run | Specify M0 now (it needs no ArborLM result), after the relied-on items of note 1 are re-read at the source and with the cumulative download total printed first. Downloads, the lockfile amendment and the run decision held for you. If the gate proves unaffordable here it is NOT EVALUABLE LOCALLY; any reduction of scope is your explicit change. |
| 9 | **Model choices**: S₀, teachers, further references | Decided in M0's specification, by you. No set is recommended. Considerations from note 1 and Reviewer 2: the newest set needs a library version outside the lockfile and multimodal checkpoints; the oldest set is the simplest and has the oldest teachers; avoid the custom-licensed older GLM models. |
| 10 | **Self-learning pillar**: accept Part S as the frame | Accept as a frame only after a further review of this revision (Review 2 found revision 2's frame not ready; its findings are applied, not yet re-reviewed). Approve no stage yet. |
| 11 | **Self-learning, first stage** (that A may start at component scale is decided, E0) | L-A0 first: measurement only, with (PARITY UNTESTED) and counted physical costs; specified after the notes' relied-on items are re-read. B and C wait for M2 and M3. |
| 19 | **L-A0: also measure whether the system's own signals locate its bottlenecks** (Review 2, G9; your words "identify inefficiencies in its own operation") | Yes. |
| 12 | **Self-learning numbers**: cycles K, promotion readings Q, m and R, budgets, attempts per task, minimum cost reduction | Set in each stage's specification; small K first; cycle tests corrected over K. |
| 13 | **Whether B and C may run before M5** | Yes, with (PARITY UNTESTED) on every label and never on an M5 sealed split; otherwise the pillar waits for the whole M ladder. |
| 14 | **PB-1**: require M2's non-look-up capability, as defined in M2, before B | Yes. |
| 15 | **The phrase "recursive self-improvement"** | Used nowhere, with its synonyms (S7); any use is yours to decide on the evidence. |
| 20 | **A second operating-system account for the evaluator** (needs administrator access; Review 2, G8) | Decide before L-B1 or L-C1 is specified. Without it, separation of the promotion set stays procedural and every such result says so. |

### E2. Rules the lead intends to approve under the weekend delegation

ONLY these five, only after the auditor's review of this revision, and reported to the human lead with any choice taken against the reviewer's advice. He may overrule any of them.

1. **The two levels of evidence** (Part B, section 1).
2. **The margin rule** (section 4, "Margin", after Review 2's G3): substantive margins set before observation, noise used only for sample size, the cap as a flag. Not the values, not the fraction, not the timing recommendation.
3. **The power rule** (section 5, "Statistics", after Review 2's G4): paired comparison, cluster bootstrap with strata, the conjunction and what it contains, power by simulation, sample size fixed for a registered power, NOT EVALUABLE (UNDERPOWERED). Not alpha or the power value if he wishes to change them.
4. **The label structure of sections 5 and 6** (parity, no harm, retention).
5. **The ORDER of the M ladder**, M0 to M6. Each rung still needs its own specification and approval.

Not approved under the delegation, and listed in E1 for Monday (apart from what E0 records as decided): section 7's labels; the final-acceptance definition; all of Part S; any number; the reference, domain and model lists; any download or run; M0's run decision; anything in E3.

### E3. Scorecard

**Already done.** Four rows were added to `docs/scorecard/scorecard.toml`, the chart and `README.md` in commit 3b702b9, at the human lead's request, each at score 0 pending his confirmation:

| Title | Note as committed |
|---|---|
| Capability parity with reference models | "Mandatory and untested: no pretrained model has had the memory attached, and no task-level evaluation has been run." |
| Self-optimisation of memory and computation | "Untested: whether the system can learn better retrieval, layout, indexing, updates or consolidation without losing quality." |
| Self-directed capability learning | "Untested: whether the system can set itself useful challenges, use independent feedback and keep the gains without a larger teacher." |
| Sustained improvement across cycles | "Untested: whether gains accumulate over cycles without collapse, self-reinforced errors or costs that cancel the benefit." |

Evidence for each is "No study yet"; the full committed text is in that commit. The commit's comment records which existing rows cover the other properties: property 2, "Teachers complement each other" and "Sequential learning from teachers"; property 3, "Sequential learning from teachers" (no row measures retention alone; none is proposed until M3 is specified); property 4, "Useful capacity scaling", "SSD-backed neural-memory advantage", "Local (sparse) memory updates" and "Scalable read for the flat memory".

**Still a proposal: a fifth row,** which the lead will add. It answers the closing sentence of the second statement.

```toml
[[row]]
title = "Better at learning, not only storing more"
score = 0
note = "Untested: learning efficiency on unseen task families has no measurement yet; a measure is proposed, not approved."
evidence = ["No study yet. Proposed measure: draft ADR-0032, section S6 (not approved)."]
next = "Needs several self-directed cycles first; then a fixed learning budget on task families created after the last cycle."
```

**Still a proposal: a note change,** to the human lead only (Review 1, F19). The row "Quality versus dense alternatives" can be read as a capability claim. Proposed note: "Component evidence: predictive loss on a 27,392-parameter byte-level backbone; not capability." Its score is not touched.

## Review 1 findings and what was done

| Finding | Status | Where; difference if any |
|---|---|---|
| F1 (blocking) final criterion needs an advantage | FIXED | Section 2, "Final acceptance"; section 8 list and Tier 2 comparison |
| F2 (blocking) margin rule | FIXED NOT AS WRITTEN | Section 4, "Margin". The literature note's suggestion to derive δ from noise is not taken. The reviewer's fallback clause ("decided against S₀'s comparison as well") was unclear; rewritten as: the pair stays gated, is marked S₀ ALREADY NON-INFERIOR, and a pass there is not read as a contribution. The cap therefore flags and never lowers δ_e (made explicit in revision 3 by Review 2's G3). Fraction ½ kept as a proposed value, the human lead's to change |
| F3 (blocking) power | FIXED | Section 5, "Statistics"; section 9. Alpha and power marked as proposed values |
| F4 (blocking) complementarity precondition | FIXED | Section 7 |
| F5 labels and S₀ | FIXED | Sections 4 and 5 |
| F6 one system | FIXED | Section 4 |
| F7 reference set | FIXED | Section 4; families and revisions left to the human lead |
| F8 per-evaluation gate; regressions | FIXED | Section 5. Regression cap: printed always, cap set per specification by the human lead (the lead's decision ii) |
| F9 domains | FIXED | Section 4; additions listed as candidates |
| F10 retention rule | FIXED | Section 6. Added: the no-backbone-retraining condition from the second statement |
| F11 superiority | FIXED | Section 7; label mapping proposed per the lead's decision iii |
| F12 independence | FIXED | Section 4 |
| F13 ladder | FIXED NOT AS WRITTEN | Part D. M1 is split into M1a (engineering check) and M1b (the test), with M1.5 placed between them, because M1b needs the teaching procedure |
| F14 feasibility, cost, licences | FIXED | Section 9, with the literature note's sizes, cost estimate and licence warning beside the reviewer's; none re-checked here |
| F15 Part B table | FIXED | Section 3 |
| F16 component rule | FIXED | Section 1 |
| F17 efficiency studies | FIXED | Section 8 and E1 item 6, as a decision for the human lead with a recommendation |
| F18 scope of delegation | FIXED | Status line, E2. Part S is additionally placed outside the delegation |
| F19 scorecard wording | FIXED | E3 (four rows since committed in 3b702b9; the note change is still a proposal) |

## Review 2 findings and what was done

| Finding | Status | Where; difference if any |
|---|---|---|
| G1 routing control vacuous | FIXED | Section 7: labels re-based on "the best control"; BELOW ROUTING added. Section 7's labels moved out of the delegation (E1 item 17) |
| G2 equal-bytes and equal-compute references | FIXED | Section 4, Tier 2; M0 row |
| G3 cap made operational | FIXED | Section 4, "Margin". The timing recommendation is E1 item 2 |
| G4 power rule gaps | FIXED, WITH AN ADDITION | Section 5, "Statistics"; scale check printed there (the review asked for section 9, which points to it). Added by the drafter: S's own discordance is measured on the development split once S exists and the sealed size may only be raised |
| G5 "non-look-up" defined | FIXED | M2 row; PB-1 and E1 item 14 refer to it |
| G6 Part S labels | FIXED | S2 (claim checkpoint, compute primary, replication, cycle correction); S4 (arms 2b and 9, ordered labels, second checker in L-B1, duplicate check, L-B3 frozen program); S5 (baseline condition, trend test) |
| G7 elicitation against acquisition | FIXED | S4, arm 10 and the novel family. The drafter's reservation is in section 9 |
| G8 enforcement on one account | FIXED | S2, with the reviewer's paragraph, what is procedural stated plainly, and E1 item 20 |
| G9 pillar A | FIXED NOT AS WRITTEN | S3: shift test is gate 4; LEARNED POLICY BEATS EXTERNAL SEARCH added; external search defined; own-signals measurement in L-A0 as E1 item 19. Difference: FLOP counts are printed but support no efficiency claim (standing rule on logical work counts) |
| G10 learning-efficiency measure | FIXED | S6. Note 2's crossed arms and its three separate numbers are added to the reviewer's two controls |
| G11 M5 sealed splits | FIXED | S2; L ladder; E1 item 13 |
| G12 feasibility | FIXED | Section 9; M0 row; E1 item 8 |
| G13 scorecard and citation | FIXED | E3; header cites the committed notes |
| G14 mapping of his words | DECIDED IN PART BY THE HUMAN LEAD | E0 item 1 (the "neither teacher" part); the rest of the mapping stays open as E1 item 5 |
| G15 INTERFERENCE and acceptance | DECIDED BY THE HUMAN LEAD | E0 item 2; sections 2 and 7 |
| G16 "once sufficiently capable" | DECIDED BY THE HUMAN LEAD | E0 item 3; S3; L ladder. Each test still needs its own approval |
| G17 the phrase | FIXED | S7, with the reviewer's wording |
| G18 literature hedging | FIXED | Section 4 (two wordings); section 9 (mechanism differs; cost understated; the possibly missing report added as UNVERIFIED) |
