# ruff: noqa: E501
"""Apply the human lead's approved 1-hour extension of S1's evaluate cap to the registered run's LEDGER (the only file the cap arithmetic reads that is not frozen). See docs/decisions/ADR-0024-addendum-evaluate-cap-extension.md.

``stage_cap_seconds`` is ``min(plan cap - spent on the cap key, ledger remaining)``; the plan's cap (``stage_caps.evaluate_hours`` = 1.0) is frozen and is NOT changed. The extension appends TWO entries to the ledger and
changes no existing one:

* ``{"stage": "evaluate", "seconds": -3600.0}``   — a credit on the evaluate cap key (spent on it falls by one hour);
* ``{"stage": "evaluate-cap-extension-offset", "seconds": +3600.0}`` — an equal debit on a stage that belongs to NO cap key, so the TOTAL charged seconds (and so the total cap) are exactly as before.

Both name the SHA-256 of the committed approval record. The ledger's pre-image is written to a NEW file beside it first. Nothing is deleted, moved or overwritten except the ledger's own rewrite with its old entries intact.

Usage (dry run is the default; ``--apply`` writes):
  PYTHONPATH=<worktree>/src:<worktree> timeout 300 <venv python> results/p10is1-evaluate-cap-extension-20261121/apply_extension.py --ledger <experiments>/P10IS1-ledger.json [--apply]
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
APPROVAL = HERE / "APPROVAL.md"
OFFSET_STAGE = "evaluate-cap-extension-offset"
FREEZE_COMMIT = "46bf55a5cc0eda11b7201c4ab777e69c6970c4cd"
S1_PROCESS_MARK = "studies.p10is1"  # any command line that runs a module of this study (the registered stages and their workers)


def live_s1_processes(table: list[tuple[int, int, str]] | None = None) -> list[str]:
    """R2: command lines of every ``studies.p10is1`` process alive other than this one's own family. ``Ledger.charge`` is read-modify-write, so a stage charging while the ledger is rewritten could silently drop the two
    extension entries (or the extension could drop its charge): the credit is applied only with S1 stopped."""
    from studies.p10is1 import machine

    rows = table if table is not None else machine.ps_table()
    import os

    own = machine.family(rows, os.getpid())
    return [f"{p}: {c}" for p, _, c in rows if p not in own and S1_PROCESS_MARK in c]


def read_approval(path: Path) -> tuple[float, str]:
    """The extension in hours and the SHA-256 of the approval record; refuses a record without the machine-read lines."""
    text = path.read_text(encoding="utf-8")
    lines = {ln.split(":", 1)[0].strip(): ln.split(":", 1)[1].strip() for ln in text.splitlines() if ln.startswith(("EXTENSION:", "FREEZE_COMMIT:", "TOTAL_CAP:"))}
    if lines.get("EXTENSION") != "evaluate_hours +1.0" or lines.get("FREEZE_COMMIT") != FREEZE_COMMIT or lines.get("TOTAL_CAP") != "unchanged":
        raise SystemExit(f"refused: {path} does not carry the machine-read lines of the approval (EXTENSION: evaluate_hours +1.0, FREEZE_COMMIT, TOTAL_CAP: unchanged)")
    if "Approve 1 h" not in text:
        raise SystemExit(f"refused: {path} does not quote the human lead's answer")
    return 1.0, hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None, process_table: list[tuple[int, int, str]] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--approval", default=str(APPROVAL))
    ap.add_argument("--plan", default=str(REPO / "studies" / "p10is1" / "freeze" / "plan.json"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    from arborlm.io import write_json
    from studies.p10is1 import core, stages
    from studies.p10is1 import plan as planmod

    hours, sha = read_approval(Path(a.approval))
    secs = hours * 3600.0
    ledger_path = Path(a.ledger)
    led = core.Ledger(ledger_path, float(json.loads(ledger_path.read_text())["total_seconds"]))
    entries = led.entries()  # refuses a file that is not a P10IS1 ledger
    if any(e["stage"] == OFFSET_STAGE for e in entries):
        raise SystemExit("refused: the extension has already been applied to this ledger (an entry of the offset stage exists): it is applied once")
    plan = planmod.Plan.load(Path(a.plan))
    before = {"total_charged_s": led.charged(), "evaluate_key_spent_s": sum(led.charged(s) for s, k in stages.CAP_KEY.items() if k == "evaluate"), "evaluate_cap_remaining_s": stages.stage_cap_seconds(plan, "evaluate", led), "baselines_cap_remaining_s": stages.stage_cap_seconds(plan, "baselines", led)}
    now = datetime.now(UTC).isoformat()
    run = f"EXTENSION evaluate_hours +{hours} approval-sha256={sha}"
    new = [
        {"run": run, "seconds": -secs, "stage": "evaluate", "utc": now, "note": "credit on the evaluate cap key: the human lead's approved +1 h (a ledger credit; the plan's frozen cap is unchanged)"},
        {"run": run, "seconds": secs, "stage": OFFSET_STAGE, "utc": now, "note": "equal debit on a stage of no cap key: the TOTAL charged seconds are unchanged"},
    ]
    alive = live_s1_processes(process_table)
    out = {"s1_processes_alive": alive, "plan_evaluate_hours": plan.data["stage_caps"]["evaluate_hours"], "approval_sha256": sha, "before": before, "new_entries": new, "ledger_total_cap_s": led.total_seconds}
    if not a.apply:
        print(json.dumps({"dry_run": True, **out}, indent=2, sort_keys=True))
        return 0
    if alive:
        raise SystemExit("refused: a studies.p10is1 process is alive (the ledger would be rewritten under a running stage); stop S1 first, nothing was written:\n" + "\n".join(alive))
    pre = ledger_path.with_name(ledger_path.name + ".before-evaluate-cap-extension")
    if pre.exists():
        raise SystemExit(f"refused: {pre} exists")
    pre.write_text(ledger_path.read_text(), encoding="utf-8")  # the pre-image, a NEW file
    write_json(ledger_path, {"study": core.STUDY, "kind": "ledger", "schema": core.SCHEMA, "total_seconds": led.total_seconds, "entries": [*entries, *new]})
    led2 = core.Ledger(ledger_path, led.total_seconds)
    after = {"total_charged_s": led2.charged(), "evaluate_key_spent_s": sum(led2.charged(s) for s, k in stages.CAP_KEY.items() if k == "evaluate"), "evaluate_cap_remaining_s": stages.stage_cap_seconds(plan, "evaluate", led2), "baselines_cap_remaining_s": stages.stage_cap_seconds(plan, "baselines", led2)}
    assert abs(after["total_charged_s"] - before["total_charged_s"]) < 1e-6, "the total charged seconds changed"
    assert led2.entries()[: len(entries)] == entries, "an existing entry changed"
    print(json.dumps({"applied": True, "pre_image": str(pre), **out, "after": after}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
