"""Synthetic tests for the P7-B layout construction (ADR-0014 section 4).

Hand-built affinities with known answers, an independent naive reading of the ADR text compared on
random instances, the partitions' registered hashes, the canonical hash, the R = 1 invariants and
the calibration-only interface. No real trace is read.
"""

import json
import random
from pathlib import Path

import pytest
import torch

from arborlm import p7a_core as a_core
from arborlm import p7b_core as core
from arborlm import p7b_layout as L
from arborlm import p7b_sim as sim
from arborlm.p7a_trace import synthetic_trace

LABELS = {
    "flat": "b101-o301-flat-s501",
    "fixed_tree": "b101-o301-fixed_tree-s501",
    "learned_tree": "b101-o301-learned_tree-s501",
}


def rows_of(*queries: list[int]) -> torch.Tensor:
    return torch.tensor(queries, dtype=torch.int64)


# --- affinity
def test_same_query_affinity_hand_case() -> None:
    selected = rows_of(
        [0, 1, 2, 3, 4, 5, 6, 7],
        [0, 1, 8, 9, 10, 11, 12, 13],
        [0, 2, 8, 20, 21, 22, 23, 24],
    )
    adj = L.pair_affinity(selected)
    assert adj[0][1] == 2 and adj[1][0] == 2  # both in queries 0 and 1
    assert adj[0][2] == 2 and adj[0][8] == 2  # (0,2): queries 0, 2; (0,8): queries 1, 2
    assert adj[2][8] == 1 and adj[8][2] == 1  # query 2 only
    assert 9 not in adj[2]  # never together
    assert all(i not in row for i, row in adj.items())  # no self affinity
    assert all(adj[j][i] == v for i, row in adj.items() for j, v in row.items())  # symmetric


def brute_window(selected: torch.Tensor, window: int) -> dict[tuple[int, int], int]:
    rows = selected.tolist()
    out: dict[tuple[int, int], int] = {}
    for start in range(0, len(rows), 64):
        for t in range(64):
            for u in range(max(0, t - window), t + 1):
                for i in rows[start + t]:
                    for j in rows[start + u]:
                        if i != j:
                            out[(i, j)] = out.get((i, j), 0) + 1
                            out[(j, i)] = out.get((j, i), 0) + 1
    return out


def test_windowed_affinity_matches_a_brute_force_reading() -> None:
    generator = random.Random(5)
    selected = rows_of(*[generator.sample(range(30), 8) for _ in range(128)])
    expected = brute_window(selected, 8)
    adj = L.window_affinity(selected, 8)
    flat = {(i, j): v for i, row in adj.items() for j, v in row.items()}
    assert flat == expected


def test_windowed_affinity_window_edges_and_context_boundaries() -> None:
    """Slots a and b: a at query t = 9 of context 0, b at query u = 1 (offset 8: counted) and at
    u = 0 (offset 9: not counted); a also meets c in the next context (not counted)."""
    filler = [100, 101, 102, 103, 104, 105, 106, 107]
    queries = [list(filler) for _ in range(128)]
    queries[9] = [1, 100, 101, 102, 103, 104, 105, 106]  # a = 1 at t = 9
    queries[1] = [2, 100, 101, 102, 103, 104, 105, 106]  # b = 2 at u = 1, offset 8
    queries[0] = [3, 100, 101, 102, 103, 104, 105, 106]  # c = 3 at u = 0, offset 9
    queries[64] = [4, 100, 101, 102, 103, 104, 105, 106]  # d = 4 in the next context
    adj = L.window_affinity(rows_of(*queries), 8)
    assert adj[1][2] == 1 and adj[2][1] == 1  # N[1][2] = 1 (a at t, b at u), A = N + N^T
    assert 3 not in adj.get(1, {})  # offset 9 is outside the window
    assert 4 not in adj.get(1, {}) and 1 not in adj.get(4, {})  # across a context boundary
    # t = u counts: two slots in one query are paired once per ordered direction (N + N^T = 2)
    adj0 = L.window_affinity(rows_of(*[[0, 1, 2, 3, 4, 5, 6, 7]] * 64), 0)
    assert adj0[0][1] == 2 * 64  # window 0: N[0][1] = 64 (t = u), A = N + N^T


# --- greedy fill
def freq_table(values: dict[int, int]) -> list[int]:
    f = [0] * core.SLOTS
    for slot, value in values.items():
        f[slot] = value
    return f


