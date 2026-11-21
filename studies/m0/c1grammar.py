# ruff: noqa: E501
"""C1 (code tracing): the typed program grammar, its renderer, and the execution of generated programs.

A program is a list of statements in a small JSON-friendly tree (nested lists). The renderer turns it into Python
source. Programs are OUR generated code, never model-written. Execution here is by the locked interpreter with
restricted builtins; the independent second solver (``solvers_c1``) walks the tree without Python's ``exec``.

Expression nodes:  ["n", int] ["s", str] ["v", name] ["b", op, l, r] (+ - * // %) ["c", op, l, r] (< <= > >= == !=)
                   ["and", l, r] ["or", l, r] ["not", e] ["list", e...] ["idx", e, i] ["slice", e, a|None, b|None, c|None]
                   ["call", fname, args...] ["m", obj, method, args...]
Statement nodes:   ["set", name, e] ["aug", name, op, e] ["setidx", name, i, e] ["append", name, e]
                   ["for", var, start, stop, step(int), body] ["while", cond, body] ["if", cond, then, else] ["def", name, params, body]
                   ["ret", e] ["print", e]
"""

from __future__ import annotations

import builtins
import json
import subprocess
import sys
from typing import Any

PREC = {"or": 1, "and": 2, "not": 3, "c": 4, "+": 5, "-": 5, "*": 6, "//": 6, "%": 6}
BUILTINS_ALLOWED = ("len", "sum", "max", "min", "abs", "range", "sorted", "str")


def _prec(e: list) -> int:
    k = e[0]
    if k in ("or", "and", "not"):
        return PREC[k]
    if k == "c":
        return PREC["c"]
    if k == "b":
        return PREC[e[1]]
    if k == "n" and e[1] < 0:
        return 9
    return 10


def rexpr(e: list, parent: int = 0, right: bool = False) -> str:
    k = e[0]
    p = _prec(e)
    if k == "n":
        s = f"({e[1]})" if e[1] < 0 else str(e[1])
    elif k == "s":
        s = repr(e[1])
    elif k == "v":
        s = e[1]
    elif k == "b":
        s = f"{rexpr(e[2], p)} {e[1]} {rexpr(e[3], p, True)}"
    elif k == "c":
        s = f"{rexpr(e[2], p + 1)} {e[1]} {rexpr(e[3], p + 1)}"
    elif k in ("and", "or"):
        s = f"{rexpr(e[1], p)} {k} {rexpr(e[2], p, True)}"
    elif k == "not":
        s = f"not {rexpr(e[1], p)}"
    elif k == "list":
        s = "[" + ", ".join(rexpr(x) for x in e[1:]) + "]"
    elif k == "idx":
        s = f"{rexpr(e[1], 10)}[{rexpr(e[2])}]"
    elif k == "slice":
        a = "" if e[2] is None else rexpr(e[2])
        b = "" if e[3] is None else rexpr(e[3])
        c = "" if e[4] is None else rexpr(e[4])
        s = f"{rexpr(e[1], 10)}[{a}:{b}" + (f":{c}" if c else "") + "]"
    elif k == "call":
        s = f"{e[1]}(" + ", ".join(rexpr(x) for x in e[2:]) + ")"
    elif k == "m":
        s = f"{rexpr(e[1], 10)}.{e[2]}(" + ", ".join(rexpr(x) for x in e[3:]) + ")"
    else:
        raise ValueError(k)
    if p < parent or (p == parent and right and p < 10):
        return f"({s})"
    return s


