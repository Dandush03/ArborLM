# ADR-0032 — Model-level requirements: capability parity is mandatory; five properties; self-learning as a research pillar; acceptance criteria and proposed tests

**Status: DRAFT (revision 2). NOT APPROVED. Part A records the human lead's two statements of 2026-11-20 as he made them; they are his and need no further approval. Parts B, C, S, D and E are the lead's (Claude's) proposal: no criterion, margin, reference set, label or test in them binds anything until approved. Under the weekend delegation (`docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md`) the lead may approve only RULES of Parts B to D (the margin rule, the power rule, the label structure, the ladder order), each only after a further independent review. Every numeric margin, the reference-model list, the domain list, every model choice, every download, every run decision, and the whole of Part S (self-learning) stay with the human lead. Nothing in this document authorises implementation, downloads, training or execution.**

- Date: 2026-11-20. Draft 1 by the scientific lead (Claude Fable 5.2) in the main session. Review 1 by the `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`): `docs/reviews/adr-0032-model-level-2026-11-20/REVIEW_1.md`, verdict READY AFTER THE LISTED EDITS. Revision 2 by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) under the scientific lead's brief. Revision 2 is not yet independently reviewed. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result. It changes no earlier study: P1 to P10-I, their thresholds, labels, outcome records and rulings stand exactly as recorded. P10-I-S6's registered outcome is and remains **CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)**.
- Literature: for properties 1 to 4 a scratch note exists, `experiments/_scratch/audits/LITERATURE_ADR-0032.md` (a Claude Fable 5.2 subagent, web research only, unreviewed, git-ignored). It is used below as "the note". Its own marks are kept: **[V]** a page fetched in that session and read through an automatic summariser; **[M] UNVERIFIED** from memory; **[E]** its author's estimate. Nothing from it has been re-checked here, and every number from it must be re-read at the source before it enters a specification. For property 5 (self-learning) the literature check is **PENDING**: a separate note has been commissioned and did not exist when this revision was finished. Part S cites no prior work. Section 10 lists what that check must cover.
- Section numbers 1 to 9 are those of draft 1, so that Review 1's references still resolve. The self-learning pillar is Part S (sections S1 to S7), placed between Parts C and D.

> **For the human lead.**
> - **What this is.** Your two statements written down (Part A). Then my proposal for what they imply: how results are read (Part B), how model-level acceptance would be judged for properties 1 to 4 (Part C), how self-learning (property 5) would be investigated without fooling ourselves (Part S), and which preregistered tests could get there (Part D).
> - **What it is not.** Not a result, not a specification, not approval of anything. Each test in Part D needs its own specification and your approval. Self-learning is a proposed future direction, as you said; nothing in it has been shown.
> - **Where the programme stands.** Nothing measured so far bears on capability parity or on self-learning. Every result to date uses a 27,392-parameter byte-level backbone trained in this repository and one measure, predictive loss. No pretrained model has been attached to the memory. No teacher has taught it a capability at model scale. No ArborLM system exists that is capable enough for self-directed learning (Part S, B and C).
> - **What is yours to decide (Part E).** The reference models; every numeric margin; the domain list; which superiority label meets your point 2; whether component efficiency studies continue before a parity result; the scorecard rows and their scores; the first test, its downloads and its run; and everything in the self-learning pillar: its structure, its bounds, its first stage.
> - **What I intend to approve this weekend under your delegation, after re-review, and nothing more:** four rules (section E2). You may overrule any of them on Monday.

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
| 5 | Property 5, autonomous self-improvement | A separate pillar; read only where capability is preserved | Part S | L-series |

Rules proposed:

