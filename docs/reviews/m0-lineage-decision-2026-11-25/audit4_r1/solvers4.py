# ruff: noqa
"""Audit 4 (R1): the auditor's own text-only solvers for the 27 fix-round-3 (_r5) shapes.

Each solver reads ONLY the rendered question text (never the structured form, never the key) and returns the answer string,
or raises Ambiguous(reason) when the text does not determine a unique answer. Imports nothing from studies.m0.
Algorithms are chosen to differ from the generators' where that is cheap (minute-indexed DP for meetings, up-closure
type models for syllogisms, parity union-find for two-colouring, brute force over seatings, Fractions for rates).
"""
import itertools, re
from collections import defaultdict, deque
from fractions import Fraction


class Ambiguous(Exception):
    pass


NAME = r"[A-Z][a-z]+(?:-[a-z]+)?"


def unique(vals, what="answer"):
    vals = list(vals)
    if len(vals) != 1:
        raise Ambiguous(f"{what}: {len(vals)} candidates")
    return vals[0]


def split_and(s):
    parts = s.split(", ")
    last = parts[-1].rsplit(" and ", 1)
    return [*parts[:-1], *last]


def choose(q):
    m = re.search(r"Choose from (.+?)\.\s*$", q)
    return split_and(m.group(1)) if m else None


# ---------------------------------------------------------------- activity selection: DP over minutes
def activity_selection_r5(q):
    ms = [(int(a), int(b)) for a, b in re.findall(r"meeting runs from minute (\d+) to minute (\d+)\.", q)]
    T = max(b for _, b in ms)
    by_end = defaultdict(list)
    for a, b in ms:
        by_end[b].append(a)
    best = [0] * (T + 1)
    for t in range(1, T + 1):
        best[t] = max([best[t - 1]] + [best[a] + 1 for a in by_end[t]])
    return str(best[T])


# ---------------------------------------------------------------- attribute rule: recursive descent (narrow negation scope), optional wide scope
def _tok(s):
    return re.findall(r"\(|\)|it is not true that|it is \w+|it has an? \w+|and|or", s)


def _parse_rule(toks, wide=False):
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        pos[0] += 1
        return toks[pos[0] - 1]

    def expr():
        terms = [unary()]
        ops = []
        while peek() in ("and", "or"):
            ops.append(take())
            terms.append(unary())
        if len(set(ops)) > 1:
            raise Ambiguous("mixed operators without parentheses")
        return terms[0] if not ops else [ops[0], *terms]

    def unary():
        t = take()
        if t == "(":
            e = expr()
            if take() != ")":
                raise Ambiguous("paren")
            return e
        if t == "it is not true that":
            if wide:  # the negation takes everything up to the end of the enclosing parenthesis
                return ["not", expr()]
            return ["not", unary()]
        if t.startswith("it is "):
            return ["is", t[6:]]
        if t.startswith("it has "):
            return ["has", t[7:].split()[-1]]
        raise Ambiguous(f"token {t}")

    e = expr()
    if pos[0] != len(toks):
        raise Ambiguous("trailing tokens")
    return e


def _ev(t, badge):
    k = t[0]
    if k == "is":
        return t[1] in (badge[0], badge[1])
    if k == "has":
        return t[1] == badge[2]
    if k == "not":
        return not _ev(t[1], badge)
    if k == "and":
        return all(_ev(x, badge) for x in t[1:])
    return any(_ev(x, badge) for x in t[1:])


def attribute_rule_r5(q, wide=False):
    rule = re.search(r"satisfies this rule: (.+?)\. The badges: ", q).group(1)
    tree = _parse_rule(_tok(rule), wide)
    badges = {m.group(1): (m.group(2), m.group(3), m.group(4).split()[-1]) for m in re.finditer(rf"({NAME})'s badge is (\w+), (\w+) and has (an? \w+)", q)}
    return unique([o for o, b in badges.items() if _ev(tree, b)], "badges")


# ---------------------------------------------------------------- categories: realisable membership types via up-closures
def _upclose(groups, alls):
    up = {g: {g} for g in groups}
    changed = True
    while changed:
        changed = False
        for a, b in alls:
            for g in groups:
                if a in up[g] and b not in up[g]:
                    up[g].add(b)
                    changed = True
    return up


