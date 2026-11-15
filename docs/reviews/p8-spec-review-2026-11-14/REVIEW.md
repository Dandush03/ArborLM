# P8 specification review: ADR-0015 draft

- Reviewer: **Claude Opus 5.5 (`claude-opus-5-5`)**, from this session's own metadata; auditor role, separate context. Date 2026-11-13 local, 2026-11-14 UTC.
- Reviewed: `docs/decisions/ADR-0015-p8-locality-aware-memory-training.md` (untracked draft on branch `claude/p8-locality-aware-training`, HEAD `57be5ff`), SHA-256 `4f1f26a9787c5b3e86b410c71128a88adf1ca5f8f67b104d66ed5ca46d003f6f`.
- **Status: independent engineering and mathematical evidence. Not Astra validation. Not human approval.** `Astra review: NOT_PERFORMED`. Scientific choices are marked **PENDING LEAD REVIEW**. The human-fixed matrix, panels, 0.80 and 0.90–1.10 margins and resource limits are out of scope and are not questioned.

**Verdict: NOT READY.** Counts: 1 BLOCKER, 6 MAJOR, 10 MINOR. It becomes READY WITH REQUIRED CHANGES once B1 and M1–M6 are resolved in the text. None needs a change to the human-fixed matrix.

## 0. Material, environment, commands

| Item | Value |
|---|---|
| Interpreter | `uv run --locked python` (CPython 3.12.14, torch 2.8.0, float64, CPU), Apple M5 Max, macOS (darwin) |
| Script | `proxy_checks.py` (SHA-256 `4e6af1b9…a4c2`), output `proxy_checks.out.txt` (`d7b35232…2786`); wall time 179 s |
| Script | `tau_check.py`, output `tau_check.out.txt` |
| Commands | `uv run --locked python docs/reviews/p8-spec-review-2026-11-14/proxy_checks.py 2>&1 \| grep -v -e NumPy -e _conversion_method`; same for `tau_check.py`; `uv run --locked ruff check docs/reviews/p8-spec-review-2026-11-14/` (passes) |
| Imports | `arborlm.pilot_model.Memory` only (check E7, parameter layout). No `arborlm.*_analysis`, no implementer code (none exists yet). |
| Data read | P5 **training** step records (`results/p5-2026-11-13/b101-o301-{flat,fixed_tree,learned_tree}-s501/metrics.jsonl`, `train_step` events, field `pre_clip_gradient_norm`). The first line of that file is a P5-panel evaluation record and was displayed in passing; it is not a P8 panel. **No P8 panel, no validation rank ≥ 3072, no checkpoint was opened. No training on any real parent.** |

Every check is synthetic: unit-normalized random keys/queries/router in 16 dimensions with the real sizes (4,096 slots, 16 × 256, T = 0.2, β = 0.25, top-8, 8 rows × 64 positions).

**Auditor defect, kept:** `proxy_checks.py` E4 prints `tau unchanged={bool(True)}`, a hard-coded literal, not a check. `tau_check.py` verifies it separately (τ = 0.425 and the same top-8 set at every bump). The script is left byte-identical; `ruff.toml` exempts UP018 with that reason.

## 1. Findings

### B1 (BLOCKER) — §3's sharpening claims and the §10.2 gate are false; the tie claim is false

Three statements in the spec are false, and §10 makes two of them pre-freeze gates:

1. "By construction the 8 hard-selected slots have π > ½ … for every parameter value." If s⁽⁸⁾ = s⁽⁹⁾, then τ = s⁽⁸⁾ and both slots have π = ½ exactly, so only seven have π > ½ (E2, float64 and float32). §10.2 asks for this "for random and **adversarial** score inputs", and a tie is the obvious adversarial input. `stable_top` exists because ties occur.
2. R_co "cannot be lowered by sharpening … the ratio is unchanged by making π more nearly 0 or 1." This is false. With one whole group selected at inclusion p, R_co = (1 − (1−p)⁸)/(8p): 0.244 at p = 0.51, 0.208 at 0.6, 0.139 at 0.9, and 1/8 only as p → 1 (E3). The stated minimum is reached **only** by sharpening.
3. §10.2: "none of the three decreases when a constructed query's mass is sharpened onto one slot with the top-8 set unchanged." With τ and the top-8 set verified unchanged (tau_check), all three decrease (E4):
   - R_co 0.8821 → 0.8720 when the sharpened slot shares a group with another selected slot;
   - R_temp 0.8656 → 0.8554 when the sharpened slot was used at the previous position;
   - R_conc 0.7566 → 0.7546 when the sharpened slot is a batch-hot slot.

   The gate passes or fails depending on which construction the implementer picks. That is a test design chosen to pass, which a freeze cannot contain.