def test_greedy_known_answer_with_zero_score_fallthrough() -> None:
    f = freq_table({0: 10, 1: 9, 2: 8, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3})
    adj = {0: {3: 5}, 3: {0: 5}, 1: {2: 2}, 2: {1: 2}}
    pages = L.greedy_pages(range(8), 2, f, adj)
    assert pages == [[0, 3], [1, 2], [4, 5], [6, 7]]  # 4: no affinity -> hottest unplaced (5)


def test_greedy_tie_rules_at_every_level() -> None:
    # seed ties: equal f -> lowest slot ID
    f = freq_table({5: 7, 3: 7, 9: 7})
    assert L.greedy_pages([5, 3, 9], 1, f, {}) == [[3], [5], [9]]
    # score ties: higher f first, then lowest ID
    f = freq_table({0: 100, 1: 5, 2: 6, 3: 6})
    adj = {0: {1: 3, 2: 3, 3: 3}, 1: {0: 3}, 2: {0: 3}, 3: {0: 3}}
    assert L.greedy_pages([0, 1, 2, 3], 2, f, adj)[0] == [0, 2]  # 2 and 3 tie on f: lowest ID
    f = freq_table({0: 100, 1: 5, 2: 6, 3: 7})
    assert L.greedy_pages([0, 1, 2, 3], 2, f, adj)[0] == [0, 3]  # higher f wins the score tie
    # the score vector accumulates: after taking 1, slot 3 (linked to both) overtakes slot 2
    f = freq_table({0: 100, 1: 90, 2: 80, 3: 70})
    adj = {0: {1: 5, 2: 3, 3: 2}, 1: {0: 5, 3: 4}, 2: {0: 3}, 3: {0: 2, 1: 4}}
    assert L.greedy_pages([0, 1, 2, 3], 3, f, adj)[0] == [0, 1, 3]  # 3: 2 + 4 = 6 > 2: 3


def test_greedy_restricted_to_the_given_set_and_page_sizes() -> None:
    f = freq_table({i: 100 - i for i in range(10)})
    adj = {0: {5: 9}, 5: {0: 9}, 1: {7: 1}, 7: {1: 1}}
    assert L.greedy_pages([0, 1, 7], 2, f, adj) == [[0, 1], [7]]  # 5 is outside the set
    assert [len(p) for p in L.greedy_pages(range(10), 4, f, {})] == [4, 4, 2]


def test_zero_affinity_gives_frequency_packing_for_every_r() -> None:
    generator = random.Random(1)
    f = [generator.randrange(0, 6) for _ in range(core.SLOTS)]  # many ties
    freq_order = sorted(range(core.SLOTS), key=lambda s: (-f[s], s))
    for rows in core.RS:
        pages, info = L.coax_pages(rows, f, {}, refine=True)
        assert L.layout_from_pages(pages) == freq_order
        assert info["swaps"] == 0 and info["converged"]


def test_zero_affinity_bcoax_is_frequency_packing_inside_count_ordered_branches() -> None:
    generator = random.Random(2)
    f = [generator.randrange(0, 6) for _ in range(core.SLOTS)]
    branches = L.branch_groups()
    totals = [sum(f[s] for s in g) for g in branches]
    branch_order = sorted(range(core.BRANCHES), key=lambda g: (-totals[g], g))
    expected = [s for g in branch_order for s in sorted(branches[g], key=lambda s: (-f[s], s))]
    for rows in core.RS:
        pages, _ = L.group_coax_pages(branches, rows, f, {}, refine=True)
        assert L.layout_from_pages(pages) == expected, rows


# --- refinement
def total_within(pages: list[list[int]], adj: L.Adjacency) -> int:
    return L.within_page_affinity(pages, adj)


def test_refinement_makes_the_specific_best_swap_and_keeps_positions() -> None:
    f = freq_table({0: 10, 1: 9, 2: 8, 3: 7})
    adj = {0: {2: 5}, 2: {0: 5}}
    pages, info = L.refine_pages([[0, 1], [2, 3]], adj, f)
    # x = 0 (page 0) may swap with 2 (gain 0, not positive) or with 3 (gain 5): it takes 3's place
    # and 3 takes 0's position: [3, 1] and [2, 0]
    assert pages == [[3, 1], [2, 0]]
    assert info["within_page_affinity_before"] == 0 and info["within_page_affinity_after"] == 5
    assert info["swaps"] == 1 and info["converged"]


