from pathlib import Path
from typing import Any

import pytest
import torch

from arborlm import checkpoint
from arborlm.data import generate_dataset
from arborlm.engine import optimizer_for, train_step
from arborlm.io import file_sha256, read_json, write_json
from arborlm.model import DenseBaseline


@pytest.fixture
def trained() -> tuple[Any, Any, dict[str, str]]:
    # Unit-test fixture: state shape/counters only; it is not an accepted E0 experiment.
    model = DenseBaseline()
    optimizer = optimizer_for(model)
    data = generate_dataset()
    before = [p.detach().clone() for p in model.parameters()]
    for _ in range(16):
        train_step(model, optimizer, data.train[:8])
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    assert any(not torch.equal(p, old) for p, old in zip(model.parameters(), before, strict=True))
    return model, optimizer, {"unit_fixture": "only"}


def test_checkpoint_roundtrip_and_no_replacement(tmp_path: Path, trained: tuple[Any, ...]) -> None:
    model, opt, identity = trained
    destination = tmp_path / "checkpoint-16"
    digest = checkpoint.save_checkpoint(destination, model, opt, 16, identity)
    state = checkpoint.read_checkpoint(destination, model, opt, identity)
    assert checkpoint.restore_checkpoint(state, model, opt) == (16, 128, 4096)
    with pytest.raises(FileExistsError):
        checkpoint.save_checkpoint(destination, model, opt, 16, identity)
    assert file_sha256(destination / "state.pt") == digest
    vacant = tmp_path / "vacant"
    vacant.mkdir()
    with pytest.raises(FileExistsError):
        checkpoint._publish_exclusive(destination, vacant)
    assert destination.is_dir() and not list(vacant.iterdir())


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("hash", "checksum"),
        ("index_version", "schema"),
        ("state_version", "schema"),
        ("identity", "identity"),
        ("missing", "fields"),
        ("optimizer", "entries incomplete"),
    ],
)
def test_checkpoint_rejects_corruption(
    tmp_path: Path,
    trained: tuple[Any, ...],
    damage: str,
    message: str,
) -> None:
    model, opt, identity = trained
    destination = tmp_path / "checkpoint-16"
    checkpoint.save_checkpoint(destination, model, opt, 16, identity)
    index_path, state_path = destination / "index.json", destination / "state.pt"
    index = read_json(index_path)
    if damage == "hash":
        state_path.write_bytes(b"corrupt")
    elif damage == "index_version":
        write_json(index_path, {**index, "schema_version": 2})
    else:
        state = torch.load(state_path, weights_only=True)
        if damage == "state_version":
            state["schema_version"] = 2
        elif damage == "identity":
            state["identity"] = {}
        elif damage == "missing":
            del state["python_rng"]
        else:
            del state["optimizer"]["state"][0]
        torch.save(state, state_path)
        write_json(index_path, {**index, "state_sha256": file_sha256(state_path)})
    with pytest.raises(ValueError, match=message):
        checkpoint.read_checkpoint(destination, model, opt, identity)


def test_failed_staging_never_exposes_final(
    tmp_path: Path,
    trained: tuple[Any, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, opt, identity = trained
    destination = tmp_path / "checkpoint-16"

    def disk_failure(*args: Any) -> None:
        raise OSError("fixture disk failure")

    monkeypatch.setattr(checkpoint, "write_json", disk_failure)
    with pytest.raises(OSError, match="fixture disk failure"):
        checkpoint.save_checkpoint(destination, model, opt, 16, identity)
    assert not list(tmp_path.iterdir())
