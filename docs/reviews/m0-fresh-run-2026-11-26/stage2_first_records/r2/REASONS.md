# M0 stage 2, R2: what was read, per lineage

Paths are relative to the implementation worktree `agent-a0c9d741ea96ce52f` (HEAD `128a02a7`; `git diff 7cd0ac5a HEAD -- studies/m0/*.py` empty). The builder of record of each lineage is the function `r2_fix4_set.fix4_set()[id].build`, resolved with `inspect` (not by name: several files define functions of the same name). Fixture items: `s2r2_examples.out.json` (first item per level) and `s2r2_check.out.json`. Level figures: `s2r2_check.out.json` ("levels") and `s2r2_levels_exact.out.txt`.

Common to every lineage, second solver: `docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_solver.py` (SHA-256 `559e918c…46a5`), committed at `b78e58b1`; dispatch by name at :464-470; reads only the question. Provenance: `FINAL_R2.md`:3-5 (separate auditor context, Opus 5.5), :16 and :31 (0 mismatches, 0 errors, 133,000 items, 19 lineages including `to_base_wide`); `f_solver.py`:2-4 (written from `f_render.out`, `f_shapes.out`, `f_phrases.out`); `f_render.py`:20 prints `--> ANSWER: <key>` under each rendered item; `f_shapes.py`:33 prints each example's key (`-> {a!r}`). Section 8 item 1 of the approved text: fixtures received carry no answer from the first solver; the author has not read the generator's or first solver's source. Spec: ADR-0033 §6.2 (`Difficulty. Five registered levels (depth, steps or program size)`), addendum 1 §4A stage 2, §8, §12 item 16.

| Lineage | Builder of record | Wording read | Levels read |
|---|---|---|---|
| binary_search_trace | `studies/m0/lineages_r2_fix3.py`:101-124, helper `_probe_positions` :86-98 | rule text :118-121, asks :123-124 | n :107-109 |
| caesar_shift | `lineages_r2_fix4.py`:79-87 | :86; `vocab.PSEUDO` all `[a-z]+` (checked) | words :82 |
| cellular_automaton | `lineages_r2_fix3.py`:235-258, `_ca_step` :230 | :256-257 | cells :241, steps :251 |
| cheapest_network | `lineages_r2_fix4.py`:90-107, `lineages_r2_graphs.mst_weight` :13-30 | :105-106; Retry on disconnected :99-100 | towns :94 |
| count_divisible | `lineages_r2_fix4.py`:60-73 | :71-72 (the fix-4 clause) | n :67, range :65 |
| crt_smallest | `lineages_r2_fix4.py`:180-194 | :193; coprime Retry :187-188 | k :185, moduli :186 |
| dictionary_rank | `lineages_r2_fix3.py`:296-312, `_unrank_partial` :269, `_rank_partial` :281, `_DR_PLAN` :293 | :305-312 | `_DR_PLAN` :293 |
| expression_eval | `lineages_r2_fix4.py`:130-177, `lineages_r2_parsing.evaluate` :141-181, `lineages_r2_fix3_b._num/_paren_sum` :190-195 | ranked :156-158, left-to-right :173-175 | k :136, :160; extra parentheses :144-152, :167-169 |
| from_base | `lineages_r2.py`:106-112 | :111 | base :108, digits :109 |
| grid_sum | `lineages_r2.py`:176-191 | :188 (diagonal phrase), :190 | rows/cols :178 |
| list_ops | `lineages_r2.py`:57-88 | :87; drop guard :64-65 | start :59, ops :62 |
| luhn_check | `lineages_r2_codes.py`:28-48, `luhn_total` :12-21 | rule :24-25, :43, :46-47; assert :42 | n :33 |
| min_heap_ops | `lineages_r2_fix3.py`:205-224, `_heap_insert` :182, `_heap_pop` :190 | :218-223; distinct xs :211 | n :210, removals :212 |
| run_length | `lineages_r2_fix3.py`:318-332 | :331; letter differs from previous :326 | runs :325, length :327 |
| sort_list | `lineages_r2.py`:38-44 | :43 | n :40 |
| string_rewrite_nonidentity | `lineages_r2_rev2.py`:115-135 | :134; pattern from current string :123-125, non-empty :130-132 | length :120, rules :122 |
| to_base_wide | `lineages_r2_rev2.py`:138-150 | :149 | base :143, n :144 |

Keys checked by hand on the rendered fixtures (my arithmetic, beside the solver): binary_search_trace L0/0 (107), caesar_shift L0/0 (dlyti), crt_smallest L0/0 (104), dictionary_rank L3/0 (14237), expression_eval L0/0 (69), from_base L0/0 (935), grid_sum L3/0 (11, non-square diagonal), list_ops L0/0, string_rewrite_nonidentity L3/0 (aaac), to_base_wide L0/0 (4525). All equal the key.

Per-lineage reasons are the `reason` strings of `stage2_conditions_r2.json`, written in `s2r2_record.py`.
