# ArborLM — Research Log

Chronological, append-only notes. Scientific decisions also go into reviewed ADRs. **There were no experimental results at project initialization; subsequent run records and their limitations are recorded below.**

## 2026-11-12 — Origin and project definition

- Starting observation: Colibrì streams large MoE experts from NVMe while achieving constrained throughput in disk-bound configurations.
- Explored faster CPU/NPU vs transfer bottlenecks; NVMe-to-RAM-to-CPU hierarchy; computational storage; lossless compression, quantization and shared parameter representations.
- Research pivot: rather than accelerating transfer of weights an unchanged model requires, train a **new architecture** that navigates learned parameter memory hierarchically and accesses very little per token.
- User emphasized input vector / related million-vector neighborhood / database or SQL indexing analogy. Interpretation: learned coarse-to-fine routing plus sparse retrieval, not literal database SQL on every token and not fetching 1M vectors.
- Chosen working name: ArborLM; layer concept HNM (Hierarchical Neural Memory).
- Decision: portable proof of concept first, not hosted in user's infrastructure; conditional future scale if evidence warrants it.
- Decision: publication-quality methodology and documentation from inception.
- User model-workflow rule: Astra for science/reasoning/orchestration/final validation; lower-tier model for implementation under Astra-approved specification.
- GitHub repository created: https://github.com/Dandush03/ArborLM . Apache-2.0 recommended; direct integration write previously failed, so verify `LICENSE` is committed.
- Open risks: trainability, novelty, fair baselines, physical read amplification, path to model migration, quality vs stored capacity.
- **No ArborLM experiment run yet; no scientific result claimed.**

## 2026-11-12 — Phase 0 implementation proposal recorded

- Read the repository policy, canonical handoff, experiment protocol, research log, ADR-0001 and kickoff prompt in full; inspected the README, paper outline and experiment-record template.
- At inspection, HEAD was `2555ed4`; the working tree was clean and contained no model implementation, tests or experiment artifacts. `LICENSE` is tracked and contains Apache-2.0 text; the root handoff copy matches the canonical document.
- Added `docs/decisions/ADR-0002-phase0-plan.md`, marked **SPEC: PENDING ASTRA REVIEW**, consolidating the inherited E0/G0 roadmap, reproducibility requirements, proposed correctness checks, review decisions and deferred memory/storage work.
- This is a planning/documentation change only. No scientific settings were approved, no model code was written, and no tests, training or benchmarks were run. No result or Astra validation is claimed.
- Next dependency: actual Astra review of the specification and recorded decisions before dependent model/data implementation; lower-tier implementation and independent validation remain pending.

## 2026-11-12 — Human authorizes alternate scientific reviewer

- The human lead explicitly selected **“Authorize this model as scientific reviewer”** in this project chat. This is a recorded session exception to the mandatory Astra reviewer preference; no Astra identity or review is inferred.
- Planning files were committed/pushed as `815f528` at the human's request.
- Added ADR-0003 as the concrete E0 specification, approved by the authorized root Codex reviewer. It resolves ADR-0002 A0–A8 for a bounded CPU correctness/reproducibility milestone; implementation and independent result inspection remain pending.
- Lower-tier implementation will follow ADR-0003. No E0 result, core-hypothesis validation, novelty, speedup or publication approval is claimed.

### Implementation service failure

- Attempted the required lower-tier implementation delegation using `glm-5.3-flash:cloud`. The agent failed before implementation with: `ollama cloud is disabled: remote model is unavailable`.
- No model code or experiment was produced by that attempt. Requested an explicit human exception for this model to implement, or restoration of the lower-tier service; reviewer authorization alone was not silently extended to coding-model authorization.
- Human response: **“use luna or sol if you see fit, not another astra agent”**. Implementation is therefore delegated to an explicitly selected Sol/Luna agent; no root-implementation exception or additional Astra agent is inferred.

## 2026-11-12 — E0 local gate accepted; real-text screen preregistered

