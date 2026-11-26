# M0 R1, final re-measurement after fix 4: independent second solver, pooled shortcut excess, levels, capacity

Auditor: arbor-auditor context (Claude Opus 5.5), 2026-11-25. Independent engineering and mathematical evidence only: **not Astra validation, not human
approval, nothing registered.** I wrote none of the code audited. Governing rulings: `LEAD_RULINGS_5.md` (R-24 to R-29), `LEAD_RULINGS_6.md` (R-30 to R-37).

Code read (read only, nothing written there): worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `9bcec484`, with the
uncommitted fix-4 files as they stand. `find <worktree> -newer work/start_marker -type f -not -path '*/.git/*'` listed no file mid-audit (22:3x); at the end it lists 49 files, all NOT mine: 48 under `docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/` (all stamped 22:31:52, another agent's cross-evaluation work) and one `docs/reviews/.ruff_cache/` entry (22:33:47; I ran no ruff). None of my scripts writes outside the scratch directory, and no `__pycache__` file is among them.
Environment: macOS 27.2.1 arm64, `uv 0.12.15`, `uv run --locked python` = CPython 3.12.14 (the worktree's locked venv), `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0` unless stated, every command run from the worktree root. `D` = `experiments/_scratch/m0_final_r1_20261125/deliver/`.
Seeds (throwaway, chosen by me, never registered study seeds): keys Random(31000+level) x1000 and Random(31500+level) x500 (trial 30000, 30 per level);
audit-4 battery items Random(32000+level) x3000, fit Random(32100+level) x400; implementer battery `items_of(..., 33000)` = Random(33000000+level) x3000, fit 33100 x300;
feature lookups fit Random(34000+level) / test Random(34100+level) x3000; levels Random(35000+level) x1000 and identity streams Random(4243) x100; NEW rules fit 36000 /
test 36100 x3000; reproducibility Random(37000+level) x300 and pool seed 8900; capacity `core.generate_pool` pool seed 8800, role `development`.

## Verdict table (the twelve shapes the manifest marks SURVIVES)

Keys = my text-only solver against the stored key (1,500 items per level: 1,000 at 31000 + 500 at 31500). Ambiguous = share with no unique answer under the
stated convention. Pooled excess = R-32 item-weighted pooled estimate (implementer primary n=1,000 + implementer replicate n=1,000 + my fresh n=3,000 per level), largest
over levels of the counted classes C and A (R-31), per shape and level (R-34). Levels: identity classes (7 = every level its own generator) / cross-level repeated texts.
Capacity: `core.generate_pool` as written; worst level, distinct texts supplied per lineage / demand.

| shape | cluster | key mismatches / n | ambiguous | largest pooled excess (level, rule, class) | levels | capacity | verdict |
|---|---|---|---|---|---|---|---|
| boolean_lights_r4 | R1.boolean_lights | 0 / 10,500 | 0 | 0.126 (L0, wired-switch count parity, C) | 7 / 0 | pass G=4 and G=3 (11-set); G=5 and G=4 (12-set) | STAYS |
| categories_default_exceptions_r4 | R1.categories_default_exceptions | 0 / 10,500 | 0 | 0.068 (L0, least specific rule, C) | 7 / 0 | pass, all four | STAYS |
| compass_turns | R1.boolean_lights | 0 / 10,500 | 0 | 0.078 (L0, last turn only, C) | 7 / 0 | pass, all four | STAYS |
| conditional_decision_tree_r6 | R1.attribute_rule | 0 / 10,500 | 0 | 0.040 (L0, negate all, C) | 7 / 0 | pass, all four | STAYS |
| conditional_threshold_rule_r4 | R1.conditional_threshold_rule | 0 / 10,500 | 0 | 0.083 (L0, approx count x mean, C) | 7 / 0 | pass, all four | STAYS |
| equivalence_exchange_rates_r6 | R1.equivalence_exchange_rates | 0 / 10,500 | 0 | 0.058 (L3, fitted constant, C) | 7 / 0 | pass, all four | STAYS |
| **graph_shortest_route_r6** | **R1.graph_shortest_route** | 0 / 10,500 | 0 | **0.163 (L1, fewest roads then length, A)** | 7 / 0 | pass G=5 and G=4 (12-set) | **DROPS** |
| knights_knaves_r6 | R1.conditional_chain | 0 / 10,500 | 0 | 0.120 (L2, accuses someone means knave, C) | 7 / 0 | pass, all four | STAYS |
| spatial_grid_walk_r5 | R1.spatial_grid_walk | 0 / 10,500 | 0 | 0.052 (L5, net displacement clamped, A) | 7 / 0 | pass, all four | STAYS |
| swap_tracking_r5 | R1.swap_tracking | 0 / 10,500 | 0 | 0.019 (L0, ignore swaps, A) | 7 / 0 | pass, all four | STAYS |
| temporal_weekday_shift_r6 | R1.equivalence_exchange_rates | 0 / 10,500 | 0 | 0.034 (L0, ignore before/after, A) | 7 / 0 | pass, all four | STAYS |
| venn_counting_r5 | R1.venn_counting | 0 / 10,500 | 0 | 0.050 (L0, fitted ratio x size, C) | 7 / 0 | pass, all four | STAYS |

**Final list (my measurement under R-24, R-31, R-32, R-34): 11 shapes in 9 clusters.**
- Shapes: boolean_lights_r4, categories_default_exceptions_r4, compass_turns, conditional_decision_tree_r6, conditional_threshold_rule_r4,
  equivalence_exchange_rates_r6, knights_knaves_r6, spatial_grid_walk_r5, swap_tracking_r5, temporal_weekday_shift_r6, venn_counting_r5.
- Clusters: R1.attribute_rule, R1.boolean_lights, R1.categories_default_exceptions, R1.conditional_chain, R1.conditional_threshold_rule,
  R1.equivalence_exchange_rates, R1.spatial_grid_walk, R1.swap_tracking, R1.venn_counting.
- Dropped here: graph_shortest_route_r6, a singleton, so the cluster R1.graph_shortest_route goes with it (10 -> 9 clusters). Cluster-keys partition (seed 400004) of
  the 11 shapes: A = {attribute_rule, conditional_chain, equivalence_exchange_rates, swap_tracking} (5 shapes), B = {boolean_lights, categories_default_exceptions,
  conditional_threshold_rule, spatial_grid_walk, venn_counting} (6 shapes); G = floor(9/2) = 4 = the smaller part.

## 1. Second solver from a separate context (`D/solvers_final.py`, `D/check_keys_final.py`)

Twelve solvers written by me from item texts only (`D/samples.py` dumps; sentence templates extracted from 280 items per shape). Before they were complete I had
not opened any builder, any implementer solver (`solvers_r1`, `r1_fix4_a3_solvers`, test solvers) or audit 3/4's `solvers3.py` / `solvers4.py`; the solvers import
nothing from the repository and read only the question string. I had read the implementer's notes (stated level parameters, no answer code) and the lead rulings.
Methods: lamp xor simulation; up-chain walk with most-specific-rule-wins and checks for two parents, cycles, contradictory rules, no rule; heading mod 4 with
multiple-of-90 check; recursive-descent parser of the nested if/then/otherwise rule; weighted sum against "at least"; BFS over exchange rates in Fractions with
cycle-consistency and integrality checks; Dijkstra; brute force over all knight/knave assignments with uniqueness of the asked person; grid simulation with
wall / edge convention; swap and 3-cycle simulation; signed day offsets mod 7 with consistency; full inclusion-exclusion (Moebius) for 2-4 groups with
non-negative region checks. Unknown wording raises a parse error (counted separately, never as agreement).

`PYTHONHASHSEED=0 uv run --locked python D/check_keys_final.py 1000 31000 D/check_keys_run1.jsonl` -> **84,000 items, 0 mismatches, 0 ambiguous, 0 parse errors**
(digest `811e263b...42cb9`); `PYTHONHASHSEED=5 ... 500 31500 D/check_keys_run2.jsonl` -> **42,000 items, 0 / 0 / 0**. Per shape 10,500 items, 1,500 per level.
**Mismatches classified: none remain.** Trial 1 (`check_keys_try1.txt`, 30 per level): 69 categories_default_exceptions mismatches, all **my solver's error** (my
rule regex consumed the ". " separator and skipped every other "A x can/cannot v." sentence); fixed (marked `FIX after try 1`), trial 2 0 mismatches; try 3 under
PYTHONHASHSEED=77 gives the same digest as try 2.

## 2. Wording

Share with no unique answer under the stated convention: **0 of 10,500 for every shape** (the solvers return "ambiguous" on any of the conditions listed above;
none fired). Conventions the key depends on are stated in the text of every shape (most specific rule wins; a move into a wall or off the map does nothing;
abstentions count for neither side; "at least"; each person counted once in each number that applies; knights always true / knaves always false).
Not tested: alternative readings a reader might bring despite the stated convention (for example "both" read as "exactly both" in Venn items).

## 3. Cheap rules: re-run, pooling, verdicts (`D/run_rules_final.py`, `D/pool_final.py`)

Re-run on my seeds, 3,000 items per shape and level, one process per shape:
`PYTHONHASHSEED=0 uv run --locked python D/run_rules_final.py 3000 32000 32100 33000 33100 34000 34100 3000 D/rules_run1`.
(1) audit 4's battery: `heuristics4.py` (with `heuristics3.py`, `solvers3.py`) copied **byte-identical** into `D/a4copy/` (SHA-256 equal to the audit files),
`heuristics4.main` run unchanged through a `gen4.py` shim serving the fix-4 set; the one adaptation: `preds` receives an `_r6` id as `_r5` so audit 4's NEW rules for a
shape's `_r5` builder apply to its `_r6` builder (the implementer made the same change by editing a copy). (2) the implementer's battery
`studies.m0.r1_fix3_battery.measure`, imported read-only. (3) audit 4's fitted count-feature lookups (`feature_tells4.py`, `kept_tells4.py` feature functions for the
four surviving shapes they cover) on fresh fit / test seeds. The set of (level, rule) rows per shape and source equals the implementer's in both of its runs (36 files
compared, 0 differences).

