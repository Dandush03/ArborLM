# P10-S1 — independent review of ADR-0021 revision 5 (DRAFT, shifted capacity grid), 2026-11-15

- **Reviewer:** Claude Opus 5.5 (auditor context; it did not write the draft, the design notes, the rulings or `rev5_arithmetic.py`). This is a Claude review. **It is not Astra review and not human approval. Astra review: NOT_PERFORMED.**
- **Scope:** specification review before any code change or run. Nothing was trained, no study stage was run, nothing was downloaded, no project file was edited. Only my own scripts were run, over existing records.
- **Inputs (HEAD `da78a0a`, branch `claude/p10s1`; SHA-256):** ADR-0021 rev 5 `ed07895b…`; `ADR-0021-rev4-with-s22-s24.md` `c04c21f9…`; `DESIGN_NOTES.md` `3fa310bf…`; `LEAD_RULINGS.md` `50c5eba5…`; `rev5_arithmetic.py` `b04c1d15…`, `.out` `55f6dfb0…`. Raw calibration records: `experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c/cells/*/{train.json,eval/u*/eval.json}` (main checkout), manifest `results/p10s1-calibration-2026-11-15/calibrate_manifest.json`.

## Verdict

**READY AFTER M1–M7** (text edits and one rule addition; no blocker). The minors are listed for the same edit pass. Rulings of the lead I would overturn: **9** (do not adopt). Rulings I accept with required text: **2, 5, 7, 8, 11, 12**. Rulings accepted as they stand: **1, 3, 4, 6, 10** (1 with a recording note, m12).

## Commands and environment

macOS (Darwin 27.2.0), Apple M5 Max (18 cores: 6 "Super" + 12 "Performance", `sysctl hw.perflevel0/1.physicalcpu`), 48 GB. Scripts beside this file.

```sh
S=<this folder>; W=<worktree>; X=/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c
python3 -I $S/a0_sections.py $W/docs/reviews/p10s1-revision5-2026-11-15/ADR-0021-rev4-with-s22-s24.md $W/docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md > a0_sections.out   # Python 3.15.1, stdlib
python3 -I $S/a1_calibration.py $X $W/results/p10s1-calibration-2026-11-15/calibrate_manifest.json > a1_calibration.out                                    # stdlib, raw records
python3 -I $S/a2_cost.py > a2_cost.out                                                                                                                       # stdlib
cd $W && uv run --locked python -I $S/a3_read_geometry.py > $S/a3_read_geometry.out                                                                          # Python 3.12.14, torch 2.8.0, seed 941777 (auditor-only)
cd $W/docs/reviews/p10s1-revision5-2026-11-15 && python3 -I rev5_arithmetic.py | diff - rev5_arithmetic.out                                              # reproduction only: byte-identical
```

**Failed checker attempts, kept:** `a1_calibration.attempt1_failed.out` (KeyError: my chance-interval table lacked n = 16,384; fixed by computing intervals on demand); `a2_cost.attempt1_failed.out` (my bug: loop variables `c2`, `c3` overwrote the fitted coefficient `c2`, so every "model" figure of its sections 6–7 was garbage; sections 1–5 of that attempt were unaffected; renamed and rerun); `a3_read_geometry.attempt1_failed.out` (numpy is not in `uv.lock`; rewritten on torch). None of these was a discrepancy in the draft.

## 0. What I confirmed (no finding)

