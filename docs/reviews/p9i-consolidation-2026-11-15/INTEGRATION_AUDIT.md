# P9-I consolidation: Phase 0 integration audit (Task 0.1)

- **Integration owner:** Claude Opus 5.5 (model id `claude-opus-5-5`). This is an integration context only. It is independent engineering evidence. **It is not Astra validation and not human approval. Astra review: NOT_PERFORMED.**
- **Date:** 2026-11-14 local / 2026-11-15 UTC.
- **Worktree:** `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design`, HEAD `dc88dab1de72d69d800d9f239898b5dfcbea24b8` (equal to GitHub `refs/heads/claude/adr-0017-design`, checked with `git ls-remote`).
- **Environment:** macOS (Darwin 27.2.0, arm64), uv 0.12.15, Python 3.12 from `uv sync --locked --extra pilot` (lock unchanged), `gh` authenticated as the repository owner (admin permission).
- **What I did:** read-only `git` and `gh` queries; a throw-away clone in the session scratch directory where I simulated the two merges and ran ruff, mypy and pytest; read the records listed below. This file is the only file written in the worktree; it is not committed.
- **What I did not do:** no merge, no `gh pr ready`, no PR opened, no push, no commit, no tag, no edit of any existing file, no training or registered stage, no change to branch settings.

## 1. Commit graph (as of this audit)

