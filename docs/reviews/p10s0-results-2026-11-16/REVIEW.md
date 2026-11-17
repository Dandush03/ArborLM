# P10-S0: independent recomputation of the registered run (ADR-0020 rev. 4 and addenda)

Auditor: Claude Opus 5.5 (independent context; I wrote none of the S0 code, analysis or report). This is a Claude review. It is **not Astra review and not human approval**. Astra review: NOT_PERFORMED.

Verdict: **AGREES WITH NOTED DEFECTS**. Every number, class and label I recomputed from the raw records matches the report: 1,065 automated comparisons and 0 disagreements in the final run. The defects are in presentation and in what the report leaves out. None changes a class, a label, a hypothesis reading or the outcome row.

## 0. Inputs, environment, commands

- Worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-afc8a4b295465fecc`, branch `claude/p10-s0`, HEAD `d963176`. Freeze commit `579d332` (22:34:18 UTC). Run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S0-registered-20261115`. Committed record `results/p10s0-run-2026-11-16/`.
- Environment: `/opt/homebrew/bin/python3` 3.15.1, macOS-27.2.1-arm64, stdlib only, every command run as `python3 -I` under `nice -n 10` in a single process. Nothing from `studies/` or `arborlm` was imported. No training, network or new environment was used. Nothing in the repository or the run directory was written.
- Frozen tree: `git archive 579d332 docs/decisions studies configs src | tar -x -C tree579`.
- Commands (S = this folder, X = the run directory, W = the worktree):
  - `python3 -I integrity.py S/tree579 X W/results/p10s0-run-2026-11-16 x` writes `integrity_out.json`
  - `python3 -I p9ii_identity.py S/tree579`
  - `python3 -I stages.py X experiments/P10S0-ledger.json S/tree579 experiments/P10S0J-projection-20261115-r2/projection.json` writes `stages_out.txt`
  - `python3 -I integrity2.py X` writes `integrity2_out.txt`
  - `python3 -I recompute.py X S/tree579/studies/p10s0/freeze/arm_selection.json W/results/p9ii-run-2026-11-15/results.json S/mine.json` writes `recompute_run4.txt` (final)
  - `python3 -I compare.py S/mine.json W/results/p10s0-run-2026-11-16` writes `compare_run3.txt` (final) and `comparisons.tsv` (every comparison, one line each)
  - `python3 -I extras.py S/mine.json X` writes `extras_out.txt`
  - `python3 -I timing.py X experiments/P10S0J-projection-20261115-r2/projection.json experiments` writes `timing_out.txt`
  - `python3 -I strings.py W/docs/decisions/ADR-0020-…md W/results/p10s0-run-2026-11-16`
  - Also: `shasum -a 256 -c CODE_SHA256.txt` in the worktree, and a loop comparing each listed file's hash at `git show 579d332:<path>`.

## 1. Integrity (item 1): all checks pass

