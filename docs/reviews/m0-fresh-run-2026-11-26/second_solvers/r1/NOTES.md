# Second solvers, R1 (NAME = r1): per-lineage notes

Written by an auditor context (Claude Opus 5.5, model id claude-opus-5-5) from the answer-free fixtures, SCHEMA.md and question texts only. Not Astra validation, not human approval. Astra review: NOT_PERFORMED.

All ten solvers compute from `structured`. Every question text was also parsed independently with strict per-template regexes (`textcheck_v2.py`, output `textcheck_v2.out`): for all 2800 items, every sentence matched a template, the text-derived fields equal the `structured` fields exactly, and solving from the text-derived form gives the same answer (0 parse failures, 0 field mismatches, 0 answer differences in every lineage). So each lineage is effectively solved from both; the module itself reads `structured` only (the `question` argument is unused). `textcheck.py` (v1) is a kept failed attempt: its sentence splitter required an uppercase letter after a full stop and failed to split the exchange-rate sentences, which start with a digit (all 280 items of that lineage were PARSEFAIL); v2 fixes the splitter only.

Hand checks: `handcheck.py` (v1, kept) reported 2 differences that were my own labelling error: I had attached my hand answers for the two level-6 categories items to the wrong indices (I printed levels 0, 3, 6 and miscounted the level-3 items as level 6). `handcheck_v2.py` relabels them and adds items: 40 hand-worked items, 0 differences (`handcheck_v2.out`).

## R1.boolean_lights_r4
Procedure: start from `initial`; for each colour in `presses` toggle every lamp in `switches[colour]`; answer `yes` iff lamp `ask` is on. Read: `initial`, `presses`, `switches`, `ask`.
Templates: "There are N lamps numbered 1 to N."; start: "lamps a, b and c are on / lamp a is on, and all the lamps not named here are off" (272), "all lamps are off" (4), "all lamps are on" (4); "The C switch toggles lamp(s) ... (each one goes ...)"; "The switches are pressed in this order: ..."; "Is lamp N on at the end?"; "Answer yes or no."
Hand-checked: L0 i0 yes, L0 i1 yes, L6 i0 no, L6 i1 yes.

## R1.categories_default_exceptions_r4
Procedure: walk `chain` from the member's own group (index 0) towards the most general; the first group that has a rule about `verb` decides (specificity rule stated in the text). Raises if a group has both can and cannot for the verb or no group on the chain has a rule (neither happened). Read: `chain`, `rules`, `verb`.
Templates: "Every X is a Y."; "A X can V." / "A X cannot V."; the specificity sentence; "Name is a X."; "Can Name V?"; "Answer yes or no." The is-a sentences form a single chain; no group in the text lies off the member's chain (checked). The deciding rule sits at chain position 1..20; in 149/280 items the most general rule on the chain disagrees with the deciding one.
Hand-checked: L0 i0 no, L0 i1 yes, L3 i0 yes, L3 i1 yes, L6 i0 yes, L6 i1 no.

## R1.compass_turns
Procedure: heading in degrees clockwise from north; left = -90, right = +90, around = 180, cwN = +N, ccwN = -N; walks do not change heading. Read: `start`, `seq`.
Templates: "You are facing D. You <step>, then <step>, ... . Which direction are you facing now? Answer north, east, south or west." Steps: walk N steps; turn left/right/around; turn 90/180/270 degrees clockwise; turn 90 degrees counterclockwise (only 90 occurs for counterclockwise).
Hand-checked: L0 i0 east, L0 i1 north, L3 i0 east, L6 i1 west.

## R1.conditional_threshold_rule_r4
Procedure: net = sum of yes weights - sum of no weights; `yes` iff net >= margin ("at least"). Read: `members`, `votes`, `margin`.
Template: one fixed template (members 6..12, D may be negative). 64 items sit exactly on the boundary (net == D), so "at least" (>=) matters there; the text is explicit.
Hand-checked: L0 i0 no, L0 i1 no, L3 i0 yes, L6 i1 no.

## R1.equivalence_exchange_rates_r6
Procedure: exact rational values (fractions.Fraction) propagated from x over the rate graph (p of a = q of b gives val(b) = val(a)·p/q); answer n·val(x)/val(y); raises if not a positive integer or rates inconsistent (never). No item has redundant rates (graph is a tree). Read: `rates`, `x`, `y`, `n`.
Templates: "p units of A are worth the same as q units of B." (written "1 units" when p = 1); "How many units of Y are worth the same as n units of X?"
Hand-checked: L0 i0 2, L0 i1 18, L3 i1 5, L6 i0 100.

