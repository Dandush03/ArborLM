# P7-B pre-freeze audit (ADR-0014, revision 4 + section 15 clarifications)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`), auditor role, separate context. Date 2026-11-13.
- **Status:** independent engineering and mathematical evidence. **Not Astra validation, not human approval.** `Astra review: NOT_PERFORMED`.
- Scope: the untracked P7-B implementation (12 modules, 5 test files) on branch `claude/p7b-coaccess-layout-proposal`, HEAD `40cf266`, against the binding text of ADR-0014 (sha256 `79906d74…0c5fd`). SHA-256 of every audited file: `outputs/audited_source_sha256.txt`; re-verified unchanged at the end of the audit.
- Result: **0 BLOCKER, 1 MAJOR, 12 MINOR, 8 NOTE.** Verdict at the end.

## What was read and what was not

Read: `AGENTS.md`, `CLAUDE.md`, ADR-0014 in full (incl. sections 13, 15 and the five clarifications), ADR-0013 sections 10–15, every audited module and test, the immutable modules they call (`p7a_core`, `p7a_sim`, `p7a_trace`, `p7a_stage`, `p6_stage`, `p6_common` (registry and loader), `p5_model` (`evaluate`, `state_digest`), `p5_data`, `p2_data`, `pilot_data`, `io`, `records.record_source`, `fetch_wikitext` pinned hashes), the identity manifest and the head of `panel_usage.md` under `docs/reviews/p7b-spec-inputs-2026-11-13/`, `results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json`, my own earlier review scripts, and the 18-checkpoint selection recorded in `docs/reviews/p7a-results-audit-2026-11-13/independent_sim_registered.json`.

Real data opened: the 81 **calibration** `calib_selected.int16.bin` files (my tool) and, through the implementer's calibration-only loader in scratch harnesses, the 81 `calib_selected` and 54 `calib_branches` files; the pinned **train** parquet (`data/wikitext2/train-00000-of-00001.parquet`) by `checks/panel_tool_train_only.py`.

**Not opened:** no evaluation trace (`eval_selected` / `eval_branches`) of any checkpoint; no stream B trace (none exists; none was generated); the raw **validation** parquet; any P7-A simulation worker record. No registered stage was run against `experiments/` or `results/`; no layout was evaluated on an evaluation stream; no model was loaded (`loader-smoke` was not run). The scratch harnesses that call the implementer's code install an `open()`/`read_bytes()` spy that aborts on any trace file not named `calib_*`; it never fired. Everything written is inside this folder or the session scratchpad.

## Environment and commands

Apple M5 Max (18 cores), Darwin 27.2.0; `.venv/bin/python` = CPython 3.12.14; uv 0.12.15; repository root as working directory. Tools are run with `-I` (isolated; no `arborlm` import is possible from them).

