# P10-I-S2-D0 implementation notes (implementer: Claude Sonnet 5.5, `claude-sonnet-5-5`)

Self-check only. Not independent review, not Astra validation, not human approval. Nothing here is a result.

## Failing-first evidence (ADR-0035 section 8.1: tests before any real snapshot is opened)

The three test files `tests/test_p10is2d0_reads.py`, `tests/test_p10is2d0_gates_stats.py` and `tests/test_p10is2d0_report.py` were written before `studies/p10is2d0/` existed. Each test imports the module it needs inside
its first line (`_m("...")`), so that each failed at its own line. Command and output (kept in the git-ignored scratch file `experiments/_scratch/p10is2d0_impl_20261124/failing_first.txt`):

    uv run --locked --offline pytest tests/test_p10is2d0_*.py --tb=short -q -p no:cacheprovider   ->   36 failed

Every one of the 36 failed with `ModuleNotFoundError: No module named 'studies.p10is2d0'` at the line shown (line numbers are those of the files as first written; the files were edited afterwards in five places: two
wrong expectations in the report tests (a float-exact `approx(abs=0)`, a borderline `0.02` against `T / 3`, a "five of six" case with five defined cells), the key list of the identity gates (the sum identity is checked
at the append point as well), `summarise`'s dictionary and an unused variable).

| Test | Failing line (before the code existed) | Source line |
|---|---|---|
| `test_every_gate_identity_passes_on_an_honest_append_pair` | `tests/test_p10is2d0_gates_stats.py:45` | `gates = _m("gates")` |
| `test_a_moved_stage_one_key_fails_the_frozen_gate_and_the_b1_gate` | `tests/test_p10is2d0_gates_stats.py:55` | `gates = _m("gates")` |
| `test_a_nonzero_append_gate_fails_g2` | `tests/test_p10is2d0_gates_stats.py:66` | `gates = _m("gates")` |
| `test_the_sum_identity_uses_the_stated_tolerance` | `tests/test_p10is2d0_gates_stats.py:76` | `gates = _m("gates")` |
| `test_compare_with_registered_demands_exact_scores_and_identical_sequences` | `tests/test_p10is2d0_gates_stats.py:84` | `gates = _m("gates")` |
| `test_read_statistics_on_a_hand_built_store` | `tests/test_p10is2d0_gates_stats.py:98` | `stats = _m("stats")` |
| `test_read_statistics_mark_an_undefined_ratio_not_a_number` | `tests/test_p10is2d0_gates_stats.py:132` | `stats = _m("stats")` |
| `test_fs_manifest_sees_an_added_file_and_a_changed_byte` | `tests/test_p10is2d0_gates_stats.py:142` | `run = _m("run")` |
| `test_output_directory_inside_the_part_t_run_directory_is_refused` | `tests/test_p10is2d0_gates_stats.py:155` | `run = _m("run")` |
| `test_loading_snapshots_and_reading_writes_nothing_under_the_run_directory` | `tests/test_p10is2d0_gates_stats.py:169` | `run = _m("run")` |
| `test_a_is_bit_identical_to_the_registered_read` | `tests/test_p10is2d0_reads.py:104` | `reads = _m("reads")` |
| `test_a_matches_the_adr_notation` | `tests/test_p10is2d0_reads.py:110` | `reads = _m("reads")` |
| `test_b_is_the_unmodified_read_of_stage_p_alone` | `tests/test_p10is2d0_reads.py:117` | `reads = _m("reads")` |
| `test_b_is_the_unmodified_read_of_stage_p_alone` | `tests/test_p10is2d0_reads.py:117` | `reads = _m("reads")` |
| `test_b1_on_an_append_store_is_the_first_stage_read_bit_for_bit` | `tests/test_p10is2d0_reads.py:125` | `reads = _m("reads")` |
| `test_c_is_b1_plus_b2` | `tests/test_p10is2d0_reads.py:139` | `reads = _m("reads")` |
| `test_d_e_g_match_the_adr_notation` | `tests/test_p10is2d0_reads.py:146` | `reads = _m("reads")` |
| `test_d_e_g_match_the_adr_notation` | `tests/test_p10is2d0_reads.py:146` | `reads = _m("reads")` |
| `test_d_is_the_zero_vector_when_the_protected_stage_has_no_row_among_the_eight` | `tests/test_p10is2d0_reads.py:154` | `reads = _m("reads")` |
| `test_d_renormalises_over_the_protected_rows_and_e_does_not` | `tests/test_p10is2d0_reads.py:172` | `reads = _m("reads")` |
| `test_e_sums_to_a_and_e_of_a_zero_gate_stage_is_the_append_point_a` | `tests/test_p10is2d0_reads.py:185` | `reads = _m("reads")` |
| `test_g_is_b_p_plus_the_other_stage_part_of_a` | `tests/test_p10is2d0_reads.py:194` | `reads = _m("reads")` |
| `test_ties_go_to_the_lowest_row_index_across_stages` | `tests/test_p10is2d0_reads.py:201` | `reads = _m("reads")` |
| `test_condition_reader_covers_every_condition_of_section_4` | `tests/test_p10is2d0_reads.py:219` | `reads = _m("reads")` |
| `test_diag_arm_adds_the_condition_read_at_the_registered_positions` | `tests/test_p10is2d0_reads.py:229` | `reads = _m("reads")` |
| `test_diag_arm_refuses_an_ablation` | `tests/test_p10is2d0_reads.py:248` | `reads = _m("reads")` |
| `test_the_three_terms_telescope_to_t_exactly` | `tests/test_p10is2d0_report.py:19` | `rep = _m("report")` |
| `test_values_first_order_and_the_interaction` | `tests/test_p10is2d0_report.py:28` | `rep = _m("report")` |
| `test_a_residual_against_the_registered_f_is_printed_not_hidden` | `tests/test_p10is2d0_report.py:40` | `rep = _m("report")` |
| `test_the_append_point_decomposition_has_no_values_term` | `tests/test_p10is2d0_report.py:46` | `rep = _m("report")` |
| `test_summary_word_needs_five_of_six_cells` | `tests/test_p10is2d0_report.py:53` | `rep = _m("report")` |
| `test_a_cell_with_no_positive_total_never_counts_toward_a_word` | `tests/test_p10is2d0_report.py:64` | `rep = _m("report")` |
| `test_order_dependent_is_added_on_a_large_interaction_or_differing_words` | `tests/test_p10is2d0_report.py:73` | `rep = _m("report")` |
| `test_counterfactual_ret_arithmetic_uses_the_unchanged_thresholds` | `tests/test_p10is2d0_report.py:86` | `rep = _m("report")` |
| `test_paired_contrast_uses_the_sample_standard_deviation` | `tests/test_p10is2d0_report.py:94` | `rep = _m("report")` |
| `test_every_block_carries_the_oracle_line_and_the_posthoc_line` | `tests/test_p10is2d0_report.py:107` | `rep = _m("report")` |

After the code was written all 36 passed. A mutation check (scratch script `experiments/_scratch/p10is2d0_impl_20261124/mutation_check.py`, run once) replaced `read_d` by `read_e`, `read_g` by `read_b` and `read_e` by
`read_a`: each was caught by two tests.

`tests/test_p10is2d0_pipeline.py` (10 tests: the task list of 96 + 24 passes, the worker body, the ledger and the cap, the report, a tiny synthetic world from Part T's engine fixtures) was written AFTER the code: it is
an integration test, not failing-first. It writes only into pytest temporary directories.

## Readings of the ADR taken without asking (formatting or mechanics, no scientific content)

1. Section 3 names `studies/p10is2/evaluate.py`; the file is `studies/p10s2/evaluate.py` (`score_panel`). Used as it is.
2. Part T's configuration says `deterministic_algorithms = false` (plan platform record); the ADR and the brief say deterministic algorithms. D0 sets `torch.use_deterministic_algorithms(True)` and six threads. If the
   reproduction gate fails, this is the first thing to look at.
3. "Every line D0 prints carries Part T's oracle line and the words ...": implemented as the two lines directly above every report block (as ADR-0025 section 5.4 carries them above every table), and as the fields
   `oracle_line` and `label` in every JSON record. Not as a prefix on every text line.
4. The 24 reproduction passes (M1 on E_first, append and final on E_first, final on E_second, per cell) use the UNMODIFIED registered read (`MemoryArm`). The 96 counted passes are separate computations (the M1 pass is
   again the registered arm; every other pass uses `DiagArm`). So 120 passes are decoded in all (about 24 more than the ADR's 96 counted passes: the gate's cost, which section 10 does not list). Charged to the 8
   worker-hour cap with everything else.
5. Medians and the 5th and 95th percentiles are the 0.5, 0.05 and 0.95 quantiles of `torch.quantile` (linear interpolation), over the finite values; undefined ratios (a zero reference read) are counted, not dropped silently.
6. For each cell the "contrasts" of section 5.3 are: every pass against its reference pass (M1 on E_first; `a` on E_second), and each term of the decomposition (T, (i), (ii), (iii), values first, competition given
   values), each as a paired per-item difference with sd / sqrt(1000), sd with n - 1.
7. A cell whose T is not positive has no share (undefined) and never counts toward a word; ADR-0035 is silent on that case and Part T's F (0.056 to 0.086) makes it not expected. If it occurs it is printed.
8. The counterfactual RET arithmetic (section 7) is printed beside the second capability's cost under c, as the ADR says, and also beside the cost under g(2) (a pass that is computed anyway).
9. Chunking: a pass is decoded in chunks of 100 items so that the cap is checked inside a pass; chunks are independent items, so the result equals one `score_panel` call over all 1,000 items (tested on a tiny world with a chunk of 5).

## Rulings of the coordinator, 2026-11-24 (recorded here, no scientific change)

- Path correction: ADR-0035 section 3 names `studies/p10is2/evaluate.py`; the file the ADR means is `studies/p10s2/evaluate.py`. Accepted as a path correction.
- Deterministic algorithms stay ON, as the ADR says. If the reproduction gate fails, stop and report; do not switch it off.
- The oracle and post-hoc lines above every report block and in every JSON record are accepted.
- The 24 reproduction passes count against the 8 worker-hour cap.
- Departure from the standing rule: `studies/p10is2d0/launch_d0.sh` was given the exec bit by `chmod +x` during the first implementation session (a breach of the no-chmod rule). The coordinator ruled that the bit stays as it is; no further chmod was run. The file commits with mode 100755. Nothing depends on the bit: `sh studies/p10is2d0/launch_d0.sh` is the launch form.
