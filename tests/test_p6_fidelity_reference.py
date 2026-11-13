"""Synthetic tests for the auditor's independent float64 P6-Q exhaustive reference.

No checkpoint or real data is opened. The frozen pilot code is imported only to
cross-check selected IDs on random fixtures.
"""

from __future__ import annotations

import math

import pytest
import torch
import torch.nn.functional as F

from arborlm.p6_fidelity_reference import exhaustive_reference
from arborlm.pilot_model import EPS, TEMP, tree_candidates

SLOTS = 4096
NEAR_TIE = 1e-5


def _unit(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True)


def _zeros() -> tuple[torch.Tensor, torch.Tensor]:
    return torch.zeros(SLOTS, 16), torch.zeros(16, 16)


def _e(index: int, scale: float = 1.0) -> torch.Tensor:
    vector = torch.zeros(16)
    vector[index] = scale
    return vector


# Hand-computed case: q = e0.
#   slots 0..7 (branch 0): key (3, 4, 0, ...) -> cos 0.6 -> 3.0
#   slot 4000 (branch 15): key 2*e0           -> cos 1.0 -> 5.0
#   all other slots zero                       -> cos 0   -> 0.0
#   router row 0 = e0 (route 5), rows 1..15 = e1 (route 0).
#   L = log(e^5 + 15); prior_0 = 5 - L, prior_b = -L otherwise.
def _hand_case() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    keys, router = _zeros()
    keys[0:8, 0] = 3.0
    keys[0:8, 1] = 4.0
    keys[4000] = _e(0, 2.0)
    router[0] = _e(0)
    router[1:] = _e(1)
    return _e(0).unsqueeze(0), keys, router


def test_hand_case_prior_off() -> None:
    q, keys, router = _hand_case()
    scores, selected, gap = exhaustive_reference(q, keys, router, use_prior=False)
    expected = torch.zeros(1, SLOTS, dtype=torch.float64)
    expected[0, 0:8] = 3.0
    expected[0, 4000] = 5.0
    assert torch.allclose(scores, expected, rtol=0, atol=1e-12)
    # 4000 first, then the 3.0 tie broken by ascending ID; slot 7 is the 9th.
    assert selected.tolist() == [[4000, 0, 1, 2, 3, 4, 5, 6]]
    assert gap.tolist() == [0.0]


def test_hand_case_prior_on_changes_selection() -> None:
    q, keys, router = _hand_case()
    scores, selected, gap = exhaustive_reference(q, keys, router, use_prior=True)
    log_z = math.log(math.exp(5.0) + 15.0)
    expected = torch.full((1, SLOTS), -log_z, dtype=torch.float64)
    expected[0, 0:256] = 5.0 - log_z  # branch 0 prior, zero cosine
    expected[0, 0:8] = 3.0 + 5.0 - log_z
    expected[0, 4000] = 5.0 - log_z
    assert torch.allclose(scores, expected, rtol=0, atol=1e-12)
    # The prior moves slot 4000 out; branch 0's cosine-0.6 slots take all eight places.
    assert selected.tolist() == [[0, 1, 2, 3, 4, 5, 6, 7]]
    # 9th score is 5 - L (slot 8, tied with 4000 and the rest of branch 0).
    assert gap.item() == pytest.approx(3.0, abs=1e-12)


def test_prior_can_promote_a_lower_cosine_slot() -> None:
    # q = e0; slot 10 (branch 0) cosine 1.0, slots 300..307 (branch 1) cosine 0.8.
    # Router favours branch 1 by 5 logits: prior on promotes branch 1 above slot 10.
    keys, router = _zeros()
    keys[10] = _e(0)
    keys[300:308, 0] = 4.0
    keys[300:308, 1] = 3.0
    router[1] = _e(0)
    router[[b for b in range(16) if b != 1]] = _e(2)
    q = _e(0).unsqueeze(0)
    _, off, off_gap = exhaustive_reference(q, keys, router, use_prior=False)
    _, on, on_gap = exhaustive_reference(q, keys, router, use_prior=True)
    assert off.tolist() == [[10, 300, 301, 302, 303, 304, 305, 306]]
    assert off_gap.item() == 0.0  # slot 307 ties slot 306
    assert on.tolist() == [[300, 301, 302, 303, 304, 305, 306, 307]]
    # 8th = 4 + p1, 9th = max(5 + p0 = 5 + p1 - 5, 0 + p1) -> gap 4.
    assert on_gap.item() == pytest.approx(4.0, abs=1e-12)


