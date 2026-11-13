# P5 critical review — Claude workflow, 2026-11-13

- Reviewer: Claude Fable 5.2 (`claude-fable-5-2`), at the human research lead's request, under the workflow proposed in [ADR-0012](../../decisions/ADR-0012-claude-workflow-governance-amendment.md), which is **pending human approval**.
- Label: `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW`.
- Reviewed baseline: branch `codex/e0-reproducible-baseline` at `451c2dbf5ed15e65b77e110d3f7f967336caa97f` (matches the handoff; local and remote heads identical; no newer study present). This review lives on branch `claude/p5-review-p6-proposal`.
- This review changes no P5 file, threshold, outcome or label. **The registered P5 composite criterion FAILED and remains FAILED.** The earlier authorized review by root Codex stands as the historical record; this is an additional, later reading of the same evidence.
- Who did what, and how model identity was checked: [DELEGATION.md](DELEGATION.md).

## 1. Verdict

P5 is a carefully executed study whose numbers reproduce. Its published conclusions are supported by its records. What it supports is narrower than a casual reading suggests, in three ways this review adds:

1. The three memory architectures are not distinguishable from each other in quality at the registered resolution. Their mean NLLs differ by 0.0008–0.0014 nats/byte, while the registered effect margin is 0.005 and parents differ from each other by about 0.02.
2. The learned-router result tests a router that can barely learn. In this implementation the router receives gradient only through the branch prior, only for queries whose selected slots span both visited branches, and only on those two router rows. Nothing tells it which branches should have been visited. The failed R gate is solid evidence that *this* training signal does not help; it is weak evidence about learned routing in general.
3. The latency inversion is real, but the explanation P5 foregrounded (64× more key-normalization input) is a minor contributor. An exploratory operator profile puts normalization at about 14% of the tree path. Gathering raw keys, `topk`, and the batched product are each larger, and `topk` is 85% of the *flat* path. That last fact means removing the tree's avoidable overhead may bring it to parity with flat at 4,096 slots without making it faster.

Nothing in P5 demonstrates an SSD, physical-I/O, capacity-scaling or reasoning advantage, and nothing in this review does either.

## 2. Evidence: what the records establish

Each item is a measured or recorded fact, with the source that confirms it.

| # | Finding | Kind | Confirmed by |
|---|---|---|---|
| E1 | 117 quality cells and 36 timing workers all record `completed`; no cell failed or was rerun. | Recorded | Inventory (`inventory/`): 153/153 `outcome: completed`, 153/153 terminal `status: completed`. |
| E2 | Mean final NLL (nats/byte): frozen baseline 2.356630572; flat 2.333691890; fixed tree 2.334497243; learned tree 2.335080704; dense adapter 2.329312946. | Measured | Recomputed from per-cell records by the implementer (`figures/README.md`, all within 4e-10) and by the auditor (`audit/`). |
| E3 | All three memories reduce NLL relative to the frozen backbone in 27/27 cells, and shuffling values removes essentially all of the gain (shuffle penalty ≈ gain). Disabling the addition returns the baseline NLL exactly. | Measured | Same; fig. 3. |
| E4 | R = NLL(fixed) − NLL(learned): mean −0.000583461, SD 0.001871, positive in 10/27 cells and 3/9 parent means, no cell ≥ +0.005. Registered R gate: FAIL. | Measured | Same; fig. 2. |
| E5 | Both trees are within +0.005 of flat in 26/27 cells and 9/9 parent means (Q: PASS). Mean tree-minus-flat: +0.000805 fixed, +0.001389 learned. | Measured | Same. |
| E6 | Dense adapter has the lowest mean NLL; lower than flat in 25/27 pairs and than each tree in 27/27. Dense-reference criterion: FAIL for all three memories. | Measured | P5 review; auditor recomputation. |
| E7 | Per query the trees score 16 router rows and 512 keys against flat's 4,096 keys: 0.12890625× the score count. | Analytical, confirmed against operand traces | P5 artifact audit (648 traces). Not re-derived here. |
| E8 | On CPU at batch 8 × context 64, tree/flat latency ratios (geometric mean of 27 paired medians): addition 2.603 fixed / 2.598 learned; full forward 2.190 / 2.184; lookup only 2.697 / 2.695. At batch 1: addition 2.378 / 2.385; full forward 1.874 / 1.873. Every one of the 27 primary pairs is slower. L: FAIL, not inconclusive. | Measured | Recomputed (`figures/`); fig. 4, fig. 7. 4 of 612 timing records are flagged unusable, none in a primary decision scope. |
| E9 | Mean final unique selected slots: flat 428.6, fixed 383.4, learned 313.1 of 4,096. Effective slots (exp entropy): 132.3 / 96.2 / 83.0. Learned trees have fewer nonzero top-1 branches (10.85 vs 14.22 of 16). | Measured | Recomputed means (`figures/`); fig. 5. The entropy itself was taken from stored per-cell values, not re-derived from histograms in this review; P5's own utilization audit did re-derive it. |
| E10 | Everything stayed resident in RAM. No storage, I/O, FLOP, energy, cache or decode-throughput quantity was measured. | Recorded | ADR-0010 §6; P5 README. |

