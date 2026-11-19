# P10-I-S5 third re-audit: the launcher keep-awake watcher fix, commit c2f316d (2026-11-18)

**Auditor:** `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`). I wrote none of the audited code. Not Astra validation, not a human approval. `Astra review: NOT_PERFORMED`.
**Object:** `git diff 5ad9142 c2f316d` (one commit): `system.py` +49/−4 (`parse_ps_comm`, `launcher_watchers`, `own_family`, `descendants_pairs`, the `record` callback of `take_idle_window` and `idle_baseline`), `core.py` +14 (`append_jsonl`), `r1.py` one line, `testing.py` the fake `ps`, tests +75. Nothing else changed.

## Verdict

**CONFIRMED — READY FOR R1**, with one launch-procedure condition (finding 1): launch the stage as a single command with output **redirected to a file, never piped**, or the same hang returns through a different sibling.

## Environment and commands

Fresh `git archive c2f316d` in `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit-p10is5/code`, `GIT_CEILING_DIRECTORIES=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit-p10is5` (outside any git repository). No stage was run against `ArborLM-ssd.noindex` or `P10IS5-run-20261118`; no SSD probe; no git write; nothing under /tmp.

| Command | Result |
|---|---|
| `timeout 1800 uv run --offline --locked pytest tests/test_p10is5_*.py -q -p no:cacheprovider` (one process) | 253 passed, 1 skipped, 21.0 s |
| `uv run --offline --locked ruff check .` | All checks passed |
| `timeout 120 sh d1_launcher_shape.sh 2>&1 \| grep … \| grep …` (the launch scripts' exact shape, `exec caffeinate -i uv run … python …`, a read-only probe in the stage's place whose command line carries `studies.p10is5`) | see 1 and 2 |
| `timeout 120 sh d1_launcher_shape.sh > out/d1_noredirect_pipe.txt 2>&1` (same, output redirected, no pipe) | see 1 and 2 |

## 1. The rule is no wider than stated; what it hides

`launcher_watchers` adds only pids whose **parent is the stage or one of its ancestors** and whose **executable basename is `caffeinate`**; nothing below them is added (`process_family` walks descendants from the stage only, and the watchers are united afterwards). Operator precedence in `ancestors = fam - {descendants} | {me}` is `(fam − descendants) ∪ {me}`, as intended.

- **Still counted:** any study process of any parent (it is not `caffeinate`); a sibling python; another study launched from the same session through its own launch script — its tool-call zsh is a sibling of the stage's zsh, so its watcher's parent (its own `uv`) is not an ancestor, and its `uv` and python are counted anyway; the children of any hidden caffeinate.
- **Hidden:** only `caffeinate` processes that are direct children of an ancestor. The ancestors reach up to the Claude desktop app (on this machine: python → `uv` → `timeout` → tool `zsh` → `claude` 46727 → `disclaimer` 46726 → `Claude` 44716). So a `caffeinate` started by the Claude app or session for its own keep-awake is hidden — correct, it is not a study. A second study started by **the same shell** as `caffeinate -i <study>` would have its `caffeinate` hidden, but its `uv` and python (children of that caffeinate, not family) are still counted. **Nothing that reads or writes for another study is hidden;** only `caffeinate` itself, which does no I/O.

**Finding 1 (REQUIRED for the runbook, not the code).** The probe launched *inside a pipeline* (`… 2>&1 | grep | grep`) found one process of its own launch still counted: pid 71661, a forked `/bin/zsh -c source …shell-snapshots… && eval '…'` — the tool call's own subshell for the pipe, a **sibling** of the stage (child of the ancestor zsh), whose command line is the whole tool command and so carries `studies/`, `arborlm` and the launch path. The same probe with output redirected and no pipe counted **nothing** of its own launch. A launch such as `timeout N sh studies/p10is5/launch/r1.sh RUN DATA 2>&1 | tail` would therefore fail every idle sample exactly as before. Launch as one command with `> RUN/r1.log 2>&1` (no `|`, no `$( )`, no `&` alongside), in a background tool call, and make no other tool call while it runs. (A code alternative, if the lead prefers: also treat as family a process whose parent is an ancestor and whose command line equals that ancestor's command line, i.e. a forked subshell.)

## 2. The real tree and `ps -o comm` on this machine

