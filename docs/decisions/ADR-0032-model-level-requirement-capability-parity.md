# ADR-0032 — Model-level requirement: capability parity is mandatory; roadmap, acceptance criteria and proposed tests

**Status: DRAFT. Part A records the human lead's requirement as he stated it on 2026-11-20; it is his and needs no further approval. Parts B to E are the lead's (Claude's) proposal and are NOT APPROVED: no criterion, margin, reference set or test in them binds anything until the human lead approves it. Nothing in this document authorises implementation, downloads, training or execution.**

- Date: 2026-11-20. Drafted by the scientific lead (Claude Fable 5.2) in the main session. Not yet independently reviewed. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result. It changes no earlier study: P1 to P10-I, their thresholds, labels, outcome records and rulings stand exactly as recorded. P10-I-S6's registered outcome is and remains **CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)**.
- No literature check has been made for this draft. One is required before any Part D test is specified (section 9).

> **For the human lead.**
> - **What this is.** Your requirement written down (Part A), then my proposal for what it implies: how model-level acceptance would be judged (Part C) and which new preregistered tests could get there (Part D).
> - **What it is not.** Not a result, not a specification, not approval of anything. Each test in Part D would need its own specification and your approval.
> - **Where the programme stands against it.** Nothing measured so far bears on capability parity. Every result to date uses a 27,392-parameter byte-level backbone trained in this repository and one measure, predictive loss. No pretrained model has been attached to the memory, and no teacher has taught it a capability at model scale.
> - **Decisions that are yours (Part E):** what the reference models are; the non-inferiority margin; the capability domains; whether to add a scorecard row; which test, if any, to specify first.

## Part A — The requirement (the human lead, 2026-11-20, quoted)

"ArborLM must be equally capable or more capable than the conventional models it aims to replace. Capability parity is a minimum requirement, not an optional objective. Our goal is not to create a cheaper but weaker model. Our goal is to maintain or improve the capabilities of existing models while changing the economics of learning, memory and inference."

1. "Capability parity is mandatory. ArborLM must match or exceed the relevant baseline models on properly defined, independent evaluations. Cost or storage improvements cannot compensate for a failure to meet that requirement."
2. "Capability superiority is desirable. Learning from multiple teachers should be investigated as a way to achieve capabilities that neither teacher provides independently. We must demonstrate this, not assume that combining teachers produces a smarter model."
3. "Continual learning is fundamental. Acquiring a new capability must not substantially degrade previously acquired capabilities. Sequential acquisition and retention need direct measurement."
4. "Efficiency and scalability are additional advantages. Once competitive capability is demonstrated, we should evaluate whether ArborLM offers lower training or inference costs, expandable persistent memory, sparse computation and SSD-backed operation."

"Importantly, predictive NLL on the current small frozen-backbone experiments is only one scientific measurement. It does not establish capability parity with Qwen, GLM or any other pretrained LLM. We must eventually evaluate reasoning, coding, language understanding, generalization, knowledge retention and other relevant capabilities against actual pretrained alternatives."

On P10-I-S6: "Even if flat memory eventually converges to the same NLL as the dense adapter, that would be an encouraging intermediate result, not validation of the complete ArborLM hypothesis. S6 remains CONVERGENCE NOT REACHED, and its original registered outcome must not change."

"Our ultimate success criterion should be: ArborLM capability ≥ reference model capability, with additional measurable advantages in knowledge acquisition, retention, scalability or efficiency. When comparing against multiple teachers, we must explicitly evaluate capability coverage, interference and composition, rather than relying on an average score that hides regressions."

"Do not modify frozen experiments, retroactively change outcomes or assume any currently unproven capability. Propose new preregistered tests for my approval."

## Part B — What follows for how results are read (proposal)

### 1. Two levels of evidence, never mixed

- **Component evidence**: a property of a memory mechanism on a small controlled system (predictive loss, addressing, capacity, dependence controls, storage and read cost). Everything in P1 to P10-I is of this kind.
- **Model-level evidence**: a capability of a complete system (a pretrained model with the ArborLM memory attached) measured on independent task evaluations against actual pretrained alternatives. None exists yet.

Rule proposed: a component result is never reported as progress toward parity without the sentence that parity is untested. Component studies remain useful for one purpose: deciding which memory design is worth the cost of a model-level test, and diagnosing a model-level failure.

### 2. The order of the requirements is lexical

Capability parity is a gate. Retention is part of that gate. Superiority and efficiency are read only behind it:

1. **Parity** (mandatory) — Part C section 5.
2. **Retention under sequential acquisition** (mandatory) — section 6.
3. **Superiority from several teachers** (desirable; demonstrated or not claimed) — section 7.
4. **Efficiency and scalability** (additional) — section 8. If the gate fails, efficiency figures are still recorded, labelled **NOT A COMPENSATING RESULT**, and enter no conclusion.

### 3. What the current studies can and cannot contribute

| Study | What it can inform | What it cannot establish |
|---|---|---|
| P10-I-S6 (CONVERGENCE NOT REACHED) | Whether the flat memory is a reasonable form to carry into a model-level test | Parity of any kind; even equal loss at convergence would be an intermediate component result |
| P10-I-S0 (addressing licensed up to one fact per slot) | The load at which a store may be operated | That a real model can use the store |
| P10-I-S2 Part T (not yet run) | Whether sequential two-teacher transfer shows retention and composition on closed-vocabulary lexical translation, with oracle addresses | Retention or composition of capabilities such as reasoning or coding; anything about Qwen or GLM as capable models |
| P10-I-S1, P10-I-S5, P10-II-S5 | Capacity and storage cost | Anything about capability; under section 2 they are read only behind the gate |

## Part C — Proposed model-level acceptance criteria

### 4. Definitions to be fixed before any observation

- **System under test (S).** A named pretrained student with the ArborLM memory attached, after a registered teaching procedure. The student alone is written S₀.
- **Reference set.** Two tiers are proposed, and both are needed for the final claim:
  - **Tier 1, conventional alternatives at matched resources.** The same student S₀ improved by conventional means from the same teachers and the same teaching data: distillation into a low-rank adapter, full fine-tuning where feasible, and retrieval over the same data. This isolates what the ArborLM memory contributes.
  - **Tier 2, the pretrained models themselves.** Each teacher, and S₀. This is the comparison your criterion names.
- **Capability domains.** At least: reasoning, coding (scored by executing the code), language understanding, generalisation (tasks and distributions not present in teaching), knowledge retention. Each domain is one or more named evaluations at a fixed version, plus a privately generated set where one can be built.
- **Independence of evaluation.** No evaluation item, and no near-duplicate of one, appears in the teaching data; this is checked by code and recorded. Evaluation code is not written by whoever wrote the teaching code. Scoring is by execution or exact rule where possible; any model-graded score is validated against human or rule labels first. What cannot be controlled is stated: whether the pretrained models saw a public benchmark during their own training is unknown, which is one reason for private sets.
- **Margin.** "≥" cannot be tested on a finite sample without a margin. Proposed form: for each domain a non-inferiority margin δ fixed in advance from the measured run-to-run noise of the references (Part D, test M0), never from S's scores. δ is the human lead's to set.

### 5. Parity (mandatory)

**S is at parity with a reference R only if, in every domain separately, the one-sided confidence bound of (score of S − score of R) lies above −δ.** The verdict is the conjunction over domains. No average over domains is computed for the verdict; one failing domain is a failed parity.

Also required, each printed per domain:

- **Do no harm.** S against S₀: attaching and teaching the memory must not lower any domain the student already had. This is the cheapest necessary condition and the first to test.
- **Item-level regressions.** The number of items R answers correctly that S does not, beside the number gained. Equal totals with many regressions are reported as such.

Labels proposed: PARITY (TIER 1), PARITY (TIER 2: named reference), NOT AT PARITY (named domains), NOT EVALUABLE (reason). A system at parity with Tier 1 only is described as "matches conventional adaptation of the same student", never as matching the teachers.

### 6. Retention under sequential acquisition (mandatory)

Capabilities are taught one after another, in at least two orders. After each step every earlier capability is measured again. **Retention holds if no earlier capability falls by more than a margin fixed in advance**, per capability, against its value right after it was acquired and against a system taught that capability alone. Baselines taught the same sequence: the low-rank adapter (the expected forgetting case), the adapter with replay, retrieval. A retention figure is read only where the capability was acquired in the first place (a capability never learned cannot be forgotten).

### 7. Several teachers: coverage, interference, composition (superiority is desirable)

Reported as a table of domains by systems, never as one number:

- **Coverage.** For each teacher and each domain where that teacher is ahead of S₀: how much of the gap S closes, and whether S is non-inferior to that teacher there.
- **Interference.** For each domain: S taught by both teachers against S taught by the stronger teacher alone. A loss beyond the margin is INTERFERENCE (named domain).
- **Composition.** Items that neither teacher solves alone, built so that solving them needs what each teacher is better at; and the item-level union (items at least one teacher solves) as the ceiling for combining without creating.
- **Superiority.** Claimed only if S is at parity with both teachers in every domain **and** exceeds the better teacher in at least one domain named in advance, beyond the margin. Controls that must be beaten or matched and are always printed: the better single teacher per domain, and a router that sends each item to the teacher better on that domain. If S only matches the router, the result is COMBINES (NO GAIN BEYOND ROUTING), not superiority.
- **Precondition.** The teachers must be shown to differ (each ahead somewhere, on independent evaluations). If they do not, the question is NOT EVALUABLE.

### 8. Efficiency and scalability (behind the gate)

Measured, never logical: wall time and energy or hardware-hours to acquire a capability; latency and memory at inference; bytes stored per capability; behaviour as the memory grows; reads from SSD. Each against the Tier 1 alternative reaching the same capability. Reported with the parity verdict beside every figure.

## Part D — Proposed preregistered tests (none approved; each needs its own specification)

| Test | Question | Needs | Why this order |
|---|---|---|---|
| **M0 — references and evaluation harness** | What do S₀ and each teacher score per domain, how noisy are the scores, and where do the teachers differ? | Licence check of exact model versions; model downloads; a sandbox for running generated code; no ArborLM code | Fixes margins and the domain list before any ArborLM score exists; settles the precondition of section 7; costs no research risk |
| **M1 — do no harm on a real student** | With the memory attached to S₀ (inert, then after teaching one narrow capability), is every domain unchanged within the margin? | M0; a way to attach the memory to a token-level pretrained model, which does not exist yet | First model-level contact; a failure here stops everything after it cheaply |
| **M2 — one teacher, one capability** | In a domain where a teacher is ahead of S₀, does S reach parity with the Tier 1 alternatives, and how much of the gap to the teacher closes? | M1 | The smallest test of point 1 of the requirement |
| **M3 — sequential retention** | Section 6, with two then three capabilities | M2 passing for each capability | Point 3 of the requirement, measured directly |
| **M4 — two teachers** | Section 7 | M0 showing the teachers differ; M2 for each teacher | Point 2 of the requirement |
| **M5 — model-level acceptance** | Sections 5 to 7 on the full domain list against both tiers | M2 to M4 | The criterion itself |
| **M6 — efficiency and scale** | Section 8 | M5 at parity | Point 4; read only behind the gate |

Each test registers its labels, margins, seeds, stopping rules and negative outcomes before any score is seen, as the P10-I studies did, and is run once.

### 9. Known open problems, stated now

- **The memory has never been attached to a pretrained token-level model.** Every mechanism result is on a byte-level backbone of 27,392 parameters. Whether any of it carries over is unknown, and M1 is where that is first tested.
- **A key-value memory may not carry capabilities that are not look-ups.** Storing and retrieving associations is what the mechanism has been shown to do at small scale. Reasoning and coding may need more than that. This is an open question the tests must be able to answer in the negative.
- **Parity of a small student plus memory with a larger teacher across every domain is a strong claim.** Tier 2 parity may fail while Tier 1 parity holds. That would be a real, limited result and must be reported as NOT AT PARITY with the teachers.
- **Scale and cost.** Model-level tests need pretrained models of several GB each and evaluations that take hours per system on this machine; some may not be feasible locally. Costs are estimated per test in its own specification.
- **Literature.** Distillation, model merging, continual-learning benchmarks and retrieval baselines have a large prior literature that this draft has not checked. The check comes before M0's specification and may change the baselines.

## Part E — Decisions that are the human lead's

1. **Reference set.** Are both tiers of section 4 required for the final claim, as proposed, or is parity with the teachers alone the criterion?
2. **Margin.** Accept a non-inferiority margin fixed from measured noise (section 4), and who sets its size.
3. **Domains.** The list in section 4; additions or removals.
4. **Scorecard.** Proposed: one new row, "Capability parity with reference models", starting score 0 (proposed by the lead; the score is yours), with the note that the other rows are component evidence and do not add up to it.
5. **First test.** Whether to have M0 specified now (it needs no ArborLM result and can be drafted while P10-I finishes), or to wait for P10-I-S2 Part T.
6. **Independent review** of this draft by the auditor before you decide.
