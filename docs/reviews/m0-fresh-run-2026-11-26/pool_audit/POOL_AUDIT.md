# M0 fresh run: audit of the pooling script, field table, run plan and runner (stage 1S point 9 (v))

**Verdict: FIT AFTER REQUIRED CHANGES.** `pool_fresh.py` (`b22876ad…c41b`) and `field_table.json` (`20cf1975…995b`) are fit to hash as they are: no disagreement with the approved text was found, and every case from point 9 (v) passes. `run_plan.json` (`316f1026…f389`) is fit. Two required changes are in the runner `run_fresh.py` (`86e4c495…d03d`): P1 and P2.

Auditor: `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. It wrote none of the scripts, copies, plan, rule scripts, closed list or amendment list. It did not read `studies/m0/fresh_run/selfchecks/` or `experiments/_scratch/m0_fr_pool_impl_20261126/` at any point. It opened no past run output, executed no plan unit and generated no item.
Astra review: NOT_PERFORMED. This is independent engineering evidence. It is neither Astra validation nor human approval.

## Environment and commands
- Implementation worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f`, HEAD `d2707f65`. The files under audit are untracked, and their hashes equal the brief's: pool `b22876ad…`, field table `20cf1975…`, plan `316f1026…`, runner `86e4c495…`, `assemble_run_plan.py` `3fb74baa…`.
- Pooling script runs (from the worktree root):
  `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I studies/m0/fresh_run/pool_fresh.py --plan <fixture>/plan.json --survivors <fixture>/survivors.json --class-table <consolidation worktree>/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json --amendments <fixture>/amend.json --field-table studies/m0/fresh_run/field_table.json --out <deliver>/runs/<name>`. Python 3.12.14 (uv locked).
- Fixtures: `python3 -I scripts/make_fixture_v2.py fixtures/<name> <variant>` (v3: `echo`; v4: `classes2`). Checker: `python3 -I scripts/check_cases_v2.py runs/main2_attempt1`. Python 3.15.1 (`/opt/homebrew/bin/python3`), standard library only.
- Plan check: `python3 -I scripts/check_plan.py <worktree>/studies/m0/fresh_run/run_plan.json` gives `check_plan.out.txt`.
- Runner exercised only on made-up harmless plans: `python3 -I studies/m0/fresh_run/run_fresh.py --plan runner_test/t2/plan.json --seed-set 1`. Python 3.15.1. Every command was `/usr/bin/python3 -I -c …` writing one file. No unit of the real plan was run.

## Findings
**P1. MUST CHANGE BEFORE HASH (runner).** A second failure stops only the current invocation. A later invocation starts the remaining units.
- Text violated (point 11): "If the unchanged command fails a second time, nothing is changed and nothing is left out: the run stops, it is written down as a departure and it goes to the human lead before G-gen's record."
- Shown: `runner_test/t2_attempt1` exited 1 with `STOP unit=R1c`. Then `--units R2a` (`t2_attempt2`) ran R2a and exited 0.
- Smallest change: in `main()`, refuse with exit 2 before starting anything if any `hashes_*.json` under either output root holds a unit with `"ok": false`.

**P2. MUST CHANGE BEFORE HASH (runner).** An exception inside `run_unit`/`run_chain` is not caught. Examples are an `OSError` from `makedirs`/`open`, or an existing stdout file. When one is raised, the unit is not recorded, `STOP` is not set and later units still run. The traceback appears only at the end.
- Text violated (point 11): "As each unit ends for a seed, the SHA-256 of each of its output files is recorded, with its exit status".
- Shown: `runner_test/t1_attempt1.*`. My v1 test plan gave two chained commands one stdout file. R1b then raised `FileExistsError`, R1b was never recorded, and R1c still ran.
- The real plan does not trigger this particular path: no chain shares a stdout or stderr file (`check_plan_stdout_unique.out.txt`).
- Smallest change: wrap the body of `job()` in `try/except BaseException`. On an exception, record `{"exception": type name, "ok": false}` and the tree hashes of what exists, set `STOP`, and return False.