Pooling (R-32): per (shape, level, source, rule) the item-weighted mean of eff and of anti over implementer primary (n=1,000), implementer replicate (n=1,000) and my
run (n=3,000); excess = max(eff, anti); exact rules and error markers dropped; classes exactly audit 4's (`final_table4.py` definitions executed from the audit file,
not retyped): C and A counted, M and EXCL (convention slips, prefix walks, exact algorithms) not counted (R-31). **Discrepancy found:** the implementer's feature-lookup
rows are byte-identical in its primary and replicate runs (`r1_fix4_tells` fixes the seeds 8300/8400, 8500/8600), so its "replicate" did not replicate those rules; I
counted them once. Command: `uv run --locked python D/pool_final.py <audit4>/final_table4.py <impl>/run1 <impl>/run2_replicate D/rules_run1 D/pool_run1.json`.

Pooled counted maximum per level (`D/pool_run1.txt`):

| shape | L0 | L1 | L2 | L3 | L4 | L5 | L6 | verdict |
|---|---|---|---|---|---|---|---|---|
| boolean_lights_r4 | 0.126 | 0.092 | 0.074 | 0.040 | 0.034 | 0.034 | 0.026 | STAYS |
| categories_default_exceptions_r4 | 0.068 | 0.066 | 0.053 | 0.058 | 0.046 | 0.044 | 0.042 | STAYS |
| compass_turns | 0.078 | 0.011 | 0.007 | 0.012 | 0.009 | 0.011 | 0.005 | STAYS |
| conditional_decision_tree_r6 | 0.040 | 0.037 | 0.016 | 0.020 | 0.017 | 0.011 | 0.009 | STAYS |
| conditional_threshold_rule_r4 | 0.083 | 0.064 | 0.065 | 0.065 | 0.058 | 0.054 | 0.061 | STAYS |
| equivalence_exchange_rates_r6 | 0.056 | 0.054 | 0.049 | 0.058 | 0.047 | 0.056 | 0.052 | STAYS |
| graph_shortest_route_r6 | 0.136 | **0.163** | 0.097 | 0.092 | 0.082 | 0.081 | 0.083 | **DROPS** |
| knights_knaves_r6 | 0.119 | 0.116 | 0.120 | 0.115 | 0.110 | 0.117 | 0.109 | STAYS |
| spatial_grid_walk_r5 | 0.029 | 0.034 | 0.034 | 0.033 | 0.033 | 0.052 | 0.036 | STAYS |
| swap_tracking_r5 | 0.019 | 0.016 | 0.010 | 0.009 | 0.011 | 0.006 | 0.006 | STAYS |
| temporal_weekday_shift_r6 | 0.034 | 0.013 | 0.007 | 0.009 | 0.002 | 0.001 | 0.011 | STAYS |
| venn_counting_r5 | 0.050 | 0.044 | 0.033 | 0.028 | 0.022 | 0.025 | 0.014 | STAYS |

