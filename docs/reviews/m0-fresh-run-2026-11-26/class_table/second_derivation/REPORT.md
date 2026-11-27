# M0 fresh run: second, independent derivation of the closed list of uncounted rules

ADR-0033 addendum 1 (draft 7 text at `d70ba38d`), section 4A stage 1S point 8, last bullet ("The class table, and the second derivation"), with points 6 and 8 and section 13 item 18 as the specification. Code read at `b78e58b1` (`b78e58b1f47619f070dfc6c0a88999d345b1a34b`) in the worktree `agent-a0c9d741ea96ce52f`, through `git show` only.

- Ran as: `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`), on 2026-11-26. I wrote none of the lineages, the rule scripts or the first list.
- **Astra review: NOT_PERFORMED.** This is independent engineering evidence. It is not Astra validation and not human approval.
- Not read: anything under `docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted*` or `addendum1_review6/`, in any worktree or commit, and nothing under `experiments/_scratch/m0_addendum1_*` (I saw those directory names in a listing of `experiments/_scratch/` and opened none of them). I read the addendum text, which states the first list's sizes and names some entries. I derived every entry below from code. Where an entry rests on the text and not on code, that is said in section 3.
- Not done: no rule script, pooling script or generator was run, imported or `exec`'d; no item was generated; no run output was opened; no lineage figure was computed. The derivation script parses source with `ast` and copies literals.

## 1. Counts

| Evaluation | Entries in `uncounted_rules_second.json` | Composition |
|---|---|---|
| R1 | **35** | 19 names of `M` (every lineage); 16 names of `EXCL`: 3 for every lineage, 13 limited to one lineage stem each |
| R2 | **38** | 35 atomic clauses of `klass()` (16 `P`, 6 `artifact`, 13 `partial`; 1 depends on the shape, 3 on the level); 3 `[NEW] ` rules (2 `(P)`, 1 `(partial)`) |
| M1 | **13** | 12 of the 13 `PROC` pairs, plus 1 audit-3 pair by name and definition (`ratio_share`, `a3:largest_share`) |
| C1 | **66** (63 distinct names per output family) | in the output of `s5_analyse_v2.py`: `EFF_SM`, the 50 `M.*` and 1 `H.*` names of `s4_rules_v2.py`; in the battery's output: 4 `C.*`; in the output of `a3_shortcuts.py`: the 4 of `A3_MUT`; in the outputs of the two closed-form scripts: `M.no_even_branch`, `M.style0_everywhere` and `H.negative_step_as_positive`, written **once per script** (2 × 3 = 6 entries) |

The C1 total is a format difference, not a difference of substance. The schema's `output_of` takes a single script, so the three closed-form names appear twice, once under `f5_closed_forms.py` and once under `f5b_closed_forms_v2.py`. Counted per name they are 63. A mechanical comparison against a list that writes the three once must collapse those pairs first.

All four counts match the sizes the addendum text states for the first list (35, 38, 13, 63). That is a comparison with the text and nothing more. I have not seen the first list's entries, so the entry-by-entry comparison is still to be made.

## 2. The judgements, and which way each went

R1
- **J1. Unit scope.** The entries apply to units R1a and R1b (`"unit_scope": "R1a,R1b"`). `final_r1/new_rules_final.py` (unit R1c) has no class code; I checked it for `EXCL`, `cls(` and `final_table4` and found none. A rule is matched by its bare name, as `bare()` of `final_table4.py` strips `a3:` and `a4:`. `feat:` rows are `C` or `A` under `pool_final.py` and count.
- **J2. `EXCL` against the battery.** All 16 `EXCL` names occur in `r1_fix3_battery.py`. 3 are in `EXCLUDED` (every lineage), so there is one reading and they are entries for every lineage. 13 are in `EXCLUDED_BY_SHAPE`, each under exactly one stem, so they are entries for that stem only and count elsewhere. The stem is the battery's `re.sub(r"_r\d+$", "", id.split(".", 1)[1])`. No `EXCL` name is missing from the battery, and the battery excludes no name that is outside `EXCL`. `M` and `EXCL` are disjoint.

