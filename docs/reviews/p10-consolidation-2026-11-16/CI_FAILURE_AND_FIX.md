# P9-II / P10 consolidation — the CI failures and the fix (2026-11-16)

Written by the lead (Claude Fable 5.2). Astra review: NOT_PERFORMED.

## What failed

The Linux x86-64 CI job (`.github/workflows/e0-cpu.yml`, job `e0`) failed on every run of `claude/adr-0019-p9ii` (PR 7) and `claude/p10-design` (PR 8) with the same three tests and nothing else:

- `tests/test_p9ii_replay.py::test_replay_is_bit_identical_to_the_calibration_code[A0]`, `[A1]`, `[A2]`.

Runs read: 43714201168 (PR 7: 3 failed, 1,896 passed, 12 skipped, 20 min 31 s) and 43889270648 (PR 8: 3 failed, 1,896 passed, 12 skipped, 33 min 44 s). The tests compare SHA-256 digests of the per-update losses and of the trained parameters with digests recorded on the platform of record (macOS arm64). The Linux runner produced other digests, and different ones on the two runs (for A0 `46d76c91…` and `ae5f5a95…` against the recorded `61864022…`), so no fixed Linux value exists to compare with.

The job's limit was 45 minutes; PR 8 already used 33 min 44 s before the P10-S0 and P10-S2 tests are added.

## The fix, and who approved it

The standing rules forbid editing a completed study's tests without the human lead's approval. The lead proposed (1) making the three bit-for-bit assertions apply on the platform of record only, as the earlier consolidation did for two P9 tests (commit `4b932b2`), and (2) raising the CI time limit; or merging with CI red. The human lead, verbatim: "Yes, fix then merge".

1. `tests/test_p9ii_replay.py`: the replay still runs on every platform and must yield two SHA-256 digests; the comparison with the recorded digests is made on macOS only, and the test is reported as skipped elsewhere with the reason. Nothing changes on the platform of record: the three tests pass there as before. No study code, record or threshold is touched.
2. `.github/workflows/e0-cpu.yml`: `timeout-minutes` 45 → 120.

What this does not show: that P9-II's training is bit-reproducible on Linux. It is not; the record of P9-II is the macOS arm64 run.
