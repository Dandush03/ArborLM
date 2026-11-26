# M0 fresh run, stage 1S points 1 and 2: the auditor's listing of the rule scripts and their dependencies

- Auditor: an `arbor-auditor` context, model **Claude Opus 5.5** (`claude-opus-5-5`, from session metadata), 2026-11-26.
- Status: independent engineering and mathematical evidence only. **Not Astra validation, not human approval.**
  **Astra review: NOT_PERFORMED.** I wrote none of the code listed and none of the specification.
- Specification read: `ADR-0033-addendum-1-lineage-clusters.md` at `d70ba38d` (stage 1S, points 1 to 11; status line there:
  "DRAFT 7 — NOT APPROVED"). The approval is recorded on `claude/m0-impl` at `f627389a`
  (`HUMAN_LEAD_WORDS_9.md`, read only to confirm that its one amendment concerns the class table, not points 1 or 2).
- Code read: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, commit `b78e58b1f47619f070dfc6c0a88999d345b1a34b`, by
  `git ls-tree` / `git cat-file` / `git show` only. Branch tip `claude/m0-impl` = `206d45a9b91cd38413c12e543e4d988d4d85d05f`.
- What I did not do: run any rule script, generator or test; generate any item; open any run output; compute any lineage
  figure; write anywhere but this directory. No file in any worktree was changed.
- Environment: macOS 27.2.1 arm64; `uv 0.12.15`; `uv run --locked python` = CPython 3.12.14 (the implementation worktree's
  locked venv), standard library only; git 2.54.0. Every script below was run as
  `cd <impl worktree> && PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this dir>/<script> > <this dir>/<script>.out.json`
  (s4_assemble.py writes `script_listing.json` itself and prints a count). System `python3` (3.15.1) was used only to print
  summaries of these JSON files to my terminal and once to correct three line citations in my own `UNITS.md`; no reported
  figure depends on it.

## Files

| File | What |
|---|---|
| `s1_list.py` -> `s1_list.out.json` | item 1: the path rule applied to `git ls-tree -r b78e58b1`, blob and SHA-256 of each match, comparison with the text's twenty, near misses |
| `s2_scan.py` -> `scan_a1.json` | first exploratory AST scan of three scripts (kept; superseded by s2_resolve) |
| `s2_resolve.py` -> `s2_resolve.out.json` | item 2, **attempt 1, kept**: missed the `importlib.import_module` edges inside `studies/m0` (71 dependencies) |
| `s2_resolve_v2.py` -> `s2_resolve_v2.out.json` | item 2, attempt 2: closure with those edges (128 dependencies); also the call sites examined, ambiguity and unresolved lists (both empty) |
| `s3_ids.py` -> `s3_ids.out.json` | item 3: literal lineage lists / lineage-keyed tables / alias tables against the survivor list of record (membership only) |
| `s4_assemble.py` -> `script_listing.json` | the deliverable listing |
| `s5_checks.py` -> `s5_checks.out.json` | item 4 per file: blobs of the closure at b78e58b1 vs the tip and vs 7cd0ac5a; M1 manifest vs record; R1c name truncation |
| `s6_seed_spacing.py` -> `s6_seed_spacing.out.json` | numerical hazard: re-derivation of the four base seeds, distinctness, no collision of R1 `Random(root + level)` / `Random(base*1000 + level)` streams |
| `s7_m1_substring.py` -> `s7_m1_substring.out.json`; `m1_names_grep.txt` | M1a `--only` substring hazard (the .txt is an earlier shell-grep version of the same name list, see "my own slips") |
| `UNITS.md` | item 3, one section per unit |
| `SHA256SUMS.txt` | SHA-256 of every file here except itself |

`script_listing.json` SHA-256 is in `SHA256SUMS.txt`. It is byte-identical on a second run of `s4_assemble.py`.

## Item 1: the path rule

Rule (a), (b), (c) of point 1 applied with `re` to the 12,788 paths of `git ls-tree -r b78e58b1` (s1_list.py):
**20 matches: 6 under (a), 11 under (b), 3 under (c). They are exactly the twenty the text names, with the same pattern
letter for each. No difference.** All three (c) paths exist at the commit. No path matches two patterns.
Near misses (same folders, `.py`, not matched; listed in `s1_list.out.json`) include the pooling scripts
(`final_r1/pool_final.py`, `final_r2/f_pool.py`, `final_m1/pool_a5.py`, `final_c1/f4b_pool_v2.py`) and
`studies/m0/c1_fix4_rules_table.py`; none of them is reached as a dependency of a listed script.

