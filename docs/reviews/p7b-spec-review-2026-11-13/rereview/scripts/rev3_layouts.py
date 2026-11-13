"""ADR-0014 revision 3, section 4, as read by the auditor (Claude Opus 5.5). Standard library only.

No arborlm import, no implementer code. Independent engineering evidence; not Astra validation.

Readings pinned here (see REREVIEW.md for where the text is silent):
  * A0[i][j] (i != j) = number of queries in which i and j are both selected (rev 3 wording;
    half of the revision-1 "N + N^T" reading; scaling does not change any decision).
  * A8 as revision 1/2 (N + N^T over offsets 0..8).
  * Greedy (step 1): seed = unplaced slot of highest f, ties lowest ID; next = highest score,
    ties higher f, then lowest ID; zero-score fall-through = hottest unplaced (score dict empty).
  * Refinement (step 2): visit slots with >= 1 nonzero affinity by (-f, id); candidate pages Q != P
    holding >= 1 slot with nonzero affinity to x (restricted to x's group when constrained); y any
    slot on Q; gain = change of total within-page affinity; best strictly positive gain, ties
    lowest Q then lowest y; a swap exchanges the positions of x and y (READING: the text does not
    say where y goes inside P); passes until a pass makes no swap or 12 passes.
  * Groups ordered by descending total f, ties lowest group index; pages concatenated in group
    order. R = 512 group-level construction implemented for timing only (within-group row order
    there is the step-1 order at R = 256: READING, the text is silent).
"""

from __future__ import annotations

import random

SLOTS, TOP, CTX, PB, NBR = 4096, 8, 64, 256, 16
MAX_PASSES = 12


def counts_of(sel):
    c = [0] * SLOTS
    for s in sel:
        c[s] += 1
    return c


def affinity0(sel, nq):
    """Same-query affinity, dict of dicts, A[i][j] = #queries with both i and j selected."""
    A = {}
    for q in range(nq):
        row = sel[q * TOP:(q + 1) * TOP]
        for a in range(TOP):
            i = row[a]
            d = A.get(i)
            if d is None:
                d = A[i] = {}
            for b in range(TOP):
                if a != b:
                    j = row[b]
                    d[j] = d.get(j, 0) + 1
    return A


def affinity_w(sel, nctx, W):
    """Windowed affinity N + N^T, offsets 0..W inside a context (revision-1 reading)."""
    N = {}
    for k in range(nctx):
        rows = [tuple(sel[(k * CTX + p) * TOP:(k * CTX + p + 1) * TOP]) for p in range(CTX)]
        for t in range(CTX):
            for u in range(max(0, t - W), t + 1):
                for i in rows[t]:
                    d = N.setdefault(i, {})
                    for j in rows[u]:
                        if i != j:
                            d[j] = d.get(j, 0) + 1
    A = {}
    for i, d in N.items():
        for j, v in d.items():
            # attempt 1 evaluated A[j] before creating it (KeyError); fixed:
            di = A.setdefault(i, {})
            di[j] = di.get(j, 0) + v
            dj = A.setdefault(j, {})
            dj[i] = dj.get(i, 0) + v
    return A


def greedy_pages(S, R, f, A):
    order = sorted(S, key=lambda s: (-f[s], s))
    Sset = set(S)
    placed = set()
    ptr = 0
    pages = []
    while len(placed) < len(S):
        while order[ptr] in placed:
            ptr += 1
        seed = order[ptr]
        placed.add(seed)
        page = [seed]
        sc = {}
        for j, v in A.get(seed, {}).items():
            if j in Sset and j not in placed:
                sc[j] = sc.get(j, 0) + v
        while len(page) < R and len(placed) < len(S):
            if sc:
                nxt = max(sc.items(), key=lambda kv: (kv[1], f[kv[0]], -kv[0]))[0]
            else:
                while order[ptr] in placed:
                    ptr += 1
                nxt = order[ptr]
            placed.add(nxt)
            page.append(nxt)
            sc.pop(nxt, None)
            for j, v in A.get(nxt, {}).items():
                if j in Sset and j not in placed:
                    sc[j] = sc.get(j, 0) + v
        pages.append(page)
    return pages


def within_page_affinity(pages, A):
    tot = 0
    for pg in pages:
        for a in range(len(pg)):
            d = A.get(pg[a])
            if d:
                for b in range(a + 1, len(pg)):
                    tot += d.get(pg[b], 0)
    return tot


