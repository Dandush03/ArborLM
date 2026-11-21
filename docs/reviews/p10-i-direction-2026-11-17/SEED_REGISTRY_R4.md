# P10-I seed registry — revision 4 (addendum)

> **Revision 4 — 2026-11-19 (UTC), `arbor-auditor` (Claude Opus 5.5, `claude-opus-5-5`), at the lead's request.** This file is an addendum to `SEED_REGISTRY.md`. Under the registry's own rule (section 4.5 item 5; revision 2 item 6), a revision is written as new files and records the hashes of the old ones. `SEED_REGISTRY.md`, `seed_registry_check.py` and `seed_registry_check_r3.py` were not edited. Revision 4 (1) allocates the seeds of P10-I-S6 (ADR-0031, approved for implementation and rehearsal only on 2026-11-19), (2) records corrections for P10-I-S3 (ADR-0026) and P10-I-S5 (ADR-0028), both executed, and (3) adds a checker, `seed_registry_check_r4.py`. That checker treats an executed study's allocation hitting that study's own files as the known own-files case of ADR-0029 ruling 6. Checker result: **RESULT: PASS**, with 67 allocations, 0 problems and 124 known own-files cases that are not failures (section 9).
>
> **Status.** This is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. The P10-I-S6 registered run is not approved (ADR-0031 section 21, Decision 2 not given). Nothing here changes any seed, record, label or outcome of P1 to P10-I.

## 0. Repository state, files and hashes

- Worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-ii-s5-design` at `c8df9efa2c63b0c50128ca5786514562d797b379` (= `main`), plus one untracked draft, `docs/decisions/ADR-0030-p10-ii-s5-ssd-memory-on-trained-stores.md`. That draft is not approved, was not used, and has **nothing allocated** here. The checker's six-digit-literal scan (section [5], informational) excludes it, along with ADR-0023 to ADR-0031.
- ADR-0031 as read: SHA-256 `2db830d279470c49f10b3c451b205edeaca2f12184f4fc35f1a67399552854f8`.

| File | State | SHA-256 |
|---|---|---|
| `SEED_REGISTRY.md` (revisions 1–3) | unchanged | `7211706f1172e55aad445053b1d28294a24de5b6eb766f1d3cbb779ecb154f39` |
| `seed_registry_check.py` (revision 2 checker) | unchanged | `b078100689211a437d59d898e5a7fb04ee03fbcc2a388288e9f5e83dbe759289` |
| `seed_registry_check_r3.py` (revision 3 checker; cited by the S3, S5 and R configs) | unchanged | `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594` |
| `seed_registry_check_r4.py` (new, revision 4 checker) | new | `7bc791e0f24528020b9c3f569751f6528f30444a761b6bae514efad96acd81e8` |
| `SEED_REGISTRY_R4.md` (this file) | new | stated in the coordinator's commit; a file cannot contain its own hash |

## 1. P10-I-S6 (ADR-0031): final allocation

Cell index `c = 3p + s`: registered parent `p = 0..8`, seed position `s = 0..2`. Calibration parent `q = 0..2` (ADR-0031 G8). P_used draw `j = 0..3`.

### 1.1 Rows (blocks reserved to P10-I-S6)

| Role | Range | Used / size |
|---|---|---|
| Data block | **320001–329999** | — |
| registered streams | 320001–320099 | 27 / 99 |
| OA streams | 320101–320199 | 27 / 99 |
| registered P_used | 320201–320399 | 108 / 199 |
| spare (R-KNN was left out; 320401–320427 is not allocated to it) | 320401–320999 | 0 / 599 |
| parent order seeds | 321001–321999 | 12 / 999 |
| spare | 322001–328999 | 0 / 6,999 |
| calibration streams and P_used | 329001–329199 | 15 / 199 |
| dry-rehearsal stream, P_used and held DRY values | 329201–329299 | 5 (+2 held) / 99 |
| spare (R-KNN was left out; 329301–329303 is not allocated to it) | 329301–329999 | 0 / 699 |
| Initialisation sub-row (the first supplement sub-row of the P10-I spare) | **330701–330799** | 46 (+2 by revision 4) / 99 |
| Test range | **952001–952999** | — / 999 |
| P10-I spare initialisation sub-rows (was 330701–330999) | 330801–330999 | 0 / 199 |

### 1.2 Named values

| Role | Count | Values |
|---|---|---|
| Registered stream (shared by both arms of a cell, all rates and all rungs incl. rung −1) | 27 | 320001 + c (320001–320027) |
| OA stream (old nine parents × 3 seed positions) | 27 | 320101 + c (320101–320127) |
| Registered P_used (the same draws at every rung) | 108 | 320201 + 4c + j (320201–320308) |
| Order seed, registered new parents | 9 | 321001 + p (321001–321009) |
| Order seed, calibration new parents | 3 | 321091 + q (321091–321093) |
| Calibration stream | 3 | 329001 + q (329001–329003) |
| Calibration P_used (calibration controls; NEG-REF on calibration checkpoints) | 12 | 329031 + 4q + j (329031–329042) |
| Dry-rehearsal stream | 1 | 329201 |
| Dry-rehearsal P_used (also the planted-positive gate's P_used draws, as in P10-I-S3) | 4 | 329231–329234 |
| *Held* DRY OA stream: used only if the DRY profile runs OA as a separate item and needs its own stream | (1) | 329202 |
| *Held* DRY parent order seed: used only if the DRY profile trains a parent | (1) | 329211 |
| Addition initialisation, registered (one per cell; both arms) | 27 | 330701 + c (330701–330727) |
| Addition initialisation, OA (one per seed position, shared by the old nine parents) | 3 | 330731 + s (330731–330733) |
| Backbone seed, registered new parents | 9 | 330741 + p (330741–330749) |
| Backbone seed, calibration new parents | 3 | 330751 + q (330751–330753) |
| Addition initialisation, calibration (all three calibration cells, every rate, the prefix and resume gates) | 1 | 330791 |
| Addition initialisation, dry rehearsal; read-equality gate | 1 | 330792 |
| Planted-positive toy model, gate (**added by revision 4**) | 1 | 330793 |
| *Held* DRY parent backbone seed: used only if the DRY profile trains a parent (**added by revision 4**) | (1) | 330794 |
| Test-mode initialisation | 2 | 330798, 330799 |
| Test seeds (unit tests, synthetic resources) | — | 952001–952999 |

Not seeded, so no value is needed: X_mean, V_mean, X_mean_dense, BASE, the disabled and replay reads, the panel walk, the article exclusion, the SHA-256 ranking of the pool, rate selection, R16 and OA labels. OA runs no P_used, because ADR-0026's K1–K3 read Q, C and C_dense only. Not allocated: R-KNN (open choice 14, left OUT at Decision 1) and the continuation rung (choice 2(a); it has no seeds). Every value is in the initialisation row or in the data block, so every component seed `s + 1000·k` (k ≤ 10) of an initialisation value lies in the row's derivation reserve 331701–340799.

### 1.3 Conditions for the implementer (taken from the registry's rules; nothing new on the science)

1. No arithmetic derivation from a data, P_used, order or test seed (registry section 4.3 item 1; ADR-0031's own test). Checker section [9] shows why: there are 84 pairs (named S6 data value `d`, k ≤ 10) with `d + 1000·k` equal to a named P10-I initialisation value, for example 320001 + 10,000 = 330001, which is P10-I-S0's registered initialisation.
2. Synthetic and unit-test paths use 952001–952999 or the test-mode values 330798 and 330799. They must not use the P1 seeds 42–44, as P10-I-S3's synthetic backbones did (section 3.1). The equality test of the re-implemented planted-positive construction against `studies/p10i_s3/planted.plant` calls both with a test-mode value.
3. The order of the OA parents (`p` in `320101 + 3p + s`) is fixed in the config, for example P10-I-S3's parent order, and is not chosen later.
4. The calibration addition initialisation is a single value shared by the three calibration cells, as in P10-I-S3 (330391). This is ADR-0031's count, kept.
5. A held value is used only under its stated condition; the frozen config either lists it or omits it.

## 2. Differences from ADR-0031 section 14's proposal, value by value

| Value | Proposal | Revision 4 | Reason |
|---|---|---|---|
| all 194 data values and all 46 initialisation values of the proposal (R-KNN excluded) | as proposed | **unchanged** | 0 collisions under R1–R3 (checker sections [1], [2], [9]) |
| 952001–952999 | test range | unchanged | clear of every W1 image (941001 + 10,000 = 951001; P10-I tests + 10,000 ≤ 948999) |
| 330793 | no value (the planted-positive gate is named in section 11, but section 14 gives it no seed) | **added**: planted-positive toy initialisation | P10-I-S3 used the literal 1 here (section 3.1). A gate value in the study's own row avoids an undeclared re-use |
| 330794 | no value | **added, held**: DRY parent backbone | R3 runs "every registered stage" in the DRY profile, and P0 trains parents. Used only if DRY trains a parent |
| 329211 | no value | **added, held**: DRY parent order seed | as above |
| 329202 | no value | **added, held**: DRY OA stream | used only if DRY runs OA as a separate item that needs a distinct stream; otherwise DRY uses 329201 |
| 320401–320427; 329301–329303 | R-KNN store sampling (only if choice 14 is taken) | **not allocated** | choice 14 was left OUT; the values stay spare inside S6's block |
| 330701–330799 | "P10-I spare sub-rows" | becomes P10-I-S6's sub-row; the P10-I spare shrinks to 330801–330999 | registry rule 4.5 item 2 |

Nothing in the proposal was moved. Four values were added: one allocated (330793) and three held, each used only under its condition (330794, 329211, 329202). The lead can record them as an amendment note before the implementer's config is frozen. The order of the rule was not followed literally, but no value changes because of it: registry rule 4.5 lists 310001–319999 before 320001–329999, and 939001–939999 before 952001. ADR-0031 took the second of each to stay clear of the ADR-0030 draft. Both are free, and taking the second collides with nothing. 310001–319999 and 939001–939999 remain **unallocated**; this revision reserves nothing for ADR-0030. **PENDING LEAD REVIEW**: whether to record that departure from the rule's order.

## 3. Corrections of record for executed studies

Each correction was reconstructed by the checker (section [8]) from the frozen config and seed plan. Each was also compared with the study's own `planned_seed_values` function, which gave equal sets on every role (section [8], import half).

### 3.1 P10-I-S3 (ADR-0026, executed)

| What revision 3 says | What P10-I-S3 used | Evidence |
|---|---|---|
| Registered streams and permutations: 324 values (stream, P_all, P_used, X) | **351**: also the **joint-permutation seeds 260131 + c (260131–260157)** | `configs/p10i_s3_longer_training.toml:79` (`joint_base`); ADR-0026 section 9 table ("Joint-permutation seeds 27 + 3 + 1"; "the registry's ADR-0026 row is extended by the lead"); `studies/p10i_s3/freeze/seed_plan.json` `registered_joint` (27); `results/p10i-s3-run-2026-11-18/OUTCOME.md:58` ("The seed registry needs the joint-permutation seeds added") |
| Calibration: 36 values | **39**: also joint **269024–269026** | config `cal_joint_base = 269024`; seed plan `calibration` (39) |
| Dry rehearsal: 12 values | **13**: also joint **269222** | config `dry_joint = 269222`; seed plan `dry` (13) |
| Initialisation 330301–330303, 330391, 330392, 330398, 330399 | same | seed plan `init`, `test_init` |
| Test 935001–935999 (no values named) | test-profile values 935001–935081, 935101–935127, 935201–935227, 935301–935408, 935501–935608 (351), plus synthetic resources 935901 + seed | `studies/p10i_s3/core.py` `Seeds._t`; `studies/p10i_s3/stages.py:59` |

All of these lie inside P10-I-S3's existing rows, so no row changes. Revision 4's `NAMED_DATA` now lists all 403 data values P10-I-S3 used. Two facts of the record that revision 3 does not carry, both on synthetic paths only and touching no registered value: the planted-positive toy model is built with seed **1** (`studies/p10i_s3/planted.py:50`; component generators 1001–5001), and synthetic resources build backbones with `PilotModel("dense_small", 42 + parent % 3)`, which re-uses the P1 seeds **42–44** (`studies/p10i_s3/stages.py:53-68`). Both values were already in the inventory, and neither was declared as a re-use. **PENDING LEAD REVIEW**: whether P10-I-S3's record needs a note.

### 3.2 P10-I-S5 (ADR-0028, executed; engineering part)

ADR-0028 section 10 (revision 6) asks for exactly this: "For the registry's revision 4 (by the auditor, before the freeze)". The study was frozen and run with these values. They are recorded now, after the fact.

| Role | Revision 3 named | Used (`configs/p10is5_ssd.toml` `[seeds]`, `studies/p10is5/testing.py`) |
|---|---|---|
| Registered request orders ("query workloads") | 280001–280010 | **280001–280005, spare 280006** |
| Registered file contents ("store contents") | 280101–280103 | **280101** |
| Registered pass orders ("arm order") | 280201–280205 | **280201–280205, spare 280206** |
| Registered ANN build | 280301–280303 | none |
| Auxiliary | none (0 used) | **287001** (tile assignment) |
| R1 | 289001, 289011–289013, 289021, 289031 | **289001** (rehearsal file contents), **289013** (control file contents; role changed from "positive-control workload"; also the source of the harness's request order), **289011** (request order), **289021** (pass order), **289051** (re-read offsets) |
| Rehearsal | 289201, 289211, 289212, 289221, 289231 | **289211–289215** (M request orders; 289212's role changed from "second pattern"), **289216–289220** (K request orders), **289221–289225** (M pass orders), **289226–289230** (K pass orders), **289241**, **289242** (M, K tile assignments) |
| Initialisation 330501–330599 | held, unused | unused |
| Test 937001–937999 | — | 937001, 937011, 937021–937023, 937031–937033 |

Assigned in revision 3 and never used: 280007–280010, 280102, 280103, 280301–280303, 289012, 289031, 289201, 289231 (13 values). They stay inside S5's block and nothing else takes them. ADR-0028 also names 287101 and 287102 as "unassigned"; they stay unassigned. Every used value lies in S5's revision-3 rows, so no row changes.

### 3.3 P10-I-R (ADR-0029, executed)

Revision 3 holds it exactly. Bridge sets (160 values), I64 index seeds 298001–298003, rehearsal set 299201 (32 values), and initialisation 330601–330605, 330692, 330698 and 330699 all equal the config and `gates.planned_seed_values`. Two roles revision 3 did not name both lie in its test row, so there is no correction, only this note: test index seeds 938901–938903, and test sets of 288 values (9 sets, 938001–938861).

## 4. Declared re-uses added for P10-I-S6 (not allocations, not collisions)

| Purpose | Values | Source |
|---|---|---|
| OA anchor (old nine parents read by hash) and adapter identity gate (reproduce them bitwise): the P2/P3 control lineage of P10-I-S3's parents | backbone 101, 102, 103; order 301, 302, 303 | `src/arborlm/p2_config.py:34-36`, `p2_model.py:20-22`, `p2_data.py:151-156`; ADR-0031 sections 7 and 16a G9–G10 |
| Adapter identity gate, only if it needs the frozen control memory (G9) | 201 and its components 1201, 2201, 3201, 4201, 5201 | `src/arborlm/p2_config.py:48`; `pilot_model.py:110-124` |
| Process default generators set by `engine.configure_cpu` (`random.seed(42)`, `torch.manual_seed(42)`), part of the P2/P3 lineage and of every study's set-up | 42 | `src/arborlm/engine.py:26-27` |

The OA's three addition initialisations (330731–330733) and its streams (320101–320127) are **new** values. They do not re-use P10-I-S3's 330301–330303 or 260001 + 3c + g. Checker section [7]: each re-used value is in the inventory and lies in no P10-I allocation.

## 5. Corrections to the registry's text (SEED_REGISTRY.md is not edited; read these as superseding)

1. Section 4.1: "The row sits 20,000 above the highest P10-I data block, so even W1 … cannot reach it" **is no longer true**. The highest P10-I data block now ends at 329,999, two below the row. Under the binding rules nothing changes: R2 applies to initialisation seeds only, and R3 images of the block start at 320,001,000. Under W1, which is informational, the block reaches 330,001–339,999. Condition 4.3 item 1 and ADR-0031's test that no data seed is expanded by + 1000·k are what keep the two apart (section 1.3 item 1).
2. Section 4.2: the row "P10-I spare | 330701–330999" becomes 330801–330999. P10-I-S3's and P10-I-S5's named values are as in section 3 of this file.
3. Section 4.5 rule: the next free data blocks are **310001–319999**, then 400001 upward. The next free initialisation sub-rows are **330801–330899** and **330901–330999**, then the next programme row 341001–341999. The next free test range is **939001–939999**, then **953001** upward.
4. Section 4.5 item 5 and the gates: the revision-3 checker as cited now prints `RESULT: FAIL` on `main`. It reports 124 binding lines, all of them an executed study's allocation hitting its own config, code or tests (P10-I-S3 52, P10-I-S5 38, P10-I-R 34; revision-3 output kept at `experiments/_scratch/seed_registry_r4/r3_unchanged_on_c8df9ef.txt`). Revision 4's checker classifies exactly those 124 as the own-files case. A later study cites `seed_registry_check_r4.py` by SHA-256, runs it **without editing it**, and passes its own file globs:
   ```sh
   uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r4.py --own "P10-I-S6 ADR-0031=configs/p10i_s6_*,studies/p10i_s6/*,tests/test_p10i_s6_*"
   ```
   It must print `RESULT: PASS`, and it checks its own values separately against its rows (as P10-I-S3, P10-I-S5 and P10-I-R did). The own-files exemption covers only a hit between a study's allocation and that **same** study's files. A hit on another study's files fails, as the self-test shows.

## 6. Collisions found and how they are resolved

- **Binding (R1–R3), revision 4 allocation:** none. Section [1] reports 0 problems.
- **ADR-0031 section 14 proposal against the inventory:** 0 actual, 0 conservative-only and 0 own-files collisions for the data block, the initialisation sub-row and the test range (section [2]).
- **Within the proposal:** the R-KNN values 320301 + c would have collided with P_used 320201 + 4c + j (320301–320308). The second review found this and the ADR moved R-KNN to 320401 + c. R-KNN is now out, so nothing is allocated.
- **Executed studies' own files:** 124 hits, all of them the known own-files case (section 5 item 4).
- **Informational only:** under W1 (section [3]), 84 (S6 data value, k) pairs reach named initialisation values (section 1.3 item 1). Section [5] finds six-digit literals of other studies' ranges in `studies/p10i_s3/freeze/seed_registry_check.py`, the frozen checker copy, which holds the whole ALLOC table, and in sizes such as 262144. None of them is a seed.

## 7. What revision 4 leaves unchanged

Every revision-3 allocation row, named value, declared re-use and rule, except the P10-I spare row (section 5 item 2) and S5's named values (section 3.2). The inventory rules R1–R3, K_MAX = 10, INDEX_SPAN = 1000 and the catch-alls are unchanged. The revision-4 inventory adds an owner to each file-derived entry and splits the literal-scan catch-all by owner; the union of values is unchanged. ADR-0023, ADR-0024, ADR-0025, ADR-0027 and their allocations are untouched.

## 8. Attempts (failed attempts kept)

All runs were from the worktree root, one process each. Outputs are in `experiments/_scratch/seed_registry_r4/`.

1. **Attempt 1: FAIL, my error.** I added a no-repeat check for named data values. P10-I-S4's Route A and Route B share values by design (section 4.7), so the check tripped on them. `[1]` was already 0 problems. Fixed by applying the check only to the studies revision 4 adds or corrects (S3, S5, S6). I also moved two `line_of` calls out of an f-string. Output: `attempt1_output.txt` (stdout and stderr together).
2. **Self-test (`--selftest`): FAIL, as required.** The three planted faults were all caught. An S6 row on 260131 (P10-I-S3's joint seed) gave 4 binding failures, including the hit on S3's own config, which is **not** excused for S6. An S6 initialisation value 330801 outside its sub-row failed twice ([structure] and [9]). A declared re-use 320001 inside an allocation was caught. Output: `selftest_output.txt`.
3. **Attempt 2: PASS** (below). With `--own` for S6's future file globs the output is identical apart from the header line, since no S6 file exists yet: `attempt2_with_own_s6.txt`.
4. **Revision-3 checker, unchanged, same tree:** `RESULT: FAIL`, `allocations: 56; problems: 124`. This is the own-files case; the file prints the first 40, all P10-I-S3 → its config. Output: `r3_unchanged_on_c8df9ef.txt`.

Command: `uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r4.py` (also `--tables`, `--selftest`, `--own STUDY=GLOBS`). Environment: macOS 27.2.1 (build 26B131), arm64 (Apple silicon), uv 0.12.15, Python 3.12.14, torch 2.8.0 from the locked environment. Torch is needed only for section [6] and the import half of [8]; it prints one NumPy warning to stderr, which is not part of the output below. Wall time 1.98 s (`/usr/bin/time -p`). Exit status 0. Counts: **67 allocations, 0 problems, 124 known own-files cases; 165 named initialisation and 705 named data values; 7 declared re-uses; 0 missing in [6]; 0 failures in [7], [8] and [9].**

## 9. Checker output (attempt 2, verbatim)

```text
SEED REGISTRY CHECK (P10-I) revision 4 — arbor-auditor, standard library only
root: /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1
rules: R1 identity; R2 s+1000k, k=1..10, on initialization seeds and on every inventory literal < 100000; R3 s*1000+i, i in [0,999], on every value >= 1000; in-set offsets enumerated per study
own files (ADR-0029 ruling 6): P10-I-S3 ADR-0026 = configs/p10i_s3_*, studies/p10i_s3/*, tests/test_p10is3_*; P10-I-S5 ADR-0028 = configs/p10is5_*, studies/p10is5/*, tests/test_p10is5_*; P10-I-R ADR-0029 = configs/p10ir_*, studies/p10ir/*, tests/test_p10ir_*
inventory: 68 entries, 51219 identity values (with overlaps); entries owned by a P10-I study: 6
named values checked: 165 initialization, 705 data (revision 4)

[1] binding: P10-I allocations (R1-R3 expanded) against the inventory (R1-R3 expanded) and against each other
    allocations: 67; problems: 0; known own-files cases (not failures): 124; revision-3-equivalent count (own files not separated): 124
    known own-files case: P10-I-R ADR-0029: 34 hits of its own allocation against its own files
    known own-files case: P10-I-S3 ADR-0026: 52 hits of its own allocation against its own files
    known own-files case: P10-I-S5 ADR-0028: 38 hits of its own allocation against its own files

[2] the drafts' own proposals under the same rules, against the inventory only
    (listed: collisions with a seed the code itself uses or derives; 'conservative' counts hits that exist only through
     the catch-all entries or the +1000k applied to small literals that are not initialization seeds; 'own-files' counts
     hits on an executed study's own files, which [1] classifies against the allocation)
    ADR-0023 draft 1 init 3001–3002: 14 actual collisions, 85 conservative-only, 16 own-files
       ADR-0023 draft 1 init [id] 3001..3002 = P10-S0 / initialization [+1000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+1000] 4001..4002 = P10-S0 / initialization [+2000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+2000] 5001..5002 = P10-S0 / initialization [+3000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+3000] 6001..6002 = P10-S0 / initialization [+4000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P8 / permutation [id] (src/arborlm/p8_core.py:113; src/arborlm/p8_eval.py:285; src/arborlm/p8_core.py:533)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P7-A/P7-B / test (budget) [id] (src/arborlm/p7a_study.py:823; src/arborlm/p7b_budget.py:97)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P10-S0 / initialization [+5000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+5000] 8001..8002 = P7-A/P7-B / test (budget) [id] (src/arborlm/p7a_study.py:823; src/arborlm/p7b_budget.py:97)
       ADR-0023 draft 1 init [+5000] 8001..8002 = P10-S0 / initialization [+6000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+6000] 9001..9002 = P6 / permutation [id] (src/arborlm/p6_common.py:196)
       ADR-0023 draft 1 init [+6000] 9001..9002 = P10-S0 / initialization [+7000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+7000] 10001..10002 = P10-S0 / initialization [+8000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+8000] 11001..11002 = P10-S0 / initialization [+9000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+9000] 12001..12002 = P10-S0 / initialization [+10000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
    ADR-0023 draft 1 init 3091–3092: 10 actual collisions, 18 conservative-only, 0 own-files
       ADR-0023 draft 1 init [id] 3091..3092 = P10-S0 / initialization [+1000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+1000] 4091..4092 = P10-S0 / initialization [+2000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+2000] 5091..5092 = P10-S0 / initialization [+3000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+3000] 6091..6092 = P10-S0 / initialization [+4000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+4000] 7091..7092 = P10-S0 / initialization [+5000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+5000] 8091..8092 = P10-S0 / initialization [+6000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+6000] 9091..9092 = P10-S0 / initialization [+7000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+7000] 10091..10092 = P10-S0 / initialization [+8000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+8000] 11091..11092 = P10-S0 / initialization [+9000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+9000] 12091..12092 = P10-S0 / initialization [+10000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
    ADR-0023 draft 1 data 300001–309999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0024 draft 1 init 2401–2405: 9 actual collisions, 9 conservative-only, 0 own-files
       ADR-0024 draft 1 init [id] 2401..2403 = P4 / initialization [+2000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+1000] 3401..3403 = P4 / initialization [+3000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+2000] 4401..4403 = P4 / initialization [+4000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+3000] 5401..5403 = P4 / initialization [+5000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+4000] 6401..6403 = P4 / initialization [+6000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+5000] 7401..7403 = P4 / initialization [+7000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+6000] 8401..8403 = P4 / initialization [+8000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+7000] 9401..9403 = P4 / initialization [+9000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+8000] 10401..10403 = P4 / initialization [+10000] (src/arborlm/p4_config.py:21)
    ADR-0024 draft 1 init 2491–2493: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0024 draft 1 data 240001–249999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0024 draft 1 test 924001–924999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0025 draft 1 data 250001–259999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0025 draft 1 test 259001–259999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0026 init 2601–2699: 9 actual collisions, 9 conservative-only, 0 own-files
       ADR-0026 init [id] 2601..2602 = P8 / initialization [+2000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+1000] 3601..3602 = P8 / initialization [+3000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+2000] 4601..4602 = P8 / initialization [+4000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+3000] 5601..5602 = P8 / initialization [+5000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+4000] 6601..6602 = P8 / initialization [+6000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+5000] 7601..7602 = P8 / initialization [+7000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+6000] 8601..8602 = P8 / initialization [+8000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+7000] 9601..9602 = P8 / initialization [+9000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+8000] 10601..10602 = P8 / initialization [+10000] (src/arborlm/p8_core.py:88)
    ADR-0026 data 260001–269999: 0 actual collisions, 0 conservative-only, 34 own-files
    ADR-0026 test 926001–926999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0027 init 2701–2799: 20 actual collisions, 30 conservative-only, 0 own-files
       ADR-0027 init [id] 2701..2702 = P9 / initialization [+1000] (studies/p9/core.py:149)
       ADR-0027 init [id] 2791..2792 = P9-I / initialization [+1000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+1000] 3701..3702 = P9 / initialization [+2000] (studies/p9/core.py:149)
       ADR-0027 init [+1000] 3791..3792 = P9-I / initialization [+2000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+2000] 4701..4702 = P9 / initialization [+3000] (studies/p9/core.py:149)
       ADR-0027 init [+2000] 4791..4792 = P9-I / initialization [+3000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+3000] 5701..5702 = P9 / initialization [+4000] (studies/p9/core.py:149)
       ADR-0027 init [+3000] 5791..5792 = P9-I / initialization [+4000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+4000] 6701..6702 = P9 / initialization [+5000] (studies/p9/core.py:149)
       ADR-0027 init [+4000] 6791..6792 = P9-I / initialization [+5000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+5000] 7701..7702 = P9 / initialization [+6000] (studies/p9/core.py:149)
       ADR-0027 init [+5000] 7791..7792 = P9-I / initialization [+6000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+6000] 8701..8702 = P9 / initialization [+7000] (studies/p9/core.py:149)
       ADR-0027 init [+6000] 8791..8792 = P9-I / initialization [+7000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       … 6 more
    ADR-0027 data 270001–279999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0028 data 280001–289999: 0 actual collisions, 0 conservative-only, 32 own-files
    ADR-0024 draft 3 (block X) data 240501–240901: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0024 draft 3 (block X) init 330121–330125: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0025 draft 3 data (disjoint draws) 250916–250917: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0025 draft 3 data (Part Q rehearsal) 252901–252914: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0027 draft 3 Route A data (streams d=6..9) 270501–270803: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0027 draft 3 init 330401–330405: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0028 draft 3 data (registered) 280001–280303: 0 actual collisions, 0 conservative-only, 6 own-files
    ADR-0031 section 14 data 320001–329999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0031 section 14 init 330701–330799: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0031 section 14 test 952001–952999: 0 actual collisions, 0 conservative-only, 0 own-files
    between drafts: 0

[3] informational (not binding): worst case, +1000k applied to EVERY value of every role, both sides
    hits: 10618; 5223 inside one study's own block or own files (not listed); the rest grouped by study pair (roles merged):
          32  P10-I-R ADR-0029  <->  P10-I-S3 ADR-0026 own files
          10  P10-I-R ADR-0029  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-R ADR-0029  <->  P10-I-S6 ADR-0031
          16  P10-I-R ADR-0029  <->  P10I / config literal
         682  P10-I-R ADR-0029  <->  P10IS5 / config literal
           8  P10-I-R ADR-0029  <->  Review diagnostics / unknown role
         280  P10-I-S0 ADR-0023  <->  P10-I-R ADR-0029
          25  P10-I-S0 ADR-0023  <->  P10-I-R ADR-0029 own files
          10  P10-I-S0 ADR-0023  <->  P10-I-S1 ADR-0024
           9  P10-I-S0 ADR-0023  <->  P10-I-S2 ADR-0025
           8  P10-I-S0 ADR-0023  <->  P10-I-S3 ADR-0026
          32  P10-I-S0 ADR-0023  <->  P10-I-S3 ADR-0026 own files
           7  P10-I-S0 ADR-0023  <->  P10-I-S4 ADR-0027
           6  P10-I-S0 ADR-0023  <->  P10-I-S5 ADR-0028
           6  P10-I-S0 ADR-0023  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S0 ADR-0023  <->  P10-I-S6 ADR-0031
          16  P10-I-S0 ADR-0023  <->  P10I / config literal
         244  P10-I-S0 ADR-0023  <->  P10IR / config literal
          12  P10-I-S0 ADR-0023  <->  P10IS5 / config literal
           2  P10-I-S0 ADR-0023  <->  Review diagnostics / unknown role
           6  P10-I-S1 ADR-0024  <->  P10-I-R ADR-0029
          30  P10-I-S1 ADR-0024  <->  P10-I-R ADR-0029 own files
         422  P10-I-S1 ADR-0024  <->  P10-I-S2 ADR-0025
           9  P10-I-S1 ADR-0024  <->  P10-I-S3 ADR-0026
          36  P10-I-S1 ADR-0024  <->  P10-I-S3 ADR-0026 own files
           8  P10-I-S1 ADR-0024  <->  P10-I-S4 ADR-0027
           7  P10-I-S1 ADR-0024  <->  P10-I-S5 ADR-0028
           7  P10-I-S1 ADR-0024  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S1 ADR-0024  <->  P10-I-S6 ADR-0031
          18  P10-I-S1 ADR-0024  <->  P10I / config literal
          18  P10-I-S1 ADR-0024  <->  P10IR / config literal
          14  P10-I-S1 ADR-0024  <->  P10IS5 / config literal
           3  P10-I-S1 ADR-0024  <->  Review diagnostics / unknown role
           7  P10-I-S2 ADR-0025  <->  P10-I-R ADR-0029
          35  P10-I-S2 ADR-0025  <->  P10-I-R ADR-0029 own files
          91  P10-I-S2 ADR-0025  <->  P10-I-S3 ADR-0026
          40  P10-I-S2 ADR-0025  <->  P10-I-S3 ADR-0026 own files
           9  P10-I-S2 ADR-0025  <->  P10-I-S4 ADR-0027
           8  P10-I-S2 ADR-0025  <->  P10-I-S5 ADR-0028
           8  P10-I-S2 ADR-0025  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S2 ADR-0025  <->  P10-I-S6 ADR-0031
         316  P10-I-S2 ADR-0025  <->  P10I / config literal
          21  P10-I-S2 ADR-0025  <->  P10IR / config literal
          16  P10-I-S2 ADR-0025  <->  P10IS5 / config literal
           4  P10-I-S2 ADR-0025  <->  Review diagnostics / unknown role
           8  P10-I-S3 ADR-0026  <->  P10-I-R ADR-0029
          40  P10-I-S3 ADR-0026  <->  P10-I-R ADR-0029 own files
         250  P10-I-S3 ADR-0026  <->  P10-I-S4 ADR-0027
           9  P10-I-S3 ADR-0026  <->  P10-I-S5 ADR-0028
           9  P10-I-S3 ADR-0026  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S3 ADR-0026  <->  P10-I-S6 ADR-0031
          24  P10-I-S3 ADR-0026  <->  P10IR / config literal
          18  P10-I-S3 ADR-0026  <->  P10IS5 / config literal
           5  P10-I-S3 ADR-0026  <->  Review diagnostics / unknown role
           9  P10-I-S4 ADR-0027  <->  P10-I-R ADR-0029
          45  P10-I-S4 ADR-0027  <->  P10-I-R ADR-0029 own files
          40  P10-I-S4 ADR-0027  <->  P10-I-S3 ADR-0026 own files
         250  P10-I-S4 ADR-0027  <->  P10-I-S5 ADR-0028
          10  P10-I-S4 ADR-0027  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S4 ADR-0027  <->  P10-I-S6 ADR-0031
         658  P10-I-S4 ADR-0027  <->  P10I / config literal
          27  P10-I-S4 ADR-0027  <->  P10IR / config literal
         214  P10-I-S4 ADR-0027  <->  P10IS5 / config literal
           6  P10-I-S4 ADR-0027  <->  Review diagnostics / unknown role
         251  P10-I-S5 ADR-0028  <->  P10-I-R ADR-0029
          50  P10-I-S5 ADR-0028  <->  P10-I-R ADR-0029 own files
          36  P10-I-S5 ADR-0028  <->  P10-I-S3 ADR-0026 own files
          55  P10-I-S5 ADR-0028  <->  P10-I-S6 ADR-0031
          18  P10-I-S5 ADR-0028  <->  P10I / config literal
         103  P10-I-S5 ADR-0028  <->  P10IR / config literal
           7  P10-I-S5 ADR-0028  <->  Review diagnostics / unknown role
          55  P10-I-S6 ADR-0031  <->  P10-I spare
         165  P10-I-S6 ADR-0031  <->  P10I / config literal
         165  P10-I-S6 ADR-0031  <->  P10IR / config literal

[4] informational (not binding): R3 also applied to values < 1000, both sides
    hits: 4
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..301999 hits inventory: All code and tests / literal scan [x1000+i] (71 literals in src/arborlm, studies, tests (files no P10-I study owns))
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..302999 hits inventory: P9 / config literal [x1000+i] (configs/p9_diagnostics.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2 / config literal [x1000+i] (configs/p2_optimization_followup.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2/P3 / data (order) [x1000+i] (configs/p2_optimization_followup.toml:7)

[5] informational: six-digit literals inside a P10-I allocation, in configs/*.toml, src, studies, tests (*.py),
    docs/decisions/*.md (ADR-0023..0031 excluded) and docs/reviews/**/*.py (P10-I review folders excluded); sizes are not seeds
    hits: 1071 occurrences; in the allocation's own study's files: 515 (P10-I-R ADR-0029 169, P10-I-S3 ADR-0026 154, P10-I-S5 ADR-0028 192); elsewhere: 556 occurrences of 182 distinct values
       240001 in P10-I-S1 ADR-0024 / data: block M registered draw sets (5): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:383
       240499 in P10-I-S1 ADR-0024 / data: block M registered draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:383
       240501 in P10-I-S1 ADR-0024 / data: block X fresh draw sets (5): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:384
       240901 in P10-I-S1 ADR-0024 / data: block X fresh draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:520
       240999 in P10-I-S1 ADR-0024 / data: block X fresh draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:384
       241001 in P10-I-S1 ADR-0024 / data: spare draw sets: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:385
       246999 in P10-I-S1 ADR-0024 / data: spare draw sets: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:385
       247001 in P10-I-S1 ADR-0024 / lane L data sets (PENDING: decided in the lane L revision): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:386
       247999 in P10-I-S1 ADR-0024 / lane L data sets (PENDING: decided in the lane L revision): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:386
       248001 in P10-I-S1 ADR-0024 / auxiliary: spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:387
       248999 in P10-I-S1 ADR-0024 / auxiliary: spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:387
       249001 in P10-I-S1 ADR-0024 / calibration draw sets (2): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:388
       249199 in P10-I-S1 ADR-0024 / calibration draw sets (2): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:388
       249201 in P10-I-S1 ADR-0024 / rehearsal draw set (1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:389
       249299 in P10-I-S1 ADR-0024 / rehearsal draw set (1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:389
       249301 in P10-I-S1 ADR-0024 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:390
       249999 in P10-I-S1 ADR-0024 / spare: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:390
       250001 in P10-I-S2 ADR-0025 / data: registered replicate sets (3): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:393
       250899 in P10-I-S2 ADR-0025 / data: registered replicate sets (3): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:393
       250901 in P10-I-S2 ADR-0025 / partition side, analysis, disjoint-draw permutations: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:394
       250916 in P10-I-S2 ADR-0025 / partition side, analysis, disjoint-draw permutations: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:521
       250917 in P10-I-S2 ADR-0025 / partition side, analysis, disjoint-draw permutations: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:521
       250999 in P10-I-S2 ADR-0025 / partition side, analysis, disjoint-draw permutations: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:394
       251001 in P10-I-S2 ADR-0025 / calibration: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:395
       251999 in P10-I-S2 ADR-0025 / calibration: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:395
       252001 in P10-I-S2 ADR-0025 / Part T rehearsal sets (i = 0..8): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:396
       252899 in P10-I-S2 ADR-0025 / Part T rehearsal sets (i = 0..8): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:396
       252901 in P10-I-S2 ADR-0025 / Part Q rehearsal partition side: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:397
       252914 in P10-I-S2 ADR-0025 / Part Q rehearsal partition side: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:521
       252999 in P10-I-S2 ADR-0025 / Part Q rehearsal partition side: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:397
       253001 in P10-I-S2 ADR-0025 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:398
       259001 in P10-I-S2 ADR-0025 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:516
       259999 in P10-I-S2 ADR-0025 / spare: 6 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:398
       262144 in P10-I-S3 ADR-0026 / registered streams and permutations: 104 occurrences, first configs/p10s1_capacity.toml:40
       263424 in P10-I-S3 ADR-0026 / registered streams and permutations: 3 occurrences, first tests/test_p10s1_classes.py:243
       270001 in P10-I-S4 ADR-0027 / data: registered draw sets (5): 8 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:408
       270501 in P10-I-S4 ADR-0027 / data: registered draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:522
       270803 in P10-I-S4 ADR-0027 / data: registered draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:522
       271001 in P10-I-S4 ADR-0027 / data: registered draw sets (5): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:457
       276999 in P10-I-S4 ADR-0027 / data: registered draw sets (5): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:408
       277001 in P10-I-S4 ADR-0027 / auxiliary: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:409
       278999 in P10-I-S4 ADR-0027 / auxiliary: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:409
       279001 in P10-I-S4 ADR-0027 / calibration draw sets (2): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:410
       279101 in P10-I-S4 ADR-0027 / calibration draw sets (2): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:455
       279199 in P10-I-S4 ADR-0027 / calibration draw sets (2): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:410
       279201 in P10-I-S4 ADR-0027 / rehearsal draw set (1): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:411
       279299 in P10-I-S4 ADR-0027 / rehearsal draw set (1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:411
       279301 in P10-I-S4 ADR-0027 / spare: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:412
       279401 in P10-I-S4 ADR-0027 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:458
       279501 in P10-I-S4 ADR-0027 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:458
       279999 in P10-I-S4 ADR-0027 / spare: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:412
       280001 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 8 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:415
       280011 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:461
       280101 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:462
       280102 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:462
       280103 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:462
       280201 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:463
       280206 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:463
       280301 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:464
       280302 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:464
       280303 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:464
       286999 in P10-I-S5 ADR-0028 / data: registered workloads / stores / orders: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:415
       287001 in P10-I-S5 ADR-0028 / auxiliary: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:416
       288999 in P10-I-S5 ADR-0028 / auxiliary: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:416
       289001 in P10-I-S5 ADR-0028 / calibration (R1): 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:417
       289011 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:465
       289012 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:465
       289013 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:465
       289021 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:465
       289031 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:465
       289199 in P10-I-S5 ADR-0028 / calibration (R1): 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:417
       289201 in P10-I-S5 ADR-0028 / rehearsal: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:418
       289211 in P10-I-S5 ADR-0028 / rehearsal: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:466
       289212 in P10-I-S5 ADR-0028 / rehearsal: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:466
       289221 in P10-I-S5 ADR-0028 / rehearsal: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:466
       289231 in P10-I-S5 ADR-0028 / rehearsal: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:466
       289299 in P10-I-S5 ADR-0028 / rehearsal: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:418
       289301 in P10-I-S5 ADR-0028 / spare: 2 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:419
       289999 in P10-I-S5 ADR-0028 / spare: 4 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:419
       290001 in P10-I-R ADR-0029 / data: bridge draw sets (5): 3 occurrences, first studies/p10i_s3/freeze/seed_registry_check.py:422
       … 102 more distinct values

[6] cross-check: every seed the studies' own functions declare lies inside the reconstruction
     P10-S0 check: 69 seeds, 0 outside the reconstruction
     P10-S0 check_rehearsal_init: 2 seeds, 0 outside the reconstruction
     P10-S0 init: 2 seeds, 0 outside the reconstruction
     P10-S0 registered: 897 seeds, 0 outside the reconstruction
     P10-S0 rehearsal: 69 seeds, 0 outside the reconstruction
     P10-S0 reserve: 138 seeds, 0 outside the reconstruction
     P10-S0 test: 552 seeds, 0 outside the reconstruction
     P10-S1 calibration: 64 seeds, 0 outside the reconstruction
     P10-S1 derived_init: 60 seeds, 0 outside the reconstruction
     P10-S1 init: 12 seeds, 0 outside the reconstruction
     P10-S1 registered: 160 seeds, 0 outside the reconstruction
     P10-S1 rehearsal: 32 seeds, 0 outside the reconstruction
     P10-S1 test: 999 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(calibration): 110 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-analysis): 1 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-data): 11 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-run): 44 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(rehearsal): 110 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(test): 999 seeds, 0 outside the reconstruction
     P10-S2 listed_partition_seeds: 12 seeds, 0 outside the reconstruction
     P9 registered_seed_values: 22 seeds, 0 outside the reconstruction
     P9-I calibration_data: 20 seeds, 0 outside the reconstruction
     P9-I calibration_init: 2 seeds, 0 outside the reconstruction
     P9-I p9_registered: 22 seeds, 0 outside the reconstruction
     P9-I registered_data: 20 seeds, 0 outside the reconstruction
     P9-I registered_init: 2 seeds, 0 outside the reconstruction
     P9-I rehearsal_data: 180 seeds, 0 outside the reconstruction
     P9-I test: 60 seeds, 0 outside the reconstruction
     P9-II calibration_data_3: 24 seeds, 0 outside the reconstruction
     P9-II calibration_data_4: 24 seeds, 0 outside the reconstruction
     P9-II calibration_init: 2 seeds, 0 outside the reconstruction
     P9-II init: 2 seeds, 0 outside the reconstruction
     P9-II p9_registered: 22 seeds, 0 outside the reconstruction
     P9-II p9_rehearsal_other: 168 seeds, 0 outside the reconstruction
     P9-II p9i_registered: 24 seeds, 0 outside the reconstruction
     P9-II registered: 336 seeds, 0 outside the reconstruction
     P9-II rehearsal_data_5: 24 seeds, 0 outside the reconstruction
     P9-II reserve: 48 seeds, 0 outside the reconstruction
     P9-II test: 72 seeds, 0 outside the reconstruction

