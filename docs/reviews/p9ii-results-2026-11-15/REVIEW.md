# P9-II registered run (ADR-0019 revision 4): independent results audit, 2026-11-15

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.** Independent engineering and mathematical evidence only. The auditor did not write, launch or tune any part of P9-II, did not train or evaluate any model, and changed no file outside this folder.

## Verdict

**The registered outcome stands as printed:**

> ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0. Stage 2 COMPLETE, Stage 3 COMPLETE. Interface carried forward: A0 (LABEL-FREE). Stage 3: SCALE PROBE UNINFORMATIVE (0 of 2, A0).

The auditor's code was written from the ADR text and imports nothing from `studies/` or `arborlm`. It reproduces every registered decision: 171 comparisons with `results.json`, 0 disagreements, after two fixes to the auditor's own comparison code (both recorded below). The integrity checks hold. The code that ran is the freeze commit. The committed records are byte-identical to the raw records. All 174 cells are present and each was trained once. Seeds and draws are the registered ones and are disjoint from the calibration and rehearsal seeds. Every cap was respected and every gate passed.

The run applies the rules correctly. Four points about what the outcome means, set out below, are flagged **PENDING LEAD REVIEW**:

- (F1) The carry-forward rule selects A0, an arm that was UNRELIABLE at 4,096. As a result, Stage 3 probed A0 and not A5-D.
- (F2) H19-A fails on its gradient clause by a wide margin.
- (F3) A1-S is a weaker control than the ADR describes.
- (F4) A1's Stage 2 class turns on half a fact.

## Environment and commands

