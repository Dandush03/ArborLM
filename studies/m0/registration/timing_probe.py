# ruff: noqa: E501
"""Timing probe for the capacity stage. It DECIDES NOTHING and is not part of the stage.

Three lineages chosen by name before anything was measured (one each of R1, M1, C1), levels 0 and 6, the
stream label ``capacity-timing-probe`` (NOT the label of record, so no item of the capacity stream is read),
2,000 keys per draw with the key of ``distinct_key``. It reports only speeds and the discard rate: attempts per
second (``build_item`` plus the key), the share of attempts discarded as already seen, and the extra time of the
second-solver check per item. It does not report or keep how many distinct keys a lineage can reach.

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python -m studies.m0.registration.timing_probe OUT.json
"""

from __future__ import annotations

import json
import os
import sys
import time

from studies.m0.core import build_item, stream
from studies.m0.registration import capacity as cap
from studies.m0.registration.distinct_key import item_key

PICKED = ("R1.compass_turns", "M1.tiered_pricing", "C1.postfix_evaluation")  # named before measuring
LEVELS = (0, 6)
KEYS = 2000
REPEATS = 3
LABEL = "capacity-timing-probe"
SOLVER_ITEMS = 300


def main(argv: list[str]) -> int:
    out_path = argv[1]
    if os.path.exists(out_path):
        print("refusing to overwrite", out_path, file=sys.stderr)
        return 2
    src = cap.RealSource()
    rows = []
    for lid in PICKED:
        lin = src.lineage(lid)
        solver = src.solver(lid)
        for level in LEVELS:
            for rep in range(REPEATS):
                rng = stream(cap.SEED, LABEL, lin.eval, lin.id, str(level))  # the same stream every repeat
                seen: set[bytes] = set()
                attempts = 0
                t0 = time.perf_counter()
                while len(seen) < KEYS and attempts < cap.ATTEMPT_FACTOR * KEYS + cap.ATTEMPT_BASE:
                    attempts += 1
                    it = build_item(lin, level, rng, "-", "probe")
                    seen.add(item_key(lin.id, it.question, it.structured))
                dt = time.perf_counter() - t0
                rng2 = stream(cap.SEED, LABEL, lin.eval, lin.id, str(level))
                items = [build_item(lin, level, rng2, "-", "probe") for _ in range(SOLVER_ITEMS)]
                t1 = time.perf_counter()
                for it in items:
                    cap._check(solver, it.question, it.structured, it.answer, 0)
                ds = time.perf_counter() - t1
                rows.append(
                    {
                        "lineage": lid, "level": level, "repeat": rep, "attempts": attempts,
                        "seconds": round(dt, 4), "attempts_per_second": round(attempts / dt, 1),
                        "discard_rate": round(1 - len(seen) / attempts, 5),
                        "solver_seconds_per_item": round(ds / SOLVER_ITEMS, 6),
                    }
                )
                print(rows[-1], flush=True)
    with open(out_path, "x") as f:
        json.dump({"label": LABEL, "keys_asked": KEYS, "python": sys.version.split()[0], "cpu_count": os.cpu_count(), "rows": rows}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
