# ruff: noqa: E501
"""Extra heuristics of the revision-4 battery, for schemas the auditor's functions do not read (written for this round; names beginning ``X:``). Registered in ``r1_rev4_battery.EXTRA``
by base id. Where an auditor heuristic assumed a fixed property that a revision-4 shape now draws (the first mover of a game tree), the same key is redefined so that it reads the drawn
property (a heuristic that is correct exactly when the drawn property takes one value is a procedure for those items, not a shortcut)."""

from __future__ import annotations

from collections import Counter

from studies.m0.core import Item
from studies.m0.r1_rev4_battery import EXTRA, Pred


def _leaves(t: object) -> list[int]:
    return [t] if isinstance(t, int) else [x for c in t for x in _leaves(c)]  # type: ignore[attr-defined,union-attr]


def _val(t: object, maxing: bool) -> int:
    if isinstance(t, int):
        return t
    v = [_val(c, not maxing) for c in t]  # type: ignore[attr-defined]
    return max(v) if maxing else min(v)


def minimax(it: Item) -> dict[str, Pred]:
    s = it.structured
    t, first = s["tree"], s["first"]
    lv = sorted(_leaves(t))
    return {
        "M:min_player_first": str(_val(t, first != "max")),  # the value with the OTHER player moving first (redefined: it read "Min first" for every item)
        "X:value_with_the_stated_first_mover_ignoring_depth": str(max(lv) if first == "max" else min(lv)),
        "X:median_leaf_low": str(lv[(len(lv) - 1) // 2]),
        "X:median_leaf_high": str(lv[len(lv) // 2]),
        "X:mean_leaf_rounded": str(round(sum(lv) / len(lv))),
    }


def venn(it: Item) -> dict[str, Pred]:
    s = it.structured
    tot, sizes, pairs = s["total"], s["sizes"], s["pairs"]
    ssz, sp = sum(sizes.values()), sum(pairs.values())
    st = sum(s["triples"].values())
    out: dict[str, Pred] = {
        "M:total_minus_sum_of_sizes": str(tot - ssz),
        "M:total_minus_largest_group": str(tot - max(sizes.values())),
        "M:total_minus_sum_of_pairs": str(tot - sp),
        "X:forget_the_triples": str(tot - ssz + sp),
        "X:sum_of_sizes": str(ssz),
        "X:sum_of_pairs": str(sp),
        "X:total_minus_sizes_plus_pairs_minus_triples": str(tot - ssz + sp - st),
        "X:inclusion_exclusion_to_a_union_formula": str(ssz - sp + st - (s["quad"] or 0)),
    }
    return out


def bracket(it: Item) -> dict[str, Pred]:
    s = it.structured
    pl, res, ask = s["players"], s["results"], s["ask"]
    wins = Counter(a for a, _ in res)
    n = len(pl)
    order = sorted(pl, key=lambda p: -wins.get(p, 0))
    out: dict[str, Pred] = {"X:most_wins_overall": [p for p in pl if wins.get(p, 0) == max(wins.values())], "X:first_listed": [pl[0]], "X:last_listed": [pl[-1]]}
    half = n // 2
    if ask[0] == "champion":
        out["X:champion_is_the_player_with_most_wins"] = [p for p in pl if wins.get(p, 0) == max(wins.values())]
    elif ask[0] == "runner_up":
        top = order[0]
        other = pl[half:] if pl.index(top) < half else pl[:half]
        out["X:runner_up_is_most_wins_of_the_other_half"] = [p for p in other if wins.get(p, 0) == max(wins.get(q, 0) for q in other)]
        out["X:runner_up_is_second_most_wins"] = [order[1]]
    else:
        x = ask[1]
        i = pl.index(x)
        beaters = [a for a, b in res if b == x]
        mine = pl[:half] if i < half else pl[half:]
        out["X:round_one_neighbour"] = [pl[i ^ 1]]
        out["X:beater_in_own_half"] = [p for p in beaters if p in mine] or None
        out["X:beater_with_most_wins"] = [p for p in beaters if wins.get(p, 0) == max(wins.get(q, 0) for q in beaters)] or None
        out["X:first_listed_beater"] = beaters[:1] or None
        quarter = pl[(i // (n // 4)) * (n // 4) : (i // (n // 4) + 1) * (n // 4)]
        out["X:beater_in_own_quarter"] = [p for p in beaters if p in quarter and p != x] or None
    return out


def sparse_relative(it: Item) -> dict[str, Pred]:
    s = it.structured
    facts = s["facts"]
    ks = [f[2] for f in facts]
    return {"X:sum_of_all_offsets": str(sum(ks)), "X:largest_offset": str(max(ks)), "X:sum_of_two_largest_offsets": str(sum(sorted(ks)[-2:]))}


def threshold(it: Item) -> dict[str, Pred]:
    s = it.structured
    w = dict((p, x) for p, x in s["members"])
    v = s["votes"]
    d = s["margin"]
    yes_w = sum(w[p] for p in w if v[p] == "yes")
    no_w = sum(w[p] for p in w if v[p] == "no")
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    return {"X:yes_weight_ge_margin_plus_no_weight_halved": yn(yes_w - no_w // 2 >= d), "X:count_margin_times_weight_mean": yn((sum(1 for p in w if v[p] == "yes") - sum(1 for p in w if v[p] == "no")) * (sum(w.values()) / len(w)) >= d)}


EXTRA["minimax_tree"] = minimax
EXTRA["venn_counting"] = venn
EXTRA["elimination_bracket"] = bracket
EXTRA["spatial_relative_directions"] = sparse_relative
EXTRA["conditional_threshold_rule"] = threshold
