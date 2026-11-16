# Consolidation receipt: P8 and P9-I into `main` (Task 0.3)

- **Integration owner:** Claude Opus 5.5 (model id `claude-opus-5-5`). Engineering record only. **Not Astra validation and not human approval. Astra review: NOT_PERFORMED** (for P8, the P8 supplement, P9 and P9-I alike).
- **Date:** 2026-11-15 (UTC). Repository `Dandush03/ArborLM`.
- **Human approvals used:**
  - PR #5 merge: the human lead answered "approved" in chat. The lead recorded it with a narrow reading in `docs/reviews/p9i-consolidation-2026-11-15/HUMAN_APPROVAL.md`. Only question 1 (un-draft PR #5 and merge it with a merge commit pinned to `afd62e5`) was answered; questions 2 (closing the P8 review) and 3 (preserving `80f46ae`) were not.
  - PR #6 (P9-I) merge: authorized by the mission text (Task 0.2), conditional on CI, integrity checks and an independent review of the integration diff. Those conditions are met in rows 7 and 9 of the table below.
- Companion records in this folder: `INTEGRATION_AUDIT.md`, `INTEGRATION_LOG.md` (committed at `4b932b2`), `INTEGRATION_LOG_PART2.md`, `CI_FAILURE_AND_FIX.md`, `INDEPENDENT_DIFF_REVIEW.md`. At the time of writing, this receipt, `INTEGRATION_LOG_PART2.md` and `INDEPENDENT_DIFF_REVIEW.md` are **not yet committed**; the lead will commit them on the next branch cut from `main`.

## 1. Merge order and SHAs