| Check | Result |
|---|---|
| `CODE_SHA256.txt` (29 files) against the tree at `579d332` and against the working tree | 29/29 equal in both. The list covers all 28 files under `studies/p10s0/` plus the config |
| Commits after the freeze | `579d332..d963176` adds only `results/p10s0-run-2026-11-16/*` (19 files). No code, config, ADR or freeze file changed |
| Code identity in the records | 784 identity blocks in the run directory. 778 equal my independently computed frozen identity (`source 41e6bac7…`, `frozen_source 8b5a03a0…`, `spec 3b3ccc76…`, `config 0d8b1f34…`). The other 6 are G4's "theirs" side (`gate_runs/identity_*/theirs`), and they equal P9-II's identity, which I recomputed in the frozen tree (`8da53fc8…`, config `d5c9fe0b…`, spec = ADR-0019 `893b605d…`). This is expected for a bit-identity gate against `studies.p9ii` |
| Frozen plan | `plan.json`: 15/15 data manifests match by sha256. Draw plan `f55c411d…` and projection `f7e13716…` match. Arm selection `e8bbd2c0…` is in CODE_SHA256. G1 passed on 15/15 draws. No replacements. Seed layout: base + 0…19 / 20…39 / 60…79 per fact set, with bases 200001 + 100(d−1) and reserves at 201301/201401, on all 15 manifests |
| Per-cell plan conformance (256 cells) | 0 issues. Checked: updates (8,192 / 32,768 / 131,072), facts, slots, init seeds (2001+j; alternating by draw at 8K/4K and WX; 2001 for A6, A7 and the probe), target seeds base+40/44/48+j, seed set, hyper-parameters λ=1, U_pre=2,048 (A2 schedule u_pre = 2,048·F/2,048), μ=1, k0 0.125, 512 exposures per fact min/max, 0 trainable backbone parameters, readouts {U} or {U, 4U}, a diagnostics record every 64 updates. No A1 or A2 cell at 8K/4K |
| Matrix | 256 cells = Q1 230 + WX 20 + probe 6, none missing or extra. All 256 trainings `completed`. 396 evaluations, 0 G5 failures. All 512 snapshot `model.pt` hashes equal `train.json` |
| Stage order (manifest timestamps) | gates 22:37:12 → train-q1 22:38:10 → evaluate-q1 → [q1_gate.json written 02:28:54] → train-wx 02:29:08 → evaluate-wx → train-probe → evaluate-probe → analyze → report 04:30:38. Each stage starts after the previous one finishes, all `COMPLETE`, 0 failed or skipped tasks. 0 task result-hash mismatches |
| Frozen paths after the freeze | 92 files (draws, generate stages, draw plan, projection): none modified after 22:34:18 UTC |
| Registered gates | 72 pass/ok flags, none false (G1, G2, G4, G5, G6, G9, G10) |
| Ledger | Total 21,940.986 s (6.0947 h) of the 79,200 s (22 h) cap. 486.258 s before the registered run. Charged before Q1 834.782 s and at the Q1 gate 14,656.477 s: both equal the records |
| Headroom before Q1 | 834.8 + 2·(30,276.3 + 60) = 61,507 s ≤ 79,200. No cut (`q1_start.json` `required_seconds` 60,672.5 = 2·(Q1 + reserve), the same arithmetic) |
| Headroom at the Q1 gate | 14,656.5 + 2·(3,032.6 + 11,824.6 + 60) = 44,490.8 s ≤ 79,200, a margin of 34,709 s. WX and probe run, no cut. The WX and probe projections equal (train + evaluate caps)/2 for A5-D |
| Stage caps | No stage reached its cap. Use was 0.20–0.37 of each cap (report 0.015). The largest peak RSS was 0.84 GiB (probe evaluation) |
| Byte identity of the committed record with the run directory | 18/18 files byte-identical (RESULTS.md, results.json, classes.csv in `X/results/`; analysis.json, gates.json, q1_*.json, draw_plan.json at top level; the 9 manifests at `X/<stage>/manifest.json`; `ledger_after_run.json` = `experiments/P10S0-ledger.json`). README.md was written for the record and has no counterpart. `analysis.json`'s `result` equals `results.json`'s `result` |
| Arm selection (G10, from §3.2 and §3.5) | The calibration record `ad5d7ee2…`, P9-II OUTCOME `66946b87…` and results `9b2ca547…` match their cited hashes at HEAD and at `579d332`. Outcome row 4, Stage 2 COMPLETE, carried arm A0 → mapping gives no fourth arm (§3.3 row 3). The override gives A5-D. Candidate list: A0 excluded (6 of 8 P9-II draws failed at 4,096), A2 excluded (8 of 8), so A5-D and A1 remain. P9-II classes and failed-draw counts read independently from P9-II's `results.json` (`stage{1,2}.arms.*.draw_sensitivity.draw_counts`) equal the arm-selection record for A0, A1, A2 and A5-D at both sizes. A2 has no Stage 2 class |

## 2. Recomputation (item 2)

My code is written from ADR-0020 §6–§8 and ADR-0019 §8.1–§8.4. Thresholds are compared in integer arithmetic on the recorded counts (for example `10·correct ≥ 9·correct_A6` and `100·a_use_count ≥ 95·correct`), so no float rounding decides a cell. G2 is the exact binomial central interval at level 1 − 0.001/8 around 1/32. I recomputed it ([36,96], [198,318], [905,1147]) and it equals every recorded interval. All recorded at-chance and LEAKAGE flags equal my own (0 mismatches).

Classes, at the class readout:

