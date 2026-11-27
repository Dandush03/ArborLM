# ruff: noqa: E501
"""R2 rev2, ruling R-1: tells removed by construction. Each test shows the old shape's tell (it fails there) and the rev2 shape without it. The bounds are regression guards
for these tests, NOT thresholds of any rule. Self-checked only."""

from __future__ import annotations

import itertools
import math
from collections import Counter

from studies.m0.lineages_r2_structures import cache_run
from studies.m0.r2_audit_heuristics_copy import H
from tests.test_m0_r2_rev2_helpers import NEW, OLD, acc, draw, share


def test_chip_toppling_drops_the_shapes_a_conservation_law_answers() -> None:
    old = draw(OLD["R2.chip_toppling"], 4, 300)
    asks = Counter(it.structured["ask"] for it in old)
    assert asks["final"] > 50 and asks["lost"] > 50
    fin = [it for it in old if it.structured["ask"] == "final"]
    lost = [it for it in old if it.structured["ask"] == "lost"]

    def formula(s):  # type: ignore[no-untyped-def]
        n, row = len(s["row"]), s["row"]
        w = sum((i + 1) * c for i, c in enumerate(row))
        z = (n * (n + 1) // 2 - w) % (n + 1)
        pat = [1] * n
        if 1 <= z <= n:
            pat[z - 1] = 0
        return ", ".join(map(str, pat))

    assert acc(fin, formula) > 0.95  # the closed form the audit found
    assert acc(lost, lambda s: str(sum(s["row"]) - (len(s["row"]) - 1))) > 0.7
    for lv in range(7):
        new = draw(NEW["R2.chip_toppling"], lv, 150)
        assert {it.structured["ask"] for it in new} == {"topplings", "topplings_of"}
        # key of a per-cell question: independent of the order of toppling (random order simulation)
        import random

        for it in new[:20]:
            row, cnt, rnd = list(it.structured["row"]), [0] * len(it.structured["row"]), random.Random(3)
            while any(v >= 2 for v in row):
                i = rnd.choice([j for j, v in enumerate(row) if v >= 2])
                row[i] -= 2
                cnt[i] += 1
                for j in (i - 1, i + 1):
                    if 0 <= j < len(row):
                        row[j] += 1
            want = sum(cnt) if it.structured["ask"] == "topplings" else cnt[it.structured["cell"] - 1]
            assert it.answer == str(want)


def test_bracket_valid_no_adjacent_wrong_pair_by_construction_and_match_never_next_position() -> None:
    def adj_bad(s):  # type: ignore[no-untyped-def]
        t = s["s"]
        return any(t[i] in "([{" and t[i + 1] in ")]}" and {"(": ")", "[": "]", "{": "}"}[t[i]] != t[i + 1] for i in range(len(t) - 1))

    old = [it for it in draw(OLD["R2.bracket_match"], 3, 600) if it.structured["ask"] == "valid" and it.answer == "no"]
    assert share(old, adj_bad) > 0.7  # the audit's 0.84-0.87 tell
    for lv in range(7):
        new = [it for it in draw(NEW["R2.bracket_match"], lv, 400) if it.structured["ask"] == "valid"]
        assert not any(adj_bad(it.structured) for it in new)
        no = [it for it in new if it.answer == "no"]
        assert all(all(it.structured["s"].count(o) == it.structured["s"].count(c) for o, c in ("()", "[]", "{}")) for it in no)
        assert 0.4 < len(no) / len(new) < 0.6  # a coin, not a redraw
        m = [it for it in draw(NEW["R2.bracket_match"], lv, 400) if it.structured["ask"] == "match"]
        assert all(it.answer != str(it.structured["p"] + 1) for it in m)


def test_coin_change_question_is_ways_and_old_ceil_plus_one_tell_is_gone() -> None:
    old = draw(OLD["R2.coin_change_min"], 0, 500)
    assert acc(old, lambda s: str(-(-s["amount"] // max(s["coins"])) + 1)) > 0.5  # audit: 0.55-0.69 (overshoot from excluding ceil)
    for lv in range(7):
        new = draw(NEW["R2.coin_change_min"], lv, 100)
        for it in new[:25]:
            s = it.structured
            n = sum(1 for combo in itertools.product(*[range(s["amount"] // c + 1) for c in s["coins"]]) if sum(a * c for a, c in zip(combo, s["coins"], strict=True)) == s["amount"])
            assert it.answer == str(n) and s["ask"] == "ways"
        assert acc(new, lambda s: str(-(-s["amount"] // max(s["coins"])) + 1)) < 0.35


def test_hash_probe_target_is_uniform_among_keys_and_table_is_nearly_full() -> None:
    old = [it for it in draw(OLD["R2.hash_probe"], 2, 600) if it.structured["ask"] == "slot"]

    def displaced(s):  # type: ignore[no-untyped-def]
        slots: dict[int, int] = {}
        for k in s["keys"]:
            p = k % s["m"]
            while p in slots:
                p = (p + 1) % s["m"]
            slots[p] = k
        pos = next(p for p, k in slots.items() if k == s["target"])
        return pos != s["target"] % s["m"]

    assert share(old, displaced) > 0.75  # batch 1 drew about 80% displaced targets
    for lv in range(7):
        new = [it for it in draw(NEW["R2.hash_probe"], lv, 600) if it.structured["ask"] == "slot"]
        assert all(len(it.structured["keys"]) == it.structured["m"] - 1 for it in new)
        # the asked key is a uniform key: its displaced share equals the displaced share over the keys of the same tables
        tot = hit = 0
        for it in new:
            s = it.structured
            slots: dict[int, int] = {}
            for k in s["keys"]:
                p = k % s["m"]
                while p in slots:
                    p = (p + 1) % s["m"]
                slots[p] = k
            hit += sum(1 for p, k in slots.items() if p != k % s["m"])
            tot += len(s["keys"])
        assert abs(share(new, displaced) - hit / tot) < 0.06


def test_cache_present_shape_is_fifo_only_with_a_half_full_pool_and_old_lru_tell_existed() -> None:
    old = [it for it in draw(OLD["R2.cache_eviction"], 4, 800) if it.structured["ask"] == "present"]
    lru = [it for it in old if it.structured["policy"] == "lru"]
    assert acc(lru, lambda s: "yes" if s["item"] in s["seq"][-s["cap"] :] else "no") > 0.7  # audit: LRU 0.75
    for lv in range(7):
        new = [it for it in draw(NEW["R2.cache_eviction"], lv, 600) if it.structured["ask"] == "present"]
        assert {it.structured["policy"] for it in new} == {"fifo"}
        assert 0.4 < sum(it.answer == "yes" for it in new) / len(new) < 0.6
        for it in new[:20]:
            s = it.structured
            assert it.answer == ("yes" if s["item"] in cache_run(s["seq"], s["cap"], "fifo")[1] else "no")
        mis = [it for it in draw(NEW["R2.cache_eviction"], lv, 300) if it.structured["ask"] == "misses"]
        assert {it.structured["policy"] for it in mis} == {"lru", "fifo"}


def test_subtraction_game_two_piles_key_by_recursion_and_no_old_residue_tell() -> None:
    old = draw(OLD["R2.subtraction_game"], 5, 800)
    raw = acc(old, lambda s: "yes" if s["n"] % (max(s["moves"]) + 1) != 0 else "no")
    assert abs(raw - 0.5) > 0.08  # audit: 0.39-0.41 raw (an overshoot made by excluding the heuristic's answer)
    from functools import cache

    for lv in range(7):
        new = draw(NEW["R2.subtraction_game"], lv, 150)
        assert 0.4 < sum(it.answer == "yes" for it in new) / len(new) < 0.6
        for it in new[:15]:
            mv = tuple(it.structured["moves"])

            @cache
            def wins(a: int, b: int, mv: tuple[int, ...] = mv) -> bool:
                return any(m <= a and not wins(a - m, b) for m in mv) or any(m <= b and not wins(a, b - m) for m in mv)

            assert it.answer == ("yes" if wins(*it.structured["piles"]) else "no")


def test_deferred_acceptance_key_is_proposer_optimal_stable_and_has_no_redraw() -> None:
    for lv in range(7):
        for it in draw(NEW["R2.deferred_acceptance_partner"], lv, 40)[:12]:
            s = it.structured
            props, resps = s["proposers"], s["responders"]
            if len(props) > 5:
                continue
            best = None
            for perm in itertools.permutations(resps):
                m = dict(zip(props, perm, strict=True))
                inv = {v: k for k, v in m.items()}
                if any(s["prefs_p"][p].index(r) < s["prefs_p"][p].index(m[p]) and s["prefs_r"][r].index(p) < s["prefs_r"][r].index(inv[r]) for p in props for r in resps):
                    continue
                if best is None or all(s["prefs_p"][p].index(m[p]) <= s["prefs_p"][p].index(best[p]) for p in props):
                    best = m
            assert best is not None and it.answer == best[s["who"]]


def test_cheapest_network_cheap_sum_heuristics_are_wrong_by_construction() -> None:
    def naive(s):  # type: ignore[no-untyped-def]
        return str(sum(sorted(c[2] for c in s["cables"])[: len(s["towns"]) - 1]))

    old = draw(OLD["R2.cheapest_network"], 0, 500)
    assert acc(old, lambda s: H["R2.cheapest_network"](s)["X:cheapest per town minus cheapest cable"]) > 0.5  # batch 1 (audit: 0.71 at level 0)
    for lv in range(7):
        new = draw(NEW["R2.cheapest_network"], lv, 300)
        assert acc(new, naive) == 0.0
        assert acc(new, lambda s: H["R2.cheapest_network"](s)["A:cheapest cable at each town"]) < 0.02
        assert acc(new, lambda s: H["R2.cheapest_network"](s)["X:cheapest per town minus cheapest cable"]) < 0.02
        for it in new[:10]:
            towns = it.structured["towns"]
            cab = it.structured["cables"]
            best = None
            for mask in range(1 << len(cab)):
                sel = [cab[i] for i in range(len(cab)) if mask >> i & 1]
                if len(sel) != len(towns) - 1 or (best is not None and sum(c[2] for c in sel) >= best):
                    continue
                comp = {t: t for t in towns}

                def find(x: str, comp: dict[str, str] = comp) -> str:
                    while comp[x] != x:
                        x = comp[x]
                    return x

                for a, b, _w in sel:
                    comp[find(a)] = find(b)
                if len({find(t) for t in towns}) == 1:
                    best = sum(c[2] for c in sel)
            if len(cab) <= 17:
                assert it.answer == str(best)


def test_max_subarray_planted_block_contains_a_negative_number_and_run_tell_is_gone() -> None:
    def best_run(s):  # type: ignore[no-untyped-def]
        cur = best = 0
        for x in s["xs"]:
            cur = cur + x if x >= 0 else 0
            best = max(best, cur)
        return str(best)

    old = draw(OLD["R2.max_subarray_sum"], 0, 500)
    assert acc(old, best_run) > 0.3  # audit: 0.36-0.59
    for lv in range(7):
        new = draw(NEW["R2.max_subarray_sum"], lv, 300)
        assert acc(new, best_run) == 0.0
        for it in new[:60]:
            xs = it.structured["xs"]
            assert it.answer == str(max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1)))


def test_gcd_common_divisor_has_no_small_prime_and_steps_shape_is_gone() -> None:
    old = [it for it in draw(OLD["R2.gcd_euclid"], 1, 600) if it.structured["ask"] == "gcd"]
    assert acc(old, lambda s: H["R2.gcd_euclid"](s)["X:common small primes (2,3,5,7) product"]) > 0.6  # audit: 0.60-0.86
    for lv in range(7):
        new = draw(NEW["R2.gcd_euclid"], lv, 400)
        assert {it.structured["ask"] for it in new} == {"gcd", "lcm"}
        for it in new:
            g = math.gcd(it.structured["a"], it.structured["b"])
            assert all(g % p for p in (2, 3, 5, 7)) and g >= 11
            assert it.answer == (str(g) if it.structured["ask"] == "gcd" else str(it.structured["a"] * it.structured["b"] // g))
        gc = [it for it in new if it.structured["ask"] == "gcd"]
        assert acc(gc, lambda s: H["R2.gcd_euclid"](s)["X:common small primes (2,3,5,7) product"]) == 0.0


def test_merge_level0_ascending_chain_tell_is_reduced() -> None:
    old = draw(OLD["R2.merge_smallest_cost"], 0, 500)
    new = draw(NEW["R2.merge_smallest_cost"], 0, 500)
    f = lambda s: H["R2.merge_smallest_cost"](s)["X:join in ascending order (chain)"]  # noqa: E731
    assert acc(old, f) > 0.6 and acc(new, f) < 0.45  # audit: 0.735 at level 0


def test_modular_power_modulus_is_a_product_of_two_primes_and_exponent_exceeds_it() -> None:
    old = draw(OLD["R2.modular_power"], 0, 500)
    assert acc(old, lambda s: H["R2.modular_power"](s)["X:a^(e mod (m-1)) mod m (Fermat, valid only for prime m)"]) > 0.4
    for lv in range(7):
        for it in draw(NEW["R2.modular_power"], lv, 150):
            s = it.structured
            assert s["e"] >= 2 * s["m"] and it.answer == str(pow(s["a"], s["e"], s["m"]))
            fs = [p for p in range(2, s["m"]) if s["m"] % p == 0 and all(p % d for d in range(2, int(p**0.5) + 1))]
            assert len(fs) == 2 and fs[0] * fs[1] == s["m"]
        new = draw(NEW["R2.modular_power"], lv, 400)
        assert acc(new, lambda s: H["R2.modular_power"](s)["X:a^2 mod m"]) < 0.25


def test_lcs_lis_lps_prime_answers_are_spread() -> None:
    def mode(items):  # type: ignore[no-untyped-def]
        items = [it for it in items if it.structured.get("ask") in (None, "largest")]  # for the prime lineage the audit's rate is on the `largest` shape
        return Counter(it.answer for it in items).most_common(1)[0][1] / len(items)

    for lid, old_lv, bound in (("R2.lcs_length", 1, 0.28), ("R2.lis_length", 4, 0.27), ("R2.longest_palindromic_substring", 0, 0.2), ("R2.prime_factor_query", 6, 0.16)):
        old_mode = mode(draw(OLD[lid], old_lv, 1500))
        assert old_mode > 0.2  # the audit's mode rates (0.29, 0.32, 0.29, 0.21)
        for lv in range(7):
            m = mode(draw(NEW[lid], lv, 1500))
            assert m <= bound and m < old_mode, (lid, lv, m)


def test_prime_factor_largest_is_uniform_over_the_pool_and_repeat_is_forced() -> None:
    for lv in (0, 3, 6):
        for it in draw(NEW["R2.prime_factor_query"], lv, 200):
            n, fs, d = it.structured["n"], [], 2
            while n > 1:
                while n % d == 0:
                    fs.append(d)
                    n //= d
                d += 1
            assert len(fs) > len(set(fs)) and max(fs) >= 17
            assert it.answer == (str(max(fs)) if it.structured["ask"] == "largest" else str(sum(fs)))
