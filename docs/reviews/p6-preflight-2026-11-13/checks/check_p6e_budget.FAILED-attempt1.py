"""Auditor feasibility estimate of P6-E per-worker durations on a SYNTHETIC cell.

Random-weight models with the registered shapes; real checkpoints, data and outcomes are not
touched. Output directories go to the path given as argv[1] (a scratch directory).

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget.py <scratch>

Exploratory, single run, one machine: not registered evidence, only a check of whether the
approved caps are plausibly reachable by the code as written.
"""

import sys
import time
from pathlib import Path

from arborlm import p6_common as common
from arborlm import p6_equivalence as eq
from arborlm import p6_timing_study as ts
from arborlm.engine import configure_cpu


def main() -> None:
    scratch = Path(sys.argv[1])
    scratch.mkdir(parents=True, exist_ok=True)
    configure_cpu()
    pair = (101, 301, 501)
    t = time.monotonic()
    source = common.load_synthetic_cell(pair, rows=512)
    print(f"synthetic cell load (512 panel rows, 3 NLL evaluations): {time.monotonic()-t:.1f} s")

    t = time.monotonic()
    eq_dir = scratch / "eq"
    eq_dir.mkdir(exist_ok=True)
    result = eq.run_cell(source, eq_dir, binding="hash")
    print(f"equivalence run_cell (full-size synthetic panel): {time.monotonic()-t:.1f} s; "
          f"classes={ {k: {v: r['class'] for v, r in c['variants'].items()} for k, c in result['checkpoints'].items()} }")

    for label, plan in (
        ("screen (15 entities)", {"flat": ["F0", "F1", "F2"],
                                  "fixed_tree": ["T0", "T1", "T2", "T3", "T4", "T5"],
                                  "learned_tree": ["T0", "T1", "T2", "T3", "T4", "T5"]}),
        ("confirm (6 entities)", {"flat": ["F0", "F1"], "fixed_tree": ["T0", "T4"],
                                  "learned_tree": ["T0", "T4"]}),
    ):
        child = scratch / label.split()[0]
        child.mkdir(exist_ok=True)
        args = common.StudyArgs(
            data_dir=scratch, parent_suite=scratch, output_root=scratch, results_root=scratch,
            synthetic=True, pair_count=1, rounds=8, panel_rows=8,
        )
        spec = {"mode": label.split()[0], "args": args.to_json(), "plan": plan}
        t = time.monotonic()
        ts.timing_worker(spec, child, pair)
        from arborlm.io import read_json
        rec = read_json(child / "result.json")
        print(f"timing worker {label}, 8 rounds: {time.monotonic()-t:.1f} s "
              f"(timing schedule alone {rec['timing_seconds']:.1f} s)")
        meds = {}
        for r in rec["timing"]["records"]:
            if r["workload"] == "W8" and r["scope"] == "addition_forward":
                meds[r["entity"]] = r["median_ns"] / 1e3
        print("  W8 addition_forward medians (us, synthetic, exploratory):",
              {k: round(v) for k, v in meds.items()})


if __name__ == "__main__":
    main()