- **Faithful carry-over.** §4, §15, §17–§23 and the Addendum are byte-identical to revision 4; §24 differs only by trailing blank lines; all six verbatim quotations (including "im ok with b") are present; the kept revision-4 copy is identical to commit `a235d48` (`a0_sections.out`).
- **The draft's arithmetic reproduces** byte for byte, and my independent transcription of the config's `madds_formula` gives the same counts: backbone 57.54 M; F-OQ / T-OQ / H8 / D-OQ = 62.43 / 60.35 / 58.14 / 74.52 M at 1,024; 75.60 / 60.99 / 58.53 / 124.41 at 4,096; 128.29 / 63.55 / 60.10 / 324.00 at 16,384. D-OQ widths 1,024 / 4,033 / 16,071 match 49h+1 within 0.008% (G8). Multipliers D-OQ/arm 1.19 / 1.65 / 2.53 (F-OQ), 1.23 / 2.04 / 5.10 (T-OQ), 1.28 / 2.13 / 5.39 (H8): every dense matched snapshot is ≤ 6·U_P on the analytic measure (`a2_cost.out` §1–2).
- **§1 facts 13–17 recomputed from raw counts** (not from `calibration.json`): every range in the fact-13 table, the dense figures of fact 16 and the rates of fact 17 match (`a1_calibration.out` §1, §6, §7). The lead's N2 efficiency reading also matches (u_T 4,117 / 2,628 and 5,629 / 3,016; ratios 0.638 and 0.536).
- **G2 intervals** [34,100], [192,325], [894,1,159] and the i thresholds (0.473 at a_use 0.25; 4.0 → 0.8956; 4.5 → 0.9537; 3.0 → 0.7576) are correct.
- **Counts:** 7+7+7+6+3 = 30 per replicate, 150 cells; calibration 8+12+8+40 = 68; W = 17,664 / 66,816 / 263,424 (F-OQ) and 9,536 / 9,728 / 10,496 (T-OQ) are right; T-OQ is SUBLINEAR, F-OQ is not.
- **The plateau guard does what §8.2 says.** Without it every calibration curve is "loaded on all four views" at 1,024–8,192 updates; with it, none is; at revision 4's registered run lengths it changes no plateau status (`a1_calibration.out` §3).
- **R2 at 32K/32K (ruling 6):** one dedicated row per fact, so the 32,768 unused rows of revision 4's 65,536-row table were never read and, with zero gradient and no weight decay, never moved. A 32,768-row table is functionally the same reference. Accept.
- **Extrapolations are marked** wherever U_L, bits per slot when full or anything at 1,024 slots is used (§1 fact 15, §2, §5.1, §8.8, §10.3, §25.6, DESIGN_NOTES). "16,384→65,536 NOT TESTED" is carried in §0, the printed capacity label, §8.9 item 12 and §12.
- **Stale text in §1–§16:** only §9's "Calibration blocked" row (m6). §14 names the old sizes only as the human lead's requirement, with the new sizes beside it.

## 1. Findings

### M1 (major) — Ruling 9 should not be adopted

A loaded cell with no F-OQ U_L would, under ruling 9, fix its transition as CAPACITY NOT TESTED and proceed with the study. Three things are wrong with that:
1. **It reverses the human lead's direction.** §23 records: "S1 does not proceed to its freeze with the capacity line fixed as NOT TESTED while a resolution is being worked out." §10.1 item 0b as drafted gives that decision back to the human lead. A lead ruling cannot replace it (AGENTS.md authority order, item 1).
2. **It would run a study that cannot answer anything.** If either loaded cell fails: no arm can be CAPACITY_SUPPORTED (§22 m13). The saturation pair becomes NOT FULL. Clause (a) of CAPACITY-NEGATIVE cannot be reached for F-OQ anyway (§25.4; m11). The result is about 25–35 charged hours that can only print NOT TESTED / NOT MEASURED, plus the efficiency line.
3. **A second automatic route is not needed.** The return costs nothing, because no registered seed exists at that point.

**Text I would accept.** Ruling 9 is withdrawn. Keep the third row of §10.1 item 0b's outcome table exactly as drafted, and add after the table:

> "This return is not automated: the human lead's direction of §23 stands. A loaded cell that is NOT LOADED WITHIN ITS CEILING makes CAPACITY_SUPPORTED unreachable in every arm (§22 m13) and fixes the saturation pair that uses it as NOT FULL, so the lead does not proceed without the human lead's recorded answer."

§8.7 row 5 stays as drafted.

### M2 (major) — Saturation line: what was already seen about it is not disclosed (ruling 12)

§8.10 says "Nothing seen so far decides it". §25.6 says the saturation pair has "Nothing" predicting it. §2 expectation 2 says the lead has no confident expectation. In fact one side of the pair 1,024 → 4,096 was observed before the line and its threshold were chosen:

- i\* is non-decreasing, and every possible U_L of 32K/4K is at least 196,608 (two consecutive passes, first candidate 131,072).
- On the calibration draws 32K/4K already held **1.887–1.943 bits per fact = 15.1–15.5 bits per slot at 65,536 updates** (`a1_calibration.out` §4).
- So ρ < 3.0 (SUBPROPORTIONAL) needs i\*(8K/1K; U_L) > **2.52 bits per fact (a_use 0.68; 20.1 bits per slot)** if 32K/4K stops where it was seen, and **> 2.67–3.00 (21.3–24.0 bits per slot)** if it stops at the check's extrapolated 2.0–2.25.
- The 4,096-slot store at load 4 already held 16.3–16.5 bits per slot.

