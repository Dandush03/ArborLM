# P9-I consolidation: integration log (Phase 0, Tasks 0.2 steps A–D)

- **Integration owner:** Claude Opus 5.5 (model id `claude-opus-5-5`), continuing from `INTEGRATION_AUDIT.md` in this folder. Engineering record only. **It is not Astra validation and not human approval. Astra review: NOT_PERFORMED.**
- **Authority used:** `HUMAN_APPROVAL.md` in this folder (question 1 only: un-draft and merge PR #5 with a merge commit pinned to `afd62e5`); the mission text for opening the P9-I PR. Questions 2 and 3 were not answered and nothing was done for them: ADR-0015's status line is untouched, `80f46ae` and the local backup branches were not pushed (`git ls-remote --heads origin | grep -c backup` → 0).
- **Environment:** macOS (Darwin 27.2.0, arm64); worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design` at `413d74788ed5d49764f4bfcd240fd6fb13fb2549` (equal to GitHub); `gh` authenticated as the repository owner. All times UTC, 2026-11-15.
- **Not done:** no merge of the P9-I PR (step E), no force-push, squash, rebase, `--admin`, branch deletion, commit, tag or push from this worktree; no edit of any existing file. This file is new and uncommitted.

## 1. Pre-checks (read-only), 04:15

| Check | Result |
|---|---|
| `git fetch origin`; `git rev-parse origin/main origin/claude/p8-locality-aware-training` | `57be5ff4e5e0ed319da90bcb2ac161bc6574e709`, `afd62e5d5ab39c86fbd3403d75001edf1d8e9867` |
| `git ls-remote --heads origin` | `claude/adr-0017-design` = `413d747…`; no backup branch on GitHub |
| `gh pr view 5 --json …` | OPEN, draft, head `afd62e5d5ab39c86fbd3403d75001edf1d8e9867`, `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` |
| `gh pr checks 5`; `gh run view 43607178425 --json headSha,conclusion,event` | `e0` pass; run on `afd62e5d…`, event `pull_request`, success. Log: ruff "All checks passed!", mypy "Success: no issues found in 85 source files", pytest "868 passed, 9 skipped, 3 warnings in 434.83s" |
| `gh api repos/Dandush03/ArborLM/branches/main/protection` | HTTP 404 "Branch not protected" (nothing to bypass) |
| `gh pr list --state open` | only #5 |

## 2. Commands that changed GitHub state

| # | Time | Command | Result |
|---|---|---|---|
| 1 | 04:16:03 | `gh pr edit 5 --body-file …/scratchpad/integration/pr5_body_after.md` | exit 0. The original body (5,566 bytes, saved as `…/pr5_body_before.md`) is kept byte-for-byte as the prefix; a section **"Update before merge (2026-11-15)"** is appended: CI counts 868 passed / 9 skipped on `afd62e5` (run 43607178425); ADR-0016 supplement scope (`supplements/p8s/`, `tests/test_p8s_*.py`, `results/p8-supplement-2026-11-14/`, `docs/reviews/p8-supplement-*`, `HUMAN_DECISION.md`, `COMMIT_MAP.md`); `make_report.py` fix `d47a9fd` is +4/−1, not one line; `80f46ae` → `378aeac` (tree `b13a9f9c…`) with `COMMIT_MAP.md`, `80f46ae` not on GitHub; human approval reference and its narrow reading; P8 stays INCOMPLETE (55/60), decision `none`, no LOCALITY-POSITIVE; Astra review NOT_PERFORMED. Re-read with `gh pr view 5 --json body`: identical apart from one trailing blank line |
| 2 | 04:16:09 | `gh pr ready 5` | "marked as ready for review"; afterwards `isDraft false`, head `afd62e5…`, MERGEABLE, CLEAN |
| 3 | 04:16:13 | `gh pr merge 5 --merge --match-head-commit afd62e5d5ab39c86fbd3403d75001edf1d8e9867` | exit 0; `state MERGED`, `mergedAt 2026-11-15T04:16:15Z`, merge commit **`30084fac4d6520c52bffef9fefd96a680d628eec`**. Branch not deleted (`claude/p8-locality-aware-training` still at `afd62e5…` on GitHub) |
| 4 | 04:29:40 | `gh pr create --base main --head claude/adr-0017-design --title "P9-I (ADR-0017 Part I): query-interface prerequisite — registered negative result NO_INTERFACE_SELECTED" --body-file …/scratchpad/integration/p9i_pr_body.md` (not draft) | **PR #6**, https://github.com/Dandush03/ArborLM/pull/6, head `413d74788ed5d49764f4bfcd240fd6fb13fb2549`. Posted body equals the file apart from a trailing newline; no @-mention (`grep -c '@'` → 0); last line is the Claude Code line |

Opening PR #6 started CI automatically (event `pull_request`); I did not re-run any job.

## 3. PR #5 merge verification

| Check | Result |
|---|---|
| `git fetch origin`; `git rev-parse origin/main` | `30084fac4d6520c52bffef9fefd96a680d628eec` (new `main`) |
| `git log -1 --format=%P%n%s 30084fa` | parents `57be5ff4e5e0ed319da90bcb2ac161bc6574e709` `afd62e5d5ab39c86fbd3403d75001edf1d8e9867`; "Merge pull request #5 from Dandush03/claude/p8-locality-aware-training" |
| `git rev-parse 30084fa^{tree} afd62e5^{tree}` | both `a36e363b6b9164c6d2cff209b5784e56a8c09866` (equal; also equal to the simulated merge-1 tree in the audit §5) |
| `git diff --quiet 57be5ff origin/main -- pyproject.toml uv.lock .github` | unchanged |
| Push-to-main CI: `gh run list --branch main`, `gh run view 43676025579` | run **43676025579**, workflow "E0 CPU", event `push`, head `30084fa…`, job `e0` (id 132696245825): **success**. Log: ruff "All checks passed!"; mypy "Success: no issues found in 85 source files"; pytest "868 passed, 9 skipped, 3 warnings in 722.06s"; E0 smoke recorded |
| `origin/main` status strings | `results/p8-2026-11-14/SUMMARY.md` on `origin/main`: "Study status: INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE."; P8 `analysis.json` `study_status` INCOMPLETE, option `none`; ADR-0015 status line unchanged ("… PENDING HUMAN REVIEW") |

## 4. P9-I PR range (step B)

- `git rev-list --count origin/main..origin/claude/adr-0017-design` → **32** = the 31 audited (`e46d5f8` … `dc88dab`) + `413d747` (audit, human approval, CLAUDE.md/README pointers). `git rev-list --merges --count` → 0. `git rev-list --count afd62e5..dc88dab` → 31.
- No P8 commit in the range: every commit of `57be5ff..afd62e5` checked against `origin/main..origin/claude/adr-0017-design`; none present.
- `gh pr view 6 --json commits --jq '.commits|length'` → 32. `changedFiles` 478, `additions` 67,832, `deletions` 1. `mergeable MERGEABLE`; `mergeStateStatus` was `UNSTABLE` while CI was pending.

## 5. CI on PR #6 (step C)

**BLOCKER: CI FAILED on the PR head.** Run **43677006179** (workflow "E0 CPU", event `pull_request`, head `413d74788ed5d49764f4bfcd240fd6fb13fb2549`, created 04:29:45, finished 04:50:52), job `e0` (id 132699269818): **failure**. `gh pr checks 6` → `e0 fail 21m3s`. PR `mergeStateStatus` UNSTABLE. This is the first CI run on any P9 commit (Linux, Python 3.12.14, pytest 8.4.1).

| Step | Result |
|---|---|
| Install locked CPU dependencies | success |
| ruff | "All checks passed!" |
| `mypy src/arborlm` | "Success: no issues found in 85 source files" |
| pytest | **"2 failed, 1735 passed, 12 skipped, 3 warnings in 1210.05s"** (1,749 collected, equal to the local count in audit §5) |
| E0 smoke (runs after a test failure: workflow condition `!cancelled() && steps.setup.outcome == 'success'`) | success, recorded |
| Upload E0 artifacts | success, artifact 14146838888 |

Full log saved: `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/integration/pr6_ci_43677006179.log` (command `gh run view 43677006179 -R Dandush03/ArborLM --log`).

Failures (log excerpts, verbatim):

```
FAILED tests/test_p9_model.py::test_chunked_equals_unchunked[flat] - assert False
>       assert torch.equal(s0.scores, s1.scores)
E       assert False
tests/test_p9_model.py:137: AssertionError

FAILED tests/test_p9_sim.py::test_65536_slot_smoke_time_and_memory - assert 1138970624 < (1024 ** 3)
>       assert out["maxrss_bytes"] < 1024**3  # peak resident set of the whole process, bytes
E       assert 1138970624 < (1024 ** 3)
tests/test_p9_sim.py:718: AssertionError
```

**Neither is the known watchdog flake** (`test_watchdog_kills_timed_out_child_and_saves_logs` is not in the failure list, so it passed here). Therefore **no re-run was made**, as instructed.

Read-only diagnosis (no file edited, nothing run locally; cause not proven):

1. `test_chunked_equals_unchunked[flat]` (added in `44ebcbd`, P9 implementation I1–I7) requires **bit-for-bit** equality of the memory score tensor between the unchunked forward and a forward that computes scores in row blocks (`studies/p9/model.py` line 365: `scores = (q[start : start + rows] @ normalized.T) / TEMP`). In CI the preceding assertions on `selected` and `candidate_ids` passed, and the printed leading score values agree to 4 decimals, so the difference is most likely at the floating-point rounding level: a row-block matrix product on Linux x86-64 BLAS is not guaranteed to round identically to the full product. The same tree passed on macOS arm64 (audit §5 run 2; `413d747` changes only documentation). The `learned_tree` parametrization passed in CI.
2. `test_65536_slot_smoke_time_and_memory` asserts peak RSS of a subprocess below 1 GiB. CI measured 1,138,970,624 bytes (1.061 GiB; 6.1% over). The unit conversion in the test is correct for both platforms (`ru_maxrss * (1 if sys.platform == "darwin" else 1024)`, line 708). It passed on macOS; on Linux the process's peak resident set is above the bound.

Both are platform-dependent assertions in new P9 tests, not regressions in `main` code. Whether to (a) relax the tests' bit-exactness / memory bound, (b) mark them platform-specific, or (c) treat the chunking non-equivalence on x86 as relevant to any registered P9/P9-I number is a decision for the lead: changing a P9 test or bound after the freeze is an edit of frozen-era code and needs a recorded decision. **PENDING LEAD REVIEW.** (My assessment, not a decision: P9-I's registered run was on the lead's macOS host, where the chunked/unchunked equality holds, so the CI failure does not by itself contradict the recorded results; it does mean the P9 code's "chunking is exact" property is platform-dependent.)

Skips: 12 in CI versus 6 in the local clean clone (audit §5) and 9 in PR #5's CI; CI runs pytest with `-q` and does not print skip reasons, so the CI skip set is not known to me.

## 6. Integrity on the PR head (step D)

Three-dot diff `origin/main...origin/claude/adr-0017-design` (`git diff --name-status`), cross-checked against GitHub's file list:

- **Failed checker attempt (kept):** `gh pr diff 6 --name-only` fails with "HTTP 406: Sorry, the diff exceeded the maximum number of files (300)"; it printed 0 names. Replaced by `gh api --paginate repos/Dandush03/ArborLM/pulls/6/files` (478 entries: 475 added, 3 modified), whose sorted names equal the local `git diff --name-only` list exactly.
- 478 files: 475 `A`, 3 `M` (`CLAUDE.md`, `README.md`, `docs/RESEARCH_LOG.md`). No `D` or `R`.
- `git diff --name-status … -- src configs tests pyproject.toml uv.lock .github supplements docs/decisions`, filtered for added `configs/p9*`, `tests/test_p9*`, `docs/decisions/ADR-001[78]*`: **empty**. So: no change under `src/arborlm/`; `configs/` only adds `p9_diagnostics.toml` and `p9i_interface.toml`; no existing test modified (only 23 `tests/test_p9_*.py` and 9 `tests/test_p9i_*.py` added); `pyproject.toml`, `uv.lock`, `.github/`, `supplements/` unchanged; only ADR-0017 and ADR-0018 added under `docs/decisions/`.
- `docs/RESEARCH_LOG.md`: +13/−0 (append only).
- No checkpoint/binary extension (`.pt .bin .safetensors .bytes .npy .npz`) in the range; largest added blob 91,943 bytes.
- **Frozen commits** (`git merge-base --is-ancestor`): `378aeac`, `3018126`, `afd62e5` reachable from the PR head and now from `main`; `da9d077`, `dd39aa6`, `dd8b205`, `8261f22`, `a1b4b39`, `326ab0d`, `dc88dab` reachable from the PR head (they reach `main` only when PR #6 is merged). `80f46ae` exists locally (`git cat-file -t` → commit) but is **not** reachable from the PR head or GitHub, as recorded in the audit §4.1; resolved through `COMMIT_MAP.md`.
- **Status strings:** P8 `SUMMARY.md` "INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE"; P8 `analysis.json` `study_status` INCOMPLETE, `section_8_option_indicated` `none`. P9-I `results.json` `status` COMPLETE, `interpretable` true, `selection.outcome` NO_INTERFACE_SELECTED, step 4; `analysis.json` `status` COMPLETE, `analysis.selection.outcome` NO_INTERFACE_SELECTED; `OUTCOME.md` "Study status: COMPLETE … Registered outcome: NO_INTERFACE_SELECTED". (Correction to my own audit §4.4: in `analysis.json` the selection is nested under `analysis`, not at the top level; `analysis.json['selection']` is absent. The value is the same.)

### 6.1 README and CLAUDE.md lines added in `413d747`

- **Placement:** the CLAUDE.md sentence is inserted in item 3 of "Read before doing anything", after the ADR-0016 sentence and before "ADR-0012 (governance) is **not approved**", as proposed in audit §6. The README bullet follows the P8 bullet in the results list. Both as proposed.
- **CLAUDE.md accuracy:** consistent with the records. ADR-0017 status line says Lanes A–D CALIBRATION BLOCKED (§15.2) and no run authorized; §15.7 records attempt 1 stopped at the gates and attempt 2 approved; §15.9 exists ("Human acceptance of the Part I result — 2026-11-15"); `OUTCOME.md` gives NO_INTERFACE_SELECTED; ADR-0018 status "WITHDRAWN as a separate ADR … Never approved; nothing was implemented or run under it."
- **README accuracy: one imprecision, and it is my own wording** (audit §6 proposed text, adopted verbatim by the lead). "Within 8,192 updates on this backbone no learned query interface addressed the memory" is too broad if BB counts as a learned query interface: BB (block-0 attention trained) was INTERFACE_PARTIAL at 4,096 slots (0.54–0.65), and the results review says "BB's PARTIAL accuracy is carried by the memory" (disabling the memory drops it to 109–126 of 2,048; `docs/reviews/p9i-results-2026-11-15/REVIEW.md` line 85). The registered statement is "no tested interface reached INTERFACE_WORKS at all three sizes" (`OUTCOME.md`). The rest of the bullet (57 cells, outcome, human acceptance, oracle rungs, exploratory labels) matches `OUTCOME.md`. Not a merge blocker; a wording fix needs the lead's decision and a new commit. PENDING LEAD REVIEW. The PR #6 body uses the registered wording and states BB's PARTIAL result explicitly.

## 7. Unexpected observations

1. `gh pr diff` cannot list files for PRs over 300 files (above); `--name-only` does not avoid the limit.
2. PR #5's push-to-main CI took 722 s for pytest versus 435 s on the PR run (runner variance; same counts).
3. Several of my blocking wait commands were moved to the background by the harness after 180 s; they only polled `gh run view` and changed nothing.
4. Audit §4.4 path imprecision for `analysis.json` selection (above), my own error.
5. README wording on "no learned query interface addressed the memory" (§6.1), my own proposed text.
6. Two new P9 tests fail on Linux CI but passed on macOS (§5). The audit's local simulation (macOS) did not, and could not, reveal this; my audit §8 R2 named "no CI has ever run on any P9 commit" as a risk and it materialised.
7. The PR #6 body says "CI on this PR: see the checks on this PR"; it does not yet mention the failure. I did not edit it (not requested); the lead may want an appended note.

## 8. State left for the next step

- **Blocker: PR #6 CI is red** (§5). Nothing further was attempted after the failure apart from read-only diagnosis and this log.
- `main` = `30084fac4d6520c52bffef9fefd96a680d628eec` (PR #5 merged). PR #6 open, not draft, head `413d74788ed5d49764f4bfcd240fd6fb13fb2549`, **not merged** (step E). Merging requires the independent review of the integration diff by someone other than the integrator; when merging, pin with `--match-head-commit 413d74788ed5d49764f4bfcd240fd6fb13fb2549` (or the then-current reviewed head) and use `--merge`.
- If anything is pushed to `claude/adr-0017-design` before the merge (for example committing this log or a README wording fix), the PR head changes, CI re-runs, and the reviewed head must be re-pinned.

Astra review: NOT_PERFORMED.
