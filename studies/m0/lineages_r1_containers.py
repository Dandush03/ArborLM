# ruff: noqa: E501
"""R1 pilot, family "containers" (intended part A): last-in-first-out piles and a double-ended waiting line."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import COLOURS, NAMES, OBJECTS


@pilot("containers", "A")
def containers_stack_piles(level: int, r: random.Random) -> Built:
    """structured: {"piles": [name], "initial": {pile: [block bottom..top]}, "ops": [["move", from, to] | ["reverse", pile]], "ask": pile}.
    move puts the top block of `from` on top of `to`; reverse turns a pile upside down. Answer: the block on top of `ask` at the end."""
    piles = [f"the {c} pile" for c in r.sample(COLOURS, 3)]
    nb = 4 + level
    blocks = r.sample(OBJECTS, nb)
    state = {p: [] for p in piles}
    for b in blocks:
        state[r.choice(piles)].append(b)
    initial = {p: list(v) for p, v in state.items()}
    ops, text = [], []
    for _ in range(3 + 2 * level):
        full = [p for p in piles if state[p]]
        if level >= 3 and r.random() < 0.2:
            p = r.choice(full)
            state[p].reverse()
            ops.append(["reverse", p])
            text.append(f"Turn {p} upside down.")
            continue
        a = r.choice(full)
        b = r.choice([p for p in piles if p != a])
        state[b].append(state[a].pop())
        ops.append(["move", a, b])
        text.append(f"Move the top block of {a} onto {b}.")
    ask = r.choice([p for p in piles if state[p]])
    init = " ".join(f"{p.capitalize()} holds, from bottom to top: {and_(initial[p]) if initial[p] else 'nothing'}." for p in piles)
    q = f"There are three piles of blocks. {init} {' '.join(text)} Which block is on top of {ask} at the end? Choose from {and_(sorted(blocks))}."
    return Built(q, {"piles": piles, "initial": initial, "ops": ops, "ask": ask}, state[ask][-1], "text", nb)


@pilot("containers", "A")
def containers_queue_line(level: int, r: random.Random) -> Built:
    """structured: {"line": [front..back], "ops": [["join", name] (to the back) | ["cut", name] (to the front) | ["serve"] (front leaves) |
    ["leave", name] (that person leaves)], "ask": "front" | "back"}. Answer: who is at the asked end at the end."""
    pool = r.sample(NAMES, 14 + level)
    line = pool[: 2 + level // 2]
    fresh = pool[len(line):]
    cur = list(line)
    ops, text = [], []
    for _ in range(3 + 2 * level):
        kind = r.choice(("join", "join", "cut", "serve", "leave"))
        if kind in ("serve", "leave") and len(cur) <= 1:
            kind = "join"
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
        else:
            p = r.choice(cur)
            cur.remove(p)
            ops.append(["leave", p])
            text.append(f"{p} gets tired and leaves.")
    if not cur:
        raise Retry
    ask = r.choice(("front", "back"))
    allnames = sorted({*line, *(o[1] for o in ops if o[0] in ("join", "cut"))})
    q = f"A line, from front to back, is: {and_(line)}. " + " ".join(text) + f" Who is at the {ask} of the line at the end? Choose from {and_(allnames)}."
    return Built(q, {"line": line, "ops": ops, "ask": ask}, cur[0] if ask == "front" else cur[-1], "name", len(allnames))
