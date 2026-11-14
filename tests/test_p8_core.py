"""P8 registry, constants, identity helpers and model construction (synthetic, no local data)."""

import os
from pathlib import Path

import pytest
import torch

from arborlm import p8_core as core
from arborlm.io import file_sha256
from arborlm.p5_config import Cell as P5Cell
from arborlm.p5_model import Model as P5Model
from arborlm.p5_model import state_digest
from arborlm.pilot_model import Memory


def test_sixty_unique_cells_in_index_order() -> None:
    registry = core.cells()
    assert len(registry) == 60
    assert [c.index for c in registry] == list(range(60))
    assert len({c.label for c in registry}) == 60
    assert registry[0].label == "b101-o301-s601-C01"
    assert registry[59].label == "b103-o303-s602-C10"
    for cell in registry:
        assert core.parse_label(cell.label) == cell
        pidx, sidx, cidx = (
            cell.backbone - 101,
            core.SEEDS.index(cell.seed),
            core.CASES.index(cell.case),
        )
        assert cell.index == 20 * pidx + 10 * sidx + cidx
    assert core.all_labels() == [c.label for c in registry]


def test_cell_validation_and_parent_label() -> None:
    with pytest.raises(ValueError):
        core.Cell(101, 301, 501, "C01")  # P5's seed
    with pytest.raises(ValueError):
        core.Cell(101, 302, 601, "C01")  # off-diagonal parent
    with pytest.raises(ValueError):
        core.Cell(101, 301, 601, "C11")
    with pytest.raises(ValueError):
        core.parse_label("b101-o301-s601-C99")
    cell = core.Cell(102, 302, 602, "C07")
    assert cell.parent_label == P5Cell(102, 302, 501, "flat").parent_label == "b102-o302-baseline"
    assert cell.variant == "learned_tree" and cell.objective == ("co",)
    assert cell.fields() == {"backbone": 102, "order": 302, "seed": 602, "case": "C07"}


def test_matrix_tables_match_the_adr() -> None:
    assert core.CASE_BASELINE == {
        "C04": "C01", "C05": "C03", "C06": "C01", "C07": "C03", "C08": "C01", "C09": "C03",
        "C10": "C03",
    }  # fmt: skip
    assert core.CASE_FLAT_COUNTERPART == {
        "C02": "C01", "C03": "C01", "C05": "C04", "C07": "C06", "C09": "C08",
    }  # fmt: skip
    assert core.CASE_OBJECTIVE["C10"] == ("co", "temp")
    assert all(core.CASE_OBJECTIVE[c] == () for c in ("C01", "C02", "C03"))
    assert [core.CASE_VARIANT[c] for c in core.CASES] == [
        "flat", "fixed_tree", "learned_tree", "flat", "learned_tree", "flat", "learned_tree",
        "flat", "learned_tree", "learned_tree",
    ]  # fmt: skip
    assert core.PARENTS == ((101, 301), (102, 302), (103, 303)) and core.SEEDS == (601, 602)
    assert (core.STEPS, core.BATCH, core.CONTEXT) == (512, 8, 64)
    assert (core.BETA, core.ALPHA, core.GROUP, core.WINDOW) == (0.25, 0.5, 8, 8)
    assert core.PANEL_A_RANKS == (3072, 3584) and core.PANEL_B_RANKS == (3584, 4096)
    assert core.CAL_RANKS == (2048, 2560) and core.CHECKPOINT_STEPS == (0, 256, 512)


def test_config_file_is_validated_and_agrees_with_constants() -> None:
    config = core.load_config()
    reg = config["regularizer"]
    assert (reg["beta"], reg["alpha"], reg["group"], reg["window"]) == (
        core.BETA, core.ALPHA, core.GROUP, core.WINDOW,
    )  # fmt: skip
    assert config["seeds"] == list(core.SEEDS)
    assert config["limits"]["train_stage_seconds"] == core.TRAIN_STAGE_CAP
    assert config["limits"]["rss_worker_bytes"] == core.RSS_WORKER
    assert config["measurement"]["panel_a_null_seeds"] == list(core.PANEL_A_NULL_SEEDS)
    changed = core.load_config()
    changed["regularizer"]["alpha"] = 0.6
    with pytest.raises(ValueError):
        core.validate_config(changed)


