# P5 independent audit: arithmetic, data inspection and retrieval mathematics

- Auditor: Claude Code subagent `arbor-auditor`, model `claude-opus-5-5` (Opus 5.5). Date 2026-11-13.
- Status: independent engineering and mathematical evidence only. **This is not Astra validation and not human approval of anything.** I did not write or supervise any P5 code or analysis.
- Scope limits I followed: no training, no checkpoint loading, no real-data model forwards. I wrote nothing outside this folder. P5 artifacts were only read.
- Environment: macOS (Darwin 27.2.0, Apple Silicon; torch reports CPU capability "NO AVX"), Python 3.12.14, torch 2.8.0, via `uv run --locked --extra pilot python ...`. `uv.lock` was not changed.

## Files in this folder

| File | Content |
|---|---|
| `recompute.py` | Part A script. Uses only the standard library, imports nothing from `arborlm`, and reuses no `results/p5-2026-11-13/audit/*.py`. Reads the 117 `result.json` cell files, the 117 learned/fixed `metrics.jsonl` files and the 36 timing `result.json` files. |
| `recompute.json` | Full output: effects, parent means, marginals, every flag clause, latency (all scopes and workloads), reliability, exploratory descriptives, and all 27 paired rows. |
| `attempt-01..03.{stdout,stderr,exit}` | The three runs of `recompute.py`. All three exited 0. Attempts 01 and 02 ran earlier versions of the same script. Each later version only *added* sections (02: utilization, router gradients, trace normalization counts; 03: timing call counts), and the headline output did not change (the first 30 stdout lines of 02 and 03 are identical). I did not snapshot the earlier source versions separately. |
| `primitive_checks.py` / `primitive_checks.json` | Part B checks on **SYNTHETIC tensors only**. They import `arborlm.pilot_model` only to run its functions on random tensors. |
| `primitive-attempt-01..02.{stdout,stderr,exit}` | Both runs exited 0. Attempt 02 added the shape and position checks. |

Commands (from repo root):
```sh
uv run --locked --extra pilot python docs/reviews/p5-claude-review-2026-11-13/audit/recompute.py
uv run --locked --extra pilot python docs/reviews/p5-claude-review-2026-11-13/audit/primitive_checks.py
```
stderr only contains the torch "Failed to initialize NumPy" warning.

---

## 1. Verified (with evidence)

All values below come from `recompute.json`. "Published" means `results/p5-2026-11-13/README.md` and/or `authorized-scientific-review.md`.

**Integrity**
- 117/117 cells are present and have `outcome = completed`. In every cell, `final.nll` is bitwise equal to the enabled replay.
- `disabled` NLL is **bitwise** equal to the paired baseline in all 108 trained cells.
- The dense identity `Q_X = G_X − (Z − D)` holds with max |diff| = **0.0**, which is stricter than the registered 1e-12.
- Fixed and learned initial NLL are bitwise equal in 27/27 cells. Their initial selected-slot count vectors are identical in 27/27 cells.
- No two variants share a bitwise-equal final NLL in any cell.
- Joint (key/value) permutation:
  - All 81 memory cells are within 1e-6.
  - It is **bitwise** exact in 27/27 fixed and 27/27 learned cells.
  - It is bitwise exact in 26/27 flat cells. The exception is b102-o301-s502: Δ = 8.94e-8, within tolerance. See Discrepancies item D4.

**Means.** Every published value agrees to ≤ 4.8e-16, i.e. the published decimals are the double-precision value rounded.
- Baseline mean: 2.356630571600464.
- Final NLL, mean / SD / min / max:

  | Variant | Mean | SD | Min | Max |
  |---|---:|---:|---:|---:|
  | Flat | 2.333691890 | 0.020962 | 2.294886 | 2.355110 |
  | Fixed | 2.334497243 | 0.019773 | 2.298571 | 2.355647 |
  | Learned | 2.335080704 | 0.020514 | 2.298096 | 2.354743 |
  | Dense | 2.329312946 | 0.021013 | 2.291067 | 2.349517 |

