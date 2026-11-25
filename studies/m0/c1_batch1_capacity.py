# ruff: noqa: E501
"""Capacity of the C1 batch-1 lineages, counted two ways (measurement; the registered gate is the first).

1. Text capacity (the registered G-gen rule, ``lineage_gates.capacity_rows`` at G = 300): distinct normalised question texts, at least 10 times
   the demand (1,800 per core level, 1,000 per reserve level).
2. Capacity up to renaming (stricter, added here): distinct programs after every variable and function name is replaced by its order of first
   appearance. Two items that differ only in variable names count once. The brief asks for at least 2,000 distinct items per level by design;
   this count shows whether that holds without leaning on the 28-name variable pool.

``exhibit`` stops at ``need`` distinct keys or after ``3 * need + 1000`` draws, as the registered gate does.
"""

from __future__ import annotations

import ast
import time
from typing import Any

from studies.m0.c1grammar import render
from studies.m0.core import ALL_LEVELS, Lineage, build_item, stream, text_hash

STAT_SEED = 953601
BUILTIN_NAMES = frozenset({"len", "sum", "max", "min", "abs", "range", "sorted", "str", "print"})


def alpha_key(src: str) -> str:
    """The program with its variable, parameter and function names replaced by v0, v1, ... in order of first appearance."""
    tree = ast.parse(src)
    mapping: dict[str, str] = {}

    class Rename(ast.NodeTransformer):
        def name(self, n: str) -> str:
            return n if n in BUILTIN_NAMES else mapping.setdefault(n, f"v{len(mapping)}")

        def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
            node.id = self.name(node.id)
            return node

        def visit_arg(self, node: ast.arg) -> ast.AST:
            node.arg = self.name(node.arg)
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
            node.name = self.name(node.name)
            self.generic_visit(node)
            return node

    # first appearance must follow source order, so visit in order (NodeTransformer visits fields in order)
    return ast.dump(Rename().visit(tree), annotate_fields=False)


def exhibit_alpha(lin: Lineage, level: int, need: int) -> tuple[int, int, int]:
    """(distinct up to renaming, distinct texts, draws) after at most 3 * need + 1000 draws or when both reach ``need``."""
    keys: set[str] = set()
    texts: set[str] = set()
    rng = stream(STAT_SEED, "c1-alpha-capacity", lin.id, str(level))
    draws = 0
    while len(keys) < need and draws < 3 * need + 1000:
        draws += 1
        it = build_item(lin, level, rng, "A", "cap")
        texts.add(text_hash(it.question))
        keys.add(alpha_key(render(it.structured["program"])))
    return len(keys), len(texts), draws


def alpha_rows(lin: Lineage, need: int = 2000) -> list[dict[str, Any]]:
    rows = []
    for lv in ALL_LEVELS:
        t = time.time()
        a, tx, d = exhibit_alpha(lin, lv, need)
        rows.append({"level": lv, "need": need, "distinct_up_to_renaming": a, "distinct_texts_in_same_draws": tx, "draws": d, "passed": a >= need, "seconds": round(time.time() - t, 2)})
    return rows
