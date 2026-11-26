# ruff: noqa
# mypy: ignore-errors
# COPIED from docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/solvers3.py (= audit3_r1/solvers3.py) by Claude Opus 5.5 (arbor-auditor), audit 3/4 of R1, for the round-4 re-run (R-24, R-26).
# Edits by the round-4 implementer (Claude Sonnet 5.5), all listed in studies/m0/NOTES_FIX4_R1.md: none (header only)
# ruff: noqa
"""Audit 3 (R1): independent solvers that read ONLY the rendered question text (never the structured form, never the key).

Written by the auditor from the wording of each item; imports nothing from studies.m0. Each solver returns the answer
string, or raises Ambiguous(reason) when the text does not determine a unique answer (several solutions, ties, ...).
"""
import itertools, re
from collections import defaultdict, deque
from fractions import Fraction


class Ambiguous(Exception):
    pass


NAME = r"[A-Z][a-z]+"


def sentences(q):
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z\"0-9a-z])", q) if s]


def opts_of(q):
    m = re.search(r"Choose from (.+?)\.\s*$", q)
    if not m:
        return None
    parts = m.group(1).split(", ")
    last = parts[-1].rsplit(" and ", 1)
    return [*parts[:-1], *last]


def unique(vals, what="answer"):
    vals = list(vals)
    if len(vals) != 1:
        raise Ambiguous(f"{what}: {len(vals)} candidates")
    return vals[0]


def split_and(s):
    parts = s.split(", ")
    last = parts[-1].rsplit(" and ", 1)
    return [*parts[:-1], *last]


# ------------------------------------------------------------------ scheduling
def activity_selection_r4(q):
    ms = [(int(a), int(b)) for a, b in re.findall(r"meeting runs from minute (\d+) to minute (\d+)\.", q)]
    ms.sort()
    starts = [s for s, _ in ms]
    import bisect
    n = len(ms)
    dp = [0] * (n + 1)
    for i in range(n - 1, -1, -1):  # weighted-interval DP (unit weights), not the greedy rule
        j = bisect.bisect_left(starts, ms[i][1])
        dp[i] = max(dp[i + 1], 1 + dp[j])
    return str(dp[0])


def topological_order_r4(q):
    jobs = {}
    for m in re.finditer(rf"({NAME}) has no prerequisite\.", q):
        jobs[m.group(1)] = set()
    for m in re.finditer(rf"({NAME}) needs (.+?) to be done first\.", q):
        jobs[m.group(1)] = set(split_and(m.group(2)))
    day = int(re.search(r"done on day (\d+)\?", q).group(1))
    done, order = set(), []
    while len(order) < len(jobs):
        ready = sorted(p for p in jobs if p not in done and jobs[p] <= done)
        if not ready:
            raise Ambiguous("cycle")
        order.append(ready[0])
        done.add(ready[0])
    return order[day - 1]


# ------------------------------------------------------------------ rules
COLS = None


def _attr_parse(s):
    s = s.strip()
    # top-level split on ' and ' / ' or ' outside parentheses
    depth, parts, cur, ops, i = 0, [], "", set(), 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if depth == 0:
            for op in (" and ", " or "):
                if s.startswith(op, i):
                    parts.append(cur)
                    cur = ""
                    ops.add(op.strip())
                    i += len(op)
                    break
            else:
                cur += c
                i += 1
                continue
            continue
        cur += c
        i += 1
    parts.append(cur)
    if len(parts) > 1:
        if len(ops) != 1:
            raise Ambiguous("mixed and/or at one level")
        return [ops.pop(), *[_attr_parse(p) for p in parts]]
    s = parts[0].strip()
    if s.startswith("(") and s.endswith(")"):
        # strip one pair only if it encloses the whole
        d = 0
        for k, c in enumerate(s):
            d += c == "("
            d -= c == ")"
            if d == 0 and k < len(s) - 1:
                break
        else:
            return _attr_parse(s[1:-1])
    if s.startswith("it is not true that "):
        return ["not", _attr_parse(s[len("it is not true that "):])]
    if s.startswith("it is "):
        return ["is", s[6:]]
    if s.startswith("it has "):
        return ["has", s[7:]]
    raise Ambiguous(f"cannot parse rule atom {s!r}")


def _attr_eval(t, badge):
    if t[0] == "is":
        return t[1] in (badge[0], badge[1])
    if t[0] == "has":
        return t[1] == badge[2]
    if t[0] == "not":
        return not _attr_eval(t[1], badge)
    if t[0] == "and":
        return all(_attr_eval(x, badge) for x in t[1:])
    return any(_attr_eval(x, badge) for x in t[1:])


def attribute_rule(q):
    rule = re.search(r"satisfies this rule: (.+?)\. The badges: ", q).group(1)
    tree = _attr_parse(rule)
    badges = {m.group(1): (m.group(2), m.group(3), m.group(4)) for m in re.finditer(rf"({NAME})'s badge is (\w+), (\w+) and has (an? \w+)", q)}
    return unique([o for o, b in badges.items() if _attr_eval(tree, b)], "badges")