R2
- **J3. Atomising `klass()`.** I wrote one clause for each literal in a tuple, an `or` chain or a list (`MISREAD`, `PARTIAL`), and kept the order of the code. This gives 37 atomic clauses: 35 uncounted and 2 `construct`, followed by the default `cue`. `clause_index` is **1-based** over all 37, and the 35 uncounted clauses are indices 1 to 35. `match` is the literal only. The operator (`equals`, `contains`, `startswith`) and the shape or level condition are in `uncounted_rules_second_detail.json`. If the first list numbers the clauses from 0, or numbers whole `if` statements, the indices must be mapped before comparing.
- **J4. Readings of `klass()`.** Clause 7 (`[a3] rules in reverse order`, artefact at level 0) is followed by clause 8 (the same name as `P`), so that rule is uncounted at every level. Clause 4 (shape `removals=0`) and clauses 5 and 6 (level 0) fall through to `cue` outside their condition. The body of `klass()` and its three lists are AST-equal in `final_r2/f_pool.py` and `studies/m0/r2_fix4_battery.py` once the type annotations are stripped, so the class has one reading. The two headers differ on *which classes count*: `f_pool.py` counts only `cue`, while `r2_fix4_battery.py` says "R-24 counts cue + partial + construct". That is a difference over counting, which item 18 settles. It is not a second reading of any rule's class, and I did not treat it as one. PENDING LEAD REVIEW only if the lead reads it otherwise.
- **J5. `[NEW] ` rules.** The output name is `"[NEW] " + name` (`f_rules_new.py`, `f_rules.py`). The label is the first parenthesised token of the name, so `[cond] (cue) …` is `(cue)`. The header defines `(cue)`, `(partial)` and `(P)`. I took `(partial)` = "truncated procedure" as partial trace and `(P)` as class `P`, giving 3 entries. `(artifact)`, used by one rule, is not defined in the header, so it has no class and counts. In `f_pool.py`, `klass()` is never applied to `[NEW]` names; they are read apart as `newrows`. So no code gives them a second reading. Applied to the names, `klass()` would give `P` for the two `(P)` rules (via `"(P" in hn`) and `cue` for the `(partial)` rule, and no `(cue)`-labelled rule hits an uncounted clause.

M1
- **J6. Which `PROC` reasons are a second reading.** Only a reason that itself says the rule is kept as a rule is taken as a second reading: `finite_differences` / `im:next_term_only` ("… kept as a rule"), which counts. I kept as entries the pairs whose reasons only qualify where the rule equals the procedure, with no other class named. These are `consecutive` (the 4-number case "only coincides"), `gcd_lcm` `im:` (k = 2), `prime_factors` (the cofactor), `slot_permutations` (the subclass) and `last_digit_power` (exponent ≤ p). For the two `gcd_lcm` `a4:` keys the reason says "NOT cheap … listed as a construct-validity issue". I read that as costly plus correct procedure, both uncounted, so the two keys are entries. If "construct-validity issue" is read as a class, it is none of the four, and those two keys would count. **PENDING LEAD REVIEW.**
- **J7. The extension by name and definition.** These are my readings of the test in point 8. (a) The audit-3 branch for a lineage stem is the `n == "<stem>"` branch of `spec()`. `last_digit_power` maps to `power_remainder`, as `rules_a5.py`, `rules_a5_attempt1.py` and `m1_fix4_battery.py` all write it (parsed). (b) The names a statement reads are its free `Load` names. Names bound in comprehensions and lambdas are excluded, and a nested `def` contributes its free variables. (c) "The last statement before" is the last textually earlier statement in `spec()` that binds the name and does not lie in a mutually exclusive `if` branch. (d) Parameters, module-level names and builtins are compared by name only. (e) **The dict `h` written into by `h["<name>"] = …` is not counted as a name the rule reads.** Under that reading one pair is equal: `ratio_share` `a3:largest_share` (`shortcuts_a3.py` line 82 against `m1_fix3_shortcuts.py` line 143). Four pairs differ and count: `k_minus_remainder_ignores_exact_fit` (304–305 against 376–377), `largest_le_sqrt` (162, 169 against 238, 245), `parity_fraction_of_total` (205–211 against 278–285) and `fermat_misapplied_e_mod_p_plus_1` (175, 176, 181 against 252, 254, 260). Six `PROC` `im:` rules have no audit-3 rule of the same name in their branch. **Under the literal Python reading, `h` is loaded by the assignment, so its binding is part of the definition.** The two bindings differ (`h = {}` against the annotated `h: dict[str, F | None] = {}`), which makes no pair equal and **would strike `a3:largest_share`, so it would count.** I took (e) because the dict is the output slot and not part of the rule. **PENDING LEAD REVIEW.** Adding the enclosing `if` guards to the test changes nothing: `ratio_share` has none.

