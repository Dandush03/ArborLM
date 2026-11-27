# M0 fresh run: independent recomputation of the pooled result

**Verdict: REPRODUCED WITH DIFFERENCES.** The 15 drops, their deciding rows and the counts per evaluation (R1 10→6, R2 17→16, M1 29→24, C1 26→21; 67 left) are reproduced exactly from the raw outputs with the auditor's own code. All 33,521 rows that both poolings define agree to the exact fraction, and so does their counted/uncounted status. The differences are below. None changes any lineage's status: one is in uncertainty bookkeeping (the script is stricter), one in reporting (exact R1 rows), and one is a reading both poolings share (R2 levels with two open answer types).

Auditor: Claude Opus 5.5 (`claude-opus-5-5`), running as the `arbor-auditor` context for this task. Independent engineering evidence only. **Astra review: NOT_PERFORMED.** This is not human approval. The result is not called a success.

## Environment and commands

- Run from the implementation worktree root `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` (HEAD `a0351534`, branch `claude/m0-impl`). Spec worktree HEAD `2c944302`. Environment: `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout <s> uv run --locked python <script> ...`, Python 3.12.14, uv 0.12.15, macOS 27.2.1 arm64. Standard library only.
- `D=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_recompute_20261126/deliver`
  1. `integrity_check.py` → `integrity_check.out.txt`
  2. `my_pool.py $D/attempt1` → `attempt1/{rows.jsonl, per_lineage.json, notes.json, s5_alt_recovery.json}`, `attempt1.stdout.txt`
  3. `compare.py`, then `compare_v2.py`, then `compare_v3.py` `$D/attempt1 .../pooled/pooled_table.json $D/attempt1/compare*.json` (see "Failed checker attempts")
  4. `detail.py $D/attempt1 .../pooled/per_lineage.json` → `attempt1/detail.txt`
  5. `efff_components.py $D/efff_components.json` → `efff_components.stdout.txt`
  6. `unread_check.py $D/attempt1 $D/attempt1/unread_check.json` → `attempt1/unread_check.stdout.txt`
  7. `r1_exact_rows.py $D/attempt1/r1_exact_rows.json` → `attempt1/r1_exact_rows.stdout.txt`
- Every command ran in under 10 minutes and exited 0. No process was left running.
- What I used: the approved text (2c944302, section 4A stage 1S points 2, 6, 7, 8, 11; section 7; section 13 items 12 and 18), `LEAD_RULINGS_8.md`, `run_plan.json` (id maps, `must_contain`, the `per_survivor` primary/fallback map of the a3 wrappers, items per level), the class table, the amendment list (empty), `OUTPUT_FORMATS.md`, and the field table (for structure only). For the item-3 facts I also read committed code: `r1_fix4_measure.py` (run copy), `r1_fix4_a3_heur.py`, `r1_fix3_battery.py`, `audit4_r1/final_table4.py`, `s5_analyse_v2.py`, `final_r2/f_pool.py`, `f_new_heur.py` and the R1 generators at `7cd0ac5a`. **I did not open, import or copy `pool_fresh.py`, and I did not need it to explain any difference.**
- **Disclosure.** A `git grep` for `constant_mfk_fitted` at `b78e58b1` also printed matching lines from past-run output files (`audit3_r1/heur_run*_summary.txt`, `audit4_r1/heur_run1_all.jsonl`, `audit4_r1/final_table_run1.txt`). This was unintended. Those figures are not used anywhere here.

## 1. Integrity (`integrity_check.out.txt`)

- 975 output files, listed in the three hash records (11 units × 3 seeds, one attempt each, every command exit 0), recomputed: **0 mismatches** in SHA-256 or size. No file on disk is missing from a hash record. `hashes_seed{1,2,3}.json` in the run directory are byte-identical to the committed ones, and each carries `plan_sha256` = SHA-256 of `run_plan.json` (`316f1026…f389`).
- Pooled files: all 5 match `SHA256SUMS_pooled.txt`. The committed copies (`dropped.json`, `per_lineage.json`, `report_extras.json`, `SUMMARY.md`, and `pooled_table.json.gz` decompressed) are identical to the run-directory files.
- `run/commit_at_start.txt` = `570e130c9a04…` = the only commit that touches `HASH_RECORD.json`.
- All 34 hashes in `HASH_RECORD.json` match the files, both in the worktree and at `570e130c`. The class table was checked at `2c944302` in the spec worktree, and the approved text through `git show 2c944302:…`. `git diff 570e130c HEAD -- studies/m0/fresh_run studies/m0/manifests` is empty.

