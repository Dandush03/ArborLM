# ruff: noqa: E501
"""R1 fix round 3: independent re-derivation of the answer key of every rebuilt shape from its structured form (a self-check, NOT the independent second solver that ruling R-9 requires),
the registry and cluster-map invariants, the NOT REGISTERED exclusion (ruling R-12), determinism across processes, and the absence of any redraw on a heuristic's outcome (rulings R-1, R-13)."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import subprocess
import sys
from collections import deque
from fractions import Fraction
from pathlib import Path

import pytest

from studies.m0 import lineages_r1_fix3_clusters as c3
from studies.m0.core import Retry
from studies.m0.lineages_r1_fix3_common import REPLACES, load_fix3

ROOT = Path(__file__).resolve().parents[1]
NEW = [x for x in load_fix3() if x.id not in c3.NOT_REGISTERED_V3]
ALL_NEW = load_fix3()


def draw(lin, level: int, n: int, seed: int):
    r = random.Random(seed * 100 + level)
    out = []
    tries = 0
    while len(out) < n and tries < 60 * n:
        tries += 1
        try:
            out.append(lin.build(level, r))
        except Retry:
            continue
    assert len(out) == n, f"{lin.id} level {level}: too many Retry"
    return out


# ---------------------------------------------------------------- independent solvers (read only the structured form)


def s_order(st):
    t = {(a, b) for a, b in st["taller"]}
    ppl = sorted({x for p in t for x in p})

    def reach(a, b):
        seen, q = {a}, deque([a])
        while q:
            u = q.popleft()
            for x, y in t:
                if x == u and y not in seen:
                    seen.add(y)
                    q.append(y)
        return b in seen

    return "yes" if reach(st["x"], st["y"]) else ("no" if reach(st["y"], st["x"]) else "cannot be determined") if ppl else "?"


def s_road(st):
    n = len(st["towns"])
    adj = {i: [] for i in range(n)}
    for a, b in st["roads"]:
        adj[a].append(b)
    seen, q = {st["x"]}, deque([st["x"]])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return "yes" if st["y"] in seen else "no"


def s_equiv(st):
    par = {}

    def f(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for a, b in st["same"]:
        par[f(a)] = f(b)
    if f(st["x"]) == f(st["y"]):
        return "yes"
    if any({f(a), f(b)} == {f(st["x"]), f(st["y"])} for a, b in st["different"]):
        return "no"
    return "cannot be determined"


def s_cpath(st):
    jobs = {p: (d, w) for p, d, w in st["jobs"]}
    memo: dict[str, int] = {}

    def fin(p):
        if p not in memo:
            memo[p] = jobs[p][0] + max((fin(x) for x in jobs[p][1]), default=0)
        return memo[p]

    return str(max(fin(p) for p in jobs))


def s_activity(st):
    ms = sorted((e, s) for _, s, e in st["meetings"])  # dynamic programming over meetings sorted by end
    best = [0] * (len(ms) + 1)
    for i, (e, s) in enumerate(ms, start=1):
        j = max((k for k in range(i) if k == 0 or ms[k - 1][0] <= s), default=0)
        best[i] = max(best[i - 1], best[j] + 1)
    return str(best[-1])


def s_topo(st):
    deps = {p: set(w) for p, w in st["jobs"]}
    done: list[str] = []
    while len(done) < len(deps):
        ready = sorted(p for p in deps if p not in done and deps[p] <= set(done))
        done.append(ready[0])
    return done[st["day"] - 1]


def s_nim(st):
    x = 0
    for p in st["piles"]:
        x ^= p
    return "first" if x else "second"


def s_grid(st):
    g = st["grid"]
    i, j = st["start"]
    for m in st["moves"]:
        di, dj = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}[m]
        if 0 <= i + di < len(g) and 0 <= j + dj < len(g[0]) and g[i + di][j + dj]:
            i, j = i + di, j + dj
    return g[i][j]


def s_queue(st):
    cur = list(st["line"])
    for o in st["ops"]:
        if o[0] == "join":
            cur.append(o[1])
        elif o[0] == "cut":
            cur.insert(0, o[1])
        elif o[0] == "serve":
            cur.pop(0)
        elif o[0] == "leave":
            cur.remove(o[1])
        else:
            cur.append(cur.pop(0))
    return cur[st["ask"][1] - 1]


def s_accounts(st):
    b = dict(st["start"])
    for o in st["ops"]:
        if o[0] == "pay":
            b[o[1]] -= o[3]
            b[o[2]] += o[3]
            assert b[o[1]] >= 0
        elif o[0] == "earn":
            b[o[1]] += o[2]
        else:
            h = b[o[1]] // 2
            assert b[o[1]] % 2 == 0
            b[o[1]] -= h
            b[o[2]] += h
    return str(b[st["ask"]])


def s_swap(st):
    h = dict(st["hold"])
    for o in st["ops"]:
        if o[0] == "swap":
            h[o[1]], h[o[2]] = h[o[2]], h[o[1]]
        else:
            a, b, c = o[1:]
            h[b], h[c], h[a] = h[a], h[b], h[c]
    return h[st["who"]]


def s_bip(st):
    adj: dict[str, set[str]] = {}
    for a, b in st["rivals"]:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    col: dict[str, int] = {}
    for s0 in sorted(adj):
        if s0 in col:
            continue
        col[s0] = 0
        q = deque([s0])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in col:
                    col[v] = 1 - col[u]
                    q.append(v)
                elif col[v] == col[u]:
                    return "no"
    return "yes"


def s_overlap(st):
    sp = dict(zip(st["events"], st["spans"], strict=True))

    def days(s):
        return set(range(s[1], s[2] + 1)) if s[0] == "range" else set(range(s[1], s[1] + s[2]))

    return "yes" if days(sp[st["x"]]) & days(sp[st["y"]]) else "no"


def s_weekday(st):
    adj: dict[str, list] = {}
    for later, earlier, k in st["links"]:
        adj.setdefault(earlier, []).append((later, k))
        adj.setdefault(later, []).append((earlier, -k))
    val = {st["anchor"][0]: st["days"].index(st["anchor"][1])}
    q = deque([st["anchor"][0]])
    while q:
        u = q.popleft()
        for v, k in adj.get(u, []):
            if v not in val:
                val[v] = val[u] + k
                q.append(v)
    return st["days"][val[st["ask"]] % 7]


def s_minimax(st):
    def v(t, mx):
        return t if isinstance(t, int) else (max if mx else min)(v(c, not mx) for c in t)

    return str(v(st["tree"], st["first"] == "max"))


def s_reldir(st):
    pos = {st["x"]: (0, 0)}
    changed = True
    d = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    while changed:
        changed = False
        for a, dr, k, b in st["facts"]:  # a lies k blocks dr of b
            if b in pos and a not in pos:
                pos[a] = (pos[b][0] + d[dr][0] * k, pos[b][1] + d[dr][1] * k)
                changed = True
            elif a in pos and b not in pos:
                pos[b] = (pos[a][0] - d[dr][0] * k, pos[a][1] - d[dr][1] * k)
                changed = True
    return str(abs(pos[st["y"]][0]) + abs(pos[st["y"]][1]))


def s_event(st):
    day = {st["x"]: 0}
    changed = True
    while changed:
        changed = False
        for later, earlier, g in st["rel"]:
            if earlier in day and later not in day:
                day[later] = day[earlier] + g
                changed = True
            elif later in day and earlier not in day:
                day[earlier] = day[later] - g
                changed = True
    return str(abs(day[st["y"]]))


def s_exchange(st):
    val = {st["x"]: Fraction(1)}  # value of one unit
    changed = True
    while changed:
        changed = False
        for p, a, q, b in st["rates"]:  # p units of a = q units of b
            if a in val and b not in val:
                val[b] = val[a] * p / q
                changed = True
            elif b in val and a not in val:
                val[a] = val[b] * q / p
                changed = True
    ans = st["n"] * val[st["x"]] / val[st["y"]]
    assert ans.denominator == 1
    return str(ans.numerator)


def s_cousins(st):
    par = st["parent"]
    x, y = st["x"], st["y"]
    return "yes" if x in par and y in par and par[x] != par[y] and par.get(par[x]) is not None and par.get(par[x]) == par.get(par[y]) else "no"


def s_desc(st):
    kids: dict[str, list] = {}
    for c, p in st["parent"].items():
        kids.setdefault(p, []).append(c)

    def cnt(p):
        return sum(1 + cnt(k) for k in kids.get(p, []))

    return max(st["candidates"], key=cnt)


def s_knights(st):
    ppl = st["people"]
    n = len(ppl)
    sols = []
    for kn in itertools.product((True, False), repeat=n):
        ok = True
        for i, (k, a) in enumerate(st["statements"]):
            v = {"is_knight": lambda: kn[a[0]], "is_knave": lambda: not kn[a[0]], "both_knights": lambda: kn[a[0]] and kn[a[1]], "some_knave": lambda: not (kn[a[0]] and kn[a[1]]),
                 "same_kind": lambda: kn[a[0]] == kn[a[1]], "differ": lambda: kn[a[0]] != kn[a[1]]}[k]()
            if v != kn[i]:
                ok = False
                break
        if ok:
            sols.append(kn)
    assert len(sols) == 1
    return "knight" if sols[0][st["who"]] else "knave"


def s_seating(st):
    ppl = st["people"]
    n = len(ppl)
    outs = set()
    for perm in itertools.permutations(range(n)):
        pos = {p: i for i, p in enumerate(perm)}
        ok = True
        for c in st["clues"]:
            t = c[0]
            if t == "adj":
                ok = pos[c[2]] == pos[c[1]] + 1
            elif t == "left":
                ok = pos[c[1]] < pos[c[2]]
            elif t == "end":
                ok = pos[c[1]] in (0, n - 1)
            elif t == "pos":
                ok = pos[c[1]] == c[2]
            elif t == "between":
                ok = pos[c[1]] < pos[c[2]] < pos[c[3]] or pos[c[3]] < pos[c[2]] < pos[c[1]]
            else:
                ok = abs(pos[c[1]] - pos[c[2]]) != 1
            if not ok:
                break
        if ok:
            outs.add(ppl[perm[st["seat"]]])
    assert len(outs) == 1
    return outs.pop()


def s_chain(st):
    vs = st["vars"]
    idx = {v: i for i, v in enumerate(vs)}
    seen = set()
    for w in range(1 << len(vs)):
        val = lambda v: bool((w >> idx[v]) & 1)  # noqa: E731
        if any(val(v) != b for v, b in st["facts"]):
            continue
        if all(not all(val(v) == b for v, b in a) or val(c[0]) == c[1] for a, c in st["rules"]):
            seen.add(val(st["query"]))
    return "cannot be determined" if len(seen) == 2 else ("yes" if True in seen else "no")


def s_attr(st):
    from studies.m0.lineages_r1 import _rule_eval

    ok = [o for o, it in zip(st["owners"], st["items"], strict=True) if _rule_eval(st["rule"], it)]
    assert len(ok) == 1
    return ok[0]


def s_bracket(st):
    beat = {(w, lo) for w, lo in st["results"]}
    rnd = list(st["players"])
    final_loser = ""
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2], strict=True):
            w, lo = (a, b) if (a, b) in beat else (b, a)
            nxt.append(w)
            final_loser = lo if len(rnd) == 2 else final_loser
        rnd = nxt
    return rnd[0] if st["ask"][0] == "champion" else final_loser


def s_cats(st):
    from studies.m0.lineages_r1_rev4 import _closure_facts

    n = len(st["cats"])
    cl = _closure_facts(n, [tuple(e) for e in st["all"]], [tuple(e) for e in st["none"]], [tuple(e) for e in st["some"]])
    assert cl is not None
    m, wit = cl
    x, y = st["x"], st["y"]
    up = [{t for t in range(n) if m[i][t]} for i in range(n)]
    dis = lambda a, b: any((p in up[a] and q in up[b]) or (q in up[a] and p in up[b]) for p, q in st["none"])  # noqa: E731
    ov = lambda a, b: any(a in f and b in f for f in wit)  # noqa: E731
    if st["kind"] == "all":
        return "yes" if m[x][y] else ("no" if any(x in f and any(dis(g, y) for g in f) for f in wit) else "cannot be determined")
    if st["kind"] == "none":
        return "yes" if dis(x, y) else ("no" if ov(x, y) else "cannot be determined")
    return "yes" if ov(x, y) else ("no" if dis(x, y) else "cannot be determined")


def s_venn(st):
    return None  # the closed formulas are checked in the earlier tests; r5 only widens magnitudes


SOLVERS = {
    "order_compare": s_order, "road_reachability": s_road, "equivalence_classes": s_equiv, "temporal_critical_path": s_cpath, "activity_selection": s_activity, "topological_order": s_topo,
    "nim_xor": s_nim, "spatial_grid_walk": s_grid, "containers_queue_line": s_queue, "tracking_accounts": s_accounts, "swap_tracking": s_swap, "graph_bipartite": s_bip,
    "temporal_interval_overlap": s_overlap, "temporal_weekday_shift": s_weekday, "minimax_tree": s_minimax, "spatial_relative_directions": s_reldir, "event_timeline": s_event,
    "equivalence_exchange_rates": s_exchange, "kinship_cousins": s_cousins, "kinship_descendants": s_desc, "knights_knaves": s_knights, "seating_row": s_seating,
    "conditional_chain": s_chain, "attribute_rule": s_attr, "elimination_bracket": s_bracket, "categories_follow": s_cats,
}


def base(lin) -> str:
    return lin.id.split(".", 1)[1].rsplit("_r", 1)[0]


@pytest.mark.parametrize("lin", [x for x in NEW if base(x) in SOLVERS], ids=lambda x: x.id)
def test_independent_solver_agrees_with_the_key(lin):
    solve = SOLVERS[base(lin)]
    for level in range(7):
        for b in draw(lin, level, 12, 31):
            assert solve(b.structured) == b.answer, (lin.id, level, b.question[:200])


def test_every_registered_shape_has_a_solver_or_is_venn():
    missing = [base(x) for x in NEW if base(x) not in SOLVERS]
    assert missing == ["venn_counting"], missing


# ---------------------------------------------------------------- registry, map, exclusion


def test_the_set_is_37_shapes_in_23_clusters_and_the_auditors_merges_hold():
    reg = c3.registered_v3()
    ct = c3.cluster_table_v3()
    assert len(reg) == 37 and len(ct) == 23
    assert c3.cluster_of_v3("R1.conditional_chain_r5") == c3.cluster_of_v3("R1.knights_knaves_r5") == c3.cluster_of_v3("R1.one_culprit")
    assert c3.cluster_of_v3("R1.elimination_bracket_r5") == c3.cluster_of_v3("R1.attribute_rule_r5") == c3.cluster_of_v3("R1.minimax_tree_r5")
    assert len({x.id for x in reg}) == 37


def test_not_registered_shapes_are_nowhere_in_the_map_or_the_fixtures():
    ids = {x.id for x in c3.registered_v3()}
    for lid in c3.NOT_REGISTERED_V3:
        assert lid not in ids
    fx = ROOT / "studies/m0/fixtures/r1_fix3"
    if fx.exists():
        for lid in c3.NOT_REGISTERED_V3:
            assert not (fx / f"{lid}.jsonl").exists()
    # a shape removed outright leaves no cluster of its own
    assert "R1.elimination_josephus" not in c3.cluster_table_v3() and "R1.order_extreme" not in c3.cluster_table_v3() and "R1.order_tournament_wins" not in c3.cluster_table_v3()
    assert "R1.instant_runoff" not in c3.cluster_table_v3() and "R1.stable_matching" not in c3.cluster_table_v3()


def test_no_cluster_spans_both_parts_under_the_cluster_keys_reading():
    ck = c3.partition_readings_v3()["cluster_keys"]
    for cid, members in c3.cluster_table_v3().items():
        assert len({ck[m.id] for m in members}) == 1, cid


def test_every_replacement_target_is_in_the_version_2_set():
    from studies.m0 import lineages_r1_clusters_v2 as v2

    ids = {x.id for x in v2.registered_v2()}
    assert all(old in ids for old in REPLACES.values())


# ---------------------------------------------------------------- reproducibility and the ban on redraws by heuristic


def test_generation_is_deterministic_across_processes():
    code = (
        "import hashlib, random, sys\n"
        "sys.path.insert(0, '.')\n"
        "from studies.m0.core import Retry\n"
        "from studies.m0.lineages_r1_fix3_clusters import registered_v3\n"
        "h = hashlib.sha256()\n"
        "for lin in registered_v3():\n"
        "    if not lin.id.endswith('_r5'): continue\n"
        "    for lv in (0, 3, 6):\n"
        "        r = random.Random(17 + lv); k = 0\n"
        "        while k < 3:\n"
        "            try: b = lin.build(lv, r)\n"
        "            except Retry: continue\n"
        "            h.update((b.question + '|' + b.answer).encode()); k += 1\n"
        "print(h.hexdigest())\n"
    )
    outs = []
    for seed in ("0", "0"):
        p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-500:]
        outs.append(p.stdout.strip())
    assert outs[0] == outs[1] and len(outs[0]) == 64


def test_no_fix3_module_redraws_on_a_heuristic():
    for f in sorted((ROOT / "studies/m0").glob("lineages_r1_fix3*.py")):
        src = f.read_text()
        for banned in ("_anti(", "credit(", "ANTI_P", "anti_override", "SPECIFIC", "generic(", "shortcuts import"):
            assert banned not in src, (f.name, banned)


def test_every_shape_builds_at_every_level_with_a_consistent_k():
    for lin in ALL_NEW:
        for level in range(7):
            for b in draw(lin, level, 4, 5):
                assert b.answer and isinstance(b.question, str)
                assert (b.k is None) == (b.answer_type == "number"), lin.id
                assert hashlib.sha256(json.dumps(b.structured, sort_keys=True).encode()).hexdigest()
