recompute_p7b.py attempt 1 (kept as recompute_p7b.attempt1.py / recompute_attempt1.json): 6103 values compared,
18 differences. All 18 were my comparison mistakes, not study defects:
 - 16 x BC_K five-partition counterpart: I compared my mean-of-per-checkpoint-ratios mean(m_P/m_COAX) against
   analysis.json's value, which is the ratio of means mean(m_P)/mean(m_COAX). My ratio of means matches exactly.
   Both definitions are now reported; the ADR text "mean m_P / m_tree(L-COAX)" admits either reading.
 - 2 x robustness grid R8C8 HB class (fixed tree, streams A and B): I compared my ascending-only class against
   the grid entry, which at the two criterion settings reports the class combined over both tie rules
   (TIE-RULE DEPENDENT). My combined class agrees.
Command: .venv/bin/python -I docs/reviews/p7b-results-audit-2026-11-13/recompute_p7b.py --repo . --out <scratchpad>/try1.json
