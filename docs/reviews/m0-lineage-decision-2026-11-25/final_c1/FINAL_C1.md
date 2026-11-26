# FINAL_C1: independent key check and final re-measurement of the C1 survivors after fix 4 (M0, ADR-0033)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`), arbor-auditor role. **Not Astra validation, not human approval.** Independent engineering and
  mathematical evidence only. I wrote none of the audited code; I repaired nothing and registered nothing.
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`. I read it as the uncommitted fix-4 state; during my
  audit the lead committed it as `7cd0ac5a` (22:33). Every C1 file I drew from has mtime <= 22:11:35, before my first draw (22:21), and the
  working tree equals HEAD for `studies/m0` (`git diff --stat HEAD -- studies/m0` empty), so the audited code is `7cd0ac5a`. SHA-256 (first 16):
  `lineages_c1_fix4.py` 2372627593ee6944, `lineages_c1_fix4_clusters.py` 2b8ae909126be5fa, `core.py` 07907f1e559f6814, `c1_fix3_battery.py`
  fb91e7992dbdde46, `c1_fix4_battery.py` e397cd096be39441, `s4_rules_v2.py` 3fa429c9fb8415e4, `s5_analyse_v2.py` b6ed2ec95426058a, `a3_shortcuts.py` 29ff7b07f9839245.
- Nothing written in any worktree. All files are under `experiments/_scratch/m0_final_c1_20261125/` (draws, rule records, capacity hashes) and its
  `deliver/` (scripts `f*.py`, `final_c1.json`, `outputs/`). Scripts start with `# ruff: noqa`; none imports an `*_analysis` module or the implementer's
  summary scripts (`c1_fix4_rules_table.py`, `c1_fix4_survivors.py`); the implementer's battery module was RUN, as the brief asked.
- Environment: macOS arm64, 18 cores shared (load 9-14), uv 0.12.15 `--locked`, venv Python 3.12.14; second interpreter `/opt/homebrew/bin/python3.15`
  (3.15.1). `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0` unless stated. Throwaway seeds (mine; no registered study seed): 9311 (draw: keys, rules,
  levels; 2,000 items per lineage and level), 9323 (battery, 2,000 per level), 9337 (reproducibility), 9341 (capacity per level), 9343 (capacity,
  levels sharing one `taken`), 1 (trials).

## Result

Under the rule classes R-31 counts (cheap: S + generic + most-frequent-key, and closed forms), pooled per R-32 over the implementer's draws
(audit-4 and audit-3 scripts on seed 71, battery seed 83; n = 400 per level each) and mine (n = 2,000 per level each), applied per lineage and
level over all shapes (R-34):

- **All 27 lineages STAY; 18 clusters (16 without the two variants).** Largest pooled excess: **0.111** (`merge_two_sorted_f3`, L0, audit-4
  `EFF_S`); next 0.108 (`postfix_evaluation` L0), 0.102 (`sieve_marking_f4` L0), 0.100 (`slices_f4` L0). Nothing is above 0.15 under either
  my strict class reading or the implementer's (which also counts the battery's mutation rules): the two readings give the same maxima except
  `shared_lists_f3` 0.040 vs 0.041 and `turtle_walk_f3` 0.005 vs 0.039.
- **Key mismatches: 0 / 94,500** (500 per lineage and level), each program extracted from the item TEXT by my extractor and run in its own fresh
  subprocess under 3.12.14 (PYTHONHASHSEED 0) and 3.15.1 (PYTHONHASHSEED 2718281): 189,000 processes, 0 errors, 0 timeouts, 0 stderr, 0 outputs not
  exactly one non-empty line, 0 disagreements between the runs, 0 frame mismatches, 0 static flags (one print, last top-level statement; no import,
  set, dict, hash, id, eval, I/O); the text program equals the rendered program in every item.
- **Capacity passes** at G = 9 (27,680), G = 8 (31,000) and G = 7 (35,300) for every lineage and level, against `core.generate_pool` as written,
  both per level alone and with one `taken` shared over the seven levels.
