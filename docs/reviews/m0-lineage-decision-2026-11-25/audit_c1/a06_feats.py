# ruff: noqa
"""Literal features of a C1 program read from the TREE in source (textual) order, mirroring what the author's
shortcut script reads from the rendered source with ast (incl. its quirk that a negative literal yields both -v and v,
and that `range(stop)` shows no start literal). Validated against an ast reading of the fixture questions (a06_validate)."""
from a02_myeval import to_str
from collections import Counter

_C = Counter()


def _lit_value(e):
    """literal_eval-able value of an expression node, else raise."""
    k = e[0]
    if k in ("n", "s"):
        return e[1]
    if k == "list":
        return [_lit_value(x) for x in e[1:]]
    raise ValueError


def facts(prog):
    nums, strs, lists = [], [], []

    def num(v):
        if v < 0:
            nums.extend([v, -v])
        else:
            nums.append(v)

    def ex(e):
        if e is None:
            return
        k = e[0]
        if k == "n":
            num(e[1])
        elif k == "s":
            strs.append(e[1])
        elif k == "v":
            pass
        elif k in ("b", "c"):
            ex(e[2]); ex(e[3])
        elif k in ("and", "or"):
            ex(e[1]); ex(e[2])
        elif k == "not":
            ex(e[1])
        elif k == "list":
            try:
                lists.append(_lit_value(e))
            except ValueError:
                pass
            for x in e[1:]:
                ex(x)
        elif k == "idx":
            ex(e[1]); ex(e[2])
        elif k == "slice":
            for x in e[1:]:
                ex(x)
        elif k == "call":
            for x in e[2:]:
                ex(x)
        elif k == "m":
            ex(e[1])
            for x in e[3:]:
                ex(x)

    def st(body):
        for s in body:
            k = s[0]
            if k == "set":
                ex(s[2])
            elif k == "aug":
                ex(s[3])
            elif k == "setidx":
                ex(s[2]); ex(s[3])
            elif k == "append":
                ex(s[2])
            elif k == "for":
                if not (s[2] == ["n", 0] and s[4] == 1):
                    ex(s[2])
                ex(s[3])
                if s[4] != 1:
                    num(s[4])
                st(s[5])
            elif k == "while":
                ex(s[1]); st(s[2])
            elif k == "if":
                ex(s[1]); st(s[2]); st(s[3])
            elif k == "def":
                st(s[3])
            elif k in ("ret", "print"):
                ex(s[1])

    st(prog)
    flat = [x for x in lists if x and all(isinstance(v, int) for v in x)]
    # echo: the printed expression is a bare name -> its first top-level assignment, if a literal
    echo = None
    pr = _find_print(prog)
    if pr is not None and pr[1][0] == "v":
        nm = pr[1][1]
        for s in prog:
            if s[0] == "set" and s[1] == nm:
                try:
                    echo = to_str(_lit_value(s[2]), _C)
                except ValueError:
                    echo = None
                break
    return {"nums": nums, "strs": strs, "lists": lists, "flat": flat, "echo": echo, "print": pr[1] if pr else None}


def _find_print(body):
    for s in body:
        if s[0] == "print":
            return s
        for sub in ([s[5]] if s[0] == "for" else [s[2]] if s[0] == "while" else [s[2], s[3]] if s[0] == "if" else [s[3]] if s[0] == "def" else []):
            p = _find_print(sub)
            if p is not None:
                return p
    return None