- G (gain over baseline): flat 0.022938682, fixed 0.022133329, learned 0.021549867, dense 0.027317625.
- P (shuffle penalty): flat 0.022679532, fixed 0.021944248, learned 0.021603653.
- R = fixed − learned: mean −0.000583461175, SD 0.001871343960, min −0.004701465, max +0.003432028. Positive in 10/27 cells and 3/9 parents.
- T = tree − flat:
  - Fixed: mean +0.000805353; 26/27 cells and 9/9 parents ≤ .005; fixed beats flat in 12/27.
  - Learned: mean +0.001388814; 26/27 cells and 9/9 parents ≤ .005; learned beats flat in 8/27.
- Q = dense − memory:
  - Means: flat −0.004378944, fixed −0.005184297, learned −0.005767758.
  - Cells / parents within −.005: 15/27 and 6/9 (flat), 14/27 and 5/9 (fixed), 13/27 and 5/9 (learned).
  - Dense is better than flat in 25/27 cells and better than each tree in 27/27.

**Flags.** I recomputed each one from the ADR-0010 §8 text.
- U_flat, U_fixed and U_learned each PASS on all five clauses (27/27 cells, 9/9 parents).
- R FAILS. The U clause passes. The mean, the 22/27-cells clause and the 8/9-parents clause all fail.
- Q tolerance PASSES for both trees.
- The dense tolerance FAILS for all three memory variants. For flat only the mean clause passes.
- W passes for both trees. All 216 comparisons per tree give score and logical ratios of exactly 0.12890625, with 8 values each.
- L_fixed and L_learned both FAIL, not INCONCLUSIVE. All 27 batch-8 addition and model pairs are usable. 0/27 cells and 0/9 parents meet any latency clause.
- The composite is FALSE.

**Latency.** Geometric mean of the tree/flat per-pair median ratio:

| Workload / scope | Fixed | Learned | Dense |
|---|---:|---:|---:|
| bs8 addition | 2.603052229693476 | 2.598485032668176 | 1.0108 |
| bs8 model | 2.190282147732538 | 2.184085943163431 | 1.0015 |
| bs8 lookup | 2.6969 | 2.6950 | n/a |
| bs1 addition | 2.3784 | 2.3851 | 0.9188 |
| bs1 model | 1.8742 | 1.8735 | 0.9324 |
| bs1 lookup | 2.5707 | 2.5684 | n/a |

- The bs8 addition and model values match the published values exactly.
- Ranges of the individual pair ratios: bs8 addition 2.458–2.779, bs8 model 2.091–2.270. All 9 parent geometric means are > 2.

**Timing reliability.**
- I recomputed all 612 records from raw durations: 80 samples, 8 round medians, the median, and the criteria (positive, median ≥ 100× resolution, round-median ratio ≤ 1.25). There are 0 mismatches with the stored `median_ns`, `round_medians_ns` and `usable`.
- Exactly 4 records are unusable, all on the stability criterion:
  - bs8 lookup flat, b101-o302-s502 (ratio 1.268).
  - bs8 lookup fixed, b102-o301-s501 (1.270).
  - bs1 model fixed, b102-o302-s503 (1.265).
  - bs1 lookup fixed, b102-o303-s503 (1.445).
- This matches the published "two batch-8 retrieval-only and two batch-1 records".

**Counts and utilization**
- Timing calls: 9,792 warmups + 48,960 timed = 58,752. The timed sample count in the records is also 48,960.
- Trace key-normalization inputs at batch 8 (512 queries): flat 65,536 elements; both trees 4,194,304.
- Final utilization, recomputed from the slot and branch count vectors:
  - Mean effective slots: 132.34 / 96.25 / 83.02 (flat / fixed / learned).
  - Mean unique slots: 428.59 / 383.41 / 313.11.
  - Hottest-slot fraction: 0.029284 / 0.040757 / 0.043199.
  - Nonzero top-1 branches: 14.22 (fixed) and 10.85 (learned).
  - Normalized top-1 entropy: 0.652912 and 0.613652.
  - Hottest top-1 branch fraction: 0.329350 and 0.353433.
  - Initial effective slots: 234.81 (trees) and 273.15 (flat).
  - All of these match the review.
- Router behaviour:
  - Learned router: nonzero gradient in 512/512 steps in every cell. The minimum `pre_clip_router_gradient_norm` over all 13,824 learned steps is 8.26e-5. Final router movement is 1.081–1.345 L2.
  - Fixed router: movement exactly 0, and the router-gradient field is `None`.
