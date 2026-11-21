# Review of ADR-0033 draft 1 (M0: reference models and evaluation harness)

Reviewer: `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-20. Independent design review; I did not write ADR-0033 or ADR-0032. Claude review is not Astra review. `Astra review: NOT_PERFORMED`. This is not human approval and not validation. Nothing here is a result about any model or about ArborLM.

## 0. What was read and run

- Read: `AGENTS.md`, `CLAUDE.md`; ADR-0033 at commit `c89c1f2` (file SHA-256 `94c1c790…6ae8`); ADR-0032 revision 4 in full (SHA-256 `b5f5e564…0ad4`); `APPROVAL_OF_RULES.md`, `DELEGATION.md`, `HUMAN_LEAD_DECISIONS_2026-11-20.md`, `REVIEW_3.md`; `LITERATURE_NOTE_1.md` sections 3 to 7; ADR-0031 sections 16 to 21 (house pattern); `studies/p10s2/requirements-datagen.txt` header; ADR-0022 lines on §14.2; `uv.lock` package list; `pyproject.toml`; `SEED_REGISTRY_R4.md` §5; `SEED_REGISTRY_R5.md` (untracked).
- Ran (all trivial CPU; read-only on the repository):
  - `git show <ref>:docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md` for `origin/main` (`5d648e1`), `HEAD`, `aa41a62`, and a loop over every local and remote branch: only two final totals exist, **1,188,183,868** and **1,502,260,446**; difference **314,076,578** = the two WikiText-103 shards. Confirms the drafter.
  - `git ls-tree -r` over every branch for files named `*ledger*`: one download ledger only.
  - `du -sk` and `stat` on `/Users/daniellaloush/dandush03/ArborLM/data/*` (sizes only; nothing opened except `wikitext2/provenance-notes.jsonl`): see finding R10.
  - `git grep` over every branch for literals `40xxxx` and `953xxx` in `*.py`/`*.toml`: none. ADR-0030 (untracked) uses 310001–319999 and 939001–939999 only.
  - `sysctl`: Apple M5 Max, 18 cores, 51,539,607,552 bytes (48 GiB). Confirms the draft.
  - My power checker: `experiments/_scratch/audits/adr0033_review/power_check.py` (SHA-256 `f872d24e…6418`), run as `timeout 300 nice -n 19 python3 -I power_check.py` with `/opt/homebrew/bin/python3`, Python 3.15.1, standard library only; output kept verbatim in `power_check.out.txt` beside it.
- Not done: no download, no model, no package install, no commit, no edit outside this review folder.

## 1. Verdict

**READY AFTER THE LISTED EDITS.** Two findings are BLOCKING (B1 power simulation models the wrong cluster design; B2 Decision 1 as drafted would let the lead take a decision held for the human lead). Both are fixable by text. Because B1 changes a generator design number that is frozen at G-gen, I recommend a short confirmation review of B1, B2, R1, R3 and R4 before Decision 1.

## 2. Findings

### BLOCKING

**B1. Section 9.4 simulates more independent clusters than M5's sealed split will have, so the sizes are anti-conservative and may be unreachable at any n.**

The sealed split of a private part is drawn from the same finite set of templates as the M0 draw (the generator is frozen; draft §6.2: "at least 60 clusters ... in each evaluation part"). M5's test is a cluster bootstrap over those templates (approved power rule). Its standard error therefore carries a between-template term τ²/G that does not shrink with n. The draft's simulation resamples clusters "up to n items", i.e. about n/25 independent clusters of 25 items each, so its between-template term is 25τ²/n and vanishes as n grows.

My check (`power_check.py`, section C; d = 0.30, 11 parts × 5 tests, product rule; τ = between-template SD of the recentred difference within family):

| τ | G | δ | n by the draft's construction | n under M5's design | Largest per-test power at any n (need 0.9960) |
|---|---|---|---|---|---|
| 0.05 | 60 | 0.03 | 7,422 | 41,833 | 0.9987 |
| 0.05 | 60 | 0.02 | 16,701 | unreachable | 0.9270 |
| 0.10 | 60 | 0.03 | 11,262 | unreachable | 0.7514 |
| 0.10 | 60 | 0.05 | 4,054 | unreachable | 0.9871 |
| 0.10 | 300 | 0.03 | 11,262 | 19,349 | 0.9998 |

The draft would print a size on the ladder where the real M5 test cannot reach the registered power. Recentring keeps the template-level heterogeneity of S₀ against a teacher, which is plausibly large, so τ near 0.1 is not far-fetched [E]. Only G moves the floor, and G is fixed when the generator is frozen at G-gen, under Decision 1. It has to be settled now.

A second, related point: if items that share a rule shape but differ in surface frame are correlated, a cluster defined at frame level understates dependence.

Replace the second bullet of §9.4 with:

> - **Per-test power by simulation of M5's own design from the measured paired outcomes.** For that pair, a candidate size n and G_e, the number of clusters the part's sealed split will contain (for a private part, the number of templates of the part as fixed by the frozen generator and recorded at G-gen; for a public part, the number of clusters in its sealed part): 20,000 simulated samples. Each is drawn in two stages within strata: first G_e clusters with replacement from the M0 draw's clusters, allocated to strata as the sealed split will be; then n/G_e items with replacement within each drawn cluster. In each sample, the mean difference is recentred to zero. The mean difference and its cluster-robust standard error over the G_e drawn clusters are then scaled by √(d_e / (d_e − μ²)). The simulated test passes if the estimate minus t₀.₉₅,G_e−1 standard errors is above −δ. π_e(n, δ) is the share that pass, printed with its Monte Carlo standard error.
> - **Floor from the clusters.** Also printed per part: τ̂_e, the between-cluster standard deviation of the paired difference within strata (method of moments, registered formula); and the largest per-test power reachable at any n, Φ(δ·√G_e / τ̂_e − z₀.₉₅). If that is below the per-test target, the part is NOT EVALUABLE (UNDERPOWERED, e, δ) whatever the pool size.

Replace the first requirement of §6.2 with:

> - **Families and clusters.** At least 12 template families, each a distinct rule structure. A cluster is a (family, rule shape) pair, the level at which items share their rule; surface frames vary within a cluster. The number of clusters per evaluation part, G, is a registered design number, fixed before G-gen. Proposed: at least 300 (the human lead's number). The reason: in the sealed split the clusters are fixed, and between-cluster variance sets a floor on the standard error that no number of items removes (review B1). Families are strata.

Add G to the §14 "Sizes" row and to the §16 choice 10 list.

**B2. Decision 1 as drafted covers D0a, installing the packages that run the measured models. That is the human lead's choice 8, and ADR-0032 E1 item 8 holds "the lockfile amendment" for him. The P10-S2 precedent is also misdescribed.**

ADR-0022 (P10-S2), line 62, reads: "The registered path runs on the locked environment only (torch 2.8.0, no other package)". There, the non-lock packages ran a one-off data-generation step only, and the student was re-implemented in plain torch and checked for equivalence. In M0 the non-lock packages (`transformers`, `tokenizers`) would be the measuring instrument of the registered run. Approving D0a would choose option 2 of §5 in substance. My ruling on question 7 is in section 4.

Replace the last bullet of "For the human lead" with:

> - **What the lead may do under your weekend delegation, after the auditor's review, and nothing more:** approve this specification for the work that runs on the locked environment alone. That is stage I0-a (generators, solvers, scorers, analysis and their tests) and stage G-gen. The packages that would run the models (choice 8), every model and dataset (choices 1, 2 and 7) and every number of section 14 are yours. No package, model or dataset is fetched before your choice.

In §13, split I0 as follows:

- I0-a: locked environment only; needs Decision 1.
- I0-b: harness and loaders, tested on a tiny random model; needs D0a.

D0a's "Needs" becomes "the human lead's choice 8".

In §5, replace "These five pins are the versions already resolved, hashed and installed once for P10-S2" and the sentence after it with:

> These five pins are versions already resolved and hashed for P10-S2. There they ran a one-off data-generation step only; P10-S2's registered path ran on the locked environment alone, with the model re-implemented in torch and checked for equivalence (ADR-0022 §14.2). In M0 they would run the registered measurement itself, which has no precedent in this repository.

Add option 3 to the §5 table:

> 3. Models re-implemented in plain torch inside the locked environment, verified once against the library's reference logits and greedy outputs in a separate one-off step (the P10-S2 pattern). The lock is untouched, and M1 attaches the memory to code the project owns. Against: more implementation work, and an equivalence gate per architecture (Qwen2, GLM-4).

### REQUIRED

**R1. The product bound: the stated reason is not shown, and a dependence-free alternative costs about 2 %.**

The claim "Tests that share S's answers are expected to be positively dependent, which makes the product a lower bound" is not proved in the draft.

What I can show: for binary items, if S and the two references in a pair of tests have equal true means, the per-item covariance of the two paired differences is non-negative. Proof: write D_i = S − R_i and X = 2S − R_i − R_j. On items where the two references disagree, X = ±1. So E[X²] ≥ P(R_i ≠ R_j), and Cov(D_i, D_j) = [Var X − Var(R_i − R_j)]/4 ≥ [(μ_i − μ_j)² − (E X)²]/4 = (μ_i − μ_j)²/4 ≥ 0. Under a normal approximation, Slepian's inequality then gives the product as a lower bound.

The argument fails in two places:
- At cluster level: between-template covariances of the differences can be negative.
- When the SE is random.

My attempted counterexample (section D) showed no dependence at all: covariance zero by construction, joint 0.7457 against product 0.7488, MC SE 0.008. See section 5.

Boole's bound P(all pass) ≥ 1 − Σ(1 − π) needs no argument. It raises n by a factor of 1.017 at 55 tests and 1.016 at 70 (section A). Replace the third bullet and the "What this is and is not" paragraph's second and third sentences with:

> - **The conjunction.** With M_e = m·P tests in all, the size required for part e is the smallest n on the ladder with π_e(n, δ) ≥ 1 − 0.2/M_e. This is Boole's inequality, which holds whatever the dependence between tests, so no assumption about dependence is needed. P counts every gate-candidate part of the registered domain list, including parts later found NOT EVALUABLE.

**R2. Monte Carlo resolution.** The per-test target is about 0.996. With 2,000 simulations about 8 failures are expected, so the MC SE of π^5 is about 0.007 (section E). Use 20,000 simulations (already in the B1 wording). In the confirmation bullet, replace "500 simulations" with "2,000 simulations, its MC standard error printed". The full bootstrap's cost at that count is measured in R2.

**R3. δ_e has to be fixed before any model scores any item (departure 6).** The draft allows "before Decision 2, while scores are sealed". But R1 produces tuning scores before that, and the public rehearsal record carries chosen level ranges, which encode where the references sit. ADR-0032's recommendation is "before M0 scores anything". In §16 choice 3(a) and §19 row 6, replace "before Decision 2" with:

> before stage R1, i.e. before any model scores any item. If he has not fixed it, R1 waits.

**R4. The stage table under-states what each stage needs from the human lead.**

- R1 uses the band (choice 9), choice 3 (R3 above) and the rehearsal cap (choice 5).
- D0b needs choices 7 and 11.
- F generates the sealed pool at its size (choice 10) and G (B1).
- §17 says D0b to F need "only" the model list and the domain list.
- ADR-0032's approval record says "Not approved: every number".

Replace the Decision 1 bullet's third sentence with:

> It covers D0b, G-load, R1, R2, R3 and F only after the human lead has given every choice of section 16 that the stage uses (the "Needs" column of section 13 names them). Every number in `configs/m0_reference_models.toml` is a proposal until he confirms it, which he does before F.

Add those choice numbers to the "Needs" column.

**R5. The repeat identity gate and the batch sizes are out of order.**

- §7 runs the gate "at the registered batch size" in G-load.
- §7 also fixes batch sizes "after the measuring rehearsal" (R2), and R1 runs before R2.
- R2 needs chosen formats, which come from R1.

Replace the Batching row with:

> Left padding; batches formed by a stable sort on prompt length. Batch size per (model, mode) is fixed at G-load by a rule: the largest power of two whose peak memory at the longest admitted prompt plus the token limit stays at or under 24 GiB. It is used unchanged in R1, R2, R3 and M. Each item's batch membership is stored in its raw record.

Replace the repeat-gate paragraph with:

> **Repeat identity gate.** For each model and mode, 64 tuning items are run twice at the fixed batch size, in two separate fresh processes. The second process runs after a full model reload, and if possible under different machine load. The two runs must give identical token sequences. The gate runs at G-load and again inside R3. A failure is an engineering stop (NON-DETERMINISTIC STACK).

**R6. The rehearsal cost is about three times the draft's figure, and "charged hours" is undefined.**

The format choice scores tuning items under three formats. Per system that is roughly:
- private: 4 evaluations × 2 parts × 5 levels × 100 items × 3 formats = 12,000;
- public: 6 sets × 150 × 3 = 2,700;
- reserve levels: up to 1,600 more.

That is about 14,700 to 16,300 scorings, against 27,000 for the registered measurement: roughly 55 %, not "a fifth". On the draft's own rates, R1 alone could exceed the 30-hour rehearsal cap. Required:
- (a) state how many tuning items the format choice uses (proposed: 50 per part at the middle level, under all three formats; level ranges then on the full tuning draw at the chosen format);
- (b) recompute the rehearsal estimate in §11;
- (c) add to §14: "Charged hours: a stage supervisor's wall clock (ADR-0031 §17)."

**R7. The one-system rule needs these fixings before the freeze (question 5).** Add rows to §7:

> | Template differences | The rendered example of each model is recorded, and every difference between families is listed in the record. This includes the default system text that the Qwen2.5 template inserts when no system message is given, and the GLM-4-0414 prefix tokens. These are the listed exceptions of ADR-0032 §4. S uses S₀'s template unchanged |
> | Tokenisation | Token ids come from the chat template's own tokenisation, never from re-tokenising rendered text with special tokens added. At G-load, each model's ids for the fixed example are compared with a hand-checked expected sequence |
> | Attention and cache | `attn_implementation` is pinned to one value for every model; the KV cache is the library's default dynamic cache; both are recorded |
> | Generation config | A new GenerationConfig is built from scratch: `do_sample=False`, `num_beams=1`, `repetition_penalty=1.0`, no temperature, top-p or top-k, and the model's listed EOS ids. It is passed explicitly, so the checkpoint's `generation_config.json` is not merged. The effective config is recorded per model |
> | Numerical check | At G-load, each model's greedy output in MPS bfloat16 on 32 fixed prompts is compared with CPU float32 (models up to 1.5B) or CPU bfloat16 (larger models). The token-agreement rate and any non-finite value are recorded. A non-finite value fails the precision gate |
> | Token limit (worked mode) | Chosen by code on the tuning draw: the smallest of {384, 512, 768, 1,024} at which every system's limit-hit rate is at most 2 %. Fixed before the development pools are generated |
> | Answer grammar | Per evaluation, a registered regular expression for the marker and a canonical answer grammar: numbers; one letter A–J; yes/no/cannot be determined; single-line printed output for C1, whose programs print exactly one line; lists. The scorer is tested on at least 200 hand-labelled raw outputs per evaluation from R1, labelled by a context that did not write the scorer. Any disagreement is an engineering stop |
> | Chance level | c of section 10.2 is the item mean of 1/k_i for closed answers, 0 for open answers |

Also in §5, replace the precision fallback's "float16 ... for every system" with:

> float16 on MPS for every system. If any model is then non-finite, every model it affects is REFERENCE NOT RUNNABLE LOCALLY (PRECISION), and the lead returns to the human lead before R1.

Qwen-family activations overflowing in float16 is a known hazard ([D] UNVERIFIED, my memory).

**R8. Coding as tracing (departure 1).** Code output prediction measures reading and tracing code. It does not measure writing it, which is what the human lead's "coding" ordinarily means. It is an honest part-measure only if it is never called coding. In §6.8, rename the domain to "Code tracing (output prediction)" and add:

> Code writing is NOT MEASURED in M0. Every label, report, scorecard line and later verdict that uses C1 or CRUXEval says "code tracing", never "coding". Any later claim about the coding capability the human lead named carries NOT EVALUABLE (CODE WRITING NOT MEASURED) until a code-generation evaluation scored by execution exists. ADR-0032's L-B0 prerequisite PB-3 (the container) stays undelivered.

**R9. Sealed pools and generators (question 4).**

- (a) ADR-0032 §4 requires teaching data to be checked against every evaluation, sealed splits included; with the pool unreadable that check has no route. Add to the sealed-pool paragraph:

  > The stage also writes, inside the sealed directory, a keyed fingerprint set of the pool: HMAC-SHA-256 under the salt of each normalised item and of each of its 13-grams. M1.5's overlap check runs as a sealed-stage process that reads salt, fingerprints and teaching data, and writes counts only.

- (b) Replace "What the seals are" with:

  > The hashes commit M0 to the pools. At M5 anyone can check that the pool scored is the pool generated at F. That is the guarantee. Confidentiality is procedural on one account, and of limited value anyway: the generator and its templates are in the repository, so exact sealed items add little secrecy beyond the template set. Held-out part B rests on procedure: no teaching code may use part-B families, checked in M1.5 by template signature.

- (c) Generators must be bit-reproducible across processes. Add:

  > No generator iterates a set or dict of strings without sorting, and none calls `hash()`. Every process runs with `PYTHONHASHSEED=0`. A test generates each pool twice in two processes and compares hashes.

- (d) Add a capacity gate to G-gen:

  > For every cluster and level, the number of distinct items the generator can produce is at least 10 times the number the pools demand. Otherwise engineering stop.

- (e) Add:

  > Tuning, development and sealed items are pairwise disjoint after normalisation.

  At present only sealed against the others is stated.

**R10. The download count (question 6).** The drafter's figures check out (section 0). Additional findings for the D0b inventory gate:

- (i) `data/wikitext2/` holds 7,030,741 bytes fetched 2026-11-12, before the ledger began (2026-11-15), with no row.
- (ii) `data/p10s2-pre-20261115/downloads/` exceeds its rows by exactly 4,867 bytes. That is `fetch_record.json`, a local file.

Add to §4.1:

> The inventory counts every fetch since 2026-11-15 against the 50 GB limit, and lists earlier fetches (WikiText-2, 7,030,741 bytes, 2026-11-12) separately with the human lead's ruling on whether they count. A fetch after 2026-11-15 with no row is an engineering stop.

Also add to §4.1:

> Weights are fetched by plain HTTPS resolve URLs at the pinned revision with resumable range requests, never through the hub's chunked (Xet) transfer, and the ledger counts transferred bytes. The allowlist adds `model.safetensors.index.json` and `chat_template.jinja`. The repository-code check covers `config.json`, `tokenizer_config.json` and `generation_config.json`: no `auto_map`, no custom tokenizer class, and no `.py` file in the repository listing that the loader would reference.

**R11. Multilingual ability is dropped without a departure.** ADR-0032 E1 item 3 recommends adding mathematics and multilingual ability, giving the reason that a student taught in English could regress in Chinese. The draft excludes multilingual ability in §3 on the ground that note 1 has no licence-checked evaluation. That is a reason to check one, not to drop the domain. Add departure 13:

> | 13 | E1 item 3 recommends multilingual ability | Not specified: no evaluation was licence-checked. Candidate public sets exist ([D] UNVERIFIED: MGSM, XNLI, Belebele). The human lead may add the domain before the freeze, with licence re-read at D0b | Human lead (choice 2) |

Instruction following belongs in the same row (IFEval, [D] UNVERIFIED).

**R12. The §10.6 projection omits systems and has no rule for UNDERPOWERED parts.** INTERFERENCE (ADR-0032 §7, joining the conjunction) needs S taught by each teacher alone, which adds two systems. "S₀ with retrieval" runs longer prompts than S₀. Replace the system list with:

> S₀, every Tier 2 reference, S, S taught by each teacher alone (two systems), and five Tier 1 systems, all at S₀'s measured rate except retrieval, which is taken at S₀'s rate × (mean prompt tokens with retrieval ÷ without). Retrieval's prompt length is fixed in M1.5; until then the factor is 2.

Also add:

> A part that is UNDERPOWERED at δ enters at its pool maximum.

**R13. Floor and ceiling per pair (departure 8).** Acceptable only if the consequence for the verdict is stated. Add to §10.2:

> A pair that is NOT EVALUABLE (FLOOR OR CEILING) cannot pass. A PARITY verdict that needs it reads NOT EVALUABLE for that reference, so reading per pair never makes PARITY easier to print than the per-evaluation wording of ADR-0032.

Use c as defined in R7.

**R14. Tier 2 (c) collapses onto S₀ (departure 7).** This is the honest consequence of a 1.25 × bound. It contradicts ADR-0032's sentence that S₀ "is not a parity reference" unless reconciled. Add to §4.3:

> Under this bound, reference (c) is S₀. Its parity test is the NO HARM test at the same margin, which adds no test to the conjunction. Every PARITY verdict names it as "(c) = S₀, by NO HARM". S₀ is a parity reference in this role only.

Also: the count is "registered now". Define what "parameters read per token" counts: tied embeddings once; input embedding look-up excluded; LM head included. For Qwen2.5-0.5B, embeddings are about 136 M of 494 M parameters ([D] UNVERIFIED), so the choice moves the bound by about 25 %.

**R15. Composition items deferred (departure 2).** ADR-0032 §7 (not approved) says composition items are generated "before S exists". S exists from M1b. Replace "A supplement after M0, before M4" with:

> A supplement after M0, frozen before any S is trained (before M1b), or, if the human lead accepts, before any S taught by both teachers exists (before M4).

**R16. NOT RUNNABLE LOCALLY.**

- Add a precedence: NEEDS REPOSITORY CODE, then PRECISION, then MEMORY, then COST.
- Define the memory reading: "peak of the process's `ri_lifetime_max_phys_footprint` (macOS `proc_pid_rusage`), which includes Metal allocations".
- Add: "the registered batch size must also stay under the cap".
- Add to §10.4 and §9.4:

  > If a teacher is NOT RUNNABLE, complementarity on every part reads NOT EVALUABLE (REFERENCE NOT RUNNABLE), never NO COMPLEMENTARITY. d_e is taken over runnable references, and the M5 tests against an unrunnable reference are NOT EVALUABLE LOCALLY.

**R17. Seeds (question 9).**

- The block 400001–409999 and the test range 953001–953999 collide with nothing on any branch I checked (section 0). They follow R4 §5 item 3.
- Revision 5 is untracked in this worktree. Revision 6 must cite R5 by hash, or R5 must be committed first.
- Replace "M0's freeze gate needs a checker that passes, run unedited with M0's own file globs" with:

  > M0's freeze gate needs a checker run, unedited, that reports no failure involving M0's allocations or any collision with them. Failures that predate M0 and belong to other studies are listed and do not block M0, unless the auditor finds that they touch M0's ranges.

  PENDING LEAD REVIEW.

### RECOMMENDED

- **C1. The comparison of sets A and B overstates B's advantages.** Reason 2: Qwen3's thinking mode is turned off by a documented template switch, so the 5–20 × cost does not apply. Reason 3: Qwen3 is, to my memory, supported by transformers 4.57.1 ([D] UNVERIFIED). The real differences are 2.6 GB of headroom, one template switch to register, and age: set B's models are about two years old, set A's about eighteen months. Say so in §4.2.
- **C2. Option for the human lead: one identical neutral system message for every model** (for example "You are a helpful assistant."). It replaces Qwen's default persona and makes the prompt more nearly identical. Proposed as a §16 choice, with "default system text" as a fifth nuisance variation in §9.3.
- **C3. Departure 4 (bespoke harness).** Acceptable with R7's scorer test. Also add: for GSM8K and MMLU-Pro, print the bespoke scorer's agreement with each benchmark's published answer-extraction rule on the same raw outputs.
- **C4. Second solvers.** The auditor context that writes the second solvers must not audit them. State that a separate auditor context audits the solver pair.
- **C5. Public splits.** One third for development makes MMLU-Pro's sealed part about 8,000 items and PopQA's about 9,300, so δ = 0.02 is probably UNDERPOWERED there. Consider a development split of exactly 1,650 plus a registered reserve of 1,000, with the rest sealed. Specify whether the third is taken per task inside L1.
- **C6. Memory guard during generation.** Generation pauses between batches while available memory is under 4 GiB, with a deadline. KV caches grow after the load-time check, and other studies hold up to 12 GiB.
- **C7. Attachability.** ADR-0032's M0 row asks that the choice of S₀ consider whether the memory can be attached (width, tokenizer, licence). Add a paragraph: hidden width 896, vocabulary about 151 k, Apache-2.0 permits modification ([D] UNVERIFIED). M1a may find attachment infeasible.
- **C8. PENDING LEAD REVIEW.** Retention tests (ADR-0032 §6, part of the gate) are not among the m tests. State whether M5 scores retention on sealed splits. If it does, they join the conjunction.
- **C9. Item formats.** For PopQA, apply alias match to the extracted answer, by normalised exact match against any alias, not substring match in free text. Specify the item units of MultiRC (one answer option) and ReCoRD (exact match against any gold entity).
- **C10. PENDING LEAD REVIEW.** On a part where S₀ AT FLOOR, the NO HARM test is nearly vacuous. Say so beside the flag.
- **C11. Sealed archive check.** The auditor verifies the sealed tuning archive with code that prints only agree or disagree and hashes, never a score.

## 3. Rulings on the twelve departures (§19)

| # | Ruling | Edit |
|---|---|---|
| 1 Coding as tracing | Acceptable with an edit | R8 |
| 2 Composition deferred | Acceptable with an edit | R15 |
| 3 Product bound | **Not acceptable as written**; acceptable after B1 and R1 | B1, R1, R2 |
| 4 Bespoke harness | Acceptable with an edit | R7 (scorer test), C3 |
| 5 No private set for language understanding or real-world knowledge | Acceptable with an edit. Real-world knowledge cannot be private. A narrow private language set (rule-built reading over generated fictional passages) can be built, so the row must say "not built", give the reason, and leave the choice to him. Public-set exposure is disclosed on every line | Reword the row: "can be built only as a much narrower construct; not built in M0" |
| 6 δ_e outside the spec | Acceptable with an edit | R3 |
| 7 Tier 2 (c) = S₀ | Acceptable with an edit | R14 |
| 8 Floor or ceiling per pair | Acceptable with an edit | R13 |
| 9 No lockfile amendment | **Not acceptable as something the lead can take.** Acceptable as his choice, with the precedent described correctly and option 3 added | B2 |
| 10 Download count | Acceptable with an edit | R10 |
| 11 Complementarity per part | Acceptable. Choosing the superiority domain after M0 is legitimate, because the choice uses development data and the test is on the sealed split | — |
| 12 (b) = same release series | Acceptable (his choice). Under the broad reading, "strongest" can only be decided by measuring in M0, before any score of S | — |

## 4. Question 7: the packages, ruled

The separate hash-pinned file keeps the letter of CLAUDE.md, since `uv.lock` and `pyproject.toml` are untouched. CLAUDE.md's one stated route for packages outside the lock is `uv run --locked --with` for **analysis-only** tools, and these packages are not that: `transformers` and `tokenizers` would build the prompts, tokenise them and run every measured model. That makes them the instrument of the registered measurement and of every later rung.

The only precedent, P10-S2, deliberately kept its registered path on the locked environment. It used the extra packages for a one-off data step behind an equivalence check, under an ADR the human lead approved.

**Ruling:** using a separate pinned environment for the registered measurement is an amendment in substance to the project's environment of record. ADR-0032 E1 item 8 already holds "the lockfile amendment" for the human lead. The lead may not take it under the weekend delegation, and D0a may not run before his choice 8. Whichever route he picks (amendment, separate file, or the P10-S2 re-implementation pattern), its resolved versions bind M1 to M5, as the draft's condition says. Implementation that needs only the locked environment (I0-a, G-gen) may proceed under Decision 1.

## 5. Recomputations, discrepancies and my own errors

- **Coefficient k** (section A): 18.43 at 55 tests and 19.12 at 70 (product rule). The draft says "18 to 19". Agrees.
- **Draft's example sizes:**
  - d = 0.3, δ = 0.03: 6,143 to 6,375 (draft: "about 6,400"). Agrees.
  - d = 0.3, δ = 0.02: 13,821 to 14,344 (draft: "about 14,300"). Agrees.
  - The largest d that 20,000 items cover at δ = 0.02: 0.418 to 0.434 (draft: "about 0.42"). Agrees.
  - ADR-0032's figures: 6.18 (draft 6.2), 11.25 product / 11.53 Boole (draft 11.5), 17.50 (draft 17.5). Agree.
- **Recentring and variance scaling** (section B): correct to first order.
  - n = 1,000, δ = 0.05: simulated 0.8270 against analytic 0.8301.
  - n = 2,000, δ = 0.03: simulated 0.7045 against analytic 0.7125.
  - Both gaps are within MC error (about 0.010). Scaling the estimate and its SE by the same factor is equivalent to testing against −δ/k, which is what is intended.
- **Smaller design:** ±2.84 points at 1,000 items and ±2.32 at 1,500 (d = 0.3). Agrees.
- **Download totals:** set B 40.8, set A 43.4, set C 47.1; the ledger totals 1,188,183,868 and 1,502,260,446. All agree.
- **Discrepancy with the draft:** the rehearsal cost (R6).
- **My own error, kept:** section D of `power_check.py` was meant as a counterexample to the product bound. Its student copies one teacher per item, so the per-item covariance of the two differences is zero by construction, and it showed nothing: joint 0.7457 against product 0.7488. I had reasoned from a continuous analogue (S the average of two independent teachers) that does not carry over to binary items. The derivation in R1 replaces it. R1 stands on Boole's bound, not on that example.
- **The cluster model in section C is mine and analytic.** Var = d/n + τ²/G for M5; d/n + 25τ²/n for the draft's construction. The τ values are illustrative, not measured.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
