# Independent check: ADR-0021 §24 draft, "extension of the load calibration"

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**
Model: Claude Opus 5.5 (`claude-opus-5-5`), run as the auditor. I did not write the draft, its analysis script or any S1 code. Date 2026-11-15 (UTC).

**Verdict: READY SUBJECT TO the edits listed in §8.** There is no blocker. There are six majors: four are text edits I give paste-ready, and two (M4, M6) are scientific points marked PENDING LEAD REVIEW. Nothing in the extension may run until the edits are recorded and the implementation audit of ruling 9 is done.

## 0. Scope, inputs, environment

- **Spec:** `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` in worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-s1`, HEAD `2d11953`. I read §5, §8 (all of it), §10, §11, §15, the Addendum, §22, §22.1 and §23. Code read: `studies/p10s1/{calibrate,classes,core,train,budget}.py`, `studies/p9/data.py` (TrainingStream), `studies/p9/train.py` (rng_state/restore_rng) and `studies/p9/core.py` (chance interval, Fano bits).
- **Draft:** `AMENDMENT_LOAD_SEARCH.md`, `load_curve_analysis.py` / `.out` (this folder). The draft predates the lead's rulings 1–9, so I check it against them.
- **Raw data (read-only):** `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c` (eval.json, train.json, snapshot.json, `calibrate/manifest.json`), and `results/p10s1-calibration-2026-11-15/ledger_after_calibration.json`.
- **My scripts:** all in this folder; none imports `arborlm.*`, `studies.*` or the drafter's script.
  - `audit_curves.py` → `audit_curves.out`, `audit_curves.json`. It recomputes i from the counts, with my own chance interval and Fano formula.
  - `audit_extrapolate.py` → `audit_extrapolate.out`: six curve families, per view, on the candidate grid.
  - `audit_backtest.py` → `audit_backtest.out`: hold-out test of the families. It execs `audit_extrapolate.py` from this folder for the fit functions.
  - `audit_costs.py` → `audit_costs.out`: costs from measured rates.
  - `audit_fund.py` → `audit_fund.out`: cap needed for row combinations.
- **Commands** (run from this folder):
  - `python3 -I audit_curves.py <run_dir>`
  - `python3 -I audit_extrapolate.py`
  - `python3 -I audit_backtest.py`
  - `python3 -I audit_costs.py <run_dir>`
  - `python3 -I audit_fund.py`
  - Hash checks: `shasum -a 256` on `snapshots/u0065536/{model,optimizer}.pt` of the four X8/Y4 calibration cells, plus an inline `python3 -I` reading the D-OQ eval records (the command is shown in the session).
- **Environment:** system Python 3.15.1 with the standard library only. The locked uv environment has no numpy or scipy, so the fits are grid searches with closed-form inner least squares. No training, no new runs, no network, no commits, and nothing written outside this folder.

## 1. Task (a): the curves, recomputed

- **Chance intervals.** My implementation gives [34,100], [192,325] and [894,1159] at 2,048 / 8,192 / 32,768, the same as G2.
- **Curves.** Every i(u) of the 16 load cells, per draw and panel, is in `audit_curves.out` Part A. Every entry of the draft's §24.0.1 table matches mine to the stated precision: levels at 8K, 16K, 32K and 65K, increments, and ratios.
  - Spot checks: 4K/L8 at 65,536 is 1.887–1.943. 16K/L4 is 3.495–3.540. The last increments are 0.290–0.330 (4K/L8) and 0.638–0.708 (16K/L4). The ratios are 0.546–0.572 (4K/L8) and 0.519–0.544 (16K/L4).
- **Draft §24.0.2.** Items 1–5 are confirmed. 4K/L4's i\* is 4.063–4.116 at 65,536, and its d(49,152) is 0.332–0.413. The draft's item 5 artefact is real: by the letter of §8.2, every cell is "plateaued and loaded" at 1,024–8,192 updates, before it learns (Part C).
- **Information budget (§24.0.4).** Recomputed and correct: 197,633 and 787,457 parameters; retained bits 67.0k / 62.7k / 48.3k / 230.6k / 194.7k.
- **The rule as coded.** `classes.View.plateaued` is i\*(run) − i\*(run//2) ≤ 0.10 + 1e-12. i\* is the running maximum over snapshots ≤ limit, so it is monotone. `loaded` adds i\*(run) ≤ 4.0 + 1e-12. `calibrate.loaded_at_slot_count` requires all four views. The draft's "LOADED AT U" is this definition with U in place of U_run, and it is used correctly.
  - Every candidate's U/2 (65,536, 98,304, 131,072, 196,608, 262,144) is a snapshot under the draft's grid, so `run//2` never falls between snapshots.
  - For X8 and Y4, i\*(131,072) − i\*(65,536) must combine the calibration's eval records (u ≤ 65,536, in the calibration run directory) with the extension's records (new run directory). The draft does not say this; see edit E6.
