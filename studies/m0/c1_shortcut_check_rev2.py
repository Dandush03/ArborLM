# ruff: noqa: E501
"""Shortcut battery, revision 2 (measurement only; no threshold is registered; ruling R-3).

Adds to the batch-1 battery (``c1_shortcut_check``, my own) the independent auditor's rules, COPIED and adapted with attribution from
``docs/reviews/m0-lineage-decision-2026-11-25/audit_c1/a07_shortcuts.py`` and ``a07b_shortcuts_v2.py`` (arbor-auditor, Claude Opus 5.5, audit
AUDIT_M0_C1_1): O1 shape-constant (most frequent key per printed expression, 2-fold cross-validated), O2 last top-level int assigned, O3 first
loop bound, O4 longest list literal, O5 best single literal rule out of about 60 (fit on one half, scored on the other), O6 the rate of key '0',
O7 best rule per printed expression (cross-validated), and the lineage-specific recognition rules R.* (closed forms and naive readings). The
auditor's code ran on his own tree representation; here every rule reads the program through ``ast`` of the rendered source (parse only, never
executed), so a rule that depends on tree positions was re-derived, not copied byte for byte.

Reported per lineage, level and SHAPE (the printed expression with names renamed by first appearance and constants masked): the hit rate of each
rule beside the most-frequent-key rate of the same cell. The 'worst' row of a lineage is the largest raw rule rate over cells of at least 100 items;
raw maxima over many rules are optimistic for small cells, so the cross-validated O1/O5/O7 are printed beside them.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_shortcut_check_rev2 --per-level 2000 --out <json>``.
"""

from __future__ import annotations

import ast
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from studies.m0.c1_shortcut_check import GENERIC, Facts, oracle_list_stat, oracle_literal
from studies.m0.c1grammar import render
from studies.m0.core import ALL_LEVELS, Item, draw_items, stream

SEED = 953801  # test block 953001-953999
MIN_CELL = 100


# ------------------------------------------------------------------------------------------------ program reading through ast


class _Rename(ast.NodeTransformer):
    BUILTIN = frozenset({"len", "sum", "max", "min", "abs", "range", "sorted", "str", "print"})

    def __init__(self) -> None:
        self.m: dict[str, str] = {}

    def nm(self, n: str) -> str:
        return n if n in self.BUILTIN else self.m.setdefault(n, f"v{len(self.m)}")

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        node.id = self.nm(node.id)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self.nm(node.arg)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
        node.name = self.nm(node.name)
        self.generic_visit(node)
        return node


