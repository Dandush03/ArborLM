# M0-R2 final re-measurement after fix round 4 (second solver, rules, levels, capacity, reproducibility)

- Auditor: arbor-auditor, Claude Opus 5.5 (model id claude-opus-5-5, from session metadata). Independent engineering and mathematical evidence. It is not Astra validation and not human approval. Nothing here registers a lineage.
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, read only. When I started, fix 4 was uncommitted (HEAD `9bcec484`). During my audit the lead committed it as `7cd0ac5a2a2c5261352e66b4a41650576dcfe1be` (22:33 local). Every R2 generator file I ran was last modified at or before 22:16. My runs were from 22:17 to 22:34. After the commit the working tree is clean apart from two `.bak` files that are not mine. I wrote nothing in any worktree.
- I wrote none of the audited code. My solver, harness, rules and summaries are in this folder. I imported nothing from the implementer's fix-4 scripts or from any `*_analysis` module. The audit-3 and audit-4 rule files and `r2_fix3_heuristics.OWN` were run as written, because the brief asks for that.
- Rulings applied: R-30 (G per part), R-31 (counted classes), R-32 (pooled estimate) and R-34 (unit) from `LEAD_RULINGS_6.md`, and R-24 to R-28 from `LEAD_RULINGS_5.md`.

## Environment and commands

