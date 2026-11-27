# ruff: noqa: E501
"""Shortcut check for the C1 batch-1 lineages (lineage repair; measurement only, no threshold is registered here).

For every lineage and each of the seven levels it draws 2,000 DISTINCT items (``core.draw_items``, the same uniqueness rule the pools use) and
scores trivial heuristics that do not trace the program: the constant most-frequent answer; a numeric or string literal of the source taken
by position (first, last, largest, smallest, most frequent); the printed variable's initial value echoed; the first flat list literal's first,
last, sum, length, maximum, minimum, mode, sum of positives, sorted and reversed form; the first string literal's length, its reverse and
its character counts; the first string literal itself; and one lineage-specific guess where a tempting one is known. The 'oracle' rows
are upper bounds over several guesses (the answer is ANY literal of the source; the answer is ANY list statistic of ANY list literal) and
are reported as coverage, not as the accuracy of one rule. The reference for 'far above' is the constant most-frequent-answer rate of the same
lineage and level. Source text is only parsed (``ast.parse``), never executed here.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_shortcut_check [--per-level 2000]``.
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from studies.m0.c1grammar import render
from studies.m0.core import ALL_LEVELS, Item, draw_items, stream
from studies.m0.lineages_c1_common import load_batch1

ROOT = Path(__file__).resolve().parents[2]
SEED = 953701  # test block 953001-953999
Guess = Callable[["Facts"], str | None]


class Facts:
    """What a non-tracing reader can see in the source."""

    def __init__(self, it: Item) -> None:
        src = render(it.structured["program"])
        tree = ast.parse(src)
        key = lambda n: (n.lineno, n.col_offset)  # noqa: E731
        nodes = sorted((n for n in ast.walk(tree) if hasattr(n, "lineno")), key=key)
        self.nums: list[int] = []
        self.strs: list[str] = []
        self.lists: list[list[Any]] = []
        for n in nodes:
            if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
                self.nums.append(n.value)
            elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) and isinstance(n.operand.value, int):
                self.nums.append(-n.operand.value)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                self.strs.append(n.value)
            if isinstance(n, ast.List):
                try:
                    v = ast.literal_eval(n)
                except (ValueError, TypeError):
                    continue
                self.lists.append(v)
        self.flat = [x for x in self.lists if x and all(isinstance(e, int) for e in x)]
        # the printed variable's first literal assignment
        self.echo: str | None = None
        pr = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"]
        if pr and isinstance(pr[0].args[0], ast.Name):
            nm = pr[0].args[0].id
            for st in tree.body:
                if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name) and st.targets[0].id == nm:
                    try:
                        self.echo = str(ast.literal_eval(st.value))
                    except (ValueError, TypeError):
                        self.echo = None
                    break
        self.it = it


def _mode(xs: list[int]) -> int:
    c = Counter(xs)
    return min(c, key=lambda k: (-c[k], k))


def list_stats(xs: list[int]) -> dict[str, str]:
    return {"first": str(xs[0]), "last": str(xs[-1]), "sum": str(sum(xs)), "len": str(len(xs)), "max": str(max(xs)), "min": str(min(xs)), "mode": str(_mode(xs)),
            "posum": str(sum(x for x in xs if x > 0)), "sorted": str(sorted(xs)), "rev": str(xs[::-1]), "sorted_desc": str(sorted(xs, reverse=True))}


def _g_list1(stat: str) -> Guess:
    return lambda f: list_stats(f.flat[0])[stat] if f.flat else None


def _g_str1(kind: str) -> Guess:
    def g(f: Facts) -> str | None:
        if not f.strs:
            return None
        s = f.strs[0]
        return {"len": str(len(s)), "rev": s[::-1], "self": s, "first": s[0] if s else None, "last": s[-1] if s else None}[kind]

    return g


GENERIC: dict[str, Guess] = {
    "lit_first": lambda f: str(f.nums[0]) if f.nums else None,
    "lit_last": lambda f: str(f.nums[-1]) if f.nums else None,
    "lit_max": lambda f: str(max(f.nums)) if f.nums else None,
    "lit_min": lambda f: str(min(f.nums)) if f.nums else None,
    "lit_mode": lambda f: str(_mode(f.nums)) if f.nums else None,
    "echo_printed_initial": lambda f: f.echo,
    **{f"list1_{s}": _g_list1(s) for s in ("first", "last", "sum", "len", "max", "min", "mode", "posum", "sorted", "rev", "sorted_desc")},
    **{f"str1_{k}": _g_str1(k) for k in ("len", "rev", "self", "first", "last")},
}


def oracle_literal(f: Facts, ans: str) -> bool:
    return ans in {str(x) for x in f.nums} or ans in f.strs or ans in {str(x) for x in f.lists}


def oracle_list_stat(f: Facts, ans: str) -> bool:
    return any(ans in list_stats(xs).values() for xs in f.flat) or any(ans == str(len(s)) or ans in {str(s.count(c)) for c in sorted(set(s))} for s in f.strs)


SPECIFIC: dict[str, tuple[str, Guess]] = {
    "C1.binary_search": ("probes_bit_length", lambda f: str(len(f.flat[0]).bit_length()) if f.flat else None),
    "C1.sieve_marking": ("initial_ones", lambda f: str(sum(f.flat[0])) if f.flat else None),
    "C1.majority_vote_scan": ("mode", lambda f: str(_mode(f.flat[0])) if f.flat else None),
    "C1.kadane_scan": ("max_or_posum_larger", lambda f: str(max(max(f.flat[0]), sum(x for x in f.flat[0] if x > 0))) if f.flat else None),
    "C1.insertion_sort": ("sorted_asc", lambda f: str(sorted(f.flat[0])) if f.flat else None),
    "C1.merge_two_sorted": ("sorted_concat", lambda f: str(sorted(f.flat[0] + f.flat[1])) if len(f.flat) > 1 else None),
    "C1.circle_elimination": ("n_minus_1", lambda f: str(len(f.flat[0]) - 1) if f.flat else None),
    "C1.shared_lists": ("value_semantics_first_list", lambda f: str(f.flat[0]) if f.flat else None),
    "C1.mirror_pointers": ("half_length", lambda f: str(len(f.strs[0]) // 2) if f.strs else None),
    "C1.run_length_scan": ("run_count", lambda f: str(1 + sum(1 for a, b in zip(f.strs[0], f.strs[0][1:], strict=False) if a != b)) if f.strs else None),
}


def check_lineage(lin_id: str, items_by_level: dict[int, list[Item]]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for lv, items in items_by_level.items():
        facts = [Facts(it) for it in items]
        ans = [it.answer for it in items]
        n = len(items)
        top_key, top = Counter(ans).most_common(1)[0]
        row: dict[str, Any] = {"n": n, "distinct_answers": len(set(ans)), "constant_top_key": top_key[:30], "constant": round(top / n, 4)}
        guesses = dict(GENERIC)
        if lin_id in SPECIFIC:
            nm, g = SPECIFIC[lin_id]
            guesses["specific:" + nm] = g
        for name, g in sorted(guesses.items()):
            hit = 0
            for f, a in zip(facts, ans, strict=True):
                if g(f) == a:
                    hit += 1
            row[name] = round(hit / n, 4)
        row["oracle_any_literal"] = round(sum(oracle_literal(f, a) for f, a in zip(facts, ans, strict=True)) / n, 4)
        row["oracle_any_list_or_string_statistic"] = round(sum(oracle_list_stat(f, a) for f, a in zip(facts, ans, strict=True)) / n, 4)
        rows[str(lv)] = row
    return rows


def summarise(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Worst single-rule heuristic over the five core levels and over all seven."""
    skip = {"n", "distinct_answers", "constant_top_key", "constant", "oracle_any_literal", "oracle_any_list_or_string_statistic"}
    out: dict[str, Any] = {}
    for label, levels in (("core_1_5", ("1", "2", "3", "4", "5")), ("all_0_6", tuple(str(x) for x in ALL_LEVELS))):
        worst = max(((rows[lv][k], k, lv) for lv in levels for k in rows[lv] if k not in skip), key=lambda t: (t[0], t[1], t[2]))
        const = max((rows[lv]["constant"], lv) for lv in levels)
        out[label] = {"worst_rule_accuracy": worst[0], "worst_rule": worst[1], "worst_rule_level": worst[2], "constant_max": const[0], "constant_max_level": const[1],
                      "oracle_any_literal_max": max(rows[lv]["oracle_any_literal"] for lv in levels), "oracle_stat_max": max(rows[lv]["oracle_any_list_or_string_statistic"] for lv in levels),
                      "distinct_answers_min": min(rows[lv]["distinct_answers"] for lv in levels)}
    return out