| Command | Result | Log |
|---|---|---|
| `uv run --locked pytest tests/test_p7b_{layout,sim,analysis,gates,study}.py -q -p no:cacheprovider` | 164 passed, 59.7 s | `outputs/pytest_p7b.log` |
| `uv run --locked ruff check . ; uv run --locked mypy src/arborlm` | clean (after adding `ruff.toml` in this folder, see below) | `outputs/ruff_mypy.log` |
| `uv run --locked --extra pilot python -m arborlm.p7b_study budget` | all twofold margins met (see section 11 below) | `outputs/budget.log` |
| `.venv/bin/python -I checks/implementer_layouts_scratch.py <scratch>/impl_table_jobs1.json 1` | implementer builder, R = 2, 8, 81 checkpoints, 63.6 s | `outputs/implementer_layouts_scratch.log` |
| `.venv/bin/python -I tools/independent_layouts.py --repo . --hash-table <scratch>/impl_table_jobs1.json --layout-run-id SCRATCH-IMPLEMENTER-HARNESS --jobs 1 --out outputs/layout_confirmation_vs_scratch_implementer.json --detail <scratch>/layout_detail_jobs1.json` | **AGREE**, 81 checkpoints, 0 differences, 81.2 s | `outputs/independent_layouts_real_calibration_jobs1.log`, `outputs/layout_detail_real_calibration.json` |
| `.venv/bin/python -I checks/gate_controls_layout.py …` | genuine file accepted by gate (b); 6 altered files refused; tool reports DISAGREE (exit 2) on an altered table | `outputs/gate_controls_layout.log` |
| `.venv/bin/python -I checks/implementer_sim_on_calibration.py <scratch>/calsimA 9 A` (and `… calsimB 9 B`) | implementer's full per-checkpoint plan on the 18 selected **calibration** traces treated as a stream | `outputs/implementer_sim_on_calibration_{A,B}.log` |
| `.venv/bin/python -I tools/independent_resim.py --repo . --stream A --stream-source calibration --hash-table <scratch>/calsimA/layout_hash_table.json --simulate-dir <scratch>/calsimA/simulate --simulate-run-id SCRATCH-CAL-AS-STREAM-A --jobs 1 --out outputs/resim_confirmation_calibration_as_streamA.json --detail <scratch>/resim_detail_calA.json` (and the same for B) | **AGREE** both, 18 checkpoints × 2,280 simulations each, 0 differences, 190.7 s and 190.2 s | `outputs/independent_resim_calibration_as_stream{A,B}_jobs1.log`, `outputs/resim_detail_calibration_as_stream{A,B}.json` |
| `.venv/bin/python -I checks/resim_negative_controls.py …` | gate (c) accepts the genuine file, refuses 6 altered ones; tool DISAGREE on a +1 count, an altered null hash and an altered layout table; AGREE on the clean control | `outputs/resim_negative_controls.log` |
| `.venv/bin/python -I checks/validate_panel_synthetic.py <scratch>/panelval` | panel tool AGREE with `p7b_panel.reconstruct_from_rows` on a synthetic corpus at registered sizes; gate (a) accepts genuine, refuses 7 altered; implementer stops on a wrong earlier hash | `outputs/validate_panel_synthetic.log` |
| `uv run --locked --extra pilot python -I checks/panel_tool_train_only.py` | panel tool's reader and ranking on the real **train** parquet reproduce P1 train hash, P5 train selection hash and P5 train counters | `outputs/panel_tool_train_only.log` |
| `uv run --locked --extra pilot python -I checks/dry_sequence_with_auditor_tools.py <scratch>/dryseq` | full registered sequence (panel → layouts → trace-b → simulate A → simulate B → analyze) on the dry-run fixture with **every confirmation file produced by my tools**: all stages completed, all tools AGREE, repository `experiments/` and `results/` unchanged | `outputs/dry_sequence_with_auditor_tools.log` |
| `.venv/bin/python -I checks/analysis_independent.py` | my own criterion layer vs `p7b_analysis`: 972 outcome-table inputs, 64 pairing, 64 decision, 16 recommendation inputs, 20 synthetic 81-checkpoint two-stream scenarios: **0 mismatches** (exact ρ and ρ_adj rationals) | `outputs/analysis_independent.log` |
| `.venv/bin/python -I checks/sensitivity_layouts_crosscheck.py` | A0 and A8 affinities, L-COAX8, L-COAXg, L-BCOAX8, L-COAX/L-BCOAX/L-BCOAXg/L-PCOAX-1 at R = 512 equal on 3 real calibration traces | `outputs/sensitivity_layouts_crosscheck.log` |
| `python3 -I checks/r1_invariance_on_scratch_records.py <scratch>/calsimA/simulate` | R = 1 invariants hold on 300 groups (finding m2) | `outputs/r1_invariance_on_scratch_records.log` |

Failed attempts are kept in `failed_attempts/` (all three were my own mistakes): the panel tool first applied the registered-file identity checks in synthetic mode (verdict DISAGREE though the reconstruction agreed); the calibration-simulation harness first did not create its output folders; the analysis fixture first omitted the `stats` block the implementer's descriptive tables need.

`ruff.toml` in this folder: the repository's `ruff check .` flagged two unused imports in my files; to keep the tools byte-identical to the versions whose SHA-256 is embedded in the confirmation files I added a folder-level ignore (as earlier review folders do) instead of editing them.

Tool SHA-256 (the versions validated here): `independent_layouts.py` `bfb21a57…77b9`, `independent_resim.py` `4e53ebbc…02f1`, `independent_panel.py` `73a2176c…a53`.

## Part A — findings

### MAJOR

