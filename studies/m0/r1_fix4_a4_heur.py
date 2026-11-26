# ruff: noqa
# mypy: ignore-errors
# COPIED from docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/heuristics4.py (= audit3_r1/heuristics4.py) by Claude Opus 5.5 (arbor-auditor), audit 3/4 of R1, for the round-4 re-run (R-24, R-26).
# Edits by the round-4 implementer (Claude Sonnet 5.5), all listed in studies/m0/NOTES_FIX4_R1.md: imports (gen4, heuristics3 -> package modules); the _r5 test also accepts _r6 (the repaired shapes keep the rules written for their _r5 builders)
# ruff: noqa
"""Audit 4 (R1): the auditor's shortcut battery for the fix-round-3 set, per lineage and level, two-sided.

Heuristics: audit 3's generic + specific batteries (heuristics3.py, reused unchanged; run on every shape, an error = does not fire)
plus NEW heuristics written here for the _r5 shapes (functions n_*). Each maps an item (question text + structured fields that
restate the text) to a prediction (str or list of tied str) or None (does not fire). Scoring per level as audit 3:
  eff  = mean credit - chance (a non-firing item scores chance 1/k; 0 for open answers);
  anti = the same for "pick uniformly among the options the heuristic did NOT choose" (closed answers only).
Fitted on a separate draw (seed base FIT): the most frequent key per level (constant), and for open numbers the median ratio
answer / size (size = number of meetings, jobs, ...), applied as round(ratio * size).
usage (implementation worktree root): PYTHONHASHSEED=0 uv run --locked python <this> <n> <seed_base> <fit_base> <out.jsonl> [substr]
"""
import itertools, json, os, re, statistics, sys
from collections import Counter, defaultdict, deque
from fractions import Fraction

from studies.m0 import r1_fix4_a3_heur as H3
from studies.m0 import r1_fix4_gen as gen4

S3 = H3.SPECIFIC


def yn(v):
    return "yes" if v else "no"


