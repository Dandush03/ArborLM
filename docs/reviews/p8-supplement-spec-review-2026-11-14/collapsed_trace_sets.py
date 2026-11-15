"""ADR-0016 spec review: read (do not simulate) the calibration, Panel A and Panel B selected-slot
traces of the five failed P8 cells. Reports, per trace: queries, number of distinct query slot sets,
the set if unique, number of distinct within-row orders, and rows already in ascending order.

Standard library only; no arborlm import. Not Astra validation.

Run: uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/collapsed_trace_sets.py EVAL_RUN_DIR
"""

import array
import collections
import json
import sys
from pathlib import Path

CELLS = (
    "b101-o301-s601-C04",
    "b101-o301-s601-C05",
    "b101-o301-s602-C04",
    "b101-o301-s602-C05",
    "b102-o302-s601-C05",
)
FILES = ("calibration_selected.int16.bin", "panelA_selected.int16.bin", "panelB_selected.int16.bin")


def main() -> int:
    run = Path(sys.argv[1])
    assert sys.byteorder == "little"
    out: dict[str, object] = {}
    for cell in CELLS:
        entry: dict[str, object] = {}
        for name in FILES:
            data = array.array("h")
            data.frombytes((run / "cells" / cell / name).read_bytes())
            rows = [tuple(data[i * 8 : (i + 1) * 8]) for i in range(len(data) // 8)]
            sets = {frozenset(r) for r in rows}
            entry[name.split("_")[0]] = {
                "queries": len(rows),
                "distinct_sets": len(sets),
                "the_set": sorted(next(iter(sets))) if len(sets) == 1 else None,
                "rows_with_8_distinct": sum(1 for r in rows if len(set(r)) == 8),
                "distinct_within_row_orders": len(collections.Counter(rows)),
                "rows_in_ascending_order": sum(1 for r in rows if list(r) == sorted(r)),
            }
        sets_all = {json.dumps(v["the_set"]) for v in entry.values()}  # type: ignore[index]
        entry["same_set_on_calibration_A_B"] = len(sets_all) == 1
        out[cell] = entry
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
