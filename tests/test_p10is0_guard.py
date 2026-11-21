# ruff: noqa: E501
"""P10IS0: the public-output leak guard matches whole tokens, not substrings of opaque identifiers; Stage R's completion line; the status and rebind commands."""

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is0 import core, drivers, labels, ladder, sealed  # noqa: E402

CFG = core.load_config()
H = "a" * 64


def test_the_reported_key_passes_and_hash_values_must_be_64_hex() -> None:
    key = "tasks/stage_r_a0_base_i4/t1af0a449caccd5.log"  # "acc" inside "caccd5": the false positive that crashed stage-r
    sealed.validate_public({"hashes": {key: H}})
    sealed.validate_public({"stage": "R", "status": "COMPLETE", "hashes": {key: H, "cal/CAL-S-A5-D-2K-512-d01-i330099/updates_00000000.jsonl": H, "2K-512-A6-c1-r0-e8.json": H, "model.pt": H}})
    for bad in ("0.93", "a" * 63, "A" * 64, "g" * 64, "", 5, None):
        with pytest.raises(sealed.PublicOutputError, match="64-hex"):
            sealed.validate_public({"hashes": {key: bad}})
    with pytest.raises(sealed.PublicOutputError, match="64-hex"):
        sealed.validate_public({"sealed_files_sha256": {"x.json": "0.5"}})


@pytest.mark.parametrize("name", ["accuracy", "recall_at_1", "mean_acc", "meanAcc", "m_p", "plateau_value", "train_loss", "bits_per_fact", "curve_x", "correct"])
def test_a_measure_name_is_still_refused(name: str) -> None:
    assert sealed.names_a_measure(name)
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"status": "x", "cell_types": {name: {}}})  # an ordinary key
    with pytest.raises(sealed.PublicOutputError, match="forbidden measure"):
        sealed.validate_public({"hashes": {f"cal/{name}.json": H}})  # a path component that IS a measure name, in a hashes map
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({name: 1})


def test_ordinary_keys_are_not_weakened() -> None:
    with pytest.raises(sealed.PublicOutputError, match="not allowed"):
        sealed.validate_public({"acc": 0.9})
    with pytest.raises(sealed.PublicOutputError, match="not allowed"):
        sealed.validate_public({"stage": "R", "labels_extra": 1})
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"stage": "R", "tasks": {"accuracy_a": 1}})
    assert not any(sealed.names_a_measure(x) for x in ("stage_r_a0_base_i4", "taskstats-stage_r_a0_base_i0-20261118T101010Z.json", "extensions-r0.json", "tasksalt-r0.json", "convergence", "snapshots/u0000008/model.pt"))


def copy_repo(tmp: Path) -> Path:
    root = tmp / "repo"
    shutil.copytree(REPO / "studies", root / "studies", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "freeze"))
    shutil.copytree(REPO / "configs", root / "configs")
    (root / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    return root


def test_stage_r_status_prints_the_completion_line_and_writes_only_missing_event_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = copy_repo(tmp_path)
    ctx = drivers.Ctx(repo, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    sealed.write_sealed(tmp_path / "store", "2K-512-A6-c1-r0-e8.json", {"obs": {}})
    ent = {"8K/16K": {"convergence": labels.NOT_SHOWN_REFUSED, "reference_flags": {"cond4": False, "other": []}}}
    write_json(repo / core.DURATIONS, ladder.durations_record(ent, drivers.code_identity(repo)))
    monkeypatch.setattr(sealed, "read_sealed", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a sealed value was read")))
    events = tmp_path / "results"
    r = drivers.cmd_stage_r_status(ctx, events_dir=events)
    out = capsys.readouterr().out
    assert r["status"] == "COMPLETE" and r["event_files_written"] == ["EVENT_1.md"] and '"stage": "R"' in out and '"sealed_digest"' in out and "2K-512" not in out
    (events / "EVENT_1.md").write_text("kept")
    r2 = drivers.cmd_stage_r_status(ctx, events_dir=events)
    assert r2["event_files_written"] == [] and (events / "EVENT_1.md").read_text() == "kept"  # never overwritten
    (repo / core.DURATIONS).unlink()
    with pytest.raises(drivers.StageRefused, match="not finished"):
        drivers.cmd_stage_r_status(ctx)
