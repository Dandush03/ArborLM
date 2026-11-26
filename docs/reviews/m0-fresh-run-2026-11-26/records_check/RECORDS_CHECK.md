# M0 stages 5 and 6: independent check of the records (registration, status record v1, G-gen's record)

**Verdict: RECORDS AGREE WITH THE SOURCES AFTER REQUIRED CHANGES.** Every number, id, part, status, reason and hash I recomputed agrees with the committed records. No count or status needs to change. The required changes concern completeness: what the status record says set each status, which rulings the departures list carries, the stale notes, and naming the frozen generator files.

- Checker: `arbor-auditor` context, model **Claude Opus 5.5** (`claude-opus-5-5`), 2026-11-26. I wrote none of the records, `build_records.py` or the notes, and did not import `build_records.py` (it was only run, unchanged, for item 5).
- This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. **Astra review: NOT_PERFORMED.**
- Under check: `claude/m0-impl`, worktree `agent-a0c9d741ea96ce52f`. The records were committed at `0f664401`. HEAD at check time was `e57f8709` (a merge that touches only `docs/PARAMETER_CHANGELOG.md`). SHA-256: `registration_record.json` e50b69f8…3e39, `status_record_v1.json` b1f94e9d…39ae, `g_gen_record.json` c3a0d645…dfde0, `domain_list.json` bd9a4e58…6069, `build_records.py` 0d5d2889…0751. All equal the brief.
- Specification: addendum 1 at `2c944302` (`spec/addendum1_2c944302.md` in my scratch directory, SHA-256 154d16a0…923c, equal to `approved_text` in HASH_RECORD.json).
- Environment: macOS arm64 (Darwin), uv 0.12.15, CPython 3.12.14 via `uv run --locked`. Every command used `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1` and was run from the implementation worktree root with a `timeout` of 300 s or less (500 s for the output hashing).

## Commands (from `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f`, D = this deliver directory)

```sh
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python $D/generator_files.py --root . --out $D/out/generator_files_raw.json   # also writes out/families.json
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python $D/check_records_v3.py --root . --spec-root /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/m0-spec-push-20261126 --families $D/out/families.json --out $D/out/check_records_v3.json
PYTHONDONTWRITEBYTECODE=1 timeout 500 uv run --locked python $D/hash_run_outputs.py --root . --out $D/out/run_outputs_hash_check.json
git diff --name-status 7cd0ac5a HEAD -- 'studies/m0/*.py' > $D/out/git_diff_name_status_7cd0ac5a_HEAD_studies_m0_py.txt
PYTHONDONTWRITEBYTECODE=1 timeout 60 uv run --locked python $D/make_registered_generator_files.py $D
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python studies/m0/registration/build_records.py --root . --out $D/out/rebuild_attempt1
```

Failed attempts are kept:
- `check_records.py` (attempt 1) stopped with a `TypeError`. The G-gen record holds survivor *counts* under `survivor_list_of_record.lineages`, and I had assumed ids. No output was written.
- `check_records_v2.py` ran, but my parse of ADR-0033 section 6.8 ran on into section 7's table. That gave a false `rows_equal: false` (38 rows; `out/check_records_v2.json`). This was my error, not the record's.
- `check_records_v3.py` fixes only that parse. Every other output is equal between v2 and v3.

## Item 1: registration

The registration is recomputed from the sources as follows:
- Candidates are the survivor list less the 15 lineages in `dropped.json`, intersected with the stage-2 PASS rows (82 of 82 PASS).
- Each cluster's part is read from `partition_of_record.json`. I computed **no** `cluster-partition` stream, because section 4 item 7 allows the partition to be computed only once. I checked it for consistency: the part clusters are exactly the 44 candidate clusters, each group has one part, the group identities are correct, the parts of the 48 no-candidate clusters are right, and the candidate counts equal the record.
- Stage 4 is replayed from the counts in `capacity_of_record.json`. Per round I checked G, k, the targets, each lineage's failure (count below D_lin at any level, or a solver disagreement), the union condition only where every lineage passed, `failing`, and the fixed point. D_lin is single-valued per (G, k) and D(G) per G.

