"""FIXED COPY (as a wrapper) of the auditor's frozen independent_trace_stats_p8.py for cells WITHOUT
sim.json. Auditor: Claude Opus 5.5. Not Astra validation, not human approval.

Why: the frozen tool (sha256 5105387379ae...c16c2, kept unchanged) opens sim.json for every label
and raises FileNotFoundError on the five cells whose simulation failed (kept in
failed_attempts/trace_stats_attempt2_FAILED_unchanged_tool_missing_sim_json.log).

What changed: nothing in the formulas. This wrapper loads the frozen tool by path (hash checked)
and reuses its read_bin / util / branch_util / reuse / persistence functions unchanged. The only
difference is control flow: when sim.json is missing, the utilization fields are still compared
with eval.json, the trace file hashes are still checked, and temporal reuse / branch persistence
are computed and REPORTED (there is no implementation value to compare with). The order-shuffled
statistics are not computed (they need the registered permutation from arborlm; skipped to keep
this wrapper free of implementation imports).

Usage: python -I trace_stats_p8_failed_cells.py --eval-run E --sim-run S --labels L ...
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "p8-preflight-2026-11-14" / "independent_trace_stats_p8.py"
SHA = "5105387379ae73ac0e3eade180e45b181cd951dde502bc8adacdc9130dec16c2"


def main() -> int:
    assert hashlib.sha256(TOOL.read_bytes()).hexdigest() == SHA
    spec = importlib.util.spec_from_file_location("ts", TOOL)
    T = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(T)  # type: ignore[union-attr]
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-run", type=Path, required=True)
    ap.add_argument("--sim-run", type=Path, required=True)
    ap.add_argument("--labels", nargs="+", required=True)
    a = ap.parse_args()
    print("hand-constructed checks:", "PASS" if not T.hand_checks() else "FAIL")
    compared, maxd, mism, report = 0, 0.0, [], {}
    for lab in a.labels:
        cdir = a.eval_run / "cells" / lab
        ev = json.loads((cdir / "eval.json").read_text())
        has_sim = (a.sim_run / "cells" / lab / "sim.json").is_file()
        report[lab] = {"sim_json": has_sim}
        for name in ("calibration", "A", "B"):
            fs = ev["traces"][name]["files"]
            for k in ("selected", "branches"):
                if fs.get(k) and hashlib.sha256((cdir / fs[k]["file"]).read_bytes()).hexdigest() != fs[k]["sha256"]:
                    mism.append(f"{lab}|{name}|{k}|file hash")
            sel = T.read_bin(cdir / fs["selected"]["file"], "h", fs["selected"]["shape"])
            br = T.read_bin(cdir / fs["branches"]["file"], "b", fs["branches"]["shape"]) if fs.get("branches") else None
            mine = T.util(sel)
            impl = ev["traces"][name]["utilization"]
            pairs = [(k, mine[k], impl[k]) for k in mine]
            if br is not None:
                mb = T.branch_util(br)
                pairs += [(f"branches.{k}", mb[k], impl["branches"][k]) for k in mb]
            for k, x, y in pairs:
                compared += 1
                d = abs(float(x) - float(y))
                maxd = max(maxd, d)
                if d > 1e-9 * max(1.0, abs(float(y))):
                    mism.append(f"{lab}|{name}|{k}: auditor {x} impl {y}")
            entry = {"utilization": mine}
            if name in ("A", "B"):
                entry["reuse_actual"] = T.reuse(sel)
                if br is not None:
                    entry["persistence_top_pair"] = T.persistence(br)
            report[lab][name] = entry
    print(json.dumps({"labels": len(a.labels), "compared": compared, "max_abs_diff": maxd,
                      "mismatch_count": len(mism), "mismatches": mism, "report": report}, indent=1))
    return 0 if not mism else 1


if __name__ == "__main__":
    sys.exit(main())
