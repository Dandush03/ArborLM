# ruff: noqa: E501
"""R1 revision 4, part 3: shapes whose tell was removed by a planted or symmetric construction (second audit; lead rulings R-1). No redraw on a heuristic's outcome.

containers_stack_piles_r4   many random moves (12 + 3 level) of few blocks (5 + level), so the final top is nearly independent of where it started; the asked pile is drawn at the end
stable_matching_r4          the matching is planted: each proposer's rank of their partner is drawn (uniform 1..n), every list built around it
instant_runoff_r4           equal-ish first-place counts (a base plus 0 to 2 for each candidate) with at least four candidates, so the plurality leader is a near coin flip
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pl
from studies.m0.lineages_r1_rev4_common import rev4
from studies.m0.vocab import COLOURS, NAMES, OBJECTS

NO_COLOUR_OBJECTS = tuple(o for o in OBJECTS if o not in COLOURS)


@rev4("containers", "R1.containers_stack_piles_r3")
def containers_stack_piles_r4(level: int, r: random.Random) -> Built:
    """Same schema as containers_stack_piles: {"piles", "initial": {pile: [bottom..top]}, "ops": [["move", a, b] | ["reverse", p]], "ask": pile}. Blocks are never named like a colour. Every move
    is a legal move of a random top block, and there are many of them for the number of blocks (12 + 3 level moves for 5 + level blocks; reversals from level 1 on, 3 in 10 operations), so the final top block of a
    pile has come from nearly anywhere: the initial top, the initial bottom, the last block moved onto the pile and the first one moved onto it are each right about as often as a random
    block (earlier shapes: the last block moved onto the asked pile was right 0.60 of the time, and 0.17 only after a redraw that raised the initial bottom to 0.30). The asked pile is drawn uniformly among the non-empty piles whose most
    recent change was a block taken off or a turn (a design rule of the question, not a reading of a heuristic: the block last put onto the pile is then never the top, and the top is
    whatever lay below it). No redraw."""
    piles = [f"the {c} pile" for c in r.sample(COLOURS, 3)]
    nb = 5 + level
    blocks = r.sample(NO_COLOUR_OBJECTS, nb)
    state: dict[str, list[str]] = {p: [] for p in piles}
    for b in blocks:
        state[r.choice(piles)].append(b)
    initial = {p: list(v) for p, v in state.items()}
    ops, text = [], []
    last_event: dict[str, str] = {}
    for _ in range(12 + 3 * level):
        full = [p for p in piles if state[p]]
        if level >= 1 and r.random() < 0.3:
            p = r.choice(full)
            state[p].reverse()
            ops.append(["reverse", p])
            text.append(f"Turn {p} upside down.")
            last_event[p] = "turn"
            continue
        a = r.choice(full)
        b = r.choice([p for p in piles if p != a])
        state[b].append(state[a].pop())
        ops.append(["move", a, b])
        text.append(f"Move the top block of {a} onto {b}.")
        last_event[a], last_event[b] = "off", "onto"
    cands = [p for p in piles if state[p] and last_event.get(p) in ("off", "turn")]  # the asked pile is one whose most recent change was a removal or a turn
    if not cands:
        raise Retry
    ask = r.choice(cands)
    init = " ".join(f"{p.capitalize()} holds, from bottom to top: {and_(initial[p]) if initial[p] else 'nothing'}." for p in piles)
    q = f"There are three piles of blocks. {init} {' '.join(text)} Which block is on top of {ask} at the end? Choose from {and_(sorted(blocks))}."
    return Built(q, {"piles": piles, "initial": initial, "ops": ops, "ask": ask}, state[ask][-1], "text", nb)


def _deferred_acceptance(ps: list[str], pp: dict[str, list[str]], pr: dict[str, list[str]]) -> dict[str, str]:
    nxt = {p: 0 for p in ps}
    held: dict[str, str] = {}
    free = list(ps)
    while free:
        p = free.pop(0)
        rcv = pp[p][nxt[p]]
        nxt[p] += 1
        if rcv not in held:
            held[rcv] = p
        elif pr[rcv].index(p) < pr[rcv].index(held[rcv]):
            free.append(held[rcv])
            held[rcv] = p
        else:
            free.append(p)
    return {p: x for x, p in held.items()}


@rev4("matching", "R1.stable_matching_r2")
def stable_matching_r4(level: int, r: random.Random) -> Built:
    """Same schema as stable_matching: {"proposers", "receivers", "prefs_p", "prefs_r", "ask"}. Deferred acceptance as before. The instance is PLANTED around a matching M: each proposer's rank rho_p
    of M(p) is drawn; proposers are put in a random planting order with the asked proposer LAST, and the receivers above M(p) in p's list are rho_p - 1 partners of EARLIER proposers (rho_p uniform
    in 1..position, so rho of the asked proposer is uniform in 1..n); each receiver's list is a random permutation of the proposers in which the receiver's partner under M is moved above every
    proposer that wanted the receiver more than their own partner. Then M is stable, and no stable matching is better for any proposer (take the first proposer, in planting order, who does better
    in some stable M'; the receiver he gets is the partner under M of an earlier proposer q, who then does worse than M and forms a blocking pair with that receiver), so deferred acceptance gives
    M. The answer is still computed by running the procedure. The asked proposer's partner is their rho-th choice with rho uniform on 1..n, so no fixed rank (first, second, last choice) is the
    answer more than 1/n of the time (the earlier shape: first choice 0.57; after a redraw on it, second choice 0.46 and first-mentioned 0.15). No redraw on a heuristic's outcome."""
    n = 3 + (level + 1) // 2  # 3, 4, 4, 5, 5, 6, 6 proposers (level 1 needs more than 3: the capacity at G = 13 is 19,470 structures)
    names = r.sample(NAMES, 2 * n)
    ps, rs = names[:n], names[n:]
    perm = r.sample(rs, n)
    mm = dict(zip(ps, perm, strict=True))
    ask = r.choice(ps)
    seq = [p for p in ps if p != ask]
    r.shuffle(seq)
    seq.append(ask)  # the asked proposer is last in the planting order, so its rank is uniform over 1..n
    pp: dict[str, list[str]] = {}
    above: dict[str, list[str]] = {}
    for pos, p in enumerate(seq, start=1):
        rho = r.randint(1, pos)  # rho - 1 receivers above the partner, all partners of EARLIER proposers (makes M the proposer-optimal stable matching)
        earlier = [mm[q] for q in seq[: pos - 1]]
        above[p] = r.sample(earlier, rho - 1)
        rest = [x for x in rs if x != mm[p] and x not in above[p]]
        r.shuffle(rest)
        pp[p] = [*above[p], mm[p], *rest]
    inv = {x: p for p, x in mm.items()}
    pr: dict[str, list[str]] = {}
    for x in rs:
        lst = r.sample(ps, n)
        wanters = [p for p in ps if x in above[p]]
        first = min((lst.index(p) for p in wanters), default=n)
        if lst.index(inv[x]) > first:
            lst.remove(inv[x])
            lst.insert(first, inv[x])
        pr[x] = lst
    match = _deferred_acceptance(ps, pp, pr)
    order = ps[:]
    r.shuffle(order)
    q = ("Some people ask others to partner with them. " + " ".join(f"{p} would like, from best to worst: {', '.join(pp[p])}." for p in order) + " " + " ".join(f"{x} would like, from best to worst: {', '.join(pr[x])}." for x in rs)
         + f" Matching goes in turns: a person from {and_(sorted(ps))} who has no partner asks the best person on their list that they have not asked yet. The person asked keeps the best proposer so far (by their own list) and says no to the others, who then ask the next person on their list. This goes on until everyone in {and_(sorted(ps))} has a partner. Who is {ask}'s partner at the end? Choose from {and_(sorted(rs))}.")
    return Built(q, {"proposers": ps, "receivers": rs, "prefs_p": pp, "prefs_r": pr, "ask": ask}, match[ask], "name", n)


@rev4("voting", "R1.instant_runoff_r2")
def instant_runoff_r4(level: int, r: random.Random) -> Built:
    """Same schema as instant_runoff: {"candidates", "ballots": [[count, [ranking, best first]]]}. Rounds of elimination of the candidate with the fewest ballots counting for them, as before.
    Candidates: 4 + level // 3 (at least four, so that "the top two meet in a runoff" is a different rule from the elimination count). Each candidate's first-place total is a base of 18 plus
    0 to 2 (so the plurality leader is a near coin flip among the candidates), split into one to three groups of voters; the rest of every ranking is a random order. Items with a tie for
    the fewest are drawn again (a validity rule, not a reading of a heuristic). The earlier shape had the plurality leader winning 79 % of the time, and the redraw that fixed that made the
    items comeback-heavy by level."""
    c = 4 + level // 3
    cands = r.sample(NAMES, c)
    ballots: list[list] = []
    for cand in cands:
        total = 18 + r.randint(0, 2)
        g = r.randint(1, 3)
        cuts = sorted(r.sample(range(1, total), g - 1))
        parts = [b - a for a, b in zip([0, *cuts], [*cuts, total], strict=True)]
        for cnt in parts:
            rest = [x for x in cands if x != cand]
            r.shuffle(rest)
            ballots.append([cnt, [cand, *rest]])
    r.shuffle(ballots)
    alive = list(cands)
    while len(alive) > 1:
        tally = {a: 0 for a in alive}
        for cnt, rk in ballots:
            tally[next(x for x in rk if x in alive)] += cnt
        low = min(tally.values())
        out = [a for a in alive if tally[a] == low]
        if len(out) != 1:
            raise Retry
        alive.remove(out[0])
    q = (f"{and_(sorted(cands))} are candidates. " + " ".join(f"{pl(cnt, 'voter')} rank them {' > '.join(rk)} (best first)." for cnt, rk in ballots)
         + " The count goes in rounds: each round, every ballot counts for its best candidate still in the race; the candidate with the fewest ballots counting for them is out, and the next round starts. "
           "It continues until one candidate is left. Who is left?")
    return Built(q, {"candidates": cands, "ballots": ballots}, alive[0], "name", c)