- **NEW (does not decide here):** `sieve_marking_f4` has an order-free closed form that answers **1.000 of items at every level** (16,800 items:
  14,000 mine, 2,800 the implementer's). If it is ruled a closed form as the flag-list shape's was, `sieve_marking_f4` and the cluster
  `C1.sieve_marking` drop: 26 lineages, 17 clusters (15 without the variants). PENDING LEAD REVIEW.

Surviving lineages (27), by cluster (the implementer's map; I agree with it, section 4):
B1 {string_build_f3, list_build_f3, nested_pairs_f3}; B2 {func_branch_f4, func_compose_f4}; B3 {slices_f4, string_methods_f3}; B5
{euclid_gcd_traced_f3, cond_chain_f3}; B6 {fib_like_f3, fib_shapes_recursive_f3, recursive_calls_r2}; B7 {bytecode_loop_f3, turtle_walk_f3};
B8 {bracket_matching_f3, postfix_evaluation}; single-lineage clusters C1.while_counter, C1.digit_peel, C1.run_length_scan, C1.sieve_marking,
C1.binary_search, C1.merge_two_sorted, C1.union_find_links, C1.circle_elimination, C1.shared_lists; variant clusters C1.fast_power_square_map
{fast_power_f4} and C1.counter_list_state_machine {counter_list_f3}. **With the variants: 27 lineages, 18 clusters (G = 9). Without: 25
lineages, 16 clusters (G = 8).**

## Per-lineage table

Keys = mismatches or other key problems / items checked. Pooled = largest pooled excess under the counted classes, with level and rule
(`a4` audit-4 script, `a3` audit-3 script, `battery` the implementer's). Partial = the same with partial-trace mutations allowed (NOT counted, R-31).
In-shape = largest pooled in-shape rate (NOT counted, R-34). Capacity: G9 27,680, G8 31,000, G7 35,300.

| lineage | cluster | keys | pooled (counted) | partial (not counted) | in-shape (not counted) | R-19 | levels | capacity | verdict |
|---|---|---|---|---|---|---|---|---|---|
| list_build_f3 | B1 | 0/3500 | 0.034 L2 `battery.sum|S.n_times_half` | 0.034 L2 | 0.090 L2 | none | distinct (cross-level repeats <= 0.002); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| nested_pairs_f3 | B1 | 0/3500 | 0.062 L0 `a4.MFsh` | 0.062 L0 | 0.142 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| string_build_f3 | B1 | 0/3500 | 0.004 L0 `a4.MF` | 0.147 L1 | 0.009 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| func_branch_f4 | B2 | 0/3500 | 0.062 L0 `battery.BEST_generic_cv` | 0.672 L2 | 0.023 L1 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise; 2 step(s) only in largest literal | pass G9/G8/G7 | STAYS |
| func_compose_f4 | B2 | 0/3500 | 0.095 L3 `battery.MF_cv` | 0.095 L3 | 0.110 L3 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise; 4 step(s) only in largest literal | pass G9/G8/G7 | STAYS |
| slices_f4 | B3 | 0/3500 | 0.100 L0 `a4.EFF_S` | 0.114 L0 | 0.301 L0 | answer (empty, via finish) - needed | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| string_methods_f3 | B3 | 0/3500 | 0.058 L0 `battery.text|S.word_lower` | 0.058 L0 | 0.008 L0 | answer (empty) needed; intermediate-empty not strictly needed (minor) | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| cond_chain_f3 | B5 | 0/3500 | 0.076 L0 `battery.tot|S.k_times_gcd` | 0.220 L0 | 0.107 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| euclid_gcd_traced_f3 | B5 | 0/3500 | 0.018 L1 `a4.MFsh` | 0.018 L1 | 0.021 L1 | trace-conditioned, not answer | distinct (cross-level repeats <= 0.000); 6/6 steps rise; 4 step(s) only in largest literal | pass G9/G8/G7 | STAYS |
| fib_like_f3 | B6 | 0/3500 | 0.088 L0 `battery.all|S.plain_fibonacci_a` | 0.088 L0 | 0.038 L5 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| fib_shapes_recursive_f3 | B6 | 0/3500 | 0.015 L0 `battery.BEST_generic_cv` | 0.015 L0 | 0.012 L0 | none | distinct (cross-level repeats <= 0.003); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| recursive_calls_r2 | B6 | 0/3500 | 0.013 L0 `a4.MFsh` | 0.027 L0 | 0.020 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| bytecode_loop_f3 | B7 | 0/3500 | 0.069 L2 `a4.EFF_S` | 0.091 L3 | 0.080 L3 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| turtle_walk_f3 | B7 | 0/3500 | 0.005 L0 `a4.MFsh` | 0.049 L0 | 0.011 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| bracket_matching_f3 | B8 | 0/3500 | 0.035 L0 `a4.EFF_S` | 0.063 L0 | 0.066 L1 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| postfix_evaluation | B8 | 0/3500 | 0.108 L0 `a4.EFF_S` | 0.108 L0 | 0.065 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| binary_search_f3 | C1.binary_search | 0/3500 | 0.073 L0 `a4.EFF_S` | 0.073 L0 | 0.171 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| circle_elimination_r2 | C1.circle_elimination | 0/3500 | 0.094 L0 `battery.MF_cv` | 0.271 L0 | 0.111 L0 | structural (never fired) | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| counter_list_f3 | C1.counter_list_state_machine | 0/3500 | 0.059 L0 `battery.counts|S.uniform` | 0.059 L0 | 0.067 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| digit_peel_f3 | C1.digit_peel | 0/3500 | 0.072 L0 `a3.rev_bN|F.closed` | 0.072 L0 | 0.032 L1 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| fast_power_f4 | C1.fast_power_square_map | 0/3500 | 0.054 L6 `battery.MF_cv` | 0.054 L6 | 0.048 L5 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| merge_two_sorted_f3 | C1.merge_two_sorted | 0/3500 | 0.111 L0 `a4.EFF_S` | 0.111 L0 | 0.127 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| run_length_scan | C1.run_length_scan | 0/3500 | 0.016 L0 `a3.MF_shape_cv` | 0.117 L1 | 0.039 L0 | answer (empty) - needed | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| shared_lists_f3 | C1.shared_lists | 0/3500 | 0.040 L0 `a4.EFF_S` | 0.150 L6 | 0.062 L0 | structural, not answer | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| sieve_marking_f4 | C1.sieve_marking | 0/3500 | 0.102 L0 `a4.MFsh` | 0.102 L0 | 0.102 L0 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS (NEW closed form, see 5) |
| union_find_links_f3 | C1.union_find_links | 0/3500 | 0.036 L0 `battery.parents|S.naive_node_links` | 0.314 L0 | 0.018 L5 | none | distinct (cross-level repeats <= 0.000); 6/6 steps rise | pass G9/G8/G7 | STAYS |
| while_counter_f3 | C1.while_counter | 0/3500 | 0.024 L0 `battery.BEST_generic_cv` | 0.024 L0 | 0.021 L0 | none | distinct (cross-level repeats <= 0.006); 6/6 steps rise; 3 step(s) only in largest literal | pass G9/G8/G7 | STAYS |

## 1. Keys (`f2_keys.py`)

Extractor: the text between the fixed frame line `Here is a Python program.` plus a blank line and the blank line before `What exactly does it
print? It prints a single line.`; an item whose text does not match the frame is reported (none). One process per program (`python -I -S -c`,
env PATH + PYTHONHASHSEED only, 10 s timeout). Totals above; nothing raised, nothing failed to terminate, no hash-order or other non-determinism
(two interpreters, two hash seeds, identical output), and every question identifies one value (one print, one line). The static checker was
self-tested on seven programs before use (`outputs/f2_static_selftest_out.txt`). Hazards are Python-defined (negative `//`, `%`, slice bounds) as
audit 4 recorded; I found no new one. Run: 819.5 s.

## 2. Cheap rules, pooling, closed forms (`f1_draw.py`, `f3_a3_run.py`, `f4b_pool_v2.py`, `f5b_closed_forms_v2.py`)

- Re-run on my draw (seed 9311, 2,000 per lineage and level, the five fix-4 ids written under the ids the scripts know, as the implementer did):
  audit-4 `s4_rules_v2.py` + `s5_analyse_v2.py` (0 parse failures, every lineage), audit-3 `a3_shortcuts.py` (every lineage ran under its old id
  except `while_counter_f3`, whose old parser fails and which ran under its own id with generic rules only: the same failure in the implementer's
  run), and the implementer's battery (`python -m studies.m0.c1_fix4_battery --per-level 2000 --seed 9323`).
- The implementer's inputs: `s5_72.json`, `battery83b.json`, `a3run72/` in `experiments/_scratch/m0_fix4_c1_20261125/`. I re-derived `s5_72.json`
  from their raw `rules72/` with `s5_analyse_v2.py`: identical. Their `gen72` aliased files are fix-4 builds (func_branch calls 2,2,2,3,3,4,4 by
  level; sieve never prints the list; fast_power always prints res; slices string length 10-25). There is no replicate seed on their side (gen71
  and gen72 are both seed 71), so each pooled figure is 400 of theirs + 2,000 of mine (2,400 items).
- Classes (R-31): counted = audit-4 `EFF_S`, `MF`, `MFsh`, every S.* and F.* rule's level share; battery `MF_cv`, `BEST_generic_cv` and its S.*/F.*
  rules except control rules `C.*` and the rules that run a mutated program (`S.all_ones_start, no_halving, no_c_term, thr0_run, run_inc_1,
  naive_copy, no_skips, always_skip, no_turns, no_back, no_mod, ignore_step`; read from the `mut()`/`regex_run()`/`run_src()` call sites);
  audit-3 `MF_cv`, `MF_shape_cv`, `BEST_generic_cv` and its rules except its four mutation rules. Not counted: audit-4 M.* / `EFF_SM`, H.*.
- **If partial-trace mutations counted** (pooled `EFF_SM`, battery mutation rules): func_branch_f4 0.672 (L2, `M.drop_even_branch`),
  union_find_links_f3 0.314 (L0), circle_elimination_r2 0.271 (L0), cond_chain_f3 0.220 (L0), **shared_lists_f3 0.1503 (L6; 0.117 theirs, 0.157
  mine)** would drop: **22 lineages, 15 clusters (13 without the variants)**; clusters lost C1.union_find_links, C1.circle_elimination,
  C1.shared_lists. This differs from the implementer's list (22 / 16 / 14): they had string_build_f3 (0.155 on their draw) instead of
  shared_lists_f3; pooled, string_build_f3 is 0.1475 (L1) and stays. Both are within one standard error (about 0.007) of the bound.
- Audit-3's mutation rules score a mutation that changes nothing as a hit (bytecode_loop_f3 L0 `S.no_skips` 1.000, turtle_walk_f3 L1 `S.no_back`
  0.683); these are artefacts and are excluded from every column (the implementer excluded them too).
- **In-shape rates above 0.15 (pooled; reported, not counted):** slices_f4 shape `sum_list`, most frequent key, 0.255-0.301 at every level (the key
  is `0`: 27.8 % of sum_list items sum an empty slice); binary_search_f3 shape `probes_half`, most frequent key, 0.171 (L0) and 0.167 (L1). The
  implementer's other two (circle_elimination_r2 0.198, nested_pairs_f3 0.151) pool to 0.111 and 0.142.
- **Closed forms (about 50 minutes; `f5_closed_forms.py` v1 kept, `f5b_closed_forms_v2.py`):**
  - **NEW, sieve_marking_f4: `F.order_free_strikesum` = 1.000 at every level** on my draw (2,000 per level) and on the implementer's (400 per
    level). The indices that run a strike pass are exactly those i with init[i] = 1 and no initially flagged d < i with d | i and i >= start(d)
    (start = 2d or 3d, stated), because a struck index's multiples beyond its start are struck by the divisor that struck it; the answer is then
    the sum over those i of the arithmetic series start(i), start(i) + i, ... < n, with no pass simulated. It is the same order-free divisor test
    that audit 4 found for the flag-list shape (which the implementer dropped as a closed form). The audit-4 script's rule for this shape
    (`M.use_initial_flags`) ignores the clearing and scores 0.00-0.01, which is why it was missed. What it would do: if counted as a closed form,
    sieve_marking_f4 drops and with it the single-lineage cluster C1.sieve_marking (26 lineages, 17 clusters, 15 without the variants; G = 8 or
    7). Whether a divisor test is "without tracing" was left PENDING LEAD REVIEW by audit 4; it is the lead's ruling.
  - NEW, func_branch_f4 (partial-trace class): `S.always_high_branch` (every call takes the `x > t` branch) is right in 0.43-0.51 (L0-L1) and
    0.24-0.47 (L2-L6) of items: most call arguments exceed the threshold. It is a mutation (one feature ignored), so it is not counted; it adds
    nothing to the drop list above (func_branch_f4 is already on it).
  - fast_power_f4: pow(b, e, m) 0.010-0.048, pow terms plus c 0.05-0.09, last-b power <= 0.034: none. counter_list_f3: residue histogram <= 0.048,
    prefix-sum histogram <= 0.033, uniform <= 0.055, style-0 machine on branching items <= 0.045: none. slices_f4: negative steps read as positive
    0.02-0.06 (a convention error, class H). func_compose_f4: nothing found beyond the program itself (f(f(x)) = a^2 x + ab + b is evaluating it).

## 3. Answer-conditional rejection (R-19; retry reasons counted by wrapping the shared finish in my process, `f1_draw.py`; 14,000 draws per lineage)

| lineage | what is rejected | on the answer? | needed for a well-posed item? | per 14,000 |
|---|---|---|---|---|
| run_length_scan | `long` shape with no run of length >= 2 | yes (empty answer) | yes: an empty key is not gradable (`scoring.in_grammar` returns False for '') | 46 |
| slices_f4 | empty string answer (both slices empty), via the shared finish | yes (empty) | yes, same reason | 459 |
| string_methods_f3 | empty final answer (finish) / empty intermediate string (builder) | final: yes; intermediate: no, on state | final yes; intermediate not strictly (it avoids `r.choice('')` in a later replace) - PENDING LEAD REVIEW, minor | 37 / 22 |
| euclid_gcd_traced_f3 | equal operands; fewer than max(4, 3 + L // 2) rounds | no (trace length) | rounds >= 4 yes (the rsum shape's R range); the higher minimum at L >= 4 is a difficulty condition - PENDING LEAD REVIEW (R-13 wording) | 28,175 |
| shared_lists_f3 | an alias of a name to itself | no (structure) | yes (the statement says nothing) | 3,248 |
| circle_elimination_r2 | fewer than 4 live flags | no (structure) | not strictly (3 would do); never fired | 0 |
| the other 21 | nothing of their own; the shared finish never fired | - | - | 0 |

The shared finish's other conditions (program error, upper case, padding, double space, final full stop) never fired for any survivor.

## 4. Clusters (R-20)

`fast_power_f4` and `counter_list_f3` each sit alone in their own clusters (`C1.fast_power_square_map`, `C1.counter_list_state_machine`), not
under C1.fast_power / C1.counter_list. `fast_power_f4` prints `res` in 14,000 of 14,000 of my items (only that shape); `sieve_marking_f4` never
prints the flag list (14,000 of 14,000). The implementer's own `check_consistency()` returns no problem, and my recomputation (every written C1 id
minus the superseded, PROPOSED, NOT REGISTERED and dropped ones) equals the 27 and the map. Each survivor's cluster is its program's algorithm; I
have no disagreement with the map. The borderline merges audit 4 listed and did not make (B7~B8 interpreters, fast_power_f4~digit_peel bit scan,
counter_list_f3~B7 state machine) remain borderline; under strict merging they would lower the count by up to 3 (18 -> 15).

## 5. Levels (`f7_levels.py`; my criterion, not the implementer's 99 % shared-stream test)

On 2,000 items per level: every level has at least 99.75 % distinct normalised texts, and at most 0.65 % of a level's items occur at another level
(while_counter_f3; 0 for 22 lineages): no level pair is indistinguishable. Every step L -> L+1 of every lineage rises in at least one feature
(one-sided Mann-Whitney z >= 3.09: executed line events, characters, AST nodes, largest literal, longest literal, calls, statements). The feature
I tied to each docstring's stated parameter rises at every step except bytecode_loop_f3 L1 -> L2 (9 pairs at both levels as stated; the step
adds the `mod` opcode: characters z 44.7, AST nodes 56.6). Nominal steps (rise only in the largest literal, executed steps flat): func_compose_f4
L0->L1, L3->L4, L4->L5, L5->L6 (z 3.3-6.9); euclid_gcd_traced_f3 L0->L1, L1->L2, L2->L3, L4->L5; while_counter_f3 L3->L4, L4->L5, L5->L6;
func_branch_f4 L3->L4, L5->L6. They are distinct and the stated parameter rises, but the difficulty difference is small. Steps where one feature
falls while others rise: bytecode_loop_f3 L3->L4 (largest literal), L4->L5 (statements), string_build_f3 L4->L5 (AST nodes).

