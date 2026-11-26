# ruff: noqa
# mypy: ignore-errors
# COPIED from docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/heuristics3.py (= audit3_r1/heuristics3.py) by Claude Opus 5.5 (arbor-auditor), audit 3/4 of R1, for the round-4 re-run (R-24, R-26).
# Edits by the round-4 implementer (Claude Sonnet 5.5), all listed in studies/m0/NOTES_FIX4_R1.md: imports (gen, solvers3 -> package modules); h_mst iterates sorted(set(...)) (package hygiene test)
# ruff: noqa
"""Audit 3 (R1): the auditor's own shortcut battery, per lineage and level, two-sided.

Each heuristic maps an item (question text + structured form fields that restate the text) to a prediction (str or
list of tied str) or None (does not fire). Scoring per level:
  eff   = mean credit - chance, where an item the heuristic does not fire on gets the chance credit (1/k; 0 if open);
  anti  = the same for "pick uniformly among the options the heuristic did NOT choose" (closed answers only);
  fired = how many items it fired on, acc = accuracy on those.
The constant most-frequent-key per level is fitted on a separate draw (seed base FIT) and scored on the main draw.
Nothing from studies.m0 is imported except the generators (through gen.py).

usage (worktree root): PYTHONHASHSEED=0 uv run --locked python <this> <n_per_level> <seed_base> <fit_seed_base> [lineage-substring]
"""
import itertools, json, os, re, statistics, sys
from collections import Counter, defaultdict, deque

from studies.m0 import r1_fix4_a3_solvers as SV
from studies.m0 import r1_fix4_gen as gen

NAME = r"[A-Z][a-z]+"


def opts(b):
    o = SV.opts_of(b.question)
    if o:
        return o
    st = b.structured
    for k in ("candidates", "people", "events", "players", "items"):
        if k in st and isinstance(st[k], list) and st[k] and isinstance(st[k][0], str):
            return sorted(st[k])
    if b.answer_type == "yn":
        return ["yes", "no"]
    if b.answer_type == "ynu":
        return ["yes", "no", "cannot be determined"]
    return None