Results (all equal to `registration_record.json`, id for id and cluster for cluster):

| | R1 | R2 | M1 | C1 | total |
|---|---|---|---|---|---|
| survivors / candidates / registered | 10 / 6 / 6 | 17 / 16 / 15 | 29 / 24 / 23 | 26 / 21 / 21 | 82 / 67 / 65 |
| N_e | 5 | 15 | 14 | 17 | |
| G_A (clusters/lineages) | 4/5 | 8/9 | 8/15 | 13/17 | |
| G_B (clusters/lineages) | 1/1 | 6/6 | 6/8 | 4/4 | |
| groups of registered clusters A / B | 1 / 1 | 1 / 6 | 1 / 6 | 1 / 4 | |
| candidate clusters A / B (groups) | 4/1 (1/1) | 8/7 (1/7) | 8/6 (1/6) | 13/4 (1/4) | |
| strictest under R-65, A / B | 1 / 1 | 1 / 6 | 1 / 6 | 1 / 4 | |
| direct-pairs information count, A / B | 4 / 1 | 6 / 6 | 4 / 6 | 3 / 4 | |
| section 9 item 5 | A 3 df; **B ONE CLUSTER** | A 7 df; B 5 df | A 7 df; B 5 df | A 12 df; B 3 df | |

- Capacity removed two lineages, both in round 1 and both for missing their own demand: `M1.rectangle_r3` (A, G 8, k 6; levels 0 and 1 ended on the attempt budget) and `R2.cellular_automaton` (B, G 7, k 1; level 0). Both detail blocks equal the capacity record.
- `C1.cellular_update` is the only cluster that had a candidate and lost it at capacity (R2 part B, kept in part B). The registration record lists it under R2 B. In the status record, its three C1 lineages and R2.cellular_automaton carry cluster part B with `part_binds_it`.
- Across 616 cells: 0 solver disagreements and no timeouts (R-64 has nothing to list).
- Expected totals 65 (R1 6, R2 15, M1 23, C1 21): **reproduced**.

## Item 2: status record