Apple arm64, uv 0.12.15, `uv run --locked --offline python` = Python 3.12.14. The working directory was the audited worktree. Every generator run used `PYTHONPATH=.` (plus `:<deliver>` where my modules were imported) and `PYTHONDONTWRITEBYTECODE=1`, with `PYTHONHASHSEED=0` unless stated otherwise. The summaries ran under `python3 -I` from `deliver/`. `<deliver>` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_final_r2_20261125/deliver`. All seeds are throwaway string seeds that I chose before the runs. None of them is a registered seed.

| Script | Command (after the env above) | Output |
|---|---|---|
| f_render.py | `python f_render.py 2 0,6` | f_render.out (attempt 1 FAILED, PYTHONPATH missing: f_render_attempt1_failed.out) |
| f_shapes.py, f_phrases.py | `python f_shapes.py`; `python f_phrases.py` | f_shapes.out, f_phrases.out (phrase inventory for the parser) |
| f_solver.py (text-only second solver), f_keys.py | `python f_keys.py 100 smoke ../keys_smoke100.json` (smoke run); `python f_keys.py 1000 k1 f_keys_1000_k1.json` | f_keys_1000_k1.out/.json |
| f_rules.py | `python f_rules.py 4000 f_rules_4000.json` (seeds `finalr2\|<lid>\|<level>\|5` train, `\|6` test) | f_rules_4000.json/.log (smoke at N=100: ../rules_smoke100.json) |
| f_harness_check.py | `python f_harness_check.py <impl scratch>` (my harness run with the implementer's `a4r2` seeds) | f_harness_check.out |
| f_pool.py | `python3 -I f_pool.py f_rules_4000.json /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fix4_r2_20261125 f_pool.json` | f_pool.out/.json |
| f_interval_diag.py | `python f_interval_diag.py` (diagnostic only, not pooled) | f_interval_diag.out |
| f_new_heur.py, f_rules_new.py, f_new_summ.py | `python f_rules_new.py 4000 f_rules_new_4000.json`; `python3 -I f_new_summ.py f_rules_new_4000.json f_new_summ.json` | f_rules_new_4000.out/.json (v1 kept: *_v1.*), f_new_summ.out/.json |
| f_levels.py, f_frombase_digits.py | `python f_levels.py 1000 f_levels_1000.json`; `python f_frombase_digits.py` | f_levels_1000.out/.json, f_frombase_digits.out |
| f_capacity.py | `python f_capacity.py 9 f_capacity_g9.json`; `python f_capacity.py 8 f_capacity_g8.json` | f_capacity_g9.*, f_capacity_g8.* |
| f_repro.py | three fresh processes, `PYTHONHASHSEED` = 0, 4242 and `random` | f_repro_h0.out, f_repro_h4242.out, f_repro_hrandom.out |
| f_final_json.py | `python3 -I f_final_json.py` | final_r2.json, f_final_json.out |

Inputs from the implementer, with sha256 values equal to those recorded in the manifest: `bat_a4_2000.json` 6f804261…, `bat_a4_2000_crt.json` 3ba2dc16…, `bat_f4_2000.json` 33eae5c1…, `bat_f4_2000_crt.json` 982a263d… (all in `experiments/_scratch/m0_fix4_r2_20261125/`). The `_crt` files replace the crt entries of the main files, as the manifest does.

## 1. Second solver (text only) and answer keys

`f_solver.py` reads only `item.question`. It uses the standard library and nothing from `studies.m0`. I wrote it from rendered texts and my phrase inventory. Its methods include literal earliest-finish rounds, Kruskal with union-find, stepping CRT candidates up to the lcm, a falling-factorial rank that is checked against brute-force enumeration whenever the list has ≤ 20,000 words, two recursive-descent evaluators, a manual left-to-right rewrite scan, and a literal heap simulation. **0 mismatches and 0 errors in 133,000 items** (1,000 per lineage and level, seeds `final-r2-key|<lid>|<level>|k1`, 19 lineages × 7 levels). It also matched on the first smoke run (13,300 items), so no fix to my solver was needed. Because the solver parses everything from the text, it also confirms that every quantity the key uses is stated in the question.

## 2. Wording: items with no unique answer under the stated convention

The solver raises a flag for each ill-posed case I could name: no CRT solution or remainder ≥ divisor, a disconnected town graph, a dictionary rank or word outside the list, an invalid digit for the base, removal from an empty list, more than one valid check digit, an empty or reversed meeting, a tie between equal children during a heap sift-down, and an empty rewrite result. **None of them fired on the 133,000 items: the share is 0 for all 19 lineages.**
- **count_divisible (reworded this round):** the new clause ("Every entry of the list counts each time it appears…") is present on 7,000 of 7,000 items. Under the set-of-values reading the key would change on **2,203 of 7,000 items (31.5 %)**. The clause settles those items, so I count 0 ambiguous. A NEW (P) rule that sums each distinct value once reads 0.62 to 0.72. That figure is the stake the clause carries, not a defect.
- grid_sum: 1,019 of 7,000 items (14.6 %) ask for "the diagonal from the top left corner" of a non-square grid. The stated "(cells (1,1), (2,2), and so on)" defines it uniquely, so I count 0. The lead may want to confirm this reading (PENDING LEAD REVIEW).
- luhn_check: every number has odd length, so "doubling counted from the left" gives the same key on 100 % of items (also in audit 4). The stated convention is unique but is never tested.

## 3. Cheap rules: pooled per R-32, counted classes per R-31

- Rules: audit 4's `a4_heur.py` and audit 3's `a3_heur.py`, imported from their review folders (the originals; I diffed the package copies and they match apart from the header, one import line and three `sorted(set())` edits), plus `r2_fix3_heuristics.OWN`. That is the same union as the implementer's fix-4 battery.
- Measurement: I wrote my own harness from audit 4's definition. Per shape, open answers score k/n (a rule that does not apply counts as wrong), `[cond]` rules score k/napp, and yes/no rules score |k/napp − 0.5|. The most-frequent-answer rule is learned on a separate training draw. The implementer's `r2_fix4_battery.py` cannot take other seeds (the tag is fixed to `a4`/`f4`), so I did not run that file. Instead I checked my harness against it: with the implementer's `a4r2` seeds it reproduces their counts in **1,251 of 1,251 (level, shape, rule) cells** (f_harness_check.out).
- Fresh seeds: **4,000 test items + 4,000 training items per lineage and level**. Pooled with the implementer's a4 and f4 sets (2,000 each), item-weighted: **8,000 test items per lineage and level**.
- R-31: the lead's table in `LEAD_RULINGS_4.md` (R2: 15/20/24 clusters at 0.10/0.15/0.25) is audit 4's "cues only" row. So **only class `cue` is counted**, using audit 4's `klass()` as re-typed in f_pool.py. Partial, construct, P and artifact are reported but not counted. The implementer counted cue + partial + construct. No survivor's verdict depends on that difference.
- R-34: I report two units. "Per shape" takes the maximum over the question shapes, as audit 4's harness did. "All shapes" sums the counts over the shapes of one answer type. For every lineage the all-shapes value is ≤ the per-shape value, and the verdicts are the same under both.

## 4. Levels

My test (f_levels.py, 1,000 items per level, parameters parsed from the text):
- Distinct items: I counted exact normalised texts shared between levels.
- Rise: the mean of a stated parameter must increase at every adjacent step, and the AUC P(L+1 > L) + ½P(=) must be ≥ 0.6. This is my reading, not a registered threshold.

All 19 lineages have a strictly rising mean at every step. Exceptions to the AUC part, and overlaps:
- **dictionary_rank L1→L2:** list size barely rises (log10 3.789 → 3.815, AUC 0.52). Word length rises 4 → 5 at that step while the alphabet shrinks (10.5 → 8.0 letters). The items are distinct, with 0 shared texts, so the levels have not collapsed. The rise in difficulty at that step is thin: PENDING LEAD REVIEW.
- **from_base:** digit count is uniform on {L+3, L+4, L+5}, so the mean rises by exactly 1 per level and the AUC on digit count is 0.78. On value, the AUC is 0.57 to 0.60 at L4–L6. **317 texts are shared between levels in 7 × 1,000 draws** (99 between L0 and L1, mostly small base-2 numbers). At L0 only 653 of 1,000 draws are distinct texts. The implementer reported 64 in 300 per level. Whether "every level produces distinct items" forbids an item from appearing at two levels is PENDING LEAD REVIEW. Under my reading (the distributions differ and the parameter rises) the lineage passes.
- crt_smallest: 13 shared texts (L0/L1). to_base_wide: 19 shared texts. All others: 0.

## 5. Capacity against `core.generate_pool` as written (R-28, R-30)

Survivors per the manifest: 18 clusters, so G = floor(18/2) = **9** and the demand is **27,680** per cluster and level. One G lower is **G = 8, demand 31,000**. Method: in a worker process per lineage, `core.part_lineages` is replaced so that the pool holds only that lineage. Then `core.generate_pool("R2","A","capacity-final-r2",20261125, 7·D, uniform mix over levels 0–6, taken=set(), shortfalls=[])` runs, with core's own allocation, its 40·count+1000 attempt limit and its text de-duplication. Text-distinct means distinct after core's normalisation.
- **G = 9:** 18 lineages supply 27,680 at every level. **to_base_wide L0 supplies 15,928**, the whole L0 space, which matches the implementer's figure. Every other level-cell passes.
- **G = 8:** the same pattern: 18 lineages pass at 31,000, and to_base_wide L0 supplies 15,928.
- No text was shared between any two lineages' pools (I intersected the hash sets).
- The single call per lineage is a model. The real pools use several roles that share `taken`, with an attempt limit per call, plus the registered level mix and partition. That structure was not run. The implementer's margin run reports the thin L0 spaces: cellular_automaton about 32,768 and from_base about 36,471. Both pass at G = 8 but would not pass far below it.

## 6. Reproducibility

The same seeds give byte-identical items (300 per lineage and level through `build_item`) and identical `generate_pool` hashes (1,400 items per lineage) in three fresh processes with `PYTHONHASHSEED` = 0, 4242 and random. `hash('x')` differed between the three processes, which confirms the seeds really differed. Combined hash: `af0581d3cc1f011371167031722b26dc1e2dc0a07fc3a9c030801e2529806747`.

## 7. Are dropped lineages excluded where the fix-4 set is built?

- `r2_fix4_set.fix4_set()` returns all **40** lineages by design, including the 21 marked NOT_REGISTERED and to_base_wide. The exclusion exists only as `status` in `manifests/r2_fix4_survivors.json`. No accessor returns only the survivors.
- The manifest is internally consistent: 18 SURVIVES equals `surviving_lineages`; 18 distinct strict clusters equals `surviving_clusters`; `G_per_part` = 9 and the demand is 27,680. The capacity input `cap_g9_perpart.json` covers exactly the 19 survivors that were candidates before capacity.
- `core.REGISTRY["R2"]` was not changed by this round. It still holds the 16 pre-repair core lineages, including dropped ones (count_letter, kth_smallest, multiples_between, palindrome_check, permutation_power, stack_machine, string_rewrite, to_base). So `core.generate_pool("R2", …)` as written would build today from that old registry, not from the fix-4 survivors. That is expected while nothing is registered. Registration will need a filtered set.
- `studies/m0/fixtures/r2_fix3/` keeps the fixtures of the dropped fix-3 shapes, on file as policy requires. There is no fix-4 fixture directory.

## 8. Per-lineage table

Keys = mismatches / items (seeds k1). "No unique" = items with no unique answer under the stated convention. "Cue" = the largest pooled counted excess, per shape, with its level and rule. "P / artifact / partial" = the largest pooled values of the classes that are not counted. Capacity = core.generate_pool as written at G = 9 / G = 8.

| Lineage (cluster) | Keys | No unique | Cue (pooled, 8,000/level) | Not counted: partial · P · artifact | NEW rules > 0.15 (fresh seeds only) | Levels | Capacity G9 / G8 | Verdict |
|---|---|---|---|---|---|---|---|---|
| binary_search_trace | 0/7,000 | 0 | 0.078 (L1, [mine] midpoint rounded up, sum) | – · 1.00 (0-based = same search) · – | – | list length 17.5→41.5, AUC ≥ 0.97, 0 shared | pass / pass | STAYS |
| caesar_shift | 0/7,000 | 0 | 0.046 (L3, [a3] shift backwards) | – · 0.05 · – | – | letters 5→35, AUC 1.00 | pass / pass | STAYS |
| cellular_automaton | 0/7,000 | 0 | 0.043 (L2, [a3] one step only) | – · 0.20 (edge cells keep value) · – | – | cells×steps 22→115, AUC 1.00 | pass / pass | STAYS |
| cheapest_network | 0/7,000 | 0 | 0.058 (L0, [a3] n−1 cheapest cables) | – · 1.00 (Kruskal) · – | – | towns 8→14 | pass / pass | STAYS |
| count_divisible | 0/7,000 | 0 (set reading would change 31.5 %; clause on 100 %) | 0.031 (L0, most frequent answer) | – · – · – | (P) distinct values once 0.62–0.72 | list length 18→42 | pass / pass | STAYS |
| crt_smallest | 0/7,000 | 0 | **0.112** (L0, [mine] largest remainder; SE 0.004) | – · 0.02 · – | (partial) try r, r+m, r+2m: 0.37 L0, 0.19 L1 | log10 lcm 2.29→5.31, AUC ≥ 0.70; 13 shared | pass / pass | STAYS |
| dictionary_rank | 0/7,000 | 0 | 0.047 (L0, [impl] index in full alphabet) | – · – · – | – | list size rises; L1→L2 AUC 0.52 (word length 4→5) | pass / pass | STAYS (L1→L2 thin, PENDING LEAD REVIEW) |
| digit_root | 0/7,000 | 0 | **0.112** (L5, most frequent answer; about 1/9 chance) | – · 1.00 (n mod 9) · – | **(cue) digit sum once, first digit 0.195–0.211 at every level** | digits 5→11 | pass / pass | STAYS |
| expression_eval | 0/7,000 | 0 | 0.083 (L0, [a3] ranked item worked left to right) | – · – · – | – | operators 4.95→15.14, AUC ≥ 0.71 | pass / pass | STAYS |
| from_base (with to_base_wide) | 0/7,000 | 0 | 0.019 (L0, most frequent answer) | – · 0.155 (digits right to left) · – | – | digits +1/level (AUC 0.78); 317 shared between levels | pass / pass | STAYS (overlap PENDING LEAD REVIEW) |
| grid_sum | 0/7,000 | 0 (14.6 % non-square diagonals, defined) | 0.074 (L0, most frequent answer) | – · – · – | – | cells 9→36 | pass / pass | STAYS |
| interval_scheduling | 0/7,000 | 0 | **0.141** (L0, [impl] shortest first; SE 0.004; sets 0.129 / 0.133 / mine 0.151) | – · 0.63 (tie/touching misreadings) · – | **(cue) fewest clashes first 0.51 L0 … 0.23 L6** | meetings 25→55, AUC ≥ 0.91 | pass / pass | STAYS |
| list_ops | 0/7,000 | 0 | 0.010 (L6, [mine] [cond] append at front) | 0.144 ([cond] ignore reverses) · – · 0.68 (ignore reverses) | (artifact) ignore all reorderings 0.41 L0 | steps 2→8 | pass / pass | STAYS |
| luhn_check | 0/7,000 | 0 | 0.103 (L3, most frequent check digit; 1/10 chance) | 0.103 (plain digit sum) · 1.00 (doubling from left) · – | – | digits 6.5→18.5 | pass / pass | STAYS |
| min_heap_ops | 0/7,000 | 0 | 0.004 | – · 0.25 (Floyd heapify) · 1.00 (removal keeps order, removals=0) | – | inserts+removals 10.3→16.8, AUC ≥ 0.77 | pass / pass | STAYS |
| run_length | 0/7,000 | 0 | 0.000 | – · 1.00 (the procedure) · – | – | length 15→48, runs 6→12 | pass / pass | STAYS |
| sort_list (cluster of kth_smallest) | 0/7,000 | 0 | 0.000 | – · 0.00 · – | – | count 4→10 | pass / pass | STAYS |
| string_rewrite_nonidentity | 0/7,000 | 0 | 0.026 (L2, [mine] [cond] only the last rule) | – · 1.00 (simultaneous; L0 has one rule) · 1.00 (L0 one rule) | (P) repeat each step to fixpoint 0.21–0.74 | steps×length 6→72 | pass / pass | STAYS |
| to_base_wide (cluster from_base) | 0/7,000 | 0 | 0.043 (L0, [a3] digits reversed) | – · 0.04 · – | – | log10 n 2.86→6.44, AUC ≥ 0.86; 19 shared | **FAIL L0: 15,928 / 27,680; 15,928 / 31,000** | **NOT PASSING (capacity)**: DROPS under R-26, HELD under the R-28/R-36 reading; PENDING LEAD REVIEW |

No partial or construct rule exceeds 0.15 on any survivor. The largest pooled excess of any counted rule on any survivor is **0.141** (interval_scheduling L0, "shortest first"). Next come crt_smallest at 0.112, digit_root at 0.112 and luhn_check at 0.103. The last two are the most-frequent-answer floors of answers with 9 and 10 roughly uniform values. list_ops' 0.145 is a partial rule and is not counted under R-31; pooled it reads 0.144.

## 9. Final list

**Surviving lineages (18), each STAYS on keys, wording, counted rules, levels and capacity at G = 9 and G = 8:** binary_search_trace, caesar_shift, cellular_automaton, cheapest_network, count_divisible, crt_smallest, dictionary_rank, digit_root, expression_eval, from_base, grid_sum, interval_scheduling, list_ops, luhn_check, min_heap_ops, run_length, sort_list, string_rewrite_nonidentity.

**Surviving clusters (18, G per part = 9):** binary_search_trace, caesar_shift, cellular_automaton, cheapest_network, count_divisible, crt_smallest, dictionary_rank, digit_root, expression_eval, from_base (to_base_wide not passing), grid_sum, interval_scheduling, kth_smallest (through sort_list), list_ops, luhn_check, min_heap_ops, run_length, string_rewrite_nonidentity. I took the cluster map from `r2_fix3_clusters` and the manifest, which agree with audit 4's map. I did not re-derive it.

**Not passing:** to_base_wide, on capacity only (L0 space 15,928). Its cluster survives through from_base either way, so the count of 18 clusters and G = 9 do not depend on its fate.

**What would drop if other classes counted** (pooled, > 0.15):
- partial: none.
- construct: none.
- P: binary_search_trace, cellular_automaton, cheapest_network, digit_root, from_base, interval_scheduling, luhn_check, min_heap_ops, run_length and string_rewrite_nonidentity. Several of these P rules are the stated procedure itself or an identical computation (0-based positions, Kruskal, grouping into runs), so counting P as such would drop lineages for being solvable.
- artifact: list_ops, min_heap_ops and string_rewrite_nonidentity.

**NEW rules (mine; they do not decide a drop here):**
- (cue) "digit sum once, then its first digit" reads 0.195–0.211 at every level of digit_root. It is right whenever the one-round sum is below 10 or ends in 0 or 9, an arithmetic property of digit roots.
- (cue) "fewest clashes first" reads 0.51 (L0) down to 0.23 (L6) on interval_scheduling. It needs all pairwise clash counts, which is no cheaper than the stated procedure. Whether it counts as "cheap" or "costly" is PENDING LEAD REVIEW.
- (partial) truncated CRT search reads 0.37 / 0.19 at crt_smallest L0 / L1.
- If the NEW cues counted, digit_root and interval_scheduling would drop (16 lineages and 16 clusters, G = 8). If NEW partial counted as well, crt_smallest would also drop (15, G = 7).

## 10. Discrepancies with the implementer's records (all reported)

1. **R-31 classes.** The implementer counts cue + partial + construct. The lead's R2 column is audit 4's "cues only". No survivor changes. hamming_error_position and prime_factor_query were dropped for partial rules, but they also have non-distinct levels and stay dropped under R-32.
2. **R-32 estimate.** The implementer took the larger of two seed sets, and its test `test_every_survivor_is_within_the_bound_distinct_and_has_capacity` asserts every seed set ≤ 0.15. **On my fresh seeds alone, interval_scheduling L0 "shortest first" reads 0.1512 (> 0.15).** Pooled it reads 0.1409 (SE 0.0039), which is what decides under R-32. A diagnostic over 20,000 further items, not pooled, reads 0.1411. The margin to the bound is about 0.009, roughly 2.3 SE.
3. **NOTES_FIX4_R2.md is stale.** As committed in 7cd0ac5a it says 19 survivors, G = 18, D = 14,350 and "no lineage passes only under a per-cluster builder". The manifest says 18 survivors, G = 9, D = 27,680, and to_base_wide NOT_REGISTERED on capacity. My figures agree with the manifest.
4. **to_base_wide's status.** The manifest writes NOT_REGISTERED with "fate left to the addendum". R-26 says a capacity failure is dropped. R-28/R-36 hold lineages that fail only under the builder as written. PENDING LEAD REVIEW.
5. The brief spoke of 19 survivors. By the time I read the manifest it held 18 plus to_base_wide not passing, which my measurement confirms.

## 11. What I could not verify

- The real pool structure: several roles sharing `taken`, the registered level mix, the family partition and the other evaluations' items (cross-evaluation text collisions). Capacity is the single-call model of section 5.
- The strict cluster map itself, which I took from `r2_fix3_clusters` and audit 4.
- Semantic difficulty: only the stated parameters were measured. No model was run.
- Whether cheap rules beyond the three batteries and my nine NEW ones exist. Each round so far has found some.
- The repository test suite. The brief did not ask for it, and I did not run it.

## 12. My slips and failed attempts (kept)

- f_render attempt 1 failed because PYTHONPATH was missing (f_render_attempt1_failed.out).
- In NEW-rule run v1, my list_ops rule "ignore all moves and reverses" was labelled cue. On items without those steps it equals the procedure, so it is an artifact. I relabelled it and added a `[cond]` version (≤ 0.074 where it applies), patching my own file with a Python string replacement. The v1 outputs are kept as `f_rules_new_4000_v1.*`.
- Smoke outputs `keys_smoke100.json` and `rules_smoke100.json` are in the parent scratch directory.
- No forbidden command was run: no rm, chmod, chown, sudo, mv, pkill, killall, `sed -i` or `ruff --fix`. No background process was left running. Nothing was written under /tmp or in any worktree.

Astra review: NOT_PERFORMED
