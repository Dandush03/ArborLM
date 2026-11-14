# P7-B pre-freeze re-audit (narrow re-check after the fixes to AUDIT.md findings)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`), auditor role, separate context. Date 2026-11-13.
- **Status:** independent engineering and mathematical evidence. **Not Astra validation, not human approval.** `Astra review: NOT_PERFORMED`.
- Scope: the changed files `p7b_analysis.py`, `p7b_core.py`, `p7b_gates.py`, `p7b_sim.py`, `p7b_stage.py`, `p7b_study.py`, `p7b_workers.py` and `tests/test_p7b_*.py`, each re-read in full; HEAD `40cf266`; ADR-0014 unchanged (sha256 `79906d74…2a30`). SHA-256 of every file re-checked: `recheck/outputs/rechecked_source_sha256.txt`.
- Unchanged, confirmed by SHA-256 against `outputs/audited_source_sha256.txt`: `p7b_layout.py`, `p7b_panel.py`, `p7b_trace.py`, `p7b_synth.py`, `p7b_budget.py`, `tests/test_p7b_layout.py`, the ADR, and my three tools.
- **Verdict: READY TO FREEZE**, under the procedural conditions listed at the end. No new BLOCKER or MAJOR.

## Not opened

No evaluation trace, no stream-B trace (none exists), no raw validation parquet, no model checkpoint. No registered stage against `experiments/` or `results/` of the repository. Real data opened: the 81 calibration traces (`calib_selected`, `calib_branches`), behind an `open()`/`read_bytes()` spy that aborts on any non-`calib_` trace (it did not fire). The registered-path harness ran in a scratch `git clone` with synthetic data only.

## Environment and commands

Apple M5 Max, Darwin 27.2.0, CPython 3.12.14 (`.venv`), uv 0.12.15, repository root as working directory. `SP` is the session scratchpad.

| Command | Result | Log |
|---|---|---|
| `uv run --locked pytest -q -p no:cacheprovider tests/test_p7b_{layout,sim,analysis,gates,study}.py` | 195 passed, 88 s | `recheck/outputs/pytest_p7b_recheck.log` |
| `uv run --locked ruff check .`; the same on P7-B files and `tools/`; `ruff format --check` on P7-B files; `uv run --locked mypy src/arborlm` | all clean (76 source files) | `recheck/outputs/ruff_mypy_recheck.log` |
| `uv run --locked --extra pilot python -m arborlm.p7b_study dry-run` | every stage 0, experiments/results unchanged | `recheck/outputs/dry_run_recheck.log` |
| `.venv/bin/python -I recheck/registered_path_scratch_git.py "$PWD" $SP/regpath` | **PASS, 30/30 checks** (see item 3) | `recheck/outputs/registered_path_scratch_git.{log,json}` |
| `.venv/bin/python -I checks/implementer_layouts_scratch.py $SP/recheck_impl_table.json 1` | 81 checkpoints, 76.5 s | `recheck/outputs/implementer_layouts_scratch_recheck.log` |
| `.venv/bin/python -I tools/independent_layouts.py --repo . --hash-table $SP/recheck_impl_table.json --layout-run-id SCRATCH-RECHECK-IMPLEMENTER-HARNESS --jobs 1 --out recheck/outputs/layout_confirmation_recheck_vs_scratch_implementer.json --detail $SP/recheck_layout_detail.json` | **AGREE**, 81 checkpoints, 0 differences, 104.8 s; `checkpoints` block identical to the pre-fix audit's | `recheck/outputs/independent_layouts_real_calibration_recheck.log` |
| `.venv/bin/python -I recheck/run_time_checks_on_calibration.py $SP/rc_cal{A,B} 9 {A,B}` | 81 checkpoints × 2 seed sets: **0** m10 failures, **0** m2 failures, 2,538 R = 1 groups compared per seed set | `recheck/outputs/run_time_checks_on_calibration_{A,B}.log` |
| `.venv/bin/python -I tools/independent_resim.py --repo . --stream {A,B} --stream-source calibration --hash-table $SP/rc_cal{A,B}/layout_hash_table.json --simulate-dir $SP/rc_cal{A,B}/simulate --simulate-run-id SCRATCH-RECHECK-CAL-AS-STREAM-{A,B} --jobs 9 --out recheck/outputs/resim_confirmation_recheck_calibration_as_stream{A,B}.json --detail …` | **AGREE** both, 18 checkpoints, 2,280 simulations each, 0 differences | `recheck/outputs/independent_resim_recheck_calibration_as_stream{A,B}.log` |
| `.venv/bin/python -I checks/analysis_independent.py` | PASS, 0 mismatches (outcome, pairing, decision, recommendation, 20 scenarios) | `recheck/outputs/analysis_independent_recheck.log` |

