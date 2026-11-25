# ruff: noqa: E501
"""R2 fix round 3: each fix is guarded by a property that the audited (old) shape fails. Failing-first: run with ``R2_FIX3_TEST_OLD=1`` and the same tests are applied to the shape the registries held before this round
(``r2_fix3_set.current_set``); the implementer ran that and recorded the failures (see studies/m0/NOTES_FIX3_R2.md). Thresholds are loose guards on throwaway seeds, NOT the registered bound (none is registered).
Self-checks, not independent review."""

from __future__ import annotations

import inspect
import math
import os
import random
import re
from collections import Counter
from collections.abc import Callable
from typing import Any

import pytest

from studies.m0.core import Item, build_item
from studies.m0.r2_fix3_set import current_set, fix3_set

TARGET_OLD = os.environ.get("R2_FIX3_TEST_OLD") == "1"
SET = current_set() if TARGET_OLD else fix3_set()


def draw(lid: str, level: int, n: int) -> list[Item]:
    lin = SET["R2." + lid]
    r = random.Random(f"fix3-prop|{lid}|{level}")
    return [build_item(lin, level, r, "A", f"{lid}/{level}/{i}") for i in range(n)]


def rate(items: list[Item], rule: Callable[[dict[str, Any]], str | None]) -> float:
    hit = tot = 0
    for it in items:
        g = rule(it.structured)
        if g is None:
            continue
        tot += 1
        hit += g == it.answer
    return hit / tot if tot else 0.0


def lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


# ---------------------------------------------------------------- static: no redraw conditional on a heuristic (R-1, R-13)
REDRAW_FREE = "interval_scheduling binary_search_trace bst_traversal min_heap_ops cellular_automaton dictionary_rank hash_probe cache_eviction bracket_match cheapest_network max_subarray_sum gcd_euclid".split()
VALIDITY_RETRY_OK = {"cellular_automaton", "bracket_match", "cheapest_network", "coin_change_min", "gcd_euclid", "palindrome_check"}


@pytest.mark.parametrize("name", sorted(set(REDRAW_FREE) | {"subtraction_game", "coin_change_min", "palindrome_check", "stack_machine", "lcs_length", "count_letter", "count_divisible", "permutation_power", "expression_eval"}))
def test_builder_has_no_redraw_loop_or_unlisted_retry(name: str) -> None:
    src = inspect.getsource(SET["R2." + name].build)
    if name != "subtraction_game":  # subtraction_game balances yes/no on the KEY (as in rev2), nothing else
        assert "until(" not in src, f"{name} redraws with until()"
    if name not in VALIDITY_RETRY_OK:
        assert "Retry" not in src, f"{name} raises Retry (only validity retries are listed)"
    # the old redraw pattern: drawing again inside the builder
    assert "while True" not in src or name == "coin_change_min"
    assert "random() <" not in src or "hard" not in src
    assert "(1, total)" not in src, "dictionary_rank still redraws on rank 1 or last"


# ---------------------------------------------------------------- interval_scheduling
def _greedy(iv: list[list[int]], key: Callable[[int], Any]) -> str:
    taken: list[int] = []
    for i in sorted(range(len(iv)), key=key):
        if all(iv[i][1] <= iv[j][0] or iv[i][0] >= iv[j][1] for j in taken):
            taken.append(i)
    return lst(sorted(i + 1 for i in taken))


@pytest.mark.parametrize("level", [0, 3, 6])
def test_interval_made_of_independent_blocks_and_no_single_greedy_gets_the_list(level: int) -> None:
    items = draw("interval_scheduling", level, 300)
    assert all(it.structured.get("ask") == "chosen" for it in items)
    for it in items:
        iv = sorted(it.structured["meetings"])
        windows = 1
        end = iv[0][1]
        for s, e in iv[1:]:
            if s > end:
                windows += 1
                end = e
            else:
                end = max(end, e)
        assert windows >= 5
    assert rate(items, lambda s: _greedy(s["meetings"], lambda i: (s["meetings"][i][0], s["meetings"][i][1], i))) <= 0.25
    assert rate(items, lambda s: _greedy(s["meetings"], lambda i: (s["meetings"][i][1] - s["meetings"][i][0], s["meetings"][i][0], i))) <= 0.3


