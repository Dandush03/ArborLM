# ADR-0017 revision 1 — independent scientific design review

- Reviewer: Claude Opus 5.5 (session model `claude-opus-5-5`), auditor role, launched by the Claude lead. This is independent engineering and mathematical evidence. It is **not** Astra review and **not** human approval. Astra review: NOT_PERFORMED.
- Reviewed (untracked, read on 2026-11-14, branch `claude/adr-0017-design`, HEAD `afd62e5`): `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` (rev 1), `ADR-0017-draft-rev0-human.md`, `EXECUTION_PLAN.md`, `RESOURCE_BUDGET.md`, `benchmark/`, `EVIDENCE_INVENTORY.md` (clerk, treated as unverified; every number used below was re-read from source or records). Code read: `pilot_model.py`, `model.py` (Block), `p4_model.py`, `p5_model.py`, `p8_objective.py`, `p7a_core.py`, `p7b_sim.py`, `p7b_layout.py`.
- I wrote none of the design. I wrote the earlier P8 spec/result audits; the only P8 artefact reused here is the P8 training record (`results/p8-2026-11-14/train/.../steps.jsonl`), read by a new script.
- Nothing was implemented, trained or evaluated. No ArborLM model was run. All checks below are toy or pure-math scripts in `opus_checks/`, with outputs beside them.
- Environment: Apple M5 Max (18 cores), macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0 (CPU), no numpy. Load average about 2 (not a timing measurement). Each command was run from the repository root: `uv run --locked python -W ignore docs/reviews/adr-0017-design-2026-11-14/opus_checks/<script>.py [repo root] | tee .../<script>.out.txt`. `uv run --locked ruff check .` passes.
- Failed attempts: none. Every script ran on its first try. No discrepancy in my own work had to be retracted.

## Verdict: **NOT READY** for Human Decision 1

Three blockers mean the registered run could produce class labels that do not mean what they say. (1) The primary information metric credits knowledge to a model that has none. (2) The usage objective's coefficient rule turns a property of the initial state into ENGINEERING_FAIL, or else lets one cap set both doses. (3) Whether the task is valid is unmeasured, and the plan forbids measuring it before the run. Each has a concrete fix (below). With those fixes, plus the majors on loss masking, panels, identifier density and the locality specification, the design is a reasonable diagnostic.

## Answers to the lead's questions (short form; details in the findings)

| Q | Answer |
|---|---|
| A. Can the frozen backbone expose a 4-symbol identifier? | Unknown. It is the binding risk, and rev 1 does not measure it before the run. The memory sits after block 0 (`pilot_model.py:188-191`). At the binding byte the hidden state is that byte's embedding, its position embedding, one 4-head causal attention read (head dim 8; `model.py:26-36`) and an FFN. Any identifier information must therefore come through one frozen attention layer trained on WikiText, mixed with the prefix and up to 7 earlier records (cluster-mates) at varying offsets. Identifier density reaches 1/32 at 32,768 facts, so **98% of facts have a Hamming-1 twin** (C1). How well twins separate depends on how the attention weights the 4 identifier positions, and nobody has measured that (C1b, stylized). The answer path is expressible in principle (see B3). Floored I is not a lower bound and can be gamed (B1). Held-out templates confound query shift with memory (M2). Planted clusters do not leak answers but give a context cue (m5). Family 2's "latent two-hop impossible" claim is **correct** for this architecture, with one in-context loophole (M12). |
| B. Capacity logic | Snapshot estimand: valid (constant LR, step-indexed bias correction, epoch-aligned streams). "Matched exposure" is not matched optimization, because dense AdamW moves a sparse row about √K·lr per exposure: 4×, 8× and 15× lr at the three sizes (C4, M5). The plateau rule (5% between E = 24 and 32) is weak and lets UNDERTRAINED absorb null results (M8). The D04 cap is undefined ("as much") and nearly vacuous (M8). Thresholds 3.0 / 1.10 / 0.50 / 90% are defensible only on a valid metric (B1). Addressing capacity: random 16-d codes are **not** the accuracy bottleneck at 32,768 facts (naive accuracy 0.98), but temperature 0.2 keeps reads diffuse (median self weight 0.29). The dense adapter matches parameters exactly, uses 3× the MACs of flat, and reads the full 32-d state (fair, and favourable to dense). |
| C. Ladder | R1−R0 mixes four things, R2 is not an upper bound on R0, and "gap" has no number (M4, M9). The key-width arm is placed correctly but enters no rule (M8). |
| D. U* | Well defined and not circular. It is **inflated by diffuseness**: with weights near 1/8, every selected slot clears 0.05, so U* ≈ 8 × dependent facts. The 2/32 threshold ignores the backbone's prior over Σ. Cost is negligible only with per-query masking (M6). |
| E. Objectives | R_util range is [0, ln 512 / ln N] = 0.75 / 0.64 / 0.56. On P8's own init records the hinge is **inactive in all 6 flat cells**, which makes it ENGINEERING_FAIL by rev 1's rule, and barely active in the tree (B2). It is batch-local, so it cannot prevent global collapse at 16K/64K, and slots outside every top-64 get no gradient, so they never revive (M7). The lazy-Adam arm is confounded by a 4–15× change in per-row step size (M5). R_co is coherent at 16K/64K: 8-slot groups nest in 256-slot branches. |
| F. Locality | The cache rule is fixed before outcomes and does not depend on misses. With high utilization E is identifiable (null 6–7.5 misses per query, far above 0.05; C6). Planted clusters alone give E ≈ 0.77 under a cluster layout. The oracle layout needs a tie rule because shared slots have a majority-cluster share of 0.25. The P7-B code cannot be reused "unchanged" (M10). Key-traffic accounting is honest but is an identity, not a measurement. |
| G. Lane D | Replay is confounded with exposure. Retention as a ratio has no floor on a_A⁰. The parameters trained in phase B are unspecified (M11). |
| H. Statistics | Two init seeds on one data draw plus one parent replicate: within-testbed robustness only. G2 has a 0.1% false-fail rate per test, and up to 45% family-wise (C5, M13). The class tables overlap or are undefined in several places (M8, m10–m12). |
| I. Matrix / budget | 108 cells recount exactly (C7). Training arithmetic is consistent. Evaluation is unbudgeted (an uncached evaluation is about 15 h at 64K against a 2.7 h allowance). The dense adapter is under-budgeted about 3× at 64K. A9 has no update count (M14). |
| J. Governance | §12's two-decision order resolves the conflict correctly. "Rehearsal accuracy not written" can be enforced only by code review, and it blocks the calibration the design needs (B3). Rev 1's departures from the draft are listed in §5. |

