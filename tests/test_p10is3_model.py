# ruff: noqa: E501
"""P10IS3 model, read, control, stream and training tests (ADR-0026 sections 3, 16). Tiny models and tens of updates; seeds of the unit tests are in 935001-935999 only. Self-check only."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from arborlm import p4_model  # noqa: E402
from arborlm.p4_config import MEMORY, Cell  # noqa: E402
from arborlm.p4_model import Backbone  # noqa: E402
from arborlm.pilot_model import EPS, TEMP, TOP, Memory, PilotModel, stable_top, tree_candidates  # noqa: E402
from studies.p10i_s3 import core, model  # noqa: E402

T = core.test_seed


def backbone() -> Backbone:
    return Backbone(PilotModel("dense_small", 42))


def data(n: int, k: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(T(900 + k))
    return torch.randint(0, 256, (n, 65), generator=g, dtype=torch.int64)


def test_read_equality_with_memory_forward_bitwise() -> None:
    for variant, arm in (("learned_tree", core.TREE), ("flat", core.FLAT)):
        m = model.build_model(backbone(), arm, T(1))
        assert isinstance(m.addition, Memory) and m.addition.variant == variant
        h = torch.randn(4, 64, 32, generator=torch.Generator().manual_seed(T(2)))
        with torch.no_grad():
            ref, _ = m.addition(h)
            mine, _ = model.memory_read(m.addition, h, None)
            mine2, _ = model.memory_read(m.addition, h, model.Ctl(None))
        assert torch.equal(ref, mine) and torch.equal(ref, mine2)


def test_dense_read_equals_adapter_forward() -> None:
    m = model.build_model(backbone(), core.DENSE, T(1))
    h = torch.randn(4, 64, 32, generator=torch.Generator().manual_seed(T(2)))
    with torch.no_grad():
        assert torch.equal(m.addition(h)[0], model.dense_read(m.addition, h, None))  # type: ignore[misc, operator]


def test_exhaustive_and_prior_off_reads_against_independent_computation() -> None:
    m = model.build_model(backbone(), core.TREE, T(3))
    mem = m.addition
    assert isinstance(mem, Memory)
    h = torch.randn(2, 64, 32, generator=torch.Generator().manual_seed(T(4)))
    with torch.no_grad():
        q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
        routes = (q @ F.normalize(mem.router, dim=-1, eps=EPS).T) / TEMP
        for visit, prior, ctl in ((16, True, model.Ctl("exhaustive", visit=16)), (2, False, model.Ctl("prior_off", visit=2, use_prior=False))):
            w, sel, _, _ = tree_candidates(q, mem.keys, routes, visit=visit, use_prior=prior)
            comb = (w.softmax(-1)[..., None] * mem.values[sel]).sum(-2)
            expect = h + mem.gate.sigmoid() * F.linear(comb.reshape(h.shape), mem.wo)
            got, _ = model.memory_read(mem, h, ctl)
            assert torch.equal(expect, got)
        # visit=16 is exhaustive: it equals a flat top-8 over all keys plus the log prior of each key's branch
        wf, sf, _, _ = tree_candidates(q, mem.keys, routes, visit=16)
        flat = (q @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP + routes.log_softmax(-1).repeat_interleave(256, dim=-1)
        vals, ids = stable_top(flat, TOP)
        assert torch.equal(sf, ids)
        assert torch.allclose(wf, vals, atol=1e-5)


def test_p_used_brute_force_and_p_all_and_joint() -> None:
    values = torch.arange(4096 * 32, dtype=torch.float32).reshape(4096, 32)
    used = [5, 100, 7, 3000, 42]
    out = model.p_used_values(values, used, T(10))
    assert out is not None
    s = sorted(used)
    sigma = [s[i] for i in torch.randperm(len(s), generator=model.seeded(T(10))).tolist()]
    expect = values.clone()
    for t in range(len(sigma)):
        expect[sigma[t]] = values[sigma[(t + 1) % len(sigma)]]
    assert torch.equal(out, expect)
    # slots not in S are untouched; no slot keeps its own value
    assert all(torch.equal(out[i], values[i]) for i in range(4096) if i not in used)
    assert all(not torch.equal(out[i], values[i]) for i in used)
    assert model.p_used_values(values, [9], T(10)) is None  # COLLAPSED
    ids = torch.randperm(4096, generator=model.seeded(T(11)))
    assert torch.equal(model.p_all_values(values, T(11)), torch.stack([values[i] for i in ids.tolist()]))
    keys = torch.randn(4096, 16, generator=model.seeded(T(12)))
    k2, v2 = model.joint_permutation(keys, values, T(13))
    g = model.seeded(T(13))
    ids2 = torch.cat([b * 256 + torch.randperm(256, generator=g) for b in range(16)])
    assert torch.equal(k2, keys[ids2]) and torch.equal(v2, values[ids2])
    assert all(sorted(ids2[b * 256 : (b + 1) * 256].tolist()) == list(range(b * 256, (b + 1) * 256)) for b in range(16))


def test_x_and_x_mean_reads_brute_force() -> None:
    m = model.build_model(backbone(), core.FLAT, T(5))
    mem = m.addition
    assert isinstance(mem, Memory)
    h = torch.randn(8, 64, 32, generator=torch.Generator().manual_seed(T(6)))
    with torch.no_grad():
        q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
        sigma = torch.randperm(512, generator=model.seeded(T(7))).tolist()
        q2 = q.clone()
        for t in range(512):
            q2[sigma[t]] = q[sigma[(t + 1) % 512]]
        scores = (q2 @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP
        w, sel = stable_top(scores, TOP)
        comb = (w.softmax(-1)[..., None] * mem.values[sel]).sum(-2)
        expect = h + mem.gate.sigmoid() * F.linear(comb.reshape(h.shape), mem.wo)
        got, _ = model.memory_read(mem, h, model.Ctl("X", gen=model.seeded(T(7))))
        assert torch.equal(expect, got)
        # X_mean: the read before W_o is the mean over the 512 positions at every position
        w0, s0 = stable_top((q @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP, TOP)
        c0 = (w0.softmax(-1)[..., None] * mem.values[s0]).sum(-2)
        mean = c0.mean(0)
        expect_m = h + mem.gate.sigmoid() * F.linear(mean.expand(512, 32).reshape(h.shape), mem.wo)
        got_m, _ = model.memory_read(mem, h, model.Ctl("X_mean"))
        assert torch.allclose(expect_m, got_m, atol=1e-6)


def test_dense_x_controls_brute_force() -> None:
    m = model.build_model(backbone(), core.DENSE, T(8))
    ad = m.addition
    h = torch.randn(8, 64, 32, generator=torch.Generator().manual_seed(T(9)))
    with torch.no_grad():
        delta = ad.gate.sigmoid() * F.linear(F.gelu(F.linear(h, ad.w1), approximate="none"), ad.w2)  # type: ignore[union-attr, arg-type, operator]
        flat = delta.reshape(-1, 32)
        sigma = torch.randperm(512, generator=model.seeded(T(14))).tolist()
        use = flat.clone()
        for t in range(512):
            use[sigma[t]] = flat[sigma[(t + 1) % 512]]
        assert torch.equal(h + use.reshape(h.shape), model.dense_read(ad, h, model.Ctl("X", gen=model.seeded(T(14)))))  # type: ignore[arg-type]
        got = model.dense_read(ad, h, model.Ctl("X_mean"))  # type: ignore[arg-type]
        assert torch.allclose(got, h + flat.mean(0).expand(512, 32).reshape(h.shape), atol=1e-6)


def test_streams_brute_force() -> None:
    rows = torch.arange(32).reshape(32, 1).expand(32, 65).clone()
    s = model.Stream(rows, T(20), fresh=False)  # a 32-row "epoch" of four updates
    g = model.seeded(T(20))
    perms = [torch.randperm(32, generator=g) for _ in range(3)]
    for k in range(12):
        assert torch.equal(s.indices(k), perms[k // 4][(k % 4) * 8 : (k % 4) * 8 + 8])
    f = model.Stream(rows, T(21), fresh=True)
    p = torch.randperm(32, generator=model.seeded(T(21)))
    for k in range(4):
        assert torch.equal(f.indices(k), p[8 * k : 8 * k + 8])
    with pytest.raises(core.EngineeringStop):
        f.indices(4)  # the pool is exhausted: no chunk is reused in FRESH


@pytest.mark.parametrize("arm", [core.TREE, core.DENSE])
def test_train_step_matches_p4_train_step_bitwise(arm: str) -> None:
    bb = backbone()
    cell = Cell(101, 301, 401, MEMORY if arm == core.TREE else "dense")
    ref = p4_model.FrozenModel(cell, copy.deepcopy(bb))
    ref_opt = p4_model.optimizer_for(ref)
    assert ref_opt is not None
    mine = model.build_model(copy.deepcopy(bb), arm, 401)
    opt = model.make_optimizer(mine, 0.003)
    d = data(24, 1)
    for k in range(3):
        batch = d[8 * k % 24 : 8 * k % 24 + 8]
        p4_model.train_step(ref, ref_opt, batch, k + 1)
        model.train_step(mine, opt, batch, k + 1)
    for (n1, a), (n2, b) in zip(ref.addition.state_dict().items(), mine.addition.state_dict().items(), strict=True):  # type: ignore[union-attr]
        assert n1 == n2 and torch.equal(a, b)


def test_failed_cell_is_a_failed_run_not_an_error(tmp_path: Path) -> None:
    mine = model.build_model(backbone(), core.DENSE, T(30))
    stream = model.Stream(data(32, 2), T(31), fresh=True)
    res = model.train_run(mine, stream, float("inf"), tmp_path, [2], 3, {"t": 1})
    assert res["status"] == "failed_cell" and "non-finite" in res["reason"]


def test_snapshots_roundtrip_and_prefix_identity(tmp_path: Path) -> None:
    """A 4-update run equals the 4-update checkpoint of an 8-update run, bitwise on this machine's platform (the gate asserts it on the platform of record only)."""
    d = data(64, 3)
    ident = {"t": 1}
    a = model.build_model(backbone(), core.FLAT, T(40))
    model.train_run(a, model.Stream(d, T(41), fresh=True), 0.003, tmp_path / "long", [4, 8], 8, ident)
    b = model.build_model(backbone(), core.FLAT, T(40))
    model.train_run(b, model.Stream(d, T(41), fresh=True), 0.003, tmp_path / "short", [4], 4, ident)
    s1 = torch.load(model.snapshot_dir(tmp_path / "long", 4) / "state.pt", weights_only=True)
    s2 = torch.load(model.snapshot_dir(tmp_path / "short", 4) / "state.pt", weights_only=True)
    assert all(torch.equal(s1["addition"][k], s2["addition"][k]) for k in s1["addition"])
    fresh = model.build_model(backbone(), core.FLAT, T(40))
    model.restore_snapshot(tmp_path / "long", fresh, 8, ident)
    assert model.state_digest(fresh) == model.state_digest(a)
    with pytest.raises(ValueError):
        model.restore_snapshot(tmp_path / "long", fresh, 8, {"t": 2})


