# ruff: noqa: E501
"""P9 package I4: general-N layouts (studies/p9/layout.py).

Self-check only: not independent review, not Astra validation, not human approval. No local data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm import p7a_core as a_core  # noqa: E402
from arborlm import p7b_layout as frozen  # noqa: E402
from studies.p9 import layout as lay  # noqa: E402
from studies.p9.core import Trace  # noqa: E402


def make_trace(
    selected: torch.Tensor,
    slots: int,
    *,
    stream: str = "calibration",
    cluster: torch.Tensor | None = None,
) -> Trace:
    q = int(selected.shape[0])
    zeros = torch.zeros(q, dtype=torch.int64)
    return Trace(
        "test",
        0,
        stream,
        "answer",
        slots,
        selected.to(torch.int64),
        None,
        zeros,
        zeros,
        zeros,
        zeros - 1 if cluster is None else cluster,
    )


def structured_selected(slots: int, queries: int, seed: int, *, block: int = 32) -> torch.Tensor:
    """Queries whose eight slots lie in one block of ``block`` consecutive-after-permutation slots, so
    co-access has real structure; a little popularity skew on top."""
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(slots, generator=g)
    blocks = perm[: (slots // block) * block].view(-1, block)
    chosen = torch.randint(0, blocks.shape[0], (queries,), generator=g)
    pick = torch.rand(queries, block, generator=g).argsort(dim=1)[:, :8]
    return torch.gather(blocks[chosen], 1, pick)


def all_layouts(trace: Trace, arch: str, **kw: int) -> dict[str, lay.Layout]:
    return lay.build_layouts(trace, (2, 8, 32), arch=arch, seed=7, clusters=4, **kw)


# --- permutation validity at the registered sizes ---------------------------------------------------------------
@pytest.mark.parametrize("slots", [4096, 16384, 65536])
def test_layouts_are_permutations_at_registered_sizes(slots: int) -> None:
    selected = structured_selected(slots, 1500, seed=slots)
    cluster = torch.randint(0, 4, (1500,), generator=torch.Generator().manual_seed(1))
    trace = make_trace(selected, slots, cluster=cluster)
    branches = slots // 256
    layouts = lay.build_layouts(trace, (2, 8, 32), arch="flat", seed=7, clusters=4)
    layouts.update(
        {
            k: v
            for k, v in lay.build_layouts(
                trace,
                (8,),
                arch="learned_tree",
                seed=7,
                clusters=4,
                branches=branches,
                per_branch=256,
            ).items()
            if v.name == "branch_coaccess"
        }
    )
    assert {
        "identity",
        "frequency",
        "oracle_cluster",
        "coaccess@2",
        "coaccess@8",
        "coaccess@32",
    } <= set(layouts)
    assert "branch_coaccess@8" in layouts
    for key, layout in layouts.items():
        assert layout.key() == key
        assert sorted(layout.order.tolist()) == list(range(slots)), key
        assert int(layout.order.max()) == slots - 1  # ids above 32,767 are not truncated
        assert torch.equal(layout.order[layout.positions()], torch.arange(slots))
    groups = [list(range(b * 256, (b + 1) * 256)) for b in range(branches)]
    lay.verify_layout(layouts["branch_coaccess@8"], slots, groups)


def test_tree_layout_set_and_flat_layout_set() -> None:
    selected = structured_selected(4096, 600, seed=3)
    trace = make_trace(selected, 4096)
    flat = all_layouts(trace, "flat")
    tree = all_layouts(trace, "fixed_tree", branches=16, per_branch=256)
    assert not any(k.startswith("branch") for k in flat)
    assert {f"branch_coaccess@{r}" for r in (2, 8, 32)} <= set(tree)
    with pytest.raises(ValueError):
        lay.build_layouts(trace, (8,), arch="learned_tree", seed=1, clusters=1)


# --- calibration only ------------------------------------------------------------------------------------------
def test_require_calibration_refuses_evaluation_streams_and_other_objects() -> None:
    selected = structured_selected(512, 100, seed=1)
    for stream in ("panel_a", "panel_b", "h1", "mixed"):
        bad = make_trace(selected, 512, stream=stream)
        with pytest.raises(ValueError, match="calibration"):
            lay.require_calibration(bad)
        with pytest.raises(ValueError):
            lay.frequency_layout(bad)
        with pytest.raises(ValueError):
            lay.coaccess_layout(bad, 8, seed=0)
        with pytest.raises(ValueError):
            lay.oracle_cluster_layout(bad, 4)
        with pytest.raises(ValueError):
            lay.build_layouts(bad, (8,), arch="flat", seed=0, clusters=4)
    with pytest.raises(TypeError):
        lay.require_calibration(selected)  # type: ignore[arg-type]
    good = make_trace(selected, 512)
    assert lay.require_calibration(good) is good


# --- sparse co-access equals the dense P7-B affinity ---------------------------------------------------------------
@pytest.mark.parametrize("slots,queries", [(64, 80), (300, 400), (4096, 700)])
def test_sparse_coaccess_equals_dense_affinity(slots: int, queries: int) -> None:
    g = torch.Generator().manual_seed(slots)
    selected = (
        torch.rand(queries, slots, generator=g).argsort(dim=1)[:, :8]
        if slots <= 300
        else structured_selected(slots, queries, 5)
    )
    trace = make_trace(selected, slots)
    co = lay.sparse_coaccess(trace)
    assert lay.adjacency(co) == frozen.pair_affinity(selected)
    assert co.frequency.tolist() == torch.bincount(selected.flatten(), minlength=slots).tolist()
    assert bool((co.pairs[:, 0] < co.pairs[:, 1]).all())
    assert (
        int(co.counts.sum()) == queries * 28
    )  # 28 unordered pairs per query of eight distinct slots
    assert co.pairs.shape[0] == co.counts.shape[0]


def test_sparse_coaccess_memory_is_not_quadratic() -> None:
    selected = structured_selected(65536, 3000, seed=9)
    co = lay.sparse_coaccess(make_trace(selected, 65536))
    assert co.pairs.numel() <= 3000 * 28 * 2 and co.slots == 65536


# --- same algorithm as P7-B's layouts at 4,096 slots ---------------------------------------------------------------
@pytest.mark.parametrize("rows", [2, 8, 32])
def test_coaccess_layout_equals_p7b_lcoax_at_4096(rows: int) -> None:
    selected = structured_selected(4096, 2500, seed=11)
    trace = make_trace(selected, 4096)
    mine = lay.coaccess_layout(trace, rows, seed=0)
    counts = torch.bincount(selected.flatten(), minlength=4096).tolist()
    adj = frozen.pair_affinity(selected)
    pages, info = frozen.coax_pages(rows, counts, adj, refine=True)
    assert mine.order.tolist() == frozen.layout_from_pages(pages)
    assert mine.info["swaps"] == info["swaps"] and mine.info["passes"] == info["passes"]
    assert info["swaps"] > 0  # the refinement step was actually exercised


@pytest.mark.parametrize("rows", [2, 8])
def test_branch_layout_equals_p7b_lbcoax_at_4096(rows: int) -> None:
    selected = structured_selected(4096, 2500, seed=12)
    trace = make_trace(selected, 4096)
    mine = lay.branch_coaccess_layout(trace, rows, branches=16, per_branch=256, seed=0)
    counts = torch.bincount(selected.flatten(), minlength=4096).tolist()
    pages, _ = frozen.group_coax_pages(
        frozen.branch_groups(), rows, counts, frozen.pair_affinity(selected), refine=True
    )
    assert mine.order.tolist() == frozen.layout_from_pages(pages)


def test_frequency_layout_equals_p7a_lfreq_at_4096() -> None:
    selected = structured_selected(4096, 900, seed=13)
    mine = lay.frequency_layout(make_trace(selected, 4096))
    counts = torch.bincount(selected.flatten(), minlength=4096).tolist()
    positions = a_core.layout_freq(counts)
    expected = [0] * 4096
    for slot, position in enumerate(positions):
        expected[position] = slot
    assert mine.order.tolist() == expected
    # ties by slot id: the unaccessed slots come last in id order
    tail = mine.order[int((torch.tensor(counts) > 0).sum()) :].tolist()
    assert tail == sorted(tail)


def test_coaccess_packs_a_planted_block_into_pages() -> None:
    """Eight-slot queries drawn from fixed blocks of 8: the co-access layout puts each block on one page."""
    slots = 256
    perm = torch.randperm(slots, generator=torch.Generator().manual_seed(2))
    blocks = perm.view(-1, 8)
    selected = blocks[torch.arange(400) % blocks.shape[0]]
    layout = lay.coaccess_layout(make_trace(selected, slots), 8, seed=0)
    pages = layout.positions()[selected] // 8
    assert bool((pages == pages[:, :1]).all())


# --- random partition ----------------------------------------------------------------------------------------------
def test_random_partition_is_seeded_permutation() -> None:
    a, b, c = (lay.random_partition_layout(1024, 8, s) for s in (5, 5, 6))
    assert torch.equal(a.order, b.order) and not torch.equal(a.order, c.order)
    assert a.key() == "random_partition@8" and sorted(a.order.tolist()) == list(range(1024))


# --- oracle cluster layout -----------------------------------------------------------------------------------------
def test_oracle_cluster_layout_majority_ties_and_unaccessed() -> None:
    slots = 16
    # slot 0: cluster 1 (2 accesses) beats cluster 0 (1); slot 1: tie 1-1 between clusters 0 and 2 -> 0;
    # slot 2: only in a query with cluster -1 (ignored) -> never accessed; slot 3: cluster 2.
    selected = torch.tensor(
        [
            [0, 1, 4, 5, 6, 7, 8, 9],  # cluster 0
            [0, 3, 4, 5, 6, 7, 8, 9],  # cluster 1
            [0, 3, 4, 5, 6, 7, 8, 9],  # cluster 1
            [1, 3, 4, 5, 6, 7, 8, 9],  # cluster 2
            [2, 10, 11, 12, 13, 14, 15, 9],  # cluster -1 (ignored)
        ]
    )
    cluster = torch.tensor([0, 1, 1, 2, -1])
    layout = lay.oracle_cluster_layout(make_trace(selected, slots, cluster=cluster), 3)
    lay.verify_layout(layout, slots)
    order = layout.order.tolist()
    # cluster of each slot by majority: 0->1; 1->0 (tie 0/2 -> lowest); 3->1 (2 of 3 accesses); 4..9 -> cluster 1 (3 vs 1 vs 1)
    assert order.index(1) < order.index(0)  # cluster 0 block before cluster 1 block
    assert order.index(0) < order.index(3)  # within cluster 1 by slot id
    assert order[:1] == [1]  # cluster 0 holds only slot 1
    assert order[1 : 1 + 8] == [0, 3, 4, 5, 6, 7, 8, 9]  # cluster 1
    assert order[9:] == [
        2,
        10,
        11,
        12,
        13,
        14,
        15,
    ]  # never accessed (cluster -1 ignored), id order, last
    assert layout.info["unassigned_slots"] == 7
    with pytest.raises(ValueError):
        lay.oracle_cluster_layout(
            make_trace(selected, slots, cluster=torch.tensor([0, 1, 1, 5, -1])), 3
        )


def test_oracle_cluster_layout_keeps_clusters_contiguous_on_planted_sharing() -> None:
    slots = 1024
    g = torch.Generator().manual_seed(4)
    perm = torch.randperm(slots, generator=g)
    clusters = 32
    blocks = perm.view(clusters, 32)
    cluster = torch.arange(600) % clusters
    pick = torch.rand(600, 32, generator=g).argsort(dim=1)[:, :8]
    selected = torch.gather(blocks[cluster], 1, pick)
    layout = lay.oracle_cluster_layout(make_trace(selected, slots, cluster=cluster), clusters)
    pos = layout.positions()
    accessed = set(torch.unique(selected).tolist())
    for c in range(clusters):
        members = [s for s in blocks[c].tolist() if s in accessed]
        places = sorted(int(pos[s]) for s in members)
        assert places[-1] - places[0] + 1 == len(
            members
        )  # each cluster's accessed slots are contiguous
    starts = [
        min(int(pos[s]) for s in blocks[c].tolist() if s in accessed) for c in range(clusters)
    ]
    assert starts == sorted(starts)  # clusters in cluster order


# --- verification and file IO ---------------------------------------------------------------------------------------
def test_verify_layout_rejects_bad_layouts() -> None:
    ok = lay.Layout("x", None, torch.arange(8))
    lay.verify_layout(ok, 8)
    for bad in (
        torch.tensor([0, 1, 2, 3, 4, 5, 6, 6]),
        torch.tensor([0, 1, 2, 3, 4, 5, 6, 8]),
        torch.arange(7),
    ):
        with pytest.raises(lay.LayoutError):
            lay.verify_layout(lay.Layout("x", None, bad), 8)
    with pytest.raises(lay.LayoutError):
        lay.verify_layout(
            lay.Layout("x", None, torch.tensor([0, 4, 1, 5, 2, 6, 3, 7])), 8, [[0, 1, 2, 3]]
        )
    lay.verify_layout(ok, 8, [[0, 1, 2, 3], [4, 5, 6, 7]])


def test_write_and_read_layouts_with_hashes(tmp_path: Path) -> None:
    slots = 65536
    layouts = {
        "identity": lay.identity_layout(slots),
        "random_partition@8": lay.random_partition_layout(slots, 8, 3),
    }
    hashes = lay.write_layouts(tmp_path / "l.int32.bin", layouts)
    assert (tmp_path / "l.int32.bin").stat().st_size == 2 * slots * 4  # 32-bit entries
    back = lay.read_layouts(tmp_path / "l.int32.bin", hashes)
    assert set(back) == set(layouts)
    for key in layouts:
        assert (
            torch.equal(back[key].order, layouts[key].order) and back[key].rows == layouts[key].rows
        )
    assert int(back["identity"].order.max()) == slots - 1
    assert len({*hashes.values()}) == 2
    with pytest.raises(lay.LayoutError):
        lay.read_layouts(tmp_path / "l.int32.bin", {**hashes, "identity": "0" * 64})
    blob = bytearray((tmp_path / "l.int32.bin").read_bytes())
    blob[0] ^= 1
    (tmp_path / "bad.bin").write_bytes(bytes(blob))
    (tmp_path / "bad.bin.index.json").write_bytes(
        (tmp_path / "l.int32.bin.index.json").read_bytes()
    )
    with pytest.raises(lay.LayoutError):
        lay.read_layouts(tmp_path / "bad.bin")


def test_write_layouts_is_deterministic(tmp_path: Path) -> None:
    selected = structured_selected(1024, 400, seed=8)
    layouts = lay.build_layouts(make_trace(selected, 1024), (8,), arch="flat", seed=1, clusters=1)
    h1 = lay.write_layouts(tmp_path / "a.bin", layouts)
    h2 = lay.write_layouts(tmp_path / "b.bin", layouts)
    assert h1 == h2 and (tmp_path / "a.bin").read_bytes() == (tmp_path / "b.bin").read_bytes()
