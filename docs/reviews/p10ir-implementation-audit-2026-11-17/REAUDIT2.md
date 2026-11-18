# P10-I-R second re-audit: fixes N1–N4 and the measuring rehearsal, 2026-11-18

**Auditor:** `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`); I wrote none of the code or records audited. **Objects:** commit `dd273b3` (fixes, diffed against `1d667e5`), commit `33ad9d2` (the measuring rehearsal's record, `results/p10ir-rehearsal-measure-2026-11-18/`) and the run directory `experiments/P10IR-rehearsal-measure-20261118`. Independent engineering evidence; not Astra validation, not a human approval. `Astra review: NOT_PERFORMED`.

**Seal attestation.** I opened no `eval.json` and no checkpoint of the registered P10-S1 run. I read six of its `snapshot.json` files (the recorded `model_sha256` of the draw-1 8K/4K cells at 512, 1,024 and 2,048 updates) to re-check the adapter identity gate by hash. In the rehearsal's files I searched for the sealed key names and report presence by location only; I printed no value.

## Verdict

**READY FOR THE COUNTING REHEARSAL AND FREEZE AFTER THE LISTED FIXES**: F1 (two exception paths still turn MemoryError or OSError into NOT EVALUABLE) and F2 (two tests fail once the caps are set; the uncommitted caps edit in the worktree already makes them fail). F3 (a freeze-time trap) and the cap figures need the lead's attention; F4–F7 are advisory. The measuring rehearsal itself is sound: every check on my watch list holds.

## Environment and commands

macOS 27.2.1 arm64, the locked environment (torch 2.8.0). Scripts in the scratchpad `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10ir-audit/` (`audit_n1.py` is reproduced in the appendix).

| Command | Result |
|---|---|
| `PYTHONPATH=$PWD uv run --locked python <scratch>/audit_n1.py <scratch>/n1` (synthetic plan, test seeds) | see N1 below |
| `timeout 1500 uv run --locked pytest tests/test_p10ir_*.py -q -p no:cacheprovider` in the worktree | **2 failed, 217 passed**: the worktree holds an uncommitted edit of `configs/p10ir_routing.toml` (caps set, `provisional = false`) made while I worked (F2) |
| the same suite in a `git clone --local` of `33ad9d2` (the worktree's interpreter) | 219 passed, 2 warnings in 129.96s (0:02:09) |
| `uv run --locked ruff check .` | All checks passed |
| Python and `grep` reads of the rehearsal directory and its committed copy (no value printed) | see Part 2 |

## Part 1: fixes N1–N4

| Item | Status | Evidence |
|---|---|---|
| N1 missing checkpoint during a stage | **FIXED** | A worker task (`work reads`, subprocess) on a T-OQ cell whose U_P `model.pt` was renamed: `paused_identity`, return code 75, no failed record, its item directory empty. After restoring the file: `completed`, item complete. |
| N1 changed checkpoint | **FIXED** | Same with one byte appended to `model.pt`: `paused_identity`, 75, nothing written; resumes when restored. A regenerated draw that differs from its manifest now raises `StageRefused` too (code reading). |
| N1 OSError / MemoryError outside the gates | **FIXED** | Injected into `reads.read_counts` (T-OQ and F-OQ items): the exception propagates, no `item.json` is written. |
| N1 OSError / MemoryError inside a gate | **NOT FIXED (F1)** | Injected into `gates.path_gate` (MemoryError), `gates.index_rebuild_gate` (OSError) and `gates.exactness_gates` (MemoryError): each is recorded as that gate FAILED (`t0_path`, `index_rebuild_*`, `tv1/t3/t2_*`) and the item completes: the replicate becomes NOT EVALUABLE for good. |
| N1 a gate-4 failure | **FIXED** | A failing `tv1_priors_on_against_off` on draw 1 only: tree label of draw 1 NOT EVALUABLE (reason names the gate), draws 2–5 NO GAP, the index label of draw 1 unaffected (SPARSE INDEX APPROACHES FLAT). |
| N1 code error inside an item | **FIXED (counted and printed)** | `tree_fact_pass` raising ValueError: `item_error` gate with scope tree. With every fact pass raising, stage `a1` is COMPLETE with `item_errors: 80`, `clean: false`, a printed warning; `analysis` and `report` run to COMPLETE; the report prints `R-DIAGNOSIS: NOT EVALUABLE …` and an `ITEM ERRORS … 80` line. |
| N2 `--supersede` | **FIXED** (code reading; tests pass on the clean clone) | Refuses an existing plan without the flag; refuses once a freeze record exists; moves the old file to `freeze/superseded/plan-<sha12>.json` (never deleted); the new plan's frozen-file hashes include the superseded file. |
| N2 freeze re-derivation | **FIXED, with a trap (F3)** | `freeze` rebuilds the plan with `build_candidate` and refuses any difference. |
| N2 provisional rehearsal record | **FIXED** | `rehearsal.json` now carries `caps_provisional`; `freeze` refuses anything but `false`. The measuring record says `true`, so it cannot be frozen on. |
| N3 ledger | **FIXED** | `require_ignored_path` refuses a ledger at the repository root (checked: refused) and allows one under `experiments/`; `execute_stage` checks it. |
| N4 candidate hash | **FIXED** | Hashed at load, compared again at the end of the phase. |

**Should the analysis refuse when every item has an `item_error`?** My judgement: yes, in registered mode, whenever A1 has any `item_error`. An `item_error` is by construction a code or data error, not a gate outcome, and the A1 analysis record is written once and never rewritten; letting it run turns a bug into an irrevocable registered NOT EVALUABLE (or, with a partial bug, a set of labels with silently missing replicates). Refusing leaves the item records intact for a diagnosis and a decision by the human lead. Ruling 7 says such items count as NOT EVALUABLE, so this is a change to a ruling: **PENDING LEAD REVIEW**. If the ruling stands, at least print the `item_error` count on the R-DIAGNOSIS line itself, not further down the report.

## Part 2: the measuring rehearsal

| Watch-list item | Result |
|---|---|
| All stages COMPLETE | Yes: the eight stages of the synthetic phase, the five of the real-size phase (`gates-a1`, `a1`, `gates-a2`, `a2-train`, `a2` manifests all COMPLETE), and `gates12`. |
| `item_errors` 0 | Yes, but see F5: the rehearsal's own count of the real-size phase could not see A1. I read every item record directly: 4 A1 and 4 A2 real-size items, 80 + 40 synthetic, none with `item_error`; every gate of the real-size items passed. |
| No task paused or killed | Yes: every task `completed` in every manifest; no `paused_identity`, `killed_cap` or `killed_rss`. |
| Peak memory per worker | 643.5 MiB (A1 flat task), 710.8 MiB (A2 flat task, which also runs P10-S1's reference evaluation), 343.6 MiB (A2 training), against the 3 GiB guard; six such workers ≈ 4.3 GiB against 18 GiB. B1's fix holds at the registered size. |
| Gates 1 and 2 on 280 registered checkpoints | 280 gate records (140 T-OQ, 140 F-OQ), `passed: true` each. Every one of identity, `t0_path`, `t0_counts`, `f0_counts`, `i256_counts` has status **passed** (none skipped, so the bit-exact gates really ran on the platform of record); every count gate's source is "P10-S1's recorded counts (eval.json, through the whitelist extractor)" with `counts_equal: true`; every `i256_counts` has `index_hash_equal: true`; every `t0_path` checked a positive number of queries with no mismatch. Identity here is model.pt = snapshot.json = train.json; the two §4 links that `gate1_all` adds (train.json against the committed train manifest, data manifests against P10-S1's frozen `data_manifests`) were **not** part of `gates12` (F6). |
| Adapter identity gate | `passed`. Independently: the six `model.pt` files the adapter wrote in `gates12/gates12/identity_work` (F-OQ and T-OQ, 512, 1,024, 2,048 updates) hash exactly to the registered `snapshot.json` `model_sha256`. The rehearsal record keeps only passed/status, not the per-snapshot detail (F7). |
| Gate 3 not run; no sealed value | `gate3_run: false`; no file under `gates12/` mentions "recall". The sealed key names occur only in the rehearsal's **own** miniature P10-S1 records (`synthetic/s1`: 10, 50 and 40 files for the three names; `real/s1`: 1, 3 and 2), which P10-S1's evaluation writes by construction and which are not registered results; the 53 `*recall_reproduction` gate records of the miniatures hold only `equal`, `passed`, `scope`, `status`. |
| Worker settings | The top-level `platform` block (6 threads, 18 interop threads, determinism off) is the driver's. Every real-size item record carries the worker's platform: 1 thread, 1 interop thread, deterministic algorithms on; and every bit-exact gate has status `passed`, which `gates.exact` gives only when those settings hold. The record need not be fixed for correctness; for provenance the counting rehearsal's record should carry the workers' settings (advisory). |

**README against `rehearsal.json`.** Peak memory (643 / 711 / 344 MiB), charged seconds (synthetic 67.6, real 959.6, gates12 294.3) and every per-read time in the README's table agree with the record (for example T2 58.3–58.7 s, T3 58.3–58.8 s, I64@2048 11.5–11.8 s). The sums of read times per checkpoint, 172.1 s (tree) and 172.9 s (flat), agree with the README's 172 and 173.

**The A1 projection.** The basis (every checkpoint costed at the largest cell, 32,768 facts and 16,384 slots) is a sound upper bound: every other cell has fewer facts, fewer slots, or both. The arithmetic is low, because read seconds omit the fact passes, gate 4 and gate 2/3 inside each item. The item records give the whole cost per checkpoint: tree 238.0 and 233.5 s, flat 198.9 and 197.3 s; per-task overhead about 0.6 s. Hence 140 × 235.75 + 140 × 198.1 + 70 × 0.65 ≈ **60,800 worker-seconds, 2.81 hours on six workers** (README: 57,400 and about 2.7). Unmeasured: slowdown when six workers run at once (the real-size phase ran two).

**Caps under §12 ("charged + 2 × projected remaining"; nothing is charged yet on the registered ledger).**
- A1 group: a1 2.81 h + gates-a1 (gate1_all hashes 280 checkpoints and regenerates five draws, plus the seed checker; well under 0.1 h by the gates12 timing) + analysis and report (seconds) ≈ 2.9 h → **about 5.8 h; I would set 6.0**.
- A2 group: training 0.87 h (§10, from P10-S1's seconds per update) + reads of 40 checkpoints bounded by the largest A2 item (243.4 s; 9,700 worker-seconds, 0.45 h) + gates-a2 with the identity gate (about 0.05 h) ≈ 1.37 h → **about 2.75 h; 3.0**.
- Total ≈ 8.8 h → **9.0** or more. The uncommitted edit in the worktree (a1 5.5, a2 3.0, total 10.0) has A1 slightly below 2 × my projection (5.8) and above 2 × the README's (5.3); it is the human lead's figure to set.

## Findings

**F1 (REQUIRED). MemoryError and OSError inside a gate are still recorded as a failed gate.** `studies/p10ir/items.py` `guarded` (`except Exception`) and the `try` around `gates.exactness_gates` in `run_tree_item`. Reproducer: `audit_n1.py` cases e3–e5. Fix: in both, re-raise `StageRefused`, `MemoryError` and `OSError` except `sealed.SealedMissing` (a `FileNotFoundError`, which is a genuine gate-2/3 failure: a key or record that is not there).

**F2 (REQUIRED). Two tests depend on the live caps and fail once the caps are set.** With the worktree's uncommitted caps edit, `test_verify_plan_checks_every_frozen_file_the_config_the_caps_and_the_run_directory` fails (`the stage caps in the config differ from the plan's`) and `test_freeze_refuses_provisional_caps_and_a_registered_verify_needs_the_freeze_record` fails (`FileNotFoundError: …/frepo/studies/p10s1/freeze/plan.json`: with provisional cleared the test reaches the re-derivation, which its temporary repository cannot support). Both pass on the clean commit. The suite must be green at the freeze commit: give these tests their own temporary config.

**F3 (lead's attention before the freeze). The freeze's re-derivation compares fields that are not frozen inputs.** `build_plan` stores the ADR's hash (`adr`, provenance only by §13) and the process's `platform` record; `cmd_freeze` compares the whole re-derived plan. Any edit of ADR-0029 between `candidate-plan` and `freeze` (for example recording the caps or a ruling), or a different thread setting of the freezing process, makes the freeze refuse, and the remedy is supersede and rehearse again. Either exclude `adr` and `platform` from the comparison, or make every ADR edit before `candidate-plan`.

**F4 (ADVISORY). Timing attribution in A2.** `I256@512` takes 23.5–24.0 s in A2 against 9.5–9.7 s in A1 because its timer also covers gate 2's reference evaluation by P10-S1's `_read_record` (A2 only). The read's `seconds` field is descriptive; stop the timer before the gate.

**F5 (ADVISORY). Case-insensitive file system.** On macOS `a1/` (manifest and tasks) and `A1/` (items) are one directory, created as `a1` in the real-size phase. `stages.item_errors(run_dir)` with its default pattern `A[12]` therefore saw only A2's items there (4 of 8). Registered stages call it with the literal stage name and are not affected; the rehearsal's own count of the real-size phase is. Use literal names (or rename the stage directories).

**F6 (watch item). The two §4 identity links run first at `gates-a1`.** `gates12` checked model.pt, snapshot.json and train.json on all 280 checkpoints, but not train.json against the committed train manifest nor the data manifests against P10-S1's frozen hashes; nor has `gate1_all` regenerated the five registered draws. A failure there would stop A1 before any read (safe), but it would be seen only after Decision 2.

**F7 (ADVISORY).** Keep the adapter identity gate's per-snapshot detail (tensors equal, hash equal) in the rehearsal record, not only passed/status.

## Part 3: still unexercised before the registered run

- `generate-bridge` (five bridge manifests) and `candidate-plan` on the real run directories (280 digests, `bridge_cells` from P10-S1's frozen plan, plateau lists, D-OQ context, the train manifest and frozen data-manifest hashes).
- The `candidate` phase against that real candidate plan, and a rehearsal record with `caps_provisional: false` (the counting rehearsal).
- `freeze` outside a temporary repository: the full re-derivation (F3), the seed gate with the real checker, the attestations.
- `gates-a1`'s `gate1_all` on the registered inputs (F6), the registered entry points end to end, `confirm` after a real A2.
- Six workers at once on the registered sizes (contention; the cap's factor 2 covers a moderate slowdown).

What to watch in the counting rehearsal: the candidate phase COMPLETE with no problems and tasks 70/20/20; `caps_provisional: false` in the record; item errors counted with literal stage names; no worker exiting 75 unless you changed the tree; and no edit of ADR-0029 or the config between `candidate-plan` and `freeze`.

## Appendix: `audit_n1.py` (verbatim)

```python
"""Re-audit 2, N1: identity failures, environment errors, gate-4 failure and item errors on a synthetic rehearsal plan (test seeds, tiny sizes). Writes only under argv[1]."""
import collections, json, shutil, sys
from pathlib import Path
from studies.p10ir import analysis, core, gates, items, reads, registry, rehearsal, runner, stages, stages_io
from studies.p10ir import plan as planmod
from studies.p10s1 import core as s1core
from studies.p10s1 import train as t
t.configure()
base = Path(sys.argv[1]); repo = Path.cwd(); cfg = core.load_config()
root = base / "syn"
plan, ctx = rehearsal.build_synthetic_plan(root, cfg, 5)
ppath = root / "freeze" / "plan.json"
stages.execute_stage("gates-a1", plan, ctx, root, ppath, repo=repo, workers=1, inline=True, run_checker=False)
it_t = next(i for i in plan.items("A1") if i["arm"] == "T-OQ" and i["update"] == i["u_p"])
label = it_t["cell"]
def task():
    argv = (sys.executable, "-m", "studies.p10ir.stages", "work", "reads", "--stage", "a1", "--labels", label, "--run-dir", str(root), "--plan", str(ppath), "--mode", "rehearsal")
    td = stages.task_dir(root, "a1")
    return runner.Task(label, argv, td / f"{stages_io.safe_name(label)}.done.json", td / f"{stages_io.safe_name(label)}.failed.json", td / f"{stages_io.safe_name(label)}.log")
pt = ctx.snapshot_dir(it_t) / "model.pt"
idir = stages_io.item_dir(root, "A1", it_t["id"])
for case in ("missing", "changed"):
    orig = pt.read_bytes()
    if case == "missing":
        pt.rename(pt.with_suffix(".bak"))
    else:
        pt.chmod(0o644); pt.write_bytes(orig + b"\0")
    out, _ = runner.run_tasks([task()], workers=1, cap_seconds=600, rss_worker_bytes=3 << 30, rss_aggregate_bytes=18 << 30, env={"PYTHONPATH": str(repo)})
    written = sorted(p.name for p in idir.glob("*")) if idir.exists() else []
    print(f"N1 {case} checkpoint: status {out[label]['status']} rc {out[label].get('returncode')} | failed record {task().failed_path.exists()} | files in its item dir {written}")
    if case == "missing":
        pt.with_suffix(".bak").rename(pt)
    else:
        pt.write_bytes(orig)
out, _ = runner.run_tasks([task()], workers=1, cap_seconds=900, rss_worker_bytes=3 << 30, rss_aggregate_bytes=18 << 30, env={"PYTHONPATH": str(repo)})
print("   after restoring:", out[label]["status"], "| item complete:", (idir / "item.json").is_file())

# injected environment errors and a gate-4 failure, on fresh run directories sharing the miniature P10-S1 run
def fresh(name):
    r = base / name
    c = items.Ctx("rehearsal", r, root / "s1", None, synthetic=True, run_sealed=False, sizes=ctx.sizes, manifests=ctx.manifests, index_seeds=ctx.index_seeds)
    return r, c
digests = plan.data["checkpoint_digests"]
def inject(name, target, attr, exc, item):
    r, c = fresh(name)
    orig = getattr(target, attr)
    def boom(*a, **k):
        raise exc
    setattr(target, attr, boom)
    try:
        items.run_item(c, item, digests); res = "returned"
    except BaseException as e:  # noqa: BLE001
        res = f"raised {type(e).__name__}"
    finally:
        setattr(target, attr, orig)
    rec = stages_io.item_dir(r, item["stage"], item["id"]) / "item.json"
    g = json.loads(rec.read_text())["gates"] if rec.is_file() else {}
    bad = {k: (v.get("scope"), str(v.get("error", ""))[:50]) for k, v in g.items() if v.get("passed") is False}
    print(f"N1 inject {exc.__class__.__name__} in {attr}: {res} | item.json {rec.is_file()} | failed gates {bad}")
it_f = next(i for i in plan.items("A1") if i["arm"] == "F-OQ" and i["update"] == i["u_p"])
inject("e1", reads, "read_counts", OSError("disk"), it_t)
inject("e2", reads, "read_counts", MemoryError(), it_f)
inject("e3", gates, "path_gate", MemoryError(), it_t)
inject("e4", gates, "index_rebuild_gate", OSError("disk"), it_f)
inject("e5", gates, "exactness_gates", MemoryError(), it_t)
inject("e6", reads, "tree_fact_pass", ValueError("code bug"), it_t)

# gate-4 failure on one replicate only, then every item an item_error, through the stage and the analysis
r7 = base / "g4"; c7 = items.Ctx("rehearsal", r7, root / "s1", None, synthetic=True, run_sealed=False, sizes=ctx.sizes, manifests=ctx.manifests, index_seeds=ctx.index_seeds)
orig_ex = gates.exactness_gates
def fail_d1(source, codes, th, **k):
    out = orig_ex(source, codes, th, **k)
    if fail_d1.first:
        out["tv1_priors_on_against_off"] = gates.gate("tree", False, injected=True)
    return out
target = [i for i in plan.items("A1") if i["cell_name"] == it_t["cell_name"] and i["update"] == it_t["update"]]
for it in target:
    fail_d1.first = it["id"] == it_t["id"]
    gates.exactness_gates = fail_d1
    items.run_item(c7, it, digests)
gates.exactness_gates = orig_ex
spec = [s for s in stages._specs_of(plan, "A1") if s.name == it_t["cell_name"]][0]
reg = registry.load(r7, "A1"); lab = analysis.label_of_from_items(plan.items("A1"))
th = core.Thresholds.from_config(cfg)
from studies.p10ir import labels as L
rows = [(d, L.tree_replicate(analysis.tree_rep(reg, "A1", spec, d, it_t["update"], lab), th).row, L.tree_replicate(analysis.tree_rep(reg, "A1", spec, d, it_t["update"], lab), th).reason[:40], L.index_replicate(analysis.index_rep(reg, "A1", spec, d, it_t["update"], lab, cfg, ctx.index_seeds), th).row) for d in range(1, 6)]
print("N1 gate-4 failure on draw", it_t["draw"], "only:", rows)

r8 = base / "allerr"; c8 = stages.ctx_for(plan, r8, run_sealed=False, experiments_root=None)
stages.execute_stage("gates-a1", plan, c8, r8, ppath, repo=repo, workers=1, inline=True, run_checker=False)
ot, of = reads.tree_fact_pass, reads.flat_fact_pass
def bug(*a, **k): raise ValueError("injected code bug")
reads.tree_fact_pass = reads.flat_fact_pass = bug
m = stages.execute_stage("a1", plan, c8, r8, ppath, repo=repo, workers=1, inline=True)
reads.tree_fact_pass, reads.flat_fact_pass = ot, of
print("N1 every item an item_error: a1 status", m["status"], "| item_errors", m["item_errors"], "| clean", m["clean"])
for st in ("analysis", "report"):
    try:
        mm = stages.execute_stage(st, plan, c8, r8, ppath, repo=repo, workers=1, inline=True); print(f"   {st}: {mm['status']}")
    except planmod.StageRefused as e:
        print(f"   {st}: refused {str(e)[:80]}")
txt = (r8 / "report" / "REPORT.md").read_text() if (r8 / "report" / "REPORT.md").is_file() else ""
print("   report: R-DIAGNOSIS line:", next((l for l in txt.splitlines() if l.startswith("**R-DIAGNOSIS")), None)[:60] if txt else None, "| ITEM ERRORS line:", next((l[:70] for l in txt.splitlines() if l.startswith("ITEM ERRORS")), None))
```

### Output

```text
N1 missing checkpoint: status paused_identity rc 75 | failed record False | files in its item dir []
N1 changed checkpoint: status paused_identity rc 75 | failed record False | files in its item dir []
   after restoring: completed | item complete: True
N1 inject OSError in read_counts: raised OSError | item.json False | failed gates {}
N1 inject MemoryError in read_counts: raised MemoryError | item.json False | failed gates {}
N1 inject MemoryError in path_gate: returned | item.json True | failed gates {'t0_path': ('tree', 'MemoryError: ')}
N1 inject OSError in index_rebuild_gate: returned | item.json True | failed gates {'index_rebuild_i256': ('index', 'OSError: disk'), 'index_rebuild_i64_s938901': ('index', 'OSError: disk'), 'index_rebuild_i64_s938902': ('index', 'OSError: disk'), 'index_rebuild_i64_s938903': ('index', 'OSError: disk')}
N1 inject MemoryError in exactness_gates: returned | item.json True | failed gates {'t2_against_independent_flat': ('tree', 'MemoryError: '), 't3_against_independent_flat': ('tree', 'MemoryError: '), 'tv1_priors_on_against_off': ('tree', 'MemoryError: ')}
N1 inject ValueError in tree_fact_pass: returned | item.json True | failed gates {'item_error': ('tree', 'ValueError: code bug')}
N1 gate-4 failure on draw 1 only: [(1, 'NOT EVALUABLE', 'T-OQ: gate(s) failed: tv1_priors_on_agai', 'SPARSE INDEX APPROACHES FLAT'), (2, 'NO GAP', '', 'SPARSE INDEX APPROACHES FLAT'), (3, 'NO GAP', '', 'SPARSE INDEX APPROACHES FLAT'), (4, 'NO GAP', '', 'SPARSE INDEX APPROACHES FLAT'), (5, 'NO GAP', '', 'SPARSE INDEX APPROACHES FLAT')]
WARNING: 80 item(s) raised in worker code (item_error): the stage is not clean; see the manifest
N1 every item an item_error: a1 status COMPLETE | item_errors 80 | clean False
   analysis: COMPLETE
   report: COMPLETE
   report: R-DIAGNOSIS line: **R-DIAGNOSIS: NOT EVALUABLE [REGISTERED RE-ANALYSIS OF OBSE | ITEM ERRORS line: ITEM ERRORS (worker code raised inside an item; counted apart from gat
```

`Astra review: NOT_PERFORMED`.