**P3. NOTE, PENDING LEAD REVIEW (leans toward passing; follows the text).** M1a writes the echo rule under a name that contains the positions fitted per seed and level: `echo_best_position[{best_a}/{best_b}]`, in `m1_fix3_shortcuts.py:442` and `m1_fix4_battery.py:141`.
- "One rule is one name … nothing has to be judged 'the same rule'" (point 6). So seeds whose fitted positions differ make different rules, and each counts no hit for the other seeds.
- Shown in `echo_case.out.txt`: a rate of 0.20 in every seed, under `[max/max]` in seeds 1 and 2 and `[max/last]` in seed 3, pools to 2/15 and 1/15. The lineage is kept.
- The script does what the text says. Only the lead can decide whether the name is read without the bracket. M1b and M1c write the same rule under the fixed name `echo_best_position` (`rules_a5.py:178`), on their own streams.

**P4. NOTE, PENDING LEAD REVIEW.** Point 6 says "rates within one shape are reported and not counted". The pooling script writes no within-shape rate: no R2 per-shape figure for a rule that does not depend on the shape, and no C1 `rate_in_shape` or `MF_in_shape_cv`. Point 9 (v) does not list them among the script's outputs. If the report of point 11 is to carry them, they must come from somewhere. After the hash only an unhashed reader could produce them.

