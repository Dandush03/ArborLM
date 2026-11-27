# ruff: noqa: E501
"""C1 batch 1, family "swaps" (existing family): in-place reordering of a list (the existing ``bubble_pass`` is the adjacent-swap pass).

Strict procedures: ``insertion_sort`` take each next element and shift larger elements of the sorted prefix one place right until its hole is
found; ``partition_pass`` Lomuto partition, one sweep that swaps elements not above the pivot behind a growing boundary, pivot placed last.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, V, batch, finish, names


@batch("swaps")
def insertion_sort(level: int, r: random.Random) -> Built:
    """Insertion sort run for the first K outer rounds (K is the whole list about one time in five): key = xs[i]; shift every larger
    element of xs[0..i-1] one place right; drop key in the hole. The order is ascending (test '>') or descending (test '<'), and the test is
    strict or not (stated in the code). Shapes: the list afterwards, the number of shifts made, the element at one index afterwards.
    The list has 4 + level entries with repeated values."""
    xs, i, j, key, sh = names(r, 5)
    n = 4 + level
    vals = [r.randint(1, 3 * n) for _ in range(n)]
    k_rounds = n if r.random() < 0.2 else r.randint(2, n - 1)
    op = r.choice((">", "<", ">=", "<="))
    shape = r.choice(("list", "shifts", "at"))
    inner: list[list] = [["setidx", xs, B("+", V(j), N(1)), IDX(V(xs), V(j))], ["set", j, B("-", V(j), N(1))]]
    if shape == "shifts":
        inner.append(["aug", sh, "+", N(1)])
    body = [["set", key, IDX(V(xs), V(i))], ["set", j, B("-", V(i), N(1))],
            ["while", AND(C(">=", V(j), N(0)), C(op, IDX(V(xs), V(j)), V(key))), inner],
            ["setidx", xs, B("+", V(j), N(1)), V(key)]]
    prog: list[list] = [["set", xs, LIST(vals)]]
    if shape == "shifts":
        prog.append(["set", sh, N(0)])
    prog.append(["for", i, N(1), N(k_rounds), 1, body])
    prog.append(["print", {"list": V(xs), "shifts": V(sh), "at": IDX(V(xs), N(r.randrange(n)))}[shape]])
    return finish(prog)


@batch("swaps")
def partition_pass(level: int, r: random.Random) -> Built:
    """Lomuto partition around the last element of the first m entries (the pivot): i = -1; for j over the entries before the pivot, when
    xs[j] <= pivot (or < pivot, as the code states) do i += 1 and swap xs[i] with xs[j]; finally swap xs[i + 1] with the pivot. Shapes: the list
    afterwards, the sum of the positions j at which a swap was made inside the loop. The final position of the pivot is never asked (it is a
    count), and a draw whose list comes out unchanged is redrawn. 5 + level entries, m = the whole list or the first m_ >= 4."""
    xs, i, j, t, pv, tot = names(r, 6)
    n = 5 + level
    vals = [r.randint(1, 3 * n) for _ in range(n)]
    m = n if r.random() < 0.5 else r.randint(4, n)
    cmp_op = r.choice(("<=", "<"))
    shape = r.choice(("list", "list", "swapj"))
    after = vals[:]
    pv_v, bound = after[m - 1], -1
    for jj in range(m - 1):
        if (after[jj] <= pv_v) if cmp_op == "<=" else (after[jj] < pv_v):
            bound += 1
            after[bound], after[jj] = after[jj], after[bound]
    after[bound + 1], after[m - 1] = after[m - 1], after[bound + 1]
    if shape == "list" and after == vals:
        raise Retry  # an unchanged list would make 'echo the input' a correct answer
    swap = [["set", t, IDX(V(xs), V(i))], ["setidx", xs, V(i), IDX(V(xs), V(j))], ["setidx", xs, V(j), V(t)]]
    body_if: list[list] = [["aug", i, "+", N(1)], *swap]
    if shape == "swapj":
        body_if.append(["aug", tot, "+", V(j)])
    prog: list[list] = [["set", xs, LIST(vals)], ["set", pv, IDX(V(xs), N(m - 1))], ["set", i, N(-1)]]
    if shape == "swapj":
        prog.append(["set", tot, N(0)])
    prog.append(["for", j, N(0), N(m - 1), 1, [["if", C(cmp_op, IDX(V(xs), V(j)), V(pv)), body_if, []]]])
    prog += [["set", t, IDX(V(xs), B("+", V(i), N(1)))], ["setidx", xs, B("+", V(i), N(1)), V(pv)], ["setidx", xs, N(m - 1), V(t)]]
    prog.append(["print", V(xs) if shape == "list" else V(tot)])
    return finish(prog)