## 6. Capacity (`f6_capacity.py`, `f6b_collisions.py`, `f6d_capacity_all_levels.py`)

`core.generate_pool("C1", "A", role, seed, size, level_mix, taken, shortfalls=[])` is called as written; the only substitution, in my process, is
`core.part_lineages` returning the one lineage, because no fix-4 survivor is in `core.REGISTRY` (none of the 27 is registered, so the builder
cannot reach them unaided). Text de-duplication is `core.normalise` of the question (NFKC, case fold, whitespace), budget 40 x count + 1000.

- Per level alone (seed 9341, count 35,300): all 189 lineage-levels supplied 35,300 text-distinct items; the attempt at which each demand was
  reached is within its own budget for G = 9, 8 and 7 (worst 1.03 attempts per item, while_counter_f3 L0; budget is 40 per item).
- 12,700 texts were drawn at two levels of the same lineage (overlapping parameter ranges); none occurs in two lineages. Because
  `generate_pool` shares `taken` across the levels of a pool, I re-ran it (seed 9343) once per lineage over all seven levels with one `taken`,
  size 7 x D: **no shortfall at D = 27,680 (G = 9), 31,000 (G = 8) or 35,300 (G = 7)** for any of the 27 lineages. (My first summary, `f6b`,
  subtracted cross-level collisions from a draw of exactly 35,300 and marked 46 lineage-levels as failing G = 7; that was a wrong conservative
  rule, superseded by f6d.)