def categories_follow_r5(q):
    """A model is a set of membership types (sets of groups). All/No restrict which types may exist; non-emptiness and Some need a type
    to exist. The cheapest type containing a set of groups is its up-closure under All; the existential constraints are satisfiable iff each
    needed up-closure is free of No pairs (realising every allowed type at once satisfies all of them together)."""
    alls = re.findall(r"All (\w+) are (\w+)\.", q)
    nos = re.findall(r"No (\w+) are (\w+)\.", q)
    somes = re.findall(r"Some (\w+) are (\w+)\.", q)
    m = re.search(r'Consider the statement: "(every|no|some) (\w+) (?:is an?|are) (\w+)"', q)
    kind, x, y = m.group(1), m.group(2), m.group(3)
    groups = sorted({g for p in alls + nos + somes for g in p} | {x, y})

    def sat(A, N):
        up = _upclose(groups, A)
        bad = lambda s: any(a in s and b in s for a, b in N)  # noqa: E731
        return all(not bad(up[g]) for g in groups) and all(not bad(up[a] | up[b]) for a, b in somes)

    if not sat(alls, nos):
        raise Ambiguous("premises inconsistent")
    up = _upclose(groups, alls)
    bad = lambda s: any(a in s and b in s for a, b in nos)  # noqa: E731
    if kind == "every":
        can_true = sat(alls + [(x, y)], nos)
        can_false = y not in up[x]  # a type = up-closure of {x} (allowed, since x is non-empty) lacking y can be realised
    elif kind == "no":
        can_true = sat(alls, nos + [(x, y)])
        can_false = not bad(up[x] | up[y])
    else:
        can_true = not bad(up[x] | up[y])
        can_false = sat(alls, nos + [(x, y)])
    if can_true and can_false:
        return "cannot be determined"
    if can_true:
        return "yes"
    if can_false:
        return "no"
    raise Ambiguous("neither")


# ---------------------------------------------------------------- conditional chain: brute force over assignments
def conditional_chain_r5(q):
    facts = re.findall(r"(?:^|(?<=\. ))([A-Z]) is (true|false)\.", q)  # audit-4 fix 1: the earlier pattern consumed ". " and skipped consecutive facts
    rules = re.findall(r"If ([^,]+), then ([A-Z]) is (true|false)\.", q)
    qv = re.search(r"Is ([A-Z]) true\?", q).group(1)
    vs = sorted({v for v, _ in facts} | {c for _, c, _ in rules} | {qv} | {v for a, _, _ in rules for v in re.findall(r"\b([A-Z]) is", a)})
    R = [([(v, b == "true") for v, b in re.findall(r"([A-Z]) is (true|false)", a)], c, cb == "true") for a, c, cb in rules]
    F = [(v, b == "true") for v, b in facts]
    seen = set()
    for bits in itertools.product((False, True), repeat=len(vs)):
        w = dict(zip(vs, bits))
        if any(w[v] != b for v, b in F):
            continue
        if any(all(w[v] == b for v, b in a) and w[c] != cb for a, c, cb in R):
            continue
        seen.add(w[qv])
        if len(seen) == 2:
            return "cannot be determined"
    if not seen:
        raise Ambiguous("no model")
    return "yes" if True in seen else "no"


# ---------------------------------------------------------------- queue
def containers_queue_line_r5(q):
    line = deque(split_and(re.search(r"A line, from front to back, is: (.+?)\. ", q).group(1)))
    st = re.search(r"A line, from front to back, is: .+?\. ", q).end()
    body = q[st : q.index(" Who is in position")]
    for s in re.split(r"(?<=\.) ", body):
        if m := re.fullmatch(rf"({NAME}) joins at the back\.", s):
            line.append(m.group(1))
        elif m := re.fullmatch(rf"({NAME}) is let in at the very front\.", s):
            line.appendleft(m.group(1))
        elif s == "The person at the front is served and leaves.":
            line.popleft()
        elif m := re.fullmatch(rf"({NAME}) gets tired and leaves\.", s):
            line.remove(m.group(1))
        elif s == "The person at the front goes to the back of the line.":
            line.rotate(-1)
        else:
            raise Ambiguous(f"op {s}")
    j = int(re.search(r"Who is in position (\d+)", q).group(1))
    return line[j - 1]


