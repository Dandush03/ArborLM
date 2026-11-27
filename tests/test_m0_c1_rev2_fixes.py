# ruff: noqa: E501
"""C1 batch 1, revision 2: one failing-first test per audited defect. Each check is a function that returns the problems it finds; the test asserts that the
revised lineage has none AND that the superseded one (kept on file) does, so the test fails on the old code and passes on the new. Self-checked only; the rates
asserted are regression guards for these fixes, not registered thresholds (ruling R-3: measured, not thresholded)."""

from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import pytest

from studies.m0.c1_batch1_capacity import alpha_key
from studies.m0.c1grammar import render, run_isolated
from studies.m0.core import ALL_LEVELS, Lineage, build_item, lineages_of, stream
from studies.m0.lineages_c1_common import load_batch1
from studies.m0.lineages_c1_rev2 import NOT_REGISTERED, PROPOSED, SUPERSEDES, load_rev2
from studies.m0.solvers_c1 import c1_trace

ROOT = Path(__file__).resolve().parents[1]
OLD = {x.id: x for x in load_batch1()}
EXISTING = {x.id: x for x in lineages_of("C1")}
NEW = {x.id: x for x in load_rev2()}
KNOWN_NAME_COLLISION_DEFECT = {"C1.cellular_update"}  # fixed accumulator name 'w' (audit); superseded by cellular_update_r2


def items(lin: Lineage, level: int, n: int, label: str) -> list:
    r = stream(953901, "c1-rev2-tests", label, lin.id, str(level))
    return [build_item(lin, level, r, "A", f"{lin.id}/{label}/{level}/{i}") for i in range(n)]


# ------------------------------------------------------------------------------------------------ 2. no fixed identifier can collide with a drawn one


def fixed_name_collisions(lin: Lineage, per_level: int) -> list[tuple[int, int]]:
    """Differential test. Build each item twice from the same stream: once as written, once with every DRAWN name replaced by 'zz_' + name (a pool no fixed identifier can
    equal). If a fixed identifier equals a drawn one the two programs differ (as programs up to renaming, or in their key)."""
    g = lin.build.__globals__
    orig = g["names"]

    def renamed(r, k):  # type: ignore[no-untyped-def]
        return ["zz_" + x for x in orig(r, k)]

    bad = []
    for lv in ALL_LEVELS:
        for t in range(per_level):
            a = build_item(lin, lv, stream(953902, "collide", lin.id, str(lv), str(t)), "A", "a")
            g["names"] = renamed
            try:
                b = build_item(lin, lv, stream(953902, "collide", lin.id, str(lv), str(t)), "A", "b")
            finally:
                g["names"] = orig
            if alpha_key(render(a.structured["program"])) != alpha_key(render(b.structured["program"])) or a.answer != b.answer:
                bad.append((lv, t))
    return bad


@pytest.mark.parametrize("lid", sorted(OLD))
def test_no_fixed_identifier_collides_with_a_drawn_one_in_any_of_the_25_batch_one_lineages(lid: str) -> None:
    if lid in KNOWN_NAME_COLLISION_DEFECT:
        assert fixed_name_collisions(OLD[lid], 300), "the old cellular_update defect should still be reproducible (it stays on file)"
    else:
        assert fixed_name_collisions(OLD[lid], 50) == []


@pytest.mark.parametrize("lid", sorted(NEW))
def test_no_fixed_identifier_collides_with_a_drawn_one_in_the_revision_two_lineages(lid: str) -> None:
    assert fixed_name_collisions(NEW[lid], 50) == []


def _cellular_expected(src: str) -> set[str]:
    tree = ast.parse(src)
    cells = ast.literal_eval(tree.body[0].value)  # type: ignore[attr-defined]
    rule = ast.literal_eval(tree.body[1].value)  # type: ignore[attr-defined]
    gens = tree.body[2].iter.args[0].value  # type: ignore[attr-defined]
    n = len(cells)
    for _ in range(gens):
        cells = [rule[cells[(i - 1) % n] * 4 + cells[i] * 2 + cells[(i + 1) % n]] for i in range(n)]
    return {str(cells), str(sum(i * v for i, v in enumerate(cells)))}


def test_cellular_update_r2_prints_the_intended_quantity_and_the_four_old_fixtures_did_not() -> None:
    for lv in (1, 6):
        for it in items(NEW["C1.cellular_update_r2"], lv, 400, "cell"):
            assert it.answer in _cellular_expected(render(it.structured["program"])), it.id
    rows = [json.loads(x) for x in (ROOT / "studies/m0/fixtures/c1_batch1/C1.cellular_update.jsonl").read_text().splitlines()]
    wrong = [r["id"] for r in rows if r["answer"] not in _cellular_expected(render(r["structured"]["program"]))]
    assert wrong == ["C1.cellular_update/fixture/1/4", "C1.cellular_update/fixture/1/14", "C1.cellular_update/fixture/1/16", "C1.cellular_update/fixture/6/6"]


# ------------------------------------------------------------------------------------------------ 3. shortcuts by construction


