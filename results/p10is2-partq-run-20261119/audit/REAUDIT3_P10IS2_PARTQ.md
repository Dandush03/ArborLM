# P10-I-S2 Part Q: third re-audit, at 039b1d4, before the freeze for registered attempt 2

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-18. I wrote none of the audited code.
- **Object.** `git diff f36a46e..039b1d4` on `claude/p10-i-s2-impl` (`223bd76`, `ea105e3`, `039b1d4`), read by commit (`git archive 039b1d4`), never from the working tree. Earlier findings are in `_scratch/audits/REAUDIT2_P10IS2_PARTQ.md`.
- **Scratch.** `agent-acd0bce1f7811562f/experiments/_scratch/audit-reaudit3/` (git-ignored); deleted after this report.
- **Clones.** Four fully frozen scratch clones (A–D), each a `git archive 039b1d4` plus `git init`, with the committed attempt-1 freeze files removed. Each has a registered-mode candidate plan built by the code with its own import walk, a freeze record and a committed Decision 2.
- **Launches.** Every stage was launched through `studies/p10is2/launch/partq_registered.sh` in a fresh process. Fakes were limited to the downloads and teachers: the implementer's test module `p10is2_e2e_world.install()`, run by a fake `uv` on `PATH`. No `PYTHONPATH` was set, so no package outside the lock was used. Everything else ran as real code, on tiny synthetic inputs.
- **Limits observed.**
  - One process at a time, a `timeout` on every command, no parallel pytest.
  - No sealed value opened, no registered seed on real data, no network, no git writes outside the scratch clones.
  - The public measuring record was copied, not its `sealed/` folder.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdict: READY AFTER THE LISTED FIXES

The defect behind attempt 1 is gone on the registered path. R1 and R2 hold. Three items remain before the freeze:
- **F1** needs a small code fix, or a recorded acceptance.
- **F2** is a pre-freeze command and needs no code.
- **F3** is a record in Decision 2.

## 1. The chicken-and-egg at `inputs`, and the other stages

- **Clone A**, all eight stages launched as a registered launch calls them (`partq_registered.sh <stage> <run-dir> <freeze-commit>`): each exits 0, COMPLETE, with `mode=registered` and `within_cap=True`. The label is `TEACHERS-QUALIFIED (DISJOINT DRAWS)` on synthetic data, and the tree stays clean.
- **What each stage requires at its start:**
  - every stage: the previous stage's completion record (`require_prerequisites`);
  - every stage after `inputs`: `inputs/record.json` (`make_ctx`, with `inputs` itself exempt through `inputs_stage`);
  - the gated stages: the `qcheck` completion and the Q records (`gate_outcome`);
  - `outputs`: `generation/pools.json` (`accepted_pool`);
  - `qcheck` and `generation`: `step_qfit`, which re-reads `qfit/record.json` or recomputes it.
- **None of them requires a record written only by itself or by a later stage.**
- The earlier NOT RUN BY RULE path (attempt-1 code, `REAUDIT2` "Check of f36a46e", case B) is unchanged by this diff, except that completion records now carry their mode.

## 2. Remaining branches on `--rehearsal`, and what they could hide

**The branches.**

| # | Branch | What it does |
|---|---|---|
| a | Preconditions | It skips `check_preconditions` (clean tree, freeze commit ancestry, HEAD equal to the freeze commit, foreign freeze record), `require_decision_2`, `verify_freeze_record` and the provisional-caps check. It adds three refusals: the commit argument must be `-`, no freeze record may exist, and the run directory must not be the plan's. It verifies the plan with `candidate=True` against the plan's own run directory, and asserts the platform |
| b | `mode="rehearsal"` | Seeds 2529xx; the candidate ledger in the run directory; the sealed layout; the analysis prints the public summary instead of the label |
| c | `limits` | 2 generation blocks, 1 Q_check block, `force_generation` |
| d | The teacher gate | `gate_outcome` and the DATA-EXHAUSTED refusal are not applied |
| e | `--pause-after-batches` and `--plan-file` | Rehearsal only |
| f | `cmd_ledger --mode rehearsal` | Allowed after a plan exists, but not into the plan's run directory |

