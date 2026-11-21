# P10-I-S0: independent recomputation of the registered result (run P10IS0-run-20261118, freeze 58cef50)

Auditor: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-20. This is Claude review. `Astra review: NOT_PERFORMED`; it is not Astra validation and not a human approval.

**Result: every printed item MATCHES** my own recomputation from the raw cell records. There is one wording difference: the headline prints the symbol "ℓ₁" where the rule's template stands for the load, 2. The integrity checks pass, with one engineering defect to disclose: the ledger does not record the main-grid invocations that were killed (section 3b). The headline's UNRESOLVED rests entirely on the 8K/4K extension refusal: by the rule it was refused by 0.61 h (P 55.61 h against B = 55). Had 8K/4K been SHOWN, the same cells would give **OVERLOAD NOT QUALIFIED AT 2** (step 6). The report does not say this.

## Inputs and commands
Everything below was read-only.
- **Cell records:** `<run>/cells/*/result.json` and `train_*.json` (200 cells), snapshot `model.pt` hashes, `cells/*/incomplete/*`.
- **Run records:** `analysis.json`, `report.md`, `P10IS0-ledger.json`, `main/manifest.json`, `tasks/main/*`, `timing/rates.json`, `timing/memory_peaks.json`, `x8/gate.json`, `sealed_location.json`.
- **Freeze files** in the worktree: `freeze/{plan,durations,stage_caps,freeze_record}.json`, and `configs/p10is0_overload.toml`.
- **Sealed values read** (allowed now that the analysis has run): the 24 Stage R points of 8K/4K, `/Users/daniellaloush/dandush03/ArborLM-sealed/p10is0/sealed/8K-4K-{A5-D,A6}-c{1,2}-r0-e{512..16384}.json`. Nothing else sealed.

Scripts are in `experiments/_scratch/audits/p10is0_recompute/` (system `python3`, standard library only, no import from `studies/`, each under `timeout`):
- `recompute.py`: the ADR rules written out, with the thresholds asserted equal to the config;
- `integrity.py`;
- `extension_p.py`;
- a field-by-field comparison with `analysis.json` (`cmp.txt`);
- the restart reconstruction (`restarts.txt`) and the 8K/4K sealed read (`sealed_8k4k.txt`).

**My own error, kept on record:** `integrity.py` first failed to serialise a dict with tuple keys; I changed the key format and reran it.

## 1. Recomputation, item by item
**Field-by-field comparison with `analysis.json`: 0 mismatches.** I compared, for every cell type: class, successes of evaluated cells, one-sided 95% Clopper–Pearson bound, n_A, n_G, (A, G, Q) state, combination number, A5-D and A6 accuracy medians, ratio, regime, convergence status and tags, the four d values (exact), ADDRESS STABLE, LM reduced, failure counts per condition, the 512-exposure class, condition 6 deciding any cell, and the paired d, p and pairs.

| Cell type | successes / evaluated, bound | class | n_A, n_G | (A, G, Q), combination | A5-D, A6 median, ratio | convergence |
|---|---|---|---|---|---|---|
| 8K/16K | 10/10, 0.741 | RELIABLE | 0, 0 | H H H, 5 | 0.999, 1.000, 0.999 | CONFIRMED |
| 8K/8K | 10/10, 0.741 | RELIABLE | 0, 0 | H H H, 5 | 0.997, 1.000, 0.997 | CONFIRMED |
| 8K/4K | 2/10, 0.037 | FAILS | 0, 8 | H F F, 7 | 0.981, 0.998, 0.983 | NOT CONFIRMED (NOT SHOWN) |
| 8K/2K | 0/10, 0.000 | FAILS | 2, 8 | F NR F, 8 | 0.863, 0.951, 0.907 | NOT CONFIRMED (NOT SHOWN) |
| 2K/4K | 10/10, 0.741 | RELIABLE | 0, 0 | H H H, 5 | 1.000, 1.000, 1.000 | CONFIRMED |
| 2K/2K | 10/10, 0.741 | RELIABLE | 0, 0 | H H H, 5 | 1.000, 1.000, 1.000 | CONFIRMED |
| 2K/1K | 10/10, 0.741 | RELIABLE | 0, 0 | H H H, 5 | 0.993, 1.000, 0.993 | NOT CONFIRMED (NOT SHOWN) |
| 2K/512 | 0/10, 0.000 | FAILS | 0, 10 | H F F, 7 | 0.916, 0.961, 0.952 | NOT CONFIRMED (NOT SHOWN) |

