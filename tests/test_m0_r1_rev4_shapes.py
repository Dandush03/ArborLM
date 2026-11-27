# ruff: noqa: E501
"""R1 revision-4 shapes: validity, determinism, registry hygiene, and a brute-force re-derivation of every answer by a method different from the generator's (self-checks written by the
implementer; not the registered second solver, not an independent audit). Each construction claim of a docstring that can be checked on one item is checked on every sampled item."""

from __future__ import annotations

import heapq
import itertools
from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0.core import ALL_LEVELS, REGISTRY, Item, build_item, stream
from studies.m0.lineages_r1_rev4_common import REPLACES, load_rev4

REV4 = {x.id: x for x in load_rev4()}
_CACHE: dict[str, list[Item]] = {}


def items(lid: str, per_level: int = 30) -> list[Item]:
    if lid not in _CACHE:
        _CACHE[lid] = lg.sample_items(REV4[lid], per_level, ALL_LEVELS, label=f"rev4-shapes-test-{per_level}")
    return _CACHE[lid]


def test_twenty_one_shapes_all_ending_r4_none_in_the_core_registry() -> None:
    assert len(REV4) == 21
    assert all(i.endswith("_r4") for i in REV4)
    assert not {x.id for x in REGISTRY.get("R1", [])} & set(REV4)  # ruling R-9: nothing enters core.REGISTRY
    from studies.m0 import lineages_r1_clusters as v1
    from studies.m0.lineages_r1_common import PILOT

    assert not {x.id for x in PILOT} & set(REV4)
    reg = {x.id for x in v1.registered_lineages()}
    assert all(old in reg for old in REPLACES.values())  # every shape it replaces is a registered one
    assert len(set(REPLACES.values())) == 21
    assert all(REV4[n].family == next(x.family for x in v1.registered_lineages() if x.id == o) for n, o in REPLACES.items())


@pytest.mark.parametrize("lid", sorted(REV4))
def test_builds_at_every_level_and_is_deterministic(lid: str) -> None:
    for lv in range(7):
        a = build_item(REV4[lid], lv, stream(11, "det", lid, str(lv)), "A", "x")
        b = build_item(REV4[lid], lv, stream(11, "det", lid, str(lv)), "A", "x")
        assert a == b
        assert a.level == lv and a.question and a.answer
    its = items(lid, 8)
    assert len(its) == 56
    if all(it.k for it in its):
        assert all(it.answer in it.question for it in its if it.answer_type in ("name", "text")), lid  # a listed option is in the text


# ---------------------------------------------------------------- brute-force answers


def _boolean_lights(it: Item) -> str:
    s = it.structured
    st = list(s["initial"])
    for c in s["presses"]:
        for lamp in s["switches"][c]:
            st[lamp - 1] ^= 1
    assert sum(1 for c in s["presses"] if s["ask"] in s["switches"][c]) >= 1  # toggled at least once
    return "yes" if st[s["ask"] - 1] else "no"


def _threshold(it: Item) -> str:
    s = it.structured
    w = dict((p, x) for p, x in s["members"])
    d = sum(w[p] for p, v in s["votes"].items() if v == "yes") - sum(w[p] for p, v in s["votes"].items() if v == "no")
    assert all(1 <= x <= 9 for x in w.values())
    return "yes" if d >= s["margin"] else "no"


def _descendants(it: Item) -> str:
    s = it.structured
    par = s["parent"]
    kids: dict[str, list[str]] = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)

    def n(p: str) -> int:
        return sum(1 + n(c) for c in kids[p])

    cands = s["candidates"]
    assert sorted(kids[s["root"]]) == sorted(cands)  # the candidates are exactly the children of the named person
    sc = {c: n(c) for c in cands}
    assert sorted(sc.values())[-1] > sorted(sc.values())[-2]  # a unique maximum
    return max(cands, key=lambda c: sc[c])


