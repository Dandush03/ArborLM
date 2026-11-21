# ADR-0033 — M0: the reference models and the evaluation harness (first rung of the model-level ladder)

**Status: DRAFT (revision 2). NOTHING APPROVED. Draft 1 was reviewed once (`docs/reviews/adr-0033-m0-2026-11-20/REVIEW_1.md`: READY AFTER THE LISTED EDITS, two blocking findings). This revision applies that review and has not been reviewed again; the reviewer recommends a short confirmation review of B1, B2, R1, R3 and R4 before Decision 1. Nothing in this document authorises implementation, a download, a run or a decision.**

- Date: 2026-11-20 (Panama time). Draft 1 (commit `c89c1f2`) and revision 2 by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) on the scientific lead's brief. Review 1 by the `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`). The drafter read records only. It downloaded nothing, ran no model, ran no heavy computation and made no git write.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result. P1 to P10-I, their thresholds, labels, outcome records and rulings stand exactly as recorded. No existing file is edited.
- **What binds this specification.** The five rules of ADR-0032 revision 4, section E2, approved by the lead under the weekend delegation (`docs/reviews/adr-0032-model-level-2026-11-20/APPROVAL_OF_RULES.md`): the two levels of evidence; the margin rule; the power rule; the label structure of sections 5 and 6; the order of the M ladder. The human lead may overrule any of them on Monday 2026-11-23. Everything else in ADR-0032 is a proposal and is treated as one here.
- **Literature.** `docs/reviews/adr-0032-model-level-2026-11-20/LITERATURE_NOTE_1.md` ("note 1") is unreviewed. Its marks are kept: **[V]** a page fetched in that session and read through an automatic summariser; **[M] UNVERIFIED** from its author's memory; **[E]** an estimate. One mark is added here: **[D] UNVERIFIED**, from the drafter's or the reviewer's memory. **No number from note 1 has been re-read at its source.** Every one is re-read at the source before it is used (section 13, stage D0b); none is a fact of this specification until then.
- **[KNOWN].** Nothing about any candidate model has been measured in this project. No rule below was written after seeing a score. What could have shaped the design is note 1 only.

> **For the human lead.**
> - **What M0 is.** Groundwork with no ArborLM component in it. It measures the pretrained models themselves, the small student and the larger models it would be compared with, on evaluations built for the purpose. It contains no memory code and says nothing about ArborLM.
> - **What it can tell you.** How each model scores here, on this machine and software. Whether each teacher is ahead of the student, and where. Whether the two teachers differ item by item, which the two-teacher question needs. How many test items the parity gate needs for a margin of 2, 3 or 5 points, and whether any number of items is enough. Whether that gate is affordable on this machine.
> - **What it cannot tell you.** Anything about ArborLM. Whether parity is reachable. Anything about cost or efficiency of a memory. Anything about writing code: M0 measures code tracing only.
> - **Expectation, not a measurement.** The teachers will most likely be ahead of a small student almost everywhere. Whether the two teachers complement each other is open. The gate will most likely need several thousand sealed items per evaluation; at a 2-point margin some evaluations may be out of reach whatever the number of items (section 9.4). The final test (M5) may project to weeks of machine time.
> - **Cost.** About 41 GB (set B) or 43 GB (set A) of downloads in total after M0 (limit 50 GB; 1.50 GB already used, not 1.19: section 4.1). One to four days of machine time for the registered measurement, and about a third to two fifths as much again for rehearsals; all uncertain by a factor of about three until timed here (section 11).
> - **Yours alone, in the order the work waits for them (sections 16 and 17):**
>   1. **How the models are run (choice 8)**: a lockfile amendment, a separate pinned package file, or the models re-implemented in plain torch on the locked environment. No package is installed before this. Recommended to you: the third, with its cost stated in section 5.
>   2. **The model list**: which set, which model is the student S₀, the upper bounds on the student plus memory. Sets A and B are both workable; draft 1 recommended B, and after the review's corrections the drafter gives no recommendation between them (section 4.2).
>   3. **The domain list** and which evaluations may gate. Recommended: reasoning, mathematics, code tracing (output prediction), language understanding, factual knowledge. Code writing is then NOT MEASURED.
>   4. **G, the number of clusters per evaluation part**, before the generators are frozen. Proposed: at least 300.
>   5. **The margins δ_e**, per evaluation, **before stage R1**, that is before any model scores any item.
>   6. **Every number of the config** (section 14) before the freeze: alpha, power, the cap fraction, the floor and ceiling band, pool sizes, hour ceilings.
>   7. **A ruling on 7,030,741 bytes of WikiText-2** fetched on 2026-11-12, before the download ledger began: do they count against the 50 GB?
>   8. **Starting Docker (Colima)**, only if you want code writing measured by execution. Recommended: not in M0.
>   9. **Every model and dataset download**, the non-commercial licence of ANLI, and any model that needs repository code to load.
>   10. **Decision 2**: the registered measurement.
> - **What the lead may do under your weekend delegation, after the auditor's review, and nothing more:** approve this specification for the work that runs on the locked environment alone. That is stage I0-a (generators, solvers, scorers, analysis and their tests) and stage G-gen. The packages that would run the models (choice 8), every model and dataset (choices 1, 2 and 7) and every number of section 14 are yours. No package, model or dataset is fetched before your choice.

## 1. Question, registered outcomes and non-claims

**Question.** On one inference stack, one numeric precision and one fixed prompt and decoding rule, on development items only:

1. What does each reference model score on each evaluation?
2. On which evaluations is each teacher ahead of the candidate student S₀?
3. Do the two teachers differ item by item, so that their union is above the better one?
4. How often do two systems disagree on an item, and how many sealed items does the power rule therefore require for margins of 0.02, 0.03 and 0.05?
5. What does it cost in measured machine time, and is each reference runnable here?

M0 also fixes what later rungs inherit: the reference set, the prompts and decoding, the development pools, the sealed pools and their hashes.

**Registered outcomes.** Every one is negative or blocking. Each has an exact rule in section 10, fixed before any score exists. Where the opposite holds, the line printed is descriptive (EVALUABLE, TEACHER AHEAD, COMPLEMENTARY) and is a statement about the reference models on these items, nothing more.

| Outcome | Unit |
|---|---|
| REFERENCE NOT RUNNABLE LOCALLY (cause) | per reference |
| NOT EVALUABLE (FLOOR OR CEILING) | per reference and evaluation part; per evaluation part when no Tier 2 pair is left |
| TEACHER NOT AHEAD | per teacher and evaluation part; per domain when no teacher is ahead on any part |
| NO COMPLEMENTARITY | per evaluation part and candidate margin |
| NOT EVALUABLE (UNDERPOWERED) | per evaluation part and candidate margin |
| GATE NOT EVALUABLE LOCALLY (PROJECTED) | whole gate, per candidate margin |

**Non-claims, whatever the outcome.**

- Nothing about ArborLM. No memory code is imported, attached or run.
- No outcome is evidence for or against the ArborLM hypothesis. No outcome is reported as an achievement.
- Not a ranking of Qwen against GLM in general. Scores hold for these items, this stack, this precision, greedy decoding and these prompts. They are not comparable with published scores.
- Not a capability claim for any private set beyond what it measures; a generated set is a narrower construct than a human-written benchmark.
- Nothing about writing code. Code tracing is never called coding (section 6.8).
- Timing is a cost record on a shared machine. It is not a throughput claim about any model.
- Every model-level label of ADR-0032 (PARITY, NO HARM, RETENTION, the section 7 labels) is out of reach of M0. None is printed.

## 2. What is taken from ADR-0032, and how it is read

| ADR-0032 text | Reading used here |
|---|---|
| Section 4, "One system" | Section 7 below, for the references. S does not exist yet. |
| Section 4, Tier 2 (a), (b), (c) and the upper bounds | Section 4.3. |
| Section 4, margin rule and cap | M0 does **not** set δ_e. It reports the cap flag for each (reference, evaluation part) at each candidate margin. "Lower 95 % bound" is read as one-sided at 0.05. |
| Section 4, floor and ceiling | Rule of section 10.2. Read per (reference, evaluation part): a departure from the wording, listed in section 19. |
| Section 5, power rule | Section 9.4. M0 has no S, so the discordance is item (i) of the rule: the largest between S₀ and any Tier 2 reference. |
| Section 5, sealed pool | Section 8. Created at a registered maximum size and hashed at the freeze. Never scored in M0. |
| Section 7, complementarity precondition | Section 10.4. Section 7's labels are not approved; M0 prints the measurement and its rule only. |
| M0 row of the ladder | Sections 4 to 14. |

**Component-free.** M0 is neither component evidence nor model-level evidence about ArborLM (ADR-0032 section 1). It is a measurement of reference models. Its report carries the sentence: "M0 measured reference models only; capability parity of ArborLM is untested."

## 3. Scope and exclusions

In scope: the reference models of one set; development-split scoring; item-level disagreement; the union of the teachers; nuisance variations on a small subset; timing; development pools; sealed pools; the template-family partition that later defines the generalisation split.

Excluded, with the reason:

| Excluded | Reason; where it goes |
|---|---|
| Any ArborLM code, any training, any adapter | M0 is groundwork. M1a onward. |
| Tier 1 systems | They need a teaching procedure. M1.5 and M2. |
| Scoring of any sealed item | M5 stays the only reader (section 8). |
| Code writing; execution of model-written code (recommended option) | Needs a container; Docker (Colima) is stopped on this machine by the human lead's permission and starting it is his call (section 6.3). Code writing is NOT MEASURED. |
| Composition items of ADR-0032 section 7 | They need M0's own result first (section 19, row 2). A later supplement with its own approval. |
| Multilingual ability and instruction following | ADR-0032 E1 item 3 recommends multilingual ability. Not specified here because no evaluation for either was licence-checked: a departure (section 19, row 13), and his to add before the freeze. |
| Long context, calibration | No licence-checked evaluation is in note 1 for them. Not specified. His to add before the freeze, by an amendment and a review; never after. |
| Quantised or converted checkpoints, other stacks | One stack, one precision. No cross-check stack is specified in M0. |
| Thinking modes | Off for every model that has one (section 7). |

## 4. Models

### 4.1 Precondition: the cumulative download total (ADR-0032, Review 2 G12)