def test_exact_ties_resolve_by_ascending_slot_id() -> None:
    keys, router = _zeros()
    tied = [4095, 17, 2048, 5, 999, 3000, 12, 1, 700, 64]
    keys[tied] = _e(0)
    q = _e(0).unsqueeze(0)
    _, selected, gap = exhaustive_reference(q, keys, router, use_prior=False)
    assert selected.tolist() == [sorted(tied)[:8]]
    assert gap.tolist() == [0.0]
    # Zero router -> uniform prior; the tie order must be unchanged.
    _, selected_prior, gap_prior = exhaustive_reference(q, keys, router, use_prior=True)
    assert selected_prior.tolist() == [sorted(tied)[:8]]
    assert gap_prior.tolist() == [0.0]


def test_mixed_scores_order_descending_then_ascending_id() -> None:
    keys, router = _zeros()
    # Two strictly higher slots, then a five-way tie, then a lower slot.
    keys[3500] = _e(0)  # cos 1.0
    keys[[2600, 40]] = torch.tensor([4.0, 3.0] + [0.0] * 14)  # cos 0.8
    keys[[3999, 7, 1024, 255, 256]] = torch.tensor([3.0, 4.0] + [0.0] * 14)  # cos 0.6
    keys[9] = torch.tensor([1.0, 1.0] + [0.0] * 14)  # cos ~0.707
    q = _e(0).unsqueeze(0)
    _, selected, gap = exhaustive_reference(q, keys, router, use_prior=False)
    assert selected.tolist() == [[3500, 40, 2600, 9, 7, 255, 256, 1024]]
    assert gap.tolist() == [0.0]  # 3999 is the 9th and ties the 8th


def test_all_identical_keys_with_prior_select_top_branch_block() -> None:
    keys = _e(0).repeat(SLOTS, 1)
    router = torch.zeros(16, 16)
    router[:] = _e(1)
    router[3] = _e(0)
    q = _e(0).unsqueeze(0)
    _, selected, _ = exhaustive_reference(q, keys, router, use_prior=True)
    assert selected.tolist() == [list(range(768, 776))]
    _, selected_off, gap_off = exhaustive_reference(q, keys, router, use_prior=False)
    assert selected_off.tolist() == [list(range(8))]
    assert gap_off.tolist() == [0.0]


