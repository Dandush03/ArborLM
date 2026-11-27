# Stage 4 (capacity) of ADR-0033 addendum 1, section 4A: code notes

Self-checks only: not independent review, not Astra validation, not human approval. Nothing here was run on the
capacity stream of record (label `capacity`); the partition of record does not exist yet. Text = the approved
addendum at `2c944302`.

Files (new, to be copied to `studies/m0/registration/`): `__init__.py`, `distinct_key.py`, `capacity.py`,
`pool_builder.py`, `test_capacity.py`, `timing_probe.py`, this file. Standard library only.

Checks as run (from the implementation worktree root, staged files put on the package path by the test itself):
`PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python -m pytest -p no:cacheprovider --import-mode=importlib <dir>/test_capacity.py`
and `uv run --locked ruff check --config pyproject.toml <dir>`. The 5 real-lineage tests use the label
`capacity-smoke` (monkeypatched) and targets of at most a few hundred keys.

## 1. Sentence-to-code map

| Text | Code |
|---|---|
| stage 4: "start with S, the candidate lineages of e whose cluster is in p" | `capacity.build_parts` (candidate list, partition `cluster_part`, map `clusters`) |
| "a fresh stream `stream(400002, "capacity", e, id of x, str(v))`" | `capacity.stream_labels`, `count` (uses `studies.m0.core.stream`, i.e. the derivation of section 4); `SEED`, `LABEL` |
| "a set of keys that starts empty and belongs to x and v alone" | the `seen` set created per `count` call; nothing is shared (tests: `test_no_set_is_shared_...`) |
| "items are built one after another with the builder's own `build_item`, as `draw_items` does" | `capacity._advance` (the loop of `draw_items`, same order: budget check, `build_item`, key, discard) |
| "an item whose key is already in the set is discarded" | `_advance`: `k in seen: continue`; key = `distinct_key.item_key` |
| "stops when the set holds T keys; or attempts exceed 40 x T + 1,000; or `build_item` gives up after 500 retries" | `_advance` loop condition, `n > budget`, `except RuntimeError ... "consecutive retries"` |
| "c(x, v, T) is the number of keys then in the set" | `Draw.count` |
| "No set ... shared between lineages, levels, clusters, parts or roles; the part is not a label" | stream labels have no part; one `seen` per call |
| "One round. G = clusters with at least one lineage in S; k_c = lineages of c in S" | `run_stage4.start_round`, `_round_record` |
| "(i) fails if at any of the seven levels c(x, v, D_lin(G, k_c)) < D_lin(G, k_c)" | `_round_record` (own demand), `demand_lin` |
| "(ii) for a cluster all of whose lineages pass (i) ... union ... below D(G) at any level, all its lineages fail" | `_round_record`: `union_evaluated` only if no lineage of the cluster failed (i); `_union_count`; `demand` |
| "(iii) a lineage whose two solvers disagree on any item built in this stage fails" | `_advance` (every attempt) + `_check`; `_round_record` (solver_disagreement) |
| "all failing lineages removed at once; run again with the new G and k_c, until a round removes nothing; never brought back" | `run_stage4` loop; `_Part.live` only shrinks |
| "a later round's higher target is drawn again from the start of the same stream with that target's own budget" | `count` (from the start, or equivalently from a cached prefix of the same stream: section 3 here) |
| "the eight evaluation parts are independent" | one `_Part` per (e, p); parts progress as their own cells finish (no waiting on other parts) |
| stage 5 "lineages left in S are registered; G_e,A, G_e,B; the family count" | record fields `registered`, `G_registered`, `families`, `n_families` per part |
| stage 6 "the rounds of stage 4 with every count" | the JSON record: every round, G, D(G), k_c, D_lin, every count (`count`, `target`, `ended`, `attempts`), every union, every removal with its reasons |
| section 10 A item 1 (key, decision (i)) | `distinct_key.key_text`, `item_key` |
| A item 2 `D(G) = 10 x (ceil(4,000/G) + ceil(20,000/G) + 100)` on each of the seven levels | `capacity.demand`; `LEVELS` |
| A item 4 `D_lin(G, k) = 10 x (ceil(ceil(4,000/G)/k) + ceil(ceil(20,000/G)/k) + ceil(100/k))` | `capacity.demand_lin` |
| B, "option not taken", `D_w(L)` | `capacity.demand_w` (comparison only; used nowhere) |
| A item 5 "no cluster at some levels only" | (i) and (ii) fail a lineage or a cluster for ALL levels; nothing is registered per level |
| section 13 item 16 "each part's own cluster count" | `G = len(live)` of that (e, p) |
| section 8 "in stage 4 the two solvers must agree on every item built" | `RealSource.solver` loads `solvers2/solver2_*.py`; `_check` compares the builder's `Item.answer` (first solver) with `SOLVERS[lid](question, structured)` |
| B items 1 to 4 | `pool_builder.clusters_in_order`, `plan_pool` (uses `core.allocate`) |
| B item 5 streams | `pool_builder.build_pool`: `stream(seed, role, salt_label, e, p, lineage id, str(level))` |
| B item 6 uniqueness, order | `build_pool` -> `core.draw_items` with the shared `taken` set; order clusters, levels, lineages; shortfall -> `CapacityShortfall` or `shortfalls` |
| B item 7 M0 draw | `pool_builder.m0_draw_by_cluster` |
| B item 8 record | `PoolItem.cluster`, `summarise`, `pool_hash` |

