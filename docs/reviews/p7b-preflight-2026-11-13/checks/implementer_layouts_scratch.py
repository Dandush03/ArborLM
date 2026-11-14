"""Scratch harness (auditor role): build the implementer's layouts from the REAL CALIBRATION traces
through its public calibration-only interface (``CalibrationTrace.from_identity`` +
``build_layouts``), outside any registered stage, and write a hash table in the layout stage's
schema to a scratch path. Used only to validate ``tools/independent_layouts.py`` before the freeze.

This harness imports arborlm (it exercises the implementer's code); the tool it validates does not.
It opens calibration files only (the implementer's loader resolves calibration roles only, and the
open() spy below records every file opened and fails if a non-calibration trace is touched).
"""

import builtins
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))


def one(label: str) -> dict:
    opened: list[str] = []
    real_open = builtins.open
    import io as _io

    def spy(file, *a, **k):  # type: ignore[no-untyped-def]
        name = str(file)
        if "/traces/" in name and "calib_" not in Path(name).name:
            raise RuntimeError(f"non-calibration trace opened: {name}")
        if "/traces/" in name:
            opened.append(Path(name).name)
        return real_open(file, *a, **k)

    builtins.open = spy
    _io.open = spy
    import pathlib

    real_read_bytes = pathlib.Path.read_bytes

    def rb(self):  # type: ignore[no-untyped-def]
        name = str(self)
        if "/traces/" in name and "calib_" not in self.name:
            raise RuntimeError(f"non-calibration trace read: {name}")
        if "/traces/" in name:
            opened.append(self.name)
        return real_read_bytes(self)

    pathlib.Path.read_bytes = rb
    from arborlm import p7b_core as core
    from arborlm import p7b_layout as L

    identity = core.load_identity(REPO)
    t0 = time.monotonic()
    cal = L.CalibrationTrace.from_identity(identity, label)
    built, meta = L.build_layouts(cal, rows_list=(2, 8))
    seconds = time.monotonic() - t0
    return {
        "label": label,
        "table": L.hash_table(built, rows_list=(2, 8)),
        "meta": meta,
        "seconds": seconds,
        "passes": {b.key(): b.info.get("passes") for b in built if b.rows is not None},
        "opened": sorted(set(opened)),
    }


def main() -> int:
    out = Path(sys.argv[1])
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sys.path.insert(0, str(REPO / "src"))
    from arborlm import p7b_core as core

    labels = core.all_labels()
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(one, labels))
    table = {r["label"]: r["table"] for r in results}
    payload = {
        "schema": "P7B-layout-hash-table-v1 (SCRATCH, auditor harness, not a registered stage)",
        "layouts": table,
        "meta": {r["label"]: r["meta"] for r in results},
        "seconds": {r["label"]: r["seconds"] for r in results},
        "max_passes": max(max(v for v in r["passes"].values() if v is not None) for r in results),
        "files_opened": sorted({n for r in results for n in r["opened"]}),
        "wall_seconds": time.monotonic() - started,
        "jobs": jobs,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(
        f"implementer scratch build: {len(results)} checkpoints, wall {payload['wall_seconds']:.1f} s "
        f"(jobs={jobs}), sum of per-checkpoint seconds {sum(payload['seconds'].values()):.1f}, "
        f"max passes {payload['max_passes']}, files opened: {payload['files_opened']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