# ---------------------------------------------------------------- binary_search_trace
@pytest.mark.parametrize("level", [0, 2, 5])
def test_binary_search_long_list_fair_coin_no_third(level: int) -> None:
    items = draw("binary_search_trace", level, 400)
    assert {it.structured["ask"] for it in items} == {"values", "sum"}
    assert all(len(it.structured["xs"]) >= 16 and len(it.structured["xs"]) not in (15, 31, 63) for it in items)
    absent = sum(it.structured["target"] not in it.structured["xs"] for it in items) / len(items)
    assert 0.4 <= absent <= 0.6


# ---------------------------------------------------------------- bst_traversal, min_heap_ops
def test_bst_n_and_no_rejection_of_the_insertion_order() -> None:
    items = draw("bst_traversal", 0, 4000)
    assert all(len(it.structured["xs"]) == 8 for it in items)
    assert any(it.answer == lst(it.structured["xs"]) for it in items), "no item has the insertion order as its answer: the old rejection is still in place"


@pytest.mark.parametrize("level", [0, 4])
def test_heap_size(level: int) -> None:
    assert all(len(it.structured["xs"]) == 10 + level for it in draw("min_heap_ops", level, 50))


# ---------------------------------------------------------------- cellular_automaton
@pytest.mark.parametrize("level", [0, 3, 6])
def test_cellular_automaton_ends_one_mirror_pairs_differ_and_reverse_reading_wrong(level: int) -> None:
    items = draw("cellular_automaton", level, 300)
    for it in items:
        s = it.structured
        assert s["ask"] == "row" and s["row"][0] == 1 and s["row"][-1] == 1 and len(s["row"]) == 11 + 2 * level and s["steps"] == 2 + level // 2
        assert s["table"]["001"] != s["table"]["100"] and s["table"]["011"] != s["table"]["110"]

    def reversed_reading(s: dict[str, Any]) -> str:
        t = {k[::-1]: v for k, v in s["table"].items()}
        row = "".join(map(str, s["row"]))
        for _ in range(s["steps"]):
            pad = "0" + row + "0"
            row = "".join(str(t[pad[i : i + 3]]) for i in range(len(row)))
        return row

    assert rate(items, reversed_reading) <= 0.12


# ---------------------------------------------------------------- dictionary_rank, run_length (capacity under reading b)
def test_dictionary_rank_letters_taken_from_a_larger_alphabet_and_space_covers_demand() -> None:
    from studies.m0.lineages_r2_fix3 import _DR_PLAN
    from studies.m0.r2_fix3_clusters import demand

    for lv, (ln, sizes) in _DR_PLAN.items():
        assert all(m - ln >= 2 for m in sizes)
        space = sum(2 * math.perm(m, ln) - 2 for m in sizes)  # word shape k in 2..total-1, position shape every word
        assert space >= demand(17), (lv, space)
    assert all(it.structured["length"] <= len(it.structured["letters"]) - 2 for it in draw("dictionary_rank", 1, 40))


