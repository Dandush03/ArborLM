# ruff: noqa: E501
# one long rule function that reuses scratch names across lineages, like the auditor's a3_shortcuts.py
# mypy: disable-error-code="assignment,index,operator,call-overload,arg-type,no-redef,attr-defined,var-annotated,misc,no-untyped-call,type-arg,union-attr"
"""Shortcut and closed-form battery for the C1 fix round 3 lineages (measurement, not a threshold; rulings R-3, R-14; brief: every cheap rule at or below 0.10, a working
target, not a registered bound).

For each lineage, level and shape the battery reports the rate at which each rule's prediction equals the key (open answers: chance 0). It reads ONLY the rendered source
and the key. Parts adapted from the auditor's ``a3_shortcuts.py`` (``docs/reviews/m0-lineage-decision-2026-11-25/audit3_c1/``; literals, lists, the generic literal rules, the
2-fold most-frequent-key estimate); the lineage-specific rules below are new: the audit's formulas for the old shapes adapted to the new questions, plus other cheap attempts.
Some rules run a MUTATED copy of the program (a branch dropped, a term removed) in process under a 2 s alarm; those mutations are the 'ignore this feature' attempts.

Rates are 'inside the shape': the number of items of the shape whose key the rule hits, over the items of the shape. Draws use a throwaway seed (never a registered one).

  uv run --locked python -m studies.m0.c1_fix3_battery --per-level 400 --seed 31 --out <json> [--only C1.x_f3,...] [--workers 6]
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
import re
import signal
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Any


# ------------------------------------------------------------------ parsing helpers (adapted from the audit's a3_shortcuts.py)
def lit(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int):
        return -node.operand.value
    return None


def ints_in_order(tree: ast.AST) -> list[int]:
    out: list[int] = []

    class Vis(ast.NodeVisitor):
        def visit_UnaryOp(self, n: ast.UnaryOp) -> None:
            v = lit(n)
            if v is not None:
                out.append(v)
            else:
                self.generic_visit(n)

        def visit_Constant(self, n: ast.Constant) -> None:
            v = lit(n)
            if v is not None:
                out.append(v)

    Vis().visit(tree)
    return out


def int_lists(tree: ast.AST) -> list[list[int]]:
    res = []
    for n in ast.walk(tree):
        if isinstance(n, ast.List) and n.elts and all(lit(e) is not None for e in n.elts):
            res.append((n.lineno, n.col_offset, [lit(e) for e in n.elts]))
    res.sort()
    return [x[2] for x in res]


def strs(tree: ast.AST) -> list[str]:
    res = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            res.append((n.lineno, n.col_offset, n.value))
    res.sort()
    return [x[2] for x in res]


def top_sets(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    return [(n.targets[0].id, n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)]


def print_name(tree: ast.Module) -> str | None:
    a = tree.body[-1].value.args[0]
    return a.id if isinstance(a, ast.Name) else None


def alpha_dump(tree: ast.AST) -> ast.AST:
    keep = {"len", "sum", "max", "min", "abs", "str", "range", "print", "append", "upper", "lower", "replace", "count", "sorted"}
    mp: dict[str, str] = {}

    def nm(x: str) -> str:
        if x in keep:
            return x
        return mp.setdefault(x, f"v{len(mp)}")

    t = ast.parse(ast.unparse(tree))
    for n in ast.walk(t):
        if isinstance(n, ast.Name):
            n.id = nm(n.id)
        elif isinstance(n, ast.FunctionDef):
            n.name = nm(n.name)
        elif isinstance(n, ast.arg):
            n.arg = nm(n.arg)
    return t


def run_src(src: str) -> str | None:
    buf = io.StringIO()

    def _al(s: Any, f: Any) -> None:
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, _al)
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<m>", "exec"), {"__name__": "__m__"})  # noqa: S102
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    finally:
        signal.signal(signal.SIGALRM, old)
    t = buf.getvalue()
    return t[:-1] if t.endswith("\n") and t.count("\n") == 1 else None


def mut(src: str, fn: Any) -> str | None:
    """Run a mutated copy: ``fn(tree)`` edits the parsed tree in place."""
    before = ast.unparse(ast.parse(src))
    t = ast.parse(src)
    fn(t)
    ast.fix_missing_locations(t)
    after = ast.unparse(t)
    return None if after == before else run_src(after)  # a mutation that changed nothing does not apply


def regex_run(src: str, pat: str, rep: str) -> str | None:
    old = ast.unparse(ast.parse(src))
    new = re.sub(pat, rep, old)
    return None if new == old else run_src(new)


class DropIf(ast.NodeTransformer):
    def __init__(self, pat: str, keep_else: bool = True) -> None:
        self.pat, self.keep_else = re.compile(pat), keep_else

    def visit_If(self, n: ast.If) -> Any:
        self.generic_visit(n)
        if self.pat.search(ast.unparse(n.test)):
            n.body = [ast.Pass()]
        return n


class DropMod(ast.NodeTransformer):
    """Replace every ``x % k`` where k is a constant by x (the 'ignore the modulus' attempt)."""

    def visit_BinOp(self, n: ast.BinOp) -> Any:
        self.generic_visit(n)
        if isinstance(n.op, ast.Mod) and isinstance(n.right, ast.Constant):
            return n.left
        return n


def max_suffix(xs: list[int]) -> int:
    best, s = None, 0
    for v in reversed(xs):
        s += v
        best = s if best is None or s > best else best
    return best if best is not None else 0


def max_sub(xs: list[int]) -> int:
    return max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1))


def is_prime(k: int) -> bool:
    return k >= 2 and all(k % d for d in range(2, int(k**0.5) + 1))


def first_int(pat: str, src: str) -> int | None:
    m = re.search(pat, src)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ lineage-specific shapes and rules
Rules = dict[str, str | None]


def specific(lid: str, src: str, tree: ast.Module) -> tuple[str, Rules]:  # noqa: C901
    L: Rules = {}
    ints = ints_in_order(tree)
    lists = int_lists(tree)
    ts = top_sets(tree)
    ss = strs(tree)
    pn = print_name(tree)
    last = src.strip().splitlines()[-1]
    sh = "?"
    name = lid.replace("C1.", "")
    if name == "while_counter_f3":
        if "!= 1" in src:
            sh = "collatz"
            x0 = ints[0]
            vals, x = [], x0
            while x != 1:
                vals.append(x)
                x = x // 2 if x % 2 == 0 else 3 * x + 1
            before = sum(vals)
            L["C.algorithm_rerun_after"] = str(before - x0 + 1)  # control: the trajectory sum when acc is added AFTER the update (the program does this in half of the items)
            L["C.algorithm_rerun_before"] = str(before)  # control: when acc is added BEFORE the update
            L["S.peak"] = str(max(vals))
            L["S.steps"] = str(len(vals))
            L["S.sum_even_only"] = str(sum(v for v in vals if v % 2 == 0))
        elif re.search(r"while \w+ < (\d+):", src):
            sh = "grow"
            thr = int(re.search(r"while \w+ < (\d+):", src).group(1))
            mm = re.search(r"= \w+ \* (\d+) \+ \w+ % (\d+) \+ (\d+)", src)
            mlt, c = int(mm.group(1)), int(mm.group(3))
            x = ints[0]
            while x < thr:
                x = x * mlt + c
            L["S.no_remainder_term"] = str(x)  # the audit's logarithm/geometric formula, exact for x -> m x + c
            L["S.threshold"] = str(thr)
            x = ints[0]
            k = max(0, math.ceil(math.log(thr / x) / math.log(mlt)))
            L["S.geometric_closed_form"] = str(x * mlt**k + c * (mlt**k - 1) // (mlt - 1))
        else:
            sh = "down"
            thr = int(re.search(r"while \w+ > (\d+):", src).group(1))
            d = int(re.search(r"= \w+ - (\d+)\n", src).group(1))
            x0 = ints[0]
            x, acc = x0, 0
            while x > thr:  # ignore the halving: subtract d every round
                x -= d
                acc += x
            L["S.subtract_only"] = str(acc)
            L["S.shrink_closed_form"] = str(x0 - d * math.ceil((x0 - thr) / d))
            x, acc = x0, 0
            while x > thr:  # halve every round
                x //= 2
                acc += x
            L["S.halve_only"] = str(acc)
    elif name == "euclid_gcd_traced_f3":
        x, y = ints[0], ints[1]
        sh = "state" if "' '" in last else "rsum"
        p, q, qs, st, rs = x, y, [], [], []
        while q:
            qs.append(p // q)
            p, q = q, p % q
            st.append((p, q))
            rs.append(q)
        R = int(re.search(r"< (\d+):", src).group(1))
        L["S.gcd_pair"] = f"{math.gcd(x, y)} 0"
        L["S.literal_pair"] = f"{x} {y}"
        if sh == "rsum":
            L["S.sum_all_remainders"] = str(sum(rs))
            L["S.sum_remainders_R_plus_1"] = str(sum(rs[: R + 1]))
            L["S.sum_remainders_R_minus_1"] = str(sum(rs[: max(R - 1, 0)]))
            L["S.sum_quotients_R"] = str(sum(qs[:R]))
            L["S.literal_y"] = str(y)
            L["C.algorithm_rerun"] = str(sum(rv * (k + 2) for k, rv in enumerate(rs[:R])))  # each remainder times (round number + 1)
        else:
            L["S.state_one_more_round"] = f"{st[R][0]} {st[R][1]}" if R < len(st) else None
            L["S.state_one_less_round"] = f"{st[R - 2][0]} {st[R - 2][1]}" if R >= 2 else f"{x} {y}"
            L["C.algorithm_rerun"] = f"{st[R - 1][0]} {st[R - 1][1]}"
    elif name == "cond_chain_f3":
        a0, b0 = ints[0], ints[1]
        sh = "tot"
        k = int(re.search(r"range\((\d+)\)", src).group(1))
        g = math.gcd(a0, b0)
        L["S.k_times_gcd"] = str(k * g)
        L["S.k_times_2gcd"] = str(2 * k * g)
        L["S.gcd"] = str(g)
        L["S.k_times_literal_a"] = str(k * a0)
        L["S.k_times_literal_b"] = str(k * b0)
        L["S.no_halving"] = mut(src, DropIf(r"> \d+$").visit) if "// 2" in src else None
        L["S.no_halving"] = None if L["S.no_halving"] == pn else L["S.no_halving"]
    elif name == "fast_power_f3":
        res_n, b_n, e_n, m_n = (n for n, _ in ts[:4])
        vals = {n: lit(v) for n, v in ts}
        B0, E0, M0 = vals[b_n], vals[e_n], vals[m_n]
        sh = "res" if pn == res_n else ("base" if pn == b_n else "bsum")
        bl = E0.bit_length()
        L["S.pow"] = str(pow(B0, E0, M0)) if sh == "res" else None
        L["S.pow_base_final"] = str(pow(B0, 2**bl, M0)) if sh == "base" else None
        L["S.pow_bsum"] = str(sum(pow(B0, 2**k, M0) for k in range(bl))) if sh == "bsum" else None
        L["S.no_c_term"] = regex_run(src, r"\((\w+) \* (\w+) \+ \d+\) % ", r"(\1 * \2) % ")
        L["S.pow_any"] = str(pow(B0, E0, M0))
    elif name == "digit_peel_f3":
        x = ints[0]
        dd = [int(c) for c in str(x)][::-1]  # decimal digits, least significant first
        sh = "wsum" if "+= " in src and re.search(r"\+= \w+ \* \w+\n", src) else "fold"
        if sh == "fold":
            k = int(re.search(r"= \w+ \* (\d+) \+ \w+\n", src).group(1))
            acc = 0
            for d in dd:
                acc = acc * k + d
            L["S.decimal_digits_fold"] = str(acc)
            acc = 0
            for d in reversed(dd):
                acc = acc * k + d
            L["S.decimal_digits_fold_msd"] = str(acc)
            L["S.literal"] = str(x)
        else:
            L["S.decimal_digits_wsum"] = str(sum(d * (i + 1) for i, d in enumerate(dd)))
            L["S.decimal_digits_wsum_msd"] = str(sum(d * (i + 1) for i, d in enumerate(reversed(dd))))
    elif name == "partition_pass_f3":
        vals = lists[0]
        rng = re.search(r"range\((\d+)\)", src)
        m1 = int(rng.group(1)) if rng else 0
        op = re.search(r"if \w+\[\w+\] (<=|<) \w+:", src).group(1)
        piv = vals[m1]
        small = lambda v: v <= piv if op == "<=" else v < piv  # noqa: E731
        lo = [v for v in vals[:m1] if small(v)]
        hi = [v for v in vals[:m1] if not small(v)]
        if "+=" in src and "range" in src and "tot" not in src.split("\n")[-1] and not src.strip().splitlines()[-1].startswith("print([") and pn is not None and pn != ts[0][0]:
            sh = "disp"
        elif pn == ts[0][0]:
            sh = "list" if re.search(r"\[\w+ \+ 1\] = ", src) else "mid"
        else:
            sh = "disp"
        if sh == "disp":
            L["S.sum_larger"] = str(sum(hi))
            L["S.sum_smaller"] = str(sum(lo))
            L["S.sum_first"] = str(vals[0])
            L["S.sum_larger_minus_first"] = str(sum(hi) - vals[0])
        else:
            L["S.sorted_prefix"] = str(sorted(vals[: m1 + 1]) + vals[m1 + 1 :])
            L["S.stable_partition"] = str(lo + [piv] + hi + vals[m1 + 1 :]) if sh == "list" else str(lo + hi + [piv] + vals[m1 + 1 :])
            L["S.stable_partition_nopivot"] = str(lo + hi + vals[m1:])
    elif name == "merge_two_sorted_f3":
        a, b = lists[0], lists[1]
        op = "<=" if re.search(r"if \w+\[\w+\] <= ", src) else "<"
        sh = "diffsum" if re.search(r"\+= \w+\[\w+\] - \w+\[\w+\]", src) else "maxsum"
        i = j = 0
        heads: list[tuple[int, int]] = []
        while i < len(a) and j < len(b):
            heads.append((a[i], b[j]))
            if (a[i] <= b[j]) if op == "<=" else (a[i] < b[j]):
                i += 1
            else:
                j += 1
        L["C.algorithm_rerun"] = str(sum(x - y for x, y in heads)) if sh == "diffsum" else str(sum(max(x, y) for x, y in heads))
        # closed-form attempts that do not follow the pointers
        k = min(len(a), len(b))
        if sh == "diffsum":
            L["S.sum_a_minus_sum_b"] = str(sum(a) - sum(b))
            L["S.first_heads_times_steps"] = str((a[0] - b[0]) * (len(a) + len(b) - 1))
            L["S.zip_heads"] = str(sum(a[q] - b[q] for q in range(k)))
            L["S.mean_diff_times_steps"] = str((sum(a) // len(a) - sum(b) // len(b)) * (len(a) + len(b) - 1))
        else:
            full = sorted(a + b)
            L["S.sorted_tail_sum"] = str(sum(full[len(full) // 2 :]))
            L["S.zip_max"] = str(sum(max(a[q], b[q]) for q in range(k)))
            L["S.sum_all_minus_min"] = str(sum(a + b) - min(a + b))
            L["S.max_head_times_steps"] = str(max(a[0], b[0]) * (len(a) + len(b) - 1))
    elif name == "sieve_marking_f3":
        fl = lists[0]
        n = len(fl)
        sh = "flags" if pn == ts[0][0] else "strikesum"
        allones = src.replace(str(fl), str([1] * n), 1)
        if sh == "strikesum":
            L["S.all_ones_start"] = run_src(allones)
        else:
            L["S.all_ones_start"] = run_src(allones)
            L["S.primes_only"] = str([f if (k < 2 or is_prime(k)) else 0 for k, f in enumerate(fl)])
            L["S.input_echo"] = str(fl)
            L["S.flagged_composites_struck"] = str([f if (k < 2 or is_prime(k)) else 0 for k, f in enumerate(fl)])
    elif name == "binary_search_f3":
        vals, t = lists[0], ints[len(lists[0])]
        closed = "<=" in re.search(r"while (.*):", src).group(1)
        sh = "probes" if "str(" in src else ("path" if "''" in src else "sum")
        sh += "_closed" if closed else "_half"
        bl = bisect_left(vals, t)
        if sh.startswith("sum"):
            L["S.target_if_present"] = str(t) if t in vals else None
            L["S.value_at_bisect"] = str(vals[bl]) if bl < len(vals) else None
        elif sh.startswith("path"):
            L["S.all_l"] = "l" * bl
            L["S.all_r"] = "r" * (len(vals) - bl)
        else:
            L["S.mid_only"] = f"{(len(vals) - 1) // 2},"
    elif name == "kadane_scan_f3":
        vals = lists[0]
        sh = "curs" if re.search(r"\+= \w+\n", src) else "cur"
        L["S.kadane_cur"] = str(max_suffix(vals)) if sh == "cur" else None
        L["S.kadane_curs"] = str(sum(max_suffix(vals[: i + 1]) for i in range(1, len(vals)))) if sh == "curs" else None
        L["S.thr0_run"] = regex_run(src, r"if (\w+) < \(-\d+\):", r"if \1 < 0:")
        L["S.max_elem"] = str(max(vals))
        L["S.sum_pos"] = str(sum(v for v in vals if v > 0))
        L["S.sum_all"] = str(sum(vals))
        L["S.last_elem"] = str(vals[-1])
        L["S.sum_suffix_from_last_negative"] = str(sum(vals[max(i for i in range(len(vals)) if vals[i] < 0) + 1 :]) if any(v < 0 for v in vals) else sum(vals))
    elif name == "majority_vote_scan_f3":
        vals = lists[0]
        m_last = re.search(r"\n(\s+)(\w+) \+= (\w+)\nprint", src)
        take_adds = re.search(r"= 1\n\s+\w+ \+= \w+\n", src) is not None
        if take_adds:
            sh = "repl"
        else:
            nm_add = m_last.group(3) if m_last else ""
            sh = "cntsum" if re.search(r"-= 1\n\s+\w+ \+= " + re.escape(nm_add) + r"\nprint", src + "\n") and nm_add == ts[2][0] else "candsum"
        n = len(vals)
        L["S.first_elem"] = str(vals[0])
        L["S.sum_distinct"] = str(sum(set(vals)))
        L["S.first_plus_last"] = str(vals[0] + vals[-1])
        L["S.n_times_last"] = str(n * vals[-1])
        L["S.n_times_mode"] = str(n * Counter(vals).most_common(1)[0][0])
        L["S.n"] = str(n)
        L["S.n_times_half"] = str(n * (n + 1) // 4)
    elif name == "counter_list_f3":
        vals, k = lists[0], len(lists[1])
        sh = "counts"
        mul = int(re.search(r"= \(\w+ \* (\d+) \+ \w+\) % \d+", src).group(1))
        c = [0] * k
        for v in vals:
            c[v % k] += 1
        L["S.residue_histogram"] = str(c)
        st, c2 = 0, [0] * k
        for v in vals:
            st = (st + v) % k
            c2[st] += 1
        L["S.prefix_sum_histogram"] = str(c2)
        L["S.uniform"] = str([len(vals) // k + (1 if q < len(vals) % k else 0) for q in range(k)])
        thr_m = re.search(r"if \w+ > (\d+):", src)
        st, c3 = 0, [0] * k
        for v in vals:
            if "% 2 == 0" in src:
                st = (st * mul + v) % k if v % 2 == 0 else (st + 1 + v // 2) % k
            elif thr_m:
                st = (st * mul + v) % k if v > int(thr_m.group(1)) else (st + mul) % k
            else:
                st = (st * mul + v) % k
            c3[st] += 1
        L["C.self_check"] = str(c3)  # must be 1.0: the intended answer, to show the rule parser is right
        # the first draft's machine (one style, no branch) applied to every item
        st, c4 = 0, [0] * k
        for v in vals:
            st = (st * mul + v) % k
            c4[st] += 1
        L["S.plain_machine"] = str(c4) if ("% 2 == 0" in src or thr_m) else None  # only where the program branches: otherwise it is the program
    elif name == "list_build_f3":
        sh = "wsum" if re.search(r"\+= \w+ \* \w+\[", src) else ("sum" if "sum(" in last else "list")
        m = int(re.findall(r"% (\d+)\)", src)[-1]) if re.findall(r"% (\d+)\)", src) else 1
        n = int(re.search(r"range\((\d+)\)", src).group(1))
        L["S.n_times_half"] = str(n * (m - 1) // 2)
        L["S.n_times_m"] = str(n * m)
    elif name == "nested_pairs_f3":
        sh = "count"
        rs = [int(v) for v in re.findall(r"range\((\d+)\)", src)]
        a = rs[0]
        b = rs[1] if len(rs) > 1 else None
        L["S.a_times_b"] = str(a * b) if b else None
        L["S.half_pairs"] = str(a * b // 2) if b else None
        L["S.run_inc_1"] = regex_run(src, r"\+= .*\n", "+= 1\n") if "+= " in src else None
    elif name == "bracket_matching_f3":
        s = ss[0]
        if re.search(r"range\((\d+)\):\n\s+\w+ = ", src):
            sh = "remain_at"
            p = int(re.search(r"range\((\d+)\):\n\s+\w+ = ", src).group(1))
            pre = s[:p]
        else:
            pre = s
            sh = "code" if "* 10" in last else ("remain" if "[0:" in last else ("popsum_or_errpos"))
            if sh == "popsum_or_errpos":
                # the accumulator is added in the 'hit' or the 'fail' branch
                sh = "popsum" if re.search(r"-= 1\n\s+\w+ \+= \w+\n", src) else "errpos"
        opens = [c for c in pre if c in "([{<"]
        closers = [(i, c) for i, c in enumerate(pre) if c in ")]}>"]
        code_of = {"(": 1, "[": 2, "{": 3, "<": 4, ")": 1, "]": 2, "}": 3, ">": 4}
        if sh == "code":
            L["S.naive_height"] = str(10 * 0 + max(0, len(opens) - len(closers)))
            L["S.ignore_kinds_code"] = None
        elif sh in ("remain", "remain_at"):
            L["S.all_opens"] = str([code_of[c] for c in opens])
            st: list[int] = []  # a stack that pops on any closer
            for c in pre:
                if c in "([{<":
                    st.append(code_of[c])
                elif st:
                    st.pop()
            L["S.pop_any_closer"] = str(st)
            L["S.empty"] = "[]"
        elif sh == "popsum":
            L["S.sum_all_closers"] = str(sum(i for i, _ in closers))
            st = []
            tot = 0
            for i, c in enumerate(pre):
                if c in "([{<":
                    st.append(code_of[c])
                elif st:
                    st.pop()
                    tot += i
            L["S.pop_any_closer"] = str(tot)
        else:
            L["S.zero"] = "0"
            L["S.sum_all_closers"] = str(sum(i for i, _ in closers))
    elif name == "union_find_links_f3":
        sh = "parents" if (pn is not None and pn == "p") else None
        sh = "parents" if "print(" in last and "(" not in last[6:-1] and re.search(r"^print\(\w+\)$", last) and not re.search(r"\+= ", src.split("find(")[-1].split("for k")[-1]) and "tot" not in last else "tot"
        if re.search(r"\+= find\(", src):
            sh = "rootsum"
        elif re.search(r"\+= \w+ \* \w+\[", src):
            sh = "wsum"
        else:
            sh = "parents"
        n = len(lists[0])
        pu, pv = lists[1], lists[2]
        par = list(range(n))

        def find(z: int) -> int:
            while par[z] != z:
                z = par[z]
            return z

        naive = list(range(n))
        for u, w in zip(pu, pv, strict=True):  # link the nodes themselves (not their roots), 'second under first'
            naive[w] = u
        L["S.identity"] = str(list(range(n))) if sh == "parents" else (str(sum(range(n))) if sh == "rootsum" else str(sum(k * k for k in range(n))))
        L["S.naive_node_links"] = str(naive) if sh == "parents" else (str(sum(naive[k] for k in range(n))) if sh == "rootsum" else str(sum(k * naive[k] for k in range(n))))
        L["S.zero"] = "0"
    elif name == "shared_lists_f3":
        sh = "list" if re.search(r"^print\(\w+\)$", last) else ("sum" if "sum(" in last else ("len" if "len(" in last else "at"))

        class Copyish(ast.NodeTransformer):
            def visit_Assign(self, n: ast.Assign) -> Any:
                self.generic_visit(n)
                if isinstance(n.value, ast.Name):
                    n.value = ast.Subscript(value=n.value, slice=ast.Slice(), ctx=ast.Load())
                return n

            def visit_FunctionDef(self, n: ast.FunctionDef) -> Any:
                self.generic_visit(n)
                if n.args.args and any(isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Subscript) for s in n.body):
                    p = n.args.args[0].arg
                    n.body.insert(0, ast.parse(f"{p} = {p}[:]").body[0])
                return n

        L["S.naive_copy"] = mut(src, Copyish().visit)
    elif name == "bytecode_loop_f3":
        code = lists[0]
        sh = "sumarg" if re.search(r"\n\s+\w+ \+= \w+\n\s+if ", src) else "other"
        L["S.sum_all_args"] = str(sum(code[1::2]))
        L["S.no_skips"] = mut(src, DropIf(r"% 2 == \w+ % 2").visit)
        L["S.always_skip"] = regex_run(src, r"if (\w+) % 2 == (\w+) % 2:", "if True:")
    elif name == "turtle_walk_f3":
        cmds = lists[0]
        sh = "pos" if "','" in last else "pathsum"
        L["S.sum_forward"] = str(sum(c for c in cmds if c <= 3)) if sh != "pos" else None
        L["S.zero"] = "0,0" if sh == "pos" else "0"
        L["S.no_turns"] = mut(src, lambda t: DropAssign(r"% 4$").visit(t))
        L["S.no_back"] = mut(src, DropIf(r"== 6$").visit) if 6 in cmds else None
    elif name == "cellular_update_f3":
        init = lists[0]
        sh = "row" if re.search(r"^print\(\w+\)$", last) else "weighted"
        L["S.echo_init"] = str(init) if sh == "row" else str(sum(i * v for i, v in enumerate(init)))
        L["S.all_zero"] = str([0] * len(init)) if sh == "row" else "0"
        L["S.all_one"] = str([1] * len(init)) if sh == "row" else str(sum(range(len(init))))
    elif name == "func_compose_f3":
        sh = "mod" if "%" in src.split("def")[-1] and re.search(r"return \w+\(\w+\) % \d+", src) else "plain"
        L["S.no_mod"] = regex_run(src, r"return (\w+\(\w+\)) % \d+", r"return \1") if sh == "mod" else None
        L["S.single_call_arg"] = None
    elif name in ("fib_like_f3", "fib_shapes_recursive_f3"):
        sh = "all"
        L["S.no_mod"] = mut(src, DropMod().visit)
        if name == "fib_like_f3":
            n = int(re.search(r"range\((\d+)\)", src).group(1))
            a, b = ints[0], ints[1]
            for _ in range(n):
                a, b = b, a + b
            L["S.plain_fibonacci_a"] = str(a)
            L["S.plain_fibonacci_b"] = str(b)
    elif name == "string_methods_f3":
        sh = "text"
        w = ss[0]
        L["S.word_lower"] = w.lower()
        L["S.word_rev_lower"] = w.lower()[::-1]
        L["S.word_lower_alt"] = w.lower()[::2]
        L["S.word_lower_tail"] = w.lower()[1:]
    elif name == "string_build_f3":
        sh = "s" if re.search(r"^print\(\w+\)$", last) else ("rev" if "::(-1)]" in last or "::-1" in last else "alt")
        L["S.ignore_step"] = regex_run(src, r"range\((\d+), (\d+), 2\)", r"range(\1, \2)") if ", 2)" in src else None
    return sh, L


def bisect_left(vals: list[int], t: int) -> int:
    lo, hi = 0, len(vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if vals[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


class DropAssign(ast.NodeTransformer):
    def __init__(self, pat: str) -> None:
        self.pat = re.compile(pat)

    def visit_Assign(self, n: ast.Assign) -> Any:
        if self.pat.search(ast.unparse(n)):
            return ast.Pass()
        return n


def generic_preds(src: str, tree: ast.Module) -> Rules:
    P: Rules = {}
    ints = ints_in_order(tree)
    for k in range(10):
        P[f"lit{k}"] = str(ints[k]) if k < len(ints) else None
        P[f"litr{k + 1}"] = str(ints[-k - 1]) if k < len(ints) else None
    lists = int_lists(tree)
    ss = strs(tree)
    if lists:
        x = lists[0]
        P["L.len"], P["L.sum"], P["L.max"], P["L.min"], P["L.echo"] = str(len(x)), str(sum(x)), str(max(x)), str(min(x)), str(x)
        for k in range(4):
            P[f"L.e{k}"] = str(x[k]) if k < len(x) else None
            P[f"L.er{k + 1}"] = str(x[-k - 1]) if k < len(x) else None
        P["L.sorted"] = str(sorted(x))
        P["L.rsorted"] = str(sorted(x, reverse=True))
        P["L.reversed"] = str(x[::-1])
    if ss:
        P["S0.echo"], P["S0.len"], P["S0.rev"] = ss[0], str(len(ss[0])), ss[0][::-1]
    if len(ints) >= 2:
        for a in range(min(6, len(ints))):
            for b in range(a + 1, min(6, len(ints))):
                x, y = ints[a], ints[b]
                P[f"pair{a}{b}.sum"], P[f"pair{a}{b}.diff"], P[f"pair{a}{b}.prod"] = str(x + y), str(abs(x - y)), str(x * y)
                P[f"pair{a}{b}.gcd"] = str(math.gcd(x, y))
                P[f"pair{a}{b}.mod"] = str(x % y) if y else None
                P[f"pair{a}{b}.floordiv"] = str(x // y) if y else None
    P["const0"], P["const1"], P["constm1"] = "0", "1", "-1"
    return P


def lit_set(tree: ast.Module) -> set[str]:
    return {str(v) for v in ints_in_order(tree)}


# ------------------------------------------------------------------ drawing and evaluation
def rng_for(seed: int, lid: str, lv: int) -> random.Random:
    d = hashlib.sha256(f"fix3-battery|{seed}|{lid}|{lv}".encode()).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def all_lineages() -> dict[str, Any]:
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_fix3 import load_fix3
    from studies.m0.lineages_c1_rev2 import load_rev2

    return {x.id: x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2(), *load_fix3()]}


def draw(lid: str, seed: int, per_level: int) -> list[dict[str, Any]]:
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry

    lin = all_lineages()[lid]
    rows = []
    for lv in range(7):
        r = rng_for(seed, lid, lv)
        for i in range(per_level):
            tries = 0
            while True:
                tries += 1
                if tries > 500:
                    raise RuntimeError(f"{lid} L{lv}: 500 retries")
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            rows.append({"lid": lid, "lv": lv, "i": i, "src": render(b.structured["program"]), "key": b.answer, "retries": tries - 1})
    return rows


def cv_mf(items: list[dict[str, Any]], keyf: Any) -> float:
    hit = 0
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        tab: dict[Any, Counter[str]] = defaultdict(Counter)
        for x in train:
            tab[keyf(x)][x["key"]] += 1
        for x in test:
            c = tab.get(keyf(x))
            if c:
                best = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                hit += best == x["key"]
    return hit / max(1, len(items))


def cv_best_generic(items: list[dict[str, Any]]) -> tuple[float, list[str]]:
    rules = sorted({r for x in items for r in x["G"]})
    hit, chosen = 0, []
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        sc = {r: sum(1 for x in train if x["G"].get(r) == x["key"]) for r in rules}
        best = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        chosen.append(best)
        hit += sum(1 for x in test if x["G"].get(best) == x["key"])
    return hit / max(1, len(items)), chosen


def evaluate(args: tuple[str, int, int]) -> tuple[str, dict[str, Any]]:
    lid, seed, per_level = args
    rows = draw(lid, seed, per_level)
    recs = []
    for row in rows:
        tree = ast.parse(row["src"])
        try:
            sh, S = specific(lid, row["src"], tree) if lid.endswith("_f3") else ("all", {})
        except Exception as ex:  # a parse slip in a rule must be visible, not silent
            sh, S = "RULE_ERROR:" + type(ex).__name__ + ":" + str(ex)[:60], {}
        recs.append({"lv": row["lv"], "i": row["i"], "key": row["key"], "shape": sh, "S": S, "G": generic_preds(row["src"], tree), "lits": row["key"] in lit_set(tree)})
    per: dict[str, Any] = {}
    for lv in range(7):
        its = [x for x in recs if x["lv"] == lv]
        n = len(its)
        shapes = Counter(x["shape"] for x in its)
        srules: dict[str, Any] = {}
        for shp in sorted(shapes):
            sub = [x for x in its if x["shape"] == shp]
            for rn in sorted({r for x in sub for r in x["S"]}):
                k = sum(1 for x in sub if x["S"].get(rn) is not None and x["S"][rn] == x["key"])
                srules[f"{shp}|{rn}"] = {"hit": k, "n_shape": len(sub), "rate": round(k / len(sub), 3)}
        bg, ch = cv_best_generic(its)
        mf_shape = {shp: round(cv_mf([x for x in its if x["shape"] == shp], lambda x: 0), 3) for shp in sorted(shapes) if shapes[shp] >= 20}
        # generic rules inside each shape (every literal/list/pair rule, not cross-validated: an upper bound for a fixed rule)
        gmax: dict[str, Any] = {}
        for shp in sorted(shapes):
            sub = [x for x in its if x["shape"] == shp]
            if len(sub) < 20:
                continue
            sc = Counter()
            for x in sub:
                for rn, pv in x["G"].items():
                    if pv is not None and pv == x["key"]:
                        sc[rn] += 1
            if sc:
                rn, k = sc.most_common(1)[0]
                gmax[shp] = {"rule": rn, "rate": round(k / len(sub), 3)}
            else:
                gmax[shp] = {"rule": None, "rate": 0.0}
        per[str(lv)] = {"n": n, "MF_cv": round(cv_mf(its, lambda x: 0), 3), "MF_shape_cv": mf_shape, "BEST_generic_cv": round(bg, 3), "BEST_generic_chosen": ch,
                        "best_generic_in_shape": gmax, "oracle_any_literal": round(sum(x["lits"] for x in its) / n, 3), "shapes": dict(shapes), "S": srules,
                        "distinct_keys": len({x["key"] for x in its}), "retries": sum(r["retries"] for r in rows if r["lv"] == lv)}
    return lid, per


def summarise(res: dict[str, Any]) -> str:
    lines = ["lineage | worst rule in shape (rate, level) | worst generic in shape | MF_cv max over levels | MF|shape max | BEST generic max | any-literal oracle max", "---|---|---|---|---|---|---"]
    for lid in sorted(res):
        p = res[lid]
        worst = (0.0, "-", -1)
        gw = (0.0, "-", -1)
        mfs = 0.0
        for lv in range(7):
            c = p[str(lv)]
            for k, v in c["S"].items():
                if "|C." in k:
                    continue
                if v["rate"] > worst[0]:
                    worst = (v["rate"], k, lv)
            for shp, g in c["best_generic_in_shape"].items():
                if g["rate"] > gw[0]:
                    gw = (g["rate"], f"{shp}|{g['rule']}", lv)
            for shp, mv in c["MF_shape_cv"].items():
                mfs = max(mfs, mv)
        mf = max(p[str(lv)]["MF_cv"] for lv in range(7))
        bg = max(p[str(lv)]["BEST_generic_cv"] for lv in range(7))
        orc = max(p[str(lv)]["oracle_any_literal"] for lv in range(7))
        lines.append(f"{lid} | {worst[0]:.2f} {worst[1]} L{worst[2]} | {gw[0]:.2f} {gw[1]} L{gw[2]} | {mf:.2f} | {mfs:.2f} | {bg:.2f} | {orc:.2f}")
    return "\n".join(lines)


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level", type=int, default=400)
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    from studies.m0.lineages_c1_fix3 import load_fix3

    ids = [x.id for x in load_fix3()]
    if a.only:
        ids = a.only.split(",")
    res: dict[str, Any] = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, per in ex.map(evaluate, [(i, a.seed, a.per_level) for i in ids]):
            res[lid] = per
            print(lid, "done", flush=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(summarise(res))


if __name__ == "__main__":
    main()