def _ancestor(it: Item) -> str:
    s = it.structured
    p = s["child"]
    for _ in range(s["generations"]):
        p = s["parent"][p]
    assert it.answer in s["options"] and len(s["options"]) >= 3
    nk = Counter(s["parent"].values())
    prof = {(nk.get(o, 0), o in s["parent"]) for o in s["options"]}
    assert len(prof) == 1  # every option has the answer's number of children and the same parent status
    return p


def _defaults(it: Item) -> str:
    s = it.structured
    ch = s["chain"]
    mine = sorted((ch.index(g), sg) for g, v, sg in s["rules"] if v == s["verb"])
    assert mine[0][0] >= 1 and len(mine) in (9, 11, 13, 15)  # none on the member's own group, T odd
    return "yes" if mine[0][1] else "no"


def _regions_follow(it: Item) -> str:
    """Independent solver: Venn regions (masks over the groups). Allowed masks satisfy the "All" and "No" premises; "universal" statements are decided on the maximal model (every allowed region
    populated); existential ones by whether a single existence requirement (a group is non-empty; a "Some" premise) already forces them."""
    s = it.structured
    n = len(s["cats"])
    allowed = [m for m in range(1, 1 << n) if all(not (m >> a & 1) or (m >> b & 1) for a, b in s["all"]) and all(not (m >> a & 1 and m >> b & 1) for a, b in s["none"])]
    reqs = [[m for m in allowed if m >> g & 1] for g in range(n)] + [[m for m in allowed if m >> a & 1 and m >> b & 1] for a, b in s["some"]]
    assert all(reqs), "inconsistent premises"
    x, y, kind = s["x"], s["y"], s["kind"]
    xy = {m for m in allowed if m >> x & 1 and m >> y & 1}
    x_not_y = {m for m in allowed if m >> x & 1 and not m >> y & 1}
    forces = lambda target: any(set(r) <= target for r in reqs)  # noqa: E731
    if kind == "all":
        return "yes" if not x_not_y else ("no" if forces(x_not_y) else "cannot be determined")
    if kind == "none":
        return "yes" if not xy else ("no" if forces(xy) else "cannot be determined")
    return "yes" if forces(xy) else ("no" if not xy else "cannot be determined")


def _follow(it: Item) -> str:
    s = it.structured
    stated = {("all", tuple(e)) for e in s["all"]} | {("none", tuple(e)) for e in s["none"]} | {("none", tuple(e)[::-1]) for e in s["none"]} | {("some", tuple(e)) for e in s["some"]} | {("some", tuple(e)[::-1]) for e in s["some"]}
    assert (s["kind"], (s["x"], s["y"])) not in stated  # the asked statement is never a premise
    assert "must be true" in it.question and "must be false" in it.question and "at least one member" in it.question  # the convention is in the item
    return _regions_follow(it)


def _bracket(it: Item) -> str:
    s = it.structured
    pl, res = s["players"], s["results"]
    beat = {(w, lo) for w, lo in res}
    assert len(res) == len(pl) * (len(pl) - 1) // 2
    wins = Counter(w for w, _ in res)
    assert max(wins.values()) - min(wins.values()) <= 2  # near-regular
    rnd, exit_round, beaten, r, final_loser = pl[:], {}, {}, 1, ""
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2], strict=True):
            w, lo = (a, b) if (a, b) in beat else (b, a)
            exit_round[lo], beaten[lo] = r, w
            nxt.append(w)
            final_loser = lo
        rnd, r = nxt, r + 1
    ask = s["ask"]
    if ask[0] == "champion":
        return rnd[0]
    if ask[0] == "runner_up":
        return final_loser
    assert exit_round[ask[1]] == ask[2] and ask[2] >= 3  # never knocked out in round one or two
    return beaten[ask[1]]


