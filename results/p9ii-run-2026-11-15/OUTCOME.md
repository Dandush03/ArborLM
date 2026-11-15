# P9-II (ADR-0019 revision 4) — outcome of the single registered run

- **Written by the lead (Fable 5.2) after the independent recomputation.** Opus 5.5 recomputed every registered decision from the raw records with code written from the ADR text: 171 comparisons, 0 disagreements, integrity checks hold (`docs/reviews/p9ii-results-2026-11-15/REVIEW.md`).
- **Not accepted by the human lead at the time of writing.** A Claude review is not an Astra review. Astra review: NOT_PERFORMED. No breakthrough is claimed.

## Registered outcome

**Study COMPLETE. ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0.** (§8.6 row 4.) Interface carried forward under the registered order: **A0**. Stage 3: **SCALE PROBE UNINFORMATIVE**.

| Hypothesis | Reading |
|---|---|
| H19-A collapse with starved addressing gradient | not supported |
| H19-B address supervision (A1) | supported |
| H19-C staged optimization (A2) | CONTRADICTED |
| H19-D top-k curriculum (A4) | CONTRADICTED |
| H19-F query centring (A5-C) | not supported |
| H19-G diversity penalty (A5-D) | supported |
| H19-E draw robustness | supported for A1 and A5-D (at 4,096); not for the others |

## What the records show, in plain words

1. At 4,096 slots the answer-only interface succeeds in 4 of 16 cells over 8 draws. Its unreliability across draws is now a registered observation, not an exploratory one.
2. A label-free diversity penalty on the batch's queries succeeds in 16 of 16 cells at 4,096 and 8 of 8 at 16,384, and is never in the collapsed category. Address supervision succeeds in 16 of 16 at 4,096 and 6 of 8 at 16,384.
3. At 16,384 slots with four times the updates, the answer-only interface also succeeds in 8 of 8. At matched updates it is at chance in all 8 (it escapes between about 10,900 and 18,800 updates). The registered class is read at four times the updates, so at this size the diversity penalty is not distinguished from the baseline.
4. Random-target supervision never helps: the benefit of address supervision is fact-specific.
5. The dense control is at ceiling at both sizes. No memory arm is shown ahead of a dense model.

## Findings of the audit and the lead's rulings

No rule, threshold or reading is changed after observation. The rulings below only say how each finding is recorded.

- **F1 (major) — the carried-forward arm.** §8.6 literally selects A0 (first RELIABLE arm at 16,384 in the registered order). The ADR did not anticipate A0 being UNRELIABLE at 4,096 and RELIABLE at 16,384 (4U). **Ruling:** the registered selection stands as printed, with this annotation attached wherever it is cited: *A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.* Whether a later study uses A0, A5-D or both is a design decision for that study's own specification and approval, not a result of this one.
- **F2 (major) — H19-A.** Every A0 cell collapses by update 64, but the gradient-ratio clause holds in 0 of 16 cells (ratios 0.034–3.6 against ≤ 0.01). **Ruling:** H19-A stays "not supported". The collapse is observed; the registered mechanism (a starved addressing gradient) is not.
- **F3 (minor) — A1-S.** Its query-projection gradient after the first 1,024 updates is about a tenth of A1's, so it is a weaker gradient-magnitude control than the ADR describes. It did its registered job (0 successes at both sizes). Recorded as a limitation of the control.
- **F4 (minor) — A1 at 16,384.** One of its two failures misses the H1 line by half a fact. Its class stays UNRELIABLE as registered; the outcome row does not depend on it.
- **F5 (minor) — HARMS at the minimum count.** HARMS for A2, A4 and A1-S at 4,096 is d = −4 exactly (A0's four successes, p = 0.125). The labels and the CONTRADICTED readings stand as registered; the evidence that these arms are *worse* than A0 is weak, the evidence that they are *not reliable* (0 of 16) is not.
- **Not checkable from the stored records:** byte-level disjointness of the held-out templates from training, and tie counting in accuracy. Both are covered by unit tests and gate G1, not by this audit.
- **Corrections to the lead's README:** peak worker memory was 0.702 GiB in training and 0.881 GiB in evaluation (not 0.75 GiB); "H1 0.888 against 0.888" is a miss by half a fact. See `CORRECTION.md`.

## What may be said

- On this synthetic task, backbone and interface, a label-free diversity penalty made sparse address learning reliable across 12 registered data draws at two memory sizes, where answer-only training was unreliable at the smaller size and slow at the larger.
- Answer-only training recovers by itself at 16,384 slots given four times the updates.

## What may not be said

- Nothing about capacity, useful-capacity scaling, locality, incremental learning, natural language, other backbones or 65,536 slots.
- Not that the diversity penalty beats a tuned baseline (A0 is untuned), nor that any memory arm beats a dense model, nor any efficiency claim.
- Not that the mechanism of collapse is understood.
- Not a breakthrough. One run of one registered design, reviewed by Claude models only.