def test_evaluate_reads_all_keys_disabled_equals_base_and_replay(tmp_path: Path) -> None:
    panel = data(16, 4)
    seeds = core.Seeds("test")
    bb = backbone()
    for arm, n in ((core.TREE, 16), (core.FLAT, 13), (core.DENSE, 8)):
        m = model.build_model(copy.deepcopy(bb), arm, T(50))
        base = model.build_model(copy.deepcopy(bb), core.BASE, 0)
        b = model.evaluate(base, panel, expected_targets=1024)
        res = _eval(m, panel, seeds)
        assert len(res["reads"]) == n - 1  # every read of section 9 but the replay, which the caller makes after a fresh restore
        assert res["reads"]["disabled|0"] == b  # disabled equals BASE bitwise
        assert set(k.split("|")[0] for k in res["reads"]) <= set(core.READS_OF[arm])
        again = _eval(m, panel, seeds)
        assert again["reads"] == res["reads"]  # replay
        # a step-0 memory is the baseline up to float noise: the gate is near zero
        assert abs(res["reads"]["enabled|0"] - b) < 1e-3


def _eval(m: model.S3Model, panel: torch.Tensor, seeds: core.Seeds) -> dict:  # type: ignore[type-arg]
    # evaluate_reads has the registered target count built in through ``evaluate``; tiny panels pass their own
    orig = model.evaluate

    def ev(mm, data, ctl=None, **kw):  # type: ignore[no-untyped-def]
        kw["expected_targets"] = 1024
        return orig(mm, data, ctl, **kw)

    model.evaluate = ev  # type: ignore[assignment]
    try:
        return model.evaluate_reads(m, panel, seeds, 0)
    finally:
        model.evaluate = orig  # type: ignore[assignment]


def test_read_counts_per_arm_match_section_9() -> None:
    assert [len(core.read_list(a)) for a in (core.TREE, core.FLAT, core.DENSE)] == [16, 13, 8]