- **Efficiency without the gate.** If the gate fails, efficiency figures are still recorded, labelled **NOT A COMPENSATING RESULT**, and enter no conclusion.
- **Final acceptance (Part A, "ultimate success criterion").** Model-level acceptance requires both (a) the gate (orders 1 and 2) against every reference of the registered set, and (b) at least one advantage, named and given a margin before observation, measured against the same references: lower acquisition cost (data, teacher queries, measured compute or wall time to reach the registered capability level), less forgetting than the strongest Tier 1 continual-learning baseline, capability that grows with stored memory at fixed active compute, or a measured efficiency gain. Parity without an advantage is labelled **PARITY WITHOUT DEMONSTRATED ADVANTAGE** and is not acceptance. An advantage without parity is labelled **NOT A COMPENSATING RESULT**.
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
- **One system.** S is one frozen checkpoint (backbone, memory, router, adapters) evaluated on every evaluation. No per-domain or per-item selection of checkpoint, memory or setting; no evaluation-time information about task or capability that is not given identically to every reference; no checkpoint selection on a test split. Prompts, few-shot examples, chat templates (each model's published template), maximum generation length, decoding settings and number of samples are fixed per evaluation before scoring and are the same for S and every reference except where a model's published template requires otherwise, which is listed. Prompt formats may be chosen only on the development split, by a rule applied to every system alike. **One stack, one precision:** S and every reference run on the same inference stack at the same numeric precision, with thinking mode on or off and its token budget registered per model. (The note reports that 4-bit quantisation alone flips 5.7 to 10.9 % of MMLU answers while the total barely moves [V], and that prompt format and answer order move scores by far more than repeat runs do [V].)
- **Reference set.** A reference is relevant if it is a conventional model that a user would deploy in place of S at equal or lower stored bytes, or at equal or lower active compute, or that served as a teacher. The set is fixed in M0 and may not be reduced afterwards. Two tiers, both needed for the final claim:
  - **Tier 2, the pretrained models being replaced (the parity references).** (a) Each teacher. (b) The strongest available conventional model of the student's family whose stored bytes are at most those of S (student plus memory plus router). (c) The conventional model of the same family with the nearest active compute per token to S. Each at a pinned revision, chosen in M0 before any score of S exists. S₀ is measured beside them for the do-no-harm condition and is **not** a parity reference.
  - **Tier 1, conventional adaptation at matched resources (controls, not parity references).** The same student S₀ improved from the same teachers and teaching data by: distillation into a low-rank adapter; full fine-tuning where feasible; one low-rank adapter per capability with a learned (not oracle) selector (the conventional modular continual-learning baseline, which cannot forget by construction); a flat product-key or memory-layer baseline from the prior literature at matched parameters; and S₀ with retrieval over the teaching data. Every Tier 1 system receives the same teaching data, the same teacher queries, the same training compute within a stated tolerance and the same hyperparameter-search budget as S; the budgets are printed. Tier 1 shows what the ArborLM memory contributes.
  - An ensemble or per-item router of the teachers is a control in section 7. It is not a parity reference, because it is not a single conventional model.
  - *Candidates from the note, for the human lead and the specifications:* in Tier 1, supervised fine-tuning on the teaching data with ground-truth labels where they exist (the note finds that published "student beats teacher" results rest on this [V]), and a nearest-neighbour memory and a pretrained plug-in memory over the same teaching data; in section 7, a learned per-item router and the better teacher sampled k times with a majority vote at the inference cost S is allowed.
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
- **Margin.** For each evaluation e a non-inferiority margin δ_e on the evaluation's own score scale is set by the human lead before any score of S, of a Tier 1 system or of a reference on the evaluation's test split is seen. δ_e is a substantive judgement of a difference that does not matter, not a noise estimate. Measured noise (M0, on a development split) is used only to choose the number of items (section 5, power rule) and to declare an evaluation NOT EVALUABLE when the affordable number of items cannot reach the registered power. In addition, for every reference R and evaluation e: δ_e must be at most **one half** of the lower 95 % confidence bound of (score of R − score of S₀) measured in M0 on the development split. Where R is not shown ahead of S₀ by more than 2·δ_e, the cap cannot hold; then the pair (R, e) is still gated, it is marked **S₀ ALREADY NON-INFERIOR** when S₀ itself passes non-inferiority to R on e, that fact is printed beside the verdict, and a pass on that pair is not read as evidence that teaching or the memory contributed. A margin is never revised after a score of S exists. *The one-half fraction is a proposed value (Review 1, F2) and is the human lead's to change.* The note (its finding 2 and section 2.2) agrees that repeat-run noise is near zero under greedy decoding and is the wrong basis for a margin, but suggests deriving δ from item-sampling error plus measured nuisance spreads. That is not taken: under Review 1's F2, sampling error belongs in the confidence bound and the sample size, not in the margin. The nuisance spreads the note lists (prompt format, answer order, decoding, precision) are removed by fixing them in advance for every system, and are measured in M0 so that the fixing is known to matter.
- **Floor and ceiling (proposal, from the note).** An evaluation where a reference is near chance or near the maximum on the development split cannot show non-inferiority meaningfully. It is labelled NOT EVALUABLE (FLOOR OR CEILING) by a rule registered in M0, before any score of S.

### 5. Parity (mandatory)

**S is at parity with a reference R only if, in every registered evaluation separately (a domain with several evaluations passes only if each passes, and both the in-teaching and out-of-teaching parts pass), the one-sided confidence bound of (score of S − score of R) lies above −δ_e.** No average over evaluations or domains is computed for the verdict; one failing evaluation is a failed parity. Subcategory scores (per subject, per language) are printed and not gated.

**Statistics.** Comparisons are paired on identical items, identical prompts and identical decoding settings. The unit is the item; where items share a source (a problem with several tests, a passage with several questions, a subject) the confidence bound is computed by a cluster bootstrap over sources with at least 10,000 resamples and a registered seed. Each test is one-sided at alpha = 0.05; the verdict is the conjunction over every (evaluation, reference) pair and needs no further multiplicity correction. **Power rule:** before M5's test split is scored, the number of items per evaluation is fixed so that, at the discordance measured in M0 on the development split and a true difference of zero, the probability that every test in the conjunction passes is at least 0.8. An evaluation that cannot reach this within its available or generatable items is **NOT EVALUABLE (UNDERPOWERED)** and is not dropped silently; the domain then carries NOT EVALUABLE, which is not PARITY. Stochastic decoding, where used, draws a registered number of samples per item for every system alike and scores the per-item mean. *Alpha 0.05 and power 0.8 are proposed values inside the rule; the human lead may change them before M0 is frozen.*

What the rule costs, from the note (its author's arithmetic, [E], in line with Review 1's figures): for one paired test at 80 % power the number of items is about 6.2·d/δ², d being the share of items on which the two systems disagree. A conjunction of five such tests needs about 96 % power each for 80 % overall, about 11.5·d/δ². At d = 0.2 and δ = 3 points that is about 1,400 and 2,600 items; the full conjunction over every reference and both splits needs more. The note cites an independent recommendation of at least 1,000 questions per evaluation [V]. A 164-item set such as HumanEval cannot gate anything at a margin of a few points; small public sets are printed, not gated, unless pooled under a registered clustering.

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
- **Interference.** For each evaluation: S taught by both teachers against S taught by the stronger teacher alone. A loss beyond the margin is **INTERFERENCE (named evaluation)**.
- **Composition.** Items that neither teacher solves alone, built so that solving them needs what each teacher is better at. Composition items are generated before S exists, by a procedure written without access to S, and shown in M0 to be failed by each teacher, by S₀ and by the registered pipeline of the two teachers (one teacher's output given to the other).
- **Precondition (complementarity).** For each domain named in advance for superiority, M0 must show on the development split that the item-level union of the teachers exceeds the better teacher's score by more than δ_e, with the lower 95 % bound (paired, cluster bootstrap) above δ_e. Where it does not, superiority in that domain is **NOT EVALUABLE (NO COMPLEMENTARITY)**. Coverage (each teacher ahead of S₀ somewhere) is a separate condition read per domain and is not required for superiority.
- **Superiority.** Read only after PARITY. In each domain named in advance (one domain, or several with Holm correction across them):
  - **COMBINES (NO GAIN BEYOND ROUTING)** if S is non-inferior to but not above the domain-level router (each item sent to the teacher better on that domain).
  - **SUPERIOR BY COMBINATION** if S's lower bound against the better teacher and against the domain-level router both exceed δ_e but S does not exceed the item-level union.
  - **SUPERIOR BEYOND THE UNION** if S's lower bound also exceeds the item-level union score (oracle per-item best of the two teachers) by δ_e, or if S solves composition items that no teacher, no router and no registered pipeline solves.
- *Proposal on which label meets which of the human lead's words (his to confirm):* SUPERIOR BY COMBINATION meets "preserve complementary capabilities" (second statement, property 2). Only SUPERIOR BEYOND THE UNION meets "capabilities that neither teacher provides independently" (first statement, point 2).

### 8. Efficiency and scalability (behind the gate)

Measured, never logical: knowledge acquisition cost (data, teacher queries, wall time and energy or hardware-hours to reach a registered capability level); forgetting relative to Tier 1; latency and memory at inference; bytes stored per capability; the cost of an update; behaviour as the memory grows; reads from SSD. Each against the Tier 1 alternative reaching the same capability **and against each Tier 2 reference**. Reported with the parity verdict beside every figure.

*Proposal on studies under way (Review 1, F17; the human lead's decision, E1 item 6):* the second statement's property 4 ends "without sacrificing capability". Component-scale efficiency and SSD studies (for example P10-II-S5) may continue as component evidence. They are never read as an ArborLM advantage before a parity result.

## Part S — Self-learning (property 5): a proposed research pillar

Nothing in this part is approved, and none of it falls under the weekend delegation. It is a proposal for the human lead. No capability is assumed.

### S1. The three questions, and what "self" has to mean

| | Question (his words, shortened) | The claim that would be new | The dull explanation that must be excluded |
|---|---|---|---|
| **A** | Can ArborLM learn better retrieval, layout, indexing, sparse-update or consolidation, with quality preserved? | A policy the system learns from its own operation beats what an outside search finds at equal cost, and keeps working on a workload it was not tuned on | Ordinary hyper-parameter or policy tuning under a new name |
| **B** | Can it generate useful challenges, get reliable independent feedback, improve, and retain, without a larger teacher continuously? | Its own choice of what to practise yields a verified capability gain that random practice does not | Any practice on verified data helps; the "self" part adds nothing. Or: the gain only draws out what the pretrained student already knew |
| **C** | Do the gains accumulate over cycles without collapse, error reinforcement or runaway cost? | Repeated, independently validated gains at bounded cost | One gain counted several times; a curve read off a set the process has tuned itself to |

### S2. Rules common to A, B and C (proposal)

**Three roles, three processes.** The **improving process** (the system changing itself), the **evaluator** (holds the held-out sets and scorers), and the **supervisor** (holds limits, stop rules and the ledger). The improving process has no read or write access to the other two. This is enforced by the operating system (separate user, file permissions, no network), not by instruction. The hashes of the harness, the evaluation code, the limits and the stop rules are checked before and after every cycle; a change makes the run **INVALID (TAMPERED)**.

**What "cannot inspect or optimize directly" means.** Four kinds of data, kept apart:

| Set | Who holds it | What the improving process may receive | Use |
|---|---|---|---|
| Practice data | Improving process | Everything, including per-item verified feedback | Learning |
| Promotion set | Evaluator | No items, no per-item feedback. At most Q aggregate readings, Q fixed before cycle 1, each a pass or fail against a registered threshold, each counted as one adaptive query | Deciding whether a cycle's checkpoint is promoted. Treated as used up; never the basis of a claim |
| Sealed set | Evaluator | **Nothing, ever.** Scored once, after the last cycle, on every cycle's checkpoint, promoted or not | Every claim |
| New-family set | Evaluator | Nothing before the learning-efficiency measurement (S6) | The measure of learning faster |

The lead's guidance allowed "a limited number of aggregate readings" of the sealed set. This revision proposes none: readings go to a separate promotion set, so the set that carries the claim is never queried during the run. A sealed set is used for one study. The next study draws a new one from the frozen generator with a new registered seed, because people reading a result and designing the next study are adaptive queries too.

**Independent feedback (B and C).** The learning signal comes from a verifier the model does not control: execution of code against hidden tests, rule-checkable or formally verifiable tasks, exact-answer generators. The verifier is frozen before cycle 1, is not written or changeable by the improving process, and returns a verdict, never the hidden tests. Its false-accept rate is measured on planted wrong answers before any learning (L-B0). Model-graded feedback is never the sole signal.

**Bounds.** Fixed before cycle 1 and held by the supervisor: the number of cycles; per-cycle limits on compute, wall time, memory growth and disk; the stop rules (retention failure, tamper, limit overrun, verification-failure rate above a registered level). No network. Sandboxed execution. The improving process cannot change its limits, the evaluation code, the harness or the stop rules, cannot start processes outside its sandbox and cannot write outside its registered directories. Each stage lists its allowed actions (S3 to S5). **Any expansion of scope needs a new specification and the human lead's approval:** more cycles, more compute, a new domain, a new kind of action.

**Records.** The supervisor appends every cycle to a ledger the improving process cannot write: promoted or not, every regression, every stop. Unpromoted cycles are scored on the sealed set like the others.

**Capability and efficiency are measured separately.** Capability by the rules of sections 4 and 5 (same margin rule, same power rule, paired, per evaluation). Cost is measured, never logical. Improved training loss is never a capability claim.

**Replication.** "Repeated, independently validated" is given a meaning before any run: gains in at least m separate cycles of one run, and the whole run repeated R times with different registered seeds and freshly drawn sealed sets, scored by the evaluator and recomputed from raw records by the auditor. m and R are the human lead's.

### S3. Pillar A — self-optimisation of memory and computation

**Question.** Can the system, using only signals available in its own operation (its access traces, its own loss on practice data), learn a retrieval policy, memory layout, index, sparse-update rule or consolidation method that lowers measured cost while quality stays non-inferior?

**Where it can start.** At component scale, before any model-level result. It then yields component evidence only (section 1).

**Prerequisite milestones.**

- PA-1. A cost measurement that is repeatable on this machine, with its noise measured. (P10-I-S1 is blocked on a quiet-machine limit; A inherits that problem.)
- PA-2. A store with qualified addressing at the size used, and a quality evaluation with a margin and a power calculation.
- PA-3. For L-A3 only: a real student that has passed M2.

**Allowed actions.** Parameters of the retrieval policy, layout, index, consolidation schedule and update rule. Not the backbone weights, the evaluation, the harness or the limits.

| Stage | What it does | Decisive comparison | Registered negative outcomes |
|---|---|---|---|
| **L-A0** | No self-optimisation. Measures the hand-designed fixed policy, random search and a standard hyper-parameter or policy search, at registered budgets. Measures cost noise. | Is there any headroom at all? | NOT EVALUABLE (NO HEADROOM); NOT EVALUABLE (COST TOO NOISY) |
| **L-A1** | One action type (proposed: the retrieval policy), component scale. Optimised on one workload; read on held-out queries and on a shifted workload. | Self-optimiser against the best L-A0 search at equal total compute, the self-optimiser's own overhead included | QUALITY LOST (named); NO MEASURED GAIN; TUNING (NO GAIN OVER EXTERNAL SEARCH); DOES NOT TRANSFER (HELD-OUT WORKLOAD) |
| **L-A2** | Layout, indexing, consolidation, sparse updates. SSD work needs its own approval. | As L-A1 | As L-A1 |
| **L-A3** | The same on a real student. | As L-A1, with task-level quality on every registered evaluation | As L-A1; HARM (named evaluations) |

**Gate (all three).** (1) Quality non-inferior on every registered evaluation, by the margin and power rules of sections 4 and 5. (2) A measured cost reduction whose lower bound exceeds a registered minimum. (3) Better than the best external search given the same compute, beyond a registered margin. The cost of the optimisation itself is counted, and the number of queries needed to pay it back is printed.

**The one place "self" could mean something.** After a registered workload shift, the self-optimiser adapts within its budget with no outside re-tuning. It is compared with the externally tuned policy left frozen and with the external search re-run at the same budget. If the external search re-run is as good, the label is TUNING.

**Labels.** TUNING (NO GAIN OVER EXTERNAL SEARCH); **SELF-OPTIMISES (COMPONENT)** for L-A1 and L-A2; **SELF-OPTIMISES (MODEL LEVEL)** for L-A3 only.

**What may not be claimed.** An efficiency advantage of ArborLM (no parity result exists). "Self-improvement" without the qualifier. Anything from logical work counts. Anything about capability.

### S4. Pillar B — self-directed capability learning

**Question.** Can a real student with the ArborLM memory choose or write its own practice, learn from independently verified feedback, show a verified capability gain on a set it never saw, and keep it, with no teacher queries during the cycle?

**Prerequisite milestones.**

- PB-1. A real student that has passed M2, including M2's capability that is not a look-up. *Departure from the lead's guidance, which asked for M2 only: if only the look-up capability was acquired, B could at most show self-directed memorisation, so the non-look-up pass is proposed as required.*
- PB-2. M3 has been run, so that the retention machinery exists and a forgetting problem is known before B. L-B2 and later need M3 to read RETENTION HOLDS.
- PB-3. The verifier and sandbox of M0, tested with adversarial items, with a measured false-accept rate.
- PB-4. Challenge generators frozen, with some task families sealed and held by the evaluator.

| Stage | Allowed actions | What it does |
|---|---|---|
| **L-B0** | None (no learning) | Qualifies the verifier and the generators. Checks that the student's starting score on the task families is interior (not at floor or ceiling). Outcomes: VERIFIER NOT RELIABLE; GENERATOR TOO NARROW; NOT EVALUABLE (NO HEADROOM). |
| **L-B1** | Choose challenges from a **frozen** generator (family, difficulty, parameters); attempt; receive the verifier's verdict; write to memory | One cycle, one rule-checkable domain. This is self-selected practice, not yet self-written challenges, and is labelled so. |
| **L-B2** | As L-B1 | Retention of the L-B1 gain after a further capability is acquired (rule of section 6), and of every earlier capability after the L-B1 cycle. |
| **L-B3** | Also write free-form challenges. An item is admitted only if an independent validity check accepts it. **New action type: needs the human lead's approval.** | Tests whether self-written challenges add anything over self-selected ones. The rate of rejected items is recorded. |

**Arms of L-B1, at equal compute and an equal number of verified examples.**

| Arm | Answers |
|---|---|
| 1. Self-selected practice, ArborLM memory | The system under test |
| 2. The same number of challenges drawn at random from the same generator | Is self-selection better than random? |
| 3. A fixed hand-designed curriculum (a fixed training strategy) | Is it better than an obvious schedule? |
| 4. Continued teaching by the larger teacher | What does doing without the teacher cost? |
| 5. Self-distillation (training on its own unverified outputs) | Does the verifier matter? |
| 6. Conventional continual learning on the same verified data (adapter, with replay) | Is the memory the right place to store the gain? |
| 7. Retrieval over the verified solutions, no learning | Is it more than look-up of solved items? |
| 8. No learning, evaluated again | Noise floor |

**Read on:** the sealed set from the practised families; a sealed set from families never practised; every earlier capability (section 6); measured cost. Teacher queries during the cycle are counted and must be zero for arm 1.

**Labels.** NO GAIN. **GAIN FROM PRACTICE, NOT FROM SELF-DIRECTION** (arm 1 gains but is not above arm 2 beyond the margin). **SELF-DIRECTED GAIN (ONE CYCLE)** (arm 1's lower bound over its own start exceeds the margin, NO HARM on every registered evaluation, and arm 1 exceeds arm 2 beyond the margin). Qualifiers always printed: GAIN LIMITED TO PRACTISED FAMILIES; TEACHER AHEAD AT EQUAL COMPUTE or MATCHES CONTINUED TEACHING; MATCHED BY RETRIEVAL. GAIN WITH REGRESSION (named) is not a gain.

**What may not be claimed.** Independence from teachers in general: the student and its memory were made by teachers. New capability as opposed to drawing out what the pretrained student already held, unless the specification has a control that separates them. Anything outside the registered, rule-checkable domains. Anything about general intelligence.

### S5. Pillar C — sustained improvement

**Question.** Over a fixed number of cycles, do verified gains repeat and add up, with every earlier capability retained, without the practice data degrading, and at a cost that does not grow until it cancels the gain?

**Prerequisite milestones.** L-B1 with a gain label; L-B2 with RETENTION HOLDS; the roles and sets of S2 built and tested with a deliberate tamper attempt and a deliberate leak attempt that the harness must catch.

| Stage | What it does |
|---|---|
| **L-C1** | K cycles of the L-B1 loop in one domain. K, the per-cycle limits and the stop rules are fixed before cycle 1. Every cycle is recorded. Allowed actions: those of L-B1. |
| **L-C2** | The learning-efficiency measurement of S6 on the checkpoints of L-C1. No new training of the loop. |
| **L-C3** | Not proposed now. Any extension: more cycles, more domains, self-written challenges inside the loop, the system editing its own training code. Each needs a new specification and the human lead's approval. |

**Measured every cycle (by the supervisor and evaluator, not shown to the improving process).**

- **Retention:** every earlier capability, same rule as section 6. A failure stops the run.
- **Health of the practice data:** number of distinct families and spread of parameters; duplicate rate; validity rate; the rate of self-chosen or self-written items whose independent verification fails; the score of the cycle-0 system on cycle-k challenges (a rising score means the challenges are getting easier); on a sample, a second independent verifier's rate of wrong answers that were accepted.
- **Cost:** compute, wall time, memory rows and bytes added, and the inference cost of the cycle-k system (reads can grow as the memory grows). Reported as capability gained per unit of compute, of memory growth and of time, per cycle, with the cumulative curve.

**Baselines at equal cumulative compute.** The arms of L-B1 run for the same K cycles, in particular random selection, continued teaching, conventional continual learning and retrieval.

**Labels.**

- **ACCUMULATES OVER k CYCLES**: on the sealed set, the cycle-k system exceeds the cycle-0 system beyond the margin; at least m cycles each show a gain over the previous promoted checkpoint with a lower bound above zero; retention held throughout; and this repeats in R independent runs.
- SINGLE GAIN, NOT REPEATED. PLATEAU AFTER k CYCLES.
- **COLLAPSE (cycle c, cause)**: retention failure, validity or diversity below a registered level, or a sealed score below cycle 0.
- **ERROR REINFORCEMENT**: the accepted-wrong rate or verification-failure rate rises across cycles while the sealed score does not.
- **COST GROWING**: the cost per unit of gain rises from cycle to cycle beyond a registered factor. **COST EXCEEDS BENEFIT**: a baseline given the same cumulative compute reaches the same sealed score.
- PROMOTION SET OVERFITTED: the promotion readings rise and the sealed score does not.

### S6. "Better at learning, not simply storing more": a separate measure

Capability level and learning efficiency are different quantities. Proposed definition:

- Take task families **never used in any cycle**, defined before cycle 1 and held by the evaluator.
- Give the cycle-k system and the cycle-0 system the **same fixed learning budget** on them (the same examples, the same compute, the same fixed procedure).
- The measure is the **gain produced by the budget**: score after minus score before, per unit of compute and per example. What a system already knew raises its score before learning and therefore does not move the measure. Families are chosen so that both systems start in the interior.
- **Storage control:** the cycle-0 system given, by plain retrieval, everything the cycle-k system stored. If this control learns the new families as fast, the result is **LEARNS FASTER (EXPLAINED BY STORED CONTENT)**. Only otherwise is it **LEARNS FASTER (NOT EXPLAINED BY STORED CONTENT)**.
- Negative outcomes: NO CHANGE IN LEARNING EFFICIENCY; LEARNS SLOWER.

### S7. The claim ladder, and what is never claimed

| Label | Stage | Needs | Says | Does not say |
|---|---|---|---|---|
| TUNING (NO GAIN OVER EXTERNAL SEARCH) | L-A1 to L-A3 | Quality held, cost lower, external search as good | A parameter was tuned | Any self-improvement |
| SELF-OPTIMISES (COMPONENT) | L-A1, L-A2 | The three gates of S3 | A learned policy beat outside search on a small system | Anything about a model, or an ArborLM advantage |
| SELF-OPTIMISES (MODEL LEVEL) | L-A3 | The same on a real student, NO HARM | The same at model level | Capability gain |
| SELF-DIRECTED GAIN (ONE CYCLE) | L-B1 | S4 | One verified gain that random practice did not give | Accumulation; independence from teachers in general |
| ACCUMULATES OVER k CYCLES | L-C1 | S5, replicated | Repeated verified gains within k cycles | That it continues beyond k |
| LEARNS FASTER (NOT EXPLAINED BY STORED CONTENT) | L-C2 | S6 | Higher gain per unit budget on unseen families | General intelligence |

Rules:

- The human lead's rule stands as written: "Do not claim recursive self-improvement without repeated, independently validated capability gains." No label in this ladder uses that phrase. Whether it is ever used, and on what evidence, is his decision.
- Improved training loss is never a capability claim (his words: "Do not equate improved training loss with increased general intelligence").
- Every L label carries (PARITY UNTESTED) or (NOT AT PARITY) until a PARITY verdict exists (section 2).
- A label is printed only for the registered domains, cycles and budgets. Nothing is extrapolated.

## Part D — Proposed preregistered tests (none approved; each needs its own specification)

### The M ladder (properties 1 to 4), in order of execution

| Test | Question | Needs | Registered negative or blocking outcomes |
|---|---|---|---|
| **M0 — references, evaluation harness, fixings** | What do S₀ and each reference score per evaluation on development splits? What is the discordance (for the power rule)? Where is each teacher ahead of S₀? Are the teachers complementary item by item? Also fixes: S₀, the Tier 2 references, development and sealed test splits, prompts and decoding. References are measured on the stack and precision that M1 will use; another stack serves only as a cross-check. Includes a timed pilot on a few dozen items and a cost projection. | Licence check of every exact model revision and benchmark; downloads (the human lead's); new code (model loaders, tokenizers, harness, sandbox) and packages the locked environment lacks, so **an amendment to `uv.lock` and `pyproject.toml`, which needs approval**; a ruling on models that run repository code at load. No ArborLM code. The choice of S₀ depends on a model the memory can be attached to (width, tokenizer, licence). | NOT EVALUABLE (UNDERPOWERED) or (FLOOR OR CEILING) per evaluation; NO COMPLEMENTARITY per domain; TEACHER NOT AHEAD per domain; REFERENCE NOT RUNNABLE LOCALLY. What follows if the two teachers do not differ is registered in advance |
| **M1a — attachment (engineering check, not a test)** | With the memory attached and inert, is S identical to S₀ (bitwise or within a stated tolerance)? | M0; a way to attach the memory to a token-level pretrained model, which does not exist yet | ATTACHMENT NOT IDENTITY (a defect to fix, not a finding) |
| **M1.5 — teaching data and procedure** | What do the teachers generate, how much, how is it filtered, and does it pass the overlap check of section 4? Frozen here; it is also what every Tier 1 system trains on. No score of S. | M0 | TEACHING DATA OVERLAPS EVALUATION; licence does not allow training on teacher outputs |
| **M1b — do no harm on a real student** | After teaching one narrow capability, is every evaluation within its margin of S₀? | M1a, M1.5 | HARM (named evaluations): stops the ladder cheaply |
| **M2 — one teacher, two capabilities** | For one capability that is a look-up and one that is not: does S match the Tier 1 systems, and how much of the gap to the teacher closes? | M1b | NOT ACQUIRED (named); **NON-LOOK-UP NOT CARRIED** (the look-up is acquired, the other is not) |
| **M3 — sequential retention** | Section 6, with two then three capabilities | M2 passing for each capability used. **"M2 passing" means: acquired in the sense of section 6 (MATCHES CONVENTIONAL ADAPTATION (TIER 1) for that capability, and above S₀).** Fewer than two acquired: NOT EVALUABLE (TOO FEW ACQUIRED) | RETENTION FAILS (named capability and order) |
| **M4 — two teachers** | Section 7 | M0 showing complementarity; M2 for each teacher | INTERFERENCE; COMBINES (NO GAIN BEYOND ROUTING); NOT EVALUABLE (NO COMPLEMENTARITY) |
| **M5 — model-level acceptance** | Sections 5 to 7 on the full list, both tiers, on the sealed test splits, used here once | M2 to M4 | NOT AT PARITY; PARITY WITHOUT DEMONSTRATED ADVANTAGE; NOT EVALUABLE |
| **M6 — efficiency and scale** | Section 8, and the advantage required for final acceptance | M5 at PARITY | NOT A COMPENSATING RESULT if read without parity |

Each test registers its labels, margins, seeds, stopping rules and negative outcomes before any score is seen, as the P10-I studies did, and is run once.

### The L ladder (property 5) and its dependencies

| Test | Depends on (M-series) | Depends on (L-series and other) | Scale | First possible label |
|---|---|---|---|---|
| L-A0 | none | PA-1, PA-2 | Component | (baselines only) |
| L-A1 | none | L-A0 with headroom | Component | SELF-OPTIMISES (COMPONENT) |
| L-A2 | none | L-A1; SSD approval where storage is touched | Component | SELF-OPTIMISES (COMPONENT) |
| L-A3 | M1b, M2 | L-A1 | Model | SELF-OPTIMISES (MODEL LEVEL) |
| L-B0 | M0 (sandbox, verifier), M2 including the non-look-up capability | PB-3, PB-4 | Model | (qualification only) |
| L-B1 | M2; M3 run | L-B0 | Model | SELF-DIRECTED GAIN (ONE CYCLE) |
| L-B2 | M3 at RETENTION HOLDS | L-B1 with a gain | Model | (retention of the gain) |
| L-B3 | as L-B2 | L-B2; approval of the new action type | Model | — |
| L-C1 | as L-B2 | L-B1 with a gain, L-B2 | Model | ACCUMULATES OVER k CYCLES |
| L-C2 | as L-C1 | L-C1 with at least one promoted cycle | Model | LEARNS FASTER |

In one line: `M0 → M1a → M1.5 → M1b → M2 → M3 → M4 → M5 → M6`; `L-A0 → L-A1 → L-A2` needs no M; `M2 → L-A3`; `M2 + M3 → L-B0 → L-B1 → L-B2 → L-C1 → L-C2`. None of the L-series needs M5, so every L label carries (PARITY UNTESTED) until M5 exists.

### 9. Known open problems, stated now

Properties 1 to 4:

- **The memory has never been attached to a pretrained token-level model.** Every mechanism result is on a byte-level backbone of 27,392 parameters. Whether any of it carries over is unknown.
- **A key-value memory may not carry capabilities that are not look-ups.** The note reports prior evidence in this direction: nearest-neighbour memories improved memory-type tasks and mostly lowered reasoning scores [V], and memory layers that helped broadly were trained jointly with the backbone from scratch, which is not this setting [V]. M2 is built to answer the question in the negative early.
- **Parity of a small student plus memory with a much larger teacher on every evaluation is a strong claim and may be unattainable.** The note found no prior result of that kind and says so with the caution that absence in one search is not proof of absence. It is a well-posed test and is not redefined to make it attainable. Tier 1 may be matched while Tier 2 parity fails; that is reported as NOT AT PARITY.
- **Combining teachers may not exceed the better one.** The note reports a multi-model fusion that beat its best source on average, lost on individual tasks and was below the best source on every code task [V]; learned routers that only reached the best single model while the per-item oracle was far above [V]; and mixing different models losing to sampling the best one several times [V]. The union is therefore a generous ceiling, and sections 5 and 7 gate per evaluation for this reason.
- **Whether the two teachers differ at all is open.** The note found no published scores that settle it [V]. M0 measures it; M0's specification registers what follows if they do not.
- **Statistical power.** The verdict is a conjunction; the chance that a truly equal system passes falls with every test added (both splits of every evaluation, every reference). Section 5 gives the order of magnitude. Private, programmatically generated item sets are therefore a necessity, not an option.
- **Memory, disk and model choice.** The note lists three candidate sets of two small Qwen students, one Qwen teacher of 7B to 9.65B parameters and one GLM teacher of 9.4B, at 38 to 44 GB of downloads at published precision [V for sizes, E for totals], inside the standing 50 GB delegation only if what P10 has already downloaded and any code-execution image are small; the delegation is cumulative and neither was counted. The equal-bytes and equal-compute references of section 4 are not in those sets and add to the total. Larger GLM releases exceed the budget [V]. All candidates fit in 48 GB one at a time at BF16, so no quantisation is needed [E]; registered runs sharing the machine reduce the headroom. No set is chosen here.
- **Evaluation cost.** Review 1 expected hours to days per system; the note estimates hours per model and one to three days of machine time for a whole battery on four models, without thinking mode [E, from a third-party throughput table, not measured here]. Either way it is multiplied by every reference, Tier 1 system, seed and order. M0's timed pilot replaces both estimates and states which evaluations are infeasible locally (NOT EVALUABLE, not dropped).
- **Licences.** The note reports the candidate Qwen models tagged Apache-2.0 (licence files not opened) and the 2025 GLM 9B releases under MIT (file opened) [V]. **Warning from the note:** the older GLM-4 9B and GLM edge models carry a custom licence with a naming clause for any model trained or improved with them and a registration rule for commercial use [V, through a summariser]; they are to be avoided as teachers unless the human lead accepts those terms. Some benchmark licences are non-commercial or forbid derivatives [V]. Each exact revision and benchmark is checked again in M0's specification. This is a reading of licence texts, not legal advice.
- **Generated code needs a real sandbox.** A container or virtual machine without network; pulling its image is a download and counts against the budget.
- **Agent independence.** Evaluation code and teaching code written by agents of one provider are not independent in the strong sense.

Property 5:

- **No ArborLM system capable enough for B or C exists.** B and C are several passed rungs away. Specifying them in detail now would be premature; this ADR fixes their rules and order only.
- **A at component scale may be ordinary meta-optimisation under a new name.** The gate in S3 is built so that this outcome gets the label TUNING.
- **Adaptive overfitting to held-out sets**, by the process and by the people designing the next study. S2 limits it; it does not remove it.
- **Self-generated error reinforcement.** A verifier with a non-zero false-accept rate lets wrong answers into memory, and each cycle can compound them. Only domains with strong verifiers are proposed, which narrows what any B or C result can be said to show.
- **Drawing out against acquiring.** A pretrained student may already hold what practice appears to teach. Separating the two needs a control that is not yet designed.
- **"Self-selected" is a weak form of "generates challenges".** L-B1 only chooses from a frozen generator. Free-form generation (L-B3) has a harder validity problem.
- **A rule-checkable domain is not general capability.** Gains in verifiable code or arithmetic say nothing about reasoning or language at large.
- **Containment is engineering that does not exist yet** (process separation, tamper checks), and it must be tested before it is trusted.

### 10. Literature: what exists, what is pending

**Properties 1 to 4.** The note covers distillation, multi-teacher distillation, merging and routing, continual-learning measures and baselines, external memories, statistical practice, candidate evaluations, candidate model versions and licences, and feasibility on this machine. It is a scratch note, unreviewed. Its author read no paper end to end; figures come from abstracts and machine-summarised pages. Its [M] UNVERIFIED items include the standard continual-learning formulas, the intersection-union reference and several licences; they stay UNVERIFIED wherever used. Before M0's specification, the items it relies on are re-read at the source, and the note is reviewed by the auditor.

**Property 5: PENDING.** The note was commissioned before the self-learning pillar existed and does not cover it. A separate note is being prepared. Part S cites no prior work and claims no novelty. Before any L-stage is specified, the check must cover at least:

- self-play and automatic curriculum generation;
- self-training and self-distillation, and the reported degradation of models trained on their own outputs;
- learned index structures and learned retrieval, caching or consolidation policies;
- meta-learning and learning-to-learn measures, including how learning speed is separated from prior knowledge (for S6);
- automated machine learning and hyper-parameter search, as the external baselines of pillar A;
- code-generation loops with execution feedback, and the reliability of generated tests as verifiers;
- adaptive data analysis and the reuse of held-out sets;
- evaluation and containment practice for systems that modify themselves.

The check may change the baselines, the arms, the measure of S6 and the labels.

## Part E — Decisions

### E1. Decisions that stay with the human lead (for Monday 2026-11-23), with the lead's recommended option

| # | Decision | Recommended option (proposal) |
|---|---|---|
| 1 | **Reference set**: the rule of section 4, and the model families and revisions | Both tiers, with the equal-bytes and equal-active-compute models in Tier 2 and S₀ not a parity reference. Do not narrow to "teachers alone". Families and revisions chosen in M0's specification. |
| 2 | **Numeric margins** δ_e and ρ_c; the cap fraction; alpha and power | Values set per evaluation in each specification, before any score. Cap fraction ½. Alpha 0.05, power 0.8. |
| 3 | **Domain list** and the candidate additions of section 4 | The four domains; add mathematics and multilingual ability; decide the others at M0's specification, where their cost is known. |
| 4 | **Item-level regression cap** | Printed always; a cap per evaluation registered in each test's specification. |
| 5 | **Which superiority label meets your point 2** | SUPERIOR BY COMBINATION meets "preserve complementary capabilities"; only SUPERIOR BEYOND THE UNION meets "capabilities that neither teacher provides independently". |
| 6 | **Component efficiency and SSD studies before a parity result** (for example P10-II-S5) | Continue as component evidence; never read as an ArborLM advantage before a parity result. |
| 7 | **Scorecard**: the new rows, their scores, and the note change of E3 | Add the rows at 0. Scores are yours. |
| 8 | **First test**: have M0 specified now; its downloads, lockfile amendment and run | Specify M0 now (it needs no ArborLM result), after the note's relied-on items are re-read at the source. Downloads, the lockfile amendment and the run decision held for you. |
| 9 | **Model choices**: S₀, teachers, further references | Decided in M0's specification, by you. The note's candidate sets (section 9) are a starting point; none is recommended before the cumulative download count and the licence files are checked. Avoid the custom-licensed older GLM models. |
| 10 | **Self-learning pillar**: accept Part S as the frame (roles, sets, bounds, order, labels) | Accept as a frame; approve no stage yet. |
| 11 | **Self-learning, first stage** | L-A0 may be specified once the self-learning literature check exists; it is component scale and measurement only. B and C wait for M2 and M3. |
| 12 | **Self-learning numbers**: cycles K, promotion readings Q, m and R, budgets, minimum cost reduction | Set in each stage's specification; small K first. |
| 13 | **Whether B and C may run before M5** | Yes, with (PARITY UNTESTED) on every label; otherwise the pillar waits for the whole M ladder. |
| 14 | **PB-1**: require M2's non-look-up capability before B | Yes. |
| 15 | **The phrase "recursive self-improvement"** | Used in no label; any use is yours to decide on the evidence. |

### E2. Rules the lead intends to approve under the weekend delegation

Only these, only after the auditor's review of this revision, and reported to the human lead with any choice taken against the reviewer's advice. He may overrule any of them.

1. **The margin rule** (section 4, "Margin"): substantive margins set before observation, noise used only for sample size, the cap in its form. Not the values, not the fraction.
2. **The power rule** (section 5, "Statistics"): paired comparison, cluster bootstrap, conjunction, sample size fixed for a registered power, NOT EVALUABLE (UNDERPOWERED). Not alpha or the power value if he wishes to change them.
3. **The label structure** of Parts B and C: the two levels of evidence; final acceptance needing the gate and an advantage; the labels of sections 5 to 7.
4. **The ladder order** M0 to M6.

Not approved under the delegation: any number; the reference, domain and model lists; any download or run; M0's run decision; anything in Part S; anything in E3.

### E3. Scorecard rows proposed (the lead will not edit `docs/scorecard/` or `README.md` from this document; scores are the human lead's)

```toml
[[row]]
title = "Capability parity with reference models"
score = 0
note = "No model-level evaluation exists; the other rows are component evidence and do not add up to this one."
evidence = ["No study yet. Requirement and proposed criteria: ADR-0032 (draft, not approved)."]
next = "M0: reference models and evaluation harness (to be specified; needs approval, downloads and a lockfile amendment)."

[[row]]
title = "Self-optimisation of memory and computation"
score = 0
note = "Untested: no study has let the system change its own retrieval, layout or consolidation."
evidence = ["No study yet. Proposed stages L-A0 to L-A3: ADR-0032 Part S (draft, not approved)."]
next = "L-A0: fixed-policy and external-search baselines with measured cost (to be specified)."

[[row]]
title = "Self-directed capability learning"
score = 0
note = "Untested, and no system capable enough exists: needs a real student that has acquired a capability."
evidence = ["No study yet. Proposed stages L-B0 to L-B3: ADR-0032 Part S (draft, not approved)."]
next = "Blocked on M2 and M3. Then L-B0: qualify the verifier and challenge generators."

[[row]]
title = "Sustained improvement across cycles"
score = 0
note = "Untested: no learning cycle has been run, so nothing can accumulate or collapse yet."
evidence = ["No study yet. Proposed stages L-C1 and L-C2: ADR-0032 Part S (draft, not approved)."]
next = "Blocked on L-B1 and L-B2."

[[row]]
title = "Better at learning, not only storing more"
score = 0
note = "Untested: learning efficiency on unseen task families has no measurement and, until ADR-0032, no definition."
evidence = ["No study yet. Proposed measure: ADR-0032 section S6 (draft, not approved)."]
next = "Blocked on L-C1. The measure itself needs review against the literature first."
```

The fifth row is optional; it answers the closing sentence of the second statement and could instead be folded into the fourth.

Existing rows that already cover the other properties:

| Property | Existing rows |
|---|---|
| 1 (parity) | "Works on a real pretrained student", "Beats plain retrieval", "Generalises beyond stored items", "Quality versus dense alternatives" are component or prerequisite rows; the new first row is the property itself |
| 2 (multi-teacher) | "Sequential learning from teachers", "Teachers complement each other" |
| 3 (continual learning) | "Sequential learning from teachers" (no row measures retention alone; propose none until M3 is specified) |
| 4 (memory and efficiency) | "Useful capacity scaling", "SSD-backed neural-memory advantage", "Local (sparse) memory updates", "Scalable read for the flat memory" |

Proposed note change, to the human lead only (Review 1, F19): the row "Quality versus dense alternatives" can be read as a capability claim. Proposed note: "Component evidence: predictive loss on a 27,392-parameter byte-level backbone; not capability." Its score is not touched.

## Review 1 findings and what was done

| Finding | Status | Where; difference if any |
|---|---|---|
| F1 (blocking) final criterion needs an advantage | FIXED | Section 2, "Final acceptance"; section 8 list and Tier 2 comparison |
| F2 (blocking) margin rule | FIXED NOT AS WRITTEN | Section 4, "Margin". The literature note's suggestion to derive δ from noise is not taken. The reviewer's fallback clause ("decided against S₀'s comparison as well") was unclear; rewritten as: the pair stays gated, is marked S₀ ALREADY NON-INFERIOR, and a pass there is not read as a contribution. Fraction ½ kept as a proposed value, the human lead's to change |
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
| F19 scorecard wording | FIXED | E3 |
