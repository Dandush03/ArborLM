# P10-I-S0 result (self-checked; not independent review, not Astra validation, not human approval)

**Headline (step 5): OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (NOT SHOWN); ADDRESSING QUALIFIED UP TO 1**

## Lines (MEASURED, from the cell records)

- Line A: L_A = 2.000 (largest load held with every lower load); l1 = 4.000 (FAILS). States by load: 0.5: HOLDS, 1: HOLDS, 2: HOLDS, 4: FAILS.
- Line G: L_G = 1.000 (largest load held with every lower load); l1 = 2.000 (FAILS). States by load: 0.5: HOLDS, 1: HOLDS, 2: FAILS, 4: FAILS.
- Line Q: L_Q = 1.000 (largest load held with every lower load); l1 = 2.000 (FAILS). States by load: 0.5: HOLDS, 1: HOLDS, 2: FAILS, 4: FAILS.

## Section 7 prints at L_Q and at l1 (MEASURED)

- at L_Q, series M (8K/8K): REFERENCE NEAR CEILING; CONVERGENCE CONFIRMED []
- at L_Q, series S (2K/2K): REFERENCE NEAR CEILING; CONVERGENCE CONFIRMED []
- at l1, series M (8K/4K): REFERENCE NEAR CEILING; CONVERGENCE NOT CONFIRMED ['NOT SHOWN']
- at l1, series S (2K/1K): REFERENCE NEAR CEILING; CONVERGENCE NOT CONFIRMED ['NOT SHOWN']
- which line fails at l1, series M: LINE G FAILS (A HOLDS)
- RATIO ABOVE 1 is this study's descriptive tag: the median over evaluated draws of A5-D's mean panel accuracy over A6's exceeds 1; it enters no line (ADR-0023 section 3 says only that the label adds it)

## Series states by load

- load 0.5: series M (8K/16K): A HOLDS, G HOLDS, Q HOLDS (combination 5); series S (2K/4K): A HOLDS, G HOLDS, Q HOLDS (combination 5)
- load 1: series M (8K/8K): A HOLDS, G HOLDS, Q HOLDS (combination 5); series S (2K/2K): A HOLDS, G HOLDS, Q HOLDS (combination 5)
- load 2: series M (8K/4K): A HOLDS, G FAILS, Q FAILS (combination 7); series S (2K/1K): A HOLDS, G HOLDS, Q HOLDS (combination 5) — IN SERIES S ONLY (slots 1024)
- load 4: series M (8K/2K): A FAILS, G NOT READ, Q FAILS (combination 8); series S (2K/512): A HOLDS, G FAILS, Q FAILS (combination 7)

## Cell types: labels and descriptive measures (MEASURED)