- So: with the variants (18 clusters) G = 9 and one lower G = 8 pass; without (16) G = 8 and G = 7 pass. Under the NEW sieve finding without the
  variants (15 clusters) G = 7 passes and G = 6 (41,010) was not measured; under the partial-trace reading (15 / 13 clusters) G = 6 and 5 (49,000)
  were not measured. Per lineage, not per cluster: every lineage passes on its own (R-28), so no per-cluster-builder result is used.
- Not measured: the stricter readings of a distinct item (R-16, unruled; audit 4 found them failing for most clusters).

## 7. Reproducibility and exclusions (`f9_repro_pool.py`, `f8_consistency.py`)

Two fresh processes with PYTHONHASHSEED 1 and 987654321: my draw (seed 9337, 200 per level, 27 files) is byte-identical after decompression and
its retry statistics are equal; `generate_pool` pools for all 27 lineages (1,400 items each, seven levels, one shared `taken`) give the same
`pool_hash` set (SHA-256 of the set 5723dbc92bb0325a...). Dropped lineages and shapes are excluded everywhere the fix-4 set is built: the six
manifests that list ids (survivors, clusters, capacity_raw, exec, levels_final_set, rules_final_set) each hold exactly the 27, no dropped or
superseded id; `DROPPED_AFTER_REMEASURE` is empty; the dropped flag-list and base/bsum shapes never occur.

