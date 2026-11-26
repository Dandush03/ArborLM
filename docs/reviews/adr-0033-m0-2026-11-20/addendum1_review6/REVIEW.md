# Check 6 of ADR-0033 addendum 1, draft 6 (narrow scope: the fresh shortcut run of section 4A stage 1S)

**Verdict: APPROVABLE AFTER REQUIRED CHANGES.** 0 blocking, 12 required (K1 to K12; one is TEXT MUST CHANGE BEFORE APPROVAL, eleven CAN BE A CONDITION OF APPROVAL), 8 notes (K13 to K20).

- Ran as: `arbor-auditor` role, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. I did not write the addendum, ADR-0033, any earlier review or check, the rule scripts or the implementation. This check is independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. Scientific choices are marked PENDING LEAD REVIEW.
- What I did not do: run a model, run any rule script, generate any item, compute any lineage figure, read any run output file (`*.json`, `*.jsonl`, `*_out.txt`, `*.log` of the M0 record), read a sealed value, download anything, or change git state anywhere. I read the five lineage ids in `drops_after_final_checks.txt` and nothing else in that file. I did not read the survivor manifests.
- Reviewed: `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` at `944484eb` on `claude/m0-spec`. SHA-256 `dfe51d782d69151ad5d7b604ca4c43d04206415f5c62e2379baeddd67efd09e5`, the same in the working tree and in `git show 944484eb:`. I read the diff against `56a018dd` (177 insertions, 68 deletions in this file) and check 5 (`addendum1_review5/REVIEW.md`). ADR-0033 is `7719f6d4…ec90b`, as the addendum cites.
- The drafter's script reproduces its cited hashes: `addendum1_rev6_fresh_run.py` `b442b17e…120a`, output `4d20979e…8919`. I did not re-run it. I wrote my own code (below).
- Human lead's record: `HUMAN_LEAD_WORDS_8.md` `a3c0ae5d…9499` in worktree `agent-a0c9d741ea96ce52f`, HEAD `27769002`. It matches the hash the addendum cites. The words are "Yes, fresh run".
- Code read with `git show` / `git ls-tree` / `git diff` / `git grep` at `b78e58b1` (and `7cd0ac5a`, `27769002`) in worktree `agent-a0c9d741ea96ce52f`. I read headers, seed handling, scoring and output code, and class functions of every unit script and the main dependencies. I checked that `git diff 7cd0ac5a 27769002 -- studies tests src` is empty, and that neither `fresh-shortcut` nor `cluster-partition` occurs in `studies`, `tests` or `docs` at `27769002`. Both hold.
- Environment: macOS 27.2.1 arm64, uv 0.12.15, CPython 3.12.14, the locked environment of worktree `agent-a0c9d741ea96ce52f`, standard library only. Commands, run from that worktree with `D=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_addendum1_check6_20261126/deliver`:
  - `timeout 300 uv run --locked python -I -B $D/k6_path_rule.py /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f > $D/k6_path_rule.out.txt` (read-only `git ls-tree` and `git show` subprocesses)
  - `timeout 120 uv run --locked python -I -B $D/k6_seeds_se.py /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt > $D/k6_seeds_se.out.txt`
- Process:
  - The Write tool refused this path, because it is outside this session's worktree, so every file here was written with a shell heredoc. No other path was written.
  - Both scripts ran first time; there are no failed attempts.
  - Two wording slips in my own files, left unedited. In `k6_seeds_se.out.txt`, "0.149 + 0.00055 < 0.15 <= 0.1500" means "the largest printed value below the bound, 0.149, plus the largest error stays below 0.15". In `k6_seeds_se.py` there is a dead `for … pass` loop. Neither changes any number.

## Scope 1. J1 to J8 of check 5

