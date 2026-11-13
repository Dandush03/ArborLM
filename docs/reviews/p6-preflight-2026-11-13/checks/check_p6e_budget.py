"""Auditor feasibility estimate of P6-E per-worker durations on a SYNTHETIC cell (attempt 2).

Random-weight models with the registered shapes; real checkpoints, data and outcomes are not
touched. Each phase runs in its own process (timing_worker calls configure_cpu itself, which
torch allows only once per process; attempt 1 failed on that, see *.FAILED-attempt1.*).

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget.py \
        <scratch> {eq|screen|confirm}

Exploratory, single run, one machine: not registered evidence, only a check of whether the
approved caps are plausibly reachable by the code as written.
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
    from arborlm.io import read_json

    if phase == "eq":
        from arborlm import p6_equivalence as eq
        from arborlm.engine import configure_cpu

        configure_cpu()
        t = time.monotonic()
        source = common.load_synthetic_cell(PAIR, rows=512)
        print(f"synthetic cell load (512 panel rows): {time.monotonic()-t:.1f} s")
        t = time.monotonic()
        out = scratch / "eq"
        out.mkdir(exist_ok=True)
        result = eq.run_cell(source, out, binding="hash")
        classes = {k: {v: r["class"] for v, r in c["variants"].items()}
                   for k, c in result["checkpoints"].items()}
        print(f"equivalence run_cell, full-size synthetic panel: {time.monotonic()-t:.1f} s")
        print(f"  classes on synthetic: {classes}")
    else:
        from arborlm import p6_timing_study as ts

        child = scratch / phase
        child.mkdir(exist_ok=True)
        args = common.StudyArgs(
            data_dir=scratch, parent_suite=scratch, output_root=scratch, results_root=scratch,
            synthetic=True, pair_count=1, rounds=8, panel_rows=8,
        )
        t = time.monotonic()
        ts.timing_worker({"mode": phase, "args": args.to_json(), "plan": PLANS[phase]}, child, PAIR)
        rec = read_json(child / "result.json")
        print(f"timing worker {phase} ({len(ts.canonical_entities(PLANS[phase]))} entities, 8 rounds):"
              f" worker {time.monotonic()-t:.1f} s, schedule {rec['timing_seconds']:.1f} s")
        meds = {r["entity"]: round(r["median_ns"] / 1e3) for r in rec["timing"]["records"]
                if r["workload"] == "W8" and r["scope"] == "addition_forward"}
        usable = sum(r["usable"] for r in rec["timing"]["records"])
        print(f"  W8 addition_forward medians, us (synthetic, exploratory): {meds}")
        print(f"  usable measurements: {usable}/{len(rec['timing']['records'])}")
    print(f"process wall incl. imports: {time.monotonic()-start:.1f} s")


if __name__ == "__main__":
    main()