## Discrepancies with the implementer

1. Missed closed form: sieve_marking_f4 strike-sum is answered by the order-free divisor test in 1.000 of items (implementer: "strike-sum kept: 0.110").
2. Partial-trace drop list: shared_lists_f3 (pooled 0.1503) instead of string_build_f3 (pooled 0.1475); same totals in lineages (22), one more
   cluster lost (15 / 13 instead of 16 / 14).
3. In-shape above 0.15: circle_elimination_r2 and nested_pairs_f3 pool below (0.111, 0.142); slices_f4 0.301 and binary_search_f3 0.171 confirmed.
4. Largest counted excess: 0.111 merge_two_sorted_f3 L0 pooled (implementer 0.115 slices_f4 L3 on 400 items; pooled slices_f4 maximum 0.100).
5. Capacity: the implementer drew each lineage-level with a fresh `taken`; with one `taken` over the levels (as `generate_pool` does) it still passes.
6. Levels: my test finds the same nominal steps as theirs for func_compose_f4 and more (euclid, while_counter, func_branch); all are distinct.

## My own errors and failed attempts (kept)

- First trial draw (`outputs/FAILED_trial1_draw_meta_double_counted.json`): my finish wrapper was installed twice in a worker that handled two
  lineages, double-counting retry reasons (negative 'builder' counts). Fixed (wrap once) before the main draw; the items were not affected.