## Item 2: dependencies (128)

Method: AST of every file in the closure, all `import` / `from ... import` statements wherever they occur, resolved against
the ordered `sys.path` each entry has when it runs (`ENTRY_PATH` in s2_resolve_v2.py, taken from each script's own
`sys.path` handling and documented command); a package import counts its `__init__.py` files. Dynamic edges were found by
listing every `open`, `Path`, `read_text`, `exec`, `compile`, `subprocess`, `importlib`, `runpy`, `sys.path.insert`,
`glob`, `os.environ` call in the closure (printed in `call_sites`) and reading each; they are entered by hand with
file:line (`MANUAL`, `IMPORTLIB`). Result: no bare module name resolves in two directories of any entry's path; no import
is unresolved; nothing outside the repository except the standard library is imported (torch is not imported by any file of
the closure). The 20 listed scripts are not repeated among the dependencies; three of them are also reached from other
listed scripts (`a3_shortcuts.py` by the two a3 wrappers as a subprocess, `f_new_heur.py` by `f_rules_new.py`,
`c1_fix4_draw.py` by `c1_fix4_battery.py`).

By kind (an edge per reaching statement): import 1,217; importlib module name 186; importlib file path 8; file open 1;
subprocess 2 (both to the listed `a3_shortcuts.py`). By place: 114 under `studies/` (2 package `__init__.py`, 111 modules,
1 data file), 14 under `docs/reviews/m0-lineage-decision-2026-11-25/` (`audit3_m1/{common_a3,shortcuts_a3}.py`,
`audit4_m1/{common_a4,shortcuts_a4}.py`, `audit3_r2/{a3_heur,a3_solvers}.py`, `audit4_r2/a4_heur.py`,
`final_m1/fm1_common.py`, `final_r1/fgen.py`, `final_r1/a4copy/{gen,gen4,heuristics3,heuristics4,solvers3}.py`).
Every dependency the text names is present: `r1_fix3_battery.py`, `r1_fix4_a3_heur.py`, `r1_fix4_a4_heur.py`,
`r1_fix4_tells.py`, `r2_fix4_a3_heur.py`, `r2_fix4_a4_heur.py`, `r2_fix3_heuristics.py`, `c1_fix3_battery.py`,
`m1_fix3_shortcuts.py`, the audit folders' rule files, `final_r1/a4copy/` (all five files).

The one data file: `studies/m0/manifests/m1_fix4_survivors.json` (opened cwd-relative by `final_m1/fm1_common.py:17`,
reached by M1b and M1c). Every dependency exists at `b78e58b1`. The importlib loops of
`lineages_r1_fix3_common.py:40` and `lineages_r1_rev4_common.py:39` tolerate a missing module; every module they name
exists at the commit, so nothing is skipped.

Breadth: the R1, R2, M1 and C1 entries each reach the whole lineage-module family of their evaluation (e.g. all
`lineages_r1_*` builders through `lineages_r1_common.load_pilot`), because the loaders import every family module. This is
what executing them loads; whether a given builder is called is a run-time question, so all are listed and hashed.

### Flags (item 2)

- **F1 (absolute path; needs S3 if the run is not in that worktree).** `docs/.../final_r1/fgen.py:7`
  `W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"`, put first on `sys.path` at
  :8-9. Reached by R1b (`run_rules_final.py:35`, and `a4copy/gen4.py:6`) and R1c (`new_rules_final.py:9`). Effect: every
  `studies.*` import of R1b and R1c comes from **that worktree's working tree**, whatever the cwd. That working tree is at
  the tip `206d45a9`, not at `b78e58b1`, and holds two untracked `.bak` files; every file of the closure has the same blob
  at `b78e58b1` and at the tip (s5_checks), so today it is equivalent, but only while nothing there changes. If the run
  executes from another checkout, R1b and R1c silently import generators from this one.
- **F2 (scratch paths).** None in code. Scratch paths appear only in docstrings and reports.
- **F3 (cwd-relative paths; the run must start from the worktree root).** `final_r2/f_rules.py:17, 39-40` (`REV`, the
  audit folders put on `sys.path` relative to cwd); `final_m1/rules_a5.py:37` and `rules_a5_attempt1.py:35` (`AUD`);
  `final_m1/fm1_common.py:17` (manifest); `studies/m0/c1_fix4_draw.py:90`, `c1_fix4_battery.py:49`,
  `c1_fix3_battery.py:786` (`sys.path.insert(0, ".")`); `final_c1/f1_draw.py:16` (`os.getcwd()`).