More generally, π has a **margin direction**: widening s⁽⁸⁾ − s⁽⁹⁾ and pushing the tail down lowers every regularizer without changing any hard selection. At init-like geometry the flat proxy carries Σπ = 19.7 per query, of which 14.3 lies outside the hard top-8 (tree: 11.75 and 5.85; E5). Under R alone, the gap s⁽⁸⁾ − s⁽⁹⁾ grows from 0.03 to 2.9 (flat R_co) and from 0.05 to 5.3 (tree R_conc) (E6). Scores are bounded (|q·k̂|/T ≤ 5, plus the tree prior), so the direction is bounded but large: (s − τ)/β can reach about 40.

**Fix.** Replace the sentence in §3 with:

> "If s⁽⁸⁾ > s⁽⁹⁾, the 8 hard-selected slots have π > ½ and all others π < ½. At a tie s⁽⁸⁾ = s⁽⁹⁾ both tied slots have π = ½. Ties are measure-zero in parameters and are counted at run time."

Delete "It cannot be lowered by sharpening … 0 or 1". Add to §3:

> "All three regularizers are also lowered, with no change in hard selection, by widening the top-8 margin and by sharpening already-selected slots. This is a known non-locality direction of the proxy. Its magnitude is reported per cell as the mean of s⁽⁸⁾ − s⁽⁹⁾ and of Σπ outside the hard top-8 at updates 1, 128, 256, 384 and 512."

In §10.2, replace the sharpening test with: "π > ½ count is 8 on tie-free inputs and 7 at a constructed 8th/9th tie; R_co on one whole group equals (1−(1−p)⁸)/(8p) for uniform p."

### M1 (MAJOR) — §4 "matched pressure" does not survive Adam; α is not the dose at the update level

λ matches norms **before** AdamW. AdamW normalizes each coordinate by √v̂. On coordinates where only g_R is nonzero, the step is about lr whatever λ is. On a first step the R-only rows move 3.00e-3, 3.00e-3 and 2.97e-3 for λ = 1, 0.1 and 0.01, and only drop at λ = 10⁻⁴, where |λg_R| approaches eps = 10⁻⁸ (E8). At init-like flat geometry, with λ set by the rule (assuming ‖g_L|Θr‖ ≈ 0.02), **65,465 of 65,536 key coordinates and all 4,096 key rows** have |λg_R| > eps. 1,933 of those rows were not hard-selected in the batch. So in every regularized flat cell, almost every key moves at roughly full learning rate from R alone, while in C01 unselected keys do not move at all.

The sentence "keeps the regularizer's pull on the routing parameters at half the language-model gradient's magnitude there" is false for the update. "Up to twice" for C10 is also not what Adam does. The same mechanism creates a flat/tree asymmetry: flat spreads π over all 4,096 rows, a tree only over the visited branches.

Gradient clipping is **not** an issue. P5 pre-clip norms for b101-o301 s501 have maxima of 0.055 (flat), 0.062 (fixed) and 0.081 (learned), and 0 of 512 steps exceed 1. Adding ‖λg_R‖ ≤ 0.5‖g_L|Θr‖ cannot plausibly reach 1.0. λ cannot explode either: ‖λg_R‖ = α‖g_L|Θr‖ by construction.

**Fix (PENDING LEAD REVIEW on the option).**
- (a) Keep the rule and correct the text: "λ matches gradient norms before the optimizer. Adam's per-coordinate normalization means that on coordinates where only R has gradient (keys of slots not hard-selected), the update is of order lr regardless of α. α fixes only the relative weight where both gradients act." Then add per-step records: ‖Adam update on Θr‖ for the regularized cell and its baseline, the number of key rows whose update exceeds 10⁻⁴, and clip events.
- (b) Alternatively, define matching in update space. That is more work and changes the method.

Option (a) is sufficient for a pilot. §9 "too weak gives an uninformative null" should then cite this.

### M2 (MAJOR) — The quality guard tolerates losing a quarter of what is being trained

