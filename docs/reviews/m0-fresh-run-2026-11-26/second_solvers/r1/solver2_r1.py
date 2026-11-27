"""Second solvers for the R1 lineages (M0, ADR-0033 addendum 1, section 8 item 1).

Written by an auditor context from the answer-free fixtures, SCHEMA.md files and
question texts only. Standard library only. Each solver computes from
`structured`; where a reading of the question text matters it is noted.
A solver raises AmbiguousItem when the item does not determine a unique
answer under the reading implemented (these are reported, never guessed).
"""
from fractions import Fraction
from itertools import combinations, product


class AmbiguousItem(Exception):
    pass


def _yn(b):
    return "yes" if b else "no"


# --- boolean_lights_r4 -------------------------------------------------------
def boolean_lights(question, s):
    state = list(s["initial"])
    if len(state) != s["lamps"]:
        raise AmbiguousItem("initial length != lamps")
    for colour in s["presses"]:
        for lamp in s["switches"][colour]:
            state[lamp - 1] ^= 1
    return _yn(state[s["ask"] - 1] == 1)


# --- categories_default_exceptions_r4 ----------------------------------------
def categories(question, s):
    verb = s["verb"]
    for group in s["chain"]:
        vals = {can for g, v, can in s["rules"] if g == group and v == verb}
        if len(vals) > 1:
            raise AmbiguousItem(f"conflicting rules for {group}/{verb}")
        if vals:
            return _yn(vals.pop())
    raise AmbiguousItem(f"no rule about {verb} on the chain")


# --- compass_turns -----------------------------------------------------------
_DIRS = ["north", "east", "south", "west"]


def _turn_deg(t):
    if t == "left":
        return -90
    if t == "right":
        return 90
    if t == "around":
        return 180
    if t.startswith("ccw"):
        return -int(t[3:])
    if t.startswith("cw"):
        return int(t[2:])
    raise AmbiguousItem(f"unknown turn {t}")