[7] declared re-uses (read-only use of a completed study's seeds; not allocations, not collisions)
     P10-I-S0 ADR-0023: identity gate part (a): P10-S0 rehearsal data set (base 209101), read-only, bit-identity at 4,096 and 16,384 slots: 69 values, 209101–209142, 209145–209146, 209149–209153, 209161–209180 (69 values); source studies/p10s0/core.py:424 (REHEARSAL_BASE), :489 (REHEARSAL_SET), :541 (check_seed_set); not in inventory: 0; inside a P10-I allocation: 0
     P10-I-S0 ADR-0023: identity gate part (a): P10-S0 rehearsal initialization seed 2092 and its +1000k component seeds: 6 values, 2092, 3092, …, 6092, 7092 (6 values); source studies/p10s0/core.py:145 (REHEARSAL_INIT); studies/p9/model.py:272-279; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-R ADR-0029: stage A1 reproduction reads: P10-S1 registered draws 1..5 incl. index seed (base + 60): 160 values, 210001–210014, 210021–210023, …, 210441, 210451–210461 (160 values); source studies/p10s1/core.py:812-877; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-R ADR-0029: adapter identity gate (section 10): P10-S1 cells F-OQ and T-OQ at 8K/4K, draw 1 (set 210001) with initialization seed 2101 and its component seeds: 38 values, 2101, 3101, …, 210041, 210051–210061 (38 values); source studies/p10s1/core.py:486 (2100 + r), :812 (REGISTERED_BASE), :820 (SEED_RANGE whitelist); not in inventory: 0; inside a P10-I allocation: 0
     P10-I-S6 ADR-0031: OA anchor (old nine parents, read-only by hash) and adapter identity gate (reproduce them bitwise): the P2/P3 control lineage seeds the old parents (also P10-I-S3's parents) were built from, backbone 101-103 and order 301-303: 6 values, 101–103, 301–303 (6 values); source src/arborlm/p2_config.py:34-36; src/arborlm/p2_model.py:20-22; src/arborlm/p2_data.py:151-156; ADR-0031 sections 7, 16a G9-G10; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-S6 ADR-0031: adapter identity gate, only if it needs the frozen control memory (ADR-0031 G9): control memory seed 201 and its component seeds: 6 values, 201, 1201, …, 4201, 5201 (6 values); source src/arborlm/p2_config.py:48 (control_memory_seed); src/arborlm/pilot_model.py:110-124; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-S6 ADR-0031: process default generators set by engine.configure_cpu (random.seed(42), torch.manual_seed(42)), part of the P2/P3 lineage and of every P10-I study's process set-up: 1 values, 42; source src/arborlm/engine.py:26-27; not in inventory: 0; inside a P10-I allocation: 0

[8] executed P10-I studies (revision 4): values used, from frozen configs and seed plans, against the record and their rows
     P10-I-S3 ADR-0026: frozen seed plan = config formula for 9 roles; data values used 403 (registered 351, calibration 39, dry 13); joint 260131–260157, 269024–269026, 269222 among them
     P10-I-S3 ADR-0026: data values 260001–260081, 260101–260127, …, 269231–269234, 269251–269254 (403 values); outside the study's data rows: 0
     P10-I-S3 ADR-0026: init values 330301–330303, 330391–330392, 330398–330399 (7 values); outside the study's init rows: 0
     P10-I-S3 ADR-0026: test values 935001–935081, 935101–935127, …, 935301–935408, 935501–935608 (351 values); outside the study's test rows: 0
     P10-I-S3 ADR-0026: note (not a failure): the planted-positive toy model is built with seed [1] (studies/p10i_s3/planted.py:50); synthetic resources use test seed 935901 + seed and backbones PilotModel('dense_small', 42 + parent % 3) (studies/p10i_s3/stages.py:59): undeclared re-uses of inventory literals 1 and 42-44 on synthetic paths only
     P10-I-S5 ADR-0028: values used 41 (registered 13, auxiliary 1, R1 5, rehearsal 22); test [937001, 937011, 937021, 937022, 937023, 937031, 937032, 937033]; revision-3 values never used: 280007–280010, 280102–280103, 280301–280303, 289012, 289031, 289201, 289231 (13 values)
     P10-I-S5 ADR-0028: data values outside the study's data rows: 0
     P10-I-S5 ADR-0028: test values outside the study's test rows: 0
     P10-I-R ADR-0029: data values 290001–290014, 290021–290023, …, 299241, 299251–299261 (195 values); outside the study's data rows: 0
     P10-I-R ADR-0029: init values 330601–330605, 330692, 330698–330699 (8 values); outside the study's init rows: 0
     P10-I-R ADR-0029: test values 938901–938903 (3 values); outside the study's test rows: 0
     import P10-I-S3 gates.planned_seed_values[calibration]: 39 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[dry]: 13 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[init]: 5 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[init_components]: 35 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[registered_joint]: 27 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[registered_p_all]: 27 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[registered_p_used]: 108 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[registered_streams]: 81 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[registered_x]: 108 values; equal to the reconstruction: True
     import P10-I-S3 gates.planned_seed_values[test_init]: 2 values; equal to the reconstruction: True
     import P10-I-S5 gates.planned_seed_values[auxiliary]: 1 values; equal to the reconstruction: True
     import P10-I-S5 gates.planned_seed_values[r1]: 5 values; equal to the reconstruction: True
     import P10-I-S5 gates.planned_seed_values[registered]: 13 values; equal to the reconstruction: True
     import P10-I-S5 gates.planned_seed_values[rehearsal]: 22 values; equal to the reconstruction: True
     import P10-I-S5 gates.planned_seed_values[test]: 8 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[bridge_sets]: 160 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[derived_initialisation]: 40 values (R2 images of the initialisation seeds; not compared)
     import P10-I-R gates.planned_seed_values[i64_index_seeds]: 3 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[initialisation]: 8 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[rehearsal_set]: 32 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[test_index_seeds]: 3 values; equal to the reconstruction: True
     import P10-I-R gates.planned_seed_values[test_sets]: 288 values, 938001–938014, 938021–938023, …, 938841, 938851–938861 (288 values); outside the test row: 0

[9] P10-I-S6 (ADR-0031 section 14) against the revision-4 allocation
     P10-I-S6 ADR-0031: named data 196, named initialisation 48; test row 952001–952999 (proposal 952001–952999)
     P10-I-S6 ADR-0031: proposal values kept: data 194 of 194, initialisation 46 of 46
     P10-I-S6 ADR-0031: proposal values moved or dropped: data [], initialisation []
     P10-I-S6 ADR-0031: values added by revision 4 (roles the proposal left without a value): data [329202, 329211], initialisation [330793, 330794]
     P10-I-S6 ADR-0031: R-KNN values of the ADR text (320401–320427, 329301–329303) named in the allocation: [] (open choice 14 left OUT)
     P10-I-S6 ADR-0031: informational (W1, not binding): S6 named data values d with d + 1000k equal to a named P10-I initialisation value: 84; e.g. 320001+10000=330001 (P10-I-S0 ADR-0023), 320002+10000=330002 (P10-I-S0 ADR-0023), 320101+10000=330101 (P10-I-S1 ADR-0024), 320102+10000=330102 (P10-I-S1 ADR-0024)

RESULT: PASS
```

## 10. Open points

1. **PENDING LEAD REVIEW**: the lead may record the four added S6 values (330793; held 330794, 329211 and 329202) as an amendment note to ADR-0031 section 14 before the config freeze (section 2).
2. **PENDING LEAD REVIEW**: whether to note S6's departure from rule 4.5's order of blocks and test ranges (section 2).
3. **PENDING LEAD REVIEW**: whether P10-I-S3's record needs a note about its undeclared synthetic-path literals 1 and 42–44, and whether P10-I-S5's record needs one about its values being registered after the fact (sections 3.1 and 3.2).
4. Unknowns of revision 3, section 7, are unchanged: unbounded P9 rehearsal draws, 941001, hash-derived seeds, and literal coverage.

`Astra review: NOT_PERFORMED`. This is independent engineering evidence by the `arbor-auditor` subagent (Claude Opus 5.5). It is not Astra validation and not human approval.
