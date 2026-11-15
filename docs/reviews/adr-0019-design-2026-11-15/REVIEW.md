# ADR-0019 (P9-II) design revision 1: independent specification review

- **Reviewer:** Claude Opus 5.5 (model id `claude-opus-5-5`), specification auditor. I ran in a context separate from the integration work and did not touch git state, GitHub or any tracked file. This review is independent engineering and mathematical evidence. **Astra review: NOT_PERFORMED. This is not Astra validation and not a human approval.** The human lead has delegated self-approval of this ADR to the lead, so this review is the main independent check, and I wrote it adversarially.
- **Object:** the draft `ADR-0019-robust-sparse-address-learning.md`, "DESIGN REVISION 1 — NOT YET REVIEWED", which sits outside the repository in the session scratchpad (214 lines). I checked it against the human lead's binding requirements as relayed in my task, ADR-0017 §4–§6, §8.1, §8.6, §15.3–§15.9, §18, `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`, `docs/reviews/p9i-results-2026-11-15/REVIEW.md` (with its outputs), and `studies/p9i/`, `studies/p9/` at worktree HEAD `413d747` (branch `claude/adr-0017-design`).
- **Environment:** macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0, `uv run --locked` (no lock change, no new dependency). All scripts and outputs are in this folder. `uv run --locked ruff check --config docs/reviews/ruff.toml --extend-ignore E501,I001,E401,E702,F841,E701,E402,F401 <folder>/*.py` passes.
- **What I ran:** c1 and c2 (pure arithmetic and synthetic, no data); c3 (a 256-update diagnostic training of W7 answer-only on **rehearsal draw 0**, init seed 600001, with my own trainer); c4 (re-scoring, with my own forward, of the three W7 parameter sets the P9-I review trained on the **unit-test seed sets p9i-test-0/1/2**); c5 (arithmetic on the P9-I registered train records and the ledger); c6 (a synthetic AdamW simulation). I also searched the repository, `experiments/` and the session scratchpads for uses of rehearsal sets 3, 4 and 5 and of seeds 190001 and above.
- **What I did not run:** anything on rehearsal sets 3, 4 or 5 or on any 1900xx seed; any registered stage; any training beyond the 256 updates of c3; any edit to a tracked file; any commit.

## Verdict: **NOT READY** for the lead's self-approval

There are three blockers and nine majors. Each one has replacement text below. Most of the fixes are wording or rule changes that cost no cells, and the recommended matrix keeps Stage 1 at 128 cells (§B). None of the fixes relaxes a threshold. Several make a rule stricter, and the rest close gaps through which a likely outcome would be misread.

Numbers in **[brackets]** are the lead's to choose. Any bracketed number must be fixed before calibration and must not be revisited after it.

---

## Key evidence (diagnostic, not results)

