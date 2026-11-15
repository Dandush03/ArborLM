# ADR-0018 design revision 1 — independent design review (2026-11-14)

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), auditor role, launched by the Claude lead. I did not write ADR-0018 or anything under `studies/p9/`. I wrote the calibration audit (`docs/reviews/p9-calibration-audit-2026-11-14/AUDIT.md`) and the ADR-0017 design checks (`docs/reviews/adr-0017-design-2026-11-14/`). Where this review corrects one of those, it says so.
- **Status of this document:** independent engineering and mathematical evidence only. **Not Astra validation (Astra review: NOT_PERFORMED) and not human approval.** Scientific choices are marked `PENDING LEAD REVIEW`; numbers in brackets in the required changes are the lead's choice.
- **Reviewed:** `docs/decisions/ADR-0018-query-interface-prerequisite.md` at commit `80155d6` (sha256 `d9fbabb0…4fba07`), in full; ADR-0017 revision 3 in full (including §15.2); my calibration audit and its scripts and outputs; `AGENTS.md`, `CLAUDE.md`; the relevant parts of `studies/p9/` (`model.py`, `core.py`, `data.py`) and `RESOURCE_BUDGET.md`.
- **What I ran** (all on CPU; nothing registered; no memory system built or trained):
  - `b1_code_families.py` — pure math on synthetic checksum identifiers. No backbone, no study data.
  - `b2_window_query_probe.py`, `b3_multihead_probe.py` — representation-only probes on the **frozen** backbones B101 and B102, **rehearsal draw 0** (data seeds 179001+, the draw that already informed the design). **Draw 1 was not touched.** No learned keys, values, output projection, gate or block 1. Each candidate query map is fitted by a contrastive objective. It is then read against an **oracle store**: key = mean query of the fact over its training contexts, value = one-hot answer, read exactly as ADR-0017 §5.1 (cosine, top-8, softmax at T = 0.2, ties wrong), on Panel A.
  - `c1_dense_window_toy.py` — a toy MLP of the D7 shape on ideal one-hot inputs. No backbone, no study data. **It is not the D7 arm.**
  - `f1_annotation_overlap.py` — pure arithmetic on the class and annotation rules.
- **Not run:** any arm of ADR-0018 §3 (N, W7, E7, A1, R1, R2, D, D7, tree) as a memory system; any training of a backbone parameter; anything on rehearsal draw 1 or registered seeds.
- **Environment:** Apple M5 Max, 48 GB, macOS (Darwin 27.2.0), CPU only. Python 3.12.14, torch 2.8.0, `uv run --locked`; no package added. Commands are at the end. Outputs are in `outputs/`.
- Nothing in `studies/`, `results/`, `configs/`, `experiments/` or any ADR was edited. Nothing was committed.

## Verdict: NOT READY FOR HUMAN DECISION 1

There are **2 BLOCKERS, 6 MAJORS and 14 minors**. All of them are text changes; none needs a new probe. The design's core arm (W7) is **feasible by calculation and by probe**. The single-head arm (A1) is not. The blockers concern what the study can conclude:

- **B1.** As written, an outcome would be read as the answer to the human's question, and it is not that answer.
- **B2.** An unmeasured ceiling can print "no tested interface works".

If B1, B2 and M1–M6 are applied as written below, I expect a narrow confirmation check to suffice, not a full re-review.

## BLOCKERS

**B1 — The design does not test "how the language model communicates what it needs"; it tests a memory-side encoder of the input window, and the probes show the backbone contributes nothing to it (A).**

The interface in every learned arm belongs to the memory, not the model. W7 and A1 are new parameters that read the frozen block-0 states, and E7 reads raw embeddings. Measured on the frozen states (oracle store, Panel A, B101):

- E7 is at least as good as W7 at every size (0.980 vs 0.957 at 32,768 facts).
- Attention over raw embeddings is far better than attention over block-0 states: 4 heads 0.85 vs 0.34; one head 0.78 vs 0.24 at 8,192.

So the frozen backbone *hurts* addressing. A W7 "INTERFACE_WORKS" would show that the memory can read its key from the input bytes. The selection rule would then carry that into ADR-0017 as "the interface". §14 item 2 asks the human about this, but without this evidence and without a concrete alternative.

