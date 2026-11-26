# P10-I seed registry — revision 5 (addendum)

> **Revision 5 — 2026-11-20 (UTC), `arbor-auditor` (Claude Opus 5.5, `claude-opus-5-5`), at the coordinator's request.** This is an addendum to `SEED_REGISTRY.md` and `SEED_REGISTRY_R4.md`. As the registry's rule requires (section 4.5 item 5), it uses new files and records the hashes of the earlier ones; none of them was edited. Revision 5 does four things for P10-I-S2 (ADR-0025):
> 1. It allocates the new Part T role "rehearsal training draw from the accepted pools (teacher A then teacher B, one generator)" under the lead's ruling 1.
> 2. It records what Part Q actually used.
> 3. It checks every seed Part T's config and code make against the registry. This finds one binding problem, the test-mode initialisation, and three advisory points.
> 4. It adds a checker, `seed_registry_check_r5.py`, which reproduces revision 4 and treats P10-I-S2 as a fourth executed study with own files.
>
> **Checker result on origin/main: RESULT: FAIL.** The only cause is Part T's test-mode initialisation, which runs out of P10-I-S2's sub-row onto P10-I-S3's registered initialisation seeds (section 3.1). Every check carried over from revision 4 passes: 67 allocations, 0 problems, 194 known own-files cases. With the fix this revision allocates, applied to a scratch copy of the config, the result is **RESULT: PASS** (section 8).
>
> **Status.** This is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. Part T has not run. Nothing here changes any seed, record, label or outcome of P1 to P10-I.

## 0. Repository state, inputs and hashes

- The worktree checkout `arborlm-consolidation-experiment-2b31c1` is at `25d63ce`, an ancestor of origin/main, 150 files behind. I made no git write. Read-only snapshots were exported with `git archive` into `experiments/_scratch/seed_registry_r5/`:
  - `tree_main` = **origin/main `f9f5350533b2c0d9b996c5fb0ef6e7283bb3ccfb`** (P10-I-S2 Part Q merged; revision 4; the parameter changelog);
  - `tree_impl` = **`59342e60c939a9f18f7d06421f85fe25b610415d`**, the head of the local branch `claude/p10-i-s2-impl` in the worktree `agent-acd0bce1f7811562f`, four commits ahead of `origin/claude/p10-i-s2-impl` (`8594a65`, already merged into main). That worktree's two uncommitted files (`studies/p10is2/labels.py` and a test) do not touch seeds and were not used.
- The checker was run with `--root` pointing at each snapshot. The two new files were written into this worktree's `docs/reviews/p10-i-direction-2026-11-17/`.
- `docs/decisions/ADR-0030-…` (untracked, not approved) was not used, and nothing is allocated for it.

| File | State | SHA-256 |
|---|---|---|
| `SEED_REGISTRY.md` | unchanged (identical on origin/main) | `7211706f1172e55aad445053b1d28294a24de5b6eb766f1d3cbb779ecb154f39` |
| `SEED_REGISTRY_R4.md` | unchanged (identical on origin/main) | `d1d22cc45d12b0bfa2856aed00ce7e2d1cbf1eef14c366b8abcea4b7237cab7f` |
| `seed_registry_check.py` (revision 2) | unchanged | `b078100689211a437d59d898e5a7fb04ee03fbcc2a388288e9f5e83dbe759289` |
| `seed_registry_check_r3.py` (revision 3; cited by both P10-I-S2 configs) | unchanged | `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594` |
| `seed_registry_check_r4.py` (revision 4) | unchanged | `7bc791e0f24528020b9c3f569751f6528f30444a761b6bae514efad96acd81e8` |
| `seed_registry_check_r5.py` | **new** | `8ce47ab52abbe25b4b308ca2a1e7587f5461b13340f1faa2a0c0cff6804f4611` |
| `SEED_REGISTRY_R5.md` (this file) | new | stated in the coordinator's commit |

Inputs read:

| Input | Source | SHA-256 |
|---|---|---|
| ADR-0025 | origin/main | `2f5be0f95f232c566e3496d5e293a8a142ab50dc853e0c5a640ecea627f894b2` |
| ADR-0025 Part T rulings addendum | `59342e6`; equal to the hash `configs/p10is2_partt.toml` cites on the branch | `13b472dc0c0e9fac7100221f4f5bde7610b59aae3df1ce201a158652152ad14e` |
| `configs/p10is2_partt.toml` | origin/main; the `[seeds]` table is identical at `59342e6` | `a9cdefaaeb4f8f80c680f6503d7896e49f5aa89d47fdba1530cfa1286e29be72` |
| `configs/p10is2_partq.toml` | origin/main = `59342e6` | `5d79898df6cd4e22918b7a104fcc73f802b625a7070d8aa5cdf8588c90848f46` |

