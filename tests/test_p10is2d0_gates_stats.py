# ruff: noqa: E501
"""P10-I-S2-D0 (ADR-0035 sections 4, 5.2, 8): the identities of the gate list on synthetic stores (passing and deliberately broken), the read statistics, and the no-write guarantees."""

import importlib
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import torch

from studies.p10s2 import core
from studies.p10s2.memory import CodeBook, MemoryArm, SparseStore

WIDTH = 5


def _m(name: str) -> ModuleType:
    return importlib.import_module(f"studies.p10is2d0.{name}")


def trio(seed: int = 0) -> tuple[SparseStore, SparseStore, SparseStore]:
    """M1, M-append at the append point (stage-2 gate exactly 0) and M-append final (stage 2 trained: keys, values, gate moved; stage 1 untouched)."""
    g = torch.Generator().manual_seed(seed)
    m1 = SparseStore.new(WIDTH, 12, g)
    with torch.no_grad():
        m1.values[0].mul_(40)
        m1.gates[0].fill_(1.1)
    at = m1.clone()
    at.append_stage(12, torch.Generator().manual_seed(seed + 100))
    final = at.clone()
    with torch.no_grad():
        final.keys[1].add_(0.01 * torch.randn(12, core.KEY_WIDTH, generator=torch.Generator().manual_seed(7)))
        final.values[1].mul_(40)
        final.gates[1].fill_(0.6)
    return m1, at, final


def qs(n: int = 50) -> torch.Tensor:
    q = torch.randn(n, core.KEY_WIDTH, generator=torch.Generator().manual_seed(3))
    return q / q.norm(dim=-1, keepdim=True)


def test_every_gate_identity_passes_on_an_honest_append_pair() -> None:
    gates = _m("gates")
    m1, at, final = trio()
    rec = gates.identity_gates(m1, at, final, qs())
    assert set(rec) == {"stage1_frozen_at_append", "stage1_frozen_final", "g2_zero_at_append", "a_weights_equal_registered_read_at_append", "a_weights_equal_registered_read_final", "b1_equals_m1_read_at_append", "b1_equals_m1_read_final", "e1_equals_a_at_append", "a_equals_e1_plus_e2_at_append", "a_equals_e1_plus_e2_final"}
    assert all(v["pass"] for v in rec.values()), rec
    assert all(set(v) == {"pass", "largest_deviation"} for v in rec.values())
    assert rec["b1_equals_m1_read_final"]["largest_deviation"] == 0.0


def test_a_moved_stage_one_key_fails_the_frozen_gate_and_the_b1_gate() -> None:
    gates = _m("gates")
    m1, at, final = trio()
    with torch.no_grad():
        final.keys[0][3, 0] += 1e-3
    rec = gates.identity_gates(m1, at, final, qs())
    assert not rec["stage1_frozen_final"]["pass"]
    assert rec["stage1_frozen_final"]["largest_deviation"] > 0
    assert not rec["b1_equals_m1_read_final"]["pass"]


def test_a_nonzero_append_gate_fails_g2() -> None:
    gates = _m("gates")
    m1, at, final = trio()
    with torch.no_grad():
        at.gates[1].fill_(1e-9)
    rec = gates.identity_gates(m1, at, final, qs())
    assert not rec["g2_zero_at_append"]["pass"]
    assert rec["g2_zero_at_append"]["largest_deviation"] == pytest.approx(1e-9, rel=1e-3)


def test_the_sum_identity_uses_the_stated_tolerance() -> None:
    gates = _m("gates")
    assert gates.SUM_TOLERANCE == 1e-6
    assert gates.within_sum_tolerance(torch.tensor([10.0]), torch.tensor([10.0 + 5e-6])) is True  # 5e-6 <= 1e-6 * max(1, 10)
    assert gates.within_sum_tolerance(torch.tensor([10.0]), torch.tensor([10.0 + 2e-5])) is False
    assert gates.within_sum_tolerance(torch.tensor([0.1]), torch.tensor([0.1 + 2e-6])) is False  # the bound is 1e-6 * max(1, 0.1)


def test_compare_with_registered_demands_exact_scores_and_identical_sequences() -> None:
    gates = _m("gates")
    reg = {"items": [0.5, 0.25, 1.0], "sequences": [[1, 2], [3], [4, 5, 6]]}
    same = {"items": [0.5, 0.25, 1.0], "sequences": [[1, 2], [3], [4, 5, 6]]}
    assert gates.compare_pass(reg, same) == {"pass": True, "largest_deviation": 0.0}
    off = {"items": [0.5, 0.25 + 1e-12, 1.0], "sequences": [[1, 2], [3], [4, 5, 6]]}
    r = gates.compare_pass(reg, off)
    assert r["pass"] is False and r["largest_deviation"] > 0
    seq = {"items": [0.5, 0.25, 1.0], "sequences": [[1, 2], [3], [4, 5, 7]]}
    assert gates.compare_pass(reg, seq)["pass"] is False
    short = {"items": [0.5, 0.25], "sequences": [[1, 2], [3]]}
    assert gates.compare_pass(reg, short)["pass"] is False


