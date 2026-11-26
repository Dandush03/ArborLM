# P10-I-S2 Part T and P10-I-S2-D0: the human lead's merge approval and the external review pasted with it

Recorded by the lead (arbor-lead, Claude Fable 5.2) on 2026-11-25. This file quotes; it does not interpret beyond the section marked as the lead's.

## What was done on these words

- Part T (pull request 28) merged into main by signed merge commit `decb90a5`.
- D0 (pull request 29) merged into main by signed merge commit `ef8d5fac`. GitHub could not retarget the stacked pull request to main once main held its commits, so it was closed with a note rather than shown as merged.
- No registered label, threshold or record was changed by the merges. Part T stays a registered negative (MILESTONE NOT ESTABLISHED). D0 stays exploratory with no label.

## The lead's reading of the message (the lead's, not the human lead's)

- "I reviewed the PRs and aprobé the merge and close off both" is read as the human lead's approval to merge both pull requests and close both studies. It is not read as approval of any new study, of the learned-composition proposal in the pasted text, or of the open review items listed in the outcome records (they stay listed).
- "thi is astra though" is read as: the text below the first line is Astra's review, pasted by the human lead. It was received after both outcomes were recorded and both recomputations had finished. Records written before it say `Astra review: NOT_PERFORMED`; they were true when written and are not edited. From this date an Astra review of the D0 outcome (pull request 29) exists on record here. Whether it counts as Astra validation under AGENTS.md is the human lead's to say; the lead does not claim it.
- Two figures in the pasted text were not checked by the lead against the records before this file was written: the "required 0.03 maximum" on forgetting, and M-ii retention ratios "around 0.97-1.03". The pasted text's statement that neither pull request had merged describes the time of its writing.
- The proposed next step (learned, input-dependent composition of capability banks, compared with unconditional addition, per-bank isolation, a dictionary and matched LoRA adapters, without oracle capability identities) is a proposal. Nothing is specified, approved or implemented.

## The human lead's message, verbatim (2026-11-25)

````text
I reviewed the PRs and aprobé the merge and close off both 

thi is astra though 
Worked for 47s

### ArborLM PR #29 — D0 Interference Diagnosis

[View PR #29 on GitHub](https://github.com/Dandush03/ArborLM/pull/29?utm_source=chatgpt.com)

Mixed result

Open draft · Not merged · Exploratory analysis

This PR changes my assessment of our proposed solution. The experiment suggests that isolating memory banks at inference time would not, by itself, solve the forgetting observed in PR #28.

That's important because it challenges the hypothesis I suggested: that new memory slots displacing old ones might be the primary cause.

The good news is that we've narrowed the problem without another expensive training run.

### What D0 actually found

PR #29 compares different ways of reading the same frozen memory checkpoints from the two-teacher experiment.

| Finding                             | Result                                        |
| ----------------------------------- | --------------------------------------------- |
| Cross-stage top-8 competition       | Not supported as the dominant cause           |
| New stage's learned values          | Substantial contribution to the observed loss |
| Separate top-8 retrieval per bank   | Did not restore retention                     |
| Protecting stage A's read           | Recovered some performance, but not enough    |
| Student's use of both memory stages | Teacher B still benefited from stage A's rows |

The headline attribution is MIXED, meaning the evidence does not support a single dominant mechanism under the study's predefined criteria.

This is a diagnosis of already-trained memory, not a new training experiment. It cannot tell us whether memory banks trained separately from the beginning would behave differently.

### The most important numbers

Observed forgetting

### 0.056–0.086

Loss in normalized chrF score across six cells

Protected read forgetting

### 0.043–0.057

Better, but above the required 0.03 maximum

Two findings stand out.

First, the trained values of B matter more than we initially expected. Their contribution explains a substantial part of the measured first-capability loss. Softmax renormalization actually offsets some of the loss in all six cells.

Second, teacher B is using teacher A's memory. Reading B's memory stage alone reduces its score by 0.075–0.131 compared with the original combined read.

That second result is particularly relevant to your vision. It suggests these trained representations are interacting rather than functioning as entirely independent modules. However, the interaction isn't yet producing reliable capability retention.

Sources: [D0 outcome](https://github.com/Dandush03/ArborLM/blob/main/results/p10is2d0-run-20261124/OUTCOME.md?utm_source=chatgpt.com) and [PR #29](https://github.com/Dandush03/ArborLM/pull/29?utm_source=chatgpt.com).

### How I would adjust our next architecture

I wouldn't abandon capability banks. I would change how they contribute to the model.

Instead of always adding both banks' outputs, explore a learned, input-dependent composition mechanism:

h'=h+\\alpha_A(x)M_A(x)+\\alpha_B(x)M_B(x)

Where:

* and are trainable capability-memory modules.

* and determine each bank's contribution from the model's own hidden states.

* Both banks can contribute when their knowledge is complementary.

* Previously learned capabilities are protected through retention constraints.

This is a research proposal, not something D0 has validated.

The distinction is important: we don't want two disconnected experts forever. We want a system capable of selectively using, combining, and eventually consolidating their knowledge.

For the next experiment, I would compare learned composition against unconditional addition, per-bank isolation, a dictionary and matched LoRA adapters. The comparison must include genuinely held-out tasks, and the learned router must not receive oracle capability identities.

### PR quality and merge decision

The audit is encouraging:

* 120,000 decoded sequences matched between implementation and auditor.

* All 702 derived numerical readings agreed within approximately .

* The Part T source records remained unchanged.

* The run consumed 7.714 of its approved 8 worker-hours.

* The PR reports 62 passing D0 tests.

See [Independent audit](https://github.com/Dandush03/ArborLM/blob/main/results/p10is2d0-run-20261124/audit/AUDIT_P10IS2D0_2.md?utm_source=chatgpt.com).

However, I'd hold the merge pending your review, for three reasons.

The study was designed after observing the original failure, so it's exploratory rather than confirmatory. The specification had no third independent review and the implementation had no pre-run audit. Also, after the numerical passes completed, a reporting crash required a limited code correction and a separate finalization step; the auditor considers it technically sound, but the authorization question remains for you.

As of my check, PR #29 is a draft targeting PR #28's branch, and neither PR has merged. PR #29 also has no submitted GitHub review or completed check run.

I would preserve this outcome exactly as reported, without turning it into an architectural success claim.

### My recommended next move

D1 should now investigate learned, capability-dependent composition—not merely isolated retrieval.

I would proceed only after a small, preregistered study demonstrates that the proposed mechanism preserves A while acquiring B, and doesn't simply exploit the oracle-provided task identity.

One additional clue deserves attention: the earlier M-ii replay/consolidation arm reportedly achieved retention ratios around 0.97–1.03, although its overall result was intermediate and not a validated success. I would examine whether replay contributes something that bank isolation alone cannot.

### My conclusion

PR #29 is scientifically valuable because it eliminates an overly simple explanation.

We can no longer assume that freezing A and fixing its top-k retrieval will preserve its capabilities.

Instead, the evidence points toward learning how new memory should interact with established knowledge, while protecting earlier capabilities and still allowing useful cross-bank collaboration.

That's a harder problem, but it is much closer to your original goal: one model that learns from multiple masters, combines their capabilities, and eventually consolidates what it has learned.
````
