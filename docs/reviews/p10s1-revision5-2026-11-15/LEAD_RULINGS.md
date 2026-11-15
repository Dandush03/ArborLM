# P10-S1 revision 5 — the lead's rulings on the draft's open questions (§25.8), 2026-11-15 UTC

Written by the scientific lead before the independent review of the draft and before any run on the new grid. No registered seed has been observed. These are rulings on a draft; the review may overturn any of them, and the text is not adopted until the review's findings are closed.

1. **Cap ceiling.** C_max = 36 hours: the upper end of the draft's central extrapolation (35.2 h) rounded up to the hour. The cap itself is still computed by the draft's rule from rehearsed rates. A computed need above 36 hours after the three fixed cuts returns to the human lead; nothing is started.
2. **Saturation at three sizes.** The 16,384-slot saturation block (36–54 h) is not funded. A 256-slot cell at eight facts per slot (2,048 facts), F-OQ only, is added so that bits per slot when full is read at 256, 1,024 and 4,096 slots (two fourfold pairs). It is outside the sizes named to the human lead and is reported to them as the lead's addition; it adds a measurement, removes none, and enters no capacity step. If the review finds a 256-slot store ill-defined for the read (top 8 of 256), it is dropped and the saturation line stays one pair, labelled as such.
3. **Need above the ceiling after the fixed cuts:** return to the human lead (NOT STARTED: BUDGET). No further cut is improvised.
4. **Dense at saturation is binding**: a dense lead on the full cells counts as DENSE AHEAD and blocks the positive.
5. **The 0.80 floor of §8.4 read at 32K/16K:** accepted (value unchanged; the cell is the largest registered one).
6. **R2 reference at a 32,768-row table:** accepted.
7. **Plateau guard** (i* ≥ the DEP floor at half the run length): accepted, subject to the review confirming it cannot exclude a cell that has genuinely saturated low.
8. **U_P per row by rule:** accepted with the declaration in §25.6 that it was fixed after the curves were seen. The review is asked to say whether this opens a route to a favourable label.
9. **A loaded cell that is not loaded within its search ceiling:** the step is fixed as CAPACITY NOT TESTED by rule, recorded, and the study proceeds. It does not return to the human lead a second time.
10. **Efficiency line:** kept on the two control steps.
11. **T-OQ against D-OQ possibly MC-AMBIGUOUS:** no rule change.
12. **One number (3.0) on both sides of the saturation line:** accepted provisionally; the review is asked whether the negative side is reachable.

---

## Rulings on the independent review (`review/REVIEW.md`: READY AFTER M1–M7), 2026-11-15 UTC

- **M1 accepted; ruling 9 above is withdrawn.** A loaded cell that is not loaded within its search ceiling returns to the human lead, as drafted. Proceeding automatically would contradict the human lead's direction of §23 and could only print NOT TESTED.
- **M2 accepted.** The text states that 32K/4K was already seen at 15.1–15.5 bits per slot at 65,536 updates, that PROPORTIONAL is therefore the likelier reading of the saturation line, and what a negative requires (the reviewer's text).
- **M3 accepted.** The crowding of the fixed-width oracle codes as the fact set grows is stated as a confound of the saturation line with the reviewer's measured shares, and a SUBPROPORTIONAL reading carries that label; it is not attributed to the store.
- **M4 accepted.** The declaration of the per-row U_P rule also names its effect on the 0.80 floor at 32K/16K.
- **M5 accepted.** The cap is computed from six-worker rates measured in the rehearsal under the load that will hold in the registered run. S1's timing preview, isolated timing, rehearsal and registered run do not overlap P10-S0's registered run: they start after S0's last training stage has finished. This costs no science and needs no new decision from the human lead (their recorded permission for concurrent studies is not used here). Overlap with P10-S2 follows the conditions already recorded and is rehearsed under that load or not used.
- **M6 accepted** with the reviewer's text: the 256-slot cell is F-OQ only, 31 configurations per replicate, 155 cells, 70 calibration runs.
- **M7 accepted.** The reviewer's tie rule for the matched-compute reading is adopted and the claim that the reading is "established for every arm" is removed.
- **Minors:** all applied as the reviewer wrote them unless the drafting context finds one wrong, in which case it is listed for the lead and not silently skipped.
- Rulings 1, 3, 4, 6 and 10 stand; 2, 5, 7, 8, 11 and 12 stand with the reviewer's required text. C_max stays 36 hours.
