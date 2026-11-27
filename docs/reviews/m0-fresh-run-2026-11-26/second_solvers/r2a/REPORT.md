# REPORT: second solvers r2a (EVAL R2)

Model: Claude Opus 5.5 (claude-opus-5-5), run as an `arbor-auditor` context, 2026-11-26.
Astra review: NOT_PERFORMED. This is not Astra validation and not human approval. No result here is called a success; the answers have not been compared with any key.

## Lineages (9)
R2.binary_search_trace, R2.caesar_shift, R2.cellular_automaton, R2.cheapest_network, R2.count_divisible, R2.crt_smallest, R2.dictionary_rank, R2.expression_eval, R2.from_base. 280 items each, 2520 answers in `answers_r2a.jsonl`; every answer well formed (format regex from SCHEMA.md), no exceptions. All solvers compute from `structured`; the question text was parsed independently for every item and agrees with `structured` and gives the same answer (attempt 2: 0 mismatches). Could not solve: none.
Ambiguities: 0 genuine; 4 edge cases listed in `AMBIGUITIES.md`.
Attempt 1 of the runner flagged 280 checker false alarms (town order in R2.cheapest_network); kept as `run_solver2.out`; attempt 2 is `run_solver2_v2.out`. Details in `NOTES.md`.

## What I read (restriction)
- The brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md` (only that file in that directory).
- `experiments/_scratch/m0_second_solver_fixtures_20261126/README.md`, and for the 9 lineages above `R2/<lineage>/SCHEMA.md` and `R2/<lineage>/fixtures.jsonl`. The `ls` of each of those 9 lineage directories (showing only `SCHEMA.md`, `fixtures.jsonl`).
- Nothing else of the project: not the repository/worktree, not the keys tree, not the fixtures-impl tree, not any `m0_fr_*` other than the brief, not other lineages' fixtures. The README itself names those other paths (keys tree, build script, self-check files) and lists sha256 sums of all 82 lineages' fixture files and some C1 facts; I saw those names and hashes as part of the README only and opened none of them.
- Not read by me but present in my context: the session harness automatically injected the worktree's CLAUDE.md text and the user's memory index (pointer list) at start, and a git status line (branch, recent commit subjects). None concerns these lineages' generator, keys or first solver. Reported for completeness.
- `ls -d` of my own new output directory before creating it (did not exist).

## Commands (all from shell, absolute paths, `python3` = /opt/homebrew/bin/python3, Python 3.15.1, `-I -B`, under `timeout`)
- `python3 -I -B peek.py <lineage> <levels> <n>`: print example items.
- `python3 -I -B templates.py R2.<lineage>` -> `templates.out`.
- `python3 -I -B run_solver2.py` -> `run_solver2.out`, `answers_r2a.jsonl` (attempt 1).
- `python3 -I -B run_solver2_v2.py` -> `run_solver2_v2.out`, `answers_r2a_v2.jsonl` (attempt 2; byte-identical answers, `cmp`).
- `python3 -I -B props.py` -> `props.out` (item properties: ties, absent targets, base counts, etc.).
- `shasum -a 256` -> `SHA256SUMS.txt`.
No `rm`/`mv`/`chmod` or deletions; no writes outside this directory; no network.