def test_read_statistics_on_a_hand_built_store() -> None:
    stats = _m("stats")
    reads = _m("reads")
    # stage 1: 10 rows around direction u0; stage 2: 3 rows closer to the query than any of stage 1 -> displace three stage-1 rows
    g = torch.Generator().manual_seed(0)
    u = torch.zeros(core.KEY_WIDTH)
    u[0] = 1.0
    s = SparseStore.new(WIDTH, 10, g)
    s.append_stage(3, g)
    with torch.no_grad():
        k1 = torch.stack([u + 0.05 * (i + 1) * torch.eye(core.KEY_WIDTH)[1] for i in range(10)])
        s.keys[0].copy_(k1)
        k2 = torch.stack([u + 0.01 * (i + 1) * torch.eye(core.KEY_WIDTH)[2] for i in range(3)])
        s.keys[1].copy_(k2)
        s.gates[0].fill_(1.0)
        s.gates[1].fill_(0.5)
        s.values[0].mul_(50)
        s.values[1].mul_(50)
    q = u.unsqueeze(0)
    view = reads.slot_view(s, q)
    assert int((view.stage[0] == 1).sum()) == 3
    st = stats.per_read_quantities(s, q, 0)
    assert float(st["n_p"][0]) == 5.0
    assert float(st["displaced"][0]) == 3.0
    mass = float((view.weights[0] * (view.stage[0] == 0)).sum())
    assert float(st["mass_p"][0]) == pytest.approx(mass, rel=1e-6)
    bw = torch.softmax(torch.tensor([float(q[0] @ (k / k.norm())) for k in s.keys[0]]).sort(descending=True).values[:8] / core.TEMPERATURE, dim=0)
    assert float(st["displaced_weight"][0]) == pytest.approx(float(bw[5:].sum()), rel=1e-5)
    assert float(st["top_kept"][0]) == 1.0
    assert float(st["rel_a"][0]) > 0
    summ = stats.summarise(torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert summ["n"] == 5 and summ["undefined"] == 0
    assert summ["mean"] == 3.0 and summ["median"] == 3.0
    assert summ["p5"] == pytest.approx(1.2) and summ["p95"] == pytest.approx(4.8)


def test_read_statistics_mark_an_undefined_ratio_not_a_number() -> None:
    stats = _m("stats")
    s = SparseStore.new(WIDTH, 12, torch.Generator().manual_seed(2))  # one stage, gate 0 -> R_b(p) is the zero vector
    s.append_stage(12, torch.Generator().manual_seed(3))
    q = qs(4)
    st = stats.per_read_quantities(s, q, 0)
    summ = stats.summarise(st["rel_a"])
    assert summ["n"] == 0 and summ["undefined"] == 4


def test_fs_manifest_sees_an_added_file_and_a_changed_byte(tmp_path: Path) -> None:
    run = _m("run")
    (tmp_path / "x.txt").write_text("one")
    before = run.fs_manifest(tmp_path)
    assert run.fs_manifest(tmp_path) == before
    (tmp_path / "y.txt").write_text("two")
    assert run.fs_manifest(tmp_path) != before
    (tmp_path / "y.txt").write_text("tw0")
    after_change = run.fs_manifest(tmp_path)
    assert run.manifest_diff(before, after_change) == {"added": ["y.txt"], "removed": [], "changed": []}
    (tmp_path / "x.txt").write_text("ONE")
    assert run.manifest_diff(after_change, run.fs_manifest(tmp_path)) == {"added": [], "removed": [], "changed": ["x.txt"]}


def test_output_directory_inside_the_part_t_run_directory_is_refused(tmp_path: Path) -> None:
    run = _m("run")
    part_t = tmp_path / "partt"
    part_t.mkdir()
    with pytest.raises(run.D0Refused):
        run.require_new_output_dir(part_t / "d0", part_t)
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(run.D0Refused):
        run.require_new_output_dir(existing, part_t)
    fresh = run.require_new_output_dir(tmp_path / "fresh", part_t)
    assert fresh.is_dir()


def test_loading_snapshots_and_reading_writes_nothing_under_the_run_directory(tmp_path: Path) -> None:
    run = _m("run")
    reads = _m("reads")
    from studies.p10s2.world import save_arm

    m1, at, final = trio()
    snaps = tmp_path / "partt" / "snapshots"
    codes = CodeBook(seed=5, vocabulary=2000)
    save_arm(MemoryArm(m1, 4, codes), snaps, "r0/M1/AB")
    save_arm(MemoryArm(at, 4, codes), snaps, "r0/M-append/AB@append")
    save_arm(MemoryArm(final, 4, codes), snaps, "r0/M-append/AB")
    before = run.fs_manifest(tmp_path / "partt")
    world = SimpleNamespace(codes=lambda r: codes)
    arms = run.load_cell(world, 0, "AB", snaps)  # type: ignore[arg-type]
    assert set(arms) == {"M1", "append", "final"}
    q = qs(8)
    for c in reads.CONDITIONS:
        reads.condition_reader(arms["final"].store, c)(q)
    assert run.manifest_diff(before, run.fs_manifest(tmp_path / "partt")) == {"added": [], "removed": [], "changed": []}
    assert json.dumps(arms["M1"].store.stage_rows) == "[12]"
