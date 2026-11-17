# P10-S0 pre-freeze confirmation: fix commit 89cdd6a, measure-analysis, projection r2, cap table, S0 suite

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

Intended location: `docs/reviews/p10s0-implementation-audit-2026-11-15/prefreeze/CONFIRM.md` in worktree `agent-afc8a4b295465fecc`. This session's write hook refuses writes to another worktree, so the file is here in the session scratchpad. It should be copied unchanged.

## Scope and environment

- **What was checked.** Worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-afc8a4b295465fecc`, branch `claude/p10-s0`, HEAD `89cdd6a`. The fix diff is `git diff 686df62 89cdd6a`. The one untracked file is `studies/p10s0/freeze/stage_caps.json` (sha256 `b9f85b41bc190664c76c1904be2e29100971333497685b471373e2029115adb8`).
- **Auditor.** Opus 5.5 (`claude-opus-5-5`). I wrote none of the code under review. My earlier audit is `PREFREEZE.md`.
- **Environment.**
  - macOS-27.2.1-arm64, uv 0.12.15, and the worktree's `.venv` (Python 3.12.14, torch 2.8.0).
  - My recomputations ran under `/usr/bin/python3 -I` (3.9.6, json only, no repository import).
- **Not done.**
  - I generated no draw, read no registered seed, and ran no registered stage, no rehearsal, no e2e and no `measure-analysis`. There was no network use.
  - The repository was not edited and nothing was committed.
  - `experiments/` was listed before and after the test run, and the listing was identical. The ledger sha256 stayed `374090ce…66a4e2` before and after.
- **Scratch.** `$S` = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/confirm/`:
  - `c3_projection_r2.py` is my earlier `prefreeze/scripts/p3_projection.py` with only the projection path changed to `-r2`; its output is `c3_projection_r2.json`;
  - `c4_caps_headroom.py` and its output `c4_caps_headroom.json`;
  - `pytest_s0.txt`;
  - `exp_before.txt` and `exp_after.txt`.

## 1. Findings F1–F11 closed by 89cdd6a

| Item | Result | Evidence |
|---|---|---|
| Code identity | **PASS** | `train.py`, `evaluate.py` and `model.py` at HEAD hash to `453b762c…`, `8c742bd2…` and `ac558df8…`, identical to `3a9a742`. `git diff 686df62 89cdd6a` does not touch `configs/`, `src/`, `studies/p9*`, `studies/p10s0/launch/`, `uv.lock` or `pyproject.toml`. The rehearsal and the rehearsal-draw gates stand. |
| F1 | **PASS** | The worked examples now pass `cap_seconds=16 h` explicitly. The ledger tests compare against `core.cap_hours()`. A new guard test, `test_no_s0_test_pins_the_value_of_the_real_config_s_hour_cap`, was added. No cap-related failure remains (§5). The fix did not add the optional "config = 22 h" assertion. The config is pinned by the freeze hash, so this is acceptable. |
| F2 | **PASS by code and unit test; e2e not re-run (open)** | The scaled Q1 is now 0.52 × cap, so 2 × full = 1.04 × cap and cut 3 always applies. Cut 3 is ≈ 0.69 × full, so it fits. The test is parametrised at caps of 16, 22 and 30 h. I found no evidence of an e2e run at `89cdd6a`; README step 1 and PREFREEZE require one. |
| F3 | **PASS** | `registered_q1` calls `require_gates_passed` and `require_draw_plan` before the decision, the memory check and the `q1_start.json` write (`stages.py:1263-1279`). `cmd_q1_gate` refuses without both the `train-q1` and the `evaluate-q1` manifest (`:1146-1148`). Those manifests are written only after the pool returns (`:512`). Residual, informational: `block_cap` and `require_room` still run after the start record. Both pass under any passing decision (§4), and the table has both Q1 keys. |
| F4 | **PASS (code)**; one caveat on the values | The booleans are now computed against the config cap and the ledger. In r2, `reserve_seconds` is 0.0, because the caps did not exist yet; the caps are computed from the projection, so this ordering cannot be avoided. The figures also omit the 15 registered draws (≈ 502 s) and the registered gates (78 s). The "after Q1" margin implied by the record is therefore 960.6 s, against **260.8 s** with everything counted. The booleans (true, true) are still right. |
| F6 | **PASS** (cosmetic leftover) | `budget.py:237`'s docstring still says "(16 - 2 x other)" (context-only function). `DEFAULT_CAP_HOURS = 16.0` is only the template default. |
| F8 | **PASS** | `ran` now holds only the entries whose `run == run_dir.name`. Registered gates are charged as `("gates", run_dir.name)`. Because the gates are now required first, `before = 0` in the registered flow. If the gates' ledger entry were missing, 78.09 s would be counted, which is conservative. |
| F9 | **PASS** | `caps` reads the config's `measured_seconds`. It refuses a provisional generation block and a typed value that differs by more than rel 1e-9. The table's `generate` = 66.89776783401612, exactly the config's `cap_seconds`. |
| F10 | **PASS** | See §3. |
| F11 | **PASS** | `work_rehearse_cell` calls `registered_worker_guard`, and a test covers it. |