# ---------------------------------------------------------------- bracket
def elimination_bracket_r5(q):
    players = re.search(r"listed in bracket order: (.+?)\. In round one", q).group(1).split(", ")
    beat = set(re.findall(rf"({NAME}) beat ({NAME})\.", q))
    rnd = players
    final_loser = None
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2]):
            if (a, b) in beat and (b, a) not in beat:
                w, l = a, b
            elif (b, a) in beat and (a, b) not in beat:
                w, l = b, a
            else:
                raise Ambiguous("no result")
            nxt.append(w)
            if len(rnd) == 2:
                final_loser = l
        rnd = nxt
    if "Who wins the tournament?" in q:
        return rnd[0]
    if "Who loses the final?" in q:
        return final_loser
    raise Ambiguous("question kind")


# ---------------------------------------------------------------- equivalence classes
def equivalence_classes_r5(q):
    same = re.findall(r"(\w+) is the same thing as (\w+)\.", q)
    diff = re.findall(r"(\w+) is a different thing from (\w+)\.", q)
    x, y = re.search(r"Is (\w+) the same thing as (\w+)\? Answer", q).groups()
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


# ---------------------------------------------------------------- exchange rates (Fractions)
def equivalence_exchange_rates_r5(q):
    rates = re.findall(r"(\d+) units of ([\w -]+?) are worth the same as (\d+) units of ([\w -]+?)\.", q)
    m = re.search(r"How many units of ([\w -]+?) are worth the same as (\d+) units of ([\w -]+?)\?", q)
    y, nn, x = m.group(1), int(m.group(2)), m.group(3)
    adj = defaultdict(list)
    for p, a, qq, b in rates:  # p a = qq b  ->  value(a) = qq/p value(b)
        adj[a].append((b, Fraction(int(qq), int(p))))
        adj[b].append((a, Fraction(int(p), int(qq))))
    val = {x: Fraction(1)}
    dq = deque([x])
    while dq:
        u = dq.popleft()
        for v, r in adj[u]:  # value(u) = r value(v)  ->  value(v) = value(u) / r
            nv = val[u] / r
            if v in val:
                if val[v] != nv:
                    raise Ambiguous("inconsistent")
            else:
                val[v] = nv
                dq.append(v)
    if y not in val:
        raise Ambiguous("unconnected")
    ans = nn * val[x] / val[y]
    if ans.denominator != 1:
        raise Ambiguous("not whole")
    return str(ans.numerator)


# ---------------------------------------------------------------- event timeline / weekday (potential propagation)
def _dated(q):
    out = []
    for s in re.split(r"(?<=\.) ", q):
        if m := re.fullmatch(r"(.+?) took place (\d+) days? (after|before) (.+?)\.", s):
            a, d, rel, b = m.group(1).lower(), int(m.group(2)), m.group(3), m.group(4).lower()
            out.append((a, b, d if rel == "after" else -d))  # date(a) = date(b) + signed d
    return out


def _potentials(rels, root):
    adj = defaultdict(list)
    for a, b, d in rels:
        adj[b].append((a, d))
        adj[a].append((b, -d))
    pot = {root: 0}
    dq = deque([root])
    while dq:
        u = dq.popleft()
        for v, d in adj[u]:
            if v in pot:
                if pot[v] != pot[u] + d:
                    raise Ambiguous("inconsistent")
            else:
                pot[v] = pot[u] + d
                dq.append(v)
    return pot


def event_timeline_r5(q):
    m = re.search(r"How many days apart did (.+?) and (.+?) take place\?", q)
    x, y = m.group(1).lower(), m.group(2).lower()
    pot = _potentials(_dated(q), x)
    if y not in pot:
        raise Ambiguous("unconnected")
    return str(abs(pot[y]))


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def temporal_weekday_shift_r5(q):
    m = re.match(r"(.+?) took place on a (\w+)\. ", q)
    anc, wd = m.group(1).lower(), DAYS.index(m.group(2))
    ask = re.search(r"On which day of the week did (.+?) take place\?", q).group(1).lower()
    pot = _potentials(_dated(q[m.end():]), anc)
    if ask not in pot:
        raise Ambiguous("unconnected")
    return DAYS[(wd + pot[ask]) % 7]