**Required change (paste-ready):**

- §2, new first paragraph: "**Scope.** W7, E7 and A1 are query encoders that belong to the memory; they read the frozen states (or the embeddings) of the input window. A WORKS class shows that a memory-side encoder can address facts on this task. It does not show that the language model communicates what it needs. If BACKBONE ADDS NOTHING holds, the outcome is reported as 'addressed by a memory-side encoder of the input; the frozen backbone contributes nothing to addressing'."
- §8 selection rule, after step 2: "The selected interface carries its backbone annotation into the revision of ADR-0017 and into every summary."
- §14 item 2, replaced by: "**Decision on the question asked.** (a) Accept that this study tests memory-side encoders only, so that 'how does the language model communicate what it needs' stays open; or (b) add arm **BB**. BB trains the block-0 attention (qkv and output projection, 4,224 parameters) together with the memory, and the memory reads arm N's natural query W·h_t at the answer site. It has two controls with the same trainable attention: D plain, and the no-memory backbone trained on the answer loss. It runs at [16,384 and 65,536] slots × seeds 1801/1802 [+ B102 replicate at 16,384], = [10–12] cells. It needs approval to train a backbone parameter. G4 forward invariance does not apply to BB. The backbone's next-byte loss on its own corpus rows is reported before and after."
- Evidence to cite there: the input a retrained block-0 attention sees is the embedding. 4 heads over embeddings reach 0.99 / 0.97 / 0.85 in the oracle-store probe (B101; B102 0.98 / 0.94 / 0.81). That is representation-only evidence that BB is feasible, not a result.

**B2 — U is calibrated on R2 alone, while every class needs R1 ≥ 0.5 and the selection needs WORKS at all three sizes; a ceiling miss at 65,536 becomes "no tested interface works" (D, F, G).**

- **What calibration measures.** R2 has dedicated slots and no key learning. With the alphabet loss it reaches ≥ 0.95 within 2,048 updates at 4K and 16K (my audit), so §6 will probably select the smallest U.
- **What U then gives the largest size.** With U equal at every size, 32,768 facts get 8 / 16 / 32 exposures per fact at U = 2,048 / 4,096 / 8,192. R1, which learns keys, has never been run in P9. The D7-shape toy shows that this regime can limit learning: 0.05 / 0.10 / 0.16 at 32,768 facts, against 1.00 at 2,048 and 8,192 facts by 2,048 updates.
- **How the rule turns this into a negative.** If R1 < 0.5 at 65,536, that size is NOT_EVALUATED. Steps 1 and 2 then fail, and step 3 prints "no tested interface works; ADR-0017 stays blocked on this backbone". That is a negative scientific conclusion produced by an unmeasured ceiling.

**Required change (paste-ready):**

- §6: "Allowed: controls; **R2 and R1** at the three sizes with the alphabet loss, snapshots at 1,024 / 2,048 / 4,096 / 8,192 [/ 16,384] updates. **Rule:** U is the smallest of {2,048, 4,096, 8,192 [, 16,384]} at which, at every size, R2 accuracy ≥ 0.95 **and R1 accuracy ≥ [0.90]**. Each is the minimum over the two B101 calibration runs (init seeds [179101, 179102]) and both panels; the B102 run is reported. A size at which no U qualifies is `TASK_CEILING_FAIL` (R2) or `ORACLE_QUERY_FAIL` (R1) and is not run. R1 is an oracle rung, not an interface; no interface arm is run."
- §8, replacing the last sentence: "A size that is TASK_CEILING_FAIL, ORACLE_QUERY_FAIL or NOT_EVALUATED removes itself from the selection rule, and the outcome names the sizes the selection rests on. If [65,536] removes itself, no interface is selected and the outcome is **INCONCLUSIVE AT 65,536**, not step 3."

## MAJORS

**M1 — A1 is a weighted bag of one shared value map and is predictably far below W7; the rule's preferred arm is close to unreachable (B, H).**

- **Probe (oracle store), one head over block-0 states:**
  - B101: 0.34 / 0.24 / 0.16 at 2,048 / 8,192 / 32,768 facts.
  - B102: 0.42 / 0.32 / 0.21.
  - Not optimizer-limited: 0.365 with three times the steps.
