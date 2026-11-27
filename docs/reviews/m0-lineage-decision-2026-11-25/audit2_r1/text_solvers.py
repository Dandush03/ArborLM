# ruff: noqa
"""Auditor's independent solvers. Each reads ONLY the rendered question text (never `s`, never `a`, never generator code paths)
and returns (answer, notes) where notes lists any ambiguity found (ties, alternative readings that change the answer).
Usage: text_solvers.py ITEMSDIR [MODE]  (MODE default reg). Prints per-lineage agreement and every mismatch/ambiguity id."""
import gzip
import itertools
import json
import os
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache


def names_list(s):
    s = s.strip().rstrip(".")
    parts = s.split(", ")
    last = parts[-1].split(" and ")
    return [*parts[:-1], *last]


def sents(q):
    return [x for x in re.split(r"(?<=[.?!])\s+", q) if x]


# ---------- new 8 ----------
def topo(q):
    jobs = {}
    for s in sents(q):
        m = re.fullmatch(r"(\w+) has no prerequisite\.", s)
        if m:
            jobs[m.group(1)] = set()
        m = re.fullmatch(r"(\w+) needs (.+) to be done first\.", s)
        if m:
            jobs[m.group(1)] = set(names_list(m.group(2)))
    n = int(re.search(r"There are (\d+) jobs", q).group(1))
    assert len(jobs) == n, (len(jobs), n)
    j = int(re.search(r"done on day (\d+)\?", q).group(1))
    done = []
    while len(done) < n:
        avail = sorted(p for p, d in jobs.items() if p not in done and d <= set(done))
        if not avail:
            return None, ["cycle"]
        done.append(avail[0])
    return done[j - 1], []


def activity(q):
    ms = [(int(a), int(b)) for _, a, b in re.findall(r"(\w+)'s meeting runs from minute (\d+) to minute (\d+)\.", q)]
    ms.sort(key=lambda x: x[1])
    # DP over intervals sorted by end: best[i] = max(best[i-1], 1 + best[last j with end <= start_i])
    best = [0] * (len(ms) + 1)
    for i, (s, e) in enumerate(ms, 1):
        k = 0
        for j in range(i - 1, 0, -1):
            if ms[j - 1][1] <= s:
                k = j
                break
        best[i] = max(best[i - 1], 1 + best[k])
    # alternative reading: touching meetings overlap (strict)
    best2 = [0] * (len(ms) + 1)
    for i, (s, e) in enumerate(ms, 1):
        k = 0
        for j in range(i - 1, 0, -1):
            if ms[j - 1][1] < s:
                k = j
                break
        best2[i] = max(best2[i - 1], 1 + best2[k])
    notes = ["touch_convention_matters"] if best2[-1] != best[-1] else []
    return str(best[-1]), notes


def mst(q):
    rs = [(a, b, int(w)) for a, b, w in re.findall(r"A road between (\w+) and (\w+) could be built with length (\d+)\.", q)]
    towns = sorted({x for a, b, _ in rs for x in (a, b)})
    # Prim from the alphabetically first town
    inside = {towns[0]}
    tot = 0
    while len(inside) < len(towns):
        cand = [(w, a, b) for a, b, w in rs if (a in inside) != (b in inside)]
        if not cand:
            return None, ["disconnected"]
        w, a, b = min(cand)
        inside |= {a, b}
        tot += w
    return str(tot), []


def irv(q):
    cands = names_list(re.search(r"^(.+?) are candidates\.", q).group(1))
    ballots = [(int(c), r.split(" > ")) for c, r in re.findall(r"(\d+) voters? rank them (.+?) \(best first\)\.", q)]
    alive = list(cands)
    notes = []
    while len(alive) > 1:
        t = {a: 0 for a in alive}
        for c, rk in ballots:
            t[next(x for x in rk if x in alive)] += c
        lo = min(t.values())
        out = [a for a in alive if t[a] == lo]
        if len(out) > 1:
            notes.append("tie_at_elimination")
        alive.remove(sorted(out)[0])
    return alive[0], notes