def compass(question, s):
    deg = _DIRS.index(s["start"]) * 90
    for kind, arg in s["seq"]:
        if kind == "turn":
            deg += _turn_deg(arg)
        elif kind != "walk":
            raise AmbiguousItem(f"unknown step {kind}")
    if deg % 90:
        raise AmbiguousItem("not a multiple of 90")
    return _DIRS[(deg // 90) % 4]


# --- conditional_threshold_rule_r4 -------------------------------------------
def threshold(question, s):
    w = dict((n, x) for n, x in s["members"])
    net = 0
    for name, vote in s["votes"].items():
        if vote == "yes":
            net += w[name]
        elif vote == "no":
            net -= w[name]
        elif vote != "abstain":
            raise AmbiguousItem(f"unknown vote {vote}")
    return _yn(net >= s["margin"])


# --- equivalence_exchange_rates_r6 -------------------------------------------
def exchange(question, s):
    # value[item] in units of x: p units of a == q units of b -> val(a)*p == val(b)*q
    val = {s["x"]: Fraction(1)}
    changed = True
    while changed:
        changed = False
        for p, a, q, b in s["rates"]:
            if a in val and b not in val:
                val[b] = val[a] * p / q
                changed = True
            elif b in val and a not in val:
                val[a] = val[b] * q / p
                changed = True
            elif a in val and b in val and val[a] * p != val[b] * q:
                raise AmbiguousItem("inconsistent rates")
    if s["y"] not in val:
        raise AmbiguousItem("y not connected to x")
    ans = Fraction(s["n"]) * val[s["x"]] / val[s["y"]]
    if ans.denominator != 1 or ans <= 0:
        raise AmbiguousItem(f"non positive-integer answer {ans}")
    return str(ans.numerator)


# --- knights_knaves_r6 -------------------------------------------------------
def _stmt(kind, idx, k):
    if kind == "is_knight":
        return k[idx[0]]
    if kind == "is_knave":
        return not k[idx[0]]
    if kind == "both_knights":
        return k[idx[0]] and k[idx[1]]
    if kind == "some_knave":
        return (not k[idx[0]]) or (not k[idx[1]])
    if kind == "same_kind":
        return k[idx[0]] == k[idx[1]]
    if kind == "differ":
        return k[idx[0]] != k[idx[1]]
    raise AmbiguousItem(f"unknown kind {kind}")


def knights(question, s):
    n = len(s["people"])
    found = set()
    for k in product((True, False), repeat=n):
        if all(k[i] == _stmt(kind, idx, k) for i, (kind, idx) in enumerate(s["statements"])):
            found.add(k[s["who"]])
    if len(found) != 1:
        raise AmbiguousItem(f"asked person's kind not determined: {found}")
    return "knight" if found.pop() else "knave"


# --- spatial_grid_walk_r5 ----------------------------------------------------
_STEP = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}


def grid_walk(question, s):
    if s["convention"] != "row 1 is the northernmost, column 1 is the westernmost":
        raise AmbiguousItem(f"unknown convention {s['convention']}")
    g = s["grid"]
    r, c = s["start"]
    if g[r][c] is None:
        raise AmbiguousItem("start on wall")
    for m in s["moves"]:
        dr, dc = _STEP[m]
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(g) and 0 <= nc < len(g[nr]) and g[nr][nc] is not None:
            r, c = nr, nc
    return g[r][c]


# --- swap_tracking_r5 --------------------------------------------------------
def swap_tracking(question, s):
    h = dict(s["hold"])
    for op in s["ops"]:
        if op[0] == "swap":
            _, a, b = op
            h[a], h[b] = h[b], h[a]
        elif op[0] == "rotate":
            # "a hands their item to b, b hands theirs to c, and c hands theirs to a, all at once"
            _, a, b, c = op
            h[a], h[b], h[c] = h[c], h[a], h[b]
        else:
            raise AmbiguousItem(f"unknown op {op[0]}")
    return h[s["who"]]


# --- temporal_weekday_shift_r6 -----------------------------------------------
def weekday(question, s):
    ev, day = s["anchor"]
    days = s["days"]
    off = {ev: 0}
    changed = True
    while changed:
        changed = False
        for later, earlier, n in s["links"]:
            if earlier in off and later not in off:
                off[later] = off[earlier] + n
                changed = True
            elif later in off and earlier not in off:
                off[earlier] = off[later] - n
                changed = True
            elif later in off and earlier in off and off[later] - off[earlier] != n:
                raise AmbiguousItem("inconsistent links")
    if s["ask"] not in off:
        raise AmbiguousItem("asked event not connected")
    return days[(days.index(day) + off[s["ask"]]) % 7]


# --- venn_counting_r5 --------------------------------------------------------
def venn(question, s):
    groups = s["groups"]
    m = len(groups)

    def inter(sub):
        if len(sub) == 0:
            return s["total"]
        if len(sub) == 1:
            return s["sizes"][sub[0]]
        if len(sub) == 2:
            return s["pairs"]["|".join(sub)]
        if len(sub) == 3:
            return s["triples"]["|".join(sub)]
        if len(sub) == 4:
            return s["quad"]
        raise AmbiguousItem("more than four groups")

    # exact region counts by inclusion-exclusion (Moebius inversion)
    exact = {}
    for k in range(m + 1):
        for sub in combinations(groups, k):
            tot = 0
            rest = [g for g in groups if g not in sub]
            for j in range(len(rest) + 1):
                for extra in combinations(rest, j):
                    full = tuple(g for g in groups if g in sub or g in extra)
                    tot += (-1) ** j * inter(full)
            if tot < 0:
                raise AmbiguousItem(f"negative region {sub}: {tot}")
            exact[sub] = tot
    by_k = [sum(v for sub, v in exact.items() if len(sub) == k) for k in range(m + 1)]
    ask = s["ask"]
    if ask == "none":
        return str(by_k[0])
    if ask == "one":
        return str(by_k[1])
    if ask == "two":
        return str(by_k[2])
    if ask == "atleast_two":
        return str(sum(by_k[2:]))
    raise AmbiguousItem(f"unknown ask {ask}")


SOLVERS = {
    "R1.boolean_lights_r4": boolean_lights,
    "R1.categories_default_exceptions_r4": categories,
    "R1.compass_turns": compass,
    "R1.conditional_threshold_rule_r4": threshold,
    "R1.equivalence_exchange_rates_r6": exchange,
    "R1.knights_knaves_r6": knights,
    "R1.spatial_grid_walk_r5": grid_walk,
    "R1.swap_tracking_r5": swap_tracking,
    "R1.temporal_weekday_shift_r6": weekday,
    "R1.venn_counting_r5": venn,
}
