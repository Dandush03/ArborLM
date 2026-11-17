# ruff: noqa: E501
"""P10S0 models: WX (ADR-0020 section 5.2: 16 x 2,048 over the whole causal context, zero-padded before position 0, W7 as its special case), the arms taken unedited from studies.p9ii, the seeded derangement
of the read swap. Tiny sizes, test seeds 920001-920999 only, synthetic backbone. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9ii import model as p9iimodel  # noqa: E402
from studies.p10s0 import core, evaluate, model, train  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

SPEC = core.test_set(1)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


@pytest.fixture(scope="module")
def draw():  # type: ignore[no-untyped-def]
    return syn.tiny_data(SPEC, 2048)


@pytest.fixture(scope="module")
def tokens(draw):  # type: ignore[no-untyped-def]
    return train.training_stream_for(draw, 128).batch(1).tokens[:, : core.INPUT_LENGTH]


# --- WX -----------------------------------------------------------------------------------------------------------------------------------------
def test_wx_has_a_16_by_2048_projection_and_the_base_arms_other_parameters(backbone) -> None:  # type: ignore[no-untyped-def]
    for base in ("A5-D", "A1"):
        wx = model.build_model(f"WX-{base}", 4096, 920041, backbone)
        plain = p9iimodel.build_model(base, 4096, 920041, backbone)
        assert tuple(wx.addition.wq.shape) == (16, 2048) and wx.addition.wq.numel() == 32768 and plain.addition.wq.numel() == 3584
        others = {n: p for n, p in wx.addition.named_parameters() if n != "wq"}
        assert {n for n, _ in plain.addition.named_parameters() if n != "wq"} == set(others)
        assert all(torch.equal(p, dict(plain.addition.named_parameters())[n]) for n, p in others.items())  # keys, values, wo, gate are the base arm's at the same seed
        assert wx.arm == f"WX-{base}" and wx.ii_arm == base and sum(p.numel() for p in wx.backbone.parameters() if p.requires_grad) == 0


def test_wx_initializer_is_w7_s_at_fan_in_2048(backbone) -> None:  # type: ignore[no-untyped-def]
    from arborlm.pilot_model import _matrix

    wx = model.build_model("WX-A5-D", 4096, 920041, backbone)
    assert torch.equal(wx.addition.wq, _matrix(920041 + 3000, 16, 2048))
    assert float(wx.addition.wq.std()) == pytest.approx(0.02, rel=0.05)


def test_full_window_is_oldest_first_and_zero_padded_before_position_0() -> None:
    x = torch.arange(2 * 63 * 32, dtype=torch.float32).reshape(2, 63, 32) + 1.0
    sites = p9iimodel.SITES
    w = model.WXMemory.full_window(x, sites)
    assert tuple(w.shape) == (2, 8, 2048)
    last = w[:, :, -7 * 32 :].reshape(2, 8, 7, 32)
    index = sites[:, None] + torch.arange(-6, 1)[None, :]
    assert torch.equal(last, x[:, index])  # the last 7 steps are W7's window, oldest first
    first = w[:, 0].reshape(2, 64, 32)  # site 0 is position 6: steps 0..56 reach before position 0
    assert bool((first[:, :57] == 0).all()) and torch.equal(first[:, 57], x[:, 0]) and torch.equal(first[:, 63], x[:, 6])
    full = w[:, 7].reshape(2, 64, 32)  # position 62: steps from position -1 are zero
    assert bool((full[:, 0] == 0).all()) and torch.equal(full[:, 1], x[:, 0])


def test_wx_with_w_x_zero_outside_the_last_224_columns_gives_w7_s_query(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    w7 = p9iimodel.build_model("A5-D", 4096, 920041, backbone, seed_rng=False)
    wx = model.build_model("WX-A5-D", 4096, 920041, backbone, seed_rng=False)
    with torch.no_grad():
        wx.addition.wq.copy_(model.w7_equivalent_projection(w7.addition.wq))
    assert bool((wx.addition.wq[:, :-224] == 0).all()) and torch.equal(wx.addition.wq[:, -224:], w7.addition.wq)
    w7.eval()
    wx.eval()
    h = w7.embed_block0(tokens)
    q7, qx = w7.answer_queries(h, tokens), wx.answer_queries(h, tokens)
    assert q7 is not None and qx is not None
    assert torch.allclose(q7, qx, atol=1e-6)
    if core.on_registered_platform():
        assert torch.equal(q7, qx)  # bit for bit where the gate asserts it
    z7, zx = w7.answer_z(h, tokens), wx.answer_z(h, tokens)
    assert z7 is not None and zx is not None and torch.allclose(z7, zx, atol=1e-6)


def test_wx_changes_only_the_query(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    """Same keys and values, so the read differs only through the query: with the same projection the logits equal W7's up to the platform tolerance."""
    w7 = p9iimodel.build_model("A1", 4096, 920041, backbone, seed_rng=False)
    wx = model.build_model("WX-A1", 4096, 920041, backbone, seed_rng=False)
    with torch.no_grad():
        wx.addition.wq.copy_(model.w7_equivalent_projection(w7.addition.wq))
    w7.eval()
    wx.eval()
    with torch.no_grad():
        assert torch.allclose(w7(tokens)[0], wx(tokens)[0], atol=1e-5)