Every cell type is REFERENCE NEAR CEILING, and no draw is NOT_EVALUATED. The 512-exposure classes are RELIABLE except 2K/1K (UNRELIABLE), 8K/4K, 8K/2K and 2K/512 (FAILS); all match.

**Lines — all MATCH:**
- Line A: 0.5 H, 1 H, 2 H, 4 F → L_A 2, ℓ₁ 4 (FAILS).
- Line G: H, H, F, F → L_G 1, ℓ₁ 2.
- Line Q: H, H, F, F → L_Q 1, ℓ₁ 2 (FAILS).
- No line is NON-MONOTONE. At load 2, Line Q holds in series S only (slots 1,024).

**Headline:** step 5 MATCHES. Mine reads "OVERLOAD UNRESOLVED AT **2** — CONVERGENCE NOT CONFIRMED (NOT SHOWN); ADDRESSING QUALIFIED UP TO 1"; the printed text has "AT **ℓ₁**" (see section 3d).

**Everything else — all MATCH:**
- which line fails at ℓ₁: series M, LINE G FAILS (A HOLDS);
- hypotheses: H23-A supported, H23-G supported, H23-O not supported, H23-P not supported;
- lane licence: loads [0.5, 1.0];
- X8: not triggered (L_Q = 1, step 5), equal to `x8/gate.json`;
- penalty against A0: 8K/16K d 0, p 1, 10 pairs; 8K/8K d 0, p 1, 10; 8K/4K d −1, p 1, 10; 8K/2K d 0, p 1, 10; all NOT DISTINGUISHED;
- false-negative table: one series 0.736 / 0.914 / 0.965 / 0.996; both 0.542 / 0.835 / 0.932 / 0.991; L_Q ≥ 2 about 0.16 / 0.58 / 0.81 / 0.97.

## 2. Convergence and the extension refusal (c)
**P recomputed by hand.** `extension_p.py` rebuilds P from the run's timing rates and its ledger, following section 5.1 item 2:
- charged Stage R base hours 4.0015, plus 2.1516 for generation, gates and the 2.0 h analysis/report allowance;
- the main grid at each type's T, the extension rounds and X8 with its calibration at T = 16,384;
- six workers, quiet rates.

It reproduces the recorded decisions exactly: 8K/4K **55.609 h > 55 → refused**; 2K/1K 42.698 granted; 8K/2K 52.026 granted; 2K/512 53.127 granted. The order (ascending load, M before S, continuing after a refusal) follows the rule. The 8K-fact type 8K/2K was granted after 8K/4K was refused because its rates at 2,048 slots are lower. P includes X8 at its ceiling, which never ran. So **"EXTENSION REFUSED (BUDGET)" follows the registered rule.**

**Stage R curves of 8K/4K** (sealed; m_P / m_H by exposures 512 → 16,384):
- A5-D, calibration draw 1, m_H: 0.867, 0.889, 0.893, 0.901, 0.913, 0.912.
- A5-D, calibration draw 2, m_H: 0.867, 0.891, 0.914, 0.925, 0.925, 0.927.
- A6 is flat at about 0.998.

No base-ladder plateau: e = 2,048 fails on draw 2's m_H step of +0.0112, and e = 4,096 fails on draw 1's m_H step of +0.0121. The 8,192 → 16,384 steps are all ≤ 0.0021. So with the extension, e* = 8,192 (T = 16,384) was likely if the next step stayed within 0.01; unknown, because it did not run. 2K/1K, 8K/2K and 2K/512 were extended and still NOT SHOWN at the extended ceiling.

**Counterfactual.** On the registered draws, 8K/4K's d values are A5-D P +0.0034, A5-D H +0.0032, A6 P +0.00003 and A6 H +0.00006, all within 0.02. Had 8K/4K been SHOWN, it would be CONVERGENCE CONFIRMED and the headline would be step 6, **OVERLOAD NOT QUALIFIED AT 2; ADDRESSING QUALIFIED UP TO 1**. The UNRESOLVED therefore comes only from NOT SHOWN, caused by a refusal by 0.61 h that was driven partly by X8's reserved budget. The report states NOT SHOWN but neither the counterfactual nor the margin. The rule says a failure under NOT SHOWN reads UNRESOLVED, so the label is right; the outcome record should state both.

