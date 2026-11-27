# ruff: noqa: E501
"""R1 fix round 3: one guard per audited defect. Each guard is a PROPERTY of the structured form; it is asserted to HOLD for the round-3 shape and to FAIL for the earlier shape that the audit found defective
(the failing-first demonstration is the second assertion of each test: it is the earlier shape that is expected to break the property). Seeds are throwaway integers."""

from __future__ import annotations

import random
from collections import deque

from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0.core import Retry
from studies.m0.lineages_r1_fix3_common import load_fix3

NEW = {x.id: x for x in load_fix3()}
OLD = {x.id: x for x in v2.registered_v2()}


def items(lin, level: int, n: int, seed: int):
    r = random.Random(seed * 1000 + level)
    out, tries = [], 0
    while len(out) < n and tries < 80 * n:
        tries += 1
        try:
            out.append(lin.build(level, r))
        except Retry:
            continue
    assert len(out) == n
    return out


def rate(lin, levels, n, seed, pred) -> float:
    xs = [pred(b, lv) for lv in levels for b in items(lin, lv, n, seed)]
    return sum(xs) / len(xs)


# ---------------------------------------------------------------- stated answers (conditional_chain, seating_row, pet_owners)


def test_conditional_chain_never_states_the_asked_variable():
    pred = lambda b, lv: b.structured["query"] in {v for v, _ in b.structured["facts"]}  # noqa: E731
    assert rate(NEW["R1.conditional_chain_r5"], range(7), 60, 1, pred) == 0.0
    assert rate(OLD["R1.conditional_chain"], range(7), 60, 1, pred) > 0.25  # the earlier shape stated it in 37 to 49 % (audit 3)


def test_seating_row_never_states_the_asked_seat():
    pred = lambda b, lv: any(c[0] == "pos" and c[2] == b.structured["seat"] for c in b.structured["clues"])  # noqa: E731
    assert rate(NEW["R1.seating_row_r5"], range(7), 40, 2, pred) == 0.0
    assert rate(OLD["R1.seating_row"], range(7), 80, 2, pred) > 0.08


def test_pet_owners_rebuild_never_names_the_pet_in_owns_or_either_and_is_not_registered():
    pred = lambda b, lv: any(c[0] in ("owns", "either") and b.structured["ask"] in c[2:] for c in b.structured["clues"])  # noqa: E731
    assert rate(NEW["R1.pet_owners_r5"], range(7), 40, 3, pred) == 0.0
    assert rate(OLD["R1.pet_owners"], range(7), 80, 3, pred) > 0.2
    from studies.m0 import lineages_r1_fix3_clusters as c3

    assert "R1.pet_owners_r5" in c3.NOT_REGISTERED_V3  # the partial elimination reads +0.63 to +0.73, so the shape is excluded (R-12)


# ---------------------------------------------------------------- wording: temporal_critical_path


def test_critical_path_states_the_day_convention_and_the_key_follows_it():
    new = items(NEW["R1.temporal_critical_path_r5"], 3, 30, 4)
    for b in new:
        assert "starts at the beginning of day 1" in b.question and "first day after the last of them has finished its final day" in b.question and "How many days in all" in b.question
        jobs = {p: (d, w) for p, d, w in b.structured["jobs"]}
        memo: dict[str, int] = {}

        def fin(p, jobs=jobs, memo=memo):
            if p not in memo:
                memo[p] = jobs[p][0] + max((fin(x) for x in jobs[p][1]), default=0)
            return memo[p]

        # under the stated convention a job of d days that starts on day s occupies days s .. s + d - 1; count the days used by an explicit day-by-day schedule
        day_done = {}
        t = 1
        for p in sorted(jobs, key=fin):
            start = 1 + max((day_done[x] for x in jobs[p][1]), default=0)
            day_done[p] = start + jobs[p][0] - 1
            t = max(t, day_done[p])
        assert str(t) == b.answer
    old = items(OLD["R1.temporal_critical_path_r4"], 3, 5, 4)[0]
    assert "starts on day 0" in old.question and "convention" not in old.question  # the earlier item named no convention for the day a job finishes


