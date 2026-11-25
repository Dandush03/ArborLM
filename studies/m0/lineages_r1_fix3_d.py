# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 3, part d: scheduling, queues, accounts, grids, games and topological order. Ids end in ``_r5``.

temporal_critical_path_r5     every job that waits has exactly two prerequisites; the day convention is stated; the answer is the number of days in all
temporal_interval_overlap_r5  the start gap g is drawn first, independent of the answer; the earlier event's length is drawn above g (yes) or at most g (no)
containers_queue_line_r5      the asked position j is drawn first; every leave removes one of the first j people, so no operation class can be ignored
tracking_accounts_r5          asks one person's final balance (a number); an earning, a payment and a halving involving them are planted
spatial_grid_walk_r5          3 + level // 3 moves are blocked by walls, planted by construction; the other moves are free
nim_xor_r5                    the xor of a first-player win is a single bit (position uniform), so no partial run of the xor reads above chance
topological_order_r5          parallel chains of unequal length, names unrelated to the order, so the alphabetical rule decides most days
"""

from __future__ import annotations

import heapq
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pl
from studies.m0.lineages_r1_fix3_common import fix3
from studies.m0.lineages_r1_spatial import DIMS, STEP
from studies.m0.vocab import EVENTS, NAMES, PSEUDO


@fix3("temporal", "R1.temporal_critical_path_r4")
def temporal_critical_path_r5(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[person, days, [persons it waits for]]]}. Answer: how many days in all pass until the last job has finished (an open number). The item STATES the convention: jobs take whole days; a
    job that waits for nobody starts at the beginning of day 1; a job that waits for others starts at the beginning of the first day after the last of them has finished its final day; the count runs from the beginning of day 1
    to the end of the final day of the last job. (The earlier item said 'starts on day 0 ... on which day is the last job finished' and the key was one too high under the inclusive-day reading in 7,000 of 7,000 items.) 8 + level jobs;
    durations 5 to 12 days; the first two wait for nobody and every later job waits for exactly two of the four jobs before it, so a walk back through 'the longest predecessor' has to choose at every step of a long chain and the finish times of the two predecessors differ by more than a duration does (the earlier shape: 50 % of the jobs had one prerequisite and
    that walk scored +0.69 to +0.86)."""
    n = 8 + level
    people = r.sample(NAMES, n)
    jobs, finish = [], {}
    for i, p in enumerate(people):
        deps = sorted(r.sample(people[max(0, i - 4) : i], 2)) if i >= 2 else []  # the two prerequisites are among the four jobs before it, so chains are long
        d = r.randint(5, 12)
        jobs.append([p, d, deps])
        finish[p] = max([finish[x] for x in deps], default=0) + d
    ans = max(finish.values())
    order = jobs[:]
    r.shuffle(order)
    text = [f"{p}'s job takes {pl(d, 'day')} and waits for nobody." if not deps else f"{p}'s job takes {pl(d, 'day')} and waits for the jobs of {and_(deps)}." for p, d, deps in order]
    q = (" ".join(text) + " Jobs take whole days. A job that waits for nobody starts at the beginning of day 1. A job that waits for others starts at the beginning of the first day after the last of them has finished its final day. "
         "How many days in all pass, counting from the beginning of day 1 to the end of the final day of the last job to finish?")
    return Built(q, {"jobs": jobs}, str(ans), "number", None)


