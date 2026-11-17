# P10-S1 pre-freeze audit (2026-11-16)

- **Reviewer:** Claude Opus 5.5 (`arbor-auditor`), at head `8b6b6bf` of `claude/p10-s1`, read-only, with its own scripts. Written up by the lead (Claude Fable 5.2) from the reviewer's report. Independent engineering review; not Astra validation and not human approval. Astra review: NOT_PERFORMED.
- **Verdict: READY AFTER FIXES** — one blocker (finding 1). The lead's rulings are in ADR-0021 §25.17.

## Findings

1. **Blocker — the freeze cannot record S0's accepted outcome truthfully.** With S0's record (`ADDRESSING-QUALIFIED (4,096 AND 16,384)`, candidate A5-D, overload not qualified) `frozen.lane_l_status` gives "OMITTED — NOT OVERLOAD-QUALIFIED", but `s0_status_and_lane` sets the return-to-lead flag and `cmd_freeze` refuses before writing anything. Without the record the freeze writes "S0 NOT YET DECIDED" and "OMITTED — no interface qualified before the freeze", both false now; an unrecognised outcome string falls through to the same false label. ADR §22 (b) returns the question to the lead with no default; §5.6 item 2 names this case; nothing stops S1. Needed before the freeze commit: the lead's ruling, S0's record files with hashes, and an audited code path that writes the ruled label.
2. **Minor — contention ratio.** The code follows the registered rule (c from the rehearsal as measured, 1.9457: §25.12 item 2, §25.13, §25.16). The freeze README step 8 and a bullet of §10.3 still give the rejected "larger of" reading. For information: with 2.2015 the need would be about 193,548 s (53.76 h), cut 1 would apply, and the cap would be 50 h.
3. **No defect — the C_max change.** Commit `543f1bf` touches only the ceiling and its source note. Recomputed: remaining 74,157.850 + 353.997 fixed = 74,511.847 s; C_need = 25,740.757 + 2 × 74,511.847 = 174,764.451 s (48.55 h); cap 49 h; no cut. The two projections agree in rates, contention, dense rates, plan values, fixed costs, baselines, memory, generation, H8 lists and charged seconds.
4. **No defect — the plan the freeze will write.** 178 cells: 150 per-replicate cells (30 configurations × 5 draws) and 28 seed-block cells (initialization seeds 2111/2121 on draw 1, 2112/2122 on draw 2; replicate seeds 2101–2105). Run lengths 393,216 at 8K/1K and 786,432 at 32K/4K; every cell's snapshots stay within its run length and include its U_P. D-OQ rates 0.1 at 2K/4K and 8K/4K, 0.03 elsewhere. No 524,288 ceiling or 36-hour figure remains in live code.
5. **Minor — `6f7b1d8`.** The four extension-audit findings are fixed. The cap file was written at 15:52:08.60 and the pool started at 15:52:08.79. A double launch is possible only if two invocations race before either writes the cap file; moot now that calibration is complete.
6. **Major (record quality only) — the registered `timing` stage.** It measures throughput and requires a load average of at most 1.0 (three retries, 120 s apart); its cap (399.5 s) is twice a projection of the CPU timing, and the throughput measurement itself was never timed. Under load the record says THROUGHPUT NOT MEASURED; if the machine turns quiet on a late retry the stage is likely STOPPED BY CAP. Neither blocks the analysis or the report.
7. **Passed — generation cap.** The five registered draws took 26.6–26.9 s each against 40 s, G1 passed.
8. **Minor — ledger and gates headroom.** 25,874.5 of 176,400 s charged; stage caps sum to 149,015 s, leaving about 1,510 s of slack if every stage reaches its cap. The gates cap is the 60 s floor, from one rehearsal draw (5.55 s); the registered gates stage checks five draws (estimate 15–30 s).
9. **No defect — the merge of main (`79cb472`)** changed nothing under `studies/`, `src/`, `configs/`, ADR-0021, `uv.lock` or `tests/test_p10s1_*`. The Decision 2 check reads committed content only.

## Not checked

Pool kill semantics, the evaluate and analysis numerics, the end-to-end run, the full suite, and the duration of the throughput measurement.