## 1. Blockers

### B1 — The primary metric "retained information" is not a lower bound; a zero-knowledge model passes the capacity step test

- Evidence: rev 1 §6.1 (lines 162–165) defines I = Σ_f max(0, 5 + log₂ p_f). The floor makes each term ≥ the unfloored term, so the sum is not a lower bound on information. Any spread of p around 1/32 that does not depend on the answer earns positive bits. `opus_checks/c2_floored_information.out.txt`:
  - Zero-knowledge predictor with logit noise s.d. 0.1: 0.054 floored bits per fact, accuracy 0.031, unfloored −0.006, Fano 0.0. Floored I = 107 / 424 / 1,763 bits at 2K / 8K / 32K facts. **Step ratios 3.95 and 4.16 ≥ 3.0.**
  - With s.d. 1.0: 0.29 bits per fact, ratios 4.14 / 4.04. A "confident random guess" at mass 0.5 gives exactly 0.125 bits per fact, ratio 4.0.
  - Because the inflation scales with F, **"step supported" holds for any zero-knowledge model with non-flat outputs.**
- Why it matters: CAPACITY_PARTIAL (§8.2, line 223) needs only the 4K→16K step, beats-dense at 16K and dependence. All three hold for a zero-knowledge memory whose random-looking outputs are more peaked than the dense adapter's:
  - value permutation and disabling give chance (G2 interval);
  - the chance-correct facts lose their p when the support is zeroed, so they count as "knowledge-dependent".
  - There is no accuracy floor in PARTIAL.
- Required change, replacing §6.1's primary quantity:
  - "**Primary information is the Fano bound from accuracy**, I_acc = F · [5 − h₂(e) − e·log₂31] with e = 1 − accuracy. It is a valid lower bound on the mutual information between answer and argmax prediction for uniform answers; it is 0 at chance and 1.52 bits per fact at accuracy 0.5 (C2). **Secondary is the unfloored log-loss gain** I_ll = Σ_f (5 + log₂ p_f), which may be negative. The floored sum is descriptive only and enters no rule."
  - Every rule in §8.2–§8.5 that uses I uses I_acc.
  - Add to CAPACITY_PARTIAL: "accuracy at 16K above the upper end of the G2 interval in both seeds and both panels".

### B2 — The usage objective's coefficient rule fails at initialization by construction

