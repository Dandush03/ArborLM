# ruff: noqa: E501
"""R14 (the report prints what the ADR prints with each line) and R11 (the keep-awake watcher is the stage's own process family, ADR-0025 audit; the defect that hung P10-I-S5 for 2.5 hours). Self-check only."""

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import psutil  # noqa: E402
import pytest  # noqa: E402
from p10is2_partt_fixtures import quantities  # noqa: E402

from studies.p10is2 import annotations, partt_plan, report  # noqa: E402
from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2.common import procs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_the_report_prints_the_tables_companions_annotations_and_cost_lines() -> None:
    q = quantities()
    derived = L.derive_all(q)
    ctx: dict[str, Any] = {"U": 2000, "converged": True, "draws": "DISJOINT DRAWS", "shared_share": {}, "annotations": {a["name"]: a for a in (annotations.no_advantage_over_separate(q),)}, "cost_lines": ["counted training multiply-adds per update, M-append: 1.0e9 (logical work)"]}
    text = report.render(L.study_status(q.reg, required=partt_plan.required_keys()), derived, ctx)
    for must in ("ACQUISITION table, G_first(M1)", "ACQUISITION table, ACQ2", "RETENTION table, rho", "RETENTION table, evaluable_cells_in_negative_zone", "AGAINST-DENSE per-cell delta_G", "AGAINST-DENSE per-cell delta_rho",
                 "GENERAL-QUALITY per-cell loss increases", "AGAINST-LOOKUP per cell", "ANNOTATION NO ADVANTAGE OVER SEPARATE ADAPTERS", "COST: counted training multiply-adds per update", "DISCLOSED LIMITATION (ruling 19)"):
        assert must in text, must
    assert all(b.split("\n")[0] == core_oracle() for b in text.split("\n\n"))  # every block still starts with the fixed line (the renderer's own check passed)


def core_oracle() -> str:
    from studies.p10is2.common import core

    return core.ORACLE_LINE


def test_the_companions_of_an_inconclusive_acquisition_and_controls_undefined_are_printed() -> None:
    derived = {"ACQUISITION": {"label": "ACQUISITION-INCONCLUSIVE", "table": {"CONTROLS UNDEFINED": ["0AB:A"], "ACQ1": {"0AB": True}}, "passing_cells_per_order": {"ACQ1": {"AB": 3, "BA": 2}}, "why": "x"}}
    text = "\n\n".join(report.companion_blocks(derived, {"U": 2000, "converged": True}))
    assert "ACQUISITION table, CONTROLS UNDEFINED: [0AB:A]" in text and "ACQUISITION passing cells per order: {ACQ1: {AB: 3, BA: 2}}" in text


def test_a_keep_awake_process_is_never_another_study_nor_a_second_instance_of_this_one(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = [
        SimpleNamespace(info={"pid": 90001, "cmdline": ["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())]}),
        SimpleNamespace(info={"pid": 90002, "cmdline": ["/usr/bin/caffeinate", "-i", "uv", "run", "python", "-m", "studies.p10is2.partt_stages", "work"]}),  # a WRAPPER that carries the stage's command line
        SimpleNamespace(info={"pid": 90003, "cmdline": ["/usr/bin/caffeinate", "-i", "uv", "run", "python", "-m", "studies.p10is5.stages"]}),
        SimpleNamespace(info={"pid": 90004, "cmdline": ["python", "-m", "studies.p10is5.stages", "run"]}),
        SimpleNamespace(info={"pid": 90005, "cmdline": ["python", "-m", "studies.p10is2.partt_stages", "work"]}),
    ]
    monkeypatch.setattr(procs.psutil, "process_iter", lambda attrs=None: iter(fake))
    assert procs.other_studies_alive() == ["python -m studies.p10is5.stages run"]  # the watchers (90001-90003) are not another study; the real one (90004) is
    assert procs.own_study_alive() == ["python -m studies.p10is2.partt_stages work"]  # the wrapper (90002) is not a second instance of this study


@pytest.mark.skipif(platform.system() != "Darwin" or shutil.which("caffeinate") is None, reason="caffeinate is macOS's")
def test_the_launch_scripts_start_the_watcher_on_the_stages_own_pid_and_it_ends_with_the_stage() -> None:
    for name in ("partt_registered.sh", "partt_rehearse.sh"):
        text = (ROOT / "studies/p10is2/launch" / name).read_text()
        calls = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("caffeinate")]
        assert calls == ["caffeinate -i -w $$ >/dev/null 2>&1 &"]  # the only call, on the stage's own pid; never a bare caffeinate -i
        assert text.index("caffeinate -i -w $$") < text.index("exec uv run")  # started before the exec, which keeps the pid
    out = subprocess.run(["sh", "-c", 'if command -v caffeinate >/dev/null 2>&1; then caffeinate -i -w $$ >/dev/null 2>&1 & echo $!; fi; exec sleep 1'], capture_output=True, text=True, timeout=30, check=True)  # noqa: S603, S607
    pid = int(out.stdout.strip())
    deadline = time.monotonic() + 10.0
    while psutil.pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE  # the watcher ended when the stage's pid ended (no hanging process)