**M1. "Stream-B identity manifest committed before any simulation" is not enforced, and simulation is not bound to the manifest itself.** ADR §7a ("written and committed before any simulation of either stream"), §15 clarifications 2 and 5.
- `p7b_study.run_simulate` (`src/arborlm/p7b_study.py:491-533`) checks only that a completed trace-b run exists (`stages.upstream_linkage`, `p7b_stage.py:212-235`) and a layout confirmation. Nothing checks that `results/…/trace-b/<run>/stream_b_identity_manifest.json` is tracked by Git and unmodified, and its SHA-256 is not recorded in the simulate manifests (it is reachable only transitively through the trace-b `result.json` hash).
- The stream-B simulate worker verifies the trace file and the null-stream hashes against the per-checkpoint compact records `trace-b/<run>/checkpoints/<label>.json` (`p7b_workers.py:345-356, 359-374`), not against the manifest, and never compares the per-slot counts hash with the manifest's `counts_sha256`.
- Consequence: the registered order can be run with the manifest uncommitted (or a regenerated compact record) and nothing in the records shows that stream B's identity was fixed before simulation. It does not by itself produce a wrong number, but it removes the code-level evidence for a registered requirement.
- Fix: in `run_simulate` (both streams) refuse unless the manifest is tracked and clean (`git ls-files --error-unmatch <path>` and `git diff --quiet HEAD -- <path>`; this is a cleanliness check, not a HEAD binding, so it is compatible with clarification 2), record its SHA-256 in `linkage`; in the stream-B worker verify the selected/branches SHA-256, `counts_sha256` and the three null hashes against the manifest entry; add a test that an uncommitted or edited manifest is refused. Until fixed, my `independent_resim.py --stream B` independently checks the trace file hashes, counts hash and null hashes against the manifest (it reads the manifest, not only the compact records), and the post-freeze commands below include the Git check.

### MINOR (each with a fix)

