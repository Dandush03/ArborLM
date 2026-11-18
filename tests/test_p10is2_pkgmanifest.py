# ruff: noqa: E501, F401, F811
"""P10IS2 re-audit R7 and A7: the installed-package manifest of the durable copy (a fake package tree; the real 4,270-file copy is not read here), its verification at stage start, the shadowed lock packages, and the
freeze's refusal without it. Seeds 935001-935999. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_partq_freeze import (  # noqa: E402
    CAP_HOURS,
    FAKE_WALK,
    INPUTS,
    freeze_args,
    measuring_record,
    platform_ok,
    repo,
    set_caps,
)

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partq import (  # noqa: E402
    freeze,
    pkgmanifest,
    stages,  # noqa: E402
)
from studies.p10is2.partq import plan as qplan  # noqa: E402


def dist(site: Path, name: str, version: str, files: dict[str, str]) -> None:
    d = site / f"{name}-{version}.dist-info"
    d.mkdir(parents=True)
    (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
    for rel, text in files.items():
        (site / rel).parent.mkdir(parents=True, exist_ok=True)
        (site / rel).write_text(text)


def fake_trees(tmp: Path) -> tuple[Path, Path]:
    durable, lock = tmp / "durable", tmp / "lock"
    dist(durable, "sacrebleu", "2.5.1", {"sacrebleu/__init__.py": "x = 1\n"})
    dist(durable, "filelock", "4.2.10", {"filelock/__init__.py": "y = 1\n"})
    dist(durable, "typing_extensions", "5.0", {"typing_extensions.py": "z = 1\n"})
    dist(lock, "filelock", "3.0.0", {"filelock/__init__.py": "old\n"})
    dist(lock, "typing-extensions", "5.0", {"typing_extensions.py": "z = 1\n"})
    dist(lock, "torch", "2.8.0", {"torch/__init__.py": ""})
    return durable, lock


def test_the_manifest_names_versions_hashes_and_the_shadowed_lock_packages(tmp_path: Path) -> None:
    durable, lock = fake_trees(tmp_path)
    m = pkgmanifest.build_manifest(durable, lock)
    assert m["packages"] == {"sacrebleu": "2.5.1", "filelock": "4.2.10", "typing-extensions": "5.0"}
    assert m["file_count"] == len(m["files"]) == 6 and all(len(h) == 64 for h in m["files"].values())
    assert m["tree_sha256"] == pkgmanifest.tree_sha256(m["files"])
    assert m["shadowed_lock_packages"] == {"filelock": {"durable_version": "4.2.10", "lock_version": "3.0.0", "same_version": False}, "typing-extensions": {"durable_version": "5.0", "lock_version": "5.0", "same_version": True}}
    assert "torch" not in m["shadowed_lock_packages"] and "sacrebleu" not in m["shadowed_lock_packages"]
    assert json.loads(json.dumps(m)) == m


def test_a_changed_added_or_removed_file_is_paused_identity(tmp_path: Path) -> None:
    durable, lock = fake_trees(tmp_path)
    m = pkgmanifest.build_manifest(durable, lock)
    pkgmanifest.verify_manifest(durable, m)  # untouched: passes
    f = durable / "sacrebleu/__init__.py"
    f.write_text("x = 2\n")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_manifest(durable, m)
    f.write_text("x = 1\n")
    pkgmanifest.verify_manifest(durable, m)  # restored: the stage resumes
    (durable / "extra.py").write_text("")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_manifest(durable, m)
    (durable / "extra.py").unlink()
    f.unlink()
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_manifest(durable, m)
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_manifest(tmp_path / "elsewhere", m)


def test_stage_start_verifies_the_inputs_block_and_the_packages(tmp_path: Path) -> None:
    durable, lock = fake_trees(tmp_path)
    data = tmp_path / "data.bin"
    data.write_bytes(b"abc")
    from arborlm.io import file_sha256

    inputs = {"data": {"path": str(data), "sha256": file_sha256(data)}, pkgmanifest.KEY: pkgmanifest.build_manifest(durable, lock)}
    pkgmanifest.verify_inputs(inputs, uses_packages=True)
    data.write_bytes(b"abd")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_inputs(inputs, uses_packages=False)  # the analysis does not use packages but still checks its file inputs
    data.write_bytes(b"abc")
    (durable / "sacrebleu/__init__.py").write_text("changed")
    pkgmanifest.verify_inputs(inputs, uses_packages=False)
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_inputs(inputs, uses_packages=True)


def test_a_registered_stage_builds_no_world_when_the_package_copy_differs(tmp_path: Path) -> None:
    from studies.p10is2.partq import real_stages

    durable, lock = fake_trees(tmp_path)
    m = pkgmanifest.build_manifest(durable, lock)
    (durable / "sacrebleu/__init__.py").write_text("changed")
    plan = planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "Q", "inputs": {pkgmanifest.KEY: m}}, "Q")
    cfg = core.load_config("Q")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        real_stages.build_world(cfg, core.ROOT, tmp_path / "run", "registered", load_teachers=False, plan=plan)


def test_the_package_manifest_command_merges_into_an_inputs_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    durable, lock = fake_trees(tmp_path)
    monkeypatch.setattr(core, "load_config", lambda part, path=None: {"paths": {"durable_packages": str(durable)}})
    target = tmp_path / "inputs.json"
    target.write_text(json.dumps({"downloads": {"path": "/x", "sha256": "0" * 64}}))
    assert stages.main(["package-manifest", "--merge-into", str(target), "--lock-site-packages", str(lock)]) == 0
    merged = json.loads(target.read_text())
    assert "downloads" in merged and merged[pkgmanifest.KEY]["file_count"] == 6
    assert stages.main(["package-manifest", "--lock-site-packages", str(lock)]) == 2  # exactly one of --out and --merge-into


def test_the_freeze_refuses_a_plan_without_the_package_manifest(repo: Path, tmp_path: Path, platform_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planmod, "import_walk", lambda *a, **k: FAKE_WALK)
    units, rates = {k: 100.0 for k in qplan.STAGES}, {k: 36.0 for k in qplan.STAGES}
    set_caps(repo, qplan.caps_proposal(3600.0, qplan.project_stage_seconds(units, rates)))
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    bare = {k: v for k, v in INPUTS.items() if k != pkgmanifest.KEY}
    qplan.write_candidate(repo, qplan.build_candidate(repo, repo / "runs", cfg, inputs=bare, walk=FAKE_WALK))
    measuring_record(tmp_path, units, rates)
    with pytest.raises(core.StageRefused, match="installed-package manifest"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path))


def test_not_run_by_rule_exits_zero_and_a_refusal_does_not(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from studies.p10is2.partq import real

    monkeypatch.setattr(stages, "refuse_unless_registered_ready", lambda *a, **k: object())
    monkeypatch.setattr(real, "run_registered_stage", lambda *a, **k: {"status": "NOT RUN BY RULE"})
    assert stages.main(["registered", "--stage", "generation", "--run-dir", str(tmp_path)]) == 0
    monkeypatch.setattr(real, "run_registered_stage", lambda *a, **k: {"status": "PAUSED"})
    assert stages.main(["registered", "--stage", "generation", "--run-dir", str(tmp_path)]) == 4