- Sol implemented ADR-0003; Luna independently checked the contract and supplied hand-calculated loss/causality/state-isolation tests. Root inspected the model, generator, objective, checkpoint, orchestration and test code.
- Root independently ran `uv run --locked ruff check .`, `uv run --locked mypy src/arborlm`, `uv run --locked pytest` (31 passed), and the registered CPU smoke (11/11 checks passed). Exact outputs and compact raw evidence are in `results/e0-2026-11-12/`; full checkpoints/source archives remain locally under the recorded experiment directories.
- Fresh repeat, checkpoint reload and interrupted resume match bitwise within the tested macOS arm64 environment. G0 engineering gate accepted by the authorized reviewer; Astra validation NOT PERFORMED. Linux CI awaits execution. No memory architecture has yet been tested.
- Human approved pinned WikiText-2 local pilot use (ADR-0004). ADR-0005 preregisters six variants × three seeds, exact data/lookup rules, token/resource budgets and screening thresholds before pilot outcomes. A failed screen will stop promotion of that configuration, not establish universal disproof.
- Human additionally requested each checkpoint/check be pushed to GitHub for tracking; completed verification bundles and subsequent experiment outcomes will be versioned and pushed on the work branch. Merge/publication approval remains separate.

### Linux CI and data-acquisition checkpoints

- E0 implementation/evidence pushed as `677ef8e`; draft PR #1 tracks this work. GitHub Actions run `43351992585` passed Linux lint/typecheck, 31 tests and 11 smoke gates. Logs/status and compact CI evidence are preserved under `results/e0-2026-11-12/linux-ci-43351992585/`; full CI artifacts were downloaded locally before expiry.
- Luna acquired approved pinned train/validation files plus the upstream README, 7,025,216 bytes transferred. Both corpus SHA-256 values match ADR-0004; test data was neither acquired nor inspected. Root reran the downloader's 9 mocked tests, Ruff and mypy successfully.
- Root review caught an idempotency bug accepting a manifest when a data file was missing; Luna corrected it and added regression coverage before the acquisition checkpoint was accepted. Failed acquisition attempts now retain status/error history.
- The publisher README has conflicting license metadata (front matter 3.0/GFDL, body 4.0); both are preserved without choosing legal precedence. Exact-byte local-use approval remains recorded; release rights are unresolved. No pilot model has been trained at this checkpoint.

### RAM pilot preflight accepted before trial

- Sol implemented the six registered variants and bounded suite; Luna audited lookup math, tie handling, gradients, initialization, parameter counts and data rules. Root independently reviewed code and reran locked Ruff/mypy, 59 tests and E0 smoke (11 gates), all passing.
- Root independently reconstructed the selected UTF-8 byte chunks and matched both arrays and rank/row/offset identities. Evidence is in `results/p1-preflight-2026-11-12/`.
- Source/config/spec are frozen before trial. Root authorizes the exact ADR-0005 command under its registered CPU/RSS/token/time bounds. No observed pilot loss was used to select thresholds or change settings.
- At the human's request, each completed run will be reported in chat with observed loss/runtime and a bounded interpretation, and completed checkpoints will be pushed to GitHub.

### P1 completed — promotion threshold missed

- All 18 preregistered runs completed within limits; each consumed 131,072 targets. Every run was reported in chat and all six controls for seeds 42/43/44 were preserved/pushed. See `results/p1-2026-11-12/` for full-precision raw results and the authorized reviewer interpretation.
- Learned-tree mean validation NLL: 2.578732837; small dense: 2.588018314. Improvement 0.0092854773 nats/byte is below the required 0.01. **Promotion gate FAILED; do not scale this configuration under this protocol.** The gate was not relaxed.
- Learned routing beat fixed routing for all seeds and avoided the registered gross-collapse condition. Parameter-matched dense had lower loss for all seeds and lower observed training time. These are bounded observations, not significance, novelty, inference speed or general concept proof/disproof.
- ADR-0006 preregisters a separate post-screen diagnostic on existing checkpoints, with no additional training. Its outcome cannot reverse the original gate. Independent artifact/arithmetic audit is pending; Astra review remains NOT PERFORMED.

- Subsequent Luna read-only artifact audit confirmed all 18 cells, target/event counts, arithmetic, identities and actual checkpoint hashes. One Git HEAD changed mid-suite because of a result-only push; the auditor verified identical source archive hashes and no code/config/spec/data changes. See the separate audit record; original metadata remains unchanged.

### Frozen-memory diagnostic — inconsistent contribution