| Item | Value |
|---|---|
| `origin/main` | `57be5ff4e5e0ed319da90bcb2ac161bc6574e709` (merge of PR #4, P7-B) |
| PR #5 | OPEN, **draft**, base `main`, head `claude/p8-locality-aware-training` = `afd62e5d5ab39c86fbd3403d75001edf1d8e9867`; `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`; no review decision; 0 comments |
| PR #5 CI | one required-by-nobody check, workflow "E0 CPU" job `e0`, run 43607178425 on `afd62e5` (event `pull_request`): **success**. Log: ruff "All checks passed!", mypy "Success: no issues found in 85 source files", pytest "868 passed, 9 skipped, 3 warnings in 434.83s", E0 smoke success |
| `main` ancestor of PR #5 head | yes |
| PR #5 head ancestor of `claude/adr-0017-design` | **yes** (`git merge-base --is-ancestor afd62e5 dc88dab`) |
| `main..p8` | 18 commits, `dae567a` … `afd62e5`, no merge commits |
| `p8..p9` | 31 commits, `e46d5f8` … `dc88dab`, no merge commits |
| `p9..main` | 0 commits (P9 branch is fully up to date with main) |
| Other open PRs | none (only #5). Merged: #1–#4 |
| Branch protection on `main` | **none** (`gh api …/branches/main/protection` → HTTP 404 "Branch not protected"); rulesets: `[]` |
| Repository merge settings | merge commit, squash and rebase all allowed; delete-branch-on-merge off |
| CI on `claude/adr-0017-design` | **never run.** The workflow triggers on `pull_request` and on `push` to `main` only, and no PR exists for this branch (`gh run list --branch claude/adr-0017-design` is empty) |
| Precedent | PRs #1–#4 were merged on GitHub with merge commits ("Merge pull request #n from …") |

Commands: `git fetch origin`; `git rev-parse origin/main origin/claude/p8-locality-aware-training HEAD`; `git merge-base --is-ancestor …`; `git log --oneline A..B`; `gh pr view 5 --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,…`; `gh pr checks 5`; `gh run view 43607178425 --log`; `gh pr list --state open`; `gh api repos/Dandush03/ArborLM/branches/main/protection`; `gh api repos/Dandush03/ArborLM/rulesets`; `git ls-remote --heads https://github.com/Dandush03/ArborLM.git`.

Local-only observations (no effect on GitHub): the local `main` branch is stale at `2f629a3` (behind `origin/main`); any integration step must use `origin/main`. Local branches `backup/p8-before-single-line-rewrite` (`59aac82`) and `backup/claude-p5-review-p6-proposal-before-message-rewrite` (`718f620`) exist only locally (see §4.1).

## 2. Dependency of P9 / P9-I on P8

Imports of P8 code that exists only on the P8 branch (none of these modules is on `main`):

| Importer | Imports |
|---|---|
| `studies/p9i/core.py` | `from arborlm import p8_core` |
| `studies/p9/core.py`, `controls.py`, `incremental.py`, `train.py` | `from arborlm import p8_core` |
| `studies/p9/objective.py` | `from arborlm.p8_objective import Soft, r_co` |
| `studies/p9/sim.py` | `from arborlm import p8_core, p8_sim`; `from supplements.p8s.null import identity_stream, precondition_from_counts` (ADR-0016 supplement code) |
| `tests/test_p9_core.py`, `tests/test_p9_objective.py` | `arborlm.p8_core`, `arborlm.p8_objective` |

`studies/p9i` reaches `studies/p9` (core, data, model, controls, pool, evaluate, objective, train), so P9-I depends transitively on `arborlm.p8_core`, `p8_objective`, `p8_sim` and `supplements.p8s`. Other imports (`arborlm.io`, `engine`, `config`, `pilot_model`, `p2_*`, `p4_model`, `p5_*`, `p7a_core`, `p7b_*`) are on `main`.

**Consequence.** All 18 P8 commits are ancestors of every P9 commit, including the frozen ones (`da9d077`, `dd39aa6`, `8261f22`, `326ab0d`). A PR from `claude/adr-0017-design` against the current `main` would carry PR #5's 18 commits and merge them as a side effect. Removing them would require rebasing the P9 commits onto `main`, which rewrites every frozen P9 commit hash cited in the records — prohibited. 

**The only safe merge order:** (1) PR #5 into `main` with a merge commit, with the head pinned to `afd62e5`; (2) then a new P9-I PR `claude/adr-0017-design` → `main` with a merge commit. After step 1 the P9-I PR's diff contains exactly the 31 P9 commits. If the P8 branch head moved before step 1, the P9 branch would no longer contain it and the order would have to be re-audited; pin with `--match-head-commit`.

## 3. PR #5 readiness

### 3.1 Recorded status: accurate

Recomputed from the committed records with my own short `python3 -I` reads (no project analysis module imported):

- `results/p8-2026-11-14/analysis/P8A-…/analysis.json`: `cells_expected` 60, `cells_with_complete_records` 55, `missing_cells` 5, `study_status` INCOMPLETE; `decision_inputs.section_8_option_indicated` = `none` ("INCOMPLETE study: no option is derived"); `locality_positive_cases_both_panels` = `[]`, `flat_cases_beating_optimized_flat` = `[]`, `architecture_advantage_cases` = `[]`.
- `scorecard.csv` study classes: C04, C05 INCOMPLETE; C06 COLLAPSED; C07 CONCENTRATION-ONLY; C08 QUALITY-FAILED; C09 NOT REPLICATED ACROSS PANELS (A QUALITY-FAILED, B COLLAPSED); C10 QUALITY-FAILED. These equal the PR body table and `results/p8-2026-11-14/SUMMARY.md`.
- `results/p8-supplement-2026-11-14/README.md` is titled "not the registered P8 output" and states the registered study is unchanged, INCOMPLETE, decision `none`. ADR-0016 status says the same.
- `docs/reviews/p8-results-2026-11-14/HUMAN_DECISION.md` records the human lead's "yeah" accepting the C06–C10 classes, with the narrow scope, and states it does not cover direction, ADR-0012 or merging.

### 3.2 Open items on PR #5 (none is a technical blocker)

1. **Merge approval.** Not given. The PR body itself says "Do not merge without the human lead's decision." Merging also requires un-drafting (`gh pr ready 5`), which is part of the approval requested.
2. **ADR-0015 status line still reads "PENDING HUMAN REVIEW".** No record shows the human lead closing the P8 review beyond the C06–C10 decision and the ADR-0016 approval. PENDING LEAD REVIEW: whether merge approval also closes the P8 review, or the status line stays as is (it must not be edited in place either way without a decision; a dated record is the established pattern).
3. **ADR-0012 not approved.** P8 ran under a study-specific workflow. Precedent: PRs #3 and #4 merged with ADR-0012 pending. Not a blocker; stated for the record.
4. **PR body is stale in places** (cosmetic; body edits need no code change but are a GitHub write, so not done): the "Scope / files" list predates the supplement and omits `supplements/p8s/`, `tests/test_p8s_*.py`, `results/p8-supplement-2026-11-14/`, `docs/reviews/p8-supplement-*`; the test count "798 passed, 3 skipped, at the freeze" differs from current CI (868 passed, 9 skipped, which includes supplement tests); the "one-line post-run fix" of `make_report.py` is a 1-line replacement by 4 lines (`d47a9fd`, +4/−1); the freeze is cited as `80f46ae` without mentioning that it was pushed as `378aeac` (documented in `docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md`); unresolved-decision items 1 and 2 are answered by the "Update" section, item 3 (direction) has no recorded P8 decision.
5. **CI passes on the exact head** `afd62e5` (run 43607178425).

**Verdict:** technically ready to merge (mergeable, clean, CI green on the exact head, no conflicts, records consistent with the PR's statements). Governance: blocked only by the absent human merge approval (and the un-draft that goes with it).

## 4. Integrity

### 4.1 Frozen commits

| Commit | Role | Reachable from `dc88dab` | On GitHub |
|---|---|---|---|
| `80f46ae` | P8 freeze **as cited in records** | **no** | **no** |
| `378aeac` | P8 freeze as pushed (same tree `b13a9f9c…` as `80f46ae`) | yes | yes (P8 and P9 branches) |
| `3018126` | P8 supplement freeze | yes | yes |
| `da9d077` | P9-I freeze 1 | yes | yes (P9 branch) |
| `dd39aa6` | P9-I freeze 2 | yes | yes |
| `dd8b205` | P9-I code, attempt 1 | yes | yes |
| `8261f22` | P9-I code, attempt 2 | yes | yes |
| `326ab0d` | P9-I outcome | yes | yes |
| `afd62e5` | PR #5 head | yes | yes |

**Risk R1.** `80f46ae` (cited in every P8 stage manifest, ADR-0015 §17, `SUMMARY.md` and the PR #5 body) is the pre-rewrite hash. It is reachable only from the local, unpushed branch `backup/p8-before-single-line-rewrite`. Content identity is preserved: `git rev-parse 80f46ae^{tree}` = `git rev-parse 378aeac^{tree}` = `b13a9f9c09083a9b486adb9b691089f00409059f`, and `COMMIT_MAP.md` maps every original hash to its pushed hash with tree hashes. If the local backup branch is deleted and garbage-collected, the cited hash can only be resolved through `COMMIT_MAP.md`. PENDING LEAD REVIEW: whether to preserve the original objects on GitHub (e.g. push the backup branch or a tag); I did not push anything.

### 4.2 No code change after any freeze

`git diff --name-status` over `src`, `studies`, `supplements`, `configs`, `tests`:

- `378aeac..afd62e5` (P8 freeze → PR #5 head): no change to `src` or `configs`; only added test files for the supplement (`tests/test_p8s_*`), no modification.
- `3018126..afd62e5` (supplement freeze → head): none.
- `dd8b205..da9d077` (code 1 → freeze 1): none.
- `8261f22..dd39aa6` (code 2 → freeze 2): none (also `pyproject.toml`, `uv.lock`).
- `dd39aa6..dc88dab`: only `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` and `c4_c8_comparison_output.txt` added; no code.
- After freeze 1, `studies/p9i/stages.py` (`0e0fbfb`) and `classes.py`, `core.py`, `evaluate.py`, `report.py`, `stages.py` (`8261f22`) changed. This is the disclosed attempt-1 repair, covered by the human approval of attempt 2 (ADR-0017 §15.7) and freeze record 2 (§15.8).

### 4.3 `pyproject.toml`, `uv.lock`, `.github/`

`git diff --stat origin/main dc88dab -- pyproject.toml uv.lock .github` is empty: **unchanged across the whole range.**

### 4.4 Committed result folders and status strings

| Folder | Status found |
|---|---|
| `results/p8-2026-11-14/` | `SUMMARY.md`: "Study status: INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE."; `analysis.json` `study_status` INCOMPLETE (see §3.1) |
| `results/p8-supplement-2026-11-14/` | README: not the registered P8 output; 5 of 5 cells; registered P8 unchanged |
| `results/p9i-run-attempt1-2026-11-14/` | README: "STOPPED BEFORE TRAINING. No cell was trained or evaluated" |
| `results/p9i-run-attempt2-2026-11-15/` | `results.json` and `analysis.json`: `status` COMPLETE, `interpretable` true, `selection.outcome` NO_INTERFACE_SELECTED (step 4), G1/G2/G4 passed, `updates` 8192; `cells.csv` 57 rows; `OUTCOME.md`: "Study status: COMPLETE … Registered outcome: NO_INTERFACE_SELECTED" |
| Also present | `results/p9-calibration-2026-11-14/`, `results/p9i-calibration-2026-11-14/`, `results/p9i-rehearsal-2026-11-14/` |

Within `main..dc88dab`, the only commit that modifies (rather than adds) anything under `results/` is `d47a9fd` (`results/p8-2026-11-14/report/make_report.py`, post-run ZeroDivisionError fix, analysis-only, disclosed as P8 defect 9). No P9-I record was modified after the run commit `a1b4b39`.

### 4.5 Files that exist on `main` and are modified in the range

| File | Change | Judgement |
|---|---|---|
| `docs/RESEARCH_LOG.md` | +27 / −0 (pure append) | consistent with the rules (log appends) |
| `README.md` | +1 / −0 (P8 line) | pointer addition; acceptable. P8 supplement and P9-I have no README line yet (§5) |
| `CLAUDE.md` | +2 / −2: ADR pointer list extended with ADR-0015/0016; standing rule changed from "P1–P5 are immutable" to "P1–P5 are immutable (and treat P6–P8 code, records and ADRs the same way)" | pointer update acceptable; the rule change **strengthens** immutability. It is still an edit of the policy-pointer file; flag for the human lead's awareness, not a defect |

No file under `src/arborlm/`, `configs/`, `tests/`, `docs/decisions/` or `results/` that exists on `main` is modified.

### 4.6 In-place edits of files added within the range (for completeness)

| File | Commits | Judgement |
|---|---|---|
| ADR-0015 | `01731f0`, `378aeac` (pre-freeze revisions); `2d10338` (status line replaced, outcome §17 added: +14/−1) | allowed pattern: proposal revised before freeze; status line and outcome record after the run |
| ADR-0016 | `6808693` (pre-approval revision); `afd62e5` (status line, §10 "None. Not executed." replaced by the outcome) | same pattern |
| ADR-0017 | revisions 2–4 while a proposal; after approvals: status lines replaced and §15.1–§15.9 appended (`da9d077` +34/−1, `dd39aa6` +26/−1, `dc88dab` +10/−0) | same pattern |
| ADR-0017 §18 / `INTERFACE_CONTRACT.md` | `0da0582`: one clause of §18 (BB optimizer) replaced in place after the human Part I decision (§15.3) and before freeze 1, disclosed as lead clarification §15.4 | PENDING LEAD REVIEW: an approved text corrected in place rather than only appended; disclosed and pre-freeze, so I do not count it as a defect |
| ADR-0017 status line | still says "attempt 2 is approved … The outcome of Part I is recorded in `results/` and the research log, not in this text", while §15.9 now records the acceptance | stale but not false; optional future status-line update needs the lead |
| ADR-0018 | replaced by a "WITHDRAWN" stub (`c330adf`); revisions 1–3 in history; never approved | acceptable |
| `studies/p9/*`, `configs/p9_diagnostics.toml`, `tests/test_p9_core.py` | `44ebcbd` filled the I0 stubs (and removed the "stubs raise NotImplementedError" test) | pre-calibration implementation; acceptable |
| `docs/reviews/p9-calibration-audit-2026-11-14/AUDIT.md`, `outputs/probes_8192_32768.log` | first committed in `37c0a94` with probes still running; completed in `0e05662` (B102 columns added) | audit record completed by its author; low risk |
| `docs/reviews/p8-preflight-2026-11-14/ruff.toml`, `docs/reviews/p8-results-2026-11-14/README.md`, `docs/reviews/adr-0017-design-2026-11-14/{EXECUTION_PLAN,RESOURCE_BUDGET}.md` | review documents revised alongside their ADR | acceptable |

## 5. Simulated merges and repository checks

Clone: `git clone --no-hardlinks <worktree> …/scratchpad/simclone`; push URL set to `DISABLED`; GitHub refs fetched as `refs/remotes/gh/*` from the worktree's `origin/*` (verified against `git ls-remote`).

```sh
git checkout -b sim-integration gh/main                         # 57be5ff
git merge --no-ff --no-edit gh/claude/p8-locality-aware-training # exit 0, no conflict
git merge --no-ff --no-edit gh/claude/adr-0017-design            # exit 0, no conflict
```

- Merge 1 tree `a36e363b6b9164c6d2cff209b5784e56a8c09866` = tree of `afd62e5`.
- Merge 2 tree `a0ec0a8e578ad50595c9580e6a14eae70cb928e1` = tree of `dc88dab`. (Expected: each branch contains its base, so the merged tree equals the branch tree.)

Checks on the final simulated tree (same invocation as CI, `--extra pilot`):

| Command | Result |
|---|---|
| `uv sync --locked --extra pilot` | exit 0 |
| `uv run --locked --extra pilot ruff check .` | exit 0, "All checks passed!" |
| `uv run --locked --extra pilot mypy src/arborlm` | exit 0, "Success: no issues found in 85 source files" |
| `uv run --locked --extra pilot pytest -q -rs -p no:cacheprovider` | **run 1:** exit 1, "1 failed, 1742 passed, 6 skipped, 3 warnings in 579.79s"; **run 2 (same tree, unchanged):** exit 0, "1743 passed, 6 skipped, 3 warnings in 574.84s" |

**The run-1 failure, kept and reported.** `tests/test_run_records.py::test_watchdog_kills_timed_out_child_and_saves_logs` failed once: `terminal["reason"]` was `"watchdog error: PermissionError: [Errno 1] Operation not permitted"` instead of `"process wall-time limit exceeded"`. Facts: the test and `src/arborlm/watchdog.py` exist on `main` and are **unchanged** in the range (`git diff --stat gh/main HEAD -- tests/test_run_records.py src/arborlm/watchdog.py` is empty); the test passed in `main`'s last CI (677 passed) and in PR #5's CI on Linux; afterwards it passed 3/3 alone, 20/20 as the whole file, 15/15 alone under 8 busy CPU loops, and in the full run 2. The cause is **not established**. A plausible mechanism (unverified) is macOS returning EPERM from `os.killpg` on a process group whose only remaining member is an unreaped zombie; `_stop` catches only `ProcessLookupError`. I classify it as an intermittent failure of an existing `main` test on this macOS host, not attributable to P8/P9 code on the evidence; it is a risk (§8 R7), not a merge blocker. Logs: `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/outputs/pytest.log` (run 1, with JUnit `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/outputs/pytest_junit.xml`) and `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/outputs/pytest_run2.log`.

Skips (identical in both runs; all six are missing git-ignored local data or the optional `matplotlib`): `test_p8_core.py:136` (local experiments root not provided), `test_p8_panel.py:123` (local corpus not present), `test_p8_sim.py:182` (local P7-A traces not present), `test_p9_controls.py:194` (frozen `experiments/` not present), `test_p9_core.py:717` (frozen `train.bytes` not present), `test_p9_report.py:711` (`matplotlib` not installed).

Counts by group from the run-1 JUnit file (1,749 collected): `main`'s own tests 677 (676 passed, 1 failed as above); `test_p8_*` 124 (121 passed, 3 skipped); `test_p8s_*` 76 passed; `test_p9_*` 730 (727 passed, 3 skipped); `test_p9i_*` 142 passed. Cross-checks: `main`'s last CI (run 43551509358) collected 677, all passed; PR #5's CI collected 868 + 9 = 877 = 677 + 124 + 76. CI on Linux skipped 9 where this macOS clone skipped 3 in that subset; CI does not print skip reasons (`-q` without `-rs`), so the Linux skip set is not known to me. The implementation records report "1745 tests passing" at `8261f22` in the lead's checkout, which has `experiments/`; 1,749 collected here is consistent with that (4 data-dependent skips plus `matplotlib`), but I did not run the suite with the local data.

CI coverage (workflow `e0-cpu.yml` as on `main`, unchanged in the range):

- `pytest` uses `testpaths = ["tests"]`, so every `tests/test_p9_*.py` (23 files) and `tests/test_p9i_*.py` (9 files) is collected by CI. Tests that need the git-ignored `experiments/` corpus/backbones skip (`test_p9_core.py` line 717, `test_p9_controls.py` line 194); `test_p9_report.py` line 711 skips without `matplotlib` (not in the lock).
- **CI's mypy covers `src/arborlm` only; `studies/` and `supplements/` are not type-checked in CI.** Informational, not changed: `mypy studies supplements` in the CI environment fails with 84 errors (60 `import-untyped`, 24 `no-any-return`), all caused by the installed `arborlm` package having no `py.typed` marker; `MYPYPATH=src mypy studies supplements` passes ("Success: no issues found in 38 source files"). Logs: `…/scratchpad/outputs/mypy_studies_supplements_informational.log`, `…/mypy_studies_supplements_mypypath_src_informational.log`.
- The P9-I PR will be the first CI run on any P9 commit.

## 6. CLAUDE.md on the branch

It lists ADR-0010/0011/0013/0014/0015/0016 as completed and ADR-0012 as not approved; it says nothing about ADR-0017 or ADR-0018. Proposed text only (not applied; would be added to item 3 after the ADR-0016 sentence, in a separate commit after approval):

> ADR-0017 (P9): Lanes A–D are calibration blocked (human lead, §15.2), not scientifically failed, and nothing under them has run; Part I (P9-I, the query-interface prerequisite, §18) was human-approved, executed once as attempt 2 after attempt 1 stopped at the gates stage before training, and is complete with the registered outcome NO_INTERFACE_SELECTED, accepted by the human lead as a registered negative result (§15.9). ADR-0018 is withdrawn (folded into ADR-0017 Part I).

Optional README line (proposal only), after the P8 line:

> - [P9-I query-interface prerequisite](results/p9i-run-attempt2-2026-11-15/OUTCOME.md) (ADR-0017 Part I): 57 cells, registered outcome **NO_INTERFACE_SELECTED**, accepted by the human lead as a registered negative result. Within 8,192 updates on this backbone no learned query interface addressed the memory; oracle rungs show the memory stores and returns answers. Address collapse and draw sensitivity are exploratory diagnostics, not registered findings.

## 7. Drafts

### 7(a) Request to the human lead: approval to merge PR #5

> **Request: approve merging PR #5 (P8, ADR-0015 and the ADR-0016 supplement) into `main`.**
>
> Why now: P9 and P9-I code imports P8 code (`arborlm.p8_core`, `p8_objective`, `p8_sim`, `supplements.p8s`) and the P9 branch is built on PR #5's head `afd62e5`. P9-I can only reach `main` after PR #5, without rewriting frozen commits.
>
> What I would do if you approve: mark PR #5 ready for review (it is a draft), then merge it on GitHub with a **merge commit** (no squash, no rebase), pinned to head `afd62e5`. CI passed on exactly that commit (run 43607178425: ruff, mypy, 868 passed / 9 skipped, E0 smoke). The simulated merge has no conflict and the merged tree equals the tested tree. `main` has no branch protection, so nothing would be bypassed.
>
> What merging **means**: the P8 records, code, tests, reviews, the ADR-0016 supplement and the C06–C10 human decision become part of `main` as they are. The registered P8 study stays **INCOMPLETE (55/60 simulated), decision `none`, no case LOCALITY-POSITIVE**; the supplement stays separately labelled and does not complete P8.
>
> What merging **does not mean**: it is not Astra validation (Astra review: NOT_PERFORMED); it does not change any class, record or ADR; it does not approve ADR-0012; it does not decide direction for the locality line; it does not authorize publication. ADR-0015's status line will still say "PENDING HUMAN REVIEW" unless you say otherwise.
>
> Please answer: (1) Approve un-drafting and merging PR #5 with a merge commit? (2) Does your approval also close the P8 human review (so it can be recorded with a dated entry), or should it stay open? (3) Optional: should the original pre-rewrite P8 commits (e.g. `80f46ae`, cited in the records) be preserved on GitHub by pushing the local backup branch or a tag?

### 7(b) Planned P9-I PR

**Title:** `P9-I: query-interface prerequisite (ADR-0017 Part I), executed once (attempt 2); COMPLETE — NO_INTERFACE_SELECTED (registered negative result)`

**Description:**

```markdown
## Registered result

**Study status: COMPLETE (57/57 cells, 8,192 updates each). Registered outcome: NO_INTERFACE_SELECTED (§I.8.3 step 4).** No tested query interface reached INTERFACE_WORKS at all three sizes within U updates. The human lead accepted this as a registered negative result (ADR-0017 §15.9). Lanes A–D of ADR-0017 remain calibration blocked; nothing under them has run.

Start with `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`, then `docs/reviews/p9i-results-2026-11-15/REVIEW.md`.

## Intent / hypothesis

ADR-0017 Part I (§18): can a model trained only through the answer loss learn to tell its memory what it needs (query interfaces N, W7, E7, A4, A4E, BB), against oracle rungs R1/R2 and dense controls, before any capacity or locality study (Lanes A–D) is meaningful?

## Attempt history (both kept)

- **Attempt 1** (freeze `da9d077`, code `dd8b205`): stopped at the gates stage; G4 recorded "gradient reach failed for R2" due to a defect in the gate's own harness. Nothing trained. Records: `results/p9i-run-attempt1-2026-11-14/` (README, ADDENDUM).
- Harness fix (`0e0fbfb`), non-finite handling fix (`8261f22`), Opus audits (`32d72e9`, `c53acaa`); the human lead approved attempt 2 (§15.7); freeze record 2 (`dd39aa6`).
- **Attempt 2** (freeze `dd39aa6`, code `8261f22`): complete, 57/57. G1, G2, G4 passed; no LEAKAGE. Charged 2,691 s of 14,400 s.

## Accuracy summary

[Table copied from OUTCOME.md: R1 reference ~1.0 / 0.97; all learned interfaces at chance (0.028–0.044); BB PARTIAL at 4,096 only, with LANGUAGE MODELLING DEGRADED; D7 dense control 0.78–0.80 at 16,384.]

## Deviations and process notes

- Attempt 1 stop and the post-freeze code repair (above), approved by the human lead before attempt 2.
- Three mistyped launch commands across the two attempts were refused by the argument parser before anything ran; no stage ran twice.
- C4–C8 before-training comparisons with attempt 1 were run by the lead (transcribed output `c4_c8_comparison_output.txt`) and re-checked independently by the auditor.
- BB-0's two seeds are bit-identical runs and count as one.
- ADR-0017 §18 BB optimizer clause corrected in place before freeze 1 (§15.4).

## Exploratory findings (diagnostic, NOT registered evidence)

- Address collapse in learned-query arms (query cosine 0.95–1.00; 1–6 distinct top-1 slots; loss stalls near ln 32).
- Draw sensitivity of W7 at 4,096 slots on rehearsal/test draws (never registered seeds): escape from collapse in 9 of 11 runs; not observed on the registered draw.
- D7 shows the identity is present in the window; W7's failure is about addressing.

## Limitations / what may not be claimed

Within 8,192 updates, this backbone, this loss, synthetic fact task only. No claim about capacity, utilization, locality, natural language, or the ArborLM concept as a whole; no claim that W7 cannot learn or that it works; no dense label from D7; BB is not evidence of a model communicating what it needs.

## Scope / files

New files only, apart from `docs/RESEARCH_LOG.md` (append). ADR-0017 (revisions 2–4, §15.1–§15.9), ADR-0018 (withdrawn stub); `studies/p9/`, `studies/p9i/`, `configs/p9_diagnostics.toml`, `tests/test_p9_*.py`, `tests/test_p9i_*.py`; results under `results/p9-calibration-2026-11-14/`, `results/p9i-{calibration,rehearsal}-2026-11-14/`, `results/p9i-run-attempt1-2026-11-14/`, `results/p9i-run-attempt2-2026-11-15/`; reviews under `docs/reviews/{adr-0017-design,adr-0018-design,p9-calibration-audit,p9i-implementation,p9i-prefreeze-audit,p9i-results}-*`. `pyproject.toml`, `uv.lock` and `.github/` unchanged. No checkpoints or corpus bytes committed. Depends on PR #5 (merged first).

## Commands and tests

[Exact commands from the records; CI result of this PR; local integration checks from docs/reviews/p9i-consolidation-2026-11-15/INTEGRATION_AUDIT.md.]

## Validation status

Opus 5.5 independent recomputation: no difference in any count, class, annotation or selection. **Astra review: NOT_PERFORMED.** The human lead accepted the classification (§15.9); merge requires the human lead's approval.

## Unresolved decisions

- ADR-0012 not approved. Lanes A–D blocked. Next study (ADR-0019, address learning) is not started and not part of this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### 7(c) Command sequence after approval (not run)

```sh
REPO=Dandush03/ArborLM
# 0. Re-verify state immediately before acting
git fetch origin
test "$(git rev-parse origin/main)" = 57be5ff4e5e0ed319da90bcb2ac161bc6574e709
test "$(git rev-parse origin/claude/p8-locality-aware-training)" = afd62e5d5ab39c86fbd3403d75001edf1d8e9867
test "$(git rev-parse origin/claude/adr-0017-design)" = dc88dab1de72d69d800d9f239898b5dfcbea24b8
gh pr view 5 --json state,isDraft,mergeable,mergeStateStatus,headRefOid
gh pr checks 5                                     # must be pass on afd62e5
gh api repos/$REPO/branches/main/protection        # expect 404; if protected, follow the rules, never bypass

# 1. PR #5 (only with the human lead's approval)
gh pr ready 5
gh pr merge 5 --merge --match-head-commit afd62e5d5ab39c86fbd3403d75001edf1d8e9867   # merge commit; no --admin, no --squash/--rebase; branch kept
git fetch origin
M1=$(git rev-parse origin/main)
git rev-parse "$M1^1" "$M1^2"                      # expect 57be5ff…, afd62e5…
test "$(git rev-parse $M1^{tree})" = "$(git rev-parse afd62e5^{tree})"
gh run list --branch main --limit 1                # wait for push CI on main; must succeed

# 2. P9-I PR against the updated main
gh pr create --base main --head claude/adr-0017-design --draft \
  --title "<7(b) title>" --body-file <7(b) body file>
gh pr view <N> --json commits --jq '.commits|length'   # expect 31
gh pr diff <N> --name-only                              # expect only P9 files + docs/RESEARCH_LOG.md
gh pr checks <N> --watch                                # first CI on any P9 commit; must pass
# Local verification on the PR merge ref (throw-away clone): ruff, mypy src/arborlm, pytest, counts compared with §5

# 3. Independent review of the integration diff (a separate Opus auditor context; not by me)
#    Scope: diff main..claude/adr-0017-design; no file outside P9 additions and the log append; no record changed.

# 4. Merge, only with the human lead's approval of the P9-I merge
gh pr ready <N>
gh pr merge <N> --merge --match-head-commit dc88dab1de72d69d800d9f239898b5dfcbea24b8
git fetch origin
M2=$(git rev-parse origin/main)
git rev-parse "$M2^1" "$M2^2"                      # expect M1, dc88dab
test "$(git rev-parse $M2^{tree})" = "$(git rev-parse dc88dab^{tree})"
for c in 378aeac 3018126 da9d077 dd39aa6 dd8b205 8261f22 326ab0d dc88dab afd62e5; do git merge-base --is-ancestor $c origin/main && echo "$c on main"; done
git diff --quiet 57be5ff origin/main -- pyproject.toml uv.lock .github && echo "lock, pyproject, workflow unchanged"
gh run list --branch main --limit 1                # push CI on main must succeed
```

If any `test` fails, any check fails, or a conflict appears, stop and report; do not force, squash, rebase or use `--admin`.

### 7(d) Consolidation receipt template (Task 0.3)

```markdown
# Consolidation receipt — P8 and P9-I into main

- Integration owner: <model, model id>; date/time (UTC): <…>
- Human approvals: PR #5 merge <verbatim + date + where recorded>; P9-I merge <verbatim + date + where recorded>
- Astra review: NOT_PERFORMED. This receipt is not Astra validation.

| Step | Value |
|---|---|
| main before | 57be5ff4e5e0ed319da90bcb2ac161bc6574e709 |
| PR #5 head merged | afd62e5d5ab39c86fbd3403d75001edf1d8e9867 |
| PR #5 merge commit (M1), parents | <sha>; 57be5ff…, afd62e5… |
| CI on PR #5 head / on main after M1 | run <id> <result> / run <id> <result> |
| P9-I PR number, head | #<n>, dc88dab1de72d69d800d9f239898b5dfcbea24b8 |
| CI on P9-I PR | run <id>: ruff <…>, mypy <…>, pytest <passed>/<skipped>, smoke <…> |
| Independent integration review | <reviewer model>, <file>, verdict |
| P9-I merge commit (M2), parents | <sha>; M1, dc88dab… |
| Tree check | M1 tree = afd62e5 tree: <yes/no>; M2 tree = dc88dab tree: <yes/no> |
| Frozen commits reachable from main | 378aeac, 3018126, da9d077, dd39aa6, dd8b205, 8261f22, 326ab0d: <yes/no each> |
| 80f46ae (cited P8 freeze) | <resolved via COMMIT_MAP / preserved on GitHub as …> |
| pyproject.toml, uv.lock, .github unchanged | <yes/no> |
| CI on main after M2 | run <id> <result> |
| Recorded statuses on main | P8 INCOMPLETE (55/60, decision none, no LOCALITY-POSITIVE); P8 supplement separate; P9-I COMPLETE — NO_INTERFACE_SELECTED |
| Branches deleted | none (unless the human lead directs) |
| Deviations / incidents | <none or list> |
```

## 8. Blockers and risks

1. **Blocker (governance): no human approval to merge PR #5** (and to un-draft it). Everything else waits on it.
2. **Blocker (order): the P9-I PR must not be opened against the current `main`**; it would merge PR #5's 18 commits as a side effect.
3. R1: cited P8 freeze `80f46ae` exists only in the local repository (§4.1).
4. R2: no CI has ever run on any P9 commit; the P9-I PR will be the first. Local simulation passed (§5).
5. R3: CI does not type-check `studies/` or `supplements/`; they pass only with `MYPYPATH=src`. Not changed.
6. R4: tests depending on `experiments/` skip in CI and in a clean clone; CI evidence for those paths comes only from the local runs recorded in the study folders.
7. R5: PR #5 head must not move before merge; pin with `--match-head-commit`.
8. R6: local `main` is stale (`2f629a3`); use `origin/main`.
9. R7: one intermittent failure of the existing `main` test `test_watchdog_kills_timed_out_child_and_saves_logs` in local run 1 (passed in run 2 and 38 isolated reruns; code unchanged in the range; cause not established; §5).
10. Open governance items, not merge blockers: ADR-0015 "PENDING HUMAN REVIEW"; ADR-0012 not approved; stale PR #5 body; CLAUDE.md/README have no P9-I line (§6); ADR-0017 status line stale relative to §15.9; ADR-0017 §18 in-place clause correction (§4.6), PENDING LEAD REVIEW.
