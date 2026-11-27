# M0 partition: independent audit of the implementer's partition code (ADR-0033 addendum 1, section 4; section 4A stage 3)

**Verdict: AGREE — FIT TO COMPUTE** (engineering and mathematical agreement with the approved text at `2c944302`; no disagreement found in any case). One seed-free consequence of the rule on the real map is raised for the lead as **PENDING LEAD REVIEW** (section 7 below). It does not change the verdict on the code.

Auditor: `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`). I wrote none of the code I audited. This is independent engineering evidence. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`.

**Registered seed.** No partition code (mine or the implementer's) was run with seed 400004 on the real map or candidate list. I used 400004 only on the made-up identities of the text's vectors V1 to V8 and on the text's `a`..`h` list, which the text licenses (section 4 item 8). Every real-map run used other seeds; `compare_impls.py` asserts that 400004 is not among them. My CLI refuses 400004 unless an explicit flag is given; I never passed that flag.

Environment: macOS 27.2.1 (arm64), `uv 0.12.15`, `uv run --locked python` gives CPython 3.12.14. Run from the implementation worktree root `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` (branch `claude/m0-impl`, HEAD `09fe73bf`, registration files uncommitted), with `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1` unless stated otherwise. Standard library only. Every command ran under `timeout` of 500 s or less.

Inputs (SHA-256):
- implementer `studies/m0/registration/partition.py`: `4e43d280f60730ead54922be1a3687cca99468758d5a75417944cb6b58714d03` (matches the brief; it is also the code hash the implementer's CLI recorded at run time)
- `candidate_list.json`: `8dcc796c0dc8554fab52a5e3093f73c6f2838fe5b965e2b3743fea6291f8946a`
- `build_candidates.py`: `7d48d84e…fe9f`; `NOTES.md`: `c5c3b03a…c4cf`; `test_partition_vectors.py`: `dbca5950…d430`
- `studies/m0/manifests/map_of_record.json`: `1ba6ddd520dfe6514dfd282883ce4bc84660b7dca1abfefdac58285dcab5809c`
- `survivor_list_of_record.json`: `0b658145…be0d`; `stage2_conditions.json`: `81d454a2…3e55`; `docs/reviews/m0-fresh-run-2026-11-26/run/pooled/dropped.json`: `248ee3f0…b83b`
- approved text, from `git show 2c944302:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` (copy at `../work/addendum1_2c944302.md`): `154d16a0…923c`
- drafter's `partition_vector_rev4.py`: `3b28dbbb…527f`; its output `partition_vector_rev4.out.txt`: `c4fbae36…ec8d` (both equal the hashes the text gives)

## 1. ORDER.md (contents, verbatim)

```
# ORDER.md — order of work of the independent partition audit (M0, 2026-11-26)

Auditor: arbor-auditor context, model Claude Opus 5.5 (claude-opus-5-5). Not Astra review; not human approval.

Step 1 (from the text alone). Read: AGENTS.md; experiments/_scratch/m0_fr_briefs_20261126/COMMON.md;
the approved addendum `git -C .../m0-spec-push-20261126 show 2c944302:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md`
(copy saved as ../work/addendum1_2c944302.md, SHA-256 154d16a0597dc8b2d41179ded63a5da3e6e92aa4f7b414fefda1f93cd4d0923c),
sections 0, 3, 4, 4A (stages 2, 3), 13. To learn the input format I also read the top-level structure of
`studies/m0/manifests/map_of_record.json` (keys, counts, first entries; no partition computed).
Not opened before the hash below: studies/m0/registration/ (any file), partition_vector_rev*.py and their outputs,
partition_from_text_review3.py, partition_check4.py.

partition_audit.py, first version, written and saved:
  time   2026-11-26T16:54:35-0500
  SHA-256 fe9636827f010fcbe7cd9fbdde5982a0a05e0b07b4511e996e4a3a42c78927c8
  (frozen copy: ../work/partition_audit_v1.py, same hash)