- **F4 (`__file__`-relative paths: a run copy in another directory breaks them unless redirected).**
  `studies/m0/m1_fix4_battery.py:33` `ROOT = Path(__file__).resolve().parents[2]`: a copy at
  `studies/m0/fresh_run/m1_fix4_battery.py` gives `ROOT = <worktree>/studies`, so `AUDIT_DIR` (:34-36) and the four
  importlib loads (:87-96) point at paths that do not exist. M1a needs a copy (its seeds, F/D4), so this must be handled
  under S4 (the importlib paths to the copied `shortcuts_a4.py`/`shortcuts_a3.py`) and S3 for `ROOT`. Also
  `audit4_m1/shortcuts_a4.py:22` and `audit3_m1/shortcuts_a3.py:17` put their own directory on `sys.path` to import
  `common_a4`/`common_a3`; in M1a those are pre-loaded into `sys.modules` (m1_fix4_battery.py:76, 87, 94), so a copy
  elsewhere still finds them there. `run_rules_final.py:13`, `new_rules_final.py:8`, `a4copy/gen4.py:5`,
  `a4copy/heuristics3.py:17`, `a4copy/heuristics4.py:17` are file-relative as well (no copy is needed for R1b or R1c,
  which take seeds and ids on the command line, except under F1).
- **F5 (environment the text does not name).** Scripts run as files that import `studies` without putting the root on
  `sys.path` need `PYTHONPATH=<worktree root>`: `f_rules.py` and `f_rules_new.py` (headers :11 and :3 say
  `PYTHONPATH=.`, `.:<deliver>`), `rules_a5.py`, `rules_a5_attempt1.py` (fm1_common.py:5). The final auditors ran with it
  (FINAL_R2.md:10, FINAL_M1.md:11). Point 1 fixes `PYTHONHASHSEED=0` and `PYTHONDONTWRITEBYTECODE=1` only; the run plan
  must carry `PYTHONPATH`. The `studies/m0` scripts must be run with `-m` (their usage lines).
- **F6 (subprocesses).** `c1_fix4_a3_run.py:60` and `f3_a3_run.py:34` run `[sys.executable, "-I", <a3 path>, ...]`; the
  path is a command-line argument, so the run plan chooses it (relative or absolute). `-I` drops `PYTHONPATH` and the cwd;
  `a3_shortcuts.py` imports the standard library only, so that is harmless. A timeout raises `subprocess.TimeoutExpired`,
  which neither wrapper catches: the unit stops (c1_fix4_a3_run.py:60; f3_a3_run.py:34 inside `ThreadPoolExecutor.map`,
  re-raised at :62). `studies/m0/c1grammar.py:176` runs `sys.executable -I -S -c <inline string>` (no file; in
  `run_isolated`, which no listed unit calls as far as I read).
- **F7 (not a dependency, recorded).** `r1_fix3_battery.py:1150-1151` appends to the file named by `FIX3_ALL` only in its
  own `main()`, which no unit calls; the run plan should not set `FIX3_ALL` anyway. `lineage_gates.py` writes manifests only
  in functions no unit calls (it is imported inside a function of `lineages_r1_shortcuts.py:570`).
- **F8 (copy and S4).** `audit4_m1/shortcuts_a4.py:174` imports `studies.m0.m1_fix3_shortcuts.spec` by module name. If
  `m1_fix3_shortcuts.py` is copied for its seed (S1), point 3 S4 says imports of it are redirected "to that copy and to
  nothing else"; read literally, the copy of `shortcuts_a4.py` (needed for its own seed) then also needs that redirect.
  The `spec` function is the same in both files, so no figure changes either way; the copy checker should know.

## Item 3: units (details in UNITS.md)

The table of point 2 is right on scripts, N and how each seed enters for 9 of the 11 rows. Differences:

- **D1 (M1a, "its three seed literals").** None of the three literals is in `m1_fix4_battery.py`. They are
  `SEED = 410302` (studies/m0/m1_fix3_shortcuts.py:29), `SEED = 17` (audit4_m1/shortcuts_a4.py:25) and `SEED = 5`
  (audit3_m1/shortcuts_a3.py:20, read by the battery as `mod.SEED`, :124). Point 3's S4 example names only
  `m1_fix3_shortcuts.py`; the two audit files are loaded by `importlib` file path from `m1_fix4_battery.py` (F4), so M1a
  needs three copied dependencies plus a copy of the battery whose importlib paths and `ROOT` are redirected.
