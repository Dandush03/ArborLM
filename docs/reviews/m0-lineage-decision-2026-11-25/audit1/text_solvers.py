# ruff: noqa
# ruff: noqa
"""Auditor's independent solvers for the 20 pilot R1 lineages.

Each solver parses the rendered QUESTION TEXT only (never `structured`, never
the generator modules, never `answer`), so a pass checks both the key and the
wording. Where a brute-force method is cheap it is used instead of the
generator's algorithm (bipartite: 2^n assignments; shortest route: all simple
paths). Each solver also returns a uniqueness flag where uniqueness matters.

Usage: python text_solvers.py <fixtures dir>
"""
import itertools
import json
import os
import re
import sys
from fractions import Fraction


def split_and(s):
    s = s.strip()
    if " and " not in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    head, last = s.rsplit(" and ", 1)
    parts = [x.strip() for x in head.split(",")] if head else []
    return [p for p in parts if p] + [last.strip()]


def sentences(q):
    # split on '. ' boundaries not inside parentheses
    out, depth, cur = [], 0, ""
    for i, ch in enumerate(q):
        cur += ch
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch in ".?" and depth == 0 and (i + 1 == len(q) or q[i + 1] == " "):
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


# ---------------- 1 boolean_lights
def s_boolean_lights(q):
    n = int(re.search(r"There are (\d+) lamps", q).group(1))
    state = [0] * (n + 1)
    m = re.search(r"At the start, lamps? ([\d, and]+?) (?:is|are) on", q)
    if m:
        for x in split_and(m.group(1)):
            state[int(x)] = 1
    else:
        assert "all lamps are off" in q
    wiring = {}
    for c, lst in re.findall(r"The (\w+) switch toggles lamps? ([\d, and]+?) \(", q):
        wiring[c] = [int(x) for x in split_and(lst)]
    presses = [x.strip() for x in re.search(r"pressed in this order: ([a-z, ]+)\.", q).group(1).split(",")]
    for p in presses:
        for l in wiring[p]:
            state[l] ^= 1
    k = int(re.search(r"Is lamp (\d+) on at the end", q).group(1))
    return ("yes" if state[k] else "no"), True


# ---------------- 2 categories_default_exceptions
def s_categories_default_exceptions(q):
    up = dict(re.findall(r"Every (\w+) is a (\w+)\.", q))
    rules = {}
    for g, cc, v in re.findall(r"A (\w+) (can|cannot) (\w+)\.", q):
        assert (g, v) not in rules
        rules[(g, v)] = cc == "can"
    m = re.search(r"(\w+) is a (\w+)\. Can \1 (\w+)\?", q)
    g, v = m.group(2), m.group(3)
    while True:
        if (g, v) in rules:
            return ("yes" if rules[(g, v)] else "no"), True
        if g not in up:
            return None, False
        g = up[g]


# ---------------- 3 conditional_decision_tree
def s_conditional_decision_tree(q):
    rule = re.search(r"Your rule is: (.*)\. Right now, ", q).group(1)
    facts_s = re.search(r"Right now, (.*)\. What do you do\?", q).group(1)
    facts = {}
    for tf, cond in re.findall(r"it is (true|false) that ([^;]+)", facts_s):
        facts[cond.strip()] = tf == "true"

    def parse(s):
        s = s.strip()
        if not s.startswith("if "):
            return ("do", s)
        cm = re.match(r"if (.+?), then \(", s)
        cond = cm.group(1)
        i = cm.end()
        depth, j = 1, i
        while depth:
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
            j += 1
        a = s[i:j - 1]
        rest = s[j:]
        assert rest.startswith(", otherwise ("), rest[:30]
        b = rest[len(", otherwise ("):-1]
        return ("if", cond, parse(a), parse(b))

    node = parse(rule)
    while node[0] == "if":
        node = node[2] if facts[node[1]] else node[3]
    return node[1], True