Branches a–f are the documented overrides; there is no other difference.

**Registered-only paths a rehearsal therefore never runs on real data:**
1. The **shared ledger** checked against the real window grid (`verify_study_ledger` on `data/p10i-shared/panel_ledger.json`): only the registered `inputs` stage does it. The rehearsal checks its own candidate ledger instead (see F2).
2. Q_check beyond one block, generation beyond two blocks, and the target and draw logic (`draws_label`, and `make_draws` with seeds 250916 and 250917): exercised only synthetically (clone A reached DISJOINT draws).
3. NOT RUN BY RULE and the label: exercised only synthetically.

Of these, only (1) could make the registered run stop on a defect no rehearsal saw. (2) and (3) do not depend on the real data.

## 3. R1 and R2

**R1: FIXED.**

| Case | Result |
|---|---|
| `inputs <dir> <freeze commit> --rehearsal` | REFUSED: "a rehearsal stage takes '-' …" |
| `inputs <dir> - --rehearsal` after a freeze | REFUSED: "a freeze record exists" |
| Before a freeze, `inputs <plan's run dir> - --rehearsal` | REFUSED: "the plan's own (registered) run directory"; the directory was never created |
| `partq_ledger.sh rehearsal <plan's run dir>` | REFUSED |

- **A registered run in a former rehearsal directory (clone C).** The rehearsal ledger and the rehearsal `inputs` ran in directory X. A later plan was then written naming X, frozen, and given a Decision 2. The registered `inputs` and `partition` launched into X are both **REFUSED**: "inputs.complete.json … is a record of mode 'rehearsal'" (`require_one_mode`).

**R2: FIXED** (`t2_freeze_d.py`). These run the real `cmd_freeze` with the caps matched to a copy of the public measuring record and a synthetic counting record, each case with no freeze record present:

| Counting record | Freeze |
|---|---|
| `partition` over cap | **REFUSED** ("not within: partition …") |
| `analysis` over cap | **REFUSED** |
| `within_cap` missing on `regeneration` | **REFUSED** |
| Made against another plan file hash | **REFUSED** (rehearsal gate) |
| Everything within cap | Froze |

- Completion records carry `within_cap`, and the caps are stated as frozen (`CAP_SENTENCE`).
- **A killed process is charged by the next launch** from its heartbeat marker. This is a lower bound, within the 10 s heartbeat interval.

Note on how my test D was run: my first run let the "all within" case write a freeze record first, so the later cases were refused for that reason instead. That attempt is kept as `t1` part D; the corrected run is `t2`.

## 4. The attempt-1 files moved aside, and the charges

- `freeze/attempt1-refused-at-inputs/{partq_plan.json, partq_freeze_record.json}` are picked up by nothing:
  - the Part Q frozen set covers `partq/`, `common/` and `launch/partq_*` only;
  - Part T excludes `freeze/`;
  - `foreign_freeze_records` globs one level (`studies/*/freeze/*freeze_record*.json`) and skips `p10is2`;
  - `verify_freeze_record`, `Plan.load` and `write_candidate` read only the fixed paths `freeze/partq_plan.json` and `freeze/partq_freeze_record.json`.
- The attempt-1 Decision 2 (`results/p10is2-partq-freeze-*/DECISION_2_PARTQ.md`, naming `cb62815`) stays committed, but `require_decision_2` matches only a file naming the *new* freeze commit. A launch given the old commit is refused, because HEAD's frozen files differ from it.
- The new plan names `experiments/P10IS2-Q-registered2-20261118`. It pins the shared ledger `62f811161420…`, which is the current live hash, and its caps are 22.49 h total.
- The attempt-1 run directory `experiments/P10IS2-Q-registered-20261118` holds `stages/inputs.refused.json` (no mode field, written by older code) and a ledger with **13.09 s** charged ("inputs"; 16 s was the wall time). Being a separate directory, it cannot interfere with attempt 2.

