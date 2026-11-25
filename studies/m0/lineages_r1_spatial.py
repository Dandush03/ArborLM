# ruff: noqa: E501
"""R1 pilot, family "spatial" (intended part A): simulation on a walled grid, and coordinate propagation with a farthest-point query."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot, pl
from studies.m0.vocab import PSEUDO, TOWNS

DIMS = {0: (3, 3), 1: (3, 3), 2: (3, 4), 3: (4, 4), 4: (4, 4), 5: (4, 5), 6: (5, 5)}
STEP = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


@pilot("spatial", "A")
def spatial_grid_walk(level: int, r: random.Random) -> Built:
    """structured: {"grid": [[name | null]] rows top to bottom (null = wall), "start": [row, col] (0-based), "moves": [direction]}.
    north is towards row 0. A move into a wall or off the grid leaves you where you are. Answer: the name of the cell you end on."""
    rows, cols = DIMS[level]
    names = [w.capitalize() for w in r.sample(PSEUDO, rows * cols)]
    grid = [[names[i * cols + j] if r.random() > 0.15 else None for j in range(cols)] for i in range(rows)]
    opens = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j]]
    if len(opens) < 4:
        raise Retry
    pos = start = r.choice(opens)
    moves = [r.choice(list(STEP)) for _ in range(4 + 2 * level)]
    for m in moves:
        ni, nj = pos[0] + STEP[m][0], pos[1] + STEP[m][1]
        if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj]:
            pos = (ni, nj)
    txt = " ".join(f"Row {i + 1}: " + ", ".join(c if c else "wall" for c in row) + "." for i, row in enumerate(grid))
    q = (f"A map has {rows} rows (row 1 is the northernmost) and {cols} columns. {txt} You start at {grid[start[0]][start[1]]}. You move {', then '.join(moves)}, one cell each time. "
         f"A move into a wall or off the map does nothing. Which place do you end on? Choose from {and_(sorted(c for row in grid for c in row if c))}.")
    return Built(q, {"grid": grid, "start": list(start), "moves": moves}, grid[pos[0]][pos[1]], "name", len(opens))


@pilot("spatial", "A")
def spatial_relative_directions(level: int, r: random.Random) -> Built:
    """structured: {"places": [name], "facts": [[a, direction, k, b]] meaning a lies k blocks <direction> of b, "anchor": name}.
    Streets form a grid. Answer: the place (other than the anchor) with the largest street distance (|d_ns| + |d_ew|) from the anchor."""
    n = 3 + level
    places = r.sample(TOWNS, n)
    xy = {places[0]: (0, 0)}
    facts = []
    for i in range(1, n):
        parent = places[r.randrange(i)]
        d = r.choice(list(STEP))
        k = r.randint(1, 9)
        xy[places[i]] = (xy[parent][0] + STEP[d][0] * k, xy[parent][1] + STEP[d][1] * k)
        facts.append([places[i], d, k, parent] if r.random() < 0.5 else [parent, OPP[d], k, places[i]])
    r.shuffle(facts)
    anchor = r.choice(places)
    dist = {p: abs(xy[p][0] - xy[anchor][0]) + abs(xy[p][1] - xy[anchor][1]) for p in places if p != anchor}
    top = max(dist.values())
    if sum(1 for v in dist.values() if v == top) != 1:
        raise Retry
    q = " ".join(f"{a} is {pl(k, 'block')} {d} of {b}." for a, d, k, b in facts) + f" Which place is farthest from {anchor} by street distance (blocks north or south plus blocks east or west)? Choose from {and_(sorted(dist))}."
    return Built(q, {"places": places, "facts": facts, "anchor": anchor}, next(p for p, v in dist.items() if v == top), "name", n - 1)