## 2. What "names relabelled" means (`distinct_key.py`)

The key is the rendered question with names replaced, in order of first appearance, by placeholders; nothing
else is changed (no case folding, no whitespace or Unicode normalisation: the text says "exact duplicates of
the rendered question"). It is stored as the first 16 bytes of the SHA-256 of that text (a collision among
a few hundred thousand keys has probability below 1e-27).

* **R1, R2, M1.** A name is a whole-word occurrence (ASCII letter/digit boundaries) of an entry of the word
  lists in `studies/m0/vocab.py`: people `NAMES`, places `TOWNS`, events `EVENTS` (without the leading "the "),
  objects `OBJECTS`, pets `PETS`, invented words `PSEUDO`. `NAMES` and `TOWNS` match case-sensitively; the
  lower-case lists match with the first letter in either case. A plural `s`/`es` after a name stays in the text;
  so does a possessive `'s`; "a"/"an" before a name is written "a" (agreement, not part of the name). Longest
  entry first ("book sale" before "book"). One counter for all classes. NOT names (left as they are, that is reading (ii)):
  `COLOURS`, `SHAPES`, `MARKS` and any word of a name list that is also one of those ("orange"), letters, numbers, weekdays,
  activity words, every other word. One lineage uses a vocabulary word as DATA: `R2.caesar_shift`
  shifts invented words, so its invented words are not relabelled (`DATA_VOCABULARY`); evidence in section 5, choice 9.
* **C1.** A name is an identifier of the program the question shows: variables, parameters, function names
  (`ast` Name/arg/def), except builtins (`dir(builtins)`) unless the program binds one; attribute names after a dot
  (methods), string literals, numbers, operators, layout and the frame sentences are untouched. The program
  source is found in the question as `render(structured["program"])` (`ValueError` if it is not there).
* The word lists come from `studies/m0/vocab.py` (the builders import them: 38 lineage modules use `NAMES`, 16 `TOWNS`, 17 `OBJECTS`,
  20 `PSEUDO`, 5 `EVENTS`, 2 `PETS`). Inline word lists inside a builder (activities, weekdays, hobbies) are not names here.

Tests: names-only differences give one key (people, places, events, objects, invented words, plural, possessive, article,
hyphenated entry); every other difference listed (number, order, punctuation, whitespace, case, repeated-name pattern, labels,
letters, weekdays) gives another; C1 variants likewise; hash-seed independence in two subprocesses. Checks on real
lineages: renaming every name one-to-one in question, structured form and key answer keeps the key and the second solver's answer
(3 items for each of 5 lineages in the test; in a scratch run 84 items, 12 per level, for each of the 46 R1/R2/M1 candidates: 0 failures
where names occur; with `R2.caesar_shift` NOT excepted, 84 of 84 fail); in a scratch run on 7,280 C1 items of the 26 survivors, no group
of items with the same `alpha_key` (`c1_batch1_capacity.py`) gets two keys.

## 3. The prefix property (answer: provable given one assumption; cache across targets implemented)

