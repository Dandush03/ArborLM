# P5 visual-analysis package

Visualisation of the completed, immutable P5 study (ADR-0010) from the committed compact records only
(`results/p5-2026-11-13/<cell>/result.json`, 117 quality cells; `.../timing/<worker>/result.json`, 36 workers).
Every number is derived independently from raw per-cell / per-worker JSON: no `arborlm` import, no audit
scripts, no checkpoints, no model run. These figures are an implementer self-check and visualisation aid. They are
**not** independent review, **not** Astra validation and **not** human approval; no scientific claim is added.

All 27 cells share 9 parents, 3 seeds and one validation panel: they are correlated paired observations, not
independent replicates. Accordingly there are no p-values, significance marks, brackets or error bars.

## Reproduction

Run from the repository root (the `--with` overlay does not touch `uv.lock`; `git status` was checked afterwards):

```sh
uv run --locked --extra pilot --with matplotlib==3.10.8 \
    python docs/reviews/p5-claude-review-2026-11-13/figures/make_figures.py
```

Versions used: Python 3.12.14, matplotlib 3.10.8, numpy 2.5.4
(macOS-27.2.1-arm64-arm-64bit). Inputs: 153 files, per-file sha256 in `inputs.sha256`; sha256 over the sorted
per-file hash lines = `9d5ea75d170c33c95697d5eda634edeee40b23c2fcce58e8abb45e3582a12a20`. PNG metadata carries no timestamp/software tag; byte stability across reruns
on this machine/version is checked (see report) but is not promised across platforms or font/library versions.
Output PNG sha256 values are recorded in `figure_data.json` (`output_png_sha256`).

## Quantities and their status

* **MEASURED**: NLL values (nats per byte, fresh P5 panel), value-shuffle NLL, slot/branch counts from the
  study's retrieval recorder, `median_ns` timings (CPU, one thread, no KV cache, full fixed-context forward).
* **ANALYTICAL**: score-work ratio 528/4096 = 0.12890625 (key plus router dot products per query). It is a count,
  **not** a speedup, latency, FLOP, memory-traffic or SSD figure.
* **DERIVED**: G = Z - X (Z = frozen-baseline NLL of the same parent), P = shuffled - X, R = fixed - learned,
  latency ratio = median_ns(hierarchy)/median_ns(flat) on the same worker, scope and batch, geometric means.

## Figures

| File | Shows | Units / axes |
|---|---|---|
| `fig1_nll_by_architecture.png` | Final NLL of baseline (9), flat, fixed, learned, dense (27 each); marker shape = parent backbone B; diamond = mean | nats per byte, lower is better |
| `fig2_router_contrast.png` | R = NLL(fixed) - NLL(learned) for 27 paired cells by B, O, seed; registered +0.005 line and zero line; mean and positive counts annotated | nats per byte |
| `fig3_memory_dependence.png` | G (all 4 variants, dense for reference) and P (3 memories) for all cells; registered 0.005 line | nats per byte |
| `fig4_work_vs_latency.png` | ANALYTICAL 528/4096 line beside MEASURED latency ratios hierarchy/flat per scope and workload (batch 8 primary, batch 1 secondary), log axis, ceilings 0.80 / 1.05 on primary row only; `usable=false` records drawn as X | dimensionless ratio |
| `fig5_slot_utilization.png` | Unique selected slots, effective selected slots exp(entropy), nonzero top-1 branches (trees) at initial vs final; lines join each cell | counts (slots of 4096, branches of 16) |
| `fig6_parent_dispersion.png` | Per parent: three seed values and mean of (final NLL - parent baseline NLL) = -G, per architecture | nats per byte, negative is better |
| `fig7_absolute_latency.png` | Every worker's median latency by variant, scope, workload | microseconds per call |

`figure_data.json` holds every plotted number (per-cell table, per-pair ratios, all 36x22-record medians
with `usable` flags), the aggregates and the comparison below. Timing records with `usable=false`:
4 of 612 (marked, never dropped).

## Independently computed aggregates versus published values

**No mismatches** at the precision of the published values.  "Matches" means the difference is within half a unit of the published last digit.

