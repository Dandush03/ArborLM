# ruff: noqa: E501
"""C1 batch 1, family "minmax" (existing family): one-pass scans that keep a small invariant state.

Strict procedures: ``kadane_scan`` the maximum-subarray running state (cur = max(cur + x, x)); ``majority_vote_scan`` the Boyer-Moore pairing
scan (candidate and a count that cancels against other values).
"""

from __future__ import annotations

import random
from collections import Counter

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import IDX, LIST, B, C, N, S, V, batch, finish, names


@batch("minmax")
def kadane_scan(level: int, r: random.Random) -> Built:
    """Maximum-subarray scan: cur = max(cur + x, x) and best = max(best, cur) over the list from its second element (cur and best start at
    xs[0]). Shapes: best, the final cur, the sum of the values cur has after each step. The list has 5 + 2 *
    level entries; about 40 percent of them are negative, so neither the largest element nor the sum of the positives is the answer."""
    xs, cur, best, i, cnt = names(r, 5)
    n = 5 + 2 * level
    vals = [-r.randint(1, 9) if r.random() < 0.4 else r.randint(1, 9) for _ in range(n)]
    best_v = cur_v = vals[0]
    for x in vals[1:]:
        cur_v = max(cur_v + x, x)
        best_v = max(best_v, cur_v)
    shape = r.choice(("best", "cur", "curs"))
    if shape == "best" and best_v in (max(vals), sum(v for v in vals if v > 0), sum(vals)):
        raise Retry
    if shape == "cur" and cur_v in (vals[-1], best_v):
        raise Retry
    prog: list[list] = [["set", xs, LIST(vals)], ["set", cur, IDX(V(xs), N(0))], ["set", best, V(cur)]]
    if shape == "curs":
        prog.append(["set", cnt, N(0)])
    body: list[list] = [["set", cur, ["call", "max", B("+", V(cur), IDX(V(xs), V(i))), IDX(V(xs), V(i))]], ["set", best, ["call", "max", V(best), V(cur)]]]
    if shape == "curs":
        body.append(["aug", cnt, "+", V(cur)])
    prog.append(["for", i, N(1), N(n), 1, body])
    prog.append(["print", {"best": V(best), "cur": V(cur), "curs": V(cnt)}[shape]])
    return finish(prog)


@batch("minmax")
def majority_vote_scan(level: int, r: random.Random) -> Built:
    """Boyer-Moore pairing scan: if cnt == 0 take the element as candidate with cnt 1; else cnt += 1 on an equal element and cnt -= 1 on a
    different one. Shapes: the final candidate; the candidate and the count written together as 'candidate count'; the number of times a new
    candidate was taken. The list (6 + 2 * level values from 1 to 6) is drawn so that the final candidate is neither the first nor the last
    element and is the most frequent value in only about a quarter of the items, so 'answer the mode' or 'answer the last value' is not a
    shortcut."""
    xs, cand, cnt, i, rep = names(r, 5)
    n = 6 + 2 * level
    k = r.randint(3, 6)
    vals = [r.randint(1, k) for _ in range(n)]
    c_v, n_v, repl = 0, 0, 0
    for x in vals:
        if n_v == 0:
            c_v, n_v = x, 1
            repl += 1
        elif x == c_v:
            n_v += 1
        else:
            n_v -= 1
    top = Counter(vals).most_common()
    is_mode = top[0][0] == c_v and (len(top) == 1 or top[1][1] < top[0][1])
    want_mode = r.random() < 0.25
    shape = r.choice(("cand", "cand", "pair", "pair", "repl"))
    if shape == "cand" and (c_v in (vals[0], vals[-1]) or is_mode != want_mode):
        raise Retry
    take: list[list] = [["set", cand, IDX(V(xs), V(i))], ["set", cnt, N(1)]]
    if shape == "repl":
        take.append(["aug", rep, "+", N(1)])
    body = [["if", C("==", V(cnt), N(0)), take, [["if", C("==", IDX(V(xs), V(i)), V(cand)), [["aug", cnt, "+", N(1)]], [["aug", cnt, "-", N(1)]]]]]]
    prog: list[list] = [["set", xs, LIST(vals)], ["set", cand, N(0)], ["set", cnt, N(0)]]
    if shape == "repl":
        prog.append(["set", rep, N(0)])
    prog.append(["for", i, N(0), N(n), 1, body])
    prog.append(["print", {"cand": V(cand), "pair": B("+", B("+", ["call", "str", V(cand)], S(" ")), ["call", "str", V(cnt)]), "repl": V(rep)}[shape]])
    return finish(prog)