| Check | Script / output | Finding |
|---|---|---|
| Address loss vs answer loss, gradient on `wq` and keys | c3 (rehearsal draw 0, W7, 4,096/2,048) | At init: ‖∇wq‖ 6.45 (L_addr) vs 4.3e-4 (answer). In the collapsed state at update 256 (mean cos 0.956, 4 distinct top-1 slots of 512): wq 0.368 vs 0.0067 (55×), keys 4.105 vs 0.0144 (285×). Per-site L_addr gradients on z point in diverse directions (mean pairwise cosine 0.020). **A1-S gives the same magnitude:** wq 0.403, keys 4.10. |
| L_addr floor at τ_a = 0.2 (best case: query = target key) | c2(b) | 4.09 / 5.47 / 6.84 nats at N = 4,096 / 16,384 / 65,536. The loss never saturates. |
| A4 soft read over all N at τ = 0.2 (best case) | c2(a) | Weight outside the top 8: **0.956 / 0.987 / 0.996** at N = 4,096 / 16,384 / 65,536. The read concentrates only at τ ≈ 0.05 (4,096; 2% outside) or ≈ 0.02 (65,536). |
| Centred-query cosine (A5) | c2(c), c3 | Slot-collapsed queries (3–4 distinct top-1 of 512, participation rank 1.1–1.6) have centred mean cosine **+0.0002 to +0.002**. In the synthetic case it is −0.002 for rank-1, rank-2 and healthy residuals alike. |
| Fact-independent structure left after global centring | c3 | (separator byte × record index) explains **0.56** of the centred query variance at init and **0.73–0.74** in the collapsed state (120 groups). The common share of E‖z‖² is 0.51 at init and 0.97 at update 64. |
| Batch composition | c3 | Every one of the first 64 batches has **128 distinct facts in 128 answer sites**, at 2,048 and at 8,192 facts. L_div never repels two occurrences of the same fact. |
| G5 as drafted | c3 | W7 memory at init vs the frozen backbone on 256 corpus rows: max \|Δlogit\| **1.24e-3 at the read positions and 5.3e-4 at other positions** (block 1 attention spreads the read). Not bit-identical. |
| H1/H2 condition feasibility | c4 (test sets; my forward reproduces the d4 Panel A accuracies 0.1592 / 0.0557 / 0.9512 exactly) | Escaped model (test-2): A 0.951, B 0.949, H1 0.934, H2 0.893 → H1/A 0.982, H2/A **0.938**. Partly escaped (test-0, A 0.159, cos 0.077): H1/A 0.776. Values permuted 0.031, disabled 0.022 (inside G2). Same top-1 slot A vs B 0.89. |
| Clustering of outcomes by draw | c1 | If the outcome is a property of the draw (as the P9-I diagnostics suggest), the one-sided 95% lower bound is 0.69 for 8/8 draws and 0.47 for 4/4. The draft's 0.74 / 0.83 hold only for independent cells. P(RELIABLE) for a per-cell success probability of 0.90 is 0.52 (independent) or 0.43 (draw-clustered). |
| A1-S flagged FAILED by the baseline alone | c1 | If A1-S is no better than A0 and A0 escapes on 20 / 30 / 50% of draws, P(A1-S ≥ 4/16) = **0.50 / 0.75 / 0.97**. |
| AdamW carry-over at removal of L_addr | c6 | With the c3 gradient ratios (5.5–285×), the mean step of `wq`/keys after removal is **0.03–0.72× a fresh optimizer's**. At ratio ≥ 55 it stays below 0.5× for the whole remaining run (A2) or past U (A3). |
| Resources | c5 (P9-I attempt-2 records) | s/update with six workers: W7 0.0098 / 0.0138–0.0141 / 0.047–0.053. The slowest P9-I memory or dense arm (A4, which is not this draft's A4): 0.0112 / 0.0195 / 0.0619. Registered-stage makespan 1.6 h (W7 rates) to 2.1 h (slowest rates). Peak RSS in training 0.63 GiB; in the P9-I rehearsal evaluation 1.49 GiB. |

---

## Blockers

### B1. The negative control and the hypothesis readings are absolute, not paired against A0; the most likely positive outcome turns into INCONCLUSIVE, and an A0-reliable outcome has no reading

**Problem.** §8.4 flags NEGATIVE CONTROL FAILED if A1-S is UNRELIABLE (≥ 4/16). §8.6 row 2 then makes the study INCONCLUSIVE unless A4 or A5 is RELIABLE. In the P9-I diagnostics, answer-only W7 escaped at 4,096 on 3 of 5 non-registered draws (9 of 11 runs). A1-S is A0 plus a fact-independent gradient. If it is merely no better than A0, it reaches ≥ 4/16 with probability 0.50–0.97 for A0 draw-escape rates of 20–50% (c1 §4). So "A1 RELIABLE" would most likely be read INCONCLUSIVE, because of A0's own escape rate rather than any shortcut.

The same absolute logic runs through the rest of the readings:

- H19-B ("A1 RELIABLE and A1-S not"), H19-D ("A4 RELIABLE") and H19-F ("A5 RELIABLE") do not require that A0 fail, or that the arm beat A0 on paired cells.
- If A0 is itself RELIABLE, every one of them reads "supported" while showing nothing.
- A0 is missing from the carry-forward order (§8.4, §8.6), so an outcome where A0 is RELIABLE carries no interface.
- §8.6 row 3 ("some learned arm … RELIABLE") would then print ADDRESSING-RELIABLE on the strength of the baseline.

**Replacement text (§8.4, after the class table):**

> **Paired comparisons with A0 (fixed now).** For each learned arm X ≠ A0 at a size and readout, let d(X) = (cells where X succeeds and A0 fails) − (cells where A0 succeeds and X fails), over the paired cells (same draw and init seed). X **IMPROVES ON A0** if d(X) ≥ [4] and X has more successes than A0. X **HARMS** if d(X) ≤ −[4]. Otherwise X is **NOT DISTINGUISHED FROM A0**. The exact two-sided sign-test p-value on the discordant pairs is printed beside d(X) (descriptive).
>
> **NEGATIVE CONTROL FAILED** is printed if A1-S IMPROVES ON A0, or if A1-S is RELIABLE. A1-S being UNRELIABLE while NOT DISTINGUISHED FROM A0 is not a failed control.

**Replacement text (§8.6, new row before row 3, and hypothesis readings):**

> | 3a | ANSWER-ONLY RELIABLE | A0 is RELIABLE at 4,096. The collapse of P9-I's registered draw is not a reliability failure on these draws. H19-A is not supported. Other arms are reported by their paired comparison with A0 (IMPROVES ON / NOT DISTINGUISHED FROM / HARMS) and by median escape update; none is "supported" unless it IMPROVES ON A0 at 16,384. |
>
> Hypothesis readings: H19-B is supported if A1 is RELIABLE, IMPROVES ON A0, and NEGATIVE CONTROL FAILED is not printed. H19-C: A2 [or A3] is RELIABLE and IMPROVES ON A0, and the post-removal rule of M3 holds. H19-D: A4 is RELIABLE and IMPROVES ON A0. H19-F: (per arm of M1) RELIABLE and IMPROVES ON A0. "Not supported" otherwise. **CONTRADICTED** if the arm HARMS.
>
> The interface carried forward is the first RELIABLE arm at 16,384 in the order **A0**, then label-free arms (A5-C, A5-D, A4), then A2, then A1.

### B2. G5 fails by construction, and the LM-capability criterion the human requires is missing

**Problem.** The memory reads at the fixed positions 8r + 6 on every 64-byte input (`SITES` in `studies/p9i/model.py`), and block 1 attention carries the read to later positions. On corpus rows a memory arm's logits therefore differ from the backbone's: c3 measured 1.24e-3 at the read positions and 5.3e-4 elsewhere at initialization. Trained arms will differ by more. G5 as written ("every arm's logits equal the frozen backbone's bit for bit") would therefore fail the gates stage and stop the run, which is the P9-I attempt-1 pattern. If it is instead implemented on the backbone alone, it is vacuous.

"Unchanged by construction" is true of the backbone parameters, not of the system's next-byte predictions. The human asked for a registered criterion of "no unacceptable loss of pretrained LM capability".

**Replacement text (§3 last sentence of the first bullet, and §9 G5):**

> No backbone parameter is trained in any arm. **G5 (backbone identity):** the sha256 of every backbone tensor after training equals the frozen backbone's, and with the addition disabled each arm's logits on the backbone's corpus rows equal the frozen backbone's bit for bit.
>
> **LM capability (measured, registered):** for every learned arm and A7, the next-byte loss on the backbone's 2,048 corpus rows is computed with the addition active, reading at its fixed positions as in training, and compared with the frozen backbone's. **LM CAPABILITY REDUCED** is printed if the loss rises by more than [5]% relative in any cell. An arm with LM CAPABILITY REDUCED in more than [one] cell of a size is not RELIABLE at that size.
>
> §13 adds: "the memory is told where the answer site is (it reads only at positions 8r + 6), a task-structure input like W7's record length."

### B3. Stage 2 runs 4U while the A2, A3 and A4 schedules are defined in U; the two readouts are not both valid

**Problem.** A2's U_pre, A3's "λ to 0 at U/2" and A4's "τ to 0.2 at U/2, top-8 from U/2" are tied to U. Stage 2 trains 4U and reads at U and 4U. The draft does not say whether the schedules scale.

- If they scale by 4, the U readout falls mid-curriculum. For A4 the read at U would still be dense, so "success at U" is undefined for A4, and A3 would still be supervised at U. The snapshot is then not a run of U updates, and ADR-0017 §5.5's "a snapshot is a valid shorter run" no longer holds.
- If they do not scale, the 4U readout matches Stage 1 in exposures per fact but not in supervised exposures per fact (4,096 supervised updates = 64 per fact at 8,192 facts against 256 at 2,048).

Either choice invalidates one readout for the scheduled arms. An implementer would have to make a scientific choice, which `AGENTS.md` forbids.

**Replacement text (§5, "Stage 2 runs 4U" bullet):**

> In Stage 2 every schedule is expressed in **exposures per fact**: A2's U_pre, A3's decay end and A4's annealing end are multiplied by 4, so the 4U readout reproduces Stage 1's protocol in every respect at matched exposure. **The 4U readout decides the Stage 2 class for every arm.** The U readout is a valid matched-update run only for arms with a constant objective (A0, A1, A1-S, A5-C, A5-D, A6, A7); for them it is printed as ALSO AT MATCHED UPDATES. For A2, A3 and A4 the U readout is printed as **MID-SCHEDULE (not a matched-update run)** and enters no rule. A4 is scored at a mid-schedule readout with its standard top-8 read.

---

## Majors

### M1. A5 combines two mechanisms, and its collapse diagnostics are vacuous by construction

**Problem.**

- **Two mechanisms.** A5 joins EMA centring, an architectural change that also applies at inference, with a uniformity penalty L_div. If A5 works, H19-F ("the common mode is the cause") cannot be told apart from "a diversity penalty suffices", which is the human's A5.
- **The cosine statistic says nothing for A5.** Centred, normalized queries have mean pairwise cosine ≈ 0 for any residual (c2(c): −0.002 for rank 1, rank 2 and healthy alike). In the real collapsed state it is +0.0002 to +0.002 while only 3–4 slots are used (c3). For A5, therefore:
  - collapse onset (≥ 0.9) can never fire;
  - every A5 cell would be reported "never collapsed";
  - success condition 3 holds automatically.
- **Global centring removes little of the fact-independent structure.** 56–74% of the centred variance is (template × record position) structure that a global mean cannot remove (c3). L_div can be satisfied by spreading queries along that structure.
- **What the draft gets right.** L_div does not repel same-fact pairs: no batch contains a repeated fact (c3).

**Replacement text (§4 table and definitions):**

> | A5-C | Answer-only + centred queries z′ = z − m (m an EMA of the batch mean of z, decay 0.99, no gradient through m; **m initialized as the mean of z at initialization over the first [16] training batches**; frozen at evaluation) | none | none (m is a buffer) |
> | A5-D | Answer-only + μ·L_div on the batch's normalized queries (no centring) | none | none |
>
> H19-F is read on A5-C only. The human's "query-diversity constraint" is A5-D.

**Replacement text (§8.1 collapse definitions, all arms):**

> Collapse statistics are computed on the **un-centred** normalized query z/‖z‖ for every arm (A5-C also reports its centred version, descriptively), and on slots:
>
> - **Collapse onset:** the first record at which mean query cosine ≥ 0.9 **or** distinct top-1 slots on the probe ≤ [32].
> - **Escape:** the first later record from which, to the end, mean cosine ≤ 0.5 **and** distinct top-1 ≥ [0.25 × probe facts].
> - Four categories: never collapsed and separated; never collapsed, not separated; collapsed and recovered; collapsed and not recovered.
>
> Recorded too: the share of centred query variance explained by (template, record index) groups.

The cells freed by dropping A3 (§B) pay for the split.

### M2. A4's curriculum ends at a read that is not the top-8 read

**Problem.** At τ = 0.2 a dense read over all N puts 95.6–99.6% of its weight outside the top 8, even when the query equals its target key (c2(a)). Annealing τ to 0.2 and then switching to top-8 at U/2 therefore replaces the read wholesale; it is not the end point of a curriculum. Both τ_0 values in the grid (1.0, 5.0) give reads that are almost uniform. A failure of A4 would then say nothing about H19-D.

**Replacement text (§4, A4):**

> A4: answer-only. The read is softmax(a/0.2) over the **top-k(t)** slots, with k(t) = max(8, round(k_0 · (8/k_0)^{t / T_A})), T_A = U/2 (scaled per B3), and k = 8 from T_A on. At t ≥ T_A it is exactly the standard read. Calibration grid: k_0 ∈ {[N], [512]}. Reported: soft mass outside the top 8 and active retrieval work (k(t) value rows per query) per record.

An alternative of equal standing is to anneal τ to [0.05 at 4,096; 0.02 at 16,384] before the switch. If chosen, the switch discontinuity (the change of the read vector at the switch) must be reported. **PENDING LEAD REVIEW.**

### M3. In A2 and A3, "addresses survive removal" can be an AdamW artifact; SUPERVISION-DEPENDENT measures the wrong thing

**Problem.**

- **AdamW carry-over.** While L_addr is on, its gradients on `wq` and the keys are 55× and 285× the answer loss's at λ = 1 (c3). AdamW's second moment (β2 = 0.999) then keeps those groups nearly frozen after removal: the mean step is 0.03–0.21× a fresh optimizer's for ratios 55–285, and 0.24–0.72× even at λ = 0.1 (c6). So "survival" could mean that `wq` and the keys were held still.
- **Wrong measure.** SUPERVISION-DEPENDENT fires on a fall in s(f) recall. A model that legitimately re-maps facts to other slots and keeps working would be flagged, and H19-C would read "not supported", which is a perverse reading. The measure should be function, not label agreement.
- **A3 adds little.** With the ratios above, λ(t)·L_addr dominates `wq` and the keys until the last ~2–20% of the decay. A3 therefore behaves like A1 until about U/2, then like A2 with U_pre ≈ U/2. It is unlikely to differ in class from A1 or A2 (§B).

**Replacement text (§4, A2/A3, and §8.4 annotation):**

> At the update where the address loss becomes zero (A2: U_pre; A3: the decay end), the AdamW first and second moments of **all** parameters are reset to zero and the bias-correction counters restart. A G4 test checks this.
>
> **SUPERVISION-DEPENDENT** (A2, A3): in more than half of the cells, the probe accuracy at the readout is lower by more than [0.10] than its maximum over the [512] updates before removal, **or** the cell's escape status after removal is "collapsed and not recovered".
>
> **ADDRESSES RE-MAPPED** (descriptive): top-8 recall of s(f) falls by more than 0.10 between removal and the readout while the cell succeeds.
>
> Movement of `wq` and the keys after removal, relative to A0's movement over the same updates, is printed.

### M4. The confidence bounds assume independent cells; the draw-sensitivity estimands are not defined; probe accuracy is missing

**Problem.**

- **The bounds.** The P9-I diagnostics found that "within a draw the outcome hardly depends on the init seed; between draws it does". The 16 cells are then about 8 draws. Under that clustering the one-sided 95% lower bounds are 0.69 (8/8) and 0.53 (7/8), not 0.83 / 0.74. Stage 2's 4/4 gives 0.47 (c1).
- **A vacuous clause.** "Every evaluated draw has at least one success" is implied by ≥ 15/16 and by ≥ 7/8 (c1 §3), so it adds nothing.
- **Missing estimands.** The human asked for between- and within-draw variability, failure rate, escape time and the frequency of sustained success. The draft names none of these as an estimator. The probe also records no accuracy, so sustained success cannot be computed.

**Replacement text (§5 "Why 8 × 2", §8.1 and a new §8.7):**

> With outcomes clustered by draw, 8 of 8 draws gives a one-sided 95% lower bound of 0.69 on the per-draw success probability. 15 or 16 of 16 cells give 0.74 or 0.83 only if cells were independent, which the P9-I diagnostics contradict. The study states the per-draw bound. [The draw-robustness clause of RELIABLE is replaced by: no draw has both of its cells failed.]
>
> §8.1 adds **probe accuracy** (ties wrong) at every record.
>
> **§8.7 Draw-sensitivity estimands (descriptive, fixed now), per arm and size:**
> - the 8 × 2 success table;
> - the counts of draws with 2/2, 1/2 and 0/2 successes;
> - the within-draw discordance rate (1/2 draws over 8);
> - an exact permutation test of seed exchangeability within draws (are failures clustered by draw?);
> - failure rate with its per-draw Clopper–Pearson interval;
> - escape update per cell, with never-escaped cells censored at the readout, its median, and the between-draw and within-draw mean squares of log escape update (one-way ANOVA, 2 seeds per draw, uncensored cells only, with the censored count);
> - time to first success: the first record with probe accuracy ≥ 0.90 × A6's readout accuracy;
> - **sustained success:** after the first success, no later record falls below that line by more than [0.05]. Its frequency is printed per arm.
>
> H19-E (draw robustness) is supported for arm X if X is RELIABLE with no draw at 0/2, and not supported otherwise. For A0 the clustering test is the primary H19-E evidence.

### M5. Stages 2 and 3 reuse the draws that selected the arms (control 8)

**Problem.** A draw's 2,048-fact cells train on facts 0–2,047 of the same 32,768-fact table, panels and templates that its 8,192-fact cells use (`studies/p9/data.py` `build_study_data`, `facts_of`, `restrict_stream`). So Stage 2's draws 1–4 contain the Stage 1 facts and templates on which the Stage 1 gate selected the arms. The confirmation at a larger size is then not on an untouched split. Fresh draws cost nothing.

**Replacement text (§5 Draws, §7):**

> Stage 1 uses registered draws 1–8. **Stage 2 uses four further registered draws 9–12, and Stage 3 two further draws 13–14** (seed sets `p9ii-draw-9` … `p9ii-draw-14`, bases 190801 … 191301). No Stage 1 draw enters Stage 2 or 3, and no panel used for the Stage 1 gate enters a later class. All 14 draws are generated, hashed and checked by G1 at freeze time.

### M6. Outcome precedence: stage cuts and NOT_EVALUATED fall through to "AT 4,096 ONLY"; labels hide supervision

**Problem.**

- **Precedence gaps.** If Stage 2 is cut (§10), not started (§14), INCOMPLETE, or NOT_EVALUATED at 16,384, row 4 still prints "ADDRESSING-RELIABLE AT 4,096 ONLY", which reads like a failure to scale. Row 1 ("missing or failed cells") also conflicts with §14 ("completed stages stand").
- **The label hides supervision.** "ADDRESSING-RELIABLE" is reachable through A1 alone, which needs a fact label in training.
- **Denominators.** With one draw NOT_EVALUATED, 15/16 becomes impossible and no denominator rule exists.
- **LEAKAGE is outside the success rule.**

**Replacement text (§8.3 and §8.6):**

> §8.3 adds: 5. the cell has no LEAKAGE flag. Denominators: RELIABLE requires at most one failed cell among the evaluated cells and at least [14] evaluated cells (Stage 2: at most one failed, at least [7] evaluated).
>
> §8.6: Stage 1's outcome is decided from Stage 1 alone and stands whatever happens later. Each later stage gets its own status: COMPLETE, NOT RUN (BUDGET), NOT RUN (NO ARM PASSED), INCOMPLETE or NOT_EVALUATED. Row 4 applies only if Stage 2 is COMPLETE. Otherwise the outcome is "ADDRESSING-RELIABLE AT 4,096; 16,384 <status>".
>
> Every ADDRESSING-RELIABLE label carries its supervision class in the label itself: **(LABEL-FREE)** if the arm is A0, A4, A5-C or A5-D; **(ADDRESS-SUPERVISED IN TRAINING)** if A1 or A2 [A3]. Summaries must not shorten it.

### M7. The budget: 2× headroom, a full-matrix rehearsal and Stages 2 and 3 do not all fit in 4 h; the reduced Stage 2 has no thresholds

**Problem.**

- **The arithmetic (c5).** Recomputed from the P9-I records with six workers, the registered stages take 1.6 h at W7 rates (Stage 1 0.49, Stage 2 0.90, Stage 3 0.24) and 2.1 h at the slowest P9-I rates. That is before probes, the dense reads of A4, L_addr's all-key backward and evaluation. Caps at twice that need 3.3–4.2 h, and calibration (0.11 h) plus a rehearsal come on top. The 4 h total holds only with a short rehearsal (P9-I's was 64 updates per cell, 101 s) and less than about 10% overhead. Otherwise the cut rule bites.
- **The human's wording.** The human set "≤ 4 hours charged for the initial registered phase" and asked for a separately defined budget for the capacity stages. The draft folds everything into one 4 h line.
- **The reduced Stage 2.** The cut rule's "Stage 2 on draws 1–2" leaves 4 cells per arm, for which no class thresholds exist.
- **The Stage 3 time gate.** It depends on how many arms passed Stage 1. That is mechanical and fixed in advance, but it should be stated.

