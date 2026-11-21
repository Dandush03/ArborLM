# ruff: noqa: E501
"""Part Q's stages launched the way the real run launches them: through ``partq_registered.sh`` (and ``partq_rehearse.sh counting``), in a FRESH process per stage, in order, in a synthetic FROZEN repository (plan, freeze
record, committed Decision 2). Un-stubbed apart from the downloads and the teachers (``p10is2_e2e_world``): the launch script, the entry point, the platform check, the plan checks, ``run_stage``, ``build_world``, every
stage body and P10-S2's functions are the real code. Written after the registered run's first stage refused on a defect the counting rehearsal had passed. Self-check only."""

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10is2_launch import freeze, git, make_repo  # noqa: E402
from test_p10is2_pkgmanifest import dist  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common.panel_ledger import RowMap  # noqa: E402
from studies.p10is2.partq import counting, pkgmanifest, real_stages, step8  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
ON_RECORD = platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"
pytestmark = pytest.mark.skipif(not ON_RECORD, reason="the platform of record (the platform check is the real one)")


def fake_uv(tmp: Path, overhead: float = 0.0) -> dict[str, str]:
    """A ``uv`` that runs the child through ``p10is2_e2e_hook.py`` with the lock environment's interpreter and NO PYTHONPATH (a test never puts the durable packages on a path)."""
    bindir = tmp / "bin"
    bindir.mkdir()
    uv = bindir / "uv"
    uv.write_text('#!/bin/sh\nwhile [ "$1" != "python" ]; do shift; done\nshift\nshift\nunset PYTHONPATH\nexec "$E2E_PY" "$E2E_HOOK" "$@"\n')
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    env.update(PATH=f"{bindir}:{env['PATH']}", E2E_PY=sys.executable, E2E_HOOK=str(TESTS / "p10is2_e2e_hook.py"), E2E_SRC=str(ROOT / "src"), E2E_ROOT=str(ROOT), E2E_TESTS=str(TESTS), E2E_OVERHEAD=str(overhead), PYTHONDONTWRITEBYTECODE="1")
    return env


def synthetic_base(tmp: Path) -> tuple[Path, dict]:  # type: ignore[type-arg]
    """The synthetic repository (scaled config, the study's windows in a shared ledger written with test seeds) and the plan's inputs block; no plan yet."""
    import p10is2_e2e_world as world

    r = make_repo(tmp)
    (r / "studies/__init__.py").write_text((ROOT / "studies/__init__.py").read_text())
    adr = r / "docs/decisions/ADR-0004-real-data-pilot-prerequisite.md"  # read for its hash by the world builder (its pins are the faked part)
    adr.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / adr.relative_to(r), adr)
    ledger = tmp / "panel_ledger.json"
    cfg_path = r / core.CONFIG_Q
    cfg_path.write_text(world.scaled_config_text(cfg_path.read_text(), ledger))
    cfg = core.load_config("Q", cfg_path)
    w = world.make_world(cfg, r, tmp / "w")
    _grid, marker, ordinary = real_stages.window_candidates(w, cfg)
    step8.write_study_ledger(cfg, "test", ledger, marker, ordinary, row_map=RowMap.from_rows(w.wikitext_rows["validation"]))  # the ONE pre-freeze ledger step, on the synthetic text, with test seeds
    durable = tmp / "durable"
    dist(durable, "sacrebleu", "2.5.1", {"sacrebleu/__init__.py": "x = 1\n"})
    data = tmp / "in.bin"
    data.write_bytes(b"abc")
    inputs = {"data": {"path": str(data), "sha256": file_sha256(data)}, pkgmanifest.KEY: pkgmanifest.build_manifest(durable, None)}
    return r, inputs


def synthetic_repo(tmp: Path, *, decision: bool = True, record: bool = True) -> tuple[Path, str]:
    r, inputs = synthetic_base(tmp)
    commit = freeze(r, "Q", decision=decision, inputs=inputs, record=record)
    return r, commit


