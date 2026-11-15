"""ADR-0016 gate 4: the single-set precondition detector and the identity null provider."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm import p7a_core as a_core  # noqa: E402
from arborlm import p7b_core as b_core  # noqa: E402
from arborlm.io import sha256  # noqa: E402
from supplements.p8s import null  # noqa: E402

S = (7, 300, 1000, 1500, 2222, 3000, 3500, 4095)


def _single(queries: int, order_shift: bool = True) -> torch.Tensor:
    base = torch.tensor(S, dtype=torch.int64)
    shift = torch.arange(queries)[:, None] if order_shift else 0
    return base[(torch.arange(8)[None, :] + shift) % 8]


def test_single_set_holds_and_slots_are_ascending() -> None:
    selected = _single(256)
    pre = null.detect_single_set(selected)
    assert pre.holds and pre.queries == 256 and pre.nonzero_slots == 8
    assert pre.slots == S and pre.reasons == ()


def test_q_other_than_32768_is_handled() -> None:
    assert null.detect_single_set(_single(64)).holds
    assert null.detect_single_set(_single(32768)).holds
    # the counts of a 32,768-query collapse do not satisfy the precondition for another Q
    counts = [0] * 4096
    for slot in S:
        counts[slot] = 32768
    assert null.precondition_from_counts(counts, 32768).holds
    assert not null.precondition_from_counts(counts, 100).holds
    assert not null.precondition_from_counts(counts, 32769).holds


def test_one_query_differing_fails() -> None:
    selected = _single(128)
    selected[5, 0] = 9  # slot 9 replaces one occurrence of S[...]
    pre = null.detect_single_set(selected)
    assert not pre.holds and pre.slots == ()


def test_nine_slots_fail() -> None:
    counts = [0] * 4096
    for slot in (*S, 11):
        counts[slot] = 100
    pre = null.precondition_from_counts(counts, 100)
    assert not pre.holds and any("expected 8" in r for r in pre.reasons)


def test_unequal_counts_fail() -> None:
    counts = [0] * 4096
    for i, slot in enumerate(S):
        counts[slot] = 100 if i else 99
    assert not null.precondition_from_counts(counts, 100).holds


def test_eight_slots_one_count_below_q_fails_on_rows() -> None:
    # eight slots appear, but one is missing from one query (replaced by a ninth slot)
    selected = _single(64)
    selected[0, selected[0].tolist().index(S[0])] = 11
    pre = null.detect_single_set(selected)
    assert not pre.holds


def test_wrong_total_fails() -> None:
    counts = [0] * 4096
    for slot in S[:7]:
        counts[slot] = 100  # seven slots at Q: total 700 != 800
    pre = null.precondition_from_counts(counts, 100)
    assert not pre.holds
    assert any("sum" in r or "expected 8" in r for r in pre.reasons)
    assert not null.precondition_from_counts([0] * 4096, 0).holds


def test_bad_shape_fails() -> None:
    assert not null.detect_single_set(torch.zeros(10, 7, dtype=torch.int64)).holds
    assert not null.detect_single_set(torch.zeros(10, dtype=torch.int64)).holds


def test_identity_null_passes_registered_checks_and_hash() -> None:
    selected = _single(128)
    counts = a_core.selection_counts(selected)
    pre = null.detect_single_set(selected)
    stream = null.identity_stream(pre.slots, pre.queries)
    null.check_null_stream(stream, counts)  # registered count and distinctness checks
    assert stream.shape == (128, 8) and stream.dtype == torch.int64
    assert all(row == sorted(S) for row in stream.tolist())  # ascending slot-ID order
    assert null.stream_sha256(stream) == sha256(a_core._pack(stream, "h"))
    # the registered check rejects a broken stream (the check is not vacuous)
    bad = stream.clone()
    bad[0, 1] = bad[0, 0]
    with pytest.raises(a_core.InvariantError):
        null.check_null_stream(bad, counts)
    shifted = stream.clone()
    shifted[0, 0] = 11
    with pytest.raises(a_core.InvariantError):
        null.check_null_stream(shifted, counts)


def test_provider_records_seeds_method_and_identical_hashes() -> None:
    selected = _single(128)
    seeds = (91331, 91332, 91333)
    streams, info = null.supplement_null_provider(selected, seeds, 3)
    assert len(streams) == 3 and all(torch.equal(streams[0], s) for s in streams)
    assert [d["replicate_seed"] for d in info] == list(seeds)
    assert [d["generator_seed"] for d in info] == [s * 1000 + 3 for s in seeds]  # recorded
    assert {d["method"] for d in info} == {"single-set identity null (ADR-0016 §3)"}
    assert all(d["precondition"] is True for d in info)
    assert len({d["stream_sha256"] for d in info}) == 1
    assert info[0]["stream_sha256"] == null.stream_sha256(streams[0])
    # the streams are independent tensors (no aliasing)
    streams[0][0, 0] = 0
    assert not torch.equal(streams[0], streams[1])


def test_provider_calls_registered_generator_when_precondition_false() -> None:
    from arborlm.p7a_trace import synthetic_trace

    selected, _ = synthetic_trace("flat", 5, queries=128, hot_slots=64)
    assert not null.detect_single_set(selected).holds
    seeds = (91341, 91342, 91343)
    mine, info = null.supplement_null_provider(selected, seeds, 7)
    reg, reg_info = b_core.null_streams(a_core.selection_counts(selected), seeds, 7)
    assert all(torch.equal(a, b) for a, b in zip(mine, reg, strict=True))
    assert [d["stream_sha256"] for d in info] == [d["stream_sha256"] for d in reg_info]
    assert all(d["precondition"] is False for d in info)
    assert {d["method"] for d in info} == {"exact count-preserving (ADR-0013 section 14 item 8)"}


def test_identity_stream_rejects_bad_sets() -> None:
    with pytest.raises(ValueError):
        null.identity_stream((1, 2, 3), 10)
    with pytest.raises(ValueError):
        null.identity_stream((8, 7, 6, 5, 4, 3, 2, 1), 10)  # not ascending
