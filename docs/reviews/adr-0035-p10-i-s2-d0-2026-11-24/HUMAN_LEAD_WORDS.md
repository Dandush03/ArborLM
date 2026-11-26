# ADR-0035 (P10-I-S2-D0) — the human lead's words

Recorded by the lead (Claude Fable 5.2) from the chat session of 2026-11-24 (Panama time). `Astra review: NOT_PERFORMED`.

## 1. The message that endorsed the direction

The human lead's message, verbatim and whole, extracted mechanically from the session transcript. Its first line, "I agree with gpt", is his own; everything after it is an analysis written by another assistant that he pasted. The pasted text is recorded as data: it is not his wording, and nothing in it is an approval of any run.

````text
I agree with gpt


Worked for 51s

Yes. And after examining PR #28 alongside the earlier ArborLM experiments, I have a more specific idea of how we might make it work.

I think our next breakthrough, if there is one, will come from separating three things we currently mix together: storing knowledge, acquiring capabilities, and deciding which knowledge to use.

More importantly, I found a concrete mechanism in our code that could explain part of the forgetting problem.

### 1\. The first thing I would fix: new memories can interfere with frozen memories

In PR #28, when we teach the second capability, the implementation does correctly freeze the first memory stage's keys, values and gate.

However, look at what happens during retrieval.

The code concatenates all memory keys and selects the global top eight:

```python
keys = torch.cat(list(self.keys), dim=0)
values = torch.cat(list(self.values), dim=0)

scores = query @ normalized_keys.T
selected = top_8(scores)

weights = softmax(selected_scores)
output = sum(weights * gates * values)
```