def run(per_level: int, only: list[str] | None = None, out_path: Path | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"per_level": per_level, "seed": SEED, "lineages": {}}
    for lin in load_batch1():
        if only and lin.id not in only:
            continue
        by_level = {}
        for lv in ALL_LEVELS:
            rng = stream(SEED, "c1-shortcut", lin.id, str(lv))
            by_level[lv] = draw_items(lin, "A", lv, per_level, rng, set(), "shortcut")
        rows = check_lineage(lin.id, by_level)
        result["lineages"][lin.id] = {"family": lin.family, "levels": rows, "summary": summarise(rows)}
        s = result["lineages"][lin.id]["summary"]["core_1_5"]
        print(f"{lin.id:28s} const {s['constant_max']:.3f}  worst rule {s['worst_rule']} {s['worst_rule_accuracy']:.3f} (L{s['worst_rule_level']})  oracle-literal {s['oracle_any_literal_max']:.3f}  oracle-stat {s['oracle_stat_max']:.3f}  distinct>= {s['distinct_answers_min']}", flush=True)
    if out_path:
        out_path.write_text(json.dumps(result, indent=1, sort_keys=True))
        out_path.with_name(out_path.stem + "_table.md").write_text(table_md(result))
    return result


def table_md(result: dict[str, Any]) -> str:
    """One row per lineage: the constant guess, the worst single rule and the two oracle coverages, maxima over the five core levels, with the all-level constant."""
    lines = [f"# C1 batch 1 shortcut check (measured; {result['per_level']} distinct items per lineage and level, seed {result['seed']})\n",
             "Rates are exact-match accuracies of a rule that does not trace the program. `constant` is the most frequent key of that lineage and level (the reference); `worst rule` is the best single non-constant rule; both are the MAXIMUM over core levels 1-5. `oracle` columns are upper bounds over many guesses (coverage, not one rule). No threshold is registered.\n",
             "| lineage | constant (core max) | constant (all 7 levels max) | worst rule | accuracy | at level | oracle: any literal | oracle: any list/string statistic | min distinct answers |", "|---|---|---|---|---|---|---|---|---|"]
    for lid, v in sorted(result["lineages"].items()):
        c, a = v["summary"]["core_1_5"], v["summary"]["all_0_6"]
        lines.append(f"| {lid} | {c['constant_max']:.3f} | {a['constant_max']:.3f} | {c['worst_rule']} | {c['worst_rule_accuracy']:.3f} | {c['worst_rule_level']} | {c['oracle_any_literal_max']:.3f} | {c['oracle_stat_max']:.3f} | {c['distinct_answers_min']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out")
    a = ap.parse_args()
    run(a.per_level, a.only, Path(a.out) if a.out else None)


if __name__ == "__main__":
    main()