**P5. NOTE (a reading, consistent with the script's convention).** For an R1 rule that a seed does not name, the script adds eff 0 over that seed's items.
- An R1 rule is unnamed in a seed only when it gave no answer on any item (`r1_fix3_battery.py` 1084–1090; `a4copy/heuristics4.py` 617–631).
- The R1 convention scores such an item at chance. That convention is "part of the hashed script" (point 6), so eff 0 is that convention.
- A reading of "no hit" as accuracy 0 would instead give −chance. The text does not use that reading for R1.

**P6. NOTE (robustness).** C1 rule keys are split at the first `|` (`partition("|")`). If a shape label contains `|`, the rule name is misread. This could happen with s4's `"tail:"+…` label or a3's `"pf:"+printform`. `f4b_pool_v2.py` does the same (`split("|", 1)`). Rule names never contain `|`, so `rpartition` would be safer. I found no committed label that contains `|`, but I did not prove that none can.

**P7. NOTE (plan, reproducibility).** The commands `s4_rules_v2.py`, `s5_analyse_v2.py`, `f5*.py` run with `python -I`, and so do the a3 subprocesses inside the committed wrappers (`c1_fix4_a3_run.py:60`, `f3_a3_run.py:34`). `-I` makes the interpreter ignore `PYTHONHASHSEED` and `PYTHONDONTWRITEBYTECODE`.
- Point 1 says every script runs with `PYTHONHASHSEED=0`. For the a3 subprocesses this cannot be met without changing committed code.
- A grep of those five files found no `hash()`, no `random.` and no iteration over an unsorted set (shallow check). Recommend recording this as a known limit.

**P8. NOTE.** `pool_fresh.py` checks the class table's hash. It does not check the amendment list (`a861df02…caf1`), the field table or the plan against recorded hashes. Recommend adding the amendment list hash at least, since point 9 (iv) hashes it with the class table.

**P9. NOTE (run-time stop risk).** `new_rules_final.py` (R1c) takes rule names per level from `test[:50]`, and `cde_rules` names depend on the items. A rule that is absent from the first 50 items at one level gives a line with fewer than 7 values, and the pooling script then stops (choice 2). With 20 items, the dry run cannot show whether this happens at 3,000.

**P10. NOTE (runner).**
- (a) No expected-plan-hash check. Recommend `--expect-plan-sha256`.
- (b) The docstring says `python3 -I`. On this machine `/usr/bin/python3` is 3.9.6, which cannot import `datetime.UTC`. Recommend `uv run --locked python -I`.
- (c) A retried unit is pooled only through `--dir-override`, a manual step. Write it into the procedure.
- (d) The runner prints only unit names and exit statuses. No figure leaked: 0 occurrences of the planted figure in the runner's stdout and stderr.

**P11. NOTE.** Minor points:
- An engineering stop adds a reason text, for example "a line does not have 7 values …" or "a level outside 0 to 6: {v}". It carries no figure, but the second form echoes a level key from an output.
- R2 counts a level key whose shape map is empty as present.
- `dry_run_exclusions` is not copied into `report_extras.json`. The report takes it from the plan.

**P12. My own errors (kept).**
- `check_cases.py` case ALL-2 expected 10 C1 drops. My own hand list holds 11. Attempt 1 gave 141/142, and the one failure was my error (`check_cases_main2_attempt1.out.txt`); fixed in `check_cases_v2.py`.
- `make_fixture.py` v1 wrote a battery hit greater than `n_shape`. `fixtures/main` is left unused, and v2 fixes it.
- `make_runner_plan.py` v1 shared one stdout file in a chain. That mistake is what exposed P2.
- In `classes2`, `R2.crt_smallest` was dropped by the `[NEW] (P)` rule my generator also placed on it. That entry belongs to `count_divisible`, so the drop is correct. The case itself, the `(partial)` entry, is uncounted as expected.

## Case table (item 1)
The fixtures are my own, written from the text, in the committed output forms, with a made-up plan and survivor list in `run_plan.json`'s schema. Plan items: R1 100, R2 40, M1 100, C1 40. Hand values are exact fractions. The full listing is in `check_cases_v2_main2.out.txt`: **142 cases, 142 PASS.** Stop cases are in `stop_cases.out.txt`: **5/5 PASS.** `classes2_case.out.txt`: **3/3 PASS.**

| Case (point 9 (v)) | Expected (hand) | Script | Result |
|---|---|---|---|
| figure exactly 0.15 from counts (R2 open 18/120; C1 a3 hits 6,6,6 of 40) | 3/20, margin 3/20, kept | same | PASS |
| just above (R2 19/120; C1 a3 19/120) | over, dropped | same | PASS |
| just below −0.15 (R2 yes/no 41/120 vs 1/2; R1 eff −0.1501) | −19/120 and −1501/10000, dropped | same | PASS |
| yes/no exactly ±0.15 (78/120, 42/120 vs 1/2) | ±3/20, kept | same | PASS |
| rounded figure within half a unit: R1 eff 0.1500 (4 dp) | margin 3/20 + 1/20000, dropped | same | PASS |
| R1c +0.150 (0.00055) | 3/20 + 11/20000, dropped; +0.149 gives 0.14955, kept | same | PASS |
| C1 s5 recovered 18/120 from 3-dp shares | 3/20 + 1/2000, dropped | same | PASS |
| rule named for one seed only | R2: 18/120, items 120, kept; R1: eff 1/10 over 300 items, kept | same | PASS |
| rule of each class, counted and each uncounted kind | R1: M, EXCL for every lineage, EXCL limited to one stem, a3:/a4: stripped, `im:` not stripped. R2: P (`(P`), P by name, artifact by name, artifact by shape, artifact at level 0, partial, construct (counted), cue (counted), NEW (P)/(partial) for their own stem, NEW name on another lineage (counted). M1: PROC, PROC by name and definition, a3 rule with a non-entry partner (counted). C1: EFF_SM, M.\* and H.\* literal entries, M.\* that is not an entry (counted), C.\* in the battery, A3_MUT in a3, BATTERY_MUT in the battery (counted), C.\* in a3 (counted), closed-form M/H entries, M.no_back in closed forms (counted) | as expected | PASS |
| lineage not on the survivor list (R1, R2, M1, C1) | no row | none | PASS |
| exact R1 rule that is an entry / that is not | listed and set aside / listed, counted, dropped | same | PASS |
| lineage written under an alias id (s5 `C1.slices` → `C1.slices_f4`; a3 primary key alias) | read under the survivor id | same | PASS |
| survivor missing from one unit's output (R2a seed 2; M1b one level; C1c f5) | exit 3, only `STOP unit=… lineage=…`, no file written | same | PASS |
| R2 `[cond]` k/n 1/8 vs k/napp 1/4 | both computed, the larger drops | same | PASS |
| shape-dependent R2 rule per shape (removals=0 k=20/20 uncounted; removals=1 6/60) | kept (summed would be 66/120) | kept | PASS |
| same rule, removals=1 12/60 | 1/5 dropped (summed would be 12/120) | same | PASS |
| same rule given only over shapes together (shape `-`) | counts on that figure, 1/5 | same | PASS |
| M1 key ending `__within_applicable` (M1a own, M1b) | not read | not read | PASS |
| M1 pair that is an entry / same name for another lineage | uncounted / counted, dropped | same | PASS |
| `EFF_F` 0.200 with every single rule below | dropped | same | PASS |
| R1 row and M1 row with an item count other than the plan's | 2/15 over 240; 16/115 over 230; listed | same | PASS |
| M1 against chance and against `base` (base 0.1499, 0.1500, 0.1499; rate 0) | vs chance kept; base row 2249/15000 + 1/20000 kept; vs base margin 4501/30000, dropped | same | PASS |
| amendment rule on its lineage / scored for another | uncounted / counted, dropped | same | PASS |
| C1 a3 with run_log fallback (alias_rc 1) / without | own file read, 3/5, fallback listed ×3 / alias file read, 1/20 | same | PASS |
| C1 battery `MF_shape_cv` per shape | round(0.375×16) = 6 per seed, 3/20 + 1/2000, dropped | same | PASS |
| f5/f5b shares | round(share × n) | same | PASS |
| R-46 fields (oracle_any_literal, best_generic_in_shape, mode_rate, mode_insample, answer_echoed_anywhere) written high | not read | not read | PASS |
| `MF_printform_cv` 0.200 | counted, dropped | same | PASS |
| error-marker shapes (s5, a3, battery) | not read | not read | PASS |
| R1c line with 6 values | engineering stop | stop | PASS |
| a3 survivor absent from run_log | engineering stop | stop | PASS |

## The fourteen choices (item 2)
1. **OK.** "stops … if any such lineage has no row in that unit at any level or seed". A stop goes to the lead and keeps or drops nothing.
2. **OK.** The text is silent. Reading values with unknown levels is impossible, and dropping the rule would lean toward passing; a stop leans neither way. See P9 for the risk at run time.
3. **OK. Neither formula is wrong.** The text's formula is "round(share × items of the shape)". Only the in-shape rate times `n_shape` is a hit count, so the script's formula is the text's. `f4b_pool_v2.py:77` uses round(`share_of_level` × n), the same count from a coarser figure; "as f4b does" names the method, recovery by rounding. At 3 dp and n = 2,000, the script's recovery is exact for shapes up to 1,000 items and off by at most 1 hit per seed otherwise. The script lists every decision that f4b's formula would change.
4. **OK (strict).** Point 7: "A script that writes a figure rounded to d decimals leaves an uncertainty …". At the plan size the recovery error is at most 1/2000 per seed, so 0.0005 covers it. For the closed forms (4 dp) recovery is exact, so 0.00005 is extra strictness.
5. **OK.** The text counts `MF_shape_cv`. Point 6 says to recover shares per shape and sum them. Shapes under 20 items have no entry and count as misses, as the battery's figure stands.
6. **OK.** M1a "is named by its section and key". Separate rows are stricter than merging two streams.
7. **OK.** This is `f_pool.py`'s R-34 reading (lines 122–132). Mixed answer types have different bases and are listed.
8. **OK.** K5 applies "for … an item with an open answer". For yes/no, `effect()`, `eff()` and `f_rules_new.py` all use k/napp against 0.5.
9. **OK.** "The larger absolute value decides".
10. **OK.** This matches "counts no hit and that seed's items".
    - Taking the smallest count leans strict.
    - A count of 0 occurs only where the seed has no item of that group, which `f_pool.py` also skips.
    - The plan-count fallback cannot be reached for a lineage the output must contain.
11. **OK.** "rows that are error markers and not rules, are not read".
12. **OK.** `fired` is a count. `acc_fired` has 4 dp, and with n ≤ 10,000 a written 1.0 implies exact. Exactness only affects the list and decides nothing.
13. **OK (note).** The text says "run again unchanged". Only the output prefix differs, which keeps both attempts and their hashes, and an assert checks that nothing else differs. Earlier commands of a chain are re-run deterministically. Pooling a retried unit needs `--dir-override` (P10c).
14. **OK.** "each entry is a unit, a lineage and a rule's name as that unit's output names it". The list is empty.

No choice is marked TEXT SAYS OTHERWISE or LEANS TOWARD PASSING. The one point found that leans toward passing is P3, which the text itself prescribes.

## Field table and R-46 (item 3)
Each field below was confirmed from committed code at `b78e58b1` to use the answers of the items it is scored on. Each stays not read, and the **table needs no change.**

| Field | Where (file:line at b78e58b1) | What it uses |
|---|---|---|
| `oracle_any_literal`, C1 battery | `studies/m0/c1_fix3_battery.py:723` (`row["key"] in lit_set(tree)`), `:754` (mean over the scored items) | the item's own key |
| `oracle_any_literal`, a3 | `docs/reviews/m0-lineage-decision-2026-11-25/audit3_c1/a3_shortcuts.py:556` (`row["key"] in ints`), `:630` | the item's own key |
| `best_generic_in_shape` | `c1_fix3_battery.py:739–752`: per shape, the generic rule with the most `pv == x["key"]` over `sub`, rated on the same `sub` | a best-of choice made and scored on the same items |
| R1b `mode_rate` | `final_r1/a4copy/heuristics4.py:634`: `Counter(b.answer for b in its)` with `its` the scored draw (line 612) | in-sample mode |
| M1a `mode_insample` | `studies/m0/m1_fix3_shortcuts.py:449`: `Counter(ans)` over the scored items | in-sample mode |
| M1a `answer_echoed_anywhere` | `m1_fix3_shortcuts.py:449` and `audit4_m1/shortcuts_a4.py:231`: `ans[i] in numl[i]` | the item's own answer |

- `MF_printform_cv` (`a3_shortcuts.py:615`) is a 2-fold cross-validated rule. It is read and counted (case C1-19).
- No written field is missing. I compared every writer's keys (R1 aud/impl/feat in both units, R2a/R2b/f_rules_new, M1a three sections, M1b/M1c, s5, a3, battery, f5/f5b) with the table.
- The script stops on any field that is not in the table (`FieldTable.check`).
- The decimals in the table match the writers' `round()` calls.

## Class-table application (item 4)
- **R1:** the bare name drops only a leading `a3:`/`a4:`. The 13 `EXCL` names apply only to their stem, and the others to every lineage. Units are R1a and R1b only, so an R1c rule named after an `M` entry counts.
- **R2:** the `klass()` clauses run in order and the first match decides. That gives the same result as "any uncounted clause matches", because the counted classes come last in `klass()`. The shape-dependent and level-dependent entries work as tested. `[NEW] ` rules are matched by name and stem only.
- **M1:** the class is decided by stem and prefixed key. In the a4 section the key is taken as written.
- **C1:** entries apply only within their own source (`a4`, `battery`, `a3`, `closed forms`), and measures match only measure entries.
- Each of these was tested with a made-up row (case table).

## Runner and plan (item 5)
- **Runner:**
  - It runs the plan's argv and cwd exactly. The environment is the plan's plus PATH and HOME.
  - It refuses a non-empty output directory, a non-empty retry directory, or a unit already recorded, and opens stdout and stderr with `xb`.
  - It hashes outputs without reading them, and retries once into `<dir>_retry1`.
  - On a second failure it prints only the unit and the exit statuses (`t2_attempt1`). No figure is printed.
  - Required changes: P1 and P2.
- **Plan** (`check_plan.out.txt`, 0 problems):
  - Unit order R1a…C1c.
  - Output directories are `/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/<unit>/seed<i>` and `…/m0_fresh_run_dry_20261126/<unit>`. Every write is inside its unit's directory.
  - No path points at `_scratch` or a smoke folder.
  - The four bases re-derive from `sha256('400002|fresh-shortcut|i')` and `…-dry-run`. Every one of the 104 unit and role integers re-derives as `sha256("<base>|<unit>|<role>")[:8]`, and each sits at its argv or env position. With the 4 bases, all 108 integers are distinct.
  - Every command has `PYTHONHASHSEED=0` and `PYTHONDONTWRITEBYTECODE=1` (see P7 for `-I`).
  - C1a `--timeout 3000` equals `final_c1/f3_a3_run.py:34` (`timeout=3000`).

## Files in this directory
`scripts/` (generators, checkers, runner-test plans), `fixtures/` (made-up outputs), `runs/` (pooling outputs on fixtures), `runner_test/`, `*.out.txt`, `*.stdout.txt`, `*.stderr.txt`, `SHA256SUMS.txt`. Leftovers kept as they are: `fixtures/main` (v1, unused), `check_cases_main2_attempt1.out.txt`, `runner_test/t1*`. The `work/` copies of committed files, one level up, are reading aids.