def cnt(text, w):
    return len(re.findall(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", text))


def firstpos(text, w):
    m = re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", text)
    return m.start() if m else 10 ** 9


def lastpos(text, w):
    ms = list(re.finditer(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", text))
    return ms[-1].start() if ms else -1


def argbest(cands, key, best=max):
    if not cands:
        return None
    vals = {c: key(c) for c in cands}
    t = best(vals.values())
    return [c for c in cands if vals[c] == t]


def generic(b):
    out = {}
    o = opts(b)
    q = b.question
    bd = q[: q.rfind("?")] if "?" in q else q
    bd = re.sub(r"Choose from .*$", "", bd)
    if b.answer_type in ("name", "text") and o:
        out["first_mentioned"] = argbest(o, lambda c: -firstpos(bd, c))
        out["last_mentioned"] = argbest(o, lambda c: lastpos(bd, c))
        out["most_mentioned"] = argbest(o, lambda c: cnt(bd, c))
        out["least_mentioned"] = argbest(o, lambda c: -cnt(bd, c))
        out["alpha_first"] = [sorted(o)[0]]
        out["alpha_last"] = [sorted(o)[-1]]
        out["longest_name"] = argbest(o, len)
        out["shortest_name"] = argbest(o, lambda c: -len(c))
    if b.answer_type == "number":
        nums = [int(x) for x in re.findall(r"(?<![\w])-?\d+", bd)]
        if nums:
            out["largest_number"] = str(max(nums))
            out["smallest_number"] = str(min(nums))
            out["last_number"] = str(nums[-1])
            out["first_number"] = str(nums[0])
            out["modal_number"] = str(Counter(nums).most_common(1)[0][0])
            out["sum_numbers"] = str(sum(nums))
    return out


# ------------------------------------------------------------------ specific batteries
def h_activity(b):
    ms = [(int(a), int(c)) for a, c in re.findall(r"from minute (\d+) to minute (\d+)", b.question)]
    n = len(ms)

    def greedy(key, touch_ok=True):
        acc = []
        for m in sorted(ms, key=key):
            if all((m[0] >= x[1] or m[1] <= x[0]) if touch_ok else (m[0] > x[1] or m[1] < x[0]) for x in acc):
                acc.append(m)
        return str(len(acc))

    nested = sum(1 for m in ms if any(x != m and m[0] <= x[0] and x[1] <= m[1] for x in ms))
    return {"shortest_first": greedy(lambda m: (m[1] - m[0], m[0])), "earliest_start": greedy(lambda m: (m[0], m[1])),
            "listed_order": greedy(lambda m: 0), "latest_start_first": greedy(lambda m: (-m[0], -m[1])),
            "earliest_finish_touch_overlaps": greedy(lambda m: (m[1], m[0]), touch_ok=False),
            "n_minus_containing": str(n - nested), "round_2n_3": str(round(2 * n / 3)), "n_minus_1": str(n - 1), "n_minus_2": str(n - 2)}


def h_topo(b):
    st = b.structured
    jobs = {p: set(d) for p, d in st["jobs"]}
    j = st["day"]
    depth = {}

    def dep(p):
        if p not in depth:
            depth[p] = 0 if not jobs[p] else 1 + max(dep(x) for x in jobs[p])
        return depth[p]

    layered = sorted(jobs, key=lambda p: (dep(p), p))
    anc = {}

    def A(p):
        if p not in anc:
            anc[p] = set().union(*[A(x) | {x} for x in jobs[p]]) if jobs[p] else set()
        return anc[p]

    listed = [p for p, _ in st["jobs"]]
    nprereq = [p for p in jobs if len(A(p)) == j - 1]
    by_nprereq = sorted(jobs, key=lambda p: (len(A(p)), p))

    def kahn(key):
        done, order = set(), []
        while len(order) < len(jobs):
            ready = sorted((p for p in jobs if p not in done and jobs[p] <= done), key=key)
            order.append(ready[0]); done.add(ready[0])
        return order

    return {"layered_depth_then_name": layered[j - 1], "jth_alphabetical": sorted(jobs)[j - 1], "jth_listed": listed[j - 1],
            "ancestors_eq_j_minus_1": nprereq or None, "sort_by_ancestor_count": by_nprereq[j - 1],
            "kahn_listed_order": kahn(lambda p: listed.index(p))[j - 1],
            "kahn_reverse_alpha": kahn(lambda p: [-ord(c) for c in p] + [0] * (12 - len(p)))[j - 1]}


def h_attr(b):
    st = b.structured
    rule, owners, items = st["rule"], st["owners"], st["items"]

    def ev(r, it, drop_not=False, all_or=False, all_and=False):
        op = r[0]
        if op == "attr":
            return it[r[1]] == r[2]
        if op == "not":
            return ev(r[1], it, drop_not, all_or, all_and) if drop_not else not ev(r[1], it, drop_not, all_or, all_and)
        vals = [ev(x, it, drop_not, all_or, all_and) for x in r[1:]]
        if all_or:
            return any(vals)
        if all_and:
            return all(vals)
        return all(vals) if op == "and" else any(vals)

    def leaves(r):
        return [r] if r[0] == "attr" else [l for x in r[1:] for l in leaves(x)]

    lv = leaves(rule)
    out = {}
    for nm, kw in (("drop_negation", dict(drop_not=True)), ("all_or", dict(all_or=True)), ("all_and", dict(all_and=True))):
        ok = [o for o, it in zip(owners, items) if ev(rule, it, **kw)]
        out[nm] = ok or None
    out["most_leaves_matched"] = argbest(owners, lambda o: sum(items[owners.index(o)][l[1]] == l[2] for l in lv))
    out["matches_first_leaf"] = [o for o, it in zip(owners, items) if it[lv[0][1]] == lv[0][2]] or None
    out["matches_last_leaf"] = [o for o, it in zip(owners, items) if it[lv[-1][1]] == lv[-1][2]] or None
    out["first_listed_badge"] = [owners[0]]
    out["last_listed_badge"] = [owners[-1]]
    return out


def h_dtree(b):
    st = b.structured
    t, facts = st["tree"], st["facts"]

    def walk(node, pick):
        while node[0] == "if":
            node = pick(node)
        return node[1]

    leaves = []

    def L(n):
        if n[0] == "do":
            leaves.append(n[1])
        else:
            L(n[2]); L(n[3])
    L(t)
    return {"all_then": walk(t, lambda n: n[2]), "all_else": walk(t, lambda n: n[3]), "first_leaf": leaves[0], "last_leaf": leaves[-1],
            "first_cond_only_then_first": walk(t[2] if facts[t[1]] else t[3], lambda n: n[2]),
            "negate_all": walk(t, lambda n: n[3] if facts[n[1]] else n[2]),
            "ignore_last_condition": walk(t, lambda n: (n[2] if facts[n[1]] else n[3]) if n[2][0] == "if" else n[2])}


def h_threshold(b):
    st = b.structured
    w = dict(st["members"]); v = st["votes"]; D = st["margin"]
    yes = sum(w[p] for p in w if v[p] == "yes"); no = sum(w[p] for p in w if v[p] == "no")
    ny = sum(1 for p in w if v[p] == "yes"); nn = sum(1 for p in w if v[p] == "no")
    ab = sum(w[p] for p in w if v[p] == "abstain")
    mw = statistics.mean(w.values())
    yn = lambda c: "yes" if c else "no"
    return {"yes_weight_ge_D": yn(yes >= D), "count_margin_ge_D": yn(ny - nn >= D), "abstain_as_no": yn(yes - no - ab >= D), "abstain_as_yes": yn(yes + ab - no >= D),
            "D_le_0": yn(D <= 0), "more_yes_votes": yn(ny > nn), "more_yes_weight": yn(yes > no), "approx_count_times_mean": yn((ny - nn) * mw >= D),
            "strict_gt_D": yn(yes - no > D), "heaviest_voter": yn(v[max(w, key=lambda p: (w[p], p))] == "yes"), "off_by_one_low": yn(yes - no >= D + 1)}


def h_boolean(b):
    st = b.structured
    init, sw, pr, a = st["initial"], st["switches"], st["presses"], st["ask"]
    s0 = init[a - 1]
    cnt_p = Counter(pr)
    par_distinct = sum(1 for c in cnt_p if a in sw[c]) % 2
    par_all = sum(1 for c in pr if a in sw[c]) % 2
    last_toggles = a in sw[pr[-1]]
    yn = lambda x: "yes" if x else "no"
    return {"initial_state": yn(s0), "flip_initial": yn(1 - s0), "each_switch_once": yn(s0 ^ par_distinct), "last_press_flips": yn(s0 ^ last_toggles),
            "wired_switch_count_parity": yn(s0 ^ (sum(1 for c in sw if a in sw[c]) % 2)), "presses_parity_all": yn(s0 ^ (len(pr) % 2)),
            "majority_on_at_start": yn(sum(init) * 2 > len(init)), "ignore_initial": yn(par_all)}


def h_cde(b):
    st = b.structured
    chain, rules, verb = st["chain"], st["rules"], st["verb"]
    pos = {g: i for i, g in enumerate(chain)}
    rv = sorted((pos[g], ok) for g, v, ok in rules if v == verb)
    yn = lambda x: "yes" if x else "no"
    listed = [ok for g, v, ok in rules if v == verb]
    q = b.question
    out = {"majority_sign": yn(sum(ok for _, ok in rv) * 2 > len(rv)), "first_listed_rule": yn(listed[0]), "last_listed_rule": yn(listed[-1]),
           "least_specific_rule": yn(rv[-1][1]), "second_nearest_rule": yn(rv[1][1]), "third_nearest_rule": yn(rv[2][1]),
           "rule_at_distance_1": yn(rv[0][1]) if rv[0][0] == 1 else None, "odd_yes_count": yn(sum(ok for _, ok in rv) % 2),
           "all_can": yn(all(ok for _, ok in rv))}
    sents = re.findall(r"Every (\w+) is an? (\w+)\.", q)
    order = []
    for a, c in sents:
        for g in (a, c):
            if g not in order:
                order.append(g)
    rg = {g: ok for g, v, ok in rules if v == verb}
    first_text = next((g for g in order if g in rg), None)
    out["first_rule_group_in_chain_text"] = yn(rg[first_text]) if first_text else None
    near = [ok for d, ok in rv if d <= 3]
    out["partial_walk_3"] = yn(near[0]) if near else None
    # a rule whose group is named in the member sentence's neighbourhood: the group directly above the member's own group, stated in the text
    return out


def h_catfollow(b):
    st = b.structured
    alls, nos, somes, kind, x, y = [tuple(e) for e in st["all"]], [tuple(e) for e in st["none"]], [tuple(e) for e in st["some"]], st["kind"], st["x"], st["y"]
    n = len(st["cats"])
    reach = [[i == j for j in range(n)] for i in range(n)]
    for a, c in alls:
        reach[a][c] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if reach[i][k] and reach[k][j]:
                    reach[i][j] = True
    direct_no = (x, y) in nos or (y, x) in nos
    direct_some = (x, y) in somes or (y, x) in somes
    out = {}
    if kind == "all":
        out["naive_no_lifting"] = "yes" if reach[x][y] else ("no" if direct_no else "cannot be determined")
        out["all_reach_else_cbd"] = "yes" if reach[x][y] else "cannot be determined"
    elif kind == "none":
        out["naive_no_lifting"] = "yes" if direct_no else ("no" if direct_some or reach[x][y] or reach[y][x] else "cannot be determined")
        out["all_reach_else_cbd"] = "no" if reach[x][y] or reach[y][x] else "cannot be determined"
    else:
        out["naive_no_lifting"] = "yes" if direct_some or reach[x][y] or reach[y][x] else ("no" if direct_no else "cannot be determined")
        out["all_reach_else_cbd"] = "yes" if reach[x][y] or reach[y][x] else "cannot be determined"
    out["x_has_outgoing_all"] = "yes" if any(a == x for a, _ in alls) else "cannot be determined"
    out["x_or_y_in_a_no"] = "no" if any(x in p or y in p for p in nos) else None
    out["mentions_both_in_one_premise"] = "yes" if any({x, y} == set(p) for p in [*alls, *nos, *somes]) else None
    out["kind_constant"] = {"all": "cannot be determined", "none": "no", "some": "yes"}[kind]
    return out


def h_compass(b):
    st = b.structured
    dirs = ["north", "east", "south", "west"]
    s = dirs.index(st["start"])
    amt = {"left": 3, "right": 1, "around": 2, "cw90": 1, "cw270": 3, "ccw90": 3, "cw180": 2}
    turns = [v for k, v in st["seq"] if k == "turn"]
    return {"start_direction": dirs[s],
            "ccw_as_cw": dirs[(s + sum({**amt, "ccw90": 1}[t] for t in turns)) % 4],
            "ignore_180s": dirs[(s + sum(amt[t] for t in turns if amt[t] != 2)) % 4],
            "cw270_as_90": dirs[(s + sum({**amt, "cw270": 1}[t] for t in turns)) % 4],
            "left_right_only": dirs[(s + sum(amt[t] for t in turns if t in ("left", "right"))) % 4],
            "last_turn_only": dirs[(s + (amt[turns[-1]] if turns else 0)) % 4],
            "opposite_of_start": dirs[(s + 2) % 4]}


def h_condchain(b):
    st = b.structured
    facts = {v: bb for v, bb in st["facts"]}
    qv = st["query"]
    rules = st["rules"]
    concl = [c for a, c in rules if c[0] == qv]
    out = {"query_is_fact_else_cbd": ("yes" if facts[qv] else "no") if qv in facts else "cannot be determined",
           "never_concluded_cbd": "cannot be determined" if qv not in facts and not concl else None,
           "majority_conclusion_sign": (("yes" if sum(c[1] for c in concl) * 2 > len(concl) else "no") if concl else None),
           "one_step_forward": None}
    for a, c in rules:
        if c[0] == qv and all(facts.get(v) is bb for v, bb in a):
            out["one_step_forward"] = "yes" if c[1] else "no"
            break
    if qv in facts:
        out["one_step_forward"] = "yes" if facts[qv] else "no"
    return out


def h_queue(b):
    st = b.structured
    j = st["ask"][1]

    def sim(skip=()):
        cur = list(st["line"])
        for o in st["ops"]:
            k = o[0]
            if k in skip:
                continue
            if k == "join":
                cur.append(o[1])
            elif k == "cut":
                cur.insert(0, o[1])
            elif k == "serve":
                if cur: cur.pop(0)
            elif k == "leave":
                if o[1] in cur: cur.remove(o[1])
            else:
                if cur: cur.append(cur.pop(0))
        return cur[j - 1] if len(cur) >= j else None

    joins = [o[1] for o in st["ops"] if o[0] == "join"]; cuts = [o[1] for o in st["ops"] if o[0] == "cut"]
    return {"ignore_leave": sim(("leave",)), "ignore_front_to_back": sim(("front_to_back",)), "ignore_serve": sim(("serve",)), "ignore_cut": sim(("cut",)),
            "initial_position_j": st["line"][j - 1] if len(st["line"]) >= j else None, "last_joiner": joins[-1] if joins else None, "last_cut": cuts[-1] if cuts else None}


def h_stack(b):
    st = b.structured
    a = st["ask"]

    def sim(skip_rev=False):
        s = {p: list(v) for p, v in st["initial"].items()}
        for o in st["ops"]:
            if o[0] == "reverse":
                if not skip_rev:
                    s[o[1]].reverse()
            elif s[o[1]]:
                s[o[2]].append(s[o[1]].pop())
        return s[a][-1] if s[a] else None

    def sim_bottom_after_turn():  # misreading "turn upside down" as "the bottom block goes to the top"
        s = {p: list(v) for p, v in st["initial"].items()}
        for o in st["ops"]:
            if o[0] == "reverse":
                if s[o[1]]:
                    s[o[1]].append(s[o[1]].pop(0))
            elif s[o[1]]:
                s[o[2]].append(s[o[1]].pop())
        return s[a][-1] if s[a] else None

    init = st["initial"][a]
    return {"ignore_turns": sim(skip_rev=True), "turn_moves_bottom_to_top": sim_bottom_after_turn(), "initial_top": init[-1] if init else None, "initial_bottom": init[0] if init else None}


def h_bracket(b):
    st = b.structured
    pl = st["players"]; res = st["results"]
    beat = {(w, l) for w, l in res}
    wins = Counter(w for w, _ in res)
    n = len(pl)
    ask = st["ask"]
    out = {"most_wins": argbest(pl, lambda p: wins[p])}
    if ask[0] == "beaten_by":
        x = ask[1]; i = pl.index(x)
        half = n // 2; q = n // 4
        hstart = (i // half) * half
        qstart = (i // q) * q
        other_q = [p for k, p in enumerate(pl[hstart:hstart + half], start=hstart) if not (qstart <= k < qstart + q)]
        out["beater_in_own_half"] = [p for p in other_q if (p, x) in beat] or None
        out["any_beater_of_x"] = [p for p in pl if (p, x) in beat]
        out["most_wins_in_other_quarter"] = argbest(other_q, lambda p: wins[p])
    else:
        half = n // 2
        inside = lambda grp: argbest(grp, lambda p: sum((p, o) in beat for o in grp))
        out["best_in_each_half"] = (inside(pl[:half]) or []) + (inside(pl[half:]) or [])
    return out


def h_josephus(b):
    st = b.structured
    ppl, k = st["people"], st["step"]
    n = len(ppl)
    out = {}
    if st["ask"][0] == "leave":
        j = st["ask"][1]
        out["no_removal_index"] = ppl[(j * k - 1) % n]
        out["every_kth_first_pass"] = ppl[j * k - 1] if j * k - 1 < n else None
    else:
        out["kth_person"] = ppl[(k - 1) % n]
        out["first_person"] = ppl[0]
        out["last_person"] = ppl[-1]
    return out


def h_eqclass(b):
    st = b.structured
    same = [tuple(p) for p in st["same"]]; diff = [tuple(p) for p in st["different"]]
    x, y = st["x"], st["y"]
    nb = defaultdict(set)
    for a, c in same:
        nb[a].add(c); nb[c].add(a)
    dn = defaultdict(set)
    for a, c in diff:
        dn[a].add(c); dn[c].add(a)
    return {"common_same_neighbour_else_cbd": "yes" if nb[x] & nb[y] else "cannot be determined",
            "x_or_y_has_a_different": "no" if dn[x] or dn[y] else None,
            "one_step_no": "no" if (dn[x] & nb[y]) or (dn[y] & nb[x]) else None,
            "both_have_same_links_yes": "yes" if nb[x] and nb[y] else "cannot be determined"}


def h_exchange(b):
    st = b.structured
    rates = st["rates"]
    items = st["items"]
    more = Counter(); less = Counter(); small = {}
    for p, a, q, c in rates:
        if p < q:
            more[a] += 1; less[c] += 1
        elif q < p:
            more[c] += 1; less[a] += 1
        small[a] = min(small.get(a, 10 ** 9), p); small[c] = min(small.get(c, 10 ** 9), q)
    local_max = [i for i in items if less[i] == 0 and more[i] > 0]
    return {"local_max": local_max or None, "most_local_wins": argbest(items, lambda i: more[i] - less[i]), "smallest_unit_count": argbest(items, lambda i: -small[i])}


def h_event(b):
    st = b.structured
    rel = st["rel"]; ask = st["ask"]; evs = st["events"]
    later = Counter(r[0] for r in rel); earlier = Counter(r[1] for r in rel)
    cand = [e for e in evs if later[e] == 0] if ask == "first" else [e for e in evs if earlier[e] == 0]
    big = max(rel, key=lambda r: r[2])
    return {"never_on_the_wrong_side": cand or None, "end_of_largest_gap": [big[1] if ask == "first" else big[0]],
            "net_side_count": argbest(evs, lambda e: (earlier[e] - later[e]) if ask == "first" else (later[e] - earlier[e]))}


def h_bip(b):
    st = b.structured
    ppl = st["people"]; rv = [tuple(r) for r in st["rivals"]]
    n, m = len(ppl), len(rv)
    adj = defaultdict(set)
    for a, c in rv:
        adj[a].add(c); adj[c].add(a)
    tri = any(adj[a] & adj[c] for a, c in rv)
    return {"triangle_means_no": "no" if tri else "yes", "edges_ge_n": "no" if m >= n else "yes", "edges_gt_n": "no" if m > n else "yes",
            "edges_ge_n_plus_1": "no" if m >= n + 1 else "yes", "tree_means_yes": "yes" if m <= n - 1 else None,
            "anyone_with_3_rivals": "no" if any(len(adj[p]) >= 3 for p in ppl) else "yes"}


def h_route(b):
    st = b.structured
    es = st["roads"]; s, t = st["start"], st["end"]
    adj = defaultdict(dict)
    for a, c, w in es:
        adj[a][c] = w; adj[c][a] = w
    out = {"direct_road": str(adj[s][t]) if t in adj[s] else None}
    two = [adj[s][m] + adj[m][t] for m in adj[s] if t in adj[m]]
    out["best_two_road"] = str(min(two)) if two else None
    cur, seen, tot = s, {s}, 0
    for _ in range(40):
        if cur == t:
            break
        nxt = [(w, v) for v, w in adj[cur].items() if v not in seen]
        if not nxt:
            tot = None; break
        w, v = min(nxt); tot += w; cur = v; seen.add(v)
    out["nearest_neighbour_walk"] = str(tot) if tot is not None and cur == t else None
    dist = {s: (0, 0)}; dq = deque([s])
    while dq:
        u = dq.popleft()
        for v, w in adj[u].items():
            cand = (dist[u][0] + 1, dist[u][1] + w)
            if v not in dist or cand < dist[v]:
                dist[v] = cand; dq.append(v)
    out["fewest_roads_then_length"] = str(dist[t][1]) if t in dist else None
    return out


def h_runoff(b):
    st = b.structured
    c = st["candidates"]; bal = st["ballots"]
    first = Counter(); borda = Counter()
    for n, rk in bal:
        first[rk[0]] += n
        for i, x in enumerate(rk):
            borda[x] += n * (len(rk) - 1 - i)
    out = {"plurality": argbest(c, lambda x: first[x]), "borda": argbest(c, lambda x: borda[x]), "anti_plurality_last": argbest(c, lambda x: -sum(n for n, rk in bal if rk[-1] == x))}
    top2 = sorted(c, key=lambda x: (-first[x], x))[:2]
    a, d = top2
    va = sum(n for n, rk in bal if rk.index(a) < rk.index(d))
    vd = sum(n for n, rk in bal if rk.index(d) < rk.index(a))
    out["top_two_runoff"] = [a] if va > vd else ([d] if vd > va else [a, d])
    cw = [x for x in c if all(sum(n for n, rk in bal if rk.index(x) < rk.index(y)) > sum(n for n, rk in bal if rk.index(y) < rk.index(x)) for y in c if y != x)]
    out["condorcet_winner"] = cw or None
    low = min(c, key=lambda x: first[x])
    rest = [x for x in c if x != low]
    t = Counter()
    for n, rk in bal:
        t[next(x for x in rk if x in rest)] += n
    out["one_elimination_then_plurality"] = argbest(rest, lambda x: t[x])
    return out


def h_ancestor(b):
    st = b.structured
    par = st["parent"]; ch = st["child"]; k = st["generations"]
    o = st["options"]

    def up(p, m):
        for _ in range(m):
            if p not in par:
                return None
            p = par[p]
        return p

    root = ch
    while root in par:
        root = par[root]
    nk = Counter(par.values())
    return {"k_minus_1": up(ch, k - 1) if up(ch, k - 1) in o else None, "k_plus_1": up(ch, k + 1) if up(ch, k + 1) in o else None,
            "root_of_family": root if root in o else None, "parentless_option": [p for p in o if p not in par] or None,
            "most_children_option": argbest(o, lambda p: nk[p])}


def h_cousins(b):
    st = b.structured
    par = st["parent"]; x, y = st["x"], st["y"]
    gp = lambda p: par.get(par.get(p, ""), None)

    def root(p):
        while p in par:
            p = par[p]
        return p

    return {"share_grandparent_any": "yes" if gp(x) and gp(x) == gp(y) else "no", "same_family_root": "yes" if root(x) == root(y) else "no",
            "different_parents": "yes" if par.get(x) != par.get(y) else "no"}


def h_desc(b):
    st = b.structured
    par = st["parent"]; c = st["candidates"]
    kids = defaultdict(list)
    for a, p in par.items():
        kids[p].append(a)

    def height(p):
        return 0 if not kids[p] else 1 + max(height(k) for k in kids[p])

    def gc(p):
        return sum(len(kids[k]) for k in kids[p])

    return {"most_children": argbest(c, lambda p: len(kids[p])), "most_grandchildren": argbest(c, gc), "deepest_line": argbest(c, height),
            "most_children_plus_grandchildren": argbest(c, lambda p: len(kids[p]) + gc(p))}


def h_kk(b):
    st = b.structured
    stm = st["statements"]; who = st["who"]
    acc = [s for s in stm if s[0] == "is_knave" and s[1][0] == who]
    sup = [s for s in stm if s[0] == "is_knight" and s[1][0] == who]
    own = stm[who]
    return {"called_knave_means_knave": "knave" if acc else None, "called_knight_means_knight": "knight" if sup else None,
            "self_doubt_means_knight": "knight" if own[0] == "some_knave" and who in own[1] else None,
            "self_praise_means_knave": "knave" if own[0] == "both_knights" and who in own[1] else None,
            "accuses_someone_means_knave": "knave" if own[0] in ("is_knave", "some_knave") else "knight"}


def h_minimax(b):
    st = b.structured
    t = st["tree"]; first = st["first"]

    def leaves(x):
        return [x] if isinstance(x, int) else [l for c in x for l in leaves(c)]

    lv = leaves(t)
    srt = sorted(lv)

    def v(x, mx, alt=True):
        if isinstance(x, int):
            return x
        vals = [v(c, (not mx) if alt else mx, alt) for c in x]
        return max(vals) if mx else min(vals)

    def greedy(x, mx):
        while not isinstance(x, int):
            x = (max if mx else min)(x, key=lambda c: (max if mx else min)(leaves(c)))
            mx = not mx
        return x

    return {"median_low": str(srt[(len(srt) - 1) // 2]), "median_high": str(srt[len(srt) // 2]), "max_leaf": str(srt[-1]), "min_leaf": str(srt[0]),
            "no_alternation": str(v(t, first == "max", alt=False)), "wrong_first_mover": str(v(t, first != "max")), "greedy_best_leaf": str(greedy(t, first == "max")),
            "first_leaf": str(lv[0]), "mean_leaf_rounded": str(round(statistics.mean(lv)))}


def h_mst(b):
    st = b.structured
    es = sorted((w, a, c) for a, c, w in st["roads"])
    towns = sorted({x for _, a, c in es for x in (a, c)})
    n = len(towns)
    cheapest = {}
    for w, a, c in es:
        cheapest.setdefault(a, (w, a, c)); cheapest.setdefault(c, (w, a, c))
    out = {"n_minus_1_cheapest": str(sum(w for w, _, _ in es[: n - 1])), "each_town_cheapest_distinct": str(sum(w for w, _, _ in sorted(set(cheapest.values()))))}
    s = re.search(r"between (\w+) and", b.question).group(1)
    INF = 10 ** 9
    d = {t: INF for t in towns}; d[s] = 0; par = {}
    left = set(towns)
    adj = defaultdict(list)
    for w, a, c in es:
        adj[a].append((c, w)); adj[c].append((a, w))
    while left:
        u = min(left, key=lambda t: (d[t], t)); left.remove(u)
        for v, w in adj[u]:
            if v in left and d[u] + w < d[v]:
                d[v] = d[u] + w; par[v] = w
    out["shortest_path_tree"] = str(sum(par.values()))
    cur, seen, tot = s, {s}, 0
    while len(seen) < n:
        cand = [(w, v) for v, w in adj[cur] if v not in seen]
        if not cand:
            tot = None; break
        w, v = min(cand); tot += w; cur = v; seen.add(v)
    out["nearest_neighbour_path"] = str(tot) if tot is not None else None
    # MST of the cheap roads only (roads <= 10) plus the single cheapest road between groups: needs the groups, so use "Kruskal on roads <= 10, then add the cheapest > 10 roads n - 1 - used"
    return out


def h_nim(b):
    p = b.structured["piles"]
    b1 = sum((v >> 1) & 1 for v in p) % 2
    b2 = sum((v >> 2) & 1 for v in p) % 2
    fs = lambda c: "first" if c else "second"
    return {"bit1_parity": fs(b1), "bit2_parity": fs(b2), "bits1_2_parity": fs(b1 or b2), "sum_mod4": fs(sum(p) % 4), "max_gt_half_rest": fs(max(p) * 2 > sum(p)),
            "all_distinct": fs(len(set(p)) == len(p))}


def h_culprit(b):
    st = b.structured
    ppl = st["people"]; s = st["statements"]
    named_was = Counter(x[1] for x in s if x[0] == "was")
    named_either = Counter(y for x in s if x[0] == "either" for y in x[1:])
    named_not = Counter(x[1] for x in s if x[0] == "not")
    acc = lambda p: named_was[ppl.index(p)] + named_either[ppl.index(p)]
    return {"most_accused": argbest(ppl, acc), "least_accused": argbest(ppl, acc, best=min),
            "never_denied": [p for i, p in enumerate(ppl) if named_not[i] == 0] or None,
            "most_denied": argbest(ppl, lambda p: named_not[ppl.index(p)])}


def h_ordercmp(b):
    st = b.structured
    tl = [tuple(p) for p in st["taller"]]
    x, y = st["x"], st["y"]
    out_ = Counter(a for a, _ in tl); in_ = Counter(c for _, c in tl)
    allp = {a for a, _ in tl} | {c for _, c in tl}
    two = any((x, z) in tl and (z, y) in tl for z in allp)
    two_r = any((y, z) in tl and (z, x) in tl for z in allp)
    return {"two_step_else_cbd": "yes" if two else ("no" if two_r else "cannot be determined"),
            "outdegree_compare": "yes" if out_[x] > out_[y] else ("no" if out_[x] < out_[y] else "cannot be determined"),
            "net_degree_compare": "yes" if out_[x] - in_[x] > out_[y] - in_[y] else "no", "always_cbd": "cannot be determined"}


def h_extreme(b):
    st = b.structured
    tl = [tuple(p) for p in st["taller"]]
    ppl = st["people"]
    c = Counter(x for p in tl for x in p)
    q = b.question
    subj_taller = re.findall(rf"({NAME}) is taller than", q)
    return {"mentioned_once": [p for p in ppl if c[p] == 1] or None, "first_taller_subject": [subj_taller[0]] if subj_taller else None}


def h_rr(b):
    st = b.structured
    res = st["results"]; ppl = st["players"]
    first_w = Counter()
    for w, l in res[: len(res) // 2]:
        first_w[w] += 1
    return {"half_of_results_tally": argbest(ppl, lambda p: first_w[p] if st["ask"] == "most" else -first_w[p])}


def h_pets(b):
    st = b.structured
    ppl, cl, ask = st["people"], st["clues"], st["ask"]
    n = len(ppl)
    excl = defaultdict(set); owns = {}
    for c in cl:
        if c[0] == "not":
            excl[c[1]].add(c[2])
        elif c[0] == "owns":
            owns[c[1]] = c[2]
        else:
            excl[c[1]] |= {p for p in range(n) if p not in c[2:]}
    stated = [ppl[i] for i, p in owns.items() if p == ask]
    either = [ppl[c[1]] for c in cl if c[0] == "either" and ask in c[2:]]
    return {"stated_owner": stated or None, "named_in_either_with_pet": either or None,
            "never_excluded_from_pet": [ppl[i] for i in range(n) if ask not in excl[i] and i not in owns] or None}


def h_road(b):
    st = b.structured
    rd = [tuple(e) for e in st["roads"]]
    x, y = st["x"], st["y"]
    outd = Counter(a for a, _ in rd); ind = Counter(c for _, c in rd)
    two = (x, y) in rd or any((x, z) in rd and (z, y) in rd for z in range(len(st["towns"])))
    return {"direct_road": "yes" if (x, y) in rd else "no", "within_two": "yes" if two else "no", "y_no_incoming": "no" if ind[y] == 0 else None,
            "x_no_outgoing": "no" if outd[x] == 0 else None, "unmentioned_no": "no" if (outd[x] + ind[x] == 0 or outd[y] + ind[y] == 0) else None,
            "reverse_road": "yes" if (y, x) in rd else None, "many_roads_yes": "yes" if len(rd) >= 2 * len(st["towns"]) else "no",
            "x_outdeg_ge_2_yes": "yes" if outd[x] >= 2 else "no"}


def h_seat(b):
    st = b.structured
    ppl, cl, seat = st["people"], st["clues"], st["seat"]
    n = len(ppl)
    stated = [ppl[c[1]] for c in cl if c[0] == "pos" and c[2] == seat]
    ends = [ppl[c[1]] for c in cl if c[0] == "end"]
    cm = Counter()
    for c in cl:
        for x in (c[1:] if c[0] != "pos" else c[1:2]):
            cm[x] += 1
    return {"stated_seat": stated or None, "end_person_for_end_seat": (ends or None) if seat in (0, n - 1) else None,
            "least_constrained": argbest(ppl, lambda p: -cm[ppl.index(p)]), "most_constrained": argbest(ppl, lambda p: cm[ppl.index(p)])}


def h_grid(b):
    st = b.structured
    g = st["grid"]; R, C = len(g), len(g[0]); pos = tuple(st["start"])
    d = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}

    def sim(walls=True, mirror_cols=False):
        p = pos
        for m in st["moves"]:
            dj = -d[m][1] if mirror_cols else d[m][1]
            i, j = p[0] + d[m][0], p[1] + dj
            if not (0 <= i < R and 0 <= j < C):
                continue
            if walls and g[i][j] is None:
                continue
            p = (i, j)
        return g[p[0]][p[1]]

    di = sum(d[m][0] for m in st["moves"]); dj = sum(d[m][1] for m in st["moves"])
    ni, nj = min(max(pos[0] + di, 0), R - 1), min(max(pos[1] + dj, 0), C - 1)
    out = {"ignore_walls": sim(walls=False), "net_displacement_clamped": g[ni][nj], "start_cell": g[pos[0]][pos[1]], "east_west_mirrored": sim(mirror_cols=True)}
    return {k: v for k, v in out.items()}


def h_reldir(b):
    st = b.structured
    facts = st["facts"]; x, y = st["x"], st["y"]
    adj = defaultdict(list)
    for a, dr, k, c in facts:
        adj[a].append((c, k)); adj[c].append((a, k))
    prev = {x: None}; dq = deque([x])
    while dq:
        u = dq.popleft()
        for v, k in adj[u]:
            if v not in prev:
                prev[v] = (u, k); dq.append(v)
    path = []
    u = y
    while prev[u]:
        path.append(prev[u][1]); u = prev[u][0]
    return {"sum_along_path_unsigned": str(sum(path)), "max_on_path": str(max(path)), "last_leg": str(path[0]), "first_leg": str(path[-1])}


def h_match(b):
    st = b.structured
    pp, pr, a = st["prefs_p"], st["prefs_r"], st["ask"]
    rs = st["receivers"]
    free = list(rs); nxt = {r: 0 for r in rs}; held = {}
    while free:
        r = free.pop(0); p = pr[r][nxt[r]]; nxt[r] += 1
        if p not in held:
            held[p] = r
        elif pp[p].index(r) < pp[p].index(held[p]):
            free.append(held[p]); held[p] = r
        else:
            free.append(r)
    order = re.findall(rf"({NAME}) would like, from best to worst", b.question)
    taken, sd = set(), {}
    for p in order:
        if p in pp:
            c = next(x for x in pp[p] if x not in taken); sd[p] = c; taken.add(c)
    return {"first_choice": pp[a][0], "second_choice": pp[a][1], "last_choice": pp[a][-1], "receiver_proposing": held[a], "serial_dictatorship_text_order": sd.get(a),
            "receiver_ranking_ask_highest": argbest(rs, lambda r: -pr[r].index(a)),
            "best_mutual_rank_sum": argbest(rs, lambda r: -(pp[a].index(r) + pr[r].index(a)))}


def h_swap(b):
    st = b.structured
    hold = dict(st["hold"]); who = st["who"]

    def sim(skip_rot=False, rev_rot=False):
        s = dict(hold)
        for o in st["ops"]:
            if o[0] == "swap":
                s[o[1]], s[o[2]] = s[o[2]], s[o[1]]
            elif not skip_rot:
                a, c, d = o[1:]
                if rev_rot:
                    s[a], s[c], s[d] = s[c], s[d], s[a]
                else:
                    s[c], s[d], s[a] = s[a], s[c], s[d]
        return s[who]

    return {"initial_item": hold[who], "ignore_rotations": sim(skip_rot=True), "rotation_reversed": sim(rev_rot=True)}


def h_cpath(b):
    st = b.structured
    jobs = {p: (d, deps) for p, d, deps in st["jobs"]}
    fin = {}

    def f(p):
        if p not in fin:
            fin[p] = max([f(x) for x in jobs[p][1]], default=0) + jobs[p][0]
        return fin[p]

    ans = max(f(p) for p in jobs)
    durs = [d for d, _ in jobs.values()]
    one = max(jobs[p][0] + max([jobs[x][0] for x in jobs[p][1]], default=0) for p in jobs)
    waited = {x for _, (_, ds) in jobs.items() for x in ds}
    sinks = [p for p in jobs if p not in waited]

    def back(p):
        t = 0
        while True:
            t += jobs[p][0]
            if not jobs[p][1]:
                return t
            p = max(jobs[p][1], key=lambda x: jobs[x][0])

    return {"sum_durations": str(sum(durs)), "max_duration": str(max(durs)), "one_level_chain": str(one), "greedy_backward": str(max(back(p) for p in sinks)),
            "inclusive_day_reading": str(ans - 1)}


def h_overlap(b):
    st = b.structured
    ev = st["events"]; sp = dict(zip(ev, st["spans"]))
    x, y = st["x"], st["y"]

    def iv(s, off=0):
        return (s[1], s[2]) if s[0] == "range" else (s[1], s[1] + s[2] - 1 + off)

    a, c = iv(sp[x], 1), iv(sp[y], 1)
    yn = lambda v: "yes" if v else "no"
    a0, c0 = iv(sp[x]), iv(sp[y])
    return {"duration_end_off_by_one": yn(max(a[0], c[0]) <= min(a[1], c[1])), "starts_within_20": yn(abs(a0[0] - c0[0]) <= 20),
            "same_format": yn(sp[x][0] == sp[y][0]), "start_order": yn(a0[0] < c0[0])}


def h_weekday(b):
    st = b.structured
    days = st["days"]; anc, wd = st["anchor"]; links = st["links"]; ask = st["ask"]
    adj = defaultdict(list)
    for a, c, k in links:
        adj[a].append((c, k)); adj[c].append((a, k))
    val = {anc: days.index(wd)}; dq = deque([anc])
    while dq:
        u = dq.popleft()
        for v, k in adj[u]:
            if v not in val:
                val[v] = val[u] + k; dq.append(v)
    return {"anchor_weekday": wd, "ignore_before_after": days[val[ask] % 7]}


def h_accounts(b):
    st = b.structured
    start = st["start"]; ops = st["ops"]; ask = st["ask"]
    ppl = list(start)
    net = Counter(); bal_nohalf = dict(start); bal_noearn = dict(start)
    for o in ops:
        if o[0] == "pay":
            net[o[2]] += o[3]; net[o[1]] -= o[3]
            bal_nohalf[o[1]] -= o[3]; bal_nohalf[o[2]] += o[3]
            bal_noearn[o[1]] -= o[3]; bal_noearn[o[2]] += o[3]
        elif o[0] == "earn":
            net[o[1]] += o[2]; bal_nohalf[o[1]] += o[2]
        else:
            h = bal_noearn[o[1]] // 2; bal_noearn[o[1]] -= h; bal_noearn[o[2]] += h
    best = max if ask == "most" else min
    return {"net_flow_extreme": argbest(ppl, lambda p: net[p], best), "start_extreme": argbest(ppl, lambda p: start[p], best),
            "ignore_halves": argbest(ppl, lambda p: bal_nohalf[p], best), "ignore_earnings": argbest(ppl, lambda p: bal_noearn[p], best)}


def h_venn(b):
    st = b.structured
    tot = st["total"]; sz = sum(st["sizes"].values()); pr = sum(st["pairs"].values()); tr = sum(st["triples"].values()); qd = st["quad"] or 0
    return {"total_minus_sizes": str(tot - sz), "ignore_triples": str(tot - sz + pr), "sum_pairs": str(pr), "sum_pairs_minus_triple": str(pr - tr),
            "sizes_minus_pairs": str(sz - pr), "sizes_minus_2pairs": str(sz - 2 * pr + 3 * tr - 4 * qd), "pairs_minus_3triples": str(pr - 3 * tr + 6 * qd),
            "pairs_minus_2triples": str(pr - 2 * tr + 3 * qd), "total_minus_union_wrong_sign": str(tot - (sz - pr - tr))}


SPECIFIC = {
    "R1.activity_selection_r4": h_activity, "R1.topological_order_r4": h_topo, "R1.attribute_rule": h_attr, "R1.conditional_decision_tree_r4": h_dtree,
    "R1.conditional_threshold_rule_r4": h_threshold, "R1.boolean_lights_r4": h_boolean, "R1.categories_default_exceptions_r4": h_cde,
    "R1.categories_follow_r4": h_catfollow, "R1.compass_turns": h_compass, "R1.conditional_chain": h_condchain, "R1.containers_queue_line_r2": h_queue,
    "R1.containers_stack_piles_r4": h_stack, "R1.elimination_bracket_r4": h_bracket, "R1.elimination_josephus": h_josephus, "R1.equivalence_classes_r2": h_eqclass,
    "R1.equivalence_exchange_rates": h_exchange, "R1.event_timeline": h_event, "R1.graph_bipartite": h_bip, "R1.graph_shortest_route_r4": h_route,
    "R1.instant_runoff_r4": h_runoff, "R1.kinship_ancestor_r4": h_ancestor, "R1.kinship_cousins": h_cousins, "R1.kinship_descendants_r4": h_desc,
    "R1.knights_knaves": h_kk, "R1.minimax_tree_r4": h_minimax, "R1.mst_cost_r4": h_mst, "R1.nim_xor_r4": h_nim, "R1.one_culprit": h_culprit,
    "R1.order_compare_r4": h_ordercmp, "R1.order_extreme": h_extreme, "R1.order_tournament_wins": h_rr, "R1.pet_owners": h_pets,
    "R1.road_reachability": h_road, "R1.seating_row": h_seat, "R1.spatial_grid_walk_r2": h_grid, "R1.spatial_relative_directions_r4": h_reldir,
    "R1.stable_matching_r4": h_match, "R1.swap_tracking": h_swap, "R1.temporal_critical_path_r4": h_cpath, "R1.temporal_interval_overlap": h_overlap,
    "R1.temporal_weekday_shift": h_weekday, "R1.tracking_accounts": h_accounts, "R1.venn_counting_r4": h_venn,
}


def chance(b):
    return 0.0 if b.k is None else 1.0 / b.k


def credit(p, b):
    if p is None or p == []:
        return None
    ps = p if isinstance(p, list) else [p]
    return sum(1 for x in ps if x == b.answer) / len(ps)


def anti(p, b):
    if p is None or p == [] or b.k is None:
        return None
    ps = set(p if isinstance(p, list) else [p])
    o = opts(b)
    if o and len(o) == b.k:
        rest = [x for x in o if x not in ps]
        return (b.answer in rest) / len(rest) if rest else None
    rest_n = b.k - len(ps)
    return ((b.answer not in ps) / rest_n) if rest_n > 0 else None


def main():
    n = int(sys.argv[1]); base = int(sys.argv[2]); fit = int(sys.argv[3]); filt = sys.argv[4] if len(sys.argv) > 4 else ""
    L = gen.lineages()
    rows = []
    for lid in sorted(L):
        if filt and filt not in lid:
            continue
        for lv in range(7):
            fit_items = gen.items(L[lid], lv, 300, fit)
            mfk = Counter(b.answer for b in fit_items).most_common(1)[0][0]
            its = gen.items(L[lid], lv, n, base)
            acc = defaultdict(lambda: {"eff": [], "anti": [], "fired": 0, "hit": []})
            allp = [{"constant_mfk_fitted": mfk, **generic(b), **SPECIFIC[lid](b)} for b in its]
            names = sorted({h for p in allp for h in p})  # run-1 slip fixed: a heuristic absent from an item's dict now scores chance there (it does not fire)
            for b, preds0 in zip(its, allp):
                ch = chance(b)
                preds = {h: preds0.get(h) for h in names}
                for h, p in preds.items():
                    c = credit(p, b)
                    a = anti(p, b)
                    r = acc[h]
                    r["eff"].append(ch if c is None else c)
                    r["anti"].append(ch if a is None else a)
                    if c is not None:
                        r["fired"] += 1; r["hit"].append(c)
            chm = statistics.mean(chance(b) for b in its)
            for h, r in acc.items():
                rows.append({"lineage": lid, "level": lv, "heuristic": h, "n": len(its), "chance": round(chm, 4), "fired": r["fired"],
                             "acc_fired": round(statistics.mean(r["hit"]), 4) if r["hit"] else None,
                             "eff": round(statistics.mean(r["eff"]) - chm, 4), "anti": round(statistics.mean(r["anti"]) - chm, 4) if its[0].k else None})
    json.dump(rows, sys.stdout)


if __name__ == "__main__":
    main()
