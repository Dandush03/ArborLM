"""Second solver for the 26 C1 (code tracing) lineages of M0.

Written by an independent auditor context from the answer-free fixtures only.

Approach: a tree-walking interpreter written here. The program source is
taken from the question text and parsed with the standard `ast` module
(parsing only; the host interpreter never executes item code: no exec, eval,
compile-and-run, runpy or subprocess). Every node type the interpreter meets
is dispatched explicitly; any node, operator, builtin or method that it does
not implement raises `Unsupported` naming the construct.

A secondary front end (`structured_to_ast`) converts the `structured`
program tree into `ast` nodes so that the same interpreter can be run on it;
`run_solver2.py` uses it only as a consistency check between the two forms.
The answer returned by `SOLVERS[...]` is always from the question text.

Standard library only. No randomness, no file or network access.
"""

from __future__ import annotations

import ast
import sys

PREFIX = "Here is a Python program.\n\n"
SUFFIX = "\n\nWhat exactly does it print? It prints a single line."

MAX_STEPS = 5_000_000        # guard against non-terminating loops
MAX_CALL_DEPTH = 900         # CPython's default recursion limit is 1000 frames
INT_STR_MAX_DIGITS = 4300    # CPython's default int->str digit limit


class Unsupported(Exception):
    """A construct the interpreter deliberately does not implement."""


class ItemRuntimeError(Exception):
    """A run-time error the real program would also raise (e.g. IndexError)."""


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class RangeObj:
    __slots__ = ("start", "stop", "step")

    def __init__(self, start, stop, step):
        self.start, self.stop, self.step = start, stop, step

    def values(self):
        i = self.start
        if self.step > 0:
            while i < self.stop:
                yield i
                i += self.step
        else:
            while i > self.stop:
                yield i
                i += self.step


class Function:
    __slots__ = ("name", "params", "body", "local_names")

    def __init__(self, name, params, body, local_names):
        self.name, self.params, self.body, self.local_names = name, params, body, local_names


class Builtin:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


_UNBOUND = object()

# ---------------------------------------------------------------- value helpers


def is_int(x):
    # bool is an int subtype in Python: True == 1, False == 0 in arithmetic.
    return isinstance(x, int)


def as_int(x):
    return 1 if x is True else 0 if x is False else x


def type_name(x):
    if isinstance(x, bool):
        return "bool"
    if isinstance(x, int):
        return "int"
    if isinstance(x, str):
        return "str"
    if isinstance(x, list):
        return "list"
    if x is None:
        return "NoneType"
    if isinstance(x, RangeObj):
        return "range"
    if isinstance(x, (Function, Builtin)):
        return "function"
    return type(x).__name__


def truthy(x):
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return x != 0
    if isinstance(x, (str, list)):
        return len(x) > 0
    if isinstance(x, (Function, Builtin, RangeObj)):
        return True if not isinstance(x, RangeObj) else any(True for _ in x.values())
    raise Unsupported("truth value of " + type_name(x))


def floordiv(a, b):
    """Python floor division on ints, done from non-negative magnitudes."""
    a, b = as_int(a), as_int(b)
    if b == 0:
        raise ItemRuntimeError("ZeroDivisionError: integer division or modulo by zero")
    qa, qb = (a if a >= 0 else -a), (b if b >= 0 else -b)
    q = qa // qb            # magnitude quotient, both operands non-negative
    exact = q * qb == qa
    if (a < 0) != (b < 0):  # signs differ: true quotient negative -> floor rounds away from zero
        q = -q if exact else -q - 1
    return q


def mod(a, b):
    """Python modulo: a - b * floor(a / b); result has the divisor's sign."""
    a, b = as_int(a), as_int(b)
    return a - b * floordiv(a, b)


def int_to_str(n):
    n = as_int(n)
    if n == 0:
        return "0"
    neg = n < 0
    m = -n if neg else n
    digits = []
    while m > 0:
        digits.append("0123456789"[m % 10])
        m //= 10
    if len(digits) > INT_STR_MAX_DIGITS:
        raise ItemRuntimeError("ValueError: int too large to convert to str")
    return ("-" if neg else "") + "".join(reversed(digits))


