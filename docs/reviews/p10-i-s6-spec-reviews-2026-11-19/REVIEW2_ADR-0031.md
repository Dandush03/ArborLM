# Confirmation review of ADR-0031, second draft

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I am the reviewer of the first draft (`REVIEW_ADR-0031.md`). I wrote none of the ADR.
- Object: `docs/decisions/ADR-0031-p10-i-s6-flat-lead-persistence.md`, 518 lines, SHA-256 `2802816b1f571aa962af57f5970cdb7b7244c8afcfec7f9e347a8aacc4f12b60`.
- How the review was done: read-only reading, plus arithmetic on the ADR's own figures. No code was run in this review. No network, git write, sealed value or registered checkpoint was used.
- This is engineering review evidence. It is not Astra validation and not an approval. `Astra review: NOT_PERFORMED`.

## Verdict

**READY AFTER THE LISTED EDITS.** The edits are R1–R14 in section C; each is a text edit.
- Every required finding of the first review is FIXED or FIXED with small residues.
- The new material raises five problems:
  - **R-KNN seed collision.** The R-KNN seeds collide with this study's own P_used seeds.
  - **Continuation trigger reads the class.** The continuation trigger reads the rung-4 class, although the text says it does not.
  - **Continuation is open to an outcome-informed stop.** Unless the rung-4 values stay hidden and the cap is fixed in advance, the continuation can be stopped after its outcome is seen.
  - **§17 contradiction.** §17 still says the ladder is never extended.
  - **Trend tag identity.** One trend tag is the same as R16 and is not said to be.

## A. Required findings of the first review

| Finding | Status | Note |
|---|---|---|
| F1 convergence | FIXED | §4 δrun row; §9.1; §20 item 13 |
| F2 sealing | FIXED | §8 |
| F3 licensing cause | FIXED | §19 |
| F4 likely outcome | FIXED | Status block, §18. Status line 5 says the study "answers 'does the lead persist'"; it only describes (R10) |
| F7 compute | FIXED | §3, §5 |
| F11 failed cell and R | FIXED | §12.2. NEW PROBLEM in the continuation case: a non-finite event after U_4 would retroactively fail rungs 0–4 (R9) |
| F12 cost figures | FIXED | One stale column label remains: "up to 4 more rates per arm" (R11) |
| F13 k_max | PARTLY | The mapping covers "rung 4" but not the ranges "−1..4", "0..4" and "k ≤ j ≤ 4" in §4, §8, §9.1, §9.2 and §12.2 (R3) |
| F14 imports, frozen inputs | FIXED | |
| F15 registered panel / DRY | FIXED | |
| F17 pool order | FIXED | Typo: "may stream, The order" (R12) |
| F18 calibration pool fallback | FIXED | |
| F19 pause mechanism | PARTLY: real conflict, resolved by R1 | My C8 sentence applied rulings "1–3 and 5–18", which includes ruling 6 (restart from update 0), against the resume-on-pass rule beside it. The drafter is right; this was my drafting error |
| F24 Decision 2 | FIXED | |
| C15 rulings | FIXED; record corrected by R2 | My findings cited G7–G10, G20, G25, G26. My own table numbers them G6–G7, G18 and G19. My error. The §16a table is the reference |

F9 (the 0.0005 rate tie tolerance) is left to the human lead at open choice 6. That is acceptable. F27 is partly applied; the registry revision itself is mine to do in a separate task.

## B. New material

### a. §12.6, the trend line

**The tag list is total and exclusive.**
- Row 1 takes the failure states.
- Without HELD(0), row 2 applies.
- With HELD(0): either some rung is not HELD, and then row 3 (none HELD after the first miss) or row 4 (some later rung HELD again) applies; or every rung is HELD, and then rows 5–7 split the cases by Δ (≤ −0.005, ≥ +0.005, in between), which is exhaustive.

