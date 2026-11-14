# ADR-0018 design revision 2: narrow confirmation check (2026-11-14)

- **Checker:** Claude Opus 5.5 (`claude-opus-5-5`), auditor role, launched by the Claude lead (Fable 5.2). I wrote the revision-1 review (`REVIEW.md`, same folder). I did not write ADR-0018.
- **Status:** independent engineering and mathematical evidence only. **Not Astra validation and not human approval. Astra review: NOT_PERFORMED.** Scientific choices are marked `PENDING LEAD REVIEW`.
- **Reviewed:** `docs/decisions/ADR-0018-query-interface-prerequisite.md` at commit `649f76f` in full; `git diff 80155d6 649f76f` of the ADR and of `docs/RESEARCH_LOG.md`; `REVIEW.md`. For facts only: `src/arborlm/model.py` (`Block`), `studies/p9/model.py` (`DenseAdapter`, `P9Model`), `studies/p9/train.py` (header), `studies/p9/core.py` (seeds), ADR-0017 §4, §6.1 and §8.1 (G2).
- **What I ran:** `g1_confirm_checks.py` (pure arithmetic: no backbone, no study data, no training). Output: `outputs/g1_confirm_checks.log`. I also ran `uv run --locked ruff check .`, which passes.
- **Not run:** no backbone probe, no training, nothing on rehearsal draw 1 or on registered seeds. No existing file was edited. Nothing was committed.
- **Environment:** Apple M5 Max, macOS (Darwin 27.2.0), CPU. Python 3.12.14 via `uv run --locked`; no package added.

## Verdict: NOT READY AS COMMITTED. READY FOR HUMAN DECISION 1 once the four required text edits (R1–R4) are pasted.

- There are **no blockers**. B1, B2 and M1–M6 are applied faithfully, and so are all 14 minors.
- **R1–R4** are required text edits. Each changes a label, a residual bin or a missing cell. None changes the core design, and none needs a probe. If they are pasted as written, a diff check by the lead is enough; I do not need to review again.
- The minors (n1–n8) are recommended and do not block.

## 1. Revision-1 findings: applied or diverging

