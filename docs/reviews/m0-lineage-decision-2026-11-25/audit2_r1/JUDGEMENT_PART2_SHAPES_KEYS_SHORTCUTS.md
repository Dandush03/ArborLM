# Judgement part 2 (revised shapes, keys, shortcuts), written before reading NOTES_LINEAGE_REPAIR.md (beyond the 3 lines
# logged in PROCESS_LOG.md), manifest free-text notes, r1_two_sided_table.md or similarity docstrings

Auditor: Opus 5.5 (claude-opus-5-5). Astra review: NOT_PERFORMED. Not human approval.
Evidence: render_run1.txt (500 items x levels 0-6 per lineage, auditor seeds, registered "reg" and redraw-disabled "unc"),
text_solvers_run2.txt / text_solvers_unc_run1.txt, heuristics_reg_run2.txt / heuristics_unc_run1.txt, distortion_run1.txt,
defect_checks_run1.txt.

## Keys (task 4)
Independent text-only solvers (different algorithms where practical): 20 lineages x 3,500 reg items = 70,000 and 10 x 3,500
unc = 35,000: 0 mismatches (attempt 2). Attempt 1 failed by my regex bug (3,500 false mismatches on threshold_r3; kept).
No wrong key, no tie, no unstable matching, no IRV tie, no inconsistent venn counts. Hand solves: stable_matching_r2
L2/0 (Sean), L4/0 (Tom), L0/0 (Esme); topological L2/0 (Nell); IRV L2/0 (Zed); minimax L2/0 (1); venn L2/0 (2); mst L2/0 (33);
nim L2/0 (first); activity L2/0 (6): all match.
Stated-convention dependence (not ambiguity): activity touching rule decides 2,015/3,500 reg (1,589/3,500 unc);
categories_follow_r2 empty-group convention decides 153/3,500.
AMBIGUITY (frame): categories_follow_r2 asks "Does it follow that ...? Answer yes, no or cannot be determined" without
defining "no" (the key uses no = the negation follows). Read literally ("no, it does not follow"), every cbd key (1,394/3,500)
would be "no". Same frame as the original shape. Wording hazard: boolean_lights_r2 "every other lamp is off" (3,374/3,500)
can be read as "alternate lamps".

## Revised shapes: original defect gone? new defects?
- spatial_grid_walk_r2: column convention stated 3,500/3,500. GONE. Residual: start_cell +0.076 (honest random-walk return).
- kinship_descendants_r3: root no longer an option (0/3,500). GONE. NEW: answer is a child of the root 86-100% by level;
  "parent of the person with most children" fires 1,775/3,500 with 0.863 (unc 798 fires); "root's child with most children"
  0.660 vs chance 0.157. Redraw on most_children moved mass to correlated tells.
- kinship_ancestor_r3: most_mentioned 0.237 -> 0.102 (chance 0.104). Design: root is never the answer (0/3,500, by extra>=1
  generations) - an elimination created by the r2 shape; parent never (honest, k>=2); leaves never (honest).
- equivalence_classes_r2: verbatim 0/3,500, unmentioned 0/3,500. GONE. Residual: common 'same' neighbour -> yes else cbd
  0.588 vs 0.333 (approximate procedure). Keys skew to "no" 37.7%.
- elimination_bracket_r3: ratings removed (0/3,500). GONE. NEW/STRENGTHENED: "Who knocks X out?" -> X's round-1 neighbour
  0.693 vs chance 0.195 (unc 0.613); the redraw pushed knockouts into round 1. most_wins_logic 0.181 (slightly below chance).
- containers_queue_line_r2: last-joiner shortcut gone (question changed). No strong cheap tell (last cut at j=1: 0.33 vs
  0.13). The front-to-back op (3,232/3,500 items) makes it the Josephus procedure (strict merge).
- categories_default_exceptions_r3: all-agree and own-group cases gone (0/3,500). NEW SEVERE: exactly 5 rules about the asked
  verb, none on the member's group, and at levels 0-1 (c=6) every chain[1..5] group has one, so the rule on the group named
  in the FIRST sentence is the answer: fires 100% at L0-L1, 61-84% at L2-L6, correct 100% when it fires (2,853/3,500).
  Also second-most-specific rule anti-informative 0.325 (by the n_mid_want in {0,2} design).
- conditional_threshold_rule_r3: veto gone, keys balanced. NEW: margin alone (d <= 0 -> yes) 0.771 overall, 0.958 L0,
  0.922 L1 (unc 0.633); heaviest voter's vote 0.816 when it fires; author's yes_count_majority is ANTI-informative at L0
  (-0.22) and L1 (-0.17) and positive at L2-L6 (+0.03..+0.09): one pooled fitted probability miscalibrates per level.
- boolean_lights_r2: never-toggled gone (0/3,500). NEW: "flip the initial state" 0.68 at L0, 0.58 L1 (asked lamp is toggled
  exactly once in 31% of L0 items).
- graph_shortest_route_r2: first-hop greedy question replaced by distance. Shallow: the shortest route has 2 roads in 58-77% of
  items per level; best route within 2 roads 0.841 when it fires.
- containers_stack_piles_r3: colour-word blocks 0/3,500. GONE. Redraw: last_onto 0.595 -> 0.169; NEW initial bottom of the
  asked pile 0.199 -> 0.295.