**Reading it as PERSISTS is prevented as far as text can prevent it.** The fixed closing sentence and the δ-against-lead sentence do this. The residual risk is the bare words "LEAD HELD AT EVERY RUNG". R5 makes Δ and the per-rung means part of the tag.

**The ±0.005 band is about the right size.**
- Across-parent SD of Q in P10-I-S3 was 0.0069, so the SE of a parent-clustered 27-cell mean is about 0.0023.
- A band of ±0.005 is about two of those.
- A fall from 0.0127 to 0.0078 (Δ = −0.0049) is not resolvable from noise, so calling it HELD is defensible, as long as Δ is printed.
- A narrower band would tag noise. A wider one would hide real shrinking.

**HELD omits the Q† clause.** This is mildly favourable to the memory, but consistent: equal updates at each rung. It is acceptable because the trend line is descriptive.

**Rung 0 is not identified as R16 (NEW PROBLEM).**
- Rung 0 is the first ladder rung on the 27 registered cells: new parents, new corpus.
- HELD(0) is exactly R16's K3 on the same cells, so tag 2 is exactly "R16 not REPLICATED".
- The ADR does not say so, and the name "AT 16,384" can be confused with P10-I-S3's 16,384 (R4).

### b. §9.5, the continuation rung (choice 2(c))

**It reads more than it says (NEW PROBLEM).**
- Condition 1 ("line P is one of rows 10–12") separates row 8 from row 11, and row 9 from row 10, by the rung-4 class, which is Q.
- So, contrary to "no condition reads Q, a class or a trend tag", the trigger fires exactly when the arm that is still improving is not ahead. That gives the trailing improving arm a second chance.
- It is structurally symmetric, but it is outcome-dependent.
- Fix: trigger on "K\* does not exist" only (R6).

**It is open to an outcome-informed stop (NEW PROBLEM).**
- If the rung-4 analysis is computed, or the rung-5 cost needs a new cap decision, then someone can stop the run after seeing the interim label.
- Fix: nothing of rung 4 except the trigger quantities is computed until rung 5 is done or declined, and rung 5 is in the frozen plan and in the cap from the start (R6).

**The uncalibrated rate removes §9.1's protection at rung 5.**
- At rung 5, δ(5) = δrun(5). So §9.1's second reason (a plateau caused by a rate too high for the longer run) is not guarded.
- A dense arm plateauing at a stale rate while behind would read as converged. That is the memory-favourable direction of P10-I-S3.
- It must at least be disclosed (R6).

**Reading δ to decide more training is acceptable only in the fixed form of R6.** Condition 2 is symmetric between arms.

**§17 contradicts it (NEW PROBLEM).** §17 says U_max is "never extended… whatever the outcome" and that an outcome is "not a reason to add rungs" (R7).

**My view: I would not recommend (c).** On P10-I-S3's trend it probably does not fire. When it does fire, its convergence read is the weakest in the study. It adds the most complex rule in the ADR. If the human lead takes it anyway, apply R6 and R7.

### c. Open choice 14, R-KNN

**Seed collision (NEW PROBLEM).**
- R-KNN seeds 320301 + c collide with registered P_used seeds 320201 + 4c + j, which run to 320308.
- c = 25 and 26 of P_used occupy 320301–320308, the same values as R-KNN's c = 0..7.
- Fix: use 320401 + c (R8).

**Not implementable the same way twice as written.**
- The NLL arithmetic of a probability mixture is undefined; §4's path is for logits.
- The store is drawn only from updates below 16,384 while the arms train to U_max. At later rungs that compares the memory with a store that saw a sixteenth of its data.
- Fix: a store per rung from updates below U_k, at the same cost class (R8).

**It is a byte-matched store, not a retrieval baseline.** The 1.1 GB data-matched store is the real retrieval comparison. The printed sentence must say both directions (R8).

**As a descriptive readout it is acceptable.** It costs minutes, but it adds implementation and audit work to a long study. I would leave it to the human lead without a recommendation either way.

### d. Choice 15, the pool estimate and the ladder options

