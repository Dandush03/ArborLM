# P5 independent engineering audit

## Scope

This is an artifact and accounting audit of the completed P5 suite `P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be`. It did not train a model or call a model forward. Five strict checkpoint restores loaded model/optimizer state for integrity comparison only; no evaluation followed those restores.

The audit does not provide scientific approval or Astra validation. `ASTRA_NOT_PERFORMED`.

## Independent results

The arithmetic checker passed with no errors. From raw cell metrics and raw timing-block events it confirmed 117 registered quality cells, 36 timing workers, 612 scientific evaluations, nine parent-integrity evaluations, 55,296 optimizer updates, and 333 snapshots. The totals were 20,054,016 scientific evaluation targets, 294,912 parent-integrity targets, and 28,311,552 training targets. It recomputed paired contrasts, preregistered gates, reliability summaries, timing ratios and logical-work ratios; raw training-step cursors and timing schedule/input rotations matched the registered sequence.

The arithmetic output records these gates as computed: `U_flat`, `U_fixed_tree`, `U_learned_tree`, `Q_fixed_tree`, and `Q_learned_tree` are true; `R` and all three `dense_tolerance_*` clauses are false. These are recorded results, not scientific interpretation.

The artifact checker passed with no errors. It checked all 333 physical snapshots, 27 cross-parent initialization groups, nine P4/P3 parent pairs, 162 registered permutation files, 1,674 raw-to-compact quality-file comparisons, 365 raw-to-compact timing-file comparisons, five strict representative no-forward restores, and 648 raw operator traces. The timing operand checks independently matched the implementation’s stable top-9 boundary check followed by gather-8 selection, including tree branch top-3/gather-2 and the score and candidate-ID gather operands.

All 117 cells and 36 timing workers used the frozen source archive SHA-256 `6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e`; the 95-entry source-file map matched the committed freeze map. The dataset manifest hash was `481dba62b283fc7b732bcf3692f38f37c2891b9d2200f9e1fc304c0f5721e848`.

The raw `state.pt` and `source.tar` binaries were checked in the local retained quality-run directories. Compact result directories omit those binaries; their checkpoint indexes and JSON records were compared to the local raw records. This audit does not establish binary availability in GitHub or any other remote store.

## Commands and evidence

Commands used the locked pilot environment:

```text
uv run --locked --extra pilot ruff format results/p5-2026-11-13/audit/independent-arithmetic.py results/p5-2026-11-13/audit/independent-artifacts.py
uv run --locked --extra pilot ruff check results/p5-2026-11-13/audit/independent-arithmetic.py results/p5-2026-11-13/audit/independent-artifacts.py
uv run --locked --extra pilot python results/p5-2026-11-13/audit/independent-arithmetic.py
uv run --locked --extra pilot python results/p5-2026-11-13/audit/independent-artifacts.py
```

Final checker stdout, stderr, exit codes, and source snapshots are retained as `independent-arithmetic-attempt-05.*` and `independent-artifacts-attempt-04.*`. Script hashes are in `independent-arithmetic.sha256` and `independent-artifacts.sha256`. Ruff logs and every checker attempt’s stdout/stderr/exit record are also retained in this directory.

The artifact attempts record auditor-only fixes: attempt 01 looked for binaries in compact output instead of raw runs; attempt 02 exposed an incorrect top-k trace expectation; attempt 03 exposed the corresponding flat-path expectation. No model, config, raw result, or frozen source files were changed. Attempt 04 passed. Exact source snapshots/hashes for attempts 01–02 were not retained; their output and exit records are preserved, and this evidence gap is stated rather than reconstructed as if original. Exact checker snapshots/hashes are available from attempt 03 onward.

PyTorch emitted a nonfatal warning that NumPy is not installed during artifact loading. Both final checker runs exited 0; the warning did not alter their results.

## Limits

This audit verifies engineering artifacts and accounting. It makes no Astra or human scientific-validation claim and does not endorse the experiment’s scientific conclusions.
