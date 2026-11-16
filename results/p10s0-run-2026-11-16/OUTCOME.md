# P10-S0 — outcome statement (2026-11-16 UTC)

ArborLM is unproven research. **Status: registered run complete and independently recomputed; NOT YET ACCEPTED BY THE HUMAN LEAD.** Astra review: NOT_PERFORMED. The recomputation is a Claude review (Opus 5.5), not Astra review and not human approval.

## The registered outcome, as it must be cited

**Outcome (row 4): ADDRESSING-QUALIFIED (4,096 AND 16,384)** — arm A5-D (label-free; diversity penalty μ = 1.0), 512 exposures per fact, 0.5 facts per slot.

Wherever this label is cited, these lines go with it (the lead's ruling on the recomputation's points, below):

- **Provenance.** A5-D was added by the human lead's decision after P9-II's outcome was observed, knowing it was RELIABLE there. For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test.
- **Against the answer-only arm A0:** IMPROVES ON A0 at 4,096 slots (d = +11 of 20 pairs, sign test p = 0.001); **NOT DISTINGUISHED FROM A0 at 16,384 slots (d = +1); H20-D reads not supported.** A0 is itself RELIABLE at 16,384 (9 of 10 draws) though every one of its cells had a collapse onset and recovered; A5-D had none in 20 of 20 cells at either size.
- **OVERLOAD NOT QUALIFIED.** At two facts per slot (8K/4K) A5-D succeeds in 1 of 10 cells. The recomputation shows the nine failures are on condition 4 (held-out templates) alone, at about 0.95 accuracy, with no collapse.
- **RECORD-LENGTH-FREE VARIANT: DOES NOT PASS** (2 of 10 and 0 of 10 cells); not evidence that the record length is required.
- **65,536 slots:** a probe only (3 of 3 draws, one initialization seed, per-draw bound 0.368); not a qualification.
- The memory is told the answer position in every arm. Nothing here is about capacity, transfer, efficiency, natural language or another backbone. It is not a success of the ArborLM concept and not a failure of it.

Other readings: A1 (address supervision) RELIABLE at 4,096 and UNRELIABLE at 16,384 (H20-B CONTRADICTED); A2 FAILS at both (H20-C CONTRADICTED); every comparable class REPLICATES P9-II.

## Independent recomputation

`docs/reviews/p10s0-results-2026-11-16/REVIEW.md`: **AGREES WITH NOTED DEFECTS** — 1,065 comparisons recomputed from the raw per-cell records with independent code, 0 disagreements; integrity passes (frozen code and plan, registered order, no cut, no reserve, no failed cell, committed files byte-identical to the run directory).

## The lead's rulings on the recomputation's points

`RESULTS.md` is the registered report and is not edited. Its presentation defects are recorded here:

- Raw dictionaries are printed in the notes of five hypothesis rows (H20-B, H20-C, H20-D and the two A5-D H20-R rows). They hide nothing.
- **"A0: qualifies at 16,384 ONLY" and "A1: qualifies at 4,096 ONLY" in the Qualification section do not stand as statements of qualification.** ADR-0020 defines no single-size scope and A0 cannot be the candidate at any scope. They are per-arm descriptions of where the class was RELIABLE and must not be cited as qualifications; the registered line is "ALSO QUALIFIES: A1 (4,096 ONLY)".
- "FAILS — ALSO AT MATCHED UPDATES" misuses a tag that belongs to a RELIABLE class; read it as "the readout at U also fails". Duplicated or empty label text ("ADDRESS STABLE ADDRESS STABLE") is cosmetic.
- The provenance strings are missing from the section "Annotations on the candidate" and the H20-O, H20-L and H20-S rows; they apply there too.
- Summaries of the outcome carry A5-D's paired labels, H20-D's reading and OVERLOAD's failure reason, as listed above.
- Condition 6 (S0's stricter criterion) decided no class: classes under S0's and P9-II's criteria are identical everywhere. Recorded as an observation for the design of later studies; it changes nothing here.

## Timing (MEASURED)

21,941 s charged (6.09 h) of the 22-hour cap. Stages ran at 0.40–0.63 of their projections, which used rates rehearsed under load.