- Resource arithmetic:
  - 108×512 = 55,296 updates; ×512 = 28,311,552 targets.
  - 612×32,768 = 20,054,016 targets; 9×32,768 = 294,912.
  - 1281.554948874982 + 214.90431116719265 = 1496.4592600421747 (matches `suite/terminal.json`).

**`p5_analysis.py` against ADR-0010 §8.** Reading the code clause by clause:
- U, R (including the U_C clause), Q_B/Q_C, the dense tolerance, W, L and the composite (U_C ∧ R ∧ Q_C ∧ W_C ∧ L_C) are implemented as written.
- The ADR's "mean final < mean initial" is coded as `mean(final − initial) < 0`. This is algebraically identical.
- L is INCONCLUSIVE if any pair in either primary scope is unusable. This matches "both scopes must meet reliability rules".
- I found no place where the code's logic contradicts the preregistration. There are two hazards that do not change the outcome; they are listed under Discrepancies (D2, D3).

## 2. Discrepancies

- **D1, accounting snapshot mismatch (cosmetic).** `results/p5-2026-11-13/suite/result.json` → `accounting` differs from the published final values:

  | Field | `suite/result.json` | Published |
  |---|---:|---:|
  | `timing_worker_active_seconds` | 214.90122166718356 | 214.90431116719265 |
  | `combined_worker_active_seconds` | 1496.4561705421656 | 1496.4592600421747 |
  | `timing_stage_wall_seconds` | 1037.5921259160386 | 1037.5952154160477 |

  The published values match `suite/terminal.json` and the orchestration audit. The 0.0031 s gap looks like finalization charged after `result.json` was written. A reader of `suite/result.json` alone gets non-final accounting.
- **D2, name collision in `p5_analysis.py`.** The same key `Q_<variant>` means two different things. In `paired_cells` / `summary` it is the dense contrast `D − X` (line 107). In `quality_clauses` / `quality_flags` it is the tree-versus-flat tolerance on `T` (line 150). The verdicts are unaffected, but anyone reading `suite/result.json` can easily confuse "Q_fixed_tree: pass" (tolerance) with the dense contrast, which fails.
- **D3, the W `validated` field is tautological.** `p5_timing.trace_memory` always returns `"validated": True` (line 318) whenever it does not raise. The `tree["validated"] and flat["validated"]` clause in `p5_analysis.py` (lines 286–287) therefore adds no independent validation. The ADR's "independently validated traces" requirement rests on the separate artifact audit, not on this field.
- **D4, flat joint permutation is not bitwise in one cell.** b102-o301-s502: joint NLL − reference = +8.94e-8. This is within the registered 1e-6 tolerance, so it is not a protocol failure. All 54 tree cells are bitwise exact.
  - On synthetic data, permuting the 4,096 key columns in `q @ K̂ᵀ` was bitwise invariant (`primitive_checks.json` → `shape_position_checks`). So a kernel position effect is not the obvious cause on this build.
  - An exact score tie at the selection boundary, or among the 8 selected scores, combined with the slot-ID tie rule is a plausible cause, as ADR §5 anticipates. I cannot confirm it without loading data.
- No numerical discrepancy was found between my recomputation and any published effect, flag, count or latency ratio.

## 3. Overstatements or omissions in the P5 report/review

1. **Required descriptive outputs are omitted.** ADR §11 requires the final report to include "train/supervised/timing wall times" and §6 says to "Record gate trajectories". They are recorded per cell but are not reported or discussed in the README, the review or `implementation-execution.md`. Two notable facts are therefore not visible:
   - **Training time per variant** (`training_seconds_including_logs_and_saves`, mean of 27): flat 3.06 s, dense 4.25 s, fixed 14.05 s, learned 14.07 s. The trees take about **4.6× flat's training time**, a larger gap than the inference latency ratios. This supports, and was not used for, the latency conclusion.
   - **The dense gate moves the opposite way in every cell.** It goes from −2.0 to a mean of −2.60 (range −2.67 to −2.53, 27/27 below initial). All memory gates rise (means −1.26 flat, −1.34 fixed, −1.36 learned). Because the dense W1/W2 scale is unconstrained, this is not itself a problem, but it is an unreported systematic behaviour. Dense G correlates with the dense gate at r = 0.83 across cells.
