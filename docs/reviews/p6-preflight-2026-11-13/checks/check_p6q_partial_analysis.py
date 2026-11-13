"""Auditor check: can the P6-Q analysis compute the registered flags when some step-0
checkpoints were not reached (ADR-0011 clarification 6)? Synthetic records only.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_partial_analysis.py <scratch>
"""

import sys
from pathlib import Path
from types import SimpleNamespace

from arborlm import p6_fidelity_analysis as analysis
from arborlm import p6_fidelity_study as study
from arborlm.io import write_json


def record(b: int, o: int, s: int, variant: str, kind: str) -> dict:
    return {
        "outcome": "completed", "label": f"{variant}-{b}-{o}-{s}-{kind}", "kind": kind,
        "step": 512 if kind == "final" else 0,
        "cell": {"backbone": b, "order": o, "seed": s, "variant": variant},
        "recall": {"P": {"mean": 0.97}, "C": {"mean": 0.9}},
        "delta_nll": {"restrict": 0.001, "prior": 0.01}, "nll": {"T2P": 2.0},
    }


def main() -> None:
    scratch = Path(sys.argv[1])
    cells = analysis.expected_cells()
    finals = [record(*c, v, "final") for c in cells for v in ("fixed_tree", "learned_tree")]
    initials = [record(*c, "fixed_tree", "initial") for c in cells[:6]]  # only 6 of 27 reached
    try:
        analysis.analyze([*finals, *initials])
        print("54 finals + 6 step-0: analysis completed")
    except Exception as exc:  # noqa: BLE001
        print(f"54 finals + 6 step-0: analysis raised {type(exc).__name__}: {exc}")
    # A cell killed by the cap: suite exports terminal/manifest but no result.json.
    root = scratch / "results"
    for i, rec in enumerate([*finals, *initials]):
        folder = root / "cells" / f"c{i:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / "result.json", rec)
    (root / "cells" / "zz-killed").mkdir()
    write_json(root / "cells" / "zz-killed" / "terminal.json", {"status": "failed"})
    try:
        study.analyze_study(SimpleNamespace(results_root=root))
        print("analyze_study with a killed cell folder: completed")
    except Exception as exc:  # noqa: BLE001
        print(f"analyze_study with a killed cell folder: raised {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