def str_repr(s):
    """Python repr of a str: single quotes unless it has ' and no "."""
    q = '"' if ("'" in s and '"' not in s) else "'"
    out = [q]
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == q:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            raise Unsupported("repr of non-printable/non-ASCII character %r" % ch)
    out.append(q)
    return "".join(out)


def render_repr(x, active=None):
    if isinstance(x, bool):
        return "True" if x else "False"
    if isinstance(x, int):
        return int_to_str(x)
    if isinstance(x, str):
        return str_repr(x)
    if x is None:
        return "None"
    if isinstance(x, list):
        active = set() if active is None else active
        if id(x) in active:
            return "[...]"
        active.add(id(x))
        try:
            return "[" + ", ".join(render_repr(e, active) for e in x) + "]"
        finally:
            active.discard(id(x))
    raise Unsupported("rendering of " + type_name(x))


def render_str(x):
    """What str(x) / print(x) shows: strings bare, everything else as repr."""
    if isinstance(x, str):
        return x
    return render_repr(x)


def eq(a, b):
    if is_int(a) and is_int(b):
        return as_int(a) == as_int(b)
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        if a is b:
            return True
        if len(a) != len(b):
            return False
        return all(eq(x, y) for x, y in zip(a, b))
    if a is None or b is None:
        return a is b
    if isinstance(a, (Function, Builtin)) or isinstance(b, (Function, Builtin)):
        return a is b
    if type_name(a) != type_name(b) and not (is_int(a) and is_int(b)):
        return False
    raise Unsupported("== between %s and %s" % (type_name(a), type_name(b)))


def less(a, b):
    """a < b with Python's ordering for ints, strs (code points) and lists."""
    if is_int(a) and is_int(b):
        return as_int(a) < as_int(b)
    if isinstance(a, str) and isinstance(b, str):
        for x, y in zip(a, b):
            if x != y:
                return ord(x) < ord(y)
        return len(a) < len(b)
    if isinstance(a, list) and isinstance(b, list):
        for x, y in zip(a, b):
            if not eq(x, y):
                return less(x, y)
        return len(a) < len(b)
    raise ItemRuntimeError("TypeError: '<' not supported between %s and %s" % (type_name(a), type_name(b)))


def compare(op, a, b):
    if isinstance(op, ast.Eq):
        return eq(a, b)
    if isinstance(op, ast.NotEq):
        return not eq(a, b)
    if isinstance(op, ast.Lt):
        return less(a, b)
    if isinstance(op, ast.Gt):
        return less(b, a)
    if isinstance(op, ast.LtE):
        # for the types supported here, a <= b is (a < b) or (a == b)
        return less(a, b) or eq(a, b)
    if isinstance(op, ast.GtE):
        return less(b, a) or eq(a, b)
    raise Unsupported("comparison operator " + type(op).__name__)


def binop(op, a, b):
    if isinstance(op, ast.Add):
        if is_int(a) and is_int(b):
            return as_int(a) + as_int(b)
        if isinstance(a, str) and isinstance(b, str):
            return a + b
        if isinstance(a, list) and isinstance(b, list):
            return list(a) + list(b)       # a new list; operands untouched
        raise ItemRuntimeError("TypeError: + between %s and %s" % (type_name(a), type_name(b)))
    if isinstance(op, ast.Sub):
        if is_int(a) and is_int(b):
            return as_int(a) - as_int(b)
        raise ItemRuntimeError("TypeError: - between %s and %s" % (type_name(a), type_name(b)))
    if isinstance(op, ast.Mult):
        if is_int(a) and is_int(b):
            return as_int(a) * as_int(b)
        if isinstance(a, (str, list)) and is_int(b):
            return repeat(a, as_int(b))
        if is_int(a) and isinstance(b, (str, list)):
            return repeat(b, as_int(a))
        raise ItemRuntimeError("TypeError: * between %s and %s" % (type_name(a), type_name(b)))
    if isinstance(op, ast.FloorDiv):
        if is_int(a) and is_int(b):
            return floordiv(a, b)
        raise ItemRuntimeError("TypeError: // between %s and %s" % (type_name(a), type_name(b)))
    if isinstance(op, ast.Mod):
        if is_int(a) and is_int(b):
            return mod(a, b)
        raise Unsupported("% on " + type_name(a) + " (string formatting)")
    raise Unsupported("binary operator " + type(op).__name__)