| Item | Status | One line |
|---|---|---|
| J1 (which files record a run; what a rule script is) | **moot** | The membership rule is withdrawn (§4A stage 0, "Withdrawn"). The path rule that replaces it is mechanical: my listing equals the drafter's (scope 2). |
| J2 (byte-identity test of 4(b)) | **moot** | Withdrawn with the membership rule. No past run is pooled. |
| J3 (the further pooling script has no definition) | **partly fixed** | Points 6 to 8 now define the pooled figure, its base and its comparison. Several outcome-relevant readings are still open: K1, K5, K6, K7, K8. |
| J4 (the class of a rule) | **partly fixed** | "Strict resolution" stated: committed code only, two readings count, no class counts. Still open: the M/P/H mapping (K9), M1's "name and definition" against `pool_a5.py`'s name-only test (K7), R2's shape-dependent class (K6) and C1's `EFF_F` (K8). |
| J5 (map file carries statuses) | **fixed** | §3 item 6: "It carries no registration status"; a separate versioned status record; one hash of the map, re-checked at G-gen and F. |
| J6 (no default when a status differs from R-38) | **moot** | §4A 1S point 11: "The result of the fresh run governs … There is nothing for anyone to answer on a difference." |
| J7 (which checks may remove a lineage after the record) | **fixed** | §4 item 7 and §7 item 10: after the partition, only the capacity stage removes a lineage, read on all eight parts, and "no cheap-rule script is run again after the fresh run". A different gap is new: removal by stage-2 judgement after the fresh figures exist (K10). |
| J8 (top list incomplete; "nothing left" wording) | **partly fixed** | A9, A10, A16, A20, A21, A23, A26, A27, R-7 and item 19 are now listed, and the wording is corrected. Still missing: the new readings of K5 to K11 and the M/P/H mapping (K12). |

## Scope 2. The scripts rule applied to `git ls-tree -r --name-only b78e58b1`

`k6_path_rule.out.txt`: 12,788 paths in the tree. Pattern (a) matches 6, pattern (b) 11, and (c) names 3, all present. The union is **20, identical to the drafter's twenty**. There are no differences in either direction.

**Rule scripts that the patterns miss** (from reading every unmatched `.py` under `final_*/` and every `studies/m0/*fix4*.py`):
- `final_r2/f_interval_diag.py` scored a cheap rule in the final checks. It runs `'[impl] shortest first'` (from `r2_fix3_heuristics.OWN`) on `R2.interval_scheduling` level 0 over 10 extra seed sets, and its header says "DIAGNOSTIC ONLY (not pooled …)". Leaving it out changes nothing: its rule is already in R2a and R2b, and `R2.interval_scheduling` is in `drops_after_final_checks.txt`.
- `final_r2/f_harness_check.py` re-runs `f_rules.py`'s batteries at the implementer's seeds. It has the same rules and is a reproduction check.
- Nothing else that scores a rule. `final_r1/weekday_hops.py` gives a distribution of path lengths and scores no rule. The poolers and summarisers (`pool_final.py`, `f_pool.py`, `f_new_summ.py`, `pool_a5.py`, `f4_pool.py`, `f4b_pool_v2.py`, `c1_fix4_rules_table.py`, `r1_fix4_table.py`) are replaced by the new pooling script, but **they hold definitions the new script needs** (K5, K7).