C1
- **J8. `A3_MUT`.** The code (`measures()`) and the header's opening paragraph class the four as artefacts ("v2 classes them as artefacts"). Line 13 of the same header still says "partial trace", left over from v1. Both are uncounted classes, so the counting outcome is the same either way, and I kept the 4 as entries. Under a fully literal reading of "two readings of a class → counts" they would count. **PENDING LEAD REVIEW.**
- **J9. `BATTERY_MUT`** (12 rules, all present in `c1_fix3_battery.py`). The header says "NOT counted under the strict reading; counted by the implementer". That is two readings, so they count and none is an entry.
- **J10. `C.*` controls.** I took the 4 names written as stored keys in `c1_fix3_battery.py`. The battery's own `summarise()` skips `|C.` as well, so the class has one reading.
- **J11. Literal names.** `M.*` and `H.*` entries are the literals stored as dict keys in `s4_rules_v2.py`, including both arms of a conditional key. That gives 50 `M.` and 1 `H.` (`H.c_semantics`). The f-string names in that file are all `G.*`. `EFF_F` has no class in `f4b_pool_v2.py` and counts. `F.pow_res_c0` is `closed` by its prefix and "the unmodified algorithm" in the closed-form header. That is two readings, so it counts.
- **J12. The closed-form outputs** (see section 3). `f4b_pool_v2.py` never reads their outputs. The 6 entries apply `measures()`'s prefix map (`M` → partial, `H` → hazard) to the names written in `f5_closed_forms.py` and `f5b_closed_forms_v2.py`, because point 8 names those two scripts as sources of names for the C1 class code. Without that sentence of the text these outputs have no class and would count. **PENDING LEAD REVIEW.**

## 3. Entries justified only by the text

- **The mapping of a label to item 18's four classes**, as point 8 rules it, and not literally by code. R1 `M` (19 entries) and `EXCL` (16); R2 `P` (16 clauses and 2 `[NEW] (P)` rules); C1 `hazard` (`H.c_semantics` and `H.negative_step_as_positive` ×2) and `control` (4 `C.*`). The names in each set come from code. That these labels are uncounted classes comes from point 8's ruling. R1 `M` is the clearest case: the implementer's battery gives those names no class, so nothing in that file supports leaving them uncounted.
- **The 6 closed-form entries (J12).** No committed class code reads those outputs.
- No entry's **name** was taken from the text.

## 4. Discrepancies and failed attempts (kept)

- `derive_uncounted_second.py` (attempt 1) stopped with `STOP: computed rule name with a counted-out prefix f'L.e{k}'`. This was my error: the guard against computed names fired on the generic `L.*` f-string names, which play no part in any entry. It wrote no JSON. The output is in `derive_attempt1.out.txt`. `derive_uncounted_second_v2.py` differs from it by that one line (the guard limited to the prefixes `M`, `H`, `C`) and ran with exit status 0 (`derive_v2.out.txt`).
- `../src/` holds reading copies of 17 committed files, extracted with `git show b78e58b1:<path>` so that I could read them. The script does not use them; it reads through `git show` itself.

## 5. Commands and environment

From `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` (branch `claude/m0-impl`; only `git show b78e58b1:<path>` is read), macOS arm64, uv 0.12.15, Python 3.12.14 (`uv run --locked python -V`):

```sh
O=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_uncounted_second_20261126/deliver
PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python $O/derive_uncounted_second.py    <impl worktree> $O > $O/derive_attempt1.out.txt 2>&1   # exit 1 (section 4)
PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python $O/derive_uncounted_second_v2.py <impl worktree> $O > $O/derive_v2.out.txt 2>&1        # exit 0
```

The specification was read with `git -C …/arborlm-consolidation-experiment-2b31c1 show d70ba38d:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md`. The SHA-256 of each of the 23 committed files parsed is in `derive_v2.out.txt` and in `uncounted_rules_second_detail.json` (`source_files_sha256_at_b78e58b1`).

## 6. Files

- `uncounted_rules_second.json`: the list in the requested shape, sorted by its fields.
- `uncounted_rules_second_detail.json`: per entry, the operator, condition, reason and battery line; the rules considered that count, each with its reason; the M1 definition tests under the three readings; the source hashes.
- `derive_uncounted_second.py`, `derive_attempt1.out.txt` (failed attempt 1); `derive_uncounted_second_v2.py`, `derive_v2.out.txt`.
- `SHA256SUMS.txt`.