| Arm | Cell type | S0 class | Cells | Draws | Bound | P9-II criteria | P9-II class | Replication | Consistency (pooled, P9-II criteria) | ADDRESS STABLE median | COLLAPSE-FREE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 2K/4K | UNRELIABLE | 9/20 | 3/10 | 0.087 | UNRELIABLE (same counts) | UNRELIABLE | REPLICATES | INCONSISTENT (5 of 18; 13 failed; bound 0.116) | 0.876 | 0/20 |
| A0 | 8K/16K | RELIABLE | 19/20 | 9/10 | 0.606 | RELIABLE | RELIABLE | REPLICATES | CONSISTENT (13 of 14; 0.703) | 0.896 | 0/20 |
| A0 | 8K/4K | FAILS | 0/10 | 0/10 | 0.000 | FAILS | — | NOT COMPARABLE | — | 0.833 | 0/10 |
| A1 | 2K/4K | RELIABLE | 20/20 | 10/10 | 0.741 | RELIABLE | RELIABLE | REPLICATES | CONSISTENT (18 of 18; 0.847) | 1.000 | 3/20 |
| A1 | 8K/16K | UNRELIABLE | 15/20 | 5/10 | 0.222 | UNRELIABLE | UNRELIABLE | REPLICATES | INCONSISTENT (7 of 14; 0.264) | 0.999 | 0/20 |
| A2 | 2K/4K | FAILS | 0/20 | 0/10 | 0.000 | FAILS | FAILS | REPLICATES | INCONSISTENT (0 of 18; 0.000) | 0.809 | 0/20 |
| A2 | 8K/16K | FAILS | 2/20 | 0/10 | 0.000 | FAILS | none | NOT COMPARABLE | SINGLE-STUDY EVIDENCE | 0.842 | 0/20 |
| A5-D | 2K/4K | RELIABLE | 20/20 | 10/10 | 0.741 | RELIABLE | RELIABLE | REPLICATES | CONSISTENT (18 of 18; no bound printed, correctly) | 0.916 | 20/20 |
| A5-D | 8K/16K | RELIABLE | 20/20 | 10/10 | 0.741 | RELIABLE | RELIABLE | REPLICATES | CONSISTENT (14 of 14; no bound printed, correctly) | 0.871 | 20/20 |
| A5-D | 8K/4K | FAILS | 1/10 | 1/10 | 0.005 | FAILS | — | NOT COMPARABLE | — | 0.863 | 10/10 |

- LM CAPABILITY REDUCED: 0 flagged cells anywhere. The smallest margin to the flag is 0.035 (A1 2K/4K).
- Paired against A0 (S0 criteria, with the P9-II-criteria d identical in every row): A1 +11 IMPROVES (p 0.001) / −4 HARMS (p 0.219); A2 −9 HARMS (0.004) / −17 HARMS (1.5e−5); A5-D +11 IMPROVES (0.001) / +1 NOT DISTINGUISHED (1.000). d(A2 vs A1): −20 (p 1.9e−6) at 2K/4K and −13 (p 2.4e−4) at 8K/16K.
- Qualification: in the order A0, A5-D, A2, A1, A5-D is the first arm that meets the criteria and is CONSISTENT at both sizes, so it is the candidate. ALSO QUALIFIES: A1 (4,096 ONLY). A0 meets the criteria only at 8K/16K and A2 nowhere. Outcome **row 4, ADDRESSING-QUALIFIED (4,096 AND 16,384)**. 2K/4K is not NOT_EVALUATED, since A6 = 0.9995–1.000 on every draw.
- Q2: OVERLOAD NOT QUALIFIED (A5-D 8K/4K FAILS; A6 ≥ 0.50 on all 10 draws, at 0.993–0.997). WX: 2K/4K FAILS 2/10, stable median 0.840, AUC median 0.929, i median 3.220. 8K/16K FAILS 0/10, stable median 0.327 (not ADDRESS STABLE), AUC 0.843, i 1.708. This gives RECORD-LENGTH-FREE VARIANT: DOES NOT PASS. Probe: 3 of 3 succeed (bound 0.368), with all three A6 cells evaluated.
- Hypotheses: H20-A supported; H20-B CONTRADICTED (A1 HARMS at 8K/16K); H20-C CONTRADICTED; H20-D not supported (A0 fails 1 cell at 8K/16K, so d ≥ 4 is unreachable); H20-Q supported; H20-O not supported; H20-L not supported; H20-S supported (annotation); H20-R supported for A0, A1 and A2 at 2K/4K, A0 and A1 at 8K/16K and A5-D at both sizes; H20-R not read for A2 at 8K/16K.
- Matched-update readout at U (enters no rule): A0 8K/16K FAILS (0/20), A1 8K/16K FAILS (3/20), A2 FAILS (MID-SCHEDULE), A5-D 8K/16K UNRELIABLE (16/20), A0 and A5-D 8K/4K FAILS.
- Descriptive values all match: categories, i medians (with the "0 at or below the chance interval" convention), sustained success, ADDRESS RECALL (A1 1.000 / 1.000, A2 0.004 / 0.003), DENSE AT CEILING for every RELIABLE arm (median A7 accuracy > 0.909; for example A5-D 8K/16K median ratio 1.0247, arm higher on 10 of 10 draws) and the A6 table.

