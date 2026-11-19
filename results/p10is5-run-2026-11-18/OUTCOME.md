# P10-I-S5 — outcome record (engineering part of ADR-0028; 2026-11-19 UTC, 2026-11-18 local)

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This record claims no success for the project and says nothing about any memory: no memory, key, query or index was in the file.

Run once, as frozen: freeze commit `45a2c84ec28ccd1f2807c1eb363e1ba4bbbb196f`; Decision 2 `results/p10is5-freeze-2026-11-18/DECISION_2.md` (taken by the lead, Claude Fable 5.2, under the human lead's delegation of 2026-11-18; not read and signed by him). Accepted by the lead under the same delegation after the independent recomputation below. The human lead can overrule either.

## Registered labels (as the frozen code wrote them; `REPORT.md`, `analysis.json`)

| Line | Label |
|---|---|
| EQ-A, measured counter against predicted bytes | **BYTES CONFIRMED EXACTLY** (120 of 120 passes; 16,384 B per page; 3,428,843,520 B read) |
| EQ-B, a page inside a contiguous request | **CONTIGUOUS REQUEST CHEAPER PER PAGE** (rho(3) 0.377 to 0.444 in 5 of 5 repeats, against 1 − m_t = 0.90) |
| EQ-D, descriptive cost table | **COST TABLE REGISTERED** (24 cells; five tagged HARNESS-LIMITED) |
| Scientific neural-memory advantage | **SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)** — not approved, not evaluated |

One cold 16 KiB page at depth 1: pooled median 75.8 µs (p90 102.7, p99 130.0). Pages per second range from about 11,000 (depth 1, one page) to about 520,000 (64-page requests at depth 8 and above). These are host-side figures through a CPython thread harness on one Apple SSD behind APFS with FileVault, on a 4 GiB synthetic file that fits in RAM and was held uncached.

## Independent recomputation

`audit/RECOMPUTE_P10IS5.md` (arbor-auditor subagent, Claude Opus 5.5; own code, no import of the study's modules): **REPRODUCED WITH CORRECTIONS**. 963 quantities bit-equal to `analysis.json`; 839 numbers of the report within printed rounding; its own tiling reproduces the request lists of all 144 planned passes; all five blocks valid; every frozen file equals the freeze commit.

## Corrections and disclosures (the registered report is not edited; no number, label or table entry changes)

1. **A Docker virtual machine (Colima, the human lead's development stack) ran on the machine from about 20:31 local through K, E1, P and E2**, until the lead stopped it at 22:44. It is not a study process by the registered markers and every block's quiet readings passed. The recomputation finds no effect on any label; E2's disk rates and loads do not differ from before it started. Added spread in EQ-D's figures cannot be excluded (CV 6.9 % and 6.4 % at 1 and 8 pages, depth 1). The lead did not check for it before the registered stages: that is the lead's omission.
2. **The quiet-load ceiling (3.53) was looser than a settled machine gives**, because R1's idle window was started about two minutes after an unrelated test run (Decision 2, item 2). From the settled part of the same window the recomputation gets 2.32 for the load and 31.4 KB/s for reads; every E2 block also passes those (highest load 1.88, highest read rate 18.5 KB/s). No block was admitted that a settled window would have refused.
3. **The maxima of about 2.6 ms, and the p99 of the 64-page cells (where p99 equals the maximum at n = 64), are a first-request effect of each pass process**, not steady-state device latency: in 19 of 20 depth-1 passes the maximum is request 0, and M's blocks show the same.
4. E2's block 5 started after two failed quiet readings, about 21 minutes after block 4; which condition failed was not recorded.
5. M's block 5 was not quiet at its end (34 MB/s written, during the virtual machine's start-up) and M's record does not list it as invalid; leaving it out does not change m_t (0.10).
6. R1 took three attempts (Decision 2, item 3): the first two could not take an idle window because the launch script's keep-awake watcher was counted as another study's process (fixed in `c2f316d`, audited in `audit/REAUDIT3_P10IS5.md`). Neither wrote to the drive or charged time.
7. A4 of the implementation audit stands: K's enumeration, analysis and report were not charged (seconds).

## Cost

Charged 469.3 s (0.13 h) of the 1,960.6 s cap: rehearsal 288.4 of 560.5, E1 and P 14.8 of 600.1, E2 and analysis 166.2 of 800.3. Written 5,494,538,240 B, 54.9 % of the 10 GB cap (permitted by the human lead: 250 GB). SMART status Verified before and after. Lifetime writes, percentage used and temperature are not readable without administrator access. No download, no paid service, no administrator access.

## Deletion

The registered `delete` stage ran after the recomputation: the store, the rehearsal file and the control file are deleted (`records/delete/`); the data directory is empty; no snapshot retained the store.

## What this does and does not license

It licenses, for this machine and this harness only: that device reads of an uncached file can be counted exactly from the host; a measured cost of one cold page; that a page costs less inside a contiguous request, by the registered margin; and a descriptive table over six depths and four request sizes. It licenses no statement about a memory, a tree against a flat index, routing cost, whether storage is needed, other drives or systems, or writes and wear. The arithmetic-only table in the report is arithmetic on that table and not a measurement of any read path. A scientific SSD study still needs the prerequisites the report names: an approved learned-address capacity line and a licensed cell far larger than about 3 MB.

Files here: `REPORT.md`, `analysis.json`, `hours_ledger.json`, `write_ledger.json`, `records/` (R1's, M's and K's records, R1's idle readings, the deletion record), `audit/`. The full run directory (pass and block records, 28 MB) stays in the git-ignored `experiments/P10IS5-run-20261118`.