- Hardware and OS: macOS-27.2.1-arm64, 18 CPUs (the same machine as the run).
- Interpreter: `/opt/homebrew/bin/python3` (Python 3.15.1), always run with `-I`, so no project module can be imported. Standard library only. Lint: `uv run --locked ruff check .`, which gives "All checks passed!" with ruff 0.12.12 and the project's Python 3.12.14. No local `ruff.toml` was needed.
- Inputs:
  - worktree at HEAD `d72b173`
  - raw run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b` (read only)
  - ledgers `/Users/daniellaloush/dandush03/ArborLM/experiments/P9II-ledger-{A,B}.json`
- Commands, run from the worktree root (`S` is a scratch directory used for the `git archive` exports):

```sh
python3 -I docs/reviews/p9ii-results-2026-11-15/a1_integrity.py $PWD /Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b /Users/daniellaloush/dandush03/ArborLM/experiments $S > docs/reviews/p9ii-results-2026-11-15/outputs/a1_integrity.txt
python3 -I docs/reviews/p9ii-results-2026-11-15/b1_recompute.py /Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b results/p9ii-run-2026-11-15 docs/reviews/p9ii-results-2026-11-15/outputs/b1_recompute.json > docs/reviews/p9ii-results-2026-11-15/outputs/b1_recompute.txt
python3 -I docs/reviews/p9ii-results-2026-11-15/c1_explain.py /Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b docs/reviews/p9ii-results-2026-11-15/outputs/b1_recompute.json > docs/reviews/p9ii-results-2026-11-15/outputs/c1_explain.txt
python3 -I docs/reviews/p9ii-results-2026-11-15/c2_heldout_context.py /Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b > docs/reviews/p9ii-results-2026-11-15/outputs/c2_heldout_context.txt
```

### Failed or corrected attempts of the auditor's own scripts (kept)

| Attempt | Output kept | What went wrong | Fix |
|---|---|---|---|
| a1 #1 | `outputs/a1_attempt1_generate_manifests_misclassified.txt` | It reported "identity mismatch in 16 records". These are the sixteen `generate-*` stage manifests, written at the generation commit `a1685d0`. Their spec hash is the ADR before the freeze record was added (`dfd43ce…`). The script compared them with the freeze commit's identity, which was the auditor's error. | They are now compared with the re-derived identity of `a1685d0`, and all 16 match. The run itself was not at fault. |
| b1 #1 | `outputs/b1_attempt1_nan_comparison_and_recall_reading.txt`, `outputs/b1_attempt1.json` | (i) Four "disagreements" compared the auditor's `None` with the run's string `"nan"` for the median escape update of arms with no escaped cell. Both mean "no escaped cell". (ii) For A2's ADDRESS RECALL median, the auditor got 0.003662 and the run 0.003418. The auditor took the mean of the Panel A and B recalls per cell. The run takes the smaller of the two (`studies/p9ii/classes.py` line 13, read afterwards). The ADR says only "on Panels A and B". (iii) The borderline list included margins of cells that fail other conditions anyway. | The comparison now treats `"nan"` as `None`. All three readings of recall are printed (mean, pooled, min); the label is the same under each: A1 1.0 gives ADDRESS RECALL, A2 0.003 gives no label. Borderline cells are listed only where that single condition decides the cell. |

## 1. Integrity (script `a1_integrity.py`)

| Check | Result |
|---|---|
| Code identity | The auditor re-derived the four identity digests from `git archive` of the freeze commit `d2746d3`: source `8da53fc8…`, spec `47b14090…`, config `d5c9fe0b…`, frozen source `8b5a03a0…`. **All 398 run records that carry an identity equal it**: train and eval records, stage manifests and `gates.json`. The 16 `generate-*` manifests and 16 data manifests equal the identity of `a1685d0`. That commit's source digest equals the freeze's; only the spec hash differs, because the freeze commit added the §16 record to the ADR. `git diff d2746d3 HEAD` touches only `results/`. |
| generate.sh fix | `git diff 51c00b2 a1685d0 -- studies/` is exactly two lines of `launch/generate.sh`, each adding `--stage-cap-seconds 300`. It is a time cap on the generation calls; each call used 11.5–11.7 s. **Nothing scientific changed.** The source digest moves from `41b5e2a9…` (51c00b2) to `8da53fc8…`, and the run used the latter. The value 300 is not taken from the frozen cap table, but generation is not one of the §9 registered stages (minor note). Attempt 1's directory `P9IIP-registered-20261115` holds only a draw plan and no data. |
| Committed vs raw | SHA256SUMS: all 412 entries verify. 408 committed files have a raw counterpart and **all 408 are byte-identical** to it (cells, manifests, ledgers, results, analysis, gates, stage gates, draw plan). The remaining 4 files were written by the lead: README, launch log and the two wrapper scripts. All manifest `result_sha256` values hold against the raw files. |
| Frozen plan | 22 of 22 checks hold: the plan's sha256 `b4c057e9…`, calibration, projection, stage caps, draw plan, run directory and the sixteen data-manifest hashes. Draw plan: ok, no replacement, G1 passed for all 16 draws. |
| Census | 174 cells, exactly the set that ADR §5 and the two gate records imply: S1 128; S2 A0, A5-D, A1 and A1-S × 8 plus A6 and A7 × 4 (40 cells); S3 A0, A6 and A7 × 2 (6 cells). Each was trained exactly once (train1/2/3 manifests: 128/40/6 unique tasks, returncode 0, nothing skipped). Every cell is `completed` with 8,192 updates (32,768 at Stage 2) and a matching `updates.jsonl` line count. Readouts: u0008192 everywhere, plus u0032768 at Stage 2. There is no sign of a re-run. |
| Seeds | Every cell has seed set `p9ii-draw-d`, init seed 1901+j, target seed base+40+j and stream seed base+60+j, with base = 190001+100(d−1). Each draw lies inside its stage (1–8, 9–12, 13–14). All 16 data manifests follow the layout base+0…13 / +14…16 / +17…19. The calibration run directory uses seeds 179341…179461 and init seed 1891. The rehearsal gate directories use 179501…179533. **There is no overlap with the registered seeds.** |
| Budgets | Budget A charged 2,554.2 s of 14,400; before Stage 1, 736.8 s was charged. Stage 1's doubled projection of 4,143.3 s fit the remaining 13,663.2 s. Budget B charged 4,089.3 s of 10,800. The Stage 2 configuration A5-D+A1 had a doubled projection of 6,927.0 s against 10,800. Stage 3 (A0) had 631.2 s against the 7,077.9 s remaining after Stage 2. |
| Stage caps | train1 1,719 s against a cap of 3,965; evaluate1 88 against 178; train2 3,658 against 6,797; evaluate2 64 against 130; train3 341 against 580; evaluate3 26 against 51; gates, analysis and report 17.7, 9.4 and 0.6 s against 60 each. Every manifest cap equals the frozen table entry. |
| Memory | The largest task peak was 0.881 GiB (evaluate3, S3-A7 d14), against 3 GiB per worker. Workers × largest peak was at most 5.3 GiB, against 24 GiB. The lead's README says "peak worker memory 0.75 GiB". The auditor does not reproduce that figure: training peaks at 0.702 GiB and evaluation at 0.881 GiB (minor wording point, m4). |
| Gates | G1, G2, G4 (no defects), G5 and G6 all passed, with `dry: false`. G2 passed per draw for all 14 draws. The auditor recomputed the G2 interval independently as an exact equal-tailed binomial at p = 1/32 and level 0.999875: [36, 96], [198, 318] and [905, 1147] for 2,048, 8,192 and 32,768 facts. These equal the records. G5 passed in all 214 eval records. |

## 2. Recomputation (script `b1_recompute.py`, output `outputs/b1_recompute.txt`)

### Agreement table

"Run" means `results.json`, `classes.csv` and `RESULTS.md`.

| Item | Auditor | Run | |
|---|---|---|---|
| Success per cell (all learned arms, S1 at U; S2 at 4U) | 16 tables | same | AGREE |
| S1 A0 | UNRELIABLE, 4/16 (draws 7 and 8 both cells), LM-flagged 0 | same | AGREE |
| S1 A1 | RELIABLE 16/16; d = +12, p = 0.00049, IMPROVES ON A0 | same | AGREE |
| S1 A2 | FAILS 0/16; d = −4, p = 0.125, HARMS | same | AGREE |
| S1 A4 | FAILS 0/16; d = −4, HARMS | same | AGREE |
| S1 A5-C | UNRELIABLE 9/16; d = +5 (7 vs 2), p = 0.180, IMPROVES ON A0 | same | AGREE |
| S1 A5-D | RELIABLE 16/16; d = +12, IMPROVES ON A0 | same | AGREE |
| S1 A1-S | FAILS 0/16; d = −4, HARMS | same | AGREE |
| NEGATIVE CONTROL FAILED | not printed at 4,096 or at 16,384 | same | AGREE |
| d(A2 against A1), 4,096 | −16 | −16 | AGREE |
| Stage 1 gate | eligible [A5-D, A1]; both advance; A1-S runs with A1; Budget B check passes | same (`stage_gate_1.json`) | AGREE |
| S2 A0 (4U) | RELIABLE 8/8; at U FAILS 0/8 | same | AGREE |
| S2 A5-D (4U) | RELIABLE 8/8; d = 0, NOT DISTINGUISHED; at U RELIABLE 8/8, so ALSO AT MATCHED UPDATES | same | AGREE |
| S2 A1 (4U) | UNRELIABLE 6/8; d = −2, NOT DISTINGUISHED; at U FAILS 1/8 | same | AGREE |
| S2 A1-S (4U) | FAILS 0/8; d = −8, HARMS | same | AGREE |
| Carried forward (first RELIABLE at 16,384, 4U, in the order A0, A5-C, A5-D, A4, A2, A1) | A0 | A0 | AGREE |
| Stage 3 selection and label | A0; 0/2 succeed; SCALE PROBE UNINFORMATIVE | same | AGREE |
| Outcome row | row 4; A5-D is the only arm RELIABLE at both 4,096 and 16,384 | row 4, A5-D | AGREE |
| H19-A | onset ≤ 256 in 16/16 (all at update 64); gradient ratio ≤ 0.01 in **0/16** under three readings; not supported | `onset_cells 16, ratio_cells 0`; not supported | AGREE |
| H19-B | supported | supported | AGREE |
| H19-C | CONTRADICTED (A2 HARMS); also SUPERVISION-DEPENDENT 14/16 | same | AGREE |
| H19-D | CONTRADICTED (A4 HARMS) | same | AGREE |
| H19-F | not supported (A5-C UNRELIABLE, although it IMPROVES ON A0) | same | AGREE |
| H19-G | supported | same | AGREE |
| H19-E | supported for A1 and A5-D only; A0's clustering test p = 0.0154 | same | AGREE |
| Categories, median escape (escaped only and censored), ADDRESS STABLE, ADDRESS RECALL (min reading), dense labels, draw counts, permutation p | every arm at both sizes | same | AGREE |
| LM capability | no cell flagged; smallest margin to the line A6 + 0.05 is 0.0155 (S1 A5-C) | no flag | AGREE |

The independent G2 interval equals the interval in every record. The probe's slot statistics in the final 64-update diagnostics record equal the readout's probe in all 196 readouts compared. If condition 4 is also required against Panel B accuracy (a second reading of "conditions 1, 2 and 4 on both Panels A and B"), no success count changes.

**Disagreements with the run: none.** Disagreements with the lead's README: wording points m4 and m5 only (section 4).

### Values behind the H19-A gradient clause

The ratio is ‖∇wq‖ / ‖∇wo‖ of the answer loss, over updates 64–1,024, for 961 updates per cell, taken from `updates.jsonl` (pre-clip norms). Per-cell means range from 0.034 to 3.61; the lowest are cells 6/1 at 0.034, 6/0 at 0.043 and 2/1 at 0.046. Taking the ratio of means instead gives 0.048 to 3.37. The 64-update diagnostic records give 0.047 to 3.15. The smallest single-update ratio in any cell is 0.00074. The clause "≤ 0.01 in at least 12 of 16" fails in every reading by a factor of 3 to 300.

## 3. Explanations from the records (descriptive; enter no rule)

### Why A5-C is UNRELIABLE at 4,096 with Panel A at 0.97–1.00

All seven failures fail **only condition 4** (held-out templates). Conditions 1, 2, 3 and 5 hold, and each failing cell has Panel A between 0.9888 and 0.9985.

| Cell | Held-out ratio |
|---|---|
| 2/0 | H2/A 0.698 |
| 2/1 | H2/A 0.735 |
| 3/0 | H1/A 0.874, H2/A 0.764 |
| 3/1 | H2/A 0.785 |
| 5/1 | H1/A 0.883 |
| 8/0 | H1/A 0.874 |
| 8/1 | H1/A 0.876 |

The failures cluster by draw (draws 2, 3 and 8 lose both cells; permutation p = 0.049).

In ADR-0017 §4, H1 and H2 use separator and binding bytes that are disjoint from the training templates. A5-C's un-centred query is 91–95% fact-independent at the readout; for A0, A1 and A5-D the figure is 0.5–3.6%. A5-C works by subtracting m, which is frozen at evaluation and is a mean over training templates (ADR §8.3 says so). A template whose common mode differs from m therefore leaves a large residual in z − m. That residual would hurt held-out templates and not Panels A and B, which use training templates. This mechanism fits the records but **is not demonstrated by them**: showing it would need a new evaluation, which is outside this audit.

The held-out condition is not specific to A5-C. Four of A0's twelve Stage 1 failures (2/0, 3/0, 4/1, 5/1) also fail only condition 4. A4's working cells have min(H1/A, H2/A) of 0.72–0.93.

### Why A1 loses two cells at 16,384 (4U)

Both losses are held-out failures.

| Cell | Condition 4 result |
|---|---|
| 9/1 | H2 0.87646 (7,180/8,192) against a line of 0.88671: −84 facts |
| 11/1 | H1 0.88818 (7,276/8,192) against a line of 0.888245, i.e. 7,276.5 facts: **short by half a fact** |

One more correct H1 answer in cell 11/1 would make A1 7/8, which is RELIABLE at 16,384 (F4).

### A0 at 16,384

- **At U:** Panel A is 0.0297–0.0372 in all 8 cells, which is at chance. Distinct top-1 slots on the probe number 4–27; the largest share is 0.31–0.93. All 8 cells are FAILED at U.
- **At 4U:** Panel A is 0.9937–0.9976 and Panel B 0.9930–0.9967, in all 8 cells. All succeed.
- **Registered rule:** §5 and §8.4 say "The 4U readout decides the Stage 2 class for every arm." The U readout of a constant-objective arm is printed, and labelled "ALSO AT MATCHED UPDATES" only when RELIABLE there. A0 at 16,384 is therefore RELIABLE, and its U readout is "not RELIABLE at U". The run prints exactly this.
- **When A0 escapes (descriptive):** from the 64-update probe records, every cell collapses at update 64. The slot-based escape comes at 10,944–18,752 updates (median 15,392). Probe accuracy first reaches 0.5 at 12,864–20,352. Time to first success (probe accuracy ≥ 0.90 × A6's 4U accuracy) is 15,808–22,848, that is 1.9 to 2.8 U. A5-D never collapses, reaches probe accuracy 0.5 at 2,880–3,392 and succeeds first at 4,480–5,312. A1 escapes at 448–512 and succeeds first at 6,528–7,488.

### Is "carried forward: A0" what §8.6 literally prescribes? (F1)

Yes. §8.6: "**The interface carried forward** is the first RELIABLE arm at 16,384 (4U) in the order **A0**, then A5-C, A5-D, A4, then A2, then A1, with all its annotations, and only if it does not carry LM CAPABILITY REDUCED." A0 is RELIABLE at 16,384 (4U) and carries no LM flag, so A0 is selected. §8.5 selects Stage 3's arm by the same order: "The selected arm is the first RELIABLE arm at 16,384 in the carry-forward order of §8.6". This is why Stage 3 ran A0, not A5-D.

The ADR did not anticipate this situation:

- The rule has no condition on the arm's class at 4,096.
- The only text about A0 being reliable is row 3 ("A0 is RELIABLE at 4,096 …") and §2 ("If A0 itself is reliable on these draws …"). Both concern 4,096.
- No passage considers A0 UNRELIABLE at 4,096 but RELIABLE at 16,384, or what "carried forward" should mean when the outcome row names a different arm (A5-D).
- The Stage 1 gate always sends A0 to Stage 2 ("A0 runs at Stage 2 whenever Stage 2 is run"), so this combination was reachable by design.

The consequences:

- The printed outcome names A5-D, the arm reliable at both sizes, while the interface carried forward is A0, which was UNRELIABLE (4/16) at 4,096.
- A5-D was never probed at 65,536.

The run followed the text literally and correctly. Whether the carry-forward is meant to require reliability at 4,096 as well is a scientific question: **PENDING LEAD REVIEW**. Under §15, any change after the freeze belongs to the human lead.

## 4. Findings by severity

There are no blockers and no engineering defects in the run.

**Majors (interpretation; PENDING LEAD REVIEW)**

- **F1. Carried-forward interface and Stage 3 arm.** See section 3. The registered text yields A0 for both the carried-forward interface and the Stage 3 probe, although A0 was UNRELIABLE at 4,096 and the outcome names A5-D. The Stage 3 result (A0: 0.031 and 0.030 on Panel A, 3–4 distinct top-1 slots) tells nothing about A5-D at 65,536. Any statement that "the interface for P10 is A0" should carry this context.
- **F2. H19-A's mechanism clause is far from met.** The answer-loss gradient ratio ‖∇wq‖ / ‖∇wo‖ over updates 64–1,024 is 0.034–3.6, not ≤ 0.01, in all 16 cells, even though every A0 cell collapses at update 64. The "starved addressing gradient" in §1 (2.7e-6 against 1.9e-2) came from an exploratory diagnostic and is not reproduced by the registered measure on these draws. The record therefore supports "collapse is early and universal" and contradicts "the gradient is starved by two orders of magnitude" as measured by the registered statistic. H19-A is correctly printed as "not supported".

**Minors**

- **F3. A1-S is weaker than the ADR's description.** §4 says L_addr's gradient (4–6) exceeds the clip, so that A1's answer gradients are scaled by about 0.2, and A1-S is meant to give "an address-loss gradient of the same magnitude".
  - The median clip factor over updates 1–1,024 is 0.94 for A1 and 0.67 for A1-S, and 1.0 for both over 1,025–8,192.
  - Over 1,025–8,192, A1-S's query-projection gradient has a median of 0.059, against A1's 0.61, ten times smaller. Its key gradient is about twice A1's (0.52 against 0.27).
  - A1-S's address loss sits at 8.34, close to ln 4,096 = 8.32, as an unlearnable target should.

  The control still did its registered job: it never improves on A0 and is never RELIABLE, so NEGATIVE CONTROL FAILED is correctly not printed. A1-S even HARMS (d = −4 at 4,096; −8 at 16,384). But "same-magnitude gradient without fact information" holds for the keys, not for wq after the first thousand updates. PENDING LEAD REVIEW for interpretation only; no rule is affected.
- **F4. A1's Stage 2 class turns on half a fact** (cell 11/1, H1). A one-fact change would make A1 RELIABLE at 16,384. The outcome row (4) and the carried-forward arm (A0) would not change, but the printed classes would. Tie handling ("ties counted wrong") cannot be re-checked from the records without re-running evaluation.
- **F5. HARMS, and so CONTRADICTED, for A2, A4 and A1-S at 4,096 rests on the minimum count.** d = −4 equals A0's 4 successes, all on draws 7 and 8, and the sign-test p is 0.125. The label follows the rule exactly. Its evidential weight is the weight of two draws. The A2 records also show that its addresses collapse within 64 updates of the moment reset: target top-8 recall drops from 1.0 at update 2,048 to 0.04–0.07 at 2,112, with 1–4 distinct top-1 slots. So "H19-C CONTRADICTED" is a statement about this registered A2, with its reset, which the freeze record (item 3) kept on purpose. It is not a statement about staged optimisation in general.
- **m1.** ADR §8.4 defines d(X) "at a size and readout". The run prints the paired label at 16,384 only at 4U. At U the auditor finds the following (descriptive; enters no rule, because the Stage 2 class and readings are at 4U):
  - A5-D: d = +8, p = 0.0078
  - A1: d = +1
  - A1-S: d = 0
- **m2.** ADDRESS RECALL "on Panels A and B" does not say how the two panels combine. The run uses the smaller; mean and pooled readings give the same labels.
- **m3.** The `--stage-cap-seconds 300` in `generate.sh` is a value that no frozen table holds. Generation is not a §9 registered stage, and it charged 11.5–11.7 s per draw.
- **m4.** The README's "Peak worker memory 0.75 GiB" is not reproduced. The largest task peaks are 0.702 GiB in training and 0.881 GiB in evaluation, both far under the caps.
- **m5.** The README's "H1 0.888 against 0.888" is accurate to three decimals, but the cell misses by 0.5 of a fact (F4). The other README ranges reproduce:
  - A0 at U: 0.0297–0.0372; distinct top-1 4–27
  - A0 at 4U: 0.9937–0.9976
  - A5-D: 0.9819–0.9883 at U; 0.9985–0.9994 at 4U
  - A5-C failures: Panel A 0.9888–0.9985
  - A7: 0.9971–0.9995 at 4,096; 0.9736–0.9821 at 16,384 (4U), with H1/H2 0.802–0.888
  - Stage 3: A0 0.0315 and 0.0304; A6 0.9726 and 0.9709; A7 0.1321 and 0.1226
  - Budget charges: 2,554 s and 4,089 s

## 5. Borderline cells

The list covers conditions within 0.005 of their threshold where that condition alone decides the cell, plus the LM margin.

| Stage / readout | Arm | Cell | Condition | Margin | Cell |
|---|---|---|---|---|---|
| 2 / 4U (deciding) | A1 | 11/1 | H1 ≥ 0.9 × A | −0.00006 (−0.5 facts) | FAILED |
| 2 / U (printed only) | A1 | 9/0 | H2 ≥ 0.9 × A | −0.00098 (−8 facts) | FAILED |

Closest passes, all outside 0.005: A5-C cell 6/1 H1 +0.0082; A1 at 16,384 H2 +0.0063; A0 at 16,384 H1 +0.0122. The smallest LM margin is 0.0155 (S1 A5-C). The smallest probe slot statistics among successes are 256 distinct top-1 slots and a largest share of 0.0078, far from the 128 and 0.02 limits.

Count-level borderlines (F5): HARMS at d = −4 exactly, three times at 4,096. A5-C's IMPROVES ON A0 is at d = +5, one above the line.

## 6. Threats to validity checked

- **Leakage:** no LEAKAGE flag in any of 428 panel readouts. Unseen-fact accuracy is 0.021–0.041 (chance about 0.031). G1's `panel_not_in_training` passes for every panel, including H1 and H2.
- **Memory dependence:** permuted and disabled accuracies are inside the independently recomputed G2 interval for every successful cell.
- **Slot probe:** the probe set is the calibration stream, not a registered panel. Its readout statistics equal the last training record in all 196 readouts. The successful cells clear the slot condition by a wide margin.
- **Held-out templates:** these decide most failures: A5-C 7/7, A1 at 16,384 2/2, and A0 at 4,096 4 of 12. The condition was fixed before the measurement (ADR §8.3). The auditor could not independently check that the H1/H2 byte sets are disjoint from the training templates, because the data are not stored. Only the G1 checks and the manifest hashes are on record.
- **Tuned against untuned:** A0 is untuned by design (§6, §13). A5-D's μ = 1.0 and A1's λ = 1.0 were chosen on two calibration draws. Every "IMPROVES ON A0" compares a calibrated arm with an untuned baseline.
- **Few draws:** Stage 2 has 4 draws (8/8 for A0 and A5-D gives a per-draw one-sided 95% lower bound of 0.47). At Stage 1, 8 of 8 draws gives 0.69 for A1 and A5-D. A0's Stage 1 outcome is strongly draw-clustered: 2 draws at 2/2, 6 at 0/2, permutation p = 0.0154.
- **Matched updates against matched exposure:** at 16,384, A0 vs A5-D is NOT DISTINGUISHED at 4U (d = 0). The large U contrast (A0 0/8 against A5-D 8/8) is descriptive. §13 also states that matched exposure is not matched optimisation.
- **Dense control:** A7 is 0.997–1.000 at 4,096 and 0.974–0.982 at 16,384 (4U), so DENSE AT CEILING. No memory arm is shown to beat the dense adapter. At 65,536, A7 is 0.12–0.13 at 32 exposures per fact, and the probe is uninformative by design.

## 7. What may and may not be claimed (ADR §13; plain words)

**May be stated** (with the outcome label in full, never shortened):

- On this task, backbone and W7 interface, with the memory told the answer position: answer-only training (A0, untuned) gave reliable sparse addressing on only 2 of 8 independent data draws at 4,096 slots. The study's arm with a query-diversity penalty (A5-D, label-free, calibrated μ = 1.0) succeeded in 16 of 16 cells and was RELIABLE.
  - At 16,384 slots and 512 exposures per fact (4U), A5-D was RELIABLE (8/8), but so was untuned A0 (8/8): NOT DISTINGUISHED FROM A0.
  - At matched updates (U), A5-D was 8/8 and A0 0/8. This is descriptive; the registered reading is at 4U.
- The constant address loss (A1, address-supervised in training) was RELIABLE at 4,096 and UNRELIABLE at 16,384 (6/8, one cell short by half a fact). The staged A2 (with moment reset) and the top-k anneal A4 failed in every cell and are recorded as harmful relative to A0 under the registered rule. The random-target control never helped.
- H19-A is not supported: the collapse is early and universal, but the registered gradient-starvation clause fails in all cells.
- The per-draw success probability bounds are 0.69 (8/8 draws) and 0.47 at Stage 2 (4/4). No higher figure may be claimed.

**Must not be claimed:**

- Anything about capacity, useful-capacity scaling, locality, incremental learning, natural language, another backbone, another interface, or 65,536 slots. The Stage 3 probe ran A0, not A5-D, and is uninformative by design.
- That A5-D is needed at 16,384 (it is not distinguished from A0 at 4U), or that a tuned arm beats a tuned baseline (A0 is untuned).
- That address supervision is available in a real system (A1 relies on a training label), or that the LM-capability result says anything about a deployed system (the memory is told the answer position).
- That memory beats the dense adapter. Dense is at ceiling at 4,096 and 16,384.
- That staged optimisation in general is contradicted. The contradiction is of this A2 with its moment reset, at d = −4 on two draws.
- Any efficiency claim; any failure or success of the ArborLM concept; "breakthrough", "validated" or "approved". This review is not Astra validation and not a human approval.

## Files

- `a1_integrity.py` and `outputs/a1_integrity.txt` (attempt 1 kept: `outputs/a1_attempt1_generate_manifests_misclassified.txt`)
- `b1_recompute.py`, `outputs/b1_recompute.txt` and `outputs/b1_recompute.json` (attempt 1 kept: `outputs/b1_attempt1_nan_comparison_and_recall_reading.txt` and `outputs/b1_attempt1.json`)
- `c1_explain.py` and `outputs/c1_explain.txt`
- `c2_heldout_context.py` and `outputs/c2_heldout_context.txt`

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
