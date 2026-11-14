# ADR-0015 — P8: locality-aware memory training (bounded ten-case pilot)

- Date: 2026-11-13 (America/Panama); drafted 2026-11-14 UTC.
- Status: **EXECUTED ONCE, 2026-11-14 — STUDY INCOMPLETE (55 of 60 cells simulated); NO CASE LOCALITY-POSITIVE — see §17. PENDING HUMAN REVIEW.** Specification as frozen: **REVISION 3, FROZEN (§16). Human-authorized matrix and limits (§15); Fable-drafted, Opus-reviewed and Opus-audited; execution authorized by the overnight direction once every gate passed.** The study matrix, budgets and limits were set by the human research lead in the overnight direction recorded in §15. Astra review: **NOT_PERFORMED**.
- Prepared by Claude Fable 5.2 (`claude-fable-5-2`) as scientific lead under a **study-specific Claude workflow for P8 only**. ADR-0012 remains pending. Nothing here is Astra validation.
- Scope: one bounded CPU/RAM training pilot on frozen P4 backbones, 60 training cells, followed by trace-driven **simulation** of value-page cache misses. No storage device, no capacity change, no new corpus, no change to any backbone parameter. P1–P7-B code, records, thresholds and outcomes are immutable; nothing P8 finds changes them.

## 1. Question

H3 has never been tested: no ArborLM memory has been trained with a locality objective. P7-A and P7-B found that the existing trees' lower simulated page misses come from using fewer rows, and that a flat memory laid out by observed co-access matches them.

> **Can explicit locality-aware training create memory access patterns that outperform a well-optimized post-hoc layout of a conventionally trained flat memory, while keeping predictive quality and without collapsing memory utilization?**

Competing explanations the design separates:

1. **Trained locality.** The objective creates co-access or temporal structure a layout can exploit beyond the checkpoint's own slot popularity.
2. **Concentration.** The objective only makes the model use fewer slots. Misses fall, but the count-preserving null falls with them. Cases C04 and C05 measure this directly.
3. **Quality trade.** Misses fall because routing stops serving prediction.
4. **Architecture.** A learned tree benefits more (or less) than flat memory from the same objective.

A reduction in selected slots or in raw misses is not, by itself, evidence for explanation 1.

## 2. Model and what is trainable

The unchanged P5 mathematics (`src/arborlm/pilot_model.py::Memory`, `p5_model.py::Model`): 4,096 slots, 16 branches of 256, key width 16, value width 32, top-8 selection, temperature T = 0.2, two visited branches for trees, gate initial −2.0. Backbone: frozen P4 parent (27,392 parameters). Trainable: the memory addition only (flat and fixed tree 198,145 scalars; learned tree 198,401).

Selection scores for a query q (unit vector), exactly as in the existing code:

- flat: s(i) = q·k̂ᵢ / T for all 4,096 slots;
- tree: s(i) = q·k̂ᵢ / T + log softmax(route)(b(i)) for the 512 slots i in the two visited branches; route = q·r̂ / T.

The hard top-8 of s is selected; the output is the softmax-weighted sum of the 8 selected values. **Hard slot IDs, top-k indices and page assignments are not differentiable and are never treated as such.**

## 3. The differentiable locality proxy

All three interventions are functions of one relaxation, the **soft inclusion** of slot i in query t:

> **π_t(i) = σ((s_t(i) − τ_t) / β)**, τ_t = ½ (s_t⁽⁸⁾ + s_t⁽⁹⁾), β = 0.25,

where s_t⁽ʲ⁾ is the j-th largest score among that query's candidates (4,096 for flat, 512 for trees) and σ is the logistic function. **π is computed on the query's 64 highest-scoring candidates only and is 0 for every other slot**, for both architectures (revision 2; the review found that over all candidates the soft mass outside the top 8 was 14.3 for flat against 5.9 for trees at initialization, an unmatched pressure). τ_t is a differentiable (piecewise-linear) function of the scores and is **not** detached. When the 8th and 9th scores differ, the 8 hard-selected slots have π > ½ and all others π < ½; in the measure-zero tie case both tied slots have π = ½ exactly. Wherever log(1 − π) is needed it is computed exactly as −softplus((s − τ)/β), with no clamp.

Discontinuities, stated: π jumps by a small amount when a slot crosses rank 64 (about 0.02 at initialization) and, for trees, when the visited branch pair changes. The proxy is differentiable almost everywhere, not everywhere.

π depends on keys, the query projection `wq` and (learned tree) the router, and on nothing else. **It does not depend on values, the output projection `wo` or the gate**, so no regularizer below has a gradient on them: none can lower its loss by closing the gate or shrinking values. This is tested (§10).

Queries are indexed (r, t): context row r of the batch, position t = 0…63. Slots are grouped by slot ID into **reference groups** of 8: g(i) = ⌊i / 8⌋ (512 groups; 32 per branch, nested in branches). Slot IDs are exchangeable at initialization for flat memory, so the reference grouping is an arbitrary fixed partition for flat and a branch-respecting one for trees — the same partition and formula for both.

**R_conc — concentration (C04, C05).** u(i) = Σ_{r,t} π_{r,t}(i) / Σ_{r,t,j} π_{r,t}(j) over the batch; **R_conc = −Σᵢ u(i) ln u(i) / ln 4096**. Lower means the batch's soft selections fall on fewer slots. It carries no within-query or temporal term. It is a confound control.

