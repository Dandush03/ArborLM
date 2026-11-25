# ruff: noqa
"""Audit 3 (C1), step 3: shapes, closed formulas and cheap shortcuts, from the rendered SOURCE only (stdlib; imports nothing from studies/).

For every item: a shape label (lineage-specific, read from the source), generic rules, lineage-specific rules (S.*) and closed formulas (F.*).
Some S.* rules run a MUTATED copy of the item's program (e.g. turns removed, skips removed); those run in-process under a 2 s alarm.
Generic: MF (most frequent key, 2-fold CV), MFs (most frequent key per print form, 2-fold CV), BEST (best single generic literal rule,
chosen on one half, scored on the other, both ways). Usage:  python a3_shortcuts.py GEN_DIR OUT_JSON
"""
import ast, bisect, contextlib, gzip, glob, io, json, math, os, re, signal, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor


# ------------------------------------------------------------------ parsing helpers
def lit(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return -node.operand.value
    return None


def ints_in_order(tree):
    out = []

    class Vis(ast.NodeVisitor):
        def visit_UnaryOp(self, n):
            v = lit(n)
            if v is not None:
                out.append(v)
            else:
                self.generic_visit(n)

        def visit_Constant(self, n):
            v = lit(n)
            if v is not None:
                out.append(v)

    Vis().visit(tree)
    return out


def int_lists(tree):
    res = []
    for n in ast.walk(tree):
        if isinstance(n, ast.List) and n.elts and all(lit(e) is not None for e in n.elts):
            res.append((n.lineno, n.col_offset, [lit(e) for e in n.elts]))
    res.sort()
    return [x[2] for x in res]


def strs(tree):
    res = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            res.append((n.lineno, n.col_offset, n.value))
    res.sort()
    return [x[2] for x in res]


def alpha_dump(tree):
    """ast.dump with every identifier renamed by first appearance (builtins kept)."""
    keep = {"len", "sum", "max", "min", "abs", "str", "range", "print", "append", "upper", "lower", "replace", "count", "sorted"}
    mp = {}

    def nm(x):
        if x in keep:
            return x
        if x not in mp:
            mp[x] = f"v{len(mp)}"
        return mp[x]

    t = ast.parse(ast.unparse(tree))
    for n in ast.walk(t):
        if isinstance(n, ast.Name):
            n.id = nm(n.id)
        elif isinstance(n, ast.FunctionDef):
            n.name = nm(n.name)
            for a in n.args.args:
                a.arg = nm(a.arg)
        elif isinstance(n, ast.arg):
            n.arg = nm(n.arg)
    return t


def print_form(tree):
    t = alpha_dump(tree)
    pr = t.body[-1]
    return ast.dump(pr.value.args[0])


def run_src(src):
    buf = io.StringIO()

    def _al(s, f):
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, _al)
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<m>", "exec"), {"__name__": "__m__"})
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    finally:
        signal.signal(signal.SIGALRM, old)
    t = buf.getvalue()
    return t[:-1] if t.endswith("\n") and t.count("\n") == 1 else None


def sets(tree):
    """[(name, value_node)] for top-level-and-nested simple assignments, in order."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            out.append((n.lineno, n.targets[0].id, n.value))
    out.sort(key=lambda x: x[0])
    return [(a, b) for _, a, b in out]


def top_sets(tree):
    return [(n.targets[0].id, n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)]


def print_name(tree):
    a = tree.body[-1].value.args[0]
    return a.id if isinstance(a, ast.Name) else None


def range_args(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range":
            out.append((n.lineno, [lit(a) for a in n.args]))
    out.sort(key=lambda x: x[0])
    return [x[1] for x in out]


# ------------------------------------------------------------------ mutation helper
class DropIf(ast.NodeTransformer):
    """Replace the body of every `if` whose test source matches pat by `pass` (used to drop a branch's effect)."""

    def __init__(self, pat):
        self.pat = re.compile(pat)

    def visit_If(self, n):
        self.generic_visit(n)
        if self.pat.search(ast.unparse(n.test)):
            n.body = [ast.Pass()]
        return n


class DropAssignMatching(ast.NodeTransformer):
    def __init__(self, pat):
        self.pat = re.compile(pat)

    def visit_Assign(self, n):
        if self.pat.search(ast.unparse(n)):
            return ast.Pass()
        return n


def mutate_run(src, transformer):
    t = ast.parse(src)
    t = transformer.visit(t)
    ast.fix_missing_locations(t)
    return run_src(ast.unparse(t))


# ------------------------------------------------------------------ closed forms used by F.*
def max_suffix(xs):
    best, s = None, 0
    for v in reversed(xs):
        s += v
        best = s if best is None or s > best else best
    return best


def max_sub(xs):
    return max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1))