def _dt_parse(s):
    s = s.strip()
    if not s.startswith("if "):
        return ["do", s]
    m = re.match(r"if (.+?), then \(", s)
    cond = m.group(1)
    i = m.end() - 1

    def grab(i):
        assert s[i] == "("
        d = 0
        for k in range(i, len(s)):
            d += s[k] == "("
            d -= s[k] == ")"
            if d == 0:
                return s[i + 1:k], k + 1
        raise Ambiguous("paren")

    a, j = grab(i)
    assert s.startswith(", otherwise (", j), s[j:j + 20]
    b, k = grab(j + len(", otherwise "))
    return ["if", cond, _dt_parse(a), _dt_parse(b)]


def conditional_decision_tree_r4(q):
    rule = re.search(r"Your rule is: (.+?)\. Right now, ", q).group(1)
    facts = {}
    st = re.search(r"Right now, (.+?)\. What do you do\?", q).group(1)
    for part in st.split("; "):
        m = re.match(r"it is (true|false) that (.+)$", part)
        facts[m.group(2)] = m.group(1) == "true"
    t = _dt_parse(rule)
    while t[0] == "if":
        t = t[2] if facts[t[1]] else t[3]
    return t[1]


def conditional_threshold_rule_r4(q):
    w = {m.group(1): int(m.group(2)) for m in re.finditer(rf"({NAME}) has weight (\d+)", q)}
    d = int(re.search(r"is at least (-?\d+) \(", q).group(1))
    votes = re.search(r"The votes: (.+?)\. Does the motion pass", q).group(1)
    tot = 0
    for part in votes.split(", "):
        p, v = part.split(" ")
        tot += w[p] if v == "yes" else (-w[p] if v == "no" else 0)
    return "yes" if tot >= d else "no"


def conditional_chain(q):
    body = q[: q.index(" Is ")]
    qv = re.search(r"Is ([A-Z]) true\?", q).group(1)
    facts, rules, vs = [], [], set()
    for s in sentences(body):
        m = re.match(r"([A-Z]) is (true|false)\.$", s)
        if m:
            facts.append((m.group(1), m.group(2) == "true"))
            vs.add(m.group(1))
            continue
        m = re.match(r"If (.+), then ([A-Z]) is (true|false)\.$", s)
        ante = [(a, b == "true") for a, b in re.findall(r"([A-Z]) is (true|false)", m.group(1))]
        rules.append((ante, (m.group(2), m.group(3) == "true")))
        vs |= {a for a, _ in ante} | {m.group(2)}
    vs.add(qv)
    vs = sorted(vs)
    seen = set()
    for bits in itertools.product((False, True), repeat=len(vs)):
        w = dict(zip(vs, bits))
        if any(w[v] != b for v, b in facts):
            continue
        if all(not all(w[v] == b for v, b in a) or w[c] == cb for a, (c, cb) in rules):
            seen.add(w[qv])
    if not seen:
        raise Ambiguous("inconsistent")
    return "cannot be determined" if len(seen) == 2 else ("yes" if True in seen else "no")


# ------------------------------------------------------------------ boolean / spatial folds
def boolean_lights_r4(q):
    nl = int(re.search(r"There are (\d+) lamps", q).group(1))
    st = [0] * (nl + 1)
    start = re.search(r"At the start, (.+?)\. The ", q).group(1)
    if start == "all lamps are on":
        st = [1] * (nl + 1)
    elif start != "all lamps are off":
        m = re.match(r"lamps? (.+?) (?:is|are) on, and all the lamps not named here are off$", start)
        for x in split_and(m.group(1)):
            st[int(x)] = 1
    sw = {m.group(1): [int(x) for x in split_and(m.group(2))] for m in re.finditer(r"The (\w+) switch toggles lamps? (.+?) \(each one", q)}
    presses = re.search(r"pressed in this order: (.+?)\. Is lamp", q).group(1).split(", ")
    for c in presses:
        for l in sw[c]:
            st[l] ^= 1
    ask = int(re.search(r"Is lamp (\d+) on at the end\?", q).group(1))
    return "yes" if st[ask] else "no"


