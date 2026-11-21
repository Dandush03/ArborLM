# P10-I-S3 (ADR-0026) — independent recomputation of the registered run

**Verdict: REPRODUCED WITH CORRECTIONS.** Every number and every label in `analysis/analysis.json` was reproduced from the raw item records. The largest absolute difference over 921 compared quantities is 0.0, and no label differs. Several corrections and disclosures are still needed: none changes a registered label, but they change what the record may say. One question, the scope of the integrity check, is marked PENDING LEAD REVIEW.

- Auditor: the `arbor-auditor` subagent, model Claude Opus 5.5 (model ID `claude-opus-5-5`, as stated in this session's system context). This audit is independent engineering and mathematical evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- ArborLM is unproven research. Nothing here is a success claim.
- Date: 2026-11-18. Platform: macOS 27.2.1 arm64. `uv run --locked python` gave Python 3.12.14 and torch 2.8.0; the lock has no numpy.
- Inputs, all read-only:
  - Frozen worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a8a655df6017ce8d1`, HEAD 936c4fc. The only change from freeze 2e98578 is `results/p10i-s3-freeze-2026-11-18/DECISION_2.md` (`git diff --stat`).
  - Run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS3-registered-20261118`.
  - `rehearsal_public.json` from `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS3-rehearsal-20261118`.
  - Nothing else under `ArborLM-sealed/` was opened apart from my own scratch folder.
- Code: the scripts are my own and are in the appendix. They import nothing from `studies/p10i_s3` or `arborlm`. `recompute.py`, `compare.py` and `margins.py` use the standard library only. `snapshots_check.py` uses torch only to read the registered checkpoints (identity, hashes and keys). No evaluation, no training and no data were run.
- Commands, all from the worktree root `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, with `S=/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s3-recompute`, `W=…/agent-a8a655df6017ce8d1` and `R=…/P10IS3-registered-20261118`:
  - `timeout 600 uv run --locked python -I $S/recompute.py $W $R $S/mine.json`
  - `timeout 300 uv run --locked python -I $S/compare.py $S/mine.json $R/analysis/analysis.json $S/rows.json`
  - `timeout 120 uv run --locked python -I $S/margins.py $S/mine.json`
  - `timeout 590 uv run --locked python -I $S/snapshots_check.py $W $R`

## 1. Quantity table (registered → recomputed)

Unless a row says otherwise, values are FRESH at U\* = 16,384, from the primary-rate run.

| Quantity | Registered | Recomputed | Max abs diff (all regimes, all cells) |
|---|---|---|---|
| Line 1: mean C (D1) | 0.12866462235925374 | 0.12866462235925374 | 0.0 |
| Line 1: mean P_used (D2; four draws averaged, then H subtracted) | 0.27879050660326526 | same | 0.0 |
| Line 1: mean X_mean (D3) | 0.13286276996411658 | same | 0.0 |
| D1/D2/D3 cell and parent counts | 27, 9 for each | 27, 9 for each | 0 |
| Line 2 [TREE]: mean Q (Q = A − H) | −0.0008112259761050895 | same | 0.0 (Q = A − H and Q = C − C_dense are bitwise equal in every cell) |
| K1 [TREE] cells, parents | 22, 7 | 22, 7 | 0 |
| K2 [TREE]: mean C, mean C_dense | 0.128665, 0.129476 | same | 0.0 |
| K3 [TREE] cells, parents | 11, 3 | 11, 3 | 0 |
| Line 2 [FLAT]: mean Q | 0.012658601695740665 | same | 0.0 |
| K1 / K3 [FLAT] cells, parents | 27, 9 for each | 27, 9 for each | 0 |
| Convergence δ, FRESH: M-TREE / M-FLAT / D-ADAPT | 0.018102877 / 0.020784389 / 0.017224793 | same | 0.0 |
| Convergence δ, REP: M-TREE / M-FLAT / D-ADAPT | 0.000266446 / −0.001465062 / 0.009879422 | same | 0.0 |
| Convergence δ, REP-U: M-TREE / D-ADAPT | 0.002348520 / 0.010735239 | same | 0.0 |
| Mean curves (every arm, regime and checkpoint) | — | — | 0.0 |
| PAST BEST flags (REP, REP-U) | all false | all false | — |
| Integrity lists | REP: `c12/u16384/r0.01` joint; REP-U: `c21/u512/r0.03` joint | identical under the same (wide) reading | — |
| Contrasts of §3.3 (C, C_dense, Q, P_used, X_mean at 512 and U\*, three regimes) | — | — | 0.0 |
| Routing G_train, G_read, G_prior (per cell, four checkpoints, REP and FRESH), primary-rate G_train, ΔG and its sign counts | — | — | 0.0 |
| Six-parent readout (means and counts, three regimes) | — | — | 0.0 |
| P4-rate anchor: M-TREE REP mean C at 0.003 | 0.09121273899519886 | same | 0.0 |
| M-FLAT descriptive D1–D3 means | — | — | 0.0 |
| used_slots per cell at U\* | — | — | 0 (the minimum in FRESH is 753, so no cell is COLLAPSED) |
| Ledger total (charged seconds) | 656.6 + 21,904.3 + 1,503.4 | 24,064.29 s = 6.6845 h; cap 36,631.48 s = 10.1754 h (65.7 % used) | — |

The bit-exact agreement is plausible. B, A and H are within a factor of two of each other, so every subtraction is exact (Sterbenz). Means over 27 values of similar size round the same way with naive summation and with `fsum`.

## 2. Label table

| Line / regime | Registered | Recomputed (registered integrity reading) | Recomputed (integrity checked only on the evaluations the label reads) |
|---|---|---|---|
| Line 1 FRESH (registered label) | DEPENDENT (M-TREE NOT CONVERGED) [RATE-AT-EDGE] | same | same |
| Line 2 [TREE] FRESH (registered label) | INCONCLUSIVE (MEMORY RATE AT EDGE) (MEMORY STILL IMPROVING); base label NOT COMPETITIVE | same | same |
| Line 2 [FLAT] FRESH | MEMORY AHEAD (DENSE STILL IMPROVING) | same | same |
| Registered positive | line 1 True, line 2 False | same | same |
| Route A | A1 label qualifies True, A1 False after open choice 13; A2 False; D-ADAPT FRESH NOT CONVERGED | same | same |
| Line 1 REP-U | NOT EVALUABLE | same | **DEPENDENT (M-TREE NOT CONVERGED)** |
| Line 2 [TREE] REP-U | NOT EVALUABLE | same | **NOT COMPETITIVE (MEMORY STILL IMPROVING)** |
| Line 1 REP | NOT EVALUABLE | same | NOT EVALUABLE (the failing cell is the primary run at U\*) |
| Line 2 [TREE] REP | NOT EVALUABLE | same | NOT EVALUABLE |
| Line 2 [FLAT] REP | NOT COMPETITIVE | same | same |
| Convergence tags | FRESH: all NOT CONVERGED. REP: M-TREE CONVERGED, M-FLAT CONVERGED, D-ADAPT NOT CONVERGED. REP-U: both NOT CONVERGED | same | — |
| Routing | FRESH: G_train 512 WITHIN, 2048/8192/U\* TREE BEHIND; G_read WITHIN at all four. REP: G_train WITHIN / TREE BEHIND / WITHIN / TREE AHEAD; G_read WITHIN ×3, then RESTRICTION HELPS at U\*. Trends: FRESH G_train changes, G_read no change; REP both change | same | — |

## 3. Completeness and identity (task 2)

All checks pass. My checker recorded 0 problems.

- **Plan file.** SHA-256 `2c02a0268bdbcb7e9dba588f8adf93a7e73d61a0e138d0b939d2692aa358cf8b`. It equals `rehearsal_public.json` → `candidate.plan_file_sha256` and the freeze record. `freeze/rate_table.json` (sha `6d4c8771…`) equals the plan's rate table and `rehearsal_public.json`'s rate table.
- **Items.** The plan has 621 train and 1,755 eval items with no duplicate IDs. `items/` holds exactly 2,376 directories, one per planned ID, and nothing extra.
  - Every train record has status `ok`, `failed_at_update` null, `updates_done` equal to the plan's `max_update`, and the snapshot set equal to the plan's.
  - Trainable parameters are 198,401 for M-TREE, 198,145 for M-FLAT and 198,401 for D-ADAPT.
  - Every eval record's ID, update and controls match its plan item, and each has exactly the read set of its arm and controls: 16 reads for M-TREE, 13 for M-FLAT, 8 for D-ADAPT; enabled and disabled at step 0; enabled, replay and disabled for `enabled` controls.
  - No value is non-finite. No `item_error` exists anywhere.
- **Seeds and rates.** In every plan item, init seed = 330301 + c mod 3, stream seed = 260001 + 3c + g, and parent = c div 3. Every rate equals the frozen table: the primary rate for U\*, a per-duration rate that differs from the primary, or the anchor at 0.003 (M-TREE REP only, because D-ADAPT's REP rate is already 0.003).
- **Snapshots.** I hashed all 1,755 snapshot files. Every file SHA equals the train record's SHA, and every `index.json` step is right. The identity stored in each run's last snapshot (arm, regime, rate, cell, parent, init seed, stream seed, profile) equals the plan in 621 of 621 runs, and so does the optimizer's `lr`.
- **Panel and integrity identities.** `disabled|0` equals BASE bitwise in 1,755 of 1,755 eval records, where BASE is the value from `gates/results/core.json` and is itself bitwise equal to its replay on all nine parents. `replay|0` equals `enabled|0` bitwise in every record that has a replay. The records do not name the panel; the bitwise disabled = BASE identity is the evidence that every evaluation ran on the registered panel. The control seeds (P_all, P_used, X, joint) are not in the records and can only be checked through the code (ADVISORY F12).
- **Manifests.** gates, train and eval are all COMPLETE, mode `registered`, identity commit 2e98578. Each has one history entry (no resume), and every task is `completed`. No item was computed twice: one record per ID, and `write_record` refuses to overwrite.
- **Ledger.** Gates 656.6 s, train 21,904.3 s, eval 1,503.4 s. Total 24,064.3 s = 6.68 h against a cap of 10.18 h. Decision 2 projected 5.09 h; the run charged 1.31 times the projection.

## 4. Findings

**F1 — REQUIRED CORRECTION (disclosure; scope is PENDING LEAD REVIEW). REP-U is NOT EVALUABLE only under the implementer's reading of "on any cell".**
- The failing REP-U evaluation is `M-TREE|REP-U|c21|u512|r0.03`, joint deviation 3.33e-6. It is a per-duration run at a descriptive checkpoint, and no rule of §§6.2–6.5 reads it. The primary REP-U run (rate 0.003) has a deviation of exactly 0 at U\* in all 27 cells.
- ADR §10 says "joint permutation outside 1e-6 on any cell … the affected arm and regime is NOT EVALUABLE". It names no checkpoint and no run. The code's docstring (`analysis.py:151-152`) calls its widest reading a "ruling": every checkpoint, the per-duration runs and the primary run. I found no recorded ruling in the frozen tree outside that docstring.
- If the check is limited to the evaluations the labels read, REP-U line 1 = DEPENDENT (M-TREE NOT CONVERGED) and line 2 [TREE] = NOT COMPETITIVE (MEMORY STILL IMPROVING).
- These are regime labels. They never decide a line (§6.5), so no registered label changes. The outcome record must still say that the REP-U NOT EVALUABLE comes from a descriptive checkpoint, under a reading the implementer chose.

**F2 — REQUIRED CORRECTION (disclosure; the specification question is PENDING LEAD REVIEW). The joint-permutation check is not an exact invariance; the two failures are most consistent with tie-breaking, not with float accumulation noise or a mis-paired key and value.**
- **Tolerance.** 1e-6 is the ADR's own number (§3.4: "NLL must match the enabled reference within 1e-6"; §10; config `tolerance_joint = 1e-6`, frozen). The code compares |joint − enabled| > 1e-6.
- **Measured.** There are 324 M-TREE evaluations with a joint read. 317 are bitwise equal to the enabled read. The 7 that differ are all in REP or REP-U, with both signs:

  | Regime, cell, checkpoint, rate | Deviation |
  |---|---|
  | REP-U c21 u512 r0.03 | +3.33e-6 |
  | REP c12 u16384 r0.01 (primary) | −1.80e-6 |
  | REP c15 u2048 r0.03 | −8.46e-7 |
  | REP-U c15 u8192 r0.03 | +3.43e-7 |
  | REP c8 u16384 r0.01 (primary) | −2.64e-7 |
  | REP-U c13 u512 r0.03 | −1.71e-7 |
  | REP-U c11 u512 r0.03 | +3.4e-8 |

- **FRESH.** All 108 FRESH joint reads (27 primary at U\* and 81 at the other checkpoints) deviate by exactly 0.0. The FRESH labels do not stand on a near miss of this check.
- **Cause, from reading the code (`pilot_model.tree_candidates` and `stable_top`).**
  - Keys and values are permuted together within each branch, and the router is not permuted, so the candidate set and every per-candidate score are bitwise unchanged.
  - The 8 selected values are summed in score order, which is also unchanged.
  - The one place the permutation can matter is a row with an exact float32 score tie among the top 9 candidates. There `stable_top` falls back to a stable argsort with the slot ID as the secondary key, and the permutation changes which (key, value) pair holds the lower ID.
  - The pattern fits this mechanism: zero almost everywhere, rare discrete jumps of either sign. It does not fit accumulation-order noise, which would make most deviations non-zero.
  - Magnitude: 3.33e-6 × 32,768 ≈ 0.109 nats in total. That is a changed selection at one or a few positions, not reordering at the level of an ulp.
  - A static check found no duplicate key rows, raw or normalised, within any branch in the seven failing checkpoints or in five controls (minimum normalised-key distance ≥ 4.3e-3). So the ties are coincidental float32 ties, not structural duplicates.
- **Limits.** This is inference from code and records. I did not re-evaluate any checkpoint on the panel; a tie-logging re-evaluation would be a new computation on registered data and needs the lead's authorization (PENDING LEAD REVIEW).
- **Is the regime rule the ADR's?** Yes. §10, §6.2 row 1, §6.3 row 1 and ruling 11 make the whole arm-regime NOT EVALUABLE on one cell. For REP the failing evaluation (`c12/u16384/r0.01`) is the one the label reads, so REP NOT EVALUABLE follows the ADR text exactly. Thresholds are not changed after observation (§5.3), and the labels stand as computed.
- **What the record must say.** The check as specified can fail on a correctly paired tree read when float32 scores tie. The REP and REP-U NOT EVALUABLE labels are integrity labels, not scientific ones. Without the check, D1–D3 hold in REP with large margins (mean C 0.0922, mean P_used 0.336, mean X_mean 0.0938, 27/27 cells). That is a descriptive figure, not a label.

**F3 — REQUIRED CORRECTION. The report omits the rehearsal convergence tags where they differ from the registered ones (ADR §5.2, last bullet: "both are printed").**
- M-TREE REP: rehearsal NOT CONVERGED (δ 0.001234), registered CONVERGED (δ 0.000266).
- M-FLAT REP: rehearsal NOT CONVERGED (δ 0.004522), registered CONVERGED (δ −0.001465).
- `report.md` and `analysis.json` print only the registered tags. No label changes, since the registered tag is the one used.

**F4 — REQUIRED CORRECTION (disclosure of margins). The registered line-2 [TREE] label is one parent mean away from COMPETITIVE.**
- The base label is NOT COMPETITIVE only because K1's parent count is 7 of 9, and 8 are needed.
- The deciding parent is parent 0 (B101/O301, a calibration parent), at −0.00568 against −0.005: a margin of 0.00068. The within-parent SD of Q is 0.00215, so the SE of a 3-cell mean is about 0.00124. A move smaller than one SE would pass K1.
- The K1 cell count is exactly at its threshold (22 of 22 needed). The next cell up sits at −0.0043, 0.0007 inside the line, and the 5th-lowest at −0.00606.
- K2 passes: mean C − 0.9 × mean C_dense = +0.0121. K3 fails clearly: mean Q −0.0008 against +0.005.
- If K1 had passed, the label would be COMPETITIVE (D-ADAPT's edge flag is false) and "registered positive line 2" would be True. A2 would still be False under open choice 13, because D-ADAPT FRESH δ = 0.0172, 17 times ε. The Route A outcome is robust; the line-2 label is not.
- `report.md` prints no K1, K2 or K3 figure. The outcome record must give them.

**F5 — REQUIRED CORRECTION. D2 passes largely through harm beyond the loss of the gain, and the report does not print B − H_used or B − H_mean (ADR §3.4 requires both, with counts).**
- FRESH: H_used > B in 27 of 27 cells, and mean B − H_used = −0.1501. Value reassignment makes the model worse than the frozen backbone by more than the gain (mean C 0.1287). The minimum per-cell P_used/C is 1.70.
- FRESH D3: H_mean > B in 19 of 27 cells, mean B − H_mean = −0.0042, minimum X_mean/C 0.980. The batch-mean read returns the model to roughly the baseline.
- The ADR anticipated both effects. The figures are in `analysis.json → descriptive` but not in `report.md`.
- DEPENDENT licenses only the two sentences of ADR §1, line 1. The outcome record should give these figures beside it.

**F6 — REQUIRED CORRECTION (minor). Step-0 losses are not printed (ADR §6.2: "Step-0 losses are printed").**
- Neither `report.md` nor `analysis.json` carries them. The code reads them only inside PAST BEST.
- Recomputed step-0 mean enabled NLL (identical in every regime): M-TREE 2.3516840399, M-FLAT 2.3516838491, D-ADAPT 2.3516919788. Mean B is 2.3516840475.

**F7 — ADVISORY. The FRESH G_train trend label rests on a 0.00012 margin.**
- FRESH G_train at 512 is +0.004881, 24 of 27 cells positive, labelled WITHIN RESOLUTION. At +0.005 it would read TREE BEHIND, and the trend would become NO CHANGE AT THIS RESOLUTION.
- REP's 512 value (+0.004898) is similarly close to its threshold, but REP's trend holds either way because U\* reads TREE AHEAD.
- The report prints ΔG (+0.008589; 26 cells positive, 1 negative) as §6.6 requires. The outcome record should state the margin. This section is descriptive.

**F8 — ADVISORY. The REP routing rows, the REP and REP-U six-parent readouts and the §3.3 contrasts use M-TREE values from arm-regimes that §10 makes NOT EVALUABLE.** The ADR does not forbid descriptive figures there, but the report should flag them.

**F9 — ADVISORY. Report presentation.**
- The routing rows are in string order (16384, 2048, 512, 8192).
- The heading "Registered positive: line 1 True" is the ADR's own term (§6.5). It is not followed by the §1 limit ("Nothing beyond these two statements") or by "no outcome is a success claim" in the same place.

**F10 — ADVISORY. Missing stage records.**
- No load average is recorded at the start of each stage, which ADR §8 requires. The manifests carry none.
- There is no `NOTES.md` in the run directory.
- Since the run shared the machine (Decision 2, item 5), the record of sharing rests on Decision 2's text alone.

**F11 — ADVISORY. Decision 2's hash statement does not match the file now present.**
- Decision 2, item 3, says the counting-rehearsal folder holds "byte-identical copies of R1's `rehearsal_public.json` (sha256 753a0c66…)".
- The file there now has SHA `d902be55049f13d4f5af9d22c4ed676ffd1c8da9f1b6913a7cf154cf446ba21e`, and that is the hash the freeze record names. R3 probably rewrote the file when it added the `candidate` block.
- This does not affect the run, but Decision 2's sentence is inaccurate as written.

**F12 — ADVISORY. The records do not identify the panel or the control seeds.** Panel identity is inferred from disabled = BASE, bitwise, in all 1,755 records. The P_all, P_used, X and joint seeds can be checked only by reading `core.Seeds`, not from records.

**F13 — ADVISORY. What MEMORY AHEAD [FLAT] licenses.**
- Its margins are robust:
  - mean Q 0.01266 against 0.005 (margin 0.0077);
  - Q > 0 in 27 of 27 cells (the 6th-lowest cell is +0.0063);
  - every parent mean > 0 (the smallest is +0.00436);
  - K2 margin +0.0256.
- Both arms are NOT CONVERGED. M-FLAT's δ (0.0208) and D-ADAPT's δ (0.0172) each exceed the flat memory's lead of 0.0127.
- Under ADR §6.3 and §12 the sub-label never qualifies anything, and a flat result points to P10-I-R, not to S4.
- It is consistent with FRESH G_train at U\*: TREE BEHIND, +0.0135, 27 of 27 cells. Note that the tree runs at 0.3, the edge of the grid, while the flat memory runs at 0.01.

**F14 — ADVISORY. COLLAPSED handling is a moot ambiguity.**
- The code turns one COLLAPSED cell into a failure of the whole D2 condition, because its P_used becomes None and the mean becomes undefined.
- The ADR says only that such a cell "fails D2". My script fails the cell only.
- No cell is COLLAPSED (the minimum `used_slots` is 753 in FRESH), so the difference has no effect here.

**What DEPENDENT, NOT CONVERGED and RATE-AT-EDGE together mean (task 4).**
- Under §6.2, RATE-AT-EDGE and NOT CONVERGED are printed beside line 1 and change no label.
- Under §§1 and 12, DEPENDENT means only this: at 16,384 updates, on FRESH, for M-TREE at rate 0.3 (the edge of the twice-extended grid), at least half the gain is lost under used-slot value reassignment, and at least half is lost under the batch-mean read.
- It says nothing about convergence, about a better rate or a better constant, or about storage of facts.
- "Registered positive: line 1 True" is §6.5's wording. It licenses only that A1's label qualifies. Under open choice 13, A1 does not qualify.

## 5. Margins table (thresholds that decided a registered or FRESH label)

| Label element | Value | Threshold | Margin | Within cell-to-cell spread? |
|---|---|---|---|---|
| D1 mean C (FRESH) | 0.12866 | ≥ 0.005 | +0.1237 | no |
| D1 cells / parents | 27 / 9 | ≥ 22 / ≥ 8 | +5 / +1 | no |
| D2 mean P_used | 0.27879 | ≥ 0.005 | +0.2738 | no |
| D2 per-cell min P_used/C | 1.698 | ≥ 0.5 | +1.198 | no |
| D3 mean X_mean | 0.13286 | ≥ 0.005 | +0.1279 | no |
| D3 per-cell min X_mean/C | 0.980 | ≥ 0.5 | +0.480 | no |
| K1 [TREE] mean Q | −0.00081 | ≥ −0.005 | +0.0042 | no |
| **K1 [TREE] cells** | **22** | **≥ 22** | **0 (next cell up at −0.0043)** | **yes** |
| **K1 [TREE] parents** | **7** | **≥ 8** | **−1; parent 0 at −0.00568, 0.00068 short (SE of a 3-cell mean ≈ 0.0012)** | **yes; it decides the label** |
| K2 [TREE] | 0.12866 vs 0.9 × 0.12948 | ≥ | +0.0121 | no |
| K3 [TREE] mean Q | −0.00081 | ≥ +0.005 | −0.0058 | no |
| K3 [FLAT] mean Q | 0.01266 | ≥ +0.005 | +0.0077 | no |
| K3 [FLAT] cells / parents | 27 / 9 | ≥ 22 / ≥ 8 | +5 / +1 (minimum parent mean +0.0044) | no |
| Losing arm [TREE] (mean H_mem − mean H_dense) | +0.00081 | > 0 | +0.0008 | yes (only appends the STILL IMPROVING tag) |
| δ FRESH M-TREE / M-FLAT / D-ADAPT | 0.0181 / 0.0208 / 0.0172 | NOT CONVERGED if ≥ 0.001 | +0.017 / +0.020 / +0.016 | no |
| δ REP M-TREE (registered CONVERGED) | 0.000266 | < 0.001 | 0.00073 | the rehearsal said NOT CONVERGED |
| δ REP-U M-TREE | 0.00235 | ≥ 0.001 | +0.00135 | — |
| Joint check, REP c12 at U\* (primary) | 1.80e-6 | ≤ 1e-6 | −8.0e-7 | — |
| Joint check, REP-U c21 u512 (per-duration run) | 3.33e-6 | ≤ 1e-6 | −2.3e-6 | — |
| FRESH G_train at 512 (descriptive) | +0.004881 | ≥ +0.005 | −0.00012 | yes (it decides the trend) |

## 6. To disclose first in the outcome record

1. Open choice 1. The fixed duration departs from the direction's "convergence-based duration". It was taken by the lead under the delegation, against the third reviewer's advice that it go to the human lead.
2. The calibration found every arm NOT CONVERGED at 16,384, and that is public in Decision 2. The registered run confirms it in FRESH for all three arms (δ is 17 to 21 times ε). REP-U's two arms are also NOT CONVERGED, and so is REP's D-ADAPT.
3. M-TREE's FRESH rate, 0.3, is at the edge of the grid after two extensions. Line 2 [TREE] is INCONCLUSIVE for that reason, on top of a K1 failure by one parent at a 0.00068 margin (F4).
4. Route A is closed by open choice 13 whatever line 2 shows. A1 is False only because of that ruling.
5. The machine was shared with P10-I-S1's calibration (6 workers) and with subagents. Training and evaluation are deterministic, and the bitwise identities hold in all 1,755 records. The run charged 6.68 h against a projection of 5.09 h and a cap of 10.18 h. No load average was recorded (F10).
6. REP and REP-U are NOT EVALUABLE through the joint-permutation check. In REP-U this rests on a descriptive checkpoint and on the implementer's scope reading (F1). The check itself is not tie-invariant (F2).
7. F3, F5 and F6 must be added to the record.

## 7. Discrepancies of my own (kept)

- **Draft error in D2, fixed before any run.** My first draft of `recompute.py` made D2 fail as a whole if any cell was COLLAPSED (`and not any(collapsed)`). That is the implementer's reading, not mine, so I removed it with `sed` before the first run. It has no effect, since no cell is COLLAPSED.
- **Failed checker attempt 1.** The first run stopped with `KeyError: 'result'`: I assumed `rehearsal_public.json` had a `result` envelope like `analysis.json`, and it has none. The failed script was kept as `recompute_attempt1_failed.py` (the D2 fix was already applied). Its only difference from the final script is line 61:
  ```
  < pub = load(".../rehearsal_public.json")["result"]
  ---
  > pub = load(".../rehearsal_public.json")
  ```
- **Wrong ulp estimate.** During the analysis I briefly used a wrong ulp scale: a per-batch sum of about 74,000, when it is about 1,180, because a batch has 512 targets. That gave "ulp/32768 ≈ 2.4e-7". The correct figure is about 3.7e-9. This makes the 1e-6 deviations even less like rounding noise. The wrong figure appears in no conclusion.

## Appendix — scripts (verbatim)

The scratch folder `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s3-recompute/` was deleted after these were copied.


### recompute.py

```python
"""Independent recomputation of the P10-I-S3 registered outcome (ADR-0026) from raw item records.

Auditor's own code (arbor-auditor). Imports nothing from studies/p10i_s3 or arborlm. Standard library only.
Usage: python recompute.py <worktree> <run_dir> <out_json>
"""

import hashlib
import json
import math
import os
import statistics
import sys
import tomllib

WT, RUN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ITEMS = os.path.join(RUN, "items")
problems: list[str] = []


def P(msg: str) -> None:
    problems.append(msg)
    print("PROBLEM:", msg)


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(path: str):
    with open(path) as f:
        return json.load(f)


# ---------------- ADR constants (hard-coded from the ADR text, then compared with the frozen config) ----------------
ADR = dict(effect=0.005, dense_tolerance=-0.005, min_cells=22, min_parents=8, half=0.5, dense_share=0.90, dense_floor=0.005,
           tolerance_joint=1e-6, epsilon=0.001, past_best_margin=0.005, routing_effect=0.005)
U, CK = 16384, [512, 2048, 8192, 16384]
ARMS_OF = {"REP": ["M-TREE", "M-FLAT", "D-ADAPT"], "REP-U": ["M-TREE", "D-ADAPT"], "FRESH": ["M-TREE", "M-FLAT", "D-ADAPT"]}
G_IDX = {"REP": 0, "REP-U": 1, "FRESH": 2}
CAL_PARENTS = {0, 4, 8}  # parent index 3(B-101)+(O-301): B101/O301, B102/O302, B103/O303

cfg = tomllib.load(open(os.path.join(WT, "configs/p10i_s3_longer_training.toml"), "rb"))
t = cfg["thresholds"]
for k, v in [("effect", t["effect"]), ("dense_tolerance", t["dense_tolerance"]), ("min_cells", t["min_cells"]), ("min_parents", t["min_parents"]),
             ("half", t["half"]), ("dense_share", t["dense_share"]), ("dense_floor", t["dense_floor"]), ("tolerance_joint", t["tolerance_joint"]),
             ("routing_effect", t["routing_effect"]), ("epsilon", cfg["duration"]["epsilon"]), ("past_best_margin", cfg["duration"]["past_best_margin"])]:
    if float(v) != float(ADR[k]):
        P(f"config {k}={v} differs from ADR {ADR[k]}")
if list(cfg["duration"]["checkpoints"]) not in (CK, [0] + CK):
    print("config checkpoints", cfg["duration"]["checkpoints"])

# ---------------- frozen plan, rate table ----------------
plan_path = os.path.join(WT, "studies/p10i_s3/freeze/plan.json")
plan_sha = sha(plan_path)
plan = load(plan_path)
rt = load(os.path.join(WT, "studies/p10i_s3/freeze/rate_table.json"))
pub = load("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS3-rehearsal-20261118/rehearsal_public.json")
if plan["rate_table"] != rt:
    P("plan rate table != freeze/rate_table.json")
if pub["rate_table"] != rt:
    P("rehearsal_public rate table != frozen rate table")
if pub["candidate"]["plan_file_sha256"] != plan_sha:
    P("plan sha differs from the one R3 recorded")
RATES = {k: {int(d): float(r) for d, r in v.items()} for k, v in rt["rates"].items()}
EDGE = rt["edge"]


def rate(arm, g, d=U):
    return RATES[f"{arm}|{g}"][d]


def rl(r):
    return f"{r:.6g}"


# ---------------- completeness and identity ----------------
tr_items, ev_items = plan["items"]["train"], plan["items"]["eval"]
print("plan items", len(tr_items), len(ev_items), "plan sha", plan_sha)
ids = [i["id"] for i in tr_items + ev_items]
if len(ids) != len(set(ids)):
    P("duplicate plan ids")


def dirname(item_id):
    return item_id.replace("|", "__")


on_disk = set(os.listdir(ITEMS))
expect = {dirname(i) for i in ids}
if on_disk != expect:
    P(f"item dirs differ from plan: extra {sorted(on_disk - expect)[:5]} missing {sorted(expect - on_disk)[:5]}")
print("item dirs", len(on_disk), "train", sum(1 for d in on_disk if d.startswith("train")), "eval", sum(1 for d in on_disk if d.startswith("eval")))

TP = {"M-TREE": 198401, "M-FLAT": 198145, "D-ADAPT": 198401}
train_by_id = {}
for it in tr_items:
    c, g, arm = it["cell"], it["regime"], it["arm"]
    if it["init_seed"] != 330301 + c % 3:
        P(f"{it['id']} init seed {it['init_seed']}")
    if it["stream_seed"] != 260001 + 3 * c + G_IDX[g]:
        P(f"{it['id']} stream seed {it['stream_seed']}")
    if it["parent"] != c // 3 or it["profile"] != "registered":
        P(f"{it['id']} parent/profile")
    role = it["role"]
    if role == "primary":
        ok = it["rate"] == rate(arm, g) and it["max_update"] == U and it["snapshots"] == [0] + CK
    elif role == "duration":
        d = it["max_update"]
        ok = it["rate"] == rate(arm, g, d) and it["rate"] != rate(arm, g)
    elif role == "anchor":
        ok = g == "REP" and it["rate"] == 0.003 and rate(arm, g) != 0.003 and it["max_update"] == U
    else:
        ok = False
    if not ok:
        P(f"{it['id']} rate/role inconsistent with the frozen rate table: {role} {it['rate']} {it['max_update']}")
    if it["id"] != f"train|{arm}|{g}|r{rl(it['rate'])}|c{c:02d}":
        P(f"{it['id']} id format")
    rec = load(os.path.join(ITEMS, dirname(it["id"]), "train.json"))
    if rec.get("id") != it["id"] or rec.get("status") != "ok" or rec.get("failed_at_update") is not None or rec.get("updates_done") != it["max_update"]:
        P(f"train record {it['id']}: {rec.get('status')} {rec.get('updates_done')}")
    if rec.get("trainable_parameters") != TP[arm]:
        P(f"train record {it['id']} trainable {rec.get('trainable_parameters')}")
    if sorted(int(k) for k in rec["snapshots"]) != sorted(it["snapshots"]):
        P(f"train record {it['id']} snapshots {sorted(rec['snapshots'])} vs plan {it['snapshots']}")
    train_by_id[it["id"]] = (it, rec)

roles = {}
for it, _ in train_by_id.values():
    roles.setdefault((it["arm"], it["regime"], it["role"], it["rate"], it["max_update"]), 0)
    roles[(it["arm"], it["regime"], it["role"], it["rate"], it["max_update"])] += 1

base = {int(p): v for p, v in load(os.path.join(RUN, "gates/results/core.json"))["results"]["base_values"].items()}
for p, v in base.items():
    if not (v["enabled"] == v["replay"] == v["disabled"]):
        P(f"BASE parent {p} enabled/replay/disabled differ")
B = {p: v["enabled"] for p, v in base.items()}

TREE_READS = ["enabled|0", "replay|0", "disabled|0", "P_all|0"] + [f"P_used|{j}" for j in range(4)] + ["X_mean|0"] + [f"X|{j}" for j in range(4)] + ["joint|0", "exhaustive|0", "prior_off|0"]
FLAT_READS = ["enabled|0", "replay|0", "disabled|0", "P_all|0"] + [f"P_used|{j}" for j in range(4)] + ["X_mean|0"] + [f"X|{j}" for j in range(4)]
DENSE_READS = ["enabled|0", "replay|0", "disabled|0"] + [f"X_dense|{j}" for j in range(4)] + ["X_mean_dense|0"]
FULL = {"M-TREE": TREE_READS, "M-FLAT": FLAT_READS, "D-ADAPT": DENSE_READS}

V = {}  # (arm, regime, rate_label, cell, ckpt) -> reads dict, stats
nonfinite_any = 0
for it in ev_items:
    arm, g, c, k = it["arm"], it["regime"], it["cell"], it["update"]
    tr = train_by_id.get(it["train"])
    if tr is None:
        P(f"{it['id']} refers to unplanned train item")
        continue
    if tr[0]["rate"] != it["rate"] or tr[0]["cell"] != c or tr[0]["arm"] != arm or tr[0]["regime"] != g or k not in tr[0]["snapshots"]:
        P(f"{it['id']} inconsistent with its train item")
    rec = load(os.path.join(ITEMS, dirname(it["id"]), "eval.json"))
    if rec.get("id") != it["id"] or rec.get("update") != k or rec.get("controls") != it["controls"] or rec.get("nonfinite_enabled") or rec.get("status") == "item_error":
        P(f"eval record {it['id']} header")
    reads = rec["reads"]
    if it["controls"] == "full":
        exp = FULL[arm]
    elif it["controls"] == "step0":
        exp = ["enabled|0", "disabled|0"]
    else:
        exp = ["enabled|0", "replay|0", "disabled|0"]
    if sorted(reads) != sorted(exp):
        P(f"eval record {it['id']} read keys {sorted(reads)}")
    for kk, v in reads.items():
        if v is None or not math.isfinite(v):
            nonfinite_any += 1
            P(f"non-finite {it['id']} {kk}")
    if reads.get("disabled|0") != B[c // 3]:
        P(f"disabled != BASE bitwise {it['id']}")
    if "replay|0" in reads and reads["replay|0"] != reads["enabled|0"]:
        P(f"replay != enabled bitwise {it['id']}")
    key = (arm, g, rl(it["rate"]), c, k)
    if key in V:
        P(f"duplicate evaluation {key}")
    V[key] = (reads, rec.get("stats", {}))
print("eval records loaded", len(V), "non-finite", nonfinite_any)
print("train roles", json.dumps({"|".join(map(str, k)): v for k, v in sorted(roles.items(), key=str)}))

# manifests and ledger
for s in ("gates", "train", "eval"):
    m = load(os.path.join(RUN, s, "manifest.json"))
    if m["status"] != "COMPLETE" or m["mode"] != "registered" or m["identity"]["commit"] != "2e985787c466c5ac66356635d4c68704d3730c55":
        P(f"manifest {s}: {m['status']} {m['identity']}")
    print("manifest", s, m["status"], "history", len(m["history"]), "charged", m["charged_seconds"], "tasks", len(m["tasks"]))
led = load(os.path.join(RUN, "ledger.json"))
charged = sum(e["seconds"] for e in led["entries"])
print("ledger", [(e["stage"], round(e["seconds"], 1)) for e in led["entries"]], "total s", round(charged, 1), "h", round(charged / 3600, 4),
      "cap s", led["total_seconds"], "cap h", round(led["total_seconds"] / 3600, 4), "plan cap h", plan["caps"]["registered_hours"])


# ---------------- quantities ----------------
def H(arm, g, c, k, read="enabled", r=None, draws=1):
    r = rate(arm, g, k) if r is None else r
    reads = V[(arm, g, rl(r), c, k)][0]
    if draws == 1:
        return reads[f"{read}|0"]
    vals = [reads[f"{read}|{j}"] for j in range(draws)]
    return sum(vals) / draws  # ruling 12: average the draws' NLLs, then subtract H


CELLS = list(range(27))


def mean(v):
    return math.fsum(v) / len(v)


def pmeans(v):
    return [mean(v[3 * p: 3 * p + 3]) for p in range(9)]


def cnt(v, pred):
    return sum(1 for x in v if pred(x))


def cells_for(g, k=U):
    out = {}
    for arm in ARMS_OF[g]:
        out[arm] = {"H": [H(arm, g, c, k) for c in CELLS]}
    return out


Bc = [B[c // 3] for c in CELLS]


def line1(g):
    k = U
    r = rate("M-TREE", g)
    Hs = [H("M-TREE", g, c, k) for c in CELLS]
    C = [b - h for b, h in zip(Bc, Hs)]
    Pu = [H("M-TREE", g, c, k, "P_used", draws=4) - h for c, h in zip(CELLS, Hs)]
    Xm = [H("M-TREE", g, c, k, "X_mean") - h for c, h in zip(CELLS, Hs)]
    used = [V[("M-TREE", g, rl(r), c, k)][1]["used_slots"] for c in CELLS]
    collapsed = [u < 2 for u in used]
    d1 = {"mean": mean(C), "cells": cnt(C, lambda x: x > 0), "parents": cnt(pmeans(C), lambda x: x > 0)}
    d1["ok"] = d1["mean"] >= ADR["effect"] and d1["cells"] >= 22 and d1["parents"] >= 8
    d2 = {"mean": mean(Pu), "cells": sum(1 for ci, pi, col in zip(C, Pu, collapsed) if not col and ci > 0 and pi >= 0.5 * ci), "parents": cnt(pmeans(Pu), lambda x: x > 0)}
    d2["ok"] = d2["mean"] >= ADR["effect"] and d2["cells"] >= 22 and d2["parents"] >= 8  # a collapsed cell fails D2 per cell (count above)
    d3 = {"mean": mean(Xm), "cells": sum(1 for ci, xi in zip(C, Xm) if ci > 0 and xi >= 0.5 * ci), "parents": cnt(pmeans(Xm), lambda x: x > 0)}
    d3["ok"] = d3["mean"] >= ADR["effect"] and d3["cells"] >= 22 and d3["parents"] >= 8
    # minimum per-cell ratios (margins)
    ratio_p = min(pi / ci for ci, pi in zip(C, Pu))
    ratio_x = min(xi / ci for ci, xi in zip(C, Xm))
    return {"C": C, "P_used": Pu, "X_mean": Xm, "used": used, "D1": d1, "D2": d2, "D3": d3, "min_ratio_P": ratio_p, "min_ratio_X": ratio_x, "collapsed": sum(collapsed)}


def line2(g, mem):
    Hm = [H(mem, g, c, U) for c in CELLS]
    A = [H("D-ADAPT", g, c, U) for c in CELLS]
    C = [b - h for b, h in zip(Bc, Hm)]
    Cd = [b - a for b, a in zip(Bc, A)]
    Q = [a - h for a, h in zip(A, Hm)]  # ADR: Q = A - H
    Qalt = [c - d for c, d in zip(C, Cd)]
    k1 = {"mean": mean(Q), "cells": cnt(Q, lambda x: x >= -0.005), "parents": cnt(pmeans(Q), lambda x: x >= -0.005)}
    k1["ok"] = k1["mean"] >= -0.005 and k1["cells"] >= 22 and k1["parents"] >= 8
    k2 = {"mean_C": mean(C), "mean_C_dense": mean(Cd)}
    k2["ok"] = k2["mean_C"] >= 0.90 * k2["mean_C_dense"]
    k3 = {"mean": mean(Q), "cells": cnt(Q, lambda x: x > 0), "parents": cnt(pmeans(Q), lambda x: x > 0)}
    k3["ok"] = k3["mean"] >= 0.005 and k3["cells"] >= 22 and k3["parents"] >= 8
    if mean(Cd) < 0.005:
        lab = "NOT EVALUABLE"
    elif k3["ok"]:
        lab = "MEMORY AHEAD"
    elif k1["ok"] and k2["ok"]:
        lab = "COMPETITIVE"
    else:
        lab = "NOT COMPETITIVE"
    return {"Q": Q, "Q_via_gains_maxdiff": max(abs(a - b) for a, b in zip(Q, Qalt)), "C": C, "C_dense": Cd, "K1": k1, "K2": k2, "K3": k3, "base_label": lab,
            "mean_H_mem": mean(Hm), "mean_H_dense": mean(A), "Q_parent_means": pmeans(Q)}


def curve(arm, g):
    r = rate(arm, g)
    out = {}
    for k in [0] + CK:
        key0 = (arm, g, rl(r), 0, k)
        if key0 in V:
            out[k] = mean([V[(arm, g, rl(r), c, k)][0]["enabled|0"] for c in CELLS])
    return out


def conv(arm, g):
    cu = curve(arm, g)
    d = cu[8192] - cu[U]
    tag = "CONVERGED" if d < ADR["epsilon"] else "NOT CONVERGED"
    pb = None
    if g in ("REP", "REP-U"):
        earlier = [v for k, v in cu.items() if k < U]
        pb = cu[U] - min(earlier) > ADR["past_best_margin"]
    return {"delta": d, "tag": tag, "past_best": pb, "curve": cu}


def joint_devs():
    """|joint - enabled| for every M-TREE evaluation that has a joint read."""
    out = []
    for (arm, g, r, c, k), (reads, _) in V.items():
        if arm == "M-TREE" and "joint|0" in reads:
            out.append({"regime": g, "rate": r, "cell": c, "ckpt": k, "dev": abs(reads["joint|0"] - reads["enabled|0"]), "signed": reads["joint|0"] - reads["enabled|0"],
                        "primary": float(r) == rate("M-TREE", g), "rate_for_ckpt": float(r) == rate("M-TREE", g, k) if k in CK else None})
    return out


def integrity(arm, g):
    """ADR section 10. Checked on (a) the evaluations the registered label reads (primary run at U*), and (b) every evaluated checkpoint of the run at the
    per-duration rate and of the primary run (the implementer's wider reading), reported separately."""
    narrow, wide = [], []
    for (a, gg, r, c, k), (reads, _) in V.items():
        if a != arm or gg != g or k == 0:
            continue
        rr = float(r)
        if not (rr == rate(arm, g) or (k in CK and rr == rate(arm, g, k))):
            continue  # anchor runs are not checked by either reading
        bad = []
        if reads.get("replay|0") != reads["enabled|0"]:
            bad.append("replay")
        if reads["disabled|0"] != B[c // 3]:
            bad.append("disabled")
        if "joint|0" in reads and abs(reads["joint|0"] - reads["enabled|0"]) > ADR["tolerance_joint"]:
            bad.append("joint")
        for b in bad:
            s = f"{arm}|{g}|c{c}|u{k}|r{r}: {b}"
            wide.append(s)
            if k == U and rr == rate(arm, g):
                narrow.append(s)
    return {"narrow_U_star_primary": sorted(narrow), "wide_every_checkpoint": sorted(wide)}


def gap_label(v, pos, neg):
    m = mean(v)
    if m >= 0.005 and cnt(v, lambda x: x > 0) >= 22:
        return pos
    if m <= -0.005 and cnt(v, lambda x: x < 0) >= 22:
        return neg
    return "WITHIN RESOLUTION"


def routing(g):
    rows = {}
    for k in CK:
        ht = [H("M-TREE", g, c, k) for c in CELLS]
        hf = [H("M-FLAT", g, c, k) for c in CELLS]
        gt = [a - b for a, b in zip(ht, hf)]
        gr = [a - H("M-TREE", g, c, k, "exhaustive") for c, a in zip(CELLS, ht)]
        gp = [H("M-TREE", g, c, k, "prior_off") - a for c, a in zip(CELLS, ht)]
        prim = [H("M-TREE", g, c, k, r=rate("M-TREE", g)) - H("M-FLAT", g, c, k, r=rate("M-FLAT", g)) for c in CELLS]
        rows[k] = {"G_train": gt, "G_read": gr, "G_prior": gp, "G_train_mean": mean(gt), "G_read_mean": mean(gr), "G_prior_mean": mean(gp), "G_train_primary_rate_mean": mean(prim),
                   "G_train_label": gap_label(gt, "TREE BEHIND", "TREE AHEAD"), "G_read_label": gap_label(gr, "RESTRICTION COSTS", "RESTRICTION HELPS"),
                   "G_train_pos": cnt(gt, lambda x: x > 0), "G_train_neg": cnt(gt, lambda x: x < 0), "G_read_pos": cnt(gr, lambda x: x > 0), "G_read_neg": cnt(gr, lambda x: x < 0)}
    tr = {}
    for nm in ("G_train", "G_read"):
        d = [b - a for a, b in zip(rows[512][nm], rows[U][nm])]
        tr[nm] = {"trend": "GAP CHANGES WITH DURATION" if rows[512][nm + "_label"] != rows[U][nm + "_label"] else "NO CHANGE AT THIS RESOLUTION",
                  "dG_mean": mean(d), "pos": cnt(d, lambda x: x > 0), "neg": cnt(d, lambda x: x < 0)}
    return {"rows": rows, "trend": tr}


def six(g):
    keep = [c for c in CELLS if c // 3 not in CAL_PARENTS]
    Hs = {c: H("M-TREE", g, c, U) for c in keep}
    C = [B[c // 3] - Hs[c] for c in keep]
    Cd = [B[c // 3] - H("D-ADAPT", g, c, U) for c in keep]
    Q = [H("D-ADAPT", g, c, U) - Hs[c] for c in keep]
    Pu = [H("M-TREE", g, c, U, "P_used", draws=4) - Hs[c] for c in keep]
    Xm = [H("M-TREE", g, c, U, "X_mean") - Hs[c] for c in keep]
    return {"cells": len(keep), "parents": len({c // 3 for c in keep}), "C": mean(C), "C_dense": mean(Cd), "Q": mean(Q), "nC": cnt(C, lambda x: x > 0),
            "nP": sum(1 for a, b in zip(C, Pu) if a > 0 and b >= 0.5 * a), "nX": sum(1 for a, b in zip(C, Xm) if a > 0 and b >= 0.5 * a),
            "nQwithin": cnt(Q, lambda x: x >= -0.005), "nQahead": cnt(Q, lambda x: x > 0),
            "parent_means_Q": pmeans_sub(Q, keep)}


def pmeans_sub(v, keep):
    out = {}
    for x, c in zip(v, keep):
        out.setdefault(c // 3, []).append(x)
    return {p: mean(xs) for p, xs in out.items()}


def contrasts(g):
    out = {}
    for k in (512, U):
        Ht = [H("M-TREE", g, c, k) for c in CELLS]
        A = [H("D-ADAPT", g, c, k) for c in CELLS]
        out[k] = {"C_mean": mean([b - h for b, h in zip(Bc, Ht)]), "C_dense_mean": mean([b - a for b, a in zip(Bc, A)]), "Q_mean": mean([a - h for a, h in zip(A, Ht)]),
                  "P_used_mean": mean([H("M-TREE", g, c, k, "P_used", draws=4) - h for c, h in zip(CELLS, Ht)]),
                  "X_mean_mean": mean([H("M-TREE", g, c, k, "X_mean") - h for c, h in zip(CELLS, Ht)])}
    return out


res = {"problems": problems, "plan_sha256": plan_sha, "ledger_seconds": charged, "ledger_cap_seconds": led["total_seconds"], "regimes": {}}
for g in ("REP", "REP-U", "FRESH"):
    R = {"conv": {a: conv(a, g) for a in ARMS_OF[g]}, "integrity": {a: integrity(a, g) for a in ARMS_OF[g]}, "line1": line1(g), "line2_tree": line2(g, "M-TREE"), "contrasts": contrasts(g), "six": six(g)}
    if "M-FLAT" in ARMS_OF[g]:
        R["line2_flat"] = line2(g, "M-FLAT")
        R["routing"] = routing(g)
        # M-FLAT descriptive D1-D3
        Hf = [H("M-FLAT", g, c, U) for c in CELLS]
        Cf = [b - h for b, h in zip(Bc, Hf)]
        Pf = [H("M-FLAT", g, c, U, "P_used", draws=4) - h for c, h in zip(CELLS, Hf)]
        Xf = [H("M-FLAT", g, c, U, "X_mean") - h for c, h in zip(CELLS, Hf)]
        R["flat_d1d3"] = {"D1": mean(Cf), "D2": mean(Pf), "D3": mean(Xf), "D2cells": sum(1 for a, b in zip(Cf, Pf) if a > 0 and b >= 0.5 * a), "D3cells": sum(1 for a, b in zip(Cf, Xf) if a > 0 and b >= 0.5 * a)}
    # labels under both integrity readings
    l1 = R["line1"]
    l1_label = "DEPENDENT" if (l1["D1"]["ok"] and l1["D2"]["ok"] and l1["D3"]["ok"]) else ("CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" if l1["D1"]["ok"] else "NO CAPACITY")
    R["line1_label_no_integrity"] = l1_label
    for reading in ("wide_every_checkpoint", "narrow_U_star_primary"):
        stop_t = bool(R["integrity"]["M-TREE"][reading])
        stop_d = bool(R["integrity"]["D-ADAPT"][reading])
        lab1 = "NOT EVALUABLE" if stop_t else l1_label
        labs = {"line1": lab1}
        for mem, key in (("M-TREE", "line2_tree"), ("M-FLAT", "line2_flat")):
            if key not in R:
                continue
            l2 = R[key]
            stop = bool(R["integrity"][mem][reading]) or stop_d
            lab = "NOT EVALUABLE" if stop else l2["base_label"]
            tags = []
            if lab != "NOT EVALUABLE":
                if lab == "NOT COMPETITIVE" and EDGE[f"{mem}|{g}"]:
                    lab = "INCONCLUSIVE (MEMORY RATE AT EDGE)"
                elif lab in ("COMPETITIVE", "MEMORY AHEAD") and EDGE[f"D-ADAPT|{g}"]:
                    lab = "INCONCLUSIVE (DENSE RATE AT EDGE)"
                hm, hd = l2["mean_H_mem"], l2["mean_H_dense"]
                if hm > hd and R["conv"][mem]["tag"] != "CONVERGED":
                    tags.append("(MEMORY STILL IMPROVING)")
                if hd > hm and R["conv"]["D-ADAPT"]["tag"] != "CONVERGED":
                    tags.append("(DENSE STILL IMPROVING)")
                if g != "FRESH":
                    if R["conv"][mem]["past_best"]:
                        tags.append(f"({mem} PAST BEST CHECKPOINT)")
                    if R["conv"]["D-ADAPT"]["past_best"]:
                        tags.append("(D-ADAPT PAST BEST CHECKPOINT)")
            labs[key] = (lab, tags)
        R[f"labels_{reading}"] = labs
    res["regimes"][g] = R

jd = joint_devs()
res["joint_devs"] = jd
# anchor
Ht = [H("M-TREE", "REP", c, U, r=0.003) for c in CELLS]
res["anchor_C_at_0.003"] = mean([b - h for b, h in zip(Bc, Ht)])
res["step0"] = {f"{a}|{g}": mean([V[(a, g, rl(rate(a, g)), c, 0)][0]["enabled|0"] for c in CELLS]) for g in ARMS_OF for a in ARMS_OF[g] if (a, g, rl(rate(a, g)), 0, 0) in V}
res["B_mean"] = mean(Bc)
json.dump(res, open(OUT, "w"), indent=1, default=str)
print("problems", len(problems))
```

### compare.py

```python
"""Compare the auditor's recomputation (mine.json) with the registered analysis.json, quantity by quantity. Standard library only."""

import json
import statistics
import sys

mine = json.load(open(sys.argv[1]))
reg = json.load(open(sys.argv[2]))["result"]
rows = []  # (quantity, registered, recomputed, absdiff)


def add(name, a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        rows.append((name, a, b, abs(a - b)))
    else:
        rows.append((name, a, b, 0.0 if a == b else "DIFFERENT"))


U = "16384"
for g in ("REP", "REP-U", "FRESH"):
    M, Rg = mine["regimes"][g], reg["regimes"][g]
    l1 = Rg["line1"]["detail"]["conditions"]
    if l1:
        for d in ("D1", "D2", "D3"):
            for f in ("mean", "cells", "parents", "ok"):
                add(f"{g} line1 {d} {f}", l1[d][f], M["line1"][d][f])
    else:
        add(f"{g} line1 conditions (registered printed none: NOT EVALUABLE)", "none", "computed")
    for key in ("line2_tree", "line2_flat"):
        if key not in Rg:
            continue
        det = Rg[key]["detail"]
        if det.get("conditions"):
            for kx in ("K1", "K3"):
                for f in ("mean", "cells", "parents", "ok"):
                    add(f"{g} {key} {kx} {f}", det["conditions"][kx][f], M[key][kx][f])
            for f in ("mean_C", "mean_C_dense", "ok"):
                add(f"{g} {key} K2 {f}", det["conditions"]["K2"][f], M[key]["K2"][f])
        add(f"{g} {key} q_mean", det["q_mean"], statistics.fmean(M[key]["Q"]))
    for a, cv in Rg["convergence"].items():
        add(f"{g} delta {a}", cv["delta"], M["conv"][a]["delta"])
        add(f"{g} conv tag {a}", cv["tag"], M["conv"][a]["tag"])
        for k, v in Rg["curves"][a].items():
            add(f"{g} curve {a} {k}", v, M["conv"][a]["curve"][k])
        add(f"{g} past_best {a}", Rg["past_best"][a]["flag"], bool(M["conv"][a]["past_best"]))
    for a, ip in Rg["integrity_problems"].items():
        add(f"{g} integrity {a} (registered vs auditor wide reading)", sorted(x.replace(" outside 1e-06", "").replace("joint permutation", "joint") for x in ip), M["integrity"][a]["wide_every_checkpoint"])
    # labels (registered final vs mine under the registered (wide) integrity reading)
    labs = M["labels_wide_every_checkpoint"]
    add(f"{g} label line1", Rg["line1"]["label"], labs["line1"])
    add(f"{g} line1 tags", Rg["line1"]["tags"], (["(M-TREE NOT CONVERGED)"] if M["conv"]["M-TREE"]["tag"] != "CONVERGED" else []) + (["(M-TREE PAST BEST CHECKPOINT)"] if M["conv"]["M-TREE"]["past_best"] else []) if labs["line1"] != "NOT EVALUABLE" else [])
    for key in ("line2_tree", "line2_flat"):
        if key in Rg:
            add(f"{g} label {key}", [Rg[key]["label"], Rg[key]["tags"]], list(labs[key]))
    # contrasts
    for k in ("512", U):
        for f, v in reg["contrasts"][g][k].items():
            add(f"{g} contrast {k} {f}", v, M["contrasts"][k if k == "512" else "16384"][f] if k in M["contrasts"] else M["contrasts"][int(k)][f])
    # six-parent
    sp, ms = reg["six_parent"][g], M["six"]
    for f, mf in (("C", "C"), ("C_dense", "C_dense"), ("Q", "Q")):
        add(f"{g} six-parent mean {f}", sp[f]["mean"], ms[mf])
    for f, mf in (("n_C_positive", "nC"), ("n_P_half", "nP"), ("n_X_half", "nX"), ("n_Q_within", "nQwithin"), ("n_Q_ahead", "nQahead"), ("cells", "cells"), ("parents", "parents")):
        add(f"{g} six-parent {f}", sp[f], ms[mf])
    if "routing" in M:
        ro = reg["routing"][g]
        for k in ("512", "2048", "8192", U):
            r, m = ro["rows"][k], M["routing"]["rows"][k]
            add(f"{g} routing {k} G_train label", r["G_train_label"], m["G_train_label"])
            add(f"{g} routing {k} G_read label", r["G_read_label"], m["G_read_label"])
            add(f"{g} routing {k} G_train mean", statistics.fmean(r["G_train"]), m["G_train_mean"])
            add(f"{g} routing {k} G_read mean", statistics.fmean(r["G_read"]), m["G_read_mean"])
            add(f"{g} routing {k} G_prior mean", r["G_prior_stats"]["mean"], m["G_prior_mean"])
            add(f"{g} routing {k} G_train primary-rate mean", r["G_train_primary_rate_mean"], m["G_train_primary_rate_mean"])
            for i, (x, y) in enumerate(zip(r["G_train"], m["G_train"])):
                add(f"{g} routing {k} G_train per-cell", x, y)
            for i, (x, y) in enumerate(zip(r["G_read"], m["G_read"])):
                add(f"{g} routing {k} G_read per-cell", x, y)
            for i, (x, y) in enumerate(zip(r["G_prior"], m["G_prior"])):
                add(f"{g} routing {k} G_prior per-cell", x, y)
        for nm in ("G_train", "G_read"):
            t, mt = ro[f"{nm}_trend"], M["routing"]["trend"][nm]
            add(f"{g} {nm} trend", t["trend"], mt["trend"])
            add(f"{g} {nm} dG mean", t["delta_G"]["mean"], mt["dG_mean"])
            add(f"{g} {nm} dG pos", t["delta_G"]["n_positive"], mt["pos"])
            add(f"{g} {nm} dG neg", t["delta_G"]["n_negative"], mt["neg"])
    # per-cell C, P_used, X_mean at U* from descriptive
    de = reg["descriptive"][g]["M-TREE"][U]
    add(f"{g} descriptive M-TREE C mean", de["C"]["mean"], statistics.fmean(M["line1"]["C"]))
    add(f"{g} descriptive M-TREE P_used mean", de["P_used"]["mean"], statistics.fmean(M["line1"]["P_used"]))
    add(f"{g} descriptive M-TREE X_mean mean", de["X_mean"]["mean"], statistics.fmean(M["line1"]["X_mean"]))
    add(f"{g} descriptive used_slots", de["used_slots"], M["line1"]["used"])
    if "flat_d1d3" in Rg:
        for d in ("D1", "D2", "D3"):
            add(f"{g} flat {d} mean", Rg["flat_d1d3"][d]["mean"], M["flat_d1d3"][d])

add("registered line1", reg["line1"]["label"], mine["regimes"]["FRESH"]["labels_wide_every_checkpoint"]["line1"])
add("registered line2_tree", reg["line2_tree"]["label"], mine["regimes"]["FRESH"]["labels_wide_every_checkpoint"]["line2_tree"][0])
add("registered line2_flat", reg["line2_flat"]["label"], mine["regimes"]["FRESH"]["labels_wide_every_checkpoint"]["line2_flat"][0])
add("anchor C at 0.003", reg["anchor"]["M-TREE"]["C_at_p4_rate"]["mean"], mine["anchor_C_at_0.003"])

# summary: max abs difference per quantity family
fam = {}
for name, a, b, d in rows:
    key = " ".join(w for w in name.split() if not w.isdigit() or w in ("512", "2048", "8192", "16384"))
    if isinstance(d, str):
        fam.setdefault(key, []).append(d)
    else:
        fam.setdefault(key, []).append(d)
diffs = [r for r in rows if isinstance(r[3], str)]
print("rows", len(rows), "label/structure differences", len(diffs))
for r in diffs:
    print("DIFF", r[0], "| registered:", r[1], "| auditor:", r[2])
nums = [r for r in rows if not isinstance(r[3], str)]
print("max abs numeric diff over all", max(r[3] for r in nums))
worst = sorted(nums, key=lambda r: -r[3])[:12]
for r in worst:
    print("WORST", r[0], r[1], r[2], r[3])
json.dump([list(r) for r in rows], open(sys.argv[3], "w"), indent=0, default=str)
```

### margins.py

```python
"""Margins and spread for the deciding thresholds (auditor's own; reads mine.json and registered eval records only)."""
import json, statistics, sys
m = json.load(open(sys.argv[1]))
def pm(v): return [statistics.fmean(v[3*p:3*p+3]) for p in range(9)]
def within_sd(v):
    return statistics.fmean([statistics.stdev(v[3*p:3*p+3]) for p in range(9)])
for g in ("FRESH", "REP-U", "REP"):
    R = m["regimes"][g]
    for key in ("line2_tree", "line2_flat"):
        if key not in R: continue
        Q = R[key]["Q"]
        pmq = pm(Q)
        srt = sorted(Q)
        print(g, key, "Q mean %.6f sd %.6f min %.6f max %.6f within-parent sd(mean over parents) %.6f" % (statistics.fmean(Q), statistics.stdev(Q), min(Q), max(Q), within_sd(Q)))
        print("   cells Q>=-0.005:", sum(q >= -0.005 for q in Q), " 5th-6th lowest Q:", ["%.6f" % x for x in srt[:7]])
        print("   parent means:", ["%.5f" % x for x in pmq], " SE of a 3-cell mean ~ %.5f" % (within_sd(Q) / 3 ** 0.5))
        print("   cells Q>0:", sum(q > 0 for q in Q), " parents Q>0:", sum(x > 0 for x in pmq), " K2 margin mean_C - 0.9 mean_Cd = %.6f" % (R[key]["K2"]["mean_C"] - 0.9 * R[key]["K2"]["mean_C_dense"]))
        print("   cell C sd %.6f, C_dense sd %.6f" % (statistics.stdev(R[key]["C"]), statistics.stdev(R[key]["C_dense"])))
    l = R["line1"]
    print(g, "line1 D1 mean-0.005 %.5f D2 %.5f D3 %.5f min P/C %.3f min X/C %.3f" % (l["D1"]["mean"]-0.005, l["D2"]["mean"]-0.005, l["D3"]["mean"]-0.005, l["min_ratio_P"], l["min_ratio_X"]))
    BmH = [c - p for c, p in zip(l["C"], l["P_used"])]  # B - H_used = C - P_used
    BmX = [c - x for c, x in zip(l["C"], l["X_mean"])]
    print("   B-H_used mean %.5f, cells with H_used > B: %d; B-H_mean mean %.5f, cells with H_mean > B: %d" % (statistics.fmean(BmH), sum(v < 0 for v in BmH), statistics.fmean(BmX), sum(v < 0 for v in BmX)))
    for a, c in R["conv"].items():
        cu = {int(k): v for k, v in c["curve"].items()}
        pb = cu[16384] - min(v for k, v in cu.items() if k < 16384)
        print("   conv %s delta %.6f (eps margin %.6f) tag %s; U* minus lowest earlier checkpoint %.6f (PAST BEST margin 0.005); step0 present %s" % (a, c["delta"], c["delta"] - 0.001, c["tag"], pb, 0 in cu))
    if "routing" in R:
        for k, r in R["routing"]["rows"].items():
            print("   routing u%s G_train mean %+.6f pos %d neg %d label %s | G_read mean %+.6f pos %d neg %d label %s | G_prior %+.6f | primary %+.6f" % (k, r["G_train_mean"], r["G_train_pos"], r["G_train_neg"], r["G_train_label"], r["G_read_mean"], r["G_read_pos"], r["G_read_neg"], r["G_read_label"], r["G_prior_mean"], r["G_train_primary_rate_mean"]))
print("step0 means", m["step0"], "B mean", m["B_mean"])
```

### snapshots_check.py

```python
"""Snapshot identity (seeds, rate, arm, cell) against the frozen plan, snapshot file hashes against train records, and a static tie
diagnostic of the M-TREE keys for the joint-permutation cases. Reads registered checkpoints only; no data, no evaluation, no training."""

import hashlib
import json
import os
import sys

import torch

WT, RUN = sys.argv[1], sys.argv[2]
plan = json.load(open(os.path.join(WT, "studies/p10i_s3/freeze/plan.json")))
ITEMS = os.path.join(RUN, "items")
bad = []
nsnap = 0
for it in plan["items"]["train"]:
    d = os.path.join(ITEMS, it["id"].replace("|", "__"))
    rec = json.load(open(os.path.join(d, "train.json")))
    for k, meta in rec["snapshots"].items():
        p = os.path.join(d, "snapshots", f"snap-u{int(k):05d}")
        idx = json.load(open(os.path.join(p, "index.json")))
        h = hashlib.sha256(open(os.path.join(p, "state.pt"), "rb").read()).hexdigest()
        nsnap += 1
        if h != meta["sha256"] and h != idx.get("state_sha256"):
            bad.append(f"{it['id']} u{k}: file sha matches neither record")
        if meta["sha256"] != h:
            bad.append(f"{it['id']} u{k}: train record sha != file sha (index state_sha256 {'matches' if idx.get('state_sha256') == h else 'differs'})")
        if idx.get("step") != int(k):
            bad.append(f"{it['id']} u{k}: index step {idx.get('step')}")
    # identity from the last snapshot
    last = max(int(k) for k in rec["snapshots"])
    s = torch.load(os.path.join(d, "snapshots", f"snap-u{last:05d}", "state.pt"), weights_only=True, map_location="cpu")
    ident = s["identity"]
    for f in ("arm", "regime", "rate", "cell", "parent", "init_seed", "stream_seed", "profile"):
        if ident.get(f) != it[f]:
            bad.append(f"{it['id']}: snapshot identity {f}={ident.get(f)} plan {it[f]}")
    if s.get("step") != last:
        bad.append(f"{it['id']}: snapshot step {s.get('step')}")
    if it["arm"] != "D-ADAPT" and "optimizer" in s:
        lr = s["optimizer"]["param_groups"][0]["lr"]
        if lr != it["rate"]:
            bad.append(f"{it['id']}: optimizer lr {lr} != plan rate {it['rate']}")
    elif "optimizer" in s:
        lr = s["optimizer"]["param_groups"][0]["lr"]
        if lr != it["rate"]:
            bad.append(f"{it['id']}: optimizer lr {lr} != plan rate {it['rate']}")
print("snapshots hashed", nsnap, "identity/hash problems", len(bad))
for b in bad[:40]:
    print("BAD", b)

# static tie diagnostic: duplicate key rows (raw and L2-normalised, float32) within a branch, for the M-TREE checkpoints with a joint read
cases = [("REP-U", "0.03", 21, 512), ("REP", "0.01", 12, 16384), ("REP", "0.03", 15, 2048), ("REP-U", "0.03", 15, 8192), ("REP", "0.01", 8, 16384),
         ("REP-U", "0.03", 13, 512), ("REP-U", "0.03", 11, 512),
         # controls with a bitwise-zero deviation
         ("REP", "0.01", 0, 16384), ("REP-U", "0.03", 21, 2048), ("FRESH", "0.3", 12, 16384), ("FRESH", "0.3", 21, 16384), ("REP-U", "0.003", 21, 16384)]
for g, r, c, k in cases:
    p = os.path.join(ITEMS, f"train__M-TREE__{g}__r{r}__c{c:02d}", "snapshots", f"snap-u{k:05d}", "state.pt")
    keys = torch.load(p, weights_only=True, map_location="cpu")["addition"]["keys"]
    nk = torch.nn.functional.normalize(keys, dim=-1, eps=1e-6)
    dup_raw = dup_norm = 0
    min_gap = float("inf")
    for b in range(16):
        blk, nb = keys[b * 256:(b + 1) * 256], nk[b * 256:(b + 1) * 256]
        dup_raw += 256 - torch.unique(blk, dim=0).shape[0]
        dup_norm += 256 - torch.unique(nb, dim=0).shape[0]
        dist = torch.cdist(nb.double(), nb.double())
        dist.fill_diagonal_(float("inf"))
        min_gap = min(min_gap, float(dist.min()))
    print(f"{g} r{r} c{c} u{k}: duplicate key rows within a branch raw {dup_raw}, normalised {dup_norm}; min distance between normalised keys in a branch {min_gap:.3e}; key norm min {float(keys.norm(dim=-1).min()):.3e}")
```

### recompute_attempt1_failed.py

Identical to recompute.py except line 61 (see section 7).
