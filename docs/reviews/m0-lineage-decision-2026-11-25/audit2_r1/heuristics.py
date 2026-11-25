# ruff: noqa
"""Auditor's own heuristic battery, two-sided. Re-implements (from their description, not by import) the heuristics the author
lists, plus >= 5 auditor heuristics per lineage. Uses the item's structured form `s` (equivalent information to the text) or
the text. Usage: heuristics.py ITEMSDIR MODE [ids]
Metrics per heuristic (closed answers): fires n; accuracy when it fires; chance when it fires (mean 1/k, or 1/len-adjusted for
list picks: a list pick of m options is credited 1/m if it contains the key); departure = acc - chance; z = departure / SE with
SE = sqrt(chance(1-chance)/n). Negative departure = the heuristic's pick is informative as an ELIMINATION.
Open answers: exact-match rate vs the per-level modal-answer rate."""
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.setrecursionlimit(10000)


def sents(q):
    return [x for x in re.split(r"(?<=[.?!])\s+", q) if x]


def opts_of(q):
    m = re.search(r"Choose from (.+?)\.$", q)
    if not m:
        return None
    parts = m.group(1).split(", ")
    return [*parts[:-1], *parts[-1].split(" and ")]


def body_of(q):
    ss = sents(q)
    qi = max(i for i, s in enumerate(ss) if "?" in s)
    return " ".join(ss[:qi])


def cnt(body, o):
    return len(re.findall(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body))


def argset(cands, key, best="max"):
    if not cands:
        return None
    v = {c: key(c) for c in cands}
    t = max(v.values()) if best == "max" else min(v.values())
    return [c for c in cands if v[c] == t]


def first_pos(body, o):
    m = re.search(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body)
    return m.start() if m else 10**9


def last_pos(body, o):
    ms = list(re.finditer(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body))
    return ms[-1].start() if ms else -1


def mention_h(r):
    q = r["q"]
    o = opts_of(q)
    b = body_of(q)
    if not o:
        return {}
    men = [x for x in o if cnt(b, x)]
    return {
        "A:most_mentioned": argset(o, lambda x: cnt(b, x)),
        "A:least_mentioned": argset(o, lambda x: cnt(b, x), "min"),
        "A:first_mentioned": argset(men, lambda x: first_pos(b, x), "min"),
        "M:last_mentioned": argset(men, lambda x: last_pos(b, x)),
        "M:alphabetical_first": [sorted(o)[0]],
    }


# ---------------- per-lineage heuristics ----------------
def h_kin_desc(r):
    s, q = r["s"], r["q"]
    par = s["parent"]
    cands = s["candidates"]
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)
    root = [p for p in s["people"] if p not in par]
    depth = {}

    def dep(p):
        return 0 if p not in par else 1 + dep(par[p])

    def desc(p):
        return sum(1 + desc(c) for c in kids[p])

    other = "descendants" if s["ask"] == "grandchildren" else "grandchildren"
    sc_other = {p: (sum(len(kids[c]) for c in kids[p]) if other == "grandchildren" else desc(p)) for p in cands}
    top_kid = argset(list(s["people"]), lambda p: len(kids[p]))
    out = mention_h(r)
    out.update({
        "A:most_children": argset(cands, lambda p: len(kids[p])),
        "M:child_of_root": [p for p in cands if par.get(p) in root] or None,
        "M:deepest_candidate": argset(cands, dep),
        "M:question_swap": argset(cands, lambda p: sc_other[p]) if max(sc_other.values()) > 0 else None,
        "M:parent_of_most_children_person": [par[x] for x in top_kid if x in par and par[x] in cands] or None,
        "M:root_child_with_most_children": argset([p for p in cands if par.get(p) in root], lambda p: len(kids[p])),
    })
    return out


def h_kin_anc(r):
    s, q = r["s"], r["q"]
    par = s["parent"]
    child = s["child"]
    b = body_of(q)
    root = [p for p in s["people"] if p not in par]
    two = par.get(par.get(child, ""), None)
    out = mention_h(r)
    out.update({
        "A:parentless": root,
        "M:childs_parent": [par[child]],
        "M:two_steps_regardless_of_term": [two] if two else None,
        "M:mentioned_twice_plus_not_parent_not_root": [p for p in s["people"] if cnt(b, p) >= 2 and p != par[child] and p not in root and p != child] or None,
        "M:has_parent_and_child": [p for p in s["people"] if p in par and p in par.values() and p != par[child]] or None,
    })
    return out