## 3. Evidence added by this review

| # | Finding | Kind and limits |
|---|---|---|
| N1 | **Architecture differences are small against the study's own yardsticks.** Flat/fixed/learned means span 0.00139 nats/byte. The registered margin is 0.005. The SD of the nine baselines is 0.0202 and of the 27 flat cells 0.0210, almost all of it between parents. Fixed tree beats flat in 12/27 cells, learned in 8/27. | Recomputed from records. Descriptive; cells are correlated, no inference. |
| N2 | **R depends on the backbone.** Mean R by backbone: B101 −0.001584 (2/9 positive), B102 +0.000578 (6/9 positive), B103 −0.000745 (2/9 positive). With three backbones this cannot be separated from chance. The overall mean is not driven by one outlier cell. | Recomputed; fig. 2. |
| N3 | **Router gradient support.** With float64 synthetic tensors, for queries whose eight selected slots lie in one branch the router gradient is zero to rounding (ratio to key gradient ≤ 5e-16); for the rest, only the two visited router rows receive gradient (unvisited/visited ≤ 2e-15). The reason is algebraic: the prior is added to scores that then pass through a softmax over the eight selected slots, so a prior common to all eight cancels, and for two branches only the difference of their route scores survives. | Synthetic check, `lead-checks/router_gradient_support.py`; mathematical argument reviewed independently in `audit/AUDIT.md`. Not measured on P5 checkpoints. |
| N4 | **P5's "positive router-gradient norm in all 512 updates" is uninformative** about useful learning. In float32 the cancellation in N3 leaves rounding residue, so a nonzero norm is expected regardless. P5 did say nonzero gradients cannot pass R; this explains why they carry almost no information. | Inference from N3. |
| N5 | **Where the time goes** (synthetic tensors, 512 queries, one thread, one machine, one invocation; medians). Tree 6,529 µs end to end: gather of raw candidate keys 31.5%, `topk(9)` 24.5%, batched product 17.8%, normalization of gathered keys 14.4%, candidate-ID sort and regather 9.1%, router + prior + index construction under 3%. Flat 2,378 µs: `topk(9)` 85%, matrix product 13.9%, key normalization 0.7%. The synthetic tree/flat ratio (2.75) is close to the retained P5 lookup ratio (2.67). | Exploratory, `operators/`. The stage decomposition is bitwise equal to the original. Not registered evidence; run-to-run variance not measured; internal temporaries not counted in bytes. |
| N6 | `topk(9)` on the tree's 512-wide rows costs 77% of what it costs on flat's 4,096-wide rows. Selection cost here is dominated by a per-row cost, not by row length. | Exploratory, same source. The cause inside PyTorch was not established. |
| N7 | The tree path materializes at least 45 MB of intermediate tensors per 512-query call against about 9 MB for flat. "Fewer keys consulted" coexists with about five times more memory traffic in this implementation. | Exploratory lower bound (stage outputs only). |

## 4. Hypotheses — not established

Each is consistent with the evidence and none has been tested.

- **H-a. The tree can be made roughly as fast as flat at 4,096 slots by removing gather, re-normalization and the ID sort.** N5 says about 55% of tree time is in those stages. Not tested: no optimized implementation exists.
- **H-b. The tree cannot be made much faster than flat at 4,096 slots,** because selection is a shared floor (N6) and flat's scoring product is already only ~14% of its time. If so, any efficiency case for hierarchy at this size disappears and rests entirely on larger memories, which have not been studied.
- **H-c. The branch prior, not the candidate restriction, drives the trees' lower slot diversity (E9).** Route scores are cosines divided by 0.2, so the two visited branches' priors can differ by several nats, enough to suppress the second branch's candidates in an eight-slot softmax. Training the router could widen that gap, which would fit learned being more concentrated than fixed. Untested.
- **H-d. The top-2 restriction excludes slots an exhaustive search would select.** Never measured. Even if true, it need not matter for prediction, since unvisited branches' keys were not trained for those queries.
- **H-e. The trees' small quality deficit to flat comes from (c) or (d).** Untested, and the deficit itself is below the registered resolution (N1).
- **H-f. A router trained with a signal about branch choice would help.** P5 does not bear on this (N3).
- **H-g. Dense adapters lead because the comparison matches parameters and updates but not the kind of capacity.** A dense adapter updates all its weights on every token; a sparse memory updates eight of 4,096 value rows per query over 512 updates. P4 and P5 show dense ahead at this budget; whether that persists with longer training or larger memory is unknown.
- **H-h. At much larger memory the tree's work reduction turns into a time advantage.** This is the project's original bet. P5 offers no evidence for or against it.