## R1.knights_knaves_r6
Procedure: enumerate all 2^n knight/knave worlds; keep those where each person's statement truth equals their being a knight; the asked person's kind must be the same in every kept world (raises otherwise). Every item has exactly one consistent world. Read: `people`, `statements`, `who`.
Statement templates: "X is a knight." (is_knight), "X is a knave." (is_knave), "X and Y are both knights." (both_knights), "at least one of X and Y is a knave." (some_knave), "X and Y are of the same kind." (same_kind), "exactly one of X and Y is a knight." (differ); frame "Each person is either a knight ... Is X a knight or a knave? Answer knight or knave."
Hand-checked: L0 i0 knave, L0 i1 knight, L3 i0 knight.

## R1.spatial_grid_walk_r5
Procedure: row 0 is north; north = row-1, south = row+1, east = col+1, west = col-1; a move into a wall (null) or off the grid is skipped; answer the name of the final cell. Read: `grid`, `start`, `moves`, `convention` (only one convention string occurs; the solver raises on any other).
Templates: header "A map has R rows (row 1 is the northernmost) and C columns (column 1 is the westernmost)."; "Row k: name/wall, ..."; "You start at Name."; "You move d, then d, ..., one cell each time."; "A move into a wall or off the map does nothing."; "Which place do you end on?"; "Choose from ...". Text check: place names unique, choices = all places, answer always in choices.
Hand-checked: L0 i0 Kanek, L0 i1 Ralar, L3 i0 Niler, L6 i0 Lilor.

## R1.swap_tracking_r5
Procedure: swap a,b exchanges; rotate a,b,c ("a hands their item to b, b hands theirs to c, and c hands theirs to a, all at once") sets new[b]=old[a], new[c]=old[b], new[a]=old[c]. Read: `hold`, `ops`, `who`.
Templates: "At the start A holds the x, ..."; "A and B swap what they are holding."; the rotate sentence (the text check confirms the three names are consistent with the cycle a->b->c->a); "What is A holding at the end?"; "Choose from ...". Answer always in choices.
Hand-checked: L0 i0 scarf, L0 i1 globe, L3 i0 apple.

## R1.temporal_weekday_shift_r6
Procedure: day offsets from the anchor event by propagating links (later = earlier + n); answer days[(index(anchor day) + offset(ask)) mod 7]. No redundant links (tree). Read: `anchor`, `links`, `ask`, `days`.
Templates: "The E took place on a D."; "The E took place N days after/before the F." (also "1 day"); "On which day of the week did the E take place?"
Hand-checked: L0 i0 Tuesday, L0 i1 Sunday, L3 i0 Wednesday.

## R1.venn_counting_r5
Procedure: pair/triple/quad numbers read as inclusive intersections ("N are in both A and B" includes people also in other groups; SCHEMA says the same); exact region counts by inclusion-exclusion over all subsets (raises on a negative region: never); answer sum of regions with 0 / 1 / 2 / >=2 memberships for ask none / one / two / atleast_two. Read: `total`, `groups`, `sizes`, `pairs`, `triples`, `quad`, `ask`.
Templates: "Among N people, a people are in the G group; ...; k are in both the G and the H groups; ...; k are in all of the G, H and I groups; ...; k are in all four groups. Each person is counted once in each number that applies to them. How many of the people are in none / exactly one / exactly two / at least two of these groups?" Levels: L0 2 groups none, L1 2 groups one, L2 3 groups none, L3 3 groups two, L4 3 groups at least two, L5 4 groups none, L6 4 groups two.
Hand-checked: L0 i0 28, L0 i1 13, L3 i0 60, L3 i1 65, L6 i0 165.

## Commands (all run with system Python 3.15.1, `python3 -I -B`, standard library only)
- `python3 -I -B .../run_solver2.py` -> `answers_r1.jsonl` (2800 lines; 0 ambiguous, 0 bad format)
- `python3 -I -B .../textcheck.py` (failed attempt, output not kept beyond the tool log), `python3 -I -B .../textcheck_v2.py > textcheck_v2.out`
- `python3 -I -B .../diagnostics.py` -> `diagnostics.out`
- `python3 -I -B .../handcheck.py` -> `handcheck.out` (2 differences, my labelling error), `handcheck_v2.py` -> `handcheck_v2.out` (0)