def compass_turns(q):
    dirs = ["north", "east", "south", "west"]
    cur = dirs.index(re.search(r"You are facing (\w+)\.", q).group(1))
    body = re.search(r"\. You (.+?)\. Which direction", q).group(1)
    deg = {"turn left": -90, "turn right": 90, "turn around": 180, "turn 90 degrees clockwise": 90, "turn 270 degrees clockwise": 270,
           "turn 90 degrees counterclockwise": -90, "turn 180 degrees clockwise": 180}
    for step in body.split(", then "):
        if step.startswith("walk "):
            continue
        cur = (cur + deg[step] // 90) % 4
    return dirs[cur]


def spatial_grid_walk_r2(q):
    rows = re.findall(r"Row \d+: (.+?)\.", q)
    grid = [r.split(", ") for r in rows]
    start = re.search(r"You start at (\w+)\.", q).group(1)
    pos = unique([(i, j) for i, r in enumerate(grid) for j, c in enumerate(r) if c == start], "start")
    moves = re.search(r"You move (.+?), one cell each time", q).group(1).split(", then ")
    d = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    for m in moves:
        i, j = pos[0] + d[m][0], pos[1] + d[m][1]
        if 0 <= i < len(grid) and 0 <= j < len(grid[0]) and grid[i][j] != "wall":
            pos = (i, j)
    return grid[pos[0]][pos[1]]


def spatial_relative_directions_r4(q):
    d = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    adj = defaultdict(list)
    for a, k, dr, b in re.findall(r"(\w+) is (\d+) blocks? (north|south|east|west) of (\w+)\.", q):
        k = int(k)
        v = (d[dr][0] * k, d[dr][1] * k)
        adj[b].append((a, v))
        adj[a].append((b, (-v[0], -v[1])))
    x, y = re.search(r"How far apart are (\w+) and (\w+) by", q).groups()
    pos = {x: (0, 0)}
    dq = deque([x])
    while dq:
        u = dq.popleft()
        for w, v in adj[u]:
            p = (pos[u][0] + v[0], pos[u][1] + v[1])
            if w in pos:
                if pos[w] != p:
                    raise Ambiguous("inconsistent")
                continue
            pos[w] = p
            dq.append(w)
    if y not in pos:
        raise Ambiguous("not connected")
    return str(abs(pos[y][0]) + abs(pos[y][1]))


# ------------------------------------------------------------------ categories
def categories_default_exceptions_r4(q):
    up = {}
    for a, b in re.findall(r"Every (\w+) is an? (\w+)\.", q):
        if a in up and up[a] != b:
            raise Ambiguous("two parents")
        up[a] = b
    rules = defaultdict(list)
    for g, ok, v in re.findall(r"An? (\w+) (can|cannot) (\w+)\.", q):
        rules[(g, v)].append(ok == "can")
    member, g = re.search(rf"({NAME}) is an? (\w+)\. Can", q).groups()
    verb = re.search(rf"Can {member} (\w+)\?", q).group(1)
    seen = set()
    while True:
        if (g, verb) in rules:
            v = set(rules[(g, verb)])
            return "yes" if unique(v, "rule signs") else "no"
        if g not in up or g in seen:
            raise Ambiguous("no rule applies")
        seen.add(g)
        g = up[g]


def categories_follow_r4(q):
    alls = re.findall(r"All (\w+) are (\w+)\.", q)
    nos = re.findall(r"No (\w+) are (\w+)\.", q)
    somes = re.findall(r"(?<![\"])Some (\w+) are (\w+)\.", q)
    stmt = re.search(r'Consider the statement: "(.+?)"', q).group(1)
    cats = sorted({x for p in [*alls, *nos, *somes] for x in p})
    m = re.match(r"every (\w+) is an? (\w+)$", stmt) or re.match(r"no (\w+) is an? (\w+)$", stmt) or re.match(r"some (\w+) are (\w+)$", stmt)
    kind = stmt.split()[0]
    x, y = m.groups()
    cats = sorted(set(cats) | {x, y})
    idx = {c: i for i, c in enumerate(cats)}
    n = len(cats)
    # admissible membership types: subsets closed under All and containing no No pair
    types = []
    for mask in range(1, 1 << n):
        ok = all(not (mask >> idx[a] & 1) or (mask >> idx[b] & 1) for a, b in alls) and all(not ((mask >> idx[a] & 1) and (mask >> idx[b] & 1)) for a, b in nos)
        if ok:
            types.append(mask)

    def sat(ts):  # existential premises: every group non-empty, every Some witnessed
        return all(any(t >> i & 1 for t in ts) for i in range(n)) and all(any((t >> idx[a] & 1) and (t >> idx[b] & 1) for t in ts) for a, b in somes)

    if not sat(types):
        raise Ambiguous("premises inconsistent")
    xi, yi = idx[x], idx[y]
    if kind == "every":
        holds = lambda t: not (t >> xi & 1) or (t >> yi & 1)  # universal: every realised type satisfies
        universal = True
    elif kind == "no":
        holds = lambda t: not ((t >> xi & 1) and (t >> yi & 1))
        universal = True
    else:
        holds = lambda t: not ((t >> xi & 1) and (t >> yi & 1))  # "some" is false iff the universal "no" holds
        universal = False
    can_univ = sat([t for t in types if holds(t)])
    can_break = any(not holds(t) for t in types)  # the maximal model contains a breaking type
    if universal:
        can_true, can_false = can_univ, can_break
    else:
        can_true, can_false = can_break, can_univ
    if can_true and can_false:
        return "cannot be determined"
    return "yes" if can_true else "no"


def equivalence_classes_r2(q):
    same = re.findall(r"(\w+) is the same thing as (\w+)\.", q)
    diff = re.findall(r"(\w+) is a different thing from (\w+)\.", q)
    x, y = re.search(r"Is (\w+) the same thing as (\w+)\?", q).groups()
    par = {}

    def f(a):
        par.setdefault(a, a)
        while par[a] != a:
            a = par[a]
        return a

    for a, b in same:
        par[f(a)] = f(b)
    for a, b in diff:
        if f(a) == f(b):
            raise Ambiguous("inconsistent")
    if f(x) == f(y):
        return "yes"
    if any({f(a), f(b)} == {f(x), f(y)} for a, b in diff):
        return "no"
    return "cannot be determined"


def road_reachability(q):
    adj = defaultdict(set)
    for a, b in re.findall(r"one-way road from (\w+) to (\w+)\.", q):
        adj[a].add(b)
    x, y = re.search(r"travel from (\w+) to (\w+) using", q).groups()
    seen, st = {x}, [x]
    while st:
        u = st.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                st.append(v)
    return "yes" if y in seen else "no"


def order_compare_r4(q):
    adj = defaultdict(set)
    for a, b in re.findall(rf"({NAME}) is taller than ({NAME})\.", q):
        adj[a].add(b)
    x, y = re.search(rf"Is ({NAME}) taller than ({NAME})\?", q).groups()

    def reach(s, t):
        seen, st = {s}, [s]
        while st:
            u = st.pop()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    st.append(v)
        return t in seen

    a, b = reach(x, y), reach(y, x)
    if a and b:
        raise Ambiguous("cycle")
    return "yes" if a else ("no" if b else "cannot be determined")


def order_extreme(q):
    adj = defaultdict(set)
    ppl = set()
    for a, b in re.findall(rf"({NAME}) is taller than ({NAME})\.", q):
        adj[a].add(b); ppl |= {a, b}
    for a, b in re.findall(rf"({NAME}) is shorter than ({NAME})\.", q):
        adj[b].add(a); ppl |= {a, b}
    ask, lst = re.search(r"Who is the (tallest|shortest) of (.+)\?", q).groups()
    ppl |= set(split_and(lst))
    # the tallest must be provably taller than everyone else
    def below(s):
        seen, st = {s}, [s]
        while st:
            u = st.pop()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); st.append(v)
        return seen
    if ask == "tallest":
        return unique([p for p in ppl if below(p) == ppl], "tallest")
    return unique([p for p in ppl if all(p in below(o) for o in ppl)], "shortest")