I checked all 345 lineages of the map field by field: evaluation, global cluster, group identity, cluster part (or `none` with the group's part beside it, and `tied_by_borderline_pair`), `part_binds_it`, on the survivor list, candidate, status, and stage. **0 differences.**
- Stages: 65 registered; 15 at the stage-1S fresh run; 2 at stage-4 capacity; 263 before the survivor list. No lineage is not registered for an unexplained reason.
- The 15 fresh-run drops: every field of `reason` in `dropped.json` is copied exactly (rule, unit, level, reading, source, shape, excess, rounding uncertainty, |excess| + uncertainty, pooled figure, bound 15/100), and `n_rows_over_the_bound` equals the number of rows. The reason row is the row with the largest |excess| + uncertainty. That sum and the comparison with 15/100 hold in exact fractions. The prose reason contains the rule, unit, level, decimal, fraction and bound.
- The 2 capacity drops: the detail equals the capacity record's `removed` entry plus evaluation and part. The prose gives the round, part, G, k and each level's count, demand and how it ended.
- Wording notes: they are on exactly the seven lineages named in `HUMAN_LEAD_WORDS_11.md` (R1 `spatial_grid_walk_r5`, `swap_tracking_r5`; C1 `circle_elimination_r2`, `cond_chain_f3`, `shared_lists_f3`, `union_find_links_f3`; R2 `list_ops`). Each keeps status NOT REGISTERED at the fresh-run stage, and the note source is that file.
- R-66 tiers: **83 / 39 / 141** reproduced.
  - Sample (seed 20261126, `random.Random.sample`): 40 of the 83 named-source reasons and 20 of the 39 "superseded by" reasons. Each was checked against the file it cites: the JSON entry of that lineage holds the text; the `ast.literal_eval` of the cited module table holds that key and text; the id is in `drops_after_final_checks.txt` with the quoted header; or the supersession field ties the two ids. **60 of 60 FOUND**, and also **122 of 122** when all were run. Lists: `out/check_records_v3.json` keys `sample_named_40` and `sample_superseded_20`.
  - The supersession matcher is permissive: it accepts the older id anywhere in the newer id's manifest entry. Where the source is a module table or the C1 `superseded` map, the match is exact.
  - **No reason was invented.** The 141 carry the fixed sentence exactly, with empty `reason_statements`. I searched every named source for each of the 141. 24 occur there only as cluster names (`strict_cluster`, `capacity.clusters`, `dropped_clusters` keys, `cluster_members`), never as a lineage entry with a reason. So none of the 141 has a reason that was missed.
  - The one truncated reason (`M1.binomial_choose_r3`, ending "group-pro...") is truncated in the source manifest itself.

## Item 3: G-gen's record against the sentence of stage 6

| Item of the sentence | Field | Result |
|---|---|---|
| survivor list of record and its hash | `stage_6_items.survivor_list_of_record` | hash equal; counts 10/17/29/26 = 82 |
| the map and its hash | `map_of_record` | 1ba6ddd5…809c, equal to the file, HASH_RECORD and HASH_RECORD_STAGES_2_TO_4; counts 345/92/294/99/30 |
| the seven hashes of stage 1S point 9 | `fresh_run_seven_hashes_stage_1S_point_9` | every path hashed again, all equal. Class table ccea7d78…d24d is equal both to the file in the m0-spec worktree and to `git show 2c944302:` of it (the record's note "not checked here" can now be closed). Stage 0 says "five things" and stage 6 "seven": a wording inconsistency in the text, not in the record |
| record of the stage-2 conditions and its hash | `record_of_the_stage_2_conditions` | 81d454a2…3e55 equal; 82 rows |
| hash of every output file as its unit ended | `hash_of_every_output_file_…` | references the three **committed** records `run/hashes_seed{1,2,3}.json` (hashes equal; tracked in git), 325 file hashes each, 975 in all. I hashed (without parsing) all 975 files on disk under `experiments/m0_fresh_run_20261126/`: **975 equal, 0 differ, 0 missing, 0 unlisted** |
| its outputs | (none; reference only) | not committed (git-ignored); see N4 |
| pooled table | `pooled_table` | `.gz` decompresses to 68894016…3b13d = SHA256SUMS_pooled; the four committed companions (`dropped.json`, `per_lineage.json`, `report_extras.json`, `SUMMARY.md`) equal the sums file |
| lineages it dropped | `lineages_dropped_by_the_fresh_run` | 15 ids equal; per evaluation 5/5/4/1; the seven equal |
| candidates and their hash | `candidates` | 8dcc796c…946a equal; counts 6/16/24/21 = 67 |
| partition and its code hash | `partition` | record 750715d8…37e9 and code 4e43d280…4d03 equal; seed 400004; the integers equal the partition record |
| rounds of stage 4 with every count | `rounds_of_stage_4_with_every_count` | by reference to `capacity_of_record.json` (33c393fb…fb34, equal) plus a summary; replay agrees (item 1) |
| registered lineages | `registered_lineages` | 65, equal per evaluation and part |
| first version of the status record and its hash | `status_record_first_version` | b1f94e9d…39ae equal |
| G per part with the strictest beside it | `G_per_part_with_the_strictest_counts_beside_it` | equal to my recomputation (R-65 and the information count) |
| N_e | `N_e` | 5/15/14/17 equal |
| counts per part in clusters and groups | `counts_of_each_part_in_clusters_and_in_groups` | equal (candidates and registered) |
| every hash of stage 0 | `every_hash_of_stage_0` | all 34 hashes of HASH_RECORD.json and all 14 of HASH_RECORD_STAGES_2_TO_4.json occur in the record; every path-and-hash pair is equal to its file |

- Over the three records together, 398 path-and-hash pairs (158 distinct files) were checked: **0 differ, 0 missing.**
- The chain holds: registration → status v1, G-gen → registration, G-gen → status v1, G-gen → domain list. The `script_sha256` in all three records equals `build_records.py` at HEAD.
- **Strictest counts (R-65).** I recomputed them as the components of the borderline-pair graph over all 92 clusters, ignoring status, counting those that hold a registered cluster of the evaluation in the part. The map has 30 groups; the largest has 57 clusters. Every part A sits in it, so the strictest count for each part A is 1. Every part B equals its G.
- **Families.** The capacity record takes them from `source.lineage(x).family` (`capacity.py` line 801). That is the `family` field of `studies.m0.core.Lineage`, the author's descriptive topic label set where each lineage is defined (e.g. `age`, `stacks`, `temporal`). It is neither a cluster nor a lineage. I read it by importing the four loaders that `RealSource` uses, without calling any builder.
  - Per part: R1 5/1, R2 8/6, M1 12/7, C1 10/3.
  - Per evaluation (union): R1 6, R2 14, M1 17, C1 10.
  - The 9 departure entries are exactly the parts and unions below 12. The record flags both per part and per evaluation (see N3).
- **Domain list.**
  - `domain_list.json` has the five rows of ADR-0033 section 6.8, cell for cell. I parsed the table myself, including "—" and "(public)".
  - It has code writing NOT MEASURED, as in section 6.8's text.
  - It records the decision "Yes, the five", quoted in `HUMAN_LEAD_WORDS_13.md`, whose hash 5c5c0c31… is equal.
  - The G-gen copy equals the file. ADR-0033 is byte-identical on `claude/m0-impl` and in the m0-spec worktree (7719f6d4…).
- **Departures.** The record lists R-56, R-61 and the family count. My reading of R-44 to R-66 is in the next table. The classification is mine and is **PENDING LEAD REVIEW**.

| Ruling | My class |
|---|---|
| R-44, R-45, R-47, R-48, R-49, R-50, R-51, R-53, R-55, R-57, R-58, R-63, R-64, R-65 | Fill a gap the text leaves, or apply the text as written. Not departures |
| R-52 | The strict reading; enforces section 8 item 1. Not a departure |
| R-46 | Fills a gap (the text anticipates unread fields in the field table, but does not define what a "rule" is). It leans toward passing. Not a departure in my reading, but it is not in the record's list of favourable readings |
| R-54 | Reads "fixtures carry no answer" as allowing aggregate format lines taken from the keys. Favourable to the lineages; the lead names it as such. At the edge of the text; I class it as a reading, not a departure |
| R-59 | Extends point 10's plan-count run to a case point 10 does not name. Neutral. Gap |
| **R-56** | Departure (listed) |
| **R-61** | Departure (listed) |
| **R-60** | **Departure, not listed.** ADR-0033 section 6.2 says "Every process runs with `PYTHONHASHSEED=0`"; under `-I` the five C1 scripts ignore it, and the ruling says reproducibility is "not claimed" for them |
| **R-62 (b), (c)** | **Departure, not listed.** (b) The key relabels object, event and category words; the decided reading (i) is "names relabelled only" (section 13 item 1, A5). Unfavourable to passing. (c) The `R2.caesar_shift` exception favours one registered part-B lineage, was written with the partition possibly in view, and is "reported to the human lead for his confirmation with the capacity results". I found no recorded confirmation (`HUMAN_LEAD_WORDS_13.md` does not mention it; searched all `.md` under both review folders and `PARAMETER_CHANGELOG.md`) |
| **R-66** | **Departure, not listed.** Section 8 ("marked NOT REGISTERED with its reason in the status record") and section 3 item 6 ("the reason, with the stage and the record that set it") are not met for 141 lineages, or 180 counting supersession-only. R-66 accepts the shortfall rather than filling a gap |

## Item 4: "It freezes the generators at commit 7cd0ac5a"

- `git diff --name-status 7cd0ac5a HEAD -- 'studies/m0/*.py'` gives 51 entries, **all `A`**: 33 under `fresh_run/`, 11 under `registration/`, 7 under `solvers2/`. No `M`, `D` or `R`.
- The same diff over all of `studies/m0` (manifests included) also shows only additions. No generator or first-solver file has changed. The working tree is clean for them; the untracked `studies/m0/m1_rev2_gates.py.bak` is outside the record.
- `registered_generator_files.json` lists the files that define the 65 registered lineages, with SHA-256 at HEAD. Each listed file is byte-identical at `7cd0ac5a`, checked with `git show 7cd0ac5a:<f>`:
  - (a) **20 files** define `Lineage.build`.
  - (b) **32 files** hold a function reachable from a builder (through closures, partials, defaults, `__wrapped__`, or global function names).
  - (c) **49 files** form the static import closure of (b). I recommend (c) as the list for the record.
  - (d) The 97 worktree files loaded by importing the four loaders, as a superset.
- For the 82 survivors: 22 / 34 / 53.

## Item 5: determinism

`build_records.py --root . --out $D/out/rebuild_attempt1` (no `--domain-list`, since the file is now committed) exited 0. All three files are **byte-identical** to the committed ones (`cmp`), with the same three SHA-256 values. The implementation worktree was not written.

## Findings

1. **MUST CHANGE.** Section 3 item 6 asks for each lineage's status "with the stage and the record that set it". The status record names no stage or record for the 65 REGISTERED lineages (stage 5, `registration_record.json` / `capacity_of_record.json`), and gives no source file in the detail of the two capacity drops. The fresh-run drops and the pre-survivor reasons already name theirs. Fixing this changes the status hash, and with it the registration and G-gen hashes.
2. **MUST CHANGE.** G-gen's `departures` should either list R-60, R-62 (b) and (c), and R-66, or say for each why it is not one. It should also state that R-62 (c) (`R2.caesar_shift`, registered, part B) awaits the human lead's confirmation, which I found nowhere recorded. Classification: PENDING LEAD REVIEW.
3. **MUST CHANGE.** G-gen's record should name the frozen generator files with their hashes, not only the commit. Use list (c) (49 files) of `registered_generator_files.json`, or list (a) and (b) at minimum.
4. **MUST CHANGE.** `NOTES_RECORDS_fieldmap.md` describes a superseded draft: `g_gen_record_DRAFT.json`, "`domain_list` is `null`", "`choice_left` reads `PENDING LEAD`", and a class table "not checked". `NOTES_RECORDS.md` points to `final_v2/NOTES_RECORDS.md`, which is not in the worktree. The notes contradict the committed record and should be updated or marked superseded. This is documentation only; no figure is affected.
5. NOTE. Every number, id and hash recomputed agrees (items 1 to 3); item 5 is byte-identical.
6. NOTE (N2), PENDING LEAD REVIEW. The strictest count of every part A is 1. Read under section 9 item 5, each part A would then be ONE CLUSTER. The record prints the section 9 item 5 reading at G only, as the text has it; the lead may want this stated in the report.
7. NOTE (N3), PENDING LEAD REVIEW. Line 268 ("At least 12 families") reads per evaluation. The record flags parts as well: R2 A and B and M1 B are flagged although their evaluations hold 14 and 17. That is harmless over-listing, but should be labelled.
8. NOTE (N4), PENDING LEAD REVIEW. "Its outputs" are held by reference to git-ignored files. All 975 exist and match their hashes today, but their retention is outside git. The record could say where they are kept and that they are not to be deleted.
9. NOTE. Six of the 83 "named-source" reasons are pointers with no content: 5 say they are listed in `drops_after_final_checks.txt`, which "states no figure", and `M1.min_cost_packs` is "listed under excluded_everywhere (no reason text in the file)". Strictly, 77 have content.
10. NOTE. `HUMAN_LEAD_WORDS_11.md` says the gap in exact R1 rows "is filled from the recomputation's listing in the record". G-gen's record holds no such listing. If "the record" means G-gen's record, it is missing. PENDING LEAD REVIEW.
11. NOTE. The record could close two open notes: R-64 (no timeout; 0 solver disagreements in 616 cells) and the class table check (it is equal, see item 3).
12. NOTE (process). I read reason texts of past rounds in the fix-4 manifests and module tables only as strings to match, which this task requires. COMMON.md forbids consulting past figures for the fresh run. No figure influenced anything here.
13. NOTE (my own error). Early in the session one command wrote the addendum text to `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/adr_tmp_check_x`, outside my directory. It is a leftover, not deleted, per the rules. The other errors (attempt 1, the v2 parse) are listed above.

Astra review: NOT_PERFORMED