## Findings

**F1 (REQUIRED; `partq/real_stages.py`, `run_stage` analysis body → `write_manifest`, and `pipeline.hashes_of`): the Part Q manifest is wrong as written.**
- It is written by the analysis while its own process is still running, so it hashes files that change or vanish afterwards.
- In clone A, the manifest's 141 entries include:
  - `stages/analysis.running.json`, which is **missing** afterwards (the heartbeat marker, new in `ea105e3`);
  - `charged_ledger.json` and the manifest's own `manifest.json`, **with other hashes now**.
- And it leaves out `analysis/manifest.json` and `stages/analysis.complete.json`.
- Part T reads only the manifest file's own hash, so the run is not stopped. But ADR section 4.1 ("every output is listed with its hash") and any recomputation that checks the listed files would fail.
- Fix: `hashes_of` excludes `stages/`, `charged_ledger.json`, `*/manifest.json` and `manifest.json`. Alternatively, record in Decision 2 that these volatile files are outside the manifest's guarantee.

**F2 (REQUIRED before the freeze, no code change): verify the shared ledger against the real grid once before freezing.**
- The registered `inputs` stage is the **only** place where the 144 windows of `data/p10i-shared/panel_ledger.json` meet the real tokenizer's grid (`verify_study_ledger`). No rehearsal does it.
- A mismatch there after the freeze would end attempt 2 at stage 1 again.
- Run, with the packages (as the ledger command does): `real_stages.window_candidates(build_world(…, light=True), cfg)` followed by `step8.verify_study_ledger(cfg, <shared ledger>, marker, ordinary)`. Record the result, and also run P10-I-S3's reader on the live file (the a14 procedure).

**F3 (REQUIRED, a record in Decision 2): charges not in the total cap.**
- The total cap of 22.49 h uses the measuring record's pre-freeze charge, 6,698.09 s.
- Not counted:
  - the first measuring attempt, 959.3 s;
  - the counting rehearsals;
  - the ledger command;
  - attempt 1, 13.09 s charged, in its own run directory.
- The cap is therefore stricter than the rule, not looser. But the charge ledger of ruling L2 is incomplete, and nothing carries attempt 1's seconds into attempt 2's ledger.
- Record each figure in Decision 2 of attempt 2.

**A1 (ADVISORY; `freeze.cmd_freeze`):** the freeze trusts the counting record's own fields. My hand-typed record with `within_cap: true` and 1 s per stage froze. Recompute `within_cap` from the seconds and the caps, and check the record against the counting run directory's ledger and completion records.

**A2 (ADVISORY; `real_stages.settle_killed`):** a dead process whose PID has since been reused makes the stage refuse ("still running") until the marker is removed by hand. Compare the process start time as well as the PID.

## Scripts (verbatim; scratch deleted)