**New paths.** I found no new path that runs a registered stage out of order, writes a once-only record early, or changes a registered number.

ruff reports "All checks passed!". `mypy src/arborlm studies/p10s0` reports "no issues found in 101 source files".

**N10 (minor, PENDING LEAD REVIEW).** No code links the cap table to its projection.

- `stage_caps.json` records no projection sha.
- `freeze-plan` pins both files by hash but does not check that caps = `caps_table(projection)`.
- Two projections now exist (r1 `d6f6e6be…`, r2 `f7e13716…`). `freeze-plan --projection <r1>` with the r2-derived table would be accepted. The headroom decisions would then use r1 while the block caps came from r2. The differences are seconds, but the inconsistency is unguarded.
- **Fix.** Either name r2 in the freeze record and rely on the recomputation in §4, or add the check. A code change needs only the e2e and suite re-run.

## 2. `measure-analysis`

- **Cannot touch registered seeds or a registered run directory: PASS.**
  - The command is `MODE_FREE` and ignores any typed `--mode`. The workers always run with `--mode check` or `--dry`.
  - The template data is `core.test_set(2)` (seed base 920201), trained in mode `dry`.
  - Everything is written in `mkdtemp(prefix="p10s0-measure-")` and deleted unless `--keep`. The draw plan carries registered *names* only.
  - It never calls `run_stage_tasks`, so it never charges the ledger: the ledger is unchanged at 486.258 s with six entries.
  - `--out` refuses an existing file.
  - Informational: `--out` and `--out-root` are unrestricted. Nothing reads `timing` records automatically, and the workers' `--run-dir` is always the temporary `registry/`.
- **"Errs high": partly not shown, and immaterial.**
  - The arithmetic holds: 22.28296 + 0.00705 = 22.29000 s; 0.50415 + 0.00269 = 0.50684 s.
  - The doubled part, however, is only the 7 ms of in-process computation. Meanwhile the registry omits 3 learned cells (≈ 2.1 % of the update-log lines, which `analysis.py:396` reads) and the evaluation records of 1 failed cell. That shortfall is ≈ 0.5 s.
  - The measurement was also taken on a warm cache and without the registered freeze re-check (≈ 0.3–0.9 s).
  - So against a full registry the figure probably errs **low by about 1 s**.
  - **The caps are unaffected.** Both are the 60 s floor: the analysis would be stopped only at 2.69 × 22.29 s, the report only at 118 × 0.507 s.
  - `timing.json` carries no commit or code identity.

## 3. Projection r2 against r1

- **Recomputed independently: PASS.** My script reads every folder's raw `rehearsal.json`, `rehearsal_evaluate.json` and pool task, takes the larger of alone and busy, and adds r2's guard. Its six totals equal r2's to 0.0 s, and every rate field of all 24 items agrees, the A2 pre items included.

| Block | r1 (s) | r2 (s) | Δ | 2 × rounds × Δguard (Δguard = 0.122314) |
|---|---|---|---|---|
| Q1 full | 30,285.796 | 30,276.255 | −9.540 | 78 × Δ = 9.540 |
| Q1 cut 3 | 21,023.979 | 21,016.151 | −7.828 | 64 × Δ = 7.828 |
| WX A5-D / A1 | 3,033.544 / 3,921.066 | 3,032.566 / 3,920.088 | −0.979 | 8 × Δ |
| Probe A5-D / A1 | 11,824.836 / 19,818.606 | 11,824.592 / 19,818.362 | −0.245 | 2 × Δ |

