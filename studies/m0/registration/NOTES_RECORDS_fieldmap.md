# NOTES_RECORDS: stage 5 and stage 6 records of M0 (assembled by code)

Self-check by the implementer. Not independent review, not Astra validation, not human approval. Astra review: NOT_PERFORMED.
Nothing here is a registration or a result; the record of record waits for the human lead's domain list (ADR-0033 choice 2).

Command (from the implementation worktree root, inputs committed at `95852f3c`):
`PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/registration/build_records.py --root . --out <staging>`
The script stops (exit 1, nothing written) if an input hash differs from a hash recorded elsewhere, if the registered lineages differ
from the expected table (R1 A 4/5, B 1/1; R2 A 8/9, B 6/6; M1 A 8/15, B 6/8; C1 A 13/17, B 4/4; 65 in all), or if its counts differ
from the partition or capacity record. It did not stop. A second run gave byte-identical files.

## Where each item of stage 6's sentence sits (`g_gen_record_DRAFT.json`, under `stage_6_items` unless stated)

| Item of the sentence | Field |
|---|---|
| the survivor list of record and its hash | `survivor_list_of_record` |
| the map and its hash | `map_of_record` |
| the seven hashes of the fresh run (stage 1S point 9) | `fresh_run_seven_hashes_stage_1S_point_9` (i survivor list; ii script listing; iii copy audit and run copies; iv class table and amendment list; v pooling script and field table; vi dry run; vii run plan), also under `every_hash_of_stage_0` |
| the record of the stage-2 conditions and its hash | `record_of_the_stage_2_conditions` |
| the hash of every output file of the run as taken when its unit ended | `hash_of_every_output_file_of_the_run_as_taken_when_its_unit_ended`: the three hash records with their SHA-256, the run plan, files and attempts counted (325 files per seed, 975 in all, 11 units, every exit status 0) |
| its outputs | the files themselves are not committed; the `dir` fields of the hash records name the git-ignored `experiments/` directories (see "not filled") |
| its pooled table's hash | `pooled_table` (the hash of the uncompressed `pooled_table.json` from `SHA256SUMS_pooled.txt`, checked by decompressing the committed `.gz`; the hash of the `.gz`; every hash of the sums file) |
| the lineages it dropped | `lineages_dropped_by_the_fresh_run` (15, with the file's hash and the seven that come from the rule's wording) |
| the candidates and their hash | `candidates` |
| the partition and its code hash | `partition` (record, code hash, seed, derived integers, step 2 trace, counts) |
| the rounds of stage 4 with every count | `rounds_of_stage_4_with_every_count`: the capacity record by path and SHA-256, plus a compact per-round summary (G, D(G), failing lineages, per cluster k, D_lin and the union by level); the per-level draw counts are in the capacity record |
| the registered lineages | `registered_lineages` (65, per evaluation and part); by cluster in `registration_record.json` |
| the first version of the status record and its hash | `status_record_first_version` (and the file `status_record_v1.json`) |
| G per part with the strictest counts beside it | `G_per_part_with_the_strictest_counts_beside_it` (see below) |
| N_e | `N_e` (R1 5, R2 15, M1 14, C1 17; recomputed from the map and the candidates and equal to the partition record) |
| the counts of each part in clusters and in groups | `counts_of_each_part_in_clusters_and_in_groups`: the partition record's counts (candidates) and the registered clusters and groups per part |
| every hash of stage 0 | `every_hash_of_stage_0`: both hash records by path and SHA-256 and every entry of them; `verified_against_files_in_this_worktree` lists the 38 files whose hash the script computed again and found equal to the record |
| top-level `status` and `domain_list` | exactly as the brief gives them; `domain_list` is `null` |
| `departures` (top level) | lead rulings R-56 (`LEAD_RULINGS_8.md`) and R-61 (`LEAD_RULINGS_9.md`) with file hashes and the ruling's title taken from the file, and the family count |

## Strictest counts

Section 1 item 3: borderline pairs are "reported with the count they would give if merged ('strictest')". Computed as the number of
groups of the map (components of the graph whose links are the borderline pairs, over all 92 clusters, statuses ignored) that hold a
cluster with a registered lineage of the evaluation in the part. Result (G, strictest): R1 A 4 and 1, B 1 and 1; R2 A 8 and 1, B 6 and 6;
M1 A 8 and 1, B 6 and 6; C1 A 13 and 1, B 4 and 4. Every part A sits in the one 57-cluster group of the map, hence 1.

The text does not say whether a chain of borderline pairs through a cluster that is not registered in that evaluation merges two
registered clusters. The alternative (direct pairs between two clusters both registered in the evaluation and part) is printed beside it:
R1 A 4, R2 A 6, M1 A 4, C1 A 3, every part B equal to G. Which is "the strictest count" is not chosen; the field `choice_left` reads
`PENDING LEAD`. The main `strictest_G` values are the chain reading, computed and not a placeholder.

## Family count