def stable(q):
    prefs = {p: l.split(", ") for p, l in re.findall(r"(\w+) would like, from best to worst: (.+?)\.(?= |$)", q)}
    props = names_list(re.search(r"a person from (.+?) who has no partner asks", q).group(1))
    recv = names_list(re.search(r"Choose from (.+?)\.$", q).group(1))
    ask = re.search(r"Who is (\w+)'s partner at the end\?", q).group(1)
    # proposals processed LAST-IN-FIRST-OUT (different order from the generator)
    nxt = {p: 0 for p in props}
    held = {}
    free = list(props)
    while free:
        p = free.pop()
        r = prefs[p][nxt[p]]
        nxt[p] += 1
        if r not in held:
            held[r] = p
        elif prefs[r].index(p) < prefs[r].index(held[r]):
            free.append(held[r])
            held[r] = p
        else:
            free.append(p)
    match = {p: r for r, p in held.items()}
    # stability check
    notes = []
    for p in props:
        for r in prefs[p][: prefs[p].index(match[p])]:
            if prefs[r].index(p) < prefs[r].index(held[r]):
                notes.append("unstable")
    return match[ask], notes


@lru_cache(maxsize=None)
def _win(state):
    for i, h in enumerate(state):
        for take in range(1, h + 1):
            ns = list(state)
            ns[i] -= take
            ns = tuple(sorted(x for x in ns if x))
            if not _win(ns):
                return True
    return False


def nim(q):
    piles = [int(x) for x in re.search(r"piles of stones: ([\d, ]+)\.", q).group(1).split(", ")]
    if len(piles) <= 4 and max(piles) <= 40:
        w = _win(tuple(sorted(piles)))
        how = []
    else:
        x = 0
        for p in piles:
            x ^= p
        w = x != 0
        how = ["bouton_used_not_bruteforce"]
    return ("first" if w else "second"), how


def minimax(q):
    depth = int(re.search(r"a game with (\d+) choices in a row", q).group(1))
    expr = re.search(r"nested options: (.+?)\. When the options", q).group(1)
    toks = re.findall(r"\(|\)|or|-?\d+", expr)
    pos = 0

    def parse():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            kids = [parse()]
            while toks[pos] == "or":
                pos += 1
                kids.append(parse())
            assert toks[pos] == ")"
            pos += 1
            return kids
        pos += 1
        return int(t)

    tree = parse()

    def depth_of(t):
        return 0 if isinstance(t, int) else 1 + max(depth_of(c) for c in t)

    notes = [] if depth_of(tree) == depth else ["depth_mismatch"]

    def val(t, mx):
        if isinstance(t, int):
            return t
        v = [val(c, not mx) for c in t]
        return max(v) if mx else min(v)

    return str(val(tree, True)), notes


def venn(q):
    total = int(re.search(r"^Among (\d+) people", q).group(1))
    sizes = {g: int(n) for n, g in re.findall(r"(\d+) people are in the (\w+) group", q)}
    pairs = {frozenset((a, b)): int(n) for n, a, b in re.findall(r"(\d+) are in both the (\w+) and the (\w+) groups", q)}
    m = re.search(r"(\d+) are in all three groups", q)
    triple = int(m.group(1)) if m else 0
    union = sum(sizes.values()) - sum(pairs.values()) + triple
    # brute-force check that a non-negative region assignment exists (consistency)
    gs = sorted(sizes)
    notes = []
    if len(gs) == 3:
        ab, ac, bc = (pairs[frozenset((gs[i], gs[j]))] for i, j in ((0, 1), (0, 2), (1, 2)))
        regs = [ab - triple, ac - triple, bc - triple, sizes[gs[0]] - ab - ac + triple, sizes[gs[1]] - ab - bc + triple, sizes[gs[2]] - ac - bc + triple]
        if min(regs) < 0:
            notes.append("inconsistent_counts")
    if total - union < 0:
        notes.append("negative_none")
    return str(total - union), notes


# ---------- revised shapes ----------
DIRS = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}


def grid(q):
    rows = re.findall(r"Row \d+: (.+?)\.(?= |$)", q)
    g = [r.split(", ") for r in rows]
    start = re.search(r"You start at (\w+)\.", q).group(1)
    moves = re.search(r"You move (.+?), one cell each time", q).group(1).split(", then ")
    pos = next((i, j) for i, r in enumerate(g) for j, c in enumerate(r) if c == start)
    for m in moves:
        i, j = pos[0] + DIRS[m][0], pos[1] + DIRS[m][1]
        if 0 <= i < len(g) and 0 <= j < len(g[0]) and g[i][j] != "wall":
            pos = (i, j)
    # alternative: column 1 easternmost (should be excluded by the stated convention)
    return g[pos[0]][pos[1]], []


