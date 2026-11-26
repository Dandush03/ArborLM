# Lead decision 1 on P10-I-S2-D0: report-step defect (2026-11-25)

Lead decision, not human approval. Astra review: NOT_PERFORMED. Made by arbor-lead (Fable 5.2) under ADR-0035 section 8.2/8.3 ("anything else goes to the lead"), relayed by the coordinator. Recorded in substance, not verbatim.

## Facts

- The run launched at commit `e74cbf25` finished all 96 counted passes (worker exit codes [0, 0, 0], 02:18 EST on 2026-11-25) and then crashed in the report step. The driver process (pid 88694) is gone.
- The output directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2D0-run-20261124` holds passes/ (96 files), stats/ (6), gate_passes/, gates/ and cost/ ledgers; it has no report.txt, no run_complete.json and no records/.
- Cause: in `finalize.render` the statistics loop skipped only the keys `rep` and `order`, but each `stats/S__r__o.json` also carries the top-level scalar keys `id`, `label`, `oracle_line`, `pid`, `task_seconds` and `worker`; `v['panel']` was then taken on a string.
- The coordinator opened one stats file only to print key names, types and those scalar values. No read statistic and no pass record was looked at by anyone before the report was written by code.

## Traceback tail (from launch.log, kept; launch.log is not altered)

```
/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124/.venv/lib/python3.12/site-packages/torch/_subclasses/functional_tensor.py:279: UserWarning: Failed to initialize NumPy: No module named 'numpy' (Triggered internally at /Users/runner/work/pytorch/pytorch/pytorch/torch/csrc/utils/tensor_numpy.cpp:81.)
  cpu = _conversion_method_template(device=torch.device("cpu"))
[00:17:00] stage gate: worker exit codes [0, 0, 0]
[02:18:06] stage main: worker exit codes [0, 0, 0]
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124/studies/p10is2d0/driver.py", line 233, in <module>
    sys.exit(main())
  File "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124/studies/p10is2d0/driver.py", line 226, in main
    return run_command(a)
  File "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124/studies/p10is2d0/driver.py", line 194, in run_command
    text = finalize.render(rec, gate_record, stats_by_cell, cost, commit, "COMPLETE")
  File "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124/studies/p10is2d0/finalize.py", line 129, in render
    lines.append(f"{key} {sk} panel={v['panel']} protected_stage={v['protected_stage']} reads={v['reads']} marker_reads={v['marker_reads']} gates={v['gates']}")
                                     ~^^^^^^^^^
TypeError: string indices must be integers, not 'str'
```

## Decision

1. The failure is in report rendering after the last pass. No read, decode, score, gate or statistic code is at fault. The failed attempt is kept: nothing in the output directory is deleted, moved or overwritten.
2. The fix is limited to the statistics loop of `finalize.render`: skip top-level entries that are not per-store mappings (iterate only entries whose value is a dict with `panel`). A test feeds `render` a stats mapping with the real file's scalar keys: it failed before the fix (`TypeError: string indices must be integers, not 'str'`, finalize.py:129) and passes after (`tests/test_p10is2d0_finalize_fix.py`).
3. `driver.py` is not edited and its same-commit check on resume is not weakened. A new entry point, `studies/p10is2d0/finalize_only.py` (with tests), refuses unless the run directory is in the post-pass state (launch.json present; run_complete.json and report.txt absent; exactly 96 pass, 24 gate-pass and 6 statistics records plus the gate files), the tree is clean, and the only code that differs from the launch commit is `finalize.py` and `finalize_only.py` under `studies/p10is2d0` (plus `tests/` and `docs/`). It records the changed files and both commits, writes the SHA-256 of every pass, statistics and gate record before reading any of them, appends to `resumes.json` with the cause, and then performs the driver's post-pass steps by calling finalize/run/passes. The report header and run_complete.json carry the launch commit, the finalize commit and the words "report step re-run after a rendering defect; lead decision 1".
4. This is D0's single run: all counted passes were computed once, by the launch commit, and no counterfactual score was seen before the fix.