@fix3("temporal", "R1.temporal_interval_overlap")
def temporal_interval_overlap_r5(level: int, r: random.Random) -> Built:
    """structured: {"events", "spans": [["range", a, b] | ["dur", s, d]], "x", "y"} as temporal_interval_overlap. The asked pair: the answer (yes / no) and the gap g between the two starts (uniform 0 .. 40) are drawn
    independently; the event that starts first lasts L days with L uniform in g + 1 .. g + 12 (they overlap) or in max(2, g - 11) .. g (they do not), and the other lasts 2 to 60 days (so 'the longer of the two lasts longer than the gap' is not the test). So the gap between the starts says nothing
    (the earlier shape: 'the starts are within 20 days' scored +0.39 to +0.42), the duration of the event that starts last is irrelevant, and both date formats occur. 4 + (level + 1) // 2 events; the other events are random."""
    n = 4 + (level + 1) // 2
    events = r.sample(EVENTS, n)
    want = r.choice(("yes", "no"))
    g = r.randint(0, 40)
    if want == "yes":
        e_len = r.randint(g + 1, g + 12)
    else:
        if g < 2:
            g = r.randint(2, 40)
        e_len = r.randint(max(2, g - 11), g)
    l_len = r.randint(2, 60)
    s_early = r.randint(1, 100)
    ab: list[tuple[int, int]] = [(s_early, s_early + e_len - 1), (s_early + g, s_early + g + l_len - 1)]
    for _ in range(n - 2):
        s, d = r.randint(1, 140), r.randint(2, 25)
        ab.append((s, s + d - 1))
    order = list(range(n))
    r.shuffle(order)  # position of each interval among the events; intervals 0 and 1 are the asked pair
    spans: list[list] = [[] for _ in range(n)]
    text: list[str] = [""] * n
    for k, pos in enumerate(order):
        a, b = ab[k]
        if r.random() < 0.5:
            spans[pos] = ["range", a, b]
            text[pos] = f"{events[pos].capitalize()} ran from day {a} to day {b}, both days included."
        else:
            spans[pos] = ["dur", a, b - a + 1]
            text[pos] = f"{events[pos].capitalize()} started on day {a} and went on for {pl(b - a + 1, 'day')} (day {a} counts as the first)."
    i, j = order[0], order[1]
    if r.random() < 0.5:
        i, j = j, i
    got = "yes" if max(ab[0][0], ab[1][0]) <= min(ab[0][1], ab[1][1]) else "no"
    if got != want:
        raise Retry
    q = " ".join(text) + f" Did {events[i]} and {events[j]} overlap, that is, was there at least one day on which both were going on? Answer yes or no."
    return Built(q, {"events": events, "spans": spans, "x": events[i], "y": events[j]}, want, "yn", 2)