def order_tournament_wins(q):
    wins = defaultdict(int)
    ppl = split_and(re.match(r"(.+?) played a round-robin", q).group(1))
    for p in ppl:
        wins[p] += 0
    for a, b in re.findall(rf"({NAME}) beat ({NAME})\.", q):
        wins[a] += 1
    ask = re.search(r"Who won the (most|fewest) games\?", q).group(1)
    t = max(wins.values()) if ask == "most" else min(wins.values())
    return unique([p for p in wins if wins[p] == t], "extreme")


# ------------------------------------------------------------------ kinship
def _parents(q):
    par = {}
    for a, b in re.findall(rf"({NAME}) is the parent of ({NAME})\.", q):
        if b in par and par[b] != a:
            raise Ambiguous("two parents")
        par[b] = a
    for b, a in re.findall(rf"({NAME})'s parent is ({NAME})\.", q):
        if b in par and par[b] != a:
            raise Ambiguous("two parents")
        par[b] = a
    return par


def kinship_ancestor_r4(q):
    par = _parents(q)
    term, child = re.search(rf"Who is the ([a-z-]+) of ({NAME})\?", q).groups()
    k = {"grandparent": 2, "great-grandparent": 3, "great-great-grandparent": 4}[term]
    p = child
    for _ in range(k):
        if p not in par:
            raise Ambiguous("no ancestor")
        p = par[p]
    if p not in opts_of(q):
        raise Ambiguous("answer not an option")
    return p


def kinship_cousins(q):
    par = _parents(q)
    a, b = re.search(rf"Are ({NAME}) and ({NAME}) cousins\?", q).groups()
    pa, pb = par.get(a), par.get(b)
    return "yes" if pa and pb and pa != pb and par.get(pa) is not None and par.get(pa) == par.get(pb) else "no"


def kinship_descendants_r4(q):
    par = _parents(q)
    x = re.search(rf"Among the children of ({NAME}), who has", q).group(1)
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)

    def nd(p):
        return sum(1 + nd(c) for c in kids[p])

    cands = opts_of(q)
    if sorted(cands) != sorted(kids[x]):
        raise Ambiguous("options are not the children")
    sc = {c: nd(c) for c in cands}
    t = max(sc.values())
    return unique([c for c in cands if sc[c] == t], "most descendants")


# ------------------------------------------------------------------ truth / culprit / arrangement
def knights_knaves(q):
    stm = re.findall(rf'({NAME}) says: "(.+?)\."', q)
    ppl = [p for p, _ in stm]
    who = re.search(rf"Is ({NAME}) a knight or a knave\?", q).group(1)

    def holds(body, kn):
        m = re.match(rf"({NAME}) is a knight$", body)
        if m: return kn[m.group(1)]
        m = re.match(rf"({NAME}) is a knave$", body)
        if m: return not kn[m.group(1)]
        m = re.match(rf"({NAME}) and ({NAME}) are both knights$", body)
        if m: return kn[m.group(1)] and kn[m.group(2)]
        m = re.match(rf"at least one of ({NAME}) and ({NAME}) is a knave$", body)
        if m: return (not kn[m.group(1)]) or (not kn[m.group(2)])
        raise Ambiguous(body)

    sols = []
    for bits in itertools.product((True, False), repeat=len(ppl)):
        kn = dict(zip(ppl, bits))
        if all(holds(b, kn) == kn[p] for p, b in stm):
            sols.append(kn)
    if len(sols) != 1:
        raise Ambiguous(f"{len(sols)} knight/knave assignments")
    return "knight" if sols[0][who] else "knave"


