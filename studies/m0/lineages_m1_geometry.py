# ruff: noqa: E501
"""M1 batch 1, family "geometry": the Pythagorean relation, the perimeter of a tiled shape (exposed edges), and painted-cube counting (region decomposition)."""

from __future__ import annotations

import math
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, ctx, m1
from studies.m0.vocab import NAMES


def _triples(limit: int) -> list[tuple[int, int, int]]:
    out = []
    for a in range(3, limit):
        for b in range(a + 1, limit):
            c2 = a * a + b * b
            c = math.isqrt(c2)
            if c * c == c2 and c <= limit:
                out.append((a, b, c))
    return out


_T = _triples(600)


@m1("geometry")
def pythagoras(level: int, r: random.Random) -> Built:
    """structured: {"shape": "ladder_top" | "ladder_base" | "walk" | "diagonal" | "perimeter", "legs": [a, b], "hyp": c, "given": [..the numbers in the item..]}; (a, b, c) is a Pythagorean triple.
    ladder_top: a ladder of length c leans on a wall, its foot is a from the wall; answer the height reached. ladder_base: length c, reaching height a; answer the distance of the foot.
    walk: walk a east then b north; answer the straight-line distance back. diagonal: a rectangle a by b; answer its diagonal. perimeter: a right triangle with legs a and b; answer its perimeter."""
    limit = 60 + 80 * level
    a, b, c = r.choice([t for t in _T if t[2] <= limit])
    if r.random() < 0.5:
        a, b = b, a
    shape = r.choice(("ladder_top", "ladder_base", "walk", "diagonal", "perimeter"))
    name = r.choice(NAMES)
    if shape == "ladder_top":
        ans, given = b, [c, a]
        q = f"A ladder {c} metres long leans against a vertical wall. Its foot is {a} metres from the base of the wall, on level ground. How high up the wall does the top of the ladder reach, in metres? {WHOLE}"
    elif shape == "ladder_base":
        ans, given = a, [c, b]
        q = f"A ladder {c} metres long leans against a vertical wall and its top reaches {b} metres up the wall. How far is its foot from the base of the wall, in metres, on level ground? {WHOLE}"
    elif shape == "walk":
        ans, given = c, [a, b]
        q = f"{name} walks {a} metres due east and then {b} metres due north. How far is {name} now from the starting point in a straight line, in metres? {WHOLE}"
    elif shape == "diagonal":
        ans, given = c, [a, b]
        q = f"A rectangular screen is {a} centimetres wide and {b} centimetres tall. What is the length of its diagonal, in centimetres? {WHOLE}"
    else:
        ans, given = a + b + c, [a, b]
        q = f"A right-angled triangle has two short sides (the sides next to the right angle) of {a} centimetres and {b} centimetres. What is the length of the whole boundary of the triangle (its perimeter), in centimetres? {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"shape": shape, "legs": [a, b], "hyp": c, "given": given}, str(ans), "number", None)


@m1("geometry")
def grid_perimeter(level: int, r: random.Random) -> Built:
    """structured: {"rows": [[first_column, last_column]] from the top row down}. Unit squares fill, in each row, every column from first to last (inclusive); consecutive rows share at least one column.
    Answer: the perimeter of the whole shape in unit lengths (every side of a unit square that has no unit square of the shape on its other side). The generator rejects shapes whose
    perimeter equals that of their bounding box."""
    nrows = 3 + level // 2 + (level >= 5)
    rows: list[list[int]] = []
    lo = r.randint(1, 4)
    hi = lo + r.randint(1, 4 + level // 2)
    rows.append([lo, hi])
    for _ in range(nrows - 1):
        a = r.randint(max(1, rows[-1][0] - 3), rows[-1][1])
        b = r.randint(max(a, rows[-1][0]), rows[-1][1] + 3)
        if a > rows[-1][1] or b < rows[-1][0]:
            raise Retry
        rows.append([a, b])
    cells = sum(b - a + 1 for a, b in rows)
    horiz = sum(b - a for a, b in rows)
    vert = sum(min(rows[i][1], rows[i + 1][1]) - max(rows[i][0], rows[i + 1][0]) + 1 for i in range(len(rows) - 1))
    per = 4 * cells - 2 * (horiz + vert)
    cmin, cmax = min(a for a, _ in rows), max(b for _, b in rows)
    if per == 2 * ((cmax - cmin + 1) + len(rows)):
        raise Retry
    txt = " ".join(f"Row {i + 1} (counting from the top) has squares in columns {a} to {b}, both included." for i, (a, b) in enumerate(rows))
    q = (f"Unit squares (each side 1 unit long) are placed on a grid to make one shape. {txt} Every column number is a position along the row, so squares with the same column number in neighbouring rows sit directly above and below each other. "
         f"What is the perimeter of the whole shape, that is, the total length of its outer boundary, in units? {WHOLE}")
    return Built(q, {"rows": rows}, str(per), "number", None)


@m1("geometry")
def painted_cube(level: int, r: random.Random) -> Built:
    """structured: {"dims": [a, b, c], "bottom_unpainted": true | false, "faces": f}. A block a x b x c is built from unit cubes, then every outer face is painted (except the bottom face if
    `bottom_unpainted`) and the block is taken apart. Answer: how many unit cubes have exactly f painted faces (f is 0, 1 or 2)."""
    top = 8 + 2 * level
    dims = [r.randint(3, top) for _ in range(3)]
    ba = r.random() < 0.5
    f = r.choice((0, 1, 2))
    a, b, c = dims
    cnt = 0
    for x in range(a):
        for y in range(b):
            for z in range(c):
                p = (x in (0, a - 1)) + (y in (0, b - 1)) + (z == c - 1) + (z == 0 and not ba)
                cnt += p == f
    if cnt < 4 or cnt in dims:
        raise Retry
    paint = "every outer face is painted red except the bottom face, which stays unpainted" if ba else "every outer face (including the bottom) is painted red"
    q = (f"A block is made from small cubes of the same size glued together into a box {a} cubes long, {b} cubes wide and {c} cubes high. The whole box is placed on a table and {paint}. "
         f"Then the box is taken apart into the small cubes. How many small cubes have exactly {f} painted {'face' if f == 1 else 'faces'}? {WHOLE}")
    return Built(f"{ctx(r)} {q}", {"dims": dims, "bottom_unpainted": ba, "faces": f}, str(cnt), "number", None)
