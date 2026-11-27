# ruff: noqa: E501
"""R2 batch 1, family "dynamics": repeated local update of a one-dimensional row. Synchronous table rule (cellular automaton) versus
asynchronous relaxation to a stable state (chip toppling, whose end state does not depend on the order)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1, lst


def ca_step(row: list[int], table: dict[str, int]) -> list[int]:
    n = len(row)
    out = []
    for i in range(n):
        left = row[i - 1] if i > 0 else 0
        right = row[i + 1] if i < n - 1 else 0
        out.append(table[f"{left}{row[i]}{right}"])
    return out


@batch1("dynamics")
def cellular_automaton(level: int, r: random.Random) -> Built:
    """Procedure: synchronous three-neighbour table update. structured: {"row": [0|1], "table": {"LCR": 0|1} (all 8 triples), "steps": int, "ask": "row" | "count"}.
    Cells beyond either end count as 0. Answer: the row after `steps` steps as a 0/1 string without spaces, or the number of 1s in it. Rejected: constant tables, a final row equal to the start, or an all-equal final row."""
    n = 7 + 2 * level
    row = [r.randint(0, 1) for _ in range(n)]
    keys = [f"{a}{b}{c}" for a in (1, 0) for b in (1, 0) for c in (1, 0)]
    table = {k: r.randint(0, 1) for k in keys}
    if len(set(table.values())) < 2 or table["000"] == 1:
        raise Retry
    steps = 1 + level // 2 if level < 6 else 4
    cur = row
    for _ in range(steps):
        cur = ca_step(cur, table)
    if cur == row or len(set(cur)) < 2:
        raise Retry
    ask = r.choice(("row", "row", "count"))
    tt = ", ".join(f"{k} becomes {table[k]}" for k in keys)
    q = (f"A row of {n} cells holds 0s and 1s: {''.join(map(str, row))}. In one step every cell changes at the same moment, according to the three digits (left neighbour, the cell itself, right neighbour): {tt}. "
         f"The cells beyond the two ends of the row count as 0. After {steps} step{'s' if steps > 1 else ''}, "
         + ("what does the row look like? Give the digits with no spaces." if ask == "row" else "how many cells hold a 1?"))
    if ask == "row":
        return Built(q, {"row": row, "table": table, "steps": steps, "ask": ask}, "".join(map(str, cur)), "text", None)
    return Built(q, {"row": row, "table": table, "steps": steps, "ask": ask}, str(sum(cur)), "number", None)


def stabilise(row: list[int]) -> tuple[list[int], int, int]:
    """returns (final row, topplings, chips lost off the ends)."""
    cur = list(row)
    topple = lost = 0
    n = len(cur)
    while True:
        i = next((j for j in range(n) if cur[j] >= 2), -1)
        if i < 0:
            return cur, topple, lost
        cur[i] -= 2
        topple += 1
        if i > 0:
            cur[i - 1] += 1
        else:
            lost += 1
        if i < n - 1:
            cur[i + 1] += 1
        else:
            lost += 1


@batch1("dynamics")
def chip_toppling(level: int, r: random.Random) -> Built:
    """Procedure: topple until stable (abelian sandpile on a path with open ends). structured: {"row": [int], "ask": "final" | "topplings" | "lost"}.
    A cell with 2 or more chips topples: -2 for itself, +1 to each neighbour; a chip passed beyond an end is lost. Order does not change the end state, the number of topplings or the chips lost.
    Answer: the final row (comma list), the total number of topplings, or the chips lost. Rejected when fewer than 2 or more than 400 topplings."""
    n = 5 + level
    row = [r.randint(0, 3 + (level + 2) // 2) for _ in range(n)]
    fin, top, lost = stabilise(row)
    if not 2 <= top <= 400:
        raise Retry
    ask = r.choice(("final", "topplings", "lost"))
    if ask == "lost" and lost == 0:
        raise Retry
    head = (f"A row of {n} cells holds chips: {lst(row)} (from left to right). A cell that holds 2 or more chips topples: it gives up 2 chips, one going to the cell on its left and one to the cell on its right; "
            "a chip that goes past either end of the row is lost for good. Cells topple one at a time, in any order you like, until no cell holds 2 or more chips (the outcome does not depend on the order). ")
    if ask == "final":
        return Built(head + "What does the row hold at the end? Give the numbers from left to right, separated by commas.", {"row": row, "ask": ask}, lst(fin), "list", None)
    if ask == "topplings":
        return Built(head + "How many topplings happen in total?", {"row": row, "ask": ask}, str(top), "number", None)
    return Built(head + "How many chips are lost past the two ends in total?", {"row": row, "ask": ask}, str(lost), "number", None)
