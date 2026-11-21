# ruff: noqa: E501
"""P10-I-S1 analysis supplement (ADR-0024 addendum on the analysis loader defect; the P10-S1 ADR-0021 section 25.21 precedent). A NEW file outside every frozen root.

The registered ``analysis`` and ``report`` stages cannot run: the frozen ``stages.build_registry`` reads every ``run_dir/baselines/*.json`` as a ``baseline`` record, and the baselines STAGE MANIFEST
(``baselines/manifest.json``, kind ``stage_manifest``) matches. This driver

* runs the registered pre-checks (``check_preconditions``, ``load_registered_plan``, ``verify_plan``, ``require_decision_2``, ``require_ignored_run_dir``: the same frozen functions as ``cmd_registered``);
* refuses unless the evaluate and baselines stage manifests are COMPLETE;
* builds the registry by calling the FROZEN ``stages.build_registry`` unchanged, on a path object whose ``baselines`` directory lists only the baseline record files (``d<draw>_f<facts>.json``, never ``manifest.json``) — the
  one difference from the registered loader; every other read of the frozen function is the registered one;
* calls the FROZEN ``analysis.analyze`` and ``report.render`` unchanged, on that registry (the registered ``rehearsal_record_of`` supplies the R2 table, as in the registered analysis stage);
* writes ONLY to a NEW directory beside the run, ``<run dir>-analysis-supplement`` (never under the run directory, never overwriting: it must not exist), and labels every output with ``LABEL``;
* records the registered analysis and report stages as ``ENGINEERING STOP — ANALYSIS LOADER DEFECT`` with the traceback TAILS of the two crashes, taken from the ``analysis`` and ``report`` sections of the stage-output file (truncated
  to each stage's last 1,500 bytes; only frame, source/caret and exception lines; no line beginning ``{``); it refuses unless exactly two are found.

It is NOT the registered analysis stage. Usage: PYTHONPATH=<worktree>/src:<worktree> timeout 3000 <venv python> run_analysis_supplement.py --run-dir <run dir> --freeze-commit <full hash> --stages-out <stage output file>
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path, PosixPath
from typing import Any

LABEL = "frozen analysis function on the registered records, through a disclosed corrected loader — not the registered analysis stage"
STOP = "ENGINEERING STOP — ANALYSIS LOADER DEFECT"
BASELINE_RECORD_FILE = re.compile(r"d\d+_f\d+\.json")


class RunDir(PosixPath):
    """The run directory as the frozen loader sees it: identical to the real one in every respect except that ``baselines/``'s ``glob`` lists baseline record files only (the corrected loader; Python 3.12 path subclass)."""

    def glob(self, pattern: str, **kw: Any) -> Any:
        found = super().glob(pattern, **kw)
        return (p for p in found if BASELINE_RECORD_FILE.fullmatch(p.name)) if self.name == "baselines" else found


EXCEPTION_LINE = re.compile(r"^[A-Za-z_][\w.]*(Error|Exception|Exit|Interrupt|Warning)(: .*)?$")
TAIL_NOTE = "the tracebacks are the TRUNCATED TAILS that were captured: each stage's output in the stage-output file was cut to its last 1,500 bytes, so a section may begin mid-line (a caret line, the tail of a frame) and holds no 'Traceback (most recent call last):' header"


def extract_tracebacks(text: str) -> list[str]:
    """The captured traceback tail of the ``analysis`` and of the ``report`` section of the stage-output file (``=== <stage> <date>`` ... ``=== <stage> exit=<n>``), in that order. The file is truncated (each stage's output
    is cut to its last 1,500 bytes), so there is no ``Traceback`` header to look for. Within a section only frame lines (``  File ...``), the indented source and caret lines and the final exception line are kept; any line that
    begins with ``{`` (a stage result line) and every other line is dropped. A section without an ending exception line is not a block. Returns the blocks found (the caller requires exactly two)."""
    lines = text.splitlines()
    out: list[str] = []
    for name in ("analysis", "report"):
        start = next((i for i, ln in enumerate(lines) if ln.startswith(f"=== {name} ") and not ln.startswith(f"=== {name} exit=")), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(f"=== {name} exit=")), len(lines))
        kept: list[str] = []
        for ln in lines[start + 1 : end]:
            if ln.startswith(("{", "===")) or not ln.strip():
                continue
            if ln[0].isspace() or set(ln) <= set("^~ ") or EXCEPTION_LINE.match(ln):
                kept.append(ln)
        if kept and EXCEPTION_LINE.match(kept[-1]) and not kept[-1][0].isspace():
            out.append("\n".join(kept))
    return out


def manifest_status(run_dir: Path, stage: str) -> str:
    from studies.p10is1 import core

    p = run_dir / stage / "manifest.json"
    return str(core.read_record(p, "stage_manifest")["status"]) if p.is_file() else "ABSENT"


def build_registry(ctx: Any, pl: Any, run_dir: Path, rehearsal_record: Any = None) -> Any:
    """The corrected loader: the frozen ``build_registry`` on ``RunDir(run_dir)``."""
    from studies.p10is1 import stages

    return stages.build_registry(ctx, pl, RunDir(run_dir), rehearsal_record=rehearsal_record)


def supplement_dir_of(run_dir: Path) -> Path:
    return run_dir.parent / f"{run_dir.name}-analysis-supplement"


