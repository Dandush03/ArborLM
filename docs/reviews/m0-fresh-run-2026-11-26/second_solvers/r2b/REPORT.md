# REPORT: second solvers r2b (EVAL R2)

Task: brief `experiments/_scratch/m0_fr_briefs_20261126/SOLVER2.md`, NAME = r2b, EVAL = R2, lineages R2.grid_sum, R2.list_ops, R2.luhn_check, R2.min_heap_ops, R2.run_length, R2.sort_list, R2.string_rewrite_nonidentity, R2.to_base_wide.
Model I ran as: Claude Opus 5.5 (model id claude-opus-5-5), arbor-auditor context, 2026-11-26.
Astra review: NOT_PERFORMED. This is not Astra validation and not human approval. Nothing here is a success claim; no answers have been compared with any key.

## What I read
- The brief SOLVER2.md (only file of the briefs directory).
- Fixtures tree: `README.md`, and for each of my 8 lineages `R2/<lineage>/SCHEMA.md` and `fixtures.jsonl`. Nothing else in the fixtures tree.
- My own directory.
Restriction held: I did not read, list or grep the repository, any worktree, AGENTS.md/CLAUDE.md, the keys tree, the fixtures-impl tree, any other m0_fr_* or briefs file, or other lineages' fixtures. One disclosure: the fixtures `README.md` itself (allowed) names paths of the keys tree, the build script and selfcheck scripts, the builder module names, and lists sha256 lines of all 82 lineages' files; I saw those names and hashes only as README text and opened none of them. The session's system context (not chosen by me) also showed the CLAUDE.md of the worktree and git status lines; no generator, solver or key content was in it.

## Results (no keys; self-checks only)
- `run_solver2.py` over 2240 items (8 x 280): 0 exceptions, 0 format failures against SCHEMA.md, 0 mismatches between text-parsed inputs and `structured`. Output `answers_r2b.jsonl` (2240 lines), log `run_solver2.out`.
- Hand checks: 3-4 items per lineage at levels 0, 1, 3, 6 (NOTES.md); all equal the code after one hand error of mine on string_rewrite L3#0, recorded in NOTES.md.
- Ambiguities: 0 item-level (AMBIGUITIES.md lists 4 considered points).
- Source used per lineage: `structured` for computation in all 8; question text parsed independently as a cross-check in all 8.

## Files
solver2_r2b.py, run_solver2.py, run_solver2.out, answers_r2b.jsonl, templates_r2b.py, templates_r2b.out, probe_r2b.py, probe_r2b.out, NOTES.md, AMBIGUITIES.md, REPORT.md, SHA256SUMS.txt.