@fix3("containers", "R1.containers_queue_line_r2")
def containers_queue_line_r5(level: int, r: random.Random) -> Built:
    """structured: {"line": [front..back], "ops": [["join", n] | ["cut", n] | ["serve"] | ["leave", n] | ["front_to_back"]], "ask": ["position", j]} as containers_queue_line_r2. The asked position j (2, 3 or 4) is drawn
    first. 8 + 2 * level operations: one of each kind, in random places, and the rest drawn with the weights of the earlier shape except that 'cut' counts twice; a person who leaves is drawn among the people in positions 2 to j of the line at that moment, and the line never has fewer than j + 2 people, so
    every serve, cut, leave and front-to-back move shifts the person in position j, and ignoring any one kind of operation changes who stands there (the earlier shape: ignoring 'leave' scored +0.22 to +0.48).
    The line starts with 9 + level // 2 people."""
    j = r.randint(2, 4)
    pool = r.sample(NAMES, 34 + 2 * level)
    line = pool[: 9 + level // 2]
    fresh = pool[len(line) :]
    cur = list(line)
    ops, text = [], []
    total = 8 + 2 * level
    sched = ["join", "cut", "serve", "leave", "front_to_back"] + [r.choice(("join", "cut", "cut", "serve", "leave", "front_to_back", "front_to_back")) for _ in range(total - 5)]
    r.shuffle(sched)  # every kind of operation occurs at least once, in a random place
    for kind in sched:
        if kind in ("serve", "leave", "front_to_back") and len(cur) < j + 3:
            raise Retry  # validity: every planned operation must be possible
        if kind == "join":
            p = fresh.pop()
            cur.append(p)
            ops.append(["join", p])
            text.append(f"{p} joins at the back.")
        elif kind == "cut":
            p = fresh.pop()
            cur.insert(0, p)
            ops.append(["cut", p])
            text.append(f"{p} is let in at the very front.")
        elif kind == "serve":
            cur.pop(0)
            ops.append(["serve"])
            text.append("The person at the front is served and leaves.")
        elif kind == "leave":
            p = r.choice(cur[1:j])  # positions 2 .. j (the front is the one a later 'serve' takes)
            cur.remove(p)
            ops.append(["leave", p])
            text.append(f"{p} gets tired and leaves.")
        else:
            cur.append(cur.pop(0))
            ops.append(["front_to_back"])
            text.append("The person at the front goes to the back of the line.")
    allnames = sorted({*line, *(o[1] for o in ops if o[0] in ("join", "cut"))})
    q = f"A line, from front to back, is: {and_(line)}. " + " ".join(text) + f" Who is in position {j} from the front of the line at the end (position 1 is the very front)? Choose from {and_(allnames)}."
    return Built(q, {"line": line, "ops": ops, "ask": ["position", j]}, cur[j - 1], "name", len(allnames))


@fix3("tracking", "R1.tracking_accounts")
def tracking_accounts_r5(level: int, r: random.Random) -> Built:
    """structured: {"start": {name: dollars}, "ops": [["pay", a, b, amount] | ["earn", a, amount] | ["half", a, b]], "ask": name} as tracking_accounts, except that the question asks how many dollars ONE person
    has at the end (an open number; the earlier shape asked who has the most or the least, and a walk that ignored the earnings scored +0.50 to +0.57). The asked person is drawn first and three operations
    that involve them are planted at random places: a payment (they pay or are paid), an earning, and a halving (they give or receive half). Everyone starts with 50 to 80 dollars; pay and earn amounts are 5 to 50;
    the payer always has the money; 6 + 2 * level operations among 4 + level // 2 people. Ignoring any one kind of operation therefore changes the asked person's balance."""
    n = 4 + level // 2
    ps = r.sample(NAMES, n)
    bal = {p: r.randint(50, 80) for p in ps}
    start = dict(bal)
    who = r.choice(ps)
    total = 6 + 2 * level
    must = dict(zip(r.sample(range(total), 3), r.sample(("pay", "earn", "half"), 3), strict=True))
    ops, text = [], []
    for step in range(total):
        kind = must.get(step) or r.choice(("pay", "pay", "earn", "half"))
        a, b = r.sample(ps, 2)
        if step in must and kind in ("pay", "half"):
            if r.random() < 0.5:
                a = who
            else:
                b = who
            if a == b:
                a = r.choice([p for p in ps if p != b])
        if kind == "earn" and step in must:
            a = who
        if kind == "half" and step in must:  # a planted halving needs an even balance of at least 20 in the giver; the asked person is the giver if they have it, else the receiver
            ok = [p for p in ps if bal[p] % 2 == 0 and bal[p] >= 20]
            opts = [(who, r.choice([p for p in ps if p != who]))] if who in ok else []
            opts += [(g, who) for g in ok if g != who]
            if not opts:
                raise Retry
            a, b = r.choice(opts)
        elif kind == "half" and (bal[a] % 2 or bal[a] < 20):
            kind = "earn"
        if kind == "pay" and bal[a] < 6:
            if step in must:
                raise Retry
            kind = "earn"
        if kind == "pay":
            amt = r.randint(5, min(50, bal[a]))
            bal[a] -= amt
            bal[b] += amt
            ops.append(["pay", a, b, amt])
            text.append(f"{a} pays {b} {pl(amt, 'dollar')}.")
        elif kind == "earn":
            amt = r.randint(5, 50)
            bal[a] += amt
            ops.append(["earn", a, amt])
            text.append(f"{a} earns {pl(amt, 'dollar')}.")
        else:
            h = bal[a] // 2
            bal[a] -= h
            bal[b] += h
            ops.append(["half", a, b])
            text.append(f"{a} gives half of their money to {b}.")
    q = "At the start " + ", ".join(f"{p} has {pl(start[p], 'dollar')}" for p in ps) + ". " + " ".join(text) + f" How many dollars does {who} have at the end?"
    return Built(q, {"start": start, "ops": ops, "ask": who}, str(bal[who]), "number", None)


@fix3("spatial", "R1.spatial_grid_walk_r2")
def spatial_grid_walk_r5(level: int, r: random.Random) -> Built:
    """structured: {"grid": [[name | null]], "start": [row, col], "moves": [direction], "convention": ...} as spatial_grid_walk_r2. About 30 % of the cells are walls (the earlier shape: 15 %). The walk has
    L = 4 + level + (0 to 3) free moves (so its length is not always odd or even, which would fix the colour of the end cell on the grid) and 3 + level // 3 moves blocked by a wall. The END cell is drawn first, uniformly among the open
    cells that a walk of exactly L free steps can reach from the start; the free walk is then drawn uniformly among such walks (counted by dynamic programming); the blocked moves are inserted at uniformly drawn places where the
    current cell has a wall next to it, each blocked direction uniform among the walls next to that cell (a Retry when no place has one: validity). So a walk that ignores the walls enters a wall in almost every item (the earlier
    shape scored +0.46 to +0.66) and the end cell is not tied to the start cell."""
    rows, cols = DIMS[level]
    names = [w.capitalize() for w in r.sample(PSEUDO, rows * cols)]
    grid = [[names[i * cols + j] if r.random() > 0.30 else None for j in range(cols)] for i in range(rows)]
    opens = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j]]
    if len(opens) < 4:
        raise Retry
    nblock = 3 + level // 3
    length = 4 + level + r.randint(0, 3)
    idx = {c: k for k, c in enumerate(opens)}
    nbrs: dict[tuple[int, int], list[tuple[str, tuple[int, int]]]] = {c: [] for c in opens}
    walls: dict[tuple[int, int], list[str]] = {c: [] for c in opens}
    for c in opens:
        for m, (di, dj) in STEP.items():
            ni, nj = c[0] + di, c[1] + dj
            if 0 <= ni < rows and 0 <= nj < cols:
                if grid[ni][nj]:
                    nbrs[c].append((m, (ni, nj)))
                else:
                    walls[c].append(m)
    start = r.choice(opens)
    # forward counts from the start: reach[k][v] = number of free walks of k steps from start to v
    reach = [[0] * len(opens) for _ in range(length + 1)]
    reach[0][idx[start]] = 1
    for k in range(length):
        for c in opens:
            if reach[k][idx[c]]:
                for _, nb in nbrs[c]:
                    reach[k + 1][idx[nb]] += reach[k][idx[c]]
    ends = [c for c in opens if reach[length][idx[c]]]
    if not ends:
        raise Retry
    end = r.choice(ends)
    # sample a walk uniformly among those from start to end of `length` steps, backwards
    walk = [end]
    cur = end
    for k in range(length, 0, -1):
        prev = [(nb, reach[k - 1][idx[nb]]) for _, nb in nbrs[cur] if reach[k - 1][idx[nb]]]
        tot = sum(w for _, w in prev)
        pick = r.randrange(tot)
        for nb, w in prev:
            if pick < w:
                cur = nb
                break
            pick -= w
        walk.append(cur)
    walk.reverse()
    places = [t for t in range(length + 1) if walls[walk[t]]]
    if not places:
        raise Retry
    at = sorted(r.choice(places) for _ in range(nblock))
    moves: list[str] = []
    k = 0
    for t in range(length + 1):
        while k < len(at) and at[k] == t:
            moves.append(r.choice(walls[walk[t]]))
            k += 1
        if t < length:
            a, b2 = walk[t], walk[t + 1]
            moves.append(next(m for m, nb in nbrs[a] if nb == b2))
    txt = " ".join(f"Row {i + 1}: " + ", ".join(c if c else "wall" for c in row) + "." for i, row in enumerate(grid))
    q = (f"A map has {rows} rows (row 1 is the northernmost) and {cols} columns (column 1 is the westernmost). {txt} You start at {grid[start[0]][start[1]]}. You move {', then '.join(moves)}, one cell each time. "
         f"A move into a wall or off the map does nothing. Which place do you end on? Choose from {and_(sorted(c for row in grid for c in row if c))}.")
    return Built(q, {"grid": grid, "start": list(start), "moves": moves, "convention": "row 1 is the northernmost, column 1 is the westernmost"}, grid[end[0]][end[1]], "name", len(opens))