- **Pure math.** The idealization (shared symbol table, free position weights, no noise) gives 0.81 at 32,768, against 0.985 for free per-position tables.
- **What helps.** Four heads of 8 (same 3,072 parameters, the backbone's own attention shape) give 0.66 / 0.49 / 0.34 over the states and 0.99 / 0.97 / 0.85 over embeddings.

**Required change:** "A4: one attention layer of 4 heads × 8 (q, k, v 32 × 32, bias-free, 3,072 parameters), query from h_t, keys and values over [h_{t−15..t} | the full causal prefix], then W." Replace A1 by A4, or run both [lead's choice]. Add **A4E** (the same layer over embeddings) at 16,384, 2 seeds, so that the backbone contrast exists for the head-based arm. §3's claim that "A1 does not know the record length" must be reworded: a 16-position window is two records and is also task-shaped. The window length is decisive: one head over 7 positions gives 0.81 / 0.62.

**M2 — The two dense annotations can both fire, D7's read position is unspecified, and the D7 outcome is predictable (C).**

- **They are not exclusive.** BEATS DENSE WINDOW (I_acc ratio ≥ 1.10) and DENSE WINDOW SUFFICES (accuracy ratio ≥ 0.90) hold together in 698 grid pairs. Example: arm 1.00 and D7 0.95 give an accuracy ratio of 0.95 and an I ratio of 1.12.
- **The toy outcome.** A D7-shape MLP (h = 786 / 3,090 / 12,306, matched exactly: 256h + 1 = N·48 + 4,609) memorizes 2,048 and 8,192 ideal facts by 2,048 updates. At 32,768 facts it reaches only 0.16 after 8,192 updates.
- **What that predicts.** SUFFICES at 16,384 and probably not at 65,536. That would be a per-fact learning-rate effect under matched updates, not evidence about capacity or about the interface.

**Required change:** "D7 (and D plain) add their output at answer sites only. With r = I_acc(arm) / I_acc(D7) at a size and both B101 seeds: **BEATS DENSE WINDOW** if r ≥ [1.10]; **DENSE WINDOW SUFFICES** otherwise. It is printed per size and does not change the interface class. Reading fixed now: SUFFICES means a dense adapter on the same window does as well within U updates at that size. It is a statement about this task and budget, not about the query interface or about memory in general."

**M3 — BACKBONE ADDS NOTHING is one-sided and already predicted (A, H).**

- Probe E7 vs W7: B101 1.000 / 0.999 / 0.980 vs 1.000 / 0.992 / 0.957; B102 1.000 / 0.999 / 0.980 vs 0.998 / 0.993 / 0.953.

**Required change:**

- §8: "BACKBONE ADDS NOTHING if E7 ≥ [0.97] × W7; **BACKBONE HURTS ADDRESSING** if E7 ≥ [1.03] × W7 (both at 16,384, both seeds); the same pair for A4E/A4."
- §2 H18-BB: "Auditor's probe on rehearsal draw 0 predicts E7 ≥ W7."

**M4 — Class precedence is incomplete (F).** NOT REPLICATED has order "—", and "seeds disagree → INTERMEDIATE" is outside the table.

**Required change:** use this table, first match wins.

| Order | Class |
|---|---|
| 1 | NOT REPLICATED (Panels A and B give different classes) |
| 2 | NOT_EVALUATED |
| 3 | INTERMEDIATE (the two B101 seeds give different classes) |
| 4 | WORKS |
| 5 | PARTIAL |
| 6 | FAILS |

Each class is decided per panel, from both B101 seeds.

**M5 — The imported P9 code is called audited, but it is not (I).**

- My calibration audit covered R2, the probes, G2, the controls and the exposure rule only.
- R1 codes, flat and tree selection, the dense adapter, the evaluation and minimal supports, and the job manager were tested by their implementers and never run at scale or audited.
- G4's "arm N bit-identical to ADR-0017's R0a" cannot hold for training, because the loss differs.

**Required change:**

- §11: "Imported P9 code is tested, not audited. The ADR-0018 implementation audit covers every imported path used."
- §9 G4: "for equal parameters and inputs, arm N's forward equals ADR-0017's R0a forward bit for bit; training differs by the loss."

**M6 — Matched updates fixes F3 and inverts it (D).**

- The shared parameters (W, wo, gate) now get equal updates at every size, which fixes F3.
- Exposures per fact now differ 16-fold: 256 / 64 / 16 at U = 4,096. The smaller memories are favoured, and 65,536 is the binding size of "works at all three sizes".
- Using it as the only estimand is right for a study that derives no capacity class.

**Required change:**

- §4: "Exposures per fact are reported per size."
- §13: "A difference in class between sizes is not evidence about capacity: exposures per fact differ sixteenfold."

## Minors

1. §10 "0.128 s per update at 65,536 slots" is ADR-0017's planning allowance (3 × a stand-in), not a P9 measurement. The measured P9 R2 cell at 65,536 slots ran 32,768 updates in 386 s (0.012 s/update). The projection is plausible.
2. Seed namespaces collide at draw 10: `core.rehearsal_seeds(k)` = 179001 + 100k + i, which reaches 180001 (ADR-0018's registered data seeds). State "rehearsal draws k ≤ 9", or move the registered data seeds to [181001+].
3. §6/§7: the init seeds of the calibration runs are not given.
4. N is not run at 4,096, so H18-NAT is assessed at 16K and 64K only. Say so, or add 2 cells.
5. R1 is a reference, not a ceiling: optimized additive codes equal or exceed random codes (32K: 0.985 vs 0.982; 2K median self weight 0.48 vs 0.42), so η may exceed 1. Rename it the "oracle-query reference".
6. The interface classes use an accuracy ratio and the annotations an I_acc ratio. Use one metric family [lead's choice].
7. §5 should name the Σ-renormalized log-loss gain (ADR-0017 §6.1 secondary) beside the descriptive 256-way loss.
8. §1 says the 256-way loss "slows learning roughly fourfold". The audit measured "severalfold" (16K at 2,048 updates: 0.68 vs 0.993). Use the measured statement.
9. The status line lacks the AGENTS.md marker `SPEC: PENDING ASTRA REVIEW`.
10. ADR-0017 §15.2 records the lead's intent as "a new revision" of ADR-0017. ADR-0018 departs from that and asks in §14.1, which is right. It should also state the cost: ADR-0017 still needs its own revision, audit, calibration and two approvals afterwards.
11. §10's "3 hours for calibration, rehearsal and the run together" is a new figure. The human set ADR-0017's budget; ask for this one explicitly at decision 1.
12. W7's extra-parameter count (3,072) and A1's (3,072) are right. The D7 widths 786 / 3,090 / 12,306 match the 0.1% tolerance exactly.
13. Tree arms: TREE ROUTES enters no rule and the tree is not the question (4 cells). Keep them only if the lead wants routing evidence before ADR-0017.
14. "Value permutation and disabling give chance" (WORKS) should name the G2 interval as the definition of chance, as ADR-0017 does.

## B. Feasibility by calculation and probe (key numbers)

**What the numbers mean.** They come from an oracle-store read: naive accuracy with one-hot values at top-8 and T = 0.2. Learned values would raise them, and an answer-loss-trained query might not find the map the probe finds. They are **representation feasibility, not predictions of the arms**.

**Pure math, no backbone (`b1`; checksum identifiers, no noise, key = query; key width 16 unless stated):**

| Code family | 2,048 | 8,192 | 32,768 | 32,768, width 32 |
|---|---|---|---|---|
| R1 random unit codes | 1.000 | 0.997 | 0.982 | 1.000 |
| additive, random tables (a random linear W) | 0.999 | 0.985 | 0.940 | 0.999 |
| additive, optimized per-position tables (best linear W) | 1.000 | 0.999 | **0.985** | 1.000 |
| one shared table × position weights (idealized one head) | 0.993 | 0.953 | **0.813** | 0.873 |
| one-hidden-layer MLP query | 1.000 | 1.000 | 0.988 | 1.000 |

**Frozen backbone, rehearsal draw 0, Panel A (`b2`, `b3`):**

| Interface | B101 2K | B101 8K | B101 32K | B102 2K | B102 8K | B102 32K |
|---|---|---|---|---|---|---|
| N (W·h_t) | 0.040 | 0.033 | 0.032 | 0.037 | 0.030 | 0.031 |
| E7 (embeddings) | 1.000 | 0.999 | 0.980 | 1.000 | 0.999 | 0.980 |
| **W7** | 1.000 | 0.992 | **0.957** | 0.998 | 0.993 | 0.953 |
| W7, key width 32 | 1.000 | 0.997 | 0.999 | — | — | — |
| W7 MLP (256 hidden) | 1.000 | 0.999 | 0.972 | — | — | — |
| **A1** (1 head, 16 positions, states) | 0.344 (0.365 at 3× steps) | 0.242 | **0.157** | 0.416 | 0.315 | 0.211 |
| A1, 7 positions | 0.806 | 0.616 | — | — | — | — |
| A1 over embeddings | 0.929 | 0.782 | — | 0.913 | 0.749 | 0.546 |
| A4 (4 heads × 8, states) | 0.656 | 0.490 | 0.345 | 0.669 | 0.487 | 0.354 |
| A4E (4 heads × 8, embeddings) | 0.987 | 0.968 | 0.852 | 0.983 | 0.945 | 0.810 |
| R1 (reference) | 1.000 | 0.997 | 0.983 | 1.000 | 0.997 | 0.983 |

**Answers to the questions in B:**

- **Can W·[h_{t−6..t}] separate the identifiers at T = 0.2, top-8, width 16? Yes.**
  - W7's own key ranks first for 100% of Panel A queries at every size.
  - The accuracy loss at 32,768 facts (0.957) comes only from the self weight (median 0.27) competing with neighbours' one-hot answers. R1 has the same loss (0.983). Learned values remove most of it.
  - Representational η ≈ 0.957 / 0.983 = 0.97 (B101) and 0.953 / 0.983 = 0.97 (B102). There is no generalization gap: training contexts give 0.961.
- **Is W7 doomed at 65,536 by construction? No.**
  - My ADR-0017 check C1b (0.14–0.58 at 32K) assumed *fixed* attention profiles, a random projection and up to 30% context noise. A linear W has a **separate** table per position, so it can equalize and optimize the codes. The checksum symbol, a mod-32 function of the other four, adds a non-additive component.
  - Free per-position additive codes reach 0.985 at 32,768 (equal to R1). C1b's pessimism does not transfer to W7. **This corrects the implication the brief drew from my C1b**; C1b itself stands as a stylized statement about fixed-profile codes.
  - The "three sizes" requirement is therefore not unfair to W7 representationally. It can still be unfair through the training budget (B2).
- **Width 32 or a non-linear query?** Not needed for feasibility. They do help at 32,768: 0.999 with width 32 and 0.972 with the MLP, against 0.957. Width 32 would be the cheapest margin if the lead wants one. R1 and W7 should then use the same width.
- **A1 is "additive" in the worse sense.** One head forms Σ_j α_j V h_j with one shared V. The symbol code is the same at every position up to block-0 effects, so the query is close to a weighted bag of symbols. The idealization falls to 0.81, and the real states to 0.16–0.34.
- **Product/hash codes** are R1 (the reference); as an interface they make the address an oracle, which is not the question.

## Answers to A–J (brief)

**A.**

- **Does it dodge?** In effect, yes (B1). Whether the human accepts a memory-side encoder as "the model telling the memory" is the human's decision, but it must be taken with the evidence that the frozen states add nothing and hurt attention-based forms.
- **The minimal honest version where the model forms the query** is BB: trainable block-0 attention, the natural query at the answer site, and matched dense and no-memory controls. It needs approval to train a backbone parameter. `RESEARCH_HANDOFF.md` names joint training of backbone and memory as the eventual path (lines 93 and 242), so this does not break the north star. It does break the P4–P8 frozen-backbone lineage.
- **Separate ADR or revision of ADR-0017?** A separate prerequisite ADR is the cleaner structure, because ADR-0017's hypotheses stay untested and its records stay as they are. The human must choose it explicitly (minor 10).
- **The selection rule** is fixed and non-adaptive. It is unsound in two ways: it can be decided by a ceiling miss (B2), and its first step is nearly unreachable for an architectural reason (M1).

**C.**

- **Is D7 a fair comparator?** Yes: same window, same updates, same parameters to within 0.1%. Through its hidden layer it can compute a non-linear query, which is stronger than W7's linear one.
- **Will it trigger DENSE WINDOW SUFFICES?** Very likely at 16,384 (toy). The right reading is "on this task and budget, a dense adapter on the same window suffices at that size". It is not "memory not needed" in general, and not a statement about the interface (M2).
- **What it means for the project's question.** At 8,192 facts the window carries the identifier, and a small dense store can hold the answers. The memory question only becomes informative where the dense adapter stops keeping up.

**D.** Fixes F3; inverts the exposure bias; the right estimand here, provided the ceiling is calibrated on R1 (B2, M6).

**E. Alphabet-only loss.**

- No downside for the rules. Scoring is within Σ, and memory reads only at answer sites, so mass the memory moves onto non-Σ bytes at the answer site only worsens the descriptive 256-way loss.
- Training is no longer comparable with ADR-0017 R0a and P4–P8 (all 256-way). G4 must say so (M5).
- The dense arms must also act at answer sites only, or they change non-answer positions with no loss attached (M2).
- The 256-way report is enough if the Σ-renormalized log-loss is named too (minor 7).

**F. Classes and thresholds.**

- Reachable and not vacuous. η is well defined when R1 ≥ 0.5, but R1 is a reference rather than a ceiling (minor 5).
- **Perverse path:** B2.
- **Mixed metrics:** at R1 = 1.0, WORKS needs accuracy ≥ 0.90 (4.04 Fano bits), while the annotations use bit ratios (minor 6).
- **G2:** the alphabet loss does not change G2, which uses the no-memory baseline. Unseen-fact LEAKAGE remains meaningful: a learned query maps an unseen identifier near its two-symbol neighbours, whose answers are independent.

**G. Calibration.**

- The aggregation (minimum over the B101 runs and both panels; B102 reported) is now specified. The init seeds are missing (minor 3).
- The rule selects on the wrong rung (B2).
- Draw 1 is sufficient. This review used only draw 0 and synthetic data, so draw 1 is still unobserved.

**H. Matrix and budget.**

- The count of 40 is right (16K: 10 arms × 2 = 20 + 4 replicates; 64K: 5 × 2; 4K: 3 × 2).
- Missing: A4 or A4E and the backbone-contrast for heads (M1); N at 4K (minor 4); BB if the human chooses it (B1).
- The tree arms are optional (minor 13).
- The budget is plausible. Per update at 65,536: answer-site key scoring is 128 × 65,536 × 16 ≈ 1.3·10⁸ multiply-adds, and D7 forward ≈ 128 × 12,306 × 256 ≈ 4·10⁸. Against the measured 0.012 s/update for R2, that is ≲ 0.05 s/update, so 8,192 updates take about 7 minutes per 65,536 cell and the matrix about 2–3 hours serial.

**I. Governance.**

- A new package that imports `studies/p9/` without editing it is consistent with ADR-0017's blocked status: blocked forbids execution of ADR-0017, not reuse of its code. The conditions are M5, and records labelled with the new study's code, not P9.
- The human said "only then authorize a new execution", and §12's two decisions respect that.
- §14.2 must be asked as in B1.
- §10's figure needs the human (minor 11).
- The roles and "Astra review: NOT_PERFORMED" are stated correctly.

**J. A cheaper and sharper alternative** (for the lead; not required):

- **(i)** Put the representation probes of this review, with the oracle store and no memory, into the draw-1 calibration as reported-only numbers. They cost minutes and would have predicted A1's failure.
- **(ii)** Run a 2 × 2 at 16,384 and 65,536: query formed by {memory-side W7, backbone-side BB} × {memory, D7}, with R1 as reference and E7 for the backbone contrast. That is about 20–24 cells and drops the tree arms. It answers the human's question directly, and is cheaper than 40 cells that answer a narrower one.

## What this study could and could not tell the human

1. **Could:** whether a small encoder belonging to the memory, reading the last seven input positions, lets a learned memory address 2,048–32,768 facts. The probe says very likely yes for the linear window and likely no for a single attention head.
2. **Could:** whether this frozen backbone helps addressing. The probe already says no: raw embeddings do as well or better, and much better for attention-based queries.
3. **Could not (as designed):** how a language model communicates what it needs. No arm lets the model itself form the query; that needs a trained part of the backbone (arm BB), which is a human decision.
4. **Could not:** anything about capacity scaling, locality, natural text or the ArborLM concept; and the sizes differ sixteenfold in exposures per fact.
5. **If W7 is selected,** ADR-0017 would test a memory with its own input encoder that knows the record length. That is a different system from the P4–P8 memory addressed by the backbone's state, and it must be reported as such.

## My own errors, discarded runs and caveats (kept)

- `outputs/b1_smoke_2048.log` and `outputs/b2_smoke.log` (with `b2_b101_2048_N_W7_A1-16_R1.json`) are smoke runs. The smoke A1-16 gave 0.3345 against 0.3442 in the full run with the same seeds. The difference is the model-initialization order (one global torch seed, other variants built first), so the A1 numbers carry about ±0.01 of init noise.
- I started two copies of a wait loop by mistake (shell only; no computation).
- To save time I ran B101 at 32,768 facts as a separate process with a reduced variant list. I then **killed** the original loop's own 32,768-fact B101 process just after it started; it produced no output, which is why that background task reports exit code 1. A1 over 7 positions and A1 over embeddings were therefore not run for B101 at 32,768 facts.
- Seed hygiene: my scripts use their own `torch.Generator` constants 180101–181900. Those numbers fall in ADR-0018's proposed registered data-seed range (180001+). They are not the study generator (`studies.p9.data._derive`), and no study stream was generated with them, so nothing leaked. The lead may still prefer registered seeds that avoid them (minor 2).
- The probe objective is contrastive at T = 0.05 with 8 training contexts per fact. That is a representation search and may be easier than learning the map through the answer loss and top-8 selection. The oracle store with one-hot values is pessimistic about values. Both directions are stated wherever numbers are used.
- The D7 toy bypasses the frozen block 1, the final norm, the tied unembedding and the gate. Its numbers are optimistic for 2K/8K and say nothing exact about 32K.
- Correction to my earlier work: the brief summarised my C1b as "additive codes fall to 0.14–0.58 at 32K". That holds for fixed attention profiles with noise. It does not hold for a learned per-position linear map (see B).

## Commands (from the worktree root; all `uv run --locked`)

```sh
uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b1_code_families.py 2048            # smoke
uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b1_code_families.py 2048 8192 32768
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b2_window_query_probe.py b101 2048 N W7 A1-16 R1   # smoke
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b2_window_query_probe.py b101 {2048,8192}
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b2_window_query_probe.py b101 32768 W7 E7 A1-16 W7-mlp W7-k32 N R1
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14:docs/reviews/adr-0018-design-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b3_multihead_probe.py b101 {2048,8192,32768} A4-16 A4E-16
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14:docs/reviews/adr-0018-design-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b3_multihead_probe.py b101 2048 A1-16L
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b2_window_query_probe.py b102 {2048,8192,32768} N E7 W7 A1-16 A1E-16 R1
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14:docs/reviews/adr-0018-design-2026-11-14 uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b3_multihead_probe.py b102 {2048,8192,32768} A4-16 A4E-16
uv run --locked python docs/reviews/adr-0018-design-2026-11-14/c1_dense_window_toy.py
uv run --locked python docs/reviews/adr-0018-design-2026-11-14/f1_annotation_overlap.py
uv run --locked ruff check .
```

Output logs: `outputs/b1_code_families.log`, `outputs/b2_b101.log`, `outputs/b2_b101_32768.log`, `outputs/b3_b101.log`, `outputs/b3_b101_A1-16L.log`, `outputs/b2b3_b102.log`, `outputs/c1_dense_window_toy.log`, `outputs/f1_annotation_overlap.log`; per-run JSON `outputs/b2_*.json`. Wall time per probe variant: 26–60 s at 2,048 facts and 6.5–10 minutes at 8,192 and 32,768 facts (contended, 2–3 processes).
