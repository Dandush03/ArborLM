# M0 stage 4 (capacity): independent audit of the code before the run of record

**Verdict: FIT AFTER REQUIRED CHANGES.** The counting loop, the rounds and fixed point, the demand tables, the cache, solver agreement and determinism agree with the approved text and with my own code in every case I tested. Two items must be settled before the run. C1 is a process item: the stage-0 hashes of the key, the runner and the pool builder are missing. C2 is a small gap in the key's relabelling: "orange" in `M1.shopping_r3`. No defect found in `capacity.py`'s logic.

- Ran as: `arbor-auditor` task, model **Opus 5.5** (`claude-opus-5-5`, from session metadata). I wrote none of the audited code.
- Astra review: NOT_PERFORMED. This audit is independent engineering and mathematical evidence. It is not Astra validation and not human approval.
- Text: the approved addendum at `2c944302` (`docs/decisions/ADR-0033-addendum-1-lineage-clusters.md`). I read section 4A stages 0 and 2 to 6, section 4 item 7, section 8, section 10 parts A and B, section 12 items 15 and 21, and section 13 items 1, 6, 16 and 21.
- Files audited (implementation worktree `agent-a0c9d741ea96ce52f`, uncommitted, SHA-256 unchanged at the end of the audit):
  - `distinct_key.py` `1059b07b…08e4`
  - `capacity.py` `00638afa…2152`
  - `pool_builder.py` `728856b6…4862`
  - `test_capacity.py` `cd9bbb4b…7c34`
  - `NOTES_CAPACITY.md` `5507ddc8…9029`
  - Read alongside: `core.py` `07907f1e…c81d` (unchanged since `9bcec484`) and `vocab.py` `2c4036be…c286`.
- Inputs of record, read only:
  - `candidate_list.json` `8dcc796c…946a`
  - `partition_of_record.json` `750715d8…37e9`
  - `map_of_record.json` `1ba6ddd5…809c`
- Environment: macOS (darwin), Apple Silicon, CPython 3.12.14. Every command ran from the implementation worktree root as `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout <≤590> uv run --locked python <deliver>/<script>.py`. Where another hash seed, worker count or start method was used, it is stated. Standard library only.
- Labels: every real-lineage draw used an audit label, `capacity-audit` or `capacity-audit-names`. Scripts that call `capacity.py` set `capacity.LABEL = "capacity-audit"` and wrap `capacity.stream` with a guard that raises on the label `capacity`. The guard is installed in the parent and in every worker, including spawned ones (`g_determinism.AuditSource.__setstate__`). **No item of the stream `capacity` was drawn for any real lineage.** No capacity of a real lineage is reported here: no count of distinct keys, no discard rate, no budget outcome under the key of record.

## Findings

**C1. MUST CHANGE BEFORE THE RUN (record and report a departure; no code change).**
- The text, section 4A stage 0, says: "Recorded before anything below is computed on the map of record: … Then the inputs and the code are hashed: … the distinct-item key; the partition code; the pool builder; the capacity runner."
- What happened: the partition of record was computed at `af2a987d`. `distinct_key.py`, `capacity.py` and `pool_builder.py` are still uncommitted and unhashed. They are not in `docs/reviews/m0-fresh-run-2026-11-26/HASH_RECORD.json`, and I found no recorded ruling that covers this.
- Why it matters: the key and the runner are being finished with the parts known. Several of the key's choices act on known parts. For example:
  - the `R2.caesar_shift` exception favours a lineage that is in R2 part B;
  - the "orange" gap (C2) favours `M1.shopping_r3`, which is in M1 part A.