# ---------------------------------------------------------------- relative directions (street distance)
def spatial_relative_directions_r5(q):
    st = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    adj = defaultdict(list)
    for p, k, d, o in re.findall(rf"({NAME}) is (\d+) blocks? (north|south|east|west) of ({NAME})\.", q):
        v = (st[d][0] * int(k), st[d][1] * int(k))
        adj[o].append((p, v))
        adj[p].append((o, (-v[0], -v[1])))
    x, y = re.search(rf"How far apart are ({NAME}) and ({NAME}) by street distance", q).groups()
    pos = {x: (0, 0)}
    dq = deque([x])
    while dq:
        u = dq.popleft()
        for v, (dx, dy) in adj[u]:
            nv = (pos[u][0] + dx, pos[u][1] + dy)
            if v in pos:
                if pos[v] != nv:
                    raise Ambiguous("inconsistent")
            else:
                pos[v] = nv
                dq.append(v)
    if y not in pos:
        raise Ambiguous("unconnected")
    return str(abs(pos[y][0]) + abs(pos[y][1]))


# ---------------------------------------------------------------- bipartite: parity union-find
def graph_bipartite_r5(q):
    pairs = re.findall(rf"({NAME}) and ({NAME}) are rivals\.", q)
    par, rel = {}, {}

    def f(a):
        par.setdefault(a, a)
        rel.setdefault(a, 0)
        if par[a] == a:
            return a, 0
        r, p = f(par[a])
        par[a] = r
        rel[a] ^= p
        return r, rel[a]

    for a, b in pairs:
        (ra, pa), (rb, pb) = f(a), f(b)
        if ra == rb:
            if pa == pb:
                return "no"
        else:
            par[ra] = rb
            rel[ra] = pa ^ pb ^ 1
    return "yes"


# ---------------------------------------------------------------- kinship
def _parents(q):
    return {c: p for p, c in re.findall(rf"({NAME}) is the parent of ({NAME})\.", q)}


def kinship_cousins_r5(q):
    par = _parents(q)
    x, y = re.search(rf"Are ({NAME}) and ({NAME}) cousins\?", q).groups()
    px, py = par.get(x), par.get(y)
    if px is None or py is None or px == py:
        return "no"
    gx, gy = par.get(px), par.get(py)
    return "yes" if gx is not None and gx == gy else "no"


def kinship_descendants_r5(q):
    par = _parents(q)
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)

    def size(p):
        return sum(1 + size(c) for c in kids[p])

    x = re.search(rf"Among the children of ({NAME}), who has the most descendants", q).group(1)
    cands = choose(q)
    if sorted(cands) != sorted(kids[x]):
        raise Ambiguous("candidates are not the children")
    sc = {c: size(c) for c in cands}
    top = max(sc.values())
    return unique([c for c in cands if sc[c] == top], "most descendants")


# ---------------------------------------------------------------- knights and knaves: enumerate
def knights_knaves_r5(q):
    says = re.findall(rf'({NAME}) says: "(.+?)\."', q)
    ppl = [p for p, _ in says]
    who = re.search(rf"Is ({NAME}) a knight or a knave\?", q).group(1)
    allp = sorted(set(ppl) | {who} | {w for _, s in says for w in re.findall(NAME, s)})

    def truth(s, w):
        if m := re.fullmatch(rf"({NAME}) is a knight", s):
            return w[m.group(1)]
        if m := re.fullmatch(rf"({NAME}) is a knave", s):
            return not w[m.group(1)]
        if m := re.fullmatch(rf"({NAME}) and ({NAME}) are both knights", s):
            return w[m.group(1)] and w[m.group(2)]
        if m := re.fullmatch(rf"at least one of ({NAME}) and ({NAME}) is a knave", s):
            return not (w[m.group(1)] and w[m.group(2)])
        if m := re.fullmatch(rf"({NAME}) and ({NAME}) are of the same kind", s):
            return w[m.group(1)] == w[m.group(2)]
        if m := re.fullmatch(rf"exactly one of ({NAME}) and ({NAME}) is a knight", s):
            return w[m.group(1)] != w[m.group(2)]
        raise Ambiguous(f"statement {s}")

    vals = set()
    nsol = 0
    for bits in itertools.product((True, False), repeat=len(allp)):
        w = dict(zip(allp, bits))
        if all(truth(s, w) == w[p] for p, s in says):
            nsol += 1
            vals.add(w[who])
    if len(vals) != 1:
        raise Ambiguous(f"{nsol} solutions, asked person not fixed")
    return "knight" if vals.pop() else "knave"


