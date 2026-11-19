# ruff: noqa: E501
"""P10IS0: the public-output leak guard matches whole tokens, not substrings of opaque identifiers; Stage R's completion line; the status and rebind commands."""

import random
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


def test_random_task_names_never_raise() -> None:
    rng = random.Random(20261119)
    for _ in range(5000):
        ident = rng.choice("tabcdef") + "".join(rng.choice("0123456789abcdef") for _ in range(14))
        stage = f"stage_r_a{rng.randint(0, 3)}_{rng.choice(['base', 'ext'])}_i{rng.randint(0, 9)}"
        for suffix in ("log", "result.json", "failed.json"):
            sealed.validate_public({"hashes": {f"tasks/{stage}/{ident}.{suffix}": H}})
    # a few hundred names of the form the driver writes, all in one map, as the completion line used to print
    sealed.validate_public({"hashes": {f"tasks/stage_r_a0_base_i{i % 6}/t{rng.getrandbits(56):014x}.log": H for i in range(800)}})


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


def test_rebind_identity_needs_a_ruling_and_a_change_confined_to_output_validation(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    ctx = drivers.Ctx(repo, tmp_path / "run", registered=False)
    write_json(repo / core.DURATIONS, ladder.durations_record({}, drivers.code_identity(repo)))
    ruling = tmp_path / "results" / "RULING.md"
    ruling.parent.mkdir()
    ruling.write_text("RULING: the change is confined to output validation\n")
    with pytest.raises(drivers.CodeChanged):
        drivers.check_code_identity(repo)  # unchanged so far: no error
        f = repo / "studies/p10is0/sealed.py"
        f.write_text(f.read_text() + "\n# fix\n")
        drivers.check_code_identity(repo)
    with pytest.raises(drivers.StageRefused, match="ruling file"):
        drivers.cmd_rebind_identity(ctx, tmp_path / "missing.md")
    g = repo / "studies/p10is0/adapter.py"
    g.write_text(g.read_text() + "\n# a training-path change\n")
    with pytest.raises(drivers.StageRefused, match="outside the ruling's scope"):
        drivers.cmd_rebind_identity(ctx, ruling)  # a file of the training path differs: refused
    g.write_text(g.read_text().replace("\n# a training-path change\n", ""))
    out = drivers.cmd_rebind_identity(ctx, ruling)
    assert out["changed_files"] == ["studies/p10is0/sealed.py"]
    drivers.check_code_identity(repo)  # now consistent
    hist = (repo / core.FREEZE_DIR / "durations_identity_rebind.json").read_text()
    assert "ruling_sha256" in hist and "old_identity" in hist
