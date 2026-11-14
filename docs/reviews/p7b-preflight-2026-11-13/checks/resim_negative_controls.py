"""Negative and positive controls for tools/independent_resim.py and gate (c), on the scratch
calibration-as-stream records (no evaluation trace). Auditor role; imports arborlm only for the gate.

argv: scratch_calsim_dir genuine_confirmation.json work_dir
"""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from arborlm import p7b_core as core  # noqa: E402
from arborlm import p7b_gates as gates  # noqa: E402
from arborlm.io import file_sha256  # noqa: E402

TOOL = REPO / "docs/reviews/p7b-preflight-2026-11-13/tools/independent_resim.py"


def record_hashes(sim: Path) -> dict:
    return {p.name.replace(".result.json", ""): file_sha256(p) for p in (sim / "workers").glob("*.result.json")}


def gate(conf: Path, sim: Path, run_id: str) -> str:
    try:
        gates.check_resim_confirmation(conf, stream="A", simulate_run_id=run_id, record_sha256=record_hashes(sim))
        return "ACCEPTED"
    except core.GateError as exc:
        return f"refused: {str(exc)[:150]}"


def tool(sim: Path, table: Path, work: Path, tag: str, selection: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-I", str(TOOL), "--repo", str(REPO), "--stream", "A", "--stream-source", "calibration",
         "--hash-table", str(table), "--simulate-dir", str(sim), "--simulate-run-id", "NEG",
         "--selection", *selection, "--out", str(work / f"{tag}.json"), "--detail", str(work / f"{tag}_d.json")],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def main() -> int:
    src, genuine, work = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    work.mkdir(parents=True, exist_ok=True)
    out = {"gate_genuine": gate(genuine, src / "simulate", "SCRATCH-CAL-AS-STREAM-A")}
    base = json.loads(genuine.read_text())
    for name, fn in {
        "stream": lambda d: d.__setitem__("stream", "B"),
        "run_id": lambda d: d.__setitem__("simulate_stage_run_id", "X"),
        "one_record_hash": lambda d: d["record_sha256"].__setitem__(sorted(d["record_sha256"])[0], "0" * 64),
        "listed_difference": lambda d: d["checkpoints"][sorted(d["checkpoints"])[2]]["differences"].append({"x": 1}),
        "selection": lambda d: d.__setitem__("selection", d["selection"][:-1]),
        "tie_rules": lambda d: d.__setitem__("tie_rules", ["asc"]),
    }.items():
        d = copy.deepcopy(base)
        fn(d)
        p = work / f"gate_mut_{name}.json"
        p.write_text(json.dumps(d))
        out[f"gate_{name}"] = gate(p, src / "simulate", "SCRATCH-CAL-AS-STREAM-A")
    # tool-level: perturb one count in a copy of one record; only that checkpoint is re-simulated
    label = "b101-o301-fixed_tree-s503"
    sim2 = work / "sim_perturbed"
    if sim2.exists():
        shutil.rmtree(sim2)
    (sim2 / "workers").mkdir(parents=True)
    data = json.loads((src / "simulate" / "workers" / f"{label}.result.json").read_text())
    data["record"]["streams"]["null_2"]["L-PCOAX-3|R8"]["by_c"]["8"]["desc"]["misses_warm"] += 1
    (sim2 / "workers" / f"{label}.result.json").write_text(json.dumps(data))
    out["tool_perturbed_count"] = tool(sim2, src / "layout_hash_table.json", work, "perturbed", [label])
    # tool-level: a record whose null hash is altered
    data = json.loads((src / "simulate" / "workers" / f"{label}.result.json").read_text())
    data["null_streams"][1]["stream_sha256"] = "0" * 64
    (sim2 / "workers" / f"{label}.result.json").write_text(json.dumps(data))
    out["tool_altered_null_hash"] = tool(sim2, src / "layout_hash_table.json", work, "nullhash", [label])
    # tool-level: a layout table entry altered
    table = json.loads((src / "layout_hash_table.json").read_text())
    table["layouts"][label]["L-BCOAX|R2"] = "e" * 64
    t2 = work / "table_altered.json"
    t2.write_text(json.dumps(table))
    data = json.loads((src / "simulate" / "workers" / f"{label}.result.json").read_text())
    (sim2 / "workers" / f"{label}.result.json").write_text(json.dumps(data))
    out["tool_altered_layout_table"] = tool(sim2, t2, work, "table", [label])
    # unperturbed single-label control through the same path (must agree except the table binding)
    out["tool_unperturbed_single"] = tool(sim2, src / "layout_hash_table.json", work, "clean", [label])
    print(json.dumps(out, indent=1))
    ok = (out["gate_genuine"] == "ACCEPTED"
          and all(v.startswith("refused") for k, v in out.items() if k.startswith("gate_") and k != "gate_genuine")
          and out["tool_perturbed_count"][0] == 2 and out["tool_altered_null_hash"][0] == 2
          and out["tool_altered_layout_table"][0] == 2 and out["tool_unperturbed_single"][0] == 0)
    print("RESIM CONTROLS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
