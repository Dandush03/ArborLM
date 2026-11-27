# ruff: noqa
"""Auditor's OWN evaluator for the C1 program tree (independent of studies.m0.solvers_c1 and the generators).

Written from the grammar description in c1grammar.py's docstring and Python 3 semantics. It does not call exec/eval/compile.
It implements Python scoping (a name assigned anywhere in a function body is local; other names are read from globals),
in-place `+=` on lists, Python slice index adjustment (implemented here, not delegated to the host's slice), str/repr of
values, and records every construct used so the caller can compare with what the repo's second solver supports.

Also: ast_to_tree() converts the rendered question source (parsed with ast.parse, never executed) into the same tree
form, so the caller can check that the question shows exactly the structured program.
"""
from __future__ import annotations

import ast
from collections import Counter
from typing import Any

STEP_LIMIT = 5_000_000


class EvalError(Exception):
    pass


class _Ret(Exception):
    def __init__(self, v):
        self.v = v


def _pyrepr_str(s: str, hz: Counter) -> str:
    # Python repr for str: single quotes unless the string contains ' and no ".
    if any(ord(ch) < 32 or ord(ch) > 126 for ch in s) or "\\" in s:
        hz["repr_unusual_char"] += 1
    if "'" in s and '"' not in s:
        hz["repr_double_quote"] += 1
        return '"' + s + '"'
    if "'" in s:
        hz["repr_escaped_quote"] += 1
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return "'" + s.replace("\\", "\\\\") + "'"


def to_str(v: Any, hz: Counter) -> str:
    if v is True:
        hz["bool_printed"] += 1
        return "True"
    if v is False:
        hz["bool_printed"] += 1
        return "False"
    if v is None:
        hz["none_printed"] += 1
        return "None"
    if isinstance(v, int):
        # decimal by hand (independent of str(int))
        if v == 0:
            return "0"
        neg = v < 0
        x = -v if neg else v
        ds = []
        while x:
            ds.append("0123456789"[x % 10])
            x //= 10
        return ("-" if neg else "") + "".join(reversed(ds))
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "[" + ", ".join(_repr(x, hz) for x in v) + "]"
    raise EvalError(f"cannot print {type(v).__name__}")


def _repr(v: Any, hz: Counter) -> str:
    if isinstance(v, str):
        return _pyrepr_str(v, hz)
    return to_str(v, hz)


def _adjust_slice(n: int, a, b, c):
    """CPython PySlice_GetIndicesEx semantics, written out."""
    if c is None:
        c = 1
    if c == 0:
        raise EvalError("slice step 0")
    if c > 0:
        lo_def, hi_def = 0, n
    else:
        lo_def, hi_def = n - 1, -1
    def fix(x, default, is_start):
        if x is None:
            return default
        if x < 0:
            x += n
            if x < 0:
                x = 0 if c > 0 else -1
        elif x >= n:
            x = n if c > 0 else n - 1
        return x
    start = fix(a, lo_def, True)
    stop = fix(b, hi_def, False)
    idx = []
    i = start
    if c > 0:
        while i < stop:
            idx.append(i)
            i += c
    else:
        while i > stop:
            idx.append(i)
            i += c
    return idx


def _assigned_names(body: list) -> set:
    out = set()
    for st in body:
        k = st[0]
        if k in ("set", "aug"):
            out.add(st[1])
        elif k == "for":
            out.add(st[1])
            out |= _assigned_names(st[5])
        elif k == "while":
            out |= _assigned_names(st[2])
        elif k == "if":
            out |= _assigned_names(st[2]) | _assigned_names(st[3])
        elif k == "def":
            out.add(st[1])
    return out


