"""Auditor demonstration (synthetic, dry-run flag, scratch folder): the analyze stage does not refuse to
run when the p7a sources differ from those recorded by the simulate stage it consumes.

The change of sources is simulated by patching ``p7a_core.source_hashes`` after the simulate stage
(no file is edited). Expected behaviour if guarded: run_analyze refuses. Observed: printed below.
Run: uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_analyze_source_guard.py <scratch>
"""

import argparse
import sys
from pathlib import Path

from arborlm import p6_common as common
from arborlm import p7a_core as core
from arborlm import p7a_study as study
from arborlm.io import read_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch", type=Path)
    root = ap.parse_args().scratch.resolve()
    args = argparse.Namespace(
        data_dir=root / "d", parent_suite=root / "s", output_root=root / "experiments",
        results_root=root / "results", p5_results=root / "p5", supersede=None, reason=None,
    )
    opt = study.Options(args)
    opt.dry_run, opt.synthetic = True, True
    opt.pair_list, opt.contexts = common.pairs()[:1], 4
    assert study.run_trace(opt)[0] == 0
    assert study.run_simulate(opt)[0] == 0
    real = core.source_hashes()
    changed = {**real, "src/arborlm/p7a_analysis.py": "0" * 64}
    core.source_hashes = lambda root=None: changed  # type: ignore[assignment]
    try:
        code, run = study.run_analyze(opt)
    except Exception as exc:  # a guard would raise here
        print("analyze REFUSED:", type(exc).__name__, exc)
        return 0
    sim = read_json(next((opt.results_root / "simulate").iterdir()) / "manifest.json")
    ana = read_json(opt.results_root / "analyze" / run.name / "manifest.json")
    print("analyze exit code:", code, "status:", ana["status"])
    print("simulate manifest p7a_analysis.py:", sim["p7a_source_sha256"]["src/arborlm/p7a_analysis.py"])
    print("analyze  manifest p7a_analysis.py:", ana["p7a_source_sha256"]["src/arborlm/p7a_analysis.py"])
    print("=> analyze completed with sources different from the simulate stage (no guard)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
