# P9-I consolidation: integration log, part 2 (PR #6 merge)

- **Integration owner:** Claude Opus 5.5 (model id `claude-opus-5-5`). This continues `INTEGRATION_LOG.md` (committed at `4b932b2`). Engineering record only. **Not Astra validation and not human approval. Astra review: NOT_PERFORMED.**
- **Authority:** the mission text (Task 0.2) authorizes merging the P9-I PR after CI, integrity checks and an independent review of the integration diff. The independent review (`INDEPENDENT_DIFF_REVIEW.md`, a separate Opus 5.5 context, reviewed head `ecd5b87`) gave the verdict APPROVED AFTER a PR-body note (its §6).
- **Environment:** macOS (Darwin 27.2.0, arm64); worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, local HEAD `ecd5b87`; `gh` authenticated as the repository owner. Times are UTC on 2026-11-15.
- **Not done:** no push, commit, force, squash, rebase or `--admin`; no branch deleted; no tracked file edited. ADR-0015's status is untouched and `80f46ae` was not pushed. This file, `CONSOLIDATION_RECEIPT.md` and the reviewer's `INDEPENDENT_DIFF_REVIEW.md` are uncommitted.

## 1. Pre-checks (read-only), about 05:12

| Check | Result |
|---|---|
| `git fetch origin`; `git rev-parse origin/claude/adr-0017-design origin/main` | `ecd5b87970776257e093ea50dc6a85eb64f74ace`, `30084fac4d6520c52bffef9fefd96a680d628eec` |
| `gh pr view 6 --json state,isDraft,headRefOid,mergeable,mergeStateStatus` | OPEN, not draft, head `ecd5b87970776257e093ea50dc6a85eb64f74ace`, MERGEABLE, CLEAN |
| `gh pr checks 6`; `gh run view 43678731935 --json headSha,conclusion,event` | `e0` pass, 17m43s; run on `ecd5b87…`, `pull_request`, success. The reviewer read the log: ruff pass, mypy pass, pytest 1,737 passed, 12 skipped |
| `git rev-parse ecd5b87^{tree} 4b932b2^{tree}` | both `e021f505fbddc09543ef177605273459c2530281` (the merge of `main` into the branch is content-neutral) |
| `git diff --stat 413d747 4b932b2` (also restricted to `studies src configs results .github pyproject.toml uv.lock docs/decisions`: empty) | 5 files: `README.md`, `tests/test_p9_model.py`, `tests/test_p9_sim.py`, `CI_FAILURE_AND_FIX.md`, `INTEGRATION_LOG.md` |
| `git diff --name-status origin/main...origin/claude/adr-0017-design` | 477 A, 3 M (480) |
| `git rev-list --count origin/main..origin/claude/adr-0017-design`; `--merges` | 34; one merge commit (`ecd5b87`) |
| `gh api repos/Dandush03/ArborLM/pulls/6 -q '.changed_files,.commits'` | 480, 34 |

## 2. Commands that changed GitHub state

| # | Time | Command | Result |
|---|---|---|---|
| 1 | 05:13:24 | `gh pr edit 6 --body-file …/scratchpad/integration/pr6_body_after.md` | exit 0. The previous body was saved as `…/pr6_body_before_merge.md` and kept unchanged as the prefix, except that the closing Claude Code line was moved to stay last. The appended section "Update before merge (2026-11-15 UTC): first CI failure, test-only fix, and platform of record" follows the reviewer's §6 text and adds three things: the corrected counts (34 commits including one merge; 480 files, 477 added; 296 review files), the CI result on `ecd5b87`, and a line that the independent diff review approved the merge, noting its file is not yet committed. No @-mention (the script asserted no `@`). The re-read body matches the file apart from trailing newlines. The head was unchanged afterwards (`ecd5b87…`, CLEAN) |
| 2 | 05:13:30 | `gh pr merge 6 --merge --match-head-commit ecd5b87970776257e093ea50dc6a85eb64f74ace` (preceded in the same command by `gh pr checks 6`: pass) | exit 0; `state MERGED`, `mergedAt 05:13:32Z`, merge commit **`587746889d1ce3159bf879e134ceaebd26272518`** |

## 3. Verification after the merge