def test_refinement_tie_breaking_lowest_page_then_lowest_slot() -> None:
    f = freq_table({i: 100 - i for i in range(8)})
    # x = 0 is linked to slot 2 (page 1) and slot 4 (page 2) with equal weight; every move of 0
    # next to either gains the same amount: the lowest page number wins
    adj = {0: {2: 5, 4: 5}, 2: {0: 5}, 4: {0: 5}}
    pages, _ = L.refine_pages([[0, 1], [2, 3], [4, 5], [6, 7]], adj, f)
    assert 0 in pages[1]  # page 1 (lowest Q), not page 2
    # same page, two equal-gain partners without any affinity: the lowest slot ID is displaced
    f = freq_table({i: 100 - i for i in range(6)})
    adj = {0: {4: 5}, 4: {0: 5}}
    pages, _ = L.refine_pages([[0, 1], [4, 5, 3]], adj, f)
    assert pages == [[3, 1], [4, 5, 0]]  # 3 < 5 and neither has affinity: 3 swaps out


def test_refinement_never_decreases_and_stops_within_twelve_passes() -> None:
    generator = random.Random(3)
    for _ in range(40):
        n = 24
        f = [generator.randrange(1, 9) for _ in range(n)]
        adj: L.Adjacency = {}
        for _e in range(60):
            i, j = generator.sample(range(n), 2)
            w = generator.randrange(1, 6)
            adj.setdefault(i, {})[j] = adj.setdefault(i, {}).get(j, 0) + w
            adj.setdefault(j, {})[i] = adj.setdefault(j, {}).get(i, 0) + w
        pages = L.greedy_pages(range(n), 3, f, {})  # a deliberately poor start: no affinity used
        out, info = L.refine_pages(pages, adj, f)
        assert info["within_page_affinity_after"] >= info["within_page_affinity_before"]
        assert info["passes"] <= core.MAX_PASSES
        assert sorted(s for p in out for s in p) == list(range(n))
        capped, capped_info = L.refine_pages(pages, adj, f, max_passes=1)
        assert capped_info["passes"] == 1


def test_constrained_refinement_stays_inside_the_group() -> None:
    f = freq_table({i: 100 - i for i in range(8)})
    adj = {0: {4: 9}, 4: {0: 9}}  # 0 would love to sit with 4, which belongs to another group
    groups = [0, 0, 0, 0, 1, 1, 1, 1] + [0] * (core.SLOTS - 8)
    pages = [[0, 1], [2, 3], [4, 5], [6, 7]]
    out, info = L.refine_pages(pages, adj, f, group_of=groups)
    assert out == pages and info["swaps"] == 0
    free, _ = L.refine_pages(pages, adj, f)
    assert free != pages  # unconstrained refinement does move it


def naive_greedy(slots: list[int], rows: int, f: list[int], adj: L.Adjacency) -> list[list[int]]:
    """A literal, unoptimized reading of section 4 step 1."""
    unplaced = set(slots)
    pages = []
    while unplaced:
        seed = min(unplaced, key=lambda s: (-f[s], s))
        page = [seed]
        unplaced.remove(seed)
        score = {s: adj.get(seed, {}).get(s, 0) for s in unplaced}
        while len(page) < rows and unplaced:
            nxt = min(unplaced, key=lambda s: (-score[s], -f[s], s))
            page.append(nxt)
            unplaced.remove(nxt)
            for s in unplaced:
                score[s] += adj.get(nxt, {}).get(s, 0)
        pages.append(page)
    return pages


def naive_refine(
    pages: list[list[int]],
    adj: L.Adjacency,
    f: list[int],
    group_of: dict[int, int] | None = None,
) -> list[list[int]]:
    """A literal reading of step 2: every y on every candidate page is tried by recomputing the
    total within-page affinity."""
    pages = [list(p) for p in pages]
    visit = sorted((s for s, row in adj.items() if row), key=lambda s: (-f[s], s))
    for _ in range(core.MAX_PASSES):
        made = False
        for x in visit:
            p = next(i for i, page in enumerate(pages) if x in page)
            base = L.within_page_affinity(pages, adj)
            best = None
            for q, page_q in enumerate(pages):
                if q == p:
                    continue
                if group_of is not None and group_of[page_q[0]] != group_of[x]:
                    continue
                if not any(adj.get(x, {}).get(z, 0) > 0 for z in page_q):
                    continue
                for y in page_q:
                    trial = [list(pg) for pg in pages]
                    ix, iy = trial[p].index(x), trial[q].index(y)
                    trial[p][ix], trial[q][iy] = y, x
                    gain = L.within_page_affinity(trial, adj) - base
                    if gain > 0:
                        key = (gain, -q, -y)
                        if best is None or key > best:
                            best = key
            if best is not None:
                q, y = -best[1], -best[2]
                ix, iy = pages[p].index(x), pages[q].index(y)
                pages[p][ix], pages[q][iy] = y, x
                made = True
        if not made:
            break
    return pages