# ---------------------------------------------------------------- tells removed by construction


def _leaf_matches(rule, item):
    if rule[0] == "attr":
        return [item[rule[1]] == rule[2]]
    return [m for c in rule[1:] for m in _leaf_matches(c, item)]


def test_attribute_rule_every_badge_matches_the_same_number_of_tests():
    def equal(b, lv):
        st = b.structured
        return len({sum(_leaf_matches(st["rule"], it)) for it in st["items"]}) == 1

    assert rate(NEW["R1.attribute_rule_r5"], range(7), 40, 5, equal) == 1.0
    assert rate(OLD["R1.attribute_rule"], range(7), 40, 5, equal) < 0.3


def _hops(taller, a, b):
    dist = {a: 0}
    q = deque([a])
    while q:
        u = q.popleft()
        for x, y in taller:
            if x == u and y not in dist:
                dist[y] = dist[u] + 1
                q.append(y)
    return dist.get(b)


def test_order_compare_depth_is_set_by_the_level_and_the_pair_is_never_stated():
    lin = NEW["R1.order_compare_r5"]
    for level in (0, 3, 6):
        for b in items(lin, level, 60, 6):
            t = [tuple(p) for p in b.structured["taller"]]
            x, y = b.structured["x"], b.structured["y"]
            assert (x, y) not in t and (y, x) not in t
            if b.answer == "yes":
                assert 2 + level <= _hops(t, x, y) <= 7 + level
            elif b.answer == "no":
                assert 2 + level <= _hops(t, y, x) <= 7 + level

    def two_step(b, lv):  # the earlier audit's rule: a path of at most two steps, else "cannot be determined"
        t = [tuple(p) for p in b.structured["taller"]]
        h, hr = _hops(t, b.structured["x"], b.structured["y"]), _hops(t, b.structured["y"], b.structured["x"])
        guess = "yes" if h is not None and h <= 2 else ("no" if hr is not None and hr <= 2 else "cannot be determined")
        return guess == b.answer

    assert rate(NEW["R1.order_compare_r5"], (1, 3, 5), 120, 6, two_step) < 0.45
    assert rate(OLD["R1.order_compare_r4"], (1, 3, 5), 120, 6, two_step) > 0.85


def test_road_reachability_outdegree_of_x_is_independent_of_the_answer():
    lin = NEW["R1.road_reachability_r5"]
    out = {"yes": [], "no": []}
    for lv in range(7):
        for b in items(lin, lv, 80, 7):
            x = b.structured["x"]
            out[b.answer].append(sum(1 for a, _ in b.structured["roads"] if a == x))
    assert abs(sum(out["yes"]) / len(out["yes"]) - sum(out["no"]) / len(out["no"])) < 0.2
    old_out = {"yes": [], "no": []}
    for lv in range(7):
        for b in items(OLD["R1.road_reachability"], lv, 80, 7):
            old_out[b.answer].append(sum(1 for a, _ in b.structured["roads"] if a == b.structured["x"]))
    assert abs(sum(old_out["yes"]) / len(old_out["yes"]) - sum(old_out["no"]) / len(old_out["no"])) > 0.3


def test_kinship_cousins_one_family_and_a_third_yes():
    def root(par, p):
        while p in par:
            p = par[p]
        return p

    same_family = lambda b, lv: root(b.structured["parent"], b.structured["x"]) == root(b.structured["parent"], b.structured["y"])  # noqa: E731
    assert rate(NEW["R1.kinship_cousins_r5"], range(7), 60, 8, same_family) == 1.0
    assert rate(OLD["R1.kinship_cousins"], range(7), 60, 8, same_family) < 0.8  # two unrelated families: 'same family' decided many items
    yes = rate(NEW["R1.kinship_cousins_r5"], range(7), 120, 8, lambda b, lv: b.answer == "yes")
    assert 0.28 < yes < 0.40