_NIM5 = [(4, 256), (4, 512), (4, 1024), (6, 512), (6, 1024), (8, 512), (8, 1024)]  # (piles, m): every pile in [m, 2m)


@fix3("games", "R1.nim_xor_r4")
def nim_xor_r5(level: int, r: random.Random) -> Built:
    """structured: {"piles": [sizes], "size_class": m} as nim_xor_r4. The answer ('first' or 'second') is drawn first. second: the last pile is the xor of the others (xor 0); first: the last pile is that xor with ONE bit
    flipped, the bit position drawn uniformly among bits 1 .. log2(m) - 1 (so the xor of the piles is a single power of two). Every pile is in [m, 2m), so the top bit is in every pile and the sum is even. A
    run of the xor on one or two bit positions is then right only 1 / (log2(m) - 1) of the time on the first-player items (+0.5 / (bits) over chance, 0.06 at 9 bits; the earlier shape: bit 1 alone scored +0.23 to +0.30)."""
    k, m = _NIM5[level]
    bits = m.bit_length() - 1
    want = r.choice(("first", "second"))
    piles = [r.randint(m, 2 * m - 1) for _ in range(k - 1)]
    x = 0
    for p in piles:
        x ^= p
    last = x if want == "second" else x ^ (1 << r.randint(1, bits - 1))
    if not m <= last < 2 * m:
        raise Retry
    piles.append(last)
    r.shuffle(piles)
    q = (f"A game has {k} piles of stones: " + ", ".join(str(p) for p in piles) + ". Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). "
         "The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.")
    return Built(q, {"piles": piles, "size_class": m}, want, "word", 2)


