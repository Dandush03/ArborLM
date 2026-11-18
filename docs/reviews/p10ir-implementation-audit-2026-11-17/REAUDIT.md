# P10-I-R re-audit of the fixes (ADR-0029 §19), 2026-11-17

**Auditor:** `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`); I did not write the fixes (the `arbor-implementer` subagent did). **Object:** branch `claude/p10-i-r`, commit `1d667e5` (fixes) on `9649f7b` (audit and rulings), diffed against `aeac3fd`. Independent engineering evidence; not Astra validation, not a human approval. `Astra review: NOT_PERFORMED`.

**Seal attestation.** As before: I opened no `eval.json`, no checkpoint and no data manifest of `experiments/P10S1-registered-attempt2-20261117`, and saw no sealed value. All runs below use test-range seeds, synthetic backbones and scratch directories.

## Verdict

**READY FOR REHEARSAL AFTER THE LISTED FIXES** — one REQUIRED fix (N1, small) and the procedure point N2 for the lead. Everything I raised is fixed and verified by my own reproducers; the oracles agree with the code on every case under the rulings.

## Environment and commands

macOS 27.2.1 arm64, locked environment (torch 2.8.0), one thread, deterministic algorithms (platform of record). Scripts in the scratchpad `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10ir-audit/` (new ones in the appendix; earlier ones in `AUDIT.md`).

| Command | Result |
|---|---|
| `timeout 1200 uv run --locked pytest tests/test_p10ir_*.py -q -p no:cacheprovider` | 213 passed, 2 warnings, 128 s |
| `uv run --locked ruff check .` | All checks passed |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_reads.py` (unchanged from the audit) | 4,100 tree, 66 flat, 462 index queries: 0 problems; no autograd warning any more |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_labels_v3.py` | 200,000 tree, 90,000 index, 32,768 cell, 100,000 combination, 6,561 R-CONFIRM, 20,000 plateau cases: **0 disagreements** |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_grad_memory_v2.py {256,1024}` | autograd enabled in the caller: fact pass 21.9 / 27.1 MiB, gate 4 16.5 / 64.8 MiB (transient), outputs carry no grad |
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_pipeline_v2.py <scratch>/pipe2` | B3 order, R2, ruling 3: see below |
| `sh <scratch>/audit_b2.sh` (scratch clone at HEAD; fake freeze, freeze record and Decision 2 committed in the clone only) | B2: see below |

## Findings of the audit