- Smallest change: before the run, the lead writes this down as a recorded departure (what was hashed late, when, and whether the code's author had the partition in view), hashes the three files as audited (after C2), and puts it to the human lead, as section 4 item 7 and the "only if it arises" list provide.
- Whether a late hash is acceptable is PENDING LEAD REVIEW.

**C2. MUST CHANGE BEFORE THE RUN (the key; the direction favours passing).**
- The text, section 10 A item 1, says: "The key of an item is its rendered question with names relabelled." `distinct_key.py` treats every entry of `vocab.OBJECTS` as a name, except "orange", which it drops because "orange" is also in `COLOURS`.
- `M1.shopping_r3` draws its bought objects from `OBJECTS`, and "orange"/"oranges" occurs in 253 of my 1,400 audit-label items. All 23 other objects are relabelled. So two shopping items that differ only by "oranges" against "kettles" in one slot get two keys. That over-counts the lineage, in the direction that favours passing.
- Sample results (`c_names2.json`, varying tokens left in the key): "orange" is the only object word left in any lineage. Only two lineages contain the word: `R1.boolean_lights_r4` (a switch colour, which is correctly left alone as a label) and `M1.shopping_r3`.
- Smallest change: relabel "orange" as an object in `M1.shopping_r3` only. For example, add a per-lineage set beside `DATA_VOCABULARY`: `{"M1.shopping_r3": {"orange"}}` words that are names there despite being labels elsewhere.
- Alternatively the lead may record it as a departure. If the lead rules that objects are not names (C3), this finding falls away and C3 applies.

**C3. NOTE, PENDING LEAD REVIEW (the key's breadth; stricter than "names").**
- The key relabels people, towns, events, objects, pets and invented words. On the sample, the classes that actually vary in candidate lineages are:
  - people, in 19 lineages;
  - towns, in the M1 frames and `R2.cheapest_network`;
  - events, in `R1.temporal_weekday_shift_r6`;
  - objects, in `M1.shopping_r3`;
  - invented words, used as category names, in `R1.categories_default_exceptions_r4`.
- Treating ordinary object nouns (drums, violins) and event phrases as "names" merges items. That is stricter than a people-and-places reading and less favourable to passing.
- Labels (colours), letters, weekdays, activity words and ability verbs are left in the key, as reading (i) asks.
- Constant template words that are list entries ("book", "taken", "never", "ribbon") are relabelled. They are the same in every item of a template, so they change no comparison.
- Whether objects, events and invented category words are "names" under the decided reading (i) is the lead's call.

**C4. NOTE (the `R2.caesar_shift` exception is right under the decided reading).**
- Under the decided reading (i), "names relabelled" removes differences that do not change the item. In `caesar_shift` the invented words are the text being shifted, the same role as the letter strings of `R2.run_length` or `R2.dictionary_rank` and the string literals of C1, which the key also leaves alone.
- Test (`j_extra2.out` (a)): in all 1,400 audit items, renaming the invented words one-to-one changed the second solver's answer. A key without the exception would give the original and the renamed item one key in all 1,400 cases, though their answers differ.
- Direction: against a mechanical relabelling of every vocabulary word it favours passing (it keeps the lineage countable). Against the reading itself it is neutral. Relabelling would be the departure, and an unfavourable one.
- No other lineage needs the same exception. The rename test changed no answer and no key in 26,600 renamed items over 19 lineages that contain names.
- Because the exception was written with the partition known (C1), the lead should confirm it explicitly. PENDING LEAD REVIEW.

**C5. NOTE (solver timeout).** `_check` counts a 20-second wall-clock timeout as a disagreement. That would make a removal depend on machine load, against "fixed by the candidates, the partition and the generators". The slowest second-solver call on 93,800 audit items was 0.017 s (`b_sample_solvers.json`), about 1,000 times inside the limit, so the risk is remote. Recommended, not required: treat a timeout as an engineering stop (raise) instead of a disagreement, and print the largest solver time per cell.

**C6. NOTE (stops rather than silent outcomes).** Some events stop the whole run instead of counting as a capacity outcome:
- any builder exception other than the 500-retry give-up;
- a C1 program the key cannot parse consistently (keyword arguments, `global`);
- a C1 question that does not contain `render(structured["program"])`.

None occurred on 9,800 C1 audit items or on any draw of this audit. This matches the implementer's choice list item 5.

**C7. NOTE (zero slack in round 1; arithmetic only).**
- With the round-1 counts, three clusters of two lineages have zero slack, `k·D_lin = D(G)`:
  - `R1.boolean_lights` in R1A (G = 4);
  - `C1.digit_peel` in R2A (G = 8);
  - `C1.fib_like` in M1A (G = 8).
- One key shared by the two siblings at any level fails both lineages (section 12 item 15).
- The other multi-lineage clusters have slack 10 to 80 keys:
  - M1A `M1.ages`, k = 6: 80;
  - M1A `M1.mixture`, k = 3: 50;
  - M1B `M1.fraction_remainder`, k = 3: 60;
  - C1A, k = 2: 10;
  - C1A, k = 3: 30.
- Siblings share a key only if their rendered questions are identical up to names. I did not measure that.

**C8. NOTE (cache hygiene).**
- The trace header holds the tag, the stream labels, whether solvers were checked and `KEY_VERSION`. It does not hold the key function actually passed (`key_fn`; the tests pass non-default ones) or a generator hash. The tag carries the generator identity by convention only.
- If the cache is used for the record (item 4), it should go in a new, empty directory created for the run, with a tag naming the generator commit and the key's SHA-256. The record should say so.

**C9. NOTE (my own process slips, recorded).**
- While looking for the earlier definitions of the readings, I read lines of `AUDIT3_R2.md` and `AUDIT4_C1.md` (`docs/reviews/m0-lineage-decision-2026-11-25/`) that contain old working capacity figures. I used none of them, and nothing here depends on them.
- I changed my own new script `e_fixed_point.py` in place once (a speed change, before it had produced any result), against the brief's "edit no existing file". It then failed on an indentation error and is kept as is. The working version is `e_fixed_point2.py`/`3.py`.

## 1. The count

My `my_count` (`a_common.py`) is written from the text alone:
- a fresh stream `stream(400002, label, e, id, str(v))` derived as section 4 says;
- a key set that starts empty;
- `core.build_item` called as `draw_items` calls it, with the attempt counter raised before the budget test;
- a budget of `40T + 1000`;
- a stop at the give-up `RuntimeError` after 500 consecutive retries.

Label and argument order:
- `capacity.stream_labels(lin, v)` is `("capacity", lin.eval, lin.id, str(v))`, and `SEED` is 400002.
- `core.derive_seed` equals SHA-256 of `"|".join(...)`, first 8 bytes, big-endian.
- That is exactly the registered label, seed and order. The evaluation comes from `lin.eval`, and `RealSource` asserts that it equals the evaluation it loads under.

Comparison (`d_count.py`, output `d_count.out`/`.json`). **0 disagreements.** Key sequences are identical in content and order, with the same way of stopping and the same attempt count:
- **44 toy cases:**
  - the 5th key at attempt 1,200, exactly the budget for T = 5: reached;
  - the 5th key at attempt 1,201: stopped on the budget with 4 keys;
  - a give-up at attempt 4, and a give-up after duplicates;
  - 499 retries followed by a success: no give-up;
  - one distinct item;
  - random toys with 1, 7, 50, 999, 1,000, 1,001 and 3,000 distinct items at T of 1, 50, 1,000, 1,001 and 2,500;
  - two toys with retries.
- **72 real cells:** 12 real lineages, 3 per evaluation:
  - `R1.compass_turns`, `R1.knights_knaves_r6`, `R1.temporal_weekday_shift_r6`;
  - `R2.caesar_shift`, `R2.cheapest_network`, `R2.dictionary_rank`;
  - `M1.shopping_r3`, `M1.change_ways_r3`, `M1.tiered_pricing`;
  - `C1.postfix_evaluation`, `C1.slices_f4`, `C1.func_compose_f4`;

  each at levels 0, 3 and 6 and T = 300 and 3,000, under `capacity-audit`. The 36 cells at T = 300 ran with the second solver: 0 disagreements.
- `capacity.RealSource` loads the same lineage objects and the same second-solver functions as the pair audit's `gen_fresh.py` loading, for all 67 candidates (`k_source.out`).

## 2. The distinct-item key

Results:
- **My own relabelling against `key_text`.** My version is independent code: one scan over every surface form, the longest first, with an optional plural `s`/`es`, numbering by first appearance and articles written "a"; for C1, tokenize plus `ast` names. It gives the identical key text on all 93,800 audit items, 1,400 per candidate lineage (`c_names2.out`: 0 differences).
- **Names only.** A one-to-one renaming within each class, in question, structured form and answer:
  - left the key unchanged in 26,600 of 26,600 items;
  - left the second solver's answer equal to the renamed answer in all of them (`j_extra2.out` (c)).
- **Other changes.**
  - Changing one digit, or the first word, changed the key in 3,520 of 3,520 text items (`j_extra2.out` (b)).
  - For C1 I did not perturb the question alone: the C1 key renders the program from `structured`, so a question-only edit is not an item. It raises ValueError, which is my first attempt in `j_extra_attempt1_failed.out`.
  - C1 equality with my independent key text covers C1.
- **Same key, different answers:** none in the sample, under any lineage.
- **Every C1 lineage has one constant frame.** Identifiers do not leak into the frame.

Each normalisation beyond relabelling names, and its direction:
- **"a"/"an" before a name, written "a".** It only acts where a name follows, so it merges exactly the items relabelling merges. It is part of relabelling, with no extra merge.
- **Plural and possessive kept outside the name.** "drum" against "drums" stay different. That splits only what the text differs in, so it is neutral.
- **First-letter case of lower-case lists accepted.** "Book" matches "book". Neutral: the same object.
- **One placeholder counter for all classes.** A person swapped with a town would share a key. That could only merge, so it is stricter. No template allows such a swap; no practical effect.
- **Labels excluded from the name lists.** Neutral, except "orange" in shopping, where it splits (C2).
- **C1.** Identifiers that the program binds or uses, excluding builtins it does not bind; attributes, literals and keywords untouched. This matches reading (a) as the C1 auditors measured it ("identifiers renamed … except builtins"). Neutral.
- **No case folding or whitespace normalisation.** "Exact duplicates" as written. Items differing only in case or spacing would split, but no generator produces them as far as I saw.

Missed name classes and over-relabelled words. I listed every varying non-number token left in the key for all 67 lineages (`c_names2.json`, `varying_tokens_left_in_key`):
- **Missed name class:** only "orange" (C2).
- **No non-name word relabelled as a name in a varying position.** Invented-word matches that are English words ("taken", "never") are constant template words. No varying invented-word match occurs outside `R1.categories_default_exceptions_r4`, where those words are category names.
- **The rest of what varies is not names:** weekdays (temporal), activities (inclusion_exclusion), ability verbs (categories), switch colours (boolean_lights), letter strings (dictionary_rank, run_length, string_rewrite, from_base), C1 string literals and builtins, and frame wording.

## 3. The round and the fixed point

My implementation (`e_fixed_point*.py`, function `mine`) follows the text:
- G = clusters with a lineage in S; k_c = lineages of c in S.
- (i) at each of the 7 levels at D_lin(G, k_c).
- (ii) only for clusters all of whose lineages pass (i), on the union of the key sets drawn for (i), against D(G).
- (iii) any disagreement in the round's draws.
- All failures removed at once, empty clusters dropped, repeated until no failure. Each round's targets are drawn from a model in which a later round is a re-draw from the start.

Comparison with `capacity.run_stage4(count_fn=…)` on the same model, demand constants scaled by 1/100 (40/200/1) for speed:
- **First set:** 3,000 random cases with seed 4,002 (`e_fixed_point2.out`; its JSON could not be written because the 100-case trial had already written that name). Up to 7 rounds per part. Parts ending empty. Cross-evaluation clusters and non-candidate members. Sibling overlaps of 1 to 400 keys. Give-ups and solver disagreements at random attempts. Budgets that bind only at larger targets. **0 disagreements.**
- **Second set:** 3,000 more with a milder distribution (`e_fixed_point3.out`/`.json`): up to 6 rounds, **0 disagreements**.

Hand cases at the registered constants. All agree, and one shared key fails both siblings exactly where the slack is zero:
- (G, k) = (10, 2), (4, 4), (5, 5), (16, 2) and (1, 2);
- (16, 8): 160 shared keys pass, 161 fail;
- (10, 3), slack 50: 1 and 10 shared keys pass.

Demand tables:
- `capacity.demand` and `demand_lin` equal my integer formulas for G = 1 to 399 and k = 1 to 39.
- D(1) = 241,000; D(2) = 121,000; D(3) = 81,010; D(4) = 61,000; D(5) = 49,000; D(8) = 31,000; D(9) = 27,680; D(10) = 25,000; D(11) = 22,830; D(13) = 19,470; D(14) = 18,150; D(15) = 17,010; D(19) = 13,640.
- D_lin(10, 2) = 12,500; D_lin(13, 3) = 6,500.
- Zero slack for k = 2 at G ∈ {1, 2, 4, 5, 7, 8, 10, 16}; for k = 4 at {1, 2, 4, 5, 8, 10}; for k = 5 at {1, 2, 4, 5, 8, 10, 16}; never for k = 3, 6, 7 or 8.
- The largest slack is 160, at G = 16, k = 8.
- All of these are as the text prints.

## 4. The cache

The cache is **verified.**
- **Proof.** The prefix argument of `NOTES_CAPACITY.md` §3 is correct given P1, that the builder is a pure function of the stream state. The stop attempt min(a_T, 40T + 1000, g) is non-decreasing in T. The draw for any T is a prefix of one stream, and its key set is the first c(T) keys in first-occurrence order.
- **Real lineages, key of record** (`capacity-audit`, `d_count.out` CACHE lines). On 8 real cells (4 lineages, levels 0 and 6):
  - a draw to 400 followed by a draw to 1,500 continued from the stored generator state equals a fresh draw to 1,500 and my `my_count`;
  - a later request for 400 answered from the longer trace equals the fresh draw;
  - the 400 set is a prefix of the 1,500 set.
- **When the T₁ draw stopped on its budget.** On real builders the budget does not bind at audit-size targets under the key of record, so I used an artificial coarse key (not the key of record). The four T₁, T₂, T₃ = 200, 400, 300 draws all stopped on the budget. In every case:
  - the cached answers equal fresh draws and mine;
  - the lower draw's set is a prefix of the higher draw's set (`BUDGET-PROBE` lines).
- **Across processes.** Determinism across processes and hash seeds (item 6) supports P1.

What is different in a later round:
- **Nothing.** Each later draw uses its own target's budget from attempt 1, and `_derive` applies exactly that. The solver check covers every attempt up to the new stop. Disagreement details are the first 20 within the stop either way.
- Targets only rise from round to round (D_lin falls in G and in k), so a later round never asks for less than the trace holds.

Should the run of record use the cache?
- Either gives the same record. Running **without** the cache is the literal reading ("drawn again from the start") and has no stale-state risk; I recommend it unless time binds.
- If the cache is used, follow C8 and say so in the record.

## 5. Solver agreement

- **How `structured` is formed: identical to the pair audit.**
  - The pair audit (`pair_audit/gen_fresh.py` and `apply_solvers.py`) stored `json.loads(json.dumps(it.structured))` with insertion order, without sort_keys, and passed `copy.deepcopy` of it.
  - `capacity._call_solver` passes `copy.deepcopy(json.loads(json.dumps(structured)))`.
  - Both use a 20 s alarm per item.
- **What counts as a disagreement.** The first solver is `Item.answer`, the pair audit's `key`.
  - capacity: an exception, a timeout, a non-`str` answer, or `got != answer`.
  - pair audit: compared `str(a) != str(key)` and listed errors and non-`str` answers apart.
  - The two are equal on `str` answers and capacity is stricter on errors. Since "must agree" needs an answer, I read that as faithful.
  - Two small differences: the pair audit catches `BaseException` and capacity only `Exception`, so a `SystemExit` from a solver would stop the run; and the timeout (C5).
- **Every attempt, discarded duplicates included.** The text says "any item built in this stage" and "every generated item". A discarded duplicate is an item built: it has the same key but may differ in names. So checking every attempt is **equal to the text, not stricter**.
- **Deliberate loud failures.** The pair audit lists failures on items out of the range the builders produce: compass turns not multiples of 90; heap ties; bases outside 2–16; unary minus; legs crossing midnight; non-lowercase caesar input.
  - Such a failure counts as a disagreement and removes the lineage under (iii). That is what the text says ("disagree on any item built in this stage fails"), whichever solver is at fault.
  - I found none in 93,800 audit items (`b_sample_solvers.json`, 0 disagreements and 0 errors for all 67), nor in the 36 solver-checked real cells of item 1.
  - The heap builder draws distinct values (`r.sample(range(1, 100), n)`), so ties cannot occur.
  - A rare one over the roughly 14 million attempts of the run cannot be excluded by sampling.

## 6. Determinism and safety

- **Same record everywhere.** `g_determinism.py` (`g_determinism2.out`) uses 2 toy lineages and 5 real lineages under the audit label, the demand cut to 4/20/1, and solvers checked. The record (`capacity.dumps`) has the same SHA-256, `83509c63…bb4f`, under all six combinations:
  - 1 worker at `PYTHONHASHSEED` 0 and 1;
  - 16 workers with fork at seed 0 and 1;
  - 16 workers with spawn at seed 0 and 1.

  The first try, `g_determinism.out`, failed before running: zsh did not split the arguments.
- **Spawned workers use the audit label.** Their output is identical, and the guard would have raised on the label `capacity`.
- **No overwrite.** `main()` returns 2 and writes nothing when `--out` or `--timings-out` exists (`i_misc.out`). Outputs and cache files are opened with `"xb"`.
- **Memory** (`h_memory.out`). One cell at 240,000 keys holds 27.9 MiB (Python set of 16-byte bytes, plus bytearray, plus attempt array). With 16 workers that is about 446 MiB. Each returned `Draw.keys` is 3.7 MiB. The parent holds at most one round's keys, about 13.8 million keys or 210 MiB in round 1 if every cell reaches its target.

## 7. The round-1 targets

Computed by `f_round1.py` from the inputs of record and the formulas only. `capacity.build_parts` gives the same parts (`i_misc.out`).

| Part | G | Lineages | D(G) | D_lin per k_c (number of clusters) | Budget 40T + 1,000 |
|---|---|---|---|---|---|
| R1A | 4 | 5 | 61,000 | k = 1 (3): 61,000; k = 2 (1): 30,500 | 2,441,000; 1,221,000 |
| R1B | 1 | 1 | 241,000 | k = 1 (1): 241,000 | 9,641,000 |
| R2A | 8 | 9 | 31,000 | k = 1 (7): 31,000; k = 2 (1): 15,500 | 1,241,000; 621,000 |
| R2B | 7 | 7 | 35,300 | k = 1 (7): 35,300 | 1,413,000 |
| M1A | 8 | 16 | 31,000 | k = 1 (5): 31,000; k = 2 (1): 15,500; k = 3 (1): 10,350; k = 6 (1): 5,180 | 1,241,000; 621,000; 415,000; 208,200 |
| M1B | 6 | 8 | 41,010 | k = 1 (5): 41,010; k = 3 (1): 13,690 | 1,641,400; 548,600 |
| C1A | 13 | 17 | 19,470 | k = 1 (10): 19,470; k = 2 (2): 9,740; k = 3 (1): 6,500 | 779,800; 390,600; 261,000 |
| C1B | 4 | 4 | 61,000 | k = 1 (4): 61,000 | 2,441,000 |

Round 1 work:
- **Size:** 469 cells (67 lineages × 7 levels).
- **Attempts:** at least 13,800,570 if every cell reaches its target with no discard; at most 552,491,800 if every cell runs its whole budget.

Worst case per cell:
- **Round 1:** 40T + 1,000 attempts. The largest is 9,641,000 (R1B); for C1 it is 2,441,000 (C1B).
- **Any later round:** at most 40 · D(1) + 1,000 = 9,641,000 attempts. Each attempt can call the builder up to 500 times through `Retry`.

Time, using the implementer's probe rather than my measurements (about 22,100 attempts/s for text and 1,750/s for C1, with the solver):
- a failing R1B cell is about 7 minutes;
- a failing C1B cell is about 23 minutes;
- a C1 cell at G = 1 is about 92 minutes.

## 8. `pool_builder.py` against section 10 part B (read, not run)

Items 1 to 8 are implemented as written:
1. Clusters are sorted by code point from `registered`.
2. Cluster quotas come from `allocate`, ties to the earlier cluster.
3. Levels use `allocate` with the mix weights, in increasing level order.
4. Lineages within a cluster are sorted by id and quotas come from `allocate`.
5. The stream is `stream(seed, role, salt_label, e, p, id, str(lv))`.
6. `taken` is shared. The order is cluster, then level, then lineage. A shortfall raises `CapacityShortfall` or is recorded; nothing is moved to a sibling.
7. The M0 draw is equal per cluster, then per lineage, with `stream(400006, "m0-draw", id).sample`.
8. `PoolItem.cluster`, the counts per family, cluster, lineage and level, and the pool hash.

Departures, none substantive:
- **Give-up (item 6).** When `build_item` gives up, `draw_items` raises a `RuntimeError`, not `CapacityShortfall`, so the run stops instead of recording a shortfall (the implementer's note 5.1).
- **Role order (item 6).** The order of roles (tuning, then development, then sealed) and the shared `taken` are left to the caller, so the order of record must be enforced where `build_pool` is called.
- **Development pool (item 7).** `m0_draw_by_cluster` samples from whatever `pool` it is given. The caller must pass the development pool.
- **Pool hash (item 8).** The hash includes the new `cluster` field, so it is not comparable with `core.pool_hash` hashes.

## Not done

- I did not run the implementer's `test_capacity.py`: it writes to pytest temporary directories outside the scratch directory and draws under its own smoke label.
- I did not time the cells myself; the time figures above come from the implementer's probe.
- I did not measure key overlap between sibling lineages (C7).
- I did not check the stage-0 order beyond `HASH_RECORD.json` and a search of the review folders (C1).

## Files

Everything is in `experiments/_scratch/m0_capacity_audit_20261126/`, and nothing was written elsewhere. `SHA256SUMS.txt` covers `deliver/`.

Scripts and their outputs:
- `a_common.py`: my stream, loader and `my_count`.
- `b_sample_items.py`: the audit-label sample and the solver check.
- `c_names2.py`: the key check.
- `d_count.py`: the count and the cache.
- `e_fixed_point3.py`: the fixed point.
- `f_round1.py`: the round-1 targets.
- `g_determinism.py`: determinism.
- `h_memory.py`: memory.
- `i_misc.py`: the parts and the overwrite refusal.
- `j_extra2.py`: the caesar check, perturbations and totals.
- `k_source.py`: the loader comparison.
- Each script's output is the `.out`/`.json` file of the same stem.

Failed or superseded attempts, kept:
- `c_names.py`/`.out`, with copies `c_names_attempt1_failed.*`: a `rename` index error, then too slow.
- `e_fixed_point.py`: broken by my in-place edit.
- `e_fixed_point2.json`: the 100-case trial. `e_fixed_point2.out` is the 3,000-case run whose JSON write was refused.
- `g_determinism.out`: the zsh argument failure.
- `j_extra.py` and `j_extra.out`/`j_extra_attempt1_failed.out`: the C1 perturbation error.

`work/` holds:
- `sample_items.jsonl`: 93,800 audit-label items;
- `spec.md`: a copy of the approved text;
- trace caches of `d_count.py`;
- `g_det_*.json`: tiny-target records under the audit label, where every real cell reached its target of at most 250;
- `e_trial100.out`.