**Replacement text (§10):**

> Rehearsal: every distinct (arm, size, phase) of the matrix for [256] updates plus one full evaluation, on rehearsal set 5, six workers. Projection = measured s/update × planned updates plus measured evaluation. Caps per stage = 2 × projection.
>
> **Budget A (initial registered phase): calibration + rehearsal + Stage 1 ≤ 4 h charged.**
>
> **Budget B (progression): Stage 2 ≤ [x] h and Stage 3 ≤ [y] h**, recorded at the freeze with their projections. If Budget B is not within what the human lead has authorized, Stages 2 and 3 are not run and return to the human lead; they are not shrunk.
>
> [If the lead keeps a single 4 h line, the cut rule must give thresholds for the reduced Stage 2 (2 draws × 2 seeds: RELIABLE = 4/4).]
>
> Stage 3's time condition uses the cap actually left after Stage 2, whose size depends on how many arms passed. This is stated as a mechanical, pre-registered dependency.

**PENDING LEAD REVIEW**, or a question to the human lead, on whether the human's 4 h covers Stages 2 and 3.

### M8. Gates: G1 false-failure risk over 8–14 draws, and the G4 tests the new arms need

**Problem.**

- **G1 false failures.** G1 runs 10 independence streams per draw, each Bonferroni-controlled at 0.001 (P9-I `g1.json`: 10 streams × 8 tests). That bounds false failures at about 1% per draw, so up to about 8% over 8 draws and about 13% over 14. A failed G1 stops the run, which is the P9-I attempt-1 lesson.
- **G4 does not cover the new machinery:** schedules, the moment reset (M3), m, the per-occurrence random targets, and the full-N softmax paths, which the chunked top-64 scorer in `studies/p9` does not provide at 65,536.
- **Gate outputs.** The C4–C8 comparison output of P9-I was not committed; the P9-I review flagged this.