# ---------------------------------------------------------------- new heuristics for the _r5 shapes
def n_activity(b):
    ms = [(s, e) for _, s, e in b.structured["meetings"]]
    n = len(ms)
    alone = sum(1 for i, (s, e) in enumerate(ms) if not any(j != i and s2 < e and s < e2 for j, (s2, e2) in enumerate(ms)))
    return {"round_n_2": str(round(n / 2)), "round_0_6n": str(round(0.6 * n)), "round_0_75n": str(round(0.75 * n)),
            "isolated_count": str(alone), "distinct_starts": str(len({s for s, _ in ms})), "n_minus_overlapping_pairs_half": str(n - sum(1 for a, c in itertools.combinations(ms, 2) if a[0] < c[1] and c[0] < a[1]) // 2)}


def _leafs(t):
    return [t] if t[0] == "attr" else ([("NOT", t[1])] if t[0] == "not" and t[1][0] == "attr" else [x for c in t[1:] for x in _leafs(c)])


def n_attr(b):
    st = b.structured
    rule, owners, items = st["rule"], st["owners"], st["items"]
    lv = _leafs(rule)

    def signed(it):
        s = 0
        for l in lv:
            if l[0] == "NOT":
                s -= it[l[1][1]] == l[1][2]
            else:
                s += it[l[1]] == l[2]
        return s

    def neg_matched(it):
        return sum(1 for l in lv if l[0] == "NOT" and it[l[1][1]] == l[1][2])

    def top_operands(it):  # how many top-level operands the badge satisfies (evaluating each operand fully)
        from studies.m0.lineages_r1 import _rule_eval
        return sum(_rule_eval(c, it) for c in rule[1:])

    out = {"signed_match_count": H3.argbest(owners, lambda o: signed(items[owners.index(o)])),
           "fewest_negated_matches": H3.argbest(owners, lambda o: -neg_matched(items[owners.index(o)])),
           "most_top_operands": H3.argbest(owners, lambda o: top_operands(items[owners.index(o)]))}
    return out


def n_catfollow(b):
    st = b.structured
    n = len(st["cats"])
    alls = [tuple(e) for e in st["all"]]; nos = [tuple(p) for p in st["none"]]; somes = [tuple(p) for p in st["some"]]
    x, y, kind = st["x"], st["y"], st["kind"]
    adj = defaultdict(set)
    for a, c in alls + nos + somes:
        adj[a].add(c); adj[c].add(a)
    seen, dq = {x}, deque([x])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); dq.append(v)
    conn = y in seen
    up = {g: {g} for g in range(n)}
    ch = True
    while ch:
        ch = False
        for a, c in alls:
            for g in range(n):
                if a in up[g] and c not in up[g]:
                    up[g].add(c); ch = True
    no_touch = any((p in up[x] and q in up[y]) or (q in up[x] and p in up[y]) for p, q in nos)
    some_touch = any((p in up[x] or p == x) and (q in up[y]) or (q in up[x] and p in up[y]) for p, q in somes)
    common_below = any(x in up[g] and y in up[g] for g in range(n))
    out = {"unconnected_cbd_else_kind_yes": ("cannot be determined" if not conn else "yes"),
           "unconnected_cbd_else_kind_no": ("cannot be determined" if not conn else "no"),
           "lift_no_only": ({"every": None, "all": ("no" if no_touch else ("yes" if y in up[x] else "cannot be determined")), "none": ("yes" if no_touch else "cannot be determined"), "some": ("no" if no_touch else "cannot be determined")}[kind]),
           "overlap_only": ({"all": None, "none": ("no" if (common_below or some_touch) else "cannot be determined"), "some": ("yes" if (common_below or some_touch) else "cannot be determined")}[kind])}
    return out


def n_condchain(b):
    st = b.structured
    facts = {v: bb for v, bb in st["facts"]}
    rules = [([(v, bb) for v, bb in a], (c[0], c[1])) for a, c in st["rules"]]
    q = st["query"]
    qr = [(a, c) for a, c in rules if c[0] == q]
    concl = {c[0] for _, c in rules}
    # forward chaining (modus ponens only) to a fixpoint
    known = dict(facts)
    ch = True
    while ch:
        ch = False
        for a, (cv, cb) in rules:
            if all(known.get(v) == bb for v, bb in a) and cv not in known:
                known[cv] = cb; ch = True
    out = {"forward_chaining": ("yes" if known[q] else "no") if q in known else "cannot be determined",
           "q_rule_with_fact": next((("yes" if c[1] else "no") for a, c in qr if any(v in facts for v, _ in a)), "cannot be determined"),
           "q_rule_with_two_literals": next((("yes" if c[1] else "no") for a, c in qr if len(a) == 2), "cannot be determined"),
           "q_rule_whose_antecedent_is_concluded": (lambda lst: ("yes" if lst[0] else "no") if len(lst) == 1 else "cannot be determined")([c[1] for a, c in qr if any(v in concl for v, _ in a)]),
           # audit-4 fix 2: run 1 took "first / last" from the structured rule list (construction order, not shown); now the TEXT order
           "q_rule_listed_first": (lambda t: ("yes" if t[0] == "true" else "no") if t else None)(re.findall(rf"then {q} is (true|false)\.", b.question)),
           "q_rule_listed_last": (lambda t: ("yes" if t[-1] == "true" else "no") if t else None)(re.findall(rf"then {q} is (true|false)\.", b.question))}
    return out


def n_queue(b):
    st = b.structured
    j = st["ask"][1]
    line = list(st["line"])
    ops = st["ops"]
    ns = sum(1 for o in ops if o[0] == "serve"); nc = sum(1 for o in ops if o[0] == "cut"); nl = sum(1 for o in ops if o[0] == "leave"); nf = sum(1 for o in ops if o[0] == "front_to_back")
    idx = j - 1 + ns + nf + nl - nc
    cuts = [o[1] for o in ops if o[0] == "cut"]
    return {"arith_original_index": line[idx] if 0 <= idx < len(line) else None,
            "arith_ignoring_leaves": line[j - 1 + ns + nf - nc] if 0 <= j - 1 + ns + nf - nc < len(line) else None,
            "jth_last_cut": cuts[-j] if len(cuts) >= j else None, "first_cut": cuts[0] if cuts else None}


def n_bracket(b):
    st = b.structured
    pl = st["players"]; res = st["results"]
    wins = Counter(w for w, _ in res)
    beat = {(w, l) for w, l in res}
    n = len(pl)
    halves = [pl[: n // 2], pl[n // 2:]]
    hb = [max(h, key=lambda p: (sum((p, q) in beat for q in h), -pl.index(p))) for h in halves]
    champ = hb[0] if (hb[0], hb[1]) in beat else hb[1]
    rup = hb[1] if champ == hb[0] else hb[0]
    q = b.question
    out = {"half_best_then_h2h": champ if "wins the tournament" in q else rup}
    quarters = [pl[i: i + n // 4] for i in range(0, n, n // 4)]
    qb = [max(h, key=lambda p: (sum((p, r) in beat for r in h), -pl.index(p))) for h in quarters]
    # quarter winners by record, then the half winner by head-to-head, then the final by head-to-head
    def hh(a, c):
        return a if (a, c) in beat else c
    sf = [hh(qb[i], qb[i + 1]) for i in range(0, len(qb), 2)]
    ch2 = hh(sf[0], sf[1]) if len(sf) == 2 else None
    out["quarter_best_then_h2h"] = (ch2 if "wins the tournament" in q else ([s for s in sf if s != ch2][0] if ch2 else None))
    out["first_round_winner_with_most_wins"] = H3.argbest([hh(a, c) for a, c in zip(pl[0::2], pl[1::2])], lambda p: wins[p])
    return out


def n_eqclass(b):
    st = b.structured
    same = [tuple(e) for e in st["same"]]; diff = [tuple(e) for e in st["different"]]
    x, y = st["x"], st["y"]
    adj = defaultdict(set)
    for a, c in same + diff:
        adj[a].add(c); adj[c].add(a)
    seen, dq = {x}, deque([x])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); dq.append(v)
    conn = y in seen
    # path parity: along the unique BFS path count the different links
    prev = {x: None}; dq = deque([x])
    while dq:
        u = dq.popleft()
        for v in sorted(adj[u]):  # audit-4 fix 3: sorted, so the path chosen does not depend on construction order
            if v not in prev:
                prev[v] = u; dq.append(v)
    ndiff = None
    if y in prev:
        ndiff = 0; u = y
        while prev[u] is not None:
            p = prev[u]
            ndiff += ((p, u) in diff or (u, p) in diff)
            u = p
    return {"connected_same_only_else_cbd": ("yes" if conn and ndiff == 0 else ("no" if conn else "cannot be determined")),
            "connected_means_yes": "yes" if conn else "cannot be determined",
            "bfs_path_one_diff_no": ("yes" if ndiff == 0 else ("no" if ndiff == 1 else "cannot be determined")) if ndiff is not None else "cannot be determined",
            "x_or_y_direct_diff_no": "no" if any(x in e or y in e for e in diff) else None}


def _path(adj, x, y):
    prev = {x: None}; dq = deque([x])
    while dq:
        u = dq.popleft()
        for v, w in adj[u]:
            if v not in prev:
                prev[v] = (u, w); dq.append(v)
    if y not in prev:
        return None
    out = []; u = y
    while prev[u] is not None:
        out.append(prev[u][1]); u = prev[u][0]
    return out[::-1]


def n_event(b):
    st = b.structured
    adj = defaultdict(list)
    for later, earlier, g in st["rel"]:
        adj[earlier].append((later, (g, +1))); adj[later].append((earlier, (g, -1)))
    p = _path(adj, st["x"], st["y"])
    ws = [g for g, _ in p]
    allw = [g for _, _, g in st["rel"]]
    # "ignore before / after": every sentence read as "first-mentioned event is later"; the text order is random, so this is the sign-free walk on a random orientation
    return {"path_unsigned_sum": str(sum(ws)), "path_max": str(max(ws)), "sum_all": str(sum(allw)), "largest_stated": str(max(allw)),
            "path_alt_signs": str(abs(sum(w * (1 if i % 2 == 0 else -1) for i, w in enumerate(ws)))), "path_first": str(ws[0]), "path_last": str(ws[-1]),
            "path_len_times_30": str(30 * len(ws))}


def n_exch(b):
    st = b.structured
    x, y, nn = st["x"], st["y"], st["n"]
    adj = defaultdict(list)
    for p, a, qq, c in st["rates"]:
        adj[a].append((c, (p, qq, +1))); adj[c].append((a, (p, qq, -1)))
    path = _path(adj, x, y)
    # true: one unit of a = qq/p of c along the stated direction; slips: always multiply by (second number / first number) regardless of direction, or always by first/second
    v_slip1, v_slip2, v_true = Fraction(nn), Fraction(nn), Fraction(nn)
    for p, qq, sg in path:
        v_slip1 *= Fraction(qq, p); v_slip2 *= Fraction(p, qq)
        v_true *= Fraction(qq, p) if sg > 0 else Fraction(p, qq)
    out = {"direction_ignored_q_over_p": str(v_slip1) if v_slip1.denominator == 1 else None, "direction_ignored_p_over_q": str(v_slip2) if v_slip2.denominator == 1 else None,
           "inverse_answer": str(Fraction(nn * nn) / v_true) if (Fraction(nn * nn) / v_true).denominator == 1 else None,
           "first_leg_only": None, "last_leg_only": None}
    p0, q0, s0 = path[0]; out["first_leg_only"] = str(nn * (Fraction(q0, p0) if s0 > 0 else Fraction(p0, q0))) if (nn * (Fraction(q0, p0) if s0 > 0 else Fraction(p0, q0))).denominator == 1 else None
    return out


def n_bip(b):
    st = b.structured
    E = [tuple(e) for e in st["rivals"]]
    adj = defaultdict(set)
    for a, c in E:
        adj[a].add(c); adj[c].add(a)
    ppl = sorted(adj)
    # odd cycle of length <= 5 (local search), greedy colouring in listed order without propagation
    def has_short_odd(L):
        for s in ppl:
            dist = {s: 0}; dq = deque([s])
            while dq:
                u = dq.popleft()
                if dist[u] >= L // 2:
                    continue
                for v in adj[u]:
                    if v not in dist:
                        dist[v] = dist[u] + 1; dq.append(v)
                    elif dist[v] == dist[u] and 2 * dist[u] + 1 <= L:
                        return True
        return False
    col = {}
    greedy = "yes"
    for a, c in E:
        if a in col and c in col:
            if col[a] == col[c]:
                greedy = "no"; break
        elif a in col:
            col[c] = 1 - col[a]
        elif c in col:
            col[a] = 1 - col[c]
        else:
            col[a], col[c] = 0, 1
    degs = sorted((len(v) for v in adj.values()), reverse=True)
    return {"odd_cycle_le_5_no": "no" if has_short_odd(5) else "yes", "odd_cycle_le_7_no": "no" if has_short_odd(7) else "yes", "greedy_listed_colouring": greedy,
            "max_degree_ge_4_no": yn(degs[0] < 4), "odd_edge_count_no": yn(len(E) % 2 == 0)}


def n_cousins(b):
    st = b.structured
    par = st["parent"]; x, y = st["x"], st["y"]

    def depth(p):
        d = 0
        while p in par:
            p = par[p]; d += 1
        return d

    px, py = par.get(x), par.get(y)
    return {"same_generation_diff_parents": yn(depth(x) == depth(y) and px != py),
            "same_generation": yn(depth(x) == depth(y)), "both_have_grandparent_diff_parents": yn(px != py and px in par and py in par)}


def n_desc(b):
    st = b.structured
    par = st["parent"]; cands = st["candidates"]
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)

    def lvl(p, d):
        return [p] if d == 0 else [z for k in kids[p] for z in lvl(k, d - 1)]

    def height(p):
        return 0 if not kids[p] else 1 + max(height(k) for k in kids[p])

    return {"most_at_depth3": H3.argbest(cands, lambda c: len(lvl(c, 3))), "most_at_depth2_3": H3.argbest(cands, lambda c: len(lvl(c, 2)) + len(lvl(c, 3))),
            "widest_generation": H3.argbest(cands, lambda c: max(len(lvl(c, d)) for d in range(1, 7))), "shallowest": H3.argbest(cands, lambda c: -height(c)),
            "most_named_in_subtree_text": H3.argbest(cands, lambda c: sum(1 for ch in par if ch in kids[c]))}


def n_kk(b):
    st = b.structured
    ppl = st["people"]; stm = st["statements"]; who = st["who"]
    kind_own = stm[who][0]
    about = Counter()
    for i, (k, a) in enumerate(stm):
        if who in a:
            if k == "is_knight":
                about["knight"] += 1
            elif k == "is_knave":
                about["knave"] += 1
            elif k == "both_knights":
                about["knight"] += 1
            elif k == "some_knave":
                about["knave"] += 1
    vote = None if about["knight"] == about["knave"] else ("knight" if about["knight"] > about["knave"] else "knave")
    return {"own_statement_kind_table": KK_TABLE.get((b_level(b), kind_own)), "about_asked_vote": vote,
            "own_kind_some_knave_knight_both_knave": {"some_knave": "knight", "both_knights": "knave"}.get(kind_own)}


KK_TABLE = {}


def b_level(b):
    return b.structured.get("_level", 0)


def n_minimax(b):
    st = b.structured
    t = st["tree"]; mx = st["first"] == "max"

    def leaves(x):
        return [x] if isinstance(x, int) else [z for c in x for z in leaves(c)]

    def v(x, m):
        if isinstance(x, int):
            return x
        vals = [v(c, not m) for c in x]
        return max(vals) if m else min(vals)

    def two_level(x, m):  # top two levels true, subtrees below replaced by their median leaf
        vals = []
        for c in x:
            vv = [statistics.median_low(leaves(cc)) if not isinstance(cc, int) else cc for cc in c] if not isinstance(c, int) else [c]
            vals.append(min(vv) if m else max(vv))
        return max(vals) if m else min(vals)

    def one_level(x, m):  # top level true, each option valued by its mean leaf
        vals = [round(statistics.mean(leaves(c))) for c in x]
        return max(vals) if m else min(vals)

    return {"two_levels_then_median": str(two_level(t, mx)), "one_level_then_mean": str(one_level(t, mx)),
            "last_mover_only": str((max if (st["depth"] % 2 == 1) == mx else min)(leaves(t)))}


def n_nim(b):
    piles = b.structured["piles"]
    out = {}
    for k in range(1, 5):
        x = 0
        for p in piles:
            x ^= p & ((1 << (k + 1)) - 1)
        out[f"xor_low_{k + 1}_bits"] = "first" if x else "second"
    x = 0
    for p in piles:
        x ^= p >> 4
    out["xor_high_bits_only"] = "first" if x else "second"
    return out


def n_ordercmp(b):
    st = b.structured
    facts = [tuple(f) for f in st["taller"]]; x, y = st["x"], st["y"]
    adj = defaultdict(set); und = defaultdict(set)
    for a, c in facts:
        adj[a].add(c); und[a].add(c); und[c].add(a)

    def reach(s, k):
        seen = {s}; fr = {s}
        for _ in range(k):
            fr = {v for u in fr for v in adj[u]} - seen
            seen |= fr
        return seen

    seen, dq = {x}, deque([x])
    while dq:
        u = dq.popleft()
        for v in und[u]:
            if v not in seen:
                seen.add(v); dq.append(v)
    out = {}
    for k in (3, 4, 5):
        out[f"search_{k}_else_cbd"] = "yes" if y in reach(x, k) else ("no" if x in reach(y, k) else "cannot be determined")
    out["undirected_unconnected_cbd_else_yes"] = "cannot be determined" if y not in seen else "yes"
    return out


def n_road(b):
    st = b.structured
    roads = [tuple(e) for e in st["roads"]]; x, y = st["x"], st["y"]
    adj = defaultdict(set); und = defaultdict(set)
    for a, c in roads:
        adj[a].add(c); und[a].add(c); und[c].add(a)

    def reach(g, s, k=99):
        seen = {s}; fr = {s}
        for _ in range(k):
            fr = {v for u in fr for v in g[u]} - seen
            seen |= fr
        return seen

    out = {"undirected_connected_yes": yn(y in reach(und, x)), "x_mentioned_yes": yn(any(x in e for e in roads))}
    for k in (3, 4, 5):
        out[f"within_{k}"] = yn(y in reach(adj, x, k))
    return out


def n_seat(b):
    st = b.structured
    ppl = st["people"]; clues = st["clues"]; seat = st["seat"]; n = len(ppl)
    placed = {c[1] for c in clues if c[0] == "pos"}
    ends = {c[1] for c in clues if c[0] == "end"}
    free = [ppl[i] for i in range(n) if i not in placed]
    free_e = [ppl[i] for i in range(n) if i not in placed and ((i in ends) == (seat in (0, n - 1)) or not ends)]
    return {"not_placed_uniform": free or None, "not_placed_end_consistent": free_e or None}


def n_reldir(b):
    st = b.structured
    dv = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    adj = defaultdict(list)
    for p, d, k, o in st["facts"]:
        adj[o].append((p, (dv[d][0] * k, dv[d][1] * k))); adj[p].append((o, (-dv[d][0] * k, -dv[d][1] * k)))
    path = _path(adj, st["x"], st["y"])
    dx = sum(v[0] for v in path); dy = sum(v[1] for v in path)
    allk = [f[2] for f in st["facts"]]
    return {"path_unsigned": str(sum(abs(v[0]) + abs(v[1]) for v in path)), "only_ns": str(abs(dy)), "only_ew": str(abs(dx)), "chebyshev": str(max(abs(dx), abs(dy))),
            "euclid_rounded": str(round((dx * dx + dy * dy) ** 0.5)), "sum_all_legs": str(sum(allk)), "signed_axis_merged": str(abs(dx + dy))}


def n_swap(b):
    st = b.structured
    hold = dict(st["hold"]); who = st["who"]
    def sim(skip_swap=False, rev=False, only_last=None):
        s = dict(hold)
        ops = st["ops"] if only_last is None else st["ops"][-only_last:]
        for o in ops:
            if o[0] == "swap":
                if skip_swap:
                    continue
                s[o[1]], s[o[2]] = s[o[2]], s[o[1]]
            else:
                a, c, d = o[1], o[2], o[3]
                if rev:
                    s[a], s[c], s[d] = s[c], s[d], s[a]
                else:
                    s[a], s[c], s[d] = s[d], s[a], s[c]
        return s[who]
    return {"ignore_swaps": sim(skip_swap=True), "rotations_reversed": sim(rev=True), "last_half_only": sim(only_last=max(1, len(st["ops"]) // 2))}


def n_cpath(b):
    jobs = b.structured["jobs"]
    J = {p: (d, deps) for p, d, deps in jobs}
    memo = {}

    def fin(p, pick=None):
        d, deps = J[p]
        if not deps:
            return d
        if pick == "first":
            return fin(deps[0], pick) + d
        if pick == "longest_dur":
            return fin(max(deps, key=lambda z: (J[z][0], z)), pick) + d
        if pick == "sum":
            return sum(fin(z, pick) for z in deps) / 2 + d
        return max(fin(z) for z in deps) + d

    sinks = [p for p in J if not any(p in J[q][1] for q in J)]
    out = {"first_listed_prereq_only": str(max(fin(p, "first") for p in J)), "longest_duration_prereq": str(max(fin(p, "longest_dur") for p in J)),
           "sinks_only_max": str(max(fin(p) for p in sinks)) if sinks else None, "total_div_2": str(round(sum(d for d, _ in J.values()) / 2)),
           "deepest_chain_by_count_times_mean": None}
    return out


def n_overlap(b):
    st = b.structured
    sp = dict(zip(st["events"], st["spans"]))

    def iv(s):
        return (s[1], s[2]) if s[0] == "range" else (s[1], s[1] + s[2] - 1)

    a, c = iv(sp[st["x"]]), iv(sp[st["y"]])
    if a[0] > c[0]:
        a, c = c, a
    la, lc = a[1] - a[0] + 1, c[1] - c[0] + 1
    gap = c[0] - a[0]
    return {"starts_within_12": yn(gap <= 12), "starts_within_6": yn(gap <= 6), "earlier_long_20": yn(la >= 20), "later_shorter": yn(lc < la)}


def n_weekday(b):
    st = b.structured
    anc, d0 = st["anchor"]
    D = st["days"]
    adj = defaultdict(list)
    for later, earlier, k in st["links"]:
        adj[earlier].append((later, k)); adj[later].append((earlier, -k))
    p = _path(adj, anc, st["ask"])
    i0 = D.index(d0)
    return {"path_unsigned": D[(i0 + sum(abs(k) for k in p)) % 7], "path_negated": D[(i0 - sum(p)) % 7], "last_link_only": D[(i0 + p[-1]) % 7],
            "sum_all_links_unsigned": D[(i0 + sum(k for _, _, k in st["links"])) % 7], "off_by_one_plus": D[(i0 + sum(p) + 1) % 7]}


def n_acc(b):
    st = b.structured
    who = st["ask"]

    def sim(skip=(), half_of_start=False, half_round_up=False):
        s = dict(st["start"])
        for o in st["ops"]:
            if o[0] in skip:
                continue
            if o[0] == "pay":
                s[o[1]] -= o[3]; s[o[2]] += o[3]
            elif o[0] == "earn":
                s[o[1]] += o[2]
            else:
                base = st["start"][o[1]] if half_of_start else s[o[1]]
                h = base // 2
                s[o[1]] -= h; s[o[2]] += h
        return str(s[who])

    only_who = [o for o in st["ops"] if who in o[1:3] or (o[0] == "earn" and o[1] == who)]
    return {"ignore_pay": sim(("pay",)), "half_of_start_balance": sim(half_of_start=True), "ignore_earn": sim(("earn",)), "ignore_half": sim(("half",)),
            "pay_direction_reversed": None}


def n_venn(b):
    st = b.structured
    return {}


NEW = {"activity_selection": n_activity, "attribute_rule": n_attr, "categories_follow": n_catfollow, "conditional_chain": n_condchain,
       "containers_queue_line": n_queue, "elimination_bracket": n_bracket, "equivalence_classes": n_eqclass, "equivalence_exchange_rates": n_exch,
       "event_timeline": n_event, "graph_bipartite": n_bip, "kinship_cousins": n_cousins, "kinship_descendants": n_desc, "knights_knaves": n_kk,
       "minimax_tree": n_minimax, "nim_xor": n_nim, "order_compare": n_ordercmp, "road_reachability": n_road, "seating_row": n_seat,
       "spatial_relative_directions": n_reldir, "swap_tracking": n_swap, "temporal_critical_path": n_cpath, "temporal_interval_overlap": n_overlap,
       "temporal_weekday_shift": n_weekday, "tracking_accounts": n_acc}

SIZE = {"activity_selection": lambda st: len(st["meetings"]), "temporal_critical_path": lambda st: len(st["jobs"]), "minimax_tree": lambda st: 1,
        "event_timeline": lambda st: len(st["rel"]), "spatial_relative_directions": lambda st: len(st["facts"]), "tracking_accounts": lambda st: st["start"][st["ask"]],
        "equivalence_exchange_rates": lambda st: st["n"], "venn_counting": lambda st: st["total"]}


def base_of(lid):
    return re.sub(r"_r\d+$", "", lid.split(".", 1)[1])


def preds(lid, b):
    out = dict(H3.generic(b))
    bs = base_of(lid)
    oldk = next((k for k in S3 if base_of(k) == bs), None)
    if oldk:
        try:
            out.update({f"a3:{k}": v for k, v in S3[oldk](b).items()})
        except Exception:
            out["a3:error"] = None
    if lid.endswith(("_r5", "_r6")) and bs in NEW:
        try:
            out.update({f"a4:{k}": v for k, v in NEW[bs](b).items()})
        except Exception as e:
            out["a4:error:" + repr(e)[:40]] = None
    return out


def main():
    n = int(sys.argv[1]); base = int(sys.argv[2]); fit = int(sys.argv[3]); outp = sys.argv[4]; filt = sys.argv[5] if len(sys.argv) > 5 else ""
    L = gen4.lineages()
    fo = open(outp, "w")
    for lid in sorted(L):
        if filt and filt not in lid:
            continue
        bs = base_of(lid)
        for lv in range(7):
            fit_items = gen4.items(L[lid], lv, 400, fit)
            mfk = Counter(b.answer for b in fit_items).most_common(1)[0][0]
            ratio = None
            if bs in SIZE and fit_items[0].k is None:
                rs = [int(b.answer) / max(1, SIZE[bs](b.structured)) for b in fit_items]
                ratio = statistics.median(rs)
            if bs == "knights_knaves":
                tab = defaultdict(Counter)
                for b in fit_items:
                    tab[b.structured["statements"][b.structured["who"]][0]][b.answer] += 1
                for k, c in tab.items():
                    KK_TABLE[(lv, k)] = c.most_common(1)[0][0]
            its = gen4.items(L[lid], lv, n, base)
            acc = defaultdict(lambda: {"eff": [], "anti": [], "hit": []})
            allp = []
            for b in its:
                b.structured["_level"] = lv
                p = {"constant_mfk_fitted": mfk, **preds(lid, b)}
                if ratio is not None:
                    p["fitted_ratio_times_size"] = str(round(ratio * SIZE[bs](b.structured)))
                allp.append(p)
                del b.structured["_level"]
            names = sorted({h for p in allp for h in p})
            for b, p0 in zip(its, allp):
                ch = H3.chance(b)
                for h in names:
                    p = p0.get(h)
                    c = H3.credit(p, b); a = H3.anti(p, b)
                    r = acc[h]
                    r["eff"].append(ch if c is None else c)
                    r["anti"].append(ch if a is None else a)
                    if c is not None:
                        r["hit"].append(c)
            chm = statistics.mean(H3.chance(b) for b in its)
            mode_rate = Counter(b.answer for b in its).most_common(1)[0][1] / len(its)
            for h, r in acc.items():
                fo.write(json.dumps({"lineage": lid, "level": lv, "heuristic": h, "n": len(its), "chance": round(chm, 4), "fired": len(r["hit"]),
                                     "acc_fired": round(statistics.mean(r["hit"]), 4) if r["hit"] else None, "eff": round(statistics.mean(r["eff"]) - chm, 4),
                                     "anti": round(statistics.mean(r["anti"]) - chm, 4) if its[0].k else None, "mode_rate": round(mode_rate, 4)}) + "\n")
        fo.flush()
        print(lid, "done", flush=True)


if __name__ == "__main__":
    main()