The negative can be reached, so ruling 12's answer is "yes", but only if a slot in the 1,024-slot store holds about a third more than a 4,096-slot slot was already seen to hold. The threshold 3.0 predates every record and I would not move it; adding a band would mean a new number chosen after data. The issue is disclosure only.

**Replacement text for §8.10, bullet "It can return a negative"** (replace its last sentence):

> "What was seen bounds it from one side. On the calibration draws 32K/4K held 1.89–1.94 bits per fact (15.1–15.5 bits per slot) at 65,536 updates; i\* does not fall and every possible U_L of 32K/4K is at least 196,608. SUBPROPORTIONAL on 1,024 → 4,096 therefore needs 8K/1K to hold more than 2.52 bits per fact (20.1 bits per slot) if 32K/4K stops where it was seen, and more than 2.67–3.00 (21.3–24.0 bits per slot) if it stops at the check's extrapolated 2.0–2.25 — about a third more per slot than the 4,096-slot store was already seen to hold. Nothing has been run at 1,024 slots. PROPORTIONAL is the more likely verdict of this pair; the line is kept because its negative is reachable and its threshold predates every record."

**§25.6, saturation row, middle column:**

> "PROPORTIONAL is the more likely verdict: the 4,096-slot side is bounded below by what was seen (15.1–15.5 bits per slot at 65,536 updates), so SUBPROPORTIONAL needs at least 20.1 bits per slot at 1,024 slots (§8.10). Nothing was run at 1,024 slots."

**§2 expectation 2, append:** "The 4,096-slot side is bounded below by revision 4's calibration (§8.10), so a negative needs a 1,024-slot slot to hold at least about 20 bits."

**§25.4 item 2:** replace "is the measurement whose answer is not known" with "is the measurement whose answer was not seen; one side of it is bounded (§8.10)".

### M3 (major) — Saturation line: oracle-code crowding is a size-linked confound and is not named

The oracle query codes are fixed random unit vectors of width 16, and they do not grow with the store. At initialization (`a3_read_geometry.out` §2), the share of facts whose code has a neighbour above cosine 0.8 is:

| Facts | Share with a neighbour above 0.8 |
|---|---|
| 2,048 | 0.10 |
| 8,192 | 0.38 |
| 32,768 | 0.85 |
| 131,072 | 0.999 |

The mean nearest-neighbour cosine rises from 0.74 at 2,048 facts to 0.83 at 32,768. Every saturation pair compares a fact set with one four times larger. A falling ratio of bits per slot can therefore come from the crowding of the oracle's query codes, which is an artefact of the oracle's code width, and not from the store. The draft's list of causes (§8.9 item 9, DESIGN_NOTES §4) names the shared output projection and key interference but not this.

**Add to §8.10 "What it does not say":**

> "The oracle codes have width 16 and do not grow with the store; the share of facts whose code has a neighbour above cosine 0.8 is 0.10 at 2,048 facts, 0.38 at 8,192 and 0.85 at 32,768 (at initialization; auditor's computation). Each pair compares a fact set with one four times larger, so a SUBPROPORTIONAL verdict may come from crowding of the oracle's query codes rather than from the store. The separability figures of §7.3 are printed beside every ρ, and SATURATION-SUBPROPORTIONAL is never read as a property of the store alone."

**§8.9 item 9:** replace "(the shared output projection, interference between keys)" with "(the shared output projection, interference between keys, or crowding of the fixed width-16 oracle codes)".

### M4 (major) — Rulings 5 and 8: U_P per row also makes the 0.80 floor almost automatic

Ruling 8 asks whether U_P per row opens a route to a favourable label. It opens two, and the draft declares only the first.

1. **C2 becomes readable as CAPACITY.** This is declared in §25.6.
2. **The 0.80 floor of §8.4 becomes near-automatic.** This is not declared. The U_P rule picks the smallest U_P at which F-OQ reaches a_use ≥ 0.90 at 32K/16K on both calibration draws. That is the same cell and the same readout where the 0.80 floor is read. On the calibration draws, 32K/16K had a_use 0.910–0.923 at 16,384 and 0.585–0.697 at 8,192 (`a1_calibration.out` §2). So the floor now passes by construction, up to the spread between calibration and registered replicates. In revision 4 it was an independent check at a fixed U_P.

