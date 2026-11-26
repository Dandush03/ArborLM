# M0 stage 2, R1: what was read, per lineage (file:line)

Paths are relative to the implementation worktree `agent-a0c9d741ea96ce52f` (HEAD `128a02a7`). Builders unchanged since `7cd0ac5a` (checked with `git diff --quiet 7cd0ac5a -- <files>`, working tree included); `final_r1/` unchanged since `b78e58b1` (same check). `final_r1/` = `docs/reviews/m0-lineage-decision-2026-11-25/final_r1/`. The set: `studies/m0/lineages_r1_fix4_clusters.py:73-84` (`registered_v4`), filtered to the 10 ids of `studies/m0/manifests/survivor_list_of_record.json` (all 10 found). Shared: `studies/m0/core.py:44-84` (Retry, Built, Lineage); `studies/m0/vocab.py` (lists checked: no duplicates; no entry equal to wall/yes/no/knight/knave). Rendered fixtures read: `run1/samples_r1.txt` (2 per level per lineage). Level parameters confirmed from structured output: `levels_params_r1.stdout.txt`.

Second solver for every lineage: `final_r1/solvers_final.py` (imports at 9-11, `heapq` inside 224; `SOLVERS` 463-476); recorded agreement `final_r1/FINAL_R1.md:46-61`; wording note of that auditor 63-68; the dump the solver was written from, `final_r1/samples.py:2,15`, prints the builder's key.

| Lineage | Builder read | Solver function read | Level parameters (from code) |
|---|---|---|---|
| R1.boolean_lights_r4 | `lineages_r1_rev4.py:26-70` | `solvers_final.py:38-63` | lamps 4+L, presses 3+2L, switches 3+L//3 (33-37) |
| R1.categories_default_exceptions_r4 | `lineages_r1_rev4.py:182-214` | `solvers_final.py:67-91` | T 9+2(L//2), chain T+8+2L (192-193) |
| R1.compass_turns | `lineages_r1.py:606-628` | `solvers_final.py:98-116` | commands 3+2L (611) |
| R1.conditional_threshold_rule_r4 | `lineages_r1_rev4.py:73-90` | `solvers_final.py:165-179` | members 6+L (80) |
| R1.equivalence_exchange_rates_r6 | `lineages_r1_fix4_a.py:109-130`; `_spine`, `_smooth` `lineages_r1_fix3_b.py:24-31,110-114` | `solvers_final.py:183-211` | spine 3+L, extras 2+L//3 (113-114) |
| R1.knights_knaves_r6 | `lineages_r1_fix4_a.py:133-174`; `_kk_true` `lineages_r1_fix3_c.py:129-142` | `solvers_final.py:241-287` | people 4+L (138) |
| R1.spatial_grid_walk_r5 | `lineages_r1_fix3_d.py:199-271`; `DIMS`, `STEP` `lineages_r1_spatial.py:12-13` | `solvers_final.py:294-323` | DIMS by level, free moves 4+L+U(0..3), blocked 3+L//3 (213-214) |
| R1.swap_tracking_r5 | `lineages_r1_fix3_e.py:403-439` (OBJECTS import 318) | `solvers_final.py:327-357` | people 5+L//2, operations 6+2L (409, 416) |
| R1.temporal_weekday_shift_r6 | `lineages_r1_fix4_a.py:62-82`; `_spine`, `DAYS` `lineages_r1_fix3_b.py:19,24-31` | `solvers_final.py:364-400` | spine 5+L, extras 2+L//3 (66-67) |
| R1.venn_counting_r5 | `lineages_r1_fix3_d.py:350-378`; earlier docstring `lineages_r1_rev4_b.py:401-403` | `solvers_final.py:404-460` | `_VENN5` (groups, ask) per level (350); regions 1..24+4L, none 0..30+2L (359-360) |

## Per lineage

- **boolean_lights_r4.** Wording: the asked lamp's toggles are exactly the pressed switches in `s_ask` (42-55; `others` excludes the asked lamp at 50, so no other switch reaches it except unpressed ones, which do not act); the key is the simulated state (56-59, 70). The start sentence states the lamps that are on and that all others are off (60-66). Levels: every level has a different lamp and press count.
- **categories_default_exceptions_r4.** Wording: one chain (209), member in `chain[0]` (213), the deciding rule at distance d >= 1 (197, 203), other rules on the asked verb only beyond d on distinct groups (198, 203), rules on the other verb irrelevant (204-206); the stated convention makes the nearest rule decide, which is `want` (214). Unique key. Levels: chain and rule counts differ at every level.
- **compass_turns.** Wording: amounts (610) match the text (619-620): left = 270 clockwise, 90 counterclockwise = 270 clockwise. Levels: 3+2L commands.
- **conditional_threshold_rule_r4.** Wording: threshold d = margin - offset (84-87); "at least d" with yes iff offset in {0,1} (86), so the key equals (margin >= d). Levels: member count differs at every level.
- **equivalence_exchange_rates_r6.** Wording: p v_a = q v_b at 124 matches "p units of a are worth the same as q units of b"; edges form a tree (`_spine`), so the ratio X:Y is determined; answer nn v_X / v_Y is an integer since nn is a multiple of v_Y / gcd (125-127). Levels: spine 3..9.
- **knights_knaves_r6.** Wording: statements rendered (164-172) match `_kk_true`; the builder keeps only statement sets with exactly one consistent assignment over all n people (155-157), so the key is unique. Levels: n = 4..10.
- **spatial_grid_walk_r5.** Wording: blocked moves are only into wall cells inside the grid (215-224, 257-259), covered by the stated convention; place names come from distinct pseudo-words (207). Levels: cells 9,9,12,16,16,20,25; free-move range shifts by one per level; blocked 3,3,3,4,4,4,5.
- **swap_tracking_r5.** Wording: rotation text (434) matches the simultaneous assignment (425); start holdings and the options are all objects (411, 437). Levels: 6+2L operations.
- **temporal_weekday_shift_r6.** Wording: links form a tree from the anchor (`_spine`), signs rendered consistently with `wd` (74-79); the asked event is the spine end (80). The question asks for a day of the week without listing the seven names; I read "which day of the week" as stating the answer form. Levels: spine 5..11.
- **venn_counting_r5.** Wording: every intersection of every subset of groups is stated (365-371); the convention sentence (373) makes the pair and triple figures inclusive; the key is the region sum for the asked read-out (366). Levels: see the R-40 decision in `REPORT.md`.
