# P10-I seed registry: revision 6 (addendum)

> **Revision 6, 2026-11-21 (UTC). Written by the implementer under the lead's ruling 42 (`docs/decisions/ADR-0025-addendum-part-t-rulings-11.md`), not by the registry's auditor.** An addendum to `SEED_REGISTRY.md`, `SEED_REGISTRY_R4.md` and `SEED_REGISTRY_R5.md`. As the registry's rule requires (section 4.5 item 5) it uses new files; revisions 2 to 5 and their checkers are unchanged. `Astra review: NOT_PERFORMED`. This is engineering evidence, not Astra validation and not human approval.

## 1. The one change

Revision 5's checker treats P10-I-S3, P10-I-S5, P10-I-R and P10-I-S2 as owners of their own files (a hit between a study's allocation and an inventory entry built from that same study's own files is the known own-files case, listed and not failed). P10-I-S0 (ADR-0023) is on main with its own config `configs/p10is0_overload.toml`, and revision 5 does not list it. After main was merged into the P10-I-S2 branch, revision 5 therefore printed `RESULT: FAIL` with 48 problems, every one of the form `P10-I-S0 ADR-0023 / <row> hits inventory: P10IS0 / config literal (configs/p10is0_overload.toml)`.

Revision 6 adds one built-in owner and nothing else:

```
"P10-I-S0 ADR-0023": ("configs/p10is0_*", "studies/p10is0/*", "tests/test_p10is0_*")
```

**No seed value, block, row, role or check of any study is altered or added.** The checker file `seed_registry_check_r6.py` differs from `seed_registry_check_r5.py` in three places only (`diff` run on this tree): a revision-6 note ahead of the revision-5 docstring text, the usage line naming r6, and the one `OWN_FILES` entry above.

## 2. Files and hashes (SHA-256)

| File | SHA-256 |
|---|---|
| `seed_registry_check_r5.py` (unchanged) | `8ce47ab52abbe25b4b308ca2a1e7587f5461b13340f1faa2a0c0cff6804f4611` |
| `SEED_REGISTRY_R5.md` (unchanged) | `19199e46d9f4e51d5650b9cfd9f3e1dd11730d45ae9fdada776a111e741ea865` |
| `seed_registry_check_r6.py` (new) | `eb757082dac6e0e34a28c4d2ac87e0b96cd0e1f6af68505dc434792f475280a4` |

## 3. Measured results (this tree, the P10-I-S2 branch after the merge of main)

- `seed_registry_check_r5.py --root .`: `RESULT: FAIL`, 48 problems, all P10-I-S0's own allocation in its own config (before this revision).
- `seed_registry_check_r6.py --root .`: `RESULT: PASS`, 67 allocations, 0 problems, 248 known own-files cases (P10-I-R 34, P10-I-S0 48, P10-I-S2 76, P10-I-S3 52, P10-I-S5 38).
- `--selftest` of r6 plants its faults (a row on P10-I-S3's joint seed 260131, a named initialisation value outside its sub-row) and prints `RESULT: FAIL` with exactly those 4 problems; r5's selftest shows the same planted faults plus the 48 S0 problems. So r6 still fails on a planted value.

## 4. Use in a gate

Part T's G9 cites `seed_registry_check_r6.py` and this addendum by SHA-256 and runs the checker unedited; it must print `RESULT: PASS`. No `--own` argument is needed for P10-I-S0, P10-I-S2, P10-I-S3, P10-I-S5 or P10-I-R. A later study adds its own files with `--own "STUDY=GLOBS"` as before.