@pytest.mark.parametrize("arm", ["WX-A5-D", "WX-A1"])
def test_wx_trains_with_the_base_arm_s_loss_terms(arm: str, backbone, draw, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    cell = core.make_cell(arm, "2K/4K")
    job = train.Job(cell=cell, mode="dry", data=draw, stream=train.training_stream_for(draw, 128), backbone=backbone, out_dir=tmp_path, init_seed=920041, r1_seed=draw.seeds.r1_codes, target_seed=SPEC.target_seed("2K/4K", 0), unit=8, diag_every=4, max_updates=4)
    stream_tokens = job.stream.batch(1)
    reach = train.gradient_reach(job, stream_tokens.tokens, stream_tokens.fact_ids, "training")
    assert reach["reached"]["addition.wq"] and all(reach["reached"].values()) and not reach["stray"] and not reach["buffer_gradients"]
    base = core.base_arm(arm)
    parts = "div" if base == "A5-D" else "addr"
    own = train.gradient_reach(job, stream_tokens.tokens, stream_tokens.fact_ids, parts)
    reached = sorted(n.rsplit(".", 1)[-1] for n, v in own["reached"].items() if v)
    assert reached == (["wq"] if base == "A5-D" else ["keys", "wq"])  # L_div reaches the query projection; L_addr the projection and the keys
    run = train.run_job(job)
    rec = run.updates[0]
    assert (rec["diversity_loss"] is not None) == (base == "A5-D") and (rec["address_loss"] is not None) == (base == "A1")
    assert run.record["trainable_backbone_parameters"] == 0 and run.record["parameters_by_group"]["wq"] == 32768


# --- the arms of studies.p9ii are used unedited ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["A0", "A1", "A2", "A5-D", "A6", "A7"])
def test_non_wx_arms_are_p9ii_s_own_models(arm: str, backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    ours = model.build_model(arm, 4096, 920041, backbone, r1_seed=920101)
    theirs = p9iimodel.build_model(arm, 4096, 920041, backbone, r1_seed=920101)
    assert type(ours) is type(theirs) and all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in ours.named_parameters())
    ours.eval()
    theirs.eval()
    with torch.no_grad():
        assert torch.equal(ours(tokens)[0], theirs(tokens)[0])


def test_unknown_arms_are_refused(backbone) -> None:  # type: ignore[no-untyped-def]
    for arm in ("A4", "A5-C", "A1-S", "WX-A0", "WX-A2", "nonsense"):
        with pytest.raises(ValueError):
            model.build_model(arm, 4096, 1, backbone)


def test_the_forward_takes_tokens_only(backbone) -> None:  # type: ignore[no-untyped-def]
    for arm in core.LEARNED_ARMS:
        args = p9iimodel.forward_arguments(model.build_model(arm, 4096, 920041, backbone, seed_rng=False))
        assert args["forward"] == ["tokens"] and args["select"] == ["h_pre", "tokens"], arm


# --- the derangement and the swap -------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n,seed", [(128, 920051), (256, 920052), (512, 920053), (2048, 920051), (4096, 7)])
def test_derangement_has_no_fixed_point_and_no_pair_with_equal_answers(n: int, seed: int) -> None:
    answers = torch.randint(0, 32, (n,), generator=torch.Generator().manual_seed(n + seed))
    perm = model.derangement(answers, seed)
    assert sorted(perm.tolist()) == list(range(n)) and not bool((perm == torch.arange(n)).any()) and not bool((answers[perm] == answers).any())
    assert torch.equal(perm, model.derangement(answers, seed)) and not torch.equal(perm, model.derangement(answers, seed + 1))  # deterministic in the seed


def test_derangement_with_the_registered_answer_distribution_at_every_fact_count() -> None:
    for n in (2048, 8192, 32768):
        answers = torch.arange(n) % 32
        perm = model.derangement(answers[torch.randperm(n, generator=torch.Generator().manual_seed(1))], 920051)
        assert perm.numel() == n


def test_derangement_refuses_when_none_exists() -> None:
    with pytest.raises(ValueError):
        model.derangement(torch.zeros(8, dtype=torch.int64), 1)
    with pytest.raises(ValueError):
        model.derangement(torch.tensor([3]), 1)


def test_swapping_twice_with_the_inverse_restores_the_reads() -> None:
    table = torch.randn(512, 32, generator=torch.Generator().manual_seed(3))
    perm = model.derangement(torch.arange(512) % 32, 920051)
    swapped = model.swap_reads(table, perm)
    assert not bool((swapped == table).all(dim=1).any()) and torch.equal(model.swap_reads(swapped, model.inverse(perm)), table)
    assert torch.equal(model.inverse(model.inverse(perm)), perm)


def test_the_fact_answers_come_from_the_panel_and_cover_every_trained_fact(draw) -> None:  # type: ignore[no-untyped-def]
    a = evaluate.fact_answers(draw, 128, "A")
    b = evaluate.fact_answers(draw, 128, "B")
    assert a.shape == (128,) and torch.equal(a, b) and int(a.min()) >= 0 and int(a.max()) < 32
    perm = evaluate.swap_permutation(draw, 128, SPEC.swap_seed(2048))
    assert not bool((a[perm] == a).any())