- categories_follow_r2: verbatim pairs excluded. NEW two-sided: when x and y share any sentence the key is never "yes"
  (693 items, 0.000). Kind restricts the key to 2 options (some: no/cbd; all, none: yes/cbd), so chance is 1/2 not 1/3.
  Frame ambiguity above.
- topological_order_r2: jth_alphabetical 0.292 -> 0.161 (chance). No new strong tell; layer-by-depth approximation 0.564.
- instant_runoff_r2: plurality 0.795 -> 0.294 (chance 0.279) but per level L0 +0.18, L3-L6 -0.03..-0.05. The redraw changes
  the construct: "plurality leader wins" falls from 93% to 52% (L0) and 65% to 15% (L6). top-two runoff = IRV exactly at
  3 candidates (L0-L2).
- stable_matching_r2: first_choice 0.572 -> 0.245. NEW: asker's second choice 0.264 -> 0.456; first-mentioned receiver
  0.255 -> 0.148 (below chance, z -13.7). The extra first_mentioned redraw in rev3 has probability 0.0 (no-op).

General judgement on redraw-by-heuristic: it removes the targeted heuristic on the pooled sample but (a) relocates
accuracy to correlated heuristics (second choice, parent of hub, margin only, initial bottom, round-1 neighbour, each town's
cheapest road 0.455 -> 0.537), (b) leaves per-level two-sided miscalibration because one probability is fitted over pooled
levels, (c) changes the construct (IRV comeback items, stable-matching partner rank 1.48 -> 1.88 at L0, threshold items
pulled toward the threshold). It is a distortion that must be registered as part of each lineage's definition if kept.

## New 8 (non-revised) design
- activity_selection: shortest-duration-first greedy (a wrong algorithm) 0.927; redraw makes greedy-by-start 0.278 vs modal
  0.387 (below baseline at L1-L6).
- mst_cost: sum of each town's cheapest road (Boruvka first phase) 0.537 overall, 0.93 at L0.
- nim_xor: honest partial rule (largest > rest -> first) 0.635; capacity: only 270 distinct ordered 'second' tuples at L0
  (426 L1, 678 L2); my sample of 247 L0 'second' items had 161 distinct.
- minimax_tree: levels L0=L1=L2 (depth 2), L3=L4, L5=L6 are identical generators. Depth-2 answer is the 2nd-smallest leaf
  about 2/3 of the time (median-low 0.59-0.64 above baseline at L0-L2); smallest/largest leaf almost never (math).
- venn_counting: levels differ only in number ranges (g=2 at L0-L1, g=3 at L2-L6). Constant: honest uniform answer.

## Task 5 judgements (real defect vs honest property)
- order_compare verbatim pair: REAL DEFECT. Stated pair 959/3,500 (always yes), reverse stated 993/3,500 (always no): 55.8%
  of items decided by one stated fact. Same defect class as the repaired equivalence_classes.
- conditional_decision_tree most-mentioned: 0.408 vs 0.271. Honest base rate (actions with more leaves) but exploitable
  from the option text alone; DESIGN DEFECT, cheap fix (one action per leaf or balanced mentions).
- tracking_accounts richest at start: 0.370 vs 0.224. HONEST property (persistence); approximate net-flow count 0.598.
- spatial_relative_directions: least-mentioned 0.383 vs 0.245, most-mentioned 0.083, direct neighbour of anchor 0.072.
  DESIGN DEFECT (random fact tree: farthest place is a leaf mentioned once), moderate.
- kinship_*_r3 least-mentioned / parentless: leaves never answer = honest logic; root never in ancestor_r3 = design
  artefact (minor); descendants_r3 parent-of-hub / root-child tells = REAL (redraw).
- containers_queue_line_r2: no strong tell; strict merge with Josephus is the issue.
- temporal_critical_path: longest job 0.319 vs 0.190; depth-only approximation 0.718: DESIGN WEAKNESS (durations rarely
  decide), moderate.
- stable_matching_r2 first mentioned: REAL redraw artefact (0.148 vs 0.248, opposite informative); second choice +0.21.
- activity_selection greedy: REAL (shortest-first 0.927).
- minimax smallest leaf: honest math eliminator; REAL level-design defect (identical levels).
- venn constant: HONEST.

## Must be fixed before registration (my list)
1. Cluster map: four more strict merges (27 not 31); borderline range 14-27; PENDING LEAD REVIEW.
2. Partition reading ruling; under the author's partition 3 of my primary clusters straddle. The 28 pilot/new lineages are not
   in core.REGISTRY, and core.REGISTRY still holds the superseded kinship_ancestor and categories_follow, so core.family_partition
   / generate_pool would build pools from the wrong set.
3. categories_default_exceptions_r3 chain[1] tell; conditional_threshold_rule_r3 margin tell and per-level miscalibration;
   order_compare verbatim pairs; kinship_descendants_r3 hub tells; elimination_bracket_r3 neighbour tell; stable_matching_r2
   second-choice / first-mentioned; activity_selection shortest-first; mst_cost cheapest-per-town at low levels.
4. Level design: minimax (identical levels), nim/venn (magnitude-only levels), graph_shortest_route_r2 (2-hop at all levels);
   nim L0 capacity to be checked against the pool demand at G-gen.
5. Wording: categories_follow_r2 frame ("Does it follow ... no / cannot be determined"); boolean_lights_r2 "every other lamp".
6. Redraw method: if kept, fit per level and register it as part of the lineage; better, remove heuristics by construction.
