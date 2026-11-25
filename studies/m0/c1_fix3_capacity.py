# ruff: noqa: E501
"""Structural capacity of the C1 lineages of the current set (after fix round 3), at the G actually written, under the three readings of the brief (measurement; no new threshold).

Demand (rulings R-10, R-11): per cluster and level 10 * (ceil(4000 / G) + ceil(20000 / G) + 100); at G = 12 that is 10 * (334 + 1667 + 100) = 21,010, the same on every level
including the reserve levels 0 and 6. (The brief says 'about 20,940'; the formula as written gives 21,010 and is what is used.)

Readings:
  (a) identifiers renamed (``c1_batch1_capacity.alpha_key``: variable, parameter and function names replaced by order of first appearance), counted per CLUSTER (the union of the
      programs of the cluster's lineages);
  (b) the same count per LINEAGE, as ``core.generate_pool`` allocates (it allocates per lineage);
  (c) also literals that do not change control flow discounted: every int and str constant is blanked and the sequence of source lines the program executes (``sys.settrace``) is part of
      the key. Reported only for the lineages named in ``--k2`` (the brief asks for cellular_update and counter_list); K2 classes are unions of K1 classes, so K2 is evaluated once per new K1 class.

Draws stop at the demand or at ``--budget`` draws; a count that stops at the budget is a LOWER BOUND and is flagged (with a Chao1 estimate). Seeds are throwaway (stated in the output).

  uv run --locked python -m studies.m0.c1_fix3_capacity --g 12 --budget 100000 --seed 17 --out <json> [--only id,..] [--workers 6]
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import math
import random
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from studies.m0.c1_batch1_capacity import alpha_key

K2_DEFAULT = ("C1.cellular_update_f3", "C1.counter_list_f3", "C1.cellular_update_r2", "C1.counter_list")


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def _h(s: str) -> str:
    return hashlib.blake2b(s.encode(), digest_size=8).hexdigest()


class _Blank(ast.NodeTransformer):
    def visit_Constant(self, n: ast.Constant) -> Any:
        return ast.Constant(value="<S>" if isinstance(n.value, str) else 0)

    def visit_UnaryOp(self, n: ast.UnaryOp) -> Any:
        if isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
            return ast.Constant(value=0)
        return self.generic_visit(n)


_BUILTIN_NAMES = frozenset({"len", "sum", "max", "min", "abs", "range", "sorted", "str", "print"})


def _renamed(src: str) -> ast.AST:
    """The parsed program with variable, parameter and function names replaced by v0, v1, ... in order of first appearance (as ``alpha_key`` does)."""
    mapping: dict[str, str] = {}

    class Rename(ast.NodeTransformer):
        def name(self, n: str) -> str:
            return n if n in _BUILTIN_NAMES else mapping.setdefault(n, f"v{len(mapping)}")

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

    tree: ast.AST = Rename().visit(ast.parse(src))
    return tree


def k2_key(src: str) -> str:
    """Renamed skeleton with every literal blanked, plus the sequence of executed source lines (literals that do not change control flow do not count)."""
    skel = ast.dump(_Blank().visit(_renamed(src)), annotate_fields=False)
    lines: list[int] = []

    def tr(frame: Any, event: str, arg: Any) -> Any:
        if frame.f_code.co_filename == "<k2>":
            lines.append(frame.f_lineno if event == "line" else (-1 if event == "call" else -2))
        return tr

    code = compile(src, "<k2>", "exec")
    with contextlib.redirect_stdout(io.StringIO()):
        sys.settrace(tr)
        try:
            exec(code, {"__name__": "__k2__"})  # noqa: S102
        finally:
            sys.settrace(None)
    return _h(skel + "|" + ",".join(map(str, lines)))


def cell(args: tuple[str, int, int, int, int, bool]) -> tuple[str, int, dict[str, Any]]:
    lid, lv, need, budget, seed, want_k2 = args
    sys.path.insert(0, ".")
    from studies.m0.c1_fix3_battery import all_lineages
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry

    lin = all_lineages()[lid]
    d = hashlib.sha256(f"fix3-cap|{seed}|{lid}|{lv}".encode()).digest()
    r = random.Random(int.from_bytes(d[:8], "big"))
    k1: Counter[str] = Counter()
    k2: set[str] = set()
    draws = 0
    t0 = time.time()
    while draws < budget and len(k1) < need:
        try:
            b = lin.build(lv, r)
        except Retry:
            continue
        draws += 1
        src = render(b.structured["program"])
        h = _h(alpha_key(src))
        if h not in k1 and want_k2:
            k2.add(k2_key(src))
        k1[h] += 1
    f1 = sum(1 for v in k1.values() if v == 1)
    f2 = sum(1 for v in k1.values() if v == 2)
    chao1 = len(k1) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    out: dict[str, Any] = {"draws": draws, "k1": len(k1), "reached": len(k1) >= need, "budget_hit": draws >= budget and len(k1) < need, "chao1": round(chao1), "secs": round(time.time() - t0, 1), "hashes": sorted(k1)}
    if want_k2:
        out["k2"] = len(k2)
    return lid, lv, out


def run(g: int, budget: int, seed: int, only: list[str], workers: int, k2_ids: tuple[str, ...]) -> dict[str, Any]:
    from studies.m0.lineages_c1_fix3_clusters import MEMBERS

    need = demand(g)
    ids = sorted({m for ms in MEMBERS.values() for m in ms} | set(k2_ids))
    if only:
        ids = [i for i in ids if i in only]
    jobs = [(i, lv, need, budget, seed, i in k2_ids) for i in ids for lv in range(7)]
    jobs.sort(key=lambda j: -j[1])
    rows: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(workers) as ex:
        for lid, lv, rr in ex.map(cell, jobs, chunksize=1):
            rows.setdefault(lid, {})[str(lv)] = rr
            print(lid, lv, {k: rr[k] for k in ("draws", "k1", "chao1", "secs", "reached")}, flush=True)
    clusters: dict[str, dict[str, Any]] = {}
    for cname, ms in MEMBERS.items():
        ms = tuple(m for m in ms if m in rows)
        if not ms:
            continue
        for lv in range(7):
            union: set[str] = set()
            for m in ms:
                union.update(rows[m][str(lv)]["hashes"])
            clusters.setdefault(cname, {})[str(lv)] = {"k1_union": len(union), "reached": len(union) >= need, "members": list(ms), "any_budget_hit": any(rows[m][str(lv)]["budget_hit"] for m in ms)}
    for lid in rows:
        for lvk in rows[lid]:
            rows[lid][lvk].pop("hashes")
    return {"g": g, "need": need, "budget": budget, "seed": seed, "k2_ids": list(k2_ids), "rows": rows, "clusters": clusters}


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--g", type=int, default=12)
    ap.add_argument("--budget", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--k2", default=",".join(K2_DEFAULT))
    a = ap.parse_args()
    res = run(a.g, a.budget, a.seed, [x for x in a.only.split(",") if x], a.workers, tuple(x for x in a.k2.split(",") if x))
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    need = res["need"]
    print(f"need per cluster and level at G={a.g}: {need}")
    bad_c = [(c, lv, v["k1_union"]) for c, d in res["clusters"].items() for lv, v in d.items() if not v["reached"]]
    bad_l = [(i, lv, v["k1"], v["budget_hit"]) for i, d in res["rows"].items() for lv, v in d.items() if not v["reached"]]
    print("reading (a), clusters below need:", bad_c)
    print("reading (b), lineages below need:", bad_l)
    for i, d in res["rows"].items():
        if "k2" in next(iter(d.values())):
            print("reading (c)", i, {lv: v["k2"] for lv, v in sorted(d.items())})


if __name__ == "__main__":
    main()