def _turtle_rule_rate(lin: Lineage, levels: tuple[int, ...], n: int) -> float:
    hit = tot = 0
    for lv in levels:
        for it in items(lin, lv, n, "turtle"):
            tree = ast.parse(render(it.structured["program"]))
            lits = [ast.literal_eval(x) for x in ast.walk(tree) if isinstance(x, ast.List) and x.elts and all(isinstance(e, ast.Constant) for e in x.elts)]
            strs = [x.value for x in ast.walk(tree) if isinstance(x, ast.Constant) and isinstance(x.value, str) and len(x.value) > 3]
            guess = str(strs[0].count("F")) if strs else str(sum(v for v in lits[0] if v <= 3))
            hit += guess == it.answer
            tot += 1
    return hit / tot


def test_turtle_walk_r2_has_no_count_of_commands_tell_and_no_distance_shapes() -> None:
    old = _turtle_rule_rate(OLD["C1.turtle_walk"], (1,), 500)
    new = _turtle_rule_rate(NEW["C1.turtle_walk_r2"], (1, 2, 3, 4, 5), 300)
    assert old > 0.4  # the audit's 0.53 'count the F commands' at level 1, kept on file
    assert new < 0.25
    for lv in (1, 4):
        for it in items(NEW["C1.turtle_walk_r2"], lv, 200, "turtle-shape"):
            assert "abs(" not in render(it.structured["program"]), "a distance shape is NOT REGISTERED"
    assert "C1.turtle_walk[manhattan shape]" in NOT_REGISTERED and "C1.turtle_walk[far shape]" in NOT_REGISTERED


def _sumarg_items(lin: Lineage, level: int, n: int) -> list:
    out = []
    for it in items(lin, level, n, "bytecode"):
        src = render(it.structured["program"])
        m = re.search(r"print\((\w+)\)\s*$", src)
        aug = re.search(rf"\b{m.group(1)} \+= (\w+)", src) if m else None
        if aug and re.search(rf"\b{aug.group(1)} = \w+\[\w+ \+ 1\]", src):
            out.append(it)
    return out


def _sum_args_rate(lin: Lineage, levels: tuple[int, ...], n: int) -> float:
    hit = tot = 0
    for lv in levels:
        for it in _sumarg_items(lin, lv, n):
            code = next(ast.literal_eval(x) for x in ast.walk(ast.parse(render(it.structured["program"]))) if isinstance(x, ast.List))
            hit += str(sum(code[1::2])) == it.answer
            tot += 1
    assert tot > 100
    return hit / tot


def test_bytecode_loop_r2_sum_of_all_arguments_is_no_longer_the_key_of_its_shape() -> None:
    assert _sum_args_rate(OLD["C1.bytecode_loop"], (1, 2, 3, 4, 5), 400) > 0.7  # audit: 0.82-0.89
    assert _sum_args_rate(NEW["C1.bytecode_loop_r2"], (1, 2, 3, 4, 5), 400) < 0.35


def test_bytecode_loop_r2_has_exactly_three_skip_pairs_from_level_one_and_the_skip_depends_on_parity() -> None:
    for lv in (1, 2, 3, 4, 5, 6):
        for it in items(NEW["C1.bytecode_loop_r2"], lv, 60, "skips"):
            src = render(it.structured["program"])
            m = re.search(r"if \w+ == (\d+):\n\s+if \w+ % 2 == \w+ % 2:", src)
            assert m, src
            code = next(ast.literal_eval(x) for x in ast.walk(ast.parse(src)) if isinstance(x, ast.List))
            assert code[0::2].count(int(m.group(1))) == 3
    for it in items(NEW["C1.bytecode_loop_r2"], 0, 60, "skips0"):
        assert "% 2 ==" not in render(it.structured["program"])


def test_merge_two_sorted_r2_has_neither_the_partial_list_nor_the_comparison_count() -> None:
    for lv in (1, 3, 5):
        for it in items(NEW["C1.merge_two_sorted_r2"], lv, 150, "merge"):
            src = render(it.structured["program"])
            assert it.answer.isdigit() and "[" not in it.answer
            assert re.search(r"print\(\w+\)\s*$", src)
            assert re.search(r"if \w+ != \d+:", src)  # the source-change counter, not a bare comparison counter
    assert "C1.merge_two_sorted[out shape]" in NOT_REGISTERED and "C1.merge_two_sorted[cmp shape]" in NOT_REGISTERED
    assert any(it.answer.startswith("[") for it in items(OLD["C1.merge_two_sorted"], 3, 200, "merge-old"))


def test_sieve_marking_r2_has_no_count_shape() -> None:
    for lv in (1, 4):
        for it in items(NEW["C1.sieve_marking_r2"], lv, 150, "sieve"):
            assert "print(sum(" not in render(it.structured["program"])
    assert any("print(sum(" in render(it.structured["program"]) for it in items(OLD["C1.sieve_marking"], 1, 100, "sieve-old"))
    assert "C1.sieve_marking[count shape]" in NOT_REGISTERED


