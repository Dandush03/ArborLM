# ruff: noqa: E501
"""P10-I-S2-D0 (ADR-0035 section 4 and 8.1): tiny synthetic stores with known answers for every counterfactual read and every identity of the gate list. Synthetic stores only; no real snapshot is opened.

Each test imports the package inside its first line, so that before the code existed every test failed at its own line (recorded in studies/p10is2d0/NOTES.md)."""

import importlib
from types import ModuleType

import pytest
import torch

from studies.p10s2 import core
from studies.p10s2.memory import SparseStore

WIDTH = 5
TOP = core.TOP
TEMP = core.TEMPERATURE


def _m(name: str) -> ModuleType:
    return importlib.import_module(f"studies.p10is2d0.{name}")


def make_store(rows1: int = 12, rows2: int = 12, seed: int = 0, gates: tuple[float, float] = (1.3, 0.7), scale: float = 40.0) -> SparseStore:
    g = torch.Generator().manual_seed(seed)
    s = SparseStore.new(WIDTH, rows1, g)
    s.append_stage(rows2, g)
    with torch.no_grad():
        for k in range(2):
            s.values[k].mul_(scale)
            s.gates[k].fill_(gates[k])
    return s


def queries(n: int = 40, seed: int = 1) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    q = torch.randn(n, core.KEY_WIDTH, generator=g)
    return q / q.norm(dim=-1, keepdim=True)


def naive(store: SparseStore, q: torch.Tensor, cond: str, p: int = 0) -> torch.Tensor:
    """Loops straight from the ADR's notation (section 4): a_s, T8(X), sigma(X), G, K = G intersect Sp."""
    keys = torch.cat(list(store.keys))
    vals = torch.cat(list(store.values))
    stage = torch.cat([torch.full((r,), k) for k, r in enumerate(store.stage_rows)])
    gate = [float(g) for g in store.gates]
    out = []
    for qi in q:
        a = [float(qi @ (k / k.norm())) for k in keys]

        def top8(rows: list[int]) -> list[int]:
            return sorted(rows, key=lambda s: (-a[s], s))[:TOP]

        def sigma(rows: list[int]) -> dict[int, float]:
            e = [torch.exp(torch.tensor(a[s] / TEMP, dtype=torch.float64)) for s in rows]
            z = sum(e)
            return {s: float(x / z) for s, x in zip(rows, e, strict=True)}

        allrows = list(range(len(a)))
        G = top8(allrows)
        sp = [s for s in allrows if int(stage[s]) == p]
        r = torch.zeros(WIDTH, dtype=torch.float64)
        if cond == "a":
            w = sigma(G)
            for s in G:
                r += w[s] * gate[int(stage[s])] * vals[s].double()
        elif cond == "b":
            T = top8(sp)
            w = sigma(T)
            for s in T:
                r += w[s] * gate[p] * vals[s].double()
        elif cond == "d":
            K = [s for s in G if int(stage[s]) == p]
            if K:
                w = sigma(K)
                for s in K:
                    r += w[s] * gate[p] * vals[s].double()
        elif cond == "e":
            w = sigma(G)
            for s in G:
                if int(stage[s]) == p:
                    r += w[s] * gate[p] * vals[s].double()
        elif cond == "g":
            T = top8(sp)
            wb = sigma(T)
            for s in T:
                r += wb[s] * gate[p] * vals[s].double()
            w = sigma(G)
            for s in G:
                if int(stage[s]) != p:
                    r += w[s] * gate[int(stage[s])] * vals[s].double()
        else:
            raise ValueError(cond)
        out.append(r.float())
    return torch.stack(out)


def close(x: torch.Tensor, y: torch.Tensor) -> bool:
    return bool(torch.allclose(x, y, rtol=1e-4, atol=1e-5))


def test_a_is_bit_identical_to_the_registered_read() -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    assert torch.equal(reads.read_a(s, q), s.read(q))


def test_a_matches_the_adr_notation() -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    assert close(reads.read_a(s, q), naive(s, q, "a"))


@pytest.mark.parametrize("p", [0, 1])
def test_b_is_the_unmodified_read_of_stage_p_alone(p: int) -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    alone = SparseStore.from_state({"width": WIDTH, "stage_rows": [s.stage_rows[p]], "keys": [s.keys[p].detach()], "values": [s.values[p].detach()], "gates": [s.gates[p].detach()]})
    assert torch.equal(reads.read_b(s, q, p), alone.read(q))
    assert close(reads.read_b(s, q, p), naive(s, q, "b", p))


def test_b1_on_an_append_store_is_the_first_stage_read_bit_for_bit() -> None:
    reads = _m("reads")
    g = torch.Generator().manual_seed(3)
    m1 = SparseStore.new(WIDTH, 12, g)
    with torch.no_grad():
        m1.gates[0].fill_(0.9)
    appended = m1.clone()
    appended.append_stage(12, torch.Generator().manual_seed(4))
    with torch.no_grad():
        appended.gates[1].fill_(0.4)
    q = queries()
    assert torch.equal(reads.read_b(appended, q, 0), m1.read(q))


def test_c_is_b1_plus_b2() -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    assert torch.equal(reads.read_c(s, q), reads.read_b(s, q, 0) + reads.read_b(s, q, 1))


@pytest.mark.parametrize("p", [0, 1])
def test_d_e_g_match_the_adr_notation(p: int) -> None:
    reads = _m("reads")
    s, q = make_store(seed=5), queries(60, seed=7)
    assert close(reads.read_d(s, q, p), naive(s, q, "d", p))
    assert close(reads.read_e(s, q, p), naive(s, q, "e", p))
    assert close(reads.read_g(s, q, p), naive(s, q, "g", p))


