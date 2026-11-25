# ruff: noqa: E501
"""Shortcut screen for the R2 batch-1 lineages (lineage repair; designed against the pilot's main defect: keys guessable without the procedure).

For every lineage and level 0..6 it draws ``--per-level`` items (default 2,000; seed block 953731) and scores trivial heuristics WITHOUT
solving the task: the constant commonest key (per level and shape), number-token guesses from the question text, and lineage-specific
shortcuts read from the structured form (greedy, home slot, first choice, other convention, naive sum, ...). A heuristic returning ``None``
abstains and is excluded; its accuracy is over the items where it applies (coverage reported). Chance = mean 1/k for closed answers, 0 for open ones.

The screen is the author's, not a registered rule: no threshold is registered here (ruling 5). The flag used in the manifest (a heuristic or constant guess
at or above max(chance + 0.25, 0.30) at any level) is a working rule for authoring decisions only.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_shortcut_check --out <dir>``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, Item, build_item, stream
from studies.m0.lineages_r2_common import load_batch1

SEED = 953731
Heur = Callable[[dict[str, Any]], str | None]
_NUM = re.compile(r"-?\d+")


def lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


def shape_key(s: dict[str, Any]) -> str:
    return "|".join(f"{k}={s[k]}" for k in ("ask", "kind", "convention", "policy") if k in s and not isinstance(s[k], list | dict))


def _ints(s: str) -> list[int]:
    return [int(x) for x in _NUM.findall(s)]


# ---------------------------------------------------------------- lineage-specific heuristics (structured form only)


def _lcs_common(s: dict[str, Any]) -> str:
    a, b = Counter(s["a"]), Counter(s["b"])
    return str(sum(min(a[c], b[c]) for c in sorted(a)))


def _lis_run(s: dict[str, Any]) -> str:
    xs, best, cur = s["xs"], 1, 1
    for i in range(1, len(xs)):
        cur = cur + 1 if xs[i] > xs[i - 1] else 1
        best = max(best, cur)
    return str(best)


def _lis_ascents(s: dict[str, Any]) -> str:
    xs = s["xs"]
    return str(1 + sum(1 for i in range(1, len(xs)) if xs[i] > xs[i - 1]))


def _prime_small(s: dict[str, Any], ask: str) -> str | None:
    if s["ask"] != ask:
        return None
    small = [p for p in (2, 3, 5, 7, 11, 13) if s["n"] % p == 0]
    if not small:
        return None
    return str(max(small)) if ask == "largest" else str(sum(small))


def _cache_other(s: dict[str, Any]) -> str | None:
    from studies.m0.lineages_r2_structures import cache_run

    if s["ask"] != "misses":
        return None
    return str(cache_run(s["seq"], s["cap"], "fifo" if s["policy"] == "lru" else "lru")[0])


def _cache_present_last(s: dict[str, Any]) -> str | None:
    if s["ask"] != "present":
        return None
    return "yes" if s["item"] in s["seq"][-s["cap"] :] else "no"


def _br_counts(s: dict[str, Any]) -> str | None:
    if s["ask"] != "valid":
        return None
    t = s["s"]
    return "yes" if all(t.count(o) == t.count(c) for o, c in ("()", "[]", "{}")) else "no"


def _br_ends(s: dict[str, Any]) -> str | None:
    if s["ask"] != "valid":
        return None
    t = s["s"]
    return "yes" if t[0] in "([{" and t[-1] in ")]}" else "no"


def _br_next_same(s: dict[str, Any]) -> str | None:
    if s["ask"] != "match":
        return None
    t, p = s["s"], s["p"] - 1
    want = {"(": ")", "[": "]", "{": "}"}[t[p]]
    nxt = t.find(want, p + 1)
    return str(nxt + 1) if nxt >= 0 else None


def _expr_other(s: dict[str, Any]) -> str:
    from studies.m0.lineages_r2_parsing import evaluate

    return str(evaluate(s["text"], s["convention"] != "ranked"))


def _expr_flat(s: dict[str, Any]) -> str:
    from studies.m0.lineages_r2_parsing import evaluate

    return str(evaluate(s["text"].replace("(", "").replace(")", ""), True))


def _interval_start(s: dict[str, Any]) -> str:
    from studies.m0.lineages_r2_greedy import earliest_start_greedy

    return str(earliest_start_greedy(s["meetings"]))


def _interval_short(s: dict[str, Any]) -> str:
    n, taken = 0, []
    for a, b in sorted(s["meetings"], key=lambda x: (x[1] - x[0], x[0])):
        if all(b <= c or a >= d for c, d in taken):
            taken.append([a, b])
            n += 1
    return str(n)


def _merge_chain(s: dict[str, Any]) -> str:
    tot, acc = 0, s["ws"][0]
    for w in s["ws"][1:]:
        acc += w
        tot += acc
    return str(tot)


def _net_naive(s: dict[str, Any]) -> str:
    w = sorted(e[2] for e in s["cables"])
    return str(sum(w[: len(s["towns"]) - 1]))


def _net_per_town(s: dict[str, Any]) -> str:
    best: dict[str, int] = {}
    for a, b, w in s["cables"]:
        for t in (a, b):
            best[t] = min(best.get(t, 10**9), w)
    return str(sum(best[t] for t in sorted(best)))


def _da_first(s: dict[str, Any]) -> str:
    return s["prefs_p"][s["who"]][0]


def _da_best_by(s: dict[str, Any]) -> str:
    w = s["who"]
    return min(s["responders"], key=lambda j: (s["prefs_r"][j].index(w), j))


def _sub_mod(s: dict[str, Any]) -> str:
    return "no" if s["n"] % (max(s["moves"]) + 1) == 0 else "yes"


def _sub_mod_sum(s: dict[str, Any]) -> str:
    return "no" if s["n"] % (min(s["moves"]) + max(s["moves"])) == 0 else "yes"


def _sub_parity(s: dict[str, Any]) -> str:
    return "yes" if s["n"] % 2 else "no"


def _ca_initial(s: dict[str, Any]) -> str | None:
    if s["ask"] == "row":
        return "".join(map(str, s["row"]))
    return str(sum(s["row"]))


def _ca_one_step(s: dict[str, Any]) -> str | None:
    from studies.m0.lineages_r2_dynamics import ca_step

    if s["steps"] == 1:
        return None  # one step IS the procedure then

    cur = ca_step(s["row"], s["table"])
    return "".join(map(str, cur)) if s["ask"] == "row" else str(sum(cur))


def _chip_initial(s: dict[str, Any]) -> str | None:
    if s["ask"] == "final":
        return lst(s["row"])
    if s["ask"] == "topplings":
        return str(sum(s["row"]) // 2)
    return None


def _chip_mod2(s: dict[str, Any]) -> str | None:
    return lst([x % 2 for x in s["row"]]) if s["ask"] == "final" else None


def _luhn_plain_valid(s: dict[str, Any]) -> str | None:
    return ("yes" if sum(s["digits"]) % 10 == 0 else "no") if s["ask"] == "valid" else None


def _luhn_plain_check(s: dict[str, Any]) -> str | None:
    return str((-sum(s["digits"])) % 10) if s["ask"] == "check_digit" else None


def _hamming_low(s: dict[str, Any]) -> str:
    n, bits = s["n"], s["bits"]
    p = 1
    while p <= n:
        if sum(b for i, b in enumerate(bits, 1) if i & p) % 2:
            return str(p)
        p *= 2
    return "0"


def _hamming_first_one(s: dict[str, Any]) -> str:
    return str(next((i for i, b in enumerate(s["bits"], 1) if b), 0))


def _perm_sorted(s: dict[str, Any]) -> str | None:
    return "".join(s["letters"]) if s["ask"] == "word" else None


def _perm_reverse(s: dict[str, Any]) -> str | None:
    return "".join(reversed(s["letters"])) if s["ask"] == "word" else None


def _perm_rank_naive(s: dict[str, Any]) -> str | None:
    if s["ask"] != "position":
        return None
    w, letters = s["word"], s["letters"]
    return str(letters.index(w[0]) * math.factorial(len(w) - 1) + 1)


def _bs_log(s: dict[str, Any]) -> str | None:
    return str(math.floor(math.log2(len(s["xs"]))) + 1) if s["ask"] == "count" else None


def _bs_mid(s: dict[str, Any]) -> str | None:
    return lst([s["xs"][(1 + len(s["xs"])) // 2 - 1]]) if s["ask"] == "values" else None


def _lps_run(s: dict[str, Any]) -> str:
    t = s["s"]
    best = cur = 1
    for i in range(1, len(t)):
        cur = cur + 1 if t[i] == t[i - 1] else 1
        best = max(best, cur)
    return str(best)


def _gcd_naive(s: dict[str, Any]) -> str:
    a, b = s["a"], s["b"]
    return str(a - b) if s["ask"] == "gcd" else str(a * b) if s["ask"] == "lcm" else "3"


def _coin_greedy(s: dict[str, Any]) -> str | None:
    from studies.m0.lineages_r2_dynprog import coin_greedy

    g = coin_greedy(s["coins"], s["amount"])
    return "stuck" if g is None else str(g)  # a greedy that cannot reach the amount is a wrong guess


SPECIFIC: dict[str, list[tuple[str, Heur]]] = {
    "R2.lcs_length": [("letter-multiset overlap", _lcs_common), ("half the shorter string", lambda s: str(min(len(s["a"]), len(s["b"])) // 2))],
    "R2.coin_change_min": [("largest coin first", _coin_greedy), ("amount / largest coin, rounded up", lambda s: str(-(-s["amount"] // max(s["coins"]))))],
    "R2.lis_length": [("longest run of ascents", _lis_run), ("ascents + 1", _lis_ascents)],
    "R2.max_subarray_sum": [("largest single number", lambda s: str(max(s["xs"]))), ("sum of positives", lambda s: str(sum(x for x in s["xs"] if x > 0))), ("total", lambda s: str(sum(s["xs"])))],
    "R2.gcd_euclid": [("a-b / a*b / 3", _gcd_naive)],
    "R2.modular_power": [("a", lambda s: str(s["a"])), ("a mod m after e mod 5", lambda s: str(pow(s["a"], s["e"] % 5, s["m"]))), ("e mod m", lambda s: str(s["e"] % s["m"]))],
    "R2.crt_smallest": [("first remainder", lambda s: str(s["congruences"][0][0])), ("sum of remainders", lambda s: str(sum(c[0] for c in s["congruences"]))), ("largest remainder", lambda s: str(max(c[0] for c in s["congruences"])))],
    "R2.prime_factor_query": [("largest small prime (<=13) dividing n", lambda s: _prime_small(s, "largest")), ("sum of the small primes (<=13) dividing n", lambda s: _prime_small(s, "sum_all"))],
    "R2.bst_traversal": [("insertion order", lambda s: lst(s["xs"])), ("sorted", lambda s: lst(sorted(s["xs"]))), ("sorted descending", lambda s: lst(sorted(s["xs"], reverse=True)))],
    "R2.min_heap_ops": [("insertion order", lambda s: lst(s["xs"])), ("sorted", lambda s: lst(sorted(s["xs"]))), ("sorted minus the removals", lambda s: lst(sorted(s["xs"])[s["removals"] :]))],
    "R2.cache_eviction": [("other policy", _cache_other), ("item among the last cap requests", _cache_present_last), ("number of distinct items", lambda s: str(len(set(s["seq"]))) if s["ask"] == "misses" else None)],
    "R2.hash_probe": [("home slot (key mod m)", lambda s: str(s["target"] % s["m"]) if s["ask"] == "slot" else None), ("one slot looked at", lambda s: "1" if s["ask"] == "probes" else None)],
    "R2.bracket_match": [("equal counts of each kind", _br_counts), ("starts with opener, ends with closer", _br_ends), ("next closer of the same kind", _br_next_same), ("mirror position", lambda s: str(len(s["s"]) + 1 - s["p"]) if s["ask"] == "match" else None)],
    "R2.expression_eval": [("the other convention", _expr_other), ("parentheses ignored, ranked", _expr_flat)],
    "R2.interval_scheduling": [("earliest start first", _interval_start), ("shortest first", _interval_short)],
    "R2.merge_smallest_cost": [("join in written order", _merge_chain), ("sum of sizes", lambda s: str(sum(s["ws"])))],
    "R2.cheapest_network": [("n-1 cheapest cables", _net_naive), ("cheapest cable at each town", _net_per_town)],
    "R2.deferred_acceptance_partner": [("own first choice", _da_first), ("responder who ranks them first-highest", _da_best_by)],
    "R2.subtraction_game": [("n mod (largest move + 1)", _sub_mod), ("n mod (smallest + largest)", _sub_mod_sum), ("parity of n", _sub_parity)],
    "R2.cellular_automaton": [("the start", _ca_initial), ("one step only", _ca_one_step)],
    "R2.chip_toppling": [("the start / half the chips", _chip_initial), ("start mod 2", _chip_mod2)],
    "R2.luhn_check": [("plain digit sum", _luhn_plain_valid), ("plain digit-sum check digit", _luhn_plain_check)],
    "R2.hamming_error_position": [("lowest failing check", _hamming_low), ("first 1", _hamming_first_one)],
    "R2.dictionary_rank": [("sorted letters", _perm_sorted), ("reverse letters", _perm_reverse), ("first-letter block start", _perm_rank_naive)],
    "R2.binary_search_trace": [("first middle value only", _bs_mid), ("the target", lambda s: str(s["target"]) if s["ask"] == "third" else None)],
    "R2.longest_palindromic_substring": [("longest run of one letter", _lps_run), ("3", lambda s: "3")],
}


# ---------------------------------------------------------------- generic scoring


def run(per_level: int, out: Path) -> dict[str, Any]:
    res: dict[str, Any] = {"seed": SEED, "per_level": per_level, "lineages": {}}
    for lin in load_batch1():
        rec: dict[str, Any] = {"levels": {}}
        for lv in ALL_LEVELS:
            r = stream(SEED, "shortcut", lin.id, str(lv))
            items: list[Item] = [build_item(lin, lv, r, "A", f"{lin.id}/sc/{lv}/{i}") for i in range(per_level)]
            n = len(items)
            chance = sum((1.0 / it.k) if it.k else 0.0 for it in items) / n
            by_shape: dict[str, list[Item]] = {}
            for it in items:
                by_shape.setdefault(shape_key(it.structured), []).append(it)
            const = sum(max(Counter(it.answer for it in grp).values()) for grp in by_shape.values()) / n
            heur: dict[str, Any] = {}
            nums = [(it, _ints(it.question)) for it in items if it.answer_type == "number"]
            if nums:
                for name, pick in (("first number in the question", lambda xs: xs[0]), ("last number in the question", lambda xs: xs[-1]), ("largest number in the question", max), ("smallest number in the question", min)):
                    ok = sum(1 for it, xs in nums if xs and str(pick(xs)) == it.answer)
                    heur[name] = {"accuracy": round(ok / len(nums), 4), "coverage": round(len(nums) / n, 3), "chance_on_subset": 0.0}
            for name, fn in SPECIFIC.get(lin.id, []):
                hit = tot = 0
                ch = 0.0
                for it in items:
                    g = fn(it.structured)
                    if g is None:
                        continue
                    tot += 1
                    hit += g == it.answer
                    ch += (1.0 / it.k) if it.k else 0.0
                if tot >= 50:
                    acc = hit / tot
                    cs = ch / tot
                    # for a two-way answer the opposite of a heuristic is as good as the heuristic, so its accuracy is read as max(acc, 1 - acc)
                    heur[name] = {"accuracy": round(max(acc, 1 - acc) if abs(cs - 0.5) < 1e-9 else acc, 4), "raw_accuracy": round(acc, 4), "coverage": round(tot / n, 3), "chance_on_subset": round(cs, 4)}
            leak = sum(1 for it in items if it.answer_type == "number" and it.answer in [str(x) for x in _ints(it.question)]) / n
            rec["levels"][str(lv)] = {"chance": round(chance, 4), "constant_key_per_shape": round(const, 4), "answer_token_in_question": round(leak, 4), "distinct_answers": len({it.answer for it in items}), "heuristics": heur,
                                      "shapes": {k: len(v) for k, v in sorted(by_shape.items())}}
        res["lineages"][lin.id] = rec
    out.mkdir(parents=True, exist_ok=True)
    (out / "shortcuts.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


def summarise(res: dict[str, Any]) -> list[dict[str, Any]]:
    """Per lineage: the constant-key share (worst level), the heuristic with the largest margin over its own chance, and the working flag."""
    rows = []
    for lid, rec in sorted(res["lineages"].items()):
        worst = ("", 0.0, -1, 0.0)
        const = (0.0, 0.0, -1)
        for lv, d in rec["levels"].items():
            if d["constant_key_per_shape"] - d["chance"] > const[0] - const[1]:
                const = (d["constant_key_per_shape"], d["chance"], int(lv))
            for name, h in d["heuristics"].items():
                if h["accuracy"] - h["chance_on_subset"] > worst[1] - worst[3]:
                    worst = (name, h["accuracy"], int(lv), h["chance_on_subset"])
        flag_c = const[0] >= max(const[1] + 0.25, 0.30)
        flag_h = worst[1] >= max(worst[3] + 0.25, 0.30)
        rows.append({"lineage": lid, "worst_constant": round(const[0], 3), "constant_chance": round(const[1], 3), "constant_level": const[2],
                     "worst_heuristic": worst[0], "worst_heuristic_acc": worst[1], "worst_heuristic_chance": worst[3], "worst_heuristic_level": worst[2], "flag": flag_c or flag_h})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lineage", default="")
    a = ap.parse_args()
    res = run(a.per_level, a.out)
    rows = summarise(res)
    (a.out / "summary.json").write_text(json.dumps(rows, indent=1, sort_keys=True))
    for row in rows:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