class _Mask(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
        return ast.Constant(value=type(node.value).__name__)


def shape_key(src: str) -> str:
    """The printed expression with names renamed by first appearance and constants masked (the auditor's 'canonical print expression')."""
    tree = _Rename().visit(ast.parse(src))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print":
            arg = n.args[0]
            key = ast.dump(_Mask().visit(arg), annotate_fields=False)
            if isinstance(arg, ast.Name):  # a bare variable: add how it is updated, so 'count comparisons' and 'count switches' are different shapes
                parent = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
                ups = set()
                for m in ast.walk(tree):
                    if isinstance(m, ast.AugAssign | ast.Assign) and _target_name(m) == arg.id:
                        up, ctx = m, "-"
                        while up in parent:
                            up = parent[up]
                            if isinstance(up, ast.If):
                                ctx = ast.dump(_Mask().visit(up.test), annotate_fields=False)
                                break
                        ups.add(ast.dump(_Mask().visit(m.value), annotate_fields=False) + "@" + ctx)
                key += "|" + "|".join(sorted(ups))
            return key
    return "?"


def _target_name(m: ast.AST) -> str | None:
    t = m.targets[0] if isinstance(m, ast.Assign) else m.target  # type: ignore[attr-defined]
    return t.id if isinstance(t, ast.Name) else None


def top_sets(tree: ast.Module) -> list[ast.Assign]:
    return [s for s in tree.body if isinstance(s, ast.Assign)]


def _const(node: ast.AST | None) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return -node.operand.value
    return None


class Ctx:
    """Facts plus the parsed tree, built once per item."""

    def __init__(self, it: Item) -> None:
        self.f = Facts(it)
        self.src = render(it.structured["program"])
        self.tree = ast.parse(self.src)
        self.ans = it.answer


def S(v: Any) -> str:
    return str(v)


def _mode(xs: list[int]) -> int:
    c = Counter(xs)
    return min(c, key=lambda k: (-c[k], k))


# ------------------------------------------------------------------------------------------------ auditor's candidate rules (O5/O7); copied and adapted


def _kth(f: Facts, k: int, rev: bool) -> str | None:
    xs = sorted(set(f.nums), reverse=rev)
    return S(xs[k]) if len(xs) > k else None


def _last_set_int(tree: ast.Module) -> str | None:
    v = None
    for s in top_sets(tree):
        c = _const(s.value)
        if c is not None:
            v = c
    return S(v) if v is not None else None


def _loop_bound(tree: ast.Module) -> str | None:
    for n in ast.walk(tree):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and n.iter.args:
            c = _const(n.iter.args[-1])
            if c is not None:
                return S(c)
        if isinstance(n, ast.While) and isinstance(n.test, ast.Compare):
            c = _const(n.test.comparators[0])
            if c is not None:
                return S(c)
    return None


def cand_rules() -> dict[str, Callable[[Ctx], str | None]]:
    C: dict[str, Callable[[Ctx], str | None]] = {}
    for k in range(10):
        C[f"num[{k}]"] = (lambda k: lambda c: S(c.f.nums[k]) if len(c.f.nums) > k else None)(k)
        C[f"num[-{k + 1}]"] = (lambda k: lambda c: S(c.f.nums[-k - 1]) if len(c.f.nums) > k else None)(k)
    for k in range(3):
        C[f"max#{k + 1}"] = (lambda k: lambda c: _kth(c.f, k, True))(k)
        C[f"min#{k + 1}"] = (lambda k: lambda c: _kth(c.f, k, False))(k)
    C["sum_nums"] = lambda c: S(sum(c.f.nums)) if c.f.nums else None
    C["count_nums"] = lambda c: S(len(c.f.nums))
    C["n_distinct_nums"] = lambda c: S(len(set(c.f.nums)))
    C["len_str1"] = lambda c: S(len(c.f.strs[0])) if c.f.strs else None
    C["len_str_last"] = lambda c: S(len(c.f.strs[-1])) if c.f.strs else None
    C["str1"] = lambda c: c.f.strs[0] if c.f.strs else None
    C["len_list1"] = lambda c: S(len(c.f.flat[0])) if c.f.flat else None
    C["len_list_last"] = lambda c: S(len(c.f.flat[-1])) if c.f.flat else None
    C["len_list_longest"] = lambda c: S(max(len(x) for x in c.f.lists)) if c.f.lists else None
    C["len_list1_minus1"] = lambda c: S(len(c.f.flat[0]) - 1) if c.f.flat else None
    C["sum_list1"] = lambda c: S(sum(c.f.flat[0])) if c.f.flat else None
    C["max_list1"] = lambda c: S(max(c.f.flat[0])) if c.f.flat else None
    C["min_list1"] = lambda c: S(min(c.f.flat[0])) if c.f.flat else None
    C["list1"] = lambda c: S(c.f.flat[0]) if c.f.flat else None
    C["list1_sorted"] = lambda c: S(sorted(c.f.flat[0])) if c.f.flat else None
    C["list1_sorted_desc"] = lambda c: S(sorted(c.f.flat[0], reverse=True)) if c.f.flat else None
    C["ones_list1"] = lambda c: S(c.f.flat[0].count(1)) if c.f.flat else None
    C["zeros_list1"] = lambda c: S(c.f.flat[0].count(0)) if c.f.flat else None
    C["last_set_int"] = lambda c: _last_set_int(c.tree)
    C["loop_bound"] = lambda c: _loop_bound(c.tree)
    C["echo"] = lambda c: c.f.echo
    for k in ("0", "1", "2", "3"):
        C["const_" + k] = (lambda k: lambda c: k)(k)
    return C


# ------------------------------------------------------------------------------------------------ auditor's lineage-specific rules R.*; adapted to ast


def R_euclid(c: Ctx) -> dict[str, str]:
    x, y = c.f.nums[0], c.f.nums[1]
    return {"R.gcd_of_literals": S(math.gcd(x, y)), "R.min_literal": S(min(x, y)), "R.sum_quot_naive_max_div_min": S(max(x, y) // min(x, y))}


def R_fastpow(c: Ctx) -> dict[str, str]:
    base, ex, mod = c.f.nums[1], c.f.nums[2], c.f.nums[3]
    bb = base
    for _ in range(ex.bit_length()):
        bb = bb * bb % mod
    return {"R.pow(base,exp,mod)": S(pow(base, ex, mod)), "R.base_mod": S(base % mod), "R.base^(2^bits)": S(bb)}


def R_digit(c: Ctx) -> dict[str, str]:
    n = c.f.nums[0]
    return {"R.decimal_digit_sum_of_literal": S(sum(int(ch) for ch in str(n))), "R.decimal_digit_count": S(len(str(n)))}


def _insertion_params(c: Ctx) -> tuple[int, str]:
    loop = next(n for n in ast.walk(c.tree) if isinstance(n, ast.For))
    k = _const(loop.iter.args[1]) or 0
    wh = next(n for n in ast.walk(loop) if isinstance(n, ast.While))
    cmp_ = wh.test.values[1]  # type: ignore[attr-defined]
    op = {ast.Gt: ">", ast.Lt: "<", ast.GtE: ">=", ast.LtE: "<="}[type(cmp_.ops[0])]
    return k, op


def R_insertion(c: Ctx) -> dict[str, str]:
    xs = c.f.flat[0]
    k, op = _insertion_params(c)
    desc = op in ("<", "<=")
    after = sorted(xs[:k], reverse=desc) + xs[k:]
    out = {"R.sorted_prefix_list": S(after)}
    pr = next(n for n in ast.walk(c.tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print").args[0]
    if isinstance(pr, ast.Subscript) and _const(pr.slice) is not None:
        out["R.sorted_prefix_at"] = S(after[_const(pr.slice)])  # type: ignore[index]
    inv = 0
    for i in range(k):
        for j in range(i):
            a, b = xs[j], xs[i]
            if (a > b if op == ">" else a >= b if op == ">=" else a < b if op == "<" else a <= b):
                inv += 1
    out["R.inversions_prefix"] = S(inv)
    return out


def R_partition(c: Ctx) -> dict[str, str]:
    xs = c.f.flat[0]
    pv_assign = top_sets(c.tree)[1]
    m = _const(pv_assign.value.slice) + 1  # type: ignore[attr-defined]
    piv = xs[m - 1]
    loop = next(n for n in c.tree.body if isinstance(n, ast.For))
    op = "<=" if isinstance(loop.body[0].test.ops[0], ast.LtE) else "<"  # type: ignore[attr-defined]
    le = [x for x in xs[: m - 1] if (x <= piv if op == "<=" else x < piv)]
    gt = [x for x in xs[: m - 1] if not (x <= piv if op == "<=" else x < piv)]
    return {"R.stable_partition": S(le + [piv] + gt + xs[m:]), "R.input_list": S(xs)}


def _max_sub(xs: list[int]) -> int:
    best = cur = xs[0]
    for x in xs[1:]:
        cur = max(cur + x, x)
        best = max(best, cur)
    return best


def R_kadane(c: Ctx) -> dict[str, str]:
    xs = c.f.flat[0]
    return {"R.max_subarray": S(_max_sub(xs)), "R.last_element": S(xs[-1])}


def R_majority(c: Ctx) -> dict[str, str]:
    xs = c.f.flat[0]
    return {"R.last_element": S(xs[-1]), "R.first_element": S(xs[0]), "R.mode_space_0": S(_mode(xs)) + " 0"}


def R_bracket(c: Ctx) -> dict[str, str]:
    s = c.f.strs[0]
    opens = s.count("(") + s.count("[")
    st: list[str] = []
    err, first = 0, -1
    for i, ch in enumerate(s):
        if ch in "([":
            st.append(ch)
        elif st and ((ch == ")" and st[-1] == "(") or (ch == "]" and st[-1] == "[")):
            st.pop()
        else:
            err += 1
            first = i if first < 0 else first
    return {"R.net_balance": S(opens - (len(s) - opens)), "R.opens": S(opens), "R.standard_height": S(len(st)), "R.standard_code": S(10 * err + len(st)), "R.standard_first": S(first)}


def R_coin(c: Ctx) -> dict[str, str]:
    coins = c.f.flat[0]
    pr = next(n for n in ast.walk(c.tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print").args[0]
    if not (isinstance(pr, ast.Subscript) and _const(pr.slice) is not None):
        return {}
    t = _const(pr.slice)
    assert t is not None
    g, rem = 0, t
    for cn in sorted(coins, reverse=True):
        g += rem // cn
        rem %= cn
    return {"R.greedy_fewest": S(g) if rem == 0 else "", "R.T_div_maxcoin": S(t // max(coins))}


def R_strpair(c: Ctx) -> dict[str, str]:
    a, b = c.f.strs[0], c.f.strs[1]
    ham = sum(1 for x, y in zip(a, b, strict=False) if x != y) + abs(len(a) - len(b))
    ca, cb = Counter(a), Counter(b)
    return {"R.hamming_plus_lendiff": S(ham), "R.multiset_overlap": S(sum(min(ca[ch], cb[ch]) for ch in sorted(ca))), "R.len_a": S(len(a))}


def R_grid(c: Ctx) -> dict[str, str]:
    g = c.f.lists[0]
    r, cc = len(g), len(g[0])
    out = {"R.binom_paths": S(math.comb(r + cc - 2, r - 1))}
    for name, better in (("R.greedy_max_path", lambda a, b: a >= b), ("R.greedy_min_path", lambda a, b: a <= b)):
        i = j = 0
        tot = g[0][0]
        while (i, j) != (r - 1, cc - 1):
            if i == r - 1 or (j < cc - 1 and better(g[i][j + 1], g[i + 1][j])):
                j += 1
            else:
                i += 1
            tot += g[i][j]
        out[name] = S(tot)
    return out


def R_union(c: Ctx) -> dict[str, str]:
    n = len(c.f.flat[0])
    us, vs = c.f.flat[1], c.f.flat[2]
    p1, p2 = list(range(n)), list(range(n))
    for u, v in zip(us, vs, strict=True):
        p1[u] = v
        p2[v] = u
    return {"R.naive_links_u->v": S(p1), "R.naive_links_v->u": S(p2), "R.identity": S(list(range(n)))}


def R_turtle(c: Ctx) -> dict[str, str]:
    if not c.f.strs:  # revision 2 encodes commands as integers: 1-3 forward, 4/5 turn, 6 back one
        t = c.f.flat[0]
        fwd = [v for v in t if v <= 3]
        return {"R.sum_forward_steps": S(sum(fwd)), "R.count_forward": S(len(fwd)), "R.sum_forward_minus_back": S(sum(fwd) - t.count(6)), "R.count_turns": S(t.count(4) + t.count(5))}
    s = c.f.strs[0]
    return {"R.F_minus_B": S(s.count("F") - s.count("B")), "R.count_F": S(s.count("F")), "R.count_F_plus_B": S(s.count("F") + s.count("B"))}


def R_bytecode(c: Ctx) -> dict[str, str]:
    return {"R.sum_all_args": S(sum(c.f.flat[0][1::2]))}


def R_sieve(c: Ctx) -> dict[str, str]:
    fl = c.f.flat[0]
    n = len(fl)
    pr = [i for i in range(2, n) if all(i % d for d in range(2, int(i**0.5) + 1))]
    out = {"R.prime_count_below_n": S(len(pr)), "R.ones_minus_strikes_naive": S(sum(fl[:2]) + len([i for i in pr if fl[i]]))}
    # my addition: the all-ones sieve read (a prime table), for either printed quantity, for each of the three start rules
    for start_name, start in (("sq", lambda i: i * i), ("dbl", lambda i: 2 * i), ("tri", lambda i: 3 * i)):
        allones = [1] * n
        for i in range(2, n):
            if allones[i] == 1:
                j = start(i)
                while j < n:
                    allones[j] = 0
                    j += i
        out[f"R.mine_allones_{start_name}_count"] = S(sum(allones))
        out[f"R.mine_allones_{start_name}_indexsum"] = S(sum(i for i, v in enumerate(allones) if v))
    return out


def R_mirror(c: Ctx) -> dict[str, str]:
    s = c.f.strs[0]
    n = len(s)
    return {"R.unequal_pairs": S(sum(1 for k in range(n // 2) if s[k] != s[n - 1 - k]))}


def R_merge(c: Ctx) -> dict[str, str]:
    a, b = c.f.flat[0], c.f.flat[1]
    return {"R.len_a+len_b-1": S(len(a) + len(b) - 1), "R.sorted_all_but_last": S(sorted(a + b)[:-1])}


def R_circle(c: Ctx) -> dict[str, str]:
    fl = c.f.flat[0]
    return {"R.last_live_index": S(max(i for i, v in enumerate(fl) if v)), "R.first_live_index": S(min(i for i, v in enumerate(fl) if v))}


def R_postfix(c: Ctx) -> dict[str, str]:
    toks = c.f.flat[0]
    return {"R.last_operand": S([t for t in toks if t >= 0][-1]), "R.first_operand": S(toks[0])}


SPECIFIC: dict[str, Callable[[Ctx], dict[str, str]]] = {
    "euclid_gcd": R_euclid, "fast_power": R_fastpow, "digit_peel": R_digit, "insertion_sort": R_insertion, "partition_pass": R_partition, "kadane_scan": R_kadane,
    "majority_vote_scan": R_majority, "bracket_matching": R_bracket, "coin_change_table": R_coin, "string_pair_table": R_strpair, "grid_path_table": R_grid,
    "union_find_links": R_union, "turtle_walk": R_turtle, "bytecode_loop": R_bytecode, "sieve_marking": R_sieve, "mirror_pointers": R_mirror,
    "merge_two_sorted": R_merge, "circle_elimination": R_circle, "postfix_evaluation": R_postfix,
}


def specific_for(lid: str) -> Callable[[Ctx], dict[str, str]] | None:
    base = lid.removeprefix("C1.").removesuffix("_r2").removesuffix("_traced")
    return SPECIFIC.get(base)


# ------------------------------------------------------------------------------------------------ per-item guesses and cell statistics


def author_generic() -> dict[str, Callable[[Ctx], str | None]]:
    return {"A." + k: (lambda g: lambda c: g(c.f))(g) for k, g in GENERIC.items()}


def guesses(c: Ctx, lid: str, cands: dict[str, Callable[[Ctx], str | None]], auth: dict[str, Callable[[Ctx], str | None]]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for k, g in auth.items():
        out[k] = _safe(g, c)
    for k, g in cands.items():
        out["O." + k] = _safe(g, c)
    sp = specific_for(lid)
    if sp is not None:
        try:
            out.update(sp(c))
        except (IndexError, ValueError, TypeError, AttributeError, StopIteration, KeyError, ZeroDivisionError):
            pass
    return out


def _safe(g: Callable[[Ctx], str | None], c: Ctx) -> str | None:
    try:
        return g(c)
    except (IndexError, ValueError, TypeError, AttributeError, StopIteration, KeyError, ZeroDivisionError):
        return None


def cv_constant_by_shape(rows: list[tuple[str, str]]) -> float:
    hit = 0
    for fit, test in ((0, 1), (1, 0)):
        tab: dict[str, Counter[str]] = defaultdict(Counter)
        for i, (sh, a) in enumerate(rows):
            if i % 2 == fit:
                tab[sh][a] += 1
        best = {sh: min(cn, key=lambda k: (-cn[k], k)) for sh, cn in sorted(tab.items())}
        hit += sum(1 for i, (sh, a) in enumerate(rows) if i % 2 == test and best.get(sh) == a)
    return hit / len(rows)


def cv_best_rule(rows: list[tuple[str, str, dict[str, str | None]]], rule_names: list[str], per_shape: bool) -> float:
    hit = 0
    for fit, test in ((0, 1), (1, 0)):
        score: dict[str, Counter[str]] = defaultdict(Counter)
        consts: dict[str, Counter[str]] = defaultdict(Counter)
        for i, (sh, a, g) in enumerate(rows):
            if i % 2 != fit:
                continue
            key = sh if per_shape else "*"
            for nm in rule_names:
                if g.get(nm) == a:
                    score[key][nm] += 1
            consts[key][a] += 1
        pick: dict[str, tuple[str, str | None]] = {}
        for key in sorted(set(score) | set(consts)):
            bn = max(rule_names, key=lambda nm: (score[key][nm], nm)) if score[key] else None
            bc = min(consts[key], key=lambda a: (-consts[key][a], a)) if consts[key] else None
            if per_shape and bc is not None and consts[key][bc] > (score[key][bn] if bn else 0):
                pick[key] = ("const", bc)
            else:
                pick[key] = ("rule", bn)
        for i, (sh, a, g) in enumerate(rows):
            if i % 2 != test:
                continue
            pk = pick.get(sh if per_shape else "*")
            if pk is None:
                continue
            if (pk[0] == "const" and pk[1] == a) or (pk[0] == "rule" and pk[1] is not None and g.get(pk[1]) == a):
                hit += 1
    return hit / len(rows)


def measure_lineage(lid: str, per_level: int) -> dict[str, Any]:
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2

    lin = next(x for x in [*load_batch1(), *load_rev2()] if x.id == lid)
    cands, auth = cand_rules(), author_generic()
    cand_names = sorted("O." + k for k in cands)
    res: dict[str, Any] = {"levels": {}}
    for lv in ALL_LEVELS:
        rng = stream(SEED, "c1-rev2-battery", lin.id, str(lv))
        items = draw_items(lin, "A", lv, per_level, rng, set(), "battery")
        ctxs = [Ctx(it) for it in items]
        ans = [it.answer for it in items]
        shapes = [shape_key(c.src) for c in ctxs]
        gs = [guesses(c, lid, cands, auth) for c in ctxs]
        n = len(items)
        cells: dict[str, Any] = {}
        for sh in sorted(set(shapes)):
            idx = [i for i in range(n) if shapes[i] == sh]
            cnt = Counter(ans[i] for i in idx)
            top = min(cnt, key=lambda k: (-cnt[k], k))
            rates: dict[str, float] = {}
            for nm in sorted({k for i in idx for k in gs[i]}):
                h = sum(1 for i in idx if gs[i].get(nm) == ans[i])
                if h:
                    rates[nm] = h / len(idx)
            best = sorted(rates.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
            cells[sh[:90]] = {"n": len(idx), "share": round(len(idx) / n, 4), "constant_key": top[:24], "constant": round(cnt[top] / len(idx), 4), "best_rules": [[k, round(v, 4)] for k, v in best]}
        rows = [(shapes[i], ans[i], gs[i]) for i in range(n)]
        all_names = sorted({k for g in gs for k in g})
        res["levels"][str(lv)] = {
            "n": n, "distinct_keys": len(set(ans)), "key_is_0": round(sum(1 for a in ans if a == "0") / n, 4),
            "O1_shape_const_cv": round(cv_constant_by_shape([(shapes[i], ans[i]) for i in range(n)]), 4),
            "O5_best_literal_rule_cv": round(cv_best_rule(rows, cand_names, False), 4),
            "O7_best_rule_per_shape_cv": round(cv_best_rule(rows, cand_names, True), 4),
            "O7_all_rules_per_shape_cv": round(cv_best_rule(rows, all_names, True), 4),
            "oracle_any_literal": round(sum(oracle_literal(c.f, c.ans) for c in ctxs) / n, 4),
            "oracle_list_or_string_statistic": round(sum(oracle_list_stat(c.f, c.ans) for c in ctxs) / n, 4),
            "cells": cells,
        }
    return res


def summarise(res: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, levels in (("core_1_5", ("1", "2", "3", "4", "5")), ("all_0_6", tuple(str(x) for x in ALL_LEVELS))):
        worst: tuple[float, str, str, str, float, int] = (-1.0, "", "", "", 0.0, 0)
        for lv in levels:
            for sh, cell in sorted(res["levels"][lv]["cells"].items()):
                if cell["n"] >= MIN_CELL and cell["best_rules"] and cell["best_rules"][0][1] > worst[0]:
                    worst = (cell["best_rules"][0][1], cell["best_rules"][0][0], sh, lv, cell["constant"], cell["n"])
        out[label] = {"worst_cell_rule_rate": worst[0], "rule": worst[1], "shape": worst[2], "level": worst[3], "constant_in_that_cell": worst[4], "cell_n": worst[5],
                      "O1_max": max(res["levels"][lv]["O1_shape_const_cv"] for lv in levels), "O5_max": max(res["levels"][lv]["O5_best_literal_rule_cv"] for lv in levels),
                      "O7_max": max(res["levels"][lv]["O7_best_rule_per_shape_cv"] for lv in levels), "O7_all_max": max(res["levels"][lv]["O7_all_rules_per_shape_cv"] for lv in levels),
                      "min_distinct_keys": min(res["levels"][lv]["distinct_keys"] for lv in levels)}
    return out


def _work(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    lid, per_level = args
    r = measure_lineage(lid, per_level)
    r["summary"] = summarise(r)
    return lid, r


def run(per_level: int, ids: list[str], out_path: Path | None, workers: int = 8) -> dict[str, Any]:
    result: dict[str, Any] = {"per_level": per_level, "seed": SEED, "min_cell": MIN_CELL, "lineages": {}}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for lid, r in ex.map(_work, [(i, per_level) for i in ids]):
            result["lineages"][lid] = r
            s = r["summary"]["core_1_5"]
            print(f"{lid:34s} worst cell rule {s['rule']} {s['worst_cell_rule_rate']:.3f} (shape n={s['cell_n']}, constant there {s['constant_in_that_cell']:.3f}, L{s['level']})  O1 {s['O1_max']:.3f} O5 {s['O5_max']:.3f} O7 {s['O7_max']:.3f} O7all {s['O7_all_max']:.3f}", flush=True)
    if out_path:
        out_path.write_text(json.dumps(result, indent=1, sort_keys=True))
        out_path.with_name(out_path.stem + "_table.md").write_text(table_md(result))
        out_path.with_name(out_path.stem + "_cells.md").write_text(cells_md(result))
    return result


def _status(lid: str) -> str:
    from studies.m0.lineages_c1_rev2 import PROPOSED, SUPERSEDES

    if lid in PROPOSED:
        return "PROPOSED shape (additional)"
    if lid in SUPERSEDES:
        return f"revised (supersedes {SUPERSEDES[lid].removeprefix('C1.')})"
    if lid in set(SUPERSEDES.values()):
        return "SUPERSEDED (before)"
    return "unchanged (batch 1 or existing)"


def table_md(result: dict[str, Any]) -> str:
    """Worst cell per lineage over core levels 1-5 (a cell is one printed-expression shape at one level, at least 100 items): the best rule's hit rate beside the
    most-frequent-key rate of the same cell, then the cross-validated O1/O5/O7 maxima."""
    lines = [f"# C1 shortcut battery, revision 2 (measured; {result['per_level']} distinct items per lineage and level, seed {result['seed']}; no threshold registered)\n",
             "Rules: the batch-1 battery plus the independent auditor's O1, O5, O6, O7 and R.* rules (copied and adapted with attribution, see `c1_shortcut_check_rev2.py`). `rate` is the best single rule's exact-match rate in the worst cell; `const` is the most frequent key of that same cell. A rate of 1.000 is a closed form that answers without tracing (decision reserved to the human lead). Maxima over many rules are optimistic in small cells; the cross-validated O columns are printed beside them.\n",
             "| lineage | status | worst cell: rule | rate | const in cell | cell n | level | O1 max | O5 max | O7 max | O7 (all rules) max | min distinct keys |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for lid, v in sorted(result["lineages"].items()):
        s = v["summary"]["core_1_5"]
        lines.append(f"| {lid} | {_status(lid)} | {s['rule'] or '-'} | {s['worst_cell_rule_rate']:.3f} | {s['constant_in_that_cell']:.3f} | {s['cell_n']} | {s['level']} | {s['O1_max']:.3f} | {s['O5_max']:.3f} | {s['O7_max']:.3f} | {s['O7_all_max']:.3f} | {s['min_distinct_keys']} |")
    lines += ["", "## Before and after (superseded lineage, its revision), worst cell over levels 1-5", "", "| superseded | rate (rule) | const | revised | rate (rule) | const |", "|---|---|---|---|---|---|"]
    from studies.m0.lineages_c1_rev2 import SUPERSEDES

    for new, old in sorted(SUPERSEDES.items()):
        if new in result["lineages"] and old in result["lineages"]:
            a, b = result["lineages"][old]["summary"]["core_1_5"], result["lineages"][new]["summary"]["core_1_5"]
            lines.append(f"| {old} | {a['worst_cell_rule_rate']:.3f} ({a['rule']}) | {a['constant_in_that_cell']:.3f} | {new} | {b['worst_cell_rule_rate']:.3f} ({b['rule']}) | {b['constant_in_that_cell']:.3f} |")
    return "\n".join(lines) + "\n"


def cells_md(result: dict[str, Any]) -> str:
    """Every cell of at least 100 items for core levels 1-5: lineage, level, shape (printed expression with the statements that update it), n, const key and rate, best three rules."""
    lines = ["# C1 shortcut battery, revision 2: per level and shape (measured)\n", "| lineage | level | n | const key | const rate | best rules (rate) | shape |", "|---|---|---|---|---|---|---|"]
    for lid, v in sorted(result["lineages"].items()):
        for lv in ("1", "2", "3", "4", "5"):
            for sh, c in sorted(v["levels"][lv]["cells"].items(), key=lambda kv: -kv[1]["n"]):
                if c["n"] >= MIN_CELL:
                    best = "; ".join(f"{k} {r:.3f}" for k, r in c["best_rules"][:3])
                    lines.append(f"| {lid} | {lv} | {c['n']} | `{c['constant_key']}` | {c['constant']:.3f} | {best} | `{sh[:48]}` |")
    return "\n".join(lines) + "\n"


def main() -> None:
    import argparse

    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    ids = [x.id for x in [*load_batch1(), *load_rev2()]]
    if a.only:
        ids = [i for i in ids if i in a.only]
    run(a.per_level, ids, Path(a.out) if a.out else None, a.workers)


if __name__ == "__main__":
    main()
