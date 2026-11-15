# ruff: noqa: E501
"""P9I models: gradient reach for every arm, arm N against ADR-0017's R0a, initial identities of block BB,
parameter counts and the D7 match, answer-site-only reads, interface structure. Tiny inputs, test seeds,
synthetic random backbone. Self-check only: not independent review, not Astra validation, not human
approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9i import core, model, train  # noqa: E402
from studies.p9i.model import IDense, IMemory, P9IModel  # noqa: E402

SEED = 900011


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


@pytest.fixture(scope="module")
def tokens() -> torch.Tensor:
    g = torch.Generator().manual_seed(5)
    out = torch.randint(0x40, 0x60, (6, 64), generator=g)
    out[:, 0::8] = 100  # a template separator byte outside the alphabet
    return out


def _lut(n: int = 4096) -> torch.Tensor:
    g = torch.Generator().manual_seed(9)
    return torch.randint(0, n, (32**4,), generator=g)


def _build(arm: str, backbone, slots: int = 4096) -> P9IModel:  # type: ignore[no-untyped-def]
    return model.build_model(arm, slots, SEED, backbone, fact_lut=_lut(slots) if arm == "R2" else None, r1_seed=900031)


# arm -> trainable group names that must exist (everything else must be absent)
EXPECTED_GROUPS = {
    "N": {"keys", "values", "projections"},
    "W7": {"keys", "values", "projections"},
    "E7": {"keys", "values", "projections"},
    "A4": {"keys", "values", "projections", "interface"},
    "A4E": {"keys", "values", "projections", "interface"},
    "R1": {"keys", "values", "projections"},
    "R2": {"values", "projections"},
    "D": {"dense"},
    "D7": {"dense"},
    "BB": {"keys", "values", "projections", "backbone_attention"},
    "BB-D": {"dense", "backbone_attention"},
    "BB-0": {"backbone_attention"},
}


@pytest.mark.parametrize("arm", core.ARMS)
def test_gradient_reach_every_trainable_group_and_nothing_else(arm: str, backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    net = _build(arm, backbone)
    groups = {g for g, items in net.trainable_groups().items() if items}
    assert groups == EXPECTED_GROUPS[arm]
    result = train.gradient_reach(net, tokens)
    assert result["stray"] == []
    assert result["reached"] and all(result["reached"].values()), [n for n, ok in result["reached"].items() if not ok]
    # every parameter that is not trainable received no gradient and did not change
    for name, p in net.named_parameters():
        assert p.requires_grad == (name in result["reached"])
        assert p.grad is None  # gradient_reach clears its gradients


@pytest.mark.parametrize("arm", ["N", "A4", "BB", "D7", "R2"])
def test_a_step_changes_only_the_trainable_parameters(arm: str, backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    net = _build(arm, backbone)
    before = {n: p.detach().clone() for n, p in net.named_parameters()}
    opts = train.build_optimizers(net)
    trainer = train.Trainer(core.make_cell(arm, 4096), net, opts)
    trainer.step(tokens)
    moved = 0
    for name, p in net.named_parameters():
        same = torch.equal(before[name], p.detach())
        if not p.requires_grad:
            assert same, name  # frozen parameters never change
        else:
            moved += int(not same)
    assert moved >= 1


def test_bb_trains_exactly_the_4224_block0_attention_parameters(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    for arm in core.BB_ARMS:
        net = _build(arm, backbone)
        trainable_backbone = {n for n, p in net.named_parameters() if n.startswith("backbone.") and p.requires_grad}
        assert trainable_backbone == {"backbone.blocks.0.qkv.weight", "backbone.blocks.0.qkv.bias", "backbone.blocks.0.attn_out.weight", "backbone.blocks.0.attn_out.bias"}
        assert sum(p.numel() for n, p in net.named_parameters() if n in trainable_backbone) == 4224
        assert model.parameter_report(net).trainable_backbone == 4224
    for arm in set(core.ARMS) - set(core.BB_ARMS):
        net = _build(arm, backbone)
        assert model.parameter_report(net).trainable_backbone == 0
        assert not any(p.requires_grad for n, p in net.named_parameters() if n.startswith("backbone."))
    # after training steps the other backbone tensors are bit-identical to the original backbone
    net = _build("BB", backbone)
    opts = train.build_optimizers(net)
    trainer = train.Trainer(core.make_cell("BB", 4096), net, opts)
    for _ in range(3):
        trainer.step(tokens)
    original = dict(backbone.named_parameters())
    for name, p in net.named_parameters():
        if name.startswith("backbone."):
            key = name[len("backbone.") :]
            if p.requires_grad:
                assert not torch.equal(p, original[key]), name
            else:
                assert torch.equal(p, original[key]), name


def test_n_forward_equals_p9_r0a_bit_for_bit(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    for slots in (4096, 16384):
        result = model.n_against_p9_r0a(backbone, slots, SEED, tokens[:, :63])
        assert result["same_parameters"] and result["hidden_identical"]
        assert result["selection_identical"] and result["scores_identical"] and result["read_vector_identical"]
        assert result["logits_identical"] and result["answer_site_logits_identical"]
        assert result["max_abs_logit_difference"] == 0.0
        assert result["read_positions"] == list(core.ANSWER_SITE_POSITIONS)


def test_initial_forward_identities_of_block_bb(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    ids = model.initial_identities(backbone, 4096, SEED, tokens[:, :63])
    assert ids == {"bb_equals_n": True, "bb_d_equals_d": True, "bb_0_equals_no_memory": True}
    # BB-0 is the no-memory baseline of P9's controls
    net = _build("BB-0", backbone)
    net.eval()
    with torch.no_grad():
        got = net(tokens[:, :63])[0]
        base = controls.logits_from_hidden(backbone, controls.insertion_hidden(backbone, tokens[:, :63]))
    assert torch.equal(got, base)


def test_parameter_counts_at_the_three_sizes(backbone) -> None:  # type: ignore[no-untyped-def]
    expected_hidden = {4096: 786, 16384: 3090, 65536: 12306}
    for slots in core.SLOTS_BY_SIZE:
        n = model.parameter_report(_build("N", backbone, slots))
        assert n.trainable == p9core.memory_parameters("flat", slots) and n.interface_extra == 0
        w7 = model.parameter_report(_build("W7", backbone, slots))
        assert w7.interface_extra == 3072 and w7.trainable == n.trainable + 3072
        assert model.parameter_report(_build("E7", backbone, slots)).interface_extra == 3072
        for arm in ("A4", "A4E"):
            a = model.parameter_report(_build(arm, backbone, slots))
            assert a.interface_extra == 3072 and a.trainable == n.trainable + 3072 and a.by_group["interface"] == 3072
        d = model.parameter_report(_build("D", backbone, slots))
        assert d.trainable == n.trainable  # parameter-matched to arm N
        d7 = model.parameter_report(_build("D7", backbone, slots))
        assert d7.dense_hidden == expected_hidden[slots]
        assert abs(d7.trainable - w7.trainable) / w7.trainable <= 0.001  # within 0.1%, including the interface
        for arm in core.BB_ARMS:
            assert model.parameter_report(_build(arm, backbone, slots)).trainable_backbone == 4224
        bb = model.parameter_report(_build("BB", backbone, slots))
        assert bb.trainable == n.trainable + 4224 and bb.frozen_backbone == 27392 - 4224


def test_reads_and_dense_outputs_are_at_answer_sites_only(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    sites = list(core.ANSWER_SITE_POSITIONS)
    others = [p for p in range(63) if p not in sites]
    for arm in ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7", "BB-D"):
        net = _build(arm, backbone)
        net.eval()
        with torch.no_grad():
            h = net.embed_block0(tokens[:, :63])
            sel = net.select(h, tokens[:, :63])
            delta = net.memory_delta(h, sel)
        assert float(delta[:, others].abs().max()) == 0.0, arm
        assert float(delta[:, sites].abs().max()) > 0.0, arm
        if sel is not None:
            assert sel.positions.tolist() == sites


def test_window_features_are_positions_t_minus_6_to_t() -> None:
    x = torch.arange(2 * 63 * 32, dtype=torch.float32).reshape(2, 63, 32)
    feats = IMemory.window(x, torch.tensor(core.ANSWER_SITE_POSITIONS))
    assert feats.shape == (2, 8, 224)
    for r in range(8):
        t = 8 * r + 6
        assert torch.equal(feats[:, r], torch.cat([x[:, t - 6 + j] for j in range(7)], dim=-1))
    with pytest.raises(ValueError):
        IMemory.window(x, torch.tensor([3]))


def test_a4_is_causal_over_the_prefix_with_the_backbones_attention_form(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    mem = IMemory("A4", 4096, SEED)
    g = torch.Generator().manual_seed(2)
    x = torch.randn(2, 63, 32, generator=g)
    positions = torch.tensor(core.ANSWER_SITE_POSITIONS)
    out, w = mem.attend(x, positions)
    assert out.shape == (2, 8, 32) and w.shape == (2, 4, 8, 63)
    assert torch.allclose(w.sum(-1), torch.ones(2, 4, 8))
    for r, t in enumerate(core.ANSWER_SITE_POSITIONS):
        assert t + 1 >= 63 or float(w[:, :, r, t + 1 :].abs().max()) == 0.0  # nothing after the answer site
    changed = x.clone()
    changed[:, 40:] += 5.0  # later positions do not affect the early sites
    out2, _ = mem.attend(changed, positions)
    assert torch.equal(out[:, :5], out2[:, :5])  # sites 6 .. 38 see only positions <= 38
    assert mem.attn_q.shape == mem.attn_k.shape == mem.attn_v.shape == (32, 32)
    assert not any("bias" in n for n, _ in mem.named_parameters())
    # scores scaled by 1/sqrt(8): recompute one head by hand
    q = torch.nn.functional.linear(x[:, positions], mem.attn_q).reshape(2, 8, 4, 8).permute(0, 2, 1, 3)
    k = torch.nn.functional.linear(x, mem.attn_k).reshape(2, 63, 4, 8).permute(0, 2, 1, 3)
    scores = (q @ k.transpose(-2, -1)) / 8**0.5
    mask = torch.arange(63)[None, :] > positions[:, None]
    ref = scores.masked_fill(mask, -torch.inf).softmax(-1)
    assert torch.allclose(ref, w, atol=1e-7)


def test_e7_and_a4e_read_embeddings_not_block_zero_output(backbone, tokens) -> None:  # type: ignore[no-untyped-def]
    for arm in ("E7", "A4E"):
        net = _build(arm, backbone)
        net.eval()
        with torch.no_grad():
            e = net.embedding(tokens[:, :63])
            h = net.embed_block0(tokens[:, :63])
            q = net.answer_queries(h, tokens[:, :63])
            q_other = net.answer_queries(h * 3.0 + 1.0, tokens[:, :63])  # the block-0 state is ignored
            direct = net.addition._query(e, tokens[:, :63], model.SITES).reshape(6, 8, -1)
        assert q is not None and q_other is not None
        assert torch.equal(q, q_other) and torch.equal(q, direct)
    net = _build("W7", backbone)
    with torch.no_grad():
        h = net.embed_block0(tokens[:, :63])
        assert not torch.equal(net.answer_queries(h, tokens[:, :63]), net.answer_queries(h * 3.0 + 1.0, tokens[:, :63]))  # type: ignore[arg-type]


def test_dense_plain_matches_p9_adapter_initialization_and_d7_shapes() -> None:
    from studies.p9.model import DenseAdapter

    h = core.dense_plain_hidden_width(4096)
    mine, theirs = IDense(h, SEED, 1), DenseAdapter(h, SEED)
    for name in ("w1", "w2", "gate"):
        assert torch.equal(getattr(mine, name), getattr(theirs, name))
    d7 = IDense(core.d7_hidden_width(4096), SEED, 7)
    assert d7.w1.shape == (786, 224) and d7.w2.shape == (32, 786)


def test_unknown_arm_and_missing_lut_are_refused(backbone) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        model.build_model("A1", 4096, SEED, backbone)
    with pytest.raises(ValueError):
        model.build_model("R2", 4096, SEED, backbone)
    with pytest.raises(ValueError):
        model.set_trainable(_build("N", backbone), ["nonsense"])


def test_identifier_attention_mass_counts_the_five_identifier_positions() -> None:
    w = torch.zeros(1, 4, 8, 63)
    for r in range(8):
        w[0, :, r, 8 * r + 1 : 8 * r + 6] = 0.1
    mass = model.identifier_attention_mass(w)
    assert mass.shape == (1, 4, 8) and torch.allclose(mass, torch.full((1, 4, 8), 0.5))