def h_bracket(r):
    s = r["s"]
    pl = s["players"]
    res = s["results"]
    w = Counter(a for a, _ in res)
    ask = s["ask"]
    order = sorted(pl, key=lambda p: -w.get(p, 0))
    out = {}
    out["A:most_wins_logic"] = [order[1]] if ask[0] == "runner_up" else ([order[0]] if order[0] != ask[1] else [order[1]])
    if ask[0] == "beaten_by":
        x = ask[1]
        i = pl.index(x)
        out["M:round1_neighbour"] = [pl[i ^ 1]]
        beaters = [a for a, b in res if b == x]
        out["M:first_listed_beater"] = beaters[:1] or None
        out["M:beater_with_most_wins"] = argset(beaters, lambda p: w.get(p, 0)) if beaters else None
        half = len(pl) // 2
        mine = pl[:half] if i < half else pl[half:]
        out["M:beater_in_own_half"] = [p for p in beaters if p in mine] or None
        out["M:first_listed_player"] = [pl[0]] if pl[0] != x else [pl[1]]
    else:
        top = order[0]
        half = len(pl) // 2
        other = pl[half:] if pl.index(top) < half else pl[:half]
        out["M:most_wins_other_half"] = argset(other, lambda p: w.get(p, 0))
        out["M:first_listed_player"] = [pl[0]]
        out["M:last_listed_player"] = [pl[-1]]
        out["M:fewest_wins"] = argset(pl, lambda p: w.get(p, 0), "min")
        out["M:alphabetical_first"] = [sorted(pl)[0]]
    return out


def h_threshold(r):
    s = r["s"]
    w = dict((p, x) for p, x in s["members"])
    v = s["votes"]
    d = s["margin"]
    Y = sum(w[p] for p in w if v[p] == "yes")
    N = sum(w[p] for p in w if v[p] == "no")
    y = sum(1 for p in w if v[p] == "yes")
    n = sum(1 for p in w if v[p] == "no")
    heavy = max(w.values())
    hv = [v[p] for p in w if w[p] == heavy and v[p] != "abstain"]
    yn = lambda b: "yes" if b else "no"
    return {
        "A:yes_count_majority": None if y == n else yn(y > n),
        "M:weighted_yes_ge_no_ignore_margin": yn(Y >= N),
        "M:weighted_yes_gt_no": yn(Y > N),
        "M:margin_le_zero": yn(d <= 0),
        "M:unweighted_counts_with_margin": yn(y - n >= d),
        "M:heaviest_vote": (yn(hv[0] == "yes") if len(set(hv)) == 1 else None) if hv else None,
        "M:yes_weight_ge_margin_ignore_no": yn(Y >= d),
        "M:yes_weight_ge_half_total": yn(2 * Y >= sum(w.values())),
    }


def h_stacks(r):
    s = r["s"]
    ask = s["ask"]
    st = {p: list(x) for p, x in s["initial"].items()}
    last_onto, first_onto, last_any = None, None, None
    src_of_last = None
    st2 = {p: list(x) for p, x in s["initial"].items()}
    last_onto_norev = None
    for op in s["ops"]:
        if op[0] == "move":
            b = st[op[1]].pop()
            st[op[2]].append(b)
            last_any = b
            if op[2] == ask:
                last_onto = b
                first_onto = first_onto or b
                src_of_last = op[1]
            if st2[op[1]]:
                b2 = st2[op[1]].pop()
                st2[op[2]].append(b2)
                if op[2] == ask:
                    last_onto_norev = b2
        else:
            st[op[1]].reverse()
    init = s["initial"]
    allblocks = [b for p in s["piles"] for b in init[p]]
    return {
        "A:last_block_moved_onto_asked": [last_onto] if last_onto else None,
        "A:initial_top": [init[ask][-1]] if init[ask] else None,
        "M:last_block_moved_anywhere": [last_any] if last_any else None,
        "M:initial_bottom_of_asked": [init[ask][0]] if init[ask] else None,
        "M:initial_top_of_source_of_last_onto": [init[src_of_last][-1]] if src_of_last and init[src_of_last] else None,
        "M:last_listed_block_initially": [allblocks[-1]],
        "M:first_block_moved_onto_asked": [first_onto] if first_onto else None,
        "M:simulate_ignoring_reversals": [st2[ask][-1]] if st2[ask] else None,
        "M:alphabetical_first": [sorted(allblocks)[0]],
    }