2. **The variant ordering is not consistent, and the review does not say so.** "Flat is the best memory architecture on mean NLL" is true on means. Per cell, though:
   - The lowest-NLL memory is flat in 12/27, fixed in 10/27 and learned in 5/27.
   - All six possible orderings occur; flat < fixed < learned occurs in only 7/27.
   - Mean/SD is 0.35 for T_fixed, 0.77 for T_learned and −0.31 for R.

   The mean ordering flat < fixed < learned is within the cell-to-cell spread and should not be read as a robust ranking. The review's tolerance wording is appropriately bounded.
3. **The context for factor effects is not reported.** The order factor O moves gain G by about 0.010–0.012 nats/byte between levels (marginal range: flat 0.0106, learned 0.0102, dense 0.0118). That is roughly 10× the tree-versus-flat differences (|mean T| ≤ 0.0014) and 2× the dense advantage. Backbone B moves G by 0.0025–0.0030; seed by ≤ 0.0013.
   - For the contrasts: B range is 0.0022 for R, 0.0022 for T_fixed and 0.0029 for T_learned. O range is 0.0010 for R and 0.0014 for T_fixed. Seed range is 0.0009 for R and 0.0017 for T_fixed.
   - The paired design removes the main O/B effects from the contrasts. But the factor-dependent spread of the contrasts is as large as the contrasts themselves. The README says marginals are "retained" but does not show this.
4. **What "learned routing" could learn is not stated (see §4.2).** The review frames R as testing "router trainability" and the ADR concedes the experiment "cannot separate learned candidate selection from learned branch-prior weighting". The code is stronger than that concession:
   - The router receives **no gradient about which branches to visit**.
   - It only receives the gradient of the route-score *difference between the two already-visited branches*.
   - That gradient is zero in exact arithmetic whenever all 8 selected slots lie in one branch.

   So the R test is a test of training a two-branch offset term, not of learned candidate selection. The review's sentence "It does not establish that all possible router training methods fail" is correct but understates how narrow the tested mechanism is.
5. **"Positive router-gradient norms in all 512 updates" is weak evidence.** The review correctly says this only rules out a disconnected router. Readers should note that a nonzero batch norm only requires one query in the batch whose selected 8 span both branches. It is not evidence of a useful routing signal. The router's median share of the global pre-clip gradient norm is 0.35, so the router does compete for the global clipping budget.
6. **Bitwise invariance.** "Joint paired permutation controls preserve panel NLL within the registered tolerance" is accurate. The one non-bitwise flat cell (D4) is not called out. This is minor.
7. **R robustness is fine but undocumented.** Leaving out any single parent keeps mean R in [−0.00089, −0.00041]. Leaving out any seed keeps it in [−0.00074, −0.00031]. So no single parent or seed drives the negative mean. Positive R parents are b102-o302, b102-o303 and b103-o302; backbone 102 is the only backbone with a positive marginal (+0.00058). No individual R reaches +0.005. The review's "direct evidence against the registered benefit" is supported for the registered threshold. It should not be read as evidence that learned routing is *worse*: the mean is −0.31 SD and 10/27 cells are positive.

I found no outright numerical overstatement in the README or review. The issues above are omissions and missing context.

## 4. Mathematical findings (Part B)

Notation: `pilot_model.py` line numbers. T = 0.2, EPS = 1e-8, TOP = 8 (l.16). `normalize(x)` = x / max(‖x‖₂, EPS).

### 4.1 Exact scoring and selection rules

- **Query (all memories), l.145:** q = normalize(h·Wqᵀ), reshaped to [N,16].
- **Flat, l.131–134:**
  - sᵢ = ⟨q, normalize(kᵢ)⟩ / T for all 4,096 slots. The key normalization is done once per call for the whole table.
  - Selection is `stable_top(s, 8)` (l.22–34). It takes `topk(9)`. If the 9 values are strictly decreasing, it uses the top 8. Otherwise it does a full `argsort(descending, stable=True)`, so ties go to the lower position, which is the lower slot ID.
  - It returns the 8 gathered scores (descending; equal scores in ascending ID order), the IDs, and `candidate_ids=None`.