## 2. My pooling, from the text

Rules I implemented: id maps from the plan. R1 `eff` and `anti` are pooled as the item-weighted mean of the written 4-decimal figures, u = 0.00005. R1c is read from stdout with the plan's 3,000 per seed, u = 0.00055, and all its rows count. R2 sums k, napp and n over shapes and seeds within the level: yes/no gives k/napp − 1/2; open gives k/n, and also k/napp for `[cond]` names. The shape-dependent rule is read per counted shape. The class rules are `klass()` order from the table, and `[NEW]` names are classed only by the `new_rules` entries. M1 is pooled Σ N·rate / Σ N, against chance and against the same section's pooled `base` (u, 2u). `base` itself counts as a rule. Prefixes are `im:`/`a3:`/as written, plus the R-56 stripped reading. C1 scalars are pooled with u = 0.0005. s5 single rules use hits = round(rate_in_shape × n_shape) summed. a3 and battery `S` rows use `hit` summed over the level n. Closed forms use u = 0.00005. `EFF_SM`, `M.*`/`H.*` entries, `C.*` and `A3_MUT` are uncounted. R-46 fields are not read, and R-57 in-shape rates are not counted. The decision is |excess| + u > 3/20, on exact fractions.

**Result: the same 15 lineages are dropped, with the same number of rows over the bound for each, and every one of the 82 lineages has the same status.** The row-by-row comparison (`attempt1/compare_v3.*`) matched 33,521 of 33,521 rows: 0 differences in value, 0 in counted status, 0 in over-bound status. The script's 24 extra rows are rows with no figure (R2b, napp = 0, excess `None`), which I do not write.

### 2a. The 15 dropped lineages: the rows that decide them (exact fractions; u = rounding uncertainty)

- **R1.equivalence_exchange_rates_r6.** `a4:direction_ignored_q_over_p` (R1a and R1b, `aud`): eff = **1/1** at all 7 levels, n = 9,000, u = 1/20000. It fired on every item and was right on every one in all three seeds, so it is exact at all 7 levels. It is not an entry (`M` holds `direction_ignored_p_over_q`, not `…q_over_p`), so by point 8's exact-row bullet it counts. 14 rows over.
- **R1.spatial_grid_walk_r5.** `constant_mfk_fitted`, levels 0 and 1 only, below −0.15: R1a aud −2459/15000, −197/1200; R1a impl −4909/30000, **−4939/30000** (L1, the largest); R1b aud −4927/30000, −49/300; R1b impl −1639/10000, −821/5000. 8 rows. See 3(i).
- **R1.swap_tracking_r5.** `constant_mfk_fitted`, L0 and L1: R1a aud **−1611/10000** (L0, the largest), −1201/7500; R1a impl −481/3000, −4747/30000; R1b aud −4757/30000, −1611/10000; R1b impl −4783/30000, −4769/30000. 8 rows. The smallest |excess| + u is 4747/30000 + 1/20000 = 0.15828 > 0.15.
- **R1.venn_counting_r5.** Four rules with eff = **1/1**, each exact at particular levels, in aud (prefix `a3:`) and impl (bare name) of R1a and R1b: `ignore_triples` L0, `sizes_minus_2pairs` L1, `pairs_minus_3triples` L3 and L6, `pairs_minus_2triples` L4. None is an entry, and none is exact at all seven levels. 20 rows.
- **R2.list_ops.** `[NEW] (artifact) final list = start list with adds appended and removals applied, all moves and reverses ignored` (R2b, `f_rules_new.json`, k/n): L0 **1599/4000** = 0.39975, L1 1621/6000 = 0.27017, L2 757/4000 = 0.18925 (n = 12,000, exact counts). 3 rows. See 3(iii).
- **M1.division_counting_r3.** Only `a3:k_minus_remainder_ignores_exact_fit`, at all 7 levels in M1a (a3 section), M1b and M1c, on both readings. The largest is M1a vs chance L3 **99/200** = 0.495. 42 rows. This is one of the four amendment-scope M1 rules. Its partner `im:…` is a PROC entry, and the amendment list is empty, so it counts.
- **M1.grid_perimeter_r3.** L0 only, vs chance. `im:bbox_plus_4` in M1a's a4 section **619/3750** = 0.165067 and in its own section 63/400; M1b 1847/12000 (the smallest, 0.153917); M1c 49/300. `a3:bbox_plus_4` in M1a 81/500, M1b 1847/12000 and M1c 49/300. `new:mode_by_template` in M1b 79/500. 8 rows. None is an entry.
- **M1.last_digit_power_r3.** `a3:fermat_misapplied_e_mod_p_plus_1` at L0 and L1 (M1a **5957/30000** = 0.198567; M1b 24/125, 327/2000; M1c 1169/6000, 2003/12000) is an amendment-scope rule. **It is also dropped independently** by `im:exp_mod_p` and `a3:exp_mod_p` at L0 (0.1670 to 0.1753; no entry). 13 rows.
- **M1.prime_factors_r3.** Only `a3:largest_le_sqrt` (amendment scope): against chance at L0 to L6, and against base at L1 to L6, in M1a, M1b and M1c. The largest is M1c vs chance L5 **1493/6000** = 0.248833. 39 rows.
- **M1.ratio_share_r3.** `new:ratio_first_named` and `new:ratio_last_named` (M1b and M1c) at all levels, on both readings. The largest is M1c `new:ratio_first_named` vs chance L1 **6431/12000** = 0.535917. 56 rows. (`im:largest_share`, `im:smallest_share` and `a3:largest_share` are entries and stay uncounted.)
- **C1.circle_elimination_r2.** Only `EFF_F` (C1a and C1c) at all 7 levels: C1c L0 **169/600** = 0.281667, falling to 49/300 = 0.163333 at C1a L6. 14 rows.
- **C1.cond_chain_f3.** Only `EFF_F`: L0 C1a 9/40, C1c **89/375** = 0.237333. At L1, C1a 451/3000 and C1c exactly 3/20, which is over only through u = 0.0005; on the exact hits of the s4 records it is 903/6000 = 0.1505. 4 rows.
- **C1.func_branch_f4.** `EFF_F` at L2 to L6 (C1a L2 **339/500** = 0.678), and **also** `S.always_high_branch` in `f5.json` and `f5b.json` at L0 to L6 (649/1500 to 2839/6000; a counted cheap rule). It does not rest on `EFF_F` alone. 24 rows.
- **C1.shared_lists_f3.** Only `EFF_F` at L6: C1a **153/1000** = 0.153, C1c 113/750 = 0.150667, each + u = 0.0005. 2 rows. See 3(ii).
- **C1.union_find_links_f3.** Only `EFF_F` at L0 and L1: C1c L0 **47/150** = 0.313333; C1a L0 31/100; L1 9/50 and 11/60. 4 rows.