## 3. Comparison with the report (item 3)

**Final: 1,065 comparisons, 0 disagreements** (`compare_run3.txt`, `comparisons.tsv`). They cover all 10 arm × cell-type blocks of results.json (both criteria, every count, bound, label, pooled value, failed-condition sets per cell, categories, medians, dense values per draw), the 12 paired blocks, d(A2,A1), selection, outcome, overload, WX, probe, all 16 hypothesis readings, the A6 table (30 draws × 4), every row of classes.csv, and the numbers printed in RESULTS.md (class table, paired table, outcome block, i lines, U-readout lines, WX lines, A6 table, hypothesis column).

Disagreements found along the way. **All four were my own mistakes**; failed attempts are kept:

1. `recompute_attempt1_p9check_bug.py`: my P9-II cross-check reported "A2 16384 available False vs False" as a mismatch. This was a bug in my comparison code, and it was fixed.
2. `recompute_attempt2_c4_panelA_only.py` with `compare_run1.txt` (5 disagreements). I applied condition 4 against Panel A only. The report applies it against Panel A and Panel B, following ADR-0019 §8.3's "(conditions 1, 2 and 4 on both Panels A and B)". The report's reading is the better reading of the text, and I adopted it. Under either reading every class-readout success is identical. Exactly one cell's success depends on the reading: `Q1-A1-8K16K-d09-j0` at the U readout, which enters no rule, and its class at U (FAILS) is the same either way. Three of the five disagreements were per-cell failed-condition lists in already-failed cells.
3. Two of the five were my str/int typing in the RESULTS.md parser (`compare_attempt1_typing_bug.py`).
4. `extras_out_attempt1_c4margin_panelA_only.txt`: my descriptive condition-4 margins used Panel A only. Corrected. No comparison was affected.

The report's descriptive conventions that I matched rather than derived from ADR-0020 are listed here so the lead can see them. (a) i is set to 0 when a panel's accuracy is at or below the G2 upper end. This is the ADR-0017 I_acc convention, it is stated in the unit string and in the frozen wording table, and without it A2 2K/4K's median would be 0.033 instead of 0.012. (b) The sustained-success line uses A6's mean of Panels A and B. (c) ADDRESS RECALL uses the per-cell minimum over the two panels. (d) DENSE COMPARISON averages the two seeds and the two panels per draw. The labels do not depend on (b)–(d).

## 4. Wording (item 4)

No line claims success of the science, autonomy, capacity or efficiency. "A hypothesis reading is not a success of the science" and "not a success of it either" are present. The §8.7 print items 1–7 for row 4 are present, including "The memory is told the answer position" (and "W7 is told the record length"). The three fixed A5-D strings are verbatim (they equal the ADR text exactly) in 9 places in RESULTS.md, in results.json and in the classes.csv header. The probe is printed as "probe; not a qualification; S0 only; three draws; one initialization seed" and "Nothing reliable about 65,536 slots". "Not an unbiased first test of A5-D" is in "What may not be said".

Defects (presentation; none changes a reading):

