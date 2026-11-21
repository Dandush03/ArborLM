# P10-I-S0 — Decision 2 (2026-11-19 UTC)

DECISION: RUN

Freeze commit: 58cef50acb61d5cc2beea72bdffad112227fa689

Taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` on `main`, sections 1 and 7). It is a decision of the lead under that delegation, not a decision the human lead read and signed; he can overrule it. It covers the registered stage `main` (200 cells), then `analysis` and `report`. The conditional load-8 extension (`x8-gate`, `x8`) is covered only if the registered trigger (L_Q = 4 after the complete main grid) fires by code, and is reported before it starts.

Stated before anything registered runs, and to be reported to the human lead first:

1. **Convergence was not shown in the calibration at the four high-load cell types** (public tags of Stage R only; no sealed value was opened): 2K/1K, 2K/512 and 8K/2K are CONVERGENCE NOT SHOWN IN REHEARSAL and were granted the one registered extension (T = 16,384 exposures); 8K/4K is CONVERGENCE NOT SHOWN — EXTENSION REFUSED (BUDGET), because its extension projected 55.61 h against the registered B = 55 h, and runs at T = 8,192. The four cell types at load 1 or below are SHOWN (T = 1,024 to 8,192). ADR-0023's rules cap what any label can claim for a cell type whose convergence was not shown. No reference flag, no removed cell type, no event of section 5.2.
2. **Stage R stands under a recorded identity rebind** (`RULING_CODE_CHANGE.md` beside this file, with both audits): its final status print crashed on a false positive of the leak guard; four files changed afterwards (output validation and commands only). The human lead can overrule that ruling, in which case Stage R (about 6 h) is rerun and this freeze is void.
3. **Cost.** Charged so far 6.30 h (gates, rehearsal, generation, timing, Stage R, a0-memory). Projection for what remains 53.36 h at the larger of the quiet and busy rates with six workers, the conditional load-8 part included (main about 30.6 h; load-8 calibration about 6.2 h and load-8 about 14.4 h, only if triggered; analysis and report 2 h as an allowance). Caps by the rule (charged + 2 x projected): main 61.15 h, load-8 calibration 12.43 h, load-8 28.82 h, total 113.01 h. The projection is inside B = 55 h and below the 75 h above which the lead undertook not to start the main grid without the human lead's word. The caps are resource caps, never a label. Disk projection for the main grid 39.3 GB (646 GB free).
4. Timing was READY on the second quiet attempt (the first was NOT QUIET and is kept); six workers; peak memory about 0.5 GB per worker, 0.37 GB in a0-memory at the longest duration.
5. Rulings of the lead on the audit's open advisories: E3 — the registry checker copy excludes P10-I-R's own files, by ADR-0029 ruling 6, and the seed gate passed at this freeze; the definition of RATIO ABOVE 1 is descriptive and stands as implemented; G1 of REAUDIT7 (the leak guard's digest exemption accepts any lowercase extension inside a hashes map: a name, never a value) is left open.
6. Seal attestation: lead, implementer and auditor attest that no sealed value was opened.
7. The machine is shared during this run with P10-I-S2 Part Q's registered attempt 2 and with subagents. The main grid registers no wall-time reading; its rates were projected at the busy figure.
8. The lead commits nothing and writes nothing in this worktree between the start of a registered stage and its end.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
