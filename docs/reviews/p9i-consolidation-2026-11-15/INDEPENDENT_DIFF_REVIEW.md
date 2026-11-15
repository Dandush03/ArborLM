# Independent review of the PR #6 integration diff (P9-I into `main`) — 2026-11-15 (UTC)

- **Reviewer:** Claude Opus 5.5 (model id `claude-opus-5-5`), launched as an independent reviewer. I am not the integration owner, did not open PR #6, and did not author any commit in it, the P9/P9-I code, the analyses or the records reviewed here.
- **Reviewed head:** `ecd5b87970776257e093ea50dc6a85eb64f74ace` (`origin/claude/adr-0017-design`). Base: `origin/main` = `30084fac4d6520c52bffef9fefd96a680d628eec`. Any later push changes the head and voids this review for the new commits.
- **Read-only:** I did not merge, push, commit, re-run CI, edit the PR or edit any tracked file. This file is new and uncommitted.
- **Environment:** macOS 27.2.1 arm64, worktree `.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, `uv run --locked` (torch 2.8.0, `BLAS_INFO=accelerate`), `gh` against `Dandush03/ArborLM`, system `python3 -I` for my own checks. My scripts are in the session scratchpad (not committed): `check_cells.py`, `check_cells2.py`.
- **Astra review: NOT_PERFORMED.** This is independent engineering review only. It is not Astra validation and it is not human approval.

## Verdict

**APPROVED AFTER the listed non-code change:** append the PR-body note proposed in §6 before merging, so that `CI_FAILURE_AND_FIX.md`'s statement "This limitation is stated in the pull request" becomes true and the stale counts are corrected. No code, test, record or ADR change is required. I found no blocking defect in the integration diff: CI is green on head `ecd5b87`, the fix touches tests, README wording and review records only, the merge commit is content-neutral, the diff is limited to P9/P9-I material plus the three shared files, and the registered result, attempt history and provenance are intact. Merge with a merge commit pinned to `ecd5b87` (for example `--match-head-commit ecd5b87970776257e093ea50dc6a85eb64f74ace`). Editing the PR body does not change the head; any push does, and voids this approval for the new commits. The unresolved items in §7 are for the consolidation receipt; none blocks the merge. This verdict is not human approval and not Astra validation.

## 1. CI on the PR head

- `gh pr checks 6`: one check, `e0`, **pass**, 17m43s. Workflow "E0 CPU", event `pull_request`, run **43678731935**, job **132704500317**, head `ecd5b87970776257e093ea50dc6a85eb64f74ace`, created 04:53:53Z, completed 05:11:40Z, conclusion `success`.
- From the job log (`gh run view 43678731935 --log`): ruff `All checks passed!`; mypy (`src/arborlm` only) `Success: no issues found in 85 source files`; pytest **`1737 passed, 12 skipped, 3 warnings in 1010.55s`**; E0 smoke recorded (`Recorded E0 smoke: …/experiments/E0-20261115T051123318751Z-…`).
- 1,737 = 1,735 passed in the first run + the 2 previously failing tests. Skips are unchanged at 12. Because the Linux run passed the off-darwin branch, the actual Linux differences are within 1e-6 (scores) and 1e-5 (logits, loss), and peak RSS is below 1.25 GiB. The exact Linux magnitudes are still not logged.
- `gh pr view 6`: `mergeStateStatus CLEAN`, `mergeable MERGEABLE`, head unchanged at `ecd5b87`.

The first run (43677006179, head `413d747`) is confirmed from its log, as recorded in `CI_FAILURE_AND_FIX.md`: `2 failed, 1735 passed, 12 skipped, 3 warnings in 1210.05s`. The failures were `tests/test_p9_model.py::test_chunked_equals_unchunked[flat]` at `assert torch.equal(s0.scores, s1.scores)` (line 137) and `tests/test_p9_sim.py::test_65536_slot_smoke_time_and_memory` with `assert 1138970624 < (1024 ** 3)` (line 718). Command used: `gh run view 43677006179 --log | grep -E "FAILED|passed|failed|AssertionError|assert "`.

## 2. The fix in `4b932b2`

**Scope.** `git show --stat 4b932b2` shows five files: `README.md` (1 line), `tests/test_p9_model.py`, `tests/test_p9_sim.py`, and two new review records (`CI_FAILURE_AND_FIX.md`, `INTEGRATION_LOG.md`). It does not touch `studies/`, `src/`, `configs/`, `results/`, any ADR or `.github/`. `git diff --stat 8261f22 origin/claude/adr-0017-design -- studies/ configs/ src/` is empty, so the frozen P9-I code identity (`studies/p9i/*.py` and the imported `studies/p9/*.py`) is byte-identical to the code that ran. `git diff --stat 326ab0d origin/claude/adr-0017-design -- results/` is empty. Between the run's own record commit `a1b4b39` and `326ab0d`, `results/p9i-run-attempt2-2026-11-15/` gained only `OUTCOME.md` and `c4_c8_comparison_output.txt`, and no file was modified.

**Is the rounding difference the expected cause? Reasoned from the code, not verified on Linux.**
- `ScalableMemory._top_flat` (`studies/p9/model.py` lines 357–369) computes `(q[start:start+rows] @ normalized.T) / TEMP` in row blocks. Chunking changes only the M dimension of a single sgemm. The inner dimension K = `key_width` = 16, and every output element is still one 16-term dot product of the same two vectors. The method is therefore mathematically identical, as the class docstring says. Bit equality also needs the BLAS to produce each row's dot product independently of M and of the row's position in the block. Accelerate on macOS arm64 evidently does. x86-64 BLAS builds (the Linux PyTorch wheels) choose micro-kernels, remainder handling and FMA/vector paths by shape, so a row can round differently in a 3-row block than in the full matrix. This is the known lack of batch invariance in GEMM, and it is a benign cause.
- Supporting evidence: the `learned_tree` parameter of the same test passed bit-for-bit on Linux. `_top_tree` scores each query with `torch.bmm(local, q.unsqueeze(-1))`, a per-row matrix-vector product whose shape does not depend on the block size. A failure confined to the GEMM path whose shape depends on the block is exactly what the batch-invariance explanation predicts. A real indexing defect (wrong slice, off-by-one at a block boundary) would instead change `selected` and `candidate_ids` or give O(1) score differences, and those assertions passed on Linux: they ran before the failing line and are still exact on every platform.
- **Could not verify:** the size of the Linux difference. pytest stopped at the first failing assertion, `torch.equal` reports no magnitude, and nobody logged one. It is also unknown whether `candidate_scores`, logits and loss differed in the first run. The new CI run is the only evidence that the 1e-6 / 1e-5 tolerances hold. I could not run Linux x86-64. The local Docker daemon is linux/aarch64, not the CI architecture, and would need a torch download, which I did not do.
- **Locally verified (macOS arm64):** `uv run --locked pytest tests/test_p9_model.py tests/test_p9_sim.py -q -k "chunked_equals_unchunked or 65536_slot_smoke"`: 3 passed, so the strict darwin branch still holds bit for bit.

**Tolerances.**
- Scores are cosines divided by `TEMP` = 0.2, so |score| ≤ 5. The float32 ulp is about 4.8e-7 at magnitude 4 and 2.4e-7 at magnitude 2. `atol=1e-6` therefore allows about 2–4 ulp at the top of the range. That is tight, still meaningful (any logic error is orders of magnitude larger), and does not hide defects. A residual flakiness risk remains: the worst-case reordering bound for a 16-term sum (about 16·u·5 ≈ 5e-6) exceeds 1e-6, so another BLAS or CPU could fail spuriously. A relative term (for example `rtol=1e-6`) would have been more principled. This is a suggestion, not a blocker. 1e-5 on logits and on the scalar loss is likewise small next to any real defect.
- The selections and candidate ids remain **exact** on all platforms, and that is the scientifically relevant property (which slots are read). Gradients were already compared with `assert_close(rtol=1e-5, atol=1e-9)` on every platform before this change.
- The 1.25 GiB RSS bound: the measured Linux figure is 1,138,970,624 bytes (1.061 GiB), so there is about 18% headroom. The unit conversion is correct (`ru_maxrss` × 1024 off darwin, bytes on darwin). The bound still catches a chunking regression, since an unchunked 32,768 × 65,536 float32 score matrix alone is 8 GiB. It would not catch a 15% growth on Linux. That is acceptable, because 1 GiB was never a registered threshold.
- `sys.platform == "darwin"` also covers Intel macOS, while the records speak of "macOS arm64". This is a minor imprecision.

**Legitimate or hiding?** It is a legitimate resolution. The assertions removed off-darwin were bit-identity claims about one numerical environment, not properties of the method. The method-level invariants (exact selections, exact candidates, near-equal values and gradients) are still tested everywhere. The repository README (lines 63–64, pre-existing) already says macOS and Linux are separate numerical environments and that no cross-platform bitwise match is promised.

**Is the limitation visible?**
- `CI_FAILURE_AND_FIX.md` states it ("bit-identical reproduction is claimed for the platform of record only") and also says "This limitation is stated in the pull request." **That is not currently true.** The PR #6 body does not mention the first CI failure, the fix or the platform limitation (its CI section says only "see the checks on this PR"). The PR body needs the appended note proposed in §6. `OUTCOME.md` and the run README do not mention it. They are frozen records and should not be edited, so the PR body and the consolidation receipt are the right places.
- **Provenance gap (not caused by this PR, cannot be fixed without editing records):** the registered P9-I manifests (`*_manifest.json` → `identity`) record config, spec and source hashes but **no OS, CPU architecture, hardware or torch version**. A recursive search of `results/p9i-*` for `darwin|arm64|macos|hardware` finds nothing. The "platform of record = macOS arm64" statement rests on the consolidation records and on the auditor's own environment line in `docs/reviews/p9i-results-2026-11-15/REVIEW.md`. The software is pinned by `uv.lock`. AGENTS.md asks for hardware to be recorded for every experiment. This belongs in the receipt as an unresolved limitation.
- Precision note: `CI_FAILURE_AND_FIX.md` says re-running "may differ at rounding level in the memory scores". For the **trained** registered results, a rounding-level difference in scores can flip a near-tied top-k selection and then diverge over 8,192 updates. A re-run on another platform could therefore differ by more than rounding. That does not touch the recorded results or the recomputation (which was on macOS), but the receipt should not promise rounding-level agreement off-platform.

## 3. The merge commit `ecd5b87`

- Parents: `4b932b2c…` and `30084fac…`. `git rev-parse ecd5b87^{tree} 4b932b2^{tree}` gives `e021f505fbddc09543ef177605273459c2530281` for both, so there is no content change.
- `git log --oneline 4b932b2..ecd5b87` lists only `ecd5b87` and `30084fa`, so the merge brings in only the PR #5 merge commit. Its second parent `afd62e5` was already an ancestor.
- No frozen commit was rewritten: `git merge-base --is-ancestor` is true for `da9d077`, `dd39aa6`, `dd8b205`, `8261f22`, `326ab0d`, `a1b4b39`, `dc88dab`, `0e0fbfb`, `32d72e9`, `c53acaa` and the ADR-0018 history commits `80155d6`, `649f76f`, `8e12f96`.

## 4. The integration diff

`git diff origin/main...origin/claude/adr-0017-design --stat` gives 480 files, 67,975 insertions and 1 deletion. `--name-status` gives 477 A and 3 M. The PR API agrees: `changed_files` 480, `commits` 34.
- **Modified (only):** `CLAUDE.md` (one line replaced, extending the ADR pointer list), `README.md` (+1 P9-I line), `docs/RESEARCH_LOG.md` (+13/−0). The single deletion is the replaced CLAUDE.md line.
- **RESEARCH_LOG is append-only:** 267 lines on `main`, 280 at the head, with the hunk beginning after line 267.
- **No change** to `src/`, `.github/`, `pyproject.toml`, `uv.lock` or `experiments/` (the grep returns none). No commit in `origin/main..head` touches `results/p1*`–`results/p8*`, `src/` or `experiments/`.
- **Configs:** only the new `configs/p9_diagnostics.toml` and `configs/p9i_interface.toml`. **Tests:** 32 new files (23 `test_p9_*`, 9 `test_p9i_*`); no pre-existing test changed.
- Everything else is P9/P9-I material: `studies/__init__.py`, `studies/p9/` (19), `studies/p9i/` (8), ADR-0017, ADR-0018, five `results/p9*` folders and 296 files under `docs/reviews/` (ADR-0017 and ADR-0018 design, P9 calibration audit, P9-I implementation, pre-freeze audit, results review, consolidation). Nothing unrelated is included. The largest added file is 91,943 bytes, and no checkpoints or corpus are included.
- **ADR-0018** is a 6-line withdrawn stub ("WITHDRAWN as a separate ADR … Never approved; nothing was implemented or run under it"), with an Astra label and pointers to its history.
- **CLAUDE.md line** is accurate against ADR-0017 §15.2, §15.7, §15.8 and §15.9 and the records: Lanes A–D calibration blocked; Part I executed once as attempt 2 after attempt 1 stopped at the gates before training; COMPLETE, NO_INTERFACE_SELECTED, accepted by the human lead.
- **README line** (as corrected in `4b932b2`) is accurate. I recomputed from `results/p9i-run-attempt2-2026-11-15/cells.csv`: 57 rows, all `completed`, all `matched_updates` = 8192. BB at 4,096 (B101) has accuracy 0.5435–0.6494 and is `INTERFACE_PARTIAL` in `classes.csv`; BB at 16,384 and 65,536 is `INTERFACE_FAILS`; all three are `LANGUAGE MODELLING DEGRADED`. No arm/size class is INTERFACE_WORKS.

## 5. Integrity of the science being merged

- **Status strings.** P9-I: `OUTCOME.md` "Study status: COMPLETE … Registered outcome: NO_INTERFACE_SELECTED", and `analysis.json` gives `status: COMPLETE`. P8 on `main` (via PR #5): ADR-0015 reads "STUDY INCOMPLETE (55 of 60 cells simulated); NO CASE LOCALITY-POSITIVE … PENDING HUMAN REVIEW"; the RESEARCH_LOG entry reads "INCOMPLETE with decision `none`". This PR does not change either.
- **My recomputation from raw `cells.csv`** (scripts `check_cells.py` and `check_cells2.py`, run with `python3 -I <script> results/p9i-run-attempt2-2026-11-15/cells.csv`): every B101 accuracy range in the OUTCOME/PR table matches after rounding to the printed precision (for example R1 65,536: 0.9674–0.9720; D7 16,384: 0.7828–0.8021, B102 0.4393; BB-0 4,096: 0.0835–0.0889). The BB-family LM rise is 0.6706–0.9981 and the after-loss 3.925–4.694 nats, which matches "67–100%" and "3.92–4.69".
- **Discrepancy that was my own mistake:** my first script grouped B101 and B102 rows together, and it took the LM rise over arm `BB` only (giving 0.688–0.901). Both were scope errors on my side. The OUTCOME table is B101-only, and "BB arms" there includes BB, BB-0 and BB-D. With the correct scope there is no difference. Kept as `check_cells.py` (first attempt) and `check_cells2.py`.
- **Records present.** Attempt 1 is `results/p9i-run-attempt1-2026-11-14/` (README, ADDENDUM, gates, g1, ledger, the lead's diagnostic); attempt 2 is `results/p9i-run-attempt2-2026-11-15/`; calibration is in `results/p9i-calibration-2026-11-14/` and `results/p9-calibration-2026-11-14/`; rehearsal is in `results/p9i-rehearsal-2026-11-14/`. **Opus reviews present:** `adr-0017-design-2026-11-14/` (REVIEW, RECHECK, CONFIRM), `adr-0018-design-2026-11-14/` (REVIEW, CONFIRM), `p9-calibration-audit-2026-11-14/AUDIT.md`, `p9i-prefreeze-audit-2026-11-14/` (AUDIT, RECHECK, GATE_FIX_AUDIT, FINAL_RECHECK, scripts, and outputs including attempts marked `FAILED_auditor_bug`), `p9i-results-2026-11-15/REVIEW.md` with scripts and outputs, and `p9i-consolidation-2026-11-15/INTEGRATION_AUDIT.md`.
- **Human decisions recorded verbatim** in ADR-0017 §15.2, §15.3, §15.7 and §15.9 (the §15.9 acceptance is quoted). §15.5, §15.6 and §15.8 are freeze and delegated-decision records.
- **Exploratory labelling.** OUTCOME ("diagnostic, not registered results"), REVIEW §2.3 and §104–110, the PR body and the README all mark address collapse and W7 draw sensitivity as exploratory or diagnostic.
- **Astra labels.** "Astra review: NOT_PERFORMED" appears in every P9-I results README, OUTCOME, every Opus review, ADR-0018, ADR-0017 §15.9 and the consolidation records. `results/p9-calibration-2026-11-14/README.md` has no Astra line, but it is marked "Lead's reading (not audited)", and ADR-0017's status line carries "SPEC: PENDING ASTRA REVIEW". This is minor and needs no edit, since the folder is frozen.

## 6. The PR description

It is accurate on the science (outcome, table, May / May not, attempt history, exploratory section, Lanes A–D, ADR-0018, P8 status, CI coverage gaps, Astra status, unresolved decisions), and limitations are prominent. It is **stale** after `4b932b2` and `ecd5b87`:
1. "478 files … 475 added" is now 480 files, 477 added (the two new consolidation records); "reviews … 294 files" is now 296.
2. "32 commits, no merge commits, no P8 commit" is now 34 commits, including one merge commit (`ecd5b87`) that brings in the `main` merge commit `30084fa`.
3. The first CI failure, the test-only fix and the platform limitation are absent, although `CI_FAILURE_AND_FIX.md` says they are stated in the PR.
4. "that review has not yet happened" will be superseded by this file.

**Proposed text to append (not replace) to the PR body:**

> ## Update before merge (2026-11-15 UTC): first CI failure, test-only fix, and platform of record
>
> - The first CI run on this PR (43677006179, head `413d747`, Linux x86-64) failed: `2 failed, 1735 passed, 12 skipped`. `tests/test_p9_model.py::test_chunked_equals_unchunked[flat]` found the memory scores computed in row blocks not bit-identical to the unblocked computation (selections and candidate ids identical), and `tests/test_p9_sim.py::test_65536_slot_smoke_time_and_memory` measured peak RSS 1,138,970,624 bytes against a 1 GiB bound. This was the first CI run on any P9 commit.
> - Fix `4b932b2` (tests, README wording and review records only; no file under `studies/`, `src/`, `configs/`, `results/` or any ADR changed): on macOS the two assertions are unchanged (bit for bit; 1 GiB). Elsewhere, selections and candidates stay exact, scores and candidate scores must agree within 1e-6, logits and loss within 1e-5 (absolute), and the RSS bound is 1.25 GiB. Record: `docs/reviews/p9i-consolidation-2026-11-15/CI_FAILURE_AND_FIX.md`.
> - **Platform limitation:** every P9/P9-I calibration, rehearsal, registered run and independent recomputation was made on macOS arm64. Bit-identical reproduction is claimed for that platform only. On another platform the memory scores may differ at rounding level, and a re-run of training may then diverge further. The registered manifests do not themselves record the OS or hardware.
> - `ecd5b87` merges `origin/main` (`30084fa`, the PR #5 merge commit) into this branch, with a tree identical to `4b932b2`. The PR now has 34 commits including that one merge commit, and 480 files (477 added, 3 modified).
> - Independent review of the integration diff (Opus 5.5, not the integrator): `docs/reviews/p9i-consolidation-2026-11-15/INDEPENDENT_DIFF_REVIEW.md`. Not Astra validation and not human approval. Astra review: NOT_PERFORMED.

## 7. Blockers and unresolved limitations for the consolidation receipt

**Blocking:** none.

**Not blocking, to record in the receipt as unresolved:**
1. ADR-0015 (P8) status line still reads "PENDING HUMAN REVIEW". The PR #5 approval answered question 1 only (`HUMAN_APPROVAL.md`).
2. The pre-rewrite P8 commit `80f46ae` (the P8 freeze, cited in P8 records) exists only on the local branch `backup/p8-before-single-line-rewrite`. `git ls-remote origin` shows no backup ref. Loss of this machine loses it; its preservation is a human decision (question 3, unanswered).
3. ADR-0017's status line predates §15.9 (it still reads "attempt 2 is approved" and defers the outcome to `results/`). It is stale, not false.
4. The ADR-0017 §I.3.2 optimizer clause ("row-lazy Adam at 0.012") was corrected **in place** in human-approved text after the Part I decision and before freeze 1, disclosed as §15.4. The approved wording survives only in git history. PENDING LEAD REVIEW / human acknowledgement.
5. CI mypy covers `src/arborlm` only (`.github/workflows/e0-cpu.yml` line 26); `studies/` and `supplements/` are not type-checked in CI.
6. Data-dependent tests skip in CI (12 skipped in CI against 6 in the clean local clone; CI runs `pytest -q` and does not print skip reasons). Evidence for those paths is local only.
7. `tests/test_run_records.py::test_watchdog_kills_timed_out_child_and_saves_logs` is intermittent on macOS (`PermissionError`, once). The cause is not established; it is a `main` test, unchanged here.
8. Bit-identical reproduction is claimed for macOS arm64 only, and the registered manifests do not record OS, hardware or torch version (§2).
9. `results/p9-calibration-2026-11-14/README.md` carries no "Astra review: NOT_PERFORMED" line (frozen; minor).
10. The tolerance in the off-darwin branch is absolute-only and tight (about 2–4 ulp at |score| ≈ 5). It could flake on another BLAS; a future relative tolerance would be more robust. This is an engineering suggestion and needs an approved change to a test file.
11. `ADR-0012` (governance) is not approved; the role split used here is proposed only.

## 8. What I ran (all from the worktree root)

```sh
git fetch origin; git rev-parse HEAD origin/main
gh pr view 6 --json headRefOid,state,mergeable,baseRefName,title,body
gh pr checks 6; gh run view 43678731935 …; gh run view 43677006179 --log | grep …
git show --stat 4b932b2; git show 4b932b2 -- tests README.md …
git rev-parse ecd5b87^{tree} 4b932b2^{tree}; git log --oneline 4b932b2..ecd5b87
git diff origin/main...origin/claude/adr-0017-design --stat | --name-status | -- CLAUDE.md README.md docs/RESEARCH_LOG.md
git diff --stat 8261f22 origin/claude/adr-0017-design -- studies/ configs/ src/
git diff --stat 326ab0d origin/claude/adr-0017-design -- results/
git diff --name-status a1b4b39 326ab0d -- results/p9i-run-attempt2-2026-11-15
git merge-base --is-ancestor <commit> origin/claude/adr-0017-design   # for each commit listed in §3
git branch -a --contains 80f46ae; git ls-remote origin | grep -i backup
gh api repos/Dandush03/ArborLM/pulls/6 -q '.changed_files,.commits'
uv run --locked pytest tests/test_p9_model.py tests/test_p9_sim.py -q -k "chunked_equals_unchunked or 65536_slot_smoke"
python3 -I <scratchpad>/check_cells.py  results/p9i-run-attempt2-2026-11-15/cells.csv
python3 -I <scratchpad>/check_cells2.py results/p9i-run-attempt2-2026-11-15/cells.csv
```

**Not verified:** behaviour on Linux x86-64 beyond what CI reports; the magnitude of the first run's Linux score difference; the full local pytest suite (I ran only the two changed tests); any registered stage (not re-run, by rule); the scientific content of the Opus reviews beyond the spot recomputation above.

This review is not human approval and not Astra validation. Astra review: NOT_PERFORMED.