Failed attempt (my mistake), kept: `recheck/failed_attempts/cmp_oneliner_FAILED_compared_different_json_shapes.log`. I compared two JSON objects with different shapes, so the result is discarded.

## 1. Status of each item

| Item | Status | Where |
|---|---|---|
| **M1** | **FIXED** | `p7b_core.py:256-274` (`tracked_and_clean`), `p7b_study.py:495-523` (`verify_stream_b_manifest`: tracked and clean, complete, equal to trace-b's recorded hash, bound to the layout table and the identity manifest), `:538-540, 556, 600-601` (both streams; SHA-256 in linkage and job); `p7b_workers.py:329-344` (manifest re-hashed per worker), `:365-376` (trace file hashes against the manifest), `:394-402` (counts hash), `:405-426` (null seeds and hashes); tests `test_p7b_study.py:614-811` |
| m1 | FIXED | `p7b_gates.py:44-74`, applied at `:116, 186, 259`; `p7b_core.py:229-253` |
| m2 | FIXED | `p7b_sim.py:241-272`, called at `p7b_workers.py:505`, recorded at `:518` |
| m3 | FIXED as scoped (linkage). The second half, "refuse a registered stage when sources or the ADR are uncommitted", is **not implemented** and is handled procedurally (r1) | `p7b_core.py:212-220`; `p7b_stage.py:159-160, 190-191, 204-206, 227-245`; `p7b_workers.py:439, 508` |
| m4 | Procedural (lead). A probe confirms that an ADR edit makes the next stage refuse | — |
| m5, m7 | No code change (lead). m7: no measured `loader-smoke` timing is recorded, so the 2.49× panel + trace-b margin is still projected, not measured | — |
| m6 | FIXED. Writing the partial record costs ≤ 0.02 s per checkpoint at real record size | `p7b_sim.py:479-490, 517-526`; `p7b_workers.py:459-461`; `p7b_stage.py:334-337` |
| m8 | FIXED | `p7b_analysis.py:909-963`; test `test_p7b_analysis.py:649` |
| m9 | FIXED | `p7b_core.py:420-432`; `p7b_workers.py:484-486` |
| m10 | FIXED | `p7b_sim.py:230-238` |
| m11 | FIXED | `p7b_study.py:335-337`; test `test_p7b_study.py:830` |
| m12 | Decided (lead): panel is the first registered stage, after the freeze. The code agrees: `panel` is a registered stage, and trace-b and simulate are bound to it by hash | — |

Regressions: none found. The changes are additive checks. The criterion arithmetic is unchanged (independent check: 0 mismatches). The layout builder is unchanged (identical hashes on 81 calibration checkpoints). The simulator counts are unchanged (independent re-simulation AGREE).

## 2. M1 specifically

- **Can either stream be simulated without the manifest tracked and unmodified at HEAD?** No. `run_simulate` calls `verify_stream_b_manifest` for both A and B before `open_stage`. In the scratch clone, using the registered (non-dry) path:
  - simulate A and B were refused while the manifest was untracked;
  - simulate A was refused while it was staged but not committed;
  - simulate B was refused when the committed file had been edited in the working tree.
  - No simulate stage directory was created by any refusal.
- **Does the stream-B worker check the trace, counts and null hashes against the manifest?** Yes. Each worker:
  - re-hashes the manifest against the hash recorded when the stage opened;
  - compares the selected and branch file hashes with the manifest entry, then `read_trace` verifies the files against those hashes;
  - checks `counts_sha256`;
  - checks every null `replicate_seed` and `stream_sha256`.
  - Every one of these refusals is covered by a test.
- **Can the dry-run Git stand-in be reached outside a dry run?** Not from the command line.
  - `Options.dry_run` is `False` for every command (tested); only `p7b_study.dry_run()` (`:968`) sets it, together with scratch roots.
  - A stage opened with `dry_run=True` refuses the registered roots (`registered_roots_refused`).
  - `require_completed` refuses to let a dry-run stage consume a registered record, and the reverse.
  - The linkage records `stand_in: false` and the real Git check text. The scratch run confirmed this for both streams.

## 3. m1: do my tools, unmodified, satisfy the gates?

**Yes. No tool change is needed.** End-to-end run in a scratch clone (`recheck/registered_path_scratch_git.py`):

- **Setup:** the clone was made at `40cf266`, and the P7-B sources, tests and my three tools were committed at their registered paths as a simulated freeze. Then the **registered** code path ran (`dry_run=False`; synthetic data from the implementer's fixture).
- **Gates:** each tool's own `tool_sha256` equalled `git show HEAD:<path> | sha256` and passed:
  - gate (a) in `trace-b`;
  - gate (b) in `trace-b` and in both `simulate` stages;
  - gate (c) twice in `analyze`.
  - Every linkage records `stand_in: false`.
- **Negative controls:** a stand-in file was refused outside a dry run. The output of a tool edited after the commit was refused ("not the SHA-256 of … at HEAD"). The tool was restored byte-identical.
- **Conditions:**
  - The working-tree bytes must equal the blob bytes. There is no `.gitattributes` and `core.autocrlf` is unset, so they do.
  - The tools must not be in an ignored path. They are not; only `__pycache__/` and `.ruff_cache/` under this folder are ignored.

Final tool hashes (unchanged from AUDIT.md):

```
bfb21a577f03b4643caf418b99f04bab59b7c2f2de1eb324effb63bae10477b9  tools/independent_layouts.py
73a2176c5dc94f5843b9209f847a5dbfedf9bdac465dafa912f53c69c7e85a53  tools/independent_panel.py
4e53ebbce18418393e97cfba6f595cc419cf3fd2691c4704b901a448a38f02f1  tools/independent_resim.py
```

## 4. m3: linkage across the required commits

This was tested in the same clone, using the registered order:

1. Freeze commit, then `panel` and `layouts`.
2. Commit 1: panel and layouts compact folders, plus the confirmation files under `docs/reviews/`.
3. `trace-b`.
4. Commit 2: the trace-b compact folder, including `stream_b_identity_manifest.json`.
5. `simulate` A and B.
6. Commit 3 (optional): simulate records and re-simulation confirmations.
7. `analyze`.

Results:

- **Commits between stages are safe.** Every stage completed, and every stage's end-of-stage frozen check passed. All six manifests carry the same `package_source_sha256` while recording four different informational HEADs. Commits that touch only `results/` and `docs/reviews/` therefore do not break linkage.
- **Edits under `src/arborlm/` or to ADR-0014 are not safe.** An edit to `src/arborlm/io.py`, a non-P7-B module, made the next stage refuse ("the src/arborlm sources differ"). So did an edit to ADR-0014 ("the specification differs"). After either edit the study cannot continue without restoring the bytes or running `--supersede`.
- **Do not commit while a stage is running.** Each stage checks the version-controlled tree at its end.

## 5. Can m2 or m10 stop the registered run spuriously?

**No, in principle or in practice.**

- **Proof sketch.** Every query holds 8 distinct slots: `check_trace` enforces this for streams A and B, and the null construction enforces it for nulls. Every C is ≥ 8.
  - **m10:** after a query, the cache holds exactly the C most recently used pages in one global recency order (the current query's ≤ 8 pages are the most recent). LRU is therefore a stack algorithm: every access that hits at C also hits at every C' > C. Capacity misses cannot increase with C, for any subset of accesses, under either tie rule.
  - **m2:** at R = 1 every layout is a bijection from slots to pages, so query sizes and first touches are layout-invariant. At C = 8 the cache after each query is exactly that query's page set, so misses are |Q_t \ Q_{t−1}|, which does not depend on the layout.
- **Measured.** On all 81 real calibration traces treated as a stream, with both null seed sets: 0 failures of either check; 2,538 R = 1 groups compared per seed set, which is every R = 1 group in the records.

## 6. Calibration layout check and synthetic full sequence

See the table above:

- layouts AGREE on 81/81;
- re-simulation AGREE for both seed sets on records from the changed simulator;
- full synthetic sequence with every confirmation file produced by my tools, under the new gate bindings and the real Git checks, passed (section 3).

## New findings (MINOR or NOTE; none blocks the freeze)

- **r1 (MINOR, procedural).** No code check that the sources and ADR are committed when a stage starts. m3's second half is not implemented, and `git_dirty_informational` only records the state. Before each stage, run the clean-tree check in the sequence below. After the run, compare `panel` `package_source_sha256` with the freeze commit.
- **r2 (MINOR, procedural).** Gate (c) binds only `independent_resim.py`. That tool imports `independent_layouts.py` at run time, and that file's hash appears only inside the `tool` string. Gate (b) binds it at HEAD, but a working-tree edit made between gates (b) and (c) would go unnoticed. The pre-step `git diff --quiet HEAD -- $T` below closes this gap.
- **r3 (MINOR, procedural).** The tools must be committed together with this folder's `ruff.toml`. Without it, `ruff check .` flags two unused imports in `tools/`.
- **r4 (NOTE).** The docstring of `p7a_stage.tracked_state_sha256` (immutable P7-A file) says `results/` is git-ignored. It is not; only `/experiments/` and `/data/` are. This has no effect on P7-B, because `results/` files are committed between stages, never during one.

## Post-freeze command sequence (registered order)

Run from the repository root.

- **Freeze commit (lead):** the 12 `src/arborlm/p7b_*.py`, the 5 `tests/test_p7b_*.py`, all of `docs/reviews/p7b-preflight-2026-11-13/` (including `tools/` and `ruff.toml`), and the ADR-0014 freeze record as the last ADR edit.
- **Raw validation parquet:** read only by steps 1 and 2.
- **Model:** only step 5 runs one.

```sh
A=docs/reviews/p7b-results-audit-2026-11-13; T=docs/reviews/p7b-preflight-2026-11-13/tools; R=results/p7b-2026-11-13
# before EVERY numbered step: must print nothing and exit 0
git status --porcelain --untracked-files=all -- src tests configs docs/decisions $T && git diff --quiet HEAD -- src tests configs docs/decisions $T
mkdir -p $A; shasum -a 256 $T/*.py > $A/tool_sha256.txt      # must equal the three hashes above
for f in $T/*.py; do git show HEAD:$f | shasum -a 256; done  # same three hashes

# 1. panel (implementer stage)                      READS raw train + VALIDATION parquet; no model
uv run --locked --extra pilot python -m arborlm.p7b_study panel
# 2. independent panel (auditor)                    READS raw train + VALIDATION parquet; no model
uv run --locked --extra pilot python -I $T/independent_panel.py --mode real --data-dir data/wikitext2 \
  --panel-record $R/panel/<PANEL_RUN>/panel_record.json --panel-run-id <PANEL_RUN> \
  --out $A/panel_confirmation.json --detail $A/panel_detail.json > $A/panel.log 2>&1
# 3. layouts (implementer stage)                    calibration traces only; no model
uv run --locked --extra pilot python -m arborlm.p7b_study layouts
# 4. independent layouts (auditor)                  calibration traces only; no model
.venv/bin/python -I $T/independent_layouts.py --repo . --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --layout-run-id <LAYOUT_RUN> \
  --out $A/layout_confirmation.json --detail $A/layout_detail.json > $A/layouts.log 2>&1
# COMMIT 1: layout hash table, panel record and both confirmations (only results/ and docs/reviews/)
git add $R/panel/<PANEL_RUN> $R/layouts/<LAYOUT_RUN> $A/tool_sha256.txt \
  $A/panel_confirmation.json $A/panel_detail.json $A/panel.log \
  $A/layout_confirmation.json $A/layout_detail.json $A/layouts.log
git commit -m "P7-B: panel record, layout hash table and independent confirmations"
# 5. trace-b (implementer stage)                    RUNS THE MODEL (P5 checkpoints; P5 frozen-data
#    tensors and panel_b.bytes from step 1; not the raw parquet)
uv run --locked --extra pilot python -m arborlm.p7b_study trace-b --parent-suite <P5_SUITE> \
  --panel-confirmation $A/panel_confirmation.json --layout-confirmation $A/layout_confirmation.json
#    (<P5_SUITE> as P7-A used: experiments/P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be)
# COMMIT 2: the stream-B identity manifest, before any simulation (simulate refuses otherwise)
git add $R/trace-b/<TRACE_B_RUN> && git commit -m "P7-B stream-B identity manifest"
# 6./7. simulate stream A, then stream B, back to back, no inspection   eval traces; no model
uv run --locked --extra pilot python -m arborlm.p7b_study simulate --stream A --layout-confirmation $A/layout_confirmation.json
uv run --locked --extra pilot python -m arborlm.p7b_study simulate --stream B --layout-confirmation $A/layout_confirmation.json
# 8. independent re-simulation, both streams (auditor, 18 registered checkpoints)   no model
.venv/bin/python -I $T/independent_resim.py --repo . --stream A --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --simulate-dir $R/simulate-a/<SIM_A_RUN> \
  --out $A/resim_confirmation_A.json --detail $A/resim_detail_A.json > $A/resim_A.log 2>&1
.venv/bin/python -I $T/independent_resim.py --repo . --stream B --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --simulate-dir $R/simulate-b/<SIM_B_RUN> \
  --trace-b-compact $R/trace-b/<TRACE_B_RUN> --trace-b-dir experiments/<TRACE_B_RUN>/traces \
  --out $A/resim_confirmation_B.json --detail $A/resim_detail_B.json > $A/resim_B.log 2>&1
# optional COMMIT 3 (verified safe): $R/simulate-a/<SIM_A_RUN> $R/simulate-b/<SIM_B_RUN> $A/resim_*
# 9. analyze, once                                  no model, no parquet
uv run --locked --extra pilot python -m arborlm.p7b_study analyze \
  --resim-confirmation-a $A/resim_confirmation_A.json --resim-confirmation-b $A/resim_confirmation_B.json
```

Any tool exit code 2 (`DISAGREE`), or any stage refusal, stops the study at that point (ADR §11). If a stage needs a rerun, it takes `--supersede <RUN> --reason <text>`. If anything in `src/arborlm/`, ADR-0014 or `$T` changes after the freeze, the study needs a new freeze.

## Conditions for the freeze (procedural; not code)

1. The freeze commit includes the three tools at their registered paths, unmodified (hashes above), together with `ruff.toml` (r3).
2. The ADR-0014 freeze record is the last edit of ADR-0014 until `analyze` completes (m4). It records m12 as decided (panel after the freeze), and m5/m7 as accepted without code change.
3. The clean-tree pre-step runs before each numbered step (r1, r2).

## Not checked

- the real validation-parquet path of either panel reconstruction;
- real trace-b (model loading, replay, regeneration, the RSS of real workers);
- the real P7-A reproduction on stream A;
- measured `loader-smoke` timing (m7);
- the clerk's inventory of prior rank usage;
- descriptive tables beyond spot checks;
- whether the workers in the scratch clone imported the clone's or the repository's `src`. The harness process imported the clone's. The two copies were byte-identical (same package hashes in every manifest), so the result does not depend on it.
