"""Synthetic tests for P6-Q (ADR-0011 Part Q). No real checkpoint, panel or outcome is used."""

import itertools
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import torch
from torch import Tensor
from torch.nn import functional as F

from arborlm import p6_fidelity as fid
from arborlm import p6_fidelity_analysis as analysis
from arborlm import p6_fidelity_study as study
from arborlm import pilot_model
from arborlm.io import canonical_json, sha256
from arborlm.p2_config import CONTROL
from arborlm.p2_config import Cell as ParentCell
from arborlm.p2_model import FollowupModel
from arborlm.p4_model import extract
from arborlm.p5_config import FIXED, LEARNED, SEEDS, Cell
from arborlm.p5_model import Model, evaluate, state_digest
from arborlm.pilot_model import EPS, TEMP, TOP, Memory, stable_top, tree_candidates

ROWS = 16  # two registered 8x64 batches
TARGETS = ROWS * 64


def standin_reference(
    q: Tensor, keys: Tensor, router: Tensor, *, use_prior: bool
) -> tuple[Tensor, Tensor, Tensor]:
    """Test-only float64 stand-in with the interface of the auditor's reference."""
    q64, k64, r64 = q.double(), keys.double(), router.double()
    scores = q64 @ (k64 / k64.norm(dim=-1, keepdim=True).clamp_min(1e-8)).T / TEMP
    if use_prior:
        routes = q64 @ (r64 / r64.norm(dim=-1, keepdim=True).clamp_min(1e-8)).T / TEMP
        prior = routes.log_softmax(-1)
        scores = scores + prior[:, torch.arange(4096) // 256]
    ordered, order = torch.sort(scores, dim=1, descending=True, stable=True)
    return scores, order[:, :TOP].contiguous(), ordered[:, TOP - 1] - ordered[:, TOP]


def _references() -> list[Any]:
    found: list[Any] = [pytest.param(standin_reference, id="standin")]
    try:
        found.append(pytest.param(fid.load_reference(), id="auditor"))
    except ImportError:  # pragma: no cover - only while the auditor file is absent
        pass
    return found


@pytest.fixture(scope="module", params=[LEARNED, FIXED])
def tree_model(request: pytest.FixtureRequest) -> Model:
    backbone = extract(FollowupModel(ParentCell(101, 201, 301, CONTROL)))
    model = Model(Cell(101, 301, 501, request.param), backbone)
    generator = torch.Generator().manual_seed(11)
    memory = model.addition
    assert isinstance(memory, Memory)
    with torch.no_grad():
        memory.keys += torch.randn(4096, 16, generator=generator) * 0.06
        memory.values += torch.randn(4096, 32, generator=generator) * 0.05
    return model


@pytest.fixture(scope="module")
def panel() -> Tensor:
    return torch.randint(0, 256, (ROWS, 65), generator=torch.Generator().manual_seed(5))


def _fixture(n: int = 256, seed: int = 3) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    g = torch.Generator().manual_seed(seed)
    keys = torch.randn(4096, 16, generator=g) * 0.02
    router = torch.randn(16, 16, generator=g) * 0.02
    q = F.normalize(torch.randn(n, 16, generator=g), dim=-1, eps=EPS)
    routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
    return q, keys, router, routes


# ---- bitwise identity and non-mutation -------------------------------------------------------


def test_t2p_wrapper_is_bitwise_the_unmodified_model(tree_model: Model, panel: Tensor) -> None:
    unmodified = evaluate(tree_model, panel, TARGETS)
    wrapped = fid.run_rule(tree_model, panel, "T2P", expected_targets=TARGETS)
    assert wrapped.nll == unmodified["nll"]
    assert canonical_json(fid.concentration_report(wrapped.tracker)) == canonical_json(
        unmodified["retrieval"]
    )
    tree_model.eval()
    with torch.no_grad():
        direct_logits, direct_lookup = tree_model(panel[:8, :-1])
        recorder = fid.RuleRecorder("T2P", tree_model.cell.variant)
        memory = tree_model.addition
        assert isinstance(memory, Memory)
        with fid.substituted_rule(memory, "T2P", recorder):
            wrapped_logits, wrapped_lookup = tree_model(panel[:8, :-1])
    assert torch.equal(direct_logits, wrapped_logits)
    assert direct_lookup is not None and wrapped_lookup is not None
    for name in ("selected", "candidate_ids", "branch_ids", "route_scores"):
        assert torch.equal(getattr(direct_lookup, name), getattr(wrapped_lookup, name))


def test_substitution_changes_selection_but_not_state(tree_model: Model, panel: Tensor) -> None:
    memory = tree_model.addition
    assert isinstance(memory, Memory)
    before = state_digest(tree_model)
    python_state, torch_state = random.getstate(), torch.get_rng_state()
    grads = [p.requires_grad for p in tree_model.parameters()]
    passes = {r: fid.run_rule(tree_model, panel, r, expected_targets=TARGETS) for r in fid.RULES}
    assert state_digest(tree_model) == before
    assert random.getstate() == python_state
    assert torch.equal(torch.get_rng_state(), torch_state)
    assert [p.requires_grad for p in tree_model.parameters()] == grads
    assert "lookup" not in memory.__dict__
    assert passes["X16P"].branches.shape[1] == 16 and passes["T2P"].branches.shape[1] == 2
    assert not torch.equal(passes["X16P"].selected, passes["T2P"].selected)


def test_substitution_is_removed_after_an_error(tree_model: Model) -> None:
    memory = tree_model.addition
    assert isinstance(memory, Memory)
    original = pilot_model.stable_top
    recorder = fid.RuleRecorder("X16P", tree_model.cell.variant, spy_scores=True)
    with pytest.raises(RuntimeError, match="boom"), fid.substituted_rule(memory, "X16P", recorder):
        raise RuntimeError("boom")
    assert "lookup" not in memory.__dict__
    with pytest.raises(RuntimeError, match="boom"), fid._spy_candidate_scores([]):
        raise RuntimeError("boom")
    assert pilot_model.stable_top is original


# ---- structure of the rules --------------------------------------------------------------------


def test_t2p_is_x16p_restricted_to_visited_branches_and_lost_slots_rank_three_plus() -> None:
    q, keys, _, routes = _fixture()
    sink: list[tuple[Tensor, Tensor]] = []
    with fid._spy_candidate_scores(sink):
        v16, s16, _, b16 = tree_candidates(q, keys, routes, visit=16, use_prior=True)
    v2, s2, _, b2 = tree_candidates(q, keys, routes, visit=2, use_prior=True)
    scores, ids = sink[0]
    found = fid.restricted_selection_mismatches(scores, ids, b16, s2, v2, b2)
    assert found["selection_mismatch_rows"] == []
    assert found["visited_branch_mismatch_rows"] == []
    # Independent restriction: mask unvisited branches and take the stable top 8 by slot ID.
    mask = (ids // 256)[:, :, None] == b2[:, None, :]
    masked = scores.masked_fill(~mask.any(-1), float("-inf"))
    by_id = ids.argsort(-1)
    order = masked.gather(-1, by_id).argsort(dim=-1, descending=True, stable=True)[:, :TOP]
    assert torch.equal(ids.gather(-1, by_id).gather(-1, order), s2)
    assert fid.lost_rank_violations(s16, b16, s2) == []
    assert int((~fid.membership(s16, s2)).sum()) > 0  # something is lost on this fixture
    assert int(((~fid.membership(s16, s2)).sum(-1) > 0).sum()) > 0


def test_x16n_equals_the_flat_rule_without_near_ties() -> None:
    q, keys, router, routes = _fixture(256, seed=9)
    _, ids, gap = standin_reference(q, keys, router, use_prior=False)
    assert float(gap.min()) > 10 * fid.NEAR_TIE
    _, x16n, _, _ = tree_candidates(q, keys, routes, visit=16, use_prior=False)
    flat = stable_top((q @ F.normalize(keys, dim=-1, eps=EPS).T) / TEMP, TOP)[1]
    assert torch.equal(x16n.sort(-1).values, flat.sort(-1).values)
    assert torch.equal(x16n.sort(-1).values, ids.sort(-1).values)


def test_recall_by_width_is_monotone_and_ends_at_one() -> None:
    q, keys, _, routes = _fixture()
    x16 = tree_candidates(q, keys, routes, visit=16)[1]
    recalls = []
    for k in fid.WIDTHS:
        sel = tree_candidates(q, keys, routes, visit=k)[1]
        recalls.append(int(fid.overlap_counts(sel, x16).sum()))
    assert recalls == sorted(recalls)
    assert recalls[-1] == TOP * q.shape[0]


# ---- hand-built measurement cases --------------------------------------------------------------


def _ids(*rows: list[int]) -> Tensor:
    return torch.tensor(rows, dtype=torch.int64)


def test_recall_and_weighted_recall_hand_case() -> None:
    t2p = _ids([0, 1, 2, 3, 4, 5, 6, 7], [0, 1, 2, 3, 4, 5, 6, 7])
    ref = _ids([7, 6, 5, 4, 3, 2, 1, 0], [0, 1, 2, 3, 100, 101, 102, 103])
    counts = fid.overlap_counts(t2p, ref)
    assert counts.tolist() == [8, 4]
    summary = fid.recall_summary(counts)
    assert summary["mean"] == 12 / 16 and summary["fraction_one"] == 0.5
    assert summary["histogram"] == [0, 0, 0, 0, 1, 0, 0, 0, 1]
    weights = torch.tensor([[0.5, 0.25, 0.125, 0.125, 0, 0, 0, 0]] * 2)
    other = _ids([10, 12, 99, 98, 97, 96, 95, 94], [13, 12, 11, 10, 9, 8, 7, 6])
    reference = _ids([10, 11, 12, 13, 14, 15, 16, 17], [10, 11, 12, 13, 14, 15, 16, 17])
    expected = (0.5 + 0.125 + (0.5 + 0.25 + 0.125 + 0.125)) / 2
    assert fid.weighted_recall(weights, reference, other) == pytest.approx(expected, abs=1e-12)


def test_certificate_hand_case() -> None:
    routes = torch.zeros(3, 16)  # uniform prior: log(1/16) everywhere
    visited = torch.tensor([[0, 1]] * 3)
    threshold = 1 / TEMP + float(torch.tensor(1 / 16).log())
    values = torch.zeros(3, 8)
    values[:, 7] = torch.tensor([threshold + 0.01, threshold - 0.01, 0.0])
    certified = fid.certificate_mask(values, routes, visited)
    assert certified.tolist() == [True, False, False]
    summary = fid.certificate_summary(values, routes, visited, torch.tensor([8, 7, 8]))
    assert summary["certified_queries"] == 1 and summary["certified_with_recall_below_one"] == 0
    bad = fid.certificate_summary(values, routes, visited, torch.tensor([7, 7, 8]))
    assert bad["certified_with_recall_below_one"] == 1


def test_lost_candidates_hand_case() -> None:
    # Reference slots 0..7: slots 6, 7 lie in branch 5 (route rank 3) and branch 9 (rank 4).
    branches = torch.tensor([[0, 1, 5, 9, *range(2, 5), *range(6, 9), *range(10, 16)]])
    assert branches.shape == (1, 16) and sorted(branches[0].tolist()) == list(range(16))
    reference = _ids([0, 1, 2, 3, 4, 5, 5 * 256 + 3, 9 * 256 + 4])
    values = torch.tensor([[3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3]])
    t2p = _ids([0, 1, 2, 3, 4, 5, 6, 7])
    t2p_values = torch.tensor([[3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.2, 2.1]])
    trained = torch.zeros(4096, dtype=torch.bool)
    trained[5 * 256 + 3] = True
    out = fid.lost_candidates(
        reference, values, branches, t2p, t2p_values, trained, with_scores=True
    )
    assert out["lost_candidates"] == 2 and out["queries_with_loss"] == 1
    assert out["route_rank_histogram"][2] == 1 and out["route_rank_histogram"][3] == 1
    assert sum(out["route_rank_histogram"]) == 2
    assert out["lost_trained"] == 1 and out["lost_untrained"] == 1
    # margins: 2.4 - 2.1 and 2.3 - 2.1
    assert out["margin_to_t2p_boundary"]["min"] == pytest.approx(0.2)
    assert out["margin_to_t2p_boundary"]["max"] == pytest.approx(0.3)
    assert out["reference_score"]["count"] == 2
    recall = out["reference_recall_trained"]
    assert recall["reference_slots_trained"] == 1 and recall["recall_pooled"] == 0.0


def test_trained_recall_hand_case() -> None:
    reference = _ids([0, 1, 2, 3, 4, 5, 6, 7], [10, 11, 12, 13, 14, 15, 16, 17])
    kept = torch.tensor(
        [[True, True, False, False, True, True, True, True]] * 2,
    )
    trained = torch.zeros(4096, dtype=torch.bool)
    trained[[0, 1, 2, 3]] = True  # query 0: 4 trained, 2 kept; query 1: none trained
    out = fid.trained_recall(reference, kept, trained)
    assert out["reference_slots_trained"] == 4 and out["queries_with_trained_reference"] == 1
    assert out["recall_macro_over_queries_with_trained_reference"] == 0.5
    assert out["recall_pooled"] == 0.5


def test_coverage_detects_one_ulp_and_negative_zero() -> None:
    init_keys = torch.zeros(4096, 16)
    init_values = torch.ones(4096, 32)
    final_keys, final_values = init_keys.clone(), init_values.clone()
    final_keys[3, 0] = torch.nextafter(torch.tensor(0.0), torch.tensor(1.0))
    final_keys[4, 5] = -0.0
    final_values[9, 31] = 2.0
    final_values[3, 7] = 2.0  # slot 3: key and value both moved
    cov = fid.slot_coverage(final_keys, final_values, init_keys, init_values)
    assert cov["key_changed"].nonzero().flatten().tolist() == [3, 4]
    assert cov["value_changed"].nonzero().flatten().tolist() == [3, 9]
    assert float(cov["value_l2"][9]) == 1.0 and float(cov["key_l2"][4]) == 0.0
    summary = fid.coverage_summary(cov)
    assert (summary["key_changed"], summary["value_changed"], summary["either_changed"]) == (
        2,
        2,
        3,
    )
    # Explicit key-only (slot 4), value-only (slot 9) and both (slot 3) counts.
    assert (summary["key_only_changed"], summary["value_only_changed"]) == (1, 1)
    assert summary["both_changed"] == 1
    assert (
        summary["key_only_changed"] + summary["value_only_changed"] + summary["both_changed"]
        == summary["either_changed"]
    )


def test_prior_effects_and_token_split_hand_case() -> None:
    routes = torch.zeros(2, 16)
    routes[0, 3], routes[0, 7] = 2.0, 0.5
    routes[1, 3], routes[1, 7] = 1.0, 1.0
    t2p_branches = torch.tensor([[3, 7], [3, 7]])
    t2p = torch.tensor(
        [[3 * 256 + i for i in range(8)], [3 * 256 + i for i in range(7)] + [7 * 256]]
    )
    t2n = t2p.clone()
    t2n[1, 0] = 7 * 256 + 1
    out = fid.prior_effects(routes, t2p_branches, t2p, t2n)
    assert out["fraction_all_selected_in_top1_branch"] == 0.5
    assert out["fraction_t2n_t2p_sets_differ"] == 0.5
    assert out["t2n_t2p_overlap_mean"] == (8 + 7) / 16
    assert out["route_gap_top1_minus_top2"]["quantiles"]["0"] == 0.0
    assert out["route_gap_top1_minus_top2"]["max"] == 1.5
    split = fid.token_loss_split(
        torch.tensor([1.0, 2.0, 3.0]),
        torch.tensor([0.5, 2.0, 4.0]),
        torch.tensor([True, False, True]),
    )
    assert split["changed"]["mean_difference"] == pytest.approx(0.25)
    assert split["unchanged"]["mean_difference"] == 0.0 and split["all"]["tokens"] == 3
    assert split["changed"]["fraction_alternative_lower"] == 0.5


def test_write_array_roundtrip(tmp_path: Path) -> None:
    tensor = torch.arange(24, dtype=torch.float32).reshape(2, 3, 4)
    meta = fid.write_array(tmp_path, "sample", tensor)
    raw = (tmp_path / "sample.bin").read_bytes()
    assert meta["sha256"] == sha256(raw) and meta["shape"] == [2, 3, 4]
    assert torch.equal(
        torch.frombuffer(bytearray(raw), dtype=torch.float32).reshape(2, 3, 4), tensor
    )
    with pytest.raises(FileExistsError):
        fid.write_array(tmp_path, "sample", tensor)


# ---- engineering gates -------------------------------------------------------------------------


def _evaluate(
    model: Model,
    panel: Tensor,
    reference: Callable[..., tuple[Tensor, Tensor, Tensor]],
    recorded_nll: float | None = None,
    initial: bool = True,
) -> tuple[dict[str, Any], dict[str, Tensor]]:
    recorded = evaluate(model, panel, TARGETS)
    memory = model.addition
    assert isinstance(memory, Memory)
    initial_tensors = (
        (memory.keys.detach() + 0.01 * torch.ones(4096, 16), memory.values.detach().clone())
        if initial
        else None
    )
    return fid.evaluate_checkpoint(
        model,
        panel,
        recorded_nll=recorded["nll"] if recorded_nll is None else recorded_nll,
        recorded_retrieval=recorded["retrieval"],
        initial_tensors=initial_tensors,
        reference=reference,
        expected_targets=TARGETS,
    )


@pytest.mark.parametrize("reference", _references())
def test_evaluate_checkpoint_end_to_end(
    tree_model: Model, panel: Tensor, reference: Callable[..., Any]
) -> None:
    record, arrays = _evaluate(tree_model, panel, reference)
    canonical_json(record)  # JSON-safe and finite
    assert record["gates"]["i"]["passed"] and record["gates"]["state_and_rng_unchanged"]
    p, c = record["recall"]["P"], record["recall"]["C"]
    assert 0 <= p["mean"] <= 1 and 0 <= c["mean"] <= 1
    assert sum(p["histogram"]) == p["queries"] == TARGETS
    assert record["recall_by_width"]["2"]["mean"] == p["mean"]
    assert record["recall_by_width"]["16"]["mean"] == 1.0
    means = [record["recall_by_width"][str(k)]["mean"] for k in fid.WIDTHS]
    assert means == sorted(means)
    assert record["certificate"]["certified_with_recall_below_one"] == 0
    assert record["certificate"]["fraction"] <= p["fraction_one"]
    nll = record["nll"]
    assert record["delta_nll"]["restrict"] == nll["X16P"] - nll["T2P"]
    assert record["delta_nll"]["prior"] == nll["T2N"] - nll["T2P"]
    assert record["delta_nll"]["both"] == nll["X16N"] - nll["T2P"]
    total_lost = record["lost"]["P"]["lost_candidates"]
    assert total_lost == TOP * TARGETS - p["overlap_sum"]
    assert record["lost"]["P"]["lost_trained"] + record["lost"]["P"]["lost_untrained"] == total_lost
    assert sum(record["lost"]["P"]["route_rank_histogram"][:2]) == 0
    assert record["concentration"]["T2P"]["queries"] == TARGETS
    assert record["concentration"]["X16P"]["router"]["visited_branch_counts"] == [TARGETS] * 16
    changed = record["token_loss"]["X16P"]
    assert changed["changed"]["tokens"] + changed["unchanged"]["tokens"] == TARGETS
    assert arrays["selected_ids_T2P"].dtype == torch.int16
    assert set(arrays) >= {f"token_loss_{r}" for r in fid.RULES}
    assert record["gates"]["iv"]["disagreement_count"] >= 0


def test_gate_i_fails_on_a_perturbed_recorded_nll(tree_model: Model, panel: Tensor) -> None:
    recorded = evaluate(tree_model, panel, TARGETS)["nll"]
    wrong = float(torch.tensor(recorded, dtype=torch.float64).nextafter(torch.tensor(1e9)))
    with pytest.raises(fid.GateViolation) as caught:
        _evaluate(tree_model, panel, standin_reference, recorded_nll=wrong)
    assert caught.value.gate == "i"


def test_gate_i_fails_when_recorded_concentration_differs(tree_model: Model, panel: Tensor) -> None:
    recorded = evaluate(tree_model, panel, TARGETS)
    retrieval = dict(recorded["retrieval"])
    retrieval["unique_selected_slots"] += 1
    with pytest.raises(fid.GateViolation) as caught:
        fid.evaluate_checkpoint(
            tree_model,
            panel,
            recorded_nll=recorded["nll"],
            recorded_retrieval=retrieval,
            initial_tensors=None,
            reference=standin_reference,
            expected_targets=TARGETS,
        )
    assert caught.value.gate == "i"


def test_gate_ii_function_detects_a_corrupted_t2p_selection() -> None:
    q, keys, _, routes = _fixture(64)
    sink: list[tuple[Tensor, Tensor]] = []
    with fid._spy_candidate_scores(sink):
        _, _, _, b16 = tree_candidates(q, keys, routes, visit=16)
    v2, s2, _, b2 = tree_candidates(q, keys, routes, visit=2)
    bad = s2.clone()
    bad[5, 3] = (int(bad[5, 3]) + 1) % 4096
    found = fid.restricted_selection_mismatches(*sink[0], b16, bad, v2, b2)
    assert found["selection_mismatch_rows"] == [5]
    wrong_branches = b2.clone()
    wrong_branches[2, 0] = (int(wrong_branches[2, 0]) + 1) % 16
    found = fid.restricted_selection_mismatches(*sink[0], b16, s2, v2, wrong_branches)
    assert found["visited_branch_mismatch_rows"] == [2]


def test_gate_ii_and_iii_stop_the_checkpoint(
    tree_model: Model, panel: Tensor, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = fid.restricted_selection_mismatches

    def corrupted(*args: Any) -> dict[str, Any]:
        out = real(*args)
        out["selection_mismatch_rows"] = [0]
        return out  # type: ignore[no-any-return]

    monkeypatch.setattr(fid, "restricted_selection_mismatches", corrupted)
    with pytest.raises(fid.GateViolation) as caught:
        _evaluate(tree_model, panel, standin_reference)
    assert caught.value.gate == "ii"
    monkeypatch.undo()
    monkeypatch.setattr(
        fid, "lost_rank_violations", lambda *a: [{"query": 0, "position": 0, "slot": 1, "rank": 2}]
    )
    with pytest.raises(fid.GateViolation) as caught:
        _evaluate(tree_model, panel, standin_reference)
    assert caught.value.gate == "iii"


def test_lost_rank_violation_function_flags_rank_two_losses() -> None:
    branches = torch.arange(16).repeat(1, 1)
    x16p = _ids([0, 1, 2, 3, 4, 5, 6, 7 * 256])
    x16p = torch.cat([x16p, torch.tensor([[256]])], dim=1)  # slot 256 is in branch 1 (rank 2)
    t2p = _ids([0, 1, 2, 3, 4, 5, 6, 7])
    found = fid.lost_rank_violations(x16p, branches, t2p)
    assert [(d["slot"], d["rank"]) for d in found] == [(256, 2)]
    ok = fid.lost_rank_violations(_ids([0, 1, 2, 3, 4, 5, 6, 2 * 256]), branches, t2p)
    assert ok == []


def _perturbed(reference: Callable[..., Any], gap: float, set_change: bool) -> Callable[..., Any]:
    def wrapped(q: Tensor, keys: Tensor, router: Tensor, *, use_prior: bool) -> Any:
        scores, ids, boundary = reference(q, keys, router, use_prior=use_prior)
        ids, boundary = ids.clone(), boundary.clone()
        ids[0] = ids[0].roll(1) if not set_change else torch.cat([ids[0, :7], ids[0, 7:] + 1])
        if gap >= 0:
            boundary[0] = gap
        return scores, ids, boundary

    return wrapped


def test_gate_iv_stops_outside_near_ties_and_lists_near_ties(
    tree_model: Model, panel: Tensor
) -> None:
    with pytest.raises(fid.GateViolation) as caught:
        _evaluate(tree_model, panel, _perturbed(standin_reference, 0.25, True))
    assert caught.value.gate == "iv" and caught.value.details["outside_near_ties"] >= 1
    record, _ = _evaluate(tree_model, panel, _perturbed(standin_reference, 5e-6, True))
    listed = record["gates"]["iv"]["disagreements"]
    assert listed and all(d["near_tie"] and d["sets_differ"] for d in listed)
    # An order-only difference is listed but does not stop (the registered measures use sets).
    record, _ = _evaluate(tree_model, panel, _perturbed(standin_reference, 0.25, False))
    assert record["gates"]["iv"]["sets_differ_count"] == 0
    assert record["gates"]["iv"]["disagreement_count"] >= 1


def test_reference_disagreement_boundary_equality() -> None:
    frozen = _ids([0, 1, 2, 3, 4, 5, 6, 7])
    other = _ids([0, 1, 2, 3, 4, 5, 6, 8])
    at = fid.reference_disagreements("X16P", 10, frozen, other, torch.tensor([fid.NEAR_TIE]))
    above = fid.reference_disagreements(
        "X16P", 10, frozen, other, torch.tensor([fid.NEAR_TIE * 1.01])
    )
    assert at[0]["near_tie"] and not above[0]["near_tie"] and at[0]["query"] == 10


# ---- flags and consistency counts ---------------------------------------------------------------


def _record(b: int, o: int, s: int, variant: str, **values: float) -> dict[str, Any]:
    return {
        "outcome": "completed",
        "label": f"{variant}-{b}-{o}-{s}",
        "kind": "final",
        "step": 512,
        "cell": {"backbone": b, "order": o, "seed": s, "variant": variant},
        "recall": {
            "P": {"mean": values.get("p", 1.0)},
            "C": {"mean": values.get("c", 1.0)},
        },
        "delta_nll": {"restrict": values.get("restrict", 0.0), "prior": values.get("prior", 0.0)},
        "nll": {"T2P": 2.0 + values.get("shift", 0.0)},
        "gates": {"ignored": 1.0},
    }


def _cells() -> list[tuple[int, int, int]]:
    return analysis.expected_cells()


def _kind(variant: str, fn: Callable[[int], dict[str, float]]) -> dict[Any, dict[str, Any]]:
    return {cell: _record(*cell, variant, **fn(index)) for index, cell in enumerate(_cells())}


def test_registered_grid_has_nine_parents_and_27_cells() -> None:
    cells = _cells()
    assert len(cells) == 27 and len({(b, o) for b, o, _ in cells}) == 9
    assert [c[2] for c in cells[:3]] == list(SEEDS)


def test_fidelity_flag_boundary_equality_and_each_clause() -> None:
    exact = analysis.flags(_kind(FIXED, lambda i: {"p": 0.95, "c": 0.95}))["FID"]
    assert exact["passed"] and all(exact["clauses"].values()) and exact["mean"] == 0.95
    # 22 cells at 0.96 and 5 at 0.9, the five low cells spread over two parents (3 + 2).
    low = {0, 1, 2, 3, 4}
    shaped = analysis.flags(_kind(FIXED, lambda i: {"p": 0.9 if i in low else 0.96}))["FID"]
    assert shaped["cells_meeting"] == 22 and shaped["clauses"]["cells"]
    assert shaped["parents_meeting"] == 7 and not shaped["clauses"]["parents"]
    assert not shaped["clauses"]["mean"] and not shaped["passed"]
    assert shaped["mean"] == pytest.approx((22 * 0.96 + 5 * 0.9) / 27)
    # 21 cells meeting the level fails the cells clause even though every parent meets it.
    mixed = analysis.flags(
        _kind(FIXED, lambda i: {"p": 0.9 if i in {0, 4, 8, 12, 16, 20} else 1.0})
    )
    assert mixed["FID"]["cells_meeting"] == 21 and not mixed["FID"]["clauses"]["cells"]
    assert mixed["FID"]["parents_meeting"] == 9 and mixed["FID"]["clauses"]["parents"]
    cos = analysis.flags(_kind(FIXED, lambda i: {"c": 0.9499999}))["COS"]
    assert not cos["passed"] and cos["cells_meeting"] == 0


def test_loss_flag_boundary_and_sign_clauses() -> None:
    boundary = analysis.flags(_kind(FIXED, lambda i: {"restrict": -0.005}))["LOSS"]
    assert boundary["passed"] and boundary["mean"] == -0.005
    weak = analysis.flags(_kind(FIXED, lambda i: {"restrict": -0.0049}))["LOSS"]
    assert not weak["clauses"]["mean"] and weak["clauses"]["cells"] and not weak["passed"]
    # One parent (three cells) positive: mean, 24 cells and 8 parents pass the counts.
    split = analysis.flags(_kind(FIXED, lambda i: {"restrict": 0.5 if i < 3 else -0.5}))["LOSS"]
    assert split["cells_negative"] == 24 and split["parents_negative"] == 8
    assert split["clauses"]["cells"] and split["clauses"]["parents"] and split["clauses"]["mean"]
    zero = analysis.flags(_kind(FIXED, lambda i: {"restrict": 0.0}))["LOSS"]
    assert zero["cells_negative"] == 0 and not zero["passed"]


def test_prior_flag_sign_and_magnitude() -> None:
    plus = analysis.flags(_kind(FIXED, lambda i: {"prior": 0.005}))["PRIOR"]
    assert plus["passed"] and plus["sign"] == 1 and plus["cells_with_sign"] == 27
    minus = analysis.flags(_kind(FIXED, lambda i: {"prior": -0.25}))["PRIOR"]
    assert minus["passed"] and minus["sign"] == -1
    small = analysis.flags(_kind(FIXED, lambda i: {"prior": 0.00499}))["PRIOR"]
    assert not small["clauses"]["magnitude"] and small["clauses"]["cells"]
    # Mean is positive but only 21 cells share the sign (6 negative): cells clause fails.
    uneven = analysis.flags(
        _kind(FIXED, lambda i: {"prior": -0.001 if i in {0, 4, 8, 12, 16, 20} else 0.5})
    )["PRIOR"]
    assert uneven["sign"] == 1 and uneven["cells_with_sign"] == 21
    assert not uneven["clauses"]["cells"] and uneven["clauses"]["parents"]
    flat = analysis.flags(_kind(FIXED, lambda i: {"prior": 0.0}))["PRIOR"]
    assert flat["sign"] == 0 and not flat["passed"]


def test_paired_differences_counts_and_parent_means() -> None:
    fixed = _kind(FIXED, lambda i: {"p": 0.5})
    learned = _kind(
        LEARNED,
        lambda i: {"p": 0.75 if i < 9 else (0.25 if i < 12 else 0.5)},
    )
    out = analysis.paired_differences(fixed, learned)["recall.P.mean"]
    assert out["positive"] == 9 and out["negative"] == 3 and out["zero"] == 15
    assert out["mean_difference"] == (9 * 0.25 - 3 * 0.25) / 27
    assert out["parents_positive"] == 3 and out["parents_negative"] == 1
    assert out["parent_means"]["b101-o301"] == 0.25
    assert "gates.ignored" not in analysis.paired_differences(fixed, learned)


def _initial(cell: tuple[int, int, int], shift: float = 0.5) -> dict[str, Any]:
    rec = _record(*cell, FIXED, shift=shift)
    rec.update(kind="initial", step=0, label=analysis.initial_label(cell))
    return rec


def _finals(**values: float) -> list[dict[str, Any]]:
    out = []
    for variant in (FIXED, LEARNED):
        for cell in _cells():
            rec = _record(*cell, variant, **values)
            rec["label"] = analysis.final_label(variant, cell)
            out.append(rec)
    return out


def test_analysis_labels_equal_the_study_labels() -> None:
    for item in study.items():
        key = (item.cell.backbone, item.cell.order, item.cell.seed)
        expected = (
            analysis.initial_label(key)
            if item.kind == study.INITIAL
            else analysis.final_label(item.kind, key)
        )
        assert item.label == expected


def test_analyze_complete_records_and_labels_initials() -> None:
    result = analysis.analyze([*_finals(), *(_initial(c) for c in _cells())])
    assert result["records"] == {"final": 54, "initial": 27}
    assert result["expected"] == {"final": 54, "initial": 27}
    assert result["flags_status"] == "COMPUTED"
    assert result["initial_checkpoints"]["summary"]["nll.T2P"]["mean"] == 2.5
    assert set(result["flags"]) == {FIXED, LEARNED}
    assert result["finals_missing_or_not_completed"] == []
    assert result["step0_unexecuted_or_failed"] == []


def test_flags_come_from_the_54_finals_alone_when_step0_is_partial() -> None:
    """The case clarification 6 expects: all finals completed, only some step-0 checkpoints ran."""
    initials = [_initial(c) for c in _cells()[:6]]
    unexecuted = {
        analysis.initial_label(c): {"label": analysis.initial_label(c), "status": "unexecuted"}
        | {"reason": "budget"}
        for c in _cells()[6:]
    }
    result = analysis.analyze(
        _finals(p=0.97, restrict=-0.01, prior=0.01), unexecuted | {}, {"outcome": "partial"}
    )
    assert result["flags_status"] == "COMPUTED" and result["records"]["initial"] == 0
    assert result["flags"][FIXED]["FID"]["passed"] and result["flags"][LEARNED]["LOSS"]["passed"]
    full = analysis.analyze([*_finals(p=0.97, restrict=-0.01, prior=0.01), *initials], unexecuted)
    assert full["flags"] == result["flags"]  # step 0 never changes a registered flag
    assert full["records"] == {"final": 54, "initial": 6}
    assert full["initial_checkpoints"]["completed"] == 6 and full["initial_checkpoints"]["of"] == 27
    assert full["initial_checkpoints"]["summary"]["nll.T2P"]["cells"] == 6
    assert full["initial_checkpoints"]["summary"]["nll.T2P"]["mean"] == 2.5
    listed = full["step0_unexecuted_or_failed"]
    assert [row["label"] for row in listed] == [analysis.initial_label(c) for c in _cells()[6:]]
    assert all(
        row["suite_status"] == "unexecuted" and row["suite_reason"] == "budget" for row in listed
    )
    assert full["suite"] is None and result["suite"] == {"outcome": "partial"}
    # No step-0 record at all is also fine.
    assert (
        result["initial_checkpoints"]["cells"] == {}
        and result["initial_checkpoints"]["summary"] == {}
    )
    assert len(result["step0_unexecuted_or_failed"]) == 27


def test_flags_are_incomplete_not_an_exception_when_a_final_is_missing_or_failed() -> None:
    finals = _finals(p=0.97, restrict=-0.01, prior=0.01)
    dropped = finals.pop(5)  # a final with no record at all
    broken_index = next(
        i for i, r in enumerate(finals) if r["label"].endswith("learned_tree-s503-final")
    )
    broken = finals[broken_index]
    finals[broken_index] = {
        "label": broken["label"],
        "outcome": "gate_violation",
        "gate": "ii",
        "message": "synthetic",
    }
    killed = {dropped["label"]: {"label": dropped["label"], "status": "failed", "reason": "wall"}}
    result = analysis.analyze([*finals, _initial(_cells()[0])], killed)
    assert result["flags_status"] == "INCOMPLETE" and result["records"]["final"] == 52
    for kind in (FIXED, LEARNED):
        assert result["flags"][kind]["status"] == "INCOMPLETE"
    assert result["paired_learned_minus_fixed"]["status"] == "INCOMPLETE"
    listed = {row["label"]: row for row in result["finals_missing_or_not_completed"]}
    assert set(listed) == {dropped["label"], broken["label"]}
    assert listed[dropped["label"]]["suite_status"] == "failed"
    assert listed[broken["label"]]["record_outcome"] == "gate_violation"
    assert listed[broken["label"]]["gate"] == "ii"
    assert result["initial_checkpoints"]["completed"] == 1  # step 0 is still summarized
    canonical_json(result)


def test_analyze_still_rejects_duplicate_or_malformed_records() -> None:
    finals = _finals()
    with pytest.raises(ValueError, match="duplicate final"):
        analysis.analyze([*finals, finals[0]])
    bad = dict(finals[0], step=7)
    with pytest.raises(ValueError, match="unexpected or duplicate final"):
        analysis.analyze([bad, *finals[1:]])
    with pytest.raises(ValueError, match="unknown record kind"):
        analysis.analyze([dict(finals[0], kind="other")])


# ---- study driver -------------------------------------------------------------------------------


def test_study_order_and_labels() -> None:
    plan = study.items()
    assert len(plan) == 81 and len({i.label for i in plan}) == 81
    # All 54 finals (fixed then learned, parent/seed ascending) precede the 27 step-0 checkpoints.
    assert [i.record_kind for i in plan] == ["final"] * 54 + ["initial"] * 27
    assert [i.kind for i in plan[:4]] == [FIXED, LEARNED, FIXED, LEARNED]
    assert [i.step for i in plan if i.kind == study.INITIAL] == [0] * 27
    first = plan[0].cell
    assert (first.backbone, first.order, first.seed) == (101, 301, 501)
    for part in (plan[:54], plan[54:]):
        assert all(a.cell.index <= b.cell.index for a, b in itertools.pairwise(part))


def test_run_refuses_to_overwrite_results(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "existing.json").write_text("{}")

    class Args:
        output_root = tmp_path / "out"
        results_root = results
        parent_suite = tmp_path / "suite"
        data_dir = tmp_path / "data"
        p5_results = tmp_path / "p5"
        p4_suite = None

    with pytest.raises(SystemExit, match="refusing to overwrite"):
        study.run_study(Args())  # type: ignore[arg-type]
    assert not (tmp_path / "out").exists()


class _Args:
    def __init__(self, tmp_path: Path) -> None:
        self.output_root = tmp_path / "out"
        self.results_root = tmp_path / "results"
        self.parent_suite = tmp_path / "suite"
        self.data_dir = tmp_path / "data"
        self.p5_results = tmp_path / "p5"
        self.p4_suite = None
        self.command = "run"


def _patch_cheap_provenance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(study, "quality_directory", lambda suite: tmp_path / "quality")
    monkeypatch.setattr(study, "verify_hashes", lambda quality, p5: {"x": "y"})
    monkeypatch.setattr(
        study, "_preflight", lambda: {"synthetic": True, "frozen_equals_reference": True}
    )
    monkeypatch.setattr(
        study,
        "record_source",
        lambda run, cwd, spec: {
            "git_root": str(root),
            "spec_sha256": "s" * 64,
            "code_commit": "c" * 40,
            "dirty": True,
            "archive": {"sha256": "a" * 64},
            "lock_sha256": "l" * 64,
        },
    )
    monkeypatch.setattr(study, "record_environment", lambda run, family: {"synthetic": True})


def _fake_supervise(
    seconds: float, fail_at: int | None = None, record: list[float] | None = None
) -> Callable[..., Any]:
    """A supervisor stand-in: every cell takes ``seconds``; call number ``fail_at`` fails."""
    from arborlm.io import write_json
    from arborlm.records import allocate_run

    calls = [0]

    def fake(root: Path, operation: str, arguments: list[str], **kw: Any) -> Any:
        calls[0] += 1
        if record is not None:
            record.append(kw["process_seconds"])
        child = allocate_run(root, prefix="P6QCELL")
        failed = fail_at == calls[0]
        write_json(
            child / "terminal.json",
            {
                "status": "failed" if failed else "completed",
                "reason": "process wall-time limit exceeded" if failed else None,
                "process_wall_seconds": seconds,
                "peak_process_tree_rss_bytes": 1,
            },
        )
        if not failed:
            write_json(child / "result.json", {"outcome": "completed"})
        return child, not failed

    return fake


def _events(run: Path) -> list[dict[str, Any]]:
    import json

    return [json.loads(line) for line in (run / "metrics.jsonl").read_text().splitlines() if line]


def test_suite_never_starts_an_item_below_the_per_checkpoint_cap_even_a_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.io import read_json

    _patch_cheap_provenance(monkeypatch, tmp_path)
    limits: list[float] = []
    monkeypatch.setattr(study, "supervise", _fake_supervise(59.0, record=limits))
    args = _Args(tmp_path)
    assert study.run_study(args) == 1  # type: ignore[arg-type]
    # 30 cells of 59 s use 1,770 s; the 31st would start with 30 s left, less than the 60 s cap.
    assert limits == [60] * 30
    run = next(args.output_root.glob("P6Q-*"))
    result = read_json(run / "result.json")
    assert result["outcome"] == study.BUDGET_DURING_FINALS
    assert "below the 60 s per-checkpoint cap" in result["reason"] and "-final" in result["reason"]
    assert result["active_worker_seconds"] == pytest.approx(30 * 59)
    skipped = [c for c in result["cells"] if c["status"] == "unexecuted"]
    assert len(skipped) == 81 - 30
    assert (
        skipped[0]["reason"] == "budget"
        and skipped[1]["reason"] == "stage stopped earlier (budget)"
    )
    assert result["finals_completed"] == 30 and result["step0_completed"] == 0
    assert len(list((args.results_root / "cells").iterdir())) == 30
    (event,) = [e for e in _events(run) if e["event"] == "budget_exhausted_before_start"]
    assert event["kind"] == "final" and event["remaining_seconds"] == pytest.approx(30.0)
    assert event["terminal_status"] == study.BUDGET_DURING_FINALS
    assert not (run / "checkpoint_hashes_after.json").exists()
    manifest = read_json(run / "manifest.json")
    assert manifest["status"] == "failed" and manifest["outcome"] == study.BUDGET_DURING_FINALS
    assert manifest["dirty"] is True and manifest["code_commit"] == "c" * 40
    assert "src/arborlm/p6_fidelity.py" in manifest["p6_source_sha256"]
    assert manifest["limits"]["checkpoint_seconds"] == 60
    assert manifest["experiment_family"] == study.FAMILY
    assert manifest["known_limits"] == list(fid.KNOWN_LIMITS)
    assert (args.results_root / "suite" / "manifest.json").exists()
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        study.run_study(_Args(tmp_path))  # type: ignore[arg-type]


def test_suite_with_all_finals_done_and_budget_ending_in_step0_is_distinct_and_successful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.io import read_json

    _patch_cheap_provenance(monkeypatch, tmp_path)
    limits: list[float] = []
    monkeypatch.setattr(study, "supervise", _fake_supervise(30.0, record=limits))
    args = _Args(tmp_path)
    assert study.run_study(args) == 0  # type: ignore[arg-type]
    # 54 finals use 1,620 s; step-0 items start at 1,620 ... 1,740 s (remaining 180 ... 60 s),
    # the item that would start with 30 s left is not started.
    assert len(limits) == 54 + 5 and set(limits) == {60}
    run = next(args.output_root.glob("P6Q-*"))
    result = read_json(run / "result.json")
    assert result["outcome"] == study.PARTIAL_STEP0 == "completed_finals_step0_partial"
    assert result["finals_completed"] == 54 and result["step0_completed"] == 5
    assert result["step0_unexecuted"] == 22 and result["checkpoints_completed"] == 59
    assert all(
        c["reason"] in ("budget", "stage stopped earlier (budget)")
        for c in result["cells"]
        if c["status"] == "unexecuted"
    )
    terminal = read_json(run / "terminal.json")
    assert terminal["status"] == "completed_finals_step0_partial" and terminal["reason"].startswith(
        "budget"
    )
    assert read_json(run / "manifest.json")["status"] == "completed_finals_step0_partial"
    assert (run / "checkpoint_hashes_after.json").exists()
    (event,) = [e for e in _events(run) if e["event"] == "budget_exhausted_before_start"]
    assert event["kind"] == "initial" and event["terminal_status"] == study.PARTIAL_STEP0
    assert read_json(args.results_root / "suite" / "result.json")["outcome"] == study.PARTIAL_STEP0


def test_a_failed_cell_still_halts_the_stage_and_marks_the_rest_unexecuted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.io import read_json

    _patch_cheap_provenance(monkeypatch, tmp_path)
    monkeypatch.setattr(study, "supervise", _fake_supervise(10.0, fail_at=3))
    args = _Args(tmp_path)
    assert study.run_study(args) == 1  # type: ignore[arg-type]
    run = next(args.output_root.glob("P6Q-*"))
    result = read_json(run / "result.json")
    assert result["outcome"] == "stopped" and "process wall-time" in result["reason"]
    assert [c["status"] for c in result["cells"][:3]] == ["completed", "completed", "failed"]
    assert all(
        c["status"] == "unexecuted" and c["reason"] == "stage stopped earlier (failure)"
        for c in result["cells"][3:]
    )
    # The killed cell's folder holds a terminal record but no result.json.
    killed = args.results_root / "cells" / result["cells"][2]["label"]
    assert (killed / "terminal.json").is_file() and not (killed / "result.json").exists()
    assert not [e for e in _events(run) if e["event"] == "budget_exhausted_before_start"]


def test_a_false_preflight_stops_before_any_cell_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.io import read_json

    _patch_cheap_provenance(monkeypatch, tmp_path)
    monkeypatch.setattr(
        study, "_preflight", lambda: {"synthetic_queries": 64, "frozen_equals_reference": False}
    )
    started: list[int] = []
    monkeypatch.setattr(study, "supervise", lambda *a, **k: started.append(1))
    args = _Args(tmp_path)
    with pytest.raises(ValueError, match="disagree in the preflight"):
        study.run_study(args)  # type: ignore[arg-type]
    assert started == []
    run = next(args.output_root.glob("P6Q-*"))
    assert read_json(run / "result.json")["outcome"] == "stopped"
    assert read_json(run / "terminal.json")["status"] == "failed"


def test_suite_completes_when_every_worker_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.io import read_json, write_json
    from arborlm.records import allocate_run

    _patch_cheap_provenance(monkeypatch, tmp_path)

    def fake_supervise(root: Path, operation: str, arguments: list[str], **kw: Any) -> Any:
        child = allocate_run(root, prefix="P6QCELL")
        write_json(
            child / "terminal.json",
            {
                "status": "completed",
                "reason": None,
                "process_wall_seconds": 10.0,
                "peak_process_tree_rss_bytes": 1,
            },
        )
        write_json(child / "result.json", {"outcome": "completed"})
        return child, True

    monkeypatch.setattr(study, "supervise", fake_supervise)
    args = _Args(tmp_path)
    assert study.run_study(args) == 0  # type: ignore[arg-type]
    run = next(args.output_root.glob("P6Q-*"))
    assert read_json(run / "result.json")["checkpoints_completed"] == 81
    assert (run / "checkpoint_hashes_after.json").exists()


def test_analyze_command_reads_cells_and_refuses_to_overwrite(tmp_path: Path) -> None:
    from arborlm.io import read_json, write_json

    results = tmp_path / "results"
    for index, cell in enumerate(_cells()):
        for variant in (FIXED, LEARNED):
            record = _record(*cell, variant, p=0.97, restrict=-0.01, prior=0.01)
            folder = results / "cells" / f"{variant}-{index}"
            folder.mkdir(parents=True)
            write_json(folder / "result.json", record)
        initial = _record(*cell, FIXED)
        initial.update(kind="initial", step=0)
        folder = results / "cells" / f"initial-{index}"
        folder.mkdir(parents=True)
        write_json(folder / "result.json", initial)

    class Args:
        results_root = results

    assert study.analyze_study(Args()) == 0  # type: ignore[arg-type]
    out = read_json(results / "analysis.json")
    assert out["flags"][FIXED]["FID"]["passed"] and out["flags"][LEARNED]["LOSS"]["passed"]
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        study.analyze_study(Args())  # type: ignore[arg-type]


def test_analyze_command_lists_a_cap_killed_cell_folder_instead_of_crashing(
    tmp_path: Path,
) -> None:
    """54 finals, a few step-0 records, one final killed by the watchdog (no result.json)."""
    from arborlm.io import read_json, write_json

    results = tmp_path / "results"
    killed_label = analysis.final_label(LEARNED, _cells()[-1])
    for kind in (FIXED, LEARNED):
        for cell in _cells():
            label = analysis.final_label(kind, cell)
            folder = results / "cells" / label
            folder.mkdir(parents=True)
            if label == killed_label:  # the watchdog killed this worker before it wrote a result
                write_json(
                    folder / "terminal.json",
                    {"status": "failed", "reason": "process wall-time limit exceeded"},
                )
                write_json(folder / "manifest.json", {"status": "running"})
                continue
            write_json(
                folder / "result.json",
                {**_record(*cell, kind, p=0.97, restrict=-0.01, prior=0.01), "label": label},
            )
    for cell in _cells()[:4]:
        folder = results / "cells" / analysis.initial_label(cell)
        folder.mkdir(parents=True)
        write_json(folder / "result.json", _initial(cell))
    cells_log = [
        {"label": killed_label, "status": "failed", "reason": "process wall-time limit exceeded"},
        *(
            {"label": analysis.initial_label(c), "status": "unexecuted", "reason": "budget"}
            for c in _cells()[4:]
        ),
    ]
    (results / "suite").mkdir()
    write_json(
        results / "suite" / "result.json",
        {"outcome": "stopped", "reason": "killed", "cells": cells_log},
    )

    class Args:
        results_root = results

    assert study.analyze_study(Args()) == 0  # type: ignore[arg-type]
    out = read_json(results / "analysis.json")
    assert out["flags_status"] == "INCOMPLETE" and out["flags"][LEARNED]["status"] == "INCOMPLETE"
    (missing,) = out["finals_missing_or_not_completed"]
    assert missing["label"] == killed_label and missing["record_outcome"] == "no_result_json"
    assert missing["suite_status"] == "failed"
    assert out["suite"]["outcome"] == "stopped" and out["records"] == {"final": 53, "initial": 4}
    assert len(out["step0_unexecuted_or_failed"]) == 23
    assert out["initial_checkpoints"]["completed"] == 4


def test_analyze_command_with_partial_step0_computes_every_flag_from_the_finals(
    tmp_path: Path,
) -> None:
    from arborlm.io import read_json, write_json

    results = tmp_path / "results"
    for kind in (FIXED, LEARNED):
        for cell in _cells():
            label = analysis.final_label(kind, cell)
            (results / "cells" / label).mkdir(parents=True)
            record = _record(*cell, kind, p=0.97, restrict=-0.01, prior=0.01)
            write_json(results / "cells" / label / "result.json", {**record, "label": label})

    class Args:
        results_root = results

    assert study.analyze_study(Args()) == 0  # type: ignore[arg-type]
    out = read_json(results / "analysis.json")
    assert out["flags_status"] == "COMPUTED" and out["records"] == {"final": 54, "initial": 0}
    assert out["flags"][FIXED]["FID"]["passed"] and len(out["step0_unexecuted_or_failed"]) == 27


# ---- width curve from the captured X16P scores (audit M1) ----------------------------------------


def test_width_curve_from_captured_scores_equals_tree_candidates_for_every_k() -> None:
    q, keys, _, routes = _fixture(256, seed=21)
    sink: list[tuple[Tensor, Tensor]] = []
    with fid._spy_candidate_scores(sink):
        _, x16, _, b16 = tree_candidates(q, keys, routes, visit=16, use_prior=True)
    scores, ids = sink[0]
    assert scores.shape == (256, 4096)
    for k in fid.WIDTHS:
        columns = 256 * k
        _, chosen = stable_top(scores[:, :columns], TOP, ids[:, :columns])
        _, direct, _, _ = tree_candidates(q, keys, routes, visit=k, use_prior=True)
        assert torch.equal(chosen, direct), k
        # The first 256 * k columns are the k best-routed branches, in route-rank order.
        assert torch.equal(ids[:, :columns] // 256, b16[:, :k].repeat_interleave(256, dim=-1))
    assert torch.equal(stable_top(scores, TOP, ids)[1], x16)


def test_width_curve_costs_one_cross_check_not_five_tree_candidate_passes(
    tree_model: Model, panel: Tensor, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    real = fid.tree_candidates

    def counting(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs["visit"])
        return real(*args, **kwargs)

    monkeypatch.setattr(fid, "tree_candidates", counting)
    record, _ = _evaluate(tree_model, panel, standin_reference)
    batches = ROWS // 8
    # Four rule passes use one call per batch; the width curve adds one call per k (batch 1).
    assert len(calls) == 4 * batches + len(fid.WIDTHS)
    assert calls.count(6) == 1 and calls.count(12) == 1  # only the cross-check ever visits 6, 12
    check = record["width_cross_check"]
    assert check["passed"] and check["widths"] == list(fid.WIDTHS) and check["batch_offset"] == 0
    assert "first 256*k columns" in record["width_curve_method"]
    assert "width_curve" not in record["phase_seconds"]


def test_width_cross_check_mismatch_is_an_engineering_stop(
    tree_model: Model, panel: Tensor, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = fid.tree_candidates

    def corrupted(*args: Any, **kwargs: Any) -> Any:
        values, selected, candidates, branches = real(*args, **kwargs)
        if kwargs["visit"] == 6:  # only the cross-check visits six branches
            selected = selected.roll(1, dims=-1)
        return values, selected, candidates, branches

    monkeypatch.setattr(fid, "tree_candidates", corrupted)
    with pytest.raises(fid.GateViolation) as caught:
        _evaluate(tree_model, panel, standin_reference)
    assert caught.value.gate == "width" and caught.value.details == {"k": 6}


# ---- concentration reports for the non-registered rules (audit MINOR 7) --------------------------


def test_concentration_keeps_t2p_work_fields_and_drops_them_for_other_rules(
    tree_model: Model, panel: Tensor
) -> None:
    record, _ = _evaluate(tree_model, panel, standin_reference)
    t2p = record["concentration"]["T2P"]
    assert t2p["full_key_dots_per_query"] == 512 and t2p["logical_key_elements_per_query"] == 8192
    for rule in ("T2N", "X16P", "X16N"):
        report = record["concentration"][rule]
        assert not set(fid.ANALYTICAL_WORK_FIELDS) & set(report), rule
        assert report["analytical_work_fields"].startswith("omitted")
        assert report["queries"] == TARGETS and report["unique_selected_slots"] > 0
        assert report["router"]["visited_branch_counts"] is not None
        assert "effective_selected_slots" in report and "hottest_selected_slot_fraction" in report
    assert "analytical_work_fields" not in t2p
    assert record["known_limits"] == list(fid.KNOWN_LIMITS)


# ---- loader-smoke ----------------------------------------------------------------------------


class _Parent:
    def check_unchanged(self) -> None:
        return None


def _smoke_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, model: Model, panel: Tensor, nll: float | None
) -> None:
    """Replace only the real-data loading by a synthetic ``Prepared``; everything else is real."""

    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("loader-smoke reached a forbidden code path")

    for module, names in (
        (fid, ("evaluate_checkpoint", "run_rule", "substituted_rule", "load_reference")),
        (fid, ("restricted_selection_mismatches", "lost_candidates", "slot_coverage")),
        (fid, ("recall_summary", "certificate_summary", "write_array", "reference_disagreements")),
        (study, ("_measure", "run_study", "analyze_study", "supervise", "verify_hashes")),
        (study, ("_preflight", "_worker", "_export")),
        (analysis, ("analyze", "flags", "paired_differences", "initial_tables")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, boom)
    recorded = evaluate(model, panel, TARGETS)
    if nll is not None:
        recorded["nll"] = nll
    ready = study.Prepared(
        model=model,
        panel=panel,
        evidence=study.Evidence(tmp_path, {}, {}, {}),
        recorded=recorded,
        initial_tensors=None,
        shared_initial=None,
        hash_paths={},
        hashes_before={},
        parent=_Parent(),
    )
    calls: list[tuple[Any, ...]] = []

    def fake_prepare(*args: Any) -> study.Prepared:
        calls.append(args)
        assert Path(args[0]).is_dir()  # the scratch run folder exists while loading
        return ready

    monkeypatch.setattr(study, "prepare", fake_prepare)
    monkeypatch.setattr(study, "quality_directory", lambda suite: tmp_path / "quality")
    monkeypatch.setattr(study, "VAL_TARGETS", TARGETS)
    monkeypatch.setattr(study, "runtime_supported", lambda: None)
    monkeypatch.setattr(study, "SMOKE_CALLS", calls, raising=False)


def _smoke_argv(tmp_path: Path, step: str = "final") -> list[str]:
    return [
        "p6_fidelity_study",
        "loader-smoke",
        "--parent-suite",
        str(tmp_path / "suite"),
        "--cell",
        "b101-o301-fixed_tree-s501",
        "--step",
        step,
    ]


def test_loader_smoke_loads_and_replays_but_computes_no_p6_quantity(
    tree_model: Model,
    panel: Tensor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import json
    import sys

    work = tmp_path / "work"
    work.mkdir()
    _smoke_setup(monkeypatch, work, tree_model, panel, None)
    monkeypatch.chdir(work)  # a stray experiments/ or results/ would be created here
    before = sorted(p.name for p in work.iterdir())
    monkeypatch.setattr(sys, "argv", _smoke_argv(tmp_path))
    assert study.main() == 0
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert report["command"] == "loader-smoke" and report["study"] == "P6-Q"
    assert report["label"] == "b101-o301-fixed_tree-s501-final" and report["step"] == 512
    assert report["replay_bitwise_equal"] is True and report["checkpoint_files_unchanged"] is True
    assert report["p6_quantities_computed"] is False
    assert report["wall_seconds"] > 0 and report["peak_rss_bytes_ru_maxrss"] > 0
    assert report["prepare_seconds"] >= 0 and report["replay_seconds"] > 0
    assert sorted(p.name for p in work.iterdir()) == before  # nothing written anywhere near here
    assert not (work / "experiments").exists() and not (work / "results").exists()
    (call,) = study.SMOKE_CALLS  # type: ignore[attr-defined]
    assert call[5].label == "b101-o301-fixed_tree-s501-final"


def test_loader_smoke_selects_the_step_zero_item_and_reports_a_replay_mismatch(
    tree_model: Model,
    panel: Tensor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import json
    import sys

    wrong = float(
        torch.tensor(evaluate(tree_model, panel, TARGETS)["nll"]).nextafter(torch.tensor(9.0))
    )
    _smoke_setup(monkeypatch, tmp_path, tree_model, panel, wrong)
    monkeypatch.setattr(sys, "argv", _smoke_argv(tmp_path, "initial"))
    assert study.main() == 1
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert report["label"] == "b101-o301-shared_initial-s501" and report["step"] == 0
    assert report["replay_bitwise_equal"] is False


def test_loader_smoke_item_resolution_and_argument_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    assert study.resolve_item("b101-o301-learned_tree-s503", "final").step == 512
    assert study.resolve_item("b101-o301-fixed_tree-s503", "initial").step == 0
    with pytest.raises(SystemExit, match="no registered"):
        study.resolve_item("b101-o301-learned_tree-s503", "initial")  # step 0 is the fixed cell
    with pytest.raises(SystemExit, match="no registered"):
        study.resolve_item("b999-o301-fixed_tree-s501", "final")
    monkeypatch.setattr(sys, "argv", ["p", "loader-smoke", "--parent-suite", str(tmp_path)])
    with pytest.raises(SystemExit):
        study.main()  # --cell and --step are required
    monkeypatch.setattr(sys, "argv", ["p", "analyze"])
    with pytest.raises(SystemExit):
        study.main()  # --results-root is required for analyze


def test_loader_smoke_refuses_a_scratch_folder_under_results_or_experiments(
    tree_model: Model, panel: Tensor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import tempfile

    _smoke_setup(monkeypatch, tmp_path, tree_model, panel, None)
    (tmp_path / "experiments").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "experiments"))
    monkeypatch.setattr(study, "prepare", lambda *a: pytest.fail("must not load"))
    monkeypatch.setattr(sys, "argv", _smoke_argv(tmp_path))
    with pytest.raises(SystemExit, match="outside experiments/ results/"):
        study.main()