def refine(pages, A, f, group_of=None, max_passes=MAX_PASSES):
    """Registered bounded swap refinement. group_of: slot -> group id (constrained) or None."""
    pages = [list(p) for p in pages]
    where = {}
    for pi, pg in enumerate(pages):
        for s in pg:
            where[s] = pi
    # wp[s][page] = affinity of s to the slots on that page (s itself excluded: A[s][s] absent)
    wp = {}
    for s, d in A.items():
        w = {}
        for z, v in d.items():
            if v:
                pz = where[z]
                w[pz] = w.get(pz, 0) + v
        wp[s] = w
    active = sorted((s for s, d in A.items() if any(d.values())), key=lambda s: (-f[s], s))
    passes = swaps = 0
    converged = False
    while passes < max_passes:
        passes += 1
        made = 0
        for x in active:
            P = where[x]
            wx = wp[x]
            ax = A[x]
            wxP = wx.get(P, 0)
            gx = None if group_of is None else group_of[x]
            best = None  # (gain, -Q, -y)
            for Q in sorted(q for q, v in wx.items() if q != P and v > 0):
                pq = pages[Q]
                if gx is not None and group_of[pq[0]] != gx:
                    continue
                wxQ = wx[Q]
                for y in pq:
                    axy = ax.get(y, 0)
                    wy = wp.get(y)
                    if wy:
                        gain = wxQ - 2 * axy + wy.get(P, 0) - wxP - wy.get(Q, 0)
                    else:
                        gain = wxQ - wxP
                    if gain > 0:
                        key = (gain, -Q, -y)
                        if best is None or key > best:
                            best = key
            if best is not None:
                Q, y = -best[1], -best[2]
                ix, iy = pages[P].index(x), pages[Q].index(y)
                pages[P][ix], pages[Q][iy] = y, x
                where[x], where[y] = Q, P
                for z, v in ax.items():
                    if v:
                        w = wp[z]
                        w[P] -= v
                        if not w[P]:
                            del w[P]
                        w[Q] = w.get(Q, 0) + v
                for z, v in A.get(y, {}).items():
                    if v:
                        w = wp[z]
                        w[Q] -= v
                        if not w[Q]:
                            del w[Q]
                        w[P] = w.get(P, 0) + v
                made += 1
                swaps += 1
        if not made:
            converged = True
            break
    return pages, {"passes": passes, "swaps": swaps, "converged": converged}


def layout_freq(f, slots=None):
    slots = range(SLOTS) if slots is None else slots
    return sorted(slots, key=lambda s: (-f[s], s))


def order_to_pages(order, R):
    return [list(order[i:i + R]) for i in range(0, len(order), R)]


def partition_groups(seed):
    lst = list(range(SLOTS))
    random.Random(seed).shuffle(lst)
    return [lst[g * PB:(g + 1) * PB] for g in range(NBR)]


def branch_groups():
    return [list(range(b * PB, (b + 1) * PB)) for b in range(NBR)]


def coax(R, f, A, refine_on=True):
    pages = greedy_pages(list(range(SLOTS)), R, f, A)
    if not refine_on:
        return pages, None
    return refine(pages, A, f)


def group_coax(groups, R, f, A, refine_on=True):
    """L-BCOAX / L-PCOAX for R <= 256: groups ordered by descending total count (ties lowest
    group index); steps 1 and 2 inside each group; swaps restricted to the group."""
    tot = [sum(f[s] for s in g) for g in groups]
    gorder = sorted(range(len(groups)), key=lambda g: (-tot[g], g))
    if R > PB:
        return group_level(groups, R, f, A, refine_on)
    pages = []
    for g in gorder:
        pages += greedy_pages(groups[g], R, f, A)
    if not refine_on:
        return pages, None
    gof = {}
    for gi, g in enumerate(groups):
        for s in g:
            gof[s] = gi
    return refine(pages, A, f, gof)


def group_level(groups, R, f, A, refine_on=True):
    """R = 512: the two steps applied to groups (unit = group), page of R // 256 groups."""
    k = R // PB
    gof = {}
    for gi, g in enumerate(groups):
        for s in g:
            gof[s] = gi
    fg = [sum(f[s] for s in g) for g in groups]
    Ag = {}
    for i, d in A.items():
        gi = gof[i]
        for j, v in d.items():
            gj = gof[j]
            if gi != gj:
                Ag.setdefault(gi, {})
                Ag[gi][gj] = Ag[gi].get(gj, 0) + v
    gp = greedy_pages(list(range(len(groups))), k, fg, Ag)
    info = None
    if refine_on:
        gp, info = refine(gp, Ag, fg)
    pages = []
    for page in gp:
        rows = []
        for g in page:
            rows += [s for pg in greedy_pages(groups[g], PB, f, A) for s in pg]
        pages.append(rows)
    return pages, info


def positions(pages):
    pos = [None] * SLOTS
    p = 0
    for pg in pages:
        for s in pg:
            pos[s] = p
            p += 1
    assert p == SLOTS and None not in pos
    return pos