def produce(ctx: Any, pl: Any, run_dir: Path, out: Path, *, rehearsal_record: Any, stages_text: str, identity: dict[str, str], repo: Path | None = None) -> dict[str, Any]:
    """The supplement proper. Refuses unless evaluate and baselines are COMPLETE and ``out`` is new; writes only under ``out``."""
    from studies.p10is1 import analysis, core, quiet, report, stages

    if out.resolve() == run_dir.resolve() or run_dir.resolve() in out.resolve().parents:
        raise SystemExit(f"refused: {out} lies inside the run directory: the supplement is written beside it, never into it")
    if repo is not None and (out.resolve() == repo.resolve() or repo.resolve() in out.resolve().parents):
        raise SystemExit(f"refused: {out} lies inside the repository or worktree: a supplement written there would dirty the tree and break the identity checks of every later stage")
    tbs = extract_tracebacks(stages_text)
    if len(tbs) != 2:
        raise SystemExit(f"refused: exactly two captured tracebacks (the analysis and the report section of the stage-output file) are required to record the engineering stop; {len(tbs)} were found")
    state = {s: manifest_status(run_dir, s) for s in ("evaluate", "baselines")}
    if set(state.values()) != {"COMPLETE"}:
        raise SystemExit(f"refused: the evaluate and baselines stage manifests must both be COMPLETE: {state}")
    if out.exists():
        raise SystemExit(f"refused: {out} exists: the supplement is written once, never overwritten")
    out.mkdir(parents=True)
    s_path = out / "ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json"
    core.write_record(
        s_path,
        {**core.envelope("engineering_stop"), "label": LABEL, "status": STOP, "stages": {"analysis": f"{STOP} (not run to completion: crashed)", "report": f"{STOP} (not run: analysis.json missing)"}, "tracebacks": tbs, "traceback_count": len(tbs), "tracebacks_note": TAIL_NOTE, "section_headers": [ln for ln in stages_text.splitlines() if ln.startswith(("=== analysis ", "=== report ")) and " exit=" not in ln],
         "cause": "stages.build_registry reads run_dir/baselines/*.json as baseline records; the baselines stage manifest baselines/manifest.json (kind stage_manifest) matches", "addendum": "docs/decisions/ADR-0024-addendum-analysis-loader-defect.md"},
    )  # fmt: skip
    errs = stages.item_errors(run_dir)
    reg = build_registry(ctx, pl, run_dir, rehearsal_record)
    res = analysis.analyze(reg)
    res_json = json.loads(json.dumps(core.jsonable(res)))  # what the registered stage writes and the registered report reads back
    a_path = out / "analysis" / "analysis_supplement.json"
    core.write_record(a_path, {**core.envelope("analysis"), "label": LABEL, "item_errors": errs, "result": res_json})
    label_throughput = quiet.throughput_label(run_dir)
    text = report.render(res_json, throughput={"state": {"MEASURED": "MEASURED", "THROUGHPUT NOT MEASURED": "NOT MEASURED"}.get(label_throughput, "PAUSED")}, caps=pl.data["stage_caps"])
    r_path = out / "report" / "REPORT_SUPPLEMENT.md"
    r_path.parent.mkdir(parents=True)
    r_path.write_text(f"> **{LABEL}**\n> Registered analysis and report stages: {STOP}. See docs/decisions/ADR-0024-addendum-analysis-loader-defect.md.\n\n{text}", encoding="utf-8")
    files = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file()}
    m_path = out / "SUPPLEMENT_MANIFEST.json"
    core.write_record(
        m_path,
        {**core.envelope("report_manifest"), "label": LABEL, "run_dir": str(run_dir), "supplement_dir": str(out), "created_utc": datetime.now(UTC).isoformat(), "stage_manifests": state, "identity_checks": identity, "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "registry_counts": {"cells": len(reg.cells), "reads": len(reg.reads), "baselines": len(reg.baselines), "ladder_stops": len(reg.ladder_stops)}, "analysis_status": res_json.get("status"), "item_errors": len(errs), "files_sha256": files},
    )  # fmt: skip
    return {"supplement_dir": str(out), "analysis_status": res_json.get("status"), "item_errors": errs}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--freeze-commit", required=True)
    ap.add_argument("--stages-out", required=True, help="the stage-output file holding the two tracebacks (only Traceback blocks are read into the record)")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--supplement-dir", help="a NEW directory beside the run (default: <run dir>-analysis-supplement); needed to try again after a refusal that left one behind")
    a = ap.parse_args(argv)
    from studies.p10is1 import core, freeze, gates, stages
    from studies.p10is1 import plan as planmod

    repo, run_dir = Path(a.repo), Path(a.run_dir)
    gates.configure_worker()
    try:
        planmod.check_preconditions(core.REGISTERED, repo, a.freeze_commit)
        pl = planmod.load_registered_plan(repo)
        planmod.verify_plan(pl, repo, run_dir, freeze_commit=a.freeze_commit)
        planmod.require_decision_2(repo, a.freeze_commit)
        planmod.require_ignored_run_dir(repo, run_dir)
        ctx = stages.ctx_for(pl, run_dir, experiments_root=freeze.experiments_root())
        rec = stages.rehearsal_record_of(pl, repo)
        res = produce(ctx, pl, run_dir, Path(a.supplement_dir) if a.supplement_dir else supplement_dir_of(run_dir), rehearsal_record=rec, stages_text=Path(a.stages_out).read_text(encoding="utf-8", errors="replace"), identity={"check_preconditions": "PASS", "verify_plan": "PASS", "require_decision_2": "PASS"}, repo=repo)
    except core.StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"label": LABEL, **res}))
    return 0 if not res["item_errors"] else 3


if __name__ == "__main__":
    sys.exit(main())