# ---------------- 4 conditional_threshold_rule
def s_conditional_threshold_rule(q):
    w = {p: int(x) for p, x in re.findall(r"(\w+) has weight (\d+)", q)}
    need = int(re.search(r"is at least (\d+)", q).group(1))
    vm = re.search(r"the veto holders are (.+?)\. The votes", q)
    vetoes = split_and(vm.group(1)) if vm else []
    votes = dict(re.findall(r"(\w+) (yes|no)(?=[,.])", q.split("The votes: ")[1].split(". Does the motion pass")[0] + "."))  # attempt-2 fix: attempt 1 also matched "or no." in the answer instruction
    assert set(votes) == set(w)
    ok = sum(w[p] for p in w if votes[p] == "yes") >= need and all(votes[v] == "yes" for v in vetoes)
    return ("yes" if ok else "no"), True


# ---------------- 5 containers_queue_line
def s_containers_queue_line(q):
    line = split_and(re.search(r"A line, from front to back, is: (.+?)\. ", q).group(1))
    body = q.split(". ", 1)[1]
    for s in sentences(body):
        if m := re.match(r"(\w+) joins at the back\.", s):
            line.append(m.group(1))
        elif m := re.match(r"(\w+) is let in at the very front\.", s):
            line.insert(0, m.group(1))
        elif s == "The person at the front is served and leaves.":
            line.pop(0)
        elif m := re.match(r"(\w+) gets tired and leaves\.", s):
            line.remove(m.group(1))
        elif s.startswith("Who is at the"):
            ask = re.match(r"Who is at the (front|back)", s).group(1)
            return (line[0] if ask == "front" else line[-1]), True
    raise ValueError


# ---------------- 6 containers_stack_piles
def s_containers_stack_piles(q):
    piles = {}
    for name, content in re.findall(r"The (\w+) pile holds, from bottom to top: (.+?)\.(?= )", q):
        piles[name] = [] if content == "nothing" else split_and(content)
    for s in sentences(q):
        if m := re.match(r"Move the top block of the (\w+) pile onto the (\w+) pile\.", s):
            piles[m.group(2)].append(piles[m.group(1)].pop())
        elif m := re.match(r"Turn the (\w+) pile upside down\.", s):
            piles[m.group(1)].reverse()
    ask = re.search(r"Which block is on top of the (\w+) pile at the end", q).group(1)
    return piles[ask][-1], True


# ---------------- 7 elimination_bracket
def s_elimination_bracket(q):
    pl = [(n, int(r)) for n, r in re.findall(r"(\w+) \(rating (\d+)\)", q)]
    rating = dict(pl)
    rnd = [n for n, _ in pl]
    knocked = {}
    final_loser = None
    while len(rnd) > 1:
        nxt = []
        for i in range(0, len(rnd), 2):
            a, b = rnd[i], rnd[i + 1]
            assert rating[a] != rating[b]
            win, lose = (a, b) if rating[a] > rating[b] else (b, a)
            knocked[lose] = win
            nxt.append(win)
            if len(rnd) == 2:
                final_loser = lose
        rnd = nxt
    if q.endswith("Who loses the final?"):
        return final_loser, True
    who = re.search(r"Who knocks (\w+) out\?", q).group(1)
    return knocked[who], True


# ---------------- 8 elimination_josephus
def s_elimination_josephus(q):
    people = split_and(re.match(r"(.+?) stand in a circle", q).group(1))
    k = int(re.search(r"Every time the count reaches (\d+)", q).group(1))
    circle = list(people)
    out = []
    # simulate literally: count one by one
    idx = 0  # index of person who says "1"
    while circle:
        cnt = 1
        j = idx
        while cnt < k:
            j = (j + 1) % len(circle)
            cnt += 1
        out.append(circle.pop(j))
        if circle:
            idx = j % len(circle)
    if "last person left" in q:
        return out[-1], True
    j = int(re.search(r"Who is number (\d+) to leave", q).group(1))
    return out[j - 1], True


