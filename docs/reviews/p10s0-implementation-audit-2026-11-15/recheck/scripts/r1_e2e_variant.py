"""Re-check of P10-S0 (3a9a742): a VARIANT of studies.p10s0.e2e written by the auditor, reusing only its helpers
(shim, copy, commit, stage and script runners, solve_factor). Differences from the implementer's _run_e2e:
  * the 32K/64K rehearsal peak is NOT raised, so the probe is allowed by the Q1 gate (the implementer's run refuses it for MEMORY
    before the WX-before-probe guard is ever reached);
  * order through the real launch scripts: gates, q1, q1_gate, probe (expected REFUSED: WX first), wx, probe (expected 0), analysis, report, q1 (refused);
  * the work directory is NOT deleted, so every product can be scanned afterwards (r2_scan_products.py); the auditor deletes it at the end.
Test seeds only (TEST_PROFILE marker), tiny sizes, synthetic backbone, a throwaway git clone. Nothing at real size; no registered/rehearsal/check seed.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import json
import shutil
import sys
from pathlib import Path

from studies.p10s0 import core
from studies.p10s0 import e2e as E


def scale_no_mem(src: Path, dst: Path, factor: float) -> None:
    shutil.copytree(src, dst)
    for path in dst.glob("rehearsal/*/rehearsal.json"):
        rec = json.loads(path.read_text())
        rec["seconds_per_update"] = float(rec["seconds_per_update"]) * factor
        path.write_text(json.dumps(rec, sort_keys=True))


def main(out: Path, source: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work"
    work.mkdir()
    log = out / "e2e.log"
    clone = work / "clone"
    E.write_uv_shim(work / "shim")
    clone.mkdir()
    E.copy_working_tree(source, clone)
    E.run(["git", "init", "-q"], clone, log)
    E.commit(clone, "base", log)
    exp = clone / "experiments"
    arm = clone / "studies/p10s0/freeze/arm_selection.json"
    summary: dict = {"steps": {}}
    reh = exp / "E2E-rehearsal"
    E.stages(clone, log, "rehearse", "--dry", "--run-dir", str(reh), "--arm-selection", str(arm), "--stage-cap-seconds", "3000")
    gen = exp / "E2E-generation"
    E.stages(clone, log, "generate", "--dry", "--run-dir", str(gen), "--stage-cap-seconds", "600")
    gen_manifest = next(gen.glob("generate-*/manifest.json"))
    E.stages(clone, log, "set-generation-cap", "--generate-manifest", str(gen_manifest))
    E.stages(clone, log, "gates", "--dry", "--run-dir", str(gen), "--arm-selection", str(arm), "--stage-cap-seconds", "3000")
    gates_manifest = json.loads((gen / "gates/manifest.json").read_text())
    gates_seconds = float(sum(t["seconds"] for t in gates_manifest["tasks"]))
    per_draw = float(json.loads((gen / "gates.json").read_text())["timing"]["per_draw_seconds"])
    generate_seconds = float(sum(t["seconds"] for t in json.loads(gen_manifest.read_text())["tasks"]))
    probe_json = exp / "E2E-projection-unscaled.json"
    E.stages(clone, log, "projection", "--dry", "--rehearsal-alone", str(reh), "--rehearsal-busy", str(reh), "--arm-selection", str(arm), "--out", str(probe_json))
    factor = E.solve_factor(json.loads(probe_json.read_text()))
    scaled = exp / "E2E-rehearsal-scaled"
    scale_no_mem(reh, scaled, factor)
    projection = exp / "E2E-projection.json"
    E.stages(clone, log, "projection", "--dry", "--rehearsal-alone", str(scaled), "--rehearsal-busy", str(scaled), "--arm-selection", str(arm), "--out", str(projection))
    caps = clone / "studies/p10s0/freeze/stage_caps.json"
    E.stages(clone, log, "caps", "--dry", "--projection", str(projection), "--out", str(caps), "--gates-wall-seconds", str(gates_seconds), "--gates-per-draw-seconds", str(per_draw), "--analysis-wall-seconds", "1", "--report-wall-seconds", "1", "--generate-wall-seconds", str(generate_seconds))
    decision = clone / "results/p10s0-freeze-e2e/DECISION.md"
    decision.parent.mkdir(parents=True)
    decision.write_text("# auditor variant of the end-to-end exercise (throwaway clone): not a decision about S0.\n")
    pre_freeze = E.commit(clone, "pre-freeze", log)
    run_dir = exp / "E2E-registered"
    run_dir.mkdir(parents=True)
    (run_dir / core.TEST_PROFILE_MARKER).write_text("test profile\n")
    summary["steps"]["generate.sh"] = E.run(["sh", "studies/p10s0/launch/generate.sh", str(run_dir), pre_freeze], clone, log, expect=None, env=E.clone_env(clone, clone.parent / "shim"))
    plan_path = clone / "studies/p10s0/freeze/plan.json"
    E.stages(clone, log, "freeze-plan", "--test-profile", "--test-candidate", "A5-D", "--run-dir", str(run_dir), "--arm-selection", str(arm), "--projection", str(projection), "--out", str(plan_path))
    freeze = E.commit(clone, "freeze", log)
    summary["freeze_commit"] = freeze
    order = [("gates", 0), ("q1", 0), ("q1_gate", 0), ("probe", 2), ("wx", 0), ("probe", 0), ("analysis", 0), ("report", 0), ("q1", 2)]
    codes = []
    for name, expect in order:
        codes.append((name, expect, E.script(clone, log, name, run_dir, freeze, expect=None)))
    summary["steps"]["scripts"] = codes
    summary["mismatches"] = [c for c in codes if c[1] != c[2]]
    summary["q1_start"] = json.loads((run_dir / "q1_start.json").read_text())
    summary["q1_gate_blocks"] = json.loads((run_dir / "q1_gate.json").read_text())["blocks"]
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    return 0 if not summary["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
