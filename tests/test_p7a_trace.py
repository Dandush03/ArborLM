"""Synthetic tests for P7-A trace files, integrity checks and trace collection (ADR-0013 section 9).

The model used here is the tiny random fixture of ``p6_common.load_synthetic_cell``; no real
checkpoint, panel or trace is involved.
"""

import struct
from pathlib import Path

import pytest
import torch

from arborlm import p6_common as common
from arborlm import p7a_core as core
from arborlm import p7a_trace as tr
from arborlm.p5_model import evaluate

N = 8 * core.CONTEXT  # eight contexts in the fixture
PAIR = (101, 301, 501)


def good_flat(seed: int = 1) -> torch.Tensor:
    return tr.synthetic_trace("flat", seed, queries=N)[0]


def good_tree(seed: int = 2) -> tuple[torch.Tensor, torch.Tensor]:
    selected, branches = tr.synthetic_trace("fixed_tree", seed, queries=N)
    assert branches is not None
    return selected, branches


def test_synthetic_traces_are_concentrated_and_well_formed() -> None:
    selected = good_flat()
    info = core.check_trace(selected, None, "flat", queries=N)
    assert 100 < info["unique_selected_slots"] <= 400
    tree, branches = good_tree()
    core.check_trace(tree, branches, "fixed_tree", queries=N)
    assert bool(((tree // 256 == branches[:, :1]) | (tree // 256 == branches[:, 1:2])).all())


def test_binary_format_is_little_endian_and_round_trips(tmp_path: Path) -> None:
    selected = torch.arange(N * 8).reshape(N, 8) % core.SLOTS
    branches = torch.arange(N * 2).reshape(N, 2) % core.BRANCHES
    record = core.write_trace(tmp_path, "eval", selected, branches, N)
    raw = (tmp_path / "eval_selected.int16.bin").read_bytes()
    assert len(raw) == N * 8 * 2
    assert struct.unpack("<8h", raw[:16]) == tuple(range(8))
    assert raw[2:4] == b"\x01\x00"  # element 1 is 0x0001, little endian
    assert (tmp_path / "eval_branches.int8.bin").read_bytes()[:4] == bytes([0, 1, 2, 3])
    assert record["selected"]["dtype"] == "<i2" and record["branches"]["dtype"] == "|i1"
    assert record["selected"]["shape"] == [N, 8] and record["branches"]["shape"] == [N, 2]
    back_s, back_b = core.read_trace(tmp_path, "eval", record)
    assert torch.equal(back_s, selected) and back_b is not None and torch.equal(back_b, branches)
    flat_record = core.write_trace(tmp_path, "calib", selected, None, N)
    assert flat_record["branches"] is None
    assert core.read_trace(tmp_path, "calib", flat_record)[1] is None


def test_a_modified_trace_file_is_detected_by_its_hash(tmp_path: Path) -> None:
    selected = good_flat()
    record = core.write_trace(tmp_path, "eval", selected, None, N)
    path = tmp_path / "eval_selected.int16.bin"
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(bytes(data))
    with pytest.raises(core.TraceIntegrityError, match="hash"):
        core.read_trace(tmp_path, "eval", record)


def test_trace_with_the_wrong_shape_is_refused(tmp_path: Path) -> None:
    with pytest.raises(core.TraceIntegrityError):
        core.write_trace(tmp_path, "eval", torch.zeros(N + 1, 8, dtype=torch.int64), None, N)


def test_integrity_stops_fire_on_corrupted_traces() -> None:
    selected = good_flat()
    out_of_range = selected.clone()
    out_of_range[3, 2] = core.SLOTS
    with pytest.raises(core.TraceIntegrityError, match="range"):
        core.check_trace(out_of_range, None, "flat", queries=N)
    negative = selected.clone()
    negative[0, 0] = -1
    with pytest.raises(core.TraceIntegrityError, match="range"):
        core.check_trace(negative, None, "flat", queries=N)
    duplicate = selected.clone()
    duplicate[5, 1] = duplicate[5, 0]
    with pytest.raises(core.TraceIntegrityError, match="duplicate"):
        core.check_trace(duplicate, None, "flat", queries=N)
    tree, branches = good_tree()
    outside = tree.clone()
    for slot in range(core.SLOTS):  # a slot in a branch the query did not visit
        if slot // 256 not in branches[7].tolist() and slot not in outside[7].tolist():
            outside[7, 0] = slot
            break
    with pytest.raises(core.TraceIntegrityError, match="outside"):
        core.check_trace(outside, branches, "fixed_tree", queries=N)
    same_branch = branches.clone()
    same_branch[4, 1] = same_branch[4, 0]
    with pytest.raises(core.TraceIntegrityError):
        core.check_trace(tree, same_branch, "fixed_tree", queries=N)
    bad_branch = branches.clone()
    bad_branch[0, 0] = 16
    with pytest.raises(core.TraceIntegrityError, match="range"):
        core.check_trace(tree, bad_branch, "fixed_tree", queries=N)
    with pytest.raises(core.TraceIntegrityError, match="presence"):
        core.check_trace(tree, None, "fixed_tree", queries=N)
    with pytest.raises(core.TraceIntegrityError, match="presence"):
        core.check_trace(selected, branches, "flat", queries=N)
    with pytest.raises(core.TraceIntegrityError, match="shape"):
        core.check_trace(selected[:-1], None, "flat", queries=N)


def test_histogram_and_unique_count_must_match_the_p5_record() -> None:
    selected = good_flat()
    counts = core.selection_counts(selected)
    recorded = {
        "selected_slot_counts": counts,
        "unique_selected_slots": sum(1 for c in counts if c),
    }
    assert core.check_trace(selected, None, "flat", recorded=recorded, queries=N)[
        "histogram_matches_p5"
    ]
    moved = list(counts)
    donor = next(i for i, c in enumerate(moved) if c > 1)
    moved[donor] -= 1
    moved[(donor + 1) % core.SLOTS] += 1  # same total, different histogram
    with pytest.raises(core.TraceIntegrityError, match="histogram"):
        core.check_trace(
            selected,
            None,
            "flat",
            recorded={**recorded, "selected_slot_counts": moved},
            queries=N,
        )
    with pytest.raises(core.TraceIntegrityError, match="unique"):
        core.check_trace(
            selected, None, "flat", recorded={**recorded, "unique_selected_slots": 1}, queries=N
        )


@pytest.fixture(scope="module")
def fixture_source() -> common.CellSource:
    tr.configure_deterministic_cpu()
    return common.load_synthetic_cell(PAIR, rows=8)


@pytest.mark.parametrize("kind", core.KINDS)
def test_trace_checkpoint_replays_and_reproduces_the_recorded_histogram(
    kind: str, fixture_source: common.CellSource, tmp_path: Path
) -> None:
    model = fixture_source.models[kind]
    recorded = evaluate(model, fixture_source.panel, N)["retrieval"]
    record = tr.trace_checkpoint(
        fixture_source,
        kind,
        tmp_path,
        contexts=8,
        calibration=fixture_source.train[16:24],
        recorded_retrieval=recorded,
    )
    assert record["replay"]["bitwise_equal"] is True
    assert record["integrity"]["histogram_matches_p5"] is True
    assert record["label"] == core.cell_label(PAIR, kind) and record["queries"] == N
    selected, branches = core.read_trace(tmp_path, "eval", record["files"]["evaluation"])
    assert core.selection_counts(selected) == recorded["selected_slot_counts"]
    assert (branches is not None) == (kind != "flat")
    # registered order: row j * 64 + t is context j, position t, whatever the batching was
    for context in (0, 3, 7):
        _, lookup = model(fixture_source.panel[context : context + 1, :-1])
        assert lookup is not None
        assert torch.equal(
            selected[context * 64 : (context + 1) * 64], lookup.selected.to(torch.int64)
        )
        if branches is not None:
            assert lookup.branch_ids is not None
            assert torch.equal(
                branches[context * 64 : (context + 1) * 64], lookup.branch_ids.to(torch.int64)
            )


def test_nll_replay_mismatch_is_a_registered_stop(
    fixture_source: common.CellSource, tmp_path: Path
) -> None:
    original = fixture_source.recorded["flat"]["nll"]
    fixture_source.recorded["flat"]["nll"] = original + 1e-12
    try:
        with pytest.raises(tr.GateViolation) as caught:
            tr.trace_checkpoint(
                fixture_source,
                "flat",
                tmp_path,
                contexts=8,
                calibration=fixture_source.train[16:24],
                recorded_retrieval=None,
            )
    finally:
        fixture_source.recorded["flat"]["nll"] = original
    assert caught.value.gate == "nll_replay"
    assert not any(tmp_path.iterdir())  # nothing was written


def test_a_changed_checkpoint_is_a_registered_stop(
    fixture_source: common.CellSource, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = fixture_source.models["flat"]
    real = tr.collect_trace

    def tampering(m: object, data: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor | None]:
        out = real(m, data)
        with torch.no_grad():
            model.addition.gate.add_(1.0)  # type: ignore[union-attr]
        return out

    monkeypatch.setattr(tr, "collect_trace", tampering)
    snapshot = {k: v.clone() for k, v in model.state_dict().items()}
    try:
        with pytest.raises(tr.GateViolation) as caught:
            tr.trace_checkpoint(
                fixture_source,
                "flat",
                tmp_path,
                contexts=8,
                calibration=fixture_source.train[16:24],
                recorded_retrieval=None,
            )
    finally:
        model.load_state_dict(snapshot)
    assert caught.value.gate == "checkpoint_hash"


def test_a_corrupted_trace_stops_the_checkpoint(
    fixture_source: common.CellSource, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tr.collect_trace

    def corrupting(m: object, data: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor | None]:
        selected, branches = real(m, data)
        selected = selected.clone()
        selected[0, 1] = selected[0, 0]  # a duplicate within a query
        return selected, branches

    monkeypatch.setattr(tr, "collect_trace", corrupting)
    with pytest.raises(tr.GateViolation) as caught:
        tr.trace_checkpoint(
            fixture_source,
            "flat",
            tmp_path,
            contexts=8,
            calibration=fixture_source.train[16:24],
            recorded_retrieval=None,
        )
    assert caught.value.gate == "trace_integrity"


def test_registry_order_and_cell_indices() -> None:
    checkpoints = core.registered_checkpoints()
    assert len(checkpoints) == 81
    assert [k for _, k in checkpoints[:6]] == ["flat", "fixed_tree", "learned_tree"] * 2
    assert checkpoints[0][0] == (101, 301, 501) and checkpoints[3][0] == (101, 301, 502)
    assert checkpoints[-1][0] == (103, 303, 503)
    assert [core.cell_index(p, k) for p, k in checkpoints] == list(range(81))
    assert core.cell_label((101, 301, 501), "fixed_tree") == "b101-o301-fixed_tree-s501"
    assert core.parse_label("b103-o303-learned_tree-s503") == ((103, 303, 503), "learned_tree")
    with pytest.raises(ValueError):
        core.parse_label("b101-o301-dense-s501")