def test_d_is_the_zero_vector_when_the_protected_stage_has_no_row_among_the_eight() -> None:
    reads = _m("reads")
    s = make_store()
    with torch.no_grad():  # every stage-2 key is the negative of stage-1's best-matching direction: stage 1 fills all eight slots for a query along +u
        u = torch.zeros(core.KEY_WIDTH)
        u[0] = 1.0
        s.keys[0].copy_(u + 0.01 * torch.randn(12, core.KEY_WIDTH, generator=torch.Generator().manual_seed(9)))
        s.keys[1].copy_(-u + 0.01 * torch.randn(12, core.KEY_WIDTH, generator=torch.Generator().manual_seed(10)))
    q = u.unsqueeze(0)
    view = reads.slot_view(s, q)
    assert int((view.stage == 1).sum()) == 0
    d2 = reads.read_d(s, q, 1)
    assert torch.equal(d2, torch.zeros_like(d2))
    assert not torch.isnan(d2).any()
    assert torch.equal(reads.read_e(s, q, 1), torch.zeros_like(d2))
    assert float(reads.read_d(s, q, 0).abs().sum()) > 0


def test_d_renormalises_over_the_protected_rows_and_e_does_not() -> None:
    reads = _m("reads")
    s, q = make_store(seed=11), queries(30, seed=12)
    view = reads.slot_view(s, q)
    mixed = ((view.stage == 0).sum(dim=1) > 0) & ((view.stage == 1).sum(dim=1) > 0)
    assert bool(mixed.any()), "the synthetic store must have mixed reads"
    d1, e1 = reads.read_d(s, q, 0), reads.read_e(s, q, 0)
    assert not close(d1[mixed], e1[mixed])
    # softmax mass on the protected rows is 1 under d and m1 < 1 under e
    mass = (view.weights * (view.stage == 0)).sum(dim=1)
    assert bool((mass[mixed] < 1.0).all())


def test_e_sums_to_a_and_e_of_a_zero_gate_stage_is_the_append_point_a() -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    assert float((reads.read_e(s, q, 0) + reads.read_e(s, q, 1) - reads.read_a(s, q)).abs().max()) <= 1e-6 * max(1.0, float(reads.read_a(s, q).abs().max()))
    with torch.no_grad():
        s.gates[1].zero_()
    assert torch.equal(reads.read_e(s, q, 0), reads.read_a(s, q))


def test_g_is_b_p_plus_the_other_stage_part_of_a() -> None:
    reads = _m("reads")
    s, q = make_store(seed=13), queries()
    for p in (0, 1):
        assert torch.equal(reads.read_g(s, q, p), reads.read_b(s, q, p) + reads.read_e(s, q, 1 - p))


def test_ties_go_to_the_lowest_row_index_across_stages() -> None:
    reads = _m("reads")
    s = make_store(rows1=10, rows2=10)
    with torch.no_grad():
        s.keys[1].copy_(s.keys[0])  # stage 2 duplicates stage 1: every cosine ties between row i and row 10 + i
    q = queries(20, seed=21)
    view = reads.slot_view(s, q)
    # in each tied pair the stage-1 row (the lower index) comes first, so the selection is the registered selection
    assert torch.equal(view.order, s.selected_rows(q))
    assert torch.equal(reads.read_a(s, q), s.read(q))
    first_pairs = view.order[0]
    seen: set[int] = set()
    for row in first_pairs.tolist():
        if row >= 10:
            assert row - 10 in seen
        seen.add(row)


def test_condition_reader_covers_every_condition_of_section_4() -> None:
    reads = _m("reads")
    s, q = make_store(), queries()
    assert set(reads.CONDITIONS) == {"a", "b1", "b2", "c", "d1", "d2", "e1", "e2", "g1", "g2"}
    rd = reads.condition_reader(s, "g2")
    assert torch.equal(rd(q), reads.read_g(s, q, 1))
    with pytest.raises(ValueError):
        reads.condition_reader(s, "z")


def test_diag_arm_adds_the_condition_read_at_the_registered_positions() -> None:
    reads = _m("reads")
    from studies.p10s2.memory import CodeBook, MemoryArm

    s = make_store()
    codes = CodeBook(seed=77, vocabulary=2000)
    base = MemoryArm(s, 4, codes)
    arm = reads.DiagArm(s, 4, codes, "a")
    rl = [[(2, "A", 5), (3, "A", 2000), (3, "A", 7)]]
    add0, _ = base.prepare(rl, 1, 6, torch.device("cpu"))
    add1, _ = arm.prepare(rl, 1, 6, torch.device("cpu"))
    assert add0 is not None and add1 is not None and torch.equal(add0, add1)
    arm_b = reads.DiagArm(s, 4, codes, "b1")
    add2, _ = arm_b.prepare(rl, 1, 6, torch.device("cpu"))
    assert add2 is not None and not torch.equal(add0, add2)
    off, _ = arm.prepare([[]], 1, 6, torch.device("cpu"))
    assert off is None  # route "none": nothing applied


def test_diag_arm_refuses_an_ablation() -> None:
    reads = _m("reads")
    from studies.p10s2.memory import Ablation, CodeBook

    arm = reads.DiagArm(make_store(), 4, CodeBook(seed=1, vocabulary=2000), "a")
    with pytest.raises(ValueError):
        arm.prepare([[(1, "A", 1)]], 1, 4, torch.device("cpu"), Ablation("off"))
