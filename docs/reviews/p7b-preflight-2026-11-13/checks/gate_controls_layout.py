"""Positive and negative controls: does the implementer's layout gate accept the auditor's genuine
confirmation and refuse altered ones? Also: does the auditor's tool itself report DISAGREE when the
implementer's table is altered? (Auditor role; imports arborlm only to call the gate.)

argv: confirmation.json hash_table.json run_id scratch_dir
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from arborlm import p7b_core as core  # noqa: E402
from arborlm import p7b_gates as gates  # noqa: E402


def main() -> int:
    conf_path, table_path, run_id, scratch = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(
        sys.argv[4]
    )
    scratch.mkdir(parents=True, exist_ok=True)
    results = {}
    try:
        gates.check_layout_confirmation(conf_path, hash_table_path=table_path, layout_run_id=run_id)
        results["genuine"] = "ACCEPTED"
    except core.GateError as exc:
        results["genuine"] = f"REFUSED: {exc}"
    base = json.loads(conf_path.read_text())
    label = sorted(base["checkpoints"])[5]

    def mut_hash(d):  # one hash altered
        d["checkpoints"][label]["R8"]["L-COAX"] = "0" * 64

    def mut_run(d):
        d["layout_stage_run_id"] = "OTHER"

    def mut_verdict(d):
        d["verdict"] = "DISAGREE"

    def mut_missing(d):
        del d["checkpoints"][label]

    def mut_tablehash(d):
        d["layout_hash_table_sha256"] = "1" * 64

    def mut_layoutset(d):
        del d["checkpoints"][label]["R2"]["L-NCOAX"]

    for name, fn in (("one_hash", mut_hash), ("run_id", mut_run), ("verdict", mut_verdict),
                     ("missing_label", mut_missing), ("stale_table_hash", mut_tablehash),
                     ("missing_layout", mut_layoutset)):
        d = copy.deepcopy(base)
        fn(d)
        p = scratch / f"mut_{name}.json"
        p.write_text(json.dumps(d))
        try:
            gates.check_layout_confirmation(p, hash_table_path=table_path, layout_run_id=run_id)
            results[name] = "ACCEPTED (control FAILED)"
        except core.GateError as exc:
            results[name] = f"refused as expected: {str(exc)[:120]}"
    # the tool itself against an altered implementer table
    table = json.loads(table_path.read_text())
    table["layouts"][label]["L-PCOAX-3|R2"] = "f" * 64
    altered = scratch / "altered_table.json"
    altered.write_text(json.dumps(table))
    proc = subprocess.run(
        [sys.executable, "-I", str(REPO / "docs/reviews/p7b-preflight-2026-11-13/tools/independent_layouts.py"),
         "--repo", str(REPO), "--hash-table", str(altered), "--layout-run-id", run_id,
         "--out", str(scratch / "conf_altered.json"), "--detail", str(scratch / "detail_altered.json"),
         "--jobs", "9"],
        capture_output=True, text=True,
    )
    results["tool_vs_altered_table"] = {"exit": proc.returncode, "stdout": proc.stdout.strip()}
    try:
        gates.check_layout_confirmation(scratch / "conf_altered.json", hash_table_path=altered,
                                        layout_run_id=run_id)
        results["gate_on_tool_disagree_output"] = "ACCEPTED (control FAILED)"
    except core.GateError as exc:
        results["gate_on_tool_disagree_output"] = f"refused as expected: {str(exc)[:160]}"
    print(json.dumps(results, indent=1))
    ok = results["genuine"] == "ACCEPTED" and all(
        v.startswith("refused") for k, v in results.items() if k.startswith(("one_", "run_", "verd", "miss", "stale", "gate_"))
    ) and results["tool_vs_altered_table"]["exit"] == 2
    print("CONTROLS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