# ---------------- 9 equivalence_classes
def s_equivalence_classes(q):
    same = re.findall(r"(\w+) is the same thing as (\w+)\.", q.split(" Is ")[0] + " ")
    diff = re.findall(r"(\w+) is a different thing from (\w+)\.", q)
    x, y = re.search(r"Is (\w+) the same thing as (\w+)\?", q).groups()
    ents = sorted({a for p in same + diff for a in p} | {x, y})
    # brute-force over set partitions is too large; use model enumeration over class labels for <= 12 entities
    idx = {e: i for i, e in enumerate(ents)}
    n = len(ents)
    seen = set()
    # labels: restricted growth strings (all set partitions) -- fine for n <= 11
    def rgs(i, cur, mx):
        if i == n:
            yield cur
            return
        for v in range(mx + 2):
            cur.append(v)
            yield from rgs(i + 1, cur, max(mx, v))
            cur.pop()
    if n > 11:
        return None, False
    for lab in rgs(0, [], -1):
        if all(lab[idx[a]] == lab[idx[b]] for a, b in same) and all(lab[idx[a]] != lab[idx[b]] for a, b in diff):
            seen.add(lab[idx[x]] == lab[idx[y]])
            if len(seen) == 2:
                break
    if not seen:
        return None, False
    if len(seen) == 2:
        return "cannot be determined", True
    return ("yes" if True in seen else "no"), True


# ---------------- 10 equivalence_exchange_rates
def s_equivalence_exchange_rates(q):
    rel = re.findall(r"(\d+) units of ([\w-]+) are worth the same as (\d+) units of ([\w-]+)\.", q)
    items = split_and(re.search(r"Which of (.+?) is worth the most per single unit", q).group(1))
    val = {items[0]: Fraction(1)}
    changed = True
    while changed:
        changed = False
        for p, a, qq, b in rel:
            p, qq = int(p), int(qq)
            # p * v(a) = qq * v(b)
            if a in val and b not in val:
                val[b] = Fraction(p) * val[a] / qq
                changed = True
            elif b in val and a not in val:
                val[a] = Fraction(qq) * val[b] / p
                changed = True
            elif a in val and b in val:
                assert p * val[a] == qq * val[b]
    assert set(val) == set(items)
    top = max(val.values())
    best = [i for i in items if val[i] == top]
    return best[0], len(best) == 1


# ---------------- 11 graph_shortest_route
def s_graph_shortest_route(q):
    roads = [(a, b, int(w)) for a, b, w in re.findall(r"between (\w+) and (\w+) of length (\d+)", q)]
    s, t = re.search(r"You drive from (\w+) to (\w+) along", q).groups()
    adj = {}
    for a, b, w in roads:
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))
    best = None
    firsts = set()
    def dfs(u, seen, d, first):
        nonlocal best, firsts
        if best is not None and d > best:
            return
        if u == t:
            if best is None or d < best:
                best, firsts = d, {first}
            elif d == best:
                firsts.add(first)
            return
        for v, w in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                dfs(v, seen, d + w, first if first else v)
                seen.discard(v)
    dfs(s, {s}, 0, None)
    return (sorted(firsts)[0] if firsts else None), len(firsts) == 1


# ---------------- 12 graph_bipartite
def s_graph_bipartite(q):
    people = split_and(re.match(r"(.+?) must be split into two teams", q).group(1))
    riv = re.findall(r"(\w+) and (\w+) are rivals\.", q)
    idx = {p: i for i, p in enumerate(people)}
    n = len(people)
    for mask in range(1 << (n - 1)):
        if all(((mask >> idx[a]) & 1) != ((mask >> idx[b]) & 1) for a, b in riv):
            return "yes", True
    return "no", True