class Machine:
    def __init__(self):
        self.g: dict[str, Any] = {}
        self.out: list[str] = []
        self.steps = 0
        self.depth = 0
        self.max_depth = 0
        self.used = Counter()  # constructs used
        self.hz = Counter()  # hazards

    def tick(self):
        self.steps += 1
        if self.steps > STEP_LIMIT:
            raise EvalError("step limit")

    # ---- names
    def load(self, name, loc):
        if loc is not None:
            env, local_names = loc
            if name in local_names:
                if name not in env:
                    raise EvalError(f"UnboundLocalError {name}")
                return env[name]
            if name in self.g:
                self.hz["function_reads_global"] += 1
                return self.g[name]
            raise EvalError(f"NameError {name}")
        if name not in self.g:
            raise EvalError(f"NameError {name}")
        return self.g[name]

    def store(self, name, v, loc):
        if loc is not None:
            loc[0][name] = v
        else:
            self.g[name] = v

    # ---- expressions
    def ev(self, e, loc):
        self.tick()
        k = e[0]
        self.used["expr:" + k] += 1
        if k == "n":
            if not isinstance(e[1], int) or isinstance(e[1], bool):
                raise EvalError("non-int literal")
            return e[1]
        if k == "s":
            if not isinstance(e[1], str):
                raise EvalError("non-str literal")
            return e[1]
        if k == "v":
            return self.load(e[1], loc)
        if k == "b":
            a = self.ev(e[2], loc)
            b = self.ev(e[3], loc)
            return self.binop(e[1], a, b)
        if k == "c":
            a = self.ev(e[2], loc)
            b = self.ev(e[3], loc)
            return self.cmp(e[1], a, b)
        if k == "and":
            a = self.ev(e[1], loc)
            if not self.truth(a):
                return a
            return self.ev(e[2], loc)
        if k == "or":
            a = self.ev(e[1], loc)
            if self.truth(a):
                return a
            return self.ev(e[2], loc)
        if k == "not":
            return not self.truth(self.ev(e[1], loc))
        if k == "list":
            return [self.ev(x, loc) for x in e[1:]]
        if k == "idx":
            obj = self.ev(e[1], loc)
            i = self.ev(e[2], loc)
            return self.index(obj, i)
        if k == "slice":
            obj = self.ev(e[1], loc)
            a = None if e[2] is None else self.ev(e[2], loc)
            b = None if e[3] is None else self.ev(e[3], loc)
            c = None if e[4] is None else self.ev(e[4], loc)
            for x in (a, b, c):
                if x is not None and (not isinstance(x, int) or isinstance(x, bool)):
                    raise EvalError("slice index type")
            if not isinstance(obj, (list, str)):
                raise EvalError("slice of non-sequence")
            if (a is not None and a < 0) or (b is not None and b < 0):
                self.hz["negative_slice_bound"] += 1
            if c is not None and c < 0:
                self.hz["negative_slice_step"] += 1
            idx = _adjust_slice(len(obj), a, b, c)
            if isinstance(obj, str):
                return "".join(obj[i] for i in idx)
            return [obj[i] for i in idx]
        if k == "call":
            name = e[1]
            args = [self.ev(x, loc) for x in e[2:]]
            fn = None
            # Python resolves the callee name like any name: local, then global, then builtin
            if loc is not None and name in loc[1]:
                raise EvalError("calling a local name")
            if name in self.g:
                fn = self.g[name]
                if not (isinstance(fn, tuple) and fn[0] == "fn"):
                    raise EvalError(f"call of non-function {name}")
                self.used["call:user"] += 1
                return self.call_user(fn, args)
            self.used["call:" + name] += 1
            return self.builtin(name, args)
        if k == "m":
            obj = self.ev(e[1], loc)
            args = [self.ev(x, loc) for x in e[3:]]
            self.used["method:" + e[2]] += 1
            return self.method(obj, e[2], args)
        raise EvalError(f"unknown expr {k}")

    def truth(self, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            self.hz["int_used_as_condition"] += 1
            return v != 0
        if isinstance(v, (str, list)):
            self.hz["seq_used_as_condition"] += 1
            return len(v) != 0
        raise EvalError("truth of unknown")

    def binop(self, op, a, b):
        self.used["op:" + op] += 1
        if isinstance(a, bool) or isinstance(b, bool):
            self.hz["bool_arithmetic"] += 1
        ints = isinstance(a, int) and isinstance(b, int)
        if op == "+":
            if ints:
                return a + b
            if isinstance(a, str) and isinstance(b, str):
                return a + b
            if isinstance(a, list) and isinstance(b, list):
                return a + b
            raise EvalError("TypeError +")
        if op == "-":
            if ints:
                return a - b
            raise EvalError("TypeError -")
        if op == "*":
            if ints:
                return a * b
            if isinstance(a, (str, list)) and isinstance(b, int) and not isinstance(b, bool):
                if b < 0:
                    self.hz["negative_repeat"] += 1
                return a * b if b > 0 else a[:0]
            if isinstance(b, (str, list)) and isinstance(a, int) and not isinstance(a, bool):
                return b * a if a > 0 else b[:0]
            raise EvalError("TypeError *")
        if op in ("//", "%"):
            if not ints:
                raise EvalError("TypeError " + op)
            if b == 0:
                raise EvalError("ZeroDivisionError")
            if (a < 0) != (b < 0) and a != 0:
                self.hz["floor_div_mixed_sign"] += 1
            # floor division written out: q = floor(a / b)
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0) and q * abs(b) != abs(a):
                q = -q - 1
            elif (a < 0) != (b < 0):
                q = -q
            if op == "//":
                return q
            return a - b * q
        raise EvalError("unknown op " + op)

    def cmp(self, op, a, b):
        num = lambda x: isinstance(x, int)
        if op in ("==", "!="):
            if type(a) is not type(b) and not (num(a) and num(b)):
                self.hz["cross_type_equality"] += 1
            r = a == b
            return r if op == "==" else not r
        ok = (num(a) and num(b)) or (isinstance(a, str) and isinstance(b, str)) or (isinstance(a, list) and isinstance(b, list))
        if not ok:
            raise EvalError("TypeError compare")
        if isinstance(a, list):
            self.hz["list_ordering_compare"] += 1
        if isinstance(a, str):
            self.hz["string_ordering_compare"] += 1
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    def index(self, obj, i):
        if not isinstance(i, int) or isinstance(i, bool):
            raise EvalError("index type")
        if not isinstance(obj, (list, str)):
            raise EvalError("index of non-sequence")
        n = len(obj)
        if i < 0:
            self.hz["negative_index_read"] += 1
            i += n
        if i < 0 or i >= n:
            raise EvalError("IndexError")
        return obj[i]

    def builtin(self, name, args):
        if name == "len":
            if len(args) != 1 or not isinstance(args[0], (list, str)):
                raise EvalError("len")
            return len(args[0])
        if name == "sum":
            if len(args) != 1 or not isinstance(args[0], list):
                raise EvalError("sum")
            t = 0
            for x in args[0]:
                if not isinstance(x, int):
                    raise EvalError("sum type")
                t = t + x
            return t
        if name in ("max", "min"):
            seq = args[0] if len(args) == 1 else args
            if not isinstance(seq, list) or not seq:
                raise EvalError(name)
            best = seq[0]
            for x in seq[1:]:
                if (self.cmp(">", x, best) if name == "max" else self.cmp("<", x, best)):
                    best = x
            return best
        if name == "abs":
            if len(args) != 1 or not isinstance(args[0], int):
                raise EvalError("abs")
            return -args[0] if args[0] < 0 else args[0]
        if name == "str":
            if len(args) != 1:
                raise EvalError("str")
            return to_str(args[0], self.hz)
        if name == "sorted":
            self.hz["uses_sorted"] += 1
            return sorted(args[0])
        if name == "range":
            self.hz["uses_range_call"] += 1
            raise EvalError("range value outside for")
        raise EvalError(f"NameError {name}")

    def method(self, obj, m, args):
        if not isinstance(obj, str):
            raise EvalError(f"method {m} on {type(obj).__name__}")
        if m == "upper":
            return "".join(chr(ord(c) - 32) if "a" <= c <= "z" else c for c in obj)
        if m == "lower":
            return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in obj)
        if m == "count":
            sub = args[0]
            if sub == "":
                return len(obj) + 1
            n = i = 0
            while True:
                j = obj.find(sub, i)
                if j < 0:
                    return n
                n += 1
                i = j + len(sub)
        if m == "replace":
            old, new = args[0], args[1]
            if old == "":
                raise EvalError("replace empty")
            out, i = [], 0
            while True:
                j = obj.find(old, i)
                if j < 0:
                    out.append(obj[i:])
                    return "".join(out)
                out.append(obj[i:j])
                out.append(new)
                i = j + len(old)
        raise EvalError(f"unsupported method {m}")

    def call_user(self, fn, args):
        _, params, body = fn
        if len(params) != len(args):
            raise EvalError("arity")
        env = dict(zip(params, args))
        local_names = set(params) | _assigned_names(body)
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        if self.depth > 900:
            raise EvalError("recursion depth")
        try:
            self.run(body, (env, local_names))
        except _Ret as r:
            return r.v
        finally:
            self.depth -= 1
        self.hz["function_falls_off_end"] += 1
        return None

    # ---- statements
    def run(self, body, loc):
        for st in body:
            self.tick()
            k = st[0]
            self.used["stmt:" + k] += 1
            if k == "set":
                self.store(st[1], self.ev(st[2], loc), loc)
            elif k == "aug":
                op = st[2]
                self.used["aug:" + op] += 1
                v = self.ev(st[3], loc)
                cur = self.load(st[1], loc)
                if isinstance(cur, list):
                    self.hz["aug_on_list"] += 1
                    if op == "+":
                        if not isinstance(v, list):
                            raise EvalError("list += non-list")
                        cur.extend(list(v))  # in place, like Python
                        continue
                    if op == "*":
                        n = len(cur)
                        cur[:] = cur * v if v > 0 else []
                        continue
                    raise EvalError("aug on list")
                self.store(st[1], self.binop(op, cur, v), loc)
            elif k == "setidx":
                obj = self.load(st[1], loc)
                i = self.ev(st[2], loc)
                v = self.ev(st[3], loc)
                if not isinstance(obj, list):
                    raise EvalError("setidx on non-list")
                if not isinstance(i, int) or isinstance(i, bool):
                    raise EvalError("setidx index type")
                n = len(obj)
                if i < 0:
                    self.hz["negative_index_write"] += 1
                    i += n
                if i < 0 or i >= n:
                    raise EvalError("IndexError setidx")
                obj[i] = v
            elif k == "append":
                obj = self.load(st[1], loc)
                if not isinstance(obj, list):
                    raise EvalError("append on non-list")
                obj.append(self.ev(st[2], loc))
            elif k == "for":
                lo = self.ev(st[2], loc)
                hi = self.ev(st[3], loc)
                step = st[4]
                for x in (lo, hi, step):
                    if not isinstance(x, int) or isinstance(x, bool):
                        raise EvalError("range arg type")
                if step == 0:
                    raise EvalError("range step 0")
                if step != 1:
                    self.used["for:step!=1"] += 1
                # materialise the range first (Python semantics: bounds evaluated once)
                vals = []
                i = lo
                while (i < hi) if step > 0 else (i > hi):
                    vals.append(i)
                    i += step
                for i in vals:
                    self.store(st[1], i, loc)
                    self.run(st[5], loc)
            elif k == "while":
                n_it = 0
                while self.truth(self.ev(st[1], loc)):
                    n_it += 1
                    self.run(st[2], loc)
            elif k == "if":
                if self.truth(self.ev(st[1], loc)):
                    self.run(st[2], loc)
                else:
                    self.run(st[3], loc)
            elif k == "def":
                if loc is not None:
                    self.hz["nested_def"] += 1
                self.store(st[1], ("fn", list(st[2]), st[3]), loc)
            elif k == "ret":
                if loc is None:
                    raise EvalError("return outside function")
                raise _Ret(self.ev(st[1], loc))
            elif k == "print":
                self.out.append(to_str(self.ev(st[1], loc), self.hz))
            else:
                raise EvalError(f"unknown stmt {k}")