### 2b. Near-bound survivors (largest counted |excess| + u ≥ 0.10): confirmed, none over

All counted rows were read, and none of these lineages has a counted row over the bound (`attempt1/detail.txt`). Uncounted or unread rows over the bound are listed with what left them out (`attempt1/unread_check.stdout.txt`).

| Lineage | Largest counted row (|excess| + u) | Uncounted or unread over 0.15 |
|---|---|---|
| C1.string_build_f3 | C1a s5 `EFF_F` L0 29/200 + 0.0005 = **0.1455** (exact hits 870/6000 = 0.1450; C1c 867/6000) | none. `EFF_F` is carried by `M.no_tail` (an uncounted entry on its own) |
| R1.knights_knaves_r6 | R1c `lookup (own form, forms mentioning asked)` eff L0 403/3000 + 0.00055 = **0.134883** | none |
| R1.boolean_lights_r4 | R1c lookup (asked on at start, …) eff L1 1/8 + 0.00055 = 0.12555 | none |
| R2.crt_smallest | R2a `[mine] largest remainder` L0 479/4000 = 0.11975 | `[NEW] (partial) largest modulus…` L0 0.3628, L1 0.1959: a `new_rules` entry, label `(partial)` defined in the header. Correctly uncounted |
| C1.run_length_scan | C1c s5 `EFF_F` L1 7/60 + 0.0005 = 0.117167 | none (`EFF_F` carried by `M.no_final_close`) |
| C1.slices_f4 | C1c s5 `EFF_F` L0 341/3000 + 0.0005 = 0.114167 | none |
| C1.postfix_evaluation | C1c s5 `EFF_S` = `EFF_F` L0 67/600 + 0.0005 = 0.112167 (a tie; the script names `EFF_F`) | `oracle_any_literal` 0.16 to 0.18 at L0: not a rule under R-46 |
| M1.linear_equation_r3 | M1c `new:one_op_two_numbers` vs chance L4 223/2000 + 0.000005 = 0.111505 | none |
| R2.luhn_check | R2b `most frequent answer (train draw)` L0 k/n on the number shapes 663/6101 = 0.108671 | `[mine] (P) misread: doubling counted from the left` is exact (1.0 on number shapes, +0.5 on yes/no) at all levels: klass `(P`, uncounted as written |
| C1.fast_power_f4 | C1c `f5` `S.pow_terms_plus_c` L1 623/6000 + 0.00005 = 0.103883 | none |
| C1.merge_two_sorted_f3 | C1a s5 `EFF_S` = `EFF_F` L0 77/750 + 0.0005 = 0.103167 | `C.algorithm_rerun` 1.0 (control entry); `oracle_any_literal` ≈ 0.18 to 0.20 (R-46) |

