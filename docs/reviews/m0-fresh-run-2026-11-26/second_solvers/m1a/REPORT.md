# REPORT: second solvers m1a (EVAL M1)

Model I ran as: Claude Opus 5.5 (model id claude-opus-5-5), in an arbor-auditor context launched by another agent. This is independent engineering evidence. It is not Astra validation and not human approval. Astra review: NOT_PERFORMED.

Lineages (10): M1.ages_r3, M1.arithmetic_series_r3, M1.average_missing_r4, M1.change_ways_r3, M1.clock_duration_r4, M1.consecutive_r3, M1.crt_congruence_r3, M1.division_counting_r3, M1.finite_differences_r4, M1.fraction_remainder_r3.

## What I read
- The brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md` (only that file in the briefs directory).
- `m0_second_solver_fixtures_20261126/README.md`.
- For the 10 lineages above only: `M1/<lineage>/SCHEMA.md` and `M1/<lineage>/fixtures.jsonl`.
- One `ls` of each of my 10 lineage directories, which showed only `SCHEMA.md` and `fixtures.jsonl`.
- Files I wrote in this directory.
The restriction held. I did not open the repository, AGENTS.md, CLAUDE.md, any other briefs file, the keys tree, the fixtures_impl tree, other `m0_fr_*` directories or other lineages' fixtures.
Exposure through permitted files: the fixtures README lists file names, sha256 values of all 82 lineages' files, builder module and function names (for example `studies.m0.lineages_m1_fix4.load_registered()`, `studies.m0.core.draw_items`), the path of the keys tree, and a description of the C1 builder. It contains no generator code, keys or solver code. The CLAUDE.md and memory index that the harness injected into my context at start-up (project instructions, not fixture content) contained no generator, key or solver content.

## Results (no keys compared; nothing here is a success claim)
- 2800 answers (280 per lineage), 0 exceptions, 0 format failures, 0 text/structured disagreements.
- Ambiguities listed: 0 (see AMBIGUITIES.md).
- Unsolved: none.
- Source per lineage: structured only for arithmetic_series, change_ways, clock_duration, consecutive, crt_congruence, division_counting, finite_differences and fraction_remainder (the text was parsed only for cross-checking). Both structured and text for ages_r3 (which person is asked, matched against `ask`) and average_missing_r4 (the maximum mark, used for the range check).
- Own mistake: edgecheck attempt 1 keyed answers by lineage-level `id` (see NOTES.md). Its output is kept as `edgecheck_attempt1_WRONG_KEY.out`; corrected in `edgecheck2.py`.

Environment: system python3 3.15.1 on darwin, `python3 -I -B`, standard library only. The fixture sha256 values I computed for my 10 lineages match the README.
