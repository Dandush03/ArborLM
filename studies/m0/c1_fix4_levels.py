# ruff: noqa: E501
"""C1 fix 4: do the seven levels of each lineage produce distinct items with rising difficulty? (ruling R-21, repair (c))

Measured from a draw of ``c1_fix4_draw`` (gzip JSONL, one file per lineage), per lineage and level:
  five features of the item's program: steps (executed lines, ``sys.settrace`` line events, 2 s alarm per program), AST nodes, source characters, the largest integer literal, the longest literal list;
  dup_cross  number of items whose normalised question text also occurs at another level of the same lineage (an exact repeat across levels);
  parameter  the level parameter each builder states in its docstring (``STATED_PARAMETER`` below, copied from the builders; not measured).
A level step L -> L+1 is COLLAPSED if either holds (a generator that ignores the level, or ignores it from some level on, produces the first; the second is an exact repeat across levels):
  (1) identity under a shared stream: with the same per-item random stream at L and at L+1 (``shared_stream_identity``, 300 streams), at least 99 per cent of the items are textually identical
      (``MAX_IDENTICAL_SHARE``). Parameter ranges that widen from level to level give a partial identity (the same stream falls in an overlapping range), so a lower share is not a collapse;
  (2) more than 1 per cent of the level's items repeat (normalised question text) at another level (``MAX_CROSS_SHARE``; exact repeats of a few small-state items, at most 1 per cent, are recorded and not counted).
Reported, NOT criteria: the five features' means, the two-sample Kolmogorov-Smirnov statistic of each between consecutive levels (critical value ``KS_CRIT_COEF`` * sqrt((n + m) / (n m)), 0.115 at 400 items per
level, alpha 0.01), the features whose mean is higher at L+1, and the steps at which NO feature reaches the critical value (``weakly_separated``: the stated parameter rises but the five features do not show it at
this sample size). The thresholds 0.99 and 0.01 were chosen after seeing the pre-repair identity shares (100 per cent for the collapsed levels, at most 87 per cent otherwise); no model has been run. A lineage with a
collapsed step is not registrable as it stands (R-21): by R-26 it is dropped, not repaired again, unless the one allowed repair (c) was made in a ``_f4`` file. The five features are a stated, reproducible proxy;
difficulty itself is not claimed to be measured, and the builders' own parameters are listed beside it.

  uv run --locked python -m studies.m0.c1_fix4_levels --gen <draw dir> --out <json> [--ids ...]
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import gzip
import io
import json
import os
import signal
import sys
from typing import Any

from studies.m0.c1_fix4_draw import RULE_ALIAS  # noqa: E402

A4_NAME = {v: k for k, v in RULE_ALIAS.items()}
KS_CRIT_COEF = 1.628  # two-sample KS critical value coefficient at alpha = 0.01
MAX_CROSS_SHARE = 0.01
MAX_IDENTICAL_SHARE = 0.99
IDENTITY_STREAMS = 300
FEATURES = ("steps", "ast_nodes", "chars", "max_literal", "longest_list")

# the parameter by which each builder's difficulty rises with the level, read from the builder (levels 0..6)
STATED_PARAMETER: dict[str, str] = {
    "C1.binary_search_f3": "list length (see the builder)",
    "C1.bracket_matching_f3": "string length and bracket kinds by level (see the builder)",
    "C1.bytecode_loop_f3": "program length by level (see the builder)",
    "C1.circle_elimination_r2": "ring size n = 9 + level (one more flag half the time at level 0)",
    "C1.cond_chain_f3": "rounds 2 + level + (0..2), operand size",
    "C1.counter_list_f3": "list length and machine states by level (see the builder)",
    "C1.digit_peel_f3": "number size by level (see the builder)",
    "C1.euclid_gcd_traced_f3": "operand bound hi = 40, 44, 50, 56, 64, 76, 96 and at least max(4, 3 + level // 2) rounds",
    "C1.fast_power_f4": "exponent bits 3 + level and modulus up to 200 + 60 * level",
    "C1.fib_like_f3": "iterations by level (see the builder)",
    "C1.fib_shapes_recursive_f3": "argument by level (see the builder)",
    "C1.list_build_f3": "length by level (see the builder)",
    "C1.merge_two_sorted_f3": "list lengths by level (see the builder)",
    "C1.nested_pairs_f3": "loop bounds by level (see the builder)",
    "C1.postfix_evaluation": "token count by level (see the builder)",
    "C1.recursive_calls_r2": "argument by level (see the builder)",
    "C1.run_length_scan": "number of runs 3 + level, run length up to 3 + level // 2",
    "C1.shared_lists_f3": "number of operations by level (see the builder)",
    "C1.sieve_marking_f4": "flags n = 30, 34, 38, 42, 46, 50, 56",
    "C1.slices_f4": "string length 2 + level // 2 pseudo-words plus level % 2 letters; list length 6 + level",
    "C1.func_branch_f4": "threshold t up to 12 + 2 * level, arguments up to 20 + 4 * level, multiplier up to 5 + level // 2, offsets up to 9 + level; even branch from level 2; calls 2, 3 from level 3, 4 from level 5",
    "C1.func_compose_f4": "a up to 3 + level, b and c up to 13 + level, argument up to 24 + level, modulus up to 17 + 2 * level (level 3 up); h from level 3; two calls from level 2",
    "C1.string_build_f3": "length by level (see the builder)",
    "C1.string_methods_f3": "chain of 2 + level string operations",
    "C1.turtle_walk_f3": "commands by level (14..26; see the builder)",
    "C1.union_find_links_f3": "nodes 9 + level",
    "C1.while_counter_f3": "iteration bound by level (see the builder)",
}


def _steps(src: str) -> int | None:
    count = 0

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        nonlocal count
        if event == "line":
            count += 1
        return tracer

    def _al(s: int, f: Any) -> None:
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, _al)
    buf = io.StringIO()
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        code = compile(src, "<m>", "exec")
        sys.settrace(tracer)
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, {"__name__": "__m__"})
        finally:
            sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    finally:
        signal.signal(signal.SIGALRM, old)
    return count


def _features(src: str) -> dict[str, float] | None:
    import ast

    tree = ast.parse(src)
    steps = _steps(src)
    if steps is None:
        return None
    lits = [abs(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool)]
    lists = [len(n.elts) for n in ast.walk(tree) if isinstance(n, ast.List)]
    return {"steps": float(steps), "ast_nodes": float(sum(1 for _ in ast.walk(tree))), "chars": float(len(src)), "max_literal": float(max(lits, default=0)), "longest_list": float(max(lists, default=0))}


def ks(a: list[float], b: list[float]) -> float:
    """Two-sample Kolmogorov-Smirnov statistic (stdlib)."""
    xs = sorted(a)
    ys = sorted(b)
    pts = sorted({*xs, *ys})
    i = j = 0
    d = 0.0
    for v in pts:
        while i < len(xs) and xs[i] <= v:
            i += 1
        while j < len(ys) and ys[j] <= v:
            j += 1
        d = max(d, abs(i / len(xs) - j / len(ys)))
    return d


def shared_stream_identity(lid: str, lv: int, n: int = IDENTITY_STREAMS, seed: int = 20261125) -> float:
    """Fraction of ``n`` shared streams for which the builder gives textually identical questions at level ``lv`` and ``lv + 1``."""
    import hashlib
    import random

    from studies.m0.core import Retry
    from studies.m0.lineages_c1_fix4 import all_written

    lin = all_written()[lid]
    same = 0
    for idx in range(n):
        texts = []
        for level in (lv, lv + 1):
            d = hashlib.sha256(f"fix4c1-levels|{seed}|{lid}|{idx}".encode()).digest()
            r = random.Random(int.from_bytes(d[:8], "big"))
            for _ in range(500):
                try:
                    texts.append(lin.build(level, r).question)
                    break
                except Retry:
                    continue
        same += len(texts) == 2 and texts[0] == texts[1]
    return same / n


def measure(fn: str, lid: str = "") -> dict[str, Any]:
    from studies.m0.core import normalise

    rows = [json.loads(line) for line in gzip.open(fn, "rt")]
    by: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["lv"], []).append(r)
    seen: dict[str, set[int]] = {}
    for r in rows:
        seen.setdefault(normalise(r["q"]), set()).add(r["lv"])
    cross = {lv: 0 for lv in by}
    for r in rows:
        if len(seen[normalise(r["q"])]) > 1:
            cross[r["lv"]] += 1
    feats: dict[int, dict[str, list[float]]] = {}
    out: dict[str, Any] = {"levels": {}, "steps": {}}
    for lv in sorted(by):
        fs = [f for f in (_features(r["src"]) for r in by[lv]) if f is not None]
        feats[lv] = {k: [f[k] for f in fs] for k in FEATURES}
        out["levels"][str(lv)] = {"n": len(by[lv]), "items_with_features": len(fs), "dup_cross_level": cross[lv], **{f"mean_{k}": round(sum(v) / len(v), 2) for k, v in feats[lv].items()}}
    collapsed: list[str] = []
    weak: list[str] = []
    for lv in sorted(by)[1:]:
        a, b = feats[lv - 1], feats[lv]
        crit = KS_CRIT_COEF * ((len(a["steps"]) + len(b["steps"])) / (len(a["steps"]) * len(b["steps"]))) ** 0.5
        ksd = {k: round(ks(a[k], b[k]), 3) for k in FEATURES}
        up = [k for k in FEATURES if sum(b[k]) / len(b[k]) > sum(a[k]) / len(a[k])]
        ident = shared_stream_identity(lid, lv - 1) if lid else -1.0
        out["steps"][f"L{lv - 1}->L{lv}"] = {"ks": ksd, "ks_crit": round(crit, 3), "features_with_higher_mean": up, "shared_stream_identical_share": round(ident, 3)}
        if ident >= MAX_IDENTICAL_SHARE:
            collapsed.append(f"L{lv - 1}->L{lv}: {ident:.0%} of shared-stream items are identical")
        if not any(ksd[k] >= crit and k in up for k in FEATURES):
            weak.append(f"L{lv - 1}->L{lv}")
    for lv in sorted(by):
        if cross[lv] > MAX_CROSS_SHARE * len(by[lv]):
            collapsed.append(f"L{lv}: {cross[lv]} of {len(by[lv])} items repeat at another level")
    out["collapsed"] = collapsed
    out["weakly_separated"] = weak
    out["levels_distinct"] = not collapsed
    return out


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--aliased", action="store_true", help="the draw's files for the fix-4 lineages carry the original's name (``RULE_ALIAS``): map them back")
    a = ap.parse_args()
    want = set(a.ids.split(",")) if a.ids else None
    res: dict[str, Any] = {}
    for fn in sorted(glob.glob(os.path.join(a.gen, "*.jsonl.gz"))):
        lid = "C1." + os.path.basename(fn).replace(".jsonl.gz", "")
        lid = A4_NAME.get(lid, lid) if a.aliased else lid
        if want is not None and lid not in want:
            continue
        res[lid] = measure(fn, lid)
        res[lid]["stated_parameter"] = STATED_PARAMETER.get(lid, "")
        print(lid, "distinct" if res[lid]["levels_distinct"] else "COLLAPSED", res[lid]["collapsed"], flush=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
