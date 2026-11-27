# ruff: noqa: E501
"""R2 fix round 4, repair (c): are the levels of a lineage distinct, with difficulty rising by a stated parameter? (R-21, R-25(c)).

This is the implementer's reading of 'distinct', PENDING LEAD REVIEW (no number here is a registered threshold):
- DISTINCT PAIR: for adjacent levels L and L+1 (300 items each, string seeds ``fix4-lv|<name>|<level>``) at least one numeric leaf of the structured form (an integer, a string length, a list length, the largest and
  smallest integer of a list, recursively through the first element of a list) has a two-sample Kolmogorov-Smirnov statistic of at least ``KS_MIN`` = 0.20 (the 0.1% critical value for two samples of 300 is 0.16).
- RISING: the mean of the lineage's STATED parameter (``PARAM`` below, one per lineage) is strictly larger at L+1 than at L.
A lineage has distinct levels if all 6 adjacent pairs are distinct and the parameter rises at every step. The cross-level count of identical normalised question texts (300 draws per level) is reported, not a gate.
Usage: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix4_levels OUT.json [name,name,...]``."""

from __future__ import annotations

import bisect
import json
import math
import random
import re
import statistics
import sys
from collections.abc import Callable
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item, text_hash

KS_MIN = 0.20
N_PER_LEVEL = 300


def _ntok(s: dict[str, Any]) -> float:
    return float(len(re.findall(r"\d+", s["text"])))


PARAM: dict[str, tuple[str, Callable[[dict[str, Any]], float]]] = {
    "binary_search_trace": ("length of the sorted list", lambda s: float(len(s["xs"]))),
    "caesar_shift": ("letters in the text (words)", lambda s: float(len(s["text"]))),
    "cellular_automaton": ("cells in the row", lambda s: float(len(s["row"]))),
    "cheapest_network": ("towns", lambda s: float(len(s["towns"]))),
    "count_divisible": ("numbers in the list", lambda s: float(len(s["xs"]))),
    "crt_smallest": ("mean modulus", lambda s: statistics.mean(m for _c, m in s["congruences"])),
    "dictionary_rank": ("number of words in the dictionary (m falling length)", lambda s: math.log(math.perm(len(s["letters"]), s["length"]))),
    "digit_root": ("the number (log)", lambda s: math.log(s["n"])),
    "expression_eval": ("numbers in the expression", _ntok),
    "to_base_wide": ("the number (log)", lambda s: math.log(s["n"])),
    "from_base": ("digits", lambda s: float(len(s["digits"]))),
    "grid_sum": ("cells", lambda s: float(len(s["grid"]) * len(s["grid"][0]))),
    "interval_scheduling": ("meetings", lambda s: float(len(s["meetings"]))),
    "sort_list": ("numbers in the list", lambda s: float(len(s["xs"]))),
    "list_ops": ("operations", lambda s: float(len(s["ops"]))),
    "luhn_check": ("digits", lambda s: float(len(s["digits"]))),
    "min_heap_ops": ("numbers inserted", lambda s: float(len(s["xs"]))),
    "run_length": ("letters in the string", lambda s: float(len(s["s"]))),
    "string_rewrite_nonidentity": ("letters of the start string", lambda s: float(len(s["s"]))),
    "hamming_error_position": ("bits", lambda s: float(len(s["bits"]))),
    "prime_factor_query": ("the number (log)", lambda s: math.log(s["n"])),
}


def leaves(x: Any, pre: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(x, bool):
        return out
    if isinstance(x, int):
        out[pre] = float(x)
    elif isinstance(x, str):
        out[pre + ".len"] = float(len(x))
    elif isinstance(x, list | tuple):
        out[pre + ".n"] = float(len(x))
        nums = [v for v in x if isinstance(v, int) and not isinstance(v, bool)]
        if nums:
            out[pre + ".max"] = float(max(nums))
            out[pre + ".min"] = float(min(nums))
        if x:
            out.update(leaves(x[0], pre + "[0]"))
    elif isinstance(x, dict):
        for k in sorted(x):
            out.update(leaves(x[k], pre + "/" + str(k)))
    return out


def ks(a: list[float], b: list[float]) -> float:
    sa, sb = sorted(a), sorted(b)
    pts = sorted(set(sa) | set(sb))
    return max(abs(bisect.bisect_right(sa, v) / len(sa) - bisect.bisect_right(sb, v) / len(sb)) for v in pts)


def check(name: str, lin: Any, n: int = N_PER_LEVEL) -> dict[str, Any]:
    desc, fn = PARAM[name]
    per: list[list[dict[str, float]]] = []
    params: list[float] = []
    texts: list[set[str]] = []
    for lv in ALL_LEVELS:
        r = random.Random(f"fix4-lv|{name}|{lv}")
        its = [build_item(lin, lv, r, "A", "x") for _ in range(n)]
        per.append([leaves(i.structured) for i in its])
        params.append(statistics.mean(fn(i.structured) for i in its))
        texts.append({text_hash(i.question) for i in its})
    pairs = []
    for a in range(len(ALL_LEVELS) - 1):
        keys = sorted({k for d in per[a] + per[a + 1] for k in d})
        best = (0.0, "")
        for k in keys:
            va = [d[k] for d in per[a] if k in d]
            vb = [d[k] for d in per[a + 1] if k in d]
            if va and vb:
                v = ks(va, vb)
                if v > best[0]:
                    best = (v, k)
        pairs.append({"pair": f"L{a}-L{a + 1}", "best_ks": round(best[0], 3), "leaf": best[1], "distinct": best[0] >= KS_MIN, "param_rises": params[a + 1] > params[a]})
    dup = sum(len(texts[a] & texts[b]) for a in range(7) for b in range(a + 1, 7))
    return {
        "parameter": desc,
        "parameter_mean_by_level": [round(p, 3) for p in params],
        "pairs": pairs,
        "min_best_ks": min(p["best_ks"] for p in pairs),
        "cross_level_identical_texts": dup,
        "levels_distinct": all(p["distinct"] and p["param_rises"] for p in pairs),
    }


def main() -> None:
    from studies.m0.r2_fix4_set import fix4_set

    s = fix4_set()
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else sorted(PARAM)
    out = {n: check(n, s["R2." + n]) for n in names}
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    for n, v in out.items():
        print(f"{n:30s} distinct={v['levels_distinct']!s:5} min KS {v['min_best_ks']:.2f}  param {v['parameter_mean_by_level']}  cross-level identical texts {v['cross_level_identical_texts']}")


if __name__ == "__main__":
    main()