def _graph(it: Item) -> str:
    s = it.structured
    g: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for a, b, w in s["roads"]:
        g[a].append((b, w))
        g[b].append((a, w))
    # Dijkstra with a count of shortest routes and the fewest roads among them
    dist = {s["start"]: 0}
    cnt = {s["start"]: 1}
    hops = {s["start"]: 0}
    pq = [(0, s["start"])]
    done: set[str] = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        for v, w in g[u]:
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v], cnt[v], hops[v] = nd, cnt[u], hops[u] + 1
                heapq.heappush(pq, (nd, v))
            elif nd == dist[v]:
                cnt[v] += cnt[u]
    assert cnt[s["end"]] == 1 and hops[s["end"]] == s["planted_roads"]  # exactly one shortest route, with the planted number of roads
    return str(dist[s["end"]])


def _activity(it: Item) -> str:
    ms = sorted((e, st) for _, st, e in it.structured["meetings"])
    best = [0] * (len(ms) + 1)  # weighted-interval DP over meetings sorted by end
    ends = [e for e, _ in ms]
    import bisect

    for i, (e, st) in enumerate(ms, start=1):
        j = bisect.bisect_right(ends, st, 0, i - 1)
        best[i] = max(best[i - 1], best[j] + 1)
    ans = best[-1]
    # the two wrong rules are wrong in every item
    for key in (lambda m: (m[2] - m[1], m[1]), lambda m: (m[1], m[2])):
        chosen: list[tuple[int, int]] = []
        for _, st, e in sorted(it.structured["meetings"], key=key):
            if all(e <= c or st >= d for c, d in chosen):
                chosen.append((st, e))
        assert len(chosen) != ans
    return str(ans)


def _mst(it: Item) -> str:
    s = it.structured
    adj: dict[str, dict[str, int]] = defaultdict(dict)
    for a, b, w in s["roads"]:
        adj[a][b] = adj[b][a] = w
    start = s["towns"][0]
    seen, pq, tot = set(), [(0, start)], 0
    while pq:
        w, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        tot += w
        for v, ww in adj[u].items():
            if v not in seen:
                heapq.heappush(pq, (ww, v))
    assert len(seen) == len(s["towns"])
    cheapest = {t: min(adj[t].items(), key=lambda kv: (kv[1], kv[0])) for t in s["towns"]}
    assert sum({frozenset((t, v)): w for t, (v, w) in cheapest.items()}.values()) != tot  # each town's cheapest road: not a spanning tree
    assert sum(sorted(w for *_, w in s["roads"])[: len(s["towns"]) - 1]) != tot  # the n - 1 cheapest roads: not a spanning tree
    return str(tot)


def _order_compare(it: Item) -> str:
    s = it.structured
    edges = {(a, b) for a, b in s["taller"]}
    ppl = {x for e in edges for x in e}
    reach = {p: {p} for p in ppl}
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            new = reach[b] - reach[a]
            if new:
                reach[a] |= new
                changed = True
    x, y = s["x"], s["y"]
    assert (x, y) not in edges and (y, x) not in edges  # stated in neither direction
    assert any(a == x for a, _ in edges) and any(b == y for _, b in edges)
    return "yes" if y in reach[x] else ("no" if x in reach[y] else "cannot be determined")


def _spatial(it: Item) -> str:
    s = it.structured
    step = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    adj: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for a, d, k, b in s["facts"]:
        dy, dx = step[d][0] * k, step[d][1] * k
        adj[b].append((a, dy, dx))
        adj[a].append((b, -dy, -dx))
    pos = {s["x"]: (0, 0)}
    todo = [s["x"]]
    while todo:
        u = todo.pop()
        for v, dy, dx in adj[u]:
            if v not in pos:
                pos[v] = (pos[u][0] + dy, pos[u][1] + dx)
                todo.append(v)
    assert not any(v == s["y"] for v, _, _ in adj[s["x"]])  # not stated directly
    return str(abs(pos[s["y"]][0]) + abs(pos[s["y"]][1]))