- **D1, raw dicts in the hypothesis table.** Python `repr` dicts appear in five rows, not three: H20-B and H20-C (`paired: {'2K/4K': …}`) as well as H20-D and the two A5-D H20-R rows. In the three A5-D rows the dict holds exactly the three fixed strings, verbatim, plus the arm, the paired labels and the registered note. **It hides nothing.** It is a rendering defect that makes the required sentences hard to read.
- **D2, "A0: qualifies at 16,384 ONLY"** (Qualification section; `selection.per_arm.A0.scope`). ADR-0020 §8.5 defines no 16,384-only scope, and A0 cannot be qualified at any scope (§3.5). The line is implementer wording that I did not find in the freeze's approved wording tables. Read alone, it suggests an answer-only qualification at 16,384. "A1: qualifies at 4,096 ONLY" is likewise a per-arm line, but the registered print, "ALSO QUALIFIES: A1 (4,096 ONLY)", is also present. PENDING LEAD REVIEW: whether these per-arm lines may stand.
- **D3, "FAILS — ALSO AT MATCHED UPDATES" / "UNRELIABLE — ALSO AT MATCHED UPDATES".** ADR-0019 attaches ALSO AT MATCHED UPDATES to a class that is RELIABLE at U. Printed after FAILS or UNRELIABLE, it can be read as "fails also at matched updates" (for example A5-D 8K/16K: UNRELIABLE at U, RELIABLE at 4U).
- **D4, duplicated or empty strings.** "ADDRESS STABLE ADDRESS STABLE" (WX 2K/4K), "ADDRESS STABLE no" (WX 8K/16K), "ADDRESS RECALL median 1.000 ADDRESS RECALL" (A1), "ADDRESS RECALL median 0.004 " with an empty label (A2).
- **D5, A5-D strings not printed in two sections.** The section "Annotations on the candidate (section 8.6)" prints A5-D's OVERLOAD, WX and probe annotations without naming A5-D and without the three strings in that section. In the hypothesis table, H20-O, H20-L and H20-S are readings on A5-D but carry no provenance in their rows. §8.7 asks for the strings "wherever … an annotation or hypothesis reading of A5-D is printed". The strings do appear elsewhere in the document, so this is minor.
- **D6, COLLAPSE-FREE missing next to A0's RELIABLE at 16,384 in the outcome block.** Outcome item 6 prints "A0 at 16,384: RELIABLE" without COLLAPSE-FREE beside it. §8.4 wants it printed beside the class "so that 'collapsed and recovered' is not read as 'never collapsed'". The class table does print it.
- **D7, cosmetic.** The A6 table orders draws as strings (1, 10, 2, …).

## 5. What the records show and the report does not (item 5)

1. **Condition 4 (held-out templates, H1/H2 ≥ 0.90 × panel accuracy) decides every failure at 8K, and condition 6 decides no class.**
   - A5-D 8K/4K fails condition 4 alone in 9 of 10 cells. Its accuracy is 0.946–0.956 in every cell (≥ 0.90 × A6, which is 0.993–0.997), it never collapses (10/10), and it passes condition 6. Its one success (d07) passes condition 4 by +0.001, and the near-miss (d06) fails by −0.007. **OVERLOAD NOT QUALIFIED is therefore a held-out-template generalisation failure at two facts per slot. It is not a collapse failure and not an accuracy failure.** The report prints only "FAILS".
   - A0's single failure at 8K/16K (d3/j1) is condition 4 alone (−0.037). The 5 A1 failures at 8K/16K are condition 4 alone. A0 8K/4K fails condition 4 in all 10 cells.
   - Condition 6 margins in every successful cell are 0.046–0.050: a_use/correct is about 0.9999 everywhere, so a swapped read almost always loses the answer. As a result the S0-criteria and P9-II-criteria classes and paired d values are identical in every row. **The stricter criterion added nothing on these draws.**