## 5. Where the P5 report could mislead

None of these is an error in P5's numbers.

1. **"Reduced logical score work by 87.1%."** True as a count of dot products. In the same implementation the tree moves several times more bytes through memory per call (N7) and is 2.6× slower. The count should never appear without those two facts beside it. P5's own text is careful about this; summaries of P5 are less so.
2. **"All memory architectures added useful predictive capacity."** True relative to the frozen backbone, and the shuffle control shows the gain depends on learned key–value association. But an equal-parameter dense adapter gained more (0.0273 vs 0.0215–0.0229). On this evidence sparse memory is a less effective use of 198k parameters than a dense adapter at this budget.
3. **"Learned routing failed to improve on fixed routing."** True, and should be read with N3: the experiment could not have shown much else.
4. **Normalization as the stated cause of slowness.** P5 flagged it as plausible, not proven, which was the right caution. The profile indicates it is one of four comparable costs and not the largest.
5. **Passing Q is not equivalence.** P5 says so. The same caution applies in the other direction: flat being "best on mean NLL" is a 0.0008–0.0014 difference that the design cannot resolve (N1).
6. **One machine, one workload family.** All timing is on a single Apple-silicon CPU, single thread, full-context forwards. The inversion may differ on other hardware, with threads, or in single-token decoding. P5 states this.

## 6. Review of the performance implementation

Read: `Memory.lookup`, `Memory.forward`, `tree_candidates`, `stable_top` in `src/arborlm/pilot_model.py`, and the timing harness `src/arborlm/p5_timing.py`.

The timing harness is sound for what it claims: paired interleaving of variants within a worker, rotation of order, warmups, GC control, raw samples retained, reliability rule applied without re-timing. It measures the registered implementation fairly. Its limit is the one P5 states: it times this implementation, not the algorithm.

The tree path does the following per call that the flat path does not, in the order the profile ranks them:

1. `keys[indices]` copies 512 raw key rows per query into a fresh [N, 512, 16] tensor (16.8 MB at N = 512).
2. `stable_top(scores, 8, indices)` is called with candidate IDs that are not ascending, because branches are ordered by route score. It therefore sorts all 512 IDs per query and regathers scores and IDs before `topk`. Ordering the two visited branches by branch ID would make the list ascending by construction.
3. `torch.bmm` over N separate 512×16 by 16×1 products, a shape that gets little from an optimized matrix kernel.
4. `F.normalize` over the gathered copy, recomputing norms of the same 4,096 rows many times over.
5. `topk(9)` over 512 rows, which costs nearly what it costs flat (N6).

Items 1–4 are avoidable without changing the mathematics, in principle. Whether doing so preserves outputs exactly is a numerical question, not an obvious yes: changing the order of floating-point operations can move scores in the last bits and flip a selection at a near-tie. The auditor's analysis of those hazards is in `audit/AUDIT.md` and is the basis for the equivalence classes and guard band in draft ADR-0011.

The flat path's own cost is dominated by selection. Any fair comparison of optimized implementations has to give flat the same attention.

## 7. Independent audit