- **The whole change is the guard** (0.387163 → 0.264849 s per task). No total moved because of F10.
- **F10 is right.** In the raw records, each A2 pre/post pair shares the label `REH-Q1-A2-{2K4K,8K16K}-d01-j0` and has distinct `phase` values. r2's pre fields now equal the pre folder's own evaluation (r1 held the post values in these fields: 4.6371 / 7.6499 / 9.2149 / 15.2867 s):
  - alone 2K4K: 3.9523 s, 477,085,696 B;
  - busy 2K4K: 6.5032 s, 476,495,872 B;
  - alone 8K16K: 9.3622 s, 647,462,912 B;
  - busy 8K16K: 15.4929 s, 648,314,880 B.
  - The largest peak is unchanged at 1.0428 GiB.
- **The live guard (PENDING LEAD REVIEW).**
  - Once `plan.json` pins the projection sha, nothing re-measures the guard, so freezing it is mechanically sound.
  - It is a noisy single measurement, though (−32 % between two runs). It is also taken on a proxy, not the real `registered_state`/`verify_plan` cost; no plan and no data manifests exist at projection time.
  - The re-run, required by F4/F10, re-measured the guard as a side effect. It raised the A1 margin from 248.8 s to 260.8 s. No decision changes at nominal.
  - The frozen numbers are no longer the ones named in the cap-raise addendum (`d6f6e6be…`).
  - A guard error of ±0.1–0.5 s per task moves the A1 margin by about ±20–80 s.

## 4. Cap table and the headroom rule at 22 h

**Inputs, each read from its record:**

- G = 39.755301958008204 (gates manifest, task seconds).
- P = 3.1943115839967504 (`gates.json` timing).
- N = 33.44888391700806 (the generation manifest, equal to the config).
- A = 22.29000487504527 and R = 0.5068383340258151 (`timing.json`).
- Charged now: 486.2583528730902 s. The cap: 79,200 s.

**Every entry recomputed: PASS, with a maximum absolute difference of 0.0.**

| Entry | Recomputed (s) |
|---|---|
| gates | 2(G + 12P) = 156.17408 |
| generate | max(60, 2N) = 66.89777 |
| analysis / report | 60 / 60 (floor) |
| reserve | 60 |
| q1 full train / evaluate | 58,841.261 / 1,711.250 |
| q1 cut3 train / evaluate | 40,772.218 / 1,260.084 |
| wx A5-D train / evaluate | 5,873.366 / 191.765 |
| wx A1 train / evaluate | 7,652.086 / 188.090 |
| probe A5-D train / evaluate | 23,497.038 / 152.146 |
| probe A1 train / evaluate | 39,461.539 / 175.185 |

The block caps are exactly 2 × r2, not 2 × r1 (for example, Q1 full train would be 58,850.80 under r1).

**The rule:** margin = 79,200 − [charged + 2 × (stages + 60)].

- At the Q1 start, the charge C1 = 486.26 + 15 × 33.449 + 78.087 = 1,066.08 s, and `before` = 0.
- At the Q1 gate, the charge C2 = C1 + Q1 = 31,342.33 s.

| Point | Scenario | Full / both (s) | Fallback (s) | Decision |
|---|---|---|---|---|
| Before Q1 | nominal | **17,461.4** | cut 3: 35,981.6 | full |
| Before Q1 | generation and gates at their caps (C1 = 1,645.9) | 16,881.6 | 35,401.8 | full |
| Q1 gate, A5-D | nominal | **18,023.3** | WX only: 41,672.5 | both |
| Q1 gate, A1 | nominal | **260.8** | 39,897.5 | both |
| Q1 gate, A1 | generation and gates at their caps | **−319.1** | 39,317.7 | **cut 1 (probe)** |
| Q1 gate, A1 | Q1 +10 / +25 / +50 % | −2,766.9 / −7,308.3 / −14,877.4 | ≥ 24,759 | cut 1 |
| Q1 gate, A5-D | Q1 +10 / +25 / +50 % | 14,995.7 / 10,454.3 / 2,885.2 | — | both |
| Q1 gate | Q1 at its 2× cap | A5-D −12,252.9; A1 −30,015.5 | 11,396.3; 9,621.2 | cut 1 |