- **Discrepancy D1 (draft, minor).** The draft says that under G, 4K/L8 first meets the rule at 262,144 "(increment 0.09–0.10: on the edge)". The drafter's G works on per-draw curves averaged over the two panels. §8.2 is per panel.
  - Per view, draw 2 Panel B under G has d(262,144) = 0.330 × 0.554² = **0.101 > 0.10**. Under G, the cell (all four views) is therefore first loaded at **393,216**, not 262,144.
  - This does not change the design. It does move the G-based expectation one stage later.

## 2. Task (b): extrapolation stress test (NOT measurements)

**Families**, fitted per view on snapshots ≥ 16,384 (Hill from 4,096):
- G: the draft's rule, the last ratio held constant.
- G-sqrt: the draft's S.
- Power law: i = c − A·u^−α.
- Saturating exponential: i = c − B·e^(−u/τ).
- Hill: logistic in log u.
- Log-linear: no deceleration.

I also used a shape-transfer check, i_L8(2u) ≈ s·i_L4(u). The data support it: s = 0.53/0.50/0.50 and 0.58/0.50/0.49 over three overlaps.

**Hold-out backtest** (`audit_backtest.out`): fit up to 32,768, then predict d(65,536). Mean signed error (predicted − observed; positive means a pessimistic family):

| Family | 4K/L4 | 4K/L8 | 4K/L16 | 16K/L4 |
|---|---|---|---|---|
| G | +0.09 | +0.15 | +0.07 | +0.54 |
| power | +0.14 | +0.16 | +0.03 | n/a |
| sat-exp | +0.02 | +0.03 | −0.04 | n/a |
| Hill | −0.15 | −0.15 | −0.10 | −0.43 |

- G and the power law are **pessimistic**: ratios have kept falling, so decay has been accelerating.
- Hill is consistently **optimistic**, and I treat it as an outer bound only.
- The saturating exponential is the most accurate one step ahead at 4K. It cannot be backtested at 16K, where there are only two points in the window.

**Ranges** (first candidate passing §8.2 on all four views; U_L under ruling 2 = the second of two consecutive passes; full per-view detail in `audit_extrapolate.out`):

| Cell | First pass | Level | U_L (ruling 2) | i > 4.0? |
|---|---|---|---|---|
| **4K, load 8 (X8)** | 131,072 (sat-exp) / 196,608 (shape transfer) / 262,144–393,216 (G, power) / 786k–1.5M (G-sqrt) | 1.94–2.31 (G-sqrt 2.5–2.6) | 196,608 (sat-exp) – 393,216 (G) – 524,288 (power, 3 of 4 views) | never |
| **4K, load 6 (X6)**, synthetic: interpolated between L4 and L8, two ways | 131,072 (sat-exp, Hill) / 196,608–262,144 (G, power) / 393k–786k (G-sqrt) | 2.6–3.1 (G-sqrt 3.0–3.4) | 196,608–393,216 (G-sqrt 524k–1M) | never |
| **16K, load 4 (Y4)** | 196,608 at 3.61–3.65 (sat-exp); 131k–196k at 3.56–3.62 (Hill, optimistic) | — | 262,144 (= the ceiling) under sat-exp and Hill | **crosses 4.0 at 196,608–262,144 under G and power (asymptote 4.25–4.31)** → EXCLUDED |
| 4K, load 4 | — | 4.13–4.68 | never | already > 4.0 (measured) |
| 4K, load 16 | 131,072 at 0.8 (sat-exp) to never (G, draw 2) | 0.8–2.8 | not identified | never |

**Answers to (b):**
1. **"4,096 slots at 8 facts per slot loads near 2.2 bits by about 262,144 updates."**
   - The level is about central to slightly high. The plausible range is 1.95–2.3; a floor near 2.05 follows if the store keeps at least the ~67k bits already retained at load 4.
   - The timing is about central for the *first* pass. G and power, which the backtest shows to be pessimistic, put it at 262k–393k; sat-exp and shape transfer put it at 131k–196k.
   - Per view, G gives 393,216, not 262,144 (D1).
   - **Under ruling 2, U_L is most likely 262,144–393,216** (range 196,608–524,288). If the decay relaxes as under G-sqrt, the cell is not loaded within the 524,288 ceiling. The backtest gives no support for that, but it cannot be excluded.
2. **Load 6 is a sensible hedge.** It is predicted to pass about one stage earlier than load 8, at 2.6–3.1 bits, which leaves a margin of ≥ 0.9 bits below 4.0. It costs at most about 1,380 s of wall per stage in the search.
   - Its costs come later. If selected, it adds new cells (24K/4K, 24K/16K, R2 at 24K/64K), a U_P′ calibration, a stream verification (ruling 8), and about 1.0–1.1 h more registered time than the F\*=32,768 row at the same U_L (`audit_costs.out`).
3. **Could load 4 at 16,384 slots ever be loaded?** Yes, but only if the 16K store saturates near 3.6 bits (about 14.5 bits per slot).
   - That is the sat-exp/Hill branch. The cross-cell evidence at 4K (loads 4 and 8 converge to about 17–18 bits per slot under G) points instead to an asymptote of 4.25–4.4, which is above 4.0.
   - I rate it the less likely branch, but not negligible.
   - Two stages (to 196,608, about 0.8 h of wall) settle it: by then the cell has either crossed 4.0 (rule 3a) or passed d ≤ 0.10. Under ruling 2, Y4 can be loaded only if it already passes at 196,608, because U_L would then be exactly the 262,144 ceiling.