Limit: the standing delegation of 50 GB in total (50,000,000,000 bytes; `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` cites it; the ledger's own header still states the earlier 30 GB of 2026-11-15).

| Item | Bytes | Source |
|---|---|---|
| Ledger on `main` (`docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`) | 1,188,183,868 | read |
| **The same ledger on branch `claude/p10-i-s6-impl`, commit `aa41a62` (two WikiText-103 shards, not yet on `main`)** | **1,502,260,446** | read with `git show`; confirmed by Review 1 over every local and remote branch |
| **Total already downloaded, used here** | **1,502,260,446 (1.50 GB)** | the larger of the two |
| Not in any ledger: `data/wikitext2/`, fetched 2026-11-12, before the ledger began | 7,030,741 | Review 1, R10; **the human lead's ruling whether it counts (choice 14)** |

The ledger on `main` is behind by 314,076,578 bytes. Review 1 found one download ledger only, and one further local difference of 4,867 bytes that is a local record file, not a fetch.

**Gate at D0b.** `arbor-clerk` inventories every branch's ledger and the git-ignored `data/` directories. The inventory counts every fetch since 2026-11-15 against the 50 GB limit, and lists earlier fetches (WikiText-2, 7,030,741 bytes, 2026-11-12) separately with the human lead's ruling on whether they count. A fetch after 2026-11-15 with no row is an engineering stop. M0's first ledger row starts from the inventoried total.

**How files are fetched.** Weights are fetched by plain HTTPS resolve URLs at the pinned revision with resumable range requests, never through the hub's chunked (Xet) transfer, and the ledger counts transferred bytes. One ledger row per file is written before the fetch and completed after it.

Planned additions, decimal GB. Model sizes are note 1's [V] figures, summed by this drafter [E]; all are re-read from the repository listing at the pinned revision before any fetch.

| | Set B | Set A | Set C |
|---|---|---|---|
| Already downloaded | 1.50 | 1.50 | 1.50 |
| Models | 38.11 | 40.74 | 44.41 |
| Python packages (section 5) [E, from the 126,182,132-byte row of the same kind in the ledger] | 0.15 | 0.15 | 0.15 |
| Datasets, ceiling (note 1: "well under 1 GB together" [E]) | 1.00 | 1.00 | 1.00 |
| Sandbox image | 0 (recommended option) | 0 | 0 |
| **Cumulative total after M0** | **40.8** | **43.4** | **47.1** |
| If code execution is approved: image, ceiling 2.0 (size UNVERIFIED in note 1) | 42.8 | 45.4 | 49.1 |
| Left under the limit for every later rung | 9.2 (7.2) | 6.6 (4.6) | 2.9 (0.9) |

Rules. (1) The fetch code refuses any fetch that would take the cumulative total above 50,000,000,000 bytes. (2) M0's own ceiling is the planned cumulative total of the chosen set plus 1 GB; a plan above it is not started and returns to the human lead. (3) The cumulative count never goes down: deleting a file refunds nothing. **This is why no model is fetched before the human lead's model list: after one set is fetched, no second set fits.**

### 4.2 Candidate sets (from note 1, section 4; nothing re-read)

| Set | Student S₀ | Sibling | Qwen teacher | GLM teacher | Remarks from note 1 |
|---|---|---|---|---|---|
| B | `Qwen/Qwen2.5-0.5B-Instruct`, 494,032,768 parameters, 0.99 GB [V] | `Qwen/Qwen2.5-1.5B-Instruct`, 1,543,714,304, 3.09 GB [V] | `Qwen/Qwen2.5-7B-Instruct`, 7,615,616,512, 15.23 GB [V] | `zai-org/GLM-4-9B-0414`, 9,400,279,040, 18.80 GB [V] | Text only; no thinking mode; most mature tooling |
| A | `Qwen/Qwen3-0.6B`, 751,632,384, 1.50 GB [V] | `Qwen/Qwen3-1.7B`, 2,031,739,904, 4.06 GB [V] | `Qwen/Qwen3-8B`, 8,190,735,360, 16.38 GB [V] | the same | Text only; has a thinking mode [M] |
| C | `Qwen/Qwen3.5-0.8B`, 1.75 GB [V] | `Qwen/Qwen3.5-2B`, 4.55 GB [V] | `Qwen/Qwen3.5-9B`, 19.31 GB [V] | the same | Multimodal; thinking on by default on the 9B; cards require a library version from the main branch [V] |

Licence tags per note 1: the Qwen candidates Apache-2.0 (tag and card only; **the LICENSE files were not opened**); GLM-4-9B-0414 MIT (LICENSE file opened) [V]. The older GLM-4 9B and GLM edge models carry a custom licence with a naming clause [V, through a summariser] and are not candidates.

**Revisions and files.** Note 1 gives commit prefixes only (for example `7ae55760…` for the 0.5B student) [V]. They are pointers. At D0b each repository is pinned by its full 40-character commit and each file by the SHA-256 of its LFS metadata. The allowlist of files is: `.safetensors` weights, `model.safetensors.index.json`, `config.json`, `generation_config.json`, tokenizer files, `chat_template.jinja` and the LICENSE. No pickle file is loaded.

**Sets A and B, side by side.** Draft 1 recommended B. Review 1 (C1) corrected two of its four reasons, and one more falls with them:

| | Set B | Set A |
|---|---|---|
| Left under the limit after M0 | 9.2 GB | 6.6 GB |
| Thinking mode | None | Present; turned off by a documented template switch, so no extra cost; one more fixing to register and check ([D] UNVERIFIED, the reviewer's memory) |
| Library | Classes expected in the proposed pins ([D] UNVERIFIED) | The same expected ([D] UNVERIFIED, the reviewer's memory). Draft 1's claim that only B avoids a newer library was not established |
| Age of the Qwen models | About two years ([D], the reviewer) | About eighteen months ([D], the reviewer) |
| Age of the two teachers against each other | Qwen teacher older than the GLM teacher | Probably closer in age ([D] UNVERIFIED). Draft 1 said B's teachers were closest; that was not established either |

**No recommendation between A and B.** What would decide it is the human lead's judgement of which models ArborLM "aims to replace": A's are newer; B is simpler by one switch and leaves 2.6 GB more. Set C is not recommended: it needs a library version outside the pins, has multimodal checkpoints and leaves 2.9 GB. Figures below use set B as the worked example only; with set A the same rules apply to its models.

### 4.3 The reference set and the upper bounds on S (ADR-0032 section 4; Review 2 G2)

| Role | Worked example (set B) | Standing |
|---|---|---|
| S₀, the candidate student | `Qwen2.5-0.5B-Instruct` | Measured; not a parity reference except in role (c) below |
| Tier 2 (a), teachers | `Qwen2.5-7B-Instruct`; `GLM-4-9B-0414` | Parity references |
| Tier 2 (b), equal stored bytes | `Qwen2.5-1.5B-Instruct` | Parity reference |
| Tier 2 (c), nearest active compute | The S₀ checkpoint itself | "(c) = S₀, by NO HARM"; no further model, no further test |

**Upper bound on stored bytes (can be registered now).** S (student, memory, router, adapters, everything it needs at inference) may not exceed the byte size of the sibling's weight files at the pinned revision: about 3.09 GB in set B, 4.06 GB in set A [V], the exact number filled in at D0b from the listing. That allows the memory about 2.1 GB (set B) or 2.6 GB (set A) beyond the student [E]. Reference (b) is then the sibling: the largest model of the same release series at or under the bound.

**Upper bound on active compute (registered now as a count; its measurement on S is deferred to M1a).** S may read, per generated token, at most 1.25 times the number of parameters S₀ reads. The count is defined so: tied embeddings are counted once; the input embedding look-up is excluded; the output (language-model) head is included. The definition matters: for `Qwen2.5-0.5B` the embeddings are about 136 M of 494 M parameters ([D] UNVERIFIED, the reviewer's memory), so the choice moves the bound by about a quarter.

Under this bound, reference (c) is S₀: the sibling is 3.1 times S₀ by parameter count in set B and 2.7 times in set A [E from V]. Its parity test is the NO HARM test at the same margin, which adds no test to the conjunction. Every PARITY verdict names it as "(c) = S₀, by NO HARM". S₀ is a parity reference in this role only. The count is a rule for choosing a reference. It is a logical count and supports no efficiency statement. How S's reads are counted is specified in M1a, and S is shown to be under both bounds before it is scored.

**Why S₀ is the smaller model.** It leaves the sibling as the equal-bytes reference inside the download budget, and it is the cheapest to carry through M1 to M5. Against it: the smallest model is the farthest from the teachers. Option: S₀ = the sibling; then (b) needs a larger model, which does not fit the budget beside the rest. Not recommended.

**Can the memory be attached to it? (ADR-0032's M0 row.)** Not known. For `Qwen2.5-0.5B`: hidden width 896, vocabulary about 151 thousand, and an Apache-2.0 licence that permits modification ([D] UNVERIFIED, the reviewer's memory). Every earlier ArborLM mechanism ran at width 32 on bytes. M1a may find attachment infeasible; M0 does not test it.

**What is deferred.** Reference (b) rests on reading "the student's family" as the same release series. If the human lead reads it as every small Qwen model, a further candidate under the bound can be added before the freeze (with set B: `Qwen3-0.6B`, 1.50 GB [V], cumulative 42.3 GB). Under that broad reading "strongest" can only be settled by measuring in M0, before any score of S (Review 1, ruling 12). No larger reference can be fixed now.

**The set may not be reduced after M0** (ADR-0032 section 4). A reference found NOT RUNNABLE LOCALLY stays in the set; its comparisons are NOT EVALUABLE LOCALLY.

## 5. Inference stack

**Stack of record: PyTorch on MPS, the checkpoint's published half precision, unquantised, the same for every system.** This is where M1 would attach a memory with gradients. Platform of record: macOS arm64, Apple M5 Max, 18 cores, 48 GiB (read from the machine), `torch==2.8.0` as locked.

**Precision order, fixed now.** (1) bfloat16 on MPS. (2) If any model of the set fails the load gate in bfloat16 (an unsupported operator, a non-finite value), float16 on MPS for every system. If any model is then non-finite, every model it affects is REFERENCE NOT RUNNABLE LOCALLY (PRECISION), and the lead returns to the human lead before R1. (3) No further fallback: float32 does not fit a 9B model beside other work, and CPU is too slow. The precision is settled at the load gate, before any tuning score. CPU fallback for unsupported operators is off (`PYTORCH_ENABLE_MPS_FALLBACK` unset). Whether torch 2.8.0 runs these models in bfloat16 on MPS is not known [D] UNVERIFIED; Qwen-family activations overflowing in float16 is a known hazard ([D] UNVERIFIED, the reviewer's memory). The gate decides.

**Packages beyond the lock.** The locked environment has `torch` and `psutil` only. Loading these models with a library needs:

| Package | Proposed pin | Why |
|---|---|---|
| `transformers` | 4.57.1 | Model classes, chat templates, generation |
| `tokenizers` | 0.22.1 | Tokenizers |
| `safetensors` | 0.6.2 | Weight files |
| `huggingface-hub` | 0.35.3 | Imported by `transformers`; used offline only after D0b |
| `numpy` | 2.3.3 | Imported by `transformers`; bootstrap arithmetic |
| resolver dependencies (`regex`, `pyyaml`, `tqdm`, `requests` and theirs) | as resolved | — |

These five pins are versions already resolved and hashed for P10-S2. There they ran a one-off data-generation step only; P10-S2's registered path ran on the locked environment alone, with the model re-implemented in torch and checked for equivalence (ADR-0022 §14.2). In M0 they would run the registered measurement itself, which has no precedent in this repository. `jinja2`, which chat templates need, is expected in the lock as a dependency of `torch` [D] UNVERIFIED. Whether `transformers` 4.57.1 has built-in classes for every model of the chosen set is [D] UNVERIFIED and is gated at D0b before any weight is fetched. `accelerate` is not listed; if the load gate shows it is needed to hold peak memory, it is added before the freeze. `pyarrow` (dataset files) comes from the lock's existing `pilot` extra.

**The route is the human lead's (choice 8). The lead may not take it under the delegation** (Review 1, B2 and its ruling on question 7). `uv.lock` and `pyproject.toml` do not change without an approved amendment (CLAUDE.md), and CLAUDE.md's one stated route outside the lock is for analysis-only tools. Packages that build the prompts, tokenise them and run every measured model are the instrument of the registered measurement. Using them is an amendment in substance to the project's environment of record, whichever file it is written in. ADR-0032 E1 item 8 already holds that for him.

| Option | For | Against |
|---|---|---|
| 1. An approved amendment to `uv.lock` and `pyproject.toml` | One environment of record for M0 to M5 | Both files are frozen inputs, by hash, of studies that are frozen or running; an amendment on `main` touches all of them |
| 2. A separate hash-pinned file (`studies/m0/requirements-m0.txt`, resolved with `uv pip compile --generate-hashes`, shared packages constrained to the lock's versions, installed with `--require-hashes` into a git-ignored directory, on the path of M0 processes only) | The lock is untouched. The fastest route | A second environment that runs the registered measurement. No precedent for that |
| 3. Models re-implemented in plain torch inside the locked environment, verified once against the library's reference logits and greedy outputs in a separate one-off step (the P10-S2 pattern) | The lock is untouched, and M1 attaches the memory to code the project owns | More implementation work, and an equivalence gate per architecture (Qwen2, GLM-4) |

**Recommended to him: option 3.** Reasons:

1. It is the only route with a precedent he approved (ADR-0022 §14.2). The registered path stays on the locked environment.
2. M1 must attach a memory inside the student's forward pass. That is simplest in code the project owns, and the one-stack rule then puts every reference on that code too. Under option 1 or 2 that question returns at M1.
3. The fixings of section 7 (attention, cache, generation loop) become code under audit, not library defaults.

Its honest cost and risk:

- **Work.** Two architectures with batched greedy generation and a key-value cache; a decoder from output ids to text; an equivalence gate per architecture and per model; their audit. The drafter's guess is one to two weeks of implementation and audit before the load gate, against days for option 2 [E]. Nothing here has been measured.
- **The packages are still installed**, for two one-off steps: rendering and tokenising every prompt into stored, hashed ids; and producing the library's reference logits and greedy outputs. So the install waits for his choice under every option.
- **The equivalence gate.** Per model, on 64 fixed prompts, in CPU float32 (models up to 1.5B) or CPU bfloat16 (larger): identical greedy token sequences for 64 new tokens, and a largest logit difference under a tolerance registered before the gate runs. A failure is an engineering stop.
- **Risks.** A divergence outside the gate's prompts; a generation loop slower than the library's; the unknown behaviour of half precision on MPS, which no option removes.

If he weighs speed first, option 2 is the reasonable choice. Option 1 is not recommended while studies are frozen on the lock's hash. **Condition under every option:** the resolved versions and the model code that M0 measured bind M1 to M5; if any differs, the references are measured again before S is scored.

**Repository code.** Loading a model may never execute code from its repository. `trust_remote_code=False` is passed explicitly wherever the library is used. Before any weight is fetched, the small configuration files are fetched at the pinned revision. The repository-code check covers `config.json`, `tokenizer_config.json` and `generation_config.json`: no `auto_map`, no custom tokenizer class, and no `.py` file in the repository listing that the loader would reference; and `model_type` must be a class built into the pinned library. A model that fails is not downloaded; it is recorded as REFERENCE NOT RUNNABLE LOCALLY (NEEDS REPOSITORY CODE) and returns to the human lead. He alone may approve one specific revision, after the code has been read and its hash recorded.

**Network.** Used in stages D0a and D0b only. Every later stage runs with `HF_HUB_OFFLINE=1` and loads from local paths. The `datasets` library is not used (it can run dataset scripts); dataset files are fetched as files at a pinned revision and read with `pyarrow` in `-I` mode from their own directory.

**Harness.** Bespoke, small, and tested on hand-labelled outputs (section 7). ADR-0032 prefers an established public harness "where possible"; the reasons for not taking one are in section 19, row 4.

## 6. Evaluations

### 6.1 Units

An **evaluation** is one set of items with one scoring rule. An **evaluation part** is its in-teaching-eligible half or its held-out half (section 6.4). A **domain** groups evaluations. Outcomes are read per evaluation part; no average over parts, evaluations or domains is computed for any outcome.

Every item has one score in {0, 1}, given by a rule. No model grades anything.

### 6.2 Private generated evaluations (gate candidates)

Generated by code from registered seeds. The generator is frozen before any model is run on any item.

| Id | Domain | What is generated | How the answer is fixed | Response mode |
|---|---|---|---|---|
| R1 | Reasoning | Deduction over stated relations: orderings, kinship, set membership, simple conditional rules. Controlled depth. Answer: one name from a closed list, or yes/no/cannot be determined | The generator's solver; an independent second solver re-derives it from the item's structured form | worked |
| R2 | Reasoning | Algorithmic and symbolic tasks: counting, sorting, list operations, base conversion, string rewriting. Exact answer | As R1 | worked |
| M1 | Mathematics | Multi-step arithmetic and simple algebra word problems from own templates (not the public templated sets, whose licence forbids derivatives [V]). Integer or decimal answer | As R1 | worked |
| C1 | Code tracing | Output prediction. Small deterministic Python programs from a typed grammar: arithmetic, strings, lists, loops, conditionals, small functions. No imports, no input, bounded loops. Each prints exactly one line. The question is that line | The program is run in the locked interpreter, twice, in a fresh restricted process with a time limit. It is our generated code, not model-written | worked |

Requirements for each:

- **Families and clusters.** At least 12 template families, each a distinct rule structure. A cluster is a (family, rule shape) pair, the level at which items share their rule; surface frames vary within a cluster. The number of clusters per evaluation part, G, is a registered design number, fixed before G-gen. Proposed: at least 300 (the human lead's number). The reason: in the sealed split the clusters are fixed, and between-cluster variance sets a floor on the standard error that no number of items removes (review B1). Families are strata.
- **Difficulty.** Five registered levels (depth, steps or program size), and two reserve levels, one easier and one harder, implemented before any scoring.
- **Reproducible generation.** No generator iterates a set or dict of strings without sorting, and none calls `hash()`. Every process runs with `PYTHONHASHSEED=0`. A test generates each pool twice in two processes and compares hashes.
- **Capacity gate (G-gen).** For every cluster and level, the number of distinct items the generator can produce is at least 10 times the number the pools demand. Otherwise engineering stop.
- **Disjointness.** Tuning, development and sealed items are pairwise disjoint after normalisation.
- **Validity gates, no model involved.** Both solvers agree on every item. Items are unique after normalisation. `arbor-auditor` reads 50 rendered items per evaluation for ambiguity and records what it finds. Templates are written by an agent; their answers are computed by rule. The auditor context that writes the second solvers does not audit them: a separate auditor context audits the solver pair.
- **Interior check.** Section 6.5.
- **Stated limit.** A generated set measures a narrower construct than a human-written benchmark. Private and public scores are printed side by side and never pooled.

### 6.3 Code tracing is measured; code writing is not

**Recommended for the gate: output prediction (C1), scored by string comparison.** No model-written code is executed anywhere in M0.

This is not what ADR-0032 section 4 words as "coding (scored by executing the code)". C1 measures reading and tracing code. It does not measure writing it, which is what "coding" ordinarily means. Section 6.8 states what follows for every label.

**Option, his call: code writing scored by execution (C2).** Generated function specifications with reference solutions and generator-made tests; public beside it: HumanEval+ (164 items, Apache-2.0) and MBPP+ (378, Apache-2.0) [V]. What building it would need:

- **his decision to start Docker (Colima)** or to use another container tool. Colima is currently stopped on this machine by his permission;
- an image pulled and pinned by digest, counted in the ledger (ceiling 2.0 GB; its size is UNVERIFIED in note 1);
- a sandbox: a container or lightweight virtual machine; no network; non-root; read-only root filesystem; a size-limited scratch directory; CPU, memory, process and wall-time limits; no host mount except the per-task input; a fresh container per batch;
- generation first, execution later from stored records;
- a test with adversarial items (network access, file writes outside scratch, fork bombs, long sleeps, large allocations) before any model-written line is run; a failed test is an engineering stop;
- the C2 generator, its reference solutions and tests, their audit, and one more review of this specification; about 2,000 to 3,000 more worked-mode items per system in the registered measurement [E].

Without it C2 is NOT MEASURED IN M0 and code writing has no gate candidate until a later decision.

### 6.4 Generalisation: what M0 reserves

Generalisation is a split, not a domain, and it can be defined only when a teaching procedure exists (M1.5). M0 reserves what cannot be reserved later:

1. **The family partition.** At the freeze, a registered seed splits the families of each private evaluation into **part A** (teaching may draw on these families) and **part B** (held out: no teaching item, template or family of part B may ever be used for teaching). Half each. Fixed before any score, so that no result can shape it.
2. **Both parts are measured in M0**, separately, so that the power sizes exist per part.
3. **Public sets.** Their training splits are not downloaded and not used by M0. Whether a public evaluation counts as in-teaching or out-of-teaching is settled in M1.5; M0 records that nothing from them has been used.
4. **Seeds** for the M5 sealed draw and for the composition supplement (section 12).

### 6.5 Keeping difficulty off floor and ceiling

On a **tuning draw** (its own seed; 100 items per level and part), every system is scored at the chosen format (section 7). A code rule then fixes the mix of levels for each private evaluation part:

- candidates: every contiguous range of levels, uniform over the range;
- chosen: the range that maximises the smallest distance of any Tier 2 reference's tuning score from the band edges of section 10.2; ties to the wider range, then to the lower start;
- if no range puts every Tier 2 reference inside the band, the two reserve levels are scored once and the rule is applied again; nothing else changes.

If the best range is still outside the band, the part is flagged CALIBRATION NOT INTERIOR. It enters the registered measurement with that range, and its registered outcome is read on the development draw. No generator is rewritten after a score exists. Tuning scores are sealed (section 8); the public record holds the chosen range and a yes or no. Because a chosen range tells where the references sit, δ_e is fixed before this stage (choice 3).

### 6.6 Domains with no private set in M0, and what is done instead

| Domain | Why not | Instead |
|---|---|---|
| Language understanding | A private set can be built only as a much narrower construct (for example rule-built reading questions over generated fictional passages, or rule-made minimal pairs). Natural text cannot be produced by rule without a model in the loop, and a model in the loop would favour its own family. **Not built in M0; his to add (choice 2)** | **L1, a pooled public evaluation**, licence-confirmed tasks only: ANLI test (3,200, CC BY-NC 4.0) and SuperGLUE validation tasks (BoolQ 3,270; MultiRC 4,848; ReCoRD 10,000; WiC 638; RTE 277) [V for sizes; the SuperGLUE per-task licences are UNVERIFIED]. At most 4,000 items per task by a registered draw. Strata: tasks. Clusters: passages or premises. A task enters only if its own licence is re-read at D0b and allows local research use |
| Factual knowledge of the real world | Real facts are public by nature; a private set cannot exist | **K1**: MMLU-Pro test (12,032 items, ten options, MIT) [V]. **K2**: PopQA (about 14k entity questions; MIT per its GitHub repository, no licence on the dataset card) [V] |

Item units and scoring: MultiRC, one answer option is one item (yes or no), clustered by passage; ReCoRD, exact match of the extracted answer against any gold entity; PopQA, normalised exact match of the extracted answer against any alias, not a substring match in free text.

For these two domains the gate candidates are public items. Whether a reference saw them in training cannot be checked. It is disclosed on every line that uses them.

**Reserved, not an evaluation of the battery: K0, fictitious facts.** Invented entities and facts, generated privately. Every model should be at chance on them. M0 scores 500 development items once to check exactly that; a system above the floor band flags GENERATOR GUESSABLE (the items leak their answer). The generator is the look-up teaching material M1.5 and M2 will need.

### 6.7 Public sets printed beside the private ones (never gated alone, never pooled with them)

| Set | Items | Licence | Note |
|---|---|---|---|
| GSM8K test (`openai/gsm8k`) | 1,319 | MIT | [V]; heavily exposed [V] |
| BIG-Bench Hard, from its GitHub source | 6,511 over 27 tasks | MIT per the GitHub repository; the mirror states none | [V]; fetched from the source, not the mirror |
| CRUXEval, output-prediction half (`cruxeval-org/cruxeval`) | 800 functions | MIT | [V] |

Dataset commit prefixes in note 1 are pointers; full revisions and file hashes are pinned at D0b. Every licence is re-read at its source before the fetch. A set whose licence cannot be confirmed is not fetched and is listed as NOT MEASURED (LICENCE). For GSM8K and MMLU-Pro the report also prints the bespoke scorer's agreement with each benchmark's published answer-extraction rule on the same raw outputs.

### 6.8 Domain list as proposed

| Domain | Gate candidates | Printed beside |
|---|---|---|
| Reasoning | R1, R2 | BIG-Bench Hard |
| Mathematics (a candidate addition in ADR-0032; recommended) | M1 | GSM8K |
| Code tracing (output prediction) | C1 | CRUXEval output prediction |
| Language understanding | L1 (public) | — |
| Factual knowledge | K1, K2 (public) | K0 as a floor check |

Code writing is NOT MEASURED in M0. Every label, report, scorecard line and later verdict that uses C1 or CRUXEval says "code tracing", never "coding". Any later claim about the coding capability the human lead named carries NOT EVALUABLE (CODE WRITING NOT MEASURED) until a code-generation evaluation scored by execution exists. ADR-0032's L-B0 prerequisite PB-3 (the container) stays undelivered.

The domain list is the human lead's. Removing a domain removes its rows. Adding one needs an amendment before the freeze.

## 7. One system rule (for every reference alike)

Fixed before any tuning score, in a record whose hash enters the freeze. Rows that name library settings apply as written wherever the library runs (options 1 and 2, and the one-off steps of option 3); under option 3 the registered path's own code has the same properties and the equivalence gate checks them.

| Item | Rule |
|---|---|
| Chat template | Each model's own published template, from its tokenizer files at the pinned revision, with one user message and the generation prompt added. No system message is supplied; where a template inserts its own default system text, that is kept (the alternative is choice 13) |
| Template differences | The rendered example of each model is recorded, and every difference between families is listed in the record. This includes the default system text that the Qwen2.5 template inserts when no system message is given, and the GLM-4-0414 prefix tokens. These are the listed exceptions of ADR-0032 §4. S uses S₀'s template unchanged |
| Tokenisation | Token ids come from the chat template's own tokenisation, never from re-tokenising rendered text with special tokens added. At G-load, each model's ids for the fixed example are compared with a hand-checked expected sequence |
| Prompt | The same instruction text and item text for every system. Zero-shot. No few-shot examples from any evaluation |
| Candidate formats | Three per response mode, differing in instruction wording and answer-marker convention. Their exact texts are written and hashed before any model is run |
| Format choice | Per evaluation, by code, on 50 tuning items per part at the middle level under all three formats (public sets: 50 of their 150 tuning items): the candidate with the smallest largest format-failure rate across systems; ties to the higher mean accuracy across systems, then to the lowest index |
| Decoding | Greedy, for every system, overriding each model's own generation defaults. This departs from the sampling some vendors recommend (note 1 [V] for the Qwen3.5 cards) and is disclosed |
| Generation config | A new GenerationConfig is built from scratch: `do_sample=False`, `num_beams=1`, `repetition_penalty=1.0`, no temperature, top-p or top-k, and the model's listed EOS ids. It is passed explicitly, so the checkpoint's `generation_config.json` is not merged. The effective config is recorded per model |
| Attention and cache | `attn_implementation` is pinned to one value for every model; the KV cache is the library's default dynamic cache; both are recorded |
| Thinking mode | Off, through the model's documented template switch, for every model that has one. A model that cannot turn it off is not specified here |
| Stop | The model's end-of-sequence tokens (listed per model) or the token limit. No other stop string |
| Token limit (direct mode) | 32 new tokens |
| Token limit (worked mode) | Chosen by code on the tuning draw: the smallest of {384, 512, 768, 1,024} at which every system's limit-hit rate is at most 2 %. Fixed before the development pools are generated. Tuning runs at 1,024; an output at a smaller limit is its prefix |
| Prompt length | An item whose prompt exceeds 2,048 tokens under any system's tokenizer is excluded for every system, before scoring; the count is printed |
| Answer extraction | The text after the last answer marker on its own line; trimmed; case-folded; whitespace collapsed; a final full stop removed; numbers compared as decimals after removing thousands separators. No extractable answer scores 0 and is counted as a format failure; a limit reached without an answer scores 0 and is counted separately |
| Answer grammar | Per evaluation, a registered regular expression for the marker and a canonical answer grammar: numbers; one letter A–J; yes/no/cannot be determined; single-line printed output for C1, whose programs print exactly one line; lists. The scorer is tested on at least 200 hand-labelled raw outputs per evaluation from R1, labelled by a context that did not write the scorer. Any disagreement is an engineering stop. (The labelling runs inside the sealed stage; only counts leave it.) |
| Chance level | c of section 10.2 is the item mean of 1/k_i for closed answers, 0 for open answers |
| Batching | Left padding; batches formed by a stable sort on prompt length. Batch size per (model, mode) is fixed at G-load by a rule: the largest power of two whose peak memory at the longest admitted prompt plus the token limit stays at or under 24 GiB. It is used unchanged in R1, R2, R3 and M. Each item's batch membership is stored in its raw record. (The worked-mode limit is not yet chosen at G-load, so the rule uses the largest candidate, 1,024.) |
| Numerical check | At G-load, each model's greedy output in MPS bfloat16 on 32 fixed prompts is compared with CPU float32 (models up to 1.5B) or CPU bfloat16 (larger models). The token-agreement rate and any non-finite value are recorded. A non-finite value fails the precision gate |
| Samples | One greedy output per item |

Response mode per evaluation: worked for R1, R2, M1, C1, GSM8K, BIG-Bench Hard and CRUXEval; direct for L1, K1, K2 and K0.

**Repeat identity gate.** For each model and mode, 64 tuning items are run twice at the fixed batch size, in two separate fresh processes. The second process runs after a full model reload, and if possible under different machine load. The two runs must give identical token sequences. The gate runs at G-load and again inside R3. A failure is an engineering stop (NON-DETERMINISTIC STACK).

## 8. Splits and seals

| Split | Size | Who scores it |
|---|---|---|
| Tuning draw (private) | 100 items per level and part | Rehearsal stages only; scores sealed |
| Development pool (private) | 4,000 items per evaluation part, generated and hashed at the freeze | M0 scores a registered 1,500 of them (the M0 draw), balanced over the G clusters. The other 2,500 stay unscored for M1 to M4 |
| Development split (public) | 1,650 items (150 tuning, 1,500 scored), drawn by whole clusters with a registered seed, inside L1 in proportion to each task; where a set is too small for that, one third of its clusters. Sets above 6,000 items also set aside a registered reserve of 1,000 for M1 to M4 | M0 |
| Sealed pool (private) | **20,000 items per evaluation part**, the registered maximum, spread evenly over the G clusters | **Nobody in M0.** M5 draws its sealed split from it |
| Sealed part (public) | The rest of each public set | Nobody in M0 |
| K0 | 500 development items; a sealed pool of 20,000 | M0 scores the 500 |

**M0 scores development items only.** Every registered outcome of M0 is defined by ADR-0032 on the development split, so none needs a sealed item. M5 remains the only reader of the sealed pools. The price, stated: M0 cannot confirm that a sealed pool is interior or has the same disagreement rate as the development draw. It has the same frozen generator, level mix, families and clusters, and that is all that is known. A sealed split later found at floor or ceiling is NOT EVALUABLE and is never re-drawn.

**Why 20,000, and why it may not be enough.** Arithmetic only [E], with the rule of section 9.4 and 55 to 70 tests in the conjunction. Ignoring clusters, a part needs about 19·d/δ² items: about 6,200 to 6,500 at d = 0.3 and δ = 0.03, and about 14,100 to 14,600 at δ = 0.02. Clusters add a term that items cannot remove: the largest power any number of items can reach needs δ·√G/τ of at least about 4.3, τ being the between-cluster standard deviation of the paired difference. With the reviewer's illustrative τ = 0.10 that asks for G above about 75 at δ = 0.05, above about 210 at δ = 0.03 and above about 470 at δ = 0.02; with τ = 0.05, above about 120 at δ = 0.02. Review 1's own run gives 19,349 items at τ = 0.10, G = 300, δ = 0.03 (product rule). τ is not known before M0 measures it, and G must be fixed before that. So G = 300 may leave δ = 0.02 UNDERPOWERED whatever the pool. The pool size and G are the human lead's to change before the freeze; the pool may be raised later, never lowered (ADR-0032 section 5).

**How the sealed pool is made.** A dedicated stage at the freeze generates it from the registered sealed-pool seed combined with a secret salt (32 random bytes drawn at that moment). The pool and the salt are written outside the repository, with read permission removed. The repository receives only: the pool's SHA-256, the salt's SHA-256, item counts per family, cluster and level, and the results of the checks. The checks run inside that stage with no model: solver agreement, uniqueness, and no exact or normalised match with any tuning or development item. Revealing the salt at M5 lets anyone regenerate the pool and check the hash. No sealed item is tokenised, loaded beside a model or printed.

The stage also writes, inside the sealed directory, a keyed fingerprint set of the pool: HMAC-SHA-256 under the salt of each normalised item and of each of its 13-grams. M1.5's overlap check runs as a sealed-stage process that reads salt, fingerprints and teaching data, and writes counts only.

**Sealed scores during M0.** Tuning scores go to a sealed archive outside the repository; the public rehearsal record holds only formats chosen, level ranges chosen, the token limit chosen, yes or no flags, format-failure rates and timing. `arbor-auditor` verifies the sealed archive with code that prints only agree or disagree and hashes, never a score. Development scores are read once, in the analysis stage.

**What the seals are.** The hashes commit M0 to the pools. At M5 anyone can check that the pool scored is the pool generated at F. That is the guarantee. Confidentiality is procedural on one account, and of limited value anyway: the generator and its templates are in the repository, so exact sealed items add little secrecy beyond the template set. Held-out part B rests on procedure: no teaching code may use part-B families, checked in M1.5 by template signature. A second operating-system account would need administrator access, which only the human lead can grant (ADR-0032, E1 item 20).

## 9. Statistics

### 9.1 Measured on the M0 draw, per evaluation part

1. **Score** of each system, with a two-sided 95 % interval.
2. **Paired difference** for every pair of systems, with its interval; for (reference, S₀) also the one-sided lower 95 % bound L.
3. **Discordance** for every pair: the share of items on which exactly one of the two is right, and its two directions.
4. **Union of the teachers:** U, the share of items at least one teacher gets right; B, the better teacher's score; G_U = U − B.
5. **Format failures and limit hits** per system.

Subcategory scores (per family, per task) are printed and enter no outcome.

### 9.2 Intervals

Paired on identical items. Cluster bootstrap, stratified by family or task, 10,000 resamples, registered seed, percentile bounds. G_U is recomputed in every resample, including which teacher is the better one, so that choosing the better teacher on the same data is inside the bound. With fewer than 30 clusters: the cluster-robust standard error with a t quantile on (clusters − 1) degrees of freedom replaces the percentile bootstrap.

### 9.3 Nuisance spreads (descriptive only)

On the first 150 M0-draw items of each evaluation, by a registered order, each system is run again under one change at a time:

| Variation | Change |
|---|---|
| Format | Each of the two candidate formats not chosen |
| Sampling seed | The vendor-style sampling setting (temperature 0.7, top-p 0.8) with two registered seeds |
| Answer order | Options permuted by a registered seed (multiple-choice evaluations only) |
| Batch | Batch size 1 |
| Default system text | One identical neutral system message for every model ("You are a helpful assistant.") in place of each template's own default (or the reverse, if choice 13 makes the neutral message the rule) |

Printed per system and evaluation: the share of items whose score flips, and the change in score. They enter no outcome, no margin and no sample size. Their use is ADR-0032's: to show that the fixings matter, and to stand beside later item-level regression counts. With 150 items they are rough.

### 9.4 Sizes for the power rule

M0 does not set δ_e. It reports, for each candidate margin δ in the **registered grid {0.02, 0.03, 0.05}** (and any value the human lead adds before the freeze):

- **d_e**, per evaluation part: the largest discordance between S₀ and any Tier 2 reference (ADR-0032 section 5, item (i)), and the pair that gives it. If a reference is NOT RUNNABLE, d_e is taken over runnable references, and the M5 tests against an unrunnable reference are NOT EVALUABLE LOCALLY.
- **Per-test power by simulation of M5's own design from the measured paired outcomes.** For that pair, a candidate size n and G_e, the number of clusters the part's sealed split will contain (for a private part, the number of templates of the part as fixed by the frozen generator and recorded at G-gen; for a public part, the number of clusters in its sealed part): 20,000 simulated samples. Each is drawn in two stages within strata: first G_e clusters with replacement from the M0 draw's clusters, allocated to strata as the sealed split will be; then n/G_e items with replacement within each drawn cluster. In each sample, the mean difference is recentred to zero. The mean difference and its cluster-robust standard error over the G_e drawn clusters are then scaled by √(d_e / (d_e − μ²)). The simulated test passes if the estimate minus t₀.₉₅,G_e−1 standard errors is above −δ. π_e(n, δ) is the share that pass, printed with its Monte Carlo standard error. (μ is the measured mean difference of the pair. "Templates" here are the clusters of section 6.2.)
- **Floor from the clusters.** Also printed per part: τ̂_e, the between-cluster standard deviation of the paired difference within strata (method of moments, registered formula); and the largest per-test power reachable at any n, Φ(δ·√G_e / τ̂_e − z₀.₉₅). If that is below the per-test target, the part is NOT EVALUABLE (UNDERPOWERED, e, δ) whatever the pool size.
- **The conjunction.** Each evaluation part carries m tests: one per Tier 2 reference, one NO HARM test, and one interference test (ADR-0032 section 7 says these join; a second table omits it). With M_e = m·P tests in all, the size required for part e is the smallest n on the ladder {500, 1,000, 1,500, 2,000, 3,000, 4,000, 6,000, 8,000, 12,000, 16,000, 20,000} with π_e(n, δ) ≥ 1 − 0.2/M_e. This is Boole's inequality, which holds whatever the dependence between tests, so no assumption about dependence is needed. P counts every gate-candidate part of the registered domain list, including parts later found NOT EVALUABLE. Alpha 0.05 and power 0.8 are ADR-0032's proposed values.
- **Retention tests (PENDING LEAD REVIEW; choice 15).** ADR-0032 section 6 is part of the gate, and its tests are not among the m above. If M5 scores retention on sealed splits, they join the conjunction. Until that is decided M0 prints a third table with two more tests per part as a placeholder; the true count is fixed in M3's specification.
- **Confirmation.** At the size found, 2,000 simulations with the full percentile bootstrap inside, its Monte Carlo standard error printed; both figures are printed. The cost of this step is measured in R2.

**What this is and is not.** The per-test power is simulated from measured pairs, keeping the pairing, the strata and M5's own number of clusters. No S exists, so the tests cannot be simulated jointly; Boole's bound is used across them and needs no such simulation. It costs about 2 % more items than a product would (Review 1, R1). From M1b on, with S's own development outcomes (item (ii) of the rule), the sizes are computed again and may only rise.

Also printed, per (reference, evaluation part, δ): **CAP MET** if δ ≤ L/2, otherwise **CAP NOT MET** (ADR-0032 section 4). A flag; it moves no margin.

## 10. Registered outcome rules

All on the M0 draw. Read in this order. Scores are point estimates on 1,500 items unless a bound is named.

### 10.1 REFERENCE NOT RUNNABLE LOCALLY (named reference, cause)

The first that applies, in this order: NEEDS REPOSITORY CODE, then PRECISION, then MEMORY, then COST.

| Cause | Rule |
|---|---|
| NEEDS REPOSITORY CODE | The check of section 5 fails |
| PRECISION | Section 5's precision order ends without a finite run of the model |
| MEMORY | In the load gate at batch size 1 the process's peak memory exceeds 34 GiB. The reading is the peak of the process's `ri_lifetime_max_phys_footprint` (macOS `proc_pid_rusage`), which includes Metal allocations. The registered batch size must also stay under the cap |
| COST | The measuring rehearsal projects more than the per-reference ceiling of section 14 for its share of the registered measurement, and the human lead does not extend the ceiling at Decision 2 |

Decided before Decision 2, from gates and timing only, never from a score. Its rows read NOT MEASURED. It stays in the reference set.

### 10.2 NOT EVALUABLE (FLOOR OR CEILING)

Chance level c: the item mean of 1/k_i for closed answers with k_i options, 0 for open answers. Band: from c + 0.10·(1 − c) to 0.90.

- A pair (Tier 2 reference, evaluation part) is **NOT EVALUABLE (FLOOR)** if the reference's score is below the band, and **(CEILING)** if above it.
- A pair that is NOT EVALUABLE (FLOOR OR CEILING) cannot pass. A PARITY verdict that needs it reads NOT EVALUABLE for that reference, so reading per pair never makes PARITY easier to print than the per-evaluation wording of ADR-0032.
- The evaluation part is NOT EVALUABLE (FLOOR OR CEILING) if no Tier 2 pair on it is inside the band.
- Printed beside it, entering no outcome: S₀ AT FLOOR or S₀ AT CEILING by the same band. Beside S₀ AT FLOOR the line adds: "the NO HARM test on this part is nearly vacuous" (PENDING LEAD REVIEW; choice 16).

Reason for 0.10 and 0.90: outside them at most a tenth of the scale is left on one side, and a margin of a few points cannot be told from saturation. They are proposed values and the human lead's to change before stage R1, which uses them.

### 10.3 TEACHER NOT AHEAD

For teacher T and evaluation part e: T is AHEAD if L, the one-sided lower 95 % bound of (score of T − score of S₀), is above 0. Otherwise **TEACHER NOT AHEAD (T, e)**. A domain reads TEACHER NOT AHEAD if no teacher is ahead on any of its gate-candidate parts.

What follows, registered now: on such a part there is nothing for that teacher to teach S₀; acquisition from that teacher is NOT EVALUABLE there in M2, and coverage (ADR-0032 section 7) is not read there.

### 10.4 NO COMPLEMENTARITY

For evaluation part e and each δ of the grid: the teachers are COMPLEMENTARY if the one-sided lower 95 % bound of G_U = U − B is above δ. Otherwise **NO COMPLEMENTARITY (e, δ)**. Computed even on a part that is NOT EVALUABLE, and marked so.

If a teacher is NOT RUNNABLE, complementarity on every part reads NOT EVALUABLE (REFERENCE NOT RUNNABLE), never NO COMPLEMENTARITY.

Per domain the line reads: COMPLEMENTARY ON EVERY PART, COMPLEMENTARY ON NAMED PARTS, or NO COMPLEMENTARITY. Which of these a superiority claim needs is section 7 of ADR-0032, not approved, and the human lead's.

**What follows if the teachers do not differ, registered now.** The two-teacher test M4 is NOT EVALUABLE (NO COMPLEMENTARITY) for these teachers on those parts. M1a to M3 are single-teacher questions and are not affected. Nothing is substituted inside M0. A different second teacher (note 1 names `GLM-Z1-9B-0414`, 18.80 GB [V]) would be a supplement with its own specification, approval and download decision; with any set it would exceed the 50 GB limit.

### 10.5 NOT EVALUABLE (UNDERPOWERED)

For evaluation part e and each δ of the grid: **NOT EVALUABLE (UNDERPOWERED, e, δ)** if any of these holds: the largest reachable per-test power of section 9.4 is below the per-test target; the required size is above the sealed pool (20,000 for private parts; the fixed sealed part for public ones); the required size is not reached on the ladder. Never dropped from the conjunction to make the others smaller.

### 10.6 GATE NOT EVALUABLE LOCALLY (PROJECTED)

For each δ: the projected M5 scoring time is the sum over gate-candidate parts of (required size × measured seconds per item), over these systems: S₀, every Tier 2 reference, S, S taught by each teacher alone (two systems), and five Tier 1 systems, all at S₀'s measured rate except retrieval, which is taken at S₀'s rate × (mean prompt tokens with retrieval ÷ without). Retrieval's prompt length is fixed in M1.5; until then the factor is 2. A part that is UNDERPOWERED at δ enters at its pool maximum.

If the projection exceeds **336 charged hours** (two weeks), the line reads GATE NOT EVALUABLE LOCALLY (PROJECTED, δ). It is a projection from M0's timing and is labelled so. It is never a reason to widen a margin or drop a reference (ADR-0032 section 9); what to do is the human lead's decision.

### 10.7 Events that are not outcomes

| Event | What it is |
|---|---|
| A gate fails; a hash differs; the repeat identity gate or the equivalence gate fails; solvers disagree; the scorer disagrees with a hand label; the capacity gate fails; a fetch has no ledger row; a licence cannot be confirmed for a model | ENGINEERING STOP (named). Fixed by an amendment and a new freeze. No registered score is observed |
| An item ends with an error | `item_error`; the analysis refuses; ENGINEERING STOP. Denominators are never reduced |
| A frozen input's hash differs at a stage start | PAUSED — IDENTITY. Restoring the file lets the stage resume |
| A stage reaches a cap | PAUSED. Resumed after an extension decided on projections only; if refused, INCOMPLETE (PAUSED AT CAP) and nothing is labelled |

An engineering stop is never a registered outcome, and a registered outcome is never repaired as if it were a defect.

## 11. Cost and feasibility

**Shared-machine rule.** The machine runs other studies. M0 follows the standing conditions: at most 16 workers across all studies (M0 registers its CPU thread count and counts as that many); its stages pause, or do not start, while another study's quiet-machine stage runs; its own worktree; no write or commit in a worktree whose registered stage is running. Before a model is loaded, free memory must be at least the model's measured requirement plus 4 GiB, or the stage waits with a deadline. Generation pauses between batches while available memory is under 4 GiB, with a deadline: key-value caches grow after the load-time check, and other studies hold up to 12 GiB. One model in memory at a time. M0's load can raise other studies' charged hours; the lead checks their cap margins before a long M0 stage starts.

**No M0 stage needs a quiet machine.** Timing is taken under ordinary shared load on purpose, because later rungs will run that way. Load average and the other study processes are recorded at each stage start. **Every timing figure is measured, in charged seconds on this machine; none is a logical count; none is an efficiency claim.**

**Measuring rehearsal.** For each (model, response mode): whole-process seconds, tokens in, tokens out and peak memory on a registered sample of tuning items, at the chosen formats, the chosen token limit and the fixed batch sizes, through the same launch scripts as the registered run. From it, by code: seconds per item per evaluation, the projection of the whole battery, the cost of the confirmation bootstrap, and the caps (section 14).

**The drafter's own estimate, an order of magnitude only [E].**

- *Registered measurement.* About 28,500 item scorings per system: 12,000 private, about 6,400 public, 500 for K0, about 9,500 nuisance. About 8 million prompt tokens and about 4 million output tokens per system, nearly all of the output in worked mode; more if the token-limit rule settles above 384. No generation rate has been measured on this stack. Note 1's only throughput figures are a third-party table for another stack at 4-bit precision [V], which Review 2 judged a lower bound of unknown slack. Taking 30 to 100 output tokens per second in aggregate for a 9B model with batching, a teacher needs about 11 to 37 hours, the sibling perhaps 4 to 12, the student perhaps 2 to 8. **Of the order of one to four days of machine time.**
- *Rehearsals.* Per system: format choice about 2,100 scorings (private 4 × 2 × 50 × 3; public 6 × 50 × 3); level ranges 4,000, and up to 1,600 more for the reserve levels; the other public tuning items 600; the measuring sample and the gates about 1,500. About 8,200 to 9,800 scorings, at a token limit of 1,024: **about a third to two fifths of the registered measurement**, perhaps 10 to 35 hours. Draft 1 said "a fifth"; Review 1 (R6) showed that was about three times too low for the design as it then stood.
- **Wrong by a factor of three in either direction would not surprise the drafter.** The measuring rehearsal replaces every figure here. Option 3 of section 5 may also change the generation rate.

**A smaller design, for the human lead to weigh:** 1,000 scored items per part and no public reasoning or code-tracing sets. About half the cost. Discordance near 0.3 would be known to about ±2.8 points instead of ±2.3, before any cluster effect [E]. Not recommended, because the saving is small against what the sizes are used for.

## 12. Seeds (proposal; the registry revision and the checker run are the auditor's)

Read against `SEED_REGISTRY_R4.md`, section 5 item 3: the next free data blocks are 310001–319999, then 400001 upward; the next free test ranges are 939001–939999, then 953001 upward. The unapproved draft ADR-0030 proposes the first of each, so M0 proposes the second. M0 trains and initialises nothing, so it needs no initialisation seed. Review 1 found no collision of the block or the test range with anything on any branch it checked.

| Role | Value |
|---|---|
| Tuning draw | 400001 |
| Development pool | 400002 |
| Sealed pool (combined with the secret salt) | 400003 |
| Family partition into parts A and B | 400004 |
| Public development split, reserve and sealed part | 400005 |
| M0 draw and nuisance subset order | 400006 |
| Answer-order permutation | 400007 |
| Bootstrap | 400008 |
| Power simulation | 400009 |
| Sampling seeds (nuisance) | 400011, 400012 |
| Reserved for M5's sealed draw; not used in M0 | 400031 |
| Reserved for the composition supplement; not used in M0 | 400032 |
| Rehearsal and dry-profile draws | 409001–409099 |
| Test seeds | 953001–953999 |
| **Block asked for** | **400001–409999 (data); 953001–953999 (test)** |

Per-evaluation, per-family, per-cluster and per-level streams are derived by SHA-256 of the seed with a text label, never by adding to a seed (registry condition 4.3 item 1). A test asserts it.

**Registry revision needed.** Existing registry files are not edited. The latest addendum is revision 5, untracked in this worktree: `SEED_REGISTRY_R5.md` (SHA-256 `19199e46d9f4e51d5650b9cfd9f3e1dd11730d45ae9fdada776a111e741ea865` as it stands on 2026-11-20) with `seed_registry_check_r5.py` (`8ce47ab52abbe25b4b308ca2a1e7587f5461b13340f1faa2a0c0cff6804f4611`). M0 needs a new revision 6 by `arbor-auditor` (`SEED_REGISTRY_R6.md` and a new checker file) that allocates the block above, checks it against the whole inventory, and cites revision 5 and the earlier files by hash. Revision 5 reports that its checker fails on `origin/main` for a P10-I-S2 reason. M0's freeze gate needs a checker run, unedited, that reports no failure involving M0's allocations or any collision with them. Failures that predate M0 and belong to other studies are listed and do not block M0, unless the auditor finds that they touch M0's ranges. **PENDING LEAD REVIEW.** The registry is named for P10-I; whether the M ladder keeps using it is the lead's and the auditor's call. Recommended: yes, because its inventory covers every study.

## 13. Stages, the freeze and engineering requirements

"Choice n" is choice n of section 16. A stage does not start before every choice it names is given by the human lead.

| Stage | Content | Needs |
|---|---|---|
| I0-a | Locked environment only: generators, solvers, scorers, analysis, and their tests. No download, no package | Decision 1 |
| G-gen | Generator gates of section 6.2 (validity, reproducibility, capacity, disjointness); the registry check. It may be rehearsed under Decision 1 at the proposed numbers. Its record of record, which freezes the generators, is made only at his G and his domain list, and is made again if either changes | Decision 1; for the record: choices 2 and 10 (G) |
| D0a | Resolve and install the packages, with ledger rows | The human lead's choice 8 |
| I0-b | Harness and loaders (or, under option 3, the model code and its equivalence gates), tested on a tiny random model | Choice 8; D0a |
| D0b | Clerk's download inventory. Each licence re-read at its source and its text hashed. The repository-code check. Then weights and dataset files | Choices 1, 2, 7, 11 and 14; choice 6 if an image is pulled |
| G-load | Load without repository code; precision; numerical check; memory and batch sizes; template rendering and token ids; repeat identity | D0b; I0-b; the memory numbers of section 14 (choice 10) |
| R1 | Tuning: format choice, level ranges and worked-mode token limit, by code; scores sealed; scorer hand-label test | G-load; **choice 3 (δ_e)**; choice 9 (band); choice 5 (rehearsal cap); choice 13 |
| R2 | Measuring rehearsal; caps written by code into the candidate plan | R1; choice 5 |
| R3 | Counting rehearsal: every registered stage end to end in the dry profile against the candidate plan; repeat identity again | R2 |
| F | Freeze: development pools and sealed pools generated and hashed; family partition; every hash; the plan. The freeze refuses unless the committed plan has the hash R3 recorded | R3; the implementation audit; agree on the sealed archive; **every number of the config confirmed by him (choices 5, 9, 10)**; the registry revision |
| — | **Decision 2 (the human lead; choice 4)** | F |
| M | Registered measurement: generate, store raw outputs, score | Decision 2 |
| A | Analysis, once; pure functions over records. Report | M |
| V | `arbor-auditor` recomputes every outcome from raw records with code that imports nothing from the study. The outcome record is written only after that | A |

**Frozen at F, each by SHA-256:** every file under `studies/m0/` except its printing directory; `configs/m0_reference_models.toml`, which holds every threshold, grid, size, limit and seed of this document; `tests/test_m0_*.py`; the package file of the chosen route; `uv.lock` and `pyproject.toml` (unchanged unless option 1 is taken); every model file and dataset file; each model's rendered template example and token ids; under option 3 the stored prompt ids and the equivalence records; the prompt and format texts; the generators and their G-gen record; the development pools; the sealed pools', the fingerprint set's and the salt's hashes; the public rehearsal record and the sealed archive's hash; the plan. This ADR's hash is recorded for provenance only. A test asserts that every number in this ADR equals the config's value.

**Engineering requirements (the P10-I lessons, as ADR-0031 section 16 lists them):**

1. **Same path.** R1, R2 and R3 drive the same entry point and the same fixed launch scripts as the registered run, one fresh process per stage.
2. **Caps by code.** Cap = charged so far + 2 × projected remaining from R2's record, written into the candidate plan before R3.
3. **Generation and scoring are separate.** Raw outputs (text, token ids, finish reason, batch membership, timing) are stored first; scoring and analysis are re-runnable from records.
4. **Attempts and waits.** Every refused, failed or discarded attempt is written into the run directory and kept. No wait without a deadline. Nothing is written to the system temporary directory; scratch goes to the git-ignored `experiments/_scratch/`.
5. **Tests** do not depend on other studies' files or on the repository's planning state. The analysis is tested on a synthetic registry with a known answer for every rule of section 10, including a case where two systems' records are swapped and the test must fail.
6. **Outputs.** A stage's record is written and closed before any message is printed. Public-output guards do not match inside hashes.
7. **Stops.** Identity failures pause and resume. Code and environment errors are engineering stops.
8. **Checks run locally** (`ruff`, `mypy`, `pytest`); no CI run is required.

**Roles.** `arbor-implementer` writes the code. `arbor-auditor` contexts, each separate and working from code and records only: one writes the second solvers; another audits the solver pair and the implementation; one verifies the sealed archive with code that prints only agree or disagree and hashes; one recomputes the outcomes. The scorer's hand labels come from a context that did not write the scorer. `arbor-clerk` inventories downloads and hashes. Which model ran each task is recorded from session metadata. Which agent and model wrote the evaluation code is recorded, so that the teaching code of M1.5 can be written by another context. All are Claude models; they are not independent authors in the strong sense, and that is disclosed.

## 14. Caps and limits

Charged hours: a stage supervisor's wall clock (ADR-0031 §17). **Every number in this table is a proposal until the human lead confirms it, which he does before F** (and before the stage that first uses it: section 13).

| Limit | Kind | Rule |
|---|---|---|
| Downloads: 50,000,000,000 bytes cumulative; M0 ceiling = the chosen set's planned total plus 1 GB | Resource cap | Section 4.1. A larger size than listed is an engineering stop |
| Rehearsals R1 to R3: 48 charged hours (draft 1 said 30; raised with the corrected estimate of section 11) | Resource cap | Extended by the human lead on projections only |
| Registered measurement: by code from R2 | Resource cap | Section 13, requirement 2 |
| **Per-reference ceiling: 72 charged hours** of the registered measurement | Budget ceiling | Above it: section 10.1, COST |
| **Whole registered measurement: 168 charged hours** | Budget ceiling | Above it the lead returns to the human lead before Decision 2. The battery is not cut |
| Memory: 34 GiB peak footprint for the M0 process; 24 GiB in the batch-size rule; 4 GiB free beyond a model's need before loading and between batches | Resource cap | Sections 7, 10.1 and 11 |
| Sizes: G at least 300 clusters per private part; 1,500 scored per part; pools 4,000 and 20,000; public development 1,650 and reserve 1,000; nuisance 150; tuning 100 per level, 50 per part for the format choice | Design ceiling | G is fixed before G-gen's record. Nothing is extended after the freeze. The sealed pool may be raised before any sealed score, never lowered |
| Simulation: 20,000 samples per size; 2,000 for the confirmation; bootstrap 10,000 resamples | Design value | Fixed at the freeze |
| Token limits: 32 (direct); worked from {384, 512, 768, 1,024} at a 2 % limit-hit rate; prompt 2,048 | Design value | Section 7 |
| Margin grid {0.02, 0.03, 0.05}; alpha 0.05; power 0.8; cap fraction ½; band 0.10 and 0.90; 336 hours; active-compute bound 1.25 | Thresholds | The band before R1; all fixed at the freeze. Never changed after a score exists |

The registered measurement happens once. No outcome is a reason to add items, formats, seeds or models. A further measurement would be a later study with its own specification.

## 15. What each outcome would and would not mean

| Outcome | Would mean | Would not mean |
|---|---|---|
| Teachers ahead on most parts; COMPLEMENTARY somewhere | The preconditions of M2 and M4 hold on the named parts for these models | Anything about whether a student with a memory can close a gap or combine teachers |
| TEACHER NOT AHEAD on a part or domain | These teachers have nothing to add to this student there, on these items | That the student is good there; that other teachers would not be ahead |
| NO COMPLEMENTARITY | On these items the union of the two teachers is not shown to exceed the better one by the margin. M4's superiority question cannot be asked of this pair there | That teachers can never complement each other; that a single-teacher ladder is blocked |
| NOT EVALUABLE (FLOOR OR CEILING) | That reference, on that part, cannot support a non-inferiority reading | A defect of the model |
| NOT EVALUABLE (UNDERPOWERED) at a margin | The pool, or the number of clusters, cannot support the gate at that margin for that part | A reason to widen the margin; the margin is the human lead's substantive judgement |
| GATE NOT EVALUABLE LOCALLY (PROJECTED) | On M0's timing the final test would exceed two weeks of this machine | A decision. Any reduction of scope is the human lead's explicit change of the requirement |
| REFERENCE NOT RUNNABLE LOCALLY | That reference cannot be measured on this stack and machine within the registered limits | That it leaves the reference set |
| Every part evaluable, teachers ahead, complementary, gate affordable | The ladder may proceed to the specification of M1a | Any progress toward parity. Capability parity of ArborLM is untested. Anything about code writing |

## 16. Open choices reserved for the human lead

Each is his. None is taken by approving this specification under the delegation. Numbers 1 to 12 keep their numbers from draft 1.

1. **Model list.** (a) Set B; (b) set A; (c) set C (not recommended); (d) another list. No recommendation between A and B (section 4.2). With it: S₀ = the smaller model (recommended) or the sibling; the stored-bytes bound = the sibling's bytes (recommended); the active-compute bound = 1.25 × S₀, counted as section 4.3 defines (recommended); whether "family" means the release series (recommended) or every small Qwen model.
2. **Domain list and gate candidates.** (a) **The five rows of section 6.8 (recommended)**, with code tracing named as such and code writing NOT MEASURED; (b) without mathematics as its own domain (M1 then sits under reasoning); (c) with code writing by execution, which needs choice 6; (d) further domains by amendment before the freeze: multilingual ability, which ADR-0032 E1 item 3 recommends (candidate public sets, [D] UNVERIFIED, the reviewer's memory: MGSM, XNLI, Belebele), instruction following (IFEval, [D] UNVERIFIED), a narrow private language set (section 6.6). Each needs its licence re-read at D0b.
3. **Margins δ_e.** (a) **Fix δ_e per evaluation before stage R1, i.e. before any model scores any item. If he has not fixed it, R1 waits (recommended; ADR-0032's own recommendation, E1 item 2)**; (b) fix them after M0, knowing the references' gaps, which Review 2 called a researcher degree of freedom. Either way M0 reports the grid.
4. **Decision 2**, the registered measurement.
5. **Budget ceilings:** 72 hours per reference, 168 hours in all, 48 hours of rehearsal, 336 hours for the M5 projection flag (recommended as proposed).
6. **Starting Docker (Colima)** or another container tool, for C2 only; what it would need is in section 6.3. Recommended: not in M0.
7. **ANLI's non-commercial licence** for local research use. Recommended: accept; without it L1 is smaller and more likely underpowered.
8. **How the models are run:** (1) a lockfile amendment; (2) a separate hash-pinned file; (3) **re-implementation in plain torch on the locked environment, verified once against the library (recommended, with its cost: section 5)**. The lead cannot take this choice.
9. **Floor and ceiling:** the band 0.10 and 0.90, and reading it per pair (recommended, with the rule that such a pair cannot pass) or per evaluation as ADR-0032 words it.
10. **Every number of section 14**, among them: **G, at least 300 clusters per part, before the generators are frozen**; the sealed pool size, 20,000 per part; alpha 0.05, power 0.8, the cap fraction ½, which ADR-0032 already lists as his.
11. **A model that needs repository code**, if the gate finds one. Recommended: none.
12. **The smaller design** of section 11. Recommended: no.
13. **System message (new; Review 1, C2).** (a) Each template's own default (as drafted); (b) one identical neutral system message for every model, which replaces Qwen's default persona and makes the prompts more nearly identical. Whichever is not the rule is measured as a nuisance variation. No recommendation from the reviewer; the drafter's is (a), because ADR-0032 section 4 names each model's published template.
14. **The WikiText-2 bytes (new; Review 1, R10).** 7,030,741 bytes fetched on 2026-11-12, before the ledger began, with no row. Do they count against the 50 GB? Recommended: count them; it costs nothing.
15. **Retention tests in the M5 conjunction (new; Review 1, C8; PENDING LEAD REVIEW).** Recommended, the reviewer's reading: if M5 scores retention on sealed splits, those tests join the conjunction, and the sealed sizes may only rise for it.
16. **NO HARM where S₀ is at floor (new; Review 1, C10; PENDING LEAD REVIEW).** Recommended, the reviewer's reading: the test stays in the gate, and every line that prints it on such a part says it is nearly vacuous there.
17. **When composition items are frozen (new; Review 1, R15).** (a) Before any S is trained, that is before M1b (recommended; ADR-0032 section 7 says "before S exists"); (b) before any S taught by both teachers exists, that is before M4.

**What the drafter could not settle from the records:** whether the pinned library loads every model of the chosen set with built-in classes; whether torch 2.8.0 runs them in bfloat16 on MPS; whether greedy generation on MPS repeats exactly; any generation rate on this stack; τ, the between-cluster spread that decides whether G = 300 is enough; whether 300 distinct rule shapes per part can be written for every private evaluation; the SuperGLUE per-task licences.

## 17. Decisions and approval record

**What the lead may do under the weekend delegation** (`docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md`), only after the auditor's review, with any choice taken against the reviewer's advice reported first:

- approve this SPECIFICATION as a specification;
- take **Decision 1, limited to locked-environment implementation**: stage I0-a and stage G-gen (the latter as section 13 limits it).

Decision 1 takes none of the choices of section 16. It covers D0b, G-load, R1, R2, R3 and F only after the human lead has given every choice of section 16 that the stage uses (the "Needs" column of section 13 names them). Every number in `configs/m0_reference_models.toml` is a proposal until he confirms it, which he does before F. The human lead may overrule Decision 1 on Monday 2026-11-23. **Not given.**

**Held for the human lead (Monday 2026-11-23 or later), by the stage that waits:**

| Held | Choice | What waits for it |
|---|---|---|
| The package route | 8 | D0a, I0-b: no package is installed, no harness or model code is written |
| The model list, S₀ and the bounds on S | 1 | D0b: no model is fetched |
| The domain list; ANLI's licence; any repository code | 2, 7, 11 | D0b: no dataset is fetched. G-gen's record |
| G, the clusters per part | 10 | G-gen's record: the generators are not frozen |
| The WikiText-2 ledger ruling | 14 | D0b's inventory |
| Starting Colima | 6 | Any image pull; C2 |
| Any model or dataset download | 1, 2, 7 | D0b. Within the standing limit a download needs no further asking once its licence has been re-read at the source, but which models and datasets is his |
| δ_e, per evaluation | 3 | R1: no model scores any item |
| The band; the rehearsal cap; the system message | 9, 5, 13 | R1 |
| Every other config number | 5, 10 | F |
| **Decision 2** | 4 | M. Recorded in `results/m0-freeze-<date>/DECISION_2.md`, after the rehearsal record, the auditor's agree, the implementation audit, the cost projection and the freeze record. **Not given.** |
| Retention in the conjunction; NO HARM at floor; composition timing | 15, 16, 17 | Nothing in M0 waits; they change what M0 prints and what later rungs inherit |

- Grounds stated in advance for not running after Decision 1: an engineering stop of section 10.7, or a projection above a ceiling that he declines to extend. A refusal on another ground is recorded with its reason before any development score is read: NOT RUN (DECISION 2 REFUSED: reason).
- If the independent recomputation disagrees with the frozen analysis, the frozen outcomes are recorded as written with the disagreement beside them; nothing is changed without a recorded amendment.

No approval exists. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 18. What follows M0 (pointer only)

`M0 → M1a → M1.5 → M1b` (ADR-0032, Part D). M1a: with the memory attached and inert, is S identical to S₀; it needs a way to attach the memory to a token-level pretrained model, which does not exist. M1.5: the teaching data and procedure, frozen, drawn only from part A families and checked for overlap with every evaluation, the sealed pools through their fingerprints. M1b: after teaching one narrow capability, is every evaluation within its margin of S₀. Each needs its own specification and approval. None is specified here.

## 19. Where M0 does not satisfy ADR-0032 as written

The last column gives Review 1's ruling on each departure.

| # | ADR-0032 text | What this specification does | Whose call | Review 1 |
|---|---|---|---|---|
| 1 | Section 4: "coding (scored by executing the code)"; "the sandbox is tested with adversarial items before M0 scores anything" | Recommended option executes no model-written code and builds no sandbox. The domain is named code tracing; code writing is NOT MEASURED and any claim about coding reads NOT EVALUABLE (CODE WRITING NOT MEASURED). PB-3 stays undelivered | Human lead (choices 2, 6) | Acceptable with R8 |
| 2 | Section 7: composition items "shown in M0 to be failed by each teacher, by S₀ and by the registered pipeline" | Not in M0. They must be built from what each teacher is better at, which M0 measures first. A supplement after M0, frozen before any S is trained (before M1b), or, if the human lead accepts, before any S taught by both teachers exists (before M4). A seed is reserved | Human lead (choice 17) | Acceptable with R15 |
| 3 | Section 5: power "by simulation from the measured paired item outcomes, not by assuming independence" | Per-test power is simulated at M5's own cluster design. Across tests Boole's bound is used, which assumes nothing about dependence. No joint simulation is possible without S; sizes are recomputed from M1b | Rule approved; this reading follows the review | Draft 1's product bound not acceptable; replaced by B1, R1, R2 |
| 4 | Section 4: "an established public harness at a pinned version rather than bespoke scoring where possible" | Bespoke, with the scorer tested on at least 200 hand-labelled outputs per evaluation and its agreement with the published extraction rules printed for GSM8K and MMLU-Pro. Reasons: the one-system rule needs prompt construction under our control; public harnesses bring many packages and dataset scripts that run code; their support for this stack is UNVERIFIED in note 1 [M] | Lead after review | Acceptable with R7, C3 |
| 5 | Section 4: a private set "where one can be built" | Real-world knowledge cannot be private. For language understanding a private set can be built only as a much narrower construct; not built in M0. Their gate candidates are public items whose exposure cannot be checked, disclosed on every line | Human lead (choice 2) | Acceptable with the rewording |
| 6 | Section 4 margin: recommended that δ_e be fixed "in M0's specification" | This document cannot contain δ_e: it is his and held for Monday. He fixes it before stage R1, i.e. before any model scores any item. If he has not fixed it, R1 waits | Human lead (choice 3) | Acceptable with R3 |
| 7 | Section 4, Tier 2 (c), and "active compute per token" | Under the proposed bound (c) is S₀, by NO HARM, adding no model and no test; S₀ is a parity reference in this role only. S's active compute cannot be measured before M1a; the bound is a defined parameter count used only to choose a reference | Human lead (choice 1) | Acceptable with R14 |
| 8 | Section 4: floor and ceiling per evaluation | Read per (reference, evaluation part); such a pair cannot pass, so PARITY is never easier to print | Human lead (choice 9) | Acceptable with R13 |
| 9 | M0 row: "an amendment to `uv.lock` and `pyproject.toml`" | Three routes are put to him. Any of them is an amendment in substance. Recommended to him: option 3, which needs no change to the lock | **Human lead only (choice 8)** | Not acceptable as something the lead can take; B2 |
| 10 | M0 row and section 9: the cumulative download total "counted and printed" | Printed (1.50 GB, the ledger on `main` being behind), with a clerk inventory gate and the unledgered WikiText-2 bytes put to him | Lead; clerk; human lead (choice 14) | Acceptable with R10 |
| 11 | Section 7: complementarity "for each domain" | Measured per evaluation part; the domain line gives three readings and leaves the choice to section 7's approval | Human lead | Acceptable |
| 12 | Section 4: Tier 2 (b), "the strongest available conventional model of the student's family" | Read as the largest of the same release series under the bound | Human lead (choice 1) | Acceptable |
| 13 | E1 item 3 recommends multilingual ability | Not specified: no evaluation was licence-checked. Candidate public sets exist ([D] UNVERIFIED: MGSM, XNLI, Belebele). The human lead may add the domain before the freeze, with licence re-read at D0b. Instruction following likewise (IFEval, [D] UNVERIFIED) | Human lead (choice 2) | Added by R11 |

## 20. Review record

**Review 1** (`docs/reviews/adr-0033-m0-2026-11-20/REVIEW_1.md`, SHA-256 `f7aef8b81602fd8881c3a1431a1ed600df466250d7bc1be9d066cd794b7c1e6c`; `arbor-auditor`, Claude Opus 5.5) read draft 1 at commit `c89c1f2`. Verdict: READY AFTER THE LISTED EDITS. The scientific lead accepted B1, B2 and R1 to R17 with the reviewer's wording, and C1 to C11. Revision 2 has not been reviewed.

### Review 1 findings and what was done

| Finding | Status | Where; difference if any |
|---|---|---|
| B1 (blocking) simulation at M5's own cluster count | FIXED | Sections 6.2, 9.4, 10.5, 14; choice 10. The reviewer's wording. Added: what G = 300 can and cannot reach (section 8), and the M0 draw balanced over clusters |
| B2 (blocking) the package route is the human lead's | FIXED | The box; sections 5, 13, 17; choice 8; row 9. Option 3 added and recommended to him, with its cost |
| R1 Boole's bound | FIXED | Section 9.4 |
| R2 Monte Carlo counts | FIXED | Section 9.4; section 14 |
| R3 δ_e before stage R1 | FIXED | Choice 3; row 6; sections 6.5, 13, 17 |
| R4 what each stage needs from him | FIXED | Section 13 "Needs"; section 17 table |
| R5 batch sizes and the repeat gate | FIXED, WITH ONE ADDITION | Section 7. The batch rule uses the largest candidate token limit (1,024), because the worked-mode limit of R7 is chosen later, in R1 |
| R6 rehearsal cost; charged hours | FIXED, WITH ONE DIFFERENCE | Sections 7, 11, 14. Public sets also use 50 items for the format choice. The rehearsal cap is proposed at 48 hours, since the corrected estimate reaches 35 |
| R7 one-system fixings; precision fallback | FIXED | Section 7 (eight rows); section 5. Added: the rows' library settings are read as properties of the project's code under option 3; hand labelling runs inside the sealed stage |
| R8 code tracing | FIXED | Sections 6.2, 6.3, 6.8; choices 2 and 6; row 1. What a sandbox would need is listed as his option |
| R9 sealed pools and generators (a) to (e) | FIXED | Sections 6.2 and 8 |
| R10 download count and fetch rules | FIXED | Sections 4.1, 4.2, 5; choice 14 |
| R11 multilingual ability as a departure | FIXED | Section 3; choice 2; row 13 |
| R12 projection systems; UNDERPOWERED parts | FIXED | Section 10.6 |
| R13 floor or ceiling per pair cannot pass | FIXED | Section 10.2 |
| R14 (c) = S₀; the parameter count defined | FIXED | Section 4.3 |
| R15 composition before S exists | FIXED | Row 2; choice 17 |
| R16 NOT RUNNABLE precedence, memory reading, teacher not runnable | FIXED | Sections 9.4, 10.1, 10.4 |
| R17 seeds | FIXED | Section 12: revision 5 cited by hash; the freeze-gate wording replaced and left PENDING LEAD REVIEW |
| C1 sets A and B | FIXED | Section 4.2: the recommendation of B is withdrawn; both presented |
| C2 neutral system message | FIXED | Choice 13; fifth nuisance variation (section 9.3) |
| C3 agreement with published extraction rules | FIXED | Section 6.7; row 4 |
| C4 solver audit by a separate context | FIXED | Sections 6.2, 13 |
| C5 public splits | FIXED | Section 8 |
| C6 memory guard during generation | FIXED | Section 11 |
| C7 attachability | FIXED | Section 4.3 |
| C8 retention tests in the conjunction | PUT TO THE HUMAN LEAD | Choice 15; a placeholder table in section 9.4 |
| C9 item formats | FIXED | Section 6.6 |
| C10 NO HARM nearly vacuous at floor | PUT TO THE HUMAN LEAD | Choice 16; the sentence in section 10.2 |
| C11 sealed archive check | FIXED | Sections 8, 13 |
| Departure 5 rewording | FIXED | Section 6.6; row 5 |

`SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`.