The backbone is frozen and shared by case and baseline, so NLL_disabled is identical for c and b. Then ΔNLL = gain_b − gain_c, and the guard "ΔNLL ≤ +0.005" means "the case may lose 0.005 nats/byte of a memory gain of about 0.02" (§4's own figure): about 25% of the only trained component's effect. The second clause ("memory gain > 0.005") is then almost redundant.

This matters because the regularizers' cheap minimizers degrade retrieval semantics while keeping slot utilization. R_temp is minimized by context-constant selection (E6: hard reuse 0.03 → 0.95), and that is exactly what the count-preserving null, which permutes queries globally, turns into a large E drop. Such a route can be LOCALITY-POSITIVE with U-ratio ≥ 0.80 if utilization across contexts stays high.

**Fix (thresholds PENDING LEAD REVIEW).** Add a relative clause to §7.3:

> "and mean memory gain_c ≥ 0.75 × mean memory gain_b on that panel, and value-association effect_c ≥ 0.75 × value-association effect_b."

Also add a reported (not gating) per-context diagnostic: mean distinct hard-selected slots per 64-query context, as a ratio c/b.

### M3 (MAJOR) — "Without collapsing utilization" is not enforced on positive readings

The scientific question says "without collapsing memory utilization", but:

- LOCALITY-POSITIVE needs only U-ratio ≥ 0.50, so a "reduced" case can be positive.
- **Beats optimized flat** and **architecture advantage** have no utilization condition and no utilization-adjusted ratio against C01 or the flat counterpart.

P7-A/B established that trees' lower misses come from using fewer rows. A tree case could therefore meet "M against C01 ≤ 0.80" by the trees' existing concentration. The architecture-advantage test (raw M and E against C06/C08) omits the ADR-0014 adjusted ratio that exists for exactly this comparison.

**Fix.** In §7.4 item 3, add "and U-ratio ≥ 0.80". A case that meets every other item-3 condition with 0.50 ≤ U < 0.80 becomes **LOCALITY-POSITIVE WITH REDUCED UTILIZATION**, which is not usable for §8. In "Beats optimized flat", add "E-ratio against C01 ≤ 0.80 and utilization-adjusted E-ratio against C01 ≤ 0.80 (fitted on the 12 case and C01 checkpoints) and U-ratio against C01 ≥ 0.80". Add the same three conditions against the flat counterpart in "architecture advantage".

### M4 (MAJOR) — The concentration control is not used by any criterion

§1 says C04/C05 "measure this directly", but no rule refers to them. If C04 (pure concentration) comes out LOCALITY-POSITIVE, the E-based classification has failed to separate concentration, and a positive C06/C08 then means nothing beyond concentration.

**Fix.** Add to §8: "If C04 or C05 is LOCALITY-POSITIVE on either panel, no 'locality beyond concentration' sentence may be written for any case, and the decision memo defaults to (c) with this stated." Also report each locality case's E-ratio beside C04/C05's.

### M5 (MAJOR) — Undefined denominators and ambiguities an implementer would have to guess

1. §7.4 item 3: "all three parents have ratio below 1". It does not say which ratio. Write "two-seed mean E_c(L-COAX) ÷ two-seed mean E_b(L-COAX) < 1 for each parent", and the same for the M-ratio if it is intended.
2. E = m ÷ mean null m. When a cell's selections nearly fit in the 64 cached rows, both are ≈ 0. E6 shows R_temp alone drives a flat memory to 31 distinct slots, below 64 rows. **Fix:** "E is undefined if the mean null m < 0.05 misses/query. A case with any undefined E in a pair is INTERMEDIATE (not evaluable) unless already QUALITY-FAILED or COLLAPSED."
3. The utilization-adjusted ratio on 12 points: if the regularizer moves N_eff so that the x ranges of case and baseline do not overlap, d is pure extrapolation from collinear regressors and can take any value. **Fix:** "ρ_adj is undefined if max x of one group < min x of the other; undefined fails item 3." Also state that "(defined)" means ρ_adj is defined **and** ≤ 0.80.
4. State that M-ratio and E-ratio are ratios of means over the six pairs, not means of ratios, and that the regression is refitted for each panel × setting × tie rule.
5. §7.4 item 6 (WORSE) uses E only. Say explicitly that M ≥ 1.25 with E in band is INTERMEDIATE.

### M6 (MAJOR) — "Same formula" is not matched between flat and tree

The tail term differs between architectures because flat has 8× more candidates near τ: mass outside the top-8 is 14.3 for flat against 5.85 for the tree at init (E5). In the tree, the prior adds a second sharpening axis. The route gap between the two visited branches (up to 10 score units) can push the second branch out of π, and at init 75% of the top-8 already lies in the top branch. Under R alone the architectures reach different hard outcomes (E6, R_co: flat 1.04 groups per query with 106 distinct slots; tree 2.0 groups with 993 distinct slots). An architecture advantage (C07 against C06) could come from the proxy's candidate-set asymmetry rather than from hierarchy. The slot-ID grouping nested in branches is **not** itself a bias: for trees any group crossing branches would be partly unreachable, and for flat any partition is equivalent at initialization.

**Fix (PENDING LEAD REVIEW).** Either:
- (i) compute π for both architectures over each query's top-K₀ candidate scores only (for example K₀ = 64, π = 0 elsewhere), which equalizes the tail; or
- (ii) keep the formula and add to §9 "the proxy's tail mass differs by architecture (measured), so an architecture advantage may reflect the proxy's candidate count", with the M3 conditions as the guard.

## 2. MINOR

- m1. "Clamped to [0, 1−10⁻⁶] inside logarithms" zeroes the gradient once s − τ > 3.45, and E6 reaches gaps of 5.3. Use the exact identity log(1−π) = −softplus((s−τ)/β) and drop the clamp. `proxy_checks.py` does this, and gradcheck passes for all three regularizers (E1).
- m2. The gradient-reach metric "|g_R| row norm > 10⁻¹²" saturates: 4,096 of 4,096 rows at init (E8). Use "rows whose Adam update from the regularized step differs from the λ = 0 update by > 10⁻⁶", or a relative threshold.
- m3. Trees: π is discontinuous, not merely non-differentiable, when the visited pair changes, because slots enter or leave with π jumping to or from 0. R's router gradient flows only through the route difference of the two visited branches, since the log-softmax normalizer cancels in s − τ. Unvisited branches get no regularizer pull. State this in §3.
- m4. R_conc's attainable range is [ln 8 / ln 4096 = 0.25, 1], not [0, 1].
- m5. R_temp's gradient flows into earlier positions' queries through c. No information leaks, but "causal" should be phrased as "the target uses only earlier positions; gradients reach earlier queries".
- m6. §10.3 "λ = 0 reproduces the standard path bit for bit": if g_R has a non-finite entry, 0·inf = NaN. Specify that λ = 0 skips the addition. g_R must be taken with `torch.autograd.grad` (or `retain_graph=True` on the first backward) without altering g_L.
- m7. §10.2 "R_co near 1 on an eight-group selection" holds only with π ≈ 1 and no tail mass. Specify the constructed scores, for example eight slots at +5, the rest at −5.
- m8. The E6 runs (R alone, no language loss) show that every regularizer's unopposed minimizer collapses utilization (flat distinct slots 2,073 → 106 for R_co, 31 for R_temp, 36 for R_conc). The §3 sentence "every query selecting the same eight slots minimizes R_temp and R_conc (not R_co alone)" should add: "R_co is minimized by collapse onto few whole groups". U-ratio < 0.50 catches full collapse.
- m9. Clipping: record per-step whether clipping is active. Based on P5 norms, it is expected never to be.
- m10. C10: "total regularizer pressure up to twice" is not true under Adam (M1). Reword as "two regularizer gradients, each norm-matched before Adam".

## 3. Checked and found sound

- π and τ are well defined and piecewise smooth. Non-differentiability is confined to order changes among s⁽⁷⁾…s⁽¹⁰⁾ and, for trees, branch swaps.
- All three regularizers pass `torch.autograd.gradcheck` in float64 away from ties (E1).
- Through the real `Memory` parameters, values, `wo` and gate receive **no gradient** (`None`) from the regularizers; keys, `wq` and the router do (E7).
- λ is bounded by construction, and the 10⁻¹² guard is adequate.
- Clipping is inactive at P5's scale.
- The study classification across panels and the reuse of ADR-0013/0014 nulls and layouts are coherent.
- Nothing found conflicts with the §15 human direction or with the AGENTS.md/CLAUDE.md standing rules. The matrix, panels, margins and limits are untouched by every fix above.
- M3 brings the classification back in line with the question's own "without collapsing memory utilization" clause, which the draft did not enforce.