| Check | Result |
|---|---|
| `git fetch origin`; `git rev-parse origin/main` | **`587746889d1ce3159bf879e134ceaebd26272518`** |
| `git log -1 --format=%P%n%s 5877468` | parents `30084fac…` `ecd5b87…`; "Merge pull request #6 from Dandush03/claude/adr-0017-design" |
| `git rev-parse 5877468^{tree} ecd5b87^{tree}` | both `e021f505fbddc09543ef177605273459c2530281` (**equal**) |
| `git ls-remote --heads origin claude/adr-0017-design claude/p8-locality-aware-training` | `ecd5b87…` and `afd62e5…`: both branches kept |
| `git merge-base --is-ancestor <c> origin/main` | on `main`: `378aeac`, `3018126`, `da9d077`, `dd39aa6`, `dd8b205`, `8261f22`, `326ab0d`, `a1b4b39`, `dc88dab`, `afd62e5`, `0e0fbfb`, `4b932b2`, `ecd5b87`. Not on `main`: `80f46ae` (local backup branch only, as expected) |
| `git diff --quiet 57be5ff origin/main -- pyproject.toml uv.lock .github` | unchanged |
| `git diff --name-status 57be5ff origin/main` | 1,362 A, 3 M (`CLAUDE.md`, `README.md`, `docs/RESEARCH_LOG.md`), no D or R; `-- src/arborlm`: 9 A only. `git rev-list --count 57be5ff..origin/main` = 54 |
| Files on `main` (`git cat-file -e origin/main:<path>`) | present: P9-I `OUTCOME.md`, `results.json`, the attempt-1 README, P8 `SUMMARY.md`, the supplement README, ADR-0015/0016/0017/0018, `p9i-results` REVIEW, `COMMIT_MAP.md`, `HUMAN_DECISION.md`, and the consolidation `CI_FAILURE_AND_FIX.md`, `INTEGRATION_LOG.md`, `HUMAN_APPROVAL.md`, `INTEGRATION_AUDIT.md`. **Absent: `INDEPENDENT_DIFF_REVIEW.md`** (never committed; expected) |
| Result and review folders on `main` (`git ls-tree -d`) | `results/{p8-2026-11-14,p8-supplement-2026-11-14,p9-calibration-2026-11-14,p9i-calibration-2026-11-14,p9i-rehearsal-2026-11-14,p9i-run-attempt1-2026-11-14,p9i-run-attempt2-2026-11-15}`; `docs/reviews/{adr-0017-design,adr-0018-design,p8-preflight,p8-results,p8-results-audit,p8-spec-review,p8-supplement-preflight,p8-supplement-results-audit,p8-supplement-spec-review,p9-calibration-audit,p9i-consolidation,p9i-implementation,p9i-prefreeze-audit,p9i-results}-*` |
| Status strings on `main` (`git show "origin/main:<path>"`, with `python3 -I` for the JSON) | P9-I `OUTCOME.md`: "Study status: COMPLETE." and "Registered outcome: NO_INTERFACE_SELECTED (§I.8.3 step 4)". `results.json`: COMPLETE, NO_INTERFACE_SELECTED, step 4. P8 `SUMMARY.md`: "Study status: INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE." P8 `analysis.json`: INCOMPLETE, 60 expected, 55 complete, option `none`. ADR-0015 status "… STUDY INCOMPLETE (55 of 60 cells simulated) … PENDING HUMAN REVIEW". ADR-0016 "… The registered P8 study remains INCOMPLETE with decision `none`." ADR-0018 "WITHDRAWN as a separate ADR … Never approved". ADR-0017 contains `### 15.9`. Attempt-1 README: "stopped at the gates stage" |
| Push-to-main CI: `gh run list --branch main`; `gh run view 43680155917` | success (job `e0` id 132708813701): ruff pass; mypy `src/arborlm` 85 files pass; pytest 1,737 passed, 12 skipped, 3 warnings in 1029.72 s; E0 smoke recorded |

## 4. Failed checker attempt (my own mistake, kept)

My first status-string read used `M=origin/main; git show $M:results/…` in zsh. zsh parsed `$M:r` as the `:r` (remove-extension) history modifier, which produced `origin/mainesults/…`, and git printed "fatal: ambiguous argument". The three reads affected (P9-I `OUTCOME.md`, P8 `SUMMARY.md`, the attempt-1 README) printed nothing. I re-ran them with `"${M}:…"`, which gave the results in §3. The same loop's `git cat-file -e $M:$p` presence checks were not affected (`:$` is not a modifier) and printed "present" for each path.

## 5. Unexpected observations

1. `INDEPENDENT_DIFF_REVIEW.md` was untracked in the worktree at merge time. The PR #6 body cites it, and it is not on `main` until the lead commits it.
2. The reviewer's §6 text said "the text above is unchanged". To keep the Claude Code line last, I moved that line from the old end of the body to the new end, and I disclose this in the appended section itself.

Astra review: NOT_PERFORMED.
