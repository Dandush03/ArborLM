# ruff: noqa: E501
"""P10IS6 model layer: streams over the memory-mapped uint8 table, resume identity, prefix identity, read set, NEG-REF, planted positive (ADR-0031 sections 6.4, 11, 16). Tiny models, synthetic data, test-range seeds. Self-check only."""

import copy

import pytest
import torch

from arborlm.pilot_model import Memory
from studies.p10i_s3.model import p_used_values, train_step
from studies.p10i_s6 import core, model, testing
from studies.p10i_s6.core import DENSE, FLAT

CFG = core.load_config()
SEEDS = core.Seeds("test", CFG)
ROWS = testing.random_rows(200, core.test_seed(1, CFG))
PANEL = testing.random_rows(4, core.test_seed(2, CFG))
N_TARGETS = 4 * 64
IDENT = {"test": "identity"}


def build(arm: str) -> model.S3Model:
    return model.build_model(copy.deepcopy(testing.synthetic_backbone()), arm, SEEDS.init(0))


def stream() -> model.PoolStream:
    return model.PoolStream(ROWS, 0, ROWS.shape[0], SEEDS.stream(0))


def test_uint8_table_stream_equals_the_int64_path_bitwise() -> None:
    """G16: batch = table[rows].long() equals the int64 table indexed the same way; the table is memory-mapped; no chunk is used twice."""
    with testing.scratch("table") as d:
        testing.write_table(d / "t.u8", ROWS)
        table = model.map_table(d / "t.u8", ROWS.shape[0])
        s_u8 = model.PoolStream(table, 0, ROWS.shape[0], SEEDS.stream(0))
        g = torch.Generator().manual_seed(SEEDS.stream(0))
        perm = torch.randperm(ROWS.shape[0], generator=g)  # the s3 path: rows[perm[8k:8k+8]] over the int64 tensor
        for k in range(ROWS.shape[0] // 8):
            assert torch.equal(s_u8.get(k), ROWS[perm[8 * k : 8 * k + 8]])
        seen = torch.cat([s_u8.indices(k) for k in range(ROWS.shape[0] // 8)])
        assert seen.unique().numel() == seen.numel()
        with pytest.raises(core.EngineeringStop):
            s_u8.get(ROWS.shape[0] // 8)  # the pool is spent: never reused
        with pytest.raises(core.EngineeringStop):
            model.map_table(d / "t.u8", ROWS.shape[0] + 1)


def test_pool_slice_offsets() -> None:
    s = model.PoolStream(ROWS, 50, 100, SEEDS.stream(0))
    assert int(s.indices(0).max()) < 100 and torch.equal(s.get(0), ROWS[50 + s.indices(0)])
    with pytest.raises(ValueError):
        model.PoolStream(ROWS, 150, 100, 1)


@pytest.mark.parametrize("arm", [FLAT, DENSE])
def test_resume_identity_and_prefix_identity_bitwise(arm: str) -> None:
    """A run stopped at a rung and resumed from its snapshot (model, optimizer, stream position) equals the uninterrupted run bitwise; a separate short run equals the long run's snapshot (G15 on a tiny scale)."""
    with testing.scratch("resume") as d:
        full = build(arm)
        r_full = model.train_run(full, stream(), 0.01, d / "full", [4, 8, 12], 12, IDENT)
        assert r_full["status"] == "ok"
        part = build(arm)
        r1 = model.train_run(part, stream(), 0.01, d / "part", [4, 8], 8, IDENT)
        resumed = build(arm)
        opt = model.restore_for_resume(d / "part", resumed, 0.01, 8, IDENT)
        r2 = model.train_run(resumed, stream(), 0.01, d / "part", [12], 12, IDENT, start=8, optimizer=opt)
        assert r1["snapshots"]["8"]["sha256"] == r_full["snapshots"]["8"]["sha256"]  # prefix identity: the 8-update snapshot of a run that stops there is the same file as the long run's
        assert model.snapshots_equal(d / "part", 12, d / "full", 12)  # resume identity: model and optimizer state of the resumed run equal the uninterrupted run's, tensor by tensor
        assert model.state_digest(resumed) == model.state_digest(full)
        short = build(arm)
        rs = model.train_run(short, stream(), 0.01, d / "short", [4], 4, IDENT)
        assert rs["snapshots"]["4"]["sha256"] == r_full["snapshots"]["4"]["sha256"] and model.snapshots_equal(d / "short", 4, d / "full", 4)


def test_pause_at_a_rung_snapshot_and_resume() -> None:
    with testing.scratch("pause") as d:
        m = build(FLAT)
        r = model.train_run(m, stream(), 0.01, d, [4, 8], 12, IDENT, pause_check=lambda: "pause requested")
        assert r["status"] == "paused" and r["resume_from"] == 4 and r["updates_done"] == 4
        m2 = build(FLAT)
        opt = model.restore_for_resume(d, m2, 0.01, 4, IDENT)
        r2 = model.train_run(m2, stream(), 0.01, d, [8, 12], 12, IDENT, start=4, optimizer=opt)
        ref = build(FLAT)
        model.train_run(ref, stream(), 0.01, d / "ref", [12], 12, IDENT)
        assert r2["status"] == "ok" and model.state_digest(m2) == model.state_digest(ref)


def test_failed_cell_ends_the_run_and_keeps_snapshots() -> None:
    with testing.scratch("fail") as d:
        m = build(DENSE)
        r = model.train_run(m, stream(), 1e30, d, [1, 2, 3], 6, IDENT)  # a rate this large overflows the parameters
        assert r["status"] in ("failed_cell", "ok")
        if r["status"] == "failed_cell":
            assert "non-finite" in r["reason"] and r["updates_done"] < 6


def test_failed_cell_exception_type_is_the_one_the_code_raises() -> None:
    """G4: the failure of a non-finite training loss is identified by type and message."""
    m = build(FLAT)
    with torch.no_grad():
        m.addition.wo.fill_(float("nan"))  # type: ignore[union-attr]
    opt = model.make_optimizer(m, 0.01)
    with pytest.raises(core.FailedCell, match="non-finite training loss at step 1"):
        train_step(m, opt, ROWS[:8], 1)


@pytest.mark.parametrize("arm", [FLAT, DENSE])
def test_reads_by_mode_disabled_equals_base_and_keys(arm: str) -> None:
    m = build(arm)
    base = model.S3Model(m.backbone, core.BASE, None)
    b = model.evaluate(base, PANEL, expected_targets=N_TARGETS)
    for mode in ("step0", "enabled", "triple", "full"):
        out = model.evaluate_reads(m, PANEL, SEEDS, 0, mode, expected_targets=N_TARGETS)
        want = {f"{r}|{dd}" for r, dd in core.read_list(arm, mode)} - {f"{core.READ_REPLAY}|0"}
        assert set(out["reads"]) == want
        if "disabled|0" in out["reads"]:
            assert out["reads"]["disabled|0"] == b  # bitwise: the addition is bypassed
    full = model.evaluate_reads(m, PANEL, SEEDS, 0, "full", expected_targets=N_TARGETS)
    if arm == FLAT:
        assert full["stats"]["used_slots"] >= 1 and set(r for r in full["reads"] if r.startswith("P_used")) == {f"P_used|{j}" for j in range(4)}
        assert full["reads"]["V_mean|0"] is not None and full["reads"]["X_mean|0"] is not None
    # replay after a fresh restore equals the first read bitwise (in-process: same state, same arithmetic)
    again = model.evaluate_reads(m, PANEL, SEEDS, 0, "enabled", expected_targets=N_TARGETS)
    assert again["reads"]["enabled|0"] == full["reads"]["enabled|0"]


def test_collapsed_cell_gives_no_p_used() -> None:
    m = build(FLAT)
    with torch.no_grad():
        mem = m.addition
        assert isinstance(mem, Memory)
        mem.keys.zero_()
        mem.keys[:, 0] = 1.0  # every key identical: ties go to the smallest slot ids, so the eight lowest slots are the only ones ever selected
        mem.wq.zero_()
        mem.wq[0, 0] = 1.0
    out = model.evaluate_reads(m, PANEL, SEEDS, 0, "full", expected_targets=N_TARGETS)
    assert out["stats"]["used_slots"] >= 2  # eight tied slots are selected, so not collapsed
    # force a collapse by hand: one used slot
    assert p_used_values(m.addition.values, [3], 1) is None  # type: ignore[union-attr]


def test_neg_ref_check_and_planted_positive() -> None:
    m = build(FLAT)
    model.train_run(m, stream(), 0.03, testing.scratch_root() / "negref-unused", [], 8, IDENT)
    res = model.neg_ref_check(m, PANEL, SEEDS, CFG, cell=0, expected_targets=N_TARGETS)
    assert res["passed"] is True and all(res["zero_within_tolerance"].values())
    pp = model.planted_positive(CFG, SEEDS)
    assert pp["passed"] is True and pp["C"] > 0 and pp["P_used"] >= 0.5 * pp["C"] and pp["X_mean"] >= 0.5 * pp["C"]
    # the toy's V_mean keeps the planted gain's zero-mean construction only partly: it is descriptive and no rule reads it
    assert isinstance(pp["V_mean"], float)


def test_v_mean_equals_the_usage_weighted_constant_read() -> None:
    m = build(FLAT)
    out = model.evaluate_reads(m, PANEL, SEEDS, 0, "full", expected_targets=N_TARGETS)
    col = model.Collector()
    model.evaluate(m, PANEL, None, collector=col, expected_targets=N_TARGETS)
    vm = model.neg_ref_values(m.addition.values, col.usage)  # type: ignore[union-attr]
    assert torch.equal(vm[0], vm[100])  # every value row is the same vector
    direct = model.evaluate(m, PANEL, model.Ctl("values", values=vm), expected_targets=N_TARGETS)
    assert out["reads"]["V_mean|0"] == direct


def test_the_ladder_cannot_be_extended() -> None:
    """Decision 1, choice 2(a): no continuation rung. Rung 5 does not exist in the config and no function in the package creates it."""
    with pytest.raises(ValueError):
        core.rung_updates(CFG, 5)
    assert core.rung_updates(CFG, 4) == 262144 and core.rung_updates(CFG, -1) == 8192
    assert int(CFG["ladder"]["rungs"]) == 5 and core.k_max_for_pools(CFG, 5_000_000, 2_500_000) == 4  # the ceiling rule never raises k_max above 4
    assert core.k_max_for_pools(CFG, 5_000_000, 600_000) == 2  # a short calibration pool cuts the ladder (section 6.5)
    with pytest.raises(core.EngineeringStop, match="CORPUS TOO SMALL"):
        core.k_max_for_pools(CFG, 5_000_000, 400_000)