- **m1. Gates do not bind to the auditor's tools.** `p7b_gates.py:47-258` accepts any well-formed `AGREE` file whose hashes equal the implementer's own record; the dry-run stand-ins (`p7b_study.py:814-899`) show that a file copied from the implementer's values passes. Stale or mismatched files are refused (verified by controls). Fix: require `tool_sha256` and check it against the SHA-256 of the tracked tool file at a registered path (`docs/reviews/p7b-preflight-2026-11-13/tools/independent_*.py`); record it. My tools already emit `tool_sha256`.
- **m2. The R = 1 correctness requirement (ADR §4, §10) is checked only in tests** (`tests/test_p7b_layout.py:373`), not at run time. Fix: in the simulate worker, raise `InvariantError` unless, on the actual stream at R = 1, `hist`, both first-touch counts and the capacity misses at C = 8 are identical across all layouts. My check on 18 real calibration-as-stream records: 0 violations in 300 groups, 925 allowed layout differences at C > 8.
- **m3. The freeze is not enforced in code, and cross-stage linkage covers only `p7b_*.py` and the ADR** (`p7b_core.py:206-208`, `p7b_stage.py:212-235`). Imported modules (`p7a_core`, `p6_common`, `p5_model`, `io`, `records`, `watchdog`, `pilot_data`, `p2_data`) could change between stages without the linkage noticing (only the within-stage `tracked_state_sha256` would). Fix: bind linkage to the per-file hashes of all `src/arborlm/*.py` (already computed by `record_source`), and refuse to open a registered stage when any `p7b_*.py` or ADR-0014 is untracked or differs from HEAD.
- **m4. Any edit of ADR-0014 after the panel stage breaks every later linkage** (`spec_sha256` equality, `p7b_stage.py:223`), forcing `--supersede` reruns. Fix (procedural): the freeze record must be the last edit of ADR-0014 until `analyze` completes; interim evidence goes to `docs/reviews/` or `results/`.
- **m5. The calibration-only interface is partial.** `CalibrationTrace.declared` (`p7b_layout.py:73-77`) accepts any tensor, and `greedy_pages`, `refine_pages`, `coax_pages`, `group_coax_pages`, `pair_affinity` are public. The registered worker uses `from_identity` only, and the temporal order (layouts confirmed before stream B exists; hashes re-verified at simulation) plus my calibration-only rebuild are the real guarantee. Fix: the layouts worker asserts `cal.source == "identity-manifest"` and records it; `declared` requires an explicit synthetic marker.
- **m6. Simulation partial records exist only for the worker's own deadline.** `simulate_checkpoint` calls `progress` once, at the end (`p7b_sim.py:464-465`), so a watchdog kill (RSS or wall) leaves no partial record. Fix: write `partial.json` after each layout.
- **m7. The panel + trace-b margin (2.49×) rests on an analytical model-time projection** (`p7b_budget.py:163-173`, P7-A's 135 s scaled by 4/3). Fix: measure with `loader-smoke` and rerun `budget --replay-seconds … --load-seconds …` before the freeze (ADR §11 requires a twofold margin for every cap).
- **m8. Robustness grid:** `HB_A8`, `HB_greedy` and `HB_order_shuffled` at the two criterion settings always show class INCOMPLETE because descending runs exist only for criterion layouts (`p7b_analysis.py:909-953` with `p7b_sim.py:269-279`). Descriptive only. Fix: evaluate these variants with `ties=("asc",)` and say so.
- **m9. The P7-A reference record is read without a completeness check** in the simulate worker (`p7b_workers.py:366, 430`); `core.load_p7a_reference` (`p7b_core.py:358-364`) exists but is unused. Fix: use it.
- **m10. `p7b_sim.check_group` drops P7-A's whole-stream capacity-miss monotonicity check** (`p7a_sim.py:237-243` vs `p7b_sim.py:228-233`). Fix: add it.
- **m11. The stream-B manifest hard-codes `regeneration_byte_identical_to_identity_manifest: True`** (`p7b_study.py:335`) instead of copying the record's value. Truthful today (a record exists only if regeneration passed), fragile. Fix: copy `rec["regeneration"]["byte_identical_to_identity_manifest"]`.
- **m12. PENDING LEAD REVIEW — document conflict on where the panel proof sits.** ADR §7a ("Stream B must be shown to be unused before the freeze") and §12 put the double reconstruction **before** the freeze commit; clarification 5 lists "panel proof" as the first step of the registered order, and the code makes `panel` a registered stage bound to the P7-B source hashes. Both orders work with the code because linkage is by hash (verified in the dry sequence), provided no `p7b_*.py` changes between the panel stage and the freeze. The lead must record which order is used (AGENTS.md: documents disagree). Recommendation: run `panel` and my panel tool on the final sources immediately before the freeze commit, so a panel failure never forces a re-freeze; otherwise freeze first and accept that a panel failure means a new freeze.

### NOTE

- **n1. PENDING LEAD REVIEW.** A negative ρ_adj (tree level at common utilization below zero) satisfies "≤ 0.80" literally (`p7b_analysis.py:181-216`); only "a + b·x̄ ≤ 0" is undefined. It can matter only together with raw ρ ≤ 0.80 and the counts rule.
- **n2.** Non-degeneracy is evaluated per comparison (HB and HU each use their own numerator floor), which is the natural reading of "both layouts being compared"; "every classification there is DEGENERATE" could be read as setting-wide. HU does not enter the outcome.
- **n3.** The L-NCOAX band raises a top-level flag per stream (`ncoax_control_flagged`) and does not change any classification, as §7 says ("flagged").
- **n4.** INCOMPLETE is an extra label for missing data (never reached on a complete run; it yields decision INCOMPLETE and no recommendation row).
- **n5. Independence.** The implementer's `greedy_pages` / `refine_pages` mirror my revision-3 review script (`docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/rev3_layouts.py`) nearly line for line. My new tool therefore uses a different structure (lazy max-heap greedy; refinement gains recomputed literally from page contents, no incremental page-weight tables; my own count-preserving null), and it agrees on all 1,458 criterion layouts plus L-FREQ for the 81 real calibration traces.
- **n6.** §10 says "exactly the configurations P7-A ran" and then enumerates a list without the context-shuffled stream, which P7-A also ran; the implementation follows the list.
- **n7.** "No analysis output before both streams are simulated" is procedural for the operator: simulate A records are readable before simulate B runs. Run the two simulate stages back to back without inspecting records.
- **n8.** The order-shuffle permutation (seed 91201) is the same for both streams. It is registered and not data-dependent.

### Checks by item (what holds)

1. **Layouts (§4).** Same-query affinity, windowed A8 (nine offsets incl. t = u, N + Nᵀ), greedy fill with every tie rule, the zero-score fall-through, refinement (visit order by (−f, ID) over slots with nonzero affinity; candidate pages = other pages holding a slot with nonzero affinity to x; gain = change of total within-page affinity; strictly positive; ties lowest Q then lowest y; position exchange; ≤ 12 passes; constrained swaps within the group), group order by descending total (ties lowest index), R = 512 group rule (rows inside a group in the R = 256 greedy order), L-BCOAX/L-PCOAX, partitions (all five registered hashes reproduced), L-NCOAX from the calibration null (seed 91311, generator `s·1000 + cell_index`; null hashes and counts hashes equal to the implementer's for all 81), and the canonical hash are as written. Independent agreement: all 81 × (8 or 9 layouts) × R ∈ {2, 8}; sensitivity layouts and R = 512 on 3 checkpoints. No registered code path passes evaluation or stream-B data to a builder (layouts are built and confirmed before stream B exists; simulation re-verifies every canonical hash, `p7b_workers.py:308-326`); see m5 for the interface's limits.
2. **Panel (§7a, clarification 4).** `select` ranks all candidates and slices, so ranks 0..2559 are provably unchanged when 3,072 are requested (`pilot_data.py:75-80`); the five earlier panels are re-hashed and must equal P1–P5 (`p7b_panel.py:76-86`); overlaps checked against P1–P5, the calibration stream (train pool ranks 2048–2559), the full training candidate pool (every train chunk digest) and within the panel; P5 frozen selection, train selection and validation counters checked; any failure raises `StopError`. Freshness in the sense of "never evaluated" cannot be detected by code and rests on the clerk's inventory (I did not repeat it).
3. **Trace-b (§7a).** Per checkpoint in one process: bitwise P5 replay on the P5 panel, regeneration of calibration and stream-A traces compared with the identity manifest, stream B traced with `collect_trace` (forward on inputs only; no target, no `loss_for`), model state digest (parameters and buffers) and file hashes checked before/after, integrity checks, null seeds 91321–91323. What leaves the worker from the stream-A regeneration: the pass/fail verdict and hashes equal to the manifest's, plus the P5-panel NLL equal to the published value; nothing new. See M1 for the manifest.
4. **Simulator (§5).** Value pages only (`p7b_sim.py` imports no key path; test enforces), per-query service, LRU excluding the current query, both tie rules, hard capacity check, first-touch from the whole stream, warm boundary n/2, `pages == previous` skip is exact. My heap-based simulator agrees on 4,560 real-scale simulations (two seed sets) incl. per-context quantiles. P7-A reproduction is limited to what P7-A ran (`p7b_sim.py:289-297`). Stream B shares no state, file or seed with stream A.
5. **Analysis (§2, §7, §7a, §9).** E with the mean of three L-FREQ nulls under the same tie rule; ρ ratio of means; OLS on 54 points with x = entropy (ln effective slots) of the stream analysed, x̄ over the 54, undefined → INTERMEDIATE; floors incl. numerators under both tie rules; class order and closed boundaries; TIE-RULE DEPENDENT → INTERMEDIATE; HB/HU; PART_K on exploited structure with aggregate and every-partition clauses and its degeneracy rule; ordered outcome table with direction from ρ (primary, ascending); pairing; S/U/N/I; recommendation order. My enumeration: HIERARCHY-SPECIFIC ADVANTAGE only when HB is TREE MATERIALLY BETTER in both settings under both tie rules and PART_K is REAL BRANCHES BETTER in both settings under both tie rules; class S only with that outcome on both streams; no DEGENERATE, INCOMPLETE or tie-dependent input reaches either. `analyze` refuses unless both simulate stages completed all 81, used the same layouts and trace-b runs, and both re-simulation confirmations pass gate (c).
6. **Gates.** Each binds to the run ID and the SHA-256 of what it confirms (panel record; layout hash table; each of the 18 simulation records), refuses verdicts other than AGREE, wrong coverage and listed differences; genuine files from my tools pass in the legitimate order (dry sequence). See m1.
7. **Stages.** Single run per stage unless `--supersede` + `--reason`; manifests cite ADR-0014 and override the E0 template in worker manifests; caps per §11; partial records copied; end-of-stage frozen check; linkage by source/spec/upstream hashes, not HEAD; `loader-smoke` writes nothing under `experiments/`/`results/`. The order freeze → panel → layouts → (my layout tool) → trace-b → commit manifest → simulate A → simulate B → (my resim A, B) → analyze works with commits between stages (only ADR-0014 and `p7b_*.py` must not change; m4).
8. **Tests** test claims, not only self-consistency, in the places that matter (naive literal reading of steps 1–2, P7-A simulator equality, hand traces, gates, refusal paths). Untested: M1, m2 at run time, real `reconstruct_from_data_dir`, real trace-b and real P7-A reproduction (first exercised in the registered run). Failure mid-run: panel → stage failed, nothing downstream can start; layouts → incomplete table, gate (b) refuses; trace-b → stage failed, simulate refuses; simulate A reproduction mismatch → `StopError`, partial preserved, study stops per §11; every rerun needs `--supersede` and a recorded reason.

## PENDING LEAD REVIEW readings of the implementer

| Reading | Verdict |
|---|---|
| L-NCOAX band: mean of per-checkpoint G, both criterion settings, both tie rules | Coherent and conservative; the ADR names neither the setting nor the mean. The ratio of means is reported beside it. |
| Split-half: fit on one half of the calibration contexts, score on the other half with its own first half as warm-up (128 counted contexts), ascending rule, criterion settings | Coherent; calibration only; noisier than the full stream, which is the point of the measurement. |
| Per-context quantile levels (0, 5, 25, 50, 75, 95, 100%), lower nearest rank | Coherent; descriptive; levels are an implementer choice. |
| PART_K is NOT BETTER (flagged) when the tie rules disagree | Coherent with §7 ("only if all hold under both tie rules … otherwise NOT BETTER") and with the outcome row that names tie-rule dependence. |
| Extra L-ID null and order-shuffled runs on stream A | Coherent; required by §10's reproduction list. |
| Context-shuffled stream not run | Coherent with §6 and the §10 list; see n6 for the wording. |

## Part B — tools, validation and timing

| Tool | Validation now | Time (sequential, this machine) |
|---|---|---|
| `tools/independent_panel.py` | Synthetic corpus at registered sizes (2,000+ rows with duplicates, cross-split copies, multi-byte UTF-8): byte-identical panel, rows and ranks to `reconstruct_from_rows`; gate (a) accepts genuine, refuses 7 altered; on the real train parquet only: P1 train hash, P5 train selection and P5 train counters reproduced. **Not run on the validation file.** | < 2 s projected (train read and ranking 0.35 s) |
| `tools/independent_layouts.py` | Real calibration traces, all 81 checkpoints, R = 2 and 8: AGREE with the implementer's builder (scratch harness, public calibration-only interface), 0 differences; gate (b) controls pass; dry sequence | 81.2 s |
| `tools/independent_resim.py` | Real calibration traces treated as a stream for the 18 registered checkpoints with stream-A and stream-B seed sets: AGREE, 2 × 2,280 simulations, 0 differences; negative controls DISAGREE; synthetic dry sequence on the study's own stream-A and stream-B records: AGREE | 190.7 s + 190.2 s |

Projected auditor total after the freeze: about 81 + 191 + 190 + 2 ≈ 465 s against the 3,600 s cap (7.7× margin), all sequential (`--jobs 1`). The 18-checkpoint selection reproduced by my tool equals the one recorded in the P7-A results audit.

## Post-freeze commands (registered order)

All from the repository root; `<…>` are run IDs printed by each stage; outputs go to `docs/reviews/p7b-results-audit-2026-11-13/` (create it). Nothing in `tools/` changes after this audit; record its SHA-256 beside each output.

```sh
A=docs/reviews/p7b-results-audit-2026-11-13; T=docs/reviews/p7b-preflight-2026-11-13/tools; R=results/p7b-2026-11-13
mkdir -p $A; shasum -a 256 $T/*.py > $A/tool_sha256.txt

# 1. panel (implementer stage), then the independent panel reconstruction (reads the validation parquet)
uv run --locked --extra pilot python -m arborlm.p7b_study panel
uv run --locked --extra pilot python -I $T/independent_panel.py --mode real --data-dir data/wikitext2 \
  --panel-record $R/panel/<PANEL_RUN>/panel_record.json --panel-run-id <PANEL_RUN> \
  --out $A/panel_confirmation.json --detail $A/panel_detail.json > $A/panel.log 2>&1

# 2. layouts, then the independent rebuild (calibration traces only)
uv run --locked --extra pilot python -m arborlm.p7b_study layouts
.venv/bin/python -I $T/independent_layouts.py --repo . --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --layout-run-id <LAYOUT_RUN> \
  --out $A/layout_confirmation.json --detail $A/layout_detail.json > $A/layouts.log 2>&1
# commit: layout hash table and the two confirmation files

# 3. stream B traces (only model step), then commit the stream-B identity manifest
uv run --locked --extra pilot python -m arborlm.p7b_study trace-b --parent-suite <P5_SUITE> \
  --panel-confirmation $A/panel_confirmation.json --layout-confirmation $A/layout_confirmation.json
git add $R/trace-b/<TRACE_B_RUN> && git commit -m "P7-B stream-B identity manifest"   # before any simulation
git ls-files --error-unmatch $R/trace-b/<TRACE_B_RUN>/stream_b_identity_manifest.json \
  && git diff --quiet HEAD -- $R/trace-b/<TRACE_B_RUN>/stream_b_identity_manifest.json

# 4. simulate both streams back to back, no inspection in between
uv run --locked --extra pilot python -m arborlm.p7b_study simulate --stream A --layout-confirmation $A/layout_confirmation.json
uv run --locked --extra pilot python -m arborlm.p7b_study simulate --stream B --layout-confirmation $A/layout_confirmation.json

# 5. independent re-simulation of both streams (18 registered checkpoints)
.venv/bin/python -I $T/independent_resim.py --repo . --stream A --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --simulate-dir $R/simulate-a/<SIM_A_RUN> \
  --out $A/resim_confirmation_A.json --detail $A/resim_detail_A.json > $A/resim_A.log 2>&1
.venv/bin/python -I $T/independent_resim.py --repo . --stream B --jobs 1 \
  --hash-table $R/layouts/<LAYOUT_RUN>/layout_hash_table.json --simulate-dir $R/simulate-b/<SIM_B_RUN> \
  --trace-b-compact $R/trace-b/<TRACE_B_RUN> --trace-b-dir experiments/<TRACE_B_RUN>/traces \
  --out $A/resim_confirmation_B.json --detail $A/resim_detail_B.json > $A/resim_B.log 2>&1

# 6. analysis, once
uv run --locked --extra pilot python -m arborlm.p7b_study analyze \
  --resim-confirmation-a $A/resim_confirmation_A.json --resim-confirmation-b $A/resim_confirmation_B.json
```

Any `DISAGREE` (exit code 2) stops the study at that point (ADR §11). If m12 is decided as "panel before the freeze", step 1 runs on the final sources just before the freeze commit, with nothing else changed.

## Not checked

The real validation parquet path of both panel reconstructions; real trace-b (model loading, replay, regeneration); the real P7-A reproduction on stream A; the clerk's inventory of prior rank usage (not repeated); RSS under the watchdog on real data; the descriptive tables beyond spot checks (calibration transfer, split-half, pages-and-misses, quality beside misses, popularity cost) — their arithmetic was read, not recomputed; the windowed and greedy-only layouts at R ∈ {1, 32, 128} and all layouts at R = 1, 32, 128 beyond the implementer's tests.

## Verdict

**NOT READY TO FREEZE as submitted**, for one reason: **M1**. Conditions for READY TO FREEZE:

1. M1 fixed in code with a test (manifest tracked-and-clean check and hash binding in `simulate`), followed by a narrow re-check by the auditor role; **or** a recorded decision by the lead to enforce the commit procedurally, with the Git check in step 3 above and my stream-B re-simulation's manifest comparison as the evidence.
2. m12 decided and written into the freeze record (panel before or after the freeze).
3. Recommended before the freeze, not conditions: m1 (bind gates to tool hashes), m2 (run-time R = 1 check), m3 (wider source binding), m7 (measured trace-b timing). Any source change requires re-running the test suite, the dry run and my layout check on calibration.

No blocker was found: on everything I could run without an evaluation trace, the implementation agrees with independent code written from the ADR text.