| Finding | Status | Evidence |
|---|---|---|
| B1 autograd in fact passes and gate 4 | **FIXED** | `@torch.no_grad()` on `tree_path`, `exhaustive_top`, `independent_flat`, `tree_fact_pass`, `flat_fact_pass`, `_collect`, `exactness_gates`, `compare_selection`. With autograd on in the caller, growth is flat in the number of facts (21.9 → 27.1 MiB from 256 to 1,024 facts; was 841.6 MiB at 256). Read values unchanged (read oracle 0 problems). |
| B2 refused worker FAILED | **FIXED** | In a scratch clone with a committed fake registered freeze, a registered `work reads` task started with an untracked file: `paused_identity`, stage PAUSED, no failed record, log `?? untracked_during_stage.txt`. After removing the file the same task ran: `completed`, returncode 0, stage COMPLETE. |
| B3 R-CONFIRM after A1's analysis | **FIXED** | Synthetic plan run in the order gates-a1, a1, analysis, report, then gates-a2, a2-train, a2, `confirm`: all COMPLETE; the 1,572 A1 files (analysis.json, REPORT.md, every item and read record) have identical SHA-256 before and after `confirm`; `confirm.json` names A1's analysis hash; re-running `analysis` or `confirm` is refused. |
| R1 gate 1 per stage, two missing links | **FIXED** | `stages.gate1_all` checks every A1 checkpoint (model.pt = snapshot.json = train.json = plan digest), every `train.json` against the committed manifest's `result_sha256`, the data manifests against P10-S1's frozen `data_manifests` (same `file_sha256` definition as `studies/p10s1/stages.py:1528`), and regenerates every draw, before any read; failure fails `gates-a1`. The per-item check now runs before the checkpoint is loaded. |
| R2 labels from the config | **FIXED** | `analysis.label_of_from_items` everywhere in `run_analysis` and `run_confirm`. On the synthetic rehearsal the A1 analysis now finds every item: tree NO GAP 29, MIXED-PANEL 1, NOT EVALUABLE (WEAK) 10; index SPARSE 30, NOT EVALUABLE (WEAK) 10 (the synthetic training was lengthened to 64 updates). |
| R3 rehearsal against the plan file | **FIXED in code (ruling 5); not yet exercised on the real candidate plan** | `candidate-plan`, the `candidate` phase and the freeze's hash check; see N2 and the last section. |
| R4 accuracy version | **FIXED** | Printed per replicate, per comparison, per panel (`REPORT.md`: "T1 A: NOT RESTORED (accuracy version 0.858) …"). acc₀ = `disabled_correct / n` of each read; across all 80 (slots, draw, update, panel) groups of the synthetic A1 run every read of both arms had the same disabled count, as ruling 3 expects (the backbone is frozen). Advisory: `_retention_entry` uses X's acc₀ in the denominator too; assert X's and F0's acc₀ equal, or use F0's for F0. |
| R5 an item exception fails the cell | **FIXED as ruled (ruling 7), with a new problem N1** | `items.guarded` per gate, `run_item` catch-all `item_error`; the other checkpoints run. |
| R6 two readings | **FIXED as ruled** | Ruling 2: `cell_label` excludes MIXED-PANEL from the 4-of-5 count; ruling 1 kept (signature equality). My oracle, rewritten to the rulings, agrees on every case. |
| A1–A12 | **FIXED or answered** | A1: 38 re-use values. A2: `allocation_rows`/`allocation_problems` parse ADR-0029's `ALLOC` rows from the cited checker and require each config range inside its row. A3: docstring corrected. A4: `adapter.assert_seed_allowed` at the point of training. A5: rehearsal and tests use `test_index_seeds` 938901–938903. A6: `studies/p10s1`, `studies/p9`, `studies/p9i` compared between freeze commit and HEAD. A7: `require_ignored_run_dir` (see N3). A8: the recomputed index recall is popped in `run_gates12_item`; `--run-sealed` outside registered mode refused unless P10-S1's records are inside the run directory. A9: float64 means. A10: slack printed. A11: `h_margin_bits`. A12: tests extended (213). |

## New code reviewed as if for the first time

**`confirm`** (`stages.py` `run_confirm`, group A2, cap key a2): needs `a2` and `analysis` COMPLETE, reads A1's written record, rebuilds the diagnosis with `labels.diagnosis_from_json` (tuples restored, so signatures compare), writes `confirm/confirm.json` and `REPORT_CONFIRM.md` without overwrite. A1's report states that R-CONFIRM is the `confirm` stage's. Correct.

**`gate1_all`**: correct as above; exceptions inside a checkpoint check are recorded as failures (never pass). For A2 it checks the bridge manifests and regenerates the bridge draws (bridge checkpoints do not exist yet; their identity is the per-item check).

**`candidate-plan`, `candidate` phase, freeze hash check (ruling 5).** `candidate-plan` writes `freeze/plan.json` once; the `candidate` phase verifies it (`verify_plan(candidate=True)`: frozen files, config, manifests, items = re-derivation), enumerates tasks (70/20/20), items (280/40), checkpoint files and digests, bridge-cell seeds and schedules, manifests, and runs analysis, report and R-CONFIRM on a synthetic registry keyed by the plan's own labels; it records the plan file's SHA-256. `freeze` refuses unless that rehearsal record (in one invocation, with every stage COMPLETE and gates 1 and 2 on the registered checkpoints passed) names the SHA-256 of the plan file now in `freeze/`, and refuses a plan or config with provisional caps. Registered stages refuse unless `freeze_record.json` names the plan file's hash (`verify_freeze_record`) and the rehearsal record still hashes to what the freeze record names. **A freeze cannot be made on a plan that was not rehearsed** (short of hand-editing the rehearsal record, which code cannot prevent). On the circularity, see N2.