def _kahn(jobs, key):
    deps = {p: set(d) for p, d in jobs}
    done = []
    while len(done) < len(deps):
        av = [p for p in deps if p not in done and deps[p] <= set(done)]
        done.append(min(av, key=key))
    return done


def h_topo(r):
    s = r["s"]
    jobs = s["jobs"]
    j = s["day"]
    names = [p for p, _ in jobs]
    textpos = {p: i for i, p in enumerate(names)}
    deps = {p: set(d) for p, d in jobs}

    def depth(p):
        return 0 if not deps[p] else 1 + max(depth(x) for x in deps[p])

    rev = _kahn(jobs, key=lambda p: [-ord(c) for c in p])
    return {
        "A:jth_alphabetical": [sorted(names)[j - 1]],
        "M:jth_in_text_order": [names[j - 1]],
        "M:sort_by_prereq_count_then_name": [sorted(names, key=lambda p: (len(deps[p]), p))[j - 1]],
        "M:sort_by_depth_then_name": [sorted(names, key=lambda p: (depth(p), p))[j - 1]],
        "M:kahn_reverse_alphabetical": [rev[j - 1]],
        "M:kahn_text_order": [_kahn(jobs, key=lambda p: textpos[p])[j - 1]],
        "M:exactly_j_minus_1_prereqs": [p for p in names if len(deps[p]) == j - 1] or None,
    }


def _irv(cands, ballots, drop=None):
    alive = list(cands)
    elim = []
    while len(alive) > 1:
        t = {a: 0 for a in alive}
        for c, rk in ballots:
            t[next(x for x in rk if x in alive)] += c
        lo = min(t.values())
        out = sorted(a for a in alive if t[a] == lo)[0]
        elim.append(out)
        alive.remove(out)
    return alive[0], elim


def h_irv(r):
    s = r["s"]
    C = s["candidates"]
    B = s["ballots"]
    first = Counter()
    last = Counter()
    second = Counter()
    borda = Counter()
    for c, rk in B:
        first[rk[0]] += c
        last[rk[-1]] += c
        if len(rk) > 1:
            second[rk[1]] += c
        for i, x in enumerate(rk):
            borda[x] += c * (len(rk) - 1 - i)
    def beats(a, b):
        return sum(c for c, rk in B if rk.index(a) < rk.index(b)) > sum(c for c, rk in B if rk.index(b) < rk.index(a))
    cond = [a for a in C if all(beats(a, b) for b in C if b != a)]
    top2 = sorted(C, key=lambda x: -first[x])[:2]
    t2 = top2[0] if beats(top2[0], top2[1]) else top2[1]
    _, elim = _irv(C, B)
    return {
        "A:plurality_winner": argset(C, lambda x: first[x]),
        "M:borda_winner": argset(C, lambda x: borda[x]),
        "M:condorcet_winner": cond or None,
        "M:fewest_last_places": argset(C, lambda x: last[x], "min"),
        "M:first_eliminated": [elim[0]],
        "M:most_second_places": argset(C, lambda x: second[x]),
        "M:top_two_runoff": [t2],
        "M:alphabetical_first": [sorted(C)[0]],
    }


def _gs(props, recv, pp, pr):
    nxt = {p: 0 for p in props}
    held = {}
    free = list(props)
    while free:
        p = free.pop(0)
        x = pp[p][nxt[p]]
        nxt[p] += 1
        if x not in held:
            held[x] = p
        elif pr[x].index(p) < pr[x].index(held[x]):
            free.append(held[x])
            held[x] = p
        else:
            free.append(p)
    return {p: x for x, p in held.items()}


def h_sm(r):
    s, q = r["s"], r["q"]
    ps, rs, pp, pr, ask = s["proposers"], s["receivers"], s["prefs_p"], s["prefs_r"], s["ask"]
    ropt = _gs(rs, ps, pr, pp)  # receivers propose
    rpartner = [x for x, p in ropt.items() if p == ask]
    b = body_of(q)
    men = [x for x in rs if cnt(b, x)]
    taken, sd = set(), {}
    for p in ps:
        c = next(x for x in pp[p] if x not in taken)
        sd[p] = c
        taken.add(c)
    return {
        "A:first_choice": [pp[ask][0]],
        "A:first_mentioned": argset(men, lambda x: first_pos(b, x), "min"),
        "M:receiver_optimal_partner": rpartner,
        "M:receivers_ranking_ask_first": [x for x in rs if pr[x][0] == ask] or None,
        "M:asks_last_choice": [pp[ask][-1]],
        "M:asks_second_choice": [pp[ask][1]],
        "M:receiver_ranking_ask_highest": argset(rs, lambda x: pr[x].index(ask), "min"),
        "M:serial_dictatorship_text_order": [sd[ask]],
    }