- ADR-0006's 12 evaluations completed with zero training. All original replays and paired key/value permutations within branches reproduced the original validation NLL exactly; checkpoint files remained unchanged.
- Disabling memory slightly improved loss in seeds 42 and 43 but worsened seed 44 by 0.0067755841 nats/byte. Shuffling values followed the same directions. Mean disabled delta was +0.0020039926; mean shuffled-value delta was +0.0021469779. Both missed the registered +0.005 diagnostic threshold.
- Preserve the seed-44 positive dependence and the two opposite-sign outcomes. Useful memory contribution was not reliably demonstrated across seeds at this budget. Nonzero router gradients alone do not establish useful inference memory.
- Results and all 12 raw records are in `results/memory-diagnostic-2026-11-12/`. Earlier promotion failure remains unchanged; scaling is stopped. The broad concept is unproven, not universally disproved. Human merge/publication approval remains pending and Astra review NOT PERFORMED.
- Luna independently audited all 12 raw diagnostic records, target counts, lack of training events, arithmetic and current original checkpoint/index hashes; no discrepancy found. This is recorded separately as an engineering audit, not Astra scientific validation.

### Final tracking checkpoint

- At the research lead's request, each completed run was reported in chat and verification and results checkpoints were pushed to GitHub for tracking. The final local verification passed 67 tests, and [Linux CPU CI run 43354341475](https://github.com/Dandush03/ArborLM/actions/runs/43354341475) passed at commit `6ce7928`.

### Follow-up hypothesis from human lead

For seed 44, validation NLL was 2.5893889144062996 nats/byte for small dense, 2.5889271199703217 for the learned-tree checkpoint with memory disabled, and 2.582151535898447 with memory enabled. The interventions support a benefit from memory in that frozen checkpoint on this validation set; they do not establish statistical generalization. The lead's hypothesis is that optimization inconsistently discovers and exploits useful memory. Validation noise, effects of the shared training trajectory, the finite training budget, and sensitivity to initialization remain plausible explanations. The disabled model retains its jointly trained backbone, so it cannot substitute for a model trained without memory.

A candidate follow-up would separate the random seeds for backbone initialization, memory and router initialization, and batch order; cross those seeds under a fixed budget; and pair evaluations with memory enabled, disabled, and values shuffled. It would also include a control with memory disabled throughout training, report every seed, and define interaction and dependence metrics and thresholds before running. Confirmatory claims would require fresh held-out data because the current validation set informed the hypothesis. This design is neither preregistered nor approved for execution. No new experiments started, and the failed promotion gate remains unchanged.

### Controlled follow-up authorized and preregistered

- The human subsequently instructed: “Go ahead and preregister the controlled follow-up, then use Sol or Luna to implement and run it. Report each experiment here and push every checkpoint to GitHub.” ADR-0007 was committed/pushed as `3c0dd8c` before implementation or P2 outcomes; it supersedes the preceding candidate's unapproved status for its exact bounded design.
- The authorized reviewer fixed 27 crossed backbone/memory/order initializations plus 9 disabled-throughout controls, with unchanged model size and 131,072 training targets per cell. Batch-order seeds permute the same 2,048 examples. Memory and router initialization remain one combined factor; optimizer hyperparameters and training length do not vary.
- A previously unevaluated panel takes eligible validation ranks 512–1023 under the existing exact-chunk exclusion recipe. It is not an independent corpus; shared articles and near-duplicates remain possible. Original P1 promotion failure remains unchanged.
- Sol owns implementation and execution after root preflight; Luna independently audits controls and artifacts. Every cell and its interventions will be reported in chat, with compact evidence pushed after completion. Binary checkpoints/data remain local under existing policy. No P2 result exists at registration; Astra review NOT PERFORMED.

### P2 preflight accepted before training

- Sol implemented isolated P2 modules without changing the original numerical sources. Luna's five independent tests cover factor isolation, dense-equivalent controls, frozen optimizer-excluded memory, checkpoint resume, panel disjointness and hand-computed interaction arithmetic.
- Root read the implementation and independently passed locked Ruff, mypy (25 files), 79 tests and E0 smoke (11 gates). Independent raw-Parquet reconstruction matched the P2 panel checksum and original data identities. Evidence: `results/p2-preflight-2026-11-12/`.
- Root authorizes Sol to execute exactly ADR-0007 after committing the code freeze. No P2 outcomes were observed or used to alter the registration. During execution only result records may be committed; source/config/spec/data identities must remain invariant. Prior failed gate and Astra NOT_PERFORMED status remain unchanged.

### P2 completed — memory effects below registered sensitivity

