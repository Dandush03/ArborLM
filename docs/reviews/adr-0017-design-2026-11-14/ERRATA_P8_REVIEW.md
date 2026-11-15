# Errata to the P8 results review, found during the ADR-0017 evidence inventory (2026-11-14)

The P8 review (`docs/reviews/p8-results-2026-11-14/README.md`) is a completed-study record and is not edited. These corrections are recorded here and in the research log. None changes a registered P8 number or class.

1. **§3 of the review says the soft mass outside the top eight went to about zero in C04, C05 and C10.** For C10 the training record gives 0.209 at update 512. The statement holds for C04 and C05 only. (Lead's error.)
2. **The review's resource table shows the simulation stage's peak RSS as "—".** The simulation manifest records 268,206,080 bytes.
3. **"λ rose to about 6·10⁵"** is the C05 maximum (603,648). C10 peaked at 464,230 and C04 at 393,250.
4. **Not an erratum, a limit:** P8 recorded total key movement only. Whether rows without task gradient moved was never measured, and no P8 document should be read as showing it.

Source: `EVIDENCE_INVENTORY.md` in this folder (Haiku 5.5), which cites file and key for each figure. The lead has not re-derived items 1–3 independently.