**R_co — co-access (C06, C07, C10).** The expected number of reference groups a query touches, per expected selected slot:

> N_{r,t} = Σ_g [1 − Π_{i∈g} (1 − π_{r,t}(i))], **R_co = mean_{r,t} N_{r,t} / Σᵢ π_{r,t}(i)**.

For a query whose eight selected slots are one whole group with common inclusion p and no other mass, R_co = (1 − (1 − p)⁸) / (8p): 0.244 at p = 0.51, 0.139 at p = 0.9, and 1/8 only as p → 1.

**R_temp — causal temporal reuse (C08, C09, C10).** For position t ≥ 1 in a row, the probability a slot was softly selected in the previous W = 8 positions of the same row is c_{r,t}(i) = 1 − Π_{u = max(0, t−8)}^{t−1} (1 − π_{r,u}(i)). The expected fraction of a query's selections that are new:

> **R_temp = mean_{r, t≥1} [Σᵢ π_{r,t}(i) (1 − c_{r,t}(i))] / [Σᵢ π_{r,t}(i)]**.

It is causal in the sense that the reuse target of position t contains only positions before t in the same row; the model's queries are themselves causal. Gradients flow through both π_{r,t} and c_{r,t}. W = 8 because both registered cache settings hold 64 rows, eight queries' worth. R_temp is slot-level and layout-free.

All three are in [0, 1]. (R_conc cannot reach 0: at least eight slots carry mass, so its floor is ln 8 / ln 4096 = 0.25.)

**Known non-locality route, stated in advance (review B1): margin widening.** Each regularizer can be lowered without changing any hard selection, by widening the gap between the 8th and 9th scores (pushing selected π toward 1 and the rest toward 0). The review measured all three falling slightly under such sharpening and, with a regularizer applied alone, the gap growing from 0.03 to 2.9 (flat) and 5.3 (tree). This route spends regularizer pressure without creating locality. It cannot produce a positive reading, because every outcome is measured on hard traces, but it can make the dose weaker than intended. Each cell therefore records, at the logged updates, the mean 8th–9th score gap and the mean π mass outside the top 8.

Known degenerate optimum, stated in advance: **every query selecting the same eight slots** minimizes R_temp and R_conc (not R_co alone). The language-model loss opposes it and the utilization and quality guards (§7) detect it. An outcome reached that way is classified COLLAPSED, not positive.

## 4. Training rule (matched pressure)

Per update, with L the P5 mean next-byte loss, R the case's regularizer, Θ_r = {keys, wq, and router if trainable}:

1. g_L = ∇L over all trainable addition parameters (one backward pass, exactly as P5).
2. For regularized cases, g_R = ∇R (second backward pass; nonzero only on Θ_r).
3. **λ = α · ‖g_L restricted to Θ_r‖₂ / ‖g_R‖₂**, α = 0.5, treated as a constant of the step (no gradient through λ). If ‖g_R‖₂ < 10⁻¹² or either norm is non-finite, λ = 0 and the event is counted.
4. g = g_L + λ g_R; then P5's clipping (total norm 1.0) and P5's AdamW (lr 0.003, betas (0.9, 0.999), eps 10⁻⁸, weight decay 0), one parameter group, unchanged.

So the raw gradient handed to the optimizer is that of L + λR with a step-wise coefficient that sets the regularizer's gradient norm on the routing parameters to half the language-model gradient's there.

**What this rule does and does not match (review M1).** AdamW normalizes every coordinate separately. On a coordinate where only the regularizer has gradient — in particular the key rows of slots that are soft-included but not hard-selected — the update is about the learning rate whatever λ is (measured: 3.00·10⁻³ at λ = 1 and 0.1, 2.97·10⁻³ at 0.01). α therefore sets the *mixture* on coordinates that both objectives touch and does **not** bound the regularizer's movement of the others. In C01–C03 unselected keys never move; in regularized cases they do. The rule equalizes the raw-gradient mixture across cases and architectures; it does not equalize parameter movement, and "matched" means the first only. Each cell logs, per update, the norm of the actual parameter change on Θ_r and on the remaining parameters, so movement can be compared with the baseline case. P5's clipping never activated (largest pre-clip norm 0.081) and λ is bounded, so neither is a concern.

Reason for this rule over a fixed coefficient: the memory's whole contribution in P5 is about 0.02 nats/byte and the raw gradient scales of the three regularizers and two architectures (4,096 versus 512 candidates) differ by unknown factors; a fixed coefficient would give unmatched, unknowable pressure, and tuning one on outcomes is forbidden. α is a single registered dose, chosen before any P8 model exists. **A null result at α = 0.5 does not rule out an effect at another dose** (§9).

C10 applies R_co and R_temp together, each normalized separately by rule 3 with α = 0.5: g = g_L + λ_co g_co + λ_temp g_temp. Its raw regularizer gradient can be up to twice that of the single-objective cases (under AdamW this does not translate into twice the movement); it is exploratory.

Standard cases (C01–C03) take step 1 only and must be bit-identical to P5's `train_step`. Gate: the P8 runner, given P5's cell b101-o301 flat seed 501, reproduces P5's recorded step-512 state digest (§10).

## 5. Cases and matrix (human-fixed)

