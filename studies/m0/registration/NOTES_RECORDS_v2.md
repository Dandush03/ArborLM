# NOTES_RECORDS_v2: the stage 5 and stage 6 records of M0

This file stands alone and supersedes `NOTES_RECORDS.md` and `NOTES_RECORDS_fieldmap.md` in this folder.
Self-check by the implementer, completed after the independent records check (`docs/reviews/m0-fresh-run-2026-11-26/records_check/RECORDS_CHECK.md`).
Not Astra validation, not human approval. Astra review: NOT_PERFORMED. No model has been run on any M0 item.

## What builds the records

`studies/m0/registration/build_records.py` writes, deterministically (sorted keys, indent 2, trailing newline, no timestamp) and with the SHA-256 of
every input and of itself recorded in each file:
`studies/m0/manifests/status_record_v1.json`, `registration_record.json` and `g_gen_record.json`.
Command, from the worktree root: `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/registration/build_records.py --root . --out <dir>`.
It stops, writing nothing, if an input hash differs from a hash recorded elsewhere, if the registered lineages differ from the expected table
(R1 A 4 clusters/5 lineages, B 1/1; R2 A 8/9, B 6/6; M1 A 8/15, B 6/8; C1 A 13/17, B 4/4; 65 in all), if its counts differ from the partition or
capacity record, if `domain_list.json` differs from ADR-0033 section 6.8, or if any of the 49 frozen generator files differs from its recorded hash.

## Where each item of stage 6's sentence sits (`g_gen_record.json`, `stage_6_items` unless stated)

| Item | Field |
|---|---|
| the survivor list of record and its hash | `survivor_list_of_record` |
| the map and its hash | `map_of_record` |
| the seven hashes of the fresh run (stage 1S point 9) | `fresh_run_seven_hashes_stage_1S_point_9` (i survivor list; ii script listing; iii copy audit and run copies; iv class table and amendment list; v pooling script and field table; vi dry run; vii run plan) |
| the record of the stage-2 conditions and its hash | `record_of_the_stage_2_conditions` |
| the hash of every output file of the run as taken when its unit ended | `hash_of_every_output_file_of_the_run_as_taken_when_its_unit_ended`: the three committed hash records (`run/hashes_seed{1,2,3}.json`) by path and SHA-256, the run plan, 325 files per seed, 975 in all, 11 units, every exit status 0 |
| its outputs | not committed; see "What is not committed" |
| its pooled table's hash | `pooled_table` |
| the lineages it dropped | `lineages_dropped_by_the_fresh_run` (15, with `dropped.json` and the seven that come from the rule's wording) |
| the candidates and their hash | `candidates` |
| the partition and its code hash | `partition` |
| the rounds of stage 4 with every count | `rounds_of_stage_4_with_every_count`: the capacity record by path and SHA-256 plus a per-round summary; every per-level count is in the capacity record |
| the registered lineages | `registered_lineages` (65); by cluster in `registration_record.json` |
| the first version of the status record and its hash | `status_record_first_version` |
| G per part with the strictest counts beside it | `G_per_part_with_the_strictest_counts_beside_it` |
| N_e | `N_e` (R1 5, R2 15, M1 14, C1 17) |
| the counts of each part in clusters and in groups | `counts_of_each_part_in_clusters_and_in_groups` |
| every hash of stage 0 | `every_hash_of_stage_0` (both hash records and every entry of them) |
| the human lead's domain list | top-level `domain_list`, from `studies/m0/manifests/domain_list.json` (decision "Yes, the five", record `HUMAN_LEAD_WORDS_13.md`; the five rows of section 6.8, code writing NOT MEASURED) |
| the frozen generators | top-level `frozen_generator_files`: commit `7cd0ac5a` and the 49 files of the import closure of the 65 registered builders, path and SHA-256 each, re-hashed by the script |
| departures, rulings, confirmations | top-level `departures`, `awaiting_human_lead_confirmation`, `gap_filling_rulings_that_lean_toward_passing`, `lead_rulings`, `independent_check_of_the_records` |

## Departures and rulings

`departures` lists: R-56 (M1a echo rule), R-60 (five C1 scripts run with `-I` ignore `PYTHONHASHSEED`), R-61 (key, pool builder and capacity runner hashed after the partition),
R-62 (b) (the key relabels object, event and invented words as well as names: wider than "names relabelled only", less favourable to passing), R-62 (c) (the
`R2.caesar_shift` exception: favourable to that registered part-B lineage), R-66 (141 lineages carry no single committed reason; 180 counting the superseded-by tier;
against section 8 and section 3 item 6) and the family counts. Each carries an excerpt checked against the ruling's own text and the records check's
classification, which is PENDING LEAD REVIEW. **Awaiting the human lead's confirmation: R-62 (c).** R-65 is not a departure.
`gap_filling_rulings_that_lean_toward_passing`: R-46 (a field is a rule only if its prediction does not use the item's answer) and R-54 (aggregate format lines in the C1 fixtures are not answers).

## Strictest counts (R-65)

The strictest count of a part is the number of borderline groups that hold a registered cluster of that evaluation and part, with every borderline pair of the map
merged transitively whatever the status of the lineages it passes through. G and strictest: R1 A 4 and 1, B 1 and 1; R2 A 8 and 1, B 6 and 6; M1 A 8 and 1, B 6 and 6;
C1 A 13 and 1, B 4 and 4. Every part A lies in the single 57-cluster group. The count that merges only pairs joining two registered clusters directly (R1 A 4, R2 A 6, M1 A 4,
C1 A 3, every part B equal to G) is printed beside it as information and is not the strictest count.

## The three reason tiers (status record; R-66)

Of the 263 written lineages that are not on the survivor list (header `counts.reason_tiers_of_the_263_not_registered_before_the_survivor_list`):
- 83 have a reason from a named source: `drops_after_final_checks.txt` (5; the file states a header and no figure), the fix-4 manifests (64), the `NOT_REGISTERED` tables of the lineage modules (14).
- 39 have only "superseded by X" from a committed supersession field (C1 5, M1 6, R1 28), labelled as that tier.
- 141 have the fixed sentence "not on the survivor list of record; superseded or dropped before it (no single committed reason found)" (C1 38, M1 51, R1 48, R2 4).
Each REGISTERED lineage (65) carries `stage: "stage 5, registration"` and `established_by`, keys into the header's `records_establishing_registration` (survivor list, stage-2 conditions,
fresh-run drops file, candidate list, partition, capacity record: path and SHA-256 each). The two capacity drops and the 15 fresh-run drops carry `source_record`.
Counts: 345 written lineages, 65 REGISTERED, 280 NOT REGISTERED (15 at the fresh run, 2 at capacity, 263 before the survivor list). The seven wording drops carry the note of `HUMAN_LEAD_WORDS_11.md`; no status changes.

## Family counts

From `capacity_of_record.json` (the author's descriptive `family` label; neither cluster nor lineage). Per part: R1 5/1, R2 8/6, M1 12/7, C1 10/3. Union over both parts: R1 6, R2 14, M1 17, C1 10.
Fewer than 12 is recorded as a departure from ADR-0033 line 268 and stops nothing (section 13 item 14 (a)); the record flags parts and unions, and the text reads line 268 per evaluation, so
the part entries are over-listing, labelled. Section 9 item 5: R1 part B has one cluster (ONE CLUSTER); every other part is computed as written with G - 1 degrees of freedom.

## What is not committed

The run's output files (975, under `experiments/m0_fresh_run_20261126/`, git-ignored) are held by reference: their SHA-256 are in the three committed hash records, and the records check found all 975 present and equal.
Their retention is outside git. This script does not open them.
