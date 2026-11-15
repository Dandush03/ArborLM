# ADR-0017 revision 2 — auditor re-check

- Reviewer: Claude Opus 5.5 (session model `claude-opus-5-5`), auditor role, launched by the Claude lead. This is independent engineering and mathematical evidence. It is **not** Astra review and **not** human approval. Astra review: NOT_PERFORMED.
- Re-checked (branch `claude/adr-0017-design`, HEAD `e46d5f8`, read in full): `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` (revision 2), `EXECUTION_PLAN.md`, `RESOURCE_BUDGET.md`, against my `REVIEW.md` (revision 1) and the human draft `ADR-0017-draft-rev0-human.md`. Code read only to confirm the backbone window (`src/arborlm/pilot_model.py:15`, `CONTEXT = 64`, so 64-byte contexts fit).
- I wrote none of the design. I wrote `REVIEW.md` and the `c*` checks; the new `r*` checks below are mine too. Where revision 2 relies on something I wrote that was wrong or unsupported, I say so (finding N16).
- Nothing was implemented, trained or evaluated. No ArborLM model was run. New checks are pure math or toys, in `opus_checks/r1`–`r5`, with outputs beside them.
- Environment: Apple M5 Max (18 cores), macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0 (CPU), no numpy. Load average about 2 (not a timing measurement). Every command was run from the repository root: `uv run --locked python -W ignore docs/reviews/adr-0017-design-2026-11-14/opus_checks/<script>.py | tee docs/reviews/adr-0017-design-2026-11-14/opus_checks/<script>.out.txt`. `uv run --locked ruff check .` passes.
- Failed attempt (kept): the first run of `r3_objective_gradients.py` raised `RuntimeError: Trying to backward through the graph a second time`, because my first `autograd.grad` call freed the graph. I added `retain_graph=True` to that call and re-ran. The recorded output is from the second run. No other script failed, and no number had to be retracted.

## Verdict: **NOT READY** for Human Decision 1

Revision 2 fixes most of revision 1 properly: the Fano metric, the absolute coefficients, the calibration step, answer-site loss, primary panels, the checksum code, R0a, minimal support, the global usage floor, the precedence orders, the general-N simulator and the Lane D floor. Three problems remain where a registered label would not mean what it says:

- **RB1 (§8.2).** "Step supported" and CAPACITY_PARTIAL can be awarded to a memory at about 4% accuracy, against a chance level of 3.1%. The accuracy condition I proposed in B1 was too weak; that is my error.
- **RB2 (§7).** The global usage term does not say how its gradient passes through the moving average. Read literally, the gradient is scaled by 1/16, 1/64 or 1/256 at the three sizes, so the doses would not be what §7 says.
- **RB3 (§3 and §8.4).** Lane C's gate requires the locality cell itself to be utilization-preserving. A P8-style collapse would therefore be reported as "H17-LOC NOT EVALUATED" instead of COLLAPSED, and the §8.4 COLLAPSED row can never fire.

Every fix is a wording or number change, listed ready to paste in §3. None needs a redesign. A revision 3 that applies them can be re-checked against this list alone.

## 1. Status of the revision-1 findings