def test_majority_vote_scan_r2_has_no_redraw_and_no_candidate_alone_shape() -> None:
    src = inspect.getsource(NEW["C1.majority_vote_scan_r2"].build)
    assert "Retry" not in src and "Counter" not in src
    assert "Retry" in inspect.getsource(OLD["C1.majority_vote_scan"].build)  # the old redraws on a heuristic's outcome (ruling R-1)
    assert "C1.majority_vote_scan[cand shape]" in NOT_REGISTERED


# Retry is kept only where it enforces VALIDITY of a program, never a conditional on a heuristic's outcome (ruling R-1)
RETRY_ALLOWED = {
    "cellular_update_r2": "rule table and start row not constant",
    "fast_power_r2": "base not 0 or 1 modulo m",
    "circle_elimination_r2": "at least four live flags",
    "fast_power_traced": "base not 0 or 1 modulo m",
    "euclid_gcd_traced": "two different numbers; enough rounds for a stated R below the number of rounds",
}


@pytest.mark.parametrize("lid", sorted(NEW))
def test_revision_two_builders_redraw_only_for_validity(lid: str) -> None:
    src = inspect.getsource(NEW[lid].build)
    name = lid.removeprefix("C1.")
    if "Retry" in src:
        assert name in RETRY_ALLOWED, f"{lid} redraws: say why it is validity, not a heuristic"
        assert "most_common" not in src and "Counter" not in src


# ------------------------------------------------------------------------------------------------ 3/6. the recursive split


def test_recursive_calls_is_split_into_fib_shapes_and_the_other_three() -> None:
    pat = re.compile(r"\(\w+ - 2\)")
    for lv in (1, 3, 5):
        assert not any(pat.search(render(it.structured["program"])) for it in items(NEW["C1.recursive_calls_r2"], lv, 100, "rec"))
        fibs = items(NEW["C1.fib_shapes_recursive"], lv, 100, "fib")
        assert all("- 1)" in render(i.structured["program"]) and pat.search(render(i.structured["program"])) for i in fibs)
    assert any(pat.search(render(it.structured["program"])) for it in items(EXISTING_RECURSIVE(), 3, 100, "rec-old"))


def EXISTING_RECURSIVE() -> Lineage:  # noqa: N802
    return OLD["C1.recursive_calls"]


# ------------------------------------------------------------------------------------------------ 7. capacity


def _distinct_in_draws(lin: Lineage, level: int, draws: int) -> int:
    r = stream(953903, "c1-rev2-cap", lin.id, str(level))
    return len({alpha_key(render(build_item(lin, level, r, "A", "c").structured["program"])) for _ in range(draws)})


def test_widened_lineages_reach_the_structural_need_in_3000_draws_and_the_old_ones_did_not() -> None:
    need = 2400  # 10 x ceil(24,000 / 20 lineages per part / 5 levels), see c1_batch1_rev2_capacity
    for lid in ("C1.fast_power_r2", "C1.circle_elimination_r2"):
        assert _distinct_in_draws(NEW[lid], 0, 3000) >= need, lid
    for lv in (0, 3, 6):
        assert _distinct_in_draws(NEW["C1.recursive_calls_r2"], lv, 3000) >= need, lv
    assert _distinct_in_draws(OLD["C1.fast_power"], 0, 3000) < need
    assert _distinct_in_draws(OLD["C1.circle_elimination"], 0, 3000) < need
    assert _distinct_in_draws(OLD["C1.recursive_calls"], 3, 3000) < need


# ------------------------------------------------------------------------------------------------ 4. proposed shapes


def test_proposed_traced_shapes_are_marked_and_extend_five_named_lineages() -> None:
    assert PROPOSED == {f"C1.{n}_traced" for n in ("insertion_sort", "fast_power", "euclid_gcd", "kadane_scan", "bracket_matching")}
    assert PROPOSED.isdisjoint(SUPERSEDES)  # a proposal adds shapes; it supersedes nothing (the formula-answerable shapes stay until the human lead decides)


# ------------------------------------------------------------------------------------------------ 9. keys of every revised lineage


@pytest.mark.parametrize("lid", sorted(NEW))
def test_revision_two_items_agree_with_the_isolated_runner_twice_and_the_second_solver(lid: str) -> None:
    lin = NEW[lid]
    for lv in ALL_LEVELS:
        its = items(lin, lv, 40, "keys")
        srcs = [render(i.structured["program"]) for i in its]
        a, b = run_isolated(srcs), run_isolated(srcs)
        for it, x, y in zip(its, a, b, strict=True):
            assert x["out"] == y["out"] == it.answer == c1_trace(it.structured), it.id
            assert it.answer_type == "line" and it.k is None and set(it.structured) == {"program"}
        assert len({i.question for i in its}) >= 0.9 * len(its)


# ------------------------------------------------------------------------------------------------ 8. documentation errors


def test_the_two_documentation_errors_are_corrected() -> None:
    common = (ROOT / "studies/m0/lineages_c1_common.py").read_text()
    assert "the program contains exactly one print statement. (An earlier docstring also claimed" in common
    for f in ("studies/m0/fixtures/C1_BATCH1_SCHEMA.md", "studies/m0/c1_batch1_build.py"):
        text = (ROOT / f).read_text()
        assert "with at most about 12 nested calls" not in text and "17 measured" in text
