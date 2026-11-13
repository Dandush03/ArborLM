"""Re-audit of the B1 fix: P6-Q analysis under partial, failed, killed and malformed records.

Synthetic compact records only, written to a scratch results root and read back through the
CLI path ``analyze_study`` (folder walk included). Flags are recomputed with my own arithmetic
(plain fractions) and compared with the implementation's output.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_p6q_analysis.py <scratch>
"""

import json
import random
import sys
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

from arborlm import p6_fidelity_study as study

BACK, ORD, SEEDS = (101, 102, 103), (301, 302, 303), (501, 502, 503)
CELLS = [(b, o, s) for b in BACK for o in ORD for s in SEEDS]
KINDS = ("fixed_tree", "learned_tree")


def final(b, o, s, kind, rng):
    return {
        "outcome": "completed", "label": f"b{b}-o{o}-{kind}-s{s}-final", "kind": "final",
        "step": 512, "cell": {"backbone": b, "order": o, "seed": s, "variant": kind},
        "recall": {"P": {"mean": rng.choice([0.94, 0.95, 0.97, 0.99])},
                   "C": {"mean": rng.uniform(0.5, 0.99)}},
        "delta_nll": {"restrict": rng.uniform(-0.02, 0.004), "prior": rng.uniform(-0.001, 0.03)},
        "nll": {"T2P": 2.0},
    }


def initial(b, o, s):
    return {
        "outcome": "completed", "label": f"b{b}-o{o}-shared_initial-s{s}", "kind": "initial",
        "step": 0, "cell": {"backbone": b, "order": o, "seed": s, "variant": "fixed_tree"},
        "recall": {"P": {"mean": 0.5}, "C": {"mean": 0.5}},
        "delta_nll": {"restrict": 0.0, "prior": 0.0}, "nll": {"T2P": 5.5},
    }


def write(root: Path, label: str, files: dict) -> None:
    folder = root / "cells" / label
    folder.mkdir(parents=True)
    for name, data in files.items():
        (folder / name).write_text(json.dumps(data))


def my_flags(recs):
    """Independent arithmetic of section 4.4 for one kind."""
    def mean(xs):
        return sum(Fraction(x) for x in xs) / len(xs)

    def parents(key):
        return [mean([key(r) for r in recs if (r["cell"]["backbone"], r["cell"]["order"]) == (b, o)])
                for b in BACK for o in ORD]

    out = {}
    for name, key in (("FID", lambda r: r["recall"]["P"]["mean"]),
                      ("COS", lambda r: r["recall"]["C"]["mean"])):
        vals = [key(r) for r in recs]
        out[name] = (mean(vals) >= Fraction(0.95) and sum(Fraction(v) >= Fraction(0.95) for v in vals) >= 22
                     and sum(p >= Fraction(0.95) for p in parents(key)) >= 8)
    key = lambda r: r["delta_nll"]["restrict"]  # noqa: E731
    vals = [key(r) for r in recs]
    out["LOSS"] = (mean(vals) <= Fraction(-0.005) and sum(v < 0 for v in vals) >= 22
                   and sum(p < 0 for p in parents(key)) >= 8)
    key = lambda r: r["delta_nll"]["prior"]  # noqa: E731
    vals = [key(r) for r in recs]
    m = mean(vals)
    sign = (m > 0) - (m < 0)
    sgn = lambda x: (x > 0) - (x < 0)  # noqa: E731
    out["PRIOR"] = (abs(m) >= Fraction(0.005) and sign != 0
                    and sum(sgn(Fraction(v)) == sign for v in vals) >= 22
                    and sum(sgn(p) == sign for p in parents(key)) >= 8)
    return out