**Replacement text (§9):**

> Registered draws are generated and G1-checked at the freeze, before any model sees them. A draw that fails G1 is replaced by the next reserve seed set (`p9ii-reserve-1`, `-2`, … , bases 191401, 191501, …), in order. The replacement is recorded in the freeze. No other replacement is allowed.
>
> G4 adds:
> - λ(t), k(t) or τ(t) at [0, 1, T/2, T] updates equal the formula;
> - the moment reset at removal;
> - m receives no gradient, is restored from checkpoints and is frozen at evaluation;
> - A1-S's target stream is reproducible from its seed and independent of the fact;
> - L_addr and the dense read use all N scores, checked against a direct computation at 65,536.
>
> All gate outputs are written to the run directory and committed. Each stage is launched by one frozen script that takes no free arguments.

### M9. A1-S is a weak control and is absent at Stage 2

**Problem.**

- **What A1-S actually is.** Its per-occurrence random target gives the same gradient magnitude as A1 (c3), so it does match "extra gradient". Under AdamW, though, that noise inflates the second moment of `wq` and the keys and throttles the answer loss's effect on them (the c6 mechanism). A1-S is therefore likely to be worse than A0, which makes "A1 beats A1-S" nearly automatic. Its expected gradient is also a combination: a uniformity term (logsumexp), a pull of every query toward the key centroid, and noise.
- **Missing at Stage 2.** A1-S is not run at Stage 2, so control 9 goes untested at 16,384 whenever a supervised arm advances.