- Sol completed all 36 registered runs and 4,718,592 training targets in suite `P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7`, from source freeze `fd61cb7a69b8d29484cf8bef0170c1eb168da1fe`. Suite wall time was 321.710 seconds; peak sampled process-tree RSS was 676,052,992 bytes. All 36 checkpoint replays and all 27 joint key/value permutations matched bitwise. Per-run reports and compact GitHub checkpoints preserve the outcomes; corpus bytes and checkpoint binaries remain local.
- Mean increases from disabling memory and shuffling values were 0.000693748 and 0.000685635 nats/byte. Both effects were positive in 22 of 27 learned runs, but neither reached 0.005 in any run, and all three registered descriptive flags were false. Most of the mean gain against controls trained without memory (0.006731979) persisted with memory disabled (0.006038231). Training outcomes varied, but a strong retained memory benefit was not established at this budget. The P1 promotion gate remains failed, and the broader concept remains unproven.
- Root independently recomputed the paired deltas, summaries, factor decomposition and flags from the [per-run records](../results/p2-2026-11-12/) and found no discrepancy. Luna's separate artifact audit is pending at this entry. Astra review was not performed under the human-authorized reviewer exception. Human merge and publication approval remain pending.
- [Linux CPU CI run 43356920425](https://github.com/Dandush03/ArborLM/actions/runs/43356920425) passed at aggregate-result checkpoint `85be770`, including lint, mypy (25 files), all 79 tests and E0 smoke. Logs and uploaded artifacts were retained locally under `experiments/review/` and `experiments/ci/`.
- Luna subsequently completed the separate read-only artifact audit: all 36 cells, actual step-128/256 checkpoint bytes and embedded counters, frozen control tensors, permutations, source/data identities and independently computed effects/flags matched. The audit preserves a provenance caveat: 33 manifests record `dirty=true`, while all source diffs are empty/hash-valid and source archives identical; observed HEAD changes touch only result records. Original metadata was not rewritten. See `results/p2-2026-11-12/independent-artifact-audit.md`. This is independent engineering evidence, not Astra validation; the scientific interpretation remains the authorized root review.

### P3-LT preregistered before further training

- The human requested a bounded test of longer training before redesigning the architecture: continue all 36 existing P2 step-256 checkpoints to 1024, same 2048 examples/order/optimizer, evaluate 256/512/1024 on a new 512-chunk panel, with an 1800-second total worker ceiling and 2 GiB per cell. No favorable seed selection or reversal of P1/P2 was authorized.
- The authorized reviewer froze ADR-0008 and committed/pushed it as `aa3385b` before implementation or new-panel model outcomes. It defines paired changes in disabled/shuffled memory dependence, endpoint dependence and an endpoint quality guard; step 1024 is primary, step 512 secondary. These are descriptive sensitivities, not significance tests or automatic scaling approval.
- Luna verified all 36 local P2 parent mappings/checkpoint files and actual state hashes. Root independently reconstructed the fresh panel at validation ranks 1024–1535, matching old train/P1/P2 identities and finding no exact overlap with prior panels or full train candidates. New panel SHA-256: `a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0`; shared-article/near-duplicate limitations remain.
- Sol implements and executes only after independent preflight/code freeze; Luna independently audits continuation and artifacts. No P3 model result exists at registration. The GitHub branch/draft PR were accessible and the preregistration push succeeded; no merge occurred. Astra review NOT PERFORMED; human merge/publication approval remains pending.

### P3-LT preflight accepted before execution

- Sol implemented isolated continuation modules; Luna supplied six independent synthetic contract tests. Root read all new code/tests and independently passed locked Ruff, mypy (31 files), 90 tests and E0 smoke (11 gates). Existing numerical sources remain unchanged.
- Root caught and reviewed a bookkeeping fix to capture final suite error logs after worker exit. After that finalization-only change, Ruff/mypy and the targeted partial-evidence test passed again. Full logs and the independently reconstructed data panel are preserved in `results/p3-lt-preflight-2026-11-12/`.
- The replay-count clarification was pushed as `270c655` before any P3 model outcome. Root now authorizes Sol's exact registered CLI after source freeze, with all 36 parents, no optimizer resets/seed selection, and unchanged resource ceilings. P1/P2 results remain unchanged; Astra validation was not performed.

### P3-LT completed — prediction improved; memory-dependence thresholds missed

- Sol completed all 36 registered continuations in suite `P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d`, from source freeze `861c137a7fcccf27e3371ca2217fd7d956753ca9`. The suite ran 871.734423 seconds at peak sampled process-tree RSS of 650,657,792 bytes. It added 14,155,776 targets (18,874,368 lifetime), preserved 108 snapshot indexes and all 459 new-panel evaluations, and passed 36 old-panel parent-integrity checks. The old panel was excluded from scientific comparisons. All 36 compact bundles were reported in chat and pushed; binaries remain local.
- All 27 learned cells and nine controls improved on the new panel. Mean ΔD/ΔP were 0.002725350/0.002516165 nats/byte (both positive in 22/27); endpoint D/P were 0.003416745/0.003204836 (both positive in 24/27). Both memory-dependence flags failed their mean thresholds; the endpoint quality guard passed. Mean paired gain narrowed from 0.007235188 to 0.003421512, with endpoint S at 0.000004767. Longer training increased descriptive dependence on this panel without meeting the registered criteria. P1/P2 outcomes remain unchanged; the result neither settles the broad concept nor authorizes scaling.
- Root independently recomputed the results and found no discrepancy. See the [P3-LT report and compact evidence](../results/p3-lt-2026-11-12/). Luna's separate artifact audit is pending at this entry. Astra review was not performed under the human-authorized reviewer exception. Human merge and publication approval remain pending.

### P3-LT artifact audit and review completed

- Luna's [independent artifact audit](../results/p3-lt-2026-11-12/independent-artifact-audit.md) verified all 108 checkpoint snapshots, all 36 unchanged P2 parents, and exact model, optimizer, and RNG equality for each zero-update conversion. The audit recorded 18 distinct HEADs, 35 manifests marked dirty, 36 empty and checksum-valid source diffs, and identical source archives. Root reviewed and reran the audit: it exited successfully with identical output and no issues.
- [Linux CPU CI run 43361998534](https://github.com/Dandush03/ArborLM/actions/runs/43361998534) passed Ruff, mypy (31 files), all 90 tests, and E0 smoke. Logs and uploaded artifacts were retained locally. The [authorized scientific review](../results/p3-lt-2026-11-12/authorized-scientific-review.md) records the bounded interpretation. Astra review was not performed; human merge and publication approval remain pending.

### P4 frozen-backbone design preregistered

- The research lead authorized a bounded local RAM comparison. The [P4 specification](decisions/ADR-0009-frozen-backbone-capacity.md) uses all nine final P3 controls as immutable backbones: nine frozen baselines, 27 trainable hierarchical-memory additions, and 27 dense adapters with the same 198,401 trainable parameters and 512-update budget. It freezes the parent mapping, training examples and order, fresh validation panel, intervention checks, and descriptive criteria before any P4 outcome.
- Root approved the exact design under the standing human-authorized Codex reviewer exception. Implementation, independent engineering preflight, and the source freeze are pending; no P4 model evaluation or training has run. Astra review was not performed. P1–P3 outcomes and pending human merge, publication, and scaling decisions remain unchanged.

### P4 engineering preflight accepted before execution

- Root reviewed all seven new P4 modules, the strict config, and both test files, then independently passed locked Ruff, mypy (38 files), all 116 tests, and all 11 E0 smoke gates. Synthetic tests do not contribute to P4 outcomes. The only warning was PyTorch's optional NumPy integration.
- Root strictly restored all nine registered P3 parents and checked exact extracted tensor bytes, the frozen-backbone digest including the mask, and fresh addition-only AdamW state and membership for both 198,401-parameter additions. The corrected audit passed after a scalar dtype-view tooling error; both logs are preserved. The panel matched the independent reconstruction at SHA-256 `4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f`. See the [preflight evidence](../results/p4-preflight-2026-11-12/).
- Root accepts engineering preflight under the human-authorized reviewer exception. Execution remains conditional on a source freeze and explicit run authorization. No real-data P4 forward, evaluation, or training update has run. Astra review was not performed; human merge and publication approval remain pending.

### P4 completed — memory adds capacity; the dense adapter leads

- Sol completed all 63 registered cells in suite `P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd` at source freeze `812b3fd02d81124b0665cc96d1364a32e40d403d`: nine baselines and 54 trained additions, 27,648 updates, 14,155,776 additional targets, 171 snapshots, 288 scientific evaluations, and nine separate P3 integrity evaluations. Suite worker wall time was 652.374330791 seconds and peak sampled process-tree RSS was 670,498,816 bytes. All 63 compact cell bundles, containing 171 checkpoint indexes, were reported in chat and pushed; corpus and binary weights stay local.
- Mean capacity gain C and disabled effect D both equal 0.021988695 nats/byte. Mean shuffled-value effect P is 0.022221519. C and P were positive in all 27 memory runs and all nine parent means, meeting the registered capacity and slot-association criteria. Mean dense gain was 0.028171332 and mean Q was −0.006182638; dense had lower loss in all 27 matched comparisons. Only 10/27 pairs and 2/9 parent means met the dense tolerance. Dense tolerance, the secondary advantage flag, and the composite criterion failed. This establishes bounded frozen-backbone contribution under the registered conditions without reversing P1–P3 or authorizing scaling.
- Root independently recomputed the result from raw events with no arithmetic discrepancy. Luna saved the [final source-freeze proof](../results/p4-preflight-2026-11-12/final-freeze-proof.md) before documentation or portability changes. Linux CI flagged a synthetic test's floating-point reduction expectation; the post-run test-only repair and final CI verification are pending at this entry. See the [P4 results](../results/p4-2026-11-12/). Astra review was not performed; human merge, publication and scaling approval remain pending.

### P4 artifact audit and authorized review completed

- The [independent artifact audit](../results/p4-2026-11-12/independent-artifact-audit.md) passed for all 171 checkpoints. Root read and reran the published audit; it exited successfully and its output was byte-identical. Root also reran the published arithmetic audit and reproduced its outputs exactly. The [authorized scientific review](../results/p4-2026-11-12/authorized-scientific-review.md) records the bounded finding. P4 does not establish that freezing is better than joint training: P3 used a different memory initialization and evaluation panel.
- The post-run test-only portability repair passed [final local verification](../results/p4-2026-11-12/root-final-checks.log): all 117 tests, Ruff, mypy (38 files), and all 11 E0 smoke gates. The [original Linux CI failure log](../results/p4-preflight-2026-11-12/code-freeze-ci-43366259292.log) is preserved. No experiment evaluator or raw outcome changed. Final GitHub CI was pending when this entry was recorded; current status is tracked on [draft PR #1](https://github.com/Dandush03/ArborLM/pull/1). Astra review was not performed; human merge, publication and scaling approval remain pending.

## 2026-11-13 — P5 architecture-ablation proposal, awaiting scientific approval

- The human requested a fixed-size comparison of flat, fixed-router and learned-router memory on all nine P4 frozen-backbone parents, with the dense adapter and unchanged baseline retained as references. Read AGENTS, the canonical handoff/protocol, ADR-0005–0009, all four finalized scientific reviews, research log, P4 implementation and independent audits before drafting [ADR-0010](decisions/ADR-0010-hierarchical-memory-ablation.md).
- Root Codex drafted the proposal under the documented reviewer exception. It proposes fresh shared seeds 501–503, unchanged 512-update optimization, a new panel at eligible validation ranks 2048–2559, and fresh dense-adapter training under the same protocol: 117 cells, 108 trainings, 333 snapshots and 612 scientific evaluations plus nine old-panel integrity checks. Only frozen baseline backbones are reused; no trained P4 additions or old-panel quality results enter P5 comparisons.
- The proposed decisions separate learned-versus-fixed quality, acceptable quality relative to flat, observed score-work reduction, and reliable measured RAM latency. The real 256-scalar router difference is exposed. Flat matrix operations and tree gathers have different normalization/materialization costs, so fewer dot products cannot be reported as lower total work or hardware speed without measurement. Proposed worker caps are 1,800 seconds for quality/training plus 600 for profiling/timing, 2,400 combined, with 2 GiB RSS bounds.
- Luna performed a read-only factual check of existing code and matrix/parameter arithmetic; that is not scientific approval or P5 engineering preflight. This checkpoint contains a proposal only. Authorized scientific approval, resource approval, implementation, independent preflight and numerical freeze remain pending. No P5 model evaluation, training, timing, data acquisition or architecture implementation occurred. Astra review is NOT_PERFORMED. P1–P4 outcomes remain unchanged; human merge, publication and further-phase/scaling decisions remain pending.

### P5 specification and resource budget approved before implementation

- The human explicitly approved ADR-0010 and the 2,400-second budget and directed Sol to implement, Luna to review, and preflight/freeze to precede training. Root recorded authorized scientific acceptance in ADR-0010 under the existing reviewer exception. The exact proposal settings and thresholds are unchanged.
- Sol implementation is now authorized; Luna supplies independent engineering review. Root retains scientific decisions, independent preflight acceptance, execution orchestration and final interpretation. No P5 model evaluation/training/timing has occurred. Every completed run/checkpoint will be reported and pushed. Human merge/publication/further-phase approval remains pending; Astra review is NOT_PERFORMED.
