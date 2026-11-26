# ruff: noqa
"""Final R1 audit (fix 4): second solvers written from a separate context, from item TEXT only.

Each solver takes the question string exactly as a model would see it and returns (answer, status):
status "ok" = a unique answer under the convention stated in the text; anything else names why the item has no unique answer
("ambiguous:<reason>"). A text the parser does not recognise raises ParseError (counted separately, never as agreement).
Written by reading generated item texts (samples.py) only; no builder, generator answer code, implementer solver or audit solver was
read or imported. Exact arithmetic (Fraction) where division occurs."""
import itertools, re
from collections import deque
from fractions import Fraction


class ParseError(Exception):
    pass


def _need(m, what):
    if not m:
        raise ParseError(what)
    return m


def _nums(s):  # "1, 2 and 4" -> [1, 2, 4]
    parts = re.split(r", | and ", s.strip())
    return [int(p) for p in parts]


def _names(s):  # "a, b and c" -> ["a","b","c"]
    return [p.strip() for p in re.split(r", | and ", s.strip())]


def _sentences(q):
    return [s.strip() for s in re.split(r"(?<=[.?])\s+", q.strip()) if s.strip()]


# ------------------------------------------------------------------ boolean lights
def boolean_lights(q):
    n = int(_need(re.search(r"There are (\d+) lamps numbered 1 to (\d+)\.", q), "lamps").group(1))
    m = re.search(r"At the start, (?:lamps (.+?) are on|lamp (\d+) is on), and all the lamps not named here are off\.", q)
    if m:
        on = set(_nums(m.group(1) or m.group(2)))
    elif "At the start, all lamps are on." in q:
        on = set(range(1, n + 1))
    elif "At the start, all lamps are off." in q:
        on = set()
    else:
        raise ParseError("start")
    sw = {}
    for c, lst in re.findall(r"The (\w+) switch toggles lamps? ([\d, and]+?) \(each one goes from on to off or from off to on\)\.", q):
        if c in sw:
            return None, "ambiguous:switch defined twice"
        sw[c] = _nums(lst)
    presses = _names(_need(re.search(r"The switches are pressed in this order: ([a-z, ]+)\.", q), "presses").group(1))
    ask = int(_need(re.search(r"Is lamp (\d+) on at the end\? Answer yes or no\.$", q), "ask").group(1))
    if any(x < 1 or x > n for x in on) or not (1 <= ask <= n):
        return None, "ambiguous:lamp out of range"
    st = set(on)
    for p in presses:
        if p not in sw:
            return None, "ambiguous:unknown switch pressed"
        st ^= set(sw[p])
    return ("yes" if ask in st else "no"), "ok"


# ------------------------------------------------------------------ categories with default exceptions
def categories_default_exceptions(q):
    parent = {}
    for a, b in re.findall(r"Every (\w+) is an? (\w+)\.", q):
        parent.setdefault(a, []).append(b)
    props = {}
    for g, cc, v in re.findall(r"(?<![\w])An? (\w+) (can|cannot) (\w+)\.", q):  # FIX after try 1: the earlier pattern consumed ". " and skipped every other rule (my slip)
        props.setdefault((g, v), set()).add(cc == "can")
    _need("When two rules about the same thing disagree, the rule about the smaller (more specific) group wins." in q, "convention")
    m = _need(re.search(r"\. ([A-Z]\w+) is an? (\w+)\. Can \1 (\w+)\? Answer yes or no\.$", q), "person")
    g, verb = m.group(2), m.group(3)
    if any(len(v) > 1 for v in parent.values()):
        return None, "ambiguous:a group has two parents"
    seen = set()
    while True:
        if g in seen:
            return None, "ambiguous:cycle"
        seen.add(g)
        if (g, verb) in props:
            s = props[(g, verb)]
            if len(s) > 1:
                return None, "ambiguous:contradictory rules on one group"
            return ("yes" if next(iter(s)) else "no"), "ok"
        if g not in parent:
            return None, "ambiguous:no rule applies"
        g = parent[g][0]


# ------------------------------------------------------------------ compass turns
DIRS = ["north", "east", "south", "west"]


