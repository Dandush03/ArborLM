# M0 fresh run: recheck of the revised pooling script, field table and runner

**Verdict: FIT TO HASH.** Files rechecked: `pool_fresh.py` (`19e6f61f…47aa`), `field_table.json` (`1f64ac39…bafe`), `make_field_table.py` and `run_fresh.py` (`12fd29aa…5f8b`). `run_plan.json` (`316f1026…f389`) and `assemble_run_plan.py` (`3fb74baa…`) are unchanged; their hashes were checked. P1 and P2 of the first audit are fixed. The changes do what lead rulings R-56 to R-58 say, and the diff contains no other change to the pooling logic.

Auditor: an `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. It wrote none of the files under check. It executed no plan unit, generated no item, opened no output of any real run, and deleted or moved nothing.
Astra review: NOT_PERFORMED. This is independent engineering evidence. It is not Astra validation and not human approval.

## Commands and environment
- Pooling: `scripts/run_pool.sh FIXTURE NAME [PLAN_SHA FIELD_SHA AMEND_SHA]`. It runs `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python -I studies/m0/fresh_run/pool_fresh.py … --expect-plan-sha256 … --expect-field-table-sha256 … --expect-amendment-sha256 …` from the implementation worktree root, with Python 3.12.14. The result lines are in `pool_runs.out.txt`.
- Checkers: `python3 -I <deliver>/scripts/check_cases_v2.py runs/old_main2`, `python3 -I scripts/check_recheck_v2.py runs`. Python 3.15.1, standard library only.
- Runner: `timeout 120 uv run --locked python -I studies/m0/fresh_run/run_fresh.py --plan runner_test/t3|t4/plan.json --expect-plan-sha256 … --seed-set …`. The plans are made-up; every command is `/usr/bin/python3 -I -c` writing one file. Output: `runner_tests.out.txt`.
- Diffs: `diff -u superseded_v1/<f> <f>`, in `diff_pool_fresh.txt`, `diff_run_fresh.txt` and `diff_make_field_table.txt`. The semantic diff of the field table is in `diff_field_table.txt`.

## 1. What changed (my own diff against `superseded_v1/`)
**`pool_fresh.py`.** Every change, with what it does:
- **(a) Hash checks.** Three required arguments; the plan, field table and amendment list are each checked against an expected SHA-256, with exit 4 on a mismatch.
- **(b) `dry_run_exclusions`** is copied into the extras.
- **(c) R-56:** applies to M1a only.
  - Pattern: `^([^\[\]]+)\[[^\[\]]*\]$`.
  - Each key matching it gives one row as written and one row under the section prefix plus the stripped name. Both get the chance and the base reading.
  - The class table is looked up on the stripped name, and any over-bound row drops the lineage.
  - Exit 3 if two bracketed variants of one name, or a bracketed key next to the bare name, occur in the same seed, section, lineage and level.
  - Every row carries a `bracket_stripped` flag. The extras list the lineages whose outcome differs under the second reading, and all stripped rows.
- **(d) R-57:** rates within one shape go to `rates_within_one_shape_reported_only`. They come from:
  - R2 per-shape `k`, `napp`, `n`, `k/n` and `k/napp`;
  - s5 `rate_in_shape` and `n_shape` for every rule row, `MF_in_shape_cv` included;
  - the a3 and battery S rows' report-only fields;
  - the battery's per-shape `MF_shape_cv`.

  None of these is stored anywhere a decision reads them.
- **(e) Field table:** a new `report_only` status. `FieldTable.name`/`names` (the roles the decisions use) still return only `read` fields. `not_rule_keys` also skips `report_only` names in s5 `rule_name`, so `MF_in_shape_cv` is still not a rule.
- **(f) One further change, not on the coordinator's list:** in `read_c1_s5` the field check `ft.check(unit, form, "rule", …)` now runs before the not-a-rule skip. The fields of `MF_in_shape_cv` rows are now checked too. This is stricter: a stop instead of a silent skip. No decision changes.

Evidence that nothing else changed: the v1 run and the revised run on my 142-case fixture have identical `pooled_table.json` (5,641 rows, apart from the new `bracket_stripped` key, which is false on every row there), `dropped.json` and `per_lineage.json` (`compare_v1.out.txt`).

**`field_table.json`:** the only changes are those `make_field_table.py`'s diff makes:
- six fields move from `not_read` to `report_only`: a3 `rate_in_shape`, `mf_in_shape_cv` and `n_shape`; battery `rate` and `n_shape`; s5 `MF_in_shape_cv`;
- a new R-57 text under `rulings`.

**`run_fresh.py`:**
- a required `--expect-plan-sha256` (exit 2 on a mismatch, before anything else);
- a refusal (exit 2) if any `hashes_*.json` under either the run or the dry root holds a unit whose status is not ok;
- `job()` wrapped in `try/except BaseException`: the exception type and message and the hashes of the files present are recorded, `STOP` is set, and the runner exits 1.

## 2. Earlier cases against the new script
| Fixture | Result |
|---|---|
| My 142-case fixture (`check_cases_v2_old_main2.out.txt`) | **142/142 PASS** |
| The same cases on the regenerated v6 fixture (`check_cases_v2_new_main.out.txt`) | 142/142 PASS |
| The 5 stop cases | **5/5:** exit 3, the same stderr lines as before, no output directory |
| The 3 extra class cases (`classes2_recheck.out.txt`) | **3/3 PASS** |

**The one expectation R-56 changes:** my old echo fixture. `M1.ratio_share_r3`, at 0.20 in every seed under `[max/max]` and `[max/last]`, was kept under v1. It is now **dropped**, because its stripped row `im:echo_best_position` reads 1/5 (cases a0-*).

## 3. New cases (hand values, exact fractions)
All 30 pass (`check_recheck_v2.out.txt`). Attempt 1 gave 28/30; the two failures were my own expectations written as "16" and "2"/"20", while the script writes fractions as "16/1". The values were equal (`check_recheck_attempt1.out.txt`).

**(a) Echo, 0.20 in every seed, a different bracket in seed 3:**
- written names: 2/15 and 1/15, kept;
- stripped name: vs chance 1/5 (+1/20000), vs base 0.05 → 3/20 (+1/10000), dropped;
- listed with `dropped_without_it: false`.

**(b) Base 0, brackets differ by seed:**
- 0.1499/0.1500/0.1501 gives a stripped figure of exactly 3/20, which is **dropped**. The written M1a rates have 4 decimals, so point 7 adds 1/20000. A stripped M1a figure of exactly 0.15 cannot be kept under the text.
- 0.1498/0.1499/0.1499 gives 281/1875: 0.149917 vs chance and 0.149967 vs base, **kept**.
- 0.1500/0.1501/0.1502 gives 1501/10000, **dropped**.

**(c) Class lookup on the stripped name:**
- `largest_share[a|b]` on `M1.ratio_share_r2` (stem `ratio_share`): the stripped `im:largest_share` is an entry and is uncounted. The written names are counted at 2/15 and 1/15, and the lineage is kept.
- The same keys on `M1.e56_noentry_r3`: the stripped name is counted at 1/5, dropped.

**(d) Stops:** two bracketed variants in one seed, and a bracketed key beside its bare name: each gives exit 3 with only `STOP unit=M1a lineage=M1.e56_echo_r3 (…)` and no output directory.

**(e) Hash checks:** a wrong plan, field-table or amendment hash each gives exit 4, the message naming which file, and no output directory.

**(f) Within-shape rates:** I changed only the report-only fields: a3 `rate_in_shape` 0.777 and `mf_in_shape_cv` 0.111, battery `rate` 0.555, s5 `MF_in_shape_cv` 0.333.
- `pooled_table.json`, `dropped.json`, `per_lineage.json` and every other extras key are identical.
- The changed values appear in `rates_within_one_shape_reported_only`, as do the R2 per-shape counts and the battery's per-shape `MF_shape_cv`.

## 4. Runner (made-up plans only)
**Tests (`runner_tests.out.txt`):**
- A wrong `--expect-plan-sha256` gives exit 2, and no directory is created.
- When R1c fails twice in seed 1, the runner exits 1 and R2a is not started. Every later invocation then refuses with exit 2, naming the record and unit:
  - seed 1 with `--units R2a`;
  - seed 2;
  - the dry set;
  - seed 2 with `--check-only`.
- A runner-internal error (`FileExistsError`, from a chain sharing a stdout file) is recorded as `{"ok": false, "runner_exception": {...}, "files_present": ...}`.
  - R1c and R2a are not started, and the runner exits 1.
  - Later invocations refuse.
- A figure planted in every command's stdout, stderr and output file appears 0 times in the runner's own stdout and stderr.

**P1 and P2: fixed.**

## Findings (all NOTE; none needs a change before the hash)
- **Q1 (procedure, fails safe).**
  - The refusal also scans the dry root. Under point 10, a dry-run unit whose own code fails, and which is excluded, leaves an `ok: false` record in the dry root.
  - With that dry root in the final plan, the runner would refuse every run seed. That is safe, but it would block the run.
  - Point 10's "repeated on the same seed" also needs empty directories, so the final plan's dry root must be chosen with this in mind. This is for the lead's procedure; it cannot favour passing.
- **Q2.** On a runner error, later units print "not started (an earlier unit failed twice)", which is inaccurate wording. The STOP line prints the exception message: a path, not output content. The record's `attempts` is empty in that case; the commands that had already run in that attempt are not listed, but the files present are hashed.
- **Q3.** If a seed wrote the bare name and another seed a bracketed variant, both would fall into one row, and the bracketed reading would mark it `bracket_stripped`. This cannot happen in M1a (item 5), so I note it only.
- **Q4.** Item 1(f): s5's field check now runs before the skip (stricter).
- **Q5. My own errors, kept.**
  - Generator v5 failed on a list concatenation before writing any file and left five empty directories, `fixtures/{main,r56,r56_stop_two,r56_stop_bare,shapes_alt}`. v6 writes to `fixtures6/`.
  - `check_recheck` attempt 1 had the two expectations in the wrong format (above).

## 5. Can M1a write two bracketed variants of one name for one section, lineage and level in one run?
**No.** Read at `b78e58b1`, and checked in the run copies, which differ only in the seed, the path and the imports:
- **Section `own`** (`studies/m0/m1_fix3_shortcuts.py`, `run()`): `rates` is created at line 442 as a dict literal with exactly one bracketed key, `echo_best_position[{best_a}/{best_b}]`, per lineage and level. The keys added at 443–448 come from `spec()` (line 117) or are `k + "__within_applicable"`. No key literal in the file contains `[`, and none is the bare `echo_best_position`.
- **Section `a3`** (`studies/m0/m1_fix4_battery.py`, `a3_task()`, not `shortcuts_a3.run`): line 141 creates `rates` with the one bracketed key. The keys added at 149–151 come from `shortcuts_a3.spec` (line 56), and no key literal there contains `[`.
- **Section `a4`** (`audit4_m1/shortcuts_a4.py`, `run()`): the keys are `a4:mode_by_visible_ask`, `a4:echo_pos`, `a4:echo_pos_offset` and the keys of `mine()`/`theirs()`. None is bracketed.
- **The one bracketed name** in all three is the echo rule, and each section/lineage/level dict holds one key of it. The fitted pair is `best_a/best_b`, each from `first, second, last, max, min, sum, max_minus_min, second_last`; it differs across seeds and levels, never twice within one.
- **Conclusion:** R-56's stop cannot be triggered by committed M1a code. Method: my grep for string subscripts and f-strings with brackets in the four files. This is a reading of literals; I did not trace every dynamically built key.

## Files
`scripts/` (`make_fixture_v5.py` (failed), `make_fixture_v6.py`, `run_pool.sh`, `check_recheck.py` (attempt 1), `check_recheck_v2.py`, `make_runner_plan_v3.py`), `fixtures6/`, `fixtures/` (empty v5 leftovers), `runs/`, `runner_test/`, the diffs, `*.out.txt`, `SHA256SUMS.txt`.
