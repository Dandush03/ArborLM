# M0 fresh run, stage 1S point 2: the eleven run units, read from the scripts at b78e58b1

Independent engineering reading by an arbor-auditor context (Claude Opus 5.5). Not Astra validation, not human approval.
Astra review: NOT_PERFORMED. Nothing was run: every fact below is from reading source at commit
`b78e58b1f47619f070dfc6c0a88999d345b1a34b` (`git show b78e58b1:<path>`), cited as file:line. `D/` =
`docs/reviews/m0-lineage-decision-2026-11-25/`. "Table" = the row of stage 1S point 2 in ADR-0033 addendum 1 at `d70ba38d`.
How a unit's seeds and lineages must be supplied (command line vs run copy) follows from these facts; the copies themselves
are not my task. "Stream" names the generator each seed feeds.

## R1a: `studies/m0/r1_fix4_measure.py`

- Command line (r1_fix4_measure.py:6, 88-92): `python -m studies.m0.r1_fix4_measure <n_per_level> <aud_seed> <aud_fit> <impl_seed> <impl_fit> <out_dir> [shape id ...]`, positional, no argparse. Pool of min(#ids, 10) processes (:94).
- Seeds: four on the command line (:88). `aud_seed` -> test items `gen.items(lin, lv, n, aud_seed)` (:44), stream `random.Random(root + level)` (r1_fix4_gen.py:21); `aud_fit` -> fit draw of **400** items, a literal (:33); `impl_seed`, `impl_fit` -> `r1_fix3_battery.measure(lin, n, impl_seed, impl_fit)` (:75), whose fit draw is **300** items, a literal (r1_fix3_battery.py:1080), stream `random.Random(base * 1000 + level)` (r1_fix3_battery.py:1060). Four further seeds are literals in an imported module: `feature_rows` (r1_fix4_tells.py:57-60) uses fit/test roots 8300/8400 (`FEATS_1`) and 8500/8600 (`FEATS_2`) with fit **3,000** and test **1,000** items (defaults of `feature_rows(lin, nf=3000, nt=1000)`, called as `feature_rows(lin)` at r1_fix4_measure.py:80), stream `Random(root + level)`. These four can be set only in a run copy of `r1_fix4_tells.py` (S1) with the import at r1_fix4_measure.py:26 redirected (S4).
- Lineages: command line (`sys.argv[7:]`, :92); default `sorted(r1_fix4_gen.lineages())` = `candidates_v4()` (r1_fix4_gen.py:16-17), a function. Fitted lookups exist only for the bases in `FEATS_1`/`FEATS_2` (r1_fix4_tells.py:24-36), keyed by base id via `base_of` (:39-40): of the survivor list, `R1.knights_knaves_r6`, `R1.boolean_lights_r4`, `R1.conditional_threshold_rule_r4`, `R1.categories_default_exceptions_r4`.
- Output: per lineage, in `<out_dir>`: `<id>.aud.jsonl` (:71-73; fields lineage, level, heuristic, n, chance, fired, acc_fired, eff, anti; 4-decimal rounding, :68-70), `<id>.impl.jsonl` (:76-78; same nine fields), `<id>.feat.jsonl` (:81-83; r1_fix4_tells.py:64: eff, anti=None, acc_fired=None, fired=n=1000). Standard output: `<id> done` (:96).
- Table: correct as far as it goes. Not stated in it: the fit draws are fixed in code at 400 (audit battery) and 300 (implementer's battery), not N (see REPORT, D3).

## R1b: `D/final_r1/run_rules_final.py`

- Command line (run_rules_final.py:8, 63-68): `python <this> <n> <aud_seed> <aud_fit> <impl_seed> <impl_fit> <feat_fit> <feat_test> <n_feat> <out_dir> [ids...]`, positional. Pool of min(12, #ids) (:70).
- Seeds: six on the command line (:64). `aud_seed`, `aud_fit` are passed to the copied audit-4 battery through `sys.argv` (:41-42); `a4copy/heuristics4.py` main draws the fit set of **400** items, a literal (heuristics4.py:600), and the test set of n (:612), stream `random.Random(seed_base + level)` (final_r1/fgen.py:23, via a4copy/gen4.py). `impl_seed`, `impl_fit` -> `r1_fix3_battery.measure` (:45; fit 300 as in R1a). `feat_fit`, `feat_test` -> fit and test draws of `n_feat` items each (:52).
- Lineages: command line (`a[9:]`, :68); default `sorted(fgen.lineages())` = `registered_v4()` (fgen.py:14-15), a function. Within each process the audit battery is selected by **substring**: `filt = lid` (:41) and `if filt and filt not in lid: continue` (heuristics4.py:596). Fitted lookups only for the four ids of `feat_defs` (:17-27), a lineage-keyed table whose four ids are all on the survivor list.
- Output: in `<out_dir>`: `<id>.aud.jsonl` (written by heuristics4.py:594, 636-638; adds `mode_rate`), `<id>.impl.jsonl` (:46-48), `<id>.feat.jsonl` (:49-58; eff rounded to 4, fired = n = n_feat). Standard output: `<id> done` twice per lineage (heuristics4.py:640 and :72).
- Environment: `fgen.py:7-9` puts the absolute path of the implementation worktree first on `sys.path` (REPORT, F1).
- Table: correct ("six on the command line"; N 3,000; n_feat 3,000).

## R1c: `D/final_r1/new_rules_final.py`

- Command line (new_rules_final.py:5, 156): `python <this> <n> <FIT> <TEST>`, positional, module-level code, no `__main__` guard, no pool.
- Seeds: `FIT`, `TEST` on the command line; test draw `fgen.items(lin, lv, n, TEST)` (:170), fit draw of n for each lookup `fgen.items(lin, lv, n, FIT)` (:176); stream `Random(root + level)` (fgen.py:23).
- Lineages: only the keys of `SPEC` (:158-165), a lineage-keyed table of six ids, one of which (`R1.conditional_decision_tree_r6`) is not on the survivor list (s3_ids.out.json). No command-line selection.
- Output: **standard output only** (:179-180): one line per lineage and rule, `f"{lid:36s} {h[:60]:60s} eff ... anti ..."`, values printed with 3 decimals of figures rounded to 4 (:145); no item count is written. One rule name is longer than 60 characters and is printed truncated: `lookup (asked on at start, #switches wired to it, #presses parity)`; no two names collide after truncation (s5_checks.out.json).
- Environment: imports `fgen` (:8-9), so the F1 absolute path applies.
- Table: correct ("two on the command line (FIT, TEST)"; N 3,000).

## R2a: `studies/m0/r2_fix4_battery.py run`

- Command line (r2_fix4_battery.py:7, 163-173): `python -m studies.m0.r2_fix4_battery run [--n 2000] [--seeds {a4,f4}] --out OUT.json [--only a,b] [--procs 8]`. `--seeds` defaults to `a4` (:167): the run plan must pass `--seeds f4`.
- Seeds: a string tag, a literal: `tag = "a4r2" if seeds == "a4" else "fix4"` (:90); train stream `random.Random(f"{tag}|{lid}|{lv}|5")`, test `...|6` (:93-94); train and test draws both `--n` items (:95-96). Settable only by a run copy (S1).
- Lineages: command line `--only` (comma list; a name without a dot gets `R2.`; :178-180), filtered from `sorted(fix4_set())` (:177), a function. Default: all of `fix4_set()`.
- Output: one JSON file `--out` (:183): `{"n", "seeds", "lineages": {lid: {level: {shape: {"n", "answer_type", "distinct_answers", ["yes_share"], "rules": {name: {k, napp, nerr, acc_all, acc_app}}}}}}}` (:106-128). Rules with napp = 0 are not written (:123). Standard error: `wrote <path>` (:184). `"seeds"` records the literal choice `f4`, not the seed.
- Table: correct.

## R2b: `D/final_r2/f_rules.py`, then `D/final_r2/f_rules_new.py` with `f_new_heur.py`

- `f_rules.py` command line (:11, 18-19): `python <this> N OUT.json [names]`, module-level argv parsing; the header requires cwd = worktree root and `PYTHONPATH=.` (:11). Pool(10) (:96).
- `f_rules.py` seeds: literal tag `finalr2` in `random.Random(f"finalr2|{lid}|{lv}|5")` (train) and `|6` (test) (:61-62); both draws N items (:63-64).
- `f_rules.py` lineages: command line `argv[3]`, comma list of names **without** `R2.` (:19, 55); default `SURV` (:16), 19 names of which `digit_root` and `interval_scheduling` are not on the survivor list.
- `f_rules.py` output: JSON `OUT.json` (:99): `{"n", "seeds": "<literal description>", "lineages": {lid: {level: {shape: {"n", "answer_type", "distinct_answers", "rules": {name: {k, napp, nerr}}}}}}}` (:74-90); every rule is written, napp = 0 included (:89). Standard output: `<lid> <secs>s` (:100-101). Batteries: `audit4_r2/a4_heur.H`, `audit3_r2/a3_heur.H` by `sys.path.insert` of cwd-relative dirs (:17, 39-41), and `studies.m0.r2_fix3_heuristics.OWN` (:42). `EXTRA` (:20) is never set by anything in the closure (f_rules_new.py does not import f_rules.py).
- `f_rules_new.py` command line (:3, 7): `python <this> N OUT.json`; header requires `PYTHONPATH=.:<deliver>`; run as a file from `final_r2/`, its own directory is `sys.path[0]` and `from f_new_heur import NEW` (:24, 54) resolves there.
- `f_rules_new.py` seeds: literal tag `finalr2`, **test draw only**: `random.Random(f"finalr2|{lid}|{lv}|6")` (:29), N items (:30); there is no train draw.
- `f_rules_new.py` lineages: `sorted(NEW)` (:56), the keys of the lineage-keyed table `NEW` built by the `@rule` decorator in `f_new_heur.py` (:8-15): 15 names, of which `digit_root` and `interval_scheduling` are not on the survivor list, and 4 survivors (`caesar_shift`, `cellular_automaton`, `dictionary_rank`, `sort_list`) have no entry. No command-line selection.
- `f_rules_new.py` output: JSON `OUT.json` (:57): `{"n", "lineages": {lid: {level: {shape: {"n", "answer_type", "rules": {"[NEW] name": {k, napp, nerr}}}}}}}` (:36-48); standard output lines for effects above 0.05 or nerr > 0 (:58-64), with `k / n` for open answers.
- Table: correct ("the seed tag `finalr2`, by a run copy; one tag for both scripts").

## M1a: `studies/m0/m1_fix4_battery.py`

- Command line (m1_fix4_battery.py:13-14, 203-208): `python -m studies.m0.m1_fix4_battery [--n 2000] [--workers 6] --out OUT.json [--only a,b]`; header: `PYTHONHASHSEED=0 PYTHONPATH=<worktree>`. Spawn pool (:215).
- Seeds: three literals, **none in this file**: own `SEED = 410302` (studies/m0/m1_fix3_shortcuts.py:29; stream `stream(SEED, "fix3-shortcuts", lid, str(lv))`, :423); a4 `SEED = 17` (D/audit4_m1/shortcuts_a4.py:25; used in its `run` at :188 through `common_a4.items`, stream `stream(seed, "audit4-m1", tag, lin.id, str(level))`, common_a4.py:26); a3 `SEED = 5` (D/audit3_m1/shortcuts_a3.py:20; read by this file as `mod.SEED`, :124, stream `stream(seed, "audit3-m1", tag, ...)`, common_a3.py:20). The a4 and a3 files are loaded by `importlib` from paths computed as `Path(__file__).resolve().parents[2] / "docs" / ...` (:33-36, 72-96). Line :220 writes the literals `{"own": 410302, "a4": 17, "a3": 5}` into the output whatever seeds were used (check 6, K15).
- Lineages: `--only`, comma list matched by **substring** (`any(o in i ...)`, :211) over `sorted(_current_set(True))` = `load_all()` including not-registered lineages (:81-82, 209). Default: all of `load_all()`. A lineage whose id contains `digit_puzzle` is scored on `min(n, 300)` items (:213); **no lineage of the M1 survivor list contains `digit_puzzle`** (survivor_list_of_record.json).
- Output: one JSON `--out` (:220): `{"n", "seeds" (literal), "exclusions", "raw": {own|a4|a3: {lid: {level: {...}}}}, "summary"}`; per level `N`, `base`, `rates`, `minus_base` (4-decimal rounding: own as m1_fix3_shortcuts writes it, a4 shortcuts_a4.py:231-233, a3 :152), a4 also `best_echo`, `answer_echoed_anywhere`, `within_applicable`; `raw.a3.<lid>.a3_skipped_items` (:153). Standard output: progress lines (:218), `seconds` (:221).
- Table: "its three seed literals (own, a4, a3), by a run copy" is right on the mechanism but not on the place: the three literals are in three imported/loaded files, not in `m1_fix4_battery.py` (REPORT, D4).

## M1b: `D/final_m1/rules_a5.py fresh`

- Command line (rules_a5.py:19, 244-251): `python <this> fresh N SEED out.json` (or `repro N out.json`), positional; needs cwd = worktree root (`AUD = Path("docs/reviews/...").resolve()`, :37; manifest open, fm1_common.py:17) and `PYTHONPATH=<worktree>` (fm1_common.py:5; rules_a5.py:34-35 import `studies` without inserting the root). Spawn Pool(14) (:247).
- Seeds: one on the command line (:249); items `stream(seed, "final-m1-a5", "rules", lin.id, str(level))` (fm1_common.py:31-33), N items for every lineage (no `digit_puzzle` cap).
- Lineages: `sorted(survivors())` (:246), a function (fm1_common.py:14-21) that asserts `load_registered()` equals `studies/m0/manifests/m1_fix4_survivors.json` `survivors`. That manifest's 29 ids equal the M1 survivor list of record's 29 (s5_checks.out.json).
- Output: JSON `out.json` (:251): `{"mode", "N", "seed", "label", "results": {lid: {level: {"N", "base", "rates", "minus_base", "within_applicable", "a3_skipped_items", ["one_op_best"], ["asked_is_largest_observed_vs_uniform"]}}}}` (:216-217, rounding to 5 decimals for rates/base, 4 for within_applicable). Standard output: `done <n>` (:256).
- Table: correct.

## M1c: `D/final_m1/rules_a5_attempt1.py fresh`

- Same as M1b at rules_a5_attempt1.py:238-249 (argv :243; output :245). The only code differences from M1b are the candidate order of the echo rule's tie-break (rules_a5.py:87-99, 178 against attempt1 :85-93, 172), plus the header lines 16-17.
- Table: correct.

## C1a: `studies/m0/c1_fix4_draw.py`; on its draw `D/audit4_c1/s4_rules_v2.py`, then `D/audit4_c1/s5_analyse_v2.py`; and `studies/m0/c1_fix4_a3_run.py` with `D/audit3_c1/a3_shortcuts.py`

- `c1_fix4_draw.py` command line (:8, 91-97): `python -m studies.m0.c1_fix4_draw [--per-level 400] [--seed 71] --out DIR [--ids a,b] [--workers 8]`. Seed: `--seed`, stream `sha256("fix4c1|<seed>|<lineage>|<level>")[:8]` -> `random.Random` (:35-37). Lineages: `--ids` (fix-4 / written ids, `all_written()[lid]`, :60, 99); default `audit4_set()` (a function, :40-52) plus the five `RULE_ALIAS` keys (:99). Output: `DIR/<alias name without C1.>.jsonl.gz`, one row per item `{"lid" (the RULE_ALIAS name), "lv", "i", "src", "key", "q", "retries", "atype"}` (:75, 82-85), and `DIR/meta.json` (:100-101).
- `s4_rules_v2.py` command line (:10, 624-629): `python -I s4_rules_v2.py GEN_DIR OUT_DIR [k1,k2]` (the header says `OUT_JSONL_GZ`; the code treats argv[2] as a directory). No seed, no lineage table: every `*.jsonl.gz` of GEN_DIR, or the names in argv[3]. Output: `OUT_DIR/<same file name>` gzip JSONL, one record per item `{"lid","lv","i","key","shape","R","err"}` (:600-620). Pool of 6 (:630).
- `s5_analyse_v2.py` command line (:12, 65-66): `python -I s5_analyse_v2.py RULES_DIR OUT_JSON`. Output: JSON `{lid: {level: {"n","parse_fail","shapes","distinct_keys","MF","MFsh","EFF_S","EFF_SM","EFF_F","rules": {"<shape>|<rule>": {"rate_in_shape","share_of_level","n_shape"}, "<shape>|MF_in_shape_cv": {...}}}}}` (:76-88), all figures rounded to **3** decimals; standard output: a compact table (:90-94).
- `c1_fix4_a3_run.py` command line (:8, 65-70): `python -m studies.m0.c1_fix4_a3_run --gen DIR --a3 PATH --out DIR [--timeout 900]`. **`--timeout` default 900** (:69), seconds, per subprocess (:60), settable on the command line. Lineage ids: from the draw's file names (:73-74), relabelled with `A3_ALIAS` (25 entries, :21-47) when the file name is a key; on a non-zero exit the draw is re-run under its own id (:78-87). Output: `OUT/in/<tag>/<name>.jsonl.gz` (relabelled copies, :51-58), `OUT/<tag>.json` with `<tag>` = `<name>__alias` or `<name>__own` (:59), `OUT/run_log.json` (:90-91). Subprocess: `[sys.executable, "-I", <--a3>, d, res]` (:60); `a3_shortcuts.py` output JSON `{lid: {level: {"n","MF_cv","MF_printform_cv","MF_shape_cv","BEST_generic_cv","BEST_generic_chosen","oracle_any_literal","shapes","S": {"<shape>|<rule>": {"hit","applies","n_shape","rate_in_shape","ci","share_of_level","mf_in_shape_cv"}},"distinct_keys"}}}` (a3_shortcuts.py:604-635). In this output `share_of_level` is the **shape's** share of the level (`len(sub) / n`, :627), not a hit share as in s5.
- Seeds: only the draw's `--seed`. Table: correct.

## C1b: `studies/m0/c1_fix4_battery.py`

- Command line (:9, 50-56): `python -m studies.m0.c1_fix4_battery [--per-level 400] [--seed 83] --out OUT.json [--only a,b] [--workers 8]`.
- Seed: `--seed`; stream `sha256("fix3-battery|<seed>|<lid>|<level>")[:8]` (c1_fix3_battery.py:647-649).
- Lineages: `--only` (:60) with the ids **the battery knows**, i.e. the fix-3 / older names: `bat.all_lineages()` (c1_fix3_battery.py:652-658) has no `*_f4` id; the five fix-4 builders are reached under their `RULE_ALIAS` names through the patch (:25-38). Default: `audit4_set()` (:60). Shape rules apply only to ids ending `_f3` (c1_fix3_battery.py:720); `C1.func_branch` and `C1.slices` get generic rules only (header :6-7).
- Output: JSON `--out` keyed by the fix-4 id where `SWAP` has one (:64-68); per level `{"n","MF_cv","MF_shape_cv" (per shape),"BEST_generic_cv","BEST_generic_chosen","best_generic_in_shape","oracle_any_literal","shapes","S": {"<shape>|<rule>": {"hit","n_shape","rate"}},"distinct_keys","retries"}` (c1_fix3_battery.py:753-755). Standard output: progress and a summary table (:66, 69).
- Table: correct.

## C1c: `D/final_c1/f1_draw.py`; on its draw `s4_rules_v2.py`, then `s5_analyse_v2.py`; `D/final_c1/f3_a3_run.py` with `a3_shortcuts.py`; `D/final_c1/f5b_closed_forms_v2.py`; `D/final_c1/f5_closed_forms.py`

- `f1_draw.py` command line (:10, 115-121): `python <this> --seed S --per-level N --out DIR [--workers 8] [--ids a,b]`; `--seed` and `--per-level` required. Inserts `os.getcwd()` into `sys.path` (:16). Seed: stream `sha256("finalc1|<seed>|<fix-4 id>|<level>")[:8]` (:27-29). Lineages: `--ids` (:123); default `SURVIVORS` (:18-22), 27 ids, one of which (`C1.sieve_marking_f4`) is not on the survivor list. Output: `DIR/<ALIAS name without C1.>.jsonl.gz` rows `{"lid" (ALIAS name), "fid" (fix-4 id), "lv","i","src","key","q","retries","atype"}` (:104-110) and `DIR/meta.json` (:130-132). `ALIAS` (:23-24) equals `RULE_ALIAS` of c1_fix4_draw.py.
- s4 and s5: as in C1a.
- `f3_a3_run.py` command line (:7, 57): `python <this> GEN_DIR A3_SCRIPT OUT_DIR`, positional, no timeout argument. **Timeout: `timeout=3000`, a literal** (:34), seconds, per subprocess; not settable without a copy. Relabelling by `A3_OLD` (21 entries, :13-21); outputs as in c1_fix4_a3_run (`OUT/in/<tag>/...`, `OUT/<tag>.json`, `OUT/run_log.json`, :26-33, 65). ThreadPool of 6 (:61).
- `f5b_closed_forms_v2.py` / `f5_closed_forms.py` command line (f5b :15, 144; f5 :14, 143): `python3 <this> GEN_DIR OUT_JSON`. No seed. Lineages: keys of `FNS` (f5b :140, f5 :139), five ids, of which `C1.sieve_marking_f4` is not on the survivor list; each opens `GEN_DIR/<base>.jsonl.gz` with the base from an inline map (f5b :147-148, f5 :146-147). Output: JSON `{fid: {"per_level": {lv: {rule: share rounded to 4}}, "n_per_level", "errors"}}` (f5b :163-165, f5 :162-164); standard output one line per lineage. The two files differ in one code line (f5b :91 against f5 :90) and the header.
- Seeds: only the draw's `--seed`. Table: correct.
- `--timeout`: the text's "3,000 as check 6 reads it" is confirmed: f3_a3_run.py:34 `timeout=3000`; c1_fix4_a3_run.py:69 default 900.
