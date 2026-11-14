"""Re-check (auditor role, Claude Opus 5.5) for items m2 and m10: could the new run-time checks stop
the registered run spuriously on real data?

For EVERY one of the 81 registered checkpoints: build the implementer's layouts from the real
CALIBRATION trace (public calibration-only interface), then run the implementer's complete
per-checkpoint simulation plan (``p7b_sim.simulate_checkpoint``; ``check_group`` inside it now
includes the whole-stream capacity-miss monotonicity of m10) on that same calibration trace treated
as an evaluation stream, with the count-preserving nulls of the chosen seed set; then call
``p7b_sim.check_r1_invariants`` (m2) on the record. Any ``InvariantError`` is recorded, not hidden.
Records for all 81 are written in the simulate-worker format to a scratch folder so that
tools/independent_resim.py can re-check the registered 18 (``--stream-source calibration``).

No evaluation trace and no stream-B trace is opened: an open()/read_bytes() spy aborts on any file
under a ``traces`` folder whose name does not start with ``calib_``. Not a registered stage.
Independent engineering evidence; not Astra validation; not human approval.

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
    from arborlm.io import write_json

    identity = core.load_identity(REPO)
    pair, kind = core.parse_label(label)
    index = core.cell_index(pair, kind)
    cal = L.CalibrationTrace.from_identity(identity, label)
    built, _ = L.build_layouts(cal)
    table = L.hash_table(built)
    orders = {b.key(): b.order for b in built}
    seeds = core.STREAM_A_NULL_SEEDS if seedset == "A" else core.STREAM_B_NULL_SEEDS
    nulls, info = core.null_streams(cal.counts(), seeds, index)
    out: dict = {"label": label, "kind": kind, "table": table}
    t1 = time.monotonic()
    try:
        record = sim.simulate_checkpoint(
            trace=sim.EvaluationTrace(cal.selected, cal.branches, kind, label, seedset),
            layouts=sim.LayoutSet(orders),
            null_selected=dict(zip(core.STREAMS_NULL, nulls, strict=True)),
        )
        out["check_group_m10"] = "passed for every group"
    except core.InvariantError as exc:
        out["check_group_m10"] = f"InvariantError: {exc}"
        return out
    try:
        out["r1_m2"] = sim.check_r1_invariants(record)
    except core.InvariantError as exc:
        out["r1_m2"] = f"InvariantError: {exc}"
    # independent tally of what the R = 1 check compares, for the record
    r1_groups = sum(1 for g in record["streams"].values() for k in g if k.endswith("|R1"))
    out["r1_groups_in_record"] = r1_groups
    out["simulate_seconds"] = time.monotonic() - t1
    dest = Path(scratch) / "simulate" / "workers"
    dest.mkdir(parents=True, exist_ok=True)
    write_json(
        dest / f"{label}.result.json",
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
    return out


def main() -> int:
    scratch, jobs, seedset = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    from arborlm import p7b_core as core
    from arborlm.io import file_sha256, read_json, write_json

    labels = core.all_labels()
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(one, [(lb, str(scratch), seedset) for lb in labels]))
    table_path = scratch / "layout_hash_table.json"
    write_json(table_path, {"layouts": {r["label"]: r["table"] for r in results}})
    digest = file_sha256(table_path)
    for r in results:
        p = scratch / "simulate" / "workers" / f"{r['label']}.result.json"
        if p.is_file():
            data = read_json(p)
            data["layout_binding"]["hash_table_sha256"] = digest
            write_json(p, data)
    m10_fail = [r["label"] for r in results if r["check_group_m10"] != "passed for every group"]
    m2_fail = [r["label"] for r in results if not isinstance(r.get("r1_m2"), dict)]
    summary = {
        "seedset": seedset,
        "checkpoints": len(results),
        "m10_monotonicity_failures": m10_fail,
        "m2_r1_failures": m2_fail,
        "r1_groups_compared_total": sum(
            r["r1_m2"]["r1_groups_compared"] for r in results if isinstance(r.get("r1_m2"), dict)
        ),
        "r1_groups_in_records_total": sum(r.get("r1_groups_in_record", 0) for r in results),
        "simulate_seconds_sum": sum(r.get("simulate_seconds", 0.0) for r in results),
        "wall_seconds": time.monotonic() - started,
        "jobs": jobs,
        "layout_hash_table_sha256": digest,
    }
    print(json.dumps(summary, indent=1))
    return 0 if not m10_fail and not m2_fail else 1


if __name__ == "__main__":
    sys.exit(main())