# ---------------- 13 kinship_descendants
def s_kinship_descendants(q):
    par = {c: p for p, c in re.findall(r"(\w+) is the parent of (\w+)\.", q)}
    ps = split_and(re.search(r"Choose from (.+)\.$", q).group(1))
    kids = {p: [c for c, pp in par.items() if pp == p] for p in ps}
    def desc(p):
        return set(kids[p]) | set().union(*[desc(c) for c in kids[p]]) if kids[p] else set()
    if "most grandchildren" in q:
        sc = {p: len({g for c in kids[p] for g in kids[c]}) for p in ps}
    else:
        sc = {p: len(desc(p)) for p in ps}
    top = max(sc.values())
    best = [p for p in ps if sc[p] == top]
    return best[0], len(best) == 1


# ---------------- 14 order_tournament_wins
def s_order_tournament_wins(q):
    ps = split_and(re.match(r"(.+?) played a round-robin", q).group(1))
    res = re.findall(r"(\w+) beat (\w+)\.", q)
    assert len(res) == len(ps) * (len(ps) - 1) // 2
    assert len({frozenset(x) for x in res}) == len(res)
    wins = {p: 0 for p in ps}
    for a, _ in res:
        wins[a] += 1
    f = max if "the most games" in q else min
    top = f(wins.values())
    best = [p for p in ps if wins[p] == top]
    return best[0], len(best) == 1


# ---------------- 15 spatial_grid_walk
def s_spatial_grid_walk(q):
    rows = [r.split(", ") for r in re.findall(r"Row \d+: (.+?)\.(?= )", q)]
    start = re.search(r"You start at (\w+)\.", q).group(1)
    moves = re.search(r"You move (.+?), one cell each time", q).group(1).split(", then ")
    pos = next((i, j) for i, r in enumerate(rows) for j, c in enumerate(r) if c == start)
    d = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    for m in moves:
        i, j = pos[0] + d[m][0], pos[1] + d[m][1]
        if 0 <= i < len(rows) and 0 <= j < len(rows[0]) and rows[i][j] != "wall":
            pos = (i, j)
    return rows[pos[0]][pos[1]], True


# ---------------- 16 spatial_relative_directions
def s_spatial_relative_directions(q):
    facts = re.findall(r"(\w+) is (\d+) blocks? (north|south|east|west) of (\w+)\.", q)
    anchor = re.search(r"farthest from (\w+) by street distance", q).group(1)
    d = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    xy = {anchor: (0, 0)}
    changed = True
    while changed:
        changed = False
        for a, k, dr, b in facts:
            k = int(k)
            if b in xy and a not in xy:
                xy[a] = (xy[b][0] + d[dr][0] * k, xy[b][1] + d[dr][1] * k); changed = True
            elif a in xy and b not in xy:
                xy[b] = (xy[a][0] - d[dr][0] * k, xy[a][1] - d[dr][1] * k); changed = True
    dist = {p: abs(v[0]) + abs(v[1]) for p, v in xy.items() if p != anchor}
    top = max(dist.values())
    best = sorted(p for p in dist if dist[p] == top)
    return best[0], len(best) == 1


# ---------------- 17 temporal_critical_path
def s_temporal_critical_path(q):
    jobs = {}
    for s in sentences(q):
        if m := re.match(r"(\w+)'s job takes (\d+) days? and starts on day 0\.", s):
            jobs[m.group(1)] = (int(m.group(2)), [])
        elif m := re.match(r"(\w+)'s job takes (\d+) days? and starts as soon as the jobs? of (.+?) (?:is|are all) finished\.", s):
            jobs[m.group(1)] = (int(m.group(2)), split_and(m.group(3)))
    memo = {}
    def fin(p):
        if p not in memo:
            d, deps = jobs[p]
            memo[p] = max([fin(x) for x in deps], default=0) + d
        return memo[p]
    f = {p: fin(p) for p in jobs}
    top = max(f.values())
    best = [p for p in f if f[p] == top]
    return best[0], len(best) == 1


