# P10-I-S6 report (registered)

> Self-check output. Not independent review, not Astra validation, not human approval. A label here is a registered outcome only after the auditor's independent recomputation.

## Line P (registered): CONVERGENCE NOT REACHED (BOTH STILL IMPROVING) [LEAD SHRINKING (Δ = -0.0056; 0.0124, 0.0131, 0.0137, 0.0119, 0.0068); over 16,384 to U_max updates only; descriptive; this says nothing about the ordering at convergence and is not the label PERSISTS.]

- row 12; reading rung R = 4 (K* = None), k_max = 4; dependence-qualified: False

## Trend line (descriptive; never a label): LEAD SHRINKING (Δ = -0.0056; 0.0124, 0.0131, 0.0137, 0.0119, 0.0068); over 16,384 to U_max updates only; descriptive; this says nothing about the ordering at convergence and is not the label PERSISTS.

- |mean Q(k_max)| = 0.0068; δ(M-FLAT, k_max) = 0.0122; δ(D-ADAPT, k_max) = 0.0173. an arm is still improving per doubling by at least the size of the lead

## D[FLAT] at R: DEPENDENT
- failing: []; collapsed cells: []; cells with H_used > B: 27; mean B - H_vmean: -0.0030

## Per rung

| k | updates | rate F | rate D | L(F) | L(D) | delta F | delta D | deltarun F | deltarun D | conv F | conv D | mean Q | class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 16384 | 0.03 | 0.01 | 2.2122 | 2.2245 | 0.0194 | 0.0208 | 0.0202 | 0.0208 | NOT CONVERGED | NOT CONVERGED | 0.0124 | UNDECIDED |
| 1 | 32768 | 0.1 | 0.01 | 2.1925 | 2.2056 | 0.0197 | 0.0189 | 0.0201 | 0.0189 | NOT CONVERGED | NOT CONVERGED | 0.0131 | UNDECIDED |
| 2 | 65536 | 0.03 | 0.01 | 2.1742 | 2.1879 | 0.0183 | 0.0177 | 0.0182 | 0.0177 | NOT CONVERGED | NOT CONVERGED | 0.0137 | UNDECIDED |
| 3 | 131072 | 0.1 | 0.01 | 2.1576 | 2.1695 | 0.0166 | 0.0184 | 0.0159 | 0.0184 | NOT CONVERGED | NOT CONVERGED | 0.0119 | UNDECIDED |
| 4 | 262144 | 0.003 | 0.01 | 2.1454 | 2.1522 | 0.0122 | 0.0173 | 0.0121 | 0.0173 | NOT CONVERGED | NOT CONVERGED | 0.0068 | M-AHEAD |

## X_mean_dense per rung (descriptive: the adapter's delta replaced by its batch mean; X_mean_dense = H_xmd - A)

- rung 0: mean 0.2321 (min 0.0899, max 0.5315, cells above 0: 27)
- rung 1: mean 0.3434 (min 0.1063, max 0.8817, cells above 0: 27)
- rung 2: mean 0.4937 (min 0.1257, max 1.1253, cells above 0: 27)
- rung 3: mean 0.6340 (min 0.1581, max 1.3695, cells above 0: 27)
- rung 4: mean 0.7791 (min 0.2186, max 1.4823, cells above 0: 27)

## Harm figures per rung (strict '>')

- rung 0: B-H_used -0.1113 (27 cells worse than BASE); B-H_mean -0.0011 (15); B-H_vmean -0.0008 (14)
- rung 1: B-H_used -0.1366 (27 cells worse than BASE); B-H_mean -0.0028 (17); B-H_vmean -0.0024 (17)
- rung 2: B-H_used -0.1701 (27 cells worse than BASE); B-H_mean -0.0027 (16); B-H_vmean -0.0023 (16)
- rung 3: B-H_used -0.2103 (27 cells worse than BASE); B-H_mean -0.0060 (19); B-H_vmean -0.0054 (18)
- rung 4: B-H_used -0.2266 (27 cells worse than BASE); B-H_mean -0.0036 (17); B-H_vmean -0.0030 (17)

## R16: REPLICATED AT 16,384; OA: REPLICATED AT 16,384 (OA rates were calibrated on the new calibration parents; no label changes)

## Limits

Converged means converged by the rule of section 9 at a constant rate chosen per duration; nothing about cost, efficiency, the tree, SSD or other corpora; no p-value.