- **Tree (fixed and learned), l.140–141 and l.65–84:**
  - Route scores: ρ_b = ⟨q, normalize(r_b)⟩ / T for 16 branches.
  - Visited branches: `branch_ids = stable_top(ρ, 2)`, in rank order, with ties going to the lower branch ID.
  - Candidates: `indices = [b₁·256 … b₁·256+255, b₂·256 … b₂·256+255]`, with the top-1 block first (l.75–77).
  - Each gathered row is normalized per query (`normalize(keys[indices])`, l.78).
  - Score: sᵢ = ⟨q, k̂ᵢ⟩/T + π_{b(i)}, where π = log_softmax(ρ) over **all 16** branches (l.79–82).
  - Selection: `stable_top(s, 8, indices)` (l.35–38). It reorders candidates by ascending slot ID using `ids.argsort`, which is not a stable sort but IDs are unique, then applies the same top-8 rule. Ties therefore go to the lower **slot ID**, independent of candidate order.
  - Returns: selected scores including the prior; selected IDs in descending score then ascending ID order; `candidate_ids` in rank order; `branch_ids` in rank order; `route_scores = ρ`.
- **Prior algebra (exact arithmetic):** π_b = ρ_b − logsumexp(ρ). The logsumexp term is the same for all candidates of a query. It therefore changes neither the ranking nor the selected softmax. The prior is effectively "+ρ_b". Its only effective quantity is ρ_{b₁} − ρ_{b₂}, which lies in [0, 10] logits. The cosine term spans [−5, 5]. So the prior can dominate the within-candidate ranking.
- **Fusion, l.147–148:** w = softmax(selected scores); out = h + σ(gate)·Wo·Σⱼ wⱼ v_{selⱼ}.
- **Fixed versus learned:** the router is a buffer (l.126) or a Parameter (l.128). Everything else is identical.

### 4.2 Gradient paths

**Facts** (code reading, confirmed on synthetic tensors in `primitive_checks.json` → `gradient_paths_learned_tree_synthetic`):
- Selected IDs and `branch_ids` are integer outputs, so neither `topk` selection nor top-2 branch choice is differentiated.
- The loss reaches the lookup only through the 8 gathered selected scores (via softmax) and `values[selected]`.
- Softmax shift invariance gives Σⱼ ∂L/∂sⱼ = 0 for each query.
- Gradient reaches:
  - (i) the **selected** keys only, through the cosine of gathered, normalized rows. Unselected candidates and unvisited slots get exactly zero.
  - (ii) the **selected** values only.
  - (iii) q, and hence Wq, through both the cosine and ρ.
  - (iv) the router (learned only) **only through the prior**.
- Router gradient per query: let G_b be the sum of ∂L/∂sⱼ over selected j in branch b. Then ∂L/∂ρ = G_{b₁}(e_{b₁} − e_{b₂}), because G_{b₁} + G_{b₂} = 0 cancels the softmax-normalizer terms.
  - Only the two visited router rows receive gradient, with equal and opposite route-score gradients.
  - Unvisited rows get exactly zero.
  - If all 8 selected slots are in one branch, the whole router gradient is zero.
- Synthetic confirmation:
  - Single-branch queries: router grad norm ≤ 3.9e-9 (float residue).
  - Unvisited rows: |grad| ≤ 6.0e-10.
  - Two-branch queries: grad norm ≥ 1.06e-3.
  - Route-gradient sum: ≤ 5.8e-11.
- In the fixed tree the same ρ-difference gradient still trains Wq. Fixed routing therefore still learns query-side branch preference, as the ADR notes.

**Inference** (not tested on P5 checkpoints):
- The learned router can only learn how strongly to favour one of the two branches it already visits. In score terms this is a branch-specific offset on visited pairs.
- It gets no signal about whether an unvisited branch would have served better. There is no exploration or counterfactual term.
- Changes in which branches are visited are an untargeted side effect of moving ρ.
- What it could plausibly learn is to sharpen preference for the top-1 branch. That is consistent with the higher learned-tree concentration observed, but causation is not established.
- What it could not learn by gradient is better branch assignment or partition discovery. A null R result is therefore weak evidence about "learned routing" in general.
- Because AdamW here has weight_decay = 0 and a zero gradient leaves a zero moment, slots that were **never** selected during training should remain bitwise at their initial values. This can be checked from checkpoints; I did not check it.

### 4.3 Numerical-equivalence hazards

These were checked on synthetic float32 tensors only (this machine, torch 2.8.0, 1 thread). Bit patterns may differ on other ISAs or builds.

