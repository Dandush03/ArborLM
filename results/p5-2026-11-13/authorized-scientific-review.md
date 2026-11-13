# P5 scientific review — frozen-backbone hierarchy ablation

Reviewer: root Codex, acting under the human research lead's explicit scientific-reviewer exception. **Astra specification and result review: NOT_PERFORMED.** Sol implemented/executed; Luna independently reviews engineering artifacts. Human approval of ADR-0010 and its 2,400-second budget preceded implementation. Merge, publication and further-phase/scaling approval are separate and remain pending.

**Final disposition:** root accepts the engineering integrity and the bounded scientific interpretation below after independently reviewing and rerunning the final arithmetic, binary-artifact, utilization and reporting/resource checkers. All reruns match their originating outputs byte for byte. The experiment's full learned-hierarchy criterion is **FAILED**. No numerical outcome or preregistered threshold changed.

## Scientific finding

P5 supports useful frozen-backbone neural memory at the registered size and training budget, but **does not support a meaningful quality–latency advantage for the tested hierarchy or a benefit from training its router**. The learned-hierarchy composite fails. Reduced score counts survive direct operator inspection; lower measured latency does not. These are bounded findings about this implementation, dataset, parent family and workload. They neither prove nor disprove the broader storage-scaled learned-memory hypothesis.

The experiment included all nine P4 frozen-backbone parents and all three predetermined initialization seeds, with fresh flat memory, fixed-router memory, learned-router memory and dense adapters. All 108 additions received the same 512-update/data-order/optimizer budget. There was no checkpoint selection, favorable-seed continuation, new architecture, additional capacity, topology change, SSD experiment or result-dependent rerun. The nine frozen baseline evaluations received no training. P1–P4 outcomes are preserved.

## Registered quality tests

Mean baseline NLL was 2.356630571600464 nats/byte. Across 27 cells per addition:

| Addition | Final mean NLL | Mean gain G | Mean shuffle penalty P | Gain / shuffle both positive |
|---|---:|---:|---:|---:|
| Flat | 2.333691890041033 | 0.022938681559430 | 0.022679531739818 | 27/27 cells, 9/9 parents |
| Fixed tree | 2.334497243027996 | 0.022133328572468 | 0.021944248289974 | 27/27 cells, 9/9 parents |
| Learned tree | 2.335080704203358 | 0.021549867397105 | 0.021603652586540 | 27/27 cells, 9/9 parents |
| Dense | 2.329312946371458 | 0.027317625229005 | — | 27/27 positive gains |

All memory usefulness U clauses pass: mean G and P exceed 0.005, the required positive cell/parent counts are met, and mean final loss is below initialization. Disabling each trained addition returns the frozen baseline loss exactly. Shuffling memory values removes the learned key/value association and increases loss. Joint paired permutation controls preserve panel NLL within the registered tolerance; the retained real-data records do not establish per-logit equality. These controls distinguish useful memory contribution from backbone optimization under this frozen-backbone protocol; they do not identify the semantics stored in individual slots.

For the primary router contrast, R = NLL(fixed) − NLL(learned), the mean is **−0.000583461175362**, sample SD 0.001871343960431, minimum −0.004701465368271 and maximum +0.003432027995586. Only **10/27** paired effects and **3/9** parent means are positive. The registered mean ≥0.005, ≥22 positive cells and ≥8 positive parents all fail. No individual R reaches +0.005. Because the fixed and learned variants start with identical router/key/value/projection tensors and differ in router trainability, this is direct evidence against the registered benefit of training this router under the tested conditions. It does not establish that all possible router training methods fail.

Tree-minus-flat loss T averages **+0.000805352986963** for fixed routing and **+0.001388814162325** for learned routing. Each has 26/27 cells and 9/9 parent means at or below +0.005, so both Q flags pass. Passing a tolerance allows a small degradation; it is not evidence of equal loss or superior quality. Fixed beats flat in 12/27 cells; learned beats flat in 8/27. Flat is the best memory architecture on mean NLL.

The dense reference is evaluated separately. Dense-minus-memory NLL averages −0.004378943669575 (flat), −0.005184296656538 (fixed), and −0.005767757831900 (learned). The +0.005 memory-loss tolerance is met in only **15/27 and 6/9**, **14/27 and 5/9**, and **13/27 and 5/9** cells/parent means, respectively. All three dense-reference flags fail, including flat despite its passing mean clause. Dense has lower loss than flat in 25/27 pairs and than each tree in all 27. This comparison provides a capacity reference; it is not a test of hierarchical advantage.

Raw paired values, sample standard deviations, signs, parent means and factor marginals are in the [independent arithmetic output](audit/root-arithmetic.stdout). Cells share nine parents, three initialization seeds and a common panel. The registered descriptive consistency rules are not significance tests, independent-replicate confidence intervals or guarantees of out-of-domain generalization.

