# P10-I-S1: acceptance by the human lead (2026-11-21)

On 2026-11-21 the lead (Claude) asked the human lead: "Do you accept P10-I-S1's outcome as registered, with the labels produced through the corrected loader — accept, or review first?" He answered, in the working session:

> Accept S1

This is the acceptance of a registered result whose capacity line is negative for the store. It is not a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. `OUTCOME.md` is left as written (its statements that the outcome was not yet accepted were true then); this file records what came after.

## The labels, unchanged

| Line | Outcome |
|---|---|
| C-CAPACITY | CAPACITY-NEGATIVE (row 4, clause (b), arms [F-OQ]) |
| C-SATURATION | SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; arms F-OQ; EIGHT FACTS PER SLOT; 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED] |
| C-EFFICIENCY | EFFICIENCY-INCONCLUSIVE |

Every disclosure of `OUTCOME.md` stands beside the labels, with the independent recomputation (`recomputation/RECOMPUTATION.md`). In particular: CAPACITY-NEGATIVE is the rule as written and is not a dense lead at matched compute (the dense map is ahead at its best snapshot and at saturation; the flat memory is ahead at equal updates and at matched compute at 32K/16K).

## What the acceptance covers

- **The route by which the labels were produced.** The question named it, and he accepted it: the frozen analysis and report functions run on the registered records through the disclosed corrected loader (`docs/decisions/ADR-0024-addendum-analysis-loader-defect.md`). The registered `analysis` and `report` stages remain recorded as ENGINEERING STOP — ANALYSIS LOADER DEFECT. No amending freeze was asked for.
- **The evaluate cap extension** was his own decision earlier the same day ("Approve 1 h").

## What it does not cover

- The lead's other rulings and procedures of this study were not confirmed one by one and stay on his review list: the quiet-rule rulings, the second projection and the total cap of 52.0 h, the hand set-aside of the old plan, Decision 2 (taken by the lead under delegation), the ledger credit as the carrier of the extension, and the ruling on how panels combine in the dense-speed label. He may still overrule any of them; the record would then say so in a new file.
- It authorizes no new study. Block X (16,384 to 65,536 slots) is not approved.

## Meaning for the programme

Component evidence only: recall of trained random facts, oracle-addressed, on one small frozen backbone. By the human lead's criterion of 2026-11-20 it establishes nothing about capability parity with reference models. ADR-0024's own reading of this outcome: on this task the dense map is the better use of the parameters; what the store offers must then be shown elsewhere, in studies designed for it.