The probe under the launch shape printed: `exec` replaces `sh` by `caffeinate`, which forks its **watcher** and execs `uv` in its own pid; so `uv` (71664 / 71826) is an ancestor of the stage and the watcher (71665 / 71827) is a child of `uv`, i.e. a sibling of the python stage: the case the fix targets. `ps -Ao pid,ppid,comm` gave the watcher's comm as the bare name `caffeinate` (other processes show full paths, including paths with spaces such as `…/Application Support/…`; `parse_ps_comm` keeps the rest of the line, so spaces are safe). `comm.rsplit("/", 1)[-1] == "caffeinate"` matches both forms. `own_family` contained the watcher (`watchers in own_family: [71665]` and `[71827]`).

## 3. The incremental record

`core.append_jsonl`: one `os.write` of one line on an `O_APPEND` descriptor, then `fsync`, then close — append-only, survives a kill (at worst a last partial line if killed inside `write`, which a reader can skip). It is written to `RUN/r1/idle_attempts.jsonl` for every sample (`kind: sample`) and every attempt (`kind: attempt`). `grep idle_attempts studies/p10is5/*.py`: written in `r1.py` only, **read nowhere**; it is not in R1's final record, not in the idle figures (computed from the window in memory as before), not among the plan's hashed records (R1 and M records only). Resumption is unchanged: the `idle` step is saved only when measured, so after a kill the window is retaken from the start and new lines are appended (attempt numbers restart at 1; the UTC stamps separate the runs). Size is small: a failing sample ends its attempt, so a 6-hour retry period writes about 36 lines plus up to 60 per successful window.

## 4. Nothing else; the other stages

The diff touches nothing else. Every quiet path goes through `read_other_processes → own_family`: the block gate of M, K and E2 (`read_quiet`), the idle window of R1 (`idle_conditions_hold`) and E1's new other-study check. Launch shapes: `r1.sh`, `m.sh`, `k.sh` and `e2.sh` use `exec caffeinate -i uv run …` (same tree as above, now covered); `r0.sh`, `e1.sh`, `p.sh`, `analysis.sh`, `report.sh` and `delete.sh` use `exec uv run …` (no watcher; `uv` and the shell are ancestors). The E2 and K pass workers are children of the stage (descendants) and are not alive when the gate reads. So M, K, E1, P and E2 cannot hang the same way, **provided finding 1's launch rule is kept for every stage that has a quiet or other-study check (R1, M, K, E1, E2).**

## Scripts, verbatim

### d1_launcher_shape.sh

```sh
#!/bin/sh
# Mirror of the fixed launch scripts' shape (exec caffeinate -i uv run ... python -m ...): a probe in the stage's place prints the real process tree,
# what `ps -o comm` gives for caffeinate, and what the implementation's own_family / read_other_processes make of it. Reads only; writes nothing.
cd /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit-p10is5/code
exec caffeinate -i uv run --offline --locked python ../scripts/d1_probe.py studies.p10is5.auditprobe
```

### d1_probe.py

```python
"""Run in the stage's place under the launch shape. Prints the ancestor chain, the caffeinate processes near it, own_family's verdict, and which marker processes in MY subtree's neighbourhood are counted."""
import os, sys
sys.path.insert(0, os.getcwd())
from studies.p10is5 import system, core
rc, out, _ = system.run_command(["ps", "-Ao", "pid,ppid,comm"])
table = system.parse_ps_comm(out)
pp = {p: q for p, q, _ in table}; comm = {p: c for p, _, c in table}
chain, cur = [], os.getpid()
while cur in pp and cur > 1:
    chain.append((cur, comm.get(cur))); cur = pp[cur]
print("ancestor chain (pid, comm):", chain[:7])
anc = {p for p, _ in chain}
near = [(p, q, c) for p, q, c in table if c.rsplit("/", 1)[-1] == "caffeinate" and (q in anc or p in anc)]
print("caffeinate processes with an ancestor as parent, or in the chain:", near)
fam = system.own_family(system.run_command)
print("watchers in own_family:", sorted(p for p, q, c in near if p in fam and p not in anc))
others = system.read_other_processes(system.run_command, core.load_config()["quiet"]["process_markers"])
mine = [(p, c[:90]) for p, c in others if p in {x for x, _, _ in near} or "auditprobe" in c]
print("marker processes from THIS launch still counted:", mine)
print("other marker processes counted (count):", len(others))
```
