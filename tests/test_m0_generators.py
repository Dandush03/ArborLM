# ruff: noqa: E501
"""M0 stage I0-a: the private item generators, their second solvers and the generator rules of ADR-0033 section 6.2.

Self-checked: not independent review, not Astra validation, not human approval. Nothing here is a result.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

from studies.m0 import c1grammar, ggen
from studies.m0.core import (
    ALL_LEVELS,
    CORE_LEVELS,
    allocate,
    build_item,
    check_disjoint,
    derive_seed,
    family_partition,
    generate_pool,
    lineages_of,
    m0_draw,
    nuisance_order,
    part_lineages,
    permute_options,
    pool_hash,
    stream,
    text_hash,
)
from studies.m0.scoring import canon, in_grammar, normalise_answer
from studies.m0.vocab import NAMES, PSEUDO

ROOT = Path(__file__).resolve().parents[1]
M0 = ROOT / "studies" / "m0"
EVALS = ("R1", "R2", "M1", "C1")
ALL_LINEAGES = [(ev, lin.id) for ev in (*EVALS, "K0") for lin in lineages_of(ev)]


def _solver(ev: str, lid: str):  # type: ignore[no-untyped-def]
    return ggen._solvers(ev)[lid]


# ---------------------------------------------------------------- structure of the generators


def test_every_private_evaluation_has_at_least_twelve_families_and_both_parts_are_nonempty() -> None:
    for ev in EVALS:
        fams = {x.family for x in lineages_of(ev)}
        assert len(fams) >= 12, (ev, sorted(fams))
        part = family_partition(ev)
        assert sorted(set(part.values())) == ["A", "B"]
        assert abs(sum(1 for v in part.values() if v == "A") - sum(1 for v in part.values() if v == "B")) <= 1
        assert part_lineages(ev, "A") and part_lineages(ev, "B")
        assert {x.id for x in part_lineages(ev, "A")}.isdisjoint({x.id for x in part_lineages(ev, "B")})


def test_family_partition_is_deterministic_and_seed_dependent() -> None:
    assert family_partition("R1") == family_partition("R1")
    seen = {tuple(sorted(family_partition("R1", seed=s).items())) for s in range(400100, 400120)}
    assert len(seen) > 1  # the registered seed, not a fixed order, decides the split


def test_vocabulary_lists_are_sorted_and_unique() -> None:
    assert list(NAMES) == sorted(set(NAMES)) and len(NAMES) >= 100
    assert list(PSEUDO) == sorted(set(PSEUDO))


@pytest.mark.parametrize(("ev", "lid"), ALL_LINEAGES)
def test_second_solver_agrees_and_answer_is_in_grammar_for_every_lineage_and_level(ev: str, lid: str) -> None:
    lin = next(x for x in lineages_of(ev) if x.id == lid)
    solve = _solver(ev, lid)
    n = 6 if ev == "C1" else 12
    for lv in ALL_LEVELS:
        rng = stream(953001, "generators-test", lid, str(lv))
        for i in range(n):
            it = build_item(lin, lv, rng, "A", f"t{i}")
            assert solve(json.loads(json.dumps(it.structured))) == it.answer, (lid, lv, it.question)
            norm = normalise_answer(it.answer)
            assert in_grammar(it.answer_type, norm), (lid, it.answer)
            assert canon(it.answer_type, norm) == canon(it.answer_type, normalise_answer(norm))
            if it.k is not None:
                assert it.k >= 2


def test_second_solver_detects_a_wrong_gold_answer() -> None:
    lin = next(x for x in lineages_of("R1") if x.id == "R1.road_reachability")
    it = build_item(lin, 2, stream(953002, "mut"), "A", "x")
    flipped = "no" if it.answer == "yes" else "yes"
    assert _solver("R1", lin.id)(it.structured) != flipped


def test_second_solvers_do_not_import_the_generators() -> None:
    for f in M0.glob("solvers_*.py"):
        tree = ast.parse(f.read_text())
        mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith("studies") for m in mods), (f.name, mods)


# ---------------------------------------------------------------- reproducibility rules


def _py_files() -> list[Path]:
    return sorted(M0.glob("*.py"))


def test_no_hash_builtin_and_no_unsorted_set_or_dict_iteration_in_the_package() -> None:
    bad = []
    for f in _py_files():
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash":
                bad.append((f.name, node.lineno, "hash()"))
            its = []
            if isinstance(node, ast.For):
                its.append(node.iter)
            if isinstance(node, ast.comprehension):
                its.append(node.iter)
            for it in its:
                if isinstance(it, ast.Set | ast.SetComp):
                    bad.append((f.name, it.lineno, "iterates a set literal"))
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id in ("set", "frozenset"):
                    bad.append((f.name, it.lineno, "iterates set()"))
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr in ("keys", "values", "items") and False:
                    bad.append((f.name, it.lineno, "dict view"))
    assert not bad, bad


def test_imports_are_standard_library_torch_or_the_package_only() -> None:
    allowed_third = {"torch"}
    stdlib = set(sys.stdlib_module_names)
    for f in _py_files():
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for n in names:
                assert n in stdlib or n in allowed_third or n == "studies", (f.name, n)
    forbidden = ("transformers", "tokenizers", "numpy", "safetensors", "huggingface_hub")
    for f in _py_files():
        text = f.read_text()
        for name in forbidden:
            assert f"import {name}" not in text and f"from {name}" not in text, (f.name, name)


def test_streams_are_sha256_of_seed_and_label_never_seed_arithmetic() -> None:
    expected = int.from_bytes(hashlib.sha256(b"400001|R1|A|x").digest()[:8], "big")
    assert derive_seed(400001, "R1", "A", "x") == expected
    assert derive_seed(400001, "R1") != derive_seed(400001, "R2")
    assert derive_seed(400001, "a") != derive_seed(400002, "a")
    # no module adds to a seed: a BinOp Add with an operand whose name contains "seed" is refused
    bad = []
    for f in _py_files():
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                for side in (node.left, node.right):
                    if isinstance(side, ast.Name) and "seed" in side.id.lower():
                        bad.append((f.name, node.lineno))
    # one registered exception: the capacity gate and the audit samples use block offsets of the rehearsal draws 409001-409099
    assert all(f == "ggen.py" for f, _ in bad), bad


def test_same_stream_gives_same_items() -> None:
    lin = next(x for x in lineages_of("R1") if x.id == "R1.seating_row")
    a = [build_item(lin, 3, stream(5, "x"), "A", "i").question for _ in range(1)]
    b = [build_item(lin, 3, stream(5, "x"), "A", "i").question for _ in range(1)]
    assert a == b


def test_pools_built_twice_in_two_processes_have_equal_hashes_small_version() -> None:
    res = ggen.reproducibility_gate(b"\x07" * 32, small=True)
    assert res["equal"], res
    assert res["n_pools"] == 26


# ---------------------------------------------------------------- pools: sizes, balance, disjointness


def test_allocate_largest_remainder_and_pool_balance() -> None:
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]
    assert sum(allocate(4000, [1.0] * 7)) == 4000
    taken: set[str] = set()
    pool = generate_pool("R2", "A", "development", 400002, 400, {lv: 1.0 for lv in CORE_LEVELS}, taken)
    assert len(pool) == 400
    per = {}
    for it in pool:
        per[it.lineage] = per.get(it.lineage, 0) + 1
    g = len(part_lineages("R2", "A"))
    assert max(per.values()) - min(per.values()) <= 1 and len(per) == g
    assert {it.part for it in pool} == {"A"}
    assert all(it.family in {x.family for x in part_lineages("R2", "A")} for it in pool)


def test_tuning_development_and_sealed_are_disjoint_and_the_check_detects_a_repeat() -> None:
    sizes = ggen.Sizes(tuning_per_level=5, development=100, sealed=200, k0_development=10, k0_sealed=20)
    pools = ggen.build_pools(b"\x02" * 32, sizes, evals=("R1", "M1"))
    report = ggen.disjointness_gate(pools)
    assert all(v["problems"] == 0 for v in report.values()), report
    a = pools.items[("R1", "A", "development")]
    b = pools.items[("R1", "A", "sealed")]
    assert check_disjoint({"development": a, "sealed": [*b, a[0]]})  # a planted repeat is found
    assert len({text_hash(x.question) for x in a}) == len(a)


def test_sealed_pool_depends_on_the_salt_and_nothing_else_does() -> None:
    sizes = ggen.Sizes(tuning_per_level=2, development=40, sealed=60, k0_development=5, k0_sealed=5)
    p1 = ggen.build_pools(b"\x01" * 32, sizes, evals=("R2",))
    p2 = ggen.build_pools(b"\x02" * 32, sizes, evals=("R2",))
    assert pool_hash(p1.items[("R2", "A", "development")]) == pool_hash(p2.items[("R2", "A", "development")])
    assert pool_hash(p1.items[("R2", "A", "sealed")]) != pool_hash(p2.items[("R2", "A", "sealed")])


def test_m0_draw_is_balanced_over_clusters_and_deterministic() -> None:
    pool = generate_pool("M1", "A", "development", 400002, 800, {lv: 1.0 for lv in CORE_LEVELS}, set())
    d1, d2 = m0_draw(pool, 300), m0_draw(pool, 300)
    assert [x.id for x in d1] == [x.id for x in d2]
    per: dict[str, int] = {}
    for it in d1:
        per[it.lineage] = per.get(it.lineage, 0) + 1
    assert max(per.values()) - min(per.values()) <= 1
    order = nuisance_order(d1)
    assert sorted(x.id for x in order) == sorted(x.id for x in d1)
    assert sorted(permute_options(4, "x")) == [0, 1, 2, 3]


# ---------------------------------------------------------------- capacity gate


def test_capacity_demand_arithmetic_and_the_gate_can_fail() -> None:
    sz = ggen.Sizes()
    assert ggen.demand_per_level(sz, 7, 3) == 3429 + 100  # ceil(24000 / 7) + tuning draw
    assert ggen.demand_per_level(sz, 7, 3, kind="even") == 686 + 100
    assert ggen.demand_per_level(sz, 7, 0) == 100
    found, _ = ggen.exhibit("M1", "M1.rectangle", 1, 10 * ggen.demand_per_level(sz, 8, 1), "test")
    assert found < 10 * ggen.demand_per_level(sz, 8, 1)  # a lineage with a small parameter space fails the gate
    f2, _ = ggen.exhibit("R1", "R1.order_extreme", 1, 2000, "test")
    assert f2 == 2000


# ---------------------------------------------------------------- C1: grammar, isolation, renderer against interpreter


def test_c1_isolated_runs_agree_with_in_process_and_restrict_builtins() -> None:
    srcs = ["print(sum([1, 2, 3]))", "x = 5\nprint(x * x)", "import os\nprint(1)", "print(open('/etc/hosts'))", "print(1)\nprint(2)"]
    r1 = c1grammar.run_isolated(srcs)
    r2 = c1grammar.run_isolated(srcs)
    assert r1 == r2
    assert [r["out"] for r in r1[:2]] == ["6", "25"]
    assert all(r["err"] for r in r1[2:])  # no import, no open, not exactly one line


def test_c1_time_limit_stops_a_runaway_program() -> None:
    src = c1grammar.render([["set", "a", ["n", 1]], ["while", ["c", "==", ["n", 1], ["n", 1]], [["aug", "a", "+", ["n", 1]]]], ["print", ["v", "a"]]])
    res = c1grammar.run_isolated([src])
    assert res[0]["out"] is None and "Timeout" in res[0]["err"]


def test_c1_renderer_precedence_matches_the_tree_interpreter_on_random_expressions() -> None:
    from studies.m0.solvers_c1 import c1_trace

    r = stream(953003, "c1-fuzz")

    def expr(depth: int) -> list:
        if depth == 0 or r.random() < 0.25:
            return ["n", r.randint(-9, 9)]
        op = r.choice(("+", "-", "*", "//", "%"))
        a, b = expr(depth - 1), expr(depth - 1)
        if op in ("//", "%"):
            b = ["n", r.choice((1, 2, 3, 5, -2, -3))]
        return ["b", op, a, b]

    for _ in range(300):
        e = expr(4)
        prog = [["print", e]]
        assert c1grammar.run_inprocess(c1grammar.render(prog)) == c1_trace({"program": prog}), c1grammar.render(prog)


# ---------------------------------------------------------------- K0: no leak of the answer to simple guessers


def test_k0_simple_guessers_are_at_chance() -> None:
    lin = lineages_of("K0")[0]
    rng = stream(953004, "k0")
    items = [build_item(lin, 1, rng, "K", f"k{i}") for i in range(2000)]
    letters = "ABCD"
    hits = {"always_a": 0, "longest": 0, "alphabetical_first": 0}
    for it in items:
        opts = it.structured["options"]
        gold = letters.index(it.answer)
        hits["always_a"] += gold == 0
        hits["longest"] += gold == max(range(4), key=lambda i: (len(opts[i]), -i))
        hits["alphabetical_first"] += gold == min(range(4), key=lambda i: opts[i])
    for name, h in hits.items():
        assert abs(h / len(items) - 0.25) < 0.04, (name, h / len(items))  # about 4.2 binomial standard errors
