"""Re-audit: P6-E per-worker durations on a SYNTHETIC cell after the fixes (recheck attempt 2).

Differences from check_p6e_budget.py (kept unchanged):
- timing workers now require ``spec["source"]`` (source-archive and p6 module hashes checked at
  worker end); recheck attempt 1 omitted it and failed with KeyError (kept as
  check_p6e_budget-recheck.FAILED-attempt1.out.txt). This is an auditor-script gap.
- the synthetic panel has the registered 512 rows in the timing phases too, because timing
  workers now replay the unmodified model's NLL on the panel for all three kinds (clarification
  19), so the replay cost is included in the worker time.

Random-weight models with the registered shapes; no real checkpoint or data.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget_recheck.py \
        <scratch> {screen|confirm}
"""

import sys
import time
from pathlib import Path

PAIR = (101, 301, 501)
PLANS = {
    "screen": {"flat": ["F0", "F1", "F2"],
               "fixed_tree": ["T0", "T1", "T2", "T3", "T4", "T5"],
               "learned_tree": ["T0", "T1", "T2", "T3", "T4", "T5"]},
    "confirm": {"flat": ["F0", "F1"], "fixed_tree": ["T0", "T4"], "learned_tree": ["T0", "T4"]},
}


def main() -> None:
    start = time.monotonic()
    scratch, phase = Path(sys.argv[1]), sys.argv[2]
    scratch.mkdir(parents=True, exist_ok=True)
    from arborlm import p6_common as common
    from arborlm import p6_timing_study as ts
    from arborlm.io import read_json
    from arborlm.p6_stage import p6_source_hashes, SPEC
    from arborlm.records import record_source

    snap_dir = scratch / f"src-{phase}"
    snap_dir.mkdir(exist_ok=True)
    snapshot = record_source(snap_dir, Path.cwd(), spec=SPEC)
    source = {"source_archive_sha256": snapshot["archive"]["sha256"],
              "p6_source_sha256": p6_source_hashes()}
    child = scratch / phase
    child.mkdir(exist_ok=True)
    args = common.StudyArgs(
        data_dir=scratch, parent_suite=scratch, output_root=scratch, results_root=scratch,
        synthetic=True, pair_count=1, rounds=8, panel_rows=512,
    )
    t = time.monotonic()
    ts.timing_worker({"mode": phase, "args": args.to_json(), "plan": PLANS[phase],
                      "source": source}, child, PAIR)
    rec = read_json(child / "result.json")
    print(f"timing worker {phase} ({len(ts.canonical_entities(PLANS[phase]))} entities, 8 rounds,"
          f" 512-row synthetic panel replay): worker {time.monotonic()-t:.1f} s,"
          f" schedule {rec['timing_seconds']:.1f} s")
    print("  integrity replay bitwise:",
          {k: v["bitwise_equal"] for k, v in rec["integrity_replay_before_timing"].items()})
    print("  source recheck:", rec["source_recheck_at_worker_end"])
    usable = sum(r["usable"] for r in rec["timing"]["records"])
    print(f"  usable measurements: {usable}/{len(rec['timing']['records'])}")
    print(f"process wall incl. imports: {time.monotonic()-start:.1f} s")


if __name__ == "__main__":
    main()