def parent_facts(q):
    par = {}
    for a, b in re.findall(r"(\w+) is the parent of (\w+)\.", q):
        par[b] = a
    for b, a in re.findall(r"(\w+)'s parent is (\w+)\.", q):
        par[b] = a
    return par


def descendants(q):
    par = parent_facts(q)
    opts = names_list(re.search(r"Choose from (.+?)\.$", q).group(1))
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)

    def desc(p):
        return sum(1 + desc(c) for c in kids[p])

    gc = "grandchildren" in q.split("who has the most")[1][:20]
    sc = {p: (sum(len(kids[c]) for c in kids[p]) if gc else desc(p)) for p in opts}
    top = max(sc.values())
    best = [p for p in opts if sc[p] == top]
    notes = ["tie"] if len(best) > 1 else []
    if set(opts) != set(par):
        notes.append("options_not_equal_people_with_parent")
    return best[0], notes


def ancestor(q):
    par = parent_facts(q)
    term = re.search(r"Who is the ([\w-]+) of (\w+)\?", q)
    k = {"grandparent": 2, "great-grandparent": 3, "great-great-grandparent": 4}[term.group(1)]
    x = term.group(2)
    for _ in range(k):
        if x not in par:
            return None, ["chain_too_short"]
        x = par[x]
    return x, []


def _partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for p in _partitions(rest):
        for i in range(len(p)):
            yield p[:i] + [[first] + p[i]] + p[i + 1:]
        yield [[first]] + p


def equivalence(q):
    same = re.findall(r"(\w+) is the same thing as (\w+)\.", q)
    diff = re.findall(r"(\w+) is a different thing from (\w+)\.", q)
    x, y = re.search(r"Is (\w+) the same thing as (\w+)\?", q).groups()
    ents = sorted({e for p in same + diff for e in p} | {x, y})
    if len(ents) <= 9:
        poss = set()
        for part in _partitions(ents):
            cls = {e: i for i, blk in enumerate(part) for e in blk}
            if all(cls[a] == cls[b] for a, b in same) and all(cls[a] != cls[b] for a, b in diff):
                poss.add(cls[x] == cls[y])
        ans = "cannot be determined" if len(poss) == 2 else ("yes" if True in poss else "no")
        return ans, []
    # closure fallback
    comp = {e: e for e in ents}

    def f(a):
        while comp[a] != a:
            a = comp[a]
        return a

    for a, b in same:
        comp[f(a)] = f(b)
    if f(x) == f(y):
        return "yes", ["closure"]
    if any({f(a), f(b)} == {f(x), f(y)} for a, b in diff):
        return "no", ["closure"]
    return "cannot be determined", ["closure"]


def bracket(q):
    order = re.search(r"players listed in bracket order: (.+?)\. In round one", q).group(1).split(", ")
    beat = set(re.findall(r"(\w+) beat (\w+)\.", q))
    rnd = order[:]
    ko = {}
    final_loser = None
    while len(rnd) > 1:
        nx = []
        for a, b in zip(rnd[0::2], rnd[1::2]):
            if (a, b) in beat:
                w, l = a, b
            elif (b, a) in beat:
                w, l = b, a
            else:
                return None, ["missing_result"]
            ko[l] = w
            if len(rnd) == 2:
                final_loser = l
            nx.append(w)
        rnd = nx
    if "Who loses the final?" in q:
        return final_loser, []
    who = re.search(r"Who knocks (\w+) out\?", q).group(1)
    return ko[who], []