# ---------------------------------------------------------------- minimax
def _nested(s):
    toks = re.findall(r"\(|\)|-?\d+|or", s)
    pos = [0]

    def node():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            ch = [node()]
            while toks[pos[0]] == "or":
                pos[0] += 1
                ch.append(node())
            assert toks[pos[0]] == ")"
            pos[0] += 1
            return ch
        return int(t)

    return node()


def minimax_tree_r5(q):
    tree = _nested(re.search(r"written as nested options: (.+?)\. When the options", q).group(1))
    first = re.search(r"(Max|Min) choosing first", q).group(1)

    def v(t, mx):
        if isinstance(t, int):
            return t
        vals = [v(c, not mx) for c in t]
        return max(vals) if mx else min(vals)

    return str(v(tree, first == "Max"))


# ---------------------------------------------------------------- nim
def nim_xor_r5(q):
    piles = [int(x) for x in re.search(r"piles of stones: ([\d, ]+)\.", q).group(1).split(", ")]
    x = 0
    for p in piles:
        x ^= p
    return "first" if x else "second"


# ---------------------------------------------------------------- order compare: transitive closure (Warshall)
def order_compare_r5(q):
    facts = re.findall(rf"({NAME}) is taller than ({NAME})\.", q)
    x, y = re.search(rf"Is ({NAME}) taller than ({NAME})\? Answer", q).groups()
    ppl = sorted({p for f in facts for p in f} | {x, y})
    ix = {p: i for i, p in enumerate(ppl)}
    n = len(ppl)
    R = [[False] * n for _ in range(n)]
    for a, b in facts:
        R[ix[a]][ix[b]] = True
    for k in range(n):
        for i in range(n):
            if R[i][k]:
                for j in range(n):
                    if R[k][j]:
                        R[i][j] = True
    if any(R[i][i] for i in range(n)):
        raise Ambiguous("cycle")
    if R[ix[x]][ix[y]]:
        return "yes"
    if R[ix[y]][ix[x]]:
        return "no"
    return "cannot be determined"


# ---------------------------------------------------------------- roads
def road_reachability_r5(q):
    roads = re.findall(r"one-way road from (\w+) to (\w+)\.", q)
    x, y = re.search(r"Can you travel from (\w+) to (\w+) using", q).groups()
    adj = defaultdict(list)
    for a, b in roads:
        adj[a].append(b)
    seen, dq = {x}, deque([x])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                dq.append(v)
    return "yes" if y in seen else "no"


