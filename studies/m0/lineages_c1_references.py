# ruff: noqa: E501
"""C1 batch 1, family "references" (new family): which names share one list.

Strict procedure: ``shared_lists`` tracking object identity through assignment, copying, mutation and function calls (a name bound to
another name's list sees later changes; a slice or a concatenation makes a new list; a function that mutates its parameter changes the
caller's list, one that rebinds its parameter does not).
"""

from __future__ import annotations

import random
from typing import Any

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1 import FUNCS
from studies.m0.lineages_c1_common import IDX, LIST, B, N, V, batch, finish, names


@batch("references")
def shared_lists(level: int, r: random.Random) -> Built:
    """Two or three list names, then 2 + level operations drawn from: ``b = a`` (same list), ``b = a[:]`` (copy), ``b = a + [v]`` (new list),
    ``b.append(v)``, ``b[i] = v``, ``b = bump(a, i, v)`` (a function that adds v to xs[i] IN the list it is given and returns that list), and
    ``b = grow(a, v)`` (a function that rebinds its parameter to xs + [v] and returns it). Shapes: one list, its sum, its length, one of
    its elements. The item is kept only when the true answer differs from the one a reader would get by treating every assignment and every
    argument as a fresh copy, so the sharing always matters."""
    pool = names(r, 6)
    k = r.randint(2, 3)
    lst = pool[:k]
    init = {n: [r.randint(1, 9) for _ in range(r.randint(2, 4))] for n in lst}
    real: dict[str, Any] = {n: list(v) for n, v in init.items()}
    naive: dict[str, Any] = {n: list(v) for n, v in init.items()}
    fparam, fi, fv = pool[3:6]
    f_bump, f_grow = r.sample(FUNCS, 2)
    stmts: list[list] = []
    used: set[str] = set()
    for _ in range(2 + level):
        kind = r.choice(("alias", "copy", "concat", "append", "setidx", "bump", "grow"))
        d, s = r.choice(lst), r.choice(lst)
        v = r.randint(1, 9)
        if kind == "alias":
            if d == s:
                raise Retry
            stmts.append(["set", d, V(s)])
            real[d], naive[d] = real[s], list(naive[s])
        elif kind == "copy":
            stmts.append(["set", d, ["slice", V(s), None, None, None]])
            real[d], naive[d] = list(real[s]), list(naive[s])
        elif kind == "concat":
            stmts.append(["set", d, B("+", V(s), LIST([v]))])
            real[d], naive[d] = real[s] + [v], naive[s] + [v]
        elif kind == "append":
            stmts.append(["append", d, N(v)])
            real[d].append(v)
            naive[d].append(v)
        elif kind == "setidx":
            i = r.randrange(len(real[d]))
            if i >= len(naive[d]):
                raise Retry
            stmts.append(["setidx", d, N(i), N(v)])
            real[d][i] = v
            naive[d][i] = v
        elif kind == "bump":
            i = r.randrange(min(len(real[s]), len(naive[s])))
            stmts.append(["set", d, ["call", f_bump, V(s), N(i), N(v)]])
            used.add("bump")
            real[s][i] += v
            real[d] = real[s]
            copy = list(naive[s])
            copy[i] += v
            naive[d] = copy
        else:
            stmts.append(["set", d, ["call", f_grow, V(s), N(v)]])
            used.add("grow")
            real[d] = real[s] + [v]
            naive[d] = naive[s] + [v]
    target = r.choice(lst)
    shape = r.choice(("list", "sum", "len", "at"))
    at = r.randrange(min(len(real[target]), len(naive[target])))

    def read(state: dict[str, Any]) -> str:
        t = state[target]
        return str({"list": t, "sum": sum(t), "len": len(t), "at": t[at]}[shape])

    if read(real) == read(naive):
        raise Retry
    defs: list[list] = []
    if "bump" in used:
        defs.append(["def", f_bump, [fparam, fi, fv], [["setidx", fparam, V(fi), B("+", IDX(V(fparam), V(fi)), V(fv))], ["ret", V(fparam)]]])
    if "grow" in used:
        defs.append(["def", f_grow, [fparam, fv], [["set", fparam, B("+", V(fparam), ["list", V(fv)])], ["ret", V(fparam)]]])
    final = {"list": V(target), "sum": ["call", "sum", V(target)], "len": ["call", "len", V(target)], "at": IDX(V(target), N(at))}[shape]
    prog = [*defs, *[["set", n, LIST(init[n])] for n in lst], *stmts, ["print", final]]
    return finish(prog)