**Replacement text:**

> §5 Stage 2: if any address-supervised arm advances, A1-S advances with it (4 × 2 cells).
>
> §8.4: A1-S is read only through the paired rule of B1.
>
> [Optional, PENDING LEAD REVIEW: A1-U, the negative term only (L = logsumexp_s(a_s/τ_a), no target), replaces or joins A1-S as the control for the generic key-spreading component of L_addr.]

---

## Minor

1. **Calibration draws (§6).** "Rehearsal seed sets 3 and 4, which nothing has used" is not literally true. Seeds 179301 and 179401 appear in `tests/test_p9_data.py` (fact tables at 2,048 and 100 facts) and in `tests/test_p9_evaluate.py` (as RNG seeds). A scratchpad timing script (`g1time.py`) built rehearsal draw 3 with a random corpus and ran G1. No model has been trained or evaluated on draws 3 or 4 in the repository, `experiments/` or the session scratchpads (searched). Replacement: "on which no model has been trained or evaluated; their generator has been exercised by unit tests and by a G1 timing script."
2. **Test seeds (§7).** 900001 upward is P9-I's test namespace. The P9-I review trained W7 on p9i-test-0/1/2 (900001, 900101, 900201), so §7's own disjointness assertion would fail. Use 910001 upward. Also state the null-seed layout of the p9ii seed sets (P9-I convention base + 14…19, or rehearsal convention + 20…22 / + 30…32).
3. **Seeds 190001+ are free.** No use as a seed in the repository or `experiments/`. The only numeric matches are byte offsets in P6 and P7 worker records. 1891, 1901 and 1902 are unused as seeds.
4. **Probe set (§8.1).** It does not leak, because it takes no gradient and drives no decision. It is cleaner to use each draw's **calibration stream** (training templates, contexts not in training, every fact twice). That keeps Panels A and B untouched until the readout and gives address stability during training. If Panel A is kept, state "no rule or action during training reads the probe".
5. **Fact-independent share.** Define it as ‖mean z‖² / E‖z‖² on the probe, plus the (template × record) share of M1.
6. **L_addr (§4).** It is a supervised InfoNCE with fixed proxies: contrastive in the human's sense, and sound. It gives large, fact-specific gradients where the answer loss gives almost none (c3). Its floor is 4.1–6.8 nats, so it never saturates and acts as a permanent key-spreading term (c2(b)). Its gradient norm of 4–6 exceeds the clip of 1.0, so in A1 the answer-loss gradients are clipped by about ×0.2. AdamW is nearly invariant to that, but report the clip factor per update.
   - Both λ values in the grid make L_addr dominant (5.5–285×). Say so.
   - A label-free query–query contrastive variant would need batches with two contexts of the same fact, and no current batch has one (c3). That changes data access relative to A0 (control 5), so I do not recommend adding it.