def rstmts(body: list[list], ind: int = 0) -> list[str]:
    pad = "    " * ind
    out: list[str] = []
    for st in body:
        k = st[0]
        if k == "set":
            out.append(f"{pad}{st[1]} = {rexpr(st[2])}")
        elif k == "aug":
            out.append(f"{pad}{st[1]} {st[2]}= {rexpr(st[3])}")
        elif k == "setidx":
            out.append(f"{pad}{st[1]}[{rexpr(st[2])}] = {rexpr(st[3])}")
        elif k == "append":
            out.append(f"{pad}{st[1]}.append({rexpr(st[2])})")
        elif k == "for":
            rng = f"range({rexpr(st[3])})" if (st[2] == ["n", 0] and st[4] == 1) else (f"range({rexpr(st[2])}, {rexpr(st[3])})" if st[4] == 1 else f"range({rexpr(st[2])}, {rexpr(st[3])}, {st[4]})")
            out.append(f"{pad}for {st[1]} in {rng}:")
            out.extend(rstmts(st[5], ind + 1))
        elif k == "while":
            out.append(f"{pad}while {rexpr(st[1])}:")
            out.extend(rstmts(st[2], ind + 1))
        elif k == "if":
            out.append(f"{pad}if {rexpr(st[1])}:")
            out.extend(rstmts(st[2], ind + 1))
            els = st[3]
            while els and len(els) == 1 and els[0][0] == "if":
                out.append(f"{pad}elif {rexpr(els[0][1])}:")
                out.extend(rstmts(els[0][2], ind + 1))
                els = els[0][3]
            if els:
                out.append(f"{pad}else:")
                out.extend(rstmts(els, ind + 1))
        elif k == "def":
            out.append(f"{pad}def {st[1]}({', '.join(st[2])}):")
            out.extend(rstmts(st[3], ind + 1))
        elif k == "ret":
            out.append(f"{pad}return {rexpr(st[1])}")
        elif k == "print":
            out.append(f"{pad}print({rexpr(st[1])})")
        else:
            raise ValueError(k)
    return out


def render(prog: list[list]) -> str:
    return "\n".join(rstmts(prog))


class _Timeout(Exception):
    pass


def run_inprocess(src: str) -> str:
    """Run one generated program under restricted builtins and return what it printed (must be one line)."""
    buf: list[str] = []
    safe = {n: getattr(builtins, n) for n in BUILTINS_ALLOWED}

    def _print(*args: Any) -> None:
        buf.append(" ".join(str(a) for a in args))

    safe["print"] = _print
    exec(compile(src, "<c1>", "exec"), {"__builtins__": safe})  # noqa: S102
    if len(buf) != 1 or "\n" in buf[0]:
        raise ValueError(f"program must print exactly one line, printed {buf!r}")
    return buf[0]


_RUNNER = r"""
import builtins, json, resource, signal, sys
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
ALLOWED = ("len", "sum", "max", "min", "abs", "range", "sorted", "str")
def _alarm(signum, frame):
    raise TimeoutError("time limit")
signal.signal(signal.SIGALRM, _alarm)
srcs = json.load(sys.stdin)
res = []
for src in srcs:
    buf = []
    safe = {n: getattr(builtins, n) for n in ALLOWED}
    safe["print"] = lambda *a, _b=buf: _b.append(" ".join(str(x) for x in a))
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        exec(compile(src, "<c1>", "exec"), {"__builtins__": safe})
        signal.setitimer(signal.ITIMER_REAL, 0)
        if len(buf) != 1 or "\n" in buf[0]:
            res.append({"out": None, "err": "not exactly one line: %r" % (buf,)})
        else:
            res.append({"out": buf[0], "err": None})
    except BaseException as ex:
        signal.setitimer(signal.ITIMER_REAL, 0)
        res.append({"out": None, "err": type(ex).__name__ + ": " + str(ex)})
json.dump(res, sys.stdout)
"""


def run_isolated(sources: list[str], timeout_s: float = 600.0) -> list[dict[str, Any]]:
    """Run programs in a FRESH restricted interpreter process (``-I -S``, stdin/stdout JSON, per-program 2 s alarm,
    CPU rlimit). One fresh process per call (a batch); the gate calls it twice, so two separate processes.
    """
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-c", _RUNNER],
        input=json.dumps(sources),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
        env={"PYTHONHASHSEED": "0"},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"isolated runner failed: {proc.stderr[-500:]}")
    out: list[dict[str, Any]] = json.loads(proc.stdout)
    return out
