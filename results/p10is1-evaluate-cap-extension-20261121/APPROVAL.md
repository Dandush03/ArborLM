# P10-I-S1 — approval of a 1-hour extension of the evaluate cap (2026-11-21)

`Astra review: NOT_PERFORMED`

This is the committed approval record that `docs/decisions/ADR-0024-addendum-evaluate-cap-extension.md` points to. It is not Astra validation.

**The question put to the human lead (as relayed to the implementer by the coordinator):** "Do you approve extending S1's evaluate cap by 1 hour so the last 12 cells can finish?"

**His answer, in person, on 2026-11-21 (as relayed; the implementer did not hear it):** "Approve 1 h"

Basis: ADR-0024 section 15 (a resource cap is extended by the human lead on cost projections only; an extension that takes the caps past 60 h is his own decision). Cost grounds as the coordinator stated them: 12 cells at the observed rate are minutes, the baselines were projected at 0.02 h, and about 15.6 h of the 52 h TOTAL cap are charged (the total cap is NOT extended).

Machine-read lines (`apply_extension.py` refuses without them):

```
EXTENSION: evaluate_hours +1.0
FREEZE_COMMIT: 46bf55a5cc0eda11b7201c4ab777e69c6970c4cd
TOTAL_CAP: unchanged
```
