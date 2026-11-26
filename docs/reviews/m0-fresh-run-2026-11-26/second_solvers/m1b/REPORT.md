# Report: second solvers m1b (EVAL M1), ADR-0033 addendum 1 section 8 item 1

Model: Claude Opus 5.5 (claude-opus-5-5), running as an arbor-auditor context. This is independent engineering evidence only. Astra review: NOT_PERFORMED. Not human approval. No result here is called a success; the comparison with the builder's keys is done later by another context.

## What I read
- The brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md` (only that file in the briefs directory).
- `experiments/_scratch/m0_second_solver_fixtures_20261126/README.md`.
- For the ten assigned lineages only: `M1/<lineage>/SCHEMA.md` and `M1/<lineage>/fixtures.jsonl`.
- My own files in this directory.
The restriction held: I did not read, list or grep the repository, any worktree, AGENTS.md, CLAUDE.md, docs, git history, the keys tree, the fixture builder's directory, other `m0_fr_*` directories, or other lineages' fixtures. Notes: (a) the session's system context showed CLAUDE.md content and a git status snapshot automatically before I started (not read by me with a tool; nothing in it concerns these lineages' generators, keys or solvers); (b) the fixtures README I was allowed to read lists sha256 sums and names of all 82 lineages' files and names builder modules and file paths (e.g. `studies/m0/...`, the keys tree path); I did not open any of them.

## Deliverables
- `solver2_m1b.py`: `SOLVERS` for the ten lineages; all computed from `structured`.
- `run_solver2.py` -> `answers_m1b.jsonl` (2800 lines) and `run_solver2.out`.
- `check_text.py` / `check_text.out`: text re-parse vs `structured`, 0 mismatches.
- `check_extra.py` / `check_extra.out`: grid enclosed-gap count (67) and percent intermediate-cent check (0).
- `templates.py`: template enumeration (output summarised in NOTES.md).
- `NOTES.md`, `AMBIGUITIES.md` (0 genuine ambiguities; 4 considered items), `SHA256SUMS.txt`.

## Commands (cwd = this directory; system Python 3.15.1, standard library only)
```
timeout 60  python3 -I -B templates.py gcd_lcm_r4 grid_perimeter_r3 inclusion_exclusion_r3 last_digit_power_r3 linear_equation_r3 median_list_r3 mixture_r4 painted_cube_r3 percent_change_r3 pipes_work_r3
timeout 120 python3 -I -B run_solver2.py      # 280 answered x 10, bad 0, inexact 0
timeout 120 python3 -I -B check_text.py       # 0 flags in every lineage
timeout 120 python3 -I -B check_extra.py      # 67 grid items with enclosed empty cell; 0 percent items with sub-cent intermediates
```

## Result
All ten lineages solved; nothing unsolved; 0 exceptions, 0 malformed answers. 31 hand-checked items (3-4 per lineage, levels 0-6) agree with the solver.

## Own errata
- AMBIGUITIES.md item 1 contains the parenthetical "(all such gaps are bounded only by squares meeting at corners or by sides)", which is vacuous; the measured fact is only "empty cell not 4-connected through empty cells to the outside of the bounding box". Left in place (no file edits after writing, per the brief's keep-files rule).