| ID | Status | One line; for anything not fully resolved, the change needed (paste-ready text in §3) |
|---|---|---|
| B1 | PARTLY | Fano is now primary. But near-chance cells pass "step supported" (accuracy 0.035 → 0.040 gives ratio 20.8), the formula is positive below chance, and 0/0 is undefined. → W1–W4 |
| B2 | PARTLY | Absolute λ, no cap, no ENGINEERING_FAIL: resolved. The new EMA estimator leaves the effective dose undefined by a factor of up to 256 (RB2). → W7 |
| B3 | PARTLY | Calibration step and menu: resolved. §8 still lets thresholds change after the calibration outputs are seen. → W23 |
| M1 | RESOLVED | Loss is taken at answer sites only, for every arm. |
| M2 | PARTLY | Primary panels resolved. The template pool is ill-defined: 16 + 8 + 8 byte-disjoint pairs need 64 bytes, and the pool has 48 (R1 part 3). → W19 |
| M3 | PARTLY | Hamming-1 neighbours are gone. The share of facts with a distance-2 neighbour still rises 0.49 → 0.91 → 1.00 (R1), so §4.1's sentence overclaims. → W20 |
| M4 | RESOLVED | Declared; G3 moved into calibration; attainable probability recorded. Note: R2 has the same √K AdamW confound (its rows also have one event per F/128 updates). |
| M5 | PARTLY | Stated and measured, and A10 added. The OPTIMIZER-DEPENDENT rule has no floor: a lazy arm 4–15× slower can sit near chance and fire it (N9). "Supported" is undefined without a replicate. → W5, W6 |
| M6 | PARTLY | Minimal support adopted. R0 reads at the record's earlier positions, which answer-site-only knock-outs miss (N4). Specificity and group ablation are underspecified. → W10, W11 |
| M7 | PARTLY | Global floor adopted, and the revival limit is stated. Open: the EMA gradient (RB2), which positions feed u, u₀, and that the floor can be met by soft mass alone (N3). → W7, W8 |
| M8 | PARTLY | (a)(b)(c)(d)(e)(f)(g) all adopted. New: an at-chance cell is never "plateaued" and so lands in UNDERTRAINED. UNDERTRAINED, INTERMEDIATE and NOT REPLICATED have no decision-map entry. Key-32 has no replicate. → W2–W6 |
| M9 | RESOLVED | R0a added and limits declared. Minor: no R0a at 4K, so the 4K ladder is incomplete. → W26 |
| M10 | PARTLY | Simulator, traces, layouts, oracle tie rule, references and precedence all adopted. Open: the dead COLLAPSED row (RB3); DEGENERATE ranked above COLLAPSED; W undefined per trace type. → W12, W13, W29 |
| M11 | PARTLY | Replay, the a_A⁰ floor, the memory-only arm and NO ADVANTAGE added. Open: the dense arm's own a_A⁰ has no floor; "cannot be met" is false in general; which arms are classed; whether optimizer state carries over (N7). → W15 |
| M12 | RESOLVED | Not run; human acceptance is required (§0 item 1). The reasoning is correct. |
| M13 | PARTLY | Corrected interval adopted. "16 tests" matches no count I can derive (20 or 24; R5). Trained-cell unseen-fact accuracy is not gated. → W17 |
| M14 | PARTLY | Cached evaluation and dense cost adopted; caps at decision 2. Open: reductions conflict with the class rules; the "8 h at E = 32 with 3 workers" statement contradicts the budget's own table; key-32 cost (N8). → W28 |
| m1 | PARTLY | Permutation tests adopted. With 10,000 permutations the smallest attainable p is 1.0·10⁻⁴, so a test can reject only if k ≤ 10; k is not stated (R5). → W18 |
| m2 | RESOLVED | Ties counted wrong. |
| m3 | RESOLVED | Σ-mass reported. |
| m4 | RESOLVED | 63 targets, 8 answer sites. Checked: the last answer byte is target 63. |
| m5 | RESOLVED | Mixed-cluster panel added; unseen facts in separate contexts. |
| m6 | RESOLVED | ½U snapshots. |
| m7 | RESOLVED | Chunking, no batch change. |
| m8 | RESOLVED | ρ = 1 descriptive. |
| m9 | RESOLVED | §0 item 6, and cache/U\* reported. |
| m10 | RESOLVED | NOT REPLICATED in every lane. Seed disagreement is unhandled. → W16 |
| m11 | RESOLVED | Precedence given. But see RB3. |
| m12 | RESOLVED | Group ablation is now a condition; it must say "values only". → W11 |
| m13 | RESOLVED | Tree oracle branch at 16K. |
| m14 | RESOLVED | One data draw stated. |
| m15 | RESOLVED | Key traffic labelled an identity. This narrows the draft, though (§4 below). |
| m16 | RESOLVED | ENGINEERING_FAIL scope. |
| m17 | RESOLVED | Per-lane analysis modules (plan I6). |
| m18 | RESOLVED | No gradient matching remains. |

**Strongest objections (REVIEW.md §4)**

| # | Status | Line |
|---|---|---|
| 1 Block 0 may be the real subject | PARTLY | The calibration measures probes and R2 before the freeze. Under the stylized model, a size-dependent difficulty remains at distance 2 (R1 part 2: naive accuracy 0.98 → 0.79 from 2K to 32K facts, equal weights; down to 0.17 with steep recency and noise). The human sees the probes at decision 2. → W20 |
| 2 Metric certifies zero knowledge | PARTLY | Fixed for exact-zero knowledge. Not fixed near chance (RB1). → W1–W3 |
| 3 Anti-collapse aims at the wrong quantity, or switches off | PARTLY | Target fixed (global). Gradient scale (RB2), soft-mass gaming (N3) and Adam-amplified tiny gradients (N13) remain. → W7, W8, W22 |
| 4 U\* counts diffuse reads | PARTLY | Better. Cross-position storage (N4) and longer supports under spreading can still move U\*. → W10 |
| 5 Size-dependent optimizer confound | PARTLY | Stated and measured. The A10 rule can mislead (N9). → W5 |
| 6 Locality mostly measures cluster-following | RESOLVED as disclosure | But note: within-query packing alone passes the 0.80 bar (N17). → W14 |
| 7 Staged alternative | RESOLVED | Offered as a human option in §3. |

## 2. What revision 2 newly got wrong or left undefined

Severity: **RB** = blocker for Decision 1, **N** = major or minor as marked.

