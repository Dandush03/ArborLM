# Independent P5 engineering review

**Disposition:** engineering preflight passed for the reviewed P5 implementation and synthetic contracts. This is not scientific validation. Astra review was not performed.

## Verification

Commands run from the repository root:

```sh
uv run --no-sync ruff format tests/test_p5_independent_contract.py
uv run --no-sync ruff check tests/test_p5_independent_contract.py
uv run --no-sync ruff format --check tests/test_p5_independent_contract.py
uv run --no-sync pytest -q tests/test_p5_independent_contract.py
```

Results: Ruff check passed; Ruff format check reported `1 file already formatted`; the focused test file passed **36 tests**. Captured outputs are [luna-ruff.log](luna-ruff.log), [luna-ruff-format.log](luna-ruff-format.log), and [luna-focused-tests.log](luna-focused-tests.log). The test output has two benign warnings: optional NumPy is unavailable in the local environment, and a deliberately malformed optimizer fixture contains a duplicate parameter to verify rejection.

Root's independent data/parent and strict restore evidence is in [root-data-parent](root-data-parent/README.md) and [root-strict-restore](root-strict-restore/README.md). Root independently matched all 512 selected validation rows and P5 panel hash `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`, and verified all nine registered parent restores. The independent reconstruction is documented in [independent-data-parent-audit.md](independent-data-parent-audit.md). Its prior-use scan is a pre-freeze snapshot; the accompanying temporal caveat explains why replay against the current tree now finds P5's own manifests.

## Reviewed implementation

Read-only review covered `src/arborlm/hierarchy_ablation.py`, `p5_model.py`, `p5_config.py`, `p5_data.py`, `p5_parent.py`, `p5_checkpoint.py`, `p5_timing.py`, `p5_clock.py`, and `p5_analysis.py`, against ADR-0010 and the approved project protocol.

The independent synthetic tests cover:

- Baseline, flat, fixed-tree, learned-tree, and dense `_cell` paths, plus `_quality_suite` parent-baseline keying and one-time exclusive cell export.
- Exact backbone/addition parameter counts and optimizer membership/options, including split groups, wrong hyperparameters, duplicate and omitted parameters; fixed router buffer handling.
- Backbone parameters and nonpersistent causal mask immutability, fixed-router immutability, causal perturbation, tied output embedding, and gradient flow through the frozen suffix into a trainable addition.
- Shared fresh memory initialization across A/B/C for seeds 501–503 and across synthetic parents, including unchanged global RNG state.
- Uneven-batch token-weighted NLL with an independent float64 log-sum-exp/gather oracle and a known-logit 8+1 fixture; checkpoint restore, identity rejection, and corruption rejection.
- Intervention permutation domains, model/RNG/mode preservation on successful and exceptional evaluation, operand traces, schedule counts, and timing-state/RNG/mode/GC isolation on successful and exceptional runs.
- 22/27 and 8/9 strict-sign boundaries, all quality flags on a passing fixture, paired work arithmetic, all-27-pair latency reliability, INCONCLUSIVE behavior, positive durations, clock-resolution and round-stability limits.
- Earliest timing/combined deadline selection, charged quality finalization, single-use ACK behavior, and delayed invalid ACK exclusion.

Existing pilot tests already exercise stable top-k tie handling and the original memory lookup math; P5 tests validate the P5 variant wiring and independently inspect trace operands without duplicating those algorithms.

## Defects found and resolution

- The first runner snapshot exported each quality cell twice to the same exclusive destination. Sol removed the duplicate call; the synthetic `_quality_suite` test verifies each cell export occurs once.
- Earlier parent-map and flat-router accounting mismatches were corrected by Sol. The synthetic cell matrix exercises baseline parent-label lookup and flat-tree special cases.
- The optimizer validator initially compared flattened parameter membership only. Sol strengthened it to require one AdamW group with registered options plus exact, unique, ordered membership; the independent test checks invalid group splits and membership/options.
- ACK wait time was initially excluded before ACK content validation, so a delayed invalid ACK could reduce charged active time. Sol moved exclusion after successful validation. The independent regression asserts a delayed wrong-worker ACK leaves the wait charged; it passes on the final implementation.

The pre-fix delayed-ACK failures are retained in `experiments/review/p5-implementer/delayed-invalid-ack-before.log`; the focused post-fix results are in `experiments/review/p5-implementer/delayed-invalid-ack-after.log`. The earlier broader regression attempt, including the subsequently corrected mock-clock fixture, is retained at `experiments/review/p5-implementer/regression-attempt-01.log`. These are test/tooling records, not experiment outcomes.

## Limits

Synthetic tests execute model forwards on generated tensors only. No registered P5 dataset/model evaluation, training update, timing run, or real-data forward was run for this review. Root's full regression is a separate check and is not included in the 36-test result above. This review does not make an Astra or scientific-approval claim.