`studies/p10is2/common/core.py` is identical on origin/main and at `59342e6`.

## 1. The new Part T role: rehearsal training draw (ruling 1)

| Role | Count | Value | Row |
|---|---|---|---|
| Part T rehearsal training draw from the accepted pools: teacher A then teacher B, one generator, 8,000 per capability | **1** | **252002** | Part T rehearsal sets 252001–252899 (revision 3) |

Why this value, and why no new value is needed:

- **252001 is never a seed.** It is the base of the Part T rehearsal set. The code seeds only base + 1, 2, 4, 10 and 13 (`offsets = [1, 2, 4, 10, 13]`; `studies/p10is2/common/core.py:136`, `partt_replicate_values`), so 252001 cannot be shared with any role.
- **252002 is the rehearsal set's "training draw" slot (base + 1).** It is the slot the registered replicates (250002, 250102, 250202) and the calibration draws (251002 … 251302) use for their training draws, the latter "A then B, one generator" (`partt_real.calibration_draws`). Revision 3 already holds it inside 252001–252899. In rehearsal mode, `partt_listed_seeds("rehearsal")` lists it today, but no code draws with it. Under DISJOINT DRAWS, `load_part_q` hands the rehearsal Part Q's registered replicate indices (`studies/p10is2/partt_real.py:46-48` at `59342e6`), which is the audit's B2 that ruling 1 removes. No other role reads offset + 1 in Part T: it is read only by `gen(1, …)` for overlapping and calibration draws (`partt_real.py:53, 81`).
- So the role takes the one value its layout reserves for it, with no sharing. A **distinct** value from 252001 and from 330251 + j is satisfied: 252002 equals neither, and initialisation seeds are a different row. Count 1 is enough because both rehearsals (measuring and counting) train replicate 0 only (`CellSpec(…, 0)`, `partt_real.py:186, 214`). They use the same draw, as they already share 330251 + j (ADR-0025 section 6).
- **For the implementer:** in rehearsal mode the training material must come from `SeedPlanT(cfg, "rehearsal", 0).gen(1, "rehearsal training draw")`, as `randperm(len(pool[c]))[:8000]` for A then B with **one** generator. It must not come from Part Q's recorded registered indices. The registered replicates' 250002, 250102 and 250202 are not touched.
- **Disclosure (ruling 2's reasoning applies; it is the lead's to state):** A's accepted pool holds 24,187 items and the three registered draws take 24,000, so the rehearsal draw's *items* necessarily overlap the registered draws' items. The *seed* is distinct.

## 2. Part T: every seed against the registry (code at `59342e6` and origin/main)

All values below are reconstructed from `configs/p10is2_partt.toml` by the code's formula, and the checker compares them with `common.core.partt_replicate_values` and `partt_listed_seeds` (equal on all 10 draws).

| Mode | Data (base + 1, 2, 4, 10, 13) | Initialisation (base + j, j = 0..7) | Registry |
|---|---|---|---|
| Registered r = 0..2 | 250002…250214 (bases 250001, 250101, 250201) | 330201–330208, 330211–330218, 330221–330228 | covered (revision 3) |
| Registered analysis | 250915 bootstrap; **250918** route pieces | — | 250915 named by revision 2. **250918 was not named until now**; it lies in row 250901–250999 and is named here |
| Calibration i = 0, 1 | bases 251001, 251101 | 330231–330238, 330241–330248 | covered (revision 3) |
| Repeated calibration i = 2, 3 | **bases 251201, 251301** | **330261–330268, 330271–330278** | inside the rows; **named here for the first time**. ADR-0025 section 6 asked for this "before any freeze"; revision 4 did not do it |
| Rehearsal | base 252001: **252002** (the new role), 252003, 252005, 252011, 252014 | 330251–330258 | covered |
| Test i = 0, 1 | 934002…934114 | **330298–330305 and 330299–330306** | **NOT covered: binding problem, section 3.1** |

Also used by Part T, from Part Q's stored records only (no new draw): 250913, the timing items.

## 3. Findings on Part T's seeds

### 3.1 Binding: the test-mode initialisation leaves P10-I-S2's sub-row

