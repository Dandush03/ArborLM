# M0 stage I0-a: independent audit (known-truth gate, implementation, generators, rulings, design options)

- Auditor: `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`), fresh context; it wrote none of ADR-0033's wording, none of Reviews 1 to 3 and none of the code audited. Date 2026-11-20 (Panama).
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, commits 8230033, 8178aa0, 145e76b; ADR-0033 revision 4; ADR-0032 sections 4, 5, E2; rehearsal `experiments/M0-ggen-rehearsal-20261121/` (open pools and audit samples only; the sealed directory was not opened).
- This is a Claude audit. It is not Astra review (`Astra review: NOT_PERFORMED`) and not human approval. It approves nothing. Nothing here is a result about any model; no model was run.
- Environment: macOS arm64, `python3 -I` 3.15.1 (standard library only; nothing imported from `studies.m0`), every run `nice -n 10` under `timeout 590`, at most two processes at a time. Scripts and raw outputs: `experiments/_scratch/audits/m0_i0a_audit/` (SHA-256 of each script at the end).

## Verdict in one paragraph

Finding 1 (known-truth gate fails) is **VERIFIED** by independent code: S2, S3, S6 miss the 0.03 tolerance; S1 and S5 sit at the edge (between -0.019 and -0.031 across my two replicates), S4 passes. The cause is the truncated plug-in τ̂² (verified three ways). **But the implementer's claim that the bias is always conservative is wrong for the structure actually written**: at about 7 lineages in 6 families per part the section-9.4 procedure overstates power by +0.13 to +0.19, because single-lineage families make the stratum-centred deviations zero while the M5 test that would actually run (the fewer-than-30-clusters t branch) does not centre on strata. Finding 2 (lineage shortfall) is **VERIFIED** and is worse than stated: 6 to 10 lineages are written per part, and by my reading 4 to 8 distinct procedures per part, some duplicated across parts A and B. One BLOCKING code defect was found (`analyse_part` passes the per-part m, not M_e, to `required_size`: sizes computed at a per-test target of 0.96 instead of 0.99636). One generator lineage (`R1.categories_follow`) has a systematic answer-key ambiguity in 236 of 500 development items.

## A1. Known-truth recomputation (section 9.4, gate 2)

Truth model and scenarios re-written from `shrink_check3c.py` (read, not imported) and the config's `[knowntruth]`: G = 300, n = 6,000, one stratum. Known power: fresh clusters (cluster sums via two exact binomial draws), exact Student t quantile. Procedure: section 9.4 as worded (τ̂² = max(0, V − s_w²·mean(1/m_g)); λ_g; stratum-centred shrunk deviations; pooled corrected residuals; no recentring of the sample; scaled by √(d/(d−μ²)); t on G_e − 1).

Commands: `python3 -I kt_run.py S2,S3 400 600 20000 953777 long_a.json`, `... S6,S1 ... long_b.json`, `... S4,S5 ... long_c.json` (replicate 1: 400 draws × 600 simulations, 20,000 truth runs); `python3 -I kt_run.py S1,S3,S5,S6 200 600 20000 953780 oracle.json oracle` (replicate 2 with the TRUE τ² plugged in on the same draws).

| | Implementer (400 draws × 1,000) known / recovered / diff | Auditor rep. 1 (400 × 600) known / recovered (se) / diff | Auditor rep. 2 (200 × 600) diff | Oracle (true τ²) diff | Gate at 0.03 (auditor) |
|---|---|---|---|---|---|
| S1 | 0.831 / 0.812 / −0.020 | 0.837 / 0.817 (0.003) / −0.020 | −0.028 | −0.002 | pass, at the edge |
| S2 | 0.817 / 0.766 / −0.051 | 0.819 / 0.777 (0.003) / −0.042 | — | (τ = 0: trivial) | **FAIL** |
| S3 | 0.833 / 0.780 / −0.052 | 0.836 / 0.777 (0.008) / −0.060 | −0.061 | −0.009 | **FAIL** |
| S4 | 0.682 / 0.656 / −0.026 | 0.676 / 0.664 (0.005) / −0.012 | — | — | pass |
| S5 | 0.830 / 0.807 / −0.023 | 0.836 / 0.805 (0.003) / **−0.031** | −0.019 | +0.002 | **undecided** (straddles 0.03) |
| S6 | 0.817 / 0.717 / −0.099 | 0.812 / 0.723 (0.007) / −0.089 | −0.098 | −0.003 | **FAIL** |