# ---------------------------------------------------------------- seating: brute force over seatings
def seating_row_r5(q):
    m = re.match(r"(.+?) sit in a row of (\d+) seats", q)
    ppl, n = split_and(m.group(1)), int(m.group(2))
    seat = int(re.search(r"Who sits in seat (\d+)\?", q).group(1)) - 1
    cl = []
    for s in re.split(r"(?<=\.) ", q):
        if mm := re.fullmatch(rf"({NAME}) sits immediately to the left of ({NAME})\.", s):
            a, b = mm.groups(); cl.append(lambda P, a=a, b=b: P[b] == P[a] + 1)
        elif mm := re.fullmatch(rf"({NAME}) sits somewhere to the left of ({NAME})\.", s):
            a, b = mm.groups(); cl.append(lambda P, a=a, b=b: P[a] < P[b])
        elif mm := re.fullmatch(rf"({NAME}) sits at one of the two ends of the row\.", s):
            a = mm.group(1); cl.append(lambda P, a=a: P[a] in (0, n - 1))
        elif mm := re.fullmatch(rf"({NAME}) sits in seat (\d+)\.", s):
            a, k = mm.group(1), int(mm.group(2)) - 1; cl.append(lambda P, a=a, k=k: P[a] == k)
        elif mm := re.fullmatch(rf"({NAME}) sits somewhere between ({NAME}) and ({NAME})\.", s):
            b, a, c = mm.groups(); cl.append(lambda P, a=a, b=b, c=c: min(P[a], P[c]) < P[b] < max(P[a], P[c]))
        elif mm := re.fullmatch(rf"({NAME}) and ({NAME}) do not sit next to each other\.", s):
            a, b = mm.groups(); cl.append(lambda P, a=a, b=b: abs(P[a] - P[b]) != 1)
    occ = set()
    for perm in itertools.permutations(range(n)):
        P = dict(zip(ppl, perm))
        if all(c(P) for c in cl):
            occ.add(next(p for p in ppl if P[p] == seat))
    return unique(occ, "seat occupants")


# ---------------------------------------------------------------- grid walk
def spatial_grid_walk_r5(q):
    rows = re.findall(r"Row \d+: ([^.]+)\.", q)
    grid = [r.split(", ") for r in rows]
    start = re.search(r"You start at (\w+)\.", q).group(1)
    moves = re.search(r"You move (.+?), one cell each time\.", q).group(1).split(", then ")
    pos = next((i, j) for i, r in enumerate(grid) for j, c in enumerate(r) if c == start)
    d = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    for mv in moves:
        i, j = pos[0] + d[mv][0], pos[1] + d[mv][1]
        if 0 <= i < len(grid) and 0 <= j < len(grid[0]) and grid[i][j] != "wall":
            pos = (i, j)
    return grid[pos[0]][pos[1]]


# ---------------------------------------------------------------- swaps
def swap_tracking_r5(q):
    head = re.match(r"At the start (.+?)\. ", q)
    hold = dict(re.findall(rf"({NAME}) holds the ([\w-]+)", head.group(1)))
    body = q[head.end():]
    for s in re.split(r"(?<=\.) ", body):
        if m := re.fullmatch(rf"({NAME}) and ({NAME}) swap what they are holding\.", s):
            a, b = m.groups(); hold[a], hold[b] = hold[b], hold[a]
        elif m := re.fullmatch(rf"({NAME}) hands their item to ({NAME}), ({NAME}) hands theirs to ({NAME}), and ({NAME}) hands theirs to ({NAME}), all at once\.", s):
            a, b, b2, c, c2, a2 = m.groups()
            if not (b == b2 and c == c2 and a == a2):
                raise Ambiguous("rotation text")
            hold[a], hold[b], hold[c] = hold[c], hold[a], hold[b]
    who = re.search(rf"What is ({NAME}) holding at the end\?", q).group(1)
    return hold[who]


# ---------------------------------------------------------------- critical path (day convention as stated)
def temporal_critical_path_r5(q):
    jobs = {}
    for p, d, rest in re.findall(rf"({NAME})'s job takes (\d+) days? and (waits for nobody|waits for the jobs of [^.]+)\.", q):
        jobs[p] = (int(d), [] if rest == "waits for nobody" else split_and(rest[len("waits for the jobs of "):]))
    end = {}

    def fin(p):
        if p not in end:
            d, deps = jobs[p]
            s = 1 if not deps else max(fin(x) for x in deps) + 1  # the day after the last one's final day
            end[p] = s + d - 1  # final day of a d-day job that starts on day s
        return end[p]

    return str(max(fin(p) for p in jobs))  # from the beginning of day 1 to the end of that day


# ---------------------------------------------------------------- interval overlap
def temporal_interval_overlap_r5(q):
    iv = {}
    for s in re.split(r"(?<=\.) (?=[A-Z])", q):
        if m := re.fullmatch(r"(.+?) ran from day (\d+) to day (\d+), both days included\.", s):
            iv[m.group(1).lower()] = (int(m.group(2)), int(m.group(3)))
        elif m := re.fullmatch(r"(.+?) started on day (\d+) and went on for (\d+) days? \(day \d+ counts as the first\)\.", s):
            a = int(m.group(2)); iv[m.group(1).lower()] = (a, a + int(m.group(3)) - 1)
    x, y = re.search(r"Did (.+?) and (.+?) overlap, that is", q).groups()
    (a1, b1), (a2, b2) = iv[x.lower()], iv[y.lower()]
    return "yes" if any(a2 <= d <= b2 for d in range(a1, b1 + 1)) else "no"


