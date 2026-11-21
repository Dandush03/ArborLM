# ADR-0033 — M0: the reference models and the evaluation harness (first rung of the model-level ladder)

**Status: DRAFT 1. NOT APPROVED. Not yet reviewed. Nothing in this document authorises implementation, a download, a run or a decision. It is a proposal drafted under the scientific lead's brief; the auditor reviews it next.**

- Date: 2026-11-20 (Panama time). Drafted by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`) on the scientific lead's brief. The drafter read records only. It downloaded nothing, ran no model, ran no heavy computation and made no git write.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. This document claims no result. P1 to P10-I, their thresholds, labels, outcome records and rulings stand exactly as recorded. No existing file is edited.
- **What binds this specification.** The five rules of ADR-0032 revision 4, section E2, approved by the lead under the weekend delegation (`docs/reviews/adr-0032-model-level-2026-11-20/APPROVAL_OF_RULES.md`): the two levels of evidence; the margin rule; the power rule; the label structure of sections 5 and 6; the order of the M ladder. The human lead may overrule any of them on Monday 2026-11-23. Everything else in ADR-0032 is a proposal and is treated as one here.
- **Literature.** `docs/reviews/adr-0032-model-level-2026-11-20/LITERATURE_NOTE_1.md` ("note 1") is unreviewed. Its marks are kept: **[V]** a page fetched in that session and read through an automatic summariser; **[M] UNVERIFIED** from its author's memory; **[E]** an estimate. One mark is added here: **[D] UNVERIFIED**, from this drafter's memory. **No number from note 1 has been re-read at its source for this draft.** Every one is re-read at the source before it is used (section 13, stage D0); none is a fact of this specification until then.
- **[KNOWN].** Nothing about any candidate model has been measured in this project. No rule below was written after seeing a score. What could have shaped the design is note 1 only.

> **For the human lead.**
> - **What M0 is.** Groundwork with no ArborLM component in it. It measures the pretrained models themselves, the small student and the larger models it would be compared with, on evaluations built for the purpose. It contains no memory code and says nothing about ArborLM.
> - **What it can tell you.** How each model scores here, on this machine and software. Whether each teacher is ahead of the student, and where. Whether the two teachers differ item by item, which the two-teacher question needs. How many test items the parity gate needs for a margin of 2, 3 or 5 points. Whether that gate is affordable on this machine.
> - **What it cannot tell you.** Anything about ArborLM. Whether parity is reachable. Anything about cost or efficiency of a memory.
> - **Expectation, not a measurement.** The teachers will most likely be ahead of a 0.5B student almost everywhere. Whether the two teachers complement each other is open. The gate will most likely need several thousand sealed items per evaluation, and the final test (M5) may project to one or two weeks of machine time or more.
> - **Cost.** About 41 GB of downloads in total after M0 with the recommended set (limit 50 GB; 1.50 GB already used, not 1.19: section 4.1). One to four days of machine time for the registered measurement, uncertain by a factor of about three until it is timed here (section 11).
> - **Yours alone (section 16):**
>   1. **The model list**: which set, which model is the student S₀, the upper bounds on the size of the student plus memory. Recommended: set B (Qwen2.5 0.5B student, Qwen2.5 1.5B as the equal-bytes reference, Qwen2.5 7B and GLM-4-9B-0414 as teachers).
>   2. **The domain list** and which evaluations may gate. Recommended: reasoning, mathematics, coding (read as code tracing, no model-written code executed), language understanding, factual knowledge.
>   3. **The margins δ_e**, per evaluation, and the other numbers inside the rules (alpha, power, the cap fraction, the floor and ceiling band, the sealed pool size). Recommended: fix δ_e before Decision 2; until then nobody sees a score. The others as proposed.
>   4. **Decision 2**: the registered measurement. Held for you on Monday 2026-11-23.
>   5. **Budget**: the hour ceilings of section 14, and whether to take the smaller design of section 11 (recommended: no).
>   6. **Starting Docker (Colima)**, only if you want code generation scored by execution inside M0. Recommended: not in M0.
>   7. **Non-commercial benchmark licences** (ANLI), a lockfile amendment if you prefer one, and any model that needs repository code to load. Recommended: accept ANLI for local research; no amendment; no repository code.
> - **What the lead may do under your weekend delegation, after the auditor's review, and nothing more:** approve this specification for implementation and rehearsal; install the Python packages (about 0.15 GB). **No model and no dataset is downloaded before your model list and domain list**, because the download budget can be spent only once (section 4.1).

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
| Execution of model-written code (recommended option) | Needs a container; Docker (Colima) is stopped on this machine by the human lead's permission and starting it is his call (section 6.3). |
| Composition items of ADR-0032 section 7 | They need M0's own result first (section 19, item 2). A later supplement with its own approval. |
| Multilingual ability, long context, calibration, instruction following | No licence-checked evaluation is in note 1 for them. Not specified. The human lead may add a domain before the freeze, by an amendment and a review; never after. |
| Quantised or converted checkpoints, other stacks | One stack, one precision. No cross-check stack is specified in M0. |
| Thinking modes | Off for every model that has one (section 7). The recommended set has none. |

## 4. Models

### 4.1 Precondition: the cumulative download total (ADR-0032, Review 2 G12)

Limit: the standing delegation of 50 GB in total (50,000,000,000 bytes; `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` cites it; the ledger's own header still states the earlier 30 GB of 2026-11-15).

| Item | Bytes | Source |
|---|---|---|
| Ledger on `main` (`docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`) | 1,188,183,868 | read |
| **The same ledger on branch `claude/p10-i-s6-impl`, commit `aa41a62` (two WikiText-103 shards, not yet on `main`)** | **1,502,260,446** | read with `git show` |
| **Total already downloaded, used here** | **1,502,260,446 (1.50 GB)** | the larger of the two |

The ledger on `main` is behind by 314,076,578 bytes. The brief's figure of about 1.19 GB is the `main` figure. Whether any other branch or worktree holds a fetch with no ledger row was not checked by the drafter. **Gate at D0:** `arbor-clerk` inventories every branch's ledger and the git-ignored `data/` directories; M0's first ledger row starts from the inventoried total, and a discrepancy is an engineering stop.

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

Rules. (1) The fetch code refuses any fetch that would take the cumulative total above 50,000,000,000 bytes. (2) M0's own ceiling is the planned cumulative total of the chosen set plus 1 GB (for set B without an image: 42,000,000,000 bytes); a plan above it is not started and returns to the human lead. (3) The cumulative count never goes down: deleting a file refunds nothing. **This is why no model is fetched before the human lead's model list: after one set is fetched, no second set fits.**

### 4.2 Candidate sets (from note 1, section 4; nothing re-read)

| Set | Student S₀ | Sibling | Qwen teacher | GLM teacher | Remarks from note 1 |
|---|---|---|---|---|---|
| **B (recommended)** | `Qwen/Qwen2.5-0.5B-Instruct`, 494,032,768 parameters, 0.99 GB [V] | `Qwen/Qwen2.5-1.5B-Instruct`, 1,543,714,304, 3.09 GB [V] | `Qwen/Qwen2.5-7B-Instruct`, 7,615,616,512, 15.23 GB [V] | `zai-org/GLM-4-9B-0414`, 9,400,279,040, 18.80 GB [V] | Text only; no thinking mode; most mature tooling |
| A | `Qwen/Qwen3-0.6B`, 1.50 GB [V] | `Qwen/Qwen3-1.7B`, 4.06 GB [V] | `Qwen/Qwen3-8B`, 16.38 GB [V] | the same | Text only; has a thinking mode [M] |
| C | `Qwen/Qwen3.5-0.8B`, 1.75 GB [V] | `Qwen/Qwen3.5-2B`, 4.55 GB [V] | `Qwen/Qwen3.5-9B`, 19.31 GB [V] | the same | Multimodal; thinking on by default on the 9B; cards require a library version from the main branch [V] |

Licence tags per note 1: the Qwen candidates Apache-2.0 (tag and card only; **the LICENSE files were not opened**); GLM-4-9B-0414 MIT (LICENSE file opened) [V]. The older GLM-4 9B and GLM edge models carry a custom licence with a naming clause [V, through a summariser] and are not candidates.

**Revisions.** Note 1 gives commit prefixes only (for example `7ae55760…` for the 0.5B student) [V]. They are pointers. At D0 each repository is pinned by its full 40-character commit and each file by the SHA-256 of its LFS metadata, written to a ledger row before the fetch and verified after it. Only `.safetensors` weights, `config.json`, `generation_config.json`, tokenizer files and the LICENSE are fetched. No pickle file is loaded.

**Recommendation: set B.** Reasons:

1. It leaves the most room under the limit (9.2 GB), and later rungs will need some.
2. No thinking mode to register, which removes one nuisance dimension and a 5 to 20 times cost factor (note 1 [E]).
3. It needs no library outside versions already resolved and hashed in this repository (section 5). Set C does.
4. The two teachers are closest in age (repository commits dated 2025-01 for the Qwen teacher and 2025-04 for the GLM teacher in note 1 [V]; a commit date is not a release date). In set C the Qwen teacher is a generation newer than the only feasible GLM teacher, which makes NO COMPLEMENTARITY more likely (note 1's own remark [E]).

Its weakness, for the human lead to weigh: it is the oldest set. Parity against 2024 models is parity against older references. Whether those are "the conventional models it aims to replace" is his judgement.

### 4.3 The reference set and the upper bounds on S (ADR-0032 section 4; Review 2 G2)

| Role | Recommended (set B) | Standing |
|---|---|---|
| S₀, the candidate student | `Qwen2.5-0.5B-Instruct` | Measured; not a parity reference |
| Tier 2 (a), teachers | `Qwen2.5-7B-Instruct`; `GLM-4-9B-0414` | Parity references |
| Tier 2 (b), equal stored bytes | `Qwen2.5-1.5B-Instruct` | Parity reference |
| Tier 2 (c), nearest active compute | The S₀ checkpoint itself (see below) | Already covered by NO HARM; no further model |

**Upper bound on stored bytes (can be registered now).** S (student, memory, router, adapters, everything it needs at inference) may not exceed the byte size of the sibling's weight files at the pinned revision: about 3.09 GB [V], the exact number filled in at D0 from the listing. That allows the memory about 2.1 GB beyond a 0.99 GB student [E]. Reference (b) is then the sibling: the largest model of the same release series at or under the bound.

**Upper bound on active compute (registered now as a count; its measurement on S is deferred to M1a).** S may read, per generated token, at most 1.25 times the number of parameters S₀ reads. Under this bound the model of the series with the nearest active compute is the S₀ checkpoint (the next one, the sibling, is 3.1 times S₀ by parameter count [E from V]). So reference (c) is S₀, whose comparison is the NO HARM test, and (c) adds no model. This count is a rule for choosing a reference. It is a logical count and supports no efficiency statement. How S's reads are counted is specified in M1a, and S is shown to be under both bounds before it is scored.

**Why S₀ is the smaller model.** It leaves the sibling as the equal-bytes reference inside the download budget, and it is the cheapest to carry through M1 to M5. Against it: a 0.5B model is the farthest from the teachers. Option: S₀ = the 1.5B model; then (b) needs a model of about 3B, which note 1 recalls as carrying a non-commercial licence [M] and which does not fit the budget beside the rest. Not recommended.

**What is deferred.** Reference (b) rests on reading "the student's family" as the same release series. If the human lead reads it as every small Qwen model, a newer model under the bound (`Qwen3-0.6B`, 1.50 GB [V]) is a further candidate for (b); it fits the budget (cumulative 42.3 GB) and is his to add before the freeze. No larger reference can be fixed now.

**The set may not be reduced after M0** (ADR-0032 section 4). A reference found NOT RUNNABLE LOCALLY stays in the set; its comparisons are NOT EVALUABLE LOCALLY.

## 5. Inference stack

**Stack of record: PyTorch on MPS, the checkpoint's published half precision, unquantised, the same for every system.** This is where M1 would attach a memory with gradients. Platform of record: macOS arm64, Apple M5 Max, 18 cores, 48 GB (read from the machine), `torch==2.8.0` as locked.

**Precision order, fixed now.** (1) bfloat16 on MPS. (2) If any model of the set fails the load gate in bfloat16 (an unsupported operator, a non-finite value), float16 on MPS for **every** system. (3) No further fallback: float32 does not fit a 9B model beside other work, and CPU is too slow. A model that passes neither is REFERENCE NOT RUNNABLE LOCALLY (PRECISION). The precision is settled at the load gate, before any tuning score. CPU fallback for unsupported operators is off (`PYTORCH_ENABLE_MPS_FALLBACK` unset). Whether torch 2.8.0 runs these models in bfloat16 on MPS is not known to the drafter [D] UNVERIFIED; the gate decides.

**Packages beyond the lock.** The locked environment has `torch` and `psutil` only. M0 needs model loaders and tokenizers:

| Package | Proposed pin | Why |
|---|---|---|
| `transformers` | 4.57.1 | Model classes, chat templates, generation |
| `tokenizers` | 0.22.1 | Tokenizers |
| `safetensors` | 0.6.2 | Weight files |
| `huggingface-hub` | 0.35.3 | Imported by `transformers`; used offline only after D0 |
| `numpy` | 2.3.3 | Imported by `transformers`; bootstrap arithmetic |
| resolver dependencies (`regex`, `pyyaml`, `tqdm`, `requests` and theirs) | as resolved | — |

These five pins are the versions already resolved, hashed and installed once for P10-S2 (`studies/p10s2/requirements-datagen.txt`, read by the drafter). `jinja2`, which chat templates need, is expected in the lock as a dependency of `torch` [D] UNVERIFIED; the resolution checks it. Whether `transformers` 4.57.1 has built-in classes for every model of set B (the Qwen2 class; a GLM-4 class) is [D] UNVERIFIED and is gated at D0 before any weight is fetched. `accelerate` is not listed; if the load gate shows it is needed to hold peak memory, it is added to the same file before the freeze. `pyarrow` (dataset files) comes from the lock's existing `pilot` extra.

`uv.lock` and `pyproject.toml` do not change without an approved amendment (CLAUDE.md). Two ways:

| Option | For | Against |
|---|---|---|
| 1. An approved amendment to `uv.lock` and `pyproject.toml` | One environment for M1, where the memory and the model run in one process | Both files are frozen inputs, by hash, of studies that are frozen or running; an amendment on `main` touches all of them. Needs the human lead |
| **2. A separate hash-pinned file (recommended)** | The lock is untouched. Done once already, with an audit (P10-S2) | A second environment to keep identical in M1 |

**Recommended: option 2**, as P10-S2 did it: `studies/m0/requirements-m0.txt`, resolved with `uv pip compile --generate-hashes` at a fixed `--exclude-newer` date, every package shared with `uv.lock` constrained to the lock's version; installed with `uv pip install --require-hashes --target <git-ignored directory>` by a launch script that verifies the install; put on the path of M0 processes only. The file's SHA-256 is a frozen input. **Condition carried to M1:** M1 uses the same resolved versions, by whichever route; if any differs, the references are measured again before S is scored.

**Repository code.** Loading a model may never execute code from its repository. `trust_remote_code=False` is passed explicitly everywhere. Before any weight is fetched, `config.json` (a few kilobytes) is fetched at the pinned revision and checked: its `model_type` must be a class built into the pinned library, and it must have no `auto_map`. A model that fails is not downloaded; it is recorded as REFERENCE NOT RUNNABLE LOCALLY (NEEDS REPOSITORY CODE) and returns to the human lead. He alone may approve one specific revision, after the code has been read and its hash recorded.

**Network.** Used in stage D0 only. Every later stage runs with `HF_HUB_OFFLINE=1` and loads from local paths. The `datasets` library is not used (it can run dataset scripts); dataset files are fetched as files at a pinned revision and read with `pyarrow` in `-I` mode from their own directory.

**Harness.** Bespoke, small, and tested on hand-labelled items. ADR-0032 prefers an established public harness "where possible"; the reasons for not taking one are in section 19, item 4.

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
| C1 | Coding | Output prediction. Small deterministic Python programs from a typed grammar: arithmetic, strings, lists, loops, conditionals, small functions. No imports, no input, bounded loops. The question is the printed value | The program is run in the locked interpreter, twice, in a fresh restricted process with a time limit. It is our generated code, not model-written | worked |

Requirements for each:

- **Families and clusters.** At least 12 template families, each a distinct rule structure with its own surface frames. At least 60 clusters (a cluster is one template: a family, a rule shape and a surface frame) in each evaluation part. Families are strata; templates are clusters (ADR-0032 section 5).
- **Difficulty.** Five registered levels (depth, steps or program size), and two reserve levels, one easier and one harder, implemented before any scoring.
- **Validity gates, no model involved.** Both solvers agree on every item. Items are unique after normalisation. `arbor-auditor` reads 50 rendered items per evaluation for ambiguity and records what it finds. Templates are written by an agent; their answers are computed by rule.
- **Interior check.** Section 6.5.
- **Stated limit.** A generated set measures a narrower construct than a human-written benchmark. Private and public scores are printed side by side and never pooled.

### 6.3 Coding: what is measured, and execution

**Recommended for the gate: output prediction (C1), scored by string comparison.** No model-written code is executed anywhere in M0. The answer is the text after the registered answer marker, normalised, compared with the expected printed value.

This is not what ADR-0032 section 4 words as "coding (scored by executing the code)". C1 measures tracing and understanding code, not writing it. That narrowing is the human lead's to accept (section 16, choice 2).

**Option, his call: code generation scored by execution (C2).** Generated function specifications with reference solutions and generator-made tests; public beside it: HumanEval+ (164 items, Apache-2.0) and MBPP+ (378, Apache-2.0) [V]. It needs a sandbox, specified now so that it is not improvised later:

- a container or lightweight virtual machine; no network; non-root; read-only root filesystem; a size-limited scratch directory; CPU, memory, process and wall-time limits; no host mount except the per-task input; a fresh container per batch; the image pinned by digest and counted in the ledger;
- generation first, execution later from stored records;
- tested with adversarial items (network access, file writes outside scratch, fork bombs, long sleeps, large allocations) before any model-written line is run; a failed test is an engineering stop.

Docker (Colima) is currently stopped on this machine by the human lead's permission. Starting it, or using another container tool, is his decision. Without it C2 is NOT MEASURED IN M0 and coding by execution has no gate candidate until a later decision.

### 6.4 Generalisation: what M0 reserves

Generalisation is a split, not a domain, and it can be defined only when a teaching procedure exists (M1.5). M0 reserves what cannot be reserved later:

1. **The family partition.** At the freeze, a registered seed splits the families of each private evaluation into **part A** (teaching may draw on these families) and **part B** (held out: no teaching item, template or family of part B may ever be used for teaching). Half each. Fixed before any score, so that no result can shape it.
2. **Both parts are measured in M0**, separately, so that the power sizes exist per part.
3. **Public sets.** Their training splits are not downloaded and not used by M0. Whether a public evaluation counts as in-teaching or out-of-teaching is settled in M1.5; M0 records that nothing from them has been used.
4. **Seeds** for the M5 sealed draw and for the composition supplement (section 12).

### 6.5 Keeping difficulty off floor and ceiling

On a **tuning draw** (its own seed; 100 items per level and part), every system is scored. A code rule then fixes the mix of levels for each private evaluation part:

- candidates: every contiguous range of levels, uniform over the range;
- chosen: the range that maximises the smallest distance of any Tier 2 reference's tuning score from the band edges of section 10.2; ties to the wider range, then to the lower start;
- if no range puts every Tier 2 reference inside the band, the two reserve levels are scored once and the rule is applied again; nothing else changes.

If the best range is still outside the band, the part is flagged CALIBRATION NOT INTERIOR. It enters the registered measurement with that range, and its registered outcome is read on the development draw. No generator is rewritten after a score exists. Tuning scores are sealed (section 8); the public record holds the chosen range and a yes or no.

### 6.6 What cannot be generated privately, and what is done instead

| Domain | Why not | Instead |
|---|---|---|
| Language understanding | Natural text and its meaning cannot be produced by rule without a model in the loop, and a model in the loop would favour its own family. Rule-made minimal pairs would be a different, much narrower construct | **L1, a pooled public evaluation**, licence-confirmed tasks only: ANLI test (3,200, CC BY-NC 4.0) and SuperGLUE validation tasks (BoolQ 3,270; MultiRC 4,848; ReCoRD 10,000; WiC 638; RTE 277) [V for sizes; the SuperGLUE per-task licences are UNVERIFIED]. At most 4,000 items per task by a registered draw. Strata: tasks. Clusters: passages or premises. A task enters only if its own licence is re-read at D0 and allows local research use |
| Factual knowledge of the real world | Real facts are public by nature | **K1**: MMLU-Pro test (12,032 items, ten options, MIT) [V]. **K2**: PopQA (about 14k entity questions; MIT per its GitHub repository, no licence on the dataset card) [V], scored by its alias-match rule |

For these two domains the gate candidates are public items. Whether a reference saw them in training cannot be checked. It is disclosed on every line that uses them.

**Reserved, not an evaluation of the battery: K0, fictitious facts.** Invented entities and facts, generated privately. Every model should be at chance on them. M0 scores 500 development items once to check exactly that; a system above the floor band flags GENERATOR GUESSABLE (the items leak their answer). The generator is the look-up teaching material M1.5 and M2 will need.

### 6.7 Public sets printed beside the private ones (never gated alone, never pooled with them)

| Set | Items | Licence | Note |
|---|---|---|---|
| GSM8K test (`openai/gsm8k`) | 1,319 | MIT | [V]; heavily exposed [V] |
| BIG-Bench Hard, from its GitHub source | 6,511 over 27 tasks | MIT per the GitHub repository; the mirror states none | [V]; fetched from the source, not the mirror |
| CRUXEval, output-prediction half (`cruxeval-org/cruxeval`) | 800 functions | MIT | [V] |

Dataset commit prefixes in note 1 are pointers; full revisions and file hashes are pinned at D0. Every licence is re-read at its source before the fetch. A set whose licence cannot be confirmed is not fetched and is listed as NOT MEASURED (LICENCE).

### 6.8 Domain list as proposed

| Domain | Gate candidates | Printed beside |
|---|---|---|
| Reasoning | R1, R2 | BIG-Bench Hard |
| Mathematics (a candidate addition in ADR-0032; recommended) | M1 | GSM8K |
| Coding, read as code tracing | C1 | CRUXEval output prediction |
| Language understanding | L1 (public) | — |
| Factual knowledge | K1, K2 (public) | K0 as a floor check |

The domain list is the human lead's. Removing a domain removes its rows. Adding one needs an amendment before the freeze.

## 7. One system rule (for every reference alike)

Fixed before any tuning score, in a record whose hash enters the freeze:

| Item | Rule |
|---|---|
| Chat template | Each model's own published template, from its tokenizer files at the pinned revision, with one user message and the generation prompt added. No system message is supplied; where a template inserts its own default system text, that is kept. The rendered text of one fixed example per model is recorded and hashed |
| Prompt | The same instruction text and item text for every system. Zero-shot. No few-shot examples from any evaluation |
| Candidate formats | Three per response mode, differing in instruction wording and answer-marker convention. Their exact texts are written and hashed before any model is run |
| Format choice | Per evaluation, on tuning items only, by code: the candidate with the smallest largest format-failure rate across systems; ties to the higher mean accuracy across systems, then to the lowest index. Public sets give up 150 items of their development split as tuning items for this |
| Decoding | Greedy: no sampling, one beam, repetition penalty 1.0, for every system, overriding each model's own generation defaults. This departs from the sampling some vendors recommend (note 1 [V] for the Qwen3.5 cards) and is disclosed |
| Thinking mode | Off, through the model's documented template switch, for every model that has one. A model that cannot turn it off is not specified here |
| Stop | The model's end-of-sequence tokens (listed per model) or the token limit. No other stop string |
| Token limit | Direct mode 32 new tokens. Worked mode 384 new tokens |
| Prompt length | An item whose prompt exceeds 2,048 tokens under any system's tokenizer is excluded for every system, before scoring; the count is printed |
| Answer extraction | The text after the last answer marker on its own line; trimmed; case-folded; whitespace collapsed; a final full stop removed; numbers compared as decimals after removing thousands separators; multiple choice as one letter. No extractable answer scores 0 and is counted as a format failure; a limit reached without an answer scores 0 and is counted separately |
| Batching | Left padding; batches formed by a stable sort on prompt length; batch size per (model, mode) fixed in the plan after the measuring rehearsal |
| Samples | One greedy output per item |

Response mode per evaluation: worked for R1, R2, M1, C1, GSM8K, BIG-Bench Hard and CRUXEval; direct for L1, K1, K2 and K0.

**Repeat identity gate.** For each model and mode, 64 tuning items run twice at the registered batch size must give identical token sequences. A failure is an engineering stop (NON-DETERMINISTIC STACK), resolved by an amendment before the freeze.

## 8. Splits and seals

| Split | Size | Who scores it |
|---|---|---|
| Tuning draw (private) | 100 items per level and part | Rehearsal stages only; scores sealed |
| Development pool (private) | 4,000 items per evaluation part, generated and hashed at the freeze | M0 scores a registered 1,500 of them (the M0 draw). The other 2,500 stay unscored for M1 to M4 |
| Development split (public) | One third of the clusters by a registered seed, at most 1,650 items (150 tuning, 1,500 scored) | M0 |
| Sealed pool (private) | **20,000 items per evaluation part**, the registered maximum | **Nobody in M0.** M5 draws its sealed split from it |
| Sealed part (public) | The rest of each public set | Nobody in M0 |
| K0 | 500 development items; a sealed pool of 20,000 | M0 scores the 500 |

**M0 scores development items only.** Every registered outcome of M0 is defined by ADR-0032 on the development split, so none needs a sealed item. M5 remains the only reader of the sealed pools. The price, stated: M0 cannot confirm that a sealed pool is interior or has the same disagreement rate as the development draw. It has the same frozen generator, level mix and families, and that is all that is known. A sealed split later found at floor or ceiling is NOT EVALUABLE and is never re-drawn.

**Why 20,000.** The drafter's arithmetic [E], product bound of section 9.4, 55 to 70 tests in the conjunction: about 18 to 19·d/δ² items per part, so about 6,400 at d = 0.3 and δ = 0.03, and about 14,300 at δ = 0.02. 20,000 covers δ = 0.02 up to d of about 0.42. The size is the human lead's to change before the freeze; it may be raised later, never lowered (ADR-0032 section 5).

**How the sealed pool is made.** A dedicated stage at the freeze generates it from the registered sealed-pool seed combined with a secret salt (32 random bytes drawn at that moment). The pool and the salt are written outside the repository, with read permission removed. The repository receives only: the pool's SHA-256, the salt's SHA-256, item counts per family and level, and the results of the checks. The checks run inside that stage with no model: solver agreement, uniqueness, and no exact or normalised match with any tuning or development item. Revealing the salt at M5 lets anyone regenerate the pool and check the hash. No sealed item is tokenised, loaded beside a model or printed.

**Sealed scores during M0.** Tuning scores go to a sealed archive outside the repository; the public rehearsal record holds only formats chosen, level ranges chosen, yes or no flags, format-failure rates and timing. `arbor-auditor` verifies the sealed archive by agree or disagree. Development scores are read once, in the analysis stage.

**What the seals are.** Everything runs under one operating-system account. Removing read permission, keeping files outside the repository and sealing archives stop accidents and tooling. They do not stop a process or a person using that account. **The seals are procedural, not enforced.** A second account would need administrator access, which only the human lead can grant (ADR-0032, E1 item 20).

## 9. Statistics

### 9.1 Measured on the M0 draw, per evaluation part

1. **Score** of each system, with a two-sided 95 % interval.
2. **Paired difference** for every pair of systems, with its interval; for (reference, S₀) also the one-sided lower 95 % bound L.
3. **Discordance** for every pair: the share of items on which exactly one of the two is right, and its two directions.
4. **Union of the teachers:** U, the share of items at least one teacher gets right; B, the better teacher's score; G = U − B.
5. **Format failures and limit hits** per system.

Subcategory scores (per family, per task) are printed and enter no outcome.

### 9.2 Intervals

Paired on identical items. Cluster bootstrap, stratified by family or task, 10,000 resamples, registered seed, percentile bounds. G is recomputed in every resample, including which teacher is the better one, so that choosing the better teacher on the same data is inside the bound. With fewer than 30 clusters: the cluster-robust standard error with a t quantile on (clusters − 1) degrees of freedom replaces the percentile bootstrap.

### 9.3 Nuisance spreads (descriptive only)

On the first 150 M0-draw items of each evaluation, by a registered order, each system is run again under one change at a time:

| Variation | Change |
|---|---|
| Format | Each of the two candidate formats not chosen |
| Sampling seed | The vendor-style sampling setting (temperature 0.7, top-p 0.8) with two registered seeds |
| Answer order | Options permuted by a registered seed (multiple-choice evaluations only) |
| Batch | Batch size 1 |

Printed per system and evaluation: the share of items whose score flips, and the change in score. They enter no outcome, no margin and no sample size. Their use is ADR-0032's: to show that the fixings matter, and to stand beside later item-level regression counts. With 150 items they are rough.

### 9.4 Sizes for the power rule

M0 does not set δ_e. It reports, for each candidate margin δ in the **registered grid {0.02, 0.03, 0.05}** (and any value the human lead adds before the freeze):

- **d_e**, per evaluation part: the largest discordance between S₀ and any Tier 2 reference (ADR-0032 section 5, item (i)), and the pair that gives it.
- **Per-test power by simulation from the measured paired outcomes.** For that pair and a candidate size n: 2,000 simulated samples, each drawn by stratified cluster resampling with replacement up to n items. In each, the mean difference is recentred to zero (the true difference of the rule) and it and its cluster-robust standard error are scaled by √(d_e / (d_e − μ²)), μ being the measured mean difference, so that the variance is the one a zero difference would have at discordance d_e. The simulated test passes if the estimate minus 1.645 standard errors is above −δ. π_e(n, δ) is the share that pass.
- **The conjunction.** Each evaluation part carries m tests: one per Tier 2 reference, one NO HARM test, and one interference test (ADR-0032 section 7 says these join; a second table omits it). With P gate-candidate parts, the size required is the smallest n on the ladder {500, 1,000, 1,500, 2,000, 3,000, 4,000, 6,000, 8,000, 12,000, 16,000, 20,000} with π_e(n, δ)^m ≥ 0.8^(1/P). Alpha 0.05 and power 0.8 are ADR-0032's proposed values.
- **Confirmation.** At the size found, 500 simulations with the full percentile bootstrap inside; both figures are printed.

**What this is and is not.** The per-test power is simulated from measured pairs, keeping the pairing and the clusters. The combination across tests is a product, because no S exists to simulate the tests jointly. Tests that share S's answers are expected to be positively dependent, which makes the product a lower bound on the true power, so the sizes err on the large side. The auditor is asked to check that argument. From M1b on, with S's own development outcomes (item (ii) of the rule), the conjunction is simulated jointly and the sizes may only rise.

Also printed, per (reference, evaluation part, δ): **CAP MET** if δ ≤ L/2, otherwise **CAP NOT MET** (ADR-0032 section 4). A flag; it moves no margin.

## 10. Registered outcome rules

All on the M0 draw. Read in this order. Scores are point estimates on 1,500 items unless a bound is named.

### 10.1 REFERENCE NOT RUNNABLE LOCALLY (named reference, cause)

Exactly one of:

| Cause | Rule |
|---|---|
| NEEDS REPOSITORY CODE | The check of section 5 fails |
| PRECISION | The model passes the load gate in neither precision of section 5 |
| MEMORY | In the load gate at batch size 1 the process's peak memory (footprint including accelerator allocations) exceeds 34 GiB |
| COST | The measuring rehearsal projects more than the per-reference ceiling of section 14 for its share of the registered measurement, and the human lead does not extend the ceiling at Decision 2 |

Decided before Decision 2, from gates and timing only, never from a score. Its rows read NOT MEASURED. It stays in the reference set.

### 10.2 NOT EVALUABLE (FLOOR OR CEILING)

Chance level c: 1/k for k options, 0 for open answers. Band: from c + 0.10·(1 − c) to 0.90.

- A pair (Tier 2 reference, evaluation part) is **NOT EVALUABLE (FLOOR)** if the reference's score is below the band, and **(CEILING)** if above it.
- The evaluation part is NOT EVALUABLE (FLOOR OR CEILING) if no Tier 2 pair on it is inside the band.
- Printed beside it, entering no outcome: S₀ AT FLOOR or S₀ AT CEILING by the same band.

Reason for 0.10 and 0.90: outside them at most a tenth of the scale is left on one side, and a margin of a few points cannot be told from saturation. They are proposed values and the human lead's to change before the freeze.

### 10.3 TEACHER NOT AHEAD

For teacher T and evaluation part e: T is AHEAD if L, the one-sided lower 95 % bound of (score of T − score of S₀), is above 0. Otherwise **TEACHER NOT AHEAD (T, e)**. A domain reads TEACHER NOT AHEAD if no teacher is ahead on any of its gate-candidate parts.

What follows, registered now: on such a part there is nothing for that teacher to teach S₀; acquisition from that teacher is NOT EVALUABLE there in M2, and coverage (ADR-0032 section 7) is not read there.

### 10.4 NO COMPLEMENTARITY

For evaluation part e and each δ of the grid: the teachers are COMPLEMENTARY if the one-sided lower 95 % bound of G = U − B is above δ. Otherwise **NO COMPLEMENTARITY (e, δ)**. Computed even on a part that is NOT EVALUABLE, and marked so.

Per domain the line reads: COMPLEMENTARY ON EVERY PART, COMPLEMENTARY ON NAMED PARTS, or NO COMPLEMENTARITY. Which of these a superiority claim needs is section 7 of ADR-0032, not approved, and the human lead's.

**What follows if the teachers do not differ, registered now.** The two-teacher test M4 is NOT EVALUABLE (NO COMPLEMENTARITY) for these teachers on those parts. M1a to M3 are single-teacher questions and are not affected. Nothing is substituted inside M0. A different second teacher (note 1 names `GLM-Z1-9B-0414`, 18.80 GB [V]) would be a supplement with its own specification, approval and download decision; with any set it would exceed the 50 GB limit.

### 10.5 NOT EVALUABLE (UNDERPOWERED)

For evaluation part e and each δ of the grid: **NOT EVALUABLE (UNDERPOWERED, e, δ)** if the required size of section 9.4 is above the sealed pool (20,000 for private parts; the fixed sealed part for public ones), or is not reached on the ladder. Never dropped from the conjunction to make the others smaller.

### 10.6 GATE NOT EVALUABLE LOCALLY (PROJECTED)

For each δ: the projected M5 scoring time is the sum over gate-candidate parts of (required size × measured seconds per item), over S₀, every Tier 2 reference, S (at S₀'s rate) and five Tier 1 systems (at S₀'s rate). If it exceeds **336 charged hours** (two weeks), the line reads GATE NOT EVALUABLE LOCALLY (PROJECTED, δ). It is a projection from M0's timing and is labelled so. It is never a reason to widen a margin or drop a reference (ADR-0032 section 9); what to do is the human lead's decision.

### 10.7 Events that are not outcomes

| Event | What it is |
|---|---|
| A gate fails; a hash differs; the repeat identity gate fails; solvers disagree; the registry check fails; a licence cannot be confirmed for a model | ENGINEERING STOP (named). Fixed by an amendment and a new freeze. No registered score is observed |
| An item ends with an error | `item_error`; the analysis refuses; ENGINEERING STOP. Denominators are never reduced |
| A frozen input's hash differs at a stage start | PAUSED — IDENTITY. Restoring the file lets the stage resume |
| A stage reaches a cap | PAUSED. Resumed after an extension decided on projections only; if refused, INCOMPLETE (PAUSED AT CAP) and nothing is labelled |

An engineering stop is never a registered outcome, and a registered outcome is never repaired as if it were a defect.

## 11. Cost and feasibility

**Shared-machine rule.** The machine runs other studies. M0 follows the standing conditions: at most 16 workers across all studies (M0 registers its CPU thread count and counts as that many); its stages pause, or do not start, while another study's quiet-machine stage runs; its own worktree; no write or commit in a worktree whose registered stage is running. Before a model is loaded, free memory must be at least the model's measured requirement plus 4 GiB, or the stage waits with a deadline. One model in memory at a time. M0's load can raise other studies' charged hours; the lead checks their cap margins before a long M0 stage starts.

**No M0 stage needs a quiet machine.** Timing is taken under ordinary shared load on purpose, because later rungs will run that way. Load average and the other study processes are recorded at each stage start. **Every timing figure is measured, in charged seconds on this machine; none is a logical count; none is an efficiency claim.**

**Measuring rehearsal.** For each (model, response mode): whole-process seconds, tokens in, tokens out and peak memory on a registered sample of tuning items, at the chosen formats and batch sizes, through the same launch scripts as the registered run. From it, by code: seconds per item per evaluation, the projection of the whole battery, and the caps (section 14).

**The drafter's own estimate, an order of magnitude only [E].** About 27,000 item scorings per system: 12,000 private, about 6,400 public, 500 for K0, about 8,000 nuisance. About 8 million prompt tokens and about 4 million output tokens per system, nearly all of the output in worked mode. No generation rate has been measured on this stack. Note 1's only throughput figures are a third-party table for another stack at 4-bit precision [V], which Review 2 judged a lower bound of unknown slack. Taking 30 to 100 output tokens per second in aggregate for a 9B model with batching, a teacher needs about 11 to 37 hours, the 1.5B model perhaps 4 to 12, the 0.5B model perhaps 2 to 8. **Registered measurement: of the order of one to four days of machine time; tuning and rehearsals perhaps a fifth more. Wrong by a factor of three in either direction would not surprise the drafter.** The measuring rehearsal replaces every figure in this paragraph.

**A smaller design, for the human lead to weigh:** 1,000 scored items per part and no public reasoning or coding sets. About half the cost. Discordance near 0.3 would be known to about ±2.8 points instead of ±2.3, before any cluster effect [E]. Not recommended, because the saving is small against what the sizes are used for.

## 12. Seeds (proposal; the registry revision and the checker run are the auditor's)

Read against `SEED_REGISTRY_R4.md`, section 5 item 3: the next free data blocks are 310001–319999, then 400001 upward; the next free test ranges are 939001–939999, then 953001 upward. The unapproved draft ADR-0030 proposes the first of each, so M0 proposes the second. M0 trains and initialises nothing, so it needs no initialisation seed.

| Role | Value |
|---|---|
| Tuning draw | 400001 |
| Development pool | 400002 |
| Sealed pool (combined with the secret salt) | 400003 |
| Family partition into parts A and B | 400004 |
| Public development and sealed split | 400005 |
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

Per-evaluation, per-family and per-level streams are derived by SHA-256 of the seed with a text label, never by adding to a seed (registry condition 4.3 item 1). A test asserts it.

**Registry revision needed.** Existing registry files are not edited. The latest addendum in this worktree is revision 5 (`SEED_REGISTRY_R5.md`, untracked, 2026-11-20). M0 needs a new revision 6 by `arbor-auditor` (`SEED_REGISTRY_R6.md` and a new checker file) that allocates the block above, checks it against the whole inventory, and records the earlier files' hashes. Revision 5 reports that its checker fails on `origin/main` for a P10-I-S2 reason; M0's freeze gate needs a checker that passes, run unedited with M0's own file globs. The registry is named for P10-I; whether the M ladder keeps using it is the lead's and the auditor's call. Recommended: yes, because its inventory covers every study.

## 13. Stages, the freeze and engineering requirements

| Stage | Content | Needs |
|---|---|---|
| D0a | Resolve and install the packages, with ledger rows | Decision 1 |
| I0 | Implementation and tests: harness, generators, solvers, scorers, analysis. The pipeline is exercised on a tiny randomly initialised model built in the tests. No download | Decision 1 |
| G-gen | Generator validity gates of section 6.2; the registry check | I0 |
| — | **Held for the human lead: model list, domain list, δ_e** | — |
| D0b | Clerk's download inventory. Each licence re-read at its source and its text hashed. `config.json` check. Then weights and dataset files, one ledger row per file written before the fetch | His model list and domain list |
| G-load | Load without repository code; precision; memory; template rendering; repeat identity | D0b |
| R1 | Tuning: format choice and level ranges, by code; scores sealed | G-load |
| R2 | Measuring rehearsal; caps written by code into the candidate plan | R1 |
| R3 | Counting rehearsal: every registered stage end to end in the dry profile against the candidate plan | R2 |
| F | Freeze: development pools and sealed pools generated and hashed; family partition; every hash; the plan. The freeze refuses unless the committed plan has the hash R3 recorded | R3; the auditor's implementation audit and agree on the sealed archive |
| — | **Decision 2 (the human lead)** | F |
| M | Registered measurement: generate, store raw outputs, score | Decision 2 |
| A | Analysis, once; pure functions over records. Report | M |
| V | `arbor-auditor` recomputes every outcome from raw records with code that imports nothing from the study. The outcome record is written only after that | A |

**Frozen at F, each by SHA-256:** every file under `studies/m0/` except its printing directory; `configs/m0_reference_models.toml`, which holds every threshold, grid, size, limit and seed of this document; `tests/test_m0_*.py`; `studies/m0/requirements-m0.txt`; `uv.lock` and `pyproject.toml` (unchanged); every model file and dataset file; each model's rendered template example; the prompt and format texts; the generators; the development pools; the sealed pools' and the salt's hashes; the public rehearsal record and the sealed archive's hash; the plan. This ADR's hash is recorded for provenance only. A test asserts that every number in this ADR equals the config's value.

**Engineering requirements (the P10-I lessons, as ADR-0031 section 16 lists them):**

1. **Same path.** R1, R2 and R3 drive the same entry point and the same fixed launch scripts as the registered run, one fresh process per stage.
2. **Caps by code.** Cap = charged so far + 2 × projected remaining from R2's record, written into the candidate plan before R3.
3. **Generation and scoring are separate.** Raw outputs (text, token ids, finish reason, timing) are stored first; scoring and analysis are re-runnable from records.
4. **Attempts and waits.** Every refused, failed or discarded attempt is written into the run directory and kept. No wait without a deadline. Nothing is written under `/tmp`; scratch goes to the git-ignored `experiments/_scratch/`.
5. **Tests** do not depend on other studies' files or on the repository's planning state. The analysis is tested on a synthetic registry with a known answer for every rule of section 10, including a case where two systems' records are swapped and the test must fail.
6. **Outputs.** A stage's record is written and closed before any message is printed. Public-output guards do not match inside hashes.
7. **Stops.** Identity failures pause and resume. Code and environment errors are engineering stops.
8. **Checks run locally** (`ruff`, `mypy`, `pytest`); no CI run is required.

**Roles.** `arbor-implementer` writes the code. `arbor-auditor`, in a separate context and from code and records only, writes the second solvers, audits the implementation, verifies the sealed archive, and recomputes the outcomes. `arbor-clerk` inventories downloads and hashes. Which model ran each task is recorded from session metadata. Which agent and model wrote the evaluation code is recorded, so that the teaching code of M1.5 can be written by another context. All are Claude models; they are not independent authors in the strong sense, and that is disclosed.

## 14. Caps and limits

| Limit | Kind | Rule |
|---|---|---|
| Downloads: 50,000,000,000 bytes cumulative; M0 ceiling = the chosen set's planned total plus 1 GB (set B: 42,000,000,000) | Resource cap | Section 4.1. A larger size than listed is an engineering stop |
| Rehearsals R1 to R3: 30 charged hours | Resource cap (proposed) | Extended by the human lead on projections only |
| Registered measurement: by code from R2 | Resource cap | Section 13, requirement 2 |
| **Per-reference ceiling: 72 charged hours** of the registered measurement | Budget ceiling (proposed; his) | Above it: section 10.1, COST |
| **Whole registered measurement: 168 charged hours** | Budget ceiling (proposed; his) | Above it the lead returns to the human lead before Decision 2. The battery is not cut |
| Memory: 34 GiB for the M0 process; 4 GiB free beyond a model's need before loading | Resource cap | Section 10.1, MEMORY; section 11 |
| Sizes: 1,500 scored per part; pools 4,000 and 20,000; nuisance 150; tuning 100 per level | Design ceiling | Not extended after the freeze. The sealed pool may be raised before any sealed score, never lowered |
| Margin grid {0.02, 0.03, 0.05}; alpha 0.05; power 0.8; cap fraction ½; band 0.10 and 0.90; 336 hours | Thresholds (proposed; his) | Fixed at the freeze. Never changed after a score exists |

The registered measurement happens once. No outcome is a reason to add items, formats, seeds or models. A further measurement would be a later study with its own specification.

## 15. What each outcome would and would not mean

| Outcome | Would mean | Would not mean |
|---|---|---|
| Teachers ahead on most parts; COMPLEMENTARY somewhere | The preconditions of M2 and M4 hold on the named parts for these models | Anything about whether a student with a memory can close a gap or combine teachers |
| TEACHER NOT AHEAD on a part or domain | These teachers have nothing to add to this student there, on these items | That the student is good there; that other teachers would not be ahead |
| NO COMPLEMENTARITY | On these items the union of the two teachers is not shown to exceed the better one by the margin. M4's superiority question cannot be asked of this pair there | That teachers can never complement each other; that a single-teacher ladder is blocked |
| NOT EVALUABLE (FLOOR OR CEILING) | That reference, on that part, cannot support a non-inferiority reading | A defect of the model |
| NOT EVALUABLE (UNDERPOWERED) at a margin | The pool cannot support the gate at that margin for that part | A reason to widen the margin; the margin is the human lead's substantive judgement |
| GATE NOT EVALUABLE LOCALLY (PROJECTED) | On M0's timing the final test would exceed two weeks of this machine | A decision. Any reduction of scope is the human lead's explicit change of the requirement |
| REFERENCE NOT RUNNABLE LOCALLY | That reference cannot be measured on this stack and machine within the registered limits | That it leaves the reference set |
| Every part evaluable, teachers ahead, complementary, gate affordable | The ladder may proceed to the specification of M1a | Any progress toward parity. Capability parity of ArborLM is untested |

## 16. Open choices reserved for the human lead

Each is his. None is taken by approving this specification under the delegation.

1. **Model list.** (a) **Set B (recommended)**; (b) set A; (c) set C (needs a library version outside the pins and multimodal checkpoints; leaves 2.9 GB); (d) another list. With it: S₀ = the smaller model (recommended) or the larger; the stored-bytes bound = the sibling's bytes (recommended); the active-compute bound = 1.25 × S₀ (recommended); whether "family" means the release series (recommended) or every small Qwen model, which adds `Qwen3-0.6B`.
2. **Domain list and gate candidates.** (a) **The five rows of section 6.8 (recommended)**, with coding read as code tracing; (b) without mathematics as its own domain (M1 then sits under reasoning); (c) with code generation by execution, which needs choice 6; (d) further domains, by amendment before the freeze.
3. **Margins δ_e.** (a) **Fix δ_e per evaluation before Decision 2, while every score is sealed (recommended; ADR-0032's own recommendation, E1 item 2)**; (b) fix them after M0, knowing the references' gaps, which Review 2 called a researcher degree of freedom. Either way M0 reports the grid.
4. **Decision 2**, the registered measurement.
5. **Budget ceilings:** 72 hours per reference, 168 hours in all, 30 hours of rehearsal, 336 hours for the M5 projection flag (recommended as proposed).
6. **Starting Docker (Colima)** or another container tool, for C2 only. Recommended: not in M0.
7. **ANLI's non-commercial licence** for local research use. Recommended: accept; without it L1 is smaller and more likely underpowered.
8. **Packages:** (a) **the separate hash-pinned file (recommended)**; (b) a lockfile amendment.
9. **Floor and ceiling:** the band 0.10 and 0.90, and reading it per pair (recommended) or per evaluation as ADR-0032 words it.
10. **Sealed pool size** 20,000 per part, and the values inside the rules (alpha 0.05, power 0.8, cap fraction ½), which ADR-0032 already lists as his.
11. **A model that needs repository code**, if the gate finds one. Recommended: none.
12. **The smaller design** of section 11. Recommended: no.

**What the drafter could not settle from the records:** whether the pinned library loads every model of set B with built-in classes; whether torch 2.8.0 runs them in bfloat16 on MPS; whether greedy generation on MPS repeats exactly; any generation rate on this stack; the SuperGLUE per-task licences; whether any download exists without a ledger row.

## 17. Decisions and approval record

- **Decision 1** (the lead, under the weekend delegation of `docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md`, only after the auditor's review, with any choice taken against the reviewer's advice reported first): approve this specification for implementation and rehearsal. It covers stages D0a, I0 and G-gen at once. It covers D0b to F only after the human lead has given the model list and the domain list. It takes none of the choices of section 16. The human lead may overrule it on Monday 2026-11-23. **Not given.**
- **Downloads.** Within the standing limit they need no further asking once each licence has been re-read at its source. Which models and which datasets is his (choices 1, 2 and 7), so nothing but the packages is fetched before he decides.
- **Decision 2** (the human lead; held for Monday 2026-11-23 or later; recorded in `results/m0-freeze-<date>/DECISION_2.md`): after the rehearsal record, the auditor's agree, the implementation audit, the cost projection and the freeze record, approve the single registered measurement. **Not given.**
- Grounds stated in advance for not running after Decision 1: an engineering stop of section 10.7, or a projection above a ceiling that he declines to extend. A refusal on another ground is recorded with its reason before any development score is read: NOT RUN (DECISION 2 REFUSED: reason).
- If the independent recomputation disagrees with the frozen analysis, the frozen outcomes are recorded as written with the disagreement beside them; nothing is changed without a recorded amendment.

No approval exists. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 18. What follows M0 (pointer only)

`M0 → M1a → M1.5 → M1b` (ADR-0032, Part D). M1a: with the memory attached and inert, is S identical to S₀; it needs a way to attach the memory to a token-level pretrained model, which does not exist. M1.5: the teaching data and procedure, frozen, drawn only from part A families and checked for overlap with every evaluation. M1b: after teaching one narrow capability, is every evaluation within its margin of S₀. Each needs its own specification and approval. None is specified here.

## 19. Where M0 does not satisfy ADR-0032 as written

| # | ADR-0032 text | What this specification does | Whose call |
|---|---|---|---|
| 1 | Section 4: "coding (scored by executing the code)"; "the sandbox is tested with adversarial items before M0 scores anything" | Recommended option executes no model-written code and builds no sandbox. Coding is read as code tracing. L-B0's prerequisite PB-3 ("the container of M0") is then not delivered by M0 | Human lead (choices 2, 6) |
| 2 | Section 7: composition items "shown in M0 to be failed by each teacher, by S₀ and by the registered pipeline" | Not in M0. They must be built from what each teacher is better at, which M0 measures first. A supplement after M0, before M4; a seed is reserved | Human lead (section 7 is not approved) |
| 3 | Section 5: power "by simulation from the measured paired item outcomes, not by assuming independence" | Per-test power is simulated from measured pairs. Across tests a product bound is used, because no S exists to simulate jointly (section 9.4). Joint simulation from M1b | Auditor to check; the rule is approved, this reading is not |
| 4 | Section 4: "an established public harness at a pinned version rather than bespoke scoring where possible" | Bespoke, tested on hand-labelled items. Reasons: the one-system rule needs prompt construction under our control; public harnesses bring many packages and dataset scripts that run code; their support for this stack is UNVERIFIED in note 1 [M] | Lead after review |
| 5 | Section 4: a private set "where one can be built" | None for language understanding or real-world knowledge. Their gate candidates are public items whose exposure cannot be checked | Human lead (choice 2) |
| 6 | Section 4 margin: recommended that δ_e be fixed "in M0's specification" | This document cannot contain δ_e: it is his and held for Monday. Met in substance if he fixes it before Decision 2 while scores are sealed | Human lead (choice 3) |
| 7 | Section 4, Tier 2 (c), and "active compute per token" | Under the proposed bound (c) is the S₀ checkpoint and adds no model. S's active compute cannot be measured before M1a; the bound is a parameter count used only to choose a reference | Human lead (choice 1) |
| 8 | Section 4: floor and ceiling per evaluation | Read per (reference, evaluation part), so that a weak equal-bytes reference at floor does not remove an evaluation the teachers are interior on | Human lead (choice 9) |
| 9 | M0 row: "an amendment to `uv.lock` and `pyproject.toml`" | Recommended option needs none | Human lead (choice 8) |
| 10 | M0 row and section 9: the cumulative download total "counted and printed" | Printed, with the finding that the ledger on `main` is behind (1.19 against 1.50 GB), and a clerk inventory gate, because the drafter could not show the count is complete | Lead; clerk |
| 11 | Section 7: complementarity "for each domain" | Measured per evaluation part; the domain line gives three readings and leaves the choice to section 7's approval | Human lead |
| 12 | Section 4: Tier 2 (b), "the strongest available conventional model of the student's family" | Read as the largest of the same release series under the bound | Human lead (choice 1) |

## 20. Review record

Draft 1 has not been reviewed. The auditor receives this file, ADR-0032 and the records it cites, and no conclusion of the drafter beyond what is written here.

`SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`.
