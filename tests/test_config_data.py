from pathlib import Path

import pytest
import torch

from arborlm.config import load_config, validate_config
from arborlm.data import generate_dataset
from arborlm.io import file_sha256, read_json
from arborlm.model import PARAMETERS, DenseBaseline, active_parameters

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "e0_cpu_smoke.toml"


@pytest.mark.parametrize("mode", ["unknown", "wrong_type", "changed_setting", "missing"])
def test_config_rejects_deviations(mode: str) -> None:
    config = load_config(CONFIG)
    if mode == "unknown":
        config["model"]["unregistered"] = True
    elif mode == "wrong_type":
        config["training"]["threads"] = True
    elif mode == "changed_setting":
        config["model"]["width"] = 64
    else:
        del config["training"]["betas"]
    with pytest.raises(ValueError):
        validate_config(config)


def test_generated_data_bytes_and_disjoint_motifs(tmp_path: Path) -> None:
    data = generate_dataset()
    data.record(tmp_path)
    assert data.files() == generate_dataset().files()
    assert (len(data.train), len(data.validation)) == (256, 64)
    rows = data.train + data.validation
    assert len({tuple(row) for row in rows}) == len({tuple(row[:8]) for row in rows}) == 320
    assert all(len(row) == 33 and all(0 <= token < 16 for token in row) for row in rows)
    assert all(row == (row[:8] * 5)[:33] for row in rows)
    manifest = read_json(tmp_path / "dataset_manifest.json")
    for name, digest in manifest["checksums_sha256"].items():
        assert file_sha256(tmp_path / name) == digest
    data.record(tmp_path, verify_existing=True)
    (tmp_path / "validation.json").write_bytes(b"[]\n")
    with pytest.raises(ValueError, match="validation.json"):
        data.record(tmp_path, verify_existing=True)


@pytest.mark.parametrize("shape", [(3, 1), (1, 32), (2, 17)])
def test_model_shape_dtype_and_parameter_count(shape: tuple[int, int]) -> None:
    model = DenseBaseline()
    result = model(torch.zeros(shape, dtype=torch.int64))
    assert result.shape == (*shape, 16)
    assert result.dtype == torch.float32
    assert sum(p.numel() for p in model.parameters() if p.requires_grad) == PARAMETERS == 18688
    assert active_parameters(shape[1]) == 18688 - (32 - shape[1]) * 32


@pytest.mark.parametrize(
    "bad",
    [
        torch.zeros(32, dtype=torch.int64),
        torch.zeros((1, 2, 3), dtype=torch.int64),
        torch.zeros((0, 32), dtype=torch.int64),
        torch.zeros((1, 0), dtype=torch.int64),
        torch.zeros((1, 33), dtype=torch.int64),
        torch.zeros((1, 32), dtype=torch.float32),
        torch.full((1, 32), 16, dtype=torch.int64),
        torch.full((1, 32), -1, dtype=torch.int64),
    ],
)
def test_model_rejects_invalid_input(bad: torch.Tensor) -> None:
    with pytest.raises(ValueError):
        DenseBaseline()(bad)