def OPF(op):
    return {">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}[op]


def digits(x, base):
    d = []
    while x:
        d.append(x % base)
        x //= base
    return d


# ------------------------------------------------------------------ lineage-specific shape + rules
def specific(lid, src, tree):
    """Returns (shape, {rule: prediction}) where rule names start with F. (closed formula) or S. (shortcut)."""
    L = {}
    ints = ints_in_order(tree)
    lists = int_lists(tree)
    ss = strs(tree)
    ts = top_sets(tree)
    pn = print_name(tree)
    last = src.strip().splitlines()[-1]
    sh = None
    if lid == "C1.string_build":
        sh = "len" if "print(len(" in last else ("rev" if "::(-1)]" in last else "s")
        ra = range_args(tree)[0]
        a, b = (0, ra[0]) if len(ra) == 1 else (ra[0], ra[1])
        if sh == "len":
            L["F.b_minus_a"] = str(b - a)
    elif lid == "C1.while_counter":
        if "!= 1" in src:
            sh = "collatz"
        elif "-=" in src:
            sh = "shrink"
            x0 = ints[0]
            m = re.search(r"while \w+ > (\d+):", src)
            T = int(m.group(1))
            d = int(re.search(r"-= (\d+)", src).group(1))
            L["F.shrink_closed"] = str(x0 - d * math.ceil((x0 - T) / d) if x0 > T else x0)
        else:
            sh = "grow"
            x0 = ints[0]
            T = int(re.search(r"while \w+ < (\d+):", src).group(1))
            mm = re.search(r"= \w+ \* (\d+) \+ (\d+)", src)
            mlt, c = int(mm.group(1)), int(mm.group(2))
            L["S.log_estimate"] = str(max(0, math.ceil(math.log(T / x0) / math.log(mlt))))
            L["S.log_estimate_floor"] = str(max(0, math.floor(math.log(T / x0) / math.log(mlt))))
    elif lid in ("C1.fast_power_r2", "C1.fast_power_traced"):
        names = [n for n, _ in ts]
        vals = {n: lit(v) for n, v in ts}
        res, b, e, m = names[0], names[1], names[2], names[3]
        B0, E0, M0 = vals[b], vals[e], vals[m]
        bl = E0.bit_length()
        if lid == "C1.fast_power_r2":
            sh = "res" if pn == res else ("base" if pn == b else "bsum")
            L["F.pow"] = str(pow(B0, E0, M0))
            L["F.base_final"] = str(pow(B0, 2 ** bl, M0))
            L["F.bsum"] = str(sum(pow(B0, 2 ** k, M0) for k in range(bl)))
            if sh == "res":
                L["F.closed"] = L["F.pow"]
            elif sh == "base":
                L["F.closed"] = L["F.base_final"]
            else:
                L["F.closed"] = L["F.bsum"]
        else:
            ms = re.search(r"< (\d+):", src.splitlines()[[i for i, l in enumerate(src.splitlines()) if l.startswith("while")][0]])
            if ms:
                sh = "res_after"
                s = int(ms.group(1))
                L["F.closed"] = str(pow(B0, E0 % (2 ** s), M0))
                L["S.full_pow"] = str(pow(B0, E0, M0))
            else:
                sh = "oddsum"
                L["F.closed"] = str(sum(pow(B0, 2 ** k, M0) for k in range(bl) if (E0 >> k) & 1))
                L["S.all_rounds_bsum"] = str(sum(pow(B0, 2 ** k, M0) for k in range(bl)))
    elif lid == "C1.euclid_gcd":
        x, y = ints[0], ints[1]
        if pn == ts[0][0]:
            sh = "gcd"
        elif re.search(r"\+= \w+ // \w+", src):
            sh = "quot"
        else:
            sh = "rsum"
        L["F.gcd"] = str(math.gcd(x, y))
        L["S.literal_x"] = str(x)
        L["S.literal_y"] = str(y)
        L["S.min_xy"] = str(min(x, y))
    elif lid == "C1.euclid_gcd_traced":
        x, y = ints[0], ints[1]
        sh = "state" if "' '" in last else "bigq"
        p, q, qs, st = x, y, [], []
        while q:
            qs.append(p // q)
            p, q = q, p % q
            st.append((p, q))
        if sh == "bigq":
            L["S.sum_all_quotients"] = str(sum(qs))
            L["S.sum_quot_ge2_from_2nd"] = str(sum(v for v in qs[1:] if v >= 2))
            L["S.first_quotient"] = str(qs[0])
        else:
            R = int(re.search(r"< (\d+):", src).group(1))
            L["S.state_one_more_round"] = f"{st[R][0]} {st[R][1]}" if R < len(st) else None
            L["S.state_one_less_round"] = f"{st[R-2][0]} {st[R-2][1]}" if R >= 2 else f"{x} {y}"
            L["S.gcd_0"] = f"{math.gcd(x, y)} 0"
    elif lid in ("C1.insertion_sort", "C1.insertion_sort_traced"):
        vals = lists[0]
        K = range_args(tree)[0][1]
        op = re.search(r"and \w+\[\w+\] (>=|<=|>|<) \w+:", src).group(1)
        f = OPF(op)
        if lid == "C1.insertion_sort":
            asc = op in (">", ">=")
            pre = sorted(vals[:K], reverse=not asc)
            after = pre + vals[K:]
            if last.startswith(f"print({ts[0][0]})"):
                sh = "list"
                L["F.closed"] = str(after)
            elif "[" in last:
                sh = "at"
                idx = int(re.search(r"\[(\d+)\]\)$", last).group(1))
                L["F.closed"] = str(after[idx])
                L["S.input_at_idx"] = str(vals[idx])
            else:
                sh = "shifts"
                L["F.closed"] = str(sum(1 for q in range(K) for p in range(q) if f(vals[p], vals[q])))
        else:
            sh = "holesum" if len([1 for n, v in ts if lit(v) == 0]) >= 1 and pn != None and pn != re.search(r"for \w+ in range\(1, \d+\):\n\s+\w+ = \w+\[\w+\]\n\s+(\w+) =", src).group(1) else "hole"
            jvar = re.search(r"for \w+ in range\(1, \d+\):\n\s+\w+ = \w+\[\w+\]\n\s+(\w+) =", src).group(1)
            sh = "hole" if pn == jvar else "holesum"
            hole = lambda i: sum(1 for x in vals[:i] if not f(x, vals[i])) - 1
            L["F.closed"] = str(hole(K - 1)) if sh == "hole" else str(sum(hole(i) for i in range(1, K)))
    elif lid in ("C1.kadane_scan", "C1.kadane_scan_traced"):
        vals = lists[0]
        names = [n for n, _ in ts]
        if lid == "C1.kadane_scan":
            cur, best = names[1], names[2]
            sh = "cur" if pn == cur else ("best" if pn == best else "curs")
            if sh == "best":
                L["F.closed"] = str(max_sub(vals))
                L["S.max_elem"] = str(max(vals))
                L["S.sum_pos"] = str(sum(v for v in vals if v > 0))
                L["S.sum_all"] = str(sum(vals))
            elif sh == "cur":
                L["F.closed"] = str(max_suffix(vals))
                L["S.last_elem"] = str(vals[-1])
            else:
                L["F.closed"] = str(sum(max_suffix(vals[: i + 1]) for i in range(1, len(vals))))
        else:
            if re.search(r"if \w+ < 0:", src):
                sh = "restarts"
                L["F.closed"] = str(sum(i for i in range(1, len(vals)) if max_suffix(vals[:i]) < 0))
                L["S.prev_negative"] = str(sum(i for i in range(1, len(vals)) if vals[i - 1] < 0))
            else:
                sh = "cur_at"
                p = range_args(tree)[0][1]
                L["F.closed"] = str(max_suffix(vals[:p]))
                L["S.elem_p_minus_1"] = str(vals[p - 1])
                L["S.maxsub_prefix"] = str(max_sub(vals[:p]))
    elif lid == "C1.minmax_track":
        vals = lists[0]
        op = re.search(r"if \w+\[\w+\] (<|>) \w+:", src).group(1)
        b = max(vals) if op == ">" else min(vals)
        pos = vals.index(b)
        names = [n for n, _ in ts]
        if "+" in last:
            sh = "sum"
            L["F.closed"] = str(b + pos)
        elif pn == names[1]:
            sh = "best"
            L["F.closed"] = str(b)
        else:
            sh = "pos"
            L["F.closed"] = str(pos)
    elif lid == "C1.partition_pass":
        vals = lists[0]
        m1 = range_args(tree)[0][0] if len(range_args(tree)[0]) == 1 else range_args(tree)[0][1]
        op = re.search(r"if \w+\[\w+\] (<=|<) \w+:", src).group(1)
        f = OPF(op)
        piv = vals[m1]
        if pn == ts[0][0]:
            sh = "list"
            L["S.sorted_prefix"] = str(sorted(vals[: m1 + 1]) + vals[m1 + 1:])
            lo = [v for v in vals[:m1] if f(v, piv)]
            hi = [v for v in vals[:m1] if not f(v, piv)]
            L["S.stable_partition"] = str(lo + [piv] + hi + vals[m1 + 1:])
        else:
            sh = "swapj"
            L["F.closed"] = str(sum(j for j in range(m1) if f(vals[j], piv)))
    elif lid == "C1.digit_peel":
        x = ints[0]
        base = int(re.search(r"% (\d+)\n", src).group(1))
        ds = digits(x, base)
        if "* 10 +" in src:
            sh = "rev"
            L["F.closed"] = str(int("".join(map(str, ds)))) if ds else "0"
        elif "% 2 == 0" in src:
            sh = "even"
            L["F.closed"] = str(sum(d for d in ds if d % 2 == 0))
        elif ">=" in src:
            sh = "countge"
            th = int(re.search(r">= (\d+)", src).group(1))
            L["F.closed"] = str(sum(1 for d in ds if d >= th))
        else:
            sh = "sum"
            L["F.closed"] = str(sum(ds))
        sh = sh + ("_b10" if base == 10 else "_bN")
        L["S.decimal_digits_of_literal"] = None
        dd = [int(c) for c in str(x)]
        if sh.startswith("sum"):
            L["S.decimal_digits_of_literal"] = str(sum(dd))
        elif sh.startswith("even"):
            L["S.decimal_digits_of_literal"] = str(sum(d for d in dd if d % 2 == 0))
        elif sh.startswith("countge"):
            L["S.decimal_digits_of_literal"] = str(sum(1 for d in dd if d >= th))
    elif lid == "C1.binary_search":
        vals, t = lists[0], ints[len(lists[0])]
        closed = "<=" in re.search(r"while (.*):", src).group(1)
        if "''" in src:
            sh = "path"
        elif re.search(r"\+= \w+\[\w+\]", src):
            sh = "sum"
        else:
            sh = "last"
        sh += "_closed" if closed else "_half"
        if sh.startswith("last"):
            if t in vals and closed:
                L["F.index_of_target"] = str(vals.index(t))
            bl = bisect.bisect_left(vals, t)
            L["S.bisect_left"] = str(bl)
            L["S.bisect_left_m1"] = str(bl - 1)
            L["S.index_or_bisect"] = str(vals.index(t)) if t in vals else str(bl)
        sh += "_present" if t in vals else "_absent"
    elif lid == "C1.counter_list":
        vals = lists[0]
        k = len(lists[1])
        c = [0] * k
        for v in vals:
            c[v % k] += 1
        sh = "counts"
        L["F.closed"] = str(c)
    elif lid == "C1.list_build":
        n = range_args(tree)[0][0]
        m = int(re.search(r"% (\d+)\)", src).group(1))
        sh = "sum" if "sum(" in last else ("max" if "max(" in last else "list")
        if sh == "max":
            L["S.m_minus_1"] = str(m - 1)
    elif lid == "C1.cond_chain":
        a, b = ints[0], ints[1]
        sh = "sum" if "+" in last else ("a" if pn == ts[0][0] else "b")
        L["S.gcd"] = str(math.gcd(a, b))
        L["S.2gcd"] = str(2 * math.gcd(a, b))
    elif lid == "C1.turtle_walk_r2":
        cmds = lists[0]
        sh = "pos" if "','" in last else ("far_half" if ">= 2:" in src else "xy")
        L["S.sum_forward"] = str(sum(c for c in cmds if c <= 3))
        L["S.zero"] = "0,0" if sh == "pos" else "0"
        L["S.no_turns"] = mutate_run(src, DropAssignMatching(r"% 4$"))
        L["S.no_back"] = mutate_run(src, DropIf(r"== 6$"))
    elif lid == "C1.bytecode_loop_r2":
        code = lists[0]
        sh = "other"
        L["S.sum_all_args"] = str(sum(code[1::2]))
        L["S.no_skips"] = mutate_run(src, DropIf(r"% 2 == \w+ % 2"))
        L["S.always_skip"] = None
    elif lid == "C1.merge_two_sorted_r2":
        a, b = lists[0], lists[1]
        op = "<=" if "<=" in src.split("while")[1].splitlines()[1] else "<"
        i = j = 0
        seq = []
        while i < len(a) or j < len(b):
            if j >= len(b) or (i < len(a) and (a[i] <= b[j] if op == "<=" else a[i] < b[j])):
                seq.append(0); i += 1
            else:
                seq.append(1); j += 1
        L["S.full_merge_runs"] = str(1 + sum(1 for k in range(1, len(seq)) if seq[k] != seq[k - 1]))
        L["S.min_len_x2"] = str(2 * min(len(a), len(b)))
        L["S.min_len_x2_m1"] = str(2 * min(len(a), len(b)) - 1)
        sh = "switch"
    elif lid == "C1.majority_vote_scan_r2":
        vals = lists[0]
        sh = "pair" if "' '" in last else "repl"
        if sh == "pair":
            L["S.last_1"] = f"{vals[-1]} 1"
            L["S.mode_1"] = f"{Counter(vals).most_common(1)[0][0]} 1"
        else:
            L["S.first_elem"] = str(vals[0])
            L["S.sum_distinct"] = str(sum(set(vals)))
            L["S.first_plus_last"] = str(vals[0] + vals[-1])
    elif lid == "C1.cellular_update_r2":
        init = lists[0]
        sh = "row" if pn == ts[0][0] else "weighted"
        L["S.echo_init_row"] = str(init) if sh == "row" else str(sum(i * v for i, v in enumerate(init)))
    elif lid == "C1.sieve_marking_r2":
        fl = lists[0]
        sh = "indexsum" if src.count("for ") >= 2 else "strikesum"
        allones = src.replace(str(fl), str([1] * len(fl)), 1)
        L["S.all_ones_start"] = run_src(allones)
        isp = lambda k: k >= 2 and all(k % d for d in range(2, int(k ** 0.5) + 1))
        if sh == "indexsum":
            L["S.flagged_primes_and_01"] = str(sum(k for k in range(len(fl)) if fl[k] == 1 and (k < 2 or isp(k))))
            L["S.flagged_all"] = str(sum(k for k in range(len(fl)) if fl[k] == 1))
    elif lid == "C1.circle_elimination_r2":
        sh = "survivor" if src.count("for ") >= 2 else ("sum" if len(ts) >= 3 else "last")
    elif lid in ("C1.bracket_matching", "C1.bracket_matching_traced"):
        s = ss[0]
        if lid == "C1.bracket_matching":
            sh = "code" if "* 10" in last else ("first" if "(-1)" in src else "height")
            if sh == "height":
                L["S.opens_minus_closes"] = str(max(0, sum(1 for c in s if c in "([") - sum(1 for c in s if c in ")]")))
        else:
            m = re.search(r"for \w+ in range\((\d+)\):\n\s+\w+ = ", src)
            if m:
                sh = "height_at"
                p = int(m.group(1))
                L["S.opens_minus_closes_prefix"] = str(max(0, sum(1 for c in s[:p] if c in "([") - sum(1 for c in s[:p] if c in ")]")))
            else:
                sh = "pops"
                L["S.sum_pos_all_closers"] = str(sum(i for i, c in enumerate(s) if c in ")]"))
    elif lid == "C1.shared_lists":
        sh = "list" if pn else ("sum" if "sum(" in last else ("len" if "len(" in last else "at"))
    elif lid == "C1.union_find_links":
        sh = "root" if "find(" in last else ("parents" if pn and pn == ts[0][0] else "rootsum")
        if sh == "root":
            L["S.query_node"] = re.search(r"find\(\w+, (\d+)\)\)$", last).group(1)
    return sh, L


GEN_RULES = None


def generic_preds(src, tree):
    P = {}
    ints = ints_in_order(tree)
    for k in range(10):
        P[f"lit{k}"] = str(ints[k]) if k < len(ints) else None
        P[f"litr{k+1}"] = str(ints[-k - 1]) if k < len(ints) else None
    lists = int_lists(tree)
    ss = strs(tree)
    if lists:
        x = lists[0]
        P["L.len"], P["L.sum"], P["L.max"], P["L.min"], P["L.echo"] = str(len(x)), str(sum(x)), str(max(x)), str(min(x)), str(x)
        for k in range(4):
            P[f"L.e{k}"] = str(x[k]) if k < len(x) else None
            P[f"L.er{k+1}"] = str(x[-k - 1]) if k < len(x) else None
        P["L.sorted"] = str(sorted(x))
        P["L.rsorted"] = str(sorted(x, reverse=True))
    if ss:
        P["S0.echo"], P["S0.len"], P["S0.rev"] = ss[0], str(len(ss[0])), ss[0][::-1]
    ra = range_args(tree)
    if ra:
        a = ra[0]
        P["R.stop"] = str(a[0] if len(a) == 1 else a[1]) if (a[0] if len(a) == 1 else a[1]) is not None else None
        try:
            P["R.count"] = str(len(range(*a))) if all(v is not None for v in a) else None
        except Exception:
            P["R.count"] = None
    pn = print_name(tree)
    if pn:
        la = [v for n, v in sets(tree) if n == pn and lit(v) is not None]
        P["last_assigned_literal"] = str(lit(la[-1])) if la else None
    P["const0"], P["const1"], P["constm1"] = "0", "1", "-1"
    return P


def item_record(row):
    src = row["src"]
    tree = ast.parse(src)
    sh, S = specific(row["lid"], src, tree)
    pf = print_form(tree)
    G = generic_preds(src, tree)
    ints = set(str(v) for v in ints_in_order(tree))
    return {"lv": row["lv"], "i": row["i"], "key": row["key"], "shape": sh or "pf:" + pf[:120], "pf": pf, "S": S, "G": G,
            "oracle_any_literal": row["key"] in ints}


def process_file(fn):
    rows = [json.loads(l) for l in gzip.open(fn, "rt")]
    return rows[0]["lid"], [item_record(r) for r in rows]


def cv_mf(items, keyf):
    """2-fold CV most-frequent-key accuracy (folds: even/odd item index); keyf gives the conditioning label."""
    hit = 0
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        tab = defaultdict(Counter)
        for x in train:
            tab[keyf(x)][x["key"]] += 1
        for x in test:
            c = tab.get(keyf(x))
            if c:
                best = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                hit += best == x["key"]
    return hit / len(items)


def cv_best_generic(items):
    rules = sorted({r for x in items for r in x["G"]})
    hit, chosen = 0, []
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        sc = {r: sum(1 for x in train if x["G"].get(r) == x["key"]) for r in rules}
        best = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        chosen.append(best)
        hit += sum(1 for x in test if x["G"].get(best) == x["key"])
    return hit / len(items), chosen


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(gen, "*.jsonl.gz")))
    res = {}
    with ProcessPoolExecutor(14) as ex:
        for lid, recs in ex.map(process_file, files):
            per = {}
            for lv in range(7):
                its = [x for x in recs if x["lv"] == lv]
                n = len(its)
                mf = cv_mf(its, lambda x: 0)
                mfs = cv_mf(its, lambda x: x["pf"])
                mfsh = cv_mf(its, lambda x: x["shape"])
                bg, ch = cv_best_generic(its)
                shapes = Counter(x["shape"] for x in its)
                srules = {}
                for sh in sorted(shapes):
                    sub = [x for x in its if x["shape"] == sh]
                    rn = sorted({r for x in sub for r in x["S"]})
                    for r in rn:
                        k = sum(1 for x in sub if x["S"].get(r) is not None and x["S"][r] == x["key"])
                        applies = sum(1 for x in sub if x["S"].get(r) is not None)
                        srules[f"{sh}|{r}"] = {"hit": k, "applies": applies, "n_shape": len(sub), "rate_in_shape": round(k / len(sub), 3),
                                               "ci": wilson(k, len(sub)), "share_of_level": round(len(sub) / n, 3),
                                               "mf_in_shape_cv": round(cv_mf(sub, lambda x: 0), 3)}
                per[lv] = {"n": n, "MF_cv": round(mf, 3), "MF_printform_cv": round(mfs, 3), "MF_shape_cv": round(mfsh, 3), "BEST_generic_cv": round(bg, 3),
                           "BEST_generic_chosen": ch, "oracle_any_literal": round(sum(x["oracle_any_literal"] for x in its) / n, 3),
                           "shapes": dict(shapes), "S": srules,
                           "distinct_keys": len({x["key"] for x in its})}
            res[lid] = per
            print(lid, "done", flush=True)
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