def _height_and_size(st, cand):
    kids: dict[str, list] = {}
    for c, p in st["parent"].items():
        kids.setdefault(p, []).append(c)

    def cnt(p):
        return sum(1 + cnt(k) for k in kids.get(p, []))

    def hgt(p):
        return 0 if not kids.get(p) else 1 + max(hgt(k) for k in kids[p])

    return hgt(cand), cnt(cand)


def _corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    vx, vy = sum((a - mx) ** 2 for a in xs), sum((b - my) ** 2 for b in ys)
    return cov / (vx * vy) ** 0.5 if vx and vy else 0.0


def test_kinship_descendants_height_is_independent_of_the_number_of_descendants():
    def corr(lin):
        hs, ss = [], []
        for lv in (1, 3, 5):
            for b in items(lin, lv, 60, 9):
                for c in b.structured["candidates"]:
                    h, s = _height_and_size(b.structured, c)
                    hs.append(h)
                    ss.append(s)
        return _corr(hs, ss)

    assert abs(corr(NEW["R1.kinship_descendants_r5"])) < 0.2
    assert corr(OLD["R1.kinship_descendants_r4"]) > 0.4


def test_nim_first_player_items_have_a_single_bit_xor():
    for lv in range(7):
        for b in items(NEW["R1.nim_xor_r5"], lv, 60, 10):
            x = 0
            for p in b.structured["piles"]:
                x ^= p
            assert sum(b.structured["piles"]) % 2 == 0
            if b.answer == "first":
                assert x & (x - 1) == 0 and x > 1  # a power of two above bit 0
            else:
                assert x == 0
    # the earlier shape's xor of a first-player item usually had several bits set
    multi = [bin(b_x).count("1") > 1 for lv in range(7) for b in items(OLD["R1.nim_xor_r4"], lv, 40, 10) if b.answer == "first" for b_x in [__import__("functools").reduce(lambda a, c: a ^ c, b.structured["piles"])]]
    assert sum(multi) / len(multi) > 0.5


def _wall_blocked(st):
    g = st["grid"]
    i, j = st["start"]
    n = 0
    for m in st["moves"]:
        di, dj = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}[m]
        ni, nj = i + di, j + dj
        if 0 <= ni < len(g) and 0 <= nj < len(g[0]):
            if g[ni][nj]:
                i, j = ni, nj
            else:
                n += 1
    return n


def test_grid_walk_has_exactly_the_planted_wall_blocked_moves():
    for lv in range(7):
        for b in items(NEW["R1.spatial_grid_walk_r5"], lv, 40, 11):
            assert _wall_blocked(b.structured) == 3 + lv // 3
    old = [_wall_blocked(b.structured) for b in items(OLD["R1.spatial_grid_walk_r2"], 0, 60, 11)]
    assert sum(1 for k in old if k == 0) / len(old) > 0.2  # the earlier level 0: many walks never meet a wall, so 'ignore the walls' was right


def test_queue_line_every_kind_of_operation_occurs():
    kinds = {"join", "cut", "serve", "leave", "front_to_back"}
    for lv in range(7):
        for b in items(NEW["R1.containers_queue_line_r5"], lv, 40, 12):
            assert kinds <= {o[0] for o in b.structured["ops"]}
    old = [kinds <= {o[0] for o in b.structured["ops"]} for b in items(OLD["R1.containers_queue_line_r2"], 0, 60, 12)]
    assert sum(old) / len(old) < 0.6