Source: [SparseStore.read implementation](https://github.com/Dandush03/ArborLM/blob/f6dff34d201fb02f3ff77e5a33c17400a686f286/studies/p10s2/memory.py?utm_source=chatgpt.com).

That creates a potentially serious problem.

Illustration: retrieval before and after adding teacher B

Before B

A

A

A

A

A

A

A

A

8 slots from A

After B

A

B

A

B

B

A

A

B

Only 4 slots from A

Hypothetical selection pattern illustrating interference, not measured PR #28 slot counts.

Even though A's parameters never changed, B's new keys can displace A's keys from the top eight. They can also change the softmax weights assigned to A.

There's an even subtler possibility: a newly appended stage starts with a gate of zero, but its keys still participate in top-8 selection and softmax normalization. So it can potentially change A's output before B has learned anything useful.

This is a direct consequence of the code, although we haven't established how much of PR #28's observed forgetting it explains.

### The cheapest experiment I'd run next

Compare the same A queries against:

* A alone.

* A plus freshly initialized B, with B's gate still zero.

* A plus trained B.

* A plus trained B, but with retrieval restricted to A.

* A plus trained B, with separate top-k retrieval per memory bank.

Measure both the change in outputs and the displacement of previously selected A slots.

If A's performance is restored by isolating its retrieval, we've found a specific interference mechanism. That wouldn't yet prove multi-teacher learning, but it would tell us precisely what to redesign.

I would do this using existing frozen checkpoints before approving another large training run.

### 2\. Change from one shared memory pool to independently addressable capability banks

My preferred next architecture would look like this:

Pretrained backbone

Shared language and reasoning representation

Learned capability router

Selects banks from neural states, not supplied task identities

Expert A

Frozen skills + memory

Expert B

New skills + memory

Expert N

Expandable

Trainable composition layer

Combines selected expert contributions where useful

Model output + independent evaluation

Proposed research architecture. Not a validated ArborLM result.

Each capability bank would have its own trainable retrieval keys, values, and potentially a small adapter for skills that cannot be represented as factual associations.

The key difference is that adding B would not automatically modify A's retrieval distribution.

A learned router could activate A, B, both, or neither. But we need to train and test that router independently: passing an oracle task identifier at inference time would make retention much easier without proving that the model can select the correct capability itself.

There is precedent for this general strategy. Progressive Neural Networks preserves earlier neural modules while adding new ones with connections that can reuse previous features. It demonstrates why modular expansion is a credible direction, although memory and computation growth remain challenges. arxiv.org

### 3\. Stop expecting factual memory alone to teach reasoning

I think PR #28 also reveals a second architectural problem.

We taught short-vocabulary translation, and a conventional learned word table outperformed the neural-memory approach.

That tells us that for this particular task, much of the useful information could be captured by a straightforward lookup mechanism.

We must distinguish two different types of learning:

| Knowledge acquisition                | Capability acquisition                                                  |
| ------------------------------------ | ----------------------------------------------------------------------- |
| Memorize a new fact or association   | Learn a reusable way to solve problems                                  |
| A key/value store may be sufficient  | Often requires changing computation or behavior                         |
| Can be evaluated with factual recall | Requires unseen problems and task families                              |
| Naturally suited to external memory  | May benefit from adapters, experts, distillation, or learned algorithms |

For example, memorizing a collection of mathematical answers is not the same as learning to solve a new mathematical problem.

So I would develop a hybrid capability bank: trainable external memory for persistent associations, plus a small trainable neural adapter or expert for procedural capabilities.

Both would be attached to the same backbone.

This is consistent with Meta's Memory Layers at Scale, where sparse memory complements dense computation rather than replacing all of it. proceedings.mlr.press

### 4\. Introduce protected acquisition and consolidation

Once two independent banks work, the next challenge is genuine capability composition.

Here I'd try a two-stage learning process.

Acquisition stage: Teach a new bank using the new teacher's examples and verified feedback. Keep earlier banks immutable. Compare the newly acquired capability with LoRA, retrieval, a dictionary and the teacher itself.

Consolidation stage: Train a small shared composition mechanism using examples requiring both capabilities, while also replaying earlier tasks and preserving the previous model's outputs through distillation.

A candidate training objective might combine:

L =
L_{\\text{new}}
+\\lambda L_{\\text{replay}}
+\\mu L_{\\text{retention}}
+\\nu L_{\\text{composition}}

These are proposed terms, not a proven loss function. Their weights and effects would need controlled ablations.

The consolidation process should only be promoted if it preserves the old capabilities while acquiring the new ones. If it fails, we retain the original frozen banks and reject the candidate.

That gives us a path toward adding capabilities without making every learning stage an irreversible modification.

It also creates a foundation for your eventual self-improvement objective.

### 5\. The experiments I'd prioritize before buying more hardware

I would structure the next scientific work around these gates:

| Gate                        | Proposed experiment                                                                                        | What would justify proceeding                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| D0 — Interference diagnosis | Use PR #28 checkpoints to measure top-k displacement, old attention mass, and output changes as B is added | Identify which mechanisms explain retention loss                                              |
| D1 — Bank isolation         | Train the same two lexical capabilities with independently retrieved banks                                 | Retention improves without losing B acquisition; compare against E-table and separate modules |
| D2 — Learned routing        | Remove oracle task identity and train a router from model states                                           | Correct activation, low false-routing rate, retained A and B capabilities                     |
| D3 — Non-lookup skills      | Train two complementary procedural capabilities on held-out task families                                  | Both capabilities generalize and compete with matched adapters                                |
| D4 — Composition            | Train a controlled A+B composition mechanism                                                               | Solve registered problems that individual teachers and routing baselines cannot               |
| D5 — Physical SSD           | Move proven memory banks to SSD-backed storage                                                             | Equivalent capability and measurable storage economics                                        |

The specific pass/fail margins should be frozen before each registered experiment. These are proposed stages, not authorization to run them.

D0 should require very little new computation. D1 deserves a small preregistered training budget only after D0 is understood. Later gates should be conditional rather than launching another large parallel study immediately.

### 6\. How this leads to your four original goals

Learn from multiple masters without losing capabilities

Immutable earlier banks, controlled addition of new banks, independent retrieval, protected consolidation and measured retention.

Excel across domains

Combine factual memory with trainable procedural experts. Eventually benchmark the complete pretrained student against Qwen, GLM and strong conventional adaptations across multiple domains.

Self-heal and self-improve

Let the model propose better retrieval policies, practice tasks and code changes. Independently verify improvements in isolated environments, then promote or roll back immutable versions. Don't permit an unverified self-modifying runtime.

Use SSD for learned knowledge

Persist memory banks, keys, values and eligible expert parameters on SSD. Keep compact routing indexes and hot working sets in RAM, with batched retrieval and prefetching. Measure actual SSD latency and traffic; never assume it will be faster or cheaper overall.

The architecture also fits ArborML Lab's existing direction: Rust-first runtime, modular components, 3D visualization, immutable artifacts, local tests and independently approved promotions.

We should not let engineering changes alter the frozen PR #28 results. The redesign must be a new research line with its own preregistration.

### My recommendation to Fable

I would make D0 the immediate next scientific task, while preserving the established model-level roadmap in ADR-0032.

The instruction would be:

> Before proposing another major training experiment, determine how much of P10-I-S2 Part T's retention loss is caused by cross-stage top-k competition, softmax renormalization, and newly appended memory values.Use existing frozen checkpoints. Do not retrain or modify the registered outcome.Compare the original global top-8 retrieval with stage-isolated retrieval and a zero-gate appended-stage control. Quantify which changes restore prior capability and which do not.Then propose a minimal, fairly controlled bank-isolation experiment. Compare it against the existing E-table, LoRA and separate-module baselines.Do not claim multi-teacher success from preservation by construction. The new system must acquire both capabilities, generalize, and ultimately learn to select and combine them without oracle task identity.Keep computation bounded, delegate implementation and independent audit separately, and request approval before launching new registered training.

### My overall confidence

I'm more confident that we can build an architecture that retains separately acquired capabilities than I am that it will learn genuinely new, compositional reasoning capabilities from multiple teachers.

Retention through modular separation is a tractable engineering and research direction. Genuine knowledge transfer and capability composition are much harder, and the current results do not establish them.

I'm also not confident yet that SSD storage will provide an end-to-end efficiency advantage. That must be measured after we have something useful to store.

But PR #28 provides an unusually useful starting point: we have a concrete failure, frozen checkpoints, meaningful baselines and reproducible evaluation.

The most promising next experiment isn't about adding more memory. It's about ensuring that adding knowledge B doesn't change how knowledge A is retrieved—and then testing whether A and B can actually work together.

That's the direction I would pursue before spending another 150 hours of compute.

````

## 2. The message that delegated the approval decision

Later the same evening, after the lead said a draft specification for the diagnostic would be brought to him for approval and that nothing would run before then, verbatim:

> I'm giving you the say to approve this night, going to sleep. I'll review tomorrow morning

## 3. The lead's readings, for his review

- The first message endorses the direction of the pasted analysis's "recommendation to Fable": diagnose Part T's retention loss on existing frozen checkpoints before proposing another training experiment.
- The second delegates to the lead, for the night of 2026-11-24, the decision to approve the D0 specification. It covers no new training, no change to any registered outcome, and nothing beyond D0.