**`items.guarded`**: catches an exception inside one gate and records the gate failed with its scope and `type: message[:300]`. Sealed values: the only messages on the gate-3 path are `SealedMissing` (path and key path only) and JSON decode errors (position only); `tree_recall`'s value is never formatted. I found no path by which a sealed value reaches a message. It can, however, swallow errors that should stop or pause a stage: N1.

**acc₀ printing**: as R4 above.

**Allocation-row check**: regex over the cited checker's `("P10-I-R ADR-0029", role, lo, hi)` rows; a checker without ADR-0029 rows is a problem. Correct.

**`require_ignored_run_dir`**: correct for the run directory; see N3 for the ledger.

**Extended freeze comparison**: `check_preconditions` now compares `studies/p10ir`, `studies/p10s1`, `studies/p9`, `studies/p9i` and the config between the freeze commit and HEAD; `frozen_input_check` still covers `src/arborlm`, `uv.lock`, `pyproject.toml`.

## New problems

**N1 (REQUIRED). The catch-all in `items.run_item` turns an identity or data failure during a registered run into a permanent NOT EVALUABLE, and would let a systematic code error complete the stage.**
`studies/p10ir/items.py` `run_item` (`except Exception` → `item_error`, then `rec.finish`, so the item is complete and never retried) and `check_identity_first` (raises `RuntimeError`). Reproducer: `audit_b2.sh`, second run: a checkpoint that cannot be found was recorded `checkpoint_identity: passed False` and `item_error: RuntimeError …`, and the stage became COMPLETE. Ruling 8 and §13 say an identity failure stops the stage, and that a file restored bit for bit lets it resume; after `gates-a1` has passed, a later identity or regenerated-data mismatch means something changed during the run and should be PAUSED — IDENTITY, not a registered NOT EVALUABLE. Likewise `OSError`/`MemoryError` (environment, not checkpoint) become permanent NOT EVALUABLE, and a code error hitting every item would produce a complete A1 whose R-DIAGNOSIS is NOT EVALUABLE (the rehearsal flags `item_error` as INCOMPLETE, but a registered run does not). Fix: in `check_identity_first` and on a `load_data` mismatch raise `StageRefused` and let it propagate (worker exit 75, PAUSED — IDENTITY, no `item.json`); let `OSError` and `MemoryError` propagate; in a registered stage write the count of `item_error` gates into the stage manifest and print them in the analysis and report separately from gate failures (and, for the lead's ruling, consider refusing the analysis when every item of a cell or of the stage has an `item_error`).

**N2 (procedure, PENDING LEAD REVIEW). Caps are in the plan's hash, so "caps set from the rehearsal" (§12) costs a second full rehearsal.** The plan carries `config_sha256`, `stage_caps` and `caps_provisional`; the freeze refuses a provisional plan; a rehearsal record must contain the candidate phase *and* complete synthetic, real-size and gates-1-and-2 phases in one invocation. So the coherent, enforced procedure is: candidate plan with provisional caps → full rehearsal (measures) → lead sets caps and clears `provisional` → delete and rewrite the candidate plan → **second full rehearsal** → freeze. The code enforces every step except that caps actually came from a rehearsal (a lead could clear `provisional` with estimates before the first rehearsal; code cannot tell). Also: `candidate-plan` refuses an existing plan, so the superseded candidate must be deleted by hand (keep it and its rehearsal record elsewhere for provenance); and `freeze` does not re-run `verify_plan`, so a stale plan (code or config changed after the rehearsal) can still receive a freeze record — the registered stages then refuse it, so no wrong result, only a wasted freeze. Advisory: call `verify_plan(candidate=True)` in `freeze`.

**N3 (ADVISORY). The ledger is written at `run_dir.parent`.** If the run directory is the ignored root `experiments/` itself, `require_ignored_run_dir` passes (`experiments/x` is ignored) but the ledger goes to the repository root and dirties the tree (every later worker then pauses). Check the ledger path too, or require the run directory to be a sub-directory of an ignored directory.

**N4 (ADVISORY).** The candidate phase hashes the plan file at the end of the phase, not when it loads it; hash at load and compare at the end.

## What remains unexercised until the real rehearsal

Never executed anywhere on real inputs: `candidate-plan` and `generate-bridge`; the `candidate` phase against the real candidate plan (280/40 items, `bridge_cells` from P10-S1's frozen plan, the plateau lists and D-OQ context, the 280 digests and the real manifests); `gates-a1`'s `gate1_all` on the 280 registered checkpoints and the committed train manifest; the real-size phase (32,768 facts, 16,384 slots: seconds per read and peak memory of T3/T2 and of 15 index reads); gates 1 and 2 on the registered checkpoints; the adapter identity gate on P10-S1's draw-1 cells; the seed gate's checker run inside the freeze; the freeze itself (tested only in a temporary repository with the seed gate stubbed).

**Watch for, when you run the rehearsal:**
1. `candidate` phase: status COMPLETE with an empty `problems` list; tasks 70/20/20; `synthetic_registry.rows_reached` covers every row; `no_item_record` false for A1 and A2.
2. Real-size phase: no task `killed_rss`; peak RSS per worker well under 3 GiB (B1's fix should hold it to a few hundred MiB plus the data); seconds per read at 16,384 slots for T2/T3 and I64@2048, which set the A1 cap.
3. `registered_checkpoint_gates`: `gate1_passed` and `gate2_passed` true with `items_done = items_expected = 280`; any T0-path mismatch or count difference there is platform or library drift and must be resolved before Decision 2. `adapter_identity` passed (tensors and `model_sha256` equal at 512, 1,024, 2,048).
4. Any `item_error` in the rehearsal (the record then marks a1/a2 INCOMPLETE): read its message before anything else.
5. The order of N2: if caps are set from this rehearsal, the candidate plan must be rewritten and the whole rehearsal run again before `freeze`; `freeze` will refuse otherwise.
6. No worker ever exiting 75 during the rehearsal unless you changed the tree; no file appearing in `git status` during or after any stage.

## Appendix: new auditor scripts (verbatim)

`audit_labels_v3.py` is `audit_labels.py` (appendix of `AUDIT.md`, attempt 2) with three edits: row 3 FULLY requires both T1 and T3 RESTORED (choice 6, accepted); `combine_oracle` and the R-CONFIRM oracle carry CELL-DEPENDENT as `("CELL-DEPENDENT", row at X, row at Y)` (ruling 1); `cell_oracle` already excluded MIXED-PANEL (ruling 2). `audit_reads.py` is unchanged (appendix of `AUDIT.md`).

### `audit_grad_memory_v2.py`

```python
"""Re-audit of B1: peak RSS of reads.tree_fact_pass AND gates.exactness_gates on a 16,384-slot tree with Parameter keys, autograd ENABLED in the caller (as run_tree_item calls them).
Usage: audit_grad_memory_v2.py <facts>. Random tensors, test seeds; nothing written."""
import resource, sys
import torch
from torch.nn import functional as F
from studies.p9.model import AdditionSpec
from studies.p10ir import core, gates, reads
from studies.p10s1.model import S1Memory
torch.set_num_threads(1)
facts = int(sys.argv[1])
mem = S1Memory(AdditionSpec("learned_tree", 16384, 16, "R1", 64, 0), 938801)
assert torch.is_grad_enabled() and mem.keys.requires_grad
q = F.normalize(torch.randn(facts, 16, generator=torch.Generator().manual_seed(938802)), dim=-1)
specs = [s for s in reads.tree_read_specs(16384) if s.name in ("T0", "T1", "T1w", "T3", "T2")]
b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
out = reads.tree_fact_pass(mem, q, specs, chunk_elements=1 << 20)
m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
g = gates.exactness_gates(mem, q, core.Thresholds.from_config(), chunk_elements=1 << 20)
a = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t = reads.tree_path(mem.keys, mem.router, q[:4], 64, True, True, per=256, chunk_elements=1 << 20)
print({"facts": facts, "fact_pass_growth_mib": round((m - b) / 2**20, 1), "gate4_growth_mib": round((a - m) / 2**20, 1), "tree_path_output_requires_grad": t.values.requires_grad, "gate4_passed": [v["passed"] for v in g.values()]})
```

### `audit_pipeline_v2.py`

```python
"""Re-audit B3, R2, R4/ruling 3, R5: a synthetic rehearsal plan (test seeds, tiny sizes) run in the order of B3:
gates-a1, a1, analysis, report, THEN gates-a2, a2-train, a2, confirm. A1's records are hashed before and after confirm. Writes only under argv[1]."""
import collections, json, sys
from pathlib import Path
from arborlm.io import file_sha256
from studies.p10ir import core, rehearsal, stages
from studies.p10ir import plan as planmod
from studies.p10s1 import train as t
t.configure()
root = Path(sys.argv[1]) / "synthetic"
repo = Path.cwd()
cfg = core.load_config()
plan, ctx = rehearsal.build_synthetic_plan(root, cfg, 5)
order1 = ("gates-a1", "a1", "analysis", "report")
order2 = ("gates-a2", "a2-train", "a2", "confirm")
m1 = rehearsal.run_pipeline(plan, ctx, root, repo=repo, workers=1, inline=True, stages_to_run=order1)
a1_files = [root / "analysis" / "analysis.json", root / "report" / "REPORT.md"] + sorted((root / "A1" / "items").rglob("*.json"))
before = {str(p): file_sha256(p) for p in a1_files}
m2 = rehearsal.run_pipeline(plan, ctx, root, repo=repo, workers=1, inline=True, stages_to_run=order2)
after = {str(p): file_sha256(p) for p in a1_files}
print("statuses:", {k: v["status"] for k, v in {**m1, **m2}.items()})
print("B3: A1 files unchanged by confirm:", before == after, "| files:", len(before))
conf = json.loads((root / "confirm" / "confirm.json").read_text())
print("   confirm.json a1_analysis_sha256 matches:", conf["a1_analysis_sha256"] == before[str(root / "analysis" / "analysis.json")], "| R-CONFIRM:", {k: v["value"] for k, v in conf["r_confirm"].items()})
for st in ("analysis", "confirm"):
    try:
        stages.execute_stage(st, plan, ctx, root, root / "freeze" / "plan.json", repo=repo, workers=1, inline=True)
        print(f"   re-run {st}: ALLOWED")
    except planmod.StageRefused as e:
        print(f"   re-run {st}: refused ({str(e)[-60:]})")
full = json.loads((root / "analysis" / "analysis.json").read_text())
rows = collections.Counter((comp, r["row"], r["reason"][:30]) for c in full["A1"]["cells"].values() for ck in c["checkpoints"].values() for comp in ("tree", "index") for r in ck[comp]["replicates"])
print("R2: A1 replicate rows:", dict(rows))
print("   item_errors:", rehearsal.item_errors(root)[:3])
# R4 / ruling 3: is disabled_correct the same for every read of a draw and panel (T-OQ and F-OQ checkpoints)?
dis = collections.defaultdict(set)
for p in (root / "A1" / "items").rglob("read.*.json"):
    r = json.loads(p.read_text())
    draw = r["cell"].split("_d")[1].split("_")[0]
    for pn in ("A", "B"):
        dis[(r["cell"].split("_")[3], draw, r["update"], pn)].add((r["panels"][pn]["disabled_correct"], r["panels"][pn]["n"]))
print("ruling 3: (slots, draw, update, panel) groups:", len(dis), "with more than one disabled count:", sum(1 for v in dis.values() if len(v) > 1))
txt = (root / "report" / "REPORT.md").read_text()
print("   report prints accuracy version:", "accuracy version" in txt, "| sample:", next((l for l in txt.splitlines() if "accuracy version 0" in l or "accuracy version 1" in l), "none")[:200])
```

### `audit_b2.sh`

```sh
#!/bin/sh
# Re-audit B2 in a scratch clone at HEAD: a fake registered freeze (plan built by the code, freeze_record naming its hash, Decision 2 for A1) is committed IN THE CLONE ONLY;
# then a registered worker task is run through runner.run_tasks with an untracked file in the clone (expect paused_identity, no failed record), and again after removing it (expect the task to run).
S=/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10ir-audit
W=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1
C=$S/clone2; RUN=$S/regrun2; PY="$W/.venv/bin/python"
G="git -C $C -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false"
rm -rf "$C" "$RUN"; git clone -q --no-hardlinks --local "$W" "$C"
sed -i '' 's/^provisional = true/provisional = false/' "$C/configs/p10ir_routing.toml"
cd "$W" && PYTHONPATH="$W" "$PY" - "$C" "$RUN" <<'PYEOF' 2>&1 | grep -v "NumPy\|conversion_method"
import sys
from pathlib import Path
from arborlm.io import file_sha256, write_json
from studies.p10ir import core, plan as pm
repo, run = Path(sys.argv[1]), Path(sys.argv[2])
cfg = core.load_config(repo / core.CONFIG)
rec = pm.build_plan(mode=pm.REGISTERED, cfg=cfg, repo=repo, items=pm.registered_items(cfg), run_dir=run, s1_run_dir=None, extra={})
core.write_record(repo / core.PLAN, rec)
write_json(repo / pm.FREEZE_RECORD, {"kind": "freeze_record", "plan_file_sha256": file_sha256(repo / core.PLAN), "note": "auditor scratch fake"})
PYEOF
$G add -A >/dev/null && $G commit -qm "scratch: fake freeze"; F=$($G rev-parse HEAD)
mkdir -p "$C/results/p10ir-freeze-x"; printf 'DECISION: RUN\n%s\n' "$F" > "$C/results/p10ir-freeze-x/DECISION_2_A1.md"; $G add -A >/dev/null; $G commit -qm "scratch: decision 2 A1"
touch "$C/untracked_during_stage.txt"
cd "$W" && PYTHONPATH="$W" "$PY" - "$C" "$RUN" "$F" "$PY" <<'PYEOF' 2>&1 | grep -v "NumPy\|conversion_method"
import sys
from pathlib import Path
from studies.p10ir import core, runner, stages
from studies.p10ir import plan as pm
repo, run, F, py = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
plan = pm.Plan.load(repo / core.PLAN)
label = stages.labels_of_stage(plan, "a1")[0]
def task():
    argv = (py, "-m", "studies.p10ir.stages", "work", "reads", "--stage", "a1", "--labels", label, "--run-dir", str(run), "--plan", str(repo / core.PLAN), "--mode", "registered", "--freeze-commit", F, "--run-sealed", "--repo", str(repo))
    return runner.Task(label, argv, stages.task_dir(run, "a1") / f"{label}.done.json", stages.task_dir(run, "a1") / f"{label}.failed.json", stages.task_dir(run, "a1") / f"{label}.log")
out1, _ = runner.run_tasks([task()], workers=1, cap_seconds=300, rss_worker_bytes=3 << 30, rss_aggregate_bytes=18 << 30, env={"PYTHONPATH": str(Path.cwd())})
print("dirty tree:", out1[label]["status"], "| stage:", runner.stage_status(out1), "| failed record:", task().failed_path.exists())
print("   worker log tail:", task().log_path.read_text().strip().splitlines()[-1][:160])
(repo / "untracked_during_stage.txt").unlink()
out2, _ = runner.run_tasks([task()], workers=1, cap_seconds=600, rss_worker_bytes=3 << 30, rss_aggregate_bytes=18 << 30, env={"PYTHONPATH": str(Path.cwd())})
print("after restoring:", out2[label]["status"], "| returncode:", out2[label].get("returncode"), "| stage:", runner.stage_status(out2))
items = sorted((run / "A1" / "items").glob("*/item.json"))
import json
print("   items written:", len(items), "| gates of first:", {k: (v.get("passed"), str(v.get("error", ""))[:70]) for k, v in json.loads(items[0].read_text())["gates"].items()} if items else None)
PYEOF
```

### Outputs

```text
== audit_grad_memory_v2.out
{'facts': 256, 'fact_pass_growth_mib': 21.9, 'gate4_growth_mib': 16.5, 'tree_path_output_requires_grad': False, 'gate4_passed': [True, True, True]}
{'facts': 1024, 'fact_pass_growth_mib': 27.1, 'gate4_growth_mib': 64.8, 'tree_path_output_requires_grad': False, 'gate4_passed': [True, True, True]}
== audit_pipeline_v2.out
statuses: {'gates-a1': 'COMPLETE', 'a1': 'COMPLETE', 'analysis': 'COMPLETE', 'report': 'COMPLETE', 'gates-a2': 'COMPLETE', 'a2-train': 'COMPLETE', 'a2': 'COMPLETE', 'confirm': 'COMPLETE'}
B3: A1 files unchanged by confirm: True | files: 1572
   confirm.json a1_analysis_sha256 matches: True | R-CONFIRM: {'R-CONFIRM-INDEX': 'CONFIRMED', 'R-CONFIRM-TREE': 'CONFIRMED'}
   re-run analysis: refused (ifest.json is COMPLETE; a completed stage is never rewritten)
   re-run confirm: refused (ifest.json is COMPLETE; a completed stage is never rewritten)
R2: A1 replicate rows: {('tree', 'NO GAP', ''): 29, ('tree', 'MIXED-PANEL', ''): 1, ('index', 'SPARSE INDEX APPROACHES FLAT', ''): 30, ('tree', 'NOT EVALUABLE', 'WEAK REFERENCE'): 10, ('index', 'NOT EVALUABLE', 'WEAK REFERENCE'): 10}
   item_errors: []
ruling 3: (slots, draw, update, panel) groups: 80 with more than one disabled count: 0
   report prints accuracy version: True | sample:       - d1: T1 A: NOT RESTORED (accuracy version 0.858) / B: NOT RESTORED (accuracy version 0.832); T2 A: NOT RESTORED (accuracy version 0.689) / B: NOT RESTORED (accuracy version 0.682); T3 A: NOT RE
== audit_b2.out
dirty tree: paused_identity | stage: PAUSED | failed record: False
   worker log tail: ?? untracked_during_stage.txt
after restoring: completed | returncode: 0 | stage: COMPLETE
   items written: 4 | gates of first: {'checkpoint_identity': (False, 'ValueError: no checkpoint root for this item'), 'item_error': (False, 'RuntimeError: the checkpoint is not the frozen one (identity gate fail')}
== audit_labels_v3.out
floor 0.4730746427507113 cases {'tree': 200000, 'index': 90000, 'cell': 32768, 'combine': 100000, 'confirm': 6561}
disagreement classes: 0
== audit_reads_v2.out
{'tree_cases': 100, 'tree_queries': 4100, 'tie_skips': 0, 'flat_queries': 66, 'ivf_queries': 462}
problems: 0
```

`Astra review: NOT_PERFORMED`.