def one_culprit(q):
    ppl = split_and(re.match(r"One of (.+?) took the last cake\.", q).group(1))
    stm = re.findall(rf'({NAME}) says: "(.+?)\."', q)
    k = int(re.search(r"Exactly (\d+) of these", q).group(1))

    def tr(body, c):
        m = re.match(rf"It was not ({NAME})$", body)
        if m: return m.group(1) != c
        m = re.match(rf"It was ({NAME}) or ({NAME})$", body)
        if m: return c in m.groups()
        m = re.match(rf"It was ({NAME})$", body)
        if m: return m.group(1) == c
        raise Ambiguous(body)

    return unique([c for c in ppl if sum(tr(b, c) for _, b in stm) == k], "culprit")


def seating_row(q):
    ppl = split_and(re.match(r"(.+?) sit in a row of", q).group(1))
    n = len(ppl)
    seat = int(re.search(r"Who sits in seat (\d+)\?", q).group(1))
    cons = []
    for a, b in re.findall(rf"({NAME}) sits immediately to the left of ({NAME})\.", q):
        cons.append(lambda p, a=a, b=b: p[b] == p[a] + 1)
    for a, b in re.findall(rf"({NAME}) sits somewhere to the left of ({NAME})\.", q):
        cons.append(lambda p, a=a, b=b: p[a] < p[b])
    for a in re.findall(rf"({NAME}) sits at one of the two ends", q):
        cons.append(lambda p, a=a: p[a] in (1, n))
    for a, s in re.findall(rf"({NAME}) sits in seat (\d+)\.", q):
        cons.append(lambda p, a=a, s=int(s): p[a] == s)
    for b, a, c in re.findall(rf"({NAME}) sits somewhere between ({NAME}) and ({NAME})\.", q):
        cons.append(lambda p, a=a, b=b, c=c: min(p[a], p[c]) < p[b] < max(p[a], p[c]))
    for a, b in re.findall(rf"({NAME}) and ({NAME}) do not sit next to each other\.", q):
        cons.append(lambda p, a=a, b=b: abs(p[a] - p[b]) != 1)
    sols = set()
    for perm in itertools.permutations(range(1, n + 1)):
        p = dict(zip(ppl, perm))
        if all(c(p) for c in cons):
            sols.add(next(x for x in ppl if p[x] == seat))
    return unique(sols, "seat")


def pet_owners(q):
    ppl = split_and(re.match(r"(.+?) each own exactly one different pet", q).group(1))
    pets = split_and(re.search(r"from this list: (.+?)\. ", q).group(1))
    ask = re.search(r"Who owns the (\w+)\?", q).group(1)
    cons = []
    for a, b in re.findall(rf"({NAME}) does not own the (\w+)\.", q):
        cons.append(lambda p, a=a, b=b: p[a] != b)
    for a, b, c in re.findall(rf"({NAME}) owns either the (\w+) or the (\w+)\.", q):
        cons.append(lambda p, a=a, b=b, c=c: p[a] in (b, c))
    for a, b in re.findall(rf"({NAME}) owns the (\w+)\.", q):
        cons.append(lambda p, a=a, b=b: p[a] == b)
    sols = set()
    for perm in itertools.permutations(pets):
        p = dict(zip(ppl, perm))
        if all(c(p) for c in cons):
            sols.add(next(x for x in ppl if p[x] == ask))
    return unique(sols, "owner")


# ------------------------------------------------------------------ containers / tracking
def containers_queue_line_r2(q):
    line = split_and(re.search(r"A line, from front to back, is: (.+?)\. ", q).group(1))
    j = int(re.search(r"Who is in position (\d+) from the front", q).group(1))
    body = q[q.index(". ", q.index("from front to back")) + 2: q.index(" Who is in position")]
    for s in sentences(body):
        if (m := re.match(rf"({NAME}) joins at the back\.", s)):
            line.append(m.group(1))
        elif (m := re.match(rf"({NAME}) is let in at the very front\.", s)):
            line.insert(0, m.group(1))
        elif s == "The person at the front is served and leaves.":
            line.pop(0)
        elif (m := re.match(rf"({NAME}) gets tired and leaves\.", s)):
            line.remove(m.group(1))
        elif s == "The person at the front goes to the back of the line.":
            line.append(line.pop(0))
        else:
            raise Ambiguous(s)
    return line[j - 1]