def launch(r: Path, env: dict[str, str], stage: str, commit: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_registered.sh"), stage, str(r / "runs"), commit, *extra], cwd=r, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607


def test_every_registered_stage_launches_through_the_launch_script_in_order_and_ends_in_a_label(tmp_path: Path) -> None:
    r, commit = synthetic_repo(tmp_path)
    assert git(r, "status", "--porcelain") == ""
    env = fake_uv(tmp_path)
    for stage in real_stages.STAGE_ORDER:
        out = launch(r, env, stage, commit)
        assert out.returncode == 0, (stage, out.stderr[-1500:])
        assert real_stages.completion_path(r / "runs", stage).is_file(), stage
    label = json.loads((r / "runs/qualification.json").read_text())["label"]
    assert label.startswith("QUALIFICATION-") or "TEACHERS-QUALIFIED" in label or "NEGATIVE" in label, label
    assert json.loads((r / "runs/stages/outputs.complete.json").read_text())["status"] == "COMPLETE"  # the outputs ran: both teachers qualified on this synthetic data
    assert git(r, "status", "--porcelain") == ""  # nothing of the run is in the tree
    run = r / "runs"  # the Part Q manifest is true once the analysis has ended: every listed file re-hashes to its entry, none is missing, none of the volatile files is listed
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["files"] and manifest["excluded"]
    for rel, digest in manifest["files"].items():
        assert (run / rel).is_file(), f"{rel} is listed and missing"
        assert file_sha256(run / rel) == digest, f"{rel} changed after the manifest was written"
    assert not [k for k in manifest["files"] if k.startswith("stages/") or k.endswith("charged_ledger.json") or k == "manifest.json" or k.count("/") == 1 and k.endswith("/manifest.json")]
    assert "qualification.json" in manifest["files"]  # the analysis's own result is listed
    listed = set(manifest["files"])
    on_disk = {str(f.relative_to(run)) for f in run.rglob("*") if f.is_file()}
    left_out = {k for k in on_disk - listed if not (k.startswith(("stages/", "sealed/", "logs/")) or k in ("charged_ledger.json", "manifest.json") or k.count("/") == 1 and k.endswith("/manifest.json"))}
    assert left_out == set(), left_out  # every other file of the run directory is listed


def test_the_counting_rehearsal_drives_the_same_entry_point_in_a_fresh_process_per_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r, _commit = synthetic_repo(tmp_path, decision=False, record=False)  # a candidate plan only: the counting rehearsal runs before the freeze and has no Decision 2
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    rec = counting.run_counting_rehearsal(r, r / "runs" / "counting")
    assert rec["status"] == "COMPLETE" and rec["forced"] == {"pause_resume": True, "paused_identity_restore": True}
    assert set(rec["stages"]) == set(real_stages.STAGE_ORDER) and all(v["status"] == "COMPLETE" for v in rec["stages"].values())
    logs = sorted(p.name for p in (r / "runs/counting/logs").iterdir())
    assert "generation-forced-pause.log" in logs and "qfit-identity-altered-plan.log" in logs and "analysis.log" in logs  # one fresh process per stage, the forced pause and the forced identity difference among them
    assert (r / "runs/counting/sealed/rehearsal_values.json").is_file() and not (r / "studies/p10is2/freeze/partq_plan_altered.json").exists()


def test_an_input_that_differs_stops_the_registered_stage_and_the_counting_rehearsal_alike(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r, commit = synthetic_repo(tmp_path)
    env = fake_uv(tmp_path)
    (tmp_path / "in.bin").write_bytes(b"changed")  # the plan's input file now differs from the hash it recorded
    out = launch(r, env, "inputs", commit)
    assert out.returncode == 75 and "PAUSED — IDENTITY" in out.stderr and not real_stages.completion_path(r / "runs", "inputs").exists()


def test_the_counting_rehearsal_stops_on_an_input_that_differs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r, _commit = synthetic_repo(tmp_path, decision=False, record=False)
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    (tmp_path / "in.bin").write_bytes(b"changed")
    with pytest.raises(core.StageRefused, match="inputs: exit 75"):  # the rehearsal runs the same check in the same entry point
        counting.run_counting_rehearsal(r, r / "runs" / "counting")