def evaluate(prog):
    m = Machine()
    m.run(prog, None)
    if len(m.out) != 1:
        raise EvalError(f"printed {len(m.out)} lines")
    if "\n" in m.out[0]:
        raise EvalError("newline in output")
    return m.out[0], m


# ---------------- ast (parse only) -> tree
_BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//", ast.Mod: "%"}
_CMP = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}


class Unsupported(Exception):
    pass


def ax(e):
    if isinstance(e, ast.Constant):
        if isinstance(e.value, bool) or e.value is None:
            raise Unsupported("bool/None const")
        if isinstance(e.value, int):
            return ["n", e.value]
        if isinstance(e.value, str):
            return ["s", e.value]
        raise Unsupported("const " + type(e.value).__name__)
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub) and isinstance(e.operand, ast.Constant) and isinstance(e.operand.value, int):
        return ["n", -e.operand.value]
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
        return ["not", ax(e.operand)]
    if isinstance(e, ast.Name):
        return ["v", e.id]
    if isinstance(e, ast.BinOp):
        return ["b", _BIN[type(e.op)], ax(e.left), ax(e.right)]
    if isinstance(e, ast.Compare):
        if len(e.ops) != 1:
            raise Unsupported("chained compare")
        return ["c", _CMP[type(e.ops[0])], ax(e.left), ax(e.comparators[0])]
    if isinstance(e, ast.BoolOp):
        k = "and" if isinstance(e.op, ast.And) else "or"
        vals = [ax(v) for v in e.values]
        t = vals[0]
        for v in vals[1:]:
            t = [k, t, v]
        return t
    if isinstance(e, ast.List):
        return ["list", *[ax(x) for x in e.elts]]
    if isinstance(e, ast.Subscript):
        if isinstance(e.slice, ast.Slice):
            s = e.slice
            return ["slice", ax(e.value), None if s.lower is None else ax(s.lower), None if s.upper is None else ax(s.upper), None if s.step is None else ax(s.step)]
        return ["idx", ax(e.value), ax(e.slice)]
    if isinstance(e, ast.Call):
        if isinstance(e.func, ast.Name):
            return ["call", e.func.id, *[ax(a) for a in e.args]]
        if isinstance(e.func, ast.Attribute):
            return ["m", ax(e.func.value), e.func.attr, *[ax(a) for a in e.args]]
    raise Unsupported(type(e).__name__)


