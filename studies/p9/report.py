# ruff: noqa: E501
"""P9 reporting (package I6): decision map, study status, CSV/JSON/Markdown and the dashboard.

Specification: ADR-0017 section 8.6 (study status ENGINEERING_FAIL / INCOMPLETE; the denominator is
never reduced), 8.7 (decision map), 13 (what must not be claimed). STUB: signatures only.

Labelling rule for every number written: measured, analytical or hypothetical; logical work is never
described as a speedup; every report states "Astra review: NOT_PERFORMED" and that Claude review is
not Astra review and not human approval.
"""

from collections.abc import Sequence
from pathlib import Path

from .core import ClassResult, StageManifest

STATUSES = ("COMPLETE", "INCOMPLETE", "ENGINEERING_FAIL")
LABELS = ("measured", "analytical", "hypothetical")


def study_status(manifests: Sequence[StageManifest], engineering_defects: Sequence[str]) -> str:
    """ENGINEERING_FAIL for identity, determinism, checkpoint or gradient-reach defects only (a
    regularizer being inactive is a recorded property, not a failure); INCOMPLETE if any registered
    cell lacks a record (no class for a lane with a missing mandatory cell); else COMPLETE."""
    raise NotImplementedError


def missing_cells(manifests: Sequence[StageManifest]) -> list[str]:
    """Registered labels with no completed record in any manifest (``core.all_labels``)."""
    raise NotImplementedError


def decision_map(results: Sequence[ClassResult], status: str) -> list[str]:
    """The five-item decision map of ADR 8.7 as sentences, from the lane results; item 1 requires the
    human lead's explicit acceptance when the optimizer annotation reads OPTIMIZER-ARM UNINFORMATIVE or
    'OPTIMIZER-DEPENDENT: not assessed'. No outcome authorizes further training, storage experiments or
    scaling."""
    raise NotImplementedError


def results_table(results: Sequence[ClassResult]) -> list[dict[str, object]]:
    """Flat rows (lane, subject, class, annotations, key numbers) for CSV and JSON."""
    raise NotImplementedError


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    raise NotImplementedError


def render_markdown(results: Sequence[ClassResult], status: str, decisions: Sequence[str]) -> str:
    """The Markdown report; includes the evidence boundary, what must not be claimed (ADR 13) and the
    status of reviews."""
    raise NotImplementedError


def render_dashboard(
    results: Sequence[ClassResult], manifests: Sequence[StageManifest], status: str
) -> str:
    """Self-contained static HTML dashboard (no network, no external assets)."""
    raise NotImplementedError


def write_report(
    run_dir: Path, results_dir: Path, results: Sequence[ClassResult], status: str
) -> list[Path]:
    """Write ``results.json``, ``results.csv``, ``REPORT.md`` and ``dashboard.html`` under
    ``results_dir`` through ``core`` record IO and hashes; returns the paths."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