def repeat(seq, n):
    if isinstance(seq, str):
        return "".join(seq for _ in range(n)) if n > 0 else ""
    out = []
    for _ in range(n):
        out.extend(seq)             # shallow: the same element objects repeat
    return out


def norm_index(seq, i):
    if not is_int(i):
        raise ItemRuntimeError("TypeError: indices must be integers, not " + type_name(i))
    i = as_int(i)
    n = len(seq)
    j = i + n if i < 0 else i
    if j < 0 or j >= n:
        raise ItemRuntimeError("IndexError: index %d out of range for length %d" % (i, n))
    return j


def slice_positions(n, lo, hi, st):
    """Positions selected by seq[lo:hi:st] on a length-n sequence (CPython's
    PySlice_AdjustIndices, written out)."""
    for v in (lo, hi, st):
        if v is not None and not is_int(v):
            raise ItemRuntimeError("TypeError: slice indices must be integers or None")
    step = 1 if st is None else as_int(st)
    if step == 0:
        raise ItemRuntimeError("ValueError: slice step cannot be zero")

    def adjust(v, default):
        if v is None:
            return default
        v = as_int(v)
        if v < 0:
            v += n
            if v < 0:
                v = -1 if step < 0 else 0
        elif v >= n:
            v = n - 1 if step < 0 else n
        return v

    if step > 0:
        start, stop = adjust(lo, 0), adjust(hi, n)
    else:
        start, stop = adjust(lo, n - 1), adjust(hi, -1)
    pos = []
    i = start
    if step > 0:
        while i < stop:
            pos.append(i)
            i += step
    else:
        while i > stop:
            pos.append(i)
            i += step
    return pos


def do_slice(seq, lo, hi, st):
    if isinstance(seq, str):
        return "".join(seq[p] for p in slice_positions(len(seq), lo, hi, st))
    if isinstance(seq, list):
        return [seq[p] for p in slice_positions(len(seq), lo, hi, st)]
    raise ItemRuntimeError("TypeError: %s is not sliceable" % type_name(seq))


def ascii_lower(s):
    out = []
    for ch in s:
        if "A" <= ch <= "Z":
            out.append(chr(ord(ch) + 32))
        elif ord(ch) < 128:
            out.append(ch)
        else:
            raise Unsupported("lower() on non-ASCII character")
    return "".join(out)


def ascii_upper(s):
    out = []
    for ch in s:
        if "a" <= ch <= "z":
            out.append(chr(ord(ch) - 32))
        elif ord(ch) < 128:
            out.append(ch)
        else:
            raise Unsupported("upper() on non-ASCII character")
    return "".join(out)


def str_replace(s, old, new):
    """str.replace(old, new) with no count: left-to-right, non-overlapping."""
    if old == "":
        # Python inserts `new` before every character and at the end.
        return new + "".join(ch + new for ch in s)
    out = []
    i, k = 0, len(old)
    while i < len(s):
        if s[i:i + k] == old:
            out.append(new)
            i += k
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


# ---------------------------------------------------------------- interpreter

BUILTIN_NAMES = ("print", "len", "str", "range", "sum", "max", "min", "abs", "sorted")