2. **At 16,384 the candidate is not distinguishable from answer-only.** A0 is RELIABLE at 8K/16K (19/20). A5-D's paired label there is NOT DISTINGUISHED (d = +1), and H20-D is not supported, by the registered reading. Every one of A0's 20 cells at that size collapsed at update 64. They escaped at a median of 13,664 updates (maximum 25,600 of 32,768), and all 20 fail at the matched-update readout U. A5-D never collapses: its minimum distinct top-1 over training is 263–270 against the onset line of 32. A0's minima are 1–7 distinct slots in every cell at 2K/4K and 8K/16K. **A0's 0 of 20 never-collapsed against A5-D's 20 of 20 is the clearest contrast in the run.** The headline row-4 block does not carry A5-D's own paired labels or H20-D's reading. They are in the paired table and the hypothesis table. A reader of the outcome block alone would not learn that the penalty's measurable advantage over answer-only is at 4,096 (A0 9/20) and not at 16,384.
3. **Near-threshold successes.** A5-D 2K/4K is comfortable: smallest margins are c1 +0.096, c4 +0.061 and c6 +0.049. At 8K/16K the smallest condition-4 margin is +0.024 (d1/j0), with c1 ≥ +0.098. A0's RELIABLE at 8K/16K rests on thin margins (c4 +0.002 in d1/j1, c1 +0.041); one more condition-4 miss would make it UNRELIABLE. A1 8K/16K successes go down to c4 +0.0005. On the probe, all three A5-D cells pass with c1 +0.097 and c4 ≥ +0.071.
4. **No success is lost late.** No learned cell succeeds at U and fails at 4U. No cell's probe accuracy reaches 0.90 and later falls below 0.85. Four A5-D 8K/16K cells and 12 A1 cells succeed only at 4U.
5. **A1 collapses too.** 17 of 20 A1 cells at 2K/4K and 20 of 20 at 8K/16K have a collapse onset at update 64. They escape by update 128–512 (COLLAPSE-FREE 3/20 is printed). A2 collapses at its switch (onset at update 2,112 in all 20 cells at 2K/4K).
6. **WX at 16,384 is not address-stable** (median 0.327, per-cell 0.215–0.481, accuracy 0.44–0.70). The failure is conditions 1 and 4. By the ADR, a WX failure is not evidence that the record length is required.
7. **Timing.** Q1 trained in 13,415 s against a projection of 30,276 s (0.44). Every block ran at 0.40–0.63 of its projection. Per item, the registered rates were 0.34–0.67 of the rehearsal's busy rates (which the projection used) and mostly 0.57–0.91 of its alone rates. A0 8K/4K and A7 8K/16K ran 1.11–1.13 times their alone rates. No other study's ledger has an entry overlapping 22:28–04:31 UTC, while the rehearsals ran beside P10-S1's calibration on six cores (ADR-0020 addendum). The projection was conservative, and the caps were never approached: every stage used 37% or less of its cap. No rule depends on this. It does mean that the thin A1-candidate probe margin recorded at the freeze (+260.8 s) was an artefact of a pessimistic rate.
8. **One reserve-rule wording point.** The reserve in the headroom rule is 60 s, applied doubled (120 s = the analysis cap plus the report cap). This matches ruling N4 under the cap table's stated "reserve = (analysis cap + report cap)/2". FREEZE.md's phrase "reserve for analysis and report 60 s" could be misread as 60 s total. There is no effect.

## 6. Points for the lead (PENDING LEAD REVIEW)

- Whether D2's per-arm "qualifies at" lines may stand, given that ADR-0020 has no 16,384-only scope and §3.5 says A0 cannot be the candidate at any scope.
- Whether summaries of the outcome must carry A5-D's paired labels and H20-D's "not supported" next to the row-4 label (item 5.2 above). ADR-0020 does not require this for the candidate. ADR-0019's outcome label did carry it.
- Whether OVERLOAD's failure reason (condition 4 only, item 5.1) should be stated wherever OVERLOAD NOT QUALIFIED is cited, especially for S1's lane L, which is omitted as a consequence.
- The observation that condition 6 never decided a class bears on whether "fact-specific dependence" as operationalised adds information beyond conditions 1–5 in this testbed. This is a scientific question, not a defect.

## 7. Files in this folder

Scripts: `integrity.py`, `integrity2.py`, `p9ii_identity.py`, `stages.py`, `recompute.py` (final), `compare.py` (final), `extras.py`, `timing.py`, `strings.py`. Failed or superseded attempts, kept: `recompute_attempt1_p9check_bug.py`, `recompute_attempt2_c4_panelA_only.py`, `recompute_attempt3_c4margin_panelA.py`, `compare_attempt1_typing_bug.py`, `mine_attempt1.json`, `mine_attempt2.json`, `compare_run1.txt` (5 disagreements, mine), `compare_run2.txt`, `extras_out_attempt1_c4margin_panelA_only.txt`. Outputs: `integrity_out.json`, `integrity2_out.txt`, `stages_out.txt`, `recompute_run1..4.txt`, `mine.json`, `compare_run3.txt`, `comparisons.tsv`, `extras_out.txt`, `timing_out.txt`, `results_flat.txt`. `tree579/` is the `git archive` of the frozen commit.

**AGREES WITH NOTED DEFECTS**
