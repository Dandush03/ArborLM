"""Recheck script r4 = a4 re-run against f1e8ebb, plus the M1 deadlock probes (Claude Opus 5.5 auditor; not Astra review).

Scratch calibration directory with hand-written records (my counts; nothing trained). Cases:
  A  (a4 as before) every load/row-U_P run finished except T-OQ 32K/4K x2 (no train.json), no stage manifest.
  B  as A but a manifest exists that lists the two T-OQ tasks 'completed' (impossible from the pool, but checks the rule).
  C  as A with a manifest listing them 'killed_cap' -> finalize allowed; what is decided for 32K/4K?
  D  deadlock probe: all runs finished, the driver died before writing the manifest (no manifest). Finalize? Re-launch?
  E  a run stopped at its item cap (train.json status failed, reason ItemCapReached) with a manifest status 'failed'.
Non-DRY (no --dry) so that the real-size cell list is used; the scratch dir is run, experiments and ledger root.
  UV_NO_SYNC=1 nice uv run --locked python -I r4_finalize_midrun.py <worktree root> <scratch dir>
"""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from studies.p10s1 import calibrate, core, stages, timing  # noqa: E402
timing.running_commands = lambda: []  # never read the real process list (P10-S0 is training on this machine)
ROOT = Path(sys.argv[2])


def panel(n, a):
    u = int(round(a * n))
    return {"n": n, "correct": u, "useful": u, "disabled_correct": n // 32, "shuffled_correct": n // 32, "swap_correct": n // 32, "unseen_n": 2048, "unseen_correct": 64}


def write(D, cell, a_of, status="completed", reason=None):
    folder = core.cell_dir(D, cell.label)
    core.write_record(folder / "train.json", {**core.envelope("train"), "label": cell.label, "status": status, "reason": reason, "run_updates": cell.run_updates, "wall_seconds": 1.0})
    if status != "completed":
        return
    for u in calibrate.calibration_snapshots(cell):
        a = a_of(u)
        core.write_record(core.eval_path(D, cell.label, u), {**core.envelope("eval"), "label": cell.label, "update": u, "reads": {"main": {"panels": {"A": panel(cell.facts, a), "B": panel(cell.facts, a)}}}})


def build(name, held_status=None, held_missing=True, manifest=True, stopped=False):
    D = ROOT / name
    if D.exists():
        shutil.rmtree(D)
    D.mkdir(parents=True)
    held, tasks = [], []
    for c in core.load_search_cells():
        is_held = c.arm == "T-OQ" and (c.facts, c.slots) == (32768, 4096)
        if is_held and held_missing:
            held.append(c.label); tasks.append({"label": c.label, "status": held_status or "completed"}); continue
        if is_held and stopped:
            write(D, c, lambda u: 0.6, status="failed", reason="ItemCapReached: stopped at update 100000 of 524288"); tasks.append({"label": c.label, "status": "failed"}); continue
        write(D, c, lambda u: 0.2 if u < 16384 else 0.6); tasks.append({"label": c.label, "status": "completed"})
    for c in core.row_u_p_cells():
        write(D, c, lambda u, c=c: 0.97 if c.arm == "F-OQ" else 1.0); tasks.append({"label": c.label, "status": "completed"})
    if manifest:
        core.write_record(D / "calibrate-load-row-up" / "manifest.json", {**core.envelope("stage_manifest"), "tasks": tasks})
    return D, held


def fin(D):
    code = stages.main(["calibrate", "--finalize-items", "load,row-up", "--run-dir", str(D), "--experiments-root", str(ROOT), "--ledger-root", str(ROOT)])
    p = D / stages.ITEMS_FILE
    rec = json.loads(p.read_text()) if p.exists() else None
    return code, rec


def show(tag, D, code, rec):
    print(f"[{tag}] exit {code}; items record written: {rec is not None}")
    if rec:
        v = rec["load"].get("32K/4K")
        print(f"     32K/4K: action {v['action']}, U_L {v['u_l']}, status {v['status']}; T-OQ notes {v['arms']['T-OQ'].get('run_notes')}")
        print(f"     stage_complete: {rec.get('stage_complete')}; returns: {rec['returns_to_lead']}")


D, held = build("A", manifest=False); print("A held:", held); show("A no manifest, 2 runs in progress", D, *fin(D))
D, _ = build("B", held_status="completed"); show("B manifest says completed, no train.json", D, *fin(D))
D, _ = build("C", held_status="killed_cap"); show("C manifest killed_cap", D, *fin(D))
D, _ = build("D", held_missing=False, manifest=False); code, rec = fin(D); show("D all runs done, driver died before the manifest", D, code, rec)
relaunch = stages.main(["calibrate", "--items", "load,row-up", "--run-dir", str(D), "--timing", str(D / "nope.json"), "--experiments-root", str(ROOT), "--ledger-root", str(ROOT)])
print(f"     re-launch of items load,row-up into the same dir (expected refusal): exit {relaunch}")
D, _ = build("E", held_missing=False, stopped=True); show("E T-OQ 32K/4K stopped at its item cap", D, *fin(D))
shutil.rmtree(ROOT)