def _step_int(e):
    t = ax(e)
    if t[0] != "n":
        raise Unsupported("non-literal step")
    return t[1]


def astmts(body):
    out = []
    for st in body:
        if isinstance(st, ast.Assign):
            if len(st.targets) != 1:
                raise Unsupported("multi-assign")
            t = st.targets[0]
            if isinstance(t, ast.Name):
                out.append(["set", t.id, ax(st.value)])
            elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and not isinstance(t.slice, ast.Slice):
                out.append(["setidx", t.value.id, ax(t.slice), ax(st.value)])
            else:
                raise Unsupported("assign target")
        elif isinstance(st, ast.AugAssign):
            if not isinstance(st.target, ast.Name):
                raise Unsupported("aug target")
            out.append(["aug", st.target.id, _BIN[type(st.op)], ax(st.value)])
        elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            c = st.value
            if isinstance(c.func, ast.Name) and c.func.id == "print":
                if len(c.args) != 1:
                    raise Unsupported("print arity")
                out.append(["print", ax(c.args[0])])
            elif isinstance(c.func, ast.Attribute) and c.func.attr == "append" and isinstance(c.func.value, ast.Name):
                out.append(["append", c.func.value.id, ax(c.args[0])])
            else:
                raise Unsupported("expr stmt")
        elif isinstance(st, ast.For):
            if not (isinstance(st.iter, ast.Call) and isinstance(st.iter.func, ast.Name) and st.iter.func.id == "range" and isinstance(st.target, ast.Name)):
                raise Unsupported("for iter")
            a = st.iter.args
            if len(a) == 1:
                lo, hi, step = ["n", 0], ax(a[0]), 1
            elif len(a) == 2:
                lo, hi, step = ax(a[0]), ax(a[1]), 1
            else:
                lo, hi, step = ax(a[0]), ax(a[1]), _step_int(a[2])
            if st.orelse:
                raise Unsupported("for-else")
            out.append(["for", st.target.id, lo, hi, step, astmts(st.body)])
        elif isinstance(st, ast.While):
            if st.orelse:
                raise Unsupported("while-else")
            out.append(["while", ax(st.test), astmts(st.body)])
        elif isinstance(st, ast.If):
            out.append(["if", ax(st.test), astmts(st.body), astmts(st.orelse)])
        elif isinstance(st, ast.FunctionDef):
            out.append(["def", st.name, [a.arg for a in st.args.args], astmts(st.body)])
        elif isinstance(st, ast.Return):
            out.append(["ret", ax(st.value)])
        else:
            raise Unsupported(type(st).__name__)
    return out