| Finding | Judgement |
|---|---|
| B1 | **Applied.** It has the §2 scope paragraph, H18-MODEL, §3.2 BB, the §8.3 carry sentence and §14.2. Gap: §13 has no BB non-claim (see R4). |
| B2 | **Applied, and broader than mine.** Calibration is on R2 ≥ 0.95 **and** R1 ≥ 0.90, with up to 16,384 updates. In step 0, any failed size gives INCONCLUSIVE. That is the correct generalization: steps 1–3 need all three sizes, so any failed size makes selection impossible. My "65,536" wording was too narrow. |
| M1 | **Diverging, acceptable.** A1 is withdrawn, which was one of the two options I offered. A4 uses the **full causal prefix**, which nobody has probed (I probed 16 positions). The ADR states that honestly in §3.1, and H18-ATT records the prediction that it fails over states. The full prefix strengthens the "no window" reading. A4 can still learn the record structure from position embeddings, which §3.1 should not deny (it doesn't). A4E at 16,384 × 2 seeds is as asked. A4's normalization and scaling are unspecified (n7). |
| M2 | **Applied, with the lead's choice of an accuracy ratio.** It has one ratio, exclusive labels, answer-site-only dense outputs, and a fixed reading. On saturation, see §2 below and n1. |
| M3 | **Applied, but the residual bin is wrong** (R2). |
| M4 | **Applied as I wrote it, and my table was wrong** (R1, own error). Also, 30 of 81 raw-class patterns get a different label depending on how "different results for Panels A and B" is read. |
| M5 | **Applied.** It has §11 "tested, not audited" and the reworded G4. |
| M6 | **Applied** in §4 and §13. Exposures recomputed: at U = 4,096 they are 256 / 64 / 16 per fact; at U = 16,384, 1,024 / 256 / 64. |
| m1–m14 | **All applied.** m2: rehearsal draws k ≤ 9 reach 179,999 at most. Registered data seeds 182001+ are clear of 179001–179999 and of 180101–181900. Calibration init seeds 1791/1792 are clear of P9's 1701/1702 and the registered 1801/1802. m12: recomputed. |
| J(i) | **Not adopted, acceptable.** It keeps draw 1 limited to R1/R2. Its cost: A4 full-prefix is first observed in the registered run. |
| J(ii) | **Adopted under option b.** The matrix is {W7, BB} × {memory, dense}. |

**Recomputed numbers.**

- BB attention = qkv (32×96 + 96) + attn_out (32×32 + 32) = **4,224**. This matches `Block` in `src/arborlm/model.py`; `attn_norm` stays frozen.
- W7 extra = A4 extra = **3,072**.
- D7 hidden = (48·S + 4,608)/256 = **786 / 3,090 / 12,306**, all exact.
- Matrix:
  - Core: 16,384 → 9 × 2 + 4 = 22; 65,536 → 5 × 2 = 10; 4,096 → 4 × 2 = 8; **core total 40**.
  - BB block: 3 × 2 sizes × 2 seeds + 1 = 13, plus 2 = **15**.
  - **Total 55.**

## 2. Item checks

**Accuracy ratio in the dense comparison (question 1).**

- BEATS DENSE needs accuracy(dense) ≤ 1/1.10 = **0.9091**. Above that, the label is always DENSE SUFFICES.
- **I find this acceptable, not perverse,** provided the reading says so. Under a fixed 10% relative-accuracy margin, "a dense adapter does as well" is a fair description of arm 1.00 against dense 0.92 (r = 1.087).
- It hides error-rate differences at the top (0% against 8%). That is a property of the chosen metric, and the reading should state it (n1).
- Similarly, BACKBONE HURTS is unreachable once the state arm's accuracy is above 1/1.03 = **0.9709**. That is consistent with ADDS NOTHING.

**Three-way backbone contrast.** The thresholds are fine. The residual bin is wrong (R2).

**Calibration.** It is coherent. Training uses a constant learning rate (`studies/p9/train.py` header, ADR-0017 §5.5), so reading U from the snapshots of one 16,384-update run equals running to U.

**Step 0.** It is correct (see above). Consequence: if calibration marks any size as failed, the outcome is INCONCLUSIVE before any registered cell runs (n4).

**BB block (question 2).**

- **BB-0 is missing at 4,096 (R3a).** The "where BB-0 is run" clause leaves BB's 4,096 class without its only check against the trained attention storing facts. 2,048 facts is the size where that is most plausible, and selection step 1 needs WORKS at 4,096.
- **The MODEL_STORES_FACTS reading contradicts the WORKS row (R3b).** WORKS already requires that value permutation and disabling give chance. Any BB that reaches that row therefore depends on its memory. "The trained attention, not the memory, holds the answers" cannot then be the reading.
- **The ordering against the B102 rule is unspecified (R3c).**
- **"Same optimizer and learning rate as the memory parameters" is ambiguous (R3d).** P9 uses AdamW at 0.003 for the projections and gate, and row-lazy Adam at 0.012 for the key and value tables.
- **U is not calibrated for BB (R3e).** Nothing BB-like runs before the freeze, so a BB class below WORKS is a within-U statement on a budget calibrated with a frozen backbone.
- G4 at initialization (BB = N) is right. The analogous identities (BB-D = D plain, BB-0 = no-memory baseline) are not stated (n8).
- A trained BB-0 learning the answer prior cannot by itself leave the G2 interval. Answers are independent and uniform, and a constant modal predictor exceeds the interval's upper end with probability ≤ 0.0018 / 0.0020 / 0.0019 (union bound) at 2,048 / 8,192 / 32,768 facts. The upper ends are 96/2,048 = 0.0469, 318/8,192 = 0.0388 and 1,147/32,768 = 0.0350. So "above G2" for BB-0 does indicate fact-specific content.

**§8.1 two-step procedure (question 3).** I enumerated the cases: 3⁴ = 81 raw-class patterns over (Panel A, B) × (seed 1801, 1802), plus the all-NOT_EVALUATED case.

| Reading of "rows 2–4 applied to each panel separately give different results" | WORKS | PARTIAL | FAILS | INTERMEDIATE | NOT REPLICATED |
|---|---|---|---|---|---|
| per seed (panel A ≠ panel B for some seed) | 1 | 1 | 1 | 6 | 72 |
| per-panel class (common class or MIXED) | 1 | 1 | 1 | 36 | 42 |
| per-panel set of raw classes | 1 | 1 | 1 | 12 | 66 |

- **The label depends on the reading in 30 of 81 patterns.** Example: A (WORKS, PARTIAL) and B (PARTIAL, WORKS) is NOT REPLICATED per seed, but INTERMEDIATE under the other two readings.
- **None of the 30 can make an arm WORKS,** so selection is unaffected. The printed label is not, and an implementer would have to choose.
- **No row is unreachable.**
- **Precedence error (my M4 table, kept by the lead).** NOT REPLICATED sits above NOT_EVALUATED and is computed from rows 2–4 only. At a size where R1 < 0.5, an arm can therefore print NOT REPLICATED, from η values that have no meaning there, instead of NOT_EVALUATED. Step 0 refers to the size being NOT_EVALUATED, so selection is still safe if read at the size level. The printed class is wrong, and the wording of step 0 invites the arm-level reading.

**New problems (question 5).**

- **BB WORKS can be over-read as answering the human's question (R4).** §13 has no BB line.
- **Mixed backbone-contrast outcomes default to CONTRIBUTES (R2).** That escapes the §2 scope statement.
- **Step 4's wording is a negative over-read (n3).** NOT REPLICATED or INTERMEDIATE at one size prints "no tested interface works".
- **A4 has no dense comparator**, but §8.3 says the selected interface carries "its dense-comparison annotation" (n2).

**Governance (question 6).**

- The status line has `SPEC: PENDING ASTRA REVIEW`, says NOT APPROVED and says nothing is authorized. "Astra review: NOT_PERFORMED" is present. ADR-0012 is stated as not approved. The research log entry says "Not approved; nothing implemented or run". All of this is correct.
- §14.2 states (a) and (b) as a choice and marks the recommendation as the lead's. **It does not pre-empt the human.** However, the costs of (b) are spread over §3.2 and §10 and are not next to the recommendation (n6).

## 3. Required edits (paste-ready)

**R1 — §8.1 step 2: fix the precedence (my own M4 error) and define panel disagreement.** Replace the step-2 table with:

> | Order | Class | Rule |
> |---|---|---|
> | 1 | NOT_EVALUATED | raw class NOT_EVALUATED (R1 below 0.5 at that size) |
> | 2 | NOT REPLICATED | for at least one B101 seed, the raw classes on Panels A and B differ |
> | 3 | INTERMEDIATE | not row 2, and the two B101 seeds give different raw classes |
> | 4 | INTERFACE_WORKS / INTERFACE_PARTIAL / INTERFACE_FAILS | the common raw class of all four seed–panel pairs |
>
> Step 0 of §8.3 refers to the size: a size is NOT_EVALUATED when R1 is below 0.5 there, whatever an arm prints.

(The per-seed reading is the one I recommend; the lead may choose another reading, but must fix one.)

**R2 — §8.2 backbone contrast: no default to the favourable label.** Replace the bullet's rule with:

> With r = accuracy(embedding arm) / accuracy(state arm), paired by seed and panel (four values): **BACKBONE HURTS ADDRESSING** if all four r ≥ 1.03; else **BACKBONE ADDS NOTHING** if all four r ≥ 0.97; else **BACKBONE CONTRIBUTES** if all four r < 0.97; else **BACKBONE CONTRAST MIXED**. Not printed if both arms are INTERFACE_FAILS.

In §2 Scope, replace "If BACKBONE ADDS NOTHING or BACKBONE HURTS ADDRESSING holds" with "Unless BACKBONE CONTRIBUTES holds".

**R3 — BB block consistency.**

- (a) §7: change the 4,096 BB row to "BB, BB-0 | 4" and the totals to "**Total with block BB: 57**" (BB block 17). In §14.2, change "15 cells" to "17 cells". In §8.1, delete "where BB-0 is run". *Alternative (the lead's choice, `PENDING LEAD REVIEW`):* keep 55, and add "At 4,096 BB-0 is not run; BB's class there is reported as INTERFACE_WORKS (BB-0 NOT RUN), which counts as INTERFACE_WORKS for §8.3 step 1."
- (b), (c) §8.1 last paragraph, replaced by: "For BB, after the B102 rule: a class INTERFACE_WORKS becomes **MODEL_STORES_FACTS** if BB-0's accuracy is above the G2 interval at that size on either B101 seed or panel. Reading fixed now: the trainable attention can by itself retrieve facts at that size, so BB's result cannot be attributed to the memory interface alone, even though BB's own ablations show that it uses its memory."
- (d) §3.2 BB: replace "Same optimizer and learning rate as the memory parameters" with "AdamW, lr 0.003, in the same group as the output projection and gate (ADR-0017 §5.1; the key and value tables keep row-lazy Adam at 0.012); the same gradient clip covers it."
- (e) §6, last bullet, append: "No BB arm is calibrated. A BB class below INTERFACE_WORKS is a statement within a U calibrated on the frozen backbone's oracle rungs."

**R4 — §13 and §8.3: BB must not be read as the answer to the human's question.**

- Add to §13: "That INTERFACE_WORKS for BB shows that a language model reliably communicates what it needs. BB retrains the block-0 attention on this task's answer loss alone, with its next-byte loss unprotected; it shows that a jointly trained backbone attention can form a query for this synthetic task within U updates."
- Append to the §8.3 carry sentence: "If BB is selected, the before/after next-byte loss of BB, BB-D and BB-0 is carried with it."
- *`PENDING LEAD REVIEW`:* whether a next-byte-loss degradation threshold should block BB's selection. As written, BB is selected even if language modelling collapses.

## 4. Minors (recommended; not blocking)

- **n1 §8.2 dense.** Add: "r is paired by seed and panel. BEATS DENSE is unreachable when the dense accuracy exceeds 1/1.10 ≈ 0.909; DENSE SUFFICES then means within 10% relative accuracy." Replace "such a difference between sizes is a per-fact exposure effect" with "such a difference between sizes would be consistent with the sixteenfold difference in exposures per fact and is not evidence about capacity or the interface."
- **n2 §8.2.** Add: "A4 and A4E have no dense comparator (no dense arm reads the full prefix); their dense comparison is NOT COMPARED, and that is carried if A4 is selected."
- **n3 §8.3 step 4.** Replace with "Else → no tested interface reached INTERFACE_WORKS at all three sizes within U updates; the class of each arm at each size is reported; ADR-0017 stays blocked on this backbone."
- **n4 §6.** Add: "If calibration marks any size failed, the outcome is INCONCLUSIVE by §8.3 step 0 before the run; the human lead decides at decision 2 whether the remaining sizes are run."
- **n5 §10.** "2–3 hours serial" holds for U ≤ 8,192. With the assumed costs (0.05 / 0.02 / 0.015 s per update at 65,536 / 16,384 / 4,096; only the first is the measured-based estimate), the core is 2.4 h serial at U = 8,192 and **4.8 h serial at U = 16,384**, or 0.4 / 0.8 h with six workers. "Calibration under 45 minutes" holds only in parallel: 18 runs × 16,384 updates take about **93 min serial** and 16 min with six workers, at the assumed 0.03 / 0.015 / 0.012 s per update. State "with six workers".
- **n6 §14.2.** After the recommendation, add: "Costs of (b): it leaves the P4–P8 frozen-backbone lineage; +17 cells (or 15) whose time is not estimated (cap +2 h); BB is first in the selection rule, so a revision of ADR-0017 would then train a backbone parameter; U is not calibrated for BB. Option (a) is cheaper and keeps the lineage, but leaves the question as asked open."
- **n7 §3.1 A4** (`PENDING LEAD REVIEW`). Fix the layer form, for example "as the backbone's attention: causal, scores scaled by 1/√8, no layer norm, no output projection." Otherwise the implementer chooses.
- **n8 §9 G4.** Add: "At initialization BB-D's forward equals D plain's and BB-0's equals the no-memory baseline's."

## 5. My own errors (kept)

- **M4 table.** In `REVIEW.md` I put NOT REPLICATED above NOT_EVALUATED. That lets a size whose oracle rung failed print a panel-disagreement label computed from meaningless η values. The lead copied it. R1 corrects it.
- **B1 cell count.** I wrote "[10–12] cells" for BB at two sizes × two seeds with an optional B102 replicate. Three arms × 2 × 2 = 12, plus 1 = 13. The lead's 13 (+2 at 4,096 = 15) is right.
- **Timing assumptions.** The per-update costs in `g1` for 16,384 and 4,096 slots, and for calibration R1, are my assumptions, not measurements. Only 0.012 s/update (R2 at 65,536) is measured in P9.

## Commands (worktree root)

```sh
git diff 80155d6 649f76f -- docs/decisions/ADR-0018-query-interface-prerequisite.md docs/RESEARCH_LOG.md
uv run --locked python docs/reviews/adr-0018-design-2026-11-14/g1_confirm_checks.py | tee docs/reviews/adr-0018-design-2026-11-14/outputs/g1_confirm_checks.log
uv run --locked ruff check .
```