def compass_turns(q):
    m = _need(re.match(r"You are facing (north|east|south|west)\. You (.+)\. Which direction are you facing now\? Answer north, east, south or west\.$", q), "compass")
    d = DIRS.index(m.group(1))
    for c in m.group(2).split(", then "):
        if c == "turn left":
            d -= 1
        elif c == "turn right":
            d += 1
        elif c == "turn around":
            d += 2
        elif re.fullmatch(r"walk \d+ steps?", c):
            pass
        else:
            mm = _need(re.fullmatch(r"turn (\d+) degrees (clockwise|counterclockwise)", c), "cmd " + c)
            a = int(mm.group(1))
            if a % 90:
                return None, "ambiguous:angle not a multiple of 90"
            d += (a // 90) * (1 if mm.group(2) == "clockwise" else -1)
    return DIRS[d % 4], "ok"


# ------------------------------------------------------------------ decision tree
def _parse_tree(s, i):
    pre = "if the "
    if s.startswith(pre, i):
        j = s.index(" light is on, then (", i)
        name = s[i + len(pre):j]
        i = j + len(" light is on, then (")
        a, i = _parse_tree(s, i)
        if not s.startswith("), otherwise (", i):
            raise ParseError("otherwise at %d" % i)
        i += len("), otherwise (")
        b, i = _parse_tree(s, i)
        if not s.startswith(")", i):
            raise ParseError(") at %d" % i)
        return ("if", name, a, b), i + 1
    j = i
    while j < len(s) and s[j] not in "()":
        j += 1
    act = s[i:j]
    if not act or "," in act:
        raise ParseError("action")
    return ("act", act), j


def conditional_decision_tree(q):
    m = _need(re.match(r"Your rule is: (.+)\. Right now, (.+)\. What do you do\? Choose from (.+)\.$", q), "tree")
    t, end = _parse_tree(m.group(1), 0)
    if end != len(m.group(1)):
        raise ParseError("trailing rule text")
    state = {}
    for part in m.group(2).split("; "):
        mm = _need(re.fullmatch(r"it is (true|false) that the (\w+) light is on", part), "state " + part)
        if mm.group(2) in state and state[mm.group(2)] != (mm.group(1) == "true"):
            return None, "ambiguous:light stated both ways"
        state[mm.group(2)] = mm.group(1) == "true"
    opts = _names(m.group(3))
    while t[0] == "if":
        if t[1] not in state:
            return None, "ambiguous:needed light not stated"
        t = t[2] if state[t[1]] else t[3]
    if t[1] not in opts:
        return None, "ambiguous:action not among the options"
    return t[1], "ok"


# ------------------------------------------------------------------ weighted vote threshold
def conditional_threshold_rule(q):
    w = {a: int(b) for a, b in re.findall(r"(\w+) has weight (\d+)", q)}
    D = int(_need(re.search(r"is at least (-?\d+) \(members who abstain count for neither side\)\.", q), "D").group(1))
    votes = _need(re.search(r"The votes: (.+?)\. Does the motion pass\? Answer yes or no\.$", q), "votes").group(1)
    tot = 0
    seen = set()
    for part in votes.split(", "):
        mm = _need(re.fullmatch(r"(\w+) (yes|no|abstain)", part), "vote " + part)
        if mm.group(1) not in w or mm.group(1) in seen:
            return None, "ambiguous:unknown or repeated voter"
        seen.add(mm.group(1))
        tot += {"yes": 1, "no": -1, "abstain": 0}[mm.group(2)] * w[mm.group(1)]
    if seen != set(w):
        return None, "ambiguous:member without a vote"
    return ("yes" if tot >= D else "no"), "ok"


# ------------------------------------------------------------------ exchange rates
def equivalence_exchange_rates(q):
    adj = {}
    for a, x, b, y in re.findall(r"(\d+) units of (.+?) are worth the same as (\d+) units of (.+?)\.(?: |$)", q):
        a, b = int(a), int(b)
        r = Fraction(b, a)  # value(x) = r * value(y)
        adj.setdefault(x, []).append((y, r))
        adj.setdefault(y, []).append((x, 1 / r))
    m = _need(re.search(r"How many units of (.+?) are worth the same as (\d+) units of (.+?)\?$", q), "ask")
    tgt, N, src = m.group(1), int(m.group(2)), m.group(3)
    if src not in adj or tgt not in adj:
        return None, "ambiguous:unknown good"
    val = {src: Fraction(1)}
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for v, r in adj[u]:
            nv = val[u] / r  # value(u) = r value(v)  -> value(v) = value(u)/r
            if v in val:
                if val[v] != nv:
                    return None, "ambiguous:inconsistent rates"
            else:
                val[v] = nv
                dq.append(v)
    if tgt not in val:
        return None, "ambiguous:not connected"
    ans = N * val[src] / val[tgt]
    if ans.denominator != 1:
        return None, "ambiguous:non-integer answer %s" % ans
    return str(ans.numerator), "ok"


# ------------------------------------------------------------------ shortest route
def graph_shortest_route(q):
    adj = {}
    for a, b, l in re.findall(r"There is a two-way road between (.+?) and (.+?) of length (\d+)\.", q):
        adj.setdefault(a, []).append((b, int(l)))
        adj.setdefault(b, []).append((a, int(l)))
    m = _need(re.search(r"What is the smallest total length of a route from (.+?) to (.+?) along these roads\?$", q), "ask")
    s, t = m.group(1), m.group(2)
    if s not in adj or t not in adj:
        return None, "ambiguous:unknown town"
    import heapq
    dist = {s: 0}
    h = [(0, s)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]:
            continue
        for v, l in adj[u]:
            if d + l < dist.get(v, 1 << 60):
                dist[v] = d + l
                heapq.heappush(h, (d + l, v))
    if t not in dist:
        return None, "ambiguous:unreachable"
    return str(dist[t]), "ok"


# ------------------------------------------------------------------ knights and knaves
KK = [
    (r"(\w+) is a knight", lambda v, a: v[a[0]]),
    (r"(\w+) is a knave", lambda v, a: not v[a[0]]),
    (r"(\w+) and (\w+) are both knights", lambda v, a: v[a[0]] and v[a[1]]),
    (r"(\w+) and (\w+) are both knaves", lambda v, a: (not v[a[0]]) and (not v[a[1]])),
    (r"(\w+) and (\w+) are of the same kind", lambda v, a: v[a[0]] == v[a[1]]),
    (r"(\w+) and (\w+) are of different kinds", lambda v, a: v[a[0]] != v[a[1]]),
    (r"at least one of (\w+) and (\w+) is a knave", lambda v, a: (not v[a[0]]) or (not v[a[1]])),
    (r"at least one of (\w+) and (\w+) is a knight", lambda v, a: v[a[0]] or v[a[1]]),
    (r"exactly one of (\w+) and (\w+) is a knight", lambda v, a: v[a[0]] != v[a[1]]),
    (r"exactly one of (\w+) and (\w+) is a knave", lambda v, a: v[a[0]] != v[a[1]]),
]


def knights_knaves(q):
    _need(q.startswith("Each person is either a knight, who always tells the truth, or a knave, who always lies. "), "intro")
    st = []
    for who, said in re.findall(r'(\w+) says: "([^"]+?)\.?"', q):
        for pat, f in KK:
            mm = re.fullmatch(pat, said)
            if mm:
                st.append((who, f, mm.groups()))
                break
        else:
            raise ParseError("statement " + said)
    ask = _need(re.search(r"Is (\w+) a knight or a knave\? Answer knight or knave\.$", q), "ask").group(1)
    people = []
    for who, _, args in st:
        for p in (who, *args):
            if p not in people:
                people.append(p)
    if ask not in people:
        return None, "ambiguous:asked person not mentioned"
    if len({w for w, _, _ in st}) != len(st):
        pass  # a person may speak twice; each statement must hold
    vals = set()
    nsol = 0
    for bits in itertools.product((True, False), repeat=len(people)):
        v = dict(zip(people, bits))
        if all(f(v, a) == v[w] for w, f, a in st):
            nsol += 1
            vals.add(v[ask])
    if not vals:
        return None, "ambiguous:no consistent assignment"
    if len(vals) > 1:
        return None, "ambiguous:asked person undetermined"
    return ("knight" if vals.pop() else "knave"), "ok"


# ------------------------------------------------------------------ grid walk
DV = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}