@pytest.mark.parametrize("level", range(7))
def test_run_length_run_counts_and_letter_blind_space(level: int) -> None:
    from studies.m0.r2_fix3_clusters import demand

    items = draw("run_length", level, 40)
    for it in items:
        runs = [len(m.group(0)) for m in re.finditer(r"(.)\1*", it.structured["s"])]
        assert len(runs) == 6 + level and max(runs) <= 4 + level // 2
    # letter-blind patterns: sequences of labels, adjacent different, at most six labels (count by a small DP over (labels used, last label))
    n = 6 + level
    state = {(1, 0): 1}
    for _ in range(n - 1):
        nxt: dict[tuple[int, int], int] = {}
        for (k, last), c in state.items():
            for lab in range(k):
                if lab != last:
                    nxt[(k, lab)] = nxt.get((k, lab), 0) + c
            if k < 6:
                nxt[(k + 1, k)] = nxt.get((k + 1, k), 0) + c
        state = nxt
    assert sum(state.values()) * (4 + level // 2) ** n >= demand(17)


# ---------------------------------------------------------------- hash_probe
@pytest.mark.parametrize("level", [0, 3, 6])
def test_hash_whole_table_questions_and_spread_homes(level: int) -> None:
    items = draw("hash_probe", level, 200)
    assert {it.structured["ask"] for it in items} == {"table", "checksum"}
    homes = [k % it.structured["m"] < it.structured["m"] // 3 + 1 for it in items for k in it.structured["keys"]]
    assert sum(homes) / len(homes) <= 0.5
    assert all(len(it.structured["keys"]) == round(0.7 * it.structured["m"]) for it in items)


# ---------------------------------------------------------------- cache_eviction
@pytest.mark.parametrize("level", [0, 3, 6])
def test_cache_lists_with_hits_and_no_last_requests_rule(level: int) -> None:
    items = draw("cache_eviction", level, 300)
    assert {it.structured["ask"] for it in items} == {"evicted", "contents"}
    for it in items:
        s = it.structured
        assert s["cap"] >= 3 and len(set(s["seq"][: s["cap"] + 1])) == s["cap"] + 1
        if s["ask"] == "contents":
            assert s["policy"] == "fifo"

    def last_distinct(s: dict[str, Any]) -> str | None:
        if s["ask"] != "contents":
            return None
        seen: list[str] = []
        for x in reversed(s["seq"]):
            if x not in seen:
                seen.append(x)
        return ", ".join(reversed(seen[: s["cap"]]))

    assert rate(items, last_distinct) <= 0.25


# ---------------------------------------------------------------- bracket_match
_MATE = {")": "(", "]": "[", "}": "{"}


@pytest.mark.parametrize("level", [0, 3, 6])
def test_bracket_list_answers_balanced_kinds_and_no_partial_rule(level: int) -> None:
    items = draw("bracket_match", level, 400)
    assert {it.structured["ask"] for it in items} == {"match_all", "first_error"}
    for it in items:
        t = it.structured["s"]
        assert len(t) == 2 * (14 + level)
        for o in "([{":
            assert t.count(o) >= 4

    def queue(s: dict[str, Any]) -> str | None:
        if s["ask"] != "match_all":
            return None
        cl = {"(": ")", "[": "]", "{": "}"}[s["kind"]]
        return lst([i + 1 for i, c in enumerate(s["s"]) if c == cl])

    def count_rule(s: dict[str, Any]) -> str | None:
        if s["ask"] != "first_error":
            return None
        bal = {"(": 0, "[": 0, "{": 0}
        for i, c in enumerate(s["s"]):
            if c in bal:
                bal[c] += 1
            else:
                bal[_MATE[c]] -= 1
                if bal[_MATE[c]] < 0:
                    return str(i + 1)
        return None

    assert rate(items, queue) <= 0.3
    assert rate(items, count_rule) <= 0.35


# ---------------------------------------------------------------- expression_eval
def _ev(text: str, ranked: bool) -> int:
    from studies.m0.lineages_r2_parsing import evaluate

    return evaluate(text, ranked)


def _ev_plus_first(text: str) -> int:
    """The old reading of 'additions and subtractions': plus binds tighter than minus (shunting-yard with * > + > -)."""
    prec = {"*": 3, "+": 2, "-": 1}
    out: list[int | str] = []
    ops: list[str] = []
    for tok in re.findall(r"\d+|[()+*-]", text):
        if tok.isdigit():
            out.append(int(tok))
        elif tok == "(":
            ops.append(tok)
        elif tok == ")":
            while ops[-1] != "(":
                out.append(ops.pop())
            ops.pop()
        else:
            while ops and ops[-1] != "(" and prec[ops[-1]] >= prec[tok]:
                out.append(ops.pop())
            ops.append(tok)
    out += ops[::-1]
    st: list[int] = []
    for tok in out:
        if isinstance(tok, int):
            st.append(tok)
        else:
            b, a = st.pop(), st.pop()
            st.append(a + b if tok == "+" else a - b if tok == "-" else a * b)
    return st[0]


@pytest.mark.parametrize("level", [0, 2, 5])
def test_expression_every_misreading_differs_by_construction(level: int) -> None:
    items = draw("expression_eval", level, 300)
    agree = Counter[str]()
    n = Counter[str]()
    for it in items:
        s = it.structured
        ranked = s["convention"] == "ranked"
        k = s["convention"]
        n[k] += 1
        agree[k + ":other rule"] += _ev(s["text"], not ranked) == int(it.answer)
        stripped = s["text"].replace("(", "").replace(")", "")
        agree[k + ":no parentheses"] += _ev(stripped, ranked) == int(it.answer)
        if ranked:
            agree[k + ":plus before minus"] += _ev_plus_first(s["text"]) == int(it.answer)
    for key, c in agree.items():
        assert c / n[key.split(":")[0]] <= 0.2, (key, c)


# ---------------------------------------------------------------- subtraction_game
@pytest.mark.parametrize("level", [0, 3, 6])
def test_subtraction_four_piles_balanced_and_win_lose_rule_weak(level: int) -> None:
    items = draw("subtraction_game", level, 400)
    assert all(len(it.structured["piles"]) == 4 for it in items)
    yes = sum(it.answer == "yes" for it in items) / len(items)
    assert 0.42 <= yes <= 0.58

    def grundy(n: int, moves: list[int]) -> int:
        g = [0] * (n + 1)
        for x in range(1, n + 1):
            seen = {g[x - m] for m in moves if m <= x}
            v = 0
            while v in seen:
                v += 1
            g[x] = v
        return g[n]

    def odd_wins(s: dict[str, Any]) -> str:
        return "yes" if sum(1 for p in s["piles"] if grundy(p, s["moves"])) % 2 else "no"

    assert abs(rate(items, odd_wins) - 0.5) <= 0.2


# ---------------------------------------------------------------- cheapest_network
def _edges(s: dict[str, Any]) -> tuple[list[tuple[int, int, int]], int]:
    idx = {t: i for i, t in enumerate(s["towns"])}
    return [(idx[a], idx[b], w) for a, b, w in s["cables"]], len(s["towns"])


@pytest.mark.parametrize("level", [0, 3, 6])
def test_cheapest_network_no_template_and_no_cheap_sums(level: int) -> None:
    items = draw("cheapest_network", level, 300)

    def n_minus_1(s: dict[str, Any]) -> str:
        e, n = _edges(s)
        return str(sum(sorted(w for _, _, w in e)[: n - 1]))

    def template(s: dict[str, Any]) -> str:
        """the round-2 construction read back: cheap cables (<= 6) minus the dearest of each cheap component, plus the (g-1) cheapest dear cables"""
        e, n = _edges(s)
        dear = sorted(w for _, _, w in e if w > 6)
        par = list(range(n))

        def f(x: int) -> int:
            while par[x] != x:
                x = par[x]
            return x

        for a, b, w in e:
            if w <= 6:
                par[f(a)] = f(b)
        comp: dict[int, list[int]] = {}
        for a, b, w in e:
            if w <= 6:
                comp.setdefault(f(a), []).append(w)
        g = n // 3
        return str(sum(sum(v) - max(v) for v in comp.values()) + sum(dear[: g - 1]))

    def per_town(s: dict[str, Any]) -> str:
        e, _n = _edges(s)
        b: dict[int, int] = {}
        for x, y, w in e:
            for t in (x, y):
                b[t] = min(b.get(t, 99), w)
        return str(sum(b.values()))

    assert all(len(it.structured["towns"]) >= 8 for it in items)
    assert rate(items, n_minus_1) <= 0.2 and rate(items, per_town) <= 0.2 and rate(items, template) <= 0.2


# ---------------------------------------------------------------- max_subarray_sum
@pytest.mark.parametrize("level", [0, 3, 6])
def test_max_subarray_no_window_or_two_run_template(level: int) -> None:
    items = draw("max_subarray_sum", level, 400)

    def window7(s: dict[str, Any]) -> str:
        xs = s["xs"]
        return str(max(sum(xs[i : i + 7]) for i in range(len(xs) - 6)))

    def two_runs(s: dict[str, Any]) -> str:
        xs = s["xs"]
        runs, i = [], 0
        while i < len(xs):
            if xs[i] > 0:
                j = i
                while j < len(xs) and xs[j] > 0:
                    j += 1
                runs.append((sum(xs[i:j]), i, j))
                i = j
            else:
                i += 1
        best = max(r[0] for r in runs)
        for a, b in zip(runs, runs[1:], strict=False):
            if b[1] == a[2] + 1:
                best = max(best, a[0] + b[0] + xs[a[2]])
        return str(best)

    assert rate(items, window7) <= 0.35 and rate(items, two_runs) <= 0.35


# ---------------------------------------------------------------- coin_change_min
@pytest.mark.parametrize("level", [0, 3, 6])
def test_coin_change_fewest_coins_list_over_five_amounts(level: int) -> None:
    items = draw("coin_change_min", level, 300)
    for it in items:
        s = it.structured
        assert s["ask"] == "fewest" and len(s["amounts"]) == 5 and 1 not in s["coins"]
        assert len(it.answer.split(", ")) == 5

    def greedy(s: dict[str, Any]) -> str:
        out = []
        for a in s["amounts"]:
            n = 0
            for c in sorted(s["coins"], reverse=True):
                n += a // c
                a %= c
            out.append(n)
        return lst(out)

    def ceil_rule(s: dict[str, Any]) -> str:
        return lst([-(-a // max(s["coins"])) for a in s["amounts"]])

    assert rate(items, greedy) <= 0.2 and rate(items, ceil_rule) <= 0.25


# ---------------------------------------------------------------- lcs_length
def test_lcs_strings_are_long() -> None:
    items = draw("lcs_length", 0, 300)
    assert all(len(it.structured["a"]) >= 15 and len(it.structured["b"]) >= 15 for it in items)

    def greedy(s: dict[str, Any]) -> str:
        def gr(a: str, b: str) -> int:
            j = n = 0
            for c in a:
                k = b.find(c, j)
                if k >= 0:
                    n += 1
                    j = k + 1
            return n

        return str(max(gr(s["a"], s["b"]), gr(s["b"], s["a"])))

    assert rate(items, greedy) <= 0.3


# ---------------------------------------------------------------- gcd_euclid, multiples_between
@pytest.mark.parametrize("level", [0, 1, 2, 3, 6])
def test_gcd_common_divisor_never_prime_or_squarefree(level: int) -> None:
    items = draw("gcd_euclid", level, 300)
    for it in items:
        s = it.structured
        g = math.gcd(s["a"], s["b"])
        assert g >= 8 and any(g % (p * p) == 0 for p in range(2, int(g**0.5) + 1))
    assert rate(items, lambda s: str(s["a"] % s["b"]) if s["ask"] == "gcd" else None) <= 0.2


@pytest.mark.parametrize("level", [0, 3])
def test_multiples_both_ends_are_multiples_and_fencepost_slips_are_wrong(level: int) -> None:
    items = draw("multiples_between", level, 300)
    assert all(it.structured["a"] % it.structured["m"] == 0 and it.structured["b"] % it.structured["m"] == 0 for it in items)
    assert rate(items, lambda s: str((s["b"] - s["a"]) // s["m"]) if s["ask"] == "count" else None) <= 0.01
    assert rate(items, lambda s: str(s["b"] // s["m"] - s["a"] // s["m"]) if s["ask"] == "count" else None) <= 0.01
    assert rate(items, lambda s: str(sum(x for x in range(s["a"], s["b"]) if x % s["m"] == 0)) if s["ask"] == "sum" else None) <= 0.01


# ---------------------------------------------------------------- count_letter, count_divisible
@pytest.mark.parametrize("level", [0, 3, 6])
def test_count_letter_words_containing_is_never_the_total(level: int) -> None:
    items = draw("count_letter", level, 400)
    assert rate(items, lambda s: str(sum(1 for w in s["words"] if s["letter"] in w))) == 0.0
    assert rate(items, lambda s: str(len(s["words"]))) <= 0.15


@pytest.mark.parametrize("level", [0, 3, 6])
def test_count_divisible_threshold_planted(level: int) -> None:
    items = draw("count_divisible", level, 400)
    assert all(it.structured["t"] in it.structured["xs"] and it.structured["t"] % it.structured["m"] == 0 for it in items)
    assert rate(items, lambda s: str(sum(x for x in s["xs"] if x % s["m"] == 0 and x >= s["t"]))) == 0.0
    assert rate(items, lambda s: str(sum(x for x in s["xs"] if x % s["m"] == 0))) == 0.0


# ---------------------------------------------------------------- palindrome_check
@pytest.mark.parametrize("level", [0, 3, 6])
def test_palindrome_no_items_are_anagrams_of_palindromes(level: int) -> None:
    items = draw("palindrome_check", level, 400)
    yes = sum(it.answer == "yes" for it in items) / len(items)
    assert 0.4 <= yes <= 0.6

    def odd_counts(s: dict[str, Any]) -> str:
        t = s["phrase"].replace(" ", "")
        return "yes" if sum(1 for c in set(t) if t.count(c) % 2) <= 1 else "no"

    assert abs(rate(items, odd_counts) - 0.5) <= 0.12
    assert all(odd_counts(it.structured) == "yes" for it in items)  # every text, palindrome or not, has the letter counts of a palindrome


# ---------------------------------------------------------------- stack_machine
@pytest.mark.parametrize("level", [0, 3, 6])
def test_stack_machine_last_step_not_a_push(level: int) -> None:
    items = draw("stack_machine", level, 400)
    assert all(it.structured["prog"][-1][0] in ("add", "mul", "sub") for it in items)
    assert all(not (a[0] == "dup" and b[0] == "sub") for it in items for a, b in zip(it.structured["prog"], it.structured["prog"][1:], strict=False))
    assert rate(items, lambda s: str([p[1] for p in s["prog"] if p[0] == "push"][-1])) <= 0.15


# ---------------------------------------------------------------- permutation_power
@pytest.mark.parametrize("level", [0, 3, 6])
def test_permutation_long_cycle_and_cheap_rules_weak(level: int) -> None:
    items = draw("permutation_power", level, 400)
    for it in items:
        s = it.structured
        n = len(s["img"])
        x, c = s["img"][s["s"] - 1], 1
        while x != s["s"]:
            x = s["img"][x - 1]
            c += 1
        assert n == 12 + level and c >= n - 3 and math.gcd(c, n) == 1

    def mod_n(s: dict[str, Any]) -> str:
        x = s["s"]
        for _ in range(s["t"] % len(s["img"])):
            x = s["img"][x - 1]
        return str(x)

    assert rate(items, lambda s: str(s["s"])) <= 0.15
    assert rate(items, lambda s: str(s["img"][s["s"] - 1])) <= 0.15
    assert rate(items, mod_n) <= 0.15


# ---------------------------------------------------------------- prime_factor_query (capacity at level 0)
def test_prime_factor_level0_has_room() -> None:
    from studies.m0.r2_fix3_clusters import demand

    items = draw("prime_factor_query", 0, 25000)
    assert len({it.structured["n"] if it.structured["ask"] == "largest" else (it.structured["n"], 1) for it in items}) >= demand(17)