In the other direction (harsher on the store), the larger U_P doubles the 32K/16K run to 98,304, which lengthens D-OQ's D-BEST reading there. Reading the floor at 8,192 instead would make CAPACITY_SUPPORTED unreachable by a choice made after the data, so I do not propose it.

**§8.4 row 3:** keep the rule and replace the bracketed note with:

> "*(lead's choice of 0.80, unchanged; read at 32K/16K because 32K/64K no longer exists. Since U_P of this row is the smallest value at which F-OQ reaches a_use ≥ 0.90 at this same cell on the calibration draws (§10.1 item 1), the floor is implied by the U_P rule up to the spread between calibration and registered replicates, and tests nothing beyond that spread; §25.6)*"

**§25.6, U_P row, right column, append:**

> "It also makes the 0.80 floor of §8.4 near-automatic (0.910–0.923 at 16,384 against 0.585–0.697 at 8,192 on the calibration draws). In the other direction, it doubles D-OQ's run at 32K/16K."

**§25.8 Q5:** replace "the cell is forced. Confirm." with "the cell is forced, and the U_P rule makes it near-automatic (§8.4). Confirm."

### M5 (major) — The cap rule's inputs, and concurrency with S0

**(a) The cap rule does not say which rates it uses.** C_need is "computed from the rehearsal's measured rates". The rehearsal runs each configuration for only 64 updates, which is dominated by start-up, and its isolated timing part is a single process. The check of revision 4's calibration found the measured six-worker training 26–40% above a projection built this way (`CHECK_LOAD_SEARCH.md`, M3). A cap computed from isolated rates is therefore biased low.

**(b) Concurrency with S0** (6 single-thread workers, about 15 h):
- Item 0a, the rehearsal's isolated timing and the throughput stage require that nothing else of the project is running (§10.1 item 0a, §10.2, §7.5, §10.3). None of them can run while S0 trains.
- `docs/reviews/p10-design-2026-11-15/EXECUTION_PLAN.md` item 3 allows only one study's registered or rehearsal stage at a time. Overlap of training stages is reserved to the human lead (§13 item 2).
- So S1's rehearsal and registered run wait for S0. **PENDING LEAD REVIEW / human decision:** the lead's standing wish to use the machine fully conflicts with item 3.
- S1's calibration training is neither a rehearsal nor a registered stage. Revision 4's calibration did overlap S0's rehearsal. If it overlaps again, its charged hours grow about 1.15–1.3× (3.3 → 3.8–4.3 h; `a2_cost.out` §8). The ledger stays well under the 16 hours in force (about 6–7.5 h). The item caps (twice an uncontended projection) are exceeded only if contention passes 2×.
- **MC multipliers from contended timing are unsafe.** Processes split across Super and Performance cores can change the ratios between arms, and with them MC-AMBIGUOUS (M7).

**Text I would accept, §10.3, replacing the first sentence of the C_need bullet:**

> "After the rehearsal, C_need = charged so far + 2 × the projected remaining time of the registered stages. Training is projected from the isolated timing rates of §10.2 multiplied by c, the largest ratio, over the configurations run in revision 5's calibration, of measured six-worker training seconds per update to isolated seconds per update of the same configuration (c is never below 1.0). Evaluation is projected from the rehearsal's measured seconds per evaluated snapshot times each cell's registered snapshot count. Packing is longest first on six workers."

**Add to §10.3, Stages:**

> "Item 0a of §10.1, the isolated timing part of §10.2 and the throughput stage run only when no other study of the project is training or evaluating on the machine. S1's rehearsal and registered stages do not overlap another study's rehearsal or registered stage (EXECUTION_PLAN item 3) unless the human lead decides otherwise (§13 item 2). If he does, c is measured under that overlap. Calibration training may overlap another study's training. Its charged hours are recorded as measured and enter C_need as charged."

### M6 (major) — Ruling 2's 256-slot cell: sound for F-OQ, but not specified

**Is top-8 of 256 slots a sound store? Yes, for F-OQ** (`a3_read_geometry.out` §1, random keys at initialization):

| | 256 slots | 1,024 slots | 16,384 slots |
|---|---|---|---|
| Effective slots read, softmax(score/0.2) over the top 8 | 7.16 | 7.48 | 7.81 |
| Mean weight on the top slot | 0.21 | 0.19 | 0.16 |
| Gap between the 8th and 9th cosine | 0.012 | 0.009 | 0.005 |