def containers_stack_piles_r4(q):
    piles = {}
    for p, cont in re.findall(r"The (\w+) pile holds, from bottom to top: (.+?)\.", q):
        piles[p] = [] if cont == "nothing" else split_and(cont)
    for s in sentences(q):
        if (m := re.match(r"Move the top block of the (\w+) pile onto the (\w+) pile\.", s)):
            piles[m.group(2)].append(piles[m.group(1)].pop())
        elif (m := re.match(r"Turn the (\w+) pile upside down\.", s)):
            piles[m.group(1)].reverse()
    ask = re.search(r"on top of the (\w+) pile at the end\?", q).group(1)
    return piles[ask][-1]


def swap_tracking(q):
    hold = dict(re.findall(rf"({NAME}) holds the ([\w-]+)", q))
    for s in sentences(q):
        if (m := re.match(rf"({NAME}) and ({NAME}) swap what they are holding\.", s)):
            a, b = m.groups(); hold[a], hold[b] = hold[b], hold[a]
        elif (m := re.match(rf"({NAME}) hands their item to ({NAME}), ({NAME}) hands theirs to ({NAME}), and ({NAME}) hands theirs to ({NAME}), all at once\.", s)):
            a, b, b2, c, c2, a2 = m.groups()
            assert b == b2 and c == c2 and a == a2
            hold[a], hold[b], hold[c] = hold[c], hold[a], hold[b]
    who = re.search(rf"What is ({NAME}) holding at the end\?", q).group(1)
    return hold[who]


def tracking_accounts(q):
    bal = {p: int(v) for p, v in re.findall(rf"({NAME}) has (\d+) dollars?", q.split(". ")[0])}
    for s in sentences(q):
        if (m := re.match(rf"({NAME}) pays ({NAME}) (\d+) dollars?\.", s)):
            a, b, v = m.groups(); bal[a] -= int(v); bal[b] += int(v)
        elif (m := re.match(rf"({NAME}) earns (\d+) dollars?\.", s)):
            bal[m.group(1)] += int(m.group(2))
        elif (m := re.match(rf"({NAME}) gives half of their money to ({NAME})\.", s)):
            a, b = m.groups()
            if bal[a] % 2:
                raise Ambiguous("half of an odd amount")
            h = bal[a] // 2; bal[a] -= h; bal[b] += h
    ask = re.search(r"Who has the (most|least) money at the end\?", q).group(1)
    t = max(bal.values()) if ask == "most" else min(bal.values())
    return unique([p for p in bal if bal[p] == t], "extreme")


# ------------------------------------------------------------------ elimination
def elimination_josephus(q):
    ppl = split_and(re.match(r"(.+?) stand in a circle in this order", q).group(1))
    k = int(re.search(r"Every time the count reaches (\d+),", q).group(1))
    dq = deque(ppl)
    out = []
    while dq:
        dq.rotate(-(k - 1))
        out.append(dq.popleft())
    if "last person left" in q:
        return out[-1]
    j = int(re.search(r"Who is number (\d+) to leave", q).group(1))
    return out[j - 1]


def elimination_bracket_r4(q):
    ppl = re.search(r"listed in bracket order: (.+?)\. In round one", q).group(1).split(", ")
    beat = set(re.findall(rf"({NAME}) beat ({NAME})\.", q))
    rnd, ko, final = ppl, {}, None
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2]):
            if ((a, b) in beat) == ((b, a) in beat):
                raise Ambiguous("result missing or double")
            w, l = (a, b) if (a, b) in beat else (b, a)
            ko[l] = w; nxt.append(w)
            if len(rnd) == 2:
                final = l
        rnd = nxt
    if "Who wins the tournament?" in q:
        return rnd[0]
    if "Who loses the final?" in q:
        return final
    x = re.search(rf"Who knocks ({NAME}) out\?", q).group(1)
    return ko[x]


# ------------------------------------------------------------------ equivalence potentials
def equivalence_exchange_rates(q):
    adj = defaultdict(list)
    for p, a, qq, b in re.findall(r"(\d+) units of ([\w-]+) are worth the same as (\d+) units of ([\w-]+)\.", q):
        r = Fraction(int(qq), int(p))  # value(a) = r * value(b)
        adj[a].append((b, 1 / r)); adj[b].append((a, r))
    items = split_and(re.search(r"Which of (.+?) is worth the most", q).group(1))
    val = {items[0]: Fraction(1)}
    st = [items[0]]
    while st:
        u = st.pop()
        for w, f in adj[u]:  # value(w) = f * value(u)
            v = val[u] * f
            if w in val:
                if val[w] != v:
                    raise Ambiguous("inconsistent")
                continue
            val[w] = v; st.append(w)
    if set(val) != set(items):
        raise Ambiguous("not connected")
    t = max(val.values())
    return unique([i for i in items if val[i] == t], "most")


