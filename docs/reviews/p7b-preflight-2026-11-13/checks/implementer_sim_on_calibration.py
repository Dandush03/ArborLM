"""Scratch harness (auditor role): run the implementer's simulator (``p7b_sim.simulate_checkpoint``,
the complete per-checkpoint plan) on the REAL CALIBRATION trace of each of the 18 registered
re-simulation checkpoints, treated as if it were an evaluation stream, with the implementer's own
layouts and count-preserving nulls; write records in the simulate-worker result format into a
scratch folder. Used only to validate tools/independent_resim.py. No evaluation trace is opened
(an open() spy fails the run if a non-calibration trace file is touched). Not a registered stage.

argv: scratch_dir jobs seedset(A|B)
"""

import builtins
import json
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))


def _spy() -> None:
    real_open = builtins.open
    real_rb = pathlib.Path.read_bytes

    def guard(name: str) -> None:
        if "/traces/" in name and "calib_" not in Path(name).name:
            raise RuntimeError(f"non-calibration trace touched: {name}")

    def op(file, *a, **k):  # type: ignore[no-untyped-def]
        guard(str(file))
        return real_open(file, *a, **k)

    def rb(self):  # type: ignore[no-untyped-def]
        guard(str(self))
        return real_rb(self)

    builtins.open = op
    pathlib.Path.read_bytes = rb


def one(task: tuple[str, str, str]) -> dict:
    label, scratch, seedset = task
    _spy()
    from arborlm import p7b_core as core
    from arborlm import p7b_layout as L
    from arborlm import p7b_sim as sim
    from arborlm.io import file_sha256, write_json

    identity = core.load_identity(REPO)
    pair, kind = core.parse_label(label)
    index = core.cell_index(pair, kind)
    cal = L.CalibrationTrace.from_identity(identity, label)
    t0 = time.monotonic()
    built, _ = L.build_layouts(cal)
    t_build = time.monotonic() - t0
    table = L.hash_table(built)
    orders = {b.key(): b.order for b in built}
    seeds = core.STREAM_A_NULL_SEEDS if seedset == "A" else core.STREAM_B_NULL_SEEDS
    counts = cal.counts()
    nulls, info = core.null_streams(counts, seeds, index)
    t1 = time.monotonic()
    record = sim.simulate_checkpoint(
        trace=sim.EvaluationTrace(cal.selected, cal.branches, kind, label, seedset),
        layouts=sim.LayoutSet(orders),
        null_selected=dict(zip(core.STREAMS_NULL, nulls, strict=True)),
    )
    t_sim = time.monotonic() - t1
    out = Path(scratch)
    table_path = out / "hash_tables" / f"{label}.json"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    (out / "simulate" / "workers").mkdir(parents=True, exist_ok=True)
    write_json(table_path, {"layouts": {label: table}})
    write_json(
        out / "simulate" / "workers" / f"{label}.result.json",
        {
            "schema": core.SCHEMA_SIM,
            "outcome": "completed",
            "label": label,
            "kind": kind,
            "stream": seedset,
            "null_streams": [
                {k: d[k] for k in ("replicate_seed", "generator_seed", "stream_sha256")} for d in info
            ],
            "trace": {"files": {"selected": {"sha256": identity.recorded_sha(label, "calibration.selected")}}},
            "layout_binding": {"hash_table_sha256": "FILLED-BY-MAIN"},
            "record": record,
            "SCRATCH": "implementer simulator on a CALIBRATION trace treated as a stream; not a registered record",
        },
    )
    return {"label": label, "build_seconds": t_build, "simulate_seconds": t_sim, "table": table}


def main() -> int:
    scratch, jobs, seedset = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    from arborlm import p7b_core as core
    from arborlm.io import file_sha256, read_json, write_json

    labels = core.independent_selection()
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(one, [(lb, str(scratch), seedset) for lb in labels]))
    table_path = scratch / "layout_hash_table.json"
    write_json(table_path, {"layouts": {r["label"]: r["table"] for r in results}})
    digest = file_sha256(table_path)
    for r in results:
        p = scratch / "simulate" / "workers" / f"{r['label']}.result.json"
        data = read_json(p)
        data["layout_binding"]["hash_table_sha256"] = digest
        write_json(p, data)
    summary = {
        "labels": labels,
        "wall_seconds": time.monotonic() - started,
        "jobs": jobs,
        "simulate_seconds_sum": sum(r["simulate_seconds"] for r in results),
        "build_seconds_sum": sum(r["build_seconds"] for r in results),
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
