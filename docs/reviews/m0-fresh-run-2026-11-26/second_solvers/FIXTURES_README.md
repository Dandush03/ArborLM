# Answer-free fixtures for rewriting the second solvers (M0, ADR-0033 addendum 1, section 8 item 1)

Built by an implementer context (Claude Sonnet 5.5) on the generator side. Self-checks only: not independent review, not Astra validation, not human approval.

## What is here
- `<EVAL>/<lineage id>/fixtures.jsonl`: 280 lines per lineage (levels 0-6, 40 per level). Line: `{"id", "level", "index", "question", "structured"}`. `question` is the exact `Item.question` text of the committed builder; `structured` is the builder's structured dict with the answer-bearing fields removed (below).
- `<EVAL>/<lineage id>/SCHEMA.md`: meaning of each `structured` field and the answer's format only (type and surface form, from the builders and `studies/m0/scoring.py`).
- No keys here. Keys are in the separate tree `experiments/_scratch/m0_second_solver_keys_20261126/<EVAL>/<lineage id>/keys.jsonl` with the self-check `selfcheck_v3.py` (and the earlier `selfcheck.py`, `selfcheck_v2.py`, whose FAIL outputs are kept as `selfcheck_run1.out`, `selfcheck_run2.out`).

## Counts (measured)
Lineages per evaluation: R1 10, R2 17, M1 29, C1 26 = 82; 280 items each = 22960 items. All lineage ids are those of `studies/m0/manifests/survivor_list_of_record.json`.

## How the items were built
- Lineage objects: R1 `studies.m0.lineages_r1_fix4_clusters.candidates_v4()` (+ `registered_v4()`); R2 `studies.m0.r2_fix4_set.fix4_set()`; M1 `studies.m0.lineages_m1_fix4.load_registered()`; C1 `studies.m0.lineages_c1_fix4.all_written()`. All 82 ids resolved.
- Per (lineage, level): `studies.m0.core.draw_items(lin, "A", level, 40, rng, taken, "second-solver-fixtures")` (the call `generate_pool` makes: `build_item` with Retry handling, items whose normalised text repeats an earlier one of the same lineage are skipped; `taken` is shared across the seven levels of one lineage). `index` is the position in the level's returned list.
- Seed: `int.from_bytes(sha256(f"400002|second-solver-fixtures|{EVAL}|{lineage_id}|{level}".encode()).digest()[:8], "big")`, passed to `random.Random`. Not a run seed, dry-run seed or stage-2 check seed. EVAL is `R1`, `R2`, `M1` or `C1`.
- Code: implementation worktree, builders as at `7cd0ac5a` (the worktree HEAD at build time was `1c68e4b2`; the `studies/m0` builder modules are unchanged since `7cd0ac5a` per the common brief; not re-verified by me). Python 3.12.14, `PYTHONHASHSEED=0`, `uv run --locked`. Build script (scratch): `experiments/_scratch/m0_second_solver_fixtures_impl_20261126/build.py` and its `specs.py`; its log `build_attempt1.out` (82 lines, no failures). The script asserts, for every lineage, that every key matches the format regex stated in SCHEMA.md and that the described fields are exactly the observed fields.

## Fields removed from `structured` (per lineage)
None, in any of the 82 lineages. Reason: in every builder the `structured` dict holds only the inputs of the item (the values the question text itself states or encodes) and question-mode tags; no builder puts the key, a solution trace, an intermediate result, an expected value, a distractor marker or an answer-encoding shape tag into it (read in the code of all 82 builders). Fields I looked at twice and kept, because each is a value printed in the question text and is not computed from the answer:
- `ask`, `shape`, `mode`, `convention`, `average`, `op`, `desc`: which question or wording was drawn (stated in the text).
- R1.venn_counting_r5 `triple` (the number in all three groups, stated), M1.inclusion_exclusion_r3 `triple`, M1.tiered_pricing `bill_cents` (the bill stated in the units-mode question, in cents) and `used` (stated in bill mode), M1.quadratic_area_r3 `d`/`area`/`perimeter`/`total` (stated; unused ones are 0), M1.rectangle_r3 `ratio`/`excess` (0 when unused), M1.recurrence_iterate_r3 `mult`/`add` (0 when unused), M1.linear_equation_r3 `j` (0 = one-sided form), M1.ratio_share_r3 `who` (index asked).
- R1.conditional_threshold_rule_r4 `margin` (the threshold D, stated).
- C1 `program` (the program as a tree; the question shows the same program as Python source).
Nothing was left out for being unsure. If the lead wants the question-mode tags (`ask`, `shape`, `mode`) treated as structure to hide, say so and I will rebuild into a new directory.

