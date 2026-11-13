# ADR-0007 — Controlled initialization and batch-order follow-up

- Date: 2026-11-12 (research lead's timezone).
- Status: **SPEC APPROVED BY HUMAN-AUTHORIZED CODEX REVIEWER; NOT ASTRA REVIEWED**.
- Authority: recorded reviewer exception in ADR-0003; current human instruction to preregister, delegate implementation/runs to Sol or Luna, report every experiment in chat and push checkpoints to GitHub.
- Registration precedes all P2 training and evaluation outcomes. Sol/Luna implement; root independently validates engineering and interprets under the exception. Human merge/publication approval remains pending.

## Question and scope

ADR-0005 failed promotion and ADR-0006 found opposite-sign memory effects across three seeds. The human proposed that optimization may inconsistently discover or exploit useful memory. This follow-up tests dependence on controlled initialization and training-order choices at the SAME model size and per-run training budget. It is exploratory hypothesis testing, not a rescue of the failed gate, scaling, or a claim about novelty, semantic knowledge, significance or NVMe.

Separate three factors: backbone initialization B in **101,102,103**; all memory-component initialization M in **201,202,203**; batch permutation O in **301,302,303**. Cross all 27 combinations. M includes keys, values, adapters and router together; this experiment does not isolate router initialization from the rest of memory. All numbers are fixed before outcomes and were not selected by pilot performance.

For each B/O pair train a control with memory disabled throughout, once: 9 controls, 36 training runs total. The same control is paired with the three M settings; do not count these repeated comparisons as independent control replications. Order: ascending B, then ascending O; within each pair run control first, then learned M ascending. No seed selection, retuning or optional stopping for favorable losses.

## Fixed numerical and data contract

Reuse ADR-0005's small backbone, learned-tree mathematics, 4096 slots, top-2 branches/top-8 values, temperature, scalar gate, float32 CPU execution, optimizer and clipping unchanged. Backbone initialization must equal ADR-0005's construction algorithm with seed B. Memory uses its existing component generators with M+1000 keys, M+2000 values, M+3000 query, M+4000 output, M+5000 router. Fixed gate -2. Model construction and independent factor generators must not consume each other's RNG states.

For the disabled-throughout control, allocate memory with M=201 solely for common checkpoint layout, bypass it on EVERY training/evaluation forward, freeze all its parameters and exclude them from optimization. Report 225793 stored parameters, 27392 trainable/used parameters. Its memory must remain byte-identical to initialization; its backbone/logits/training trajectory must match a dense-small implementation with the same B/order on synthetic fixtures. Learned models retain 225793 trainable parameters. Controls are not compute matched to memory models.

Use the SAME 4096 ranked training chunks and approved pinned local WikiText train/validation files. Verify acquisition/source hashes, tokenizer and original training-byte hash `1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07`. No downloads or test-split access.

For a previously unevaluated validation panel, apply ADR-0005's exact ranking/deduplication/exclusion against ALL train candidates, select the first 1024 eligible unique validation chunks, reserve ranks **512 through 1023 (zero-based)** as P2's sole measured panel. Verify ranks 0..511 reproduce P1 validation-byte hash `2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200`. Ensure no exact overlap with the P1 panel or any full train candidate. Preserve all selected IDs, bytes locally and hashes. This panel comes from the same corpus split and may share articles/near-duplicates: it is previously unevaluated, NOT an independent corpus or a definitive confirmatory test. No P2 outcome is measured on the old panel.

Generate ONE `torch.randperm(2048, generator=CPU_Generator.manual_seed(O))` over the first 2048 ranked training rows (the same rows seen by P1). Use all 2048 indices in order, 8 per batch, for exactly 256 updates / 131072 target bytes per run. Preserve the full permutation and its hash. Thus O changes only the order of the same training examples. No new shuffle or epoch. All cells see the same examples; B/M cells sharing O and their paired controls see identical batch streams. Record this change from P1's fixed ranked traversal.

Total training budget: **4718592 target bytes**. Evaluate 512x64=32768 targets at step 0 and 256; no intermediate validation or early stopping. Save atomic checkpoints at 128 and 256 containing all model components, frozen flags/condition, optimizer, RNG, factor identities, full order hash/cursor, dataset/spec/config/source identities. Restore must reject incompatible identities/corruption. Use separate P2 schema/family; do not silently broaden P1's accepted settings or alter old artifacts/numerical code.

## Frozen final-checkpoint interventions

After every learned run, restore the same final checkpoint afresh for each condition, without training: enabled replay, memory disabled, values permuted, joint key/value permutation within branches. Enabled replay must equal the final loss bitwise; joint permutation tolerance is absolute 1e-6, relative zero. Source checkpoint bytes/index must remain unchanged. Control runs need enabled-state replay only (their memory stays bypassed).

Use `cell_index = (B-101)*9 + (O-301)*3 + (M-201)` (0..26). For values, permute 4096 rows with CPU generator seed `20000+cell_index`; for paired branch permutation use seed `30000+cell_index`, drawing 16 consecutive randperm(256), adding branch offsets. Preserve IDs/hash. Evaluate conditions in listed order, restoring before every condition. Disabled/values-permuted deltas are diagnostic counterfactuals, not retraining or proof of semantic storage. No intervention changes training.

## Outcomes and prespecified descriptive analysis

Primary unit is a learned B/M/O cell, paired to its B/O control. Define D = disabled NLL - enabled NLL, P = values-permuted NLL - enabled NLL, G = control NLL - enabled NLL, S = control NLL - disabled NLL. Verify G = D+S within 1e-12. D and P positive means that intervention worsens prediction; S separates the observed backbone difference from the final memory increment without identifying its training mechanism.

Report all 27 D/P/G/S values and raw condition NLLs, means, sample SDs, minima/maxima and sign counts. Cells are correlated through shared factors/data; no p-values, population confidence intervals or independence claim. For D and G separately, report mean at each level of each factor, each factor's marginal range (max minus min), and combined interaction RMS: sqrt(mean((Y - [grand_mean + B_effect + M_effect + O_effect])**2)), where each effect is its marginal mean minus the grand mean. This is a descriptive balanced-grid decomposition, not a variance-component estimate.

Predeclare descriptive flags (not promotion gates):

1. **Consistent dependence at this sensitivity:** mean D >=0.005 AND mean P >=0.005 AND at least 22/27 cells have BOTH D>0 and P>0.
2. **Heterogeneous useful dependence:** at least 3/27 cells have BOTH D>=0.005 and P>=0.005 AND at least 3/27 have D<=0 OR P<=0. Report overlap with flag 1 rather than forcing exclusive categories.
3. **Measured factor sensitivity:** for D, at least one marginal range or combined interaction RMS >=0.005. Name every qualifying factor/interaction; no claim about untested optimizer hyperparameters or longer training.

All flags may fail; preserve nulls. If heterogeneous dependence and factor sensitivity both occur, that supports sensitivity to the tested optimization inputs, not a universal optimization explanation. If consistent dependence occurs, this configuration shows useful memory across this grid on this panel; it still does not pass P1 retroactively. If D/P fail but G improves, report backbone/trajectory alternatives without choosing a cause. No possible outcome authorizes scaling automatically.

## Engineering gates, bounds and evidence

Before real training, test separate RNG factors/shared component identity; equal batch streams; dense-equivalent disabled-control updates and frozen memory; deterministic train/checkpoint resume; corruption/mismatched identity rejection; data panel selection/disjointness/hash checks; intervention restoration/permutation invariance; analytic decomposition on hand-computed fixtures. Run all existing tests, lint, typecheck and E0 smoke. Root reviews and reruns checks independently; Luna may independently audit Sol's code and artifacts. No scientific choices delegated to implementers.

Single CPU thread, 300 seconds and 2 GiB process-tree RSS per training+diagnostic cell; total worker suite limit 1800 seconds. Exclude human/GitHub reporting pauses from experiment runtime but record them if present. Use existing watchdogs, stop on nonfinite/correctness/resource failure, preserve failed and unexecuted cells. Do not rerun a scientific failure to replace an outcome; engineering fixes require recorded amendment before a fresh suite. No expensive services, GPU or infrastructure deployment.

Freeze code/config/spec/lock before execution. Results-only Git commits during the suite are allowed for requested tracking, but every cell must verify the identical source archive/config/spec/data hashes; record actual Git HEAD honestly. Capture per-run raw training/evaluation events, routing usage/gradient/movement, parameter counts, wall time, RSS, command, hardware/software, seed/order/permutation identities and checkpoint hashes. Preserve all binaries locally; push compact non-corpus/non-weight records after each completed training cell, including its diagnostic evaluations, and report that cell in chat. All binary checkpoints remain local under the existing data/rights policy. Keep partial evidence on failure. Final independent artifact audit precedes interpretation completion. Human merge/publication approval remains pending; Astra review NOT PERFORMED.