No rule that the class table, the amendment list and R-46/R-57 do not exclude was left unread or uncounted for any lineage. Every row over the bound that is uncounted matches a class-table entry.

### 2c. Full table: all 82 lineages

Every lineage has the same status as the script gives it. The largest counted |excess| + u per lineage is in `attempt1/detail.txt`, sorted. Where it names a different rule from `per_lineage.json`, the cause is a tie or near-tie (< 0.0004): `per_lineage.json` picks the row with the largest |excess| **without** u, while I sort by |excess| + u. This affects postfix_evaluation, merge_two_sorted, func_compose, binary_search_f3, euclid_gcd_traced (ties), nested_pairs_f3 (MF_cv 37/600 + 0.0005 against S.run_inc_1 371/6000), pipes_work (R-56 name), arithmetic_series and consecutive. It is presentation only.

## 3. The three facts

**(i) `constant_mfk_fitted` in R1.spatial_grid_walk_r5 and R1.swap_tracking_r5.**
- **What it is.** In `r1_fix4_measure.py` (R1a, aud) the rule is `mfk = Counter(b.answer for b in fit_items).most_common(1)[0][0]`: the most frequent answer string among 400 items drawn at the same level from a separate fit seed (`aud_fit`). It is then predicted for every scored item. The implementer's battery (`impl`) and R1b do the same with their own fit draw. `final_table4.py` puts it in `GENERIC`, its class C ("a fitted constant"), so it is counted, and it is not an entry.
- **What `eff` means.** eff = mean over items of (credit if the rule answered, else chance) − mean chance. Credit is 1 if the prediction equals the answer and 0 otherwise (`r1_fix4_a3_heur.credit`). Chance is 1/k (`chance()`). The constant always answers (fired = n), so eff = accuracy − mean(1/k).
- **The chance rate at L0 and L1.** swap_tracking: 0.2 exactly (k = 5 = 5 + level//2 people and objects). spatial_grid_walk: 0.163 to 0.165 per seed and level, which is mean(1/k), with k mostly 6.
- **Why it scores below chance.** It is a property of how the items are built, not of how the fit and test draws relate. Each swap item samples its 5 objects from a pool of 24 (`studies/m0/vocab.py` `OBJECTS` at 7cd0ac5a, length 24). Each grid item draws its cell names from the `PSEUDO` syllable product. So a fixed answer string is one of an item's options only rarely. The measured constant accuracy is 0.034 to 0.052 for swap (about 1/24) and 0 to 0.0007 for spatial. The in-sample mode rate that R1b writes (`mode_rate`: the commonest answer among the scored items themselves, the best any constant could do on those items) is 0.046 to 0.051 for swap and 0.0013 to 0.0017 for spatial. That is also 0.152 to 0.163 below chance. The fitted constant comes within about 0.01 of this in-sample ceiling, so fit/test mismatch explains almost none of the deficit. The rule's `anti` is about 0 (−0.001 to +0.002), so choosing among the options the constant did not pick gains nothing either.
- **Does the two-sided bound apply as written?** Yes. Section 13 item 12 (a) says "a cheap rule more than 0.15 below the base rate drops a lineage as well", and point 7 says the same. The rule is cheap (class C) and counted, and its pooled excess is below −0.15 at L0 and L1 in every unit and file. At L2 and above the chance rate is ≤ 1/6 (swap L2 −0.13; spatial L2 1/8), so no other level can cross. The committed docstring of `r1_fix3_battery.summarise` already calls this a floor: "for a closed answer a rule that always names one option has low = −1/k, a floor and not a gain". **PENDING LEAD REVIEW:** under the text, any lineage whose options are drawn per item from a large pool, at a level with k ≤ 6, is dropped by this floor whatever its tells. Here the excess cannot be exploited (anti ≈ 0).

**(ii) The C1 drops that rest only on `EFF_F`: what carries the composite** (descriptive; `efff_components.py`). I re-implemented the documented choice of `s5_analyse_v2.py` from the raw s4 records: 2-fold by item parity, and per shape the best of the shape's most frequent key and the allowed rule prefixes, chosen on one fold and scored on the other. **It reproduces all 1,260 written `EFF_S`/`EFF_SM`/`EFF_F` figures exactly** (10 lineages × 2 units × 3 seeds × 7 levels × 3 measures, 0 mismatches). Test hits by the class of the chosen component, pooled over the three seeds, at the deciding levels:
- circle_elimination_r2, all levels, both units: 100 % `M.ignore_dead_initial`. Example: C1c L0 1689/6000, all `M`. `EFF_S` (S/G/MF only) there is 485/6000.
- cond_chain_f3, L0 and L1: `M.rounds_x_final` (C1a L0 1312 of 1348 hits; the rest `S.rounds_x_gcd` 27 and MF 9. C1c L0 1384 of 1424; S 28, MF 8, `G.lit0` 4).
- shared_lists_f3, L6: 100 % `M.copy_on_alias` (C1a 919/6000, C1c 903/6000).
- union_find_links_f3, L0 and L1: 100 % `M.no_find`.
- (func_branch_f4, L2 to L6: 100 % `M.drop_even_branch`. That drop does not rest on `EFF_F` alone; see 2a.)
- In every case `EFF_F` = `EFF_SM` (no `F.*` component was chosen), and the carrying rule is an `M.*` partial-trace entry that is uncounted on its own. This is the stricter outcome that point 6 names.
- **shared_lists_f3 exact figures.** C1a L6: per-seed written 0.164, 0.149, 0.146 → pooled **153/1000** = 0.153, + u 0.0005 = 0.1535. Exact hits 328 + 299 + 292 = **919/6000** = 0.153167. Binomial SE √(p(1−p)/6000) = **0.00465**, which puts it 0.69 SE above 0.15. C1c L6: per-seed 0.140, 0.155, 0.157 → pooled **113/750** = 0.150667, + u = 0.151167. Exact hits 280 + 310 + 313 = **903/6000** = 0.1505, SE **0.00462**, 0.11 SE above 0.15. Both are over the bound on the written figures and on the exact counts. The binomial SE treats a cross-validated best-of-choice score as a simple proportion, so it is approximate.
- **Observation (PENDING LEAD REVIEW; changes nothing by itself).** Point 6 and the amendment's C1 bullet say the components "cannot be read apart from committed outputs", because `s5_analyse_v2.py` writes no `G.*` rule. The units' own hashed s4 record files (`rules/<draw>.jsonl.gz`, marked "helper, not read" in the field table) do carry every `S.*`/`G.*`/`M.*`/`F.*` answer per item. The decomposition above was computed from them without running any rule script. The text adds no rule for forming the composite from its parts, so `EFF_F` still counts whole.

**(iii) R2.list_ops and the `(artifact)` label.** `final_r2/f_new_heur.py` at b78e58b1, lines 202 to 212:
```
@rule("list_ops", "(artifact) final list = start list with adds appended and removals applied, all moves and reverses ignored")
def _(s, q):
    xs = [int(x) for x in re.search(r"Start with the list (.*?)\. Do these steps", q).group(1).split(", ")]
    for op in re.search(r"Do these steps in order: (.*?)\. What is the final list", q).group(1).split("; "):
        if op == "remove the first element":
            xs = xs[1:]
        elif op == "remove the last element":
            xs = xs[:-1]
        elif op.startswith("add "):
            xs.append(int(op.split()[1]))
    return ", ".join(map(str, xs))
```
The header defines only "(cue), (partial) = truncated procedure, (P) = full solve under a misreading". In one line: it carries out the stated list operations except "reverse the list" and "move the first element to the end", which it skips. At L0, 4,289 of the 12,000 items have no move or reverse. This follows from napp = 7,711 for the companion rule `[NEW] [cond] (cue) moves and reverses ignored (items with at least one move or reverse)`, whose hits there are 508. 4,289 + 508 = 4,797 = the artifact rule's hits. So most of its 0.39975 comes from items on which it does exactly the stated procedure. The `[a3] ignore reverses` (0.68) and `[a3] ignore moves to the end` (0.64) rules of the same idea are `klass()` artifacts and uncounted. **PENDING LEAD REVIEW**, as the class table already notes ("counted for a label the header does not define").

## 4. Differences between the pooling script and the text, and between it and me

1. **Rounding uncertainty on recovered counts (script stricter than me; no decision changes).** On 1,024 rows (s5 single rules in C1a and C1c, 421 each, recovered as round(rate_in_shape × n_shape); and C1b `MF_shape_cv` recovered per shape, 182) the script adds u = 0.0005, and I used 0, treating recovered hits as counts. The text says counts are compared exactly but also that rounded figures carry an uncertainty. Both readings give the same over-bound status on every row. The other recovery (`share_of_level × n`, as `f4b_pool_v2.py` does) changes 475 of 842 s5 rule figures by at most 0.0015 and changes no decision. The script reports the same (0).
2. **R2 levels with more than one answer type (a shared reading, stricter than R-34; no decision changes).** binary_search_trace (list + number, 7 levels × 3 files) and dictionary_rank (number + text) have two open answer types in one level. Both poolings read each answer type separately, with n = the items of that type. R-34's literal unit is the whole level. For base-0 answers the per-type reading is never smaller than the level-wide one, because the level-wide k/n is a weighted average of the per-type figures or smaller. The largest values here are 0.088 and 0.044, so nothing changes. luhn_check (number + yes/no) has to be split because the bases differ.
3. **Exact R1 rows in the report (reporting gap, not a decision).** Point 8 asks that "every exact row of the fresh run, in any R1 unit" be listed. `report_extras.json` `r1_exact_rows` lists the 2 rules that are exact at all seven levels. There are 38 (unit, file, lineage, level, rule) rows exact in all three seeds (`attempt1/r1_exact_rows.json`): the 14 rows above, plus 24 venn_counting rows. 20 of those are counted and drop the lineage (2a). 4 are `total_minus_union_wrong_sign` at L0 (`M` entry, uncounted). The 24 venn rows are not in that list.
4. **`per_lineage.json` "largest counted excess"** is chosen by |excess| without u (2c). This is presentation only.
5. **Rows with no figure.** The script writes 24 R2b k/napp rows with napp = 0 and excess `None` (its `counted_rows_with_no_items`). I write none. Neither decides anything.
6. No row was found where the script departs from the text in the direction that favours passing. No lineage's status differs under my pooling.

Also checked: the M1a names given by two sections (`im:*` in `own` and `a4`). Both poolings keep them separate. A merged reading is a convex combination of the two, so it could not drop anything more. R-56 (the stripped `[...]` reading) changes no outcome, and no row over the bound involves a bracketed name. The a3 wrapper fell back to its own run for `C1.while_counter_f3` in C1a and C1c in all three seeds (6 cases, as reported). No survivor is missing from any unit, level or seed. No row of a non-survivor id was read.

## 5. Failed checker attempts (kept)

- `compare.py` (first attempt): 3,125/3,149 rows unmatched. This was my own key mismatch, not a data difference: I wrote `src` as `f_rules.json` where the script writes `f_rules`, and named M1 `base` rows differently.
- `compare_v2.py`: fixed both, and set aside the script's 24 rows with no figure. It left 224 duplicate keys, again my own mistake: the answer type was missing from the key for R2 levels with two answer types.
- `compare_v3.py`: answer type added. Exact agreement as reported above.

## 6. Not covered

- I did not rerun any unit, generate any item or open any dry-run or past-run output, apart from the unintended grep display disclosed above.
- The rule scripts' correctness is not audited here. Figures are taken as each script wrote them (point 6).
- The class table is not re-derived. Its entries were applied as given.
- I did not read `pool_fresh.py`.
- `SUMMARY.md`'s wording was checked only for its counts and its deciding rows.

## Files
`/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_recompute_20261126/deliver/`: this file; the scripts `integrity_check.py`, `my_pool.py`, `compare.py`, `compare_v2.py`, `compare_v3.py`, `detail.py`, `efff_components.py`, `unread_check.py`, `r1_exact_rows.py`; and the outputs `integrity_check.out.txt`, `attempt1.stdout.txt`, `attempt1/*`, `efff_components.json`, `efff_components.stdout.txt`; plus `SHA256SUMS.txt`. Copies of the committed files I read (ADR text at 2c944302, `f_pool.py`, `s5_analyse_v2.py`, `f_new_heur.py` at b78e58b1) and a dump of the class table are in `../work/`.

Astra review: NOT_PERFORMED