`partt_replicate_values` in test mode takes `init0 = init_test[index % 2]` and adds the eight roles, `init0 + j` (`studies/p10is2/common/core.py:133, 137`). With `init_test = [330298, 330299]` this gives **330298–330305** (test draw 0) and **330299–330306** (test draw 1).

- **330300–330306 lie outside P10-I-S2's sub-row** 330201–330299.
- **330301, 330302 and 330303 are P10-I-S3's registered initialisation seeds** (ADR-0026, executed). Their R2 images, s + 1000·k, are P10-I-S3's.
- The two test draws also share 330299–330305 under different roles.
- ADR-0025 section 6 lists test mode as two seeds, "330298, 330299". The code reads them as two **bases** of eight roles each.
- Only test mode is affected, which means unit tests and synthetic worlds: no registered, calibration or rehearsal value. The unit tests at `59342e6` run Part T tasks in test mode (`tests/test_p10is2_partt_tasks.py:155-160`), so these values have been used there.
- The study's own G9 did not catch this. `common/gates.named_values` lists `init_test` as the two bases only, not their + j values (`studies/p10is2/common/gates.py:85`).

**Allocation by revision 5:** Part T test-mode initialisation is **330281 + 8·i + j** for test draw i = 0, 1 and role j = 0..7, which is **330281–330296**. It sits in the sub-row's spare (revision 3: "330261–330297 takes four more draws of 8", now holding the repeated calibration 330261–330278). In config terms this is `init_test = [330281, 330289]`, with the code unchanged. 330298 and 330299 stay named as test mode and are unused by Part T after the change. With exactly this change applied to a scratch copy of the config, the checker prints `RESULT: PASS` (section 8). **The config change is the implementer's.** It needs no ADR threshold or label change. The ADR text "Test mode: 330298, 330299" then disagrees with the config, and the lead may note that (**PENDING LEAD REVIEW**).

### 3.2 Advisory (covered by the registry's ranges, but against its rule that a seed serves one purpose)

1. **Route-accuracy pieces outside registered mode reuse the router seed.**
   - `SeedPlanT.route_pieces_gen` uses 250918 in registered mode, but in every other mode it uses `values["data"]["router"]`, i.e. base + 13 (`studies/p10is2/engine.py:80`).
   - `scoring.py:239-240` seeds "router sampling" with the same base + 13. In calibration, rehearsal and test, two generators therefore share one seed, and the "order" permutation equals the "picked" one.
   - Registered mode is not affected.
   - Revision 5 names distinct values, available if the implementer separates them: **base + 18** of each non-registered set, i.e. **251019, 251119, 251219, 251319** (calibration draws 0–3), **252019** (rehearsal), and 934019 / 934119 for test. Each mirrors 250918 and lies inside its own row.
2. **Gate G5 seeds its probe queries with the literal 934900** (`torch.Generator().manual_seed(934900)`, `studies/p10is2/partt_gates.py:132` at `59342e6`, `:105` on main).
   - This bypasses `seeded_generator`, so the seed is neither listed nor recorded.
   - It runs in every mode, including the registered gates stage, although 934900 is a test-range value.
   - Revision 5 names **250919** (row 250901–250999) as the G5 probe seed, to be listed in registered mode. The test value stays in tests.
3. **Part Q and Part T share test values.** Part Q's test mode uses 934001–934018 (`partq_seeds("test")`), and Part T's test draw 0 uses 934002, 934003, 934005, 934011 and 934014. Both are test-only and within one study, so there is no registry violation. The lead may prefer Part T's test bases at 934201/934301 (**PENDING LEAD REVIEW**).

No other generator in `studies/p10is2` (Part T modules, `common/`, `engine.py`, `scoring.py`) is seeded outside `seeded_generator`. The search was for `manual_seed`, `Generator(`, `Random(`, `random.seed`, `default_rng`, `np.random` and `torch.rand*` (excluding `partq/`). The P10-S2 `build_world(bundle, "test", 0, run)` call draws nothing, because it is called with zero replicates (`studies/p10s2/worldio.py:183`).

## 4. Corrections of record: P10-I-S2 Part Q as executed