```
ORDER.md SHA-256 when written (16:54:44 -0500, before step 2): `85140cf90e242f67ac63ad6ed176103d1279c6b2120a5d445045cba0c76d9324`. **`partition_audit.py` was never changed afterwards.** The delivered file is the first version (`fe963682…27c8`). I did not open `partition_from_text_review3.py` or `partition_check4.py` at any point.

Before step 2 I checked my code against the text's own worked example alone: `'400004|cluster-partition|cross'` gives 3111564968117111496, and `a`..`h` shuffles to `e,c,b,h,d,f,g,a`. Both match the text.

## 2. Vectors V1 to V8 (step 2)

Command: `uv run --locked python <deliver>/run_vectors.py <spec worktree>/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/partition_vector_rev4.out.txt` (output `run_vectors.out.txt`). The maps were copied from `partition_vector_rev4.py`. The expected values were **parsed** from its printed output (sections 1 to 3, the decided option only), not typed by hand.

- Derived integers for all five labels: 5 of 5 equal.
- V1 to V5: part A and the per-evaluation (N_e, A, B) equal. The rev4 output prints no part B or cross order for these vectors, so only those two facts were compared.
- V6, V7, V8: part A, part B, the shuffled order of the cross-evaluation groups, the clusters with no part, and the per-evaluation (N_e, A, B) are all equal.
- **Total differences: 0.** My code needed no change.
- The implementer's code on V1 to V8 (`vectors_both.py`, comparing every fact listed in section 3): 8 of 8 agree with mine.

## 3. Comparison of the two implementations (step 3)

Command: `uv run --locked python <deliver>/compare_impls.py studies/m0/registration/partition.py studies/m0/manifests/map_of_record.json studies/m0/registration/candidate_list.json 6000 <deliver>/compare_impls.out.json`. Both implementations were called in-process on identical inputs. The implementer's module was loaded from its file path.

Compared in every case:
- the derived integers (5 labels)
- the shuffled order of X and of every L_e
- the part of every candidate cluster
- the group of every candidate cluster
- per evaluation: N_e, ⌊N_e/2⌋, a_e, p, clusters in A and B, groups in A and B
- the step-2 cluster counts
- the group part printed beside every cluster with no candidate

| Set | Cases | Disagreements |
|---|---|---|
| Random made-up maps (generator seed 20261126; partition seeds drawn at random from [0, 10^6), [0, 2^63) and negatives, never 400004) | 6,000 | **0** |
| Real map of record + real candidate list, 200 distinct seeds in [1, 10^7), 400004 excluded (asserted) | 200 | **0** |
| V1 to V8 (made-up identities, seed 400004 as the text uses it) | 8 | **0** |
| Real map, both **CLIs** run end to end (seeds 7, 400003, 2026; outputs in `cli_runs/`) | 3 | **0** (cluster_part and derived integers equal; both CLIs report that the map's `clusters` and `groups` fields equal the ones recomputed from links and pairs) |

Coverage of the 6,000 random maps (cases with each feature; from `compare_impls.out.json`):

| Feature | Maps |
|---|---|
| group of more than one candidate cluster | 4,396 |
| group holding a cluster with no candidate (chaining) | 2,826 |
| cross-evaluation group spanning 3 or more evaluations | 3,958 |
| evaluation with 1 or 2 candidate clusters | 5,160 |
| group with w_e(g) > ⌊N_e/2⌋ | 5,215 |
| a_e > ⌊N_e/2⌋ (part A overfull from step 2) | 508 |
| step 2 ends with B < A | 413 |
| multi-lineage cluster | 4,709 |

Inputs also varied: shuffled input order, reversed and duplicate pairs, and ids mixing upper case, lower case, digits and `_`, which tests code-point ordering.

## 4. Candidate list (step 4)

Command: `uv run --locked python <deliver>/candidates_audit.py studies/m0/manifests/survivor_list_of_record.json studies/m0/manifests/stage2_conditions.json docs/reviews/m0-fresh-run-2026-11-26/run/pooled/dropped.json studies/m0/manifests/map_of_record.json studies/m0/registration/candidate_list.json <deliver>/candidates_audit.out.json`.

The rule I applied: a lineage is a candidate if it is on the survivor list (R1 10, R2 17, M1 29, C1 26), all four of these conditions hold, and the fresh run did not drop it.
- Each condition's own `result` was read: wording, levels_distinct, second_solver and pair_audited are each PASS, and `all_conditions` is PASS.
- The `map` condition was checked: the lineage is in the map, its recorded `cluster_id` equals the cluster recomputed from the links, and its `map_sha256` equals the map's hash.

Results:
- All 82 survivors pass every condition. No stage-2 entry falls outside the survivor list. There are no problems.
- 15 drops: R1 4, R2 1, M1 5, C1 5. Every drop is a survivor of the stated evaluation.
- Candidates: **R1 6, R2 16, M1 24, C1 21**. The ids are identical to `candidate_list.json` per evaluation; nothing appears only in mine or only in the implementer's list.
- Candidate clusters: R1 5, R2 15, M1 14, C1 17.

## 5. Reading of the implementer's `partition.py` (step 5)

- **How the seed and labels enter** (l.33–41): `"|".join([str(seed), "cluster-partition", label]).encode("utf-8")`, SHA-256, `digest()[:8]`, big-endian, then `random.Random(int)`. The labels are exactly `cross`, `R1`, `R2`, `M1`, `C1`. The exact strings hashed for the registered seed are `400004|cluster-partition|cross`, `400004|cluster-partition|R1`, `…|R2`, `…|M1` and `…|C1`, as in the text. A new stream is made for each `shuffled` call (l.157, l.195). The shuffle sorts the list, then calls `rng.shuffle` once (l.44–48). That is the text's loop: the implementer's own test checks it against an explicit `_randbelow` loop, and my code asserts the same at every call. Steps 2 and 3 walk in the order R1, R2, M1, C1 (l.26, l.190).
- **Dict and set ordering**:
  - `components` sorts its nodes, uses union-by-min, and keys each component by `min(v)` with sorted members, so the result does not depend on link order.
  - The borderline cluster pairs are normalised to (min, max), put in a set, then **sorted** (l.108–114).
  - `cand_evals` uses sorted lists.
  - X and L_e come from dict iteration, but they are passed through `sorted` before the shuffle.
  - `a_e` is a sum, so order does not matter.
  - `tied` and `group_of` are used only for membership tests.
  - The output is `json.dumps(sort_keys=True)`.

  Measured: on the real map with 6 non-registered seeds, 150 random permutations of lineage, link, pair and candidate order and of pair orientation per implementation gave **0 output changes** out of 300. Output hashes were identical under `PYTHONHASHSEED` = 0, 1, 12345 and random (`order_invariance.py`, `order_invariance.out.txt`).
- **Python version**:
  - The CLI stops on anything other than 3.12 (l.346).
  - `random.Random(int)` seeding (init_by_array of the absolute value's 32-bit words) and `shuffle` / `_randbelow` (getrandbits rejection) are not version-specific within 3.x. Only 3.12 was run.
  - `str` sort is code-point order.
- **Input order**: no dependence, as measured above. The candidate file's evaluation keys are iterated sorted. Duplicate candidates are refused. A candidate listed under the wrong evaluation is refused. The `evaluation` field must equal the id prefix.
- **Rule mapping**:
  - All clusters, with or without a candidate, are nodes of the group graph (item 17).
  - Group identity is the smallest candidate cluster (step 1).
  - w(g) = `len(groups[g])`, where `groups[g]` holds the candidate clusters only.
  - Step 2: `to_b = in_b <= in_a` (item 5 (iii), item 20).
  - Step 3: `fits = a_e + p + w_e <= half`, and the walk continues past a group that does not fit (item 20).
  - A non-candidate lineage enters neither w, w_e, N_e nor X.

  All of this matches the text.
- **Notes, not defects**:
  - (a) The "computed once" guard in the CLI only refuses an existing `--out` path. Once-only is a procedural matter for the lead (section 4 item 7).
  - (b) The CLI does not refuse seed 400004. That is correct, since the lead runs it with that seed.
  - (c) `test_partition_vectors.py` l.279–288 shuffles a made-up list of 23 ids on the five registered streams. Those identities are made up, so this is within the text's licence for vectors. Its only effect is to publish permutations of a 23-element list. The seed and code are public anyway: the protection is the hashing order, not secrecy.
  - (d) `run()` builds the structure twice, once for the partition and once for the map-consistency check. It runs the consistency check after `partition()` and stops (exit 3) before writing if the check fails. That is harmless.

## 6. Shape facts of the real case (seed-free) (step 6)

Command: `uv run --locked python <deliver>/shape_facts.py studies/m0/manifests/map_of_record.json studies/m0/registration/candidate_list.json <deliver>/shape_facts.out.json`. The structure was read with a dummy seed of 1; orders are not used.

The map holds 92 global clusters, **44 with a candidate lineage**, **14 groups with a candidate cluster**, of which **5 are cross-evaluation** (X):

| X group | w(g) | w_R1 | w_R2 | w_M1 | w_C1 |
|---|---|---|---|---|---|
| C1.bracket_matching | **29** | 4 | 8 | 8 | 13 |
| C1.merge_two_sorted | 2 | 0 | 1 | 1 | 1 |
| M1.fraction_remainder | 2 | 1 | 0 | 1 | 0 |
| C1.binary_search | 1 | 0 | 1 | 0 | 1 |
| C1.run_length_scan | 1 | 0 | 1 | 0 | 1 |

| Evaluation | N_e | ⌊N_e/2⌋ | groups with a candidate cluster in e (w_e) | L_e (local groups) |
|---|---|---|---|---|
| R1 | 5 | 2 | 4, 1 (both cross) | none |
| R2 | 15 | 7 | 8, then seven of 1 (three cross, four local) | 4 of 1 |
| M1 | 14 | 7 | 8, then six of 1 (two cross, four local) | 4 of 1 |
| C1 | 17 | 8 | 13, then four of 1 (three cross, one local) | 1 of 1 |

This **confirms the implementer's table** (R1 groups 1 and 4; R2 seven of 1 and one of 8; M1 six of 1 and one of 8; C1 four of 1 and one of 13; 44 candidate clusters; 14 groups, 5 cross-evaluation). The local groups total 0 + 4 + 4 + 1 = 9, and 9 + 5 = 14.

## 7. Possible part sizes per evaluation (a consequence of the rule alone)

I enumerated every one of the 5! = 120 orders of X, with every order of each L_e, under steps 2 and 3. This is the full set of outcomes any seed can produce. The fraction of orders giving each outcome is the probability **only under a uniformly random shuffle**; it is not a seed result.

Part sizes are given as A/B, in clusters:

| Evaluation | Possible A/B (share of orders) |
|---|---|
| R1 (N 5) | 0/5 (7/60), 1/4 (27/60), 4/1 (23/60), 5/0 (3/60) |
| R2 (N 15) | 5/10 (1/10), 6/9 (13/60), 7/8 (1/4), 8/7 (1/4), 9/6 (3/20), 10/5 (1/30) |
| M1 (N 14) | 5/9 (7/30), 6/8 (1/3), 8/6 (1/3), 9/5 (1/10). **7/7 is impossible** |
| C1 (N 17) | 2/15 (1/10), 3/14 (13/60), 4/13 (1/4), 13/4 (1/4), 14/3 (3/20), 15/2 (1/30) |

The 200 non-registered seeds on the real list produced exactly these sets of outcomes (tally in `compare_impls.out.json`), consistent with the enumeration.

Why, from the rule:
- **The group of 29 clusters (C1.bracket_matching) is larger than ⌊N_e/2⌋ in every evaluation** (4 > 2, 8 > 7, 8 > 7, 13 > 8). It is cross-evaluation, so it is placed in step 2, never in step 3. It goes to B when it is at index 0 of the cross order, or whenever B ≤ A at its turn, and otherwise to A.
- Under a uniform shuffle it goes to A in 26/60 of orders. When it is in A, step 3 can add nothing to A in R2, M1 or C1, because a_e already exceeds ⌊N_e/2⌋. Part A is then overfull (step 5), and the held-out part has the smaller share.
- R1 has no local groups, so step 2 alone decides R1.

**PENDING LEAD REVIEW (scientific, seed-free).**
- **R1 has a part of at most one cluster under every possible order.** Section 9 item 5 then gives NOT EVALUABLE (one cluster or none) for that part:
  - if the 29-cluster group is held out, R1 part A has 0 or 1 clusters;
  - if it is teaching-eligible, R1 part B has 1 or 0.
- C1 always has a part of 2 to 4 clusters.
- In 26/60 of orders (uniform shuffle) the teaching-eligible part A holds the larger share in R1, R2, M1 and C1 together.

These outcomes follow from the hashed map and candidate list under the decided rule. The text (section 4 step 5) says nothing is moved to repair them. Whether that is acceptable is the lead's question, not the auditor's. Nothing here changes the code verdict.

## 8. Discrepancies, mistakes and things to disclose

- No disagreement between my code and the text, the printed vectors, or the implementer's code. My code was not changed.
- **Disclosure.** When I first looked at `dropped.json` to learn its structure, my command printed the whole first record (`C1.circle_elimination_r2`), including its `all_rows_over_the_bound` and `reason` figures (excess values for rule `EFF_F`). My candidate rebuild reads only the `lineage` and `evaluation` fields. Those figures influenced nothing here, and I do not report or use them.
- Not done:
  - I did not run the implementer's pytest file. Its vector content is covered by `vectors_both.py`.
  - I did not compare versions of Python other than 3.12.
  - I did not compute the stage-4 vectors (4a and 4b), which are outside this brief.

## 9. Files (in this directory; hashes in `SHA256SUMS.txt`)

| File | What it is |
|---|---|
| `partition_audit.py` | My implementation. CLI: `--map --candidates --seed --out`, writing the part of every candidate cluster id, orders, integers and counts |
| `ORDER.md` | The order of work |
| `run_vectors.py`, `run_vectors.out.txt` | V1 to V8 against the drafter's printed output |
| `vectors_both.py`, `vectors_both.out.txt` | V1 to V8, my code against the implementer's |
| `compare_impls.py`, `compare_impls.out.json`, `compare_impls.out.txt` | The random-map and real-map comparisons |
| `order_invariance.py`, `order_invariance.out.txt` | Input-order and hash-seed invariance |
| `cli_runs/` | End-to-end CLI outputs for seeds 7, 400003 and 2026, with `cli_compare.out.txt` |
| `candidates_audit.py`, `candidates_audit.out.json`, `candidates_audit.out.txt` | The candidate-list rebuild |
| `shape_facts.py`, `shape_facts.out.json` | Seed-free shape facts and the enumeration of possible part sizes |

Under `../work/`: `addendum1_2c944302.md` (copy of the approved text) and `partition_audit_v1.py` (frozen first version, identical to the delivered file).