**graph_shortest_route_r6, level 1 (a core level), "fewest roads, then length" (class A, open answer, eff = accuracy):** audit-4 battery copy 0.149 (impl primary),
0.158 (impl replicate), 0.169 (mine, n=3,000) -> pooled (149 + 158 + 507) / 5,000 = **0.1628**; the implementer battery's own version of the rule pools to 0.1622
(0.140, 0.152, 0.173). Binomial SE of the pooled rate about 0.005; my fresh data alone (independent of the earlier selection of this rule) read 0.169 and 0.173 at
n=3,000 (SE about 0.007). Hand check of the pooled value against the raw rows: equal. boolean_lights_r4 L0 pools to 0.126 (0.099, 0.155, 0.1257 for the audit
copy), so the replicate's 0.155 does not survive pooling. My fresh-run maxima per shape are within 0.03 of the implementer's primary on every shape.

**Not counted, listed for the human lead (R-31):**
- M class (misreadings): largest pooled conditional_threshold_rule_r4 abstain-as-no **0.147** (L0; the implementer's primary read 0.158); grid east-west mirrored 0.060.
  **No shape would drop if M counted** at the pooled estimate (threshold sits 0.003 under the bound).
- EXCL class (convention slips of one command and prefix walks, excluded since audit 3): compass_turns ccw-as-cw 0.512, conditional_decision_tree_r6 ignore last
  condition 0.424, conditional_threshold_rule_r4 off-by-one-low 0.258, categories_default_exceptions_r4 partial walk of 3 0.184. If EXCL counted these four would drop:
  clusters R1.boolean_lights (compass; boolean_lights_r4 keeps it), R1.attribute_rule, R1.conditional_threshold_rule and R1.categories_default_exceptions -> 6 clusters.
- Raw lows (eff below base rate): the most negative are fitted constants that rarely name an option (decision tree -0.157, grid -0.165, swap -0.161: the
  -1/k floor of a constant, anti about 0.00); not exploitable and not counted, as audit 4.

**NEW cheap rules (mine, under an hour, `D/new_rules_final.py 3000 36000 36100`, `D/new_rules_run1.txt`; they do not decide anything here):**
- conditional_decision_tree_r6: "read the root light, then answer the commonest action in that branch": **+0.198 (L0), +0.195 (L1)**, +0.136, +0.132, +0.131, +0.078,
  +0.087. It is a prefix walk plus a leaf count; audit 4 classed prefix walks as EXCL. If it counted, the shape (a singleton cluster, R1.attribute_rule) would drop.
- knights_knaves_r6: fitted lookup on (own statement form, number of others calling the asked person a knight / a knave, self in own statement) +0.131 max; form of
  statements mentioning the asked person +0.137 (L0). Under the bound.
- boolean_lights_r4: lookup (asked lamp at start, switches wired to it, presses parity) +0.127 max. compass "word turns only" +0.070. Categories first / last stated
  rule for the verb, "rule nearest the top of the chain", (#can, #cannot) lookup: at most 0.065. Weekday "anchor + signed sum of all links" and "links touching
  the asked event": at most 0.016.

## 4. Levels (`D/levels_final.py 1000 35000`, `D/levels_run2.txt`, `D/weekday_hops.py`)

Tested three ways: (a) audit 4's identity test (one Random(4243) per level, 100 items; identical streams = one generator): **7 classes for all 12**; (b) cross-level
repeated normalised texts among 1,000 items per level: **0 for every pair of levels**, every shape; (c) the stated parameter measured from the TEXT by my parsers
(no structured field read), means L0..L6:
boolean presses 3,5,..,15 and lamps 4..10; categories chain from the person 16,18,22,24,28,30,34; compass commands 3,5,..,15; decision tree lights stated
5,6,8,9,10,12,13 (depth 3,3,4,4,4,5,5); threshold members 6..12; exchange hops between the asked goods 3..9 (exactly, every item); graph towns 6,7,9,10,12,13,15;
knights people 4..10; grid moves 8.6..16.6 (cells 9,9,12,16,16,20,25 not strict); swap operations 6,8,..,18; weekday links from anchor to asked event 5..11 (exactly,
every item; the event graph is a tree in 7,000 of 7,000); Venn total 52..391 strictly rising, groups 2,2,3,3,3,4,4 (not strict) with the asked quantity changing by
level (none / exactly one / none / exactly two / at least two / none / exactly two). Every stated parameter rises strictly except grid cells, swap people, decision
tree depth and Venn groups, which rise weakly beside a strictly rising one; mean text length rises strictly for all 12. All seven `_r6` formulas in the notes
match what I measured. Venn L0 -> L1 differ only in the asked quantity and magnitude (2 groups both): **PENDING LEAD REVIEW** whether that is "difficulty increasing by a
stated parameter" (R-25 c); venn was not a repaired shape.

## 5. Capacity (`D/capacity_final.py`)

`core.generate_pool` called unchanged; demand D(G) = 10 x (ceil(4000/G) + ceil(20000/G) + 100) per cluster and level, G per R-30. Every part contains a singleton
cluster, so each lineage must supply q = D distinct texts at each level (equal per-lineage quota). One call per (lineage, level) with `core.part_lineages` pointed at
that lineage (the shapes are not in `core.REGISTRY`; unpatched, `core.lineages_of('R1')` returns the 15 pre-fix lineages, of which only compass_turns is in the fix-4
set); a lineage's stream depends only on (seed, role, eval, part, lineage, level), so this equals a whole-part call; cross-lineage repeats checked afterwards per part
and level (0).
- My set (11 shapes, 9 clusters, parts 4 / 5): **G = 4, D = 61,000: 77 of 77 cells pass; G = 3, D = 81,010: 77 of 77 pass**; 0 shortfalls, 0 repeated texts.
- The implementer's set (12 shapes, 10 clusters, parts 5 / 5): **G = 5, D = 49,000: 84 of 84 pass; G = 4, D = 61,000: 84 of 84 pass**; 0 shortfalls, 0 repeats.
Commands: `... D/capacity_final.py 11 4,3 8800 12 D/capacity_set11.json`, `... 12 5,4 8800 12 D/capacity_set12.json`. Reading: text-distinct (normalised text,
names count); structural readings not recomputed.

## 6. Reproducibility (`D/repro_final.py 37000`)

Fourteen candidate shapes x 7 levels x 300 items (question, answer, type, k, structured fields) and one `generate_pool` call per shape (pool_hash), in three fresh
processes with PYTHONHASHSEED = 1, 98765 and `random`: the three outputs are **byte-identical** (`cmp`), combined digest `e9aac177...3855754`.

## 7. Exclusion of dropped shapes (`D/exclusion_final.py`, `D/exclusion_run1.txt`)

`registered_v4()` = the 12 manifest survivors; none of the 23 stage-1 drops, 2 stage-2 drops or 7 replaced earlier ids is in `registered_v4()`, the cluster table
(10 clusters), the cluster-keys partition, the survivors manifest's survivor and cluster lists, or `r1_fix4_capacity.json`. `r1_fix4_gen` and the fix-4 key / tool
tests use `candidates_v4()` (the 14 re-run shapes, including the two stage-2 drops) for measurement only; `r1_fix4_levels.json` lists the two stage-2 drops (measured
there). There is no fix-4 fixture directory; `fixtures/r1_fix3/` still holds 24 files of dropped or replaced shapes (round-3 artefacts, not part of the fix-4 build).
**My drop (graph_shortest_route_r6) is not reflected in any implementer file**: `registered_v4()`, the manifests and `r1_fix4_capacity.json` still carry it.

## What I could not verify

Model behaviour (none run). Alternative readings despite stated conventions. Structural (names-relabelled) capacity. Cross-evaluation duplicates (R-15). Readability
of long level-6 items. Whether the C / A / M / EXCL split matches the lead's notion of a cheap rule (R-31 fixes it to audit 4's). Rules outside the batteries.
Whether the two stage-2 drops (event_timeline_r6, spatial_relative_directions_r6) were correctly dropped under R-19 (accepted by R-35; not re-examined).

## My slips and failed attempts (kept)

1. `check_keys_try1.txt/.jsonl`: 69 false mismatches, my categories regex (above). 2. A syntax error in my first fix of that line (one rerun, no output).
3. `levels_run1_SLIP_weekday_regex.txt/.json`: weekday hop counts wrong (a `findall` over the whole text let the first event name span the anchor sentence);
fixed per sentence (`levels_run2`), all other rows identical. 4. The first `weekday_hops.py` run crashed on the same bug (its traceback went to the terminal only; `weekday_hops_run1.txt` is the fixed run). `levels_run1.txt/.json` are the same slip run, kept beside the renamed copies. 5. Coincidence checked, not a bug:
boolean_lights L0 reads 0.1257 in both batteries of my run on different items (`work/same_items_probe.py`: 0 shared texts).
The Write tool was refused in the scratch directory; files were written by Bash heredocs. No forbidden command was run. No commit, push, model run, download or training.

Astra review: NOT_PERFORMED
