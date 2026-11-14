"""End-to-end synthetic run of the registered P7-B stage sequence in which every confirmation file
is produced by the AUDITOR's tools (tools/independent_*.py, run as separate `python -I` processes),
not by the implementer's stand-ins. It shows that genuine agreeing confirmations pass every gate in
the legitimate order and that the tools run on the study's own outputs. Synthetic data only (the
implementer's dry-run fixture: 2 parent/seed pairs, 8 contexts); everything lives under a scratch
directory; nothing is written under experiments/ or results/ of the repository.

Auditor role. This harness imports arborlm to drive the study's stages; the tools do not.
argv: scratch_dir
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
TOOLS = REPO / "docs/reviews/p7b-preflight-2026-11-13/tools"
PY = [sys.executable, "-I"]


def run_tool(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run(PY + argv, capture_output=True, text=True, cwd=REPO)
    return proc.returncode, (proc.stdout + proc.stderr).strip()[-2000:]


def only(path: Path) -> Path:
    items = sorted(p for p in path.iterdir() if p.is_dir())
    assert len(items) == 1, items
    return items[0]


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    from arborlm import p7b_study as study
    from arborlm import p7b_stage as stages
    from arborlm.p6_common import pairs
    from arborlm.p7b_synth import build_identity, synthetic_corpus, write_references

    before = study._listing(REPO / "experiments", REPO / "results")
    stages.registered_roots_refused(root)
    args = study.build_parser().parse_args(["dry-run"])
    args.output_root, args.results_root = root / "experiments", root / "results"
    args.supersede = args.reason = None
    opt = study.Options(args)
    opt.dry_run = opt.synthetic = True
    opt.pair_list, opt.contexts = pairs()[:2], study.DRY_CONTEXTS
    opt.repo = root
    opt.parent_suite = root / "none"
    opt.p5_results = root / "p5-none"
    identity, kept = build_identity(root, opt.pair_list, opt.contexts)
    opt.identity_path = identity.path
    opt.reference_dir = write_references(root, identity, kept)
    opt.selection = opt.labels()
    labels = opt.labels()
    log: dict = {"labels": labels}
    audit = root / "auditor"
    audit.mkdir(exist_ok=True)

    # 1. panel stage, then the auditor's panel tool (synthetic mode, the dry run's own corpus)
    log["panel"] = study.run_panel(opt)[0]
    panel_compact = only(opt.results_root / "panel")
    record = json.loads((panel_compact / "panel_record.json").read_text())
    size = opt.contexts
    rows = {
        "train": synthetic_corpus(1, 400),
        "validation": synthetic_corpus(2, 240),
        "registered_earlier": {k: v["sha256"] for k, v in record["earlier_panels"].items()},
        "note": "dry-run fixture corpus; the 'registered' earlier hashes are the fixture's own",
    }
    (audit / "rows.json").write_text(json.dumps(rows))
    log["panel_tool"] = run_tool([
        str(TOOLS / "independent_panel.py"), "--mode", "synthetic", "--synthetic-rows", str(audit / "rows.json"),
        "--panel-size", str(size), "--train-pool", str(min(4096, 8 * size)),
        "--panel-record", str(panel_compact / "panel_record.json"), "--panel-run-id", panel_compact.name,
        "--out", str(audit / "panel_confirmation.json"), "--detail", str(audit / "panel_detail.json")])
    opt.panel_confirmation = audit / "panel_confirmation.json"

    # 2. layouts stage, then the auditor's layout rebuild
    log["layouts"] = study.run_layouts(opt)[0]
    layout_compact = only(opt.results_root / "layouts")
    log["layout_tool"] = run_tool([
        str(TOOLS / "independent_layouts.py"), "--repo", str(REPO), "--identity", str(identity.path),
        "--base", str(root), "--hash-table", str(layout_compact / "layout_hash_table.json"),
        "--layout-run-id", layout_compact.name, "--labels", *labels,
        "--out", str(audit / "layout_confirmation.json"), "--detail", str(audit / "layout_detail.json")])
    opt.layout_confirmation = audit / "layout_confirmation.json"

    # 3. trace-b (gated on both confirmations), simulate A, simulate B
    log["trace-b"] = study.run_trace_b(opt)[0]
    trace_compact = only(opt.results_root / "trace-b")
    log["simulate-a"] = study.run_simulate(opt, "A")[0]
    log["simulate-b"] = study.run_simulate(opt, "B")[0]
    sim_a, sim_b = only(opt.results_root / "simulate-a"), only(opt.results_root / "simulate-b")

    # 4. the auditor's re-simulation of both streams
    common = ["--repo", str(REPO), "--identity", str(identity.path), "--base", str(root),
              "--hash-table", str(layout_compact / "layout_hash_table.json"), "--selection", *labels]
    log["resim_A"] = run_tool([str(TOOLS / "independent_resim.py"), "--stream", "A", *common,
                               "--simulate-dir", str(sim_a), "--p7a-reference", str(opt.reference_dir),
                               "--out", str(audit / "resim_A.json"), "--detail", str(audit / "resim_A_detail.json")])
    log["resim_B"] = run_tool([str(TOOLS / "independent_resim.py"), "--stream", "B", *common,
                               "--simulate-dir", str(sim_b),
                               "--trace-b-compact", str(trace_compact),
                               "--trace-b-dir", str(opt.output_root / trace_compact.name / "traces"),
                               "--out", str(audit / "resim_B.json"), "--detail", str(audit / "resim_B_detail.json")])
    opt.resim_confirmation_a = audit / "resim_A.json"
    opt.resim_confirmation_b = audit / "resim_B.json"

    # 5. analyze, gated on both re-simulation confirmations
    log["analyze"] = study.run_analyze(opt)[0]
    analysis = json.loads(only(opt.results_root / "analyze").joinpath("analysis.json").read_text())
    log["analysis_streams"] = {k: v["status"] for k, v in analysis["streams"].items()}
    manifest = json.loads(only(opt.results_root / "analyze").joinpath("manifest.json").read_text())
    log["analyze_linkage_resim_sha256"] = {
        k: manifest["linkage"][k]["sha256"] for k in ("resim_confirmation_a", "resim_confirmation_b")}
    after = study._listing(REPO / "experiments", REPO / "results")
    log["repo_experiments_results_unchanged"] = before == after
    print(json.dumps(log, indent=1))
    ok = (all(log[k] == 0 for k in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze"))
          and all(log[k][0] == 0 for k in ("panel_tool", "layout_tool", "resim_A", "resim_B"))
          and log["repo_experiments_results_unchanged"])
    print("DRY SEQUENCE WITH AUDITOR TOOLS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