- Evidence: rev 1 §7 (lines 186–193). The threshold ln(0.5·M) = ln 512 = 6.238 nats at every size (F_b = 128). λ is measured once on the first batch, and ‖g_R‖ < 10⁻⁶ ⇒ ENGINEERING_FAIL.
  - **P8 records** (`c3_r_util_at_init.out.txt`, part 2): at update 1 on P8's 512-query batches at N = 4,096, the batch soft-usage entropy was 6.354–6.554 nats in **all 6 flat-baseline cells (above ln 512 ⇒ R_util = 0 ⇒ g_R = 0)**, and 6.057–6.214 in the tree cells (R_util ≈ 0.002–0.02).
  - Rev 1 doubles the batch to 1,024 queries and raises N to 16K/64K. Both raise the entropy further.
  - Toy (part 1): with isotropic-ish queries the hinge is off at N = 4,096 and 16,384 for spread ≥ 1.0, and at 65,536 already for spread ≥ 0.5.
- Consequences:
  - (a) Every flat usage cell (B1 flat 8, C1 flat 4) would very likely be ENGINEERING_FAIL. This is a property of the initial state, not an engineering defect.
  - (b) Where the hinge is barely active (tree), ‖g_R‖ is tiny. α·‖g_task‖/‖g_R‖ then exceeds 100 for both α = 0.25 and α = 1. **The cap sets both doses to λ = 100, so the two dose arms are the same configuration.**
  - (c) After initialization the hinge can switch on (P8 C01 batch entropy fell to 4.7 nats by update 128), but λ was fixed at an unrepresentative moment.
- Required change, replacing the coefficient paragraph:
  - "λ_u = α_u · ln 32 / (ln 512 / ln N). That is, a fully collapsed batch (H = 0) costs α_u times the chance-level answer loss in nats. α_u ∈ {0, 0.25, 1}. No measurement and no cap; doses are distinct by construction. The same absolute form for R_co: λ_c = α_c · ln 32 / (1 − 1/8)."
  - Delete the ENGINEERING_FAIL rule for small ‖g_R‖. Instead record per update whether the hinge is active and the gradient norms.
  - Also see M7: the batch-local floor is the wrong target at 16K/64K.

### B3 — Task validity is unmeasured, and the plan forbids measuring it before the single run

- Evidence:
  - (i) Identity exposure through one frozen attention layer is untested (above). C1b (stylized additive codes, assumed attention profiles) shows naive accuracy ranging from 0.94 down to 0.14 depending on attention profile and context noise, falling with F. The real profile is unknown.
  - (ii) Hamming-1 twin share is 21.5% / 62% / 98% at 2K / 8K / 32K facts (C1). Per-fact difficulty therefore grows with F independently of memory size.
  - (iii) G3 (R2 ≥ 0.95) is a learning-speed test as much as an expressibility test (M4).
  - (iv) §12 step 4 and EXECUTION_PLAN 2.1: "accuracy and loss are not written".
  - Together: a TASK_CEILING_FAIL or an R0 floor (decision-map item 4, "pause the line") is a live possibility that nobody can see before the registered run. The run would then spend the whole budget on an uninformative result.
- Required change, adding §12 step 4a "Task-validity calibration (rehearsal seeds only, before freeze)":
  - Allowed measurements:
    - (a) per-identifier-position linear decodability (32-way logistic probe) from the frozen answer-site hidden state, and the frozen-hidden nearest-neighbour accuracy, at 2K / 8K / 32K rehearsal facts;
    - (b) the R2 learning curve at each size up to 4× the registered exposure;
    - (c) no-memory and exact controls.
  - No R0, R1, tree, dense or regularized arm is run.
  - The outcome may change only a pre-registered menu: E ∈ {32, 64, 128}; identifier length ∈ {4, 5}. The rule is "smallest E at which R2 reaches 0.95 on rehearsal panels at every size; identifier length 5 if the NN control is below 0.5 at 32K with length 4". The rule is fixed in Decision 1; the outputs are written and audited.
  - This is calibration of the testbed, not tuning of a compared arm. It applies equally to every arm and complies with protocol §3 ("comparable tuning budget").

## 2. Major findings

**M1 — Training-loss positions are unspecified.**
- Evidence: §5.5 (lines 132–135) says only "1,024 positions = 128 fact exposures". P5/P8 train on every position (`p5_model.py:148`, `p8_objective.py:223`).
- On all positions, the identifier bytes are themselves memorizable. With 32,768 facts out of 32⁴, a 3-symbol prefix has on average 0.97 other completions, so byte 4 carries about 5 − E[log₂(1+Poisson(0.97))] ≈ **4.2 bits per fact** of completion information, comparable to the 5-bit answer. At 2,048 facts it is about 5 bits. That load competes for slots and dilutes the answer gradient 8×.
- Required: "Training loss is the cross-entropy at answer sites only. All other targets are masked for every arm (memory, dense, ladder). All-position NLL is reported descriptively."

