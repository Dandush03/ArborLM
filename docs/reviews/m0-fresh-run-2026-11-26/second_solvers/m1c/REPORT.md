# Report, second solvers NAME = m1c (EVAL = M1)

Model: Claude Opus 5.5 (`claude-opus-5-5`), run as an `arbor-auditor` context. Astra review: NOT_PERFORMED. This is not Astra validation and not human approval.

Lineages: M1.prime_factors_r3, M1.quadratic_area_r3, M1.ratio_share_r3, M1.rectangle_r3, M1.recurrence_iterate_r3, M1.shopping_r3, M1.speed_distance_r3, M1.tiered_pricing, M1.tip_split_r3. All 9 x 280 = 2520 items return a well-formed answer; 0 exceptions; 0 text/structured mismatches; 0 ambiguities.

## What I read
- The brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md` (only that file in the briefs directory).
- In the fixtures tree: `README.md`, and for each of the 9 lineages `SCHEMA.md` and `fixtures.jsonl`. My first command printed `README.md` and the 9 SCHEMA files; README contains a sha256 list naming every lineage's fixture/schema files across R1/R2/M1/C1, the names (not contents) of the keys tree and builder modules, and a short description of C1 items. I did not open any other lineage's files, the keys tree, the implementation tree, or the repository.
- One `ls experiments/_scratch/ | grep m0_solver2` to check my output directory name was free; it showed the names `m0_solver2_r1_20261126` and `m0_solver2_r2a_20261126` (other solver directories). I did not open them.
- Nothing from the repository, worktree, git history, AGENTS.md or CLAUDE.md was opened by me in this task (the harness injected CLAUDE.md text into my context at start-up; it contains project process notes, nothing about these lineages' generators or keys).

## Files
`solver2_m1c.py`, `run_solver2.py`, `run_solver2.out`, `answers_m1c.jsonl`, `NOTES.md`, `AMBIGUITIES.md`, `REPORT.md`, `work/templates.py`, `work/templates2.py`, `work/handcheck_items.out`, `SHA256SUMS.txt`.

## Commands
`python3 -I -B run_solver2.py > run_solver2.out 2>&1` in this directory; macOS system Python 3.15.1; no network, no uv.