def queue(q):
    line = names_list(re.search(r"A line, from front to back, is: (.+?)\. ", q).group(1))
    body = q.split(". ", 1)[1]
    cur = list(line)
    for s in sents(body):
        m = re.fullmatch(r"(\w+) joins at the back\.", s)
        if m:
            cur.append(m.group(1)); continue
        m = re.fullmatch(r"(\w+) is let in at the very front\.", s)
        if m:
            cur.insert(0, m.group(1)); continue
        if s == "The person at the front is served and leaves.":
            cur.pop(0); continue
        m = re.fullmatch(r"(\w+) gets tired and leaves\.", s)
        if m:
            cur.remove(m.group(1)); continue
        if s == "The person at the front goes to the back of the line.":
            cur.append(cur.pop(0)); continue
    j = int(re.search(r"Who is in position (\d+) from the front", q).group(1))
    if j > len(cur):
        return None, ["position_beyond_line"]
    return cur[j - 1], []


def defaults(q):
    up = dict(re.findall(r"Every (\w+) is a (\w+)\.", q))
    rules = defaultdict(list)
    for g, cc, v in re.findall(r"A (\w+) (can|cannot) (\w+)\.", q):
        rules[(g, v)].append(cc == "can")
    member, grp = re.search(r"(\w+) is a (\w+)\. Can", q).groups()
    verb = re.search(r"Can \w+ (\w+)\?", q).group(1)
    g = grp
    while g is not None:
        if (g, verb) in rules:
            r = rules[(g, verb)]
            notes = ["conflict_same_group"] if len(set(r)) > 1 else []
            return ("yes" if r[0] else "no"), notes
        g = up.get(g)
    return None, ["no_rule"]


def threshold(q):
    w = {p: int(x) for p, x in re.findall(r"(\w+) has weight (\d+)", q)}
    d = int(re.search(r"is at least (-?\d+)", q).group(1))
    # FIX after attempt 1 (text_solvers_run1.txt): restrict to the votes segment; the old regex also matched "or no." in "Answer yes or no."
    votes = dict(re.findall(r"(\w+) (yes|no|abstain)(?=,|\.)", q.split("The votes: ")[1].split(". Does the motion")[0] + "."))
    y = sum(w[p] for p, v in votes.items() if v == "yes")
    n = sum(w[p] for p, v in votes.items() if v == "no")
    return ("yes" if y - n >= d else "no"), ([] if len(votes) == len(w) else ["vote_parse"])


def lights(q):
    nl = int(re.search(r"There are (\d+) lamps", q).group(1))
    st = re.search(r"At the start, (.+?)\. ", q).group(1)
    if st == "all lamps are off":
        on = set()
    elif st == "all lamps are on":
        on = set(range(1, nl + 1))
    else:
        on = {int(x) for x in re.findall(r"\d+", st.split(" is on")[0].split(" are on")[0])}
    wires = {c: [int(x) for x in re.findall(r"\d+", l)] for c, l in re.findall(r"The (\w+) switch toggles lamps? ([\d, and]+) \(", q)}
    presses = re.search(r"pressed in this order: (.+?)\. Is lamp", q).group(1).split(", ")
    ask = int(re.search(r"Is lamp (\d+) on at the end\?", q).group(1))
    state = ask in on
    for c in presses:
        if ask in wires[c]:
            state = not state
    return ("yes" if state else "no"), []


def shortest(q):
    rs = [(a, b, int(w)) for a, b, w in re.findall(r"two-way road between (\w+) and (\w+) of length (\d+)\.", q)]
    s, t = re.search(r"route from (\w+) to (\w+) along these roads\?", q).groups()
    ts = sorted({x for a, b, _ in rs for x in (a, b)})
    INF = 10**9
    d = {(a, b): (0 if a == b else INF) for a in ts for b in ts}
    for a, b, w in rs:
        d[(a, b)] = min(d[(a, b)], w)
        d[(b, a)] = min(d[(b, a)], w)
    for k in ts:
        for i in ts:
            for j in ts:
                if d[(i, k)] + d[(k, j)] < d[(i, j)]:
                    d[(i, j)] = d[(i, k)] + d[(k, j)]
    return str(d[(s, t)]), []


def stacks(q):
    piles = {}
    for p, l in re.findall(r"The (\w+) pile holds, from bottom to top: (.+?)\.(?= )", q):
        piles[p] = [] if l == "nothing" else names_list(l)
    for s in sents(q):
        m = re.fullmatch(r"Move the top block of the (\w+) pile onto the (\w+) pile\.", s)
        if m:
            piles[m.group(2)].append(piles[m.group(1)].pop()); continue
        m = re.fullmatch(r"Turn the (\w+) pile upside down\.", s)
        if m:
            piles[m.group(1)].reverse()
    ask = re.search(r"on top of the (\w+) pile at the end\?", q).group(1)
    return piles[ask][-1], []