**RB1 — Near-chance cells pass "step supported" and can be CAPACITY_PARTIAL (major; partly my own B1 error).** `r2_fano_and_class_edges.out.txt`:
- Near chance, Fano bits per fact ≈ 23.8·(acc − 1/32)², so ratios of two near-chance cells are ratios of squared noise. 4K at 0.035 → 16K at 0.040 gives I = 0.66 → 13.8 bits, **ratio 20.8**. The 16K accuracy 0.040 is above the G2 upper bound of 0.0392 (8,192 facts, level 1 − 0.001/16). So the step is supported.
- Equal near-chance accuracy at both sizes gives ratio exactly 4.0 on the proportional track (F quadruples). 16K at 0.036 → 64K at 0.036 is supported, since 0.036 > 0.0352 at 32,768 facts.
- CAPACITY_PARTIAL then needs only beats-dense (a dense adapter near chance is easy to beat by 10%) and dependence. Dependence holds: chance-correct facts become incorrect under knock-out with p ≈ 1/32 ≤ 2/32. **PARTIAL at 4% accuracy is reachable.** My B1 fix ("accuracy above the G2 interval") was insufficient.
- The formula is positive below chance: 0.046 bits per fact at accuracy 0, and 2.6·10⁻⁴ at 0.028. A noise draw below chance gives positive "information".
- I_N = 0 gives x/0, which is undefined.
- At chance, the plateau rule "gain < 5% of I(U)" reads 0 < 0, which is false. A memory that learned nothing is therefore UNDERTRAINED forever.
- UNDERTRAINED, INTERMEDIATE and NOT REPLICATED have no decision-map entry.