7. **G6 wording.** Replace "changing the fact table does not change its output" with "with token inputs fixed, permuting s, the R1 codes and the fact-index tables leaves every learned arm's logits bit-identical".
8. **Calibration tie rule (§6).** With near-binary accuracy (escape or not), ties will be common and default to the first listed value. Either accept and state this, or use a fixed secondary criterion: the earlier median time to first success on the probe. Also state that A0 is untuned by design (the registered P9-I recipe), so arm-versus-A0 contrasts compare tuned arms with an untuned baseline.
9. **Dense comparison (§8.4).** BEATS DENSE is unreachable when A7 > 0.909, which is likely at 4,096 with 512 exposures per fact. Pair it by draw. State that DENSE SUFFICES speaks about this task and budget only.
10. **Stage 3.** At 32 exposures per fact, Stage 3 can produce only a positive or an uninformative result. Either say so in §8.5 and §13 or cut it [lead].
11. **§16 approval record.** Record the human's delegation verbatim and the lead's self-imposed conditions for using it, as ADR-0017 §15.3 did: no open blocker or major from this review or from the implementation audit; nothing changed after calibration but the calibrated values; the rehearsal fits Budget A; no registered seed observed. Add that this review is neither Astra validation nor human approval.
12. **H19-A's mechanism.** Add: "and in at least [12] of 16 cells the ratio ‖∇wq‖ / ‖∇wo‖ averaged over updates 64–1,024 is ≤ [0.01]". Without it, "starving addressing gradients" is not tested.
13. **Extra computation per objective (control 4).** Report analytical FLOPs and measured CPU seconds of L_addr (N-way softmax and the all-key backward), the dense or top-k(t) read of A4, and L_div (128² pairs) per update.
14. **W5 exclusion.** List W5, the identifier-only window, as excluded with a reason: it is told the identifier positions. Centring (A5-C) is the general form of removing the fact-independent window positions.
15. **H1/H2 (condition 4).** It is reachable: an escaped W7 shows H1/A 0.982 and H2/A 0.938 (c4). The margin to 0.90 is small on one of three runs, and A5-C's frozen m is a training-template mean. Keep it [lead], or move it to an annotation TEMPLATE-GENERALIZES. Do not change it after calibration.
16. **§13 additions.** Matched exposure at 16,384 is not matched optimization: under AdamW a row updated once in K steps moves about √K learning rates per exposure (ADR-0017 §5.5). Also add that a supervised arm's success says nothing about learning addresses without labels.
17. **Matrix bookkeeping.** The A1-S random-target seed and the A5-D batch definition (the 128 answer sites of the update) must be stated.