def event_timeline(q):
    adj = defaultdict(list)
    for a, d, b in re.findall(r"([A-Z][\w -]+?) took place (\d+) days after ([\w -]+?)\.", q):
        adj[a.lower()].append((b.lower(), -int(d))); adj[b.lower()].append((a.lower(), int(d)))
    for a, d, b in re.findall(r"([A-Z][\w -]+?) took place (\d+) days before ([\w -]+?)\.", q):
        adj[a.lower()].append((b.lower(), int(d))); adj[b.lower()].append((a.lower(), -int(d)))
    ask, lst = re.search(r"Which of these events took place (first|last): (.+)\?", q).groups()
    evs = split_and(lst)
    day = {evs[0]: 0}
    st = [evs[0]]
    while st:
        u = st.pop()
        for w, dd in adj[u]:  # day(w) = day(u) + dd
            if w in day:
                if day[w] != day[u] + dd:
                    raise Ambiguous("inconsistent")
                continue
            day[w] = day[u] + dd; st.append(w)
    if set(day) != set(evs):
        raise Ambiguous("not connected")
    t = min(day.values()) if ask == "first" else max(day.values())
    return unique([e for e in evs if day[e] == t], "extreme")


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def temporal_weekday_shift(q):
    first, wd = re.match(r"([A-Z][\w -]+?) took place on a (\w+)\.", q).groups()
    adj = defaultdict(list)
    for a, d, b in re.findall(r"([A-Z][\w -]+?) took place (\d+) days? after ([\w -]+?)\.", q):
        adj[a.lower()].append((b.lower(), -int(d))); adj[b.lower()].append((a.lower(), int(d)))
    for a, d, b in re.findall(r"([A-Z][\w -]+?) took place (\d+) days? before ([\w -]+?)\.", q):
        adj[a.lower()].append((b.lower(), int(d))); adj[b.lower()].append((a.lower(), -int(d)))
    ask = re.search(r"On which day of the week did (.+?) take place\?", q).group(1).lower()
    day = {first.lower(): DAYS.index(wd)}
    st = [first.lower()]
    while st:
        u = st.pop()
        for w, dd in adj[u]:
            if w in day:
                if (day[w] - day[u] - dd) % 7:
                    raise Ambiguous("inconsistent")
                continue
            day[w] = day[u] + dd; st.append(w)
    return DAYS[day[ask] % 7]


def temporal_interval_overlap(q):
    span = {}
    for e, a, b in re.findall(r"([A-Z][\w -]+?) ran from day (\d+) to day (\d+), both days included\.", q):
        span[e.lower()] = (int(a), int(b))
    for e, s, d in re.findall(r"([A-Z][\w -]+?) started on day (\d+) and went on for (\d+) days?", q):
        span[e.lower()] = (int(s), int(s) + int(d) - 1)
    x, y = re.search(r"Did (.+?) and (.+?) overlap, that is", q).groups()
    a, b = span[x.lower()], span[y.lower()]
    return "yes" if max(a[0], b[0]) <= min(a[1], b[1]) else "no"


def temporal_critical_path_r4(q):
    jobs = {}
    for p, d, rest in re.findall(rf"({NAME})'s job takes (\d+) days? and (starts on day 0|starts as soon as .+?finished)\.", q):
        deps = [] if rest == "starts on day 0" else split_and(re.match(r"starts as soon as the jobs? of (.+?) (?:is|are all) finished", rest).group(1))
        jobs[p] = (int(d), deps)
    fin = {}

    def f(p):
        if p not in fin:
            fin[p] = max([f(x) for x in jobs[p][1]], default=0) + jobs[p][0]
        return fin[p]

    return str(max(f(p) for p in jobs))


# ------------------------------------------------------------------ graphs / networks
def _wedges(q, pat):
    return [(a, b, int(w)) for a, b, w in re.findall(pat, q)]


def graph_shortest_route_r4(q):
    es = _wedges(q, r"two-way road between (\w+) and (\w+) of length (\d+)\.")
    s, t = re.search(r"route from (\w+) to (\w+) along", q).groups()
    nodes = sorted({x for a, b, _ in es for x in (a, b)})
    INF = 10 ** 9
    d = {u: {v: (0 if u == v else INF) for v in nodes} for u in nodes}
    for a, b, w in es:
        d[a][b] = min(d[a][b], w); d[b][a] = min(d[b][a], w)
    for k in nodes:
        for i in nodes:
            for j in nodes:
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    if d[s][t] >= INF:
        raise Ambiguous("unreachable")
    return str(d[s][t])


def mst_cost_r4(q):
    es = _wedges(q, r"A road between (\w+) and (\w+) could be built with length (\d+)\.")
    nodes = sorted({x for a, b, _ in es for x in (a, b)})
    inn, tot = {nodes[0]}, 0  # Prim
    while len(inn) < len(nodes):
        c = [(w, a, b) for a, b, w in es if (a in inn) != (b in inn)]
        if not c:
            raise Ambiguous("disconnected")
        w, a, b = min(c)
        tot += w; inn |= {a, b}
    return str(tot)


def graph_bipartite(q):
    adj = defaultdict(set)
    ppl = split_and(re.match(r"(.+?) must be split into two teams\.", q).group(1))
    for a, b in re.findall(rf"({NAME}) and ({NAME}) are rivals\.", q):
        adj[a].add(b); adj[b].add(a)
    col = {}
    for s in ppl:
        if s in col:
            continue
        col[s] = 0
        dq = deque([s])
        while dq:
            u = dq.popleft()
            for v in adj[u]:
                if v not in col:
                    col[v] = 1 - col[u]; dq.append(v)
                elif col[v] == col[u]:
                    return "no"
    return "yes"