| Case | Architecture | Objective | Baseline for paired deltas | Flat counterpart |
|---|---|---|---|---|
| C01 | flat | L | — | — |
| C02 | fixed tree | L | — | C01 |
| C03 | learned tree | L | — | C01 |
| C04 | flat | L + R_conc | C01 | — |
| C05 | learned tree | L + R_conc | C03 | C04 |
| C06 | flat | L + R_co | C01 | — |
| C07 | learned tree | L + R_co | C03 | C06 |
| C08 | flat | L + R_temp | C01 | — |
| C09 | learned tree | L + R_temp | C03 | C08 |
| C10 | learned tree | L + R_co + R_temp | C03 | none (exploratory) |

Parents: **B101/O301, B102/O302, B103/O303** (the diagonal of P5's nine; fixed by the human lead, not chosen on performance). Initialization seeds **601, 602** (never used before; P5 used 501–503). 10 × 3 × 2 = **60 cells**. Each: 512 updates, batch 8, context 64, P5's exact training rows and parent order (two cycles of training ranks 0–2047 in the parent's order), fresh AdamW. Cell index = 20·(parent 0–2) + 10·(seed 0–1) + (case 0–9). Three parents and two seeds are a small exploratory pilot; cells sharing a parent are not independent, and no population-level significance is claimed.

## 6. Data

Pinned local WikiText-2 acquisition only (`data/wikitext2`, recorded hashes); no download.

- Training: P5's frozen training rows, ranks 0–2047.
- **Calibration** (layout fitting only): training-pool ranks 2048–2559, never trained on (as P7-A/B).
- **Panel A**: validation ranks 3072–3583. **Panel B**: validation ranks 3584–4095. Both by the existing rank/deduplication recipe.

Before the freeze, the implementer's reconstruction and the auditor's independent reconstruction must agree byte for byte, reproduce the recorded hashes of all six earlier panels (ranks 0–511 … 2560–3071) from the same file, and show zero exact-chunk overlap of each new panel with every earlier panel, each other, the calibration stream and the complete 4,096-chunk training candidate pool. If either window is unavailable, short or previously used, **the study stops**; no other window is substituted. Panel hashes are frozen before any P8 model is evaluated. Panel B is a same-corpus check, not an independent corpus. Nothing is adjusted after Panel A is observed: both panels are traced and simulated in one registered sequence and analysed together, once.

## 7. Measurements and criteria

### 7.1 Per cell, per panel

- **Quality.** NLL (nats/byte) at step 0 and step 512; with memory disabled; with values permuted (seed 80000 + cell index). Memory gain = NLL_disabled − NLL. Value-association effect = NLL_permuted − NLL.
- **Utilization** on the hard evaluation trace (32,768 queries × 8): distinct selected slots; entropy-effective slots N_eff = exp(H of selection counts); share of selections on the 64 most-selected slots; for trees, distinct branches visited, entropy-effective branches, share of the top branch.
- **Proxy diagnostics** (training, at updates 1, 128, 256, 384, 512): mean 8th–9th score gap; mean π mass outside the top 8; each R value; each λ; and, at every update, the norm of the parameter change on Θ_r and on the other parameters.
- **Per-context breadth** on the hard evaluation trace: mean number of distinct slots selected within a 64-query context (the cheapest minimizer of R_temp is one fixed set per context, which lowers this while N_eff can stay high).
- **Gradient reach** (training, at updates 1, 128, 256, 384, 512): number of slots whose key row has nonzero g_L; number with |g_R| row norm > 10⁻¹²; number of the latter not hard-selected in that batch; cumulative distinct slots hard-selected during training.
- **Locality (simulation, ADR-0014 page model unchanged):** per-query service, LRU among pages not used by the current query, warm-up on the first 256 contexts, counting on the last 256; **m = warm capacity misses per query**; also first-touch and cold (from-empty) misses and distinct pages per query. Settings: **primary R = 2 rows/page, C = 32 pages; confirmation R = 8, C = 8** (both hypothetical row sizes, both 64 cached rows). **Both eviction tie rules** (ascending, descending page number) on numerators and denominators.
- **Layouts**, all fitted on the cell's **calibration trace only** with ADR-0014's unchanged constructions and budgets: L-ID, L-FREQ, **L-COAX** (co-access clustering, no hierarchy information), L-BCOAX (trees), **L-PCOAX-1…5** (arbitrary 16×256 partitions, seeds 91601–91605).
- **Count-preserving null**: ADR-0013's construction on the panel's trace, three replicates, seeds 91331–91333 (Panel A) and 91341–91343 (Panel B), generator seed s·1000 + cell index; simulated under L-FREQ and L-COAX.
- **E(L) = m(actual, L) ÷ mean m(three nulls, L-FREQ)**, as ADR-0014 §2.
- **Temporal reuse** on the hard trace: fraction of a query's selected slots that were selected in the previous 8 queries of the same context (positions ≥ 1), for the actual trace and for each null replicate; their ratio. **Branch persistence** (trees): fraction of consecutive in-context query pairs with the same top branch, and with the same visited pair; against the same statistic on the order-shuffled trace (seed 91201 construction).
- **Engineering**: optimizer parameter names and order; backbone digest before and after; state digests at steps 0, 256, 512; checkpoint restore-and-compare at step 256 (restored run reaches the identical step-512 digest) for the registered subset of §10; λ statistics; wall time; peak RSS.

L-NCOAX, the windowed and greedy-only sensitivity layouts, R ∉ {2, 8}, C sweeps and the key-index path are **not run** in P8 (time bound). P7-B's flagged L-NCOAX defect (confirmation setting: 1.036–1.060 against a 0.97–1.03 band) therefore still qualifies every co-access number at the confirmation setting.

### 7.2 Paired quantities

For a regularized case c with baseline b (§5), over the six (parent, seed) pairs, for each panel, setting and tie rule:

- **M-ratio** = (mean over the six case cells of m(L-COAX)) ÷ (mean over the six baseline cells of m(L-COAX)): what the layout-optimized memory pays. Ratios of means throughout, never means of ratios.
- **E-ratio** = (mean of the six case cells' E(L-COAX)) ÷ (mean of the six baseline cells' E(L-COAX)): locality beyond each checkpoint's own popularity null. **E of a checkpoint is undefined when its null mean under L-FREQ is below 0.05 misses per query** (its selections essentially fit in the cache); an E-ratio with any undefined member is undefined.
- **Utilization-adjusted E-ratio**: ADR-0014 §2's regression on the 12 checkpoints, E = a + b·x + d·[case], x = ln N_eff on that panel; ρ_adj = (a + b·x̄ + d) ÷ (a + b·x̄), refitted for every panel × setting × tie rule; undefined if a + b·x̄ ≤ 0, if any E is undefined, or if the case's and the baseline's ranges of x do not overlap (the fit would then be pure extrapolation).
- **Gain retention** = mean memory gain of the case ÷ mean memory gain of the baseline; **association retention** likewise for the value-association effect. Each is **undefined when the baseline mean is ≤ 0**, and an undefined retention fails the quality guard (revision 3).
- **ΔNLL** = mean over pairs of NLL_c − NLL_b.
- **U-ratio** = geometric mean over pairs of N_eff,c ÷ N_eff,b.
- Pair counts: number of the six pairs with m_c < m_b and with E_c < E_b (L-COAX); **parent count**: number of the three parents for which (mean of the case's two seeds' E(L-COAX)) ÷ (mean of the baseline's two seeds' E(L-COAX)) is below 1.

For tree cases the same quantities are also computed **against the flat counterpart** (C05↔C04, C07↔C06, C09↔C08; C10 against C06 and C08 separately, descriptive only), and for every case against **C01 under L-COAX** (the well-optimized conventionally trained flat memory). For trees, every quantity is reported under L-COAX and under L-BCOAX; classification uses L-COAX for all architectures (one algorithm, no hierarchy information, no choice among layouts).

### 7.3 Screening margins (fixed; reference margins from ADR-0013/0014, not significance tests)

- Ratio ≤ **0.80**: material improvement. Ratio in **[0.90, 1.10]**: no difference. Ratio ≥ 1.25: materially worse. Otherwise intermediate.
- **Quality guard** (all four): ΔNLL ≤ **+0.005 nats/byte** (P5's registered effect threshold) on the mean; at most one of six pairs above +0.005; **gain retention ≥ 0.75**; **association retention ≥ 0.75**. (The backbone is frozen, so ΔNLL equals the baseline's gain minus the case's; +0.005 is about a quarter of the roughly 0.02 nats/byte being trained, which is why retention is stated beside it.)
- **Utilization guard**: U-ratio ≥ 0.80 → retained; 0.50 ≤ U-ratio < 0.80 → reduced; < 0.50 → collapsed.

### 7.4 Classification of each regularized case (per panel; evaluated in this order)

1. **QUALITY-FAILED** if the quality guard fails.
2. **COLLAPSED** if U-ratio < 0.50.
3. Let **LOC** hold if, at **both** settings under **both** tie rules: M-ratio ≤ 0.80 **and** E-ratio ≤ 0.80 **and** utilization-adjusted E-ratio ≤ 0.80 (an undefined ratio fails), **and** at least five of six pairs have E_c < E_b and the parent count is three. **LOCALITY-POSITIVE (screening)** if LOC and U-ratio ≥ 0.80.
4. **LOCALITY WITH REDUCED UTILIZATION** if LOC and 0.50 ≤ U-ratio < 0.80. This is not a positive reading.
5. **CONCENTRATION-ONLY** if M-ratio ≤ 0.80 at both settings under both tie rules but LOC fails.
6. **NO DIFFERENCE** if M-ratio and E-ratio are both defined and within [0.90, 1.10] at both settings under both tie rules.
7. **WORSE** if M-ratio ≥ 1.25 or E-ratio ≥ 1.25, the same one at both settings under both tie rules.
8. Otherwise **INTERMEDIATE** (including any disagreement between tie rules or settings, any undefined ratio not covered above, and LOC with an undefined U-ratio).

A case's **study classification** is its Panel A class if Panel B gives the same class; otherwise **NOT REPLICATED ACROSS PANELS** with both shown.

**Beats optimized flat** (required for a positive reading, §8): the case is LOCALITY-POSITIVE and its M-ratio, E-ratio and utilization-adjusted E-ratio **against C01 under L-COAX** are all ≤ 0.80 (defined) at both settings, both tie rules, both panels, with ΔNLL against C01 ≤ +0.005. For a tree case, **architecture advantage** additionally requires the same three ratios against its flat counterpart ≤ 0.80 under the same conditions, with ΔNLL against the counterpart ≤ +0.005. The U-ratio against C01 and against the counterpart is reported beside these but is not a condition: P5's trees already use fewer slots than flat, so such a condition could not be met by any tree; the E-ratio and its utilization adjustment carry the concentration control there. C10 has no flat counterpart and cannot establish an architecture advantage.

**Concentration controls bind (review M4).** If C04 or C05 is itself LOCALITY-POSITIVE on either panel, the criteria have been shown to pass on concentration alone: no "beyond concentration" statement may then be written for any case, and the decision memo defaults to (c).

**Arbitrary-partition control** (reported, enters no class): for each case, mean m under the five L-PCOAX layouts ÷ m under L-COAX, and for trees L-BCOAX ÷ mean L-PCOAX.

**Trained-in layout** (reported, enters no class): m under L-ID ÷ m under L-COAX for C06, C07, C10, whose objective refers to slot-ID groups; a value near or below 1 means the trained grouping is itself a usable layout.

## 8. Permitted interpretations and decision map (fixed before observation)

- "Locality-aware training produced locality beyond concentration **in simulation at this scale**" may be written only for a case that is LOCALITY-POSITIVE on both panels and beats optimized flat.
- "The learned tree benefits more than flat" may be written only with an architecture advantage as defined above.
- If only C04/C05-like behaviour appears (M falls, E does not), the finding is concentration, as P7-A.
- Decision memo options: **(a) proceed toward learned topology** — requires at least one of C07, C09 with an architecture advantage; **(b) reconsider hierarchy, keep locality-aware training on flat memory** — a flat case (C06 or C08) is LOCALITY-POSITIVE on both panels and beats optimized flat, and no tree case has an architecture advantage; **(c) stop or redesign this line at this scale** — no locality case is LOCALITY-POSITIVE. Evaluated mechanically in that order: (a) if its condition holds and the concentration controls do not bind; else (b) likewise; else (c). Cases that are INTERMEDIATE or not replicated across panels are listed as open questions beside the outcome; they do not by themselves void (a) or (b), and when neither condition holds the outcome is (c). The choice remains the human lead's.
- Never claimable from P8: physical I/O, latency, throughput, SSD viability (H4), capacity scaling (H5), independent-corpus replication, statistical significance.

## 9. What could mislead, stated in advance

- **One dose.** α = 0.5, β = 0.25, group size 8 and W = 8 are single registered values. Too weak gives an uninformative null; too strong fails the quality guard. Either is reported as the outcome of this dose, not of the idea.
- **Proxy versus measure.** The regularizers act on a soft relaxation with a slot-ID grouping; the outcome is measured on hard traces under post-hoc layouts. The proxy falling during training is not a result.
- **Utilization.** E's normalization does not fully remove utilization (ADR-0014 §2); hence the adjusted ratio, the U-ratio and the concentration controls. With 12 points the adjustment is itself noisy.
- **A tree may be unable to reach "beats optimized flat".** The utilization-adjusted ratio is undefined when the two groups' utilization ranges do not overlap; on P5's checkpoints trees and flat overlap by only about 0.27 nats of ln N_eff. The condition is kept strict: an undefined adjustment fails, so option (a) can be missed for this reason alone. That is the conservative direction and is reported if it occurs.
- **Tree prior.** A learned tree can also widen its selection margin through the route prior, a route flat memory lacks; an apparent architecture difference in proxy values could come from that. Outcomes are read on hard traces only.
- **Unselected keys move.** Under AdamW the regularizers move keys that the standard objective never touches (§4). Any difference from the baseline may come from that movement as such; the concentration controls share it.
- **Layout heuristic.** One greedy pass and bounded refinement; P7-B's L-NCOAX flag stands.
- **Hypothetical row sizes, one memory size, one corpus, 512 updates, three correlated parents, two seeds.**
- **Extra compute.** Regularized cases take two backward passes; equal updates, not equal compute. Reported.
- **Same-family review.** Lead, auditor, implementer and clerk are all Claude models.

## 10. Correctness requirements (all must pass before the freeze or, where marked, at run time)

1. **Gradients.** Each regularizer, as a function of float64 scores on small synthetic instances away from ties, passes `torch.autograd.gradcheck`; analytic gradient with respect to values, `wo` and gate is exactly zero through the real model; gradient reaches keys, `wq` and (learned tree) router.
2. **Proxy properties.** Exactly eight slots have π > ½ for random untied scores, and exactly seven (two at π = ½) when the 8th and 9th scores are tied; π is zero outside the top 64; R_co equals the closed form (1 − (1 − p)⁸)/(8p) on a constructed one-group selection and is near 1 on a constructed eight-group selection; R_temp ≈ 0 on a constructed fully repeating sequence and ≈ 1 on a never-repeating one; R_conc ordering on constructed concentrated versus uniform usage and floor 0.25.
3. **Invariance.** Standard-objective path reproduces P5: recorded step-512 state digest of P5 cell b101-o301 flat seed 501 (training only; no evaluation panel is opened). A regularized step whose λ is 0 skips the addition (0·∞ would be NaN) and is then bit-identical to the standard path.
4. **Freeze of the backbone.** Backbone digest identical before and after every cell (run time); optimizer holds exactly the addition parameters in registered order (run time, every step, as P5).
5. **Checkpoint restoration.** Save at step 256 including optimizer state; a restored run reaches the identical step-512 digest. Tested pre-freeze on synthetic parents and at run time on cells with seed 601 of parent B101/O301 (ten cells).
6. **Data identity.** §6 double reconstruction and overlap proof; training rows and order equal P5's by hash.
7. **Simulation.** P8 calls ADR-0014's unchanged layout and simulation functions; on one P5 checkpoint's existing calibration and stream-A traces the P8 pipeline reproduces P7-B's recorded m for L-FREQ and L-COAX at both settings and both tie rules.
8. **Rehearsal.** A full-size synthetic rehearsal (real dimensions, synthetic parent and synthetic bytes, every case, every stage) projects each stage at no more than half its cap (§11).
9. **Determinism.** Single intra-op thread, deterministic algorithms, as P5; a repeated cell gives the identical digest.

## 11. Resource limits and stop conditions

CPU only, local machine (Apple M5 Max, 18 cores, 48 GiB). Up to four training workers in parallel, each single-threaded.

| Stage | Cap (active wall) |
|---|---:|
| Panel proof | 600 s |
| Training, 60 cells | 5,400 s total; 600 s per cell |
| Evaluation, interventions and traces | 1,800 s |
| Layouts and simulation, both panels | 5,400 s |
| Analysis | 600 s |
| Auditor's independent checks (outside the study budget) | 3,600 s |

Human-set ceilings: **8 h total active wall time for the overnight study; 2 GiB RSS per scientific worker; 8 GiB aggregate process-tree RSS;** no cloud, paid service, download, SSD experiment or capacity change. RSS is sampled by the existing watchdog.

Stop (and write a blocker report, never substitute) on: panel unavailable or not provably unused; identity or hash mismatch; failed gate in §10; unresolved audit blocker; backbone digest change; non-finite loss or parameter; cap or RSS breach. A cell that fails at run time is kept as a failed record; the study is then **INCOMPLETE** and is reported as such with the denominator unchanged at 60. No cell is rerun with a changed seed, dose or rule.

## 12. Process and audit

Draft (this document) → auditor (Opus 5.5) spec review of formulas, denominators, guards, null adjustment and degenerate optima → lead's response and revision → implementation by the implementer (Sonnet 5.5) in **new files only** (`src/arborlm/p8_*.py`, `tests/test_p8_*.py`, `configs/p8_locality_training.toml`) → auditor pre-freeze implementation audit with its own gradient check and panel reconstruction → fixes → rehearsal → **freeze commit** (source, config, spec and panel hashes) → single registered sequence: panel proof → train 60 cells → evaluate, intervene and trace (calibration, Panel A, Panel B) → layouts from calibration → simulate both panels → analyse both, once → auditor's independent recomputation of every registered quantity from raw records without importing the implementation's analysis → lead's review. Evidence inventory by the clerk (Haiku 5.5). The model that actually ran each delegation is recorded in the review's DELEGATION.md.

No analysis output of any kind is produced before both panels are simulated. No P8 checkpoint is evaluated on either panel before the freeze.

## 13. Independent review of assumptions and the lead's response

Revision 1 was reviewed by the auditor role (Claude Opus 5.5, `claude-opus-5-5`): `docs/reviews/p8-spec-review-2026-11-14/REVIEW.md`. Verdict NOT READY: 1 blocker, 6 major, 10 minor, all answerable by rewording; nothing conflicted with the human direction. No P8 model existed and no panel had been opened. The lead's response, applied in revision 2:

| Finding | Response |
|---|---|
| **B1** Three statements in §3 were false (tie case; R_co's minimum is reached only by sharpening; all three regularizers fall under margin widening) and two were gates. | Adopted. §3 corrected; the margin route is declared as a known non-locality route with per-cell diagnostics; §10.2 replaced by the tie test and the closed form. |
| **M1** Matched pressure does not survive AdamW's per-coordinate normalization. | Adopted as a correction of the claim, not of the optimizer (P5's optimizer is part of the human-fixed setup). §4 now says what is and is not matched; per-update parameter-change norms are logged. |
| **M2** The quality guard allowed losing a quarter of the memory gain; R_temp's cheapest minimizer may escape N_eff. | Adopted: gain and association retention ≥ 0.75 added to the guard; per-context breadth reported. |
| **M3** Utilization was not enforced on positive readings. | Adopted for the case-versus-baseline reading: LOCALITY-POSITIVE needs U-ratio ≥ 0.80; a separate non-positive class covers 0.50–0.80. Against C01 and the flat counterpart, E-ratio and adjusted E-ratio are now required. **Not adopted:** a U-ratio ≥ 0.80 condition against flat, because no tree could ever meet it (a criterion that cannot pass); it is reported instead. |
| **M4** The concentration controls fed no criterion. | Adopted (§7.4). |
| **M5** Undefined denominators and ambiguities. | Adopted: E undefined below 0.05 null misses per query; undefined fails LOC; parent ratio named; ratios of means; refit per panel × setting × tie; WORSE covers M-ratio. |
| **M6** "Same formula" was not matched between flat and tree. | Adopted: π over each query's top-64 candidates for both architectures. The remaining asymmetry (the tree's prior gives a second way to widen the margin) is disclosed in §9. |
| Minors | Adopted: −softplus in place of the clamp; λ = 0 skips the addition; C10 wording; R_conc floor; tree π discontinuity stated. The saturation of the gradient-reach count is reduced by the top-64 restriction and the metric is kept as descriptive. |

Every change was made before any P8 model existed. None changes the matrix, panels, margins or limits set by the human lead.

**Pre-freeze implementation audits (revision 3).** The auditor role audited the implementation in two parts: `docs/reviews/p8-preflight-2026-11-14/AUDIT_TRAINING.md` (READY TO FREEZE; 0 blocker, 2 major, 6 minor) and `AUDIT_EVAL_SIM_ANALYSIS.md` (FIX REQUIRED; 0 blocker, 2 major, 7 minor). Its own reference implementation of the regularizers and the training rule agreed with the implementation to rounding (float64 gradients within 2.2·10⁻¹⁶; finite differences within 5.6·10⁻¹⁰), and its own recomputation tool agreed with the implementation's analysis on synthetic dry-run records with zero differences. Decisions: registered constants added to the bound config and the unsourced `gain_min` removed; the run-time restore gate made a registered step (`restore-gate`); evaluation, simulation and analysis bound to the freeze commit; retention undefined for a non-positive baseline (the one change of rule, made because a negative baseline flipped the ratio's sign on a constructed fixture; no real record existed); LOC with undefined U-ratio is INTERMEDIATE; the decision map stated mechanically (§8). One minor is **not fixed** and stands as a known defect: the logged reason for a λ = 0 event can be mislabelled (label only; fixing it would have changed the audited objective module). Interpretations of the implementer accepted by the auditor and adopted: branch utilization counts both visited branches with top-branch figures beside it; L-BCOAX comparisons against a flat reference use flat's L-COAX; the LOC clauses apply at each of the four setting × tie conditions.

## 14. Decisions reserved for the human lead

Anything beyond this pilot: a second dose, a larger model, learned topology, SSD work, capacity scaling, merging the P8 pull request, publication, and the standing governance decision (ADR-0012).

## 15. Record of human direction

On 2026-11-13 (America/Panama) the human research lead issued a written overnight direction, received in the lead's session, which is the authorization for this study. Quoted:

- "Consolidate the completed research, then autonomously conduct one bounded experiment investigating locality-aware neural memory training." "You are authorized to carry out the specifically defined work below without requesting routine confirmations, subject to the safety, scientific integrity, resource and stop conditions in this prompt."
- The ten cases (C01–C10 as in §5), parents "B101 / O301, B102 / O302, B103 / O303", "initialization seeds 601 and 602", "10 cases × 3 frozen parents × 2 initialization seeds = 60 matched training cells", "512 updates, identical approved training examples, matching order, and the established P5 model dimensions", "Freeze the backbone. Keep memory at 4,096 slots."
- "Panel A: 3072–3583; Panel B: 3584–4095." "If either window is unavailable or previously used, stop rather than silently choosing another."
- "Use the previously established 0.80 material-improvement threshold and 0.90–1.10 descriptive band as reference screening margins. For this small pilot, do not make population-level significance claims."
- "The experiment matrix and upper resource limits in this prompt are human-authorized. Fable may formalize reproducible implementation details before seeing outcomes, but may not change the scientific question, expand the experiment, or approve a material deviation."
- "ADR-0012 remains pending as a standing governance decision. This prompt authorizes the defined P8 pilot under a study-specific Claude workflow, not permanent governance changes." "Astra review must remain labelled NOT_PERFORMED unless actually performed."
- Hard limits: "Maximum eight hours total active wall time", "No cloud spending", "Maximum 2 GiB RSS per scientific worker and 8 GiB aggregate process-tree RSS", "No new corpus downloads. No SSD experiments. No memory-capacity expansion. No changing pretrained backbone parameters."
- "Push the work and open a new draft PR. Do not automatically merge the new experimental PR."
- "Do not start the next research phase, train a larger model, perform an SSD experiment or revise the architecture after completing P8."

Details the human direction left to the lead and fixed here before any P8 model exists: the soft-inclusion proxy and its constants (β, group size 8, W), the three regularizer formulas, the matched-pressure rule and α, the layouts retained from ADR-0014, the paired quantities, guards and classification of §7, the null seeds, and the stage caps.

## 16. Freeze record (before any P8 training cell, any panel evaluation and any simulation)

1. **Audits complete.** Spec review (`docs/reviews/p8-spec-review-2026-11-14/REVIEW.md`), training audit (`AUDIT_TRAINING.md`), evaluation/simulation/analysis audit (`AUDIT_EVAL_SIM_ANALYSIS.md`) and narrow re-check (`REAUDIT.md`: **READY TO FREEZE**, nothing blocking), all under `docs/reviews/p8-preflight-2026-11-14/` unless noted. The files the auditor examined are listed by hash in `outputs/reaudit_examined_hashes.txt`; the source files in this commit must equal them. This document differs from the examined copy only by the status line, one clause in §8 option (b) that the re-check asked for ("on both panels and beats optimized flat"), and this section.
2. **Panels.** Implementer's and auditor's reconstructions agree on 59 fields with no difference. Panel A bytes `448017f93b994167d898460b236ac1324e2b7cfcba5cb6df1380840bc7b97342`; Panel B bytes `1bd4b984c3f7a92882ba5f8b8383314fd2899f69539a3ef2e85e5b25d323607e`; registered record `results/p8-2026-11-14/panel/panel_record.json`, sha256 `2a767b5fceb4a8cf104443d21aed2fd128d0c7fd4542534477a97c3a5c5f586d`. All six earlier panel hashes reproduced; zero exact-chunk overlap with every earlier panel, each other, the calibration stream and the 4,096-chunk training pool; 16,407 eligible validation candidates. Disclosed, descriptive: both panels come from the same articles as earlier panels; one Panel B chunk also occurs inside a training-file row at an offset that is not a pool chunk (the chunks covering it are outside the training pool and the calibration stream).
3. **Gates passed before this commit.** Gradients and proxy properties (§10.1–2; auditor's independent reference agrees to rounding). P5 invariance (§10.3): the P8 standard path reproduces P5's b101-o301 flat seed-501 step-512 state bit for bit (digest `4e9bf5c194395544794401582ba3f979a8a98982ef3c5da8a13093a53a516515`), training rows only. Restore test on synthetic parents (§10.5). P7-B reproduction (§10.7) ALL_EQUAL on two P5 checkpoints, re-run by the auditor and shown non-vacuous; it is re-run on the frozen source before simulation. Rehearsals (§10.8), full size, synthetic: training projected 440 s of 5,400 s; evaluation 125–142 s of 1,800 s; simulation 115–137 s of 5,400 s; analysis 0.2 s of 600 s; peak worker RSS 0.87 GB of 2 GiB; aggregate 2.5 GB of 8 GiB. Every stage is under half its cap. Repository checks: ruff and mypy clean, 798 tests passed, 3 skipped (skips need local data).
4. **No outcome exists.** No P8 cell has been trained on a real parent except the P5-invariance replay (P5's own cell, training rows only). No model has been evaluated on, traced on or simulated on Panel A or Panel B by anyone. Real-data contact so far: training rows, published P5/P7 records and traces, and the raw validation file for the panel proof (no model).
5. **Known defects carried into the run, none affecting a registered number:** the logged reason for a λ = 0 event can be mislabelled; `restore-gate` does not itself re-verify the freeze; the evaluation worker hashes the panel record and then reads it (a negligible window); one test's environment-variable name is inconsistent.
6. **Registered sequence.** train (60 cells, 4 workers) → restore-gate (ten cells) → evaluate → P7-B reproduction on the frozen source → simulate → analyse (once) → auditor's independent recomputation with the tool fixed before the freeze (`independent_recompute_p8.py`, sha256 `dc3e7269976b6fdcb8accf5189ab5709f1db9b94bf03b73c3d274b655e6f1acb`) → report generation (`results/p8-2026-11-14/report/make_report.py`, analysis-only, written and tested on synthetic records before the freeze) → lead's review. A failed cell stops the launch of further cells; the study is then INCOMPLETE with denominator 60.
7. **This is the last edit to this document until the analysis stage has completed.** Every stage verifies `src/arborlm/`, the config, this specification, `uv.lock` and `pyproject.toml` against the freeze commit and refuses to run on any difference. Checkpoints and traces stay local and are not published.
8. **Delegations so far** (models from each session's own metadata): lead and orchestration Claude Fable 5.2; spec review, panel proof, both implementation audits and re-check Claude Opus 5.5 (auditor role); implementation of training, evaluation/simulation/analysis and report generator by the implementer role (Sonnet 5.5 per the agent definition); evidence inventory by the clerk role (Haiku 5.5 per the agent definition). Astra review: NOT_PERFORMED.

## 17. Outcome record (2026-11-14)

Added after the analysis stage completed. Nothing above this section was changed except the status line.

- **Run.** Freeze commit `80f46ae`. Training 60/60 cells (393 s); restore gate 10/10; evaluation 60/60 on both panels (106 s); P7-B reproduction on the frozen source ALL_EQUAL; simulation **55/60** (74 s); analysis once, in incomplete mode after the strict mode refused. Peak worker RSS 0.47 GiB; aggregate 1.93 GB.
- **Why five cells are missing.** Five concentration-control cells (C04: b101-o301 seeds 601 and 602; C05: b101-o301 seeds 601 and 602, b102-o302 seed 601) select the same eight slots on every query. ADR-0013's unchanged null generator cannot construct their (unique) count-preserving null and raised an invariant error. Nothing was repaired, rerun or substituted.
- **Registered classes.** C04 INCOMPLETE; C05 INCOMPLETE; C06 COLLAPSED (both panels); C07 CONCENTRATION-ONLY (both); C08 QUALITY-FAILED (both); C09 QUALITY-FAILED on Panel A and COLLAPSED on Panel B, hence NOT REPLICATED ACROSS PANELS; C10 QUALITY-FAILED (both). No case is LOCALITY-POSITIVE; none beats optimized flat; no architecture advantage. Decision-map output: "none" (incomplete study).
- **What the numbers say.** Every regularizer reduced the slots in use by 46–92% (U-ratio 0.08–0.54). Simulated misses fell to 14–19% of baseline (co-access) or to zero (temporal), and the count-preserving null fell with them, so E and its utilization adjustment are undefined for every regularized case. Quality cost: +0.001 (C07) to +0.012 (C05) nats/byte.
- **Deviation.** The simulation stage continued launching cells after the first failure, contrary to the wording of §16 item 6 (written with the training stage in mind; §11 does not require stopping). The records are kept; acceptance of the C06–C10 classes as registered is referred to the human lead.
- **Independent recomputation** (Opus 5.5, tools fixed before the freeze, run unchanged): 1,232 analysis values and 2,032 trace statistics, zero differences; all records carry the frozen source and spec hashes; committed records byte-identical to the local run. `docs/reviews/p8-results-audit-2026-11-14/RESULTS_AUDIT.md`.
- **Review, defects and decision memo:** `docs/reviews/p8-results-2026-11-14/README.md`. Report and figures: `results/p8-2026-11-14/report/`.
- H3 was tested at one dose and not supported. H4 and H5 remain untested. P1–P7-B outcomes are unchanged. Astra review: NOT_PERFORMED. No merge of the P8 pull request, no publication, no further training, no SSD work.