---

## Answers to the review questions

**A. Do the arms isolate the hypotheses?**

- **A1.** Sound; see minor 6. It gives fact-specific gradient where the answer loss gives almost none (c3: 55× on `wq`, 285× on the keys, at collapse). It is contrastive in the human's sense: query–key InfoNCE with fixed proxies. A label-free same-fact variant would need altered batches; not recommended.
- **A1-S.** Valid for "extra gradient magnitude without fact information" (same magnitude, c3). It is weak (M9) and must be read relative to A0 (B1). A cluster-shared or answer-symbol target is not needed: answer-derived targets would test a different shortcut (a W-side answer classifier), which a linear 224→16 query cannot realize for random answers. A1-U is the cleaner optional control.
- **A2.** Stage 2 does not start from a degenerate readout: values, wo and gate are at their initial values, as in A0. But AdamW carry-over pins `wq` and the keys (M3).
- **A3.** Not distinguishable from A1 followed by A2 at these gradient ratios (M3).
- **A4.** Ill-defined endpoint (M2). Cost at 16,384 / 65,536: one 128 × N weight tensor (8 / 33 MB) and 128 × N × 32 multiply-accumulates per update. Memory is fine; time must be rehearsed.
- **A5.** Two mechanisms, with vacuous diagnostics (M1). Centring leaks nothing (m is fact-independent) and behaves at evaluation if frozen. It removes only the global part of a template × position structure. L_div never repels same-fact pairs, because every batch has 128 distinct facts.
- **Simpler fixes.** Nothing is smuggled in. A5-C is the general form; W5 is properly excluded (minor 14). A trainable bias did not prevent the collapse in the P9-I review.

**B. Smallest credible matrix.**