def test_tracking_accounts_asks_a_balance_and_each_kind_of_operation_involves_the_asked_person():
    for lv in range(7):
        for b in items(NEW["R1.tracking_accounts_r5"], lv, 40, 13):
            who = b.structured["ask"]
            ops = b.structured["ops"]
            assert any(o[0] == "pay" and who in o[1:3] for o in ops)
            assert any(o[0] == "earn" and o[1] == who for o in ops)
            assert any(o[0] == "half" and who in o[1:3] for o in ops)
    assert items(OLD["R1.tracking_accounts"], 2, 1, 13)[0].structured["ask"] in ("most", "least")


def test_swap_tracking_is_wider_and_the_asked_item_has_been_moved_by_both_kinds():
    assert all(len(b.structured["hold"]) >= 5 for b in items(NEW["R1.swap_tracking_r5"], 0, 30, 14))
    assert all(len(b.structured["hold"]) == 3 for b in items(OLD["R1.swap_tracking"], 0, 5, 14))  # 13 structures at level 0 (audit 3, exact)
    for lv in range(7):
        for b in items(NEW["R1.swap_tracking_r5"], lv, 40, 14):
            st = b.structured
            cur = {p: p for p in st["hold"]}  # cur[p]: the person whose ORIGINAL item p holds now
            moved = {p: set() for p in st["hold"]}  # by original owner: the kinds of operation that have moved their item
            for o in st["ops"]:
                if o[0] == "swap":
                    a, c = o[1], o[2]
                    cur[a], cur[c] = cur[c], cur[a]
                    moved[cur[a]].add("swap")
                    moved[cur[c]].add("swap")
                else:
                    a, c, d = o[1:]
                    cur[c], cur[d], cur[a] = cur[a], cur[c], cur[d]
                    for p in (a, c, d):
                        moved[cur[p]].add("rot")
            assert moved[cur[st["who"]]] == {"swap", "rot"}


def test_graph_bipartite_has_no_triangle_equal_edge_counts_and_the_width_of_the_capacity_fix():
    for lv in range(7):
        yes_e, no_e = [], []
        for b in items(NEW["R1.graph_bipartite_r5"], lv, 60, 15):
            adj: dict[str, set] = {}
            for a, c in b.structured["rivals"]:
                adj.setdefault(a, set()).add(c)
                adj.setdefault(c, set()).add(a)
            assert not any(adj[a] & adj[c] for a, c in b.structured["rivals"])
            assert len(b.structured["people"]) == 13 + lv
            (yes_e if b.answer == "yes" else no_e).append(len(b.structured["rivals"]) - len(b.structured["people"]))
        assert abs(sum(yes_e) / len(yes_e) - sum(no_e) / len(no_e)) < 1.0
    tri = []
    for b in items(OLD["R1.graph_bipartite"], 3, 60, 15):
        adj = {}
        for a, c in b.structured["rivals"]:
            adj.setdefault(a, set()).add(c)
            adj.setdefault(c, set()).add(a)
        tri.append(any(adj[a] & adj[c] for a, c in b.structured["rivals"]))
    assert any(tri)  # the earlier shape: 'a triangle means no'


def _path_len(edges, x, y):
    adj: dict[str, list] = {}
    for a, c in edges:
        adj.setdefault(a, []).append(c)
        adj.setdefault(c, []).append(a)
    dist = {x: 0}
    q = deque([x])
    while q:
        u = q.popleft()
        for v in adj.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist[y]


def test_tree_shapes_ask_the_ends_of_a_long_spine():
    for lv in range(7):
        for b in items(NEW["R1.event_timeline_r5"], lv, 20, 16):
            assert _path_len([(a, c) for a, c, _ in b.structured["rel"]], b.structured["x"], b.structured["y"]) == 4 + lv // 2
        for b in items(NEW["R1.spatial_relative_directions_r5"], lv, 20, 16):
            assert _path_len([(f[0], f[3]) for f in b.structured["facts"]], b.structured["x"], b.structured["y"]) == 5 + lv // 3
        for b in items(NEW["R1.temporal_weekday_shift_r5"], lv, 20, 16):
            assert _path_len([(a, c) for a, c, _ in b.structured["links"]], b.structured["anchor"][0], b.structured["ask"]) == 5 + lv // 3
        for b in items(NEW["R1.equivalence_exchange_rates_r5"], lv, 20, 16):
            assert _path_len([(r[1], r[3]) for r in b.structured["rates"]], b.structured["x"], b.structured["y"]) == 3 + lv // 2


