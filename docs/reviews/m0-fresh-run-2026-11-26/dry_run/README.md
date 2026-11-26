# The dry run of stage 1S point 10 (coordinating lead, 2026-11-26)

- Command: `uv run --locked python studies/m0/fresh_run/run_fresh.py --plan studies/m0/fresh_run/run_plan.json --expect-plan-sha256 316f1026…f389 --seed-set dry --jobs 4`, from the worktree root, at commit `0497f36e`. Dry-run seeds of point 4, 20 items per level. All eleven units ended with exit status 0 on the first attempt (`dry_runner.out.txt`); wall time 28 s. The hashes of every output file are in `hashes_dry.json`, taken by the runner without opening the files.
- The outputs were then passed through the pooling script in dry mode (`pool_fresh.py … --seed-set dry`): exit status 0, nothing on standard error. Its output files were written to scratch (`experiments/_scratch/m0_fr_dryrun_lead_20261126/pool_dry_out/`) and were opened by nobody; no dry figure was read, reported or used.
- Lead ruling R-59: unit R1c was also run once on the dry-run seeds at the plan's item count (3,000), output to scratch and opened by nobody; exit status 0; the pooling script in dry mode with that directory in place of R1c's: exit status 0.
- **Exclusions: none.** No unit failed, so `dry_run_exclusions` in the run plan stays empty and the plan is unchanged (SHA-256 `316f1026…f389`).
- Known from the implementers' smoke executions and the copy auditor's reading (not looked up again here): the a3 wrapper's alias run fails for `C1.while_counter_f3` inside `a3_shortcuts.py` and the wrapper falls back to the lineage's own id; that is the script's committed behaviour, excludes nothing, and each such fallback is listed in the run's report.

Astra review: NOT_PERFORMED