- **T = 0.2 behaves the same way at every size.** The read is close to uniform over the top 8, and selection is slightly more stable at 256 slots.
- **Interference per fact is the same at every size.** At load 8 about 465 of the other facts share at least one slot with a given fact at 256 slots, against about 500 at every larger size (random sets).
- **T-OQ is not defined at 256 slots.** There is one branch, and two are visited.
- **F-OQ-IVF degenerates to exhaustive.** There is one centroid, and 512 candidates exceed 256 keys.
- **It is the cheapest measurement.** It adds about +0.3–0.5 h of C_need with a search to 131,072, and +0.5–1.1 h with the 8K/1K candidate list (`a2_cost.out` §7).
- **It is the most open measurement.** Nothing has been run at either end of 256 → 1,024, unlike 1,024 → 4,096 (M2).

Keep it. As ruled, though, it has no run length, search, candidates, ceiling, fixed outcome, class membership, snapshot list, gate list or counts.

**Text I would accept (new bullet in §5.1, with consequential edits):**

> "**Cell 2K/256 (saturation line only; the lead's addition, outside the sizes of §24).** F-OQ only, the 2,048 facts and training stream of the row of 2,048 facts, in 256 slots (load 8). T-OQ is not defined at 256 slots and F-OQ-IVF would read every key, so neither is run or read there. The cell enters no capacity step (2K/256 → 2K/1K is not a step), no efficiency step, no dense label and no seed block. Its run length U_L is found by §10.1 item 0b for F-OQ alone, on both calibration draws, with the candidates and ceiling of 8K/1K ({65,536, 98,304, 131,072, 196,608, 262,144}; ceiling 262,144). If F-OQ has no U_L there, the pair 256 → 1,024 is fixed as NOT FULL and printed '256 NOT MEASURED — NOT FULL WITHIN CEILING'; this does not return to the human lead. Snapshots as for a loaded cell. REF and DEP as for its row. Gates G1, G2, G4 (restoration), G5, G6 and G7 (W = 16·256 + 1,280 = 5,376) apply."

Consequential edits:
- **§6.1:** F-OQ has 8 cells; **31 configurations per replicate, 155 registered cells**; calibration **70 runs**. Item 0a times F-OQ at 256 slots.
- **§8.10 Registered pairs:** "256 → 1,024 for F-OQ only; 1,024 → 4,096 for F-OQ, F-OQ-IVF, T-OQ and H8." F-OQ's arm class reads both pairs; every other arm reads one. The printed outcome names the pairs read for each arm.
- **§8.7:** the milestone reading is unchanged. It requires a SUBLINEAR arm, so the 256 pair never enters it.
- **§12:** "b(256) is an F-OQ-only figure".
- **§10.1 item 4 and §10.3 (block S3):** state "not funded (lead's ruling 2)". The printed label is '16,384 NOT MEASURED — NOT FUNDED'.

### M7 (major) — MC-AMBIGUOUS has no rule for nearly equal costs, and §8.5 / §25.7 overstate what is established (ruling 11)

`classes.mc_pair` returns MC-AMBIGUOUS whenever the analytic and CPU measures disagree on which cell costs more. The analytic step multipliers are close to 1:

| Arm, step | Analytic multiplier |
|---|---|
| T-OQ, 1K → 4K | 1.011 |
| T-OQ, 4K → 16K | 1.042 |
| H8, 1K → 4K | 1.007 |
| H8, 4K → 16K | 1.027 |

So the CPU direction is all that separates a step from "Δ_MC undefined". A Δ_MC that is undefined means no CAPACITY verdict.

**Under the draft's own planning rates** (`a2_cost.out` §4):
- With anything at 1,024 slots set to the 4,096-slot rate, F-OQ's and T-OQ's 1K → 4K CPU ratio is 0.994, so C1 would be MC-AMBIGUOUS. That is an artefact of the assumption.
- With T-OQ at 2× F-OQ, D-OQ against T-OQ is MC-AMBIGUOUS at 4,096 and 16,384 slots. The "storage half" reading would then be reachable only through F-OQ-IVF. Ruling 11 accepts this; the text of §8.5 and §25.7 does not say it.