Claim. For a fixed (x, v) let k_1, k_2, ... be the keys of the items at attempts 1, 2, ... of the stream, up to the attempt g at which
`build_item` gives up (if any). Let L be the keys in order of first occurrence and u(n) the number of distinct keys among the
first n attempts. The draw for target T stops at the first of: the attempt a_T where u first reaches T; the budget attempt
B(T) = 40 T + 1,000; the give-up. a_T, B(T) are non-decreasing in T and g does not depend on T, so every draw is a prefix of the same
sequence and its key set is the first c(T) elements of L, with c(T) = u(stop). Hence:

* If the smaller draw reached its target, its set is the first T keys of L, which are the first T keys of any larger draw
  (a larger draw stops no earlier). So the first T keys of a larger draw equal the smaller draw's set.
* If the smaller draw stopped on its budget or on the give-up, its set is the prefix of L of length u(B(T)) (or u(g-1)); the larger
  draw, with the larger budget, contains it as a prefix of L and may hold more keys. The budgets differing does not break the property:
  it only moves where each draw stops.
* So c(T) is non-decreasing in T. (This is consistent with the fourth checker's sequence that counts 99 at T = 100 and 200 at T = 200;
  it also shows that "a lineage that fails a target also fails every larger target" can fail: a lineage can fail T and pass T' > T.)

Assumption (P1): the builder is a pure function of the stream state (no clock, environment, global counter, or iteration over a
set of strings under hash randomisation). It cannot be proved by reading 67 builders. Evidence (self-check): on every lineage
of the survivor list (82), levels 3 and 6, 30 keys, two processes with `PYTHONHASHSEED` 1 and 2 give identical keys; on 3 real
lineages at levels 0 and 6 a draw continued from a cache equals a draw from the start, and the lower target is a prefix of the higher.
The toys of the tests are checked against `reference()`, an independent re-implementation of the text.

What the code does with it. `TraceCache` (optional: `--cache-dir` with a mandatory `--cache-tag`) stores, per (lineage, level),
the stream itself: keys in order of first occurrence with the attempt of each, the attempts at which the solvers disagreed, and the
generator state after the last attempt. A request for T is answered from the longest stored trace if T is reached, or its own budget, or the
give-up lies inside it (`_derive`); otherwise the stream is continued from the stored state to the new target's own budget. Either way
the answer is the one a draw from the start would give (the tests assert equality with `reference()` and with a draw without cache,
on toys and on real lineages). A trace made with the solver check does not answer a request without it and the other way round;
a file with another tag, stream, key version or checksum is ignored; files are never overwritten or deleted. If P1 is doubted for a lineage,
run without `--cache-dir`: the record is the same, and costs the time of section 7. The tag must name the generators and the key
function (suggest the commit that holds them).

## 4. Where the text left a choice (each: what I did; direction)

1. **Solver check on every attempt**, discarded duplicates included, at every round (a higher target draws more attempts, each checked). "Any item built in this stage". Least favourable to passing.
2. **What a disagreement is**: an exception, a timeout (20 s per item, as the pair audit), a non-`str` answer, or `answer != Item.answer` as exact strings. The pair audit compared `str(a) != str(key)` and kept errors apart; here an error or a non-`str` is a disagreement. Least favourable.
3. **(ii) is read on a cluster whose lineages all pass (i)** even if one of them fails (iii), and the union uses its key sets as drawn. Least favourable (one more way for a cluster to fail).
4. **"Seed position" of a disagreement** = the 1-based attempt number in the stream of (lineage, level); the record has the first position per level, the count of items, and up to 20 details (every position is in the cache trace). The text does not define it; the index among kept keys is the other reading.
5. **Give-up**: only a `RuntimeError` whose message contains "consecutive retries" ends the draw; any other exception stops the run (a defect, not a capacity fact). The failed attempt counts as an attempt (`attempts` = g) and builds no item.
6. **Attempts exceed the budget**: attempts 1..40 T + 1,000 are executed (the check is before the build, as in `draw_items`).
7. **All seven levels are drawn for every lineage in every round**, also after a failure at an earlier level (the record keeps every count); `levels=` exists only for tests and is written into the record (`reduced_levels`).
8. **Key digest** 16 bytes, not the text, to hold up to 240,000 keys per cell in memory and on disk. Equality of keys is equality of digests.
9. **Which words are names** (the text says "names"): I took every class of the committed lists that the builders draw entity names from (people, places, events, objects, pets, invented words) because the narrower reading (people only) is more favourable to passing; I did NOT relabel labels or letters (reading (ii)). **One exception goes the favourable way**: `R2.caesar_shift` keeps its invented words, because there they are the text the solver shifts and not names (84 of 84 renamed items change the answer if they are relabelled, and the key would equate items with different answers). It is a judgement about one lineage; it is listed in `DATA_VOCABULARY` and is the lead's to confirm or remove. Template words that coincide with a list entry (for example "book" in `M1.fraction_remainder_r3`, "taken" in `M1.painted_cube_r3`, "never" in `R2.min_heap_ops`) are relabelled; they are constant in every item, so this changes no key comparison.
10. **Lower-case lists match with the first letter in either case** (a name at the start of a sentence); `NAMES`, `TOWNS` match exactly. One counter for all classes (a person and a town swapped give one key; they cannot swap within a template, so no practical effect, and it is the less favourable option).
11. **C1 names**: variables, parameters, function names; builtins not renamed unless bound. The text says "names" only. The existing `alpha_key` does the same on the AST; mine works on the source text so that layout and literals stay in the key.
12. **Exact text, no normalisation** in the key (text: "exact duplicates of the rendered question removed"). The builder's own test normalises (NFKC, case-fold, whitespace); two questions that differ only in case or spacing are two keys here. No generator produces such pairs that I know of; I did not measure it.
13. **`part` and `ident` passed to `build_item`**: "-" and `<id>/capacity/L<level>/<keys so far>` (same shape as `draw_items`); builders do not read them.
14. **Stage 4 record** shape, input forms (`{"candidates": {e: [ids]}}`, the partition code's `cluster_part`, the map's `clusters`), output refused if the file exists; unknown evaluation, candidate not in a cluster, cluster without a part, duplicate candidate: `ValueError` (stop, nothing guessed).
15. **Parts progress independently** (a part's next round is submitted as soon as its own cells are done). Results do not depend on it (test).
16. **Pool builder**: `PoolItem` (new class: the fields of `core.Item` plus `cluster`) because `core.Item` is frozen and has no cluster field; `build_pool` builds one role at a time and the caller owns the order of roles and the shared `taken` set (item 6); `draw_items(..., allow_short=True)` then a shortfall is an error (`CapacityShortfall`) unless a `shortfalls` list is given, as `generate_pool` does; a quota of 0 draws nothing and consumes no randomness. A part with no cluster gives an empty pool.
17. **Tuning draw**: if built one call per level the remainder goes to the earliest clusters at every level (text, review note); `plan_pool` prints the counts, no rotation added.
18. **Family count** (stage 5): the sorted families of the registered lineages per part are in the record; whether 12 applies per part or per evaluation is not decided here.

## 5. Disagreements between the text and existing code or scripts

1. `core.draw_items` raises `RuntimeError` when `build_item` gives up, even with `allow_short=True`; the text says the draw stops and the count is the keys then in the set. `capacity._advance` follows the text. (`generate_pool` as written would stop the whole pool; `build_pool` keeps that: a give-up in a pool draw propagates.)
2. `core.generate_pool` loops lineage then level; text part B item 6 says clusters, then levels, then lineages. Followed the text.
3. The drafter's worked-example script models a count as `min(capacity, T)` and the union as `k x T - shared`; the code counts real key sets and unions them. They agree on the examples (4a, 4b) because the model's keys are chosen to make them so (`Model` in the test).
4. The third reviewer's `stage4_review3.py` reads (ii) on every cluster; the text and the drafter's 4b read it only on a cluster all of whose lineages pass (i). Followed the text.
5. The earlier capacity scripts (`studies/m0/*capacity*.py`) key on the normalised text with names included, on a structural form, or on `alpha_key` of the C1 program; none is the key of the text, which governs.
6. Text section 8 says the first solver is "the builder's key"; `Item.answer` is that key (`Built.answer`).
7. The `D_w` figures and `D(G)` printed in the text equal the formula in exact integer arithmetic; the float `math.ceil` form gives the same for G <= 300, k <= 11 (tested).
8. The text's 40 x T + 1,000 is `attempt_factor * count + 1000` of `draw_items`; same.
9. Section 10 A item 1 says the key function is "hashed with the generators at stage 0"; `distinct_key.py`, with `capacity.py`, is what to hash. `KEY_VERSION` is written into every cache file and into the record.

## 6. Not done

* Stage 5's registration and stage 6's record are the lead's; the stage-4 record holds what they need (registered lineages per part, G, families, every round).
* Not run: the capacity stage of record; no partition exists. The code is not tested on the real partition or the real candidate list beyond a three-lineage run with a demand cut to a few hundred keys.
* `--no-solvers` exists for rehearsal only; the record says if it was used (`spec.solvers_checked`).
* R2 lineages were not timed (section 7). Levels 1 to 5 were not timed.

## 7. Timing probe and estimate of the run time of stage 4

Probe (`timing_probe.py`; measured, one process, Apple M5 Max (18 cores), Python 3.12.14, `uv run --locked`): lineages fixed before measuring:
`R1.compass_turns`, `M1.tiered_pricing`, `C1.postfix_evaluation`; levels 0 and 6; label `capacity-timing-probe` (not `capacity`); 2,000 keys per draw
(three repeats; medians). It reports speeds and discard rates only; it does not report or keep how many keys a lineage can reach, and no
capacity is inferred from these figures in this note.

| lineage, level | attempts/s (build + key) | discard rate at 2,000 keys | solver check, microseconds per item |
|---|---|---|---|
| R1.compass_turns, 0 | 82,200 | 0.084 | 5 |
| R1.compass_turns, 6 | 33,100 | 0.000 | 13 |
| M1.tiered_pricing, 0 | 35,800 | 0.004 | 6 |
| M1.tiered_pricing, 6 | 30,900 | 0.000 | 19 |
| C1.postfix_evaluation, 0 | 3,560 | 0.008 | 150 |
| C1.postfix_evaluation, 6 | 3,080 | 0.000 | 245 |

Estimate (analytical, from those measurements). Assumptions: text evaluations (R1, R2, M1: 46 lineages, 322 cells) cost build + key at
the slowest measured level (30,900/s) + 13 microseconds of solver = 22,100 attempts/s (R2 not measured, assumed like M1); C1 (21 lineages, 147 cells) at level 6:
3,080/s + 245 microseconds of solver = 1,750 attempts/s; 469 cells per round; the same target T in every cell; wall = CPU / 16 workers (of 18 cores), perfect balance
(not measured); discard rate taken as zero at T (it is unmeasured above 2,000 keys and is not estimated here); one round, no cache.

| T (keys per lineage and level) | every cell reaches T: CPU, wall at 16 workers | one text cell / one C1 cell | worst case, every cell fails and runs its whole budget (40 T + 1,000 attempts): CPU, wall at 16 | one failing text cell / one failing C1 cell |
|---|---|---|---|---|
| 30,000 | 49 min, 3.1 min | 1.4 s / 17 s | 33 h, 2.1 h | 54 s / 11 min |
| 60,000 | 98 min, 6.1 min | 2.7 s / 34 s | 66 h, 4.1 h | 109 s / 23 min |
| 120,000 | 197 min, 12 min | 5.4 s / 68 s | 131 h, 8.2 h | 218 s / 46 min |
| 240,000 | 394 min, 25 min | 11 s / 137 s | 262 h, 16 h | 435 s / 91 min |

Reading: a cell that reaches T costs about T attempts (more if many are discarded); a cell that cannot reach T costs 40 T + 1,000 attempts, 40 times more,
and C1 cells cost about 12 times a text cell. The run time is therefore set by how many cells fail, which this note does not estimate (hypothetical: the right-hand
columns are bounds, not forecasts). A single failing C1 cell at T = 240,000 is 91 minutes of one core whatever the number of workers. Each later round repeats
the cells without a cache and costs only the added stream with a cache (section 3). The first-draw cost of the solver check is included; `--no-solvers` is not allowed for the record.
Memory: a cell holds about T x (16 + ~70) bytes while it runs (20 MB at 240,000); a cache file is about 20 bytes per key (up to 2.3 GB for 469 cells at 240,000).