- **Choice 15:** I agree with "no ordering-without-convergence rule". Any such rule would be chosen knowing P10-I-S3.
- **Pool estimate:** 7.5–7.7 M, 2.5 M calibration and 5.0 M registered. This is my estimate, quoted correctly.
- **Ladder options:**
  - (b): its infeasibility arithmetic is correct. 8,388,608 chunks per stream; at 32×, the 4,194,304-chunk calibration need is not met by 2.5 M or 3.8 M.
  - (c): the rung-5 cost of 6.3 projected and about 8.5 charged hours is correct (27 × 2 × 262,144 × 0.0193 s / 6).

## C. Edits (old → new)

**R1** (§16, the C8 paragraph). Replace "ADR-0026 section 16 rulings 1–3 and 5–18 apply with M-TREE, REP and REP-U removed; ruling 4 is replaced by section 6.4." with:

> "ADR-0026 section 16 rulings 1–3, 5, 7, 9, 10 and 12–18 apply with M-TREE, REP and REP-U removed; ruling 4 is replaced by section 6.4; ruling 6 (a training item restarts from update 0) applies only if the resume-identity gate fails, and otherwise a paused or killed training item resumes from its last snapshot at 8,192 or at a rung; rulings 8 and 11 have no object in this study."

Also delete the whole parenthesis "(Drafter's note on the sentence above, … The reviewer is asked to confirm.)".

**R2** (§22, row C15). Replace the disposition with:

> "APPLIED: inserted as written. The review's findings text cited ruling numbers that do not match its own table (the reviewer's error, confirmed in `REVIEW2_ADR-0031.md`): F17's "G7–G10" are G6–G7, F19's "G20" is G18, F24's "G25, G26" are G19. Section 16a is the reference."

In the F19 row, replace "APPLIED WITH NOTE (C8): … says so" with "APPLIED (C8), with ruling 6 limited to a failed resume-identity gate (confirmation review R1)".

**R3** (§4, k_max row). After "read k_max.", add:

> "Every range or bound that ends at 4 (−1..4, 0..4, k ≤ j ≤ 4) ends at k_max."

**R4** (§12.6).
- Rename tag 2 to "LEAD ABSENT AT RUNG 0 (16,384 UPDATES, NEW PARENTS AND DATA)".
- After the definition of HELD(k), add:
  > "Rung 0 is the first rung of this study's ladder on its 27 registered cells; HELD(0) is the same condition as R16's K3 on the same cells, so tag 2 occurs exactly when R16 is not REPLICATED AT 16,384."

**R5** (§12.6, after "is never quoted without its sentence."). Add:

> "Tags of rows 3–7 are printed with Δ and with mean Q(k) at every rung in the same line, for example "LEAD HELD AT EVERY RUNG (Δ = −0.0049; 0.0127, …, 0.0078)"."

**R6** (§9.5).
- Replace item 1 with:
  > "1. K\* does not exist with k_max = 4 (at least one arm is not converged at rung 4). This reads convergence states only."
- Add after item 3:
  > "Before the continuation decision the analysis computes only δ, δrun and the convergence states; no class, Q, label or trend tag of rung 4 is computed, written or shown until rung 5 has run or the trigger has failed. The rung-5 runs are items of the frozen plan, conditional on the trigger, and the registered cap includes their projection from the start, so no cap or run decision is taken after the trigger. A non-finite event after U_4 fails that cell for rung 5 only; the rung-5 label then follows rows 1–2 of section 12.3, and the rung-4 label is printed as INTERIM. At rung 5 the envelope and the run coincide (r(arm, 5) = r(arm, 4)), so section 9.1's protection against a rate that is too high for the longer duration does not apply there: a plateau at the rung-4 rate can register as convergence for either arm, and every rung-5 label says so."
- Replace "**no condition reads Q, a class or a trend tag:**" with "**no condition reads Q, a class or a trend tag (item 1 reads convergence states only):**".