_TOPO_W0 = 4
_TOPO_X = 0.1


@fix3("scheduling", "R1.topological_order_r4")
def topological_order_r5(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[name, [prerequisites]]], "day": j} as topological_order_r4. 10 + level jobs in 4 + level // 2 parallel chains of unequal length (each job needs the one before it in its chain), and
    every job also needs, with probability 1/10, one job of another chain that sits earlier in its chain than it (a cross prerequisite). Names are drawn independently of the position in a chain, so the alphabetical
    rule decides most days and a layered order (depth, then name) usually differs from the true one. Answer: the job done on day j (3 .. n)."""
    n = 10 + level
    w = _TOPO_W0 + level // 2
    ps = r.sample(NAMES, n)
    chain_of = [i % w for i in range(n)]
    r.shuffle(chain_of)
    cuts = sorted(r.sample(range(1, n), w - 1))
    sizes = [b - a for a, b in zip([0, *cuts], [*cuts, n], strict=True)]
    chains: list[list[str]] = []
    k = 0
    for s in sizes:
        chains.append(ps[k : k + s])
        k += s
    deps: dict[str, set[str]] = {p: set() for p in ps}
    for ch in chains:
        for a, b in zip(ch, ch[1:], strict=False):
            deps[b].add(a)
    for ci, ch in enumerate(chains):
        for pos, p in enumerate(ch):
            if pos >= 1 and r.random() < _TOPO_X:
                other = [o for cj, oc in enumerate(chains) if cj != ci for o in oc[: pos]]
                if other:
                    deps[p].add(r.choice(other))
    jobs = [[p, sorted(deps[p])] for p in ps]
    r.shuffle(jobs)
    left = {p: set(d) for p, d in deps.items()}
    heap = [p for p, d in deps.items() if not d]
    heapq.heapify(heap)
    done: list[str] = []
    while heap:
        p = heapq.heappop(heap)
        done.append(p)
        for q2 in sorted(left):
            if p in left[q2]:
                left[q2].discard(p)
                if not left[q2] and q2 not in done and q2 not in heap:
                    heapq.heappush(heap, q2)
    if len(done) != n:
        raise Retry
    j = r.randint(3, n)
    text = [f"{p} has no prerequisite." if not d else f"{p} needs {and_(d)} to be done first." for p, d in jobs]
    q = (f"There are {n} jobs and one job is done each day. " + " ".join(text) + " Each day, among the jobs that can be done (all their prerequisites are already done), the job whose name comes first in alphabetical order is done."
         f" Which job is done on day {j}? Choose from {and_(sorted(ps))}.")
    return Built(q, {"jobs": jobs, "day": j}, done[j - 1], "name", n)


_VENN5 = [(2, "none"), (2, "one"), (3, "none"), (3, "two"), (3, "atleast_two"), (4, "none"), (4, "two")]


@fix3("sets", "R1.venn_counting_r4")
def venn_counting_r5(level: int, r: random.Random) -> Built:
    """structured: {"total", "groups", "sizes", "pairs", "triples", "quad", "triple", "ask"} as venn_counting_r4 (the same levels: groups and asked quantity, the same wording). Only the magnitudes are wider: every region holds
    1 to 24 + 4 * level people and the number in none of the groups is 0 to 30 + 2 * level, because the earlier level 0 (two groups, regions of 1 to 9) could print only about 11,000 different items, below the demand of 22,830."""
    g, ask = _VENN5[level]
    groups = r.sample(("chess", "choir", "diving", "poetry", "rowing", "archery", "baking"), g)
    regions = {mask: r.randint(1, 24 + 4 * level) for mask in range(1, 1 << g)}
    none = r.randint(0, 30 + 2 * level)
    total = sum(regions.values()) + none

    def inter(idx: tuple[int, ...]) -> int:
        return sum(v for mk, v in regions.items() if all(mk >> i & 1 for i in idx))

    sizes = {groups[i]: inter((i,)) for i in range(g)}
    pairs = {f"{groups[i]}|{groups[j]}": inter((i, j)) for i in range(g) for j in range(i + 1, g)}
    triples = {f"{groups[i]}|{groups[j]}|{groups[k]}": inter((i, j, k)) for i in range(g) for j in range(i + 1, g) for k in range(j + 1, g)}
    quad = inter(tuple(range(4))) if g == 4 else None
    pop = {mk: bin(mk).count("1") for mk in regions}
    ans = {"none": none, "one": sum(v for mk, v in regions.items() if pop[mk] == 1), "two": sum(v for mk, v in regions.items() if pop[mk] == 2), "atleast_two": sum(v for mk, v in regions.items() if pop[mk] >= 2)}[ask]
    text = [f"{sizes[x]} people are in the {x} group" for x in groups] + [f"{v} are in both the {k.split('|')[0]} and the {k.split('|')[1]} groups" for k, v in pairs.items()]
    text += [f"{v} are in all of the {and_(k.split('|'))} groups" for k, v in triples.items()]
    if quad is not None:
        text.append(f"{quad} are in all four groups")
    what = {"none": "in none of these groups", "one": "in exactly one of these groups", "two": "in exactly two of these groups", "atleast_two": "in at least two of these groups"}[ask]
    q = f"Among {total} people, " + "; ".join(text) + f". Each person is counted once in each number that applies to them. How many of the people are {what}?"
    return Built(q, {"total": total, "groups": groups, "sizes": sizes, "pairs": pairs, "triples": triples, "quad": quad, "triple": (triples and next(iter(triples.values()))) if g == 3 else None, "ask": ask}, str(ans), "number", None)