**RB2 — The EMA usage term's gradient is undefined up to a factor 16–256 (major).**
- With u_t = (1−b)·u_{t−1}.detach() + b·ū_t and b = 128/F, autograd gives ∂R/∂θ = b·(∂R/∂u)·∂ū/∂θ. `r3` part 1: the ratio to the "full-weight" reading is **0.0625 / 0.0156 / 0.0039** at 4K / 16K / 64K.
- Revision 2 says only "the gradient flows only through the current batch's term". An implementer could build either version. Under the literal one, α_u = 1 at 16K acts like α_u ≈ 0.016 of the stated force, and the two doses would differ in size from their stated values by a size-dependent factor.
- Also unspecified: u₀; whether ū comes from answer sites or all 63 positions (P8 used all positions; here 7/8 of R0's reads are not at answer sites); and the "batch-normalized" convention.

**RB3 — Lane C's gate makes COLLAPSED unreachable (major).**
- §3 gates the trained Lane C part on "the cell is UTILIZATION_PRESERVED or UTILIZATION_IMPROVED".
- A C1 cell that collapses therefore fails the gate and is reported "H17-LOC NOT EVALUATED, descriptive only". The §8.4 row "§8.3 COLLAPSED" can never fire, and the utilization condition inside LOCALITY_POSITIVE is redundant.
- P8's actual failure mode, a locality term collapsing usage, would get the softest label.
- The draft's intent is "after Lane A capacity gate and **B guard** pass". That means Lane B's usage term works, i.e. the α_u = 0.25, α_c = 0 cell, not the locality cell itself.
- Separately, DEGENERATE (row 2) precedes COLLAPSED (row 3). A collapsed cell usually has a degenerate null, so the collapse would be printed as DEGENERATE.

**N4 — R0 can store answers at earlier positions of the record, which answer-site knock-outs miss (major).**
- R0 reads memory at all positions, and the loss gradient reaches those reads through block 1's attention. The checksum position is immediately before the answer site, and its hidden state already holds all five identifier symbols. So memory can deliver the answer there, and block 1 can carry it forward.
- A knock-out at the answer site alone then leaves the fact correct. The fact has no minimal support, dependence ("≥ 90% of correctly answered facts have a minimal support") fails, and POSITIVE/PARTIAL become impossible for a memory that works.
- R0a − R0 would show the effect but not repair the rule. Cached all-position selections make the fix cheap (W10).

**N3 — The usage floor can be met by soft mass outside the top-8 (major).** `r3` part 3, N = 16,384, floor ln 8,192 = 9.01 nats:
- With 1,000 hard-effective slots (6% of N), H(u) reaches 9.07 if π ≈ 0.5 on the 56 other candidates drawn from an 8,192-slot pool.
- With 2,000 hard slots, π ≈ 0.3 suffices (9.19).
- The hinge's gradient pushes the 9th–64th scores toward τ, which is the cheapest direction. P8's C10 already showed 0.209 soft mass outside the top-8.
- §8.3 uses U\* (hard), which protects the classes. But "entropy-effective slots" in ENTROPY_INFLATION is not said to be hard, and a "usage term satisfied by proxy" is not reported as such.

**N5 — Calibration-to-threshold leak (major).** §8 says "Thresholds may change only before the freeze, by a recorded revision approved at the second decision". §12 step 4 says calibration "may change one thing". Read together, the lead could revise any threshold after seeing probe and R2 curves, before the freeze. → W23.

**N7 — Lane D comparison (major).**
- The dense arm's own phase-A accuracy has no floor. If dense learns A poorly (say a_A⁰,dense = 0.2), flat beats it by 0.10 trivially, giving INCREMENTAL_POSITIVE because dense never learned A.
- "If dense retains a_A ≥ a_A⁰ − 0.10, the last condition cannot be met" holds only if a_A⁰ means the flat arm's value and flat cannot exceed it. With each arm's own a_A⁰ it is false.
- NO ADVANTAGE OVER DENSE has no position in the first-match order.
- Not stated: which arms receive classes; whether phase B restores V1's AdamW moments (the draft forbids silent optimizer carry-over); and how Lane D contexts are built (clusters for A and B?).

**N8 — Registered reductions break class rules; the budget sentence on 8 h is inconsistent (major).** `r5_matrix_budget.out.txt`:
- Recount: **100 cells** (14 / 64 / 22 at 4K / 16K / 64K), matching §10. Serial training at E = 32 is 9.1 h on my recount against the budget's 9.9; the budget is slightly conservative.
- 8 h with twofold headroom:

| Exposure | 2 training workers | 3 training workers |
|---|---|---|
| E = 32 | fails (5.3 h → 10.6 h); still fails after reductions 1–3 (4.02 h → 8.04 h) | holds on my recount (3.8 h → 7.6 h). By the budget's own 4.1 h → 8.2 h it does **not** hold, and not with key-32 at 2× cost (8.4 h) |
| E = 64 | never fits | never fits (best 5.1 h after 1–3) |
| E = 128 | never fits | never fits (6.9 h even after reductions 1–4) |

- Each reduction silently changes a rule:
  - (1) "≥ 2.5 in the B102 replicate" cannot be evaluated at 64K;
  - (2) KEY-WIDTH-LIMITED is defined on the 16K→64K step, so without A7 at 64K it is **not assessable at all** (not "only at 16K");
  - (3) "beats dense … both seeds" needs a dense cell per seed;
  - (4) removes A4 64K, A10 64K, A7 64K, R1/R0a at 64K, and so EMPTY-SLOT-EFFECT, OPTIMIZER-DEPENDENT at 16K→64K, KEY-WIDTH-LIMITED and two ladder terms. Decision-map item 1 ("without OPTIMIZER-DEPENDENT") then becomes undeterminable.
- Three training workers exceed the draft's "at most two" (§4 below).

**N9 — The OPTIMIZER-DEPENDENT annotation can fire from undertraining (major).**
- Row-lazy Adam moves a row 1·lr per exposure, against 3.9 / 7.6 / 14.5·lr under AdamW (`r3` part 5). The lazy arm is 4–15× slower at every size and may be near chance everywhere. Its "not supported" would then attach OPTIMIZER-DEPENDENT to a positive AdamW class and block decision item 1.
- A floor fixes this. Optionally, lazy lr = 0.012 makes the lazy arm move 4.0·lr per exposure at every size, equal to AdamW at 4K, so it differs from AdamW only in the size dependence (PENDING LEAD REVIEW).
- The lazy arm needs no dense comparison of its own: the annotation uses step support only, and a dense adapter has a gradient on every row at every update, so row-lazy and AdamW coincide for it.
- Specify that row-lazy applies to the key and value tables only; projections, gate and router use AdamW.

**N13 — Adam still amplifies vanishing regularizer gradients (major, measurement exists, no rule).**
- With fixed λ, a key row whose only gradient is a constant regularizer gradient of 10⁻⁶ moves 0.99·lr per update; at 10⁻⁷, 0.91·lr (`r3` part 4).
- This is the draft's §7 concern ("AdamW updated sparse-key coordinates that had no language-loss gradient"). §6.3 measures it but no rule reads it. → W22

**N17 — LOCALITY_POSITIVE is reachable without planted structure (minor; framing).**
- `r4_locality_ratio.out.txt` approximates "own optimized layout" by the better of identity and oracle-cluster layouts. The random-sharing reference gets E = 0.76–0.79 (C6 reproduced).
- Cluster-coherent sharing must cover about 35–50% of facts to reach ratio ≤ 0.80 (p = 0.3 gives 0.85; p = 0.5 gives 0.65).
- A memory that packs each query's 8 slots into one 8-slot page, with **no** cluster structure, reaches ratio 0.14–0.17. This is real per-query locality, and it is what R_co rewards. But §8.4's "expectation" and §13's bullet frame the test as cluster-following, and the draft asks for within-query co-selection and temporal reuse to be reported separately. → W14

**N16 — My own unsupported statement repeated as fact (minor; my error).** §7 says "both doses would have hit the cap in the tree cells" "in P8's own records". My REVIEW B2(b) argued this but did not compute it: `c3` measured entropies only, not gradient norms. → W21

**Minor.**
- **N10:** the template pool (W19).
- **N11:** distance-2 density (W20).
- **N12:** both α_c doses are large next to a learned answer loss (0.2–0.9 nats). R_co of random selections is 0.998, so α_c = 1 costs 3.96 nats, more than the chance-level answer loss of 3.47, from step 0. "Worst value costs α_c · ln 32" is off by 8/7 unless R_co is shifted by 1/8. PENDING LEAD REVIEW on adding a small dose such as 0.05.
- **N14:** G2 counts (W17).
- **N15:** permutation resolution (W18).
- **N18:** §8.3 seed handling, the dose-zero floor, and U\* NOT INTERPRETABLE (W16).
- **N19:** the decision map (W4).
- **N20:** the 4K ladder (W26).
- **N21:** key-32 cells costed as key-16 (W28).
- **N22–N23:** group-ablation and specificity definitions (W11).
- **N24:** TASK_CEILING_FAIL consequences (W25).
- **N25:** the tree's layout constraints; a DEGENERATE reference (W13).
- **N26:** Lane D contexts (W15).
- **N27:** U\* can rise through longer supports (W10).
- **N28:** per-cell exposure reporting (W31).

**Checked and sound:**
- The checksum code gives distance ≥ 2 at every size.
- "A fact's own record never appears earlier" is automatically true with 8 distinct facts per context, and is sufficient against own-answer copying. Cluster-mates' answers in context carry no answer information because answers are independent. Expect only a symbol-frequency bias, which the mixed-cluster panel measures.
- The checksum symbol sits next to the binding byte. Under the stylized additive model it helps slightly (32K, equal weights: 0.79 vs 0.69 naive accuracy) and never hurts. But 60% of distance-2 neighbours share it.
- No new answer leakage found.
- E = 64/128 is coherent:
  - fixed compute = U_16K = 4,096 / 8,192 updates;
  - 4K cells run to U_16K (four times their own matched point);
  - 64K cells snapshot at ½U_16K and U_16K before their own U;
  - both estimands exist at every size.
- The plateau rule ½U vs U treats a curve as still growing if it rises like t^0.074 or faster (r2 part 4). That is acceptable once at-chance cells are handled (W3).
- M = min(N, 8F)/2 equals N/2 on the proportional track. The 8,192 at D04 64K is unused, because no usage cell is on the fixed track. Requiring an entropy of at least ln(N/2) is sensible: a spread memory gives ≈ ln N − 0.1, and P8-like collapse (127 effective slots) is far below.
- λ_u at α_u = 1 costs 0.33–0.45 nats one nat below the floor, and 1.3–1.9 nats at P8-like collapse (`r3` part 2). Because the hinge switches off at the floor, it cannot dominate a learned task beyond restoring spread, *provided* RB2 is fixed.
- Group ablation is computable from cached all-position selections and block-0 outputs. Only block 1 is recomputed, about 16.7M position-forwards per 64K panel for 64 groups.
- Minimal support is well defined when no prefix works (the fact has none). It is not monotone in prefix length, but "shortest prefix" is still defined.

## 3. Required changes, ready to paste

PENDING LEAD REVIEW marks a number that is a scientific choice; the need for *some* fixed value is not optional.

- **W1 (§6.1, after the I_acc bullet):** "I_acc is set to 0 for a cell whose accuracy is at or below the upper end of the G2 interval for its fact count. (The formula is positive below chance: 0.046 bits per fact at accuracy 0.)"
- **W2 (§8.2, replace 'Step supported'):** "**Step supported** (N → 4N): accuracy ≥ 0.25 at both N and 4N in every cell of the step [0.25 ≈ 0.47 Fano bits per fact; PENDING LEAD REVIEW]; I_{4N}/I_N ≥ 3.0 in both B101 seeds; and ≥ 2.5 in the B102 replicate where one exists (A7 and A10 have none and use the two B101 seeds only). A ratio with I_N = 0 is +∞."
- **W3 (§8.2, replace 'Plateau' and row 2):** "**Plateau:** I(U) − I(U/2) ≤ 0.05·I(U) in both seeds, with I set to 0 by §6.1 (a cell at chance at both snapshots has plateaued)." Row 2: "some step has, in both seeds, ratio < 2.0 or accuracy below 0.25 at its larger size, and its larger cell has plateaued; the failing step is printed with the class."
- **W4 (§8.7, add item 5):** "UNDERTRAINED, INTERMEDIATE, NOT REPLICATED or NOT_EVALUATED in Lane A → no capacity decision; item 4 applies unless the human lead decides otherwise."
- **W5 (§8.2, OPTIMIZER-DEPENDENT):** "**OPTIMIZER-DEPENDENT** if a step supported under AdamW is not supported in the row-lazy arm, and the row-lazy arm's accuracy at the smaller size of that step is ≥ 0.25 in both seeds; otherwise the annotation reads OPTIMIZER-ARM UNINFORMATIVE." (§5.6) "Row-lazy applies to key and value tables only; projections, gate and router use AdamW. [Row-lazy learning rate 0.003, or 0.012 to match AdamW's per-exposure movement at 4,096 slots: PENDING LEAD REVIEW.]"
- **W6 (§8.2, KEY-WIDTH-LIMITED):** append "'Supported' for key-32 uses the two B101 seeds. If A7 at 65,536 is dropped, KEY-WIDTH-LIMITED is not assessed."
- **W7 (§7, replace the u sentence):** "u_t = (1 − b)·u_{t−1} + b·ū_t with b = 128/F; u_{t−1} is detached; u₀ is the first batch's ū. ū_t is the batch-normalized π usage **at answer sites only**. The applied gradient is λ_u·(∂R_glob/∂u at u_t)·∂ū_t/∂θ, i.e. **without** the factor b." [The alternative, keeping b, must then be stated with its effective λ_u·b: PENDING LEAD REVIEW, but one must be written.]
- **W8 (§7 and §8.3):** "Every B1 and C1 cell reports H(u) from π and from hard top-8 selections at answer sites, and soft mass outside the top 8. Entropy-effective slots in §8.3 are computed from hard top-8 selections at answer sites. A cell whose soft H(u) ≥ ln M while its hard entropy-effective-slot ratio is < 1.05 is annotated SOFT-USAGE ONLY."
- **W9 (§7, coefficients):** "λ_c multiplies (R_co − 1/8), so the best value costs 0 and the worst α_c·ln 32." [Adding α_c = 0.05: PENDING LEAD REVIEW. At α_c = 1 the term costs 3.96 nats at random selection, more than the chance-level answer loss.]
- **W10 (§6.2, knock-out and minimal support):** "Knock-out removes the chosen slots' values at the answer site **and at the record's six earlier positions** wherever those slots are selected; selections and weights stay as cached. Candidate slots are the union of slots selected at the record's seven input positions, ordered by summed weight. Reported for every cell: the share of correct facts that stay correct when the whole answer-site read is removed, and the mean minimal-support length. UTILIZATION_IMPROVED additionally needs a mean minimal-support-length ratio ≤ 1.10 [PENDING LEAD REVIEW]."
- **W11 (§6.2, specificity):** "… 8 slots drawn from other facts' minimal supports, excluding every slot selected in f's record …; zeroing a group sets its **values** to zero at all positions, selections kept."
- **W12 (§3, Lane C gate):** "Trained part: the 4K→16K step is supported for the architecture concerned (§8.2), and that architecture's B1 cell with α_u = 0.25, α_c = 0 is UTILIZATION_PRESERVED or UTILIZATION_IMPROVED against its dose-zero 16K cell." (§8.3 header) "C1 cells are classed against the B1 α_u = 0.25, α_c = 0 cell of the same architecture and seed."
- **W13 (§8.4 table):** "2 COLLAPSED / QUALITY_FAILED; 3 DEGENERATE (any primary setting degenerate for the case **or** its reference)". Also: "For the tree, the optimized layout keeps each branch's slots contiguous [or not: state which]."
- **W14 (§8.4 expectation and §13):** add "A memory that packs each query's eight slots into one page reaches an E ratio of about 0.15 with no cluster structure (auditor toy R4); cluster-coherent sharing must cover about 35–50% of facts to pass 0.80. Pages per query (within-query co-selection) and cross-query reuse are reported separately for every locality cell." In §13 replace the bullet with: "That cross-query locality found here would arise without planted structure; within-query packing is not evidence about clusters."
- **W15 (§8.5):**
  - Replace the last condition of row 4 with: "and the arm's forgetting a_A⁰ − a_A is at least 0.10 smaller than the dense sequential arm's, whose own a_A⁰ must be ≥ 0.5 (else NOT_EVALUATED)."
  - Replace the NO ADVANTAGE paragraph with: "NO ADVANTAGE OVER DENSE is an annotation printed with the class when the dense sequential arm's forgetting is ≤ 0.10."
  - Add: "Classes are assigned to flat sequential, flat memory-only and tree sequential, each against dense sequential. Every sequential arm restores the AdamW state saved at V1 [or resets it: PENDING LEAD REVIEW, but stated]. Sets A and B have their own clusters of 16; phase-B contexts contain B facts only; replay contexts contain A facts only."
- **W16 (§8.3, after the header):** "Every rule is evaluated per seed against the dose-zero cell of the same seed, and must hold in both seeds and both panels; seeds that disagree give INTERMEDIATE. Lane B classes need dose-zero 16K accuracy ≥ 0.25 in both seeds, else NOT_EVALUATED. If U\* is NOT INTERPRETABLE for the case or its reference, COLLAPSED is decided by the I ratio alone, and ENTROPY_INFLATION, IMPROVED and PRESERVED become INTERMEDIATE."
- **W17 (§8.1 G2):** "G2 tests, per primary panel: the no-memory baseline on the 2,048-, 8,192- and 32,768-fact sets (the fixed track uses the 2,048-fact proportional set), and the unseen-fact set: 8 tests, interval level 1 − 0.001/8. The unseen-fact accuracy of every trained memory cell is reported against the same interval; a cell outside it is flagged LEAKAGE and its lane is not interpreted until the auditor explains it."
- **W18 (§4.6 item 2):** "The number of tests k per stream is listed in the config; permutations ≥ 2,000·k; Bonferroni within stream."
- **W19 (§4.2 template):** "The 48-byte pool is split by seed into disjoint byte sets: 32 bytes for T (16 separators and 16 binding bytes, paired one to one), 8 for H1 and 8 for H2 (each 4 separators × 4 binding bytes, 8 of the 16 combinations by seed). No byte appears in more than one of T, H1, H2."
- **W20 (§4.1, replace 'Without this … unrelated to memory.'):** "This removes one-symbol neighbours (without it, 22% → 98% of facts would have one). It does not hold neighbour density constant: the share of facts with a two-symbol neighbour still rises from 49% to 91% to 100%, and 60% of those neighbours share the checksum symbol next to the answer site (auditor check R1). Accuracy is reported separately for facts with and without such a neighbour."
- **W21 (§7, last paragraph):** replace "and both doses would have hit the cap in the tree cells" with "and, by the auditor's argument (not computed from the records), both doses would probably have hit the cap in the tree cells".
- **W22 (§6.3 or §8.3, annotation):** "REGULARIZER-DRIVEN MOVEMENT is printed with a B1 or C1 class when more than half [PENDING LEAD REVIEW] of the cell's cumulative key movement occurred on updates where the row had no task gradient."
- **W23 (§8 opening and §12 step 4):** "After the calibration outputs are written, the only changes allowed before the freeze are E by this rule, sizes marked TASK_CEILING_FAIL, and the registered reductions of `RESOURCE_BUDGET.md` with their rule amendments. Any other change to a threshold, rule, dose or the matrix is a new design revision. The auditor re-checks it, and it is presented at decision 2 as made after calibration."
- **W24 (§12 step 5):** "The rehearsal entry point writes records only through a validator whose allowed keys are the whitelist; stdout and stderr go to a file the auditor checks for loss or accuracy values; no progress display shows loss."
- **W25 (§8.1 G3):** append "If a size is TASK_CEILING_FAIL, every step involving it is NOT_EVALUATED. CAPACITY_POSITIVE cannot be assigned if 65,536 fails. If 16,384 fails, Lanes B, C (trained part) and D are NOT_EVALUATED."
- **W26 (§10):** add the dependencies.
  - Training: each D2 sequential, memory-only or replay arm depends on the D1 cell of the same architecture and seed; every other cell is independent.
  - Analysis:
    - capacity classes depend on A1/A2 at all sizes (including B102) and on A8;
    - annotations depend on A4 with A1 4K, and on A10, A7 and A3;
    - B1 depends on A1/A2 at 16K;
    - C1 depends on A1 16K flat and on the B1 α_u = 0.25 cells;
    - the Lane C gate depends on A1/A2 at 4K and 16K and on the B1 α_u = 0.25 cells.
  - Ladder at 4K: "reports exact − R2 and R2 − R1 only (R0a is not run at 4K)", or add 2 cells.
- **W27 (§0):** add items 7–13 of §4 below.
- **W28 (`RESOURCE_BUDGET.md`):**
  - Replace "The draft's 8 hours hold twofold headroom only at E = 32 with three training workers. They do not hold at E = 64." with: "By this budget's figures, twice the E = 32 projection with three workers is 8.2 h, just above 8 h (the auditor's recount gives 7.6 h, or 8.4 h if key-32 costs twice key-16). With two workers, or at E ≥ 64, 8 hours do not hold even after the registered reductions; the human lead must then raise the cap or the study does not run as registered."
  - Attach to each reduction its rule change:
    - (1) "the 16K→64K step uses the two B101 seeds";
    - (2) "KEY-WIDTH-LIMITED is not assessed";
    - (3) "beats dense at 64K compares both memory seeds with the single dense seed";
    - (4) "EMPTY-SLOT-EFFECT, OPTIMIZER-DEPENDENT and KEY-WIDTH-LIMITED at 16K→64K, and the 64K ladder terms R1 − R0a and R0a − R0, are not assessed; a CAPACITY_POSITIVE class is then printed with 'OPTIMIZER-DEPENDENT: not assessed', and decision item 1 needs the human lead's explicit acceptance of that."
  - Cost key-32 cells at twice key-16.
- **W29 (§8.4 cache rule):** "W is computed separately for each trace type."
- **W30 (§8.2 TREE_COMPETITIVE):** append "Logical key products (§5.2) are printed beside it. The draft's 'tree must beat strong flat' is relaxed to 'not worse than 0.97 at lower logical work' (§0)."
- **W31 (§6.3):** append "Every cell reports examples, tokens, updates, unique facts, the exposure distribution and wall time (draft §5)."

## 4. Departures from the human draft that §0 does not list

The six listed are correct. Missing, each to be added to §0 for explicit acceptance (W27):

7. **Three training workers** (§11). The draft permits at most two concurrent training workers, and the E = 32 budget depends on three.
8. **Aggregate RSS 12 GiB** against the draft's 8 GiB (§0 item 4 names only the 8 h and 2 GiB).
9. **Key-on-storage reduced to an arithmetic identity.** The draft (§8, D09) asks for a new corrected simulation with strict cache-capacity invariants.
10. **Layout controls dropped.** The draft (§8) asks for frequency packing, branch-constrained placement and random-partition controls; revision 2 has identity, optimized co-access and oracle layouts only. Per-query pages, within-query co-selection and temporal reuse are not reported separately (W14).
11. **H17-INC compared with dense sequential only.** The draft compares against "matched rehearsal/adapter/retrieval baselines"; replay and exact retrieval enter no class.
12. **D03 relaxed.** The draft says "a tree must beat strong flat after accounting for active work and quality"; revision 2 has an annotation at ≥ 0.97 of flat, with no class and no decision-map use (W30).
13. **Smaller omissions:**
    - g_L against g_reg on selected and unselected slots is not split (draft §7);
    - per-cell examples, tokens and wall time (draft §5; W31);
    - "medians, full distributions, parent-level paired contrasts" (draft §10);
    - one Opus audit for the study rather than "an independent Opus audit" per workstream (draft §3);
    - oracle routing for the tree at 16K only (draft D06).

Against the human's chat instruction:
- "ten diagnostic scenarios in four parallel tracks": kept (table below; Lane-A-first is only an option).
- Fair flat, dense/adapter, oracle-routing and exact-retrieval controls: present. Oracle routing is tree-only at 16K; the flat analogue is the R1/R2 ladder.
- Isolated benchmarks: kept (§11; rehearsal timing alone).

## 5. Does dropping Family 2 leave the ten scenarios intact?

**Yes, as scenarios; no, as a data contract.**
- D01–D10 name no task family, and each maps to registered blocks and rules below.
- What is lost is the draft's §5 item 2, and with it H17-CAP's question whether more memory "supports computation rather than merely a lookup table". After this study that question remains unanswered and unanswerable with this architecture (one read between frozen layers). §0 item 1 should say this in those words.

D01–D10 → block and rule mapping (paste-ready for the ADR):

| ID | Draft question | Registered blocks (cells) | No-training controls | Rule or output that answers it |
|---|---|---|---|---|
| D01 | Oracle / exact lookup at 4K/16K/64K; task difficulty and attainable ceiling | A5 R2 at 3 sizes (6 cells, diagnostic); calibration R2 curves to E = 128 (§12 step 4, rehearsal seeds) | exact retrieval, no-memory baseline, frozen-hidden probes, attainable answer probability | G1 (dictionary = 1.0), G2, G3 → TASK_CEILING_FAIL; ladder term exact − R2 |
| D02 | Flat memory across sizes | A1 flat R0 (9, incl. B102); A8 dense (6) | no-memory | §8.2 flat class (step, beats dense, dependence) |
| D03 | 16K: flat vs fixed tree vs learned tree | A1 16K, A2 16K, A3 fixed tree (2) | — | TREE_COMPETITIVE / TREE_BEHIND annotation; fixed tree descriptive; logical work §5.2 |
| D04 | Fixed facts across sizes | A4 (4) + A1 4K | — | EMPTY-SLOT-EFFECT annotation |
| D05 | Proportional facts; exposure and compute budgets | A1, A2 (18); A8 (6); A10 row-lazy (6) | — | §8.2 classes for flat and tree, matched-exposure and fixed-compute snapshots (§5.5); OPTIMIZER-DEPENDENT |
| D06 | Oracle-routed vs ordinary-routed | A5 R1 (6), A5b R0a (4), A6 tree R1 and tree oracle branch (4), A7 key width 32 (8) | frozen-hidden probes | ladder report (gaps ≥ 0.5 bit material); KEY-WIDTH-LIMITED; decision-map item 3 |
| D07 | Bounded usage term with zero-dose controls | B1 (8); controls A1/A2 16K | — | §8.3 utilization classes |
| D08 | Usage + locality vs optimized flat co-access | C1 (8); references A1 16K flat (locality) and B1 α_u = 0.25 (utilization) | — | Lane C gate (§3) and §8.4 locality classes; hierarchy-advantage rule |
| D09 | Trace simulation: cache sizes, row widths, key placement | none trained; uses traces of A1/A2/B1/C1 | planted synthetic traces (§9) | §9 synthetic class tests; ρ × R sweep (descriptive outside the primary four); key-traffic identity |
| D10 | Sequential A → B with snapshots, replay/adapter/retrieval | D1 (6), D2 (14) | exact retrieval (append); version store | §8.5 incremental classes; version-store engineering test |

## 6. Biggest remaining scientific risks (for the human, plainly)

1. Whether the frozen 27K-parameter block exposes a 5-symbol identifier well enough is still unknown. Stylized estimates range from about 0.2 to 0.98 and fall as facts grow. Only the calibration will show it, and it may end the study at a ceiling failure.
2. The optimizer effect favours bigger memories by 4–15× per-row step size, in the same direction as the hypothesis. The row-lazy control mitigates this only if it is itself trained well enough to be informative.
3. The usage and locality terms can each be satisfied by a proxy: soft probability outside the top 8, or packing each query into one page. Honest labels depend on the hard-selection guards being worded exactly.
4. Evidence is one data draw, two seeds and one replicate, with class boundaries at sharp ratios (3.0, 0.97, 0.80). Expect NOT REPLICATED or INTERMEDIATE often. Nothing generalizes beyond this testbed.
5. If calibration selects E ≥ 64, the run cannot meet the draft's 8 hours and two workers. Decision 2 will then be a choice between more budget and a reduced matrix that drops some annotations.

## 7. Files

New in `opus_checks/` (each with a matching `.out.txt`):
- `r1_identifier_codes.py`: neighbour shares under the checksum code, the stylized additive comparison, template pool arithmetic.
- `r2_fano_and_class_edges.py`: the Fano curve, the G2 intervals at level 1 − 0.001/16, near-chance "supported" steps, the plateau rule.
- `r3_objective_gradients.py`: the EMA gradient factor (autograd), λ magnitudes, soft-usage gaming, Adam on tiny gradients, row-lazy movement.
- `r4_locality_ratio.py`: E ratio against coherence share and within-query packing.
- `r5_matrix_budget.py`: matrix recount, training hours at E = 32/64/128 with 2 and 3 workers, reductions, permutation resolution, G2 count.

No other existing file was edited. Nothing was committed.