## Work reduction and measured latency

Flat memory scores 4,096 keys/query. Each tree scores 16 router branches and 512 candidate keys/query, selecting eight values. Thus observed key-plus-router score work and logical candidate-key-plus-router element counts are **0.12890625× flat**, an **87.109375% reduction**. Each tree meets the registered ≤0.25 work ratio in all 216 paired trace comparisons. The separate artifact audit checks the actual matrix, gather, normalization and selection operand shapes; these counts must not be equated with measured FLOPs or physical traffic.

That work reduction did not become a latency benefit. Across all 27 primary CPU batch-8, length-64 comparisons:

| Hierarchy / flat ratio | Fixed tree | Learned tree | Registered geometric-mean ceiling |
|---|---:|---:|---:|
| Addition forward | 2.603052229693476 | 2.598485032668176 | 0.80 |
| Full model forward | 2.190282147732538 | 2.184085943163431 | 1.05 |

Every relevant primary pair passes the preregistered timing reliability checks. Neither hierarchy meets the pairwise addition ratio <1 or full-forward ratio ≤1.05 in any of the 27 pairs or nine parent geometric means. **Both L flags are FAIL, not INCONCLUSIVE.** All original warmups, 80 timed samples per scope/variant/workload and eight round medians are retained. Two batch-8 retrieval-only records and two secondary batch-1 records failed the stability rule; they were retained without remeasurement and do not replace the primary scopes.

The operator traces expose countervailing costs. At batch 8, flat normalizes 65,536 key elements once, whereas the existing tree path materializes and normalizes 4,194,304 candidate-key elements across its 512 queries: 64 times as many key-normalization input elements. Router normalization, index gathers and selection also contribute overhead. This supplies a plausible implementation explanation for the latency result, not a causal allocation of elapsed time to individual operators. No kernel redesign or caching change was introduced after seeing these measurements.

Parameter accounting also remains explicit. Flat and fixed have 198,145 trainable addition scalars; learned and dense have 198,401. Fixed retains 256 additional router-buffer scalars, learned trains those scalars, and flat has no router. All share the 27,392 frozen backbone scalars. No dummy parameters are used. The registered per-query consulted addition-state counts are 67,329 for flat and 10,241 for either tree, about 33.98% and 5.16% of stored addition state; fixed's trainable-only fraction is about 5.04%. These are logical consultation fractions, not the fraction of optimizer state updated, resident RAM saved, physical reads, or achieved hardware utilization. All model state is RAM resident, and optimization/normalization can touch more state than selected values.

## Slot use and routing concentration

The separate [utilization audit](audit/independent-utilization.md), reviewed and rerun by root with byte-identical output, reconstructs counts and entropy for all 162 initial/final memory evaluations. Each evaluation has 32,768 queries and 262,144 selected-slot events. Tree branch visits sum to 65,536, and selected-value branch totals agree with the underlying slot counts. The maximum scalar reconstruction discrepancy is 3.41 × 10⁻¹³, below the audit's 10⁻¹² tolerance.

| Mean final utilization | Flat | Fixed tree | Learned tree |
|---|---:|---:|---:|
| Unique selected slots | 428.59 | 383.41 | 313.11 |
| Effective selected slots, exp(Shannon entropy) | 132.34 | 96.25 | 83.02 |
| Hottest selected slot fraction | 0.029284 | 0.040757 | 0.043199 |
| Nonzero top-1 branches | — | 14.22 | 10.85 |
| Normalized top-1 branch entropy | — | 0.652912 | 0.613652 |
| Hottest top-1 branch fraction | — | 0.329350 | 0.353433 |

Fixed/learned initial utilization is exactly paired in all 27 cases. Their mean initial effective-slot count is 234.81; flat starts at 273.15. All learned-router cells record positive router-gradient norms in all 512 updates and positive final router movement; fixed-router movement is zero. Thus a completely disconnected or never-updated learned router is inconsistent with the evidence. Learned routing is descriptively more concentrated at the endpoint, but these observations do not establish that concentration caused its lower quality. No post hoc collapse gate or favorable subset analysis is used. Per-query router entropy is only the recorded mean: aggregate branch counts cannot independently reconstruct that statistic.

## Evidence and independent validation

The [execution freeze](../p5-preflight-2026-11-13/execution-freeze/) binds code, configuration, specification, data, parents and lock before training. Root independently accepted preflight after reading code/equations/tests and passing 161 tests, Ruff, mypy and E0 smoke. Separate raw data audits reconstructed the fresh panel and verified all nine parent tensors. Source acceptance was pushed as `9028507844c500bc4d296202e7c6c6e4ae552ecc`; execution freeze was pushed as `6b3e25726d709ab0efe05777ab8205bea5b59464`.

