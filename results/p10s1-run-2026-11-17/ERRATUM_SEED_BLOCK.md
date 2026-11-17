# P10-S1 erratum: the seed-block section of `RESULTS.md`

`RESULTS.md` (section "Seed block", lines 110–137) is kept as the frozen report stage wrote it. Its 28 lines are wrong: `studies/p10s1/analysis.py` (lines 167–169) stores the F-OQ-IVF read of a seed-block cell over its F-OQ read, so the printed "spread within draw" compares the main F-OQ seed with the extra seeds' F-OQ-IVF reads. Found by the independent recomputation (`audit/AUDIT.md`; script and output `audit/a5b_seedblock_bug.py`, `audit/a5b_seedblock_bug.out`). The section is descriptive and enters no rule; no outcome changes.

Corrected comparison (F-OQ reads only), spreads in bits. "Across" is the spread across draws, which the report printed correctly.

| Draw | Cell | Snapshot | Within draw, as printed | Within draw, corrected | Across draws | Dominates, as printed | Dominates, corrected |
|---|---|---|---|---|---|---|---|
| 1 | 2K/1K | U_P | 0.8349 | 0.0561 | 0.0401 | init seed | init seed |
| 1 | 2K/1K | U_run | 1.0710 | 0.0160 | 0.0301 | init seed | data draw |
| 1 | 2K/4K | U_P | 0.5188 | 0.0000 | 0.0085 | init seed | data draw |
| 1 | 2K/4K | U_run | 0.4961 | 0.0000 | 0.0000 | init seed | data draw |
| 1 | 32K/16K | U_P | 2.7691 | 0.0213 | 0.1907 | init seed | data draw |
| 1 | 32K/16K | U_run | 3.1722 | 0.0025 | 0.0105 | init seed | data draw |
| 1 | 32K/4K | U_P | 0.6649 | 0.0005 | 0.2375 | init seed | data draw |
| 1 | 32K/4K | U_run | 1.7496 | 0.0339 | 0.0258 | init seed | init seed |
| 1 | 8K/16K | U_P | 0.8594 | 0.0111 | 0.0131 | init seed | data draw |
| 1 | 8K/16K | U_run | 0.7940 | 0.0000 | 0.0000 | init seed | data draw |
| 1 | 8K/1K | U_P | 0.3248 | 0.0276 | 0.2500 | init seed | data draw |
| 1 | 8K/1K | U_run | 0.9245 | 0.0831 | 0.0617 | init seed | init seed |
| 1 | 8K/4K | U_P | 2.2268 | 0.0343 | 0.2381 | init seed | data draw |
| 1 | 8K/4K | U_run | 2.3850 | 0.0079 | 0.0175 | init seed | data draw |
| 2 | 2K/1K | U_P | 0.8342 | 0.0331 | 0.0401 | init seed | data draw |
| 2 | 2K/1K | U_run | 0.8441 | 0.0000 | 0.0301 | init seed | data draw |
| 2 | 2K/4K | U_P | 0.6211 | 0.0085 | 0.0085 | init seed | data draw |
| 2 | 2K/4K | U_run | 0.4221 | 0.0000 | 0.0000 | init seed | data draw |
| 2 | 32K/16K | U_P | 2.7080 | 0.0151 | 0.1907 | init seed | data draw |
| 2 | 32K/16K | U_run | 3.1802 | 0.0047 | 0.0105 | init seed | data draw |
| 2 | 32K/4K | U_P | 0.6676 | 0.0496 | 0.2375 | init seed | data draw |
| 2 | 32K/4K | U_run | 1.7457 | 0.0334 | 0.0258 | init seed | init seed |
| 2 | 8K/16K | U_P | 0.8829 | 0.0074 | 0.0131 | init seed | data draw |
| 2 | 8K/16K | U_run | 0.7857 | 0.0000 | 0.0000 | init seed | data draw |
| 2 | 8K/1K | U_P | 0.2916 | 0.0061 | 0.2500 | init seed | data draw |
| 2 | 8K/1K | U_run | 0.8746 | 0.0459 | 0.0617 | init seed | data draw |
| 2 | 8K/4K | U_P | 2.2204 | 0.0639 | 0.2381 | init seed | data draw |
| 2 | 8K/4K | U_run | 2.3024 | 0.0064 | 0.0175 | init seed | data draw |

Corrected: the data draw dominates in 24 of 28 lines and the init seed in 4; the report printed the init seed in 28 of 28. The figures are the auditor's; the lead has not recomputed them independently.