4. **A cheaper or more informative set?**
   - Within the same ceilings I would keep X8, X6 and Y4.
   - Adding load 5 (20,480 facts; predicted 3.4–3.7) buys little and sits closer to 4.0. Load 16 is costlier and gives no better row.
   - The most informative single cell is **Y4**. It alone decides whether S1 can reach any capacity outcome (§8.4 needs a CAPACITY STEP in each transition). The 4K cells can only yield a one-transition result (ruling 1).
   - I recommend running Y4 regardless (edit E1 keeps this). More 4K loads would not change what the study can conclude.

## 3. Task (c): the stopping rule, the margin, and continuation

**Rulings 2, 4 and 8 are not in the draft.** Rules 1, 2, 3b, 3c and 5 and case (c) must be rewritten (major **M1**, edit E1).

**Two consequences of ruling 2 that the draft does not state:**
- A cell can only be LOADED at a candidate that has a predecessor candidate. The first possible U_L is 196,608.
- **The effective ceiling for a first pass is the penultimate candidate:** 393,216 at 4,096 slots and **196,608** at 16,384 slots.

**Rule 3c needs restating under ruling 2.** The draft's "one-eighth" rule bites only at the penultimate candidate (it excludes when d > 0.237 there). Under ruling 2, a cell that does not pass at the penultimate candidate can never have two consecutive passes. The correct, simpler and assumption-free form is "not passing at U_{max−1} ⇒ EXCLUDED". It saves the last stage with no ratio assumption, and E1 replaces 3c with it.

