# M0 R1, audit 3: independent re-audit of the R1 lineage set after fix round "rev 4"

Auditor: arbor-auditor context (Claude Opus 5.5), 2026-11-25. Independent engineering and mathematical evidence only.
**Not Astra validation, not human approval, nothing registered.** `Astra review: NOT_PERFORMED`.

Code audited: implementation worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f122e6bc`
(no file changed by me; one untracked leftover there that is not mine: `studies/m0/m1_rev2_gates.py.bak`).
I did not open `studies/m0/NOTES_LINEAGE_REPAIR.md`. I saw only the one-line subjects of commits `5cbd9200`, `476e6c24`,
`f328c279`, `9e32b317` and `f122e6bc` (from `git log --oneline`); no commit body was read.

**Where the files are.** The session's write hook refused every write into the implementation worktree ("belongs to a different
worktree"), so this report and every script are in the scratch directory
`/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit3_r1_20261125/` (reached through this session's worktree
symlink). They are meant to be copied unchanged to `docs/reviews/m0-lineage-decision-2026-11-25/audit3_r1/` by whoever commits.
That directory exists in the implementation worktree but is EMPTY (I created it with `mkdir -p` before the hook refused the
first write; leftover, not removed). Every script starts with `# ruff: noqa`.

Environment: macOS (Darwin 27.2.0), 18 cores; `uv run --locked` (the worktree's locked environment, Python from its `.venv`);
`PYTHONHASHSEED=0` unless stated. All commands run from the implementation worktree root, `S` = the scratch directory above.
Seeds: throwaway integers, none a registered study seed: `random.Random(B + level)` with B = 3100 (keys), 5200 / 5300
(shortcut battery / fitted constant), 7100 (capacity), 8100 (extra checks), 9100 and 9900 (capacity detail and exact counts),
7, 9, 11, 13 (looking at items).

## 0. The set under audit

`lineages_r1_clusters_v2.registered_v2()` = 43 shapes: 21 revision-4 shapes (`lineages_r1_rev4*.py`, ids `_r4`) and 22 kept
shapes (12 in `core.REGISTRY` via `lineages_r1.py`, 10 pilot or `_r2` shapes). Every other R1 shape on file (42) has its base id in
the set (each is superseded by a later revision; checked programmatically). No `_r5` exists. This matches
`r1_registration_plan.md` section 1. The pilot `_r2` shapes kept (`containers_queue_line_r2`, `equivalence_classes_r2`,
`spatial_grid_walk_r2`) live in `lineages_r1_rev2.py`, which imports the withdrawn redraw machinery, but these three builders do not
call `_anti` (source scan of every builder of the 43: no `_anti(`, `credit(`, `ANTI_P`, `anti_override`, `SPECIFIC`, `generic(`).
Ruling R-1 (no redraw on a heuristic's outcome) holds for all 43. Redraws that remain are on the ANSWER (balancing:
`conditional_chain`, `categories_follow_r4`, `order_compare_r4`, `graph_bipartite`, `kinship_cousins`, ...) or validity
(ties, uniqueness). One borderline design rule: `containers_stack_piles_r4` chooses the asked pile among piles whose last change
was a removal or a turn, so "the block last moved onto the asked pile" is never right at level 0 (0.000 vs chance 0.200; the
elimination reading gains +0.050 at L0, <= +0.011 after) — a question-design rule, not a fitted redraw.

## 1. Correctness, determinism, wording

`solvers3.py`: my own solvers, reading ONLY the rendered question text (never the structured form or the key), different
algorithms where possible (weighted-interval DP for meetings, Floyd-Warshall for routes, Prim for MST, brute force over all
matchings for stable matching, model enumeration over membership types for the syllogisms, Moebius inversion for Venn, Fractions
for exchange rates, deque rotation for Josephus).

Command: `PYTHONHASHSEED=0 uv run --locked python $S/check_keys.py 400 3100` and the same with `PYTHONHASHSEED=77`.
Result (`check_keys_run1_h0.txt`, `_h77.txt`): **43 shapes x 7 levels x 400 = 120,400 items, 0 key mismatches, 0 ambiguous
(no multiple solutions, no ties, no unreachable answers), 0 parse errors.** Both runs give the same SHA-256 over all (question, key)
pairs, `f4b98424a1d1e3a7be230afb805be766cd57dc4b0e38c9073d468e58a4967a68`: generation does not depend on the hash seed.
A first trial (`check_keys_try1.txt`, 60 per level) had 438 failures, all mine: two regex slips in my parsers (compass body,
"yo-yo"); fixed, kept.

Wording (ruling R-4: conventions stated in the item):
- **`temporal_critical_path_r4` — DEFECT.** "X's job takes 12 days and starts on day 0 ... Counting the start as day 0, on which
  day is the last of these jobs finished?" Under the inclusive-day reading (a 12-day job starting on day 0 works days 0-11, is
  finished on day 11, and a job waiting for it starts on day 12), the key is the stated key minus 1 in **7,000 of 7,000** items
  (`extra3.py`, part b). R1's own `temporal_interval_overlap` primes exactly that reading ("day 65 counts as the first"). The item
  must state which day a job of t days started on day d is finished on, and when a waiting job starts.