def follow(q):
    alls = re.findall(r"All (\w+) are (\w+)\.", q)
    nos = re.findall(r"No (\w+) are (\w+)\.", q)
    cats = sorted({c for p in alls + nos for c in p})
    m = re.search(r"Does it follow that (every|no|some) (\w+) (?:is a|are) (\w+)\?", q)
    kind, x, y = m.groups()
    for c in (x, y):
        if c not in cats:
            cats.append(c)
    idx = {c: i for i, c in enumerate(cats)}
    allowed = []
    for t in range(1 << len(cats)):
        ok = all(not (t >> idx[a] & 1) or (t >> idx[b] & 1) for a, b in alls) and all(not ((t >> idx[a] & 1) and (t >> idx[b] & 1)) for a, b in nos)
        if ok:
            allowed.append(t)
    X, Y = 1 << idx[x], 1 << idx[y]
    xy = any((t & X) and (t & Y) for t in allowed)
    xny = any((t & X) and not (t & Y) for t in allowed)
    # any subset of allowed types is a model (the empty model included)
    if kind == "every":
        ans = "yes" if not xny else "cannot be determined"
    elif kind == "no":
        ans = "yes" if not xy else "cannot be determined"
    else:
        ans = "no" if not xy else "cannot be determined"
    notes = []
    # alternative reading: groups are non-empty (traditional syllogistic) -> does the key change?
    nonempty_models = []
    import itertools as it_
    # under non-empty reading: some model must inhabit every category; entailment over such models
    def sat(model):
        return all(any(t >> idx[c] & 1 for t in model) for c in cats)
    # cheap: entailment over the maximal model (all allowed types) and minimal covers is hard; approximate by checking
    # whether every category is inhabitable at all
    if all(any(t >> idx[c] & 1 for t in allowed) for c in cats):
        if kind == "some" and ans == "cannot be determined":
            # under non-empty reading "some X are Y" follows if X subset Y (every X-type has Y)
            if not xny:
                notes.append("nonempty_reading_gives_yes")
    return ans, notes


SOLVERS = {
    "topological_order_r2": topo, "activity_selection": activity, "mst_cost": mst, "instant_runoff_r2": irv,
    "stable_matching_r2": stable, "nim_xor": nim, "minimax_tree": minimax, "venn_counting": venn,
    "spatial_grid_walk_r2": grid, "kinship_descendants_r3": descendants, "kinship_ancestor_r3": ancestor,
    "equivalence_classes_r2": equivalence, "elimination_bracket_r3": bracket, "containers_queue_line_r2": queue,
    "categories_default_exceptions_r3": defaults, "conditional_threshold_rule_r3": threshold, "boolean_lights_r2": lights,
    "graph_shortest_route_r2": shortest, "containers_stack_piles_r3": stacks, "categories_follow_r2": follow,
}

if __name__ == "__main__":
    d = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "reg"
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    tot_bad = 0
    for lid, fn in SOLVERS.items():
        if only and lid not in only:
            continue
        path = os.path.join(d, f"{lid}.{mode}.jsonl.gz")
        if not os.path.exists(path):
            continue
        rows = [json.loads(x) for x in gzip.open(path, "rt")]
        bad, notes_c, examples = [], Counter(), defaultdict(list)
        for r in rows:
            try:
                ans, notes = fn(r["q"])
            except Exception as e:  # parsing failure is reported, never hidden
                ans, notes = None, [f"EXC {type(e).__name__}: {e}"[:80]]
            if ans is None or ans.lower() != r["a"].lower():
                bad.append((r["id"], ans, r["a"]))
            for n in notes:
                notes_c[n] += 1
                if len(examples[n]) < 3:
                    examples[n].append(r["id"])
        tot_bad += len(bad)
        print(f"{lid} [{mode}]: {len(rows) - len(bad)}/{len(rows)} agree; notes {dict(notes_c)}")
        for b in bad[:10]:
            print("   MISMATCH", b)
        for n, ex in examples.items():
            print("   note", n, "e.g.", ex)
    print("TOTAL mismatches", tot_bad)