| # | Step | Value |
|---|---|---|
| 1 | `main` before | `57be5ff4e5e0ed319da90bcb2ac161bc6574e709` (merge of PR #4, P7-B) |
| 2 | PR #5, https://github.com/Dandush03/ArborLM/pull/5 (P8, ADR-0015 and ADR-0016 supplement) | head `afd62e5d5ab39c86fbd3403d75001edf1d8e9867`; body appended "Update before merge (2026-11-15)" at 04:16:03; `gh pr ready 5` at 04:16:09; `gh pr merge 5 --merge --match-head-commit afd62e5d5ab39c86fbd3403d75001edf1d8e9867` at 04:16:13 |
| 3 | PR #5 merge commit (M1) | **`30084fac4d6520c52bffef9fefd96a680d628eec`**; parents `57be5ff…`, `afd62e5…`; tree `a36e363b6b9164c6d2cff209b5784e56a8c09866` = tree of `afd62e5` |
| 4 | PR #6, https://github.com/Dandush03/ArborLM/pull/6, "P9-I (ADR-0017 Part I): query-interface prerequisite — registered negative result NO_INTERFACE_SELECTED" | opened 04:29:40 (not draft) at head `413d747…`; the lead later pushed `4b932b2` (test-only fix and records) and `ecd5b87` (merge of `origin/main` into the branch, no content change). Final head **`ecd5b87970776257e093ea50dc6a85eb64f74ace`**, 34 commits (one of them a merge), 480 files |
| 5 | PR #6 body | appended "Update before merge (2026-11-15 UTC)" at 05:13:24: the first CI failure, the test-only fix, the macOS arm64 platform limitation, corrected counts, and the independent review's approval |
| 6 | PR #6 merge | `gh pr merge 6 --merge --match-head-commit ecd5b87970776257e093ea50dc6a85eb64f74ace` at 05:13:30; merged 05:13:32 |
| 7 | PR #6 merge commit (M2) = **resulting `main`** | **`587746889d1ce3159bf879e134ceaebd26272518`**; parents `30084fa…`, `ecd5b87…`; tree `e021f505fbddc09543ef177605273459c2530281` = tree of `ecd5b87` (and of `4b932b2`) |
| 8 | Branches | none deleted. `claude/p8-locality-aware-training` is still at `afd62e5…` and `claude/adr-0017-design` is still at `ecd5b87…` on GitHub. No force-push, squash, rebase or `--admin`. `main` has no branch protection (HTTP 404), so nothing was bypassed |
| 9 | Independent integration review | Claude Opus 5.5, a separate context (not the integrator), `INDEPENDENT_DIFF_REVIEW.md`, reviewed head `ecd5b87`: **APPROVED AFTER** the PR-body note (row 5), which was applied before merge |

## 2. Original experimental commits (unchanged and reachable from `main` = `5877468`)

Checked with `git merge-base --is-ancestor <c> origin/main`:

| Commit | Role | On `main` |
|---|---|---|
| `378aeac1f6d1b8a36b4956984b312247cf1b45a6` | P8 freeze as pushed (records cite `80f46ae`, same tree `b13a9f9c…`) | yes |
| `3018126db5f8bed740813bc6722fe2319e31024c` | P8 supplement (ADR-0016) freeze | yes |
| `afd62e5d5ab39c86fbd3403d75001edf1d8e9867` | PR #5 head (P8 + supplement outcome) | yes |
| `da9d077` | P9-I freeze 1 | yes |
| `dd8b205` | P9-I code, attempt 1 | yes |
| `0e0fbfb` | P9-I gate harness fix | yes |
| `8261f22` | P9-I code, attempt 2 | yes |
| `dd39aa6` | P9-I freeze 2 (attempt 2) | yes |
| `a1b4b39` | P9-I attempt 2 records as written by the run | yes |
| `326ab0d` | P9-I outcome and Opus recomputation | yes |
| `dc88dab` | ADR-0017 §15.9 human acceptance | yes |
| `4b932b2`, `ecd5b87` | consolidation fix and merge of `main` into the branch | yes |
| `80f46aec96d3474a18f811ea77e68aa782b787f6` | P8 freeze **as cited in records** (before the history rewrite) | **no**: only on the local branch `backup/p8-before-single-line-rewrite`; mapped to `378aeac` in `docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md` |

## 3. CI runs (workflow "E0 CPU", job `e0`)

| Run | Event / head | Result |
|---|---|---|
| 43607178425 | `pull_request`, PR #5 head `afd62e5` | success: ruff pass; mypy `src/arborlm` 85 files pass; pytest 868 passed, 9 skipped; E0 smoke |
| 43676025579 | `push` to `main`, M1 `30084fa` | success: ruff pass; mypy pass; pytest 868 passed, 9 skipped (722 s); E0 smoke |
| 43677006179 | `pull_request`, PR #6 head `413d747` | **failure**: ruff pass, mypy pass, pytest **2 failed**, 1,735 passed, 12 skipped. The failing tests were `test_p9_model.py::test_chunked_equals_unchunked[flat]` (row-blocked scores not bit-identical on Linux x86-64) and `test_p9_sim.py::test_65536_slot_smoke_time_and_memory` (peak RSS 1,138,970,624 B against a 1 GiB bound). Not re-run. Record: `CI_FAILURE_AND_FIX.md` |
| 43678731935 | `pull_request`, PR #6 head `ecd5b87` (after the test-only fix `4b932b2`) | success: ruff pass; mypy pass; pytest 1,737 passed, 12 skipped; E0 smoke |
| 43680155917 | `push` to `main`, M2 `5877468` | success (job `e0` id 132708813701): ruff pass; mypy `src/arborlm` 85 files pass; pytest 1,737 passed, 12 skipped, 3 warnings in 1029.72 s; E0 smoke recorded |

## 4. File and diff integrity

- **Whole consolidation** (`git diff --name-status 57be5ff origin/main`): 1,365 paths, of which 1,362 were added and 3 modified (`CLAUDE.md`, `README.md`, `docs/RESEARCH_LOG.md`). Nothing was deleted or renamed. `git rev-list --count 57be5ff..origin/main` = 54 commits: 18 from P8, M1, 34 from PR #6, and M2.
- **`src/arborlm/`:** 9 files added (the P8 modules from PR #5); no existing file modified.
- **`pyproject.toml`, `uv.lock`, `.github/`:** unchanged (`git diff --quiet 57be5ff origin/main -- pyproject.toml uv.lock .github`).
- **PR #6 diff** (three-dot against M1): 480 files (477 added, 3 modified). No change under `src/`, `.github/` or `supplements/`, and none to `pyproject.toml` or `uv.lock`. `configs/` only gained `p9_diagnostics.toml` and `p9i_interface.toml`. Tests only gained 23 `test_p9_*` and 9 `test_p9i_*` files; no pre-existing test changed. `docs/RESEARCH_LOG.md` is append-only. No checkpoints or corpus files were added; the largest file is 91,943 bytes. The GitHub file list (`gh api …/pulls/6/files`) matched the local diff at head `413d747`, and the reviewer re-counted at `ecd5b87` (API: 480 files, 34 commits).
- **Fix after the first CI failure** (`4b932b2`): touches only `tests/test_p9_model.py`, `tests/test_p9_sim.py`, the README P9-I line and two review records. `git diff --stat 8261f22 ecd5b87 -- studies configs src` is empty (reviewer), so the P9-I code that ran is byte-identical on `main`. `git diff --stat 326ab0d ecd5b87 -- results/` is empty (reviewer).
- **Files present on `main`:** ADR-0015, ADR-0016, ADR-0017 (with §15.9), the ADR-0018 withdrawn stub; `results/p8-2026-11-14/`, `results/p8-supplement-2026-11-14/`, `results/p9-calibration-2026-11-14/`, `results/p9i-calibration-2026-11-14/`, `results/p9i-rehearsal-2026-11-14/`, `results/p9i-run-attempt1-2026-11-14/`, `results/p9i-run-attempt2-2026-11-15/`; reviews `adr-0017-design`, `adr-0018-design`, `p8-{spec-review,preflight,results,results-audit}`, `p8-supplement-{spec-review,preflight,results-audit}`, `p9-calibration-audit`, `p9i-{implementation,prefreeze-audit,results}`, `p9i-consolidation` (with `HUMAN_APPROVAL.md`, `INTEGRATION_AUDIT.md`, `INTEGRATION_LOG.md`, `CI_FAILURE_AND_FIX.md`). `INDEPENDENT_DIFF_REVIEW.md`, this receipt and `INTEGRATION_LOG_PART2.md` are not on `main` yet.

## 5. Recorded study statuses on `main` (read from `origin/main` after M2)

- **P9-I: COMPLETE — NO_INTERFACE_SELECTED.**
  - `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`: "Study status: COMPLETE. 57 of 57 cells …" and "Registered outcome: NO_INTERFACE_SELECTED (§I.8.3 step 4)".
  - `results.json`: `status` COMPLETE, `selection.outcome` NO_INTERFACE_SELECTED, step 4.
  - The human lead accepted it as a registered negative result (ADR-0017 §15.9).
  - Attempt 1 (`results/p9i-run-attempt1-2026-11-14/README.md`): "stopped at the gates stage", nothing trained.
- **P8: INCOMPLETE.**
  - `results/p8-2026-11-14/SUMMARY.md`: "Study status: INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE."
  - `analysis.json`: `study_status` INCOMPLETE, 60 cells expected, 55 complete, `section_8_option_indicated` `none`.
  - ADR-0015 status line unchanged ("… STUDY INCOMPLETE (55 of 60 cells simulated); NO CASE LOCALITY-POSITIVE … PENDING HUMAN REVIEW").
  - The ADR-0016 supplement is labelled separately ("The registered P8 study remains INCOMPLETE with decision `none`").
- ADR-0017 Lanes A–D: calibration blocked (§15.2); nothing has run under them. ADR-0018: withdrawn, never approved.

## 6. Unresolved governance and scientific limitations

1. **ADR-0015 (P8) status line still reads "PENDING HUMAN REVIEW".** The human approval to merge PR #5 was recorded narrowly (question 1 only) and did not close the P8 review (question 2 unanswered).
2. **`80f46ae`, the P8 freeze cited in the P8 records, exists only on the local branch `backup/p8-before-single-line-rewrite`**, together with the other pre-rewrite hashes. It is not on GitHub (`git ls-remote origin` has no backup ref). It can be resolved only through `COMMIT_MAP.md`, where the tree is identical to `378aeac`. Preserving it is a human decision (question 3 unanswered).
3. **ADR-0017's status line is stale.** It predates §15.9: it still says attempt 2 is approved and defers the outcome to `results/`. It is stale, not false.
4. **In-place correction of approved text (ADR-0017 §15.4).** The BB optimizer clause in §18 (§I.3.2, "row-lazy Adam at 0.012") was corrected in place after the human Part I decision and before freeze 1, and was disclosed as §15.4. The approved wording survives only in git history. PENDING LEAD REVIEW / human acknowledgement.
5. **CI mypy covers `src/arborlm` only.** `studies/` and `supplements/` are not type-checked in CI. Locally they pass with `MYPYPATH=src`, and fail without it because of the missing `py.typed`.
6. **12 tests skip in CI** (6 in a clean local clone). Most need the git-ignored `experiments/` data or the optional `matplotlib`. CI does not print skip reasons. Evidence for the data-dependent paths is local only.
7. **Intermittent watchdog test.** `tests/test_run_records.py::test_watchdog_kills_timed_out_child_and_saves_logs` (a `main` test, unchanged) failed once on macOS with `PermissionError: [Errno 1] Operation not permitted` and has passed on every run since. The cause is not established.
8. **Bit-identical reproduction is claimed for macOS arm64 only.** Every P9/P9-I calibration, rehearsal, registered run and recomputation ran there. On Linux x86-64 the row-blocked memory scores differ at rounding level (first CI run). A re-run of training on another platform may diverge by more than rounding, because a near-tied top-k selection can flip. **The registered manifests do not record the OS, CPU architecture, hardware or torch version**, even though AGENTS.md asks for hardware to be recorded. The platform of record rests on the consolidation records and the reviewers' environment lines.
9. The off-darwin tolerances added in `4b932b2` are tight absolute tolerances (1e-6 on scores, about 2–4 ulp at |score| ≈ 5) and could fail spuriously on another BLAS. A relative tolerance would need an approved change to the test. The Linux magnitudes were never logged. Engineering note from the reviewer.
10. **`results/p9-calibration-2026-11-14/README.md` has no "Astra review: NOT_PERFORMED" line.** The folder is frozen and the issue is minor; it is labelled "Lead's reading (not audited)".
11. **ADR-0012 (governance) is not approved.** The role split used in this consolidation is proposed only.
12. **Astra review: NOT_PERFORMED** throughout: P8, the P8 supplement, P9 calibration and P9-I. No result is Astra validated. No result in this consolidation is a success claim.
13. `INDEPENDENT_DIFF_REVIEW.md`, this receipt and `INTEGRATION_LOG_PART2.md` are uncommitted. The PR #6 body cites `INDEPENDENT_DIFF_REVIEW.md`, which is not yet on `main`.

Astra review: NOT_PERFORMED.