**R7** (§17).
- In the U_max row, replace "Fixed; cut only by the corpus rule of section 6.5 before calibration. Never extended in this study, whatever the outcome." with:
  > "Fixed; cut only by the corpus rule of section 6.5 before calibration. Extended only by the single continuation rung of section 9.5, by its code rule, if open choice 2(c) is taken; never otherwise."
- In the last paragraph, replace "it is not a reason to add rungs, seeds, rates, parents or cells." with "it is not a reason to add rungs (beyond section 9.5's rule, if taken), seeds, rates, parents or cells."

**R8** (§14 and §20 item 14, R-KNN).
- In §14, replace "320301 + c registered" with "320401 + c registered (320301–320308 are P_used seeds of cells 25 and 26)".
- In item 14, replace "The positions are the first 6,144 entries of `randperm(16,384 × 512)` from a generator seeded 320301 + c, entry n meaning position n mod 512 (row-major in the 8 × 64 batch) of update n // 512 of the cell's own registered stream." with:
  > "At each rung k the store is built from the first 6,144 entries of `randperm(U_k × 512)` from a generator seeded 320401 + c, entry n meaning position n mod 512 (row-major in the 8 × 64 batch) of update n // 512 of the cell's own registered stream, so that the store and the arms have seen the same stream up to the same update."
- Replace "NLL from p on the path of section 4." with:
  > "p is computed in float32 from BASE's float32 softmax; a position's loss is −log p[target] in float32; losses are summed per evaluation batch in float32, accumulated as a Python float and divided by 32,768."
- Replace the sentence "A memory ahead of a 6,144-context store must not be reported as "ahead of retrieval"." with:
  > "The printed sentence beside every R-KNN figure is: "R-KNN is a non-learned store of 6,144 training contexts at the memory's byte count; it is not retrieval as normally used, whose store grows with the data (about 1.1 GB here). A memory ahead of R-KNN is not ahead of retrieval; a memory behind R-KNN is behind a byte-matched store of raw contexts.""

  Calibration stores use 329301 + c, built from the calibration stream up to 16,384 updates.

**R9.** This is covered by R6's sentence on non-finite events after U_4.

**R10** (Status block). Replace "the study still answers "does the lead persist" over the range it trained" with "the study still describes whether the lead held over the range it trained".

**R11** (§18). Replace "R1 extensions, up to 4 more rates per arm" with "R1 extensions, up to 6 more rates per arm".

**R12** (§6.4 item 3). Replace "The implementation may stream, The order is fixed:" with "The implementation may stream. The order is fixed:".

**R13** (§16a G11). Replace "Calibration panel on calibration checkpoints at k_max" with "Calibration panel on calibration checkpoints at the last calibrated rung (4, or the cut ladder's last rung)".

**R14** (§20 item 2). Replace "Recommendation: (c); (b) is not available on fresh data." with:

> "Drafter's recommendation: (c). Reviewer's recommendation: (a), because (c) probably does not fire on P10-I-S3's trend and, when it fires, reads convergence at an uncalibrated rate; if (c) is taken, confirmation review R6 and R7 apply. (b) is not available on fresh data."

## D. Summary for the human lead (five lines)

1. If both arms converge within 16× the old duration, the study tells you whether the flat memory's lead over an equal-size dense adapter holds at convergence, on new parents and new data. That is the converged label.
2. Most likely they will not converge (the gain per doubling showed no bend). You then get a registered description of whether the lead held, shrank or was lost up to 262,144 updates, and nothing about the ordering at convergence.
3. It cannot tell you anything about cost, efficiency, SSD, scaling, the tree, other dense forms or other corpora. It cannot open ADR-0027's Route A.
4. Cost: about 16–31 charged hours on a shared machine. Inputs: one 0.3 GB download and 12 small backbones trained from scratch.
5. Ladder: I recommend (a), 16× without the continuation. (c) adds a weakly calibrated reading that will probably not fire; if you take it, apply R6 and R7.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
