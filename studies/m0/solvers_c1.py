# ruff: noqa: E501
"""Independent second solver for C1: a tree-walking interpreter over the program tree.

It never calls ``exec``, ``eval`` or ``compile`` and imports nothing from the generator or the renderer. It
reads the structured form (the tree) only. Functions run in their own scope (parameters and locals only), so a
generator bug that reads a global inside a function makes the two solvers disagree. Written by the implementer,
not by a separate auditor context: ruling needed 3.
"""

from __future__ import annotations

from typing import Any

STEP_LIMIT = 2_000_000


class _Return(Exception):
    def __init__(self, v: Any) -> None:
        self.v = v


class _Interp:
    def __init__(self) -> None:
        self.funcs: dict[str, tuple[list[str], list]] = {}
        self.out: list[str] = []
        self.steps = 0

    def tick(self) -> None:
        self.steps += 1
        if self.steps > STEP_LIMIT:
            raise RuntimeError("step limit")

    def ev(self, e: list, env: dict[str, Any]) -> Any:
        self.tick()
        k = e[0]
        if k in ("n", "s"):
            return e[1]
        if k == "v":
            return env[e[1]]
        if k == "b":
            a, b = self.ev(e[2], env), self.ev(e[3], env)
            op = e[1]
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "//":
                return a // b
            if op == "%":
                return a % b
            raise ValueError(op)
        if k == "c":
            a, b = self.ev(e[2], env), self.ev(e[3], env)
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[e[1]]
        if k == "and":
            return self.ev(e[1], env) and self.ev(e[2], env)
        if k == "or":
            return self.ev(e[1], env) or self.ev(e[2], env)
        if k == "not":
            return not self.ev(e[1], env)
        if k == "list":
            return [self.ev(x, env) for x in e[1:]]
        if k == "idx":
            return self.ev(e[1], env)[self.ev(e[2], env)]
        if k == "slice":
            obj = self.ev(e[1], env)
            a = None if e[2] is None else self.ev(e[2], env)
            b = None if e[3] is None else self.ev(e[3], env)
            c = None if e[4] is None else self.ev(e[4], env)
            return obj[slice(a, b, c)]
        if k == "call":
            args = [self.ev(x, env) for x in e[2:]]
            name = e[1]
            if name in self.funcs:
                params, body = self.funcs[name]
                local = dict(zip(params, args, strict=True))
                try:
                    self.run(body, local)
                except _Return as r:
                    return r.v
                return None
            if name == "len":
                return len(args[0])
            if name == "sum":
                t = 0
                for v in args[0]:
                    t += v
                return t
            if name == "max":
                return max(args[0]) if len(args) == 1 else max(args)
            if name == "min":
                return min(args[0]) if len(args) == 1 else min(args)
            if name == "abs":
                return -args[0] if args[0] < 0 else args[0]
            if name == "str":
                return str(args[0])
            raise ValueError(f"unknown function {name}")
        if k == "m":
            obj = self.ev(e[1], env)
            args = [self.ev(x, env) for x in e[3:]]
            m = e[2]
            if m == "upper":
                return obj.upper()
            if m == "lower":
                return obj.lower()
            if m == "replace":
                return obj.replace(args[0], args[1])
            if m == "count":
                return obj.count(args[0])
            raise ValueError(m)
        raise ValueError(k)

    def run(self, body: list, env: dict[str, Any]) -> None:
        for st in body:
            self.tick()
            k = st[0]
            if k == "set":
                env[st[1]] = self.ev(st[2], env)
            elif k == "aug":
                v = self.ev(st[3], env)
                cur = env[st[1]]
                env[st[1]] = cur + v if st[2] == "+" else (cur - v if st[2] == "-" else cur * v)
            elif k == "setidx":
                env[st[1]][self.ev(st[2], env)] = self.ev(st[3], env)
            elif k == "append":
                env[st[1]].append(self.ev(st[2], env))
            elif k == "for":
                lo, hi = self.ev(st[2], env), self.ev(st[3], env)
                i = lo
                while (i < hi) if st[4] > 0 else (i > hi):
                    env[st[1]] = i
                    self.run(st[5], env)
                    i += st[4]
            elif k == "while":
                while self.ev(st[1], env):
                    self.run(st[2], env)
            elif k == "if":
                self.run(st[2] if self.ev(st[1], env) else st[3], env)
            elif k == "def":
                self.funcs[st[1]] = (st[2], st[3])
            elif k == "ret":
                raise _Return(self.ev(st[1], env))
            elif k == "print":
                self.out.append(self.show(self.ev(st[1], env)))
            else:
                raise ValueError(k)

    def show(self, v: Any) -> str:
        if isinstance(v, bool):
            return "True" if v else "False"
        if isinstance(v, list):
            return "[" + ", ".join(self.show_inner(x) for x in v) + "]"
        return str(v)

    def show_inner(self, v: Any) -> str:
        if isinstance(v, str):
            return "'" + v + "'"  # generated strings never contain quotes
        return self.show(v)


def c1_trace(s: dict[str, Any]) -> str:
    it = _Interp()
    it.run(s["program"], {})
    if len(it.out) != 1:
        raise ValueError(f"expected one printed line, got {it.out!r}")
    return it.out[0]


SOLVERS = {f"C1.{n}": c1_trace for n in (
    "loop_sum", "while_counter", "string_build", "string_methods", "func_branch", "func_compose", "list_build", "counter_list",
    "nested_pairs", "bubble_pass", "cond_chain", "minmax_track", "slices", "fib_like")}