**Is every branch determined by the calibration draws alone? Mostly yes; four gaps:**
- **(i) A run that fails** (crash, the trainer's non-finite refusal, a stage-cap refusal mid-stage) has no rule. E1 adds: the run is kept, never re-run, and its cell is EXCLUDED with the reason.
- **(ii) A cell that passes at U_k and fails at U_{k+1}** (possible only through noise in d, or i\* passing 4.0) has no stated continuation. E1 adds: the count restarts and the cell stays OPEN if any candidate remains.
- **(iii) "A stage that would pass its cap"** needs a stated projection: measured seconds per update of each run × the stage's updates.
- **(iv)** Which eval records a view reads (both run directories; E6).

With these four gaps closed, no branch leaves a choice.

**Wrong early stop?**
- Rule 3a is exact, because i\* is a running maximum and so can never decrease.
- The restated 3c is exact under ruling 2.
- The only residual risk is a view that would plateau only after the ceiling, which is the ceiling's intent.

**Needless run to the ceiling?**
- It is bounded: at most 2.03 h of wall for all five stages, on the draft's rates (reproduced in §5).
- Y4 stops by 196,608 in every family: it either passes 4.0 (G, power) or passes d at 196,608 (sat-exp).

**Continuation (checked in code and on disk):**
- `TrainingStream.batch(update)` is documented and implemented as a pure function of the 1-based update index (epoch permutation seeded by `order_seed`, epoch). The cache only saves time. A run continued from 65,536 therefore draws exactly the batches an uninterrupted run would.
- `Trainer.resume` restores the model state (with a frozen-backbone equality check), the AdamW state dicts (including `step`, so bias correction continues), the movement counters, the update counter, and the Python and torch global RNG.
- `job.updates` affects only the default snapshot marks and the optimizer-keep set. The extension must pass both explicitly (the draft keeps the optimizer at every candidate, which is right).
- On disk, only `u0065536` holds `optimizer.pt` in each calibration cell. For X8 d1/d2 and Y4 d1/d2, I verified that the SHA-256 of `model.pt` equals both `train.json` `snapshot_sha256["65536"]` and `snapshot.json` `model_sha256`, and that the SHA-256 of `optimizer.pt` equals `snapshot.json` `optimizer_sha256`. All four match.
- **Gap (minor, E6).** The draft's check (a) names only the model hash. Its check (b), `restore_check` under the new code, proves that the new code is self-consistent, but not that the new code's training step equals the calibration code's step. The calibration ran under source hash `9cb811fb…`; the extension needs new code.
  - Add: re-train X8 d1 from 0 to 512 updates under the extension's code and require its model hash to equal the calibration's `snapshot_sha256["512"]`. This costs about 6 s.
  - Or, equivalently, show that the training-path sources (`train.py`, `model.py`, P9/P9-I data and train modules) are hash-identical to the calibration's.

**The two-stage margin itself.**
- Under every family that fits the 4K data, d falls by a factor of about 0.6–0.75 per candidate (G/power) or much more (sat-exp/Hill) between the first and second pass. A first pass at 0.088–0.098 becomes 0.05–0.08 at U_L, which is a margin of about 0.02–0.05 in d.
- The draw-to-draw spread in d is about 0.04 at 65,536 for X8 (0.290–0.330) and should shrink in proportion to d.
- The margin is therefore adequate for data-draw variation. It does not cover initialization-seed variation, which the calibration never sampled (one seed, 2191); see §7.

## 4. Task (d): the decision rule with a loaded 4K→16K row

**Still defined.**
- MU and MC at U_P′. The MC readout of the smaller cell is at m·U_P′ ≤ 6·U_P′ = 98,304 ≤ U_L, so it is never MC-SHORT.
- SAT: i\* of the smaller cell up to U_L.
- The fifth condition: Δ_SAT − 2·[i\*(U_L) − i\*(U_L/2)] ≥ 0.5.
- CEILING at U_P′, where the smaller cell is about 1 bit: unreachable.
- REF: for F\*=32,768 this is the registered R2 32K/64K at 8,192. For 24,576 it is the new R2 24K/64K.
- DEP at every snapshot (§22 (g)).
- Cut 3, the cut order, the seed block and the efficiency line.

**Edits needed:**
- (i) **Efficiency U_run.** The efficiency line's right-censoring bound for 32K/4K (and 32K/16K) must stay at the registered 49,152 (and 32,768). It must not be the train record's `run_updates`, which becomes U_L. Minor, E7.
- (ii) **The larger cell is not plateaued.** 32K/16K at 4·U_P′ = 65,536 is measured *not* plateaued (d = 0.145–0.159). This matters only for NULL/FLAT, which are unreachable here; state it.
- (iii) **U_P′ needs a new revision.** Setting U_P′ = 16,384 for a row of revision 4 (B1's cells), changing run lengths and snapshot grids, and taking B1 off the capacity line all fall outside §8's opening list of what may change after calibration ("Anything else is a new revision"). The amendment must be adopted as **revision 5** under §11's process (confirmation review, then the lead's decision under the delegation), not as an amendment of the calibration. Major **M5**, governance; E8.

**Fairness.** The smaller cell runs up to 32·U_P′; the larger runs 4·U_P′.
- Δ_MU compares equal updates.
- Δ_MC compares matched cost, with the cheaper (smaller) cell read later.
- Δ_SAT and Δ_FULL compare the larger cell at U_P′ (or its best up to 4·U_P′) against the smaller cell's *best over up to 32× more updates*.
- Every inequality in run length works *against* CAPACITY, so the larger cell is not under-trained in a direction that favours a positive. The asymmetry would matter only for NULL (both cells plateaued, |Δ_FULL| < 0.25), which is unreachable because Δ_MU is about +3 bits.

**What the row can yield** (F-OQ, from calibration levels: the smaller cell about 1.0 bit at 16,384 and about 2.0–2.3 at U_L; the larger about 4.1–4.2 at 16,384):
- Per replicate:
  - NOT_EVALUATED (REF), DEPENDENCE_FAILED or PANEL-DISAGREE;
  - **CAPACITY**, if the smaller cell is loaded on both panels;
  - **GAIN WITHIN BUDGET ONLY**, if it is not loaded.
- CEILING, REVERSED, BEHIND, NULL, FLAT and UNRESOLVED are arithmetically out of reach (Δ_MU ≈ 3, Δ_SAT ≈ 1.9, a_use(4N) ≈ 0.91).
- Step class: CAPACITY STEP, GAIN WITHIN BUDGET, NOT REPLICATED, NOT_EVALUATED, DEPENDENCE_FAILED or MIXED. **Never NO GAIN, REVERSED or NOT LOADED.**
- The row cannot produce a negative. The draft's provenance argument (3), "finding a row where the test can be run does not favour either answer", is **false for this row** (major **M4**, E5). Whether it reads CAPACITY STEP or GAIN WITHIN BUDGET depends almost only on whether the smaller cell's plateau holds in all 5 replicates.
- **T-OQ, H8 and F-OQ-IVF.** Their smaller cells' loadedness at U_L is not predicted by anything the extension runs (F-OQ only). T-OQ is the SUBLINEAR arm the milestone reading needs, and it is half the row's cost. Major **M6**, PENDING LEAD REVIEW. Option: add T-OQ at 32K/4K on both calibration draws to the search, from zero. That is roughly 2× X8's wall per stage, which doubles E4/E5 walls to about 2,860 s.

**What the study can and cannot conclude with 16K→64K NOT TESTED** (ruling 1, §22 m13):
- No arm can be CAPACITY_SUPPORTED, so CAPACITY-POSITIVE is unreachable.
- CAPACITY-NEGATIVE is unreachable too: row 4(a) needs a NO GAIN or REVERSED step in every transition, and L1 cannot give one; 4(b) needs a SUPPORTED arm.
- Arm classes can reach CAPACITY_ONE_TRANSITION.
- **The outcome is not stated anywhere.** §8.7 row 5's first clause fails (L1 is not NOT LOADED) and its second refers to the human lead's direction. The only other row that applies is row 6, CAPACITY-INCONCLUSIVE ("ONE TRANSITION ONLY (4K→16K)" / "NOT_TESTED_BY_LOAD (16K→64K)"). E3 fixes it.
- The study could conclude, for F-OQ at one transition: "at 4,096 slots the store saturates at about 2 bits per fact on 32,768 facts, and quadrupling the slots raises useful information by at least 0.5 bits per fact under matched updates, matched compute and against saturation, in 5 of 5 replicates". It would also give the dense control's labels at 32K/16K and the arm-by-arm step classes.
- It could not conclude anything about capacity *scaling* across two transitions, the storage half of milestone question 1, or anything at 65,536 slots.
- The positive at one transition is close to foregone given the calibration: 32K/16K already reaches 4.1–4.2 bits at 16,384 updates, while 32K/4K is predicted to saturate near 2.

## 5. Task (e): costs, recomputed

**Rates.** Seconds per update from `calibrate/manifest.json` (MAN: task seconds, including the calibration-grid evaluations and start-up; the draft's basis) and from `train.json` wall (TRN: training only).
- F-OQ (MAN / TRN): 4K/L8 0.01090 / 0.00933; 4K/L6 (interpolated) 0.01052 / 0.00933; 16K/L4 0.02255 / 0.01864.
- H8@4K: 0.00820. D-OQ@16K: 0.0245. D-OQ@64K: 0.0910.

**Extension stages: the draft's table is reproduced exactly** (MAN; TRN in brackets):

| Stage | To | Wall | Cumulative |
|---|---|---|---|
| E1 | 131,072 | 1,478 s | 0.41 h [0.34] |
| E2 | 196,608 | 1,478 s | 0.82 h |
| E3 | 262,144 | 1,478 s | 1.23 h |
| E4 | 393,216 | 1,429 s | 1.63 h |
| E5 | 524,288 | 1,429 s | 2.03 h [1.70] |

- Worker-seconds of the six runs to their ceilings: 29,900 (8.3 h) [25,673].
- Row-U_P step: 0.51 h is the 16K row's (F-OQ 65K/64K to 32,768 updates ≈ 1,820 s). The 24K row's is about 0.16 h. The draft conflates them; minor, stated in E4.
- Dense grid: 0.41 h per round (D-OQ 32K/64K at 16,384 updates ≈ 1,462–1,497 s), 1.22 h for three rounds. Confirmed.
- Worst case 3.76 h charged against the 7.5 h ceiling.
- Under ruling 2 the expected search is one stage longer than the draft's 2.3 h expectation (about +0.4 h).

**Registered rows, added charged hours** (5 replicates, six workers, perfect packing; T-OQ = 2× F-OQ unmeasured; D-OQ@4K assumed 0.5× its 16K rate; added evaluations not included). MAN [TRN]:

| U_L | 131,072 | 196,608 | 262,144 | 393,216 | 524,288 |
|---|---|---|---|---|---|
| L, F\*=32K, U_P′=16K | 1.44 [1.28] | 2.06 [1.82] | 2.68 [2.35] | 3.92 [3.43] | 5.17 [4.51] |
| L, F\*=24K, U_P′=16K | 2.54 | 3.15 | 3.75 | 4.96 | 6.16 |
| L, F\*=24K, U_P′=32K | 3.84 | 4.44 | 5.05 | 6.25 | 7.46 |
| 16K row, U_P′=16K | 4.58 | 5.77 | **6.96** | — | — |
| 16K row, U_P′=32K | 6.77 | 7.96 | **9.15** | — | — |

These agree with the draft's (b) table to ±0.1 h.

**The draft's base is stale (major M3).** The draft's cap column assumes 5.6 h remaining for the unchanged study, the pre-calibration §10.3 projection of 15,440 s per replicate.
- Recomputed from the calibration's measured rates, the unchanged registered training is **19,463–21,570 s per replicate** (4.5–5.0 h). With §10.3's allowances (evaluation 1.0, gates etc. 0.4, both seed blocks) the remaining time is **6.65–7.21 h**.
- The main differences: D-OQ at 65,536 slots (0.09 s per update; 2,972 s per replicate against about 1,500 projected), H8 (2,651 against 1,540) and F-OQ (4,403 against 3,540).
- **The unchanged study alone then needs 17.6–20.2 h under the twofold rule (> 16 h)**, with or without this amendment. That is a cap raise within the recorded delegation, but it should be stated.

**Cap needed** (= 1.57 + extension + 0.45 + 2 × (remaining + added); `audit_fund.out`; extension 2.3–3.8 h):

| Configuration | Cap needed |
|---|---|
| 4K row alone, U_L 196,608 → 524,288 | 21.3–24.4 → 26.6–30.6 h: **fits under 32 at every U_L** (MAN with the 3.8 h extension: 30.6 h at 524,288) |
| 16K row alone (under ruling 2 its U_L can only be 262,144), U_P′=16,384 | 29.5–34.2 h: fits on TRN only |
| 16K row alone, U_P′=32,768 | 33.3–38.5 h: does not fit |
| **Both rows** | **33.1–46.4 h: never ≤ 32 h on either rate set** |

The draft's sentence "both together only when their added cap is at most about 16.5 hours (for example L at 262,144 with the 16K row at 131,072 …)" does not hold: 131,072 is not a possible U_L under ruling 2, and the base is 1.1–1.6 h higher. **Consequence: in the only branch where S1 could reach a capacity outcome (both transitions loaded), the fundability rule returns the work to the human lead.** Stated in E4.

**Total machine time:**
- Extension: ≤ 3.8 h of wall (about 12 worker-hours) including the dense grid.
- Registered: about 4.5–5 h of training wall plus about 1.4 h of other stages, plus 1.4–5.2 h for a 4K row (plus 4.6–9.2 h for a 16K row).

## 6. Task (f): the dense control's rate grid

**Recomputed from the D-OQ eval records** (minimum Panel A accuracy over two draws):
- At 16,384 slots: 0.091 / 0.443 / 0.998 at U_P for lr 0.001 / 0.003 / 0.01.
- At 65,536 slots: 0.044 / 0.062 / 0.294 at U_P, and 0.054 / 0.145 / 0.969 at 16,384.
- These match the draft. Accuracy rises with the rate everywhere, so the best rate is not bracketed. All 12 runs completed, with finite and decreasing losses.

**Is the rule sound?**
- **Monotone in the control's favour, stated correctly.** It can only strengthen D-OQ. Adding a rate never removes the old best from the selection, and the selection takes the maximum.
- **Not symmetric.** Memory arms keep 0.003 untuned. A stronger control makes DENSE AHEAD and DENSE FASTER easier. That is conservative for the positives but **makes CAPACITY-NEGATIVE (b) and EFFICIENCY-NEGATIVE (second clause) easier**. The draft's item 7 names the labels, not the negative outcomes. Minor; E9 states it.
- **At 16,384 slots the U_P accuracy is already 0.998,** so 0.03 will tie (within 0.02). The §22 M7 walk then decides by the faster learner: 0.01 is at 0.971 at 4,096 updates and 0.26 at 2,048. The higher rate will likely be selected for speed alone. That is legitimate under the rule, but its main effect is on DENSE FASTER (efficiency line), not on the capacity line.
- **Are 0.03 / 0.1 / 0.3 sensible for AdamW here?**
  - AdamW's per-coordinate step is about lr, independent of gradient clipping.
  - D-OQ's w2 is initialized at about ±1/√h. With h ≈ 4,000 / 16,000 / 64,000 (core.doq_hidden), that is ±0.016 / ±0.008 / ±0.004.
  - Steps of 0.1–0.3 are 10–75× that scale. Those rates will very likely be noisy or unstable, and probably below the best rate. Not non-finite, though: sigmoid gate, GELU, clipped gradients.
  - 0.03 is a reasonable next point.
  - The rule's stop (i) (the best rate is interior) should end the grid after the 0.03 or 0.1 round. The threefold spacing is fine.
- **Divergence rule.** It exists (rule 4: non-finite refusal, or chance-level accuracy at U_P or at the run length). Two gaps:
  - (i) A run that ends on the trainer's non-finite refusal raises in `run_job` and is written `failed`. The extension's driver must map that to "diverged" for the rate, not to an engineering stop. Minor, E9.
  - (ii) A rate that is above chance at U_P but collapses later is not "diverged". D-BEST reads its best snapshot, so the control is not weakened by a late collapse. Acceptable.
- **Cost.** 0.41 h per round, ≤ 1.22 h. Confirmed.

## 7. Task (g): provenance and bias

1. **No registered data enter.** The registered draws (210001–210401 bases, init seeds 2101–2105) have not been generated. Every branch of the search reads only calibration draws, so no registered observation can leak into U_L, the load, or U_P′.
2. **Selection at the threshold (regression to the mean).** U_L is a stopping time on the calibration draws: the first candidate (+1 under ruling 2) at which their noisy d falls below 0.10. Independent replicates at the same U_L have, in expectation, a larger d than the selected calibration views.
   - The two-stage margin addresses this. U_L is one candidate past the first pass, where every fitted family puts d about 0.02–0.05 below 0.10. That is larger than the calibration's draw-to-draw spread in d (about 0.01 at d ≈ 0.07).
   - **The margin does not cover initialization-seed variance.** Both calibration draws used init seed 2191, while the registered replicates vary both data and initialization. The calibration therefore under-samples the spread the registered "all 5" condition faces. The draw-1 seed block will measure this afterwards, but it cannot inform U_L. Minor; stated in E5.
3. **Design-level bias, which the margin does not address.** The search selects the row, U_L and (through the §10.1 U_P rule) U_P′. Together these make the positive step reachable, while the negatives are unreachable for that row (§4).
   - This is not statistical contamination, because the registered data are untouched.
   - But the claim "does not favour either answer" is wrong. For this row the registered run can only confirm or fail to replicate a positive step. E5 replaces the sentence.
   - The draft's limit (ii) (U_P′ helps Δ_MU and Δ_SAT) is correct and should stay.
4. **U_P′ choice.** U_P′ = 16,384 is where the larger cell reaches a_use ≥ 0.90 on the calibration draws, so the readout sits where the larger cell is nearly full.
   - With U_P = 8,192, Δ_SAT would be about 2.3 − 2.2 ≈ 0.1 and CAPACITY unreachable. The choice of U_P′ is what makes the row testable, and it should be said that plainly.
   - It is the §10.1 rule applied to a row it was not written for (M5).

## 8. Findings by severity, with paste-ready edits

**Majors**
- **M1.** The rulings are not applied: the two-consecutive-stage margin (2), return rather than fix-by-rule (4), the 24,576-fact stream test (8), and implementation, audit and rehearsal repeated (9). The stopping rule lacks a failed-run rule, a pass-then-fail rule and a stated projection. → E1, E2.
- **M2.** Case (c) fixes CAPACITY NOT TESTED by rule, against ruling 4. The outcome for the mixed case (one transition loaded, ruling 1) is not stated. → E2, E3.
- **M3.** The fundability projection uses a stale base (5.6 h against 6.65–7.21 h measured). Even the unchanged study needs more than 16 h. The "both rows" sentence is wrong, and both rows never fit under 32 h. → E4.
- **M4.** The provenance argument (3) is false for row L: no negative is reachable. The scientific value is one transition with a near-foregone F-OQ positive. → E5. **PENDING LEAD REVIEW:** whether a one-transition, positive-only row is worth 1.4–5.2 h (4K) of registered time.
- **M5.** The changes exceed §8's post-calibration list, so this must be adopted as a new revision (revision 5). → E8.
- **M6.** Loadedness is predicted for F-OQ only. T-OQ (the SUBLINEAR arm), H8 and F-OQ-IVF at U_L are unpredicted. **PENDING LEAD REVIEW:** add T-OQ at 32K/4K to the search, or accept that T-OQ may be GAIN WITHIN BUDGET by default.

**Minors**
- m1: D1, the per-view G statement.
- m2: the continuation check also needs the optimizer hash and a cross-code identity check (E6).
- m3: the views must read both run directories (E6).
- m4: the efficiency U_run for lengthened cells (E7).
- m5: 32K/16K is not plateaued at 65,536 (informational).
- m6: the dense grid's effect on the negative outcomes, and its failed-run mapping (E9).
- m7: the row-U_P cost line (E4).
- m8: running DEP at many more snapshots raises the chance of DEPENDENCE_FAILED. Informational, no change.
- m9: init-seed variance (E5).
- m10: §8.2's lack of a floor is noted (ruling 6); the extension reads only at ≥ 131,072, so it is moot here.

**Paste-ready edits**

**E1: replace §24.2 rules 1–5 with:**
> 1. **Pass at U.** A cell passes at candidate U if, on each of its four views, i\*(U) − i\*(U/2) ≤ 0.10 and i\*(U) ≤ 4.0 (`classes.View` with run = U; thresholds of §8.2 unchanged). i\* at a view is the maximum over every evaluated snapshot ≤ U of that cell and draw, from the calibration run directory for updates ≤ 65,536 and from the extension's run directory above.
> 2. **LOADED (the lead's ruling 2).** A cell is LOADED at candidate U_k if it passes at U_{k−1} and at U_k (both candidates of the list {131,072, 196,608, 262,144, 393,216, 524,288}); U_L = U_k. After stage E_k, if any cell of a slot count is LOADED, the search at that slot count stops with U_L = U_k; if X8 and X6 are LOADED at the same U_k, X8 is taken.
> 3. **EXCLUDED**, as soon as one holds: (a) i\* > 4.0 on any view at any snapshot; (b) the cell does not pass at the penultimate candidate of its slot count (393,216 at 4,096 slots; 196,608 at 16,384 slots), or has been read at its U_max without being LOADED; (c) a stage that would carry it was not started under §24.1's hour ceilings, the projection being each run's measured seconds per update in the calibration (or in the extension's previous stage, when available) times the stage's updates; (d) a run of the cell ended with status `failed` (any exception, the non-finite refusals included); the run is kept and never re-run.
> 4. **OPEN** otherwise. A cell that passed at U_{k−1} and does not pass at U_k is OPEN if a candidate remains, and its count of consecutive passes restarts.
> 5. **End at a slot count:** LOADED(F\*, U_L), or every cell EXCLUDED (NO LOADED CELL). The two slot counts end independently.
> 6. **Before stage E1:** the 24,576-fact stream, Panels A and B and G1 are verified by a test on calibration draw 1 (ruling 8); if this fails, X6 is dropped before any run and the drop is recorded.

**E2: replace §24.3 (c) with:**
> (c) **NO LOADED CELL at a slot count.** The extension's record (cells, last candidate read, the rule that closed each cell, all curves) returns to the human lead before the freeze. The lead does not fix CAPACITY NOT TESTED by itself (the lead's ruling 4). Until the human lead answers, nothing registered is generated.

**E3: add to §24.3 (a1):**
> **Outcome when only 4K→16K has a loaded row (the lead's ruling 1).** If the 16K→64K transition is NOT TESTED by the human lead's direction, no arm can be CAPACITY_SUPPORTED (§22 m13) and no CAPACITY-NEGATIVE is reachable; the capacity outcome is printed **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET (16K→64K)**, with the step classes of the 4K→16K transition and the arms' classes (CAPACITY_ONE_TRANSITION where it applies) printed beside it. It is not an overall capacity outcome and supports no reading of milestone question 1.

**E4: replace §24.3 (b)'s "cap needed" paragraph, and the fundability sentence "On the projection: … C_max = 40.", with:**
> The base is recomputed from the calibration's measured rates (not the §10.3 projection): the unchanged registered study needs about 6.7–7.2 h remaining (training 4.5–5.0 h on 5 replicates, plus §10.3's allowances), so the unchanged study alone needs about 17.6–20.2 h of cap under the twofold rule. Cap needed, with the extension at 2.3–3.8 h: the 4K row alone 21–31 h at any U_L up to 524,288; the 16K row alone (U_L = 262,144, the only value ruling 2 allows) 29.5–34.2 h at U_P′ = 16,384 and 33–39 h at 32,768; **both rows together 33–46 h, above C_max in every case** — if both slot counts are LOADED, the work returns to the human lead with the measured costs. The row-U_P step costs about 0.16 h for F\* = 24,576 and about 0.51 h for the 65,536-fact row. These are projections; the repeated rehearsal decides, with T-OQ measured first (ruling 7).

**E5: replace §24.6 "Why this does not bias…" item (3) and add to "Limits":**
> (3) The registered run judges loadedness on its own snapshots; a row found by this search can, for F-OQ, only yield CAPACITY STEP or GAIN WITHIN BUDGET (or NOT_EVALUATED / DEPENDENCE_FAILED / NOT REPLICATED / MIXED): Δ_MU is about +3 bits by the calibration, so NO GAIN, REVERSED and NOT LOADED are out of reach. The search selects a design in which a positive step is reachable and a negative is not; this is stated, not hidden.
> (iv) The calibration used one initialization seed for both draws; the registered replicates vary initialization as well, so the spread the "all 5" plateau condition faces is under-sampled. The two-stage margin covers the calibration's draw-to-draw spread in d (about 0.01 near d = 0.07), not the initialization spread.
> (v) Loadedness at U_L is predicted for F-OQ only; T-OQ, H8 and F-OQ-IVF are judged on their own snapshots with no prediction.

**E6: add to §24.1 "Continuation":**
> (a) also requires `optimizer.pt`'s SHA-256 to equal `snapshot.json` `optimizer_sha256`; (c) under the extension's code, X8 draw 1 is re-trained from initialization to 512 updates and its `model.pt` SHA-256 must equal the calibration's `snapshot_sha256["512"]`; otherwise the continued cells are run from zero. Views read both run directories as in §24.2 rule 1.

**E7: add to the (a1) table, "Efficiency line" row:**
> The efficiency line's U_run (right-censoring bound and cost bound) for 32K/4K and 32K/16K stays 49,152 and 32,768, never the longer training length.

**E8: header of §24:**
> This section changes items outside §8's post-calibration list (run lengths, U_P′ of a revision-4 row, snapshot grids, the capacity line's steps) and is therefore **revision 5** of ADR-0021, adopted by §11's process (confirmation review, the lead's decision under the delegation, recorded in §15).

**E9: add to §24.5:**
> A run that ends with status `failed` is a diverged rate under rule 4 (not an engineering stop). A stronger dense control makes DENSE AHEAD and DENSE FASTER easier and therefore makes CAPACITY-NEGATIVE (b) and EFFICIENCY-NEGATIVE (second clause) easier; the memory arms are not retuned.

**The lead's rulings, checked:**
- **Ruling 1:** consistent with §8.4 and m13; needs E3.
- **Ruling 2:** sound and adequate for data-draw spread (§3); needs E1.
- **Ruling 3:** the 32-hour cap suffices for the 4K row; not for both rows, nor reliably for the 16K row alone (§5).
- **Ruling 4:** needs E2.
- **Ruling 5:** coherent; L1 is B1 re-parameterised when F\*=32,768.
- **Ruling 6:** correct (§1).
- **Ruling 7:** necessary; T-OQ is about half of every row's cost.
- **Ruling 8:** E1 rule 6.
- **Ruling 9:** necessary; it also covers E6's cross-code check.

## 9. Recommendation (input for the lead and the human lead; not a decision)

Run the extension, because it is cheap (≤ 2 h of wall for the search), and Y4's first two stages alone decide whether S1 can reach any capacity outcome at all. But since a loaded 4K→16K row can only yield a near-foregone, one-transition positive, and both rows together exceed 32 h, I would return to the human lead after the search, before funding row L, whenever Y4 is EXCLUDED. As a better answer to the capacity question, I would put to the human lead (PENDING LEAD REVIEW) a revision that shifts the grid down one size, testing transitions 1K→4K and 4K→16K at load 8 (where R2 references exist at ≤ 65,536 slots and runs are cheap), or one that resolves the 4.0-versus-CEILING-4.5 gap in §8.2. Either is a threshold or design change that needs the human lead.