def spatial_grid_walk(q):
    m = _need(re.match(r"A map has (\d+) rows \(row 1 is the northernmost\) and (\d+) columns \(column 1 is the westernmost\)\. ", q), "map")
    R, C = int(m.group(1)), int(m.group(2))
    grid = {}
    pos = {}
    for r in range(1, R + 1):
        row = _need(re.search(r"Row %d: ([^.]+)\." % r, q), "row %d" % r).group(1).split(", ")
        if len(row) != C:
            raise ParseError("row width")
        for c, cell in enumerate(row, 1):
            if cell != "wall":
                if cell in pos:
                    return None, "ambiguous:duplicate place name"
                pos[cell] = (r, c)
                grid[(r, c)] = cell
    start = _need(re.search(r"You start at (\w+)\.", q), "start").group(1)
    moves = _need(re.search(r"You move ((?:north|south|east|west)(?:, then (?:north|south|east|west))*), one cell each time\.", q), "moves").group(1).split(", then ")
    _need("A move into a wall or off the map does nothing." in q, "convention")
    opts = _names(_need(re.search(r"Which place do you end on\? Choose from (.+)\.$", q), "opts").group(1))
    if start not in pos:
        return None, "ambiguous:start not on map"
    r, c = pos[start]
    for mv in moves:
        dr, dc = DV[mv]
        if (r + dr, c + dc) in grid:
            r, c = r + dr, c + dc
    ans = grid[(r, c)]
    if ans not in opts:
        return None, "ambiguous:answer not among options"
    return ans, "ok"