def local_names_of(fn: ast.FunctionDef):
    """Names local to a function: its parameters and every name it binds
    (assignment, augmented assignment, for target, nested def), excluding
    names bound inside nested function bodies."""
    names = [a.arg for a in fn.args.args]
    stack = list(fn.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            raise Unsupported(type(n).__name__ + " statement")
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            names.append(n.target.id)
        elif isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            names.append(n.target.id)
        elif isinstance(n, ast.FunctionDef):
            names.append(n.name)
            continue
        if isinstance(n, ast.NamedExpr):
            raise Unsupported("walrus operator")
        stack.extend(ast.iter_child_nodes(n))
    return frozenset(names)


class Interp:
    def __init__(self):
        self.globals = {}
        self.lines = []
        self.steps = 0
        self.depth = 0

    # -- scopes: frame is None at module level, else (Function, locals dict)
    def lookup(self, name, frame):
        if frame is not None and name in frame[0].local_names:
            v = frame[1].get(name, _UNBOUND)
            if v is _UNBOUND:
                raise ItemRuntimeError("UnboundLocalError: " + name)
            return v
        if name in self.globals:
            return self.globals[name]
        if name in BUILTIN_NAMES:
            return Builtin(name)
        raise ItemRuntimeError("NameError: " + name)

    def bind(self, name, value, frame):
        if frame is None:
            self.globals[name] = value
        else:
            frame[1][name] = value

    def tick(self):
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise Unsupported("step limit exceeded (possible non-terminating program)")

    # -- statements
    def exec_block(self, stmts, frame):
        for s in stmts:
            self.exec_stmt(s, frame)

    def exec_stmt(self, s, frame):
        self.tick()
        if isinstance(s, ast.Assign):
            if len(s.targets) != 1:
                raise Unsupported("chained assignment a = b = ...")
            value = self.eval(s.value, frame)          # right side first
            t = s.targets[0]
            if isinstance(t, ast.Name):
                self.bind(t.id, value, frame)          # names bind to objects: lists alias
            elif isinstance(t, ast.Subscript):
                if isinstance(t.slice, ast.Slice):
                    raise Unsupported("slice assignment")
                container = self.eval(t.value, frame)  # then container, then index
                index = self.eval(t.slice, frame)
                if not isinstance(container, list):
                    raise ItemRuntimeError("TypeError: item assignment on " + type_name(container))
                container[norm_index(container, index)] = value
            else:
                raise Unsupported("assignment target " + type(t).__name__)
        elif isinstance(s, ast.AugAssign):
            if not isinstance(s.target, ast.Name):
                raise Unsupported("augmented assignment target " + type(s.target).__name__)
            cur = self.lookup(s.target.id, frame)      # target loaded first
            rhs = self.eval(s.value, frame)
            if isinstance(cur, list) and isinstance(s.op, ast.Add):
                # list += iterable extends the SAME list object in place (aliases see it)
                if isinstance(rhs, list):
                    cur.extend(list(rhs))
                elif isinstance(rhs, str):
                    cur.extend(ch for ch in rhs)
                else:
                    raise ItemRuntimeError("TypeError: list += " + type_name(rhs))
                new = cur
            elif isinstance(cur, list) and isinstance(s.op, ast.Mult):
                raise Unsupported("list *= (in-place repeat)")
            else:
                new = binop(s.op, cur, rhs)
            self.bind(s.target.id, new, frame)
        elif isinstance(s, ast.Expr):
            self.eval(s.value, frame)
        elif isinstance(s, ast.If):
            if truthy(self.eval(s.test, frame)):
                self.exec_block(s.body, frame)
            else:
                self.exec_block(s.orelse, frame)
        elif isinstance(s, ast.While):
            if s.orelse:
                raise Unsupported("while ... else")
            while truthy(self.eval(s.test, frame)):
                self.tick()
                self.exec_block(s.body, frame)
        elif isinstance(s, ast.For):
            if s.orelse:
                raise Unsupported("for ... else")
            if not isinstance(s.target, ast.Name):
                raise Unsupported("for target " + type(s.target).__name__)
            it = self.eval(s.iter, frame)
            if not isinstance(it, RangeObj):
                raise Unsupported("for loop over " + type_name(it) + " (only range is implemented)")
            for v in it.values():                      # range evaluated once, before the loop
                self.tick()
                self.bind(s.target.id, v, frame)       # loop variable keeps last value afterwards
                self.exec_block(s.body, frame)
        elif isinstance(s, ast.FunctionDef):
            a = s.args
            if (s.decorator_list or a.defaults or a.kw_defaults or a.vararg or a.kwarg
                    or a.kwonlyargs or a.posonlyargs or s.returns is not None):
                raise Unsupported("function definition feature beyond plain positional parameters")
            self.bind(s.name, Function(s.name, [x.arg for x in a.args], s.body, local_names_of(s)), frame)
        elif isinstance(s, ast.Return):
            if frame is None:
                raise Unsupported("return outside function")
            raise _Return(None if s.value is None else self.eval(s.value, frame))
        elif isinstance(s, ast.Pass):
            pass
        else:
            raise Unsupported("statement " + type(s).__name__)

    # -- expressions
    def eval(self, e, frame):
        if isinstance(e, ast.Constant):
            v = e.value
            if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
                return v
            raise Unsupported("constant of type " + type(v).__name__)
        if isinstance(e, ast.Name):
            return self.lookup(e.id, frame)
        if isinstance(e, ast.List):
            return [self.eval(x, frame) for x in e.elts]   # a fresh list object each time
        if isinstance(e, ast.UnaryOp):
            v = self.eval(e.operand, frame)
            if isinstance(e.op, ast.USub):
                if is_int(v):
                    return -as_int(v)
                raise ItemRuntimeError("TypeError: unary - on " + type_name(v))
            if isinstance(e.op, ast.UAdd):
                if is_int(v):
                    return as_int(v)
                raise ItemRuntimeError("TypeError: unary + on " + type_name(v))
            if isinstance(e.op, ast.Not):
                return not truthy(v)
            raise Unsupported("unary operator " + type(e.op).__name__)
        if isinstance(e, ast.BinOp):
            a = self.eval(e.left, frame)
            b = self.eval(e.right, frame)
            return binop(e.op, a, b)
        if isinstance(e, ast.BoolOp):
            # short-circuit; the result is an operand, not a forced bool
            v = self.eval(e.values[0], frame)
            for nxt in e.values[1:]:
                if isinstance(e.op, ast.And):
                    if not truthy(v):
                        return v
                elif isinstance(e.op, ast.Or):
                    if truthy(v):
                        return v
                else:
                    raise Unsupported("boolean operator " + type(e.op).__name__)
                v = self.eval(nxt, frame)
            return v
        if isinstance(e, ast.Compare):
            # chained: a < b < c  ==  (a < b) and (b < c), b evaluated once, stop at first False
            left = self.eval(e.left, frame)
            for op, rnode in zip(e.ops, e.comparators):
                right = self.eval(rnode, frame)
                if isinstance(op, (ast.In, ast.NotIn, ast.Is, ast.IsNot)):
                    raise Unsupported("comparison operator " + type(op).__name__)
                if not compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(e, ast.Subscript):
            obj = self.eval(e.value, frame)
            if isinstance(e.slice, ast.Slice):
                lo = None if e.slice.lower is None else self.eval(e.slice.lower, frame)
                hi = None if e.slice.upper is None else self.eval(e.slice.upper, frame)
                st = None if e.slice.step is None else self.eval(e.slice.step, frame)
                return do_slice(obj, lo, hi, st)
            if isinstance(e.slice, ast.Tuple):
                raise Unsupported("tuple subscript")
            i = self.eval(e.slice, frame)
            if isinstance(obj, (list, str)):
                return obj[norm_index(obj, i)]
            raise ItemRuntimeError("TypeError: %s is not subscriptable" % type_name(obj))
        if isinstance(e, ast.Call):
            if e.keywords:
                raise Unsupported("keyword arguments in a call")
            if any(isinstance(a, ast.Starred) for a in e.args):
                raise Unsupported("starred arguments")
            if isinstance(e.func, ast.Attribute):
                obj = self.eval(e.func.value, frame)
                args = [self.eval(a, frame) for a in e.args]
                return self.call_method(obj, e.func.attr, args)
            fn = self.eval(e.func, frame)
            args = [self.eval(a, frame) for a in e.args]
            return self.call(fn, args)
        raise Unsupported("expression " + type(e).__name__)

    def call_method(self, obj, name, args):
        if isinstance(obj, list) and name == "append":
            if len(args) != 1:
                raise ItemRuntimeError("TypeError: append takes one argument")
            obj.append(args[0])            # mutates the shared list object
            return None
        if isinstance(obj, str) and name == "lower" and not args:
            return ascii_lower(obj)
        if isinstance(obj, str) and name == "upper" and not args:
            return ascii_upper(obj)
        if isinstance(obj, str) and name == "replace" and len(args) == 2:
            if not (isinstance(args[0], str) and isinstance(args[1], str)):
                raise ItemRuntimeError("TypeError: replace arguments must be str")
            return str_replace(obj, args[0], args[1])
        raise Unsupported("method %s.%s with %d argument(s)" % (type_name(obj), name, len(args)))

    def call(self, fn, args):
        if isinstance(fn, Builtin):
            return self.call_builtin(fn.name, args)
        if isinstance(fn, Function):
            if len(args) != len(fn.params):
                raise ItemRuntimeError("TypeError: %s takes %d arguments" % (fn.name, len(fn.params)))
            self.depth += 1
            if self.depth > MAX_CALL_DEPTH:
                raise Unsupported("call depth over %d (CPython would hit its recursion limit)" % MAX_CALL_DEPTH)
            frame = (fn, dict(zip(fn.params, args)))   # arguments bind to the caller's objects
            try:
                self.exec_block(fn.body, frame)
                result = None                          # falling off the end returns None
            except _Return as r:
                result = r.value
            finally:
                self.depth -= 1
            return result
        raise ItemRuntimeError("TypeError: %s is not callable" % type_name(fn))

    def call_builtin(self, name, args):
        if name == "print":
            self.lines.append(" ".join(render_str(a) for a in args))
            return None
        if name == "len":
            self._arity(name, args, 1)
            if isinstance(args[0], (str, list)):
                return len(args[0])
            raise ItemRuntimeError("TypeError: len of " + type_name(args[0]))
        if name == "str":
            self._arity(name, args, 1)
            return render_str(args[0])
        if name == "range":
            if not 1 <= len(args) <= 3 or not all(is_int(a) for a in args):
                raise ItemRuntimeError("TypeError: bad range arguments")
            a = [as_int(x) for x in args]
            start, stop, step = (0, a[0], 1) if len(a) == 1 else (a[0], a[1], a[2] if len(a) == 3 else 1)
            if step == 0:
                raise ItemRuntimeError("ValueError: range() arg 3 must not be zero")
            return RangeObj(start, stop, step)
        if name == "sum":
            self._arity(name, args, 1)
            if not isinstance(args[0], list):
                raise Unsupported("sum over " + type_name(args[0]))
            total = 0
            for x in args[0]:
                if not is_int(x):
                    raise ItemRuntimeError("TypeError: sum of " + type_name(x))
                total = total + as_int(x)
            return total
        if name in ("max", "min"):
            items = args[0] if len(args) == 1 else args
            if len(args) == 1 and not isinstance(items, list):
                raise Unsupported(name + " over " + type_name(items))
            if not items:
                raise ItemRuntimeError("ValueError: %s of empty sequence" % name)
            best = items[0]
            for x in items[1:]:
                # keep the first of equal elements, as CPython does
                if (less(best, x) if name == "max" else less(x, best)):
                    best = x
            return best
        if name == "abs":
            self._arity(name, args, 1)
            if is_int(args[0]):
                v = as_int(args[0])
                return -v if v < 0 else v
            raise ItemRuntimeError("TypeError: abs of " + type_name(args[0]))
        if name == "sorted":
            self._arity(name, args, 1)
            if not isinstance(args[0], list):
                raise Unsupported("sorted over " + type_name(args[0]))
            out = []
            for x in args[0]:      # stable insertion sort using `less`
                k = len(out)
                while k > 0 and less(x, out[k - 1]):
                    k -= 1
                out.insert(k, x)
            return out
        raise Unsupported("builtin " + name)

    @staticmethod
    def _arity(name, args, n):
        if len(args) != n:
            raise ItemRuntimeError("TypeError: %s takes %d argument(s)" % (name, n))


def run_module(tree: ast.Module) -> str:
    interp = Interp()
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 200_000))
    try:
        interp.exec_block(tree.body, None)
    finally:
        sys.setrecursionlimit(old)
    if len(interp.lines) != 1:
        raise ItemRuntimeError("program printed %d lines, expected exactly 1" % len(interp.lines))
    return interp.lines[0]