def source_of_question(q: str) -> str:
    head = "Here is a Python program.\n\n"
    tail = "\n\nWhat exactly does it print? It prints a single line."
    if not (q.startswith(head) and q.endswith(tail)):
        raise Unsupported("question frame")
    return q[len(head): -len(tail)]


def tree_from_question(q: str):
    return astmts(ast.parse(source_of_question(q)).body)


# ---------------- canonical renaming (capacity)
_BUILTINS = {"len", "sum", "max", "min", "abs", "str", "sorted", "range", "print"}


def canonical(prog):
    names: dict[str, str] = {}

    def nm(x):
        if x not in names:
            names[x] = f"_{len(names)}"
        return names[x]

    def ce(e):
        if e is None:
            return None
        k = e[0]
        if k in ("n", "s"):
            return e
        if k == "v":
            return ["v", nm(e[1])]
        if k in ("b", "c"):
            return [k, e[1], ce(e[2]), ce(e[3])]
        if k in ("and", "or"):
            return [k, ce(e[1]), ce(e[2])]
        if k == "not":
            return [k, ce(e[1])]
        if k == "list":
            return ["list", *[ce(x) for x in e[1:]]]
        if k == "idx":
            return [k, ce(e[1]), ce(e[2])]
        if k == "slice":
            return [k, ce(e[1]), ce(e[2]), ce(e[3]), ce(e[4])]
        if k == "call":
            f = e[1] if e[1] in _BUILTINS else nm(e[1])
            return ["call", f, *[ce(x) for x in e[2:]]]
        if k == "m":
            return ["m", ce(e[1]), e[2], *[ce(x) for x in e[3:]]]
        raise ValueError(k)

    def cs(body):
        out = []
        for st in body:
            k = st[0]
            if k == "set":
                out.append([k, nm(st[1]), ce(st[2])])
            elif k == "aug":
                out.append([k, nm(st[1]), st[2], ce(st[3])])
            elif k == "setidx":
                out.append([k, nm(st[1]), ce(st[2]), ce(st[3])])
            elif k == "append":
                out.append([k, nm(st[1]), ce(st[2])])
            elif k == "for":
                out.append([k, nm(st[1]), ce(st[2]), ce(st[3]), st[4], cs(st[5])])
            elif k == "while":
                out.append([k, ce(st[1]), cs(st[2])])
            elif k == "if":
                out.append([k, ce(st[1]), cs(st[2]), cs(st[3])])
            elif k == "def":
                out.append([k, nm(st[1]), [nm(p) for p in st[2]], cs(st[3])])
            elif k in ("ret", "print"):
                out.append([k, ce(st[1])])
        return out

    return cs(prog)