**Matched files that are not rule scripts:** `c1_fix4_draw.py` and `final_c1/f1_draw.py` (item draws), `c1_fix4_a3_run.py` and `final_c1/f3_a3_run.py` (subprocess wrappers), and `audit4_c1/s5_analyse_v2.py` (an analyser: it computes `MF`, `MFsh` and the `EFF_*` measures from `s4_rules_v2.py`'s records). Each is a necessary link of a unit chain, so including them is harmless. `rules_a5_attempt1.py` and `f5_closed_forms.py` are superseded rule scripts, included by design.

## Scope 3. Seeds (`k6_seeds_se.out.txt`)

- From the text's derivation, with my own code: `'400002|fresh-shortcut|1'` → 16103270370041696293, `|2` → 10773834973117025986, `|3` → 619660634241804713, and `'400002|fresh-shortcut-dry-run'` → 3342082268851962967. All four **agree** with the text.
- Per-unit integers: 26 roles per base, typed from point 4's text. All 104 agree with the drafter's output part A (0 differences). Sample: base 1, R1a `aud_seed` → 99048509648598239; base 2, M1a `a3` → 2546003605200785130; base 3, C1c `seed` → 878078140576336163; dry, R2b `tag` → 16488324911911726946.
- 108 integers, **all distinct**, all below 2^64. None equals any registered value of ADR-0033 §12 (400001–400013, 400031, 400032, 409001–409099, 953001–953999; the smallest of the 108 is 9.9 × 10^16). None equals the integer of `400002|development`, `|capacity`, `|cheap-rule`, `|fresh-shortcut` or `400004|cluster-partition|{cross,R1,R2,M1,C1}`.
- The R1 scripts form per-level streams by adding to the seed (K17). Under both forms (`s + level` and `s*1000 + level`), the 896 effective R1 integers are distinct. The smallest gap between two R1 role integers is 3.0 × 10^15, so no streams overlap.

## Scope 4. Standard errors at the bound

Recomputed as √(p(1−p)/n). They agree with point 5 to four decimals:

| Evaluation | n over three seeds | Open, p = 0.15 | Yes/no, p = 0.65 | p = 0.5 |
|---|---|---|---|---|
| R1 | 9,000 | 0.0038 | 0.0050 | 0.0053 |
| R2, M1 | 12,000 | 0.0033 | 0.0044 | 0.0046 |
| C1 | 6,000 | 0.0046 | 0.0062 | 0.0065 |

The dry run has n = 20: 0.080 at p = 0.15 and 0.112 at p = 0.5. Two exceptions to "the items per level" are written into the scripts (K15). For M1a's `digit_puzzle` lineages, n = 900 over three seeds gives 0.0119. R1a's feature lookups test on 1,000 items per seed.

## Scope 5. The drafter's calls

| Call | Stated as a rule in the text? | Leans toward passing? | Exercisable after fresh figures? |
|---|---|---|---|
| (a) chance base for all; M1 also against its own base, larger deciding | Yes (point 7) | No: unfavourable. **M1's "both ways" is redundant (K14).** All M1 answers are open and `base` is counted as a rule, so \|R−B\| > 0.15 implies R > 0.15 or B > 0.15. The drop set is the chance-only set except at a rounding edge. The one inconsistency is that R2 keeps 0 for closed answers with k > 2 (K19) | No |
| (b) run copies differ only by seed, set or path | Yes (point 3) | Neutral as written, but **insufficient** (K2) and **S2 is ill-defined for lineage-keyed rule tables** (K3). Both failures resolve, through the dry run, toward exclusion, which favours passing | No (before the hashes); the copy auditor's calls are made with past figures in view |
| (c) three seeds | Yes (point 4) | Toward dropping (the maximum over many rules, §12 item 25) | No |
| (d) rounded figures compared at the upper end | Yes (point 7) | Slightly unfavourable. The double rounding in `new_rules_final.py` gives 0.00055, not 0.0005, which is harmless on the 1/3000 grid (K16) | No |
| (e) R1 exact rows set aside | Yes, "strictest form", "only if" | **Yes, favourable** | No: mechanical. For R1c (three decimals, no count of fired items) the "only if" cannot be met, so nothing there is set aside (K16) |
| (f) M1 extension of `PROC` by name | Yes, but "same name **and definition**" contradicts `pool_a5.py`, which tests the name only (K7) | **Yes, favourable** | No, if fixed before the hashes |
| (g) doubtful classes count; R1 `M`, R2 `P`, C1 `H` uncounted | "Doubt counts" is a rule. The M/P/H mapping is the drafter's reading (§12 item 19(d)), not in the files (K9) | M/P/H uncounted: **favourable**, not flagged as such in the top list | No, if fixed before the hashes. Otherwise the table builder decides, with past figures in view |
| (h) class table built by an auditor before the run | Yes (point 8) | Depends on K9: which governs when the table and the list differ is unstated | No |
| (i) a unit failing twice stops the run | Yes (point 11) | Neutral. But the human lead then decides with other units' outputs possibly existing (K11) | **Yes**, by the human lead, unless the outputs stay unread |
| (j) solver disagreement at the freeze: engineering stop, not drop | Yes (§4 item 7) | Keeps a lineage pending his decision, with the split in view. Disclosed (top list item 5) | By the human lead only, as a recorded departure |
| (k) dry-run failures: plan errors corrected, code errors exclude | Yes (point 10) | **Favourable**: exclusion only removes rules. Failures caused by the dry run's small N would be classed as code (K4). Two predictable failures exist now (K3) | No (before the run seeds), but made with past figures in view |

**Can the uncounted sets of (e), (f) and (g) be written as a closed list from committed code at `b78e58b1`, without running anything?**
- (e) **No**, by construction: it depends on results. It can be bounded in advance: the class table can list per R1 lineage the rule names eligible for the exemption. Whether to restrict it so is PENDING LEAD REVIEW.
- (f) **Yes.** `PROC` is a literal dict in `audit4_m1/short_summary_a4.py` (`pool_a5.py` reads it with `ast.literal_eval`), and the audit-3 rule names are literals in `audit3_m1/shortcuts_a3.py`'s spec. A list of (lineage stem, rule key) pairs can be written by reading. **The class table should carry that list, hashed before the run** (K7).
- (g) **Yes**, as literal sets or name predicates:
  - R1: `EXCL` and `M` are literal sets in `audit4_r1/final_table4.py`.
  - R2: `klass()` is a pure function of (rule name, shape, level) over the literal lists `MISREAD`, `PARTIAL` and `CONSTRUCT`.
  - C1: the prefixes `M.`, `H.`, `X.`, `C.`, `EFF_SM`, and the literal sets `A3_MUT` and `BATTERY_MUT` in `f4b_pool_v2.py`. The f5/f5b header prose (`F.pow_res_c0`, `F.affine_collapse`, `S.ignore_negative_step`, `S.no_even_branch`, `M.*`) needs to be written out as a literal list.

  **The text should require the class table to carry these as literal lists or predicates, copied with file hashes, and hashed before the run** (K9).

## Scope 6. Order: map hash → fresh run → candidates → partition → capacity

- **Could a link be judged with fresh figures in view?** No. The map is hashed at stage 1, before 1S, and the withdrawal of §3 item 2 is allowed only before that hash.
- **Could a removal happen with the split in view?** Only the capacity stage (read on all eight parts), solver disagreement in stage 4 (iii), and recorded departures to the human lead. All of these are mechanical or his. This holds.
- **New gap: a removal with the fresh figures in view.** Stage 2 runs after 1S. It includes judgements: "its wording read by the auditor", "levels distinct" (§12 item 16 leaves three R-40 cases undecided), and "the pair audited". Each can remove a lineage, and the fresh per-lineage figures exist by then. That is selection after a fresh figure is seen. It is not aimed at a part (none exists), but the candidate list fixes the partition deterministically, by known code and seed (K10).

## Scope 7. Undefined output fields (§12 item 19(e)) and 64-bit seeds (item 26)

- **Output fields: not acceptable as a bare condition.** A synthetic test checks the pooling script against "known answers", but the known answers are its author's reading of the text. Where the text admits two readings, the test can show disagreement and cannot settle it. Reading the scripts gave seven concrete, outcome-relevant field readings that the text leaves open:
  - output ids against survivor ids (K1);
  - R2 `[cond]` (K5);
  - R2's shape-dependent class (K6);
  - M1 `__within_applicable`, sections and prefixes (K7);
  - C1 `EFF_F` (K8);
  - the M/P/H mapping (K9);
  - R1c exactness (K16).

  Each needs a fixed definition, by text or by the exact condition sentences below. What is left after that is file names and key paths. That is acceptable as a condition, if the field table is hashed with the pooling script (K1's sentence).
- **64-bit seeds: acceptable as a dry-run condition.** By code reading, every seed path accepts arbitrary Python integers:
  - R1: `random.Random(s + level)`, `random.Random(s*1000 + level)`, `int(sys.argv[i])`;
  - R2: string tags `f"{tag}|…"`;
  - M1: `core.stream` over `str(seed)`;
  - C1: `sha256(f"…|{seed}|…")` and argparse `type=int`.

  My grep found no numpy or torch seeding in the unit scripts or the dependencies I read. The one open point is §12 item 26's fallback: "to the coordinating lead … as a change to this text". After approval, a change to the text is the human lead's (K20).

## Scope 8. The top list

It is incomplete; see K12.

## Findings

**K1 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S points 2 and 6: unit outputs are keyed by ids that are not survivor ids, and nothing requires every survivor to appear.**
- Defect:
  - `c1_fix4_draw.py` (`RULE_ALIAS`) and `final_c1/f1_draw.py` (`ALIAS`) write the draws of `C1.fast_power_f4`, `C1.func_branch_f4`, `C1.func_compose_f4` and `C1.slices_f4` under `C1.fast_power_f3`, `C1.func_branch`, `C1.func_compose_f3` and `C1.slices`. `c1_fix4_battery.py` measures them "under their original names".
  - The a3 wrappers relabel to old ids (`A3_ALIAS`, `A3_OLD`) and name files `<draw id>__alias|__own.json`.
  - Point 6 says "Rows for a lineage that is not on the survivor list … are not read." Read literally, it discards these rows, and four C1 lineages escape every rule of C1a, C1b and C1c. No sentence makes a survivor that is missing from a unit's output a stop.
- Smallest fix (condition sentence): "The run plan carries, for every unit, the map from every lineage id that can occur in its output (file names included) to the survivor-list id, taken from the alias tables of the hashed scripts (`RULE_ALIAS`, `ALIAS`, `A3_ALIAS`, `A3_OLD`) and checked by the auditor of point 3. It also carries a field table naming every output field the pooling script reads and every field it does not read. The pooling script stops, as an engineering stop before any figure is reported, if any lineage of the survivor list that the dry run did not exclude has no row in any unit, level or seed."

**K2 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S point 3: S1 to S3 do not cover two units.**
- R1a: the seed literals 8300, 8400, 8500 and 8600 are in `r1_fix4_tells.py`, which `r1_fix4_measure.py` imports as a module (`from studies.m0.r1_fix4_tells import feature_rows`).
- M1a: `SEED = 410302` is in `m1_fix3_shortcuts.py`, which `m1_fix4_battery.py` imports as `import studies.m0.m1_fix3_shortcuts as sc`.
- Making the copies used requires redirecting a module import, which is not a seed, a set or an absolute or scratch path. As written, the copy auditor must reject the copy or stretch S3. The dry run then risks excluding R1a's feature lookups or M1a's implementer battery, which favours passing.
- Condition sentence: "A copy may also differ by (S4) an import, or a module path given to `importlib`, of a listed script or dependency that is itself copied under S1 or S2, redirected to that copy and to nothing else; S4 is checked line by line like S1 to S3."

**K3 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S points 2, 3 and 10: a predictable dry-run failure, and S2 on lineage-keyed rule tables.**
- Defect:
  - `final_c1/f5_closed_forms.py` and `f5b_closed_forms_v2.py` open a draw file for each key of `FNS`. `FNS` starts with `C1.sieve_marking_f4`, which `drops_after_final_checks.txt` drops.
  - Point 2 gives the survivor ids to `f1_draw.py --ids`, so no sieve file is drawn, and both scripts end with `FileNotFoundError` before scoring `fast_power_f4`, `counter_list_f3`, `func_branch_f4` and `slices_f4`.
  - S2 says such a set "is left as it is". The text then lets the auditor class the failure as plan or code. "Code" excludes the closed forms, which favours passing.
  - The same structure is in `final_r1/new_rules_final.py`. `SPEC` maps six lineages (one of them `R1.conditional_decision_tree_r6`, also dropped) to their own rules. S2 ("replaced by a reading of the survivor list") cannot apply to it without changing rules.
- Condition sentence: "S2 applies only to a plain list of ids that selects which lineages are drawn or run; a table that maps lineages to their own rules is not a set and is never changed. Every draw command includes, besides the survivor list, every lineage that a hashed script's own lineage table names, so that each script runs as committed; rows of lineages not on the survivor list are not read."

**K4 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S point 10: dry-run failures caused by the dry run's own size.** At 20 items per level a shape group can be empty, or a mean or a `most_common(1)[0]` can be taken over nothing. Such a failure would be "own code cannot execute" and would exclude the unit, though it would not occur at the plan's N. Condition sentence: "Before a unit, or a unit for some lineages, is excluded, it is run once more on the dry-run seeds at the plan's N with its output discarded unread (only the exit status and the traceback are kept); it is excluded only if that run fails in the same way."

**K5 (REQUIRED, PENDING LEAD REVIEW; CAN BE A CONDITION OF APPROVAL). §4A 1S points 6 and 7: the figure of an R2 `[cond]` rule.**
- Committed code gives two readings for an open answer:
  - k/napp: `effect()` in `r2_fix4_battery.py`, `eff()` in `final_r2/f_pool.py`, `f_new_summ.py`;
  - k/n: the line `f_rules_new.py` prints, and the text's "as a miss for an open answer … in the R2 scripts".
- k/napp ≥ k/n, so the reading changes drops wherever a counted `[cond]` rule exists. The class table will show whether one does; `PARTIAL` and `klass()` name `[cond]` rules.
- Condition sentence (the reading of the audit-4 definition, the stricter): "For an R2 rule whose name contains `[cond]` and an item with an open answer, the figure is k / napp over the items where the rule applies, and napp is its item count, as `effect()` in `studies/m0/r2_fix4_battery.py` computes it." The alternative (k/n) is less strict and should be named as such if chosen.

**K6 (REQUIRED, PENDING LEAD REVIEW; CAN BE A CONDITION OF APPROVAL). §4A 1S point 8, R2: a class that depends on the shape.** `klass()` makes `"[a3] removal by deleting the minimum and keeping the order of the rest"` an artefact only in the shape `removals=0` of `min_heap_ops` (on `f_rules.py`'s survivor list), and a cue elsewhere. Point 6 sums over shapes (R-34), so one pooled rule mixes an uncounted and a counted class. `f_pool.py`'s all-shapes reading takes the class of whichever shape comes first. Condition sentence: "Where an R2 rule's class differs between shapes of a lineage and level, its counts are summed only over the shapes in which it is counted, and the figure is formed on those items."

**K7 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S points 6 and 8, M1: three readings.**
- (i) `m1_fix3_shortcuts.py` writes `X__within_applicable` keys into `rates` and `minus_base` (M1a's own section), and `rules_a5.py` writes a `within_applicable` field. `m1_fix4_battery.py`'s docstring says "`__within_applicable` duplicates are not rules". The text is silent, and under the chance base any such rate above 0.15 drops a lineage.
- (ii) M1a's output has three sections (`own`, `a4`, `a3`) whose keys carry no prefix, or other prefixes, than `PROC`'s. `pool_a5.py` maps `own` → `im:` and `a3` → `a3:`. "One name in one unit's output" does not say how a section enters the name or how `PROC` is matched.
- (iii) The text says "the same name **and definition**", but `pool_a5.py` tests the name only (`bare(k) in proc_bare`).
- Condition sentence: "In M1 outputs, keys ending in `__within_applicable`, the field `within_applicable`, and the fields `one_op_best` and `asked_is_largest_observed_vs_uniform` are not rules and are not read. A rule of M1a is named by its section and key, with the prefixes `own` → `im:`, `a3` → `a3:` and `a4` as written. A rule is the correct procedure, and not counted, if and only if its (lineage stem, prefixed key) pair is on the closed list that the class table writes from `short_summary_a4.PROC` and the audit-3 keys of the same name, by name only, as `final_m1/pool_a5.py` tests it." Whether "and definition" should be added (stricter) is PENDING LEAD REVIEW. If it is, the list must say per pair which source lines were compared.

**K8 (REQUIRED, PENDING LEAD REVIEW; CAN BE A CONDITION OF APPROVAL). §4A 1S point 8, C1: `EFF_F` is unclassed.** `s5_analyse_v2.py` writes `EFF_F`, the best of S, G, **M** and F rules chosen on one fold, at three decimals, beside `EFF_S` and `EFF_SM`. The text lists `EFF_S` as counted and `EFF_SM` as not, and does not mention `EFF_F`. By "a rule with no class counts" it counts, which counts the partial-trace `M.*` through it, against decided item 18. `f4b_pool_v2.py` does not read it. Condition sentence: "`EFF_F` of `s5_analyse_v2.py` is not read; the F.* rules it contains are read one by one." The alternative is that it counts, which is stricter and contrary to item 18 as to M.*.

**K9 (REQUIRED, PENDING LEAD REVIEW; CAN BE A CONDITION OF APPROVAL). §4A 1S point 8 and §7 item 4: the reading of R1 `M`, R2 `P`, C1 `H.*` (and `X.*`, `C.*`) as "the correct procedure", and which governs.** None of these labels is literally one of item 18's four classes. The text's own operative sentence ("A rule with a class that is none of the four … counts"; "where the files leave a doubt, the rule counts") lets the table builder count them. The text also says "the pooling script takes classes from [the table] and from nowhere else", and does not say whether the table or the drafter's list governs when they differ. Leaving them uncounted is R-31's reading and leans toward passing, but the top list does not name it as such. Condition sentence: "The labels R1 `M` and `EXCL`, R2 `P`, and C1 `H.*`, `X.*` and `C.*` are not counted, as R-31 had them; the class table copies every uncounted class as a literal set, prefix or predicate from the committed file with that file's hash, and writes the f5/f5b header classes as a literal list of rule names; where the table and this list differ, the stricter (counting) reading governs and the difference is reported before the hashes." Whether M/P/H should instead count is PENDING LEAD REVIEW.

**K10 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A stage 2: judgements that can remove a lineage are made after the fresh figures exist.** "Wording read by the auditor", "levels distinct" (three R-40 cases left open, §12 item 16) and "the pair audited" follow stage 1S. The candidate list they produce fixes the partition by known code and seed. Condition sentence: "The stage-2 conditions that are judgements (wording, levels distinct, the pair audited) are recorded and hashed for every lineage of the survivor list before any item of the three run seeds is generated; after the fresh run, stage 2 removes only the lineages the fresh run dropped and those failing the mechanical conditions already hashed."

**K11 (REQUIRED; CAN BE A CONDITION OF APPROVAL). §4A 1S point 11: a stop leaves fresh outputs in view.** If a unit fails twice the run stops and goes to the human lead, and the other units' outputs may exist. What he decides is open (§12 item 22). Condition sentence: "If the run stops under point 11, no output of any unit is pooled, summarised or read by anyone, and only exit statuses and tracebacks are reported, until the human lead's decision on the stop is recorded."

**K12 (REQUIRED; TEXT MUST CHANGE BEFORE APPROVAL). The top list, item 2, is incomplete for what approval carries.**
- Missing:
  - the M/P/H (and X/C) mapping, a third place that leans toward passing (K9);
  - the readings fixed by K1, K5, K6, K7 and K8;
  - the copy kinds and the S2 scope (K2, K3);
  - the stage-2 timing (K10) and the handling of a stop (K11);
  - item counts written into the scripts that differ from "the items per level and seed" the list states (M1a `digit_puzzle` at 300 per level; R1a feature lookups tested on 1,000; K15).
- The human lead approves from this list, so the list must carry these items before he approves. Smallest fix: add one bullet per item above under item 2, with its direction.

**K13 (NOTE). Scope 2.** No missed rule script changes anything. `f_interval_diag.py` is the one that scored a cheap rule in the final checks, and its rule and lineage are already covered or dropped. Five matched files are draws, wrappers or an analyser, needed as links of a unit chain.

**K14 (NOTE, PENDING LEAD REVIEW). §4A 1S point 7, M1 "both ways".**
- With every M1 answer open and `base` counted as a rule, the base reading adds no drop to the chance reading. The one exception is the rounding edge, where the text does not say whether a difference of two rounded figures carries one half unit or two.
- The real change is the chance base itself. Item 18's own reason ("the table he chose 0.15 from") points toward M1's own base for M1. §12 item 23 discloses the count as unknown. It should state this tension too.

**K15 (NOTE). §4A 1S point 5: item counts.**
- `m1_fix4_battery.py` caps `digit_puzzle` lineages at 300 items per level and seed (n = 900, SE 0.0119 at 0.15). `r1_fix4_tells.feature_rows` fits on 3,000 and tests on 1,000. Neither changes a rule, but point 5's "9,000 … 12,000" does not hold for them.
- `m1_fix4_battery.py` also writes the literal seeds `{"own": 410302, "a4": 17, "a3": 5}` into its output. Under "no output line is changed", the copy's output will misreport its seeds, so the run plan should record the true ones.

**K16 (NOTE). Rounding and R1 exact rows.**
- `new_rules_final.py` rounds to 4 decimals and then prints `+.3f`, so the largest error is 0.00055, not 0.0005. With equal n over three seeds the pooled mean lies on a 1/3000 grid and the outcome is unchanged.
- C1 shares written at 4 decimals give exact counts by round(share × n) for n < 10,000.
- R1c prints no count of fired items and only three decimals, so "answered every item and right on every one" cannot be shown. By the text's "only if", no R1c row is set aside. The text should say so in one clause.

**K17 (NOTE, for the seed-registry auditor; PENDING LEAD REVIEW).** ADR-0033 §12 says per-level streams are derived "never by adding to a seed". The R1 scripts do add: `random.Random(s + level)` in `r1_fix4_gen.py`, `fgen.py` and `gen4.py`, and `random.Random(base*1000 + level)` in `r1_fix3_battery.py`. Fed with seeds derived from 400002, they form M0-labelled streams by addition. There is no numeric collision (scope 3). Whether the rule binds these throwaway item-side uses goes with §12 item 7.

**K18 (NOTE). C1a timeout and the a3 fallback.**
- `c1_fix4_a3_run.py` defaults to `--timeout 900` per subprocess, used before at 400 items per level. At 2,000 items an uncaught `TimeoutExpired` ends the unit, so the run plan should set the timeout (`f3_a3_run.py` uses 3,000).
- If the alias run fails on one seed's items, both wrappers fall back to generic rules for that seed. Point 6 then dilutes the specific rules mechanically. The report of point 11 should list every alias failure.

**K19 (NOTE). §4A 1S point 7: two base definitions for R2.** "One definition … 1/k" sits beside "the R2 scripts take 0.5 for a yes/no answer and 0 for every other answer type; that is kept". The two differ for any R2 survivor with a closed answer and k > 2. R2 builders with `answer_type "name"` and `k = n` exist in the tree. I did not check whether a survivor uses one. The text should say which governs.

**K20 (NOTE). §12 item 26.** A seed that a script cannot take "would go to the coordinating lead … as a change to this text". After approval, a change to the text is the human lead's. Say "to the human lead, as a recorded departure, before any hash".

## Files

- `k6_path_rule.py`, `k6_path_rule.out.txt`: scope 2.
- `k6_seeds_se.py`, `k6_seeds_se.out.txt`: scopes 3 and 4.
- `SHA256SUMS.txt`: hashes of the four files above and this file.

Astra review: NOT_PERFORMED