# ------------------------------------------------------------------ swaps
def swap_tracking(q):
    m = _need(re.match(r"At the start (.+?)\. ", q), "start")
    hold = {}
    for part in m.group(1).split(", "):
        mm = _need(re.fullmatch(r"(\w+) holds the (.+)", part), "holds " + part)
        hold[mm.group(1)] = mm.group(2)
    rest = q[m.end():]
    mq = _need(re.search(r"What is (\w+) holding at the end\? Choose from (.+)\.$", rest), "ask")
    body = rest[:mq.start()].strip()
    for s in _sentences(body):
        a = re.fullmatch(r"(\w+) and (\w+) swap what they are holding\.", s)
        b = re.fullmatch(r"(\w+) hands their item to (\w+), \2 hands theirs to (\w+), and \3 hands theirs to \1, all at once\.", s)
        if a:
            x, y = a.groups()
            if x == y or x not in hold or y not in hold:
                return None, "ambiguous:bad swap"
            hold[x], hold[y] = hold[y], hold[x]
        elif b:
            x, y, z = b.groups()
            if len({x, y, z}) < 3 or not all(p in hold for p in (x, y, z)):
                return None, "ambiguous:bad rotation"
            hold[y], hold[z], hold[x] = hold[x], hold[y], hold[z]
        else:
            raise ParseError("op " + s)
    who = mq.group(1)
    opts = _names(mq.group(2))
    if who not in hold:
        return None, "ambiguous:unknown person"
    if hold[who] not in opts:
        return None, "ambiguous:answer not among options"
    return hold[who], "ok"


# ------------------------------------------------------------------ weekday shift
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def temporal_weekday_shift(q):
    off = {}
    adj = {}
    anchor = None
    for s in _sentences(q):
        a = re.fullmatch(r"The (.+?) took place on a (\w+day)\.", s)
        b = re.fullmatch(r"The (.+?) took place (\d+) days? (before|after) the (.+?)\.", s)
        c = re.fullmatch(r"On which day of the week did the (.+?) take place\?", s)
        if a:
            if anchor:
                return None, "ambiguous:two anchors"
            anchor = (a.group(1), WD.index(a.group(2)))
        elif b:
            x, n, d, y = b.group(1), int(b.group(2)), b.group(3), b.group(4)
            dlt = n if d == "after" else -n  # day(x) = day(y) + dlt
            adj.setdefault(x, []).append((y, -dlt))
            adj.setdefault(y, []).append((x, dlt))
        elif c:
            ask = c.group(1)
        else:
            raise ParseError("sentence " + s)
    if anchor is None:
        raise ParseError("anchor")
    off = {anchor[0]: 0}
    dq = deque([anchor[0]])
    while dq:
        u = dq.popleft()
        for v, d in adj.get(u, []):
            if v in off:
                if off[v] != off[u] + d:
                    return None, "ambiguous:inconsistent offsets"
            else:
                off[v] = off[u] + d
                dq.append(v)
    if ask not in off:
        return None, "ambiguous:not connected"
    return WD[(anchor[1] + off[ask]) % 7], "ok"