**My fitted per-update cost model** (`a2_cost.out` §3: t = 0.00679 + 4.5e-5 × arm M-madds + 0.00669 × M-params; within 5% of the five measured rates):
- It predicts CPU ratios for 1K → 4K of 1.22 (F-OQ), 1.14 (T-OQ, without its unknown gather overhead) and 1.10 (H8). The direction is likely, not certain, to agree.
- It predicts D-OQ / F-OQ at 1,024 slots of only 1.07. That margin governs the cost condition of STORE HOLDS MORE AT SATURATION at 8K/1K.

**Minimum text (required).** Replace in §8.5 "The matched-compute reading is therefore expected to be established for every arm on the analytic measure." with:

> "On the analytic measure every matching snapshot exists. The pair is established only if the CPU-time measure of §10.2 agrees on which cell costs more. Where the analytic difference is small (T-OQ and H8 between sizes, 1.01–1.04; D-OQ against an arm at 1,024 slots, 1.19–1.28) the CPU direction decides, and a disagreement gives MC-AMBIGUOUS. If T-OQ's measured cost exceeds D-OQ's, the 'storage half supported' reading is reachable only through F-OQ-IVF (§25.8 Q11)."

Make the same correction in §25.4 item 4 ("is expected to be established for every arm" → "exists on the analytic measure for every arm; whether it is established depends on the CPU measure") and in §25.7 (delete "On the analytic measure the reading is established for every arm at every size").

**Optional rule (PENDING LEAD REVIEW; it reverses §22 (i); it uses no new number; it must be fixed before 0a, because the direction becomes known at the rehearsal):**

> "If the two cost measures disagree on which cell of a pair costs more, the pair is read in the direction that favours the comparator. The cell whose advantage would be claimed (the larger cell on the capacity line; the memory arm in the dense labels) is treated as the costlier and read at U_P. The other cell (the smaller cell; D-OQ) is read at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures. MC-AMBIGUOUS is then printed as an annotation, and the pair counts as established."

### Minors

- **m1. Dense-rate edge rule.** §10.1 item 3 returns when "the chosen rate" is 0.1. The tie walk of §22 M7 picks the fastest learner among rates within 0.02 at the readout. 0.1 could therefore be "chosen" only because it learns faster at U_P/2–U_P/16 while several rates are equal at the readout, and then return for no reason. The rate grid exists to detect a limiting edge. **Text (PENDING LEAD REVIEW):** "…returns to the human lead if 0.1 has the highest readout by more than 0.02 at the selection readout, or if every rate diverged; a 0.1 chosen only by the walk of §22 M7 among rates within 0.02 at the readout is taken and recorded as EDGE BY TIE-WALK."
- **m2. Plateau guard (ruling 7): accepted.**
  - It cannot bind at 32K/4K: i\*(65,536) ≥ 1.89, and U_L/2 ≥ 98,304.
  - At 8K/1K it binds only if the store saturates below 3.8 bits per slot. ρ would then be ≥ 16, so the guard would hide a positive, not a negative. It does not wrongly exclude a store that saturates genuinely low in a way that changes a verdict towards the store.
  - Its label is misleading, though. **Add to §8.2:** "A cell that meets the gain condition but not the floor is printed FLAT BELOW THE DEP FLOOR, not as still improving." **Add to §8.5, dense at saturation:** "where D-OQ fails the plateau only by the floor, print DENSE NOT LEARNED, not DENSE STILL RISING."
- **m3. UNDERTRAINED-AT-U_P** (§8.4, §10.1 item 2) is undefined at 2K/1K, 8K/1K and 32K/4K, where H8 is not calibrated. **Text:** "At a cell where H8 was not calibrated, its classes carry H8 NOT CALIBRATED AT cell."
- **m4. §8.10 arm class has no DEPENDENCE_FAILED row.** A DEPENDENCE_FAILED pair now falls to INTERMEDIATE. **Insert as the second row:** "DEPENDENCE_FAILED (some registered pair is DEPENDENCE_FAILED)." Insert the matching row in the outcome table: "SATURATION-INCONCLUSIVE with reason DEPENDENCE_FAILED."
- **m5. Item caps of 0a / 0b.** It is unclear whether a cap applies to the item or to a run. **Text:** "An item's cap is twice its projected wall time at six workers. A run still running when its item's cap is reached is stopped, kept, and has no U_L."
- **m6. §9, row "Calibration blocked".** Replace "U_P is fixed, not tuned; the load is measured before the freeze and mapped to rows by a fixed rule" with "U_P is set per row by a fixed rule (§10.1 item 1), not tuned; each loaded cell's run length is found by a fixed search with fixed outcomes".
- **m7. Printed labels.**
  - Efficiency outcome: add "SIZES 1,024–16,384".
  - SATURATION-PROPORTIONAL: add "EIGHT FACTS PER SLOT; FULL = PLATEAU RULE WITHIN REGISTERED RUN LENGTHS".
  - Rename the arm class SATURATION_SCALES to SATURATION_PROPORTIONAL_ALL_PAIRS. "…SCALES" is one word away from the banned summary "ArborLM's capacity scales".
