# P9-II / P10 consolidation — independent review of the integration change (2026-11-16)

- **Reviewer:** Claude Opus 5.5 (`arbor-auditor`), a separate context from the integrator. Written up by the lead (Claude Fable 5.2) from the reviewer's report. Independent engineering review; not Astra validation and not human approval. Astra review: NOT_PERFORMED.
- **Reviewed:** commit `8d4c168` and head `34fe829` of `claude/p10-design` (PR 8), and the merge plan for PRs 7, 8, 9 and 10.
- **Verdict: APPROVE WITH NOTES.**

## Findings

1. **The test edit weakens nothing on the platform of record.** On macOS arm64 the full bit-for-bit comparison still runs (`tests/test_p9ii_replay.py`; 3 passed). Elsewhere the replay runs to completion and the test is reported as skipped, not passed (CI run 43957626136: `sss`, 1,896 passed, 15 skipped; 12 skipped before). **Note (low):** `sys.platform == "darwin"` also matches Intel macOS, which is untested and would probably give other digests; that would be a loud failure, never a false pass. The record is: macOS arm64 only; Intel macOS untested.
2. **`CI_FAILURE_AND_FIX.md` is accurate** (checked against the failed runs' logs: 3 failed, 1,896 passed, 12 skipped, 20 min 31 s and 33 min 44 s; the A0 digests quoted). **Addition:** `git diff 2bc8038 071fd2d -- studies/p9 studies/p9ii src` is empty, so the two Linux runs gave different digests from identical code: the Linux runner is not reproducible run to run, not only different from macOS.
3. **No other change.** `8d4c168` touches four files and `34fe829` one documentation file; no study code, record, threshold or ADR of a completed study is altered.
4. **The merge order is sound.** PR 7's head is an ancestor of PR 8's; the design, S0 and S2 branches change no file in common. In the S0 and S2 tests the reviewer found no assertion expected to fail on Linux (MPS tests are guarded; memory units are corrected; hard-coded hashes are of committed files or downloads, not trained values). **Notes (medium):** the lead's local merged-tree run (2,913 passed, 7 skipped) used the S0 head before its lint-settings fix (`b4feb4e`), so it does not cover that commit, which changes no code; and the S0 and S2 pull requests must have `main` merged into them (for the CI fix and the 120-minute limit) and pass CI before they are merged.
5. **Nothing merged depends on P10-S1,** which is not merged now.

## Not checked

The full test suite (by instruction), the Linux run time of the S0 and S2 tests, Intel macOS, and the content of the four studies themselves.