- tracking_accounts never lets a balance go below zero (0 of 7,000 items, inline check, seed base 13). Every other wording read correct and unambiguous for its key. Grammar only (no key effect): "1 units of", "1 voter rank them",
  "Exactly 1 of these 5 statements are true".

## 2. Strict clusters

`my_clusters3.py` (my map written from the generators; imports the v2 map only to compare). Output `my_clusters3_run1.txt`:
**my count 25 against the map's 27.** Two disagreements, both merges the map does not make (it lists neither as borderline):
1. `conditional_chain` joins `knights_knaves` / `one_culprit`: all three are "enumerate truth assignments, keep those consistent with
   the stated clauses, read the asked variable" (the clause form — speaker iff content, one-hot culprit with a true-count, material
   implications — is a parameter). `conditional_chain`'s generator itself decides its key by enumerating all 2^n assignments.
2. `elimination_bracket_r4` joins `attribute_rule` / `conditional_decision_tree_r4` / `minimax_tree_r4`: a knockout bracket is
   bottom-up evaluation of a complete binary tree whose operator is the head-to-head table; the map's own reason for merge (i) is
   that the operator / number system of a tree evaluation is a parameter (the pilot docstring itself calls the bracket "tree evaluation").
Consequence: under the tabulated `cluster_keys` split (`manifests/r1_rev4_parts.md`), my merged cluster
{conditional_chain (A), knights_knaves (B), one_culprit (B)} **spans both parts** (ruling R-6); the split must be redrawn on the final
map. All nine merge groups of the map I agree with; its 13 borderline pairs I leave unmerged too. PENDING LEAD REVIEW.

## 3. Shortcuts (two-sided, per level, my own battery)

`heuristics3.py` (text-level and structure-restating heuristics; 1,000 items per level, seed base 5200; the constant key fitted on a
separate draw, base 5300). "eff" = mean credit minus chance with items it does not fire on scored at chance; two-sided (the
"pick among the others" reading is scored too). Command: `PYTHONHASHSEED=0 uv run --locked python $S/heuristics3.py 1000 5200 5300`.
Tables: `heur_run1_all.txt` (every heuristic, every level), `heur_run1_summary.txt`, `heur_run2_summary.txt` (bracket and Josephus
rerun after my scoring slip, see section 7). Noise: SE about 0.016 per cell; the per-level maximum over a battery is biased up by a
few points. Rules that are an exact alternative algorithm or a convention slip of the full computation are NOT counted as shortcuts
(listed in section 7).

### 3a. The claimed residuals, recomputed

