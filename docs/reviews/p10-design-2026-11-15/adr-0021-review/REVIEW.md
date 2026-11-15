# ADR-0021 (P10-S1) design revision 1: independent specification review

- **Reviewer:** Claude Opus 5.5 (model id `claude-opus-5-5`), specification auditor for this study only. I ran in a context separate from the integration work. I did not touch git state, GitHub or any tracked file, did not commit and downloaded nothing. This review is independent engineering and mathematical evidence. **Astra review: NOT_PERFORMED. This is not Astra validation and not a human approval.** The human lead has said the lead may self-approve P10 studies after a clean Opus review, so this is the main independent check, and I wrote it adversarially.
- **Object:** `ADR-0021-p10-s1-useful-capacity-scaling.md`, "DESIGN REVISION 1 — DRAFT FOR THE LEAD, NOT YET REVIEWED" (519 lines), in the session scratchpad outside the repository. I checked it against the human lead's binding S1 requirements as relayed in my task, `AGENTS.md`, `CLAUDE.md`, ADR-0017 (§4–§8, §15, §18), the ADR-0017 design-review history (`docs/reviews/adr-0017-design-2026-11-14/REVIEW.md`, `RECHECK.md`, `CONFIRM.md`), `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`, `docs/reviews/p9i-results-2026-11-15/REVIEW.md`, `results/p9i-calibration-2026-11-14/README.md`, `results/p9i-rehearsal-2026-11-14/` (README and `rehearsal_cells.csv`), `studies/p9/model.py` and `studies/p9i/model.py`, `studies/p9i/core.py`, and the sibling drafts ADR-0019 rev 4 and ADR-0022 for namespace and style. Worktree HEAD `ecd5b87`, branch `claude/adr-0017-design`.
- **Environment:** Apple M5 Max (18 cores), macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0 (CPU), no numpy, `uv run --locked` against the worktree's lock (no lock change, no new dependency). Every command was run from this folder as `uv run --project <worktree> --locked python -I <script> [args] > outputs/<name>.txt`. The machine was shared with other sessions (load average 4 to 15 during the toy runs); no number below is a timing measurement except the toys' own CPU-seconds, which are indicative only. `uv run --locked ruff check --config docs/reviews/ruff.toml --extend-ignore E501,I001,E401,E702,F841,E701,E402,F401 <this folder>/*.py`, run from the worktree root, passes (a `ruff.toml` copied from the ADR-0019 review folder sits here for when the folder moves under `docs/reviews/`).
- **What I ran:**
  - `c2_arithmetic.py`: Fano values, thresholds, binomial intervals, replicate probabilities, parameter counts, counted work. Pure arithmetic.
  - `c4_matrix_budget.py`: matrix recount and training projection from the P9-I rehearsal per-update costs (read-only).
  - `c1_store_toy.py`: a **synthetic stand-in** of the S1 store under oracle addressing (no ArborLM backbone, no ArborLM data generator, no ArborLM seed; synthetic seed 941001). Same read path as `ScalableMemory.delta` (cosine keys, top-8, temperature 0.2, softmax, values, `wo`, gate at −2), AdamW 0.003, clip 1.0, batch 128, N(0, 0.02) init; the frozen upper block, LayerNorm and unembedding are replaced by a fixed random readout after LayerNorm. Arms F-OQ, H8, R2, D-OQ (as drafted), F-OQ-wide, H8 at widths 127 and 8, and two dense variants (`c1b`: conventionally initialized dense; P9-style dense at lr 0.01). Load sweep to 65,536 updates (`c1c`).
  - `s9c_seed_keys.py` (structured scan of every JSON, JSONL, TOML, Python, Markdown and text file in the worktree and in `experiments/` for seeds in S1's ranges) and `s9d_positive_control.py` (the same scan for P9-I's known seeds, to show it detects them).
- **What I did not run:** any ArborLM model; anything on registered, calibration or rehearsal draws of any study (the toys use no ArborLM generator at all); any seed in 190001+, 200001+, 210001+ or 220001+; any registered stage; any edit to a tracked file; any commit.
- **Failed attempts, kept:** `outputs/c2_arithmetic_attempt1_FAILED_overflow.txt` (my binomial CDF overflowed a float; fixed with a log-space pmf; no number changed). `outputs/s9_seed_scan_attempt1_TOO_NOISY.txt` (a regex scan of all 6-digit tokens: 1,617 hits, all hashes and counters, unusable). Attempt 2 (the same regex restricted to lines mentioning "seed") was too slow on `experiments/` and I killed it after about 25 minutes (`outputs/s9_seed_scan_attempt2_KILLED.txt`); a ripgrep variant produced only false positives on single-line JSON files (`outputs/s9b_seed_rg_attempt2_FALSE_POSITIVES.txt`). The structured scan `s9c` replaced them. `s9d`'s header line still reads "ADR-0021 ranges" because I changed only the range test; its hits are P9-I's seeds (my labelling slip, not a data issue).
- **Script change during the work (disclosed):** `c1_store_toy.py` was extended after its first batch had started: a conventionally initialized dense arm (DOQS), a per-job learning rate, and the learning rate in the printed line. The code paths of the first batch's arms are unchanged (the running workers had already imported the module); lines of `outputs/c1_store_toy.txt` therefore lack the `lr=` field, and their learning rate is 0.003.
- **My own errors found while reviewing:** none retracted. The stand-in's speed bias is stated in §0 and limits how I use it.

## Verdict: **NOT READY** for the lead's self-approval

Four blockers, eleven majors, and a list of minors. Every item has replacement text. The blockers share one theme: as drafted, the dense gate and the parameter control cannot fail in the memory's disfavour, the negative outcome can fire on an unevaluated study, and the registered grid is unlikely to load the memory at all, so the most likely registered outcome is CAPACITY-INCONCLUSIVE for reasons fixed by the design, not by the store. None of the fixes relaxes a threshold. Numbers in **[brackets]** are the lead's to choose and must be fixed before calibration.

---

## 0. Key evidence (diagnostic; stand-in, not results)

The stand-in learns faster than the real system: its oracle-query arm at 32,768 facts / 65,536 slots is at 0.989 by 4,096 updates, where P9-I's calibration R1 was 0.430 (`results/p9i-calibration-2026-11-14/README.md`). Its readout is a linear map after LayerNorm, easier than the frozen block 1. So it **over-states** how much a slot can hold and how fast; it says what the read path and the optimizer can do, not what the backbone allows. I use it only where the direction of the conclusion survives that bias.