# ---------------- 18 temporal_interval_overlap
def s_temporal_interval_overlap(q):
    iv = {}
    for s in sentences(q):
        if m := re.match(r"(.+?) ran from day (\d+) to day (\d+), both days included\.", s):
            iv[m.group(1).lower()] = (int(m.group(2)), int(m.group(3)))
        elif m := re.match(r"(.+?) started on day (\d+) and went on for (\d+) days? \(day \d+ counts as the first\)\.", s):
            st, du = int(m.group(2)), int(m.group(3))
            iv[m.group(1).lower()] = (st, st + du - 1)
    a, b = re.search(r"Did (.+?) and (.+?) overlap", q).groups()
    days_a = set(range(iv[a][0], iv[a][1] + 1))
    days_b = set(range(iv[b][0], iv[b][1] + 1))
    return ("yes" if days_a & days_b else "no"), True


# ---------------- 19 temporal_weekday_shift
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def s_temporal_weekday_shift(q):
    ss = sentences(q)
    m = re.match(r"(.+?) took place on a (\w+)\.", ss[0])
    day = {m.group(1).lower(): DAYS.index(m.group(2))}
    rel = []
    for s in ss[1:]:
        if m := re.match(r"(.+?) took place (\d+) days? (after|before) (.+?)\.$", s):
            a, k, ab, b = m.group(1).lower(), int(m.group(2)), m.group(3), m.group(4).lower()
            rel.append((a, b, k if ab == "after" else -k))  # date(a) = date(b) + k
    changed = True
    while changed:
        changed = False
        for a, b, k in rel:
            if b in day and a not in day:
                day[a] = (day[b] + k) % 7; changed = True
            elif a in day and b not in day:
                day[b] = (day[a] - k) % 7; changed = True
    ask = re.search(r"On which day of the week did (.+?) take place\?", q).group(1).lower()
    return DAYS[day[ask]], True


# ---------------- 20 tracking_accounts
def s_tracking_accounts(q):
    bal = {p: int(x) for p, x in re.findall(r"(\w+) has (\d+) dollars?", q.split(". ")[0])}
    for s in sentences(q)[1:]:
        if m := re.match(r"(\w+) pays (\w+) (\d+) dollars?\.", s):
            bal[m.group(1)] -= int(m.group(3)); bal[m.group(2)] += int(m.group(3))
        elif m := re.match(r"(\w+) earns (\d+) dollars?\.", s):
            bal[m.group(1)] += int(m.group(2))
        elif m := re.match(r"(\w+) gives half of their money to (\w+)\.", s):
            h = Fraction(bal[m.group(1)], 2)
            assert h.denominator == 1, "odd halving"
            bal[m.group(1)] -= int(h); bal[m.group(2)] += int(h)
    f = max if "the most money" in q else min
    top = f(bal.values())
    best = [p for p in bal if bal[p] == top]
    assert min(bal.values()) >= 0
    return best[0], len(best) == 1


SOLVERS = {k[2:]: v for k, v in globals().items() if k.startswith("s_")}

if __name__ == "__main__":
    fx = sys.argv[1]
    tot = bad = 0
    for f in sorted(os.listdir(fx)):
        lid = f[len("R1."):-len(".jsonl")]
        rows = [json.loads(x) for x in open(os.path.join(fx, f))]
        nb = nu = 0
        for x in rows:
            tot += 1
            try:
                a, uniq = SOLVERS[lid](x["question"])
            except Exception as e:  # report, never hide
                a, uniq = f"ERR {type(e).__name__}: {e}", False
            if a != x["answer"] or not uniq:
                bad += 1; nb += 1
                print(f"  MISMATCH {x['id']} key={x['answer']!r} mine={a!r} unique={uniq}")
        print(f"{lid}: {len(rows)} items, {nb} mismatches")
    print(f"TOTAL {tot} items, {bad} mismatches")
