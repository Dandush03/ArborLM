# P10-I seed registry: revision 7 (addendum)

> **Revision 7, 2026-11-21 (UTC). Written by the implementer under the lead's ruling 45 (`docs/decisions/ADR-0025-addendum-part-t-rulings-13.md`), not by the registry's auditor.** An addendum to `SEED_REGISTRY.md` and revisions 4 to 6. As the registry's rule requires (section 4.5 item 5) it uses new files; revisions 2 to 6 and their checkers are unchanged. `Astra review: NOT_PERFORMED`. This is engineering evidence, not Astra validation and not human approval.

## 1. The one change

Revision 6's checker treats P10-I-S0, S2, S3, S5 and R as owners of their own files (a hit between a study's allocation and an inventory entry built from that same study's own files is the known own-files case, listed and not failed). P10-I-S1 (ADR-0024) and P10-I-S6 (ADR-0031) are on main with their own configs (`configs/p10is1_capacity.toml`, `configs/p10i_s6_flat_lead_persistence.toml`), and revision 6 does not list them. After main was merged into the P10-I-S2 branch, revision 6 printed `RESULT: FAIL`, `problems: 66`.

**The 66, all traced.** The checker prints at most 60 failure lines (`fails[:60]`, then "... 6 more"), which is why 60 lines were printed against 66 counted. Running revision 6 with `--own "P10-I-S1 ADR-0024=configs/p10is1_*,studies/p10is1/*,tests/test_p10is1_*" --own "P10-I-S6 ADR-0031=configs/p10i_s6_*,studies/p10i_s6/*,tests/test_p10i_s6_*"` gives `problems: 0`, `RESULT: PASS`, with 24 own-files hits for P10-I-S1 (against `configs/p10is1_capacity.toml`) and 42 for P10-I-S6 (against `configs/p10i_s6_flat_lead_persistence.toml`): 24 + 42 = 66. So every one is a study's own allocation hitting its own file, including the 6 that were not printed (all P10-I-S6).

Revision 7 adds these two owners and nothing else:

```
"P10-I-S1 ADR-0024": ("configs/p10is1_*", "studies/p10is1/*", "tests/test_p10is1_*")
"P10-I-S6 ADR-0031": ("configs/p10i_s6_*", "studies/p10i_s6/*", "tests/test_p10i_s6_*")
```

**No seed value, block, row, role or check of any study is altered or added.** `seed_registry_check_r7.py` differs from `seed_registry_check_r6.py` in three places only (`diff` on this tree): a revision-7 note ahead of the revision-6 docstring text, the usage line naming r7, and the two `OWN_FILES` entries above.

## 2. Files and hashes (SHA-256)

| File | SHA-256 |
|---|---|
| `seed_registry_check_r6.py` (unchanged) | `eb757082dac6e0e34a28c4d2ac87e0b96cd0e1f6af68505dc434792f475280a4` |
| `SEED_REGISTRY_R6.md` (unchanged) | `4f2afd94928c70229db5956a5781e53d8f25265a64318c9f56f608d5188a0efb` |
| `seed_registry_check_r7.py` (new) | `1f3b2de22ef3ff9bd01d81d67d7fcccac27710ed3394b62bec9c0688bc8b8f8f` |

## 3. Measured results (this tree, the P10-I-S2 branch after the merge of main of 2026-11-21)

- `seed_registry_check_r6.py --root .`: `RESULT: FAIL`, `problems: 66`, 248 own-files cases.
- `seed_registry_check_r7.py --root .`: `RESULT: PASS`, 67 allocations, 0 problems, 314 own-files cases (R 34, S0 48, S1 24, S2 76, S3 52, S5 38, S6 42).
- r7 still FAILS on planted faults, each in its own copy of the tree: (a) a foreign value (P10-I-S3's joint seed 260131) as `planted_seed` in P10-I-S1's owned config: FAIL, 2 problems ("hits inventory ... [entry owned by P10-I-S1 ADR-0024]"); (b) an owned value (P10-I-S1's registered draw 240001) as `random.Random(240001)` in a file no study owns: FAIL, 2 problems; (c) a Part T value outside its rows (`init_test` start 900001): FAIL, "initialisation values outside P10-I-S2's sub-row". r7's `--selftest` is the revision-5 selftest and still prints FAIL on its planted faults.

## 4. Use in a gate

Part T's G9 cites `seed_registry_check_r7.py` and this addendum by SHA-256 and runs the checker unedited; it must print `RESULT: PASS`. No `--own` argument is needed for P10-I-S0, S1, S2, S3, S5, S6 or R.