**Thresholds:**

- A1 keeps the probe up to a Q1 of 1.0086 × its projection.
- A5-D keeps both up to 1.5953 ×.
- WX is kept up to 2.32 × or 2.38 ×, which is above Q1's own 2× cap, so **cut 2 cannot occur**.
- **Cut 3 cannot occur.** It would need about 17,461 s more before Q1, and the capped pre-Q1 stages can add at most about 580 s.
- For A1, a registered generation averaging more than 50.8 s per draw (1.52 ×) cuts the probe on its own.

**Ledger room.** It suffices on every passing path: 78,133.9 s at the Q1 start against a 58,841.3 s cap; 47,857.7 s at the Q1 gate; 43,937.6 s after WX A1, against 39,461.5 s.

**At projection:**

- Nothing is cut or refused.
- The A1 probe is the only block within a small deviation of being cut: 260.8 s.
- The A5-D probe needs a Q1 at least 59.5 % slower than projected before it is cut.

## 5. S0 test files

- **Command.** `UV_NO_SYNC=1 uv run --locked pytest tests/test_p10s0_*.py -q -p no:cacheprovider --basetemp $S/pytest_base -rfEs`.
- **Result.** **1 failed, 422 passed, 2 skipped** (the two opt-in e2e tests), in 156 s.
- **The failure.** It is `test_p10s0_core.py::test_the_freeze_files_exist_both_or_neither` (`:308`). It fails only because `stage_caps.json` exists while `plan.json` does not.
  - **It passes in the frozen tree**, where both exist.
  - It also passes with the caps file absent.
- **Clean-up.** The basetemp (3.9 GB) was deleted. `experiments/` and the ledger were unchanged.

## Commands

All from the worktree:

- `git diff 686df62 89cdd6a`.
- `git show 3a9a742:<file> | shasum -a 256` for the three files.
- `git diff --stat 686df62 89cdd6a -- configs src studies/p9 studies/p9i studies/p9ii uv.lock pyproject.toml studies/p10s0/launch` (empty).
- `shasum -a 256` on both projections, the cap table and the ledger.
- `/usr/bin/python3 -I` with an inline JSON diff of r1 against r2.
- `/usr/bin/python3 -I $S/c3_projection_r2.py`.
- `/usr/bin/python3 -I $S/c4_caps_headroom.py`.
- The pytest command in §5.
- `UV_NO_SYNC=1 uv run --locked --offline ruff check .`
- `UV_NO_SYNC=1 uv run --locked --offline mypy src/arborlm studies/p10s0`.

**Failed attempts:**

- No failed checker attempt.
- One failed write: the hook refused writing this report into the other worktree.

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.

READY AFTER e2e (both variants) re-run green at the final pre-freeze commit; freeze record naming projection r2 (f7e13716…097c9a) with the reason it replaced d6f6e6be…, freeze-plan run with that projection (N10), and the A1 margin (260.8 s nominal, −319 s with generation and gates at their caps) stated

---

## The lead's rulings on this confirmation (2026-11-15 UTC; written by the lead, not by the auditor)

- **Frozen projection.** `experiments/P10S0J-projection-20261115-r2/projection.json` (sha256 `f7e13716bf670b3861cd36f041d3a16202bb33f018083ec27007a55909097c9a`) is the projection of the freeze. It replaces `d6f6e6be…` because the fix of F10 changed the projection code; the totals differ by seconds, all from the re-measured per-task guard. The cap stays at 22 hours.
- **N10.** No code check is added. The freeze record names the projection and the cap table by sha256, `freeze-plan` is run with that projection, and the auditor's recomputation of the caps from it is this report.
- **F6 leftover.** The docstring at `budget.py:237` is corrected in the commit that files this report (a comment only).
- **The A1 margin** (260.8 s nominal; negative if generation and gates reach their caps or Q1 runs 0.86 % slower than projected) is stated in the freeze record. The probe being cut for A1 in that case is the registered rule working; the cap is not raised for it (the human lead's direction of 2026-11-15 to put S1 before runtime margin in S0).
- **e2e.** Both variants are re-run at the commit that files this report, before the run decision.