- **D2 (M1a item count).** Point 5 states that M1a scores a lineage whose id contains `digit_puzzle` on min(N, 300) items
  and gives standard errors for it. The code is as stated (m1_fix4_battery.py:213), but **no M1 lineage on the survivor list
  of record contains `digit_puzzle`**, so no row the pooling script reads has that count.
- **D3 (fit / training draws).** Point 2: "A draw of the same size for fitting or training is made wherever the script makes
  one." Several fit draws have sizes fixed by literals and cannot be N without changing a script: R1a audit battery 400
  (r1_fix4_measure.py:33), R1a and R1b implementer battery 300 (r1_fix3_battery.py:1080), R1b audit battery 400
  (a4copy/heuristics4.py:600), R1a lookups fit 3,000 / test 1,000 (r1_fix4_tells.py:57, the K12 rows). Equal-size draws:
  R1c (n), R2a and `f_rules.py` (N), R1b lookups (`n_feat`). `f_rules_new.py` makes no training draw; M1 and C1 fit within
  the one draw by two folds. **PENDING LEAD REVIEW** only as to the reading of the sentence; nothing in a script changes.
- **D4 (lineage-keyed table not named in S2(b)).** `NEW` of `f_new_heur.py` is both R2b's lineage selection for
  `f_rules_new.py` (`sorted(NEW)`, :56) and a lineage-keyed rule table. It holds `digit_root` and `interval_scheduling`,
  which are not on the survivor list. Point 3 S2(b) names `FNS` and `SPEC` as its cases but not `NEW`; the general wording
  covers it, and `f_rules_new.py` needs a copy anyway (S1 tag). Whether its copy removes the two entries is for the run
  plan; if both copies sit in one directory, `from f_new_heur import NEW` reaches the copy without an S4 edit.
- **D5 (R1c output).** R1c writes no file and no item count: standard output only, 3 decimals, rule names cut at 60
  characters (one name is cut; no collision). The text already says R1c writes no count (K16); the truncation is not stated.
- **D6 (C1b ids).** "Where a script takes lineage ids on its command line they are given there": `c1_fix4_battery.py
  --only` accepts only ids its battery knows, i.e. the `RULE_ALIAS` names for the five fix-4 lineages
  (`C1.fast_power_f3`, `C1.func_branch`, `C1.func_compose_f3`, `C1.slices`, `C1.sieve_marking_f3`); a `*_f4` id is not in
  `all_lineages()` (c1_fix3_battery.py:652-658). Its output then writes them under the fix-4 id (`SWAP`, :64). R2b
  `f_rules.py` takes names without `R2.`. The K1 map should be read for inputs as well as outputs.
- **D7 (timeouts) — confirmation, no difference.** `c1_fix4_a3_run.py:69` `--timeout` default 900 s, settable;
  `final_c1/f3_a3_run.py:34` `timeout=3000` s, a literal. The text's 3,000 is right.

Other facts the run plan needs (not differences): R2a defaults to `--seeds a4` (:167) and must be given `--seeds f4`;
R2a and R2b and M1a write a literal or descriptive "seeds" field that is not the seed used (as K15 says for M1a);
R1b selects its audit battery by substring (`heuristics4.py:596`) and M1a's `--only` matches by substring
(m1_fix4_battery.py:211): no survivor id is a substring of another survivor id in any evaluation (s3_ids), and no M1
survivor id is a substring of another of the 64 M1 names visible in the builder modules (s7; the full `load_all()` set needs
execution); `A3_ALIAS` (25) and `A3_OLD` (21) differ by four keys, none of them a survivor's draw name;
`f1_draw.ALIAS` equals `c1_fix4_draw.RULE_ALIAS`; the M1 manifest that `survivors()` asserts against holds the same 29 ids
as the survivor list of record, so M1b and M1c need no lineage copy; `s4_rules_v2.py`'s header says `OUT_JSONL_GZ` but its
second argument is a directory (:617, 625).

