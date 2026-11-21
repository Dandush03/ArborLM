# Confirmation review 3 of ADR-0032 (revision 3, commit a9558ba)

Reviewer: arbor-auditor subagent (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-20. Claude review is not Astra review. `Astra review: NOT_PERFORMED`. Not human approval, not validation. Nothing here is a result.

## What was read and run

**Read:** ADR-0032 revision 3 in full, and `HUMAN_LEAD_DECISIONS_2026-11-20.md`. `LITERATURE_NOTE_2_SELF_LEARNING.md` was not spot-checked (not in scope).

**Ran** (trivial CPU, Python 3.15.1, `python3 -I`):
- `diff` of Part A between 9881701 and a9558ba: unchanged.
- `adr0032_power/power3.py`, output in `power3.out.txt`.

## Verdicts

1. **G1–G18:** all closed. G9 is closed not as written; acceptable. G4 is closed with an addition; acceptable after H2. The ADR's table matches the text.
2. **Departures:**
   - (a), (b), (d), (e): accepted.
   - (c), (g): accepted with an edit.
   - (f): the objection is right. Arm 10 is mis-specified, and the error is mine (from my G7).
   - (h): accepted; a more powerful alternative is offered.
3. **E2, the gating question for tonight:**
   - E2.1 two levels of evidence: **yes**.
   - E2.2 margin rule: **yes**.
   - E2.3 power rule: **yes after H2**.
   - E2.4 labels of sections 5 and 6: **yes after H3**.
   - E2.5 M-ladder order: **yes**.
4. **Part S:** **READY TO PUT TO HIM after H4.** H5–H7 may go to him as listed open edits.
5. **Weakening or overreach:** one weakening of his decision 2 (H1). One small inconsistency (H8). No overreach found.

## 1. G1–G18

| G | Status |
|---|---|
| G1 | Closed |
| G2 | Closed |
| G3 | Closed (word for word) |
| G4 | Closed with addition (see (c), H2) |
| G5 | Closed |
| G6 | Closed |
| G7 | Closed as I wrote it, but my wording was wrong (H4) |
| G8 | Closed (E1.20 added) |
| G9 | Closed not as written; acceptable (see (b)) |
| G10 | Closed. The crossed arms and the three separate numbers improve on my wording |
| G11 | Closed |
| G12 | Closed |
| G13 | Closed |
| G14 | Correctly recorded as decided only in part |
| G15 | Decided, but the definition it binds is loose (H1) |
| G16 | Decided |
| G17 | Closed |
| G18 | Closed |

## 2. Rulings on the departures and objections

- **(a) Accepted.** The decision record asks only which label meets "capabilities that neither teacher provides independently". The rest of the mapping correctly stays in E1.5.
- **(b) Accepted, with an edit for Part S (H6).** A FLOP count is computed, not measured. It must not support an efficiency claim. It is still the natural unit for matching budgets between arms on a shared machine, so say so.
- **(c) Accepted with H2.**
  - The sample size depends only on development data, so raising it cannot bias the sealed test.
  - "Never lowered" also guards against S's development discordance being understated after M1–M4 used that split.
  - Two definitions of "the discordance used" now coexist and must be merged.
  - A fixed public split cannot be raised.
- **(d) Accepted.** A guard used as a gate would need its own power calculation. The regression cap is his (E1.4).
- **(e) Accepted.** The record of his decision is not padded. The proposals sit beside it, marked.
- **(f) The objection is correct; arm 10 is mis-specified (H4).** Label 4 compares arm 1's single-attempt sealed score with best-of-N filtered by the same checker. On sealed code items that checker is the scorer, so arm 10 is pass@N with oracle selection. That is not a deployable system and not a matched comparison, so label 4 would nearly always fire. The question "could it be drawn out without learning?" needs a bar matched in inference compute, with pass@N printed as a ceiling.
- **(g) Accepted with an edit (in H5).** A development draw from the same frozen generator under another seed is statistically equivalent for sizing and for checking interior starts. Two gaps:
  - For S6, new-family templates that exist before the run can inform design. The families themselves should come from a seeded family generator under commit-reveal. The interior check is done on a development draw of other families from that generator.
  - A revealed set can still turn out to be at floor or ceiling. That must be a registered post-reveal outcome, not a re-draw.
- **(h) Accepted; offer the alternative.** The item cost of the cycle correction against a single test at 0.05 (80 % power, power3.out.txt) is ×1.43 at K = 3, ×1.62 at K = 5, ×1.89 at K = 10 and ×2.15 at K = 20. A fixed-sequence procedure keeps full alpha while gains continue: cycle 1 against 0, then 2 against 1, and so on, stopping at the first failure. Suggested wording is in H7.

## 3. Findings

### H1. REQUIRED (weakens decision 2 as written). INTERFERENCE needs a defined test.
Now that INTERFERENCE bars acceptance, "a loss beyond the margin" is ambiguous: it could mean a point estimate. Replace the Interference bullet's second sentence with:

> **INTERFERENCE (named evaluation)** is printed unless the one-sided lower bound of (score of S taught by both teachers − score of S taught alone by the teacher stronger on that evaluation) lies above −δ_e, paired, under the statistics of section 5. These tests join the power conjunction of section 5.

### H2. REQUIRED before E2.3. Merge the discordance definitions; handle splits that cannot be raised.
Replace "The discordance used is, per evaluation, the largest measured in M0 between S₀ and any Tier 2 reference" and the italic addition with:

> The discordance used is, per evaluation, the larger of (i) the largest measured in M0 between S₀ and any Tier 2 reference and (ii), once S exists, the largest measured on the development split between S and any Tier 2 reference or S₀. In M0 a sealed pool is created per evaluation at a registered maximum size and hashed in the freeze. The sealed split is drawn from it by a registered seed at the size fixed; the size may be raised, never lowered, before any sealed score. Where the required size exceeds the pool or a fixed public split, the evaluation is NOT EVALUABLE (UNDERPOWERED), decided before any sealed score.

### H3. REQUIRED before E2.4. The Tier 1 label must not be earned against a chosen subset.
"MATCHES CONVENTIONAL ADAPTATION (TIER 1, named systems)" lets the weakest Tier 1 system be named. Replace it with:

> **MATCHES CONVENTIONAL ADAPTATION (TIER 1)**: the test of section 5 passes against every Tier 1 system of the registered set; otherwise **NOT MATCHING CONVENTIONAL ADAPTATION (named systems)**.

Also add **RETENTION HOLDS** and **RETENTION FAILS (named capability and order)** to section 6 as its labels; at present only M3 names them.

### H4. REQUIRED before Part S goes to him. Arm 10 split into a bar and a ceiling (my G7 error).
Replace arm 10 with:

> 10a. **Elicitation at matched inference:** S₀ and the cycle-0 system with the arm-1 practice items' verified solutions as in-context examples, the same number of attempts and no more inference compute per sealed item than arm 1, with no selection by the scorer.
> 10b. **Base ceiling, printed, not a bar:** S₀'s pass@N on the sealed items, N registered (e.g. 64).

Replace label 4 with:

> 4. **GAIN WITHIN ELICITATION (DRAWING OUT NOT EXCLUDED)**: arm 1 is not above arm 10a beyond δ.

Add a qualifier: **ABOVE BASE PASS@N** or **WITHIN BASE PASS@N (SHARPENING NOT EXCLUDED)**. Acquisition is still claimed only on the novel family. Update the section 9 bullet "Arm 10 is a severe bar" accordingly.

### H5. RECOMMENDED. Commit-reveal for S6 families.
Add to the S2 commit-reveal bullet:

> New families for S6 are themselves drawn by commit-reveal from a seeded family generator frozen before cycle 1; the interior check uses a development draw of other families from that generator. A revealed set found at floor or ceiling is NOT EVALUABLE (FLOOR OR CEILING AFTER REVEAL); it is never re-drawn.

### H6. RECOMMENDED. Compute matching.
Add to S2, "Capability and efficiency":

> Budgets between arms are matched in a registered counted unit (FLOPs or tokens processed, generation and verification included); this matching supports no efficiency claim, which needs measured cost.

### H7. RECOMMENDED. A more powerful alternative to correcting over cycles.
In S2 Replication and S5 ACCUMULATES, replace "Holm, or each at 0.05/K" with:

> by a registered fixed-sequence procedure (cycle 1 against 0, then 2 against 1, …, each at 0.05, stopping at the first failure; m counts the gains before it), or by Holm over the K tests, chosen in the specification.

### H8. RECOMMENDED. Fifth scorecard row.
E3 says the lead "will add" the fifth row, but E1.7 lists it as his decision. Make it one or the other: either the lead adds it at 0 under his "add those metrics" request and E1.7 only confirms it, or it waits for him.

## 4. Own slip recorded
My G7 wording made arm 10 a bar at pass@N with selection by the scorer (H4).