### t1_e2e.py
```python
"""REAUDIT3 of 039b1d4. Own fully frozen scratch clones (git archive 039b1d4 + git init), registered-mode plan built by the code with
its import walk, freeze record, committed Decision 2; every stage launched through partq_registered.sh in a fresh process. Fakes: ONLY
downloads and teachers (the implementer's test module p10is2_e2e_world.install() via a fake `uv` on PATH; no PYTHONPATH).
A: the eight stages as a registered launch calls them -> label; then the Part Q manifest checked against the files on disk.
B: the rehearsal flag on registered launches (freeze commit given; '-' after a freeze; '-' into the plan's run dir; ledger rehearsal into
   the plan's run dir).
C: a registered run pointed (by a later plan) at a directory that already holds rehearsal records.
D: the freeze's counting-rehearsal checks (real cmd_freeze up to and including the within_cap check, real caps from a COPY of the public
   measuring record): a record over cap on one stage, and one made against another plan file hash."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
src, base, py, meas = sys.argv[1], Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
GITC = ["-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
def git(r, *a): return subprocess.run(["git", "-C", str(r), *GITC, *a], capture_output=True, text=True, check=True).stdout.strip()
SETUP = r'''
import sys, json; from pathlib import Path
r=Path(sys.argv[1]); run=Path(sys.argv[2]); led=Path(sys.argv[3]); base=Path(sys.argv[4]); write_freeze=sys.argv[5]=="1"
sys.path[:0]=[str(r), str(r/'src'), str(r/'tests')]
import p10is2_e2e_world as world
from studies.p10is2.common import core, plan as planmod
from studies.p10is2.common.panel_ledger import RowMap
from studies.p10is2.partq import plan as qplan, real_stages, step8, pkgmanifest
from arborlm.io import write_json, file_sha256
cp=r/core.CONFIG_Q
if not led.is_file():
    cp.write_text(world.scaled_config_text(cp.read_text(), led)); cfg=core.load_config('Q', cp)
    w=world.make_world(cfg, r, base/('w_'+r.name)); _g, m, o = real_stages.window_candidates(w, cfg)
    step8.write_study_ledger(cfg, 'test', led, m, o, row_map=RowMap.from_rows(w.wikitext_rows['validation']))
cfg=core.load_config('Q', cp)
d=base/('durable_'+r.name)/'fakepkg-1.0.dist-info'; d.mkdir(parents=True, exist_ok=True); (d/'METADATA').write_text('Name: fakepkg\nVersion: 1.0\n')
data=base/('in_'+r.name+'.bin'); data.write_bytes(b'abc')
inputs={'data': {'path': str(data), 'sha256': file_sha256(data)}, pkgmanifest.KEY: pkgmanifest.build_manifest(d.parent, None)}
(r/core.FREEZE_DIR).mkdir(parents=True, exist_ok=True)
if (r/core.PLAN_Q).exists(): (r/core.PLAN_Q).unlink()
rec=qplan.build_candidate(r, run, cfg, inputs=inputs, walk=planmod.import_walk(r, 'Q')); write_json(r/core.PLAN_Q, core.jsonable(rec))
if write_freeze: write_json(r/core.FREEZE_RECORD_Q, {'kind':'freeze_record','plan_file_sha256': file_sha256(r/core.PLAN_Q)})
'''
def setup(r, run, led, freeze_it):
    subprocess.run([py, "-B", "-c", SETUP, str(r), str(run), str(led), str(base), "1" if freeze_it else "0"], check=True, capture_output=True, text=True, cwd=r)
def new_clone(name):
    r = base / name
    subprocess.run(f"rm -rf '{r}' && mkdir -p '{r}' && git -C '{src}' archive 039b1d4 | tar -x -C '{r}'", shell=True, check=True)
    for f in (r / "studies/p10is2/freeze/partq_plan.json", r / "studies/p10is2/freeze/partq_freeze_record.json"):
        f.unlink(missing_ok=True)
    git(r, "init", "-q"); git(r, "add", "-A"); git(r, "commit", "-q", "-m", "base")
    return r
def commit_freeze(r):
    git(r, "add", "-A"); git(r, "commit", "-q", "-m", "freeze"); c = git(r, "rev-parse", "HEAD")
    dd = r / "results/p10is2-partq-freeze-20261201"; dd.mkdir(parents=True, exist_ok=True); (dd / "DECISION_2_PARTQ.md").write_text(f"freeze {c}\nDECISION: RUN\n")
    git(r, "add", "-A"); git(r, "commit", "-q", "-m", "d2"); return c
bindir = base / "bin"; bindir.mkdir(parents=True, exist_ok=True)
(bindir / "uv").write_text('#!/bin/sh\nwhile [ "$1" != "python" ]; do shift; done\nshift\nshift\nunset PYTHONPATH\nexec "$E2E_PY" "$E2E_HOOK" "$@"\n'); os.chmod(bindir / "uv", 0o755)
def env_for(r):
    e = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    e.update(PATH=f"{bindir}:{e['PATH']}", E2E_PY=py, E2E_HOOK=str(r / "tests/p10is2_e2e_hook.py"), E2E_SRC=str(r / "src"), E2E_ROOT=str(r), E2E_TESTS=str(r / "tests"), PYTHONDONTWRITEBYTECODE="1")
    return e
def sh(r, script, *argv):
    p = subprocess.run(["sh", str(r / "studies/p10is2/launch" / script), *argv], cwd=r, env=env_for(r), capture_output=True, text=True, timeout=900)
    errs = [l for l in p.stderr.splitlines() if "Warning" not in l and "_conversion" not in l]
    return p.returncode, (errs[-1][:190] if errs else "")
def comp(run, st):
    f = run / "stages" / f"{st}.complete.json"; return json.loads(f.read_text()) if f.is_file() else None
STAGES = ["inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis"]
# ---- A
rA = new_clone("A"); runA = base / "run_A"; setup(rA, runA, base / "led_A.json", True); cA = commit_freeze(rA)
for st in STAGES:
    rc, err = sh(rA, "partq_registered.sh", st, str(runA), cA); c = comp(runA, st) or {}
    print(f"[A] {st}: exit {rc} {c.get('status')} mode={c.get('mode')} within_cap={c.get('within_cap')} {err if rc else ''}")
print("[A] label:", json.loads((runA / "qualification.json").read_text())["label"], "| tree clean:", git(rA, "status", "--porcelain") == "")
man = json.loads((runA / "manifest.json").read_text())["files"]
missing = sorted(k for k in man if not (runA / k).is_file()); differ = sorted(k for k in man if (runA / k).is_file() and hashlib.sha256((runA / k).read_bytes()).hexdigest() != man[k])
unlisted = sorted(str(f.relative_to(runA)) for f in runA.rglob("*") if f.is_file() and "sealed" not in f.parts and str(f.relative_to(runA)) not in man)
print(f"[A] Part Q manifest: {len(man)} files listed; listed but missing now: {missing}; listed with another hash now: {differ}; on disk but unlisted: {unlisted[:8]}")
print("[A] stages/ left:", sorted(p.name for p in (runA / "stages").iterdir()))
# ---- B (pre-freeze clone for the '-' cases; frozen clone A for the commit cases)
rB = new_clone("B"); runB = base / "run_B_registered"; setup(rB, runB, base / "led_B.json", False); git(rB, "add", "-A"); git(rB, "commit", "-q", "-m", "plan")
print("[B] A frozen: inputs <registered dir> <freeze commit> --rehearsal:", sh(rA, "partq_registered.sh", "inputs", str(base / "run_A_new"), cA, "--rehearsal"))
print("[B] A frozen: inputs <other dir> - --rehearsal (freeze record exists):", sh(rA, "partq_registered.sh", "inputs", str(base / "reh_A"), "-", "--rehearsal"))
print("[B] pre-freeze: inputs <plan's run dir> - --rehearsal:", sh(rB, "partq_registered.sh", "inputs", str(runB), "-", "--rehearsal"))
print("[B] pre-freeze: ledger rehearsal <plan's run dir>:", sh(rB, "partq_ledger.sh", "rehearsal", str(runB)))
print("    plan's run dir exists after both:", runB.exists())
# ---- C: a rehearsal dir, then a later plan naming it, frozen, registered launch into it
rC = new_clone("C"); rehC = base / "reh_C"; setup(rC, base / "run_C_first", base / "led_C.json", False); git(rC, "add", "-A"); git(rC, "commit", "-q", "-m", "plan1")
print("[C] rehearsal ledger + inputs into reh_C:", sh(rC, "partq_ledger.sh", "rehearsal", str(rehC)), sh(rC, "partq_registered.sh", "inputs", str(rehC), "-", "--rehearsal"))
setup(rC, rehC, base / "led_C.json", True); cC = commit_freeze(rC)
print("[C] registered inputs into the (former) rehearsal dir:", sh(rC, "partq_registered.sh", "inputs", str(rehC), cC))
print("[C] registered partition into it:", sh(rC, "partq_registered.sh", "partition", str(rehC), cC))
# ---- D: the freeze's counting-rehearsal checks
rD = new_clone("D"); runD = base / "run_D"; setup(rD, runD, base / "led_D.json", False); git(rD, "add", "-A"); git(rD, "commit", "-q", "-m", "plan")
CODE = r'''
import sys, json, argparse; from pathlib import Path
r=Path(sys.argv[1]); meas=sys.argv[2]; base=Path(sys.argv[3]); sys.path[:0]=[str(r), str(r/'src')]
from studies.p10is2.common import core; from studies.p10is2.partq import freeze, plan as qplan
from arborlm.io import file_sha256
sha=file_sha256(r/core.PLAN_Q)
def counting(plan_sha, over):
    st={s: {"status":"COMPLETE","seconds":1.0,"within_cap": (s!=over)} for s in qplan.REHEARSAL_STAGES}
    rec={**core.envelope("rehearsal","Q"),"kind_of_rehearsal":"counting","status":"COMPLETE","plan_file_sha256":plan_sha,"caps_provisional":False,"stages":st,"forced":{"pause_resume":True,"paused_identity_restore":True}}
    p=base/("cnt_%s_%s.json"%(over,plan_sha[:6])); core.write_record(p, rec, overwrite=True); return p
for label, c in (("all within cap", counting(sha, None)), ("partition over cap", counting(sha, "partition")), ("another plan hash", counting("f"*64, None))):
    try:
        freeze.cmd_freeze(argparse.Namespace(repo=str(r), measuring_rehearsal=meas, counting_rehearsal=str(c), attest_sealed_unopened="lead,implementer,auditor", seal_broken=False)); print("[D]", label, "-> FROZE")
    except core.StageRefused as e:
        print("[D]", label, "->", str(e)[:170])
'''
p = subprocess.run([py, "-B", "-c", CODE, str(rD), str(meas), str(base)], capture_output=True, text=True, timeout=900, cwd=rD)
print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "[D]" in l or "Error" in l)[:2500])
```