Taken from `capacity_of_record.json` (`families`, `n_families`; recomputed counts equal). Per evaluation and part: R1 A 5, B 1; R2 A 8, B 6;
M1 A 12, B 7; C1 A 10, B 3. Union over both parts (my addition, labelled as such): R1 6, R2 14, M1 17, C1 10. Fewer than 12:
every part except M1 A, and the union for R1, R2 and C1. All are listed in `family_count.fewer_than_12_is_a_departure_from_ADR_0033_line_268`
and in `departures`; this stops nothing (section 13 item 14 (a)). The text says "per evaluation and per part"; I did not decide whether
the line-268 requirement is per evaluation or per part, so both are flagged.

## Section 9 item 5

R1 part B has one cluster: reading `ONE CLUSTER`. No part has none. Every other part is read "computed as written, G - 1 degrees of freedom".

## Reasons before the survivor list

Of the 263 written lineages that are not on the survivor list, sources used in this order, and only where a committed file states it:
`drops_after_final_checks.txt` (5; the file states a header and no figure); the fix-4 manifests (R1 shapes, R2 lineages before capacity, M1
candidates and `excluded_everywhere`, C1 lineages); the `NOT_REGISTERED*` tables of `studies/m0/lineages_*.py` (read with `ast`, nothing
imported or executed); then, only if none of those states a reason, the supplementary committed statements (`SUPERSEDED` of
`lineages_r1_clusters.py`, the `earlier_id`, `replaces`, `supersedes` and `superseded` fields of the manifests). Statements from all
sources are kept in `reason_statements`; the `reason` is the first.

- Reason by a source the brief names: 263 - 141 - 39 = 83 (5 final checks, 64 fix-4 manifests, 14 lineage-module tables); per evaluation and
  per kind in the status record's `counts.not_registered_by_stage_per_evaluation`.
- Only a supplementary statement ("superseded by ..."): 39 (C1 5, M1 6, R1 28, R2 0). Listed in `counts.not_registered_whose_only_committed_statement_is_a_supplementary_one`.
- **No single committed reason found: 141** (C1 38, M1 51, R1 48, R2 4), recorded with the sentence `not on the survivor list of record; superseded or dropped before it (no single committed reason found)`.
  If the supplementary tier is not accepted as a reason, the number is 141 + 39 = 180.
  They are listed in `counts.not_registered_with_no_single_committed_reason.lineages`.
- 8 keys of the lineage-module tables name sub-shapes (for example `C1.merge_two_sorted[cmp shape]`) and match no written lineage; listed in
  `lineage_module_keys_not_matching_a_written_lineage`, not used.
- `M1.min_cost_packs` is listed under `excluded_everywhere` in the M1 manifest, which gives no text; that statement is recorded as it stands.
- The 7 wording drops carry the note (field `note`, source `HUMAN_LEAD_WORDS_11.md`); their status is unchanged.
- Counts per stage (all evaluations): fresh run 15, capacity 2 (`M1.rectangle_r3`, `R2.cellular_automaton`), before the survivor list 263.
  `C1.cellular_update` (R2 part B) is a cluster that had a candidate and lost every lineage at capacity; it keeps part B (`registration_record.json`).

## Not filled, or filled with a caveat

1. **The domain list** (`domain_list: null`): the human lead's, by design.
2. **The run's outputs themselves** are not committed (git-ignored `experiments/m0_fresh_run_20261126/...`); only their hashes are. Not opened by this script.
3. **The class table** (`iv_class_table`) lives on `claude/m0-spec`; its hash is copied from `HASH_RECORD.json` and not checked against a file here
   (listed under `recorded_but_not_checked_here_because_the_file_is_not_in_this_worktree`).
4. **"Strictest counts"**: computed, but the reading is not settled by the text (above). `choice_left` is `PENDING LEAD`.
5. The text of stage 1S point 9 speaks of "five things" and stage 6 of "seven hashes"; I followed `HASH_RECORD.json`, which has seven (i to vii).
6. The status record does not parse figures out of the free-text reasons of the fix-4 manifests; a few structured fields are copied
   verbatim (`manifest_fields`). Figures in the text are the manifests' own words.
7. Section 9 item 5 and the family count are readings of the record, not statistical results. No model was run; nothing here is a result.

## Hygiene

- The script carries `# ruff: noqa: E501` for its long prose strings; `ruff check` is clean with the worktree's `pyproject.toml`, `ruff format --check` clean (the format was applied to this new file only).
- First attempt of the script: a `KeyError` (`union_by_level` absent in a cluster of a capacity round), nothing written.
- `final/` (a sibling of this directory) is a first successful run that is **superseded and left in place**: its status record words the fresh-run reason
  as "with rounding uncertainty 0.16115" where 0.16115 is the absolute excess plus the rounding uncertainty, and it lists the textless
  `excluded_everywhere` statement of `M1.min_cost_packs_r2` ahead of the lineage-module reason. Use `final_v2/`.
- `experiments/_scratch/m0_registration_impl_20261126_spec.md` is a copy of the approved addendum text that I wrote next to the staging directory to read it.
- This notes file was corrected once by overwriting (the line on the 83 lineages with a reason from a named source gave 65 and 13 for 64 and 14);
  the same applies to the build script, which I edited in place twice before its first run (a line-length suppression and a `.get`).