def source_of(question: str) -> str:
    if not (question.startswith(PREFIX) and question.endswith(SUFFIX)):
        raise Unsupported("question template not recognised")
    return question[len(PREFIX):-len(SUFFIX)]


def solve_c1(question: str, structured: dict) -> str:
    """Answer = the single line the program in the question text prints."""
    tree = ast.parse(source_of(question), mode="exec")   # parse only; never compiled or executed
    return run_module(tree)


# ---------------------------------------------------------------- structured front end (cross-check)

_BIN = {"+": ast.Add, "-": ast.Sub, "*": ast.Mult, "//": ast.FloorDiv, "%": ast.Mod}
_CMP = {"<": ast.Lt, "<=": ast.LtE, ">": ast.Gt, ">=": ast.GtE, "==": ast.Eq, "!=": ast.NotEq}


def _sx(x):
    """structured expression -> ast expression"""
    tag = x[0]
    if tag == "n":
        return ast.Constant(x[1])
    if tag == "s":
        return ast.Constant(x[1])
    if tag == "v":
        return ast.Name(x[1], ast.Load())
    if tag == "b":
        return ast.BinOp(_sx(x[2]), _BIN[x[1]](), _sx(x[3]))
    if tag == "c":
        return ast.Compare(_sx(x[2]), [_CMP[x[1]]()], [_sx(x[3])])
    if tag == "and":
        return ast.BoolOp(ast.And(), [_sx(x[1]), _sx(x[2])])
    if tag == "or":
        return ast.BoolOp(ast.Or(), [_sx(x[1]), _sx(x[2])])
    if tag == "not":
        return ast.UnaryOp(ast.Not(), _sx(x[1]))
    if tag == "list":
        return ast.List([_sx(y) for y in x[1:]], ast.Load())
    if tag == "idx":
        return ast.Subscript(_sx(x[1]), _sx(x[2]), ast.Load())
    if tag == "slice":
        def o(y):
            return None if y is None else _sx(y)
        return ast.Subscript(_sx(x[1]), ast.Slice(o(x[2]), o(x[3]), o(x[4])), ast.Load())
    if tag == "call":
        return ast.Call(ast.Name(x[1], ast.Load()), [_sx(y) for y in x[2:]], [])
    if tag == "m":
        return ast.Call(ast.Attribute(_sx(x[1]), x[2], ast.Load()), [_sx(y) for y in x[3:]], [])
    raise Unsupported("structured expression tag " + repr(tag))