- **Draft recount** (the draft's arithmetic is correct): calibration 26 (20 + 6); Stage 1 128 (7 × 16 + 2 × 8); Stage 2 at most 40 ((1 + 3) × 8 + 2 × 4); Stage 3 8. At most 202 cells.
- **Recommended:**
  - Stage 1: A0, A1, A1-S, A2, A4 (top-k(t)), A5-C, A5-D, A6, A7, which is 7 × 16 + 2 × 8 = **128**. A3 is dropped (M3: not separable from A1 → A2). A5 is split (M1).
  - Stage 2 on new draws 9–12: A0, at most 3 advanced arms, A1-S if a supervised arm advances, A6, A7, giving at most (1 + 3 + 1) × 8 + 2 × 4 = **48**.
  - Stage 3 on draws 13–14: **8** [or cut].
  - Calibration: A1 λ, A2 U_pre, A4 k_0, A5-D μ (A5-C has no free parameter), giving 4 × 2 × 2 = 16, plus 6 pipeline cells = **22**.
- This is [lead's choice]. If the lead keeps A3, it should be 8 × 1, descriptive, with no class.

**C. Calibration.**

- **Calibration draws.** They are untouched by any model (minor 1).
- **Forking paths.** The risk is limited: there are five binary choices, and the registered draws are new, so calibration cannot "rescue" an arm on registered data. It only gives each arm its better setting.
- **Tie rule.** It is effectively a default (minor 8).
- **Scaling.** How the calibrated values scale to Stage 2 is undefined (B3).

**D. Success rule and classes.**

- **Collapsed model.** Fails condition 1, except that A5's condition 3 is vacuous (M1).
- **Memorizing dense-like path.** Not possible for the learned arms: there is no fact-specific capacity outside the memory, and condition 2 covers it.
- **Right for the wrong reason.** Context- or template-keyed addressing fails on new co-record contexts (Panels A and B) and on H1/H2. LEAKAGE is not in the rule (M6).
- **Cosine ≤ 0.5.** Harmless as a conjunct but weak. N had cosine 0.087 and FAILED; test-0 had 0.077 at 0.159 accuracy (c4). It is insufficient as a definition of collapse or escape: N would be "never collapsed" (M1). The initial cosine is already 0.51–0.53 (c3; the P9-I review's d2).
- **15/16 and 7/8.** Strict, which is fine against false positives: P(RELIABLE | per-cell p = 0.9) = 0.43–0.52 (c1). The stated bounds are wrong under draw clustering (M4).
- **Stage 1 gate order.** Sound, except that A0 is missing (B1).
- **H1/H2.** Meaningful and reachable (minor 15).

**E. Stage 2 and Stage 3.**

- **Constant-objective arms.** The readouts are correctly separated.
- **Scheduled arms.** Not separated (B3).
- **Exposure read as scale.** Possible through §8.6 row 4 (M6), and through the per-row AdamW confound (minor 16). Stage 3 is exposure-starved by design (minor 10).

**F. Collapse definitions and the probe.**

- **Well defined** for non-centred arms, except for a missing category (M1).
- **Cheap:** about 2% overhead.
- **No leakage:** no gradient and no decision is taken from the probe.
- **Better source:** the calibration stream (minor 4).

**G. Gates.**

- **G5:** wrong as written (B2).
- **G1:** replacement rule needed (M8).
- **Attempt-1 lessons:** the draft keeps gates at real size on rehearsal seeds and harness coverage. It is missing committed gate outputs and fixed launch scripts, and G4 lacks tests for the new machinery (M8).

**H. Outcome table.**

- **Gaps:** the A0 path is missing (B1); stage status is missing, and the supervision qualifier and LEAKAGE are absent (M6).
- **Perverse path:** A1-S can turn the study INCONCLUSIVE (B1).
- **Negative results:** kept. ADDRESSING-UNRELIABLE and ADDRESSING-FAILS stand as registered.

**I. Resources.**

- **Figures:** recomputed in c5. Memory is comfortable: 0.63 GiB measured in training and 1.49 GiB in evaluation, against 3 GiB per worker and 24 GiB in aggregate.
- **Time:** tight under a single 4 h line with 2× caps (M7).
- **The cut rule:** non-adaptive and fixed before observation, which is acceptable, but its reduced Stage 2 lacks thresholds (M7).

**J. Other.**

- **Human's diagnostics list:** sustained success and probe accuracy are missing (M4), as are the extra cost per objective (minor 13) and slot-based collapse (M1).
- **Seeds:** see minor 1–3.
- **Governance:** see minor 11.
- **What the study cannot establish** (add to §13): label-free addressing from a supervised arm's success; a known answer position in real text; more than the per-draw bounds of M4.

---

## My own errors and failed attempts (kept)

1. My first repository search for rehearsal-set seeds (`git grep … | head -40`) was truncated by JSON matches and hid the unit-test uses of 179301 and 179401. A narrower search found them (minor 1).
2. `c3_collapsed_state.py`, first run: failed at the G5 step because I called the backbone module directly (`bbm(rows)`; `Backbone` has no `forward`). Outputs are kept as `outputs/c3_attempt1_FAILED.json` (empty) and `outputs/c3_attempt1_FAILED.stderr`. Its probe lines were identical to those of the second run. Fixed to `controls.logits_from_hidden(bbm, controls.insertion_hidden(bbm, rows))`; the code comment records the fix.
3. `c6_adam_carryover.py`, first run: I measured "updates until the step reaches 0.5× fresh" on single updates. The residual first moment of the old random-sign gradients makes single steps large right after removal, so it reported 0. Kept as `outputs/c6_attempt1_FLAWED_first_crossing_metric.txt`. The script now uses a 256-update moving average. The mean-step ratios were the same in both runs.
4. c3 and c4 ran with 2 threads and without deterministic algorithms. They are diagnostics only.

## Commands (from the worktree root; R = this folder; S = the session scratchpad)

```sh
uv run --locked python R/c1_bounds.py > R/outputs/c1_bounds.txt
uv run --locked python R/c2_softmax_mass.py > R/outputs/c2_softmax_mass.txt
PYTHONPATH=. uv run --locked python R/c3_collapsed_state.py > R/outputs/c3_collapsed_state.json 2> R/outputs/c3_collapsed_state.stderr   # DIAGNOSTIC, rehearsal draw 0, seed 600001
PYTHONPATH=. uv run --locked python R/c4_heldout_templates.py S > R/outputs/c4_heldout_templates.json 2> R/outputs/c4_heldout_templates.stderr   # DIAGNOSTIC, p9i-test-0/1/2 parameters from the P9-I review's d4
uv run --locked python R/c5_resources.py /Users/daniellaloush/dandush03/ArborLM/experiments/P9IP-20261115T020303574595Z-674730f6b8a147c0a47cac404321f2df /Users/daniellaloush/dandush03/ArborLM/experiments/P9I-ledger.json > R/outputs/c5_resources.txt
uv run --locked python R/c6_adam_carryover.py > R/outputs/c6_adam_carryover.txt
uv run --locked ruff check --config docs/reviews/ruff.toml --extend-ignore E501,I001,E401,E702,F841,E701,E402,F401 R/*.py
```

Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.