def h_defaults(r):
    s = r["s"]
    ch, rules, verb = s["chain"], s["rules"], s["verb"]
    yn = lambda b: "yes" if b else "no"
    mine = [x for x in rules if x[1] == verb]
    other = [x for x in rules if x[1] != verb]
    srt = sorted(mine, key=lambda x: ch.index(x[0]))
    sg = [x[2] for x in mine]
    out = {
        "A:all_rules_agree": yn(sg[0]) if len(set(sg)) == 1 else None,
        "A:member_group_rule": next((yn(x[2]) for x in mine if x[0] == ch[0]), None),
        "A:majority_sign": None if 2 * sum(sg) == len(sg) else yn(2 * sum(sg) > len(sg)),
        "A:last_listed": yn(sg[-1]),
        "A:least_specific_rule": yn(srt[-1][2]),
        "M:rule_on_immediate_supergroup_chain1": next((yn(x[2]) for x in mine if x[0] == ch[1]), None),
        "M:first_listed_rule": yn(sg[0]),
        "M:second_most_specific_rule": yn(srt[1][2]) if len(srt) > 1 else None,
        "M:minority_sign": None if 2 * sum(sg) == len(sg) else yn(2 * sum(sg) < len(sg)),
        "M:most_specific_rule_other_verb": yn(sorted(other, key=lambda x: ch.index(x[0]))[0][2]) if other else None,
        "M:always_yes": "yes",
        "M:odd_count_sign": yn(sum(sg) % 2 == 1),
    }
    return out


def h_equiv(r):
    s, q = r["s"], r["q"]
    x, y = s["x"], s["y"]
    same, diff = s["same"], s["different"]
    b = body_of(q)
    nb = defaultdict(set)
    for a, c in same:
        nb[a].add(c)
        nb[c].add(a)
    in_diff = {e for p in diff for e in p}
    in_same = {e for p in same for e in p}
    return {
        "M:either_in_a_different_sentence_no_else_yes": "no" if (x in in_diff or y in in_diff) else "yes",
        "M:common_same_neighbour_yes_else_cbd": "yes" if nb[x] & nb[y] else "cannot be determined",
        "M:either_mentioned_once_cbd": "cannot be determined" if min(cnt(b, x), cnt(b, y)) == 1 else None,
        "M:both_only_in_same_sentences_yes": "yes" if (x not in in_diff and y not in in_diff and x in in_same and y in in_same) else None,
        "M:always_cbd": "cannot be determined",
        "M:mentions_sum_ge4_yes": "yes" if cnt(b, x) + cnt(b, y) >= 4 else None,
        "M:different_partner_shared_cbd": "cannot be determined" if any({x, e} in [set(p) for p in diff] for e in [y]) else None,
    }


def _queue(line, ops, skip=()):
    cur = list(line)
    for o in ops:
        k = o[0]
        if k in skip:
            continue
        if k == "join":
            cur.append(o[1])
        elif k == "cut":
            cur.insert(0, o[1])
        elif k == "serve":
            if cur:
                cur.pop(0)
        elif k == "leave":
            if o[1] in cur:
                cur.remove(o[1])
        else:
            if cur:
                cur.append(cur.pop(0))
    return cur


def h_queue(r):
    s = r["s"]
    line, ops = s["line"], s["ask"] and s["ops"]
    j = s["ask"][1]
    pick = lambda cur: [cur[j - 1]] if len(cur) >= j else None
    cuts = [o[1] for o in ops if o[0] == "cut"]
    joins = [o[1] for o in ops if o[0] == "join"]
    named = [o[1] for o in ops if len(o) > 1]
    return {
        "A:initial_line_position": [line[j - 1]] if len(line) >= j else None,
        "M:last_cut_if_j1": [cuts[-1]] if (j == 1 and cuts) else None,
        "M:simulate_only_cut_and_join": pick(_queue(line, ops, ("serve", "leave", "front_to_back"))),
        "M:simulate_ignoring_rotations": pick(_queue(line, ops, ("front_to_back",))),
        "M:simulate_ignoring_leaves": pick(_queue(line, ops, ("leave",))),
        "M:last_named_in_ops": [named[-1]] if named else None,
        "M:first_joiner": [joins[0]] if joins else None,
    }