def run_case(scratch: Path, name: str, build) -> dict:
    root = scratch / name
    root.mkdir(parents=True)
    rng = random.Random(name)
    finals = {k: [final(*c, k, rng) for c in CELLS] for k in KINDS}
    suite_cells = build(root, finals)
    (root / "suite").mkdir()
    (root / "suite" / "result.json").write_text(json.dumps(suite_cells))
    try:
        study.analyze_study(SimpleNamespace(results_root=root))
    except BaseException as exc:  # noqa: BLE001 - report what happens
        return {"case": name, "raised": f"{type(exc).__name__}: {exc}"}
    out = json.loads((root / "analysis.json").read_text())
    summary = {
        "case": name,
        "flags_status": out["flags_status"],
        "records": out["records"],
        "finals_missing": [(m["label"], m.get("suite_status"), m.get("record_outcome"))
                           for m in out["finals_missing_or_not_completed"]],
        "step0_missing_count": len(out["step0_unexecuted_or_failed"]),
        "step0_missing_first": out["step0_unexecuted_or_failed"][:2],
        "initial_completed": out["initial_checkpoints"]["completed"],
        "suite_outcome": (out["suite"] or {}).get("outcome"),
    }
    if out["flags_status"] == "COMPUTED":
        mine = {k: my_flags(finals[k]) for k in KINDS}
        theirs = {k: {f: out["flags"][k][f]["passed"] for f in ("FID", "COS", "LOSS", "PRIOR")}
                  for k in KINDS}
        summary["flags_impl"] = theirs
        summary["flags_mine_agree"] = mine == theirs
        summary["cells_total"] = {k: out["flags"][k]["FID"]["cells_total"] for k in KINDS}
    else:
        summary["flags"] = out["flags"]
    return summary


def all_finals(root, finals):
    for k in KINDS:
        for r in finals[k]:
            write(root, r["label"], {"result.json": r})


def case_partial_step0_killed(root, finals):
    all_finals(root, finals)
    for c in CELLS[:6]:
        write(root, f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}", {"result.json": initial(*c)})
    c = CELLS[6]
    write(root, f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}",
          {"terminal.json": {"status": "failed", "reason": "process wall-time cap"},
           "manifest.json": {}})
    rows = [{"label": f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}", "status": "unexecuted",
             "reason": "stage stopped earlier (failure)"} for c in CELLS[7:]]
    return {"outcome": "stopped", "reason": "cap kill in step 0", "cells": rows}


def case_budget_step0(root, finals):
    all_finals(root, finals)
    for c in CELLS[:5]:
        write(root, f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}", {"result.json": initial(*c)})
    rows = [{"label": f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}", "status": "unexecuted",
             "reason": "budget"} for c in CELLS[5:]]
    return {"outcome": study.PARTIAL_STEP0, "reason": "budget", "cells": rows}


def case_final_gate_violation(root, finals):
    bad = finals["learned_tree"].pop(13)
    for k in KINDS:
        for r in finals[k]:
            write(root, r["label"], {"result.json": r})
    write(root, bad["label"], {"result.json": {"outcome": "gate_violation", "label": bad["label"],
                                               "gate": "iv", "message": "x"}})
    finals["learned_tree"].insert(13, bad)
    return {"outcome": "stopped", "cells": []}


def case_final_missing(root, finals):
    for k in KINDS:
        for r in finals[k][:-1] if k == "learned_tree" else finals[k]:
            write(root, r["label"], {"result.json": r})
    last = finals["learned_tree"][-1]["label"]
    return {"outcome": study.BUDGET_DURING_FINALS,
            "cells": [{"label": last, "status": "unexecuted", "reason": "budget"}]}


def case_final_killed(root, finals):
    for k in KINDS:
        for r in finals[k][:-1] if k == "fixed_tree" else finals[k]:
            write(root, r["label"], {"result.json": r})
    write(root, finals["fixed_tree"][-1]["label"], {"terminal.json": {"status": "failed"}})
    return {"outcome": "stopped", "cells": []}


def case_extra_completed_final(root, finals):
    all_finals(root, finals)
    extra = final(101, 301, 999, "fixed_tree", random.Random(1))
    write(root, extra["label"], {"result.json": extra})
    return {"outcome": "completed", "cells": []}


def case_step0_gate_violation_suite_stopped(root, finals):
    all_finals(root, finals)
    c = CELLS[0]
    write(root, f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}",
          {"result.json": {"outcome": "gate_violation",
                           "label": f"b{c[0]}-o{c[1]}-shared_initial-s{c[2]}", "gate": "ii"}})
    return {"outcome": "stopped", "reason": "gate ii on a step-0 checkpoint", "cells": []}


def main() -> None:
    scratch = Path(sys.argv[1])
    for name, build in (
        ("A_finals_complete_step0_partial_and_killed", case_partial_step0_killed),
        ("B_finals_complete_budget_in_step0", case_budget_step0),
        ("C_one_final_gate_violation", case_final_gate_violation),
        ("D_one_final_never_started", case_final_missing),
        ("E_one_final_killed_no_result", case_final_killed),
        ("F_extra_completed_final_outside_grid", case_extra_completed_final),
        ("G_step0_gate_violation_suite_stopped", case_step0_gate_violation_suite_stopped),
    ):
        print(json.dumps(run_case(scratch, name, build), sort_keys=True))


if __name__ == "__main__":
    main()