@pytest.mark.parametrize("constrained", [False, True])
def test_fast_construction_equals_the_naive_literal_reading(constrained: bool) -> None:
    generator = random.Random(11 if constrained else 12)
    for trial in range(60):
        n = generator.choice([12, 16, 24])
        rows = generator.choice([2, 3, 4])
        f = [generator.randrange(0, 6) for _ in range(n)]
        adj: L.Adjacency = {}
        for _e in range(generator.randrange(5, 50)):
            i, j = generator.sample(range(n), 2)
            w = generator.randrange(1, 5)
            adj.setdefault(i, {})[j] = adj.setdefault(i, {}).get(j, 0) + w
            adj.setdefault(j, {})[i] = adj.setdefault(j, {}).get(i, 0) + w
        if constrained:
            group_of = {s: (0 if s < n // 2 else 1) for s in range(n)}
            pages = naive_greedy(list(range(n // 2)), rows, f, adj) + naive_greedy(
                list(range(n // 2, n)), rows, f, adj
            )
            mine, _ = L.refine_pages(pages, adj, f, group_of=[group_of[s] for s in range(n)])
            assert mine == naive_refine(pages, adj, f, group_of), trial
        else:
            pages = naive_greedy(list(range(n)), rows, f, adj)
            assert L.greedy_pages(range(n), rows, f, adj) == pages, trial
            mine, _ = L.refine_pages(pages, adj, f)
            assert mine == naive_refine(pages, adj, f), trial


# --- partitions, canonical hash, layouts
def test_partitions_reproduce_the_registered_hashes_and_are_valid() -> None:
    hashes = L.verify_partitions()
    assert hashes == {str(k): v for k, v in core.PARTITION_SHA256.items()}
    seen = set()
    for seed in core.PARTITION_SEEDS:
        groups = L.partition_groups(seed)
        assert len(groups) == 16 and all(len(g) == 256 for g in groups)
        assert sorted(s for g in groups for s in g) == list(range(core.SLOTS))
        seen.add(frozenset(frozenset(g) for g in groups))
        shuffled = list(range(core.SLOTS))
        random.Random(seed).shuffle(shuffled)
        assert groups[3] == shuffled[768:1024]
    assert len(seen) == 5  # pairwise different


def test_a_partition_with_a_different_hash_stops_the_study(monkeypatch: pytest.MonkeyPatch) -> None:
    tampered = dict(core.PARTITION_SHA256)
    tampered[91603] = "0" * 64
    monkeypatch.setattr(core, "PARTITION_SHA256", tampered)
    with pytest.raises(core.StopError, match="91603"):
        L.verify_partitions()


def test_canonical_hash_ignores_row_order_within_a_page() -> None:
    order = list(range(core.SLOTS))
    other = list(order)
    other[0], other[1] = other[1], other[0]  # same page at R = 2
    assert core.canonical_hash(order, 2) == core.canonical_hash(other, 2)
    other[1], other[2] = other[2], other[1]  # now slots 0 and 2 changed pages
    assert core.canonical_hash(order, 2) != core.canonical_hash(other, 2)
    shuffled = list(range(core.SLOTS))
    random.Random(4).shuffle(shuffled)
    assert core.canonical_hash(shuffled, 1) != core.canonical_hash(shuffled, 2)
    # definition: little-endian 16-bit, pages in order, each page sorted
    import struct

    from arborlm.io import sha256

    expected = sha256(struct.pack("<4h", 0, 1, 2, 3) + struct.pack("<2h", 4, 5))
    assert core.canonical_hash([3, 1, 2, 0, 5, 4], 4) == expected


def build_for(kind: str, seed: int = 21) -> tuple[list[L.BuiltLayout], L.CalibrationTrace]:
    sel, br = synthetic_trace(kind, seed)
    cal = L.CalibrationTrace.declared(sel, br, kind, LABELS[kind])
    built, _ = L.build_layouts(cal, rows_list=(1, 2, 8, 512))
    return built, cal


@pytest.mark.parametrize("kind", ["flat", "fixed_tree"])
def test_registered_layout_set_and_group_contiguity(kind: str) -> None:
    built, _ = build_for(kind)
    names = {b.name for b in built}
    assert names == set(core.all_layouts(kind))
    for b in built:
        assert sorted(b.order) == list(range(core.SLOTS))
    branches, partitions = (
        L.branch_groups(),
        {n: L.partition_groups(s) for n, s in zip(core.L_PCOAX, core.PARTITION_SEEDS, strict=True)},
    )
    for b in built:
        groups = partitions.get(b.name)
        if b.name in (core.L_BCOAX, core.L_BCOAX8, core.L_BCOAXG):
            groups = branches
        if b.name == core.L_BFREQ:
            groups = branches
        if groups is None:
            continue
        position = L.positions_of(b.order)
        for g in groups:
            places = sorted(position[s] for s in g)
            assert places[-1] - places[0] == 255, (b.key(), "group not contiguous")


def test_r1_invariants_across_all_layouts() -> None:
    """Section 4: at R = 1 distinct pages per query, first-touch misses and capacity misses at
    C = 8 are identical across layouts (a page is a single row)."""
    built, _ = build_for("fixed_tree", 33)
    ev, _ = synthetic_trace("fixed_tree", 34)
    reference = None
    for b in built:
        if b.rows not in (None, 1):
            continue
        queries = sim.page_sets(sim.positions_tensor(b.order), 1, ev)
        stats = sim.stream_stats(queries)
        asc8 = sim.cache_counts(queries, 8, stats)
        row = (
            stats["hist"],
            stats["pages_sum"],
            stats["distinct_stream"],
            stats["distinct_first_half"],
            asc8["first_touch_all"],
            asc8["first_touch_warm"],
            asc8["misses_warm"] - asc8["first_touch_warm"],
        )
        if reference is None:
            reference = row
        assert row == reference, b.key()


# --- the calibration-only interface
def test_layout_builder_rejects_an_evaluation_trace() -> None:
    sel, br = synthetic_trace("fixed_tree", 41)
    evaluation = sim.EvaluationTrace(sel, br, "fixed_tree", LABELS["fixed_tree"], "A")
    with pytest.raises(TypeError, match="CalibrationTrace"):
        L.build_layouts(evaluation)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        L.build_layouts(sel)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        L.split_half_layouts(evaluation, 0, [core.L_COAX], 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        L.CalibrationTrace(sel, br, "fixed_tree", "x", source="x", _token=object())


def test_calibration_loader_refuses_evaluation_files(tmp_path: Path) -> None:
    """The identity-manifest loader only ever resolves the calibration roles, and refuses a
    calibration entry that points at an evaluation file."""
    from arborlm.p7b_synth import build_identity

    identity, _ = build_identity(tmp_path, [(101, 301, 501)], 4)
    label = LABELS["flat"]
    L.CalibrationTrace.from_identity(identity, label)  # fine
    data = json.loads((tmp_path / "identity_manifest.json").read_text())
    for entry in data["checkpoints"][0]["files"]:
        if entry["role"] == "calibration.selected":
            entry["relpath"] = entry["relpath"].replace("calib_selected", "eval_selected")
    bad = core.Identity(tmp_path / "x.json", tmp_path, data)
    with pytest.raises(core.TraceIntegrityError, match="not a calibration"):
        L.CalibrationTrace.from_identity(bad, label)


def test_calibration_loader_never_opens_an_evaluation_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm.p7b_synth import build_identity

    identity, _ = build_identity(tmp_path, [(101, 301, 501)], 4)
    opened: list[str] = []
    real = a_core.read_trace

    def spy(directory: Path, prefix: str, record: dict) -> tuple:  # type: ignore[type-arg]
        opened.extend(e["file"] for e in record.values() if e)
        return real(directory, prefix, record)

    monkeypatch.setattr(a_core, "read_trace", spy)
    for label in (LABELS["flat"], LABELS["fixed_tree"]):
        L.CalibrationTrace.from_identity(identity, label)
    assert opened and all(name.startswith("calib_") for name in opened)


def test_layout_file_round_trip_and_hash_table(tmp_path: Path) -> None:
    built, _ = build_for("flat", 51)
    index = L.write_layout_file(tmp_path / "f.bin", built)
    back = L.read_layout_file(tmp_path / "f.bin", index)
    for b in built:
        assert back[b.key()] == b.order
    table = L.hash_table(built, (1, 2, 8, 512))
    assert table[core.layout_key(core.L_FREQ, 8)] == core.canonical_hash(back[core.L_FREQ], 8)
    assert table[core.layout_key(core.L_COAX, 2)] == core.canonical_hash(back["L-COAX|R2"], 2)