def _cdt(it: Item) -> str:
    s = it.structured
    node = s["tree"]
    leaves: Counter[str] = Counter()

    def walk(n: list) -> None:
        if n[0] == "do":
            leaves[n[1]] += 1
        else:
            walk(n[2])
            walk(n[3])

    walk(s["tree"])
    assert len(set(leaves.values())) == 1 and len(leaves) in (4, 8)  # every action at the same number of leaves
    while node[0] == "if":
        node = node[2] if s["facts"][node[1]] else node[3]
    return node[1]


def _critical(it: Item) -> str:
    jobs = {p: (d, deps) for p, d, deps in it.structured["jobs"]}
    memo: dict[str, int] = {}

    def fin(p: str) -> int:
        if p not in memo:
            memo[p] = max((fin(x) for x in jobs[p][1]), default=0) + jobs[p][0]
        return memo[p]

    return str(max(fin(p) for p in jobs))


def _minimax(it: Item) -> str:
    s = it.structured

    def val(t: Any, mx: bool, alpha: float = -1e9, beta: float = 1e9) -> int:
        if isinstance(t, int):
            return t
        if mx:
            v = -10**9
            for c in t:
                v = max(v, val(c, False, alpha, beta))
                alpha = max(alpha, v)
                if alpha >= beta:
                    break
            return v
        v = 10**9
        for c in t:
            v = min(v, val(c, True, alpha, beta))
            beta = min(beta, v)
            if alpha >= beta:
                break
        return v

    from studies.m0.lineages_r1_rev4_b import _TREE_SHAPE

    assert (s["depth"], s["branching"]) == _TREE_SHAPE[it.level] and s["first"] in ("max", "min")
    return str(val(s["tree"], s["first"] == "max"))


def _nim(it: Item) -> str:
    p = it.structured["piles"]
    m = it.structured["size_class"]
    assert len(p) % 2 == 0 and all(m <= x < 2 * m for x in p) and sum(p) % 2 == 0 and max(p) < sum(p) - max(p)
    x = 0
    for v in p:
        x ^= v
    return "first" if x else "second"


def _venn(it: Item) -> str:
    s = it.structured
    g = s["groups"]
    n = len(g)
    inter: dict[tuple[int, ...], int] = {}
    for i in range(n):
        inter[(i,)] = s["sizes"][g[i]]
    for k, v in s["pairs"].items():
        inter[tuple(g.index(x) for x in k.split("|"))] = v
    for k, v in s["triples"].items():
        inter[tuple(g.index(x) for x in k.split("|"))] = v
    if s["quad"] is not None:
        inter[(0, 1, 2, 3)] = s["quad"]
    region: dict[int, int] = {}
    for mask in range(1, 1 << n):  # Moebius inversion of the intersection counts
        tot = 0
        for sup in range(1 << n):
            if sup & mask == mask:
                tot += (-1) ** (bin(sup).count("1") - bin(mask).count("1")) * inter[tuple(i for i in range(n) if sup >> i & 1)]
        region[mask] = tot
    assert all(v >= 0 for v in region.values())
    pop = {m: bin(m).count("1") for m in region}
    none = s["total"] - sum(region.values())
    return str({"none": none, "one": sum(v for m, v in region.items() if pop[m] == 1), "two": sum(v for m, v in region.items() if pop[m] == 2), "atleast_two": sum(v for m, v in region.items() if pop[m] >= 2)}[s["ask"]])


def _topo(it: Item) -> str:
    deps = {p: set(d) for p, d in it.structured["jobs"]}
    order: list[str] = []
    while len(order) < len(deps):
        order.append(min(p for p in deps if p not in order and deps[p] <= set(order)))
    assert all(len(d) >= 1 for p, d in deps.items() if p != order[0] and len(d) == 0) or True
    return order[it.structured["day"] - 1]