Root reviewed and reran the independent, implementation-free aggregate arithmetic: exact byte agreement with Luna's final output and no discrepancy in effects, thresholds, timing sample arithmetic or counts. Root separately reviewed/reran Sol's orchestration and utilization audits with exact byte agreement. The orchestration check binds 117 cell commits plus 37 stage/worker ACK commits to original and compact bytes and verifies source preservation and resource accounting. Git ancestry and ACK push attestations do not independently prove chat delivery; root directly reported every completed cell/worker in the research conversation before its relevant acknowledgment.

Luna's final [artifact checker](audit/independent-artifacts.py) passed, and root's [independent rerun](audit/root-artifacts-run.json) was byte-identical. It inspected all 333 actual model/optimizer/RNG snapshots, frozen backbone tensors/digests and fixed-router buffers, optimizer membership/options/moments/counters, 27 shared-initialization groups, nine physical P4/P3 parent pairs, 162 permutations, 1,674 quality and 365 timing raw/compact file comparisons, five representative strict restores without forwards, and 648 actual operand traces. Code/config/data identities matched the execution freeze. Both the checkpoint and trace findings support the reported engineering validity; they do not transform failed scientific gates into success. The final [arithmetic rerun](audit/root-final-arithmetic-run.json) matches Luna attempt 05, including the explicitly descriptive router-entropy field.

The suite completed 55,296 updates, 28,311,552 new training targets, 333 snapshots, 612 scientific evaluations plus nine excluded parent-integrity checks, and 58,752 timing calls. Quality time was 1,281.554948874982 seconds, timing active time 214.90431116719265, and combined active time **1,496.4592600421747**. Exactly 822.6909042488551 seconds of validated external reporting waits were recorded separately. Peak sampled suite RSS was 858,423,296 bytes. All worker/stage/suite caps passed. No training/evaluation/timing was repeated for the audits; checkpoint restoration checks perform no model forwards.

Original provenance metadata is retained: the 117 quality cells record 72 distinct Git HEADs and 116 dirty flags; the 36 timing workers record 36 HEADs and 36 dirty flags. Result checkpoint pushes and untracked result files changed repository metadata during execution. All source diffs are empty and all archived source bytes/maps match the pre-execution freeze. Numerical identity is established by those archived bytes, not by claiming identical HEADs or a continuously clean worktree. Final report/documentation edits occur after the recorded source-preservation audit.

All numerical outcomes and failed gates are immutable. Failed preflight and audit tooling attempts are retained with explanations. The initial artifact-auditor path error was a distinction between compact GitHub records and original local binaries; subsequent checker errors concerned top-k boundary bookkeeping. None required changing the frozen experiment. The checker source versions/hashes for failed artifact-audit attempts 01–02 were not retained; their stdout/stderr/exit records remain, and exact checker snapshots are retained from attempt 03. This audit-tooling provenance gap does not affect the registered experiment's archived source, raw outcomes or final reproducible checker, but it limits reconstruction of those early failed checker versions.

## Limitations and disposition

The 512-chunk validation panel is fresh under the registered selection procedure and excludes exact prior-panel/full-training-pool matches. It shares a corpus with training and previous studies; article overlap and near duplicates remain possible. Only 2,048 training chunks are repeated. The small byte-level model, fixed insertion point, one memory size, one optimizer and 512-step budget cannot settle behavior at other scales or tasks. P4 and P5 use different fresh initialization seeds and panels; comparing their aggregate losses is not a controlled P4-to-P5 improvement test.

Fixed versus learned tests router trainability at a fixed partitioning. In the fixed-tree control the router tensor is frozen while the query projector remains trainable, so token-to-branch assignments can still change during training. R isolates the additional training of the router tensor. Tree versus flat also changes candidate access and adds the existing branch-score prior; it does not isolate a pure abstract tree data structure independently of its retrieval mathematics. Hard top-k selected-score gradients, initialization, optimization, concentration, implementation costs and memory size remain possible explanations. No alternatives were tuned during P5. Dense comparisons match learned-tree trainable counts, examples and update budgets, not active compute or training wall time.

The CPU benchmark measures a fixed batched forward workload, not autoregressive decode with a KV cache, GPU performance, whole-system physical traffic, NVMe behavior or cold-storage latency. A future implementation could change the measured frontier, but P5 does not establish that it would. Likewise, reduced logical access does not demonstrate that increasing stored capacity would improve quality.

**Do not promote this P5 configuration to learned topology or memory-capacity scaling on the basis of its composite criterion.** Useful memory remains a bounded positive finding; the specific learned-router advantage and measured quality–latency proposition failed. P1–P4 conclusions stand. Any further research phase requires a new human decision and reviewed preregistration. This review authorizes no merge, publication, capacity increase or SSD work.
