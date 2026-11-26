# Report: R1 second solvers (NAME = r1, EVAL = R1)

- Ran as: Claude Opus 5.5 (model id claude-opus-5-5), arbor-auditor context, 2026-11-26.
- Astra review: NOT_PERFORMED. This is not Astra validation and not human approval. No result here is a success claim; the answers have not been compared with any key.
- Lineages (10): R1.boolean_lights_r4, R1.categories_default_exceptions_r4, R1.compass_turns, R1.conditional_threshold_rule_r4, R1.equivalence_exchange_rates_r6, R1.knights_knaves_r6, R1.spatial_grid_walk_r5, R1.swap_tracking_r5, R1.temporal_weekday_shift_r6, R1.venn_counting_r5. 280 items each, 2800 answers in `answers_r1.jsonl`, none null, all in the SCHEMA format.
- Environment: system `python3` 3.15.1, invoked as `python3 -I -B <script>`, standard library only, no `uv`, no network, no writes outside this directory.

## What I read (restriction)
- The brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md` (only that file in that directory).
- In `experiments/_scratch/m0_second_solver_fixtures_20261126/`: `README.md`, and for my ten lineages only `R1/<lineage>/SCHEMA.md` and `R1/<lineage>/fixtures.jsonl`.
- My own directory.
- Nothing else concerning the project: not the repository, any worktree, AGENTS.md/CLAUDE.md files on disk, git history, other `_scratch` directories, the keys tree, the fixtures-implementation tree, or other lineages' fixtures.
- Seen incidentally, by reading the permitted README.md: it names the keys tree path and its self-check script file names, the build script path, the builder module names in `studies/m0`, the list of all 82 lineage ids with sha256 of their fixture/schema files, and a description of how C1 items are executed. I opened none of those paths. Creating my directory with `ls -la` showed only the (empty) new directory and the parent's entry count. The CLAUDE.md content and a project memory index were injected into my context by the harness at session start (I did not open them); they contain no generator, solver or key content for these lineages.

## Results
- Every lineage solved from `structured`; independently, every question text was parsed into my own form, which equals `structured` on all 2800 items and gives the same answers (`textcheck_v2.out`).
- Ambiguities: 0 items judged genuinely ambiguous; 4 rejected alternative readings documented in `AMBIGUITIES.md` (notably venn inclusive vs exclusive pair counts, which changes all 200 items of levels 2-6).
- Unsolved items: none.
- Failed attempts kept: `textcheck.py` (sentence splitter bug: exchange-rate lineage all PARSEFAIL), `handcheck.py` + `handcheck.out` (2 differences caused by my own mislabelling of two categories items; corrected in v2, 40 hand-checked items, 0 differences).

## Files
`solver2_r1.py`, `run_solver2.py`, `answers_r1.jsonl`, `textcheck.py`, `textcheck_v2.py`, `textcheck_v2.out`, `diagnostics.py`, `diagnostics.out`, `handcheck.py`, `handcheck.out`, `handcheck_v2.py`, `handcheck_v2.out`, `peek.py`, `templates.py` (exploration helpers), `NOTES.md`, `AMBIGUITIES.md`, `REPORT.md`, `SHA256SUMS.txt`.