- **m8. Reachability of CAPACITY-NEGATIVE.** **Add to §8.7 after the table:** "On the registered grid clause (a) cannot be reached for F-OQ (NO GAIN and NULL need a loaded smaller cell whose step is flat, §25.4; REVERSED needs the larger cell behind at its full run length). CAPACITY-NEGATIVE can therefore arise only from clause (b), that is from the dense labels."
- **m9. Recording C_max (ruling 1).** The draft calls C_max "the human lead's ceiling"; the ruling sets it as the lead's.
  - **Text for §10.3:** "C_max = 36 charged hours, set by the lead under the Addendum's delegation on 2026-11-15, before any registered seed was observed; it is reported to the human lead with the adoption of revision 5."
  - 36 h is 2.25 times the human lead's last explicit figure (16 h). Telling him is a courtesy the delegation does not require; it is still advisable. PENDING LEAD REVIEW.
- **m10. The draft's high end double-counts evaluation.** Manifest task seconds already include the calibration's evaluations, and 1.5–2.5 h of evaluation is added on top. This is conservative and acceptable. Test fixtures for `budget.py` must not copy the planning rates in which 1,024-slot cost equals 4,096-slot cost (M7).

## 2. Item 1 of the brief — rules chosen after the data, and whether every verdict is reachable

| Rule | Chosen after data? | Direction relative to a predicted answer | Verdicts reachable, and by what |
|---|---|---|---|
| Sizes 1K/4K/16K at load 8 (human lead, §24) | yes, declared | makes C1/C2 near-certain positives for F-OQ (§25.4) | CAPACITY STEP by plateau, MU/MC/SAT; GAIN WITHIN BUDGET if a replicate's plateau fails; NOT LOADED by the search; NO GAIN unreachable for F-OQ (m8) |
| Row of 32,768 facts | yes, declared; forced by load 8 at 4K | as above | as above |
| U_L search with ceilings | the ceilings yes, declared; the rule reuses the plateau rule | cost bound only; two passes give margin (a first pass at U_{k−1} implies a gain well below 0.10 at U_k) | every outcome row reachable; a return when F-OQ has no U_L (keep it, M1) |
| 6·U_P everywhere | yes, declared | harsher: longer D-OQ runs, so D-BEST and DENSE AHEAD come easier | — |
| U_P per row | yes, declared for C2 only | favourable: C2 readable, 0.80 floor near-automatic (M4); harsher: longer D-OQ at 32K/16K | return if no U_P qualifies (none expected) |
| Plateau guard | yes, declared | removes false "loaded" only (m2) | — |
| Saturation line, 3.0 | the line yes; the number no | PROPORTIONAL likely on 1K→4K (M2); confound M3 | PROPORTIONAL; SUBPROPORTIONAL if b(1K) ≥ 20.1 bits per slot; NOT FULL; NOT MEASURED |
| Dense at saturation, binding (ruling 4) | yes | harsher on the store | DENSE HOLDS MORE needs D-OQ to hold more than about 0.36 bits per parameter at 50K / 198K parameters; reachable |
| Efficiency on control steps only | yes | removes a positive route (REACHED ONLY BY THE LARGER on loaded steps) | N2 at an F-OQ cost of 1.70× needs a u_T ratio ≤ 0.47 for FASTER, against 0.54–0.64 seen; EFFICIENCY-POSITIVE is very unlikely; NEGATIVE is reachable |
| 256-slot cell (ruling 2) | yes | neutral; nothing seen at either end | as the saturation line, F-OQ only (M6) |
| Dense rates up to 0.1 | yes | stronger control, harsher on the store | return at the edge (m1) |

## 3. Item 4 of the brief — hours, recomputed

Computed with LPT packing on six workers, my rates from the raw records, evaluation from measured seconds per snapshot × registered snapshot counts × 1.5–3 (F-OQ ×2 for the index read), and the draw-1 seed block included (`a2_cost.out` §5–6):

