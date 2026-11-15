"""P8 panel reconstruction: synthetic corpus tests; real-file tests skip without the local data."""

import copy
import os
import random
from pathlib import Path

import pytest

from arborlm import p7b_core as core
from arborlm import p8_core, p8_panel
from arborlm.io import read_json, sha256
from arborlm.pilot_data import CHUNK_BYTES, select

BLOCK = 4
DATA_DIR = Path(os.environ.get("ARBORLM_DATA_DIR", "data/wikitext2"))
AUDITOR = Path("docs/reviews/p8-preflight-2026-11-14/panel_confirmation.json")


def corpus(seed: int, rows: int, chunks_per_row: int = 3) -> list[str]:
    rng = random.Random(seed)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789 "
    return [
        "".join(rng.choice(alphabet) for _ in range(CHUNK_BYTES * chunks_per_row))
        for _ in range(rows)
    ]


def expected_blocks(train: list[str], validation: list[str]) -> dict[str, str]:
    _, full_train, _ = select(train, "train", 16)
    ranked, _, _ = select(validation, "validation", 8 * BLOCK, excluded=full_train)
    out = {}
    for n, name in enumerate(p8_panel.EARLIER_NAMES):
        out[name] = sha256(b"".join(c.payload for c in ranked[n * BLOCK : (n + 1) * BLOCK]))
    return out


def test_constants_agree_with_core() -> None:
    assert p8_panel.PANEL_RANKS["panel_A"] == p8_core.PANEL_A_RANKS
    assert p8_panel.PANEL_RANKS["panel_B"] == p8_core.PANEL_B_RANKS
    assert p8_panel.CAL_RANKS == p8_core.CAL_RANKS


def test_reconstruction_zero_overlap_and_ranks() -> None:
    train, validation = corpus(1, 40), corpus(2, 40)
    expected = expected_blocks(train, validation)
    result = p8_panel.reconstruct_from_rows(
        train, validation, train_ranked=16, block=BLOCK, expected_earlier=expected
    )
    rec = result.record
    assert rec["checks"]["all_six_earlier_reproduced"] and rec["checks"]["zero_exact_overlap"]
    for name in ("panel_A", "panel_B"):
        panel = rec["panels"][name]
        assert panel["rows"] == BLOCK and panel["bytes"] == BLOCK * CHUNK_BYTES
        assert not any(panel["overlap"].values())
        assert sha256(result.panel_bytes[name]) == panel["panel_sha256"]
    assert rec["panels"]["panel_A"]["ranks"] == [6 * BLOCK, 7 * BLOCK]
    assert rec["panels"]["panel_B"]["ranks"] == [7 * BLOCK, 8 * BLOCK]
    keys = set(rec["panels"]["panel_A"]["overlap"])
    assert (
        "other_new_panel" in keys
        and f"earlier_P7B_streamB_ranks_{5 * BLOCK}_{6 * BLOCK - 1}" in keys
    )
    assert f"calibration_stream_train_ranks_{4 * BLOCK}_{5 * BLOCK - 1}" in keys


def test_wrong_earlier_hash_stops() -> None:
    train, validation = corpus(1, 40), corpus(2, 40)
    expected = expected_blocks(train, validation)
    expected["P3"] = "0" * 64
    with pytest.raises(core.StopError, match="all_six_earlier_reproduced"):
        p8_panel.reconstruct_from_rows(
            train, validation, train_ranked=16, block=BLOCK, expected_earlier=expected
        )


def test_too_few_candidates_stops() -> None:
    train, validation = corpus(1, 40), corpus(2, 3)
    with pytest.raises(ValueError):
        p8_panel.reconstruct_from_rows(
            train, validation, train_ranked=16, block=BLOCK, expected_earlier={}
        )


def test_verify_panel_bytes_checks_hash_and_rows() -> None:
    raw = bytes(range(65)) + bytes(range(1, 66))
    row_hashes = [sha256(raw[:65]), sha256(raw[65:])]
    record = {
        "panels": {"panel_A": {"panel_sha256": sha256(raw), "rows": 2, "row_sha256": row_hashes}}
    }
    tensor = p8_panel.verify_panel_bytes(raw, "panel_A", record)
    assert tuple(tensor.shape) == (2, 65) and str(tensor.dtype) == "torch.int64"
    with pytest.raises(core.StopError):
        p8_panel.verify_panel_bytes(raw[:-1] + b"\x00", "panel_A", record)
    bad = copy.deepcopy(record)
    bad["panels"]["panel_A"]["row_sha256"] = row_hashes[::-1]
    with pytest.raises(core.StopError):
        p8_panel.verify_panel_bytes(raw, "panel_A", bad)


def test_compare_detects_a_difference() -> None:
    if not AUDITOR.is_file():
        pytest.skip("auditor confirmation not in the checkout")
    auditor = read_json(AUDITOR)
    record = {
        "panels": {n: copy.deepcopy(auditor["new_panels"][n]) for n in ("panel_A", "panel_B")},
        "earlier_panels": copy.deepcopy(auditor["earlier_panels"]),
        "inputs": {k: {"sha256": v["sha256"]} for k, v in auditor["inputs"].items()},
        "counts": copy.deepcopy(auditor["counts"]),
        "validation_eligible_candidates": auditor["validation_eligible_candidates"],
        "checks": {"zero_exact_overlap": True},
    }
    for n in ("panel_A", "panel_B"):
        for k in ("PANEL_unused",):
            record["panels"][n].pop(k, None)
    assert p8_panel.compare_with_auditor(record, auditor)["verdict"] == "AGREE"
    record["panels"]["panel_B"]["panel_sha256"] = "0" * 64
    result = p8_panel.compare_with_auditor(record, auditor)
    assert result["verdict"] == "DISAGREE"
    assert result["differences"][0]["field"] == "panel_B.panel_sha256"


@pytest.mark.skipif(not (DATA_DIR / "manifest.json").is_file(), reason="local corpus not present")
def test_real_panels_match_auditor() -> None:
    result = p8_panel.reconstruct_from_data_dir(DATA_DIR)
    auditor = read_json(AUDITOR)
    assert p8_panel.compare_with_auditor(result.record, auditor)["verdict"] == "AGREE"
    a, b = p8_panel.panel_tensors(DATA_DIR, result.record)
    assert tuple(a.shape) == (512, 65) == tuple(b.shape)
    calibration = p8_panel.calibration_tensor(DATA_DIR, result.record)
    assert tuple(calibration.shape) == (512, 65)