| shape | claim | mine (L0 ... L6) | verdict |
|---|---|---|---|
| topological_order_r4, layered sort (depth then name) | +0.55 to +0.68 | +0.69 +0.67 +0.61 +0.55 +0.51 +0.45 +0.46 | confirmed (lower at L5-6); also "sort by number of ancestors" +0.44..+0.68 and Kahn with listed-order tie-break up to +0.46 |
| stable_matching_r4, receivers' deferred acceptance | +0.51 | +0.47 +0.51 +0.50 +0.52 +0.52 +0.52 +0.53 | confirmed |
| instant_runoff_r4 | +0.38 | top-two runoff +0.39 +0.40 +0.35 +0.28 +0.29 +0.26 +0.20; one elimination then plurality +0.37..+0.40 (L0-5), +0.24 (L6); Borda <= +0.31; Condorcet +0.25..+0.29 | confirmed, up to +0.40 |
| minimax_tree_r4 L0, median leaf | +0.47 | median +0.55 at L0 (+0.32, +0.23, +0.19, +0.03, +0.27, +0.00) | larger than claimed; and NEW: greedy "mover takes the option with the best leaf beneath" +0.68 +0.49 +0.45 +0.36 +0.24 +0.27 +0.18 |
| elimination_bracket_r4 L5, beater in own half | +0.28 | +0.36 at L5 (beater of X in the other quarter of X's half), +0.12 at L6 | larger than claimed; NEW at L0-L2: best record inside each half +0.17 (champion / runner-up) |
| spatial_grid_walk_r2, ignore the walls | +0.57 | +0.66 +0.60 +0.55 +0.54 +0.53 +0.49 +0.46 | confirmed |

### 3b. New residuals >= about +0.15 (not in the plan's lists, or larger than listed)

Revision-4 shapes:
- **kinship_descendants_r4: "the candidate with the deepest line below them" +0.42 +0.48 +0.55 +0.58 +0.62 +0.63 +0.67** (construction
  puts every surplus descendant in one line below one grandchild, so the most descendants is almost always the longest line).
- **spatial_relative_directions_r4 (open number): sum of the leg lengths on the path, ignoring direction, +0.65 ... +0.42.**
- **temporal_critical_path_r4 (open number): greedy backward walk (from each job nobody waits for, follow the longest predecessor)
  +0.86 +0.81 +0.79 +0.76 +0.73 +0.73 +0.69.**
- **order_compare_r4: two-step search ("x > z > y") else "cannot be determined" +0.64 ... +0.60** (accuracy 0.93-0.98: depth beyond
  two almost never matters).
- **categories_follow_r4: premises read without lifting "No" through "All" (direct No / direct Some / All-reachability only)
  +0.45 +0.41 +0.38 +0.40 +0.38 +0.38 +0.41** (the plan lists only +0.063).
- **activity_selection_r4 (open number): round(2n/3) of the number of meetings +0.46 +0.33 +0.34 +0.31 +0.30 +0.30 +0.25**; the fitted
  constant key +0.16..+0.29.
- **nim_xor_r4: parity of bit 1 of the piles alone +0.30 ... +0.23** (`extra3.py` d: accuracy 0.73-0.77); bit 1 or bit 2 +0.38..+0.41.
- mst_cost_r4: nearest-neighbour path from the first town +0.17..+0.19 at L0-L2 (fires about half the items).
- containers_stack_piles_r4: simulate ignoring the turns +0.21 ... +0.11 (L1-L6; L0 has no turns); initial bottom <= +0.09.
- Small (<= +0.13): boolean_lights_r4 +0.10 (L0), graph_shortest_route_r4 +0.13 (L0-1), kinship_ancestor_r4 +0.07,
  categories_default_exceptions_r4 +0.08, conditional_decision_tree_r4 +0.11, venn_counting_r4 +0.07, conditional_threshold_rule_r4
  none above +0.05 (its +0.25 for "more than" instead of "at least" is a misreading of the full computation).

Kept (unchanged) shapes:
- **conditional_chain: the asked variable is stated as a fact in 37-49 % of items** (`verbatim3.py`; `verbatim_run1.txt` from the inline first run, `verbatim_run2.txt` from the script, identical); "copy the fact, else
  cannot be determined" +0.54 +0.50 +0.45 +0.44 +0.44 +0.42 +0.40.
- **pet_owners: the asked pet's owner is stated verbatim in 23-46 % of items**; +0.15 ... +0.38. **seating_row: the asked seat is stated
  in 16-24 %**; +0.11 ... +0.19.
- **attribute_rule: the badge that matches most of the rule's attribute tests +0.75 +0.80 +0.58 +0.59 +0.41 +0.43 +0.32**; "matches
  the last test" +0.44..+0.50 at L4-L6 (at L0-L1 the rule is flat and counting matches is the evaluation).
- **graph_bipartite: "a triangle means no" +0.50 ... +0.40** (accuracy 0.90-1.00); "rivals >= people means no" +0.34 (L0).
- **kinship_cousins: "same family means yes" (or "share a grandparent", ignoring the different-parents clause) +0.41..+0.45.**
- **event_timeline: the event at the far end of the largest stated gap +0.48 ... +0.40.**
- **temporal_interval_overlap: "the starts are within 20 days" +0.39..+0.42.**
- tracking_accounts: simulate ignoring the earnings +0.50..+0.57; ignoring the halves +0.40..+0.47.
- temporal_weekday_shift: ignore before / after +0.42 ... +0.24. equivalence_exchange_rates: the item no direct comparison beats
  +0.49 ... +0.20. road_reachability: within two roads +0.32..+0.40; "the start has two or more outgoing roads means yes" +0.31..+0.35.
- knights_knaves: "a speaker who accuses someone is a knight" +0.20..+0.33. order_tournament_wins: tally of half the results +0.29..+0.40.
- Confirmed from the plan: containers_queue_line_r2 ignore "leave" +0.48 (L0) ... +0.22; equivalence_classes_r2 common neighbour
  +0.21..+0.29; order_extreme least mentioned +0.17..+0.39; one_culprit most accused +0.07..+0.19; elimination_josephus first
  mentioned +0.18 at L5, first-pass index +0.13..+0.18; swap_tracking ignore the three-way hand-overs +0.17..+0.21 (L0-L3).

Whether an approximate procedure (ignore a constraint, a shallower search, a different rule that usually agrees) counts as a shortcut
is the shortcut-bound question; it is the lead's. PENDING LEAD REVIEW. Cheap single-feature tells, which no reading of "procedure"
covers: conditional_chain (answer stated), pet_owners and seating_row (answer stated), kinship_descendants_r4 (deepest line),
event_timeline (largest gap), temporal_interval_overlap (start gap), graph_bipartite (triangle), activity_selection_r4 (2n/3),
road_reachability (out-degree), kinship_cousins (same family), attribute_rule (match count).

## 4. Capacity

Formula. ADR-0033 6.2: "for every cluster and level, the number of distinct items the generator can produce is at least 10 times the
number the pools demand". Section 8: development pool 4,000 + sealed pool 20,000 per part, spread over the part's G clusters; tuning
100 per level and part. A level mix chosen by 6.5 may be a single level, so a cluster's worst case on one level is ceil(24,000/G)
+ 100 (the 100 counts the whole tuning draw against one cluster, an upper bound), times 10: **10 x (ceil(24,000/G) + 100), as in R-5
and the plan.** G = 13 gives 19,470; G = 14 18,150; G = 12 (my 25-cluster map) 21,000. **I read the reserve levels differently:**
6.5 third bullet — when no range is interior "the two reserve levels are scored once and the rule is applied again" — so a chosen
range can include level 0 or 6 and the 24,000 pool items can be drawn there. The worst case at a reserve level is then the core
figure, not 1,000. PENDING LEAD REVIEW. A second reading point: the plan (section 2.4) spreads a cluster's items EVENLY over its
shapes, so each shape must carry requirement / m on its own; the plan's "cluster sum" is valid only if allocation follows capacity.

Method: `capacity3.py` (an isomorphism-invariant key: names erased and refined by Weisfeiler-Lehman over the sentences, paraphrases
normalised, sentence order ignored except for operation sequences), collision estimates from 2,000-3,000 draws per cell
(`capacity_run1*.jsonl`, `capacity_run2_*.jsonl`, `cap_summary_G13_v2.txt`, `cap_summary_G12_mine.txt`), larger draws with Chao1 on short
cells (`cap_detail_*.jsonl`, N = 20,000), and EXACT counts where it decides (`exact_small_run1.txt`). My first key was NOT invariant
for symmetric phrasings ("A and B are rivals", "A and B swap", two-way roads, "either the X or the Y"): it over-counted those shapes.
Fixed as `AUDIT3_SYM=1` mode and re-run (`capacity_run3sym_*.jsonl`); the decisive failures below rest on exact counts.

Definite failures (exact or theoretical upper bounds):
- **graph_bipartite (single-shape cluster): L0 <= 11 graphs (5 seen), L1 <= 34 (16 seen), L2 <= 156 (58 seen), L3 <= 1,044
  (231 seen), L4 <= 12,346** (non-isomorphic graphs on n = level + 4 vertices; the key is a function of the graph). Fails L0 even at
  1,000 and L1-L4 at 19,470. The plan lists only L0-L2 (its counts 110 / 1,614 / 16,473 exceed the number of graphs on 4-6 vertices,
  so its key is not name-free).
- **swap_tracking (single-shape cluster): L0 13 structures, L1 6,416** (complete enumeration of every operation sequence and asked
  person the generator can emit, orbits under renaming). Fails L0 (1,000) and L1 (19,470). **Not in the plan's list.**
- **pet_owners cluster (pet_owners + seating_row) L0: 329 + 420 = 749 exact structures seen in 20,000 draws each, near saturation**
  (Chao1 on my symmetric-mode key about 330 and 409): below 1,000. Not in the plan's list as a cluster failure. L1: 7,840 + 7,167 seen,
  not saturated: undetermined.
- Shapes far below an even share (requirement / m): order_extreme 2 per level; elimination_josephus 16 (L0) to 40 (L6);
  order_tournament_wins 4 / 14 / 14 / 68 / 68 / 524 / 524 (my L0, L2, L4, L6 exact: 4, 14, 68, 524); kinship_cousins 219 (L0),
  715 (L2), 1,687 (L4), saturated; knights_knaves 32 (L0), about 5,200 (L1, L2). Their clusters pass only on the cluster-sum reading.
- containers_queue_line cluster: L0 passes 1,000 (queue_line_r2 Chao1 3,136 + Josephus 16) but fails at 19,470 under my reserve
  reading; L1 I count 13,546 distinct structures seen in 20,000 draws (Chao1 40,057), against the plan's 2,065 exhibited: the plan's
  key looks coarser than structure here. I do not confirm the plan's L1-L3 failure; L1 is undetermined on my evidence.
- Under my reserve reading only (L0/L6 at the core figure): categories_follow cluster L0, kinship_descendants_r4 L0 (Chao1 21,795, borderline),
  stable_matching_r4 L0 (Chao1 13,127), venn_counting_r4 L0 (Chao1 11,107 on the over-counting key), temporal_weekday_shift L0 (exactly
  7 x 600 = 4,200, below an even share of 4,868).

Symmetric-mode re-run (`cap_summary_G13_v2_sym.txt`, `cap_summary_G12_mine_sym.txt`; S_lo is a conservative effective-support figure,
1/sum p^2, NOT the support, so a low S_lo alone does not prove a failure): graph_bipartite S_lo 4 / 10 / 24 / 61 / 189 / 565 / 1,776
(L0-L6: L5 and L6 likely fail too, support not bounded); pet_owners + seating_row L1 3,198 (likely fail, not proven);
equivalence_classes_r2 96 / 307 / 2,010 at L0-L2 against an even share of 250 / 4,868 / 4,868; knights_knaves 18 / 2,088 / 2,159 at
L0-L2. Under my 25-cluster map (G = 12, 21,000) the same cells fail and none is added.

## 5. The three gate-bug fixes in `lineages_r1_shortcuts.py`

`gate_fix_check.py` runs every test in `tests/test_m0_r1_rev4_gates.py` against the current gate and against the gate text of
`9e32b317` (identical to `476e6c24`; `git diff` empty) substituted in `sys.modules`. Output `gate_fix_check_run1.txt`: current 7/7
pass; old: **6 fail** (possessive credit, possessive mention counts, longest-job reading, stated-pair direction, signed numbers, per-level
rows) and the symmetric-relation test passes on both (as it should). The three fixes are real and the tests discriminate.
Residual gate issues (not fixed, measured): `numbers()` still counts "one of the 2 options shown" in minimax as data ("options" is not a
structure noun: `[2, 8, 5, 5, 7]` for a 2-option item); `categories_follow_r4` has no "?" so `generic()` returns no yes/no heuristic
for it at all (empty dict, checked); for "No"/"Some" premises stated in the reverse order `_stated_reading` returns None.

## 6. Tests

`uv run --locked pytest tests/test_m0_*.py -q -p no:cacheprovider` (I added `-p no:cacheprovider` so that no cache is written into the
worktree), run once while three other auditors ran the same suite: **522 passed, 2 xfailed, 1 warning in 937 s** (the expected counts; the warning is torch's "Failed to initialize NumPy"). Output tail: `pytest_run1_tail.txt`. Passing tests do not cover the findings above (no test checks the cheap tells, the swap / graph capacity, or the critical-path wording).

## 7. Per-lineage verdict

R = REGISTRABLE AS IS; F = NEEDS FIX; N = SHOULD NOT BE REGISTERED (as the set stands); Residual = registrable only if the lead's shortcut bound admits it. "Residual" = an approximate-procedure residual
>= +0.3 left to the lead's shortcut bound (not counted as a fix here).

| shape | verdict | reason |
|---|---|---|
| activity_selection_r4 | F | round(2n/3) of the meeting count +0.25..+0.46; answer concentrated (fitted constant +0.16..+0.29) |
| attribute_rule | F | most matched attribute tests +0.32..+0.80; last test +0.44..+0.50 (L4-6); L0-1 rules are flat |
| boolean_lights_r4 | R | <= +0.10 |
| categories_default_exceptions_r4 | R | <= +0.08 (prefix walks excluded) |
| categories_follow_r4 | Residual | no-lifting reading +0.38..+0.45; capacity L0 only fails under my reserve reading |
| compass_turns | R | only misreadings of one command |
| conditional_chain | F | the asked variable is a stated fact in 37-49 % (+0.40..+0.54); cluster: merges with knights_knaves (mine) |
| conditional_decision_tree_r4 | R | <= +0.11 (partial walks excluded) |
| conditional_threshold_rule_r4 | R | no cheap rule above +0.05 |
| containers_queue_line_r2 | Residual | ignore "leave" +0.22..+0.48; capacity L1 undetermined (my 13,546 seen vs plan 2,065) |
| containers_stack_piles_r4 | R | ignore turns <= +0.21 |
| elimination_bracket_r4 | Residual | +0.36 at L5, +0.17 at L0-2; cluster: merges with attribute_rule (mine) |
| elimination_josephus | N | 16 to 40 structures per level: cannot carry an even share (>= 500 / 9,735) at any level |
| equivalence_classes_r2 | Residual | common neighbour +0.21..+0.29; capacity below an even share at L0-L2 (estimates 96 / 307 / 2,010) |
| equivalence_exchange_rates | Residual | local maximum +0.20..+0.49 |
| event_timeline | F | far end of the largest stated gap +0.40..+0.48 |
| graph_bipartite | N | capacity fails L0-L4 by the count of graphs (<= 11 / 34 / 156 / 1,044 / 12,346); triangle rule +0.40..+0.50 |
| graph_shortest_route_r4 | R | <= +0.13 |
| instant_runoff_r4 | Residual | other voting rules agree, up to +0.40 |
| kinship_ancestor_r4 | R | <= +0.07 |
| kinship_cousins | F | same family +0.41..+0.45; 219-1,687 structures, far below an even share |
| kinship_descendants_r4 | F | deepest line +0.42..+0.67 (construction); capacity L1 effective support 10,995 (not decisive) |
| knights_knaves | F | "an accuser is a knight" +0.20..+0.33; 32 structures at L0, about 5,200 at L1-2 (below an even share) |
| minimax_tree_r4 | Residual | greedy best leaf +0.68 (L0) ... +0.18; median +0.55 (L0) |
| mst_cost_r4 | R | <= +0.19 (L0-2, fires on half) |
| nim_xor_r4 | Residual | parity of bit 1 alone +0.23..+0.30 (a partial run of the xor) |
| one_culprit | R | most accused <= +0.19 |
| order_compare_r4 | F | two-step search +0.60..+0.64 at every level: depth is not controlled by level |
| order_extreme | N | 2 structures per level; least mentioned +0.17..+0.39 |
| order_tournament_wins | N | 4 to 524 structures per level (exact): cannot carry an even share |
| pet_owners | F | the asked owner stated verbatim in 23-46 %; cluster L0 749 structures seen < 1,000 |
| road_reachability | F | "two or more outgoing roads means yes" +0.31..+0.35; within two roads +0.32..+0.40 |
| seating_row | F | the asked seat stated in 16-24 %; cluster L0 capacity as pet_owners |
| spatial_grid_walk_r2 | Residual | ignore walls +0.46..+0.66 |
| spatial_relative_directions_r4 | F | unsigned sum of the legs on the path +0.42..+0.65 (open number) |
| stable_matching_r4 | Residual | receivers' deferred acceptance +0.47..+0.53 |
| swap_tracking | N | exact: 13 structures at L0, 6,416 at L1 (< 1,000 / 19,470) |
| temporal_critical_path_r4 | F | wording: key changes by one in 7,000 / 7,000 under the inclusive-day reading; greedy backward walk +0.69..+0.86 |
| temporal_interval_overlap | F | starts within 20 days +0.39..+0.42 |
| temporal_weekday_shift | Residual | ignore before / after +0.24..+0.42 |
| topological_order_r4 | Residual | layered sort +0.45..+0.69 |
| tracking_accounts | Residual | ignore the earnings +0.50..+0.57 |
| venn_counting_r4 | R | <= +0.07; capacity L0 only under my reserve reading |

Resulting cluster count: the map's 27 / my 25 for the 43 shapes. Tally: R 11, Residual 13, F 14, N 5. If the five N shapes are removed, graph_bipartite and swap_tracking take their singleton clusters with them: 25 clusters on the map, 23 on mine (josephus, order_extreme and order_tournament_wins leave clusters that keep other members).

## 8. My slips and failed attempts (kept)

1. `check_keys_try1.txt`: 438 failures from two regex slips in my own parsers (compass body, "yo-yo"); fixed.
2. Battery run 1 scored a heuristic absent from an item's dictionary as not scored instead of "not fired" (scored at chance): effective
   gains for bracket and Josephus were per-question-type, overstated (e.g. bracket L6 +0.37 instead of +0.12). Fixed; rerun
   `heur_run2_*.json`.
3. Several of my "naive" heuristics are exact at some levels and are not shortcuts: latest-start-first greedy (an exact algorithm for
   meetings), drop-negation and most-matches at L0-L1 of attribute_rule (flat rules), Venn formulas at the levels where they are the
   formula, ignore-turns at L0 of the stack piles, "more than" / off-by-one readings of the threshold, inclusive-day of intervals,
   partial walks that are prefixes of the true procedure (default exceptions, decision tree). Excluded.
4. The "pick among the others" score of knights_knaves at L0 used the people list as options (wrong): its anti column at L0 is invalid; the
   opposite-rule gain there is +0.33 (from eff -0.33).
5. Capacity key v1 over-counted shapes with symmetric phrasing (section 4); replaced by exact counts and the symmetric mode.
6. `capacity_run1.jsonl` (N = 3,000, single process): I reported it as stopped at its limit after 51 rows; that was wrong, it was
   still running and finished all 301 rows (exit 0) after the report was drafted. Its first 21 rows were used; the rest had been re-run
   in parallel at N = 2,000. Re-reading the full run with the symmetric-mode rows (`cap_summary_G13_v2_run1full_sym.txt`) gives the same
   failing cells as `cap_summary_G13_v2_sym.txt`; only the estimates move (e.g. kinship_descendants_r4 L0 9,180 vs 8,181, stable_matching_r4 L0
   8,054 vs 7,684), i.e. sampling noise of up to about 12 %. An `xargs -I` launch failed ("command line cannot be assembled, too long");
   nothing written.

## 9. Not verified

Second solvers from a separate context (none exist). Capacity of the shapes with symmetric phrasing at their larger levels beyond the
symmetric-mode collision estimate (no exact count above L3 for graphs, above L1 for swaps). Whether any rule in section 3 is "a shortcut"
for the gate (the lead's). Cross-evaluation duplicates (R-7). The partition on the final map. Readability of the long items for a model.
No model was run; nothing was trained, downloaded or registered.

Leftovers (not removed): this scratch directory (all files listed above, plus `old_shortcuts_9e32b317.py`, `samples_level2.txt`,
`cap_list*.txt`, `capacity_run1.err`, `heur_try1.*`, `cap_detail_sym_check1.txt`), and the empty directory
`docs/reviews/m0-lineage-decision-2026-11-25/audit3_r1/` in the implementation worktree.

Astra review: NOT_PERFORMED