| Check | Output | Finding |
|---|---|---|
| Does load 2 overload the store? | `c1_store_toy.txt` | F-OQ 8,192 facts / 4,096 slots (load 2): 0.957 at 2,048 updates, **1.000 at 8,192**. F-OQ 32,768 / 16,384 (load 2): 0.959 at 8,192, 0.986 at 16,384. H8 at load 2: **1.000** at 8,192 / 4,096 and at 32,768 / 16,384 by 4,096 updates. |
| Load 8 | `c1_store_toy.txt` | F-OQ 8,192 / 1,024 (load 8): 0.962 at 16,384. F-OQ 32,768 / 4,096 (load 8): 0.577 at 8,192, **0.799 at 16,384, still rising** (not plateaued by the draft's rule: +1.36 bits over the last doubling). |
| Load sweep to 65,536 updates | `c1c_load_sweep.txt` | F-OQ at 4,096 slots, value at 65,536 updates (last-doubling gain): load 2 **1.000** (reached by 8,192); load 4 **0.997**; load 8 **0.960** (+0.41 bits, still rising); load 16 0.579 (+0.46, still rising). At 16,384 slots: load 2 **0.999**; load 4 **0.988** (+0.28); load 8 (131,072 facts) 0.836 (+0.87, still rising). On the stand-in a slot holds at least 4–8 facts, and what keeps loaded cells below ceiling is updates and exposures per fact, not storage. No load reaches a plateau below 0.80 within 65,536 updates. |
| Step verdicts the draft would print on the stand-in (F-OQ, U_P = 8,192, U_run as §5.4) | derived from `c1_store_toy.txt` | A1: CEILING (i(8K/4K; 8,192) = 5.00). A2: CEILING. B1: **EFFICIENCY** (Δ_MU = 4.55 − 1.92 = 2.63, but 32K/4K gains 1.36 bits over its last doubling, so it has not plateaued). B2: CEILING (i(32K/16K; 8,192) = 4.55 ≥ 4.5). Arm class INTERMEDIATE → CAPACITY-INCONCLUSIVE, or **CAPACITY-NEGATIVE** through the vacuous clause of B1. |
| D-OQ as drafted (P9 adapter: bias-free, N(0, 0.02), gate −2, on a unit 16-d code) | `c1_store_toy.txt`, `c1b_dense_variants.txt` | At equal parameters and 16,384 updates: 8K/4K **0.161** (F-OQ 1.000); 8K/16K 0.202; 32K/16K 0.041. Same D-OQ at lr **0.01**: 8K/16K **0.626**. A conventionally initialized dense (PyTorch default init with biases, same parameter count) at 8K/4K: **0.979**. Conventional dense at 8K/16K: 0.868 at 8,192 and **1.000 at 16,384** (F-OQ 1.000 at both); at 32K/16K: 0.180 at 16,384 (F-OQ 0.986). D-OQ as drafted at 65,536 slots: 0.261 (8K) and 0.037 (32K) at 16,384 updates. |
| Iso-parameter wide-value cells | `c1_store_toy.txt` | F-OQ-wide 8K/4K (d_v 175): 0.833 at 1,024 updates against F-OQ's 0.141, then 1.000 like F-OQ. H8 width 127 at 8K/4K: 0.928 at 1,024 against 0.117. **Wider values only speed optimization**; they add no expressive capacity (math in M1). On the stand-in the parameter label would print PARAMETER-DRIVEN (d = 0) with both cells at ceiling. |
| Fano and thresholds | `c2_arithmetic.txt` | i(0.5) = 1.523, i(0.8) = 3.287, i(0.9) = 4.036, i(0.95) = **4.466**; i = 4.5 at a_use = 0.9537. +0.5 bit needs +0.12 accuracy at 0.3, +0.096 at 0.5, +0.057 at 0.9. |
| Replicate probabilities | `c2_arithmetic.txt` | all 5 of 5: 0.0312; ≥ 4 of 5: 0.1875; all 4 of 4: 0.0625; ≥ 3 of 4: **0.3125** (the draft does not state this one). |
| G2 intervals (level 1 − 0.001/40) | `c2_arithmetic.txt` | 2,048: [34, 100]; 8,192: [192, 325]; 32,768: [894, 1,159]. Family-wise false-fail ≤ 0.0010. |
| Parameter counts | `c2_arithmetic.txt` | F-OQ 197,633 / 787,457 / 3,146,753. D-OQ h = 4,117 / 16,405 / 65,557 within 0.01%. F-OQ-wide 787,937 (+0.061%). H8 4,096 × 127: −0.201%; 65,536 × 8: −0.146%. All as the draft states. |
| Counted work | `c2_arithmetic.txt` | T-OQ 8,704 / 9,472 / 12,544 (step ratios 1.088, 1.324); F-OQ 65,792 / 262,400 / 1,048,832. As the draft states, except that `wo` (1,024 MACs; 5,600 at d_v 175) is omitted for the memory arms while D-OQ's output layer is counted. |
| Matrix and projection | `c4_matrix_budget.txt` | 36 configurations, 180 cells, 22 calibration runs: confirmed. Training 15.0 CPU-h at U_P = 8,192 (draft 15.8) and 30.0 at 16,384 (draft 31.5). At 8,192 the 12 h cap holds with twofold headroom and no cut (2 × 3.60 h = 7.20 h ≤ 11.25 h). At 16,384 it needs cuts 1–3 on my recount (draft: 1–4). |
| Seed collisions | `s9c_seed_keys.txt`, `s9d_positive_control.txt` | **0 uses** of 210001–219999, 921001–929999 or init seeds 2101–2105, 2191, 2192 as seed values in 22,404 parsed files of the worktree and `experiments/`. The same scan finds 554 uses of P9-I's seeds, so it detects seeds when they exist. |

---

## 1. Answers to the questions (short form; details in the findings)

**A. Is the positive guaranteed by construction?** Not for the outcome as a whole: F-OQ and T-OQ can fail a step by CEILING, by slow learning (EFFICIENCY), by REVERSED, and on the stand-in the realistic failure is "the grid never loads the memory" (B4), not a guaranteed positive. But several components pass by construction, rule by rule:

| Rule | Degenerate or trivial system that passes it | Status in the draft |
|---|---|---|
| a_use and i (Fano with swap dependence and chance floor) | none found: a zero-knowledge model is floored to 0 (its useful count is below the G2 upper end, `c2` §4); the frozen backbone is at chance; a fact-independent output fails condition (2) | sound |
| Step CAPACITY | R2 (dedicated slot, facts ≤ slots) and H8 (hashing trick: fewer collisions with more slots) pass trivially once loaded | R2 and H8 are excluded from the outcome: correct |
| Dense label BEATS DENSE / not DOMINATED | a control that cannot learn: D-OQ as specified reaches 0.16–0.20 where F-OQ is at 1.00 (`c1`); and T-OQ is exempt from DOMINATED by its architecture | **fails: B2, B3** |
| Parameter label SLOT-SPECIFIC / PARAMETER-DRIVEN | the iso cells are reparameterizations of the same function class, so the label reads only optimization speed | **fails: M1** |
| Active work SUBLINEAR | any tree, any hashed table, and any flat memory read through a conventional ANN index; it is a property of the read path, not a finding | stated as analytic, but used as the hinge of the milestone reading: **M4, M8** |
| Diagonal PROPORTIONAL | any arm at ceiling, whatever the memory does; also a ratio with a zero or near-zero denominator | descriptive, with MEMORY-ATTRIBUTED: acceptable; floors missing: **M9** |
| CAPACITY-NEGATIVE | an unevaluated study (vacuous clause) | **fails: B1** |

What CAPACITY-POSITIVE under oracle addressing would tell the human, after the fixes: given a perfect random per-fact code, a top-8 learned key–value store trained through the answer loss retains more random associations as its slots grow, at a constant number of value rows read, and at least as well as a properly built dense map of equal parameters, input and compute. That is a **necessary condition** of ArborLM's storage claim. It says nothing about addressing, about whether a language model can use the store, or about "useful capability" beyond recall of trained random facts. The [ORACLE-ADDRESSED] annotation is right; the §8.7 reading "S1 supports question 1" overreaches (M8).

**B. Study A.** The prediction can fail, and on the stand-in A1 and A2 are CEILING (§0). The iso-parameter control is unsound (M1) and the gaps the draft admits are not the main problem: no wide-value cell can test "more parameters in fewer slots" in this read path. The dense control is not strong (B3), and the dominance rule is more lenient than ADR-0017's (ADR-0017 required ≥ 1.10 × dense for CAPACITY_POSITIVE; this draft lets a positive stand with dense ahead by any margin for T-OQ, and within 0.5 bits for F-OQ) (B2).

**C. Study B.** Comparing only cells with the same facts is the right way to attribute gains to memory, and MEMORY-ATTRIBUTED is a sound construction. It still needs a registered Study-B line, with floors, or the human's Study B question gets only descriptive labels (M9). Regimes: MU = ME within a row is correct; the ME readout across rows needs a U_P/16 snapshot that the learning grid lacks (m2); MC by rehearsal CPU-seconds is defined and separated from MU, but some MC readouts are unreachable within the fixed run lengths (m3). Plateau: too weak against the step threshold, and blind to non-monotone curves (M2). No cell loads the 16K or 64K memory beyond 2 facts per slot, and on the stand-in load 2 is stored at ceiling: capacity is bounded above nowhere that a positive needs (B4).

**D. Useful information and dependence.** The metric is not passable by a zero-knowledge model, the frozen backbone or a fact-independent path (table above). Value shuffle and address swap are well defined. Under oracle addressing H1/H2 test the shared readout, not the memory; placing them inside DEP mislabels a readout failure as a dependence failure (m7).

**E. Active work.** The formulas are right except for `wo` (m4). SUBLINEAR is architectural. The tree can honestly carry only "fewer keys scored for the same retained bits", and only against the obvious alternative, a flat memory read through a conventional index with the same candidate count, which the draft does not have (M4). The storage-traffic estimate respects the no-SSD rule; the key-bytes line is an identity (m15).

**F. Baselines.** DICT is a correct exact-address reference (and R2 and H8 are exact-address rungs). KNN-W is exhaustive nearest neighbour with linear work: it is a conventional retrieval baseline, not a sparse one. "Conventional sparse retrieval" as the human asked is missing (M4).

**G. Replication.** The probabilities are right (`c2` §3). Five draws × one seed does not separate draw from seed variance, and the draft says it "does not need to"; the human's general standard expects it (M6). The outcome-level bound under the draft's own null is ≤ 3/32, not 1/32 (m5).

**H. Lane L.** Correctly isolated, labelled, and harmless if omitted. Its step verdict is ill-defined, because S0's qualified update counts differ by slot count (m9).

**I. Matrix and budget.** Counts confirmed; projection reproduced within 5%. The cut rule is a hidden adaptive path (calibration → U_P → cuts → a weaker evidence standard), and cut 4 silently makes T-OQ unable to be CAPACITY_SUPPORTED (M5). A smaller matrix answers the question better (§5).

**J. Gates, seeds, precedence, governance.** G2 is right. Seeds 210001+ are free (`s9c`). The precedence problems are B1 and M3. "What S1 cannot establish" is good; add useful capability (M8). Governance: the draft requires human decisions 1 and 2 while the lead intends to self-approve; the record must say which applies, and the caps stay with the human (M11).

---

## 2. Blockers

### B1 — CAPACITY-NEGATIVE fires on an unevaluated study (vacuous clause)

- **Evidence.** §8.7 row 4: "…; or every learned-key arm that is CAPACITY_SUPPORTED is DOMINATED BY DENSE". When no learned-key arm is CAPACITY_SUPPORTED, the set is empty and "every … is DOMINATED" is true. Row 4 then fires whenever F-OQ and T-OQ are NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, CAPACITY_ONE_TRANSITION or INTERMEDIATE, pre-empting row 5 (INCONCLUSIVE). The first clause has the same defect for T-OQ: "T-OQ is neither CAPACITY_SUPPORTED nor CAPACITY_ONE_TRANSITION" is true when T-OQ is NOT_EVALUATED or DEPENDENCE_FAILED.
- **Why it matters.** On the stand-in the arm class is INTERMEDIATE (§0); read literally, the study would print CAPACITY-NEGATIVE. A negative that means "nothing was evaluated" is the worst kind of label for a study that "will determine if the hypothesis stands".
- **Replacement for §8.7 row 4:**
  > | 4 | **CAPACITY-NEGATIVE** | (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED (§8.4, as amended by M3); or (b) at least one of F-OQ, T-OQ [and F-OQ-IVF, M4] is CAPACITY_SUPPORTED, and every arm among them that is CAPACITY_SUPPORTED is DENSE AHEAD (§8.5). An empty set never satisfies (b). |
- Add to the implementation tests: "the analysis is exercised on synthetic records in which no arm is CAPACITY_SUPPORTED and every arm is in turn NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, CAPACITY_ONE_TRANSITION and INTERMEDIATE; each must give CAPACITY-INCONCLUSIVE with the right reason."

### B2 — The dense gate cannot block a positive

- **Evidence.** §8.5 and §8.7 row 3.
  - DOMINATED BY DENSE = DENSE AHEAD **and not SUBLINEAR**. T-OQ, H8 and R2 are SUBLINEAR by their read path (§7.4 rule 2), so T-OQ can never be dominated: CAPACITY-POSITIVE stands for T-OQ even if the dense map at equal parameters, input and compute retains several bits per fact more.
  - For F-OQ, DENSE AHEAD needs d ≤ −0.5 bits in at least 4 replicates **under both MU and MC** at every larger cell. Anything between −0.5 and +0.5 is MATCHES DENSE, which does not block. At a_use near 0.9, 0.5 bits is 5.7 points of accuracy (`c2` §1).
  - The dense arm is read only at U_P or at its MC snapshot. P9-I's dense control was "still improving at U" (`docs/reviews/p9i-results-2026-11-15/REVIEW.md` §4), and the stand-in's D-OQ is still rising at 16,384 updates.
  - ADR-0017 §8.2 required I ≥ 1.10 × dense for CAPACITY_POSITIVE. This draft is strictly more lenient, and its own definition of the outcome ("not dominated by a dense map with the same parameters, input and compute", §8.7) would be false for a T-OQ positive with the dense control ahead.
- **Replacement for the dense paragraph of §8.5:**
  > **Dense, at the larger cell of each CAPACITY STEP of the arm,** with d = i(arm) − i(D-OQ), per panel and replicate, in three readings: **MU** (both at U_P); **MC** (the cheaper of the two at its matched-cost snapshot); **D-BEST** (the arm at U_P against D-OQ at the best of its snapshots up to its U_run). **BEATS DENSE** if d ≥ +0.5 in all 5 replicates, in all three readings, at every such cell. **DENSE AHEAD** if d ≤ −[0.25] in at least 4 replicates in any one reading at any such cell. **MATCHES DENSE** otherwise. Counted work never offsets a dense lead; it is reported in the active-work label only. DOMINATED BY DENSE is withdrawn.
- **Replacement for §8.7 row 3:**
  > | 3 | **CAPACITY-POSITIVE** | F-OQ or T-OQ [or F-OQ-IVF, M4] is CAPACITY_SUPPORTED and is not DENSE AHEAD. The dense label (BEATS DENSE or MATCHES DENSE) is printed in the label. |
- Open question 1 of §16 is then answered: the memory must at least match a strong dense control in every reading. Whether to require BEATS DENSE, as ADR-0017 did, is **[the lead's choice]**; the review does not require it, because the human's definition of CAPACITY-POSITIVE is about scaling, not superiority. MATCHES DENSE then reads, verbatim: "a dense map with the same parameters, input and compute retained as much; the memory did it with [W_arm / W_dense] of the counted work".

### B3 — D-OQ, as specified, is not a strong dense alternative

- **Evidence.**
  - Construction: D-OQ takes a unit-norm 16-dimensional code into a bias-free `w1` with N(0, 0.02) entries (`studies/p9i/model.py` `IDense`; P9's `_matrix`). Pre-activations then have a standard deviation of about 0.02, where GELU is nearly linear: at initialization D-OQ is close to a linear map of a 16-d code, which cannot memorize random labels. P9's adapters read the backbone's hidden state, whose norm is much larger, so this weakness is specific to the oracle-code input. Without biases every hyperplane passes through the origin.
  - Stand-in (`c1`, `c1b`), equal parameters, 16,384 updates: D-OQ as drafted 0.161 at 8K/4K, 0.202 at 8K/16K, 0.041 at 32K/16K, against F-OQ 1.000, 1.000, 0.986. **The same D-OQ at lr 0.01 reaches 0.626 at 8K/16K; a conventionally initialized dense with biases reaches 0.979 at 8K/4K.** Built conventionally, the dense map matches F-OQ at 8K/16K by 16,384 updates (1.000) but not at 32K/16K (0.180 against 0.986): with a proper control the dense comparison carries information; with the drafted one it does not, because the drafted one hardly learns anywhere (0.04–0.26 at every cell except 2K/4K, where it reaches 1.000 only at 16,384 updates).
  - The draft's calibration tunes D-OQ over {0.003, 0.001}, which goes in the wrong direction on this evidence, at one cell (8K/16K), and calls that "favouring the control" (§10.1 item 3).
- **Why it matters.** With this control BEATS DENSE is close to guaranteed, and it would be printed with the outcome. The human asked for "strong dense alternatives"; a false "beats dense" is a false positive.
- **Replacement for §5.3 item 1 and §10.1 item 3:**
  > **D-OQ, the parameter-matched dense control**, in every cell where a dense label is read: the oracle code (the same tensor as F-OQ's) → `w1 [h, 16]` with bias `b1 [h]` → exact GELU → `w2 [32, h]` → sigmoid(gate) (init −2), added at the answer site. Initialization is the conventional one for a fan-in layer: `w1`, `b1` ~ U(−1/4, 1/4), `w2` ~ U(−1/√h, 1/√h), from seeded generators. h is set so that 49h + 1 equals F-OQ's parameter count within 0.1%. Same loss, optimizer, clip and updates.
  > **Dense learning rate (calibration):** D-OQ at 8K/16K and at 32K/64K, at learning rates [{0.001, 0.003, 0.01}], on both calibration draws, to the longest run length of §5.4. The rate with the higher minimum Panel A accuracy at U_P is chosen separately for 16,384 and 65,536 slots (the 16,384 choice is also used at 4,096); a difference below 0.02 goes to the faster of the two. [6 + 6 = 12 runs.] The memory arms keep 0.003 untuned.
- Also: the rehearsal must time the new D-OQ (its cost is no longer "P9-I's dense cost").

### B4 — The registered grid is unlikely to load the memory, so the outcome is likely INCONCLUSIVE by construction, and calibration as drafted cannot see it

- **Evidence.**
  - A CAPACITY STEP needs the smaller memory to plateau below the larger one by ≥ 0.5 bits. In the 16K→64K transition the smaller cells are 8K/16K (load 0.5) and 32K/16K (load 2). No registered cell loads 16,384 or 65,536 slots above 2 facts per slot (§5.1: "No cell overloads the 65,536-slot memory").
  - On the stand-in, load 2 is stored at ceiling: F-OQ 8K/4K 1.000 at 8,192 updates; F-OQ 32K/16K 0.986 at 16,384; H8 1.000 at load 2 in both rows. Load 8 is stored at 0.962 at 1,024 slots (8K facts) and is still rising at 4,096 slots (32K facts, 0.799 at 16,384; 32 exposures per fact at U_P). Run to 65,536 updates, the stand-in stores load 4 at 0.997 (4,096 slots) and 0.988 (16,384 slots), and load 8 at 0.960 (4,096 slots, still rising); only load 16 at 4,096 slots and load 8 at 16,384 slots stay clearly below ceiling, and both are still rising by 0.46 and 0.87 bits per doubling. On the stand-in a slot holds at least 4–8 facts; what limits the loaded cells within any affordable run is updates and exposures per fact, which is exactly the budget effect that S1's classes are built to exclude.
  - The draft's step verdicts on these stand-in numbers give A1 CEILING, A2 CEILING, B1 EFFICIENCY, B2 CEILING: no CAPACITY STEP anywhere, and the outcome is CAPACITY-INCONCLUSIVE (or, with B1 unfixed, CAPACITY-NEGATIVE).
  - The stand-in over-states per-slot capacity (§0), so load 2 may be overloaded in the real system. That is exactly the point: whether any registered step is loaded is **unmeasured**, and §10.1 item 4 forbids running any off-diagonal cell in calibration. This is the same structure as ADR-0017 review B3 (task validity unmeasured, and the plan forbade measuring it before the single run).
  - Separately, the run-length cap of 4·U_P means a loaded small cell (load 8 at 4K slots) is unlikely to plateau, so its step is EFFICIENCY, not CAPACITY. Cells at 4,096 slots cost about 0.0095 s per update (`c4`); running them longer is cheap.
- **Required change (add §10.1 item 0, "load calibration", before the U_P rule):**
  > **0. Load calibration.** On the two calibration draws, one initialization seed, F-OQ only, at 4,096 slots with [8,192 / 16,384 / 32,768 / 65,536] facts (loads 2, 4, 8, 16), and at 16,384 slots with [32,768 / 65,536 / 131,072] facts (loads 2, 4, 8), run to [65,536] updates with snapshots on the doubling grid. **L\*** is the smallest load at which, on both draws and both calibration panels, the cell has plateaued (gain ≤ [0.1] bits per fact over its last doubling) at a_use ≤ [0.80]. Cost about [3] CPU-hours at the contended per-update costs of `c4` (14 runs; the longest about 16 minutes).
  > **Rule fixed now.** If L\* ≤ 2 at both slot counts, the grid of §5.1 stands. If 2 < L\* ≤ [8], the row that tests the 16K→64K transition becomes F = L\*·16,384 facts (cells at 16,384 and 65,536 slots only, for F-OQ, T-OQ, H8, D-OQ), with its own U_P chosen by the rule of item 1 on that row's larger cell, and the 32,768-fact row keeps only its 4K→16K step. If L\* > [8] or no load qualifies, the 16K→64K transition cannot be loaded within the cap: the work stops and returns to the human lead with the cost of the smallest loaded row, before the freeze. Calibration accuracies are never results.
  > **Run lengths.** Cells at 4,096 slots run [6]·U_P; at 16,384, [4]·U_P; at 65,536, 2·U_P. A smaller cell that has not plateaued by its run length gives EFFICIENCY or UNRESOLVED, never CAPACITY, as now.
- Every class compares cells of one row, so a row-specific U_P breaks no rule. The cross-row diagonal labels become descriptive only (they already are). This is **PENDING LEAD REVIEW** for the numbers in brackets; the requirement that loading be measured before the freeze, and that a fixed rule map the measurement to the grid, is not optional.

---

## 3. Major findings

### M1 — The iso-parameter cells are reparameterizations; the parameter label cannot mean what it says

- **Math.** The memory adds g · W_o Σ_s w_s v_s with v_s ∈ R^{d_v} and W_o ∈ R^{32×d_v}. Write u_s = W_o v_s ∈ R^{32}. The read is g Σ_s w_s u_s, so the memory's function depends on (keys, U) with U ∈ R^{N×32}. For d_v ≥ 32 and W_o of full row rank, (V, W_o) reaches every U, exactly as d_v = 32 does (take W_o = I). F-OQ-wide at 4,096 slots × 175 therefore has **the same function class as F-OQ at 4,096 slots × 32**; its 590,304 extra parameters are redundant. Likewise H8 at width 127. H8 at width 8 is a different defect: its u_s lie in an 8-dimensional subspace, a rank-restricted model, not "the same parameters in more slots".
- **Stand-in.** Wide cells learn faster early (0.833 against 0.141 at 1,024 updates) and end at the same place (§0). At ceiling the label prints PARAMETER-DRIVEN (d = 0); under load it would print SLOT-SPECIFIC whenever the standard step is a capacity step. Neither is about parameters.
- **Consequence.** H21-4's second clause ("a memory with the same parameters in fewer, wider slots does not reproduce the gain") is not testable this way. Under this read path a slot has a fixed 48 expressive parameters (16 key, 32 effective value) and "more slots" and "more expressive parameters in the store" cannot be separated inside the memory. The parameter control is D-OQ (B3), which is valid.
- **Replacement for §5.3 item 2 and the parameter label of §8.5:**
  > **No iso-parameter memory cell is run.** In this read path a slot's contribution is W_o v_s ∈ R^{32}, so value widths above 32 add only redundant parameters and widths below 32 restrict the rank; neither is "the same parameters in fewer slots". A slot has 48 expressive parameters, and "more slots" cannot be separated from "more store parameters" inside the memory. Total trainable parameters are controlled by D-OQ at equal parameter count (§5.3 item 1). H21-4 is restated: "A dense map with the same parameter count, input and compute does not retain more than the memory (DENSE AHEAD, §8.5)."
- Saves 3 configurations (15 cells, about 0.12 CPU-hours per replicate).

### M2 — The plateau rule is too weak for a 0.5-bit step and blind to non-monotone curves

- **Evidence.** §8.2: "plateaued if i(U_run) − i(U_run/2) ≤ 0.25". A smaller memory still gaining 0.25 bits per doubling closes a 0.5-bit gap in two more doublings, so a step can be CAPACITY when the smaller memory was only slower. ADR-0017 review M8(g) and RECHECK made the same point about a 9% plateau. The stand-in's curves are not monotone under a constant learning rate (F-OQ 32K/64K: 0.989 → 0.933 → 0.969 at 4,096 / 8,192 / 16,384 updates): a dip between the last two snapshots makes "plateaued" true with a negative difference, and reading the smaller cell at a dip inflates Δ_SAT.
- **Replacement for the plateau sentence and the SAT definition of §8.2:**
  > Let i\*(c; U) be the maximum of i over the cell's snapshots at or below U. **Δ_SAT = i(4N; U_P) − i\*(N; U_run).** The smaller cell has **plateaued** if i\*(N; U_run) − i\*(N; U_run/2) ≤ [0.10] bits per fact. CAPACITY additionally requires Δ_SAT − 2·[i\*(N; U_run) − i\*(N; U_run/2)] ≥ 0.5, so the gap survives two further doublings at the smaller cell's last rate. The larger cell is "plateaued" by the same rule on its own snapshots.

### M3 — Negative verdicts are read under the budget; NO GAIN can come from an unloaded or slower memory

- **Evidence.** §8.2 row 6: REVERSED if Δ_MU ≤ −0.5, read at U_P only, with no condition on the larger cell. The larger memory learns more slowly (fact 5 of §1; the stand-in's 32K/64K is behind 32K/16K at 8,192 updates). REVERSED feeds NO GAIN (§8.3 row 8), blocks CAPACITY_SUPPORTED ("no step REVERSED") and counts towards CAPACITY_NOT_SUPPORTED. §9's claim "undertrained cells give UNRESOLVED or EFFICIENCY, never NO GAIN" is therefore false for REVERSED. NULL uses Δ_MU only; and a NULL whose smaller cell has 0.5–0.75 bits of room (i between 4.25 and 4.5) is counted as a capacity negative although the smaller memory was barely loaded.
- **Replacement for §8.2 rows 6–7 and §8.4 row 6:**
  > | 6 | REVERSED | Δ_MU ≤ −0.5 **and** i\*(4N; U_run(4N)) − i\*(N; U_run(N)) ≤ −0.5 (the larger memory is worse even with its full run) |
  > | 6a | SLOWER | Δ_MU ≤ −0.5, not row 6 (reported as learning efficiency; enters no negative) |
  > | 7 | NULL | \|Δ_MU\| < 0.25 and \|i\*(4N; U_run(4N)) − i\*(N; U_run(N))\| < 0.25; both cells plateaued (M2); and the smaller cell is **loaded**: i\*(N; U_run) ≤ [4.0] bits (a_use ≤ about 0.90) |
  > §8.4 row 6: **CAPACITY_NOT_SUPPORTED** — at least one step per transition is NO GAIN or REVERSED, and no step is CAPACITY STEP. A transition whose steps are all CEILING or NULL-with-an-unloaded-smaller-cell prints NOT LOADED and makes the arm NOT_TESTED_BY_LOAD.
  > §9, row "Classes passed or failed by budget": "… a negative needs both cells plateaued, a loaded smaller cell, and the difference at the full run lengths; a slower larger memory gives SLOWER, never NO GAIN."

### M4 — "Conventional sparse retrieval" is missing, and the sublinearity claim is reserved to the tree although a flat memory with a standard index gives the same counted work

- **Evidence.** KNN-W (§5.5) is exhaustive exact nearest neighbour, 224·F multiply-adds per query: linear, not sparse. The human asked for conventional sparse retrieval. The milestone reading (§8.7) makes T-OQ the only arm that can "support question 1", because only it is SUBLINEAR. But T-OQ's sublinearity is the read path (score N/256 router entries and 512 keys), and the same counted work is obtained by reading the trained F-OQ keys through a standard inverted-file index. P7-A, P7-B and P8 found no hierarchy-specific benefit in locality (`docs/RESEARCH_LOG.md`, §1 fact 9 of the draft); S1 should not hand the hierarchy the sublinearity claim without the obvious control.
- **Required addition (evaluation only, no training, about one minute per 65,536-slot cell):**
  > **F-OQ-IVF (conventional sparse retrieval over the learned store).** At every evaluated snapshot of F-OQ, the unit-normalized trained keys are clustered by k-means into N/256 centroids ([10] Lloyd iterations, seeded k-means++ initialization, seed base + 60). A query scores the centroids, visits lists in order of score until at least 512 candidate keys are collected, takes the top 8 of those by cosine, and reads values exactly as F-OQ does. Counted work K = N/256 + (candidates scored), recorded per query. Reported: a_use and i on every panel, recall of the exhaustive top-8, and W. F-OQ-IVF takes F-OQ's place in every step rule as a separate arm (its steps use F-OQ's cells read through the index).
  > **KNN-W** is renamed "exhaustive nearest neighbour over the model's states (no oracle)"; its storage of 224 values per fact is printed beside it. **KNN-W-IVF**, the same with the index above, is added. The conventional-retrieval label is evaluated for both.
  > **Hierarchy label** (§8.5): T-OQ against F-OQ-IVF at equal candidate count, on I_use at the larger cells, thresholds as now. TREE_AHEAD is reported only if T-OQ ≥ 1.03 × F-OQ-IVF.
  > **Milestone reading** (§8.7): "S1 supports the storage part of question 1 under oracle addressing only if the outcome is CAPACITY-POSITIVE for an arm whose counted work is SUBLINEAR (T-OQ or F-OQ-IVF)."

### M5 — The cut rule is an adaptive path, weakens the positive standard, and cut 4 removes T-OQ's only route to CAPACITY_SUPPORTED

- **Evidence.** §10.3. The cuts are fixed now and applied on rehearsal timing, which is fine in itself. But (a) whether cuts are needed depends on U_P, and U_P is chosen in calibration from accuracies (§10.1 item 1); at U_P = 16,384 the projection needs cuts (`c4`: 1–3 on my recount, 1–4 in the draft); (b) cut 3 changes "all 5" (p ≤ 0.031) to "all 4" (p ≤ 0.0625) and "at least 4 of 5" (0.19) to "at least 3 of 4" (**0.31**), so a calibration outcome silently weakens the evidence standard of the positive and of every negative; (c) cut 4 removes 32K/4K, so step B1 is NOT RUN. T-OQ's class is defined on B1 and B2 only (§8.4), so T-OQ can then **never** have a CAPACITY STEP in the 4K→16K transition and can never be CAPACITY_SUPPORTED. The arm on which the milestone reading rests becomes structurally negative-or-inconclusive. The same pattern was flagged in ADR-0017 RECHECK N8 ("each reduction silently changes a rule").
- **Replacement for §10.1 item 1 (U_P) and the cut rule of §10.3:**
  > U_P = 8,192 [lead's choice of value]. If, on the calibration draws, R2 < 0.95 or F-OQ < 0.90 at any diagonal cell at U_P (row-specific U_P after B4 excepted), the work stops and returns to the human lead; no larger U_P is substituted by rule.
  > **The replicate count is never cut.** Cuts, in this order, until the headroom rule holds: (1) lane L; (2) D7; (3) D-OQ at the cells where no dense label is read; (4) T-OQ at 2K/4K. If it still does not hold, stop and return to the human lead. Each cut lists the rules it changes in the freeze record; a cut that would make an arm unable to reach a class it is registered for is not allowed.
  > T-OQ is run on all seven cells of §5.1 (adds 8K/4K and 8K/64K), so its arm class is defined on A1, A2, B1 and B2 like F-OQ's.

### M6 — Draw and seed variance are not separated

- **Evidence.** §6.2: "Draw and initialization vary together. The study does not separate them and does not need to." The human's general standard (as relayed) expects them to be separated. ADR-0019 does it (8 draws × 2 seeds) and its review found outcomes clustered by draw. S1's "all 5" is then a statement about draw-plus-seed replicates; if seed variance is large, a single unlucky initialization can veto a real effect, and if it is negligible, five draws are the right unit. Nobody will know which.
- **Required addition to §6.2 (descriptive, no rule):**
  > **Seed block.** On draw 1, F-OQ and [D-OQ] are also trained at initialization seeds [2111 and 2121] on every cell where they are registered ([14 or 24] extra cells, about [1.3–3] CPU-hours). The report gives, per cell and readout, the spread of i over the three seeds of draw 1 against the spread over the five draws, and states which dominates. These cells enter no rule. "Does not need to" is deleted.

### M7 — The U_P rule is gated by H8, an arm that cannot give the outcome

- **Evidence.** §10.1 item 1 requires H8 ≥ 0.90 at every diagonal cell for U_P to qualify; item 2 makes the row of 32,768 facts REFERENCE_FAIL if 32K/64K qualifies at neither value. H8's learning speed (fixed 1/8 weights, slots shared by 4 facts at 32K/64K) can therefore double U_P or remove the row that carries B1, B2 and Study B, for a reason unrelated to the store under test or to the readout.
- **Replacement:** "U_P qualifies at a diagonal cell if R2 ≥ 0.95 and F-OQ ≥ 0.90 on both calibration draws and both panels. H8's calibration accuracies are reported; if H8 is below 0.90 at a cell at U_P, its classes there carry UNDERTRAINED-AT-U_P."

### M8 — The milestone reading and the label overreach

- **Evidence.** §8.7: "S1 supports question 1 under oracle addressing only if …". Question 1 asks about "retained knowledge **and useful capability**". S1 measures recall of trained random facts by a store given the identity of the fact. It cannot show useful capability, and the human's "p10 will determine if the hypothesis stands" makes an over-broad sentence costly.
- **Replacement for the reading paragraph of §8.7 and the printed label:**
  > **Printed label:** CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; arm(s); dense label; active-work label; hierarchy label; conventional-retrieval label; learned-address lane status].
  > **Reading for milestone question 1, fixed now.** S1 tests the storage half of question 1 under oracle addressing. CAPACITY-POSITIVE for an arm with SUBLINEAR counted work means: given the identity of the fact, this store retained more trained random facts as it grew, at bounded counted work, and at least as well as a dense map of equal size, input and compute. It is a necessary condition of the ArborLM hypothesis, not support for it as a whole: it says nothing about addressing by the model, about the use of the store by a language model, or about useful capability beyond recall of the trained facts. CAPACITY-NEGATIVE means the storage half fails for this store, backbone, task and budget.
- Add to §12: "Useful capability beyond recall of the trained facts; any improvement of a language model's behaviour."

### M9 — Study B has no registered result line, and its ratios have no floors

- **Evidence.** The human's Study B asks for "more independent useful facts as memory grows; retention with good retrieval accuracy and sublinear active memory work". The draft answers it only through descriptive labels (§8.6) and the a_use ≥ 0.80 condition of CAPACITY_SUPPORTED. The diagonal ratios divide by i of the smaller cell, which may be 0 (a ratio of +∞ or 0/0) or near chance. And the two thresholds are inconsistent: a_use 0.80 at 32K/64K with 8K/16K at ceiling gives a ratio of 2.63, below PROPORTIONAL's 3.0 (`c2` §2).
- **Replacement (add to §8.6, printed beside the outcome, entering no class):**
  > **STUDY B (knowledge with memory), per eligible arm:** **KNOWLEDGE SCALES WITH MEMORY** if, in all 5 replicates and on both panels, under MU and under MC separately: a_use ≥ [0.85] at every diagonal cell; I_use grows ≥ 3.0 times at both diagonal steps; both diagonal steps are MEMORY-ATTRIBUTED; and the arm's counted work is SUBLINEAR. **KNOWLEDGE DOES NOT SCALE** if a_use < [0.5] at the largest diagonal cell in at least 4 replicates. **NOT ESTABLISHED** otherwise. A ratio is computed only when both cells have a_use ≥ [0.5]; otherwise it is NOT ASSESSED. The ME line is printed with the sentence of §5.4 rule 3.

### M10 — Exposure confound in the larger memory is not addressed by SAT

- **Evidence.** §8.6 "Optimizer note" says SAT controls the AdamW effect. ADR-0017 §5.5 and its review (C4) showed that a row with a gradient once in K updates moves about √K learning rates per exposure under AdamW, about 90% of it on updates without gradient, and the effect favours larger memories. SAT gives the smaller memory more updates; it does not remove the larger memory's per-row step inflation, which affects Δ_MU and the dense comparison. It is a minor risk for storage at plateau, a real one for EFFICIENCY and SLOWER.
- **Replacement:** keep SAT, and add "Per cell, the cumulative movement of value rows on updates with and without their own gradient is reported (§7.3), and every EFFICIENCY or SLOWER verdict is printed with the ratio of that movement between the two cells. No class depends on it." (No row-lazy arm; open question 6 answered: SAT is enough for CAPACITY, not for EFFICIENCY.)

### M11 — Governance: who approves, and the budget

- **Evidence.** §11 and §13 require **human** decisions 1 and 2 and reserve the caps for the human. My task says the lead may self-approve P10 studies after a clean Opus review. If the lead self-approves while the ADR text says "human decision", the approval record contradicts the specification. `AGENTS.md` says the human research lead approves budget decisions; the 12-hour cap is three times any earlier cap.
- **Replacement for §11 items 2 and 8 and §15:**
  > Decision 1 (and decision 2) is taken by [the human lead | the lead under the human lead's delegation of DATE, quoted verbatim in §15]. If by delegation, §15 records the delegation verbatim, its scope, and this review's verdict. **The caps of §10.3 are a budget decision and remain the human lead's** unless the delegation names them.

---

## 4. Minor findings (each with its change)

- **m1.** §8.2 CEILING: "i ≥ 4.5 (a_use about 0.95)". i(0.95) = 4.466; 4.5 is reached at 0.9537. Write "a_use about 0.954".
- **m2.** ME across rows needs a U_P/16 snapshot for the 2,048-fact cells, and §8.6's learning grid is {1/8, 1/4, 1/2, 1}·U_P. Add 1/16. §10.1 item 3 reads the dense choice "at 8,192 updates" even if U_P is 16,384; read at U_P.
- **m3.** 65,536-slot cells run 2·U_P, but some MC readouts need g > 2 there (H8 at 0.012 s/update against D-OQ at about 0.049: g ≈ 4). Add: "If the cheaper cell's required snapshot exceeds its run length, the comparison is MC-SHORT."
- **m4.** §7.4: add `wo` (32 × d_v MACs) to W for every memory arm, and the top-k selection's comparisons as a separate count. D-OQ's W is 48h (+ h with biases, B3).
- **m5.** §6.2 states 1/32 as if it applied to the outcome. Under the draft's own null, F-OQ can reach CAPACITY_SUPPORTED through A1 or B1 and T-OQ through B1, so the outcome-level bound is ≤ 3/32 ≈ 0.094 by the union bound (with M4, ≤ 4/32 if F-OQ-IVF is an arm). State it; and state that replicates protect against noise, not against systematic confounds.
- **m6.** Seeds. G9 should name the sibling ranges explicitly: S0 190001–191599, the 200001+ block the lead reserves (owner not stated in the draft), and S2 220001–229999 (ADR-0022 §9). Bound the test ranges: ADR-0019 uses "910001 upward", which contains S1's "921001 upward"; write S1 tests as 921001–929999 and ask S0 to bound its own. Check the derived generator seeds (init + 1000·k, as `_matrix` uses) as well as the declared ones. `s9c`: no current use of S1's ranges.
- **m7.** H1/H2 inside DEP. Under oracle addressing they test the shared frozen readout. A failure there is not a dependence failure. Rename the H1/H2 condition "HELD-OUT FRAGILE", judge it against R2 at the same cell (fragile only if the arm's H/A ratio is below [0.90 × R2's]), and keep it out of DEPENDENCE_FAILED.
- **m8.** DEP's "a_use ≥ 0.95 × raw accuracy" and "value shuffle gives chance" are read at U_P only; say so, and read them at every snapshot used by a rule.
- **m9.** Lane L. S0's qualified update counts differ by slot count (U at 4,096; 4U at 16,384 in ADR-0019 rev 4), so Δ_MU between F-LA cells is not matched, and §8.2 needs U_run and SAT snapshots S0 does not define. Either run all F-LA cells to the larger count with S1's snapshot grid, or make lane L descriptive: the ratio of F-LA to F-OQ retained bits per cell, no step verdict.
- **m10.** The timing stage is refused if the load average exceeds 1.0, but S0 and S2 may be training. Add: "retried until quiet up to [3] times within the cap; if never quiet, THROUGHPUT NOT MEASURED; this does not make S1 INCOMPLETE."
- **m11.** MC by measured CPU-seconds depends on implementation efficiency (gathers, chunking). Require MC to hold under both CPU-seconds and analytic multiply-adds (use the larger multiplier).
- **m12.** §10.3 "At U_P = 16,384 the projection needs cuts 1 to 4": on my recount cuts 1–3 suffice (2 × 4.85 h = 9.70 h ≤ 11.25 h). Both are projections from contended 64-update runs; the rehearsal decides. Moot if M5 is adopted.
- **m13.** H8's iso tolerance of 0.25% (moot if M1 is adopted).
- **m14.** Pairing: "the same initialization of the shared parameters where their shapes agree" — `_matrix(seed + k, n, kw)` draws differ with n, so key and value tables never agree across slot counts. Say only `wo` and the gate are shared.
- **m15.** §7.5: say that the estimate assumes keys in RAM and values on storage; the key-bytes line is an identity.
- **m16.** The MC-MISMATCH flag compares contended registered CPU-seconds with isolated rehearsal timing; a 64K cell slows more under contention. Report the ratio, as now; no change to classes.
- **m17.** §1 fact 5's "the oracle-query rung needs more updates as the memory grows" is from rows where facts grew with slots; the draft says so. Keep the caveat in §9's table too.

---

## 5. Recommended matrix (per replicate; [lead's choices])

| Arm | Cells | Configurations | Why |
|---|---|---|---|
| F-OQ | all 7 of §5.1 (or the B4 rows) | 7 | primary |
| T-OQ | all 7 | 7 | hierarchy, symmetric with F-OQ (M5) |
| H8 | all 7 | 7 | exact address with sharing, key-learning attribution (cheap) |
| D-OQ (conventional init, B3) | 8K/16K, 8K/64K, 32K/16K, 32K/64K, 2K/4K | 5 | dense label at every larger cell; 2K/4K for the diagonal |
| R2 | 2K/4K, 8K/16K, 8K/64K, 32K/64K | 4 | REF |
| F-OQ-IVF, KNN-W, KNN-W-IVF, DICT, no-memory, unseen | evaluation only | 0 | M4 |
| Iso-parameter, D7 | dropped | 0 | M1; D7 enters no rule (optional at [1] replicate, descriptive) |
| **Per replicate** | | **30** | |
| **Five replicates** | | **150** | |
| Seed block (M6) | draw 1, F-OQ, two extra seeds | +14 | descriptive |
| Load calibration (B4) | calibration draws | +14 runs | before the freeze |
| Calibration (U_P + dense lr, B3) | | 12 + 12 runs | |
| Lane L | optional | +15 | |

Projection (`outputs/c4b_matrix_budget_final.txt`, P9-I contended per-update costs, U_P = 8,192):

- With the draft's run lengths: 15.0 CPU-hours for 150 cells plus 1.3 for the seed block, 2.7 hours with six workers, 3.8 hours remaining after calibration and rehearsal. Twofold headroom needs 7.6 hours, so a cap of [9] hours would do.
- With B4's run lengths (4K cells 6·U_P, 16K cells 4·U_P) and the load calibration (2.9 CPU-hours): 3.9 hours of training with six workers, 5.1 hours remaining, and the whole study needs a cap of at least **11.5 charged hours** for twofold headroom. **The drafted 12 hours is then about right, with no slack.** With 8·U_P at 4K it needs about 12.5 hours and does not fit.
- A B4 overload row, if the rule calls for one, does not fit in 12 hours on these costs and goes to the human lead.

## 6. PENDING LEAD REVIEW (scientific choices I do not make)

- The B4 load rule's numbers, and whether an overload row for the 16K→64K transition is worth its cost, or whether S1 accepts testing that transition only if load 2 turns out to be loaded.
- Whether CAPACITY-POSITIVE requires BEATS DENSE (ADR-0017's standard) or not-DENSE-AHEAD (B2).
- The dense learning-rate grid and initialization (B3).
- Seed-block size (M6), the plateau number (M2), the loaded-cell threshold (M3), the Study-B accuracy floor (M9).
- Whether T-OQ runs all seven cells (M5) and whether D7 is kept.
- **The framing of S1 itself.** On the stand-in, at every load the registered slot counts can afford, what separates a small memory from a large one is how many updates it needs, not how much it can hold. If the load calibration of B4 confirms this on the real readout, S1 at these sizes is a study of learning efficiency under load, which the human also asked for ("learning efficiency"), and its EFFICIENCY verdicts carry most of the information. Whether EFFICIENCY STEP should then become a registered result line beside CAPACITY STEP (it is now only a step class), with its own regime rules (MU and MC only, never "capacity"), is the lead's call; it must be made before calibration.

## 7. What S1 can and cannot establish after the fixes

- **Can:** whether, given the identity of the fact, a learned top-8 store retains more trained random facts as slots grow from 4,096 to 65,536 under matched updates, matched compute and saturation, against a strong dense map of equal parameters and against conventional exact and sparse retrieval, with counted work per query; where the store's load limit lies on this readout; whether a learned tree does better than a flat store read through a standard index.
- **Cannot:** autonomous learned memory; addressing by a language model; useful capability; anything about natural language; storage I/O, latency or SSD behaviour; behaviour beyond the registered run lengths; any claim of Astra validation or human approval.

## 8. Files (this folder)

- `c1_store_toy.py` with `c1_jobs.json`, `c1b_jobs.json`, `c1c_jobs.json`, `c1_smoke.json`; outputs `outputs/c1_smoke.txt`, `outputs/c1_store_toy.txt`, `outputs/c1b_dense_variants.txt`, `outputs/c1c_load_sweep.txt`.
- `c2_arithmetic.py` → `outputs/c2_arithmetic.txt` (and the failed first attempt).
- `c4_matrix_budget.py` → `outputs/c4_matrix_budget.txt`, and `c4b_matrix_budget_final.py` → `outputs/c4b_matrix_budget_final.txt` (the final recommended matrix and run lengths; both read `results/p9i-rehearsal-2026-11-14/rehearsal_cells.csv`). The first file's "recommended matrix" block is an earlier version of my recommendation (T-OQ on six cells), superseded by c4b.
- `s9_seed_scan.py` (attempts 1–2, kept), `s9c_seed_keys.py` → `outputs/s9c_seed_keys.txt`, `s9d_positive_control.py` → `outputs/s9d_positive_control.txt`.