# ---------------------------------------------------------------- topological order: day by day
def topological_order_r5(q):
    deps = {}
    for s in re.split(r"(?<=\.) ", q):
        if m := re.fullmatch(rf"({NAME}) has no prerequisite\.", s):
            deps[m.group(1)] = set()
        elif m := re.fullmatch(rf"({NAME}) needs (.+?) to be done first\.", s):
            deps[m.group(1)] = set(split_and(m.group(2)))
    day = int(re.search(r"Which job is done on day (\d+)\?", q).group(1))
    done = []
    while len(done) < len(deps):
        avail = sorted(p for p in deps if p not in done and deps[p] <= set(done))
        if not avail:
            raise Ambiguous("cycle")
        done.append(avail[0])
    return done[day - 1]


# ---------------------------------------------------------------- accounts
def tracking_accounts_r5(q):
    head = re.match(r"At the start (.+?)\. ", q)
    bal = {p: int(v) for p, v in re.findall(rf"({NAME}) has (\d+) dollars?", head.group(1))}
    for s in re.split(r"(?<=\.) ", q[head.end():]):
        if m := re.fullmatch(rf"({NAME}) pays ({NAME}) (\d+) dollars?\.", s):
            a, b, v = m.group(1), m.group(2), int(m.group(3))
            if bal[a] < v:
                raise Ambiguous("overdraft")
            bal[a] -= v; bal[b] += v
        elif m := re.fullmatch(rf"({NAME}) earns (\d+) dollars?\.", s):
            bal[m.group(1)] += int(m.group(2))
        elif m := re.fullmatch(rf"({NAME}) gives half of their money to ({NAME})\.", s):
            a, b = m.groups()
            if bal[a] % 2:
                raise Ambiguous("odd half")
            h = bal[a] // 2; bal[a] -= h; bal[b] += h
    who = re.search(rf"How many dollars does ({NAME}) have at the end\?", q).group(1)
    return str(bal[who])


# ---------------------------------------------------------------- venn: regions by Moebius inversion over the stated intersections
def venn_counting_r5(q):
    total = int(re.match(r"Among (\d+) people", q).group(1))
    groups = re.findall(r"(\d+) people are in the (\w+) group", q)
    G = [g for _, g in groups]
    inter = {frozenset([g]): int(v) for v, g in groups}
    for v, a, b in re.findall(r"(\d+) are in both the (\w+) and the (\w+) groups", q):
        inter[frozenset([a, b])] = int(v)
    for v, lst in re.findall(r"(\d+) are in all of the ([\w, ]+?) groups", q):
        inter[frozenset(split_and(lst))] = int(v)
    if m := re.search(r"(\d+) are in all four groups", q):
        inter[frozenset(G)] = int(m.group(1))
    subsets = [frozenset(c) for k in range(1, len(G) + 1) for c in itertools.combinations(G, k)]
    for s in subsets:
        if s not in inter:
            raise Ambiguous(f"missing intersection {sorted(s)}")
    ex = {s: sum((-1) ** (len(t) - len(s)) * inter[t] for t in subsets if s <= t) for s in subsets}
    if any(v < 0 for v in ex.values()):
        raise Ambiguous("negative region")
    none = total - sum(ex.values())
    what = re.search(r"How many of the people are in (none|exactly one|exactly two|at least two) of these groups\?", q).group(1)
    val = {"none": none, "exactly one": sum(v for s, v in ex.items() if len(s) == 1), "exactly two": sum(v for s, v in ex.items() if len(s) == 2),
           "at least two": sum(v for s, v in ex.items() if len(s) >= 2)}[what]
    return str(val)


SOLVERS = {f"R1.{n}": f for n, f in list(globals().items()) if n.endswith("_r5") and callable(f)}