Part Q had three registered attempts: attempt 1 refused at `inputs` after 13 s; attempt 2 stopped at `outputs`; attempt 3 reused attempt 2's stages 1–6 by hash and completed. Sources: `results/p10is2-partq-run-20261119/audit/STOP_P10IS2_PARTQ_ATTEMPT2.md` ("Seeds consumed"), `results/p10is2-partq-run-20261119/OUTCOME.md`, `results/p10is2-partq-run-20261119-attempt3/OUTCOME.md` and `audit/RECOMPUTE_P10IS2_PARTQ.md` (DISJOINT draws with 250916/250917 reproduced; digest indices with 250908; regeneration subsample with 250914).

| Revision 3 / 4 holds | Part Q used | Note |
|---|---|---|
| 250901–250914 "partition side" (no per-value roles) | **250901–250914, all consumed**. 250907 before the freeze (ledger); 250901–250905, 250908–250910 and 250914 in stages 1–6 (attempt 2, reused by attempt 3); 250906 and 250911–250913 in step 8 (attempts 2 and 3, same seeds) | Roles as in the config. 250908's role is "teacher tokenizer sentences and digest batches", the amended role ADR-0025 section 6 asks the registry to record |
| 250915 bootstrap | listed in Part Q's registered set; **no Part Q code reads it** (search of `studies/p10is2/partq/`) | Part T's `analysis_bootstrap` |
| 250916, 250917 disjoint permutations | **used: DISJOINT DRAWS**, 3 × 8,000 per teacher (recomputation: identical, pairwise disjoint) | as revision 2 |
| — (not named) | **250918 listed** in Part Q's registered set (`partq_seeds`, 18 values); **not read by Part Q** | Part T's registered route pieces (`engine.py:80`). Named now |
| 252901–252914 Part Q rehearsal | **used by every Part Q rehearsal** (five measuring attempts and the counting rehearsals) | as revision 2 |
| 934001–934999 test | Part Q test mode 934001–934018 | inside the test range |
| initialisation 330201–330299 | none (Part Q trains nothing) | — |

The Part Q freeze record's G9 (`studies/p10is2/freeze/partq_freeze_record.json`) ran the revision-3 checker as a copy that excluded P10-I-S2's files. It reported 34 problem lines, all P10-I-R's own files, none naming P10-I-S2, and the gate passed. Revision 5's checker classifies P10-I-S2's 70 own-file hits as the known case. All of Part Q's values lie in its revision-3 rows, so no row changes.

## 5. What revision 5 adds to and leaves unchanged in revision 4

- **Added:**
  - P10-I-S2 as a built-in own-files owner (`configs/p10is2_*`, `studies/p10is2/*`, `tests/test_p10is2_*`);
  - P10-I-S2's named data values (Part Q as used; Part T's replicate, calibration (including draws 2 and 3), rehearsal and analysis values; the new role 252002; recommended 250919 and the base + 18 values);
  - P10-I-S2's named initialisation values (repeated calibration 330261–330278; Part T test mode 330281–330296);
  - section [8] extended to Part Q, with an import cross-check of `partq_seeds` in three modes;
  - section [10], Part T conformance, which is binding.
- **Unchanged:** every ALLOC row (67), every other named value, the declared re-uses, the rules R1–R3, sections [1]–[7] and [9], `--own`, `--root` and `--selftest`.
- **Next free values (registry section 4.5, as amended by revision 4):** in P10-I-S2's initialisation sub-row, 330259, 330260, 330269, 330270, 330279, 330280 and 330297 remain.

## 6. Collisions found and resolution

| Finding | Kind | Resolution |
|---|---|---|
| Part T test-mode initialisation 330300–330306, three of them equal to P10-I-S3's registered 330301–330303 | binding (section [10]) | allocate 330281–330296 (`init_test = [330281, 330289]`); the implementer changes the config; the checker passes on the scratch copy with that change |
| Route pieces and router sampling share base + 13 outside registered mode | advisory | distinct values named (base + 18) |
| G5 probe seeded with 934900 outside the listed-seed function, also in the registered gates stage | advisory | 250919 named |
| Part Q and Part T test values in common (934002, 934003, 934005, 934011, 934014) | advisory, test-only | none required |
| Revision 4's allocations against the inventory | none | 0 problems; 194 own-files cases (S2 70, S3 52, S5 38, R 34) |

## 7. Commands, environment, attempts (failed attempts kept)

Command (one process per run):

```sh
uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r5.py --root <snapshot>
```

Environment: macOS 27.2.1 arm64, uv 0.12.15, Python 3.12.14, torch 2.8.0 from this worktree's locked environment (`uv.lock` is unchanged on origin/main). One NumPy warning goes to stderr and is not part of the output. Wall time 2.27 s (`/usr/bin/time -p`).

