# Independent specification review — draft ADR-0026 (P10-I-S3, longer training)

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-17 UTC. Launched by the lead (Claude Fable 5.2). The reviewer did not write the draft or any code or analysis it relies on.
- Reviewed file: `docs/decisions/ADR-0026-p10-i-s3-longer-training.md`, SHA-256 `b5a12c6128a88ad15208266d4b0645d7abe7763ee8dd667607d53cf0daf6db73`, untracked, in worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-i-specs`, HEAD `c525898f7471a4f8af7fcfeb16c4c714e7f7c10c`.
- Siblings read: ADR-0023, ADR-0024 (`40c6876d…`), ADR-0025 (`ec166414…`), ADR-0027 (`c659ed0f…`), ADR-0028.
- This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** a human approval. `Astra review: NOT_PERFORMED`.
- Nothing was trained, downloaded or run apart from the arithmetic in section A. No file other than this one was written. No git writes.

## Verdict: NOT READY

There is one BLOCKING finding (F1). Rule 3 of section 5.2 lets the duration, or whether the study runs at all, be chosen by discretion after calibration statistics have been seen, and those statistics are effectively the outcome on three of the nine registered parents. All the other problems can be fixed by changing the text. Two of them need a ruling from the human lead: F5, on the third regime, and F1(c), on whether a fixed 16,384-update run with a convergence check meets the direction. Every number quoted from a record that I could recompute matches (section A). I found no number that is wrong.

## A. Numbers recomputed from records

Script: my own code, standard library only, no `arborlm.*` import. It reads `results/p4-2026-11-12/per-run.csv` and each `b*-{memory,dense}-*/result.json` in P4 and P5. Command: `python3 -I <scratchpad>/check_p4p5.py <worktree>`, Python 3.15.1 (system `python3`), macOS. The script text is in Appendix 1.

| Draft claim (location) | Recomputed | Status |
|---|---|---|
| 512 updates; 256 snapshot saved, not evaluated (§2 row 1) | `configs/p4_frozen_capacity.toml`: `steps = 512`, `checkpoint_steps = [0, 256, 512]`, `evaluation_steps = [0, 512]` | match |
| 198,401 trainable (§1, §3.2) | From `pilot_model.Memory`: keys 65,536 + values 131,072 + wq 512 + wo 1,024 + gate 1 + router 256 = 198,401. Flat = 198,145. Dense 2·3,100·32 + 1 = 198,401 | match |
| C 0.021988695, P 0.022221519, Q −0.006182638, each sign 27/27 | 0.021988695 / 0.022221519 / −0.006182638; C>0 27, P>0 27, Q<0 27 | match |
| 10/27 cells and 2/9 parents with Q ≥ −0.005 | 10 and 2 (parents B103/O301 −0.0038 and B103/O303 −0.0035) | match |
| −0.005 tolerance = P4's K1 | ADR-0009 l.83: mean Q ≥ −0.005, 22/27 cells, 8/9 parents | match |
| Memory share of dense gain 0.78 (of the means), 0.62–0.90 per cell | 0.7805; 0.6193–0.8997 | match. The highest cell is 0.8997, just under K2's 0.90 |
| SD of C within a parent 0.0005–0.0027; "0.005 is 2 to 10 times" | 0.000518–0.002708, which gives 1.85 to 9.66 times | match (rounded) |
| 217–421 distinct selected slots, mean 323 | 217, 421, 323.19 (`final.retrieval.unique_selected_slots`) | match |
| Shuffled minus baseline +0.00023 (range −0.0026 to +0.0045) | +0.00023 (−0.00259 to +0.00449) | match |
| 27.6 / 6.0 / 8.3 ms per update | P4 tree 14.118 s per 512 = 27.57 ms; P5 learned tree 14.067; P5 flat 3.062 = 5.98 ms; dense 4.261 / 4.254 = 8.32 / 8.31 ms | match |
| 3.3× tree vs dense (§12) | 14.118 / 4.261 = 3.31 | match. Includes logs and saves |
| 152,515 FRESH chunks; ceiling 19,064 updates | `dataset_manifest.json`: eligible 156,611, `not_selected_after_ranking` 152,515; 152,515 / 8 = 19,064.4 | match |
| P5 means, +0.001388814, 15/14/13 of 27 | P5 README l.14–17, 28, 41 | match |
| P6 +0.00044 fixed / +0.00002 learned; prior about 0.0039 | P6 README l.74–83 (columns Fixed, Learned) | match |
| P10-S1 lessons (a)–(c) | AUDIT.md l.66, 72, 75, 90, 183 | match |
| P10-S0 6.09 h of 22 h, 0.40–0.63; P10-S1 25.39 h of 53 h | OUTCOME.md lines 37 and 17 | match |
| Cost rows: 452/98/136 s; R1 5.7 h; primary 10.3 h; 0–6.8 h; 0–4.4 h; total 12–23.5 h | 451.7/98.0/136.3 s; 5.72 h; 10.29 h; 6.75 h; 4.41 h; 12.3–23.5 h | match. See F12 for the grid-extension worst case |
| 2.4 MB per snapshot | 198,401 × 4 B × 3 (parameters + Adam m, v) = 2.38 MB | arithmetic matches; not measured |

My own error log: (1) the P6 column order (fixed, then learned) was checked against the header row, not assumed. (2) My first draft of F5 costed REP-U at "54 runs × 588 s ≈ 8.8 h" and the rehearsal at "18 runs ≈ 3.0 h". Both were wrong: 588 s is the cost of a tree run plus a dense run, not of one run. The corrected figures, 4.4 h and 30 runs ≈ 2.5 h, are in F5. I am recording the mistake as the audit policy requires.

**One factual nuance (F15, ADVISORY).** In §2, "the all-slot shuffle mostly replaces trained values by untrained ones" is an inference. Slots that the panel does not select may still have been selected, and so trained, during training. The record only shows that the swapped-in values have almost no effect. Reword to "values of slots not selected on the panel".

## B. Findings

### F1 — BLOCKING — §5.2 rule 3, §7 row "U\* and the update ladder", §10 last row: a discretionary choice after seeing calibration results, presented as a convergence rule

**Problem.**
(a) Rule 4 sets U\* ≥ 16,384. The FRESH pool stops at 19,064 updates, and the rule's only larger rung is 32,768, which FRESH cannot reach. So the rule can return only U\* = 16,384 or hand the decision to the human lead. This is a fixed duration with a convergence check, not a duration set by convergence.
(b) Rule 3 hands the decision to the human lead as a menu: (a) run NOT CONVERGED, (b) a larger corpus, (c) do not run. The lead may pick any option, with no rule, after seeing the rehearsal. The rehearsal shows these figures for the calibration cells (§5.3, bullet 3): every statistic of §6, including Q, K1–K3, C, C_dense and D1–D3, at every checkpoint. It also shows a 32,768-update probe in which memory and dense run side by side. The calibration cells are three of the nine registered parents (F6). The choice therefore depends on the outcome. Option (c) in particular makes it possible to drop a run whose calibration shows memory losing. DIRECTION §5 allows a design ceiling to be extended "only under a rule written in the specification". A menu is not such a rule.
(c) The rule is also likely to fire. For FRESH it requires every arm's improvement from 8,192 to 16,384 updates to be under 0.001 nats/byte. P4's gain was about 0.022 at 512 updates, and nothing in the records suggests the FRESH curves flatten to under 0.001 per doubling by 16,384. That is a judgement, not a measurement. If the rule fires, the discretionary path becomes the expected path.

**Change.**
1. State the design honestly: "U\* = 16,384, fixed by the direction's proposed minimum and the FRESH ceiling. The rehearsal checks convergence and assigns a CONVERGED or NOT CONVERGED tag. It does not choose the duration." Mark it `PENDING LEAD REVIEW`: the human lead must record whether this meets DIRECTION §4, "convergence-based duration".
2. Replace rule 3 with a rule that applies automatically. If any arm is NOT CONVERGED, the study runs at 16,384 with the tag. Option (b), a larger corpus, can only become a separate successor study with its own rehearsal on fresh draws, never this study. Option (c), not running, is allowed only on cost or engineering grounds, recorded before Decision 2, as for any other stop.
3. Remove the 32,768 REP probe, or seal its output (F2). It measures nothing usable for FRESH: it is 128 passes over 2,048 chunks.
4. Amend §7's limits table so that U\* has no extension path in this study.

### F2 — REQUIRED — §5.3 bullet 3, §14 Decision 2: unsealed calibration outcomes, and withdrawing a condition after observation

**Problem.** Printing every §6 statistic for the calibration cells before Decision 2 shows the decision-makers the result on a third of the registered parents. Withdrawing a condition ("only if NEG-REF or the synthetic registry shows it is defective") is a change of rule after observation. The safeguard "never because a memory arm fails it" cannot be checked once the memory statistics have been seen. The sibling ADR-0023 §5.2 already uses a blind rehearsal output: it writes `durations.json` plus a sealed curve file, the auditor recomputes the output from the sealed file, and the curves are opened only after the registered outcome. ADR-0026 is inconsistent with that design.

**Change.** Before Decision 2, the lead and the human lead see only the following: the rate table; the δ table per arm and regime, as CONVERGED or NOT CONVERGED flags and δ values; RATE-AT-EDGE flags; the NEG-REF and synthetic-registry pass or fail results; costs and storage. Per-arm NLL curves, Q, K1–K3 and D1–D3 for the calibration cells go into a sealed, hashed file. The auditor verifies the rate table and δ from that file and reports only agree or disagree. A condition found defective is not withdrawn. It is a specification amendment with an engineering stop, a recorded reason, a re-freeze and the human lead's approval, made before any sealed file is opened.

### F3 — REQUIRED — §1 line 1, §3.4 control X, §6.2 D3: what X measures; a mismatched read is not a context-free read

**Problem.** X gives each position the read addressed by another position's query. This is a mismatched read. The table calls it a test of "whether ... a context-free read would do", but a mismatched read can lower the loss by more than C, which pushes the model above baseline. So X ≥ 0.5·C can hold even when a context-free read, the same correction everywhere, would keep most of the gain. In that case D3 is met by the harm of mismatched content, not by any need for addressing. Any input-dependent module would also pass an X-type test, the dense adapter included (X_dense). D3 therefore shows that the read is query-specific, not that "the gain is tied to addressed content". The positive-label wording in §1 overstates what D2 and D3 show. P_used has the same issue, to a smaller degree: moving a trained value to a slot it does not belong to can also harm more than C.

**Change.**
1. Add a context-free control, X_mean: replace each position's read (the combined vector before W_o) by the mean read over the evaluation batch. Define D3 on H_mean − H, or require D3 on both X and X_mean. The gain kept by a context-free read, B − H_mean, is naturally bounded between 0 and roughly C, so "at least half the gain lost" means what it says.
2. Print B − H_used and B − H_x in each cell, and the number of cells in which an intervention pushes the loss above baseline.
3. Reword §1: D2 means the gain depends on which trained value sits at which address; D3 means it depends on the query (and on a context-free read not sufficing, if X_mean is adopted). No wording beyond that.

### F4 — REQUIRED — §3.4, §6.2, §6.7: the dependence test changed from P4; P4's figure cannot serve as the comparison

**Problem.** The draft replaces P4's all-slot shuffle by P_used and X, adds a 0.5·C ratio, and requires both controls. P4's P was approximately C by construction (§A: shuffled NLL sits at baseline +0.00023), and P4's flag 2 had no ratio. S3's line 1 is therefore strictly harder than P4's, apart from the harm effect in F3, and it measures something else. The draft does not say this. A NOT DEPENDENT result at U\* could later be read as "dependence was lost with longer training", but that comparison would be against P4's weaker control.

**Change.** Add to §3.4 or §12: "Line 1 is a stricter test than P4's flag 2 and is not comparable with it. Any statement about how dependence changes with duration compares P_used and X at S3's own 512-update checkpoint with the same controls at U\*. It is descriptive, and it never uses P4's P." P_used and X at 512 are already computed; the comparison rule needs to be written down.

### F5 — REQUIRED (`PENDING LEAD REVIEW`) — §3.3 table and last paragraph, §12, open choice 5: the two regimes cannot separate "additional unique data"

**Problem.** DIRECTION §4 asks that "duration, additional unique data and memory-specific learning can be told apart". REP and FRESH differ in two ways: the amount of unique data, and whether the backbone was fitted to that data. The backbone was trained jointly for 1,024 updates on ranks 0–2,047, four passes (`configs/p3_longer_training.toml`). The §3.3 table nevertheless says FRESH against REP isolates "additional unique data at equal duration". The draft admits the confound in its last paragraph and in §12, but the table still makes the claim. There is a second confound: at 16,384 updates REP is 64 passes over 131,072 target bytes, with a 198k-parameter addition, weight decay 0 and no schedule. Its endpoint is mostly a test of how fast each arm overfits.

A third regime is feasible. Train ranks 2,048–4,095 are in the ranked candidate pool. They were never used for training by the P2/P3 lineage (`configs/p2_optimization_followup.toml` and `p3_longer_training.toml` use ranks 0–2,048), and the ranking is a SHA-256 hash (`pilot_data.py` l.19), so they come from the same distribution. A regime REP-U (2,048 unseen chunks, reshuffled every epoch) separates the two contrasts: REP against REP-U at equal unique data is the "seen by the backbone" contrast, and REP-U against FRESH at equal unseen-ness is the unique-data contrast.

**Change.** Either:
- (i) add REP-U, at least for M-TREE and D-ADAPT at the primary checkpoint. Cost with the draft's own per-update figures: 27 cells × (452 + 136) s ≈ 4.4 h for both arms (54 runs), plus a rate search of 5 rates × 3 calibration cells × 2 arms = 30 runs ≈ 2.5 h (more if the grid is extended), plus a gate showing that ranks 2,048–4,095 were never used for training or evaluation; or
- (ii) have the human lead record that the direction's "additional unique data" is accepted as confounded with "unseen by the backbone". In that case rename the §3.3 row to "additional unique data, confounded with data unseen by the backbone", and word every FRESH-against-REP statement that way.

Also say in §3.3 why FRESH starts at rank 4,096 and not at 2,048.

### F6 — REQUIRED — §5, §12 bullet 5, open choice 2: calibration parents are registered parents

**Problem.** B101/O301, B102/O302 and B103/O303 are three of the nine registered parents. The draws are fresh (init seed, streams and panel), but the backbones are not. Effects: (a) rates are tuned on a third of the registered parents. Both arms are tuned the same way, so this is fair between arms, but the registered estimates on those parents are optimistic for both. (b) With F2 unsealed, the calibration statistics predict the outcome. (c) The calibration FRESH streams and the registered FRESH streams each use 131,072 of the 152,515 chunks, so their training sets overlap by about 86%. This does not leak panel data, but it should be stated.

**Change.** State all three points in §5 and §12. Add to §6.7 a descriptive readout of both lines on the six non-calibration parents only (18 cells, 6 parents), so that sensitivity to the tuning parents is visible. This changes no label. Adopt F2.

### F7 — REQUIRED — §4 "Seeds": calibration seed offsets are ambiguous and can run into ADR-0027's namespace

**Problem.** The calibration and rehearsal draws use "269001–269999, same offsets" with i = 9(B−101) + 3(O−301) + (s−2601). With s = 2691, i is 90, 102 or 114. Then P_used = 269301 + 10i + j reaches 270201–270444 and X = 269601 + 10i + j reaches 270501–270744. Both fall inside ADR-0027's proposed 270001–279999 and outside S3's own block. If instead i means the calibration cell index 0–2, every seed stays in range. The text does not say which. P_used and X seeds also carry no arm, regime or checkpoint index, so the same seed is reused across M-TREE and M-FLAT, REP and FRESH, and every checkpoint. That is harmless, and it pairs the arms, but it is not stated.

**Change.** Define i separately for calibration (0–2) and rehearsal (3), and state that the same permutation seed is reused across arms, regimes and checkpoints. The freeze gate must cover the full expanded seed set, including the component seeds derived inside the reused classes. `Memory(…, seed)` uses seed + 1000…5000 and `DenseAdapter` uses seed + 3000 and + 4000, so the registered seeds expand to 3601–7603 and 3691–7692. I found no collision in `configs/`, `src/`, `studies/` or `tests/`. Siblings: ADR-0023 uses 3001/3002/3091/3092 and 300001–309999 with tests 930xxx; ADR-0024 uses 2401–2405, 2491–2493, 240001–249999 and 924xxx; ADR-0025 uses 250001–259999, tests included; ADR-0027 uses 270001–279999 and 2701–2799; ADR-0028 uses 280001–289999. Even after expansion, none overlaps S3's ranges.

Correct the list of earlier namespaces in §4. "P9 17xx, 18xx and 179xxx" is incomplete. ADR-0023 §4.2, citing ADR-0020 §7, lists P9 170001–179933 and 1701–1702; P9-I 180101–182020, 1791–1802 and 900001–900233; P9-II 190001–191599, 1891–1902 and 910001–919999; P10-S0 tests 920xxx; P10-S1 tests 921xxx. ADR-0024 and ADR-0025 now exist. Replace "were not available" with their ranges.

### F8 — REQUIRED — §4 "Panels": the panel rule cannot be computed as written, and it ignores sibling studies

**Problem.** (a) No chunk can "share no byte with any text evaluated in an earlier study" if a byte means a byte value. Every chunk contains the letter e. The rule must mean overlapping byte positions. Validation chunks tile the rows without overlapping, and duplicates are already removed (`pilot_data.py` l.19–20), so for P1–P8 the rule is simply rank disjointness. P10-S2's 144 GEN windows, and its 100 false-trigger windows if they come from validation, are counted in teacher tokens over the raw text. They have to be mapped to (row, byte-offset) spans. (b) The rule excludes only earlier studies. ADR-0025 draws new ordinary GEN windows from WikiText-2 validation (seed 250906), and ADR-0027's S4 would run on S3's data. Whichever study freezes second could reuse the other's panel. (c) "Evaluated" should be "drawn or designated for any panel". P10-S2 stopped before its freeze, and it is unclear whether its windows were ever evaluated.

**Change.** Define the panels as: "chunks whose (row, byte span) overlaps no byte span designated for any panel or window by any earlier study or any P10-I sibling, with sibling panels mapped to row spans by a documented procedure." Reconstruct twice: `arbor-clerk` inventories, `arbor-auditor` reconstructs independently, and both reproduce the recorded P1–P8 panel SHA-256s. Write S3's two panels into a ledger that ADR-0025 and ADR-0027 must exclude. If the walk down the ranking runs out of eligible chunks, the run stops; this is an engineering stop.

### F9 — REQUIRED — §6.3, §6.4, §6.5: precedence is undefined, so two people could compute different labels

1. If K3 holds and mean C_dense < 0.005, the label table gives MEMORY AHEAD and §6.3 and §10 give NOT EVALUABLE. State that NOT EVALUABLE takes precedence.
2. In the §6.5 table, FRESH positive with REP INCONCLUSIVE or NOT EVALUABLE matches both row 2 ("not positive") and row 5. State that row 5 takes precedence, and that "not positive" means a registered negative label only.
3. §6.4 row 3 refers to "the losing arm". Define it, for example as "the arm with the higher mean NLL at U\*", including when the label is COMPETITIVE.
4. Define "mean" as the arithmetic mean over 27 cells of per-cell differences, in float64, computed from per-target sums. State that every comparison with a threshold is ≥ or > exactly as written, with no rounding before the comparison.
5. In §5.1, "If two rates are within 0.0005 … the smaller rate is taken" is ambiguous when three or more rates are close. Use "the smallest rate whose mean is within 0.0005 of the minimum".
6. ADR-0009's flag 1 also required mean final H < mean initial H. D1 drops this. State whether that is deliberate.

### F10 — REQUIRED — §12 and ADR-0027 §3 Route A: the outcome labels do not match the entry route

**Problem.** ADR-0027's Route A requires (A1) "dependence line registered positive" and (A2) competitiveness "registered positive or registered as within S3's own margin". Under ADR-0026's labels:
- "positive, REPEATED DATA ONLY" counts as a registered positive for both lines, so it satisfies Route A literally. ADR-0026 §12 says it "should not by itself support S4 entry".
- "Within S3's own margin" matches K1 alone. K1 true with K2 false is NOT COMPETITIVE in S3, yet it satisfies A2.
- ADR-0026 §12 asks for CONVERGED and no edge tag. ADR-0027 does not.
- Line 1 is computed for M-TREE only, while COMPETITIVENESS[FLAT] is a registered sub-label. ADR-0027 does not require both clauses to hold for the same arm, but Route B does.
- Each ADR defers to the other for the label names ("fixed in ADR-0027, by name" and "names of … ADR-0026 as approved"). The deferral is circular.

**Change.** List the qualifying labels in ADR-0026 §12 now: line 1 = DEPENDENT, BOTH REGIMES or FRESH ONLY; line 2 = COMPETITIVENESS[TREE] ∈ {COMPETITIVE, MEMORY AHEAD}, BOTH REGIMES or FRESH ONLY; both for M-TREE; with or without a requirement of no NOT CONVERGED or RATE-AT-EDGE tag, as the human lead decides. Record that REPEATED DATA ONLY and COMPETITIVENESS[FLAT] never satisfy Route A. Ask that ADR-0027 copy these names and drop "within S3's own margin". Consider renaming "positive, REPEATED DATA ONLY" to something without the word "positive", for example "REPEATED DATA ONLY (not a positive)".

### F11 — REQUIRED — §3.4, §8 gates, §11: no positive check of the intervention code, and the prefix identity is assumed

**Problem.** (a) No arm depends on memory by construction (open choice 7). NEG-REF checks only that identical tensors give 0, and the synthetic registry checks only the label logic. If the computation of the slot set S, the cyclic reassignment, the query permutation or the reimplemented read were wrong, D2 and D3 could fail silently. A natural-text NOT DEPENDENT result could not then be told apart from a bug. This was the P10-S1 lesson. (b) "One run serves every duration" holds only if the stream, the RNG and the checkpoint saves do not depend on the total length. The cost table and the per-duration logic rely on it, but no test checks it. (c) To apply X, P_used, the exhaustive read and prior-off with the classes left unmodified, `Memory.forward` and `lookup` have to be re-implemented: `lookup` hard-codes `visit=2`.

**Change.** (a) Add a unit test with a planted positive. Use a toy frozen backbone and a memory whose values are set so that each slot gives the exact correction for a disjoint set of queries. On it, P_used, X (and X_mean, F3) must each come out ≥ 0.5·C by construction, and NEG-REF must come out 0. (b) Add a gate: on the platform of record, a separate 512-update run is bitwise equal to checkpoint 512 of the 16,384-update run, for each arm and regime on one calibration cell. (c) Add a gate that the re-implemented read equals `Memory.forward` bitwise when no intervention is applied, for both variants, and that the exhaustive read with `visit=16` reproduces P6's tree-candidates path.

### F12 — ADVISORY — §9, §7: budget and caps

The worst case of R1 is understated. The edge rule allows up to 4 extra rates per (arm, regime), giving 72 more runs: 2 × 4 × 3 × (452 + 98 + 136) s = 4.57 h. R1 can therefore reach 10.3 h, not "about 8 h". With the probe (9 runs, 1.14 h) and the calibration evaluations, the rehearsal can approach 12–13 h against a 14 h cap. That is not "the worst case plus about half again", although the registered cap is (23.5 h → 36 h). The evaluation row of "about 2 h" leaves out the evaluations of the per-duration and anchor runs. My estimate, at 0.5 s each, is about 14,400 evaluations ≈ 2 h, more for the exhaustive read. Add F5(i) if it is adopted. Either state the true worst cases or derive the caps from them. Storage: about 2,500 snapshots × 2.4 MB ≈ 6 GB, which is consistent with "a few GB". The rehearsal measures it, as planned.

### F13 — ADVISORY — §6.6: the routing interaction

Keeping it descriptive agrees with DIRECTION §4, which makes intermediate checkpoints descriptive. A registered line across durations would contradict it. LITERATURE_AND_ROUTING_NOTE §3 says "test the interaction … in ADR-0026", so the human lead should confirm that a descriptive section satisfies that (`PENDING LEAD REVIEW`, open choice 6). The trend rule depends on the threshold: a mean of 0.0049 against 0.0051 counts as a change of label. Print ΔG = G(U\*) − G(512) with its sign count beside the label. Note also that G_train at each checkpoint mixes the effect of the per-duration rate with the effect of duration.

### F14 — ADVISORY — §5.2 reasons and §6.2–6.3 thresholds

- ε: "less than 0.002 over two doublings" assumes that the gain per doubling does not increase. State this as an assumption.
- 0.5: defensible as a convention, and it does not favour memory. It is most meaningful on X_mean (F3).
- K2's 0.90 is borrowed from an accuracy ratio in P10-S0. That reason is weak, but the threshold is conservative. K2 binds more than K1 only while mean C_dense < 0.05.
- None of the thresholds favours memory. The edge tags are symmetric. A failed memory cell counts against memory, while a failed dense cell makes the line NOT EVALUABLE, which is conservative.
- REP competitiveness can come from the dense adapter overfitting faster, with weight decay 0. Say this beside every REP line-2 label.

### F15 — ADVISORY — wording

- §2: "untrained" (see section A).
- §6.1: "2 to 10 times" is really 1.85 to 9.66.
- §12: the "3.3 times" figure is training wall time including logs and saves, not per-update compute.
- §10: "replay ≠ reference" is used but never defined in this draft.
- §4: how each cell's FRESH subset is drawn (a seeded permutation of the whole pool, first 8U) and how the 64 per-batch cyclic orders of X are generated from one seed must be written down.
- §7: list the 0.0005 tie tolerance, the 0.005 PAST-BEST margin, the 512-position X batch and the probe length among the limits.

### F16 — ADVISORY — missing NOT EVALUABLE or stop cases

Add these cases:
- the panel walk runs out of eligible chunks;
- every rate is non-finite for some (arm, regime) in calibration, so no rate can be chosen;
- BASE is missing or fails its bitwise check;
- S is computed with a different panel order between the enabled read and P_used;
- the gates of F11(b) or F11(c) fail.

## C. Binding constraints, item by item (DIRECTION §4 P10-I-S3, §5, §7)

| Constraint | Status |
|---|---|
| Rehearsal on fresh calibration draws sets a convergence-based duration and ONE primary checkpoint | One checkpoint: yes. Convergence-based: no, in effect a fixed 16,384 (F1) |
| 16,384 as the proposed minimum, only if supported | The budget supports it (12–23.5 h). Rule 4 makes the floor unconditional; acceptable, but the human lead should record that reading |
| P10-S1's update counts not carried over | Met (§2 last line, §5) |
| Intermediate checkpoints descriptive | Met; PAST BEST is a tag only |
| Repeated and fresh arms separate duration, unique data and memory-specific learning | Partly: unique data is confounded (F5) |
| Memory-disabled, value-permutation and addressing controls | Present. Memory-disabled is an identity check only (correct under a frozen backbone). The new controls are stricter than P4 but X measures mismatch harm (F3, F4) |
| Dense rate search at each duration | Met (§5.1), the same grid and rule for every arm |
| Two outcomes with separate thresholds | Met; precedence gaps (F9) |
| Whole matrix budgeted | Mostly; worst cases understated (F12); F5(i) not costed in the draft |
| P4/P5 not revised; S3's 512-update point a new measurement | Met (§3.3, §12) |
| Limits classified with rules (§5) | Rule 3 breaks the design-ceiling rule (F1) |
| Machine load stated (§7) | Met: no wall-time claim is registered, and cost measurement under load is flagged |

## Appendix 1 — checker script (run as stated in section A)

```python
import csv, json, glob, statistics as st, sys
R=sys.argv[1]; p4=R+'/results/p4-2026-11-12'; p5=R+'/results/p5-2026-11-13'
rows=list(csv.DictReader(open(p4+'/per-run.csv')))
base={(r['backbone'],r['order']):float(r['final_nll']) for r in rows if r['variant']=='baseline'}
mem={(r['backbone'],r['order'],r['seed']):r for r in rows if r['variant']=='memory'}
den={(r['backbone'],r['order'],r['seed']):r for r in rows if r['variant']=='dense'}
C={};P={};Q={};Cd={};SH={}
for k,r in mem.items():
    b=base[k[:2]]; H=float(r['final_nll']); A=float(den[k]['final_nll'])
    C[k]=b-H; P[k]=float(r['shuffled_nll'])-H; Q[k]=A-H; Cd[k]=b-A; SH[k]=float(r['shuffled_nll'])-b
# means, sign counts, Q>=-0.005 cells and parents, C/Cd share, within-parent SD of C,
# shuffled-minus-baseline; result.json: final.retrieval.unique_selected_slots and
# training_seconds_including_logs_and_saves for P4 memory/dense and P5 flat/fixed/learned/dense.
```

Output (abridged): `mean C 0.021988695 P 0.022221519 Q -0.006182638 Cd 0.028171332`; `C>0 27 P>0 27 Q<0 27`; `Q>=-0.005 cells 10`; `parent Q>=-0.005 2`; `share of means 0.7805`; `share per cell 0.6193 0.8997`; `SD C within parent 0.000518 0.002708`; `shuffled-baseline mean 0.00023 min -0.00259 max 0.00449`; `unique selected slots 217 421 323.19`; `p4mem 14.118 s/512 = 27.57 ms`; `p4den 4.261 = 8.32`; `p5flat 3.062 = 5.98`; `p5learned_tree 14.067 = 27.47`; `p5dense 4.254 = 8.31`.

`Astra review: NOT_PERFORMED`. This review is not an approval.