## 3. Integrity
**(a) Cells and identity: PASS.**
- 200 plan items; 200 distinct labels; 200 cell directories, none outside the plan; all with status `ok`; 10 draws × each (cell type, arm) of the grid.
- Each cell's seed set is `p10is0-draw-d` (no replaced draw), and its initialisation is 330001 for A6 and odd draws, 330002 for even draws, as the registered rule says.
- Every train record's label, `init_seed`, `seed_set` and planned last update equal the plan item; `end_update` equals the plan's updates; every snapshot hash it lists equals the `model.pt` on disk; the platform record shows one thread.
- One finished segment per cell.
- All 75 frozen inputs equal their freeze-record hashes now, and `durations.json`'s code identity equals the freeze inputs. The cell records carry no code identity of their own: identity was enforced at run time by the worker guard (exit 75 on a difference), and no identity pause appears in any task log.

**(b) Ledger, caps and restarts: PASS on the outcome, with an engineering defect to disclose.**
- The ledger totals 23.39 h against the registered cap of 113.01 h (main 17.09 h against a main stage cap of 61.15 h). The main manifest records one invocation only, 2026-11-20 05:36Z → 22:41Z, COMPLETE, 80 tasks, no failed record.
- But main started at **2026-11-19 13:03Z** (first task log). Killed invocations are evident from the set-aside directories at 2026-11-20 03:28Z and 05:36Z: one ran until it was killed before 03:28Z, and one ran from 03:28Z until the outage (22:33 local = 03:33Z). The driver charges the ledger and writes the manifest history only when an invocation returns, so these about 14.5 h of main are **not in the ledger or the manifest**. Main's real wall time is about 31.5 h, and the total about 38 h: still under both caps. **The cap was therefore not enforced across killed invocations.**
- **Resumption was not selective:** 88 results were written before 03:28Z and never rewritten (records are written once, exclusively); every other cell ran to completion in the last invocation.
- The 6 cells caught mid-run were restarted from update 0, and each killed attempt is kept under `incomplete/` (12 directories). Their per-update records are an exactly identical prefix of the final run's records: 527,604, 523,800, 276,996, 285,101, 275,106, 277,403 and about 30,000 records respectively, all fields but wall time and RSS. No failed record exists.

**(c) The extension refusal:** see section 2. It follows the rule, and it changes the headline from step 6 to step 5.

**(d) Wording that goes beyond the rule, or falls short of it:**
1. The headline prints the template symbol "AT ℓ₁" instead of the load. The record should read "AT LOAD 2 (ℓ₁)".
2. **"COLLAPSE-FREE: 0 of 0 counted cells never had a collapse onset"** is printed for every cell type as if measured. The collapse onsets were never computed: the registry has no onset field. Section 6.7 requires COLLAPSE-FREE k of n, so this annotation is **missing**, not zero.
3. H23-G "supported" is read at an ℓ₁ that is UNRESOLVED. The rule allows it, but the record should say that the reading is at an unresolved break.
4. The licence lists loads; the licensed cell types are 8K/16K, 2K/4K, 8K/8K and 2K/2K, all REFERENCE NEAR CEILING and CONVERGENCE CONFIRMED. 2K/1K, where Line Q holds in series S only, is not licensed.
5. The RATIO ABOVE 1 definition line is printed although no cell type carries the tag. Harmless.

## What the outcome record must disclose
- **ℓ₁ = 2.** The UNRESOLVED is solely due to 8K/4K's extension being refused by 0.61 h (P 55.61 h, B = 55, X8's reserved hours included). On the same cells a SHOWN 8K/4K would read **NOT QUALIFIED AT 2**.
- The 8K/4K calibration curves narrowly missed the 0.01 step twice (+0.0112, +0.0121).
- The extended types 2K/1K, 8K/2K and 2K/512 stayed NOT SHOWN at 16,384 exposures.
- **The ledger understates the charged time by about 14.5 h** of killed main invocations (not charged, not in the manifest history). The run stayed within its caps.
- The COLLAPSE-FREE annotation is missing, not 0 of 0.
- E3 (the checker copy excludes P10-I-R's files; the definition of RATIO ABOVE 1) remains PENDING LEAD REVIEW.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