## Lineages where structure could not be separated from the answer
None. Lineages with `structured` empty: none (all 82 have at least one field).

## C1 facts (what an item is, what the builder executes)
- An item: a short program in a small Python subset and the question text `Here is a Python program.\n\n<source>\n\nWhat exactly does it print? It prints a single line.` The program has fixed numbers and strings (no input); the model must say the one line it prints.
- Language: Python 3 syntax (generated source, rendered from the tree of `studies/m0/c1grammar.py`): assignment, augmented assignment, index assignment, `append`, `for ... in range(a, b[, step])`, `while`, `if/elif/else`, `def` with `return` (including recursion in some lineages), integer arithmetic `+ - * // %`, comparisons, `and`/`or`/`not`, list literals, indexing, slices, string methods in the lineage-specific set, and calls to `len, sum, max, min, abs, range, sorted, str` and user-defined functions. Exactly one `print` call executes and prints one line.
- What the builder executes: `studies.m0.c1grammar.run_inprocess(src)`: `exec(compile(src, "<c1>", "exec"), {"__builtins__": safe})` in the committed CPython 3.12 process, with builtins limited to `len sum max min abs range sorted str` plus a `print` replaced by one that joins its arguments with a space and records one line. The key is that single recorded line, exactly (a different line count raises and the item is redrawn). Items are redrawn (Retry) when the program raises ZeroDivisionError/IndexError/ValueError/TypeError/KeyError, or when the key has an uppercase letter, leading/trailing space, a double space, is empty, or ends with a full stop. So the key is what CPython prints; a printed list shows as `[a, b]` and a string without quotes.
- The repository's own second solver for C1 is a tree walker (`solvers_c1.c1_trace`, per the docstring of `lineages_c1.py`/`lineages_c1_common.py`) that does not use `exec`; I did not read it.
- The fixtures give `program` as the tree and the question gives the source: the second solver can work from either; an independent second solver for code tracing is therefore an interpreter or a hand trace written without reading the generator or first solver, not a different reading of the question. (Lead's decision.)

## Self-check (kept in the keys tree)
Run output in `m0_second_solver_keys_20261126/selfcheck_run3.out`; summary in the final message. The allow-list in `selfcheck_v3.py` was written after the first two runs showed 110 and 6 top-level fields equal to a key by coincidence (all stated inputs: e.g. the start direction equals the final direction); its entries and the reason for each are in the script; nothing was removed to make the check pass.

## sha256 of the files in this tree (at the time of writing)
```
c2a81715566bfcd9fe184e42c426e859599e28d8fe80874ff8b85a81bad43de2  R1/R1.boolean_lights_r4/fixtures.jsonl
60863ddb9cacfe4c8333483a78b5810cbd162b057489810dcfcfc47871d9ec3f  R1/R1.boolean_lights_r4/SCHEMA.md
9e2a00c5bf91a12c39c2d61b92375d83efa872fdf80797a23b99158f763a7e36  R1/R1.categories_default_exceptions_r4/fixtures.jsonl
525a3af16146dafe72e179597cd141a106245832d1adcbe010e126ea802108cd  R1/R1.categories_default_exceptions_r4/SCHEMA.md
d53ce81941927f0900f299ded444be9e76c7342152b56f36c5b195554079068b  R1/R1.compass_turns/fixtures.jsonl
94163b0796e0d6fabb27ae5eedd4e2eb8e26fcd8c01d2e2b5590c0d01079ae1a  R1/R1.compass_turns/SCHEMA.md
88cb00e0da0683d441cf1fb344046b40e82958bb499eb2d358d746b4d258e5ff  R1/R1.conditional_threshold_rule_r4/fixtures.jsonl
89b1b3441387b0dda25ba210b9fb1a9622f69708fd87a7954d582c5c3d1325cd  R1/R1.conditional_threshold_rule_r4/SCHEMA.md
a410cd71a426060221996f1d05c9433176bfe4701c971f592c44e8d205f0a9b7  R1/R1.equivalence_exchange_rates_r6/fixtures.jsonl
e47137f64aeacdf5379899c1b8360b4786c3d794948b66fbcc2313c9b0c36316  R1/R1.equivalence_exchange_rates_r6/SCHEMA.md
12da83e011ba3899d041f59d91dd0cb58f9e5088f1490dbb771e5ccbf26db0b4  R1/R1.knights_knaves_r6/fixtures.jsonl
20165f6fe617005d43d427180ef013e178d4ae693adee35678fce5b437ed6749  R1/R1.knights_knaves_r6/SCHEMA.md
61631a0b436d3ffcf3e41a28969ee9655540507957c4127ec4d01e98819b9985  R1/R1.spatial_grid_walk_r5/fixtures.jsonl
ee8cd07d644a61f8c45bc49fbcca6a66030b7428bdd3d3f8cd1012aa02465d04  R1/R1.spatial_grid_walk_r5/SCHEMA.md
b290f5c7336d1b4c555383485831c753afae0048c63e4dc1f08c024785579a7a  R1/R1.swap_tracking_r5/fixtures.jsonl
c86a1674c195552c59e3e9c39c2edad8bb4e7a34f7c72f2ecb85c6237116ec00  R1/R1.swap_tracking_r5/SCHEMA.md
03b51a51ad9660941fe5a161ce28033c5573d2fcff500218bd4e2e383e1172be  R1/R1.temporal_weekday_shift_r6/fixtures.jsonl
f8c9a630c5f7f34b9d33b404969c372906fbe20d4da0ffbf461d9cb1e694e576  R1/R1.temporal_weekday_shift_r6/SCHEMA.md
3872dbf5f93e32149be5a7279fdaaf72cb99fa43c1596ff34b3a2877b6501c28  R1/R1.venn_counting_r5/fixtures.jsonl
b9b52771ac4106a8c3d1f26d5e9e32ddda8a19b39026be8fd949d83f266ed525  R1/R1.venn_counting_r5/SCHEMA.md
e4b0de60693f1f038b3d4b8426103575e05810b19902d78c236f64500e16ed0b  R2/R2.binary_search_trace/fixtures.jsonl
343071796a87e0d4d5717516084b2ad93f2cc22be9e4b33286cd0e39a00b4202  R2/R2.binary_search_trace/SCHEMA.md
1b0b992bcc659686640fbed5231b7b1c20d044615b88e98d07af6e6f03e13e3f  R2/R2.caesar_shift/fixtures.jsonl
6877eede0d50974cba66194c14b514d0d17669e6cc16afcc3bff9406eba28d8a  R2/R2.caesar_shift/SCHEMA.md
0eb22e6a9c571203e42df12aeb41b25829aee9a9abbd7500bed669ba679e8bdf  R2/R2.cellular_automaton/fixtures.jsonl
05b8d95677371fda45e6d4c97e708d01540b8dd4ac097fb519c6aee7fe33bc10  R2/R2.cellular_automaton/SCHEMA.md
c1b88cdcba2447292c43f38bb92997d199170c59a80b8839cc3ff221466ee368  R2/R2.cheapest_network/fixtures.jsonl
366279814ef0984bac792d4f97b6fc1cbd4f665a7acf3af51f607cdfcd673de2  R2/R2.cheapest_network/SCHEMA.md
c075b9e0f8ce04123d2c628b39ba3e9bf9afb7f482f6dc106b584f70a10deb54  R2/R2.count_divisible/fixtures.jsonl
bbe6e7fa4df19f482ba46a1aa9e35c7348945cf3051f0e404620c9f681c1a5a1  R2/R2.count_divisible/SCHEMA.md
7d8b7d50f50eadb86ad390b40fd28d49ba1bd7f22fc8d91a2a45e5159be4d3c0  R2/R2.crt_smallest/fixtures.jsonl
04bc3c6a0805e5ecd75c83786640880e85e94978a889e84697e2f3f69424d862  R2/R2.crt_smallest/SCHEMA.md
83f839d3bc3f30adb3c955a771aea96f83e8ff952b292057f57ee86ffbfe72ab  R2/R2.dictionary_rank/fixtures.jsonl
0b6878ecfd138535ca307977e170660cb73540270a4ce67160334345016e17a3  R2/R2.dictionary_rank/SCHEMA.md
16fb11ff7f8e8725032e03e9580c2386432a4b62f124957cb7d16d2b2f42d27d  R2/R2.expression_eval/fixtures.jsonl
8d47ef3c9a3c1a34240428b167c5bad1786834f23f81895f6e46ac3a68d8e332  R2/R2.expression_eval/SCHEMA.md
703ddffb1a0a52e96a9836309af184829580932e22a5e423d5d6a6baf79675d0  R2/R2.from_base/fixtures.jsonl
313a1844b24aa3ffc4611d29b3c9d0fb9b57193e2b5de25f1e84fa091f1f8847  R2/R2.from_base/SCHEMA.md
a3e12fec6240ab5337bf1c2f746b6dbf4a38e738b1b82f2257b81c79bc005fe6  R2/R2.grid_sum/fixtures.jsonl
635bd827ed5a1cab5dd208bb07276b97a8fdd1106a042403915c4f0e475a077d  R2/R2.grid_sum/SCHEMA.md
409b3d71168ae20e167ea692b8a3db4f86eb0796840ea04b762f1d3e952d0ffa  R2/R2.list_ops/fixtures.jsonl
73d929f743bd43359e61d4dfa8bf7700b5066fe39f10dc1ace2d2870503e0fe3  R2/R2.list_ops/SCHEMA.md
fa0a0f742da99a5a83c24676bf5e912869007a9cbb6dce258953a0f70e56ef67  R2/R2.luhn_check/fixtures.jsonl
2519366e3562fc2159573c4ec49733e98f4853f50b74cf679c5856a3b7bda88e  R2/R2.luhn_check/SCHEMA.md
f3831ebcf6a87403c4337082238a7bfa831ce619e5324ce2ebf1e02f037a1822  R2/R2.min_heap_ops/fixtures.jsonl
42f6fad694dbb60bd172d79b45e7064e9e5c99f0c451ca44466474489a95eab6  R2/R2.min_heap_ops/SCHEMA.md
8f5a582e0d3a3f2ca822e134dc4fe2b57210d5098a219bf47cbd092cdc2e4d62  R2/R2.run_length/fixtures.jsonl
61c4898a7def529b4a43c796eadb165874d3a98a1f96a83d65bc7225019c893c  R2/R2.run_length/SCHEMA.md
e3bbf776f28bd0660a6dc45c6ae968e04793ec442681364f9ca245edc4d3153e  R2/R2.sort_list/fixtures.jsonl
8137dc4b1cf4f1f1923ee2d6e4bd45a29da1a0c8a6891c37bc752b0cd3697a18  R2/R2.sort_list/SCHEMA.md
417b194486e8cf056b9abcd1253ccd257882e0e3bc89c6353914c4c5b0e0f14f  R2/R2.string_rewrite_nonidentity/fixtures.jsonl
7ded0fadd41efcffc96a0638b94c97eebee24524f7affd28f03521e7498cd6f8  R2/R2.string_rewrite_nonidentity/SCHEMA.md
ab251d8b4c4cf92866487f1154a0f374352101eba9cd3aa8115cb3a861144594  R2/R2.to_base_wide/fixtures.jsonl
f22180a5aacc48022ac266d3fbb5b7f87f7ab67b2040e062858548c9579677f3  R2/R2.to_base_wide/SCHEMA.md
f4541046079323017b9f9516a94e4c9f6958fe938e0b107796ad8eedbe842801  M1/M1.ages_r3/fixtures.jsonl
c2739a00fd32eed24bd5cf35a91efe7cc8c7a1754679ed3de6a10de390cd78a1  M1/M1.ages_r3/SCHEMA.md
ee1ff991ea1b309510cf86fb3d6123fc0802aa7936539b9e2f8df6c8259fc51c  M1/M1.arithmetic_series_r3/fixtures.jsonl
2f1645db48de2e815fdcb2e7b228c8cb3a36f83c09f30e9a3390fa1aa680b49e  M1/M1.arithmetic_series_r3/SCHEMA.md
c4cc8ea883047ba9c18011b561b552daa97faa2b3d69c0678114d9d1f91f78ca  M1/M1.average_missing_r4/fixtures.jsonl
41aed9e0fc5029c9b25ec2b0390cd3a49849d6a016996e13b1de5b8fbb7ed023  M1/M1.average_missing_r4/SCHEMA.md
1b21901176a6f7f4616a9f92a1b3732177bd0e133e8c2d76645620d8bea3264d  M1/M1.change_ways_r3/fixtures.jsonl
0018c8b703bfb198f904320dc2ca41fa032f880603e445ae1bd380cea224e3f3  M1/M1.change_ways_r3/SCHEMA.md
3ad21b2732e7cbb226afe95e0f809a1951ed62b23c72930ba43740c54c661d97  M1/M1.clock_duration_r4/fixtures.jsonl
5f618ab785b8ae45ac94d3df9732c34bc5db9fa86fb2548ccc82e0a319a3af14  M1/M1.clock_duration_r4/SCHEMA.md
7dcd4caaae337ade06d93974bf487814b26ac307865815b8c78779b9a3e6741b  M1/M1.consecutive_r3/fixtures.jsonl
4d3d4291efde3fd7ffb542896de7c694f21854c6e14f0c2d93abb97cc57cf1de  M1/M1.consecutive_r3/SCHEMA.md
5d221f3ffba5a7da72623dadd8e50e0e88425e50fad9c457d49a34fde869ac92  M1/M1.crt_congruence_r3/fixtures.jsonl
da918429e363e3adbfdab61d5218835966290bc21e8d30eac1336429ad4965f9  M1/M1.crt_congruence_r3/SCHEMA.md
3b644f771dec27409cde8085c50119c553d2dcd2f3b2ee39aa8fb46085cbc2af  M1/M1.division_counting_r3/fixtures.jsonl
081a383d90c67832467d769e17be369df48fa48abe802511fa08a50fd7b42fdc  M1/M1.division_counting_r3/SCHEMA.md
c71d174e65a9b23dd7e7ed553e0166fa445e39e00d90e26750c389299664aaef  M1/M1.finite_differences_r4/fixtures.jsonl
baea69850f51d55992ed7de4367dab2db83ded21161303182edf4efa69ee4364  M1/M1.finite_differences_r4/SCHEMA.md
54f309236b367c58b554209f765919d484420033ff05a01f459e6e0d76eb5d7e  M1/M1.fraction_remainder_r3/fixtures.jsonl
9037833ba9c1f59236e8a5d70730fa6cfb2f088a28f19a44f9e8130b1b3d3370  M1/M1.fraction_remainder_r3/SCHEMA.md
995d1a42680c0ce18c7ade1f4b5d14373a1e621a8910ff419adeccdd5fb56337  M1/M1.gcd_lcm_r4/fixtures.jsonl
4dd7fbc9a6c976d3f95819213f0004c769574b0915e9faa3b88460e50224f452  M1/M1.gcd_lcm_r4/SCHEMA.md
ad9912c29109c7e1677dec119f9e90435b49d25a9f7aa589a07491d7d8c1a05e  M1/M1.grid_perimeter_r3/fixtures.jsonl
26e4c5c4840d985a76343e399fd47986bc780a4016cd34d2b9babf46317b1016  M1/M1.grid_perimeter_r3/SCHEMA.md
b2c200ec8af2a7ce70484c81898df4cb658dad1937f1b6192748e0dccdc57d83  M1/M1.inclusion_exclusion_r3/fixtures.jsonl
59d81aec884db1c4ea3ecd68d42490f11fc2b7060577da7d9099f2211091a83a  M1/M1.inclusion_exclusion_r3/SCHEMA.md
40f4b5a74204efc25774c4469890ab928c6fb9b43588853faa111bad820437b3  M1/M1.last_digit_power_r3/fixtures.jsonl
05b2118b94056062da60ba724e5dce1840f1762a05ab783824c4e03e3fa76139  M1/M1.last_digit_power_r3/SCHEMA.md
428745c6edc9327fc23af10cbff3a90b3de56885487223ad95efbc255b946268  M1/M1.linear_equation_r3/fixtures.jsonl
bc811d80eac4e4408ff20df10f985fc181004104774afc5adf5b3d8b5f4b21ab  M1/M1.linear_equation_r3/SCHEMA.md
dc1ca4266d90978a467840835a909605d064acd0ed72fb242ac021ed3e692d43  M1/M1.median_list_r3/fixtures.jsonl
82db2fcebef876e7165a4c80bc15bcb3e04e46390343098290677532df7b9430  M1/M1.median_list_r3/SCHEMA.md
30cf27a8b483057f1a605a74fd4c6c3cdcacd2375c2bd55134d0f044d0407015  M1/M1.mixture_r4/fixtures.jsonl
729588925fa210cea90a4901012a9d78119d191a514df8b9b8ea916fd8ef358b  M1/M1.mixture_r4/SCHEMA.md
ea4853762238d2ac772999694a055528f033da2de3ceb65b103eb6458e855741  M1/M1.painted_cube_r3/fixtures.jsonl
8336e11d97f8e7c39dcf4b0235765e5031bfa73fd3f67d49e6163e2c3b6156e5  M1/M1.painted_cube_r3/SCHEMA.md
336092c2e41881645d4cc950b2813bb6d49eccdd21712a976cbbcb937c1bea80  M1/M1.percent_change_r3/fixtures.jsonl
1b69c32311ee40f5d1f3873f1ba3eceed9fb4e1ddfb1e031f0c32e0a767f17af  M1/M1.percent_change_r3/SCHEMA.md
49b4099386bd847742186581c8b0c2c7a88ad9688e86adee4ac1c53c9584d939  M1/M1.pipes_work_r3/fixtures.jsonl
a93d9bba8ed177b22f5aa926f3c02c816809c00567eb3b68d6dfdd99990d4bdb  M1/M1.pipes_work_r3/SCHEMA.md
61be467b2f8476e54af588b5c2ffe12ae702fec46a3a17a879b4af2fe45483c4  M1/M1.prime_factors_r3/fixtures.jsonl
674fcf3dc422b23bf4d8ffce3b94d7b961ad52479a4fec5efff753d6a04cc890  M1/M1.prime_factors_r3/SCHEMA.md
587d42d2e9050e846191e5d526d0cc22db332151b1feab3d4ae5724b89ac1306  M1/M1.quadratic_area_r3/fixtures.jsonl
e1489fd325e421b1195b513affc778ba492ae5fa8153ae9cc49198067d95fdfe  M1/M1.quadratic_area_r3/SCHEMA.md
88a161cadcaa620b4ed784056a3c673be2d814b2f194f5852a01848f947fd83e  M1/M1.ratio_share_r3/fixtures.jsonl
a56d54bcac98815f40164fa9aaca7d9458fce161d6eae381a01649041ffb3156  M1/M1.ratio_share_r3/SCHEMA.md
4e9705935dbfed2a51c5efd341bc0d853a91a640129047c9e8a16bf00bc6a272  M1/M1.rectangle_r3/fixtures.jsonl
73e92b43bdb57cb9ae1e089dc405656e5678a44914a1781f15e92bfb1abcac07  M1/M1.rectangle_r3/SCHEMA.md
7de6dfe3c0dac133c41220262a3c7a924172e70811c579b0e97f70b9e3883685  M1/M1.recurrence_iterate_r3/fixtures.jsonl
bf48d185bea4384913d07e100ae710a5912f041a5ddaa2bd535f4352f58d2e10  M1/M1.recurrence_iterate_r3/SCHEMA.md
f2b3de6df3e9be1e75a4536ced38496aee909265a057896b60e4101090d943b6  M1/M1.shopping_r3/fixtures.jsonl
6a642c85eb27aebfd533e94232436b3e4d3b9f0a421849c51220b6a471995ee6  M1/M1.shopping_r3/SCHEMA.md
39e185b552838f1486cb211e5d7f18d84bbfa46c88c7d5f1765fc3781b235a11  M1/M1.speed_distance_r3/fixtures.jsonl
d7d52a058ff29f93b7e9cf6cdb64608f6213fdebebb9e4fcc709a0f8841c15ec  M1/M1.speed_distance_r3/SCHEMA.md
eaeb78ec3fb6054fab926a4fe2fcaaeec8578c092cb3502ec59ed4aeb3657a10  M1/M1.tiered_pricing/fixtures.jsonl
329b7465908f99c56e049db3b9e35342e0d0f763a726ab29e931dced613e97b1  M1/M1.tiered_pricing/SCHEMA.md
ada3e260a7e82bcb4045ce9d7fae5f83ade3bbc16a6cae93023990ccc8199b82  M1/M1.tip_split_r3/fixtures.jsonl
ae2040e7e675ba2848396af021cd913e5689cd225fe0bf036d50b8d3aa2757ff  M1/M1.tip_split_r3/SCHEMA.md
42a844d2c6821d32811215192f87a0fe25555dafab3c064c40c90cf5995d803c  C1/C1.binary_search_f3/fixtures.jsonl
6af812bad778c2c418eb4e8bf262cdadcd1db14ba7f1ee4fc15b8fdc9aa95d44  C1/C1.binary_search_f3/SCHEMA.md
be52264c1944fe1f5c045c095656b98a1b70ed67e5f1334b8ff7dc43d9ea1e09  C1/C1.bracket_matching_f3/fixtures.jsonl
5d33b54eb0d80cda4f566e6edd7f7a7fb871017a1fe18cfe5cddd13a90813474  C1/C1.bracket_matching_f3/SCHEMA.md
2f3e7f9716b90e84331ae6ad34ee180be0db2bf6a12994deabe1e5918e995a43  C1/C1.bytecode_loop_f3/fixtures.jsonl
061ae4e03581520466ea4017d1c060ad198fee134ded02cd2a6160c7ae449095  C1/C1.bytecode_loop_f3/SCHEMA.md
bf5d0681a85d26b09215a8df3a9e8d60fc749593313a5a46de4eb2d7672f288e  C1/C1.circle_elimination_r2/fixtures.jsonl
ba50955fe83e5f90abf061e31d06156eeeca7d5dfd927440c34b4b635efeddf2  C1/C1.circle_elimination_r2/SCHEMA.md
2901cc816320df6bbbeb0e06f6f35b64e8d9f25994f42233cc1d12e9574d279a  C1/C1.cond_chain_f3/fixtures.jsonl
818727d9e668b7f0fa7888c5c92c7be355ab396347f740ff3859e3111bdcdfab  C1/C1.cond_chain_f3/SCHEMA.md
132dc92346427e46bb0cec8742697e39a6dd629771937e59041e64f190135e8b  C1/C1.counter_list_f3/fixtures.jsonl
5cd372fca2cb9513c9a28186de497de6652f78b9f47b26bce42d2fbcd19ce1be  C1/C1.counter_list_f3/SCHEMA.md
c94d516cf34b8304413e05babecdac474fe8694086c2e5c2fd746fad24e15598  C1/C1.digit_peel_f3/fixtures.jsonl
8dcba16a71e05cf20a237ce0ccaaf92df9da90513c0943c488112f5291b8831c  C1/C1.digit_peel_f3/SCHEMA.md
d5229a6e8ae49ac2096df152c1fa0d7e90bb732b08e6c81bfb1d12ef91608148  C1/C1.euclid_gcd_traced_f3/fixtures.jsonl
2833ab99affbefc7c7dff0e3c0229c273174ff527b00e1cbabe586382bf6df20  C1/C1.euclid_gcd_traced_f3/SCHEMA.md
04c36129437cceb2a508db4fd32fdbf2391fdcdcd45af69a5c1cfdbaf2a54e66  C1/C1.fast_power_f4/fixtures.jsonl
9bf575b5f799a217c6ae4457a473ce41d2d9a98333e9bf63550c237b3921d156  C1/C1.fast_power_f4/SCHEMA.md
d4e0f4b202345b2be672ab2c6e3e4991ca081517d8182314ee0675f342d42eba  C1/C1.fib_like_f3/fixtures.jsonl
8c4f51513608cfa82decbd8067783f2ef2ef48c4331641dc349089bd10364dbb  C1/C1.fib_like_f3/SCHEMA.md
404f955b1828ee6937dfa916e0c0ae178a557ebb92d695ad7ef356b7e30eb75b  C1/C1.fib_shapes_recursive_f3/fixtures.jsonl
dfed0124c250931702275665b82d6895d7a7e42a739ccb94dc28ac4bcc7bd344  C1/C1.fib_shapes_recursive_f3/SCHEMA.md
e137248121e8d283ea2dd126f27b84aa0f92b3a19ed8572b4ed416b6af93bd60  C1/C1.func_branch_f4/fixtures.jsonl
83d9821102df3a9abd8eef55494aee0df241499fcd428f75fc7f20544098c6ac  C1/C1.func_branch_f4/SCHEMA.md
45c7541e7b78f28bc3428c85aec34ffc52cc65a1eb074b75937ed993b5ae23e1  C1/C1.func_compose_f4/fixtures.jsonl
29700f4dda0bf50a941ce2a4b5e73fcced803eaadbd973b9552a0d886d2eec83  C1/C1.func_compose_f4/SCHEMA.md
808a4e7c1103d52cab8dd6b9e8be5ec39aeda2616ee9b1ba6f3e7790324b7fa5  C1/C1.list_build_f3/fixtures.jsonl
39670711cd0add15a6090e4d5a4d3998c18b7f91bbf12e26e6dee6966166b07d  C1/C1.list_build_f3/SCHEMA.md
66ffdbc5b1b3a88b89bca467b93cb00ef64cee167488f34cdb79710d2f47291a  C1/C1.merge_two_sorted_f3/fixtures.jsonl
a9a052b99172258ba826984612807f3cf58f88d495c96933104ce09ecbfdfc24  C1/C1.merge_two_sorted_f3/SCHEMA.md
40cd1a375cfccb82e537e0794551ceaf11f382fe934a73c9f3fd724c4821e573  C1/C1.nested_pairs_f3/fixtures.jsonl
87d38c6ec414ae3d5849e762d63fd719dbe4ed262a245ac56b6febd47676c493  C1/C1.nested_pairs_f3/SCHEMA.md
059fad2f522673f0fbbc05395df6f25d6230b08b3f318460fd4d7f968f465dce  C1/C1.postfix_evaluation/fixtures.jsonl
bf185aaf4632c70bebbefbe7f879392c6bff68e9184071fb150fbe22dc319b24  C1/C1.postfix_evaluation/SCHEMA.md
ac211558d52d91e65de8b522e368efe3eeac6dd3cd190757c67b3e429f9d4be4  C1/C1.recursive_calls_r2/fixtures.jsonl
a5568e953d4957bd31a6cb09ae05b25d505184ba8932aedf6131097faf381f42  C1/C1.recursive_calls_r2/SCHEMA.md
fb5e7665a52e5ccdc4ceaf7713e8a435aeefa287b59273d218f15f5648466f0b  C1/C1.run_length_scan/fixtures.jsonl
8bbdf69aba81b1b1580abff688ce8f4da9dacc270e82bad3bc62927d1f0f5a39  C1/C1.run_length_scan/SCHEMA.md
4cd26cff2b1047a9df41b42c29e1853a6b6acba8fceb097536910049c62f8722  C1/C1.shared_lists_f3/fixtures.jsonl
a6906998a1552e941a2a3aff4b5f64fda352fd09b6ef452af80cf432b164a8a5  C1/C1.shared_lists_f3/SCHEMA.md
e71e2e678f2424abdd9a7d9adfc1325516e30b2fd27501e5e60a0329496941f7  C1/C1.slices_f4/fixtures.jsonl
bc29c93d27c05ea6a908a8299dc5fa721d07d7b5e7f3380ae0cd5e1338d603c0  C1/C1.slices_f4/SCHEMA.md
32d7b87ce5b68ad9f47ab5ceb6770f2cc5e0a9764df537f070c0b61f118e3365  C1/C1.string_build_f3/fixtures.jsonl
046af3db5e9d4a6c4aac06f4284afe1f9024708cbf0bd13d99d02a5d8c35e3ca  C1/C1.string_build_f3/SCHEMA.md
a96a2303652451889d7a1e1b019cf8c5261ad572072c1a5ee82d1af01178a29a  C1/C1.string_methods_f3/fixtures.jsonl
1dd4b6977614ac7f30ba42662d4ffe29d1f4b027908ec8b116ceb12d5b921c71  C1/C1.string_methods_f3/SCHEMA.md
43f776ab93e8327e7391dcfc89b7bf2cb54565e1b00c21dc3719c1b32f493f18  C1/C1.turtle_walk_f3/fixtures.jsonl
84fd676c1dca657b1fbdcba5d9ece81b331e9dd9d2c33148019e7205fbf80f9a  C1/C1.turtle_walk_f3/SCHEMA.md
341defaef8257f070f2d8f5d23174946e02ef4bbc926b37aa3acd374c6ce90ef  C1/C1.union_find_links_f3/fixtures.jsonl
3125dafa782b18126c9324e732fa72eabf6928f8274c0b085030dea760b0413a  C1/C1.union_find_links_f3/SCHEMA.md
ce2b515791a1373c1fb82b136e29545ae06e79a15cb6b215ab5302f8b157fb8c  C1/C1.while_counter_f3/fixtures.jsonl
5ba98f613b556907cfac1d0cbef64fa1ca2c5819618e567d91e90483bc785b18  C1/C1.while_counter_f3/SCHEMA.md
```