- Agreement with the implementer: per-scenario differences 0.000, +0.009, −0.008, +0.014, −0.008, +0.010; the largest (S4) is 1.7 combined standard errors. **The two computations agree within Monte Carlo error.**
- Cause, shown three ways. (a) Oracle: with the true τ² the same procedure recovers within 0.01 in S1, S3, S5, S6. (b) τ̂² distribution (rep. 1): τ̂² = 0 in 52 % (S2), 49 % (S6), 48 % (S3), 33 % (S1) of draws; its 95th percentile is 0.0085 (S2), 0.0248 (S6), 0.0248 (S3) against true 0 / 0 / 0.0025; the untruncated estimator is unbiased (mean raw τ̂² −0.0003, +0.0008, +0.0020), so the bias is truncation plus noise at few items per cluster. (c) Items per cluster (`kt_explore.py mvary 150 600 20000 953782`, τ = 0, d = 0.3, δ = 0.0176): m = 2: −0.103; m = 5: −0.062; m = 10: −0.028; m = 20: −0.015. τ = 0.05: m = 2: −0.083; m = 20: −0.002.
- Power level (`kt_explore.py power 150 600 20000 953781`): at G = 300 the bias is ≈ 0 at low power (p 0.30: +0.003 ± 0.004; p 0.50: +0.005 ± 0.004) and conservative at the per-test target actually used, 0.99636 (τ = 0.05, m = 5: −0.006, i.e. a failure rate 0.009 instead of 0.003; τ = 0: −0.006). **A 0.03 tolerance at power 0.8 does not test the operating point**: at the target 0.99636 an error of 0.03 is a ninefold error in the failure probability. PENDING LEAD REVIEW.
- **Not always conservative.** `kt_strata.py 150 300 20000 953779`: the procedure as worded, with strata, at the written structure (7 lineages in 6 families, family sizes [2,1,1,1,1,1]; 10 lineages [2,2,2,2,1,1]), 1,500 M0 items, sealed n = 20,000, against the M5 test the code would run there (t branch, unstratified cluster-robust SE, df = G − 1):

| Structure | τ | δ | Known power (lineages random, the approved reading) | Recovered by 9.4 | Diff | Known power if the 7 lineages are fixed |
|---|---|---|---|---|---|---|
| G = 7, V on 1 df | 0 | 0.0108 | 0.791 | 0.707 | −0.084 | 0.794 |
| G = 7, V on 1 df | 0.05 | 0.0537 | 0.790 | **0.982** | **+0.192** | 0.937 |
| G = 10, V on 4 df | 0.05 | 0.0435 | 0.797 | **0.923** | **+0.126** | 0.965 |

Mechanism: x̄_h of a one-lineage family equals that lineage's mean, so its shrunk deviation is exactly 0; between-lineage variance is estimated from the one to four two-lineage families only; the simulated sample therefore has almost no between-lineage spread, but the M5 test that will be run includes it. Second, smaller mechanism: the finite set of deviations has population variance τ̂²·(G−1)/G, 14 % low at G = 7.

- Earlier statement in the review (Review 3) that S2 recovered 0.816: with 6 draws and mean τ̂ 0.0068 it was an unrepresentative sample (400 draws give mean τ̂ 0.033); I reproduce the implementer, not Review 3, on S2.

## A2. Implementation findings (power.py, stats.py, knowntruth.py, outcomes.py, tests)

BLOCKING

- **B1. Wrong conjunction size in the size search.** `outcomes.analyse_part` line 247 calls `pw.required_size(comp, dl, p.n_clusters_sealed, m_tests, ...)`; `required_size` uses its fourth argument as M_e (`target = 1 - (1 - power) / m_tests`). The caller passes the per-part m (5 in the test, `tests_total=55, m_tests=5`), so the required size is searched at per-test power 0.96 instead of 1 − 0.2/55 = 0.99636, while the floor check on line 244 uses `tests_total`. Sizes would be too small (anti-conservative) and UNDERPOWERED too rare. Fix: pass `tests_total`; add a test that asserts the target used. No test can currently catch it.
- **B2. The simulation does not simulate M5's test at the written structure.** With every private part at 6 to 10 clusters, `stats.interval` takes the t branch with the unstratified cluster-robust SE (ruling 8), but `power.components` centres deviations on stratum means and gives single-lineage strata zero deviation. Shown above: +0.13 to +0.19 overstatement. Section 9.4's text ("allocated to strata", "x̄_h") is the source; the code follows it. This is a specification defect as much as a code one: PENDING LEAD REVIEW for the wording; the code must not be used for any size at G < 30 until resolved.