- 2K/1K: CONVERGENCE NOT SHOWN IN REHEARSAL | successes 10 of 10 evaluated cells, one-sided 95% per-draw bound 0.741 | class RELIABLE | n_A 0 n_G 0 | A5-D accuracy median 0.993, A6 1.000, ratio 0.993 | REFERENCE NEAR CEILING | convergence CONVERGENCE NOT CONFIRMED ['NOT SHOWN'] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class UNRELIABLE)
- 2K/2K: no label | successes 10 of 10 evaluated cells, one-sided 95% per-draw bound 0.741 | class RELIABLE | n_A 0 n_G 0 | A5-D accuracy median 1.000, A6 1.000, ratio 1.000 | REFERENCE NEAR CEILING | convergence CONVERGENCE CONFIRMED [] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class RELIABLE)
- 2K/4K: no label | successes 10 of 10 evaluated cells, one-sided 95% per-draw bound 0.741 | class RELIABLE | n_A 0 n_G 0 | A5-D accuracy median 1.000, A6 1.000, ratio 1.000 | REFERENCE NEAR CEILING | convergence CONVERGENCE CONFIRMED [] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class RELIABLE)
- 2K/512: CONVERGENCE NOT SHOWN IN REHEARSAL | successes 0 of 10 evaluated cells, one-sided 95% per-draw bound 0.000 | class FAILS | n_A 0 n_G 10 | A5-D accuracy median 0.916, A6 0.961, ratio 0.952 | REFERENCE NEAR CEILING | convergence CONVERGENCE NOT CONFIRMED ['NOT SHOWN'] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class FAILS)
- 8K/16K: A0 takes the cell type's T without a rehearsal of its own | successes 10 of 10 evaluated cells, one-sided 95% per-draw bound 0.741 | class RELIABLE | n_A 0 n_G 0 | A5-D accuracy median 0.999, A6 1.000, ratio 0.999 | REFERENCE NEAR CEILING | convergence CONVERGENCE CONFIRMED [] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class RELIABLE)
- 8K/2K: CONVERGENCE NOT SHOWN IN REHEARSAL; A0 takes the cell type's T without a rehearsal of its own | successes 0 of 10 evaluated cells, one-sided 95% per-draw bound 0.000 | class FAILS | n_A 2 n_G 8 | A5-D accuracy median 0.863, A6 0.951, ratio 0.907 | REFERENCE NEAR CEILING | convergence CONVERGENCE NOT CONFIRMED ['NOT SHOWN'] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class FAILS)
- 8K/4K: CONVERGENCE NOT SHOWN — EXTENSION REFUSED (BUDGET); A0 takes the cell type's T without a rehearsal of its own | successes 2 of 10 evaluated cells, one-sided 95% per-draw bound 0.037 | class FAILS | n_A 0 n_G 8 | A5-D accuracy median 0.981, A6 0.998, ratio 0.983 | REFERENCE NEAR CEILING | convergence CONVERGENCE NOT CONFIRMED ['NOT SHOWN'] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class FAILS)
- 8K/8K: A0 takes the cell type's T without a rehearsal of its own | successes 10 of 10 evaluated cells, one-sided 95% per-draw bound 0.741 | class RELIABLE | n_A 0 n_G 0 | A5-D accuracy median 0.997, A6 1.000, ratio 0.997 | REFERENCE NEAR CEILING | convergence CONVERGENCE CONFIRMED [] | COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset | condition 6 decided 0 cell(s) | 512-exposure readout: P10-S0's regime on new draws; descriptive; not a replication verdict (class RELIABLE)

## Annotations

- penalty against answer-only at 8K/16K: NOT DISTINGUISHED (d = 0, p = 1.0000, 10 pairs used)
- penalty against answer-only at 8K/2K: NOT DISTINGUISHED (d = 0, p = 1.0000, 10 pairs used)
- penalty against answer-only at 8K/4K: NOT DISTINGUISHED (d = -1, p = 1.0000, 10 pairs used)
- penalty against answer-only at 8K/8K: NOT DISTINGUISHED (d = 0, p = 1.0000, 10 pairs used)
- hypotheses (each can fail; a reading is not a success of the science): {'H23-A': 'supported', 'H23-G': 'supported', 'H23-O': 'not supported', 'H23-P': 'not supported'}
- lane licence (loads, tested cell types only): [0.5, 1.0]
- X8: NOT RUN — L_Q BELOW 4 (or the result of steps 0 to 2: step 5)

## False-negative table (ANALYTICAL, not measured; independent cells)

- p = 0.9: RELIABLE in one series 0.736, in both 0.542, Line Q at 0.5, 1 and 2 about 0.16 (ANALYTICAL)
- p = 0.95: RELIABLE in one series 0.914, in both 0.835, Line Q at 0.5, 1 and 2 about 0.58 (ANALYTICAL)
- p = 0.97: RELIABLE in one series 0.965, in both 0.932, Line Q at 0.5, 1 and 2 about 0.81 (ANALYTICAL)
- p = 0.99: RELIABLE in one series 0.996, in both 0.991, Line Q at 0.5, 1 and 2 about 0.97 (ANALYTICAL)

Stage R's public manifests still show each wave's task count and its duration, which show that some cell type decided or that a run went non-finite, but not which.

W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone. A5-D was chosen for P10-S0 after its P9-II result was observed. μ = 1.0 was calibrated at 0.5 facts per slot.