The auditor (Claude Opus 5.5, separate context, given records and code but not this review's conclusions) recomputed P5 from the per-cell and per-worker records with its own standard-library script and reviewed the retrieval mathematics. Full report: [`audit/AUDIT.md`](audit/AUDIT.md). It is independent engineering and mathematical evidence, not Astra validation and not approval.

**Confirmed.** Every published mean, effect, sign count, parent count, flag clause, latency ratio and utilization figure, to within 5e-16 of the published double. All 612 timing records' medians and reliability flags recompute with no mismatch. `p5_analysis.py` implements ADR-0010 §8 as written. The composite is FALSE.

**Discrepancies (none changes an outcome).**

- D1. `suite/result.json` holds accounting about 0.003 s short of the final values in `suite/terminal.json`; the published figures use the final ones.
- D2. In `p5_analysis.py` the key `Q_<variant>` means the dense contrast in one section and the tree-versus-flat tolerance in another. A reader of `suite/result.json` can confuse a passing tolerance with the failing dense criterion.
- D3. The W flag's `validated` field is always true when the trace function returns, so it adds nothing; the "independently validated traces" requirement rests on P5's separate artifact audit.
- D4. One flat cell (b102-o301-s502) reproduces its joint-permutation NLL to 8.9e-8, not bitwise. Within the registered 1e-6. An exact tie resolved by slot ID is the likely cause; unconfirmed.

**Omissions in the P5 report that the auditor surfaced.**

- **Training time.** Mean training time per cell: flat 3.06 s, dense 4.25 s, fixed tree 14.05 s, learned tree 14.07 s. The trees cost about 4.6× flat to train, a larger gap than at inference. ADR-0010 §11 required training wall times in the final report; they are recorded per cell but not reported.
- **Order effects dwarf architecture effects.** The batch-order factor moves the gain G by 0.010–0.012 nats/byte between levels, roughly ten times the tree-versus-flat difference. The paired design removes this from the contrasts, but the contrasts' own spread across factors is as large as the contrasts.
- **No stable ranking.** The best memory per cell is flat in 12/27, fixed in 10/27, learned in 5/27; all six orderings occur. Leaving out any one parent or seed keeps mean R negative (−0.00089 to −0.00031), so R's sign is not driven by one group, but at −0.31 SD it is not evidence that learned routing is worse either.
- **Dense gate.** The dense adapter's gate falls in all 27 cells (−2.0 to about −2.60) while every memory gate rises, and dense gain correlates with its gate at r = 0.83. Unreported; not known to be a problem.
- **Unvisited branches.** Some learned trees never visited 3 of 16 branches on the whole panel.

**Mathematics.** The auditor independently derived the router-gradient result in N3 (router gradient per query is proportional to the difference of the two visited branches' route scores and vanishes when all eight selected slots share a branch), and adds that the router's median share of the pre-clip gradient norm is 0.35, so it also competes for the global clipping budget. It showed that the prior reduces to adding each branch's route score, with a possible range of 0–10 logits between the two visited branches against a ±5 range for the key cosine term, which is what makes H-c plausible. Its equivalence-hazard and fidelity-reference analysis is incorporated into draft ADR-0011.

**Not verified by the auditor:** anything needing binaries, the operator trace events beyond summary fields, commit/ACK linkage, source-freeze hashes and data-panel reconstruction (taken from P5's own audits).

## 8. Limits of this review

- No checkpoint was loaded and no model was run on real data. Everything about real checkpoints comes from P5's retained records.
- The operator profile is synthetic, single-invocation and exploratory. It guided the P6 proposal and is not evidence of any speedup.
- The P5 test suite and P5 audits were not rerun by this review; the inventory records their exit codes (11 of 18 retained audit attempts exited 0, 7 non-zero, the failures being earlier attempts superseded by later ones, as P5 documents).
- The lead read ADR-0010, the P5 report and review, the research log and the retrieval code in full, and relied on the research log for the content of ADR-0001–0009 and the P1–P4 reviews.
- Lead, auditor, implementer and clerk are all Claude models. See ADR-0012 §6.

## 9. Contents

| Path | What | Produced by |
|---|---|---|
| `README.md` | This review | Lead (Fable 5.2) |
| [`P6_STRATEGY.md`](P6_STRATEGY.md) | Proposed P6-E / P6-Q strategy | Lead |
| [`DELEGATION.md`](DELEGATION.md) | Roles, models actually used, how checked | Lead |
| [`figures/`](figures/) | Seven figures, generating script, plotted data, input hashes | Implementer (Sonnet 5.5) |
| [`operators/`](operators/) | Exploratory operator profile of the existing retrieval code | Implementer (Sonnet 5.5) |
| [`audit/`](audit/) | Independent recomputation and mathematical review | Auditor (Opus 5.5) |
| [`inventory/`](inventory/) | Evidence inventory | Clerk (Haiku 5.5) |
| [`lead-checks/`](lead-checks/) | Router gradient-support check | Lead |

Figures: [1 NLL by architecture](figures/fig1_nll_by_architecture.png) · [2 router contrast](figures/fig2_router_contrast.png) · [3 memory dependence](figures/fig3_memory_dependence.png) · [4 work vs latency](figures/fig4_work_vs_latency.png) · [5 slot utilization](figures/fig5_slot_utilization.png) · [6 parent dispersion](figures/fig6_parent_dispersion.png) · [7 absolute latency](figures/fig7_absolute_latency.png)

Reproduce the figures: `uv run --locked --extra pilot --with matplotlib==3.10.8 python docs/reviews/p5-claude-review-2026-11-13/figures/make_figures.py`

## 10. Questions for the human research lead

1. Governance: approve, amend or reject ADR-0012.
2. P6: approve, amend or reject P6-E and P6-Q separately (nine specific decisions in ADR-0011 §6).
3. May this branch be pushed and a draft PR opened? Nothing has been pushed.
4. Should the P5 README or repository README gain a pointer to this review? Not done, to leave P5 files untouched.
5. Should an Astra review of P1–P5 still be sought?