REQUIRED

- **R1. Union gain on the t branch ignores the choice of the better teacher.** `stats.union_gain` linearises with the better teacher fixed at the point estimate. On the t branch (every private part) section 9.2's "including which teacher is the better one" is not met. A valid fix that needs no bootstrap: G_U = min(U − s₁, U − s₂), and min(L₁, L₂) of the two one-sided t bounds is a valid 95 % lower bound of the minimum (the bound for the true arg-min alone already holds with 95 %).
- **R2. Known-truth gate operating point.** The gate tests power 0.8; sizes are chosen at 0.996 to 0.997 (above). PENDING LEAD REVIEW: either gate at the target power with a tolerance on the failure probability (for example a ratio), or justify 0.8.
- **R3. Strict xfail can hide a crash.** `test_short_known_truth_s6` is `xfail(strict=True)` without `raises=AssertionError`; any exception (a refactor's TypeError) also counts as the expected failure. Add `raises=AssertionError`. Beyond that, the strict xfail is an honest tripwire, but it makes `pytest` green while the registered gate is failed; the freeze must read the long profile's verdict, not the suite.
- **R4. Short test S3 is misleading.** `test_short_known_truth_passes_in_balanced_and_unbalanced_scenarios` asserts PASS for S3 at tolerance 0.06; S3 FAILS the registered 0.03 (−0.052 / −0.060). The module docstring says the short version does not cover 0.03, which is honest; the test name and its S3 case are not. Rename and add S3 to the expected failures at 0.03 or drop it from the "passes" test.
- **R5. Oracle test covers only τ = 0.** `test_the_machinery_recovers_the_known_power_when_the_true_tau_is_plugged_in` uses S2 and S6 (τ = 0), where λ = 0 and the shrinkage path is not exercised. Add a τ > 0 scenario (S1 or S3; my oracle: −0.002, −0.009).
- **R6. Second solvers.** Section 6.2 requires the second solvers to be written by an auditor context and audited by another; they were written by the implementer (ruling 3). Solver agreement also cannot catch wording ambiguity (A3, `categories_follow`: both solvers agree on all 500 items, and 236 are ambiguous).
- **R7. Config file name** departs from section 13 (`m0_references.toml` vs `m0_reference_models.toml`); see ruling 1.

RECOMMENDED

- **C1.** `stats.t_quantile` docstring says the Cornish-Fisher series is "conservative below" df 5; it is anti-conservative (smaller than exact): df 1: 5.572 vs 6.314; df 2: 2.885 vs 2.920; df 6: 1.94282 vs 1.94318. Negligible at df ≥ 5, which is where it runs (G 6 to 10), but use the exact quantile (incomplete beta; 30 lines) since the t branch is now the operative branch. The test checks df 10 only.
- **C2.** "A stratum with no residuals keeps zero noise" (ruling 9) is the most favourable reading, not the least; fall back to the residuals pooled over strata.
- **C3.** Weak tests: `test_tau_correction_and_shrinkage_formula` checks nothing when τ̂² = 0 and otherwise re-implements the formula; `test_required_size_walks_the_ladder...` asserts `n is None or n in (500, 1000)` for the easy case (cannot fail); `test_tau_interval_and_confirmation_run_and_are_ordered` asserts only `lo <= hi`, `0 <= p <= 1` (does not check point inside [lo, hi] or any value).
- **C4.** `Table.cluster_table` keys clusters by id only; the same id in two strata would be merged silently. Lineage ids are globally unique today; assert it.
- **C5.** The capacity-gate reading "found within 3× the need" proves capacity when it succeeds, but a failure means "not shown", not "cannot"; word the record so.

## A3. Generator spot audit (rehearsal, open files only)

Sample: `gen_sample.py` (seed string `m0-i0a-audit`), 20 development items for each of 12 lineages (240 items, `sample240.jsonl`). Answers re-derived **from the question text**, not the structured form, by my own solvers (`check_r1.py`, `check_other.py`); C1 programs run each in a fresh `python3 -I` process after a refusal scan. Then extended to every open development item of those lineages.

| Lineage | Sample 20 | All open development items | Notes |
|---|---|---|---|
| R1.knights_knaves | 20 agree | 571 / 571 | unique solution for the queried person in every item |
| R1.seating_row | 20 agree | 571 / 571 | unique answer in every item |
| R1.categories_follow | 20 agree (modern reading) | 500 / 500 agree under the modern reading; **236 / 500 change under the existential-import reading** (178 "cannot be determined" → "no", 58 → "yes") | **ambiguous**; also 80 % of keys are "cannot be determined" (402/500): a constant guess scores 0.80 while the chance level c of section 10.2 counts 1/3 |
| R2.to_base / permutation_power / string_rewrite | 20 / 20 / 20 | 400 / 667 / 666 | 97 string_rewrite items contain an identity step ("replace 'b' with 'b'") |
| M1.linear_equation / percent_change / clock_duration | 20 / 20 / 20 | 500 / 500 / 500 | percent answers are exact to 2 decimals; cosmetic grammar ("1 hours", "9 compasss") elsewhere in M1 |
| C1.func_compose / string_methods / bubble_pass | 20 / 20 / 20 | 572 / 571 (part A) | every program printed exactly one line |

`categories_follow` example: "All benax are kotok. … Does it follow that no kotok is a benax?" Key: "cannot be determined" (benax may be empty). A reader with existential import answers "no". The prompt states no convention. REQUIRED: state the convention in the item ("a category may have no members") or exclude conclusions that need it; whichever, a hand-labelled ambiguity check.

Other closed-answer lineages are balanced (compass, knights, conditional_chain, kinship_cousins, order_compare, road_reachability, palindrome, K0 within 0.23 to 0.54 per answer).

**Distinct lineages, my judgement** (one level-3 example of every lineage read, plus the 240 items; the ADR's 50-pair within-family check is the formal one and is still owed):

| Part | Written | Distinct procedures (central, range) | Same-procedure pairs I would merge |
|---|---|---|---|
| R1/A | 7 | 5 (5–6) | pet_owners = seating_row (permutation assignment); knights_knaves ≈ one_culprit (enumerate hypotheses, check statement truth) |
| R1/B | 8 | 5 (4–7) | order_compare = road_reachability (directed reachability, different families); order_extreme, categories_follow close to them; kinship_ancestor ≈ kinship_cousins |
| R2/A | 10 | 7 (6–8) | kth_smallest = sort_list; from_base ≈ to_base; count_divisible ≈ count_letter ≈ multiples_between |
| R2/B | 6 | 5 (5–6) | list_ops ≈ stack_machine (container simulation) |
| M1/A | 8 | 5 (4–6) | percent_change = fraction_remainder ≈ tip_split (chained factors); ages ≈ coins (one linear equation) |
| M1/B | 8 | 6 (5–7) | consecutive = linear_equation (≈ rectangle) |
| C1/A | 7 | 6 (5–7) | func_branch ≈ func_compose |
| C1/B | 7 | 6 (5–7) | list_build ≈ counter_list |

Two further points. (1) Several merges cross families, which the ADR's check (pairs within one family) would not find; RECOMMENDED: pair the check across families within a part. (2) Some procedures appear in both parts (M1: ages/coins in A, linear_equation/consecutive in B; C1: loops and list tracing in both), so part B is not held out at the level of procedure. PENDING LEAD REVIEW.

## A4. The 14 rulings

1. Config name: use the ADR's `configs/m0_reference_models.toml` (section 13 freezes that path; the approved specification ranks above a brief), or record an amendment.
2. Capacity: keep the worst case (whole pool on one level); also print the five-level figure; record a failure to exhibit as "not shown".
3. Second solvers: not acceptable as the gate requires; a separate auditor context writes them and another audits the pair (section 6.2). Until then solver agreement is implementer self-consistency.
4. C1: one fresh restricted process per program, twice, as specified; cost about 50,000 programs × 2 × ~20 ms ≈ 35 min. Batching needs a recorded amendment.
5. Odd family counts: accept (smaller half to A), registered before the partition seed is used.
6. 13-grams: accept; the n-gram length is the specification's; HMAC full length is fine.
7. Answer grammar: accept as a registered rule, but stripping a leading currency sign and a unit word listed per evaluation is a scientific choice (it moves format failures, unevenly across model sizes): PENDING LEAD REVIEW. Whatever is chosen is tested on the hand labels.
8. Percentile index floor(p(B+1)): accept. t branch, unstratified SE, df = clusters − 1: accept as conservative for the mean difference; **replace the union-gain linearisation by min(L₁, L₂)** (R1).
9. Pooled V, single-cluster strata contribute nothing: this is the mechanism of B2; at G < 30 the simulation must centre as the M5 test does. Zero noise for a residual-less stratum: replace by the pooled residuals (C2).
10. 400 draws, 1,000 simulations, 20,000 truth runs: adequate for the 0.01 bound (my standard errors 0.003 to 0.008 with 600 simulations), but see R2 on the operating point.
11. m = Tier 2 + NO HARM + interference, M = m·P: accept; fix B1.
12. K0 without A/B and not a gate candidate: accept (section 6.6 reserves it).
13. Uniform level mix in the rehearsal: accept as a placeholder; not of record.
14. Tuning draw 100 per level and part including reserve levels, balanced over lineages: accept.

## B. Design options for the human lead (PENDING LEAD REVIEW; the auditor chooses nothing)

Numbers: `python3 -I jobB.py` (output `jobB.out`), `kt_fixed.py 100 400 20000 953783`. Per-test target 1 − 0.2/M; one-sided α 0.05; d is the discordance; item variance ≤ d.

| Option | What is claimed | What is no longer claimed | Items per part (d = 0.3, M = 55; ladder value) δ 0.02 / 0.03 / 0.05 | Smallest δ reachable | τ needed? | Known-truth check |
|---|---|---|---|---|---|---|
| (i) Lineages fixed strata, items the unit | Non-inferiority on new items from this registered set of task families, weighted as registered | Anything about task families not in the set ("other templates of the same kind") | 14,055 (16,000) / 6,247 (8,000) / 2,249 (3,000); M = 70: 14,577 / 6,479 / 2,333; d = 0.4, M = 55: 18,740 (20,000) / 8,329 / 2,999 | 0.02 within the 20,000 pool up to d ≈ 0.42 | no | trivially passes: G = 7, diff +0.000 (p 0.80), −0.001 (p 0.9964); G = 10: +0.004 |
| (ii) Clusters kept, G ≈ 7–10 | The approved inference target | — | none reachable | at any n, t on G − 1 df: G = 7: 0.056 (τ 0.03), 0.094 (τ 0.05), 0.188 (τ 0.10); G = 10: 0.045 / 0.074 / 0.149. At n = 20,000 and τ = 0: 0.019 (G = 7) | yes, from 1 to 4 df | the procedure as worded is anti-conservative here (+0.13 to +0.19) |
| (iii) Public sets for breadth, private as contamination-free checks | Breadth where public sets are large | Mathematics and code tracing at δ ≤ 0.05 | — | MMLU-Pro 0.024; PopQA 0.022; L1 pooled 0.021 (clusters ignored); BBH 0.038; GSM8K 0.080; CRUXEval 0.103 | for clustered sets | — |
| (iv) Procedural family generator, G in the hundreds | Non-inferiority over shapes drawn from one registered meta-generator | Independence from the meta-generator's own design | as (i) plus a τ term | needs G ≥ 469 / 209 / 75 at τ 0.10 (δ 0.02 / 0.03 / 0.05); 118 / 53 / 19 at τ 0.05 | yes | as section 9.4, which needs the fixes above |
| (v) Hybrid: (i) gates; between-lineage spread printed and registered as descriptive | As (i), plus a visible heterogeneity record | As (i) | as (i) | as (i) | printed, enters no gate | as (i) |

Why (iv) is circular: shapes from one meta-generator are exchangeable by construction, so their between-shape variance measures the generator's own randomisation, not the variation across task families a person would write. Evidence that would be needed (agreement of the meta-generator's τ̂ with the spread across independently hand-written families) needs many hand-written families, which is the scarce resource. It is option (i) with a larger fixed population, relabelled.

The τ² problem, separately. (a) Upper confidence bound: conservative by construction, useless at the written structure: the 95 % upper bound of V is 254 × V on 1 df, 19.5 × on 2, 5.6 × on 4, 3.7 × on 6, 1.2 × on 299. (b) REML or a small-sample-corrected moment estimator: reduces but cannot remove the truncation bias at τ = 0 (any non-negative estimator is biased up there), and does nothing about B2. (c) A design where τ does not enter: option (i)/(v).

**Recommendation (the auditor's; his decision):** (v): lineages as registered fixed strata (equal weights per lineage, the sealed split stratified exactly as registered), items the unit, the power simulated by stratified item resampling (shown to recover the known power within 0.004); between-lineage spread, per-lineage differences with intervals and τ̂ with its interval printed and registered as descriptive; part B kept as the only generalisation evidence and labelled "held-out registered families", with the cross-part procedure overlaps of A3 removed first. Cost in claim strength: PARITY on a private evaluation then means "on these registered families", not "on reasoning-of-this-kind"; generalisation to families nobody wrote is not claimed, and every line must say so. Gain: the sampling model is true by construction (items are random draws from a registered program), τ disappears, the known-truth gate becomes meaningful, and δ = 0.03 needs 6,247 to 8,329 items per part (d 0.3 to 0.4), δ = 0.02 needs 14,055 to 18,740, within the 20,000 pool.

Approved text it would amend (ADR-0032 section 5, "Statistics", approved under the delegation as rule 3 of E2):

> "The unit is the item; where items share a source (a problem with several tests, a passage with several questions, a template) the confidence bound is computed by a cluster bootstrap over sources with at least 10,000 resamples and a registered seed."

> "Clusters are items sharing a passage, template or problem; subjects or task names are strata (stratified resampling), not clusters."

and ADR-0033 section 6.2: "The cluster, for G and for every bootstrap, is the lineage." The amendment would read, in substance: for privately generated evaluations whose items are independent draws from a registered generator, the registered lineages are strata and the item is the resampling unit; the inference is conditional on the registered lineage set. Public sets keep clusters as now. Changing the approved rule is the human lead's decision alone.

## Failed and discarded attempts (kept)

- Replicate 1, attempt 1 (`kt_run.py ... 400 1000 ... oracle on`): killed by the auditor with `kill` after 3.5 min because I mis-estimated the per-simulation cost (1 ms from the smoke run; it was 0.3 ms) and expected it to exceed the 590 s cap. No output was written. Rerun as attempt 2 with 600 simulations and the oracle in a separate run.
- Smoke run `kt_run.py S1,S6 5 100 1000 1 smoke.json` (5 draws): S1 −0.011, S6 −0.111; not a result.
- `check_r1.py` first run stopped on an unparsed seating constraint ("sits somewhere between"); the parser was extended and rerun. No disagreement was hidden.
- My own discrepancies with the implementer are listed in A1 (all within 1.7 combined standard errors). S5 is undecided between us: −0.023 (implementer), −0.031 and −0.019 (mine).

## Files (SHA-256)

- `kt_lib.py` fee07a92be20999a52c53bfb31975bd2357f4aafcc8d3e6916f7c7f966ff5deb
- `kt_run.py` 54c0c1c3a4d68388b96a516512cddf11c7444f15f0ba4e6d2aacf928455eb134
- `kt_explore.py` 50b2e724a8ccb01ef0f5ba6d62700323f6c289e7ec63e37fd4cb1ff40b2827dc
- `kt_strata.py` b1a837a64dd42bb68a24feb09df90677cda783e41d5b43aa31864031962d55c9
- `kt_fixed.py` b001a7dd690b761090c2e0df07518da02bbcdb1f849bbfb04b244d8b2a6b0679
- `jobB.py` d9d55c755e7b099dd37df5e4ab09a149624c2e8538e4a94c078969ffab48ec01
- `gen_sample.py` 051fd20353815906ce0a65e1dec7ba0805d95687dbe4b4c8602e10769e41957a
- `check_r1.py` 665788361b420e892e7258db4b9e0ca81cd00e6007844bdea1cc0d27deb538df
- `check_other.py` e2012f5c7c7f449793fb5660f34d76e40f1aa8da2b257430a4d650418f3e9f63
- Outputs: `long_a/b/c.out|json`, `oracle.out|json`, `explore_power.*`, `explore_mvary.*`, `strata.*`, `fixed.*`, `jobB.out`, `sample240.jsonl`, `smoke.json`. Left for later deletion: `__pycache__/` (row added to `CLEANUP_LOG.md`).