def test_interval_overlap_start_gap_is_independent_of_the_answer():
    def gap(b):
        sp = dict(zip(b.structured["events"], b.structured["spans"], strict=True))
        return abs(sp[b.structured["x"]][1] - sp[b.structured["y"]][1])

    def mean_gap_diff(lin):
        g = {"yes": [], "no": []}
        for lv in range(7):
            for b in items(lin, lv, 80, 17):
                g[b.answer].append(gap(b))
        return abs(sum(g["yes"]) / len(g["yes"]) - sum(g["no"]) / len(g["no"]))

    assert mean_gap_diff(NEW["R1.temporal_interval_overlap_r5"]) < 4
    assert mean_gap_diff(OLD["R1.temporal_interval_overlap"]) > 10


def test_topological_order_has_parallel_chains_and_the_layered_rule_is_not_the_key():
    def layered_hits(lin, level):
        hit = 0
        its = items(lin, level, 120, 18)
        for b in its:
            deps = {p: set(w) for p, w in b.structured["jobs"]}
            depth: dict[str, int] = {}

            def dep(p, deps=deps, depth=depth):
                if p not in depth:
                    depth[p] = 0 if not deps[p] else 1 + max(dep(x) for x in deps[p])
                return depth[p]

            order = sorted(deps, key=lambda p: (dep(p), p))
            hit += order[b.structured["day"] - 1] == b.answer
        return hit / len(its)

    assert layered_hits(NEW["R1.topological_order_r5"], 1) < 0.35
    assert layered_hits(OLD["R1.topological_order_r4"], 1) > 0.5


def test_minimax_trees_are_large_at_every_level():
    def leaves(t):
        return 1 if isinstance(t, int) else sum(leaves(c) for c in t)

    for lv in range(7):
        assert all(leaves(b.structured["tree"]) >= 27 for b in items(NEW["R1.minimax_tree_r5"], lv, 5, 19))
    assert leaves(items(OLD["R1.minimax_tree_r4"], 0, 1, 19)[0].structured["tree"]) == 4


def test_bracket_asks_only_who_wins_and_who_loses_the_final():
    for lv in range(7):
        assert {b.structured["ask"][0] for b in items(NEW["R1.elimination_bracket_r5"], lv, 30, 20)} <= {"champion", "runner_up"}
    assert any(b.structured["ask"][0] == "beaten_by" for b in items(OLD["R1.elimination_bracket_r4"], 5, 30, 20))


def test_categories_follow_a_reading_without_lifting_is_wrong_on_most_yes_and_no_items():
    from studies.m0.r1_fix3_battery import h_catfollow

    def naive_acc(lin, levels):
        hit = tot = 0
        for lv in levels:
            for b in items(lin, lv, 80, 21):
                if b.answer == "cannot be determined":
                    continue
                tot += 1
                hit += h_catfollow(b)["naive_no_lifting"] == b.answer
        return hit / tot

    assert naive_acc(NEW["R1.categories_follow_r5"], range(1, 6)) < 0.3
    assert naive_acc(OLD["R1.categories_follow_r4"], range(1, 6)) > 0.6


def test_venn_level_zero_is_wide_enough_to_carry_the_demand():
    def regions_max(lin):
        return max(max(b.structured["sizes"].values()) for b in items(lin, 0, 80, 22))

    assert regions_max(NEW["R1.venn_counting_r5"]) > 25  # the earlier level 0 drew regions of 1 to 9 (about 11,000 different items)
    assert regions_max(OLD["R1.venn_counting_r4"]) <= 20