**M2 — Held-out templates as the primary panel confound memory with query robustness.**
- Evidence: §4.1 (line 62), §4.4. The binding byte is the query token. A held-out binding byte shifts h by an embedding the learned projection never saw. That shifts every query, and more facts make the query space denser, so the error grows with F even for a perfect memory. The draft asks for "unseen prompt templates/contexts" (draft line 57). Unseen contexts suffice.
- Required:
  - "Primary panels A and B use training templates in contexts never seen in training: new co-record sets, record positions and order, verified by hash. Held-out-template panels H1/H2 are secondary robustness panels that enter no class."
  - Specify the template byte pool (bytes frequent in the backbone's training corpus, excluding Σ) and split T/H1/H2 from it by seed, so the held-out templates are exchangeable with the training ones.

**M3 — Identifier density is not held constant across sizes.**
- Evidence: C1. Hamming-1 twin share is 0.22 → 0.62 → 0.98.
- Required (PENDING LEAD REVIEW on the exact form): "Identifiers are 5 symbols; the 5th is the sum mod 32 of the first four (pairwise Hamming distance ≥ 2). Unseen-control identifiers are codewords at distance ≥ 2 from all trained identifiers." This needs records of 8 bytes, e.g. no prefix and 8 records, or a 0-byte prefix with the template carried by the separator and binding bytes. Alternative: keep 4 symbols but report accuracy separately for facts with and without a Hamming-1 twin.

**M4 — G3 (R2 readout ceiling) conflates expressibility with learning speed, and R2 is not an upper bound on R0.**
- Evidence: an R2 row gets a gradient on 32 updates (one per exposure). In R0 a slot is shared by about 8F/N = 4 facts, so it gets about 4× the events, and a fact can spread over 8 × 32 value dimensions. Expressibility itself is not the issue:
  - The memory adds δ = σ(g)·W_o v at the answer site. W_o is full rank generically and v is free, so δ is any 32-d vector.
  - For large ‖δ‖ the final LayerNorm input is dominated by δ, because block 1's attention and FFN contributions are LayerNorm-bounded.
  - So the reachable logits are E(γ ⊙ x̂ + β) over the LayerNorm sphere. 32 generic points in the 31-d centred space are affinely independent, so every symbol can be the argmax within Σ.
  - The achievable maximum p, and so the bit ceiling, depends on embedding norms that nobody has measured.
- Required:
  - "G3 is evaluated on the calibration of B3. In the registered run, R2 is a diagnostic. TASK_CEILING_FAIL at a size is declared only if R2 accuracy is below 0.95 after 4× the registered exposure in the calibration."
  - Before freeze, record the maximum Σ-renormalized p attainable per symbol from the frozen final LayerNorm and unembedding. This is linear algebra on frozen weights; no training.

**M5 — Optimizer effects: matched exposure is not matched optimization, and the lazy-Adam arm is confounded.**
- Evidence: C4.
  - Under dense AdamW (β 0.9/0.999), a row with a gradient once every K updates moves about √K·lr per exposure: **3.97 / 7.88 / 15.1 × lr** for K = 16 / 64 / 256 (2K / 8K / 32K facts).
  - **88–90% of that movement happens on updates where the row has no gradient** (momentum tail). This is ordinary Adam behaviour, not a P8-specific pathology.
  - After 32 exposures a row has moved 0.38 / 0.73 / 1.39. Matched exposure therefore gives the 64K memory 3.7× the per-row step of the 4K memory.
  - Row-lazy Adam (row-count bias correction) moves exactly 1 × lr per exposure, 4–15× less. With global-step bias correction it moves 3.4–5.4×.
  - So "everything else equal" (§7, line 196) is false: the lazy arm changes the effective learning rate by a size-dependent factor.
- Required:
  - (a) In every AdamW cell, record per key/value row the cumulative movement on updates with and without that row's own task gradient. This answers "movement without task gradient" directly, at no cell cost.
  - (b) Either drop the lazy arms (10 cells), or specify the bias-correction convention and add `lr × √(F/128)` compensation so per-exposure movement matches AdamW's.
  - (c) State the √K effect as a known confound of the size comparison.
  - (d) Record AdamW state bytes as the draft §6 asks.

**M6 — U\* is inflated by diffuse reads; the knock-out threshold and implementation are underspecified.**
- Evidence:
  - With cosine scores at temperature 0.2 the logit range is at most 10. A self weight ≥ 0.95 needs all 7 competitors at cos ≤ 0, which is impossible once F ≫ d (C1: w_self = 1/(1 + 7e^{−5(1−c)}) = 0.955 at c = 0).
  - Measured: median self weight is 0.42 / 0.34 / 0.29 for random 16-d codes, and 0.13–0.28 for stylized additive codes. So **all 8 selected slots usually exceed 0.05** and U\* ≈ min(N, 8 × dependent facts), mostly a restatement of accuracy.
  - An objective that spreads weight (R_util does exactly that) raises U\* without new knowledge, which can qualify a cell as PRESERVED.
  - p ≤ 2/32 is an absolute threshold. A symbol favoured by the backbone's prior over Σ can never qualify.
  - Zeroing table values per fact means about 32K full forwards at 64K. Masking per query at the answer site is cheap.
- Required, replacing §6.2:
  - "Support of a fact: the smallest prefix of its selected slots, ordered by weight, whose per-query knock-out at the answer site (selection and weights kept, values of those slots removed from the weighted sum, all other positions unchanged) makes the fact incorrect and p_f ≤ max(2/32, p_f^nomem + 0.02). U\* counts slots in at least one such minimal support."
  - Also report the weight-entropy of each fact's read.
  - Group ablations and value permutation use cached selections.

**M7 — The usage floor targets batch entropy, not memory utilization, and cannot revive dead slots.**
- Evidence: §7 (line 186). M = min(N, 1,024) does not depend on N beyond 4K. A memory using about 1,000 slots globally at 64K satisfies the floor in every batch. π is defined on each query's top-64 only (`p8_objective.py:86`), so a key that is in no query's top-64 receives no gradient from either loss and never moves (its Adam moments are zero). It can re-enter only if queries drift towards it. P8 already found 127 effective slots out of 4,096.
- Required:
  - (a) Use a global usage term: u = EMA of π-usage over the last F/128 updates (one epoch), with gradient only through the current batch's π, and R_glob = max(0, ln(min(N, 8F)/2) − H(u)) / ln N.
  - (b) State in §7 that dead keys cannot revive through gradient, and measure revival as "keys first entering any top-64 after update 0".

**M8 — Gaps and overlaps in the capacity rules and the decision map.**
- Evidence (§8.2, lines 215–231; §8.7):
  - (a) CAPACITY_PARTIAL and CAPACITY_NOT_SUPPORTED overlap: the 4K→16K step is supported while the 16K→64K step has a ratio below 2 and has plateaued. No precedence is given.
  - (b) The D04 cap ("rises … as much") has no metric. Fixed-fact I is bounded by 5 × 2,048, so its rise can almost never match a ≥ 3× proportional rise. The rule is close to vacuous.
  - (c) "Gap" in decision items 3 and 4 has no threshold or sign. R1 is not an upper bound on R0, and R2 is not one on R1 (M4).
  - (d) The wide-key arm enters no rule.
  - (e) There is no capacity-level rule for D03 (tree vs flat at 16K), although the draft makes it a family.
  - (f) Lane C's gate refers to "Lane A class at 16K", but classes are defined over all sizes.
  - (g) The plateau test compares E = 24 with E = 32. A curve growing like E^0.3 changes by 9% over that span, so a non-learning-limited null is classed UNDERTRAINED rather than NOT_SUPPORTED.
- Required:
  - Precedence order NOT REPLICATED > NOT_SUPPORTED > POSITIVE > PARTIAL > UNDERTRAINED > INTERMEDIATE.
  - Define the D04 control as a per-fact ratio: "if Fano bits per fact at 2,048 fixed facts rise by more than 25% from 4K to 64K, the proportional class is annotated EMPTY-SLOT-EFFECT".
  - Gap ≥ 0.5 bits per fact (Fano), with sign reported.
  - Wide-key rule: "If key-32 R0 supports the 16K→64K step and key-16 does not, the failure is attributed to key width."
  - D03 rule: "TREE_COMPETITIVE: tree I_acc ≥ 0.97 × flat I_acc at 16K in both seeds and both panels; logical work reported."
  - Plateau: compare E = 16 with E = 32 and require the second-half gain to be < 5% of I.

**M9 — The addressing ladder has hidden confounds.**
- Evidence (§5.3, lines 118–124):
  - R0 reads memory at all 63 positions. Its outputs feed block 1 at later records, so it also suffers interference (and, under all-position loss, serves other targets).
  - R1 and R2 read only at answer sites. R1 bypasses both the frozen state and the learned projection, and its random codes are better spread than the additive structure R0 must use (C1 vs C1b).
  - R2 uses one slot with weight 1, and its rows learn about 4× more slowly than R0's shared slots (M4).
- Required:
  - Add **R0a** (natural query, read only at answer sites) for flat at 16K and 64K (4 cells). R0a − R0 then isolates read-everywhere interference, and R1 − R0a isolates identity exposure plus the projection.
  - Report the frozen-hidden probe of B3 beside R0.

**M10 — The locality specification cannot be executed as written, and several comparisons are unspecified.**
- Evidence:
  - The P7-B simulator and layouts are not reusable "unchanged" (§8.4, line 245). `p7a_core.py:37` fixes SLOTS = 4096, and layouts assert permutations of 0..4095 (`p7a_core.py:276,321`). `p7b_layout.pair_affinity` builds a dense n² int32 matrix (`p7b_layout.py:113-124`): **1.0 GiB at 16,384 and 16 GiB at 65,536**. Layouts are serialized as int16 (`p7b_layout.py:625`), which **overflows at 65,536** (C7).
  - The traces' positions (all 63 vs the 8 answer sites) are unspecified. Under R0 the non-answer positions are 7/8 of the reads, and their near-constant queries create popularity.
  - The E ratio's case layout is unspecified (natural, or its own optimized layout).
  - The oracle "cluster-contiguous" layout is ambiguous when slots are shared. In the toy, the majority-cluster share of a slot's accesses is 0.25 under random sharing (C6).
  - CONCENTRATION_ONLY (raw ≤ 0.80, E ratio > 0.90) overlaps NO DIFFERENCE (E in 0.90–1.10).
  - C1's utilization class is relative to "its dose-zero cell". That is ambiguous between α = 0 and the α_u = 0.25, α_c = 0 cell.
- Required:
  - "Re-implement the simulator for general N with an equivalence test against P7-B at 4,096 on P7-B's recorded traces, and a sparse co-access affinity."
  - "Locality traces are answer-site reads (primary) and all-position reads (secondary)."
  - "E ratio compares case and reference each under its own optimized co-access layout, and also under identity layout."
  - "Oracle layout assigns a slot to the cluster with most calibration accesses, ties to the lowest cluster ID."
  - Precedence DEGENERATE > COLLAPSED/QUALITY_FAILED > LOCALITY_POSITIVE > CONCENTRATION_ONLY > NO DIFFERENCE/WORSE > INTERMEDIATE.
  - "C1's utilization reference is B1's α_u = 0.25, α_c = 0 cell; its locality reference is the dose-zero flat."

**M11 — Lane D comparisons are confounded.**
- Evidence (§8.5, lines 262–271):
  - "50% replay" does not say whether B's exposure is halved (equal updates) or updates are doubled.
  - Retention a_A / a_A⁰ is undefined or noisy when a_A⁰ is small.
  - "Retention exceeds dense by ≥ 0.10" cannot pass if dense retains ≥ 0.91.
  - Which parameters move in phase B is unspecified. The draft (line 97) asks for "memory-only updates".
- Required:
  - Replay arms keep 32 B-exposures and add the replayed A examples as extra rows; updates and examples are reported.
  - Classes require a_A⁰ ≥ 0.5, else NOT_EVALUATED.
  - Use the absolute retained-A accuracy difference against the best dense arm.
  - Add "phase B trains keys and values only; projections, gate and router frozen" as the memory-only arm (2 cells), or state that all addition parameters train.

**M12 — Family 2 has no exposure, update count, threshold or class.**
- Evidence: §4.2, A9 (6 cells).
- The latent-two-hop claim is **correct**: every memory query is a function of block-0 outputs, which depend only on input bytes, and memory outputs enter only block 1, which has no memory access. So no read can be conditioned on another read's result, and a held-out composition cannot be stored as a third fact.
- Two caveats:
  - (a) In-context copying by frozen block 1 is possible if identifier₂'s record appears earlier in the same context. The generator must exclude that.
  - (b) Teacher-forced chain accuracy equals terminal-fact accuracy under the chain template. Held-out chains test template transfer, not composition.
- Required: define updates, scores and a class, or drop A9 with the human's recorded approval of the narrowing (a draft requirement, draft §5 item 2).

**M13 — G2 false failures can stop a whole size.**
- Evidence: C5. Each G2 test has an exact false-fail probability of 0.0009–0.00096. The family-wise risk is 1.5% (16 control tests), 18% (216) or 45% (648), depending on where G2 is applied, which rev 1 does not say.
- Required: "G2 is evaluated on the no-memory baseline and the unseen-fact set, once per size × track × panel (16 tests), with acceptance at the 1 − 0.001/16 central interval. In dependence checks the same corrected interval is used."

**M14 — The budget omits evaluation and under-states the dense adapter.**
- Evidence: C7.
  - Training arithmetic reproduces: 108 cells; serial training 0.24 / 2.74 / 5.27 h by size against the budget's 0.4 / 3.5 / 5.25.
  - Evaluation is not covered. Uncached full forwards at 64K are about 550 GFLOP per panel; 138 per snapshot × 54 snapshots is about **15 h** at 75 GFLOP/s (about 7.5 h at the benchmark's 150), against a 2.7 h allowance.
  - The dense adapter at 64K needs 3.1–4.2 M MACs per token, 3× flat, but is budgeted at flat's time: about +2.9 h serial.
  - A9 has no update count.
  - Snapshot restoration (G4) needs Adam state, so about 50 MB per 64K snapshot, not 13 MB.
- Required:
  - Specify that evaluation reuses cached selections and weights for knock-outs, permutation and group ablations.
  - Evaluate interventions only at the matched-exposure and fixed-compute snapshots.
  - Re-project and present caps to the human at Decision 2 with rehearsal evidence (draft §14 item 2).

## 3. Minor findings (each with the required change)

- m1. Generator χ² tests have expected counts of 2 (2K, 32×32) and 0.5 (answer × cluster). Use exact or Monte Carlo permutation tests (C5).
- m2. Accuracy ties within Σ: count as incorrect.
- m3. Renormalization over Σ hides mass on non-Σ bytes. Report Σ-mass.
- m4. Context arithmetic: 64 bytes gives 63 targets with `batch[:, :-1]`; state 65-byte chunks or 1,008 targets.
- m5. Panel contexts must follow the training cluster rule. Add an evaluation-only panel with mixed-cluster contexts (no training cost) to measure dependence on cluster-mate context. Specify where the unseen-control identifiers are placed.
- m6. The 64K fixed-compute 75% snapshot (1,536) is missing. State what the 4K 1,536 snapshot is for.
- m7. The registered reduction "halve the batch at 64K" changes dynamics at one size only. Use gradient-identical chunking of the score matrix instead.
- m8. D09 sweeps ρ = 1, which contradicts "cache always smaller than the working set". Label it descriptive.
- m9. The cache is sized on distinct selected slots, while the draft says "useful working set". State the deviation or use U\*.
- m10. NOT REPLICATED is defined only in §8.2. Define it for §8.3–§8.5 (panels disagree → NOT REPLICATED).
- m11. Utilization classes overlap: IMPROVED with PRESERVED, COLLAPSED with ENTROPY_INFLATION. Give a precedence. Lane C's gate says PRESERVED (§3) but §8.4 says PRESERVED or IMPROVED.
- m12. Group ablation ("must reduce accuracy …") has no consequence. Make it a U\* interpretability condition or descriptive.
- m13. The tree has no oracle-branch arm (draft D06 "oracle-routed"). Add tree R0 with hash-assigned branch at 16K (2 cells), or state the omission.
- m14. All cells share one data draw. State that seeds replicate initialization only.
- m15. Key-on-storage accounting is an arithmetic identity. Say so.
- m16. The ENGINEERING_FAIL scope in §8.6 should exclude scientific properties (see B2).
- m17. The draft asks for per-lane analysis scripts (draft §3). The plan has one `p9_analysis.py`. Either split it or record the deviation.
- m18. λ ratio: if gradient matching is kept anywhere, ‖g_task‖ must be measured on the same parameter set as ‖g_R‖ (P8 used Θ_r; `p8_objective.py:281`).

## 4. Strongest objections (even where graded lower)

1. The study may mostly measure the frozen WikiText block 0's ability to encode random 4-symbol strings, not memory capacity (B3, M3, M9).
2. The primary metric, as written, certifies capacity in a zero-knowledge model (B1).
3. The anti-collapse objective is aimed at the wrong quantity (batch entropy) and is switched off or saturated by its own coefficient rule (B2, M7).
4. "Useful slots" counts diffuse reads (M6).
5. The optimizer confound is size-dependent and runs in the same direction as the hypothesis: bigger memories get bigger per-row steps (M5).
6. Locality positivity mostly measures whether a model's slot sharing follows the planted clusters. The reference layout already gets E ≈ 0.77 from the stream alone (C6).
7. Cheaper alternative: run B3's calibration plus a flat-only Lane A first (R0, R0a, R1, R2 and dense at 3 sizes, about 40 cells). Only if Lane A is at least PARTIAL, launch B, C and the tree arms in the same frozen design. Lane B/C interpretation is gated on Lane A anyway, so running them in parallel spends about 40 cells that cannot be interpreted if A fails. This conflicts with the draft's "parallel tracks"; it is a human choice.

## 5. Governance: where rev 1 departs from the human draft

| Draft requirement | Rev 1 | Assessment |
|---|---|---|
| Two task families with single- and two-hop scores (draft §5) | Family 2 narrowed to explicit chains, one size, no classes | Narrowing is scientifically justified (M12) but needs **explicit human acceptance** at Decision 1 |
| "unseen prompt templates/contexts" | held-out templates as primary | Stricter than required, and confounded (M2) |
| "equal key/fact-frequency options" | equal frequency only | Acceptable; record that skewed frequency is untested |
| D06 "oracle-routed and ordinary-routed" | query/address oracles; no oracle routing for the tree | Partial (m13) |
| D03 tree must beat strong flat | no capacity-level D03 rule | Gap (M8e) |
| Cache "relative to measured useful working sets" | distinct selected slots | Weaker (m9) |
| MPS optional, only if validated | MPS not used | Not a weakening |
| 2 GiB / worker, 8 GiB aggregate, 8 h | 3 GiB / 8 GiB / 10 h requested | Flagged openly; the human decides. Approval should rest on rehearsal evidence (draft §14 item 2), i.e. at Decision 2, not 1 |
| "≥ 2× projected headroom per stage" | claimed | Not demonstrated, because evaluation is unbudgeted (M14) |
| "Report every trainable parameter, initialized slot and optimizer state byte" | parameter counts only | Add state bytes (M5d) |
| Each workstream with its own analysis script | one analysis module | m17 |
| Ordering: draft §12 has implementation, smoke tests and READY TO FREEZE before final approval; repo rule has no implementation before a recorded spec approval | Decision 1 (approve spec for implementation and rehearsal), then implementation, rehearsal, audit, freeze, then Decision 2 (approve final revision and run) | **Resolves the conflict correctly**, provided Decision 1 is recorded as approval of this specification (not a chat request) and any post-rehearsal change to the matrix or thresholds returns to the human at Decision 2 |
| "Rehearsal accuracy is not written" | — | Enforceable only by code review: the auditor checks that the rehearsal entry point's record schema is a whitelist (time, RSS, finiteness), and loss is still computed in memory. Contradicts the budget's need to time evaluation, and blocks B3's calibration. Replace with B3's scoped calibration plus the whitelist |

PENDING LEAD REVIEW (scientific choices I do not make):
- identifier length and code (M3);
- E menu (B3);
- whether to drop A9 or the lazy arms;
- staged versus parallel execution (objective 7);
- the absolute λ values (B2).

## 6. What this design can and cannot establish (with the required changes)

**Can, within this testbed:**
- whether a frozen 27K-parameter byte backbone plus a flat or tree key-value memory stores more answer information (Fano-bounded) as slots and facts grow 4K→64K, at matched exposure and at fixed updates, against a parameter-matched dense adapter;
- where a failure sits: identity exposure (probe, NN, R1−R0a), read interference (R0a−R0), key learning (R2−R1), key width (16 vs 32), readout (R2, calibration);
- whether a bounded usage term raises minimally-supported useful slots without losing accuracy;
- whether a co-access term lowers count-preserving-null-adjusted simulated page misses beyond an optimized post-hoc layout on a planted-cluster stream;
- whether a second disjoint fact set can be added from a snapshot with less forgetting than a dense adapter.

**Cannot:**
- anything about natural-language knowledge, reasoning or composition (Family 2 is lookup by construction);
- capacity beyond 64K slots or with a trainable backbone;
- statistical generalization across data draws (one draw; two init seeds; one replicate parent);
- physical storage I/O, latency or throughput (simulation and logical counts only);
- that locality emerges without planted structure (equal-frequency, planted clusters are a best case);
- any claim about Astra validation or human approval.

## 7. Files

`opus_checks/`, scripts with their outputs:
- `c1_addressing_capacity.py`: random-code self weight, naive accuracy, σ_min, Hamming twins
- `c1b_additive_identifier_codes.py`: stylized
- `c2_floored_information.py`
- `c3_r_util_at_init.py`: toy, plus P8 records read-only
- `c4_adam_sparse_rows.py`
- `c5_gate_statistics.py`
- `c6_null_identifiability.py`
- `c7_matrix_budget.py`

Each has a matching `.out.txt`.