| U_L (8K/1K, 32K/4K) | C_need, mine (draft rates / fitted model) | C_need, draft |
|---|---|---|
| 98,304 / 196,608 | 21.0–26.8 / 20.4–26.0 | 21.8–29.2 |
| 131,072 / 393,216 (central) | 25.5–32.3 / 24.7–31.3 | 26.2–35.2 |
| 262,144 / 524,288 (both ceilings) | 30.4–38.5 / 29.2–36.9 | 31.1–41.8 |

- **What drives the range:**
  1. U_L: about 5 h between early and ceilings. The long cell 32K/4K is doubled.
  2. T-OQ's cost: about 4 h between 1× and 2× F-OQ. It is never measured, and analytically T-OQ is cheaper than F-OQ.
  3. Contention: at 1.25× it adds 6–8 h.
  4. Evaluation: about 2 h.
- **Is C_max = 36 workable with the three fixed cuts? Yes, without contention.** Every case fits, at worst after cut 2: 35.9 h with draft rates and 34.4 h with the model, both at the ceilings with T-OQ at 2×.
- **It fails with contention.** At 1.25× contention it fails for T-OQ at 2× from the central U_L upward: 36.2–43.3 h after cut 3.
- **The cuts are worth little:** cut 2 about 2.1–2.6 h, cut 3 about 0.6 h.
- **The cheapest sound way to cut:**
  1. Do not overlap S1's registered stages with S0, as EXECUTION_PLAN item 3 already requires. This costs no science.
  2. Then, in this order: H8 at the two loaded cells (1.8–2.0 h); a 393,216 ceiling at 32K/4K, which bounds the worst case at 28–38 h. Both are the human lead's choice under ruling 3.
- **What concurrency with S0 does:**
  - The calibration, if overlapped, charges about 3.8–4.3 h instead of 3.3 h.
  - Item 0a, the rehearsal's isolated timing, the rehearsal itself, the registered stages and the throughput stage must wait for S0 (M5).
  - If the human lead allows the registered run to overlap, C_need must use contended rates (M5 rule). Otherwise the cap is biased low by the contention factor.

## 4. Item 6 of the brief — what an implementer must change (list only; nothing edited)

DESIGN_NOTES §11 is accurate and complete for the draft. In addition:

1. **2K/256 (M6).**
   - `core`: grid, snapshot set, calibration builders (search for F-OQ alone, 2 runs), registry counts 31 / 155 / 70, `doq_hidden` not needed.
   - `classes`: saturation pairs per arm, F-OQ two pairs.
   - `gates`: G5 / G7 at 256; T-OQ and F-OQ-IVF refused at 256.
   - `train` whitelist; `timing` 0a at 256; `report` per-arm pairs.
2. **MC tie handling (M7):**
   - the minimum: a test that `mc_pair` returns MC-AMBIGUOUS at equal CPU, and that the report says which pairs it is;
   - if the optional rule is adopted, a new `mc_pair` branch with the comparator rule.
3. **Cap inputs (M5).** `budget.py`: the contention ratio c from calibration over isolated rates; evaluation from rehearsal seconds per snapshot × registered snapshot counts; LPT packing; `cap_max_hours = 36` with its source string.
4. **Concurrency guard.** A refusal in the 0a / timing / throughput launchers if another study's workers are running (process check), recorded in the manifest.
5. **New labels:** FLAT BELOW THE DEP FLOOR, DENSE NOT LEARNED (m2); H8 NOT CALIBRATED AT cell (m3); a saturation DEPENDENCE_FAILED row (m4); EDGE BY TIE-WALK if m1 is adopted; the renamed arm class and the extra printed-label text (m7).
6. **Separability (M3).** Separability (§7.3) is computed at the saturation cells and printed beside every ρ.
7. **Item caps (m5).** In `stages.py`, stop a run at its item cap and mark it as having no U_L.
8. **Seeds.** G9 with 2193 and its derived seeds (2193 + 1000·k).

**Places where the draft is too vague to implement one way:**
- ruling 2 (M6);
- the rates feeding C_need (M5);
- the item-cap semantics (m5);
- UNDERTRAINED-AT-U_P at uncalibrated cells (m3);
- MC with equal CPU cost, |r − 1| ≤ EPS (M7);
- what "nothing else of the project running" means while S0 runs (M5).

This is a Claude review, not Astra review, and not human approval.
