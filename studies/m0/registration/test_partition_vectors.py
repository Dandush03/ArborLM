"""Tests of partition.py: the text's vectors V1 to V8 and property tests on random made-up maps.

The maps of V1 to V8 are made up and name no written lineage; they are copied from
docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/partition_vector_rev4.py (the text gives the
vectors' results and refers to that script for the maps). The expected figures are copied by
hand from
the text and from partition_vector_rev4.out.txt. The registered seed 400004 is used here ONLY
on those
made-up maps (the text's licence for the vectors); property tests use the non-registered seed
987654321 and per-map seeds drawn from a fixed generator. Nothing here reads the map of record.

Run: PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest -p no:cacheprovider
<this file>
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import partition as P  # noqa: E402

REGISTERED = 400004
NONREGISTERED = 987654321
EVALS = P.EVALS


# ---------------------------------------------------------------- the vectors' maps


def _m(spec: str) -> dict[str, bool]:
    return {t.rstrip("!"): not t.endswith("!") for t in spec.split()}


VECTORS = {
    "V1": (
        _m(
            "R1.alpha R1.beta R1.gamma R1.delta! R1.epsilon R1.zeta R2.alpha R2.beta R2.gamma "
            "R2.delta "
            "R2.epsilon M1.alpha M1.beta M1.gamma M1.delta C1.alpha C1.beta C1.gamma C1.delta "
            "C1.epsilon!"
        ),
        [
            ("R1.alpha", "R1.beta"),
            ("C1.alpha", "R2.alpha"),
            ("C1.beta", "R2.beta"),
            ("M1.alpha", "R2.gamma"),
            ("C1.gamma", "M1.beta"),
            ("R1.gamma", "R1.delta"),
            ("C1.epsilon", "R1.epsilon"),
        ],
        [],
    ),
    "V2": (
        _m(
            "R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c C1.a C1.b C1.c C1.d C1.e "
            "C1.f! C1.g!"
        ),
        [
            ("C1.a", "R2.a"),
            ("C1.b", "R2.b"),
            ("C1.c", "R2.c"),
            ("C1.d", "M1.a"),
            ("C1.e", "R1.a"),
            ("C1.f", "C1.g"),
        ],
        [],
    ),
    "V3": (
        _m("R1.e R2.e C1.e! R1.a M1.a C1.a C1.b C1.c C1.d"),
        [("R1.e", "R2.e"), ("C1.e", "R1.e"), ("R1.a", "M1.a")],
        [],
    ),
    "V4": (
        _m("R1.p R1.q R1.r R1.s R2.p! R2.q R2.r M1.p M1.q C1.p C1.q"),
        [("R1.p", "R2.p"), ("R1.q", "R2.p"), ("R2.q", "C1.p"), ("M1.p", "C1.q")],
        [],
    ),
    "V5": (
        _m(
            "C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c "
            "R2.f R2.z0"
        ),
        [
            ("C1.a", "R2.a"),
            ("C1.b", "M1.b"),
            ("C1.c", "R2.c"),
            ("C1.d", "R1.d"),
            ("C1.e", "R1.e"),
            ("C1.f", "R2.f"),
            ("C1.g", "R1.g"),
        ],
        [],
    ),
    "V6": (
        _m(
            "R1.a R1.b R1.c R1.d R1.e R1.f R1.g R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c M1.d "
            "C1.a C1.b C1.c C1.d C1.x!"
        ),
        [("C1.a", "R2.a"), ("M1.a", "R2.b"), ("C1.b", "R2.c")],
        [("R1.a", "C1.x"), ("C1.x", "R1.b"), ("R1.b", "C1.a"), ("R1.c", "R1.d"), ("M1.b", "R2.b")],
    ),
    "V7": (_m("R1.a R1.b R1.c R1.d C1.x!"), [], [("R1.a", "C1.x"), ("C1.x", "R1.b")]),
    "V8": (_m("R1.a R1.b R1.c R1.d R1.e R1.f"), [], [("R1.a", "R1.b"), ("R1.b", "R1.c")]),
}

# Expected, copied from partition_vector_rev4.out.txt. key: (vector, option); option "decided"
# is the
# decided reading (cluster counting, a cluster with no candidate passes a group on).
# value: (cross order or None, part A, part B, no part, {e: (N_e, A, B)})
Z = (0, 0, 0)
EXPECT = {
    ("V1", "decided"): (
        None,
        ["C1.alpha", "C1.beta", "C1.epsilon", "M1.delta", "M1.gamma", "R1.alpha"],
        {"R1": (4, 2, 2), "R2": (5, 2, 3), "M1": (4, 2, 2), "C1": (4, 2, 2)},
    ),
    ("V2", "decided"): (
        None,
        ["C1.a", "C1.b", "M1.c", "R1.b"],
        {"R1": (3, 1, 2), "R2": (5, 2, 3), "M1": (3, 1, 2), "C1": (5, 2, 3)},
    ),
    ("V3", "decided"): (
        None,
        ["C1.c", "C1.d", "C1.e"],
        {"R1": (2, 1, 1), "R2": (1, 1, 0), "M1": (1, 0, 1), "C1": (4, 2, 2)},
    ),
    ("V4", "decided"): (
        None,
        ["C1.p", "M1.q", "R1.s"],
        {"R1": (3, 1, 2), "R2": (2, 1, 1), "M1": (2, 1, 1), "C1": (2, 1, 1)},
    ),
    ("V5", "decided"): (
        None,
        ["C1.a", "C1.c", "C1.f", "M1.z1", "R1.z0"],
        {"R1": (4, 1, 3), "R2": (4, 3, 1), "M1": (3, 1, 2), "C1": (7, 3, 4)},
    ),
    ("V6", "decided"): (
        ["C1.b", "C1.a", "M1.a"],
        ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
        {"R1": (7, 3, 4), "R2": (5, 2, 3), "M1": (4, 2, 2), "C1": (4, 2, 2)},
    ),
    ("V7", "decided"): ([], ["R1.c", "R1.d"], {"R1": (4, 2, 2), "R2": Z, "M1": Z, "C1": Z}),
    ("V8", "decided"): ([], ["R1.d", "R1.e", "R1.f"], {"R1": (6, 3, 3), "R2": Z, "M1": Z, "C1": Z}),
    ("V6", "ignore"): (
        ["C1.b", "C1.a", "M1.a"],
        ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.g", "R2.e"],
        {"R1": (7, 3, 4), "R2": (5, 2, 3), "M1": (4, 2, 2), "C1": (4, 2, 2)},
    ),
    ("V7", "ignore"): ([], ["R1.a", "R1.b"], {"R1": (4, 2, 2), "R2": Z, "M1": Z, "C1": Z}),
    ("V6", "groups"): (
        ["C1.b", "C1.a", "M1.a"],
        ["C1.a", "C1.d", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
        {"R1": (7, 3, 4), "R2": (5, 2, 3), "M1": (4, 1, 3), "C1": (4, 2, 2)},
    ),
    ("V7", "groups"): ([], ["R1.d"], {"R1": (4, 1, 3), "R2": Z, "M1": Z, "C1": Z}),
    ("V8", "groups"): (
        [],
        ["R1.a", "R1.b", "R1.c", "R1.d"],
        {"R1": (6, 4, 2), "R2": Z, "M1": Z, "C1": Z},
    ),
    ("V6", "prefix"): (
        ["C1.b", "C1.a", "M1.a"],
        ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
        {"R1": (7, 3, 4), "R2": (5, 2, 3), "M1": (4, 2, 2), "C1": (4, 2, 2)},
    ),
    ("V8", "prefix"): ([], ["R1.d"], {"R1": (6, 1, 5), "R2": Z, "M1": Z, "C1": Z}),
}
NO_PART = {"V6": ["C1.x"], "V7": ["C1.x"]}  # "no part" lists printed in the out file (all options)


# ---------------------------------------------------------------- readings other than the
# decided one


def _lineage_eval(lineages: dict[str, bool]) -> dict[str, str]:
    return {x: x.split(".", 1)[0] for x in lineages}


def run_option(name: str, option: str, seed: int = REGISTERED) -> tuple[list[str], dict, dict]:
    """Part A, per-evaluation (N_e, A, B) and the result dict, under one of the options of the
    out file.

    "decided": partition.partition. "ignore": a cluster with no candidate lineage is not a node
    of the
    group graph, so a borderline pair that touches it is removed and the decided code is run.
    "groups" (draft 3's item 9) and "prefix" (step 3 stops at the first group that does not fit) are
    computed here from partition.py's building blocks; they are NOT decided.
    """
    lineages, links, borderline = VECTORS[name]
    le = _lineage_eval(lineages)
    cands = [x for x, c in lineages.items() if c]
    if option in ("decided", "ignore"):
        pairs = borderline
        if option == "ignore":
            st0 = P.build_structure(le, links, borderline, cands)
            pairs = [
                (a, b)
                for a, b in borderline
                if st0["has_candidate"][st0["where"][a]] and st0["has_candidate"][st0["where"][b]]
            ]
        res = P.partition(le, links, pairs, cands, seed)
        part_a = sorted(c for c, p in res["cluster_part"].items() if p == "A")
        rep = {
            e: (
                res["counts"][e]["N_e"],
                res["counts"][e]["clusters_A"],
                res["counts"][e]["clusters_B"],
            )
            for e in EVALS
        }
        return part_a, rep, res
    st = P.build_structure(le, links, borderline, cands)
    cross = [g for g in st["groups"] if len(st["group_evals"][g]) >= 2]
    order_x = P.shuffled(cross, P.stream(seed, P.LABEL, "cross"))
    gpart: dict[str, str] = {}
    in_a = in_b = 0
    for i, g in enumerate(order_x):
        to_b = (i % 2 == 0) if option == "groups" else (in_b <= in_a)
        gpart[g] = "B" if to_b else "A"
        if to_b:
            in_b += len(st["groups"][g])
        else:
            in_a += len(st["groups"][g])
    for e in EVALS:
        local = [g for g in st["groups"] if st["group_evals"][g] == [e]]
        order = P.shuffled(local, P.stream(seed, P.LABEL, e))
        if option == "groups":
            n_units = sum(1 for g in st["groups"] if e in st["group_evals"][g])
            a_units = sum(1 for g in cross if e in st["group_evals"][g] and gpart[g] == "A")
            k = min(len(order), max(0, n_units // 2 - a_units))
            for i, g in enumerate(order):
                gpart[g] = "A" if i < k else "B"
        else:  # prefix
            n_e = sum(1 for c in st["clusters"] if e in st["cand_evals"][c])
            a_e = sum(P.w_e(st, g, e) for g in cross if gpart[g] == "A")
            placed, stopped = 0, False
            for g in order:
                fits = a_e + placed + P.w_e(st, g, e) <= n_e // 2
                stopped = stopped or not fits
                if fits and not stopped:
                    gpart[g] = "A"
                    placed += P.w_e(st, g, e)
                else:
                    gpart[g] = "B"
    cpart = {c: gpart[g] for g, cs in st["groups"].items() for c in cs}
    rep = {}
    for e in EVALS:
        cs = [c for c in st["clusters"] if e in st["cand_evals"][c]]
        a = sum(1 for c in cs if cpart[c] == "A")
        rep[e] = (len(cs), a, len(cs) - a)
    return (
        sorted(c for c, p in cpart.items() if p == "A"),
        rep,
        {"order_x": order_x, "cluster_part": cpart, "st": st},
    )


# ---------------------------------------------------------------- V1 to V8


def test_derived_integers_and_the_shuffle_of_the_text() -> None:
    assert P.derive(400004, "cluster-partition", "cross") == 3111564968117111496
    assert P.derive(400004, "cluster-partition", "R1") == 12152681357659760304
    assert P.derive(400004, "cluster-partition", "R2") == 6959284715912682832
    assert P.derive(400004, "cluster-partition", "M1") == 5748257385449400496
    assert P.derive(400004, "cluster-partition", "C1") == 14653439660296977361
    got = P.shuffled(list("abcdefgh"), P.stream(400004, "cluster-partition", "cross"))
    assert got == list("ecbhdfga")  # the text: e, c, b, h, d, f, g, a


def test_shuffle_is_the_loop_of_the_text() -> None:
    """Section 4: for i from len - 1 down to 1, j = _randbelow(i + 1), swap i and j."""
    for label in ("cross", "R1", "R2", "M1", "C1"):
        xs = sorted(f"id{n:02d}" for n in range(23))
        rng = P.stream(400004, "cluster-partition", label)
        ys = list(xs)
        for i in range(len(ys) - 1, 0, -1):
            j = rng._randbelow(i + 1)  # type: ignore[attr-defined]
            ys[i], ys[j] = ys[j], ys[i]
        assert P.shuffled(xs, P.stream(400004, "cluster-partition", label)) == ys


@pytest.mark.parametrize(("name", "option"), sorted(EXPECT))
def test_vector(name: str, option: str) -> None:
    order, exp_a, exp_rep = EXPECT[(name, option)]
    part_a, rep, res = run_option(name, option)
    assert part_a == exp_a, (name, option)
    assert rep == exp_rep, (name, option)
    if option in ("decided", "ignore"):
        assert res["step2"]["order"] == (order if order is not None else res["step2"]["order"])
        part_b = sorted(c for c, p in res["cluster_part"].items() if p == "B")
        lineages = VECTORS[name][0]
        everything = sorted(
            set(
                P.build_structure(
                    _lineage_eval(lineages),
                    VECTORS[name][1],
                    VECTORS[name][2],
                    [x for x, c in lineages.items() if c],
                )["clusters"]
            )
        )
        st_ = P.build_structure(
            _lineage_eval(lineages),
            VECTORS[name][1],
            VECTORS[name][2],
            [x for x, c in lineages.items() if c],
        )
        expected_none = sorted(
            c for c, mem in st_["clusters"].items() if not any(lineages[x] for x in mem)
        )
        assert sorted(res["clusters_without_candidate"]) == expected_none
        if name in NO_PART:  # printed in the out file
            assert expected_none == NO_PART[name]
        assert sorted(part_a + part_b + sorted(res["clusters_without_candidate"])) == everything
    else:
        assert res["order_x"] == order


def test_step2_order_of_the_text_vectors_with_cross_groups() -> None:
    for name in ("V1", "V2", "V3", "V4", "V5"):
        # V1 to V5 have no borderline pair: every group is a cluster, and the three readings agree
        for option in ("prefix", "groups", "ignore"):
            a2, rep2, _ = run_option(name, option)
            assert (a2, rep2) == EXPECT[(name, "decided")][1:], (name, option)


def test_review3_probe_b2_counts() -> None:
    """Out file part 3d: V7 R1 (N, A, B) with 'ignore' / 'pass' under draft 3's counting in
    groups."""
    assert EXPECT[("V7", "ignore")][2]["R1"] == (4, 2, 2)
    assert EXPECT[("V7", "groups")][2]["R1"] == (4, 1, 3)


def test_v8_text_figures() -> None:
    """Section 13 item 20: V8 part A gets 3 of 6 (decided), 1 of 6 (stop at first), 4 of 6
    (groups)."""
    assert [run_option("V8", o)[1]["R1"][1] for o in ("decided", "prefix", "groups")] == [3, 1, 4]


def test_no_candidate_cluster_reports_group_part_beside_it() -> None:
    _, _, res = run_option("V6", "decided")
    nc = res["clusters_without_candidate"]["C1.x"]
    assert nc["tied_by_borderline_pair"] is True
    assert nc["group"] == "C1.a"  # the group {C1.a, R1.a, R1.b}, identity C1.a
    assert nc["group_part"] == "A"
    _, _, res7 = run_option("V7", "decided")
    assert res7["clusters_without_candidate"]["C1.x"]["group_part"] == "B"
    assert res7["cluster_part"]["R1.a"] == res7["cluster_part"]["R1.b"] == "B"


# ---------------------------------------------------------------- random made-up maps


def random_map(
    rng: random.Random,
) -> tuple[dict[str, str], list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    lineage_eval: dict[str, str] = {}
    for e in EVALS:
        for k in range(rng.randint(0, 11)):
            lineage_eval[f"{e}.n{k:02d}"] = e
    ids = sorted(lineage_eval)
    if len(ids) < 2:
        lineage_eval["R1.n00"] = "R1"
        lineage_eval["R2.n00"] = "R2"
        ids = sorted(lineage_eval)

    def pairs(n: int) -> list[tuple[str, str]]:
        out = []
        for _ in range(n):
            a, b = rng.choice(ids), rng.choice(ids)
            out.append((a, b) if a != b else (a, rng.choice(ids)))
        return out

    links = pairs(rng.randint(0, len(ids)))
    borderline = pairs(rng.randint(0, len(ids) // 2)) if rng.random() < 0.7 else []
    cands = [x for x in ids if rng.random() < 0.85]
    return lineage_eval, links, borderline, cands


def bfs_components(nodes: list[str], pairs: list[tuple[str, str]]) -> dict[str, str]:
    """An independent reading: node -> smallest node of its component, by breadth-first search."""
    adj: dict[str, list[str]] = {x: [] for x in nodes}
    for a, b in pairs:
        adj[a].append(b)
        adj[b].append(a)
    rep: dict[str, str] = {}
    for x in sorted(nodes):
        if x in rep:
            continue
        seen = [x]
        stack = [x]
        rep[x] = x
        while stack:
            y = stack.pop()
            for z in adj[y]:
                if z not in rep:
                    rep[z] = x
                    seen.append(z)
                    stack.append(z)
    return rep


N_MAPS = 3000


def test_property_every_rule_on_random_maps() -> None:
    rng = random.Random(20261126)
    checked = {
        "maps": 0,
        "candidate_clusters": 0,
        "evaluation_instances": 0,
        "a_e_over_half_from_step2": 0,
    }
    for _ in range(N_MAPS):
        le, links, borderline, cands = random_map(rng)
        seed = rng.randrange(10**9, 10**10)
        res = P.partition(le, links, borderline, cands, seed)
        rep = bfs_components(sorted(le), links)  # lineage -> cluster id
        cset = set(cands)
        cluster_ids = sorted(set(rep.values()))
        cand_clusters = sorted({rep[x] for x in cset})
        # 1. every candidate cluster gets exactly one part; no other cluster does
        assert sorted(res["cluster_part"]) == cand_clusters
        assert all(p in ("A", "B") for p in res["cluster_part"].values())
        assert sorted(res["clusters_without_candidate"]) == sorted(
            set(cluster_ids) - set(cand_clusters)
        )
        # 2. clusters of one group share a part (groups by an independent search over ALL clusters)
        cpairs = [(rep[a], rep[b]) for a, b in borderline if rep[a] != rep[b]]
        grp = bfs_components(cluster_ids, cpairs)
        by_group: dict[str, set[str]] = {}
        for c in cand_clusters:
            by_group.setdefault(grp[c], set()).add(res["cluster_part"][c])
        assert all(len(s) == 1 for s in by_group.values())
        for c, info in res["clusters_without_candidate"].items():
            tied = any(c in p for p in cpairs)
            assert info["tied_by_borderline_pair"] == tied
            same = {res["cluster_part"][d] for d in cand_clusters if grp[d] == grp[c]}
            assert info["group_part"] == (next(iter(same)) if same else None)
        # 3. clusters linked across evaluations share a part: a link joins two lineages into
        # one cluster,
        #    so the cluster has one entry; check that every candidate lineage of a link has
        # that part
        for a, b in links:
            if a in cset and b in cset:
                assert rep[a] == rep[b]
                assert res["cluster_part"][rep[a]] in ("A", "B")
        # 4. step 3 never takes part A above floor(N_e / 2) by its own doing
        cand_evals = {c: {le[x] for x in cset if rep[x] == c} for c in cand_clusters}
        cross_groups = {
            grp[c]
            for c in cand_clusters
            if len({e for d in cand_clusters if grp[d] == grp[c] for e in cand_evals[d]}) >= 2
        }
        for e in EVALS:
            cs = [c for c in cand_clusters if e in cand_evals[c]]
            n_e = len(cs)
            a_e = sum(1 for c in cs if grp[c] in cross_groups and res["cluster_part"][c] == "A")
            local_a = sum(
                1 for c in cs if grp[c] not in cross_groups and res["cluster_part"][c] == "A"
            )
            assert a_e + local_a <= max(a_e, n_e // 2)
            if a_e > n_e // 2:
                checked["a_e_over_half_from_step2"] += 1
                assert local_a == 0
            c_e = res["counts"][e]
            assert (c_e["N_e"], c_e["clusters_A"] + c_e["clusters_B"]) == (n_e, n_e)
            assert c_e["clusters_A"] == a_e + local_a
            checked["evaluation_instances"] += 1
        checked["maps"] += 1
        checked["candidate_clusters"] += len(cand_clusters)
    assert checked["maps"] == N_MAPS
    print("property counts:", checked)


def _shuffle_inputs(rng: random.Random, le, links, borderline, cands):
    items = list(le.items())
    rng.shuffle(items)
    links2 = [(b, a) if rng.random() < 0.5 else (a, b) for a, b in links]
    rng.shuffle(links2)
    bl2 = [(b, a) if rng.random() < 0.5 else (a, b) for a, b in borderline]
    rng.shuffle(bl2)
    c2 = list(cands)
    rng.shuffle(c2)
    return dict(items), links2, bl2, c2


def test_independent_of_the_order_of_the_input_lists() -> None:
    rng = random.Random(7)
    for _ in range(1500):
        le, links, borderline, cands = random_map(rng)
        a = P.dumps(P.partition(le, links, borderline, cands, NONREGISTERED))
        for _ in range(2):
            le2, links2, bl2, c2 = _shuffle_inputs(rng, le, links, borderline, cands)
            b = P.dumps(P.partition(le2, links2, bl2, c2, NONREGISTERED))
            assert a == b


_CHILD = (
    "import sys, json; sys.path.insert(0, sys.argv[1]); import partition as P; "
    "maps = json.load(sys.stdin); "
    "sys.stdout.buffer.write(b''.join(P.dumps(P.partition(m['le'], m['links'], m['bl'], "
    "m['cands'], "
    "123456789)) for m in maps))"
)


def test_determinism_under_pythonhashseed_0_and_1() -> None:
    rng = random.Random(99)
    maps = []
    for _ in range(60):
        le, links, borderline, cands = random_map(rng)
        maps.append({"le": le, "links": links, "bl": borderline, "cands": cands})
    payload = json.dumps(maps).encode()
    outs = []
    for hs in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": hs, "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run(
            [sys.executable, "-c", _CHILD, str(Path(__file__).resolve().parent)],
            input=payload,
            capture_output=True,
            env=env,
            timeout=120,
            check=True,
        )
        outs.append(r.stdout)
    assert outs[0] == outs[1] and len(outs[0]) > 0
    here = b"".join(
        P.dumps(P.partition(m["le"], m["links"], m["bl"], m["cands"], 123456789)) for m in maps
    )
    assert here == outs[0]
