# M0 lineage repair: lead rulings after fix round 3 and the fourth audits (2026-11-25)

By the scientific lead (Claude Fable 5.2). Working rulings only; nothing here registers a lineage, sets a bound or changes a registered rule. Fix round 3 (four `arbor-implementer` subagents, Claude Sonnet 5.5): `8fd608fe` (R2), `cd031bf6` (C1), `a790e503` (M1), `f19d08c8` (R1). Fourth audits (four `arbor-auditor` subagents, Claude Opus 5.5): `audit4_r1/`, `audit4_r2/`, `audit4_m1/`, `audit4_c1/`, copied by the lead unchanged from each auditor's `deliver/` directory.

## The state after the one authorised fix round

None of the four sets is ready to register. Clusters with a candidate, and clusters left if a shortcut bound were set at each value (the auditors' counts, cheap rules only, before the cross-evaluation rule is applied):

| Evaluation | Clusters with a candidate | bound 0.10 | bound 0.15 | bound 0.25 |
|---|---|---|---|---|
| R1 | 23 | 8 | 10 | 15 |
| R2 | 36 | 15 | 20 | 24 |
| M1 | 20 | 18 | 18 | 18 (if the slot_permutations wording is fixed) |
| C1 | 25 (23 without the two variants) | 16 (14) | 17 (15) | 21 (19) |

Answer keys: zero mismatches in every audit. In every set the auditor found cheap rules that were absent from the implementer's battery, several created by the rebuilds (R1 queue +0.79; R2 gcd 0.62-0.91 and permutation_power 1.00 at two levels; M1 mode_tally +0.38; C1 partition_pass_f3 and loop_sum closed forms at 100%).

The full M0 suite after the round: 1,072 passed, 2 xfailed, 2 FAILED (`experiments/_scratch/m0_fix3_suite_20261125/pytest_m0_full.txt`): the package-hygiene tests find set iteration in `lineages_m1_fix3_c.py:116`, `lineages_r2_fix3_c.py:172`, `r1_fix3_battery.py:624`, `r1_fix3_capacity.py:346`, and an import of the auditor's `a3_heur` in `r2_fix3_battery.py`. Not fixed: the authorised round is over. The lead's brief had each implementer run only its own evaluation's tests, which is why none saw it.

## Rulings

- **R-18.** `subtraction_game`'s redraw until the yes/no answer balances is a redraw under R-1/R-13. The earlier acceptance of it as balancing is withdrawn.
- **R-19.** Rejecting an item because its answer is a sentinel, zero or empty (C1: coin_change_table_f3, grid_path_table, mirror_pointers, run_length_scan, string_methods_f3; R1: categories_follow_r5, kinship_ancestor_r4) is answer-conditional rejection and falls under R-13 unless the rejection is needed for the item to be well posed. Each case is to be shown one or the other.
- **R-20.** The two C1 variants (`fast_power_f3`, `counter_list_f3`) may stand only as new lineages in their own clusters, as the auditor agrees; `fast_power_f3` keeps its `res` shape only. The implementer's map still files them under the originals; that is a defect.
- **R-21.** "Levels control difficulty" is part of a lineage's validity: R1 has 18 shapes whose levels produce identical items; M1's capacity widening collapsed levels in four lineages. A lineage whose levels are not distinct is not registrable as it stands.
- **R-22.** Capacity is computed against the pool builder as written (`core.generate_pool` balances per lineage and de-duplicates on text including names), or the builder's per-cluster balancing is specified in the addendum first. The M1 capacity pass assumes a builder that does not exist.
- **R-23 (stop).** The round the human lead authorised is finished. No further authoring, fixing or auditing starts without the human lead's word.

## Slips recorded this round

Implementers: `chmod +x` on a scratch file (R2); `pkill -f` once and `sed -i` on `/dev/null` twice, and a stray background `cat` left running (C1); `sed -i.bak2` leaving `tests/test_m0_m1_fix3_capacity.py.bak2` (M1); `sed -i.x` on `/dev/null` (R1). Auditors: `sed -i.bak` on a scratch script (C1); two auditors wrote to scratch through the session worktree's `experiments` symlink after the first path was refused. All were forbidden by the briefs.

Astra review: NOT_PERFORMED