def _ss(s):
    """structured statement -> ast statement"""
    tag = s[0]
    if tag == "set":
        return ast.Assign([ast.Name(s[1], ast.Store())], _sx(s[2]))
    if tag == "aug":
        return ast.AugAssign(ast.Name(s[1], ast.Store()), _BIN[s[2]](), _sx(s[3]))
    if tag == "setidx":
        return ast.Assign([ast.Subscript(ast.Name(s[1], ast.Load()), _sx(s[2]), ast.Store())], _sx(s[3]))
    if tag == "append":
        return ast.Expr(ast.Call(ast.Attribute(ast.Name(s[1], ast.Load()), "append", ast.Load()), [_sx(s[2])], []))
    if tag == "for":
        step = s[4] if isinstance(s[4], list) else ["n", s[4]]
        rng = ast.Call(ast.Name("range", ast.Load()), [_sx(s[2]), _sx(s[3]), _sx(step)], [])
        return ast.For(ast.Name(s[1], ast.Store()), rng, [_ss(y) for y in s[5]], [])
    if tag == "while":
        return ast.While(_sx(s[1]), [_ss(y) for y in s[2]], [])
    if tag == "if":
        return ast.If(_sx(s[1]), [_ss(y) for y in s[2]], [_ss(y) for y in s[3]])
    if tag == "def":
        args = ast.arguments(posonlyargs=[], args=[ast.arg(p) for p in s[2]], vararg=None,
                             kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
        return ast.FunctionDef(s[1], args, [_ss(y) for y in s[3]], [], None)
    if tag == "ret":
        return ast.Return(_sx(s[1]))
    if tag == "print":
        return ast.Expr(ast.Call(ast.Name("print", ast.Load()), [_sx(y) for y in s[1:]], []))
    raise Unsupported("structured statement tag " + repr(tag))


def structured_to_ast(program) -> ast.Module:
    return ast.Module([_ss(s) for s in program], [])


def solve_c1_structured(question: str, structured: dict) -> str:
    """Cross-check only: the same interpreter over the `structured` tree."""
    return run_module(structured_to_ast(structured["program"]))


LINEAGES = [
    "binary_search_f3", "bracket_matching_f3", "bytecode_loop_f3", "circle_elimination_r2",
    "cond_chain_f3", "counter_list_f3", "digit_peel_f3", "euclid_gcd_traced_f3", "fast_power_f4",
    "fib_like_f3", "fib_shapes_recursive_f3", "func_branch_f4", "func_compose_f4", "list_build_f3",
    "merge_two_sorted_f3", "nested_pairs_f3", "postfix_evaluation", "recursive_calls_r2",
    "run_length_scan", "shared_lists_f3", "slices_f4", "string_build_f3", "string_methods_f3",
    "turtle_walk_f3", "union_find_links_f3", "while_counter_f3",
]

SOLVERS = {"C1." + name: solve_c1 for name in LINEAGES}
