# Gate review 3 of ADR-0033 (revision 3, commit `2082cdd`)

Reviewer: `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-20. Claude review is not Astra review; not human approval; not validation. `Astra review: NOT_PERFORMED`. Nothing here is a result.

Read: ADR-0033 at `2082cdd` (SHA-256 `e3f1ac9a…7a59`), sections 0 to 9.4, 13, 14, 16, 17 and 20 checked against REVIEW2. Ran (Python 3.15.1, `/opt/homebrew/bin/python3 -I`, standard library only, about 25 s CPU each, `timeout 500 nice -n 19`), all in `experiments/_scratch/audits/adr0033_review/`, outputs verbatim beside each:
- `shrink_check3.py` (`475e1f17…e058`) → `shrink_check3.out.txt`: §9.4 **as written**, plus a pooled-residual variant.
- `shrink_check3b.py` (`0d4d43e1…2c63`) → `shrink_check3b.out.txt`: adds per-cluster λ_g and the harmonic noise term (kept: an intermediate attempt that still fails on unbalanced clusters).
- `shrink_check3c.py` (`3f52fe93…8a3e`) → `shrink_check3c.out.txt`: the corrected wording of P1 below.

Design of the check: a known truth (G = 300 clusters, cluster effects N(0, τ), items in {+1, −1, 0} with discordance d); "known power" = the M5 test (cluster-robust SE, t quantile) on fresh clusters and items, 2,000 runs; the §9.4 procedure applied to one M0 draw, 6 independent M0 draws × 600 simulations; n = 6,000, δ chosen for mid-range power so that bias is visible.

## Gate answer

**Yes, after one listed edit (P1, BLOCKING; again an error in my own wording).** Everything else is closed. With P1 applied, the lead may approve the specification as a specification and take Decision 1 limited to I0-a and a rehearsal of G-gen at the proposed numbers. Section 17 holds the right things.

## 1. N1 to N9

| | Closed as worded? |
|---|---|
| N1 | **Yes as worded, but my wording still fails the check: P1** |
| N2 | Yes (20,418 and 23,125; the product-rule figure labelled) |
| N3 | Yes (left padding, 8 long prompts to 1,024, decoder check) |
| N4 | Yes (§6.2 and G-load's Needs) |
| N5 | Yes (box; I0-a; numpy row) |
| N6 | Yes (§17, choice 12 → F) |
| N7 | Yes (lineages; G = every lineage written; table; worst-case τ his; strata option is choice 19, his only) |
| N8 | Yes (§4.2) |
| N9 | Yes (both recommendations shown; neither chosen) |

### The shrinkage simulation: numbers

| Scenario (G = 300) | True τ | Mean τ̂ (range over 6 M0 draws) | Known power | §9.4 as written | Corrected (P1) |
|---|---|---|---|---|---|
| S1 balanced, 5 per cluster, d = 0.3 | 0.05 | 0.038 (0–0.090) | 0.825 | 0.878 [0.800–0.933] | 0.829 [0.707–0.903] |
| S2 balanced, 5 per cluster, d = 0.3 | 0 | 0.007 (0–0.041) | 0.811 | 0.868 [0.852–0.882] | 0.816 [0.792–0.847] |
| S3 unbalanced (1 to 16 per cluster), d = 0.3 | 0.05 | as written 0.253; corrected 0.043 | 0.825 | 0.356 [0.115–0.985] | 0.812 [0.577–0.903] |
| S4 s_w near 0 (d = 0.02) | 0.01 | 0.009 | 0.674 | 0.746 [0.570–0.858] | 0.661 [0.488–0.785] |
| S5 s_w near 0.5 (d = 0.5) | 0.05 | 0.073 | 0.813 | 0.829 [0.688–0.928] | 0.798 [0.707–0.883] |
| S6 unbalanced, d = 0.3 | 0 | as written 0.248; corrected 0.033 | 0.811 | 0.328 [0.053–0.970] | 0.793 [0.727–0.832] |

MC standard error of the known power ≈ 0.009. The bracketed spread over M0 draws is the real imprecision of τ̂ from about 5 items per cluster (choice 18), not a defect.

Three defects in the text as written, all from my N1 wording:
1. **Within-cluster items drawn from the cluster's own 5 items** have the plug-in variance, (m − 1)/m of the true one: power overstated by about 0.05 to 0.07 (S1, S2, S4). Anti-conservative.
2. **The noise term s_w²/m̄ with the arithmetic mean m̄** is wrong when clusters are unbalanced (public parts: passages; private parts after exclusions): E[var of cluster means] = τ² + s_w²·mean(1/m_g). τ̂ came out 0.25 against a true 0.05 or 0.
3. **"In each sample, the mean difference is recentred to zero"** is ambiguous. Read literally it makes every estimate zero and every test pass. Recentring on the item-weighted mean, as I implemented it, leaves a shift of order 0.02 when clusters are unbalanced, so power swung from 0.1 to 1.0 (S3, S6). The population must be recentred on the cluster-level mean.

## P1. BLOCKING. Replace in §9.4, from "Each is drawn in two stages within strata." to "… are then scaled by √(d_e / (d_e − μ²))." with:

> Each is drawn in two stages within strata. First, G_e clusters are drawn with replacement from the M0 draw's clusters, allocated to strata as the sealed split will be. A drawn cluster g contributes its shrunk deviation λ_g·(x̄_g − x̄_h), where x̄_h is the unweighted mean of the cluster means of its stratum h, λ_g = √(τ̂² / (τ̂² + s_w²/m_g)), and τ̂² = max(0, V_h − s_w²·mean(1/m_g)), V_h being the variance of the cluster means within strata, s_w² the pooled within-cluster variance and m_g the number of M0-draw items in cluster g. This makes the simulated population's mean difference exactly zero and its between-cluster variance τ̂². Second, n/G_e item deviations per cluster are drawn with replacement from the stratum's pooled within-cluster residuals, each residual (x − x̄_g) multiplied by √(m_g/(m_g − 1)); clusters with one item contribute no residual. They are added to the cluster's shrunk deviation. The sample's own mean is never subtracted. The sample's mean difference and its cluster-robust standard error over the G_e drawn clusters are then scaled by √(d_e / (d_e − μ²)).

In the "Floor from the clusters" bullet, replace "(method of moments, registered formula)" with "(the τ̂² of the simulation bullet, square-rooted)". A test in I0-a must reproduce the known-truth check of review 3 (scenarios S1, S3 and S6) within MC error.

## 2. The drafter's four "did not fit" notes

| Note | Ruling |
|---|---|
| numpy row reworded ("Not used by the analysis, which runs on the locked environment") | Acceptable; it agrees with I0-a |
| New seed 400013 (scorer hand-label sample) | Acceptable. It lies inside the requested block; revision 6 of the registry must list it |
| Ladder top stays at 20,000 until he decides | Acceptable. The ladder must equal the pool, and the pool is his (choice 10); §8 says the ladder rises with it |
| Older G limits kept beside the table | Acceptable. Rechecked with Boole (z ≈ 4.33): 75, 208, 469 and 117 against the text's 75, 210, 470 and 120. They agree with the table's limits at infinite n |

## 3. Own errors, kept

- Review 2's N1 wording had three defects (above). Review 2's own check (`power_check2.py`, section C) tested only the between-cluster variance on balanced clusters, so it missed all three.
- `shrink_check3b.py` was an intermediate fix that still failed on unbalanced clusters (S3 power 0.551, S6 0.423). It is kept.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
