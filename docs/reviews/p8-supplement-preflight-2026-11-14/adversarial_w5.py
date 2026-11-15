"""Auditor: edge cases for the W5 allowed-difference rule in ``supplements.p8s.analysis``.

Usage: uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/adversarial_w5.py

Each case states what ADR-0016 section 5 (W5) requires: ALLOW (no stop) or STOP.
"""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from supplements.p8s import analysis  # noqa: E402

BASE = {
    "dry_run": False,
    "inputs": {"x": 1},
    "schema": "P8-analysis-v1",
    "study_status": "INCOMPLETE",
    "cells_with_complete_records": 55,
    "missing_cells": [{"label": "a"}],
    "cases": {
        "C04": {"x": [1, 2]},
        "C05": {"x": 1},
        "C06": {"v": 0.5, "l": [1, 2], "flag": True, "n": 3},
        "C10": {"refs": ["C06", "C08"]},
    },
    "concentration_controls_bind": False,
    "decision_inputs": {
        "section_8_option_indicated": "none",
        "section_8_reason": "INCOMPLETE",
        "open_questions": [{"case": "C09"}],
        "architecture_advantage_cases": [],
    },
    "open_questions": [{"case": "C09"}],
}


def new_base() -> dict:
    out = {k: copy.deepcopy(v) for k, v in BASE.items() if k not in ("dry_run", "inputs")}
    out["study_status"] = "COMPLETE"
    out["cells_with_complete_records"] = 60
    out["missing_cells"] = []
    out["decision_inputs"]["section_8_option_indicated"] = "c"
    out["decision_inputs"]["section_8_reason"] = "no flat case ..."
    out["cases"]["C04"] = {"x": [9]}
    return out


def case(name: str, expect: str, mutate) -> bool:  # type: ignore[no-untyped-def]
    new = new_base()
    mutate(new)
    got = "ALLOW" if analysis.compare_analysis(copy.deepcopy(BASE), new)["ok"] else "STOP"
    ok = got == expect
    print(f"{'OK ' if ok else 'BAD'} {name}: expected {expect}, got {got}")
    return ok


def main() -> None:
    ok = True
    ok &= case("only the allowed keys differ", "ALLOW", lambda n: None)
    ok &= case(
        "int 3 written as float 3.0 in C06",
        "ALLOW",
        lambda n: n["cases"]["C06"].__setitem__("n", 3.0),
    )
    ok &= case(
        "bool True written as 1 in C06", "STOP", lambda n: n["cases"]["C06"].__setitem__("flag", 1)
    )
    ok &= case(
        "C06 float changes in the last bit",
        "STOP",
        lambda n: n["cases"]["C06"].__setitem__("v", 0.5000000000000001),
    )
    ok &= case("extra key under C06", "STOP", lambda n: n["cases"]["C06"].__setitem__("new", 1))
    ok &= case("C06 list grows", "STOP", lambda n: n["cases"]["C06"]["l"].append(3))
    ok &= case(
        "C10 refers to C04", "STOP", lambda n: n["cases"]["C10"].__setitem__("refs", ["C04", "C08"])
    )
    ok &= case(
        "open_questions gains C04", "STOP", lambda n: n["open_questions"].append({"case": "C04"})
    )
    ok &= case(
        "decision_inputs.open_questions changes",
        "STOP",
        lambda n: n["decision_inputs"]["open_questions"].clear(),
    )
    ok &= case(
        "decision_inputs.architecture_advantage_cases changes",
        "STOP",
        lambda n: n["decision_inputs"]["architecture_advantage_cases"].append("C07"),
    )
    ok &= case(
        "concentration_controls_bind flips",
        "STOP",
        lambda n: n.__setitem__("concentration_controls_bind", True),
    )
    ok &= case("new top-level key", "STOP", lambda n: n.__setitem__("decision", "c"))
    ok &= case("schema changes", "STOP", lambda n: n.__setitem__("schema", "x"))
    ok &= case("new key under C05", "ALLOW", lambda n: n["cases"]["C05"].__setitem__("anything", 1))
    ok &= case("C04 removed entirely", "ALLOW", lambda n: n["cases"].pop("C04"))
    ok &= case(
        "decision_inputs.section_8_reason removed",
        "ALLOW",
        lambda n: n["decision_inputs"].pop("section_8_reason"),
    )
    ok &= case(
        "NaN in C06 on both sides (not JSON-representable in the registered file)",
        "STOP",
        lambda n: n["cases"]["C06"].__setitem__("v", float("nan")),
    )
    # CSV: scorecard study_status of a non-C04/C05 row may change; another column may not
    with tempfile.TemporaryDirectory() as tmp:
        reg, new = Path(tmp) / "reg", Path(tmp) / "new"
        reg.mkdir()
        new.mkdir()
        hdr = "case,study_status,x\r\n"
        (reg / "scorecard.csv").write_text(
            hdr + "C01,INCOMPLETE,1\r\nC04,INCOMPLETE,2\r\n", newline=""
        )
        (reg / "cells.csv").write_text("label,case\r\nb-C01,C01\r\nb-C06,C06\r\n", newline="")
        (reg / "pairs.csv").write_text("case,v\r\nC01,1\r\nC04,2\r\n")
        lab = "# SUPPLEMENTARY\n"
        (new / "scorecard.csv").write_text(
            lab + "case,study_status,x\nC01,COMPLETE,1\nC04,COMPLETE,7\n"
        )
        (new / "cells.csv").write_text(
            lab + "label,case\nb-C01,C01\nb101-o301-s601-C04,C04\nb-C06,C06\n"
        )
        (new / "pairs.csv").write_text(lab + "case,v\nC01,1\nC04,5\nC05,6\n")
        res = analysis.compare_csvs(reg, new)
        print(f"{'OK ' if res['ok'] else 'BAD'} CSV allowed edits only: ok={res['ok']}")
        ok &= res["ok"]
        (new / "cells.csv").write_text(lab + "label,case\nb-C06,C06\nb-C01,C01\n")
        res = analysis.compare_csvs(reg, new)
        print(f"{'OK ' if not res['ok'] else 'BAD'} CSV registered cells reordered: ok={res['ok']}")
        ok &= not res["ok"]
        (new / "cells.csv").write_text(lab + "label,case\nb-C01,C01\nb-C06,C06\n")
        (new / "scorecard.csv").write_text(
            lab + "case,study_status,x\nC01,COMPLETE,9\nC04,COMPLETE,7\n"
        )
        res = analysis.compare_csvs(reg, new)
        print(
            f"{'OK ' if not res['ok'] else 'BAD'} CSV non-C04/C05 scorecard value changes: ok={res['ok']}"
        )
        ok &= not res["ok"]
        (new / "scorecard.csv").write_text(
            lab + "case,study_status,y\nC01,COMPLETE,1\nC04,COMPLETE,7\n"
        )
        try:
            res = analysis.compare_csvs(reg, new)
            print(f"{'OK ' if not res['ok'] else 'BAD'} CSV header renamed: ok={res['ok']}")
            ok &= not res["ok"]
        except Exception as exc:  # noqa: BLE001
            print(f"NOTE CSV header renamed raised {type(exc).__name__}: {exc}")
    print("ALL AS EXPECTED" if ok else "UNEXPECTED RESULT FOUND")


if __name__ == "__main__":
    main()
