# Corrections to the calibration README (2026-11-15 UTC), from the pre-freeze audit

`docs/reviews/p9ii-prefreeze-audit-2026-11-15/AUDIT.md` (Opus 5.5) confirmed the calibration: all 22 final snapshots re-scored with an independent forward match the record exactly, and the rule reproduces the four selected values. It found two errors in the lead's README, which is left as written:

- The README says the rule uses "Panel A accuracy". The rule and the code use accuracy on the calibration stream of each calibration draw; the numbers in the table are those.
- The README says A4 "reaches at most about half". 0.521 is the minimum over the two draws at k_0 = N/8; individual cells reached 0.848 and 0.903.

What the audit added (exploratory, on calibration and test seeds; not results):

- **A2's failure is a property of the registered design, not a defect.** At the end of the address-pretraining phase addressing had fully succeeded (target top-1 recall 0.996–1.000, 256 distinct slots for 256 probe facts). Within 64 updates of the switch to the answer loss the queries collapsed (1–4 distinct slots). The first step after the switch moves the query projection by 0.170 although the answer gradient on it is about 5e-5, because a freshly reset AdamW turns a tiny gradient into a full-size step. In the auditor's diagnostic runs any one of these avoided the collapse: addresses frozen in phase 2 (0.914 / 0.721), no moment reset for the addresses (0.971), a ten times smaller rate for the addresses (0.967), the answer path trained first (0.981).
- The moment reset was added in revision 2 on the auditor's own recommendation (M3) to remove an optimizer artifact; the diagnostic shows it introduces a worse one. **The lead keeps A2 as registered:** nothing but the calibrated values may change after calibration, and repairing an arm after seeing its calibration would be tuning. A2's registered outcome will therefore measure "staged optimization with a moment reset", and the variants above are candidates for a later, separately specified study.
- A4's behaviour is also the design: queries collapse during the anneal and escape only after k reaches 8, as the answer-only baseline does.

Astra review: NOT_PERFORMED.
