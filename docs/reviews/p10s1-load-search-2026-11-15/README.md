# P10-S1 — the no-loaded-cell condition: curve analysis, a drafted extension and its independent check (2026-11-15)

- `DRAFT_AMENDMENT_LOAD_SEARCH.md` — a draft "§24, extension of the load calibration" by a Fable 5.2 drafting context, with its curve analysis (`load_curve_analysis.py`, `.out`). **Not adopted. Nothing in it has been run.**
- `CHECK_LOAD_SEARCH.md` — the independent check (Opus 5.5) with its scripts and outputs (`audit_*.py`): READY SUBJECT TO listed edits; six majors.
- Everything here is read from the calibration draws (`results/p10s1-calibration-2026-11-15/`): calibration, never results. Extrapolations are extrapolations. Astra review: NOT_PERFORMED.

## What the check established

- The curves and the plateau rule are as the draft states; continuing a calibration run from its stored checkpoint reproduces an uninterrupted run.
- Extrapolated over six curve families: 4,096 slots at 8 facts per slot would first meet the plateau rule between 131,072 and 393,216 updates at about 1.9–2.3 bits per fact; 16,384 slots at 4 facts per slot is loaded only if that store saturates near 3.6 bits, which the 4,096-slot evidence (about 17 bits per slot) points against.
- **The loaded 4K→16K row could only give a positive.** At matched updates the larger store is about 3 bits per fact ahead, so NO GAIN, REVERSED and NOT LOADED are out of reach for that row; its outcome is close to foregone given the calibration.
- **The unchanged study does not fit its 16-hour cap on measured rates** (17.6–20.2 hours under the twofold rule). The 4K row alone needs 21–31 hours; both rows never fit under 32.
- Nothing in the extension predicts whether T-OQ, H8 or the index read are loaded.
- The auditor's recommendation: the extension is cheap and its first two stages at 16,384 slots decide whether S1 can reach any capacity outcome; but a better answer to the capacity question would come from shifting the grid down (1,024 → 4,096 → 16,384 slots at 8 facts per slot, where references exist and runs are cheap) or from closing the gap between the 4.0 threshold and the ceiling. Either needs the human lead.

## Status

Returned to the human lead with the lead's recommendation. No further S1 run has been made.