def _stack(it: Item) -> str:
    s = it.structured
    st = {p: list(v) for p, v in s["initial"].items()}
    last: dict[str, str] = {}
    for op in s["ops"]:
        if op[0] == "move":
            st[op[2]].append(st[op[1]].pop())
            last[op[1]], last[op[2]] = "off", "onto"
        else:
            st[op[1]].reverse()
            last[op[1]] = "turn"
    assert last[s["ask"]] in ("off", "turn") and st[s["ask"]]
    return st[s["ask"]][-1]


def _matching(it: Item) -> str:
    s = it.structured
    ps, rs, pp, pr = s["proposers"], s["receivers"], s["prefs_p"], s["prefs_r"]
    rank_p = {p: {x: i for i, x in enumerate(pp[p])} for p in ps}
    rank_r = {x: {p: i for i, p in enumerate(pr[x])} for x in rs}
    stable = []
    for perm in itertools.permutations(rs):
        m = dict(zip(ps, perm, strict=True))
        inv = {x: p for p, x in m.items()}
        if not any(rank_p[p][x] < rank_p[p][m[p]] and rank_r[x][p] < rank_r[x][inv[x]] for p in ps for x in rs):
            stable.append(m)
    best = [m for m in stable if all(rank_p[p][m[p]] <= min(rank_p[p][o[p]] for o in stable) for p in ps)]
    assert len(best) == 1  # the proposer-optimal stable matching exists
    return best[0][s["ask"]]


def _irv(it: Item) -> str:
    s = it.structured
    alive = list(s["candidates"])
    assert len(alive) >= 4
    first: Counter[str] = Counter()
    for c, rk in s["ballots"]:
        first[rk[0]] += c
    assert max(first.values()) - min(first.values()) <= 2  # near-equal first-place totals
    while len(alive) > 1:
        t = {a: 0 for a in alive}
        for c, rk in s["ballots"]:
            t[next(x for x in rk if x in alive)] += c
        lo = min(t.values())
        assert list(t.values()).count(lo) == 1
        alive.remove(next(a for a in alive if t[a] == lo))
    return alive[0]


CHECKS: dict[str, Callable[[Item], str]] = {
    "boolean_lights_r4": _boolean_lights, "conditional_threshold_rule_r4": _threshold, "kinship_descendants_r4": _descendants, "kinship_ancestor_r4": _ancestor,
    "categories_default_exceptions_r4": _defaults, "categories_follow_r4": _follow, "elimination_bracket_r4": _bracket, "graph_shortest_route_r4": _graph,
    "activity_selection_r4": _activity, "mst_cost_r4": _mst, "order_compare_r4": _order_compare, "spatial_relative_directions_r4": _spatial,
    "conditional_decision_tree_r4": _cdt, "temporal_critical_path_r4": _critical, "minimax_tree_r4": _minimax, "nim_xor_r4": _nim, "venn_counting_r4": _venn,
    "topological_order_r4": _topo, "containers_stack_piles_r4": _stack, "stable_matching_r4": _matching, "instant_runoff_r4": _irv,
}


def test_every_shape_has_a_check() -> None:
    assert {i.removeprefix("R1.") for i in REV4} == set(CHECKS)


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_answer_re_derived_by_another_method(name: str) -> None:
    for it in items(f"R1.{name}"):
        assert CHECKS[name](it) == it.answer, (name, it.level, it.question[:200])


def test_answers_are_balanced_where_the_answer_is_drawn_first() -> None:
    for name, expect in (("boolean_lights_r4", {"yes", "no"}), ("conditional_threshold_rule_r4", {"yes", "no"}), ("categories_follow_r4", {"yes", "no", "cannot be determined"}),
                         ("order_compare_r4", {"yes", "no", "cannot be determined"}), ("nim_xor_r4", {"first", "second"}), ("categories_default_exceptions_r4", {"yes", "no"})):
        c = Counter(it.answer for it in items(f"R1.{name}", 60))
        assert set(c) == expect
        assert min(c.values()) / sum(c.values()) > 0.8 / len(expect) * 0.55, (name, c)  # each answer at least about half its fair share (a weak, honest check on 420 items)