# ------------------------------------------------------------------ games / voting / matching / sets
def _nest(s):
    s = s.strip()
    if not s.startswith("("):
        return int(s)
    inner = s[1:-1]
    parts, d, cur = [], 0, ""
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
        if d == 0 and inner.startswith(" or ", i):
            parts.append(cur); cur = ""; i += 4; continue
        cur += c; i += 1
    parts.append(cur)
    return [_nest(p) for p in parts]


def minimax_tree_r4(q):
    first = re.search(r"(Max|Min) choosing first", q).group(1)
    tree = _nest(re.search(r"nested options: (.+?)\. When the options", q).group(1))

    def v(t, mx):
        if isinstance(t, int):
            return t
        vals = [v(c, not mx) for c in t]
        return max(vals) if mx else min(vals)

    return str(v(tree, first == "Max"))


def nim_xor_r4(q):
    piles = [int(x) for x in re.search(r"piles of stones: ([\d, ]+)\.", q).group(1).split(", ")]
    x = 0
    for p in piles:
        x ^= p
    return "first" if x else "second"


def instant_runoff_r4(q):
    cands = split_and(re.match(r"(.+?) are candidates\.", q).group(1))
    bal = [(int(c), rk.split(" > ")) for c, rk in re.findall(r"(\d+) voters? rank them (.+?) \(best first\)\.", q)]
    alive = set(cands)
    while len(alive) > 1:
        t = {a: 0 for a in alive}
        for c, rk in bal:
            t[next(x for x in rk if x in alive)] += c
        lo = min(t.values())
        out = [a for a in alive if t[a] == lo]
        if len(out) != 1:
            raise Ambiguous("tie for fewest")
        alive.remove(out[0])
    return alive.pop()


def stable_matching_r4(q):
    pref = {p: lst.split(", ") for p, lst in re.findall(rf"({NAME}) would like, from best to worst: (.+?)\.", q)}
    props = split_and(re.search(r"a person from (.+?) who has no partner asks", q).group(1))
    ask = re.search(rf"Who is ({NAME})'s partner at the end\?", q).group(1)
    recs = [r for r in pref if r not in props]
    # brute force: all perfect matchings, keep the stable ones, take the proposer-optimal one
    stable = []
    for perm in itertools.permutations(recs):
        m = dict(zip(props, perm)); inv = {v: k for k, v in m.items()}
        ok = True
        for p in props:
            for r in pref[p][: pref[p].index(m[p])]:
                if pref[r].index(p) < pref[r].index(inv[r]):
                    ok = False; break
            if not ok:
                break
        if ok:
            stable.append(m)
    best = [m for m in stable if all(pref[p].index(m[p]) <= pref[p].index(o[p]) for o in stable for p in props)]
    m = unique([tuple(sorted(b.items())) for b in best], "proposer-optimal")
    return dict(m)[ask]


def venn_counting_r4(q):
    total = int(re.match(r"Among (\d+) people", q).group(1))
    inter = {}
    for n, g in re.findall(r"(\d+) people are in the (\w+) group", q):
        inter[frozenset([g])] = int(n)
    for n, a, b in re.findall(r"(\d+) are in both the (\w+) and the (\w+) groups", q):
        inter[frozenset([a, b])] = int(n)
    for n, gs in re.findall(r"(\d+) are in all of the (.+?) groups", q):
        inter[frozenset(split_and(gs))] = int(n)
    groups = sorted(g for s in inter for g in s)
    groups = sorted(set(groups))
    m4 = re.search(r"(\d+) are in all four groups", q)
    if m4:
        inter[frozenset(groups)] = int(m4.group(1))
    g = len(groups)
    # exact-region counts by Moebius inversion over the given intersections
    region = {}
    for k in range(1, g + 1):
        for S in itertools.combinations(groups, k):
            S = frozenset(S)
            region[S] = sum((-1) ** (len(T) - len(S)) * inter[T] for T in inter if S <= T)
    if any(v < 0 for v in region.values()):
        raise Ambiguous("negative region")
    none = total - sum(region.values())
    what = re.search(r"How many of the people are (.+?)\?", q).group(1)
    if what == "in none of these groups":
        return str(none)
    if what == "in exactly one of these groups":
        return str(sum(v for S, v in region.items() if len(S) == 1))
    if what == "in exactly two of these groups":
        return str(sum(v for S, v in region.items() if len(S) == 2))
    if what == "in at least two of these groups":
        return str(sum(v for S, v in region.items() if len(S) >= 2))
    raise Ambiguous(what)


SOLVERS = {f"R1.{n}": f for n, f in globals().items() if callable(f) and not n.startswith("_") and n not in ("unique", "sentences", "opts_of", "split_and", "Ambiguous", "defaultdict", "deque", "Fraction")}