### t2_freeze_d.py
```python
"""Part D again (my first run let the 'all within cap' case write a freeze record first, so the later cases were refused for that reason):
each case on clone D with the freeze record removed before it; order: over cap, other plan hash, a stage with within_cap missing, all within."""
import sys, argparse; from pathlib import Path
r=Path(sys.argv[1]); meas=sys.argv[2]; base=Path(sys.argv[3]); sys.path[:0]=[str(r), str(r/'src')]
from studies.p10is2.common import core; from studies.p10is2.partq import freeze, plan as qplan
from arborlm.io import file_sha256
sha=file_sha256(r/core.PLAN_Q)
def counting(plan_sha, over, drop=False):
    st={s: {"status":"COMPLETE","seconds":1.0,"within_cap": (s!=over)} for s in qplan.REHEARSAL_STAGES}
    if drop: st["regeneration"].pop("within_cap")
    rec={**core.envelope("rehearsal","Q"),"kind_of_rehearsal":"counting","status":"COMPLETE","plan_file_sha256":plan_sha,"caps_provisional":False,"stages":st,"forced":{"pause_resume":True,"paused_identity_restore":True}}
    p=base/("cnt2_%s_%s_%s.json"%(over,plan_sha[:6],drop)); core.write_record(p, rec, overwrite=True); return p
for label, c in (("partition over cap", counting(sha, "partition")), ("analysis over cap", counting(sha, "analysis")), ("another plan hash", counting("f"*64, None)), ("within_cap missing on regeneration", counting(sha, None, True)), ("all within cap", counting(sha, None))):
    (r/core.FREEZE_RECORD_Q).unlink(missing_ok=True)
    try:
        freeze.cmd_freeze(argparse.Namespace(repo=str(r), measuring_rehearsal=meas, counting_rehearsal=str(c), attest_sealed_unopened="lead,implementer,auditor", seal_broken=False)); print("[D]", label, "-> FROZE")
    except core.StageRefused as e:
        print("[D]", label, "->", str(e)[:200])
(r/core.FREEZE_RECORD_Q).unlink(missing_ok=True)
```

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
