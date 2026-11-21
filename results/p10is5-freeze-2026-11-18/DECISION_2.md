# P10-I-S5 — Decision 2 (2026-11-19 UTC; 2026-11-18 local)

DECISION: RUN

Freeze commit: 45a2c84ec28ccd1f2807c1eb363e1ba4bbbb196f

Taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` on branch `claude/p10-i-r`, sections 1 and 7: "accept the results as they come and continue with the next simulations until you conclude P10-I-*"; "you have my permission to auto approve everything until you complete P10-I"). It is a decision of the lead under that delegation, not a decision the human lead read and signed; he can overrule it.

Reported to the human lead first (ADR-0028's rule for choices a reviewer advised should be his and that the lead takes under the delegation):

1. **The restated entry condition EC3** (ADR-0028 section 3.1) and **the scope decision** (section 2.4): this study is the ENGINEERING part only. It measures whether exact reads of a synthetic store held on this machine's internal SSD can be counted and timed cold. It involves no neural memory, and its scientific part is not evaluable as capped. No result of it says anything about a memory's quality.
2. **The quiet-load ceiling is looser than intended, through the lead's own handling.** R1's idle window was started about two minutes after an unrelated test run ended, so its loads fell from 3.64 to about 1.4 during the window; the registered rule (95th percentile + 0.5) gives a ceiling of 3.53, where a settled machine would have given about 2. The window was not retaken: choosing a second window after seeing the first would be a selection. The four disk-activity ceilings come from the same window and are not known to be affected. Every block still records its own readings at start and end.
3. **R1 needed three attempts.** Attempt 1 (2.5 h, nothing written, stopped by the lead's own deadline) and attempt 2 (stopped by the lead after one minute) could not take an idle window: the launch script's keep-awake watcher (`caffeinate`) was counted as another study's process. Fixed in `c2f316d` (the watcher started by the stage's own launcher is part of the stage; each idle reading is written as it is taken), confirmed by the independent auditor (Claude Opus 5.5, `REAUDIT3_P10IS5.md`: CONFIRMED — READY FOR R1), on the condition, kept here, that every quiet stage is launched as one command with its output redirected to a file and that the lead makes no other tool call while it runs. Lead's ruling, a departure from the letter of section 8: "no other study's process alive" excludes the stage, its ancestors, its descendants and that watcher, and nothing else. Logs of both attempts are kept. Neither wrote to the drive or charged time.

Records this decision rests on:

4. R0 passed. R1 PASSED on attempt 3: the physical counter was exact on every band check, the store was held COLD, the positive control passed; 1.20 GB written of the 10 GB cap (permitted by the human lead: 250 GB).
5. M: MARGIN DETERMINED, m_t = 0.1, coefficient of variation 0.0126 over 240 passes, no TIMING SPREAD, no pollution, no rebuild, spare unused.
6. Config fixed before the candidate plan (commit `7338dd4`): m_t, the five quiet figures from R1, and the caps by the rule (charged + 2 × projected remaining): rehearsal 560.5 s, E1 600 s, E2 800 s, total 1,960.6 s (0.5446 h). Two tests that assumed a provisional config were made independent of the planning state in the same commit; no threshold was touched.
7. Candidate plan `3ee2a47016705bb7b6f5348c49215f1fb0d637fdcf26b538d5dd4dc8e4bee2ca` (commit `a2c08b3`); counting rehearsal K COMPLETE against that file (144 passes, 36,864 requests, 251,136 distinct pages, 4,114,612,224 bytes enumerated). Charged before the freeze: 288.4 s, all in the rehearsal group. Seed gate passed (own fail lines none; the foreign lines belong to P10-I-R, excluded by ADR-0029 ruling 6).
8. Lead's rulings on the audit's open advisories: A2 — an ENGINEERING STOP in M did not occur, so the missing path is moot for this run; A4 — K's enumeration, analysis and report were not charged (seconds), so the 288.4 s is a slight undercount and the caps are stricter for it; A5 — the spare is used per cell at pass level, and after its first use it serves neither a whole block nor a rerun, the conservative reading of "serves one invalid block or one such rerun".
9. The code after the last full audit (`5ad9142`) changed only by `c2f316d` (audited) and by the config and test commit of item 6 (not separately audited; it holds measured figures the freeze re-derives from R1's and M's records, and the caps).

This decision covers the registered stages E1, P, E2, analysis, report and delete, run once, as frozen, each alone on a quiet machine. The outcome is accepted as registered; an independent recomputation follows before any outcome record.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