**(a) Normalize all 4,096 keys once, then gather normalized rows.**
- `F.normalize` is row-wise. On this build `normalize(K)[idx]` is bitwise equal to `normalize(K[idx])` (0 mismatching elements), including for a reshaped table.
- So with an unchanged `bmm`, scores, selected IDs and order should be **bitwise identical** here.
- This is not guaranteed in general: a vectorized reduction can choose a different path depending on leading shape or strides on another build.
- Settling test: on each actual checkpoint and every panel batch, require `torch.equal` on the [N,512] candidate scores, on `selected`, and on the selected scores.

**(b) Order the two visited branches by branch ID and drop the `ids.argsort`.**
- `bmm` row results were bitwise invariant to row reordering and to random row permutations here.
- Given bitwise-equal per-slot scores, the selected IDs, scores and tie order are **bitwise identical**. This is because `stable_top` already canonicalizes candidates by slot ID before selecting, so the argsort becomes the identity.
- The prior's `repeat_interleave` must be reordered consistently.
- Two outputs **do change**:
  - `Lookup.candidate_ids` changes order (rank order becomes ID order). Its set is unchanged.
  - If `branch_ids` is also reordered, `branch_ids[:,0]` is no longer the top-1 branch. `pilot_metrics.RetrievalCounts.update` uses `branch_ids[:,0]` for `top1_branch_counts`, so the top-1 utilization statistics (entropy, hottest branch, nonzero top-1) would silently change. Visited counts and candidate unions would not.
- Settling test: `torch.equal` on `selected` and scores; set-equality of `candidate_ids` per row; and an assertion that `branch_ids[:,0]` equals the arg-max route with lower-ID tie-break.

**(c) Replace `bmm` with another contraction.**
- On this build `einsum("bkd,bd->bk")` and 3-D `matmul` dispatch to the same kernel and are **bitwise identical**.
- These alternatives are **not** bitwise identical:

  | Alternative | Mismatching elements (of 262,144) | Max abs diff |
  |---|---:|---:|
  | `(local*q).sum(-1)` | 114,546 | 7.2e-7 |
  | full-table `mm` then gather | 175,196 | 1.2e-6 |
  | `*(1/T)` instead of `/T` | 40,411 | 4.8e-7 |

  These are a few ULP at the ±5 score scale.
- With random keys none of them changed the selected IDs (minimum 8th–9th gap 4.7e-4). On trained checkpoints, however, they **can flip selection at near-ties**, i.e. 8th–9th gaps within a few ULP. They can also turn an exact tie into a non-tie. `near_tie_demo` shows that a 1-ULP difference versus an exact tie changes the selected 8th slot (3372 versus 10).
- They can also reorder near-equal selected scores. That changes `Lookup.selected` order and the softmax/weighted-sum summation order.
- Settling test: on every checkpoint and panel batch, compare scores bitwise. Where they differ, count queries whose selected **ID sets** differ, report each such query's 8th–9th gap in ULPs, and measure the resulting NLL difference.
- Note on the existing preflight claim of "full-branch/zero-prior tree-to-flat equivalence": `visit=16, use_prior=False` selected the same IDs as flat `mm` on 512/512 synthetic queries, but the scores differ bitwise. That equivalence holds only up to floating-point reordering.

### 4.4 Routing-fidelity reference definitions

Let V(q) be the two visited branches, cᵢ = ⟨q, k̂ᵢ⟩/T, and π_b = log_softmax(ρ)_b.