def _random_fixture(seed: int, n: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    generator = torch.Generator().manual_seed(seed)
    q = F.normalize(torch.randn(n, 16, generator=generator), dim=-1, eps=EPS)
    keys = torch.randn(SLOTS, 16, generator=generator)
    router = torch.randn(16, 16, generator=generator)
    return q, keys, router


def test_boundary_gap_is_eighth_minus_ninth_sorted_score() -> None:
    q, keys, router = _random_fixture(7, 32)
    for use_prior in (False, True):
        scores, selected, gap = exhaustive_reference(q, keys, router, use_prior=use_prior)
        top9 = scores.sort(dim=1, descending=True).values[:, :9]
        assert torch.equal(gap, top9[:, 7] - top9[:, 8])
        assert torch.equal(scores.gather(1, selected), top9[:, :8])
        assert bool((gap >= 0).all())


def test_logsumexp_does_not_change_selection() -> None:
    # Independent algebra check: log_softmax(rho)_b = rho_b - logsumexp(rho).
    q, keys, router = _random_fixture(11, 64)
    scores, selected, _ = exhaustive_reference(q, keys, router, use_prior=True)
    cosine, _, _ = exhaustive_reference(q, keys, router, use_prior=False)
    rho = (q.double() @ _unit(router.double()).T) / 0.2
    branch = torch.arange(SLOTS) // 256
    shifted = scores - (cosine + rho[:, branch])
    assert torch.allclose(shifted, -torch.logsumexp(rho, dim=1, keepdim=True).expand_as(shifted))
    alt = (cosine + rho[:, branch]).sort(dim=1, descending=True, stable=True).indices[:, :8]
    assert torch.equal(alt, selected)


def test_output_contract_inputs_unmodified_and_deterministic() -> None:
    q, keys, router = _random_fixture(3, 16)
    originals = (q.clone(), keys.clone(), router.clone())
    first = exhaustive_reference(q, keys, router, use_prior=True)
    second = exhaustive_reference(q, keys, router, use_prior=True)
    for before, after in zip(originals, (q, keys, router), strict=True):
        assert torch.equal(before, after) and after.dtype == torch.float32
    scores, selected, gap = first
    assert scores.shape == (16, SLOTS) and scores.dtype == torch.float64
    assert selected.shape == (16, 8) and selected.dtype == torch.int64
    assert gap.shape == (16,) and gap.dtype == torch.float64
    for a, b in zip(first, second, strict=True):
        assert torch.equal(a, b)


def test_q_is_not_renormalized() -> None:
    keys, router = _zeros()
    keys[0] = _e(0)
    q = _e(0, 0.5).unsqueeze(0)
    scores, _, _ = exhaustive_reference(q, keys, router, use_prior=False)
    assert scores[0, 0].item() == pytest.approx(2.5, abs=1e-12)


@pytest.mark.parametrize(
    ("q", "keys", "router", "error"),
    [
        (torch.zeros(2, 16, dtype=torch.float64), torch.zeros(SLOTS, 16), torch.zeros(16, 16),
         TypeError),
        (torch.zeros(2, 15), torch.zeros(SLOTS, 16), torch.zeros(16, 16), ValueError),
        (torch.zeros(16), torch.zeros(SLOTS, 16), torch.zeros(16, 16), ValueError),
        (torch.zeros(2, 16), torch.zeros(4095, 16), torch.zeros(16, 16), ValueError),
        (torch.zeros(2, 16), torch.zeros(SLOTS, 16), torch.zeros(15, 16), ValueError),
        (torch.zeros(2, 16), torch.zeros(SLOTS, 16, dtype=torch.float16), torch.zeros(16, 16),
         TypeError),
        (torch.full((2, 16), float("nan")), torch.zeros(SLOTS, 16), torch.zeros(16, 16),
         ValueError),
    ],
)
def test_rejects_bad_inputs(
    q: torch.Tensor, keys: torch.Tensor, router: torch.Tensor, error: type[Exception]
) -> None:
    with pytest.raises(error):
        exhaustive_reference(q, keys, router, use_prior=True)


@pytest.mark.parametrize("use_prior", [False, True])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_agrees_with_frozen_tree_candidates_visit16(seed: int, use_prior: bool) -> None:
    q, keys, router = _random_fixture(1000 + seed, 512)
    # Routes exactly as Memory.lookup computes them for the frozen call.
    routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
    frozen_values, frozen_ids, _, _ = tree_candidates(
        q, keys, routes, visit=16, use_prior=use_prior
    )
    scores, selected, gap = exhaustive_reference(q, keys, router, use_prior=use_prior)

    near = gap <= NEAR_TIE
    assert int(near.sum()) <= 5, "fixture is supposed to have (almost) no near-ties"
    mismatched = (frozen_ids != selected).any(dim=1)
    assert not bool((mismatched & ~near).any()), torch.nonzero(mismatched & ~near).flatten()

    # Ordered agreement holds wherever all consecutive top-9 gaps exceed the tolerance.
    top9 = scores.sort(dim=1, descending=True).values[:, :9]
    clean = (top9[:, :-1] - top9[:, 1:]).min(dim=1).values > NEAR_TIE
    assert torch.equal(frozen_ids[clean], selected[clean])

    diff = (frozen_values.double() - scores.gather(1, frozen_ids)).abs().max().item()
    print(
        f"seed={seed} use_prior={use_prior} N=512 near_ties={int(near.sum())} "
        f"id_mismatches={int(mismatched.sum())} min_gap={gap.min().item():.3e} "
        f"max_abs_selected_score_diff_f32_vs_f64={diff:.3e}"
    )
    assert diff < 1e-5