SOLVER_SUPPORTED_CALLS = {"len", "sum", "max", "min", "abs", "str"}  # plus user functions
SOLVER_SUPPORTED_METHODS = {"upper", "lower", "replace", "count"}
SOLVER_SUPPORTED_AUG = {"+", "-", "*"}  # any other aug op is silently computed as '*' by solvers_c1


def construct_problems(prog) -> list[str]:
    """Constructs the repo's second solver (solvers_c1, read not imported) cannot handle or handles differently."""
    probs = []
    user = set()

    def walk_e(e):
        if e is None:
            return
        k = e[0]
        if k == "call":
            if e[1] not in user and e[1] not in SOLVER_SUPPORTED_CALLS:
                probs.append("call:" + e[1])
            for x in e[2:]:
                walk_e(x)
        elif k == "m":
            if e[2] not in SOLVER_SUPPORTED_METHODS:
                probs.append("method:" + e[2])
            walk_e(e[1])
            for x in e[3:]:
                walk_e(x)
        elif k in ("b", "c"):
            walk_e(e[2]); walk_e(e[3])
        elif k in ("and", "or"):
            walk_e(e[1]); walk_e(e[2])
        elif k == "not":
            walk_e(e[1])
        elif k == "list":
            for x in e[1:]:
                walk_e(x)
        elif k == "idx":
            walk_e(e[1]); walk_e(e[2])
        elif k == "slice":
            for x in e[1:]:
                walk_e(x)
        elif k in ("n", "s", "v"):
            pass
        else:
            probs.append("expr:" + str(k))

    def collect_defs(body):
        for st in body:
            if st[0] == "def":
                user.add(st[1])
            for sub in ([st[5]] if st[0] == "for" else [st[2]] if st[0] == "while" else [st[2], st[3]] if st[0] == "if" else [st[3]] if st[0] == "def" else []):
                collect_defs(sub)

    def walk_s(body):
        for st in body:
            k = st[0]
            if k == "set":
                walk_e(st[2])
            elif k == "aug":
                if st[2] not in SOLVER_SUPPORTED_AUG:
                    probs.append("aug:" + st[2])
                walk_e(st[3])
            elif k == "setidx":
                walk_e(st[2]); walk_e(st[3])
            elif k == "append":
                walk_e(st[2])
            elif k == "for":
                walk_e(st[2]); walk_e(st[3]); walk_s(st[5])
            elif k == "while":
                walk_e(st[1]); walk_s(st[2])
            elif k == "if":
                walk_e(st[1]); walk_s(st[2]); walk_s(st[3])
            elif k == "def":
                walk_s(st[3])
            elif k in ("ret", "print"):
                walk_e(st[1])
            else:
                probs.append("stmt:" + str(k))

    collect_defs(prog)
    walk_s(prog)
    return probs