def h_lights(r):
    s = r["s"]
    a = s["ask"]
    init = s["initial"][a - 1]
    pr = sum(1 for c in s["presses"] if a in s["switches"][c])
    wired = sum(1 for c in s["switches"] if a in s["switches"][c])
    yn = lambda b: "yes" if b else "no"
    return {
        "A:initial_state": yn(init),
        "M:press_parity_ignoring_initial": yn(pr % 2 == 1),
        "M:in_last_pressed_switch": yn(a in s["switches"][s["presses"][-1]]),
        "M:initial_flipped": yn(not init),
        "M:wired_switch_count_odd": yn(wired % 2 == 1),
        "M:majority_initially_on": yn(2 * sum(s["initial"]) > len(s["initial"])),
        "M:always_yes": "yes",
    }


def _adj(roads):
    g = defaultdict(list)
    for a, b, w in roads:
        g[a].append((b, w))
        g[b].append((a, w))
    return g


def h_short(r):
    s = r["s"]
    g = _adj(s["roads"])
    S, T = s["start"], s["end"]
    direct = [w for b, w in g[S] if b == T]
    two = [w1 + w2 for m, w1 in g[S] for b, w2 in g[m] if b == T]
    le2 = min(direct + two) if (direct + two) else None
    # greedy nearest neighbour walk
    cur, seen, tot = S, {S}, 0
    for _ in range(20):
        if cur == T:
            break
        nx = [(w, b) for b, w in g[cur] if b not in seen]
        if not nx:
            tot = None
            break
        w, b = min(nx)
        tot += w
        seen.add(b)
        cur = b
    greedy = tot if cur == T else None
    # fewest hops, then min length among them
    from collections import deque
    hop = {S: 0}
    dq = deque([S])
    while dq:
        u = dq.popleft()
        for b, _ in g[u]:
            if b not in hop:
                hop[b] = hop[u] + 1
                dq.append(b)
    H = hop.get(T)
    best = {S: 0}
    layer = {S}
    for h in range(H or 0):
        nl = {}
        for u in layer:
            for b, w in g[u]:
                if hop.get(b) == h + 1:
                    nl[b] = min(nl.get(b, 10**9), best[u] + w)
        best.update(nl)
        layer = set(nl)
    return {
        "A:direct_road_length": str(direct[0]) if direct else None,
        "M:best_within_two_roads": str(le2) if le2 is not None else None,
        "M:greedy_nearest_walk": str(greedy) if greedy is not None else None,
        "M:fewest_roads_route": str(best.get(T)) if H else None,
        "M:cheapest_at_start_plus_cheapest_at_end": str(min(w for _, w in g[S]) + min(w for _, w in g[T])),
    }


