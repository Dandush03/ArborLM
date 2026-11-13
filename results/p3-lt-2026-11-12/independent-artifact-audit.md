# Independent P3-LT artifact audit

Scope: read-only engineering and arithmetic audit of the registered suite
`experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d`.
This is not scientific validation or Astra review.

## Reproduction

From the repository root:

```sh
uv run --no-sync ruff check results/p3-lt-2026-11-12/independent_artifact_audit.py
.venv/bin/python results/p3-lt-2026-11-12/independent_artifact_audit.py
```

Ruff passed. The audit exited 0 with `issues: []`. Captured output and stderr
are in `independent_artifact_audit.stdout.json` and
`independent_artifact_audit.stderr.txt`. Stderr contains PyTorch's optional
NumPy initialization warning because NumPy is absent; the audit does not use
NumPy. During audit-script preparation, an omitted `subprocess` import caused
one tooling-only `NameError`; it was fixed before the successful run. The
initial Ruff findings were likewise fixed and the final Ruff run passed. These
were audit-tooling corrections, not experiment failures.

## Integrity and execution checks

- All 36 registered cells completed with successful terminal records.
- All 36 P2 parent state and index files match their recorded hashes and the
  compact P2 export. Parent unchanged markers are true. Each step-256 P3
  checkpoint matches its P2 parent bitwise for model, optimizer, Python and
  Torch RNG states, `requires_grad` flags, and bypass state. All 36 P2-panel
  replays match the parent NLL bitwise and are marked integrity-only.
- All 108 P3 checkpoint state hashes match checkpoint indexes and result
  records. Counters and AdamW clocks are exact at steps 256, 512, and 1024;
  step 256 is marked zero-training conversion. Controls retain frozen memory
  tensors and bypass memory throughout.
- Each cell has 768 continuation updates (global steps 257–1024), with the
  recorded cyclic order offsets and target counters. This gives 393,216
  additional and 524,288 lifetime training targets per cell; suite totals are
  14,155,776 additional and 18,874,368 lifetime targets.
- The suite contains 27,648 train events, 108 duration references, 351
  interventions, and 36 old-panel integrity replays. Every duration reference,
  intervention, and old-panel replay records 32,768 validation targets and
  zero training targets. The 36 old-panel results are explicitly excluded
  from scientific analysis.
- All cells sharing an order factor have identical order streams. P2 and P3
  order files match per cell. Both intervention permutations reproduce from
  their recorded seeds and match P2 IDs; duration records refer to those same
  permutation files.
- Source archive identity is common across all cells:
  `7be7aaccde57383961e530b64bdc6902df3f3b690af2857f68db0c5f96ad75a0`.
  Dataset manifest identity is common across cells. Train, P2 integrity panel,
  and P3 validation bytes match their pinned hashes; P2/P3 panel bytes also
  match the selected chunk ranks. The test split remains recorded as deferred,
  not acquired or inspected. Root's independent data audit additionally
  verified zero exact overlap with the prior panels and full training data.
- Recorded source history spans 18 HEAD commits; every post-freeze commit
  touched only `results/`. All 36 per-cell source diffs are empty and hash
  valid. The manifests record 35 dirty worktrees; this is retained as a
  provenance caveat, not represented as a clean-worktree run.

## Independent arithmetic and recorded gates

Recomputed paired D/P/G/S values over the 27 learned cells at each duration,
using the nine unique controls for each backbone/order pair. `G = D + S`
holds within 1e-12. Recomputed descriptive statistics, marginal ranges,
interaction RMS values, duration deltas, and gate criteria match the suite's
recorded descriptive analysis.

At step 1024, mean D is 0.0034167449, mean P is 0.0032048363, and mean G is
0.0034215122. From step 256 to 1024, mean delta D is 0.0027253499 and mean
delta P is 0.0025161647. Both D and P deltas are positive in 22/27 cells;
both endpoint D and P are positive in 24/27. Endpoint enabled mean NLL
improves from 2.5945463461 to 2.3710573445.

The recorded mechanical flags independently recompute to:

- `duration_increases_dependence`: false
- `endpoint_dependence`: false
- `endpoint_quality_guard`: true

The narrow preregistered P3-LT result therefore does not pass either
dependence gate; the endpoint quality guard passes. This report does not
interpret the research hypothesis or establish scientific success.

## Metadata note

The raw suite manifest retains the inherited
`hypothesis_null_reason` text “infrastructure validation only; does not test
H1-H5” while also recording the narrow P3 longer-training hypothesis. The raw
metadata is preserved. The result review field remains `PENDING`, and Astra
validation remains `NOT_PERFORMED`.
