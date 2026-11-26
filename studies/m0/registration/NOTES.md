# Notes on partition.py, build_candidates.py and the tests (implementer self-check; not review)

Text: ADR-0033 addendum 1 at commit 2c944302. Line numbers are those of `partition.py` as delivered
(SHA-256 in the final message). "Measured" below means computed by the code just now.

## Section 4 and 4A mapped to code

| Sentence of the text | Where |
|---|---|
| Section 4 bullet 1: `stream(seed, l1..lk)`, join with `\|`, UTF-8, SHA-256, first 8 bytes big-endian, `random.Random` | `derive` l.33, `stream` l.39 |
| Bullet 2: labels `cluster-partition` + `cross`/`R1`/`R2`/`M1`/`C1` | `LABEL` l.27, used in `step2` l.153 and `step3` l.187 |
| Bullet 3: shuffle = sort by code point, then one `shuffle`, fresh stream per call | `shuffled` l.44 |
| Bullet 4 and section 3 item 1: ids `<eval>.<name>`; cluster id = smallest id (code-point order); clusters are components over ALL written lineages | `components` l.51; `build_structure` l.78 (clusters, `where`) |
| Section 3 item 2 (transitive merging) | the same: a cluster is a component of the link graph, whatever the evaluations |
| Step 1: groups = components of the graph whose nodes are all global clusters and whose links are borderline pairs between two different clusters | `build_structure`: pairs l.112, `raw_groups` l.116 |
| Step 1 (item 17): a cluster with no candidate lineage is a node and passes a group on, takes no part | nodes = all clusters l.116; `has_candidate` l.107 |
| Step 1: only groups with at least one candidate cluster are assigned; identity = smallest identity among clusters with a candidate | l.125 |
| Step 1: w(g), w_e(g); X; L_e; a non-candidate lineage does not make a group cross-evaluation and is not counted | `cand_evals` (candidate lineages only) in `build_structure`; `w_e` l.145; X in `step2`; L_e in `step3` |
| Step 2: shuffle X on `cross`, walk from index 0, to B if B holds no more clusters than A, else A, counting w(g) | `step2` l.153 (`to_b` l.163) |
| Step 3: per evaluation R1, R2, M1, C1; N_e in clusters; a_e = sum of w_e(g) over X-groups in A; L_e shuffled on the evaluation's label; A if a_e + p + w_e(g) <= floor(N_e/2), else B, walk continues | `step3` l.187 (`fits` l.201) |
| Step 4: every cluster with a candidate takes its group's part; a cluster with no candidate has no part, its group's part is printed beside it | `partition` l.224 (`cluster_part` l.241, `no_candidate` l.247) |
| Step 5: the counts in clusters and in groups are printed, nothing is moved | `counts` in `partition` (N_e, clusters/groups A and B, group sizes, a_e, p, orders, traces) |
| 4A stage 3: once, on groups with a candidate; needs both hashes first | the lead's procedure; the CLI refuses to overwrite an existing `--out` (a second run into the same file stops) |
| 4A stage 2: candidates = survivors with `all_conditions` PASS, less the fresh run's drops | `build_candidates.build` |

## Places the text left a choice

None in the rules. Choices of form only, none of which can change a part:

1. **Output format.** The text asks for what is printed, not its layout. JSON, `sort_keys`, indent 1,
   ASCII, trailing newline. Group identities are as the text defines them (smallest candidate cluster id).
2. **"The part of their group beside" a cluster with no candidate.** Printed for every such cluster, with a
   flag whether any borderline pair ties it, the group identity (null if the group has no candidate cluster)
   and the part (null in that case). Untied clusters with no candidate have part null.
3. **Counts "in groups" per evaluation.** I count the groups with at least one candidate cluster in e
   (`w_e > 0`) by part. A cross-evaluation group counts in each evaluation it has a candidate cluster in.
4. **Map consistency.** The CLI recomputes clusters and groups from the map's lineages, links and borderline
   pairs (the partition never reads the map's `clusters`/`groups` fields) and stops (exit 3) if they differ
   from the map's own fields. Measured on the map of record: both equal.
5. **Evaluation of a lineage** is the map's `evaluation` field; the CLI stops if it disagrees with the id
   prefix or if a candidate is listed under another evaluation.
6. **CPython 3.12 only**: the CLI stops on another minor version (the text names 3.12).
7. **Candidate file** carries the evaluation of each id; `partition.py` reads only the union of the ids.

## Disagreements between the text and the vectors or scripts

- **Where the maps of V1 to V8 are.** The text gives the vectors' results and names the scripts; the maps
  themselves are only in `partition_vector_rev4.py` (and V1 to V5 in `..._rev3.py`). The tests copy them.
  The text and the script agree on every figure compared (derived integers, the shuffle a..h = e,c,b,h,d,f,g,a,
  V8 figures 3 / 1 / 4 of 6, V7 2/2 against 1/3, V6 and V7 under "ignore").
- **Step 1 wording against the script.** The text says the group identity is the smallest identity among its
  clusters that have a candidate lineage; the script does the same. (The text's remark that draft 3 used the
  smallest in the group concerns the option not taken only.) No difference.
- **Step 2 counts w(g) over all evaluations** (clusters with a candidate lineage); the script's `len(groups[g])`
  is the same.
- No disagreement found. Not compared: section 4A stage 4 vectors (`4a`, `4b`), outside this brief.
- **The rev4 out file prints no V1 to V5 order of the cross groups**, so for those the tests compare parts and
  counts only; the order is compared for V6 to V8.

## What was run (all measured, standard library only)

- `build_candidates.py` on the real inputs: R1 6, R2 16, M1 24, C1 21 (67); 15 dropped, all PASS survivors.
- Tests: 24 passed, including every option the out file lists. The registered seed 400004 is used only on
  the made-up vectors; the property tests use per-map seeds from a fixed generator and the demo seed 123456789.
- The partition of record was not computed. No file in this directory is a partition of the real list.