def h_grid(r):
    s = r["s"]
    g = s["grid"]
    R, C = len(g), len(g[0])
    st = tuple(s["start"])
    mv = s["moves"]
    D = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}

    def walk(moves, walls=True, flip=False, start=st):
        p = start
        for m in moves:
            di, dj = D[m]
            if flip:
                dj = -dj
            i, j = p[0] + di, p[1] + dj
            if 0 <= i < R and 0 <= j < C and (g[i][j] or not walls):
                p = (i, j)
        return p

    def name(p):
        return [g[p[0]][p[1]]] if g[p[0]][p[1]] else None

    ni = sum(D[m][0] for m in mv)
    nj = sum(D[m][1] for m in mv)
    net = (min(max(st[0] + ni, 0), R - 1), min(max(st[1] + nj, 0), C - 1))
    return {
        "A:start_cell": name(st),
        "M:ignore_walls": name(walk(mv, walls=False)),
        "M:columns_reversed": name(walk(mv, flip=True)),
        "M:net_displacement_clipped": name(net),
        "M:last_move_only": name(walk(mv[-1:])),
        "M:first_half_of_moves": name(walk(mv[: len(mv) // 2])),
    }


def h_follow(r):
    s, q = r["s"], r["q"]
    cats = s["cats"]
    kind, x, y = s["kind"], cats[s["x"]], cats[s["y"]]
    nos = [(cats[a], cats[b]) for a, b in s["none"]]
    alls = [(cats[a], cats[b]) for a, b in s["all"]]
    nomention = any(x in p or y in p for p in nos)
    subj = any(a == x for a, _ in alls)
    together = any({x, y} <= set(p) for p in nos + alls)
    return {
        "M:always_cbd": "cannot be determined",
        "M:kind_default_all_none_yes_some_no": "no" if kind == "some" else "yes",
        "M:no_sentence_mentions_x_or_y": (("no" if kind == "some" else "yes") if nomention else "cannot be determined") if kind != "all" else None,
        "M:all_x_subject_yes": ("yes" if subj else "cannot be determined") if kind == "all" else None,
        "M:x_and_y_share_a_sentence_yes": "yes" if together else None,
    }


def h_activity(r):
    ms = r["s"]["meetings"]
    def greedy(key, strict=False):
        c, last = 0, -1
        for _, a, b in sorted(ms, key=key):
            if (a > last) if strict else (a >= last):
                c += 1
                last = b
        return c
    # note: greedy by duration without a proper overlap check against ALL chosen; implement properly
    chosen = []
    for _, a, b in sorted(ms, key=lambda m: (m[2] - m[1], m[1])):
        if all(b <= c or a >= d for c, d in chosen):
            chosen.append((a, b))
    lonely = sum(1 for i, (_, a, b) in enumerate(ms) if all(b <= c or a >= d for j, (_, c, d) in enumerate(ms) if j != i))
    return {
        "A:greedy_by_start": str(greedy(lambda m: (m[1], m[2]))),
        "M:greedy_by_shortest_duration": str(len(chosen)),
        "M:meetings_overlapping_none": str(lonely),
        "M:half_the_meetings": str(len(ms) // 2),
        "M:earliest_end_but_touching_overlaps": str(greedy(lambda m: (m[2], m[1]), strict=True)),
    }


def h_mst(r):
    s = r["s"]
    roads = s["roads"]
    towns = s["towns"]
    cheapest = {}
    for i, (a, b, w) in enumerate(roads):
        for t in (a, b):
            if t not in cheapest or w < roads[cheapest[t]][2]:
                cheapest[t] = i
    g = _adj(roads)
    # shortest path tree from the first-mentioned town
    import heapq
    src = roads[0][0]
    dist = {src: 0}
    par = {}
    h = [(0, src)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]:
            continue
        for b, w in g[u]:
            if d + w < dist.get(b, 10**9):
                dist[b] = d + w
                par[b] = w
                heapq.heappush(h, (d + w, b))
    seen, tot = set(), 0
    for a, b, w in roads:
        if a not in seen or b not in seen:
            tot += w
            seen |= {a, b}
    return {
        "A:smallest_n_minus_1_roads": str(sum(sorted(w for *_, w in roads)[: len(towns) - 1])),
        "M:sum_of_each_towns_cheapest_road": str(sum(roads[i][2] for i in set(cheapest.values()))),
        "M:shortest_path_tree_from_first_town": str(sum(par.values())),
        "M:all_roads_minus_longest": str(sum(w for *_, w in roads) - max(w for *_, w in roads)),
        "M:text_order_new_town_greedy": str(tot),
    }


def h_nim(r):
    p = r["s"]["piles"]
    fs = lambda b: "first" if b else "second"
    return {
        "A:odd_total_means_first": fs(sum(p) % 2),
        "M:odd_number_of_piles_first": fs(len(p) % 2),
        "M:largest_exceeds_rest_first": fs(max(p) > sum(p) - max(p)),
        "M:two_equal_piles_second": fs(len(set(p)) == len(p)),
        "M:no_odd_pile_second": fs(any(x % 2 for x in p)),
        "M:largest_pile_odd_first": fs(max(p) % 2),
        "M:smallest_pile_even_second": fs(min(p) % 2),
    }


def _leaves(t):
    return [t] if isinstance(t, int) else [x for c in t for x in _leaves(c)]


def h_minimax(r):
    t = r["s"]["tree"]
    L = _leaves(t)

    def val(t, mx):
        if isinstance(t, int):
            return t
        v = [val(c, not mx) for c in t]
        return max(v) if mx else min(v)

    srt = sorted(L)
    return {
        "A:smallest_leaf": str(min(L)),
        "M:largest_leaf": str(max(L)),
        "M:first_leaf": str(L[0]),
        "M:median_leaf_low": str(srt[(len(srt) - 1) // 2]),
        "M:min_player_first": str(val(t, False)),
        "M:max_everywhere": str(max(L)),
        "M:min_of_left_subtree_leaves": str(min(_leaves(t[0]))),
    }


def h_venn(r):
    s = r["s"]
    T = s["total"]
    S = sum(s["sizes"].values())
    P = sum(s["pairs"].values())
    t = s["triple"] or 0
    return {
        "M:total_minus_sum_of_sizes": str(T - S),
        "M:forget_triple": str(T - S + P),
        "M:total_minus_largest_group": str(T - max(s["sizes"].values())),
        "M:triple_value": str(t) if s["triple"] is not None else None,
        "PROCEDURE_CHECK:inclusion_exclusion": str(T - S + P - t),  # run1 mislabelled this "M:sign_error_on_triple"; it is the correct rule
        "M:sign_error_triple_added": str(T - S + P + t),
        "M:total_minus_sum_of_pairs": str(T - P),
    }


# task-5 lineages (not repaired)
def h_cdt(r):
    s, q = r["s"], r["q"]
    tree, facts = s["tree"], s["facts"]
    def path(n, always):
        while n[0] == "if":
            n = n[2] if always else n[3]
        return n[1]
    acts_in_order = re.findall(r"\(([a-z ]+)\)", q.split("Right now")[0])
    out = mention_h(r)
    out.update({
        "M:always_then_branch": [path(tree, True)],
        "M:always_otherwise_branch": [path(tree, False)],
        "M:first_action_in_rule": acts_in_order[:1] or None,
        "M:last_action_in_rule": acts_in_order[-1:] or None,
    })
    return out


def h_accounts(r):
    s = r["s"]
    ask = s["ask"]
    st = s["start"]
    ops = s["ops"]
    earn = Counter(o[1] for o in ops if o[0] == "earn")
    recv = Counter(o[2] for o in ops if o[0] in ("pay", "half"))
    give = Counter(o[1] for o in ops if o[0] in ("pay", "half"))
    ps = list(st)
    best = "max" if ask == "most" else "min"
    out = mention_h(r)
    out.update({
        "A:richest_or_poorest_at_start": argset(ps, lambda p: st[p], best),
        "M:most_or_fewest_earn_events": argset(ps, lambda p: earn[p], best),
        "M:received_minus_given_events": argset(ps, lambda p: recv[p] + earn[p] - give[p], best),
        "M:last_payee": [ops[-1][2]] if ops[-1][0] in ("pay", "half") else None,
    })
    return out


def h_reldir(r):
    s = r["s"]
    anc = s["anchor"]
    facts = s["facts"]
    nbr = {f[0] for f in facts if f[3] == anc} | {f[3] for f in facts if f[0] == anc}
    top = max(facts, key=lambda f: f[2])
    out = mention_h(r)
    out.update({
        "A:endpoint_of_largest_offset": [x for x in (top[0], top[3]) if x != anc],
        "M:direct_neighbour_of_anchor": sorted(nbr) or None,
        "M:not_neighbour_of_anchor": sorted(set(s["places"]) - nbr - {anc}) or None,
        "M:sum_of_offsets_mentioning_place": argset([p for p in s["places"] if p != anc], lambda p: sum(f[2] for f in facts if p in (f[0], f[3]))),
    })
    return out


def h_ocompare(r):
    s, q = r["s"], r["q"]
    x, y = s["x"], s["y"]
    facts = [tuple(f) for f in s["taller"]]
    b = body_of(q)
    return {
        "A:asked_pair_stated_verbatim": "yes" if (x, y) in facts else None,
        "M:reverse_pair_stated": "no" if (y, x) in facts else None,
        "M:x_never_taller_than_anyone_no": "no" if not any(f[0] == x for f in facts) else None,
        "M:y_never_shorter_than_anyone_cbd": "cannot be determined" if not any(f[1] == y for f in facts) else None,
        "M:x_mentioned_more_than_y_yes": "yes" if cnt(b, x) > cnt(b, y) else None,
        "M:always_cbd": "cannot be determined",
    }


def h_crit(r):
    s = r["s"]
    jobs = s["jobs"]
    names = [j[0] for j in jobs]
    deps = {j[0]: j[2] for j in jobs}
    dur = {j[0]: j[1] for j in jobs}
    dependents = Counter(x for j in jobs for x in j[2])
    out = mention_h(r)
    out.update({
        "A:longest_job": argset(names, lambda p: dur[p]),
        "M:most_prerequisites": argset(names, lambda p: len(deps[p])),
        "M:no_dependents_longest": argset([p for p in names if not dependents[p]], lambda p: dur[p]),
        "M:deepest_job": argset(names, lambda p: (lambda f: f(f, p))(lambda f, x: 0 if not deps[x] else 1 + max(f(f, d) for d in deps[x]))),
    })
    return out


H = {
    "kinship_descendants_r3": h_kin_desc, "kinship_ancestor_r3": h_kin_anc, "elimination_bracket_r3": h_bracket,
    "conditional_threshold_rule_r3": h_threshold, "containers_stack_piles_r3": h_stacks, "topological_order_r2": h_topo,
    "instant_runoff_r2": h_irv, "stable_matching_r2": h_sm, "categories_default_exceptions_r3": h_defaults,
    "equivalence_classes_r2": h_equiv, "containers_queue_line_r2": h_queue, "boolean_lights_r2": h_lights,
    "graph_shortest_route_r2": h_short, "spatial_grid_walk_r2": h_grid, "categories_follow_r2": h_follow,
    "activity_selection": h_activity, "mst_cost": h_mst, "nim_xor": h_nim, "minimax_tree": h_minimax, "venn_counting": h_venn,
    "conditional_decision_tree": h_cdt, "tracking_accounts": h_accounts, "spatial_relative_directions": h_reldir,
    "order_compare": h_ocompare, "temporal_critical_path": h_crit,
}


def k_of(r):
    if r["k"]:
        return r["k"]
    return None


def evaluate(rows, fn):
    res = defaultdict(lambda: {"n": 0, "acc": 0.0, "ch": 0.0, "lv": defaultdict(lambda: [0, 0.0, 0.0])})
    open_ans = all(r["k"] is None for r in rows)
    mode_by_level = {}
    if open_ans:
        for lv in range(7):
            c = Counter(r["a"] for r in rows if r["level"] == lv)
            mode_by_level[lv] = c.most_common(1)[0][1] / sum(c.values()) if c else 0
    for r in rows:
        hs = fn(r)
        for name, p in hs.items():
            if p is None or p == []:
                continue
            if isinstance(p, str):
                p = [p]
            p = list(dict.fromkeys(p))
            a = r["a"].lower()
            cr = (1.0 / len(p)) if a in [x.lower() for x in p] else 0.0
            if open_ans:
                ch = mode_by_level[r["level"]]
            else:
                k = r["k"]
                ch = 1.0 / k  # a list of m picks credited 1/m if it hits: expected credit of a random m-pick is m/k * 1/m = 1/k
            e = res[name]
            e["n"] += 1
            e["acc"] += cr
            e["ch"] += ch
            e["lv"][r["level"]][0] += 1
            e["lv"][r["level"]][1] += cr
            e["lv"][r["level"]][2] += ch
    out = []
    for name, e in res.items():
        n = e["n"]
        acc, ch = e["acc"] / n, e["ch"] / n
        se = math.sqrt(max(ch * (1 - ch), 1e-9) / n)
        lv = {l: round(v[1] / v[0] - v[2] / v[0], 3) for l, v in sorted(e["lv"].items()) if v[0] >= 50}
        out.append((name, n, acc, ch, acc - ch, (acc - ch) / se, lv))
    out.sort(key=lambda x: -abs(x[5]))
    return out, open_ans


if __name__ == "__main__":
    d, mode = sys.argv[1], sys.argv[2]
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    for lid, fn in H.items():
        if only and lid not in only:
            continue
        path = os.path.join(d, f"{lid}.{mode}.jsonl.gz")
        if not os.path.exists(path):
            continue
        rows = [json.loads(x) for x in gzip.open(path, "rt")]
        res, open_ans = evaluate(rows, fn)
        keyc = Counter(r["a"] for r in rows)
        print(f"\n### {lid} [{mode}] n={len(rows)} {'OPEN (baseline = per-level modal-answer rate)' if open_ans else 'closed'}; top keys {keyc.most_common(4)}")
        print("  heuristic | fires | acc | chance/baseline | departure | z | departure per level (>=50 fired)")
        for name, n, acc, ch, dep, z, lv in res:
            flag = " <==" if abs(z) >= 4 and abs(dep) >= 0.05 else ""
            print(f"  {name} | {n} | {acc:.3f} | {ch:.3f} | {dep:+.3f} | {z:+.1f} | {lv}{flag}")
