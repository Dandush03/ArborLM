# ruff: noqa: E501
"""C1 batch 1, family "tables" (new family): dynamic programming, filling a table from earlier entries.

Strict procedures (three different recurrences; a lead may judge them one 'tabulation' cluster, see the manifest log): ``coin_change_table``
a one-dimensional table over amounts, updated coin by coin; ``string_pair_table`` a two-dimensional table over the prefixes of two strings;
``grid_path_table`` a row of best path values over a grid walked right and down.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import (
    AND,
    IDX,
    LETTERS,
    LIST,
    B,
    C,
    N,
    S,
    V,
    batch,
    finish,
    names,
)


@batch("tables")
def coin_change_table(level: int, r: random.Random) -> Built:
    """Coin table over amounts 0..T: with coins processed one after another (outer loop over coins) ways[a] += ways[a - c] counts the
    combinations; with amounts in the outer loop it counts ordered sequences (the code shows which); or best[a] = min(best[a], best[a - c] + 1)
    gives the fewest coins. Shapes: ways[T], the fewest coins for T, the sum of the whole table. T = 8 + 3 * level + (0, 1 or 2), 2 to 4 coin values from 1 to 12."""
    coins, ways, a, c, k = names(r, 5)
    t = 8 + 3 * level + r.randint(0, 2)
    cv = sorted(r.sample(range(1, 13), r.randint(2, 4)))
    shape = r.choice(("combos", "orders", "fewest", "tablesum"))
    amounts_by_coin: list[list] = [["set", c, IDX(V(coins), V(k))]]
    prog: list[list] = [["set", coins, LIST(cv)]]
    if shape == "fewest":
        reach = [True] + [False] * t
        for amt in range(1, t + 1):
            reach[amt] = any(amt >= x and reach[amt - x] for x in cv)
        if not reach[t]:
            raise Retry  # the answer must be a real count, not the 99 that marks an unreachable amount
        prog += [["set", ways, ["list", N(0)]], ["for", a, N(0), N(t), 1, [["append", ways, N(99)]]],
                 ["for", k, N(0), ["call", "len", V(coins)], 1, [*amounts_by_coin, ["for", a, V(c), N(t + 1), 1,
                  [["setidx", ways, V(a), ["call", "min", IDX(V(ways), V(a)), B("+", IDX(V(ways), B("-", V(a), V(c))), N(1))]]]]]],
                 ["print", IDX(V(ways), N(t))]]
        return finish(prog)
    add = ["setidx", ways, V(a), B("+", IDX(V(ways), V(a)), IDX(V(ways), B("-", V(a), V(c))))]
    prog += [["set", ways, ["list", N(1)]], ["for", a, N(0), N(t), 1, [["append", ways, N(0)]]]]
    if shape == "orders":
        prog.append(["for", a, N(1), N(t + 1), 1, [["for", k, N(0), ["call", "len", V(coins)], 1, [*amounts_by_coin, ["if", C(">=", V(a), V(c)), [add], []]]]]])
    else:
        prog.append(["for", k, N(0), ["call", "len", V(coins)], 1, [*amounts_by_coin, ["for", a, V(c), N(t + 1), 1, [add]]]])
    prog.append(["print", ["call", "sum", V(ways)] if shape == "tablesum" else IDX(V(ways), N(t))])
    return finish(prog)


@batch("tables")
def string_pair_table(level: int, r: random.Random) -> Built:
    """Table over prefixes of two short strings, stored flat with row width len(b) + 1. Longest common subsequence: equal characters take the
    diagonal + 1, else the larger of up and left. Edit distance: first row and column are 0, 1, 2, ...; each cell is the least of up + 1, left + 1
    and diagonal + (0 if the characters are equal else 1). Shapes: the corner cell (the LCS length or the edit distance, which is also the last cell of the table), the last row of the table as a list,
    the sum of the whole table. Lengths 3 to 6 over three letters (3x3, 3x4, 4x4, 4x5, 5x5, 5x6, 6x6)."""
    sa, sb, w, tb, i, j, la, lb = names(r, 8)
    na, nb = (3, 3, 4, 4, 5, 5, 6)[level], (3, 4, 4, 5, 5, 6, 6)[level]
    letters = r.sample(LETTERS, 3)
    xa, xb = "".join(r.choice(letters) for _ in range(na)), "".join(r.choice(letters) for _ in range(nb))
    kind = r.choice(("lcs", "edit"))
    shape = r.choice(("cell", "lastrow", "tablesum"))
    ix = lambda ii, jj: B("+", B("*", ii, V(w)), jj)  # noqa: E731
    up, left, diag = ix(B("-", V(i), N(1)), V(j)), ix(V(i), B("-", V(j), N(1))), ix(B("-", V(i), N(1)), B("-", V(j), N(1)))
    same = C("==", IDX(V(sa), B("-", V(i), N(1))), IDX(V(sb), B("-", V(j), N(1))))
    prog: list[list] = [["set", sa, S(xa)], ["set", sb, S(xb)], ["set", la, ["call", "len", V(sa)]], ["set", lb, ["call", "len", V(sb)]], ["set", w, B("+", V(lb), N(1))], ["set", tb, ["list"]],
                        ["for", i, N(0), B("*", B("+", V(la), N(1)), V(w)), 1, [["append", tb, N(0)]]]]
    if kind == "lcs":
        cell = [["if", same, [["setidx", tb, ix(V(i), V(j)), B("+", IDX(V(tb), diag), N(1))]],
                 [["setidx", tb, ix(V(i), V(j)), ["call", "max", IDX(V(tb), up), IDX(V(tb), left)]]]]]
    else:
        prog += [["for", i, N(0), B("+", V(la), N(1)), 1, [["setidx", tb, ix(V(i), N(0)), V(i)]]],
                 ["for", j, N(0), B("+", V(lb), N(1)), 1, [["setidx", tb, ix(N(0), V(j)), V(j)]]]]
        cost = ["if", same, [["set", "cst", N(0)]], [["set", "cst", N(1)]]]
        cell = [cost, ["setidx", tb, ix(V(i), V(j)), ["call", "min", B("+", IDX(V(tb), up), N(1)), B("+", IDX(V(tb), left), N(1)), B("+", IDX(V(tb), diag), V("cst"))]]]
    prog.append(["for", i, N(1), B("+", V(la), N(1)), 1, [["for", j, N(1), B("+", V(lb), N(1)), 1, cell]]])
    final = {"cell": IDX(V(tb), ix(V(la), V(lb))), "lastrow": ["slice", V(tb), ix(V(la), N(0)), None, None], "tablesum": ["call", "sum", V(tb)]}[shape]
    prog.append(["print", final])
    return finish(prog)


@batch("tables")
def grid_path_table(level: int, r: random.Random) -> Built:
    """Best value of a path from the top-left to the bottom-right cell moving only right or down, kept in one row that is updated cell by cell.
    Shapes: the greatest path sum, the least path sum (values 1 to 9), or the number of paths avoiding blocked cells (cells marked 0).
    Grids are 2x3, 3x3, 3x4, 4x4, 4x5, 5x5, 5x6 for levels 0 to 6; a path-count answer of 0 is redrawn."""
    g, best, i, j, v = names(r, 5)
    nr, nc = ((2, 3), (3, 3), (3, 4), (4, 4), (4, 5), (5, 5), (5, 6))[level]
    shape = r.choice(("max", "min", "count"))
    if shape == "count":
        grid = [[0 if r.random() < 0.25 else 1 for _ in range(nc)] for _ in range(nr)]
        grid[0][0] = grid[nr - 1][nc - 1] = 1
        cnt = [[0] * nc for _ in range(nr)]
        for ri in range(nr):
            for ci in range(nc):
                if grid[ri][ci]:
                    cnt[ri][ci] = 1 if ri == ci == 0 else (cnt[ri - 1][ci] if ri else 0) + (cnt[ri][ci - 1] if ci else 0)
        if cnt[nr - 1][nc - 1] == 0:
            raise Retry
    else:
        grid = [[r.randint(1, 9) for _ in range(nc)] for _ in range(nr)]
    cell = IDX(IDX(V(g), V(i)), V(j))
    first_row, first_col = B("+", IDX(V(best), B("-", V(j), N(1))), V(v)), B("+", IDX(V(best), V(j)), V(v))
    if shape == "count":
        steps: list[list] = [["if", C("==", cell, N(0)), [["setidx", best, V(j), N(0)]],
                              [["if", AND(C("==", V(i), N(0)), C("==", V(j), N(0))), [["setidx", best, V(j), N(1)]],
                                [["if", C("==", V(i), N(0)), [["setidx", best, V(j), IDX(V(best), B("-", V(j), N(1)))]],
                                  [["if", C(">", V(j), N(0)), [["setidx", best, V(j), B("+", IDX(V(best), V(j)), IDX(V(best), B("-", V(j), N(1))))]], []]]]]]]]]
    else:
        pick = ["call", "max" if shape == "max" else "min", IDX(V(best), V(j)), IDX(V(best), B("-", V(j), N(1)))]
        inner = ["setidx", best, V(j), B("+", pick, V(v))]
        steps = [["set", v, cell], ["if", AND(C("==", V(i), N(0)), C("==", V(j), N(0))), [["setidx", best, V(j), V(v)]],
                                    [["if", C("==", V(i), N(0)), [["setidx", best, V(j), first_row]],
                                      [["if", C("==", V(j), N(0)), [["setidx", best, V(j), first_col]], [inner]]]]]]]
    prog: list[list] = [["set", g, ["list", *[LIST(rw) for rw in grid]]], ["set", best, ["list"]], ["for", j, N(0), N(nc), 1, [["append", best, N(0)]]],
                        ["for", i, N(0), N(nr), 1, [["for", j, N(0), N(nc), 1, steps]]], ["print", IDX(V(best), N(nc - 1))]]
    return finish(prog)