All outputs are in `experiments/_scratch/seed_registry_r5/`.

1. **Attempt 1: FAIL, partly my error** (`attempt1_output.txt`). My Part Q block in section [8] reassigned the variable `st`, so revision 4's P10-I-R test-set check ran against P10-I-S2's rows and reported `P10-I-R test_sets outside its test row`. Fixed by renaming the variable. The Part T findings were the same as in attempt 2.
2. **Attempt 2, against origin/main `f9f5350`: RESULT: FAIL**, exit 1, verbatim in section 9 (`attempt2_output.txt`). A timing re-run gave byte-identical output (`final_timing_run.txt`). Counts: 67 allocations; 0 problems in [1]; 194 own-files cases; 197 named initialisation and 783 named data values; 0 missing in [6]; 0 failures in [7], [8] and [9]; **4 failure lines in [10]**, two per test draw, for the one cause in section 3.1.
3. **Same checker against `59342e6` (the Part T branch head): RESULT: FAIL**, the same 4 lines and nothing else (`attempt2_impl_59342e6.txt`).
4. **Same checker against a scratch copy of origin/main with only `init_test = [330281, 330289]` changed: RESULT: PASS**, exit 0 (`attempt2_fix_scratch.txt`; 198 own-files cases, because the two new literals are in P10-I-S2's own config).
5. **Self-test (`--selftest`, on the scratch copy): FAIL, as required.** All three planted faults were reported (`selftest_output.txt`).

## 8. Note on using this checker in a gate

Part T's G9 cites `seed_registry_check_r3.py` today. If it moves to revision 5 it should cite `seed_registry_check_r5.py` by SHA-256 and run it unedited. P10-I-S2 is built in as an owner, so no `--own` argument is needed. It must print `RESULT: PASS`, which it will not do until section 3.1 is fixed. A later study adds its own files with `--own "STUDY=GLOBS"`.

## 9. Checker output (attempt 2, origin/main `f9f5350`, verbatim)

```text
SEED REGISTRY CHECK (P10-I) revision 5 — arbor-auditor, standard library only
root: /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/seed_registry_r5/tree_main
rules: R1 identity; R2 s+1000k, k=1..10, on initialization seeds and on every inventory literal < 100000; R3 s*1000+i, i in [0,999], on every value >= 1000; in-set offsets enumerated per study
own files (ADR-0029 ruling 6): P10-I-S3 ADR-0026 = configs/p10i_s3_*, studies/p10i_s3/*, tests/test_p10is3_*; P10-I-S5 ADR-0028 = configs/p10is5_*, studies/p10is5/*, tests/test_p10is5_*; P10-I-R ADR-0029 = configs/p10ir_*, studies/p10ir/*, tests/test_p10ir_*; P10-I-S2 ADR-0025 = configs/p10is2_*, studies/p10is2/*, tests/test_p10is2_*
inventory: 71 entries, 51291 identity values (with overlaps); entries owned by a P10-I study: 9
named values checked: 197 initialization, 783 data (revision 5)

[1] binding: P10-I allocations (R1-R3 expanded) against the inventory (R1-R3 expanded) and against each other
    allocations: 67; problems: 0; known own-files cases (not failures): 194; revision-3-equivalent count (own files not separated): 194
    known own-files case: P10-I-R ADR-0029: 34 hits of its own allocation against its own files
    known own-files case: P10-I-S2 ADR-0025: 70 hits of its own allocation against its own files
    known own-files case: P10-I-S3 ADR-0026: 52 hits of its own allocation against its own files
    known own-files case: P10-I-S5 ADR-0028: 38 hits of its own allocation against its own files

[2] the drafts' own proposals under the same rules, against the inventory only
    (listed: collisions with a seed the code itself uses or derives; 'conservative' counts hits that exist only through
     the catch-all entries or the +1000k applied to small literals that are not initialization seeds; 'own-files' counts
     hits on an executed study's own files, which [1] classifies against the allocation)
    ADR-0023 draft 1 init 3001–3002: 14 actual collisions, 85 conservative-only, 24 own-files
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
    ADR-0025 draft 1 data 250001–259999: 0 actual collisions, 0 conservative-only, 32 own-files
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
    ADR-0025 draft 3 data (disjoint draws) 250916–250917: 0 actual collisions, 0 conservative-only, 2 own-files
    ADR-0025 draft 3 data (Part Q rehearsal) 252901–252914: 0 actual collisions, 0 conservative-only, 2 own-files
    ADR-0027 draft 3 Route A data (streams d=6..9) 270501–270803: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0027 draft 3 init 330401–330405: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0028 draft 3 data (registered) 280001–280303: 0 actual collisions, 0 conservative-only, 6 own-files
    ADR-0031 section 14 data 320001–329999: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0031 section 14 init 330701–330799: 0 actual collisions, 0 conservative-only, 0 own-files
    ADR-0031 section 14 test 952001–952999: 0 actual collisions, 0 conservative-only, 0 own-files
    between drafts: 0

[3] informational (not binding): worst case, +1000k applied to EVERY value of every role, both sides
    hits: 13823; 6595 inside one study's own block or own files (not listed); the rest grouped by study pair (roles merged):
          42  P10-I-R ADR-0029  <->  P10-I-S2 ADR-0025 own files
          32  P10-I-R ADR-0029  <->  P10-I-S3 ADR-0026 own files
          10  P10-I-R ADR-0029  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-R ADR-0029  <->  P10-I-S6 ADR-0031
          16  P10-I-R ADR-0029  <->  P10I / config literal
          28  P10-I-R ADR-0029  <->  P10IS2 / config literal
         682  P10-I-R ADR-0029  <->  P10IS5 / config literal
           8  P10-I-R ADR-0029  <->  Review diagnostics / unknown role
         280  P10-I-S0 ADR-0023  <->  P10-I-R ADR-0029
          25  P10-I-S0 ADR-0023  <->  P10-I-R ADR-0029 own files
          10  P10-I-S0 ADR-0023  <->  P10-I-S1 ADR-0024
           9  P10-I-S0 ADR-0023  <->  P10-I-S2 ADR-0025
          54  P10-I-S0 ADR-0023  <->  P10-I-S2 ADR-0025 own files
           8  P10-I-S0 ADR-0023  <->  P10-I-S3 ADR-0026
          32  P10-I-S0 ADR-0023  <->  P10-I-S3 ADR-0026 own files
           7  P10-I-S0 ADR-0023  <->  P10-I-S4 ADR-0027
           6  P10-I-S0 ADR-0023  <->  P10-I-S5 ADR-0028
           6  P10-I-S0 ADR-0023  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S0 ADR-0023  <->  P10-I-S6 ADR-0031
          16  P10-I-S0 ADR-0023  <->  P10I / config literal
         244  P10-I-S0 ADR-0023  <->  P10IR / config literal
          36  P10-I-S0 ADR-0023  <->  P10IS2 / config literal
          12  P10-I-S0 ADR-0023  <->  P10IS5 / config literal
           2  P10-I-S0 ADR-0023  <->  Review diagnostics / unknown role
           6  P10-I-S1 ADR-0024  <->  P10-I-R ADR-0029
          30  P10-I-S1 ADR-0024  <->  P10-I-R ADR-0029 own files
         422  P10-I-S1 ADR-0024  <->  P10-I-S2 ADR-0025
          60  P10-I-S1 ADR-0024  <->  P10-I-S2 ADR-0025 own files
           9  P10-I-S1 ADR-0024  <->  P10-I-S3 ADR-0026
          36  P10-I-S1 ADR-0024  <->  P10-I-S3 ADR-0026 own files
           8  P10-I-S1 ADR-0024  <->  P10-I-S4 ADR-0027
           7  P10-I-S1 ADR-0024  <->  P10-I-S5 ADR-0028
           7  P10-I-S1 ADR-0024  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S1 ADR-0024  <->  P10-I-S6 ADR-0031
          18  P10-I-S1 ADR-0024  <->  P10I / config literal
          18  P10-I-S1 ADR-0024  <->  P10IR / config literal
         804  P10-I-S1 ADR-0024  <->  P10IS2 / config literal
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
          60  P10-I-S3 ADR-0026  <->  P10-I-S2 ADR-0025 own files
         250  P10-I-S3 ADR-0026  <->  P10-I-S4 ADR-0027
           9  P10-I-S3 ADR-0026  <->  P10-I-S5 ADR-0028
           9  P10-I-S3 ADR-0026  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S3 ADR-0026  <->  P10-I-S6 ADR-0031
          24  P10-I-S3 ADR-0026  <->  P10IR / config literal
          84  P10-I-S3 ADR-0026  <->  P10IS2 / config literal
          18  P10-I-S3 ADR-0026  <->  P10IS5 / config literal
           5  P10-I-S3 ADR-0026  <->  Review diagnostics / unknown role
           9  P10-I-S4 ADR-0027  <->  P10-I-R ADR-0029
          45  P10-I-S4 ADR-0027  <->  P10-I-R ADR-0029 own files
          54  P10-I-S4 ADR-0027  <->  P10-I-S2 ADR-0025 own files
          40  P10-I-S4 ADR-0027  <->  P10-I-S3 ADR-0026 own files
         250  P10-I-S4 ADR-0027  <->  P10-I-S5 ADR-0028
          10  P10-I-S4 ADR-0027  <->  P10-I-S5 ADR-0028 own files
          55  P10-I-S4 ADR-0027  <->  P10-I-S6 ADR-0031
         658  P10-I-S4 ADR-0027  <->  P10I / config literal
          27  P10-I-S4 ADR-0027  <->  P10IR / config literal
          36  P10-I-S4 ADR-0027  <->  P10IS2 / config literal
         214  P10-I-S4 ADR-0027  <->  P10IS5 / config literal
           6  P10-I-S4 ADR-0027  <->  Review diagnostics / unknown role
         251  P10-I-S5 ADR-0028  <->  P10-I-R ADR-0029
          50  P10-I-S5 ADR-0028  <->  P10-I-R ADR-0029 own files
          48  P10-I-S5 ADR-0028  <->  P10-I-S2 ADR-0025 own files
          36  P10-I-S5 ADR-0028  <->  P10-I-S3 ADR-0026 own files
          55  P10-I-S5 ADR-0028  <->  P10-I-S6 ADR-0031
          18  P10-I-S5 ADR-0028  <->  P10I / config literal
         103  P10-I-S5 ADR-0028  <->  P10IR / config literal
          32  P10-I-S5 ADR-0028  <->  P10IS2 / config literal
           7  P10-I-S5 ADR-0028  <->  Review diagnostics / unknown role
          55  P10-I-S6 ADR-0031  <->  P10-I spare
         165  P10-I-S6 ADR-0031  <->  P10I / config literal
         165  P10-I-S6 ADR-0031  <->  P10IR / config literal
         495  P10-I-S6 ADR-0031  <->  P10IS2 / config literal

[4] informational (not binding): R3 also applied to values < 1000, both sides
    hits: 4
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..301999 hits inventory: All code and tests / literal scan [x1000+i] (71 literals in src/arborlm, studies, tests (files no P10-I study owns))
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..302999 hits inventory: P9 / config literal [x1000+i] (configs/p9_diagnostics.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2 / config literal [x1000+i] (configs/p2_optimization_followup.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2/P3 / data (order) [x1000+i] (configs/p2_optimization_followup.toml:7)

[5] informational: six-digit literals inside a P10-I allocation, in configs/*.toml, src, studies, tests (*.py),
    docs/decisions/*.md (ADR-0023..0031 excluded) and docs/reviews/**/*.py (P10-I review folders excluded); sizes are not seeds
    hits: 1382 occurrences; in the allocation's own study's files: 815 (P10-I-R ADR-0029 169, P10-I-S2 ADR-0025 300, P10-I-S3 ADR-0026 154, P10-I-S5 ADR-0028 192); elsewhere: 567 occurrences of 183 distinct values
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
       … 103 more distinct values

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

[8] executed P10-I studies (revisions 4 and 5): values used, from frozen configs and seed plans, against the record and their rows
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
     P10-I-S2 ADR-0025 Part Q: listed registered 250901–250918 (18 values); consumed 250901–250914, 250916–250917 (16 values); listed and not read by Part Q's code: [250915, 250918] (250915 Part T's analysis bootstrap, 250918 Part T's route pieces); rehearsal 252901–252914 (14 values); test 934001–934018 (18 values)
     P10-I-S2 ADR-0025 Part Q: registered and rehearsal values in the record and in the study's data rows; test values in the test row: yes
     import P10-I-S2 common.core.partq_seeds(registered): 18 values; equal to the reconstruction: True
     import P10-I-S2 common.core.partq_seeds(rehearsal): 14 values; equal to the reconstruction: True
     import P10-I-S2 common.core.partq_seeds(test): 18 values; equal to the reconstruction: True
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
     P10-I-S6 ADR-0031: informational (W1, not binding): S6 named data values d with d + 1000k equal to a named P10-I initialisation value: 116; e.g. 320001+10000=330001 (P10-I-S0 ADR-0023), 320002+10000=330002 (P10-I-S0 ADR-0023), 320101+10000=330101 (P10-I-S1 ADR-0024), 320102+10000=330102 (P10-I-S1 ADR-0024)

[10] P10-I-S2 Part T (configs/p10is2_partt.toml; not executed): every value the config makes lies in the row of its role (binding)
     calibration draw 0: data [251002, 251003, 251005, 251011, 251014]; init 330231..330238; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     calibration draw 1: data [251102, 251103, 251105, 251111, 251114]; init 330241..330248; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     calibration draw 2: data [251202, 251203, 251205, 251211, 251214]; init 330261..330268; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     calibration draw 3: data [251302, 251303, 251305, 251311, 251314]; init 330271..330278; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     registered draw 0: data [250002, 250003, 250005, 250011, 250014]; init 330201..330208; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     registered draw 1: data [250102, 250103, 250105, 250111, 250114]; init 330211..330218; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     registered draw 2: data [250202, 250203, 250205, 250211, 250214]; init 330221..330228; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     rehearsal draw 0: data [252002, 252003, 252005, 252011, 252014]; init 330251..330258; data outside its row: []; init outside the sub-row 330201-330299: []; not in the revision-5 record: data [], init []
     test draw 0: data [934002, 934003, 934005, 934011, 934014]; init 330298..330305; data outside its row: []; init outside the sub-row 330201-330299: [330300, 330301, 330302, 330303, 330304, 330305]; not in the revision-5 record: data [], init [330300, 330301, 330302, 330303, 330304, 330305]
     test draw 1: data [934102, 934103, 934105, 934111, 934114]; init 330299..330306; data outside its row: []; init outside the sub-row 330201-330299: [330300, 330301, 330302, 330303, 330304, 330305, 330306]; not in the revision-5 record: data [], init [330300, 330301, 330302, 330303, 330304, 330305, 330306]
     registered analysis bootstrap and route pieces [250915, 250918]: outside the data rows: []
     rehearsal training draw (ruling 1; slot base + 1 of the rehearsal set): config gives 252002; the registry names 252002: equal
     informational: Part Q test-mode values and Part T test-mode data values in common (both test-only, same study): [934002, 934003, 934005, 934011, 934014]
     informational: outside registered mode the route-accuracy pieces are drawn with the router seed (base + 13), the seed 'router sampling' also uses (studies/p10is2/engine.py:80)
     informational: gate G5 seeds its probe queries with the test-range literal 934900, outside the listed-seed function, in every mode including the registered gates stage (studies/p10is2/partt_gates.py:105)
     import P10-I-S2 common.core.partt_replicate_values: 10 draws; equal to the reconstruction: True
     import P10-I-S2 common.core.partt_listed_seeds (registered, calibration, rehearsal): equal to the reconstruction: True
     FAIL: P10-I-S2 ADR-0025 Part T test draw 0: initialisation values outside P10-I-S2's sub-row: [330300, 330301, 330302, 330303, 330304, 330305]; equal to other studies' named initialisation values [330301, 330302, 330303]
     FAIL: P10-I-S2 ADR-0025 Part T test draw 0: values not in the revision-5 record: data [], init [330300, 330301, 330302, 330303, 330304, 330305]
     FAIL: P10-I-S2 ADR-0025 Part T test draw 1: initialisation values outside P10-I-S2's sub-row: [330300, 330301, 330302, 330303, 330304, 330305, 330306]; equal to other studies' named initialisation values [330301, 330302, 330303]
     FAIL: P10-I-S2 ADR-0025 Part T test draw 1: values not in the revision-5 record: data [], init [330300, 330301, 330302, 330303, 330304, 330305, 330306]

RESULT: FAIL
```

## 10. Open points

1. **PENDING LEAD REVIEW:** the Part T test-mode change (section 3.1). This is a config change by the implementer before Part T's freeze; ADR-0025's "Test mode: 330298, 330299" wording then needs a note.
2. **PENDING LEAD REVIEW:** whether to separate the route-pieces seed from the router seed outside registered mode, and to list G5's probe seed (section 3.2 items 1 and 2).
3. **PENDING LEAD REVIEW:** whether Part Q's outcome record needs a note that 250915 and 250918 were listed in its registered set but are read only by Part T.
4. Revision 4's open points stand.

`Astra review: NOT_PERFORMED`. This is independent engineering evidence by the `arbor-auditor` subagent (Claude Opus 5.5). It is not Astra validation and not human approval.
