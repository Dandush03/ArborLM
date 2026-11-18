# P10-I — the human lead's delegation of 2026-11-18 (UTC)

**What this is.** A record of an instruction by the human lead and of how the lead (Claude Fable 5.2) reads it. It changes no result, threshold, seed or outcome of any completed study. `Astra review: NOT_PERFORMED`.

## 1. The instruction, verbatim

After the measuring rehearsal of P10-I-R was reported and hour caps were proposed, the human lead wrote:

> understood, so 2 hours to see results? once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-* so we can discard what's not working and redesign our weakest point so we can achive the main idea? I still think there is ground to our main idea after what we saw with the tree but we need to optimize the search maybe think of it as a tree of weights and finding another angle to tackle it
>
> because the current stream model is flawed and we need to find a proper way to enhance memory with ssd without loosing speed nor accuracy and must importantly we need to figure out the self learn path

## 2. How the lead reads it

The human lead delegates to the lead, for the P10-I programme:

1. **Acceptance of outcomes.** Each registered outcome is recorded as the frozen rules compute it and is accepted by the lead without waiting. "Accept" means: record the registered labels unchanged, with an independent recomputation by the `arbor-auditor` subagent beside them and every finding disclosed. It never means choosing between readings after the data is seen, and it is not a success claim.
2. **The decisions that gate each study**, taken at the options the drafts recommend unless an independent review says otherwise: approval for implementation and rehearsal, the hour caps (by each ADR's own rule from its rehearsal), and the decision to run after the rehearsal record and the implementation audit are in.
3. **Continuing from one study to the next** until the P10-I studies that can be entered have a registered outcome.

## 3. What the lead does not take from it

- **No relaxation.** Thresholds fixed before observation stay fixed. A study that fails, or that cannot be evaluated, is recorded as such. No seed selection.
- **No skipped safeguards.** Every study still gets its independent specification review, implementation audit, rehearsal against its frozen plan and independent recomputation. A draft judged NOT READY is revised before it is approved under this delegation.
- **The conditional studies.** P10-I-S4 (quality against cost) and P10-I-S5 (physical SSD) are entered only if their written entry criteria are met by registered outcomes. The lead does not waive an entry criterion. The SSD write budget, anything needing administrator access, and any package outside the lock still go to the human lead.
- **Outside the delegation, unchanged:** merges to `main`, publication, pushing weights, paid services, a new redesign study after P10-I, and any change to a completed study. Downloads stay within the 50 GB delegation of 2026-11-17.
- **The human lead can withdraw or narrow this at any time**, and any result is reported as it arrives with what it means.

## 4. Two things the lead told the human lead in reply

- **Scale.** "2 hours" holds for the first results of P10-I-R only (about four hours to its main outcome, counting the second rehearsal, the freeze and the recomputation). The whole of P10-I is of the order of 100 to 250 charged hours on the human lead's working computer by the drafts' own estimates (addressing 15–55, capacity about 26 with an unbounded conditional block, teacher transfer 20–100, longer training 26–48), plus implementation, audits and rehearsals for each. That is one to three weeks of running, not hours.
- **Expectation.** Nothing in the records makes a positive outcome likely. The purpose of concluding P10-I is the one the human lead states: to find what does not work and where the weakest point is.

## 5. Direction noted for the redesign after P10-I (not a specification)

The human lead's view, recorded for the redesign: there is ground in the main idea after what the tree showed; the search needs to be optimised, possibly by treating the store as a tree of weights and approaching it from another angle; memory must be extended onto SSD without losing speed or accuracy; and, most important, the path by which the system learns by itself has to be worked out. "The current stream model is flawed" is recorded as written; the lead has asked what it refers to.

## 6. Addition: 24 hours, including merges and pushes (2026-11-18 UTC)

The human lead then wrote: "I mean 10 hours" (the hour cap of P10-I-R, set at 10 charged hours in total) and, a little later:

> I will allow you to drive it for the next 24hours including autoapprove merge and pushes
>
> do you need some special grant for this? because I want to allow you to move faster in order to read the result faster of P10-I so we know how to move foward

**How the lead reads it.** For 24 hours from this message (until about 2026-11-19 04:00 UTC) the delegation of section 2 also covers pushes and merges to `main` of P10-I work, without asking. The lead applies it this way:

- A merge to `main` happens only after the full local checks pass on the commit being merged (lint, type check, all tests, the smoke run), with the GitHub run skipped as the human lead asked on 2026-11-17, and the counts stated in the pull request.
- A study's records are merged after its outcome is recorded and independently recomputed, not before. Specifications and code may be merged earlier when a later study needs them on `main`.
- Nothing is committed or written inside a study's tree while one of its registered stages is running.
- Still outside the delegation: publication, pushing weights, paid services, packages outside the lock, the SSD write budget, administrator access, and any change to a completed study. No threshold is relaxed and no safeguard is skipped.
- After the 24 hours, merges to `main` go back to the human lead unless the grant is renewed.