- `f5_closed_forms.py` v1: counter_list `M.style0_everywhere` scored style-0 items, where it IS the program (0.33-0.39); v2 scores it only on
  branching items (<= 0.045).
- `f4_pool.py` v1 put audit-3's no-op mutation artefacts in the partial-trace column (bytecode 1.000, turtle 0.683); v2 separates them. v1 also
  did not list `S.all_ones_start` as a battery mutation rule (added; no effect on any maximum).
- `f6b_collisions.py` G = 7 "fails" (above): wrong conservative rule, superseded by `f6d`.
- I started two overlapping bounded wait loops on the same output file; both ended by themselves. Some small helper checks (trial key check,
  inline summaries) ran under `/opt/homebrew/bin/python3` (3.15.1) directly rather than `uv run`; every reported number comes from a `uv run
  --locked python` run listed below except the key check's subprocesses (explicit interpreters by design) and the inline summaries of JSON outputs.
- No forbidden command was run (no rm, mv, chmod, sed -i, pkill, ruff --fix, sudo); nothing was deleted. A stale process from another session
  (pid 47842, a zsh running `cat $D` after writing a fix-3 cluster file) is still alive; I did not signal it.

## What I could not verify

No 50-item human-style read. No second solver (my key check is an independent re-execution, not a tree walker). The implementer has one draw per
script (no replicate seed), so the pool is 2,400 items per lineage and level; figures near the bound (shared_lists_f3 0.1503, string_build_f3
0.1475 under the partial-trace reading) are within sampling error. The classification of the battery's simulated-alternative rules (e.g.
`S.naive_node_links`, `S.pop_any_closer`) as cheap rather than partial-trace is my reading; none exceeds 0.08. Capacity at G = 6 and 5 and under the
R-16 readings was not measured. Whether an empty answer could be made gradable by a wording change (R-25 (b)) is the lead's question. The
cross-evaluation map was not reviewed.

