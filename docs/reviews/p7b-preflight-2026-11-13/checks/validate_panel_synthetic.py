"""Validate tools/independent_panel.py on a synthetic corpus at the registered sizes (panel 512,
train pool 4,096), against the implementer's ``p7b_panel.reconstruct_from_rows`` and gate (a).
The real validation parquet file is NOT read. Auditor role; imports arborlm only for comparison.

argv: scratch_dir
"""

import copy
import json
import random
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
TOOL = REPO / "docs/reviews/p7b-preflight-2026-11-13/tools/independent_panel.py"


def corpus(seed: int) -> dict:
    g = random.Random(seed)
    alphabet = list("abcdefghijklmnopqrstuvwxyz      .,;'ABCDEFGHIJ0123456789") + ["é", "ß", "中", "—", "\n"]

    def text(n: int) -> str:
        return "".join(g.choice(alphabet) for _ in range(n))

    train = [text(g.randrange(0, 900)) for _ in range(1500)]
    train += train[:40]  # duplicate train rows (dedupe within split)
    train += [""] * 5
    val = [text(g.randrange(0, 900)) for _ in range(800)]
    val += [train[g.randrange(1500)] for _ in range(60)]  # cross-split copies (must be excluded)
    val += val[:30]  # duplicate validation rows
    g.shuffle(val)
    return {"train": train, "validation": val}


def main() -> int:
    scratch = Path(sys.argv[1])
    scratch.mkdir(parents=True, exist_ok=True)
    from arborlm import p7b_core as core
    from arborlm import p7b_gates as gates
    from arborlm.io import write_json
    from arborlm.p7b_panel import reconstruct_from_rows

    data = corpus(20261113)
    rows_path = scratch / "synthetic_rows.json"
    rows_path.write_text(json.dumps(data))
    # 1. the auditor's tool first, against a placeholder record, to get its own earlier hashes
    placeholder = scratch / "placeholder_record.json"
    placeholder.write_text("{}")
    subprocess.run([sys.executable, "-I", str(TOOL), "--mode", "synthetic", "--synthetic-rows", str(rows_path),
                    "--panel-record", str(placeholder), "--panel-run-id", "X",
                    "--out", str(scratch / "c0.json"), "--detail", str(scratch / "d0.json")],
                   capture_output=True, text=True)
    mine = json.loads((scratch / "d0.json").read_text())
    earlier = mine["earlier_panels"]
    data["registered_earlier"] = earlier
    rows_path.write_text(json.dumps(data))
    # 2. the implementer's reconstruction, told to expect the auditor's earlier hashes
    res = reconstruct_from_rows(data["train"], data["validation"], expected_earlier=earlier)
    record_path = scratch / "panel_record.json"
    write_json(record_path, res.record)
    # 3. the auditor's tool against the implementer's record -> confirmation
    proc = subprocess.run([sys.executable, "-I", str(TOOL), "--mode", "synthetic", "--synthetic-rows",
                           str(rows_path), "--panel-record", str(record_path), "--panel-run-id", "P7BP-SYNTH",
                           "--out", str(scratch / "panel_confirmation.json"),
                           "--detail", str(scratch / "panel_detail.json")], capture_output=True, text=True)
    out = {"tool_stdout": proc.stdout.strip(), "tool_exit": proc.returncode,
           "implementer_checks": res.record["checks"], "implementer_overlap": res.record["overlap"],
           "counts_validation": res.record["counts"]["validation"]}
    conf = scratch / "panel_confirmation.json"
    try:
        gates.check_panel_confirmation(conf, panel_record_path=record_path, panel_run_id="P7BP-SYNTH",
                                       earlier=earlier)
        out["gate_genuine"] = "ACCEPTED"
    except core.GateError as exc:
        out["gate_genuine"] = f"REFUSED: {exc}"
    base = json.loads(conf.read_text())
    muts = {
        "row_hash": lambda d: d["row_sha256"].__setitem__(7, "0" * 64),
        "panel_hash": lambda d: d.__setitem__("panel_sha256", "0" * 64),
        "overlap": lambda d: d["overlap"].__setitem__("with_calibration_stream", 1),
        "run_id": lambda d: d.__setitem__("panel_stage_run_id", "OTHER"),
        "stale_record": lambda d: d.__setitem__("panel_record_sha256", "0" * 64),
        "earlier": lambda d: d["earlier_panels_reproduced"].__setitem__("P3", "0" * 64),
        "ranks": lambda d: d.__setitem__("ranks", [2048, 2560]),
    }
    for name, fn in muts.items():
        d = copy.deepcopy(base)
        fn(d)
        p = scratch / f"mut_{name}.json"
        p.write_text(json.dumps(d))
        try:
            gates.check_panel_confirmation(p, panel_record_path=record_path, panel_run_id="P7BP-SYNTH",
                                           earlier=earlier)
            out[f"gate_{name}"] = "ACCEPTED (control FAILED)"
        except core.GateError:
            out[f"gate_{name}"] = "refused as expected"
    # 4. negative control on the tool: a record whose panel differs by one row
    rec = json.loads(record_path.read_text())
    rec["row_sha256"][100] = "a" * 64
    bad = scratch / "bad_record.json"
    bad.write_text(json.dumps(rec))
    proc2 = subprocess.run([sys.executable, "-I", str(TOOL), "--mode", "synthetic", "--synthetic-rows",
                            str(rows_path), "--panel-record", str(bad), "--panel-run-id", "P7BP-SYNTH",
                            "--out", str(scratch / "c_bad.json"), "--detail", str(scratch / "d_bad.json")],
                           capture_output=True, text=True)
    out["tool_vs_altered_record_exit"] = proc2.returncode
    # 5. negative control: the implementer must stop if the expected earlier hashes are wrong
    wrong = dict(earlier, P2="0" * 64)
    try:
        reconstruct_from_rows(data["train"], data["validation"], expected_earlier=wrong)
        out["implementer_stops_on_wrong_earlier_hash"] = False
    except core.StopError:
        out["implementer_stops_on_wrong_earlier_hash"] = True
    print(json.dumps(out, indent=1))
    ok = (proc.returncode == 0 and out["gate_genuine"] == "ACCEPTED"
          and all(v == "refused as expected" for k, v in out.items() if k.startswith("gate_") and k != "gate_genuine")
          and out["tool_vs_altered_record_exit"] == 2 and out["implementer_stops_on_wrong_earlier_hash"])
    print("PANEL VALIDATION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
