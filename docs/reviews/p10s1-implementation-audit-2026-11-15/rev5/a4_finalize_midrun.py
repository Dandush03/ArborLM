"""Audit script a4 (Claude Opus 5.5 auditor; P10-S1 revision 5 implementation audit; not Astra review).

Question: can `stages calibrate --finalize-items load,row-up` (a once-only record) be applied while the item runs are still in
progress, and what does it then decide?

Builds a scratch calibration directory with hand-written records (counts chosen by me; nothing trained): every load-search
and row-U_P cell has finished EXCEPT the two T-OQ runs at 32K/4K, which have no train record yet (as while they are still
running). There is no `calibrate-load-row-up/manifest.json` (the stage has not finished). Then runs the command through
`stages.main`, in process, with the scratch directory as run, experiments and ledger root.

  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root> <scratch dir>
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from studies.p10s1 import calibrate, core, stages  # noqa: E402

D = Path(sys.argv[2])
if D.exists():
    shutil.rmtree(D)
D.mkdir(parents=True)


def panel(n, a):
    u = int(round(a * n))
    return {"n": n, "correct": u, "useful": u, "disabled_correct": n // 32, "shuffled_correct": n // 32, "swap_correct": n // 32, "unseen_n": 2048, "unseen_correct": 64}


def write(cell, a_of):
    folder = core.cell_dir(D, cell.label)
    core.write_record(folder / "train.json", {**core.envelope("train"), "label": cell.label, "status": "completed", "run_updates": cell.run_updates, "wall_seconds": 1.0})
    for u in calibrate.calibration_snapshots(cell):
        a = a_of(u)
        core.write_record(core.eval_path(D, cell.label, u), {**core.envelope("eval"), "label": cell.label, "update": u, "reads": {"main": {"panels": {"A": panel(cell.facts, a), "B": panel(cell.facts, a)}}}})


held = []
for c in core.load_search_cells():
    if c.arm == "T-OQ" and (c.facts, c.slots) == (32768, 4096):
        held.append(c.label)  # still running: no record yet
        continue
    write(c, lambda u: 0.2 if u < 16384 else 0.6)  # flat from 16,384: passes at every candidate
for c in core.row_u_p_cells():
    write(c, lambda u: 0.97 if c.arm == "F-OQ" else 1.0)

print("runs still in progress (no train record):", held)
print("stage manifest present:", (D / "calibrate-load-row-up" / "manifest.json").exists())
code = stages.main(["calibrate", "--finalize-items", "load,row-up", "--run-dir", str(D), "--experiments-root", str(D), "--ledger-root", str(D)])
rec = json.loads((D / stages.ITEMS_FILE).read_text()) if (D / stages.ITEMS_FILE).exists() else None
print("exit code:", code, "| once-only items record written:", rec is not None)
if rec:
    for name, v in rec["load"].items():
        print(f"  {name}: action {v['action']}, U_L {v['u_l']}, status {v['status']}, T-OQ notes {v['arms']['T-OQ']['run_notes']}")
    print("  row U_P:", {k: v["u_p"] for k, v in rec["row_u_p"].items()}, "| returns:", rec["returns_to_lead"])
again = stages.main(["calibrate", "--finalize-items", "load,row-up", "--run-dir", str(D), "--experiments-root", str(D), "--ledger-root", str(D)])
print("second application after the runs finish would be refused (exit 2 expected):", again)
shutil.rmtree(D)