| Quantity | Computed (this package) | Published | Absolute difference | Match |
|---|---:|---:|---:|---|
| `mean_final_nll.baseline` | 2.356630572 | 2.356630572 | 3.995e-10 | yes |
| `mean_final_nll.flat` | 2.333691890 | 2.33369189 | 4.103e-11 | yes |
| `mean_final_nll.fixed_tree` | 2.334497243 | 2.334497243 | 2.800e-11 | yes |
| `mean_final_nll.learned_tree` | 2.335080704 | 2.335080704 | 2.034e-10 | yes |
| `mean_final_nll.dense` | 2.329312946 | 2.329312946 | 3.715e-10 | yes |
| `mean_R_fixed_minus_learned` | -0.000583461 | -0.000583461 | 1.754e-10 | yes |
| `R_positive_cells` | 10.000000000 | 10 | 0.000e+00 | yes |
| `R_positive_parent_means` | 3.000000000 | 3 | 0.000e+00 | yes |
| `primary_geomean_ratio.addition_forward.fixed_tree` | 2.603052230 | 2.603052 | 2.297e-07 | yes |
| `primary_geomean_ratio.addition_forward.learned_tree` | 2.598485033 | 2.598485 | 3.267e-08 | yes |
| `primary_geomean_ratio.model_forward.fixed_tree` | 2.190282148 | 2.190282 | 1.477e-07 | yes |
| `primary_geomean_ratio.model_forward.learned_tree` | 2.184085943 | 2.184086 | 5.684e-08 | yes |
| `mean_final_unique_selected_slots.flat` | 428.592592593 | 428.59 | 2.593e-03 | yes |
| `mean_final_unique_selected_slots.fixed_tree` | 383.407407407 | 383.41 | 2.593e-03 | yes |
| `mean_final_unique_selected_slots.learned_tree` | 313.111111111 | 313.11 | 1.111e-03 | yes |
| `mean_final_effective_selected_slots.flat` | 132.342784257 | 132.34 | 2.784e-03 | yes |
| `mean_final_effective_selected_slots.fixed_tree` | 96.248136221 | 96.25 | 1.864e-03 | yes |
| `mean_final_effective_selected_slots.learned_tree` | 83.024280933 | 83.02 | 4.281e-03 | yes |
| `mean_gain_G.flat` | 0.022938682 | 0.022938682 | 4.406e-10 | yes |
| `mean_gain_G.fixed_tree` | 0.022133329 | 0.022133329 | 4.275e-10 | yes |
| `mean_gain_G.learned_tree` | 0.021549867 | 0.021549867 | 3.971e-10 | yes |
| `mean_gain_G.dense` | 0.027317625 | 0.027317625 | 2.290e-10 | yes |
| `mean_shuffle_penalty_P.flat` | 0.022679532 | 0.022679532 | 2.602e-10 | yes |
| `mean_shuffle_penalty_P.fixed_tree` | 0.021944248 | 0.021944248 | 2.900e-10 | yes |
| `mean_shuffle_penalty_P.learned_tree` | 0.021603653 | 0.021603653 | 4.135e-10 | yes |
| `mean_T_minus_flat.fixed_tree` | 0.000805353 | 0.000805353 | 1.304e-11 | yes |
| `mean_T_minus_flat.learned_tree` | 0.001388814 | 0.001388814 | 1.623e-10 | yes |

## PENDING LEAD REVIEW (ambiguities; not decided silently)

1. **Shuffle definition for P.** Memory cells carry both `values_permuted` and `joint_within_branch`
   interventions. P uses `values_permuted` (value-only shuffle, ADR-0010 sections 5/8: "value-only shuffle changes
   only values"). The published README penalty means match this choice (see table); `joint_within_branch` was not used.
2. **Z.** Taken from each parent's baseline cell `final.nll`; each memory cell's `disabled` NLL was asserted equal to
   it (within 1e-12) while loading.
3. **Latency ratio basis.** Uses each record's `median_ns` (as specified in the brief and ADR section 8). The
   `usable` flag is plotted/marked but is not used to exclude any ratio from the geometric means (ADR counts all 27
   pairs; a ratio is marked when either record is unusable).
4. **Fig 4 analytical line in non-lookup scopes.** The brief asks for the 528/4096 line beside the measured ratios for
   every scope. It is only a score-work count for key/router dot products; it is drawn in every panel but is not a
   prediction of addition/model-forward latency. Reviewer may prefer to restrict it to `lookup_score_select`.
5. **Cell naming.** The brief writes `s50x`; the directories are `s501`, `s502`, `s503`.
6. **`usable=false` records.** Four records are false (flat lookup_score_select b8 [B101,O302,s502]; fixed_tree
   lookup_score_select b8 [B102,O301,s501]; fixed_tree model_forward b1 [B102,O302,s503]; fixed_tree
   lookup_score_select b1 [B102,O303,s503]). Three are in the explanatory lookup scope or secondary workload; none is in the
   primary addition_forward/model_forward decision scopes. They are shown, not dropped (full list: `figure_data.json`).
7. **Fig 5 slot counts** are per-cell values over the whole validation panel from the study's own recorder; they were
   not recomputed from `selected_slot_counts` here (rerunning the entropy from the raw histogram is possible but was
   outside the brief).