# ------------------------------------------------------------------ Venn counting
def venn_counting(q):
    m = _need(re.match(r"Among (\d+) people, (.+)\. Each person is counted once in each number that applies to them\. How many of the people are in (.+?)\?$", q), "venn")
    T = int(m.group(1))
    groups, inter = [], {}
    clauses = m.group(2).split("; ")
    for cl in clauses:
        a = re.fullmatch(r"(\d+) people are in the (\w+) group", cl)
        if a:
            groups.append(a.group(2))
            inter[frozenset([a.group(2)])] = int(a.group(1))
    for cl in clauses:
        if re.fullmatch(r"(\d+) people are in the (\w+) group", cl):
            continue
        b = re.fullmatch(r"(\d+) are in both the (\w+) and the (\w+) groups", cl)
        c = re.fullmatch(r"(\d+) are in all of the (.+) groups", cl)
        d = re.fullmatch(r"(\d+) are in all (?:three|four|five) groups", cl)
        if b:
            key = frozenset([b.group(2), b.group(3)])
        elif c:
            key = frozenset(_names(c.group(2)))
        elif d:
            key = frozenset(groups)
        else:
            raise ParseError("clause " + cl)
        if key in inter:
            return None, "ambiguous:intersection stated twice"
        if not key <= set(groups):
            return None, "ambiguous:unknown group"
        inter[key] = int((b or c or d).group(1))
    k = len(groups)
    subs = [frozenset(s) for r in range(1, k + 1) for s in itertools.combinations(groups, r)]
    if any(s not in inter for s in subs):
        return None, "ambiguous:an intersection is not stated"
    exact = {}
    for s in subs:
        exact[s] = sum((-1) ** (len(t) - len(s)) * inter[t] for t in subs if s <= t)
    none = T - sum(exact.values())
    if none < 0 or any(v < 0 for v in exact.values()):
        return None, "ambiguous:inconsistent counts"
    ask = m.group(3)
    if ask == "none of these groups":
        v = none
    elif ask == "exactly one of these groups":
        v = sum(x for s, x in exact.items() if len(s) == 1)
    elif ask == "exactly two of these groups":
        v = sum(x for s, x in exact.items() if len(s) == 2)
    elif ask == "exactly three of these groups":
        v = sum(x for s, x in exact.items() if len(s) == 3)
    elif ask == "at least two of these groups":
        v = sum(x for s, x in exact.items() if len(s) >= 2)
    elif ask == "at least one of these groups":
        v = sum(exact.values())
    elif ask == "all of these groups":
        v = exact[frozenset(groups)]
    else:
        raise ParseError("ask " + ask)
    return str(v), "ok"


SOLVERS = {
    "R1.boolean_lights_r4": boolean_lights,
    "R1.categories_default_exceptions_r4": categories_default_exceptions,
    "R1.compass_turns": compass_turns,
    "R1.conditional_decision_tree_r6": conditional_decision_tree,
    "R1.conditional_threshold_rule_r4": conditional_threshold_rule,
    "R1.equivalence_exchange_rates_r6": equivalence_exchange_rates,
    "R1.graph_shortest_route_r6": graph_shortest_route,
    "R1.knights_knaves_r6": knights_knaves,
    "R1.spatial_grid_walk_r5": spatial_grid_walk,
    "R1.swap_tracking_r5": swap_tracking,
    "R1.temporal_weekday_shift_r6": temporal_weekday_shift,
    "R1.venn_counting_r5": venn_counting,
}