| Reference | Rule | Relation to the tree's actual selection S_T = top8_{i∈V}(cᵢ + π_{b(i)}) | Existing call |
|---|---|---|---|
| **R1, own-score exhaustive** | top8 over all 4,096 of cᵢ + π_{b(i)} (equivalently cᵢ + ρ_{b(i)}) | **Lemma:** S_R1 ∩ V ⊆ S_T (proved; checked on synthetic data). Misses are exactly S_R1 \ V. Selected slots common to both have identical scores. **Certificate:** if the tree's 8th score is strictly > 1/T + max_{b∉V} π_b, then S_T = S_R1 exactly. Use strict > because of slot-ID ties, and allow for cosine slightly exceeding 1 by floating-point error. | `tree_candidates(q, keys, routes, visit=16, use_prior=True)`. This is exact: same prior and tie rule, and on synthetic data the visit-16 scores for the first 512 columns equal the visit-2 scores bitwise. |
| **R1_k, budget curve** | the same rule with k visited branches, k = 2…16 | Nested candidate sets. S_R1 ∩ V_k ⊆ S_{T,k}. Gives recall as a function of k. | `visit=k, use_prior=True` |
| **R2, cosine exhaustive** | top8 over all of cᵢ (the flat rule applied to tree keys) | No subset relation to S_T. Differences mix restriction with the prior. | `visit=16, use_prior=False`. Equal to the flat `mm` rule only up to floating-point reordering; `Memory.lookup` cannot be reused because the variant chooses the path. |
| **R2v, restricted cosine** | top8_{i∈V} cᵢ | Isolates the prior's effect inside V. S_R2 ∩ V ⊆ S_R2v. | `visit=2, use_prior=False` |

`Memory.lookup` does not expose `visit` or `use_prior`. A diagnostic would have to compute ρ as on l.140 and call `tree_candidates` directly.

Beyond ID recall, useful comparisons are softmax-mass recall and the fused-output difference ‖y_T − y_ref‖.

**What each comparison can tell us**
- R1 against S_T is a pure search-approximation fidelity measure, analogous to approximate-nearest-neighbour recall, for the *model's own* scoring function and fixed trained parameters.
- R2 and R2v describe how the hierarchy plus prior departs from content similarity.
- None of these measures prediction quality.

**Training-coverage caveat (fact plus inference)**
- Keys and values receive gradient only when selected (fact, §4.2). Slots in branches that a given query never visited were trained, if at all, only by other queries. Some branches were never visited on the whole panel: learned trees had as few as 3,328 unique candidate slots, i.e. 3 unvisited branches, and fixed trees as few as 3,840.
- Never-selected slots are probably still at initialization (inference, §4.2). Their cosine with q is essentially random: for random 16-dimensional directions the cosine SD is about 0.25, which is about ±1.25 logits after T.
- So an exhaustive-reference "hit" in an unvisited branch may be an accidental match carrying an untrained or foreign value. Low recall does not imply quality loss, and high recall does not imply good selection. The downstream Wo, gate and block 1 are also adapted to tree-distributed mixtures.
- To speak about prediction quality one needs counterfactual held-out NLL. That means a forward pass of the same checkpoint with the reference rule substituted (R1 and R2 at minimum), with per-query loss changes stratified by whether the selection changed. It should be paired with measuring whether reference-selected slots were ever trained, using selection counts or distance from initialization.
- These are real-data forwards and need lead approval. Comparing against the flat-trained cells answers a different, training-procedure question.

## 5. Things I could not verify

- Anything requiring binaries: checkpoints, optimizer/RNG states, per-logit equality, whether never-selected slots are at initialization, and the cause of D4.
- The operator traces beyond the summary fields. I used `key_dot_products_per_query` and similar fields; I did not re-parse `operators` events.
- Chat reporting, commit and push ACK linkage, the source-freeze archive hashes, data-panel reconstruction and parent-tensor provenance. I took these on the existing audits' word and did not re-check them.
- That the published timing reflects an unloaded CPU; the records cannot show this.
- Whether my synthetic bitwise findings (§4.3) hold on other CPUs or torch builds.

## 6. Open scientific questions — PENDING LEAD REVIEW

1. Given §4.2, should any future "learned routing" study state explicitly that the P5 router received gradient only through the two-visited-branch prior difference, and treat P5's R failure as uninformative about learned branch *assignment*? (PENDING LEAD REVIEW)
2. Should the reporting standard require per-variant training wall time and gate trajectories in the main report, as ADR §11 lists? (PENDING LEAD REVIEW)
3. Is a routing-fidelity diagnostic wanted? If so, which reference (R1 / R1_k / R2 / R2v), and is a counterfactual real-data NLL forward on existing checkpoints authorized? (PENDING LEAD REVIEW)
4. Should any future inference-only retrieval implementation be required to prove bitwise identity, or ID-set identity with a tolerance at near-ties, against the P5 reference on every checkpoint before its timings can be compared? (PENDING LEAD REVIEW)
5. Should the dense adapter's systematic gate decrease and its r = 0.83 gain/gate coupling be investigated before dense remains the reference? (PENDING LEAD REVIEW)
