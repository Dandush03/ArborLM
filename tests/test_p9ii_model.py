# ruff: noqa: E501
"""P9II models and gates (ADR-0019 sections 3, 4 and 9): A0's identity with P9-I's W7, parameter counts, gradient reach per arm on covered contexts, the
address loss, A4's schedule and read, A5-C's centre, A2's switch, A1-S's targets, G5 and G6. Tiny sizes, test seeds, synthetic backbone. Self-check only: not
independent review, not Astra validation, not human approval."""

import copy
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9i.stages import gate_contexts  # noqa: E402
from studies.p9ii import core, gates, model, train  # noqa: E402

SIZES = d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
FACTS = 128
HYPER = core.Hyper(lambda_=1.0, u_pre=4.0, k0_fraction=0.125, mu=0.1)


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def draw() -> d.StudyData:
    return d.build_study_data(core.test_seeds(1), _corpus(), sizes=SIZES)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def _job(draw: d.StudyData, backbone, arm: str, tmp: Path, updates: int = 8, **kw):  # type: ignore[no-untyped-def]
    return gates.tiny_job(arm, draw, backbone, FACTS, tmp / arm, hyper=kw.pop("hyper", HYPER), updates=updates, mode="calibration", init_seed=910041, **kw)


# --- A0 is P9-I's W7 -------------------------------------------------------------------------------------------------------------------
def test_a0_is_bit_identical_to_p9i_w7_in_forward_and_in_one_training_step(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    r = gates.a0_identity(_job(draw, backbone, "A0", tmp_path))
    assert r["same_parameters"] and r["logits_identical"] and r["selection_identical"] and r["scores_identical"]
    assert r["loss_identical"] and r["parameters_identical_after_step"] and r["passed"]


def test_a0_trains_exactly_like_w7_over_several_updates(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from studies.p9i import core as icore
    from studies.p9i import model as imodel
    from studies.p9i import train as itrain

    job = _job(draw, backbone, "A0", tmp_path)
    theirs = imodel.build_model("W7", 4096, 910041, backbone)
    t1 = itrain.Trainer(icore.make_cell("W7", 4096), theirs, itrain.build_optimizers(theirs))
    t2 = train.Trainer(job, model.build_model("A0", 4096, 910041, backbone), gates.train_probe(job))
    for u in range(1, 5):
        a, b = t1.step(job.stream.batch(u).tokens), t2.step(job.stream.batch(u))
        assert a["task_loss"] == b["task_loss"]
    assert all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in t2.model.named_parameters() if n.startswith("addition."))


# --- parameters --------------------------------------------------------------------------------------------------------------------------
def test_trainable_parameter_counts_per_arm_at_4096_slots(backbone) -> None:  # type: ignore[no-untyped-def]
    counts = {}
    for arm in core.ARMS:
        m = model.build_model(arm, 4096, 910041, backbone)
        counts[arm] = model.parameter_report(m)["trainable"]
        assert model.parameter_report(m)["trainable_backbone"] == 0 and not any(p.requires_grad for p in m.backbone.parameters())  # no backbone parameter trains, in any arm
    w7 = 4096 * 16 + 4096 * 32 + 16 * 224 + 32 * 32 + 1
    assert w7 == 201217
    same = ("A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S", "A7")
    assert {a: counts[a] for a in same} == dict.fromkeys(same, w7)
    assert counts["A6"] == 4096 * 16 + 4096 * 32 + 32 * 32 + 1  # R1 has no query projection
    a2 = model.build_model("A2", 4096, 910041, backbone)
    model.set_a2_phase(a2, 1)
    assert model.parameter_report(a2)["trainable"] == 4096 * 16 + 16 * 224 and model.parameter_report(a2)["by_group"]["wq"] == 3584  # phase 1: wq and keys only
    assert model.parameter_report(model.build_model("A5-C", 4096, 910041, backbone))["buffers"] == 17  # m (16) and its initialised flag


# --- gradient reach ------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", core.ARMS)
def test_gradient_reach_per_arm_on_covered_contexts(draw, backbone, tmp_path: Path, arm: str) -> None:  # type: ignore[no-untyped-def]
    tokens, ids = gate_contexts(draw, FACTS)
    r = gates.reach_checks(_job(draw, backbone, arm, tmp_path), tokens, ids)
    assert r["passed"], r
    assert r["training"]["all_reached"] and not r["training"]["stray"] and not r["training"]["buffer_gradients"]
    if arm in core.TARGET_ARMS:
        assert r["address_loss"]["reached"] == ["keys", "wq"] and r["address_loss"]["stray"] == []  # the address loss reaches the query projection and keys and nothing else
    if arm == "A5-D":
        assert r["diversity_loss"]["reached"] == ["wq"]
    if arm == "A2":
        assert r["phase1"]["trainable"] == ["keys", "wq"]  # values, output projection and gate are frozen in phase 1


def test_address_loss_gives_every_key_a_gradient_because_it_uses_all_n_scores(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A1", tmp_path)
    t = train.Trainer(job, model.build_model("A1", 4096, 910041, backbone), gates.train_probe(job))
    batch = job.stream.batch(1)
    _, parts = t.compute_losses(batch.tokens, batch.fact_ids, 1, 1)
    parts["addr"].backward()  # type: ignore[no-untyped-call]
    grad = t.model.addition.keys.grad
    assert grad is not None and int((grad.abs().sum(-1) > 0).sum()) == 4096  # not only the top-8 rows


def test_a_non_target_arm_has_no_address_loss(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A0", tmp_path)
    t = train.Trainer(job, model.build_model("A0", 4096, 910041, backbone), gates.train_probe(job))
    _, parts = t.compute_losses(job.stream.batch(1).tokens, job.stream.batch(1).fact_ids, 1, 1)
    assert set(parts) == {"answer"}


def test_all_n_scores_checks_at_65536_and_16384() -> None:
    r = gates.full_score_checks()
    assert r["passed"] and r["address_loss_all_n_scores"]["slots"] == 65536 and r["a4_read_k_equals_n"]["slots"] == 16384
    g = torch.Generator().manual_seed(2)
    q = F.normalize(torch.randn(6, 16, generator=g), dim=-1)
    keys = torch.randn(9, 16, generator=torch.Generator().manual_seed(1))
    manual = torch.stack([-torch.log_softmax((q[i] @ F.normalize(keys, dim=-1).T) / 0.2, 0)[3] for i in range(6)]).mean()
    assert torch.allclose(model.address_loss(q, keys, torch.full((6,), 3)), manual)
    sims = q @ q.T
    off = ~torch.eye(6, dtype=torch.bool)
    assert torch.allclose(model.diversity_loss(q), torch.log(torch.exp(2 * sims[off]).mean()), atol=1e-6)  # L_div = log(mean_{i != j} exp(2 q_i . q_j))
    assert list(inspect.signature(model.diversity_loss).parameters) == ["q"]  # uses no fact identity


# --- A4 ------------------------------------------------------------------------------------------------------------------------------------
def test_a4_schedule_endpoint_and_standard_read(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    r = gates.schedule_checks(_job(draw, backbone, "A4", tmp_path, updates=16), _job(draw, backbone, "A2", tmp_path, updates=16))
    assert r["a4"]["k_matches_formula"] and r["a4"]["final_read_is_standard_top8"] and r["passed"]
    assert r["a4"]["k_got"][0] == r["a4"]["k0"] == 512 and r["a4"]["k_got"][r["a4"]["t_anneal"]] == 8


def test_a4_wide_read_uses_k_slots_and_standard_read_at_eval(draw, backbone) -> None:  # type: ignore[no-untyped-def]
    m = model.build_model("A4", 4096, 910041, backbone)
    tokens = draw.streams["panel_a"].tokens[:4, :63].contiguous()
    m.eval()
    with torch.no_grad():
        h = m.embed_block0(tokens)
        m.set_read_k(64)
        wide = m.select(h, tokens)
        m.set_read_k(8)
        std = m.select(h, tokens)
        a0 = model.build_model("A0", 4096, 910041, backbone)
        ref = a0.select(h, tokens)
    assert wide is not None and std is not None and ref is not None and wide.selected.shape[-1] == 64 and std.selected.shape[-1] == 8
    assert torch.equal(std.selected, ref.selected) and torch.equal(std.scores, ref.scores)  # at k = 8 the read is the standard top-8 read
    assert torch.equal(wide.selected[..., :8], std.selected)
    a0.set_read_k(512)
    with torch.no_grad():
        only = a0.select(h, tokens)
    assert only is not None and only.selected.shape[-1] == 8  # only A4 reads wide


def test_a4_read_at_k_equals_n_is_the_dense_softmax_over_all_slots(backbone) -> None:  # type: ignore[no-untyped-def]
    n = 16384
    m = model.build_model("A4", n, 910041, backbone)
    g = torch.Generator().manual_seed(5)
    tokens = torch.randint(0x40, 0x60, (2, 63), generator=g)
    m.eval()
    m.set_read_k(n)
    with torch.no_grad():
        h = m.embed_block0(tokens)
        sel = m.select(h, tokens)
        assert sel is not None and sel.selected.shape[-1] == n
        delta = m.memory_delta(h, sel)
        q = m.answer_queries(h, tokens)
        assert q is not None
        mem = m.addition
        scores = (q.reshape(-1, 16) @ F.normalize(mem.keys, dim=-1).T) / 0.2
        direct = scores.softmax(-1) @ mem.values
        expected = mem.gate.sigmoid() * F.linear(direct.reshape(2, 8, 32), mem.wo)
    sites = torch.tensor(core.ANSWER_SITE_POSITIONS)
    assert torch.allclose(delta[:, sites], expected, atol=1e-5)


# --- A5-C ---------------------------------------------------------------------------------------------------------------------------------
def test_a5c_centre_is_a_buffer_ema_frozen_at_evaluation_and_restored(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A5-C", tmp_path)
    run = train.run_job(job)
    mem = run.model.addition
    assert "centre" in dict(mem.named_buffers()) and "centre" not in dict(mem.named_parameters()) and not dict(mem.named_buffers())["centre"].requires_grad
    assert "addition.centre" in run.model.state_dict()  # restored from checkpoints
    m = model.build_model("A5-C", 4096, 910041, backbone)
    rows = train.initial_centre_rows(m, job.stream)
    assert rows.shape == (16 * 128, 16)
    m.addition.init_centre(rows)
    assert torch.allclose(dict(m.addition.named_buffers())["centre"], rows.mean(0))  # initialised at the mean of z over the first 16 batches
    before = dict(m.addition.named_buffers())["centre"].clone()
    batch = job.stream.batch(1)
    m.train()
    m(batch.tokens[:, :-1])
    m.addition.commit_centre()
    moved = dict(m.addition.named_buffers())["centre"].clone()
    assert not torch.equal(moved, before)  # moves after a training forward
    m.eval()
    with torch.no_grad():
        m(batch.tokens[:, :-1])
    m.addition.commit_centre()
    assert torch.equal(dict(m.addition.named_buffers())["centre"], moved)  # frozen at evaluation
    one = model.build_model("A5-C", 4096, 910041, backbone)
    one.addition.init_centre(torch.zeros(4, 16))
    one.train()
    tokens = batch.tokens[:, :63]
    z_mean = one.addition.window_z(one.embed_block0(tokens), model.SITES).reshape(-1, 16).mean(0).detach()
    one(tokens)
    one.addition.commit_centre()
    assert torch.allclose(dict(one.addition.named_buffers())["centre"], 0.01 * z_mean, atol=1e-6)  # m <- 0.99 m + 0.01 mean(z)


# --- A2 ---------------------------------------------------------------------------------------------------------------------------------------
def test_a2_switch_resets_every_moment_and_counter(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A2", tmp_path, updates=12)
    t = train.Trainer(job, model.build_model("A2", 4096, 910041, backbone), gates.train_probe(job))
    u_pre = int(t.schedule.u_pre or 0)
    assert u_pre == 4 and t.phase == 1
    for u in range(1, u_pre + 1):
        t.step(job.stream.batch(u))
    assert {int(s["step"]) for s in t.optimizers[0].state.values()} == {u_pre} and len(t.optimizers[0].state) == 2
    frozen = {n: p.detach().clone() for n, p in t.model.named_parameters() if n.rsplit(".", 1)[-1] in model.A2_PHASE1_FROZEN}
    assert len(frozen) == 3 and all(torch.equal(p, frozen[n]) for n, p in t.model.named_parameters() if n in frozen)  # nothing moved in phase 1
    t.step(job.stream.batch(u_pre + 1))
    assert t.phase == 2 and len(t.optimizers[0].state) == 5 and {int(s["step"]) for s in t.optimizers[0].state.values()} == {1}  # fresh counters, five parameters
    assert any(not torch.equal(p, frozen[n]) for n, p in t.model.named_parameters() if n in frozen)  # the frozen groups train after the switch


# --- A1-S -------------------------------------------------------------------------------------------------------------------------------------
def test_a1s_targets_are_not_a_function_of_the_fact(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A1-S", tmp_path)
    t = train.Trainer(job, model.build_model("A1-S", 4096, 910041, backbone), gates.train_probe(job))
    f1, f2 = torch.arange(128).reshape(16, 8), torch.arange(128, 256).reshape(16, 8)
    assert torch.equal(t.targets_for(f1, 7), t.targets_for(f2, 7))  # the same update gives the same targets whatever the facts
    assert not torch.equal(t.targets_for(f1, 7), t.targets_for(f1, 8))  # redrawn every update
    tg = t.targets_for(torch.zeros(16, 8, dtype=torch.int64), 3)
    assert len(set(tg.tolist())) > 64  # one fact repeated 128 times still gets (almost) distinct random slots
    assert torch.equal(model.a1s_targets(5, 9, 4096), model.a1s_targets(5, 9, 4096)) and not torch.equal(model.a1s_targets(5, 9, 4096), model.a1s_targets(6, 9, 4096))
    assert int(model.a1s_targets(5, 9, 4096).max()) < 4096 and model.a1s_targets(5, 9, 4096).shape == (128,)
    a1 = train.Trainer(_job(draw, backbone, "A1", tmp_path), model.build_model("A1", 4096, 910041, backbone), gates.train_probe(job))
    inj = a1.injection
    ids = f1 % FACTS
    assert inj is not None and len(set(inj.tolist())) == FACTS and torch.equal(a1.targets_for(ids, 1), inj[ids.reshape(-1)])  # A1's target is a function of the fact
    assert torch.equal(model.target_injection(128, 4096, 3), model.target_injection(128, 4096, 3)) and not torch.equal(model.target_injection(128, 4096, 3), model.target_injection(128, 4096, 4))
    with pytest.raises(ValueError):
        model.target_injection(5000, 4096, 1)


# --- G5 and G6 ----------------------------------------------------------------------------------------------------------------------------------
def test_g6_no_fact_identity_in_any_learned_forward_and_identical_logits(draw, backbone) -> None:  # type: ignore[no-untyped-def]
    tokens = draw.streams["panel_a"].tokens[:4, :63].contiguous()
    lut = torch.arange(10)
    r = model.g6_check(backbone, 4096, 910041, tokens, lut, lut.flip(0))
    assert r["passed"] and set(r["arms"]) == set(core.LEARNED_ARMS)
    for arm, v in r["arms"].items():
        assert v["forward_arguments"] == {"forward": ["tokens"], "select": ["h_pre", "tokens"]} and v["logits_identical_under_changed_tables"], arm
    bad = model.g6_check(backbone, 4096, 910041, tokens, lut, lut)
    assert not bad["passed"] and not bad["fact_tables_differ"]


def test_g5_backbone_identity_and_tamper_detection(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    rows = torch.frombuffer(bytearray(_corpus()), dtype=torch.uint8).to(torch.int64).reshape(-1, 65)[:32, :64].contiguous()
    run = train.run_job(_job(draw, backbone, "A0", tmp_path, updates=4))
    r = model.g5_check(run.model, backbone, rows)
    assert r["passed"] and r["hash_mismatches"] == [] and r["disabled_logits_identical"] and r["tensors"] > 0
    bad = copy.deepcopy(run.model)
    with torch.no_grad():
        next(p for n, p in bad.named_parameters() if n.startswith("backbone.")).add_(1e-3)
    t = model.g5_check(bad, backbone, rows)
    assert not t["passed"] and t["hash_mismatches"]
    assert model.tensor_sha256(torch.zeros(3)) == model.tensor_sha256(torch.zeros(3)) != model.tensor_sha256(torch.ones(3))
