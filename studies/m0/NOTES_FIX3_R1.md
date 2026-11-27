# R1 fix round 3: notes for the lead and the final audit

Implementer: Claude Sonnet 5.5 (`arbor-implementer`). One bounded fix round authorised by the human lead's fourth decision (`HUMAN_LEAD_WORDS_4.md`: "fix round"). Not registered, not independently reviewed, not
Astra-validated, not human-approved. Nothing is in `core.REGISTRY`; no second solver exists for the new shapes; no model was run, nothing downloaded or trained. Every number below is MEASURED
(generator output scored by the rules named) unless it says analytical. Self-checks only.

## What was done

Input: `docs/reviews/m0-lineage-decision-2026-11-25/audit3_r1/AUDIT3_R1.md` (verdicts in its section 7), `LEAD_RULINGS_2.md`, `LEAD_RULINGS_3.md`, ADR-0033 sections 6.2, 6.4, 6.5.
Output: `studies/m0/lineages_r1_fix3_{a,b,c,d,e}.py` (shape ids end `_r5`; 30 builders), `lineages_r1_fix3_common.py` (the list `FIX3`, never `core.REGISTRY`),
`lineages_r1_fix3_clusters.py` (map v3 and the registered set), `r1_fix3_battery.py` (the third auditor's battery, copied, plus rules for the rebuilt shapes), `r1_fix3_gates.py` (the three gate fixes),
`r1_fix3_capacity.py`, `r1_fix3_measure.py`, `r1_fix3_tables.py`, `r1_fix3_fixtures.py`, manifests `manifests/r1_fix3_*`, fixtures `fixtures/r1_fix3/` and `fixtures/R1_FIX3_SCHEMA.md`, tests `tests/test_m0_r1_fix3_*.py`.
No existing file was edited. Old shapes stay on file and are listed in `fixtures/r1_fix3/SUPERSEDED.txt`.

Result in one line: 37 registered-candidate shapes in 23 strict clusters (the map had 43 shapes in 27; the auditor's map 25). 30 `_r5` builders were written: 27 are candidates (one of them, `venn_counting_r5`, only widens magnitudes) and 3
are NOT REGISTERED rebuilds. Six shapes are NOT REGISTERED in all (R-12). Ten earlier shapes are kept unchanged (the auditor's R verdicts).

## Rules every rebuilt shape follows

- No redraw conditional on a heuristic's outcome or on the answer value (R-1, R-13). Where a class is balanced it is DRAWN FIRST and the item is built to meet it; a `Retry` is raised only for validity
  (unique answer, non-empty candidate set, the drawn class met). A test scans the new modules for `_anti(`, `credit(`, `ANTI_P`, `anti_override`, `SPECIFIC`, `generic(`. Retry rates are in `manifests/r1_fix3_retries.json`
  (largest: `attribute_rule_r5` 0.13 to 0.27, `containers_stack_piles_r4` 0.24 at level 0 (kept shape), `kinship_ancestor_r4` 0.56 to 0.74 (kept shape)).
- Every convention is in the item text (day counting, which end of a row is first, what 'some' / 'no' say, cousin definition, the number of days 'apart', the units of a rate).

## Per shape (before = the earlier shape measured with the same battery, max over levels of the best rule's gain over the base rate; after = the new shape; both 500 items per level, seed 6200 / fit 6300)

Gain = accuracy minus chance of the best rule, or of 'choose among the options the rule did NOT choose', whichever is larger (two-sided; `low` = most negative value is in `manifests/r1_fix3_shortcuts.json`, a floor of 1/k for a
closed answer when a rule always names one option). Full per-level table: `manifests/r1_fix3_shortcuts.md`. The working target was +-0.10; it is NOT reached everywhere (see 'Not reached').

| shape | construction (what removes the defect) | levels control difficulty by | before -> after | status |
|---|---|---|---|---|
| activity_selection_r5 | zones E (a clique of 2-6 meetings, contributes 1) and F (1-10 separate meetings) decouple the answer from the meeting count; two A and two B trap zones always | 6 + level // 2 zones | 0.50 -> 0.18 | candidate |
| attribute_rule_r5 | every badge matches the same number k of the rule's tests (k drawn first; the winner and the others drawn uniformly among badges with k matches); rules always mix and/or and contain a negation; depth 3 + level // 2 | rule depth, badges | 0.70 -> 0.21 | candidate |
| conditional_chain_r5 | class drawn first; the asked variable is never a fact; chains of 2 + level // 3 rules; exactly two rules conclude it | variables, chain depth | 0.53 -> 0.03 | candidate (cluster with knights, one_culprit) |
| order_compare_r5 | class drawn first; planted chain of d in 2+L..7+L steps; x and y are interior (never chain ends); leaves hang from x and y | chain length | 0.64 -> 0.10 | candidate |
| road_reachability_r5 | same plant for roads (d in 3+L..6+L), outdegree of x drawn first for both classes | path length | 0.39 -> 0.08 | candidate |
| equivalence_classes_r5 | same plant for same / different links, 6 + level decoy items | chain length | 0.31 -> 0.12 | candidate |
| categories_follow_r5 | class and kind drawn first; premises planted so every yes / no needs a No or Some lifted through All; decoy groups | chain length | 0.44 -> 0.12 | candidate |
| event_timeline_r5 | asks 'how many days apart' for the ends of a spine of 4 + level // 2 statements | spine length | 0.51 -> 0.13 | candidate (the earlier 'first / last' question is gone) |
| temporal_weekday_shift_r5 | the asked event is 5 + level // 3 links from the anchor, random signs | spine length | 0.39 -> 0.05 | candidate |
| spatial_relative_directions_r5 | ends of a spine of 5 + level // 3 facts | spine length | 0.63 -> 0.13 | candidate |
| equivalence_exchange_rates_r5 | asks 'how many units of Y are worth N units of X' (whole number) along a spine of 3 + level // 2 rates | spine length | 0.51 -> 0.05 | candidate; question type changed, see flags |
| kinship_cousins_r5 | one family; pair type drawn first (cousins / siblings / other relation), a third each | tree size | 0.45 -> 0.20 | candidate; two clauses of the definition each leave +0.17 to +0.22 (analytic floor +0.167) |
| kinship_descendants_r5 | height 3-5 drawn independently of the number of descendants (at least 8); extra descendants never go to the candidate's children | candidates, sizes | 0.68 -> 0.04 | candidate |
| knights_knaves_r5 | statements drawn as true (knight) or false (knave) from six kinds, independent of the speaker's type; 4 + level // 2 people | people | 0.28 -> 0.14 | candidate |
| seating_row_r5 | the asked seat is never a 'pos' clue; 6 / 7 seats; all clue kinds from level 0 | seats | 0.21 -> 0.14 | candidate |
| pet_owners_r5 | tried: the asked pet in no owns / either clue | people | 0.39 -> 0.72 | NOT REGISTERED (below) |
| temporal_critical_path_r5 | convention stated in the item (days numbered from 1, a waiting job starts the day after); the answer is the number of days in all; exactly two prerequisites among the four previous jobs; durations 5-12 | jobs 8 + level | 0.82 -> 0.17 | candidate |
| temporal_interval_overlap_r5 | answer and start gap drawn independently; early length above or at most the gap; late length 2-60 | events | 0.47 -> 0.19 | candidate; the rule 'the longer interval is longer than the gap' is a partial reading of the full test |
| containers_queue_line_r5 | position j drawn first; one of every kind of operation always; leavers in positions 2..j; line 9+ | operations 8 + 2 * level | 0.47 -> 0.08 | candidate |
| tracking_accounts_r5 | asks one person's final balance (a number); a payment, an earning and a halving involving them are planted | operations, people | 0.57 -> 0.02 | candidate; question type changed, see flags |
| spatial_grid_walk_r5 | end cell drawn first (uniform over reachable cells), free walk drawn uniformly, 3 + level // 3 wall-blocked moves planted; walk length parity varies | grid size, walk length | 0.66 -> 0.07 | candidate |
| nim_xor_r5 | the xor of a first-player item is a single bit (position uniform in 1..bits-1) | piles, pile size | 0.41 -> 0.16 | candidate |
| topological_order_r5 | parallel chains (4 + level // 2) of unequal length, names independent of position; 10 + level jobs | jobs, chains | 0.69 -> 0.18 | candidate |
| venn_counting_r5 | wider magnitudes (the earlier level 0 could print only ~11,000 items) | groups, asked quantity | 0.07 -> 0.03 | candidate (capacity widening only) |
| minimax_tree_r5 | trees of 27 to 256 leaves, branching 3 or more, leaves -50..50 | depth, branching | 0.67 -> 0.20 | candidate |
| elimination_bracket_r5 | only 'who wins' and 'who loses the final' (8 players levels 0-2, 16 later); the earlier 'who knocks X out' scored +0.35 | players, question | 0.35 -> 0.17 | candidate (merged into the tree-evaluation cluster) |
| graph_bipartite_r5 | rebuilt, not dropped: n = 13 + level, triangle-free in both classes, equal edge counts, odd cycle >= 5 for no | people | 0.49 -> 0.04 | candidate |
| swap_tracking_r5 | rebuilt, not dropped: 5 + level // 2 people, asked item moved by both a swap and a rotation | people, operations | 0.22 -> 0.05 | candidate |
| instant_runoff_r5, stable_matching_r5 | tried (ring ballots, wider totals, 6-9 candidates; a planted rotation) | | 0.40 -> 0.45; 0.54 -> 0.32 | NOT REGISTERED (below) |

Kept unchanged (auditor R): boolean_lights_r4, categories_default_exceptions_r4, compass_turns, conditional_decision_tree_r4, conditional_threshold_rule_r4, containers_stack_piles_r4, graph_shortest_route_r4,
kinship_ancestor_r4, mst_cost_r4, one_culprit. Measured here with the same battery: all <= 0.19 once the rules the auditor set aside (misreadings of one command or a threshold, partial walks that are a prefix of the true
procedure; `EXCLUDED_BY_SHAPE` in the battery) are left out; the unexcluded values are in the raw rows of the measure run.

## NOT REGISTERED (ruling R-12: removed from the map, G, fixtures and capacity runs; the reasons are in `lineages_r1_fix3_clusters.NOT_REGISTERED_V3`)

- elimination_josephus, order_extreme, order_tournament_wins: capacity of 16-40, 2 and 4-524 structures per level (audit, exact); the procedure has too few parameters. Not rebuilt.
- pet_owners: when the asked pet is stated the answer is verbatim; when it is never stated (pet_owners_r5) the owner is the person the other clues leave over, and 'not struck off and not owning another named pet' reads +0.63 to +0.72.
- instant_runoff: four settings tried (a hidden cycle of candidates with probability 1/2 and 1, totals 10-30 and 18-20, 4 to 8 candidates): the runoff between the two plurality leaders reads +0.25 to +0.57, one elimination then plurality
  +0.31 to +0.43, Borda +0.28 to +0.37 and the Condorcet winner +0.20 to +0.39. The other voting rules agree with the elimination count whatever the profile (measured at 200 items for the settings, 500 for the final one).
- stable_matching: the earlier receiver-proposing reading falls from +0.51 to below +0.17 with a planted rotation, but serial dictatorship in the order of the text reads +0.14 to +0.34, the first choice up to +0.33, and the last choice is
  never the answer (a floor of -1/n); a second planting did not help.

## Strict cluster map v3 (`lineages_r1_fix3_clusters.py`, `manifests/r1_fix3_clusters.json`)

The auditor's map governs. Both merges are in: conditional_chain with knights_knaves / one_culprit; elimination_bracket with attribute_rule / conditional_decision_tree / minimax_tree. I do not disagree with either (my
rebuilds keep both algorithms: the chain is still decided by enumerating assignments; the bracket is still bottom-up evaluation). 37 shapes in 23 clusters: 6 merge groups (closure; potential propagation; pointer chasing;
assignment enumeration; tree evaluation; cyclic fold) and 17 singletons. Under the `cluster_keys` partition reading (seed 400004, the registered rule): 11 clusters in part A (16 shapes), 12 in part B (21 shapes); no cluster spans both
parts (ruling R-6). The other readings are reported, not chosen: `literal` leaves 6 clusters in both parts; `family_closure` 8 / 15 clusters (13 / 24 shapes); `literal_move_to_B` 8 / 15 (8 / 29).

## Capacity (`r1_fix3_capacity.py`; `manifests/r1_fix3_capacity.{md,json}`)

Demand per cluster and level: 10 x (ceil(4,000 / 11) + ceil(20,000 / 11) + 100) = 22,830 at G = 11, the same for the reserve levels (R-10, R-11). Two readings: (a) names, settings, presentation order and symmetric phrasings relabelled; (b) labels
(colours, shapes, marks, letters, lamp numbers) relabelled too. The key is a Weisfeiler-Lehman colour refinement of the structured form (invariant under renaming and reordering: tested on every shape; two non-isomorphic items can share a
key, so distinct keys under-count). From 2,000 draws per cell: PASS when the distinct keys seen, the collision estimate 1/sum(p^2) or, with no collision, the 95 % lower bound N(N-1)/6 reaches 22,830. Estimates are statistical (about +-12 %); seating_row
was rechecked at 20,000 draws (`manifests/r1_fix3_capacity_seating_20k_raw.jsonl`); an earlier version without 'between' at levels 0 to 2 read 20,474 at level 0 and was widened (kept in the docstring).
Result: every one of the 23 clusters passes at all 7 levels under both readings on the cluster sum. Smallest cluster margins (reading a, 2,000 draws): seating_row 52,605, graph_bipartite 60,576 (level 0), every other cluster 499,750 or more; seating_row at 20,000 draws: collision estimates of 60,861 (level 0) to 124,916.
Shapes below their even share (demand / shapes in the cluster) under reading (a), all in clusters that pass on the sum: compass_turns level 0 (11,230 against 11,415), kinship_ancestor_r4 level 0 (2,067 against 7,610), one_culprit levels 0 and 1 (2,408, 2,493 against 7,610). These
are kept shapes; I did not widen them; if the registered allocation is even over shapes they are the place to look. The earlier-flagged capacity failures are resolved by construction or by exclusion: graph_bipartite (n = 13 + level), swap_tracking (5 people),
seating_row / pet_owners (6-7 seats), topological_order (the key keeps the alphabetical order of names: only order-preserving renamings are identified), venn_counting level 0, equivalence_classes, categories_follow, kinship_cousins.

## The three gate fixes (`r1_fix3_gates.py`; the old gate unchanged; tests assert each guard fails on the old gate and holds on the new)

(1) `numbers()` no longer counts 'one of the 2 options shown'; (2) a question without '?' (categories_follow's 'Consider the statement') now gets the yes / no heuristics; (3) a 'No' / 'Some' premise stated in the reverse order is read (it is symmetric).

## Flags for the lead and the final audit (PENDING LEAD REVIEW where they touch a scientific choice)

- Question types changed (same procedure): event_timeline (first / last -> days apart), equivalence_exchange_rates (the most valuable item -> a conversion quantity), tracking_accounts (most / least -> one balance), temporal_critical_path (who finishes last -> days in all; the
  auditor's wording fix needed a number). exchange_rates now resembles a unit-rate chain; the R2 / M1 / C1 audits list no duplicate with it, but M1's multiplicative-chain family (S3) is the nearest: a call for the cross-evaluation map (R-15).
- Shortcut values above +0.10 remain (max over levels, after): attribute_rule +0.21, kinship_cousins +0.20, minimax_tree +0.20 (level 0 only), interval_overlap +0.19, mst_cost +0.19 (kept), containers_stack_piles +0.19 (kept), activity_selection +0.18,
  topological_order +0.18, critical_path +0.17, bracket +0.17, nim +0.16, knights +0.14, seating +0.14, one_culprit +0.18, boolean_lights +0.14, conditional_threshold_rule +0.15 and graph_shortest_route +0.15 (kept shapes). None is above +0.25. kinship_cousins cannot go lower: with three pair types of equal weight each of
  the two clauses of the definition leaves +0.167 (analytic), and the constant 'no' reads +0.17.
- The 'low' side: several shapes have a rule that is wrong more often than chance by more than 0.10 (kinship_cousins -0.19 for 'same family means yes', knights -0.14, categories_follow -0.14); for closed answers 'low' is mostly a floor (a rule that always names one option reads -1/k), the exploitable reading is the 'gain' column.
- Several shapes use the answer class drawn first and then check it by an independent computation (the closure for categories_follow, enumeration for conditional_chain); the Retry there is a validity check on the drawn class, not on a rule.
- `last_choice` never the answer in stable_matching_r5 and 'never the start cell' were floor effects of the first designs; the grid walk now varies the parity of the walk so the end cell is not tied to the start's colour.
- Second solvers do not exist; the independent solvers in `tests/test_m0_r1_fix3_keys.py` re-derive every key from the structured form (12 items x 7 levels x 26 shapes) as a self-check, not as the R-9 solver.
- Levels: seating_row has 6 seats at level 0 and 7 from level 1; knights, queue and bipartite grow slowly. Where a level mostly differs in size, the difficulty step between neighbouring levels is small.

## Slips, failed attempts, leftovers (kept)

- A command `sed -i.x ... /dev/null` was typed once by mistake (it wrote nothing and failed). The rule 'no `sed -i`' was broken in intent, not in effect. No other command from the forbidden list was run.
- Files were written through Bash heredocs and one-off python replacements (the Write / Edit tools were not used), as the brief allowed. All edits were to my own new files.
- Four designs tried and dropped before the ones above (kept in the shapes' docstrings): instant_runoff (4 settings), stable_matching (2 plantings), the first activity_selection (answer still 0.15-0.19 at level 0), attribute_rule at depth 2 (a rule of two tests is decided by counting).
- A capacity run at 3,000 draws was cut at 120 of 259 cells by its timeout under load (file kept in scratch); the numbers use the clean 2,000-draw run.
- Scratch (not removed): `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fix3_r1_20261125/` (runs, logs, one-off scripts). Pre-existing untracked leftover not mine: `studies/m0/m1_rev2_gates.py.bak`.

## Commands

`PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix3_measure 500 6200 6300 <out.json>`; `... -m studies.m0.r1_fix3_capacity 2000 7300 > <out.jsonl>`; `... -m studies.m0.r1_fix3_fixtures`;
`... -m studies.m0.r1_fix3_tables <measure.json> <capacity.jsonl> 6200 7300`; tests: `uv run --locked python -m pytest tests/test_m0_r1_fix3_*.py tests/test_m0_r1_*.py -q -p no:cacheprovider`.
Seeds 6200, 6300, 7300, 7400 and the small integers in the tests are throwaway; none is a registered study seed.

Astra review: NOT_PERFORMED
