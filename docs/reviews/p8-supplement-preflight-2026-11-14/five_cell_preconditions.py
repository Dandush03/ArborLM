"""Auditor: does the section 3 precondition hold on the ten real panel traces of the five cells?

Usage: uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/five_cell_preconditions.py <experiments root>

Reads the traces only (frozen ``p8_sim.load_trace``: file hashes against eval.json, ``check_trace``,
counts hash). Evaluates the precondition with the auditor's own predicate and, separately, the
supplement's detector. No null, no layout, no simulation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from arborlm import p8_sim  # noqa: E402

from supplements.p8s import null  # noqa: E402

EVAL = "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
FIVE = (
    "b101-o301-s601-C04",
    "b101-o301-s601-C05",
    "b101-o301-s602-C04",
    "b101-o301-s602-C05",
    "b102-o302-s601-C05",
)


def main() -> None:
    root = Path(sys.argv[1]) / EVAL / "cells"
    out = {}
    for label in FIVE:
        cell_dir = root / label
        record = json.loads((cell_dir / "eval.json").read_text())
        for name in ("calibration", "A", "B"):
            selected, _ = p8_sim.load_trace(cell_dir, record, name)
            rows = selected.tolist()
            sets = {frozenset(r) for r in rows}
            counts: dict[int, int] = {}
            for r in rows:
                for s in r:
                    counts[s] = counts.get(s, 0) + 1
            q = len(rows)
            mine = len(counts) == 8 and all(c == q for c in counts.values()) and len(sets) == 1
            det = null.detect_single_set(selected)
            out[f"{label} {name}"] = {
                "queries": q,
                "nonzero_slots": len(counts),
                "distinct_row_sets": len(sets),
                "slots": sorted(counts),
                "auditor_predicate": mine,
                "detector_holds": det.holds,
                "detector_slots_equal": list(det.slots) == sorted(counts) if det.holds else None,
                "dtype": str(selected.dtype),
            }
    print(json.dumps(out, indent=1))
    print(
        "ALL TEN PANEL TRACES MEET THE PRECONDITION"
        if all(
            v["auditor_predicate"] and v["detector_holds"]
            for k, v in out.items()
            if not k.endswith("calibration")
        )
        else "PRECONDITION FAILS ON SOME PANEL TRACE"
    )


if __name__ == "__main__":
    main()