## Commands (cwd = the audited worktree; `$D` = `experiments/_scratch/m0_final_c1_20261125`; `A4`, `A3` = the audit4_c1 / audit3_c1 directories)

```
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python $D/deliver/f1_draw.py --seed 9311 --per-level 2000 --out $D/gen9311 --workers 10
PYTHONDONTWRITEBYTECODE=1 uv run --locked python $D/deliver/f2_keys.py $D/gen9311 500 $D/keys9311.json <venv py3.12>:0 /opt/homebrew/bin/python3.15:2718281 12
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python -I $A4/s4_rules_v2.py $D/gen9311 $D/rules9311
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $A4/s5_analyse_v2.py $D/rules9311 $D/s5_9311.json
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python $D/deliver/f3_a3_run.py $D/gen9311 $A3/a3_shortcuts.py $D/a3run9311
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python -m studies.m0.c1_fix4_battery --per-level 2000 --seed 9323 --only <the 27, under the ids the battery knows> --out $D/battery9323.json --workers 6
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $A4/s5_analyse_v2.py <impl scratch>/rules72 $D/s5_72_rederived.json      # identical to their s5_72.json
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $D/deliver/f4b_pool_v2.py <impl scratch> $D $D/f4b_pooled_v2.json            # v1: f4_pool.py -> f4_pooled.json
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $D/deliver/f5b_closed_forms_v2.py $D/gen9311 $D/f5b_closed_forms_v2_9311.json   # and on <impl scratch>/gen72; v1 f5_closed_forms.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python $D/deliver/f6_capacity.py --seed 9341 --count 35300 --out $D/cap9341 --workers 6
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $D/deliver/f6b_collisions.py $D/cap9341 $D/f6b_capacity_summary.json
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python $D/deliver/f6d_capacity_all_levels.py --seed 9343 --out $D/f6d_capacity_shared.json --workers 6
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python -I $D/deliver/f7_levels.py $D/gen9311 $D/f7_levels_9311.json
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python $D/deliver/f8_consistency.py $D/gen9311 $D/f8_consistency.json
for HS in 1 987654321: PYTHONHASHSEED=$HS uv run --locked python $D/deliver/f9_repro_pool.py 9337 1400; PYTHONHASHSEED=$HS uv run --locked python $D/deliver/f1_draw.py --seed 9337 --per-level 200 --out $D/gen9337_hs$HS
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -I $D/deliver/f10_assemble.py $D $D/deliver/final_c1.json
```
Outputs: `deliver/outputs/` (copies of every summary named above; large draws and rule records stay in `$D`).

Astra review: NOT_PERFORMED