def test_hashes() -> None:
    hashes = core.source_hashes()
    assert "src/arborlm/p8_core.py" in hashes and "src/arborlm/p5_model.py" in hashes
    assert core.spec_sha256() == file_sha256(core.repo_root() / core.SPEC)
    assert len(core.config_sha256()) == 64
    identity = core.code_identity()
    assert set(identity) == {"source_sha256", "spec_sha256", "config_sha256"}


@pytest.mark.parametrize("case", core.CASES)
def test_build_model_matches_p5_structure_and_init(case: str) -> None:
    cell = core.Cell(101, 301, 601, case)
    backbone = core.synthetic_backbone(cell)
    model = core.build_model(cell, backbone)
    reference = P5Model(P5Cell(101, 301, 501, cell.variant), backbone)
    assert [(n, tuple(p.shape), p.requires_grad) for n, p in model.named_parameters()] == [
        (n, tuple(p.shape), p.requires_grad) for n, p in reference.named_parameters()
    ]
    assert [n for n, _ in model.named_buffers()] == [n for n, _ in reference.named_buffers()]
    memory = model.addition
    assert isinstance(memory, Memory)
    fresh = Memory(cell.variant, cell.seed)
    for (_, a), (_, b) in zip(memory.state_dict().items(), fresh.state_dict().items(), strict=True):
        assert torch.equal(a, b)
    assert not model.bypass and model.memory is model.addition
    # identical construction for the same seed is bit-identical (P5-legal seed 501 vs a P8 object)
    again = core.build_model(cell, backbone)
    assert state_digest(again) == state_digest(model)


def test_trainable_counts_match_registered() -> None:
    for case, expected in (("C01", 198145), ("C02", 198145), ("C03", 198401)):
        cell = core.Cell(101, 301, 601, case)
        model = core.build_model(cell, core.synthetic_backbone(cell))
        assert sum(p.numel() for p in model.parameters() if p.requires_grad) == expected
        assert sum(p.numel() for p in model.backbone.parameters()) == core.FROZEN_PARAMETERS


def test_synthetic_inputs_have_real_shape_and_schedule() -> None:
    cell = core.Cell(103, 303, 602, "C09")
    train, order, hashes = core.synthetic_training(cell)
    assert train.shape == (4096, 65) and sorted(order) == list(range(2048))
    assert hashes == {"synthetic": "true"}
    assert core.batch_offset(1) == 0 and core.batch_offset(257) == 0 and core.batch_offset(2) == 8
    assert core.batch_offset(512) == (511 * 8) % 2048
    with pytest.raises(ValueError):
        core.batch_offset(513)


@pytest.mark.skipif(
    "ARBOR_EXPERIMENTS_ROOT" not in os.environ, reason="local experiments root not provided"
)
def test_real_training_rows_identity_local_only() -> None:
    root = Path(os.environ["ARBOR_EXPERIMENTS_ROOT"])
    cell = core.Cell(101, 301, 601, "C01")
    train, order, hashes = core.load_training(cell, root)
    assert train.shape == (4096, 65) and sorted(order) == list(range(2048))
    assert len(hashes["train_bytes_sha256"]) == 64


def test_margin_constants_and_agreement_with_analysis_module() -> None:
    from fractions import Fraction

    from arborlm import p8_analysis as analysis

    assert (core.RETENTION_MIN, core.QUALITY_PAIRS_ABOVE_MAX, core.E_NULL_FLOOR) == (0.75, 1, 0.05)
    margins = core.load_config()["margins"]
    assert "gain_min" not in margins and not hasattr(core, "GAIN_MIN")
    assert margins["retention_min"] == core.RETENTION_MIN
    assert margins["quality_pairs_above_max"] == core.QUALITY_PAIRS_ABOVE_MAX
    assert margins["e_null_floor"] == core.E_NULL_FLOOR
    pairs = {
        "T_MATERIAL": core.MATERIAL_RATIO,
        "T_BAND_LOW": core.BAND_LOW,
        "T_BAND_HIGH": core.BAND_HIGH,
        "T_WORSE": core.WORSE_RATIO,
        "T_QUALITY": core.QUALITY_DELTA,
        "T_RETENTION": core.RETENTION_MIN,
        "T_NULL_FLOOR": core.E_NULL_FLOOR,
        "T_UTIL_RETAINED": core.UTIL_RETAINED,
        "T_UTIL_COLLAPSED": core.UTIL_COLLAPSED,
    }
    for name, value in pairs.items():
        theirs = getattr(analysis, name)
        theirs = float(theirs) if isinstance(theirs, Fraction) else theirs
        assert theirs == value, name