**PENDING LEAD REVIEW (field table, not my scope to decide).** Outputs carry fields that point 8's C1 list neither counts
nor leaves uncounted by name: in the battery's output `best_generic_in_shape` (in-shape best generic rule, chosen and scored
on the same items, c1_fix3_battery.py:738-754) and `oracle_any_literal`; in `a3_shortcuts.py`'s output `MF_printform_cv`
and `oracle_any_literal`. By point 8 ("a rule with no class counts") they would count unless the field table says they are
not rules. Also: in `a3_shortcuts.py`'s output `share_of_level` is the shape's share of the level (:627), not a hit share as
in `s5_analyse_v2.py` (:82); point 6's recovery of hits by round(share × items) must use `hit`, which that output writes.

## Item 4: diffs

- `git diff 7cd0ac5a b78e58b1 -- studies tests src`: **empty** (0 bytes). The drafter's check `git diff 7cd0ac5a 27769002
  -- studies tests src`: also empty.
- `git diff --name-status b78e58b1 claude/m0-impl -- studies tests src`: two added files only,
  `studies/m0/fresh_run/build_survivor_list.py` and `studies/m0/manifests/survivor_list_of_record.json`, the expected
  additions. No `studies/m0/*.py` file of `b78e58b1` is changed or removed. The tip also adds
  `docs/reviews/m0-fresh-run-2026-11-26/survivor_list_audit/*` and `HUMAN_LEAD_WORDS_6..9.md`; no listed script or
  dependency changes (s5_checks: 0 of 148 closure files differ between `b78e58b1` and the tip).
- Against `7cd0ac5a`, 18 closure files differ: all are under `final_r1/`, `final_r2/`, `final_m1/`, `final_c1/` and are
  **absent** at `7cd0ac5a` (added later), none changed; every `studies/` file of the closure is identical.

## Numerical hazards checked

- Seeds of point 4: the four bases re-derived as sha256(label)[:8] big-endian match the printed integers; 26 role integers
  per base; all 108 distinct (s6). R1 scripts seed `random.Random(root + level)` and `Random(base * 1000 + level)`; over all
  R1 roles, the three seeds and the dry-run base no two such streams coincide; the smallest gap between `root + level`
  roots is about 3.0e15 (s6).
- Rounding written by the scripts (for point 7's half-unit rule): R1 outputs 4 decimals (R1c prints 3 of 4); R2 writes
  counts; M1a 4, M1b/M1c 5 (`within_applicable` 4); `s5_analyse_v2.py`, `a3_shortcuts.py` and the C1 battery 3 decimals
  (with `hit` counts in the latter two); closed-form scripts 4. The text's example names `new_rules_final.py`; the
  3-decimal C1 outputs carry 0.0005.

## Discrepancies that were my own slips (kept)

1. `s2_resolve.py` (attempt 1) missed the `importlib.import_module` loops inside `studies/m0` and found 71 dependencies;
   attempt 2 adds them (128). Both outputs are kept.
2. Three line citations in my first `UNITS.md` were wrong (shortcuts_a4.py 236-238 for 231-233; c1_fix3_battery.py 719
   for 720 and 752 for 753); corrected in place before hashing. One citation in this REPORT (c1_fix3_battery.py 739-751
   for 738-754) was corrected the same way.
3. A shell command `uniq -c -w 7` failed (macOS `uniq` has no `-w`); re-run as `sort | uniq -c`: 18 absent, 0 changed.
4. The M1 substring check was first done with a shell grep (`m1_names_grep.txt`, kept) and system `python3`; re-done as
   `s7_m1_substring.py` under `uv run --locked python` with the same result.

Astra review: NOT_PERFORMED. This is not human approval, and no result here is a success or a validation of anything.

## Addendum: the branch tip moved during this audit

At the end of the audit the implementation worktree's HEAD and `claude/m0-impl` were `4991501e`
("stage 1S point 8: second derivation of the closed list ...", 2026-11-26 11:56 -05:00), one commit after `206d45a9`; I made
no commit there. It adds 14 files under `docs/reviews/m0-fresh-run-2026-11-26/class_table/` only. Re-run of item 4 against
it (`s5_checks.py` -> `s5_checks_tip4991501e.out.json`; `git diff --name-status b78e58b1 4991501e -- studies tests src`):
0 of 148 closure files differ from `b78e58b1`; the only `studies` changes are the same two expected additions.
`SHA256SUMS.txt` was written before this addendum and is kept as it was; `SHA256SUMS_final.txt` covers every file here,
this REPORT as amended included.
